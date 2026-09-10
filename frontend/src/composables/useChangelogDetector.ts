/**
 * useChangelogDetector — хук для определения новых версий и показа Changelog.
 *
 * Алгоритм:
 *   1. Читает last_seen_version из localStorage
 *   2. ИСКЛЮЧЕНИЕ v1.0.0: первый релиз с changelog — показываем всем без исключения.
 *      После показа сразу пишем last_seen_version = '1.0.0', поэтому второго раза нет.
 *   3. Новый пользователь (нет ключа) → пишем CURRENT_VERSION, ничего не показываем
 *   4. Версия отстаёт → собираем новые записи, ограничиваем до 3, пушим в overlayManager
 *   5. Сразу обновляем last_seen_version → повторного показа не будет
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
    // ──────────────────────────────────────────────────────────────────────────
    // ИСКЛЮЧЕНИЕ v1.0.0 — идёт ПЕРВЫМ, до любых других проверок.
    //
    // Зачем отдельный ключ changelog_v1_shown:
    //   Старый код (до фикса) мог записать last_seen_version = '1.0.0' сразу
    //   при старте, не показав changelog. Если бы мы полагались только на
    //   last_seen_version, обычная проверка ниже вернулась бы раньше и
    //   changelog так и не показался бы.
    //   Отдельный ключ решает это навсегда.
    //
    // Когда выйдет v1.1.0 — CURRENT_VERSION !== '1.0.0' и блок не сработает.
    // ──────────────────────────────────────────────────────────────────────────
    if (CURRENT_VERSION === '1.0.0') {
      if (!localStorage.getItem('changelog_v1_shown')) {
        // Фиксируем немедленно — повторного показа не будет
        localStorage.setItem('changelog_v1_shown', '1')
        localStorage.setItem('last_seen_version', CURRENT_VERSION)

        const entries = changelogHistory.filter(e => e.version === '1.0.0')
        if (entries.length > 0) {
          overlayManager.enqueue({
            id: 'changelog',
            type: 'modal',
            scope: 'global',
            delayBefore: 4500,
            delayAfter: 500,
            payload: { entries } as ChangelogPayload,
          })
        }
      }
      return
    }

    // ── Обычный флоу для v1.1.0+ ─────────────────────────────────────────────

    const lastSeen = localStorage.getItem('last_seen_version')

    // Версия уже актуальна — ничего не делаем
    if (lastSeen && compareSemver(lastSeen, CURRENT_VERSION) >= 0) return

    // Новый пользователь (нет ключа) → просто фиксируем версию, ничего не показываем
    if (!lastSeen) {
      localStorage.setItem('last_seen_version', CURRENT_VERSION)
      return
    }

    // Существующий пользователь с устаревшей версией → показываем новые записи
    const newEntries = changelogHistory
      .filter(entry => compareSemver(entry.version, lastSeen) > 0)
      .sort((a, b) => compareSemver(b.version, a.version))

    // Сразу обновляем версию — повторного показа не будет даже при крэше
    localStorage.setItem('last_seen_version', CURRENT_VERSION)

    if (newEntries.length === 0) return

    // Ограничиваем до 3 версий, чтобы не перегружать UI
    const limited: ChangelogEntry[] = newEntries.slice(0, 3)

    overlayManager.enqueue({
      id: 'changelog',
      type: 'modal',
      scope: 'global',
      delayBefore: 4500,
      delayAfter: 500,
      payload: { entries: limited } as ChangelogPayload,
    })
  }

  return { check }
}
