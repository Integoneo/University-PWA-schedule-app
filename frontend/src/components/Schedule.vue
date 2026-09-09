<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useScheduleData } from '../composables/schedule/useScheduleData'
import { useWeekNavigation } from '../composables/schedule/useWeekNavigation'
import { overlayManager } from '../composables/useOverlayManager'
import { store } from '../store'
import ScheduleHeader from './schedule/ScheduleHeader.vue'
import WeekDayPicker from './schedule/WeekDayPicker.vue'
import ScheduleBody from './schedule/ScheduleBody.vue'
import GroupInfoSheet from './schedule/GroupInfoSheet.vue'
import ExcelModal from './schedule/ExcelModal.vue'
import TeacherSchedule from './TeacherSchedule.vue'

// ── Константы ──────────────────────────────────────────────────────────────
const realToday = new Date()
const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
const shortDays = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

// ── Общий Ref выбранной даты (передаётся в оба composable) ─────────────────
const selectedDate = ref(new Date())

// ── Composable: загрузка данных ────────────────────────────────────────────
const {
  isLoading, allLessons, isOffline, originalExcelUrl,
  semesterStartDate, anchorIsEven, educationStart, educationEnd,
  fetchScheduleData,
} = useScheduleData({ selectedDate, realToday })

// ── Composable: навигация по дням ──────────────────────────────────────────
const {
  transitionName, isTouchDevice, isEvenWeek, currentWeekDates,
  selectDate, onTouchStart, onTouchEnd, onKeyDown,
} = useWeekNavigation({ selectedDate, semesterStartDate, anchorIsEven })

// ── Состояние UI ───────────────────────────────────────────────────────────
const isGroupSheetOpen = ref(false)
const isExcelModalOpen = ref(false)
const currentMinutes = ref(new Date().getHours() * 60 + new Date().getMinutes())

// ── Computed: данные группы и даты семестра ────────────────────────────────
const groupInfo = computed(() => store.currentViewingGroup || {
  institute_full_name: 'Загрузка...',
  institute_short_name: null,
  study_form: '',
  file_title: '...',
  logo_url: '',
  group_name: '...',
  group_id: null,
})

const formattedSemesterDates = computed(() => {
  if (isLoading.value && !educationStart.value && !educationEnd.value) return 'Загрузка...'
  if (!educationStart.value || !educationEnd.value) return 'Не указано'
  const formatter = new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'long' })
  const start = formatter.format(educationStart.value)
  const end = formatter.format(educationEnd.value)
  const year = educationEnd.value.getFullYear()
  return `${start} — ${end} ${year}`
})

// ── Computed: машина состояний ─────────────────────────────────────────────
const semesterState = computed(() => {
  if (!educationStart.value || !educationEnd.value) return 'active'
  const current = selectedDate.value.getTime()
  const start = educationStart.value.getTime()
  const end = new Date(educationEnd.value)
  end.setHours(23, 59, 59, 999)
  if (current < start) return 'before'
  if (current > end.getTime()) return 'after'
  return 'active'
})

const currentLessons = computed(() => {
  if (semesterState.value !== 'active') return []
  const jsDay = selectedDate.value.getDay()
  const apiDay = jsDay === 0 ? 6 : jsDay - 1
  return allLessons.value
    .filter(l => l.day_of_week === apiDay && l.is_even_week === isEvenWeek.value)
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
})

const currentState = computed(() => {
  if (isLoading.value) return 'loading'
  if (isOffline.value) return 'offline'
  if (semesterState.value === 'before') return 'before'
  if (semesterState.value === 'after') return 'after'
  if (currentLessons.value.length === 0) return 'empty'
  return 'lessons'
})

// ── Логика гайда по свайпу ─────────────────────────────────────────────────
const completeSwipeGuide = () => {
  if (overlayManager.state.activeItem?.id === 'swipe_guide') {
    localStorage.setItem('has_seen_swipe_guide', 'true')
    overlayManager.dismiss('swipe_guide')
  }
}

const handleGuideCompletion = () => {
  if (overlayManager.state.activeItem?.id === 'swipe_guide') {
    completeSwipeGuide()
    store.addToast(
      isTouchDevice.value ? 'Отлично! Расписание листается свайпами' : 'Отлично! Можно листать кнопками',
      'success',
    )
  }
}

// ── Обработчики touch/keyboard (навигация + гайд) ─────────────────────────
const handleTouchEnd = (e: TouchEvent) => {
  if (onTouchEnd(e)) handleGuideCompletion()
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (onKeyDown(e)) handleGuideCompletion()
}

// ── Логика PWA-установки ───────────────────────────────────────────────────
const showPwaPrompt = () => {
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone
  if (isStandalone || localStorage.getItem('pwa_prompt_ignored') === 'true') {
    overlayManager.dismiss('pwa_install')
    return
  }

  let promptCount = parseInt(localStorage.getItem('pwa_prompt_count') || '0')
  promptCount += 1
  localStorage.setItem('pwa_prompt_count', promptCount.toString())

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream
  const showCheckbox = promptCount >= 5

  const handleCheckUserIgnore = () => {
    if (store.modal.checkboxValue) localStorage.setItem('pwa_prompt_ignored', 'true')
  }

  if (store.deferredPrompt) {
    store.showModal({
      title: 'Установить приложение',
      message: 'Добавь Kosyga.Space на главный экран, чтобы расписание работало моментально и без интернета.',
      confirmText: 'Установить',
      type: 'primary',
      showCheckbox,
      checkboxText: 'Больше не предлагать',
      onConfirm: async () => {
        handleCheckUserIgnore()
        store.deferredPrompt.prompt()
        await store.deferredPrompt.userChoice
        store.deferredPrompt = null
        overlayManager.dismiss('pwa_install')
      },
      onCancel: () => { handleCheckUserIgnore(); overlayManager.dismiss('pwa_install') },
    })
  } else {
    store.showModal({
      title: isIOS ? 'Установить на iPhone' : 'Установить приложение',
      message: isIOS
        ? 'Нажми кнопку «Поделиться» (квадрат со стрелочкой) внизу экрана Safari и выбери «На экран Домой».'
        : 'Нажми на три точки в правом верхнем углу меню Chrome и выбери «Установить приложение» (или «Добавить на гл. экран»).',
      confirmText: 'Понятно',
      type: 'primary',
      showCheckbox,
      checkboxText: 'Больше не предлагать',
      onConfirm: () => { handleCheckUserIgnore(); overlayManager.dismiss('pwa_install') },
      onCancel: () => { handleCheckUserIgnore(); overlayManager.dismiss('pwa_install') },
    })
  }
}

watch(() => overlayManager.state.activeItem, (item) => {
  if (item?.id === 'pwa_install') showPwaPrompt()
})

// ── Избранное ──────────────────────────────────────────────────────────────
const toggleCurrentFavorite = () => {
  if (store.currentViewingGroup) {
    store.toggleFavorite(store.currentViewingGroup)
    if (store.isFavorite(store.currentViewingGroup.group_id)) {
      store.viewContext = 'favorite'
      store.addToast('Группа добавлена в избранное', 'success')
    } else {
      store.viewContext = 'guest'
      store.addToast('Группа удалена из избранного', 'info')
    }
  }
}

// ── Копирование расписания ─────────────────────────────────────────────────
const copyDaySchedule = async () => {
  if (currentLessons.value.length === 0) return

  const dateStr = `${selectedDate.value.getDate()} ${monthNames[selectedDate.value.getMonth()].toLowerCase()}`
  let text = `📅 Расписание на ${dateStr} (${shortDays[selectedDate.value.getDay()]}):\n\n`

  currentLessons.value.forEach((l: any) => {
    text += `🕒 ${l.start_time.slice(0, 5)} - ${l.end_time.slice(0, 5)} | ${l.lesson_name} (${l.type_of_lesson})\n`
    if (l.classroom || l.educational_place) {
      const match = l.educational_place?.match(/^(.*?)\s*(\(.*?\))$/)
      const place = match ? match[1] : (l.educational_place || '')
      text += `📍 ${l.classroom ? l.classroom + ' ' : ''}${place ? '(' + place + ')' : ''}\n`
    }
    if (l.teachers && l.teachers.length > 0) {
      text += `👨‍🏫 ${l.teachers.map((t: any) => t.name).join(', ')}\n`
    }
    text += '\n'
  })

  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text.trim())
      store.addToast('Расписание скопировано', 'success')
      return
    } catch (err) {
      console.warn('Clipboard API failed, trying fallback...', err)
    }
  }

  try {
    const textArea = document.createElement('textarea')
    textArea.value = text.trim()
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    const successful = document.execCommand('copy')
    textArea.remove()
    if (successful) store.addToast('Расписание скопировано', 'success')
    else store.addToast('Не удалось скопировать', 'error')
  } catch {
    store.addToast('Ошибка копирования', 'error')
  }
}

// ── Жизненный цикл ─────────────────────────────────────────────────────────
let timerId: ReturnType<typeof setInterval>

onMounted(() => {
  fetchScheduleData()

  isTouchDevice.value = window.matchMedia('(pointer: coarse)').matches
  window.addEventListener('keydown', handleKeyDown)

  // 1. Гайд по свайпу (только для первого визита)
  if (!localStorage.getItem('has_seen_swipe_guide')) {
    overlayManager.enqueue({ id: 'swipe_guide', type: 'guide', scope: 'lessons', delayBefore: 1500, delayAfter: 1500 })
  }

  // 2. PWA-установка строго после гайда
  overlayManager.enqueue({ id: 'pwa_install', type: 'modal', scope: 'global', delayBefore: 4000, delayAfter: 2000 })

  // Таймер обновления текущего времени (раз в 10 с)
  timerId = setInterval(() => {
    const now = new Date()
    currentMinutes.value = now.getHours() * 60 + now.getMinutes()
  }, 10000)

  // Хак для тестирования времени из консоли браузера: window.setMockTime(14, 20)
  if (typeof window !== 'undefined') {
    (window as any).setMockTime = (hours: number, minutes: number) => {
      clearInterval(timerId)
      currentMinutes.value = hours * 60 + minutes
      store.addToast(`Время заморожено на ${hours}:${minutes}`, 'info')
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  clearInterval(timerId)
})
</script>

<template>
  <div class="flex flex-col h-full bg-page text-secondary overflow-hidden">

    <!-- ══ РЕЖИМ ПРЕПОДАВАТЕЛЯ ═══════════════════════════════════════════════
         TeacherSchedule монтируется/демонтируется при смене учителя (:key).
         overlayManager, GroupInfoSheet, ExcelModal — не затрагиваются.       -->
    <TeacherSchedule
      v-if="store.currentViewingTeacher"
      :key="store.currentViewingTeacher.id"
    />

    <!-- ══ РЕЖИМ СТУДЕНТА ════════════════════════════════════════════════════ -->
    <template v-else>

      <ScheduleHeader
        :groupInfo="groupInfo"
        :isEvenWeek="isEvenWeek"
        :viewContext="store.viewContext"
        :isLoading="isLoading"
        :selectedDate="selectedDate"
        @openGroupSheet="isGroupSheetOpen = true"
        @refresh="fetchScheduleData(true)"
        @addToFavorites="toggleCurrentFavorite"
        @goHome="store.resetToMainGroup()"
      />

      <WeekDayPicker
        :selectedDate="selectedDate"
        :currentWeekDates="currentWeekDates"
        :showCopyButton="currentState === 'lessons'"
        :today="realToday"
        @selectDate="selectDate"
        @copy="copyDaySchedule"
      />

      <ScheduleBody
        :currentState="currentState"
        :lessons="currentLessons"
        :selectedDate="selectedDate"
        :currentMinutes="currentMinutes"
        :realToday="realToday"
        :transitionName="transitionName"
        :showSwipeGuide="overlayManager.state.activeItem?.id === 'swipe_guide'"
        :isTouchDevice="isTouchDevice"
        @touchstart="onTouchStart"
        @touchend="handleTouchEnd"
        @retry="fetchScheduleData(true)"
        @swipeGuideDismiss="completeSwipeGuide"
      />

      <GroupInfoSheet
        :isOpen="isGroupSheetOpen"
        :groupInfo="groupInfo"
        :formattedSemesterDates="formattedSemesterDates"
        :excelUrl="originalExcelUrl"
        :viewContext="store.viewContext"
        :isFavorite="store.isFavorite(groupInfo.group_id)"
        @close="isGroupSheetOpen = false"
        @toggleFavorite="toggleCurrentFavorite"
        @openExcel="isExcelModalOpen = true"
      />

      <ExcelModal
        :isOpen="isExcelModalOpen"
        :url="originalExcelUrl"
        @close="isExcelModalOpen = false"
      />

    </template>

  </div>
</template>
