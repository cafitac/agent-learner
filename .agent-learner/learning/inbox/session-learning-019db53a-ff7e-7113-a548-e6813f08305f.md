# Session Learning Candidate

- captured_at: 2026-04-22 22:53:26
- session_id: 019db53a-ff7e-7113-a548-e6813f08305f
- branch: main

## Changed Files
- HANGELOG.md
- README.md
- docs/architecture.md
- docs/install.md
- docs/storage-independence-and-provenance.md
- frontend/src/App.tsx
- frontend/src/components.tsx
- frontend/src/types.ts
- plugins/codex/README.md
- src/agent_learner/cli/main.py
- src/agent_learner/core/brain.py
- src/agent_learner/core/dashboard.py
- src/agent_learner/core/fastapi_app.py
- src/agent_learner/core/indexing.py
- src/agent_learner/core/lifecycle.py
- src/agent_learner/core/models.py
- src/agent_learner/core/retrieval.py
- src/agent_learner/core/storage.py
- src/agent_learner/core/webapp.py
- src/agent_learner/frontend_dist/assets/index-k_SVvm1K.js
- src/agent_learner/frontend_dist/index.html
- tests/test_cli_bootstrap.py
- tests/test_installers.py
- tests/test_retrieval.py
- .codex/
- docs/scope-learning-system.md
- src/agent_learner/core/global_learning.py
- src/agent_learner/frontend_dist/assets/index-UNy-H_-D.js

## Diff Summary

```
CHANGELOG.md                                       |  13 +
 README.md                                          |  15 +-
 docs/architecture.md                               |   2 +
 docs/install.md                                    |   6 +-
 docs/storage-independence-and-provenance.md        |  46 +--
 frontend/src/App.tsx                               |  98 ++++--
 frontend/src/components.tsx                        | 343 ++++++++++++++-------
 frontend/src/types.ts                              |  48 ++-
 plugins/codex/README.md                            |   2 +-
 src/agent_learner/cli/main.py                      |   2 +-
 src/agent_learner/core/brain.py                    |  84 -----
 src/agent_learner/core/dashboard.py                |  57 +++-
 src/agent_learner/core/fastapi_app.py              |  11 +-
 src/agent_learner/core/indexing.py                 |   6 +-
 src/agent_learner/core/lifecycle.py                |   9 +-
 src/agent_learner/core/models.py                   |   4 +-
 src/agent_learner/core/retrieval.py                |   2 +-
 src/agent_learner/core/storage.py                  |   8 +-
 src/agent_learner/core/webapp.py                   |   8 +-
 .../frontend_dist/assets/index-k_SVvm1K.js         |  40 ---
 src/agent_learner/frontend_dist/index.html         |   2 +-
 tests/test_cli_bootstrap.py                        |  59 +++-
 tests/test_installers.py                           |   2 +
 tests/test_retrieval.py                            |  51 ++-
 24 files changed, 589 insertions(+), 329 deletions(-)
```

## Recent Commits

```
6b69aa7 Make the wrapper behave like the obvious command surface
06e56ae Fix the published dashboard blank-screen regression
6d03b3b Optimize learned-rule injection before the next prompt
35d8b14 Make one-line install and doctor UX match reality
30f2b2a Cut the first dashboard-native stable release
```

## Review Prompts
- 어떤 결정이 다음 세션에도 반복해서 필요할까?
- 어떤 규칙이 AGENTS.md / rules / learning references 로 승격될 가치가 있을까?
- 어떤 내용은 단순 로그이고, 어떤 내용은 durable rule 인가?

## Suggested Next Step
- Run `$session-wrap` if the session needs a durable handoff.
- Run `$feedback-learning` if a repeatable rule emerged.
