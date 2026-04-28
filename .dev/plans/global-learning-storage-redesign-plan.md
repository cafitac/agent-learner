# Global-first learning storage implementation plan

> Status: deferred / archive reference. Do not resume this plan blindly; check `.dev/hermes-candidate-quality-handoff.md` first for the active next step.

## Archive note

This plan is not the current execution queue.

Current reality:
- the main agent-learner / Hermes integration work is already complete
- current follow-up work is paused pending more fresh real Hermes runtime data
- this storage redesign can be revisited later, but it is not the thing a new session should pick up by default

If a future session asks “what should I do now?”, the answer should come from:
- `.dev/hermes-candidate-quality-handoff.md`

Use this file only when there is an explicit decision to restart the global-storage redesign.

Goal: move canonical agent-learner storage from per-project `.agent-learner/` roots to a single global `~/.agent-learner/` store, while preserving repo-specific retrieval behavior through repo identity metadata and provenance.

Architecture: write events/candidates/history/rules into one global canonical store, attach `repo_id` + provenance to every artifact, and make retrieval filter on scope/identity instead of filesystem location. Preserve compatibility reads from project-local stores during migration, then retire them once import tooling and regressions are complete.

Tech stack: Python CLI, file-based JSON/Markdown stores, git metadata detection, pytest.

---

## Task 0: Lock the design into repo docs

Objective: ensure implementation starts from an explicit document-first contract.

Files:
- Create: `.dev/design/global-learning-storage-redesign.md`
- Create: `.dev/plans/global-learning-storage-redesign-plan.md`

Step 1: Review current storage docs and helpers
- Read:
  - `src/agent_learner/core/storage.py`
  - `src/agent_learner/adapters/hermes.py`
  - `docs/architecture.md`
  - `README.md`

Step 2: Save the redesign/design-plan docs
- This task is complete when the two new `.dev` docs exist and describe:
  - global canonical storage
  - repo identity
  - provenance fields
  - compatibility migration

Step 3: Verification
- Run: `test -f .dev/design/global-learning-storage-redesign.md && test -f .dev/plans/global-learning-storage-redesign-plan.md`
- Expected: exit code 0

---

## Task 1: Add repo identity helpers

Objective: create a single code path that turns cwd into a stable repo identity + provenance bundle.

Files:
- Create: `src/agent_learner/core/repo_identity.py`
- Modify: `src/agent_learner/adapters/hermes.py`
- Modify: `src/agent_learner/adapters/codex.py`
- Modify: `src/agent_learner/core/models.py`
- Test: `tests/test_repo_identity.py`

Step 1: Write failing tests
Add tests for:
- repo with origin remote -> normalized `owner/repo`
- repo without origin -> fallback to repo root/path fingerprint
- worktree cwd -> same `repo_id` as parent repo but different `worktree_path`

Step 2: Run targeted tests to confirm failure
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_repo_identity.py -q`
- Expected: FAIL because helper/module does not exist yet

Step 3: Implement minimal helper
Required output shape:
- `repo_id`
- `repo_remote_url`
- `repo_root`
- `cwd`
- `worktree_path`

Step 4: Re-run tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_repo_identity.py -q`
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: add repo identity helpers for global learning storage"`

---

## Task 2: Add global canonical storage helpers without deleting local reads

Objective: separate canonical storage location from compatibility fallback logic.

Files:
- Modify: `src/agent_learner/core/storage.py`
- Test: `tests/test_storage.py`

Step 1: Write failing tests
Cover:
- canonical events path under `~/.agent-learner/events/<adapter>/`
- canonical candidates path under `~/.agent-learner/candidates/<adapter>/`
- canonical history path under `~/.agent-learner/history/`
- canonical learning path under `~/.agent-learner/learning/`
- compatibility scan still sees project-local legacy files

Step 2: Run targeted tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_storage.py -q`
- Expected: FAIL on missing helpers

Step 3: Implement helpers
Add explicit functions like:
- `canonical_events_dir(adapter)`
- `canonical_candidates_dir(adapter)`
- `canonical_history_path(name)`
- `canonical_learning_root()`
- `legacy_project_storage_roots(project_root)`

Do not remove old project-local helpers yet.

Step 4: Re-run tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_storage.py -q`
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: add global canonical storage helpers"`

---

## Task 3: Write Hermes events to the global store with provenance

Objective: stop fragmenting new Hermes events by project root.

Files:
- Modify: `src/agent_learner/adapters/hermes.py`
- Modify: `src/agent_learner/core/events.py`
- Modify: `src/agent_learner/core/models.py`
- Test: `tests/test_installers.py` if bootstrap fixtures need updates
- Test: `tests/test_pipeline.py`
- Test: add `tests/test_hermes_global_event_storage.py`

Step 1: Write failing tests
Cover:
- `on_session_end` event writes under `~/.agent-learner/events/hermes/`
- event payload includes repo identity + provenance
- compatibility path reading still works for old local event fixtures

Step 2: Run targeted tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_hermes_global_event_storage.py -q`
- Expected: FAIL

Step 3: Implement minimal write-path change
- keep transcript resolution unchanged
- replace project-local event write target with global canonical target
- make sure no project-local write is required for success

Step 4: Re-run tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_hermes_global_event_storage.py -q`
- Expected: PASS

Step 5: Regression spot-check
- Run existing Hermes smoke tests and related CLI tests

Step 6: Commit
- `git commit -m "feat: store Hermes events in the global learning home"`

---

## Task 4: Process candidates in the global store

Objective: ensure `process-events`, `review-candidates`, and `history` operate on a single canonical candidate/history location.

Files:
- Modify: `src/agent_learner/core/pipeline.py`
- Modify: `src/agent_learner/cli/main.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_cli_bootstrap.py`

Step 1: Write failing tests
Cover:
- new events in global store produce candidates in `~/.agent-learner/candidates/hermes/`
- `review-candidates --adapter hermes` reads global canonical candidates by default
- candidate JSON includes repo identity/provenance
- compatibility read path still finds legacy local candidates if present

Step 2: Run targeted tests
- Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py tests/test_cli_bootstrap.py -k 'review_candidates or global candidate' -q`
- Expected: FAIL

Step 3: Implement minimal behavior
- process events from global canonical event dir first
- write candidate artifacts to global canonical candidate dir
- preserve source event path and transcript path
- add repo metadata to candidate frontmatter or JSON where appropriate

Step 4: Re-run targeted tests
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: process learning candidates from the global store"`

---

## Task 5: Move approved/review/deprecated rule lifecycle to the global canonical store

Objective: make rules durable beyond worktree/project deletion while keeping retrieval relevant.

Files:
- Modify: `src/agent_learner/core/lifecycle.py`
- Modify: `src/agent_learner/core/dashboard.py`
- Modify: `src/agent_learner/core/models.py`
- Test: `tests/test_cli_bootstrap.py`
- Test: add lifecycle-focused tests if missing

Step 1: Write failing tests
Cover:
- approved rules are stored in `~/.agent-learner/learning/approved/`
- repo-scoped rules keep `repo_id`
- usage-summary reflects global canonical state
- legacy local approved rules remain readable during transition

Step 2: Run tests to confirm failure

Step 3: Implement rule lifecycle migration
- canonical write path becomes global
- local/global split becomes metadata-driven, not directory-driven
- preserve counters and provenance when rewriting existing rules

Step 4: Re-run tests
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: move rule lifecycle to global canonical storage"`

---

## Task 6: Update retrieval to filter by scope + repo identity

Objective: avoid cross-project leakage after centralizing storage.

Files:
- Modify: `src/agent_learner/core/retrieval.py`
- Modify: `src/agent_learner/adapters/codex_context.py`
- Modify: `src/agent_learner/cli/main.py`
- Test: `tests/test_pipeline.py`
- Test: add retrieval-focused regression tests

Step 1: Write failing tests
Cover:
- repo-scoped rule from repo A does not retrieve in repo B
- global rule retrieves in both repos
- worktree and repo root of same repo share the same repo-scoped rules
- use_count/last_used update on the canonical global record

Step 2: Run targeted tests to verify failure

Step 3: Implement filtering
- detect active repo identity once
- retrieve from global canonical rules
- filter by `learning_scope` and `repo_id` before ranking
- preserve existing ranking behavior as much as possible

Step 4: Re-run targeted tests
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: filter global learning retrieval by repo identity"`

---

## Task 7: Add explicit migration/import tooling

Objective: bring old project-local artifacts into the global canonical home safely.

Files:
- Modify: `src/agent_learner/cli/main.py`
- Create: `src/agent_learner/core/migration.py`
- Test: add `tests/test_migration.py`

Step 1: Write failing tests
Cover:
- migrate project-local events/candidates/history/rules into global storage
- duplicate import is idempotent
- provenance keeps original project root/source path

Step 2: Run targeted tests
- Expected: FAIL

Step 3: Implement command
Suggested command:
- `agent-learner migrate-local-storage --project-root <path>`

Optional later command:
- `agent-learner migrate-local-storage --all-registered-projects`

Step 4: Re-run tests
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: add migration tooling for local learning stores"`

---

## Task 8: Add storage audit and aggregate visibility commands

Objective: make the new model observable and easy to trust.

Files:
- Modify: `src/agent_learner/cli/main.py`
- Modify: `src/agent_learner/core/dashboard.py`
- Test: `tests/test_cli_bootstrap.py`

Step 1: Write failing tests
Cover:
- `usage-summary` defaulting to global canonical store
- project/repo filters
- `audit-storage-layout` showing global canonical counts + legacy local remnants

Step 2: Run targeted tests
- Expected: FAIL

Step 3: Implement surfaces
Suggested commands:
- `agent-learner usage-summary --repo-id ...`
- `agent-learner audit-storage-layout`

Step 4: Re-run tests
- Expected: PASS

Step 5: Commit
- `git commit -m "feat: add audit surfaces for global learning storage"`

---

## Task 9: Update docs and handoff material

Objective: align user-facing docs to the new global-first mental model.

Files:
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/install.md`
- Modify: `docs/adapter-convergence.md`
- Modify: `.dev/hermes-candidate-quality-handoff.md`
- Modify: `CHANGELOG.md`

Step 1: Update docs
Document:
- canonical storage now lives in `~/.agent-learner/`
- repo-specific applicability uses metadata/filters
- project-local `.agent-learner/` is legacy or cache-only if retained

Step 2: Verify doc searches
- Run targeted searches for stale “project-local is canonical” wording

Step 3: Commit
- `git commit -m "docs: describe global-first learning storage"`

---

## Task 10: Full regression and live smoke

Objective: prove the redesign preserves working Hermes behavior.

Files:
- No new source files required unless regressions demand fixes

Step 1: Run Python suite
- `PYTHONPATH=src .venv/bin/python -m pytest -q`

Step 2: Run npm suite
- `npm test`

Step 3: Run Hermes smoke
- `PYTHONPATH=src .venv/bin/python -m agent_learner.cli.main qa-hermes-smoke`

Step 4: Run one live global-home retrieval/event sanity check
- verify new event appears under `~/.agent-learner/events/hermes/`
- verify candidate/review/usage surfaces can see it

Step 5: Commit any final fixes and then open PR

---

## Guardrails

- Do not use worktree path as the logical repo key.
- Do not drop provenance when migrating from local roots.
- Do not switch retrieval to global canonical storage without hard repo filtering in place.
- Do not delete old project-local data automatically in the same change that introduces global canonical writes.
- Prefer additive migration first, destructive cleanup later.

## Recommended first implementation slice

If doing this incrementally across multiple PRs, the best first slice is:
1. repo identity helper
2. global canonical event writes for Hermes
3. compatibility read path
4. regression tests

That slice is small enough to verify, but meaningful enough to prove the redesign direction before rule lifecycle migration.
