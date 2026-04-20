# Distribution Strategy

`agent-learner` now has two delivery layers:

1. **Python core** — the authoritative engine (`agent-learner` on PyPI)
2. **npm wrapper** — plugin-style installation UX (`@cafitac/agent-learner` on npm)

## Why both exist

- The real implementation and shared control plane live in the Python package.
- Codex/plugin-style installation UX is better served by npm.
- The wrapper keeps UX npm-native without forcing an immediate rewrite of the core.

## Release order

Publish in this order:

1. **PyPI first**
   - publish `agent-learner` Python package
   - verify `uvx --from agent-learner agent-learner --help`
2. **npm second**
   - publish `@cafitac/agent-learner`
   - wrapper published-mode depends on the Python package already being resolvable by `uvx`

If npm is published before PyPI, wrapper commands outside the repo checkout will fail because published-mode shells into:

```bash
uvx --from agent-learner agent-learner ...
```

## Local development

Inside this repo checkout the wrapper uses:

```bash
uv run agent-learner ...
```

So local wrapper development does **not** require the Python package to be on PyPI.

## npm package commands

```bash
npm test
npm pack --dry-run
node bin/agent-learner.cjs doctor
node bin/agent-learner.cjs version
```

## Publishing

### npm wrapper

Workflow: `.github/workflows/npm-publish.yml`

Requirements:
- `NPM_TOKEN` secret configured
- Python core already published and reachable through `uvx`

Manual publish fallback:

```bash
npm test
npm pack --dry-run
npm publish --access public
```


## Version coordination

For now, keep the Python core version and npm wrapper version aligned.

Recommended rule:
- bump both together for user-visible releases
- publish `py-vX.Y.Z` first for the Python core
- publish `npm-vX.Y.Z` second for the npm wrapper

Why:
- published wrapper mode shells into `uvx --from agent-learner agent-learner ...`
- matching versions make support/debugging simpler while the wrapper is still thin

If versions intentionally diverge later, document the compatibility matrix here.

See `docs/release-process.md` for tag conventions, changelog expectations, and the recommended GitHub/PyPI/npm release order.

## Prerelease rehearsal

Use the prerelease lanes to rehearse distribution safely:

- `.github/workflows/pypi-testpypi.yml` via `py-rc-vX.Y.Z`
- `.github/workflows/npm-prerelease.yml` via `npm-rc-vX.Y.Z`

Recommended rehearsal order matches production order: TestPyPI first, npm `next` second.

See `docs/prerelease-checklist.md` for the exact TestPyPI -> npm next rehearsal sequence before final release tags.
