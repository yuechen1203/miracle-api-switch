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
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1200;
  max-width: min(90vw, 360px);
}
.toast {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-surface-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  font-size: 13px;
  cursor: pointer;
  align-items: flex-start;
}
.toast-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.toast-title {
  font-weight: 500;
  color: var(--text-primary);
}
.toast-desc {
  color: var(--text-secondary);
  font-size: 12px;
  word-break: break-word;
}
.tone-success { border-color: rgba(92, 210, 155, 0.35); color: var(--ok); }
.tone-warn    { border-color: rgba(246, 178, 90, 0.35); color: var(--warn); }
.tone-error   { border-color: rgba(239, 106, 106, 0.35); color: var(--danger); }
.tone-info    { border-color: rgba(106, 166, 255, 0.35); color: var(--info); }
.toast :deep(svg) {
  flex-shrink: 0;
  margin-top: 2px;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 140ms ease, transform 140ms ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(8px);
}
</style>
