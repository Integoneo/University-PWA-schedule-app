// src/store.ts
import { reactive } from 'vue'

const savedGroup = localStorage.getItem('user_group')
const savedFavorites = localStorage.getItem('user_favorites')

export const store = reactive({
  // Текущая выбранная группа
  groupInfo: savedGroup ? JSON.parse(savedGroup) : null,
  
  // Массив избранных групп
  favorites: savedFavorites ? JSON.parse(savedFavorites) : [],
  
  // Установить основную группу
    setGroup(groupData: any) {
    this.groupInfo = groupData
    localStorage.setItem('user_group', JSON.stringify(groupData))
    
    // Исключаем новую основную группу из избранного (если она там была)
    this.favorites = this.favorites.filter((g: any) => g.group_id !== groupData.group_id)
    localStorage.setItem('user_favorites', JSON.stringify(this.favorites))
  },

  // Сбросить основную группу (для выхода)
  clearGroup() {
    this.groupInfo = null
    localStorage.removeItem('user_group')
  },

  // Добавить или удалить из избранного
  toggleFavorite(groupData: any) {
    // Проверяем, есть ли уже такая группа в избранном
    const index = this.favorites.findIndex((g: any) => g.group_id === groupData.group_id)
    
    if (index === -1) {
      // Если нет — добавляем
      this.favorites.push(groupData)
    } else {
      // Если есть — удаляем
      this.favorites.splice(index, 1)
    }
    
    // Сохраняем обновленный массив в память телефона
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
    
    // Защита от спама: если тостов уже 3, жестко выкидываем самый старый (первый в массиве)
    if (this.toasts.length >= 3) {
      this.toasts.shift()
    }
    
    this.toasts.push({ id, message, type })
    
    // Автоудаление
    setTimeout(() => {
      this.removeToast(id)
    }, 3000)
  },

  // Функция для удаления по клику
  removeToast(id: number) {
    this.toasts = this.toasts.filter(t => t.id !== id)
  },
// === ГЛОБАЛЬНОЕ МОДАЛЬНОЕ ОКНО ===
  modal: {
    isOpen: false,
    title: '',
    message: '',
    confirmText: '',
    onConfirm: () => {}
  },
  
  showModal(config: { title: string, message: string, confirmText: string, onConfirm: () => void }) {
    this.modal.title = config.title
    this.modal.message = config.message
    this.modal.confirmText = config.confirmText
    // Оборачиваем функцию пользователя, чтобы модалка сама закрывалась после клика
    this.modal.onConfirm = () => {
      config.onConfirm()
      this.closeModal()
    }
    this.modal.isOpen = true
  },
  
  closeModal() {
    this.modal.isOpen = false
  }
})


