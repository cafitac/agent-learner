# Contributing

Thanks for considering a contribution to `agent-learner`.

## Development setup

Preferred with uv:

```bash
uv sync --extra dev
```

This creates and manages `.venv/` automatically.

Manual venv alternative:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
```

## Common commands

```bash
uv run pytest -q
uv build
uv run agent-learner --help
```

## Contribution guidelines

- Keep the core engine generic
- Keep adapter-specific behavior inside adapter code or adapter assets
- Do not introduce private product assumptions into the OSS repo
- Add or update tests for behavior changes
- Prefer small, reviewable changes

## Pull request checklist

- [ ] tests pass
- [ ] build succeeds
- [ ] docs are updated when behavior changes
- [ ] no private project-specific assets leaked into the repo
