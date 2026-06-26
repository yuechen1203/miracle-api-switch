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
  background:
    linear-gradient(135deg, rgba(226, 247, 252, 0.3), rgba(22, 103, 119, 0.05)),
    rgba(73, 42, 30, 0.24);
  backdrop-filter: blur(10px);
  display: flex;
  justify-content: flex-end;
  z-index: 1000;
}
.drawer-panel {
  background:
    linear-gradient(150deg, rgba(255, 255, 255, 0.06), transparent 30%),
    var(--bg-glass-strong);
  border-left: 1px solid var(--border-strong);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -30px 0 80px rgba(18, 77, 91, 0.22);
  max-width: 100vw;
  backdrop-filter: blur(20px);
}
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 17px 19px;
  border-bottom: 1px solid var(--border-soft);
  background: linear-gradient(180deg, var(--panel-light), transparent);
}
.drawer-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}
.drawer-close {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--panel-light);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  transition: color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.drawer-close:hover {
  color: var(--text-primary);
  background: var(--panel-lighter);
  transform: rotate(6deg);
}
.drawer-body {
  flex: 1;
  overflow: auto;
  padding: 20px;
}
.drawer-footer {
  border-top: 1px solid var(--border-soft);
  padding: 13px 18px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  background: var(--panel-light);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity var(--duration-med) var(--ease-out);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 260ms var(--ease-out), opacity 260ms var(--ease-out);
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  opacity: 0.6;
  transform: translateX(32px);
}
</style>
