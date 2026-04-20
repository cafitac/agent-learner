# Quickstart

## Full bootstrap

```bash
uv sync --extra dev
uv run agent-learner bootstrap --target /path/to/consumer-repo
```

## Codex only

```bash
uv run agent-learner bootstrap --target /path/to/consumer-repo --adapters codex
```

Inspect which learned rules would be applied to a Codex task:

```bash
uv run agent-learner retrieve \
  --project-root /path/to/consumer-repo \
  --prompt "fix the prompt hook and keep tests green"
```

Render the exact compact context block for a prompt:

```bash
uv run agent-learner render-codex-context \
  --project-root /path/to/consumer-repo \
  --prompt "fix the prompt hook and keep tests green"
```

Run the full bootstrap -> seed -> hook simulation smoke path:

```bash
uv run agent-learner qa-codex-smoke
```

## Claude only

```bash
uv run agent-learner bootstrap --target /path/to/consumer-repo --adapters claude
```

Run the Claude session-end extraction smoke path:

```bash
uv run agent-learner qa-claude-smoke
```

Model-aware lifecycle example:

```bash
uv run agent-learner set-model --project-root /path/to/consumer-repo --model claude-opus-4-7
uv run agent-learner validate-rule --project-root /path/to/consumer-repo --name my-rule --model claude-opus-4-7
uv run agent-learner sweep --project-root /path/to/consumer-repo
```

See `docs/qa-codex-smoke.md` for the full consumer-style QA loop and `docs/adapter-convergence.md` for the shared control-plane direction.

CI now runs both `qa-codex-smoke` and `qa-claude-smoke` on Python 3.13 so the adapter-level smoke paths stay covered in automation.

CI now also installs the built wheel into a fresh environment and reruns CLI smoke checks so package-install behavior is verified, not just source-tree execution.

## npm wrapper preview

```bash
npx @cafitac/agent-learner codex install --target /path/to/consumer-repo
npx @cafitac/agent-learner codex qa --target /path/to/consumer-repo
```

Inside the repo checkout, the wrapper currently shells into the local Python core with `uv run agent-learner ...`.

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
