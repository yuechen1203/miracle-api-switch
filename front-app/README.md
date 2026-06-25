# miracle-api-switch 前端

Vue 3 + Vite + TypeScript 工具台前端，配合 `back-app` 一起使用，用于管理 Codex 与 Claude Code 的 Provider、本地代理和 Token 用量。

## 环境要求

- Node.js 20 或以上（仓库当前用的是 `node v24.14.1`）
- 已经按 `back-app/README.md` 启动后端，或使用根目录 `scripts/start.sh` 一键启动前后端。

## 快速开始

```bash
cd front-app
npm install
npm run dev
```

`npm run dev` 是本机开发模式，默认监听 `http://127.0.0.1:5173`，Vite 内置 `/api` 反向代理默认指向 `http://127.0.0.1:8765`。

远程部署或多人访问时使用根目录的一键脚本，并显式绑定服务器网卡 IP：

```bash
./scripts/start.sh --host 192.168.12.39
```

该模式会同时启动后端和前端，并把前端 `/api` 代理到同一个指定 IP 的后端端口。脚本会拒绝绑定 `127.0.0.1`、`localhost` 和 `0.0.0.0`，避免远程 IDE 的 localhost 端口转发继续生效。

如果需要手动换后端地址，可以设置 `VITE_API_TARGET`：

```bash
VITE_API_TARGET=http://192.168.12.39:8765 npm run dev
```

生产构建走同源 `/api`，建议把构建产物和后端反向代理放到同一个域名下。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 本地开发，热更新，默认监听 127.0.0.1:5173 |
| `npm run build` | 生产构建，输出到 `dist/` |
| `npm run preview` | 预览构建产物，监听 4173 |
| `npm run typecheck` | 单独跑 `vue-tsc --noEmit` |

## 目录结构

```
src/
  api/         统一 axios 客户端，封装 success/data/error 与 BackendError
  components/  自研基础组件（按钮、表单、抽屉、Modal、Toast、Logo、状态点等）
  layouts/     AppShell 顶栏 + 侧边导航布局
  router/      Hash 路由配置
  stores/      Pinia stores（app、agents、providers、usage）
  styles/      全局 CSS 与设计令牌
  types/       后端 API TypeScript 类型
  utils/       格式化、复制等小工具
  views/       Dashboard / AgentView / SettingsView
```

## 设计约定

- 深色优先工具台，强调色锁定 `--accent`（青绿），不引入第二种主色。
- 不依赖第三方 UI 组件库，所有交互组件都在 `src/components/` 自研，方便统一改色和密度。
- 图标统一使用 `lucide-vue-next`，禁止内联手绘 SVG 图标。
- 圆角层级 `4 / 6 / 8 / 12` 一套，按钮 / 输入 / 卡片 / 抽屉对应使用。
- 状态既有颜色也有文字，符合可访问性最低要求。
- 任何会改写本地 `config.toml`、`settings.json` 的操作（应用 Provider）都会先 `dry_run=true` 预览改动字段和备份路径，再让用户在 Modal 内二次确认。

## 与后端的契约要点

详细约束见 [backend-contract-notes.md](./backend-contract-notes.md)，前端落地时已遵守：

- 所有业务接口先判断 `success` / `error.code`，不依赖 HTTP 状态码。
- Provider 编辑表单中 `api_key` 留空表示不修改，新建必填。
- 本地代理 URL 一律展示为 `http://127.0.0.1:{port}`，不会出现 HTTPS。
- Provider 表单内明确提示基础文本流式转换已支持，工具调用、reasoning、多模态流事件暂不保证无损。
- Usage 数据 10 秒轮询，不做实时流式刷新；未启用代理的 Provider 不展示虚假用量。
- 端口冲突 `PORT_IN_USE`、重名 `PROVIDER_NAME_DUPLICATED` 等错误码会定位到对应字段。

## 主要页面

- `/` Dashboard：双 Agent 概览卡，含状态、当前 Provider、运行中代理数量、聚合 Token 用量。
- `/agents/codex`、`/agents/claude-code` Agent 详情页：顶部摘要 + Provider 表格 + 新建/编辑抽屉 + 应用/删除确认弹窗。
- `/settings` 系统设置：后端连接信息、缓存目录、Provider 与代理汇总、安全提示。

## 常见问题

- **顶部提示“无法连接后端服务”**：本机开发时确认后端在 `127.0.0.1:8765`；远程部署时确认使用 `./scripts/start.sh --host <服务器IP>` 启动，并访问 `http://<服务器IP>:5173`。
- **新建 Provider 时报 `PORT_IN_USE`**：换一个空闲端口，建议 1024 以上。
- **应用 Provider 后 Agent 状态仍是“未安装”**：先到 Dashboard 或详情页的“配置路径”抽屉，粘贴正确的 `config.toml` / `settings.json` 路径，再重新探测。
- **Token 用量一直是 0**：只有开启本地代理并且请求经过 `http://127.0.0.1:{port}` 时才会统计；未代理 Provider 不会累加。

## 构建产物部署

```bash
npm run build
# dist/ 即静态资源
```

生产部署时建议用 Nginx 等反向代理把 `dist/` 静态文件和后端 `/api` 放在同一个 origin 下，避免跨域并保留 `request_id` 透传。
