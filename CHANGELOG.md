# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and is intentionally lightweight while the project is still pre-1.0.

## [Unreleased]

## [0.3.25] - 2026-04-28

### Added
- `agent-learner storage-doctor` and alias `agent-learner audit-storage-layout` report the canonical `AGENT_LEARNER_HOME`, global artifact counts, legacy/local source state, migration marker details, warnings, and suggested next commands without mutating storage.

### Changed
- Documentation now describes the global-first storage model: `AGENT_LEARNER_HOME` (default `~/.agent-learner/`) is the canonical home, while project-local `.agent-learner/` assets are legacy migration sources rather than fallback stores.
- Removed the legacy `install-codex`, `install-claude`, and `install-hermes` CLI commands. `agent-learner bootstrap` is now the only install entrypoint, with `--adapters` and per-adapter scope flags handling selective setup.
- npm wrapper help, completion, and lane install forwarding now point to `bootstrap` instead of the removed top-level `install-*` aliases.
- Hermes user-scope bootstrap now auto-merges `pre_llm_call` and `on_session_end` hooks into an existing `~/.hermes/config.yaml`, writes a backup before updating the active config, and keeps `config.agent-learner.yaml` as a re-sync/reference snippet.

## [0.3.22] - 2026-04-25

### Fixed
- npm wrapper now passes `--scope` to `install-claude` and omits `--target` for user-scope installs (matching Codex behavior), preventing incorrect absolute paths in project-level `settings.json`.

## [0.3.21] - 2026-04-25

### Added
- `install-claude` now supports `--scope user` (default) and `--scope project`, mirroring the Codex install model. User-scope installs to `~/.claude/` with an absolute hook path; project-scope keeps the existing relative-path behavior.
- `bootstrap` gains a `--claude-scope` flag (default `user`) to control Claude scope alongside the existing `--codex-scope`.
- `install_claude_adapter_with_scope()` exported from `agent_learner.adapters` for programmatic use.

## [0.3.20] - 2026-04-25

### Fixed
- `subprocess.run` calls in installed Claude and Codex hook scripts now include `timeout=30` so a slow or hung `agent-learner` process cannot block session teardown indefinitely.
- `install-claude` now writes `"timeout": 30` into the `SessionEnd` hook entry in `settings.json`, matching the existing Codex hook timeout.

## [0.3.19] - 2026-04-23

### Fixed
- Auto-promotion now respects `review_required` for candidate decisions instead of silently auto-applying some review-queue items anyway.
- Operational/debugging notes such as hook-install troubleshooting guidance now stay in the candidate queue on first sighting and only auto-promote after repeated matching evidence, while normal code/test guidance keeps the existing automation-first path.

## [0.3.18] - 2026-04-23

### Fixed
- Codex and Claude installed hook scripts now call the npm wrapper through `agent-learner core ...` when the Python module is not directly importable, so user-scope installs can actually write repo-local events, candidates, and prompt context instead of silently failing through the wrapper help path.

## [0.3.17] - 2026-04-23

### Fixed
- npm published-mode installs now force a `uvx --refresh` for adapter install commands so a newly updated wrapper does not immediately hit a stale cached Python core without the new CLI flags.

## [0.3.16] - 2026-04-23

### Added
- `agent-learner install-codex` now supports a user-scope Codex install so one global hook setup can serve all local repos.
- Codex hook status messages now identify AgentLearner-triggered prompt injection and learning capture directly in the Codex hook UI.

### Changed
- `install-codex` now defaults to `user` scope, while repo-local Codex setup remains available through `--scope project`.
- User-scope Codex hooks now resolve the active repo from `cwd` and continue writing learning assets per project before falling back to global promotion.
- Wrapper parsing, doctor checks, and install routing now understand Codex user-scope installs as the default path.

### Fixed
- Codex learning hooks now target the detected project root instead of the raw working directory, reducing missed or misplaced repo-local learning state during global hook installs.

## [0.3.15] - 2026-04-23

### Fixed
- Project registry cleanup now removes old pytest/tmp entries from the user registry and prevents future test-only temp paths from appearing in the dashboard project selector.

## [0.3.14] - 2026-04-23

### Fixed
- Release verification now computes automation metrics deterministically during tests by isolating global learning state, preventing environment-specific publish failures while preserving the new dashboard KPI behavior.

## [0.3.13] - 2026-04-23

### Changed
- Learning automation now treats `needs_review` as a true exception queue, with stronger auto-resolution for clear refresh, revise, new-rule, and fork-rule cases instead of routing so many medium-confidence decisions to manual review.
- Draft placeholder generation was removed from the active Codex automation path, and legacy placeholder drafts are now cleaned up or migrated into `needs_review` automatically.
- The dashboard now focuses on approved guidance and exception handling rather than draft curation, with clearer `Needs Review` messaging and stronger explanations for unresolved items.

### Added
- Overview now reports automation KPIs such as automation rate, exception rate, recent-window automation trends, and categorized exception patterns so the learner can be monitored as an autonomous system.
- Rule and candidate detail views now surface unresolved-review reasons more explicitly so the rare manual intervention path is easier to judge.

### Fixed
- `needs_review` rules can now auto-return to `approved` when later evidence or model validation makes the resolution safe again, reducing stale exception buildup.
- Candidate records now stay in sync with automation outcomes by updating confidence and review flags when items auto-apply.

## [0.3.12] - 2026-04-23

### Changed
- Dashboard copy now frames the UI as a review-oriented control plane, with clearer Overview guidance for queue health, reusable guidance, candidate review, and audit.
- Overview now behaves more like an operator dashboard with health summaries, prioritized action queues, explicit sorting hints, and stronger quiet-workspace guidance when little data exists.
- Rules, candidates, and history views now explain their empty states and ordering logic more clearly so operators can predict what appears first and what to do next.

### Fixed
- Keyboard navigation and accessibility were improved across the dashboard with stronger focus visibility, semantic landmarks, skip navigation, live status announcements, and more explicit modal descriptions.
- Rule and candidate detail modals now surface primary details and provenance in more scannable structures instead of long ungrouped metadata lists.

## [0.3.11] - 2026-04-23

## [0.3.10] - 2026-04-23

## [0.3.9] - 2026-04-23

## [0.3.8] - 2026-04-23

## [0.3.7] - 2026-04-23

## [0.3.6] - 2026-04-22

## [0.3.5] - 2026-04-22

### Added
- A redesigned dashboard information architecture with `Curated`, `Drafts`, `Local`, and `Global` rule views so reusable guidance is separated from unfinished learning noise.
- A more modern React dashboard presentation with calmer hero/status cards, curated counters, richer candidate status pills, and card-based history timeline rendering.

### Changed
- Dashboard rule presentation now prefers higher-signal approved rules over empty drafts in merged views, hides low-signal draft placeholders from the curated view, and uses clearer empty-state copy throughout.
- Dashboard actions now follow the currently selected project when promoting global rules or reviewing candidates, preventing cross-project action mismatches from the UI.
- Internal naming is now consistently learning-first (`learning_scope`, `global_learning`, learning-focused docs/UI copy), and the old `brain_*` compatibility layer has been removed from the repo codepath.

### Fixed
- Frontmatter parsing now correctly decodes quoted scalar values such as `"approved"`, fixing malformed status display in dashboard summaries.
- Global rules are rendered with global scope in dashboard summaries even when older stored metadata would otherwise make them appear project-scoped.

## [0.3.4] - 2026-04-22

### Added
- Top-level wrapper aliases such as `agent-learner install-codex`, `agent-learner install-claude`, `agent-learner rebuild-index`, and `agent-learner bootstrap`.
- `agent-learner completion bash|zsh` for shell completion scripts and `agent-learner update` for npm-based self-update.

### Changed
- Wrapper UX now exposes the most common learning setup commands directly instead of forcing `core` or nested adapter syntax first.

## [0.3.3] - 2026-04-22

### Fixed
- Bundled React dashboard assets are now packaged with a valid `index.html`, fixing the blank white screen in published npm/PyPI dashboard launches.
- Doctor and FastAPI startup now validate the bundled frontend shell so broken dashboard assets fail loudly instead of serving an empty page.

## [0.3.2] - 2026-04-22

### Added
- Machine-readable and human-readable rule indexes under `.agent-learner/index/` so learned rules can be audited and pruned without opening every rule file.
- `agent-learner rebuild-index` to force a full reindex after manual rule edits.

### Changed
- Retrieval is now two-stage: index first, then only the top matching rule files are loaded into prompt context.
- Documentation now explains indexed retrieval and pruning as a first-class part of the learning workflow.

## [0.3.1] - 2026-04-22

### Changed
- Wrapper `doctor` now probes the published Python core in npm published mode, so release users get an accurate readiness verdict instead of a stale generic warning.
- README and install docs now lead with true one-line setup commands for both the PyPI and npm paths.

## [0.3.0] - 2026-04-22

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
- npm published mode now resolves the Python core with the `web` extra by default so dashboard commands include FastAPI dependencies.
- npm/TestPyPI prerelease rehearsals now support explicit `uvx` index and extra-argument controls, with clearer smoke guidance.
- Release smoke checks now run `doctor` through `uv run --extra web` so FastAPI dashboard readiness is actually exercised.

### Notes
- Docker Compose remains an optional convenience path, not the default OSS install path.
- Post-publish `pipx`, `uvx`, and `npx` checks are documented in `docs/publish-smoke-checklist.md`.

## [0.3.0rc3] - 2026-04-22

### Changed
- npm prerelease wrapper rehearsals now support additional `uvx` arguments so TestPyPI can be used for `agent-learner` while dependency constraints still resolve from PyPI.
- Release smoke checks now run `doctor` through `uv run --extra web` so FastAPI dashboard readiness is actually exercised.

## [0.3.0rc2] - 2026-04-22

### Changed
- npm published mode now resolves the Python core with the `web` extra by default so dashboard commands include FastAPI dependencies.
- npm prerelease smoke checks can point `uvx` at TestPyPI via `AGENT_LEARNER_UVX_INDEX_URL` before the Python core reaches production PyPI.

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
