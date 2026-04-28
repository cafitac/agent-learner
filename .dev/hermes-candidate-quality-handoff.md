# Hermes candidate quality handoff

Last updated: 2026-04-28
Repo: /Users/reddit/Project/agent-learner
Branch at handoff: main
Current HEAD at handoff: 392d5eb fix: reject generic Hermes runtime candidates (#20)

## Goal
Make Hermes adapter learning usable in real workflows by improving candidate quality using real Hermes runtime evidence, not only synthetic text fixtures.

Primary product intent:
- bootstrap must be the only install entrypoint
- Hermes user-scope bootstrap should auto-activate hooks safely
- Hermes runtime should actually produce usable learning artifacts
- candidate review queue should avoid low-signal/generic/runtime-behavior noise
- improvements should be driven by real runtime samples and then locked with tests

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
- Agent-learner snippet config: `/Users/reddit/.hermes/config.agent-learner.yaml`

## What is already done

### 1. Bootstrap-only install flow is complete
Merged previously:
- PR #12: bootstrap is the only install entrypoint
- Wrapper/help/completion/release docs aligned to bootstrap-only flow
- `.dev` design/plan/prd docs updated to bootstrap-only wording

Meaning now:
- `agent-learner bootstrap` is the default install path
- `agent-learner bootstrap --adapters hermes` installs only Hermes integration
- removed commands `install-codex`, `install-claude`, `install-hermes` should stay removed

### 2. Hermes user-scope auto-activation is complete
Merged previously:
- PR #15: bootstrap auto-merges Hermes hooks into active `~/.hermes/config.yaml`
- PR #16: compact YAML hook indentation re-bootstrap bug fixed

Meaning now:
- user-scope bootstrap preserves existing config, creates backup, and merges agent-learner hooks
- live `hermes hooks doctor` has already been verified healthy after approval refresh

### 3. Hermes runtime contract and live verification are complete
Confirmed in real runtime:
- hook events: `pre_llm_call`, `on_session_end`
- config file: `HERMES_HOME/config.yaml`
- prompt payload field: `extra.user_message`
- live runtime produced `.agent-learner/events/hermes/...` and `.agent-learner/candidates/hermes/...`

### 4. Candidate quality hardening already merged before this handoff
Merged previously:
- PR #17: ignore Hermes transcript metadata/system/tool schema during candidate extraction
- PR #18: expose Hermes candidate provenance in review/history JSON output
- PR #19: improve matching from real runtime samples so lead-in variants refresh existing rules instead of generating noisy duplicates
- PR #20: reject generic Hermes runtime candidates like “Always keep the process clean and helpful.”

## Current code state relevant to candidate quality
Current main already includes:
- `src/agent_learner/core/pipeline.py`
  - metadata/system/tool-schema exclusion for Hermes transcripts
  - operational/runtime-behavior rejection for phrases like memory/context injection notes
  - better semantic matching for real lead-in variants, e.g.:
    - existing rule: `Keep Hermes learning rules concise and reusable.`
    - runtime phrase: `When generating durable learning candidates, keep them concise and reusable.`
    - decision should be `refresh_existing`
  - stronger generic rejection terms including `helpful` and `process`
- `tests/test_pipeline.py`
  - regression tests for metadata-only transcript rejection
  - regression tests for operational note rejection
  - regression tests for real lead-in refresh behavior
  - regression test for rejecting real generic runtime phrase `Always keep the process clean and helpful.`

## Latest merged checkpoint
Latest merged PR at handoff:
- PR #20
- URL: https://github.com/cafitac/agent-learner/pull/20
- Merge commit: `392d5ebffc646eb59f18ad6f588d290509cf64ea`
- Title: `fix: reject generic Hermes runtime candidates`

Repo status at handoff should be:
- branch: `main`
- working tree: clean

## Real runtime samples used so far
These are the key real samples already used to drive behavior.

### Sample A: should refresh existing Hermes rule
Existing approved rule:
- `Keep Hermes learning rules concise and reusable.`

Observed runtime variants:
- `When generating durable learning candidates, keep them concise and reusable.`
- `Before writing a durable learning candidate, keep it concise and reusable.`

Desired behavior:
- do not create a noisy new candidate
- classify as `refresh_existing`

This is already implemented and tested.

### Sample B: should be rejected as generic
Observed runtime phrase:
- `Always keep the process clean and helpful.`

Desired behavior:
- reject as generic/low-signal
- do not promote to a durable rule

This is already implemented and tested.

### Sample C: overlap sample kept for future evaluation
Observed runtime phrase:
- `When shared behavior changes, update tests before finishing.`

This was collected as a useful real sample for future passes. It may help tune near-duplicate suppression or rule-family matching in the next round.

## Verified commands used in this project
Run tests with repo venv:
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `npm test`

Useful runtime validation pattern:
- use a temp project
- seed approved rules under `.agent-learner/learning/approved/`
- run Hermes with live user-scope hooks or synthesize an event via agent-learner lifecycle helpers
- inspect resulting `.agent-learner/events/hermes/*` and `.agent-learner/candidates/hermes/*`

## What to do next after restarting with no context
The next work should continue to be evidence-driven.

### Step 1: collect fresh real runtime evidence
If the user has used Hermes more since this handoff, inspect fresh artifacts first:
- Hermes sessions under `/Users/reddit/.hermes/sessions/`
- candidate queue under project `.agent-learner/candidates/hermes/`
- history/review output via CLI

Target:
- find 3 to 5 remaining low-signal or near-duplicate candidates from real usage
- prefer examples that actually reached review queue or were almost promoted

### Step 2: decide whether data is sufficient
If there are not enough fresh real samples, do not invent more heuristics.
Tell the user clearly:
- more real usage data would help
- ask them to use Hermes during the day and come back
- then evaluate the new candidate/review artifacts

This is important because the user explicitly approved that approach.

### Step 3: turn real samples into failing tests first
For each candidate-quality issue found:
- add or update a regression in `tests/test_pipeline.py`
- reproduce failure before changing heuristics
- prefer tests that reflect real runtime wording, not abstract paraphrases

### Step 4: likely next improvement areas
Most likely next targets:
1. near-duplicate suppress based on real review queue samples
2. stronger distinction between user preference rules vs assistant/process self-instructions
3. reason/explanation surface for why a candidate became:
   - `refresh_existing`
   - `new_rule`
   - `reject_candidate`
4. evidence quality scoring using source role/message structure
5. rule-family matching around test-related instructions, if real samples show noise there

### Step 5: if a change is made, verify in this order
1. targeted failing tests now pass
2. `PYTHONPATH=src .venv/bin/python -m pytest tests/test_pipeline.py -q`
3. `PYTHONPATH=src .venv/bin/python -m pytest -q`
4. `npm test`
5. at least one real runtime spot-check with temp project artifacts

### Step 6: GitHub workflow to continue
Use origin/cafitac only.
Typical sequence:
- create branch from `main`
- commit only relevant files
- push to `origin`
- open PR against `main`
- wait for checks
- merge with admin if review requirement blocks self-approval
- sync local `main` back to `origin/main`

## Important files to inspect first in the next session
- `/Users/reddit/Project/agent-learner/src/agent_learner/core/pipeline.py`
- `/Users/reddit/Project/agent-learner/tests/test_pipeline.py`
- `/Users/reddit/Project/agent-learner/tests/test_cli_bootstrap.py`
- `/Users/reddit/Project/agent-learner/.dev/prd/hermes-adapter.md`
- `/Users/reddit/Project/agent-learner/.dev/design/hermes-adapter-implementation.md`
- `/Users/reddit/Project/agent-learner/.dev/plans/hermes-adapter-implementation-plan.md`
- `/Users/reddit/.hermes/sessions/`
- any fresh project-local `.agent-learner/candidates/hermes/` artifacts from actual use

## Success criteria for the next pass
A next-pass quality improvement is good only if all of these are true:
- it comes from real Hermes runtime evidence
- it is captured as a failing regression test before implementation
- it reduces review noise without suppressing real user preference rules
- full pytest and npm test still pass
- at least one real runtime spot-check still behaves as expected

## Minimal restart prompt for a future session
If starting from scratch, the new session can begin with this:

"Open `.dev/hermes-candidate-quality-handoff.md`, inspect fresh Hermes runtime artifacts under `~/.hermes/sessions` and current review/candidate outputs, then continue the next real-sample-driven candidate quality pass. If there are not enough fresh real samples, tell me explicitly and ask me to use Hermes more before reevaluating."