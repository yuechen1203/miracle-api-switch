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
        <LogoMark :running="proxyRunningCount > 0" :offline="!appStore.online" :size="34" />
        <div class="brand-text">
          <div class="brand-name">miracle-api-switch</div>
          <div class="brand-sub mono">
            local control plane · {{ appStore.health?.version ?? "0.1.0" }}
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
        <div class="nav-group">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="nav-item"
            :exact-active-class="'active'"
          >
            <span class="nav-icon"><component :is="item.icon" :size="15" /></span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
        <div class="nav-foot mono">
          <span class="foot-label">cache workspace</span>
          <div class="hint">{{ appStore.health?.cache_dir ?? '.hyc_cache' }}</div>
        </div>
      </nav>
      <main class="content">
        <transition name="banner">
          <div v-if="!appStore.online" class="offline-banner">
            <div class="offline-icon"><Power :size="16" /></div>
            <div>
              <strong>无法连接后端服务</strong>
              <span class="hint">{{ appStore.lastHealthError || "请确认 back-app 已经在 127.0.0.1:8765 启动" }}</span>
            </div>
            <button class="reconnect-btn" @click="appStore.checkHealth()">重新连接</button>
          </div>
        </transition>
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
  background:
    linear-gradient(90deg, rgba(251, 254, 255, 0.96), rgba(225, 244, 249, 0.92)),
    var(--bg-glass);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 18px;
  position: sticky;
  top: 0;
  z-index: 50;
  box-shadow: 0 14px 42px rgba(18, 77, 91, 0.12);
}
.topbar::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(16, 122, 115, 0.42), rgba(40, 111, 159, 0.26), transparent);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0;
  color: var(--text-primary);
}
.brand-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0;
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
  font-size: 13px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  padding: 6px 11px;
  background: var(--panel-light);
  color: var(--text-secondary);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}
.status-pill.on {
  color: var(--ok);
  border-color: rgba(116, 224, 173, 0.35);
  background: linear-gradient(135deg, var(--ok-soft), rgba(245, 249, 255, 0.1));
}
.status-pill.off {
  color: var(--danger);
  border-color: rgba(251, 133, 133, 0.35);
  background: linear-gradient(135deg, var(--danger-soft), rgba(245, 249, 255, 0.1));
}
.status-pill.running {
  color: var(--accent);
  border-color: var(--border-glow);
  background: linear-gradient(135deg, var(--accent-soft), rgba(251, 254, 255, 0.62));
}
.status-pill .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 3px var(--accent-soft);
  animation: pulse 2s ease-in-out infinite;
}
.icon-btn,
.reconnect-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: var(--panel-light);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
}
.icon-btn:hover,
.reconnect-btn:hover {
  background: var(--bg-surface-3);
  color: var(--text-primary);
  border-color: var(--border-glow);
  transform: translateY(-1px);
}
.reconnect-btn {
  height: 32px;
  padding: 0 12px;
  margin-left: auto;
  font-size: 13px;
}

.layout {
  flex: 1;
  display: grid;
  grid-template-columns: var(--nav-w) 1fr;
  min-height: 0;
}
.sidebar {
  border-right: 1px solid var(--border-soft);
  background:
    linear-gradient(180deg, rgba(251, 254, 255, 0.94), rgba(225, 244, 249, 0.82)),
    var(--bg-glass);
  backdrop-filter: blur(18px);
  padding: 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: inset -1px 0 0 rgba(43, 101, 116, 0.1);
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 11px;
  font-size: 14.5px;
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
}
.nav-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 9px;
  bottom: 9px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--accent-strong), var(--accent));
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  background: var(--panel-light);
  color: var(--text-tertiary);
  transition: color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out);
}
.nav-item:hover {
  background: var(--panel-lighter);
  color: var(--text-primary);
  transform: translateX(2px);
}
.nav-item:hover .nav-icon {
  color: var(--accent);
  background: var(--accent-soft);
}
.nav-item.active {
  background: linear-gradient(135deg, var(--accent-soft), rgba(251, 254, 255, 0.66));
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px var(--border-glow), 0 12px 24px rgba(16, 122, 115, 0.1);
}
.nav-item.active::before {
  opacity: 1;
  transform: translateX(0);
}
.nav-item.active .nav-icon { color: var(--accent); background: var(--accent-soft); }

.nav-foot {
  margin-top: auto;
  font-size: 12.5px;
  color: var(--text-tertiary);
  padding: 12px;
  word-break: break-all;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  background: var(--panel-light);
}
.foot-label {
  display: block;
  color: var(--text-secondary);
  margin-bottom: 4px;
  letter-spacing: 0;
  text-transform: uppercase;
  font-size: 11px;
}

.content {
  padding: 28px clamp(18px, 3vw, 42px) 48px;
  min-width: 0;
  position: relative;
}
.offline-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, var(--danger-soft), var(--bg-card));
  border: 1px solid rgba(182, 63, 63, 0.34);
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
  color: var(--text-primary);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(16px);
}
.offline-icon {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--danger-soft);
  color: var(--danger);
  border: 1px solid rgba(251, 133, 133, 0.3);
}
.offline-banner strong {
  display: block;
  font-size: 14px;
}
.offline-banner .hint {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.banner-enter-active,
.banner-leave-active {
  transition: opacity var(--duration-med) var(--ease-out), transform var(--duration-med) var(--ease-out);
}
.banner-enter-from,
.banner-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 900px) {
  .topbar {
    padding: 0 14px;
  }
  .brand-sub {
    display: none;
  }
  .topbar-status .status-pill span {
    display: none;
  }
  .layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 10px;
    border-right: none;
    border-bottom: 1px solid var(--border-soft);
  }
  .nav-group {
    flex: 1;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .nav-foot { display: none; }
  .nav-item { flex: 1; justify-content: center; min-width: 130px; }
  .nav-item:hover { transform: translateY(-1px); }
  .content { padding: 18px; }
  .offline-banner { align-items: flex-start; flex-wrap: wrap; }
  .reconnect-btn { margin-left: 46px; }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50%      { box-shadow: 0 0 0 4px transparent; }
}
</style>
