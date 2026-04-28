# Global-first learning storage redesign

Last updated: 2026-04-28
Repo: /Users/reddit/Project/agent-learner
Status: proposed

## Goal

Redesign agent-learner so Hermes/Codex/Claude learning artifacts are stored in a single global home under `~/.agent-learner`, while keeping retrieval scoped correctly to the active repo/project and preserving provenance about the originating worktree/session path.

This should make learning behave more like `~/.hermes`: one durable home, one place to audit history, and no silent loss of learning when a worktree or temporary project directory is deleted.

## Problem statement

Current behavior is split across two storage concepts:
- global reusable learning under `~/.agent-learner/global/`
- project-local events/candidates/history/learning under `<project>/.agent-learner/`

That split creates three product problems:

1. Worktree fragility
- Hermes hook events and generated candidates are written under the detected `project_root`.
- If the active cwd is a worktree or temporary project directory that later gets removed, local learning artifacts can disappear with it.

2. Visibility mismatch
- Hermes runtime data is globally visible under `~/.hermes/`.
- agent-learner data is fragmented across project roots, so usage/candidate/history checks from one repo can falsely look empty even after heavy real usage.

3. Storage semantics are overloaded
- today `global` means both “stored in the global home” and “applies across projects”
- today `project` means both “stored locally” and “applies to one project”
- these should be separated into:
  - storage location
  - applicability scope
  - provenance

## Observed current behavior

Confirmed from the current codebase:
- `agent_learner_home()` resolves to `~/.agent-learner`
- `global_learning_home()` resolves to `~/.agent-learner/global`
- Hermes event storage currently resolves to `<project_root>/.agent-learner/events/<adapter>/`
- canonical learning root currently resolves to `<project_root>/.agent-learner/learning/`
- promotions history currently resolves to `<project_root>/.agent-learner/history/promotions.jsonl`
- Hermes adapter determines `project_root` from cwd/git top-level, then emits events there

Observed runtime symptom:
- heavy Hermes usage exists in `~/.hermes/state.db` and `~/.hermes/sessions/`
- learning artifacts are present, but spread across multiple roots such as:
  - `/Users/reddit/Project/.agent-learner`
  - `/Users/reddit/Project/earlypay/earlypay-backend/.agent-learner`
  - `/Users/reddit/Project/agent-learner/.agent-learner`

## Product intent after redesign

### Storage
All canonical learning artifacts should live under `~/.agent-learner/`.

Proposed canonical layout:

```text
~/.agent-learner/
  events/
    codex/
    claude/
    hermes/
  candidates/
    codex/
    claude/
    hermes/
  history/
    promotions.jsonl
    retrievals.jsonl
  learning/
    approved/
    needs_review/
    deprecated/
    inbox/
    drafts/
  indexes/
    rules.json
    projects.json
    repos.json
```

### Scope semantics
Applicability scope should be metadata on each rule, not implied by file location.

Proposed scopes:
- `repo`: applies to one logical repository
- `project`: optional narrower scope than repo if needed later
- `global`: applies across repositories

Non-goal:
- `worktree` should not be a scope. Worktree is provenance, not applicability.

### Provenance semantics
Each event/candidate/rule should preserve where it came from.

Required provenance fields:
- `repo_id`: normalized logical repo identity
- `repo_root`: canonical repo root path
- `cwd`: actual cwd when captured
- `worktree_path`: path of the active worktree, if different from repo root
- `adapter`: codex / claude / hermes
- `session_id`
- `transcript_path`
- `captured_at`

## Identity model

### Why path alone is insufficient
Different worktrees for the same repo produce different paths:
- `/Users/reddit/Project/earlypay/earlypay-backend`
- `/Users/reddit/Project/earlypay/earlypay-backend/.worktrees/EP-647`
- `/Users/reddit/Project/earlypay/earlypay-backend/.worktrees/EP-717`

If path is the identity key, one logical repo gets fragmented into many learning shards.

### Recommended repo identity
Primary identity should be a normalized git remote identity when available.

Preferred order:
1. normalized `origin` remote (`owner/repo` form when possible)
2. fallback repo fingerprint from git top-level + local repo metadata
3. final fallback absolute repo root path

Proposed metadata fields:
- `repo_id`: stable logical identifier, e.g. `Earlypay/earlypay-backend`
- `repo_remote_url`: raw remote URL for debugging
- `repo_root`: canonical repository root path
- `path_fingerprint`: optional fallback if remote is unavailable

## Retrieval model after redesign

Retrieval should read from the global store but filter by identity and scope.

Selection pipeline:
1. detect active repo identity from cwd
2. read candidate rules from the global learning index
3. keep only rules where:
   - `scope == global`, or
   - `scope == repo` and `repo_id` matches active repo, or
   - future narrower scopes match
4. apply existing lexical/semantic ranking
5. touch usage counters in the global canonical record
6. append retrieval telemetry to `~/.agent-learner/history/retrievals.jsonl`

Important consequence:
- retrieval and usage accounting become globally visible
- applicability remains correctly filtered per repo

## Data model changes

### Event records
Add fields to all adapters’ normalized events:
- `repo_id`
- `repo_remote_url`
- `repo_root`
- `cwd`
- `worktree_path`

### LearningRule model
Add or normalize fields on approved/reviewed rules:
- `repo_id: str | None`
- `repo_root: str | None`
- `source_paths: list[str]`
- `adapters_seen: list[str]`
- `last_retrieved_adapter: str | None`
- keep existing counters (`use_count`, `refresh_count`, `promote_count`, `last_used`)

Interpretation:
- `learning_scope=global` means cross-repo reusable
- `learning_scope=repo` means repo-specific reusable
- provenance fields explain where the rule came from, without forcing storage to be local

## Migration strategy

### Phase 0: additive compatibility
- keep reading existing project-local artifacts
- introduce global canonical storage alongside them
- write new artifacts to global storage first
- optionally mirror/symlink/minimize local project files during transition only if needed for compatibility

### Phase 1: global canonical writes
- events/candidates/history/rules all write to `~/.agent-learner`
- project-local lookup becomes legacy fallback only
- usage-summary / review-candidates / history read global first

### Phase 2: import old project-local stores
- scan known roots from registry + explicit migration command
- ingest local events/candidates/history into global storage
- dedupe by event id / candidate slug / rule name + provenance
- preserve source paths in metadata

### Phase 3: retire project-local canonical storage
- stop creating `<project>/.agent-learner/events|candidates|history|learning` as canonical state
- if a local footprint is still useful, reduce it to a thin cache or pointer file only

## CLI / UX implications

New or changed surfaces should make the global-first model obvious.

Potential changes:
- `review-candidates` reads global canonical candidates by default
- `history` reads global canonical history by default
- `usage-summary` reads global canonical usage by default
- add filters:
  - `--repo-id`
  - `--project-root`
  - `--adapter`
  - `--scope`
- add `projects` or `repos` summary view from the global registry

Helpful new commands:
- `agent-learner migrate-local-storage --from <path>`
- `agent-learner audit-storage-layout`
- `agent-learner usage-summary --repo-id Earlypay/earlypay-backend`

## Compatibility constraints

We must not regress:
- existing approved rule retrieval quality
- Hermes bootstrap/runtime hooks
- current review/provenance JSON surfaces
- migration safety for dirty/temporary worktrees
- live user-scope Hermes flow

During migration, old local data should still be discoverable until explicitly imported or retired.

## Risks

1. Cross-project contamination
- if repo filtering is wrong, unrelated rules may leak into prompts
- mitigation: repo identity test matrix and hard filtering before ranking

2. Duplicate artifacts during migration
- same event or rule may exist in both local and global stores
- mitigation: deterministic dedupe keys and provenance-aware merges

3. Remote identity instability
- repos without remotes or with changed remotes need fallback identity behavior
- mitigation: support fallback repo_root/path fingerprint and keep both ids in metadata

4. Existing tooling assumptions
- docs/tests/commands may assume local `.agent-learner/`
- mitigation: migrate surfaces incrementally, keep compatibility reads temporarily

## Recommended implementation shape

Do this in vertical slices:

1. Identity + storage abstraction
- centralize “active repo identity” detection
- centralize “canonical global storage path” helpers

2. Global event write path
- all adapters write normalized events to global store with provenance
- project-local read remains fallback only

3. Global candidate processing
- process-events reads/writes global-first
- candidate files carry repo metadata

4. Global rule lifecycle
- approved/review/rejected lifecycle becomes global canonical
- retrieval filters by scope + repo_id

5. Migration and audit
- explicit migration command
- storage audit command
- docs + handoff update

## Recommendation

Proceed with a global-first redesign.

Reasoning:
- matches user expectation that learning should feel like `~/.hermes`
- avoids worktree deletion silently erasing learning state
- makes usage visibility and aggregate review practical
- keeps repo-specific relevance by moving repo identity into metadata instead of directory structure

The core principle should be:

> Store globally. Filter locally. Preserve provenance always.
