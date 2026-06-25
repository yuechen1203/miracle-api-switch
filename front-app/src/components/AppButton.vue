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
  gap: 6px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 500;
  font-size: 13px;
  line-height: 1;
  padding: 0 14px;
  height: 32px;
  transition: background-color 120ms ease, border-color 120ms ease, transform 120ms ease;
  white-space: nowrap;
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.btn:active:not(:disabled) {
  transform: translateY(1px);
}
.btn-sm { height: 28px; padding: 0 10px; font-size: 12px; }
.btn-block { width: 100%; }

.btn-primary {
  background: var(--accent);
  color: #06231f;
  border-color: var(--accent);
}
.btn-primary:hover:not(:disabled) {
  background: var(--accent-strong);
  border-color: var(--accent-strong);
}

.btn-secondary {
  background: var(--bg-surface-2);
  color: var(--text-primary);
  border-color: var(--border-strong);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--bg-surface-3);
  border-color: #3a4756;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: transparent;
}
.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-surface-2);
}

.btn-danger {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: rgba(239, 106, 106, 0.32);
}
.btn-danger:hover:not(:disabled) {
  background: rgba(239, 106, 106, 0.2);
  color: #ffd2d2;
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
