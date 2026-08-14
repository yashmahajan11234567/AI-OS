# AI-OS Part 15 — Deployment Architecture

## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-PART15-DEPLOYMENT |
| **Version** | 1.0.0 |
| **Status** | **CONDITIONALLY READY** — Deployment architecture is specified from Parts 0–14 with all gaps and open decisions recorded. Ready for implementation use under the recorded gaps. Becomes fully READY when GAP-DEP-01 through GAP-DEP-11 and IMPLEMENTATION DECISION REQUIRED items are resolved by implementation or ARB. |
| **Date** | 2026-08-14 |
| **Classification** | Normative — Deployment architecture specification |
| **Author** | Part 15 Implementation Architecture Documentation |
| **Distribution** | All AI-OS engineers, operators, reviewers, AI coding agents |
| **Related Documents** | `README.md`, `glossary.md`, `components.md`, `dependency-map.md`, `configuration.md`, `observability.md`, `implementation-contracts.md`, `adrs.md`, `runtime-map.md` (EMPTY), `testing.md` (EMPTY); Parts 0–14 |

---

## 1. Purpose and Authority Boundary

### 1.1 Purpose

This document establishes the **architecture-level deployment model** for AI-OS. It defines what must be true for a deployment to be conformant: what constitutes a deployable unit, what each unit depends on, how configuration is supplied, how the system initializes and shuts down, what must be satisfied before a deployment is valid, how failures are classified and recovered, and what the architecture leaves open for implementation.

This document describes **deployment architecture requirements** only where supported by Parts 0–14 or accepted ADRs. Where the architecture is silent, this document records the gap as UNSPECIFIED, GAP, or IMPLEMENTATION DECISION REQUIRED. It does not fill gaps with invented infrastructure.

### 1.2 What This Document Is NOT

This document is NOT:

- A Docker specification
- A Kubernetes specification
- A cloud architecture reference
- A CI/CD specification
- An infrastructure-as-code specification
- A deployment runbook or script

This document does not prescribe packaging, orchestration, containerization, cloud providers, CI/CD tools, monitoring backends, logging backends, secret management products, load balancers, API gateways, service meshes, ingress controllers, or any specific deployment technology. Those are implementation choices.

### 1.3 Authority Boundary

The authority chain for deployment decisions is:

```
Parts 0–14 (authoritative)
    ↓
Architectural decision or constraint
    ↓
This document (indexes and interprets)
    ↓
Implementation contract
    ↓
Implementation decision
```

Parts 0–14 are authoritative. This document indexes and interprets; it does not override. When this document disagrees with its source:

- **Source document wins**
- The disagreement MUST be recorded

**This document cannot invent deployment infrastructure, packaging technology, orchestration platforms, CI/CD pipelines, cloud providers, or networking topologies unless explicitly required by Parts 0–14 or accepted ADRs.**

### 1.4 How to Use This Document

- **Developers** should use this document to understand what must be deployed, in what order, and what the architecture requires before any component can become operational.
- **AI coding agents** must inspect this document and the cited source Parts before modifying deployment-related code; see §22.
- **Reviewers** should use this document to verify that a proposed deployment satisfies all architectural requirements.
- **Operators** should use this document to understand dependency ordering, failure behavior, and recovery procedures.

---

## 2. Deployment Authority and Non-Governed Areas

### 2.1 Authority Boundary

Parts 0–14 are authoritative for all architectural decisions. This document is authoritative for deployment architecture only where Parts 0–14 establish constraints. Where Parts 0–14 are silent, this document records the gap and does not invent a value.

### 2.2 Non-Governed Technology

The following technology areas are **NOT governed** by this document unless Parts 0–14 explicitly require them. All are UNSPECIFIED:

| Area | Status | Reason |
|------|--------|--------|
| Containerization (Docker, Podman, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Orchestration (Kubernetes, Nomad, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Cloud providers (AWS, Azure, GCP, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| CI/CD platforms (Jenkins, GitHub Actions, ArgoCD, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Infrastructure as Code (Terraform, Pulumi, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Service mesh (Istio, Linkerd, etc.) | UNSPECIFIED | Not mentioned in Parts 0–14 |
| API gateways, ingress controllers | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Load balancers | UNSPECIFIED | Not mentioned in Parts 0–14 |
| Specific storage backends (databases, S3, etc.) | UNSPECIFIED | StorageManager defines namespaces, not backends |
| Secret management platforms (Vault, etc.) | UNSPECIFIED | SecurityManager defines behavior, not products |
| Identity providers (Okta, Auth0, etc.) | UNSPECIFIED | SecurityManager defines methods, not providers |
| HSM products | UNSPECIFIED | SecurityManager defines requirements, not products |
| Monitoring backends (Prometheus, Datadog, etc.) | UNSPECIFIED | Observability requirements exist; backends do not |
| Logging backends | UNSPECIFIED | Logging requirements exist; backends do not |

### 2.3 Deployment Decision Classification

| Classification | Meaning |
|----------------|---------|
| **EXISTING** | Directly stated in Parts 0–14 or accepted ADRs |
| **DERIVED** | Logically implied by EXISTING statements; inference path stated |
| **UNSPECIFIED** | Parts 0–14 and accepted ADRs are silent; this document does not invent |
| **GAP** | Parts 0–14 partially define but leave required fields unspecified for integration use |
| **PROPOSED** | Recommendation for implementation; not architecture fact |
| **FUTURE** | Explicitly deferred in source Parts to a named future horizon |
| **CONFLICT** | Two or more authoritative sources disagree on this point |
| **IMPLEMENTATION DECISION REQUIRED** | Architecture identifies a choice that must be made during implementation; architecture does not prescribe which option to select |

---

## 3. Deployment Unit Model

### 3.1 Deployable Unit Definition

**Status:** EXISTING

**Decision:** HermesKernel is the single deployable unit of the AI-OS system.

**Source:** Part 3 §3.1; Part 1 §1.1

**Statement:** All Core Components, Core Managers, Engineering Services, and Capability Facade Services are deployed together within the HermesKernel process. There are no independently deployable subsystems at the architecture level.

### 3.2 What Is Not a Deployable Unit

**Status:** EXISTING / DERIVED

The following assumptions are explicitly prohibited:

- **component ≠ process**: A Core Component or Core Manager is an architectural component, not a process or deployment target.
- **service ≠ container**: A Service (Engineering or Facade) is a registered runtime entity within the kernel, not a containerized unit.
- **manager ≠ deployment unit**: A Core Manager is a capability domain within the kernel, not an independently deployable artifact.

**Source:** Part 1 §1.6.1; Part 3 §3.2; DERIVED from component lifecycle ownership model

### 3.3 Component-to-Deployment Mapping

**Status:** DERIVED

| Component Category | Architectural Role | Deployment Mapping |
|--------------------|-------------------|-------------------|
| HermesKernel | Primary deployable unit | Deployed as one unit |
| Core Components (C1–C4) | Kernel-owned primitives | Included within HermesKernel; initialized during Phases 0–3 |
| Core Managers (M1–M9 + Part 4 additions) | Kernel-owned capability domains | Included within HermesKernel; initialized during Phases 4–8 |
| Engineering Services (E1–E8) | Registered runtime entities | Registered within the kernel; initialized Phase 9+ |
| Capability Facade Services (F1–F4) | Event-to-Manager bridges | Registered within the kernel; initialized Phase 9+ |
| External systems | External dependencies | Not deployed by AI-OS; connected via extension points |

**Inference path:** Since Core Components, Core Managers, and Services have no independent deployment lifecycle outside HermesKernel (Part 1 §1.6.1; Part 3 §3.2), HermesKernel is the single architecture-defined deployable unit.

**Note:** The exact composition of the Core Component set (C1–C4) is subject to CONFLICT-CC-01. The Core Manager set is subject to CONFLICT-CM-01. The deployable unit remains HermesKernel regardless of which definition is authoritative.

### 3.4 External-System Boundaries

**Status:** EXISTING

External systems are boundaries beyond the HermesKernel deployable unit. They are not deployed by AI-OS:

| External System | Integration Mechanism | Source |
|-----------------|----------------------|--------|
| Obsidian | Extension point (Part 00 §0.5.2) | Part 14 §7 |
| Graphify | Extension point (Part 00 §0.5.2) | Part 14 §7 |
| LLM providers | ModelRouter / LLMManager | Part 4 §4.11; Part 14 §7 |
| MCP servers | MCPManager / MCPService | Part 4 §4.8; Part 6 §6.8; Part 14 §7 |

**Network topology, endpoint configuration, and connectivity mechanisms are UNSPECIFIED.**

### 3.5 Process/Container/Runtime Isolation

**Status:** UNSPECIFIED

The architecture defines HermesKernel as the deployable unit but does not mandate whether it runs as a bare process, container, function, or other execution environment. This is UNSPECIFIED.

---

## 4. Deployment Dependencies

### 4.1 Internal Dependencies

**Status:** EXISTING / DERIVED

HermesKernel depends on the following internal architectural elements, all of which must be initialized before the kernel is operational:

**Core Components:**

| ID | Name | Dependency Role | Status |
|----|------|-----------------|--------|
| C1 | EventBus | Inter-component communication substrate; MUST initialize first | EXISTING (Part 2 §2.1) |
| C2 | ServiceRegistry | Service registration and dependency validation | EXISTING (Part 5 §5.1) |
| C3 | ConfigurationManager | Configuration loading and distribution | EXISTING (Part 3 §3.5) |
| C4 | LifecycleManager | Kernel lifecycle orchestration | EXISTING (Part 1 §1.9) |

**Note:** The name and role of C4 is subject to CONFLICT-CC-01 (StructuredLogger per Part 3 §3.6 vs LifecycleManager per Part 1 §1.7.1 / Part 00 §0.4 Principle 12).

**Core Managers (Part 1 §1.8.1 canonical set):**

| ID | Name | Dependency Role |
|----|------|-----------------|
| M1 | WorkflowManager | Workflow orchestration |
| M2 | MemoryManager | Memory backend coordination |
| M3 | SkillManager | Skill execution coordination |
| M4 | MCPManager | MCP transport coordination |
| M5 | CouncilManager | Consensus coordination |
| M6 | ModelRouter | Model provider routing |
| M7 | CheckpointManager | State checkpointing |
| M8 | RetryManager | Retry policy enforcement |
| M9 | RootCauseAnalyzer | Failure analysis |

**Additional managers in Part 4 §4.2.1 (CONFLICT-CM-01):** StateManager, ResourceManager, HealthManager.

**Engineering Services:**

| ID | Name | Dependency Role |
|----|------|-----------------|
| E1 | PlanningService | Planning event emission |
| E2 | CodingService | Coding event emission |
| E3 | ReviewService | Review event emission |
| E4 | TestingService | Test event emission |
| E5 | DeploymentService | Deployment lifecycle events |
| E6 | OperationsService | Operations event emission |
| E7 | LearningService | Learning event emission |
| E8 | HumanInteractionService | Human escalation |

**Note:** Engineering Service count is subject to CONFLICT-ES-01 (8 per Part 5 vs 10 per alternative inventory).

**Governance Services (G-00 through G-15):** Documented in Part 13. These services enforce governance policies and depend on EventBus and SecurityManager.

**Capability Facade Services:**

| ID | Name | Role |
|----|------|------|
| F1 | SkillService | Bridges Events to SkillManager |
| F2 | CouncilService | Bridges Events to CouncilManager |
| F3 | MCPService | Bridges Events to MCPManager |
| F4 | MemoryService | Bridges Events to MemoryManager |

### 4.2 External Dependencies

**Status:** UNSPECIFIED / GAP

Parts 0–14 do not specify external runtime dependencies for the HermesKernel process. The following are UNSPECIFIED:

- Operating system runtime requirements
- Memory allocation requirements
- CPU/core requirements
- Network port bindings (if any)
- Filesystem path requirements
- Environment variable prerequisites (names and schemas)
- External service endpoints

**GAP-DEP-02:** No resource requirements or external dependency specifications are defined in Parts 0–14. Implementation must determine minimum resource requirements and document them separately.

### 4.3 Configuration Dependencies

**Status:** EXISTING

HermesKernel depends on the four-layer configuration merge system:

1. Defaults (hardcoded architecture defaults)
2. `app.yaml` (application-level configuration)
3. `env.yaml` (environment-specific configuration)
4. Environment variables (runtime overrides)

Configuration is frozen after Phase 3 of initialization.

**Source:** `configuration.md` §1.1–1.4; Part 7 §7.1–7.4

---

## 5. Startup Semantics

### 5.1 Startup Authority

**Status:** EXISTING / CONFLICT

Startup sequencing is governed by Part 3 §3.2 (HermesKernel lifecycle) and Part 1 §3.4 (ServiceRegistry topological order). The phased initialization model is defined in Part 4 §4.1.

**Note:** The exact number and definition of initialization phases is subject to CONFLICT-INIT-01. Part 4 §4.1 defines a 5-phase model; Part 1 §1.10.2 describes a different structure. Both are preserved; the conflict is unresolved.

### 5.2 Phased Initialization

**Status:** EXISTING (Part 4 §4.1) / CONFLICT (phase count per CONFLICT-INIT-01)

**Part 4 §4.1 five-phase model:**

| Phase | Scope | Authority |
|-------|-------|-----------|
| Phase 0 | EventBus initialization | Part 2 §2.1 |
| Phase 1 | ServiceRegistry initialization | Part 5 §5.1 |
| Phase 2 | Core Components initialization + Configuration loading | Part 1 §1.7.1; Part 3 §3.5 |
| Phase 3 | Core Managers initialization + Configuration freeze | Part 4 §4.2.1; `configuration.md` §1.4 |
| Phase 4 | Engineering Services initialization | Part 5 §5.2 |

**Dependency readiness rule:** A component or service MUST NOT emit events or receive events until the EventBus is initialized. A service MUST NOT be registered in ServiceRegistry until its declared dependencies are initialized.

**Source:** Part 4 §4.1; Part 5 §5.1 (ServiceRegistry topological order)

**CONFLICT-INIT-01:** Part 1 §1.10.2 describes a different phase structure with different phase boundaries. Both source definitions are preserved; the conflict is unresolved.

### 5.3 Startup Failure Behavior

**Status:** EXISTING / DERIVED

| Failure Origin | Behavior | Kernel Response |
|---------------|----------|-----------------|
| Core Component initialization fails | Abort initialization; shut down already-initialized components in reverse order; emit failure event | Kernel does not reach RUNNING |
| Core Manager initialization fails | Abort phase; shut down managers in current and prior phases in reverse order; shut down Core Components in reverse order; emit failure event | Kernel does not reach RUNNING |
| Service initialization fails | Mark Service as FAILED; continue initializing other Services per dependency topology | Kernel may reach RUNNING with failed non-critical Services |
| Configuration validation fails (Phase 2) | FATAL; abort initialization | Kernel does not reach RUNNING |

**Source:** Part 1 §1.10.4; Part 3 §3.7.3; Part 3 §3.5.8; Part 4 §4.12.7

**Note:** `max_retries` semantics for TRANSIENT retry are unclear — whether it represents retry count or total call count (IMP-GAP-06). Retry semantics diverge between Part 2 §2.4 and Part 12 §18 (GAP-RETRY).

### 5.4 Configuration Loading During Startup

**Status:** EXISTING

Configuration is loaded during Phase 2 using the four-layer merge model. Configuration is frozen after Phase 3.

**Freeze rule:** After Phase 3 completes, configuration MUST NOT be modified through `app.yaml`, `env.yaml`, or environment variables. Runtime configuration changes MUST use the ConfigurationAuthority interface.

**Source:** `configuration.md` §1.1–1.4; Part 7 §7.1–7.4

### 5.5 Configuration Authority During Startup

**Status:** EXISTING

ConfigurationAuthority is the central governance entity for configuration access. During startup, configuration is loaded through ConfigurationAuthority before being distributed to components.

**Note:** ConfigurationAuthority is defined in Part 4 §4A/§4B, creating CONFLICT-03 with Part 1 §1.7.1 (fixed set of 4 Core Components). See §26.

**Source:** Part 4 §4A/§4B; Part 14 §14.3

---

## 6. Shutdown Semantics

### 6.1 Shutdown Ordering

**Status:** EXISTING

Shutdown ordering is the reverse of startup ordering. This is mandated by the architecture.

| Shutdown Phase | Entities | Order |
|---------------|----------|-------|
| Services (Phase 9+) | Engineering Services, Facade Services | Reverse dependency topology |
| Core Managers | All Core Managers | Reverse phase order |
| Core Components (C1–C4) | LifecycleManager → ConfigurationManager → ServiceRegistry → EventBus | Reverse initialization order |
| EventBus | C1 — MUST be last | Terminates after all other components |

**Source:** Part 1 §1.11.2; Part 3 §3.7.4; Part 4 §4.12.8

### 6.2 Shutdown Semantics

**Status:** EXISTING

Each entity's shutdown protocol:

1. Emit shutdown event
2. Flush in-flight work / drain queues
3. Release resources
4. Await acknowledgment
5. Enter SHUTDOWN state

**EventBus shutdown:** Rejects new publishes; processes in-flight events; clears subscriptions; emits shutdown event.

**ServiceRegistry shutdown:** Clears registry; emits shutdown event.

**Shutdown is best-effort.** Individual shutdown failures do not prevent the kernel from reaching TERMINATED.

**Source:** Part 1 §1.11.2; Part 3 §3.4.11; Part 1 §1.11.4

### 6.3 Shutdown Initiation

**Status:** EXISTING

Shutdown is initiated by calling `kernel.shutdown(reason, error)` where reason is one of: `graceful`, `error`, `forced`.

**Invariant:** Once TERMINATED, the kernel instance MUST be discarded; re-initialization is PROHIBITED.

**Source:** Part 1 §1.11.1; Part 1 §1.9.1 (INV-LC-003)

### 6.4 Shutdown Timeout

**Status:** UNSPECIFIED

Parts 0–14 do not define a maximum shutdown timeout. The kernel MAY wait indefinitely for in-flight operations to complete, or it MAY enforce a timeout. This decision is UNSPECIFIED.

**GAP-DEP-03:** Shutdown timeout behavior is not defined in Parts 0–14. Implementation must decide whether to use a bounded timeout or wait indefinitely, and what happens when the timeout is reached.

### 6.5 Forced Shutdown

**Status:** UNSPECIFIED

If a component does not respond to shutdown within an implementation-defined window, the behavior is UNSPECIFIED.

**GAP-DEP-04:** Forced shutdown behavior is not defined in Parts 0–14. Implementation must define forced shutdown semantics.

### 6.6 What Is Not Defined

**Status:** UNSPECIFIED

The architecture does NOT define:

- Signal handlers (SIGTERM, SIGINT)
- Process supervisors or systemd units
- Container stop signals
- Operating-system-level shutdown mechanics

These are UNSPECIFIED. The kernel governs its own lifecycle internally; how that maps to process-level or infrastructure-level lifecycle events is an implementation decision.

---

## 7. Configuration Loading Sequence

### 7.1 Four-Layer Merge

**Status:** EXISTING

Configuration loading follows the four-layer merge model:

1. **Defaults** — Hardcoded architecture defaults (lowest precedence)
2. **`app.yaml`** — Application-level configuration
3. **`env.yaml`** — Environment-specific configuration
4. **Environment variables** — Runtime overrides (highest precedence)

Each layer overrides the previous layer for the same key. The merge is performed by ConfigurationAuthority.

**Source:** `configuration.md` §1.1–1.4; Part 7 §7.1–7.4

### 7.2 Configuration Freeze

**Status:** EXISTING

Configuration is frozen after Phase 3 of initialization. After freeze:

- `app.yaml` and `env.yaml` changes are NOT picked up
- Environment variable changes are NOT picked up
- Configuration changes MUST use the ConfigurationAuthority interface
- Configuration freeze is an architectural invariant; it MUST NOT be bypassed

**Source:** `configuration.md` §1.4; Part 7 §7.4

### 7.3 Configuration Validation

**Status:** UNSPECIFIED

Parts 0–14 do not specify whether configuration is validated at load time, what validation rules apply, or what happens when invalid configuration is detected.

**GAP-DEP-05:** Configuration validation rules and error handling are not defined in Parts 0–14. Implementation must define validation logic and the behavior on validation failure.

### 7.4 Configuration Authority

**Status:** EXISTING

ConfigurationAuthority is the central governance entity for all configuration access. Components MUST read configuration through ConfigurationAuthority; they MUST NOT read configuration files directly.

**Note:** ConfigurationAuthority is defined in Part 4 §4A/§4B, creating CONFLICT-CONFIG-01 with Part 1 §1.7.1. See §26.

**Source:** Part 4 §4A/§4B; Part 14 §14.3

---

## 8. Health / Readiness

### 8.1 Probe Distinctions

**Status:** EXISTING / PARTIALLY SPECIFIED

The architecture defines four distinct probe concepts:

| Probe | Meaning | Architecture Definition | Implementation Mechanism |
|-------|---------|------------------------|-------------------------|
| **Health** | Overall system status | Aggregates health of all integrated components | UNSPECIFIED |
| **Liveness** | Process is running and not deadlocked | Kernel process is alive; entities respond to healthCheck() | UNSPECIFIED |
| **Readiness** | Kernel is ready to accept work | All required phases initialized; no CRITICAL failures | UNSPECIFIED |
| **Startup** | Kernel is still initializing | Phase 0–3 not yet complete | UNSPECIFIED |

These are architectural distinctions. The implementation mechanism for exposing them is UNSPECIFIED.

**Source:** Part 4 §4.7 (health aggregation); Part 3 §3.2 (kernel lifecycle); Part 1 §1.8.1 M8 (HealthManager); Part 12 §12.12 RI-005/RI-006 (liveness/readiness probe semantics)

### 8.2 Health Aggregation

**Status:** EXISTING

Health checks aggregate across all integrated components per Part 4 §4.7. A component reports its own health; the kernel aggregates individual health signals into a system-level health signal.

**Source:** Part 4 §4.7

**GAP-DEP-08:** The health aggregation algorithm is not defined in Parts 0–14. Implementation must define how individual component health signals are combined into a system-level health signal.

### 8.3 Readiness Criteria

**Status:** DERIVED

The kernel is ready when:

- Phase 0–3 initialization is complete
- No CRITICAL failures occurred during initialization
- EventBus is accepting and dispatching events
- ServiceRegistry is populated with all required services
- Configuration has been loaded and frozen

**Source:** DERIVED from Part 3 §3.2, Part 4 §4.1, `configuration.md` §1.4

### 8.4 Probe Semantics (Collaboration Domain)

**Status:** EXISTING

For collaboration components, the architecture defines specific probe semantics per Part 12 §12.12:

| Probe Type | Requirement | Failure Response |
|-----------|------------|-----------------|
| **Liveness (RI-005)** | MUST respond within 100ms; 3 consecutive non-responses trigger restart | Component restarted |
| **Readiness (RI-006)** | MUST respond within 100ms; non-readiness removes from routing tables within one probe interval | Component removed from routing |
| **Startup** | Prevents premature readiness checks during slow startup | Liveness probe delayed until startup succeeds |

**Important distinction:** These probe semantics apply to the **collaboration domain** (Part 12). The kernel-level health model uses `healthCheck()` polling. The two are related but distinct.

**Source:** Part 12 §12.12 RI-005, RI-006, §19.4

### 8.5 Health Check Endpoint Technology

**Status:** UNSPECIFIED

The architecture defines **probe semantics** (response time, failure behavior, liveness/readiness distinction) but does **NOT** define the implementation mechanism (HTTP endpoint, event, IPC call, etc.).

**GAP-DEP-06:** Probe exposure mechanism is not defined in Parts 0–14. Implementation must choose and implement the mechanism.

---

## 9. Rollout Strategies

### 9.1 Rollout Authority

**Status:** EXISTING / DERIVED

Rollout strategies are governed by the kernel lifecycle events defined in Part 3 §3.3 and the service deployment contracts in Part 9 §9.7 and Part 12 §19.4.

### 9.2 Supported Rollout Strategies

**Status:** EXISTING (Part 9 §9.7.15–9.7.17; Part 12 §19.4)

The architecture defines the following rollout strategies for the deployment and collaboration service domains:

| Strategy | Source | Scope |
|----------|--------|-------|
| **Blue-Green** | Part 9 §9.7.15 | Infrastructure deployment domain |
| **Canary** | Part 9 §9.7.16; Part 12 §19.4 | Infrastructure / collaboration deployment; MUST for critical path changes |
| **Rolling** | Part 9 §9.7.17; Part 12 §19.4 | Infrastructure / collaboration deployment |
| **Zero-Downtime** | Part 9 DG-9.7.14; Part 12 §19.4 | MUST support where feasible |

**Architecture constraint:** All rollout strategies must preserve the EventBus communication invariant (ADR-001: Event-First Communication).

**Source:** Part 9 §9.7.14–9.7.17; Part 12 §19.4

### 9.3 Zero-Downtime Requirements

**Status:** EXISTING (Part 9 DG-9.7.14; Part 12 §19.4)

Collaboration services MUST support zero-downtime deployments:

- Rolling deployment: New instances brought up before old instances drained
- Health gate: New instances MUST pass health checks before receiving traffic
- Drain period: Old instances MUST drain in-flight work before shutdown
- Rollback: Failed deployments MUST be rolled back automatically if error rate exceeds threshold within 5 minutes
- Canary: Critical path changes MUST be deployed to canary instances first, validated, then rolled out

### 9.4 Kernel Rollout Strategy

**Status:** IMPLEMENTATION DECISION REQUIRED

The architecture does NOT prescribe which rollout strategy applies to the HermesKernel deployment unit. The kernel is the deployable unit; its rollout strategy is an implementation decision.

**IMP-DEC-01:** Which rollout strategy to use for the HermesKernel deployment unit. Options: Blue-Green, Canary, Rolling, Big-Bang. Architecture constraint: must preserve EventBus as sole communication substrate.

### 9.5 Deployment Strategy Contract

**Status:** EXISTING (Part 9 §9.7.14.2)

All deployment strategies MUST adhere to:

- Atomic transition between states where possible
- Verifiable health at each stage
- Automated rollback on failure
- Auditable transition steps
- Resource isolation between versions where applicable

---

## 10. Failure / Recovery

### 10.1 Failure Classification

**Status:** EXISTING

Parts 0–14 define four failure classifications:

| Classification | Meaning | Architecture Response |
|----------------|---------|----------------------|
| **TRANSIENT** | Temporary condition; retry may succeed | Retry per RetryManager policy |
| **DEGRADED** | Partial capability loss; system continues | Continue in degraded mode; emit failure event |
| **CRITICAL** | Core function failure; requires intervention | Kernel may halt or enter safe state; checkpoint state |
| **FATAL** | Irrecoverable; kernel cannot continue | Kernel MUST halt; emit final event |

**Source:** Part 1 §1.12.1; Part 00 §0.4 Principle 9

### 10.2 Failure Propagation

**Status:** EXISTING

All failure communication within the HermesKernel uses the EventBus. Components MUST NOT throw exceptions across architectural boundaries. Failures are communicated via failure events that include correlation/causation IDs.

**Failure event requirement:** Every failure MUST emit an event with eventId, eventType, eventVersion, correlationId, causationId, and payload per the event envelope specification (Part 2 §2.2.1).

**Source:** Part 2 §2.2.1 (event envelope); Part 2 §2.4 (failure events); ADR-001 (Event-First Communication)

### 10.3 Retry and Backoff

**Status:** EXISTING / GAP

RetryManager (Part 4 §4.4) governs retry behavior for TRANSIENT failures.

**GAP-RETRY:** Retry semantics diverge between Part 2 §2.4 and Part 12 §18. Part 2 defines retry at the subscription level; Part 12 defines retry at the event family level. This divergence is documented in `dependency-map.md` and `observability.md`. Part 15 does not resolve this divergence.

**Note:** `max_retries` semantics are unclear — whether it represents retry count or total call count (IMP-GAP-06).

**Source:** Part 4 §4.4; Part 2 §2.4; Part 12 §18

### 10.4 Circuit Breakers

**Status:** EXISTING

Circuit breakers are documented in Part 12 §12.9 (RI-028). Circuit breakers are triggered by operational failures, NOT by conformance violations.

**Critical constraint:** Circuit breakers respond to TRANSIENT and DEGRADED operational failures. They MUST NOT be triggered by architectural conformance violations.

**Source:** Part 12 §12.9 (RI-028); Part 14 §14.8

### 10.5 Recovery Actions

**Status:** EXISTING / DERIVED

| Failure Classification | Architecture Recovery Action | Implementation Requirement |
|------------------------|-----------------------------|---------------------------|
| TRANSIENT | Retry per RetryManager | Must respect max_retries; must emit retry events |
| DEGRADED | Continue in degraded mode | Must emit degraded event; must preserve core functions |
| CRITICAL | Kernel MAY halt; checkpoint state first | Must checkpoint state before halting |
| FATAL | Kernel MUST halt; emit final event | Must emit final event; must not attempt recovery |

**Source:** DERIVED from Part 4 §4.3 (CheckpointManager), Part 4 §4.4 (RetryManager), Part 4 §4.5 (RootCauseAnalyzer), Part 2 §2.4 (failure events)

### 10.6 Collaboration-Service Recovery

**Status:** EXISTING (Part 12 §12.5–12.6)

Part 12 defines recovery for collaboration services:

| Recovery Scenario | Target RPO | Max RPO | Mechanism |
|-------------------|------------|---------|-----------|
| Workflow state | 30s | 5 minutes | Continuous checkpointing |
| Council deliberation | 0 | 1 vote cycle | Vote persistence before tally |
| Shared context | 10s | 1 minute | Replicated write-ahead log |
| Agent registry | 60s | 15 minutes | Registry replication |

| Recovery Scenario | Target RTO | Max RTO | Mechanism |
|-------------------|------------|---------|-----------|
| Single agent failure | 30s | 2 minutes | Failover to replacement |
| Workflow engine failure | 60s | 5 minutes | Resume on alternative instance |
| State store failure (single node) | 30s | 2 minutes | Failover to replica |
| State store failure (region) | 5 minutes | 30 minutes | Cross-region failover |

**Source:** Part 12 §12.5–12.6

### 10.7 What Is NOT Inferred

**Status:** EXISTING

The architecture's failure handling does NOT imply:

- **High Availability (HA) for the kernel:** The kernel is a single instance per process. HA via replication, multi-instance, or active-active is NOT defined for the kernel.
- **Automatic failover for the kernel:** Failover is defined for specific subsystems in Part 9 and Part 12 (collaboration services, state store, EventBus), not for the HermesKernel itself.
- **Autoscaling for the kernel:** Not defined for the kernel. Part 9 §9.7.13 defines scaling for infrastructure services.
- **Load balancing for the kernel:** Not defined for the kernel. Part 9 §9.7.12 defines load balancing for infrastructure services.
- **Multi-region for the kernel:** Part 12 §12.6 defines RTO/RPO for collaboration services including cross-region failover, but this applies to collaboration subsystems, not the kernel deployable unit.

**Source:** Part 14 §14.2 §10.3: "Event-based failure communication does NOT mean automatic restart, automatic retry, automatic failover, or automatic rollback."

---

## 11. External-System Boundaries

### 11.1 Boundary Definition

**Status:** EXISTING

The HermesKernel process boundary is the primary architectural boundary. External systems interact with the kernel only through documented extension points per Part 00 §0.5.2:

- Custom Memory Backend (via MemoryBackend ABC)
- Custom Skill (via Skill interface)
- Custom MCP Transport (via MCPTransport interface)
- Custom Consensus Algorithm (via ConsensusAlgorithm enum)
- Custom AI Agency Agent (via AIAgent subclass)
- Custom Model Provider (via ModelRouter registry)
- Custom Resource Type (via ResourceType enum)

**No external system may bypass the EventBus or invoke internal interfaces directly.**

**Source:** Part 00 §0.5.2; Part 14 §14.5; Part 14 §14.9

### 11.2 Facade Service Bridge Role

**Status:** EXISTING

Capability Facade Services (F1–F4) serve as the architectural bridge between external extension points and internal Core Managers:

| Facade | Bridges To | Extension Point |
|--------|-----------|----------------|
| F1: SkillService | SkillManager | Custom Skill |
| F2: CouncilService | CouncilManager | Custom Consensus Algorithm |
| F3: MCPService | MCPManager | Custom MCP Transport |
| F4: MemoryService | MemoryManager | Custom Memory Backend |

**Source:** Part 6 §6.1–6.4; Part 14 §14.5

### 11.3 Trust Boundary

**Status:** EXISTING

The architecture defines a single trust boundary for v1.0: the HermesKernel process boundary. All components within the kernel are trusted. External systems are outside the trust boundary.

**Note:** The v1.0 architecture is a trusted single-tenant system per Part 14 §14.9 and Part 14 §14.10. Multi-tenant isolation, mTLS, and zero-trust are NOT v1.0 requirements and are marked FUTURE or UNSPECIFIED.

**Source:** Part 14 §14.9; Part 14 §14.10; Part 1 §1.10 (SecurityBoundary)

### 11.4 External System Integration Contracts

**Status:** GAP

External system integration contracts are documented as gaps in `implementation-contracts.md`:

- EX-GAP-01: Identity Provider integration contract
- EX-GAP-02: Regulatory framework adapter contract
- EX-GAP-03: Telemetry backend export contract
- EX-GAP-04: External audit system integration contract

**Source:** `implementation-contracts.md` §EX-GAP-01 through EX-GAP-04

---

## 12. Configuration Cross-Reference

### 12.1 Consistency with configuration.md

| `configuration.md` Section | This Document Reference | Status |
|---------------------------|------------------------|--------|
| §4 Configuration Model | §7.1 Four-Layer Merge | Consistent |
| §5 Configuration Authority | §7.4 Configuration Authority | Consistent |
| §6 Configuration Precedence | §7.1 | Consistent |
| §7 Configuration Domains | §4.3 | Complementary — domains are architectural; deployment maps them to kernel phases |
| §8 Configuration Registry | §7.3 | Consistent — many items marked Not Specified |
| §10 Configuration Lifecycle | §5.4, §6 | Consistent — load/validate/freeze/consume lifecycle |
| §12 Invalid Configuration Behavior | §5.3 | Consistent — FATAL classification |

### 12.2 Environment Variables

**Status:** UNSPECIFIED

The architecture establishes that environment variables are the highest-precedence configuration source. However, specific environment variable names, schemas, or deployment-specific configuration keys are UNSPECIFIED. This document does not invent environment variables.

---

## 13. Health / Readiness Cross-Reference

### 13.1 Consistency with observability.md

| `observability.md` Section | This Document Reference | Status |
|---------------------------|------------------------|--------|
| §5 Health Signals | §8.2 Health Aggregation | Consistent |
| §4.2 Events (failure events) | §10.2 Failure Propagation | Consistent |
| §3.1 Metrics | UNSPECIFIED (metrics backend) | Complementary |
| §4.1 Logs | §10.2 | Consistent — failure-related logs |
| §6 Log Severity | §10.1 Failure Classification | Consistent — classification mapping |

### 13.2 Distinctions Preserved

| Distinction | This Document Treatment |
|-------------|------------------------|
| Health ≠ Readiness ≠ Liveness ≠ Startup | Preserved in §8.1 |
| Kernel healthCheck() ≠ collaboration probes | Preserved in §8.2 vs §8.4 |
| Probe semantics ≠ endpoint technology | Preserved in §8.5 |

---

## 14. Deployment Requirement Traceability

### 14.1 Requirement Map

| Deployment Requirement | Source | Status |
|-----------------------|--------|--------|
| HermesKernel is the single deployable unit | Part 3 §3.1; Part 1 §1.1 | EXISTING |
| All inter-component communication uses EventBus | Part 2 §2.1; ADR-001 | EXISTING |
| Configuration uses four-layer merge | `configuration.md` §1.1–1.4; Part 7 §7.1–7.4 | EXISTING |
| Configuration freezes after Phase 3 | `configuration.md` §1.4; Part 7 §7.4 | EXISTING |
| Startup follows phased initialization | Part 4 §4.1 | EXISTING |
| Shutdown follows reverse ordering | Part 1 §1.11.2; Part 3 §3.7.4 | EXISTING |
| Failures communicated via events, not exceptions | Part 2 §2.4; ADR-001 | EXISTING |
| Four failure classifications (TRANSIENT, DEGRADED, CRITICAL, FATAL) | Part 1 §1.12.1; Part 00 §0.4 Principle 9 | EXISTING |
| Checkpoint state before CRITICAL/FATAL shutdown | Part 4 §4.3 | EXISTING |
| External interaction via extension points only | Part 00 §0.5.2 | EXISTING |
| Circuit breakers respond to operational failures only | Part 12 §12.9 (RI-028); Part 14 §14.8 | EXISTING |
| Zero-downtime rollout for collaboration services | Part 9 DG-9.7.14; Part 12 §19.4 | EXISTING |
| Health aggregation across all integrated components | Part 4 §4.7 | EXISTING |
| Liveness probe: respond within 100ms; 3 failures → restart | Part 12 §12.12 RI-005 | EXISTING |
| Readiness probe: respond within 100ms; non-readiness → routing removal | Part 12 §12.12 RI-006 | EXISTING |
| Once TERMINATED, re-initialization PROHIBITED | Part 1 §1.9.1 | EXISTING |
| Partial initialization always rolled back on failure | Part 1 §1.10.4; Part 3 §3.7.3 | EXISTING |
| Shutdown proceeds to TERMINATED regardless of individual errors | Part 1 §1.11.4; Part 3 §3.7.4 | EXISTING |

### 14.2 Non-Requirements

The following are explicitly NOT deployment architecture requirements (all UNSPECIFIED):

- Specific container runtime or format
- Specific orchestration system
- Specific cloud platform
- Specific CI/CD pipeline
- Specific monitoring backend
- Specific logging backend
- Specific secret management product
- Multi-process or distributed deployment topology
- HA, failover, autoscaling, or load balancing for the kernel
- Process-level lifecycle mechanics (signals, supervisors)

---

## 15. Deployment-to-Contract Traceability

### 15.1 Implementation Contracts

**Status:** EXISTING

Deployment-related implementation contracts are documented in `implementation-contracts.md`:

| Contract ID | Description | Status |
|-------------|-------------|--------|
| DEP.MUST.1 | HermesKernel is the single deployable unit | EXISTING |
| DEP.MUST.2 | Startup follows phased initialization order | EXISTING |
| DEP.MUST.3 | Shutdown follows reverse initialization order | EXISTING |
| DEP.MUST.4 | Configuration uses four-layer merge; freezes after Phase 3 | EXISTING |
| DEP.MUST.5 | Health probes aggregate across all integrated components | EXISTING |
| RT.MUST.1 | Runtime initialization order — **SOURCE VERIFICATION REQUIRED** | GAP — `runtime-map.md` is EMPTY |
| TEST.MUST.1 | Deployment tests — **MISSING SOURCE** | GAP — `testing.md` is EMPTY |

**Source:** `implementation-contracts.md` §DEP.MUST.1 through DEP.MUST.5

### 15.2 Runtime Dependency Verification

**Status:** UNSPECIFIED / GAP

`runtime-map.md` is EMPTY. All runtime dependency relationships are marked UNVERIFIED in `dependency-map.md`. Deployment-specific runtime dependencies (initialization order, singleton accessor catalog, event flow) are UNSPECIFIED.

**GAP-DEP-09:** Runtime dependency verification requires `runtime-map.md` to be authored. Until then, all runtime dependency claims are UNSPECIFIED.

### 15.3 Deployment Test Verification

**Status:** UNSPECIFIED / GAP

`testing.md` is EMPTY. No deployment conformance tests are defined in Parts 0–14.

**GAP-DEP-11:** Deployment conformance tests are not defined. Implementation must define tests that verify the deployment invariants listed in §20.

---

## 16. Deployment-to-ADR Traceability

### 16.1 ADR State

**Status:** EXISTING

`adrs.md` documents that no formal ADR records currently exist in the repository. All architectural decisions are documented inline within Parts 0–14.

**However,** the following decisions established in Parts 0–14 have direct deployment implications:

| Decision | Source | Deployment Implication |
|----------|--------|----------------------|
| Event-First Communication (primary integration pathway) | Part 14 §ADR-001; Part 2 §2.1 | All deployment rollout strategies must preserve event-mediated communication; no synchronous RPC between kernel instances |
| HermesKernel as single deployable unit | Part 3 §3.1; Part 1 §1.1 | Deployment produces a single artifact; no multi-artifact coordination |
| Four-layer configuration merge | Part 7 §7.1–7.4 | Deployment must include configuration files at all four layers or document defaults |
| Configuration freeze after Phase 3 | Part 7 §7.4 | Hot-reload of configuration files is architecturally unsupported |

**Source:** `adrs.md` §1–6; Part 14 §ADR-001

### 16.2 ADR Gaps

**Status:** GAP

No formal ADR records exist for deployment-specific decisions. If implementation requires ADRs for deployment topology, probe mechanisms, or other UNSPECIFIED items, they must be created through the Part 00 §0.5.3 ADR process.

**GAP-DEP-10:** No formal ADRs exist for deployment-specific decisions. Implementation decisions for GAP-DEP-01 through GAP-DEP-09 may require ADRs.

---

## 17. Deployment Gaps and Unspecified Areas

### 17.1 GAP Registry

| Gap ID | Description | Architecture Status | Implementation Impact |
|--------|-------------|---------------------|----------------------|
| GAP-DEP-01 | Distributed deployment topology not defined | GAP — Parts 0–14 silent | Implementation must choose: single process, multi-process, or distributed |
| GAP-DEP-02 | Resource requirements (memory, CPU, ports) not defined | GAP — Parts 0–14 silent | Implementation must define minimum resource requirements |
| GAP-DEP-03 | Shutdown timeout behavior not defined | GAP — Parts 0–14 silent | Implementation must decide bounded vs. indefinite timeout |
| GAP-DEP-04 | Forced shutdown behavior not defined | GAP — Parts 0–14 silent | Implementation must define forced shutdown semantics |
| GAP-DEP-05 | Configuration validation rules not defined | GAP — Parts 0–14 silent | Implementation must define validation logic and error handling |
| GAP-DEP-06 | Probe exposure mechanism not defined | GAP — Parts 0–14 silent | Implementation must choose HTTP endpoint, event, or IPC mechanism |
| GAP-DEP-07 | Deployment-specific configuration schema not defined | GAP — Parts 0–14 silent | Implementation must define deployment config keys |
| GAP-DEP-08 | Health aggregation algorithm not defined | GAP — Parts 0–14 silent | Implementation must define how component health signals combine |
| GAP-DEP-09 | Runtime dependency verification blocked by empty runtime-map.md | GAP — `runtime-map.md` is EMPTY | All runtime dependencies UNVERIFIED until runtime-map.md authored |
| GAP-DEP-10 | No formal ADRs for deployment-specific decisions | GAP — `adrs.md` has no formal ADRs | Implementation decisions may require ADR creation per Part 00 §0.5.3 |
| GAP-DEP-11 | Deployment conformance tests not defined | GAP — `testing.md` is EMPTY | Implementation must create deployment conformance tests |

### 17.2 UNSPECIFIED Registry

The following deployment concerns are NOT addressed in Parts 0–14:

| Area | Description | Why Unspecified |
|------|-------------|----------------|
| Container runtime | Docker, Podman, etc. | Not mentioned in Parts 0–14 |
| Orchestration | Kubernetes, Nomad, etc. | Not mentioned in Parts 0–14 |
| Cloud platform | AWS, Azure, GCP, etc. | Not mentioned in Parts 0–14 |
| IaC tooling | Terraform, Pulumi, etc. | Not mentioned in Parts 0–14 |
| CI/CD pipeline | GitHub Actions, Jenkins, ArgoCD | Not mentioned in Parts 0–14 |
| Deployment manifests | Helm, Kustomize | Not mentioned in Parts 0–14 |
| Service mesh | Istio, Linkerd | Not mentioned in Parts 0–14 |
| API gateway / ingress | API gateways, ingress controllers | Not mentioned in Parts 0–14 |
| Load balancer | Specific LB configuration | Not mentioned in Parts 0–14 |
| Monitoring backend | Prometheus, Datadog, etc. | Observability requirements exist; backends do not |
| Logging backend | Specific logging infrastructure | Logging requirements exist; backends do not |
| Secret management | Vault, AWS Secrets Manager, etc. | Security requirements exist; products do not |
| OS/runtime requirements | Memory, CPU, ports, filesystem paths | Not mentioned in Parts 0–14 |
| Probe mechanism | HTTP endpoint, event, IPC | Not defined in Parts 0–14 |
| Health aggregation algorithm | How component health combines | Not defined in Parts 0–14 |

### 17.3 CONFLICT Registry

| Conflict ID | Description | Source A | Source B | Status |
|-------------|-------------|----------|----------|--------|
| CONFLICT-CC-01 | Four different Core Component definitions | Part 00 §0.3.1/§0.7, Part 1 §1.7.1, Part 3 §3.6, Part 4 §4A/§4B | Each defines a different C1–C4 set | UNRESOLVED |
| CONFLICT-CM-01 | Three different Core Manager definitions | Part 1 §1.8.1, Part 4 §4.2.1 | Part 1: 9 managers; Part 4: 13+ managers | UNRESOLVED |
| CONFLICT-ES-01 | Engineering Service count: 8 vs 10 | Part 5 §5.2, Part 14 components.md | Two different service inventories | UNRESOLVED |
| CONFLICT-INIT-01 | Initialization phase structure | Part 4 §4.1 (5 phases), Part 1 §1.10.2 | Different phase structures | UNRESOLVED |
| CONFLICT-FACADE-01 | SkillManager/CouncilManager/MCPManager not in Core Manager sets | Part 1 §1.8.1, Part 4 §4.2.1 | These managers appear in Part 4 but not Part 1 canonical set | UNRESOLVED |
| CONFLICT-CONFIG-01 | ConfigurationAuthority is a Core Component per Part 4 but not per Part 1 | Part 4 §4A/§4B, Part 1 §1.7.1 | Conflicts with fixed 4 Core Components | UNRESOLVED |

**Source:** `components.md` §11; `dependency-map.md` §5; `configuration.md` §CONFLICT entries

**All conflicts are preserved and escalated to the Architecture Review Board. This document does not resolve them.**

---

## 18. AI Coding Agent Rules

### 18.1 Source Inspection Rule

Before making any claim about deployment architecture, AI coding agents MUST inspect the authoritative source Parts (0–14). Do not assume any capability, requirement, or constraint exists until it is documented in a source Part or accepted ADR.

### 18.2 No Invention Rule

If a deployment concern is not addressed in Parts 0–14, label it UNSPECIFIED or GAP. Do NOT invent infrastructure choices (container runtimes, orchestrators, cloud platforms, CI/CD systems, monitoring stacks, logging backends, secret management products, load balancers, API gateways, service meshes, ingress controllers) to fill gaps.

### 18.3 Status Discipline Rule

Every claim must carry exactly one status label: EXISTING, DERIVED, ASSUMPTION, UNSPECIFIED, GAP, PROPOSED, FUTURE, CONFLICT, or IMPLEMENTATION DECISION REQUIRED. Do not present DERIVED claims as EXISTING; do not present PROPOSED claims as architecture fact.

### 18.4 Conflict Preservation Rule

If source Parts disagree on a deployment-related point, record the CONFLICT and escalate to the Architecture Review Board. Do NOT silently resolve conflicts by choosing one source over another.

### 18.5 Traceability Rule

Every claim must identify its source. Do not state "the architecture requires" without identifying which Part and section establishes the requirement.

### 18.6 Anti-Invention Rule

The following technologies and patterns are NOT part of the AI-OS architecture and MUST NOT appear as EXISTING or DERIVED claims:

- Docker, Kubernetes, Podman, or any container technology
- AWS, Azure, GCP, or any cloud platform
- Terraform, Pulumi, or any IaC tool
- GitHub Actions, Jenkins, ArgoCD, or any CI/CD system
- Helm, Kustomize, or any deployment manifest format
- Istio, Linkerd, or any service mesh
- API gateways or ingress controllers
- Load balancers
- Specific database products
- Vault, AWS Secrets Manager, or any secret management product
- Prometheus, Datadog, or any monitoring backend
- ELK, Splunk, or any logging backend

These are all UNSPECIFIED. Implementation must choose independently.

---

## 19. Deployment Invariants

### 19.1 Invariant Definitions

The following invariants MUST hold for all deployment configurations:

| Invariant | Description | Source |
|-----------|-------------|--------|
| INV-DEP-01 | HermesKernel is the sole deployable unit | Part 3 §3.1; Part 1 §1.1 |
| INV-DEP-02 | All inter-component communication uses EventBus | Part 2 §2.1; ADR-001 |
| INV-DEP-03 | Configuration uses four-layer merge model | `configuration.md` §1.1–1.4; Part 7 §7.1–7.4 |
| INV-DEP-04 | Configuration freezes after Phase 3 | `configuration.md` §1.4; Part 7 §7.4 |
| INV-DEP-05 | External systems interact only through extension points | Part 00 §0.5.2 |
| INV-DEP-06 | Failure communication uses events, not exceptions | Part 2 §2.4; ADR-001 |
| INV-DEP-07 | Core Component and Core Manager interfaces are non-extension points | Part 00 §0.5.2 |
| INV-DEP-08 | Shutdown follows reverse initialization order | Part 1 §1.11.2; Part 3 §3.7.4 |
| INV-DEP-09 | Checkpoint state before CRITICAL/FATAL shutdown | Part 4 §4.3 |
| INV-DEP-10 | Circuit breakers respond to operational failures only | Part 12 §12.9 (RI-028); Part 14 §14.8 |
| INV-DEP-11 | Once TERMINATED, re-initialization is PROHIBITED | Part 1 §1.9.1 |
| INV-DEP-12 | Partial initialization is always rolled back on failure | Part 1 §1.10.4; Part 3 §3.7.3 |

### 19.2 Invariant Enforcement

Invariants are enforced by the architecture through:

- EventBus contract (all communication mediated)
- ServiceRegistry topological ordering (dependency validation)
- ConfigurationAuthority freeze mechanism (post-Phase 3 immutability)
- CheckpointManager (state persistence before shutdown)
- SecurityManager authz (external access control)

Implementation MUST NOT bypass these enforcement mechanisms.

---

## 20. Deployment Anti-Patterns

### 20.1 Forbidden Deployment Patterns

The following patterns are architecturally forbidden:

| Anti-Pattern | Why Forbidden | Source |
|--------------|---------------|--------|
| Direct service-to-service calls bypassing EventBus | Violates ADR-001 (Event-First Communication) | ADR-001; Part 2 §2.1 |
| Synchronous RPC between kernel instances | Violates Event-First Communication; introduces coupling | ADR-001 |
| Shared mutable state outside StateManager | Violates StateManager scope rules | Part 4 §4.6 |
| Configuration modification after Phase 3 freeze | Violates configuration immutability invariant | `configuration.md` §1.4 |
| Bypassing SecurityManager for external access | Violates trust boundary | Part 14 §14.10 |
| Adding/removing Global Singleton Accessor signatures | Non-extension point per Part 00 §0.5.2 | Part 00 §0.5.2 |
| Altering Core Component or Core Manager interfaces | Non-extension point per Part 00 §0.5.2 | Part 00 §0.5.2 |
| Inferring HA for the kernel from subsystem recovery | Recovery actions for specific subsystems do not imply kernel HA | Part 14 §14.2 §10.3 |
| Inventing health endpoint technologies | Probe semantics are defined; endpoint technology is UNSPECIFIED | §8.5 |
| Inventing deployment infrastructure | Container runtimes, orchestrators, cloud platforms are UNSPECIFIED | §2.2 |

---

## 21. Deployment-to-Observability Integration

### 21.1 Observability Signals Relevant to Deployment

Deployment lifecycle events produce observability signals as defined in `observability.md`:

| Lifecycle Event | Signal Types Produced | Source |
|-----------------|----------------------|--------|
| Kernel startup | Events (PhaseStarted, PhaseCompleted), Logs, Traces | `observability.md` §4.2; Part 4 §4.1 |
| Component initialization | Events, Health signals | `observability.md` §4.2, §5.1 |
| Shutdown | Events (shutdown events), Logs | §6; `observability.md` §4.2 |
| Failure | Events (failure events), Logs | Part 2 §2.4; `observability.md` §4.2 |
| DEGRADED state | Health signals, Events | Part 4 §4.7; `observability.md` §5.1 |

**Note:** Metrics are UNSPECIFIED — the responsibility for emitting metrics is defined but the schema, backend, and collection mechanism are not (see `observability.md` §3.1).

### 21.2 Correlation in Deployment Events

All deployment lifecycle events MUST include correlation/causation IDs per the event envelope specification (Part 2 §2.2.1). This enables tracing a deployment operation through all phases and components.

---

## 22. Configuration Cross-Reference (Deployment Domain)

### 22.1 Deployment Configuration Keys

**Status:** UNSPECIFIED

No deployment-specific configuration keys are defined in Parts 0–14 or `configuration.md`. The following categories are UNSPECIFIED:

- Startup parameters
- Resource limits (memory, CPU)
- Shutdown timeout values
- Probe intervals
- Retry limits for deployment operations
- Rollout strategy parameters

**GAP-DEP-07:** Deployment configuration schema must be defined by implementation.

### 22.2 Configuration Integration Points

The deployment architecture integrates with configuration at the following points:

1. **Startup** — Configuration loaded via four-layer merge before Phase 3
2. **Freeze** — Configuration frozen after Phase 3
3. **Runtime changes** — Must use ConfigurationAuthority interface
4. **Shutdown** — Configuration state checkpointed via CheckpointManager

**Source:** §5.4; `configuration.md` §1.1–1.4

---

## 23. Glossary Reference

All terminology used in this document is defined in `glossary.md`. Key terms:

| Term | Definition Location |
|------|---------------------|
| HermesKernel | `glossary.md` §2.1 |
| Core Component | `glossary.md` §3.1 (CONFLICT-CC-01) |
| Core Manager | `glossary.md` §3.2 (CONFLICT-CM-01) |
| Engineering Service | `glossary.md` §3.3 |
| Capability Facade Service | `glossary.md` §3.4 |
| EventBus | `glossary.md` §4.1 |
| Event-First Communication | `glossary.md` §5.1 (ADR-001) |
| ConfigurationAuthority | `glossary.md` §6.1 |
| Four-layer merge | `glossary.md` §6.2 |
| Phase 0–4 | `glossary.md` §7.1 (CONFLICT-INIT-01) |
| CRITICAL / DEGRADED / TRANSIENT / FATAL | `glossary.md` §8.1 |
| Shutdown | `glossary.md` §9.1 |
| Health / Liveness / Readiness / Startup | `glossary.md` §10.1 |
| Rollout | `glossary.md` §11.1 |
| Extension Point | `glossary.md` §12.1 |

---

## 24. Final Deployment Architecture Audit

### 24.1 Audit Summary

This section provides the final audit of this document against the Part 15 quality framework.

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Every normative claim has a status label | PASS | All claims carry EXISTING, DERIVED, UNSPECIFIED, GAP, CONFLICT, or IMPLEMENTATION DECISION REQUIRED |
| Every EXISTING/DERIVED claim has traceable source citation | PASS | All EXISTING and DERIVED claims cite Part number and section |
| All CONFLICTs are explicitly named with parties | PASS | CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-INIT-01, CONFLICT-FACADE-01, CONFLICT-CONFIG-01 all documented with sources |
| All GAPs and UNSPECIFIED items are recorded | PASS | GAP-DEP-01 through GAP-DEP-11; UNSPECIFIED registry in §17.2 |
| No architectural invention | PASS | No invented components, APIs, events, schemas, protocols |
| No invented infrastructure technologies | PASS | Docker, Kubernetes, AWS, Terraform, etc. are all marked UNSPECIFIED |
| Scope and exclusions unambiguous | PASS | §5.1–5.2 clearly defines what deployment architecture governs and what it does not |
| AI-agent safety guidance explicit | PASS | §18 provides explicit rules for AI coding agents |
| Cross-document consistency maintained | PASS | §13–15 verify consistency with configuration.md, observability.md, implementation-contracts.md |
| runtime-map.md EMPTY correctly reflected | PASS | GAP-DEP-09, RT.MUST.1 flagged; all runtime dependencies UNVERIFIED |
| testing.md EMPTY correctly reflected | PASS | GAP-DEP-11, TEST.MUST.1 flagged; no deployment tests claimed |
| Anti-invention tests pass | PASS | No retracted claims used as architecture; no invented technologies |

### 24.2 Gap Summary

| Gap ID | Area | Resolution Required By |
|--------|------|----------------------|
| GAP-DEP-01 | Deployment topology | Implementation team |
| GAP-DEP-02 | Resource requirements | Implementation team |
| GAP-DEP-03 | Shutdown timeout | Implementation team |
| GAP-DEP-04 | Forced shutdown behavior | Implementation team |
| GAP-DEP-05 | Configuration validation | Implementation team |
| GAP-DEP-06 | Probe exposure mechanism | Implementation team |
| GAP-DEP-07 | Deployment configuration schema | Implementation team |
| GAP-DEP-08 | Health aggregation algorithm | Implementation team |
| GAP-DEP-09 | Runtime dependency verification | `runtime-map.md` authorship |
| GAP-DEP-10 | Deployment ADRs | ADR process (Part 00 §0.5.3) |
| GAP-DEP-11 | Deployment conformance tests | `testing.md` authorship |

### 24.3 CONFLICT Summary

| Conflict ID | Description | Status |
|-------------|-------------|--------|
| CONFLICT-CC-01 | Four different Core Component definitions across Parts 0, 1, 3, 4 | UNRESOLVED — escalated to ARB |
| CONFLICT-CM-01 | Three different Core Manager definitions across Parts 1, 4 | UNRESOLVED — escalated to ARB |
| CONFLICT-ES-01 | Engineering Service count: 8 vs 10 | UNRESOLVED — escalated to ARB |
| CONFLICT-INIT-01 | Initialization phase structure: Part 4 §4.1 vs Part 1 §1.10.2 | UNRESOLVED — escalated to ARB |
| CONFLICT-FACADE-01 | SkillManager/CouncilManager/MCPManager not in Core Manager sets | UNRESOLVED — escalated to ARB |
| CONFLICT-CONFIG-01 | ConfigurationAuthority as Core Component per Part 4 but not Part 1 | UNRESOLVED — escalated to ARB |

### 24.4 Readiness Decision

**READINESS: CONDITIONALLY READY**

This document is CONDITIONALLY READY for implementation use under the following conditions:

1. **CONFLICTs are preserved, not resolved:** CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-INIT-01, CONFLICT-FACADE-01, and CONFLICT-CONFIG-01 must be resolved by the Architecture Review Board before they can be considered settled. Implementation must account for all conflicting definitions.

2. **GAPs are acknowledged:** GAP-DEP-01 through GAP-DEP-11 represent areas where the architecture is silent. Implementation must make decisions for GAP-DEP-01 through GAP-DEP-08 independently. GAP-DEP-09 and GAP-DEP-11 require authoring of `runtime-map.md` and `testing.md` respectively.

3. **IMPLEMENTATION DECISION REQUIRED items are tracked:** IMP-DEC-01 through IMP-DEC-05 must be resolved during implementation planning.

4. **Non-extension-point interfaces are preserved:** Core Component interfaces, Core Manager interfaces, EventBus interface, BaseService contract, Global Singleton Accessor signatures, and other non-extension points MUST NOT be altered.

5. **Source fidelity is maintained:** When this document conflicts with Parts 0–14, the source Part wins. Implementation must verify source claims against authoritative Parts.

**This document becomes FULLY READY when:**
- CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-INIT-01, CONFLICT-CONFIG-01 are resolved by ARB
- GAP-DEP-09 is resolved by authoring `runtime-map.md`
- GAP-DEP-11 is resolved by authoring `testing.md`
- IMP-DEC-01 through IMP-DEC-05 are resolved and documented
- All GAP-DEP-01 through GAP-DEP-08 implementation decisions are documented
