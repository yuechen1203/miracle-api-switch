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
  background: var(--panel-light);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  padding: 3px;
  gap: 3px;
  width: 100%;
  box-shadow: inset 0 1px 0 var(--panel-light);
}
.seg-btn {
  flex: 1;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 13.5px;
  height: 29px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
}
.seg-btn:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--panel-light);
}
.seg-btn.active {
  background: linear-gradient(135deg, var(--accent-soft), rgba(251, 254, 255, 0.72));
  color: var(--accent);
  border-color: var(--border-glow);
  box-shadow: 0 8px 18px rgba(16, 122, 115, 0.1);
}
.seg.disabled .seg-btn {
  cursor: not-allowed;
}
</style>
