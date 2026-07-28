<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import BottomSheet from './BottomSheet.vue'
import { store } from '../store'

const router = useRouter()

// Управление шторками
const isAboutSheetOpen = ref(false)
const isShareSheetOpen = ref(false)
const isDevSheetOpen = ref(false) 

const goToProfile = () => {
  router.push('/profile')
}

// === ЛОГИКА ШАРИНГА ===
const appUrl = 'https://kosyga.ru' 

const copyLink = async () => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(appUrl)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = appUrl
      textArea.style.position = "fixed"
      textArea.style.opacity = "0"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    store.addToast('Ссылка скопирована', 'success')
  } catch (err) {
    store.addToast('Ошибка копирования', 'error')
  }
}

const shareNative = async () => {
  if (navigator.share) {
    try {
      await navigator.share({
        title: 'Kosyga.Space',
        text: 'Удобное приложение расписания РГУ Косыгина!',
        url: appUrl
      })
    } catch (err) {
      // Игнорируем закрытие системной шторки
    }
  } else {
    store.addToast('Ваш браузер не поддерживает это действие', 'info')
  }
}


// === ЛОГИКА РАЗРАБОТЧИКА ===
const openTelegram = () => {
  window.open('https://t.me/integoneo', '_blank')
}

// Твой реальный номер телефона
const myPhoneNumber = '+7 977 964-91-99' 

const copyPhoneOnly = async () => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(myPhoneNumber)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = myPhoneNumber
      textArea.style.position = "fixed"
      textArea.style.opacity = "0"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    store.addToast('Номер скопирован', 'success')
  } catch (err) {
    store.addToast('Ошибка копирования', 'error')
  }
}
</script>

<template>
  <div class="h-full w-full bg-slate-950 flex flex-col pt-12 pb-24 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
    
    <!-- Заголовок -->
    <div class="px-6 mb-8">
      <h1 class="text-3xl font-bold text-white tracking-tight">Настройки</h1>
    </div>

    <div class="flex flex-col px-4 gap-6">
      
      <!-- ЕДИНОЕ МЕНЮ НАСТРОЕК -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-3xl p-2 flex flex-col">
        
        <!-- 1. Профиль и группы -->
        <button @click="goToProfile" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">Профиль и группы</span>
          </div>
          <svg class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>

        <div class="h-px w-full bg-slate-800/50 my-1"></div>

        <!-- 2. Поделиться с друзьями -->
        <button @click="isShareSheetOpen = true" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">Поделиться с друзьями</span>
          </div>
          <svg class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>
        
        <div class="h-px w-full bg-slate-800/50 my-1"></div>

        <!-- 3. О разработчике -->
        <button @click="isDevSheetOpen = true" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">О разработчике</span>
          </div>
          <svg class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>

        <div class="h-px w-full bg-slate-800/50 my-1"></div>

        <!-- 4. О приложении -->
        <button @click="isAboutSheetOpen = true" class="flex items-center justify-between p-4 hover:bg-slate-800/50 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="flex items-center gap-4">
            <div class="p-2.5 rounded-xl bg-slate-800 text-slate-400 border border-slate-700/50">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <span class="text-base font-semibold text-slate-200">О приложении</span>
          </div>
          <svg class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
        </button>

      </div>
    </div>

    <!-- === УНИВЕРСАЛЬНЫЕ ШТОРКИ === -->
    
<!-- 1. Шторка "О разработчике" -->
    <BottomSheet :is-open="isDevSheetOpen" @close="isDevSheetOpen = false">
      <template #header>
        <div class="flex items-center gap-4 mb-2 px-1">
          <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-black text-2xl shadow-lg shadow-indigo-500/20 shrink-0">
            i
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-[11px] text-slate-500 font-bold uppercase tracking-widest mb-0.5">Разработчик</span>
            <span class="text-xl font-bold text-white truncate">integoneo</span>
          </div>
        </div>
      </template>
      
      <div class="flex flex-col gap-5 mt-4">
        
        <!-- Написать в ТГ -->
        <button @click="openTelegram" class="w-full p-4 flex items-center gap-3 bg-[#2AABEE]/10 hover:bg-[#2AABEE]/20 border border-[#2AABEE]/20 rounded-2xl transition-colors text-left active:scale-[0.98]">
          <div class="p-2.5 rounded-full bg-[#2AABEE]/20 text-[#2AABEE] shrink-0">
            <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
          </div>
          <div class="flex flex-col pr-2">
            <span class="text-sm font-bold text-[#2AABEE] mb-0.5">Написать в Telegram</span>
            <span class="text-[11px] text-[#2AABEE]/70 leading-tight">Нашли баг или есть фидбек? Я на связи</span>
          </div>
        </button>
        
<div class="h-px w-full bg-slate-800/50"></div>

        <!-- БЛОК ДОНАТОВ -->
        <div class="flex flex-col gap-3">
          
          <div class="flex flex-col mb-1">
            <span class="text-lg font-bold text-white mb-1">Угостить латте ☕</span>
            <span class="text-[11px] text-slate-400 leading-snug">
              Перевод по номеру телефона (Сбербанк или Альфа-Банк). Любая поддержка помогает проекту жить и развиваться!
            </span>
          </div>

          <button @click="copyPhoneOnly" class="w-full py-4 flex items-center justify-center gap-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-bold rounded-2xl transition-colors active:scale-[0.98]">
            <svg class="w-5 h-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            Скопировать номер телефона
          </button>
          
        </div>
      </div>
    </BottomSheet>
    <!-- 2. Шторка "Поделиться" -->
    <BottomSheet :is-open="isShareSheetOpen" @close="isShareSheetOpen = false">
      <template #header>
        <div class="w-full text-center pb-2">
          <h2 class="text-2xl font-bold text-white">Поделиться</h2>
        </div>
      </template>
      
      <div class="flex flex-col items-center gap-6 mt-2">
        <!-- Статический локальный QR-код -->
        <div class="p-4 bg-white rounded-[2rem] shadow-2xl">
          <!-- Просто закинь свой QR в папку public с именем qr.png -->
          <img src="/qr.png" alt="QR Code" class="w-48 h-48 rounded-xl object-contain" />
        </div>
        
        <div class="text-center">
          <h3 class="text-lg font-bold text-white mb-1">Kosyga.Space</h3>
          <p class="text-sm text-slate-400 leading-snug">Пусть друзья наведут камеру,<br>чтобы открыть расписание</p>
        </div>

        <div class="w-full flex gap-3 mt-2">
           <button @click="copyLink" class="flex-1 py-3.5 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition-colors active:scale-[0.98] flex justify-center items-center gap-2 text-sm">
             <svg class="w-5 h-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
             Ссылка
           </button>
           <button @click="shareNative" class="flex-1 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-colors active:scale-[0.98] flex justify-center items-center gap-2 text-sm shadow-lg shadow-indigo-900/50">
             <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
             Отправить...
           </button>
        </div>
      </div>
    </BottomSheet>

<!-- 3. Шторка "О приложении" -->
    <BottomSheet :is-open="isAboutSheetOpen" @close="isAboutSheetOpen = false">
      <template #header>
        <h2 class="text-2xl font-bold text-white mb-2">О приложении</h2>
      </template>
      
      <span class="text-indigo-400 font-bold text-sm tracking-widest uppercase mb-5 block mt-2">Версия 1.0.0 Alpha</span>
      
      <div class="flex flex-col gap-4 mb-6">
        <p class="text-slate-400 text-sm leading-relaxed">
          Я разработал нативное стильное приложение для очень удобного и быстрого просмотра расписания. Приложение создавалось на чистом энтузиазме — так сказать, от студента для студентов!
        </p>

        <!-- Красивый блок дисклеймера из Welcome.vue -->
        <div class="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex gap-3">
          <span class="text-amber-500 text-lg shrink-0">⚠️</span>
          <p class="text-xs text-amber-500/80 leading-relaxed">
            <strong>Отказ от ответственности:</strong> Приложение является лишь удобным зеркалом и транслирует данные с официального сайта вуза. Я не могу влиять на внезапные отмены пар, переносы кабинетов или ошибки деканата.
          </p>
        </div>
      </div>

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
