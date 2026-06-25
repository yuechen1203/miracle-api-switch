# miracle-api-switch 后端设计开发文档

## 1. 技术选型

| 项 | 建议 |
| --- | --- |
| 语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| ASGI Server | Uvicorn |
| HTTP 客户端 | httpx |
| TOML 处理 | `tomllib` 读取，写入使用可保留格式的 TOML 库 |
| JSON 处理 | 标准库 `json` |
| 文件锁 | 跨平台文件锁库或平台适配封装 |
| 数据校验 | Pydantic |

后端定位为本地服务，默认监听 `127.0.0.1`，不暴露到局域网。

## 2. 目录规划

未来实现代码时建议放在 `back-app/`：

| 目录/模块 | 职责 |
| --- | --- |
| `app/main` | FastAPI 应用入口 |
| `app/api` | REST API 路由 |
| `app/models` | Pydantic 请求和响应模型 |
| `app/services/cache_store` | `.hyc_cache` 文件读写 |
| `app/services/agent_probe` | 配置路径解析和状态探测 |
| `app/services/config_writer` | Codex/Claude 配置文件写入 |
| `app/services/provider_service` | provider CRUD 和应用 |
| `app/proxy/manager` | 本地代理生命周期管理 |
| `app/proxy/server` | 代理端口服务 |
| `app/proxy/transformers` | 请求和响应格式转换 |
| `app/services/usage_service` | token usage 解析、累计和查询 |
| `app/core/security` | key 脱敏、权限、日志过滤 |

## 3. 缓存存储

后端启动时：

1. 确认当前运行目录存在 `.hyc_cache/`。
2. 不存在则创建。
3. 加载各缓存文件。
4. 不存在的缓存文件使用空结构初始化。
5. 检查 `schema_version`，未来需要时执行迁移。

### 3.1 缓存文件

| 文件 | 数据 |
| --- | --- |
| `.hyc_cache/agents.json` | Agent 路径、当前 provider、最近探测状态 |
| `.hyc_cache/providers.codex.json` | Codex provider 列表 |
| `.hyc_cache/providers.claude_code.json` | Claude Code provider 列表 |
| `.hyc_cache/proxies.json` | provider 代理配置和最近运行状态 |
| `.hyc_cache/usage.codex.json` | Codex token 用量 |
| `.hyc_cache/usage.claude_code.json` | Claude Code token 用量 |
| `.hyc_cache/backups/` | 写配置前备份 |

### 3.2 写入原则

1. 所有缓存写入使用临时文件加原子替换。
2. 写入前加文件锁。
3. 写入后尽量 flush/fsync。
4. API Key 不进入普通日志。
5. 对前端返回时默认脱敏 API Key。

## 4. Agent 探测

### 4.1 路径解析

`agent_type=codex`：

| 输入 | 结果 |
| --- | --- |
| 空 | `uninitialized` |
| 目录 | 目录下的 `config.toml` |
| 文件 | 文件名必须是 `config.toml` |

`agent_type=claude_code`：

| 输入 | 结果 |
| --- | --- |
| 空 | `uninitialized` |
| 目录 | 目录下的 `settings.json` |
| 文件 | 文件名必须是 `settings.json` |

### 4.2 状态判断

| 状态 | 后端判断 |
| --- | --- |
| `uninitialized` | path 为空 |
| `missing` | path 不为空，但目标文件不存在 |
| `invalid` | 文件存在但无权限或解析失败 |
| `installed` | 文件存在，可读写，可解析 |

探测结果保存到 `.hyc_cache/agents.json`，但每次前端显式 probe 时重新检查文件系统。

## 5. REST API 设计

统一响应建议：

| 字段 | 说明 |
| --- | --- |
| `success` | 是否成功 |
| `data` | 成功数据 |
| `error` | 失败时错误对象 |
| `request_id` | 方便排查日志 |

错误对象：

| 字段 | 说明 |
| --- | --- |
| `code` | 机器可读错误码 |
| `message` | 用户可读错误 |
| `details` | 可选上下文，不能包含完整 key |

### 5.1 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 后端运行状态 |

返回内容包括版本号、缓存目录路径、启动时间。

### 5.2 Agent API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/agents` | 获取 Codex 和 Claude Code 状态 |
| `GET` | `/api/agents/{agent_type}` | 获取单个 Agent 详情 |
| `PUT` | `/api/agents/{agent_type}/config-path` | 保存配置路径并探测 |
| `POST` | `/api/agents/{agent_type}/probe` | 重新探测配置状态 |

`agent_type` 只允许 `codex` 和 `claude_code`。

### 5.3 Provider API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/agents/{agent_type}/providers` | provider 列表 |
| `POST` | `/api/agents/{agent_type}/providers` | 新建 provider |
| `GET` | `/api/agents/{agent_type}/providers/{provider_id}` | provider 详情 |
| `PATCH` | `/api/agents/{agent_type}/providers/{provider_id}` | 更新 provider |
| `DELETE` | `/api/agents/{agent_type}/providers/{provider_id}` | 删除 provider |
| `POST` | `/api/agents/{agent_type}/providers/{provider_id}/apply` | 应用 provider，改写目标配置 |

Provider 创建和更新字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `display_name` | string | 是 | 用户展示名 |
| `api_key` | string | 新建必填 | 编辑时为空表示不变 |
| `base_url` | string | 是 | 真实上游 URL |
| `model` | string | 是 | 模型名 |
| `proxy_enabled` | boolean | 是 | 是否启用代理 |
| `proxy_port` | integer | 代理开启时必填 | 本地端口 |
| `target_format` | string | 代理开启时必填 | `chat/completions`、`responses`、`messages` |

`apply` 支持参数：

| 字段 | 说明 |
| --- | --- |
| `dry_run` | 只验证和预览，不实际写配置 |
| `start_proxy` | 开启代理的 provider 是否同时启动本地代理，默认 true |

### 5.4 Proxy API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/proxies` | 获取全部代理运行状态 |
| `GET` | `/api/proxies/{provider_id}` | 获取单个 provider 代理状态 |
| `POST` | `/api/proxies/{provider_id}/start` | 启动代理 |
| `POST` | `/api/proxies/{provider_id}/stop` | 停止代理 |
| `POST` | `/api/proxies/{provider_id}/restart` | 重启代理 |

代理启动前检查：

1. provider 存在。
2. `proxy_enabled=true`。
3. 端口合法且未占用。
4. 真实 `base_url` 合法。
5. `api_key` 存在，除非目标网关不需要鉴权。

### 5.5 Usage API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/agents/{agent_type}/usage` | 获取该 Agent 下所有 provider 用量 |
| `GET` | `/api/agents/{agent_type}/providers/{provider_id}/usage` | 获取单个 provider 用量 |
| `POST` | `/api/agents/{agent_type}/providers/{provider_id}/usage/reset` | 重置单个 provider 用量 |

Usage 返回：

| 字段 | 说明 |
| --- | --- |
| `request_count` | 完成请求数 |
| `input_tokens` | 输入 token |
| `output_tokens` | 输出 token |
| `total_tokens` | 总 token |
| `cache_creation_input_tokens` | Claude 可选字段 |
| `cache_read_input_tokens` | Claude 可选字段 |
| `last_request_at` | 最近请求时间 |

## 6. 配置写入服务

### 6.1 Codex 写入

输入：agent path、provider、是否代理。

步骤：

1. 解析 `config.toml`。
2. 备份原文件。
3. 确保存在通用 provider `miracle`。
4. 设置顶层 `model_provider` 为 `miracle`。
5. 设置顶层 `model` 为 provider model。
6. 设置 provider 的 `name`、`base_url`、`wire_api`、`experimental_bearer_token`。
7. 原子写回。
8. 更新 `.hyc_cache/agents.json` 中当前 provider。

代理开启时：

| 字段 | 值 |
| --- | --- |
| `base_url` | 本地代理 URL |
| `wire_api` | `responses` |
| `experimental_bearer_token` | 空字符串或代理约定值 |

非代理时：

| 字段 | 值 |
| --- | --- |
| `base_url` | provider 真实 URL |
| `wire_api` | `responses` |
| `experimental_bearer_token` | 根据实现验证后的 key 策略写入 |

### 6.2 Claude Code 写入

输入：agent path、provider、是否代理。

步骤：

1. 解析 `settings.json`。
2. 备份原文件。
3. 确保存在 `env` 对象。
4. 写入 `ANTHROPIC_AUTH_TOKEN`。
5. 写入 `ANTHROPIC_BASE_URL`。
6. 写入五个模型字段。
7. 保留其他字段。
8. 原子写回。
9. 更新 `.hyc_cache/agents.json` 中当前 provider。

代理开启时，`ANTHROPIC_BASE_URL` 写本地代理 URL，真实 key 由本地代理持有。

## 7. 本地代理设计

### 7.1 生命周期

代理管理器按 provider 维度管理本地端口：

| 状态 | 说明 |
| --- | --- |
| `stopped` | 未运行 |
| `starting` | 正在启动 |
| `running` | 端口监听中 |
| `error` | 启动失败或运行异常 |

后端主服务停止时，应优雅关闭所有由本进程启动的代理。

### 7.2 本地 URL

默认建议：

| 字段 | 值 |
| --- | --- |
| Host | `127.0.0.1` |
| Scheme | `http` |
| Port | provider 配置端口 |

即 `http://127.0.0.1:{port}`。如果后续支持 HTTPS，需要证书路径和客户端信任策略。

### 7.3 路由兼容

代理需要接受 Agent 原始请求路径：

| Agent | 建议接收路径 |
| --- | --- |
| Codex | `/v1/responses`，兼容 `/responses` |
| Claude Code | `/v1/messages`，兼容 `/messages` |

转发到目标上游时根据 `target_format` 选择路径：

| 目标格式 | 转发路径 |
| --- | --- |
| `chat/completions` | `/v1/chat/completions` |
| `responses` | `/v1/responses` |
| `messages` | `/v1/messages` |

如果 provider 的 `base_url` 已包含版本路径，后端要避免重复拼接 `/v1`。建议实现 URL normalize 规则并在文档中固定。

### 7.4 鉴权

代理接收 Agent 请求时可以不要求本地 key，但转发真实上游必须使用 provider 保存的真实 `api_key`。

转发鉴权头：

| 目标格式 | 常见鉴权 |
| --- | --- |
| OpenAI 兼容 | `Authorization: Bearer <api_key>` |
| Claude messages | `x-api-key: <api_key>`，并设置必要版本头 |

具体头部允许在后续版本增加 provider 高级配置，以兼容不同网关。

### 7.5 转换器

内部建议定义一个标准中间结构，三种协议都先转换到中间结构，再转换到目标协议。

基础中间结构包括：

| 字段 | 说明 |
| --- | --- |
| `model` | 模型名 |
| `system` | system 指令 |
| `messages` | user/assistant 消息数组 |
| `temperature` | 可选 |
| `max_tokens` | 可选 |
| `stream` | 是否流式 |
| `tools` | 可选，首期可限制支持 |

首期转换范围建议：

| 能力 | V1 支持建议 |
| --- | --- |
| 普通文本输入输出 | 支持 |
| system/user/assistant | 支持 |
| stream | 支持基础文本增量 |
| tool calls | 可先标记实验性 |
| images/files/audio | 暂不承诺 |
| reasoning | 尽量透传，不保证等价 |

### 7.6 响应和错误转换

代理必须把目标上游响应转换回 Agent 原始格式：

| Agent | 返回给 Agent 的格式 |
| --- | --- |
| Codex | `responses` |
| Claude Code | `messages` |

错误响应也需要转换。比如目标上游返回 401，Codex 侧应收到符合 OpenAI 风格的错误结构；Claude Code 侧应收到符合 Anthropic 风格的错误结构。

## 8. Token 统计服务

### 8.1 统计时机

代理收到目标上游响应后：

1. 解析响应 JSON。
2. 提取 usage。
3. 累加到对应 provider 的 usage 缓存。
4. 控制台打印本次 usage。
5. 再将响应转换并返回给 Agent。

流式响应需要在流结束后汇总 usage。如果目标流式协议不返回 usage，则只记录请求数。

### 8.2 usage 字段归一

| 来源 | 输入 | 输出 | 总数 |
| --- | --- | --- | --- |
| `chat/completions` | `prompt_tokens` | `completion_tokens` | `total_tokens` |
| `responses` | `input_tokens` | `output_tokens` | `total_tokens` |
| `messages` | `input_tokens` | `output_tokens` | 输入加输出或上游总数 |

如果上游没有 total，则后端用输入加输出计算。

## 9. 安全和权限

1. 后端默认只监听 `127.0.0.1`。
2. 前端 CORS 只允许本地前端地址。
3. API Key 永不完整打印到日志。
4. 返回给前端的 key 默认脱敏。
5. `.hyc_cache` 尽量设置为当前用户私有权限。
6. 代理错误日志需要过滤 Authorization、x-api-key、Anthropic token 等敏感头。
7. 写配置文件前确认路径没有跳转到不安全位置，避免误写系统文件。

## 10. 并发和一致性

| 场景 | 处理 |
| --- | --- |
| 多标签页同时编辑 provider | 使用 `updated_at` 做乐观锁，可返回冲突错误 |
| 多请求同时写同一缓存 | 文件锁串行化 |
| 写配置时后端退出 | 临时文件加原子替换，保留备份 |
| 代理端口重复 | 启动前检查并返回 `PORT_IN_USE` |
| provider 删除但代理仍运行 | 删除前先停止代理，或阻止删除 |

## 11. 错误码建议

| 错误码 | 说明 |
| --- | --- |
| `AGENT_NOT_FOUND` | Agent 类型非法 |
| `CONFIG_PATH_EMPTY` | 配置路径为空 |
| `CONFIG_FILE_MISSING` | 目标配置文件不存在 |
| `CONFIG_PARSE_ERROR` | 配置文件解析失败 |
| `CONFIG_WRITE_FAILED` | 配置文件写入失败 |
| `PROVIDER_NOT_FOUND` | provider 不存在 |
| `PROVIDER_NAME_DUPLICATED` | provider 名称重复 |
| `PORT_IN_USE` | 代理端口被占用 |
| `PROXY_START_FAILED` | 代理启动失败 |
| `PROXY_TARGET_FAILED` | 目标上游请求失败 |
| `TRANSFORM_UNSUPPORTED` | 当前请求结构无法转换 |
| `CACHE_WRITE_FAILED` | 缓存写入失败 |

## 12. 测试策略

### 12.1 单元测试

1. 路径解析。
2. Agent 状态判断。
3. Provider CRUD。
4. Codex TOML 写入。
5. Claude JSON 写入。
6. URL normalize。
7. usage 字段解析。
8. 请求/响应基础格式转换。

### 12.2 集成测试

1. 新建 provider 后重启后端，数据仍存在。
2. 应用 Codex provider 后 `config.toml` 字段正确。
3. 应用 Claude Code provider 后 `settings.json` 字段正确。
4. 开启代理后端口可访问，配置文件写入本地 URL。
5. 模拟目标上游返回 usage，后端累计 token。
6. 端口冲突时返回明确错误。

### 12.3 回归测试样例

使用当前目录下的 `config.toml` 和 `settings.json` 作为基础样例，测试写入前后：

1. 未被设计修改的字段保持存在。
2. 目标字段更新为 provider 值。
3. 写入失败时备份仍可恢复。

## 13. 开发交付顺序

建议后端开发顺序：

1. FastAPI 项目骨架和健康检查。
2. `.hyc_cache` 初始化和缓存读写。
3. Agent 路径保存和探测。
4. Provider CRUD。
5. Codex 和 Claude Code 配置写入。
6. 使用 provider 的完整链路。
7. 代理管理器和端口服务。
8. 三类 API 格式基础转换。
9. token usage 统计。
10. 错误处理、安全脱敏、测试补齐。

V1 最小可用目标：

1. 能保存路径并识别已安装/未初始化/未安装/配置异常。
2. 能创建、编辑、删除、持久化 provider。
3. 能应用 provider 并正确改写配置文件。
4. 能在开启代理时启动本地端口并进行基础文本请求转换。
5. 能解析并缓存代理请求中的 token usage。
