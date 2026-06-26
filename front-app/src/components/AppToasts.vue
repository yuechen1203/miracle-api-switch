<script setup lang="ts">
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-vue-next";
import { useAppStore } from "@/stores/app";
const app = useAppStore();
const iconMap = {
  success: CheckCircle2,
  warn: AlertTriangle,
  error: XCircle,
  info: Info,
};
</script>

<template>
  <div class="toasts" role="region" aria-live="polite">
    <transition-group name="toast">
      <div
        v-for="t in app.toasts"
        :key="t.id"
        class="toast"
        :class="`tone-${t.level}`"
        @click="app.dismissToast(t.id)"
      >
        <component :is="iconMap[t.level]" :size="16" />
        <div class="toast-body">
          <div class="toast-title">{{ t.title }}</div>
          <div v-if="t.description" class="toast-desc">{{ t.description }}</div>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  top: 18px;
  right: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 1200;
  max-width: min(90vw, 380px);
}
.toast {
  display: flex;
  gap: 10px;
  padding: 12px 13px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.07), transparent 34%),
    var(--bg-glass-strong);
  border: 1px solid var(--border-strong);
  border-left-width: 3px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  font-size: 14px;
  cursor: pointer;
  align-items: flex-start;
  backdrop-filter: blur(18px);
  transition: transform var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.toast:hover {
  transform: translateX(-2px) translateY(-1px);
}
.toast-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.toast-title {
  font-weight: 650;
  color: var(--text-primary);
}
.toast-desc {
  color: var(--text-secondary);
  font-size: 13.5px;
  word-break: break-word;
}
.tone-success { border-color: rgba(116, 224, 173, 0.42); color: var(--ok); background-color: rgba(116, 224, 173, 0.06); }
.tone-warn    { border-color: rgba(71, 106, 159, 0.42); color: var(--warn); background-color: rgba(71, 106, 159, 0.06); }
.tone-error   { border-color: rgba(251, 133, 133, 0.42); color: var(--danger); background-color: rgba(251, 133, 133, 0.06); }
.tone-info    { border-color: rgba(40, 111, 159, 0.42); color: var(--info); background-color: rgba(40, 111, 159, 0.06); }
.toast :deep(svg) {
  flex-shrink: 0;
  margin-top: 2px;
  filter: drop-shadow(0 0 10px currentColor);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity var(--duration-med) var(--ease-out), transform var(--duration-med) var(--ease-out);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(14px) scale(0.98);
}
</style>
