# Release Process

This repo has three release lanes:

1. **GitHub release** for source + built artifact visibility
2. **PyPI** for the Python core package (`agent-learner`)
3. **npm** for the plugin-style wrapper (`@cafitac/agent-learner`)

## Tag conventions

- `vX.Y.Z` -> GitHub release + built artifacts
- `py-vX.Y.Z` -> publish Python core to PyPI
- `npm-vX.Y.Z` -> publish npm wrapper to npm

## Recommended release order

1. Update `CHANGELOG.md`
2. Bump Python and npm versions together
3. Push `vX.Y.Z` for a GitHub release with attached artifacts
4. Push `py-vX.Y.Z` to publish the Python core
5. Verify `uvx --from "agent-learner[web]" agent-learner --help`
6. Push `npm-vX.Y.Z` to publish the npm wrapper

## Immediately after publish

Run the real user-facing smoke paths in this order:

1. `pipx install "agent-learner[web]"` -> `agent-learner doctor` -> `agent-learner dashboard`
2. `uvx --from "agent-learner[web]" agent-learner doctor`
3. `npx @cafitac/agent-learner doctor`
4. `npx @cafitac/agent-learner bootstrap --adapters codex --target /path/to/consumer-repo`

Use `docs/publish-smoke-checklist.md` for the exact matrix and optional paths.

## Why this order matters

The npm wrapper's published mode delegates into:

```bash
uvx --from "agent-learner[web]" agent-learner ...
```

So the Python core must be published before the npm wrapper is broadly usable outside a repo checkout.

## Pre-release checklist

```bash
npm test
npm pack --dry-run
uv run pytest -q
uv build
uv run agent-learner qa-codex-smoke
uv run agent-learner qa-claude-smoke
```

## Release artifacts

The `v*` workflow uploads:
- sdist
- wheel

and creates a GitHub Release so users can inspect/download the packaged build output.

## Coordinated version bump

Use the helper to bump both the Python core and npm wrapper together and open the next changelog section:

```bash
python scripts/release/bump_version.py 0.2.0 --dry-run
python scripts/release/bump_version.py 0.2.0
```

## Prerelease rehearsal

- `py-rc-vX.Y.Z` -> TestPyPI publish workflow
- `npm-rc-vX.Y.Z` -> npm prerelease (`next` tag) workflow

This lets you rehearse the publish order before cutting the final `py-v*` and `npm-v*` tags.

See `docs/prerelease-checklist.md` for the exact TestPyPI -> npm next rehearsal sequence before final release tags.

## Release readiness check

Before pushing release tags, run:

```bash
python scripts/release/release_check.py --version X.Y.Z
```

Use `--skip-commands` for a faster structural check or `--json` for automation.
For dashboard/runtime-specific release smoke validation, also run:

```bash
python scripts/release/publish_smoke_check.py --json
python scripts/release/published_runtime_smoke.py --project-root /path/to/consumer-repo --json --skip-commands
```

Note: the Python package keeps prerelease form like `0.2.0rc2`, while the npm wrapper is normalized to npm-safe semver like `0.2.0-rc2`.
