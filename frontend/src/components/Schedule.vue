<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { mockSchedule } from '../data/mock'

// === 1. УМНАЯ МАТЕМАТИКА ДАТ И ВРЕМЕНИ ===
const semesterStartDate = new Date('2026-03-23T00:00:00')
const selectedDate = ref(new Date())
const realToday = new Date()

// === переменная открытия шторки групп===
// === ШТОРКА И ДАННЫЕ ИЗ REDIS ===
const isGroupSheetOpen = ref(false)

// Эмуляция того самого хэша из Redis + даты от C++ парсера
const groupInfo = ref({
  institute_full_name: 'ИНСТИТУТ ЭКОНОМИКИ И МЕНЕДЖМЕНТА',
  institute_short_name: null, // Если тут будет null или '', интерфейс сам перестроится
  study_form: 'ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)',
  file_title: '2 курс',
  logo_url: 'https://rguk.ru/local/templates/rguk_redesign/images/ieml.svg',
  semester_dates: '1 сентября — 28 декабря 2026'
})

// === ФИЗИКА СВАЙПА ШТОРКИ ===
const sheetY = ref(0)
const isDraggingSheet = ref(false)
let dragStartY = 0

const onSheetTouchStart = (e: TouchEvent) => {
  dragStartY = e.touches[0].clientY
  isDraggingSheet.value = true
}

const onSheetTouchMove = (e: TouchEvent) => {
  const currentY = e.touches[0].clientY
  const delta = currentY - dragStartY
  
  // Разрешаем тянуть только вниз
  if (delta > 0) {
    sheetY.value = delta
    // Блокируем системный скролл при перетаскивании
    if (e.cancelable) e.preventDefault()
  }
}

const onSheetTouchEnd = () => {
  isDraggingSheet.value = false
  // Если протянули больше чем на 100 пикселей вниз - закрываем
  if (sheetY.value > 100) {
    isGroupSheetOpen.value = false
  }
  // В любом случае сбрасываем Y. Если не закрылась - красиво отпружинит обратно
  sheetY.value = 0
}

// Форматируем форму обучения (делаем первую букву заглавной, остальное строчными)
const formatStudyForm = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

// Реактивная переменная с текущим временем в минутах (от начала суток)
const currentMinutes = ref(new Date().getHours() * 60 + new Date().getMinutes())


// === СИМУЛЯЦИЯ СЕТИ ===
const isLoading = ref(true) // При первом открытии приложения сразу показываем скелет

// Имитация запроса к твоему бэкенду (Redis -> C++ -> JSON)
const fetchScheduleData = () => {
  isLoading.value = true
  // Ждем 2 секунды и "получаем" данные
  setTimeout(() => {
    isLoading.value = false
  }, 2000)
}

// Запускаем при загрузке компонента
onMounted(() => {
  fetchScheduleData()
  // ... тут твой старый код таймера
  timerId = setInterval(() => {
    const now = new Date()
    currentMinutes.value = now.getHours() * 60 + now.getMinutes()
  }, 60000)
})


// Обновляем время каждую минуту, чтобы live-эффекты работали в реальном времени
let timerId: number
onMounted(() => {
  timerId = setInterval(() => {
    const now = new Date()
    currentMinutes.value = now.getHours() * 60 + now.getMinutes()
  }, 60000)
})
onUnmounted(() => clearInterval(timerId))

const isEvenWeek = computed(() => {
  const start = semesterStartDate.getTime()
  const current = selectedDate.value.getTime()
  const diffDays = Math.floor((current - start) / (24 * 60 * 60 * 1000))
  const diffWeeks = Math.floor(diffDays / 7)
  return diffWeeks % 2 !== 0 
})

const currentWeekDates = computed(() => {
  const dates = []
  const current = new Date(selectedDate.value)
  const day = current.getDay()
  const diff = current.getDate() - day + (day === 0 ? -6 : 1) 
  const monday = new Date(current.setDate(diff))
  for (let i = 0; i < 7; i++) {
    const nextDate = new Date(monday)
    nextDate.setDate(monday.getDate() + i)
    dates.push(nextDate)
  }
  return dates
})

const monthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
const shortDays = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

// === 2. ФИЛЬТРАЦИЯ И СТЕЙТЫ ПАР ===
const currentLessons = computed(() => {
  let jsDay = selectedDate.value.getDay()
  let apiDay = jsDay === 0 ? 6 : jsDay - 1
  return mockSchedule.lessons
    .filter((lesson) => lesson.day_of_week === apiDay && lesson.is_even_week === isEvenWeek.value)
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
})

const isSameDate = (d1: Date, d2: Date) => {
  return d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate()
}
const isRealToday = (d: Date) => isSameDate(d, realToday)

// Вычисление стейта пары (past, now, soon, future)
const getLessonState = (lesson: any) => {
  // Если это не сегодняшний реальный день - все пары дефолтные (будущее/прошлое нас не волнует)
  if (!isRealToday(selectedDate.value)) return 'future'

  const parseTime = (timeStr: string) => {
    const [h, m] = timeStr.split(':').map(Number)
    return h * 60 + m
  }
  
  const start = parseTime(lesson.start_time)
  const end = parseTime(lesson.end_time)
  const now = currentMinutes.value

  if (now > end) return 'past'
  if (now >= start && now <= end) return 'now'
  // Если до пары осталось 15 минут или меньше
  if (start - now > 0 && start - now <= 15) return 'soon'
  
  return 'future'
}

// === 3. ЛОГИКА СВАЙПОВ ===
const transitionName = ref('slide-left')
const touchStartX = ref(0)
const touchStartY = ref(0)

const selectDate = (date: Date) => {
  if (date.getTime() > selectedDate.value.getTime()) transitionName.value = 'slide-left'
  else if (date.getTime() < selectedDate.value.getTime()) transitionName.value = 'slide-right'
  selectedDate.value = date
}

const changeDay = (delta: number) => {
  transitionName.value = delta > 0 ? 'slide-left' : 'slide-right'
  const newDate = new Date(selectedDate.value)
  newDate.setDate(newDate.getDate() + delta)
  selectedDate.value = newDate
}

const onTouchStart = (e: TouchEvent) => {
  touchStartX.value = e.changedTouches[0].screenX
  touchStartY.value = e.changedTouches[0].screenY
}

const onTouchEnd = (e: TouchEvent) => {
  const deltaX = e.changedTouches[0].screenX - touchStartX.value
  const deltaY = e.changedTouches[0].screenY - touchStartY.value
  if (Math.abs(deltaY) > Math.abs(deltaX)) return
  if (deltaX > 40) changeDay(-1)
  else if (deltaX < -40) changeDay(1)
}

// === 4. ВСПОМОГАТЕЛЬНЫЕ ===
const getBadgeColor = (type: string) => {
  const t = type.toLowerCase()
  if (t.includes('лек')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (t.includes('пр')) return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
  if (t.includes('лаб')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
}

const formatPlace = (place: string) => {
  if (!place) return { main: '', sub: '' }
  const match = place.match(/^(.*?)\s*(\(.*?\))$/)
  return match ? { main: match[1], sub: match[2] } : { main: place, sub: '' }
}
</script>

<template>
  <div class="flex flex-col h-full bg-slate-950 text-slate-50 overflow-hidden">
    
    <!-- Шапка -->
    <div class="px-4 pt-6 pb-4 flex flex-col gap-3">
<!-- Верхний ряд шапки: Группа и бейдж недели -->
      <div class="flex items-start justify-between">
        
        <!-- Кнопка-селектор группы -->
        <button @click="isGroupSheetOpen = true" class="flex items-center gap-1.5 px-3 py-1.5 -ml-3 rounded-xl hover:bg-slate-900/80 transition-colors">
          <div class="w-5 h-5 rounded-md bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
          </div>
          <span class="font-bold text-slate-200 tracking-wide text-sm">Д-101</span>
          <svg class="w-3.5 h-3.5 text-slate-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
        </button>

        <!-- Правый блок: Бейдж недели + Кнопка обновления -->
        <div class="flex items-center gap-2">
          <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border bg-slate-900/50" :class="isEvenWeek ? 'border-indigo-500/20' : 'border-emerald-500/20'">
            <div class="w-1.5 h-1.5 rounded-full shadow-[0_0_8px_currentColor]" :class="isEvenWeek ? 'bg-indigo-400 text-indigo-400' : 'bg-emerald-400 text-emerald-400'"></div>
            <span class="text-xs font-semibold tracking-wide" :class="isEvenWeek ? 'text-indigo-400' : 'text-emerald-400'">
              {{ isEvenWeek ? 'Четная' : 'Нечетная' }}
            </span>
          </div>

          <!-- Кнопка обновления (крутится пока isLoading = true) -->
          <button 
            @click="fetchScheduleData"
            :disabled="isLoading"
            class="p-1.5 rounded-lg border border-slate-800 bg-slate-900/50 text-slate-400 transition-colors"
            :class="isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-800 hover:text-slate-200 active:scale-95'"
          >
            <svg class="w-4 h-4" :class="{'animate-spin text-indigo-400': isLoading}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>
      <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent capitalize">
        {{ monthNames[selectedDate.getMonth()] }}
      </h2>
    </div>

    <!-- Монолитная труба дней -->
    <div class="px-4 py-2">
      <div class="relative flex w-full bg-slate-900/60 rounded-2xl p-1 backdrop-blur-sm border border-slate-800">
        <div 
          class="absolute top-1 bottom-1 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-500/30 transition-transform duration-300 cubic-bezier(0.4, 0, 0.2, 1)"
          :style="{ width: 'calc((100% - 8px) / 7)', transform: `translateX(calc(${selectedDate.getDay() === 0 ? 6 : selectedDate.getDay() - 1} * 100%))` }"
        ></div>
        <button
          v-for="(date, index) in currentWeekDates" :key="index" @click="selectDate(date)"
          class="relative z-10 flex-1 py-1.5 flex flex-col justify-center items-center transition-all duration-300 touch-manipulation rounded-xl overflow-hidden"
          :class="isSameDate(selectedDate, date) ? 'text-white' : 'text-slate-400 hover:text-slate-300'"
        >
          <div v-if="isRealToday(date)" class="absolute inset-0 pointer-events-none" style="background: radial-gradient(circle at center, rgba(59, 192, 241, 0.28) 5%, transparent 76%);"></div>
          <span class="relative z-10 text-[10px] font-medium uppercase tracking-wider mb-0.5">{{ shortDays[date.getDay()] }}</span>
          <span class="relative z-10 text-base font-bold leading-none">{{ date.getDate() }}</span>
        </button>
      </div>
    </div>

    <!-- Список пар -->
    <div class="flex-1 relative overflow-hidden" @touchstart="onTouchStart" @touchend="onTouchEnd">
<!-- Список пар -->
      <Transition :name="transitionName" mode="out-in">
        <div :key="selectedDate.getTime()" class="absolute inset-0 px-4 py-4 overflow-y-auto space-y-4 pb-24 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] overscroll-y-contain [-webkit-overflow-scrolling:touch]">
          
          <!-- === СТЕЙТ 1: ИДЕТ ЗАГРУЗКА (СКЕЛЕТЫ) === -->
          <template v-if="isLoading">
            <div v-for="i in 4" :key="'skeleton-'+i" class="relative flex rounded-3xl p-4 bg-slate-900/40 border border-slate-800/40 shadow-sm animate-pulse">
              <!-- Левая колонка (время) -->
              <div class="w-[4.5rem] flex flex-col items-center pr-3 border-r border-slate-800/30 shrink-0 gap-2.5 pt-1 pb-1">
                <div class="h-4 w-11 bg-slate-700/50 rounded-md"></div>
                <div class="h-3 w-9 bg-slate-800/80 rounded-md"></div>
                <div class="mt-auto h-4 w-full bg-slate-800/60 rounded-md"></div>
              </div>
              <!-- Правая колонка (детали) -->
              <div class="flex-1 pl-4 flex flex-col justify-center py-1 gap-3.5">
                <div class="h-3.5 w-16 bg-slate-700/40 rounded-md"></div>
                <div class="space-y-2">
                  <div class="h-4 w-11/12 bg-slate-700/60 rounded-md"></div>
                  <div class="h-4 w-2/3 bg-slate-700/40 rounded-md"></div>
                </div>
                <div class="space-y-2 mt-1">
                  <div class="h-3 w-1/3 bg-slate-800 rounded-md"></div>
                  <div class="h-3 w-1/2 bg-slate-800 rounded-md"></div>
                </div>
              </div>
            </div>
          </template>

          <!-- === СТЕЙТ 2: ЗАГРУЗКА ПРОШЛА, НО ДЕНЬ ПУСТОЙ === -->
          <div v-else-if="currentLessons.length === 0" class="mt-12 flex flex-col items-center justify-center text-center space-y-3 opacity-60">
            <div class="w-20 h-20 rounded-full bg-slate-900/50 border border-slate-800 flex items-center justify-center text-3xl">😴</div>
            <p class="text-slate-400 text-sm font-medium">В этот день пар нет.<br>Можно отдохнуть!</p>
          </div>

          <!-- === СТЕЙТ 3: ЗАГРУЗКА ПРОШЛА, ЕСТЬ ПАРЫ (Твой код) === -->
          <template v-else>
            <div 
              v-for="lesson in currentLessons" :key="lesson.id" 
              class="relative flex rounded-3xl p-4 backdrop-blur-md transition-all duration-500"
              :class="{
                'bg-slate-900/80 border border-slate-800/80 shadow-sm': getLessonState(lesson) === 'future',
                'bg-slate-900/40 border border-slate-800/40 opacity-50 grayscale-[30%]': getLessonState(lesson) === 'past',
                'bg-slate-900/90 border border-amber-500/30 shadow-[0_0_20px_rgba(245,158,11,0.08)]': getLessonState(lesson) === 'soon',
                'bg-slate-900/95 border border-indigo-500/40 shadow-[0_0_25px_rgba(99,102,241,0.15)]': getLessonState(lesson) === 'now'
              }"
            >
              <!-- Левая колонка времени -->
              <div class="w-[4.5rem] flex flex-col items-center pr-3 border-r shrink-0" :class="getLessonState(lesson) === 'now' ? 'border-indigo-500/30' : (getLessonState(lesson) === 'soon' ? 'border-amber-500/30' : 'border-slate-800/50')">
                <span class="text-base font-bold" :class="getLessonState(lesson) === 'now' ? 'text-indigo-400' : (getLessonState(lesson) === 'soon' ? 'text-amber-400' : 'text-white')">
                  {{ lesson.start_time.slice(0, 5) }}
                </span>
                <span class="text-[13px] font-semibold text-slate-400 mt-0.5">{{ lesson.end_time.slice(0, 5) }}</span>
                <span class="mt-auto text-[10px] uppercase font-bold tracking-widest text-slate-300 bg-slate-800/80 border border-slate-700/50 px-1.5 py-0.5 rounded-md whitespace-nowrap">
                  {{ lesson.number_of_lesson }} пара
                </span>
              </div>

              <!-- Правая колонка деталей -->
              <div class="flex-1 pl-4 flex flex-col justify-center min-w-0">
                <div class="flex items-center justify-between mb-2">
                  <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide rounded-md border" :class="getBadgeColor(lesson.type_of_lesson)">
                    {{ lesson.type_of_lesson }}
                  </span>
                  <!-- Индикатор "Скоро" -->
                  <div v-if="getLessonState(lesson) === 'soon'" class="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                    <div class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
                    <span class="text-[9px] font-bold uppercase tracking-wider text-amber-500">Скоро</span>
                  </div>
                  <!-- Индикатор "Идет сейчас" -->
                  <div v-if="getLessonState(lesson) === 'now'" class="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">
                    <div class="relative flex h-1.5 w-1.5">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-500"></span>
                    </div>
                    <span class="text-[9px] font-bold uppercase tracking-wider text-indigo-400">Идет сейчас</span>
                  </div>
                </div>

                <h3 class="text-sm font-semibold leading-snug text-slate-100 break-words whitespace-normal">{{ lesson.lesson_name }}</h3>
                
                <div class="mt-3 flex flex-col gap-3">
                  <div v-if="lesson.classroom" class="flex items-center text-xs text-slate-400 mt-0.5">
                    <div class="flex items-center shrink-0">
                      <svg class="w-3.5 h-3.5 mr-1.5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" /></svg>
                      <span class="font-medium text-slate-300">{{ lesson.classroom }}</span>
                      <span class="mx-3 opacity-40">•</span>
                    </div>
                    <div class="flex flex-col text-[10px] leading-[1.35]">
                      <span>{{ formatPlace(lesson.educational_place).main }}</span>
                      <span v-if="formatPlace(lesson.educational_place).sub" class="opacity-70">{{ formatPlace(lesson.educational_place).sub }}</span>
                    </div>
                  </div>
                  <div v-if="lesson.teachers && lesson.teachers.length > 0" class="flex items-start text-xs text-slate-400">
                    <svg class="w-3.5 h-3.5 mr-1.5 mt-0.5 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                    <div class="flex flex-col gap-0.5"><span v-for="teacher in lesson.teachers" :key="teacher.id" class="truncate font-medium">{{ teacher.name }}</span></div>
                  </div>
                </div>
              </div>
            </div>
          </template>

        </div>
      </Transition>
      <div class="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent pointer-events-none z-30"></div>
    </div>

    <!-- === ШТОРКА ГРУППЫ (BOTTOM SHEET) === -->
        <Teleport to="body">
        
        <!-- Темный фон (Backdrop) -->
        <Transition name="fade">
            <div v-if="isGroupSheetOpen" @click="isGroupSheetOpen = false" class="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-[60]"></div>
        </Transition>

        <!-- Сама выезжающая панель -->
        <Transition name="slide-up">
            <div 
            v-if="isGroupSheetOpen" 
            class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 rounded-t-[2rem] z-[70] shadow-[0_-10px_40px_rgba(0,0,0,0.3)]"
            style="padding-bottom: env(safe-area-inset-bottom);"
            :style="{ 
                transform: sheetY > 0 ? `translateY(${sheetY}px)` : '',
                transition: isDraggingSheet ? 'none' : 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }"
            >
            
            <!-- ЗОНА СВАЙПА (Язычок + Заголовок) -->
            <div 
                @touchstart="onSheetTouchStart" 
                @touchmove="onSheetTouchMove" 
                @touchend="onSheetTouchEnd"
                class="px-5 pt-3 pb-4 touch-none"
            >
                <!-- Ползунок сверху -->
                <div class="w-full flex justify-center mb-4">
                <div class="w-12 h-1.5 bg-slate-700/50 rounded-full"></div>
                </div>

                <!-- Заголовок -->
                <div class="flex items-center justify-between pointer-events-none">
                <h2 class="text-2xl font-bold text-white tracking-tight">Группа Д-101</h2>
                <button @click.stop="isGroupSheetOpen = false" class="p-2 rounded-full bg-slate-800/50 text-slate-400 pointer-events-auto">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
                </div>
            </div>

            <!-- Контент шторки (не реагирует на свайп, можно скроллить если надо) -->
            <div class="px-5 pb-8">
                
    <!-- Главная информационная карточка (Минимализм) -->
                <div class="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-4 flex flex-col gap-4">
                
                <!-- 1. Институт (Адаптивный рендер short_name и full_name) -->
                <div class="flex items-center gap-3.5">
                    <!-- Логотип -->
                    <div class="w-11 h-11 rounded-xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center shrink-0 overflow-hidden p-2">
                    <img v-if="groupInfo.logo_url" :src="groupInfo.logo_url" class="w-full h-full object-contain filter invert opacity-80" alt="Логотип" />
                    <svg v-else class="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" />
                    </svg>
                    </div>
                    
                    <!-- Названия -->
                    <div class="flex flex-col justify-center">
                    <!-- Если есть short_name (например, ИЭиМ), выводим его как акцентный микро-заголовок -->
                    <span 
                        v-if="groupInfo.institute_short_name" 
                        class="text-[11px] text-indigo-400 font-bold uppercase tracking-widest mb-0.5"
                    >
                        {{ groupInfo.institute_short_name }}
                    </span>
                    <!-- Полное название -->
                    <span class="text-xs font-semibold text-slate-200 leading-tight uppercase">
                        {{ groupInfo.institute_full_name }}
                    </span>
                    </div>
                </div>

                <div class="h-px w-full bg-gradient-to-r from-transparent via-slate-700/50 to-transparent"></div>

                <!-- 2. Сетка: Поток, Форма (БЕЗ ЗАГОЛОВКОВ) и Даты -->
                <div class="grid grid-cols-2 gap-y-4 gap-x-4 items-center">
                    
                    <!-- Поток (например, "2 курс") -->
                    <div class="flex flex-col justify-center">
                    <span class="text-base font-bold text-slate-100">{{ groupInfo.file_title }}</span>
                    </div>
                    
                    <!-- Форма обучения -->
                    <div class="flex flex-col justify-center border-l border-slate-700/50 pl-4">
                    <span class="text-xs font-medium text-slate-300 leading-snug">
                        {{ formatStudyForm(groupInfo.study_form) }}
                    </span>
                    </div>

                <!-- Период обучения (Заголовок оставили, как ты просил) -->
                <div class="col-span-2 flex flex-col pt-3 border-t border-slate-700/30">
                  <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Период обучения</span>
                  <span class="text-sm font-medium text-slate-200">{{ groupInfo.semester_dates }}</span>
                </div>
                
              </div>

            </div>

                <!-- Место под Избранное -->
                <div class="mt-6">
                <span class="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Сохраненные расписания</span>
                <div class="mt-3 flex flex-col items-center justify-center py-6 bg-slate-800/20 border border-slate-700/30 border-dashed rounded-xl">
                    <span class="text-sm text-slate-400 font-medium">Пока нет других групп</span>
                </div>
                </div>

            </div>
            </div>
        </Transition>
        </Teleport>
  </div>
</template>

<style scoped>
/* Анимация затемнения фона */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Анимация выезда шторки снизу */
.slide-up-enter-active, .slide-up-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-up-enter-from, .slide-up-leave-to {
  transform: translateY(100%);
}
</style scoped>
