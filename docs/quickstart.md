# Quickstart

## Full bootstrap

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
agent-learner bootstrap --target /path/to/consumer-repo
```

## Codex only

```bash
agent-learner bootstrap --target /path/to/consumer-repo --adapters codex
```

## Claude only

```bash
agent-learner bootstrap --target /path/to/consumer-repo --adapters claude
```
