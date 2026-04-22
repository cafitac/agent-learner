# Install

If you want the shortest path, read this page in order:

1. **Recommended entrypoint**
2. **Published-package goal**
3. **npm-wrapper goal**
4. **Source checkout helper**

If you are validating a release after publish, jump to:

- `docs/publish-smoke-checklist.md`
- `docs/release-process.md`

## Recommended entrypoint

For most users, the shortest stable path is one line:

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
```

If you prefer the npm wrapper:

```bash
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

If you want a preflight check first, run `doctor` before `dashboard`.

Everything below is installation detail or alternative entrypoints.

## Recommended dev install

```bash
uv sync --extra dev
```

uv will create `.venv/` automatically and install the project in editable mode.

Manual venv alternative:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

Published-package goal:

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
```

Recommended default flow with a preflight check:

```bash
agent-learner doctor --project-root "$PWD"
agent-learner dashboard --project-root "$PWD" --open
```

The dashboard default port is `8766`. This avoids common local MCP/gateway
ports such as `8765`.

npm-wrapper goal:

```bash
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

The retrieval path uses `.agent-learner/index/rules.json` first and only loads the top matching rules into prompt context.
If you edit rule files manually, rebuild the index with:

```bash
agent-learner rebuild-index --project-root "$PWD"
```

Optional preflight check:

```bash
npx @cafitac/agent-learner@latest doctor --json
npx @cafitac/agent-learner@latest core doctor --project-root "$PWD" --format json
```

Source checkout helper:

```bash
./bin/dashboard.sh doctor
./bin/dashboard.sh --open
```

Optional Docker path:

```bash
docker compose up --build
```

Docker is a convenience option only. It should not be treated as the primary
or required OSS installation path.

## Codex adapter

```bash
agent-learner install-codex --target /path/to/consumer-repo
```

This creates:
- `.codex/hooks.json`
- `.codex/skills/session-wrap/`
- `.codex/skills/feedback-learning/`
- `.codex/skills/hermit-learner/`
- `.codex/references/scripts/auto_session_learning.py`
- `.codex/references/scripts/codex_prompt_context.py`
- `.agent-learner/learning/`
- `.agent-learner/events/codex/`
- `.agent-learner/candidates/`
- `.agent-learner/history/`
- `.agent-learner/state/processed-events/`

The Codex adapter wires two native hook paths:
- `UserPromptSubmit` -> retrieve approved learning assets and inject compact per-turn context
- `Stop` -> capture new learning candidates and refresh the dashboard

Canonical durable learning storage lives under `.agent-learner/learning/`.
`.codex/` remains the adapter and hook surface, not the system of record.
If legacy rules already exist under `.codex/references/learning/`, install/bootstrap
copies them into the canonical root and writes a migration marker so reads switch
cleanly without hiding existing assets.

Preview the prompt injection locally:

```bash
agent-learner render-codex-context \
  --project-root /path/to/consumer-repo \
  --prompt "refactor the codex prompt hook and keep tests updated"
```

Or run the end-to-end smoke path:

```bash
agent-learner qa-codex-smoke
```

## Claude adapter

```bash
agent-learner install-claude --target /path/to/consumer-repo
```

This creates:
- `.claude/settings.json`
- `.claude/hooks/auto_session_learning.py`
- `.claude/skills/session-wrap/`
- `.claude/skills/feedback-learning/`

## One-command onboarding

```bash
agent-learner bootstrap --target /path/to/consumer-repo
```

Default adapters:
- codex
- claude

Customize if needed:

```bash
agent-learner bootstrap --target /path/to/consumer-repo --adapters codex
agent-learner bootstrap --target /path/to/consumer-repo --adapters claude
```

## Independence guarantee

You can install either adapter first. Installing one should not require the other.

Claude event/candidate smoke path:

```bash
agent-learner qa-claude-smoke
```

Context/model utilities:

```bash
agent-learner doctor --project-root /path/to/consumer-repo
agent-learner dashboard --project-root /path/to/consumer-repo
agent-learner detect-context --project-root /path/to/consumer-repo
agent-learner set-model --project-root /path/to/consumer-repo --model claude-opus-4-7
agent-learner sweep --project-root /path/to/consumer-repo
```

Candidate review utilities:

```bash
agent-learner review-candidates --project-root /path/to/consumer-repo
agent-learner review-candidate --project-root /path/to/consumer-repo --candidate candidate-update-tests.md --action approve
agent-learner review-candidate --project-root /path/to/consumer-repo --candidate candidate-update-tests.md --action reject --reason "too generic"
agent-learner history --project-root /path/to/consumer-repo --rule keep-tests-updated --format json
agent-learner history --project-root /path/to/consumer-repo --decision revise_existing --since 2026-04-22T00:00:00Z
agent-learner history --project-root /path/to/consumer-repo --latest-per-rule --last 10
agent-learner history-summary --project-root /path/to/consumer-repo --by action --since 2026-04-22T00:00:00Z
agent-learner history-summary --project-root /path/to/consumer-repo --by adapter-decision --top 5
agent-learner overview --project-root /path/to/consumer-repo --format json
agent-learner dashboard-summary --project-root /path/to/consumer-repo --format json
agent-learner generate-dashboard --project-root /path/to/consumer-repo
agent-learner serve-dashboard --project-root /path/to/consumer-repo --port 8766
agent-learner serve-dashboard-fastapi --project-root /path/to/consumer-repo --port 8766
agent-learner dashboard --project-root /path/to/consumer-repo --open

FastAPI mode now exposes `/api/projects` and `/api/summary?project=<root>` so a frontend can switch between registered project brains from one global-oriented UI.
FastAPI serves frontend assets from the `agent-learner` app's own `frontend/dist`, while `--project-root` selects which project brain the API reads by default.
FastAPI is now the primary dashboard runtime; build the React frontend before using `serve-dashboard-fastapi`.
The `dashboard` command now attempts to build the frontend automatically when the bundled dist is missing. Use `--no-build` if you want a strict fail-fast path instead.

Frontend development (React + Vite scaffold):

```bash
cd frontend
npm install
npm run dev
npm run build
```

After building, `agent-learner serve-dashboard-fastapi --project-root /path/to/consumer-repo` will serve the built `frontend/dist` bundle.
```

CI now runs both `qa-codex-smoke` and `qa-claude-smoke` on Python 3.13 so the adapter-level smoke paths stay covered in automation.

CI now also installs the built wheel into a fresh environment and reruns CLI smoke checks so package-install behavior is verified, not just source-tree execution.

## npm wrapper preview

```bash
npm install -g @cafitac/agent-learner
agent-learner codex install --target /path/to/consumer-repo
```

For local development in this repo, the wrapper runs `uv run agent-learner ...`. For published usage, it is designed to fall back to `uvx --from "agent-learner[web]" agent-learner ...`.

Wrapper UX helpers:

```bash
npx @cafitac/agent-learner doctor
npx @cafitac/agent-learner version
```

`doctor` checks whether node/npm/uv/python are available and whether the wrapper will run in local-repo mode or published `uvx` mode.

See `docs/distribution.md` for the release order and npm-wrapper-vs-PyPI strategy.

Release automation now has separate `pypi-publish` and `npm-publish` workflows so the Python core can ship before the npm wrapper.

See `docs/release-process.md` for tag conventions, changelog expectations, and the recommended GitHub/PyPI/npm release order.

Lane-specific wrapper health checks:

```bash
npx @cafitac/agent-learner codex doctor --target /path/to/consumer-repo
npx @cafitac/agent-learner claude doctor --target /path/to/consumer-repo
```

These commands verify the expected adapter files/directories exist after installation and suggest the correct install command if anything is missing.
