import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      devOptions: {
        enabled: true, // Включает Service Worker в режиме разработки
        type: 'module'
      },
    manifest: {
        name: 'Kosyga.Space',
        short_name: 'Kosyga.Space',
        description: 'Система просмотра университетского расписания',
        theme_color: '#020617',
        background_color: '#020617',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/icons/android/launchericon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: '/icons/android/launchericon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
    }
    })
  ],
server: {
    allowedHosts: true,
    proxy: {
      // Перехватываем все запросы к API
      '/api/v1/client': {
        target: 'http://localhost:8000', // Твой FastAPI сервер
        changeOrigin: true,
      }
    }
  }
})
