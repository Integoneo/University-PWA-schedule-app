<script setup lang="ts">
/**
 * Полноэкранный просмотрщик Excel-файла (оригинал от ВУЗа).
 */
defineProps<{
  isOpen: boolean
  url: string | null
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <Transition name="fade">
    <div v-if="isOpen" class="fixed inset-0 z-[100] flex flex-col bg-page">

      <!-- Шапка -->
      <div class="flex items-center justify-between px-4 py-3 bg-surface border-b border-line shrink-0 shadow-md z-10">
        <div class="flex items-center gap-3 pr-4 overflow-hidden">
          <div class="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-500 shrink-0">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 class="text-primary font-bold text-[15px] truncate">Официальное расписание</h3>
        </div>
        <button @click="$emit('close')" class="p-2 -mr-2 rounded-full text-muted hover:bg-raised hover:text-primary active:scale-95 transition-all shrink-0">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Контент -->
      <div class="flex-1 w-full bg-surface relative">
        <!-- Плейсхолдер пока грузится iframe -->
        <div class="absolute inset-0 flex flex-col items-center justify-center space-y-4 opacity-50">
          <svg class="w-8 h-8 animate-spin text-accent-strong" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span class="text-sm font-semibold text-muted">Загрузка документа...</span>
        </div>

        <iframe
          :src="url || undefined"
          class="absolute inset-0 w-full h-full border-0 z-10 bg-white"
          allowfullscreen
        ></iframe>
      </div>

    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
