<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { store } from '../store'
import { api, normalizeStudyForm } from '../api'

const router = useRouter()
const route = useRoute()

// === СОСТОЯНИЯ ЗАГРУЗКИ АПИ ===
const isLoading = ref(true)
const fetchError = ref('')
const apiInstitutes = ref<any[]>([])

// Выносим загрузку в отдельную функцию, чтобы ее можно было дергать и при старте, и по кнопке
const loadInstitutes = async () => {
  isLoading.value = true
  fetchError.value = '' // Обязательно сбрасываем старую ошибку!
  
  try {
    apiInstitutes.value = await api.getInstitutes()
  } catch (err) {
    fetchError.value = 'Не удалось загрузить список институтов. Проверьте интернет.'
    store.addToast('Ошибка соединения с сервером', 'error')
  } finally {
    isLoading.value = false
  }
}

// Загружаем данные при старте
onMounted(() => {
  loadInstitutes()
})
// === ЛОГИКА НАВИГАЦИИ (URL STEP) ===
const step = ref(Number(route.query.step) || 1)

watch(() => route.query.step, (newStep) => {
  step.value = Number(newStep) || 1
})

const goToStep = (newStep: number) => {
  router.push({ query: { step: newStep } })
}

const goBack = () => {
  router.back()
}

// === СОСТОЯНИЯ ВЫБОРА ===
const searchQuery = ref('')
const selectedInstitute = ref<any>(null)
const selectedForm = ref<string>('')
const selectedCourse = ref<string>('')

// === ЛОГИКА ГЛОБАЛЬНОГО ПОИСКА С ПАГИНАЦИЕЙ ===

const displayLimit = ref(30)

// Сбрасываем лимит до 30, если пользователь начал печатать новый запрос
watch(searchQuery, () => {
  displayLimit.value = 30
})

// 1. Плоский массив с индексом нижнего регистра (работает быстро)
const allGroupsFlattened = computed(() => {
  const all: any[] = []
  for (const inst of apiInstitutes.value) {
    for (const g of inst.groups) {
      all.push({ 
        ...g, 
        institute: inst,
        _searchName: g.name.toLowerCase() 
      })
    }
  }
  return all
})

// 2. Ищем ВСЕ совпадения (без обрезки)
const allFilteredGroups = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) return []
  return allGroupsFlattened.value.filter(g => g._searchName.includes(query))
})

// 3. Отдаем в HTML только разрешенное количество (по умолчанию 30)
const searchResults = computed(() => {
  return allFilteredGroups.value.slice(0, displayLimit.value)
})

// === МАТЕМАТИКА ДЛЯ КНОПКИ "ЗАГРУЗИТЬ ЕЩЕ" ===

// Сколько групп еще осталось за кадром?
const remainingGroupsCount = computed(() => {
  return Math.max(0, allFilteredGroups.value.length - displayLimit.value)
})

// Сколько загрузим при следующем клике? (Минимум 30 или остаток)
const nextLoadCount = computed(() => {
  return Math.min(30, remainingGroupsCount.value)
})

// Функция подгрузки
const loadMoreGroups = () => {
  displayLimit.value += 30
}

// Красивое склонение слова "группа" для русского языка
const getGroupsWord = (count: number) => {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod100 >= 11 && mod100 <= 19) return 'групп'
  if (mod10 === 1) return 'группу'
  if (mod10 >= 2 && mod10 <= 4) return 'группы'
  return 'групп'
}
// === ЛОГИКА ШАГОВ (DRILL-DOWN) ===

const institutes = computed(() => {
  // Просто прокидываем данные для шаблона
  return apiInstitutes.value
})

const availableForms = computed(() => {
  if (!selectedInstitute.value) return []
  const inst = apiInstitutes.value.find(i => i.id === selectedInstitute.value.id)
  if (!inst) return []
  
  // Нормализуем формы (чтобы "Очная Форма Обучения (Дневная)" стала просто "Очная")
  const forms = inst.groups.map((g: any) => normalizeStudyForm(g.education_form))
  return [...new Set(forms)]
})

const availableCourses = computed(() => {
  if (!selectedInstitute.value || !selectedForm.value) return []
  const inst = apiInstitutes.value.find(i => i.id === selectedInstitute.value.id)
  
  // Оставляем только те группы, у которых нормализованная форма совпадает с выбранной
  const filtered = inst.groups.filter((g: any) => normalizeStudyForm(g.education_form) === selectedForm.value)
  const courses = filtered.map((g: any) => g.course)
  return [...new Set(courses)].sort()
})

const availableGroups = computed(() => {
  if (!selectedInstitute.value || !selectedForm.value || !selectedCourse.value) return []
  const inst = apiInstitutes.value.find(i => i.id === selectedInstitute.value.id)
  
  return inst.groups.filter((g: any) => 
    normalizeStudyForm(g.education_form) === selectedForm.value && g.course === selectedCourse.value
  ).sort((a: any, b: any) => a.name.localeCompare(b.name))
})

// === ОБРАБОТЧИКИ КЛИКОВ ===

const onSelectInstitute = (inst: any) => {
  selectedInstitute.value = inst
  if (availableForms.value.length === 1) {
    selectedForm.value = availableForms.value[0] as string
    goToStep(3)
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
  // parentInstitute передается, если мы кликнули из глобального поиска
  const inst = parentInstitute || apiInstitutes.value.find(i => i.id === selectedInstitute.value.id)
  
  const groupDataToSave = {
    group_id: group.id,
    group_name: group.name,
    institute_full_name: inst.name,
    institute_short_name: inst.short_name,
    study_form: normalizeStudyForm(group.education_form),
    file_title: `${group.course} курс`,
    logo_url: inst.logo_url
  }
  
  store.setGroup(groupDataToSave)
  store.addToast(`Группа ${group.name} успешно выбрана!`, 'success')
  
  // МАГИЯ ОЧИСТКИ ИСТОРИИ БРАУЗЕРА
  const depth = step.value - 1
  if (depth > 0) {
    router.go(-depth)
  } else {
    router.replace('/lessons')
  }
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

const stepTitle = computed(() => {
  if (step.value === 1) return searchQuery.value ? 'Поиск группы' : 'Институт'
  if (step.value === 2) return 'Форма обучения'
  if (step.value === 3) return 'Курс или программа'
  if (step.value === 4) return 'Группа'
})

const getGroupStyle = (name: string) => {
  const styles = [
    'bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-indigo-500/20 hover:border-indigo-500/40',
    'bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border-emerald-500/20 hover:border-emerald-500/40',
    'bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/20 hover:border-amber-500/40',
    'bg-gradient-to-br from-rose-500/10 to-pink-500/10 border-rose-500/20 hover:border-rose-500/40',
    'bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-cyan-500/20 hover:border-cyan-500/40',
    'bg-gradient-to-br from-fuchsia-500/10 to-purple-500/10 border-fuchsia-500/20 hover:border-fuchsia-500/40'
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return styles[Math.abs(hash) % styles.length]
}

const formatText = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}
</script>
<template>
  <div class="flex flex-col h-[100dvh] w-full bg-slate-950 px-6 pt-12 pb-8 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
    
    <!-- Шапка онбординга (Скрываем полностью, если есть ошибка сети) -->
    <div v-if="!fetchError" class="mb-6 relative shrink-0">
      <div class="h-8 mb-1 flex items-center">
        <Transition name="fade">
          <button v-if="step > 1 && !isLoading" @click="goBack" class="inline-flex items-center gap-1 text-slate-400 hover:text-white transition-colors p-1 -ml-1">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
            <span class="text-sm font-medium">Назад</span>
          </button>
        </Transition>
      </div>
      
        <!-- Анимированный заголовок ИЛИ его скелетон -->
      <!-- ДОБАВИЛИ type="transition", чтобы Vue игнорировал бесконечный animate-pulse -->
      <Transition name="fade-title" mode="out-in" type="transition">
        <div v-if="isLoading" class="h-9 w-48 bg-slate-800 rounded-lg animate-pulse mt-1"></div>
        <h1 v-else :key="stepTitle" class="text-3xl font-bold text-white tracking-tight leading-tight">
          {{ stepTitle }}
        </h1>
      </Transition>
    </div>

    <!-- Область контента -->
    <Transition name="slide" mode="out-in">
      
      <!-- === ШАГ 1: ВЫБОР ИНСТИТУТА === -->
      <div v-if="step === 1" class="flex flex-col gap-4 flex-1">
        
        <!-- СОСТОЯНИЕ 1: ЗАГРУЗКА (Скелетоны) -->
        <template v-if="isLoading">
          <!-- Фейковый инпут -->
          <div class="w-full h-[52px] bg-slate-900/60 border border-slate-800 rounded-2xl animate-pulse"></div>
          
          <div class="flex flex-col gap-3 mt-1">
            <!-- Фейковые институты (5 штук) -->
            <div v-for="i in 5" :key="i" class="flex items-center gap-4 bg-slate-900/40 border border-slate-800/50 p-4 rounded-2xl animate-pulse">
              <div class="w-12 h-12 rounded-xl bg-slate-800/80 shrink-0"></div>
              <div class="flex flex-col gap-2 w-full">
                <div class="h-3 w-1/4 bg-slate-800 rounded-md"></div>
                <div class="h-4 w-3/4 bg-slate-700/50 rounded-md"></div>
              </div>
            </div>
          </div>
        </template>

        <!-- СОСТОЯНИЕ 2: ОШИБКА -->
        <!-- flex-1 и justify-center отцентруют этот блок идеально посередине экрана -->
        <div v-else-if="fetchError" class="flex flex-col items-center justify-center py-12 px-4 text-center flex-1 h-full">
          <div class="w-16 h-16 bg-red-500/10 text-red-400 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </div>
          <h3 class="text-lg font-bold text-white mb-2">Сервер недоступен</h3>
          <p class="text-sm text-slate-400 mb-6">{{ fetchError }}</p>
          <!-- ИСПРАВЛЕНА КНОПКА: Теперь вызывает правильную функцию -->
          <button @click="loadInstitutes" class="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-colors active:scale-95">
            Повторить попытку
          </button>
        </div>

        <!-- СОСТОЯНИЕ 3: ДАННЫЕ ЗАГРУЖЕНЫ (Поиск и Список) -->
        <template v-else>
          <!-- Инпут поиска -->
          <div class="relative">
            <input 
              :value="searchQuery"
              @input="searchQuery = ($event.target as HTMLInputElement).value"
              type="text" 
              placeholder="Найти свою группу" 
              class="w-full bg-slate-900/60 border border-slate-800 rounded-2xl py-3.5 pl-12 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:bg-slate-900 transition-all shadow-sm"
            />
            <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1 rounded-full bg-slate-800/80 transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <!-- БЛОК С АНИМАЦИЕЙ ПЕРЕКЛЮЧЕНИЯ (Институты <-> Поиск) -->
          <Transition name="fade-switch" mode="out-in">
            
            <!-- Результаты поиска -->
            <div v-if="searchQuery" :key="'search-results'" class="flex flex-col gap-3">
              <Transition name="fade">
                <div v-if="searchResults.length === 0" class="flex flex-col items-center justify-center py-10 opacity-60">
                   <span class="text-3xl mb-2">🤔</span>
                   <span class="text-slate-400 text-sm">Группа не найдена</span>
                </div>
              </Transition>
              
              <TransitionGroup name="list" tag="div" class="flex flex-col gap-3">
                <button 
                  v-for="res in searchResults" :key="res.id"
                  @click="onSelectGroup(res, res.institute)"
                  class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left group"
                >
                  <div class="flex flex-col flex-1 min-w-0 pr-4">
                    <span class="text-lg font-bold text-white mb-1 group-hover:text-indigo-400 transition-colors truncate">{{ res.name }}</span>
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest truncate">{{ res.institute.short_name || res.institute.name }}</span>
                    <span class="text-[11px] text-slate-500 truncate mt-0.5">{{ res.course }} Курс</span>
                  </div>
                  <div class="px-2.5 py-1 bg-slate-800/80 border border-slate-700/50 rounded-lg shrink-0 mt-1">
                    <span class="text-[10px] font-bold text-slate-300 uppercase">Выбрать</span>
                  </div>
                </button>
              </TransitionGroup>
                <!-- === КНОПКА ЗАГРУЗИТЬ ЕЩЕ === -->
              <Transition name="fade">
                <button 
                  v-if="remainingGroupsCount > 0"
                  @click="loadMoreGroups"
                  class="mt-1 w-full py-4 flex items-center justify-center gap-2 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 rounded-2xl text-slate-300 text-sm font-bold transition-all active:scale-95"
                >
                  <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                  Загрузить еще {{ nextLoadCount }} {{ getGroupsWord(nextLoadCount) }}
                </button>
              </Transition>
            </div>

            <!-- Список институтов -->
            <div v-else :key="'institute-list'" class="flex flex-col gap-3">
              <button 
                v-for="inst in institutes" :key="inst.id"
                @click="onSelectInstitute(inst)"
                class="flex items-center gap-4 bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left"
              >
                <!-- Иконка -->
                <div class="w-12 h-12 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0 p-1.5">
                  <img v-if="inst.logo_url" :src="inst.logo_url" class="w-full h-full object-contain" alt="" />
                  <svg v-else class="w-6 h-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" /></svg>
                </div>
                
                <div class="flex flex-col flex-1 min-w-0 pr-2">
                  <span v-if="inst.short_name" class="text-[11px] text-indigo-400 font-bold uppercase tracking-widest">{{ inst.short_name }}</span>
                  <span class="text-sm font-semibold text-slate-200 uppercase leading-tight line-clamp-2 break-words" :class="!inst.short_name ? 'text-sm' : ''">{{ inst.name }}</span>
                </div>
                
                <svg class="w-5 h-5 text-slate-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>

          </Transition>
        </template>
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
