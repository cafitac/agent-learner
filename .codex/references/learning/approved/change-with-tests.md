---
name: change-with-tests
description: 동작 변경이 있으면 관련 테스트도 함께 갱신하거나 추가한다.
type: learned-feedback
status: "approved"
first_seen_at: "2026-04-22 21:59:21"
last_seen_at: "2026-04-23 12:38:04"
learned_from: "2026-04-23 12:38:04 + stop-hook auto-promotion"
source_session: "019db855-b2cc-7141-9cb6-5d9b6e93583b"
source_branch: "main"
auto_promoted: true
promote_count: 43
---

## Rule
동작 변경이 있으면 관련 테스트도 함께 갱신하거나 추가한다.

## Why
세션 종료 후 가장 재사용 가치가 높은 규칙은 변경과 검증을 함께 묶는 것이다.

## Scope
서비스 수정, 버그 수정, 리팩토링

## Good pattern
프로덕션 변경과 테스트 변경이 같은 세션 diff에 함께 존재한다.

## Avoid
코드만 바꾸고 테스트는 다음에 하겠다고 미루는 흐름
