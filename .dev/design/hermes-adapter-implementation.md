# Design: Hermes Adapter Implementation for agent-learner

**작성일**: 2026-04-27 15:38 KST  
**상태**: 구현 반영됨 (MVP, experimental)  
**관련 PRD**: `.dev/prd/hermes-adapter.md`

---

## 1. 목적

이 문서는 `agent-learner`에 Hermes adapter를 추가하기 위한 구현 설계를 정리한다.

PRD가 "왜 Hermes adapter가 필요한가"를 정의했다면, 이 문서는 다음을 정의한다.
- 어떤 파일을 추가/수정할지
- 어떤 CLI surface를 열지
- 어떤 이벤트 스키마를 사용할지
- Hermes 런타임과 어느 지점에서 연결할지
- MVP를 어떤 순서로 구현할지

---

## 2. 현재 기준점

이미 존재하는 adapter 관련 구현:
- `src/agent_learner/adapters/common.py`
- `src/agent_learner/adapters/codex.py`
- `src/agent_learner/adapters/claude.py`
- `src/agent_learner/adapters/codex_context.py`
- `src/agent_learner/cli/main.py`

현재 CLI surface:
- `bootstrap`
- `bootstrap --adapters codex,claude`
- `capture-event --adapter {codex,claude}`
- `process-events --adapter {codex,claude}`
- `review-candidates --adapter {codex,claude}`

즉 Hermes adapter MVP의 최소 구현은 크게 두 층이다.

1. adapter registration 확장
- CLI choice에 `hermes` 추가
- installer/export 추가

2. Hermes runtime glue 추가
- session end event capture
- prompt-time retrieval injection
- 설치용 파일/설정 생성

---

## 3. 구현 원칙

### 3.1 기존 adapter와 수렴
Hermes adapter는 새로운 패턴을 만들기보다 Codex/Claude adapter가 이미 보여준 구조를 따른다.

- installer는 `adapters/hermes.py`
- 가능하면 `common.py` 유틸 재사용
- event capture는 shared CLI 재사용
- retrieval/ranking은 core 재사용
- Hermes 고유 로직은 hook boundary에만 남김

### 3.2 Project scope 우선
MVP는 `scope=project`를 우선한다.

이유:
- 자동 학습 자산은 project-local rule로 시작하는 편이 안전함
- Hermes memory/skill과 역할 충돌을 줄일 수 있음
- user scope는 나중에 fanout/global sync 전략과 함께 추가하는 편이 낫다

명시적 결정:
- Hermes install entrypoint는 `bootstrap --adapters hermes`로 둔다.
- bootstrap 기본 adapter 목록은 초기에는 유지하고, Hermes는 opt-in experimental adapter로 시작한다.
- user scope는 `--hermes-scope user`로 제공하되, MVP 검증 범위에서는 제외 가능하다.

### 3.3 Prompt bloat 방지
Hermes는 이미 system prompt / skills / memories / toolset metadata가 큰 편일 수 있다.
따라서 adapter는 retrieval-first + small payload를 강제해야 한다.

---

## 4. 제안 파일 변경

### 4.1 신규 파일

현재 구현된 파일:

1. `src/agent_learner/adapters/hermes.py`
- installer
- Hermes auto session learning helper script 템플릿
- Hermes context hook helper script 템플릿
- `.hermes/settings.json` 병합

추가 후보(이번 MVP에서는 미도입):

2. `src/agent_learner/adapters/hermes_context.py`
- 필요 시 retrieval 결과를 Hermes 전용 포맷으로 분리
- 현재는 `codex_context.py`의 shared retrieval/render 함수를 재사용

3. `plugins/hermes/README.md`
- Hermes 사용자용 설치/작동 방식 설명
- 이번 MVP에서는 아직 미추가

### 4.2 수정 파일

1. `src/agent_learner/adapters/__init__.py`
- `install_hermes_adapter` export 추가

2. `src/agent_learner/cli/main.py`
- `bootstrap --adapters` help에 `hermes` 추가
- `capture-event/process-events/review-candidates/history` adapter choices에 `hermes` 추가
- 필요 시 `render-hermes-context` command 추가
- Hermes adapter를 experimental/opt-in으로 표시할 노출 방식 검토

3. `docs/adapter-convergence.md`
- 승인 후 Hermes를 official convergence target으로 문서화

4. `docs/install.md`, `docs/quickstart.md`
- 승인 후 Hermes 설치/예시 반영

---

## 5. Hermes adapter 책임

### 5.1 installer
예상 public function:
```python
def install_hermes_adapter_with_scope(target_root: Path, *, scope: str = "project") -> list[Path]: ...

def install_hermes_adapter(target_root: Path) -> list[Path]: ...
```

역할:
- `.hermes/` 또는 Hermes 관련 설정 파일 생성/병합
- `.agent-learner/events/hermes/` 보장
- helper script 설치
- project scope일 때 `.gitignore` 갱신
- idempotent 보장

제한:
- installer는 Hermes memory/skills/session 로그 본문을 자동 수정하지 않는다.
- installer는 adapter glue와 최소 문서/스크립트만 다룬다.
- unrelated project files를 건드리지 않는 것을 기본 원칙으로 한다.

### 5.2 auto session learning script
Codex/Claude처럼 adapter 내부 상수 문자열로 helper script를 생성한다.

예상 역할:
- stdin JSON payload 읽기
- `cwd`, `session_id`, `transcript_path`, `model`, `summary` 추출
- project root 탐지
- `capture-event --adapter hermes --event-name session_end`
- 이어서 `process-events --adapter hermes --limit 1`

### 5.3 prompt context script
새 요청 직전 relevant rule을 조회한다.

예상 역할:
- prompt/user message 추출
- project root 탐지
- `render-hermes-context` 또는 shared retrieval command 호출
- Hermes가 이해할 수 있는 injection payload stdout 출력

---

## 6. CLI 변경안

### 6.1 install command
공식 경로:
```bash
agent-learner bootstrap --adapters hermes --target <path> --hermes-scope project|user
```

기존 `install-hermes` 같은 전용 명령 대신 bootstrap-only path를 사용한다.

### 6.2 bootstrap command
현재:
```bash
agent-learner bootstrap --adapters codex,claude
```

변경:
```bash
agent-learner bootstrap --adapters codex,claude,hermes
```

주의:
- 기본값을 바로 `codex,claude,hermes`로 바꿀지는 별도 결정
- 초기에는 help text만 확장하고 default는 유지하는 편이 안전할 수 있음

### 6.3 adapter choice 확장
현재 `choices=["codex", "claude"]`인 곳을 `choices=["codex", "claude", "hermes"]`로 확장한다.

최소 대상:
- `capture-event`
- `process-events`
- `review-candidates`
- `history`
- `history-summary`

검토 대상:
- dashboard filters
- future `process`/`doctor`/`qa` surfaces

### 6.4 retrieval render command
현재 MVP 구현:
```bash
agent-learner render-hermes-context --project-root . --prompt "..." --format text|json|hook-json
```

비고:
- 구현은 `codex_context.py`의 shared retrieval/render 함수를 재사용한다.
- `hook-json`은 Hermes prompt hook helper script가 바로 stdout pass-through 할 수 있도록 지원한다.
- 장기적으로는 `render-context --adapter hermes` 형태로 수렴 가능하다.

---

## 7. 이벤트 모델

Hermes도 core의 normalized event contract를 따라야 한다.

예상 최소 event envelope:
```json
{
  "adapter": "hermes",
  "event_name": "session_end",
  "cwd": "/abs/path",
  "session_id": "...",
  "model": "openai-codex/gpt-5.4",
  "transcript_path": "/abs/path/or/null",
  "timestamp": "2026-04-27T15:38:00+09:00",
  "payload": {
    "user_summary": "...",
    "assistant_summary": "...",
    "tool_names": ["read_file", "search_files"],
    "verification": "passed|failed|unknown",
    "success": true
  }
}
```

### 필수 조건
- transcript path가 없더라도 event는 기록 가능해야 함
- payload 누락 필드는 optional이어야 함
- adapter-specific raw fields를 남기더라도 top-level normalized keys는 유지

---

## 8. Hermes 연동 지점

이 부분은 `agent-learner` 단독으로 확정할 수 없고 Hermes 쪽 runtime 구조를 확인해야 한다. 다만 현재 설계상 필요한 연결점은 명확하다.

명시적 MVP 결정:
- 학습 이벤트는 우선 `session_end` 하나만 공식 지원한다.
- retrieval 주입은 pre-prompt 1지점만 공식 지원한다.
- 둘 다 준비되지 않으면 manual CLI 흐름으로 검증 가능한 상태를 먼저 만든다.

### 8.1 session end hook
가장 중요한 지점.

필요 정보:
- session id
- cwd
- model/provider
- final summary 또는 transcript path
- success/failure signal

이 시점에서:
- `capture-event --adapter hermes --event-name session_end`
- `process-events --adapter hermes --limit 1`
호출

### 8.2 pre-prompt hook
새 user prompt 처리 직전에 retrieval을 수행.

필요 정보:
- prompt text
- cwd/project root
- optional task metadata

이 시점에서:
- approved rule top-N 조회
- Hermes prompt structure에 맞는 injection payload 생성

### 8.3 explicit/manual sync fallback
hook 통합이 바로 어렵다면 MVP 단계에서는 수동 명령도 지원 가능하다.

예:
```bash
agent-learner capture-event --adapter hermes --event-name session_end --project-root . --session-id manual-test
agent-learner process-events --adapter hermes --limit 1
```

이 fallback은 테스트 및 bring-up에 유용하다.

---

## 9. 저장 경로

MVP 기준 project-local root:
```text
<project>/.agent-learner/
  events/hermes/
  candidates/
  learning/
  history/
  index/
  state/
```

Hermes 자체 설정/도우미 파일은 scope별로 다를 수 있다.

예상 후보:
- project scope: `<project>/.hermes/...`
- user scope: `~/.hermes/...`

주의:
- 현재 Hermes가 실제로 어떤 설정 구조를 강하게 기대하는지 검증 전까지 경로를 너무 일찍 고정하지 않는다.
- adapter 설계는 "Hermes runtime 설정에 삽입되는 helper" 수준으로 유지하고, core storage는 `.agent-learner`에 집중한다.

---

## 10. Hermes context format 제안

Hermes는 Codex와 동일한 hook payload 형식을 쓸 필요는 없다.
중요한 것은 "작고 관련성 높은 learned context를 안정적으로 넣을 수 있느냐"다.

MVP 출력 예시:
```json
{
  "learning_context": {
    "rules": [
      {
        "name": "repo-local-test-order",
        "summary": "Run focused tests before full suite in this repo.",
        "why": "Validated on recent sessions.",
        "source": ".agent-learner/learning/approved/repo-local-test-order.md"
      }
    ]
  }
}
```

또는 plain text block:
```text
[Learned project guidance]
- Run focused tests before full suite in this repo.
```

선호:
- Hermes가 structured preamble 삽입을 쉽게 지원하면 JSON/structured block
- 아니면 text block

---

## 11. 구현 단계

### Phase 1 — CLI + adapter skeleton
수정:
- `adapters/hermes.py` 추가
- `adapters/__init__.py` export 추가
- `cli/main.py`에 Hermes bootstrap path 및 adapter choice 확장

검증:
- `agent-learner bootstrap --adapters hermes --target . --hermes-scope project` 동작
- `.agent-learner/events/hermes/` 생성

### Phase 2 — manual event flow
수정:
- Hermes auto session helper script 추가
- `capture-event/process-events` with `adapter=hermes` 동작 확인

검증:
- 수동 payload로 event 생성
- candidate 생성 및 processed marker 생성

### Phase 3 — retrieval injection
수정:
- `hermes_context.py` 추가
- `render-hermes-context` 또는 공통 render path 추가

검증:
- approved rule이 있을 때만 context 출력
- include-needs-review 기본 false 유지
- token budget 또는 top-N 제한 적용

### Phase 4 — runtime integration
수정:
- Hermes 런타임에 session-end / pre-prompt hook 연결

검증:
- 실제 Hermes 세션 2회 이상 반복 시 relevant learning이 자동 재주입됨

---

## 12. 테스트 전략

### 12.1 단위 테스트
대상:
- installer idempotency
- event payload normalization
- prompt context formatter
- project root detection fallback
- adapter choice 확장 시 기존 codex/claude parser 회귀 없음

### 12.2 통합 테스트
대상:
- bootstrap --adapters hermes 실행 후 파일 생성 검증
- manual capture/process flow
- approved learning retrieval path
- bootstrap에서 Hermes opt-in 경로 검증

### 12.3 smoke test
대상:
- 예시 프로젝트에서 Hermes 세션 종료 이벤트 1회 생성
- 다음 prompt에서 learned context 회수 확인
- Codex/Claude smoke가 여전히 green인지 회귀 확인

주의:
- 실제 Hermes runtime 의존 smoke는 optional integration suite로 분리 가능
- 초기에 Hermes smoke가 불안정하면 manual CLI smoke를 release gate로 사용한다.

---

## 13. 리스크와 설계 선택

### 리스크 1: Hermes prompt surface 불명확
대응:
- 먼저 manual render command 제공
- runtime hook은 후속 단계로 연결

### 리스크 2: session transcript 품질 불균일
대응:
- transcript path가 없을 때도 summary-only event 허용
- extraction pipeline이 sparse payload에서도 동작하도록 유지

### 리스크 3: memory/skill과 learned rules 중복
대응:
- PRD에 정의한 역할 구분을 installer README와 plugin README에도 반복 명시

### 리스크 4: adapter proliferation
대응:
- Hermes 전용 명령을 만들더라도 추후 공통 `render-context --adapter X`로 수렴 가능하게 구현

---

## 14. 오픈 질문

1. Hermes runtime에서 공식적으로 지원하는 session-end hook 지점이 있는가?
2. Hermes pre-prompt 단계에 structured JSON을 넣는 것이 가능한가?
3. Hermes가 session transcript path를 안정적으로 제공하는가?
4. user scope 설치 시 어떤 설정 파일을 patch해야 하는가?
5. installer가 Hermes skill/examples까지 배치해야 하는가, 아니면 pure adapter glue만 넣는 게 맞는가?

---

## 15. 추천 구현 순서

1. `cli/main.py` adapter choice 확장
2. `adapters/hermes.py` skeleton 추가
3. `bootstrap --adapters hermes` 구현
4. manual event flow 검증
5. `hermes_context.py` + render command 추가
6. Hermes runtime hook 연결
7. docs 승격 준비

---

## 16. 한 줄 결론

Hermes adapter 구현은 새로운 learner를 만드는 작업이 아니라, 기존 `agent-learner` core에 Hermes runtime을 얇게 접속시키는 adapter + hook + formatter 작업으로 범위를 엄격히 제한해야 한다.
