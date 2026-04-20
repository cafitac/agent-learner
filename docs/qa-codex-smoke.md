# Codex Smoke QA

Use this guide to validate the Codex adapter the same way a consumer repo would use it.

## Fastest path

Run the built-in smoke command:

```bash
agent-learner qa-codex-smoke
```

What it does:
1. creates a temporary consumer-style repo
2. installs the Codex adapter
3. seeds one approved learning rule
4. simulates a `UserPromptSubmit` hook payload
5. prints the resulting hook JSON

Success signals:
- `returncode: 0`
- `payload.hookSpecificOutput.hookEventName == "UserPromptSubmit"`
- `payload.hookSpecificOutput.additionalContext` contains `<active_learning>`

## Manual consumer-style QA

```bash
TMP_REPO=$(mktemp -d)
agent-learner bootstrap --target "$TMP_REPO" --adapters codex
```

Seed an approved rule:

```bash
PYTHONPATH="$PWD/src" python3 - <<'PY' "$TMP_REPO"
from pathlib import Path
import sys
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule

root = Path(sys.argv[1]) / '.codex' / 'references' / 'learning'
lifecycle = LearningLifecycle(root)
lifecycle.promote(
    LearningRule(
        name='codex-hook-tests',
        rule='Update tests whenever the Codex prompt hook changes.',
        why='Prompt wiring should stay regression-tested.',
        scope='codex adapter',
        good_pattern='Change hook code and tests together.',
        avoid_pattern='Ship prompt hook changes without verification.',
        summary='Keep Codex prompt hook changes covered by tests.',
        triggers=['hook', 'tests', 'prompt'],
        task_types=['cli', 'prompt'],
        file_patterns=['src/**', 'tests/**'],
        priority='high',
        confidence='high',
    )
)
PY
```

Preview ranked rules:

```bash
agent-learner retrieve \
  --project-root "$TMP_REPO" \
  --prompt "fix the codex prompt hook and keep tests green"
```

Simulate the real hook script:

```bash
PATH="$PWD/.venv/bin:$PATH" \
python3 "$TMP_REPO/.codex/references/scripts/codex_prompt_context.py" <<JSON
{"hook_event_name":"UserPromptSubmit","prompt":"fix the codex prompt hook and keep tests green","cwd":"$TMP_REPO"}
JSON
```

## What not to see

The injected context should **not** include:
- draft rules
- raw session logs
- the full contents of every approved rule
- unrelated documentation-only rules for a code-fix prompt

## Claude extraction smoke

```bash
agent-learner qa-claude-smoke
```

This validates the shared event -> transcript extraction -> candidate pipeline for the Claude adapter.
