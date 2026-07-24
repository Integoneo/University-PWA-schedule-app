<script setup lang="ts">
import { useRouter } from 'vue-router'
import { store } from '../store'

const router = useRouter()

const goBack = () => {
  router.back()
}

const makePrimary = (group: any) => {
  store.setGroup(group)
  store.addToast(`Группа ${group.group_name} теперь основная`, 'success')
}

const removeFavorite = (group: any) => {
  store.toggleFavorite(group)
  store.addToast(`Удалено из избранного`, 'info')
}

// Вызов ГЛОБАЛЬНОЙ модалки для Сброса группы
const promptResetGroup = () => {
  store.showModal({
    title: 'Сменить основную группу?',
    message: 'Текущая группа будет удалена из памяти. Вам придется заново выбрать институт и курс.',
    confirmText: 'Сбросить',
    onConfirm: () => {
      store.clearGroup()
      router.replace('/onboarding')
    }
  })
}

// Вызов ГЛОБАЛЬНОЙ модалки для Очистки кэша
const promptClearCache = () => {
  store.showModal({
    title: 'Очистить кэш?',
    message: 'Это удалит все сохраненные офлайн-расписания. Приложение скачает их заново.',
    confirmText: 'Очистить',
    onConfirm: () => {
      store.addToast('Кэш расписаний успешно очищен', 'success')
    }
  })
}
</script>

<template>
  <div class="h-full w-full bg-slate-950 flex flex-col pt-12 pb-12 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
    
  <!-- Добавили скрытие скроллбара в главный div -->
    <!-- Идеальная шапка со стрелочкой "Назад" -->
    <div class="px-4 mb-6">
      <button @click="goBack" class="flex items-center gap-2 -ml-2 p-2 text-slate-400 hover:text-white transition-colors active:scale-95">
        <svg class="w-6 h-6 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg>
        <h1 class="text-2xl font-bold text-white tracking-tight">Профиль</h1>
      </button>
    </div>

    <div class="flex flex-col px-4 gap-6">

      <!-- БЛОК: ТЕКУЩАЯ ГРУППА -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-3xl p-5 flex flex-col gap-4">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-widest ml-1">Основная группа</span>
        
        <div class="flex items-center gap-4 bg-slate-950/50 p-4 rounded-2xl border border-slate-800/50">
          <div class="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-lg font-bold text-white leading-tight truncate">{{ store.groupInfo?.group_name || 'Не выбрана' }}</span>
            <span class="text-xs text-slate-400 mt-0.5 truncate">{{ store.groupInfo?.institute_short_name || store.groupInfo?.institute_full_name }}</span>
          </div>
        </div>

        <!-- Кнопка вызывает модалку -->
        <button @click="promptResetGroup" class="w-full py-3.5 mt-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-semibold rounded-xl transition-colors border border-red-500/20 active:scale-[0.98]">
          Сменить группу
        </button>
      </div>

      <!-- БЛОК: ИЗБРАННЫЕ ГРУППЫ -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-3xl p-5 flex flex-col gap-4">
        <span class="text-xs font-bold text-slate-500 uppercase tracking-widest ml-1">Избранное</span>
        
        <div v-if="store.favorites.length === 0" class="flex flex-col items-center justify-center py-6 opacity-50">
          <svg class="w-8 h-8 text-slate-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>
          <span class="text-xs text-slate-400 font-medium">Нет сохраненных групп</span>
        </div>

        <div v-else class="flex flex-col gap-3">
          <div v-for="fav in store.favorites" :key="fav.group_id" class="flex items-center justify-between bg-slate-950/50 p-3 rounded-2xl border border-slate-800/50">
            <div class="flex flex-col pl-2 min-w-0 pr-2">
              <span class="text-base font-bold text-white truncate">{{ fav.group_name }}</span>
              <span class="text-[10px] text-slate-500 truncate max-w-[150px]">{{ fav.institute_short_name || fav.institute_full_name }}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button @click="makePrimary(fav)" class="px-3 py-1.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-lg text-xs font-bold active:scale-95 transition-transform">Сделать осн.</button>
              <button @click="removeFavorite(fav)" class="p-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg active:scale-95 transition-transform"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
            </div>
          </div>
        </div>
      </div>

      <!-- БЛОК: СИСТЕМА -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-3xl p-2 flex flex-col">
        <!-- Кнопка вызывает модалку -->
        <button @click="promptClearCache" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-slate-800 text-slate-400"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></div>
            <span class="text-sm font-medium text-slate-200">Очистить кэш расписаний</span>
          </div>
        </button>
      </div>

    </div>

    <!-- === УНИВЕРСАЛЬНАЯ МОДАЛКА === -->
    <Teleport to="body">
      <Transition name="modal">
        <!-- Фон (блюр). @click здесь закроет модалку при клике вне окна -->
        <div v-if="isModalOpen" @click="closeModal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[200] flex items-center justify-center p-5 pointer-events-auto">
          
          <!-- Само окно. @click.stop запрещает закрытие при клике внутри окна -->
          <div @click.stop class="modal-box bg-slate-900 border border-slate-800 rounded-[2rem] p-6 w-full max-w-sm shadow-2xl flex flex-col gap-5">
            
            <div class="flex flex-col gap-2.5">
              <h3 class="text-xl font-bold text-white leading-tight">{{ modalConfig.title }}</h3>
              <p class="text-sm text-slate-400 leading-relaxed">{{ modalConfig.message }}</p>
            </div>
            
            <div class="flex gap-3 mt-2">
              <button @click="closeModal" class="flex-1 py-3.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors">
                Отмена
              </button>
              <button @click="modalConfig.action" class="flex-1 py-3.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-semibold border border-red-500/20 rounded-xl transition-colors">
                {{ modalConfig.confirmText }}
              </button>
            </div>
            
          </div>

        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* Анимация Модального окна (Фон + Само окно) */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-active .modal-box, .modal-leave-active .modal-box {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-box, .modal-leave-to .modal-box {
  transform: scale(0.95) translateY(15px);
}
</style>
