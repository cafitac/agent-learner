# Hermes Adapter Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add an experimental Hermes adapter to `agent-learner` that supports project-scoped install, normalized `session_end` event capture, manual processing, and compact prompt-time retrieval without regressing existing Codex/Claude flows.

**Architecture:** Keep `agent-learner` core as the canonical learning plane and add Hermes as a thin adapter. The implementation should first extend CLI and installer surfaces, then add Hermes-specific helper scripts and retrieval formatting, and only after that wire Hermes runtime hook integration. Preserve project-local `.agent-learner/` as the system of record and avoid mutating unrelated Hermes memory/skills files.

**Tech Stack:** Python 3, argparse CLI in `src/agent_learner/cli/main.py`, adapter modules in `src/agent_learner/adapters/`, pytest test suite under `tests/`.

---

## Pre-read

Read these files before starting:
- `.dev/prd/hermes-adapter.md`
- `.dev/design/hermes-adapter-implementation.md`
- `.dev/reviews/hermes-adapter-review-notes.md`
- `src/agent_learner/cli/main.py`
- `src/agent_learner/adapters/codex.py`
- `src/agent_learner/adapters/claude.py`
- `tests/test_installers.py`
- `tests/test_cli_bootstrap.py`
- `tests/test_retrieval_adapter_filter.py`

Implementation constraints:
- Hermes adapter is experimental/opt-in.
- MVP default recommendation is project scope.
- MVP event is `session_end` only.
- MVP retrieval command is `render-hermes-context`.
- Do not mutate Hermes memory/skills/session content.
- Do not regress Codex/Claude installers or smoke paths.

---

## Task 1: Add failing installer tests for Hermes adapter

**Objective:** Define the expected Hermes installer behavior in tests before implementing the adapter.

**Files:**
- Modify: `tests/test_installers.py`
- Modify: `tests/test_cli_bootstrap.py`

**Step 1: Write failing test for project-scope installer assets**

Add a test in `tests/test_installers.py` that expects:
- `install_hermes_adapter(tmp_path)` to create:
  - `tmp_path / ".agent-learner" / "events" / "hermes"`
  - Hermes adapter helper script path(s)
  - Hermes adapter config/hook path(s) under project-local Hermes area
- installer returns a non-empty written-path list
- installer does not create unrelated Codex/Claude roots

Expected assertions should also check that the generated helper script contains `capture-event --adapter hermes --event-name session_end` and `process-events --adapter hermes --limit 1`.

**Step 2: Run the installer test to verify failure**

Run:
```bash
pytest tests/test_installers.py -k hermes -v
```
Expected: FAIL — missing import/function/module for Hermes adapter.

**Step 3: Write failing CLI/bootstrap tests**

Add tests in `tests/test_cli_bootstrap.py` for:
- removed-command guidance for `agent-learner install-hermes`
- `agent-learner bootstrap --target <tmp> --adapters hermes --hermes-scope project`
- optional explicit opt-in help-path behavior if you expose Hermes in bootstrap help without changing defaults

Each test should assert Hermes assets exist and Codex/Claude are not created unless explicitly requested.

**Step 4: Run CLI/bootstrap tests to verify failure**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k hermes -v
```
Expected: FAIL — unknown command or unsupported adapter.

**Step 5: Commit**

```bash
git add tests/test_installers.py tests/test_cli_bootstrap.py
git commit -m "test: add failing Hermes adapter installer and bootstrap tests"
```

---

## Task 2: Implement Hermes adapter module and exports

**Objective:** Add the Hermes adapter module with a project-scoped installer and export it through the adapter package.

**Files:**
- Create: `src/agent_learner/adapters/hermes.py`
- Modify: `src/agent_learner/adapters/__init__.py`
- Test: `tests/test_installers.py`

**Step 1: Write minimal adapter module skeleton**

Create `src/agent_learner/adapters/hermes.py` with:
- `install_hermes_adapter_with_scope(target_root: Path, *, scope: str = "project") -> list[Path]`
- `install_hermes_adapter(target_root: Path) -> list[Path]`
- helper-script string constants similar in shape to Codex/Claude adapters
- use `common.py` helpers where possible (`ensure_dir`, `merge_json_file`, `write_text`, `append_lines_if_missing`, or `upsert_hook` if applicable)

Minimal behavior for MVP:
- support `scope in {"project", "user"}` at the function level
- for `project` scope, create `.agent-learner/events/hermes/`
- write project-local Hermes adapter helper files
- keep installer idempotent
- do not touch unrelated files

**Step 2: Export installer from adapter package**

Update `src/agent_learner/adapters/__init__.py` to export `install_hermes_adapter` (and scope variant if existing pattern uses it internally).

**Step 3: Run targeted tests**

Run:
```bash
pytest tests/test_installers.py -k hermes -v
```
Expected: PASS for new Hermes installer tests, or narrow failures showing missing CLI wiring only.

**Step 4: Run existing installer regression tests**

Run:
```bash
pytest tests/test_installers.py -v
```
Expected: PASS — Codex/Claude installer tests remain green.

**Step 5: Commit**

```bash
git add src/agent_learner/adapters/hermes.py src/agent_learner/adapters/__init__.py tests/test_installers.py
git commit -m "feat: add Hermes adapter installer skeleton"
```

---

## Task 3: Extend CLI to recognize Hermes adapter

**Objective:** Make CLI surfaces understand Hermes as an experimental adapter.

**Files:**
- Modify: `src/agent_learner/cli/main.py`
- Test: `tests/test_cli_bootstrap.py`

**Step 1: Keep bootstrap-only CLI path**

Update CLI parser/setup so Hermes is reachable through bootstrap flags rather than a dedicated install subcommand:
```text
bootstrap --adapters hermes --target --hermes-scope
```

Follow the bootstrap adapter pattern and keep Hermes on the same install surface as the other adapters.

**Step 2: Extend adapter choices**

Update these command parsers to include `hermes` in choices where applicable:
- `capture-event`
- `process-events`
- `review-candidates`
- `history`
- `history-summary`

Also update bootstrap adapter help text to mention `hermes` as opt-in/experimental if you surface it there.

**Step 3: Add command execution branch**

Wire the Hermes bootstrap execution path in `cli_main()` to call the Hermes installer and print written paths, following the current bootstrap convention.

**Step 4: Run CLI tests**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "hermes or bootstrap" -v
```
Expected: PASS for Hermes tests and no regressions in bootstrap behavior.

**Step 5: Run broader CLI regression slice**

Run:
```bash
pytest tests/test_cli_bootstrap.py -v
```
Expected: PASS — existing Codex/Claude bootstrap and render-codex-context tests remain green.

**Step 6: Commit**

```bash
git add src/agent_learner/cli/main.py tests/test_cli_bootstrap.py
git commit -m "feat: add Hermes CLI install and adapter registration"
```

---

## Task 4: Add failing tests for Hermes event capture and processing

**Objective:** Lock down the normalized Hermes event path before implementation.

**Files:**
- Modify: `tests/test_cli_bootstrap.py`
- Test: `src/agent_learner/cli/main.py`

**Step 1: Add failing capture-event test**

Add a test analogous to `test_capture_event_command_writes_normalized_event` but with:
- `--adapter hermes`
- `--event-name session_end`
- stdin JSON payload containing a small summary-only event

Assert:
- output path exists
- payload JSON has `adapter == "hermes"`
- payload JSON has `event_name == "session_end"`
- summary payload survives serialization

**Step 2: Add failing process-events test**

Add a test analogous to the Claude event processing test but for Hermes:
- create `.agent-learner/events/hermes/session_end-s1.json`
- give it a minimal transcript path or summary-only payload depending on pipeline requirements
- call `process-events --adapter hermes --format json`

Assert:
- command exits 0
- output is JSON list
- result contains a promotion/review status, or at minimum does not reject Hermes as an unsupported adapter

**Step 3: Run tests to verify failure**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "capture_event or process_events" -v
```
Expected: FAIL — unsupported Hermes adapter or missing implementation details.

**Step 4: Commit**

```bash
git add tests/test_cli_bootstrap.py
git commit -m "test: add failing Hermes event capture and process tests"
```

---

## Task 5: Make manual Hermes event flow pass

**Objective:** Support Hermes in normalized event capture and shared processing without runtime hook integration yet.

**Files:**
- Modify: `src/agent_learner/cli/main.py`
- Modify: `src/agent_learner/core/events.py` (if needed)
- Modify: `src/agent_learner/core/pipeline.py` or related processing modules only if required
- Test: `tests/test_cli_bootstrap.py`

**Step 1: Implement minimal Hermes acceptance in capture-event path**

Update the CLI / event-writing path so `adapter=hermes` is accepted and written under:
```text
.agent-learner/events/hermes/
```

**Step 2: Ensure process-events can consume Hermes event files**

If processing currently assumes only Codex/Claude event names or paths, generalize the minimum necessary logic so Hermes `session_end` events work without introducing adapter-specific core branching unless truly needed.

**Step 3: Run targeted tests**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "hermes and (capture or process)" -v
```
Expected: PASS.

**Step 4: Run nearby regressions**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "capture_event or process_events or review_candidates" -v
```
Expected: PASS — existing Codex/Claude event flow remains green.

**Step 5: Commit**

```bash
git add src/agent_learner/cli/main.py src/agent_learner/core/events.py src/agent_learner/core/pipeline.py tests/test_cli_bootstrap.py
git commit -m "feat: support Hermes normalized event capture and processing"
```

---

## Task 6: Add failing retrieval-context tests for Hermes

**Objective:** Define the Hermes prompt-time retrieval contract before implementing it.

**Files:**
- Modify: `tests/test_cli_bootstrap.py`
- Modify: `tests/test_retrieval_adapter_filter.py`

**Step 1: Add failing adapter-filter test for Hermes**

Extend adapter-filter coverage so Hermes behaves like other adapters:
- universal rules included for Hermes
- Hermes-specific rules included when request adapter is Hermes
- non-Hermes rules excluded when adapter is Hermes

If the current harness field is used, add a test using `harness="hermes"`.

**Step 2: Add failing render command test**

Add a CLI test similar to `test_render_codex_context_command_outputs_hook_json` but for:
```text
render-hermes-context
```

Assert:
- command exits 0
- payload is structured and bounded
- output includes learned guidance from an approved rule
- output shape is appropriate for Hermes hook consumption

**Step 3: Run tests to verify failure**

Run:
```bash
pytest tests/test_retrieval_adapter_filter.py tests/test_cli_bootstrap.py -k hermes -v
```
Expected: FAIL — missing Hermes retrieval command/format path.

**Step 4: Commit**

```bash
git add tests/test_retrieval_adapter_filter.py tests/test_cli_bootstrap.py
git commit -m "test: add failing Hermes retrieval and render-context tests"
```

---

## Task 7: Implement Hermes retrieval formatter and command

**Objective:** Add compact prompt-time retrieval for Hermes using a dedicated MVP command.

**Files:**
- Create: `src/agent_learner/adapters/hermes_context.py`
- Modify: `src/agent_learner/cli/main.py`
- Modify: `src/agent_learner/core/retrieval.py` only if needed for adapter filtering consistency
- Test: `tests/test_retrieval_adapter_filter.py`
- Test: `tests/test_cli_bootstrap.py`

**Step 1: Create Hermes retrieval formatter**

Implement `src/agent_learner/adapters/hermes_context.py` with a small, bounded formatter that:
- retrieves approved rules relevant to the prompt
- tags retrieval request with `adapter="hermes"` if needed
- returns either:
  - structured JSON payload for Hermes, or
  - compact text block if that is easier to consume

Keep payload small and deterministic.

**Step 2: Add `render-hermes-context` CLI command**

Update `src/agent_learner/cli/main.py` to parse and execute:
```bash
agent-learner render-hermes-context --project-root . --prompt "..." --format hook-json
```

Mirror the structure of `render-codex-context` where reasonable, but do not force Codex-specific output fields if Hermes needs a different shape.

**Step 3: Run targeted retrieval tests**

Run:
```bash
pytest tests/test_retrieval_adapter_filter.py -v
pytest tests/test_cli_bootstrap.py -k "render_hermes or hermes" -v
```
Expected: PASS.

**Step 4: Run broader retrieval regressions**

Run:
```bash
pytest tests/test_retrieval.py tests/test_context.py tests/test_cli_bootstrap.py -k "render or retrieve" -v
```
Expected: PASS — existing retrieval behavior still works.

**Step 5: Commit**

```bash
git add src/agent_learner/adapters/hermes_context.py src/agent_learner/cli/main.py src/agent_learner/core/retrieval.py tests/test_retrieval_adapter_filter.py tests/test_cli_bootstrap.py
git commit -m "feat: add Hermes retrieval formatter and render command"
```

---

## Task 8: Add Hermes helper scripts and installer assertions

**Objective:** Ensure installed Hermes adapter assets include helper scripts for session-end capture and prompt-time retrieval.

**Files:**
- Modify: `src/agent_learner/adapters/hermes.py`
- Test: `tests/test_installers.py`

**Step 1: Implement helper script templates**

In `src/agent_learner/adapters/hermes.py`, add script templates similar to Codex/Claude helpers:
- auto session learning helper
- prompt context helper

The scripts should:
- read stdin JSON safely
- detect project root
- invoke shared CLI through `python -m agent_learner.cli.main` or installed binary fallback
- tolerate missing transcript path
- fail soft on timeout/errors

**Step 2: Update installer tests to inspect script content**

Assert that generated script bodies include:
- `capture-event`
- `process-events`
- `render-hermes-context`
- `--adapter hermes`

**Step 3: Run installer tests**

Run:
```bash
pytest tests/test_installers.py -k hermes -v
```
Expected: PASS.

**Step 4: Run full installer/bootstrap slice**

Run:
```bash
pytest tests/test_installers.py tests/test_cli_bootstrap.py -k "install or bootstrap" -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agent_learner/adapters/hermes.py tests/test_installers.py tests/test_cli_bootstrap.py
git commit -m "feat: add Hermes helper scripts and installer coverage"
```

---

## Task 9: Add smoke coverage for manual Hermes MVP flow

**Objective:** Provide an end-to-end testable path for the experimental Hermes adapter without requiring full Hermes runtime integration.

**Files:**
- Modify: `src/agent_learner/cli/main.py`
- Modify: `tests/test_cli_bootstrap.py`

**Step 1: Decide smoke surface**

Choose one of these minimal MVP smoke options:
- Option A: add `qa-hermes-smoke`
- Option B: keep smoke coverage inside existing CLI tests only and document the manual commands

Preferred MVP: Option A if it is small and mirrors current Codex/Claude smoke style.

**Step 2: Implement minimal smoke path**

If adding `qa-hermes-smoke`, make it:
- create temp/project-local learning state
- seed one approved Hermes-compatible rule
- run `render-hermes-context`
- emit one `session_end` capture/process cycle
- return JSON summary with `returncode == 0`

If not adding a CLI smoke command, add a test that runs the equivalent sequence through existing commands.

**Step 3: Run smoke coverage**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "hermes and smoke" -v
```
Expected: PASS.

**Step 4: Run regression slices**

Run:
```bash
pytest tests/test_cli_bootstrap.py -k "qa_codex_smoke or qa_claude_smoke or hermes" -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agent_learner/cli/main.py tests/test_cli_bootstrap.py
git commit -m "test: add Hermes MVP smoke coverage"
```

---

## Task 10: Final docs sync inside `.dev`

**Objective:** Keep draft documentation aligned with the actual implemented MVP before any promotion to `docs/`.

**Files:**
- Modify: `.dev/prd/hermes-adapter.md`
- Modify: `.dev/design/hermes-adapter-implementation.md`
- Modify: `.dev/reviews/hermes-adapter-review-notes.md`

**Step 1: Update draft docs with implementation reality**

Reflect final decisions such as:
- exact install paths
- actual Hermes helper script locations
- whether `qa-hermes-smoke` exists
- whether user scope remained signature-only or gained real coverage
- exact output format of `render-hermes-context`

**Step 2: Run a final focused test bundle**

Run:
```bash
pytest \
  tests/test_installers.py \
  tests/test_cli_bootstrap.py \
  tests/test_retrieval_adapter_filter.py -v
```
Expected: PASS.

**Step 3: Run a broader confidence suite**

Run:
```bash
pytest \
  tests/test_retrieval.py \
  tests/test_context.py \
  tests/test_pipeline.py \
  tests/test_pipeline_auto.py \
  tests/test_installers.py \
  tests/test_cli_bootstrap.py -v
```
Expected: PASS — no obvious regression in nearby core paths.

**Step 4: Commit**

```bash
git add .dev/prd/hermes-adapter.md .dev/design/hermes-adapter-implementation.md .dev/reviews/hermes-adapter-review-notes.md tests/test_installers.py tests/test_cli_bootstrap.py tests/test_retrieval_adapter_filter.py src/agent_learner/adapters/hermes.py src/agent_learner/adapters/hermes_context.py src/agent_learner/adapters/__init__.py src/agent_learner/cli/main.py
 git commit -m "feat: add experimental Hermes adapter MVP"
```

---

## Final verification checklist

- [ ] bootstrap --adapters hermes works in project scope
- [ ] Hermes installer is idempotent
- [ ] `.agent-learner/events/hermes/` is created correctly
- [ ] `capture-event --adapter hermes --event-name session_end` works
- [ ] `process-events --adapter hermes` works
- [ ] `render-hermes-context` returns bounded learned guidance
- [ ] Codex installer tests still pass
- [ ] Claude installer tests still pass
- [ ] Codex/Claude CLI smoke paths still pass
- [ ] `.dev` draft docs match implementation reality

## Execution handoff

Plan complete and saved. Ready to execute using subagent-driven-development — dispatch a fresh subagent per task with spec review first and code-quality review second.
