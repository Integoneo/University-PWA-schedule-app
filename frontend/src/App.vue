<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

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
  <main class="h-[100dvh] w-screen overflow-hidden bg-slate-950 relative">
    
    <!-- Маршрутизатор с анимацией переходов -->
    <router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <!-- Ключ route.path заставляет Vue понимать, что это разные страницы -->
        <keep-alive>
          <component :is="Component" :key="route.path" />
        </keep-alive>
      </transition>
    </router-view>

    <!-- Стеклянный Navbar с защитой Safe Area -->
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
        <!-- Точку убрали, иконка теперь подпрыгивает чуть выше (-translate-y-1) -->
        <div v-html="tab.icon" class="mb-1 transition-transform duration-300" :class="route.path === tab.path ? '-translate-y-1 scale-110' : 'scale-100'"></div>
        <span class="text-[10px] font-semibold tracking-wide">{{ tab.name }}</span>
      </button>
    </nav>

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
</style>
