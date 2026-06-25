<script setup lang="ts">
defineProps<{ title?: string; subtitle?: string; padded?: boolean }>();
</script>

<template>
  <section class="section-card">
    <header v-if="title || $slots.title || $slots.actions" class="section-head">
      <div class="head-text">
        <h3>
          <slot name="title">{{ title }}</slot>
        </h3>
        <p v-if="subtitle || $slots.subtitle" class="head-sub">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>
      <div v-if="$slots.actions" class="head-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="section-body" :class="{ padded }">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-soft);
}
.head-text h3 {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
}
.head-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 4px 0 0;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-body.padded {
  padding: 16px 18px;
}
</style>
