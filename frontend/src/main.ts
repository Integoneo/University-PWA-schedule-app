import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router' // Добавили импорт

const app = createApp(App)
app.use(router) // Подключили роутер
app.mount('#app')
