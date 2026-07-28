# AI-OS Architecture Specification v1.0
## Part 5: Engineering Services Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)
a
---

### 5.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART5 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 5 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (6–N) MUST conform to Part 5. Part 5 MUST NOT contradict Part 0, Part 1, Part 2, Part 3, or Part 4. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles), PART1 (kernel architecture), PART2 (event system), PART3 (core components), PART4 (core managers), PART6 (capability facade services), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis) |

**Conformance Requirement:** Every subsequent Part (6–N) of this specification MUST explicitly reference Part 5 sections for Engineering Service terminology, interfaces, and conformance criteria. Any Part that contradicts Part 5 is non-conformant and MUST be revised.

---

### 5.1 Purpose

#### 5.1.1 Why Engineering Services Exist

Engineering Services exist to implement the **autonomous SDLC pipeline** — the eight phase services that transform intent into deployed, operating, learning software systems. They exist because:

- **SDLC Automation Mandate:** AI-OS must execute end-to-end engineering workflows (Planning → Operations → Learning) without human intervention in the steady state (Part 0 Principle 6).
- **Event-Driven Phase Isolation:** Each SDLC phase must be a replaceable, observable, checkpointable service communicating exclusively via EventBus (Part 0 Principles 1, 5).
- **Governance Integration:** Council consensus, Final Judge decisions, and human escalation gates are first-class architectural concerns, not afterthoughts (Part 0 Principle 3).
- **Capability Abstraction:** Engineering Services consume kernel capabilities (LLM, Tools, Memory, Skills, MCP, ModelRouter) through Capability Facade Services and Core Managers — they do not couple to implementations (Part 0 Principle 7).
- **Failure as Data:** Phase failures emit events (`*_FAILED`, `RETRY_BUDGET_EXHAUSTED`, `ROOT_CAUSE_ANALYZED`) enabling deterministic recovery via WorkflowManager and Core Managers (Part 0 Principle 9, Part 4).

#### 5.1.2 Architectural Role

Engineering Services occupy the **platform layer** above the Hermes Kernel and Core Managers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-OS Platform                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Hermes Kernel                          │   │
│  │  Core Components (4)   Core Managers (9)                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Engineering Services (10)                   │   │
│  │  Planning → Coding → Review → Testing → Deployment      │   │
│  │  → Operations → Learning → Memory                        │   │
│  │  + Council Service + Human Interaction Service           │   │
│  │  (All extend BaseService; EventBus-only communication)  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            Capability Facade Services (4)                │   │
│  │  SkillService • CouncilService • MCPService • MemoryService│   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Positioning:**
- Engineering Services are **BaseService** derivatives (Part 4 §4.2 Service Framework)
- They communicate **exclusively** via EventBus (Part 0 Principle 1, Part 2)
- They consume Core Managers via **singleton accessors** on `HermesKernel.instance` (Part 1 §1.8.4, Part 3 §3.4)
- They consume Capabilities via **Capability Facade Services** (Part 6)
- They are orchestrated by **WorkflowManager** (Part 4 §4.6) for multi-phase execution

#### 5.1.3 Design Goals

| Goal ID | Goal | Success Criterion |
|---------|------|-------------------|
| ENG-DG-001 | **Phase Isolation** | Each service owns exactly one SDLC phase; no phase logic leaks across service imports another's module |
| ENG-DG-002 | **Event-First Communication** | Zero direct service-to-service calls; 100% EventBus mediation (static analysis verified) |
| ENG-DG-003 | **Checkpointable Phases** | Every phase emits `*_COMPLETED` event with artifacts enabling resume from any phase boundary |
| ENG-DG-004 | **Governance Integration** | Council, Final Judge, Human Escalation gates are mandatory events, not optional callbacks |
| ENG-DG-005 | **Capability Abstraction** | Services invoke capabilities via Facade Services; zero direct Core Manager calls for capabilities |
| ENG-DG-006 | **Deterministic Replay** | Given identical input events, phase execution produces bit-for-bit identical output artifacts |
| ENG-DG-007 | **Failure Routing** | All failures route through RCA → Recovery Action → Retry/Escalation event chain |
| ENG-DG-008 | **Learning Closure** | Every phase emits structured learnings consumed by Learning Service for pattern extraction |

#### 5.1.4 Non-Goals

| Non-Goal | Rationale |
|----------|-----------|
| **Implementing LLM Logic** | LLM interactions abstracted via LLMManager → ModelRouter (Part 4) |
| **Implementing Tool Execution** | Tool execution abstracted via ToolManager (Part 4) |
| **Implementing Storage** | Persistence abstracted via StorageManager (Part 4) |
| **Implementing Workflow Orchestration** | Workflow execution governed by WorkflowManager (Part 4 §4.6) |
| **Implementing Security Policy** | Authorization abstracted via SecurityManager (Part 4 §4.7) |
| **Defining UI/UX** | Presentation layer is external consumer concern (Part 0 §0.2.2) |

---

### 5.2 Engineering Service Overview

#### 5.2.1 Service Taxonomy

AI-OS defines **ten (10) Engineering Services** organized into three categories:

| Category | Services | Count | Purpose |
|----------|----------|-------|---------|
| **SDLC Phase Services** | Planning, Coding, Review, Testing, Deployment, Operations | 6 | Execute the linear SDLC pipeline (Part 0 Principle 6) |
| **Knowledge Services** | Learning, Memory, Research, Documentation | 4 | Accumulate, validate, and synchronize engineering knowledge |
| **Governance Services** | Council, Human Interaction | 2 | Mediate consensus, escalation, and human-in-the-loop decisions |

**Total: 10 Engineering Services**

> **Note:** Part 0 §0.2.1 specifies 8 Engineering Services in the linear pipeline (Planning → Operations → Learning). The two Governance Services (Council, Human Interaction) are cross-cutting services that participate in multiple phases but are architecturally distinct Capability Facade Services in Part 6. For Part 5 conformance, all 10 are specified here; Part 6 specifies the Facade Service variants.

#### 5.2.2 Ownership Table

| Service ID | Service Name | Namespace | Type | Owner | Criticality |
|------------|--------------|-----------|------|-------|-------------|
| ES-01 | PlanningService | engineering | SDLC Phase | Architecture Team | CRITICAL |
| ES-02 | CodingService | engineering | SDLC Phase | Architecture Team | CRITICAL |
| ES-03 | ReviewService | engineering | SDLC Phase | Architecture Team | CRITICAL |
| ES-04 | TestingService | engineering | SDLC Phase | Architecture Team | CRITICAL |
| ES-05 | DeploymentService | engineering | SDLC Phase | Architecture Team | CRITICAL |
| ES-06 | OperationsService | engineering | SDLC Phase | Architecture Team | HIGH |
| ES-07 | LearningService | engineering | Knowledge | Architecture Team | HIGH |
| ES-08 | MemoryService | engineering | Knowledge | Architecture Team | HIGH |
| ES-09 | ResearchService | engineering | Knowledge | Architecture Team | MEDIUM |
| ES-10 | DocumentationService | engineering | Knowledge | Architecture Team | MEDIUM |
| ES-11 | CouncilService | facade | Governance | Architecture Team | CRITICAL |
| ES-12 | HumanInteractionService | facade | Governance | Architecture Team | CRITICAL |

#### 5.2.3 Responsibilities Summary

| Service | Primary Responsibility | Phase Trigger Event | Completion Event |
|---------|------------------------|---------------------|------------------|
| **PlanningService** | Transform requirements into executable plan artifacts | `PLANNING_REQUESTED` | `PLANNING_COMPLETED` / `PLANNING_FAILED` |
| **CodingService** | Generate code artifacts from plan specifications | `CODING_REQUESTED` | `CODING_COMPLETED` / `CODING_FAILED` |
| **ReviewService** | Static, architecture, security review with quality gates | `REVIEW_REQUESTED` | `REVIEW_APPROVED` / `REVIEW_REJECTED` / `REVIEW_FAILED` |
| **TestingService** | Orchestrate unit, integration, system, regression, perf, security tests | `TESTING_REQUESTED` | `TESTING_COMPLETED` / `TESTING_FAILED` |
| **DeploymentService** | Manage deployment lifecycle, promotion, rollback, release governance | `DEPLOYMENT_REQUESTED` | `DEPLOYMENT_COMPLETED` / `DEPLOYMENT_FAILED` / `DEPLOYMENT_ROLLED_BACK` |
| **OperationsService** | Runtime operations: monitoring, incident response, scaling, maintenance | `OPERATIONS_REQUESTED` | `OPERATIONS_COMPLETED` / `OPERATIONS_FAILED` |
| **LearningService** | Extract patterns from execution history; refine knowledge base | `LEARNING_REQUESTED` | `LEARNING_COMPLETED` / `LEARNING_FAILED` |
| **MemoryService** | Synchronize working, episodic, semantic memory across backends | `MEMORY_SYNC_REQUESTED` | `MEMORY_SYNC_COMPLETED` / `MEMORY_SYNC_FAILED` |
| **ResearchService** | Execute research workflows; collect evidence; validate knowledge | `RESEARCH_REQUESTED` | `RESEARCH_COMPLETED` / `RESEARCH_FAILED` |
| **DocumentationService** | Generate, version, synchronize documentation artifacts | `DOCUMENTATION_REQUESTED` | `DOCUMENTATION_COMPLETED` / `DOCUMENTATION_FAILED` |
| **CouncilService** | Convene LLM Council; manage voting, consensus, dissent, escalation | `COUNCIL_CONVENED` | `COUNCIL_CONSENSUS_REACHED` / `COUNCIL_DISSENT_REGISTERED` |
| **HumanInteractionService** | Manage human approvals, questions, overrides, feedback, escalations | `HUMAN_ESCALATION_REQUIRED` | `HUMAN_RESPONSE_RECEIVED` / `HUMAN_TIMEOUT` |

#### 5.2.4 Dependency Matrix

Dependencies are declared via `BaseService.depends_on` and validated by ServiceRegistry (Part 3 §3.4). EventBus is the universal implicit dependency.

| Service → | Planning | Coding | Review | Testing | Deployment | Operations | Learning | Memory | Research | Documentation | Council | Human Interaction |
|-----------|----------|--------|--------|---------|------------|------------|----------|--------|----------|---------------|---------|-------------------|
| **PlanningService** | — | — | — | — | — | — | — | ✓ | ✓ | — | ✓ | ✓ |
| **CodingService** | ✓ | — | — | — | — | — | — | ✓ | ✓ | — | ✓ | ✓ |
| **ReviewService** | ✓ | ✓ | — | — | — | — | — | ✓ | — | — | ✓ | ✓ |
| **TestingService** | ✓ | ✓ | ✓ | — | — | — | — | ✓ | — | — | ✓ | ✓ |
| **DeploymentService** | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | — | ✓ | ✓ | ✓ |
| **OperationsService** | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| **LearningService** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — |
| **MemoryService** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| **ResearchService** | ✓ | — | — | — | — | — | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| **DocumentationService** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| **CouncilService** | — | — | — | — | — | — | — | — | — | — | — | ✓ |
| **HumanInteractionService** | — | — | — | — | — | — | — | — | — | — | ✓ | — |

**Legend:** ✓ = declares dependency (consumes events/capabilities); — = no direct dependency

**Dependency Rules (Architectural Invariants):**
- **INV-ENG-DEP-001** — SDLC Phase Services form a strict linear chain: each phase depends only on prior phases
- **INV-ENG-DEP-002** — Knowledge Services depend on all prior SDLC phases (learning from full history)
- **INV-ENG-DEP-003** — Governance Services have no SDLC phase dependencies (they are invoked by phases)
- **INV-ENG-DEP-004** — MemoryService is depended upon by ALL services (ubiquitous context)
- **INV-ENG-DEP-005** — CouncilService and HumanInteractionService are leaf dependencies (no service depends on them except each other)

#### 5.2.5 Lifecycle

All Engineering Services follow the **BaseService lifecycle** (Part 4 §4.2):

```
UNREGISTERED → REGISTERED → INITIALIZING → RUNNING → DEGRADED → FAILED
                                      ↘                         ↘
                                       → SHUTTING_DOWN → SHUTDOWN
```

| Lifecycle Stage | Service Responsibility | Kernel Coordination |
|-----------------|------------------------|---------------------|
| **REGISTERED** | Declare `depends_on`, `capabilities`, `critical` flag; subscribe to trigger events | ServiceRegistry validates DAG (Part 3 §3.4.4) |
| **INITIALIZING** | Initialize internal state; register event handlers; verify capability access | LifecycleManager executes in topological batch (Part 4 §4.3) |
| **RUNNING** | Process events; emit heartbeats; respond to health checks | HealthManager polls `healthCheck()` (Part 4 §4.10) |
| **DEGRADED** | Continue processing with reduced capability; emit `ServiceHealthChanged` | HealthManager marks DEGRADED; LifecycleManager may initiate recovery |
| **FAILED** | Stop processing; emit `ServiceFailed`; preserve state for RCA | LifecycleManager attempts restart (max 2); then escalates |
| **SHUTTING_DOWN** | Drain in-flight work; emit final events; release resources | LifecycleManager coordinates reverse topological shutdown |
| **SHUTDOWN** | Clean up; deregister from ServiceRegistry | ServiceRegistry removes entry |

**Invariant:** `INV-ENG-LC-001` — Service initialization order respects declared `depends_on` DAG.
**Invariant:** `INV-ENG-LC-002` — Service shutdown order is strict reverse of initialization.
**Invariant:** `INV-ENG-LC-003` — Critical services (`critical: true`) failing during RUNNING → kernel FATAL (Part 1 §1.12.1).

---

### 5.3 Planning Service

#### 5.3.1 Purpose

PlanningService transforms **raw requirements** (user intent, issue descriptions, architectural constraints) into **executable plan artifacts** — structured, versioned, reviewable specifications that drive the Coding phase. It is the entry point of the SDLC pipeline.

#### 5.3.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| PL-R-001 | **Requirements Analysis** | Parse, structure, and validate incoming requirements; identify ambiguities |
| PL-R-002 | **Architecture Conformance** | Verify proposed approach conforms to AI-OS Architecture Specification (Parts 0–N) |
| PL-R-003 | **Task Decomposition** | Break requirements into atomic, ordered, dependency-graphed coding tasks |
| PL-R-004 | **Resource Estimation** | Estimate LLM tokens, tool calls, human review time, test scope per task |
| PL-R-005 | **Risk Assessment** | Identify technical risks, security implications, performance concerns, rollback complexity |
| PL-R-006 | **Plan Artifact Generation** | Emit `PlanArtifact` with tasks, dependencies, estimates, risks, acceptance criteria |
| PL-R-007 | **Council Escalation** | For high-risk or architecturally significant plans, convene Council (via CouncilService) |
| PL-R-008 | **Human Approval Gate** | For plans requiring human judgment, escalate via HumanInteractionService |

#### 5.3.3 Planning Lifecycle

```
PLANNING_REQUESTED
       │
       ▼
┌──────────────────┐
│ Requirements     │
│ Ingestion &      │
│ Validation       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Architecture     │
│ Conformance      │
│ Check            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Task             │
│ Decomposition    │
│ & Estimation     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     Council Required? ──YES──▶ [CouncilService] ──▶ Consensus
│ Risk Assessment  │                                    │
└────────┬─────────┘                                    ▼
         │                                    Human Required? ──YES──▶ [HumanInteractionService]
         ▼
┌──────────────────┐
│ Plan Artifact    │
│ Generation       │
└────────┬─────────┘
         │
         ▼
 PLANNING_COMPLETED (with PlanArtifact)  OR  PLANNING_FAILED (with FailureContext)
```

#### 5.3.4 Artifacts

| Artifact | Type | Schema | Persistence |
|----------|------|--------|-------------|
| **PlanArtifact** | `PlanArtifactEvent` payload | `PlanSchema v1.0` | StorageManager (artifacts namespace) |
| **TaskGraph** | Embedded in PlanArtifact | `TaskGraphSchema v1.0` | StorageManager (artifacts namespace) |
| **RiskRegister** | Embedded in PlanArtifact | `RiskRegisterSchema v1.0` | StorageManager (artifacts namespace) |
| **EstimationReport** | Embedded in PlanArtifact | `EstimationSchema v1.0` | StorageManager (artifacts namespace) |

**PlanArtifact Schema (Architectural Notation):**
```
PlanArtifact {
  planId: UUID
  correlationId: UUID
  requirements: RequirementsSpec
  tasks: TaskSpec[]              // Ordered, dependency-graphed
  dependencies: TaskDependency[] // DAG edges
  estimates: EstimationSpec      // Tokens, time, review, test
  risks: RiskSpec[]              // Identified risks with mitigations
  acceptanceCriteria: Criterion[]
  architectureDecisionRefs: ADR[] // Links to relevant ADRs
  councilDecision?: CouncilDecisionRecord
  humanApproval?: HumanApprovalRecord
  createdAt: ISO8601Instant
  version: SemanticVersion
}
```

#### 5.3.5 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `PLANNING_REQUESTED` | Consumed | `PlanningRequestPayload` | User/Workflow submission |
| `PLANNING_COMPLETED` | Emitted | `PlanArtifact` | Successful plan generation |
| `PLANNING_FAILED` | Emitted | `FailureContext` | Unrecoverable planning error |
| `COUNCIL_CONVENED` | Emitted | `CouncilRequestPayload` | High-risk plan requires consensus |
| `HUMAN_ESCALATION_REQUIRED` | Emitted | `HumanEscalationPayload` | Plan requires human judgment |
| `REQUIREMENTS_CLARIFIED` | Emitted | `ClarificationPayload` | Ambiguity resolved via human interaction |

#### 5.3.6 Interaction Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **PlanningTrigger** | WorkflowManager / User | EventBus: `PLANNING_REQUESTED` | Initiates planning with requirements |
| **PlanDelivery** | CodingService | EventBus: `PLANNING_COMPLETED` | Delivers PlanArtifact to next phase |
| **CouncilConsensus** | CouncilService | EventBus: `COUNCIL_CONSENSUS_REACHED` | Records Council decision on plan |
| **HumanApproval** | HumanInteractionService | EventBus: `HUMAN_RESPONSE_RECEIVED` | Records human approval/rejection |
| **MemoryQuery** | MemoryService | EventBus: `MEMORY_RETRIEVE` | Retrieves relevant context for planning |
| **ResearchEvidence** | ResearchService | EventBus: `RESEARCH_COMPLETED` | Incorporates research findings into plan |

#### 5.3.7 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Requirements validation fails | PERMANENT | Emit `PLANNING_FAILED` with `ValidationFailure` | Human must clarify requirements |
| Architecture conformance fails | PERMANENT | Emit `PLANNING_FAILED` with `ArchitectureViolation` | Plan must be revised; Council may override via ADR |
| Task decomposition impossible | TRANSIENT | Retry with alternative decomposition strategy (max 2) | Escalate to Council if persistent |
| Council consensus unreachable | CRITICAL | Emit `COUNCIL_DISSENT_REGISTERED`; escalate to Human | HumanInteractionService mediates |
| Human approval timeout | TIMEOUT | Emit `HUMAN_TIMEOUT`; mark plan `PENDING_HUMAN` | Human must respond; no auto-retry |
| Capability unavailable (LLM, Research) | TRANSIENT | Retry per RetryManager budget; then `RETRY_BUDGET_EXHAUSTED` | RCA classifies; RecoveryAction may substitute capability or escalate |

**Invariant:** `INV-PL-FH-001` — PlanningService MUST NOT proceed to `PLANNING_COMPLETED` without valid PlanArtifact.
**Invariant:** `INV-PL-FH-002` — All planning failures emit `PLANNING_FAILED` with complete `FailureContext` for RCA.

#### 5.3.8 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-PL-001 | Every `PLANNING_COMPLETED` event carries a valid `PlanArtifact` conforming to `PlanSchema` |
| INV-PL-002 | PlanArtifact `tasks` array forms a valid DAG (no cycles, all dependencies resolvable) |
| INV-PL-003 | PlanArtifact includes architecture conformance verification result (PASS/FAIL with evidence) |
| INV-PL-004 | High-risk plans (per RiskRegister threshold) MUST convene Council before completion |
| INV-PL-005 | Plans affecting security, data, or kernel invariants MUST require Human approval |
| INV-PL-006 | PlanArtifact version MUST increment on every revision; history preserved in StorageManager |
| INV-PL-007 | PlanningService MUST NOT modify PlanArtifact after `PLANNING_COMPLETED` — new version required |

#### 5.3.9 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-PL-001 | Implements `BaseService`; declares `depends_on: ["MemoryService", "ResearchService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-PL-002 | Subscribes to `PLANNING_REQUESTED` in `on_start()` | Runtime: subscription verification |
| CONF-PL-003 | Emits `PLANNING_COMPLETED` with valid PlanArtifact on success | Contract test |
| CONF-PL-004 | Emits `PLANNING_FAILED` with FailureContext on failure | Contract test |
| CONF-PL-005 | Invokes CouncilService for high-risk plans | Integration test (risk threshold) |
| CONF-PL-006 | Invokes HumanInteractionService for security/data/kernel-impacting plans | Integration test |
| CONF-PL-007 | All events carry `correlationId`, `causationId` | Event schema validation |
| CONF-PL-008 | PlanArtifact persisted to StorageManager (artifacts namespace) | Integration test |
| CONF-PL-009 | Zero direct calls to other services (EventBus only) | Static analysis |
| CONF-PL-010 | Health check implements `healthCheck()` per BaseService contract | Unit test |

---

### 5.4 Coding Service

#### 5.4.1 Purpose

CodingService consumes a **PlanArtifact** and generates **executable code artifacts** — source files, configuration, tests, and deployment manifests — conforming to the plan's task specifications, architectural constraints, and quality standards. It owns the code generation governance for the SDLC.

#### 5.4.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| CD-R-001 | **Plan Interpretation** | Parse PlanArtifact; resolve task dependencies; determine execution order |
| CD-R-002 | **Workspace Ownership** | Manage isolated workspace per plan; version control integration; artifact staging |
| CD-R-003 | **Code Generation Governance** | Generate code per task spec; enforce coding standards; validate against architecture |
| CD-R-004 | **Repository Interaction** | Read existing codebase for context; write generated artifacts; create commits/PRs |
| CD-R-005 | **Dependency Resolution** | Resolve internal/external dependencies; update lockfiles; verify compatibility |
| CD-R-006 | **Incremental Generation** | Support partial re-generation on plan changes; preserve hand-written code regions |
| CD-R-007 | **Artifact Validation** | Syntax check, type check, lint, format generated code before emission |
| CD-R-008 | **Traceability** | Link every generated artifact to source PlanArtifact task(s) |

#### 5.4.3 Code Generation Governance

| Governance Aspect | Mechanism | Enforcement |
|-------------------|-----------|-------------|
| **Coding Standards** | Language-specific linters/formatters in workspace | Pre-commit validation; fail generation on violation |
| **Architecture Conformance** | Static analysis against Parts 0–4 patterns | Automated check; emit `ARCHITECTURE_VIOLATION` event |
| **Security Patterns** | Secure coding rules (OWASP, language-specific) | Integrated in generation pipeline; fail on violation |
| **License Compliance** | Dependency license scanning | Block generation on incompatible license |
| **Generated Code Markers** | Mandatory header comments: `// GENERATED BY AI-OS CODING SERVICE` | Verified on every artifact; tampering = audit event |
| **Human Region Preservation** | `// AI-OS: HUMAN-EDITED` regions protected | Merge strategy preserves; conflict = Human escalation |

#### 5.4.4 Workspace Ownership

| Aspect | Specification |
|--------|---------------|
| **Isolation** | Each `planId` gets dedicated workspace (directory or git worktree) |
| **Version Control** | Workspace is a git repository; all changes committed with `planId` correlation |
| **Staging Area** | Generated artifacts staged in `.ai-os/staging/` before commit |
| **Concurrency** | Single CodingService instance per plan; multiple plans → parallel workspaces |
| **Cleanup** | Workspace retained until `DEPLOYMENT_COMPLETED` or `PLANNING_FAILED`; then archival per retention |

#### 5.4.5 Repository Interaction

| Operation | Mechanism | Constraints |
|-----------|-----------|-------------|
| **Read Context** | `git show`, `git diff`, file read | Read-only; no mutations |
| **Write Artifacts** | File write → `git add` → `git commit` | Commits attributed to `ai-os-coding[planId]` |
| **Create PR** | `git push` + platform API (GitHub/GitLab) | Requires `REVIEW_REQUESTED` event downstream |
| **Merge** | Platform merge API (after review approval) | Only after `REVIEW_APPROVED` event |
| **Rollback** | `git revert` or branch reset | Triggered by `DEPLOYMENT_ROLLED_BACK` |

#### 5.4.6 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `CODING_REQUESTED` | Consumed | `CodingRequestPayload{planId, planArtifact}` | `PLANNING_COMPLETED` |
| `CODING_COMPLETED` | Emitted | `CodingResultPayload{planId, artifacts[], commits[]}` | All tasks generated successfully |
| `CODING_FAILED` | Emitted | `FailureContext{planId, taskId?, error}` | Unrecoverable generation error |
| `CODE_GENERATED` | Emitted (per task) | `CodeGeneratedPayload{taskId, files[], commit}` | Individual task completion |
| `ARTIFACT_CREATED` | Emitted | `ArtifactCreatedPayload` | Each generated file committed |
| `ARCHITECTURE_VIOLATION` | Emitted | `ArchitectureViolationPayload` | Governance check failure |
| `HUMAN_ESCALATION_REQUIRED` | Emitted | `HumanEscalationPayload` | Merge conflict in human region |

#### 5.4.7 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **PlanConsumption** | PlanningService | EventBus: `PLANNING_COMPLETED` → `CODING_REQUESTED` | Receives PlanArtifact |
| **ArtifactDelivery** | ReviewService | EventBus: `CODING_COMPLETED` | Delivers generated artifacts |
| **MemoryContext** | MemoryService | EventBus: `CONTEXT_ASSEMBLE` / `MEMORY_RETRIEVE` | Retrieves codebase context |
| **SkillExecution** | SkillService | EventBus: `SKILL_EXECUTE` | Invokes code generation skills |
| **ModelRouting** | ModelRouter (via LLMManager) | Capability Facade: `LLM_INVOKE` | Routes generation prompts |

#### 5.4.8 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Syntax/type error in generated code | PERMANENT | Retry with corrected prompt (max 3 per task) | Escalate to ReviewService for pattern analysis |
| Dependency resolution fails | TRANSIENT | Retry with updated lockfile (max 2) | Human escalation for version conflict |
| Workspace corruption | CRITICAL | Discard workspace; re-initialize from clean state | Full re-generation from PlanArtifact |
| Repository permission denied | PERMANENT | Emit `CODING_FAILED` with `PermissionFailure` | Human must grant access |
| LLM token budget exceeded | TRANSIENT | Chunk tasks; retry with ModelRouter fallback | Escalate to Council for budget override |
| Human region merge conflict | PERMANENT | Emit `HUMAN_ESCALATION_REQUIRED` | HumanInteractionService resolves |

**Invariant:** `INV-CD-FH-001` — CodingService MUST validate every generated artifact before `ARTIFACT_CREATED`.
**Invariant:** `INV-CD-FH-002` — Partial generation failure MUST NOT leave workspace in inconsistent state (atomic per-task).

#### 5.4.9 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-CD-001 | Every `CODING_COMPLETED` event carries complete artifact set for all plan tasks |
| INV-CD-002 | All generated files include `GENERATED BY AI-OS CODING SERVICE` marker with `planId`, `taskId`, `timestamp` |
| INV-CD-003 | No generated artifact overwrites a `HUMAN-EDITED` region without `HUMAN_ESCALATION_REQUIRED` |
| INV-CD-004 | Workspace git history preserves full traceability: `planId` → `taskId` → `commit` → `file` |
| INV-CD-005 | CodingService MUST NOT generate code for tasks not in PlanArtifact |
| INV-CD-006 | All repository mutations occur via git; no raw filesystem writes outside workspace |
| INV-CD-007 | CodingService MUST emit `CODE_GENERATED` per task for fine-grained observability |

#### 5.4.10 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-CD-001 | Implements `BaseService`; declares `depends_on: ["PlanningService", "MemoryService", "ResearchService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-CD-002 | Subscribes to `PLANNING_COMPLETED` (filtered by `planId`) | Runtime: subscription verification |
| CONF-CD-003 | Emits `CODING_COMPLETED` with complete artifact list | Contract test |
| CONF-CD-004 | All generated artifacts pass syntax/type/lint validation | Integration test (multi-language) |
| CONF-CD-005 | Generated code markers present and accurate | Automated scan |
| CONF-CD-006 | Human region preservation verified under conflict | Integration test |
| CONF-CD-007 | Zero direct service calls; EventBus only | Static analysis |
| CONF-CD-008 | Health check reports workspace status, generation queue depth | Unit test |

---

### 5.5 Review Service

#### 5.5.1 Purpose

ReviewService performs **multi-dimensional review** of generated code artifacts — static analysis, architecture conformance, security review, and quality gate enforcement. It is the mandatory quality gate between Coding and Testing phases. No artifact proceeds to Testing without ReviewService approval.

#### 5.5.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| RV-R-001 | **Static Review** | Execute static analyzers (lint, type-check, complexity, duplication, dead code) |
| RV-R-002 | **Architecture Review** | Verify conformance to AI-OS Architecture Specification (Parts 0–N); check ADR compliance |
| RV-R-003 | **Security Review** | Scan for vulnerabilities (SAST, secrets, OWASP, supply chain, crypto misuse) |
| RV-R-004 | **Quality Gates** | Enforce configurable thresholds: coverage, complexity, duplication, debt, standards |
| RV-R-005 | **Approval Flow** | Coordinate Council consensus for architectural decisions; Human approval for security exceptions |
| RV-R-006 | **Review Artifact** | Produce `ReviewReport` with findings, ratings, required fixes, approvals |
| RV-R-007 | **Feedback Loop** | Emit structured findings for CodingService re-generation; track fix verification |

#### 5.5.3 Review Dimensions

| Dimension | Tools/Checks | Severity Levels | Gate Type |
|-----------|--------------|-----------------|-----------|
| **Static Analysis** | Language linters, type checkers, complexity analyzers | ERROR, WARNING, INFO | HARD (ERROR blocks) |
| **Architecture** | Custom rules for Parts 0–4 patterns, ADR validation | VIOLATION, DEVIATION, ALIGNED | HARD (VIOLATION blocks) |
| **Security** | SAST, secret scan, dependency audit, crypto check | CRITICAL, HIGH, MEDIUM, LOW | HARD (CRITICAL/HIGH block) |
| **Quality** | Coverage, duplication, tech debt, maintainability index | THRESHOLD_BREACH, PASS | CONFIGURABLE (HARD/SOFT) |

#### 5.5.4 Approval Flow

```
CODING_COMPLETED
       │
       ▼
┌──────────────────┐
│ Parallel Review  │
│ Execution        │
│ (Static, Arch,   │
│  Security, Qual) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     Any HARD failure? ──YES──▶ REVIEW_REJECTED (with findings)
│ Aggregate        │                                    │
│ Findings         │                                    ▼
└────────┬─────────┘                            [CodingService] ◀─── Fix Loop
         │
         ▼
   Council Required? ──YES──▶ [CouncilService] ──▶ Consensus/Dissent
         │
         ▼
   Human Required? ──YES──▶ [HumanInteractionService] ──▶ Approval/Rejection
         │
         ▼
 REVIEW_APPROVED  OR  REVIEW_REJECTED
```

#### 5.5.5 Quality Gates Configuration

| Gate | Metric | Threshold | Configurable | Default Action |
|------|--------|-----------|--------------|----------------|
| **Coverage** | Line/branch coverage | ≥ 80% | Yes | HARD |
| **Complexity** | Cyclomatic complexity | ≤ 10 per function | Yes | HARD |
| **Duplication** | Code duplication | ≤ 3% | Yes | SOFT |
| **Tech Debt** | SQALE rating | ≤ A | Yes | SOFT |
| **Standards** | Lint errors | 0 | No | HARD |
| **Security** | CRITICAL/HIGH findings | 0 | No | HARD |
| **Architecture** | VIOLATION findings | 0 | No | HARD |

#### 5.5.6 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `REVIEW_REQUESTED` | Consumed | `ReviewRequestPayload{planId, artifacts[]}` | `CODING_COMPLETED` |
| `REVIEW_STARTED` | Emitted | `ReviewStartedPayload{reviewId, planId}` | Review initiation |
| `REVIEW_APPROVED` | Emitted | `ReviewReport{reviewId, planId, status: APPROVED, findings[]}` | All gates pass |
| `REVIEW_REJECTED` | Emitted | `ReviewReport{reviewId, planId, status: REJECTED, findings[]}` | Any HARD gate fails |
| `REVIEW_FAILED` | Emitted | `FailureContext{reviewId, error}` | Review execution error |
| `COUNCIL_CONVENED` | Emitted | `CouncilRequestPayload` | Architectural deviation requires consensus |
| `HUMAN_ESCALATION_REQUIRED` | Emitted | `HumanEscalationPayload` | Security exception requires human |
| `FINDING_EMITTED` | Emitted (per finding) | `FindingPayload{reviewId, finding}` | Structured finding for fix loop |

#### 5.5.7 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **ArtifactConsumption** | CodingService | EventBus: `CODING_COMPLETED` → `REVIEW_REQUESTED` | Receives generated artifacts |
| **ReportDelivery** | TestingService | EventBus: `REVIEW_APPROVED` | Delivers ReviewReport to next phase |
| **FixFeedback** | CodingService | EventBus: `FINDING_EMITTED` + `REVIEW_REJECTED` | Structured findings for re-generation |
| **CouncilConsensus** | CouncilService | EventBus: `COUNCIL_CONSENSUS_REACHED` / `COUNCIL_DISSENT_REGISTERED` | Architectural decision |
| **HumanApproval** | HumanInteractionService | EventBus: `HUMAN_RESPONSE_RECEIVED` | Security exception decision |
| **MemoryContext** | MemoryService | EventBus: `MEMORY_RETRIEVE` | Retrieves prior review patterns |

#### 5.5.8 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Static analysis tool crash | TRANSIENT | Retry with isolated file subset (max 2) | Mark file as `REVIEW_SKIPPED`; escalate |
| Security scanner timeout | TIMEOUT | Chunk artifacts; parallel scan; aggregate | Partial results + `REVIEW_DEGRADED` |
| Council deadlock | CRITICAL | Emit `COUNCIL_DISSENT_REGISTERED`; escalate Human | HumanInteractionService final decision |
| Human approval timeout | TIMEOUT | Emit `HUMAN_TIMEOUT`; mark `PENDING_HUMAN` | No auto-retry; human must respond |
| ReviewReport persistence fails | TRANSIENT | Retry StorageManager write (max 3) | Escalate to RCA on exhaustion |

**Invariant:** `INV-RV-FH-001` — ReviewService MUST emit exactly one of `REVIEW_APPROVED`, `REVIEW_REJECTED`, or `REVIEW_FAILED` per review.
**Invariant:** `INV-RV-FH-002` — `REVIEW_REJECTED` MUST include complete `ReviewReport` with all findings.

#### 5.5.9 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-RV-001 | No artifact proceeds to Testing without `REVIEW_APPROVED` (enforced by WorkflowManager) |
| INV-RV-002 | ReviewReport is immutable after emission; new review = new `reviewId` |
| INV-RV-003 | All HARD gate failures are blocking; no override without Council + Human consensus |
| INV-RV-004 | Security CRITICAL/HIGH findings MUST trigger HumanInteractionService escalation |
| INV-RV-005 | Architecture VIOLATION findings MUST trigger CouncilService consensus |
| INV-RV-006 | ReviewService MUST maintain finding traceability: `reviewId` → `findingId` → `fixCommit` |
| INV-RV-007 | Review execution MUST be deterministic: same artifacts → same Report (modulo tool versions) |

#### 5.5.10 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-RV-001 | Implements `BaseService`; declares `depends_on: ["CodingService", "MemoryService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-RV-002 | Subscribes to `CODING_COMPLETED` | Runtime: subscription verification |
| CONF-RV-003 | Emits `REVIEW_APPROVED`/`REJECTED`/`FAILED` with valid ReviewReport | Contract test |
| CONF-RV-004 | All four review dimensions execute in parallel | Integration test |
| CONF-RV-005 | Quality gates configurable via ConfigurationManager | Unit test |
| CONF-RV-006 | Council/Human escalation for mandated finding types | Integration test |
| CONF-RV-007 | Finding traceability maintained through fix loop | Integration test |
| CONF-RV-008 | Zero direct service calls; EventBus only | Static analysis |

---

### 5.6 Testing Service

#### 5.6.1 Purpose

TestingService orchestrates **comprehensive test execution** across all test tiers — unit, integration, system, regression, performance, and security. It aggregates results, enforces coverage governance, and emits the `TESTING_COMPLETED` gate event required for Deployment.

#### 5.6.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| TS-R-001 | **Test Orchestration** | Discover, schedule, and execute tests across all tiers per ReviewReport and PlanArtifact |
| TS-R-002 | **Unit Testing** | Execute isolated unit tests; enforce per-module coverage thresholds |
| TS-R-003 | **Integration Testing** | Execute service-to-service, service-to-kernel, service-to-capability integration tests |
| TS-R-004 | **System Testing** | Execute end-to-end workflows against deployed/staged environment |
| TS-R-005 | **Regression Testing** | Execute historical test suite; detect behavioral regressions |
| TS-R-006 | **Performance Testing** | Execute load, stress, soak, spike tests; enforce SLO thresholds |
| TS-R-007 | **Security Testing** | Execute DAST, penetration tests, dependency scans, compliance checks |
| TS-R-008 | **Result Aggregation** | Collect, normalize, and correlate results across all tiers |
| TS-R-009 | **Coverage Governance** | Enforce global and per-component coverage policies; track trends |
| TS-R-010 | **Test Artifact Management** | Generate test reports, coverage reports, performance baselines, security findings |

#### 5.6.3 Test Tiers and Execution Model

| Tier | Scope | Trigger | Parallelism | Timeout | Environment |
|------|-------|---------|-------------|---------|-------------|
| **Unit** | Single module/class | `REVIEW_APPROVED` | High (per module) | 5 min/module | Isolated (no external deps) |
| **Integration** | Multi-service, kernel-capability | `REVIEW_APPROVED` | Medium (per scenario) | 15 min/scenario | Test kernel + test doubles |
| **System** | Full workflow E2E | `REVIEW_APPROVED` | Low (sequential) | 60 min/workflow | Staging environment |
| **Regression** | Full historical suite | Scheduled + `REVIEW_APPROVED` | High (sharded) | 120 min | Staging environment |
| **Performance** | Load/stress/soak | Scheduled + on-demand | Controlled ramp | Configurable | Dedicated perf env |
| **Security** | DAST, pen-test, compliance | `REVIEW_APPROVED` + scheduled | Low | 60 min | Isolated security env |

**Execution Flow:**
```
REVIEW_APPROVED
       │
       ▼
┌──────────────────┐
│ Test Discovery   │
│ & Planning       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────┐     ┌─────────────┐
│ Unit Tests       │     │ Integration │     │ Parallel    │
│ (parallel)       │────▶│ Tests       │────▶│ Execution   │
└──────────────────┘     └─────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ System      │
                                              │ Tests       │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ Regression  │
                                              │ (if due)    │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ Perf/Sec    │
                                              │ (if configured)  
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                        TESTING_COMPLETED / TESTING_FAILED
```

#### 5.6.4 Result Aggregation

| Aggregation Level | Metrics | Output |
|-------------------|---------|--------|
| **Per Test** | Pass/fail, duration, assertions, coverage delta | `TestResultEvent` |
| **Per Tier** | Pass rate, duration, coverage, flakiness | `TierSummaryEvent` |
| **Per Plan** | Overall pass/fail, coverage, performance baselines, security posture | `TestReport` (artifact) |
| **Trend** | Coverage trend, flakency trend, performance trend | `TestTrendEvent` (LearningService) |

#### 5.6.5 Coverage Governance

| Policy | Scope | Enforcement | Exception |
|--------|-------|-------------|-----------|
| **Global Minimum** | All code | ≥ 80% line, ≥ 70% branch | Council + Human |
| **Per Component** | Each service/manager | ≥ 90% line, ≥ 80% branch | Council |
| **New Code** | Code added in plan | 100% line, 90% branch | Never (HARD) |
| **Critical Paths** | Security, data, kernel | 100% line, 100% branch | Never (HARD) |
| **Generated Code** | CodingService output | 100% line (tests also generated) | ReviewService validates |

#### 5.6.6 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `TESTING_REQUESTED` | Consumed | `TestingRequestPayload{planId, reviewReport, testPlan}` | `REVIEW_APPROVED` |
| `TESTING_STARTED` | Emitted | `TestingStartedPayload{testingId, planId}` | Orchestration start |
| `TEST_RESULT` | Emitted (per test) | `TestResultPayload{testingId, testId, result, duration, coverage}` | Test completion |
| `TIER_COMPLETED` | Emitted | `TierSummaryPayload{testingId, tier, summary}` | All tests in tier done |
| `TESTING_COMPLETED` | Emitted | `TestReport{testingId, planId, overallResult, artifacts[]}` | All tiers pass |
| `TESTING_FAILED` | Emitted | `FailureContext{testingId, error}` | Orchestration/any tier hard fail |
| `COVERAGE_VIOLATION` | Emitted | `CoverageViolationPayload{component, actual, required}` | Gate threshold breach |
| `PERFORMANCE_BASELINE` | Emitted | `PerformanceBaselinePayload{metrics, comparison}` | Perf test completion |
| `SECURITY_FINDING` | Emitted | `SecurityFindingPayload{finding, severity}` | Security test finding |

#### 5.6.7 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **TestTrigger** | ReviewService | EventBus: `REVIEW_APPROVED` → `TESTING_REQUESTED` | Receives approved artifacts |
| **ReportDelivery** | DeploymentService | EventBus: `TESTING_COMPLETED` | Delivers TestReport |
| **EnvironmentCoordination** | DeploymentService | EventBus: `ENVIRONMENT_PREPARE` / `ENVIRONMENT_READY` | Staging env for system tests |
| **MemoryContext** | MemoryService | EventBus: `MEMORY_RETRIEVE` | Historical flakiness, baselines |
| **LearningFeedback** | LearningService | EventBus: `LEARNING_REQUESTED` + `TestTrendEvent` | Feeds pattern extraction |

#### 5.6.8 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Test infrastructure failure | TRANSIENT | Retry test (max 2); mark `INFRASTRUCTURE_FLAKE` | RCA classifies; RecoveryAction may reschedule |
| Flaky test detected | TRANSIENT | Quarantine; run 3×; if inconsistent → `FLAKY` | LearningService extracts pattern; auto-fix or suppress |
| Coverage gate failure | PERMANENT | Emit `COVERAGE_VIOLATION`; `TESTING_FAILED` | CodingService re-generation with test focus |
| Performance regression | PERMANENT | Emit `PERFORMANCE_REGRESSION`; `TESTING_FAILED` | Council reviews baseline; Human may approve |
| Security finding (CRITICAL) | CRITICAL | Emit `SECURITY_FINDING`; `TESTING_FAILED` | Immediate Human escalation; deployment blocked |
| Test timeout | TIMEOUT | Kill test; emit `TEST_TIMEOUT`; count as failure | Retry with extended timeout (max 1) |

**Invariant:** `INV-TS-FH-001` — TestingService MUST execute all mandated tiers before `TESTING_COMPLETED`.
**Invariant:** `INV-TS-FH-002` — Any CRITICAL security finding → immediate `TESTING_FAILED`; no partial pass.

#### 5.6.9 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-TS-001 | `TESTING_COMPLETED` emitted IFF all mandated tiers pass their HARD gates |
| INV-TS-002 | TestReport includes results for EVERY test executed; no silent drops |
| INV-TS-003 | Coverage measured against PlanArtifact `tasks` — every task has test coverage |
| INV-TS-004 | Performance baselines stored in MemoryService for regression comparison |
| INV-TS-005 | Flaky tests tracked across runs; > 3 flakes in 10 runs → auto-quarantine |
| INV-TS-006 | Test artifacts (reports, coverage, baselines) persisted to StorageManager |
| INV-TS-007 | Test execution order deterministic: same seed → same order |
| INV-TS-008 | TestingService MUST NOT deploy; only test against DeploymentService-provided environments |

#### 5.6.10 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-TS-001 | Implements `BaseService`; declares `depends_on: ["ReviewService", "DeploymentService", "MemoryService", "LearningService", "HumanInteractionService"]` | Static: registration validation |
| CONF-TS-002 | Subscribes to `REVIEW_APPROVED` | Runtime: subscription verification |
| CONF-TS-003 | Executes all mandated tiers in specified order | Integration test |
| CONF-TS-004 | Emits `TESTING_COMPLETED` with valid TestReport | Contract test |
| CONF-TS-005 | Coverage gates enforced per policy | Integration test |
| CONF-TS-006 | Flaky test detection and quarantine operational | Chaos test |
| CONF-TS-007 | Performance baselines compared and stored | Integration test |
| CONF-TS-008 | Zero direct service calls; EventBus only | Static analysis |

---

### 5.7 Deployment Service

#### 5.7.1 Purpose

DeploymentService manages the **complete deployment lifecycle** — promotion through environments, release governance, rollback orchestration, and environment coordination. It is the gate between Testing and Operations phases.

#### 5.7.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| DP-R-001 | **Deployment Lifecycle** | Execute promotion: dev → staging → production (configurable pipeline) |
| DP-R-002 | **Promotion Governance** | Enforce promotion criteria: test pass, approvals, canary metrics, manual gates |
| DP-R-003 | **Rollback Orchestration** | Automated and manual rollback with compensation; state restoration |
| DP-R-004 | **Release Governance** | Versioning, changelog, sign-off, artifact provenance, SBOM generation |
| DP-R-005 | **Environment Coordination** | Provision, configure, validate, and tear down deployment environments |
| DP-R-006 | **Deployment Artifacts** | Manage release bundles, containers, configs, secrets, migrations |
| DP-R-007 | **Observability Integration** | Deploy monitoring, alerting, dashboards alongside workload |
| DP-R-008 | **Traffic Management** | Canary, blue-green, feature flags, gradual rollout |

#### 5.7.3 Deployment Lifecycle

```
TESTING_COMPLETED
       │
       ▼
┌──────────────────┐
│ Release          │
│ Preparation      │
│ (version, SBOM,  │
│  changelog)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     Promotion Gate? ──YES──▶ [CouncilService/HumanInteractionService]
│ Dev Deployment   │                                    │
│ (auto)           │                                    ▼
└────────┬─────────┘                            Approved?
         │                                        │
         ▼                                        ▼
    Dev Health Check                         NO → Rollback
         │
         ▼
┌──────────────────┐     Promotion Gate? ──YES──▶ [CouncilService/HumanInteractionService]
│ Staging Deploy   │                                    │
│ (canary/blue-grn)│                                    ▼
└────────┬─────────┘                            Approved?
         │                                        │
         ▼                                        ▼
    Canary Metrics                             NO → Rollback
         │
         ▼
┌──────────────────┐     Promotion Gate? ──YES──▶ [HumanInteractionService] (MANDATORY)
│ Production Deploy│                                    │
│ (gradual rollout)│                                    ▼
└────────┬─────────┘                            Approved?
         │                                        │
         ▼                                        ▼
    Production Health                        NO → Rollback
         │
         ▼
 DEPLOYMENT_COMPLETED
```

#### 5.7.4 Promotion Gates

| Gate | Environment | Criteria | Authority | Mandatory |
|------|-------------|----------|-----------|-----------|
| **Dev → Staging** | Dev → Staging | Unit/Integration pass; no CRITICAL security; Dev health green | CouncilService (architectural) | YES |
| **Staging → Prod** | Staging → Prod | System tests pass; canary metrics within SLO; perf baseline met; no HIGH security | HumanInteractionService (operator) | YES |
| **Prod Rollout** | Prod (progressive) | Error rate < threshold; latency < SLO; business metrics stable | HumanInteractionService (on-call) | YES (per increment) |

#### 5.7.5 Rollback Orchestration

| Trigger | Type | Procedure |
|---------|------|-----------|
| **Automated** | Canary metrics breach | Immediate traffic shift; previous version restored; `DEPLOYMENT_ROLLED_BACK` |
| **Manual** | Human decision | `HUMAN_ROLLBACK_REQUESTED` → graceful drain → previous version → `DEPLOYMENT_ROLLED_BACK` |
| **Compensating** | Migration failure | Execute down-migration; restore data from checkpoint; `DEPLOYMENT_ROLLED_BACK` |
| **Cascading** | Dependency failure | Roll back dependent services in reverse dependency order |

**Rollback Invariants:**
- **INV-DP-RB-001** — Rollback MUST complete within `rollbackSLA` (configurable, default: 10 min)
- **INV-DP-RB-002** — Rollback MUST restore exact prior version (immutable artifacts)
- **INV-DP-RB-003** — Rollback emits `DEPLOYMENT_ROLLED_BACK` with full reason and compensation log

#### 5.7.6 Release Governance

| Artifact | Generation | Storage | Retention |
|----------|------------|---------|-----------|
| **Release Bundle** | `TESTING_COMPLETED` trigger | StorageManager (artifacts) | 1 year |
| **SBOM** | CycloneDX/SPDX format | StorageManager (artifacts) | 7 years (compliance) |
| **Changelog** | Auto from commits + manual | StorageManager (artifacts) | Permanent |
| **Provenance** | SLSA build provenance | StorageManager (audit) | 7 years |
| **Signatures** | Cosign/Notary on bundles | StorageManager (audit) | Permanent |

#### 5.7.7 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `DEPLOYMENT_REQUESTED` | Consumed | `DeploymentRequestPayload{planId, testReport, targetEnv}` | `TESTING_COMPLETED` |
| `DEPLOYMENT_STARTED` | Emitted | `DeploymentStartedPayload{deploymentId, planId, environment}` | Deployment initiation |
| `ENVIRONMENT_READY` | Emitted | `EnvironmentReadyPayload{environment, endpoint}` | Environment provisioned |
| `CANARY_METRICS` | Emitted | `CanaryMetricsPayload{deploymentId, metrics, verdict}` | Canary evaluation |
| `PROMOTION_GATE` | Emitted | `PromotionGatePayload{deploymentId, fromEnv, toEnv, criteria}` | Gate evaluation |
| `DEPLOYMENT_COMPLETED` | Emitted | `DeploymentReport{deploymentId, planId, version, environments[]}` | All gates pass |
| `DEPLOYMENT_FAILED` | Emitted | `FailureContext{deploymentId, error}` | Unrecoverable deployment error |
| `DEPLOYMENT_ROLLED_BACK` | Emitted | `RollbackReport{deploymentId, reason, compensationLog}` | Rollback completion |
| `HUMAN_ESCALATION_REQUIRED` | Emitted | `HumanEscalationPayload` | Mandatory prod gate |

#### 5.7.8 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **DeploymentTrigger** | TestingService | EventBus: `TESTING_COMPLETED` → `DEPLOYMENT_REQUESTED` | Receives test report |
| **EnvironmentRequest** | OperationsService | EventBus: `ENVIRONMENT_PROVISION` / `ENVIRONMENT_TEARDOWN` | Environment lifecycle |
| **TrafficManagement** | OperationsService | EventBus: `TRAFFIC_SHIFT` / `TRAFFIC_SPLIT` | Canary/blue-green control |
| **ObservabilityDeploy** | OperationsService | EventBus: `OBSERVABILITY_DEPLOY` | Monitoring stack deployment |
| **RollbackCoordination** | OperationsService | EventBus: `ROLLBACK_EXECUTE` | Operations executes rollback |
| **MemoryContext** | MemoryService | EventBus: `MEMORY_RETRIEVE` | Prior deployment patterns |
| **CouncilConsensus** | CouncilService | EventBus: `COUNCIL_CONSENSUS_REACHED` | Architectural promotion gates |
| **HumanApproval** | HumanInteractionService | EventBus: `HUMAN_RESPONSE_RECEIVED` | Mandatory prod gates |

#### 5.7.9 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Environment provisioning fails | TRANSIENT | Retry with backoff (max 3); try alternate zone | Escalate to OperationsService manual provision |
| Canary metrics breach | PERMANENT | Auto-rollback; `DEPLOYMENT_ROLLED_BACK` | RCA on metrics; fix → re-deploy |
| Production gate timeout | TIMEOUT | Pause rollout; `DEPLOYMENT_PAUSED` | Human must resume or rollback |
| Migration failure (DB/schema) | CRITICAL | Compensating rollback; data restore from checkpoint | Full rollback + Human postmortem |
| Secret injection fails | TRANSIENT | Retry (max 3); mark deployment `DEGRADED` | OperationsService manual secret sync |
| Resource quota exceeded | TRANSIENT | Scale request via ResourceManager; retry | OperationsService capacity planning |

**Invariant:** `INV-DP-FH-001` — Production deployment REQUIRES `HUMAN_RESPONSE_RECEIVED` with approval.
**Invariant:** `INV-DP-FH-002` — Any rollback emits `DEPLOYMENT_ROLLED_BACK` with complete compensation log.

#### 5.7.10 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-DP-001 | No deployment proceeds to next environment without passing Promotion Gate |
| INV-DP-002 | Production deployment MANDATES HumanInteractionService approval (no auto-promote) |
| INV-DP-003 | All deployment artifacts are immutable and versioned; stored in StorageManager |
| INV-DP-004 | Rollback restores EXACT prior version (artifact hash verified) |
| INV-DP-005 | Canary evaluation uses predefined SLO metrics from ConfigurationAuthority |
| INV-DP-006 | DeploymentService coordinates but does not execute infrastructure ops (delegates to OperationsService) |
| INV-DP-007 | SBOM and provenance generated for EVERY production release |

#### 5.7.11 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-DP-001 | Implements `BaseService`; declares `depends_on: ["TestingService", "OperationsService", "MemoryService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-DP-002 | Subscribes to `TESTING_COMPLETED` | Runtime: subscription verification |
| CONF-DP-003 | Enforces all promotion gates per configuration | Integration test |
| CONF-DP-004 | Rollback completes within SLA and emits `DEPLOYMENT_ROLLED_BACK` | Chaos test |
| CONF-DP-005 | Production gate requires Human approval | Integration test |
| CONF-DP-006 | SBOM/provenance generated for production | Contract test |
| CONF-DP-007 | Zero direct service calls; EventBus only | Static analysis |

---

### 5.8 Documentation Service

#### 5.8.1 Purpose

DocumentationService generates, versions, and synchronizes **all documentation artifacts** — API references, architecture decision records, runbooks, user guides, and operational procedures — ensuring documentation remains consistent with deployed reality.

#### 5.8.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| DC-R-001 | **Documentation Generation** | Generate docs from code (API), architecture (ADRs), deployment (runbooks), tests (coverage reports) |
| DC-R-002 | **Versioning** | Semantic versioning of documentation; alignment with code versions; changelog integration |
| DC-R-003 | **Knowledge Synchronization** | Sync documentation across repositories, wikis, portals; detect drift |
| DC-R-004 | **Artifact Generation** | Produce PDF, HTML, Markdown, OpenAPI, AsyncAPI artifacts per audience |
| DC-R-005 | **Architecture Synchronization** | Keep ARCHITECTURE_SPEC_PART*.md synchronized with implementation via conformance evidence |
| DC-R-006 | **Review Integration** | Documentation changes follow ReviewService gates (accuracy, completeness) |

#### 5.8.3 Documentation Types

| Type | Source | Generation Trigger | Audience |
|------|--------|-------------------|----------|
| **API Reference** | Code annotations, OpenAPI specs | `CODING_COMPLETED` | Developers |
| **Architecture Decisions** | ADRs in `docs/DECISIONS.md` | ADR creation/update | Architects |
| **Runbooks** | DeploymentService templates + ops patterns | `DEPLOYMENT_COMPLETED` | Operators |
| **User Guides** | Feature specs + test scenarios | `TESTING_COMPLETED` | End users |
| **Operations Manual** | OperationsService patterns + incidents | `OPERATIONS_COMPLETED` | SRE/On-call |
| **Conformance Reports** | Automated conformance tooling output | Scheduled + on-demand | Auditors |

#### 5.8.4 Versioning and Synchronization

| Mechanism | Specification |
|-----------|---------------|
| **Doc Version** | Semantic version tied to `planId`/`deploymentId`; `v<major>.<minor>.<patch>` |
| **Drift Detection** | Periodic diff: generated docs vs. published docs; emit `DOCUMENTATION_DRIFT` |
| **Sync Targets** | GitHub Pages, Confluence, Notion, internal portal (configurable) |
| **Sync Strategy** | Push on `DOCUMENTATION_COMPLETED`; pull verification every 24h |

#### 5.8.5 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `DOCUMENTATION_REQUESTED` | Consumed | `DocumentationRequestPayload{planId, types[], trigger}` | Phase completion events |
| `DOCUMENTATION_STARTED` | Emitted | `DocumentationStartedPayload{docId, planId, types[]}` | Generation start |
| `DOCUMENTATION_COMPLETED` | Emitted | `DocumentationReport{docId, planId, artifacts[], versions[]}` | All types generated |
| `DOCUMENTATION_FAILED` | Emitted | `FailureContext{docId, error}` | Generation failure |
| `DOCUMENTATION_DRIFT` | Emitted | `DriftReport{target, expected, actual, severity}` | Periodic sync check |
| `ARCHITECTURE_SYNC` | Emitted | `ArchitectureSyncPayload{specParts[], evidence[]}` | Conformance verification |

#### 5.8.6 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **TriggerConsumption** | All Phase Services | EventBus: `*_COMPLETED` → `DOCUMENTATION_REQUESTED` | Receives phase completion |
| **ArtifactDelivery** | MemoryService | EventBus: `ARTIFACT_CREATED` (docs) | Stores generated docs |
| **ArchitectureEvidence** | Conformance Tooling | EventBus: `CONFORMANCE_REPORT` | Syncs spec with reality |
| **ReviewGate** | ReviewService | EventBus: `REVIEW_REQUESTED` (for doc changes) | Docs follow review gates |

#### 5.8.7 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Generation tool failure | TRANSIENT | Retry with alternate tool (max 2) | Mark doc type `DEFERRED`; manual fallback |
| Sync target unavailable | TRANSIENT | Queue; retry with backoff (max 24h) | Alert via HumanInteractionService |
| Drift detected (HIGH) | PERMANENT | Emit `DOCUMENTATION_DRIFT`; block new deployments until resolved | Human must reconcile |
| Version conflict | PERMANENT | Emit `DOCUMENTATION_FAILED` with `VersionConflict` | Manual version resolution |

**Invariant:** `INV-DC-FH-001` — Architecture documentation (Parts 0–N) MUST be synchronized before `KERNEL_READY` in production.

#### 5.8.8 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-DC-001 | Every `DEPLOYMENT_COMPLETED` triggers runbook generation/update |
| INV-DC-002 | Every ADR change triggers architecture documentation regeneration |
| INV-DC-003 | API reference coverage ≥ 95% of public interfaces (enforced by ReviewService) |
| INV-DC-004 | Documentation version MUST match deployment version (semantic alignment) |
| INV-DC-005 | Drift detection runs at least daily in production |
| INV-DC-006 | DocumentationService MUST NOT modify source code; only reads for generation |

#### 5.8.9 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-DC-001 | Implements `BaseService`; declares `depends_on: ["PlanningService", "CodingService", "ReviewService", "TestingService", "DeploymentService", "OperationsService", "MemoryService"]` | Static: registration validation |
| CONF-DC-002 | Subscribes to all `*_COMPLETED` events | Runtime: subscription verification |
| CONF-DC-003 | Generates all mandated documentation types | Integration test |
| CONF-DC-004 | Drift detection operational and emits events | Contract test |
| CONF-DC-005 | Architecture sync evidence traceable | Audit test |

---

### 5.9 Research Service

#### 5.9.1 Purpose

ResearchService executes **structured research workflows** — evidence collection, knowledge validation, source governance, and research artifact production — to support evidence-based engineering decisions across all SDLC phases.

#### 5.9.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| RS-R-001 | **Research Workflows** | Execute multi-step research: question → sources → evidence → synthesis → validation |
| RS-R-002 | **Evidence Collection** | Retrieve, evaluate, and cite sources (web, docs, code, papers, standards) |
| RS-R-003 | **Knowledge Validation** | Cross-reference claims; detect contradictions; assess source credibility |
| RS-R-004 | **Source Governance** | Maintain source registry; track freshness; enforce citation standards |
| RS-R-005 | **Research Artifacts** | Produce `ResearchReport` with findings, confidence, citations, recommendations |
| RS-R-006 | **Integration** | Feed research into Planning, Coding, Review, Testing for evidence-based decisions |

#### 5.9.3 Research Workflow

```
RESEARCH_REQUESTED
       │
       ▼
┌──────────────────┐
│ Question         │
│ Decomposition    │
│ (sub-questions)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────┐     ┌─────────────┐
│ Source           │────▶│ Evidence    │────▶│ Synthesis   │
│ Discovery        │     │ Collection  │     │ & Validation│
└──────────────────┘     └─────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ Research    │
                                              │ Report Gen  │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                        RESEARCH_COMPLETED / RESEARCH_FAILED
```

#### 5.9.4 Source Governance

| Aspect | Policy |
|--------|--------|
| **Source Registry** | Curated list of trusted sources (official docs, standards, peer-reviewed) |
| **Freshness** | Max age per source type (docs: 30d, standards: 1y, papers: 5y) |
| **Credibility Scoring** | Domain authority, recency, peer review, official status |
| **Citation Format** | Standardized: `[SourceID] Title, URL, AccessedDate, CredibilityScore` |
| **Conflict Resolution** | Higher credibility wins; contradictions flagged for Human review |

#### 5.9.5 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `RESEARCH_REQUESTED` | Consumed | `ResearchRequestPayload{question, context, scope}` | Any phase needs evidence |
| `RESEARCH_STARTED` | Emitted | `ResearchStartedPayload{researchId, question}` | Workflow initiation |
| `EVIDENCE_COLLECTED` | Emitted (per source) | `EvidencePayload{researchId, sourceId, evidence, credibility}` | Source processed |
| `RESEARCH_COMPLETED` | Emitted | `ResearchReport{researchId, findings[], confidence, citations[]}` | Synthesis complete |
| `RESEARCH_FAILED` | Emitted | `FailureContext{researchId, error}` | Workflow failure |
| `KNOWLEDGE_VALIDATED` | Emitted | `ValidationPayload{claim, verdict, evidence[]}` | Cross-reference result |

#### 5.9.6 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **ResearchTrigger** | Planning, Coding, Review, Testing | EventBus: `*_REQUESTED` → `RESEARCH_REQUESTED` | On-demand research |
| **EvidenceDelivery** | Requesting Service | EventBus: `RESEARCH_COMPLETED` | Delivers ResearchReport |
| **MemoryContext** | MemoryService | EventBus: `MEMORY_STORE` / `MEMORY_RETRIEVE` | Caches research results |
| **WebSearch** | MCPService | EventBus: `MCP_TOOL_CALL` (web search) | External source retrieval |
| **CouncilValidation** | CouncilService | EventBus: `COUNCIL_CONVENED` | For high-stakes findings |

#### 5.9.7 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Source unavailable | TRANSIENT | Try alternate sources; mark `SOURCE_UNAVAILABLE` | Cached evidence used; confidence reduced |
| Contradictory evidence | PERMANENT | Flag in report; emit `KNOWLEDGE_VALIDATED` with `CONTRADICTION` | HumanInteractionService resolves |
| Synthesis timeout | TIMEOUT | Emit partial `ResearchReport` with `INCOMPLETE` flag | Resume on re-request |
| Credibility assessment fails | TRANSIENT | Default to conservative (low credibility) | Manual review for critical findings |

**Invariant:** `INV-RS-FH-001` — ResearchService MUST cite all claims; uncited claims = `RESEARCH_FAILED`.

#### 5.9.8 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-RS-001 | Every `RESEARCH_COMPLETED` report includes complete citation trail |
| INV-RS-002 | Source credibility scores are transparent and auditable |
| INV-RS-003 | Contradictory evidence is never silently resolved; always flagged |
| INV-RS-004 | Research reports are immutable; new research = new `researchId` |
| INV-RS-005 | ResearchService caches results in MemoryService for reuse |

#### 5.9.9 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-RS-001 | Implements `BaseService`; declares `depends_on: ["MemoryService", "MCPService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-RS-002 | Subscribes to `RESEARCH_REQUESTED` | Runtime: subscription verification |
| CONF-RS-003 | Emits cited ResearchReport on completion | Contract test |
| CONF-RS-004 | Source governance policies enforced | Unit test |
| CONF-RS-005 | Contradiction detection operational | Integration test |

---

### 5.10 Learning Service

#### 5.10.1 Purpose

LearningService extracts **patterns from execution history**, accumulates experience, and refines the knowledge base to improve future SDLC executions. It closes the learning loop: every phase emits learnings; LearningService synthesizes them into actionable improvements.

#### 5.10.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| LS-R-001 | **Pattern Extraction** | Mine execution events for recurring patterns (success, failure, performance, architectural) |
| LS-R-002 | **Experience Accumulation** | Build compressed representations of workflows, decisions, outcomes |
| LS-R-003 | **Knowledge Refinement** | Update MemoryService with validated patterns; deprecate stale patterns |
| LS-R-004 | **Learning Governance** | Control learning rates; prevent overfitting; validate pattern utility |
| LS-R-005 | **Recommendation Emission** | Emit `LEARNING_RECOMMENDATION` events for proactive phase optimization |

#### 5.10.3 Learning Pipeline

```
LEARNING_REQUESTED (scheduled or event-triggered)
       │
       ▼
┌──────────────────┐
│ Event Log        │
│ Ingestion        │
│ (correlationId   │
│  grouped)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────┐     ┌─────────────┐
│ Pattern          │────▶│ Validation  │────▶│ Knowledge   │
│ Mining           │     │ (statistical│     │ Update      │
│ (ML/heuristic)   │     │  significance)│   │ (MemorySvc) │
└──────────────────┘     └─────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
                                              ┌─────────────┐
                                              │ Recommendation│
                                              │ Emission     │
                                              └──────┬──────┘
                                                     │
                                                     ▼
                                        LEARNING_COMPLETED / LEARNING_FAILED
```

#### 5.10.4 Pattern Categories

| Category | Source Events | Output | Application |
|----------|---------------|--------|-------------|
| **Success Patterns** | `*_COMPLETED` sequences | Reusable workflow templates | PlanningService task templates |
| **Failure Patterns** | `*_FAILED`, `RETRY_*`, `ROOT_CAUSE_*` | Failure signatures + mitigations | RCA acceleration; CodingService avoidance |
| **Performance Patterns** | `PERFORMANCE_*`, `METRIC_*` | Bottleneck signatures + optimizations | TestingService perf focus; DeploymentService sizing |
| **Architectural Patterns** | `ARCHITECTURE_VIOLATION`, `REVIEW_*` | Conformance patterns + fixes | ReviewService rule refinement |
| **Human Decision Patterns** | `HUMAN_RESPONSE_*`, `COUNCIL_*` | Decision precedents | CouncilService precedent retrieval |

#### 5.10.5 Learning Governance

| Control | Mechanism |
|---------|-----------|
| **Learning Rate** | Configurable: conservative (validate >3 occurrences) vs. aggressive (single occurrence) |
| **Pattern TTL** | Patterns expire after `patternTTL` (default: 90 days) without reinforcement |
| **Utility Validation** | A/B test: pattern application vs. baseline; require ≥ 5% improvement |
| **Overfitting Prevention** | Minimum support threshold; cross-validation on historical splits |
| **Human Oversight** | High-impact patterns (security, architecture) require HumanInteractionService approval |

#### 5.10.6 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `LEARNING_REQUESTED` | Consumed | `LearningRequestPayload{scope, trigger}` | Scheduled or post-phase |
| `LEARNING_STARTED` | Emitted | `LearningStartedPayload{learningId, scope}` | Pipeline start |
| `PATTERN_EXTRACTED` | Emitted (per pattern) | `PatternPayload{learningId, pattern, confidence, evidence[]}` | Mining result |
| `LEARNING_RECOMMENDATION` | Emitted | `RecommendationPayload{targetService, action, patternId, confidence}` | Validated pattern |
| `LEARNING_COMPLETED` | Emitted | `LearningReport{learningId, patterns[], recommendations[], updates[]}` | Pipeline complete |
| `LEARNING_FAILED` | Emitted | `FailureContext{learningId, error}` | Pipeline failure |
| `KNOWLEDGE_UPDATED` | Emitted | `KnowledgeUpdatePayload{memoryType, key, value, patternId}` | MemoryService sync |

#### 5.10.7 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **EventIngestion** | All Services | EventBus: wildcard `*` subscription | Consumes all phase events |
| **MemorySync** | MemoryService | EventBus: `MEMORY_STORE` / `MEMORY_CONSOLIDATE` | Persists learned patterns |
| **RecommendationDelivery** | Target Services | EventBus: `LEARNING_RECOMMENDATION` | Proactive optimization hints |
| **CouncilValidation** | CouncilService | EventBus: `COUNCIL_CONVENED` | High-impact pattern approval |
| **HumanApproval** | HumanInteractionService | EventBus: `HUMAN_ESCALATION_REQUIRED` | Security/arch pattern approval |

#### 5.10.8 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Event log ingestion gap | TRANSIENT | Backfill from StorageManager; mark `INGESTION_GAP` | Auto-recovery on next cycle |
| Pattern validation fails | PERMANENT | Discard pattern; emit `PATTERN_REJECTED` | No retry; learn from rejection |
| MemoryService sync fails | TRANSIENT | Retry with backoff (max 3) | Queue update; retry on next cycle |
| Recommendation ignored | N/A | Track `recommendationIgnored` metric | Learning governance adjusts confidence |

**Invariant:** `INV-LS-FH-001` — LearningService MUST NOT modify phase behavior directly; only emits recommendations.

#### 5.10.9 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-LS-001 | Every `LEARNING_COMPLETED` emits at least one `KNOWLEDGE_UPDATED` for MemoryService |
| INV-LS-002 | Pattern confidence requires minimum 3 observations (configurable) |
| INV-LS-003 | Recommendations include `patternId` for traceability to source events |
| INV-LS-004 | LearningService subscribes to ALL phase events via wildcard (explicit opt-in) |
| INV-LS-005 | High-impact patterns (security, kernel) require Council + Human approval before application |

#### 5.10.10 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-LS-001 | Implements `BaseService`; declares `depends_on: ["MemoryService", "CouncilService", "HumanInteractionService"]` | Static: registration validation |
| CONF-LS-002 | Subscribes to wildcard `*` in `on_start()` | Runtime: subscription verification |
| CONF-LS-003 | Emits `LEARNING_RECOMMENDATION` with valid pattern traceability | Contract test |
| CONF-LS-004 | Pattern validation statistical significance enforced | Unit test |
| CONF-LS-005 | High-impact pattern approval flow operational | Integration test |

---

### 5.11 Council Service

#### 5.11.1 Purpose

CouncilService implements the **LLM Council** — a mandatory governance body for architectural decisions, high-risk plans, security exceptions, and consensus-required actions. It manages voting, consensus algorithms, dissent recording, escalation, and decision finality.

#### 5.11.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| CL-R-001 | **Council Convening** | Assemble council for mandated decision types; select members per decision class |
| CL-R-002 | **Voting Protocol** | Execute configured consensus algorithm (MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT) |
| CL-R-003 | **Consensus Determination** | Evaluate votes; determine consensus reached, dissent, or deadlock |
| CL-R-004 | **Dissent Handling** | Record dissenting opinions; require dissent resolution or escalation |
| CL-R-005 | **Escalation Management** | Route unresolved decisions to HumanInteractionService (Final Judge) |
| CL-R-006 | **Decision Recording** | Emit immutable `CouncilDecisionRecord` with full rationale, votes, outcome |
| CL-R-007 | **Precedent Management** | Maintain decision precedent index for future reference |

#### 5.11.3 Council Membership

| Decision Class | Council Composition | Quorum | Algorithm |
|----------------|---------------------|--------|-----------|
| **Architectural** | 3 Architecture LLMs + 1 Security LLM | 3 | WEIGHTED (arch: 2x, sec: 1.5x) |
| **Security Exception** | 2 Security LLMs + 1 Architecture LLM | 2 | UNANIMOUS |
| **High-Risk Plan** | 3 Domain LLMs (rotating) | 2 | MAJORITY |
| **Quality Gate Override** | 2 Review LLMs + 1 Architecture LLM | 2 | CONSENT |
| **Resource Override** | 1 Architecture LLM + 1 Resource LLM | 2 | MAJORITY |

**Member Selection:** CapabilityManager resolves `council.member` capability; HealthManager verifies READY.

#### 5.11.4 Consensus Algorithms

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| **MAJORITY** | > 50% approval | Standard decisions |
| **UNANIMOUS** | 100% approval required | Security exceptions, kernel changes |
| **WEIGHTED** | Votes weighted by role/expertise | Architectural decisions |
| **RANKED_CHOICE** | Instant runoff on ranked preferences | Multi-option decisions |
| **CONSENT** | No objection (not necessarily approval) | Quality gate overrides |

#### 5.11.5 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `COUNCIL_CONVENED` | Consumed | `CouncilRequestPayload{decisionId, class, context, options[]}` | Mandated decision trigger |
| `COUNCIL_PROPOSAL_SUBMITTED` | Emitted | `ProposalPayload{decisionId, proposal, proposer}` | Member proposes option |
| `COUNCIL_VOTE_CAST` | Emitted (per vote) | `VotePayload{decisionId, voter, option, weight, rationale}` | Member votes |
| `COUNCIL_CONSENSUS_REACHED` | Emitted | `ConsensusPayload{decisionId, decision, votes[], algorithm}` | Consensus achieved |
| `COUNCIL_DISSENT_REGISTERED` | Emitted | `DissentPayload{decisionId, dissenter, rationale, resolutionPath}` | Dissent recorded |
| `COUNCIL_DECISION_FINALIZED` | Emitted | `CouncilDecisionRecord{decisionId, decision, rationale, precedent}` | Immutable record |
| `COUNCIL_ESCALATED` | Emitted | `EscalationPayload{decisionId, reason, target: HumanInteractionService}` | Deadlock/unresolved |

#### 5.11.6 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **CouncilTrigger** | Planning, Review, Deployment, Learning | EventBus: `*_REQUESTED` → `COUNCIL_CONVENED` | Mandated by phase logic |
| **DecisionDelivery** | Requesting Service | EventBus: `COUNCIL_CONSENSUS_REACHED` / `COUNCIL_ESCALATED` | Decision result |
| **MemberResolution** | CapabilityManager | EventBus: `CAPABILITY_INVOKE` (council.member) | Resolves council members |
| **HealthCheck** | HealthManager | EventBus: `HEALTH_CHECK` | Verifies member READY |
| **HumanEscalation** | HumanInteractionService | EventBus: `HUMAN_ESCALATION_REQUIRED` | Final Judge escalation |
| **MemoryPrecedent** | MemoryService | EventBus: `MEMORY_RETRIEVE` / `MEMORY_STORE` | Decision precedent storage |

#### 5.11.7 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Council member unavailable | TRANSIENT | Substitute from pool (configured alternatives) | Original member reinstated when healthy |
| Consensus deadlock | CRITICAL | Emit `COUNCIL_ESCALATED` to HumanInteractionService | Human Final Judge decides |
| Vote timeout | TIMEOUT | Default to abstain; continue with remaining votes | Quorum check; if lost → escalate |
| Decision recording fails | TRANSIENT | Retry StorageManager write (max 3) | Escalate to RCA on exhaustion |
| Member returns invalid vote | PERMANENT | Reject vote; request re-vote (max 1) | If persistent → member health DEGRADED |

**Invariant:** `INV-CL-FH-001` — Security exception decisions REQUIRE UNANIMOUS consensus.
**Invariant:** `INV-CL-FH-002` — All Council decisions are immutable once `COUNCIL_DECISION_FINALIZED`.

#### 5.11.8 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-CL-001 | Every mandated decision class triggers `COUNCIL_CONVENED` (no opt-out) |
| INV-CL-002 | CouncilDecisionRecord includes: decision, votes, rationale, algorithm, timestamp, precedent links |
| INV-CL-003 | Dissent is always recorded; never suppressed |
| INV-CL-004 | Escalation to HumanInteractionService is mandatory for deadlock/unresolved |
| INV-CL-005 | Council members are resolved via CapabilityManager (no hardcoded identities) |
| INV-CL-006 | Precedent index updated on every `COUNCIL_DECISION_FINALIZED` |

#### 5.11.9 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-CL-001 | Implements `BaseService`; declares `depends_on: ["CapabilityManager", "HealthManager", "MemoryService", "HumanInteractionService"]` | Static: registration validation |
| CONF-CL-002 | Subscribes to `COUNCIL_CONVENED` | Runtime: subscription verification |
| CONF-CL-003 | All consensus algorithms implemented correctly | Unit test (each algorithm) |
| CONF-CL-004 | Dissent recorded for every non-unanimous decision | Contract test |
| CONF-CL-005 | Escalation to HumanInteractionService on deadlock | Integration test |
| CONF-CL-006 | DecisionRecord immutable and auditable | Audit test |
| CONF-CL-007 | Zero direct service calls; EventBus only | Static analysis |

---

### 5.12 Human Interaction Service

#### 5.12.1 Purpose

HumanInteractionService manages **all human-in-the-loop interactions** — approvals, interruptions, questions, escalations, manual overrides, and feedback collection. It is the exclusive interface between AI-OS autonomous execution and human governance.

#### 5.12.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| HI-R-001 | **Human Approvals** | Present approval requests; collect decisions; enforce timeout policies |
| HI-R-002 | **Interruptions** | Pause workflows for human input; resume on response |
| HI-R-003 | **Questions** | Route clarifying questions to appropriate humans; collect structured responses |
| HI-R-004 | **Escalations** | Manage escalation paths: on-call → lead → architect → executive |
| HI-R-005 | **Manual Overrides** | Execute human-directed actions (rollback, deploy, config change) with audit |
| HI-R-006 | **Feedback Collection** | Capture human feedback on AI decisions; feed to LearningService |
| HI-R-007 | **Notification Routing** | Multi-channel (Slack, email, PagerDuty, webhook); deduplication; acknowledgment |

#### 5.12.3 Interaction Types

| Type | Trigger | SLA | Escalation | Audience |
|------|---------|-----|------------|----------|
| **Plan Approval** | High-risk plan | 4 hours | Architect → CTO | Architect |
| **Security Exception** | Review CRITICAL finding | 1 hour | Security Lead → CISO | Security Lead |
| **Production Deploy** | Staging→Prod gate | 30 min | On-call → Lead → Manager | On-call Engineer |
| **Rollback Confirmation** | Auto-rollback triggered | 5 min | On-call → Lead | On-call Engineer |
| **Architecture Override** | Council deadlock | 2 hours | Architect → CTO | Chief Architect |
| **Clarification Question** | Ambiguous requirement | 8 hours | Requestor → Lead | Domain Expert |
| **Manual Override Request** | Operator intervention | Immediate | N/A | Authorized Operator |

#### 5.12.4 Escalation Policies

| Policy | Rules |
|--------|-------|
| **Timeout Escalation** | No response in SLA → auto-escalate to next level; max 3 levels |
| **Acknowledgment Required** | Human MUST acknowledge receipt; no auto-ack |
| **Delegation** | Human may delegate to qualified peer; delegation logged |
| **Override Authority** | Only `kernel.admin` principals may execute Manual Overrides |
| **Audit Trail** | Every interaction logged: request, response, timing, delegations, channel |

#### 5.12.5 Events

| Event Type | Direction | Payload | Trigger |
|------------|-----------|---------|---------|
| `HUMAN_ESCALATION_REQUIRED` | Consumed | `HumanEscalationPayload{requestId, type, context, sla, audience}` | Phase mandates human |
| `HUMAN_QUESTION` | Consumed | `QuestionPayload{requestId, question, context, options[]}` | Phase needs clarification |
| `HUMAN_APPROVAL_REQUESTED` | Consumed | `ApprovalPayload{requestId, artifact, criteria}` |
| `HUMAN_RESPONSE_RECEIVED` | Emitted | `HumanResponsePayload{requestId, decision, respondent, rationale, timestamp}` | Human responds |
| `HUMAN_TIMEOUT` | Emitted | `TimeoutPayload{requestId, escalationLevel, nextAudience}` | SLA expired |
| `HUMAN_OVERRIDE_EXECUTED` | Emitted | `OverridePayload{requestId, action, operator, auditTrail}` | Manual override performed |
| `HUMAN_FEEDBACK` | Emitted | `FeedbackPayload{targetEventId, rating, comment, categories[]}` | Human provides feedback |

#### 5.12.6 Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **EscalationConsumption** | All Services | EventBus: `HUMAN_ESCALATION_REQUIRED` | Receives mandated escalations |
| **ResponseDelivery** | Requesting Service | EventBus: `HUMAN_RESPONSE_RECEIVED` / `HUMAN_TIMEOUT` | Delivers human decision |
| **NotificationChannels** | ObservabilityManager | EventBus: `NOTIFICATION_SEND` | Multi-channel delivery |
| **AuditLogging** | SecurityManager | EventBus: `SECURITY_AUDIT_EVENT` | Human interaction audit |
| **LearningFeedback** | LearningService | EventBus: `LEARNING_REQUESTED` + `HUMAN_FEEDBACK` | Feedback for pattern extraction |
| **IdentityVerification** | SecurityManager | EventBus: `AUTHORIZE_REQUEST` | Verifies human identity/authority |

#### 5.12.7 Failure Handling

| Failure Scenario | Classification | Response | Recovery |
|------------------|----------------|----------|----------|
| Notification delivery fails | TRANSIENT | Retry all channels (max 3); try alternate contact | Alert via ObservabilityManager |
| Human unresponsive (all levels) | CRITICAL | Emit `HUMAN_UNRESPONSIVE`; pause dependent workflows | Requires manual intervention |
| Invalid response format | PERMANENT | Reject; request re-submission with guidance | Auto-retry with structured form |
| Unauthorized override attempt | SECURITY | Reject; emit `SECURITY_AUDIT_EVENT` (UNAUTHORIZED_OVERRIDE) | SecurityManager investigation |
| Channel misconfiguration | TRANSIENT | Fallback to default channel; alert admin | Config fix via ConfigurationManager |

**Invariant:** `INV-HI-FH-001` — Production deployment gate MANDATES `HUMAN_RESPONSE_RECEIVED` with `decision: APPROVED`.
**Invariant:** `INV-HI-FH-002` — Security exception gates REQUIRE Security Lead or above approval.

#### 5.12.8 Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-HI-001 | Every `HUMAN_ESCALATION_REQUIRED` receives exactly one `HUMAN_RESPONSE_RECEIVED` or `HUMAN_TIMEOUT` |
| INV-HI-002 | Escalation path followed strictly; no level skipped without explicit delegation |
| INV-HI-003 | All human interactions produce immutable audit record in StorageManager (audit namespace) |
| INV-HI-004 | Manual overrides require `kernel.admin` authorization (SecurityManager verified) |
| INV-HI-005 | Feedback is always routed to LearningService via `HUMAN_FEEDBACK` event |
| INV-HI-006 | HumanInteractionService NEVER makes autonomous decisions; only collects and routes |

#### 5.12.9 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-HI-001 | Implements `BaseService`; declares `depends_on: ["SecurityManager", "ObservabilityManager", "MemoryService", "LearningService"]` | Static: registration validation |
| CONF-HI-002 | Subscribes to `HUMAN_ESCALATION_REQUIRED`, `HUMAN_QUESTION`, `HUMAN_APPROVAL_REQUESTED` | Runtime: subscription verification |
| CONF-HI-003 | Escalation policies enforced per configuration | Integration test |
| CONF-HI-004 | Notification delivery tracking operational | Contract test |
| CONF-HI-005 | Audit trail complete for all interactions | Audit test |
| CONF-HI-006 | Zero direct service calls; EventBus only | Static analysis |

---

### 5.13 Service Interaction

#### 5.13.1 Dependency Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| **ENG-SI-001** | Services declare `depends_on` at registration; ServiceRegistry validates acyclic DAG | Static (registration) + Runtime (initialization) |
| **ENG-SI-002** | SDLC Phase Services form linear chain: Planning → Coding → Review → Testing → Deployment → Operations | Architecture invariant; WorkflowManager enforces |
| **ENG-SI-003** | Knowledge Services depend on all prior phases they learn from | Declared in `depends_on`; verified by ServiceRegistry |
| **ENG-SI-004** | Governance Services (Council, Human Interaction) have no phase dependencies | They are invoked, not depended upon |
| **ENG-SI-005** | MemoryService is universal dependency (all services may need context) | Declared by all; verified by ServiceRegistry |

#### 5.13.2 Communication Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| **ENG-SI-010** | **All** inter-service communication via EventBus (Part 0 Principle 1) | Static analysis: zero direct imports/calls |
| **ENG-SI-011** | Services subscribe in `on_start()`; publish via `BaseService.emit()` | BaseService contract |
| **ENG-SI-012** | Events carry `correlationId` (workflow trace) and `causationId` (direct cause) | Part 2 Event contract |
| **ENG-SI-013** | Services emit exactly one completion event per trigger: `*_COMPLETED` / `*_FAILED` | Contract test |
| **ENG-SI-014** | Failure events include `FailureContext` for RCA (Part 4 §4.5) | Event schema validation |
| **ENG-SI-015** | Services do not poll; they react to events (event-driven) | Static analysis: no polling loops |

#### 5.13.3 Ownership Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| **ENG-SI-020** | Each SDLC phase owned by exactly one service | Architecture definition |
| **ENG-SI-021** | Service owns its phase artifacts; other services read via events | Event payload contracts |
| **ENG-SI-022** | Service does not modify another service's artifacts | Immutable event payloads |
| **ENG-SI-023** | Governance Services own decision records; phases consume them | CouncilService & HumanInteractionService ownership |

#### 5.13.4 Forbidden Interactions

| Forbidden Pattern | Reason | Detection |
|-------------------|--------|-----------|
| Service A calls Service B method directly | Violates Event-First (Part 0 Principle 1) | Static analysis: cross-service imports |
| Service A subscribes to Service B's internal events | Violates encapsulation | Event naming convention: only public `*_REQUESTED`, `*_COMPLETED`, `*_FAILED` |
| Service A modifies Service B's workspace/state | Violates ownership | Static analysis: no shared filesystem/db access |
| Service implements another service's phase logic | Violates phase isolation | Architecture review |
| Service bypasses governance gates (Council/Human) | Violates governance (Part 0 Principle 3) | WorkflowManager enforcement |

#### 5.13.5 Cross-Service Event Contracts

| Event Category | Naming Convention | Payload Schema | Example |
|----------------|-------------------|----------------|---------|
| **Phase Trigger** | `{PHASE}_REQUESTED` | `PhaseRequestPayload` | `PLANNING_REQUESTED` |
| **Phase Success** | `{PHASE}_COMPLETED` | `PhaseResultPayload` + Artifacts | `PLANNING_COMPLETED` |
| **Phase Failure** | `{PHASE}_FAILED` | `FailureContext` | `PLANNING_FAILED` |
| **Governance** | `COUNCIL_*`, `HUMAN_*` | Governance-specific | `COUNCIL_CONVENED` |
| **Artifact** | `ARTIFACT_CREATED`, `ARTIFACT_UPDATED` | `ArtifactPayload` | `ARTIFACT_CREATED` |
| **Finding** | `FINDING_EMITTED`, `SECURITY_FINDING` | `FindingPayload` | `FINDING_EMITTED` |
| **Learning** | `LEARNING_RECOMMENDATION`, `PATTERN_EXTRACTED` | `LearningPayload` | `LEARNING_RECOMMENDATION` |

---

### 5.14 Cross-Service Invariants

The following invariants are **mandatory** and objectively testable. They apply across all Engineering Services.

#### 5.14.1 Architectural Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| **INV-CSI-001** | **Event-First Purity:** Zero direct method calls between any two Engineering Services. All communication via EventBus. | Static analysis (import graph, call graph) |
| **INV-CSI-002** | **Phase Linearity:** SDLC Phase Services execute in strict order: Planning → Coding → Review → Testing → Deployment → Operations. No phase skipping, no parallel phase execution for same `correlationId`. | WorkflowManager enforcement; EventBus correlation tracing |
| **INV-CSI-003** | **Completion Determinism:** Given identical input events and configuration, a service produces bit-for-bit identical output artifacts. | Replay testing (Part 2 §2.11) |
| **INV-CSI-004** | **Failure as Data:** No exceptions cross service boundaries. All failures emitted as `*_FAILED` events with `FailureContext`. | Contract test; exception monitoring |
| **INV-CSI-005** | **Correlation Integrity:** Every event emitted by a service in response to a trigger event carries the same `correlationId` and the trigger's `eventId` as `causationId`. | Event schema validation |
| **INV-CSI-006** | **Governance Gate Enforcement:** No SDLC phase completes without mandated Council/Human gates for its decision class. | WorkflowManager gate verification |
| **INV-CSI-007** | **Artifact Immutability:** Once emitted in `*_COMPLETED` event, phase artifacts are immutable. Revision requires new phase execution with new `planId`/`correlationId`. | StorageManager write-once enforcement |
| **INV-CSI-008** | **Memory Ubiquity:** All services declare `depends_on: ["MemoryService"]` and use MemoryService for context. | Registration validation |
| **INV-CSI-009** | **Capability Abstraction:** Services invoke capabilities ONLY via Capability Facade Services (Part 6), never direct Core Manager calls for capabilities. | Static analysis: no `kernel.memory`, `kernel.llm`, `kernel.tools` for capability use |
| **INV-CSI-010** | **Health Contract:** Every service implements `healthCheck()` returning `HealthStatus` with `ready: boolean`, `details: object`. | BaseService interface verification |

#### 5.14.2 Runtime Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| **INV-CSI-RT-001** | **EventBus Liveness:** All services in RUNNING state publish `HEARTBEAT` every 30s (configurable). | EventBus monitoring |
| **INV-CSI-RT-002** | **Backpressure Response:** Services respect `RESOURCE_PRESSURE` events by throttling non-critical work. | Load test with ResourceManager pressure |
| **INV-CSI-RT-003** | **Graceful Degradation:** Service in DEGRADED state continues processing critical events; emits `SERVICE_DEGRADED`. | Chaos test (dependency failure) |
| **INV-CSI-RT-004** | **No Event Loss:** EventBus at-least-once delivery (Part 2 §2.8) ensures no phase trigger lost. | EventBus conformance (Part 2) |
| **INV-CSI-RT-005** | **Deterministic Replay:** Full SDLC replay from `PLANNING_REQUESTED` produces identical final deployment. | Replay test suite |

#### 5.14.3 Governance Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| **INV-CSI-GOV-001** | **Council Mandatory:** Architectural decisions, security exceptions, quality gate overrides REQUIRE Council consensus. | WorkflowManager gate check |
| **INV-CSI-GOV-002** | **Human Mandatory:** Production deployment, security CRITICAL, kernel-impacting changes REQUIRE Human approval. | WorkflowManager gate check |
| **INV-CSI-GOV-003** | **Final Judge Authority:** Council deadlock or dissent unresolved → HumanInteractionService Final Judge decides. | CouncilService escalation contract |
| **INV-CSI-GOV-004** | **Audit Completeness:** Every governance decision (Council, Human, Override) emits audit event to StorageManager (audit namespace). | Audit log verification |

---

### 5.15 Conformance Requirements

#### 5.15.1 Static Verification (Build-Time)

| Requirement ID | Check | Tooling |
|----------------|-------|---------|
| **CONF-ENG-ST-001** | All 10 Engineering Services implement `BaseService` | TypeScript/Python AST interface check |
| **CONF-ENG-ST-002** | Each service declares `depends_on` matching §5.2.4 matrix | Registration metadata validation |
| **CONF-ENG-ST-003** | Each service declares `capabilities` per Part 4 capability contract | Capability schema validation |
| **CONF-ENG-ST-004** | Criticality flags set per §5.2.2 table | Metadata validation |
| **CONF-ENG-ST-005** | Zero direct imports between service modules | Import graph analysis |
| **CONF-ENG-ST-006** | Zero direct Core Manager capability calls (`kernel.memory`, `kernel.llm`, etc.) | Call graph analysis |
| **CONF-ENG-ST-007** | All event types used are registered in EventTypeRegistry (Part 2) | Event type reference validation |
| **CONF-ENG-ST-008** | All emitted event payloads conform to declared schemas | Schema validation (JSON Schema) |
| **CONF-ENG-ST-009** | Service `on_start()` registers subscriptions; `on_stop()` deregisters | Lifecycle method analysis |
| **CONF-ENG-ST-010** | Each service has `healthCheck()` implementation | Interface verification |

#### 5.15.2 Dynamic Verification (Runtime)

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| **CONF-ENG-DY-001** | All services initialize in topological order per `depends_on` | Integration test (kernel startup) |
| **CONF-ENG-DY-002** | All services reach RUNNING state within configured timeout | Kernel initialization test |
| **CONF-ENG-DY-003** | `PLANNING_REQUESTED` → `PLANNING_COMPLETED` → `CODING_REQUESTED` → ... → `DEPLOYMENT_COMPLETED` event chain executes | End-to-end integration test (21 scenarios) |
| **CONF-ENG-DY-004** | CouncilService convenes for all mandated decision classes | Governance test suite |
| **CONF-ENG-DY-005** | HumanInteractionService enforces SLA and escalation | Chaos test (human unresponsive) |
| **CONF-ENG-DY-006** | Failure injection at any phase triggers RCA → Recovery Action → Retry/Escalation | Failure injection test suite |
| **CONF-ENG-DY-007** | LearningService extracts patterns from completed workflows | Learning pipeline test |
| **CONF-ENG-DY-008** | All services emit `HEARTBEAT` at configured interval | EventBus monitoring |
| **CONF-ENG-DY-009** | Service shutdown in reverse topological order | Kernel shutdown test |
| **CONF-ENG-DY-010** | MemoryService context assembly/retrieval functional for all services | Cross-service memory test |

#### 5.15.3 Architectural Verification (ARB Audit)

| Requirement ID | Check | Frequency |
|----------------|-------|-----------|
| **CONF-ENG-AR-001** | No Principle violations (Part 0 §0.4 Principles 1–12) | Every ARB audit (quarterly) |
| **CONF-ENG-AR-002** | All Invariants (§5.14) hold under load/failure | Every ARB audit + continuous monitoring |
| **CONF-ENG-AR-003** | Governance gates (Council, Human) not bypassed in production | Production audit (monthly) |
| **CONF-ENG-AR-004** | Capability Facade usage pattern compliance | Static + runtime audit |
| **CONF-ENG-AR-005** | Documentation drift ≤ threshold (Part 5.8) | Continuous + quarterly review |

#### 5.15.4 Audit Requirements

| Audit Artifact | Source | Retention | Review Cadence |
|----------------|--------|-----------|----------------|
| **Service Registration Manifest** | ServiceRegistry | Permanent | Every deploy |
| **Event Flow Traces** | EventBus (correlationId) | 90 days | On incident + monthly sample |
| **Governance Decisions** | CouncilService, HumanInteractionService | 7 years (audit namespace) | Quarterly |
| **Learning Patterns** | LearningService → MemoryService | Pattern TTL (90d default) | Monthly |
| **Conformance Reports** | Automated tooling | 1 year | Every CI run |
| **Architecture Decision Records** | `docs/DECISIONS.md` | Permanent | Every change |

#### 5.15.5 Violation Handling

| Severity | Detection | Response |
|----------|-----------|----------|
| **Build-Time FAIL** | Static analysis, type check, schema validation | CI pipeline blocks; merge prohibited |
| **Runtime CRITICAL** | Invariant violation (INV-CSI-*) in RUNNING | Kernel transitions to DEGRADED; alert; auto-recovery or shutdown |
| **Runtime DEGRADED** | Missed heartbeat, SLA breach, non-critical invariant | Alert via ObservabilityManager; remediation within 4 hours |
| **Audit Finding** | ARB review finds architectural violation | ARB review; remediation plan within 5 business days (Part 0 §0.5.3) |

---

### 5.16 Architecture Target

#### 5.16.1 Current Implementation (v0.1.x)

| Aspect | Current State (v0.1.x) | Gaps vs Target |
|--------|------------------------|----------------|
| **Service Count** | 3–5 ad-hoc services | Target: 10 services with defined taxonomy |
| **Communication** | Mixed direct calls + events | Target: 100% EventBus-only (INV-CSI-001) |
| **Phase Pipeline** | Implicit, no enforcement | Target: Linear mandatory gates (INV-CSI-002) |
| **Governance** | Ad-hoc human review | Target: CouncilService + HumanInteractionService mandatory |
| **Failure Handling** | Try-catch, inconsistent | Target: RCA → RecoveryAction event chain |
| **Learning** | None | Target: LearningService with pattern extraction |
| **Memory** | Basic in-memory | Target: MemoryService with multi-backend sync |
| **Research** | None | Target: ResearchService with evidence governance |
| **Documentation** | Manual | Target: DocumentationService auto-generation |
| **Conformance** | None | Target: Static (L1/L2) + Dynamic (L3/L4) mandatory |

#### 5.16.2 Target Architecture (v1.0)

The target architecture is **this specification (Part 5)**. All gaps in §5.16.1 are work items for the implementation team. The Architecture Target does not change to match implementation; implementation must converge to target.

#### 5.16.3 Migration Guidance

| Phase | Milestone | Services | Key Deliverables |
|-------|-----------|----------|------------------|
| **M1: Foundation** | EventBus-only communication; BaseService compliance | All existing services | Static analysis clean; INV-CSI-001 verified |
| **M2: Phase Pipeline** | Linear SDLC gates enforced by WorkflowManager | Planning, Coding, Review, Testing, Deployment | End-to-end `*_REQUESTED` → `*_COMPLETED` chain |
| **M3: Governance** | CouncilService + HumanInteractionService operational | Council, Human Interaction | Mandatory gates for architectural/security/prod |
| **M4: Knowledge** | MemoryService + LearningService + ResearchService | Memory, Learning, Research | Pattern extraction; evidence-based decisions |
| **M5: Documentation** | DocumentationService auto-generates all types | Documentation | Zero manual docs for API/architecture/runbooks |
| **M6: Conformance** | Full L1–L4 verification in CI | All | Zero audit findings; automated gates |

**Migration Invariants:**
- **INV-MIG-001** — No phase of migration may violate INV-CSI-001 (Event-First).
- **INV-MIG-002** — Each milestone must pass all conformance checks for delivered services.
- **INV-MIG-003** — Legacy direct-call paths removed before new service depends on them.

---

### 5.17 Summary

#### 5.17.1 Engineering Services Catalog

| # | Service | Namespace | Type | Criticality | Primary Trigger | Primary Output |
|---|---------|-----------|------|-------------|-----------------|----------------|
| 1 | PlanningService | engineering | SDLC Phase | CRITICAL | `PLANNING_REQUESTED` | PlanArtifact |
| 2 | CodingService | engineering | SDLC Phase | CRITICAL | `CODING_REQUESTED` (from Planning) | Code Artifacts |
| 3 | ReviewService | engineering | SDLC Phase | CRITICAL | `REVIEW_REQUESTED` (from Coding) | ReviewReport |
| 4 | TestingService | engineering | SDLC Phase | CRITICAL | `TESTING_REQUESTED` (from Review) | TestReport |
| 5 | DeploymentService | engineering | SDLC Phase | CRITICAL | `DEPLOYMENT_REQUESTED` (from Testing) | DeploymentReport |
| 6 | OperationsService | engineering | SDLC Phase | HIGH | `OPERATIONS_REQUESTED` (from Deployment) | OperationsReport |
| 7 | LearningService | engineering | Knowledge | HIGH | `LEARNING_REQUESTED` (scheduled/post-phase) | LearningReport |
| 8 | MemoryService | engineering | Knowledge | HIGH | `MEMORY_*` events (ubiquitous) | Context/Patterns |
| 9 | ResearchService | engineering | Knowledge | MEDIUM | `RESEARCH_REQUESTED` (on-demand) | ResearchReport |
| 10 | DocumentationService | engineering | Knowledge | MEDIUM | `DOCUMENTATION_REQUESTED` (post-phase) | Documentation Artifacts |
| 11 | CouncilService | facade | Governance | CRITICAL | `COUNCIL_CONVENED` (mandated) | CouncilDecisionRecord |
| 12 | HumanInteractionService | facade | Governance | CRITICAL | `HUMAN_ESCALATION_REQUIRED` (mandated) | HumanResponse |

#### 5.17.2 Key Architectural Properties

| Property | Specification |
|----------|---------------|
| **Communication** | 100% EventBus (Part 2); zero direct service calls (INV-CSI-001) |
| **Phase Order** | Strict linear: Planning → Coding → Review → Testing → Deployment → Operations (INV-CSI-002) |
| **Governance** | Council (LLM consensus) + Human (Final Judge) mandatory for defined decision classes |
| **Failure Model** | Failure as Data: `*_FAILED` events with `FailureContext` → RCA → RecoveryAction |
| **Learning Loop** | Every phase emits learnings → LearningService → patterns → MemoryService → next execution |
| **Memory** | Universal dependency; multi-backend (Working, Episodic, Semantic, Obsidian, Graphify) |
| **Conformance** | L1 Structural, L2 Contract, L3 Behavioral, L4 Architectural — all mandatory |
| **Determinism** | Replay from any phase boundary produces identical results (Part 2 §2.11) |

#### 5.17.3 Cross-Reference to Parts 0–4

| Part | Referenced Sections | Purpose in Part 5 |
|------|---------------------|-------------------|
| **Part 0** | Principles 1, 2, 3, 5, 6, 7, 9, 12; §0.2.1, §0.3, §0.4, §0.5 | Foundational principles, terminology, conformance model |
| **Part 1** | §1.8.4 (singleton accessors), §1.12 (failure handling), §1.13 (kernel API) | Kernel integration, manager access, failure classification |
| **Part 2** | §2.1 (Event System purpose), §2.2 (Event contract), §2.3 (EventType catalog), §2.4 (EventBus), §2.5 (Subscription), §2.7 (Ordering), §2.8 (Delivery), §2.11 (Replay), §2.12 (Observability) | All event-driven communication, correlation, replay, observability |
| **Part 3** | §3.4 (ServiceRegistry), §3.5 (ConfigurationManager), §3.6 (StructuredLogger) | Service registration, configuration, logging |
| **Part 4** | §4.2 (Service Framework), §4.3 (LifecycleManager), §4.4 (StateManager), §4.5 (StorageManager), §4.6 (WorkflowManager), §4.7 (SecurityManager), §4.8 (CapabilityManager), §4.9 (ResourceManager), §4.10 (HealthManager), §4.11 (ObservabilityManager) | Service lifecycle, workflow orchestration, capability access, health, resources |

#### 5.17.4 Conformance Summary

| Level | Scope | Status |
|-------|-------|--------|
| **L1: Structural** | All 12 services implement BaseService; correct dependencies; event contracts | Mandatory for v1.0 |
| **L2: Contract** | All event payloads valid; schemas registered; subscriptions correct | Mandatory for v1.0 |
| **L3: Behavioral** | 21 integration scenarios pass; phase pipeline executes; governance gates enforce | Mandatory for v1.0 |
| **L4: Architectural** | Zero Principle violations; all INV-CSI-* invariants hold; audit clean | Mandatory for v1.0 |

---

**END OF PART 5 — ENGINEERING SERVICES ARCHITECTURE**

*This document is FROZEN. Any modification requires Architecture Review Board approval. All subsequent Parts (6–N) MUST conform to this specification.*