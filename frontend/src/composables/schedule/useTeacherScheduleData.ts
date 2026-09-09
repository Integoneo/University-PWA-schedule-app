import { ref } from 'vue'
import type { Ref } from 'vue'
import { api } from '../../api'
import { store } from '../../store'
import type { TeacherLesson } from './useTeacherMath'

/**
 * Composable: загрузка расписания преподавателя.
 *
 * Намеренно не использует useRouter и не трогает overlayManager —
 * эти побочные эффекты остаются в TeacherSchedule.vue.
 *
 * Отличия от useScheduleData:
 *   - teacher ID фиксирован (нет watch на store)
 *   - нет educationStart/educationEnd (API преподавателя их не возвращает)
 *   - при первой загрузке просто позиционируемся на сегодня
 */
export function useTeacherScheduleData(options: {
  teacherId: string | number
  selectedDate: Ref<Date>
  realToday: Date
}) {
  const { teacherId, selectedDate, realToday } = options

  // --- реактивные данные ---
  const isLoading = ref(true)
  const allLessons = ref<TeacherLesson[]>([])
  const isOffline = ref(false)

  // --- конфигурация семестра (нужна useWeekNavigation для вычисления чётности) ---
  const semesterStartDate = ref(new Date('2026-08-31T00:00:00'))
  const anchorIsEven = ref(false)

  // --- защита от спама ---
  let lastManualFetch = 0
  let lastFetchStatus = 'actual'

  const fetchScheduleData = async (isManual = false) => {
    // === ЗАЩИТА ОТ СПАМА ===
    if (isManual) {
      const now = Date.now()
      if (now - lastManualFetch < 5000) {
        isLoading.value = true
        await new Promise(res => setTimeout(res, 400))

        if (!navigator.onLine || isOffline.value || lastFetchStatus === 'offline' || lastFetchStatus === 'error') {
          const msg = allLessons.value.length > 0
            ? 'Нет сети. Показана кэшированная версия'
            : 'Нет подключения к сети'
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
      // Берём конфиг семестра (нужен для вычисления чётности через useWeekNavigation)
      const config = await api.getConfig()
      if (config) {
        semesterStartDate.value = config.anchorDate
        anchorIsEven.value = config.isEven
      }

      const data = await api.getTeacherSchedule(teacherId)
      allLessons.value = (data.lessons || []) as TeacherLesson[]
      lastFetchStatus = data._meta?.status || 'actual'

      // При первом запуске позиционируемся на сегодня
      if (!isManual) {
        selectedDate.value = new Date(realToday)
      }

      if (isManual) {
        const elapsed = Date.now() - startTime
        if (elapsed < 800) await new Promise(res => setTimeout(res, 800 - elapsed))

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

  return {
    isLoading,
    allLessons,
    isOffline,
    semesterStartDate,
    anchorIsEven,
    fetchScheduleData,
  }
}
