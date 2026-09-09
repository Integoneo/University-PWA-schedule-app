<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'

const router = useRouter()

const startOnboarding = () => {
  router.push('/onboarding')
}

// Переменная для скрытия иконки
const isModernBrowser = ref(true)

onMounted(() => {
  const ua = navigator.userAgent
  // Ищем старые iOS (версии от 10 до 15) и старые десктопные Safari (до 16)
  const isOldIOS = /OS (1[0-5]|[1-9])_/.test(ua)
  const isOldMacSafari = /Version\/(1[0-5]|[1-9])\..*Safari/.test(ua) && !/Chrome/.test(ua)
  
  if (isOldIOS || isOldMacSafari) {
    isModernBrowser.value = false // Выпиливаем иконку из DOM
  }
})
</script>

<template>
  <div class="h-[100dvh] w-full bg-page flex flex-col justify-between p-5 sm:p-6 overflow-hidden relative">
    
    <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[120%] h-64 bg-indigo-600/20 blur-[100px] pointer-events-none rounded-full"></div>

    <div class="flex flex-col items-center mt-6 sm:mt-12 relative z-10 text-center">
      
      <!-- v-if полностью удалит этот узел из DOM-дерева на старых браузерах -->
      <div v-if="isModernBrowser" class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 p-0.5 shadow-2xl shadow-indigo-500/20 mb-4 sm:mb-6">
        <div class="w-full h-full bg-page rounded-[14px] flex items-center justify-center">
          <svg class="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
        </div>
      </div>
      
      <!-- Добавили pb-1, чтобы градиент не обрезал хвосты у букв "g" и "p" -->
      <h1 class="text-3xl sm:text-4xl font-black tracking-tight bg-gradient-to-br from-white to-muted bg-clip-text text-transparent mb-1 sm:mb-2 pb-1">
        Kosyga.Space
      </h1>
      <span class="text-[11px] sm:text-xs font-bold text-accent uppercase tracking-widest">
        Нативное приложение РГУ им. А.Н. Косыгина
      </span>
    </div>

    <div class="flex flex-col gap-3 sm:gap-5 relative z-10 mb-4 sm:mb-8">
      
      <div class="bg-surface/40 border border-line rounded-3xl p-4 sm:p-5 shadow-lg">
        <h3 class="text-primary font-bold text-base sm:text-lg mb-1.5 sm:mb-2">Привет! 👋</h3>
        <p class="text-muted text-xs sm:text-sm leading-relaxed">
           Я разработал нативное стильное приложение для очень удобного и быстрого просмотра расписания, приложение разрабатывалось на чистом энтузиазме, так сказать от студента для студентов
        </p>
      </div>

    <div v-if="isModernBrowser" class="bg-warning/10 border border-warning/20 rounded-3xl p-3.5 sm:p-4 flex gap-2.5 sm:gap-3">
        <span class="text-warning text-base sm:text-lg shrink-0">⚠️</span>
        <p class="text-[10px] sm:text-[11px] text-warning/80 leading-snug">
          <strong>Отказ от ответственности:</strong> Приложение является лишь удобным зеркалом и транслирует данные с официального сайта вуза. Я не могу влиять на внезапные отмены пар, переносы кабинетов или ошибки деканата.
        </p>
      </div>

    </div>

    <div class="mb-2 sm:mb-4 relative z-10 w-full">
      <button 
        @click="startOnboarding" 
        class="w-full py-3.5 sm:py-4 bg-accent-strong hover:bg-accent text-primary font-bold rounded-2xl transition-transform active:scale-95 shadow-xl shadow-indigo-900/50 flex items-center justify-center gap-2 text-sm sm:text-base"
      >
        Найти свою группу
        <svg class="w-5 h-5 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
      </button>
    </div>

  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
