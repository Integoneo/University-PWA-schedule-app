<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// TODO: реализовать полноценный экран расписания преподавателя
console.log('[TeacherSchedule] teacher id:', route.params.id)
</script>

<template>
  <div class="flex flex-col h-full bg-page text-secondary items-center justify-center px-6 text-center">
    <span class="text-5xl mb-5">🚧</span>
    <h2 class="text-xl font-bold text-primary mb-2">Расписание преподавателя</h2>
    <p class="text-muted text-sm leading-relaxed">
      Этот раздел находится в разработке.<br>Совсем скоро здесь появится расписание.
    </p>
    <p class="text-subtle text-xs mt-3 font-mono">ID: {{ route.params.id }}</p>
    <button
      @click="router.back()"
      class="mt-8 px-6 py-2.5 bg-raised border border-line-muted text-secondary font-bold rounded-xl text-sm active:scale-95 transition-all hover:bg-raised/80"
    >
      ← Назад
    </button>
  </div>
</template>
