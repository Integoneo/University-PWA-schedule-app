<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { store } from '../store'

const router = useRouter()
const route = useRoute()

// 1. Инициализируем шаг из URL (если параметр есть) или ставим 1
const step = ref(Number(route.query.step) || 1)

// 2. СЛЕДИМ ЗА СИСТЕМНОЙ КНОПКОЙ "НАЗАД"
// Если URL изменился (пользователь свайпнул назад), обновляем наш шаг
watch(() => route.query.step, (newStep) => {
  step.value = Number(newStep) || 1
})

// Универсальная функция перехода на новый шаг
const goToStep = (newStep: number) => {
  // Вместо изменения переменной, мы пушим новый параметр в историю роутера.
  // Vue Router сам изменит step.value благодаря watch, описанному выше!
  router.push({ query: { step: newStep } })
}

const searchQuery = ref('')
const selectedInstitute = ref<any>(null)
const selectedForm = ref<string>('')
const selectedCourse = ref<string>('')


// === ХЭШ-ФУНКЦИЯ ДЛЯ ГРАДИЕНТОВ ===
const getGroupStyle = (name: string) => {
  const styles = [
    'bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-indigo-500/20 hover:border-indigo-500/40',
    'bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/20 hover:border-emerald-500/40',
    'bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20 hover:border-amber-500/40',
    'bg-gradient-to-br from-rose-500/10 to-pink-500/10 border-rose-500/20 hover:border-rose-500/40',
    'bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-cyan-500/20 hover:border-cyan-500/40',
    'bg-gradient-to-br from-fuchsia-500/10 to-purple-500/10 border-fuchsia-500/20 hover:border-fuchsia-500/40'
  ]
  // Переводим строку в уникальное число
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return styles[Math.abs(hash) % styles.length]
}

// === МАССИВНЫЕ ТЕСТОВЫЕ ДАННЫЕ ===
const institutes = [
  {
    id: 1,
    name: "ИНСТИТУТ ЭКОНОМИКИ И МЕНЕДЖМЕНТА",
    short_name: "ИЭиМ",
    icon_url: "https://rguk.ru/local/templates/rguk_redesign/images/ieml.svg",
    groups: [
      // 1 курс (Большой поток)
      { id: 101, name: "Д-101", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 102, name: "Д-102", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 103, name: "Д-103", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 104, name: "Д-104", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 105, name: "Д-105", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 106, name: "Д-106", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 107, name: "Д-107", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 108, name: "Д-108", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      // 2 курс
      { id: 109, name: "Д-201", course: "2 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 110, name: "Д-202", course: "2 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      // Заочка
      { id: 111, name: "З-101", course: "1 курс", education_form: "ЗАОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 112, name: "З-102", course: "1 курс", education_form: "ЗАОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
    ]
  },
  {
    id: 2,
    name: "ТЕХНОЛОГИЧЕСКИЙ ИНСТИТУТ ТЕКСТИЛЬНОЙ ПРОМЫШЛЕННОСТИ",
    short_name: "ТИТиЛП",
    icon_url: null,
    groups: [
      // Тестируем сложные/длинные названия
      { id: 301, name: "КТД-11-425", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 302, name: "КТД-11-426", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 303, name: "КШК-9-425", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 304, name: "КШК-9-426", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
      { id: 305, name: "Т-101", course: "1 курс", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ (ДНЕВНАЯ)" },
    ]
  },
  {
    id: 3,
    name: "МАГИСТРАТУРА",
    short_name: null,
    icon_url: null,
    groups: [
      // Куча программ по 1-2 группы (как ты и говорил: 30+ программ в жизни)
      { id: 201, name: "ПМИ-1", course: "01.04.02 Прикладная математика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 202, name: "ПМИ-2", course: "01.04.02 Прикладная математика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 203, name: "БИ-1", course: "38.04.05 Бизнес-информатика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 204, name: "БИ-2", course: "38.04.05 Бизнес-информатика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 205, name: "ЭК-1", course: "38.04.01 Экономика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 206, name: "ЭК-2", course: "38.04.01 Экономика", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
      { id: 207, name: "М-1", course: "38.04.02 Менеджмент", education_form: "ОЧНАЯ ФОРМА ОБУЧЕНИЯ" },
    ]
  }
]
// === ЛОГИКА ГЛОБАЛЬНОГО ПОИСКА ===

// 1. Делаем плоский массив вообще всех групп, приклеивая к каждой инфу о ее институте
const allGroupsFlattened = computed(() => {
  const all: any[] = []
  for (const inst of institutes) {
    for (const g of inst.groups) {
      all.push({ ...g, institute: inst })
    }
  }
  return all
})

// 2. Фильтруем этот массив по тому, что ввел студент
const searchResults = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) return []
  return allGroupsFlattened.value.filter(g => g.name.toLowerCase().includes(query))
})

// === ЛОГИКА ШАГОВ (DRILL-DOWN) ===

const availableForms = computed(() => {
  if (!selectedInstitute.value) return []
  const forms = selectedInstitute.value.groups.map((g: any) => g.education_form)
  return [...new Set(forms)]
})

const availableCourses = computed(() => {
  if (!selectedInstitute.value || !selectedForm.value) return []
  const filtered = selectedInstitute.value.groups.filter((g: any) => g.education_form === selectedForm.value)
  const courses = filtered.map((g: any) => g.course)
  return [...new Set(courses)]
})

const availableGroups = computed(() => {
  if (!selectedInstitute.value || !selectedForm.value || !selectedCourse.value) return []
  return selectedInstitute.value.groups.filter((g: any) => 
    g.education_form === selectedForm.value && g.course === selectedCourse.value
  )
})

const goBack = () => {
  // Наша кастомная кнопка "Назад" в шапке теперь делает то же самое, что и системная
  router.back()
}

const onSelectInstitute = (inst: any) => {
  selectedInstitute.value = inst
  if (availableForms.value.length === 1) {
    selectedForm.value = availableForms.value[0] as string
    goToStep(3) // Прыгаем на 3 шаг (и в истории браузера сохранится именно это)
  } else {
    goToStep(2)
  }
}

const onSelectForm = (form: any) => {
  selectedForm.value = form
  goToStep(3)
}

const onSelectCourse = (course: any) => {
  selectedCourse.value = course
  goToStep(4)
}

const onSelectGroup = (group: any, parentInstitute?: any) => {
  const inst = parentInstitute || selectedInstitute.value
  const groupDataToSave = {
    institute_full_name: inst.name,
    institute_short_name: inst.short_name,
    logo_url: inst.icon_url,
    file_title: group.course,
    study_form: group.education_form,
    group_name: group.name,
    group_id: group.id
  }
  
  // 1. Сохраняем группу в память
  store.setGroup(groupDataToSave)
  
  // 2. МАГИЯ ОЧИСТКИ ИСТОРИИ БРАУЗЕРА
  // Считаем, насколько глубоко мы зашли в меню (например, на 4 шаге глубина = 3)
  const depth = step.value - 1
  
  if (depth > 0) {
    // router.go(-depth) заставляет телефон отмотать историю назад на нужное кол-во шагов.
    // Как только браузер отмотает нас на самое начало онбординга,
    // сработает наш новый Guard из router/index.ts и автоматически перенаправит на /lessons!
    router.go(-depth)
  } else {
    // Если мы нашли группу прямо на первом шаге (через инпут поиска), истории шагов нет
    router.replace('/lessons')
  }
}
// Заголовок динамически меняется, если мы что-то ищем
const stepTitle = computed(() => {
  if (step.value === 1) return searchQuery.value ? 'Поиск группы' : 'Институт'
  if (step.value === 2) return 'Форма обучения'
  if (step.value === 3) return 'Курс или программа'
  if (step.value === 4) return 'Группа'
})

const formatText = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}
</script>

<template>
  <div class="h-full w-full bg-slate-950 flex flex-col px-5 pt-12 pb-8 overflow-y-auto">
    
    <!-- Шапка онбординга -->
    <div class="mb-6 relative">
      <div class="h-8 mb-1 flex items-center">
        <Transition name="fade">
          <button v-if="step > 1" @click="goBack" class="inline-flex items-center gap-1 text-slate-400 hover:text-white transition-colors p-1 -ml-1">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
            <span class="text-sm font-medium">Назад</span>
          </button>
        </Transition>
      </div>
      
      <!-- Анимированный заголовок -->
      <Transition name="fade-title" mode="out-in">
        <h1 :key="stepTitle" class="text-3xl font-bold text-white tracking-tight leading-tight">
          {{ stepTitle }}
        </h1>
      </Transition>
    </div>
    <!-- Область контента -->
    <Transition name="slide" mode="out-in">
      
      <!-- ШАГ 1: Поиск ИЛИ Список институтов -->
      <div v-if="step === 1" class="flex flex-col gap-4">
        
        <!-- Инпут поиска -->
        <div class="relative">
          <input 
            :value="searchQuery"
            @input="searchQuery = ($event.target as HTMLInputElement).value"
            type="text" 
            placeholder="Найти группу (например, ПМИ-1)" 
            class="w-full bg-slate-900/60 border border-slate-800 rounded-2xl py-3.5 pl-12 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:bg-slate-900 transition-all shadow-sm"
          />
          <!-- Иконка лупы -->
          <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          
          <!-- Крестик для очистки инпута -->
          <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1 rounded-full bg-slate-800/80 transition-colors">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- Если есть текст в поиске -> показываем результаты -->
<!-- БЛОК С АНИМАЦИЕЙ ПЕРЕКЛЮЧЕНИЯ (Институты <-> Поиск) -->
        <Transition name="fade-switch" mode="out-in">
          
          <!-- ЕСЛИ ЕСТЬ ПОИСК -> Показываем результаты -->
          <div v-if="searchQuery" :key="'search-results'" class="flex flex-col gap-3">
            
            <!-- Состояние "Не найдено" -->
            <Transition name="fade">
              <div v-if="searchResults.length === 0" class="flex flex-col items-center justify-center py-10 opacity-60">
                 <span class="text-3xl mb-2">🤔</span>
                 <span class="text-slate-400 text-sm">Группа не найдена</span>
              </div>
            </Transition>
            
            <!-- Анимированный список найденных групп -->
            <TransitionGroup name="list" tag="div" class="flex flex-col gap-3">
              <button 
                v-for="res in searchResults" :key="res.id"
                @click="onSelectGroup(res, res.institute)"
                class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left group"
              >
                <!-- Левая часть (Текст) -->
                <div class="flex flex-col flex-1 min-w-0 pr-4">
                  <span class="text-lg font-bold text-white mb-1 group-hover:text-indigo-400 transition-colors truncate">{{ res.name }}</span>
                  <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest truncate">{{ res.institute.short_name || res.institute.name }}</span>
                  <span class="text-[11px] text-slate-500 truncate mt-0.5">{{ res.course }}</span>
                </div>
                
                <!-- Правая часть (Кнопка) -->
                <div class="px-2.5 py-1 bg-slate-800/80 border border-slate-700/50 rounded-lg shrink-0 mt-1">
                  <span class="text-[10px] font-bold text-slate-300 uppercase">Выбрать</span>
                </div>
              </button>
            </TransitionGroup>
          </div>

          <!-- ЕСЛИ ПОИСКА НЕТ -> Показываем институты -->
          <div v-else :key="'institute-list'" class="flex flex-col gap-3">
            <button 
              v-for="inst in institutes" :key="inst.id"
              @click="onSelectInstitute(inst)"
              class="flex items-center gap-4 bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left"
            >
              <div class="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-center shrink-0 overflow-hidden p-2.5">
                <img v-if="inst.icon_url" :src="inst.icon_url" class="w-full h-full object-contain filter invert opacity-80" alt="" />
                <svg v-else class="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" /></svg>
              </div>
              <div class="flex flex-col flex-1 min-w-0">
                <span v-if="inst.short_name" class="text-[11px] text-indigo-400 font-bold uppercase tracking-widest">{{ inst.short_name }}</span>
                <span class="text-sm font-semibold text-slate-200 uppercase truncate" :class="!inst.short_name ? 'text-sm' : ''">{{ inst.name }}</span>
              </div>
              <svg class="w-5 h-5 text-slate-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
            </button>
          </div>

        </Transition>
      </div>

      <!-- ШАГ 2: Форма обучения -->
      <div v-else-if="step === 2" class="flex flex-col gap-3">
        <!-- ... КОД ШАГА 2 БЕЗ ИЗМЕНЕНИЙ ... -->
        <button v-for="form in availableForms" :key="form as string" @click="onSelectForm(form)" class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left">
          <span class="text-base font-semibold text-slate-200">{{ formatText(form as string) }}</span>
          <svg class="w-5 h-5 text-slate-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>

      <!-- ШАГ 3: Курс или программа (Магистратура) -->
      <div v-else-if="step === 3" class="flex flex-col gap-3">
        <!-- ... КОД ШАГА 3 БЕЗ ИЗМЕНЕНИЙ ... -->
        <button v-for="course in availableCourses" :key="course as string" @click="onSelectCourse(course)" class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left">
          <span class="text-sm font-semibold text-slate-200 leading-snug pr-4">{{ course }}</span>
          <svg class="w-5 h-5 text-slate-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>

<!-- ШАГ 4: Итоговый выбор группы -->
      <div v-else-if="step === 4" class="grid grid-cols-2 gap-3 pb-8">
        <button 
          v-for="group in availableGroups" :key="group.id"
          @click="onSelectGroup(group)"
          class="flex flex-col items-center justify-center border py-5 px-3 rounded-2xl transition-all text-center group active:scale-95 shadow-sm"
          :class="getGroupStyle(group.name)"
        >
          <!-- text-base и tracking-tight спасают от разрыва длинных имен, а break-words перенесет текст, если совсем не влезет -->
          <span class="text-base font-bold text-white mb-1 uppercase tracking-tight break-words w-full">{{ group.name }}</span>
          <span class="text-[10px] uppercase tracking-widest text-slate-400">Выбрать</span>
        </button>
      </div>

    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-enter-active, .slide-leave-active { transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.slide-enter-from { opacity: 0; transform: translateX(20px); }
.slide-leave-to { opacity: 0; transform: translateX(-20px); }
/* Анимация переключения заголовка (быстрое затухание со смещением вверх) */
.fade-title-enter-active, .fade-title-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-title-enter-from { opacity: 0; transform: translateY(10px); }
.fade-title-leave-to { opacity: 0; transform: translateY(-10px); }

/* Анимация смены Институты <-> Результаты поиска */
.fade-switch-enter-active, .fade-switch-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-switch-enter-from { opacity: 0; transform: scale(0.98); }
.fade-switch-leave-to { opacity: 0; transform: scale(0.98); }

/* Анимация элементов внутри списка результатов поиска (TransitionGroup) */
.list-enter-active, .list-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.list-enter-from, .list-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}
/* Чтобы удаляемые элементы не ломали верстку во время анимации */
.list-leave-active {
  position: absolute;
  width: 100%;
}
</style>
