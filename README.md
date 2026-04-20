# agent-learner

Reusable self-learning engine for agent workflows.

`agent-learner` provides a generic self-learning core plus installable
adapter overlays for Codex and Claude-style environments.

## What it provides
- generic learning lifecycle engine
- aggressive auto-promotion pipeline
- Codex adapter plugin
- Claude adapter plugin
- draft -> approved -> needs_review -> deprecated lifecycle

## Repository shape
- `src/agent_learner/` - core package
- `plugins/codex/` - Codex adapter overlay
- `plugins/claude/` - Claude adapter overlay
- `tests/` - lifecycle and adapter tests
- `docs/` - install and architecture docs
- `examples/` - example consumer repo outcomes

## Release gates

The project treats these as mandatory for a shippable first release:

1. adapter independence
2. one-command onboarding
3. promotion reliability

## Quick start

```bash
pipx install .
agent-learner bootstrap --target /path/to/repo
```

Alternative during development:

```bash
python3 -m pip install -e .
agent-learner bootstrap --target /path/to/repo
```

## Status
Scaffold in progress with:
- working Python CLI entry point
- Codex and Claude adapter installers
- one-command bootstrap
- lifecycle and bootstrap tests
- install and quickstart docs
