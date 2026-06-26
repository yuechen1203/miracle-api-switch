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
    <svg viewBox="0 0 44 44" :width="props.size" :height="props.size" aria-hidden="true">
      <defs>
        <linearGradient id="lm-stroke" x1="4" y1="4" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="var(--accent)" />
          <stop offset="48%" stop-color="var(--info)" />
          <stop offset="100%" stop-color="var(--violet)" />
        </linearGradient>
        <radialGradient id="lm-core" cx="50%" cy="42%" r="68%">
          <stop offset="0%" stop-color="var(--bg-elev)" />
          <stop offset="34%" stop-color="var(--accent)" />
          <stop offset="100%" stop-color="var(--accent-soft)" />
        </radialGradient>
        <filter id="lm-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <circle cx="22" cy="22" r="18.5" class="outer-ring" />
      <path d="M10 23 C14 12 30 12 34 23" class="arc arc-top" />
      <path d="M10 21 C14 32 30 32 34 21" class="arc arc-bottom" />
      <path d="M12 22 H18 M26 22 H32 M22 12 V18 M22 26 V32" class="switch-lines" />
      <circle cx="22" cy="22" r="5.6" class="core" />
      <circle cx="12" cy="22" r="2.6" class="node" />
      <circle cx="22" cy="12" r="2.6" class="node" />
      <circle cx="32" cy="22" r="2.6" class="node" />
      <circle cx="22" cy="32" r="2.6" class="node" />
      <circle class="traveler" cx="12" cy="22" r="1.7" />
    </svg>
  </span>
</template>

<style scoped>
.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  isolation: isolate;
}
.logo-mark::before,
.logo-mark::after {
  content: "";
  position: absolute;
  inset: -26%;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(16, 122, 115, 0.28), transparent 62%);
  opacity: 0.62;
  filter: blur(8px);
  z-index: -1;
  transform: scale(0.92);
}
.logo-mark::after {
  inset: 4%;
  background: linear-gradient(135deg, rgba(16, 122, 115, 0.16), rgba(40, 111, 159, 0.14));
  filter: none;
  opacity: 0.8;
  border: 1px solid var(--border-soft);
}
.logo-mark svg {
  display: block;
  filter: drop-shadow(0 10px 22px rgba(16, 122, 115, 0.16));
}
.outer-ring {
  fill: var(--panel-light);
  stroke: url(#lm-stroke);
  stroke-width: 1.25;
  opacity: 0.92;
}
.arc,
.switch-lines {
  fill: none;
  stroke: url(#lm-stroke);
  stroke-width: 1.55;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.arc-bottom {
  opacity: 0.72;
}
.switch-lines {
  opacity: 0.72;
}
.core {
  fill: url(#lm-core);
  filter: url(#lm-glow);
}
.node {
  fill: var(--bg-page);
  stroke: var(--accent);
  stroke-width: 1.45;
}
.traveler {
  fill: #fffaf6;
  opacity: 0;
  filter: url(#lm-glow);
}
.logo-mark.running::before {
  animation: logoHalo 2.8s ease-in-out infinite;
}
.logo-mark.running .traveler {
  animation: orbit 2.8s linear infinite;
  opacity: 1;
}
.logo-mark.running .outer-ring {
  animation: ringBreathe 3.4s ease-in-out infinite;
}
.logo-mark.offline::before {
  opacity: 0.16;
  background: radial-gradient(circle, rgba(43, 101, 116, 0.22), transparent 62%);
}
.logo-mark.offline svg {
  filter: saturate(0.25) opacity(0.62);
}

@keyframes orbit {
  0%   { cx: 12; cy: 22; opacity: 1; }
  25%  { cx: 22; cy: 12; opacity: 1; }
  50%  { cx: 32; cy: 22; opacity: 1; }
  75%  { cx: 22; cy: 32; opacity: 1; }
  100% { cx: 12; cy: 22; opacity: 1; }
}
@keyframes ringBreathe {
  0%, 100% { opacity: 0.72; stroke-width: 1.15; }
  50%      { opacity: 1; stroke-width: 1.65; }
}
@keyframes logoHalo {
  0%, 100% { opacity: 0.36; transform: scale(0.88); }
  50%      { opacity: 0.8; transform: scale(1.05); }
}
</style>
