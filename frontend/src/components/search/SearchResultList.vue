<script setup lang="ts">
/**
 * Общий компонент списка результатов поиска.
 *
 * Принимает уже нарезанный до displayLimit массив видимых элементов.
 * Рендерит их через scoped-slot `#default="{ item }"`,
 * показывает empty-state и кнопку «Показать ещё».
 *
 * Переиспользуется для вкладки ГРУППЫ и ПРЕПОДАВАТЕЛИ.
 */
withDefaults(defineProps<{
  /** Видимые (уже нарезанные) элементы. */
  visibleItems: any[]
  /** Сколько элементов ещё осталось за лимитом. */
  remainingCount: number
  /** Полная подпись кнопки «показать ещё», уже с числом и правильным словом. */
  nextLoadLabel: string
  /** Эмодзи для пустого состояния при поиске. */
  emptyIcon?: string
  /** Подпись для пустого состояния при поиске. */
  emptyText?: string
}>(), {
  emptyIcon: '🤔',
  emptyText: 'Ничего не найдено',
})

defineEmits<{
  loadMore: []
}>()
</script>

<template>
  <div class="flex flex-col gap-3">

    <!-- Пустой результат -->
    <div v-if="visibleItems.length === 0" class="flex flex-col items-center justify-center py-12 opacity-60">
      <span class="text-3xl mb-2">{{ emptyIcon }}</span>
      <span class="text-muted text-sm">{{ emptyText }}</span>
    </div>

    <!-- Список через слот -->
    <template v-else>
      <template v-for="item in visibleItems" :key="item.id ?? item.group_id">
        <slot :item="item" />
      </template>

      <!-- Кнопка «Показать ещё» -->
      <button
        v-if="remainingCount > 0"
        @click="$emit('loadMore')"
        class="mt-1 w-full py-4 flex items-center justify-center gap-2 bg-raised/40 hover:bg-raised/80 border border-line-muted/50 rounded-2xl text-tertiary text-sm font-bold transition-all active:scale-95"
      >
        <svg class="w-4 h-4 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
        {{ nextLoadLabel }}
      </button>
    </template>

  </div>
</template>
