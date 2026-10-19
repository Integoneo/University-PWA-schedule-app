<script setup lang="ts">
/**
 * Шторка редактора заметок пары.
 * Локальный флаг открытия (не overlayManager) — пользовательское действие.
 */
import { ref, watch } from 'vue'
import BottomSheet from '../BottomSheet.vue'
import { useLessonNotes, NOTE_MAX_LENGTH } from '../../composables/schedule/useLessonNotes'

const props = defineProps<{
  isOpen: boolean
  lesson: any | null
  date: Date
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const notes = useLessonNotes()
const generalText = ref('')
const datedText = ref('')

watch(
  () => props.isOpen,
  (open) => {
    if (open && props.lesson) {
      const initial = notes.getEditorInitial(props.lesson, props.date)
      generalText.value = initial.general
      datedText.value = initial.dated
    }
  },
)

const formattedDate = () => {
  return props.date.toLocaleDateString('ru', { day: 'numeric', month: 'long' })
}

const handleClose = () => {
  if (props.lesson) {
    notes.stashDrafts(props.lesson, props.date, generalText.value, datedText.value)
  }
  emit('close')
}

const handleSave = () => {
  if (!props.lesson) return
  notes.saveNotes(props.lesson, props.date, generalText.value, datedText.value)
  emit('saved')
  emit('close')
}
</script>

<template>
  <BottomSheet :is-open="isOpen" @close="handleClose">
    <template #header>
      <div class="flex flex-col gap-1 pb-1">
        <h2 class="text-xl font-bold text-primary leading-tight">Заметки</h2>
        <p v-if="lesson" class="text-sm text-muted leading-snug">
          {{ lesson.lesson_name }}
          <span class="text-subtle"> · {{ formattedDate() }} · {{ lesson.number_of_lesson }} пара</span>
        </p>
      </div>
    </template>

    <div class="flex flex-col gap-5 mt-3">
      <!-- Общая заметка -->
      <label class="flex flex-col gap-2">
        <span class="text-[11px] font-bold uppercase tracking-widest text-subtle">Общая заметка</span>
        <span class="text-[11px] text-muted -mt-1">Для всех пар этого предмета</span>
        <textarea
          v-model="generalText"
          :maxlength="NOTE_MAX_LENGTH"
          rows="3"
          placeholder="Например: нельзя приходить без карандашей"
          class="w-full resize-none rounded-2xl bg-raised border border-line px-4 py-3 text-sm text-secondary placeholder:text-subtle outline-none focus:border-accent/40 transition-colors"
        ></textarea>
        <span class="self-end text-[10px] text-subtle">{{ generalText.length }}/{{ NOTE_MAX_LENGTH }}</span>
      </label>

      <!-- Заметка на дату -->
      <label class="flex flex-col gap-2">
        <span class="text-[11px] font-bold uppercase tracking-widest text-subtle">На эту пару</span>
        <span class="text-[11px] text-muted -mt-1">Только на {{ formattedDate() }}</span>
        <textarea
          v-model="datedText"
          :maxlength="NOTE_MAX_LENGTH"
          rows="3"
          placeholder="Например: принести презентацию про Петра I"
          class="w-full resize-none rounded-2xl bg-raised border border-line px-4 py-3 text-sm text-secondary placeholder:text-subtle outline-none focus:border-accent/40 transition-colors"
        ></textarea>
        <span class="self-end text-[10px] text-subtle">{{ datedText.length }}/{{ NOTE_MAX_LENGTH }}</span>
      </label>

      <p class="text-[11px] text-muted leading-relaxed bg-raised/50 border border-line/60 rounded-xl px-3 py-2.5">
        💾 Заметки хранятся только на этом устройстве. При удалении приложения или очистке данных браузера они будут потеряны.
      </p>

      <div class="flex gap-3">
        <button
          @click="handleClose"
          class="flex-1 py-3.5 bg-raised hover:bg-raised/80 text-primary font-semibold rounded-xl transition-colors active:scale-[0.98]"
        >
          Отмена
        </button>
        <button
          @click="handleSave"
          class="flex-1 py-3.5 bg-accent-strong hover:bg-accent text-primary font-semibold rounded-xl transition-colors active:scale-[0.98]"
        >
          Сохранить
        </button>
      </div>
    </div>
  </BottomSheet>
</template>
