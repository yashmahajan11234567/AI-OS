# Architecture Specification Part 6 — Step 6: CouncilService Architecture

## 6.6 CouncilService: The Council Execution Facade

### 6.6.1 Purpose

The **CouncilService** exists to resolve the fundamental architectural tension between *council definition* and *council execution* within the AI-OS Council Facade (Section 5.3).

The **CouncilManager** (Section 6.2) owns the **Definition Plane** — the static topology of councils including council registration, member registration, protocol validation, versioning, dependency resolution, and lifecycle governance. It operates on declarative artifacts: council manifests, member schemas, protocol definitions, and council topology graphs.

**Engineering Services** (Part 4) and **AI Agents** (Part 3) operate in the **Execution Plane** — they must *execute* councils at runtime, supplying arguments and receiving results. They require a stable, uniform execution surface that is insulated from the volatility and complexity of registration mechanics, validation logic, protocol negotiation, and persistence concerns.

These two planes **MUST NOT** communicate directly. Direct coupling would violate the Council Facade principle: Engineering Services and AI Agents would become dependent on CouncilManager's internal representation of councils, creating transitive dependencies on concerns orthogonal to execution.

CouncilService solves the **Council Execution Facade Problem**: how to present a stable, authoritative execution surface to consumers while maintaining strict separation from the Definition Plane and enforcing the execution boundary against heterogeneous council participants.

Without CouncilService, the architecture faces three architecturally unacceptable alternatives:

1. **Consumers import CouncilManager directly** — violating layer separation, leaking registration and governance concerns into execution logic, and making council execution inseparable from council discovery.

2. **Consumers execute councils via raw Event Space messages** — requiring each consumer to implement protocol-level message construction, participant orchestration, correlation tracking, timeout handling, and error normalization, duplicating infrastructure logic across every consumer.

3. **Council participants self-register execution endpoints** — inverting control, scattering execution logic across participant implementations, and preventing centralized observability, policy enforcement, and execution optimization.

CouncilService eliminates these alternatives by providing a **single, mandatory execution facade** that all Engineering Services and AI Agents **SHALL** use for all council executions.

### 6.6.2 Architectural Position

Within the AI-OS layered architecture (Part 1), CouncilService occupies a mediating position between two architectural planes:

| Plane | Responsibility | Representative Component |
|-------|----------------|--------------------------|
| **Definition Plane** | Council registration, member registration, protocol validation, versioning, lifecycle governance | CouncilManager |
| **Execution Plane** | Council execution, participant orchestration, argument validation, result normalization, policy enforcement | CouncilService |

CouncilService is the **sole component** that bridges these planes. It consumes CouncilManager's registration events to maintain an **execution index** — a read-optimized projection of the council topology graph optimized for execution-time decisions (participant routing, protocol binding, policy lookup). It does not modify registration state; it only projects it.

This unidirectional dependency is an **architectural invariant**:

> **INV-6.6.1 (Unidirectional Dependency — Definition Plane)**: CouncilManager **SHALL NOT** depend on CouncilService. CouncilService **SHALL** depend on CouncilManager's published registration events only.

### 6.6.3 Role Within the Council Facade

The Council Facade (Section 5.3) presents two distinct interfaces to two distinct consumer classes:

| Facade Interface | Owner | Consumers | Plane |
|------------------|-------|-----------|-------|
| **Definition Contract** (register council, register member, validate protocol, version, deprecate, topology query) | CouncilManager | Platform operators, CI/CD pipelines, council architects, governance tools | Definition Plane |
| **Execution Contract** (execute, stream, cancel, health, metrics, protocol binding) | CouncilService | Engineering Services, AI Agents, external integrations, platform services | Execution Plane |

CouncilService **owns the Execution Contract entirely**. It defines the execution contract, error taxonomy, timeout semantics, streaming protocol, cancellation model, correlation identity model for distributed tracing, and protocol binding abstraction. These are *execution concerns* — they do not exist in the Definition Plane.

### 6.6.4 Relationship to CouncilManager

The CouncilManager–CouncilService relationship is **publisher/subscriber**, not client/server:

- **CouncilManager** publishes council registration, member registration, protocol update, and deprecation/removal events to the Event Space (Part 4).
- **CouncilService** subscribes to these events to maintain its execution index.
- **CouncilService** **SHALL NOT** invoke CouncilManager APIs, query CouncilManager directly, or import CouncilManager types. It operates exclusively on the *eventually consistent* projection built from the event stream.

This design ensures:
- **Temporal decoupling**: CouncilService remains operational during CouncilManager maintenance windows.
- **Failure isolation**: CouncilManager failures do not cascade into execution failures (provided the execution index is current).
- **Scalability independence**: CouncilService can scale horizontally for execution throughput without affecting registration throughput.
- **Protocol insulation**: Changes to council protocol versions or participant protocols are absorbed at the CouncilService boundary without affecting CouncilManager.

### 6.6.5 Council Execution Constraint

The prohibition on direct consumer–CouncilManager communication is absolute:

> **REQ-6.6.1 (Execution Monopoly)**: Engineering Services and AI Agents **SHALL NOT** import, reference, or communicate with CouncilManager under any circumstances. All council executions **SHALL** transit CouncilService.

> **REQ-6.6.2 (Participant Boundary Enforcement)**: Engineering Services and AI Agents **SHALL NOT** communicate directly with council participants via participant protocols, raw connections, or any other mechanism. All participant interactions **SHALL** transit CouncilService.

Rationale:

- **Interface Segregation**: Consumers require execution semantics (execute, stream, cancel, consensus). CouncilManager exposes definition semantics (register, validate, govern, query). These are disjoint concerns.
- **Stability**: CouncilManager's APIs evolve with the definition model. CouncilService's execution API is stable — it changes only when the *execution contract* changes.
- **Policy Centralization**: Cross-cutting execution policies (authorization, rate limits, timeouts, retries, circuit breaking, participation quotas, audit logging) **MUST** be enforced at a single choke point. CouncilService is that choke point.
- **Substitutability**: CouncilService can be stubbed, mocked, or replaced (e.g., with a local executor for development) without touching CouncilManager.
- **Participant Isolation**: Council participants are heterogeneous and potentially untrusted. CouncilService is the **sole trust boundary** — it validates all participant responses, enforces schema conformance, applies size limits, and sanitizes errors before they enter the AI-OS trust domain.

### 6.6.6 Architectural Responsibilities

CouncilService bears the following **architectural responsibilities** (concerns, not implementations):

| Responsibility | Description |
|----------------|-------------|
| **Execution Routing** | Resolving a council identifier to its participant bindings, protocol bindings, and authentication context using the execution index. |
| **Execution Coordination** | Coordinating participant invocations per the execution semantics defined by CouncilManager; managing participant lifecycle during execution. |
| **Contract Enforcement** | Validating that execution arguments conform to the council's declared input schema before dispatch; validating participant responses against declared output schemas. |
| **Policy Application** | Applying cross-cutting execution policies (authorization, rate limits, timeouts, retries, circuit breaking, participation quotas) uniformly. |
| **Result Normalization** | Transforming raw participant responses into the **canonical council execution result contract** (success, error, streaming, consensus outcome). |
| **Correlation Tracking** | Maintaining end-to-end execution identity across asynchronous participant invocations for observability and debugging. |
| **Participant Lifecycle Isolation** | Ensuring participant failures (crash, timeout, protocol violation, schema violation) cannot corrupt the execution index or affect other executions. |
| **Index Freshness** | Guaranteeing the execution index reflects registration state within a bounded staleness window. |

### 6.6.7 Architectural Invariants

The following invariants define CouncilService's architectural contract. They are **necessary conditions** for the Council Facade architecture to hold:

> **INV-6.6.1 (Unidirectional Dependency — Definition Plane)**: CouncilService depends on CouncilManager's events; CouncilManager has zero dependency on CouncilService.

> **INV-6.6.2 (Unidirectional Dependency — Participant Boundary)**: Council participants have zero dependency on CouncilService internals. CouncilService treats all participants as untrusted.

> **INV-6.6.3 (Execution Monopoly)**: All council executions from Engineering Services and AI Agents transit CouncilService. No alternative execution path exists.

> **INV-6.6.4 (Index Read-Only)**: CouncilService's execution index is derived exclusively from CouncilManager's published events. CouncilService never writes registration state.

> **INV-6.6.5 (Policy Completeness)**: Every execution policy applicable to council execution is enforced at CouncilService. No policy enforcement is delegated to consumers or participants.

> **INV-6.6.6 (Failure Containment)**: A participant's execution failure (crash, timeout, protocol error, schema violation) cannot cause CouncilService to lose its execution index, drop unrelated executions, or publish spurious registration events.

> **INV-6.6.7 (Staleness Bound)**: The execution index reflects CouncilManager's registration state with a maximum staleness of **T_index_max**. Consumers observe at-most **T_index_max** delay for new councils or members to become executable.

> **INV-6.6.8 (Schema Fidelity)**: CouncilService validates execution arguments against the *exact* input schema declared in the council's registered manifest. Participant responses are validated against the exact output schemas. No schema transformation, relaxation, coercion, or inference occurs at the facade.

> **INV-6.6.9 (Result Canonicality)**: All council executions return the **canonical council execution result contract**. No participant-specific or protocol-specific response formats escape CouncilService.

> **INV-6.6.10 (Correlation Completeness)**: Every execution carries a correlation identity that is propagated to all participant invocations (via protocol metadata), emitted in all observability signals, and returned to the caller.

> **INV-6.6.11 (Protocol Transparency)**: Consumers invoke councils through a protocol-agnostic contract. CouncilService absorbs all participant protocol heterogeneity. No protocol-specific concerns leak to consumers.

> **INV-6.6.12 (Untrusted Participant Response)**: Every response from a council participant is treated as untrusted input. CouncilService **SHALL** validate against the declared output schema, enforce size limits, and sanitize error payloads before returning to the caller.

> **INV-6.6.13 (Execution Integrity)**: The execution semantics declared in the council's protocol are the sole determinant of execution outcome. CouncilService executes those semantics as defined by CouncilManager; participants cannot influence execution logic beyond their declared roles.

> **INV-6.6.14 (Participant Isolation)**: Quota consumption is tracked per council and per participant per consumer; one consumer's quota exhaustion does not affect other consumers, and one participant's quota does not affect other participants.

These invariants are **architectural law**. Implementation decisions that violate them constitute architectural defects, regardless of functional correctness.

### 6.6.8 Event Space Interactions

CouncilService participates in the Event Space (Part 4) as both consumer and producer:

#### Consumed Events (from CouncilManager)

| Event | Purpose |
|-------|---------|
| `CouncilRegistered` | New council version available for execution |
| `CouncilUpdated` | Council metadata, protocol, or binding changed |
| `CouncilDeprecated` | Council version entering deprecation grace period |
| `CouncilRemoved` | Council version removed after grace period expiry |
| `CouncilMemberRegistered` | New member version available on registered council |
| `CouncilMemberUpdated` | Member schema, protocol, or binding changed |
| `CouncilMemberDeprecated` | Member version entering deprecation grace period |
| `CouncilMemberRemoved` | Member version removed after grace period expiry |
| `CouncilProtocolRegistered` | New council protocol version available |
| `CouncilProtocolUpdated` | Protocol parameters or execution rules changed |
| `CouncilProtocolDeprecated` | Protocol version entering deprecation |
| `CouncilProtocolRemoved` | Protocol version removed |

CouncilService **SHALL** process these events in order, maintaining the execution index as a faithful projection.

#### Produced Events (to Event Space)

| Event | Purpose |
|-------|---------|
| `CouncilExecutionStarted` | Execution admitted to execution pipeline |
| `CouncilExecutionCompleted` | Execution terminated (success, error, or cancellation) |
| `CouncilExecutionFailed` | Execution terminated with error |
| `CouncilExecutionCancelled` | Execution cancelled by caller |
| `CouncilPolicyViolation` | Policy enforcement denied an execution or participant invocation |
| `CouncilSchemaValidationFailed` | Request or participant response failed schema validation |
| `CouncilMemberUnhealthy` | Member health check failed; circuit breaker state change |
| `CouncilExecutionIndexStalenessExceeded` | Index freshness SLO breach detected |

These events enable platform observability, audit, and automated remediation without coupling consumers to CouncilService internals.

### 6.6.9 Manager Space Interactions

CouncilService **SHALL NOT** directly invoke Manager Space components (Part 2). Its only Manager Space interaction is indirect, via the Event Space:

- It consumes CouncilManager's registration events.
- It consumes Policy Manager's policy events.
- It produces execution observability events consumed by platform managers (e.g., MonitoringManager, AuditManager, SecurityManager, QuotaManager).

This preserves the Manager Space / Event Space separation defined in Part 2.

### 6.6.10 Lifecycle

CouncilService lifecycle is defined by three states:

| State | Entry Condition | Exit Condition |
|-------|-----------------|----------------|
| **Bootstrapping** | Process start | Execution index built from event log and published |
| **Serving** | Index published, health checks passing | Shutdown signal or index corruption detected |
| **Degraded** | Dependency unavailable (event stream, policy service, auth service, member pool) | Dependency restored or graceful shutdown |

**Bootstrapping**: On startup, CouncilService **SHALL** reconstruct its execution index by consuming the registration event stream from the last known consistent position. It **SHALL NOT** enter Serving state until the index reflects all events up to the stream head.

**Serving**: CouncilService accepts executions, maintains index currency via event consumption, and emits observability events.

**Degraded**: If the event stream becomes unavailable, CouncilService **SHALL** continue serving from its last consistent index while emitting `CouncilExecutionIndexStalenessExceeded` events. If staleness exceeds a configured threshold, it **SHALL** transition to a safe mode (rejecting executions for councils not in index, or failing open/closed per policy domain configuration).

**Shutdown**: On termination signal, CouncilService **SHALL** drain in-flight executions (up to a configured grace period), flush pending observability events, and persist its index position for fast restart.

### 6.6.11 Ownership Boundaries

| Concern | Owner | CouncilService Role |
|---------|-------|-------------------|
| Council manifest | CouncilManager | Consumer (read-only projection) |
| Council protocol definition | CouncilManager | Consumer (exact enforcement) |
| Council member schema | CouncilManager | Consumer (exact enforcement) |
| Council member binding | CouncilManager | Consumer (routing target) |
| Execution policy | Policy Manager (Part 2) | Consumer (enforcement point) |
| Execution orchestration | Council member process | Orchestrator (dispatch, timeout, retry) |
| Member invocation result | Council member process | Transformer (normalization, validation) |
| Authentication credentials | Secret Manager (Part 2) | Consumer (injection at member binding) |
| Observability emission | CouncilService | Producer (canonical events) |
| Correlation identity | CouncilService | Generator / propagator |
| Execution Contract | CouncilService | Owner |
| Execution Index | CouncilService | Owner |
| Execution Lifecycle | CouncilService | Owner |
| Execution Coordination | CouncilService | Owner |
| Member Binding Lifecycle | CouncilService | Owner (per member pool) |

CouncilService **owns** the Execution Contract, the canonical council execution result contract, the Council Execution ErrorCode taxonomy, the correlation identity model, the execution index data structure, the member binding pools, the execution coordination logic, and the execution lifecycle management. It **does not own** council definitions, protocols, member schemas, member configurations, policy definitions, or authentication secrets — it consumes and enforces them.

### 6.6.12 Dependency Rules

| Dependency | Direction | Type | Rationale |
|------------|-----------|------|-----------|
| CouncilManager → CouncilService | **Forbidden** | — | Preserves Definition Plane purity |
| CouncilService → CouncilManager (events) | **Required** | Event subscription | Index currency |
| CouncilService → Policy Manager (events) | **Required** | Event subscription | Policy currency |
| CouncilService → Policy Manager | **Required** | Policy consumption | Execution policy enforcement |
| CouncilService → Secret Manager | **Required** | Credential consumption | Member credential management |
| CouncilService → Event Space | **Required** | Infrastructure | Event consumption/production |
| Engineering Service → CouncilService | **Required** | API invocation | Execution monopoly |
| AI Agent → CouncilService | **Required** | API invocation | Execution monopoly |
| Engineering Service → CouncilManager | **Forbidden** | — | Facade integrity |
| AI Agent → CouncilManager | **Forbidden** | — | Facade integrity |
| Engineering Service → Council Member | **Forbidden** | — | Member boundary enforcement |
| AI Agent → Council Member | **Forbidden** | — | Member boundary enforcement |
| Council Member → CouncilService | **None** | — | Members are opaque executables |

### 6.6.13 Communication Model

CouncilService communication follows the **Request–Response** and **Request–Stream** patterns over the **Event Space communication model** (Part 4). The Execution Contract is **protocol-agnostic** — it defines the logical interaction, not the wire protocol. Member protocols are implementation details internal to CouncilService.

#### Execution Model

```
Consumer → CouncilService → Council Members
         │                   │
         │      Execute      │
         │     (arguments)   │
         │                   │
         │◀─────────────────│
         │    Execution      │
         │      Result       │
         │                   │
```

CouncilService executes councils according to the execution semantics defined by CouncilManager. The consumer invokes the council through CouncilService's uniform execution contract. CouncilService coordinates participant invocations, manages execution lifecycle, applies policies, validates contracts, and returns the canonical execution result. The internal orchestration mechanics — participant sequencing, protocol interactions, debate or voting phases, consensus evaluation — are defined by the council's registered protocol in the Definition Plane and executed faithfully by CouncilService in the Execution Plane.

All executions traverse a fixed **pipeline** of architectural stages. Each stage either passes (enriching context) or fails (returning a typed error, aborting the pipeline). The pipeline is an architectural construct — its stages are responsibilities, not implementation modules.

#### Pipeline Stages (Architectural)

1. **Route** — Resolve council identifier to participant bindings, protocol binding, and authentication context; verify deprecation status.
2. **Authorize** — Verify caller identity, evaluate policy binding, check quotas (per consumer, per council, per member).
3. **Validate Request** — Validate arguments against council's declared input schema.
4. **Coordinate Execution** — Dispatch participant invocations per the execution semantics defined by the council's protocol; manage participant lifecycle; apply timeout, retry, circuit breaker per participant.
5. **Validate Responses** — Validate each participant response against declared output schema; enforce size limits.
6. **Normalize** — Aggregate participant responses into canonical Council Execution Result Envelope.
7. **Emit Observability** — Emit completion event, record metrics, update quota consumption.

For streaming councils, stages 4–6 operate incrementally per chunk, with a final completion chunk.

#### Cancellation Model

Callers **MAY** cancel in-flight executions. CouncilService **SHALL** propagate cancellation to all active participant invocations and **SHALL** emit a `CouncilExecutionCancelled` observability event. Cancellation **SHALL NOT** corrupt the execution index or affect other executions.

### 6.6.14 Security Responsibilities

CouncilService enforces security at the **execution boundary** and **member boundary**:

| Security Concern | CouncilService Responsibility |
|------------------|-----------------------------|
| Caller authentication | Verified at ingress (gateway); re-verified at CouncilService entry |
| Caller authorization | Policy evaluation against council's policy binding |
| Member authentication | Credential injection at member binding; mutual authentication where configured |
| Member identity verification | Identity validation per member protocol |
| Council isolation | Members execute in isolated processes; responses treated as untrusted input |
| Data protection | Request/response payloads validated against schemas; size limits enforced |
| Audit integrity | All executions and member invocations emit immutable audit events with correlation identity |
| Communication security | Member endpoints invoked over mutually authenticated channels |
| Credential isolation | Consumers never receive member credentials; injected only at member layer |
| Protocol validation | Strict member protocol compliance; malformed responses rejected |

CouncilService **SHALL NOT** delegate any of these responsibilities to callers or members.

### 6.6.15 Resource Responsibilities

| Resource | Responsibility |
|----------|----------------|
| Execution index memory | CouncilService owns lifecycle; bounded by council count, member count, protocol size, schema size |
| Event stream consumer position | CouncilService manages position tracking; consistent projection semantics |
| In-flight execution state | CouncilService tracks for timeout, cancellation, observability; bounded by concurrency limits |
| Member binding pools | CouncilService manages per-member pools; lifecycle tied to member registration state |
| Policy evaluation cache | CouncilService manages; invalidated on policy update events |
| Schema validator cache | CouncilService manages; keyed by schema identifier; invalidated on council/member update |
| Member protocol session state | CouncilService manages per-connection; includes initialization state, negotiated version |

Resource exhaustion **SHALL** trigger graceful degradation per Section 6.6.10, not catastrophic failure.

### 6.6.16 Failure Containment

Failure domains are strictly isolated by architectural boundary:

| Failure Domain | Containment Boundary |
|----------------|---------------------|
| Council member process crash | Affects only in-flight invocations to that member; index unchanged; other members proceed; execution adapts per protocol |
| Council member timeout | Affects only that member's phase; protocol-defined timeout handling applied; member health updated |
| Council member protocol violation | Affects only that member's phase; validation error recorded; member marked unhealthy; protocol adaptation per definition |
| Member binding failure | Affects only executions using that binding; pool replenished; health updated |
| Member authentication failure | Affects only that member's invocations; auth failure event emitted; no credential leakage |
| Schema validation failure (request) | Affects only that execution; validation error returned to caller |
| Schema validation failure (member response) | Affects only that member's phase; validation error recorded; member marked unhealthy |
| Event stream unavailability | Degraded mode: serve from last consistent index; emit staleness events |
| Policy service unavailability | Degraded mode: fail closed (deny) or fail open per policy domain configuration |
| Quota exhaustion | Affects only that consumer/council/member combination; other consumers/councils/members unaffected |

The execution index is **immutable per projection cycle** — it is reconstructed atomically from the event log and updated atomically. No council execution can corrupt it.

### 6.6.17 Architecture Decision Records

#### ADR-6.6.1: CouncilService as Execution Facade

**Status**: Accepted

**Context**: The Council Facade has two planes (Definition, Execution). The dependency direction between their owning components must be decided.

**Decision**: CouncilManager publishes events; CouncilService subscribes. Zero reverse dependency.

**Consequences**:
- Definition Plane remains pure — no execution concerns leak into CouncilManager.
- CouncilService can be independently versioned and substituted.
- CouncilService operates with bounded staleness (T_index_max).
- CouncilManager cannot query execution health directly (by design).

#### ADR-6.6.2: Publisher/Subscriber with CouncilManager

**Status**: Accepted

**Context**: Whether CouncilService should call CouncilManager APIs directly or consume events.

**Decision**: Event-driven subscription only. No synchronous API calls from CouncilService to CouncilManager.

**Consequences**:
- Temporal decoupling: CouncilService survives CouncilManager downtime.
- Failure isolation: CouncilManager failures don't cascade to execution.
- Scalability: Independent horizontal scaling.

#### ADR-6.6.3: Council Members as Untrusted

**Status**: Accepted

**Context**: Council members execute in external processes with heterogeneous implementations.

**Decision**: All member responses are untrusted. CouncilService validates every response against declared output schema, enforces size limits, and sanitizes errors.

**Consequences**:
- No member can inject malformed data into AI-OS trust domain.
- Schema violations are caught at facade boundary.
- Member crashes cannot corrupt execution index.

#### ADR-6.6.4: Protocol Abstraction

**Status**: Accepted

**Context**: Council protocols vary (debate, voting, consensus, custom). Consumers must not depend on protocol details.

**Decision**: CouncilService abstracts all protocol heterogeneity behind a uniform execution contract. Protocol semantics are defined in Definition Plane by CouncilManager; CouncilService executes them faithfully.

**Consequences**:
- Consumers see one execution interface regardless of council protocol.
- New protocols added via CouncilManager without facade changes.
- Protocol evolution isolated to Definition Plane.

#### ADR-6.6.5: Canonical Execution Result Contract

**Status**: Accepted

**Context**: How to unify heterogeneous council execution outcomes (consensus, deadlock, error, streaming) for consumers.

**Decision**: All executions return a **canonical council execution result contract** with variants: Success (with consensus outcome), Error, Streaming. The contract carries metadata (correlation ID, execution time, attempt count, policy decisions, participant statuses).

**Consequences**:
- Consumers handle one response model regardless of council protocol.
- Observability, retry logic, and error handling are uniform.
- Protocol authors cannot leak implementation-specific result formats.

#### ADR-6.6.6: Correlation Identity Propagation

**Status**: Accepted

**Context**: Distributed tracing across multi-participant executions requires end-to-end identity.

**Decision**: Correlation ID generated at ingress; propagated to all participant invocations via protocol metadata; emitted in all observability events.

**Consequences**:
- Full traceability from consumer request through all participants.
- Debugging and audit trails are complete.
- No consumer modification needed for tracing.

#### ADR-6.6.7: Index Staleness SLO

**Status**: Accepted

**Context**: Event-driven index projection introduces bounded staleness.

**Decision**: Maximum index staleness T_index_max is an architectural SLO. Breach triggers Degraded mode with explicit failure semantics.

**Consequences**:
- Measurable, configurable, alerted freshness guarantee.
- Consumers know maximum delay for new councils to become executable.
- Degraded mode behavior is explicit, not implicit.

#### ADR-6.6.8: Health Isolation per Member

**Status**: Accepted

**Context**: Member failures should not cascade across members or executions.

**Decision**: Member health state (circuit breaker, unhealthy flag) maintained per member. One member's failure does not affect other members' eligibility.

**Consequences**:
- Failure blast radius limited to single member.
- Healthy members continue serving during peer failures.
- Automatic recovery when member restores health.

#### ADR-6.6.9: Credential Injection at Member Layer

**Status**: Accepted

**Context**: Member credentials must not leak to consumers or execution logic.

**Decision**: Credentials injected at member binding during transport establishment. Never visible to callers, never in execution payloads, never in observability events.

**Consequences**:
- Credential rotation without consumer updates.
- No credential exposure in logs or traces.
- Secret Manager remains sole credential authority.

### 6.6.18 Conformance Requirements

A conforming CouncilService implementation **SHALL** satisfy all of the following:

#### Invariant Conformance
- [ ] **INV-6.6.1**: Zero dependency on CouncilManager APIs; consumes only registration event stream.
- [ ] **INV-6.6.2**: Participants have zero dependency on CouncilService internals; all treated as untrusted.
- [ ] **INV-6.6.3**: All Engineering Service and AI Agent executions route through CouncilService; no bypass path exists.
- [ ] **INV-6.6.4**: Execution index is read-only projection; no registration writes performed.
- [ ] **INV-6.6.5**: All execution policies enforced at CouncilService; none delegated to consumers or participants.
- [ ] **INV-6.6.6**: Participant failures cannot corrupt index or affect unrelated executions.
- [ ] **INV-6.6.7**: Index staleness ≤ T_index_max (measurable, configurable, alerted).
- [ ] **INV-6.6.8**: Input and response validation uses exact registered schemas; no coercion or transformation.
- [ ] **INV-6.6.9**: All executions return canonical council execution result contract; no participant-specific formats escape.
- [ ] **INV-6.6.10**: Correlation identity generated and propagated end-to-end; emitted in all observability signals.
- [ ] **INV-6.6.11**: Consumers cannot detect or depend on underlying participant protocol.
- [ ] **INV-6.6.12**: All participant responses validated against output schemas; size limits enforced; errors sanitized.
- [ ] **INV-6.6.13**: Declared execution semantics executed as defined by CouncilManager; participants cannot influence logic beyond declared roles.
- [ ] **INV-6.6.14**: Quota tracked and enforced per (consumer, council, member) tuple; no cross-contamination.

#### Event Space Conformance
- [ ] Consumes all CouncilManager registration event types in order.
- [ ] Consumes Policy Manager policy event types in order.
- [ ] Produces all execution observability event types.
- [ ] Event processing is idempotent and maintains consistent projection state.

#### Pipeline Conformance
- [ ] Pipeline stages execute in defined order with fail-fast semantics.
- [ ] Request validation occurs before execution coordination.
- [ ] Response validation occurs after participant response receipt.
- [ ] Timeout, retry, and circuit breaker policies applied per participant policy binding.
- [ ] Cancellation propagated to all active participants; index unaffected.

#### Lifecycle Conformance
- [ ] Bootstraps index from event log before entering Serving state.
- [ ] Enters Degraded mode on dependency loss; emits staleness events.
- [ ] Drains in-flight executions on shutdown within grace period.
- [ ] Preserves index state for fast restart.

#### Security Conformance
- [ ] Verifies caller authentication at entry.
- [ ] Evaluates authorization policy per council binding.
- [ ] Treats participant responses as untrusted; validates against output schema.
- [ ] Enforces request/response size limits.
- [ ] Invokes participants over mutually authenticated channels.
- [ ] Injects credentials at member binding layer only.

#### Observability Conformance
- [ ] Emits `CouncilExecutionStarted` and `CouncilExecutionCompleted`/`CouncilExecutionFailed` for every execution.
- [ ] Emits `CouncilExecutionCancelled` for every cancellation.
- [ ] Emits `CouncilPolicyViolation` for every policy denial.
- [ ] Emits `CouncilSchemaValidationFailed` for every validation failure.
- [ ] Emits metrics for execution count, duration, in-flight, errors, staleness, policy latency, validation latency, participant health, quota consumption.

#### Runtime Conformance
- [ ] Horizontally scalable without session affinity (execution index is read-only projection).
- [ ] Supports concurrent instantiation without coordination (parallel bootstrap capability).
- [ ] Health assessment distinguishes liveness, readiness, and index currency.

---

*End of Architecture Specification Part 6 — Step 6*