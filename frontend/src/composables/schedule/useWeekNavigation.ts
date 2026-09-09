import { ref, computed } from 'vue'
import type { Ref } from 'vue'

/**
 * Composable: навигация по дням/неделям.
 *
 * Принимает selectedDate как внешний Ref и мутирует его при переключении дней.
 * Возвращает булево значение из onTouchEnd / onKeyDown чтобы вызывающий код
 * мог среагировать (например, закрыть гайд по свайпу).
 *
 * КЛЮЧ ДЛЯ ПЕРЕИСПОЛЬЗОВАНИЯ:
 * Расписание преподавателей создаст useTeacherScheduleData.ts и передаст тот же
 * selectedDate в этот же composable — навигация по дням полностью переиспользуется.
 */
export function useWeekNavigation(options: {
  selectedDate: Ref<Date>
  semesterStartDate: Ref<Date>
  anchorIsEven: Ref<boolean>
}) {
  const { selectedDate, semesterStartDate, anchorIsEven } = options

  const transitionName = ref('slide-left')
  const touchStartX = ref(0)
  const touchStartY = ref(0)
  const isTouchDevice = ref(true) // По умолчанию считаем мобилкой

  // --- вычисляемые свойства ---

  const isEvenWeek = computed(() => {
    const start = semesterStartDate.value.getTime()
    const current = selectedDate.value.getTime()
    const diffDays = Math.floor((current - start) / (24 * 60 * 60 * 1000))
    const diffWeeks = Math.floor(diffDays / 7)
    return anchorIsEven.value ? (diffWeeks % 2 === 0) : (diffWeeks % 2 !== 0)
  })

  const currentWeekDates = computed(() => {
    const dates: Date[] = []
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

  // --- методы навигации ---

  const selectDate = (date: Date) => {
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

  // --- обработчики событий ---

  const onTouchStart = (e: TouchEvent) => {
    touchStartX.value = e.changedTouches[0].screenX
    touchStartY.value = e.changedTouches[0].screenY
  }

  /**
   * Обрабатывает конец свайпа.
   * @returns true если свайп был засчитан и день переключён.
   */
  const onTouchEnd = (e: TouchEvent): boolean => {
    const deltaX = e.changedTouches[0].screenX - touchStartX.value
    const deltaY = e.changedTouches[0].screenY - touchStartY.value

    if (Math.abs(deltaY) > Math.abs(deltaX)) return false

    if (Math.abs(deltaX) > 40) {
      if (deltaX > 40) changeDay(-1)
      else changeDay(1)
      return true
    }
    return false
  }

  /**
   * Обрабатывает нажатие клавиш навигации.
   * @returns true если клавиша была навигационной и день переключён.
   */
  const onKeyDown = (e: KeyboardEvent): boolean => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return false

    const key = e.key.toLowerCase()

    if (key === 'arrowleft' || key === 'a' || key === 'ф') {
      changeDay(-1)
      return true
    } else if (key === 'arrowright' || key === 'd' || key === 'в') {
      changeDay(1)
      return true
    }
    return false
  }

  return {
    transitionName,
    isTouchDevice,
    isEvenWeek,
    currentWeekDates,
    selectDate,
    changeDay,
    onTouchStart,
    onTouchEnd,
    onKeyDown,
  }
}
