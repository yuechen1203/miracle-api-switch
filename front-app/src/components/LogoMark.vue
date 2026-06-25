<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{ size?: number; running?: boolean; offline?: boolean }>(),
  { size: 28, running: false, offline: false },
);

const dim = computed(() => `${props.size}px`);
</script>

<template>
  <span
    class="logo-mark"
    :class="{ running: props.running, offline: props.offline }"
    :style="{ width: dim, height: dim }"
  >
    <svg viewBox="0 0 40 40" :width="props.size" :height="props.size" aria-hidden="true">
      <defs>
        <linearGradient id="lm-stroke" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="var(--accent)" />
          <stop offset="100%" stop-color="var(--info)" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="18" class="ring" />
      <circle cx="8" cy="20" r="2.6" class="node" />
      <circle cx="32" cy="20" r="2.6" class="node" />
      <path d="M8 20 L20 10 L32 20 L20 30 Z" class="path" />
      <circle class="pulse" cx="8" cy="20" r="1.4" />
    </svg>
  </span>
</template>

<style scoped>
.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.logo-mark svg .ring {
  fill: none;
  stroke: var(--border-strong);
  stroke-width: 1;
  opacity: 0.6;
}
.logo-mark svg .node {
  fill: var(--accent);
}
.logo-mark svg .path {
  fill: none;
  stroke: url(#lm-stroke);
  stroke-width: 1.6;
  stroke-linejoin: round;
}
.logo-mark svg .pulse {
  fill: var(--accent);
  opacity: 0;
}
.logo-mark.running svg .pulse {
  animation: travel 2.4s linear infinite;
}
.logo-mark.running svg .ring {
  animation: breathe 3.2s ease-in-out infinite;
}
.logo-mark.offline svg .node,
.logo-mark.offline svg .path {
  filter: grayscale(1);
  opacity: 0.55;
}

@keyframes travel {
  0%   { cx: 8; cy: 20; opacity: 1; }
  25%  { cx: 20; cy: 10; opacity: 1; }
  50%  { cx: 32; cy: 20; opacity: 1; }
  75%  { cx: 20; cy: 30; opacity: 1; }
  100% { cx: 8; cy: 20; opacity: 1; }
}
@keyframes breathe {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 0.85; }
}
</style>
