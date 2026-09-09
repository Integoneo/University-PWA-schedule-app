const API_URL = import.meta.env.VITE_API_URL || '/api/v1/client'

export const normalizeStudyForm = (rawForm: string) => {
  if (!rawForm) return 'Неизвестно'
  const text = rawForm.toLowerCase()
  if (text.includes('очно-заоч') || text.includes('вечер')) return 'Очно-заочная'
  if (text.includes('заоч')) return 'Заочная'
  if (text.includes('очн') || text.includes('дневн')) return 'Очная'
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// Вспомогательный метод для подстановки X-Device-ID ко всем клиентским запросам
const getHeaders = (extraHeaders: Record<string, string> = {}): Record<string, string> => {
  const headers: Record<string, string> = { ...extraHeaders }
  const deviceId = localStorage.getItem('user_device_id')
  if (deviceId) {
    headers['X-Device-ID'] = deviceId
  }
  return headers
}

// === СБОР ХАРАКТЕРИСТИК УСТРОЙСТВА С ФОЛЛБЭКАМИ ===
const getDeviceStatsPayload = () => {
  const width = Math.round(window.screen?.width || window.innerWidth || 390)
  const height = Math.round(window.screen?.height || window.innerHeight || 844)

  const rawRam = (navigator as any).deviceMemory
  const ram = rawRam && Number(rawRam) > 0 ? Math.round(Number(rawRam)) : 4

  const rawCpu = navigator.hardwareConcurrency
  const cpu = rawCpu && Number(rawCpu) > 0 ? Math.round(Number(rawCpu)) : 4

  return {
    screen_width: width,
    screen_height: height,
    device_ram_GB: ram,
    device_cpu_count: cpu
  }
}

let isInstallSyncing = false

export const api = {
  // 0. Отправка статистики установки PWA (БЕЗ X-Device-ID)
  async syncInstallStats() {
    if (localStorage.getItem('user_device_id')) {
      return
    }

    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone === true
    const isPending = localStorage.getItem('pwa_install_pending') === 'true'

    if (!isStandalone && !isPending) {
      return
    }

    localStorage.setItem('pwa_install_pending', 'true')

    const retryAfter = Number(localStorage.getItem('pwa_install_retry_after') || '0')
    if (Date.now() < retryAfter) {
      return
    }

    if (isInstallSyncing || !navigator.onLine) {
      return
    }

    isInstallSyncing = true

    try {
      const payload = getDeviceStatsPayload()
      const response = await fetch(`${API_URL}/stats/install`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      if (response.status === 429) {
        const retryHeader = response.headers.get('Retry-After')
        const delaySeconds = retryHeader ? parseInt(retryHeader, 10) || 60 : 60
        localStorage.setItem('pwa_install_retry_after', String(Date.now() + delaySeconds * 1000))
        setTimeout(() => {
          api.syncInstallStats()
        }, delaySeconds * 1000)
        return
      }

      if (!response.ok) {
        setTimeout(() => {
          api.syncInstallStats()
        }, 30000)
        return
      }

      const data = await response.json()
      if (data && data.device_id) {
        localStorage.setItem('user_device_id', data.device_id)
        localStorage.removeItem('pwa_install_pending')
        localStorage.removeItem('pwa_install_retry_after')
      }
    } catch {
      // Игнорируем сетевые сбои
    } finally {
      isInstallSyncing = false
    }
  },

  // 1. Конфиг (С кэшированием и X-Device-ID)
  async getConfig() {
    const cached = localStorage.getItem('api_config')
    try {
      const response = await fetch(`${API_URL}/config`, {
        headers: getHeaders()
      })
      if (!response.ok) throw new Error('Ошибка получения конфига')
      const data = await response.json()
      
      localStorage.setItem('api_config', JSON.stringify(data))
      return { anchorDate: new Date(data.semester_anchor_date), isEven: data.anchor_is_even }
    } catch (error) {
      if (cached) {
        const data = JSON.parse(cached)
        return { anchorDate: new Date(data.semester_anchor_date), isEven: data.anchor_is_even }
      }
      return null
    }
  },

  // 2. Институты и Группы (С УМНЫМ ОФФЛАЙНОМ и X-Device-ID)
  async getInstitutes() {
    const cached = localStorage.getItem('api_institutes')

    try {
      const response = await fetch(`${API_URL}/institutes`, {
        headers: getHeaders()
      })
      if (!response.ok) throw new Error('Ошибка загрузки институтов')
      
      const data = await response.json()
      const newDataString = JSON.stringify(data)

      if (cached !== newDataString) {
        localStorage.setItem('api_institutes', newDataString)
      }

      return data
    } catch (error) {
      if (cached) {
        return JSON.parse(cached)
      }
      throw error
    }
  },

  // 3. Расписание группы (С МОЩНЫМ ОФФЛАЙН-КЭШЕМ и X-Device-ID)
  async getSchedule(groupId: string | number) {
    const cacheKey = `api_schedule_${groupId}`
    const cached = localStorage.getItem(cacheKey)

    try {
      const response = await fetch(`${API_URL}/groups/${groupId}/lessons`, {
        headers: getHeaders()
      })
      
      if (response.status === 404) throw new Error('404_NOT_FOUND')
      if (!response.ok) throw new Error('SERVER_ERROR')
      
      const data = await response.json()
      const newDataString = JSON.stringify(data)
      
      const isUpdated = cached !== newDataString

      if (isUpdated) {
        localStorage.setItem(cacheKey, newDataString)
      }
      
      return {
        ...data,
        _meta: { status: isUpdated ? 'updated' : 'actual' }
      }
    } catch (error: any) {
      if (cached && error.message !== '404_NOT_FOUND') {
        return {
          ...JSON.parse(cached),
          _meta: { status: 'offline' }
        }
      }
      throw error
    }
  },

  // 4. Список преподавателей (с кешем и X-Device-ID)
  async getTeachers(): Promise<{ id: number; name: string }[]> {
    const cached = localStorage.getItem('api_teachers')
    try {
      const response = await fetch(`${API_URL}/teachers`, {
        headers: getHeaders()
      })
      if (!response.ok) throw new Error('Ошибка загрузки преподавателей')
      const data = await response.json()
      const newDataString = JSON.stringify(data)
      if (cached !== newDataString) {
        localStorage.setItem('api_teachers', newDataString)
      }
      return data as { id: number; name: string }[]
    } catch (error) {
      if (cached) return JSON.parse(cached) as { id: number; name: string }[]
      throw error
    }
  },

  clearInstitutesCache() {
    localStorage.removeItem('api_institutes')
  }
}
