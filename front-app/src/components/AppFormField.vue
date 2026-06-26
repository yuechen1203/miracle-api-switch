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
  gap: 8px;
  width: 100%;
}
.form-label {
  font-size: 14.5px;
  color: var(--text-primary);
  font-weight: 600;
  letter-spacing: 0;
}
.form-error {
  font-size: 13.5px;
  color: var(--danger);
  font-weight: 500;
}
.form-hint {
  font-size: 13.5px;
  color: var(--text-tertiary);
  line-height: 1.5;
}
</style>
