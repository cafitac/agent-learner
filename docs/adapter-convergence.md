# Adapter Convergence Roadmap

`agent-learner` should become the common control plane for learned feedback across
Codex, Claude, and Hermes instead of leaving the stronger runtime-specific logic trapped
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

### Hermes today (`.hermes` / `~/.hermes`)
- thin experimental adapter path built around project-local learned rules
- prompt-time context injection via the real Hermes `pre_llm_call` shell hook
- session-end capture via the real Hermes `on_session_end` shell hook and normalized `session_end` events
- shared retrieval and event-processing core reused instead of adding a Hermes-specific learner
- current recommended rollout is explicit opt-in, with user-scope bootstrap now validated against live Hermes runtime and project scope still available for isolated opt-in verification
- installer writes `config.yaml` only when missing, auto-merges required hooks into an existing user-scope active config with backup, and still emits `config.agent-learner.yaml` as a re-sync snippet

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
- Hermes prompt-time learning context injection via `render-hermes-context`
- Hermes normalized `session_end` event capture and processing
- adapter installers that stay thin while pointing back to shared CLI/core paths

## Must-have next capabilities

- separation between raw event capture, extracted candidates, and promoted durable rules
- runtime-contract validation for Hermes hook payloads so the experimental adapter can harden without widening core branching

## Should-have soon

- transcript-aware extraction hooks that can delegate heavier synthesis work asynchronously
- evidence scoring before promotion
- adapter-specific ranking hints layered on top of the shared retrieval core
- processed marker metadata richer than a simple done file (processor version, timestamps)
- promotion review UX that uses model validation/exclusion signals directly
- a common `render-context --adapter <name>` surface once Hermes/Codex output shapes can converge cleanly

## Later

- Claude, Codex, and Hermes parity for long-running refinement workers
- cross-runtime promotion dashboards
- autoresearch-assisted validation loops
- promotion review UX that mirrors the stronger Claude portfolio-management workflow
