# agent-learner

Reusable self-learning engine for agent workflows.

`agent-learner` provides a generic self-learning core plus installable
adapter overlays for Codex and Claude-style environments.

[![CI](https://github.com/cafitac/agent-learner/actions/workflows/ci.yml/badge.svg)](https://github.com/cafitac/agent-learner/actions/workflows/ci.yml)
[![Release](https://github.com/cafitac/agent-learner/actions/workflows/release.yml/badge.svg)](https://github.com/cafitac/agent-learner/actions/workflows/release.yml)

## What it provides
- generic learning lifecycle engine
- aggressive auto-promotion pipeline
- Codex adapter plugin
- Claude adapter plugin
- draft -> approved -> needs_review -> deprecated lifecycle

## Why this exists

Many agent setups accumulate useful learning behavior inside a single
workspace, but the learning engine, session wrap-up logic, and adapter
install flow are often too coupled to one repo. `agent-learner` extracts
that logic into a reusable OSS foundation.

## Repository shape
- `src/agent_learner/` - core package
- `plugins/codex/` - Codex adapter overlay
- `plugins/claude/` - Claude adapter overlay
- `tests/` - lifecycle and adapter tests
- `docs/` - install and architecture docs
- `examples/` - example consumer repo outcomes

## Release gates

The project treats these as mandatory for a shippable first release:

1. adapter independence
2. one-command onboarding
3. promotion reliability

## Quick start

```bash
pipx install .
agent-learner bootstrap --target /path/to/repo
```

Alternative during development:

```bash
python3 -m pip install -e .
agent-learner bootstrap --target /path/to/repo
```

## Status
Scaffold in progress with:
- working Python CLI entry point
- Codex and Claude adapter installers
- one-command bootstrap
- lifecycle and bootstrap tests
- install and quickstart docs

## Docs

- `docs/install.md`
- `docs/quickstart.md`
- `docs/architecture.md`
- `examples/consumer-repo-layout.md`
- `CONTRIBUTING.md`

## Comparison

### How `agent-learner` is different

`agent-learner` is not trying to be a full agent runtime, a generic
memory database, or a framework-specific memory SDK.

Its current focus is narrower and more opinionated:

- governed learning asset lifecycle
- file-native, repo-visible learning artifacts
- adapter-independent installation for coding-agent environments
- Codex and Claude-style adapter overlays
- promotion and cleanup flow for learned rules

### Compared with Hermes Agent

Hermes Agent presents itself as a self-improving agent runtime with
built-in learning loops, memory, and skill evolution.

`agent-learner` is different:

- it is **not** a full runtime
- it is designed as a **learning control plane**
- it focuses on **portable learned assets and lifecycle management**
- it is meant to be installed into existing coding-agent environments
  rather than replace them

In short:

- **Hermes**: a self-improving agent runtime
- **agent-learner**: a reusable learning layer for coding-agent workflows

### Compared with LangMem

LangMem is positioned as memory and learning SDK tooling for agents:
memory extraction, long-term memory, and adaptation workflows.

`agent-learner` is different:

- it is **not** centered on framework-native memory APIs
- it emphasizes **promotion governance**
  (`inbox -> drafts -> approved -> needs_review -> deprecated`)
- it keeps learned artifacts **file-native and repo-visible**
- it is designed around **adapter overlays** for real coding-agent
  surfaces

In short:

- **LangMem**: memory and learning SDK tooling
- **agent-learner**: lifecycle-driven learning asset governance for
  coding agents

### Compared with OpenMemory / Mem0

OpenMemory and Mem0 focus on persistent memory storage, retrieval, and
automatic context injection.

`agent-learner` is different:

- it is **not just a memory store**
- it focuses on **what should become a durable learned rule**
- it makes learned artifacts visible as files that can be reviewed,
  versioned, and promoted
- it is aimed at **coding-agent workflow adaptation**, not only memory
  recall

In short:

- **OpenMemory / Mem0**: persistent memory layer
- **agent-learner**: governed learning asset lifecycle with
  adapter-aware installation

## What `agent-learner` is today

Current implemented focus:

- a generic learning core
- Codex adapter installation
- Claude adapter installation
- one-command bootstrap
- file-based lifecycle:
  - `inbox`
  - `drafts`
  - `approved`
  - `needs_review`
  - `deprecated`
- automatic lifecycle transitions
- dashboard updates
- adapter-independent installation paths

## What `agent-learner` is not

At least in its current form, `agent-learner` is **not**:

- a full autonomous agent runtime
- a hosted memory platform
- a vector database
- a framework-locked SDK
- a product-specific rules pack
- a fine-tuning platform today

## Roadmap

### Planned directions

The long-term direction is broader than file storage or simple memory
recall.

### 1. Retrieval optimization

Planned work includes:

- faster retrieval paths
- smarter selection of learned assets
- ranking logic for reusable rules and references

### 2. Token-aware retrieval

Planned work includes:

- token-budget-aware context selection
- minimizing unnecessary asset injection
- choosing the smallest useful learned context for the active task

### 3. Autoresearch-assisted refinement

Planned work includes:

- using research workflows to validate and refine learned assets
- separating weak heuristics from durable rules
- improving promotion quality through stronger evidence gathering

### 4. Training-ready export paths

Planned work includes:

- exporting approved learning assets into structured datasets
- making learned artifacts reusable beyond prompt-time retrieval
- preparing a path toward supervised or adapter-based fine-tuning
  workflows

### 5. Broader adapter ecosystem

Planned work includes:

- additional coding-agent adapters beyond Codex and Claude-style
  environments
- stronger adapter isolation guarantees
- easier upgrade and compatibility management across runtimes

## Current boundary vs roadmap

### Implemented now

- learning asset lifecycle
- file-native promoted rules
- Codex adapter
- Claude adapter
- bootstrap installation flow
- dashboard and lifecycle transitions

### Planned later

- retrieval speed optimization
- token-aware retrieval
- autoresearch-assisted knowledge refinement
- fine-tuning or dataset export workflows
- wider adapter support
