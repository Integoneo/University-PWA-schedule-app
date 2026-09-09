import { ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../../store'
import { api } from '../../api'

/**
 * Composable: загрузка и хранение данных расписания.
 * Принимает внешний selectedDate (владелец — Schedule.vue) и обновляет его
 * после получения дат семестра с бэкенда.
 */
export function useScheduleData(options: { selectedDate: Ref<Date>; realToday: Date }) {
  const { selectedDate, realToday } = options
  const router = useRouter()

  // --- реактивные данные ---
  const isLoading = ref(true)
  const allLessons = ref<any[]>([])
  const isOffline = ref(false)
  const originalExcelUrl = ref<string | null>(null)

  // --- конфигурация семестра ---
  const semesterStartDate = ref(new Date('2026-08-31T00:00:00'))
  const anchorIsEven = ref(false)
  const educationStart = ref<Date | null>(null)
  const educationEnd = ref<Date | null>(null)

  // --- приватные переменные защиты от спама ---
  let lastManualFetch = 0
  let lastFetchStatus = 'actual'

  const fetchScheduleData = async (isManual = false) => {
    if (!store.currentViewingGroup) {
      router.push('/')
      return
    }

    // === ЗАЩИТА ОТ СПАМА ===
    if (isManual) {
      const now = Date.now()
      if (now - lastManualFetch < 5000) {
        isLoading.value = true
        await new Promise(res => setTimeout(res, 400))

        if (!navigator.onLine || isOffline.value || lastFetchStatus === 'offline' || lastFetchStatus === 'error') {
          const msg = allLessons.value.length > 0 ? 'Нет сети. Показана кэшированная версия' : 'Нет подключения к сети'
          store.addToast(msg, 'error')
        } else {
          store.addToast('Расписание актуально', 'success')
        }

        isLoading.value = false
        return
      }
      lastManualFetch = now
    }

    isLoading.value = true
    isOffline.value = false
    const startTime = Date.now()

    try {
      const config = await api.getConfig()
      if (config) {
        semesterStartDate.value = config.anchorDate
        anchorIsEven.value = config.isEven
      }

      const data = await api.getSchedule(store.currentViewingGroup.group_id)
      allLessons.value = data.lessons || []
      originalExcelUrl.value = data.view_url || null
      lastFetchStatus = data._meta?.status || 'actual'

      educationStart.value = data.start_education_date ? new Date(data.start_education_date) : null
      educationEnd.value = data.end_education_date ? new Date(data.end_education_date) : null

      // === ЛОГИКА ФОКУСИРОВКИ НА ДНЕ ===
      if (educationStart.value && educationEnd.value) {
        const todayTime = realToday.getTime()
        const startTimeSemester = educationStart.value.getTime()
        const endTimeSemester = educationEnd.value.getTime()

        if (todayTime > endTimeSemester) {
          selectedDate.value = new Date(educationEnd.value)
        } else if (todayTime < startTimeSemester) {
          selectedDate.value = new Date(educationStart.value)
        } else {
          if (!isManual) selectedDate.value = new Date(realToday)
        }
      } else {
        if (!isManual) selectedDate.value = new Date(realToday)
      }

      if (isManual) {
        const elapsed = Date.now() - startTime
        if (elapsed < 800) {
          await new Promise(res => setTimeout(res, 800 - elapsed))
        }
      }

      // === ЛОГИКА РАЗГОВОРЧИВОЙ КНОПКИ ===
      if (isManual) {
        if (lastFetchStatus === 'actual') {
          store.addToast('Расписание актуально', 'success')
        } else if (lastFetchStatus === 'updated') {
          store.addToast('Расписание обновлено', 'success')
        } else if (lastFetchStatus === 'offline') {
          store.addToast('Нет сети. Показана кэшированная версия', 'error')
        }
      }
    } catch {
      isOffline.value = true
      allLessons.value = []
      lastFetchStatus = 'error'

      if (isManual) {
        store.addToast('Нет подключения к сети', 'error')
      }
    } finally {
      isLoading.value = false
    }
  }

  // Отслеживаем смену просматриваемой группы из глобального поиска
  watch(() => store.currentViewingGroup, () => {
    fetchScheduleData(false)
  }, { deep: true })

  return {
    isLoading,
    allLessons,
    isOffline,
    originalExcelUrl,
    semesterStartDate,
    anchorIsEven,
    educationStart,
    educationEnd,
    fetchScheduleData,
  }
}
