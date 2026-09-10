import { reactive } from 'vue'

// ─────────────────────────────────────────────────────────────────────────────
// ПРЕДОХРАНИТЕЛЬ КЭША
// Запускается один раз при инициализации модуля, ДО любого чтения localStorage.
//
// Логика:
//   • storedVersion отсутствует  → старый пользователь → только структурная валидация
//   • storedVersion совпадает    → нормальный запуск
//   • storedVersion не совпадает → плановый breaking change → сброс + новая версия
//   • Любая структурная ошибка   → сброс + новая версия
//
// При сбросе сохраняются: user_device_id и все api_* ключи.
// Редирект на /welcome выполняется автоматически через router.beforeEach,
// т.к. store.groupInfo окажется null.
// ─────────────────────────────────────────────────────────────────────────────

/** Увеличь при любом BREAKING CHANGE в структуре user_group / user_favorites */
const DATA_VERSION = '1'

function _clearUserData(): void {
  const toKeep = new Set(
    Object.keys(localStorage).filter(k => k.startsWith('api_') || k === 'user_device_id')
  )
  Object.keys(localStorage).forEach(k => {
    if (!toKeep.has(k)) localStorage.removeItem(k)
  })
}

;(function runCacheGuard(): void {
  const storedVersion = localStorage.getItem('app_data_version')

  // Плановый breaking change: версия изменилась — сброс
  if (storedVersion !== null && storedVersion !== DATA_VERSION) {
    _clearUserData()
    localStorage.setItem('app_data_version', DATA_VERSION)
    return
  }

  // Структурная валидация user_group
  const rawGroup = localStorage.getItem('user_group')
  if (rawGroup) {
    try {
      const g = JSON.parse(rawGroup)
      if (!g || typeof g !== 'object' || !('group_id' in g) || !('group_name' in g)) {
        throw new Error('invalid_group_structure')
      }
    } catch {
      // Битые или несовместимые данные → полный сброс
      _clearUserData()
      localStorage.setItem('app_data_version', DATA_VERSION)
      return
    }
  }

  // Структурная валидация user_favorites
  const rawFavs = localStorage.getItem('user_favorites')
  if (rawFavs) {
    try {
      if (!Array.isArray(JSON.parse(rawFavs))) throw new Error('invalid_favorites_structure')
    } catch {
      // Только избранное сломано — удаляем только его, не трогаем группу
      localStorage.removeItem('user_favorites')
    }
  }

  // Структурная валидация user_favorite_teachers
  const rawFavTeachers = localStorage.getItem('user_favorite_teachers')
  if (rawFavTeachers) {
    try {
      if (!Array.isArray(JSON.parse(rawFavTeachers))) throw new Error('invalid_fav_teachers_structure')
    } catch {
      localStorage.removeItem('user_favorite_teachers')
    }
  }

  // Всё валидно — фиксируем версию (для старых пользователей это первая запись)
  if (!storedVersion) {
    localStorage.setItem('app_data_version', DATA_VERSION)
  }
})()

// ─────────────────────────────────────────────────────────────────────────────

const savedGroup = localStorage.getItem('user_group')
const savedFavorites = localStorage.getItem('user_favorites')
const savedFavoriteTeachers = localStorage.getItem('user_favorite_teachers')

// После предохранителя гарантированно валидный JSON или null
const parsedGroup = savedGroup ? JSON.parse(savedGroup) : null

export const store = reactive({
  deferredPrompt: null as any,
  // 🏠 Основная группа (всегда сохраняется в localStorage)
  groupInfo: parsedGroup,
  
  // 📋 Группа, которую мы смотрим ПРЯМО СЕЙЧАС (по умолчанию — основная)
  currentViewingGroup: parsedGroup,

  // 🔄 Контекст текущего просмотра: 'main' | 'favorite' | 'guest'
  viewContext: 'main' as 'main' | 'favorite' | 'guest',

  // 👨‍🏫 Преподаватель, расписание которого сейчас открыто (null = студенческий режим)
  currentViewingTeacher: null as { id: number; name: string } | null,
  
  // ⭐ Массив избранных групп
  favorites: savedFavorites ? JSON.parse(savedFavorites) : [] as any[],

  // ⭐ Массив избранных преподавателей
  favoriteTeachers: savedFavoriteTeachers
    ? JSON.parse(savedFavoriteTeachers) as { id: number; name: string }[]
    : [] as { id: number; name: string }[],
  
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
    // Если был открыт режим преподавателя — закрываем его
    this.currentViewingTeacher = null
  },

  // Функция быстрого возврата на 🏠 Основную группу
  resetToMainGroup() {
    this.currentViewingGroup = this.groupInfo
    this.viewContext = 'main'
    // Если был открыт режим преподавателя — закрываем его
    this.currentViewingTeacher = null
  },

  // Открыть расписание преподавателя (переключает Schedule.vue в режим препода)
  setViewingTeacher(teacher: { id: number; name: string }) {
    this.currentViewingTeacher = teacher
  },

  // Закрыть расписание преподавателя, вернуться в студенческий режим
  clearViewingTeacher() {
    this.currentViewingTeacher = null
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

  // Добавить или удалить преподавателя из избранного
  toggleFavoriteTeacher(teacher: { id: number; name: string }) {
    const index = this.favoriteTeachers.findIndex(t => t.id === teacher.id)
    if (index === -1) {
      this.favoriteTeachers.push(teacher)
    } else {
      this.favoriteTeachers.splice(index, 1)
    }
    localStorage.setItem('user_favorite_teachers', JSON.stringify(this.favoriteTeachers))
  },

  // Проверка, в избранном ли преподаватель
  isFavoriteTeacher(teacherId: number) {
    return this.favoriteTeachers.some(t => t.id === teacherId)
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


})
