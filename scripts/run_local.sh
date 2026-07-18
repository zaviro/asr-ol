#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-config/config.yaml}"
MANAGE_FUNASR="${VOXKEEP_MANAGE_FUNASR:-1}"
FUNASR_HOST="${VOXKEEP_ASR_EXTERNAL_HOST:-127.0.0.1}"
FUNASR_PORT="${VOXKEEP_ASR_EXTERNAL_PORT:-10096}"
FUNASR_START_TIMEOUT_S="${VOXKEEP_FUNASR_START_TIMEOUT_S:-600}"

compose() {
  docker compose -f docker-compose.yml "$@"
}

wait_for_funasr() {
  uv run --python 3.11 python - "$FUNASR_HOST" "$FUNASR_PORT" "$FUNASR_START_TIMEOUT_S" <<'PY'
from __future__ import annotations

import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])
timeout = float(sys.argv[3])
deadline = time.monotonic() + timeout

while time.monotonic() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            raise SystemExit(0)
    except OSError:
        time.sleep(1.0)

raise SystemExit(f"FunASR did not become reachable at {host}:{port} within {timeout:.0f}s")
PY
}

if [[ "$MANAGE_FUNASR" == "1" ]]; then
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "docker compose is required to manage the FunASR service" >&2
    exit 1
  fi
  compose up -d funasr
fi

wait_for_funasr
exec uv run --python 3.11 python -m voxkeep run --config "$CONFIG_PATH"
