/**
 * useDonationPrompt — ненавязчивое предложение поддержать проект через CloudTips.
 *
 * Показ идёт через overlayManager (пассивное системное событие, как changelog),
 * поэтому само встаёт в очередь за «Что нового» и PWA-установкой и не всплывает
 * на /welcome и /onboarding.
 *
 * Алгоритм (все отметки времени — epoch ms в localStorage):
 *   donation_first_seen_at    — первый запуск, ставится один раз. Первые 3 дня молчим.
 *   donation_next_eligible_at — дата, раньше которой показывать нельзя.
 *   donation_pending          — «окно уже назначено, ждём его даты».
 *
 * Кубик 4–7 дней кидается ОДИН раз, когда подошло время, а не при каждом открытии:
 * иначе пользователь, заходящий по 5 раз в день, видел бы донат почти ежедневно.
 * Получается ровно один показ на случайный интервал.
 *
 *   «Напомнить позже» / свайп — pending снимается, следующее окно уже записано (+4–7 дн).
 *   «Отправить донат»         — pending снимается, окно перезаписывается на +30 дней.
 */
import { overlayManager } from './useOverlayManager'

export const CLOUDTIPS_URL = 'https://pay.cloudtips.ru/p/81959e13'

const KEY_FIRST_SEEN = 'donation_first_seen_at'
const KEY_NEXT_AT = 'donation_next_eligible_at'
const KEY_PENDING = 'donation_pending'

const DAY = 86_400_000
const GRACE_DAYS = 3
const COOLDOWN_AFTER_DONATE_DAYS = 30

/** Случайный интервал до следующего показа: 4, 5, 6 или 7 дней */
const randomIntervalMs = () => (4 + Math.floor(Math.random() * 4)) * DAY

export function useDonationPrompt() {
  /**
   * Вызывай один раз в onMounted App.vue, после checkChangelog().
   * delayBefore больше, чем у changelog (4.5с) и pwa_install (4с),
   * поэтому донат всегда оказывается последним в очереди.
   */
  function check() {
    const now = Date.now()

    // 1. Льготный период: первые 3 дня после первого запуска молчим
    const firstSeenRaw = localStorage.getItem(KEY_FIRST_SEEN)
    if (!firstSeenRaw) {
      localStorage.setItem(KEY_FIRST_SEEN, String(now))
      return
    }
    if (now - Number(firstSeenRaw) < GRACE_DAYS * DAY) return

    // 2. Окно ещё не наступило
    const nextAt = Number(localStorage.getItem(KEY_NEXT_AT) || '0')
    if (now < nextAt) return

    // 3. Время пришло, а бросок ещё не сделан — назначаем следующее окно
    //    и помечаем показ как ожидающий. Бросок делается один раз на окно.
    if (localStorage.getItem(KEY_PENDING) !== 'true') {
      localStorage.setItem(KEY_NEXT_AT, String(now + randomIntervalMs()))
      localStorage.setItem(KEY_PENDING, 'true')
    }

    // 4. В очередь
    overlayManager.enqueue({
      id: 'donation',
      type: 'modal',
      scope: 'global',
      delayBefore: 6000,
      delayAfter: 500,
    })
  }

  /** «Напомнить позже» или закрытие свайпом: окно уже назначено, просто снимаем флаг */
  function dismiss() {
    localStorage.removeItem(KEY_PENDING)
    overlayManager.dismiss('donation')
  }

  /** «Отправить донат»: открываем CloudTips и замолкаем минимум на 30 дней */
  function donate() {
    window.open(CLOUDTIPS_URL, '_blank', 'noopener,noreferrer')
    localStorage.removeItem(KEY_PENDING)
    localStorage.setItem(KEY_NEXT_AT, String(Date.now() + COOLDOWN_AFTER_DONATE_DAYS * DAY))
    overlayManager.dismiss('donation')
  }

  return { check, dismiss, donate }
}
