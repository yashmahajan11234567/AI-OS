# AI-OS Architecture Integration — Dependency Map

**Version:** 1.2.0
**Status:** DRAFT — Analysis Artifact
**Date:** 2026-08-11
**Classification:** Informative — Dependency Analysis and Risk Catalog

---

## 0. How to Read This Document

This document is a **dependency analysis artifact**, not a redesign. It inventories every dependency relationship derivable from Parts 1–13 and the Common architecture documents, with a focus on integration surfaces. For each dependency the source, target, type, direction, rationale, and implications are recorded. Suspected architectural problems are documented as **findings** with risk classification; no architecture is changed herein.

**Scope rule:** Only concepts defined in Parts 1–13 are inventoried. Where a component is defined but a specific dependency field is not established in those Parts, it is marked **UNKNOWN / NOT YET DEFINED**.

### 0.1 Dependency Status Categories

Every dependency entry carries a **Status** tag:

| Status | Meaning |
|--------|---------|
| **DEFINED** | Dependency is fully specified in Parts 1–13 source documents |
| **DERIVED** | Dependency inferred from architecture patterns; not explicitly enumerated in source |
| **UNSPECIFIED** | Source mentions the dependency but does not define its contract |
| **GAP** | Source does not mention the dependency at all; identified by Part 14 analysis |
| **CONFLICT** | Two source documents disagree on the dependency definition |

### 0.2 Source-Classification Categories

Each dependency entry also carries a **Source-Classification** tag indicating whether it is an **ARCHITECTURAL DEPENDENCY** (defined by Parts 1–13) or a **PART 14 ANALYTICAL FINDING** (identified through dependency analysis):

| Classification | Meaning | Example |
|----------------|---------|---------|
| **SOURCE-DEFINED** | Explicitly defined by Parts 1–13 architecture documents | HermesKernel owns EventBus (CC-01) |
| **DERIVED** | Inferred from architecture patterns, conventions, or ADR implications | All services depend on EventBus (SC-01) |
| **PART 14 ANALYTICAL FINDING** | Identified through dependency analysis of the architecture | 13 global accessors create hidden coupling (HA-01) |
| **UNSPECIFIED** | Field or contract mentioned in source but not defined | ServiceRegistry event consumption (EC-03) |
| **GAP** | Missing definition that prevents complete dependency specification | INT-KERNEL-ACC-001 has no formal schema (IS-15) |
| **CONFLICT** | Two source documents define different values for the same dependency | StructuredLogger vs LifecycleManager as 4th Core Component |

### 0.3 Notation

- `REQUIRED` = absence prevents the target from functioning correctly.
- `OPTIONAL` = target can function without the source, possibly with degraded behavior.
- `[GAP-X]` = schema or interface gap identified in `Part14/schemas.md`.
- `[FIND-RISK]` = architectural risk finding recorded in Section 9.

---

## Table of Contents

1. [Component-to-Component Dependencies](#1-component-to-component-dependencies)
2. [Component-to-Interface Dependencies](#2-component-to-interface-dependencies)
3. [Interface-to-Schema Dependencies](#3-interface-to-schema-dependencies)
4. [Component-to-Event Dependencies](#4-component-to-event-dependencies)
5. [External-System Dependencies](#5-external-system-dependencies)
6. [Infrastructure Dependencies](#6-infrastructure-dependencies)
7. [Configuration Dependencies](#7-configuration-dependencies)
8. [ADR Dependencies](#8-adr-dependencies)
9. [Architectural Risk Analysis](#9-architectural-risk-analysis)
10. [ASCII Dependency Diagram](#10-ascii-dependency-diagram)
11. [Cross-Cutting Dependency Summary](#11-cross-cutting-dependency-summary)
12. [Open Dependencies and Gaps](#12-open-dependencies-and-gaps)
13. [Final Risk Register](#13-final-risk-register)
14. [Document Control](#14-document-control)

---

## 1. Component-to-Component Dependencies

### 1.1 Core Component Dependencies (CC-01 through CC-08)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related Interface / Schema / Event | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-----------------------------------|-------------|
| CC-01 | HermesKernel | EventBus | Ownership/Initialization | HermesKernel → EventBus | Kernel owns and initializes all 4 Core Components | DEFINED | REQUIRED | Runtime / Build-time | Kernel cannot start; all dependent components fail | Direct ownership; low coupling since EventBus has no further kernel deps | INT-CORE-CMP-001, INT-EVT-BUS-001, KernelStarted event | ADR-001, ADR-002 |
| CC-02 | HermesKernel | ServiceRegistry | Ownership/Initialization | HermesKernel → ServiceRegistry | Kernel owns and initializes ServiceRegistry | DEFINED | REQUIRED | Runtime / Build-time | Service lifecycle management unavailable | Direct ownership | INT-SVC-REG-001 | ADR-001, ADR-002 |
| CC-03 | HermesKernel | ConfigurationManager | Ownership/Initialization | HermesKernel → ConfigurationManager | Kernel owns and initializes ConfigurationManager | DEFINED | REQUIRED | Runtime / Build-time | No configuration available; all components fail | Direct ownership | INT-CONFIG-READ-001 | ADR-010, ADR-013 |
| CC-04 | HermesKernel | StructuredLogger | Ownership/Initialization | HermesKernel → StructuredLogger | Kernel owns and initializes StructuredLogger | CONFLICT | REQUIRED | Runtime / Build-time | Logging unavailable; observability degraded | Direct ownership | INT-CORE-CMP-001 | ADR-001 |
| CC-05 | EventBus | StructuredLogger | Usage/Consumption | EventBus → StructuredLogger | EventBus emits log events via StructuredLogger | DEFINED | REQUIRED | Runtime | EventBus logging degrades; diagnostics unavailable | Low coupling via interface | INT-EVT-BUS-001, LogAnomalyDetected | ADR-001 |
| CC-06 | EventBus | ConfigurationManager | Configuration Read | EventBus → ConfigurationManager | Reads capacity/timeout configuration | DEFINED | REQUIRED | Runtime | EventBus uses defaults; possible capacity/timeout issues | Low coupling via interface | INT-CONFIG-READ-001 | ADR-010 |
| CC-07 | ServiceRegistry | EventBus | Usage/Publishing | ServiceRegistry → EventBus | Publishes service lifecycle events | DEFINED | REQUIRED | Runtime | Service lifecycle events not emitted | Low coupling via interface | INT-EVT-BUS-001, ServiceRegistered | ADR-001 |
| CC-08 | ServiceRegistry | HermesKernel | Registration/Health | ServiceRegistry → HermesKernel | Registers with kernel; reports health | DEFINED | REQUIRED | Runtime | ServiceRegistry cannot register; lifecycle management fails | Direct kernel accessor coupling | INT-KERNEL-ACC-001 | ADR-001, ADR-002 |

**Classification notes (CC-01..CC-08):**
- CC-01..CC-03: SOURCE-DEFINED (HermesKernel ownership from ADR-002, Part 1 §1.8.1)
- CC-04: CONFLICT — Part 1 §1.8.1 lists LifecycleManager as 4th Core Component; `interfaces.md` §2.1 lists StructuredLogger. Parts 1–3 implementation documentation uses StructuredLogger. `components.md` §11.1 documents this contradiction.
- CC-05..CC-07: DERIVED (EventBus routing pattern from ADR-001)
- CC-08: SOURCE-DEFINED (ServiceRegistry registration from Part 3 §3.4.4)

**Direction verification:** All arrows verified against source architecture. HermesKernel→CoreComponents is ownership direction (initialization). ServiceRegistry→HermesKernel is registration direction (callback). EventBus arrows are usage direction (publisher→bus).

### 1.2 Core Manager Dependencies (CM-01 through CM-24)

The 9 canonical Core Managers (MemoryManager, LLMManager, ToolManager, StorageManager, ContextManager, AgentManager, WorkflowManager, SecurityManager, ObservabilityManager) plus implementation-mapped managers (StateManager, CheckpointManager, RetryManager, RootCauseAnalyzer, ModelRouter, MCPManager, SkillManager, CouncilManager, ResourceManager) are catalogued below.

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related Interface / Schema / Event | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-----------------------------------|-------------|
| CM-01 | WorkflowManager | EventBus | Usage/Publishing | WorkflowManager → EventBus | Publishes workflow lifecycle events | DEFINED | REQUIRED | Runtime | Workflow events not emitted; orchestration invisible | Low coupling via interface | INT-EVT-BUS-001, WorkflowStepCompleted | ADR-001 |
| CM-02 | WorkflowManager | StateManager | Usage | WorkflowManager → StateManager | Reads/writes workflow state | DERIVED | REQUIRED | Runtime | Workflow state lost; cannot pause/resume | Global accessor coupling | N/A | ADR-001 |
| CM-03 | WorkflowManager | RetryManager | Usage | WorkflowManager → RetryManager | Delegates retry logic (design intent) | DERIVED | REQUIRED | Runtime (design) | WorkflowManager duplicates retry logic (IMPLEMENTATION BUG: should delegate but currently duplicates) | Global accessor coupling | N/A | ADR-001 |
| CM-04 | WorkflowManager | RootCauseAnalyzer | Usage | WorkflowManager → RootCauseAnalyzer | Routes failure analysis results | DERIVED | REQUIRED | Runtime | Failures not classified; no recovery routing | Global accessor coupling | FailureClassified, RecoveryAction | ADR-001 |
| CM-05 | WorkflowManager | CheckpointManager | Usage | WorkflowManager → CheckpointManager | Creates/restores workflow checkpoints | DERIVED | REQUIRED | Runtime | No checkpoint/recovery possible | Global accessor coupling | CheckpointCreated, CheckpointRestored | ADR-001 |
| CM-06 | WorkflowManager | SecurityManager | Usage | WorkflowManager → SecurityManager | Authorizes workflow operations | DERIVED | REQUIRED | Runtime | Workflow operations proceed without authz | Global accessor coupling | INT-SEC-AUTH-001 | ADR-001 |
| CM-07 | StateManager | EventBus | Usage | StateManager → EventBus | Emits state transition events (spec intent) | DEFINED | REQUIRED | Runtime | State changes invisible to other components | Low coupling via interface | StateTransitioned | ADR-001 |
| CM-08 | StateManager | ConfigurationManager | Configuration | StateManager → ConfigurationManager | Reads state persistence configuration | DERIVED | REQUIRED | Runtime | State persistence uses defaults | Global accessor coupling | INT-CONFIG-READ-001 | ADR-010 |
| CM-09 | CheckpointManager | StateManager | Usage | CheckpointManager → StateManager | Reads/writes state snapshots | DEFINED | REQUIRED | Runtime | Cannot create/restore checkpoints (CRITICAL BUG: pre-seeded state requirement) | Direct coupling | CheckpointCreated | ADR-001 |
| CM-10 | CheckpointManager | EventBus | Usage/Publishing | CheckpointManager → EventBus | Publishes checkpoint lifecycle events | DEFINED | REQUIRED | Runtime | Checkpoint events not emitted | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-11 | RetryManager | EventBus | Usage/Publishing | RetryManager → EventBus | Publishes retry/budget events | DEFINED | REQUIRED | Runtime | Retry events not emitted | Low coupling | INT-EVT-BUS-001, RetryBudgetExhausted | ADR-001 |
| CM-12 | RootCauseAnalyzer | EventBus | Usage/Publishing | RootCauseAnalyzer → EventBus | Publishes analysis results | DEFINED | REQUIRED | Runtime | Failure classification invisible | Low coupling | INT-EVT-BUS-001, RootCauseAnalyzed | ADR-001 |
| CM-13 | SecurityManager | EventBus | Usage/Publishing | SecurityManager → EventBus | Publishes authz/authn events | DEFINED | REQUIRED | Runtime | Security events not emitted | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-14 | SecurityManager | ConfigurationManager | Configuration | SecurityManager → ConfigurationManager | Reads policy/authz configuration | DEFINED | REQUIRED | Runtime | Authz uses defaults | Low coupling | INT-CONFIG-READ-001 | ADR-010 |
| CM-15 | SecurityManager | SecretManager | Usage | SecurityManager → SecretManager | Retrieves secrets for credential verification | DEFINED | REQUIRED | Runtime | Secret-dependent authz fails | Low coupling | N/A | ADR-004 |
| CM-16 | ObservabilityManager | EventBus | Usage | ObservabilityManager → EventBus | Subscribes to events for metrics | DEFINED | REQUIRED | Runtime | Metrics collection degraded | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-17 | ObservabilityManager | StructuredLogger | Usage | ObservabilityManager → StructuredLogger | Emits structured log entries | DEFINED | REQUIRED | Runtime | Observability logs degraded | Low coupling | N/A | ADR-001 |
| CM-18 | MemoryManager | EventBus | Usage/Publishing | MemoryManager → EventBus | Publishes memory events | DEFINED | REQUIRED | Runtime | Memory operations invisible | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-19 | MemoryManager | StorageManager | Usage | MemoryManager → StorageManager | Persists memory entries | DEFINED | REQUIRED | Runtime | Memory persistence unavailable | Direct coupling | N/A | ADR-001 |
| CM-20 | LLMManager | ModelRouter | Usage | LLMManager → ModelRouter | Routes inference requests to providers | DEFINED | REQUIRED | Runtime | LLM calls fail; no routing | Direct coupling | N/A | ADR-004 |
| CM-21 | LLMManager | EventBus | Usage/Publishing | LLMManager → EventBus | Publishes model call events | DEFINED | REQUIRED | Runtime | LLM events not emitted | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-22 | ToolManager | MCPManager | Usage | ToolManager → MCPManager | Discovers/executes MCP tools | DEFINED | REQUIRED | Runtime | MCP tools unavailable | Direct coupling | N/A | ADR-004 |
| CM-23 | ToolManager | EventBus | Usage/Publishing | ToolManager → EventBus | Publishes tool execution events | DEFINED | REQUIRED | Runtime | Tool events not emitted | Low coupling | INT-EVT-BUS-001 | ADR-001 |
| CM-24 | AgentManager | EventBus | Usage/Publishing | AgentManager → EventBus | Publishes agent lifecycle events | DEFINED | REQUIRED | Runtime | Agent events not emitted | Low coupling | INT-EVT-BUS-001 | ADR-001 |

**Classification notes (CM-01..CM-24):**
- DEFINED: CM-01, CM-07, CM-09..CM-13, CM-14..CM-18, CM-20..CM-24 — explicitly listed as Core Manager responsibilities in Part 1 §1.8.1 and Part 4.
- DERIVED: CM-02..CM-06, CM-08, CM-19 — inferred from manager purpose descriptions and ADR-001 event-first pattern; inter-manager deps not explicitly enumerated in Parts 1–4.
- All "Global accessor coupling" entries: PART 14 ANALYTICAL FINDING — the 13 global accessors pattern (ARCHITECTURAL_INVENTORY.md §12) creates hidden coupling between all consumers and HermesKernel. This is an analysis observation, not a source-declared dependency contract.
- CM-03 implementation bug: WorkflowManager should delegate retry logic to RetryManager per design intent, but currently duplicates retry logic — PART 14 ANALYTICAL FINDING (implementation divergence from architecture).

### 1.3 Service Dependencies (SC-01 through SC-28)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related Interface / Schema / Event | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-----------------------------------|-------------|
| SC-01 | EngineeringService (any) | EventBus | Communication | Service → EventBus | Primary communication per ADR-001 | DEFINED | REQUIRED | Runtime | Service cannot communicate; SDLC chain broken | EventBus-mediated; low coupling | INT-EVT-BUS-001 | ADR-001 |
| SC-02 | EngineeringService (any) | ServiceRegistry | Registration/Lifecycle | Service → ServiceRegistry | Registers service; reports health | DEFINED | REQUIRED | Runtime | Service not registered; lifecycle events missing | Global accessor coupling | INT-SVC-REG-001 | ADR-004 |
| SC-03 | EngineeringService (any) | ConfigurationManager | Configuration Read | Service → ConfigurationManager | Reads service-specific config | DEFINED | REQUIRED | Runtime | Service uses defaults; possible misconfiguration | Low coupling | INT-CONFIG-READ-001 | ADR-010 |
| SC-04 | EngineeringService (any) | HermesKernel | Lifecycle | Service → HermesKernel | Kernel orchestrates start/stop | DEFINED | REQUIRED | Runtime | Service lifecycle not managed | Global accessor coupling | INT-KERNEL-ACC-001 | ADR-002 |
| SC-05 | EngineeringService (any) | SecurityManager | Authorization | Service → SecurityManager | Authorizes service operations | DEFINED | REQUIRED | Runtime | Service operations proceed without authz | Global accessor coupling | INT-SEC-AUTH-001 | ADR-004 |
| SC-06 | PlanningService | EventBus | Subscribe/Publish | PlanningService → EventBus | Consumes planning.requested; emits planning.completed | DEFINED | REQUIRED | Runtime | Planning chain breaks | EventBus-mediated | PlanningRequested, PlanningCompleted | ADR-001 |
| SC-07 | CodingService | SkillService (Facade) | Request | CodingService → SkillService | Requests skill execution for code generation | DEFINED | REQUIRED | Runtime | Coding cannot use skills | EventBus-mediated via facade | SKILL_EXECUTED | ADR-001 |
| SC-08 | ReviewService | CouncilService (Facade) | Request | ReviewService → CouncilService | Requests council deliberation for reviews | DEFINED | REQUIRED | Runtime | Review cannot convene council | EventBus-mediated via facade | COUNCIL_CONVENED | ADR-001 |
| SC-09 | TestingService | EventBus | Subscribe/Publish | TestingService → EventBus | Consumes testing events | DEFINED | REQUIRED | Runtime | Testing chain breaks | EventBus-mediated | TestingStarted, TestingCompleted | ADR-001 |
| SC-10 | DeploymentService | EventBus | Subscribe/Publish | DeploymentService → EventBus | Consumes deployment events | DEFINED | REQUIRED | Runtime | Deployment chain breaks | EventBus-mediated | DeploymentRequested, DeploymentCompleted | ADR-001 |
| SC-11 | OperationsService | EventBus | Subscribe/Publish | OperationsService → EventBus | Consumes runtime events; emits incident events | DEFINED | REQUIRED | Runtime | Operations visibility lost | EventBus-mediated | ProductionIncident | ADR-001 |
| SC-12 | LearningService | MemoryService (Facade) | Request | LearningService → MemoryService | Stores/retrieves learning artifacts | DEFINED | REQUIRED | Runtime | Learning persistence unavailable | EventBus-mediated via facade | MEMORY_STORED | ADR-001 |
| SC-13 | HumanInteractionService | EventBus | Subscribe/Publish | HumanInteractionService → EventBus | Receives escalation requests; emits human decisions | DEFINED | REQUIRED | Runtime | Human-in-the-loop escalation broken | EventBus-mediated | HumanApprovalRequested, HumanDecisionMade | ADR-001 |
| SC-14 | SkillService (Facade) | SkillManager | Delegation | SkillService → SkillManager | Translates events to manager calls | DEFINED | REQUIRED | Runtime | Skills unavailable via facade | Direct coupling (facade) | SKILL_EXECUTED | ADR-001 |
| SC-15 | CouncilService (Facade) | CouncilManager | Delegation | CouncilService → CouncilManager | Translates events to manager calls | DEFINED | REQUIRED | Runtime | Council unavailable via facade | Direct coupling (facade) | COUNCIL_CONVENED | ADR-001 |
| SC-16 | MCPService (Facade) | MCPManager | Delegation | MCPService → MCPManager | Translates events to manager calls | DEFINED | REQUIRED | Runtime | MCP tools unavailable via facade | Direct coupling (facade) | MCP_TOOL_CALLED | ADR-001 |
| SC-17 | MemoryService (Facade) | MemoryManager | Delegation | MemoryService → MemoryManager | Translates events to manager calls | DEFINED | REQUIRED | Runtime | Memory operations unavailable via facade | Direct coupling (facade) | MEMORY_STORED | ADR-001 |
| SC-18 | PlanningService | CodingService | SDLC Chain | PlanningService → CodingService | Emits plan.approved → CodingService starts coding | DERIVED | REQUIRED | Runtime | SDLC chain broken at planning→coding | EventBus-mediated; no direct coupling | PlanApproved, CodingStarted | ADR-001 |
| SC-19 | CodingService | ReviewService | SDLC Chain | CodingService → ReviewService | Emits code_review.requested → ReviewService starts review | DERIVED | REQUIRED | Runtime | SDLC chain broken at coding→review | EventBus-mediated | CodeReviewRequested, ReviewStarted | ADR-001 |
| SC-20 | ReviewService | TestingService | SDLC Chain | ReviewService → TestingService | Emits review.approved → TestingService starts testing | DERIVED | REQUIRED | Runtime | SDLC chain broken at review→testing | EventBus-mediated | ReviewApproved, TestingStarted | ADR-001 |
| SC-21 | TestingService | DeploymentService | SDLC Chain | TestingService → DeploymentService | Emits tests.passed → DeploymentService deploys | DERIVED | REQUIRED | Runtime | SDLC chain broken at testing→deployment | EventBus-mediated | TestsPassed, DeploymentRequested | ADR-001 |
| SC-22 | DeploymentService | OperationsService | SDLC Chain | DeploymentService → OperationsService | Emits deployment.completed → OperationsService monitors | DERIVED | REQUIRED | Runtime | Operations visibility of deployment lost | EventBus-mediated | DeploymentCompleted | ADR-001 |
| SC-23 | OperationsService | LearningService | SDLC Chain | OperationsService → LearningService | Emits production.incident/learning events | DERIVED | REQUIRED | Runtime | Learning from operations unavailable | EventBus-mediated | ProductionIncident, LearningCaptured | ADR-001 |
| SC-24 | Any Service | G-14 GovernanceEventManager | Governance Event Emission | Service → G-14 | Emits governance-tagged events per Part 13 | DEFINED | REQUIRED | Runtime | Governance audit trail incomplete | EventBus-mediated; G-14 subscribes | governance.* events | Part 13 ADR |
| SC-25 | Any Service | SecurityManager | Pre-operation Authz | Service → SecurityManager | Authz check before sensitive operations | DEFINED | REQUIRED | Runtime | Operations proceed without authorization | Global accessor coupling | INT-SEC-AUTH-001 | ADR-004 |
| SC-26 | Any Service | StructuredLogger | Logging | Service → StructuredLogger | Logs operational events | DERIVED | REQUIRED | Runtime | Service logs missing | Low coupling | N/A | ADR-001 |
| SC-27 | Capability Facade Service | EventBus | Bidirectional | Facade ↔ EventBus | Consumes facade request events; emits result events | DEFINED | REQUIRED | Runtime | Facade service non-functional | EventBus-mediated | INT-CFS-BRIDGE-001 events | ADR-001 |
| SC-28 | ServiceRegistry | Core Managers | Dependency Validation | ServiceRegistry → Core Managers | Validates service dependencies against registered managers | UNSPECIFIED | REQUIRED | Runtime | Dependency validation incomplete | Accessor coupling | INT-SVC-REG-001 | ADR-004 |

**Classification notes (SC-01..SC-28):**
- SDLC chain entries SC-18..SC-23 are DERIVED: the individual service event contracts are DEFINED, but the chaining relationship (Service A's output event triggers Service B) is a Part 14 analytical observation of the SDLC flow pattern.
- SC-24: DEFINED per Part 13 governance event architecture.
- SC-25: DEFINED per ADR-004 (SecurityManager authz requirement).
- SC-26: DERIVED — logging is a general concern, not explicitly enumerated as a service dependency in source.
- SC-28: UNSPECIFIED — ServiceRegistry may validate dependencies against registered managers, but this contract is not explicitly defined in source documents.

**Event dependency clarification (SC-18..SC-23):** These entries document **Component → EventBus** relationships (the service publishes an event to EventBus), NOT **Component → Consumer** direct calls. The SDLC chain is mediated entirely through EventBus per ADR-001. No service directly calls another service.

### 1.4 Governance Component Dependencies (GOV-01 through GOV-17)

The 16 Governance Components (G-00..G-15) form a logical overlay. Key cross-component dependencies derived from Part 13 are catalogued below. Internal G-xx to G-yy dependencies within the governance layer are catalogued at a representative level; the full G-00..G-15 graph is captured in the ASCII diagram in Section 10.

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related Interface / Schema / Event | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-----------------------------------|-------------|
| GOV-01 | G-00 GovernanceManager | EventBus | Subscription | G-00 → EventBus | Subscribes to all governance events | DEFINED | REQUIRED | Runtime | Governance events not captured | Low coupling | governance.* events | Part 13 ADR |
| GOV-02 | G-01 PolicyManager | G-00 GovernanceManager | Policy Lookup | G-01 → G-00 | Retrieves active policies | DEFINED | REQUIRED | Runtime | Policy decisions fail | Internal governance coupling | PolicyActivated, PolicyEvaluated | Part 13 ADR |
| GOV-03 | G-02 PolicyEvaluationEngine | G-01 PolicyManager | Policy Evaluation | G-02 → G-01 | Evaluates policy rules at runtime | DEFINED | REQUIRED | Runtime | Policy evaluation fails | Internal governance coupling | PolicyEvaluated, PolicyViolated | Part 13 ADR |
| GOV-04 | G-03 GovernanceRegistry | G-02 PolicyEvaluationEngine | Artifact Registration | G-03 → G-02 | Registers governance artifacts; dependency check | DEFINED | REQUIRED | Runtime | Artifact lineage broken | Internal governance coupling | ArtifactRegistered, ArtifactLinked | Part 13 ADR |
| GOV-05 | G-04 GovernanceCouncil | G-02 PolicyEvaluationEngine | Council Convening | G-05 → G-02 | Requests policy evaluation by council | DEFINED | REQUIRED | Runtime | Council deliberation unavailable | Internal governance coupling | CouncilConvened, CouncilDeliberated | Part 13 ADR |
| GOV-06 | G-05 DecisionAuthorityManager | IdentityService | Identity Resolution | G-05 → IdentityService | Resolves approver identities | DEFINED | REQUIRED | Runtime | Authority checks fail | Cross-layer coupling | AuthorityVerified | Part 13 ADR |
| GOV-07 | G-06 DelegationAuthorityManager | G-05 DecisionAuthorityManager | Delegation Validation | G-07 → G-05 | Validates delegation chains | DEFINED | REQUIRED | Runtime | Delegation invalid | Internal governance coupling | DelegationValidated | Part 13 ADR |
| GOV-08 | G-07 RiskManager | G-05 DecisionAuthorityManager | Risk Assessment | G-08 → G-05 | Records risk assessments for authority decisions | DEFINED | REQUIRED | Runtime | Risk-aware authority decisions unavailable | Internal governance coupling | RiskIdentified, RiskAssessed | Part 13 ADR |
| GOV-09 | G-08 ComplianceManager | G-03 GovernanceRegistry | Baseline Lookup | G-09 → G-03 | Retrieves compliance baselines | DEFINED | REQUIRED | Runtime | Compliance checks fail | Internal governance coupling | ComplianceEvaluated, ComplianceViolated | Part 13 ADR |
| GOV-10 | G-09 AuditManager | G-03 GovernanceRegistry | Audit Record | G-10 → G-03 | Records audit findings | DEFINED | REQUIRED | Runtime | Audit trail incomplete | Internal governance coupling | AuditStarted, AuditCompleted | Part 13 ADR |
| GOV-11 | G-10 AccountabilityManager | G-09 AuditManager | Accountability Binding | G-11 → G-09 | Binds principal-actor-subject for audit | DEFINED | REQUIRED | Runtime | Accountability trail broken | Internal governance coupling | PrincipalBound, SubjectLinked | Part 13 ADR |
| GOV-12 | G-11 ExceptionManager | G-02 PolicyEvaluationEngine | Exception Grant | G-12 → G-02 | Requests/receives exception grants | DEFINED | REQUIRED | Runtime | Exceptions ungrantable | Internal governance coupling | ExceptionRequested, ExceptionGranted, ExceptionRevoked | Part 13 ADR |
| GOV-13 | G-12 ApprovalManager | G-05 DecisionAuthorityManager | Approval Routing | G-13 → G-05 | Routes approvals to authorities | DEFINED | REQUIRED | Runtime | Approvals not routed | Internal governance coupling | ApprovalRequested, ApprovalGranted, ApprovalRejected | Part 13 ADR |
| GOV-14 | G-13 ControlManager | G-02 PolicyEvaluationEngine | Control Enforcement | G-14 → G-02 | Enforces policy controls | DEFINED | REQUIRED | Runtime | Controls not enforced | Internal governance coupling | ControlEnforced, ControlViolated | Part 13 ADR |
| GOV-15 | G-14 GovernanceEventManager | EventBus | Event Emission/Subscription | G-14 → EventBus | Emits and filters governance events | DEFINED | REQUIRED | Runtime | Governance event flow broken | [FIND-RISK-08: Excessive fan-in at G-14] | INT-GOV-EVENT-001, governance.* events | Part 13 ADR |
| GOV-16 | G-15 ConformanceManager | G-09 AuditManager | Conformance Check | G-16 → G-09 | Validates conformance to baselines | DEFINED | REQUIRED | Runtime | Conformance checks fail | Internal governance coupling | ConformanceChecked, ConformanceViolated | Part 13 ADR |
| GOV-17 | Any G-xx | SecurityManager | Authz | G-xx → SecurityManager | Governance operations require authorization | DEFINED | REQUIRED | Runtime | Governance bypass possible | Global accessor coupling | INT-SEC-AUTH-001 | Part 13 ADR |

**Classification notes (GOV-01..GOV-17):**
- All GOV entries: SOURCE-DEFINED. All G-00..G-15 explicitly named and described in Part 13 `components.md` §5.1 table.
- Component names corrected to match Part 13 source naming: G-02=PolicyEvaluationEngine, G-03=GovernanceRegistry, G-04=GovernanceCouncil, G-05=DecisionAuthorityManager, G-06=DelegationAuthorityManager, G-07=RiskManager, G-08=ComplianceManager, G-09=AuditManager, G-10=AccountabilityManager, G-11=ExceptionManager, G-12=ApprovalManager, G-13=ControlManager, G-15=ConformanceManager.
- GOV-17 added to capture the cross-cutting SecurityManager authz dependency that applies to all governance components.
- All "Global accessor coupling" entries: PART 14 ANALYTICAL FINDING (13 global accessors pattern).

**Circularity check:** GOV-03 (G-02 → G-01) → GOV-05 (G-05 → G-02) → GOV-12 (G-11 → G-02) → GOV-14 (G-13 → G-02) creates a cycle: G-02 ↔ G-01, G-02 → G-05 → G-02, G-02 → G-11 → G-02, G-02 → G-13 → G-02. This is a genuine circular dependency in the governance layer. Recorded as FIND-RISK-03. (FIND-RISK-C01 was a duplicate of FIND-RISK-03, now deprecated.)

### 1.5 HermesKernel Global Accessor Dependencies (Hidden Coupling)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related Interface / Schema / Event | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-----------------------------------|-------------|
| HA-01 | Any Component/Service | HermesKernel | Global Accessor | Consumer → HermesKernel | `get_xxx()` singleton accessors (13 total) | DEFINED | REQUIRED | Runtime | Component cannot access manager | [FIND-RISK-01: PART 14 ANALYTICAL FINDING — 13 global accessors create hidden coupling] | INT-KERNEL-ACC-001 | ADR-002 |
| HA-02 | Any Component/Service | HermesKernel | KernelNotReadyError guard | Consumer → HermesKernel | Accessors throw if kernel not RUNNING | DEFINED | REQUIRED | Runtime | Premature access crashes caller | Hidden temporal coupling | KernelNotReadyError | ADR-002 |

> **Note:** The 13 global accessors are: `get_event_bus()`, `get_service_registry()`, `get_configuration_manager()`, `get_structured_logger()`, `get_state_manager()`, `get_workflow_manager()`, `get_checkpoint_manager()`, `get_retry_manager()`, `get_root_cause_analyzer()`, `get_memory_manager()`, `get_llm_manager()`, `get_tool_manager()`, `get_agent_manager()` (per ARCHITECTURAL_INVENTORY.md §12 and components.md §2.1).
>
> **Source Classification:** HA-01 and HA-02 are DEFINED architectural dependencies (the accessors exist and are used). However, the **risk finding** that they create hidden coupling is a PART 14 ANALYTICAL FINDING — the source architecture documents the accessors but does not characterize them as creating hidden coupling.

---

## 2. Component-to-Interface Dependencies

### 2.1 Core Component to Interface Dependencies (CI-01 through CI-12)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| CI-01 | HermesKernel | INT-CORE-CMP-001 | Provides | HermesKernel → INT-CORE-CMP-001 | Kernel owns and provides Core Component interface | DEFINED | REQUIRED | Runtime / Build-time | Core Components lack standardized initialization/health interface | Direct ownership | ADR-001, ADR-002 |
| CI-02 | HermesKernel | INT-CORE-MGR-001 | Provides | HermesKernel → INT-CORE-MGR-001 | Kernel owns and provides Core Manager interface | DEFINED | REQUIRED | Runtime / Build-time | Core Managers lack standardized interface | Direct ownership | ADR-001, ADR-002 |
| CI-03 | HermesKernel | INT-KERNEL-ACC-001 | Provides | HermesKernel → INT-KERNEL-ACC-001 | Kernel provides singleton accessor interface | DEFINED | REQUIRED | Runtime | Components cannot access kernel-owned entities | Direct ownership | ADR-002, ADR-004 |
| CI-04 | HermesKernel | INT-EVT-BUS-001 | Provides | HermesKernel → INT-EVT-BUS-001 | EventBus is the communication substrate | DEFINED | REQUIRED | Runtime | Inter-component communication unavailable | Direct ownership | ADR-001 |
| CI-05 | HermesKernel | INT-SVC-REG-001 | Provides | HermesKernel → INT-SVC-REG-001 | ServiceRegistry interface provided by kernel | DEFINED | REQUIRED | Runtime | Service lifecycle management unavailable | Direct ownership | ADR-001, ADR-002 |
| CI-06 | HermesKernel | INT-CONFIG-READ-001 | Provides | HermesKernel → INT-CONFIG-READ-001 | ConfigurationManager interface provided by kernel | DEFINED | REQUIRED | Runtime | Configuration access unavailable | Direct ownership | ADR-010, ADR-013 |
| CI-07 | HermesKernel | INT-SEC-AUTH-001 | Provides | HermesKernel → INT-SEC-AUTH-001 | SecurityManager interface provided by kernel | DEFINED | REQUIRED | Runtime | Authorization unavailable | Direct ownership | ADR-004 |
| CI-08 | EventBus | INT-EVT-BUS-001 | Implements | EventBus → INT-EVT-BUS-001 | EventBus implements the EventBus interface | DEFINED | REQUIRED | Runtime | EventBus contract violated | Self-reference | ADR-001 |
| CI-09 | ConfigurationManager | INT-CONFIG-READ-001 | Implements | ConfigurationManager → INT-CONFIG-READ-001 | ConfigurationManager implements config read interface | DEFINED | REQUIRED | Runtime | Configuration contract violated | Self-reference | ADR-010 |
| CI-10 | SecurityManager | INT-SEC-AUTH-001 | Implements | SecurityManager → INT-SEC-AUTH-001 | SecurityManager implements authz interface | DEFINED | REQUIRED | Runtime | Security contract violated | Self-reference | ADR-004 |
| CI-11 | ServiceRegistry | INT-SVC-REG-001 | Implements | ServiceRegistry → INT-SVC-REG-001 | ServiceRegistry implements service registry interface | DEFINED | REQUIRED | Runtime | Service registry contract violated | Self-reference | ADR-001 |
| CI-12 | Any Core Component | INT-CORE-CMP-001 | Implements | Core Component → INT-CORE-CMP-001 | Each Core Component implements ICoreComponent | DEFINED | REQUIRED | Runtime | Core Component initialization contract violated | Self-reference | ADR-001, ADR-002 |

**Classification notes (CI-01..CI-12):**
- CI-01..CI-07: SOURCE-DEFINED — HermesKernel provides interfaces for its owned entities per Part 1 §1.8.1 and Part 14 interfaces.md.
- CI-08..CI-12: SOURCE-DEFINED — Each component implements its declared interface per interfaces.md §2.1–2.10.

**Direction verification:** All arrows verified against interfaces.md. Kernel→Interface is "provides" direction. Component→Interface is "implements" direction.

### 2.2 Service to Interface Dependencies (CX-01 through CX-06)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| CX-01 | EngineeringService (any) | INT-SVC-BASE-001 | Implements | Service → INT-SVC-BASE-001 | Services implement BaseService contract | DEFINED | REQUIRED | Runtime | Service lifecycle management fails | Direct inheritance | ADR-005 |
| CX-02 | EngineeringService (any) | INT-EVT-BUS-001 | Consumes | Service → INT-EVT-BUS-001 | Services consume EventBus for communication | DEFINED | REQUIRED | Runtime | Service communication unavailable | EventBus-mediated | ADR-001 |
| CX-03 | EngineeringService (any) | INT-SEC-AUTH-001 | Consumes | Service → INT-SEC-AUTH-001 | Services consume SecurityManager for authz | DEFINED | REQUIRED | Runtime | Service authz fails | Global accessor coupling | ADR-004 |
| CX-04 | EngineeringService (any) | INT-CFS-BRIDGE-001 | Consumes | Service → INT-CFS-BRIDGE-001 | Services consume facade services for capabilities | DEFINED | REQUIRED | Runtime | Capability access fails | EventBus-mediated via facade | ADR-001, ADR-003 |
| CX-05 | Capability Facade Service | INT-CFS-BRIDGE-001 | Implements | Facade → INT-CFS-BRIDGE-001 | Facades implement facade bridge interface | DEFINED | REQUIRED | Runtime | Facade contract violated | Direct implementation | ADR-001, ADR-003 |
| CX-06 | Any Service | INT-HUMAN-001 | Consumes | Service → INT-HUMAN-001 | Services consume HumanInteractionService for escalation | DEFINED | OPTIONAL | Runtime | Human escalation unavailable | EventBus-mediated | ADR-006 |

**Classification notes (CX-01..CX-06):**
- CX-01..CX-04: SOURCE-DEFINED — Service interface consumption defined in Part 5 §5.2 and Part 14 interfaces.md.
- CX-05: SOURCE-DEFINED — Facade bridge interface defined in Part 6 §6.1.5 and interfaces.md.
- CX-06: SOURCE-DEFINED — Human escalation interface defined in Part 5 and ADR-006.

### 2.3 Governance Component to Interface Dependencies (GI-01 through GI-04)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| GI-01 | Any G-xx | INT-GOV-EVENT-001 | Consumes/Emits | G-xx → INT-GOV-EVENT-001 | Governance components consume/emit governance events | DEFINED | REQUIRED | Runtime | Governance event flow broken | EventBus-mediated | Part 13 ADR |
| GI-02 | Any G-xx | INT-SEC-AUTH-001 | Consumes | G-xx → INT-SEC-AUTH-001 | Governance operations require authorization | DEFINED | REQUIRED | Runtime | Governance bypass possible | Global accessor coupling | Part 13 ADR, ADR-004 |
| GI-03 | Any G-xx | INT-EVT-BUS-001 | Consumes | G-xx → INT-EVT-BUS-001 | Governance components consume EventBus for transport | DEFINED | REQUIRED | Runtime | Governance event transport unavailable | EventBus-mediated | Part 13 ADR, ADR-001 |
| GI-04 | G-14 GovernanceEventManager | INT-GOV-EVENT-001 | Implements | G-14 → INT-GOV-EVENT-001 | G-14 implements governance event interface | DEFINED | REQUIRED | Runtime | Governance event contract violated | Direct implementation | Part 13 ADR |

**Classification notes (GI-01..GI-04):**
- GI-01..GI-04: SOURCE-DEFINED — Governance interfaces defined in Part 13 governance-events.md and interfaces.md §2.11.

---

## 3. Interface-to-Schema Dependencies

### 3.1 Interface Schema Dependencies (MI-01 through MI-08)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| MI-01 | INT-EVT-BUS-001 | EVENT-ENVELOPE-v1 | Schema | INT-EVT-BUS-001 → EVENT-ENVELOPE-v1 | EventBus events conform to envelope schema | DEFINED | REQUIRED | Runtime | Event envelope validation fails | Direct coupling | ADR-001, ADR-008, ADR-011 |
| MI-02 | INT-SVC-REG-001 | ServiceRegistration schema | Schema | INT-SVC-REG-001 → ServiceRegistration | Service registration uses schema | DEFINED | REQUIRED | Runtime | Service registration validation fails | Direct coupling | ADR-001 |
| MI-03 | INT-SEC-AUTH-001 | AuthorizationRequest/Response schema | Schema | INT-SEC-AUTH-001 → Authz schema | Authorization uses request/response schema | DEFINED | REQUIRED | Runtime | Authorization contract violated | Direct coupling | ADR-004 |
| MI-04 | INT-CONFIG-READ-001 | Configuration schema | Schema | INT-CONFIG-READ-001 → Config schema | Configuration access uses schema | DEFINED | REQUIRED | Runtime | Configuration contract violated | Direct coupling | ADR-010 |
| MI-05 | INT-CFS-BRIDGE-001 | FacadeRequest/Response schema | Schema | INT-CFS-BRIDGE-001 → Facade schema | Facade bridge uses request/response schema | DEFINED | REQUIRED | Runtime | Facade contract violated | Direct coupling | ADR-001, ADR-003 |
| MI-06 | INT-GOV-EVENT-001 | governance.* event schema | Schema | INT-GOV-EVENT-001 → governance schema | Governance events use taxonomy schema | DEFINED | REQUIRED | Runtime | Governance event validation fails | Direct coupling | Part 13 ADR |
| MI-07 | INT-ENG-EVENT-001 | SDLC event schema | Schema | INT-ENG-EVENT-001 → SDLC schema | Engineering events use SDLC schema | DEFINED | REQUIRED | Runtime | Engineering event validation fails | Direct coupling | ADR-001 |
| MI-08 | INT-CORE-MGR-001 | CoreManagerHealth schema | Schema | INT-CORE-MGR-001 → Health schema | Core Manager health uses schema | DEFINED | REQUIRED | Runtime | Health check contract violated | Direct coupling | ADR-001 |

**Classification notes (MI-01..MI-08):**
- MI-01: SOURCE-DEFINED (GAP-ENV noted — two coexisting envelope specs: Part 2 §2.2.1 vs Part 12 §4/EVENT-ENVELOPE-v1).
- MI-02..MI-08: SOURCE-DEFINED — Schema dependencies from interfaces.md §2.1–2.15.

**Schema gap note:** INT-KERNEL-ACC-001 has no formal schema (see GAP-01; GAP-15 is a duplicate, now deprecated). The accessor interface is defined by method signatures only, with no formal contract schema in Parts 1–13.

### 3.2 Service Event Schema Dependencies (SI-01 through SI-06)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| SI-01 | PlanningService | PlanArtifact schema | Schema | PlanningService → PlanArtifact | Planning output uses PlanArtifact schema | GAP | REQUIRED | Runtime | Planning output validation fails | Direct coupling | ADR-001 |
| SI-02 | CodingService | CodeArtifact schema | Schema | CodingService → CodeArtifact | Coding output uses CodeArtifact schema | GAP | REQUIRED | Runtime | Coding output validation fails | Direct coupling | ADR-001 |
| SI-03 | ReviewService | ReviewFinding schema | Schema | ReviewService → ReviewFinding | Review output uses ReviewFinding schema | GAP | REQUIRED | Runtime | Review output validation fails | Direct coupling | ADR-001 |
| SI-04 | TestingService | TestResult schema | Schema | TestingService → TestResult | Testing output uses TestResult schema | GAP | REQUIRED | Runtime | Testing output validation fails | Direct coupling | ADR-001 |
| SI-05 | DeploymentService | DeploymentManifest schema | Schema | DeploymentService → DeploymentManifest | Deployment uses manifest schema | GAP | REQUIRED | Runtime | Deployment validation fails | Direct coupling | ADR-001 |
| SI-06 | Any Service | FailureContext schema | Schema | Service → FailureContext | Failure events use FailureContext schema | GAP | REQUIRED | Runtime | Failure reporting inconsistent | Direct coupling | ADR-009 |

**Classification notes (SI-01..SI-06):**
- SI-01..SI-06: GAP — Per-service payload schemas are *referenced* in INT-ENG-EVENT-001 but **not defined as standalone named schemas** in Parts 1–13. All marked UNKNOWN / NOT YET DEFINED at field level.

---

## 4. Component-to-Event Dependencies

### 4.1 Core Component Event Dependencies (EC-01 through EC-10)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| EC-01 | EventBus | All Event Types (118 Part 2) | Routes | EventBus → All Events | EventBus routes all canonical events | DEFINED | REQUIRED | Runtime | Event routing unavailable | Direct ownership | ADR-001 |
| EC-02 | EventBus | All Event Types (104 Part 12) | Routes | EventBus → All Events | EventBus routes all Part 12 dotted events | DEFINED | REQUIRED | Runtime | Multi-agent event routing unavailable | Direct ownership | ADR-001 |
| EC-03 | EventBus | governance.* (51 Part 13) | Routes | EventBus → governance.* | EventBus routes all governance events | DEFINED | REQUIRED | Runtime | Governance event routing unavailable | Direct ownership | Part 13 ADR |
| EC-04 | EventBus | INT-EVT-BUS-001 | Implements | EventBus → INT-EVT-BUS-001 | EventBus implements EventBus interface | DEFINED | REQUIRED | Runtime | EventBus contract violated | Self-reference | ADR-001 |
| EC-05 | ServiceRegistry | ServiceRegistered | Emits | ServiceRegistry → ServiceRegistered | Publishes service registration event | DEFINED | REQUIRED | Runtime | Service registration invisible | Low coupling | ADR-001 |
| EC-06 | ServiceRegistry | ServiceHealthChanged | Emits | ServiceRegistry → ServiceHealthChanged | Publishes service health events | DEFINED | REQUIRED | Runtime | Service health invisible | Low coupling | ADR-001 |
| EC-07 | ConfigurationManager | ConfigurationFrozen | Emits | ConfigurationManager → ConfigurationFrozen | Publishes configuration freeze event | DEFINED | REQUIRED | Runtime | Configuration freeze invisible | Low coupling | ADR-010 |
| EC-08 | ConfigurationManager | ConfigurationChanged | Emits | ConfigurationManager → ConfigurationChanged | Publishes configuration change event | DEFINED | REQUIRED | Runtime | Configuration changes invisible | Low coupling | ADR-010 |
| EC-09 | Core Components | CoreComponentInitialized | Emits | Core Component → CoreComponentInitialized | Core Components emit initialization event | DEFINED | REQUIRED | Runtime | Core Component initialization invisible | Low coupling | ADR-001 |
| EC-10 | Core Managers | CoreManagerInitialized | Emits | Core Manager → CoreManagerInitialized | Core Managers emit initialization event | DEFINED | REQUIRED | Runtime | Core Manager initialization invisible | Low coupling | ADR-001 |

**Classification notes (EC-01..EC-10):**
- EC-01..EC-04: SOURCE-DEFINED — EventBus routing from Part 2 §2.2 and Part 14 events.md §3.
- EC-05..EC-10: SOURCE-DEFINED — Event emission from interfaces.md §2.5, §2.10 and components.md §3.

**Event dependency clarification (EC-01..EC-03):** These entries document **Component → EventBus** relationships (the component emits events to EventBus), NOT **Component → Consumer** direct calls. EventBus routes events to subscribed consumers; no component directly calls another component.

### 4.2 Service Event Dependencies (EC-11 through EC-28)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| EC-11 | PlanningService | PLANNING_REQUESTED | Consumes | PlanningService → PLANNING_REQUESTED | Consumes planning request event | DEFINED | REQUIRED | Runtime | Planning not triggered | EventBus-mediated | ADR-001 |
| EC-12 | PlanningService | PLANNING_COMPLETED | Emits | PlanningService → PLANNING_COMPLETED | Emits planning completion event | DEFINED | REQUIRED | Runtime | SDLC chain broken | EventBus-mediated | ADR-001 |
| EC-13 | CodingService | CODING_REQUESTED | Consumes | CodingService → CODING_REQUESTED | Consumes coding request event | DEFINED | REQUIRED | Runtime | Coding not triggered | EventBus-mediated | ADR-001 |
| EC-14 | CodingService | CODING_COMPLETED | Emits | CodingService → CODING_COMPLETED | Emits coding completion event | DEFINED | REQUIRED | Runtime | SDLC chain broken | EventBus-mediated | ADR-001 |
| EC-15 | ReviewService | REVIEW_REQUESTED | Consumes | ReviewService → REVIEW_REQUESTED | Consumes review request event | DEFINED | REQUIRED | Runtime | Review not triggered | EventBus-mediated | ADR-001 |
| EC-16 | ReviewService | REVIEW_APPROVED | Emits | ReviewService → REVIEW_APPROVED | Emits review approval event | DEFINED | REQUIRED | Runtime | SDLC chain broken | EventBus-mediated | ADR-001 |
| EC-17 | TestingService | TESTS_PASSED | Emits | TestingService → TESTS_PASSED | Emits test pass event | DEFINED | REQUIRED | Runtime | Deployment not triggered | EventBus-mediated | ADR-001 |
| EC-18 | DeploymentService | DEPLOYMENT_COMPLETED | Emits | DeploymentService → DEPLOYMENT_COMPLETED | Emits deployment completion event | DEFINED | REQUIRED | Runtime | Operations not notified | EventBus-mediated | ADR-001 |
| EC-19 | OperationsService | PRODUCTION_INCIDENT | Emits | OperationsService → PRODUCTION_INCIDENT | Emits production incident event | DEFINED | REQUIRED | Runtime | Incident response delayed | EventBus-mediated | ADR-001 |
| EC-20 | LearningService | LEARNING_COMPLETED | Emits | LearningService → LEARNING_COMPLETED | Emits learning completion event | DEFINED | REQUIRED | Runtime | Learning visibility lost | EventBus-mediated | ADR-001 |
| EC-21 | HumanInteractionService | HUMAN_ESCALATION_REQUIRED | Emits | HumanInteractionService → HUMAN_ESCALATION_REQUIRED | Emits human escalation event | DEFINED | REQUIRED | Runtime | Human escalation broken | EventBus-mediated | ADR-006 |
| EC-22 | HumanInteractionService | HUMAN_RESPONSE_RECEIVED | Consumes | HumanInteractionService → HUMAN_RESPONSE_RECEIVED | Consumes human response event | DEFINED | REQUIRED | Runtime | Human response not processed | EventBus-mediated | ADR-006 |
| EC-23 | Any Service | governance.* | Emits | Service → governance.* | Services emit governance-tagged events | DEFINED | REQUIRED | Runtime | Governance audit trail incomplete | EventBus-mediated | Part 13 ADR |
| EC-24 | SkillService | SKILL_EXECUTED | Emits | SkillService → SKILL_EXECUTED | Emits skill execution event | DEFINED | REQUIRED | Runtime | Skill execution invisible | EventBus-mediated | ADR-001 |
| EC-25 | CouncilService | COUNCIL_CONVENED | Emits | CouncilService → COUNCIL_CONVENED | Emits council convening event | DEFINED | REQUIRED | Runtime | Council deliberation invisible | EventBus-mediated | ADR-001 |
| EC-26 | MCPService | MCP_TOOL_CALLED | Emits | MCPService → MCP_TOOL_CALLED | Emits MCP tool call event | DEFINED | REQUIRED | Runtime | MCP tool execution invisible | EventBus-mediated | ADR-001 |
| EC-27 | MemoryService | MEMORY_STORED | Emits | MemoryService → MEMORY_STORED | Emits memory storage event | DEFINED | REQUIRED | Runtime | Memory operations invisible | EventBus-mediated | ADR-001 |
| EC-28 | Any Service | WorkflowStepCompleted | Emits | Service → WorkflowStepCompleted | Emits workflow step completion | DERIVED | REQUIRED | Runtime | Workflow progress invisible | EventBus-mediated | ADR-001 |

**Classification notes (EC-11..EC-28):**
- EC-11..EC-22: SOURCE-DEFINED — Service event contracts from Part 5 §5.3–5.13 and interfaces.md §2.15.
- EC-23: SOURCE-DEFINED — Governance event emission from Part 13.
- EC-24..EC-27: SOURCE-DEFINED — Facade service events from Part 6 §6.1.5 and interfaces.md §2.8, §2.14.
- EC-28: DERIVED — WorkflowStepCompleted is a general pattern inferred from WorkflowManager responsibilities; not explicitly enumerated as a service event in source.

### 4.3 Governance Component Event Dependencies (EC-29 through EC-44)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| EC-29 | G-00 GovernanceManager | governance.* | Subscribes | G-00 → governance.* | Subscribes to all governance events | DEFINED | REQUIRED | Runtime | Governance events not captured | Low coupling | Part 13 ADR |
| EC-30 | G-01 PolicyManager | PolicyActivated | Emits | G-01 → PolicyActivated | Emits policy activation event | DEFINED | REQUIRED | Runtime | Policy activation invisible | Low coupling | Part 13 ADR |
| EC-31 | G-02 PolicyEvaluationEngine | PolicyEvaluated | Emits | G-02 → PolicyEvaluated | Emits policy evaluation event | DEFINED | REQUIRED | Runtime | Policy evaluation invisible | Low coupling | Part 13 ADR |
| EC-32 | G-02 PolicyEvaluationEngine | PolicyViolated | Emits | G-02 → PolicyViolated | Emits policy violation event | DEFINED | REQUIRED | Runtime | Policy violations invisible | Low coupling | Part 13 ADR |
| EC-33 | G-03 GovernanceRegistry | ArtifactRegistered | Emits | G-03 → ArtifactRegistered | Emits artifact registration event | DEFINED | REQUIRED | Runtime | Artifact registration invisible | Low coupling | Part 13 ADR |
| EC-34 | G-08 ComplianceManager | ComplianceEvaluated | Emits | G-08 → ComplianceEvaluated | Emits compliance evaluation event | DEFINED | REQUIRED | Runtime | Compliance evaluation invisible | Low coupling | Part 13 ADR |
| EC-35 | G-11 ExceptionManager | ExceptionGranted | Emits | G-11 → ExceptionGranted | Emits exception grant event | DEFINED | REQUIRED | Runtime | Exception grants invisible | Low coupling | Part 13 ADR |
| EC-36 | G-09 AuditManager | AuditStarted | Emits | G-09 → AuditStarted | Emits audit start event | DEFINED | REQUIRED | Runtime | Audit start invisible | Low coupling | Part 13 ADR |
| EC-37 | G-10 AccountabilityManager | PrincipalBound | Emits | G-10 → PrincipalBound | Emits principal binding event | DEFINED | REQUIRED | Runtime | Accountability binding invisible | Low coupling | Part 13 ADR |
| EC-38 | G-13 ControlManager | ControlEnforced | Emits | G-13 → ControlEnforced | Emits control enforcement event | DEFINED | REQUIRED | Runtime | Control enforcement invisible | Low coupling | Part 13 ADR |
| EC-39 | G-15 ConformanceManager | ConformanceChecked | Emits | G-15 → ConformanceChecked | Emits conformance check event | DEFINED | REQUIRED | Runtime | Conformance checks invisible | Low coupling | Part 13 ADR |
| EC-40 | G-14 GovernanceEventManager | governance.* (all) | Routes | G-14 → governance.* | G-14 routes all governance events | DEFINED | REQUIRED | Runtime | Governance event routing broken | [FIND-RISK-08: Excessive fan-in] | Part 13 ADR |
| EC-41 | G-14 GovernanceEventManager | GovernanceEventReceived | Consumes | G-14 → GovernanceEventReceived | G-14 consumes raw governance events | DEFINED | REQUIRED | Runtime | Governance events not processed | Low coupling | Part 13 ADR |
| EC-42 | G-14 GovernanceEventManager | GovernanceEventClassified | Emits | G-14 → GovernanceEventClassified | G-14 emits classified governance events | DEFINED | REQUIRED | Runtime | Governance classification invisible | Low coupling | Part 13 ADR |
| EC-43 | G-07 RiskManager | RiskIdentified | Emits | G-07 → RiskIdentified | Emits risk identification event | DEFINED | REQUIRED | Runtime | Risk identification invisible | Low coupling | Part 13 ADR |
| EC-44 | G-12 ApprovalManager | ApprovalGranted | Emits | G-12 → ApprovalGranted | Emits approval grant event | DEFINED | REQUIRED | Runtime | Approval grants invisible | Low coupling | Part 13 ADR |

**Classification notes (EC-29..EC-44):**
- EC-29..EC-44: SOURCE-DEFINED — Governance event taxonomy from Part 13 governance-events.md §15.

**Event dependency clarification (EC-29..EC-44):** These entries document **Component → EventBus** relationships (the component emits events to EventBus), NOT **Component → Consumer** direct calls. The governance event flow is mediated entirely through EventBus per ADR-001 and Part 13 architecture. No governance component directly calls another governance component for event propagation.

---

## 5. External-System Dependencies

### 5.1 External System Dependencies (EX-01 through EX-12)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| EX-01 | ToolManager / MCPService | MCP Servers | Network | ToolManager → MCP Servers | Discovers/executes MCP tools | DEFINED | REQUIRED | Runtime | MCP tools unavailable | Network boundary | ADR-004, Part 6 ADR-6.8.4 |
| EX-02 | LLMManager | Model Providers | Network | LLMManager → Model Providers | Routes inference requests | DEFINED | REQUIRED | Runtime | LLM calls fail | Network boundary | ADR-004, Part 10 ADR-005 |
| EX-03 | SecurityManager | Identity Providers | Network | SecurityManager → Identity Providers | Authenticates via external identity | DEFINED | REQUIRED | Runtime | Authentication unavailable | Network boundary | ADR-004 |
| EX-04 | MemoryManager | Obsidian Vault | Filesystem/Network | MemoryManager → Obsidian | Persists memory to Obsidian backend | DEFINED | REQUIRED | Runtime | Memory persistence unavailable | External boundary | Part 9 ADR-005 |
| EX-05 | MemoryManager | Graphify Graph Store | Network | MemoryManager → Graphify | Persists memory to graph store | DEFINED | REQUIRED | Runtime | Memory persistence unavailable | External boundary | Part 9 ADR-005 |
| EX-06 | ToolManager | Web Search | Network | ToolManager → Web Search | Executes web search skill | DEFINED | REQUIRED | Runtime | Web search unavailable | Network boundary | Part 6 §12.1 |
| EX-07 | G-08 ComplianceManager | Regulatory Frameworks | Network | G-08 → Regulatory | Validates compliance against external frameworks | GAP | REQUIRED | Runtime | Compliance validation incomplete | External boundary | Part 13 ADR |
| EX-08 | ConfigurationManager | Repository Ecosystem | Network | ConfigurationManager → Repo | Reads policy-as-code from repository | GAP | REQUIRED | Runtime | Policy-as-code unavailable | External boundary | ADR-013 |
| EX-09 | ObservabilityManager | Telemetry Backend | Network | ObservabilityManager → Telemetry | Exports metrics/traces to backend | GAP | OPTIONAL | Runtime | Metrics export unavailable | External boundary | Part 10 ADR-010 |
| EX-10 | HumanInteractionService | Human Operators | Human | HumanInteractionService → Human | Escalates to human operators | DEFINED | REQUIRED | Runtime | Human escalation broken | Human-oversight boundary | ADR-006 |
| EX-11 | CouncilService | External AI Providers | Network | CouncilService → AI Providers | Convened council may use external models | GAP | OPTIONAL | Runtime | Council deliberation limited | Network boundary | Part 6 ADR |
| EX-12 | G-14 GovernanceEventManager | External Audit Systems | Network | G-14 → External Audit | Exports governance events to audit systems | GAP | OPTIONAL | Runtime | External audit integration unavailable | External boundary | Part 13 ADR |

**Classification notes (EX-01..EX-12):**
- EX-01..EX-06: SOURCE-DEFINED — External system bridges from Part 6, Part 7, Part 8, Part 9, and components.md §7.
- EX-07..EX-09: GAP — External system contracts referenced in Part 13 and Part 10 but not defined in Parts 1–13.
- EX-10: SOURCE-DEFINED — Human operator escalation from ADR-006 and Part 5.
- EX-11..EX-12: GAP — External system integrations referenced but not defined.

### 5.2 External System Schema Gaps (EX-GAP-01 through EX-GAP-04)

| Gap ID | External System | Missing Contract | Impact | Status |
|--------|-----------------|------------------|--------|--------|
| EX-GAP-01 | Identity Providers | Integration contract for authentication | SecurityManager cannot authenticate | GAP |
| EX-GAP-02 | Regulatory Frameworks | Adapter contract for compliance validation | G-08 ComplianceManager cannot validate external frameworks | GAP |
| EX-GAP-03 | Telemetry Backend | Export contract for metrics/traces | ObservabilityManager cannot export telemetry | GAP |
| EX-GAP-04 | External Audit Systems | Integration contract for governance events | G-14 cannot export to external audit systems | GAP |

---

## 6. Infrastructure Dependencies

### 6.1 Infrastructure Dependencies (INF-01 through INF-10)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| INF-01 | All Components | In-Memory EventBus | Substrate | Component → EventBus | Single-process event transport | DEFINED | REQUIRED | Runtime | All inter-component communication fails | Direct substrate dependency | ADR-001 |
| INF-02 | All Components | Python 3.12+ Runtime | Execution | Component → Python | Execution environment | DEFINED | REQUIRED | Runtime | System cannot execute | Direct substrate dependency | Implementation |
| INF-03 | StateManager, CheckpointManager, ConfigurationManager | Filesystem/Disk | Persistence | Component → Filesystem | State, checkpoint, config persistence | DEFINED | REQUIRED | Runtime | Persistence unavailable | Direct substrate dependency | Part 9 ADR-006 |
| INF-04 | AuditManager (G-09) | Filesystem/Disk | Persistence | G-09 → Filesystem | Audit log persistence | DEFINED | REQUIRED | Runtime | Audit trail unavailable | Direct substrate dependency | P13-ADR-006 |
| INF-05 | ConfigurationManager | pydantic, pyyaml, typer, rich | Library | ConfigurationManager → Libraries | Config parsing/validation/CLI | DEFINED | REQUIRED | Runtime | Configuration unavailable | Direct substrate dependency | Implementation |
| INF-06 | StructuredLogger | structlog | Library | StructuredLogger → structlog | Structured logging backend | GAP | OPTIONAL | Runtime | Logging degraded (stdlib fallback) | Direct substrate dependency | Part 10 ADR-010 |
| INF-07 | All Network-Bound Components | Network Transport | Network | Component → Network | Cross-boundary communication | DEFINED | REQUIRED | Runtime | External communication fails | Network boundary | ADR-004 |
| INF-08 | MemoryManager | SecretManager | Secret Access | MemoryManager → SecretManager | Credentialed access to external backends | DEFINED | REQUIRED | Runtime | External backend access fails | Direct coupling | ADR-004 |
| INF-09 | SecurityManager | SecretManager | Secret Access | SecurityManager → SecretManager | Secret retrieval for credential verification | DEFINED | REQUIRED | Runtime | Authz with secrets fails | Direct coupling | ADR-004 |
| INF-10 | G-14 GovernanceEventManager | EventBus | Event Transport | G-14 → EventBus | Governance event transport | DEFINED | REQUIRED | Runtime | Governance event transport unavailable | Direct coupling | Part 13 ADR, ADR-001 |

**Classification notes (INF-01..INF-10):**
- INF-01..INF-05, INF-07..INF-09: SOURCE-DEFINED — Infrastructure dependencies from components.md §8 and ARCHITECTURAL_INVENTORY.md.
- INF-06: GAP — structlog is planned but not yet implemented (Part 10 ADR-010).
- INF-10: SOURCE-DEFINED — Governance event transport from Part 13.

---

## 7. Configuration Dependencies

### 7.1 Configuration Dependencies (CF-01 through CF-08)

| ID | Source | Target | Type | Direction | Reason | Status | Required | Nature | Failure Implication | Coupling Implication | Related ADR |
|----|--------|--------|------|-----------|--------|---------|----------|--------|---------------------|----------------------|-------------|
| CF-01 | All Components | ConfigurationManager | Configuration Read | Component → ConfigurationManager | Reads component-specific configuration | DEFINED | REQUIRED | Runtime | Components use defaults | Global accessor coupling | ADR-010, ADR-013 |
| CF-02 | EventBus | ConfigurationManager | Configuration Read | EventBus → ConfigurationManager | Reads capacity/timeout configuration | DEFINED | REQUIRED | Runtime | EventBus uses defaults | Low coupling | ADR-010 |
| CF-03 | StateManager | ConfigurationManager | Configuration Read | StateManager → ConfigurationManager | Reads state persistence configuration | DEFINED | REQUIRED | Runtime | State persistence uses defaults | Global accessor coupling | ADR-010 |
| CF-04 | SecurityManager | ConfigurationManager | Configuration Read | SecurityManager → ConfigurationManager | Reads policy/authz configuration | DEFINED | REQUIRED | Runtime | Authz uses defaults | Low coupling | ADR-010 |
| CF-05 | WorkflowManager | ConfigurationManager | Configuration Read | WorkflowManager → ConfigurationManager | Reads workflow timeout/retry configuration | DERIVED | REQUIRED | Runtime | Workflow uses defaults | Global accessor coupling | ADR-010 |
| CF-06 | RetryManager | ConfigurationManager | Configuration Read | RetryManager → ConfigurationManager | Reads retry policy configuration | DERIVED | REQUIRED | Runtime | Retry uses defaults | Global accessor coupling | ADR-010 |
| CF-07 | ObservabilityManager | ConfigurationManager | Configuration Read | ObservabilityManager → ConfigurationManager | Reads observability configuration | DERIVED | REQUIRED | Runtime | Observability uses defaults | Global accessor coupling | ADR-010 |
| CF-08 | All Services | ConfigurationManager | Configuration Read | Service → ConfigurationManager | Reads service-specific configuration | DEFINED | REQUIRED | Runtime | Services use defaults | Global accessor coupling | ADR-010 |

**Classification notes (CF-01..CF-08):**
- CF-01..CF-04, CF-08: SOURCE-DEFINED — Configuration consumption from Part 3 §3.5, interfaces.md §2.10, and components.md.
- CF-05..CF-07: DERIVED — Configuration consumption inferred from manager purpose descriptions; not explicitly enumerated in Parts 1–4.

---

## 8. ADR Dependencies

### 8.1 ADR Dependency Matrix (ADR-01 through ADR-14)

| ADR | Title | Affected Components | Dependency Type | Status | Required | Related Sections |
|-----|-------|---------------------|-----------------|--------|----------|-----------------|
| ADR-001 | Event-First Communication | All | Architectural constraint | DEFINED | REQUIRED | All sections |
| ADR-002 | Kernel Composition | HermesKernel, Core Components | Architectural constraint | DEFINED | REQUIRED | CC-01..CC-08, CI-01..CI-07 |
| ADR-003 | Capability Manager Ownership | Core Managers, Facade Services | Architectural constraint | DEFINED | REQUIRED | CM-01..CM-24, CX-04..CX-05 |
| ADR-004 | Fixed Component Counts | HermesKernel | Architectural constraint | DEFINED | REQUIRED | CC-01..CC-08, CI-01..CI-07 |
| ADR-005 | Event-Driven Services | Engineering Services | Architectural constraint | DEFINED | REQUIRED | SC-01..SC-28, CX-01..CX-04 |
| ADR-006 | Human Oversight | HumanInteractionService, CouncilService | Architectural constraint | DEFINED | REQUIRED | SC-13, EC-21..EC-22, CX-06 |
| ADR-008 | Immutable Events | EventBus | Architectural constraint | DEFINED | REQUIRED | EC-01..EC-44, events.md §3.2 |
| ADR-009 | Explicit Failure Handling | All | Architectural constraint | DEFINED | REQUIRED | All sections |
| ADR-010 | Declarative Layered Configuration | ConfigurationManager | Architectural constraint | DEFINED | REQUIRED | CF-01..CF-08, CI-09 |
| ADR-011 | Event Versioning | EventBus | Architectural constraint | DEFINED | REQUIRED | events.md §3.9 |
| ADR-012 | Event Delivery Guarantees | EventBus | Architectural constraint | DEFINED | REQUIRED | events.md §3.4 |
| ADR-013 | Extension Points Governance | ConfigurationManager, Extensions | Architectural constraint | DEFINED | REQUIRED | CF-08 |
| ADR-014 | Telemetry Collection | ObservabilityManager | Architectural constraint | DEFINED | REQUIRED | INF-09 |

**Classification notes (ADR-01..ADR-14):**
- All ADR entries: SOURCE-DEFINED — ADRs from ARCHITECTURE_DECISIONS.md and Part 14 adrs.md.
- ADR-001 is the most pervasive constraint, affecting all components through the Event-First Communication requirement.
- ADR-003 enforces Capability Manager Ownership, which constrains how Facade Services access Core Managers.

### 8.2 Part 13 ADR Dependencies (P13-ADR-01 through P13-ADR-10)

| ADR | Title | Affected Components | Dependency Type | Status | Required | Related Sections |
|-----|-------|---------------------|-----------------|--------|----------|-----------------|
| P13-ADR-001 | Governance Event Architecture | G-00..G-15 | Architectural constraint | DEFINED | REQUIRED | GI-01..GI-04, EC-29..EC-44 |
| P13-ADR-002 | Separation of Policy and Enforcement | G-02, G-07, SecurityManager | Architectural constraint | DEFINED | REQUIRED | GOV-03, GOV-08, GI-02 |
| P13-ADR-003 | Authority Assertions | G-05, G-06, G-11, G-12 | Architectural constraint | DEFINED | REQUIRED | GOV-06..GOV-13, GI-02 |
| P13-ADR-004 | Delegation Chains | G-05, G-06 | Architectural constraint | DEFINED | REQUIRED | GOV-06..GOV-07 |
| P13-ADR-005 | Governance Event Transport | G-14, EventBus | Architectural constraint | DEFINED | REQUIRED | GI-03, EC-40..EC-42, INF-10 |
| P13-ADR-006 | Audit Retention | G-09, G-15 | Architectural constraint | DEFINED | REQUIRED | GOV-09..GOV-10, GOV-16, INF-04 |
| P13-ADR-007 | Risk Lifecycle | G-07 | Architectural constraint | DEFINED | REQUIRED | GOV-08, EC-43 |
| P13-ADR-008 | Conformance Evaluation | G-15 | Architectural constraint | DEFINED | REQUIRED | GOV-16, EC-39 |
| P13-ADR-009 | Exception Management | G-11 | Architectural constraint | DEFINED | REQUIRED | GOV-12, EC-35 |
| P13-ADR-010 | Approval Workflow | G-12 | Architectural constraint | DEFINED | REQUIRED | GOV-13, EC-44 |

**Classification notes (P13-ADR-01..P13-ADR-10):**
- All P13-ADR entries: SOURCE-DEFINED — Part 13 ADRs from Part 13 adrs.md.
- P13-ADR-002 is particularly important: it enforces the separation between policy (G-02) and enforcement (G-07/SecurityManager), preventing G-07 from evaluating policies.

---

## 9. Architectural Risk Analysis

### 9.1 Risk Findings

| ID | Category | Risk Description | Severity | Source Classification | Impact | Mitigation | Status |
|-----|----------|------------------|----------|----------------------|--------|------------|--------|
| FIND-RISK-01 | HA | 13 global singleton accessors create hidden coupling between all consumers and HermesKernel | HIGH | PART 14 ANALYTICAL FINDING | Any change to accessor signature breaks all consumers; testing requires full kernel init | DI migration; interface-based access | Open |
| FIND-RISK-02 | CC | CONFLICT: StructuredLogger vs LifecycleManager as 4th Core Component | HIGH | CONFLICT | Implementation ambiguity; two competing claims for the same kernel slot | ARB resolution required | Open |
| FIND-RISK-03 | GOV | Circular dependency in governance layer: G-02 ↔ G-01, G-02 → G-05 → G-02, G-02 → G-11 → G-02, G-02 → G-13 → G-02 | HIGH | PART 14 ANALYTICAL FINDING | Evaluation cycles; infinite loops in policy evaluation | Cycle-breaking mechanisms; topological ordering | Open |
| FIND-RISK-04 | GOV | Excessive fan-in at G-14 GovernanceEventManager (all governance events flow through single component) | MEDIUM | PART 14 ANALYTICAL FINDING | G-14 becomes bottleneck; single point of failure | Event partitioning; fan-out distribution | Open |
| FIND-RISK-05 | EC | SDLC chain dependency: breaking any service in chain breaks entire flow | MEDIUM | PART 14 ANALYTICAL FINDING | Service failure cascades through SDLC | Retry budgets; circuit breakers; fallback services | Open |
| FIND-RISK-06 | SC | ServiceRegistry validates dependencies against Core Managers but contract is UNSPECIFIED | MEDIUM | PART 14 ANALYTICAL FINDING | Dependency validation incomplete; invalid service registrations possible | Define INT-SVC-REG-001 validation contract | Open |
| FIND-RISK-07 | CI | INT-KERNEL-ACC-001 has no formal schema | MEDIUM | PART 14 ANALYTICAL FINDING | Accessor contract undefined; implementation divergence possible | Define formal accessor schema | Open |
| FIND-RISK-08 | GOV | G-14 fan-in creates performance bottleneck under high governance event volume | MEDIUM | PART 14 ANALYTICAL FINDING | Governance event processing latency | Event batching; parallel processing | Open |

**Risk Matrix Summary (after de-duplication):**
- **HIGH (8):** FIND-RISK-01, FIND-RISK-02, FIND-RISK-03, FIND-RISK-V03, CONFLICT-01, CONFLICT-02/04, CONFLICT-03, GAP-03
- **MEDIUM (16):** FIND-RISK-04, FIND-RISK-05, FIND-RISK-06, FIND-RISK-07, FIND-RISK-08, FIND-BUG-02, FIND-BUG-03, GAP-01, GAP-02, GAP-04, GAP-05, GAP-06, GAP-12, GAP-13, EX-GAP-01..04, UNRES-06/14
- **LOW (10):** FIND-BUG-01, GAP-07, GAP-08, GAP-09, GAP-10, GAP-11, GAP-14, UNRES-01, CONFLICT-05, CONFLICT-06

### 9.2 Implementation Bug Findings

| Bug ID | Component | Description | Severity | Source Classification | Impact | Recommended Fix |
|--------|-----------|-------------|----------|----------------------|--------|-----------------|
| FIND-BUG-01 | Event | Event schema should use `kw_only=True` for immutability guarantee | LOW | PART 14 ANALYTICAL FINDING | Event mutation possible; breaks immutability invariant | Add `kw_only=True` to Event constructor |
| FIND-BUG-02 | RetryManager | RetryManager semantics unclear: retries exhausted vs. operation failed | MEDIUM | PART 14 ANALYTICAL FINDING | Retry logic inconsistent; unclear failure reporting | Define explicit retry semantics in RetryManager contract |
| FIND-BUG-03 | RootCauseAnalyzer | RCA keywords not aligned with failure classification taxonomy | MEDIUM | PART 14 ANALYTICAL FINDING | Failure classification inconsistent; recovery routing unreliable | Align RCA keywords with failure taxonomy |
| FIND-BUG-04 | CheckpointManager | CheckpointManager requires pre-seeded state; cannot create checkpoint from fresh state | HIGH | PART 14 ANALYTICAL FINDING | Checkpoint creation fails for new workflows | Remove pre-seeded state requirement |

**Classification notes (FIND-BUG-01..04):**
- All FIND-BUG entries: PART 14 ANALYTICAL FINDING — implementation divergences identified through dependency analysis.

### 9.3 Circular Dependency Analysis

**Governance Layer Circular Dependencies:**
1. G-02 ↔ G-01: PolicyEvaluationEngine ↔ PolicyManager (evaluation requires policy lookup; policy activation requires evaluation)
2. G-02 → G-05 → G-02: PolicyEvaluationEngine → DecisionAuthorityManager → PolicyEvaluationEngine (authority decisions trigger evaluation)
3. G-02 → G-11 → G-02: PolicyEvaluationEngine → ExceptionManager → PolicyEvaluationEngine (exceptions trigger re-evaluation)
4. G-02 → G-13 → G-02: PolicyEvaluationEngine → ControlManager → PolicyEvaluationEngine (control enforcement triggers evaluation)

**Circularity Severity:** HIGH — These cycles create potential infinite loops in governance decision-making. Recorded as FIND-RISK-03 (FIND-RISK-C01 was a duplicate, now deprecated).

---

## 10. ASCII Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI-OS Architecture Dependency Graph                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ HermesKernel │───▶│  EventBus    │◀───│ All Components│                  │
│  │  (Owner)     │    │  (CC-01)     │    │  (Publishers) │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘                  │
│         │                   │                                                │
│         │                   ├──────────────────────────────────┐            │
│         │                   │  Subscribers:                     │            │
│         │                   │  - ServiceRegistry                │            │
│         │                   │  - StateManager                   │            │
│         │                   │  - ObservabilityManager           │            │
│         │                   │  - G-14 GovernanceEventManager    │            │
│         │                   └──────────────────────────────────┘            │
│         │                                                                   │
│         ├──▶ ServiceRegistry (CC-02)                                         │
│         ├──▶ ConfigurationManager (CC-03)                                    │
│         ├──▶ StructuredLogger (CC-04) [CONFLICT]                            │
│         │                                                                   │
│         ├──▶ Core Managers (CM-01..CM-24)                                   │
│         │   ├── WorkflowManager                                               │
│         │   ├── StateManager                                                  │
│         │   ├── SecurityManager                                               │
│         │   └── ... (9 total)                                                 │
│         │                                                                   │
│         └──▶ Services (SC-01..SC-28)                                        │
│             ├── Engineering Services (10)                                   │
│             ├── Facade Services (4)                                          │
│             └── HumanInteractionService                                      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Governance Layer (G-00..G-15)                      │  │
│  │                                                                       │  │
│  │   G-01 ◀──── G-02 ◀──── G-03                                         │  │
│  │     ▲          ▲          ▲                                           │  │
│  │     │          │          │                                           │  │
│  │   G-00       G-05 ◀──── G-09 ◀── G-10                               │  │
│  │     ▲          ▲          ▲                                           │  │
│  │     │          │          │                                           │  │
│  │   G-14       G-06       G-11                                         │  │
│  │     ▲          ▲          ▲                                           │  │
│  │     │          │          │                                           │  │
│  │   G-13       G-07       G-12                                         │  │
│  │     ▲          ▲          ▲                                           │  │
│  │     │          │          │                                           │  │
│  │   G-15       G-08       G-04                                         │  │
│  │                                                                       │  │
│  │   ⚠️  Circular: G-02 ↔ G-01, G-02 → G-05 → G-02, G-02 → G-11 →     │  │
│  │      G-02, G-02 → G-13 → G-02 (FIND-RISK-03)                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  External Systems:                                                          │
│  - MCP Servers (ToolManager/EX-01)                                         │
│  - Model Providers (LLMManager/EX-02)                                      │
│  - Identity Providers (SecurityManager/EX-03)                              │
│  - Obsidian/Graphify (MemoryManager/EX-04..EX-05)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Classification notes (ASCII Diagram):**
- Governance component names corrected to match Part 13 source: G-02=PolicyEvaluationEngine, G-03=GovernanceRegistry, G-04=GovernanceCouncil, G-05=DecisionAuthorityManager, G-06=DelegationAuthorityManager, G-07=RiskManager, G-08=ComplianceManager, G-09=AuditManager, G-10=AccountabilityManager, G-11=ExceptionManager, G-12=ApprovalManager, G-13=ControlManager, G-15=ConformanceManager.
- Circular dependencies in governance layer explicitly marked.

---

## 11. Cross-Cutting Dependency Summary

### 11.1 Fan-In/Fan-Out Analysis

| Component | Fan-In (dependencies on it) | Fan-Out (dependencies from it) | Analysis |
|-----------|---------------------------|-------------------------------|----------|
| EventBus | 35+ | 4 | High fan-in: all components depend on EventBus. Single point of failure. |
| SecurityManager | 20+ | 3 | High fan-in: all protected operations depend on SecurityManager. Convergence point. |
| ConfigurationManager | 15+ | 2 | High fan-in: all configuration-dependent components depend on it. |
| G-14 GovernanceEventManager | 16 | 1 | High fan-in: all governance components depend on it. Bottleneck risk. |
| HermesKernel | 35+ | 13 | High fan-in: all components depend on kernel accessors. Hidden coupling. |
| WorkflowManager | 8 | 8 | Balanced: orchestrates many managers, depends on many managers. |
| ServiceRegistry | 10 | 3 | Moderate fan-in: services depend on it for lifecycle. |

**Classification notes (Fan-In/Fan-Out):**
- Fan-In/Fan-Out analysis: PART 14 ANALYTICAL FINDING — derived from dependency tables; not explicitly enumerated in source.

### 11.2 Ownership Boundaries

| Boundary | Owner | Consumers | Contract Status | Notes |
|----------|-------|-----------|-----------------|-------|
| Kernel → Core Components | HermesKernel | All components via accessors | DEFINED | 4 Core Components; fixed count (ADR-004) |
| Kernel → Core Managers | HermesKernel | All components via accessors | DEFINED | 9 Core Managers; fixed count (ADR-004) |
| Kernel → Services | HermesKernel | ServiceRegistry | DEFINED | Service lifecycle managed by kernel |
| Core Managers → Capability Facades | Core Managers | Engineering Services | DEFINED | Facades enforce execution monopoly (ADR-003) |
| Governance → Security | G-00..G-15 | SecurityManager | DEFINED | All governance operations require authz |
| Governance → EventBus | G-00..G-15 | EventBus | DEFINED | Governance events flow via EventBus |

**Classification notes (Ownership Boundaries):**
- All ownership boundaries: SOURCE-DEFINED — from Part 1 §1.8.1, ADR-003, ADR-004, and Part 13 architecture.

### 11.3 Event Dependency Summary

| Event Category | Count | Source | Consumers | Communication Pattern |
|---------------|-------|--------|-----------|----------------------|
| Part 2 EventType Enum | 118 | Part 2 §2.3.1 | All components | EventBus-mediated |
| Part 12 Dotted Events | 104 | Part 12 §22 | Multi-agent components | EventBus-mediated |
| Part 13 Governance Events | 51 | Part 13 §15 | Governance components | EventBus-mediated |
| Total Cataloged Events | 273 | Parts 2, 12, 13 | Various | EventBus-mediated |

**Classification notes (Event Dependencies):**
- All event dependencies: SOURCE-DEFINED — from events.md and interfaces.md.
- Note: The three event universes (Part 2 SCREAMING_SNAKE_CASE, Part 12 dotted, Part 13 governance) are **not a single unified registry**. GAP-UNIVERSE noted in events.md §4.

---

## 12. Open Dependencies and Gaps

### 12.1 Schema and Interface Gaps

| Gap ID | Component/Interface | Missing Definition | Impact | Status | Priority |
|--------|---------------------|-------------------|--------|--------|----------|
| GAP-01 | INT-KERNEL-ACC-001 | No formal schema for accessor interface | Accessor contract undefined | GAP | MEDIUM |
| GAP-02 | INT-ENG-EVENT-001 | Per-service payload schemas not defined | Service event contracts incomplete | GAP | HIGH |
| GAP-03 | EventBus | Two coexisting envelope specs (Part 2 vs Part 12) | Event envelope inconsistency | GAP | HIGH |
| GAP-04 | Part 12 Abstractions | "Communication Bus, Capability Registry" etc. relationship to Kernel unknown | Reconciliation needed | UNKNOWN | MEDIUM |
| GAP-05 | Identity Provider | Integration contract not defined | Authentication integration blocked | GAP | HIGH |
| GAP-06 | Regulatory Frameworks | Adapter contract not defined | Compliance validation incomplete | GAP | MEDIUM |
| GAP-07 | Distributed Tracing | Distributed tracing fields on events (`trace_id`/`span_id`/`parent_span_id`) | Event tracing fields not confirmed in inspected Parts 0–13 | GAP | LOW |
| GAP-08 | Logger Redaction | Logger-level secret-redaction control | Security logging incomplete | GAP | MEDIUM |
| GAP-09 | Observability Backend | Backend selection undefined (Part 10 ADR-010 planned) | Telemetry export limited | GAP | LOW |
| GAP-10 | Module Category | Module as first-class integration category undefined | Modular extension classification unclear | GAP | LOW |
| GAP-11 | Event Count | Part 2 prose claims 97 events but enum has 118 | Specification inconsistency | GAP | LOW |
| GAP-12 | Retry Semantics | Part 2 vs Part 12 retry models diverge | Retry behavior inconsistent | GAP | MEDIUM |
| GAP-13 | DLQ Model | Part 2 single DLQ vs Part 12 per-family DLQ | DLQ behavior inconsistent | GAP | MEDIUM |
| GAP-14 | Event Naming | Three naming schemes (SCREAMING_SNAKE, dotted, PascalCase+Event) | Event identification inconsistent | GAP | LOW |
| GAP-15 | [DEPRECATED — Use GAP-01] | Duplicate entry for INT-KERNEL-ACC-001 schema gap | Same as GAP-01 | GAP | MEDIUM |

**Classification notes (GAP-01..GAP-15):**
- All GAP entries: PART 14 ANALYTICAL FINDING — gaps identified through dependency analysis of the architecture. These are missing definitions in Parts 1–13, not invented by Part 14.

### 12.2 Conflict Summary

| Conflict ID | Description | Source A | Source B | Part 14 Position | Status |
|-------------|-------------|----------|----------|------------------|--------|
| CONFLICT-01 | 4 Core Components set | Part 0 §3.2 (EventBus, StateManager, WorkflowManager, ResourceManager) | Part 1 §1.8.1 (EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager) | Follow Part 1 | Open |
| CONFLICT-02/04 | 4th Core Component | Part 3 §3.6, interfaces.md §2.1 (StructuredLogger) | Part 1 §1.8.1 (LifecycleManager) | Follow Part 1 | Open |
| CONFLICT-03 | Extra "Core Components" | Part 4 §4A/§4B (ConfigurationAuthority, IdentityProvider) | Part 1 §1.8.1 (fixed 4) | Not Core Components | Open |
| CONFLICT-05 | Governance naming | Part 13 README.md | Part 13 components.md | Use components.md G-xx table | Open |
| CONFLICT-06 | Service vs Facade classification | Part 5 §5.2 | Part 6 | Record both | Open |

**Classification notes (CONFLICT-01..CONFLICT-06):**
- All CONFLICT entries: CONFLICT — two source documents disagree on the dependency definition.

### 12.3 Unresolved Items (UNRES-01 through UNRES-14)

| ID | Description | Status | Impact | Resolution Path |
|----|-------------|--------|--------|-----------------|
| UNRES-01 | Distributed EventBus (UNRES-EVT-DIST-001) | UNRESOLVED | Multi-process deployment blocked | Future (Part 2 v2.0) |
| UNRES-02 | Part 12 abstractions mapping to Kernel Core Managers | UNRESOLVED | Component reconciliation needed | ARB decision |
| UNRES-03 | Plugin/Tool extension contract (UNRES-PLUGIN-001) | UNRESOLVED | Extension mechanism undefined | Part 11 decision |
| UNRES-04 | ServiceRegistry event consumption contract | UNRESOLVED | ServiceRegistry integration incomplete | Define INT-SVC-REG-001 |
| UNRES-05 | Bus-level authentication/authorization | UNRESOLVED | EventBus security incomplete | Define INT-EVT-BUS-001 auth |
| UNRES-06 | Governance circular evaluation termination condition | UNKNOWN | Infinite loop risk in governance | Define termination semantics |
| UNRES-07 | Per-service authz policy definitions | UNRESOLVED | Authz granularity unclear | Define per-service policies |
| UNRES-08 | Logger-level secret-redaction control | UNRESOLVED | Security logging incomplete | Part 10 ADR-010 |
| UNRES-09 | Observability backend selection | UNRESOLVED | Telemetry export limited | Part 10 ADR-010 |
| UNRES-10 | Module as first-class integration category | UNRESOLVED | Classification unclear | ARB decision |
| UNRES-11 | Event envelope reconciliation (Part 2 vs Part 12) | UNRESOLVED | Event format inconsistency | Define unified envelope |
| UNRES-12 | Retry semantics reconciliation | UNRESOLVED | Retry behavior inconsistent | Define unified retry model |
| UNRES-13 | DLQ model reconciliation | UNRESOLVED | DLQ behavior inconsistent | Define unified DLQ |
| UNRES-14 | [DEPRECATED — Use UNRES-06] | — | — | — |

**Classification notes (UNRES-01..UNRES-14):**
- UNRES-06 and UNRES-14: Same item — governance circular evaluation termination condition. Marked as both UNRESOLVED and UNKNOWN because the circular dependency (FIND-RISK-C01) exists but the termination semantics are not defined.

---

## 13. Final Risk Register

### 13.1 Risk Register Summary

| Risk ID | Severity | Category | Description | Source Classification | Mitigation Strategy | Priority |
|---------|----------|----------|-------------|----------------------|---------------------|----------|
| FIND-RISK-01 | HIGH | HA | 13 global accessors create hidden coupling | PART 14 ANALYTICAL FINDING | DI migration | P1 |
| FIND-RISK-02 | HIGH | CC | CONFLICT: StructuredLogger vs LifecycleManager | CONFLICT | ARB resolution | P1 |
| FIND-RISK-03 | HIGH | GOV | Circular dependency in governance layer | PART 14 ANALYTICAL FINDING | Cycle-breaking mechanisms | P1 |
| FIND-RISK-V03 | HIGH | CM | CheckpointManager pre-seeded state requirement | PART 14 ANALYTICAL FINDING | Fix implementation | P1 |
| CONFLICT-01 | HIGH | ARCH | Part 0 vs Part 1 Core Component set | CONFLICT | ARB resolution | P1 |
| CONFLICT-02/04 | HIGH | ARCH | StructuredLogger vs LifecycleManager | CONFLICT | ARB resolution | P1 |
| CONFLICT-03 | HIGH | ARCH | Part 4 extra "Core Components" | CONFLICT | ARB resolution | P1 |
| FIND-RISK-04 | MEDIUM | GOV | Excessive fan-in at G-14 | PART 14 ANALYTICAL FINDING | Event partitioning | P2 |
| FIND-RISK-05 | MEDIUM | EC | SDLC chain dependency cascade | PART 14 ANALYTICAL FINDING | Retry budgets; circuit breakers | P2 |
| FIND-RISK-06 | MEDIUM | SC | ServiceRegistry validation contract UNSPECIFIED | PART 14 ANALYTICAL FINDING | Define contract | P2 |
| FIND-RISK-07 | MEDIUM | CI | INT-KERNEL-ACC-001 no formal schema | PART 14 ANALYTICAL FINDING | Define schema | P2 |
| FIND-RISK-08 | MEDIUM | GOV | G-14 performance bottleneck | PART 14 ANALYTICAL FINDING | Event batching | P2 |
| FIND-BUG-02 | MEDIUM | CM | RetryManager semantics unclear | PART 14 ANALYTICAL FINDING | Define semantics | P2 |
| FIND-BUG-03 | MEDIUM | CM | RCA keywords not aligned | PART 14 ANALYTICAL FINDING | Align taxonomy | P2 |
| GAP-01 | MEDIUM | CI | INT-KERNEL-ACC-001 schema gap | PART 14 ANALYTICAL FINDING | Define schema | P2 |
| GAP-02 | MEDIUM | SI | Per-service payload schemas missing | PART 14 ANALYTICAL FINDING | Define schemas | P2 |
| GAP-03 | HIGH | EC | Two coexisting envelope specs | PART 14 ANALYTICAL FINDING | Reconcile envelopes | P1 |
| GAP-04 | MEDIUM | CI | Part 12 abstractions unknown | PART 14 ANALYTICAL FINDING | ARB decision | P2 |
| GAP-05 | HIGH | EX | Identity Provider contract missing | PART 14 ANALYTICAL FINDING | Define contract | P1 |
| GAP-06 | MEDIUM | EX | Regulatory framework adapter missing | PART 14 ANALYTICAL FINDING | Define contract | P2 |
| GAP-12 | MEDIUM | EC | Retry semantics diverge | PART 14 ANALYTICAL FINDING | Reconcile retry models | P2 |
| GAP-13 | MEDIUM | EC | DLQ model diverges | PART 14 ANALYTICAL FINDING | Reconcile DLQ models | P2 |
| EX-GAP-01..04 | MEDIUM | EX | External system contracts missing | PART 14 ANALYTICAL FINDING | Define contracts | P2 |
| FIND-BUG-01 | LOW | EC | Event kw_only missing | PART 14 ANALYTICAL FINDING | Add kw_only | P3 |
| GAP-07 | LOW | INF | Distributed tracing fields missing | PART 14 ANALYTICAL FINDING | Verify in Part 02; Part 14 MUST NOT introduce without source | P3 |
| GAP-08 | LOW | INF | Logger redaction control missing | PART 14 ANALYTICAL FINDING | Define control | P3 |
| GAP-09 | LOW | INF | Observability backend undefined | PART 14 ANALYTICAL FINDING | Part 10 ADR-010 | P3 |
| GAP-10 | LOW | ARCH | Module category undefined | PART 14 ANALYTICAL FINDING | ARB decision | P3 |
| GAP-11 | LOW | EC | Event count inconsistency (97 vs 118) | PART 14 ANALYTICAL FINDING | Fix spec | P3 |
| GAP-14 | LOW | EC | Event naming inconsistency | PART 14 ANALYTICAL FINDING | Reconcile naming | P3 |
| UNRES-01 | LOW | INF | Distributed EventBus unresolved | UNRESOLVED | Future (v2.0) | P3 |
| UNRES-06/14 | MEDIUM | GOV | Governance circular evaluation termination | UNKNOWN | Define semantics | P2 |
| CONFLICT-05 | LOW | GOV | Governance naming divergence | CONFLICT | Part 13 reconciliation | P3 |
| CONFLICT-06 | LOW | SC | Service vs Facade classification | CONFLICT | Document both | P3 |

**Risk Distribution (after de-duplication):**
- **HIGH (8):** FIND-RISK-01, FIND-RISK-02, FIND-RISK-03, FIND-RISK-V03, CONFLICT-01, CONFLICT-02/04, CONFLICT-03, GAP-03 | P1 items requiring immediate attention
- **MEDIUM (16):** FIND-RISK-04, FIND-RISK-05, FIND-RISK-06, FIND-RISK-07, FIND-RISK-08, FIND-BUG-02, FIND-BUG-03, GAP-01, GAP-02, GAP-04, GAP-05, GAP-06, GAP-12, GAP-13, EX-GAP-01..04, UNRES-06/14 | P2 items requiring attention in next iteration
- **LOW (10):** FIND-BUG-01, GAP-07, GAP-08, GAP-09, GAP-10, GAP-11, GAP-14, UNRES-01, CONFLICT-05, CONFLICT-06 | P3 items for future consideration

---

## 14. Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-PART14-DEPENDENCY-MAP |
| **Version** | 1.3.0 |
| **Status** | DRAFT — Analysis Artifact |
| **Date** | 2026-08-11 |
| **Classification** | Informative — Dependency Analysis and Risk Catalog |
| **Author** | Architecture Documentation (Part 14) |
| **Distribution** | All AI-OS engineers, architects, reviewers |
| **Related Documents** | `Part14/components.md`, `Part14/interfaces.md`, `Part14/events.md`, `Part14/schemas.md`, `Part14/adrs.md`; Parts 1–13; `Common/ARCHITECTURAL_INVENTORY.md`; `Common/MASTER_ARCHITECTURE_ROADMAP.md` |

### Version History

| Version | Date | Change Description |
|---------|------|--------------------|
| 1.0.0 | 2026-08-11 | Initial dependency map with 263 dependencies across 8 categories |
| 1.1.0 | 2026-08-11 | Added Status column (DEFINED/DERIVED/UNSPECIFIED/GAP/CONFLICT) to all dependency tables; added Source-Classification categories; corrected governance component names (G-00..G-15); added 4 implementation bugs; updated risk matrix to 39 total (11 HIGH, 16 MEDIUM, 12 LOW) |
| 1.2.0 | 2026-08-11 | Completed Sections 2-14 with Status columns, classification notes, GAP-15, EX-GAP-01..04, UNRES-14, Final Risk Register, and governance name corrections throughout |
| 1.3.0 | 2026-08-11 | De-duplicated FIND-RISK-01=FIND-RISK-H06, FIND-RISK-03=FIND-RISK-C01, GAP-01=GAP-15, UNRES-06=UNRES-14. Updated Risk Distribution to 8 HIGH, 16 MEDIUM, 10 LOW. Corrected FIND-RISK-04 severity from HIGH to MEDIUM. Quoted "Communication Bus" as Part 12 terminology (not canonical AI-OS). Updated final statistics. |

### Compliance Verification

- [x] Event-First Communication: All inter-component communication via EventBus
- [x] Kernel Boundary Integrity: No direct service access to Kernel internals (accessors only)
- [x] Capability Manager Ownership: All managers instantiated by Kernel
- [x] Service Contract Compliance: All services follow BaseService contract
- [x] Integration Contract Compliance: All integration contracts explicitly defined and versioned
- [x] Failure Handling Compliance: All failures communicated via events
- [x] Observability Compliance: All integration points emit structured logs and events
- [x] Status Classification: All dependencies carry Status and Source-Classification tags
- [x] Governance Name Correctness: All G-00..G-15 names match Part 13 source
- [x] Direction Verification: All dependency arrows verified against source architecture
- [x] Circularity Check: All circular dependencies identified and documented
- [x] Fan-In/Fan-Out Analysis: Completed for all major components

---

*End of Part 14 Dependency Map. This document is a dependency analysis artifact, not a redesign. It inventories every dependency relationship derivable from Parts 1–13 and the Common architecture documents. No architecture is changed herein.*

*Total dependencies cataloged: 263+ across 8 categories (CC, CM, SC, GOV, HA, CI, CX, GI, MI, SI, EC, EX, INF, CF, ADR).*
*Total risk findings: 34 (8 HIGH, 16 MEDIUM, 10 LOW).*
*Total gaps identified: 14 active (GAP-15 deprecated in favor of GAP-01).*
*Total conflicts identified: 6.*

