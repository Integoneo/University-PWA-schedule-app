/**
 * useMidnightReset — надёжный детектор смены суток для PWA.
 *
 * ПОЧЕМУ НЕ setTimeout ДО ПОЛУНОЧИ:
 *   Мобильные ОС (iOS, Android) ставят фоновые таймеры на паузу при блокировке
 *   экрана. Таймер на 23:59:59 → 00:00:00 пропускается или отрабатывает спустя
 *   часы — с неверным `new Date()` внутри колбэка, ломая расчёт чётности.
 *
 * КАК РАБОТАЕТ:
 *   1. `document.addEventListener('visibilitychange')` — при возврате в foreground
 *      (разблокировка телефона, переключение вкладок) сразу сверяем дату.
 *   2. `setInterval` раз в 1 минуту — запасной механизм пока вкладка видима.
 *   3. Проверка: `getCurrentDate().toDateString() !== realToday.value.toDateString()`
 *      — если строки отличаются, значит наступил новый день.
 *   4. При обнаружении нового дня:
 *      - realToday.value = getCurrentDate()  (маркер текущего дня, всегда)
 *      - selectedDate.value = getCurrentDate() ТОЛЬКО если он указывал на «вчера»
 *        (пользователь не листал расписание на другую дату вручную)
 *
 * МОКИРОВАНИЕ ДЛЯ ТЕСТОВ:
 *   Экспортируемая функция setMockDateSource(date | null) заменяет внутренний
 *   getCurrentDate(). Schedule.vue вешает window.debugSetDate на неё + checkDayChange().
 */

import { onMounted, onUnmounted } from 'vue'
import type { Ref } from 'vue'

// ─── Mockable date source (module-level → переживает пересоздание компонента) ──

let _mockDate: Date | null = null

/**
 * Устанавливает мок-дату для всех вызовов getCurrentDate() в этом модуле.
 * Передай null чтобы сбросить мок и вернуться к реальному new Date().
 */
export const setMockDateSource = (d: Date | null): void => {
  _mockDate = d
}

/**
 * Возвращает «текущую дату».
 * В продакшне — new Date().
 * В тестах — мок из setMockDateSource.
 */
export const getCurrentDate = (): Date =>
  _mockDate !== null ? new Date(_mockDate) : new Date()

// ─── Composable ──────────────────────────────────────────────────────────────

export function useMidnightReset(options: {
  /**
   * Текущий «сегодня» — передаётся из Schedule.vue / TeacherSchedule.vue.
   * Composable обновляет realToday.value при смене суток.
   */
  realToday: Ref<Date>
  /**
   * Выбранная пользователем дата.
   * Сдвигается ТОЛЬКО если указывала на «старый сегодня».
   */
  selectedDate: Ref<Date>
  /**
   * Вызывается после обновления realToday и selectedDate.
   * Используй для обновления currentMinutes и других производных стейтов.
   */
  onNewDay?: (newToday: Date) => void
}) {
  const { realToday, selectedDate, onNewDay } = options

  let interval: ReturnType<typeof setInterval> | null = null

  /**
   * Основная логика: проверяет изменение дня и обновляет стейт.
   *
   * Публичная — в dev-режиме Schedule.vue вешает её на window
   * для ручного тестирования через window.debugSetDate().
   */
  const checkDayChange = (): void => {
    const current = getCurrentDate()

    // Быстрая проверка: "Wed Sep 10 2026" vs "Wed Sep 10 2026"
    // Не зависит от UTC-сдвигов и часовых поясов.
    if (current.toDateString() === realToday.value.toDateString()) return

    // ── Новый день обнаружен ─────────────────────────────────────────────────
    const prevToday = realToday.value

    // Если пользователь смотрел на «старый сегодня» — переключаем на новый
    if (selectedDate.value.toDateString() === prevToday.toDateString()) {
      selectedDate.value = current
    }

    // Маркер текущего дня обновляем ВСЕГДА (нужен для подсветки «сегодня»)
    realToday.value = current

    onNewDay?.(current)
  }

  const onVisibilityChange = (): void => {
    if (document.visibilityState === 'visible') checkDayChange()
  }

  onMounted(() => {
    // Запасной интервал — 1 мин достаточно, короткие интервалы браузер не троттлит
    interval = setInterval(checkDayChange, 60_000)
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    if (interval !== null) clearInterval(interval)
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  return { checkDayChange }
}
