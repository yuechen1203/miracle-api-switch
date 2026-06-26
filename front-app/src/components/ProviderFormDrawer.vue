<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import AppDrawer from "@/components/AppDrawer.vue";
import AppButton from "@/components/AppButton.vue";
import AppInput from "@/components/AppInput.vue";
import AppFormField from "@/components/AppFormField.vue";
import AppToggle from "@/components/AppToggle.vue";
import AppSegmented from "@/components/AppSegmented.vue";
import InfoTip from "@/components/InfoTip.vue";
import { BackendError } from "@/api/client";
import { useProvidersStore } from "@/stores/providers";
import { useAppStore } from "@/stores/app";
import { agentDisplayName, targetFormatLabel } from "@/utils/format";
import type { AgentType, Provider, TargetFormat } from "@/types/api";

const props = defineProps<{ open: boolean; agentType: AgentType; provider: Provider | null }>();
const emit = defineEmits<{ (e: "update:open", v: boolean): void }>();

const providersStore = useProvidersStore();
const appStore = useAppStore();

interface FormState {
  display_name: string;
  api_key: string;
  base_url: string;
  model: string;
  proxy_enabled: boolean;
  proxy_port: number | null;
  target_format: TargetFormat | null;
}

const form = reactive<FormState>({
  display_name: "",
  api_key: "",
  base_url: "",
  model: "",
  proxy_enabled: false,
  proxy_port: 5555,
  target_format: "responses",
});

const errors = reactive<Record<keyof FormState, string>>({
  display_name: "",
  api_key: "",
  base_url: "",
  model: "",
  proxy_enabled: "",
  proxy_port: "",
  target_format: "",
});

const submitting = ref(false);
const submitError = ref("");

const isEdit = computed(() => !!props.provider);
const title = computed(() =>
  (isEdit.value ? "编辑 Provider · " : "新建 Provider · ") + agentDisplayName[props.agentType],
);

const sourceFormat = computed(() => (props.agentType === "codex" ? "responses" : "messages"));

const localProxyUrl = computed(() => {
  if (!form.proxy_enabled || !form.proxy_port) return "";
  return `http://127.0.0.1:${form.proxy_port}`;
});

const formatOptions: { value: TargetFormat; label: string; hint?: string }[] = [
  { value: "chat/completions", label: "chat/completions", hint: targetFormatLabel["chat/completions"] },
  { value: "responses", label: "responses", hint: targetFormatLabel.responses },
  { value: "messages", label: "messages", hint: targetFormatLabel.messages },
];

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    submitError.value = "";
    Object.keys(errors).forEach((k) => ((errors as any)[k] = ""));
    if (props.provider) {
      form.display_name = props.provider.display_name;
      form.api_key = "";
      form.base_url = props.provider.base_url;
      form.model = props.provider.model;
      form.proxy_enabled = props.provider.proxy_enabled;
      form.proxy_port = props.provider.proxy_port ?? 5555;
      form.target_format = (props.provider.target_format ?? "responses") as TargetFormat;
    } else {
      form.display_name = "";
      form.api_key = "";
      form.base_url = "";
      form.model = "";
      form.proxy_enabled = false;
      form.proxy_port = 5555;
      form.target_format = sourceFormat.value === "responses" ? "responses" : "messages";
    }
  },
);

function validate(): boolean {
  let ok = true;
  Object.keys(errors).forEach((k) => ((errors as any)[k] = ""));
  if (!form.display_name.trim()) { errors.display_name = "必填"; ok = false; }
  else if (form.display_name.length > 64) { errors.display_name = "最多 64 字符"; ok = false; }
  if (!isEdit.value && !form.api_key.trim()) { errors.api_key = "新建时必须填写 API Key"; ok = false; }
  if (!form.base_url.trim()) { errors.base_url = "必填"; ok = false; }
  else if (!/^https?:\/\//i.test(form.base_url.trim())) { errors.base_url = "必须以 http:// 或 https:// 开头"; ok = false; }
  if (!form.model.trim()) { errors.model = "必填"; ok = false; }
  else if (form.model.length > 128) { errors.model = "最多 128 字符"; ok = false; }
  if (form.proxy_enabled) {
    if (!form.proxy_port || form.proxy_port < 1 || form.proxy_port > 65535) {
      errors.proxy_port = "端口必须在 1-65535"; ok = false;
    }
    if (!form.target_format) { errors.target_format = "请选择目标 API 格式"; ok = false; }
  }
  return ok;
}

async function submit() {
  if (!validate()) return;
  submitting.value = true;
  submitError.value = "";
  try {
    const basePayload = {
      display_name: form.display_name.trim(),
      base_url: form.base_url.trim().replace(/\/+$/, ""),
      model: form.model.trim(),
      proxy_enabled: form.proxy_enabled,
      proxy_port: form.proxy_enabled ? form.proxy_port : null,
      target_format: form.proxy_enabled ? form.target_format : null,
    };
    if (isEdit.value && props.provider) {
      const payload: Record<string, unknown> = { ...basePayload };
      if (form.api_key.trim() !== "") payload.api_key = form.api_key;
      payload.expected_updated_at = props.provider.updated_at;
      await providersStore.update(props.agentType, props.provider.id, payload);
      appStore.pushToast({ level: "success", title: "Provider 已更新" });
    } else {
      await providersStore.create(props.agentType, {
        ...basePayload,
        api_key: form.api_key,
      });
      appStore.pushToast({ level: "success", title: "Provider 已创建" });
    }
    emit("update:open", false);
  } catch (e) {
    if (e instanceof BackendError) {
      submitError.value = `${e.code}: ${e.message}`;
      if (e.code === "PROVIDER_NAME_DUPLICATED") errors.display_name = e.message;
      if (e.code === "PORT_IN_USE" || e.code === "PORT_INVALID") errors.proxy_port = e.message;
    } else {
      submitError.value = "保存失败";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <AppDrawer
    :open="props.open"
    :title="title"
    width="480px"
    @update:open="(v) => emit('update:open', v)"
  >
    <form class="form-stack" @submit.prevent="submit">
      <AppFormField label="名称" :error="errors.display_name">
        <AppInput
          v-model="form.display_name"
          placeholder="例如 OpenAI Primary"
          :invalid="!!errors.display_name"
        />
      </AppFormField>

      <AppFormField
        label="API Key"
        :error="errors.api_key"
        :hint="isEdit ? '留空表示不修改原 Key' : '后端会脱敏存储，前端不会回显'"
      >
        <AppInput
          v-model="form.api_key"
          type="password"
          mono
          autocomplete="off"
          :placeholder="isEdit ? (props.provider?.api_key_masked || '保持不变') : '粘贴真实 API Key'"
          :invalid="!!errors.api_key"
        />
      </AppFormField>

      <AppFormField label="Base URL" :error="errors.base_url">
        <AppInput
          v-model="form.base_url"
          placeholder="https://api.openai.com/v1"
          mono
          :invalid="!!errors.base_url"
        />
      </AppFormField>

      <AppFormField label="Model" :error="errors.model">
        <AppInput
          v-model="form.model"
          placeholder="例如 gpt-5-codex"
          mono
          :invalid="!!errors.model"
        />
      </AppFormField>

      <section class="proxy-block">
        <header class="proxy-head">
          <div>
            <h4>本地代理 api-switch</h4>
          </div>
          <InfoTip title="本地代理说明" label="注意">
            开启后会启动本地 127.0.0.1 端口，把 {{ sourceFormat }} 转换为目标 API 格式后发送到真实网关。原始格式由 Agent 决定，不可修改。
          </InfoTip>
          <AppToggle v-model="form.proxy_enabled" />
        </header>

        <div v-if="form.proxy_enabled" class="proxy-body">
          <AppFormField label="代理端口" :error="errors.proxy_port" hint="建议 1024 - 65535">
            <AppInput
              v-model="form.proxy_port"
              type="number"
              :min="1"
              :max="65535"
              mono
              :invalid="!!errors.proxy_port"
            />
          </AppFormField>

          <AppFormField label="目标 API 格式" :error="errors.target_format">
            <AppSegmented v-model="form.target_format" :options="formatOptions" />
          </AppFormField>

          <div class="proxy-preview">
            <span class="label">本地代理 URL</span>
            <code class="mono">{{ localProxyUrl || '-' }}</code>
          </div>

          <InfoTip title="流式与写入行为" label="注意">
            当前代理支持基础文本流式转换。工具调用、reasoning、多模态流事件暂不保证无损。真实上游仍使用本表单的 Base URL 与 API Key，本地代理 URL 会写入对应 Agent 配置文件。
          </InfoTip>
        </div>
      </section>

      <div v-if="submitError" class="form-submit-error">{{ submitError }}</div>
    </form>

    <template #footer>
      <AppButton variant="ghost" :disabled="submitting" @click="emit('update:open', false)">取消</AppButton>
      <AppButton variant="primary" :loading="submitting" @click="submit">
        {{ isEdit ? '保存修改' : '创建 Provider' }}
      </AppButton>
    </template>
  </AppDrawer>
</template>

<style scoped>
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.proxy-block {
  background: linear-gradient(135deg, rgba(251, 254, 255, 0.72), var(--accent-soft));
  border: 2px solid var(--border-glow);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 8px 24px rgba(16, 122, 115, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.62);
}
.proxy-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.proxy-head h4 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-primary);
}
.proxy-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.proxy-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--field-bg);
  border: 2px solid var(--field-border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.proxy-preview .label {
  font-size: 13px;
  color: var(--text-tertiary);
}
.proxy-preview code {
  font-size: 13.5px;
  color: var(--accent);
}
.form-submit-error {
  background: var(--danger-soft);
  border: 1px solid rgba(182, 63, 63, 0.34);
  color: var(--danger);
  padding: 9px 10px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
}
.mono { font-family: var(--font-mono); }
</style>
