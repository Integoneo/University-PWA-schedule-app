<script setup lang="ts">
/**
 * DonationModal — предложение поддержать проект.
 * Рендерится в App.vue, когда overlayManager.state.activeItem?.id === 'donation'.
 * Вся логика расписания показов живёт в useDonationPrompt.
 */
import { useDonationPrompt } from '../composables/useDonationPrompt'

const { dismiss, donate } = useDonationPrompt()
</script>

<template>
  <Teleport to="body">
    <Transition name="donation-overlay">
      <div
        class="fixed inset-0 z-50 flex items-end justify-center p-4"
        style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom));"
      >
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="dismiss"></div>

        <div class="relative w-full max-w-lg bg-surface border border-line rounded-3xl shadow-2xl flex flex-col">
          <div class="px-6 pt-6 pb-2">
            <h2 class="text-xl font-black text-primary tracking-tight leading-tight">
              Расписание без боли и страданий 📱
            </h2>
          </div>

          <div class="px-6 py-4 flex flex-col gap-3">
            <p class="text-sm text-secondary leading-relaxed">
              Привет! Каждый день мой код сражается с древними экселевскими файлами, чтобы у тебя под рукой было красивое и быстрое расписание.
            </p>
            <p class="text-sm text-muted leading-relaxed">
              Приложение держится на моем энтузиазме, но хостинг просит настоящих денег. Если приложение тебе заходит — закинь любой донат через CloudTips. Даже 100 рублей сделают мой день лучше (и продлят жизнь серверу)!
            </p>
          </div>

          <div class="px-6 pb-6 pt-2 flex flex-col gap-2.5">
            <button
              @click="donate"
              class="w-full py-4 bg-accent-strong hover:bg-accent text-primary font-bold rounded-2xl text-sm transition-colors active:scale-[0.98]"
            >
              Отправить донат 🚀
            </button>
            <button
              @click="dismiss"
              class="w-full py-3.5 bg-raised hover:bg-raised/80 text-muted font-semibold rounded-2xl text-sm transition-colors active:scale-[0.98]"
            >
              Напомнить позже
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.donation-overlay-enter-active,
.donation-overlay-leave-active {
  transition: opacity 0.25s ease-out;
}
.donation-overlay-enter-from,
.donation-overlay-leave-to {
  opacity: 0;
}
</style>
