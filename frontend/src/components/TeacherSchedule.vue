<script setup lang="ts">
/**
 * TeacherSchedule.vue — тонкий оркестратор расписания ПРЕПОДАВАТЕЛЯ.
 *
 * Рендерится ВНУТРИ Schedule.vue (не отдельный маршрут).
 * Учитель читается из store.currentViewingTeacher.
 * Кнопка «Домой» вызывает store.clearViewingTeacher() → Schedule.vue
 * переключается обратно на студенческое расписание.
 *
 * НЕ трогает overlayManager — очередь модалок остаётся в Schedule.vue.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { store } from '../store'
import { useTeacherScheduleData } from '../composables/schedule/useTeacherScheduleData'
import { useWeekNavigation } from '../composables/schedule/useWeekNavigation'
import { groupLessonsWithOverlaps, computeGaps } from '../composables/schedule/useTeacherMath'
import TeacherScheduleHeader from './schedule/TeacherScheduleHeader.vue'
import WeekDayPicker from './schedule/WeekDayPicker.vue'
import TeacherScheduleBody from './schedule/TeacherScheduleBody.vue'

// ── Данные преподавателя из store ─────────────────────────────────────────
// store.currentViewingTeacher гарантированно не null (Schedule.vue вызывает нас
// только при v-if="store.currentViewingTeacher")
const teacherId   = store.currentViewingTeacher!.id
const teacherName = store.currentViewingTeacher!.name

// ── Опорная дата ──────────────────────────────────────────────────────────
const realToday    = new Date()
const selectedDate = ref(new Date())

// ── Данные ───────────────────────────────────────────────────────────────
const {
  isLoading, allLessons, isOffline,
  semesterStartDate, anchorIsEven,
  fetchScheduleData,
} = useTeacherScheduleData({ teacherId, selectedDate, realToday })

// ── Навигация по неделям (переиспользуем без изменений) ──────────────────
const {
  transitionName, isTouchDevice,
  isEvenWeek, currentWeekDates,
  selectDate, onTouchStart, onTouchEnd, onKeyDown,
} = useWeekNavigation({ selectedDate, semesterStartDate, anchorIsEven })

// ── Текущие минуты (для индикаторов сейчас/скоро) ────────────────────────
const currentMinutes = ref(realToday.getHours() * 60 + realToday.getMinutes())
let tickTimer: ReturnType<typeof setInterval>

// ── Пары текущего дня → группировка → окна ───────────────────────────────
const currentLessons = computed(() => {
  const jsDay = selectedDate.value.getDay()           // 0 = Вс
  const apiDay = jsDay === 0 ? 6 : jsDay - 1          // API: Пн=0 … Вс=6
  return allLessons.value
    .filter(l => l.day_of_week === apiDay && l.is_even_week === isEvenWeek.value)
    .slice()
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
})

const lessonGroups = computed(() => groupLessonsWithOverlaps(currentLessons.value))
const gaps         = computed(() => computeGaps(lessonGroups.value))

// ── Состояние экрана ─────────────────────────────────────────────────────
const currentState = computed(() => {
  if (isLoading.value) return 'loading'
  if (isOffline.value && allLessons.value.length === 0) return 'offline'
  if (currentLessons.value.length === 0) return 'empty'
  return 'lessons'
})

// ── Жизненный цикл ───────────────────────────────────────────────────────
const handleKeyDown = (e: KeyboardEvent) => onKeyDown(e)

onMounted(() => {
  isTouchDevice.value = window.matchMedia('(pointer: coarse)').matches
  fetchScheduleData()
  window.addEventListener('keydown', handleKeyDown)
  tickTimer = setInterval(() => {
    const now = new Date()
    currentMinutes.value = now.getHours() * 60 + now.getMinutes()
  }, 10_000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  clearInterval(tickTimer)
})
</script>

<template>
  <!-- Нет собственной оболочки h-full: Schedule.vue уже предоставляет flex-col h-full -->
  <TeacherScheduleHeader
    :teacherName="teacherName"
    :isEvenWeek="isEvenWeek"
    :isLoading="isLoading"
    :selectedDate="selectedDate"
    @refresh="fetchScheduleData(true)"
    @goHome="store.clearViewingTeacher()"
  />

  <WeekDayPicker
    :selectedDate="selectedDate"
    :currentWeekDates="currentWeekDates"
    :today="realToday"
    :showCopyButton="false"
    @selectDate="selectDate"
    @copy="() => {}"
  />

  <TeacherScheduleBody
    :currentState="currentState"
    :lessonGroups="lessonGroups"
    :gaps="gaps"
    :selectedDate="selectedDate"
    :currentMinutes="currentMinutes"
    :realToday="realToday"
    :transitionName="transitionName"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd($event)"
    @retry="fetchScheduleData(true)"
  />
</template>
