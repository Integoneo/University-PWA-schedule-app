// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { store } from '../store'
import Schedule from '../components/Schedule.vue'
import Onboarding from '../components/Onboarding.vue' // Сейчас создадим

const DummyExams = { template: '<div class="h-full flex items-center justify-center text-slate-500 font-medium pb-20">Экзамены (Скоро)</div>' }
const DummySearch = { template: '<div class="h-full flex items-center justify-center text-slate-500 font-medium pb-20">Поиск и Избранное</div>' }
const DummySettings = { template: '<div class="h-full flex items-center justify-center text-slate-500 font-medium pb-20">Настройки</div>' }

const routes = [
  { path: '/', redirect: '/lessons' },
  // meta: { hideNavbar: true } скажет нашему App.vue спрятать нижнее меню на этом экране
  { path: '/onboarding', name: 'Onboarding', component: Onboarding, meta: { hideNavbar: true } },
  { path: '/lessons', name: 'Schedule', component: Schedule },
  { path: '/exams', name: 'Exams', component: DummyExams },
  { path: '/search', name: 'Search', component: DummySearch },
  { path: '/settings', name: 'Settings', component: DummySettings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ГЛОБАЛЬНЫЙ GUARD: Проверяем каждый переход
router.beforeEach((to, from, next) => {
  // 1. Попытка вернуться на онбординг (случайный свайп назад), когда группа УЖЕ есть? -> Кидаем на расписание!
  if (to.path === '/onboarding' && store.groupInfo) {
    next('/lessons')
  } 
  // 2. Попытка зайти в расписание, когда группы НЕТ? -> Кидаем на выбор группы!
  else if (to.path !== '/onboarding' && !store.groupInfo) {
    next('/onboarding')
  } 
  // 3. Всё легально -> пускаем
  else {
    next()
  }
})

export default router
