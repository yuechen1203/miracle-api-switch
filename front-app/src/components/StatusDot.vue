<script setup lang="ts">
import { computed } from "vue";
import type { AgentStatus, ProxyStatus } from "@/types/api";

type Tone = "ok" | "warn" | "danger" | "muted" | "info";

const props = defineProps<{
  status?: AgentStatus | ProxyStatus | string;
  label?: string;
  tone?: Tone;
}>();

const inferredTone = computed<Tone>(() => {
  if (props.tone) return props.tone;
  switch (props.status) {
    case "installed":
    case "running":
      return "ok";
    case "missing":
    case "starting":
      return "warn";
    case "invalid":
    case "error":
      return "danger";
    case "uninitialized":
    case "stopped":
      return "muted";
    default:
      return "info";
  }
});

const defaultLabel = computed(() => {
  switch (props.status) {
    case "installed":
      return "已安装";
    case "missing":
      return "未安装";
    case "invalid":
      return "配置异常";
    case "uninitialized":
      return "未初始化";
    case "running":
      return "运行中";
    case "starting":
      return "启动中";
    case "stopped":
      return "未运行";
    case "error":
      return "异常";
    default:
      return props.status || "-";
  }
});
</script>

<template>
  <span class="dot-wrap" :class="`tone-${inferredTone}`">
    <span class="dot" :aria-hidden="true">
      <span class="dot-inner" />
    </span>
    <span class="dot-label">{{ props.label ?? defaultLabel }}</span>
  </span>
</template>

<style scoped>
.dot-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 650;
  color: var(--text-secondary);
  white-space: nowrap;
}
.dot {
  position: relative;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.dot::after {
  content: "";
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1px solid currentColor;
  opacity: 0.24;
}
.dot-inner {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 12px currentColor;
}
.tone-ok    { color: var(--ok); }
.tone-warn  { color: var(--warn); }
.tone-danger{ color: var(--danger); }
.tone-muted { color: var(--text-disabled); }
.tone-info  { color: var(--info); }
.dot-label  { color: var(--text-secondary); }
.tone-ok .dot-inner    { animation: pulse 2.4s ease-in-out infinite; }
.tone-warn .dot-inner  { animation: pulse 2.4s ease-in-out infinite; }
.tone-danger .dot-inner{ animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50%      { box-shadow: 0 0 0 5px transparent; }
}
</style>
