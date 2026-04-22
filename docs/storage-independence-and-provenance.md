# Storage Independence And Learning Provenance

## Status

Accepted design note. The storage-coupling portion is already reflected in the
current implementation; the remaining work is mostly around stronger
provenance, comparison, and revision history.

## Current state

`agent-learner` already has a shared-core data plane under `.agent-learner/`:

- `.agent-learner/events/`
- `.agent-learner/candidates/`
- `.agent-learner/state/`

The earlier design problem was that Codex-side learning could write
session-wrap artifacts into `.omx/wiki/session-log/`, which made the adapter
feel coupled to OMX even though OMX is supposed to be an optional runtime
integration, not a required storage dependency.

That coupling has been removed from the current repo direction: canonical
learning state now lives under `.agent-learner/`, and external wiki/KB systems
are outside the canonical lifecycle.

The current implementation also does **not** have a real "compare old learned
rule vs new learned rule and update the existing rule with an explicit diff
decision" flow.

What exists today:

- candidate extraction from raw events
- processed markers to avoid reprocessing the same event
- rule lifecycle buckets (`draft`, `approved`, `needs_review`, `deprecated`)
- same-name overwrite semantics when saving a rule
- duplicate file cleanup by exact rule filename
- `promote_count` and status refresh on lifecycle transitions

What does not exist today:

- semantic duplicate detection across differently named candidates
- candidate-to-existing-rule comparison before promotion
- explicit supersedes/replaces history between old and new rule versions
- canonical promotion ledger explaining why a rule changed

## Problem

Two problems were historically mixed together:

1. Storage coupling
   Learning artifacts could end up under `.omx/wiki/`, which made the project
   feel OMX-dependent.

2. Weak provenance
   Durable rules can carry `source` and `evidence`, but there is no canonical
   audit trail for:
   - what candidate caused a rule change
   - why the rule was promoted or updated
   - what older rule content was replaced

This leads to a bad middle ground:

- too much noisy session-log style storage
- not enough durable, reviewable learning history

## Decision

`agent-learner` will treat `.agent-learner/` as the only canonical storage root.

Adapter and runtime folders stay thin:

- `.codex/` and `.claude/` are adapter surfaces
- `.omx/` and `.omc/` are optional integration surfaces
- `.agent-learner/` is the learning system of record

We will not keep full session logs as a default durable artifact.

Instead, we will keep:

- raw normalized events for short-lived reprocessing/debugging
- extracted candidates
- durable rules
- promotion/update ledger entries
- provenance metadata on rules

See also: `docs/scope-learning-system.md` for the product-boundary decision
that keeps wiki/KB systems outside the canonical learning scope.

## Design goals

1. `agent-learner` must stay OSS-standalone without requiring OMX.
2. Learning history must explain *why* a rule exists or changed.
3. Full session transcripts/logs should not become the default durable memory format.
4. Rule updates should be explicit, reviewable, and recoverable.
5. OMX integration should be optional projection, not primary storage.

## Canonical storage layout

Proposed canonical tree:

```text
.agent-learner/
  events/
    codex/
    claude/
  candidates/
    codex/
    claude/
  learning/
    inbox/
    drafts/
    approved/
    needs_review/
    deprecated/
  history/
    promotions.jsonl
  state/
    processed-events/
    current-model.txt
```

Notes:

- `learning/` becomes the canonical lifecycle root.
- Existing `.codex/references/learning/` can remain adapter-facing for a migration
  window, but the long-term source of truth should move to `.agent-learner/learning/`.
- Wiki/KB systems remain external integrations, not part of the canonical tree.

## Why session logs are not the primary artifact

Full session logs are useful only for:

- debugging extraction failures
- replaying event processors
- manual forensic review in exceptional cases

They are poor default durable memory because they are:

- noisy
- runtime-specific
- privacy-sensitive
- expensive to review
- easy to overfit into bad rules

So the default durable artifact is **not** `session-log`.

The default durable artifact is:

- candidate
- promoted rule
- promotion ledger entry

## Provenance model

Each durable rule should retain compact provenance, not a full session dump.

Add or standardize these metadata fields on promoted rules:

- `source_event`
- `source_adapter`
- `derived_from_candidate`
- `decision`
- `decision_reason`
- `supersedes`
- `superseded_by`
- `evidence_excerpt`
- `last_validated_at`
- `last_validated_by`

Example:

```yaml
source_event: "codex/stop-2026-04-22T03-00-00Z.json"
source_adapter: "codex"
derived_from_candidate: "candidate-update-tests-with-behavior.md"
decision: "promoted"
decision_reason: "repeated pattern across multiple events and manually validated"
supersedes: "keep-tests-updated@v1"
evidence_excerpt: "Update tests whenever behavior changes."
last_validated_at: "2026-04-22T03:00:00Z"
last_validated_by: "human-review"
```

## Promotion ledger

Add a canonical append-only ledger:

```text
.agent-learner/history/promotions.jsonl
```

Each entry records a learning decision:

```json
{
  "ts": "2026-04-22T03:00:00Z",
  "action": "promote",
  "rule": "keep-tests-updated",
  "from": "draft",
  "to": "approved",
  "source_adapter": "codex",
  "source_event": "codex/stop-2026-04-22T03-00-00Z.json",
  "derived_from_candidate": "candidate-update-tests-with-behavior.md",
  "reason": "repeated pattern across 3 events and manually validated"
}
```

Allowed actions:

- `candidate_created`
- `promote`
- `refresh`
- `revise`
- `mark_needs_review`
- `deprecate`
- `reject_candidate`

This ledger replaces the need for durable session-log storage in the normal path.

## Rule update and comparison model

This is the missing capability that should be added next.

When a new candidate is extracted, the system should compare it against existing
rules before creating a brand-new durable rule.

The comparison system should be explicit enough that two different reviewers can
understand why the engine chose:

- `new_rule`
- `refresh_existing`
- `revise_existing`
- `fork_rule`
- `reject_candidate`

### Matching stages

1. Exact name match
   - If candidate slug maps to an existing rule name, treat it as a direct revision candidate.

2. Strong semantic match
   - Compare normalized rule text, summary, triggers, and scope.
   - If similarity is above threshold, treat as a revision candidate.

3. Weak related match
   - If topic overlaps but meaning differs, keep both and mark for review instead of auto-merging.

### Comparison inputs

Each comparison should evaluate the candidate against the strongest existing
matches using these normalized inputs:

- normalized rule text
- normalized summary
- scope
- triggers
- task types
- file patterns
- project/language/framework tags
- source adapter
- evidence excerpt
- validation state

Normalization rules:

- lowercase for comparison only
- collapse repeated whitespace
- strip punctuation that does not affect imperative meaning
- preserve negation words such as `not`, `never`, `avoid`, `except`
- preserve scope qualifiers such as `only`, `always`, `when`, `unless`

### Comparison output shape

The comparison primitive should return a structured result, not just a boolean:

```json
{
  "decision": "refresh_existing",
  "candidate": "candidate-update-tests-with-behavior.md",
  "matched_rule": "keep-tests-updated",
  "confidence": "high",
  "reasons": [
    "same imperative meaning",
    "scope unchanged",
    "newer evidence only"
  ],
  "field_diffs": {
    "rule": "unchanged",
    "summary": "narrower wording",
    "scope": "unchanged",
    "evidence": "updated"
  },
  "review_required": false
}
```

This result should be ledgered even when no durable rule file is changed.

### Decision outcomes

- `new_rule`
  - no meaningful existing match

- `refresh_existing`
  - same meaning, newer evidence
  - update `last_seen_at`, `promote_count`, provenance, and ledger

- `revise_existing`
  - meaning is materially changed but still the same conceptual rule
  - overwrite durable content, record `supersedes`, write ledger entry

- `fork_rule`
  - related topic but incompatible guidance
  - keep separate rules and mark the older one `needs_review` if necessary

- `reject_candidate`
  - too weak, too noisy, or contradicted by validated rule state

### Decision criteria

#### `new_rule`

Choose when:

- no existing rule crosses the semantic match threshold
- the candidate introduces a genuinely new reusable behavior constraint
- overlap with older rules is incidental rather than conceptual

Write effects:

- create a new draft or approved rule
- record provenance fields
- append `new_rule` or `promote` ledger entry

#### `refresh_existing`

Choose when:

- imperative meaning is effectively the same
- scope and constraints are unchanged
- the new candidate only adds fresher evidence or repeated confirmation

Write effects:

- keep existing durable rule text
- update `last_seen_at`
- increment `promote_count` or an explicit `refresh_count`
- update provenance and evidence references
- append `refresh` ledger entry

#### `revise_existing`

Choose when:

- the candidate is clearly about the same conceptual rule
- but the durable guidance text should change materially
- and the new wording is better, more accurate, or more recent

Examples:

- same rule but clearer boundary
- same rule but broader validated scope
- same rule but stronger exception handling language

Write effects:

- update durable rule content
- record `supersedes`
- preserve previous evidence reference in the ledger
- append `revise` ledger entry with field-level diff summary

#### `fork_rule`

Choose when:

- topic is related
- but the new candidate cannot safely replace the existing rule
- and both may be valid under different scopes, adapters, or contexts

Examples:

- one rule is Codex-specific and another is Claude-specific
- one rule applies only to Django services while the other is repo-wide
- one rule is for migration work and another is for steady-state maintenance

Write effects:

- keep existing rule unchanged
- create a separate new rule or draft
- add cross-reference metadata if useful
- optionally mark the older rule `needs_review` if the boundaries are unclear

#### `reject_candidate`

Choose when:

- the signal is too weak or too generic
- the candidate is only a one-off narrative log
- the candidate contradicts a better-validated rule
- the candidate is duplicated by a stronger existing rule and adds no new evidence

Write effects:

- no durable rule change
- append `reject_candidate` ledger entry
- optionally store a short rejection reason for future tuning

### Confidence and review gate

Every comparison should produce:

- `confidence`: `low | medium | high`
- `review_required`: `true | false`

Default rule:

- `high` confidence + no material text change -> auto `refresh_existing`
- any material text change -> `review_required = true` unless deterministic policy allows auto-revise
- contradiction or ambiguous scope -> force review

Suggested safe defaults:

- auto-allow: `new_rule` only for drafts, `refresh_existing` for evidence-only updates
- review-required: `revise_existing`, `fork_rule`, contradiction handling
- auto-reject: obviously weak generic candidates

### Field-level diff policy

The comparison engine should explain which fields changed:

- `rule`
- `summary`
- `scope`
- `triggers`
- `task_types`
- `file_patterns`
- `projects`
- `languages`
- `frameworks`
- `validated_on_models`
- `excluded_models`
- `evidence`

Each field diff should be labeled as one of:

- `unchanged`
- `metadata_only`
- `narrowed`
- `broadened`
- `contradicted`
- `rewritten`
- `updated_evidence`

This keeps revision decisions inspectable without storing full session logs.

## Update policy

Default safe policy:

- never silently replace an approved rule
- write an explicit comparison result first
- require either:
  - deterministic high-confidence refresh semantics, or
  - review gate for material revisions

Safe auto-update cases:

- same normalized rule text
- stronger or newer evidence only
- metadata-only refresh
- repeated confirmation on the same conceptual rule

Review-required cases:

- changed imperative meaning
- narrower or broader scope than existing rule
- contradiction with validated rule text
- conflict between adapters

### Candidate-to-rule comparison workflow

Recommended flow:

1. Extract candidate from raw event.
2. Rank top existing rule matches.
3. Produce structured comparison result.
4. Apply policy:
   - auto refresh
   - draft new rule
   - queue revision review
   - reject candidate
5. Write ledger entry.
6. Update provenance on any affected durable rule.

This makes the comparison result itself a first-class artifact.

### Suggested internal APIs

Shared-core primitives that should likely exist:

- `find_matching_rules(candidate, rules) -> list[RuleMatch]`
- `compare_candidate_to_rule(candidate, rule) -> ComparisonResult`
- `decide_candidate_action(candidate, matches, policy) -> ComparisonDecision`
- `apply_comparison_decision(decision, lifecycle, ledger) -> ApplyResult`
- `append_promotion_ledger(entry) -> Path`

Suggested data types:

- `RuleMatch`
  - rule name
  - similarity score
  - match reasons

- `ComparisonResult`
  - matched rule
  - field diffs
  - semantic relationship
  - confidence

- `ComparisonDecision`
  - final decision enum
  - review required
  - reason
  - write actions

### Heuristic ordering

Preferred decision precedence:

1. `reject_candidate`
   - if the candidate is below minimum quality
2. `refresh_existing`
   - if same meaning and no material text change
3. `revise_existing`
   - if same conceptual rule but durable text must change
4. `fork_rule`
   - if overlap exists but safe merge is not possible
5. `new_rule`
   - if no meaningful match exists

This ordering biases toward reuse before proliferation, while still avoiding
unsafe silent merges.

## OMX integration policy

OMX remains useful, but only as an integration target.

Allowed optional integrations:

- link learning assets to external wiki/KB pages
- let external tools export or summarize learning assets into their own wiki surfaces
- query external wiki systems during human review without making them canonical storage

Disallowed architectural assumption:

- `agent-learner` requiring `.omx/` to exist for normal operation

In short:

- `OMX-aware` is good
- `OMX-dependent` is not

## Migration path

### Phase 1

- completed: stop writing canonical artifacts into `.omx/wiki/session-log/`
- add `.agent-learner/history/promotions.jsonl`
- add provenance fields to rule metadata

### Phase 2

- move canonical lifecycle root from `.codex/references/learning/` to `.agent-learner/learning/`
- keep adapter-facing compatibility shims during migration

### Phase 3

- implement candidate-to-existing-rule comparison
- add revision vs refresh decisions
- add review-needed decisions for conflicting updates

### Phase 4

- keep any wiki export outside the canonical learning lifecycle
- remove any remaining assumption that `.omx/` exists

## Non-goals

- storing full transcripts forever
- coupling durable learning to a specific runtime's wiki format
- building a generic memory database
- auto-merging conflicting guidance without review

## Recommended next implementation slice

Smallest remaining high-value slice:

1. Introduce `history/promotions.jsonl`.
2. Add provenance fields to `LearningRule`.
3. Keep wiki/KB integration external to the canonical learning tree.
4. Add a comparison primitive that decides:
   - `new_rule`
   - `refresh_existing`
   - `revise_existing`
   - `reject_candidate`

That gives us a durable audit trail without locking the project to OMX.
