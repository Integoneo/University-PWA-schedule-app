<script setup lang="ts">
import BottomSheet from '../BottomSheet.vue'

/**
 * Шторка с информацией о группе: институт, форма обучения, период семестра.
 * Кнопки «Добавить/Удалить из избранного» и «Excel».
 */
defineProps<{
  isOpen: boolean
  groupInfo: any
  formattedSemesterDates: string
  excelUrl: string | null
  viewContext: string
  isFavorite: boolean
}>()

defineEmits<{
  close: []
  toggleFavorite: []
  openExcel: []
}>()

const formatStudyForm = (str: string) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}
</script>

<template>
  <BottomSheet :is-open="isOpen" @close="$emit('close')">
    <template #header>
      <div class="flex items-center justify-between pointer-events-none mb-2">
        <h2 class="text-xl pr-4 font-bold text-primary tracking-tight break-words">
          Группа {{ groupInfo?.group_name || 'Д-101' }}
        </h2>
        <button
          @click.stop="$emit('close')"
          class="p-2 -mr-2 rounded-full text-muted pointer-events-auto active:scale-95 transition-transform shrink-0"
        >
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </template>

    <div class="bg-raised/30 border border-line-muted/50 rounded-2xl p-4 flex flex-col gap-4">
      <div class="flex items-center gap-3.5">
        <div class="w-11 h-11 rounded-xl bg-white border border-slate-200 flex items-center justify-center shrink-0 p-1.5">
          <img v-if="groupInfo.logo_url" :src="groupInfo.logo_url" class="w-full h-full object-contain" alt="Логотип" />
          <svg v-else class="w-6 h-6 text-tertiary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1v1H9V7zm5 0h1v1h-1V7zm-5 4h1v1H9v-1zm5 0h1v1h-1v-1zm-3 4H2v6h20v-6h-9z" />
          </svg>
        </div>
        <div class="flex flex-col justify-center min-w-0 pr-2">
          <span v-if="groupInfo.institute_short_name" class="text-[11px] text-accent font-bold uppercase tracking-widest mb-0.5">
            {{ groupInfo.institute_short_name }}
          </span>
          <span class="text-xs font-semibold text-secondary leading-tight uppercase line-clamp-2 break-words">
            {{ groupInfo.institute_full_name }}
          </span>
        </div>
      </div>

      <div class="h-px w-full bg-gradient-to-r from-transparent via-slate-700/50 to-transparent"></div>

      <div class="grid grid-cols-2 gap-y-4 gap-x-4 items-center">
        <div class="flex flex-col justify-center">
          <span class="text-base font-bold text-secondary">{{ groupInfo.file_title }}</span>
        </div>
        <div class="flex flex-col justify-center border-l border-line-muted/50 pl-4">
          <span class="text-xs font-medium text-tertiary leading-snug">{{ formatStudyForm(groupInfo.study_form || '') }}</span>
        </div>
        <div class="col-span-2 flex flex-col pt-3 border-t border-line-muted/30">
          <span class="text-[10px] text-subtle font-bold uppercase tracking-widest mb-1">Период обучения</span>
          <span class="text-sm font-medium text-secondary">{{ formattedSemesterDates }}</span>
        </div>
      </div>
    </div>

    <div class="mt-4 flex flex-col gap-2">
      <button
        v-if="viewContext !== 'main'"
        @click="$emit('toggleFavorite')"
        class="w-full py-3.5 flex items-center justify-center gap-2 rounded-xl transition-colors font-bold text-sm active:scale-[0.98] border"
        :class="isFavorite
          ? 'bg-raised/80 text-tertiary border-line-muted hover:bg-raised'
          : 'bg-warning/10 text-warning border-warning/20 hover:bg-warning/20'"
      >
        <span v-if="isFavorite">
          <svg class="w-5 h-5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </span>
        <span v-else>⭐</span>
        {{ isFavorite ? 'Удалить из избранного' : 'Добавить в избранное' }}
      </button>

      <button
        v-if="excelUrl"
        @click="$emit('openExcel')"
        class="w-full py-3.5 flex items-center justify-center gap-2 rounded-xl transition-colors font-bold text-sm active:scale-[0.98] bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Оригинал от ВУЗа (Excel)
      </button>
    </div>
  </BottomSheet>
</template>
