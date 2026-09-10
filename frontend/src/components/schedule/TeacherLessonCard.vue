<script setup lang="ts">
/**
 * Карточка пары в расписании ПРЕПОДАВАТЕЛЯ.
 *
 * Два режима использования:
 *
 * 1. ОДИНОЧНАЯ ПАРА (обычный режим)
 *    <TeacherLessonCard :lesson="l" :state="'future'" :timeLeft="0" />
 *    — вместо массива преподавателей показывает массив groups: string[]
 *
 * 2. КОНФЛИКТНЫЙ БЛОК (наслоение нескольких пар)
 *    <TeacherLessonCard :conflictLessons="[l1, l2]" />
 *    — оборачивает все пары в контейнер с красной обводкой
 *    — показывает бейдж «⚠️ НАСЛОЕНИЕ»
 *    — внутри — компактная карточка на каждую пару
 *
 * ТОЧКА РАСШИРЕНИЯ: LessonCard.vue для студентов — TeacherLessonCard.vue для преподавателей.
 */
const props = withDefaults(defineProps<{
  /** Одиночная пара (обычный режим). */
  lesson?: any
  /** Состояние пары для цветовой индикации. */
  state?: 'future' | 'past' | 'soon' | 'now'
  /** Минут до начала (для бейджа «Через N мин»). */
  timeLeft?: number
  /**
   * Конфликтная группа: передайте массив пересекающихся пар.
   * Когда задан — компонент переходит в конфликтный режим.
   */
  conflictLessons?: any[]
}>(), {
  state: 'future',
  timeLeft: 0,
})

// ── Утилиты ────────────────────────────────────────────────────────────────

const getBadgeColor = (type: string) => {
  if (!type) return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
  const t = type.toLowerCase()
  if (t.includes('лек')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (t.includes('пр'))  return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
  if (t.includes('лаб')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  if (t.includes('дист')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
  return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
}

const formatPlace = (place: string) => {
  if (!place) return { main: '', sub: '' }
  const match = place.match(/^(.*?)\s*(\(.*?\))$/)
  return match ? { main: match[1], sub: match[2] } : { main: place, sub: '' }
}
</script>

<template>

  <!-- ═══════════════════════════════════════════════════════════
       КОНФЛИКТНЫЙ БЛОК
       Используется когда несколько пар пересекаются по времени.
       ═══════════════════════════════════════════════════════════ -->
  <div
    v-if="conflictLessons && conflictLessons.length > 0"
    class="rounded-3xl border border-error overflow-hidden shadow-[0_0_20px_rgba(248,113,113,0.12)]"
    style="background: color-mix(in srgb, var(--error) 5%, transparent)"
  >

    <!-- Заголовок конфликтного блока -->
    <div class="flex items-center gap-2 px-4 py-2.5 border-b border-error/20">
      <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-error/15 border border-error/30">
        <svg class="w-3 h-3 text-error shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span class="text-[10px] font-bold uppercase tracking-widest text-error">Наслоение</span>
      </div>
      <span class="text-[11px] text-error/70 font-semibold">{{ conflictLessons.length }} пары пересекаются</span>
    </div>

    <!-- Компактная карточка для каждой конфликтной пары -->
    <div class="flex flex-col divide-y divide-error/10 px-3 py-2 gap-1">
      <div
        v-for="(cl, idx) in conflictLessons"
        :key="idx"
        class="flex gap-3 py-2.5"
      >
        <!-- Левая колонка: время -->
        <div class="w-14 flex flex-col items-center shrink-0 pt-0.5">
          <span class="text-sm font-bold text-error/80">{{ cl.start_time.slice(0, 5) }}</span>
          <span class="text-[11px] font-semibold text-error/50 mt-0.5">{{ cl.end_time.slice(0, 5) }}</span>
        </div>

        <!-- Правая колонка: инфо -->
        <div class="flex-1 min-w-0">
          <!-- Тип пары -->
          <div class="mb-1">
            <span
              class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide rounded border"
              :class="getBadgeColor(cl.type_of_lesson)"
            >{{ cl.type_of_lesson || 'Не указано' }}</span>
          </div>
          <!-- Название -->
          <p class="text-xs font-semibold text-secondary leading-snug break-words">{{ cl.lesson_name }}</p>
          <!-- Аудитория -->
          <div class="flex items-center gap-1 mt-1 text-[11px] text-muted">
            <svg class="w-3 h-3 opacity-60 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" />
            </svg>
            <span class="font-medium text-tertiary">{{ cl.classroom || 'Не указано' }}</span>
          </div>
          <!-- Группы -->
          <div v-if="cl.groups && cl.groups.length > 0" class="flex items-start gap-1 mt-1 text-[11px] text-muted">
            <svg class="w-3 h-3 opacity-60 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span class="leading-snug">{{ cl.groups.join(' · ') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>


  <!-- ═══════════════════════════════════════════════════════════
       ОДИНОЧНАЯ ПАРА
       Аналог LessonCard, но с groups[] вместо teachers[].
       ═══════════════════════════════════════════════════════════ -->
  <div
    v-else-if="lesson"
    class="relative flex rounded-3xl p-4 backdrop-blur-md transition-all duration-500"
    :class="{
      'bg-surface/80 border border-line/80 shadow-sm':                                         state === 'future',
      'bg-surface/40 border border-line/40 opacity-50 grayscale-[30%]':                        state === 'past',
      'bg-surface/90 border border-warning/30 shadow-[0_0_20px_rgba(245,158,11,0.08)]':        state === 'soon',
      'bg-surface/95 border border-accent/40 shadow-[0_0_25px_rgba(99,102,241,0.15)]':         state === 'now',
    }"
  >

    <!-- 1. ЛЕВАЯ КОЛОНКА (время) -->
    <div
      class="w-[4.5rem] flex flex-col items-center pr-3 border-r shrink-0"
      :class="state === 'now' ? 'border-accent/30' : (state === 'soon' ? 'border-warning/30' : 'border-line/50')"
    >
      <span
        class="text-base font-bold"
        :class="state === 'now' ? 'text-accent' : (state === 'soon' ? 'text-warning' : 'text-primary')"
      >
        {{ lesson.start_time.slice(0, 5) }}
      </span>
      <span class="text-[13px] font-semibold text-muted mt-0.5">{{ lesson.end_time.slice(0, 5) }}</span>
    </div>

    <!-- 2. ПРАВАЯ КОЛОНКА -->
    <div class="flex-1 pl-4 flex flex-col justify-center min-w-0">

      <!-- ВЕРХНИЙ РЯД (тип пары + статус) -->
      <div class="flex items-center mb-2">
        <span
          class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide rounded-md border"
          :class="getBadgeColor(lesson.type_of_lesson)"
        >
          {{ lesson.type_of_lesson || 'Не указано' }}
        </span>

        <div v-if="state === 'soon'" class="ml-auto flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-warning/10 border border-warning/20">
          <div class="w-1.5 h-1.5 rounded-full bg-warning animate-pulse"></div>
          <span class="text-[9px] font-bold uppercase tracking-wider text-warning">
            Через {{ timeLeft }} мин
          </span>
        </div>

        <div v-if="state === 'now'" class="ml-auto flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-accent/10 border border-accent/20">
          <div class="relative flex h-1.5 w-1.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-strong"></span>
          </div>
          <span class="text-[9px] font-bold uppercase tracking-wider text-accent">Идет сейчас</span>
        </div>
      </div>

      <!-- НАЗВАНИЕ ПАРЫ -->
      <h3 class="text-sm font-semibold leading-snug text-secondary break-words whitespace-normal">{{ lesson.lesson_name }}</h3>

      <!-- НИЖНИЙ РЯД (место + группы) -->
      <div class="mt-3 flex flex-col gap-2.5">

        <!-- Аудитория -->
        <div class="flex items-center text-xs text-muted">
          <div class="flex items-center shrink-0">
            <svg class="w-3.5 h-3.5 mr-1.5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" />
            </svg>
            <span class="font-medium text-tertiary">{{ lesson.classroom || 'Не указано' }}</span>
            <span class="mx-3 opacity-40">•</span>
          </div>
          <div class="flex flex-col text-[10px] leading-[1.35]">
            <span>{{ formatPlace(lesson.educational_place).main }}</span>
            <span v-if="formatPlace(lesson.educational_place).sub" class="opacity-70">{{ formatPlace(lesson.educational_place).sub }}</span>
          </div>
        </div>

        <!-- Группы (вместо преподавателей) -->
        <div v-if="lesson.groups && lesson.groups.length > 0" class="flex items-start text-xs text-muted">
          <svg class="w-3.5 h-3.5 mr-1.5 mt-0.5 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <!-- Показываем группы через разделитель -->
          <div class="flex flex-wrap gap-x-1.5 gap-y-0.5">
            <span
              v-for="group in lesson.groups"
              :key="group"
              class="font-medium truncate"
            >{{ group }}</span>
          </div>
        </div>

      </div>
    </div>
  </div>

</template>
