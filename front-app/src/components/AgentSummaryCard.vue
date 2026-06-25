<script setup lang="ts">
import { computed } from "vue";
import { ChevronRight, FolderCog, RefreshCcw, RotateCcw } from "lucide-vue-next";
import StatusDot from "@/components/StatusDot.vue";
import { agentDisplayName, ellipsizeMiddle } from "@/utils/format";
import type { AgentInfo, ConfigCheckResult, Provider, UsageRecord } from "@/types/api";

const props = defineProps<{
  agent: AgentInfo;
  providers: Provider[];
  usageMap: Record<string, UsageRecord>;
  configCheck: ConfigCheckResult | null;
}>();
const emit = defineEmits<{
  (e: "open"): void;
  (e: "configure"): void;
  (e: "probe"): void;
  (e: "recheck"): void;
  (e: "resetUsage", providerId: string): void;
}>();

const currentProvider = computed(() =>
  props.providers.find((p) => p.id === props.agent.current_provider_id),
);

const currentProxyStatus = computed(() => currentProvider.value?.proxy_status?.status || "stopped");
const currentProxyEnabled = computed(() => !!currentProvider.value?.proxy_enabled);
const showUsage = computed(() => currentProxyEnabled.value);
const currentUsage = computed(() => {
  const providerId = currentProvider.value?.id;
  if (providerId && props.usageMap[providerId]) return props.usageMap[providerId];
  return {
    request_count: 0,
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
    last_request_at: null,
  };
});

const proxyBadgeClass = computed(() => {
  if (!currentProvider.value) return "neutral";
  if (!currentProxyEnabled.value) return "off";
  if (currentProxyStatus.value === "running") return "on";
  if (currentProxyStatus.value === "error") return "error";
  return "warn";
});

const proxyBadgeText = computed(() => {
  if (!currentProvider.value) return "未初始化";
  if (!currentProxyEnabled.value) return "未开启";
  if (currentProxyStatus.value === "running") return `已开启 · 运行中${currentProvider.value.proxy_port ? ` :${currentProvider.value.proxy_port}` : ""}`;
  if (currentProxyStatus.value === "error") return "已开启 · 异常";
  return `已开启 · 未运行${currentProvider.value.proxy_port ? ` :${currentProvider.value.proxy_port}` : ""}`;
});

const checkClass = computed(() => {
  if (!props.configCheck || props.configCheck.status === "not_initialized") return "check-muted";
  if (props.configCheck.status === "matched") return "check-ok";
  return "check-warn";
});

const checkTitle = computed(() => {
  if (!props.configCheck) return "等待校准";
  if (props.configCheck.status === "not_initialized") return "未初始化";
  if (props.configCheck.status === "matched") return "Check 通过";
  if (props.configCheck.status === "unavailable") return "无法校准";
  return "配置发生改动";
});

function format(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
</script>

<template>
  <article class="agent-card">
    <header class="agent-head">
      <div class="agent-name">
        <span class="agent-mono">{{ props.agent.agent_type }}</span>
        <h3>{{ agentDisplayName[props.agent.agent_type] }}</h3>
      </div>
      <StatusDot :status="props.agent.status" />
    </header>

    <dl class="meta">
      <div>
        <dt>配置文件</dt>
        <dd class="path mono" :title="props.agent.resolved_config_file ?? props.agent.config_path ?? '-'">
          {{ props.agent.resolved_config_file || props.agent.config_path || "未设置" }}
        </dd>
      </div>
      <div>
        <dt>当前 Provider</dt>
        <dd>
          <span v-if="currentProvider" class="current-tag">
            {{ currentProvider.display_name }}
          </span>
          <span v-else class="muted">未初始化</span>
        </dd>
      </div>
      <div>
        <dt>本地代理</dt>
        <dd>
          <span class="proxy-badge" :class="proxyBadgeClass">{{ proxyBadgeText }}</span>
        </dd>
      </div>
    </dl>

    <div class="check-panel" :class="checkClass">
      <div class="check-head">
        <div class="check-copy">
          <strong>{{ checkTitle }}</strong>
          <span>{{ props.configCheck?.message || "正在等待后端校准配置文件" }}</span>
        </div>
        <button class="check-action" title="重新校验配置文件" @click="emit('recheck')">
          <RefreshCcw :size="12" /> 重新校验
        </button>
      </div>
      <div class="config-grid">
        <div>
          <span>URL</span>
          <code :title="props.configCheck?.current_config.base_url || '-'">
            {{ ellipsizeMiddle(props.configCheck?.current_config.base_url || "-", 26, 8) }}
          </code>
        </div>
        <div>
          <span>Provider</span>
          <code :title="props.configCheck?.current_config.model_provider || '-'">
            {{ ellipsizeMiddle(props.configCheck?.current_config.model_provider || "-", 18, 6) }}
          </code>
        </div>
        <div>
          <span>API Key</span>
          <code>{{ props.configCheck?.current_config.api_key_masked || "-" }}</code>
        </div>
        <div>
          <span>Model</span>
          <code :title="props.configCheck?.current_config.model || '-'">
            {{ ellipsizeMiddle(props.configCheck?.current_config.model || "-", 24, 8) }}
          </code>
        </div>
      </div>
    </div>

    <div v-if="showUsage" class="usage-wrap">
      <div class="usage-head">
        <span>Token 用量</span>
        <button
          class="reset-usage"
          title="清零当前 Provider 的 Token 统计"
          @click="currentProvider && emit('resetUsage', currentProvider.id)"
        >
          <RotateCcw :size="12" /> 清零
        </button>
      </div>
      <div class="usage">
        <div class="usage-cell">
          <span class="usage-num mono">{{ format(currentUsage.request_count) }}</span>
          <span class="usage-label">请求</span>
        </div>
        <div class="usage-cell">
          <span class="usage-num mono">{{ format(currentUsage.input_tokens) }}</span>
          <span class="usage-label">输入 token</span>
        </div>
        <div class="usage-cell">
          <span class="usage-num mono">{{ format(currentUsage.output_tokens) }}</span>
          <span class="usage-label">输出 token</span>
        </div>
        <div class="usage-cell total">
          <span class="usage-num mono">{{ format(currentUsage.total_tokens) }}</span>
          <span class="usage-label">合计 token</span>
        </div>
      </div>
    </div>

    <footer class="card-actions">
      <button class="ghost" @click="emit('configure')">
        <FolderCog :size="13" /> 配置路径
      </button>
      <button class="ghost" @click="emit('probe')">
        <RefreshCcw :size="13" /> 重新探测
      </button>
      <button class="primary" @click="emit('open')">
        进入配置 <ChevronRight :size="14" />
      </button>
    </footer>
  </article>
</template>

<style scoped>
.agent-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  overflow: hidden;
}
.agent-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, var(--accent), var(--info));
  opacity: 0.7;
}
.agent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.agent-name h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.agent-mono {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}
.meta {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin: 0;
}
.meta dt {
  font-size: 11.5px;
  color: var(--text-tertiary);
}
.meta dd {
  margin: 2px 0 0;
  font-size: 13px;
}
.path {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.muted {
  color: var(--text-tertiary);
}
.current-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.proxy-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 2px 8px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.proxy-badge.on {
  color: var(--ok);
  background: var(--ok-soft);
  border-color: rgba(92, 210, 155, 0.35);
}
.proxy-badge.warn {
  color: var(--warn);
  background: var(--warn-soft);
  border-color: rgba(246, 178, 90, 0.35);
}
.proxy-badge.error {
  color: var(--danger);
  background: var(--danger-soft);
  border-color: rgba(239, 106, 106, 0.35);
}
.proxy-badge.off,
.proxy-badge.neutral {
  color: var(--text-tertiary);
  background: var(--bg-surface-2);
}
.check-panel {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  background: var(--bg-surface-2);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.check-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  font-size: 12px;
}
.check-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.check-copy strong {
  white-space: nowrap;
}
.check-copy span {
  color: var(--text-tertiary);
}
.check-action {
  height: 24px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--border-strong);
  background: var(--bg-surface-2);
  color: var(--text-secondary);
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: 11px;
  padding: 0 7px;
}
.check-action:hover {
  color: var(--accent);
  border-color: rgba(54, 226, 196, 0.35);
}
.check-ok {
  border-color: rgba(92, 210, 155, 0.32);
}
.check-ok .check-head strong {
  color: var(--ok);
}
.check-warn {
  border-color: rgba(246, 178, 90, 0.35);
  background: var(--warn-soft);
}
.check-warn .check-head strong {
  color: var(--warn);
}
.check-muted .check-head strong {
  color: var(--text-tertiary);
}
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.config-grid div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.config-grid span {
  font-size: 10.5px;
  color: var(--text-tertiary);
}
.config-grid code {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.usage-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.usage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--text-tertiary);
}
.reset-usage {
  height: 24px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--border-strong);
  background: var(--bg-surface-2);
  color: var(--text-secondary);
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: 11px;
  padding: 0 7px;
}
.reset-usage:hover {
  color: var(--accent);
  border-color: rgba(54, 226, 196, 0.35);
}
.usage {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-soft);
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-soft);
}
.usage-cell {
  background: var(--bg-surface-2);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.usage-num {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}
.usage-label {
  font-size: 11px;
  color: var(--text-tertiary);
}
.usage-cell.total .usage-num {
  color: var(--accent);
}
.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}
.card-actions .ghost,
.card-actions .primary {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  height: 30px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--border-strong);
}
.card-actions .ghost {
  background: transparent;
  color: var(--text-secondary);
}
.card-actions .ghost:hover {
  color: var(--text-primary);
  background: var(--bg-surface-2);
}
.card-actions .primary {
  background: var(--accent);
  color: #06231f;
  border-color: var(--accent);
}
.card-actions .primary:hover {
  background: var(--accent-strong);
  border-color: var(--accent-strong);
}
</style>
