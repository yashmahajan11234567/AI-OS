# AI-OS Part 15 — Runtime Architecture Map

## Authority Statement

**Authoritative Sources: Parts 0–14.**

This document maps authoritative architectural requirements to runtime behavior. Other Part 15 documents may be consulted for terminology or consistency, but they do not establish architectural authority. References to Part 15 files (`README.md`, `context.md`, `dependency-map.md`, `components.md`, `configuration.md`, `observability.md`, `deployment.md`, `implementation-contracts.md`, `adrs.md`, `glossary.md`, `review-checklist.md`, `testing.md`) are *supporting Part 15 documentation* only — they are never treated as a source of architecture. If a Part 15 file and Parts 0–14 disagree, Parts 0–14 govern.

## Canonical Runtime Rules

These are summary rules only. They MUST NOT introduce requirements not already supported by Parts 0–14.

### Runtime Rule 1 — Lifecycle
The runtime lifecycle follows the authoritative Kernel lifecycle. Part 1 §1.9.1 establishes a five-state FSM (UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED); Part 4 §4.3.1 establishes an eight-state LifecycleManager FSM. Both are preserved as CONFLICT-INIT-01. No other lifecycle state is invented.

### Runtime Rule 2 — Initialization
Initialization follows the authoritative phase/dependency ordering (Part 1 §1.7.3, §1.8.3, §1.10.2). The Part 4 §4.2.3 five-phase model diverges and is preserved as CONFLICT-INIT-01. No initialization ordering is invented.

### Runtime Rule 3 — Communication
Architectural inter-component communication follows the authoritative EventBus/event model (Part 0 Principle 1; Part 1 §1.6 Event-First Communication principle #4; Part 2). Direct post-initialization calls between kernel-owned entities are PROHIBITED except initialization-time injection (CC-IR-001/002).

### Runtime Rule 4 — Configuration
Runtime configuration follows the authoritative configuration lifecycle and freeze rules (Part 0 §0.4 Principle 10; Part 1 §1.10.2; Part 3 §3.5). ConfigurationManager MUST be frozen before any Service initializes (INV-INIT-002, INV-CM-006). No reload/hot-config is invented.

### Runtime Rule 5 — Security
Runtime behavior preserves authoritative security boundaries and authorization requirements (Part 4 §4.7; SecurityManager M8 is the sole enforcement authority for authN/authZ/secrets/trust).

### Runtime Rule 6 — Observability
Runtime execution preserves authoritative logging/tracing/observability requirements (Part 0 §0.4 Principle 12; Part 2 §2.1 envelope; observability.md as supporting reference). No telemetry backend is invented.

### Runtime Rule 7 — Shutdown
Shutdown follows authoritative lifecycle and ordering constraints (Part 1 §1.11.2; reverse-phase rule; EventBus drains and is last to shut down, Part 3 §3.3.2). Shutdown timeout and forced-shutdown semantics remain UNSPECIFIED (GAP-DEP-03/04).

## 1. Document Identity

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-PART15-RUNTIME-MAP |
| **Version** | 1.0.0 |
| **Status** | **CONDITIONALLY READY** — Architecture-level runtime model is reconstructable from Parts 0–14 (predominantly Part 1 and Part 3), with all gaps, unspecified areas, and conflicts preserved. Runtime verification is CONDITIONALLY READY because some runtime-ordered dependencies remain UNSPECIFIED pending resolution of CONFLICT-CC-01 / CONFLICT-CM-01 and because no conformance *test specifications/implementations* exist yet (`testing.md` is a populated testing-architecture document but its test specs are pending, GAP-P15-06). |
| **Date** | 2026-08-14 |
| **Classification** | Informative — Architecture-level runtime model (bridge between static architecture and runtime implementation) |
| **Author** | Architecture Evolution & Extensibility Documentation (Part 15) |
| **Distribution** | All AI-OS engineers, architects, reviewers, AI agents |
| **Related Documents** | Parts 0–14; `README.md`, `context.md`, `dependency-map.md`, `components.md`, `configuration.md`, `observability.md`, `deployment.md`, `implementation-contracts.md`, `adrs.md`, `glossary.md`, `review-checklist.md` (all under `part15/`) |

This document defines the **architecture-level runtime model** of AI-OS: how the static component/dependency architecture defined in Parts 0–14 becomes runtime behavior. It is the bridge between authoritative architectural definitions and actual runtime implementation. It MUST NOT become a source-code implementation specification.

---

## 2. Purpose

AI-OS needs a runtime map because static architecture (component definitions, dependency graphs, interface contracts) does not by itself specify *when* and *in what order* things become operational. The runtime map explains:

- **how static architecture becomes runtime behavior** — components defined in Parts 0–14 are instantiated and wired by the Hermes Kernel per mandated initialization phases (Part 1 §1.7–§1.10);
- **why runtime ordering matters** — HermesKernel is a state machine (UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED, Part 1 §1.9.1) whose phases enforce deterministic, dependency-ordered construction of Core Components and Core Managers;
- **how component dependencies influence initialization** — the mandated phase numbers (Phase 0–8 for Core entities, Phase 9+ for Services) *are* the initialization ordering, derived from the dependency declarations in Part 1 §1.7.3 and §1.8.3;
- **how runtime lifecycle relates to context** — context is produced, propagated, and consumed during execution (context.md §8), and correlation/causation identifiers are carried by every event (Part 2 §2.1), tying lifecycle to runtime observability;
- **how runtime behavior relates to events, workflows, agents, memory, plugins, security, and observability** — all inter-entity communication is EventBus-first (Part 0 Principle 1; Part 1 §1.6 (Event-First Communication principle, #4)), so runtime behavior *is* event-driven flow coordinated by the Kernel, with security enforced by SecurityManager (M8) and observability provided by ObservabilityManager (M9).

This document describes **architecture-level runtime behavior, not implementation technology**. No programming language, process supervisor, container, or message broker is selected herein.

---

## 3. Scope

### 3.1 In Scope

Where source-backed, this document covers:

- runtime topology (single deployable unit: HermesKernel, deployment.md §3.1);
- initialization (phased, deterministic, Part 1 §1.10);
- lifecycle (Kernel state machine and Core entity lifecycle, Part 1 §1.9, Part 3 §3.4);
- dependency ordering (mandated phase numbers, Part 1 §1.7–§1.8);
- readiness (KernelReady; accessor pre-RUNNING prohibition via INV-CM-006, Part 1 §1.8.4);
- execution (event-driven operational flow, Part 2; workflow/agent/council, Part 4/6/12);
- shutdown (reverse phase order, Part 1 §1.11);
- failure (classification and recovery, Part 1 §1.12);
- recovery (retry/restart/isolation, Part 1 §1.12.3);
- runtime verification (contract traceability, implementation-contracts.md §10).

### 3.2 Out of Scope

Unless authoritative sources require them, the following are **excluded** and remain UNSPECIFIED unless Parts 0–14 explicitly govern them:

- Docker, Podman, Kubernetes, Nomad (deployment.md §3.2, UNSPECIFIED);
- cloud platforms (AWS/Azure/GCP, deployment.md §3.2, UNSPECIFIED);
- CI/CD platforms (deployment.md §3.2, UNSPECIFIED);
- Terraform / Pulumi / IaC (deployment.md §3.2, UNSPECIFIED);
- operating-system service managers (systemd, etc., UNSPECIFIED);
- programming-language implementation (UNSPECIFIED — no language is mandated by Parts 0–14);
- concrete process supervisors / supervisor trees (UNSPECIFIED);
- specific databases / storage backends (deployment.md §3.2; StorageManager defines namespaces, not backends);
- specific message brokers (EventBus is the substrate; its backing transport is UNSPECIFIED).

No deployment technology is invented.

---

## 4. Runtime Model

**"Runtime" in AI-OS** means the period during which a HermesKernel instance is in a state other than UNINITIALIZED or TERMINATED, executing the responsibilities of its owned Core Components, Core Managers, and registered Services through EventBus-mediated communication.

What executes:
- Core Components (4) and Core Managers (9) — kernel-owned, phased, deterministic (Part 1 §1.6–§1.8);
- Services (N, dynamic) — self-registering, lifecycle-managed (Part 1 §1.6 (Services self-register via ServiceRegistry, table line); Part 3 §3.4);
- event handlers, workflow executions, agent/council activities, plugin/integration invocations — driven through EventBus.

What remains static (non-executing at runtime):
- architectural specification documents (Parts 0–14);
- Workflow Definitions (immutable specifications, Part 7 §7.3.3; WF.MUST.1 in implementation-contracts.md);
- frozen configuration after Phase 3 (Part 1 §1.10.2, INV-CM-006).

How components become operational: via the mandated phase sequence (§7). How dependencies affect execution: post-initialization direct calls between kernel-owned entities are PROHIBITED except initialization-time injection (Part 1 §1.6 (Event-First Communication principle, #4), CC-IR-001/002). How lifecycle states relate to runtime: the Kernel FSM gates all operation (no publish before RUNNING; no accessor before RUNNING, Part 1 §1.9.1, INV-CM-006 at §1.8.4).

| Runtime Concept | Definition | Source | Status |
|-----------------|------------|--------|--------|
| HermesKernel | Singleton orchestration core; sole deployable unit; owns Core Components, Core Managers, ServiceRegistry | Part 1 §1.1, §1.6; deployment.md §3.1 | **EXISTING** |
| Core Component | One of 4 kernel-owned infrastructure primitives (EventBus, ServiceRegistry, ConfigurationManager, and C4 — *ambiguous*, see CONFLICT-CC-01) | Part 1 §1.7.1; dependency-map.md §7.1 | **EXISTING** (C4 CONFLICT) |
| Core Manager | One of 9 kernel-owned capability managers exposed via singleton accessors | Part 1 §1.8.1 | **EXISTING** (identity CONFLICT-CM-01) |
| Service | BaseService-derived entity, self-registers, lifecycle-managed | Part 1 §1.6 (Services self-register via ServiceRegistry, table line); Part 3 §3.4 | **EXISTING** |
| Initialization Phase | Numbered ordered stage (0–N) with strict dependency ordering | Part 1 §1.7.3, §1.8.3 | **EXISTING** |
| Shutdown Phase | Numbered stage (N–0) with strict reverse dependency ordering | Part 1 §1.11.2 | **EXISTING** |
| Kernel State Machine | UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED | Part 1 §1.9.1 | **EXISTING** |
| EventBus | Sole inter-component/manager/service communication substrate | Part 0 Principle 1; Part 1 §1.6 (Event-First Communication principle, #4); Part 2 | **EXISTING** |
| Runtime Context | Execution/Workflow context produced and consumed during execution; correlation via EventBus envelope | context.md §7–§9; Part 2 §2.1 | **EXISTING** (lifecycle details partially UNSPECIFIED) |
| Deployable Unit | HermesKernel — single process; no independently deployable subsystems | deployment.md §3.1 | **EXISTING** |

---

## 5. Runtime Entities

Not every architectural component is independently runnable. The authoritative runtime entities are kernel-owned Core Components, Core Managers, and Services. Agents, councils, and workflows are *capabilities orchestrated by* Core Managers (AgentManager M6, WorkflowManager M7, SecurityManager M8 for councils) rather than independently-booted runtimes. Plugins/integrations are extension points realized through managers.

| Entity | Runtime Role | Lifecycle | Dependencies | Source | Status |
|--------|--------------|-----------|--------------|--------|--------|
| HermesKernel | Orchestration core; drives FSM and phases | UNINITIALIZED→…→TERMINATED | — | Part 1 §1.9 | **EXISTING** |
| EventBus (C1) | Communication substrate; first to RUNNING, last to SHUTDOWN | Part 3 §3.3.2 states | EventBus none | Part 1 §1.7.1; Part 3 §3.3 | **EXISTING** |
| ServiceRegistry (C2) | Service registration, topology, health | Part 3 §3.4.9 | EventBus | Part 1 §1.7.1 | **EXISTING** |
| ConfigurationManager (C3) | Immutable config authority; freezes post-Phase 3 | Part 1 §1.7.2 | EventBus | Part 1 §1.7.1 | **EXISTING** |
| C4 Core Component | *Ambiguous* — Part 1: LifecycleManager @ Phase 3; Part 3: StructuredLogger @ Phase 3; Part 4: LifecycleManager @ Phase 1 (Foundation) (see CONFLICT-CC-01 + CONFLICT-INIT-01) | n/a | EventBus (+ others per source) | Part 1 §1.7.1 vs Part 3 §3.2.1 vs Part 4 §4.2.3 | **CONFLICT** |
| MemoryManager (M1) | Episodic/semantic/working memory | Part 1 §1.8 | EventBus, ConfigurationManager | Part 1 §1.8.1 | **EXISTING** (Part 4 model does not enumerate M1; CONFLICT-CM-01 + CONFLICT-INIT-01) |
| LLMManager (M2) | Model routing, prompt templating | Part 1 §1.8 | EventBus, ConfigurationManager | Part 1 §1.8.1 | **EXISTING** (Part 4 names M2=StateManager; CONFLICT-CM-01) |
| ToolManager (M3) | Tool registry, sandbox, permission | Part 1 §1.8 | Phase 4–5 (Model A) | Part 1 §1.8.1 | **EXISTING** (Part 4 model does not enumerate; CONFLICT-INIT-01) |
| StorageManager (M4) | Persistence abstraction | Part 1 §1.8 | Phase 4–5 (Model A) | Part 1 §1.8.1 | **EXISTING** (Part 4 names M4=WorkflowManager @ Phase 2; CONFLICT-CM-01 + CONFLICT-INIT-01) |
| ContextManager (M5) | Conversation context, window mgmt | Part 1 §1.8 | Phase 4–6 (Model A) | Part 1 §1.8.1 | **EXISTING** (Part 4 names M5=SecurityManager; CONFLICT-CM-01) |
| AgentManager (M6) | Agent spawn/lifecycle/communication | Part 1 §1.8 | Phase 4–6 (Model A) | Part 1 §1.8.1; Part 12 | **EXISTING** (Part 4 model does not enumerate; CONFLICT-INIT-01) |
| WorkflowManager (M7) | Workflow def/exec/checkpoint | Part 1 §1.8; Part 4 §4.6 | Phase 4–6 (Model A) / Phase 4 (Model B) | Part 1 §1.8.1 | **EXISTING** (placement differs by model; CONFLICT-INIT-01) |
| SecurityManager (M8) | AuthN/AuthZ/audit/secrets/trust | Part 1 §1.8; Part 4 §4.7 | Phase 4–6 (Model A) / Phase 3 (Model B) | Part 1 §1.8.1; Part 4 §4.7 | **EXISTING** (placement differs by model; CONFLICT-INIT-01) |
| ObservabilityManager (M9) | Metrics/tracing/logging/alerting | Part 1 §1.8; observability.md | all prior | Part 1 §1.8.1 | **EXISTING** (schema/backends UNSPECIFIED) |
| Service (N) | Business/engineering capability | Part 3 §3.4.9 | Dependency topology | Part 1 §1.6 (Services self-register via ServiceRegistry, table line); Part 3 §3.4 | **EXISTING** |
| Agent | Capability instance spawned by AgentManager | delegated to M6 | M6 | Part 12 (collaboration); Part 6 §6.x (AIAgencyService) | **EXISTING** (runtime internals UNSPECIFIED) |
| Council | Consensus coordination via CouncilManager | delegated to manager | manager | Part 12 (collaboration); Part 6 §6.2 (CouncilManager) | **EXISTING** (consensus internals UNSPECIFIED) |
| Workflow Instance | Execution of an immutable Workflow Definition | Part 7 §7.4; Part 12 events.md §5 | WorkflowManager | Part 7 §7.3.3; implementation-contracts WF.MUST.1/2 | **EXISTING** (scheduling UNSPECIFIED) |
| Plugin/Integration | Extension-point realization (skill, MCP transport, custom event, custom backend, custom agent) | via owning manager | owning manager | Part 0 §0.5.2; README §8 | **EXISTING** (discovery/lifecycle UNSPECIFIED) |

---

## 6. Runtime Phases

The architecture **explicitly establishes** Kernel lifecycle phases and numbered initialization/shutdown phases. These are not invented here; they are quoted from Part 1.

| Phase | Purpose | Entry Condition | Exit Condition | Source | Status |
|-------|---------|-----------------||----------------|--------|--------|
| UNINITIALIZED | Kernel constructed, no entities live | Process start / `new HermesKernel` | `initialize()` called | Part 1 §1.9.1 | **EXISTING** |
| INITIALIZING | Phased construction of C1–C4 then M1–M9 then Services | `initialize()` called | all entities initialized; config frozen | Part 1 §1.9.1; §1.10 | **EXISTING** |
| RUNNING | Steady operational state; accepts work | INITIALIZING complete; `KernelReady` published | `shutdown()` called | Part 1 §1.9.1; §1.10.3 | **EXISTING** |
| SHUTTING_DOWN | Phased teardown (reverse order); event draining | `shutdown()` called | all entities shut down | Part 1 §1.9.1; §1.11 | **EXISTING** |
| TERMINATED | Final state; no further ops | SHUTTING_DOWN complete; `KernelTerminated` published | (terminal) | Part 1 §1.9.1; §1.11.3 | **EXISTING** |
| Service Initialization sub-phase | Services initialized in topological batches (Phase 9+) | Core entities RUNNING | Services RUNNING | Part 1 §1.10.2; §1.10.3 | **EXISTING** |

**Conflict — kernel state machine divergence (CONFLICT-INIT-01 family):** Part 1 §1.9.1 establishes a five-state Kernel FSM — `UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED` — with no distinct `DEGRADED`, `ROLLBACK`, or `RECOVERY` kernel states (recovery is described as occurring *within* `RUNNING`, Part 1 §1.12.3). Part 4 §4.3.1, by contrast, establishes an eight-state LifecycleManager FSM — `UNINITIALIZED → INITIALIZING → OPERATIONAL → DEGRADED → SHUTTING_DOWN → TERMINATED` plus `ROLLBACK_IN_PROGRESS` and `RECOVERY_IN_PROGRESS` — where `OPERATIONAL` (not `RUNNING`) is the steady state and `DEGRADED`/`RECOVERY_IN_PROGRESS` are first-class kernel states. The `DEGRADED`/`FAILED` states in Part 3 §3.4.9 are a *per-Service* lifecycle and do **not** resolve this kernel-level divergence. This runtime-map documents both machines and does **not** resolve which is authoritative; the divergence is preserved as part of **CONFLICT-INIT-01** (see §31).

---

## 7. Initialization Ordering

This is the critical section. The architecture provides **two incompatible phased-initialization models**; this document preserves both and does **not** resolve which is authoritative. The divergence is registered as **CONFLICT-INIT-01** (see §31).

### 7.A Model A — Part 1 nine-phase model (Phase 0–8 + Phase 9+ Services)

Taken from the mandated phase assignments in Part 1 §1.7.3 (Core Components), §1.8.3 (Core Managers), and the Service topological plan (Phase 9+) in Part 1 §1.10.2.

**EXPLICIT ORDER** (Part 1 states it directly):
- Core Components: Phase 0 EventBus → Phase 1 ServiceRegistry → Phase 2 ConfigurationManager → Phase 3 C4 (ambiguous, CONFLICT-CC-01).
- Core Managers: Phase 4 (MemoryManager, LLMManager), Phase 5 (ToolManager, StorageManager), Phase 6 (ContextManager, AgentManager), Phase 7 (WorkflowManager, SecurityManager), Phase 8 (ObservabilityManager).
- Within-phase deterministic sub-order: Phase 4 M1→M2; Phase 5 M3→M4; Phase 6 M5→M6; Phase 7 M7→M8 (Part 1 §1.8.3).
- Services: Phase 9+, topological batches per ServiceRegistry (Part 1 §1.10.2).
- Kernel reaches `RUNNING` and publishes `KernelReady` after Phase 8 + Service init (Part 1 §1.9.1, §1.10.3).

### 7.B Model B — Part 4 five-phase model (Phase 1–5)

Taken from Part 4 §4.2.3 (Initialization Phases) and Part 4 §4.3 (LifecycleManager). Note this model differs from Model A in **phase count**, **phase boundaries**, **state-machine vocabulary** (`OPERATIONAL` not `RUNNING`), **within-phase ordering** (alphabetical by manager name, not the Part 1 M1→M2 sub-order), and **Core Manager set** (CONFLICT-CM-01).

**EXPLICIT ORDER** (Part 4 §4.2.3 states it directly):
- Phase 1 (**Foundation**): ConfigurationAuthority, IdentityProvider (Core Components), LifecycleManager.
- Phase 2 (**State & Storage**): StateManager, StorageManager.
- Phase 3 (**Governance**): SecurityManager, ResourceManager, HealthManager.
- Phase 4 (**Execution**): CapabilityManager, WorkflowManager.
- Phase 5 (**Observability**): ObservabilityManager.
- Kernel reaches `OPERATIONAL` only after HealthManager reports all managers READY (Part 4 §4.3.3); Part 4 §4.1 §5.2 additionally frames a 5-band scheme (Phase 0 EventBus → Phase 1 ServiceRegistry → Phase 2 Core Components + Config → Phase 3 Core Managers + Config freeze → Phase 4 Engineering Services).

### 7.C Ordering reconciliation

- **Shared invariant:** phases are strictly sequential; no phase skipped/reordered/parallelized across phases; reverse order on shutdown (Part 1 §1.11.2; Part 4 §4.3.6).
- **Divergent:** phase *numbering*, phase *granularity*, kernel steady-state *name* (`RUNNING` vs `OPERATIONAL`), and within-phase *sub-order* (Part 1 M1→M2 deterministic sub-order vs Part 4 alphabetical-by-name).
- **Core Component ordering conflict:** Model A places C4 (LifecycleManager per Part 1) at Phase 3; Model B treats LifecycleManager as a Phase 1 Foundation entity. C4 identity itself is CONFLICT-CC-01.

**DERIVED (both models):** The phase numbering *is itself* the topological resolution of declared dependency edges. No additional startup order is inferred beyond what each model encodes.

**UNSPECIFIED ORDER**: (a) the concrete sequence in which individual *Services* register or begin handling work within their batch (both models); (b) cross-process initialization (single deployable unit assumed, deployment.md §3.1, but distributed not defined — GAP-DEP-01).

| Component | Model A (Part 1) | Model B (Part 4) | Basis | Status |
|-----------|------------------|------------------|-------|--------|
| EventBus (C1) | Phase 0 (first) | Phase 0 (EventBus Bootstrap) | Part 1 §1.7.3 / Part 4 §4.1 §5.2 | **EXISTING** (both) |
| ServiceRegistry (C2) | Phase 1 | Phase 1 | Part 1 §1.7.3 / Part 4 §4.1 §5.2 | **EXISTING** (both) |
| ConfigurationManager (C3) | Phase 2 | Phase 2 (config load) / Phase 3 (freeze) | Part 1 §1.7.3 / Part 4 §4.1 §5.2 | **EXISTING** (both) |
| C4 Core Component | Phase 3 (last core, LifecycleManager per Part 1) | Phase 1 (LifecycleManager, Foundation) | Part 1 §1.7.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CC-01 + CONFLICT-INIT-01) |
| MemoryManager (M1) | Phase 4 | — (State/Storage Phase 2 per Part 4) | Part 1 §1.8.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CM-01 + CONFLICT-INIT-01) |
| LLMManager (M2) | Phase 4 (after M1) | — | Part 1 §1.8.3 | **CONFLICT** (CONFLICT-CM-01) |
| ToolManager (M3) | Phase 5 | — | Part 1 §1.8.3 | **CONFLICT** (CONFLICT-CM-01) |
| StorageManager (M4) | Phase 5 (after M3) | Phase 2 (State & Storage) | Part 1 §1.8.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CM-01 + CONFLICT-INIT-01) |
| ContextManager (M5) | Phase 6 | — | Part 1 §1.8.3 | **CONFLICT** (CONFLICT-CM-01) |
| AgentManager (M6) | Phase 6 (after M5) | — | Part 1 §1.8.3 | **CONFLICT** (CONFLICT-CM-01) |
| WorkflowManager (M7) | Phase 7 | Phase 4 (Execution) | Part 1 §1.8.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CM-01 + CONFLICT-INIT-01) |
| SecurityManager (M8) | Phase 7 (after M7) | Phase 3 (Governance) | Part 1 §1.8.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CM-01 + CONFLICT-INIT-01) |
| ObservabilityManager (M9) | Phase 8 (last) | Phase 5 (Observability) | Part 1 §1.8.3 / Part 4 §4.2.3 | **CONFLICT** (CONFLICT-CM-01 + CONFLICT-INIT-01) |
| Services (N) | Phase 9+ (topological batches) | Phase 4 (Engineering Services) | Part 1 §1.10.2 / Part 4 §4.1 §5.2 | **CONFLICT** (CONFLICT-INIT-01) |

**Status note:** Component rows are marked **EXISTING** only where both models agree on the relative placement; rows where the two models disagree (or where Part 4 does not enumerate the Part 1 manager) are marked **CONFLICT** because the normative ordering is not single-valued across authoritative sources. This is the substance of **CONFLICT-INIT-01**.

---

## 8. Runtime Dependency Map

Cross-reference: dependency-map.md §5.3 (dependency types) and §7. The architecture distinguishes multiple dependency kinds; they are NOT identical to startup order.

| Source | Target | Dependency Type | Runtime Meaning | Source | Status |
|--------|--------|-----------------|-----------------|--------|--------|
| All Core Components/Managers | EventBus | TEMPORAL (init) + EVENT (runtime) | EventBus MUST reach RUNNING first; all post-init comms via EventBus | Part 1 §1.7.3; CC-IR-001; dependency-map.md §5.3 | **EXISTING** |
| ServiceRegistry | EventBus | TEMPORAL | Phase 1 after Phase 0 | Part 1 §1.7.3 | **EXISTING** |
| ConfigurationManager | EventBus | TEMPORAL | Phase 2 after Phase 0 | Part 1 §1.7.3 | **EXISTING** |
| C4 | EventBus, ServiceRegistry, ConfigurationManager | TEMPORAL | Phase 3 after 0–2 | Part 1 §1.7.3 | **EXISTING** (C4 CONFLICT) |
| Services | Dependency topology | TEMPORAL (init) + STRUCTURAL + RUNTIME | Topological init batches; runtime interaction per topology | Part 1 §1.10.2; Part 3 §3.4 | **EXISTING** |
| All Managers | ConfigurationManager | TEMPORAL | Frozen config available before manager init (INV-CM-006, INV-INIT-002) | Part 1 §1.10.2 | **EXISTING** |
| ObservabilityManager (M9) | all managers | TEMPORAL (init) | Last manager; consumes telemetry from all | Part 1 §1.8.3 | **EXISTING** |
| All entities | EventBus | EVENT (runtime) | Post-init direct calls PROHIBITED; EventBus-only | Part 1 §1.6 (Event-First Communication principle, #4); CC-IR-001 | **EXISTING** |
| SecurityManager (M8) | protected operations | SECURITY | Authorizes state transitions / resource access | Part 4 §4.7; CMP.MUST.2 | **EXISTING** |
| Services | LifecycleManager | LIFECYCLE | Lifecycle coordination via LifecycleManager | Part 3 §3.4; Part 1 §1.6 (Event-First Communication principle, #4) | **EXISTING** |
| Shutdown | reverse init order | TEMPORAL (shutdown) | Shutdown phases S0–SN reverse of init | Part 1 §1.11.2; INV-DEP-08 | **EXISTING** |

Note: `dependency-map.md` records runtime-ordered dependencies as **UNSPECIFIED** at Level 5 pending this document (§15). With this document authored and traceable to Part 1/Part 4, those runtime-ordered assertions are now classified per the rows above (EXISTING where both authoritative models agree; CONFLICT where they diverge). CONFLICT-CC-01 / CONFLICT-CM-01 / **CONFLICT-INIT-01** remain unresolved and are preserved (§31).

---

## 9. Component Lifecycle

Cross-reference: components.md §13 (Component Lifecycle). The authoritative lifecycle states are the Kernel FSM (§6) and Service lifecycle (Part 3 §3.4.9: UNREGISTERED → REGISTERED → INITIALIZING → RUNNING → DEGRADED → FAILED → SHUTTING_DOWN → SHUTDOWN). Core Component lifecycle states are given for EventBus (Part 3 §3.3.2: UNINITIALIZED/INITIALIZING/RUNNING/DRAINING/SHUTDOWN).

| Component | Created | Initialized | Ready | Running | Shutdown | Recovery | Source | Status |
|-----------|---------|-------------|-------|---------|----------|----------|--------|--------|
| HermesKernel | Kernel ctor | `initialize()` | RUNNING state | RUNNING | `shutdown()` | re-init PROHIBITED (INV-LC-003) | Part 1 §1.9 | **EXISTING** |
| EventBus (C1) | Kernel ctor | Phase 0 | RUNNING | RUNNING | DRAINING→SHUTDOWN | none specified | Part 3 §3.3.2 | **EXISTING** |
| ServiceRegistry (C2) | Kernel ctor | Phase 1 | RUNNING | RUNNING | SHUTDOWN | none specified | Part 1 §1.7; Part 3 §3.4 | **EXISTING** |
| ConfigurationManager (C3) | Kernel ctor | Phase 2 | RUNNING + frozen | RUNNING | SHUTDOWN | none specified | Part 1 §1.7 | **EXISTING** |
| C4 | Kernel ctor | Phase 3 | RUNNING | RUNNING | SHUTDOWN | none specified | Part 1 §1.7 / Part 3 §3.2 | **CONFLICT** |
| Core Managers (M1–M9) | Kernel ctor | Phase 4–8 | RUNNING | RUNNING | reverse phase | restart if CRITICAL (max 2) then FATAL | Part 1 §1.8, §1.12.3 | **EXISTING** |
| Service | self-register | topological batch | REGISTERED→RUNNING | RUNNING | SHUTTING_DOWN→SHUTDOWN | restart if CRITICAL non-critical | Part 3 §3.4.9 | **EXISTING** |
| Agent | AgentManager spawn | delegated | delegated | delegated | delegated | UNSPECIFIED | Part 12; Part 4 §4.10 | **UNSPECIFIED** (lifecycle internals) |
| Council | manager-init | delegated | delegated | delegated | delegated | UNSPECIFIED | Part 12; Part 4 §4.9 | **UNSPECIFIED** |
| Workflow Instance | WorkflowManager | delegated | delegated | delegated | delegated | checkpoint/replay | Part 7 §7.4; Part 4 §4.6 | **EXISTING** (scheduling UNSPECIFIED) |
| Plugin/Integration | owning manager load | delegated | delegated | delegated | delegated | UNSPECIFIED | Part 0 §0.5.2 | **UNSPECIFIED** |

---

## 10. Readiness Model

The architecture distinguishes three related but distinct conditions:

- **initialized** — the entity's `initialize()` has completed (Part 1 §1.7.2 `initialize()`);
- **ready / RUNNING** — Kernel has entered RUNNING and published `KernelReady` (Part 1 §1.10.3); accessor access before RUNNING throws `KernelNotReadyError` (INV-CM-006, Part 1 §1.8.4);
- **operational** — accepting and processing work (RUNNING steady state).

| State | Meaning | Entry Condition | Exit Condition | Source | Status |
|-------|---------|-----------------||----------------|--------|--------|
| Initialized (entity) | `initialize()` completed | `initialize(kernel)` returns | n/a (until shutdown) | Part 1 §1.7.2 | **EXISTING** |
| Kernel RUNNING / Ready | All core entities initialized; config frozen; `KernelReady` emitted | INITIALIZING complete | `shutdown()` | Part 1 §1.10.3 | **EXISTING** |
| Service RUNNING | Service initialized and passing health | INITIALIZING complete | DEGRADED/FAILED/SHUTDOWN | Part 3 §3.4.9 | **EXISTING** |
| Service DEGRADED | Functional but impaired | health check failure / TRANSIENT→DEGRADED | recovery / FAILED | Part 1 §1.12.1; Part 3 §3.4.9 | **EXISTING** |
| Service FAILED | Non-functional | CRITICAL unrecovered | restart / isolation | Part 1 §1.12.1 | **EXISTING** |

Health aggregation algorithm (how per-component health becomes system health) is UNSPECIFIED — GAP-DEP-08. Probe exposure mechanism is UNSPECIFIED — GAP-DEP-06. A separate "readiness probe" concept is not independently established beyond Kernel RUNNING and Service health states.

---

## 11. Runtime Context

Cross-reference: context.md (full context architecture). This section explains only how *runtime behavior* interacts with context; it does NOT redefine context architecture.

- **Context creation** — produced by an architectural element (e.g., workflow step), per Part 7 §7.2.2 (context.md §8).
- **Context propagation** — explicit, declarative, along declared transition paths; immutable once produced (Part 7 Principle 5; context.md §9).
- **Context lifecycle** — Creation → Propagation → Consumption → Transformation → (Fault recording / Suspension / Resumption) → Completion → archived; Deletion/Discard and Persistence are UNSPECIFIED (context.md §8).
- **Correlation** — every event carries `correlation_id` and `causation_id` (Part 2 §2.1; INV-EVT-004/005; context.md INV-CTX-1/2). Correlation propagates through thread/task-local storage for logging (Part 3 §3.1; context.md §9.1).
- **Execution association** — execution_context_id ↔ correlation_id and ↔ trace_id mappings are UNSPECIFIED (context.md §7). The relationship between Execution Context (Part 9/10) and Workflow Context (Part 7) is UNSPECIFIED (context.md §7, glossary §29).

Where context.md records UNSPECIFIED/GAP status, this runtime map preserves it and does not elaborate.

---

## 12. Configuration and Runtime Initialization

Cross-reference: configuration.md. The runtime-relevant configuration facts:

- **Availability** — four-layer merge (defaults → app.yaml → env.yaml → env vars), precedence 1<2<3<4 (configuration.md §5–§6; Part 0 §0.4 Principle 10). Layer 1 (defaults) loaded at bootstrap; merge completes by Phase 2/3 (configuration.md §4 citing Part 3 §3.5, Part 1 §1.10.2).
- **Validation** — schema validation during merge is EXISTING as a requirement (Part 0 §0.4 Principle 10). *Specific* validation rules (type, required-field, range, cross-field) are UNSPECIFIED (configuration.md §11; GAP-DEP-05). Behavior on validation failure is partially source-backed: **invalid configuration MUST prevent the kernel from reaching RUNNING state** (`INV-CM-VAL-003`, Part 3 §3.5) — EXISTING; the precise mechanism/abort semantics of that failure are UNSPECIFIED beyond this gate.
- **Precedence** — defined (EXISTING); merge semantics for non-scalar/conflicting structures are UNSPECIFIED (configuration.md §7: scalar replacement, object merge, list merge, null/delete all UNSPECIFIED).
- **Dependencies** — ConfigurationManager (C3) MUST be frozen before any Service initializes (INV-INIT-002; INV-CM-006; Part 1 §1.10.2). Configuration freeze is EXISTING (configuration.md §4).
- **Runtime-affected behavior** — frozen config is read-only after Phase 3 (DERIVED from Part 1 §1.10.2, configuration.md §12). **Reload behavior is UNSPECIFIED** (configuration.md §12).

No fail-fast mechanism beyond `INV-CM-VAL-003` is invented. The architecture mandates that invalid configuration MUST block RUNNING (Part 3 §3.5) but does not specify the abort mechanism; only that validation occurs during merge and that config freezes before Service init.

---

## 13. Security Runtime Initialization

Cross-reference: Part 4 §4.7 (SecurityManager), implementation-contracts CMP.MUST.2. Source-backed requirements:

- SecurityManager (M8) initializes in Phase 7 (after WorkflowManager), depending on Phase 4–6 managers (Part 1 §1.8.1, §1.8.3) — **EXISTING**.
- SecurityManager is the **sole enforcement authority** for authentication, authorization, policy enforcement, secret handling, audit coordination, identity, and trust boundaries (Part 4 §4.7, opening).
- **Authentication** — all principals authenticated before authorization; no authorization without successful authentication (Part 4 §4.7.3, invariant). Authentication flow emits `AuthenticationFailedEvent` on failure (Part 4 §4.7.3).
- **Authorization** — evaluated for protected operations (e.g., StateManager transitions consult SecurityManager, Part 4 §4.2; denial emits `StateTransitionDeniedEvent`).
- **Secret availability** — SecurityManager owns secret handling (storage, rotation, injection, access control, Part 4 §4.7.2). The runtime *moment* secrets become available relative to Phase 7 is implied by M8 init order but the precise injection timing/lifecycle is not separately specified — treated as DERIVED from M8 Phase 7 init.
- **Trust boundaries** — owned and enforced by SecurityManager (Part 4 §4.7).

No security startup ordering beyond the mandated Phase 7 placement is invented. Cross-cutting auth for all interactions (not only M8-internal) is established by Part 4 §4.7 but the global enforcement hookpoint timing is DERIVED from EventBus-first communication (every protected op is an event that SecurityManager may authorize).

---

## 14. Observability Runtime Initialization

Cross-reference: observability.md. Source-backed requirements:

- ObservabilityManager (M9) initializes **last**, Phase 8, depending on all prior managers (Part 1 §1.8.1, §1.8.3) — **EXISTING**. This is the only explicitly established observability *initialization* ordering.
- StructuredLogger is the single logging abstraction; logs MUST be structured JSON with `correlation_id` (Part 0 §0.4 Principle 12; observability.md §6). Whether StructuredLogger is a Core Component (Part 3 §3.2 names C4=StructuredLogger) or a separate substrate is subject to CONFLICT-CC-01.
- Metrics owned/aggregated by ObservabilityManager (M9) — responsibility EXISTING; metric schema and backend UNSPECIFIED (observability.md §5).
- Tracing via event-envelope `trace` object (`trace_id`/`span_id`/`parent_span_id`, W3C Trace Context) — concepts EXISTING; backend UNSPECIFIED (observability.md §5, Part 12 events.md §4).
- Audit records tamper-evident (WORM) — PROPOSED via P13-ADR-006 (Draft); not accepted architecture (observability.md §5, §13).
- Health signals / probes — defined for collaboration domain (Part 12 §12.9); endpoint technology UNSPECIFIED (GAP-DEP-06).

No telemetry infrastructure is invented. Observability initialization timing beyond "M9 Phase 8" and "StructuredLogger early (C4, if Part 3 authoritative)" is UNSPECIFIED.

---

## 15. Operational Execution Model

After RUNNING, the runtime executes work through EventBus-mediated flow. The architecture establishes event-driven execution (Part 0 Principle 1; Part 1 §1.6 (Event-First Communication principle, #4)) and specific envelope semantics (Part 2 §2.1) but does not fully specify end-to-end request/workflow sequences beyond lifecycle and event contracts.

| Runtime Flow | Start | Processing | Completion | Failure | Source | Status |
|--------------|-------|------------|------------|---------|--------|--------|
| Event dispatch | publish to EventBus | validate, enqueue, order (priority/global/correlation), dispatch to subscribers | subscriber handler returns | Dead letter/retry/timeout per EventBus failure handling (Part 2 §2.4.1) | Part 2 §2.1, §2.4.1 | **EXISTING** (dispatch internals UNSPECIFIED) |
| Service operation | Service RUNNING handles subscribed event | per service logic | emits result event | health degradation / failure (Part 1 §1.12) | Part 1 §1.6 (Services self-register via ServiceRegistry, table line); Part 3 §3.4 | **EXISTING** |
| Workflow execution | WorkflowManager starts instance | step transitions via events; checkpoints | terminal outcome event | `WorkflowAuthorizationFailedEvent` etc. (Part 4 §4.6) | Part 7 §7.4; Part 4 §4.6 | **EXISTING** (scheduling UNSPECIFIED) |
| Agent task | AgentManager / AIAgencyService invokes agent | agent executes capability | `*Completed` event pair | `*Failed` event | Part 12 (collaboration); Part 6 (facade services); Part 0 §0.5.2 | **EXISTING** (scheduling/retry UNSPECIFIED) |
| Council decision | CouncilManager convenes | consensus per algorithm | decision event | consensus failure | Part 12 (collaboration); Part 6 §6.2 (CouncilManager); Part 0 §0.5.2 | **EXISTING** (algorithm UNSPECIFIED) |
| Memory/Knowledge op | MemoryManager (Part 1 M1) / StateManager (Part 4 §4.2) invoked | read/write scoped state | result event | storage failure (UNSPECIFIED recovery) | Part 0 §0.3.2; Part 1 §1.8.1 (M1); Part 4 §4.2 (StateManager) | **EXISTING** |
| Plugin/Integration call | owning manager invokes extension | extension-point handler | result event | extension failure (UNSPECIFIED) | Part 0 §0.5.2 | **EXISTING** (lifecycle UNSPECIFIED) |

No sequence details beyond event contracts and lifecycle are invented.

---

## 16. Agent Runtime

Cross-reference: Part 12 (Multi-Agent Collaboration), Part 6 (Capability Facade Services, including AIAgencyService), Part 1 §1.8.1 M6 (AgentManager). Note: Part 0 §0.5.2 references these facades as "Part 4.10 / Part 4.9 / Part 4.8 / Part 4.11", but in the actual Part 4 those section numbers belong to ResourceManager/HealthManager/CapabilityManager/ObservabilityManager; the facade managers are owned by Part 6 (and the extension-point contract is Part 0 §0.5.2). Source-backed:

- AgentManager (M6) is initialized Phase 6; agents are spawned/lifecycled/communicated through it (Part 1 §1.8.1).
- Custom AI Agency Agents subclass a base `AIAgent` and register via `AIAgencyService`; MUST emit audit `*Requested`/`*Completed` event pairs (Part 0 §0.5.2 extension-point contract; Part 6 facade services).
- Agents declare capabilities and health endpoints (AGT.MUST.1, Part 12 events.md §5).

**UNSPECIFIED** (not invented): agent invocation scheduling, internal execution loop, retry behavior, delegation mechanics beyond "via AgentManager", and termination timing. The architecture does not define agent-level retry or scheduling policy — these remain UNSPECIFIED.

| Aspect | Status | Source |
|--------|--------|--------|
| AgentManager init (Phase 6) | **EXISTING** | Part 1 §1.8.1 |
| Agent registration / audit event pairs | **EXISTING** | Part 0 §0.5.2; Part 6 |
| Agent capability/health declaration | **EXISTING** | Part 12 events.md §5; AGT.MUST.1 |
| Agent invocation scheduling | **UNSPECIFIED** | — |
| Agent retry/delegation internals | **UNSPECIFIED** | — |
| Agent termination timing | **UNSPECIFIED** | — |

---

## 17. Council Runtime

Cross-reference: Part 12 (collaboration), Part 6 §6.2 (CouncilManager). Source-backed:

- CouncilManager is a capability-manager facade; councils follow defined consensus protocols (CGN.MUST.1, Part 12 components.md §2).
- Custom Consensus Algorithm is an extension point (Part 0 §0.5.2): add to `ConsensusAlgorithm` enum, implement in CouncilManager; MUST satisfy liveness/safety properties (Part 0 §0.5.2; Part 6 §6.2). NOTE: Part 0 §0.5.2 labels this "Part 4.9" but Part 4 §4.9 is actually ResourceManager — CouncilManager is owned by Part 6.

**UNSPECIFIED** (not invented): council initialization sequence, member participation mechanics, decision/consensus execution internals, completion/failure handling beyond "follow consensus protocol". No consensus algorithm is specified by architecture (only the property requirements). CONFLICT-FACADE-01 notes CouncilManager is not enumerated in Part 1 §1.8.1's Core Manager set — preserved.

| Aspect | Status | Source |
|--------|--------|--------|
| Council consensus-protocol adherence | **EXISTING** | CGN.MUST.1; Part 12 |
| Consensus algorithm as extension point (liveness/safety) | **EXISTING** | Part 0 §0.5.2; Part 6 §6.2 |
| Council initialization / member participation | **UNSPECIFIED** | — |
| Consensus execution internals | **UNSPECIFIED** | — |

---

## 18. Workflow Runtime

Cross-reference: Part 7 §7.3–§7.4 (Workflow Definition/Instance), Part 4 §4.6 (WorkflowManager), Part 12 events.md §5.

Source-backed:
- Workflows defined as **immutable specifications** (WF.MUST.1, Part 7 §7.3.3).
- Instances track state transitions and emit events (WF.MUST.2, Part 12 events.md §5).
- WorkflowManager (M7) initializes Phase 7; orchestrates via events; supports checkpointing and compensation (Part 1 §1.8.1; Part 4 §4.6).
- State transitions validated/authorized via SecurityManager; authorization failure marks workflow failed and emits `WorkflowAuthorizationFailedEvent` (Part 4 §4.6).
- Forward recovery via replay from last checkpoint (Part 4 §4.6).
- Context propagated immutably along declared paths; boundary preservation enforced (context.md §9; Part 7 §7.7.3).

**UNSPECIFIED** (not invented): workflow scheduling/triggering mechanism, exact state machine enumeration for instances, concurrency model, and retry policy for steps. These are not defined by Parts 0–14.

| Aspect | Status | Source |
|--------|--------|--------|
| Immutable definition | **EXISTING** | WF.MUST.1; Part 7 §7.3.3 |
| Instance state tracking + events | **EXISTING** | WF.MUST.2; Part 12 events.md §5 |
| Checkpoint / compensation / replay | **EXISTING** | Part 4 §4.6 |
| Authorization-gated transitions | **EXISTING** | Part 4 §4.6; Part 4 §4.7 |
| Scheduling / step retry policy | **UNSPECIFIED** | — |

---

## 19. Event Runtime

Cross-reference: Part 2 (Event System), Part 1 §1.6 (Event-First Communication principle, #4) (Event-First). Source-backed:

- **Emission**: every event carries `event_id` (UUIDv7), `timestamp` (UTC ns), `timestampMonotonic` (monotonic), `correlationId`, `causationId`, `priority`, `trace` object (Part 2 §2.1; INV-EVT-002..005).
- **Routing/Ordering**: global, correlation, and priority ordering enforced by EventBus; higher priority dispatched first within a batch (no preemption of in-flight handlers) (Part 2 §2.7, §2.4.1).
- **Consumption**: subscribers handle events; `INV-EVT-004/005` require correlation/causation on every event.
- **Acknowledgement**: EventBus returns an acknowledgment on publication (Part 2 §2.4.2 publish model). Specific ack semantics/redelivery are not fully detailed.
- **Retries**: EventBus provides "retry, timeout, and recursive event detection" (Part 2 §2.4.1 failure handling) — retry *capability* EXISTING; policy parameters UNSPECIFIED.
- **Correlation/Causation**: required on every event; correlation_id tracks logical workflow; causation_id = causing event's event_id (Part 2 §2.1).

**Delivery guarantees — explicit**: EventBus implements **at-least-once (default)** and **at-most-once (configured)** semantics (Part 2 §2.8). These are EXISTING architectural guarantees. Dead letter queue, retry, timeout, recursive-event detection are part of EventBus failure handling (Part 2 §2.4.1).

| Aspect | Status | Source |
|--------|--------|--------|
| Envelope fields / correlation / causation | **EXISTING** | Part 2 §2.1; INV-EVT-002..005 |
| Priority/global/correlation ordering | **EXISTING** | Part 2 §2.7, §2.4.1 |
| Delivery: at-least-once / at-most-once | **EXISTING** | Part 2 §2.8 |
| DLQ / retry / timeout / recursion detect | **EXISTING** (capability) | Part 2 §2.4.1 |
| Ack/redelivery precise semantics | **UNSPECIFIED** | — |
| Retry policy parameters | **UNSPECIFIED** | — |

No delivery guarantee beyond at-least-once / at-most-once is invented; exactly-once is NOT claimed.

---

## 20. Memory and Knowledge Runtime

Cross-reference: Part 0 §0.3.2 (State Scopes), Part 4 §4.2 (StateManager), Part 1 §1.8.1 (MemoryManager M1), §4.7.3 (SecurityManager), implementation-contracts MEM.MUST.1/2. Note: MemoryManager has no dedicated Part 4 section; it is Part 1's Core Manager M1.

Source-backed:
- **MemoryManager (M1)** — episodic/semantic/working memory, context assembly, retention (Part 1 §1.8.1). MUST persist state using configured backends (MEM.MUST.1, DERIVED from Part 0 §0.5.2 + Part 1 M1).
- **StateManager (M2 in Part 4 / M1 in Part 1 — CONFLICT-CM-01)** — scoped state transitions (WORKFLOW/SERVICE/GLOBAL/SESSION, Part 0 §0.3.2); Global state MUST use StateManager (MEM.MUST.2, Part 0 §0.3.2 + Part 4 §4.2). Transitions validated and authorized (via SecurityManager), denied transitions emit `StateTransitionDeniedEvent` (Part 4 §4.2).
- **StorageManager (M4)** — persistence abstraction; schemas, migrations, transactions, backups (Part 1 §1.8.1). StorageManager defines namespaces, not backends (deployment.md §3.2 — backends UNSPECIFIED).
- **Retrieval/Storage**: interaction is event-driven (StateManager/MemoryManager invoked via events; authorization enforced).
- **Knowledge**: no separate "Knowledge" runtime subsystem is explicitly defined beyond memory/state; knowledge storage is an extension (custom memory backend, Part 0 §0.5.2).

**UNSPECIFIED** (not invented): concrete storage backends, memory backend discovery/lifecycle beyond the ABC interface (README §8), retention policy parameters, knowledge graph mechanics.

| Aspect | Status | Source |
|--------|--------|--------|
| Scoped state (StateManager) | **EXISTING** | Part 0 §0.3.2; Part 4 §4.2 |
| Memory persistence via backends | **EXISTING** (DERIVED) | MEM.MUST.1; Part 0 §0.5.2 |
| AuthZ-gated state transitions | **EXISTING** | Part 4 §4.2; Part 4 §4.7 |
| Storage backends | **UNSPECIFIED** | deployment.md §3.2 |
| Backend discovery/lifecycle | **UNSPECIFIED** | README §8 |

---

## 21. Plugin and Integration Runtime

Cross-reference: Part 0 §0.5.2 (extension points), README §8 (Extension Points Catalog). Source-backed extension points:

- Custom Event Types — subclass `Event`, new `EventType` enum value, register in catalog; MUST follow Part 2.1/2.2 (Part 0 §0.5.2).
- Custom Memory Backend — implement `MemoryBackend` ABC; register via MemoryManager (Part 0 §0.5.2).
- Custom Skill — implement `Skill` interface; register via SkillManager; MUST be sandboxed; MUST emit `SkillExecuted`/`SkillFailed` (Part 0 §0.5.2; Part 6 §6.3 SkillManager).
- Custom MCP Transport — implement `MCPTransport`; satisfy MCPManager contract (Part 0 §0.5.2; Part 6 §6.4 MCPManager).
- Custom Consensus Algorithm — add to enum; implement in CouncilManager (Part 0 §0.5.2; Part 6 §6.2).
- Custom AI Agency Agent — subclass `AIAgent`; register via AIAgencyService (Part 0 §0.5.2; Part 6 facade services).
- Custom Model Provider — register in ModelRouter; capability-based routing (Part 0 §0.5.2; Part 4 §4.8 CapabilityManager owns capability routing).
- Custom Resource Type — extend `ResourceType`; register in ResourceManager (Part 0 §0.5.2; Part 4 §4.9 ResourceManager).

> **Note on Part 0 cross-reference inconsistency:** Part 0 §0.5.2 labels the Skill/MCP/Consensus/Agency/ModelProvider/Resource extension points as "Part 4.8 / Part 4.9 / Part 4.10 / Part 4.11 / Part 4.12". In the actual Part 4, those section numbers are CapabilityManager (§4.8), ResourceManager (§4.9), HealthManager (§4.10), ObservabilityManager (§4.11), and Manager Interaction (§4.12). The facade managers (SkillManager, MCPManager, CouncilManager, AIAgencyService, ModelRouter) are predominantly owned by Part 6. This document cites the extension-point contract (Part 0 §0.5.2) plus the owning part (Part 6 for facades, Part 4 §4.8/§4.9 for capability/resource routing) rather than propagating the inaccurate §4.x mapping. CONFLICT-FACADE-01 preserves the underlying enumeration discrepancy.

**UNSPECIFIED** (not invented): discovery mechanism, loading order, initialization sequence, and shutdown sequence for plugins/integrations; sandboxing technology; manifest schema. CONFLICT-FACADE-01 notes SkillManager/CouncilManager/MCPManager are not in Part 1 §1.8.1's manager set — preserved.

| Aspect | Status | Source |
|--------|--------|--------|
| Extension-point definitions (8 points) | **EXISTING** | Part 0 §0.5.2; README §8 |
| Sandbox/audit emission for skills | **EXISTING** | Part 0 §0.5.2 |
| Plugin discovery/loading/init/shutdown lifecycle | **UNSPECIFIED** | — |
| Sandboxing technology / manifest schema | **UNSPECIFIED** | README §8 |

---

## 22. Runtime Boundaries

| Boundary | Entering Runtime State | Leaving Runtime State | Constraint | Source | Status |
|----------|------------------------|-----------------------|------------|--------|--------|
| Core Component ↔ Core Manager | post-init communication | — | EventBus-only; direct calls PROHIBITED | Part 1 §1.6 (Event-First Communication principle, #4); CC-IR-001 | **EXISTING** |
| Kernel ↔ external system | via extension points only | via extension points only | External systems interact ONLY through extension points (Part 0 §0.5.2) | Part 0 §0.5.2; INV-DEP-05 | **EXISTING** |
| Trust boundary | SecurityManager enforcement | SecurityManager enforcement | SecurityManager sole authority for authN/authZ/secrets/trust | Part 4 §4.7 | **EXISTING** |
| Workflow context boundary | context entry | context exit | Context SHALL NOT leak across workflow boundaries; scope enforced | Part 7 §7.7.3; context.md §9 | **EXISTING** |
| Process boundary | n/a (single deployable unit) | n/a | HermesKernel is sole deployable unit; cross-process topology UNSPECIFIED | deployment.md §3.1; GAP-DEP-01 | **EXISTING** (topology) / **GAP** (distributed) |
| Plugin/Integration boundary | extension point invocation | extension point completion | Only via declared extension points; non-extension points (Core Component/Manager interfaces) MUST NOT vary | Part 0 §0.5.2; INV-DEP-07 | **EXISTING** |

No process boundary or multi-process topology is invented. Distributed deployment remains GAP-DEP-01.

---

## 23. Shutdown Model

Source-backed (Part 1 §1.11). Shutdown is the **reverse** of initialization: Services → Core Managers → Core Components, phases N→0.

| Shutdown Step | Prerequisite | Requirement | Source | Status |
|---------------|--------------|-------------|--------|--------|
| Services shutdown (S9+) | RUNNING→SHUTTING_DOWN | Reverse dependency topology batches; drain events per batch | Part 1 §1.11.2; §1.11.3 | **EXISTING** |
| Core Managers shutdown (S8→S4) | Services done | Reverse phase order; M9 first among managers | Part 1 §1.11.2; INV-DEP-08 | **EXISTING** |
| Core Components shutdown (S3→S0) | Managers done | Reverse phase order; C4 first, EventBus last (S0) | Part 1 §1.11.2; INV-EB-LC-002 | **EXISTING** |
| Event draining | shutdown initiated | EventBus enters DRAINING; reject new publishes; process in-flight | Part 3 §3.3.2 | **EXISTING** |
| KernelTerminated | all entities shut down | Publish `KernelTerminated` with collected errors | Part 1 §1.11.3 | **EXISTING** |
| Shutdown MUST complete | individual failures | Best-effort; continue on per-entity failure; collect errors (INV-SD-001/003) | Part 1 §1.11.4 | **EXISTING** |

**UNSPECIFIED** (not invented): shutdown **timeout** behavior (GAP-DEP-03) and **forced** shutdown semantics (GAP-DEP-04). Checkpoint before CRITICAL/FATAL shutdown is required (INV-DEP-09, Part 4 §4.3) — EXISTING for that case. No shutdown ordering beyond the reverse-phase rule is invented.

---

## 24. Runtime Failure Model

Source-backed (Part 1 §1.12). Failure classes: TRANSIENT, DEGRADED, CRITICAL, FATAL.

| Failure | Detection | Required Behavior | Recovery | Source | Status |
|---------|-----------|-------------------|----------|--------|--------|
| Initialization failure (Core Component) | init throws | Abort; reverse-order shutdown of initialized; publish `KernelInitializationFailed`; throw | rollback (INV-INIT-001) | Part 1 §1.10.4 | **EXISTING** |
| Initialization failure (Core Manager) | init throws | Abort phase; reverse shutdown managers+components; publish failed | rollback | Part 1 §1.10.4 | **EXISTING** |
| Initialization failure (Service) | init throws | Mark FAILED; continue others; escalate if critical | per criticality | Part 1 §1.10.4 | **EXISTING** |
| Phase timeout | timeout | Treat as init failure; rollback | rollback | Part 1 §1.10.4 | **EXISTING** |
| Dependency failure (Service) | health check fail | Mark DEGRADED/FAILED; notify dependents | restart if CRITICAL non-critical | Part 1 §1.12.1; Part 3 §3.4.9 | **EXISTING** |
| Execution failure (TRANSIENT) | classification | Retry w/ exponential backoff (max 3); if persistent → DEGRADED | retry | Part 1 §1.12.1 | **EXISTING** |
| Execution failure (CRITICAL Core Manager) | classification | Re-init attempt (max 2); if fails → FATAL | restart→FATAL | Part 1 §1.12.3; INV-FH-002 | **EXISTING** |
| Execution failure (FATAL) | classification | Emergency shutdown (Services→Managers→Components); no re-init | shutdown | Part 1 §1.12.3; INV-FH-001 | **EXISTING** |
| Event failure | DLQ/retry/timeout | EventBus dead-letter/retry | EventBus-level | Part 2 §2.4.1 | **EXISTING** (params UNSPECIFIED) |
| Storage failure | backend error | UNSPECIFIED recovery | UNSPECIFIED | — | **UNSPECIFIED** |
| Plugin failure | extension error | UNSPECIFIED | UNSPECIFIED | — | **UNSPECIFIED** |
| Security failure | authN/authZ fail | Deny; emit `AuthenticationFailedEvent`/`StateTransitionDeniedEvent` | deny/isolate | Part 4 §4.7 | **EXISTING** |

---

## 25. Runtime Recovery

Source-backed (Part 1 §1.12.3). Recovery is defined per failure class; no strategy is invented beyond these.

| Failure Condition | Recovery Behavior | Trigger | Source | Status |
|-------------------|-------------------|---------|--------|--------|
| TRANSIENT | Automatic retry via LifecycleManager; no Service disruption | TRANSIENT classification | Part 1 §1.12.3 | **EXISTING** |
| DEGRADED | `ComponentDegraded` event → ObservabilityManager alert → manual/automated remediation | health degradation | Part 1 §1.12.3 | **EXISTING** |
| CRITICAL (Service) | `ComponentFailed` → ServiceRegistry FAILED → notify dependents → attempt restart | CRITICAL non-critical | Part 1 §1.12.3 | **EXISTING** |
| CRITICAL (Core Manager) | `CoreManagerFailed` → LifecycleManager re-init (max 2) → if fail FATAL | CRITICAL manager | Part 1 §1.12.3; INV-FH-002 | **EXISTING** |
| FATAL | Emergency shutdown (abbreviated); no re-initialization | FATAL classification | Part 1 §1.12.3; INV-FH-001 | **EXISTING** |
| Workflow failure | Forward recovery: replay EventBus log from last checkpoint | checkpoint gap | Part 4 §4.6 | **EXISTING** |
| Partial initialization | Full rollback; no entity remains initialized | init failure | INV-INIT-001 | **EXISTING** |
| State restoration | Checkpoint before CRITICAL/FATAL shutdown | shutdown trigger | INV-DEP-09; Part 4 §4.3 | **EXISTING** |
| Failure isolation | Recovery MUST NOT violate init phase ordering/dependency constraints (INV-FH-004) | any recovery | Part 1 §1.12.3 | **EXISTING** |
| Retry budget exhaustion | `RETRY_BUDGET_EXHAUSTED` event (Part 2 event catalog) | budget exhausted | Part 2 event catalog | **EXISTING** |

**UNSPECIFIED**: cross-process recovery, storage-backend recovery specifics, plugin recovery, and the distributed consistency of checkpoint/replay (depends on GAP-DEP-01 topology).

---

## 26. Runtime Invariants

Only source-backed or explicitly derived invariants are listed.

| ID | Invariant | Type | Source | Verification |
|----|-----------|------|--------|--------------|
| INV-LC-002 | Kernel MUST NOT go RUNNING→TERMINATED directly; SHUTTING_DOWN mandatory | EXISTING | Part 1 §1.9.1 | Phase-transition assertion |
| INV-LC-003 | Once TERMINATED, re-initialization PROHIBITED | EXISTING | Part 1 §1.9.1 | Instance-discard assertion |
| INV-CC-001 | Core Components initialize Phase 0→1→2→3; reverse for shutdown | EXISTING | Part 1 §1.7.3 | Init-order assertion |
| INV-CC-002 | EventBus MUST be operational before any other Core Component | EXISTING | Part 1 §1.7.3 | Phase-0 gate |
| INV-CC-003 | LifecycleManager (C4 per Part 1) last to init, first to shut down | EXISTING (C4 identity CONFLICT) | Part 1 §1.7.3 | Phase assertion |
| INV-EB-LC-001 | EventBus first to RUNNING | EXISTING | Part 3 §3.3.2 | EventBus state assertion |
| INV-EB-LC-002 | EventBus last to SHUTDOWN | EXISTING | Part 3 §3.3.2 | EventBus state assertion |
| INV-EVT-004 | Every event MUST carry correlation_id | EXISTING | Part 2 §2.1; context INV-CTX-1 | Envelope assertion |
| INV-EVT-005 | Every event MUST carry causation_id | EXISTING | Part 2 §2.1; context INV-CTX-2 | Envelope assertion |
| INV-INIT-001 | Partial initialization MUST be fully rolled back | EXISTING | Part 1 §1.10.4 | Rollback assertion |
| INV-INIT-002 | ConfigurationManager MUST be frozen before any Service initializes | EXISTING | Part 1 §1.10.2 | Freeze assertion |
| INV-CM-006 | Accessor access before RUNNING throws `KernelNotReadyError` | EXISTING | Part 1 §1.8.4 | Accessor guard |
| INV-FH-001 | Core Component failure ALWAYS FATAL | EXISTING | Part 1 §1.12.3 | Failure-class assertion |
| INV-FH-002 | Core Manager failure escalates to FATAL if re-init (max 2) fails | EXISTING | Part 1 §1.12.3 | Recovery assertion |
| INV-FH-003 | Service failure CRITICAL unless `critical:true` → FATAL | EXISTING | Part 1 §1.12.3 | Failure-class assertion |
| INV-FH-004 | Recovery MUST NOT violate init phase ordering/dependencies | EXISTING | Part 1 §1.12.3 | Recovery assertion |
| INV-DEP-08 | Shutdown follows reverse initialization order | EXISTING | Part 1 §1.11.2; Part 3 §3.7.4 | Shutdown-order assertion |
| INV-DEP-09 | Checkpoint state before CRITICAL/FATAL shutdown | EXISTING | Part 4 §4.3 | Checkpoint assertion |
| INV-DEP-11 | Once TERMINATED, re-initialization PROHIBITED | EXISTING | Part 1 §1.9.1 | Instance-discard assertion |
| INV-DEP-12 | Partial initialization always rolled back on failure | EXISTING | Part 1 §1.10.4; Part 3 §3.7.3 | Rollback assertion |
| INV-CTX-3..15 | Context immutability, explicit propagation, boundary preservation, trace completeness, etc. | EXISTING (DERIVED to runtime) | context.md §25 | Context assertion |
| INV-RT (derived) | All kernel-owned entities MUST participate in phased init/shutdown | DERIVED from Part 1 §1.6 (Explicit Lifecycle principle, #5) | Part 1 §1.6 | Lifecycle-participation assertion |

---

## 27. Runtime Ordering Constraints

| Constraint | Source | Explicit/Derived | Verification | Status |
|------------|--------|------------------|--------------|--------|
| Core Components init Phase 0→3 (Model A) | Part 1 §1.7.3 | EXPLICIT | Init sequence | **EXISTING** (Model A) |
| Core Managers init Phase 4→8 (sub-order within phase, Model A) | Part 1 §1.8.3 | EXPLICIT | Init sequence | **EXISTING** (Model A) |
| Services init Phase 9+ topological (Model A) | Part 1 §1.10.2 | EXPLICIT | Topological plan | **EXISTING** (Model A) |
| 5-phase init (Foundation→Observability, Model B) | Part 4 §4.2.3 | EXPLICIT | Init sequence | **EXISTING** (Model B) |
| ConfigurationManager frozen before Service init | Part 1 §1.10.2; Part 4 §4.1 §5.2 | EXPLICIT | Freeze assertion | **EXISTING** (both) |
| Shutdown reverse of init | Part 1 §1.11.2; Part 4 §4.3.6 | EXPLICIT | Shutdown sequence | **EXISTING** (both — invariant shared across models) |
| EventBus first RUNNING / last SHUTDOWN (Model A) | Part 3 §3.3.2 | EXPLICIT | EventBus state | **EXISTING** (Model A) |
| EventBus first initialized / sole substrate (Model B) | Part 4 §4.1 §5.2 | EXPLICIT | EventBus state | **EXISTING** (Model B) |
| No direct post-init calls between kernel entities | Part 1 §1.6 (Event-First Communication principle, #4); Part 4 §4.3.10 | EXPLICIT | CC-IR-001 enforcement | **EXISTING** (both) |
| Recovery preserves phase/dependency order | Part 1 §1.12.3; Part 4 §4.3.7 | EXPLICIT | INV-FH-004 / rollback idempotency | **EXISTING** (both) |
| Determinism of init/shutdown given identical config | Part 1 §1.6 (Deterministic Ordering principle, #8); Part 4 §4.3.5 | EXPLICIT | Reproducibility test | **EXISTING** (both) |

No ordering is invented. Where C4 identity is ambiguous (CONFLICT-CC-01) or the phase *model* diverges (CONFLICT-INIT-01), the ordering constraints are recorded per-model and preserved as CONFLICT; this section does not adjudicate between Model A and Model B.

---

## 28. Runtime State Model

Using source-backed terminology (Kernel FSM + Service lifecycle). States are NOT invented; they are quoted from Part 1 §1.9.1 and Part 3 §3.4.9. **The two authoritative kernel FSMs diverge** (see §6 conflict note and CONFLICT-INIT-01); both are reproduced below without resolution.

**Model A — Part 1 §1.9.1 (5-state):**

| State | Meaning | Entry | Exit | Source | Status |
|-------|---------|-------|------|--------|--------|
| UNINITIALIZED | Kernel constructed; no entities | Kernel ctor | `initialize()` | Part 1 §1.9.1 | **EXISTING** |
| INITIALIZING | Phased construction | `initialize()` | all initialized | Part 1 §1.9.1 | **EXISTING** |
| RUNNING | Steady operational | init complete; `KernelReady` | `shutdown()` | Part 1 §1.9.1 | **EXISTING** |
| SHUTTING_DOWN | Phased teardown; draining | `shutdown()` | all shut down | Part 1 §1.9.1 | **EXISTING** |
| TERMINATED | Terminal; no ops | SHUTTING_DOWN complete | (none) | Part 1 §1.9.1 | **EXISTING** |

**Model B — Part 4 §4.3.1 (8-state, via LifecycleManager):**

| State | Meaning | Entry | Exit | Source | Status |
|-------|---------|-------|------|--------|--------|
| UNINITIALIZED | Kernel process started; no managers | — | `initialize()` | Part 4 §4.3.1 | **EXISTING** (Model B) |
| INITIALIZING | Phase 1–5 execution | `initialize()` | `OPERATIONAL` / `ROLLBACK_IN_PROGRESS` / `TERMINATED` | Part 4 §4.3.1 | **EXISTING** (Model B) |
| OPERATIONAL | All managers healthy; serving requests | INITIALIZING complete | `DEGRADED` / `SHUTTING_DOWN` | Part 4 §4.3.1 | **EXISTING** (Model B) |
| DEGRADED | One+ managers unhealthy | OPERATIONAL / RECOVERY_IN_PROGRESS | OPERATIONAL / RECOVERY_IN_PROGRESS / SHUTTING_DOWN | Part 4 §4.3.1 | **EXISTING** (Model B) |
| ROLLBACK_IN_PROGRESS | Rolling back to prior checkpoint | init failure | UNINITIALIZED / TERMINATED | Part 4 §4.3.1 | **EXISTING** (Model B) |
| RECOVERY_IN_PROGRESS | Recovering from DEGRADED | DEGRADED | OPERATIONAL / DEGRADED / SHUTTING_DOWN | Part 4 §4.3.1 | **EXISTING** (Model B) |
| SHUTTING_DOWN | Phase 1–5 shutdown | OPERATIONAL / DEGRADED / RECOVERY_IN_PROGRESS | TERMINATED | Part 4 §4.3.1 | **EXISTING** (Model B) |
| TERMINATED | All managers shut down | SHUTTING_DOWN complete | (terminal) | Part 4 §4.3.1 | **EXISTING** (Model B) |

**Shared / per-Service states (both models):**

| State | Meaning | Source | Status |
|-------|---------|--------|--------|
| UNREGISTERED→REGISTERED→INITIALIZING→RUNNING→DEGRADED→FAILED→SHUTTING_DOWN→SHUTDOWN | Service lifecycle | Part 3 §3.4.9 | **EXISTING** |
| DRAINING (EventBus) | Reject new publishes; process in-flight | Part 3 §3.3.2 | **EXISTING** |

No additional kernel states (e.g., "PAUSED", "STANDBY") are asserted. The `RUNNING` (Model A) vs `OPERATIONAL` (Model B) steady-state naming, and the `DEGRADED`/`ROLLBACK_IN_PROGRESS`/`RECOVERY_IN_PROGRESS` states present only in Model B, constitute **CONFLICT-INIT-01** and are preserved, not resolved.

---

## 29. Runtime Unspecified Registry

Genuinely unspecified runtime concerns found during inspection.

| ID | Concern | Why Unspecified | Impact | Required Decision | Status |
|----|---------|-----------------|--------|-------------------|--------|
| RT-UNSP-01 | Cross-process / distributed initialization & runtime topology | deployment.md GAP-DEP-01 (Parts 0–14 silent) | Cannot define multi-node ordering | Implementation/ARB chooses single/multi/distributed | **UNSPECIFIED** |
| RT-UNSP-02 | Shutdown timeout behavior | GAP-DEP-03 | Bounded vs indefinite wait undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-03 | Forced shutdown semantics | GAP-DEP-04 | Behavior on forced kill undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-04 | Health aggregation algorithm | GAP-DEP-08 | System-level health undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-05 | Probe exposure mechanism | GAP-DEP-06 | Readiness/liveness probe tech undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-06 | Configuration validation rules (type/required/range/cross-field) | configuration.md §11 | Validation logic undefined | Implementation decision (GAP-DEP-05) | **UNSPECIFIED** |
| RT-UNSP-07 | Configuration reload behavior | configuration.md §12 | Hot/warm reload undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-08 | Storage backend specifics & recovery | deployment.md §3.2; §24 storage | Persistence impl undefined | Implementation decision (extension point) | **UNSPECIFIED** |
| RT-UNSP-09 | Plugin/integration discovery, loading, init/shutdown lifecycle | README §8 (beyond ABC) | Plugin runtime undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-10 | Agent scheduling / retry / delegation internals | Parts 0–14 silent | Agent runtime undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-11 | Council initialization / member participation / consensus internals | Parts 0–14 silent beyond protocol adherence | Council runtime undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-12 | Workflow scheduling / step retry policy / instance state machine enumeration | Parts 0–14 silent | Workflow runtime undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-13 | Event ack/redelivery precise semantics & retry policy params | Part 2 §2.4.1 capability only | Delivery internals undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-14 | Context deletion/discard, persistence, serialization, GC | context.md §8 (UNSPECIFIED) | Context lifecycle incomplete | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-15 | Observability metric schema & backends; trace backend; audit WORM (Draft) | observability.md §5 | Telemetry impl undefined | Implementation decision | **UNSPECIFIED** |
| RT-UNSP-16 | Execution-context ↔ workflow-context ↔ trace-context mapping | context.md §7 (UNSPECIFIED) | Context correlation undefined | Implementation decision | **UNSPECIFIED** |

---

## 30. Runtime Gap Registry

| Gap ID | Gap | Source | Impact | Resolution Needed | Status |
|--------|-----|--------|--------|-------------------|--------|
| GAP-P15-05 | `runtime-map.md` was empty; now authored (this document) | README §14; deployment GAP-DEP-09 | Runtime dependency verification blocked | Author runtime-map.md (done this pass) | **EXISTING** (resolved by this authorship) — runtime verification now CONDITIONALLY READY |
| GAP-DEP-09 | Runtime dependency verification blocked by empty runtime-map.md | deployment.md §22 | Runtime deps UNVERIFIED | Author runtime-map.md | **EXISTING** (resolved by this document) |
| GAP-DEP-01 | Distributed deployment topology not defined | deployment.md §20 | Runtime ordering across nodes undefined | Implementation/ARB decision | **GAP** (open) |
| GAP-DEP-03 | Shutdown timeout behavior not defined | deployment.md §20 | Shutdown completion undefined | Implementation decision | **GAP** (open) |
| GAP-DEP-04 | Forced shutdown behavior not defined | deployment.md §20 | Forced-kill semantics undefined | Implementation decision | **GAP** (open) |
| GAP-DEP-05 | Configuration validation rules not defined | deployment.md §20; configuration.md §11 | Validation logic undefined | Implementation decision | **GAP** (open) |
| GAP-DEP-06 | Probe exposure mechanism not defined | deployment.md §20 | Readiness probe tech undefined | Implementation decision | **GAP** (open) |
| GAP-DEP-08 | Health aggregation algorithm not defined | deployment.md §20 | System health undefined | Implementation decision | **GAP** (open) |

Gaps are recorded, not filled with invention. Two former Part 15 gaps (GAP-P15-05, GAP-DEP-09) are now closed by this document's authorship and are recorded as EXISTING; the remaining GAP-DEP-* entries stay open and are owned by deployment/implementation decisions.

---

## 31. Runtime Conflict Registry

Conflicts preserved from authoritative sources (not resolved here).

| Conflict ID | Concern | Source A | Source B | Difference | Impact | Status |
|-------------|---------|----------|----------|------------|--------|--------|
| CONFLICT-CC-01 | Identity of Core Component C4 | Part 1 §1.7.1: C4 = **LifecycleManager** (`kernel.lifecycle`) | Part 3 §3.2.1: C4 = **StructuredLogger** (`kernel.logger`) | Part 1 and Part 3 name different 4th Core Component; Part 4 names C4=IdentityProvider, Part 0 names C4=ResourceManager. Only EventBus (C1) identical across all. | Initialization order row for "C4" and lifecycle ownership depend on which is authoritative. | **CONFLICT — UNRESOLVED (ARB)** |
| CONFLICT-CM-01 | Identity of Core Managers M1–M9 | Part 1 §1.8.1: M1=MemoryManager…M9=ObservabilityManager | Part 4 §4.2.1: M2=StateManager, M5=SecurityManager, etc. (different mapping) | 9 manager slots share IDs but differ in identity; Part 0 uses "Capability Managers" with different set. | Runtime init Phase 4–8 assignment ambiguous for affected slots. | **CONFLICT — UNRESOLVED (ARB)** |
| CONFLICT-FACADE-01 | Manager enumeration | Part 6 references SkillManager/CouncilManager/MCPManager as delegation targets | Not enumerated in Part 1 §1.8.1 nor Part 4 §4.2.1; Part 0 lists as Capability Managers | Plugin/integration runtime owners ambiguous. | Plugin runtime ownership (§21) partially unspecified. | **CONFLICT — UNRESOLVED (ARB)** |
| CONFLICT-P15-01 | Part 15 classification (roadmap vs TOC) | MASTER_ARCHITECTURE_ROADMAP.md §4: 13 chapters | ARCHITECTURE_SPEC_TOC.md §15: 7 appendices | Structural content model for Part 15 differs. | `runtime-map.md` position (chapter vs appendix) ambiguous. | **CONFLICT — UNRESOLVED (ARB)** (recorded in README §13) |
| CONFLICT-INIT-01 | Initialization phase model & kernel state machine | Part 1 §1.10.2 / §1.9.1: **9-phase** model (Phase 0–8 + 9+ Services), `RUNNING` steady state, 5-state FSM; within-phase deterministic sub-order M1→M2 etc. | Part 4 §4.2.3 / §4.3.1 / §4.1 §5.2: **5-phase** model (Phases 1–5), `OPERATIONAL` steady state, 8-state FSM (incl. `DEGRADED`, `ROLLBACK_IN_PROGRESS`, `RECOVERY_IN_PROGRESS`), alphabetical within-phase ordering | Phase count (9 vs 5), phase boundaries, kernel steady-state vocabulary (`RUNNING` vs `OPERATIONAL`), within-phase sub-order, and C4/LifecycleManager placement (Phase 3 vs Phase 1) all diverge between the two authoritative sources. Part 1 §1.7.3 / §1.8.3 are consistent with the 9-phase model; Part 4 §4.2.3 / §4.3 with the 5-phase model. | **Every** runtime initialization-ordering and kernel-state assertion in this document is affected: this runtime-map presents both (§6, §7.A/§7.B/§7.C) and does NOT resolve which model is authoritative. Both are preserved. | **CONFLICT — UNRESOLVED (ARB)** (preserved in deployment.md §279, dependency-map.md §8.1/§889, context.md §403) |

No runtime-specific conflict beyond the above was invented. The C4 and Core Manager identity conflicts (CONFLICT-CC-01, CONFLICT-CM-01) and the initialization-phase-model conflict (CONFLICT-INIT-01) directly affect runtime initialization ordering rows and are preserved as CONFLICT.

---

## 32. Runtime Implementation Contracts

Cross-reference: implementation-contracts.md §10 (Runtime Contracts). That section was marked "SOURCE VERIFICATION REQUIRED / MISSING SOURCE" while runtime-map.md was empty. With this document authored and traceable to Part 1/Part 3, the source now exists.

| Runtime Requirement | Contract ID | Verification | Source | Status |
|---------------------|-------------|--------------|--------|--------|
| Startup MUST initialize core entities in mandated phased order | RT.MUST.1 | Init-sequence assertion | Part 1 §1.10.2; §1.7.3; §1.8.3 | **EXISTING** (was MISSING SOURCE; now source-backed by this map → Part 1) |
| EventBus MUST be sole inter-component communication substrate | CMP.MUST.1 | Isolation/communication test | Part 0 Principle 1; Part 2 §2.1 | **EXISTING** (pre-existing) |
| SecurityManager MUST enforce authN/authZ/secret handling | CMP.MUST.2 | Security test | Part 4 §4.7; Part 14 §14.10 | **EXISTING** (pre-existing) |
| ConfigurationManager MUST use four-layer merge | CMP.MUST.5 | Config-merge test | Part 0 §0.4 Principle 10; Part 3 §3.5 | **EXISTING** (pre-existing) |
| Context propagation MUST be immutable and auditable | CTX.MUST.1 | Context test | Part 7 Principle 5; Part 12 events.md | **DERIVED** (pre-existing) |
| Workflows MUST be immutable specifications | WF.MUST.1 | Workflow test | Part 7 §7.3.3 | **EXISTING** (pre-existing) |
| Workflow instances MUST track state transitions | WF.MUST.2 | Workflow-event test | Part 12 events.md §5 | **EXISTING** (pre-existing) |

No contract IDs are invented. RT.MUST.1 is the existing ID from implementation-contracts.md §10; its source status is upgraded from MISSING SOURCE to EXISTING (source-backed) via this document's traceability. All other IDs are pre-existing in implementation-contracts.md.

---

## 33. Runtime Verification

Defines eventual verification requirements. No test *specifications/implementations* are claimed to exist; `testing.md` is a populated testing-architecture document but its concrete test specs remain pending (GAP-P15-06), so conformance tests cannot yet be cited. Verification **methods** are described; evidence is "to be produced."

| Requirement | Verification Method | Evidence | Source | Status |
|-------------|---------------------|----------|--------|--------|
| Startup phase order | Init-sequence assertion (phases 0→8 then 9+) | Kernel init logs / phase assertions | Part 1 §1.7.3, §1.8.3, §1.10.2 | **NOT VERIFIED** (no test specs; GAP-P15-06) |
| Initialization order correctness | Topological plan replay | ServiceRegistry plan dump | Part 1 §1.10.2 | **NOT VERIFIED** |
| Dependencies (EventBus-first) | Communication-path test (no direct calls) | Static analysis / runtime probe | Part 1 §1.6 (Event-First Communication principle, #4); CC-IR-001 | **NOT VERIFIED** |
| Readiness (KernelReady before work) | Accessor-guard test (throws before RUNNING) | INV-CM-006 assertion | Part 1 §1.8.4 | **NOT VERIFIED** |
| Runtime state transitions | FSM assertion (no skip of SHUTTING_DOWN) | State-log analysis | Part 1 §1.9.1; INV-LC-002 | **NOT VERIFIED** |
| Context (correlation/causation on events) | Envelope assertion on sampled events | Event log scan | Part 2 §2.1; INV-EVT-004/005 | **NOT VERIFIED** |
| Workflows (immutable def, state tracking) | Workflow contract tests | WF.MUST.1/2 tests | Part 7 §7.3.3; Part 12 events.md §5 | **NOT VERIFIED** |
| Agents (capability/health declaration) | Agent contract test | AGT.MUST.1 test | Part 12 events.md §5 | **NOT VERIFIED** |
| Events (delivery guarantees) | Delivery-semantics test (at-least-once) | EventBus test harness | Part 2 §2.8 | **NOT VERIFIED** |
| Memory (scoped state, authZ gating) | State-transition authZ test | MEM.MUST.2 / Part 4 §4.2 test | Part 0 §0.3.2; Part 4 §4.2 | **NOT VERIFIED** |
| Plugins (extension-point only) | Boundary test (no non-extension mutation) | INV-DEP-07 test | Part 0 §0.5.2 | **NOT VERIFIED** |
| Shutdown (reverse order, drain) | Shutdown-sequence assertion | Shutdown logs | Part 1 §1.11.2; INV-DEP-08 | **NOT VERIFIED** |
| Failure (classification + recovery) | Failure-injection test | INV-FH-001..004 assertions | Part 1 §1.12 | **NOT VERIFIED** |
| Recovery (rollback, restart, checkpoint) | Recovery-injection test | INV-INIT-001, INV-DEP-09 | Part 1 §1.10.4, §1.12.3, Part 4 §4.3 | **NOT VERIFIED** |

All verification rows are **NOT VERIFIED** because no conformance test specifications/implementations exist yet (`testing.md` is a populated testing-architecture document but its test specs are pending, GAP-P15-06). No test results are claimed.

---

## 34. Runtime Traceability Matrix

Every normative runtime requirement traces to source and Part 15 section.

| Runtime Requirement | Source | Part 15 Section | Contract | Verification | Status |
|----------------------|--------|-----------------|----------|--------------|--------|
| Phased Core Component init (0→3) | Part 1 §1.7.3 | §7, §26, §27 | RT.MUST.1 | §33 | **EXISTING** |
| Phased Core Manager init (4→8) | Part 1 §1.8.3 | §7, §26, §27 | RT.MUST.1 | §33 | **EXISTING** |
| Service topological init (9+) | Part 1 §1.10.2 | §7, §27 | RT.MUST.1 | §33 | **EXISTING** |
| Config freeze before Service init | Part 1 §1.10.2 | §10, §12, §26 | CMP.MUST.5 | §33 | **EXISTING** |
| EventBus sole substrate | Part 0 P1; Part 2 §2.1 | §4, §8, §22, §26 | CMP.MUST.1 | §33 | **EXISTING** |
| Kernel FSM (5 states) | Part 1 §1.9.1 | §5, §6, §9, §28 | — | §33 | **EXISTING** |
| No direct post-init calls | Part 1 §1.6 (Event-First Communication principle, #4) | §8, §22, §27 | CMP.MUST.1 | §33 | **EXISTING** |
| Shutdown reverse order + drain | Part 1 §1.11.2; Part 3 §3.3.2 | §23, §26, §27 | — | §33 | **EXISTING** |
| Failure classification + recovery | Part 1 §1.12 | §24, §25, §26 | — | §33 | **EXISTING** |
| Event envelope (corr/causation) | Part 2 §2.1 | §11, §19, §26 | CTX.MUST.1 | §33 | **EXISTING** |
| Delivery guarantees (ALO/AMO) | Part 2 §2.8 | §19 | — | §33 | **EXISTING** |
| Context immutability/propagation | Part 7 Principle 5; §7.7.3 | §11, §26 | CTX.MUST.1 | §33 | **EXISTING** |
| Workflow immutable + tracked | Part 7 §7.3.3; Part 12 | §18, §26 | WF.MUST.1/2 | §33 | **EXISTING** |
| Security enforcement (M8) | Part 4 §4.7 | §13, §22, §26 | CMP.MUST.2 | §33 | **EXISTING** |
| Extension points (8) | Part 0 §0.5.2 | §21 | — | §33 | **EXISTING** |
| C4 identity ambiguity | Part 1 §1.7.1 vs Part 3 §3.2.1 | §4, §5, §7, §31 | — | §33 | **CONFLICT** |
| Core Manager identity ambiguity | Part 1 §1.8.1 vs Part 4 §4.2.1 | §5, §7, §31 | — | §33 | **CONFLICT** |
| Init phase-model ambiguity | Part 1 §1.10.2 (9-phase) vs Part 4 §4.2.3 / §4.1 §5.2 (5-phase) | §6, §7, §27, §28, §31 | — | §33 | **CONFLICT** (CONFLICT-INIT-01) |
| Distributed topology | deployment GAP-DEP-01 | §3.2, §22, §29 | — | §33 | **UNSPECIFIED** |

---

## 35. AI Coding Agent Rules

AI agents modifying runtime-related implementation MUST:

1. Inspect authoritative architecture (Parts 0–14) before modifying runtime behavior.
2. Treat Parts 0–14 as architectural authority; treat Part 15 files (including this one) as supporting references only.
3. Treat `runtime-map.md` (this document) as a runtime interpretation layer, not a source of architecture.
4. Never invent lifecycle states — use the Kernel FSM from Part 1 §1.9.1 (and Part 4 §4.3.1, preserved as CONFLICT-INIT-01); do not add RECOVERING/PAUSED/DEGRADED/FAILED/STARTING/STOPPING as kernel states unless an authoritative source establishes them.
5. Never invent initialization ordering — use Part 1 §1.7.3 / §1.8.3 / §1.10.2 (Model A) or Part 4 §4.2.3 (Model B, preserved as CONFLICT-INIT-01).
6. Never invent runtime dependencies — distinguish architectural dependency from initialization order (§8); do not infer startup order from dependency alone.
7. Never invent retry/timeouts — use only Part 1 §1.12.3 / Part 2 §2.4.1 retry/timeout *capabilities*; policy parameters remain UNSPECIFIED.
8. Never invent concurrency — no worker pool, thread model, or parallelism is established by Parts 0–14 unless explicitly stated.
9. Never invent scheduling — no agent/workflow/council/service scheduling algorithm is specified; such mechanics remain UNSPECIFIED (§16/§17/§18, RT-UNSP-10..12).
10. Never invent deployment infrastructure — no container, orchestrator, process supervisor, or cloud topology is selected by Parts 0–14 (§3.2).
11. Preserve EventBus-first communication where architecturally required (Part 0 Principle 1; Part 1 §1.6 principle #4; CC-IR-001/002) — distinguish direct internal calls from inter-component architectural communication.
12. Preserve configuration freeze behavior where required (ConfigurationManager frozen before Service init, INV-INIT-002/INV-CM-006); do not invent hot reload.
13. Preserve security boundaries (SecurityManager M8 sole authority, Part 4 §4.7) — keep architectural requirement separate from implementation mechanism.
14. Preserve observability requirements (structured logging with correlation_id, Part 0 §0.4 Principle 12; envelope trace, Part 2 §2.1) — no telemetry backend invented.
15. Preserve UNSPECIFIED (§29), GAP (§30), and CONFLICT (§31) classifications — do not implement silence as if specified and do not fill gaps with invention.
16. Do not silently resolve architectural conflicts (CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-FACADE-01, CONFLICT-P15-01, CONFLICT-INIT-01) — preserve and escalate to ARB.
17. Stop and request architectural clarification when implementation requires an undefined decision not established by authoritative sources.

**Explicitly:** Editing `runtime-map.md` documentation is NOT equivalent to modifying architecture. This document is the bridge, not the source of truth. Parts 0–14 remain authoritative. Other Part 15 files (`dependency-map.md`, `components.md`, `context.md`, `configuration.md`, `implementation-contracts.md`, etc.) may be consulted for navigation/terminology but never override Parts 0–14.

---

## 36. Cross-Document Consistency

Checked against the listed Part 15 files (not modified). Findings:

| Document | Consistency Check | Result | Note |
|----------|-------------------|--------|------|
| README.md | References `runtime-map.md` as "Runtime initialization order, singleton accessor catalog" (§4, §9). This document delivers initialization order + entity/accessor catalog. | CONSISTENT | GAP-P15-05 now resolved by this authorship. |
| glossary.md | Terminology (Runtime, Context, Lifecycle, EventBus, etc.) matches glossary §10/§29. | CONSISTENT | C4 identity conflict noted in glossary terminology conflicts. |
| adrs.md | No Part 15-native formal ADR exists (adrs.md §7/§8 audit). No ADR cited as formal here. | CONSISTENT | No fake ADR IDs used. |
| components.md | Component lifecycle (§13) aligns with §9 here; conflict set (CONFLICT-ES-01 etc.) preserved. | CONSISTENT | C4/CM conflicts cross-referenced. |
| configuration.md | Four-layer merge, freeze, validation UNSPECIFIED align with §12. | CONSISTENT | |
| context.md | Context lifecycle/propagation (§8/§9) aligns with §11; UNSPECIFIED items preserved. | CONSISTENT | |
| dependency-map.md | Dependency types & CONFLICT-CC-01/CM-01/FACADE-01 preserved; runtime-ordered deps now sourced; CONFLICT-INIT-01 aligned. | CONSISTENT | GAP-DEP-09 resolved. |
| deployment.md | Single deployable unit (§3.1) aligns with §3/§4; GAP-DEP-01..08 preserved; CONFLICT-INIT-01 aligned (deployment §279/§954). | CONSISTENT | |
| observability.md | M9 Phase 8, StructuredLogger, UNSPECIFIED backends align with §14. | CONSISTENT | |
| implementation-contracts.md | RT.MUST.1 source now provided; no new IDs invented. | CONSISTENT | |
| review-checklist.md | Final Gate references runtime-map.md; this document supplies it. | CONSISTENT | |

No inconsistency requiring a new CONFLICT was introduced. Existing conflicts are preserved, not resolved.

---

## 37. Final Runtime Architecture Audit

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Authority | PASS | All normative claims trace to Parts 0–14 (predominantly Part 1/2/3/4/7/12) or existing Part 15 contracts |
| Scope | PASS | In-scope per §3.1; out-of-scope tech excluded per §3.2 |
| Runtime model | PASS | §4 entities/concepts sourced to Part 1/3/deployment |
| Runtime entities | PASS | §5 table; runnable vs capability distinguished |
| Runtime phases | PASS | §6 from Part 1 §1.9.1 / §1.10; dual phase models (§7) preserved as CONFLICT-INIT-01 |
| Startup | PASS | §6/§7 from Part 1 §1.10 |
| Initialization order | PASS | §7 explicit from Part 1 §1.7.3/§1.8.3/§1.10.2; Model A/B divergence preserved as CONFLICT-INIT-01 (§31) |
| Dependencies | PASS | §8 cross-ref dependency-map.md; types distinguished |
| Component lifecycle | PASS | §9 from Part 1/3; UNSPECIFIED marked |
| Readiness | PASS | §10 distinguishes initialized/RUNNING/operational |
| Context | PASS | §11 references context.md; no duplication |
| Configuration | PASS | §12 references configuration.md; no fail-fast invented |
| Security | PASS | §13 references Part 4 §4.7; no startup order invented |
| Observability | PASS | §14 references observability.md; no infra invented |
| Operational execution | PASS | §15 event-driven; no sequence invented |
| Agents | PASS | §16; internals UNSPECIFIED |
| Councils | PASS | §17; consensus internals UNSPECIFIED |
| Workflows | PASS | §18; scheduling UNSPECIFIED |
| Events | PASS | §19; delivery guarantees per Part 2 §2.8 |
| Memory/Knowledge | PASS | §20; backends UNSPECIFIED |
| Plugins | PASS | §21; lifecycle UNSPECIFIED |
| Boundaries | PASS | §22; no process topology invented |
| Shutdown | PASS | §23 reverse-phase; timeout/forced UNSPECIFIED |
| Failure | PASS | §24 from Part 1 §1.12 |
| Recovery | PASS | §25 from Part 1 §1.12.3 |
| Runtime state | PASS | §28 from Part 1 §1.9.1 / Part 3 §3.4.9 |
| Invariants | PASS | §26 source-backed/derived only |
| Contracts | PASS | §32 references implementation-contracts.md; RT.MUST.1 upgraded with existing ID |
| Verification | NOT VERIFIED | §33 — no test specs/implementations exist (`testing.md` populated as testing architecture but specs pending, GAP-P15-06) |
| Traceability | PASS | §34 matrix complete |
| Anti-invention | PASS | No startup/shutdown/lifecycle/readiness/retry/recovery/delivery/process/infra invented; no fake ADR/contract IDs; conflicts preserved |

Overall: structurally complete and source-faithful. Verification is NOT VERIFIED only because conformance tests do not yet exist.

---

## 38. Runtime Architecture Readiness

Three distinct readiness dimensions:

- **Runtime Documentation Readiness:** **CONDITIONALLY READY** — this document is now authored, source-backed, and cross-references all required Part 15 files. It resolves GAP-P15-05 and deployment GAP-DEP-09. It does NOT resolve CONFLICT-CC-01 / CONFLICT-CM-01 / CONFLICT-FACADE-01 / CONFLICT-INIT-01 (ARB-pending) nor the open GAP-DEP-01..08.
- **Runtime Implementation Readiness:** **NOT EVALUATED** — implementation artifacts are outside this document's scope; governed by implementation-contracts.md and testing.md (populated testing-architecture document, test specs pending, GAP-P15-06).
- **Runtime Conformance Readiness:** **NOT READY** — no conformance test specifications/implementations exist yet (`testing.md` populated as testing architecture but its test specs pending, GAP-P15-06); all §33 verification rows are NOT VERIFIED.

An architecture document can be structurally complete while some implementation details remain UNSPECIFIED. This document treats every UNSPECIFIED item as a recorded gap/unspecified concern (§29/§30), not a documentation failure. The Part 15 Final Gate (README §20) remains NOT READY because several Part 15 chapters are still pending authorship and `testing.md` — though populated as a testing-architecture document — has no test specifications yet (GAP-P15-06); this document's authorship does not by itself flip that gate.

---

## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-PART15-RUNTIME-MAP |
| **Version** | 1.0.0 |
| **Status** | **CONDITIONALLY READY** — Source-backed architecture-level runtime model; conflicts preserved; runtime conformance NOT VERIFIED (no test specs yet, GAP-P15-06). |
| **Date** | 2026-08-14 |
| **Classification** | Informative — Architecture-level runtime model (bridge, not source of truth) |
| **Author** | Architecture Evolution & Extensibility Documentation (Part 15) |
| **Distribution** | All AI-OS engineers, architects, reviewers, AI agents |
| **Related Documents** | Parts 0–14; all `part15/` documents listed in §36 |

*Authority remains with Parts 0–14. This document maps architecture to runtime behavior; it does not create architecture. Editing this document is not equivalent to modifying architecture. See §35 (AI Coding Agent Rules) and §31 (Conflict Registry) before any runtime change.*
