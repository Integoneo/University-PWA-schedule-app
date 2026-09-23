<script setup lang="ts">
/**
 * Шапка экрана расписания.
 * Содержит: кнопку группы, бейдж контекста (🏠⭐👁️), индикатор чётности,
 * кнопку обновления, заголовок месяца, кнопки «Добавить» и «Домой».
 */
const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

defineProps<{
  groupInfo: any
  isEvenWeek: boolean
  viewContext: string
  isLoading: boolean
  selectedDate: Date
}>()

defineEmits<{
  openGroupSheet: []
  refresh: []
  addToFavorites: []
  goHome: []
}>()
</script>

<template>
  <div class="px-4 pt-6 pb-2 flex flex-col gap-3">
    <div class="flex items-start justify-between">

      <button
        @click="$emit('openGroupSheet')"
        class="flex items-center gap-1.5 px-3 py-1.5 -ml-3 rounded-xl hover:bg-surface/80 transition-colors max-w-[55%]"
      >
        <div class="w-5 h-5 rounded-md bg-accent-strong/20 border border-accent/30 flex items-center justify-center shrink-0 text-accent">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        </div>
        <span class="font-bold text-secondary tracking-wide text-sm truncate">{{ groupInfo.group_name }}</span>
        <svg class="w-3.5 h-3.5 text-subtle shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div class="flex items-center gap-2">
        <div class="flex items-center justify-center w-6 h-6 rounded-md bg-surface/50 border border-line text-xs shrink-0 shadow-sm">
          {{ viewContext === 'main' ? '🏠' : (viewContext === 'favorite' ? '⭐' : '👁️') }}
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

    <div class="flex items-end justify-between relative z-10">
      <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-br from-primary to-muted bg-clip-text text-transparent capitalize mb-1">
        {{ monthNames[selectedDate.getMonth()] }}
      </h2>

      <TransitionGroup
        name="action-btns"
        tag="div"
        class="flex items-center justify-end gap-2 mb-1 relative"
      >
        <button
          key="add"
          v-if="viewContext === 'guest'"
          @click="$emit('addToFavorites')"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-warning/10 hover:bg-warning/20 border border-warning/20 text-warning active:scale-95 transition-all shadow-sm whitespace-nowrap"
        >
          <span class="text-[10px] leading-none">⭐</span>
          <span class="text-[10px] font-bold uppercase tracking-widest mt-0.5">Добавить</span>
        </button>

        <button
          key="home"
          v-if="viewContext !== 'main'"
          @click="$emit('goHome')"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent active:scale-95 transition-all shadow-sm whitespace-nowrap"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span class="text-[10px] font-bold uppercase tracking-widest mt-0.5">Домой</span>
        </button>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
/* === АНИМАЦИЯ КНОПОК ШАПКИ (горизонтальная, без скачков высоты) === */
.action-btns-move,
.action-btns-enter-active,
.action-btns-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.action-btns-enter-from,
.action-btns-leave-to {
  opacity: 0;
  transform: scale(0.9) translateX(10px);
}
/* position: absolute вырывает кнопку из верстки при удалении */
.action-btns-leave-active {
  position: absolute;
}
</style>
