#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if command -v uv >/dev/null 2>&1; then
  exec uv run --directory "${REPO_ROOT}" python scripts/release/publish_smoke_check.py "$@"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  exec "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/scripts/release/publish_smoke_check.py" "$@"
else
  echo "[agent-learner] uv or .venv is required. Run: uv sync --extra web" >&2
  exit 1
fi
