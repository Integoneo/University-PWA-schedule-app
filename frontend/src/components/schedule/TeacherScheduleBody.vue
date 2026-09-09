<script setup lang="ts">
import TeacherLessonCard from './TeacherLessonCard.vue'
import { parseTeacherTime } from '../../composables/schedule/useTeacherMath'
import type { LessonGroup } from '../../composables/schedule/useTeacherMath'

/**
 * Основная область контента расписания ПРЕПОДАВАТЕЛЯ.
 *
 * Принимает уже сгруппированные пары (LessonGroup[]) и массив окон (gaps[]).
 * Рендерит:
 *   — скелетон / офлайн / пустой день (аналогично студенческому)
 *   — окно между группами (если gaps[i] > 0)
 *   — конфликтный блок (если group.hasConflict)
 *   — одиночную карточку TeacherLessonCard
 */
const props = defineProps<{
  currentState: string
  lessonGroups: LessonGroup[]
  /** gaps[i] = минут перед группой i (0 для первой). */
  gaps: number[]
  selectedDate: Date
  currentMinutes: number
  realToday: Date
  transitionName: string
}>()

const emit = defineEmits<{
  touchstart: [e: TouchEvent]
  touchend: [e: TouchEvent]
  retry: []
}>()

// ── Вспомогательные функции ────────────────────────────────────────────────

const isSameDate = (d1: Date, d2: Date) =>
  d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate()

const isRealToday = (d: Date) => isSameDate(d, props.realToday)

const getLessonState = (lesson: any): 'future' | 'past' | 'soon' | 'now' => {
  if (!isRealToday(props.selectedDate)) return 'future'
  const start = parseTeacherTime(lesson.start_time)
  const end   = parseTeacherTime(lesson.end_time)
  const now   = props.currentMinutes
  if (now > end) return 'past'
  if (now >= start && now <= end) return 'now'
  if (start - now > 0 && start - now <= 20) return 'soon'
  return 'future'
}

const getTimeLeft = (lesson: any) => parseTeacherTime(lesson.start_time) - props.currentMinutes

/**
 * Форматирует количество минут в читаемый вид.
 * @example 90 → "1 ч 30 мин"   50 → "50 мин"   60 → "1 ч"
 */
const formatGap = (minutes: number): string => {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} мин`
  if (m === 0) return `${h} ч`
  return `${h} ч ${m} мин`
}
</script>

<template>
  <div
    class="flex-1 relative overflow-hidden"
    @touchstart="emit('touchstart', $event)"
    @touchend="emit('touchend', $event)"
  >
    <Transition :name="transitionName">
      <div
        :key="selectedDate.getTime()"
        class="absolute inset-0 px-4 py-4 overflow-y-auto pb-24 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] overscroll-y-contain [-webkit-overflow-scrolling:touch]"
      >

        <!-- СКЕЛЕТОН загрузки -->
        <div v-if="currentState === 'loading'" class="flex flex-col gap-4">
          <div v-for="i in 4" :key="'sk-' + i" class="relative flex rounded-3xl p-4 bg-surface/40 border border-line/40 shadow-sm animate-pulse">
            <div class="w-[4.5rem] flex flex-col items-center pr-3 border-r border-line/30 shrink-0 gap-2.5 pt-1 pb-1">
              <div class="h-4 w-11 bg-raised/50 rounded-md"></div>
              <div class="h-3 w-9 bg-raised/80 rounded-md"></div>
            </div>
            <div class="flex-1 pl-4 flex flex-col justify-center py-1 gap-3.5">
              <div class="h-3.5 w-16 bg-raised/40 rounded-md"></div>
              <div class="space-y-2">
                <div class="h-4 w-11/12 bg-raised/60 rounded-md"></div>
                <div class="h-4 w-2/3 bg-raised/40 rounded-md"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- ОФЛАЙН -->
        <div v-else-if="currentState === 'offline'" class="mt-12 flex flex-col items-center justify-center text-center space-y-4 px-4">
          <div class="w-20 h-20 rounded-full bg-error/10 border border-error/20 flex items-center justify-center text-error">
            <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18M9 9l3 3m0 0l3-3m-3 3v4" />
            </svg>
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-primary font-bold text-lg">Нет подключения</h3>
            <p class="text-muted text-sm">Расписание ещё не загружено, а интернета нет.</p>
          </div>
          <button @click="emit('retry')" class="mt-2 px-6 py-2.5 bg-raised hover:bg-raised/80 text-primary font-semibold rounded-xl border border-line-muted transition-colors active:scale-95">
            Обновить
          </button>
        </div>

        <!-- ПУСТОЙ ДЕНЬ -->
        <div v-else-if="currentState === 'empty'" class="mt-12 flex flex-col items-center justify-center text-center space-y-3 opacity-60">
          <div class="w-20 h-20 rounded-full bg-surface/50 border border-line flex items-center justify-center text-3xl">😴</div>
          <p class="text-muted text-sm font-medium">В этот день пар нет.</p>
        </div>

        <!-- СПИСОК ГРУПП ПАР -->
        <div v-else-if="currentState === 'lessons'" class="flex flex-col gap-4">
          <template v-for="(group, i) in lessonGroups" :key="i">

            <!-- Окно между группами (пропускаем нулевой и нулевые значения) -->
            <div
              v-if="gaps[i] > 0"
              class="flex items-center gap-3 px-1 -mb-1"
            >
              <div class="flex-1 border-t border-dashed border-line-muted/40"></div>
              <span class="text-[11px] font-semibold text-subtle whitespace-nowrap select-none">
                Окно: {{ formatGap(gaps[i]) }}
              </span>
              <div class="flex-1 border-t border-dashed border-line-muted/40"></div>
            </div>

            <!-- Конфликтный блок (наслоение) -->
            <TeacherLessonCard
              v-if="group.hasConflict"
              :conflictLessons="group.lessons"
            />

            <!-- Одиночная пара -->
            <TeacherLessonCard
              v-else
              :lesson="group.lessons[0]"
              :state="getLessonState(group.lessons[0])"
              :timeLeft="getTimeLeft(group.lessons[0])"
            />

          </template>
        </div>

      </div>
    </Transition>

    <!-- ГРАДИЕНТ СНИЗУ -->
    <div class="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-page via-page/90 to-transparent pointer-events-none z-30"></div>
  </div>
</template>

<style scoped>
/* === АНИМАЦИИ СМЕНЫ ДНЯ (идентичны ScheduleBody.vue) === */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1), transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-left-enter-from  { opacity: 0; transform: translateX(30px); }
.slide-left-leave-to    { opacity: 0; transform: translateX(-30px); }
.slide-right-enter-from { opacity: 0; transform: translateX(-30px); }
.slide-right-leave-to   { opacity: 0; transform: translateX(30px); }
</style>
