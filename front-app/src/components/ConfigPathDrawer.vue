<script setup lang="ts">
import { ref, watch } from "vue";
import AppDrawer from "@/components/AppDrawer.vue";
import AppButton from "@/components/AppButton.vue";
import AppInput from "@/components/AppInput.vue";
import AppFormField from "@/components/AppFormField.vue";
import InfoTip from "@/components/InfoTip.vue";
import StatusDot from "@/components/StatusDot.vue";
import { BackendError } from "@/api/client";
import { useAgentsStore } from "@/stores/agents";
import { useAppStore } from "@/stores/app";
import { agentDisplayName } from "@/utils/format";
import type { AgentInfo, AgentType } from "@/types/api";

const props = defineProps<{ open: boolean; agentType: AgentType; agent: AgentInfo | null }>();
const emit = defineEmits<{ (e: "update:open", v: boolean): void }>();

const agentsStore = useAgentsStore();
const appStore = useAppStore();

const pathInput = ref("");
const saving = ref(false);
const error = ref("");

watch(
  () => [props.open, props.agent?.config_path],
  () => {
    if (props.open) {
      pathInput.value = props.agent?.config_path ?? "";
      error.value = "";
    }
  },
);

async function save() {
  saving.value = true;
  error.value = "";
  try {
    const agent = await agentsStore.setConfigPath(props.agentType, pathInput.value.trim());
    appStore.pushToast({
      level: agent.status === "installed" ? "success" : "warn",
      title: `路径已更新 (${agentDisplayName[props.agentType]})`,
      description: agent.status_message,
    });
    emit("update:open", false);
  } catch (e) {
    error.value = e instanceof BackendError ? e.message : "保存失败";
  } finally {
    saving.value = false;
  }
}

async function probe() {
  saving.value = true;
  error.value = "";
  try {
    const previous = props.agent?.config_path ?? "";
    if (pathInput.value.trim() !== previous) {
      await agentsStore.setConfigPath(props.agentType, pathInput.value.trim());
    } else {
      await agentsStore.probe(props.agentType);
    }
  } catch (e) {
    error.value = e instanceof BackendError ? e.message : "探测失败";
  } finally {
    saving.value = false;
  }
}

async function clear() {
  saving.value = true;
  error.value = "";
  try {
    pathInput.value = "";
    await agentsStore.setConfigPath(props.agentType, "");
    emit("update:open", false);
  } catch (e) {
    error.value = e instanceof BackendError ? e.message : "清空失败";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppDrawer
    :open="props.open"
    :title="`配置路径 · ${agentDisplayName[props.agentType]}`"
    @update:open="(v) => emit('update:open', v)"
  >
    <div class="content">
      <div class="notice-row">
        <InfoTip title="路径填写说明" label="注意">
          浏览器无法直接打开本地文件选择器，请粘贴目录或具体文件路径。后端会拼接默认文件名：
          Codex 为 <span class="mono">config.toml</span>，Claude Code 为
          <span class="mono">settings.json</span>。
        </InfoTip>
      </div>

      <AppFormField label="配置路径" :error="error">
        <AppInput
          v-model="pathInput"
          placeholder="/home/you/.codex 或 /home/you/.codex/config.toml"
          mono
          :invalid="!!error"
        />
      </AppFormField>

      <div class="result" v-if="props.agent">
        <div class="result-row">
          <span class="label">解析后的目标文件</span>
          <span class="value mono">{{ props.agent.resolved_config_file || '-' }}</span>
        </div>
        <div class="result-row">
          <span class="label">状态</span>
          <StatusDot :status="props.agent.status" />
        </div>
        <div class="result-row">
          <span class="label">最近探测</span>
          <span class="value mono">{{ props.agent.updated_at || '-' }}</span>
        </div>
        <div v-if="props.agent.status_message" class="result-msg">
          {{ props.agent.status_message }}
        </div>
      </div>
    </div>

    <template #footer>
      <AppButton variant="ghost" :disabled="saving" @click="clear">清空路径</AppButton>
      <AppButton variant="secondary" :loading="saving" @click="probe">仅探测</AppButton>
      <AppButton variant="primary" :loading="saving" @click="save">保存并探测</AppButton>
    </template>
  </AppDrawer>
</template>

<style scoped>
.content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.notice-row {
  display: flex;
  justify-content: flex-start;
}
.result {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  background: var(--bg-surface-2);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}
.result-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12.5px;
}
.result-row .label { color: var(--text-tertiary); }
.result-row .value {
  color: var(--text-primary);
  text-align: right;
  word-break: break-all;
}
.result-msg {
  font-size: 12px;
  color: var(--text-secondary);
  border-top: 1px dashed var(--border-soft);
  padding-top: 8px;
}
.mono { font-family: var(--font-mono); }
</style>
