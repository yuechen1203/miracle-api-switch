<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { ArrowRight } from "lucide-vue-next";
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
    <header class="page-header">
      <h1>Dashboard</h1>
      <p class="page-subtitle">
        管理 Codex 和 Claude Code 的 API 提供商配置、密钥以及本地代理网关。
      </p>
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
        <span>管理 Codex Providers</span>
        <ArrowRight :size="14" />
      </RouterLink>
      <RouterLink to="/agents/claude-code" class="link-card">
        <span>管理 Claude Code Providers</span>
        <ArrowRight :size="14" />
      </RouterLink>
      <RouterLink to="/settings" class="link-card">
        <span>系统设置</span>
        <ArrowRight :size="14" />
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
.page-header {
  margin-bottom: 22px;
}
.page-header h1 {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 6px;
}
.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 65ch;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
  margin-bottom: 22px;
}
.card-col {
  min-width: 0;
}
.quick-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.link-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  transition: color 120ms ease, border-color 120ms ease;
}
.link-card:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.skeleton-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton { border-radius: var(--radius-sm); }
.h4 { height: 16px; width: 50%; }
.h3 { height: 12px; width: 70%; }
.h-32 { height: 100px; }

@media (max-width: 900px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
