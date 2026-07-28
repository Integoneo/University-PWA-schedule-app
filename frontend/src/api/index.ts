const API_URL = import.meta.env.VITE_API_URL || '/api/v1/client'

export const normalizeStudyForm = (rawForm: string) => {
  if (!rawForm) return 'Неизвестно'
  const text = rawForm.toLowerCase()
  if (text.includes('очно-заоч') || text.includes('вечер')) return 'Очно-заочная'
  if (text.includes('заоч')) return 'Заочная'
  if (text.includes('очн') || text.includes('дневн')) return 'Очная'
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const api = {
  // 1. Конфиг (С кэшированием)
  async getConfig() {
    const cached = localStorage.getItem('api_config')
    try {
      const response = await fetch(`${API_URL}/config`)
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

  // 2. Институты и Группы
  async getInstitutes() {
    const cached = localStorage.getItem('api_institutes')
    if (cached) return JSON.parse(cached)

    try {
      const response = await fetch(`${API_URL}/institutes`)
      if (!response.ok) throw new Error('Ошибка загрузки институтов')
      const data = await response.json()
      localStorage.setItem('api_institutes', JSON.stringify(data))
      return data
    } catch (error) {
      throw error
    }
  },

  // 3. Расписание группы (С МОЩНЫМ ОФФЛАЙН-КЭШЕМ)
async getSchedule(groupId: string | number) {
    const cacheKey = `api_schedule_${groupId}`
    const cached = localStorage.getItem(cacheKey)

    try {
      const response = await fetch(`${API_URL}/groups/${groupId}/lessons`)
      
      if (response.status === 404) throw new Error('404_NOT_FOUND')
      if (!response.ok) throw new Error('SERVER_ERROR')
      
      const data = await response.json()
      const newDataString = JSON.stringify(data)
      
      // Имитируем логику 304 для фронтенда: просто сверяем строки кэша
      const isUpdated = cached !== newDataString

      // Успешно скачали и данные реально новые? Сохраняем/обновляем в память!
      if (isUpdated) {
        localStorage.setItem(cacheKey, newDataString)
      }
      
      // Возвращаем данные, приклеив статус
      return {
        ...data,
        _meta: { status: isUpdated ? 'updated' : 'actual' }
      }
    } catch (error: any) {
      // МАГИЯ ОФФЛАЙНА
      if (cached && error.message !== '404_NOT_FOUND') {
        return {
          ...JSON.parse(cached),
          _meta: { status: 'offline' }
        }
      }
      throw error
    }
  },

  clearInstitutesCache() {
    localStorage.removeItem('api_institutes')
  }
}
