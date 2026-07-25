
const API_URL = import.meta.env.VITE_API_URL || 'http://192.168.31.233:8000/api/v1/client'

// === Утилиты для нормализации данных ===
export const normalizeStudyForm = (rawForm: string) => {
  if (!rawForm) return 'Неизвестно'
  const text = rawForm.toLowerCase()
  if (text.includes('очно-заоч') || text.includes('вечер')) return 'Очно-заочная'
  if (text.includes('заоч')) return 'Заочная'
  if (text.includes('очн') || text.includes('дневн')) return 'Очная'
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const api = {
  // 1. Конфиг (Запрашиваем при старте в App.vue)
  async getConfig() {
    try {
      const response = await fetch(`${API_URL}/config`)
      if (!response.ok) throw new Error('Ошибка получения конфига')
      const data = await response.json()
      
      // Бэкенд отдает строку "2026-03-23". Превращаем её в объект Date для UI
      return {
        anchorDate: new Date(data.semester_anchor_date),
        isEven: data.anchor_is_even
      }
    } catch (error) {
      console.error('API Config Error:', error)
      return null
    }
  },

  // 2. Институты и Группы
  async getInstitutes() {
    // В памяти браузера лежит кэш? Отдаем мгновенно.
    const cached = localStorage.getItem('api_institutes')
    if (cached) return JSON.parse(cached)

    try {
      const response = await fetch(`${API_URL}/institutes`)
      if (!response.ok) throw new Error('Ошибка загрузки институтов')
      
      const data = await response.json()
      localStorage.setItem('api_institutes', JSON.stringify(data))
      return data
    } catch (error) {
      console.error('API Institutes Error:', error)
      throw error
    }
  },

  // 3. Расписание группы
  async getSchedule(groupId: string | number) {
    try {
      const response = await fetch(`${API_URL}/groups/${groupId}/lessons`)
      
      // Обработка 404, если айдишника нет в базе
      if (response.status === 404) {
        throw new Error('Расписание для этой группы не найдено')
      }
      if (!response.ok) {
        throw new Error('Ошибка сервера при загрузке расписания')
      }
      
      return await response.json()
    } catch (error) {
      console.error(`API Schedule Error for group ${groupId}:`, error)
      throw error
    }
  },

  clearInstitutesCache() {
    localStorage.removeItem('api_institutes')
  }
}
