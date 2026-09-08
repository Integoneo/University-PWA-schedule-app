import { reactive } from 'vue'

const savedGroup = localStorage.getItem('user_group')
const savedFavorites = localStorage.getItem('user_favorites')

const parsedGroup = savedGroup ? JSON.parse(savedGroup) : null

export const store = reactive({
  deferredPrompt: null as any,
  // 🏠 Основная группа (всегда сохраняется в localStorage)
  groupInfo: parsedGroup,
  
  // 📋 Группа, которую мы смотрим ПРЯМО СЕЙЧАС (по умолчанию — основная)
  currentViewingGroup: parsedGroup,

  // 🔄 Контекст текущего просмотра: 'main' | 'favorite' | 'guest'
  viewContext: 'main' as 'main' | 'favorite' | 'guest',
  
  // ⭐ Массив избранных групп
  favorites: savedFavorites ? JSON.parse(savedFavorites) : [] as any[],
  
  // Установить основную группу
  setGroup(groupData: any) {
    this.groupInfo = groupData
    localStorage.setItem('user_group', JSON.stringify(groupData))
    
    // Принудительно выставляем ее как текущую просматриваемую
    this.currentViewingGroup = groupData
    this.viewContext = 'main'
    
    // Исключаем новую основную группу из избранного (если она там была)
    this.favorites = this.favorites.filter((g: any) => g.group_id !== groupData.group_id)
    localStorage.setItem('user_favorites', JSON.stringify(this.favorites))
  },

  // Временное переключение контекста просмотра (вызывается из Поиска или Профиля)
  setViewingGroup(groupData: any, context: 'favorite' | 'guest') {
    this.currentViewingGroup = groupData
    this.viewContext = context
  },

  // Функция быстрого возврата на 🏠 Основную группу
  resetToMainGroup() {
    this.currentViewingGroup = this.groupInfo
    this.viewContext = 'main'
  },

  // Сбросить основную группу (для выхода)
  clearGroup() {
    this.groupInfo = null
    this.currentViewingGroup = null
    this.viewContext = 'main'
    localStorage.removeItem('user_group')
  },

  // Добавить или удалить из избранного
  toggleFavorite(groupData: any) {
    const index = this.favorites.findIndex((g: any) => g.group_id === groupData.group_id)
    if (index === -1) {
      this.favorites.push(groupData)
    } else {
      this.favorites.splice(index, 1)
      // Если удалили группу, которую прямо сейчас смотрели в качестве Избранной — мягко переключаем контекст на гостя или основную
      if (this.currentViewingGroup?.group_id === groupData.group_id && this.viewContext === 'favorite') {
        this.viewContext = 'guest'
      }
    }
    localStorage.setItem('user_favorites', JSON.stringify(this.favorites))
  },

  // Проверка, в избранном ли группа
  isFavorite(groupId: string | number) {
    return this.favorites.some((g: any) => g.group_id === groupId)
  },

  // === СИСТЕМА УВЕДОМЛЕНИЙ ===
  toasts: [] as Array<{ id: number, message: string, type: 'success' | 'error' | 'info' }>,
  
  addToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
    const id = Date.now()
    if (this.toasts.length >= 3) {
      this.toasts.shift()
    }
    this.toasts.push({ id, message, type })
    setTimeout(() => {
      this.removeToast(id)
    }, 3000)
  },

  removeToast(id: number) {
    this.toasts = this.toasts.filter(t => t.id !== id)
  },

// === УНИВЕРСАЛЬНАЯ МОДАЛКА ===
  modal: {
    isOpen: false,
    title: '',
    message: '',
    confirmText: '',
    type: 'danger' as 'danger' | 'primary',
    showCheckbox: false, // Показывать ли чекбокс
    checkboxText: '',
    checkboxValue: false, // Состояние галочки
    onConfirm: () => {},
    onCancel: () => {}
  },
  
  showModal(options: { 
    title: string, 
    message: string, 
    confirmText: string, 
    type?: 'danger' | 'primary', 
    showCheckbox?: boolean,
    checkboxText?: string,
    onConfirm: () => void,
    onCancel?: () => void 
  }) {
    this.modal.title = options.title
    this.modal.message = options.message
    this.modal.confirmText = options.confirmText
    this.modal.type = options.type || 'danger'
    
    // Настройки чекбокса
    this.modal.showCheckbox = options.showCheckbox || false
    this.modal.checkboxText = options.checkboxText || ''
    this.modal.checkboxValue = false // Сбрасываем галочку при новом открытии
    
    this.modal.onConfirm = () => {
      options.onConfirm()
      this.closeModal(false) // false означает, что закрыли НЕ через "Отмену"
    }
    this.modal.onCancel = options.onCancel || (() => {})
    this.modal.isOpen = true
  },
  
  closeModal(isCancel = true) {
    if (this.modal.isOpen && isCancel) {
      this.modal.onCancel()
    }
    this.modal.isOpen = false
  },


// === ОЧЕРЕДЬ УВЕДОМЛЕНИЙ (ДИРЕКТОР) ===
displayQueue: [] as Array<{ id: string; delayAfter: number }>,
activeEventId: null as string | null,
activeEventDelay: 1000,
isEventWaiting: false,
queueTimer: null as any,

enqueueEvent(id: string, delayAfter = 1000) {
  // Не дублируем, если уже в очереди или активно прямо сейчас
  if (this.displayQueue.some(e => e.id === id) || this.activeEventId === id) return
  
  this.displayQueue.push({ id, delayAfter })
  this.processQueue()
},

processQueue() {
  if (this.activeEventId || this.isEventWaiting || this.displayQueue.length === 0) return

  const nextEvent = this.displayQueue.shift()
  if (nextEvent) {
    this.activeEventId = nextEvent.id
    this.activeEventDelay = nextEvent.delayAfter
  }
},

finishEvent(id: string) {
  // Завершаем только если переданный ID совпадает с активным
  if (this.activeEventId === id) {
    const delay = this.activeEventDelay
    this.activeEventId = null
    this.isEventWaiting = true

    if (this.queueTimer) clearTimeout(this.queueTimer)

    this.queueTimer = setTimeout(() => {
      this.isEventWaiting = false
      this.processQueue()
    }, delay)
  }
},

// Аварийный сброс текущего события (например, при смене роута)
skipCurrentEvent() {
  if (this.activeEventId) {
    const current = this.activeEventId
    this.finishEvent(current)
  }
}
})
