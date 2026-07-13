// src/store.ts
import { reactive, watch } from 'vue'

// Пытаемся достать группу из кэша телефона при запуске
const savedGroup = localStorage.getItem('user_group')

export const store = reactive({
  // Если группа была сохранена, парсим её. Иначе null.
  groupInfo: savedGroup ? JSON.parse(savedGroup) : null,
  
  // Функция для сохранения новой группы (вызовем её после выбора)
  setGroup(groupData: any) {
    this.groupInfo = groupData
    localStorage.setItem('user_group', JSON.stringify(groupData))
  },

  // Функция для выхода (сброс группы)
  clearGroup() {
    this.groupInfo = null
    localStorage.removeItem('user_group')
  }
})
