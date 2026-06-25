<script setup lang="ts">
const props = defineProps<{
  modelValue: string | null;
  options: { value: string; label: string; hint?: string }[];
  disabled?: boolean;
}>();
const emit = defineEmits<{ (e: "update:modelValue", value: string): void }>();
function select(value: string) {
  if (props.disabled) return;
  emit("update:modelValue", value);
}
</script>

<template>
  <div class="seg" :class="{ disabled: props.disabled }" role="radiogroup">
    <button
      v-for="opt in props.options"
      :key="opt.value"
      type="button"
      class="seg-btn"
      :class="{ active: props.modelValue === opt.value }"
      :title="opt.hint"
      :disabled="props.disabled"
      @click="select(opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
  width: 100%;
}
.seg-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.seg-btn:hover:not(:disabled) {
  color: var(--text-primary);
}
.seg-btn.active {
  background: var(--bg-surface-3);
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px var(--border-strong);
}
.seg.disabled .seg-btn {
  cursor: not-allowed;
}
</style>
