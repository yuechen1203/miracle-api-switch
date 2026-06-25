# miracle-api-switch 前端设计开发文档

## 1. 技术选型

| 项 | 建议 |
| --- | --- |
| 框架 | Vue 3 |
| 构建工具 | Vite |
| 语言 | TypeScript |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| HTTP 客户端 | Axios 或 Fetch 封装 |
| UI 基础 | 可选 Element Plus / Naive UI，也可自研轻量组件 |
| 图标 | lucide-vue-next |
| 动效 | CSS transition 为主，关键 logo 动效可用 CSS 或 Canvas |

前端不直接读写本地配置文件，所有本地路径探测、配置写入、缓存读写、代理启动都通过后端 API 完成。

## 2. 信息架构

### 2.1 页面结构

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/` | Dashboard | 展示 Codex 和 Claude Code 两个 Agent 卡片、全局后端连接状态 |
| `/agents/codex` | Codex 配置页 | 管理 Codex provider、配置路径、代理和 token 用量 |
| `/agents/claude-code` | Claude Code 配置页 | 管理 Claude Code provider、配置路径、代理和 token 用量 |
| `/settings` | 系统设置 | 缓存目录说明、备份管理、全局偏好、风险提示 |

首屏应是可操作的 Dashboard，不做营销式落地页。

### 2.2 全局布局

采用工作台式布局：

| 区域 | 内容 |
| --- | --- |
| 顶部栏 | Logo、产品名、后端连接状态、刷新按钮、设置入口 |
| 左侧导航 | Dashboard、Codex、Claude Code、Settings |
| 主内容区 | 当前页面核心工作区 |
| 右侧抽屉 | Provider 新建/编辑、路径配置、备份恢复等表单 |

移动端降级为顶部导航加卡片式纵向布局，Provider 表格切换为列表。

## 3. 视觉风格

### 3.1 设计方向

整体风格应偏“精密工具台”，不是营销官网。视觉关键词：

1. 干净、克制、可扫描。
2. 局部使用高亮色表达“切换”和“连接”。
3. 卡片、表格和表单保持紧凑，适合频繁操作。
4. 动效只用于状态变化、切换确认、代理运行状态，不做干扰性装饰。

### 3.2 配色建议

| 用途 | 建议 |
| --- | --- |
| 背景 | 浅灰白或近黑两套主题，首期可先做深色主题 |
| 主强调色 | 电青色，用于连接线、启用状态、主按钮 |
| 辅助强调色 | 琥珀色，用于未安装、警告和待初始化 |
| 危险色 | 红色，用于无效配置、写入失败 |
| 成功色 | 绿色，用于已安装、代理运行 |

避免整站只使用单一紫蓝渐变。Logo 可使用轻量动态线条表达 API 路由切换，但不要让背景成为大面积炫光。

### 3.3 Logo 设计

Logo 建议由三部分构成：

1. 左右两个端点代表 Agent 和目标网关。
2. 中间交叉折线代表格式转换。
3. 外圈微动扫描线代表本地代理运行。

动效建议：

| 状态 | 动效 |
| --- | --- |
| 后端连接正常 | Logo 低频呼吸光 |
| 代理运行中 | 中间线路有小型流动光点 |
| 后端断开 | Logo 降低亮度并停止流动 |

## 4. Dashboard 设计

### 4.1 Agent 状态卡片

Dashboard 放置两个主卡片：

| 卡片 | 信息 |
| --- | --- |
| Codex | 状态、配置文件路径、当前 provider、代理状态、今日请求数/token |
| Claude Code | 状态、配置文件路径、当前 provider、代理状态、今日请求数/token |

每张卡片操作：

| 操作 | 行为 |
| --- | --- |
| 进入配置 | 跳转到对应 Agent 页面 |
| 配置路径 | 打开路径配置抽屉 |
| 重新探测 | 调用后端 probe 接口 |

### 4.2 状态徽标

| 状态 | 文案 | 样式 |
| --- | --- | --- |
| `uninitialized` | 未初始化 | 灰色圆点 |
| `installed` | 已安装 | 绿色圆点 |
| `missing` | 未安装 | 橙色圆点 |
| `invalid` | 配置异常 | 红色圆点 |

状态徽标需要有 tooltip，说明当前判断依据。

## 5. Agent 详情页

### 5.1 顶部摘要区

内容：

1. Agent 名称和状态。
2. 当前配置路径。
3. 当前生效 provider。
4. 代理运行数量。
5. 10 秒自动刷新开关。

操作：

1. 配置路径。
2. 重新探测。
3. 新建 provider。
4. 刷新 provider 列表。

### 5.2 Provider 列表

桌面端使用表格，移动端使用列表。

| 列 | 说明 |
| --- | --- |
| 名称 | provider display name |
| Base URL | 脱敏显示域名和路径 |
| Model | 完整展示，可复制 |
| Key | 只显示掩码，例如 `sk-****abcd` |
| Proxy | 开关状态、端口、目标格式 |
| Usage | 请求数、输入 token、输出 token、总 token |
| 状态 | 已应用、未应用、代理运行、端口冲突 |
| 操作 | 使用、编辑、复制、删除、启动/停止代理 |

“使用”是高风险操作，需要确认弹窗说明将改写哪个配置文件，并展示备份策略。

### 5.3 Provider 表单

新建和编辑使用同一个右侧抽屉。

基础字段：

| 字段 | 组件 | 校验 |
| --- | --- | --- |
| 名称 | 文本输入 | 必填，Agent 内唯一 |
| API Key | 密码输入 | 新建必填，编辑可留空表示不变 |
| Base URL | URL 输入 | 必填，必须是 `http` 或 `https` |
| Model | 文本输入 | 必填 |

代理字段：

| 字段 | 组件 | 校验 |
| --- | --- | --- |
| 本地代理 api-switch | Switch | 默认关闭 |
| 代理端口 | 数字输入 | 1-65535，建议 1024 以上 |
| 目标 API 格式 | Segmented Control | `chat/completions`、`responses`、`messages` |
| 本地代理 URL 预览 | 只读文本 | 根据端口和协议生成 |

当开启代理时，表单要清楚展示：

1. 原始格式固定，不允许用户改。
2. 真实上游仍使用原来的 Base URL 和 API Key。
3. Agent 配置文件会写入本地代理 URL。

### 5.4 路径配置抽屉

字段：

| 字段 | 说明 |
| --- | --- |
| 配置路径 | 可输入目录或具体文件 |
| 解析结果 | 展示后端最终识别的目标文件路径 |
| 状态 | 文件存在、权限、格式解析结果 |

按钮：

1. 保存并探测。
2. 仅探测。
3. 清空路径。

由于浏览器不能可靠访问任意本地文件，V1 使用手动输入路径。未来如果包装桌面应用，可增加原生文件选择器。

## 6. Token 用量界面

### 6.1 展示位置

Token 用量在 Agent 详情页和 Provider 行内展示。前端每 10 秒轮询：

1. 当前 Agent provider 列表。
2. 代理状态。
3. usage 汇总。

### 6.2 指标

| 指标 | 说明 |
| --- | --- |
| 请求数 | 代理接收到并完成的请求数量 |
| 输入 token | prompt/input tokens |
| 输出 token | completion/output tokens |
| 总 token | 上游返回或后端累计计算 |
| 缓存创建 token | Claude usage 可用时展示 |
| 缓存读取 token | Claude usage 可用时展示 |
| 最近请求时间 | 最近一次代理成功统计时间 |

未开启代理的 provider 显示“未代理，不统计”。

## 7. 交互状态

| 场景 | 前端行为 |
| --- | --- |
| 后端断开 | 顶部状态红色，禁用写入类按钮，保留本地页面可读 |
| 配置路径无效 | Agent 卡片红色或橙色，详情页顶部展示修复入口 |
| 端口冲突 | 表单端口字段报错，禁止保存或启动 |
| 使用 provider 成功 | Toast 提示已写入配置，展示备份路径 |
| 使用 provider 失败 | 展示错误原因和是否已生成备份 |
| 删除 provider | 二次确认，若是当前已应用 provider，提示风险 |
| Key 字段编辑 | 默认不回显完整 key，留空表示不修改 |

## 8. API 对接约定

前端封装一个 API Client，统一处理：

1. 后端基础地址。
2. 错误结构。
3. loading 状态。
4. 请求取消。
5. 10 秒轮询生命周期。

主要调用：

| 前端场景 | 后端接口 |
| --- | --- |
| Dashboard 初始化 | `GET /api/agents` |
| 保存配置路径 | `PUT /api/agents/{agent_type}/config-path` |
| 重新探测 | `POST /api/agents/{agent_type}/probe` |
| 获取 provider | `GET /api/agents/{agent_type}/providers` |
| 新建 provider | `POST /api/agents/{agent_type}/providers` |
| 编辑 provider | `PATCH /api/agents/{agent_type}/providers/{provider_id}` |
| 删除 provider | `DELETE /api/agents/{agent_type}/providers/{provider_id}` |
| 使用 provider | `POST /api/agents/{agent_type}/providers/{provider_id}/apply` |
| 获取 token 用量 | `GET /api/agents/{agent_type}/usage` |
| 获取代理状态 | `GET /api/proxies` |

## 9. 前端校验规则

前端校验只做用户体验优化，后端仍必须再次校验。

| 字段 | 规则 |
| --- | --- |
| `display_name` | 非空，长度 1-64 |
| `api_key` | 新建非空，编辑可空 |
| `base_url` | 非空，合法 URL |
| `model` | 非空，长度 1-128 |
| `proxy_port` | 整数，1-65535，建议 1024-65535 |
| `target_format` | 三选一 |

## 10. 可访问性和响应式

1. 所有按钮提供文本或 tooltip。
2. 状态不能只依赖颜色，需要有文字和图标。
3. 表格在窄屏下变为列表。
4. 长 URL 和长 model 名允许复制，显示时中间省略。
5. 表单错误直接显示在字段下方。
6. 关键操作支持键盘聚焦和回车确认。

## 11. 开发交付建议

前端开发顺序：

1. 搭建 Vue 3 + 路由 + 状态管理。
2. 完成 API Client 和全局错误处理。
3. 实现 Dashboard 和 Agent 状态卡片。
4. 实现路径配置抽屉。
5. 实现 Provider 列表和表单。
6. 接入使用 provider、代理状态、usage 轮询。
7. 补齐响应式、动效、脱敏展示和确认弹窗。

验收重点：

1. 首次启动时两类 Agent 均显示未初始化。
2. 配置路径后状态能即时刷新。
3. 新建 provider 后刷新页面仍存在。
4. 使用 provider 会提示写入结果和备份路径。
5. 开启代理后 provider 行显示本地代理 URL、端口和目标格式。
6. token 用量每 10 秒刷新一次，未代理 provider 不显示虚假的用量。

