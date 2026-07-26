<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import BottomSheet from './BottomSheet.vue'
import { store } from '../store'
import { api } from '../api'

const router = useRouter()

// === 1. УМНАЯ МАТЕМАТИКА ДАТ И ВРЕМЕНИ ===
const semesterStartDate = ref(new Date('2026-03-23T00:00:00')) 
const anchorIsEven = ref(false) 

// Границы семестра с бэкенда
const educationStart = ref<Date | null>(null)
const educationEnd = ref<Date | null>(null)

const selectedDate = ref(new Date())
const realToday = new Date()
const currentMinutes = ref(new Date().getHours() * 60 + new Date().getMinutes())

// === EXCEL ОРИГИНАЛ ===
const isExcelModalOpen = ref(false)
const originalExcelUrl = ref<string | null>(null)

// === ШТОРКА И ДАННЫЕ ИЗ STORE ===
const isGroupSheetOpen = ref(false)

const groupInfo = computed(() => store.groupInfo || {
  institute_full_name: 'Загрузка...',
  institute_short_name: null,
  study_form: '',
  file_title: '...',
  logo_url: '',
  group_name: '...'
})

const formatStudyForm = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

// Красивое форматирование периода обучения для шторки
const formattedSemesterDates = computed(() => {
  if (!educationStart.value || !educationEnd.value) return 'Загрузка...'
  const formatter = new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long' })
  const start = formatter.format(educationStart.value)
  const end = formatter.format(educationEnd.value)
  const year = educationEnd.value.getFullYear()
  return `${start} — ${end} ${year}`
})


// Переменная живет ВНЕ функции, чтобы помнить время последнего клика
let lastManualFetch = 0 

// === РЕАЛЬНАЯ СЕТЬ (API) ===
const isLoading = ref(true)
const allLessons = ref<any[]>([]) 
const isOffline = ref(false)

const fetchScheduleData = async (isManual = false) => {
  if (!store.groupInfo) {
    router.push('/')
    return
  }

  // === 1. ГЕНИАЛЬНАЯ ЗАЩИТА ОТ СПАМА (ФЕЙКОВАЯ РАБОТА) ===
  if (isManual) {
    const now = Date.now()
    // Если с прошлого обновления прошло меньше 5 секунд (5000 мс)
    if (now - lastManualFetch < 5000) {
      isLoading.value = true
      // Имитируем бурную деятельность на 400 миллисекунд
      await new Promise(res => setTimeout(res, 400)) 
      store.addToast('Расписание актуально', 'success')
      isLoading.value = false
      return // ПРЕРЫВАЕМ ФУНКЦИЮ! До твоего сервера запрос не долетит.
    }
    lastManualFetch = now
  }

  isLoading.value = true
  isOffline.value = false
  const startTime = Date.now() // Засекаем время старта реального запроса
  
  try {
    const config = await api.getConfig()
    if (config) {
      semesterStartDate.value = config.anchorDate
      anchorIsEven.value = config.isEven
    }

    const data = await api.getSchedule(store.groupInfo.group_id)
    allLessons.value = data.lessons || []
    
    // Сохраняем ссылку на эксель
    originalExcelUrl.value = data.view_url || null
    
    if (data.start_education_date) educationStart.value = new Date(data.start_education_date)
    if (data.end_education_date) educationEnd.value = new Date(data.end_education_date)
    
    if (educationStart.value && educationEnd.value) {
      const todayTime = realToday.getTime()
      const startTimeSemester = educationStart.value.getTime()
      const endTimeSemester = educationEnd.value.getTime()

      if (todayTime > endTimeSemester) {
        selectedDate.value = new Date(educationEnd.value)
      } else if (todayTime < startTimeSemester) {
        selectedDate.value = new Date(educationStart.value)
      } else {
        selectedDate.value = new Date(realToday)
      }
    }

    // === 2. МИНИМАЛЬНОЕ ВРЕМЯ АНИМАЦИИ (Красота) ===
    if (isManual) {
      const elapsed = Date.now() - startTime
      // Если запрос выполнился слишком быстро (например за 10мс из кэша),
      // докручиваем таймер, чтобы анимация длилась ровно 500мс
      if (elapsed < 800) {
        await new Promise(res => setTimeout(res, 800 - elapsed))
      }
    }

    // === ЛОГИКА РАЗГОВОРЧИВОЙ КНОПКИ ===
    if (isManual) {
      if (data._meta.status === 'actual') {
        store.addToast('Расписание актуально', 'success') 
      } else if (data._meta.status === 'updated') {
        store.addToast('Расписание обновлено', 'success')
      } else if (data._meta.status === 'offline') {
        store.addToast('Нет сети. Показана кэшированная версия', 'error')
      }
    }
    
  } catch (error) {
    isOffline.value = true
    allLessons.value = []
  } finally {
    isLoading.value = false
  }
}


let timerId: number


onMounted(() => {
  fetchScheduleData()
  timerId = setInterval(() => {
    const now = new Date()
    currentMinutes.value = now.getHours() * 60 + now.getMinutes()
  }, 60000)
})
onUnmounted(() => clearInterval(timerId))

const isEvenWeek = computed(() => {
  const start = semesterStartDate.value.getTime()
  const current = selectedDate.value.getTime()
  const diffDays = Math.floor((current - start) / (24 * 60 * 60 * 1000))
  const diffWeeks = Math.floor(diffDays / 7)
  return anchorIsEven.value ? (diffWeeks % 2 === 0) : (diffWeeks % 2 !== 0)
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

// === ЛИМИТЫ И СОСТОЯНИЯ СЕМЕСТРА ===
const semesterState = computed(() => {
  if (!educationStart.value || !educationEnd.value) return 'active' // Если дат еще нет - считаем активным

  const current = selectedDate.value.getTime()
  const start = educationStart.value.getTime()
  
  // Конец семестра считаем до последней миллисекунды этого дня
  const end = new Date(educationEnd.value)
  end.setHours(23, 59, 59, 999)
  const endTime = end.getTime()

  if (current < start) return 'before'
  if (current > endTime) return 'after'
  return 'active'
})

// === 2. ФИЛЬТРАЦИЯ И СТЕЙТЫ ПАР ===
const currentLessons = computed(() => {
  // Если семестр еще не начался или уже закончился — пар НЕТ, не пытаемся их даже искать
  if (semesterState.value !== 'active') return []

  let jsDay = selectedDate.value.getDay()
  let apiDay = jsDay === 0 ? 6 : jsDay - 1
  return allLessons.value
    .filter((lesson) => lesson.day_of_week === apiDay && lesson.is_even_week === isEvenWeek.value)
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
})

const isSameDate = (d1: Date, d2: Date) => {
  return d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate()
}
const isRealToday = (d: Date) => isSameDate(d, realToday)

const getLessonState = (lesson: any) => {
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
  if (start - now > 0 && start - now <= 15) return 'soon'
  return 'future'
}



// === ЕДИНЫЙ КОНТРОЛЛЕР СОСТОЯНИЙ (STATE MACHINE) ===
// Эта штука гарантирует, что Vue не запутается в v-if'ах при перерисовках
const currentState = computed(() => {
  if (isLoading.value) return 'loading'
  if (isOffline.value) return 'offline'
  if (semesterState.value === 'before') return 'before'
  if (semesterState.value === 'after') return 'after'
  if (currentLessons.value.length === 0) return 'empty'
  return 'lessons'
})



// === 3. ЛОГИКА СВАЙПОВ (Освобожденная) ===
const transitionName = ref('slide-left')
const touchStartX = ref(0)
const touchStartY = ref(0)

const selectDate = (date: Date) => {
  // Никаких тостов и блокировок, просто листаем!
  if (date.getTime() > selectedDate.value.getTime()) transitionName.value = 'slide-left'
  else if (date.getTime() < selectedDate.value.getTime()) transitionName.value = 'slide-right'
  selectedDate.value = date
}

const changeDay = (delta: number) => {
  const newDate = new Date(selectedDate.value)
  newDate.setDate(newDate.getDate() + delta)
  transitionName.value = delta > 0 ? 'slide-left' : 'slide-right'
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

// === ФУНКЦИЯ КОПИРОВАНИЯ РАСПИСАНИЯ ===
const copyDaySchedule = async () => {
  if (currentLessons.value.length === 0) return

  const dateStr = `${selectedDate.value.getDate()} ${monthNames[selectedDate.value.getMonth()].toLowerCase()}`
  let text = `📅 Расписание на ${dateStr} (${shortDays[selectedDate.value.getDay()]}):\n\n`

  currentLessons.value.forEach(l => {
    text += `🕒 ${l.start_time.slice(0,5)} - ${l.end_time.slice(0,5)} | ${l.lesson_name} (${l.type_of_lesson})\n`
    if (l.classroom || l.educational_place) {
      const place = formatPlace(l.educational_place).main
      text += `📍 ${l.classroom ? l.classroom + ' ' : ''}${place ? '(' + place + ')' : ''}\n`
    }
    if (l.teachers && l.teachers.length > 0) {
      text += `👨‍🏫 ${l.teachers.map((t: any) => t.name).join(', ')}\n`
    }
    text += `\n`
  })

  // 1. Пытаемся использовать современный API (Сработает на HTTPS/localhost)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text.trim())
      store.addToast('Расписание скопировано', 'success')
      return
    } catch (err) {
      console.warn('Clipboard API failed, trying fallback...', err)
    }
  }

  // 2. Фолбэк для HTTP (твой случай с 192.168.x.x)
  try {
    const textArea = document.createElement("textarea")
    textArea.value = text.trim()
    // Прячем элемент за экраном
    textArea.style.position = "fixed"
    textArea.style.left = "-999999px"
    textArea.style.top = "-999999px"
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    
    const successful = document.execCommand('copy')
    textArea.remove()
    
    if (successful) {
      store.addToast('Расписание скопировано', 'success')
    } else {
      store.addToast('Не удалось скопировать', 'error')
    }
  } catch (err) {
    store.addToast('Ошибка копирования', 'error')
  }
}

// === 4. ВСПОМОГАТЕЛЬНЫЕ ===
const getBadgeColor = (type: string) => {
  if (!type) return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
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
        
        <!-- Кнопка-селектор группы (Теперь не ломается от длинных имен) -->
        <button @click="isGroupSheetOpen = true" class="flex items-center gap-1.5 px-3 py-1.5 -ml-3 rounded-xl hover:bg-slate-900/80 transition-colors max-w-[55%]">
          <div class="w-5 h-5 rounded-md bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0 text-indigo-400">
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
          </div>
          <!-- ДОБАВЛЕН truncate -->
          <span class="font-bold text-slate-200 tracking-wide text-sm truncate">{{ groupInfo.group_name }}</span>
          <svg class="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
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
            @click="fetchScheduleData(true)" 
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
    <div class="px-4 py-2 relative flex flex-col items-end">
      
      <!-- ГЛАВНАЯ ТРУБА (z-10, чтобы быть ПОВЕРХ закладки) -->
      <div class="relative flex w-full bg-slate-900/60 rounded-2xl p-1 backdrop-blur-sm border border-slate-800 z-10">
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
  <!-- Внутренний контент (он отобразится, но не будет раздвигать верстку) -->
      <!-- ЗАКЛАДКА (z-0, прячется ПОД трубой, вылезает за счет -mt-2 и pt-3) -->
      <Transition name="fade">
        <div v-if="currentState === 'lessons'" class="w-full h-0 relative">
          <button
            @click="copyDaySchedule"
            class="
              absolute top-0 right-4 z-1 flex items-center gap-1 px-3 
              -mt-2 pt-3 pb-1.5 /* -mt-2 затягивает кнопку под трубу, pt-3 компенсирует это для текста */
              rounded-b-xl backdrop-blur-md transition-all active:scale-95
              bg-slate-900/40 border border-slate-800/90 border-t-0 shadow-sm
              text-slate-500 hover:text-slate-300 hover:bg-slate-800/60
            "
          >
            <svg class="w-4 h-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          </button>
        </div>
      </Transition>




    </div>
    <div class="flex-1 relative overflow-hidden" @touchstart="onTouchStart" @touchend="onTouchEnd">
    <!-- Список пар -->
      <Transition :name="transitionName" mode="out-in">
        <div :key="selectedDate.getTime()" class="absolute inset-0 px-4 py-4 overflow-y-auto space-y-4 pb-24 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] overscroll-y-contain [-webkit-overflow-scrolling:touch]">
          
          <!-- СТЕЙТ 1: ЗАГРУЗКА -->
          <div v-if="currentState === 'loading'" class="flex flex-col gap-4">
            <div v-for="i in 4" :key="'skeleton-'+i" class="relative flex rounded-3xl p-4 bg-slate-900/40 border border-slate-800/40 shadow-sm animate-pulse">
              <div class="w-[4.5rem] flex flex-col items-center pr-3 border-r border-slate-800/30 shrink-0 gap-2.5 pt-1 pb-1">
                <div class="h-4 w-11 bg-slate-700/50 rounded-md"></div>
                <div class="h-3 w-9 bg-slate-800/80 rounded-md"></div>
                <div class="mt-auto h-4 w-full bg-slate-800/60 rounded-md"></div>
              </div>
              <div class="flex-1 pl-4 flex flex-col justify-center py-1 gap-3.5">
                <div class="h-3.5 w-16 bg-slate-700/40 rounded-md"></div>
                <div class="space-y-2">
                  <div class="h-4 w-11/12 bg-slate-700/60 rounded-md"></div>
                  <div class="h-4 w-2/3 bg-slate-700/40 rounded-md"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- СТЕЙТ 1.5: ОФФЛАЙН (Если нет кэша) -->
          <div v-else-if="currentState === 'offline'" class="mt-12 flex flex-col items-center justify-center text-center space-y-4 px-4">
            <div class="w-20 h-20 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
              <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18M9 9l3 3m0 0l3-3m-3 3v4" /></svg>
            </div>
            <div class="flex flex-col gap-1">
              <h3 class="text-white font-bold text-lg">Нет подключения</h3>
              <p class="text-slate-400 text-sm">Расписание еще не загружено, а интернета нет.</p>
            </div>
            <button @click="fetchScheduleData" class="mt-2 px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl border border-slate-700 transition-colors active:scale-95">
              Обновить
            </button>
          </div>

          <!-- СТЕЙТ 2: ДО СЕМЕСТРА -->
          <div v-else-if="currentState === 'before'" class="mt-12 flex flex-col items-center justify-center text-center space-y-3 opacity-60">
            <div class="w-20 h-20 rounded-full bg-slate-900/50 border border-slate-800 flex items-center justify-center text-3xl">🏖️</div>
            <p class="text-slate-400 text-sm font-medium">Семестр еще не начался.<br>Можно со спокойной душой кайфовать!</p>
          </div>

          <!-- СТЕЙТ 3: ПОСЛЕ СЕМЕСТРА -->
          <div v-else-if="currentState === 'after'" class="mt-12 flex flex-col items-center justify-center text-center space-y-3 opacity-60">
            <div class="w-20 h-20 rounded-full bg-slate-900/50 border border-slate-800 flex items-center justify-center text-3xl">🎓</div>
            <p class="text-slate-400 text-sm font-medium">Учеба всё! Желаем удачи на сессии<br>(или классного отдыха).</p>
          </div>

          <!-- СТЕЙТ 4: ПУСТОЙ ДЕНЬ -->
          <div v-else-if="currentState === 'empty'" class="mt-12 flex flex-col items-center justify-center text-center space-y-3 opacity-60">
            <div class="w-20 h-20 rounded-full bg-slate-900/50 border border-slate-800 flex items-center justify-center text-3xl">😴</div>
            <p class="text-slate-400 text-sm font-medium">В этот день пар нет.<br>Можно отдохнуть!</p>
          </div>

          <!-- СТЕЙТ 5: ЕСТЬ ПАРЫ -->
          <div v-else-if="currentState === 'lessons'" class="flex flex-col gap-4">
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
          </div>
        </div>
      </Transition>
      <div class="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent pointer-events-none z-30"></div>
    </div>

<!-- === УНИВЕРСАЛЬНАЯ ШТОРКА ГРУППЫ === -->
    <BottomSheet :is-open="isGroupSheetOpen" @close="isGroupSheetOpen = false">
      
    <!-- ЗОНА СВАЙПА: Заголовок шторки -->
      <template #header>
        <div class="flex items-center justify-between pointer-events-none mb-2">
          <!-- ДОБАВЛЕН break-words, уменьшен шрифт для конских названий -->
          <h2 class="text-xl pr-4 font-bold text-white tracking-tight break-words">Группа {{ groupInfo?.group_name || 'Д-101' }}</h2>
          <button @click.stop="isGroupSheetOpen = false" class="p-2 -mr-2 rounded-full text-slate-400 pointer-events-auto active:scale-95 transition-transform shrink-0">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </template>

      <!-- КОНТЕНТ ШТОРКИ (Оставляешь свою карточку Института как есть) -->

      <!-- КОНТЕНТ ШТОРКИ -->
      
        <!-- Главная информационная карточка -->
      <div class="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-4 flex flex-col gap-4">
        <!-- Институт -->
        <div class="flex items-center gap-3.5">
          <!-- Иконка как в Onboarding (Белая) -->
          <div class="w-11 h-11 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0 p-1.5">
            <img v-if="groupInfo.logo_url" :src="groupInfo.logo_url" class="w-full h-full object-contain" alt="Логотип" />
            <svg v-else class="w-6 h-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" /></svg>
          </div>
          <div class="flex flex-col justify-center min-w-0 pr-2">
            <span v-if="groupInfo.institute_short_name" class="text-[11px] text-indigo-400 font-bold uppercase tracking-widest mb-0.5">{{ groupInfo.institute_short_name }}</span>
            <span class="text-xs font-semibold text-slate-200 leading-tight uppercase line-clamp-2 break-words">{{ groupInfo.institute_full_name }}</span>
          </div>
        </div>

        <div class="h-px w-full bg-gradient-to-r from-transparent via-slate-700/50 to-transparent"></div>

        <!-- Сетка: Поток, Форма и Даты -->
        <div class="grid grid-cols-2 gap-y-4 gap-x-4 items-center">
          <div class="flex flex-col justify-center">
            <span class="text-base font-bold text-slate-100">{{ groupInfo.file_title }}</span>
          </div>
          <div class="flex flex-col justify-center border-l border-slate-700/50 pl-4">
            <span class="text-xs font-medium text-slate-300 leading-snug">{{ formatStudyForm(groupInfo.study_form) }}</span>
          </div>
          <div class="col-span-2 flex flex-col pt-3 border-t border-slate-700/30">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Период обучения</span>
            <!-- ДИНАМИЧЕСКИЕ ДАТЫ -->
            <span class="text-sm font-medium text-slate-200">{{ formattedSemesterDates }}</span>
          </div>
        </div>
      </div>

    <!-- КНОПКА ОРИГИНАЛЬНОГО РАСПИСАНИЯ -->
      <div v-if="originalExcelUrl" class="mt-4">
        <button 
          @click="isExcelModalOpen = true"
          class="w-full py-3.5 flex items-center justify-center gap-2 rounded-xl transition-colors font-bold text-sm active:scale-[0.98] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Оригинал от ВУЗа (Excel)
        </button>
      </div>

    </BottomSheet>

<!-- === ПОЛНОЭКРАННОЕ ОКНО EXCEL === -->
    <!-- Используем Transition для красивого появления поверх всего -->
    <Transition name="fade">
      <div v-if="isExcelModalOpen" class="fixed inset-0 z-[100] flex flex-col bg-slate-950">
        
        <!-- Шапка модалки -->
        <div class="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 shrink-0 shadow-md z-10">
          <div class="flex items-center gap-3 pr-4 overflow-hidden">
             <div class="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-500 shrink-0">
               <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
             </div>
            <h3 class="text-white font-bold text-[15px] truncate">Официальное расписание</h3>
          </div>
          <button @click="isExcelModalOpen = false" class="p-2 -mr-2 rounded-full text-slate-400 hover:bg-slate-800 hover:text-white active:scale-95 transition-all shrink-0">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- Контейнер для iframe (flex-1 занимает всю оставшуюся высоту) -->
        <div class="flex-1 w-full bg-slate-900 relative">
          <!-- Скелетон загрузки (крутится под iframe, пока тот грузится) -->
          <div class="absolute inset-0 flex flex-col items-center justify-center space-y-4 opacity-50">
            <svg class="w-8 h-8 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span class="text-sm font-semibold text-slate-400">Загрузка документа...</span>
          </div>

          <!-- Сам iframe -->
          <!-- z-10 перекрывает скелетон, как только прогрузится -->
          <iframe 
            :src="originalExcelUrl" 
            class="absolute inset-0 w-full h-full border-0 z-10 bg-white" 
            allowfullscreen
          ></iframe>
        </div>
        
      </div>
    </Transition>

  </div>
</template>
<style scoped>
/* Общие настройки скорости и плавности (как в iOS) */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* === АНИМАЦИЯ ВПЕРЕД (Свайп влево, следующий день) === */
/* Новый день вылетает справа */
.slide-left-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
/* Старый день улетает влево */
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* === АНИМАЦИЯ НАЗАД (Свайп вправо, прошлый день) === */
/* Новый день вылетает слева */
.slide-right-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}
/* Старый день улетает вправо */
.slide-right-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
