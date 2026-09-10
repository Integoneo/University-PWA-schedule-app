<script setup lang="ts">
/**
 * Карточка одной пары.
 *
 * Чистый презентационный компонент — никаких emit'ов.
 * ТОЧКА РАСШИРЕНИЯ: для расписания преподавателей создаётся TeacherLessonCard.vue
 * с иной разметкой (список групп вместо списка преподов и т.п.)
 */
defineProps<{
  lesson: any
  state: 'future' | 'past' | 'soon' | 'now'
  timeLeft: number
}>()

const getBadgeColor = (type: string) => {
  if (!type) return 'bg-slate-500/10 text-slate-400 border-slate-500/20'
  const t = type.toLowerCase()
  if (t.includes('лек')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (t.includes('пр')) return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
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
  <div
    class="relative flex rounded-3xl p-4 backdrop-blur-md transition-all duration-500"
    :class="{
      'bg-surface/80 border border-line/80 shadow-sm': state === 'future',
      'bg-surface/40 border border-line/40 opacity-50 grayscale-[30%]': state === 'past',
      'bg-surface/90 border border-warning/30 shadow-[0_0_20px_rgba(245,158,11,0.08)]': state === 'soon',
      'bg-surface/95 border border-accent/40 shadow-[0_0_25px_rgba(99,102,241,0.15)]': state === 'now',
    }"
  >
    <!-- 1. ЛЕВАЯ КОЛОНКА -->
    <div
      class="w-[4.5rem] flex flex-col items-center pr-3 border-r shrink-0"
      :class="state === 'now' ? 'border-accent/30' : (state === 'soon' ? 'border-warning/30' : 'border-line/50')"
    >
      <span class="text-base font-bold" :class="state === 'now' ? 'text-accent' : (state === 'soon' ? 'text-warning' : 'text-primary')">
        {{ lesson.start_time.slice(0, 5) }}
      </span>
      <span class="text-[13px] font-semibold text-muted mt-0.5">{{ lesson.end_time.slice(0, 5) }}</span>

      <div class="mt-auto pt-2 w-full flex justify-center">
        <span class="text-[10px] uppercase font-bold tracking-widest text-tertiary bg-raised/80 border border-line-muted/50 px-1.5 py-0.5 rounded-md whitespace-nowrap">
          {{ lesson.number_of_lesson }} пара
        </span>
      </div>
    </div>

    <!-- 2. ПРАВАЯ КОЛОНКА -->
    <div class="flex-1 pl-4 flex flex-col justify-center min-w-0">

      <!-- ВЕРХНИЙ РЯД (Бейджи) -->
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

      <!-- НИЖНИЙ РЯД (Место и преподы) -->
      <div class="mt-3 flex flex-col gap-3">
        <div class="flex items-center text-xs text-muted mt-0.5">
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
        <div v-if="lesson.teachers && lesson.teachers.length > 0" class="flex items-start text-xs text-muted">
          <svg class="w-3.5 h-3.5 mr-1.5 mt-0.5 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <div class="flex flex-col gap-0.5">
            <span v-for="teacher in lesson.teachers" :key="teacher.id" class="truncate font-medium">{{ teacher.name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
