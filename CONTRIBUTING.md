# Contributing

Thanks for considering a contribution to `agent-learner`.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Common commands

```bash
python -m pytest -q
python -m build
agent-learner --help
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
