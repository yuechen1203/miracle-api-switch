<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  FolderCog,
  Pencil,
  Play,
  Plus,
  Power,
  RefreshCcw,
  RotateCw,
  Trash2,
  Zap,
  AlertTriangle,
} from "lucide-vue-next";
import SectionCard from "@/components/SectionCard.vue";
import AppButton from "@/components/AppButton.vue";
import StatusDot from "@/components/StatusDot.vue";
import AppModal from "@/components/AppModal.vue";
import AppToggle from "@/components/AppToggle.vue";
import InfoTip from "@/components/InfoTip.vue";
import ConfigPathDrawer from "@/components/ConfigPathDrawer.vue";
import ProviderFormDrawer from "@/components/ProviderFormDrawer.vue";
import { useAgentsStore } from "@/stores/agents";
import { useProvidersStore } from "@/stores/providers";
import { useUsageStore } from "@/stores/usage";
import { useAppStore } from "@/stores/app";
import { BackendError } from "@/api/client";
import {
  agentDisplayName,
  copyText,
  ellipsizeMiddle,
  formatDateTime,
  formatNumber,
  targetFormatLabel,
} from "@/utils/format";
import type { AgentType, ApplyResult, Provider, UsageRecord } from "@/types/api";

const props = defineProps<{ agentType: AgentType }>();

const agentsStore = useAgentsStore();
const providersStore = useProvidersStore();
const usageStore = useUsageStore();
const appStore = useAppStore();

const agent = computed(() => agentsStore.agents[props.agentType]);
const configCheck = computed(() => agentsStore.configChecks[props.agentType]);
const providers = computed(() => providersStore.providers[props.agentType]);
const usageMap = computed(() => usageStore.usage[props.agentType]);

const configDrawerOpen = ref(false);
const formDrawerOpen = ref(false);
const editingProvider = ref<Provider | null>(null);
const revealedKeys = ref<Record<string, string>>({});

const applyModal = ref<{
  open: boolean;
  provider: Provider | null;
  applying: boolean;
  preview: ApplyResult | null;
  error: string;
  startProxy: boolean;
}>({ open: false, provider: null, applying: false, preview: null, error: "", startProxy: true });

const deleteModal = ref<{ open: boolean; provider: Provider | null; deleting: boolean }>({
  open: false,
  provider: null,
  deleting: false,
});

function openCreate() {
  editingProvider.value = null;
  formDrawerOpen.value = true;
}

function openEdit(provider: Provider) {
  editingProvider.value = provider;
  formDrawerOpen.value = true;
}

async function openApply(provider: Provider) {
  applyModal.value = {
    open: true,
    provider,
    applying: false,
    preview: null,
    error: "",
    startProxy: provider.proxy_enabled,
  };
  try {
    const preview = await providersStore.apply(props.agentType, provider.id, {
      dryRun: true,
      startProxy: provider.proxy_enabled,
    });
    applyModal.value.preview = preview;
  } catch (e) {
    applyModal.value.error = e instanceof BackendError ? `${e.code}: ${e.message}` : "预览失败";
  }
}

async function confirmApply() {
  if (!applyModal.value.provider) return;
  applyModal.value.applying = true;
  applyModal.value.error = "";
  try {
    const result = await providersStore.apply(props.agentType, applyModal.value.provider.id, {
      dryRun: false,
      startProxy: applyModal.value.startProxy,
    });
    await agentsStore.refresh();
    await usageStore.refresh(props.agentType);
    appStore.pushToast({
      level: "success",
      title: `已应用到 ${agentDisplayName[props.agentType]}`,
      description: result.write_result.backup_path
        ? `已生成备份 ${result.write_result.backup_path}`
        : undefined,
    });
    await agentsStore.configCheck(props.agentType);
    applyModal.value.open = false;
  } catch (e) {
    applyModal.value.error = e instanceof BackendError ? `${e.code}: ${e.message}` : "应用失败";
  } finally {
    applyModal.value.applying = false;
  }
}

async function toggleProxy(provider: Provider) {
  try {
    if (provider.proxy_status?.status === "running") {
      await providersStore.stopProxy(props.agentType, provider.id);
      appStore.pushToast({ level: "success", title: "本地代理已停止" });
    } else {
      await providersStore.startProxy(props.agentType, provider.id);
      appStore.pushToast({ level: "success", title: "本地代理已启动" });
    }
  } catch (e) {
    appStore.notifyError(e, "代理操作失败");
  }
}

async function restartProxy(provider: Provider) {
  try {
    await providersStore.restartProxy(props.agentType, provider.id);
    appStore.pushToast({ level: "success", title: "本地代理已重启" });
  } catch (e) {
    appStore.notifyError(e, "重启失败");
  }
}

async function copyValue(value: string, label: string) {
  const ok = await copyText(value);
  appStore.pushToast({
    level: ok ? "success" : "warn",
    title: ok ? `已复制 ${label}` : "复制失败",
  });
}

async function toggleRevealKey(provider: Provider) {
  if (revealedKeys.value[provider.id]) {
    const next = { ...revealedKeys.value };
    delete next[provider.id];
    revealedKeys.value = next;
    return;
  }
  try {
    const result = await providersStore.revealApiKey(props.agentType, provider.id);
    revealedKeys.value = { ...revealedKeys.value, [provider.id]: result.api_key };
  } catch (e) {
    appStore.notifyError(e, "显示 API Key 失败");
  }
}

function openDelete(provider: Provider) {
  deleteModal.value = { open: true, provider, deleting: false };
}

async function confirmDelete() {
  if (!deleteModal.value.provider) return;
  deleteModal.value.deleting = true;
  try {
    await providersStore.remove(props.agentType, deleteModal.value.provider.id);
    await agentsStore.refresh();
    await agentsStore.configCheck(props.agentType);
    appStore.pushToast({ level: "success", title: "Provider 已删除" });
    deleteModal.value.open = false;
  } catch (e) {
    appStore.notifyError(e, "删除失败");
  } finally {
    deleteModal.value.deleting = false;
  }
}

const proxyRunningCount = computed(
  () => providers.value.filter((p) => p.proxy_status?.status === "running").length,
);

function usageFor(providerId: string): UsageRecord {
  return usageMap.value[providerId] || {
    request_count: 0,
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
    last_request_at: null,
  };
}

async function refreshAll() {
  try {
    await agentsStore.probe(props.agentType);
    await providersStore.refresh(props.agentType);
    await agentsStore.configCheck(props.agentType);
    await usageStore.refresh(props.agentType);
  } catch (e) {
    appStore.notifyError(e, "刷新失败");
  }
}

async function recheckConfig() {
  try {
    await agentsStore.configCheck(props.agentType);
    appStore.pushToast({ level: "success", title: "校验状态已刷新" });
  } catch (e) {
    appStore.notifyError(e, "重新校验失败");
  }
}

onMounted(() => {
  refreshAll();
});

watch(
  () => props.agentType,
  () => {
    revealedKeys.value = {};
    refreshAll();
  },
);

function changeSummary(preview: ApplyResult | null): { label: string; value: string }[] {
  if (!preview?.write_result?.changes) return [];
  const out: { label: string; value: string }[] = [];
  for (const [k, v] of Object.entries(preview.write_result.changes)) {
    let display: string;
    if (typeof v === "string") display = v;
    else if (v && typeof v === "object" && "to" in (v as any)) display = String((v as any).to);
    else display = JSON.stringify(v);
    out.push({ label: k, value: display });
  }
  return out;
}
</script>

<template>
  <div class="agent-view">
    <header class="page-header">
      <div class="title-row">
        <h1>{{ agentDisplayName[props.agentType] }} Providers</h1>
        <StatusDot v-if="agent" :status="agent.status" />
      </div>
      <p v-if="agent" class="page-subtitle">
        {{ agent.status_message || "管理 API key、Base URL、Model 与本地代理转换。" }}
      </p>
    </header>

    <SectionCard padded title="配置文件">
      <template #actions>
        <AppButton size="sm" variant="ghost" @click="refreshAll">
          <RefreshCcw :size="13" /> 探测
        </AppButton>
        <AppButton size="sm" variant="secondary" @click="configDrawerOpen = true">
          <FolderCog :size="13" /> 配置路径
        </AppButton>
      </template>
      <div class="meta-grid">
        <div>
          <div class="meta-label">配置路径</div>
          <div class="meta-value mono">{{ agent?.config_path || "未设置" }}</div>
        </div>
        <div>
          <div class="meta-label">解析后的目标文件</div>
          <div class="meta-value mono">{{ agent?.resolved_config_file || "-" }}</div>
        </div>
        <div>
          <div class="meta-label">当前应用 Provider</div>
          <div class="meta-value">
            <span
              v-if="providers.find((p) => p.id === agent?.current_provider_id)"
              class="current-tag"
            >
              {{ providers.find((p) => p.id === agent?.current_provider_id)?.display_name }}
            </span>
            <span v-else class="muted">未初始化</span>
          </div>
        </div>
        <div>
          <div class="meta-label">本地代理</div>
          <div class="meta-value">
            <span v-if="proxyRunningCount > 0" class="muted">
              <Zap :size="13" /> {{ proxyRunningCount }} 个运行中
            </span>
            <span v-else class="muted">未运行</span>
          </div>
        </div>
      </div>

      <div
        v-if="configCheck"
        class="config-check"
        :class="{
          ok: configCheck.status === 'matched',
          warn: configCheck.status === 'mismatched' || configCheck.status === 'provider_missing' || configCheck.status === 'unavailable',
          muted: configCheck.status === 'not_initialized',
        }"
      >
        <div class="check-status">
          <div class="check-copy">
            <strong>
              {{
                configCheck.status === 'matched'
                  ? 'Check 通过'
                  : configCheck.status === 'not_initialized'
                    ? '当前 Provider 未初始化'
                    : configCheck.status === 'unavailable'
                      ? '无法校准'
                    : '配置文件发生改动'
              }}
            </strong>
            <span>{{ configCheck.message }}</span>
          </div>
          <AppButton size="sm" variant="ghost" @click="recheckConfig">
            <RefreshCcw :size="13" /> 重新校验
          </AppButton>
        </div>
        <div class="current-config-grid">
          <div>
            <span>当前配置 URL</span>
            <code :title="configCheck.current_config.base_url || '-'">
              {{ configCheck.current_config.base_url || '-' }}
            </code>
          </div>
          <div>
            <span>当前配置 Provider</span>
            <code :title="configCheck.current_config.model_provider || '-'">
              {{ configCheck.current_config.model_provider || '-' }}
            </code>
          </div>
          <div>
            <span>当前配置 API Key</span>
            <code>{{ configCheck.current_config.api_key_masked || '-' }}</code>
          </div>
          <div>
            <span>当前配置 Model</span>
            <code :title="configCheck.current_config.model || '-'">
              {{ configCheck.current_config.model || '-' }}
            </code>
          </div>
        </div>
        <div v-if="configCheck.mismatched_fields.length" class="mismatch-list">
          不匹配字段：
          <span v-for="field in configCheck.mismatched_fields" :key="field" class="mismatch-pill">
            {{ field }}
          </span>
        </div>
      </div>
    </SectionCard>

    <SectionCard class="providers-card" title="Provider 组">
      <template #actions>
        <span class="hint">{{ providers.length }} 个</span>
        <AppButton size="sm" variant="primary" @click="openCreate">
          <Plus :size="13" /> 新建 Provider
        </AppButton>
      </template>

      <div v-if="!providers.length" class="empty">
        <p>还没有 Provider，点击右上角“新建 Provider”开始。</p>
      </div>

      <div v-else class="provider-table-wrap">
        <table class="provider-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>Base URL</th>
              <th>Model</th>
              <th>Key</th>
              <th>本地代理</th>
              <th>端口</th>
              <th>Token</th>
              <th>更新时间</th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in providers" :key="p.id" :class="{ current: p.is_current }">
              <td>
                <div class="cell-name">
                  <CheckCircle2 v-if="p.is_current" :size="13" class="check" />
                  <span :title="p.display_name">{{ p.display_name }}</span>
                </div>
              </td>
              <td>
                <button
                  class="cell-copy mono"
                  :title="p.base_url"
                  @click="copyValue(p.base_url, 'Base URL')"
                >
                  <span>{{ ellipsizeMiddle(p.base_url, 24, 8) }}</span>
                  <Copy :size="11" />
                </button>
              </td>
              <td>
                <button
                  class="cell-copy mono"
                  :title="p.model"
                  @click="copyValue(p.model, 'Model')"
                >
                  <span>{{ ellipsizeMiddle(p.model, 22, 10) }}</span>
                  <Copy :size="11" />
                </button>
              </td>
              <td>
                <div v-if="p.has_api_key" class="key-cell">
                  <span class="mono key-mask">{{ revealedKeys[p.id] || p.api_key_masked }}</span>
                  <button
                    class="icon-act key-toggle"
                    :title="revealedKeys[p.id] ? '隐藏完整 Key' : '显示完整 Key'"
                    @click="toggleRevealKey(p)"
                  >
                    <component :is="revealedKeys[p.id] ? EyeOff : Eye" :size="13" />
                  </button>
                </div>
                <span v-else class="muted small">无</span>
              </td>
              <td>
                <div v-if="p.proxy_enabled" class="proxy-cell">
                  <StatusDot :status="p.proxy_status?.status || 'stopped'" />
                  <button
                    v-if="p.local_proxy_url"
                    class="cell-copy mono"
                    @click="copyValue(p.local_proxy_url!, '本地代理 URL')"
                    :title="p.local_proxy_url"
                  >
                    <span>{{ p.local_proxy_url }}</span>
                    <Copy :size="11" />
                  </button>
                  <span class="proxy-tag">{{ targetFormatLabel[p.target_format || ''] || p.target_format }}</span>
                </div>
                <span v-else class="muted small">未开启</span>
              </td>
              <td class="mono">
                <span v-if="p.proxy_enabled && p.proxy_port">{{ p.proxy_port }}</span>
                <span v-else class="muted small">-</span>
              </td>
              <td>
                <InfoTip label="Token" title="Token 详情">
                  <div class="token-detail">
                    <div><span>请求</span><strong class="mono">{{ formatNumber(usageFor(p.id).request_count) }}</strong></div>
                    <div><span>输入 token</span><strong class="mono">{{ formatNumber(usageFor(p.id).input_tokens) }}</strong></div>
                    <div><span>输出 token</span><strong class="mono">{{ formatNumber(usageFor(p.id).output_tokens) }}</strong></div>
                    <div><span>合计 token</span><strong class="mono">{{ formatNumber(usageFor(p.id).total_tokens) }}</strong></div>
                    <div><span>缓存创建</span><strong class="mono">{{ formatNumber(usageFor(p.id).cache_creation_input_tokens) }}</strong></div>
                    <div><span>缓存读取</span><strong class="mono">{{ formatNumber(usageFor(p.id).cache_read_input_tokens) }}</strong></div>
                    <div><span>最近请求</span><strong class="mono">{{ formatDateTime(usageFor(p.id).last_request_at) }}</strong></div>
                  </div>
                </InfoTip>
              </td>
              <td class="time mono">{{ formatDateTime(p.updated_at) }}</td>
              <td class="actions">
                <div class="row-actions">
                  <button class="icon-act" title="使用此 provider" @click="openApply(p)">
                    <Play :size="14" />
                  </button>
                  <button
                    v-if="p.proxy_enabled"
                    class="icon-act"
                    :title="p.proxy_status?.status === 'running' ? '停止本地代理' : '启动本地代理'"
                    @click="toggleProxy(p)"
                  >
                    <Power :size="14" />
                  </button>
                  <button
                    v-if="p.proxy_enabled && p.proxy_status?.status === 'running'"
                    class="icon-act"
                    title="重启本地代理"
                    @click="restartProxy(p)"
                  >
                    <RotateCw :size="14" />
                  </button>
                  <button class="icon-act" title="编辑" @click="openEdit(p)">
                    <Pencil :size="14" />
                  </button>
                  <button class="icon-act danger" title="删除" @click="openDelete(p)">
                    <Trash2 :size="14" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>

    <ConfigPathDrawer
      v-if="agent"
      :open="configDrawerOpen"
      :agent-type="props.agentType"
      :agent="agent"
      @update:open="configDrawerOpen = $event"
    />

    <ProviderFormDrawer
      :open="formDrawerOpen"
      :agent-type="props.agentType"
      :provider="editingProvider"
      @update:open="formDrawerOpen = $event"
    />

    <AppModal
      :open="applyModal.open"
      width="520px"
      title="确认应用 Provider"
      @update:open="applyModal.open = $event"
    >
      <div v-if="applyModal.provider" class="apply-body">
        <p class="apply-lead">
          将把 <strong>{{ applyModal.provider.display_name }}</strong>
          写入 <span class="mono">{{ agent?.resolved_config_file || '-' }}</span>。
        </p>

        <div v-if="applyModal.preview" class="apply-diff">
          <div class="diff-title">将修改的字段</div>
          <div v-if="changeSummary(applyModal.preview).length === 0" class="muted small">
            未检测到字段变更。
          </div>
          <ul v-else>
            <li v-for="(c, i) in changeSummary(applyModal.preview)" :key="i">
              <span class="mono diff-key">{{ c.label }}</span>
              <span class="mono diff-val">{{ c.value }}</span>
            </li>
          </ul>
          <div v-if="applyModal.preview.write_result?.backup_path" class="diff-backup">
            写入前将生成备份：
            <span class="mono">{{ applyModal.preview.write_result.backup_path }}</span>
          </div>
        </div>

        <div v-if="applyModal.provider.proxy_enabled" class="apply-proxy">
          <AppToggle v-model="applyModal.startProxy" />
          <div>
            <div class="apply-proxy-title">
              同时启动本地代理
              <InfoTip title="写入顺序" label="注意">
                将先启动
                <span class="mono">
                  {{ applyModal.provider.local_proxy_url || `http://127.0.0.1:${applyModal.provider.proxy_port}` }}
                </span>
                ，再把代理地址写入配置文件。
              </InfoTip>
            </div>
          </div>
        </div>

        <div v-if="applyModal.error" class="form-submit-error">
          <AlertTriangle :size="13" /> {{ applyModal.error }}
        </div>
      </div>

      <template #footer>
        <AppButton variant="ghost" :disabled="applyModal.applying" @click="applyModal.open = false">取消</AppButton>
        <AppButton variant="primary" :loading="applyModal.applying" @click="confirmApply">确认写入</AppButton>
      </template>
    </AppModal>

    <AppModal
      :open="deleteModal.open"
      title="删除 Provider"
      @update:open="deleteModal.open = $event"
    >
      <p v-if="deleteModal.provider">
        将删除 Provider <strong>{{ deleteModal.provider.display_name }}</strong>。
        如果它当前已被应用到配置文件，删除后请重新选择一个 Provider 应用。
      </p>
      <template #footer>
        <AppButton variant="ghost" :disabled="deleteModal.deleting" @click="deleteModal.open = false">
          取消
        </AppButton>
        <AppButton variant="danger" :loading="deleteModal.deleting" @click="confirmDelete">
          确认删除
        </AppButton>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.agent-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-subtitle {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}
.meta-label {
  font-size: 11.5px;
  color: var(--text-tertiary);
}
.meta-value {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 6px;
}
.muted {
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.muted.small { font-size: 12px; }
.current-tag {
  display: inline-flex;
  padding: 2px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 999px;
  font-size: 12px;
}
.mono { font-family: var(--font-mono); }
.config-check {
  margin-top: 16px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  background: var(--bg-surface-2);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.config-check.ok {
  border-color: rgba(92, 210, 155, 0.34);
}
.config-check.warn {
  background: var(--warn-soft);
  border-color: rgba(246, 178, 90, 0.36);
}
.config-check.muted {
  opacity: 0.9;
}
.check-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  font-size: 12.5px;
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
.config-check.ok .check-status strong {
  color: var(--ok);
}
.config-check.warn .check-status strong {
  color: var(--warn);
}
.check-copy span {
  color: var(--text-secondary);
}
.current-config-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 1fr 1fr;
  gap: 10px;
}
.current-config-grid div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.current-config-grid span {
  font-size: 11px;
  color: var(--text-tertiary);
}
.current-config-grid code {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mismatch-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-secondary);
}
.mismatch-pill {
  font-family: var(--font-mono);
  border: 1px solid rgba(246, 178, 90, 0.32);
  background: rgba(246, 178, 90, 0.12);
  color: var(--warn);
  border-radius: var(--radius-xs);
  padding: 1px 6px;
}

.providers-card .empty {
  padding: 32px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

.provider-table-wrap {
  width: 100%;
  overflow-x: auto;
}
.provider-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  min-width: 980px;
}
.provider-table thead th {
  text-align: left;
  font-weight: 500;
  color: var(--text-tertiary);
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-soft);
  background: var(--bg-surface);
  position: sticky;
  top: 0;
}
.provider-table tbody td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-soft);
  vertical-align: middle;
  color: var(--text-primary);
}
.provider-table tbody tr:last-child td { border-bottom: none; }
.provider-table tr.current {
  background: rgba(54, 226, 196, 0.04);
}
.provider-table .actions { text-align: right; width: 1%; white-space: nowrap; }
.provider-table .time { white-space: nowrap; color: var(--text-tertiary); }

.cell-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 220px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-name .check { color: var(--accent); }
.cell-copy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 0;
  font-size: 12px;
}
.cell-copy:hover { color: var(--accent); }
.cell-copy span {
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
}
.key-mask {
  font-size: 12px;
  color: var(--text-secondary);
}
.key-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 260px;
}
.key-cell .key-mask {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 210px;
}
.key-toggle {
  width: 22px;
  height: 22px;
}
.proxy-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.proxy-tag {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-surface-3);
  color: var(--text-secondary);
  border-radius: var(--radius-xs);
}
.token-detail {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  min-width: 220px;
}
.token-detail > div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.token-detail span {
  color: var(--text-tertiary);
}
.token-detail strong {
  color: var(--text-primary);
  font-weight: 500;
  text-align: right;
}

.row-actions {
  display: inline-flex;
  gap: 4px;
}
.icon-act {
  width: 26px;
  height: 26px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-strong);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: color 120ms ease, background-color 120ms ease, border-color 120ms ease;
}
.icon-act:hover {
  color: var(--text-primary);
  border-color: #3a4756;
}
.icon-act.danger:hover {
  color: var(--danger);
  border-color: rgba(239, 106, 106, 0.35);
}

.apply-body { display: flex; flex-direction: column; gap: 14px; }
.apply-lead { margin: 0; font-size: 13px; color: var(--text-primary); }
.apply-diff {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.apply-diff .diff-title {
  font-size: 11.5px;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}
.apply-diff ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.apply-diff li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
}
.diff-key {
  color: var(--text-secondary);
}
.diff-val {
  color: var(--accent);
  word-break: break-all;
  text-align: right;
  max-width: 60%;
}
.diff-backup {
  margin-top: 8px;
  font-size: 11.5px;
  color: var(--text-tertiary);
  word-break: break-all;
}
.apply-proxy {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--bg-surface-2);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.apply-proxy-title {
  font-size: 12.5px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.form-submit-error {
  background: var(--danger-soft);
  border: 1px solid rgba(239, 106, 106, 0.32);
  color: #ffd2d2;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@media (max-width: 1100px) {
  .meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .current-config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
