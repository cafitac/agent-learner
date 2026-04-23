# Architecture

- `src/agent_learner/core/` holds lifecycle and retrieval logic.
- `src/agent_learner/adapters/` holds adapter-specific installation and rendering surfaces.
- `frontend/` holds the React + Vite dashboard UI that talks to the FastAPI dashboard surface.
- Consumer repos can install adapters independently, while the Codex adapter can also be installed once at user scope and still resolve per-project learning roots from `cwd`.
- `agent-learner` owns the canonical learning plane, not cross-runtime wiki management.
- Codex prompt application is retrieval-first: approved learned rules are ranked per-turn and injected through `UserPromptSubmit` as ephemeral additional context instead of expanding the persistent system prompt.
- Long-lived storage remains file-native under `.agent-learner/learning/`, while runtime context stays token-budgeted and temporary.
- Both adapters now emit normalized raw hook events under `.agent-learner/events/<adapter>/` so stronger Claude-side learning logic can be absorbed into shared core workflows instead of remaining adapter-local only.
- Normalized raw hook events feed a shared transcript-aware extraction pipeline that writes draft candidates and processed markers independently of adapter-specific storage.
- Shared context detection (project, language, framework, current model) now informs retrieval so approved rules can be gated similarly to Claude's `cc-learner` portfolio behavior.
- Retrieval and lifecycle now support model-aware validation/exclusion metadata and sweep-based status transitions.
- External wiki/KB systems such as `.omx/wiki/` or runtime-specific KBs may coexist, but they are outside the canonical learning lifecycle.

- Retrieval is now two-stage: a machine-readable rule index under `.agent-learner/index/rules.json` narrows candidates first, then only the top matching rule files are loaded for prompt injection.
- Human-readable index snapshots under `.agent-learner/index/index.md` make it easier to audit and prune stale knowledge without opening every rule file.
