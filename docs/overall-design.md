# miracle-api-switch 总体设计文档

## 1. 项目目标

miracle-api-switch 是一个用于管理 AI Agent 工具 API Key、Base URL、模型名以及本地格式转换代理的桌面本地化 Web 工具。首期支持两类 Agent：

| Agent | 配置文件 | 原始请求格式 | 说明 |
| --- | --- | --- | --- |
| Codex | `config.toml` | `responses` | 使用一个通用 provider，切换 provider 时改写该 provider 的配置 |
| Claude Code | `settings.json` | `messages` | 切换 provider 时改写 `env` 中的 Anthropic 相关字段 |

系统采用前后端分离：

| 目录 | 职责 |
| --- | --- |
| `front-app/` | Vue 前端应用，负责状态展示、provider 管理、代理配置、token 用量查看 |
| `back-app/` | Python 后端服务，负责配置文件读写、缓存持久化、代理服务管理、请求格式转换 |
| `.hyc_cache/` | 后端运行时自动创建，保存路径配置、provider 组、代理配置、token 用量、配置备份等缓存数据 |

本次文档只定义设计，不包含实现代码。

## 2. 核心概念

### 2.1 Agent 配置状态

由于首期不自动推断默认配置目录，Codex 和 Claude Code 初次启动时配置路径为空，状态均为 `未初始化`。

| 状态 | 触发条件 | 前端标识 |
| --- | --- | --- |
| `uninitialized` | 配置路径为空 | 灰色标识，提示需要配置路径 |
| `installed` | 配置路径存在，目标配置文件存在且格式可解析 | 绿色标识，提示已安装 |
| `missing` | 已配置路径，但目标配置文件不存在 | 橙色标识，提示未安装或路径错误 |
| `invalid` | 文件存在但 JSON/TOML 解析失败，或权限不足 | 红色标识，提示配置不可用 |

这里的“已安装”只代表目标配置文件存在且可被工具读写，不代表系统中一定存在对应命令行程序。

### 2.2 配置路径

前端提供手动配置入口。后端接收路径后按以下规则解析：

| 输入类型 | Codex | Claude Code |
| --- | --- | --- |
| 目录路径 | 拼接 `config.toml` | 拼接 `settings.json` |
| 文件路径 | 必须文件名为 `config.toml` | 必须文件名为 `settings.json` |

保存路径后立即探测并刷新状态。

### 2.3 Provider 组

Provider 组是用户保存的一组可切换配置，包含：

| 字段 | 说明 |
| --- | --- |
| `id` | 后端生成的唯一 ID |
| `agent_type` | `codex` 或 `claude_code` |
| `display_name` | 用户自定义名称 |
| `api_key` | 真实上游 API Key，本地缓存保存，前端默认脱敏展示 |
| `base_url` | 真实上游网关 URL |
| `model` | 模型名 |
| `proxy_enabled` | 是否启用本地 api-switch 代理 |
| `proxy_port` | 本地代理端口 |
| `target_format` | 代理转发到真实上游时使用的目标格式 |
| `created_at` / `updated_at` | 创建和更新时间 |

Codex 和 Claude Code 的 provider 组分文件保存，避免不同 Agent 的数据互相污染。

### 2.4 本地代理

本地代理只在 provider 开启 `api-switch` 时生效。不开启代理时，工具只修改对应 Agent 的配置文件，不经过后端转发请求，也无法统计 token 消耗。

代理转换方向由 Agent 原始格式和 provider 目标格式共同决定：

| Agent | 进入本地代理的原始格式 | 可选目标格式 |
| --- | --- | --- |
| Codex | `responses` | `chat/completions`、`responses`、`messages` |
| Claude Code | `messages` | `chat/completions`、`responses`、`messages` |

示例：Codex provider 开启代理，端口 `5555`，目标格式 `messages`。工具将 Codex 配置改为本地代理地址，Codex 发出的 `responses` 请求进入代理后转换为 `messages` 请求，转发到真实上游；真实上游响应再转换回 `responses` 格式返回给 Codex。

## 3. 总体架构

### 3.1 组件划分

| 组件 | 职责 |
| --- | --- |
| Vue 前端 | 展示 Agent 状态、维护 provider 表单、触发应用配置、展示代理状态和 token 用量 |
| FastAPI 后端 | 提供 REST API、读写缓存、读写 Agent 配置文件、启动和关闭代理服务 |
| 配置写入服务 | 安全修改 `config.toml` 与 `settings.json`，写入前生成备份 |
| 缓存服务 | 读写 `.hyc_cache` 下的多份缓存文件，支持原子写入和文件锁 |
| 代理管理器 | 根据 provider 配置启动本地端口服务，维护端口占用和运行状态 |
| 格式转换器 | 负责 `responses`、`chat/completions`、`messages` 三类协议之间的请求和响应转换 |
| Token 统计器 | 代理响应返回后解析 `usage` 字段，累计到缓存文件并打印控制台日志 |

### 3.2 数据流

1. 后端启动，创建 `.hyc_cache/`。
2. 后端读取缓存中的 Agent 路径、provider 组、代理配置、token 用量。
3. 前端请求 Agent 列表，展示 Codex 和 Claude Code 两个入口。
4. 用户配置某个 Agent 的配置文件路径，后端探测文件存在性和格式。
5. 用户创建 provider 组，后端保存到对应缓存文件。
6. 用户选择“使用”某个 provider：
   - 如果未开启代理：后端直接改写目标 Agent 配置文件。
   - 如果开启代理：后端启动或复用本地代理端口，并将 Agent 配置文件写为本地代理 URL。
7. Agent 后续请求：
   - 未代理：请求直接打到真实上游，后端不可见。
   - 已代理：请求进入本地代理，转换格式后转发真实上游，响应转换回原始格式，同时统计 token。
8. 前端每 10 秒轮询 token 用量和代理状态。

## 4. 配置文件写入规则

### 4.1 Codex `config.toml`

Codex 只维护一个通用 provider，推荐固定 provider ID 为 `miracle`。应用 provider 时：

| 字段 | 未开启代理 | 开启代理 |
| --- | --- | --- |
| `model_provider` | `miracle` | `miracle` |
| `model` | provider 的 `model` | provider 的 `model` |
| `[model_providers.miracle].name` | provider 的 `display_name` | provider 的 `display_name` 或追加代理标识 |
| `[model_providers.miracle].base_url` | provider 的真实 `base_url` | 本地代理 URL |
| `[model_providers.miracle].wire_api` | `responses` | `responses` |
| `[model_providers.miracle].experimental_bearer_token` | provider 的 key 写入策略 | 空字符串或本地代理约定值 |

注意：Codex 的 token 字段已统一写入 `experimental_bearer_token`。旧 `env_key` 仅作为读取兼容字段。

| 策略 | 行为 | 风险 |
| --- | --- | --- |
| 兼容需求策略 | 将用户输入 key 写入 `experimental_bearer_token` | 依赖 Codex 支持该实验字段 |
| 安全代理策略 | 开启本地代理时该字段置空，由本地代理接管鉴权 | 请求必须经过本地代理 |

若开启本地代理，建议 Agent 配置中的 key 置空，由本地代理持有真实上游 key 并向目标网关加鉴权头。

### 4.2 Claude Code `settings.json`

应用 provider 时改写 `env` 字段：

| 字段 | 未开启代理 | 开启代理 |
| --- | --- | --- |
| `ANTHROPIC_AUTH_TOKEN` | provider 的 `api_key` | provider 的 `api_key` |
| `ANTHROPIC_BASE_URL` | provider 的真实 `base_url` | 本地代理 URL |
| `ANTHROPIC_MODEL` | provider 的 `model` | provider 的 `model` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | provider 的 `model` | provider 的 `model` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | provider 的 `model` | provider 的 `model` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | provider 的 `model` | provider 的 `model` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | provider 的 `model` | provider 的 `model` |

其他已有字段应原样保留，例如样例中的 `language`。

### 4.3 写入安全

每次写入配置文件前必须：

1. 解析原文件，确认格式有效。
2. 生成备份到 `.hyc_cache/backups/`。
3. 只改写目标字段，保留未知字段和用户原有格式中可保留的信息。
4. 使用临时文件加原子替换写入，避免写到一半损坏配置。
5. 如果写入失败，返回明确错误并保留备份路径。

## 5. 缓存文件设计

`.hyc_cache/` 首次启动自动创建。不同类型数据使用不同缓存文件。

| 文件 | 内容 |
| --- | --- |
| `.hyc_cache/agents.json` | Agent 配置路径、最近探测结果、当前选中的 provider |
| `.hyc_cache/providers.codex.json` | Codex provider 组 |
| `.hyc_cache/providers.claude_code.json` | Claude Code provider 组 |
| `.hyc_cache/proxies.json` | 已配置代理端口、目标格式、运行状态快照 |
| `.hyc_cache/usage.codex.json` | Codex provider 的 token 用量累计 |
| `.hyc_cache/usage.claude_code.json` | Claude Code provider 的 token 用量累计 |
| `.hyc_cache/backups/` | 配置文件写入前的备份 |

缓存文件建议保存 `schema_version`，方便后续升级迁移。

API Key 属于敏感信息。首期如果按需求保存在缓存文件中，应至少做到：

1. `.hyc_cache` 和 key 文件权限尽量设置为仅当前用户可读写。
2. 前端接口默认返回脱敏 key，只在编辑时由用户重新输入或显式请求显示。
3. 后端日志不打印完整 key。
4. token 统计、代理日志、错误堆栈均不得包含完整鉴权头。

## 6. Token 用量统计

Token 统计只在本地代理开启时可用，因为只有代理路径能看到真实响应。

### 6.1 支持解析字段

| 目标格式 | 常见 usage 字段 |
| --- | --- |
| `chat/completions` | `usage.prompt_tokens`、`usage.completion_tokens`、`usage.total_tokens` |
| `responses` | `usage.input_tokens`、`usage.output_tokens`、`usage.total_tokens` |
| `messages` | `usage.input_tokens`、`usage.output_tokens`、`usage.cache_creation_input_tokens`、`usage.cache_read_input_tokens` |

### 6.2 展示策略

1. 后端每次代理请求完成后解析 usage，累加到 provider 对应的 usage 缓存文件。
2. 后端控制台打印本次请求 token 和累计 token。
3. 前端无需实时流式更新，每 10 秒轮询一次 usage 接口。
4. 如果目标网关未返回 usage 字段，记录一次请求数，但 token 数不增加，并在调试日志中提示。

## 7. 边界和限制

### 7.1 格式转换限制

三种 API 格式并非完全等价，特别是以下能力：

| 能力 | 风险 |
| --- | --- |
| 流式响应 | SSE event 类型和增量结构不同，需要单独转换 |
| 工具调用 | OpenAI tools、Responses tool calls、Claude tool_use/tool_result 结构差异较大 |
| reasoning 字段 | 不同厂商暴露方式不同，可能无法无损转换 |
| 多模态输入 | 图片、文件、音频字段差异大，首期建议只声明文本优先支持 |
| 缓存控制 | Claude prompt cache 与 OpenAI cache 字段不完全等价 |
| 错误响应 | 需要转换为原始 Agent 能识别的错误格式 |

建议首期明确支持文本对话、基础 system/user/assistant 消息、普通非工具流式响应；工具调用和多模态作为后续增强。

### 7.2 HTTPS 本地代理问题

需求示例中展示 `https://127.0.0.1:5555`。实际实现时：

| 方案 | 优点 | 问题 |
| --- | --- | --- |
| 默认 `http://127.0.0.1:{port}` | 简单稳定，Agent 通常可访问本地 HTTP | 与示例中的 HTTPS 不完全一致 |
| 支持 HTTPS | 更符合示例 | 需要证书，很多客户端会拒绝自签名证书 |

建议 V1 默认 HTTP，前端展示协议可配置；如果启用 HTTPS，需要提供证书路径配置和证书信任说明。

### 7.3 浏览器本地路径限制

前端运行在浏览器中，无法直接弹出系统级文件选择器访问任意路径，除非未来包装为 Electron/Tauri 桌面应用。V1 建议提供路径文本输入，由后端验证路径是否存在。

### 7.4 端口冲突

开启代理时必须检查端口是否被占用。如果端口已占用：

1. 阻止启用并返回明确错误。
2. 前端提示用户更换端口。
3. 不应自动抢占或杀死其他进程。

### 7.5 并发写入

同一时间多个前端标签页可能同时操作同一 provider 或配置文件。后端需要文件锁和最后更新时间校验，避免配置被后写入覆盖。

## 8. 优化建议

1. Provider 列表支持导入/导出脱敏配置，方便迁移。
2. API Key 长期建议迁移到系统 keychain，缓存文件只保存引用。
3. 代理转换器先做严格的最小可用矩阵，避免承诺无损支持所有厂商扩展字段。
4. 配置写入前提供“预览变更”能力，显示将修改哪些字段。
5. 配置恢复入口允许用户从 `.hyc_cache/backups/` 选择备份回滚。
6. 后端提供 `dry_run` 参数，用于只验证 provider 是否能写入，不实际修改配置。
7. 后续可支持自动探测常见路径，但默认仍保持空路径，避免误改用户文件。
