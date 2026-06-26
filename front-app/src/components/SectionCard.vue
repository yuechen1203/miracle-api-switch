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
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.105), var(--panel-light) 38%),
    var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
  position: relative;
}
.section-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(16, 122, 115, 0.38), rgba(40, 111, 159, 0.22), transparent);
  opacity: 0.9;
}
.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 19px;
  border-bottom: 1px solid var(--border-soft);
  background: linear-gradient(180deg, var(--panel-light), rgba(255, 255, 255, 0));
}
.head-text h3 {
  font-size: 15px;
  font-weight: 800;
  margin: 0;
  letter-spacing: 0;
  color: var(--text-primary);
}
.head-sub {
  font-size: 13.5px;
  color: var(--text-tertiary);
  margin: 5px 0 0;
}
.head-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}
.section-body.padded {
  padding: 18px 19px;
}
</style>
