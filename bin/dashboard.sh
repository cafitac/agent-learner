#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_PROJECT_ROOT="${REPO_ROOT}"

if [[ $# -gt 0 && "$1" == "doctor" ]]; then
  shift
  if command -v uv >/dev/null 2>&1; then
    exec uv run --directory "${REPO_ROOT}" agent-learner doctor --project-root "${DEFAULT_PROJECT_ROOT}" "$@"
  elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    exec "${REPO_ROOT}/.venv/bin/python" -m agent_learner.cli.main doctor --project-root "${DEFAULT_PROJECT_ROOT}" "$@"
  else
    echo "[agent-learner] uv or .venv is required. Run: uv sync --extra web" >&2
    exit 1
  fi
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --directory "${REPO_ROOT}" agent-learner dashboard --project-root "${DEFAULT_PROJECT_ROOT}" "$@"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  exec "${REPO_ROOT}/.venv/bin/python" -m agent_learner.cli.main dashboard --project-root "${DEFAULT_PROJECT_ROOT}" "$@"
else
  echo "[agent-learner] uv or .venv is required. Run: uv sync --extra web" >&2
  exit 1
fi
