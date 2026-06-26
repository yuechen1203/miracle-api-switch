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
  background:
    linear-gradient(135deg, rgba(251, 254, 255, 0.78), rgba(220, 243, 246, 0.42)),
    linear-gradient(145deg, var(--panel-lighter), transparent 36%),
    var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 17px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(18px);
  transition: transform var(--duration-med) var(--ease-out), border-color var(--duration-med) var(--ease-out), box-shadow var(--duration-med) var(--ease-out);
}
.agent-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-glow);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}
.agent-card::before {
  content: "";
  position: absolute;
  top: 18px;
  left: 0;
  width: 4px;
  height: calc(100% - 36px);
  background: linear-gradient(180deg, var(--accent-strong), var(--accent), var(--violet));
  opacity: 0.88;
  border-radius: 0 999px 999px 0;
}
.agent-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.agent-name h3 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 0;
}
.agent-mono {
  display: block;
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--accent);
  letter-spacing: 0;
  text-transform: uppercase;
  margin-bottom: 3px;
}
.meta {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin: 0;
}
.meta > div {
  padding: 10px 11px;
  background: var(--panel-light);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
}
.meta dt {
  font-size: 12.5px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0;
}
.meta dd {
  margin: 4px 0 0;
  font-size: 14.5px;
}
.path {
  font-size: 13.5px;
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
  padding: 3px 9px;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--border-glow);
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 650;
}
.proxy-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 3px 9px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 650;
}
.proxy-badge.on {
  color: var(--ok);
  background: var(--ok-soft);
  border-color: rgba(116, 224, 173, 0.35);
}
.proxy-badge.warn {
  color: var(--warn);
  background: var(--warn-soft);
  border-color: rgba(71, 106, 159, 0.35);
}
.proxy-badge.error {
  color: var(--danger);
  background: var(--danger-soft);
  border-color: rgba(251, 133, 133, 0.35);
}
.proxy-badge.off,
.proxy-badge.neutral {
  color: var(--text-tertiary);
  background: var(--panel-light);
}
.check-panel {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  background: var(--panel-light);
  padding: 12px 13px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.check-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  font-size: 13.5px;
}
.check-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.check-copy strong {
  white-space: nowrap;
}
.check-copy span {
  color: var(--text-tertiary);
}
.check-action,
.reset-usage {
  height: 25px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--border-strong);
  background: var(--panel-light);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12.5px;
  padding: 0 8px;
  transition: color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.check-action:hover,
.reset-usage:hover {
  color: var(--accent);
  border-color: var(--border-glow);
  background: var(--accent-soft);
  transform: translateY(-1px);
}
.check-ok {
  border-color: rgba(116, 224, 173, 0.32);
  background: linear-gradient(135deg, rgba(116, 224, 173, 0.08), var(--panel-light));
}
.check-ok .check-head strong {
  color: var(--ok);
}
.check-warn {
  border-color: rgba(71, 106, 159, 0.35);
  background: linear-gradient(135deg, var(--warn-soft), var(--panel-light));
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
  padding: 8px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  background: var(--panel-light);
}
.config-grid span {
  font-size: 11.5px;
  color: var(--text-tertiary);
}
.config-grid code {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.usage-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.usage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-tertiary);
}
.usage {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.usage-cell {
  background: var(--panel-light);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.usage-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}
.usage-label {
  font-size: 12.5px;
  color: var(--text-tertiary);
}
.usage-cell.total {
  background: linear-gradient(135deg, var(--accent-soft), var(--panel-light));
  border-color: var(--border-glow);
}
.usage-cell.total .usage-num {
  color: var(--accent);
}
.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}
.card-actions .ghost,
.card-actions .primary {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  height: 31px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--border-strong);
  transition: transform var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.card-actions .ghost {
  background: var(--panel-light);
  color: var(--text-secondary);
}
.card-actions .ghost:hover {
  color: var(--text-primary);
  background: var(--panel-lighter);
  transform: translateY(-1px);
}
.card-actions .primary {
  background: linear-gradient(135deg, var(--accent-strong), var(--accent));
  color: #fffaf6;
  border-color: rgba(16, 122, 115, 0.82);
  box-shadow: 0 12px 24px rgba(16, 122, 115, 0.16);
}
.card-actions .primary:hover {
  border-color: var(--accent-strong);
  transform: translateY(-1px);
}
@media (max-width: 560px) {
  .usage {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
