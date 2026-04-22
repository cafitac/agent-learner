# Quickstart

## Recommended default flow

For most users:

```bash
agent-learner doctor --project-root /path/to/consumer-repo
agent-learner dashboard --project-root /path/to/consumer-repo --open
```

If the frontend bundle is missing, `dashboard` will try to build it unless you pass `--no-build`.

## Published Python package

```bash
pipx install "agent-learner[web]"
agent-learner doctor --project-root /path/to/consumer-repo
agent-learner dashboard --project-root /path/to/consumer-repo --open
```

## npm wrapper

```bash
npx @cafitac/agent-learner doctor
npx @cafitac/agent-learner dashboard --project-root /path/to/consumer-repo
```

## Source checkout

```bash
./bin/dashboard.sh doctor
./bin/dashboard.sh --open
```

## Optional Docker

```bash
docker compose up --build
```

Docker is optional convenience only. The primary path is still `agent-learner dashboard`.

## Useful next commands

```bash
agent-learner bootstrap --target /path/to/consumer-repo
agent-learner review-candidates --project-root /path/to/consumer-repo
agent-learner history --project-root /path/to/consumer-repo --latest-per-rule --last 10
agent-learner history-summary --project-root /path/to/consumer-repo --by adapter-decision
agent-learner overview --project-root /path/to/consumer-repo --format json
```

## If you are validating a release

```bash
python scripts/release/publish_smoke_check.py --json
./bin/publish-smoke.sh --json
```

Then follow `docs/publish-smoke-checklist.md`.
