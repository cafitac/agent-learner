# Quickstart

## Recommended default flow

For most users, use one line:

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
```

Or with npm:

```bash
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

If the frontend bundle is missing, `dashboard` will try to build it unless you pass `--no-build`.

## Published Python package

```bash
pipx install "agent-learner[web]" && agent-learner dashboard --project-root "$PWD" --open
```

## npm wrapper

```bash
npx @cafitac/agent-learner@latest dashboard --project-root "$PWD" --open
```

Optional preflight check:

```bash
npx @cafitac/agent-learner@latest doctor --json
npx @cafitac/agent-learner@latest core doctor --project-root "$PWD" --format json
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
agent-learner rebuild-index --project-root "$PWD"
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


## Wrapper convenience

Common wrapper aliases now work directly:

```bash
agent-learner install-codex --target "$PWD"
agent-learner install-claude --target "$PWD"
agent-learner rebuild-index --project-root "$PWD"
agent-learner bootstrap --target "$PWD"
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
