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
  background:
    linear-gradient(135deg, rgba(226, 247, 252, 0.3), rgba(22, 103, 119, 0.05)),
    rgba(73, 42, 30, 0.24);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
}
.modal-panel {
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.06), transparent 34%),
    var(--bg-glass-strong);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  max-width: 100%;
  overflow: hidden;
  backdrop-filter: blur(20px);
}
.modal-header {
  padding: 17px 20px;
  border-bottom: 1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent);
}
.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}
.modal-body {
  padding: 19px 20px;
  font-size: 14.5px;
  color: var(--text-primary);
}
.modal-footer {
  padding: 13px 16px;
  border-top: 1px solid var(--border-soft);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  background: var(--panel-light);
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--duration-med) var(--ease-out);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform var(--duration-med) var(--ease-out), opacity var(--duration-med) var(--ease-out);
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  opacity: 0;
  transform: translateY(14px) scale(0.975);
}
</style>
