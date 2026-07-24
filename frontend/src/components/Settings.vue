<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import BottomSheet from './BottomSheet.vue'
const router = useRouter()
const isAboutSheetOpen = ref(false)

const goToProfile = () => {
  router.push('/profile')
}
</script>

<template>
  <div class="h-full w-full bg-slate-950 flex flex-col pt-12 pb-24 overflow-y-auto">
    
    <!-- Заголовок -->
    <div class="px-6 mb-8">
      <h1 class="text-3xl font-bold text-white tracking-tight">Настройки</h1>
    </div>

    <div class="flex flex-col px-4 gap-4">
      
      <!-- Меню Настроек -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-3xl p-2 flex flex-col">
        
        <!-- Кнопка: Профиль -->
        <button @click="goToProfile" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">Профиль</span>
          </div>
          <svg class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>
        
        <div class="h-px w-full bg-slate-800/50 my-1"></div>

        <!-- Кнопка: О приложении (Открывает шторку) -->
        <button @click="isAboutSheetOpen = true" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-slate-800 text-slate-400 border border-slate-700/50">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">О приложении</span>
          </div>
        </button>
      </div>

    </div>

<!-- ВЫЗОВ УНИВЕРСАЛЬНОЙ ШТОРКИ -->
    <BottomSheet :is-open="isAboutSheetOpen" @close="isAboutSheetOpen = false">
      
      <!-- То, что засунуто в #header, станет зоной, за которую можно тянуть -->
      <template #header>
        <h2 class="text-2xl font-bold text-white mb-2">О приложении</h2>
      </template>
      
      <!-- Основной контент -->
      <span class="text-indigo-400 font-bold text-sm tracking-widest uppercase mb-6 block mt-2">Версия 1.0.0 Alpha</span>
      
      <p class="text-slate-400 text-sm leading-relaxed mb-6">
        Данное приложение разработано для удобного просмотра расписания. <br><br>
        <strong class="text-slate-200">Внимание:</strong> Приложение транслирует данные с официального сайта университета. Разработчик не несет ответственности за внезапные отмены пар, изменения в расписании или неточности со стороны деканата.
      </p>

      <button @click="isAboutSheetOpen = false" class="w-full py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition-colors active:scale-[0.98]">
        Понятно, закрыть
      </button>
    </BottomSheet>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1); }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
</style>
