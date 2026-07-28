# AI-OS Architecture Specification v1.0
## Part 0: Front Matter

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Supersedes:** ARCHITECTURAL_INVENTORY.md (planning), ARCHITECTURE_SPEC_TOC.md (planning)  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 0.1 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART0 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 0 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (1–N) MUST conform to Part 0. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis), MIGRATION_PLAN.md (phasing), ARCHITECTURE_ANALYSIS.md (architectural decisions) |

**Conformance Requirement:** Every subsequent Part (1–N) of this specification MUST explicitly reference Part 0 sections for terminology, principles, and conformance criteria. Any Part that contradicts Part 0 is non-conformant and MUST be revised.

---

### 0.2 Scope & Non-Goals

#### 0.2.1 In Scope

This specification defines the **authoritative architecture** of the AI-OS Hermes Kernel v1.0, covering:

- **Event System** — The sole communication substrate (EventBus, Event types, Subscription model, Correlation/Causation semantics, Versioning strategy)
- **Hermes Kernel** — The orchestration core owning exactly four (4) Core Components
- **Core Managers (9)** — Kernel-owned capability managers exposed via global singleton accessors
- **Service Framework** — BaseService contract, ServiceRegistry, lifecycle, dependency topology
- **Engineering Services (8)** — Event-driven SDLC phase services (Planning → Operations → Learning)
- **Capability Facade Services (4)** — Event-driven facades over Kernel Capability Managers
- **Configuration System** — Four-layer merge (defaults → app.yaml → env.yaml → env vars)
- **CLI Surface** — Command structure for kernel, workflow, service, event, checkpoint, memory, skill, MCP, council, learning operations
- **Architectural Invariants** — Invariants that MUST hold at runtime; violations constitute architecture defects

#### 0.2.2 Explicitly Out of Scope

The following are **NOT** specified in this architecture and are explicitly deferred:

| Out-of-Scope Item | Disposition |
|-------------------|-------------|
| **Implementation code** | Belongs in `src/aios/`; architecture specifies contracts, not code structure |
| **Specific LLM provider APIs** | Abstracted behind ModelRouter; provider SDKs are implementation detail |
| **Persistence schema migration tooling** | Event schema versioning strategy is specified; migration tooling is implementation |
| **Distributed EventBus** | v1.0 is single-process, in-memory only; distributed bus is v2.0 scope |
| **UI / Dashboard / Visualization** | Out of scope for kernel architecture |
| **Authentication / Authorization (AuthN/AuthZ)** | Kernel assumes trusted single-tenant process; multi-tenant auth is v2.0 |
| **Network protocols (gRPC, REST, GraphQL)** | Kernel is library-embeddable; transport bindings are adapters |
| **Specific test implementations** | Architecture specifies testable contracts; test code is implementation |
| **CI/CD pipeline definition** | Infrastructure concern, not kernel architecture |
| **Packaging / distribution (PyPI, Docker, etc.)** | Deployment artifact concern |

> **Rationale:** Architecture specifications that attempt to specify implementation details become brittle and unmaintainable. Part 0 draws a hard line: this document specifies **what the system must do and why**, not **how the code is organized**.

#### 0.2.3 AI-OS vs. Hermes Kernel Distinction

**AI-OS** is the complete engineering operating system — the full platform encompassing the kernel, all services, all capability managers, the configuration system, the CLI, and every extension point.

**Hermes** is the orchestration kernel — a single component of AI-OS. Hermes owns exactly four (4) Core Components (`EventBus`, `StateManager`, `WorkflowManager`, `ResourceManager`) and instantiates/manages the nine (9) Capability Managers.

> **AI-OS ⊃ Hermes Kernel** — Hermes is one component of AI-OS.

This Architecture Specification governs the **entire AI-OS platform**. Kernel-internal details (Core Component interfaces, initialization order, lifecycle) are specified in Part 3. Platform capabilities (services, managers, extensions) are specified in Parts 4–N.

This distinction **MUST** be maintained in all documentation, code comments, and architectural discourse to prevent category errors.

#### 0.2.4 Goals and Non-Goals

##### Goals (Architectural)

| Goal | Description |
|------|-------------|
| **Autonomous Engineering Workflows** | Enable end-to-end SDLC execution (Planning → Operations → Learning) without human intervention in the steady state. |
| **Event-Driven Orchestration** | All coordination, state transitions, and failure routing occur via the EventBus; no direct calls, no shared mutable state outside `StateManager`. |
| **Human-Governed AI** | AI Agency agents operate under Council consensus; `FinalJudge` is a mandatory gate; dissent escalation to human is a first-class path. |
| **Extensibility** | Custom events, memory backends, skills, MCP transports, consensus algorithms, AI agents, model providers, and resource types are supported via explicit extension points (Part 0.5.2). |
| **Observability** | Structured logging, correlation/causation IDs on every event, metrics emission, and health checks are built-in requirements (Principle 12). |
| **Deterministic Recovery** | Checkpoints, retry budgets, and RCA-driven recovery actions enable resume-from-failure with bounded data loss (RPO/RTO specified in Part 13). |
| **Vendor Independence** | ModelRouter abstracts LLM providers; no kernel or service code depends on a specific vendor SDK. |
| **Long-Term Maintainability** | Kernel stability via pure orchestration (Principle 2); domain logic isolated in replaceable services; explicit contracts with versioning (Principle 11). |

##### Non-Goals (Architectural)

| Non-Goal | Rationale |
|----------|-----------|
| **Replacing Software Engineers** | AI-OS augments engineering capacity; human judgment gates (FinalJudge, Council dissent) are mandatory. |
| **Depending on One AI Provider** | ModelRouter capability-based routing + fallback chains are required. |
| **Distributed Orchestration in v1.0** | Single-process, in-memory EventBus only; distributed bus is v2.0 scope (Part 0.2.2). |
| **Defining UI/UX** | Kernel is library-embeddable; presentation layer is a consumer concern. |
| **Specifying Implementation Details** | This is an architecture specification; code structure, algorithms, and libraries are implementation decisions. |
| **Building Business Applications Inside the Kernel** | Kernel and services are infrastructure; user workloads run as workflows or external consumers. |

---

### 0.3 Terminology & Conventions

#### 0.3.1 RFC 2119 Keywords

This specification uses RFC 2119 terminology with the following binding interpretations:

| Keyword | Meaning | Conformance Test |
|---------|---------|------------------|
| **MUST** | Absolute requirement. Violation = architecture defect. | Automated conformance check MUST fail. |
| **MUST NOT** | Absolute prohibition. Violation = architecture defect. | Automated conformance check MUST fail. |
| **SHOULD** | Strong recommendation. Deviation requires documented justification in ADR. | Lint warning; CI gate at ARB discretion. |
| **SHOULD NOT** | Strong discouragement. Deviation requires documented justification in ADR. | Lint warning; CI gate at ARB discretion. |
| **MAY** | Optional. No conformance implication. | Informational only. |

> **Note:** "SHALL" is not used; "MUST" is the sole mandatory keyword. "RECOMMENDED" / "NOT RECOMMENDED" are synonyms for SHOULD / SHOULD NOT.

#### 0.3.2 Core Definitions

| Term | Definition | Normative Reference |
|------|------------|---------------------|
| **Event** | Immutable, timestamped, correlated data carrier emitted to the EventBus. The **sole** mechanism for inter-component communication. | Part 2 |
| **Command** | **PROHIBITED** in v1.0. Do not use. There are no commands, only Events. | Part 0.4 Principle 2 |
| **Query** | **PROHIBITED** in v1.0. Do not use. There are no synchronous queries; state is read via StateManager (scoped, event-sourced) or emitted events. | Part 0.4 Principle 2 |
| **Kernel** | `HermesKernel` — The single orchestration instance owning exactly four (4) Core Components. | Part 3 |
| **Core Component** | One of: `EventBus`, `StateManager`, `WorkflowManager`, `ResourceManager`. Owned exclusively by Kernel. | Part 3.1 |
| **Capability Manager** | One of nine (9) kernel-owned managers providing cross-cutting capabilities (Retry, Checkpoint, RootCause, Memory, Skill, MCP, Council, AI Agency, ModelRouter). | Part 4 |
| **Engineering Service** | One of eight (8) services implementing SDLC phases. Extends `BaseService`. Communicates **only** via EventBus. | Part 5, Part 6 |
| **Capability Facade Service** | One of four (4) services (`SkillService`, `CouncilService`, `MCPService`, `MemoryService`) wrapping a Capability Manager for event-driven access. | Part 6 |
| **Global Singleton Accessor** | `get_xxx()` / `set_xxx()` function pair providing process-global access to a Kernel Component or Capability Manager. | Part 3.4 |
| **Correlation ID** | `correlation_id: UUID` — Tracks a logical workflow across all events from initiation to completion. | Part 2.5 |
| **Causation ID** | `causation_id: UUID` — Identifies the **direct cause** event that triggered the current event. | Part 2.5 |
| **Event Type** | A value of the `EventType` enum identifying the semantic meaning and payload schema of an Event. | Part 2.2 |
| **State Scope** | One of `WORKFLOW`, `SERVICE`, `GLOBAL`, `SESSION` — Isolation boundary for `StateManager` data. | Part 4.1 |
| **Checkpoint** | Persisted workflow execution snapshot enabling resume after failure or restart. | Part 4.3 |
| **Retry Budget** | Per-task limit on total attempts (initial + retries). Exhaustion emits `RetryBudgetExhausted`. | Part 4.4 |
| **Root Cause Analysis (RCA)** | Automated classification of failures into `FailureCategory` + `RecoveryAction` routing. | Part 4.5 |
| **Consensus Algorithm** | One of MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT — used by CouncilManager. | Part 4.9 |
| **Memory Type** | One of WORKING, CLAUDE, ENGINEERING, OBSIDIAN, GRAPHIFY — distinct stores with distinct backends/TTL. | Part 4.6 |

#### 0.3.3 Naming Conventions

| Convention | Rule | Example |
|------------|------|---------|
| **Event Type Enum** | `SCREAMING_SNAKE_CASE`, domain-prefixed | `TASK_CREATED`, `WORKFLOW_STEP_FAILED` |
| **Event Class** | `PascalCase`, suffix `Event` | `TaskCreatedEvent`, `WorkflowStepFailedEvent` |
| **Event Payload Fields** | `snake_case` | `task_id`, `execution_id`, `error_message` |
| **Service Class** | `PascalCase`, suffix `Service` | `PlanningService`, `CodingService` |
| **Manager Class** | `PascalCase`, suffix `Manager` | `StateManager`, `RetryManager` |
| **Configuration Class** | `PascalCase`, suffix `Config` | `KernelConfig`, `RetryPolicy` |
| **Global Accessor** | `get_<snake_case>()`, `set_<snake_case>()` | `get_event_bus()`, `set_retry_manager()` |
| **Environment Variable** | `AIOS_<SECTION>_<KEY>` (uppercase, underscores) | `AIOS_KERNEL_LOG_LEVEL` |

---

### 0.4 Architectural Principles

The following principles are **axiomatic** for AI-OS v1.0. Every architectural decision in Parts 1–N MUST be traceable to one or more principles. A design that violates a principle is non-conformant.

#### Principle 1: Event-First Communication
> **All** inter-component communication **MUST** occur via the EventBus. There are **no** direct service-to-service calls, **no** synchronous RPC, **no** shared mutable state outside `StateManager`.

- **Rationale:** Decouples lifecycle, enables observability, enables replay/debugging, enables distributed evolution (v2.0).
- **Enforcement:** Static analysis MUST flag any `service_x.method()` call across service boundaries. EventBus is the **only** valid dependency between services.

#### Principle 2: Kernel as Pure Orchestrator
> The Kernel **MUST** own exactly four (4) Core Components and **MUST NOT** contain domain logic (planning, coding, review, testing, deployment, operations, learning).

- **Rationale:** Kernel stability = system stability. Domain logic evolves rapidly; orchestration primitives evolve slowly.
- **Enforcement:** Kernel source files (`kernel.py`, `kernel_management.py`) MUST NOT import any service module.

#### Principle 3: Capability Managers Are Kernel-Owned
> The nine (9) Capability Managers are **instantiated, owned, and lifecycle-managed by the Kernel**. They are exposed via Global Singleton Accessors for system-wide access.

- **Rationale:** Capabilities (retry, checkpoint, RCA, memory, skills, MCP, council, AI agency, model routing) are cross-cutting infrastructure. Central ownership prevents duplication and ensures consistent policy.
- **Enforcement:** Each Capability Manager MUST have exactly one global accessor pair. No service MAY instantiate its own RetryManager, CheckpointManager, etc.

#### Principle 4: Global Singleton Accessors Are Explicit Architecture
> The 13 `get_xxx()`/`set_xxx()` accessor pairs are **architectural fixtures**, not implementation shortcuts. They **MUST** be documented, initialized in deterministic order, and testable via `set_xxx(mock)`.

- **Rationale:** Dependency injection frameworks add complexity without benefit in a single-process kernel. Explicit globals are testable, debuggable, and auditable.
- **Conformance:** Part 3.4 specifies the complete registry, initialization order, and testing protocol.

#### Principle 5: Services Are Event-Driven Actors
> Every Service **MUST** extend `BaseService`, declare `depends_on`, subscribe in `on_start()`, emit typed Events, and **MUST NOT** call other services directly.

- **Rationale:** Uniform lifecycle, topological start/stop, health checks, and event-only communication enable composition and replacement.
- **Enforcement:** ServiceRegistry validates `depends_on` DAG. BaseService provides `emit()`/`subscribe()` helpers; direct EventBus access is permitted but discouraged.

#### Principle 6: Engineering Services Implement SDLC Phases
> The eight (8) Engineering Services form a strict linear pipeline: **Planning → Coding → Review → Testing → Deployment → Operations → Learning → Memory**. Each phase emits exactly one "Completed" event that triggers the next.

- **Rationale:** Mirrors human SDLC; enables checkpointing, RCA, and learning at phase boundaries.
- **Deviation:** Parallel execution within a phase (e.g., multiple coding tasks) is managed by WorkflowManager, not by service-to-service calls.

#### Principle 7: Capability Facade Services Bridge Events to Managers
> The four (4) Capability Facade Services (`SkillService`, `CouncilService`, `MCPService`, `MemoryService`) **MUST** translate incoming Events into Manager calls and emit result Events. They **MUST NOT** contain business logic.

- **Rationale:** Keeps Managers pure (no EventBus dependency); keeps Services thin; enables Manager unit testing without EventBus.

#### Principle 8: Immutable Events with Correlation & Causation
> Every Event **MUST** carry `correlation_id` (workflow trace) and `causation_id` (direct cause). Events **MUST** be immutable (frozen dataclass, `kw_only=True`).

- **Rationale:** Enables distributed tracing, replay debugging, and causal analysis without log parsing.
- **Enforcement:** Part 2.1 specifies the `Event` base contract; Part 2.2 the `EventType` catalog.

#### Principle 9: Explicit Failure Handling via Events
> Failures **MUST** be communicated via Events (`TaskFailed`, `RetryBudgetExhausted`, `RootCauseAnalyzed`). There are **no** exceptions crossing service boundaries.

- **Rationale:** Exceptions are control flow; events are data. Eventual consistency requires failure as data.
- **Enforcement:** BaseService `on_error()` MUST emit failure event; MUST NOT raise.

#### Principle 10: Configuration Is Declarative & Layered
> Configuration **MUST** use the four-layer merge (defaults → app.yaml → env.yaml → env vars). No hardcoded defaults in Kernel or Manager code.

- **Rationale:** Environment parity; secrets via env vars; reproducible deployments.
- **Enforcement:** Part 7 (Configuration) specifies schema, merge semantics, validation.

#### Principle 11: Version & Compatibility Are First-Class
> Event schemas, configuration schemas, and APIs **MUST** carry version identifiers. Breaking changes require major version bump and migration path.

- **Rationale:** Production systems evolve. Schema evolution strategy is specified in Part 2.6.

#### Principle 12: Observability Is Built-In, Not Bolted On
> Every component **MUST** emit structured logs (JSON, correlation IDs) and Events for state transitions. `StructuredLogger` is the single logging abstraction.

- **Rationale:** Debugging distributed event flows requires correlation from the start.

---

### 0.5 Conformance & Extension Points

#### 0.5.1 Conformance Levels

| Level | Description | Verification |
|-------|-------------|--------------|
| **L1: Structural** | Code compiles, imports resolve, base classes implemented | `mypy --strict`, `pytest` collection |
| **L2: Contract** | Event schemas match spec; interfaces honor signatures | Schema validation tests, interface compliance tests |
| **L3: Behavioral** | Runtime invariants hold (event ordering, lifecycle, failure routing) | Integration tests (21 scenarios in `tests/integration/`) |
| **L4: Architectural** | No principle violations (direct calls, missing correlation IDs, kernel domain logic) | Static analysis rules (Part 0.4 Principles 1–12) |

#### 0.5.2 Extension Points (Explicitly Permitted Variability)

| Extension Point | Mechanism | Governance |
|-----------------|-----------|------------|
| **Custom Event Types** | Subclass `Event` with new `EventType` enum value | MUST follow Part 2.1/2.2; register in EventType catalog |
| **Custom Memory Backend** | Implement `MemoryBackend` ABC | MUST satisfy Part 4.6 contract; register via `MemoryManager` |
| **Custom Skill** | Implement `Skill` interface; register via `SkillManager` | MUST be sandboxed; MUST emit `SkillExecuted`/`SkillFailed` |
| **Custom MCP Transport** | Implement `MCPTransport` for new protocol | MUST satisfy `MCPManager` contract (Part 4.8) |
| **Custom Consensus Algorithm** | Add to `ConsensusAlgorithm` enum; implement in `CouncilManager` | MUST satisfy liveness/safety properties (Part 4.9) |
| **Custom AI Agency Agent** | Subclass base `AIAgent`; register via `AIAgencyService` | MUST emit audit `*Requested`/`*Completed` event pairs (Part 4.10) |
| **Custom Model Provider** | Register in `ModelRouter` capability registry | MUST implement capability-based routing interface (Part 4.11) |
| **Custom Resource Type** | Extend `ResourceType` enum; register quota in `ResourceManager` | MUST implement allocation/wait-queue/TTL semantics (Part 4.12) |

> **Non-Extension Points (MUST NOT vary):** EventBus interface, Kernel lifecycle, BaseService contract, ServiceRegistry topological order, StateManager scopes, Checkpoint disk format, RetryBudget semantics, RCA keyword lists (extensible via config only), global accessor signatures.

#### 0.5.3 Architecture Decision Records (ADRs)

Any deviation from Principles (0.4) or Non-Extension Points (0.5.2) **MUST** be documented in an ADR in `docs/DECISIONS.md` with:

1. **Decision** — What is being deviated
2. **Rationale** — Why the principle cannot be met
3. **Impact** — Affected components, failure modes
4. **Mitigation** — How risk is bounded
5. **Expiry** — Date or milestone when deviation will be resolved

ADRs are reviewed by the Architecture Review Board (ARB) and are part of the conformance evidence.

---

### 0.6 Implementation vs. Architecture Target Tracking

This specification documents the **Architecture Target (v1.0)**. The current implementation (v0.1.x) has known gaps documented in `ARCHITECTURAL_INVENTORY.md` §10–11. Throughout this specification, differences are annotated using:

> **Implementation (v0.1.x)** — Current code behavior (may deviate from target)  
> **Architecture Target (v1.0)** — Normative requirement for v1.0 conformance

All Parts 1–N MUST use this notation consistently. Implementation gaps are **not** rationale for changing the Architecture Target; they are work items for the implementation team.

---

### 0.7 High-Level Layer Overview

The following orientation diagram shows the major architectural layers of AI-OS. Detailed specifications for each layer appear in subsequent Parts.

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-OS Platform                           │
│  (Complete Engineering Operating System)                        │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Hermes Kernel                              │
│  • EventBus        • StateManager    • WorkflowManager         │
│  • ResourceManager • Global Singletons • ServiceRegistry       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Capability Managers (9)                      │
│  Retry • Checkpoint • RootCause • Memory • Skill               │
│  MCP • Council • AI Agency • ModelRouter                       │
│  (Kernel-owned, exposed via global singleton accessors)        │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Engineering Services (8)                       │
│  Planning → Coding → Review → Testing → Deployment             │
│  → Operations → Learning → Memory                               │
│  (Event-driven, BaseService, topological lifecycle)            │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              Capability Facade Services (4)                     │
│  SkillService • CouncilService • MCPService • MemoryService     │
│  (Thin event↔manager bridges; no business logic)               │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Extensions / Plugins                         │
│  Custom Events • Memory Backends • Skills • MCP Transports     │
│  Consensus Algorithms • AI Agents • Model Providers • Resources│
└─────────────────────────────────────────────────────────────────┘
```

> **Note:** This diagram is an orientation aid only. Normative layer definitions, interfaces, and invariants are specified in Parts 3–6 and 14. This overview does not replace detailed specifications.

---

**END OF PART 0 — FRONT MATTER**

*This document is FROZEN. Subsequent Parts (1–N) MUST conform to the terminology, principles, scope, and conformance model established herein. Any Part that contradicts Part 0 is non-conformant.*