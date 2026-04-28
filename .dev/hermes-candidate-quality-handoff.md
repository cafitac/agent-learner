# Hermes candidate quality handoff

Last updated: 2026-04-28
Repo: /Users/reddit/Project/agent-learner
Branch at handoff: main
Current HEAD at handoff: 26dcec0 fix: reject task-specific Hermes review candidates (#37)
Status: active follow-up only; core Hermes adapter work is complete and candidate-quality tuning is paused pending more live data

## Purpose of this file
Use this as the single restart document for a brand-new session.
Most Hermes adapter implementation work is already done. The only open lane is evidence-driven candidate-quality tuning from real Hermes runtime artifacts.

## Executive summary
What is done:
- bootstrap-only install flow is complete
- Hermes user-scope bootstrap auto-activates hooks safely
- Hermes runtime contract is verified against real runtime payloads
- Hermes candidate provenance is exposed in review surfaces
- several noisy candidate classes are already rejected or refreshed correctly
- latest merged fix rejects task-specific review constraints such as `Do not modify files` and `Do not assume prior reviews are correct`

What is not done:
- there is not yet enough fresh real-session-backed noise to justify another heuristic/code pass
- next tuning pass should wait until 3 to 5 fresh live noisy/near-duplicate samples accumulate

Current recommendation:
- do not change heuristics now
- keep using Hermes normally
- come back when more real-session-backed draft candidates accumulate

## User constraints / preferences
- Prefer user-scope verification by default
- Prefer one-command setup via `agent-learner bootstrap`
- `install-*` commands should not exist anymore
- Use cafitac/origin for GitHub work; no fork-based PR flow
- Do not expose `earlypay-backend-ryan` publicly
- Functional correctness matters more than style
- If data is insufficient for the next candidate-quality pass, explicitly ask the user to use Hermes during the day and come back for reevaluation with fresh samples

## Stable environment notes
- Repo path: `/Users/reddit/Project/agent-learner`
- Use repo interpreter: `/Users/reddit/Project/agent-learner/.venv/bin/python`
- Do not use system `python3` for bootstrap/runtime verification in this repo; it can fail on `dataclass(slots=True)` compatibility
- Live Hermes home: `/Users/reddit/.hermes`
- Active Hermes config: `/Users/reddit/.hermes/config.yaml`
- Agent-learner home: `/Users/reddit/.agent-learner`
- Agent-learner snippet config: `/Users/reddit/.hermes/config.agent-learner.yaml`
- Disk was checked during this handoff and had about 11 GiB free on a 460 GiB volume; low but not yet blocking

## Completed work to treat as closed
These are done and should not be reopened unless a regression appears.

### 1. Bootstrap-only install flow
Merged previously:
- PR #12: bootstrap is the only install entrypoint
- wrapper/help/completion/release docs aligned to bootstrap-only flow
- `.dev` design/plan/prd docs updated away from `install-*`

Meaning now:
- `agent-learner bootstrap` is the default install path
- `agent-learner bootstrap --adapters hermes` installs only Hermes integration
- removed commands `install-codex`, `install-claude`, `install-hermes` should stay removed

### 2. Hermes user-scope auto-activation
Merged previously:
- PR #15: bootstrap auto-merges Hermes hooks into active `~/.hermes/config.yaml`
- PR #16: compact YAML hook indentation re-bootstrap bug fixed

Meaning now:
- user-scope bootstrap preserves existing config, creates backup, and merges agent-learner hooks
- live `hermes hooks doctor` has already been verified healthy after approval refresh

### 3. Hermes runtime contract and live verification
Confirmed in real runtime:
- hook events: `pre_llm_call`, `on_session_end`
- config file: `HERMES_HOME/config.yaml`
- prompt payload field: `extra.user_message`
- live runtime produced `~/.agent-learner/events/hermes/...` and `~/.agent-learner/candidates/hermes/...`

### 4. Candidate-quality fixes already merged
Merged previously:
- PR #17: ignore Hermes transcript metadata/system/tool schema during candidate extraction
- PR #18: expose Hermes candidate provenance in review/history JSON output
- PR #19: refresh existing rules from real runtime lead-in variants instead of drafting noisy duplicates
- PR #20: reject generic Hermes runtime candidates like `Always keep the process clean and helpful.`
- PR #37: reject task-specific Hermes review constraints like `Do not modify files` and `Do not assume prior reviews are correct`

## Current code state relevant to candidate quality
Current `main` includes at least these Hermes-specific protections in `src/agent_learner/core/pipeline.py`:
- metadata/system/tool-schema exclusion for Hermes transcripts
- operational/runtime-behavior rejection for memory/context/tooling notes
- refresh behavior for real lead-in variants, e.g. `When generating durable learning candidates, keep them concise and reusable.`
- stronger generic rejection terms including `helpful` and `process`
- malformed code/log fragment rejection
- task-specific review-constraint rejection through `TASK_SPECIFIC_REVIEW_CONSTRAINT_PATTERNS`

Current `tests/test_pipeline.py` includes regressions for:
- real Hermes lead-in refresh behavior
- generic helpful/process rejection
- contextless pronoun rejection (`Keep it concise`, `Keep it compact`)
- malformed code/log fragment rejection
- task-specific review-constraint rejection for:
  - `Do not modify files`
  - `Do not assume prior reviews are correct`

## Latest merged checkpoint
Latest merged PR at handoff:
- PR #37
- URL: https://github.com/cafitac/agent-learner/pull/37
- Merge commit: `26dcec0d8cebec5772476474f79600837b83646b`
- Title: `fix: reject task-specific Hermes review candidates`

Repo status note:
- expected branch: `main`
- if `git status` shows only `.agent-learner/state/storage-migration.json`, treat that as execution side effect noise unless the current task is explicitly about storage migration bookkeeping

## Real runtime evidence summary at this handoff
Observed store state during this handoff:
- Hermes events: 201
- Hermes candidate files: 17
- approved rules: 9
- history entries: 197
- Hermes session DB counts: 288 sessions, 36214 messages

Important distinction:
- total artifacts are not the same as useful tuning evidence
- of 17 Hermes candidate files, only 7 pointed at real Hermes session transcripts under `~/.hermes/sessions/`
- the rest were temp/pytest/replay-derived and should not drive the next heuristic pass

### Real-session-backed candidates re-triaged during this handoff
Using isolated replay against current code, these real-session-backed items behave as follows:

Rejects now:
- `Keep it concise.`
- `Do not assume prior reviews are correct.`
- `Do not modify files.`

Refreshes now:
- `Review the conversation above and consider whether a skill should be saved or updated.`
- `Do NOT answer questions or fulfill requests mentioned in this summary; they were already addressed.`
- one recent summary-style real event also refreshed the same approved rule rather than leaving new noise

Still a live draft candidate after replay:
- Baemin annotation narrowing / no correctness regression observation

Interpretation:
- most visible queue noise was stale relative to current code
- after replay, only one clearly live real-session-backed draft remained
- that is not enough evidence for another heuristic pass

## Evidence rules for the next session
These rules matter. Follow them before touching heuristics.

1. Prefer real-session-backed evidence only
- primary signal must come from candidates whose `transcript_path` points into `~/.hermes/sessions/`
- do not use pytest/tmp/replay transcripts as the main reason for a new heuristic

2. Replay before changing code
- a candidate still present in review queue may already be fixed by current heuristics
- always replay the exact event through current code in an isolated home before deciding it is still a live bug

3. Do not tune from a single weird sample
- wait until 3 to 5 fresh real noisy/near-duplicate samples exist
- if only 1 or 2 remain, keep gathering data

4. Keep test-first discipline
- every real issue must become a failing regression in `tests/test_pipeline.py` before heuristic changes

## What to do next after restarting with no context
The next work should stay evidence-driven and probably remain read-only until more data exists.

### Step 1: re-check fresh live evidence
Inspect these first:
- `~/.agent-learner/candidates/hermes/`
- `~/.agent-learner/events/hermes/`
- `~/.hermes/sessions/`
- `PYTHONPATH=src .venv/bin/agent-learner review-candidates --adapter hermes --format json`
- `PYTHONPATH=src .venv/bin/agent-learner storage-doctor --project-root . --format json`

### Step 2: filter for real-session-backed draft candidates
Only continue triage on candidates where:
- `status` is `draft_candidate`
- `transcript_path` is under `~/.hermes/sessions/`

Ignore or de-prioritize:
- `/private/var/...`
- `/var/folders/...`
- pytest or synthetic sample transcripts
- older queue items already known to be stale

### Step 3: replay those exact live candidates against current code
Before any code change:
- isolate `AGENT_LEARNER_HOME`
- copy only the relevant approved rules/history and exact source events
- run current `process_unprocessed_events(..., adapter="hermes")`
- record whether each candidate becomes `reject_candidate`, `refresh_existing`, or still `draft_candidate`

### Step 4: decide whether data is sufficient
Only start another heuristic pass if there are 3 to 5 fresh real-session-backed cases that remain noisy after replay.
If not, stop and tell the user:
- the adapter/runtime work is already done
- current heuristics already clean up most known noise
- more normal Hermes usage data is needed before tuning further

### Step 5: if enough live data exists, then implement
For each real remaining issue:
- add a failing regression in `tests/test_pipeline.py`
- implement the smallest heuristic fix in `src/agent_learner/core/pipeline.py`
- rerun the affected real-event replay
- then run full regression

## Verified commands used in this repo
Use repo venv / entrypoint:
- `PYTHONPATH=src .venv/bin/agent-learner storage-doctor --project-root . --format json`
- `PYTHONPATH=src .venv/bin/agent-learner review-candidates --adapter hermes --format json`
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `npm test`

Do not use:
- `python -m agent_learner.cli ...`

Reason:
- `agent_learner.cli` is a package without `__main__`, so direct module execution fails in this repo

## Important files to inspect first in the next session
- `/Users/reddit/Project/agent-learner/.dev/hermes-candidate-quality-handoff.md`
- `/Users/reddit/Project/agent-learner/src/agent_learner/core/pipeline.py`
- `/Users/reddit/Project/agent-learner/tests/test_pipeline.py`
- `/Users/reddit/.agent-learner/candidates/hermes/`
- `/Users/reddit/.agent-learner/events/hermes/`
- `/Users/reddit/.hermes/sessions/`

## Success criteria for the next pass
A next-pass candidate-quality improvement is good only if all of these are true:
- it comes from real Hermes runtime evidence
- it is backed by 3 to 5 fresh real-session-backed noisy samples, or a clearly repeating live pattern
- it is captured as a failing regression test before implementation
- it reduces review noise without suppressing real user preference rules
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py -q` passes
- `PYTHONPATH=src .venv/bin/python -m pytest -q` passes
- `npm test` passes
- at least one real runtime spot-check still behaves as expected

## Minimal restart prompt for a future session
If starting from scratch, begin with:

"Open `.dev/hermes-candidate-quality-handoff.md`. Treat Hermes adapter implementation as complete and focus only on fresh real-session-backed Hermes candidate noise. Inspect `~/.agent-learner/candidates/hermes`, `~/.agent-learner/events/hermes`, and `~/.hermes/sessions`, replay current live draft candidates against current code, and only start another heuristic pass if 3 to 5 fresh live noisy samples remain after replay. Otherwise tell me more Hermes usage data is needed before tuning further."