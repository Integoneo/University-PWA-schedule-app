/**
 * useChangelogDetector — хук для определения новых версий и показа Changelog.
 *
 * Алгоритм:
 *   1. Читает last_seen_version из localStorage
 *   2. Новый пользователь (нет ключа) → пишем CURRENT_VERSION, ничего не показываем
 *   3. Версия отстаёт → собираем новые записи, ограничиваем до 3, пушим в overlayManager
 *   4. Сразу обновляем last_seen_version → повторного показа не будет
 */

import { CURRENT_VERSION, changelogHistory } from '../config/changelog'
import type { ChangelogEntry } from '../config/changelog'
import { overlayManager } from './useOverlayManager'

// ─── Semver сравнение ────────────────────────────────────────────────────────

/**
 * Сравнивает две semver-строки.
 * @returns  1 если a > b | -1 если a < b | 0 если равны
 */
function compareSemver(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    const diff = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (diff !== 0) return diff > 0 ? 1 : -1
  }
  return 0
}

// ─── Типы payload ────────────────────────────────────────────────────────────

export interface ChangelogPayload {
  entries: ChangelogEntry[]
}

// ─── Хук ─────────────────────────────────────────────────────────────────────

export function useChangelogDetector() {
  /**
   * Вызывай один раз в onMounted App.vue.
   * Сайд-эффект: пишет/обновляет last_seen_version, ставит задачу в overlayManager.
   */
  function check() {
    const lastSeen = localStorage.getItem('last_seen_version')

    // Версия актуальна
    if (lastSeen && compareSemver(lastSeen, CURRENT_VERSION) >= 0) return

    // Новый пользователь / сброс кэша → считаем что видел '0.0.0'.
    // Это гарантирует показ changelog даже для первой версии приложения.
    const effectiveLastSeen = lastSeen || '0.0.0'

    // Собираем все записи новее effectiveLastSeen, сортируем от новых к старым
    const newEntries = changelogHistory
      .filter(entry => compareSemver(entry.version, effectiveLastSeen) > 0)
      .sort((a, b) => compareSemver(b.version, a.version))

    // Сразу обновляем версию — повторного показа не будет даже при крэше
    localStorage.setItem('last_seen_version', CURRENT_VERSION)

    if (newEntries.length === 0) return

    // Ограничиваем до 3 версий, чтобы не перегружать UI
    const limited: ChangelogEntry[] = newEntries.slice(0, 3)

    const payload: ChangelogPayload = { entries: limited }

    overlayManager.enqueue({
      id: 'changelog',
      type: 'modal',
      scope: 'global',
      delayBefore: 4500,  // Даём время на начальный рендер + swipe guide / PWA prompt
      delayAfter: 500,
      payload,
    })
  }

  return { check }
}
