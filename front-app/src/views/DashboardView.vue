<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { ArrowRight, Brain, Settings, Sparkles, Workflow } from "lucide-vue-next";
import AgentSummaryCard from "@/components/AgentSummaryCard.vue";
import ConfigPathDrawer from "@/components/ConfigPathDrawer.vue";
import { useAgentsStore } from "@/stores/agents";
import { useProvidersStore } from "@/stores/providers";
import { useUsageStore } from "@/stores/usage";
import { useAppStore } from "@/stores/app";
import { agentDisplayName } from "@/utils/format";
import type { AgentType } from "@/types/api";

const agentsStore = useAgentsStore();
const providersStore = useProvidersStore();
const usageStore = useUsageStore();
const appStore = useAppStore();

const configDrawer = ref<{ open: boolean; agentType: AgentType }>({ open: false, agentType: "codex" });

function openConfig(agentType: AgentType) {
  configDrawer.value = { open: true, agentType };
}

const agentCodes: AgentType[] = ["codex", "claude_code"];

const agentCards = computed(() =>
  agentCodes.map((type) => ({
    agent: agentsStore.agents[type],
    providers: providersStore.providers[type],
    usageMap: usageStore.usage[type],
    configCheck: agentsStore.configChecks[type],
  })),
);

function agentRoute(agentType: AgentType): string {
  return agentType === "claude_code" ? "/agents/claude-code" : "/agents/codex";
}

async function refreshDashboard() {
  await appStore.checkHealth();
  if (!appStore.online) return;
  await agentsStore.refresh();
  await Promise.all([
    providersStore.refresh("codex"),
    providersStore.refresh("claude_code"),
    agentsStore.configCheck("codex"),
    agentsStore.configCheck("claude_code"),
    usageStore.refresh("codex"),
    usageStore.refresh("claude_code"),
  ]);
}

async function resetUsage(agentType: AgentType, providerId: string) {
  const confirmed = window.confirm(`确认清零 ${agentDisplayName[agentType]} 当前 Provider 的 Token 用量统计？`);
  if (!confirmed) return;
  try {
    await usageStore.reset(agentType, providerId);
    appStore.pushToast({ level: "success", title: `${agentDisplayName[agentType]} 用量已清零` });
  } catch (e) {
    appStore.notifyError(e, "清零失败");
  }
}

async function recheckConfig(agentType: AgentType) {
  try {
    await agentsStore.configCheck(agentType);
    appStore.pushToast({ level: "success", title: `校验已刷新 (${agentDisplayName[agentType]})` });
  } catch (e) {
    appStore.notifyError(e, "重新校验失败");
  }
}

onMounted(() => {
  refreshDashboard().catch((e) => appStore.notifyError(e, "Dashboard 刷新失败"));
});
</script>

<template>
  <div class="dashboard">
    <header class="page-hero">
      <div class="hero-copy">
        <div class="eyebrow"><Sparkles :size="14" /> Local AI Gateway</div>
        <h1>Dashboard</h1>
        <p class="page-subtitle">
          用一个更清晰的控制台管理 Codex 和 Claude Code 的 API 提供商配置、密钥以及本地代理网关。
        </p>
      </div>
      <div class="hero-orb" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </header>

    <div class="agent-grid">
      <div v-for="card in agentCards" :key="card.agent?.agent_type" class="card-col">
        <template v-if="card.agent">
          <AgentSummaryCard
            :agent="card.agent"
            :providers="card.providers"
            :usage-map="card.usageMap"
            :config-check="card.configCheck"
            :key="card.agent.updated_at ?? card.agent.agent_type"
            @open="$router.push(agentRoute(card.agent!.agent_type))"
            @configure="openConfig(card.agent!.agent_type)"
            @recheck="recheckConfig(card.agent!.agent_type)"
            @reset-usage="(providerId) => resetUsage(card.agent!.agent_type, providerId)"
            @probe="
              agentsStore.probe(card.agent!.agent_type).then(() => agentsStore.configCheck(card.agent!.agent_type)).then(() => {
                appStore.pushToast({ level: 'success', title: `探测完成 (${agentDisplayName[card.agent!.agent_type]})` });
              }).catch((e) => appStore.notifyError(e, '探测失败'))
            "
          />
        </template>
        <div v-else class="skeleton-card">
          <div class="skeleton h4 w-60" />
          <div class="skeleton h3 w-80" />
          <div class="skeleton h-32" />
        </div>
      </div>
    </div>

    <div class="quick-links">
      <RouterLink to="/agents/codex" class="link-card">
        <span class="link-icon"><Workflow :size="18" /></span>
        <span class="link-text">
          <strong>管理 Codex Providers</strong>
          <small>配置 Responses 代理与模型</small>
        </span>
        <ArrowRight :size="15" />
      </RouterLink>
      <RouterLink to="/agents/claude-code" class="link-card">
        <span class="link-icon"><Brain :size="18" /></span>
        <span class="link-text">
          <strong>管理 Claude Code Providers</strong>
          <small>维护 Anthropic 环境配置</small>
        </span>
        <ArrowRight :size="15" />
      </RouterLink>
      <RouterLink to="/settings" class="link-card">
        <span class="link-icon"><Settings :size="18" /></span>
        <span class="link-text">
          <strong>系统设置</strong>
          <small>查看缓存、状态与安全提示</small>
        </span>
        <ArrowRight :size="15" />
      </RouterLink>
    </div>

    <ConfigPathDrawer
      v-if="configDrawer.agentType && agentsStore.agents[configDrawer.agentType]"
      :open="configDrawer.open"
      :agent-type="configDrawer.agentType"
      :agent="agentsStore.agents[configDrawer.agentType]!"
      @update:open="configDrawer.open = $event"
    />
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1440px;
  margin: 0 auto;
}
.page-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
  padding: 24px 26px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(135deg, rgba(251, 254, 255, 0.8), rgba(220, 243, 246, 0.55)),
    var(--bg-card);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
}
.page-hero::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(16, 122, 115, 0.5), rgba(40, 111, 159, 0.28), transparent);
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--accent);
  font-size: 13.5px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.page-hero h1 {
  font-size: clamp(30px, 3.2vw, 42px);
  line-height: 1.12;
  font-weight: 800;
  margin: 0 0 10px;
  letter-spacing: 0;
}
.page-subtitle {
  margin: 0;
  font-size: 15.5px;
  color: var(--text-secondary);
  max-width: 66ch;
}
.hero-orb {
  position: relative;
  flex: 0 0 150px;
  height: 120px;
}
.hero-orb span {
  position: absolute;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-glow);
  background: linear-gradient(135deg, var(--accent-soft), rgba(251, 254, 255, 0.72));
  box-shadow: var(--shadow-glow);
  animation: floaty 5s ease-in-out infinite;
}
.hero-orb span:nth-child(1) { width: 92px; height: 92px; right: 16px; top: 4px; }
.hero-orb span:nth-child(2) { width: 48px; height: 48px; right: 95px; top: 42px; animation-delay: -1.4s; background: linear-gradient(135deg, var(--info-soft), rgba(251, 254, 255, 0.72)); }
.hero-orb span:nth-child(3) { width: 32px; height: 32px; right: 62px; top: 84px; animation-delay: -2.5s; background: linear-gradient(135deg, var(--violet-soft), rgba(251, 254, 255, 0.74)); }
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 22px;
}
.card-col {
  min-width: 0;
}
.quick-links {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.link-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 15px 16px;
  background:
    linear-gradient(145deg, var(--panel-lighter), transparent 42%),
    var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  font-size: 14.5px;
  color: var(--text-secondary);
  transition: color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-soft);
}
.link-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--accent);
  background: var(--accent-soft);
  border: 1px solid var(--border-glow);
}
.link-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.link-text strong {
  color: var(--text-primary);
  font-size: 14.5px;
}
.link-text small {
  color: var(--text-tertiary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.link-card:hover {
  color: var(--accent);
  border-color: var(--border-glow);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md), var(--shadow-glow);
}
.link-card:hover :deep(svg:last-child) {
  transform: translateX(2px);
}

.skeleton-card {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-md);
}
.skeleton { border-radius: var(--radius-sm); }
.h4 { height: 16px; width: 50%; }
.h3 { height: 12px; width: 70%; }
.h-32 { height: 120px; }

@keyframes floaty {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-8px) scale(1.04); }
}

@media (max-width: 1100px) {
  .quick-links {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .page-hero {
    padding: 20px;
  }
  .hero-orb {
    display: none;
  }
  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
