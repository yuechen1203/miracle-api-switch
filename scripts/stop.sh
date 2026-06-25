#!/usr/bin/env bash
# 停止 scripts/start.sh 启动的前后端进程。
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
PID_FILE="$PROJECT_ROOT/.runtime/pids"

if [[ ! -f "$PID_FILE" ]]; then
  echo "[stop] 没有找到 $PID_FILE，可能进程并非由 start.sh 启动。"
  exit 0
fi

stopped=0
while IFS=' ' read -r label pid; do
  [[ -z "${pid:-}" ]] && continue
  if kill -0 "$pid" 2>/dev/null; then
    echo "[stop] 关闭 $label (pid=$pid)"
    kill "$pid" 2>/dev/null || true
    stopped=$((stopped + 1))
  fi
done < "$PID_FILE"

sleep 1
while IFS=' ' read -r label pid; do
  [[ -z "${pid:-}" ]] && continue
  if kill -0 "$pid" 2>/dev/null; then
    echo "[stop] 强制结束 $label (pid=$pid)"
    kill -9 "$pid" 2>/dev/null || true
  fi
done < "$PID_FILE"

rm -f "$PID_FILE"
echo "[stop] 共关闭 $stopped 个进程"
