<script setup lang="ts">
/**
 * Оверлей первого запуска — подсказывает листать расписание свайпом или клавишами.
 * Показывается поверх ScheduleBody, скрывается при любом клике/тапе по нему.
 */
defineProps<{
  isTouchDevice: boolean
}>()

defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <div
    @click="$emit('dismiss')"
    class="absolute inset-0 z-40 flex items-center justify-center pt-32 bg-page/20 backdrop-blur-[2px] cursor-pointer touch-manipulation"
  >
    <div class="flex flex-col items-center bg-surface/95 backdrop-blur-md px-5 py-3.5 rounded-2xl border border-line-muted/60 shadow-xl pointer-events-auto active:scale-95 transition-transform text-center">

      <!-- Иконка руки для тач-устройств -->
      <svg v-if="isTouchDevice" class="w-8 h-8 text-accent animate-swipe-hand mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
      </svg>

      <!-- Иконка кнопок для десктопа (Стрелочки + WASD) -->
      <div v-else class="flex items-center gap-2 mb-2">
        <div class="flex gap-1 text-accent">
          <div class="w-6 h-6 flex items-center justify-center bg-raised border border-line-muted rounded-md text-xs font-bold shadow-sm">←</div>
          <div class="w-6 h-6 flex items-center justify-center bg-raised border border-line-muted rounded-md text-xs font-bold shadow-sm">→</div>
        </div>
        <span class="text-[10px] font-bold text-subtle uppercase tracking-widest">или</span>
        <div class="flex gap-1 text-accent">
          <div class="w-6 h-6 flex items-center justify-center bg-raised border border-line-muted rounded-md text-[11px] font-bold shadow-sm">A</div>
          <div class="w-6 h-6 flex items-center justify-center bg-raised border border-line-muted rounded-md text-[11px] font-bold shadow-sm">D</div>
        </div>
      </div>

      <span class="text-xs font-semibold text-primary tracking-wide">
        {{ isTouchDevice ? 'Свайпай дни' : 'Листай дни на клавиатуре' }}
      </span>
      <span class="text-[10px] text-muted mt-0.5">или нажми в любое место</span>
    </div>
  </div>
</template>

<style scoped>
@keyframes swipe-hand {
  0%   { transform: translateX(15px) rotate(5deg); }
  50%  { transform: translateX(-15px) rotate(-10deg); }
  100% { transform: translateX(15px) rotate(5deg); }
}
.animate-swipe-hand {
  animation: swipe-hand 2s ease-in-out infinite;
}
</style>
