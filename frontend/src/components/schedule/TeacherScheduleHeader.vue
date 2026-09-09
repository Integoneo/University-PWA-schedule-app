<script setup lang="ts">
/**
 * Шапка экрана расписания ПРЕПОДАВАТЕЛЯ.
 *
 * Верхняя строка: [иконка + имя препода] | [чётность] [обновить]
 * Нижняя строка:  [Месяц]               | [🏠 Домой]
 *
 * Визуально идентична ScheduleHeader, кнопка «Домой» — всегда видна.
 */
const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

defineProps<{
  teacherName: string
  isEvenWeek: boolean
  isLoading: boolean
  selectedDate: Date
}>()

defineEmits<{
  refresh: []
  goHome: []
}>()
</script>

<template>
  <div class="px-4 pt-6 pb-2 flex flex-col gap-3">

    <!-- Верхняя строка: имя препода слева, бейджи справа -->
    <div class="flex items-start justify-between">

      <!-- Имя преподавателя (без кнопки-шторки — аналог кнопки группы) -->
      <div class="flex items-center gap-1.5 px-3 py-1.5 -ml-3 max-w-[55%]">
        <div class="w-5 h-5 rounded-md bg-accent-strong/20 border border-accent/30 flex items-center justify-center shrink-0 text-accent">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <span class="font-bold text-secondary tracking-wide text-sm truncate">{{ teacherName }}</span>
      </div>

      <!-- Правая часть: 👁️ бейдж + чётность + обновление -->
      <div class="flex items-center gap-2">
        <!-- Бейдж режима просмотра (всегда «глаз» для препода) -->
        <div class="flex items-center justify-center w-6 h-6 rounded-md bg-surface/50 border border-line text-xs shrink-0 shadow-sm">
          👁️
        </div>

        <div
          class="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border bg-surface/50"
          :class="isEvenWeek ? 'border-accent/20' : 'border-success/20'"
        >
          <div
            class="w-1.5 h-1.5 rounded-full shadow-[0_0_8px_currentColor]"
            :class="isEvenWeek ? 'bg-accent text-accent' : 'bg-success text-success'"
          ></div>
          <span class="text-xs font-semibold tracking-wide" :class="isEvenWeek ? 'text-accent' : 'text-success'">
            {{ isEvenWeek ? 'Четная' : 'Нечетная' }}
          </span>
        </div>

        <button
          @click="$emit('refresh')"
          :disabled="isLoading"
          class="p-1.5 rounded-lg border border-line bg-surface/50 text-muted transition-colors"
          :class="isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-raised hover:text-secondary active:scale-95'"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin text-accent': isLoading }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Нижняя строка: месяц + кнопка Домой -->
    <div class="flex items-end justify-between relative z-10">
      <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-br from-white to-muted bg-clip-text text-transparent capitalize mb-1">
        {{ monthNames[selectedDate.getMonth()] }}
      </h2>

      <!-- Кнопка «Домой» — всегда видна в режиме преподавателя -->
      <button
        @click="$emit('goHome')"
        class="flex items-center gap-1.5 px-3 py-1.5 mb-1 rounded-xl bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent active:scale-95 transition-all shadow-sm whitespace-nowrap"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        <span class="text-[10px] font-bold uppercase tracking-widest mt-0.5">Домой</span>
      </button>
    </div>

  </div>
</template>
