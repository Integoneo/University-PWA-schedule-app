<script setup lang="ts">
/**
 * Changelog.vue — полная страница истории обновлений.
 * Маршрут: /changelog  |  hideNavbar: true
 */
import { useRouter } from 'vue-router'
import { CURRENT_VERSION, changelogHistory } from '../config/changelog'
import type { ChangelogEntry } from '../config/changelog'

const router = useRouter()

// Сортируем от новых к старым (на случай если в массиве порядок не соблюдён)
const sortedHistory: ChangelogEntry[] = [...changelogHistory].sort((a, b) => {
  const pa = a.version.split('.').map(Number)
  const pb = b.version.split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    const diff = (pb[i] ?? 0) - (pa[i] ?? 0)
    if (diff !== 0) return diff
  }
  return 0
})

const TYPE_LABELS: Record<string, string> = {
  major: 'Крупное обновление',
  minor: 'Обновление',
  patch: 'Патч',
}

const TYPE_COLORS: Record<string, string> = {
  major: 'bg-accent/20 text-accent border-accent/30',
  minor: 'bg-success/20 text-success border-success/30',
  patch: 'bg-warning/20 text-warning border-warning/30',
}

const formatDate = (iso: string) => {
  const d = new Date(iso)
  return d.toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' })
}
</script>

<template>
  <div class="h-full w-full bg-page flex flex-col pt-12 pb-8 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">

    <!-- Шапка -->
    <div class="px-4 mb-6">
      <button @click="router.back()" class="flex items-center gap-2 -ml-2 p-2 text-muted hover:text-primary transition-colors active:scale-95">
        <svg class="w-6 h-6 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
        </svg>
        <h1 class="text-2xl font-bold text-primary tracking-tight">История изменений</h1>
      </button>
    </div>

    <!-- Текущая версия -->
    <div class="mx-4 mb-6 p-4 bg-accent/10 border border-accent/20 rounded-2xl flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-500 flex items-center justify-center text-lg shadow-lg shadow-indigo-900/30 shrink-0">
        🚀
      </div>
      <div class="flex flex-col">
        <span class="text-xs font-bold text-subtle uppercase tracking-widest">Текущая версия</span>
        <span class="text-lg font-black text-primary">v{{ CURRENT_VERSION }}</span>
      </div>
    </div>

    <!-- Список версий -->
    <div class="px-4 flex flex-col gap-4">

      <!-- Пустой список -->
      <div
        v-if="sortedHistory.length === 0"
        class="flex flex-col items-center justify-center py-16 bg-surface/20 border border-surface rounded-3xl opacity-60"
      >
        <span class="text-4xl mb-3">📋</span>
        <span class="text-muted text-sm font-medium">История обновлений пока пуста</span>
        <span class="text-subtle text-xs mt-1">Здесь появятся записи при следующих релизах</span>
      </div>

      <!-- Записи -->
      <div
        v-for="entry in sortedHistory"
        :key="entry.version"
        class="bg-surface/60 border border-line rounded-3xl p-5 flex flex-col gap-4"
      >
        <!-- Заголовок записи -->
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-lg font-black text-primary">v{{ entry.version }}</span>
              <span
                class="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border"
                :class="TYPE_COLORS[entry.type]"
              >
                {{ TYPE_LABELS[entry.type] }}
              </span>
            </div>
            <span class="text-xs text-subtle">{{ formatDate(entry.date) }}</span>
          </div>
        </div>

        <!-- Новые функции -->
        <div v-if="entry.features.length > 0" class="flex flex-col gap-2">
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[11px] font-bold text-subtle uppercase tracking-widest">✨ Новые функции</span>
          </div>
          <div
            v-for="(feat, i) in entry.features"
            :key="'f' + i"
            class="flex items-start gap-3 bg-accent/5 border border-accent/10 rounded-xl px-3 py-2.5"
          >
            <span class="text-accent text-xs mt-0.5 shrink-0 font-bold">→</span>
            <span class="text-sm text-secondary leading-snug">{{ feat }}</span>
          </div>
        </div>

        <!-- Исправления -->
        <div v-if="entry.fixes.length > 0" class="flex flex-col gap-2">
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[11px] font-bold text-subtle uppercase tracking-widest">🔧 Исправления</span>
          </div>
          <div
            v-for="(fix, i) in entry.fixes"
            :key="'fx' + i"
            class="flex items-start gap-3 bg-success/5 border border-success/10 rounded-xl px-3 py-2.5"
          >
            <span class="text-success text-xs mt-0.5 shrink-0 font-bold">✓</span>
            <span class="text-sm text-secondary leading-snug">{{ fix }}</span>
          </div>
        </div>

      </div>

    </div>

  </div>
</template>
