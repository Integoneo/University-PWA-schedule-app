import { createRouter, createWebHistory } from 'vue-router'
import { store } from '../store'
import Welcome from '../components/Welcome.vue'
import Schedule from '../components/Schedule.vue'
import Onboarding from '../components/Onboarding.vue' 
import Settings from '../components/Settings.vue'
import Profile from '../components/Profile.vue'
import Search from '../components/Search.vue' 
import Exams from '../components/Exams.vue'
import Changelog from '../components/Changelog.vue'

const routes = [
  { path: '/', redirect: '/lessons' },
  { path: '/welcome', name: 'Welcome', component: Welcome, meta: { hideNavbar: true } },
  { path: '/onboarding', name: 'Onboarding', component: Onboarding, meta: { hideNavbar: true } },
  { path: '/lessons', name: 'Schedule', component: Schedule },
  { path: '/exams', name: 'Exams', component: Exams },
  { path: '/search', name: 'Search', component: Search },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/profile', name: 'Profile', component: Profile, meta: { hideNavbar: true } },
  { path: '/changelog', name: 'Changelog', component: Changelog, meta: { hideNavbar: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const hasGroup = !!store.groupInfo

  // Если группа ЕСТЬ, запрещаем идти на стартовые экраны (кидаем в расписание)
  if (hasGroup && (to.path === '/welcome' || to.path === '/onboarding')) {
    next('/lessons')
  } 
  // Если группы НЕТ, и мы пытаемся зайти куда-то кроме стартовых экранов -> кидаем на Welcome
  else if (!hasGroup && to.path !== '/welcome' && to.path !== '/onboarding') {
    next('/welcome')
  } 
  // Иначе пропускаем
  else {
    next()
  }
})

export default router
