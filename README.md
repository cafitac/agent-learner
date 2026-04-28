# agent-learner

Reusable learning control plane for coding-agent workflows.

`agent-learner` helps you:
- capture learned rules from agent work
- keep repo-scoped and global learning assets in one canonical global store
- review candidates and promote useful rules
- use a dashboard UI for history, rules, and promotions

It is a learning system, not a unified wiki layer.

It is designed to layer onto existing agent environments rather than replace them.

## Start here

If you want the shortest one-line setup, use one of these:

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

If you want a preflight check first, run `doctor` before `dashboard`.

The dashboard defaults to `127.0.0.1:8766` to avoid common local MCP/gateway
ports such as `8765`.

`doctor` tells you whether the dashboard can run now, what is missing, and the next command to use.

## Choose your path

### 1. Published Python package

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
```

### 2. npm / npx wrapper

```bash
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

### 3. Source checkout

```bash
./bin/dashboard.sh doctor
./bin/dashboard.sh --open
```

### 4. Optional Docker path

```bash
docker compose up --build
```

Docker is optional convenience only. It is not the primary OSS install path.

## Typical workflow

1. Install the adapter you want to use first
   - Codex is the most established path
   - Hermes is available as an explicit experimental opt-in
2. Run `doctor`
3. Open the dashboard
4. Review rules, candidates, and history
5. Promote reusable learning assets after review; repo scoping is tracked by metadata, not separate local stores

## Core concepts

### Global-first learning storage

- canonical durable learning lives under `AGENT_LEARNER_HOME` (default `~/.agent-learner/`)
- events, candidates, history, rules, and indexes are stored in that global home
- repo-specific behavior is selected by repo identity, learning scope, and provenance metadata rather than by a project-local storage root
- existing `<project>/.agent-learner/` and `.codex/references/learning/` assets are treated as legacy migration sources, not normal fallback stores
- `agent-learner storage-doctor --project-root "$PWD" --format json` reports the canonical home, global artifact counts, legacy source state, migration markers, warnings, and suggested next commands
- Codex, Claude, and Hermes can be installed at user scope while still resolving the active repo from `cwd`
- external wiki/KB systems remain separate and are not part of the canonical learning lifecycle

### Indexed retrieval and pruning

- rules are indexed into machine-readable metadata under `$AGENT_LEARNER_HOME/index/rules.json`
- a human-readable summary is also written to `$AGENT_LEARNER_HOME/index/index.md`
- retrieval uses the index first, then loads only the top matching rules
- `approved` rules are injected by default; `needs_review` and `deprecated` stay out unless explicitly requested
- use `agent-learner rebuild-index --project-root "$PWD"` if you want to force a full reindex after manual edits

### Main runtime

The primary UI/runtime path is:

- FastAPI backend
- built React dashboard frontend

Static dashboard generation and stdlib-only serving still exist, but they are secondary paths.

## Key commands

```bash
agent-learner doctor --project-root /path/to/repo
agent-learner storage-doctor --project-root /path/to/repo --format json
agent-learner dashboard --project-root /path/to/repo --open
agent-learner bootstrap
agent-learner bootstrap --adapters hermes
agent-learner review-candidates --project-root /path/to/repo
agent-learner history --project-root /path/to/repo --latest-per-rule --last 10
agent-learner history-summary --project-root /path/to/repo --by adapter-decision
agent-learner overview --project-root /path/to/repo --format json
agent-learner rebuild-index --project-root /path/to/repo
agent-learner update
```

Bootstrap note:
- `agent-learner bootstrap` is now the only install entrypoint
- default `bootstrap` installs `codex,claude,hermes`
- use `agent-learner bootstrap --adapters hermes` if you only want Hermes

## Repository shape

- `src/agent_learner/` — Python core
- `frontend/` — React + Vite dashboard UI
- `bin/` — shell / wrapper entrypoints
- `tests/` — CLI, lifecycle, wrapper, and dashboard tests
- `docs/` — install, architecture, release, and smoke docs

## Docs

- Start here:
  - `docs/install.md` — install and run paths
  - `docs/quickstart.md` — shortest command sequences
- Release and publish:
  - `docs/publish-smoke-checklist.md` — post-publish smoke matrix
  - `docs/release-process.md` — tag order and release flow
  - `docs/distribution.md` — Python core vs npm wrapper strategy
- Architecture:
  - `docs/architecture.md`
  - `docs/adapter-convergence.md`
  - `docs/scope-learning-system.md`
  - `docs/storage-independence-and-provenance.md`

- `docs/install.md`
- `docs/quickstart.md`
- `docs/architecture.md`
- `docs/adapter-convergence.md`
- `docs/scope-learning-system.md`
- `docs/storage-independence-and-provenance.md`
- `docs/distribution.md`
- `docs/publish-smoke-checklist.md`
- `docs/release-process.md`
- `docs/prerelease-checklist.md`

## Status

Current implemented areas:
- local/global learning split
- merged retrieval
- candidate/rule/history lifecycle
- dashboard UI
- global promotion and sync
- npm wrapper + source checkout helper
- Hermes experimental adapter with user-scope config.yaml-based hook wiring and runtime smoke coverage

## Release note

If you are validating a release, use:

```bash
python scripts/release/publish_smoke_check.py --json
python scripts/release/published_runtime_smoke.py --project-root /path/to/repo --json --skip-commands
```

Or from a source checkout:

```bash
./bin/publish-smoke.sh --json
```

Then follow `docs/publish-smoke-checklist.md`.


## Wrapper convenience

Common wrapper aliases now work directly:

```bash
agent-learner rebuild-index --project-root "$PWD"
agent-learner bootstrap
agent-learner bootstrap --adapters hermes
agent-learner update
agent-learner completion zsh
```


## Shell completion

Zsh:

```bash
echo 'source <(agent-learner completion zsh)' >> ~/.zshrc
source ~/.zshrc
```

Bash:

```bash
echo 'source <(agent-learner completion bash)' >> ~/.bashrc
source ~/.bashrc
```
