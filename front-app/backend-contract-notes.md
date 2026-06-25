# 后端对接约束和前端开发注意事项

本目录本次只保存前端对接文档，不包含任何 Vue 前端代码。

## 1. 后端基础信息

默认后端地址建议为：

```text
http://127.0.0.1:8765
```

健康检查：

```text
GET /api/health
```

所有业务接口返回统一包裹结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "..."
}
```

失败时：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "用户可读错误",
    "details": {}
  },
  "request_id": "..."
}
```

前端不要只依赖 HTTP 状态码，应优先判断 `success` 和 `error.code`。

## 2. Agent 状态

支持的 `agent_type`：

| 前端展示 | API 值 |
| --- | --- |
| Codex | `codex` |
| Claude Code | `claude_code` |

状态值：

| status | 前端含义 |
| --- | --- |
| `uninitialized` | 未初始化，配置路径为空 |
| `installed` | 配置文件存在且可解析 |
| `missing` | 已配置路径，但目标配置文件不存在 |
| `invalid` | 文件存在但解析失败或不可写 |

`GET /api/agents` 返回固定顺序：Codex、Claude Code。

## 3. 配置路径输入

路径配置接口：

```text
PUT /api/agents/{agent_type}/config-path
```

请求体：

```json
{
  "config_path": "/path/to/config/dir-or-file"
}
```

前端只需要提供文本输入。后端支持目录或具体文件：

| Agent | 目录时拼接 | 文件名要求 |
| --- | --- | --- |
| Codex | `config.toml` | `config.toml` |
| Claude Code | `settings.json` | `settings.json` |

浏览器前端不要假设可以直接选择本地任意路径；如果未来做 Electron/Tauri 再接原生文件选择。

## 4. Provider 表单约束

创建接口：

```text
POST /api/agents/{agent_type}/providers
```

编辑接口：

```text
PATCH /api/agents/{agent_type}/providers/{provider_id}
```

字段：

| 字段 | 前端规则 |
| --- | --- |
| `display_name` | 必填，1-64 字符，同一 Agent 下唯一 |
| `api_key` | 新建必填；编辑时传空字符串表示保持原 key 不变 |
| `base_url` | 必填，必须以 `http://` 或 `https://` 开头 |
| `model` | 必填，1-128 字符 |
| `proxy_enabled` | 布尔值 |
| `proxy_port` | 代理开启时必填，1-65535 |
| `target_format` | 代理开启时必填 |

`target_format` 推荐前端使用后端标准值：

| 展示文案 | API 值 |
| --- | --- |
| OpenAI Chat Completions | `chat/completions` |
| OpenAI Responses | `responses` |
| Anthropic Messages | `messages` |

后端兼容接收旧值 `response`，但返回会统一为 `responses`。

## 5. API Key 脱敏

Provider 查询接口不会返回完整 `api_key`，只返回：

| 字段 | 说明 |
| --- | --- |
| `has_api_key` | 后端是否保存了 key |
| `api_key_masked` | 脱敏后的 key |

前端编辑页不要尝试回显完整 key。编辑时：

1. 用户不改 key：提交 `api_key: ""` 或不提交该字段。
2. 用户要替换 key：提交新的完整 key。

## 6. 应用 Provider

接口：

```text
POST /api/agents/{agent_type}/providers/{provider_id}/apply
```

请求体：

```json
{
  "dry_run": false,
  "start_proxy": true
}
```

注意：

1. `dry_run=true` 只预览写入字段，不改配置文件，不启动代理。
2. Provider 开启代理且 `start_proxy=true` 时，后端会先启动本地代理，再写 Agent 配置。
3. 成功返回的 `write_result.backup_path` 可展示给用户。
4. 前端需要把这是“会修改本地配置文件”的高风险操作作为确认弹窗处理。

## 7. 本地代理限制

V1 本地代理 URL 固定为：

```text
http://127.0.0.1:{proxy_port}
```

不是 HTTPS。前端不要展示 `https://127.0.0.1`，避免用户误以为需要证书。

V1 代理稳定支持文本请求转换，并支持基础文本 SSE 流式转换。跨 `messages` 和 `responses` 时，后端会做基础工具字段映射：

- Anthropic `tools[].input_schema` -> OpenAI Responses `tools[].parameters`
- Anthropic `tool_use` / `tool_result` -> OpenAI Responses `function_call` / `function_call_output`
- OpenAI Responses `function_call` -> Anthropic `tool_use`

| 场景 | 行为 |
| --- | --- |
| `stream=false` 或未传 `stream` | 后端执行格式转换、转发、响应转换、usage 统计 |
| `stream=true` | 后端执行基础文本和基础 function call 流式事件转换，流结束后汇总 usage |
| 多模态、复杂 reasoning、厂商私有工具字段 | 不保证无损转换 |

前端在代理配置界面需要展示这个限制，尤其是跨格式代理时。

## 8. Token Usage 轮询

usage 只在本地代理开启且请求经过代理时统计。未代理 provider 显示“未代理，不统计”。

轮询建议：

```text
GET /api/agents/{agent_type}/usage
POST /api/agents/{agent_type}/usage/reset
GET /api/proxies
```

间隔 10 秒。不要做实时流式刷新。

usage 字段：

| 字段 | 说明 |
| --- | --- |
| `request_count` | 已完成代理请求数 |
| `input_tokens` | 输入 token |
| `output_tokens` | 输出 token |
| `total_tokens` | 总 token |
| `cache_creation_input_tokens` | Claude 可选缓存字段 |
| `cache_read_input_tokens` | Claude 可选缓存字段 |
| `last_request_at` | 最近请求时间 |

## 9. 代理状态

接口：

```text
GET /api/proxies
GET /api/proxies/{provider_id}
POST /api/proxies/{provider_id}/start
POST /api/proxies/{provider_id}/stop
POST /api/proxies/{provider_id}/restart
```

状态值：

| status | 含义 |
| --- | --- |
| `stopped` | 未运行 |
| `starting` | 启动中 |
| `running` | 运行中 |
| `error` | 启动或运行异常 |

端口冲突会返回 `PORT_IN_USE`，前端应把 `proxy_port` 字段标红并提示用户更换端口。

## 10. 前端错误处理建议

需要重点处理的错误码：

| code | 前端动作 |
| --- | --- |
| `CONFIG_PATH_EMPTY` | 引导用户先配置路径 |
| `CONFIG_FILE_MISSING` | 提示路径不正确或配置文件不存在 |
| `CONFIG_PARSE_ERROR` | 提示配置文件格式异常 |
| `PROVIDER_NAME_DUPLICATED` | 标记 provider 名称字段 |
| `PROVIDER_UPDATE_CONFLICT` | 提示刷新后重试 |
| `PORT_IN_USE` | 标记端口字段 |
| `TRANSFORM_UNSUPPORTED` | 展示代理能力限制 |
| `PROXY_TARGET_FAILED` | 展示目标网关错误 |
