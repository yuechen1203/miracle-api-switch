export type AgentType = "codex" | "claude_code";

export type AgentStatus = "uninitialized" | "installed" | "missing" | "invalid";

export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  request_id: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface AgentInfo {
  agent_type: AgentType;
  config_path: string;
  resolved_config_file: string | null;
  status: AgentStatus;
  status_message: string;
  current_provider_id: string | null;
  updated_at: string | null;
}

export type ProxyStatus = "stopped" | "starting" | "running" | "error";

export type TargetFormat = "chat/completions" | "responses" | "messages";

export interface ProxyStatusSnapshot {
  provider_id?: string;
  agent_type?: AgentType;
  port?: number | null;
  local_url?: string | null;
  status: ProxyStatus;
  target_format?: TargetFormat | null;
  last_error?: string | null;
  updated_at?: string | null;
}

export interface UsageRecord {
  request_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  last_request_at: string | null;
}

export interface Provider {
  id: string;
  agent_type: AgentType;
  display_name: string;
  base_url: string;
  model: string;
  proxy_enabled: boolean;
  proxy_port: number | null;
  target_format: TargetFormat | null;
  created_at: string;
  updated_at: string;
  has_api_key: boolean;
  api_key_masked: string;
  local_proxy_url: string | null;
  proxy_status?: ProxyStatusSnapshot;
  usage?: UsageRecord;
  is_current?: boolean;
}

export type ConfigCheckStatus =
  | "not_initialized"
  | "matched"
  | "mismatched"
  | "unavailable"
  | "provider_missing";

export interface CurrentConfigSnapshot {
  agent_type: AgentType;
  config_file: string | null;
  base_url: string;
  model: string;
  model_provider: string;
  provider_name: string;
  model_fields: Record<string, string>;
  has_api_key: boolean;
  api_key_masked: string;
}

export interface ExpectedConfigSnapshot {
  base_url: string;
  model: string;
  model_provider: string;
  provider_name: string;
  has_api_key: boolean;
  api_key_masked: string;
}

export interface ConfigCheckResult {
  agent: AgentInfo;
  status: ConfigCheckStatus;
  is_match: boolean | null;
  message: string;
  current_config: CurrentConfigSnapshot;
  expected_config: ExpectedConfigSnapshot | null;
  mismatched_fields: string[];
}

export interface ProviderApiKeyReveal {
  provider_id: string;
  has_api_key: boolean;
  api_key: string;
}

export interface ProviderCreatePayload {
  display_name: string;
  api_key: string;
  base_url: string;
  model: string;
  proxy_enabled: boolean;
  proxy_port?: number | null;
  target_format?: TargetFormat | null;
}

export interface ProviderUpdatePayload {
  display_name?: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  proxy_enabled?: boolean;
  proxy_port?: number | null;
  target_format?: TargetFormat | null;
  expected_updated_at?: string;
}

export interface ApplyResult {
  agent: AgentInfo;
  provider: Provider;
  write_result: {
    success: boolean;
    backup_path?: string | null;
    target_file?: string | null;
    changes?: Record<string, unknown>;
    dry_run?: boolean;
  };
  proxy_status?: ProxyStatusSnapshot;
  dry_run: boolean;
}

export interface HealthInfo {
  name: string;
  version: string;
  status: string;
  started_at: string;
  workspace_root: string;
  cache_dir: string;
}
