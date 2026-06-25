#!/usr/bin/env bash
# miracle-api-switch 一键启动脚本
# 用法：./scripts/start.sh --host <server-ip> [--reinstall] [--no-front] [--no-back]
#
# 流程：
#   1. 检测端口占用，若 8765 / 5173 被占用则先尝试停掉旧的本工具进程。
#   2. 确认本地 Python (./python3/bin/python3) 已安装 back-app/requirements.txt 依赖。
#   3. 确认 front-app/node_modules 已存在；不存在则执行 npm install。
#   4. 后台启动后端 (uvicorn) 与前端 (vite dev)，把日志写到 .runtime/。
#   5. 健康检查通过后打印访问地址。
#   6. 通过 .runtime/pids 记录子进程，配合 scripts/stop.sh 关停。

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="$PROJECT_ROOT/python3/bin/python3"
BACK_DIR="$PROJECT_ROOT/back-app"
FRONT_DIR="$PROJECT_ROOT/front-app"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"
BACK_LOG="$RUNTIME_DIR/back.log"
FRONT_LOG="$RUNTIME_DIR/front.log"
PID_FILE="$RUNTIME_DIR/pids"

BACK_HOST="${MIRACLE_BACK_HOST:-${MIRACLE_BIND_HOST:-}}"
BACK_PORT="${MIRACLE_BACK_PORT:-8765}"
FRONT_HOST="${MIRACLE_FRONT_HOST:-${MIRACLE_BIND_HOST:-}}"
FRONT_PORT="${MIRACLE_FRONT_PORT:-5173}"

START_BACK=1
START_FRONT=1
FORCE_REINSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      [[ $# -ge 2 ]] || { echo "[start] --host requires an IP address" >&2; exit 2; }
      BACK_HOST="$2"
      FRONT_HOST="$2"
      shift 2
      ;;
    --back-host)
      [[ $# -ge 2 ]] || { echo "[start] --back-host requires an IP address" >&2; exit 2; }
      BACK_HOST="$2"
      shift 2
      ;;
    --front-host)
      [[ $# -ge 2 ]] || { echo "[start] --front-host requires an IP address" >&2; exit 2; }
      FRONT_HOST="$2"
      shift 2
      ;;
    --no-back)
      START_BACK=0
      shift
      ;;
    --no-front)
      START_FRONT=0
      shift
      ;;
    --reinstall)
      FORCE_REINSTALL=1
      shift
      ;;
    -h|--help)
      sed -n '1,18p' "$0"
      exit 0
      ;;
    *)
      echo "[start] unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$RUNTIME_DIR"

log()  { printf "[start] %s\n" "$*"; }
fail() { printf "[start] error: %s\n" "$*" >&2; exit 1; }

validate_bind_hosts() {
  if [[ $START_BACK -eq 1 && -z "$BACK_HOST" ]]; then
    fail "请指定后端监听 IP，例如 ./scripts/start.sh --host 192.168.1.20"
  fi
  if [[ $START_FRONT -eq 1 && -z "$FRONT_HOST" ]]; then
    fail "请指定前端监听 IP，例如 ./scripts/start.sh --host 192.168.1.20"
  fi

  for host in "$BACK_HOST" "$FRONT_HOST"; do
    [[ -z "$host" ]] && continue
    case "$host" in
      127.*|localhost|0.0.0.0|::1)
        fail "不允许绑定到 ${host}。请使用服务器实际网卡 IP，避免 localhost 或全网卡监听。"
        ;;
    esac
  done
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -E "[:.]${port}\$" -q
  else
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -E "[:.]${port}\$" -q
  fi
}

stop_recorded_pids() {
  [[ -f "$PID_FILE" ]] || return 0
  while IFS=' ' read -r label pid; do
    [[ -z "${pid:-}" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      log "stopping previous ${label} (pid=$pid)"
      kill "$pid" 2>/dev/null || true
    fi
  done < "$PID_FILE"
  sleep 1
  rm -f "$PID_FILE"
}

ensure_back_deps() {
  [[ -x "$PYTHON_BIN" ]] || fail "缺少本地 Python: $PYTHON_BIN"
  if [[ $FORCE_REINSTALL -eq 1 ]] \
    || ! "$PYTHON_BIN" -c "import fastapi, uvicorn, httpx, tomlkit" >/dev/null 2>&1; then
    log "安装 back-app 依赖 ..."
    "$PYTHON_BIN" -m pip install -q -r "$BACK_DIR/requirements.txt"
  else
    log "back-app 依赖已具备"
  fi
}

ensure_front_deps() {
  command -v npm >/dev/null 2>&1 || fail "未找到 npm，请先安装 Node.js 20+"
  if [[ $FORCE_REINSTALL -eq 1 ]] || [[ ! -d "$FRONT_DIR/node_modules" ]]; then
    log "安装 front-app 依赖 ..."
    (cd "$FRONT_DIR" && npm install --no-audit --no-fund)
  else
    log "front-app 依赖已具备"
  fi
}

start_back() {
  if port_in_use "$BACK_PORT"; then
    fail "后端端口 ${BACK_PORT} 已被占用，请先释放或调整 MIRACLE_BACK_PORT"
  fi
  log "启动后端 uvicorn ${BACK_HOST}:${BACK_PORT}"
  (
    cd "$BACK_DIR"
    MIRACLE_WORKSPACE_DIR="$PROJECT_ROOT" \
      nohup setsid "$PYTHON_BIN" -m uvicorn app.main:app \
        --host "$BACK_HOST" --port "$BACK_PORT" \
        >"$BACK_LOG" 2>&1 &
    echo "back $!" >> "$PID_FILE"
  )
}

start_front() {
  if port_in_use "$FRONT_PORT"; then
    fail "前端端口 ${FRONT_PORT} 已被占用，请先释放或调整 MIRACLE_FRONT_PORT"
  fi
  log "启动前端 vite ${FRONT_HOST}:${FRONT_PORT}"
  (
    cd "$FRONT_DIR"
    VITE_API_TARGET="http://${BACK_HOST}:${BACK_PORT}" \
      nohup setsid ./node_modules/.bin/vite \
      --host "$FRONT_HOST" --port "$FRONT_PORT" --strictPort \
      >"$FRONT_LOG" 2>&1 &
    echo "front $!" >> "$PID_FILE"
  )
}

wait_for_back() {
  local url="http://${BACK_HOST}:${BACK_PORT}/api/health"
  log "等待后端就绪 ($url)"
  for _ in $(seq 1 40); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  fail "后端未在 20s 内就绪，查看日志 $BACK_LOG"
}

wait_for_front() {
  local url="http://${FRONT_HOST}:${FRONT_PORT}/"
  log "等待前端就绪 ($url)"
  for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  fail "前端未在 30s 内就绪，查看日志 $FRONT_LOG"
}

validate_bind_hosts

stop_recorded_pids

[[ $START_BACK -eq 1 ]] && ensure_back_deps
[[ $START_FRONT -eq 1 ]] && ensure_front_deps

: > "$PID_FILE"

if [[ $START_BACK -eq 1 ]]; then
  start_back
  wait_for_back
fi

if [[ $START_FRONT -eq 1 ]]; then
  start_front
  wait_for_front
fi

log "全部就绪"
[[ $START_BACK -eq 1 ]] && log "  后端: http://${BACK_HOST}:${BACK_PORT}/api/health"
[[ $START_FRONT -eq 1 ]] && log "  前端: http://${FRONT_HOST}:${FRONT_PORT}/"
log "  日志: ${BACK_LOG} , ${FRONT_LOG}"
log "  停止: ./scripts/stop.sh"
