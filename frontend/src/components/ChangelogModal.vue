<script setup lang="ts">
/**
 * ChangelogModal.vue — всплывающая модалка «Что нового».
 *
 * Рендерится в App.vue когда overlayManager.state.activeItem?.id === 'changelog'.
 * Данные читает из activeItem.payload.entries (ChangelogEntry[]).
 * Закрывается через overlayManager.dismiss('changelog').
 */
import { computed } from 'vue'
import { overlayManager } from '../composables/useOverlayManager'
import type { ChangelogEntry } from '../config/changelog'

const entries = computed<ChangelogEntry[]>(
  () => (overlayManager.state.activeItem?.payload?.entries ?? []) as ChangelogEntry[]
)

const close = () => overlayManager.dismiss('changelog')

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
  <Teleport to="body">
    <Transition name="changelog-overlay">
      <div
        v-if="entries.length > 0"
        class="fixed inset-0 z-[200] flex items-end justify-center p-4"
        style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom));"
      >
        <!-- Бэкдроп -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close"></div>

        <!-- Карточка -->
        <Transition name="changelog-card">
          <div class="relative w-full max-w-lg bg-surface border border-line rounded-3xl shadow-2xl flex flex-col max-h-[82vh]">

            <!-- Шапка -->
            <div class="px-6 pt-6 pb-4 border-b border-line/50 shrink-0">
              <div class="flex items-center gap-3">
                <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-accent to-purple-500 flex items-center justify-center text-xl shadow-lg shadow-indigo-900/40 shrink-0">
                  🎉
                </div>
                <div class="flex flex-col min-w-0">
                  <span class="text-[10px] font-bold text-subtle uppercase tracking-widest">Kosyga.Space</span>
                  <h2 class="text-xl font-black text-primary tracking-tight leading-tight">Что нового?</h2>
                </div>
              </div>
            </div>

            <!-- Контент (скроллируемый) -->
            <div class="flex-1 overflow-y-auto px-6 py-5 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] flex flex-col gap-6">
              <template v-for="(entry, idx) in entries" :key="entry.version">

                <!-- Разделитель между версиями -->
                <div v-if="idx > 0" class="h-px bg-line/50 -mx-2"></div>

                <!-- Версия + дата + тип -->
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-base font-black text-primary">v{{ entry.version }}</span>
                  <span
                    class="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border"
                    :class="TYPE_COLORS[entry.type]"
                  >{{ TYPE_LABELS[entry.type] }}</span>
                  <span class="text-[11px] text-subtle ml-auto">{{ formatDate(entry.date) }}</span>
                </div>

                <!-- Новые функции -->
                <div v-if="entry.features.length > 0" class="flex flex-col gap-3">
                  <span class="text-[10px] font-bold text-subtle uppercase tracking-widest">✨ Новые функции</span>
                  <div
                    v-for="(feat, fi) in entry.features"
                    :key="'f' + fi"
                    class="flex flex-col gap-1.5 bg-accent/5 border border-accent/10 rounded-2xl px-4 py-3"
                  >
                    <div class="flex items-start gap-2">
                      <span class="text-accent text-xs mt-0.5 shrink-0 font-bold">→</span>
                      <span class="text-sm font-semibold text-secondary leading-snug">{{ feat.name }}</span>
                    </div>
                    <!-- description рендерится как HTML -->
                    <p
                      v-if="feat.description"
                      class="text-xs text-muted leading-relaxed pl-4 changelog-html"
                      v-html="feat.description"
                    ></p>
                  </div>
                </div>

                <!-- Исправления -->
                <div v-if="entry.fixes.length > 0" class="flex flex-col gap-3">
                  <span class="text-[10px] font-bold text-subtle uppercase tracking-widest">🔧 Исправления</span>
                  <div
                    v-for="(fix, fi) in entry.fixes"
                    :key="'fx' + fi"
                    class="flex flex-col gap-1.5 bg-success/5 border border-success/10 rounded-2xl px-4 py-3"
                  >
                    <div class="flex items-start gap-2">
                      <span class="text-success text-xs mt-0.5 shrink-0 font-bold">✓</span>
                      <span class="text-sm font-semibold text-secondary leading-snug">{{ fix.name }}</span>
                    </div>
                    <p
                      v-if="fix.description"
                      class="text-xs text-muted leading-relaxed pl-4 changelog-html"
                      v-html="fix.description"
                    ></p>
                  </div>
                </div>

              </template>
            </div>

            <!-- Кнопка закрытия -->
            <div class="px-6 pb-6 pt-4 border-t border-line/50 shrink-0">
              <button
                @click="close"
                class="w-full py-4 bg-accent-strong hover:bg-accent text-primary font-bold rounded-2xl text-sm transition-colors active:scale-[0.98] shadow-lg shadow-indigo-900/40"
              >
                Понятно, спасибо! 👍
              </button>
            </div>

          </div>
        </Transition>

      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.changelog-overlay-enter-active,
.changelog-overlay-leave-active {
  transition: opacity 0.25s ease-out;
}
.changelog-overlay-enter-from,
.changelog-overlay-leave-to {
  opacity: 0;
}

.changelog-card-enter-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease-out;
}
.changelog-card-leave-active {
  transition: transform 0.2s ease-in, opacity 0.2s ease-in;
}
.changelog-card-enter-from {
  transform: translateY(50px);
  opacity: 0;
}
.changelog-card-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

/* Стили для HTML-контента в описаниях */
:deep(.changelog-html a) {
  color: var(--accent);
  text-decoration: underline;
  font-weight: 600;
}
:deep(.changelog-html a:hover) {
  opacity: 0.8;
}
:deep(.changelog-html b),
:deep(.changelog-html strong) {
  color: var(--text-secondary);
  font-weight: 700;
}
:deep(.changelog-html em) {
  font-style: italic;
}
</style>
