# Install

## Recommended dev install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
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
- `.omx/wiki/session-log/`

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
