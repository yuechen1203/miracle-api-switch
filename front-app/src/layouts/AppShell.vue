<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import {
  LayoutDashboard,
  Workflow,
  Brain,
  Settings,
  RefreshCw,
  Power,
} from "lucide-vue-next";
import LogoMark from "@/components/LogoMark.vue";
import AppToasts from "@/components/AppToasts.vue";
import { useAppStore } from "@/stores/app";
import { useAgentsStore } from "@/stores/agents";
import { useProvidersStore } from "@/stores/providers";
import { useUsageStore } from "@/stores/usage";

const appStore = useAppStore();
const agents = useAgentsStore();
const providers = useProvidersStore();
const usage = useUsageStore();

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/agents/codex", label: "Codex", icon: Workflow },
  { to: "/agents/claude-code", label: "Claude Code", icon: Brain },
  { to: "/settings", label: "Settings", icon: Settings },
];

const proxyRunningCount = computed(() => {
  let n = 0;
  for (const type of ["codex", "claude_code"] as const) {
    for (const p of providers.providers[type]) {
      if (p.proxy_status?.status === "running") n++;
    }
  }
  return n;
});

async function refreshAll() {
  await appStore.checkHealth();
  await agents.refresh();
  await Promise.all([
    providers.refresh("codex"),
    providers.refresh("claude_code"),
    usage.refresh("codex"),
    usage.refresh("claude_code"),
  ]);
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <LogoMark :running="proxyRunningCount > 0" :offline="!appStore.online" />
        <div class="brand-text">
          <div class="brand-name">miracle-api-switch</div>
          <div class="brand-sub mono">
            local · {{ appStore.health?.version ?? "0.1.0" }}
          </div>
        </div>
      </div>
      <div class="topbar-spacer" />
      <div class="topbar-status">
        <div class="status-pill" :class="appStore.online ? 'on' : 'off'">
          <Power :size="13" />
          <span>{{ appStore.online ? "Backend Online" : "Backend Offline" }}</span>
        </div>
        <div v-if="proxyRunningCount > 0" class="status-pill running">
          <span class="dot" /> {{ proxyRunningCount }} proxy running
        </div>
        <button class="icon-btn" title="Refresh" @click="refreshAll">
          <RefreshCw :size="14" />
        </button>
      </div>
    </header>

    <div class="layout">
      <nav class="sidebar">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :exact-active-class="'active'"
        >
          <component :is="item.icon" :size="15" />
          <span>{{ item.label }}</span>
        </RouterLink>
        <div class="nav-foot mono">
          <div>cache: <span class="hint">{{ appStore.health?.cache_dir ?? '.hyc_cache' }}</span></div>
        </div>
      </nav>
      <main class="content">
        <div v-if="!appStore.online" class="offline-banner">
          <div>
            <strong>无法连接后端服务</strong>
            <span class="hint">{{ appStore.lastHealthError || "请确认 back-app 已经在 127.0.0.1:8765 启动" }}</span>
          </div>
          <button class="icon-btn" @click="appStore.checkHealth()">重新连接</button>
        </div>
        <slot />
      </main>
    </div>
    <AppToasts />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100vh;
}
.topbar {
  height: var(--header-h);
  border-bottom: 1px solid var(--border-soft);
  background: rgba(7, 9, 12, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 14px;
  position: sticky;
  top: 0;
  z-index: 50;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-name {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.brand-sub {
  font-size: 11px;
  color: var(--text-tertiary);
}
.topbar-spacer { flex: 1; }
.topbar-status {
  display: flex;
  align-items: center;
  gap: 10px;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  padding: 4px 10px;
  background: var(--bg-surface-2);
  color: var(--text-secondary);
}
.status-pill.on {
  color: var(--ok);
  border-color: rgba(92, 210, 155, 0.35);
  background: var(--ok-soft);
}
.status-pill.off {
  color: var(--danger);
  border-color: rgba(239, 106, 106, 0.35);
  background: var(--danger-soft);
}
.status-pill.running {
  color: var(--accent);
  border-color: rgba(54, 226, 196, 0.35);
  background: var(--accent-soft);
}
.status-pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 3px rgba(54, 226, 196, 0.18);
  animation: pulse 2s ease-in-out infinite;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: var(--bg-surface-2);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 120ms ease, background 120ms ease;
  padding: 0;
}
.icon-btn:hover {
  background: var(--bg-surface-3);
  color: var(--text-primary);
}

.layout {
  flex: 1;
  display: grid;
  grid-template-columns: var(--nav-w) 1fr;
  min-height: 0;
}
.sidebar {
  border-right: 1px solid var(--border-soft);
  background: var(--bg-surface);
  padding: 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.nav-item:hover {
  background: var(--bg-surface-2);
  color: var(--text-primary);
}
.nav-item.active {
  background: var(--accent-soft);
  color: var(--accent);
}
.nav-item.active :deep(svg) { color: var(--accent); }

.nav-foot {
  margin-top: auto;
  font-size: 11px;
  color: var(--text-tertiary);
  padding: 8px 10px;
  word-break: break-all;
}

.content {
  padding: 22px 28px 40px;
  min-width: 0;
}
.offline-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--danger-soft);
  border: 1px solid rgba(239, 106, 106, 0.32);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  margin-bottom: 18px;
  color: var(--text-primary);
}
.offline-banner strong {
  display: block;
  font-size: 13px;
}
.offline-banner .hint {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 8px;
  }
  .nav-foot { display: none; }
  .nav-item { flex: 1; justify-content: center; }
  .content { padding: 16px; }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50%      { box-shadow: 0 0 0 4px transparent; }
}
</style>
