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
  height: 40px;
  background: var(--field-bg);
  border: 2px solid var(--field-border);
  border-radius: var(--radius-md);
  padding: 0 13px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-field);
  transition: border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out);
  box-shadow: 0 4px 12px rgba(18, 77, 91, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.72);
}
.input.mono {
  font-family: var(--font-mono);
  letter-spacing: 0.01em;
}
.input::placeholder {
  color: var(--text-field-placeholder);
  font-weight: 400;
}
.input:hover:not(:disabled) {
  border-color: var(--field-border-hover);
  background: var(--field-bg-hover);
  box-shadow: 0 6px 16px rgba(18, 77, 91, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.78);
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  background: var(--field-bg-hover);
  box-shadow: 0 0 0 3px var(--accent-ring), 0 8px 20px rgba(16, 122, 115, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.input.is-invalid {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px rgba(251, 133, 133, 0.18);
}
.input:disabled {
  background: rgba(22, 103, 119, 0.08);
  border-color: rgba(43, 101, 116, 0.28);
  color: var(--text-disabled);
  cursor: not-allowed;
}
</style>
