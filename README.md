# agent-learner

Reusable learning control plane for coding-agent workflows.

`agent-learner` helps you:
- capture learned rules from agent work
- keep project-local and global brain knowledge separate
- review candidates and promote useful rules
- use a dashboard UI for history, rules, and promotions

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

1. Point `agent-learner` at a project
2. Run `doctor`
3. Open the dashboard
4. Review rules, candidates, and history
5. Promote reusable knowledge to the global brain when appropriate

## Core concepts

### Project brain vs global brain

- project-local knowledge lives under `<project>/.agent-learner/`
- reusable shared knowledge lives under `~/.agent-learner/global/`
- retrieval is local-first, then global

### Indexed retrieval and pruning

- rules are indexed into machine-readable metadata under `.agent-learner/index/rules.json`
- a human-readable summary is also written to `.agent-learner/index/index.md`
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
agent-learner dashboard --project-root /path/to/repo --open
agent-learner bootstrap --target /path/to/repo
agent-learner review-candidates --project-root /path/to/repo
agent-learner history --project-root /path/to/repo --latest-per-rule --last 10
agent-learner history-summary --project-root /path/to/repo --by adapter-decision
agent-learner overview --project-root /path/to/repo --format json
agent-learner rebuild-index --project-root /path/to/repo
```

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

- `docs/install.md`
- `docs/quickstart.md`
- `docs/architecture.md`
- `docs/adapter-convergence.md`
- `docs/distribution.md`
- `docs/publish-smoke-checklist.md`
- `docs/release-process.md`
- `docs/prerelease-checklist.md`

## Status

Current implemented areas:
- local/global brain split
- merged retrieval
- candidate/rule/history lifecycle
- dashboard UI
- global promotion and sync
- npm wrapper + source checkout helper

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
