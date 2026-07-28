# Architecture Specification Part 6 — Step 5: MemoryService Architecture

## 6.5 MemoryService: The Memory Execution Facade

### 6.5.1 Purpose

The **MemoryService** exists to resolve the fundamental architectural tension between *memory definition* and *memory access* within the AI-OS Memory Facade (Section 5.2).

The **MemoryManager** (Section 6.2) owns the **Definition Plane** — the static topology of memory spaces including registration, schema validation, versioning, dependency resolution, lifecycle governance, and memory policy definition. It operates on declarative artifacts: memory space manifests, memory schemas, memory policies, and memory topology graphs.

**Engineering Services** (Part 4) and **AI Agents** (Part 3) operate in the **Execution Plane** — they must *access* memory at runtime, performing reads, writes, queries, subscriptions, and snapshots across heterogeneous memory spaces. They require a stable, uniform access surface that is insulated from the volatility and complexity of registration mechanics, schema validation logic, persistence concerns, and memory infrastructure heterogeneity.

These two planes **MUST NOT** communicate directly. Direct coupling would violate the Memory Facade principle: Engineering Services and AI Agents would become dependent on MemoryManager's internal representation of memory spaces, creating transitive dependencies on concerns orthogonal to memory access.

MemoryService solves the **Memory Access Facade Problem**: how to present a stable, authoritative memory access surface to consumers while maintaining strict separation from the Definition Plane and enforcing the memory boundary against heterogeneous memory infrastructure.

Without MemoryService, the architecture faces three architecturally unacceptable alternatives:

1. **Consumers import MemoryManager directly** — violating layer separation, leaking registration and governance concerns into access logic, and making memory access inseparable from memory space discovery.

2. **Consumers access memory via raw Event Space messages** — requiring each consumer to implement memory protocol negotiation, query construction, connection management, consistency handling, snapshot coordination, and error normalization across heterogeneous memory infrastructure, duplicating infrastructure logic across every consumer.

3. **Memory providers self-register access endpoints** — inverting control, scattering access logic across memory implementations, and preventing centralized observability, policy enforcement, consistency guarantees, and access optimization.

MemoryService eliminates these alternatives by providing a **single, mandatory memory access facade** that all Engineering Services and AI Agents **SHALL** use for all memory operations. It is the **sole architectural boundary** between the trusted AI-OS Execution Plane and heterogeneous memory infrastructure.

### 6.5.2 Architectural Position

Within the AI-OS layered architecture (Part 1), MemoryService occupies a mediating position between two architectural planes:

| Plane | Responsibility | Representative Component |
|-------|----------------|--------------------------|
| **Definition Plane** | Memory space registration, schema validation, versioning, lifecycle governance, memory policy definition | MemoryManager |
| **Execution Plane** | Memory access (read, write, query, subscribe, snapshot), memory abstraction management, argument validation, result normalization, policy enforcement | MemoryService |

MemoryService is the **sole component** that bridges these planes. It consumes MemoryManager's registration events to maintain an **access index** — a read-optimized projection of the memory topology graph optimized for access-time decisions (routing, schema lookup, policy evaluation, consistency resolution). It does not modify registration state; it only projects it.

This unidirectional dependency is an **architectural invariant**:

> **INV-6.5.1 (Unidirectional Dependency — Definition Plane)**: MemoryManager **SHALL NOT** depend on MemoryService. MemoryService **SHALL** depend on MemoryManager's published registration events only.

### 6.5.3 Role Within the Memory Facade

The Memory Facade (Section 5.2) presents two distinct interfaces to two distinct consumer classes:

| Facade Interface | Owner | Consumers | Plane |
|------------------|-------|-----------|-------|
| **Definition Contract** (register space, validate schema, define policy, version, deprecate, topology query) | MemoryManager | Platform operators, CI/CD pipelines, memory space architects, governance tools | Definition Plane |
| **Access Contract** (read, write, query, subscribe, snapshot, health, metrics, consistency) | MemoryService | Engineering Services, AI Agents, external integrations, platform services | Execution Plane |

MemoryService **owns the Access Contract entirely**. It defines the access contract, error taxonomy, consistency semantics, streaming protocol, cancellation model, correlation identity model for distributed tracing, and memory abstraction binding. These are *access concerns* — they do not exist in the Definition Plane.

### 6.5.4 Relationship to MemoryManager

The MemoryManager–MemoryService relationship is **publisher/subscriber**, not client/server:

- **MemoryManager** publishes memory space registration, schema update, policy update, and deprecation/removal events to the Event Space (Part 4).
- **MemoryService** subscribes to these events to maintain its access index.
- **MemoryService** **SHALL NOT** invoke MemoryManager APIs, query MemoryManager directly, or import MemoryManager types. It operates exclusively on the *eventually consistent* projection built from the event stream.

This design ensures:
- **Temporal decoupling**: MemoryService remains operational during MemoryManager maintenance windows.
- **Failure isolation**: MemoryManager failures do not cascade into access failures (provided the access index is current).
- **Scalability independence**: MemoryService can scale horizontally for access throughput without affecting registration throughput.
- **Infrastructure insulation**: Changes to memory infrastructure, indexing mechanisms, or persistence engines are absorbed at the MemoryService boundary without affecting MemoryManager.

### 6.5.5 Memory Access Constraint

The prohibition on direct consumer–MemoryManager communication is absolute:

> **REQ-6.5.1 (Access Monopoly)**: Engineering Services and AI Agents **SHALL NOT** import, reference, or communicate with MemoryManager under any circumstances. All memory operations **SHALL** transit MemoryService.

> **REQ-6.5.2 (Memory Boundary Enforcement)**: Engineering Services and AI Agents **SHALL NOT** communicate directly with memory providers via memory protocols, raw connections, query languages, or any other mechanism. All memory provider interactions **SHALL** transit MemoryService.

Rationale:
- **Interface Segregation**: Consumers require access semantics (read, write, query, subscribe, snapshot, consistency). MemoryManager exposes definition semantics (register, validate, govern, query topology). These are disjoint concerns.
- **Stability**: MemoryManager's APIs evolve with the definition model. MemoryService's access API is stable — it changes only when the *access contract* changes.
- **Policy Centralization**: Cross-cutting access policies (authorization, rate limiting, consistency enforcement, quota management, audit logging, data residency) **MUST** be enforced at a single choke point. MemoryService is that choke point.
- **Substitutability**: MemoryService can be stubbed, mocked, or replaced (e.g., with an in-memory simulator for development) without touching MemoryManager.
- **Provider Isolation**: Memory providers are heterogeneous and potentially untrusted. MemoryService is the **sole trust boundary** — it validates all operations against declared schemas, enforces consistency guarantees, applies size limits, and sanitizes errors before they enter the AI-OS trust domain.

### 6.5.6 Architectural Responsibilities

MemoryService bears the following **architectural responsibilities** (concerns, not implementations):

| Responsibility | Description |
|----------------|-------------|
| **Access Routing** | Resolving a memory space identifier to its memory provider, consistency domain, and access binding using the access index. |
| **Memory Abstraction** | Managing the memory abstraction to the target provider; abstracting memory infrastructure heterogeneity from consumers. |
| **Contract Enforcement** | Validating that access arguments conform to the memory space's declared schema before dispatch; validating results against output schema. |
| **Policy Application** | Applying cross-cutting access policies (authorization, rate limits, quotas, consistency requirements, data residency, retention) uniformly. |
| **Result Normalization** | Transforming raw provider responses into the **canonical access result contract** (success, error, streaming, snapshot). |
| **Correlation Tracking** | Maintaining end-to-end access identity across asynchronous boundaries for observability and debugging. |
| **Provider Lifecycle Isolation** | Ensuring provider failures (unavailability, corruption, schema drift) cannot corrupt the access index or affect other operations. |
| **Index Freshness** | Guaranteeing the access index reflects registration state within a bounded staleness window. |
| **Consistency Mediation** | Enforcing declared consistency levels at the access boundary; mediating cross-provider consistency. |
| **Credential Management** | Managing authentication credentials for memory providers; injecting credentials at the memory binding without exposing them to consumers. |

### 6.5.7 Architectural Invariants

The following invariants define MemoryService's architectural contract. They are **necessary conditions** for the Memory Facade architecture to hold:

> **INV-6.5.1 (Unidirectional Dependency — Definition Plane)**: MemoryService depends on MemoryManager's events; MemoryManager has zero dependency on MemoryService.

> **INV-6.5.2 (Unidirectional Dependency — Memory Boundary)**: Memory providers have zero dependency on MemoryService internals. MemoryService treats all memory providers as untrusted.

> **INV-6.5.3 (Access Monopoly)**: All memory operations from Engineering Services and AI Agents transit MemoryService. No alternative access path exists.

> **INV-6.5.4 (Index Read-Only)**: MemoryService's access index is derived exclusively from MemoryManager's published events. MemoryService never writes registration state.

> **INV-6.5.5 (Policy Completeness)**: Every access policy applicable to memory operations is enforced at MemoryService. No policy enforcement is delegated to consumers or providers.

> **INV-6.5.6 (Failure Containment)**: A memory provider failure (unavailability, corruption, protocol error, consistency violation) cannot cause MemoryService to lose its access index, drop unrelated operations, or publish spurious registration events.

> **INV-6.5.7 (Staleness Bound)**: The access index reflects MemoryManager's registration state with a maximum staleness of **T_index_max**. Consumers observe at-most **T_index_max** delay for new memory spaces to become accessible.

> **INV-6.5.8 (Schema Fidelity)**: MemoryService validates access arguments against the *exact* schema declared in the memory space's registered manifest. No schema transformation, relaxation, coercion, or inference occurs at the facade.

> **INV-6.5.9 (Result Canonicality)**: All memory operations return the **canonical access result contract**. No provider-specific response formats escape MemoryService.

> **INV-6.5.10 (Correlation Completeness)**: Every memory operation carries a correlation identity that is propagated to the provider (via metadata), emitted in all observability signals, and returned to the caller.

> **INV-6.5.11 (Memory Protocol Transparency)**: Consumers invoke memory operations through a memory-agnostic contract. MemoryService absorbs all memory protocol heterogeneity. No protocol-specific concerns leak to consumers.

> **INV-6.5.12 (Untrusted Provider Response)**: Every response from a memory provider is treated as untrusted input. MemoryService **SHALL** validate against the declared output schema, enforce size limits, and sanitize error payloads before returning to the caller.

> **INV-6.5.13 (Consistency Fidelity)**: MemoryService enforces the consistency level declared in the memory space's policy. No operation returns a result weaker than the declared consistency guarantee.

> **INV-6.5.14 (Quota Isolation)**: Quota consumption is tracked per memory space and per consumer; one consumer's quota exhaustion does not affect other consumers or other memory spaces.

These invariants are **architectural law**. Implementation decisions that violate them constitute architectural defects, regardless of functional correctness.

### 6.5.8 Event Space Interactions

MemoryService participates in the Event Space (Part 4) as both consumer and producer:

#### Consumed Events (from MemoryManager)

| Event | Purpose |
|-------|---------|
| `MemorySpaceRegistered` | New memory space version available for access |
| `MemorySpaceUpdated` | Memory space metadata, schema, or binding changed |
| `MemorySpaceDeprecated` | Memory space version entering deprecation grace period |
| `MemorySpaceRemoved` | Memory space version removed after grace period expiry |
| `MemoryPolicyRegistered` | New memory policy (consistency, retention, residency, quota) available |
| `MemoryPolicyUpdated` | Policy parameters changed |
| `MemoryPolicyDeprecated` | Policy version entering deprecation |
| `MemoryPolicyRemoved` | Policy version removed |
| `MemoryTopologyChanged` | Memory space dependency or topology graph changed |

MemoryService **SHALL** process these events in order, maintaining the access index as a faithful projection.

#### Produced Events (to Event Space)

| Event | Purpose |
|-------|---------|
| `MemoryAccessStarted` | Access operation admitted to execution pipeline |
| `MemoryAccessCompleted` | Access operation terminated (success, error, or cancellation) |
| `MemoryAccessStreamChunk` | Streaming chunk emitted for subscription/snapshot operations |
| `MemoryPolicyViolation` | Policy enforcement denied an access operation |
| `MemorySchemaValidationFailed` | Request or response failed schema validation |
| `MemoryConsistencyViolation` | Provider failed to meet declared consistency guarantee |
| `MemoryProviderError` | Provider-level failure (unavailable, corruption, timeout) |
| `AccessIndexStalenessExceeded` | Index freshness SLO breach detected |

These events enable platform observability, audit, and automated remediation without coupling consumers to MemoryService internals.

### 6.5.9 Manager Space Interactions

MemoryService **SHALL NOT** directly invoke Manager Space components (Part 2). Its only Manager Space interaction is indirect, via the Event Space:

- It consumes MemoryManager's registration events.
- It consumes Policy Manager's policy events.
- It produces access observability events consumed by platform managers (e.g., MonitoringManager, AuditManager, SecurityManager, QuotaManager).

This preserves the Manager Space / Event Space separation defined in Part 2.

### 6.5.10 Lifecycle

MemoryService lifecycle is defined by three states:

| State | Entry Condition | Exit Condition |
|-------|-----------------|----------------|
| **Bootstrapping** | Process start | Access index built from event log and published |
| **Serving** | Index published, health checks passing | Shutdown signal or index corruption detected |
| **Degraded** | Dependency unavailable (event stream, policy service, auth service, provider pool) | Dependency restored or graceful shutdown |

**Bootstrapping**: On startup, MemoryService **SHALL** reconstruct its access index by consuming the registration event stream from the last known consistent position. It **SHALL NOT** enter Serving state until the index reflects all events up to the stream head.

**Serving**: MemoryService accepts access operations, maintains index currency via event consumption, and emits observability events.

**Degraded**: If the event stream becomes unavailable, MemoryService **SHALL** continue serving from its last consistent index while emitting `AccessIndexStalenessExceeded` events. If staleness exceeds a configured threshold, it **SHALL** transition to a safe mode (rejecting operations for memory spaces not in index, or failing open/closed per policy domain configuration).

**Shutdown**: On termination signal, MemoryService **SHALL** drain in-flight operations (up to a configured grace period), flush pending observability events, and persist its index position for fast restart.

### 6.5.11 Ownership Boundaries

| Concern | Owner | MemoryService Role |
|---------|-------|-------------------|
| Memory space manifest | MemoryManager | Consumer (read-only projection) |
| Memory space schema | MemoryManager | Consumer (exact enforcement) |
| Memory policy | Policy Manager (Part 2) | Consumer (enforcement point) |
| Memory provider binding | MemoryManager | Consumer (routing target) |
| Access policy | Policy Manager (Part 2) | Consumer (enforcement point) |
| Access execution | Memory provider process | Orchestrator (dispatch, timeout, retry) |
| Access result | Memory provider process | Transformer (normalization, validation) |
| Authentication credentials | Secret Manager (Part 2) | Consumer (injection at memory binding) |
| Observability emission | MemoryService | Producer (canonical events) |
| Correlation identity | MemoryService | Generator / propagator |
| Memory abstraction lifecycle | MemoryService | Owner (per provider binding) |
| Consistency domain state | MemoryService | Mediator (cross-provider coordination) |

MemoryService **owns** the Access Contract, the canonical access result contract, the Memory Access ErrorCode taxonomy, the correlation identity model, the access index data structure, the memory abstraction bindings, and the consistency mediation logic. It **does not own** memory space definitions, schemas, policies, provider configurations, or authentication secrets — it consumes and enforces them.

### 6.5.12 Dependency Rules

| Dependency | Direction | Type | Rationale |
|------------|-----------|------|-----------|
| MemoryManager → MemoryService | **Forbidden** | — | Preserves Definition Plane purity |
| MemoryService → MemoryManager (events) | **Required** | Event subscription | Index currency |
| MemoryService → Policy Manager (events) | **Required** | Event subscription | Policy currency |
| MemoryService → Policy Manager | **Required** | Policy consumption | Access policy enforcement |
| MemoryService → Secret Manager | **Required** | Credential consumption | Provider credential management |
| MemoryService → Event Space | **Required** | Infrastructure | Event consumption/production |
| Engineering Service → MemoryService | **Required** | API invocation | Access monopoly |
| AI Agent → MemoryService | **Required** | API invocation | Access monopoly |
| Engineering Service → MemoryManager | **Forbidden** | — | Facade integrity |
| AI Agent → MemoryManager | **Forbidden** | — | Facade integrity |
| Engineering Service → Memory Provider | **Forbidden** | — | Memory boundary enforcement |
| AI Agent → Memory Provider | **Forbidden** | — | Memory boundary enforcement |
| Memory Provider → MemoryService | **None** | — | Providers are opaque executables |

### 6.5.13 Communication Model

MemoryService communication follows the **Request–Response**, **Request–Stream**, and **Request–Snapshot** patterns over the **Event Space communication model** (Part 4). The Access Contract is **memory-agnostic** — it defines the logical interaction, not the wire protocol. The memory abstraction is an implementation detail internal to MemoryService.

#### Access Operation Model

```
Consumer → MemoryService → Memory Provider
         │                 │
         │  1. Route       │
         │  2. Authorize   │
         │  3. Validate    │
         │  4. Dispatch ───▶
         │                 │  5. Execute
         │                 │  (read/write/query/subscribe/snapshot)
         │                 ◀─── 6. Respond
         │  7. Validate    │
         │  8. Normalize   │
         │  9. Respond ────▶
         │                 │
```

All access operations traverse a fixed **pipeline** of stages. Each stage either passes (enriching context) or fails (returning a typed error, aborting the pipeline). The pipeline is an architectural construct — its stages are responsibilities, not implementation modules.

#### Pipeline Stages (Architectural)

1. **Route** — Resolve memory space identifier to memory provider, consistency domain, and authentication context; verify deprecation status.
2. **Authorize** — Verify caller identity, evaluate policy binding, check quotas, verify data residency constraints.
3. **Validate Request** — Validate arguments against declared schema (read filter, write payload, query predicate, subscription filter).
4. **Dispatch** — Dispatch operation via memory abstraction; enforce consistency level.
5. **Validate Response** — Validate response against declared output schema; enforce size limits; verify consistency.
6. **Normalize** — Transform to canonical Access Result Envelope.
7. **Emit Observability** — Emit completion event, record metrics, update quota consumption.

For streaming operations (subscribe, tail), stages 4–6 operate incrementally per chunk, with a final completion chunk. For snapshot operations, stages 4–6 coordinate a consistent point-in-time cut across the consistency domain.

#### Cancellation Model

Callers **MAY** cancel in-flight access operations. MemoryService **SHALL** propagate cancellation to the memory provider and **SHALL** emit a `MemoryAccessCancelled` observability event. Cancellation **SHALL NOT** corrupt the access index or affect other operations.

### 6.5.14 Security Responsibilities

MemoryService enforces security at the **access boundary** and **memory boundary**:

| Security Concern | MemoryService Responsibility |
|------------------|-----------------------------|
| Caller authentication | Verified at ingress (gateway); re-verified at MemoryService entry |
| Caller authorization | Policy evaluation against memory space's policy binding |
| Provider authentication | Credential injection at memory binding; mutual authentication where configured |
| Provider identity verification | Identity validation per memory abstraction |
| Memory space isolation | Memory spaces execute in isolated providers; responses treated as untrusted input |
| Data protection | Request/response payloads validated against schemas; size limits enforced; encryption mandated by policy |
| Audit integrity | All access operations emit immutable audit events with correlation identity |
| Communication security | Provider endpoints invoked over mutually authenticated channels |
| Credential isolation | Consumers never receive provider credentials; injected only at memory layer |
| Protocol validation | Strict memory abstraction compliance; malformed responses rejected |
| Data residency | Enforced via policy binding; provider selection respects residency constraints |
| Retention enforcement | Write operations validated against retention policy; expired data inaccessible |

MemoryService **SHALL NOT** delegate any of these responsibilities to callers or providers.

### 6.5.15 Resource Responsibilities

| Resource | Responsibility |
|----------|----------------|
| Access index memory | MemoryService owns lifecycle; bounded by memory space count, schema size, policy count |
| Event stream consumer position | MemoryService manages position tracking; consistent projection semantics |
| In-flight operation state | MemoryService tracks for timeout, cancellation, observability; bounded by concurrency limits |
| Memory abstraction bindings | MemoryService manages per-provider bindings; lifecycle tied to memory space registration state |
| Policy evaluation cache | MemoryService manages; invalidated on policy update events |
| Schema validator cache | MemoryService manages; keyed by schema identifier; invalidated on memory space update |
| Consistency domain state | MemoryService manages per-domain; includes coordination state |
| Quota tracking state | MemoryService manages per-consumer, per-space; persisted for durability |

Resource exhaustion **SHALL** trigger graceful degradation per Section 6.5.10, not catastrophic failure.

### 6.5.16 Failure Containment

Failure domains are strictly isolated by architectural boundary:

| Failure Domain | Containment Boundary |
|----------------|---------------------|
| Memory provider process crash | Affects only in-flight operations to that provider; index unchanged; other providers proceed |
| Memory provider timeout | Affects only that operation; provider health updated |
| Memory provider protocol violation | Affects only that operation; validation error returned; provider marked unhealthy |
| Memory provider corruption detected | Affects only that provider's operations; consistency violation event emitted; coordination re-evaluated |
| Memory abstraction failure | Affects only operations using that binding; binding replenished; health updated |
| Provider authentication failure | Affects only that provider's operations; auth failure event emitted; no credential leakage |
| Schema validation failure (request) | Affects only that operation; validation error returned to caller |
| Schema validation failure (response) | Affects only that operation; validation error returned; provider marked unhealthy |
| Consistency guarantee violation | Affects only that operation; consistency violation event emitted; provider health degraded |
| Event stream unavailability | Degraded mode: serve from last consistent index; emit staleness events |
| Policy service unavailability | Degraded mode: fail closed (deny) or fail open per policy domain configuration |
| Quota exhaustion | Affects only that consumer/space combination; other consumers/spaces unaffected |

The access index is **immutable per projection cycle** — it is reconstructed atomically from the event log and updated atomically. No memory operation can corrupt it.

### 6.5.17 Architecture Decision Records

| ADR | Title | Decision |
|-----|-------|----------|
| ADR-6.5.1 | MemoryService as Access Facade | MemoryService is the sole access facade for memory operations; separates Definition Plane from Execution Plane. |
| ADR-6.5.2 | Publisher/Subscriber with MemoryManager | MemoryManager publishes events; MemoryService subscribes. No direct API calls. |
| ADR-6.5.3 | Memory Providers as Untrusted | All memory providers are untrusted; responses validated, size-limited, sanitized. |
| ADR-6.5.4 | Memory Abstraction | MemoryService abstracts memory infrastructure behind a uniform access contract. |
| ADR-6.5.5 | Canonical Access Result Contract | All provider responses normalized to canonical Access Result Envelope; no provider-specific formats escape. |
| ADR-6.5.6 | Correlation Identity Propagation | Correlation ID generated at ingress; propagated to provider via metadata; emitted in all events. |
| ADR-6.5.7 | Index Staleness SLO | Maximum index staleness T_index_max is an architectural SLO; breach triggers Degraded mode. |
| ADR-6.5.8 | Health Isolation per Provider | Provider health state maintained per memory provider; isolates cascading failures. |
| ADR-6.5.9 | Credential Injection at Memory Layer | Provider credentials injected at memory binding; never visible to consumers or access logic. |
| ADR-6.5.10 | Streaming as First-Class Access Mode | Streaming subscriptions use incremental pipeline stages with chunk-level validation and normalization. |
| ADR-6.5.11 | Consistency as Declared Contract | Consistency level is a declared property of the memory space; MemoryService enforces it; no implicit weakening. |
| ADR-6.5.12 | Snapshot as Coordinated Cut | Snapshot operations coordinated by MemoryService across consistency domain; returns verifiable snapshot token. |
| ADR-6.5.13 | Quota Isolation per Consumer/Space | Quota tracked and enforced per (consumer, memory space) tuple; no cross-contamination. |

### 6.5.18 Conformance Requirements

A conforming MemoryService implementation **SHALL** satisfy all of the following:

1. **Unidirectional Definition Plane** — Zero dependency on MemoryManager APIs; consumes only registration event stream.
2. **Memory Boundary Enforcement** — Memory providers have zero dependency on MemoryService internals; all providers treated as untrusted.
3. **Access Monopoly** — All Engineering Service and AI Agent memory operations route through MemoryService; no bypass path exists.
4. **Read-Only Index Projection** — Access index is a read-only projection of registration state; no registration writes performed.
5. **Policy Completeness** — All access policies enforced at MemoryService; none delegated to consumers or providers.
6. **Failure Containment** — Provider failures cannot corrupt the access index or affect unrelated operations.
7. **Bounded Staleness** — Index staleness ≤ T_index_max (measurable, configurable, alerted).
8. **Schema Fidelity** — Request and response validation uses exact registered schemas; no coercion or transformation.
9. **Canonical Result Contract** — All operations return the canonical access result contract; no provider-specific formats escape.
10. **Correlation Completeness** — Correlation identity generated and propagated end-to-end; emitted in all observability signals.
11. **Memory Abstraction Transparency** — Consumers cannot detect or depend on the underlying memory abstraction.
12. **Untrusted Provider Response** — All provider responses validated against output schema; size limits enforced; errors sanitized.
13. **Consistency Fidelity** — Declared consistency level enforced; no operation returns a weaker guarantee.
14. **Quota Isolation** — Quota tracked and enforced per (consumer, memory space) tuple; no cross-contamination.
15. **Event Space Compliance** — Consumes all MemoryManager and Policy Manager event types in order; produces all access observability event types; processing is idempotent with consistent projection state.
16. **Pipeline Compliance** — Pipeline stages execute in defined order with fail-fast semantics; validation before dispatch and after receipt; consistency enforced per declaration; cancellation propagated; index unaffected.
17. **Lifecycle Compliance** — Bootstraps index before Serving; enters Degraded on dependency loss with staleness events; drains in-flight on shutdown; preserves index for fast restart.
18. **Security Compliance** — Verifies caller authentication; evaluates authorization per binding; treats provider responses as untrusted; enforces size limits; invokes providers over mutually authenticated channels; injects credentials at memory layer only; enforces residency and retention per policy.
19. **Observability Compliance** — Emits canonical access events for all operations; emits metrics for count, duration, in-flight, errors, staleness, latencies, provider health, quota, and consistency.
20. **Runtime Compliance** — Horizontally scalable without session affinity; supports concurrent instantiation without coordination; health assessment distinguishes liveness, readiness, and index currency.

---

*End of Architecture Specification Part 6 — Step 5*