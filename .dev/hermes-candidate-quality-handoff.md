# agent-learner handoff: current source of truth

Last updated: 2026-04-29
Repo: /Users/reddit/Project/agent-learner
Current branch: main
Current HEAD: af60c5c docs: refresh Hermes handoff and archive completed design docs
Status: core work complete; only evidence-driven follow-up remains

## Read this first
This is the only restart document a brand-new session should trust first.

If a future session needs to know “what should I do now?”, the answer is:
- do not reopen finished implementation work
- do not change heuristics just to keep moving
- only re-enter candidate-quality work when fresh real Hermes runtime data has accumulated

## Executive summary
Done:
- Hermes adapter implementation is complete
- bootstrap-only install flow is complete
- user-scope Hermes bootstrap / hook merge path is complete
- Hermes runtime contract has been validated against real runtime artifacts
- multiple Hermes candidate-quality noise fixes have already landed
- storage-doctor legacy Codex remediation fix landed
- wrapper update / npm prefix fixes landed
- releases through 0.3.29 were published and smoke-tested from installed artifacts
- repo auth is now repo-localized to cafitac SSH + local git identity
- completed design docs were already moved into archive/reference status

Not active now:
- no immediate feature implementation is required
- no immediate release work is required
- no immediate candidate-quality heuristic change is justified

Only active follow-up:
- wait for more real Hermes usage data
- when enough fresh noisy live samples accumulate, replay them against current code and only then decide whether another heuristic pass is warranted

## What a future session should do
### Default answer
If the user asks “what should we do next?” and no fresh evidence has been collected yet:
- say the main agent-learner work is done
- say Hermes candidate-quality tuning is intentionally paused
- ask for more normal Hermes usage / more live data before touching code again

### Only resume code work when this threshold is met
Resume candidate-quality tuning only if BOTH are true:
1. there are 3 to 5 fresh real-session-backed noisy or near-duplicate candidates
2. those candidates still remain noisy after replay against current main

If either condition is false, stop.

## What counts as valid evidence
Use only candidates/events that are backed by real Hermes runtime artifacts.

Primary evidence sources:
- `~/.agent-learner/candidates/hermes/`
- `~/.agent-learner/events/hermes/`
- `~/.hermes/sessions/`

Accept for tuning only when:
- candidate status is effectively still a draft/noisy candidate
- transcript path points into `~/.hermes/sessions/`
- the pattern is fresh and repeating enough to justify a heuristic

Do NOT use as the main reason for code changes:
- `/private/var/...`
- `/var/folders/...`
- pytest fixtures
- temp replay transcripts
- old queue items that current code already rejects or refreshes

## Required workflow when enough new data exists
1. Re-check fresh evidence
   - inspect `~/.agent-learner/candidates/hermes/`
   - inspect `~/.agent-learner/events/hermes/`
   - inspect `~/.hermes/sessions/`
   - run `PYTHONPATH=src .venv/bin/agent-learner review-candidates --adapter hermes --format json`

2. Filter to real-session-backed draft candidates only
   - keep only candidates whose transcript path is under `~/.hermes/sessions/`

3. Replay before changing code
   - isolate `AGENT_LEARNER_HOME`
   - copy only relevant approved rules/history and exact source events
   - run current processing against those exact events
   - record whether each one becomes `reject_candidate`, `refresh_existing`, or still `draft_candidate`

4. Change code only if the replay still shows real noise
   - add a failing regression test first
   - make the smallest fix in `src/agent_learner/core/pipeline.py`
   - rerun targeted replay + tests
   - then rerun full regression

## Current recommendation
Right now the correct move is:
- keep using Hermes normally
- let real data accumulate
- come back later for another evidence pass

This is intentional. More heuristic changes now would likely overfit stale or low-volume samples.

## Known current state
Repository state:
- branch should be `main`
- origin should be `git@github.com-cafitac:cafitac/agent-learner.git`
- repo-local git identity should be `cafitac / cafitac99@gmail.com`

Worktree note:
- if `git status` only shows `.agent-learner/state/storage-migration.json`, treat it as generated execution noise unless the task is explicitly about storage-migration bookkeeping

Environment notes:
- use repo interpreter: `/Users/reddit/Project/agent-learner/.venv/bin/python`
- do not use system `python3` here; it can fail on `dataclass(slots=True)` compatibility
- live Hermes home: `/Users/reddit/.hermes`
- agent-learner home: `/Users/reddit/.agent-learner`

## Closed work that should stay closed unless a regression appears
- bootstrap-only install flow
- Hermes hook auto-merge / user-scope bootstrap
- Hermes runtime contract validation
- Hermes candidate provenance surfacing
- generic/noisy candidate rejection passes already merged
- malformed code/log fragment rejection
- injected skill-wrapper stripping
- task-specific review-constraint rejection
- storage-doctor legacy Codex remediation
- wrapper update npm selection fix
- wrapper update prefix pin fix
- release/publish/local reinstall/smoke verification through 0.3.29
- repo auth hardening for cafitac

## Important merged checkpoints
Hermes candidate-quality:
- PR #30: malformed Hermes code fragment rejection
- PR #31: ignore injected Hermes skill wrapper candidates
- PR #37: reject task-specific Hermes review candidates

Release / installer hardening:
- PR #33: use active node npm for wrapper updates
- PR #34: release 0.3.28
- PR #35: release 0.3.29 with wrapper-prefix pin fix and installed-artifact smoke verification

Docs:
- `af60c5c docs: refresh Hermes handoff and archive completed design docs`

## Verified commands for future use
Use repo-local entrypoints:
- `PYTHONPATH=src .venv/bin/agent-learner review-candidates --adapter hermes --format json`
- `PYTHONPATH=src .venv/bin/agent-learner storage-doctor --project-root . --format json`
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `npm test`

Do not use:
- `python -m agent_learner.cli ...`

Reason:
- `agent_learner.cli` is not the correct direct execution path in this repo

## .dev document map
Active source of truth:
- `.dev/hermes-candidate-quality-handoff.md`

Archive/reference only:
- `.dev/prd/hermes-adapter.md`
- `.dev/design/hermes-adapter-implementation.md`
- `.dev/plans/hermes-adapter-implementation-plan.md`
- `.dev/design/global-learning-storage-redesign.md`
- `.dev/plans/global-learning-storage-redesign-plan.md`

Meaning:
- the above archive/reference docs provide historical context and design rationale
- they are not the active task queue
- future sessions should not resume their checklists blindly

## Minimal restart prompt
If starting from scratch, begin with:

"Open `.dev/hermes-candidate-quality-handoff.md` first. Treat the main agent-learner implementation work as complete. Do not reopen finished Hermes adapter/install/release work. Inspect fresh real Hermes runtime artifacts only, replay any current live draft candidates against current main, and only start another heuristic pass if 3 to 5 fresh real-session-backed noisy samples still remain after replay. Otherwise report that more Hermes usage data is needed before tuning further."