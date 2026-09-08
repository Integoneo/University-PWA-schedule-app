import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import { overlayManager } from './composables/useOverlayManager'

// Инициализируем менеджер оверлеев до монтирования приложения.
// Это гарантирует, что router.afterEach уже подписан когда Vue начнёт рендер.
overlayManager.init(router)

const app = createApp(App)
app.use(router)
app.mount('#app')
