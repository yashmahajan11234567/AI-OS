# AI-OS Architecture Specification v1.0
## Part 4: Core Managers Architecture (Continued)

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 4.6 WorkflowManager

#### 4.6.1 Purpose

WorkflowManager SHALL serve as the **sole governance authority** for workflow execution within the Hermes Kernel. It SHALL own workflow lifecycle, scheduling, cancellation, timeouts, retry, nested workflows, and coordination.

#### 4.6.2 Responsibilities

WorkflowManager SHALL be responsible for:

1. **Workflow Execution Governance** — Authoritative control over workflow instance lifecycle from submission to completion
2. **Workflow Lifecycle** — State machine for workflow instances (PENDING, SCHEDULED, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED, COMPENSATING)
3. **Scheduling** — Placement of workflow steps on available capacity; coordination with ResourceManager
4. **Cancellation** — Cooperative and forced cancellation of running workflows
5. **Timeouts** — Enforcement of step-level and workflow-level timeouts
6. **Retry** — Configurable retry policies with backoff, jitter, and circuit breaking
7. **Nested Workflows** — Management of parent-child workflow relationships, isolation, and propagation
8. **Coordination** — Synchronization, branching, joining, and event-driven continuation

#### 4.6.3 Workflow Execution

WorkflowManager SHALL execute workflows as **directed acyclic graphs (DAGs)** of steps.

**Workflow Definition:**
- Steps with explicit dependencies (edges)
- Each step: capability invocation, inline logic, or sub-workflow
- Resource requirements per step (CPU, memory, GPU, LLM quota)
- Timeout per step and workflow-level
- Retry policy per step
- Compensation (saga) actions for rollback

**Execution Model:**
1. Workflow submitted via EventBus (WorkflowSubmitEvent)
2. WorkflowManager validates definition, resolves capabilities (CapabilityManager), checks resources (ResourceManager), authorizes (SecurityManager)
3. WorkflowManager creates workflow instance, assigns ID, emits WorkflowCreatedEvent
4. Scheduler places ready steps (dependencies met) on execution queue
5. Step execution: invoke capability via CapabilityManager; capture result/artifact
6. On step completion: evaluate downstream readiness; schedule next steps
7. On workflow completion: emit WorkflowCompletedEvent; store artifacts via StorageManager
8. On failure: execute compensation; emit WorkflowFailedEvent

**Invariant:** WorkflowManager SHALL NOT execute step logic directly. All step execution SHALL be via CapabilityManager resolution.

#### 4.6.4 Workflow Lifecycle

Workflow instance state machine:

| State | Description | Valid Transitions |
|-------|-------------|-------------------|
| **PENDING** | Submitted, awaiting validation | → SCHEDULED, → CANCELLED |
| **SCHEDULED** | Validated, awaiting resources | → RUNNING, → CANCELLED |
| **RUNNING** | At least one step executing | → PAUSED, → COMPLETED, → FAILED, → CANCELLED |
| **PAUSED** | Suspended (admin, resource pressure) | → RUNNING, → CANCELLED |
| **COMPLETED** | All steps succeeded | (terminal) |
| **FAILED** | Step failed, compensation done | → CANCELLED (terminal) |
| **CANCELLED** | Terminated before completion | (terminal) |
| **COMPENSATING** | Executing saga compensation | → FAILED, → CANCELLED |

**Invariant:** Every state transition SHALL emit WorkflowStateChangedEvent with timestamp, previous state, new state, and reason.

#### 4.6.5 Scheduling

WorkflowManager SHALL schedule steps based on:

1. **Readiness** — All upstream dependencies completed successfully
2. **Resources** — ResourceManager confirms availability for step requirements
3. **Priority** — Workflow priority (configurable per submission)
4. **Fairness** — Prevent starvation (weighted fair queuing across tenants/workflows)
5. **Affinity** — Placement preferences (GPU, zone, data locality)

**Scheduling Decisions** SHALL be logged for observability.

#### 4.6.6 Cancellation

WorkflowManager SHALL support two cancellation modes:

| Mode | Behavior |
|------|----------|
| **Cooperative** | Emit CancellationRequestedEvent to running steps; steps check cancellation token; graceful shutdown; execute compensation |
| **Forced** | After grace period (configurable): terminate step execution; force resource release; execute compensation |

**Invariant:** Cancellation SHALL always execute compensation actions for completed steps (saga pattern).

#### 4.6.7 Timeouts

WorkflowManager SHALL enforce timeouts at two levels:

| Level | Scope | Enforcement |
|-------|-------|-------------|
| **Step Timeout** | Individual step execution | Hard limit; on expiry: mark step failed; trigger retry or compensation |
| **Workflow Timeout** | Entire workflow wall-clock | Hard limit; on expiry: initiate cancellation (cooperative then forced) |

**Timeout Configuration:** Per-step and per-workflow; inheritable from workflow template; overrideable at submission.

#### 4.6.8 Retry

WorkflowManager SHALL support configurable retry policies:

| Policy Parameter | Description |
|------------------|-------------|
| **Max Attempts** | Maximum retry count (default: 3) |
| **Backoff Strategy** | Exponential, linear, fixed (default: exponential) |
| **Base Delay** | Initial delay (default: 1s) |
| **Max Delay** | Cap on delay (default: 60s) |
| **Jitter** | Randomization factor (default: 0.1) |
| **Retryable Errors** | Error classification for retry (default: transient only) |
| **Circuit Breaker** | Open after N failures; half-open probe; close on success |

**Retry Execution:** Retries SHALL be scheduled as new step attempts; original attempt marked RETRYING.

#### 4.6.9 Nested Workflows

WorkflowManager SHALL support parent-child workflow relationships:

| Aspect | Behavior |
|--------|----------|
| **Invocation** | Parent step invokes sub-workflow via CapabilityManager (capability type: workflow) |
| **Isolation** | Child has own state machine, resources, timeout; failure does not auto-fail parent |
| **Propagation** | Parent may configure: wait for child, fire-and-forget, rollback on child failure |
| **Context** | Child inherits parent's security context (subject to policy); own resource allocation |
| **Observability** | Correlation ID links parent and child traces |

**Invariant:** Nested workflow depth SHALL be bounded (configurable max, default: 10).

#### 4.6.10 Coordination

WorkflowManager SHALL provide coordination primitives:

| Primitive | Description |
|-----------|-------------|
| **Join** | Wait for multiple parallel branches to complete |
| **Branch** | Split into parallel execution paths |
| **Signal** | Event-driven continuation (wait for external event) |
| **Barrier** | Synchronize multiple workflow instances |
| **Aggregate** | Collect results from dynamic fan-out |

**Event-Driven Continuation:** Steps may emit WaitForEventEvent; WorkflowManager suspends workflow until matching EventBus event arrives.

#### 4.6.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: WorkflowCreatedEvent, WorkflowStateChangedEvent, WorkflowStepStartedEvent, WorkflowStepCompletedEvent, WorkflowCompletedEvent, WorkflowFailedEvent, WorkflowCancelledEvent. Consumes: WorkflowSubmitEvent, WorkflowCancelEvent, WorkflowPauseEvent, WorkflowResumeEvent, CapabilityInvocationResultEvent, ResourceReleasedEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.workflow` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.workflow.*` configuration |
| **CapabilityManager** | Outbound | Invokes `capability.invoke(capabilityId, input)`; receives async result |
| **ResourceManager** | Outbound | Invokes `resources.reserve(requirements)`, `resources.release(reservationId)` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, workflowAction, workflowId)` |
| **StorageManager** | Outbound | Invokes `artifact.store()`, `artifact.retrieve()` |
| **HealthManager** | Outbound | Reports workflow health; invokes `health.readiness(capability)` |
| **ObservabilityManager** | Outbound | Emits workflow metrics, traces |

**Forbidden:** Direct step execution. All capability invocations SHALL go through CapabilityManager.

#### 4.6.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Step capability unavailable | Retry per policy; if exhausted: mark step failed; trigger compensation |
| Step timeout | Mark step failed; trigger retry or compensation |
| Resource exhaustion mid-workflow | Pause workflow; emit WorkflowPausedEvent; resume when resources available |
| CapabilityManager failure | Pause affected workflows; emit WorkflowManagerDegradedEvent |
| StorageManager failure (artifacts) | Queue artifact writes; retry; if persistent: mark workflow degraded |
| SecurityManager denial | Mark workflow failed; emit WorkflowAuthorizationFailedEvent |
| Nested workflow failure | Per parent propagation config: fail, compensate, or continue |

**Invariant:** WorkflowManager SHALL never leave a workflow in an undefined state. Every failure path leads to a defined terminal state (COMPLETED, FAILED, CANCELLED) with compensation executed.

#### 4.6.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom scheduling algorithms (pluggable)
- Custom coordination primitives
- Custom retry policies (per workflow template)
- Custom compensation action types
- Custom timeout enforcement (e.g., CPU-time vs wall-clock)

**Extension Constraints** (MUST be preserved):
- DAG execution model SHALL be preserved
- Saga compensation SHALL be mandatory for stateful steps
- EventBus as sole coordination mechanism SHALL be preserved
- CapabilityManager for all step execution SHALL be preserved
- Nested workflow depth bound SHALL be enforced

**Forbidden Extensions:**
- Direct capability invocation bypassing CapabilityManager
- Shared state between sibling workflows (except via artifacts)
- Unbounded recursion in nested workflows
- Skipping compensation for completed steps

#### 4.6.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **DAG execution** | No cycles in executed step graph; topological order preserved |
| **Saga compensation** | Every completed step in failed workflow has compensation executed |
| **Resource accounting** | Every step execution has ResourceManager reservation |
| **Capability mediation** | Zero direct capability invocations observed |
| **State machine completeness** | Every workflow instance reaches terminal state |
| **Correlation integrity** | All nested workflow events carry parent correlation ID |

#### 4.6.15 Conformance

A WorkflowManager implementation SHALL be conformant IFF:

1. **Static:** Passes workflow schema validation, DAG validation, compensation completeness validation
2. **Runtime:** Workflows execute per DAG; compensation executes on failure; timeouts enforced; retries per policy; nested workflows isolated
3. **Architectural:** No direct step execution; all capabilities via CapabilityManager; all resources via ResourceManager; all coordination via EventBus

---

### 4.7 SecurityManager

#### 4.7.1 Purpose

SecurityManager SHALL serve as the **sole enforcement authority** for all security policies within the Hermes Kernel. It SHALL own authentication, authorization, policy enforcement, secret handling, audit coordination, identity management, and trust boundaries.

#### 4.7.2 Responsibilities

SecurityManager SHALL be responsible for:

1. **Authentication** — Verification of principal identity for all kernel interactions
2. **Authorization** — Evaluation of access control decisions for all protected operations
3. **Policy Enforcement** — Centralized policy decision and enforcement point (PDP/PEP)
4. **Secret Handling** — Secure storage, rotation, injection, and access control for secrets
5. **Audit Coordination** — Emission of security audit events for all security-relevant actions
6. **Identity Management** — Principal lifecycle, authentication methods, credential management
7. **Trust Boundaries** — Definition and enforcement of trust zones, network policies, capability boundaries

#### 4.7.3 Authentication

SecurityManager SHALL authenticate all principals before authorization:

| Principal Type | Authentication Method |
|----------------|----------------------|
| **Human Operators** | OIDC/OAuth2, mTLS, SSH certificates, WebAuthn |
| **Services** | mTLS, SPIFFE/SPIRE, JWT (short-lived), API keys (deprecated) |
| **Workflows** | Short-lived workload identity (SPIFFE), capability tokens |
| **Core Managers** | Kernel-internal identity (bootstrapped at init) |
| **External Systems** | Mutual TLS, signed requests, pre-shared keys (rotated) |

**Authentication Flow:**
1. Principal presents credentials to SecurityManager (via EventBus or direct for kernel-internal)
2. SecurityManager validates credentials against IdentityProvider (Core Component, Part 3)
3. On success: SecurityManager issues authenticated context (principal ID, claims, expiry, trust level)
4. On failure: SecurityManager emits AuthenticationFailedEvent; denies request

**Invariant:** No authorization decision SHALL be made without successful authentication.

#### 4.7.4 Authorization

SecurityManager SHALL authorize all protected operations using **Attribute-Based Access Control (ABAC)**:

| Decision Input | Source |
|----------------|--------|
| **Principal** | Authenticated context (ID, roles, attributes, trust level) |
| **Action** | Operation being attempted (capability invocation, state transition, storage access, etc.) |
| **Resource** | Target resource (namespace, workflow, capability, secret, etc.) |
| **Context** | Request metadata (time, network zone, certification level, etc.) |

**Policy Language:** Declarative, versioned, stored in ConfigurationAuthority. Policies SHALL support:
- Allow/deny with obligations
- Condition evaluation (CEL or equivalent)
- Data-dependent decisions (resource attributes)
- Delegation and impersonation constraints

**Authorization Flow:**
1. Caller (manager or service) invokes `security.authorize(principal, action, resource, context)`
2. SecurityManager evaluates applicable policies in priority order
3. SecurityManager returns Decision: ALLOW, DENY, or CHALLENGE (step-up auth)
4. SecurityManager emits AuthorizationDecisionEvent (audit)

**Invariant:** Authorization SHALL be the single enforcement point. No manager SHALL implement custom authorization logic.

#### 4.7.5 Policy Enforcement

SecurityManager SHALL enforce policies at **enforcement points**:

| Enforcement Point | Protected Operations |
|-------------------|---------------------|
| **Capability Invocation** | `capability.invoke()` — principal must have `capability.invoke` on target |
| **State Transition** | `state.transition()` — principal must have `state.transition` on target category |
| **Storage Access** | `storage.read/write/delete` — principal must have `storage.*` on namespace |
| **Workflow Control** | `workflow.submit/cancel/pause` — principal must have `workflow.*` on workflow |
| **Secret Access** | `secret.get/set/rotate` — principal must have `secret.*` on secret path |
| **Configuration** | `config.read/write` — principal must have `config.*` on key path |
| **Manager Admin** | `manager.restart/configure` — principal must have `kernel.admin` |

**Enforcement Modes:**
- **Blocking** (default): Request waits for decision
- **Non-blocking**: Decision cached; async re-evaluation on policy change
- **Audit-only**: Log decision but allow (for policy testing)

#### 4.7.6 Secret Handling

SecurityManager SHALL govern all secrets:

| Secret Type | Examples | Handling |
|-------------|----------|----------|
| **Static Secrets** | API keys, database passwords | Encrypted at rest; injected via environment/files at runtime; never logged |
| **Dynamic Secrets** | Database credentials, cloud tokens | Generated on-demand; short TTL; auto-rotated |
| **Certificates** | mTLS certs, signing keys | Managed via PKI; auto-renewed before expiry |
| **Encryption Keys** | Data encryption keys, KEK | HSM-backed; never exported; key handles only |
| **Workflow Secrets** | Per-workflow credentials | Scoped to workflow; auto-revoked on completion |

**Secret Operations:**
- `secret.create(path, type, policy)` — Create secret with policy
- `secret.get(handle)` — Retrieve secret value (audited)
- `secret.rotate(path)` — Rotate secret per policy
- `secret.revoke(path)` — Immediately revoke

**Invariant:** SecurityManager SHALL never log secret values. All secret access SHALL be audited.

#### 4.7.7 Audit Coordination

SecurityManager SHALL emit **SecurityAuditEvent** for all security-relevant actions:

| Event Category | Examples |
|----------------|----------|
| **Authentication** | Login success/failure, MFA challenge, token issuance/refresh/revocation |
| **Authorization** | Allow/deny/challenge decisions with full context |
| **Secret Access** | Create, read, rotate, revoke, injection |
| **Policy Changes** | Policy create/update/delete, version activation |
| **Identity Changes** | Principal create/update/delete, role assignment, credential rotation |
| **Trust Boundary** | Zone changes, network policy updates, certificate validation |

**Audit Event Structure:** Timestamp, principal, action, resource, decision, policy version, correlation ID, request context.

**Invariant:** SecurityAuditEvent SHALL be emitted to EventBus with `audit` namespace. ObservabilityManager SHALL ensure durable delivery to audit store (Part 4 §4.11).

#### 4.7.8 Identity

SecurityManager SHALL manage principal identity lifecycle:

| Operation | Description |
|-----------|-------------|
| **Provision** | Create principal identity (human, service, workflow) |
| **Authenticate** | Bind credentials to principal |
| **Attribute** | Assign/modify attributes (roles, groups, trust level) |
| **Delegate** | Create delegation token with constrained scope |
| **Revoke** | Invalidate all credentials and tokens for principal |
| **Archive** | Soft-delete; retain for audit; prevent reuse |

**Identity Source of Truth:** IdentityProvider (Core Component, Part 3) for authentication; SecurityManager for authorization attributes.

#### 4.7.9 Trust Boundaries

SecurityManager SHALL define and enforce trust boundaries:

| Boundary Type | Enforcement |
|---------------|-------------|
| **Network Zones** | Ingress/egress policies per zone; mTLS required cross-zone |
| **Capability Boundaries** | Capability invocation restricted by trust level |
| **Data Classification** | Storage namespace access by data classification |
| **Workflow Isolation** | Workflow tenants isolated unless explicit sharing |
| **Manager Boundaries** | Core Managers operate at highest trust; services at lower |

**Trust Levels:** SYSTEM (kernel managers), PRIVILEGED (platform services), STANDARD (user services), UNTRUSTED (external).

#### 4.7.10 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: SecurityAuditEvent, AuthenticationFailedEvent, AuthorizationDecisionEvent, SecretRotatedEvent, PolicyUpdatedEvent, TrustBoundaryViolationEvent. Consumes: AuthenticateRequestEvent, AuthorizeRequestEvent, SecretRequestEvent, PolicyChangeEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.security` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.security.*` configuration; policy definitions |
| **IdentityProvider** | Outbound | Invokes `identity.validate(credentials)`, `identity.getPrincipal(id)` |
| **CapabilityManager** | Inbound | Receives `capability.invoke` authorization requests |
| **StateManager** | Inbound | Receives `state.transition` authorization requests |
| **StorageManager** | Inbound | Receives `storage.*` authorization requests; provides key handles |
| **WorkflowManager** | Inbound | Receives `workflow.*` authorization requests |
| **ResourceManager** | Inbound | Receives `resources.reserve` authorization requests |
| **ObservabilityManager** | Outbound | Emits security metrics (auth latency, authz decisions, violations) |

**Forbidden:** Any manager or service performing authentication or authorization independently. All security decisions SHALL go through SecurityManager.

#### 4.7.11 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| IdentityProvider unavailable | Cache recent authentications (short TTL); deny new; emit SecurityDegradedEvent |
| Policy evaluation error | Default deny; emit SecurityPolicyErrorEvent; alert |
| Secret rotation failure | Retry; alert; do not revoke old until new confirmed |
| HSM unavailable | Queue key operations; emit SecurityHSMUnavailableEvent |
| Audit event loss | Buffer locally; retry with backoff; emit SecurityAuditBufferFullEvent if persistent |
| Policy conflict (allow+deny) | Default deny; emit SecurityPolicyConflictEvent |

**Invariant:** SecurityManager SHALL fail closed (deny) on any internal failure. Availability degradation SHALL NOT weaken enforcement.

#### 4.7.12 Extension Rules

**Extension Points** (MAY be extended):
- Custom authentication methods (pluggable validators)
- Custom policy language (if CEL-compatible)
- Custom obligation handlers (post-authorization actions)
- Custom trust boundary types
- Custom secret types with custom rotation logic

**Extension Constraints** (MUST be preserved):
- ABAC model SHALL be preserved
- Single enforcement point SHALL be preserved
- Fail-closed behavior SHALL be preserved
- Audit completeness SHALL be preserved
- IdentityProvider as authn source SHALL be preserved

**Forbidden Extensions:**
- Bypassing authorization for "internal" calls
- Caching allow decisions beyond TTL
- Logging secret values in any form
- Custom encryption without SecurityManager coordination

#### 4.7.13 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single enforcement point** | Zero authorization decisions outside SecurityManager |
| **Fail-closed** | All induced failures result in deny decisions |
| **Audit completeness** | Every protected operation has SecurityAuditEvent |
| **Secret non-logging** | Zero secret values in any log/observability output |
| **Policy versioning** | Every decision references policy version |
| **Trust boundary enforcement** | No cross-boundary access without explicit policy |

#### 4.7.14 Conformance

A SecurityManager implementation SHALL be conformant IFF:

1. **Static:** Passes policy language validation, trust boundary configuration validation, secret policy validation
2. **Runtime:** All authn/authz decisions correct per policy; secrets managed per policy; audit events complete; fail-closed under failure
3. **Architectural:** No independent authn/authz; all via SecurityManager; EventBus for audit; IdentityProvider for authn source

---

### 4.8 CapabilityManager

#### 4.8.1 Purpose

CapabilityManager SHALL serve as the **sole registry and routing authority** for all capabilities within the Hermes Kernel. It SHALL own capability registration, discovery, resolution, routing, version compatibility, facade interaction, provider selection, and conflict resolution.

#### 4.8.2 Responsibilities

CapabilityManager SHALL be responsible for:

1. **Capability Registration** — Registration of capability providers with metadata, contracts, and health
2. **Discovery** — Query and enumeration of available capabilities by type, interface, tags
3. **Resolution** — Binding of capability requests to specific provider instances
4. **Routing** — Direction of invocation requests to selected providers
5. **Version Compatibility** — Enforcement of semantic version compatibility between facades and providers
6. **Facade Interaction** — Management of capability facades (stable interfaces) and provider implementations
7. **Provider Selection** — Load balancing, affinity, priority, and policy-based selection
8. **Conflict Resolution** — Handling of duplicate registrations, version conflicts, capability overlaps

#### 4.8.3 Capability Registration

CapabilityManager SHALL maintain a **Capability Registry** with entries:

| Field | Description |
|-------|-------------|
| **Capability ID** | Globally unique identifier (e.g., `ai-os.llm.inference.v1`) |
| **Facade** | Interface definition (schema, version, stability) |
| **Provider ID** | Unique provider instance identifier |
| **Provider Metadata** | Version, capabilities, resource profile, health endpoint, tags |
| **Contract** | Input/output schemas, SLOs, error definitions, deprecation policy |
| **Lifecycle State** | REGISTERING, ACTIVE, DEPRECATED, DRAINING, REMOVED |
| **Security Context** | Required trust level, authentication, authorization policy |
| **Resource Profile** | CPU, memory, GPU, network, LLM quota requirements |

**Registration Flow:**
1. Provider (service or manager) emits CapabilityRegisterEvent
2. CapabilityManager validates facade contract, version, metadata
3. CapabilityManager checks for conflicts (Section 4.8.10)
4. CapabilityManager registers provider; emits CapabilityRegisteredEvent
5. Provider begins health reporting via HealthManager

**Invariant:** No capability SHALL be invocable before CapabilityRegisteredEvent is emitted.

#### 4.8.4 Discovery

CapabilityManager SHALL support discovery queries:

| Query Type | Parameters | Returns |
|------------|------------|---------|
| **By Facade** | Facade ID, version range | All compatible providers |
| **By Tag** | Tag selector (key=value, expressions) | Matching providers |
| **By Resource** | Resource requirements (GPU, memory) | Providers meeting requirements |
| **By Health** | Minimum health level | Healthy providers only |
| **By Security** | Required trust level | Providers meeting trust level |

**Discovery Result:** List of provider summaries (ID, version, health, location, resource profile).

**Invariant:** Discovery SHALL only return ACTIVE providers. DEPRECATED providers SHALL be excluded unless explicitly requested.

#### 4.8.5 Resolution

CapabilityManager SHALL resolve invocation requests to providers:

**Resolution Input:** Capability ID (or facade + version), input payload, caller context (principal, workflow, priority), routing hints.

**Resolution Algorithm:**
1. Filter providers by facade compatibility (semver)
2. Filter by caller authorization (SecurityManager)
3. Filter by resource availability (ResourceManager)
4. Filter by health (HealthManager)
5. Apply selection policy (Section 4.8.7)
6. Return selected provider ID + routing information

**Resolution Result:** Provider endpoint, capability version, correlation ID, timeout, retry policy.

**Invariant:** Resolution SHALL be deterministic given same inputs and registry state.

#### 4.8.6 Routing

CapabilityManager SHALL route invocations:

| Routing Mode | Description |
|--------------|-------------|
| **Direct** | Caller invokes provider directly using returned endpoint |
| **Proxied** | CapabilityManager proxies request (for authz, observability, transformation) |
| **Async** | Request queued; result via EventBus (for long-running) |
| **Streaming** | Bidirectional streaming for streaming capabilities |

**Routing Responsibilities:**
- Inject correlation IDs
- Enforce timeouts
- Apply retry policy (from facade contract)
- Emit CapabilityInvocationEvent (observability)
- Handle provider failures (circuit breaker, failover)

#### 4.8.7 Version Compatibility

CapabilityManager SHALL enforce **semantic versioning (SemVer)** compatibility:

| Compatibility Rule | Facade → Provider |
|--------------------|-------------------|
| **Exact Match** | Facade `1.2.3` → Provider `1.2.3` |
| **Compatible** | Facade `^1.2.3` → Provider `1.2.x` (patch) |
| **Minor Compatible** | Facade `~1.2.3` → Provider `1.x.x` (minor+patch) |
| **Major Incompatible** | Facade `1.x.x` ↛ Provider `2.x.x` (blocked) |

**Deprecation Handling:**
- DEPRECATED providers: excluded from resolution unless caller opts in
- Deprecation timeline: announced → grace period (configurable) → removal
- Migration: CapabilityManager SHALL emit CapabilityDeprecatedEvent with migration guidance

#### 4.8.8 Facade Interaction

CapabilityManager SHALL manage **facades** (stable interfaces):

| Facet | Responsibility |
|-------|----------------|
| **Facade Definition** | Schema (input/output), version, stability (EXPERIMENTAL, STABLE, DEPRECATED), owner |
| **Facade Registry** | Global registry of facades; version history; deprecation schedule |
| **Contract Validation** | Provider registration validates against facade schema |
| **Compatibility Matrix** | Published matrix of facade versions ↔ provider versions |
| **Mock/Stub Support** | Test facades for development (never in OPERATIONAL) |

**Invariant:** Facades SHALL be owned by a single team. Facade evolution SHALL follow SemVer.

#### 4.8.9 Provider Selection

CapabilityManager SHALL select providers using configurable policies:

| Policy | Description |
|--------|-------------|
| **Round Robin** | Distribute evenly across healthy providers |
| **Least Loaded** | Select provider with lowest current utilization |
| **Priority** | Providers with priority weight; higher weight preferred |
| **Affinity** | Prefer provider in same zone, with cached data, same GPU type |
| **Cost-Aware** | Prefer lower-cost providers (spot, reserved) when SLO permits |
| **Canary** | Route small percentage to new version |

**Policy Composition:** Policies SHALL compose (e.g., priority → least loaded → affinity). ConfigurationAuthority defines policy per capability or globally.

#### 4.8.10 Conflict Resolution

CapabilityManager SHALL resolve conflicts:

| Conflict Type | Resolution |
|---------------|------------|
| **Duplicate Provider ID** | Reject registration; emit CapabilityConflictEvent |
| **Same Facade, Same Version** | Allow multiple (load balanced); require distinct provider IDs |
| **Same Facade, Overlapping Versions** | Allow; resolution picks highest compatible |
| **Contract Mismatch** | Reject registration; provider must match facade schema |
| **Resource Profile Mismatch** | Warn; allow but resolution filters by actual resources |
| **Security Context Mismatch** | Reject if provider requires higher trust than facade declares |

**Invariant:** Conflicts SHALL be detected at registration time. No runtime surprises.

#### 4.8.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: CapabilityRegisteredEvent, CapabilityDeprecatedEvent, CapabilityRemovedEvent, CapabilityInvocationEvent, CapabilityConflictEvent. Consumes: CapabilityRegisterEvent, CapabilityDeregisterEvent, CapabilityInvokeEvent, CapabilityDiscoverEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.capability` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.capability.*` configuration; selection policies |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, capability.invoke, capabilityId)` |
| **ResourceManager** | Outbound | Invokes `resources.checkAvailability(profile)` |
| **HealthManager** | Outbound | Invokes `health.readiness(providerId)`; subscribes to health changes |
| **WorkflowManager** | Inbound | Receives `capability.invoke()` for workflow steps |
| **ObservabilityManager** | Outbound | Emits capability metrics (latency, errors, throughput, selection) |

**Forbidden:** Direct provider invocation bypassing CapabilityManager resolution. All capability calls SHALL go through CapabilityManager.

#### 4.8.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| No compatible provider | Emit CapabilityUnavailableEvent; fail invocation |
| Provider health check failure | Mark provider UNHEALTHY; exclude from resolution; emit CapabilityProviderUnhealthyEvent |
| Provider invocation timeout | Retry per facade retry policy; circuit breaker on repeated failure |
| Provider returns error | Classify error (retryable/non-retryable); retry or fail per policy |
| Registry corruption | Rebuild from ServiceRegistry; emit CapabilityRegistryRecoveredEvent |
| Version incompatibility | Emit CapabilityVersionConflictEvent; fail resolution |

**Invariant:** CapabilityManager SHALL never route to an UNHEALTHY provider. Circuit breaker SHALL open after configurable failure threshold.

#### 4.8.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom selection policies (pluggable)
- Custom routing modes (e.g., gRPC, HTTP, message queue)
- Custom contract validation (beyond schema)
- Custom conflict resolution rules
- Custom facade stability levels

**Extension Constraints** (MUST be preserved):
- Single registry authority SHALL be preserved
- SemVer compatibility SHALL be preserved
- Facade ownership SHALL be preserved
- SecurityManager authorization SHALL be mandatory
- HealthManager health checks SHALL be mandatory

**Forbidden Extensions:**
- Provider self-registration without validation
- Bypassing version compatibility
- Direct provider references in callers
- Unregistered capability invocation

#### 4.8.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single registry** | All capability registrations visible in CapabilityManager registry |
| **SemVer enforcement** | No resolution of incompatible major versions |
| **Authorization gate** | Zero invocations without SecurityManager allow |
| **Health gating** | Zero routes to UNHEALTHY providers |
| **Facade ownership** | Each facade has exactly one owning team |
| **No direct invocation** | Zero capability invocations bypassing CapabilityManager |

#### 4.8.15 Conformance

A CapabilityManager implementation SHALL be conformant IFF:

1. **Static:** Passes facade schema validation, SemVer compatibility matrix validation, policy configuration validation
2. **Runtime:** Registrations validated; discovery accurate; resolution deterministic; routing observes policies; conflicts detected
3. **Architectural:** Single registry; all invocations mediated; EventBus for events; SecurityManager for authz; HealthManager for health

---

### 4.9 ResourceManager

#### 4.9.1 Purpose

ResourceManager SHALL serve as the **sole accounting and enforcement authority** for all computational resources within the Hermes Kernel. It SHALL own resource accounting (CPU, memory, disk, network, GPU, LLM quotas), reservations, limits, and backpressure.

#### 4.9.2 Responsibilities

ResourceManager SHALL be responsible for:

1. **Resource Accounting** — Real-time tracking of resource allocation, usage, and availability across all resource types
2. **CPU Accounting** — Core allocation, usage tracking, throttling
3. **Memory Accounting** — Allocation tracking, OOM prevention, swap management
4. **Disk Accounting** — Volume allocation, usage, IOPS, throughput
5. **Network Accounting** — Bandwidth allocation, connection tracking, egress/ingress quotas
6. **GPU Accounting** — Device allocation, memory, compute units, MIG slices
7. **LLM Quota Accounting** — Token budgets, request rates, model-specific quotas
8. **Reservations** — Advance reservation of resources for workflows/capabilities
9. **Limits** — Hard and soft limits per principal, workflow, capability, namespace
10. **Backpressure** — Signaling and enforcement when resources exhausted

#### 4.9.3 Resource Accounting

ResourceManager SHALL maintain a **Resource Ledger** for each resource type:

| Resource Type | Unit | Accounting Granularity |
|---------------|------|------------------------|
| **CPU** | Millicores (mCPU) | Per reservation |
| **Memory** | Bytes | Per reservation |
| **Disk** | Bytes, IOPS, throughput (MB/s) | Per volume |
| **Network** | Mbps, connections | Per interface/zone |
| **GPU** | Device, memory (bytes), compute % | Per device/slice |
| **LLM Quota** | Tokens (input+output), requests | Per model, per principal |

**Accounting Principles:**
- **Attribution** — Every allocation attributed to a principal (workflow, capability, service, manager)
- **Hierarchy** — Nested allocations (workflow → step → capability) roll up to parent
- **Real-time** — Ledger reflects current state within 100ms
- **Auditable** — All allocation/release events emitted to EventBus

#### 4.9.4 Reservations

ResourceManager SHALL support **advance reservations**:

| Reservation Type | Use Case | Lifetime |
|------------------|----------|----------|
| **Workflow Reservation** | Full workflow resource needs | Workflow duration |
| **Step Reservation** | Single capability invocation | Step duration |
| **Capability Reservation** | Provider capacity guarantee | Configurable TTL |
| **Maintenance Reservation** | Kernel operations (compaction, backup) | Operation duration |

**Reservation Protocol:**
1. Caller invokes `resources.reserve(requirements, holder, ttl)`
2. ResourceManager checks availability against limits and current usage
3. If available: atomically deduct from available; emit ResourceReservedEvent; return reservation ID
4. If unavailable: queue request (if waitable) or reject with ResourceUnavailableEvent
5. On completion: caller invokes `resources.release(reservationId)`; ResourceManager returns to available

**Invariant:** Reservations SHALL be atomic. Partial reservations SHALL NOT occur.

#### 4.9.5 Limits

ResourceManager SHALL enforce limits at multiple scopes:

| Scope | Limit Types | Enforcement |
|-------|-------------|-------------|
| **Global** | Total cluster capacity | Hard; never exceeded |
| **Namespace** | Per Kubernetes namespace equivalent | Hard; quota enforcement |
| **Principal** | Per user, service, workflow | Hard + soft (warning) |
| **Capability** | Per capability type | Soft; backpressure |
| **Workflow** | Per workflow template | Hard; defined at submit |

**Limit Configuration:** Via ConfigurationAuthority; versioned; changes take effect on next reservation.

#### 4.9.6 Backpressure

ResourceManager SHALL signal and enforce backpressure:

| Signal | Trigger | Action |
|--------|---------|--------|
| **Soft Limit Warning** | Usage > 80% of limit | Emit ResourcePressureEvent; callers may throttle |
| **Hard Limit Reached** | Usage = limit | Reject new reservations; emit ResourceExhaustedEvent |
| **Critical Pressure** | Usage > 95% + queue depth > threshold | Emit ResourceCriticalEvent; LifecycleManager may degrade kernel |
| **OOM Imminent** | Memory available < reserve | Trigger emergency eviction; emit ResourceOOMImminentEvent |

**Backpressure Enforcement:**
- WorkflowManager pauses scheduling on ResourcePressureEvent
- CapabilityManager rejects invocations on ResourceExhaustedEvent
- LifecycleManager transitions to DEGRADED on ResourceCriticalEvent

#### 4.9.7 LLM Quota Accounting

ResourceManager SHALL provide specialized accounting for LLM resources:

| Quota Dimension | Description |
|-----------------|-------------|
| **Token Budget** | Total tokens (input+output) per period (day, month) |
| **Request Rate** | Requests per minute/hour |
| **Model-Specific** | Separate budgets per model (e.g., `opus`, `sonnet`, `haiku`) |
| **Priority Classes** | Guaranteed, best-effort, batch |
| **Carryover** | Unused budget rollover (configurable) |

**LLM Quota Enforcement:**
- CapabilityManager checks quota before routing LLM invocations
- Streaming token counting (estimate → actual on completion)
- Quota exhaustion triggers ResourceExhaustedEvent for LLM capability

#### 4.9.8 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: ResourceReservedEvent, ResourceReleasedEvent, ResourcePressureEvent, ResourceExhaustedEvent, ResourceCriticalEvent, ResourceOOMImminentEvent, ResourceUsageReportEvent. Consumes: ResourceReserveRequestEvent, ResourceReleaseRequestEvent, ResourceLimitChangeEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.resource` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.resource.*` configuration; limits, quotas |
| **WorkflowManager** | Inbound | Receives `resources.reserve()`, `resources.release()` |
| **CapabilityManager** | Inbound | Receives `resources.checkAvailability(profile)` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, resources.reserve, resourceType)` |
| **HealthManager** | Outbound | Reports resource health (capacity, pressure, saturation) |
| **ObservabilityManager** | Outbound | Emits resource metrics (usage, saturation, latency, quotas) |

**Forbidden:** Direct resource allocation by other managers. All allocation SHALL go through ResourceManager.

#### 4.9.9 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Reservation conflict (race) | Retry with backoff; deterministic ordering via reservation ID |
| Limit configuration error | Reject change; emit ResourceConfigErrorEvent; retain previous limits |
| Accounting drift detected | Reconcile from source of truth (cgroups, device plugins); emit ResourceDriftCorrectedEvent |
| GPU device loss | Release all reservations on device; emit ResourceDeviceLostEvent; notify affected holders |
| LLM quota service unavailable | Cache last known quota; allow with warning; emit ResourceQuotaUnavailableEvent |
| Backpressure signal loss | Default to conservative (assume pressure); emit ResourceSignalLostEvent |

**Invariant:** ResourceManager SHALL never over-allocate beyond global capacity. Accounting drift SHALL be detected and corrected within 30 seconds.

#### 4.9.10 Extension Rules

**Extension Points** (MAY be extended):
- Custom resource types (e.g., TPU, FPGA, custom accelerators)
- Custom limit scopes (e.g., team, project, folder)
- Custom backpressure algorithms
- Custom quota models (e.g., cost-based, carbon-aware)
- Custom reservation priority schemes

**Extension Constraints** (MUST be preserved):
- Single accounting authority SHALL be preserved
- Atomic reservations SHALL be preserved
- Global capacity hard limit SHALL be preserved
- Attribution to principal SHALL be preserved
- EventBus for all allocation events SHALL be preserved

**Forbidden Extensions:**
- Untracked resource usage
- Bypassing limits for "system" workloads
- Shared reservations without attribution
- Negative resource accounting

#### 4.9.11 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **No over-allocation** | Sum of reservations ≤ global capacity for all resource types |
| **Attribution completeness** | Every allocated unit has a principal |
| **Atomic reservation** | Zero partial reservations under concurrent load |
| **Limit enforcement** | No reservation exceeds declared limit |
| **Backpressure signaling** | ResourcePressureEvent emitted within 100ms of threshold crossing |
| **Accounting accuracy** | Ledger matches actual usage within 5% (measured via cgroups/device plugins) |

#### 4.9.12 Conformance

A ResourceManager implementation SHALL be conformant IFF:

1. **Static:** Passes resource type registration, limit configuration validation, quota model validation
2. **Runtime:** Reservations atomic; limits enforced; backpressure signaled; accounting accurate; drift corrected
3. **Architectural:** Single accounting authority; all allocation via ResourceManager; EventBus for events; SecurityManager for authz

---

### 4.10 HealthManager

#### 4.10.1 Purpose

HealthManager SHALL serve as the **sole health authority** within the Hermes Kernel. It SHALL own health monitoring, readiness, liveness, heartbeat, diagnostics, recovery recommendations, and health aggregation.

#### 4.10.2 Responsibilities

HealthManager SHALL be responsible for:

1. **Health Monitoring** — Continuous assessment of all kernel components (managers, services, capabilities, infrastructure)
2. **Readiness** — Determination of whether a component can serve traffic / perform its function
3. **Liveness** — Determination of whether a component is alive (not deadlocked, not crashed)
4. **Heartbeat** — Collection and aggregation of heartbeat signals
5. **Diagnostics** — On-demand and automated diagnostic data collection
6. **Recovery Recommendations** — Emission of actionable recovery steps for unhealthy components
7. **Health Aggregation** — Composite health views (kernel, subsystem, tenant, workflow)

#### 4.10.3 Health Monitoring

HealthManager SHALL monitor health at multiple levels:

| Level | Subjects | Frequency | Method |
|-------|----------|-----------|--------|
| **Kernel** | All Core Managers | Continuous (event-driven) | State machine + dependency graph |
| **Manager** | Each Core Manager | 10s interval | HTTP/health endpoint + self-report |
| **Service** | Registered services | 30s interval | HTTP/health endpoint |
| **Capability** | Capability providers | 30s interval | CapabilityManager health proxy |
| **Infrastructure** | Nodes, disks, network, GPUs | 60s interval | Node agent + device plugins |
| **Workflow** | Active workflows | Event-driven | WorkflowManager state events |

**Health State Values:** HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN, DRAINING

#### 4.10.4 Readiness

Readiness SHALL indicate **ability to serve current function**:

| Component | Ready Criteria |
|-----------|----------------|
| **LifecycleManager** | All phases complete; kernel OPERATIONAL |
| **StateManager** | Accepting transitions; checkpoint current |
| **StorageManager** | All namespaces accessible; no corruption |
| **WorkflowManager** | Scheduler running; no backlog > threshold |
| **SecurityManager** | Policy engine responsive; IdentityProvider reachable |
| **CapabilityManager** | Registry consistent; >0 healthy providers per facade |
| **ResourceManager** | Accounting current; no critical pressure |
| **HealthManager** | Self-healthy; monitoring active |
| **ObservabilityManager** | Collectors running; no buffer overflow |
| **Service** | HTTP 200 on /ready; dependencies ready |
| **Capability Provider** | HTTP 200 on /ready; resources available |

**Invariant:** HealthManager SHALL be the single source of readiness truth. LifecycleManager SHALL gate OPERATIONAL on all managers READY.

#### 4.10.5 Liveness

Liveness SHALL indicate **process viability**:

| Component | Live Criteria |
|-----------|---------------|
| **All Managers** | Process responds; no deadlock detected; heartbeat within 3× interval |
| **Services** | Process responds; HTTP 200 on /live |
| **Infrastructure** | Node agent heartbeat; kernel responsive |

**Invariant:** Liveness failure SHALL trigger immediate recovery action (restart, failover). Readiness failure SHALL trigger traffic draining.

#### 4.10.6 Heartbeat

HealthManager SHALL manage heartbeat protocol:

| Aspect | Specification |
|--------|---------------|
| **Interval** | 10s (managers), 30s (services), 60s (infrastructure) |
| **Missed Threshold** | 3× interval = UNHEALTHY |
| **Payload** | Component ID, state, metrics snapshot, dependency health |
| **Aggregation** | HealthManager maintains heartbeat timeline per component |
| **Failure Detection** | Missing heartbeat → DEGRADED → UNHEALTHY (configurable) |

#### 4.10.7 Diagnostics

HealthManager SHALL collect diagnostics:

| Trigger | Collection | Output |
|---------|------------|--------|
| **On-Demand** | Admin request | Diagnostic bundle (logs, metrics, traces, config, state) |
| **State Change** | HEALTHY → DEGRADED/UNHEALTHY | Automated mini-bundle (last 5min logs, current metrics, stack traces) |
| **Periodic** | Daily | Full diagnostic snapshot (archived) |
| **Pre-Recovery** | Before recovery action | Pre-recovery baseline |

**Diagnostic Bundle:** Stored in StorageManager (diagnostics namespace); correlated via EventBus.

#### 4.10.8 Recovery Recommendations

HealthManager SHALL emit **HealthRecoveryRecommendationEvent** for UNHEALTHY components:

| Component | Recommendation Types |
|-----------|---------------------|
| **Manager** | Restart manager; rollback to checkpoint; failover to standby |
| **Service** | Restart pod; drain + reschedule; circuit breaker reset |
| **Capability Provider** | Drain connections; restart; failover to alternate provider |
| **Infrastructure** | Node cordon+drain; disk replacement; network reset |
| **Workflow** | Retry failed step; compensate; cancel |

**Recommendation Properties:** Priority, estimated duration, risk level, prerequisites, automation eligibility.

#### 4.10.9 Health Aggregation

HealthManager SHALL compute aggregate health:

| Aggregate | Composition | Semantics |
|-----------|-------------|-----------|
| **Kernel Health** | All Core Managers | HEALTHY iff all managers HEALTHY |
| **Subsystem Health** | Related managers (e.g., execution: workflow+capability+resource) | Worst-of |
| **Tenant Health** | Tenant's workflows, capabilities, services | Weighted by criticality |
| **Workflow Health** | Workflow steps, dependencies | HEALTHY iff all steps HEALTHY |
| **Capability Health** | All providers for a facade | HEALTHY iff ≥1 provider HEALTHY per required version |

**Aggregation Rules:** Configurable per aggregate; default: worst-of.

#### 4.10.10 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: HealthChangedEvent, ReadinessChangedEvent, LivenessLostEvent, HealthRecoveryRecommendationEvent, HealthAggregatedEvent, DiagnosticBundleReadyEvent. Consumes: ComponentHeartbeatEvent, ComponentStateEvent, ManagerInitializedEvent, WorkflowStateChangedEvent, CapabilityProviderHealthEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.health` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.health.*` configuration; thresholds, intervals |
| **LifecycleManager** | Outbound | Invokes `lifecycle.getKernelState()`, `lifecycle.requestRecovery(manager)` |
| **StateManager** | Outbound | Invokes `state.getSnapshot()` for diagnostics |
| **StorageManager** | Outbound | Invokes `storage.diagnosticBundle()` |
| **ResourceManager** | Outbound | Invokes `resources.getUsage()` for pressure detection |
| **CapabilityManager** | Outbound | Invokes `capability.getProviderHealth()` |
| **WorkflowManager** | Outbound | Invokes `workflow.getHealth()` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, health.diagnostic, component)` |
| **ObservabilityManager** | Outbound | Emits health metrics; receives observability alerts |

**Forbidden:** Other managers making independent health determinations for gating. All readiness/liveness SHALL come from HealthManager.

#### 4.10.11 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| HealthManager self-failure | LifecycleManager detects via missing heartbeat; initiates HealthManager restart |
| Heartbeat storm (too frequent) | Throttle; emit HealthHeartbeatStormEvent |
| Diagnostic collection failure | Retry; partial bundle; emit HealthDiagnosticPartialEvent |
| Recovery recommendation ignored | Escalate; emit HealthRecoveryIgnoredEvent after timeout |
| Aggregation inconsistency | Recompute; emit HealthAggregationCorrectedEvent |

**Invariant:** HealthManager SHALL monitor itself. Self-health SHALL be reported via dedicated heartbeat.

#### 4.10.12 Extension Rules

**Extension Points** (MAY be extended):
- Custom health check types (pluggable)
- Custom aggregation functions
- Custom diagnostic collectors
- Custom recovery recommendation engines
- Custom health state values (beyond standard 5)

**Extension Constraints** (MUST be preserved):
- Single health authority SHALL be preserved
- Readiness/liveness separation SHALL be preserved
- Heartbeat protocol SHALL be preserved
- LifecycleManager gating on readiness SHALL be preserved
- EventBus for all health events SHALL be preserved

**Forbidden Extensions:**
- Services self-declaring ready without HealthManager
- Managers bypassing HealthManager for peer health
- Health state modification without HealthManager
- Diagnostic bundles without StorageManager

#### 4.10.13 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single health authority** | Zero readiness/liveness decisions outside HealthManager |
| **Readiness gating** | Kernel never OPERATIONAL with any manager NOT_READY |
| **Heartbeat timeliness** | UNHEALTHY declared within 3× interval of missed heartbeat |
| **Diagnostic completeness** | Every state change to UNHEALTHY produces diagnostic bundle |
| **Aggregation consistency** | Aggregate health = f(component health) per configured function |
| **Self-monitoring** | HealthManager reports own health via heartbeat |

#### 4.10.14 Conformance

A HealthManager implementation SHALL be conformant IFF:

1. **Static:** Passes health check configuration validation, aggregation rule validation, threshold validation
2. **Runtime:** Readiness/liveness accurate; heartbeats processed; diagnostics collected; recommendations emitted; aggregation correct
3. **Architectural:** Single authority; all gating via HealthManager; EventBus for events; StorageManager for diagnostics

---

### 4.11 ObservabilityManager

#### 4.11.1 Purpose

ObservabilityManager SHALL serve as the **sole governance authority** for all observability within the Hermes Kernel. It SHALL own metrics, tracing, monitoring, dashboards, alerting, telemetry, diagnostics, and audit integration.

#### 4.11.2 Responsibilities

ObservabilityManager SHALL be responsible for:

1. **Metrics Governance** — Collection, aggregation, storage, and query of all kernel and service metrics
2. **Tracing Governance** — Distributed trace collection, correlation, sampling, and storage
3. **Monitoring** — Real-time observation of system state via metrics and traces
4. **Dashboards** — Governance of dashboard definitions, versioning, and access
5. **Alerting** — Rule evaluation, notification routing, deduplication, escalation
6. **Telemetry** — OpenTelemetry-compatible collection pipeline management
7. **Diagnostics** — On-demand high-cardinality data collection
8. **Audit Integration** — Secure, tamper-evident delivery of SecurityAuditEvent to audit store

#### 4.11.3 Metrics

ObservabilityManager SHALL govern metrics per **OpenTelemetry Metric Data Model**:

| Metric Type | Kernel Sources | Cardinality Control |
|-------------|----------------|---------------------|
| **Counter** | Request counts, error counts, event counts | Low (labels: component, operation, status) |
| **Gauge** | Current usage, queue depth, health status | Low (labels: component, resource) |
| **Histogram** | Latency, duration, size | Medium (labels: component, operation, quantile) |
| **Summary** | Quantile latencies (client-side) | Low |

**Metric Standards:**
- **Naming:** `ai_os_<subsystem>_<metric>` (snake_case)
- **Labels:** Standardized (component, instance, version, zone, tenant)
- **Units:** Base units (seconds, bytes, count) with SI prefixes
- **Collection Interval:** 10s (managers), 30s (services), configurable
- **Retention:** Hot (24h, 10s resolution), Warm (30d, 1m), Cold (1y, 1h)

**Cardinality Enforcement:** ObservabilityManager SHALL reject metric registration exceeding cardinality budget (default: 10k series/metric).

#### 4.11.4 Tracing

ObservabilityManager SHALL govern distributed tracing per **W3C TraceContext**:

| Aspect | Specification |
|--------|---------------|
| **Trace Propagation** | `traceparent`, `tracestate` headers on all RPC/EventBus |
| **Sampling** | Head-based (probabilistic), tail-based (error/latency), parent-based |
| **Sampling Rate** | Default 1% (configurable per component, operation) |
| **Span Attributes** | Standard (service.name, span.kind, http.*, db.*, messaging.*) + kernel custom |
| **Context Propagation** | Automatic via EventBus correlation IDs; manual for external calls |
| **Retention** | Hot (24h, all), Warm (7d, sampled), Cold (30d, errors only) |

**Kernel Trace Spans:** Every manager operation SHALL produce spans:
- LifecycleManager: phase transitions, rollback, recovery
- StateManager: transitions, snapshots, recovery
- StorageManager: checkpoint/artifact operations
- WorkflowManager: workflow/step execution, scheduling
- SecurityManager: authn, authz, secret operations
- CapabilityManager: registration, resolution, invocation
- ResourceManager: reservations, pressure, limits
- HealthManager: checks, diagnostics, recommendations

#### 4.11.5 Monitoring

ObservabilityManager SHALL provide **real-time monitoring** capabilities:

| Capability | Description |
|------------|-------------|
| **Live Query** | Ad-hoc metric/trace queries (PromQL/OTel compatible) |
| **Streaming** | WebSocket/SSE for real-time metric updates |
| **Topology** | Service/manager dependency graph from traces |
| **SLO Tracking** | SLI/SLO definition, burn rate alerting |

#### 4.11.6 Dashboards

ObservabilityManager SHALL govern dashboards as **code**:

| Property | Requirement |
|----------|-------------|
| **Definition** | JSON/YAML (Grafana-compatible or native) |
| **Versioning** | Stored in ConfigurationAuthority; git-tracked |
| **Templating** | Variables for tenant, component, time range |
| **Access Control** | SecurityManager authorization (read/write) |
| **Validation** | Schema validation on register; reference validation (metrics exist) |

#### 4.11.7 Alerting

ObservabilityManager SHALL govern alerting:

| Aspect | Specification |
|--------|---------------|
| **Rule Definition** | PromQL/OTel query + condition + duration + labels |
| **Evaluation Interval** | 30s (configurable per rule) |
| **States** | FIRING, PENDING, RESOLVED |
| **Deduplication** | Group by labels; suppress during maintenance windows |
| **Notification** | Webhook, PagerDuty, Slack, email (pluggable) |
| **Escalation** | Time-based; auto-escalate if unacknowledged |
| **Silencing** | Label-based; scheduled; manual |

**Alert Categories:** Infrastructure, Kernel, Service, Security, Business.

#### 4.11.8 Telemetry

ObservabilityManager SHALL manage the **telemetry pipeline**:

| Pipeline Stage | Responsibility |
|----------------|----------------|
| **Collection** | OTel receivers (OTLP, Prometheus, statsd, custom) |
| **Processing** | Transformation, filtering, enrichment, batching |
| **Export** | OTel exporters (OTLP, Prometheus, CloudWatch, custom) |
| **Buffering** | In-memory + disk spillover; backpressure to senders |

**Pipeline Guarantees:**
- At-least-once delivery (configurable)
- Ordering per trace
- Resource attribution preserved
- PII redaction (configurable)

#### 4.11.9 Diagnostics

ObservabilityManager SHALL support **high-cardinality diagnostics**:

| Trigger | Data | Retention |
|---------|------|-----------|
| **On-Demand** | Profiler traces, heap dumps, custom queries | 7 days |
| **Alert Firing** | Context snapshot (metrics, traces, logs) | 30 days |
| **Error Spike** | Exemplar traces for erroring requests | 14 days |
| **Performance Regression** | Comparative profiles | 30 days |

**Diagnostic Isolation:** Diagnostics SHALL NOT impact production pipeline (separate buffer, lower priority).

#### 4.11.10 Audit Integration

ObservabilityManager SHALL ensure **audit event delivery**:

| Requirement | Implementation |
|-------------|----------------|
| **Tamper Evidence** | Cryptographic chaining (hash chain) or Merkle tree |
| **Immutability** | Write-once storage (WORM) or append-only log |
| **Completeness** | Gap detection via sequence numbers |
| **Delivery** | Direct to audit namespace (StorageManager) + SIEM export |
| **Latency** | <5s from SecurityAuditEvent emission to durable storage |
| **Verification** | Periodic audit log integrity verification |

**Invariant:** SecurityAuditEvent SHALL never be dropped. Buffer overflow SHALL block SecurityManager (backpressure).

#### 4.11.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: MetricRegisteredEvent, AlertFiringEvent, AlertResolvedEvent, DashboardRegisteredEvent, TraceSampledEvent. Consumes: All kernel events (for metrics/traces), SecurityAuditEvent (for audit pipeline), HealthChangedEvent (for SLO) |
| **ServiceRegistry** | Outbound | Registers self as `kernel.observability` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.observability.*` configuration; pipelines, rules, dashboards |
| **StorageManager** | Outbound | Invokes `storage.auditWrite()` for audit events; `artifact.store()` for diagnostic bundles |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, observability.*, resource)` |
| **ResourceManager** | Outbound | Invokes `resources.reserve()` for telemetry pipeline resources |
| **HealthManager** | Inbound | Receives health metrics; emits SLO burn alerts |
| **All Managers** | Inbound | Receive metrics, spans, logs via OTel SDK (configured by ObservabilityManager) |

**Forbidden:** Direct metric/trace emission to backends bypassing ObservabilityManager pipeline. All telemetry SHALL flow through ObservabilityManager.

#### 4.11.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Metric backend unavailable | Buffer locally (disk spillover); emit ObservabilityBackendUnavailableEvent |
| Trace sampling misconfiguration | Default to parent-based; emit ObservabilitySamplingWarnEvent |
| Alert evaluation failure | Skip cycle; emit ObservabilityAlertEvalFailedEvent; alert on repeated failure |
| Audit pipeline backpressure | Block SecurityManager; emit ObservabilityAuditBackpressureEvent |
| Cardinality explosion | Auto-throttle high-cardinality metrics; emit ObservabilityCardinalityThrottleEvent |
| Diagnostic collection failure | Retry; partial; emit ObservabilityDiagnosticPartialEvent |

**Invariant:** ObservabilityManager failure SHALL NOT cause kernel degradation. Telemetry is best-effort; audit is mandatory.

#### 4.11.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom metric types (beyond OTel)
- Custom trace exporters
- Custom alert notification channels
- Custom dashboard formats
- Custom diagnostic collectors
- Custom PII redaction rules

**Extension Constraints** (MUST be preserved):
- OTel compatibility SHALL be preserved
- Audit pipeline priority SHALL be preserved
- Cardinality budgets SHALL be enforced
- SecurityManager authorization SHALL be mandatory
- EventBus as event source SHALL be preserved

**Forbidden Extensions:**
- Dropping audit events
- Bypassing pipeline for "internal" metrics
- Unbounded cardinality
- Plaintext audit storage

#### 4.11.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single telemetry pipeline** | Zero direct backend writes by managers/services |
| **Audit completeness** | Zero SecurityAuditEvent gaps (sequence continuity) |
| **Audit latency** | 99th percentile <5s emission to durable storage |
| **Cardinality compliance** | No metric exceeds registered cardinality budget |
| **Trace correlation** | 100% of kernel operations have trace span |
| **Pipeline isolation** | Diagnostic collection never blocks primary pipeline |

#### 4.11.15 Conformance

An ObservabilityManager implementation SHALL be conformant IFF:

1. **Static:** Passes pipeline configuration validation, alert rule validation, dashboard schema validation, cardinality budget validation
2. **Runtime:** Metrics collected per interval; traces sampled per policy; alerts evaluated; audit events delivered; cardinality enforced
3. **Architectural:** Single pipeline; all telemetry mediated; audit priority; EventBus as source; SecurityManager for authz

---

**End of Part 4 (Sections 4.6–4.11)**