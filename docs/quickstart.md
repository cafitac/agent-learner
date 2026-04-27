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
agent-learner bootstrap
agent-learner review-candidates --project-root /path/to/consumer-repo
agent-learner history --project-root /path/to/consumer-repo --latest-per-rule --last 10
agent-learner history-summary --project-root /path/to/consumer-repo --by adapter-decision
agent-learner overview --project-root /path/to/consumer-repo --format json
```

## Hermes experimental quickstart

If you want to try the Hermes adapter specifically, use the bootstrap path:

```bash
agent-learner bootstrap --adapters hermes
agent-learner render-hermes-context --project-root "$PWD" --prompt "update hermes bootstrap wiring and keep tests green"
agent-learner render-hermes-context --project-root "$PWD" --prompt "update hermes bootstrap wiring and keep tests green" --format hook-json
agent-learner qa-hermes-smoke
```

If you explicitly want an isolated project-local Hermes home instead:

```bash
agent-learner bootstrap --adapters hermes --hermes-scope project --target "$PWD"
HERMES_HOME=.hermes hermes --accept-hooks
```

Notes:
- Hermes is still marked experimental.
- Default `bootstrap` now installs `codex,claude,hermes`.
- Hermes default install scope is `user`.
- The installer writes `~/.hermes/config.agent-learner.yaml` and `~/.hermes/AGENT_LEARNER_README.md` so existing Hermes users can merge hook entries safely.
- `qa-hermes-smoke` now checks direct script output plus `hermes hooks list/doctor/test` runtime wiring.

## If you are validating a release

```bash
python scripts/release/publish_smoke_check.py --json
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
