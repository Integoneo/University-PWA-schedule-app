<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { store } from './store'
import { onMounted } from 'vue'
const route = useRoute()
const router = useRouter()
import Modal from './components/Modal.vue'

onMounted(() => {
  // При перезапуске сбрасываем контекст на основную группу
  store.resetToMainGroup()

  // ПЕРЕХВАТ PWA УСТАНОВКИ (Android / Chrome)
  window.addEventListener('beforeinstallprompt', (e) => {
    // Отменяем стандартный браузерный баннер
    e.preventDefault()
    // Сохраняем событие, чтобы вызвать его своей красивой модалкой позже
    store.deferredPrompt = e
  })
})

onMounted(() => {
  // Слушаем событие "возвращения" в приложение
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      // Когда юзер вернулся, даем WebView 100 миллисекунд на раздумья 
      // и принудительно имитируем изменение размера окна. 
      // Это заставит Android заново посчитать высоту экрана и вернуть навбар на место.
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'))
      }, 100)
    }
  })
})

const tabs = [
  {
    path: '/lessons',
    name: 'Расписание',
    icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>'
  },
  {
    path: '/exams',
    name: 'Экзамены',
    icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>'
  },
  {
    path: '/search',
    name: 'Поиск',
    icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>'
  },
  {
    path: '/settings',
    name: 'Настройки',
    icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>'
  }
]


onMounted(() => {
  // При перезапуске приложения сбрасываем контекст просмотра на 🏠 Основную группу
  store.resetToMainGroup()
})


window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  store.deferredPrompt = e
  // ВРЕМЕННЫЙ ТОСТ ДЛЯ ДИАГНОСТИКИ:
  store.addToast('Событие PWA поймано! Браузер готов к установке', 'success')
})
</script>

<template>
  <main class="h-[100dvh] w-screen overflow-hidden bg-slate-950 relative">
    
<router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <keep-alive>
          <component :is="Component" :key="route.path" />
        </keep-alive>
      </transition>
    </router-view>
    <nav 
      v-if="!route.meta.hideNavbar"
      class="absolute bottom-0 left-0 right-0 bg-slate-950/75 backdrop-blur-2xl border-t border-slate-800/60 rounded-t-3xl z-50 flex items-start justify-between px-6 pt-2"
      style="padding-bottom: env(safe-area-inset-bottom); height: calc(5rem + env(safe-area-inset-bottom));"
    >
      <button 
        v-for="tab in tabs" 
        :key="tab.path"
        @click="router.push(tab.path)"
        class="relative flex flex-col items-center justify-start h-full pt-2 transition-colors duration-300 touch-manipulation flex-1"
        :class="route.path === tab.path ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-400'"
      >
        <div v-html="tab.icon" class="mb-1 transition-transform duration-300" :class="route.path === tab.path ? '-translate-y-1 scale-110' : 'scale-100'"></div>
        <span class="text-[10px] font-semibold tracking-wide">{{ tab.name }}</span>
      </button>
    </nav>
<!-- ГЛОБАЛЬНЫЕ УВЕДОМЛЕНИЯ (TOASTS) -->
    <Teleport to="body">
      
<!-- ТОСТЫ -->
      <div class="fixed top-0 left-0 right-0 z-[100] flex flex-col items-center gap-2 px-4 pointer-events-none" style="padding-top: calc(env(safe-area-inset-top) + 16px);">
        <TransitionGroup name="toast">
          <div 
            v-for="toast in store.toasts" :key="toast.id"
            @click="store.removeToast(toast.id)"
            class="flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl pointer-events-auto backdrop-blur-md cursor-pointer hover:scale-[1.02] transition-transform"
            :class="{
              'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400': toast.type === 'success',
              'bg-red-500/10 border border-red-500/20 text-red-400': toast.type === 'error',
              'bg-slate-800/80 border border-slate-700/50 text-white': toast.type === 'info'
            }"
          >
            <svg v-if="toast.type === 'error'" class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-if="toast.type === 'success'" class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            <span class="text-sm font-semibold tracking-wide">{{ toast.message }}</span>
          </div>
        </TransitionGroup>
      </div>

      <!-- УНИВЕРСАЛЬНАЯ МОДАЛКА -->
       <Modal/> 
    </Teleport>
  </main>
</template>

<style scoped>
/* Анимация переключения вкладок Navbar */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}

/* Старт появления: прозрачность 0, масштаб чуть уменьшен (эффект "всплытия" из глубины) */
.page-fade-enter-from {
  opacity: 0;
  transform: scale(0.97);
}

/* Конец исчезновения: прозрачность 0, масштаб чуть уменьшен */
.page-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}
/* === Анимация Тостов === */

/* 1. Скорость и плавность. Поменяй 0.4s на 0.6s, чтобы сделать медленнее. 
   cubic-bezier(0.16, 1, 0.3, 1) — это "пружинистый" отскок как в iOS. */
.toast-move,
.toast-enter-active, 
.toast-leave-active { 
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); 
}

/* 2. Откуда тост появляется. Сейчас он вылетает сверху (-20px) и немного увеличен (scale 0.95) */
.toast-enter-from { 
  opacity: 0; 
  transform: translateY(-20px) scale(0.95); 
}

/* 3. Куда тост улетает. Если хочешь, чтобы он улетал вправо — напиши translateX(50px) */
.toast-leave-to { 
  opacity: 0; 
  transform: translateY(-20px) scale(0.95); 
}

/* 4. МАГИЯ VUE: Делает так, чтобы остальные тосты плавно подтягивались вверх, а не дергались */
.toast-leave-active {
  position: absolute;
}

/* Анимация Модального окна (Фон + Само окно) */
</style>
