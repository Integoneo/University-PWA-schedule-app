<script setup lang="ts">
/**
 * Карточка-потеряшка: датированная заметка, пара которой исчезла
 * из расписания на эту дату. Визуально резко отличается от LessonCard.
 */
import type { OrphanNote } from '../../composables/schedule/useLessonNotes'

defineProps<{
  orphan: OrphanNote
}>()

defineEmits<{
  delete: []
}>()
</script>

<template>
  <div class="relative flex rounded-3xl p-4 bg-raised/30 border border-dashed border-warning/40">
    <div class="w-[4.5rem] flex flex-col items-center pr-3 border-r border-dashed border-warning/30 shrink-0">
      <span class="text-2xl leading-none mt-0.5">👻</span>
      <span class="text-[10px] font-bold uppercase tracking-wider text-warning/80 mt-2 text-center leading-tight">
        потеряшка
      </span>
    </div>

    <div class="flex-1 pl-4 flex flex-col min-w-0 gap-1.5">
      <div class="flex items-start justify-between gap-2">
        <div class="flex flex-col min-w-0">
          <span class="text-[10px] font-bold uppercase tracking-widest text-warning/70">Заметка без пары</span>
          <h3 class="text-sm font-semibold text-secondary leading-snug break-words">{{ orphan.lessonName }}</h3>
        </div>
        <button
          @click.stop="$emit('delete')"
          class="p-1.5 -mr-1 -mt-0.5 rounded-lg text-muted hover:text-error hover:bg-error/10 transition-colors shrink-0"
          aria-label="Удалить потеряшку"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      <p class="text-[11px] text-subtle">
        {{ orphan.startTime?.slice(0, 5) }} · {{ orphan.slot }} пара
      </p>
      <p class="text-xs text-muted leading-relaxed whitespace-pre-wrap break-words">{{ orphan.text }}</p>
    </div>
  </div>
</template>
