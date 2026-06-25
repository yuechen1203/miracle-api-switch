<script setup lang="ts">
import { watch, onBeforeUnmount } from "vue";
const props = defineProps<{ open: boolean; title?: string; width?: string }>();
const emit = defineEmits<{ (e: "update:open", value: boolean): void }>();

function close() {
  emit("update:open", false);
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.open) close();
}

watch(
  () => props.open,
  (val) => {
    if (val) document.addEventListener("keydown", onKeydown);
    else document.removeEventListener("keydown", onKeydown);
  },
);
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="props.open" class="modal-root" @mousedown.self="close">
        <div
          class="modal-panel"
          :style="{ width: props.width || '480px' }"
          role="dialog"
          aria-modal="true"
        >
          <header v-if="props.title || $slots.title" class="modal-header">
            <h3>
              <slot name="title">{{ props.title }}</slot>
            </h3>
          </header>
          <div class="modal-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-root {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 12, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
}
.modal-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 100%;
}
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-soft);
}
.modal-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}
.modal-body {
  padding: 18px 20px;
  font-size: 13px;
  color: var(--text-primary);
}
.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-soft);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 140ms ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 180ms ease;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateY(6px) scale(0.99);
}
</style>
