# Install

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

## Codex adapter

```bash
agent-learner install-codex --target /path/to/consumer-repo
```

This creates:
- `.codex/hooks.json`
- `.codex/skills/session-wrap/`
- `.codex/skills/feedback-learning/`
- `.codex/skills/hermit-learner/`
- `.codex/references/learning/`
- `.codex/references/scripts/auto_session_learning.py`
- `.codex/references/scripts/codex_prompt_context.py`
- `.omx/wiki/session-log/`
- `.agent-learner/events/codex/`
- `.agent-learner/candidates/`
- `.agent-learner/state/processed-events/`

The Codex adapter wires two native hook paths:
- `UserPromptSubmit` -> retrieve approved learning assets and inject compact per-turn context
- `Stop` -> capture new learning candidates and refresh the dashboard

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
agent-learner detect-context --project-root /path/to/consumer-repo
agent-learner set-model --project-root /path/to/consumer-repo --model claude-opus-4-7
agent-learner sweep --project-root /path/to/consumer-repo
```

CI now runs both `qa-codex-smoke` and `qa-claude-smoke` on Python 3.13 so the adapter-level smoke paths stay covered in automation.

CI now also installs the built wheel into a fresh environment and reruns CLI smoke checks so package-install behavior is verified, not just source-tree execution.

## npm wrapper preview

```bash
npm install -g @cafibot/agent-learner
agent-learner codex install --target /path/to/consumer-repo
```

For local development in this repo, the wrapper runs `uv run agent-learner ...`. For published usage, it is designed to fall back to `uvx --from agent-learner agent-learner ...`.

Wrapper UX helpers:

```bash
npx @cafibot/agent-learner doctor
npx @cafibot/agent-learner version
```

`doctor` checks whether node/npm/uv/python are available and whether the wrapper will run in local-repo mode or published `uvx` mode.

See `docs/distribution.md` for the release order and npm-wrapper-vs-PyPI strategy.

Release automation now has separate `pypi-publish` and `npm-publish` workflows so the Python core can ship before the npm wrapper.

See `docs/release-process.md` for tag conventions, changelog expectations, and the recommended GitHub/PyPI/npm release order.

Lane-specific wrapper health checks:

```bash
npx @cafibot/agent-learner codex doctor --target /path/to/consumer-repo
npx @cafibot/agent-learner claude doctor --target /path/to/consumer-repo
```

These commands verify the expected adapter files/directories exist after installation and suggest the correct install command if anything is missing.
