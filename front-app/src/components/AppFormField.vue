<script setup lang="ts">
defineProps<{ label?: string; hint?: string; error?: string }>();
</script>

<template>
  <label class="form-field">
    <span v-if="$slots.label || label" class="form-label">
      <slot name="label">{{ label }}</slot>
    </span>
    <slot />
    <span v-if="error" class="form-error">{{ error }}</span>
    <span v-else-if="hint || $slots.hint" class="form-hint">
      <slot name="hint">{{ hint }}</slot>
    </span>
  </label>
</template>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.form-label {
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 0.01em;
}
.form-error {
  font-size: 12px;
  color: var(--danger);
}
.form-hint {
  font-size: 11.5px;
  color: var(--text-tertiary);
}
</style>
