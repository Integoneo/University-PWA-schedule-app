/**
 * OverlayManager — глобальный менеджер очереди всплывающих элементов.
 *
 * Принципы работы:
 *  - FIFO-очередь с поддержкой scope, задержек и "заморозки" локальных элементов
 *  - Blacklist роутов: на /welcome и /onboarding очередь полностью на паузе
 *  - Глобальные элементы (scope: 'global') показываются на любой из 4 вкладок
 *  - Локальные элементы при уходе с их вкладки замораживаются и возвращаются
 *    в начало очереди, при возврате активируются без задержки delayBefore
 *  - Единственный публичный синглтон: overlayManager
 */

import { reactive } from 'vue'
import type { Router } from 'vue-router'

// ─── Типы ────────────────────────────────────────────────────────────────────

export type OverlayScope = 'global' | 'lessons' | 'exams' | 'search' | 'settings'

export type OverlayType = 'guide' | 'modal' | 'banner' | 'alert'

export interface OverlayItem {
  /** Уникальный идентификатор. Повторный enqueue с тем же id игнорируется. */
  id: string
  /** Вид элемента — используется потребителями для выбора шаблона рендера */
  type: OverlayType
  /** Область видимости */
  scope: OverlayScope
  /**
   * Задержка (мс) перед тем, как элемент станет активным.
   * Для размороженных элементов игнорируется.
   */
  delayBefore: number
  /**
   * Задержка (мс) после dismiss() перед обработкой следующего элемента.
   */
  delayAfter: number
  /** Произвольные данные для потребителей */
  payload?: Record<string, any>
  /** Вызывается в момент, когда элемент становится активным */
  onActivate?: () => void
  /** Вызывается в момент, когда элемент закрывается */
  onDismiss?: () => void
}

// Внутреннее расширение для хранения состояния "заморозки"
interface OverlayItemInternal extends OverlayItem {
  _frozen: boolean
}

// ─── Конфигурация ────────────────────────────────────────────────────────────

/** Роуты, на которых очередь полностью на паузе */
const BLOCKED_ROUTES = ['/welcome', '/onboarding']

/** Карта scope -> роут для локальных элементов */
const SCOPE_TO_ROUTE: Record<string, string> = {
  lessons:  '/lessons',
  exams:    '/exams',
  search:   '/search',
  settings: '/settings',
}

// ─── Состояние (module-level singleton) ──────────────────────────────────────

interface OverlayState {
  activeItem:   OverlayItemInternal | null
  queue:        OverlayItemInternal[]
  isPaused:     boolean
  isWaiting:    boolean
  currentRoute: string
}

const state = reactive<OverlayState>({
  activeItem:   null,
  queue:        [],
  isPaused:     true, // Стартуем на паузе — init() снимет её на нужном роуте
  isWaiting:    false,
  currentRoute: '/',
})

let waitTimer: ReturnType<typeof setTimeout> | null = null

// ─── Вспомогательные ─────────────────────────────────────────────────────────

const clearWaitTimer = () => {
  if (waitTimer !== null) {
    clearTimeout(waitTimer)
    waitTimer = null
  }
}

const isItemCompatibleWithRoute = (item: OverlayItemInternal, route: string): boolean => {
  if (item.scope === 'global') return true
  return SCOPE_TO_ROUTE[item.scope] === route
}

const activateItem = (item: OverlayItemInternal) => {
  state.activeItem = item
  item.onActivate?.()
}

/** Замораживает элемент и возвращает его в начало очереди */
const freezeItem = (item: OverlayItemInternal) => {
  item._frozen = true
  state.queue.unshift(item)
}

// ─── Ядро обработчика очереди ────────────────────────────────────────────────

const processQueue = () => {
  if (state.activeItem !== null || state.isWaiting || state.isPaused) return
  if (state.queue.length === 0) return

  // Ищем первый элемент, совместимый с текущим роутом
  const idx = state.queue.findIndex(item => isItemCompatibleWithRoute(item, state.currentRoute))
  if (idx === -1) return

  const next = state.queue.splice(idx, 1)[0]

  // Размороженные элементы активируются без задержки delayBefore
  const delay = next._frozen ? 0 : next.delayBefore
  next._frozen = false

  if (delay > 0) {
    state.isWaiting = true
    waitTimer = setTimeout(() => {
      state.isWaiting = false
      // После задержки проверяем, не ушли ли мы с нужного роута
      if (!state.isPaused && isItemCompatibleWithRoute(next, state.currentRoute)) {
        activateItem(next)
      } else {
        // Роут сменился за время задержки — замораживаем элемент
        freezeItem(next)
        processQueue()
      }
    }, delay)
  } else {
    activateItem(next)
  }
}

// ─── Обработчик смены роута ──────────────────────────────────────────────────

const handleRouteChange = (newRoute: string) => {
  state.currentRoute = newRoute

  // 1. Проверяем blacklist
  if (BLOCKED_ROUTES.includes(newRoute)) {
    state.isPaused = true
    clearWaitTimer()
    state.isWaiting = false
    // Замораживаем активный элемент, если он есть
    if (state.activeItem !== null) {
      freezeItem(state.activeItem)
      state.activeItem = null
    }
    return
  }

  // 2. Снимаем паузу при выходе из blacklist
  state.isPaused = false

  // 3. Проверяем активный локальный элемент при смене вкладки
  if (state.activeItem !== null) {
    const active = state.activeItem
    if (!isItemCompatibleWithRoute(active, newRoute)) {
      state.activeItem = null
      clearWaitTimer()
      state.isWaiting = false
      freezeItem(active)
    }
    // Глобальный активный элемент — не трогаем, остаётся видимым
  }

  // 4. Обрабатываем очередь (покажет первый совместимый с новым роутом)
  processQueue()
}

// ─── Публичное API ───────────────────────────────────────────────────────────

export const overlayManager = {
  /** Реактивное состояние для использования в шаблонах Vue */
  state,

  /**
   * Инициализация. Вызывается ОДИН РАЗ из main.ts после создания router.
   * Подписывается на смену роутов и устанавливает начальное состояние.
   */
  init(router: Router) {
    router.afterEach((to) => {
      handleRouteChange(to.path)
    })
    // Устанавливаем начальный роут
    handleRouteChange(router.currentRoute.value.path)
  },

  /**
   * Добавить элемент в конец очереди.
   * Идемпотентно: элемент с таким же id игнорируется.
   */
  enqueue(item: OverlayItem) {
    const id = item.id
    if (state.activeItem?.id === id) return
    if (state.queue.some(q => q.id === id)) return

    const internal: OverlayItemInternal = { ...item, _frozen: false }
    state.queue.push(internal)
    processQueue()
  },

  /**
   * Закрыть текущий активный элемент.
   * id должен совпадать с activeItem.id — защита от гонки состояний.
   */
  dismiss(id: string) {
    if (state.activeItem?.id !== id) return

    const item = state.activeItem
    state.activeItem = null
    item.onDismiss?.()

    const delay = item.delayAfter
    if (delay > 0) {
      state.isWaiting = true
      waitTimer = setTimeout(() => {
        state.isWaiting = false
        processQueue()
      }, delay)
    } else {
      processQueue()
    }
  },

  /**
   * Полностью удалить элемент из очереди (если ещё не активен).
   */
  cancel(id: string) {
    state.queue = state.queue.filter(item => item.id !== id)
  },

  /**
   * Принудительная пауза (для внешних вызовов).
   * Не замораживает активный элемент — только стопит обработку очереди.
   */
  pause() {
    state.isPaused = true
    clearWaitTimer()
    state.isWaiting = false
  },

  /**
   * Снять принудительную паузу.
   */
  resume() {
    if (BLOCKED_ROUTES.includes(state.currentRoute)) return
    state.isPaused = false
    processQueue()
  },
}
