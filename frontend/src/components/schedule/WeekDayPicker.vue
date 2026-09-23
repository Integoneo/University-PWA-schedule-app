<script setup lang="ts">
/**
 * 7-дневная полоска выбора дня.
 * Подсвечивает активный день скользящим индикатором,
 * показывает кнопку копирования когда есть пары.
 */
const shortDays = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

const props = defineProps<{
  selectedDate: Date
  currentWeekDates: Date[]
  showCopyButton: boolean
  today: Date
}>()

const emit = defineEmits<{
  selectDate: [date: Date]
  copy: []
}>()

const isSameDate = (d1: Date, d2: Date) =>
  d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate()

const isToday = (d: Date) => isSameDate(d, props.today)
</script>

<template>
  <div class="px-4 pt-2 pb-0 relative z-20 flex flex-col items-end">

    <div class="relative flex w-full bg-surface/60 rounded-2xl p-1 backdrop-blur-sm border border-line z-10">
      <!-- Скользящий активный индикатор -->
      <div
        class="absolute top-1 bottom-1 bg-accent-strong rounded-xl shadow-lg shadow-indigo-500/30 transition-transform duration-300 cubic-bezier(0.4, 0, 0.2, 1)"
        :style="{
          width: 'calc((100% - 8px) / 7)',
          transform: `translateX(calc(${selectedDate.getDay() === 0 ? 6 : selectedDate.getDay() - 1} * 100%))`,
        }"
      ></div>

      <button
        v-for="(date, index) in currentWeekDates"
        :key="index"
        @click="emit('selectDate', date)"
        class="relative z-10 flex-1 py-1.5 flex flex-col justify-center items-center transition-all duration-300 touch-manipulation rounded-xl overflow-hidden"
        :class="isSameDate(selectedDate, date) ? 'text-primary' : 'text-muted hover:text-tertiary'"
      >
      <!-- Подсветка сегодняшнего дня -->
        <div
          v-if="isToday(date)"
          class="absolute inset-0 pointer-events-none"
          style="background: radial-gradient(circle at center, var(--today-glow) 5%, transparent 76%);"
        ></div>
        <span class="relative z-10 text-[10px] font-medium uppercase tracking-wider mb-0.5">{{ shortDays[date.getDay()] }}</span>
        <span class="relative z-10 text-base font-bold leading-none">{{ date.getDate() }}</span>
      </button>
    </div>

    <!-- Кнопка копирования (видна только когда есть пары) -->
    <Transition name="fade">
      <div v-if="showCopyButton" class="w-full h-0 relative">
        <button
          @click="emit('copy')"
          class="
            absolute top-0 right-4 z-1 flex items-center gap-1 px-3
            -mt-2 pt-3 pb-1.5
            rounded-b-xl backdrop-blur-md transition-all active:scale-95
            bg-surface/40 border border-line/90 border-t-0 shadow-sm
            text-subtle hover:text-tertiary hover:bg-raised/60
          "
        >
          <svg class="w-4 h-4 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
