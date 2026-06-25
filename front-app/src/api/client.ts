import axios, { AxiosError, AxiosInstance } from "axios";
import type {
  AgentInfo,
  AgentType,
  ApiEnvelope,
  ApplyResult,
  ConfigCheckResult,
  HealthInfo,
  Provider,
  ProviderApiKeyReveal,
  ProviderCreatePayload,
  ProviderUpdatePayload,
  ProxyStatusSnapshot,
  UsageRecord,
} from "@/types/api";

const baseURL = "/api";

export class BackendError extends Error {
  code: string;
  details?: Record<string, unknown>;
  status?: number;
  constructor(code: string, message: string, status?: number, details?: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 20_000,
  headers: {
    "Content-Type": "application/json",
  },
});

async function unwrap<T>(promise: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  try {
    const { data } = await promise;
    if (data.success && data.data !== null) return data.data;
    if (data.success && data.data === null) return undefined as unknown as T;
    const err = data.error || { code: "UNKNOWN", message: "未知错误" };
    throw new BackendError(err.code, err.message, undefined, err.details as any);
  } catch (raw) {
    if (raw instanceof BackendError) throw raw;
    const err = raw as AxiosError<ApiEnvelope<unknown>>;
    if (err.response?.data?.error) {
      const e = err.response.data.error;
      throw new BackendError(e.code, e.message, err.response.status, e.details as any);
    }
    if (err.code === "ECONNABORTED") {
      throw new BackendError("NETWORK_TIMEOUT", "后端响应超时", undefined);
    }
    throw new BackendError(
      "BACKEND_UNREACHABLE",
      "无法连接后端服务，请确认 back-app 已经启动",
      err.response?.status,
    );
  }
}

export const api = {
  health() {
    return unwrap<HealthInfo>(http.get("/health"));
  },
  listAgents() {
    return unwrap<AgentInfo[]>(http.get("/agents"));
  },
  getAgent(agentType: AgentType) {
    return unwrap<AgentInfo>(http.get(`/agents/${agentType}`));
  },
  setConfigPath(agentType: AgentType, configPath: string) {
    return unwrap<AgentInfo>(
      http.put(`/agents/${agentType}/config-path`, { config_path: configPath }),
    );
  },
  probeAgent(agentType: AgentType) {
    return unwrap<AgentInfo>(http.post(`/agents/${agentType}/probe`));
  },
  configCheck(agentType: AgentType) {
    return unwrap<ConfigCheckResult>(http.get(`/agents/${agentType}/config-check`));
  },
  listProviders(agentType: AgentType) {
    return unwrap<Provider[]>(http.get(`/agents/${agentType}/providers`));
  },
  createProvider(agentType: AgentType, payload: ProviderCreatePayload) {
    return unwrap<Provider>(http.post(`/agents/${agentType}/providers`, payload));
  },
  updateProvider(agentType: AgentType, providerId: string, payload: ProviderUpdatePayload) {
    return unwrap<Provider>(
      http.patch(`/agents/${agentType}/providers/${providerId}`, payload),
    );
  },
  deleteProvider(agentType: AgentType, providerId: string) {
    return unwrap<Provider>(http.delete(`/agents/${agentType}/providers/${providerId}`));
  },
  revealProviderApiKey(agentType: AgentType, providerId: string) {
    return unwrap<ProviderApiKeyReveal>(
      http.get(`/agents/${agentType}/providers/${providerId}/api-key`),
    );
  },
  applyProvider(
    agentType: AgentType,
    providerId: string,
    body: { dry_run: boolean; start_proxy: boolean },
  ) {
    return unwrap<ApplyResult>(
      http.post(`/agents/${agentType}/providers/${providerId}/apply`, body),
    );
  },
  listProxies() {
    return unwrap<Record<string, ProxyStatusSnapshot>>(http.get("/proxies"));
  },
  startProxy(providerId: string) {
    return unwrap<ProxyStatusSnapshot>(http.post(`/proxies/${providerId}/start`));
  },
  stopProxy(providerId: string) {
    return unwrap<ProxyStatusSnapshot>(http.post(`/proxies/${providerId}/stop`));
  },
  restartProxy(providerId: string) {
    return unwrap<ProxyStatusSnapshot>(http.post(`/proxies/${providerId}/restart`));
  },
  listUsage(agentType: AgentType) {
    return unwrap<Record<string, UsageRecord>>(http.get(`/agents/${agentType}/usage`));
  },
  resetAgentUsage(agentType: AgentType) {
    return unwrap<Record<string, UsageRecord>>(http.post(`/agents/${agentType}/usage/reset`));
  },
  resetUsage(agentType: AgentType, providerId: string) {
    return unwrap<UsageRecord>(
      http.post(`/agents/${agentType}/providers/${providerId}/usage/reset`),
    );
  },
};
