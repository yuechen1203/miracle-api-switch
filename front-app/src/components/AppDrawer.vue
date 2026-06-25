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
    if (val) {
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onKeydown);
    } else {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeydown);
    }
  },
);
onBeforeUnmount(() => {
  document.body.style.overflow = "";
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <Teleport to="body">
    <transition name="drawer">
      <div v-if="props.open" class="drawer-root" @mousedown.self="close">
        <aside
          class="drawer-panel"
          :style="{ width: props.width || '440px' }"
          role="dialog"
          aria-modal="true"
        >
          <header class="drawer-header">
            <h2>{{ props.title }}</h2>
            <button class="drawer-close" aria-label="关闭" @click="close">×</button>
          </header>
          <div class="drawer-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="drawer-footer">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.drawer-root {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 12, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: flex-end;
  z-index: 1000;
}
.drawer-panel {
  background: var(--bg-surface);
  border-left: 1px solid var(--border-soft);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  max-width: 100vw;
}
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-soft);
}
.drawer-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}
.drawer-close {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}
.drawer-close:hover {
  color: var(--text-primary);
}
.drawer-body {
  flex: 1;
  overflow: auto;
  padding: 18px;
}
.drawer-footer {
  border-top: 1px solid var(--border-soft);
  padding: 12px 18px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  background: var(--bg-surface);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 140ms ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 200ms cubic-bezier(0.2, 0.7, 0.2, 1);
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(24px);
}
</style>
