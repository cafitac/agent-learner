# Adapter Convergence Roadmap

`agent-learner` should become the common control plane for learned feedback across
Codex and Claude instead of leaving the stronger runtime-specific logic trapped
inside adapter-local scripts.

## What the real local setups show

After inspecting the current local environments:

### Claude today (`~/.claude`)
- richer learning portfolio manager via `cc-learner.py`
- context detection (`project`, `language`, `framework`, `current model`)
- lifecycle buckets beyond a single draft path (`pending`, `approved`, `needs_review`, `deprecated`, `auto-learned`)
- model-aware gating (`validated_on_models`, `excluded_models`, `model_dependency`)
- sweep/deprecation workflow
- transcript-oriented extraction handoff via `delegate-prompt`
- review-first philosophy before promotion

### Codex today (`~/.codex`)
- stronger native hook/event surfaces (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`)
- prompt-time context injection is the natural place to apply approved learning
- OMX adds routing/state/trace infrastructure, but not a shared learned-feedback control plane equivalent to Claude's `cc-learner`

## Principle

Do not try to make Codex behave like Claude by copying ad hoc scripts forever.
Instead:
1. extract the best Claude-side learning behaviors into the shared core
2. expose them through a normalized event + lifecycle contract
3. keep each adapter thin and runtime-specific only at the hook boundary

## What this repo now provides

- shared retrieval/ranking core
- shared normalized raw hook event location under `.agent-learner/events/`
- transcript-aware candidate extraction into `.agent-learner/candidates/`
- processed marker state under `.agent-learner/state/processed-events/`
- Codex prompt-time learning context injection
- adapter installers that stay thin while pointing back to shared CLI/core paths

## Must-have next capabilities

- separation between raw event capture, extracted candidates, and promoted durable rules

## Should-have soon

- transcript-aware extraction hooks that can delegate heavier synthesis work asynchronously
- evidence scoring before promotion
- adapter-specific ranking hints layered on top of the shared retrieval core
- processed marker metadata richer than a simple done file (processor version, timestamps)
- promotion review UX that uses model validation/exclusion signals directly

## Later

- Claude and Codex parity for long-running refinement workers
- cross-runtime promotion dashboards
- autoresearch-assisted validation loops
- promotion review UX that mirrors the stronger Claude portfolio-management workflow
