# PRD: Hermes Adapter for agent-learner

**작성일**: 2026-04-27 15:38 KST  
**상태**: 초안  
**범위**: `.dev` 전용 AI 초안 / 사람 승인 전  
**의존성**: agent-learner v2 core, existing Codex/Claude adapters

---

## 1. 목표

`agent-learner`를 하네스 독립적인 learning control plane으로 유지하면서, Hermes가 별도 legacy learner를 재구현하지 않고도 동일한 학습 파이프라인을 사용할 수 있게 한다.

핵심 결과:
- Hermes 세션에서 학습 이벤트를 정규화하여 `agent-learner`로 전달한다.
- Hermes 프롬프트 처리 시 approved learning을 retrieval-first 방식으로 주입한다.
- Hermes의 기존 memory / skills / session_search와 충돌하지 않는 역할 분리를 확립한다.
- 장기적으로 Hermit legacy learner 제거 및 공용 adapter 전략의 기반을 마련한다.

---

## 2. 배경

현재 `agent-learner`는 이미 Codex/Claude adapter를 통해 하네스별 hook 차이를 얇은 glue code로 흡수하고, 학습 자산의 생명주기와 retrieval을 shared core에서 처리하는 방향으로 발전하고 있다.

확인된 현황:
- `src/agent_learner/adapters/codex.py`
- `src/agent_learner/adapters/claude.py`
- `src/agent_learner/adapters/common.py`
- `src/agent_learner/adapters/codex_context.py`
- `src/agent_learner/core/events.py`
- `src/agent_learner/core/pipeline_auto.py`
- `src/agent_learner/core/retrieval.py`

반면 Hermes는 현재:
- user profile / durable memory 저장
- reusable skills 저장
- session transcript / session_search 기반 회상
에 강점이 있지만,
프로젝트 로컬 행동 규칙을 자동 수집·검토·승격·주입하는 shared learning plane은 아직 없다.

따라서 Hermes에 필요한 것은 새로운 독자 learner가 아니라, `agent-learner`에 연결되는 얇은 adapter 계층이다.

---

## 3. 문제 정의

Hermes에는 다음 공백이 있다.

1. 세션 종료 후 학습 가능한 패턴을 표준 이벤트로 수집하는 경로가 없다.
2. 프로젝트별 approved rule을 다음 턴에 retrieval-first 방식으로 주입하는 표준 경로가 없다.
3. memory / skills / project-local learning rule의 경계가 명확히 문서화되어 있지 않다.
4. 장기적으로 여러 하네스(Hermes, Hermit, Codex, Claude)가 같은 learning plane을 공유하려면 adapter contract가 더 명시적이어야 한다.

---

## 4. 제품 원칙

### 4.1 Shared core, thin adapters
- 학습 규칙의 추출 / lifecycle / retrieval / history는 `agent-learner` core가 담당한다.
- adapter는 하네스별 hook 연결, event normalization, prompt injection boundary만 담당한다.

### 4.2 Retrieval-first
- 모든 학습 자산을 프롬프트에 고정 주입하지 않는다.
- 현재 작업, cwd, session context에 맞는 approved rule만 top-N으로 주입한다.
- prompt bloat를 방지한다.

### 4.3 Role separation
- Hermes memory = 사용자 선호 / 환경 사실 / durable profile
- Hermes skills = 수동 또는 준정적 재사용 절차
- agent-learner rules = 프로젝트 로컬 행동 규칙 / 작업 패턴 / 검증된 learned feedback

### 4.4 Local-first with optional global fanout
- 기본값은 프로젝트 로컬 학습 우선
- 장기적으로 사용자 범위 fanout / global retrieval은 열어둘 수 있으나 MVP 필수는 아니다.

---

## 5. 목표 범위

### In scope
- Hermes adapter 설치 경로 정의
- Hermes 이벤트 캡처 포맷 정의
- Hermes용 retrieval injection 경로 정의
- CLI surface에 Hermes adapter 추가
- 프로젝트 로컬 learning 디렉터리 초기화
- history / review / dashboard와의 호환성 확보
- MVP 범위에서의 명시적 제품 결정 문서화
  - project scope 우선
  - `session_end` 이벤트 우선
  - experimental adapter로 시작

### Out of scope
- Hermes 자체 memory 시스템 대체
- Hermes skill 시스템 대체
- 자동 승인 정책의 대폭 변경
- 장기 실행 autoresearch 기능 구현
- Hermit legacy 제거 자체를 이번 작업에서 완료
- MVP에서 user-scope default 도입
- Hermes용 별도 장기 실행 background learner 추가

---

## 6. 사용자 가치

### 6.1 Hermes 사용자
- 반복적으로 교정한 작업 방식이 프로젝트 단위로 축적된다.
- 다음 세션에서 relevant rule만 자동 회수된다.
- 수동 스킬 작성 전에 실제 반복 패턴을 더 자연스럽게 포착할 수 있다.

### 6.2 agent-learner 유지보수자
- 새 하네스 지원이 “별도 learner 구현”이 아니라 “adapter 추가” 문제가 된다.
- Codex/Claude/Hermes/Hermit 사이의 수렴 전략이 분명해진다.

### 6.3 장기 제품 전략
- legacy Hermit learner를 제거하고 v2를 공용 오픈소스 라이브러리로 정리하기 쉬워진다.

---

## 7. 제안 아키텍처

```text
Hermes session/runtime
  ├─ emits normalized events
  ├─ invokes agent-learner process step
  └─ requests retrieval context before prompt execution

agent-learner Hermes adapter
  ├─ bootstrap --adapters hermes
  ├─ capture-event --adapter hermes
  ├─ process-events --adapter hermes
  └─ render-hermes-context (or shared retrieval formatter)

agent-learner shared core
  ├─ events/
  ├─ candidates/
  ├─ learning/{approved,needs_review,deprecated,...}
  ├─ history/
  ├─ index/
  └─ state/
```

---

## 8. Hermes adapter 기능 요구사항

### 8.1 설치
새 adapter installer를 제공한다.

예상 CLI:
```bash
agent-learner bootstrap --adapters hermes --target <repo-or-home> --hermes-scope project|user
```

역할:
- Hermes와 연동할 설정/훅 파일 생성 또는 patch
- `.agent-learner/` 초기 디렉터리 보장
- 필요 시 `.gitignore` 갱신
- Hermes용 안내 문서/샘플 자산 배치

### 8.2 이벤트 캡처
Hermes 세션의 적절한 종료/완료 시점에 normalized event를 기록한다.

MVP 결정:
- 1차 이벤트는 `session_end` 하나로 시작한다.
- `task_complete` 같은 세분화 이벤트는 후속 단계에서 추가 검토한다.
- transcript가 없어도 summary-only event를 허용한다.

최소 필드:
- `adapter`: `hermes`
- `event_name`: `session_end`
- `cwd`
- `session_id`
- `model`
- `timestamp`
- `payload`

`payload` 후보:
- user request summary
- assistant final summary
- tool usage summary
- verification result
- success/failure marker
- relevant transcript/session file path

예상 CLI:
```bash
agent-learner capture-event \
  --adapter hermes \
  --event-name session_end \
  --project-root . \
  --session-id <id>
```

### 8.3 이벤트 처리
캡처 직후 shared core pipeline을 실행한다.

예상 CLI:
```bash
agent-learner process-events --adapter hermes --limit 1
```

역할:
- raw event 로드
- candidate 추출
- scoring / auto-classification
- approved / needs_review / deprecated lifecycle 반영
- processed marker 기록

### 8.4 프롬프트 시점 retrieval
Hermes가 새 user request를 처리하기 직전에 relevant rule을 조회한다.

요구사항:
- retrieval-first
- top-N 제한
- cwd/task/session signal 반영
- memory/skills보다 먼저 또는 뒤에 넣을지 ordering을 명시
- injected context가 너무 크면 truncation / ranking 적용

MVP 결정:
- Hermes 전용 `render-hermes-context` 커맨드로 먼저 시작한다.
- 장기적으로는 `render-context --adapter hermes` 같은 공통 surface로 수렴할 수 있다.
- 기본 주입 위치는 memory/skills 이후의 compact learned-guidance block으로 가정하되, 실제 Hermes runtime 제약을 확인한 뒤 확정한다.

예상 인터페이스:
```bash
agent-learner render-hermes-context --project-root . --cwd <cwd> --session-id <id>
```
또는 shared retrieval API를 Hermes 런타임에서 직접 호출.

### 8.5 Review/history/dashboard 호환
Hermes adapter가 생성한 이벤트와 후보는 기존 review/history/dashboard에서 보이도록 한다.

즉 다음이 모두 adapter=hermes를 지원해야 한다.
- `review-candidates`
- `history`
- `history-summary`
- dashboard filters

---

## 9. 저장소 / 경로 제안

### agent-learner repo 내부
새 파일 후보:
- `src/agent_learner/adapters/hermes.py`
- `src/agent_learner/adapters/hermes_context.py` 또는 공통 retrieval formatter 재사용
- `plugins/hermes/README.md`
- `docs/install.md` 업데이트 (승인 후)
- `docs/quickstart.md` 업데이트 (승인 후)
- `docs/adapter-convergence.md` 업데이트 (승인 후)

### consumer repo / runtime 쪽
프로젝트 루트 기준:
```text
.agent-learner/
  events/hermes/
  candidates/
  learning/
  history/
  index/
  state/
```

---

## 10. Hermes와 기존 memory/skills의 관계

혼동을 막기 위한 명시적 규칙이 필요하다.

### memory에 남겨야 하는 것
- 사용자 선호
- 계정/환경 관련 durable facts
- 프로젝트 전반에 걸친 안정적 사실

### skill로 남겨야 하는 것
- 사람이 의도적으로 재사용하고 싶은 절차
- 다단계 운영 runbook
- 비슷한 작업에서 반복 호출할 workflow

### agent-learner rule로 남겨야 하는 것
- 특정 repo 또는 작업 맥락에서 반복적으로 유효한 행동 교정
- 검증을 통해 쓸모가 입증된 learned feedback
- “이 프로젝트에서는 이런 식으로 접근해야 한다”에 가까운 규칙

원칙:
- 모든 반복 패턴을 memory/skill로 승격하지 않는다.
- 자동 수집된 rule은 기본적으로 project-local 자산으로 본다.

---

## 11. MVP 제안

### Phase 1 — adapter skeleton
목표:
- Hermes adapter 파일 추가
- CLI에 `bootstrap --adapters hermes` 경로 노출
- `capture-event/process-events`가 `adapter=hermes`를 받도록 확장
- adapter를 experimental 상태로 노출

검증:
- 설치 명령 성공
- `.agent-learner/events/hermes/`에 raw event 생성
- processing 후 processed marker 생성
- 기존 codex/claude install path 회귀 없음

### Phase 2 — session end learning
목표:
- Hermes 세션 종료 시 자동 `capture-event`
- 후속 `process-events`
- candidate 생성 및 lifecycle 반영

검증:
- 실제 Hermes 세션 1회 후 candidate/learning/history 변화 확인
- `review-candidates --adapter hermes`에서 결과 노출

### Phase 3 — prompt-time retrieval
목표:
- 새 요청 처리 직전 approved learning retrieval
- top-N context injection
- prompt bloat 방지 규칙 적용

검증:
- 동일 프로젝트 후속 세션에서 approved rule이 relevant할 때만 주입
- irrelevant한 프로젝트에서는 주입되지 않음

### Phase 4 — convergence hardening
목표:
- Codex/Claude/Hermes adapter contract 정리
- 공통 formatter / installer / event schema 정돈
- Hermit migration 경로 문서화

검증:
- adapter별 차이가 hook boundary로 제한됨
- 공통 dashboard/history에서 adapter filter만으로 비교 가능

---

## 12. 구현 가이드라인

1. Hermes adapter는 가능하면 `common.py` 유틸을 재사용한다.
2. 새로운 core 개념을 만들기 전에 Codex/Claude 경로와 수렴시킨다.
3. 이벤트 스키마는 `core/events.py`의 normalized contract를 따른다.
4. retrieval formatting은 Hermes prompt 구조에 맞추되, ranking/retrieval 로직은 core에서 유지한다.
5. installer는 idempotent해야 한다.
6. Hermes 전용 구현이 shared core로 올라갈 수 있으면 먼저 core화를 검토한다.

---

## 13. 성공 기준

### 기능 성공
- Hermes에서 설치 가능한 adapter surface가 존재한다.
- Hermes 세션 종료 후 학습 이벤트가 자동 수집된다.
- approved learning이 후속 Hermes 요청에 retrieval-first 방식으로 주입된다.
- review/history/dashboard에서 adapter=hermes가 일관되게 동작한다.

### 제품 성공
- Hermes 쪽에 별도 legacy learner를 만들 필요가 없어진다.
- `agent-learner`가 실제로 multi-harness learning plane 역할을 수행한다.
- 이후 Hermit migration 논의에서 Hermes adapter가 선행 증거가 된다.

---

## 14. 리스크

1. Hermes memory/skills와 learning rule의 역할이 사용자에게 혼동될 수 있다.
2. retrieval injection ordering이 잘못되면 prompt bloat 또는 instruction conflict가 생길 수 있다.
3. Hermes session transcript 구조가 Codex/Claude와 달라 candidate extraction 품질이 떨어질 수 있다.
4. adapter별로 예외 처리가 늘어나면 shared core보다 adapter-local logic가 다시 비대해질 수 있다.

대응:
- 역할 구분 문서화
- top-N + truncation 강제
- raw event schema를 먼저 최소 단위로 정규화
- 공통 contract 위반 시 adapter-local workaround를 임시로만 허용

---

## 15. 오픈 질문

1. Hermes의 가장 안정적인 hook 지점은 어디인가?
2. Hermes session transcript에서 extraction에 필요한 최소 필드는 무엇인가?
3. retrieval context를 Hermes system prompt / tool preamble / user-message preprocessor 중 어디에 넣는 것이 가장 적절한가?
4. Hermes adapter는 project scope만 먼저 지원할지, user scope까지 MVP에 포함할지?
5. Hermit migration과 Hermes adapter 작업 순서를 어떻게 조정할지?

---

## 16. 출시 가드레일

MVP를 merge-ready로 보기 위한 최소 조건:
- Codex/Claude 기존 install 및 smoke path 회귀 없음
- Hermes adapter install이 idempotent함
- manual capture/process 흐름이 재현 가능함
- retrieval output이 bounded size를 유지함
- adapter가 Hermes memory/skills 파일을 자동으로 변경하지 않음
- `.dev` 문서의 핵심 결정(project scope 우선, session_end 우선, experimental rollout)이 구현/README와 일치함

---

## 17. 다음 문서/작업 연결

이 초안이 승인되면 이후 작업:
1. `docs/adapter-convergence.md`에 Hermes 추가
2. `docs/install.md`에 Hermes 설치 경로 반영
3. `docs/quickstart.md`에 Hermes 예시 추가
4. `src/agent_learner/adapters/hermes.py` 구현 시작
5. adapter contract를 별도 문서로 분리할지 검토

---

## 18. 한 줄 요약

Hermes는 자체 learner를 새로 만들지 말고, `agent-learner v2`의 shared learning plane에 붙는 세 번째 정식 adapter로 들어가는 것이 바람직하다.
