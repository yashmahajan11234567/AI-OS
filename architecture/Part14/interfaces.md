# AI-OS Architecture Specification v1.0
## Part 14: Integration Interface Inventory

**Version:** 1.0.0
**Status:** DRAFT — Inventory Only
**Date:** 2026-08-11
**Author:** Architecture Documentation
**Classification:** Informative — Cross-Part Interface Catalog

---

### 14.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART14 |
| **Classification** | Informative — Inventory and Catalog |
| **Purpose** | Authoritative inventory of integration interfaces defined in Parts 1–13; does not create new interfaces |
| **Distribution** | All AI-OS engineers, architects, reviewers |
| **Related Documents** | PART1–PART13, Common/ARCHITECTURE_SPEC_TOC.md, Part14/adrs.md, Part14/components.md, Part14/events.md, Part14/schemas.md |

**Scope Rule:** This Part inventories only interfaces defined in Parts 1–13. It does not invent protocols, contracts, endpoints, or behavioral guarantees absent from those Parts. Where Parts 1–13 define an interface without specifying one of the fields below, that field is marked **NOT YET DEFINED**.

---

## 1. How to Read This Inventory

Each interface entry documents where the information exists in the authoritative source material. Every field carries a provenance marker so reviewers can judge confidence.

| Property | Meaning in this document |
|---------|--------------------------|
| **Interface ID** | Canonical inventory identifier |
| **Name** | Interface name as defined in source Parts |
| **Status** | Classification of the interface itself: **EXISTING** if defined with a named contract in Parts 1–13; **DERIVED** if logically inferred from multiple source statements; **UNSPECIFIED** if named but contract absent; **GAP** if required for integration but missing; **CONFLICT** if Parts 1–13 disagree on the interface identity |
| **Provider** | Component/service that owns/exposes the interface |
| **Consumer(s)** | Component/service that uses the interface |
| **Purpose** | Why the interface exists |
| **Direction** | Actual data/control flow. For event-mediated flows, use **Producer → EventBus → Consumer**. For direct calls, use **Provider → Consumer** or **Consumer → Provider**. Do not collapse both directions into “bidirectional” unless both paths are independently established. |
| **Interaction style** | Synchronous, asynchronous, event-driven, etc. |
| **Protocol/mechanism** | Defined only if Parts 1–13 specify one; otherwise NOT YET DEFINED |
| **Request contract** | Defined only if Parts 1–13 define the request shape; otherwise NOT YET DEFINED |
| **Response contract** | Defined only if Parts 1–13 define the response shape; otherwise NOT YET DEFINED |
| **Error contract** | Defined only if Parts 1–13 define error behavior; otherwise NOT YET DEFINED |
| **Authentication/authorization requirements** | Defined only if Parts 1–13 specify authn/authz; otherwise NOT YET DEFINED |
| **Timeout expectations** | Defined only if Parts 1–13 specify timeouts; otherwise NOT YET DEFINED |
| **Retry expectations** | Defined only if Parts 1–13 specify retry behavior; otherwise NOT YET DEFINED |
| **Idempotency requirements** | Defined only if Parts 1–13 specify idempotency; otherwise NOT YET DEFINED |
| **Versioning strategy** | Defined only if Parts 1–13 specify versioning; otherwise NOT YET DEFINED |
| **Compatibility requirements** | Defined only if Parts 1–13 specify compatibility rules; otherwise NOT YET DEFINED |
| **Related schemas** | Schemas defined in Parts 1–13 that relate to this interface |
| **Related events** | Events defined in Parts 1–13 that relate to this interface |
| **Related components** | Components defined in Parts 1–13 that relate to this interface |
| **Related ADRs** | ADRs from Parts 0–14 that constrain or shape this interface |
| **Where defined** | Part and section references |

---

## 2. Established Interfaces

Established interfaces are those explicitly defined with named contracts, event envelopes, method signatures, or manager/service interaction rules in Parts 1–13.

Interfaces are organized by category to avoid treating every interface as bidirectional:

- **2.1 Lifecycle / Initialization Interfaces** — interfaces that govern component/service startup and shutdown
- **2.2 Singleton Accessor Interfaces** — read-only accessors exposing kernel-owned singletons
- **2.3 Service Contract Interfaces** — BaseService-derived contracts for registered services
- **2.4 Event Interfaces** — publish/subscribe contracts and canonical event taxonomies
- **2.5 Facade Bridge Interfaces** — translation contracts between EventBus events and Manager method calls
- **2.6 Configuration Interfaces** — read-only configuration access after freeze
- **2.7 Governance Interfaces** — governance event taxonomy and cross-part governance contracts

---

### 2.1 Lifecycle / Initialization Interfaces

#### 2.1.1 Kernel Core Component Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-CORE-CMP-001 |
| **Interface name** | `ICoreComponent` |
| **Status** | EXISTING |
| **Provider** | HermesKernel |
| **Consumer(s)** | HermesKernel (initialization lifecycle), HealthManager (health probing) |
| **Purpose** | Mandated interface for all four Core Components |
| **Direction** | HermesKernel → Core Component (initialization); Core Component → HermesKernel/HealthManager (health check response) |
| **Interaction style** | Synchronous initialization contract; synchronous health check |
| **Protocol/mechanism** | Direct method invocation |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `CoreComponentInitialized`, `CoreComponentShutdown` |
| **Related components** | EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 1 §1.7.2, Part 1 §1.8.1, Part 3 §3.3.6 |
| **Verification note** | Provider corrected to HermesKernel. `StructuredLogger` removed from related components because Part 1 §1.8.1 defines the four Core Components as EventBus, ServiceRegistry, ConfigurationManager, and LifecycleManager. `components.md` §3.1 notes that `interfaces.md` §2.1.1 incorrectly listed `StructuredLogger`; Part 1 is authoritative here. |

---

#### 2.1.2 Kernel Core Manager Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-CORE-MGR-001 |
| **Interface name** | `ICoreManager` |
| **Status** | EXISTING |
| **Provider** | HermesKernel |
| **Consumer(s)** | HermesKernel (initialization lifecycle), ObservabilityManager (metrics probing) |
| **Purpose** | Mandated interface for all nine Core Managers |
| **Direction** | HermesKernel → Core Manager (initialization); Core Manager → HermesKernel/ObservabilityManager (health/metrics response) |
| **Interaction style** | Synchronous initialization contract; synchronous health and metrics probing |
| **Protocol/mechanism** | Direct method invocation |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `CoreManagerInitialized`, `CoreManagerShutdown`, `CoreManagerDegraded`, `CoreManagerFailed` |
| **Related components** | MemoryManager, LLMManager, ToolManager, StorageManager, ContextManager, AgentManager, WorkflowManager, SecurityManager, ObservabilityManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 1 §1.8.2, Part 4 §4.2.2 |

---

### 2.2 Singleton Accessor Interfaces

#### 2.2.1 HermesKernel Public Accessor Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-KERNEL-ACC-001 |
| **Interface name** | `HermesKernel.instance` singleton accessors |
| **Status** | EXISTING |
| **Provider** | HermesKernel |
| **Consumer(s)** | Core Managers, Engineering Services, Capability Facade Services, Extensions |
| **Purpose** | Expose exactly four Core Components and nine Core Managers via read-only singleton accessors |
| **Direction** | Consumer → HermesKernel |
| **Interaction style** | Synchronous property access returning singleton instances |
| **Protocol/mechanism** | Language-native accessor invocation |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | Throws `KernelNotReadyError` if accessed before RUNNING state |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | No additional accessors may be added; no accessor may be removed |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | NOT YET DEFINED |
| **Related components** | All Core Components and Core Managers |
| **Related ADRs** | ADR-004 (Global Singleton Accessors) |
| **Source authority** | Part 1 §1.8.4, Part 1 INV-CM-004 through INV-CM-006 |

---

### 2.3 Service Contract Interfaces

#### 2.3.1 BaseService Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-SVC-BASE-001 |
| **Interface name** | `BaseService` |
| **Status** | EXISTING |
| **Provider** | HermesKernel |
| **Consumer(s)** | Engineering Services, Capability Facade Services, HumanInteractionService |
| **Purpose** | Mandated base class / contract for all registered services |
| **Direction** | Service → HermesKernel (registration/lifecycle); HermesKernel → Service (lifecycle transitions) |
| **Interaction style** | Lifecycle-driven with EventBus-mediated communication |
| **Protocol/mechanism** | Service registration, initialization, lifecycle, health check, and event subscription via BaseService contract |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `ServiceRegistered`, `ServiceHealthChanged`, `ServiceInitialized`, `ServiceShutdown`, `ServiceFailed`, `ServiceDegraded` |
| **Related components** | All Engineering Services, Capability Facade Services, HumanInteractionService |
| **Related ADRs** | ADR-005 (Event-Driven Services) |
| **Source authority** | Part 4 §4.2, Part 5 §5.2.5, Part 6 §6.1 |

---

#### 2.3.2 Service Registration Contract

| Property | Value |
|---------|-------|
| **Interface ID** | INT-SVC-REG-001 |
| **Interface name** | `ServiceRegistration` |
| **Status** | EXISTING |
| **Provider** | ServiceRegistry |
| **Consumer(s)** | Services (registration), LifecycleManager (topological start/stop), WorkflowManager (discovery) |
| **Purpose** | Authoritative service registration, discovery, dependency topology, and health tracking |
| **Direction** | Consumer → ServiceRegistry (registration); ServiceRegistry → Consumer (discovery) |
| **Interaction style** | Synchronous registration and lookup |
| **Protocol/mechanism** | Direct method invocation through kernel accessor |
| **Request contract** | `ServiceRegistration` structure including `service`, `serviceId`, `serviceType`, `dependsOn`, `capabilities`, `critical`, `tags`, `metadata` |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | `Capability` |
| **Related events** | `ServiceRegistered`, `ServiceHealthChanged`, `ServiceInitialized`, `ServiceShutdown` |
| **Related components** | ServiceRegistry, LifecycleManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 3 §3.4.4, Part 3 §3.4.5, Part 3 §3.4.7 |

---

### 2.4 Event Interfaces

#### 2.4.1 EventBus Publication and Subscription Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-EVT-BUS-001 |
| **Interface name** | `EventBus` publish / subscribe contract |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | All Core Components, Core Managers, Services, Extensions, Governance components |
| **Purpose** | Primary event-mediated communication substrate for event publication, subscription, routing, ordering, and delivery. Lifecycle and control paths outside EventBus are direct invocation interfaces; they are not subsumed by this interface. |
| **Direction** | Event producer → EventBus → Event consumer |
| **Interaction style** | Asynchronous publish/subscribe with priority lanes and retry semantics |
| **Protocol/mechanism** | EventBus in-memory bus; events validated against registered schemas |
| **Request contract** | Immutable `Event` conforming to base contract including `eventId`, `eventType`, `eventVersion`, `timestamp`, `timestampMonotonic`, `correlationId`, `causationId`, `source`, `target`, `priority`, `category`, `payload`, `checksum` |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | `REJECTED_SHUTDOWN`, `REJECTED_CAPACITY`; failed deliveries route to retry queue or dead-letter queue |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | Handler timeout default 30,000 ms; queue capacity defaults 10,000 publish, 1,000 retry, 10,000 dead letter |
| **Retry expectations** | Retry queue with configurable max attempts; dead-letter queue after exhaustion |
| **Idempotency requirements** | `eventId` deduplication; handlers must be idempotent |
| **Versioning strategy** | Semantic versioning per `eventVersion`; MAJOR for breaking schema changes, MINOR for backward-compatible additions, PATCH for fixes |
| **Compatibility requirements** | Backward/forward compatibility enforced via schema registry; breaking changes require major version bump |
| **Related schemas** | Event base contract, all payload schemas |
| **Related events** | All canonical event types |
| **Related components** | All components using EventBus |
| **Related ADRs** | ADR-001 (Event-First Communication), ADR-008 (Immutable Events), ADR-009 (Explicit Failure Handling) |
| **Source authority** | Part 1 §1.7.4, Part 2 §2.2–2.4, Part 2 §2.8, Part 2 §2.9, Part 3 §3.3.4 |
| **Verification note** | Provider is EventBus. All Core Components, Core Managers, Services, Facades, Extensions, and governance components may be consumers, but only as event producers or subscribers; they do not own the substrate. The claim "primary event-mediated communication substrate" is limited to event interfaces. Direct lifecycle/control interfaces remain synchronous and do not flow through this interface. |

---

#### 2.4.2 Part 12 Multi-Agent Event Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-C12-EVENT-001 |
| **Interface name** | Multi-agent collaboration event interfaces |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | Workflow Manager, Council Manager, agents, runtime, security, observability, governance components |
| **Purpose** | Canonical event-driven interfaces for workflow, council, agent lifecycle, delegation, knowledge, context, runtime, communication, security, monitoring, scheduler, and system state changes |
| **Direction** | Event producer → EventBus → Event consumer |
| **Interaction style** | Asynchronous event-driven |
| **Protocol/mechanism** | Part 12 canonical envelope with topics, priority lanes, partition keys, and WORM log |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | Retry then DLQ with reconciliation |
| **Authentication/authorization requirements** | Signed events; PII and secrets redacted in payload |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | Typically 5 retries with exponential backoff; some final-state events use 10 retries |
| **Idempotency requirements** | `event_id` deduplication with default 24h window; idempotent handlers |
| **Versioning strategy** | Semantic versioning per event type; schema registry with major-version gating |
| **Compatibility requirements** | At-least-once delivery; ordered per `partition_key`; backward-compatible additions preferred |
| **Related schemas** | Part 12 event envelope schema, per-event payload schemas |
| **Related events** | `workflow.lifecycle.started`, `workflow.lifecycle.completed`, `workflow.step.scheduled`, `workflow.step.started`, `workflow.step.completed`, `workflow.step.failed`, `workflow.step.retried`, `council.lifecycle.convened`, `council.lifecycle.dissolved`, `agent.lifecycle.registered`, `agent.lifecycle.deregistered`, `agent.lifecycle.heartbeat`, `context.lifecycle.snapshot`, `tool.lifecycle.registered`, `tool.lifecycle.deprecated`, and related workflow, council, delegation, knowledge, context, runtime, communication, security, monitoring, scheduler, and system events |
| **Related components** | Workflow Manager, Council Manager, Agent Manager, Communication Bus, Shared Context Manager, Scheduler |
| **Related ADRs** | P12-ADR-001 (Event-First Collaboration), P12-ADR-004 (Workflow Orchestration), P12-ADR-008 (Zero-Trust Security) |
| **Source authority** | Part 12 `events.md`, Part 12 `components.md` |
| **Verification note** | Provider corrected to EventBus. “Part 12 event backbone” is not a standalone component in Parts 1–13; Part 12 events flow through EventBus. Direction rewritten as Producer → EventBus → Consumer to match the event-mediated pattern used elsewhere in this inventory. |
| **Part 2 vs Part 12 note** | `INT-EVT-BUS-001` and `INT-C12-EVENT-001` are related but not identical interfaces. Part 2 defines the transport-level `EventType` enum, base `Event` contract, priority lanes, retry/queues, and handler lifecycle. Part 12 defines the integration-level lowercase-dotted event taxonomy, `EVENT-ENVELOPE-v1`, partition-key ordering, 24h `event_id` dedup, WORM log, and per-family DLQ topics. These two models coexist and are not merged in this inventory. |

---

#### 2.4.3 Governance Event Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-GOV-EVENT-001 |
| **Interface name** | `governance.*` event taxonomy |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | Governance services, policy gates, councils, audit service, security domain, observability |
| **Purpose** | Canonical governance event taxonomy for policy, decision, authority, approval, risk, compliance, audit, control, conformance, agent, and capability state changes |
| **Direction** | Event producer → EventBus → Event consumer |
| **Interaction style** | Asynchronous event-driven |
| **Protocol/mechanism** | Part 12 event envelope via EventBus |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED at the EventBus level; governance events themselves are signed, minimum classification `confidential`, ACL-gated subscription |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | At-least-once delivery with `event_id` dedup window default 24h |
| **Idempotency requirements** | `event_id` deduplication; projection writers reject duplicate lifecycle transitions |
| **Versioning strategy** | Semantic versioning per Part 12 §27; Part 13 §7 requires Security-domain co-signature for major bumps |
| **Compatibility requirements** | Backward-compatible additions only in MINOR; MAJOR for field removal or semantic change |
| **Related schemas** | Part 12 event envelope schema, Part 13 schemas for policy, decision, audit, risk, compliance, control, agent, capability |
| **Related events** | `governance.policy.created`, `governance.policy.updated`, `governance.policy.approved`, `governance.policy.activated`, `governance.policy.suspended`, `governance.policy.deprecated`, `governance.policy.retired`, `governance.policy.violation.detected`, `governance.policy.exception.requested`, `governance.policy.exception.approved`, `governance.policy.exception.rejected`, `governance.policy.submitted`, `governance.policy.override.granted`, `governance.policy.exception.expiring`, `governance.policy.conflict.detected`, `governance.policy.validation.failed`, `governance.decision.created`, `governance.decision.approved`, `governance.decision.rejected`, `governance.authority.delegated`, `governance.authority.revoked`, `governance.approval.requested`, `governance.approval.granted`, `governance.approval.rejected`, `governance.risk.identified`, `governance.risk.escalated`, `governance.risk.accepted`, `governance.compliance.violation.detected`, `governance.audit.started`, `governance.audit.completed`, `governance.control.evaluated`, `governance.conformance.verified`, `governance.conformance.failed`, `governance.agent.created`, `governance.agent.provisioned`, `governance.agent.activated`, `governance.agent.suspended`, `governance.agent.revoked`, `governance.agent.action`, `governance.agent.action.denied`, `governance.agent.behavior.anomaly`, `governance.agent.accountability.gap`, `governance.capability.created`, `governance.capability.issued`, `governance.capability.revoked`, `governance.capability.expired`, `governance.capability.suspended`, `governance.capability.modified`, `governance.capability.used`, `governance.capability.usage.violation`, `governance.capability.usage.anomaly` |
| **Related components** | Policy Manager, Decision Authority Manager, Approval Manager, Risk Manager, Compliance Manager, Audit Manager, Control Manager, Conformance Manager, Governance Event Manager, Accountability Manager |
| **Related ADRs** | P13-ADR-005 (Governance Event Architecture), P13-ADR-006 (Governance Auditability) |
| **Source authority** | Part 13 `governance-events.md`, Part 13 `components.md` |
| **Verification note** | Provider corrected to EventBus. Governance components are producers/consumers of `governance.*` events, but the interface substrate is EventBus. Direction rewritten as Producer → EventBus → Consumer. The “Consumer → Provider” publication path is preserved in the event producer set above; it does not justify calling the interface itself bidirectional. |

---

#### 2.4.4 Engineering Service Trigger/Completion Event Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-ENG-EVENT-001 |
| **Interface name** | Engineering Service phase event contracts |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | WorkflowManager, downstream Engineering Services, governance services |
| **Purpose** | Define request/completion/failure events for each SDLC phase |
| **Direction** | Event producer → EventBus → Event consumer |
| **Interaction style** | Asynchronous event-driven |
| **Protocol/mechanism** | EventBus |
| **Request contract** | Phase request payloads such as `PlanningRequestPayload`, `CodingRequestPayload`, `ReviewRequestPayload`, `TestingRequestPayload`, `DeploymentRequestPayload`, `OperationsRequestPayload`, `LearningRequestPayload`, `MemorySyncRequestPayload`, `ResearchRequestPayload`, `DocumentationRequestPayload` |
| **Response contract** | Phase result payloads such as `PlanArtifact`, `FailureContext`, `ArtifactPayload`, `FindingPayload`, `LearningPayload` |
| **Error contract** | `*_FAILED` events with `FailureContext` for RCA |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | Semantic versioning per event schema |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | `PlanArtifact`, `TaskGraphSchema`, `RiskRegisterSchema`, `EstimationSchema`, `FindingPayload`, `LearningPayload`, `ArtifactPayload` |
| **Related events** | `PLANNING_REQUESTED`, `PLANNING_COMPLETED`, `PLANNING_FAILED`, `CODING_REQUESTED`, `CODING_COMPLETED`, `CODING_FAILED`, `REVIEW_REQUESTED`, `REVIEW_APPROVED`, `REVIEW_REJECTED`, `REVIEW_FAILED`, `TESTING_REQUESTED`, `TESTING_COMPLETED`, `TESTING_FAILED`, `DEPLOYMENT_REQUESTED`, `DEPLOYMENT_COMPLETED`, `DEPLOYMENT_FAILED`, `DEPLOYMENT_ROLLED_BACK`, `OPERATIONS_REQUESTED`, `OPERATIONS_COMPLETED`, `OPERATIONS_FAILED`, `LEARNING_REQUESTED`, `LEARNING_COMPLETED`, `LEARNING_FAILED`, `MEMORY_SYNC_REQUESTED`, `MEMORY_SYNC_COMPLETED`, `MEMORY_SYNC_FAILED`, `RESEARCH_REQUESTED`, `RESEARCH_COMPLETED`, `RESEARCH_FAILED`, `DOCUMENTATION_REQUESTED`, `DOCUMENTATION_COMPLETED`, `DOCUMENTATION_FAILED` |
| **Related components** | All Engineering Services |
| **Related ADRs** | ADR-006 (Engineering Service SDLC Pipeline), ADR-009 (Explicit Failure Handling) |
| **Source authority** | Part 5 §5.3–5.13 |
| **Verification note** | Provider corrected to EventBus. Engineering Services are the event producers, but the interface substrate is EventBus. Direction rewritten as Producer → EventBus → Consumer. The previous “Consumer → Provider (request events)” direction was unjustified because these are event-driven service contracts, not direct request/response APIs. |

---

### 2.5 Facade Bridge Interfaces

#### 2.5.1 Capability Facade Service Event Bridge Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-CFS-BRIDGE-001 |
| **Interface name** | Capability Facade Service translation contract |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | Engineering Services, HumanInteractionService |
| **Purpose** | Translate EventBus events into Capability Manager method calls and emit result events |
| **Direction** | Event producer → EventBus → Facade Service; Facade Service → EventBus → Event consumer |
| **Interaction style** | Event-driven request/response |
| **Protocol/mechanism** | EventBus publish/subscribe |
| **Request contract** | Defined per facade event type consumed |
| **Response contract** | Defined per facade event type produced |
| **Error contract** | Facade emits failure event types such as `SKILL_FAILED`, `COUNCIL_ESCALATED`, `MCP_TOOL_FAILED` |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | Semantic versioning per event schema |
| **Compatibility requirements** | Event payloads must not contain provider-specific fields; facade adapts to manager, not reverse |
| **Related schemas** | Facade event payload schemas |
| **Related events** | `SKILL_EXECUTED`, `SKILL_FAILED`, `COUNCIL_CONVENED`, `COUNCIL_CONSENSUS_REACHED`, `COUNCIL_DISSENT_REGISTERED`, `COUNCIL_DECISION_FINALIZED`, `COUNCIL_ESCALATED`, `MCP_TOOL_CALLED`, `MCP_TOOL_SUCCEEDED`, `MCP_TOOL_FAILED`, `MEMORY_STORED`, `MEMORY_RETRIEVED`, `MEMORY_UPDATED`, `MEMORY_CONSOLIDATED`, `MEMORY_PRUNED` |
| **Related components** | SkillManager, CouncilManager, MCPManager, MemoryManager |
| **Related ADRs** | ADR-007 (Capability Facade Services), ADR-003 (Capability Manager Ownership) |
| **Source authority** | Part 6 §6.1.5, Part 6 §6.2.2 |
| **Verification note** | Provider corrected to EventBus. Facade Services are the logical translators, but the interface substrate is EventBus. Direction rewritten as event-mediated to avoid conflating service implementation with interface ownership. The previous “Consumer → Provider / Provider → Consumer” labeling was justified for facade-to-manager translation calls, but that internal translation is not itself a separate integration interface in Parts 1–13. |

---

### 2.6 Configuration Interfaces

#### 2.6.1 Configuration Authority Read Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-CONFIG-READ-001 |
| **Interface name** | `ConfigurationManager` read contract |
| **Status** | EXISTING |
| **Provider** | ConfigurationManager |
| **Consumer(s)** | Core Managers, Engineering Services, Capability Facade Services |
| **Purpose** | Provide immutable read-only configuration after freeze |
| **Direction** | Consumer → ConfigurationManager |
| **Interaction style** | Synchronous read |
| **Protocol/mechanism** | Direct manager read via singleton accessor |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | Configuration value |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | Configuration frozen after initialization; runtime mutation prohibited |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `ConfigurationFrozen`, `ConfigurationChanged` |
| **Related components** | ConfigurationManager |
| **Related ADRs** | ADR-010 (Declarative Layered Configuration) |
| **Source authority** | Part 1 §1.10.2, Part 3 §3.5 |
| **Verification note** | Interface is EXISTING because Parts 1 and 3 explicitly define `ConfigurationManager` as the configuration authority and specify read access through the singleton accessor. The request/response/error contract details are left NOT YET DEFINED in inspected Parts 1–13. |

---

### 2.7 Governance Interfaces

**Governance event interface note:** `INT-GOV-EVENT-001` is defined once, in §2.4.3. That section is the authoritative entry for provider, direction, event list, authentication, retry, idempotency, versioning, and compatibility. §2.7.x does not redefine it.

#### 2.7.1 Workflow Manager Control Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-WF-CTRL-001 |
| **Interface name** | `WorkflowManager` control contract |
| **Status** | EXISTING |
| **Provider** | WorkflowManager |
| **Consumer(s)** | Operators, orchestration layers, administrators |
| **Purpose** | External lifecycle control of workflow instances |
| **Direction** | Consumer → WorkflowManager |
| **Interaction style** | Synchronous command interface |
| **Protocol/mechanism** | Direct manager method via singleton accessor |
| **Request contract** | Workflow definition, pause/resume/cancel requests |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `WorkflowCreated`, `WorkflowStateChanged`, `WorkflowStepStarted`, `WorkflowStepCompleted`, `WorkflowCompleted`, `WorkflowFailed`, `WorkflowCancelled` |
| **Related components** | WorkflowManager, CapabilityManager, ResourceManager, SecurityManager, StorageManager, HealthManager, ObservabilityManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 4 §4.6.3, Part 4 §4.6.11 |
| **Verification note** | Interface is EXISTING because Part 4 §4.6.3 and §4.6.11 explicitly define `WorkflowManager` lifecycle control operations (create, pause, resume, cancel). However, the concrete response and error contracts are left NOT YET DEFINED in Parts 1–13. |

---

#### 2.7.2 Health Check Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-HEALTH-001 |
| **Interface name** | `healthCheck()` |
| **Status** | UNSPECIFIED |
| **Provider** | Core Components, Core Managers, Services |
| **Consumer(s)** | HealthManager |
| **Purpose** | Periodic health probe for all kernel-owned entities and services |
| **Direction** | Consumer → Provider |
| **Interaction style** | Synchronous polling |
| **Protocol/mechanism** | Direct method invocation |
| **Request contract** | NOT YET DEFINED |
| **Response contract** | `HealthStatus` with `ready: boolean`, `details: object` |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | `HealthStatus` |
| **Related events** | `HealthCheckPassed`, `HealthCheckFailed`, `ServiceHealthChanged`, `ServiceDegraded`, `ServiceFailed` |
| **Related components** | HealthManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 1 §1.7.2, Part 1 §1.8.2, Part 5 §5.14.1 INV-CSI-010, Part 4 §4.10 |
| **Verification note** | Status is UNSPECIFIED because `HealthStatus` schema and `healthCheck()` method signatures are referenced but not formally defined as a contract in Parts 1–13. The interface concept exists, but its concrete shape is not published. |

---

#### 2.7.3 Security Authorization Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-SEC-AUTH-001 |
| **Interface name** | `SecurityManager.authorize` |
| **Status** | EXISTING |
| **Provider** | SecurityManager |
| **Consumer(s)** | Core Managers, Engineering Services, Capability Facade Services, WorkflowManager |
| **Purpose** | Attribute-Based Access Control decision point for all protected operations |
| **Direction** | Consumer → SecurityManager |
| **Interaction style** | Synchronous authorization decision |
| **Protocol/mechanism** | Direct manager method via singleton accessor |
| **Request contract** | Principal, action, resource, context |
| **Response contract** | Decision: `ALLOW`, `DENY`, or `CHALLENGE` |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | All authorization decisions require successful prior authentication |
| **Verification note** | The prior-authentication requirement is stated in source architecture as a precondition for authorization. The concrete authn mechanism is NOT YET DEFINED in the inspected Parts 1–13 source for this interface. |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | Policy rule schema |
| **Related events** | `AuthorizationDecisionEvent`, `AuthenticationFailedEvent` |
| **Related components** | SecurityManager |
| **Related ADRs** | P12-ADR-008 (Zero-Trust Security), P13-ADR-002 (Separation of Policy and Enforcement) |
| **Source authority** | Part 4 §4.7.4 |
| **Verification note** | Interface is EXISTING because Part 4 §4.7.4 explicitly defines `SecurityManager.authorize` with named parameters (principal, action, resource, context) and a fixed response contract (`ALLOW`/`DENY`/`CHALLENGE`). The error contract is left NOT YET DEFINED. |

---

#### 2.7.4 Human Interaction Service Interface

| Property | Value |
|---------|-------|
| **Interface ID** | INT-HUMAN-001 |
| **Interface name** | `HumanInteractionService` event interface |
| **Status** | EXISTING |
| **Provider** | EventBus |
| **Consumer(s)** | Engineering Services, CouncilService, SecurityManager (request events); HumanInteractionService (request/response mediation) |
| **Purpose** | Exclusive interface between autonomous execution and human governance |
| **Direction** | Event producer → EventBus → HumanInteractionService → EventBus → Event consumer |
| **Interaction style** | Event-driven with SLA-bounded human response |
| **Protocol/mechanism** | EventBus |
| **Request contract** | Escalation, question, approval, and override request payloads |
| **Response contract** | `HumanResponsePayload`, `TimeoutPayload`, `OverridePayload`, `FeedbackPayload` |
| **Error contract** | `HUMAN_TIMEOUT`, `HUMAN_UNRESPONSIVE` |
| **Authentication/authorization requirements** | NOT YET DEFINED at the EventBus level; manual overrides require `kernel.admin` and identity verification via SecurityManager |
| **Timeout expectations** | SLA-bounded by interaction type: plan approval 4h, security exception 1h, production deploy 30m, rollback 5m, architecture override 2h, clarification 8h, manual override immediate |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | Semantic versioning per event schema |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | `HumanEscalationPayload`, `QuestionPayload`, `ApprovalPayload`, `HumanResponsePayload`, `TimeoutPayload`, `OverridePayload`, `FeedbackPayload` |
| **Related events** | `HUMAN_ESCALATION_REQUIRED`, `HUMAN_QUESTION`, `HUMAN_APPROVAL_REQUESTED`, `HUMAN_RESPONSE_RECEIVED`, `HUMAN_TIMEOUT`, `HUMAN_OVERRIDE_EXECUTED`, `HUMAN_FEEDBACK` |
| **Related components** | HumanInteractionService, SecurityManager, ObservabilityManager, LearningService |
| **Related ADRs** | ADR-006 (Human Oversight) |
| **Source authority** | Part 5 §5.12 |
| **Verification note** | Provider corrected to EventBus. HumanInteractionService is the mediator, not the interface substrate. Direction rewritten as Producer → EventBus → HumanInteractionService → EventBus → Consumer to reflect both request and response flows through EventBus. The interface is genuinely bidirectional because it carries both request events and response events. |

---

### 2.8 Workflow Manager External Control Interface

> **Duplicate notice:** `INT-WF-CTRL-001` is defined once, in §2.7.1. That section is the authoritative entry. This section existed as a duplicate definition with the same interface ID, provider, consumer, direction, and source authority. It is retained here only as a cross-reference, not as an independent interface definition.

| Property | Value |
|---------|-------|
| **Interface ID** | INT-WF-CTRL-001 |
| **Interface name** | `WorkflowManager` control contract |
| **Status** | EXISTING |
| **Provider** | WorkflowManager |
| **Consumer(s)** | Operators, orchestration layers, administrators |
| **Purpose** | External lifecycle control of workflow instances |
| **Direction** | Consumer → WorkflowManager |
| **Interaction style** | Synchronous command interface |
| **Protocol/mechanism** | Direct manager method via singleton accessor |
| **Request contract** | Workflow definition, pause/resume/cancel requests |
| **Response contract** | NOT YET DEFINED |
| **Error contract** | NOT YET DEFINED |
| **Authentication/authorization requirements** | NOT YET DEFINED |
| **Timeout expectations** | NOT YET DEFINED |
| **Retry expectations** | NOT YET DEFINED |
| **Idempotency requirements** | NOT YET DEFINED |
| **Versioning strategy** | NOT YET DEFINED |
| **Compatibility requirements** | NOT YET DEFINED |
| **Related schemas** | NOT YET DEFINED |
| **Related events** | `WorkflowCreated`, `WorkflowStateChanged`, `WorkflowStepStarted`, `WorkflowStepCompleted`, `WorkflowCompleted`, `WorkflowFailed`, `WorkflowCancelled` |
| **Related components** | WorkflowManager, CapabilityManager, ResourceManager, SecurityManager, StorageManager, HealthManager, ObservabilityManager |
| **Related ADRs** | NOT YET DEFINED |
| **Source authority** | Part 4 §4.6.3, Part 4 §4.6.11 |
| **Verification note** | Interface is EXISTING because Part 4 §4.6.3 and §4.6.11 explicitly define `WorkflowManager` lifecycle control operations (create, pause, resume, cancel). However, the concrete response and error contracts are left NOT YET DEFINED in Parts 1–13. |

---

## 3. Proposed Interfaces

Proposed interfaces are mentioned in Parts 1–13 as planned extension points, future work, or explicit proposals without finalized contracts. They are cataloged here to prevent them from being mistaken for established interfaces.

---

### 3.1 External System Adapter Interface

| Property | Value |
|---------|-------|
| **Interface ID** | PRO-EXT-ADAPTER-001 |
| **Interface name** | External system integration adapter interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Enable integration with external regulatory frameworks, industry standards, and organizational governance policies |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Unspecified |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | Unspecified |
| **Source authority** | Part 13 README boundary description |
| **Verification note** | Status is UNSPECIFIED because this interface is named as a boundary concept in Part 13 but no contract, schema, or binding is defined in Parts 1–13. |

---

### 3.2 Domain Policy Adapter Interface

| Property | Value |
|---------|-------|
| **Interface ID** | PRO-GOV-ADAPTER-001 |
| **Interface name** | Domain policy adapter interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Allow domain-specific governance requirements in Parts 14–15 to map to and extend core governance architecture |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Unspecified |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | Unspecified |
| **Source authority** | Part 13 README boundary description |
| **Verification note** | Status is UNSPECIFIED because this interface is proposed as a future extension point in Part 13 but no contract, schema, or binding is defined in Parts 1–13. It is cataloged as proposed to prevent misinterpretation as an established interface. |

---

### 3.3 Compliance Reporting Interface

| Property | Value |
|---------|-------|
| **Interface ID** | PRO-GOV-REPORT-001 |
| **Interface name** | Compliance reporting interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Exchange compliance reports between Part 13 governance components and external audit frameworks |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Unspecified |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | Unspecified |
| **Source authority** | Part 13 README boundary description |
| **Verification note** | Status is UNSPECIFIED because this interface is proposed as a future extension point in Part 13 but no contract, schema, or binding is defined in Parts 1–13. It is cataloged as proposed to prevent misinterpretation as an established interface. |

---

## 4. Unresolved Interfaces

Unresolved interfaces are referenced in Parts 1–13 as integration points, but with no defined name, contract, event schema, or binding sufficient to inventory as established.

---

### 4.1 External Audit Hook Interface

| Property | Value |
|---------|-------|
| **Interface ID** | UNRES-EXT-AUDIT-001 |
| **Interface name** | External audit hook interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Provide external audit systems access to governance artifacts and audit trails |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Unspecified |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | Unspecified |
| **Source authority** | Part 13 README boundary description |
| **Verification note** | Status is UNSPECIFIED because this integration point is referenced as a boundary concept in Part 13 but no contract, schema, or binding is defined in Parts 1–13. It is cataloged as unresolved to prevent misinterpretation as an established interface. |

---

### 4.2 Policy Import/Export Interface

| Property | Value |
|---------|-------|
| **Interface ID** | UNRES-POLICY-IO-001 |
| **Interface name** | Policy import/export interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Exchange policy artifacts with external governance frameworks |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Unspecified |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | Unspecified |
| **Source authority** | Part 13 README boundary description |
| **Verification note** | Status is UNSPECIFIED because this integration point is referenced as a boundary concept in Part 13 but no contract, schema, or binding is defined in Parts 1–13. It is cataloged as unresolved to prevent misinterpretation as an established interface. |

---

### 4.3 Distributed EventBus Interface

| Property | Value |
|---------|-------|
| **Interface ID** | UNRES-EVT-DIST-001 |
| **Interface name** | Distributed EventBus interface |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Future extension from single-process in-memory EventBus to distributed event routing |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | v1.0 is single-process only |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | ADR-002 (Kernel as Pure Orchestrator) — explicitly out of scope for v1.0 |
| **Source authority** | Part 2 §2.1.4 |
| **Verification note** | Status is UNSPECIFIED because this interface is named as a future extension in Part 2 but explicitly out of scope for v1.0 and no contract is defined in Parts 1–13. It is cataloged as unresolved to prevent misinterpretation as an established interface. |

---

### 4.4 Plugin/Tool Extension Interfaces

| Property | Value |
|---------|-------|
| **Interface ID** | UNRES-PLUGIN-001 |
| **Interface name** | Plugin/tool extension interfaces |
| **Status** | UNSPECIFIED |
| **Provider** | Unspecified |
| **Consumer(s)** | Unspecified |
| **Purpose** | Enable custom formatters, enrichment plugins, transport adapters, and debug extensions without violating service contracts |
| **Direction** | Unspecified |
| **Interaction style** | Unspecified |
| **Protocol/mechanism** | Unspecified |
| **Request contract** | Unspecified |
| **Response contract** | Unspecified |
| **Error contract** | Unspecified |
| **Authentication/authorization requirements** | Unspecified |
| **Timeout expectations** | Unspecified |
| **Retry expectations** | Unspecified |
| **Idempotency requirements** | Unspecified |
| **Versioning strategy** | Unspecified |
| **Compatibility requirements** | Plugins must not violate service contracts or introduce nondeterminism |
| **Related schemas** | Unspecified |
| **Related events** | Unspecified |
| **Related components** | Unspecified |
| **Related ADRs** | ADR-013 (Extension Points Governance) — permits extension points but does not define the plugin contract itself |
| **Source authority** | Part 11 logging, observability, and debug architecture references |
| **Verification note** | Status is UNSPECIFIED because ADR-013 permits extension points but does not define the plugin contract itself, and no concrete plugin contract is defined in Parts 1–13. It is cataloged as unresolved to prevent misinterpretation as an established interface. |

---

## 5. Cross-Part Interface Map

| Interface ID | Source Part(s) | Consumed By |
|-------------|----------------|-------------|
| INT-CORE-CMP-001 | Part 1, Part 3 | HermesKernel, HealthManager |
| INT-CORE-MGR-001 | Part 1, Part 4 | HermesKernel, ObservabilityManager |
| INT-KERNEL-ACC-001 | Part 1 | Core Managers, Engineering Services, Capability Facade Services, Extensions |
| INT-SVC-BASE-001 | Part 4, Part 5, Part 6 | Engineering Services, Capability Facade Services, HumanInteractionService |
| INT-SVC-REG-001 | Part 3 | Services, LifecycleManager, WorkflowManager |
| INT-EVT-BUS-001 | Part 1, Part 2, Part 3 | All kernel entities, governance components |
| INT-SEC-AUTH-001 | Part 4 | Core Managers, Engineering Services, Capability Facade Services, WorkflowManager |
| INT-CFS-BRIDGE-001 | Part 6 | Engineering Services, HumanInteractionService |
| INT-WF-CTRL-001 | Part 4 | Operators, orchestration layers, administrators |
| INT-CONFIG-READ-001 | Part 1, Part 3 | Core Managers, Engineering Services, Capability Facade Services |
| INT-GOV-EVENT-001 | Part 12, Part 13 | Governance services, policy gates, councils, audit service, security domain, observability |
| INT-C12-EVENT-001 | Part 12 | Workflow Manager, Council Manager, agents, runtime, security, observability, governance components |
| INT-HEALTH-001 | Part 1, Part 4, Part 5 | HealthManager |
| INT-ENG-EVENT-001 | Part 5 | WorkflowManager, downstream services, governance services |
| INT-HUMAN-001 | Part 5 | Engineering Services, CouncilService, SecurityManager |

---

## 6. Interface Gaps

These gaps are classified as **GAP** rather than resolved by inventing solutions. They represent integration surfaces referenced in Parts 1–13 but not yet defined with sufficient detail to inventory as established interfaces.

| Gap ID | Description | Source Evidence | Classification |
|--------|-------------|-----------------|----------------|
| GAP-IF-01 | `BaseService` contract schema is referenced in Parts 0/1 but not formally defined as a JSON Schema or data model | Part14/schemas.md §10 GAP-1 | GAP |
| GAP-IF-02 | `HealthStatus` and `ManagerMetrics` schemas are referenced by `ICoreManager.healthCheck()` and `getMetrics()` but not defined in Parts 1–13 | Part14/schemas.md §10 GAP-2 | GAP |
| GAP-IF-03 | `ServiceRegistry` data model (service metadata, dependency DAG shape) is not defined as a schema | Part14/schemas.md §10 GAP-3 | GAP |
| GAP-IF-04 | `StateManager` scope/state schema is referenced (WORKFLOW/SERVICE/GLOBAL/SESSION) but not defined as a serializable schema | Part14/schemas.md §10 GAP-4 | GAP |
| GAP-IF-05 | `RetryBudget` and `RootCauseAnalysis` schemas are referenced in Part 0/4 but not defined as published schemas | Part14/schemas.md §10 GAP-5 | GAP |
| GAP-IF-06 | 51 governance event payloads are enumerated by type in Part 13 but not individually JSON-schematized | Part14/schemas.md §10 GAP-6 | GAP |
| GAP-IF-07 | `defaults.yaml`, environment YAML, and environment variable layer schemas are not fully enumerated | Part14/schemas.md §10 GAP-7 | GAP |
| GAP-IF-08 | `RequirementsSpec`, `TaskSpec`, `TaskDependency`, `EstimationSpec`, `RiskSpec`, `Criterion`, `CouncilDecisionRecord`, `HumanApprovalRecord` sub-schemas are referenced by PlanArtifact but not individually defined in published docs | Part14/schemas.md §10 GAP-8 | GAP |
| GAP-IF-09 | External system integration contracts for MCP servers, LLM/model providers, identity providers, Obsidian vault, Graphify graph store are referenced in architecture but not defined as formal interfaces in Parts 1–13 | Part14/components.md §5 | GAP |
| GAP-IF-10 | Event bus-level authentication/authorization is not defined; governance events carry their own signing/ACL, but the bus-level auth model is unspecified | Part14/interfaces.md §2.6, Part14/components.md §2.2.1 | GAP |

---

## 7. Architecture Integrity and Unsupported Assumptions

This section documents where the interface inventory could not be completed from Parts 1–13 alone, and where assumptions would be required to fill gaps. Per the scope rule, no assumptions have been invented into the inventory above.

### 7.1 NOT YET DEFINED vs. Invented

Throughout this inventory, fields are marked **NOT YET DEFINED** rather than invented. This is a deliberate choice: the inventory's purpose is to catalog what Parts 1–13 establish, not to extend the architecture. Inventing request/response contracts, error semantics, timeout values, or retry policies where Parts 1–13 are silent would create false confidence that those behaviors are established.

### 7.2 Assumptions That Would Be Required to Close Gaps

The following assumptions would be needed to convert the NOT YET DEFINED fields above into concrete contracts. None of these assumptions have been made in this inventory:

| Gap | What Would Need to Be Assumed | Risk of Assuming |
|------|------------------------------|------------------|
| `ICoreComponent` request/response/error | Method signatures, return types, error taxonomy | Would create a contract that may not match implementation |
| `ICoreManager` request/response/error | Method signatures, return types, error taxonomy | Would create a contract that may not match implementation |
| EventBus handler timeout justification | The 30,000 ms default and queue capacities | These values appear in source material but their derivation is not documented |
| `SecurityManager.authorize` error contract | Error types returned on authz failure | Not defined; assuming would lock in an error model |
| `HealthStatus` schema | Field names and types beyond `ready: boolean` | Would create a schema that may not match implementation |
| `ManagerMetrics` schema | Field names and types | Would create a schema that may not match implementation |
| External system contracts | MCP transport protocols, LLM API shapes, identity provider flows | Would invent external integration contracts outside AI-OS scope |

### 7.3 MUST Statement Verification

The following MUST statements from Parts 1–13 have been verified against the source architecture:

| MUST Statement | Source | Verified |
|---------------|--------|----------|
| All inter-component communication MUST occur via EventBus | ADR-001 | Yes — Part 1 §1.7.4, Part 2 §2.2, Part 3 §3.3.4 |
| No direct service-to-service calls | ADR-001, ADR-005 | Yes — stated explicitly in ADR-001 and ADR-005 |
| Every Service MUST extend BaseService | ADR-005 | Yes — Part 4 §4.2, Part 5 §5.2.5 |
| Services MUST declare depends_on | ADR-005 | Yes — Part 3 §3.4.4 |
| Services MUST NOT call other services directly | ADR-005 | Yes — stated explicitly |
| Every event MUST carry correlation_id and causation_id | ADR-008, Part 12 §30 | Yes — Part 2 §2.2, Part 12 §30 |
| Events MUST be immutable | ADR-008 | Yes — Part 2 §2.2, Part 12 §4 |
| Failures MUST be communicated via Events | ADR-009 | Yes — Part 5 §5.14.1 INV-CSI-010 |
| No exceptions crossing service boundaries | ADR-009 | Yes — stated explicitly |
| Configuration MUST use four-layer merge | ADR-010 | Yes — Part 1 §1.10.2, Part 3 §3.5 |
| Every integration contract MUST carry version identifiers | ADR-011 | Yes — stated explicitly |
| Breaking changes require major version bump | ADR-011 | Yes — stated explicitly |
| Kernel MUST own exactly four Core Components | ADR-002 | Yes — Part 1 §1.7 |
| Kernel MUST NOT contain domain logic | ADR-002 | Yes — stated explicitly |
| The 13 get_xxx()/set_xxx() accessor pairs are architectural fixtures | ADR-004 | Yes — stated explicitly |
| No additional accessors may be added; no accessor may be removed | Part 1 INV-CM-004 through INV-CM-006 | Yes — stated explicitly |
| All governance events are signed, minimum classification confidential | Part 13 governance-events.md | Yes — stated explicitly |
| At-least-once delivery with event_id dedup window default 24h | Part 13 governance-events.md | Yes — stated explicitly |

### 7.4 Source Material Limitations

The following limitations in Parts 1–13 affect the completeness of this inventory:

1. **No formal interface definition language.** Parts 1–13 describe interfaces in prose and TypeScript-like notation, but do not publish machine-readable interface contracts (e.g., OpenAPI, AsyncAPI, protobuf). This inventory reflects the prose descriptions.

2. **Inconsistent naming conventions.** Part 2 uses `WORKFLOW_STEP_COMPLETED` (PascalCase enum form) while Part 12 uses `workflow.step.completed` (lowercase dotted form). This inventory follows the canonical dotted form from Part 12 as the authoritative wire format.

3. **Proposed interfaces mixed with established concepts.** Parts 12–13 reference external systems, distributed EventBus, and plugin contracts as future work without clearly separating them from established interfaces. This inventory makes that separation explicit.

4. **Schema definitions incomplete.** Many schemas are referenced by name (e.g., `PlanArtifact`, `HealthStatus`, `ManagerMetrics`) but not defined as standalone schemas in Parts 1–13. Part14/schemas.md documents these as GAPs.

5. **Governance namespace ratification pending.** Part 13 §5 registers `governance` as a namespace "subject to ESC ratification per Part 12 §24/§25." The 51 `governance.*` types are therefore ratified-candidate, not fully ratified, until ESC completes its review.

---

## 8. Notes

- This inventory is derived from Parts 1–13 only. Parts 14–15 may extend these interfaces, but such extensions are not inventoried here.
- Where an interface is named in Parts 1–13 but request/response/error contracts are described only informally, those fields are marked **NOT YET DEFINED** rather than invented.
- Part 13 references external regulatory, standards, and organizational governance interfaces as boundary descriptions only; no Part 1–13 document defines concrete contracts for them. Those are cataloged as unresolved.
- Part 2 EventBus and Part 12 event architecture share conceptual overlap. This inventory treats them as separate sources because both are authoritative in their respective Parts.
- This inventory does not classify "Module" as a first-class integration category because Parts 1–13 do not define it as such. De-facto modular extension units (Skills, MCP connections, AI Agency agents, custom memory backends) are captured under their proper categories (Components, Services, Interfaces, External Systems).
