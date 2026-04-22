# Publish Smoke Checklist

Use this checklist before or immediately after publishing `agent-learner` to
PyPI and `@cafitac/agent-learner` to npm.

You can also run the local structural smoke helper first:

```bash
python scripts/release/publish_smoke_check.py --json
./bin/publish-smoke.sh --json
```

And after publish, use the published-runtime helper:

```bash
python scripts/release/published_runtime_smoke.py --project-root /path/to/consumer-repo --json --skip-commands
```

The goal is simple:

- confirm the Python package installs and runs
- confirm the npm wrapper can reach the Python core
- confirm the dashboard UX works through the recommended paths

## Recommended smoke matrix

Check these paths in order:

1. **Python package path** (`pipx`)
2. **Published Python execution path** (`uvx`)
3. **npm wrapper path** (`npx`)
4. **Source checkout helper path** (`./bin/dashboard.sh`) — optional sanity check
5. **Docker Compose path** — optional sanity check only

Do not treat Docker as the primary publish smoke path.

## 1. Python package smoke (required)

From a clean shell:

```bash
pipx install "agent-learner[web]"
agent-learner doctor --project-root /path/to/consumer-repo
agent-learner dashboard --project-root /path/to/consumer-repo --open
```

Expected:

- install succeeds
- `doctor` returns a meaningful `verdict`
- `dashboard` launches without extra hidden setup
- if `--open` is used, the browser opens to the dashboard URL

## 2. Published Python execution smoke (required)

```bash
uvx --from "agent-learner[web]" agent-learner doctor --project-root /path/to/consumer-repo
uvx --from "agent-learner[web]" agent-learner dashboard --project-root /path/to/consumer-repo
```

Expected:

- `uvx` can resolve the published Python package
- the CLI behavior matches the direct `pipx` install path

## 3. npm wrapper smoke (required for npm release)

```bash
npx @cafitac/agent-learner doctor
npx @cafitac/agent-learner dashboard --project-root /path/to/consumer-repo
```

Expected:

- wrapper launches
- `doctor` reports a dashboard-oriented verdict/advice
- `dashboard` delegates correctly into the Python core

## 4. Source checkout helper smoke (recommended)

Inside a repo checkout:

```bash
./bin/dashboard.sh doctor
./bin/dashboard.sh --open
```

Expected:

- shell helper finds `uv` or `.venv`
- dashboard launches through the same main path as the published Python CLI

## 5. Docker Compose smoke (optional)

Only run this if you want the containerized path verified.

```bash
docker compose config
docker compose up --build
```

Expected:

- compose file is valid
- image builds
- dashboard becomes reachable on the published port

Again: Docker is a convenience path, not the primary OSS install path.

## Dashboard-specific checks

When the dashboard opens, verify:

- project selector renders
- local/global/merged rule views render
- candidate list renders
- recent history renders
- global promotion action works
- candidate approve / reject / needs-review actions work

## CLI checks

Also verify:

```bash
agent-learner history --project-root /path/to/consumer-repo --latest-per-rule --last 5
agent-learner history-summary --project-root /path/to/consumer-repo --by adapter-decision
agent-learner overview --project-root /path/to/consumer-repo --format json
```

Expected:

- no crashes
- output shape is stable
- overview / history surfaces agree with dashboard data

## Failure handling

If the Python package works but npm wrapper fails:

- confirm the Python package is already published and reachable through `uvx`
- confirm wrapper version and Python package version are compatible

If dashboard fails:

- run `doctor`
- confirm `verdict`
- follow the printed `remediations`
- confirm the selected port is not busy

## Release sign-off

Only call the release healthy when:

- `pipx` path passes
- `uvx` path passes
- `npx` path passes
- dashboard opens and actions work
- smoke commands above produce sane output

Optional sign-off:

- source checkout helper passes
- Docker Compose path passes
