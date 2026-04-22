# Prerelease Checklist

Use this checklist before pushing prerelease tags.

## Goal

Rehearse the production distribution order safely:
1. TestPyPI for the Python core
2. npm `next` prerelease for the wrapper

## Commands to run locally first

```bash
npm test
npm pack --dry-run
uv run pytest -q
uv build
uv run agent-learner qa-codex-smoke
uv run agent-learner qa-claude-smoke
python scripts/release/bump_version.py X.Y.Z --dry-run
python scripts/release/prerelease_checklist.py X.Y.Z
python scripts/release/release_check.py --version X.Y.Z
```

## Tag order

### 1. Python prerelease first

```bash
git tag py-rc-vX.Y.Z
git push origin py-rc-vX.Y.Z
```

Wait for `.github/workflows/pypi-testpypi.yml` to pass.

Then verify from a clean shell:

```bash
uvx --from agent-learner --index https://test.pypi.org/simple agent-learner --help
```

### 2. npm prerelease second

```bash
git tag npm-rc-vX.Y.Z
git push origin npm-rc-vX.Y.Z
```

Wait for `.github/workflows/npm-prerelease.yml` to pass.

Then verify:

```bash
npx @cafitac/agent-learner@next version
npx @cafitac/agent-learner@next doctor
AGENT_LEARNER_UVX_INDEX_URL=https://test.pypi.org/simple \
AGENT_LEARNER_UVX_EXTRA_ARGS="--refresh --with fastapi<1 --with uvicorn<1 --index-strategy unsafe-best-match" \
  npx @cafitac/agent-learner@next core --help
```

## What to check

- TestPyPI publish completed successfully
- npm prerelease publish completed successfully
- wrapper published-mode can see the Python core through `uvx`
- Codex/Claude smoke paths still work in repo checkout
- `CHANGELOG.md` and release notes are ready for final release tags

## Final release after successful rehearsal

```bash
git tag vX.Y.Z
git push origin vX.Y.Z

git tag py-vX.Y.Z
git push origin py-vX.Y.Z

git tag npm-vX.Y.Z
git push origin npm-vX.Y.Z
```
