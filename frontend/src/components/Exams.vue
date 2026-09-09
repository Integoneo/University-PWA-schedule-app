<script setup lang="ts">
// Заглушка, здесь пока нет логики
</script>

<template>
  <div class="h-[100dvh] w-full bg-page flex flex-col items-center justify-center p-6 text-center pb-24 overflow-hidden relative">
    
    <div class="relative mb-8">
      <!-- Еле заметная медленная пульсация (Дыхание) -->
      <div class="absolute inset-0 bg-amber-500 rounded-full animate-slow-pulse blur-xl"></div>
      
      <!-- Круглая плашка с иконкой -->
      <div class="relative w-28 h-28 flex items-center justify-center bg-surface/80 border border-line rounded-full shadow-2xl backdrop-blur-md">
        <span class="text-5xl">🚧</span>
      </div>
    </div>
    
    <h2 class="text-2xl font-bold text-primary mb-3 tracking-tight">Экзамены в разработке</h2>
    <p class="text-muted text-sm leading-relaxed max-w-[280px]">
      Я уже активно работаю над этим разделом. Скоро добавлю сюда удобный и красивый просмотр расписания сессии!
    </p>
    
  </div>
</template>

<style scoped>
/* Кастомная анимация для очень мягкого дыхания */
@keyframes slow-pulse {
  0%, 100% { opacity: 0.25; transform: scale(1); }
  50% { opacity: 0.15; transform: scale(1.15); }
}
.animate-slow-pulse {
  animation: slow-pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
