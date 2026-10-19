/**
 * useLessonNotes — локальные заметки к парам. Работают ТОЛЬКО для основной группы.
 *
 * Два типа заметок:
 *  - Общая: привязана к предмету (нормализованное название lesson_name),
 *    отображается на каждой паре этого предмета.
 *  - Датированная: привязана к (дата + номер пары + предмет) — конкретное занятие.
 *
 * Хранение: localStorage['user_lesson_notes']. Полностью локально, на сервер не уходит.
 * Черновики: in-memory Map (не персистятся, живут до перезапуска приложения).
 *
 * Миграция (migrateNotes) вызывается из useScheduleData после успешной загрузки
 * расписания основной группы:
 *  - общие заметки, предмет которых исчез из расписания, — удаляются навсегда;
 *  - заметки других групп (осталась после смены основной группы) — удаляются;
 *  - датированные заметки старше MAX_AGE_DAYS — удаляются (автоочистка);
 *  - датированные заметки без мэтча НЕ удаляются — рендерятся «потеряшками»
 *    (см. getOrphansForDate), пока их не удалит пользователь или автоочистка.
 *
 * Преподавательский режим (TeacherSchedule) заметки не использует вообще.
 */
import { reactive, ref } from 'vue'
import { store } from '../../store'

export const NOTE_MAX_LENGTH = 600
const STORAGE_KEY = 'user_lesson_notes'
const MAX_AGE_DAYS = 30

export interface DatedNoteRecord {
  text: string
  lessonName: string
  startTime: string
  slot: string
  date: string // YYYY-MM-DD (локальная дата)
  updatedAt: number
}

export interface OrphanNote extends DatedNoteRecord {
  key: string
}

interface NotesState {
  general: Record<string, { text: string; updatedAt: number }>
  dated: Record<string, DatedNoteRecord>
}

// ── Загрузка из localStorage (устойчива к битым данным) ─────────────────────
const loadState = (): NotesState => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { general: {}, dated: {} }
    const parsed = JSON.parse(raw)
    return {
      general: parsed?.general && typeof parsed.general === 'object' ? parsed.general : {},
      dated: parsed?.dated && typeof parsed.dated === 'object' ? parsed.dated : {},
    }
  } catch {
    return { general: {}, dated: {} }
  }
}

const state = reactive<NotesState>(loadState())

// Черновики несохранённых заметок (ключи те же, что у заметок)
const drafts = reactive(new Map<string, string>())

/** Инкрементируется при каждом persist — чтобы computed в UI гарантированно пересчитались */
const revision = ref(0)

const persist = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, general: state.general, dated: state.dated }))
  revision.value++
}

// ── Ключи ────────────────────────────────────────────────────────────────────
const normalizeName = (name: string) => (name || '').trim().toLowerCase()

/** Локальная дата YYYY-MM-DD (НЕ toISOString — тот даёт UTC и сдвигает сутки) */
const toDateKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const mainGroupId = (): string | null =>
  store.groupInfo?.group_id != null ? String(store.groupInfo.group_id) : null

const generalKey = (gid: string, lessonName: string) => `${gid}|${normalizeName(lessonName)}`

const datedKey = (gid: string, date: Date, slot: unknown, lessonName: string) =>
  `${gid}|${toDateKey(date)}|${String(slot)}|${normalizeName(lessonName)}`

// ── Публичное API ────────────────────────────────────────────────────────────
const notesApi = {
  revision,

  /** Текст общей заметки предмета или null */
  getGeneralNote(lesson: any): string | null {
    const gid = mainGroupId()
    if (!gid) return null
    return state.general[generalKey(gid, lesson.lesson_name)]?.text ?? null
  },

  /** Текст датированной заметки конкретной пары на дату или null */
  getDatedNote(lesson: any, date: Date): string | null {
    const gid = mainGroupId()
    if (!gid) return null
    return state.dated[datedKey(gid, date, lesson.number_of_lesson, lesson.lesson_name)]?.text ?? null
  },

  /**
   * Начальные значения для редактора: сохранённая заметка → черновик → пусто.
   * Черновик подставляется только если сохранённой заметки нет.
   */
  getEditorInitial(lesson: any, date: Date): { general: string; dated: string } {
    const gid = mainGroupId()
    if (!gid) return { general: '', dated: '' }
    const gKey = generalKey(gid, lesson.lesson_name)
    const dKey = datedKey(gid, date, lesson.number_of_lesson, lesson.lesson_name)
    return {
      general: state.general[gKey]?.text ?? drafts.get(gKey) ?? '',
      dated: state.dated[dKey]?.text ?? drafts.get(dKey) ?? '',
    }
  },

  /**
   * Сохранить обе заметки пары. Пустой текст = удаление заметки.
   * Связанные черновики очищаются.
   */
  saveNotes(lesson: any, date: Date, generalText: string, datedText: string) {
    const gid = mainGroupId()
    if (!gid) return
    const gKey = generalKey(gid, lesson.lesson_name)
    const dKey = datedKey(gid, date, lesson.number_of_lesson, lesson.lesson_name)
    const g = (generalText || '').trim().slice(0, NOTE_MAX_LENGTH)
    const d = (datedText || '').trim().slice(0, NOTE_MAX_LENGTH)

    if (g) state.general[gKey] = { text: g, updatedAt: Date.now() }
    else delete state.general[gKey]

    if (d) {
      state.dated[dKey] = {
        text: d,
        lessonName: lesson.lesson_name,
        startTime: lesson.start_time,
        slot: String(lesson.number_of_lesson),
        date: toDateKey(date),
        updatedAt: Date.now(),
      }
    } else {
      delete state.dated[dKey]
    }

    drafts.delete(gKey)
    drafts.delete(dKey)
    persist()
  },

  /**
   * Отложить несохранённый текст в черновик (вызывается при «Отмена»/свайпе).
   * Черновик создаётся только для полей, у которых НЕТ сохранённой заметки:
   * правки существующей заметки при отмене отбрасываются (классическое поведение).
   */
  stashDrafts(lesson: any, date: Date, generalText: string, datedText: string) {
    const gid = mainGroupId()
    if (!gid) return
    const gKey = generalKey(gid, lesson.lesson_name)
    const dKey = datedKey(gid, date, lesson.number_of_lesson, lesson.lesson_name)
    const g = (generalText || '').trim()
    const d = (datedText || '').trim()

    if (!state.general[gKey]) {
      g ? drafts.set(gKey, g) : drafts.delete(gKey)
    }
    if (!state.dated[dKey]) {
      d ? drafts.set(dKey, d) : drafts.delete(dKey)
    }
  },

  /**
   * Заметки-потеряшки на дату: датированные заметки этой даты,
   * для которых в расписании дня нет пары с тем же слотом И тем же предметом.
   */
  getOrphansForDate(date: Date, lessonsOfDay: any[]): OrphanNote[] {
    const gid = mainGroupId()
    if (!gid) return []
    const prefix = `${gid}|${toDateKey(date)}|`
    const result: OrphanNote[] = []

    for (const [key, rec] of Object.entries(state.dated)) {
      if (!key.startsWith(prefix)) continue
      const matched = lessonsOfDay.some(
        l =>
          String(l.number_of_lesson) === rec.slot &&
          normalizeName(l.lesson_name) === normalizeName(rec.lessonName),
      )
      if (!matched) result.push({ ...rec, key })
    }

    return result.sort((a, b) => a.startTime.localeCompare(b.startTime))
  },

  /** Удалить датированную заметку по ключу (кнопка на карточке-потеряшке) */
  deleteDatedByKey(key: string) {
    delete state.dated[key]
    persist()
  },
}

export function useLessonNotes() {
  return notesApi
}

/**
 * Миграция заметок. Вызывается из useScheduleData после успешной загрузки
 * расписания, ТОЛЬКО если загружено расписание основной группы.
 * Идемпотентна — безопасно вызывать на каждый фетч.
 */
export function migrateNotes(lessons: any[]) {
  const gid = mainGroupId()
  if (!gid) return
  const gPrefix = `${gid}|`
  let changed = false

  // 1. Общие: удаляем чужие группы и предметы, исчезнувшие из расписания
  const names = new Set(lessons.map(l => normalizeName(l.lesson_name)))
  for (const key of Object.keys(state.general)) {
    if (!key.startsWith(gPrefix)) {
      delete state.general[key]
      changed = true
      continue
    }
    const name = key.slice(gPrefix.length)
    if (!names.has(name)) {
      delete state.general[key]
      changed = true
    }
  }

  // 2. Датированные: удаляем чужие группы и записи старше MAX_AGE_DAYS.
  //    Несмэтченные, но свежие записи НЕ трогаем — это потеряшки.
  const cutoff = Date.now() - MAX_AGE_DAYS * 86_400_000
  for (const [key, rec] of Object.entries(state.dated)) {
    if (!key.startsWith(gPrefix)) {
      delete state.dated[key]
      changed = true
      continue
    }
    const noteDate = new Date(`${rec.date}T23:59:59`)
    if (isNaN(noteDate.getTime()) || noteDate.getTime() < cutoff) {
      delete state.dated[key]
      changed = true
    }
  }

  if (changed) persist()
}
