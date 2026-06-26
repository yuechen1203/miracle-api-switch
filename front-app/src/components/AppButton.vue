<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md";
    loading?: boolean;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    fullWidth?: boolean;
  }>(),
  { variant: "secondary", size: "md", type: "button" },
);

const emit = defineEmits<{ (e: "click", ev: MouseEvent): void }>();

const cls = computed(() => [
  "btn",
  `btn-${props.variant}`,
  `btn-${props.size}`,
  { "btn-loading": props.loading, "btn-block": props.fullWidth },
]);
</script>

<template>
  <button
    :class="cls"
    :type="props.type"
    :disabled="props.disabled || props.loading"
    @click="(e) => emit('click', e)"
  >
    <span v-if="props.loading" class="spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 650;
  font-size: 14.5px;
  line-height: 1;
  padding: 0 15px;
  height: 34px;
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}
.btn::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.16) 45%, transparent 72%);
  transform: translateX(-120%);
  transition: transform 520ms var(--ease-out);
  pointer-events: none;
}
.btn:hover:not(:disabled)::before {
  transform: translateX(120%);
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}
.btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.btn:active:not(:disabled) {
  transform: translateY(1px);
}
.btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-ring), 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
}
.btn-sm { height: 31px; padding: 0 12px; font-size: 13.5px; }
.btn-block { width: 100%; }

.btn-primary {
  background: linear-gradient(135deg, var(--accent-strong), var(--accent));
  color: #fffaf6;
  border-color: rgba(16, 122, 115, 0.82);
  box-shadow: 0 12px 28px rgba(16, 122, 115, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.32);
}
.btn-primary:hover:not(:disabled) {
  border-color: var(--accent-strong);
  box-shadow: 0 16px 34px rgba(16, 122, 115, 0.26), inset 0 1px 0 rgba(255, 255, 255, 0.36);
}

.btn-secondary {
  background: linear-gradient(180deg, var(--panel-lighter), rgba(255, 255, 255, 0.02)), var(--bg-surface-2);
  color: var(--text-primary);
  border-color: var(--border-strong);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--bg-surface-3);
  border-color: var(--border-glow);
  box-shadow: var(--shadow-soft);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: transparent;
}
.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--panel-lighter);
}

.btn-danger {
  background: linear-gradient(135deg, rgba(182, 63, 63, 0.18), rgba(182, 63, 63, 0.08));
  color: var(--danger);
  border-color: rgba(182, 63, 63, 0.38);
}
.btn-danger:hover:not(:disabled) {
  background: rgba(182, 63, 63, 0.18);
  color: #8e2f2f;
  box-shadow: 0 14px 32px rgba(182, 63, 63, 0.12);
}

.spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
