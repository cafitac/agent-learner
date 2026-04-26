# Session Learning Candidate

- captured_at: 2026-04-23 12:38:04
- session_id: 019db855-b2cc-7141-9cb6-5d9b6e93583b
- branch: main

## Changed Files
- EADME.md
- docs/architecture.md
- docs/install.md
- lib/wrapper.cjs
- src/agent_learner/adapters/codex.py
- src/agent_learner/cli/main.py
- test/wrapper.test.cjs
- tests/test_cli_bootstrap.py
- tests/test_installers.py
- .agent-learner/
- .codex/

## Diff Summary

```
README.md                           |   4 +-
 docs/architecture.md                |   2 +-
 docs/install.md                     |  18 +++++++
 lib/wrapper.cjs                     |  95 +++++++++++++++++++++++----------
 src/agent_learner/adapters/codex.py | 102 ++++++++++++++++++++++++++++++------
 src/agent_learner/cli/main.py       |  23 ++++++--
 test/wrapper.test.cjs               |  42 ++++++++++++++-
 tests/test_cli_bootstrap.py         |  35 +++++++++++++
 tests/test_installers.py            |  24 ++++++++-
 9 files changed, 291 insertions(+), 54 deletions(-)
```

## Recent Commits

```
7be1e4b Keep published project lists free of test noise
6ef0ea1 Make learner release verification deterministic
16c03c0 Reduce manual exception handling in the published learner
1e3790c Make the published dashboard easier to review and trust
08736b6 Fix curated learning promotion semantics in the 0.3.11 release
```

## Review Prompts
- 어떤 결정이 다음 세션에도 반복해서 필요할까?
- 어떤 규칙이 AGENTS.md / rules / learning references 로 승격될 가치가 있을까?
- 어떤 내용은 단순 로그이고, 어떤 내용은 durable rule 인가?

## Suggested Next Step
- Run `$session-wrap` if the session needs a durable handoff.
- Run `$feedback-learning` if a repeatable rule emerged.
