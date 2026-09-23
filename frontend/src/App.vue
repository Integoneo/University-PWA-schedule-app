<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { store } from './store'
import { api } from './api'
import { onMounted } from 'vue'
import Modal from './components/Modal.vue'
import ChangelogModal from './components/ChangelogModal.vue'
import { useRegisterSW } from 'virtual:pwa-register/vue'
import { overlayManager } from './composables/useOverlayManager'
import { useChangelogDetector } from './composables/useChangelogDetector'


const { needRefresh, updateServiceWorker } = useRegisterSW({
  // 1. РАЗВЕДЧИК (Ищет обновления)
  onRegistered(r) {
    if (r) {
      // Пока тестируешь, оставь 10 секунд. На проде вернёшь 60 * 60 * 1000
      setInterval(() => {
        r.update()
      }, 60 * 60 * 1000)
    }
  },

  // 2. ТРИГГЕР (Срабатывает, когда обнова найдена и скачана)
  onNeedRefresh() {
    // Ставим в глобальную очередь — покажется на любой вкладке,
    // но не на Welcome/Onboarding (blacklist в overlayManager)
    overlayManager.enqueue({
      id: 'pwa_update',
      type: 'banner',
      scope: 'global',
      delayBefore: 0,
      delayAfter: 0,
    })
  }
})

const applyUpdate = async () => {
  overlayManager.dismiss('pwa_update')
  await updateServiceWorker(true)
}

const closeUpdateBanner = () => {
  overlayManager.dismiss('pwa_update')
  needRefresh.value = false
}
const route = useRoute()
const router = useRouter()

const { check: checkChangelog } = useChangelogDetector()

onMounted(() => {
  // 0a. Применяем сохранённую тему до первого рендера (до любой другой логики)
  document.documentElement.setAttribute('data-theme', store.currentTheme)

  // 0. Проверяем новые версии и при необходимости ставим в очередь модалку
  checkChangelog()

  // 1. При старте пробуем отправить статистику установки (если это standalone/PWA)
  api.syncInstallStats()

  // 2. Слушаем событие успешной установки в Chrome / Android
  window.addEventListener('appinstalled', () => {
    localStorage.setItem('pwa_install_pending', 'true')
    api.syncInstallStats()
  })

  // 3. Слушаем появление интернета (если установка произошла в оффлайне)
  window.addEventListener('online', () => {
    api.syncInstallStats()
  })

  // 4. При перезапуске сбрасываем контекст на основную группу
  store.resetToMainGroup()

  // 5. Перехват браузерного баннера PWA установки
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    store.deferredPrompt = e
  })

  // 6. Слушаем событие возвращения в приложение
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      api.syncInstallStats()
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
</script>

<template>
  <main class="h-[100dvh] w-screen overflow-hidden bg-page relative">
    
    <router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <keep-alive>
          <component :is="Component" :key="route.path" />
        </keep-alive>
      </transition>
    </router-view>

    <nav 
      v-if="!route.meta.hideNavbar"
      class="absolute bottom-0 left-0 right-0 bg-page/75 backdrop-blur-2xl border-t border-line/60 rounded-t-3xl z-50 flex items-start justify-between px-6 pt-2"
      style="padding-bottom: env(safe-area-inset-bottom); height: calc(5rem + env(safe-area-inset-bottom));"
    >
      <button 
        v-for="tab in tabs" 
        :key="tab.path"
        @click="router.push(tab.path)"
        class="relative flex flex-col items-center justify-start h-full pt-2 transition-colors duration-300 touch-manipulation flex-1"
        :class="route.path === tab.path ? 'text-accent' : 'text-subtle hover:text-muted'"
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
              'bg-success/10 border border-success/20 text-success': toast.type === 'success',
              'bg-error/10 border border-error/20 text-error': toast.type === 'error',
              'bg-raised/80 border border-line-muted/50 text-primary': toast.type === 'info'
            }"
          >
            <svg v-if="toast.type === 'error'" class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-if="toast.type === 'success'" class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            <span class="text-sm font-semibold tracking-wide">{{ toast.message }}</span>
          </div>
        </TransitionGroup>
      </div>

    <!-- ПЛАШКА ОБНОВЛЕНИЯ PWA -->
    <Transition name="toast">
      <div 
        v-if="overlayManager.state.activeItem?.id === 'pwa_update'" 
        class="fixed bottom-24 left-4 right-4 z-[90] p-4 bg-surface/95 border border-accent/30 rounded-2xl shadow-2xl backdrop-blur-xl flex flex-col gap-3"
      >
        <div class="flex items-start gap-3">
          <div class="p-2 bg-accent/20 text-accent rounded-xl shrink-0">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-primary font-bold text-sm">Доступно обновление</span>
            <span class="text-xs text-muted leading-snug">Вышла новая версия Kosyga.Space. Обновите приложение, чтобы применить изменения.</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button @click="closeUpdateBanner" class="flex-1 py-2 text-xs font-semibold text-muted hover:text-primary bg-raised/60 rounded-xl transition-colors">
            Позже
          </button>
          <button @click="applyUpdate" class="flex-1 py-2 text-xs font-bold text-primary bg-accent-strong hover:bg-accent rounded-xl transition-colors shadow-lg shadow-indigo-900/50">
            Обновить сейчас
          </button>
        </div>
      </div>
    </Transition>
      <!-- УНИВЕРСАЛЬНАЯ МОДАЛКА -->
      <Modal />

      <!-- МОДАЛКА CHANGELOG (управляется через overlayManager) -->
      <ChangelogModal v-if="overlayManager.state.activeItem?.id === 'changelog'" />
    </Teleport>
  </main>
</template>

<style scoped>
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}

.page-fade-enter-from {
  opacity: 0;
  transform: scale(0.97);
}

.page-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

.toast-move,
.toast-enter-active, 
.toast-leave-active { 
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); 
}

.toast-enter-from { 
  opacity: 0; 
  transform: translateY(-20px) scale(0.95); 
}

.toast-leave-to { 
  opacity: 0; 
  transform: translateY(-20px) scale(0.95); 
}

.toast-leave-active {
  position: absolute;
}
</style>
