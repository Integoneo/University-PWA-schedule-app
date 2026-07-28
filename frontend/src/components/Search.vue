<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { api, normalizeStudyForm } from '../api'

const router = useRouter()

const isLoading = ref(true)
const fetchError = ref('')
const apiInstitutes = ref<any[]>([])
const searchQuery = ref('')
const displayLimit = ref(30)

// Загрузка структуры институтов для локального инкрементального поиска
const loadData = async () => {
  isLoading.value = true
  fetchError.value = ''
  try {
    apiInstitutes.value = await api.getInstitutes()
  } catch (err) {
    fetchError.value = 'Не удалось загрузить данные для поиска.'
    store.addToast('Ошибка обновления базы групп', 'error')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})

watch(searchQuery, () => {
  displayLimit.value = 30
})

// Преобразование древовидной структуры в плоский поисковый индекс
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

// Фильтрация: если строка пустая — показываем только избранные, если заполнена — ищем совпадения
const filteredGroups = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) return []
  return allGroupsFlattened.value.filter(g => g._searchName.includes(query))
})

const searchResults = computed(() => {
  return filteredGroups.value.slice(0, displayLimit.value)
})

const remainingGroupsCount = computed(() => {
  return Math.max(0, filteredGroups.value.length - displayLimit.value)
})

const nextLoadCount = computed(() => {
  return Math.min(30, remainingGroupsCount.value)
})

const loadMoreGroups = () => {
  displayLimit.value += 30
}

const getGroupsWord = (count: number) => {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod100 >= 11 && mod100 <= 19) return 'групп'
  if (mod10 === 1) return 'группу'
  if (mod10 >= 2 && mod10 <= 4) return 'группы'
  return 'групп'
}

// 🎯 Главный диспетчер клика по группе
const onSelectGroup = (group: any, isFavClick = false) => {
  const inst = group.institute

  const groupData = {
    group_id: group.id || group.group_id,
    group_name: group.name || group.group_name,
    institute_full_name: inst?.name || group.institute_full_name,
    institute_short_name: inst?.short_name || group.institute_short_name,
    study_form: group.education_form ? normalizeStudyForm(group.education_form) : group.study_form,
    file_title: group.course ? `${group.course} курс` : group.file_title,
    logo_url: inst?.logo_url || group.logo_url
  }

  // Если кликнули на саму карточку группы — ведем смотреть расписание
  if (!isFavClick) {
    const isMain = store.groupInfo?.group_id === groupData.group_id
    const isFav = store.isFavorite(groupData.group_id)
    
    // Определяем контекст просмотра
    const context = isMain ? 'main' : (isFav ? 'favorite' : 'guest')
    
    if (context === 'main') {
      store.resetToMainGroup()
    } else {
      store.setViewingGroup(groupData, context)
    }
    
    router.push('/lessons')
  }
}

// Переключение состояния избранного (звёздочка) прямо из поиска
const handleToggleFavorite = (group: any) => {
  const inst = group.institute
  const groupData = {
    group_id: group.id,
    group_name: group.name,
    institute_full_name: inst.name,
    institute_short_name: inst.short_name,
    study_form: normalizeStudyForm(group.education_form),
    file_title: `${group.course} курс`,
    logo_url: inst.logo_url
  }
  
  store.toggleFavorite(groupData)
  store.addToast(
    store.isFavorite(groupData.group_id) ? 'Добавлено в избранное' : 'Удалено из избранного', 
    'info'
  )
}
</script>

<template>
  <div class="h-full w-full bg-slate-950 flex flex-col pt-12 pb-24 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
    
    <!-- Заголовок экрана -->
    <div class="px-6 mb-6">
      <h1 class="text-3xl font-bold text-white tracking-tight">Поиск</h1>
    </div>

    <div class="flex flex-col px-4 gap-4 flex-1">
      
      <!-- Поисковый инпут (Стиль Onboarding) -->
      <div class="relative shrink-0">
        <input 
          :value="searchQuery"
          @input="searchQuery = ($event.target as HTMLInputElement).value"
          type="text" 
          placeholder="Введите название группы..." 
          class="w-full bg-slate-900/60 border border-slate-800 rounded-2xl py-3.5 pl-12 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:bg-slate-900 transition-all shadow-sm"
        />
        <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1 rounded-full bg-slate-800/80 transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Скелетон загрузки индексов -->
      <div v-if="isLoading" class="flex flex-col gap-3 mt-1">
        <div v-for="i in 4" :key="i" class="flex items-center justify-between bg-slate-900/40 border border-slate-800/50 p-4 rounded-2xl animate-pulse">
          <div class="flex flex-col gap-2 w-2/3">
            <div class="h-4 w-1/3 bg-slate-700/50 rounded-md"></div>
            <div class="h-3 w-1/2 bg-slate-800 rounded-md"></div>
          </div>
        </div>
      </div>

      <!-- Ошибка подгрузки индексов -->
      <div v-else-if="fetchError" class="flex flex-col items-center justify-center py-12 px-4 text-center flex-1">
        <p class="text-sm text-slate-400 mb-4">{{ fetchError }}</p>
        <button @click="loadData" class="px-5 py-2.5 bg-indigo-600 text-white font-bold rounded-xl text-xs active:scale-95 transition-all">
          Обновить
        </button>
      </div>

      <!-- ОСНОВНОЙ КОНТЕНТ -->
      <div v-else class="flex flex-col gap-3">
        
        <!-- Окна вывода при пустой строке: Показываем Избранное -->
        <div v-if="!searchQuery" class="flex flex-col gap-3">
          <span class="text-xs font-bold text-slate-500 uppercase tracking-widest ml-1 mb-1 block">⭐ Избранные группы</span>
          
          <div v-if="store.favorites.length === 0" class="flex flex-col items-center justify-center py-16 bg-slate-900/20 border border-slate-900 rounded-3xl opacity-50">
            <svg class="w-8 h-8 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>
            <span class="text-xs text-slate-400 font-medium">Здесь будут группы быстрого доступа</span>
          </div>

          <div v-else class="flex flex-col gap-3">
            <div 
              v-for="fav in store.favorites" 
              :key="fav.group_id"
              @click="onSelectGroup(fav, false)"
              class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/50 transition-all text-left group active:scale-[0.99] cursor-pointer"
            >
              <div class="flex flex-col flex-1 min-w-0 pr-4">
                <span class="text-lg font-bold text-white mb-0.5 group-hover:text-indigo-400 transition-colors truncate">{{ fav.group_name }}</span>
                <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest truncate">{{ fav.institute_short_name || fav.institute_full_name }}</span>
              </div>
              
              <!-- КНОПКА "К ПРОСМОТРУ" -->
              <div class="px-2.5 py-1.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl shrink-0 group-hover:bg-indigo-500/20 transition-colors">
                <span class="text-[10px] font-bold uppercase tracking-widest">К просмотру</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Результаты активного поиска -->
        <div v-else class="flex flex-col gap-3">
          <div v-if="searchResults.length === 0" class="flex flex-col items-center justify-center py-12 opacity-60">
            <span class="text-3xl mb-2">🤔</span>
            <span class="text-slate-400 text-sm">Группа с таким именем не найдена</span>
          </div>
          
          <div v-else class="flex flex-col gap-3">
            <div 
              v-for="res in searchResults" 
              :key="res.id"
              @click="onSelectGroup(res, false)"
              class="flex items-center justify-between bg-slate-900/60 border border-slate-800 p-4 rounded-2xl hover:bg-slate-800/80 transition-all text-left group active:scale-[0.99] cursor-pointer"
            >
              <div class="flex flex-col flex-1 min-w-0 pr-4">
                <span class="text-lg font-bold text-white mb-0.5 group-hover:text-indigo-400 transition-colors truncate">{{ res.name }}</span>
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest truncate">{{ res.institute.short_name || res.institute.name }}</span>
                <span class="text-[11px] text-slate-500 mt-0.5">{{ res.course }} курс • {{ normalizeStudyForm(res.education_form) }}</span>
              </div>
            </div>
            
            <!-- Пагинация: Показать еще -->
            <button 
              v-if="remainingGroupsCount > 0"
              @click="loadMoreGroups"
              class="mt-1 w-full py-4 flex items-center justify-center gap-2 bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 rounded-2xl text-slate-300 text-sm font-bold transition-all active:scale-95"
            >
              <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
              Показать еще {{ nextLoadCount }} {{ getGroupsWord(nextLoadCount) }}
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
