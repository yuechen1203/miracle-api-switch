<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null | undefined;
    type?: string;
    placeholder?: string;
    invalid?: boolean;
    disabled?: boolean;
    autocomplete?: string;
    mono?: boolean;
    min?: number | string;
    max?: number | string;
  }>(),
  { type: "text" },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string | number | null): void;
}>();

const value = computed<string | number>({
  get() {
    return props.modelValue ?? "";
  },
  set(v) {
    if (props.type === "number") {
      if (v === "" || v === null) emit("update:modelValue", null);
      else emit("update:modelValue", Number(v));
    } else {
      emit("update:modelValue", v as string);
    }
  },
});
</script>

<template>
  <input
    v-model="value"
    :type="props.type"
    :placeholder="props.placeholder"
    :disabled="props.disabled"
    :autocomplete="props.autocomplete"
    :min="props.min"
    :max="props.max"
    class="input"
    :class="{ 'is-invalid': props.invalid, mono: props.mono }"
  />
</template>

<style scoped>
.input {
  width: 100%;
  height: 34px;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 0 10px;
  font-size: 13px;
  color: var(--text-primary);
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.input.mono {
  font-family: var(--font-mono);
}
.input::placeholder {
  color: var(--text-disabled);
}
.input:hover:not(:disabled) {
  border-color: #3a4756;
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-ring);
}
.input.is-invalid {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px rgba(239, 106, 106, 0.18);
}
.input:disabled {
  background: var(--bg-surface-2);
  color: var(--text-disabled);
  cursor: not-allowed;
}
</style>
