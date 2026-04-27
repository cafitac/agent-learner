# Learned Rule Drafts

- captured_at: 2026-04-23 12:38:04
- session_id: 019db855-b2cc-7141-9cb6-5d9b6e93583b
- branch: main

## change-with-tests

### Rule
동작 변경이 있으면 관련 테스트도 함께 갱신하거나 추가한다.

### Why
세션 종료 후 가장 재사용 가치가 높은 규칙은 변경과 검증을 함께 묶는 것이다.

### Scope
서비스 수정, 버그 수정, 리팩토링

### Good pattern
프로덕션 변경과 테스트 변경이 같은 세션 diff에 함께 존재한다.

### Avoid
코드만 바꾸고 테스트는 다음에 하겠다고 미루는 흐름

