# Scope Declaration — Learning System, Not Unified Wiki

## Status

Accepted product and architecture direction.

## Positioning

`agent-learner` is the canonical learning system for reusable agent behavior.

It is **not** a unified wiki, knowledge-base orchestrator, or cross-runtime
session-log manager.

Its job is to:

- capture learning signals from agent/runtime adapters
- extract candidate rules
- review, promote, revise, and deprecate durable learning assets
- preserve provenance and lifecycle history
- retrieve the right approved rules at prompt time
- provide structured inputs for future `autoresearch` workflows

## Why the scope stays narrow

Different runtimes already have different knowledge surfaces:

- OMX can manage `.omx/wiki/`
- HermitAgent can manage project KB/wiki flows
- Claude-oriented environments may manage knowledge differently again

Trying to make `agent-learner` unify all of those surfaces would make it
heavier in the wrong way:

- different schemas
- different validation rules
- different lifecycle semantics
- unclear source-of-truth boundaries
- tighter coupling to specific runtimes

That would weaken the OSS story and blur the product boundary.

## Canonical storage owned by agent-learner

`agent-learner` should own and evolve only the learning-oriented data plane:

```text
.agent-learner/
  events/
  candidates/
  learning/
  history/
  index/
  state/
```

These artifacts are the canonical inputs for:

- retrieval
- review workflows
- promotion/deprecation history
- future `autoresearch`

## What is explicitly out of scope

`agent-learner` should not become responsible for:

- `.omx/wiki/` management
- `kb/wiki/` management
- cross-runtime wiki synchronization
- bidirectional wiki mirroring
- session-log consolidation across tools
- narrative documentation ownership

Those systems may continue to exist, but they are not part of the canonical
learning lifecycle.

## Relationship to external wiki/KB systems

External wiki/KB systems may reference learning assets, but `agent-learner`
should treat them as adjacent systems, not managed storage.

The preferred relationship is:

- `agent-learner` owns structured learning state
- wiki/KB tools own human-facing narrative knowledge

If light interoperability is ever needed, it should stay minimal:

- optional links or references from a learning asset to an external page
- optional exports performed by another tool

But not:

- required wiki writes for normal operation
- canonical data mirrored into multiple stores
- read/write coupling between learning lifecycle and wiki lifecycle

## Autoresearch implication

Future `autoresearch` should build on the structured learning plane, not on
runtime-specific wiki storage.

The important inputs are:

- source events
- extracted candidates
- approved rules
- revision/deprecation history
- evidence and provenance metadata
- retrieval/index metadata

This keeps `autoresearch` focused on machine-usable learning data instead of
runtime-specific narrative pages.

## Product thesis

> `agent-learner` is a learning control plane for reusable agent behavior.

Not:

> a universal knowledge hub for every runtime's wiki system.

That narrower thesis is more OSS-friendly, easier to explain, and better
aligned with the long-term `autoresearch` goal.
