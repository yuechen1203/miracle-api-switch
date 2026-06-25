# miracle-api-switch backend

Python/FastAPI 后端服务，负责：

- Agent 配置路径探测。
- Provider 组持久化管理。
- Codex `config.toml` 和 Claude Code `settings.json` 写入。
- 本地 API 格式转换代理。
- 代理链路上的 token usage 统计。

## 环境要求

需要 Python 3.11+。

```bash
cd back-app
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

默认缓存目录是项目根目录下的 `.hyc_cache/`，也就是 `back-app/` 的上一级目录。可以用环境变量覆盖：

```bash
MIRACLE_WORKSPACE_DIR=/path/to/project/root uvicorn app.main:app --host 127.0.0.1 --port 8765
```

## API

健康检查：

```bash
curl http://127.0.0.1:8765/api/health
```

全部 API 返回统一结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "..."
}
```

失败时 `success=false`，`error.code` 为前端可判断的错误码。

