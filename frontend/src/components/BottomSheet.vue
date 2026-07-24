<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits(['close'])

// === ФИЗИКА СВАЙПА ===
const sheetY = ref(0)
const isDraggingSheet = ref(false)
let dragStartY = 0

// Сбрасываем позицию шторки каждый раз, когда она открывается заново
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    sheetY.value = 0
    isDraggingSheet.value = false
  }
})

const onTouchStart = (e: TouchEvent) => {
  dragStartY = e.touches[0].clientY
  isDraggingSheet.value = true
}

const onTouchMove = (e: TouchEvent) => {
  const currentY = e.touches[0].clientY
  const delta = currentY - dragStartY
  
  // Позволяем тянуть шторку только вниз
  if (delta > 0) {
    sheetY.value = delta
    if (e.cancelable) e.preventDefault() // Блокируем скролл страницы
  }
}

const onTouchEnd = () => {
  isDraggingSheet.value = false
  
  // Если протянули вниз больше чем на 100 пикселей - закрываем
  if (sheetY.value > 100) {
    emit('close')
    // Важно: мы не сбрасываем sheetY.value в 0 прямо сейчас, 
    // чтобы шторка не "прыгнула" вверх перед тем, как исчезнуть.
  } else {
    // Иначе плавно отпружиниваем обратно
    sheetY.value = 0
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- Затемнение фона -->
    <Transition name="fade">
      <div v-if="isOpen" @click="emit('close')" class="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-[60]"></div>
    </Transition>

    <!-- Сама шторка -->
    <Transition name="slide-up">
      <div 
        v-if="isOpen"
        class="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 rounded-t-[2rem] z-[70] shadow-[0_-10px_40px_rgba(0,0,0,0.3)] flex flex-col"
        style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom)); max-height: 90vh;"
        :style="{ 
          transform: sheetY > 0 ? `translateY(${sheetY}px)` : '',
          transition: isDraggingSheet ? 'none' : 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }"
      >
        <!-- ЗОНА СВАЙПА (Ползунок + Шапка) -->
        <div 
          @touchstart="onTouchStart" 
          @touchmove="onTouchMove" 
          @touchend="onTouchEnd"
          class="pt-4 pb-2 touch-none w-full flex flex-col shrink-0"
        >
          <!-- Ползунок -->
          <div class="w-12 h-1.5 bg-slate-700/50 rounded-full mx-auto mb-4"></div>
          
          <!-- Слот для заголовка -->
          <div v-if="$slots.header" class="px-5 w-full">
            <slot name="header"></slot>
          </div>
        </div>
        
        <!-- ОСНОВНОЙ КОНТЕНТ (Скроллится, не реагирует на свайп закрытия) -->
        <div class="px-5 pb-4 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <slot></slot>
        </div>

      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
</style>
