<script setup lang="ts">
import { store } from '../store'
</script>

<template>
  <Transition name="modal">
    <div v-if="store.modal.isOpen" @click="store.closeModal(true)" class="fixed inset-0 bg-page/80 backdrop-blur-sm z-[200] flex items-center justify-center p-5 pointer-events-auto">
      
      <div @click.stop class="modal-box bg-surface border border-line rounded-[2rem] p-6 w-full max-w-sm shadow-2xl flex flex-col gap-5">
        
        <div class="flex flex-col gap-2.5">
          <h3 class="text-xl font-bold text-primary leading-tight">{{ store.modal.title }}</h3>
          <p class="text-sm text-muted leading-relaxed">{{ store.modal.message }}</p>
        </div>
        
        <!-- КАСТОМНЫЙ ЧЕКБОКС -->
        <label v-if="store.modal.showCheckbox" class="flex items-center gap-3 mt-1 cursor-pointer group">
          <div class="relative flex items-center justify-center w-6 h-6 rounded-md border border-line-muted bg-raised group-hover:border-accent transition-colors">
            <input type="checkbox" v-model="store.modal.checkboxValue" class="peer sr-only" />
            <svg class="w-4 h-4 text-accent-strong opacity-0 peer-checked:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
          </div>
          <span class="text-sm text-muted select-none group-hover:text-tertiary transition-colors">
            {{ store.modal.checkboxText }}
          </span>
        </label>
        
        <div class="flex gap-3 mt-2">
          <button @click="store.closeModal(true)" class="flex-1 py-3.5 bg-raised hover:bg-raised/80 text-primary font-semibold rounded-xl transition-colors">
            Отмена
          </button>
          
          <button 
            @click="store.modal.onConfirm()" 
            :class="[
              'flex-1 py-3.5 font-semibold border rounded-xl transition-colors',
              store.modal.type === 'primary' 
                ? 'bg-accent-strong hover:bg-accent text-primary border-accent/50 shadow-lg shadow-indigo-900/20' 
                : 'bg-error/10 hover:bg-error/20 text-error border-error/20'
            ]"
          >
            {{ store.modal.confirmText }}
          </button>
        </div>
        
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.25s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .modal-box, .modal-leave-active .modal-box { transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.modal-enter-from .modal-box, .modal-leave-to .modal-box { transform: scale(0.95) translateY(15px); }
</style>
<style scoped>
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-active .modal-box, .modal-leave-active .modal-box {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-box, .modal-leave-to .modal-box {
  transform: scale(0.95) translateY(15px);
}
</style>
