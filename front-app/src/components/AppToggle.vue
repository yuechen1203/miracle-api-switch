<script setup lang="ts">
const props = defineProps<{ modelValue: boolean; disabled?: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", value: boolean): void }>();
function toggle() {
  if (props.disabled) return;
  emit("update:modelValue", !props.modelValue);
}
</script>

<template>
  <button
    type="button"
    class="toggle"
    :class="{ on: props.modelValue, disabled: props.disabled }"
    role="switch"
    :aria-checked="props.modelValue"
    :disabled="props.disabled"
    @click="toggle"
  >
    <span class="thumb" />
  </button>
</template>

<style scoped>
.toggle {
  width: 38px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--bg-surface-2);
  position: relative;
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease;
  padding: 0;
}
.toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-ring);
}
.thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: left 160ms ease, background-color 160ms ease;
}
.toggle.on {
  background: var(--accent-soft);
  border-color: var(--accent);
}
.toggle.on .thumb {
  left: 18px;
  background: var(--accent);
}
.toggle.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
