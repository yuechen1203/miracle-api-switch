<script setup lang="ts">
import { computed } from "vue";
import SectionCard from "@/components/SectionCard.vue";
import AppButton from "@/components/AppButton.vue";
import InfoTip from "@/components/InfoTip.vue";
import { useAppStore } from "@/stores/app";
import { useAgentsStore } from "@/stores/agents";
import { useProvidersStore } from "@/stores/providers";
import { useUsageStore } from "@/stores/usage";

const appStore = useAppStore();
const agentsStore = useAgentsStore();
const providersStore = useProvidersStore();
const usageStore = useUsageStore();

async function refreshAll() {
  await appStore.checkHealth();
  await agentsStore.refresh();
  await Promise.all([
    providersStore.refresh("codex"),
    providersStore.refresh("claude_code"),
    usageStore.refresh("codex"),
    usageStore.refresh("claude_code"),
  ]);
  appStore.pushToast({ level: "success", title: "已重新加载后端数据" });
}

const totals = computed(() => {
  const both = [
    ...providersStore.providers.codex,
    ...providersStore.providers.claude_code,
  ];
  return {
    providers: both.length,
    proxyEnabled: both.filter((p) => p.proxy_enabled).length,
    proxyRunning: both.filter((p) => p.proxy_status?.status === "running").length,
  };
});
</script>

<template>
  <div class="settings">
    <header class="page-header">
      <h1>Settings</h1>
      <p class="page-subtitle">
        本地工具，不上报数据。所有 provider 与代理状态保存在
        <span class="mono">.hyc_cache/</span> 目录。
      </p>
    </header>

    <SectionCard title="后端信息" padded>
      <dl class="kv">
        <div>
          <dt>地址</dt>
          <dd class="mono">/api → http://127.0.0.1:8765</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>
            <span :class="appStore.online ? 'tone-ok' : 'tone-danger'">
              {{ appStore.online ? "在线" : "离线" }}
            </span>
          </dd>
        </div>
        <div>
          <dt>版本</dt>
          <dd class="mono">{{ appStore.health?.version || "-" }}</dd>
        </div>
        <div>
          <dt>启动时间</dt>
          <dd class="mono">{{ appStore.health?.started_at || "-" }}</dd>
        </div>
        <div>
          <dt>缓存目录</dt>
          <dd class="mono">{{ appStore.health?.cache_dir || ".hyc_cache" }}</dd>
        </div>
        <div>
          <dt>工作目录</dt>
          <dd class="mono">{{ appStore.health?.workspace_root || "-" }}</dd>
        </div>
      </dl>
    </SectionCard>

    <SectionCard title="使用概览" padded>
      <div class="kpi">
        <div>
          <span class="kpi-num mono">{{ totals.providers }}</span>
          <span class="kpi-label">已保存 Provider</span>
        </div>
        <div>
          <span class="kpi-num mono">{{ totals.proxyEnabled }}</span>
          <span class="kpi-label">开启代理</span>
        </div>
        <div>
          <span class="kpi-num mono">{{ totals.proxyRunning }}</span>
          <span class="kpi-label">代理运行中</span>
        </div>
      </div>
    </SectionCard>

    <SectionCard title="安全提示" padded>
      <template #actions>
        <InfoTip title="安全与代理注意事项" label="注意">
          <ul class="tip-list">
            <li>API Key 默认脱敏展示，编辑时留空表示不修改原值。</li>
            <li>本地代理 URL 固定为 <span class="mono">http://127.0.0.1:{port}</span>，不会自动配置 HTTPS。</li>
            <li>切换 provider 会改写 Codex/Claude Code 配置文件，后端会自动备份到 <span class="mono">.hyc_cache/backups/</span>。</li>
            <li>代理支持基础文本流式转换，工具调用、reasoning、多模态流事件暂不保证无损。</li>
          </ul>
        </InfoTip>
      </template>
      <p class="compact-note">密钥、配置写入和代理转换限制请查看右上角提示。</p>
    </SectionCard>

    <SectionCard title="操作" padded>
      <div class="actions">
        <AppButton variant="primary" @click="refreshAll">重新加载后端数据</AppButton>
      </div>
    </SectionCard>
  </div>
</template>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1120px;
  margin: 0 auto;
}
.page-header {
  position: relative;
  overflow: hidden;
  padding: 21px 23px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(135deg, rgba(251, 254, 255, 0.8), rgba(220, 243, 246, 0.55)),
    var(--bg-card);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
}
.page-header::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(40, 111, 159, 0.38), rgba(16, 122, 115, 0.34), transparent);
}
.page-header h1 {
  margin: 0;
  font-size: clamp(25px, 2.2vw, 34px);
  font-weight: 800;
  letter-spacing: 0;
}
.page-subtitle {
  margin: 7px 0 0;
  color: var(--text-secondary);
  font-size: 15px;
  max-width: 72ch;
}
.kv {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}
.kv > div {
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  background: var(--panel-light);
}
.kv dt {
  font-size: 12.5px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0;
}
.kv dd {
  margin: 6px 0 0;
  font-size: 14.5px;
  color: var(--text-primary);
  word-break: break-all;
}
.kpi {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.kpi > div {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(135deg, var(--accent-soft), rgba(251, 254, 255, 0.68)),
    var(--panel-light);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: inset 0 1px 0 var(--panel-light);
}
.kpi > div::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--accent-strong), var(--accent));
}
.kpi-num {
  font-size: 29px;
  color: var(--accent);
  font-weight: 800;
  letter-spacing: 0;
}
.kpi-label {
  color: var(--text-tertiary);
  font-size: 13.5px;
}
.compact-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  padding: 14px 15px;
  border: 1px dashed rgba(71, 106, 159, 0.34);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(71, 106, 159, 0.1), var(--panel-light));
}
.tip-list {
  margin: 0;
  padding-left: 16px;
}
.tip-list li + li {
  margin-top: 4px;
}
.tone-ok { color: var(--ok); font-weight: 700; }
.tone-danger { color: var(--danger); font-weight: 700; }
.mono { font-family: var(--font-mono); }
.actions { display: flex; gap: 8px; }
@media (max-width: 760px) {
  .kv,
  .kpi {
    grid-template-columns: 1fr;
  }
}
</style>
