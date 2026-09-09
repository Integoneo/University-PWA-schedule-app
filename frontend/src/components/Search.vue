<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { api, normalizeStudyForm } from '../api'
import SearchResultList from './search/SearchResultList.vue'

const router = useRouter()

// ── Загрузка данных ────────────────────────────────────────────────────────
const isLoading = ref(true)
const fetchError = ref('')
const apiInstitutes = ref<any[]>([])
const apiTeachers = ref<{ id: number; name: string }[]>([])

const loadData = async () => {
  isLoading.value = true
  fetchError.value = ''
  try {
    // Грузим параллельно; если преподаватели не ответят — группы всё равно работают
    const [institutesResult, teachersResult] = await Promise.allSettled([
      api.getInstitutes(),
      api.getTeachers(),
    ])

    if (institutesResult.status === 'fulfilled') {
      apiInstitutes.value = institutesResult.value
    } else {
      fetchError.value = 'Не удалось загрузить данные для поиска.'
      store.addToast('Ошибка обновления базы групп', 'error')
    }

    if (teachersResult.status === 'fulfilled') {
      apiTeachers.value = teachersResult.value
    } else {
      console.warn('[Search] Teachers API unavailable:', (teachersResult as PromiseRejectedResult).reason)
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(loadData)

// ── Табы и свайп ──────────────────────────────────────────────────────────
const activeTab = ref<'groups' | 'teachers'>('groups')
let swipeStartX = 0
let swipeStartY = 0

const onSwipeStart = (e: TouchEvent) => {
  swipeStartX = e.changedTouches[0].screenX
  swipeStartY = e.changedTouches[0].screenY
}

const onSwipeEnd = (e: TouchEvent) => {
  const deltaX = e.changedTouches[0].screenX - swipeStartX
  const deltaY = e.changedTouches[0].screenY - swipeStartY

  // Реагируем только на явно горизонтальный свайп
  if (Math.abs(deltaX) <= Math.abs(deltaY) || Math.abs(deltaX) < 60) return

  if (deltaX < 0 && activeTab.value === 'groups') {
    activeTab.value = 'teachers'
  } else if (deltaX > 0 && activeTab.value === 'teachers') {
    activeTab.value = 'groups'
  }
}

// ── Поисковая строка ───────────────────────────────────────────────────────
const searchQuery = ref('')

// При изменении запроса сбрасываем пагинацию обеих вкладок
watch(searchQuery, () => {
  groupDisplayLimit.value = 30
  teacherDisplayLimit.value = 30
})

// ── Вкладка ГРУППЫ ────────────────────────────────────────────────────────
const allGroupsFlattened = computed(() => {
  const all: any[] = []
  for (const inst of apiInstitutes.value) {
    for (const g of inst.groups) {
      all.push({ ...g, institute: inst, _searchName: g.name.toLowerCase() })
    }
  }
  return all
})

const groupDisplayLimit = ref(30)

const filteredGroups = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return []
  return allGroupsFlattened.value.filter(g => g._searchName.includes(q))
})

const visibleGroups = computed(() => filteredGroups.value.slice(0, groupDisplayLimit.value))
const remainingGroupsCount = computed(() => Math.max(0, filteredGroups.value.length - groupDisplayLimit.value))
const nextGroupsCount = computed(() => Math.min(30, remainingGroupsCount.value))
const loadMoreGroups = () => { groupDisplayLimit.value += 30 }

const getGroupsWord = (count: number) => {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod100 >= 11 && mod100 <= 19) return 'групп'
  if (mod10 === 1) return 'группу'
  if (mod10 >= 2 && mod10 <= 4) return 'группы'
  return 'групп'
}

// ── Вкладка ПРЕПОДАВАТЕЛИ ─────────────────────────────────────────────────
const teacherDisplayLimit = ref(30)

const filteredTeachers = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return []
  return apiTeachers.value.filter(t => t.name.toLowerCase().includes(q))
})

const visibleTeachers = computed(() => filteredTeachers.value.slice(0, teacherDisplayLimit.value))
const remainingTeachersCount = computed(() => Math.max(0, filteredTeachers.value.length - teacherDisplayLimit.value))
const nextTeachersCount = computed(() => Math.min(30, remainingTeachersCount.value))
const loadMoreTeachers = () => { teacherDisplayLimit.value += 30 }

const getTeachersWord = (count: number) => {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod100 >= 11 && mod100 <= 19) return 'преподавателей'
  if (mod10 === 1) return 'преподавателя'
  if (mod10 >= 2 && mod10 <= 4) return 'преподавателя'
  return 'преподавателей'
}

// ── Обработчики выбора ────────────────────────────────────────────────────
const onSelectGroup = (group: any) => {
  const inst = group.institute
  const groupData = {
    group_id: group.id || group.group_id,
    group_name: group.name || group.group_name,
    institute_full_name: inst?.name || group.institute_full_name,
    institute_short_name: inst?.short_name || group.institute_short_name,
    study_form: group.education_form ? normalizeStudyForm(group.education_form) : group.study_form,
    file_title: group.course ? `${group.course} курс` : group.file_title,
    logo_url: inst?.logo_url || group.logo_url,
  }

  const isMain = store.groupInfo?.group_id === groupData.group_id
  const isFav = store.isFavorite(groupData.group_id)
  const context = isMain ? 'main' : (isFav ? 'favorite' : 'guest')

  if (context === 'main') {
    store.resetToMainGroup()
  } else {
    store.setViewingGroup(groupData, context)
  }
  router.push('/lessons')
}

const onSelectTeacher = (teacher: { id: number; name: string }) => {
  store.setViewingTeacher(teacher)
  router.push('/lessons')
}
</script>

<template>
  <div class="h-full w-full bg-page flex flex-col">

    <!-- СТАТИЧНАЯ ШАПКА -->
    <div class="pt-12 px-6 mb-4 shrink-0">
      <h1 class="text-3xl font-bold text-primary tracking-tight">Поиск</h1>
    </div>

    <div class="px-4 shrink-0 flex flex-col gap-3">

      <!-- Поисковый инпут -->
      <div class="relative">
        <input
          :value="searchQuery"
          @input="searchQuery = ($event.target as HTMLInputElement).value"
          type="text"
          :placeholder="activeTab === 'groups' ? 'Введите название группы...' : 'Введите фамилию преподавателя...'"
          class="w-full bg-surface/60 border border-line rounded-2xl py-3.5 pl-12 pr-10 text-primary placeholder-subtle focus:outline-none focus:border-accent/50 focus:bg-surface transition-all shadow-sm"
        />
        <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <button
          v-if="searchQuery"
          @click="searchQuery = ''"
          class="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-primary p-1 rounded-full bg-raised/80 transition-colors"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Табы -->
      <div class="relative flex bg-surface/60 rounded-2xl p-1 border border-line">
        <!-- Скользящий индикатор -->
        <div
          class="absolute top-1 bottom-1 w-[calc(50%-4px)] bg-accent-strong rounded-xl shadow-lg shadow-indigo-500/30 transition-transform duration-300"
          :style="{ transform: activeTab === 'groups' ? 'translateX(0%)' : 'translateX(calc(100% + 2px))' }"
        ></div>
        <button
          @click="activeTab = 'groups'"
          class="relative z-10 flex-1 py-2 text-xs font-bold uppercase tracking-widest transition-colors duration-300"
          :class="activeTab === 'groups' ? 'text-primary' : 'text-muted hover:text-tertiary'"
        >
          Группы
        </button>
        <button
          @click="activeTab = 'teachers'"
          class="relative z-10 flex-1 py-2 text-xs font-bold uppercase tracking-widest transition-colors duration-300"
          :class="activeTab === 'teachers' ? 'text-primary' : 'text-muted hover:text-tertiary'"
        >
          Преподаватели
        </button>
      </div>
    </div>

    <!-- ОСНОВНАЯ ОБЛАСТЬ (свайп между табами) -->
    <div
      class="flex-1 overflow-hidden relative mt-3"
      @touchstart="onSwipeStart"
      @touchend="onSwipeEnd"
    >

      <!-- Скелетон -->
      <div v-if="isLoading" class="absolute inset-0 px-4 flex flex-col gap-3 pt-1">
        <div v-for="i in 5" :key="i" class="flex items-center justify-between bg-surface/40 border border-line/50 p-4 rounded-2xl animate-pulse">
          <div class="flex flex-col gap-2 w-2/3">
            <div class="h-4 w-1/3 bg-raised/50 rounded-md"></div>
            <div class="h-3 w-1/2 bg-raised rounded-md"></div>
          </div>
        </div>
      </div>

      <!-- Ошибка -->
      <div v-else-if="fetchError" class="absolute inset-0 px-4 flex flex-col items-center justify-center text-center">
        <p class="text-sm text-muted mb-4">{{ fetchError }}</p>
        <button @click="loadData" class="px-5 py-2.5 bg-accent-strong text-primary font-bold rounded-xl text-xs active:scale-95 transition-all">
          Обновить
        </button>
      </div>

      <!-- Два скользящих контентных блока -->
      <div
        v-else
        class="flex h-full transition-transform duration-300 ease-out"
        :style="{ width: '200%', transform: activeTab === 'groups' ? 'translateX(0%)' : 'translateX(-50%)' }"
      >

        <!-- ═══════════════ ВКЛАДКА ГРУППЫ ═══════════════ -->
        <div class="w-1/2 h-full overflow-y-auto px-4 pb-28 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div class="flex flex-col gap-3 pt-1">

            <!-- Пустой запрос → избранное -->
            <template v-if="!searchQuery">
              <span class="text-xs font-bold text-subtle uppercase tracking-widest ml-1 mb-1 block">⭐ Избранные группы</span>

              <div v-if="store.favorites.length === 0" class="flex flex-col items-center justify-center py-16 bg-surface/20 border border-surface rounded-3xl opacity-50">
                <svg class="w-8 h-8 text-subtle mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
                <span class="text-xs text-muted font-medium">Здесь будут группы быстрого доступа</span>
              </div>

              <div v-else class="flex flex-col gap-3">
                <div
                  v-for="fav in store.favorites"
                  :key="fav.group_id"
                  @click="onSelectGroup(fav)"
                  class="flex items-center justify-between bg-surface/60 border border-line p-4 rounded-2xl hover:bg-raised/50 transition-all text-left group active:scale-[0.99] cursor-pointer"
                >
                  <div class="flex flex-col flex-1 min-w-0 pr-4">
                    <span class="text-lg font-bold text-primary mb-0.5 group-hover:text-accent transition-colors truncate">{{ fav.group_name }}</span>
                    <span class="text-[10px] font-bold text-subtle uppercase tracking-widest truncate">{{ fav.institute_short_name || fav.institute_full_name }}</span>
                  </div>
                  <div class="px-2.5 py-1.5 bg-accent/10 border border-accent/20 text-accent rounded-xl shrink-0 group-hover:bg-accent/20 transition-colors">
                    <span class="text-[10px] font-bold uppercase tracking-widest">К просмотру</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Активный поиск → результаты -->
            <SearchResultList
              v-else
              :visible-items="visibleGroups"
              :remaining-count="remainingGroupsCount"
              :next-load-label="`Показать ещё ${nextGroupsCount} ${getGroupsWord(nextGroupsCount)}`"
              empty-icon="🤔"
              empty-text="Группа с таким именем не найдена"
              @load-more="loadMoreGroups"
            >
              <template #default="{ item }">
                <div
                  @click="onSelectGroup(item)"
                  class="flex items-center justify-between bg-surface/60 border border-line p-4 rounded-2xl hover:bg-raised/80 transition-all text-left group active:scale-[0.99] cursor-pointer"
                >
                  <div class="flex flex-col flex-1 min-w-0 pr-4">
                    <span class="text-lg font-bold text-primary mb-0.5 group-hover:text-accent transition-colors truncate">{{ item.name }}</span>
                    <span class="text-[10px] font-bold text-muted uppercase tracking-widest truncate">{{ item.institute.short_name || item.institute.name }}</span>
                    <span class="text-[11px] text-subtle mt-0.5">{{ item.course }} курс • {{ normalizeStudyForm(item.education_form) }}</span>
                  </div>
                </div>
              </template>
            </SearchResultList>

          </div>
        </div>

        <!-- ═══════════════ ВКЛАДКА ПРЕПОДАВАТЕЛИ ═══════════════ -->
        <div class="w-1/2 h-full overflow-y-auto px-4 pb-28 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div class="flex flex-col gap-3 pt-1">

            <!-- Пустой запрос → заглушка избранного -->
            <template v-if="!searchQuery">
              <span class="text-xs font-bold text-subtle uppercase tracking-widest ml-1 mb-1 block">⭐ Избранные преподаватели</span>

              <div class="flex flex-col items-center justify-center py-16 bg-surface/20 border border-surface rounded-3xl opacity-50">
                <svg class="w-8 h-8 text-subtle mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span class="text-xs text-muted font-medium">Избранные преподаватели появятся здесь</span>
              </div>
            </template>

            <!-- Активный поиск → результаты -->
            <template v-else>
              <!-- Если API ещё не вернул данные -->
              <div v-if="apiTeachers.length === 0" class="flex flex-col items-center justify-center py-12 opacity-60">
                <span class="text-3xl mb-2">😕</span>
                <span class="text-muted text-sm">База преподавателей недоступна</span>
              </div>

              <SearchResultList
                v-else
                :visible-items="visibleTeachers"
                :remaining-count="remainingTeachersCount"
                :next-load-label="`Показать ещё ${nextTeachersCount} ${getTeachersWord(nextTeachersCount)}`"
                empty-icon="🤔"
                empty-text="Преподаватель с таким именем не найден"
                @load-more="loadMoreTeachers"
              >
                <template #default="{ item }">
                  <div
                    @click="onSelectTeacher(item)"
                    class="flex items-center justify-between bg-surface/60 border border-line p-4 rounded-2xl hover:bg-raised/80 transition-all text-left group active:scale-[0.99] cursor-pointer"
                  >
                    <div class="flex flex-col flex-1 min-w-0 pr-4">
                      <span class="text-lg font-bold text-primary mb-0.5 group-hover:text-accent transition-colors truncate">{{ item.name }}</span>
                    </div>
                    <div class="px-2.5 py-1.5 bg-accent/10 border border-accent/20 text-accent rounded-xl shrink-0 group-hover:bg-accent/20 transition-colors">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </template>
              </SearchResultList>
            </template>

          </div>
        </div>

      </div>
    </div>
  </div>
</template>
