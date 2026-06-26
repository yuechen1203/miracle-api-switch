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
  width: 42px;
  height: 24px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--panel-light);
  position: relative;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
  padding: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.58);
}
.toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-ring);
}
.thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: linear-gradient(180deg, #ffffff, #d7e9ec);
  border-radius: 50%;
  transition: left var(--duration-med) var(--ease-out), background var(--duration-med) var(--ease-out), box-shadow var(--duration-med) var(--ease-out);
  box-shadow: 0 4px 10px rgba(18, 77, 91, 0.18);
}
.toggle.on {
  background: linear-gradient(135deg, rgba(16, 122, 115, 0.24), rgba(40, 111, 159, 0.18));
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft), inset 0 1px 0 rgba(255, 255, 255, 0.58);
}
.toggle.on .thumb {
  left: 20px;
  background: linear-gradient(180deg, #ffffff, var(--accent));
  box-shadow: 0 0 18px rgba(16, 122, 115, 0.34);
}
.toggle.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
