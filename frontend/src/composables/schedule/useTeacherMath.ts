/**
 * Утилиты для математики расписания преподавателей.
 *
 * Бэкенд гарантирует сортировку:
 *   1) нечётная неделя → чётная (is_even_week: false → true)
 *   2) внутри: день 0 (пн) → 6 (вс)
 *   3) внутри дня: по start_time ASC
 *
 * Функции принимают уже отфильтрованный список пар
 * (конкретный день + чётность недели).
 */

// ─── Типы ────────────────────────────────────────────────────────────────────

export interface TeacherLesson {
  day_of_week: number
  is_even_week: boolean
  lesson_name: string
  type_of_lesson: string
  classroom: string
  educational_place: string
  start_time: string
  end_time: string
  groups: string[]
}

/**
 * Группа пар, сформированная алгоритмом слияния интервалов.
 * Если hasConflict=true — две или более пары пересекаются по времени.
 */
export interface LessonGroup {
  lessons: TeacherLesson[]
  hasConflict: boolean
  /** Минуты с 00:00 для старта самой ранней пары в группе. */
  startMinutes: number
  /** Минуты с 00:00 для окончания самой поздней пары в группе. */
  endMinutes: number
}

// ─── Вспомогательные функции ─────────────────────────────────────────────────

/**
 * Разбирает строку времени в формате:
 *   "HH:mm", "HH:mm:ss", "HH:mm:ss.mmmZ"
 * и возвращает количество минут с начала суток.
 *
 * @example parseTeacherTime("14:25")        // → 865
 * @example parseTeacherTime("15:14:00.000Z") // → 914
 */
export function parseTeacherTime(timeStr: string): number {
  const parts = timeStr.split(':')
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10)
}

// ─── Основные функции ─────────────────────────────────────────────────────────

/**
 * Группирует пары одного дня с учётом наслоений (конфликтов).
 *
 * Алгоритм — sweep line / merge overlapping intervals:
 *   наслоение возникает, если startB < endA
 *   (пример: 14:25–15:15 и 15:14–16:00 → наслоение, т.к. 914 < 915)
 *
 * Входной массив должен быть уже отсортирован по start_time.
 *
 * @param lessons Отфильтрованный список пар одного дня/чётности.
 * @returns Массив групп. Группы с hasConflict=true содержат 2+ конфликтующих пары.
 *
 * @example
 * // Три пары: А(10:00–11:30), B(11:00–12:30), C(13:00–14:30)
 * // A и B пересекаются → одна конфликтная группа
 * // C отдельная → одиночная группа
 * // Итого: [{ lessons:[A,B], hasConflict:true }, { lessons:[C], hasConflict:false }]
 */
export function groupLessonsWithOverlaps(lessons: TeacherLesson[]): LessonGroup[] {
  if (lessons.length === 0) return []

  const groups: LessonGroup[] = []
  let currentLessons: TeacherLesson[] = [lessons[0]]
  let currentEnd = parseTeacherTime(lessons[0].end_time)

  for (let i = 1; i < lessons.length; i++) {
    const lesson = lessons[i]
    const lessonStart = parseTeacherTime(lesson.start_time)
    const lessonEnd = parseTeacherTime(lesson.end_time)

    if (lessonStart < currentEnd) {
      // ⚡ Наслоение — добавляем в текущую группу, расширяем конец кластера
      currentLessons.push(lesson)
      currentEnd = Math.max(currentEnd, lessonEnd)
    } else {
      // ✓ Нет наслоения — фиксируем текущую группу, открываем новую
      groups.push({
        lessons: currentLessons,
        hasConflict: currentLessons.length > 1,
        startMinutes: parseTeacherTime(currentLessons[0].start_time),
        endMinutes: currentEnd,
      })
      currentLessons = [lesson]
      currentEnd = lessonEnd
    }
  }

  // Фиксируем последнюю группу
  groups.push({
    lessons: currentLessons,
    hasConflict: currentLessons.length > 1,
    startMinutes: parseTeacherTime(currentLessons[0].start_time),
    endMinutes: currentEnd,
  })

  return groups
}

/**
 * Вычисляет окна (gaps) между группами пар в минутах.
 *
 * Длина результата равна длине входного массива.
 * gaps[0] всегда 0 (нет окна перед первой группой).
 * gaps[i] = group[i].startMinutes − group[i−1].endMinutes, минимум 0.
 *
 * Значение > 0 — реальное свободное окно между парами.
 * Значение = 0 — группы идут вплотную (или API вернул некорректные данные).
 *
 * @param groups Массив групп, полученный из groupLessonsWithOverlaps.
 * @returns Массив размером groups.length, где gaps[i] — минуты перед группой i.
 *
 * @example
 * // Группа A заканчивается в 11:30 (690 мин)
 * // Группа B начинается в 13:00 (780 мин)
 * // gaps = [0, 90]  → 90-минутное окно перед группой B
 */
export function computeGaps(groups: LessonGroup[]): number[] {
  return groups.map((group, i) => {
    if (i === 0) return 0
    return Math.max(0, group.startMinutes - groups[i - 1].endMinutes)
  })
}
