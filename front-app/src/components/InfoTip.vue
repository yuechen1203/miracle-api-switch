<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { AlertCircle } from "lucide-vue-next";

defineProps<{ label?: string; title?: string }>();

const open = ref(false);
const pinned = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const popoverRef = ref<HTMLElement | null>(null);
const popoverStyle = ref<Record<string, string>>({});
let closeTimer: number | undefined;

function updatePosition() {
  const trigger = triggerRef.value;
  if (!trigger) return;
  const rect = trigger.getBoundingClientRect();
  const width = Math.min(320, window.innerWidth - 16);
  const height = popoverRef.value?.offsetHeight ?? 0;
  const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8);
  const below = rect.bottom + 8;
  const above = rect.top - height - 8;
  const top = height > 0 && below + height > window.innerHeight - 8 && above >= 8 ? above : below;
  popoverStyle.value = {
    left: `${left}px`,
    top: `${Math.max(8, Math.min(top, window.innerHeight - height - 8))}px`,
    width: `${width}px`,
  };
}

function cancelClose() {
  if (closeTimer !== undefined) {
    window.clearTimeout(closeTimer);
    closeTimer = undefined;
  }
}

function showHover() {
  cancelClose();
  if (!open.value) {
    pinned.value = false;
    open.value = true;
  }
  nextTick(updatePosition);
}

function scheduleClose() {
  if (pinned.value) return;
  cancelClose();
  closeTimer = window.setTimeout(() => close(), 120);
}

function toggle() {
  cancelClose();
  if (open.value && pinned.value) {
    close();
    return;
  }
  pinned.value = true;
  open.value = true;
  nextTick(updatePosition);
}

function close() {
  cancelClose();
  open.value = false;
  pinned.value = false;
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as Node;
  if (triggerRef.value?.contains(target) || popoverRef.value?.contains(target)) return;
  close();
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape") close();
}

watch(open, (value) => {
  if (value) {
    window.addEventListener("click", handleDocumentClick);
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("keydown", handleEscape);
  } else {
    window.removeEventListener("click", handleDocumentClick);
    window.removeEventListener("resize", updatePosition);
    window.removeEventListener("scroll", updatePosition, true);
    window.removeEventListener("keydown", handleEscape);
  }
});

onBeforeUnmount(() => {
  close();
  window.removeEventListener("click", handleDocumentClick);
  window.removeEventListener("resize", updatePosition);
  window.removeEventListener("scroll", updatePosition, true);
  window.removeEventListener("keydown", handleEscape);
});
</script>

<template>
  <span class="info-tip">
    <button
      ref="triggerRef"
      type="button"
      class="info-trigger"
      :aria-label="label || title || '注意'"
      :aria-expanded="open"
      @click.stop="toggle"
      @mouseenter="showHover"
      @mouseleave="scheduleClose"
    >
      <AlertCircle :size="14" />
      <span v-if="label">{{ label }}</span>
    </button>
    <Teleport to="body">
      <div
        v-if="open"
        ref="popoverRef"
        class="info-popover"
        :style="popoverStyle"
        role="tooltip"
        @mouseenter="cancelClose"
        @mouseleave="scheduleClose"
        @click.stop
      >
        <strong v-if="title">{{ title }}</strong>
        <div class="info-content"><slot /></div>
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.info-tip {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.info-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--border-strong);
  background: linear-gradient(135deg, rgba(71, 106, 159, 0.12), var(--panel-light));
  color: var(--text-secondary);
  border-radius: 999px;
  height: 25px;
  padding: 0 8px;
  cursor: pointer;
  font-size: 12px;
  transition: color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.info-trigger:hover,
.info-trigger[aria-expanded="true"] {
  color: var(--warn);
  border-color: rgba(71, 106, 159, 0.46);
  background: var(--warn-soft);
  transform: translateY(-1px);
}
.info-popover {
  position: fixed;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px 13px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.07), transparent 36%),
    var(--bg-glass-strong);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  color: var(--text-secondary);
  font-size: 12.5px;
  line-height: 1.55;
  text-align: left;
  backdrop-filter: blur(18px);
}
.info-popover::before {
  content: "";
  position: absolute;
  top: -5px;
  left: 18px;
  width: 10px;
  height: 10px;
  background: var(--bg-glass-strong);
  border-left: 1px solid var(--border-strong);
  border-top: 1px solid var(--border-strong);
  transform: rotate(45deg);
}
.info-popover strong {
  color: var(--text-primary);
  font-size: 13px;
}
.info-content {
  display: block;
}
</style>
