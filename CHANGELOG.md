# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and is intentionally lightweight while the project is still pre-1.0.

## [Unreleased]

## [0.3.0rc1] - 2026-04-22

### Added
- Local/global brain split with merged retrieval and global promotion/sync flows.
- Dashboard-first UX with `doctor`, `dashboard`, source checkout helpers, npm wrapper dashboard support, and optional Docker Compose.
- FastAPI + React dashboard path with project selector, local/global/merged views, candidates, history, and promotion actions.
- Candidate comparison workflow with `new_rule`, `refresh_existing`, `revise_existing`, `fork_rule`, and `reject_candidate` decisions.
- Promotion history, history summary, overview, dashboard summary, and publish smoke helpers.

### Changed
- Canonical learning storage moved from Codex-specific references into `.agent-learner/learning`.
- Dashboard defaults to port `8766` to avoid common local MCP/gateway port conflicts.
- README and quickstart now prioritize the dashboard-first OSS path.

### Notes
- Docker Compose remains an optional convenience path, not the default OSS install path.
- Post-publish `pipx`, `uvx`, and `npx` checks are documented in `docs/publish-smoke-checklist.md`.

## [0.2.0] - 2026-04-21

## [0.2.0rc2] - 2026-04-21

## [0.2.0rc1] - 2026-04-21

### Added
- npm wrapper scaffold for plugin-style delivery
- uv-based local/CI workflow
- Codex prompt-time retrieval and context injection
- normalized adapter event capture, transcript-aware extraction, and processed-event pipeline
- model-aware lifecycle utilities, smoke QA commands, and release/publish workflows

### Changed
- CI/release verification now covers source-tree smoke, built-wheel smoke, and npm wrapper packaging checks

## [0.1.0] - 2026-04-21

### Added
- initial public OSS scaffold for the Python core CLI
- Codex and Claude adapter bootstrap/install flows
- learning lifecycle directories and promotion primitives
