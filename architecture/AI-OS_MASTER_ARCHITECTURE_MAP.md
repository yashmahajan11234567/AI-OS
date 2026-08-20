# AI-OS MASTER ARCHITECTURE MAP

> **Classification:** Informative index / navigation map
> **Basis:** `architecture/Common/MASTER_ARCHITECTURE_ROADMAP.md`, `architecture/Common/ARCHITECTURE_SPEC_TOC.md`, `architecture/project-knowledge/AI_OS_MASTER_CONTEXT.md`, Part READMEs, part inventories, and diagrams/metadata under `architecture/project-knowledge/diagrams/`.
> **Scope:** read-only synthesis of existing architecture documentation only.

---

## 1. INVENTORY

This inventory is organized by type and covers documentation present under `C:\Development\AI-OS\architecture\`.

### 1.1 Architecture Specification Parts

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `Part00/ARCHITECTURE_SPEC_PART0.md` | Normative spec | Front matter: scope, terminology, principles, extension points, conformance levels, ADR process | Part 0 | Authoritative frozen foundation |
| `Part01/ARCHITECTURE_SPEC_PART1.md` | Normative spec | System overview, layer map, component taxonomy, kernel/core concepts | Part 1 | Authoritative for system overview |
| `Part02/ARCHITECTURE_SPEC_PART2.md` | Normative spec | Event system: Event base, EventType catalog, EventBus, subscriptions, correlation/causation | Part 2 | Authoritative for event substrate |
| `Part03/ARCHITECTURE_SPEC_PART3.md` | Normative spec | Hermes Kernel specification: lifecycle, singleton registry, ServiceRegistry, kernel API | Part 3 | Authoritative for kernel runtime |
| `Part04/ARCHITECTURE_SPEC_PART4.md`, `Part04/ARCHITECTURE_SPEC_PART4A.md`, `Part04/ARCHITECTURE_SPEC_PART4B.md`, `Part04/ARCHITECTURE_SPEC_PART4C.md` | Normative spec | Core managers: State, Workflow, Checkpoint, Retry, RCA, Memory, Skill, MCP, Council, AI Agency, ModelRouter, ResourceManager | Part 4 | Authoritative for all kernel managers |
| `Part05/ARCHITECTURE_SPEC_PART5.md` | Normative spec | Service framework: BaseService contract, ServiceRegistry, metadata, testing contract | Part 5 | Authoritative for services |
| `Part06/ARCHITECTURE_SPEC_PART6_STEP1.md` … `STEP11.md` and `STEP3_MCP.md` | Normative spec | Engineering services (Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory Service facade) and capability facades (SkillService, CouncilService, MCPService, MemoryService) | Part 6 | Authoritative for services |
| `Part07/ARCHITECTURE_SPEC_PART7_STEP1.md` … `STEP10.md` | Normative spec | Configuration system: AppConfig, layered loading, validation, YAML schema, CLI doctor | Part 7 | Authoritative for configuration |
| `Part08/ARCHITECTURE_SPEC_PART8_STEP1.md` … `STEP10.md`; `PART8_CONTEXT.md` | Normative spec | CLI command specification: version, doctor, kernel, workflow, service, event, checkpoint, memory, skill, MCP, council, learning | Part 8 | Authoritative for CLI |
| `Part09/ARCHITECTURE_SPEC_PART9_STEP1.md` … `STEP20.md`; `shared/*.json` | Normative spec + shared schemas | Observability & logging: structured logging, metrics, tracing, health checks; shared JSON schemas for lifecycle, feature flags, config, deployment, version policy | Part 9 | Authoritative for observability |
| `Part10/ARCHITECTURE_SPEC_PART10_STEP01.md` … `STEP08.md`; `PART10_CONTEXT.md` | Normative spec | AI Runtime Architecture | Part 10 | Authoritative for runtime |
| `Part11/ARCHITECTURE_SPEC_PART11_STEP01.md` … `STEP08.md`; `PART11_CONTEXT.md` | Normative spec | Agent & Cognitive Architecture | Part 11 | Authoritative for cognition |
| `Part12/12.1-Architecture-Overview.md` … `12.13-Cross-References-and-ADR-Summary.md`; `README.md`, `context.md`, `components.md`, `events.md`, `schemas.md`, `adrs.md`, `dependency-map.md`, `review-checklist.md`, `glossary.md` | Normative chapter set | Multi-Agent Collaboration Architecture: discovery, delegation, workflow orchestration, council decisions, shared context, multi-agent communication, resource coordination, reliability/recovery/performance, security, schemas, invariants/conformance, cross-references/ADRs | Part 12 | Authoritative for collaboration |
| `Part13/13.1-Architecture-Overview.md` … `13.13-Cross-References-and-ADR-Summary.md`; `README.md`, `context.md`, `components.md`, `governance-events.md`, `policies.md`, `schemas.md`, `adrs.md`, `dependency-map.md`, `review-checklist.md`, `glossary.md` | Normative chapter set | Governance Architecture: policy architecture, decision authority/delegation, governance councils/committees, risk/compliance, agent/capability governance, workflow/execution governance, data/knowledge governance, security/trust governance, auditability/accountability, invariants/conformance | Part 13 | Authoritative for governance |
| `Part14/14.1-Architecture-Overview.md` … `14.13-Cross-References-and-ADR-Summary.md`; `README.md`, `context.md`, `components.md`, `events.md`, `schemas.md`, `adrs.md`, `dependency-map.md`, `review-checklist.md`, `glossary.md`, `integrations.md`, `interfaces.md`, `MEMORY.md` | Normative chapter set | Integration Architecture: how Parts 0–13 compose, platform integration, API/interface architecture, plugin/extension architecture, external-system integration, model/provider integration, storage/data integration, observability/operations integration, deployment/infrastructure integration, integration security, integration schemas/contracts, integration invariants/conformance, cross-references/ADRs; status taxonomy: EXISTING/DERIVED/ASSUMPTION/UNSPECIFIED/GAP/PROPOSED/FUTURE/CONFLICT | Part 14 | Authoritative for integration composition |
| `Part15/README.md`, `glossary.md`, `adrs.md`, `components.md`, `configuration.md`, `deployment.md`, `dependency-map.md`, `implementation-contracts.md`, `observability.md`, `review-checklist.md`; chapters `15.1`…`15.13`; `context.md`, `runtime-map.md`, `testing.md` | Partially normative chapter set | Architecture Evolution & Extensibility: implementation-facing mapping from specification to implementation, extension points catalog, implementation gap registry, deployment/observability/configuration mapping, conformance/review mechanisms. Many chapter/supporting files are currently empty; final gate is NOT READY. | Part 15 | Implementation-facing bridge; still incomplete |

### 1.2 Common / Master Documents

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `Common/MASTER_ARCHITECTURE_ROADMAP.md` | Master index/roadmap | 15-part roadmap, shared components, shared JSON schemas, ADR mapping categories, global principles, global runtime invariants, document standards, progress tracker | All parts | Primary navigation document |
| `Common/ARCHITECTURE_SPEC_TOC.md` | Planned TOC/spec outline | Recommended table of contents; cross-reference to implementation files; open decisions list | All parts | Planning artifact; superseded by frozen Part0 but still referenced |
| `Common/ARCHITECTURAL_INVENTORY.md` | Inventory/evidence | Implementation inventory; source evidence for planning and reviews | All parts | Evidence base for review |
| `Common/ARCHITECTURE_ANALYSIS.md` | Analysis | Architectural analysis document | All parts | Supporting analysis |
| `Common/ARCHITECTURE_REVIEW_REPORT.md` | Review report | Review/audit report evidence | All parts | Supporting review artifact |

### 1.3 Project-Knowledge Documents

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/AI_OS_MASTER_CONTEXT.md` | Master context / synthesis | Defines AI-OS principles, layers, kernel, managers, services, agency/governance, memory, skills, MCP, repo ecosystem, observability, recovery, validation, learning, runtime, engineering principles, migration guidance | All parts | High-level authoritative narrative |
| `project-knowledge/ROADMAP.md` | Roadmap | Near/mid/long-term roadmap for specification, ecosystem, reference runtime, governance | All parts | Roadmap/navigation |
| `project-knowledge/IMPLEMENTATION_GUIDE.md` | Implementation guidance | Conformance guidance for implementations | All parts | Implementation guidance |
| `project-knowledge/VALIDATION_ARCHITECTURE.md` | Validation architecture | Methods for assessing specification conformance | All parts | Validation methodology |
| `project-knowledge/ENGINEERING_PRINCIPLES.md` | Principles | Foundational engineering principles | All parts | Principles source |
| `project-knowledge/ARCHITECTURE_EVOLUTION.md` | History | Historical progression to current state | All parts | Context/history |
| `project-knowledge/ARCHITECTURE_DECISIONS.md` | ADR index | Foundational architectural decisions | All parts | Decision history |
| `project-knowledge/GLOSSARY.md` | Terminology | Consolidated terminology | All parts | Term reference |
| `project-knowledge/AI_AGENCY.md` | Agency overview | AI agency overview | AIAgencyService | Agency context |
| `project-knowledge/COUNCILS.md` | Councils overview | Council governance overview | CouncilManager | Council context |
| `project-knowledge/MEMORY_ARCHITECTURE.md` | Memory overview | Memory architecture overview | MemoryManager | Memory context |
| `project-knowledge/MCP_ECOSYSTEM.md` | MCP overview | MCP ecosystem overview | MCPManager/MCPService | MCP context |
| `project-knowledge/SKILLS_ECOSYSTEM.md` | Skills overview | Skills ecosystem overview | SkillManager/SkillService | Skills context |
| `project-knowledge/REPOSITORY_ECOSYSTEM.md` | Repository overview | Repository ecosystem overview | Ecosystem | Repository context |
| `project-knowledge/FUTURE_RESEARCH.md` | Research | Future research topics | All parts | Future context |
| `project-knowledge/VERSION_HISTORY.md` | History | Version history document | All parts | Version history |

### 1.4 Diagrams

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/diagrams/OVERALL_ARCHITECTURE.md` | Diagram | Overall architecture diagram | All parts | High-level orientation |
| `project-knowledge/diagrams/AI_OS_COMPLETE_ARCHITECTURE.md` | Diagram | Complete architecture diagram | All parts | Complete system map |
| `project-knowledge/diagrams/AGENT_FLOW.md` | Diagram | Agent flow | AI Agency | Agent lifecycle |
| `project-knowledge/diagrams/MCP_FLOW.md` | Diagram | MCP flow | MCP | Integration flow |
| `project-knowledge/diagrams/MEMORY_FLOW.md` | Diagram | Memory flow | Memory | Memory data flow |
| `project-knowledge/diagrams/COUNCIL_FLOW.md` | Diagram | Council flow | Councils | Governance flow |
| `project-knowledge/diagrams/WORKFLOW_FLOW.md` | Diagram | Workflow flow | WorkflowManager | Workflow execution flow |
| `project-knowledge/diagrams/RUNTIME_EXECUTION_FLOW.md` | Diagram | Runtime execution flow | Kernel/initialization | Runtime lifecycle |
| `project-knowledge/diagrams/PART_FLOW.md` | Diagram | Part flow | All parts | Part sequencing |
| `project-knowledge/diagrams/REPOSITORY_MAP.md` | Diagram | Repository map | Repository ecosystem | Ecosystem map |

### 1.5 Prompts

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/prompts/ARCHITECTURE_PROMPTS.md` | Prompts | Architecture authoring prompts | All parts | Authoring guidance |
| `project-knowledge/prompts/CHATGPT_PROMPTS.md` | Prompts | ChatGPT prompts used in architecture creation | All parts | Historical prompts |
| `project-knowledge/prompts/CLAUDE_PROMPTS.md` | Prompts | Claude prompts used in architecture creation | All parts | Historical prompts |
| `project-knowledge/prompts/REVIEW_PROMPTS.md` | Prompts | Review prompts | All parts | Review guidance |

### 1.6 Templates

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/templates/ADR_TEMPLATE.md` | Template | ADR template | ADRs | Standard ADR structure |
| `project-knowledge/templates/PART_TEMPLATE.md` | Template | Part chapter template | All parts | Standard Part structure |
| `project-knowledge/templates/REVIEW_TEMPLATE.md` | Template | Review checklist template | Reviews | Standard review structure |

### 1.7 Meeting Notes / Project Knowledge

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/meeting-notes/PROJECT_LOG.md` | Meeting notes | Project log / notes | All parts | Historical record |

### 1.8 Research Documents

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `project-knowledge/research/FUTURE_FEATURES.md` | Research | Future features research | All parts | Future considerations |
| `project-knowledge/research/GITHUB_REPOSITORIES.md` | Research | GitHub repository research | Repositories | Ecosystem map |
| `project-knowledge/research/PAPERS.md` | Research | Papers/references research | All parts | External references |

### 1.9 JSON Schemas / Shared Data

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `Part09/shared/FeatureFlagSchema.json` | Shared schema | Feature flag schema | Part 9 | Configuration/feature flags |
| `Part09/shared/ConfigManifest.json` | Shared schema | Config manifest | Part 9 | Configuration manifest |
| `Part09/shared/ChangeLog.json` | Shared schema | Changelog schema | Part 9 | Change tracking |
| `Part09/shared/ProvisioningContract.json` | Shared schema | Provisioning contract schema | Part 9 | Provisioning contract |
| `Part09/shared/DeploymentManifest.json` | Shared schema | Deployment manifest | Part 9 | Deployment manifest |
| `Part09/shared/VersionPolicy.json` | Shared schema | Version policy schema | Part 9 | Versioning policy |
| `Part09/shared/LifecyclePolicy.json` | Shared schema | Lifecycle policy | Part 9 | Lifecycle policy |
| `Part09/shared/LifecycleState.json` | Shared schema | Lifecycle state | Part 9 | Lifecycle state |
| `Part09/shared/LifecycleTransition.json` | Shared schema | Lifecycle transition | Part 9 | Lifecycle transitions |
| `Part09/shared/DependencyGraph.json` | Shared schema | Dependency graph | Part 9 | Dependency graph |

### 1.10 Part-Specific Context / Memory Artifacts

| File | Category | Purpose | Architecture Part(s) | Importance |
|------|----------|---------|----------------------|------------|
| `Part08/PART8_CONTEXT.md` | Part context | Part 8 context | Part 8 | Local context |
| `Part09/PART9_CONTEXT.md` | Part context | Part 9 context | Part 9 | Local context |
| `Part10/PART10_CONTEXT.md` | Part context | Part 10 context | Part 10 | Local context |
| `Part11/PART11_CONTEXT.md` | Part context | Part 11 context | Part 11 | Local context |
| `Part09/memory/user_summary.md` | Memory artifact | User summary example | Part 9 | Memory backend example |
| `Part09/memory/feedback_summary_format.md` | Memory artifact | Feedback summary format example | Part 9 | Memory format example |
| `Part09/.claude/memory/final_consistency_review.md` | Review artifact | Consistency review | Part 9 | Review evidence |
| `Part11/CONVERSATION_SUMMARY.md` | Review artifact | Conversation summary for Part 11 | Part 11 | Review evidence |

---

## 2. 15-PART ARCHITECTURE MAP

The authoritative roadmap classification is maintained in `Common/MASTER_ARCHITECTURE_ROADMAP.md` §4.
There is also a conflicting classification in `Common/ARCHITECTURE_SPEC_TOC.md` §15; this conflict is preserved as CONFLICT-P15-01/03 in Part 15 README.

| Part | Title | Purpose | Major Concepts | Components Defined | Important Interfaces / Contracts | Dependencies on Other Parts | Related Supporting Documents | Diagrams / ADRs |
|------|-------|---------|----------------|--------------------|-------------------------------|---------------------------|-------------------------------|-----------------|
| Part 0 | Front Matter | Defines scope, terminology, principles, conformance levels, extension points, ADR process; frozen source of truth | Event-first communication, kernel as pure orchestrator, capability manager ownership, immutable events, configuration declarative/layered | HermesKernel concept, Core Components (4), Capability Managers (9), Engineering Services (8), Capability Facade Services (4) | Event base contract, EventType enum, EventBus interface, BaseService contract, Global Singleton Accessor pattern, StateScope enum, MemoryType enum, ConsensusAlgorithm enum | None foundational; all later Parts must conform to Part 0 | `MASTER_ARCHITECTURE_ROADMAP.md`, `ARCHITECTURE_SPEC_TOC.md`, `AI_OS_MASTER_CONTEXT.md` | ADR process in §0.5.3 |
| Part 1 | Core Foundation Layer | Fundamental building blocks: kernel structure, component taxonomy, data flow overview, deployment topology, version/compatibility matrix | Kernel layer, platform layer, application layer, extension points | HermesKernel, Core Components, Core Managers, Engineering Services, Facade Services | Kernel config schema, event flow overview, component taxonomy, deployment topology, compatibility matrix | None | `AI_OS_MASTER_CONTEXT.md` (layered architecture) | Orientation diagram in Part 0 §0.7 |
| Part 2 | Communication & Integration Layer | Event system specification: base contract, EventType catalog, EventBus, subscriptions, correlation/causation, versioning, handler decorators | Event substrate, correlation/causation, schema evolution, sync/async handlers | Event base, EventType enum, EventBus, Subscription, handler decorators | EventBus interface (`subscribe`, `unsubscribe`, `publish`, `publish_async`, `get_history`, `get_stats`, `shutdown`) | Part 1 | `MASTER_ARCHITECTURE_ROADMAP.md` shared schemas | Schema registry TBD |
| Part 3 | Hermes Kernel Specification | Kernel lifecycle, singleton registry, ServiceRegistry, service registration, kernel stats, kernel management API | Kernel phases, global singletons, topological start/stop | HermesKernel, ServiceRegistry | `KernelConfig`, `run_kernel()`, `stop_kernel()`, `get_kernel()`, `execute_with_kernel()` | Part 1, Part 2 | Part 15 `runtime-map.md` (EMPTY), Part 14 integration docs | Initialization phase diagram in Part 14 README |
| Part 4 | Security & Governance Layer / Core Managers | Defines Core Managers and security controls: State, Workflow, Checkpoint, Retry, RCA, Memory, Skill, MCP, Council, AIAgency, ModelRouter, ResourceManager | State scopes, workflow DAG, retry budgets, failure categories, memory tiers, skill sandboxing, council consensus, model routing, resource quotas | StateManager, WorkflowManager, CheckpointManager, RetryManager, RootCauseAnalyzer, MemoryManager, SkillManager, MCPManager, CouncilManager, AIAgencyService, ModelRouter, ResourceManager | `StateScope` enum, `WorkflowDefinition`/`WorkflowStep` schema, `Checkpoint` schema, `RetryPolicy`/`RetryBudget`, `FailureCategory`/`FailureSeverity`/`RecoveryAction`, `MemoryType` enum, `Skill` schema, `MCPTransport` enum, `CouncilRole`/`ConsensusAlgorithm`, 9 agent specs, `ResourceType` enum | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6 | Part 14 interfaces, Part 12 events/components, Part 13 governance-events | Event schemas for each manager |
| Part 5 | Operational & Observability Layer | Monitoring, logging, alerting, operational management: structured logging, metrics, tracing, health checks | Metrics, tracing, health probes, log levels/formats | Observability abstractions: StructuredLogger, MetricSchema, health check system | `/health` endpoint spec, Prometheus exposition format, OpenTelemetry integration | Part 1, Part 2, Part 3 | Part 9 shared schemas (`MetricSchema`) | Part 9 README chapter map |
| Part 6 | Infrastructure Abstraction Layer | Infrastructure/cloud resource interfaces: MCP manager and service patterns, capability facade services | Infrastructure abstraction, MCP transports, facade pattern | MCPService, SkillService, CouncilService, MemoryService | `MCPTransport` contract, `SkillInvocationSchema`, service facade contracts | Part 1, Part 2, Part 3, Part 4, Part 5, Part 6, Part 7 | Part 14 external integration chapters | MCP flow diagram |
| Part 7 | AI Core Services Layer | Foundational AI capabilities: model serving/training orchestration, model routing logic | Model routing, capability-based routing, fallback chains | ModelRouter | `ModelRouter` capability registry, capability-based routing interface | Part 1, Part 2, Part 3, Part 5, Part 6 | Part 14 model/provider integration | NOT SPECIFIED |
| Part 8 | Agent & Skill Management Layer | AI agent framework: lifecycle management, skill integration, discovery, execution, task execution | Agent lifecycle, skill registry, discovery protocol, sandboxing | SkillService, CouncilService, MCPService, MemoryService | `Skill` interface, `SkillInvocationSchema`, council service contract, `AgentTaskSchema` | Part 1, Part 2, Part 7 | Part 14 plugin/extension architecture, Part 9 events | Agent flow diagram |
| Part 9 | Learning Layer Architecture | Continuous learning, adaptation, knowledge acquisition: reinforcement loops, knowledge acquisition | Memory backend ABC, consolidation pipeline, TTL, query API | MemoryManager, MemoryService | `MemoryBackend` ABC, `InMemoryBackend`, `FileMemoryBackend`, `MemoryType` enum | Part 3, Part 7, Part 8 | Part 14 storage/data integration, Part 09 shared JSON schemas | Memory flow diagram |
| Part 10 | AI Runtime Architecture | Execution environment and runtime orchestration: scheduling, execution isolation, process lifecycle | Runtime scheduling, execution isolation, process lifecycle | Runtime layer | Runtime conformance contracts | Part 1, Part 8 | Part 15 `runtime-map.md` (EMPTY) | Runtime execution flow diagram |
| Part 11 | Agent & Cognitive Architecture | Cognitive models, memory hierarchies, reasoning processes for agents | Cognitive state persistence, reasoning models | Cognitive/agent reasoning layer | Memory/context contracts, cognitive state interfaces | Part 8, Part 9 | Part 11 context | NOT SPECIFIED |
| Part 12 | Multi-Agent Collaboration Architecture | Coordination, negotiation, conflict resolution: agent discovery, delegation, workflow orchestration, council decisions, shared context, multi-agent communication, resource coordination, reliability/recovery/performance, security | Collaboration Manager, Delegation Manager, Workflow Manager, shared context, agent communication primitives, resource coordination policies | Collaboration components (Collaboration Manager, Delegation Manager, Workflow Manager) | events (`TaskDelegated`, `WorkflowStarted`, `ContextUpdated`, etc.), schemas, interface contracts | Parts 1, 2, 4, 5, 8, 9, 10, 11 | Part 12 docs: `README.md`, `context.md`, `components.md`, `events.md`, `schemas.md`, `dependency-map.md`, `review-checklist.md` | Component interaction, data flow, state transition, sequence, dependency matrix diagrams |
| Part 13 | Governance Architecture | Operational governance: policy architecture, decision authority/delegation, governance councils/committees, risk/compliance, agent/capability governance, workflow/execution governance, data/knowledge governance, security/trust governance, auditability/accountability, invariants/conformance | Policy lifecycle, authority delegation, risk assessment, compliance monitoring, audit trails, governance invariants | Policy Manager, Authority Delegator, Council Secretariat, Risk Assessor, Compliance Monitor, Audit Logger | governance events (`PolicyCreated`, `AuthorityDelegated`, `RiskIdentified`, `ComplianceViolation`, `AuditLogGenerated`, etc.), policy schemas, authority delegation contracts | Parts 1–12 | Part 13 docs: `README.md`, `context.md`, `components.md`, `governance-events.md`, `policies.md`, `schemas.md`, `dependency-map.md`, `review-checklist.md` | Governance lifecycle, domain map diagrams |
| Part 14 | Integration Architecture | How Parts 0–13 compose: contracts, communication patterns, dependency ordering, extension rules, failure propagation, observability boundaries | Integration status taxonomy, layered composition, explicit contract visibility, failure transparency, future AI agent integration rules | Integration contracts across all layers | EventBus integration, global singleton accessor boundaries, ServiceRegistry topology, facade bridge contracts, extension point boundaries | Parts 0–13 | Part 14 docs: `README.md`, `context.md`, `components.md`, `events.md`, `schemas.md`, `dependency-map.md`, `interfaces.md`, `integrations.md`, `adrs.md`, `review-checklist.md` | Initialization phase/shutdown diagram, domain chapters diagram sets |
| Part 15 | Architecture Evolution & Extensibility | Implementation-facing mapping from architecture to implementation; extension points catalog; implementation gaps; deployment/observability/configuration mapping; conformance/review mechanisms | Implementation constraints, extension points registry, gap registry, architecture-to-implementation contracts | Extension points registry, component registry, deployment/observability/configuration architecture | Implementation contracts, deployment architecture, observability mapping, testing contracts | Parts 0–14 | Part 15 docs: `README.md`, `glossary.md`, `adrs.md`, `components.md`, `configuration.md`, `deployment.md`, `dependency-map.md`, `implementation-contracts.md`, `observability.md`, `review-checklist.md`, `runtime-map.md` (EMPTY), `testing.md` (EMPTY), `context.md` (EMPTY), chapters `15.1`–`15.13` (mostly EMPTY) | NOT SPECIFIED; Part 15 Final Gate is NOT READY |

---

## 3. COMPLETE SYSTEM HIERARCHY

The hierarchy below is synthesized from `AI_OS_MASTER_CONTEXT.md`, Part 0 §0.7, `Common/MASTER_ARCHITECTURE_ROADMAP.md` §4, and the READMEs for Parts 12–15.
It uses the actual component names defined by the architecture; no missing components are invented.

```
AI-OS Platform
|
|-- Hermes Kernel (orchestration core)
|   |-- Core Components (4)
|   |   |-- EventBus
|   |   |-- StateManager
|   |   |-- WorkflowManager
|   |   |-- ResourceManager
|   |
|   |-- Core Managers (9) — kernel-owned, exposed via global singleton accessors
|       |-- RetryManager
|       |-- CheckpointManager
|       |-- RootCauseAnalyzer
|       |-- MemoryManager
|       |-- SkillManager
|       |-- MCPManager
|       |-- CouncilManager
|       |-- AIAgencyService
|       |-- ModelRouter
|
|-- Engineering Services (8) — event-driven SDLC phase services
|   |-- PlanningService
|   |-- CodingService
|   |-- ReviewService
|   |-- TestingService
|   |-- DeploymentService
|   |-- OperationsService
|   |-- LearningService
|   |-- MemoryService (facade)
|
|-- Capability Facade Services (4) — thin event↔manager bridges
|   |-- SkillService
|   |-- CouncilService
|   |-- MCPService
|   |-- MemoryService
|
|-- AI Agency
|   |-- Agent lifecycle management
|   |-- 9 specified agents:
|   |   SecurityAgent, PerformanceAgent, ChaosAgent, AccessibilityAgent,
|   |   DocumentationAgent, ConcurrencyAgent, BugHunterAgent, ArchitectureAgent, FinalJudge
|   |-- Permission sandboxing
|   |-- Audit event pairs (*Requested / *Completed)
|
|-- Councils
|   |-- CouncilManager
|   |-- Council types: Claude Council, LLM Council, specialized councils
|   |-- Consensus algorithms: MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT
|   |-- Dissent escalation to human judges (FinalJudge)
|
|-- Memory
|   |-- MemoryManager
|   |-- Memory tiers:
|       |-- Working Memory
|       |-- Claude Memory
|       |-- Engineering Intelligence
|       |-- Obsidian
|       |-- Graphify
|   |-- MemoryBackend ABC
|   |-- InMemoryBackend, FileMemoryBackend
|
|-- MCP (Model Context Protocol)
|   |-- MCPManager
|   |-- MCPService
|   |-- MCP transports (4): stdio, HTTP, WebSocket, plus extensions
|   |-- Tool registry, call timeout/retries, capability negotiation, security profiles
|
|-- Skills
|   |-- SkillManager
|   |-- SkillService
|   |-- Discovery protocol
|   |-- Built-in skills (4)
|   |-- Marketplace extension point
|   |-- Execution sandboxing
|
|-- Observability
|   |-- Structured logging
|   |-- Metrics
|   |-- Tracing / correlation IDs
|   |-- Health checks
|
|-- Recovery
|   |-- RetryManager / RetryPolicy / RetryBudget
|   |-- CheckpointManager / Checkpoint schema
|   |-- RootCauseAnalyzer / FailureCategory / RecoveryAction
|
|-- Governance
|   |-- Policy architecture
|   |-- Decision authority / delegation
|   |-- Governance councils / committees
|   |-- Risk and compliance governance
|   |-- Agent and capability governance
|   |-- Workflow and execution governance
|   |-- Data and knowledge governance
|   |-- Security and trust governance
|   |-- Auditability and accountability
|   |-- Governance invariants and conformance
|
|-- Extensions
|   |-- Custom Event Types
|   |-- Custom Memory Backends
|   |-- Custom Skills
|   |-- Custom MCP Transports
|   |-- Custom Consensus Algorithms
|   |-- Custom AI Agency Agents
|   |-- Custom Model Providers
|   |-- Custom Resource Types
|
|-- External Ecosystem
    |-- External system integration boundaries
    |-- Model/provider integration boundaries
    |-- Storage/data integration boundaries
    |-- Deployment/infrastructure integration boundaries
```

---

## 4. COMPONENT → FILE INDEX

This section maps each major component to its primary specification location(s).
Where multiple docs cover the same component, the authoritative source is listed first.

### 4.1 Kernel Components

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| HermesKernel | Part 0 §0.3, Part 3 | Part 1, Part 14 | Runtime execution flow | NOT SPECIFIED | Part 14 README §Conformance; Part 15 `runtime-map.md` (EMPTY) |
| EventBus | Part 2 | Part 0 §0.3, Part 3, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 12 events.md; Part 14 events.md |
| StateManager | Part 4 | Part 0 §0.3, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 12 components.md; Part 14 interfaces.md |
| WorkflowManager | Part 4 | Part 12, Part 14 | Workflow flow diagram | NOT SPECIFIED | Part 12 dependency-map.md; Part 14 interfaces.md |
| ResourceManager | Part 4 / Part 13 | Part 0 §0.3, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 13 components.md; Part 14 interfaces.md |

### 4.2 Core Managers

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| RetryManager | Part 4 | Part 0 §0.3, Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Retry Budget semantics |
| CheckpointManager | Part 4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Checkpoint disk format |
| RootCauseAnalyzer | Part 4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §RCA keyword lists |
| MemoryManager | Part 4 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tier backends |
| SkillManager | Part 4 / Part 8 | Part 7, Part 9, Part 10, Part 11, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Skill interface |
| MCPManager | Part 4 / Part 6 | Part 7, Part 13, Part 14 | MCP flow diagram | NOT SPECIFIED | Part 14 README §MCPTransport contract |
| CouncilManager | Part 4 / Part 12 | Part 8, Part 11, Part 14 | Council flow diagram | NOT SPECIFIED | Part 14 README §ConsensusAlgorithm enum |
| AIAgencyService | Part 4 / Part 8 | Part 7, Part 9, Part 10, Part 11, Part 12, Part 14 | Agent flow diagram | NOT SPECIFIED | Part 14 README §Agent audit event pairs |
| ModelRouter | Part 4 / Part 7 | Part 8, Part 9, Part 10, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §ModelRouter capability registry |

### 4.3 Services

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| BaseService | Part 5 | Part 14 README §Service Framework | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Service lifecycle contract |
| ServiceRegistry | Part 3 / Part 5 | Part 14 README §ServiceRegistry topology | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §ServiceRegistry topology |
| PlanningService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| CodingService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| ReviewService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| TestingService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| DeploymentService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| OperationsService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| LearningService | Part 6 | Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 events.md |
| MemoryService (facade) | Part 6 / Part 8 | Part 9, Part 14 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Facade bridge contracts |
| SkillService | Part 6 / Part 8 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Facade bridge contracts |
| CouncilService | Part 6 / Part 8 | Part 12, Part 14 | Council flow diagram | NOT SPECIFIED | Part 14 README §Facade bridge contracts |
| MCPService | Part 6 / Part 8 | Part 13, Part 14 | MCP flow diagram | NOT SPECIFIED | Part 14 README §Facade bridge contracts |

### 4.4 AI Agency

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| AIAgencyService | Part 4.10 | Part 8, Part 12, Part 14 | Agent flow diagram | NOT SPECIFIED | Part 14 README §Agent lifecycle |
| 9 Agent specs | Part 4.10 | Part 8 | Agent flow diagram | NOT SPECIFIED | Part 14 README §Agent audit pairs |

### 4.5 Councils

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| CouncilManager | Part 4.9 / Part 12 / Part 13 | Part 8, Part 14 | Council flow diagram | NOT SPECIFIED | Part 14 README §Council consensus |
| Claude Council | Part 4.9 / Part 12 | Part 8 | Council flow diagram | NOT SPECIFIED | Part 14 README §Council types |
| LLM Council | Part 4.9 / Part 12 | Part 8 | Council flow diagram | NOT SPECIFIED | Part 14 README §Council types |
| Governance councils | Part 13 | Part 12 | NOT SPECIFIED | NOT SPECIFIED | Part 13 governance-events.md |

### 4.6 Memory Layers

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| Working Memory | Part 4.6 / Part 9 | Part 8, Part 10, Part 11 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tiers |
| Claude Memory | Part 4.6 / Part 9 | Part 8, Part 10, Part 11 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tiers |
| Engineering Intelligence | Part 4.6 / Part 9 | Part 8, Part 10, Part 11 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tiers |
| Obsidian | Part 4.6 / Part 9 | Part 8, Part 10, Part 11 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tiers |
| Graphify | Part 4.6 / Part 9 | Part 8, Part 10, Part 11 | Memory flow diagram | NOT SPECIFIED | Part 14 README §Memory tiers |
| MemoryBackend ABC | Part 4.6 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 0 §0.5.2 extension point |

### 4.7 MCP Ecosystem

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| MCPManager | Part 4.8 / Part 6 | Part 7, Part 13, Part 14 | MCP flow diagram | NOT SPECIFIED | Part 14 README §MCPTransport contract |
| MCP transports | Part 4.8 / Part 6 | Part 14 | MCP flow diagram | NOT SPECIFIED | Part 14 README §Transport extensions |
| MCP tool registry | Part 4.8 | Part 6, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Tool registry |
| MCP capability negotiation | Part 14 | Part 6, Part 13 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Capability negotiation |
| MCP security profiles | Part 14 | Part 4, Part 13 | NOT SPECIFIED | NOT SPECIFIED | Part 14 14.10-Integration-Security.md |

### 4.8 Skills Ecosystem

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| SkillManager | Part 4.7 / Part 8 | Part 7, Part 9, Part 10, Part 11, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Skill interface |
| Skill schema | Part 4.7 | Part 6, Part 8 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Skill schema |
| Skill discovery | Part 4.7 / Part 8 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Discovery protocol |
| Skill sandboxing | Part 4.7 / Part 8 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Sandboxing |
| Skill composition | Part 8 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Skill composition |

### 4.9 Observability

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| Structured logging | Part 5 / Part 9 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 9 README chapter map |
| Metrics | Part 5 / Part 9 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 9 shared schemas |
| Tracing | Part 5 / Part 9 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 observability integration |
| Health checks | Part 5 / Part 9 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 observability integration |

### 4.10 Recovery

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| Retry budget semantics | Part 4.4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Retry Budget semantics |
| Checkpoint disk format / restore semantics | Part 4.3 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Checkpoint disk format |
| Failure classification / RCA routing | Part 4.5 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §RCA keyword lists |

### 4.11 Governance

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| Policy Manager | Part 13 | Part 4, Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |
| Authority Delegator | Part 13 | Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |
| Council Secretariat | Part 13 | Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |
| Risk Assessor | Part 13 | Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |
| Compliance Monitor | Part 13 | Part 4, Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |
| Audit Logger | Part 13 | Part 4, Part 5, Part 12, Part 14 | NOT SPECIFIED | Part 13 adrs.md | Part 13 review-checklist.md |

### 4.12 Extensions

| Component | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-----------|---------------|--------------------|---------|-----|------------|
| Custom Event Types | Part 0 §0.5.2 | Part 2, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Events |
| Custom Memory Backend | Part 0 §0.5.2 | Part 4.6, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Memory Backend |
| Custom Skill | Part 0 §0.5.2 | Part 4.7, Part 8, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Skills |
| Custom MCP Transport | Part 0 §0.5.2 | Part 4.8, Part 6, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom MCP Transport |
| Custom Consensus Algorithm | Part 0 §0.5.2 | Part 4.9, Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Consensus Algorithm |
| Custom AI Agency Agent | Part 0 §0.5.2 | Part 4.10, Part 8, Part 12, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom AI Agency Agent |
| Custom Model Provider | Part 0 §0.5.2 | Part 4.11, Part 7, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Model Provider |
| Custom Resource Type | Part 0 §0.5.2 | Part 4.12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README §Custom Resource Type |

---

## 5. ARCHITECTURAL DEPENDENCY MAP

Dependency ordering is taken from `Common/MASTER_ARCHITECTURE_ROADMAP.md` §3 and Part 14 README.
Only relationships explicitly supported by documentation are shown; others are marked INFERRED or NOT SPECIFIED.

```
Part 0 — Front Matter (foundation)
    |
    +-- Part 1 — Core Foundation Layer
    |       |
    |       +-- Part 2 — Communication & Integration Layer (Event System)
    |       |       |
    |       |       +-- Part 5 — Operational & Observability Layer
    |       |       |
    |       |       +-- Part 6 — Infrastructure Abstraction Layer
    |       |       |       |
    |       |       |       +-- Part 7 — AI Core Services Layer
    |       |       |
    |       |       +-- Part 8 — Agent & Skill Management Layer
    |       |       |       |
    |       |       |       +-- Part 10 — AI Runtime Architecture (INFERRED)
    |       |       |       |
    |       |       |       +-- Part 11 — Agent & Cognitive Architecture
    |       |       |
    |       |       +-- Part 14 — Integration Architecture
    |       |
    |       +-- Part 3 — Hermes Kernel Specification
    |       |       |
    |       |       +-- Part 4 — Security & Governance Layer / Core Managers
    |       |               |
    |       |               +-- Part 9 — Learning Layer Architecture
    |       |               |
    |       |               +-- Part 12 — Multi-Agent Collaboration Architecture
    |       |               |
    |       |               +-- Part 13 — Governance Architecture
    |       |                       |
    |       |                       +-- Part 14 — Integration Architecture
    |       |
    |       +-- Part 4 — Core Managers (kernel-owned)
    |       |       |
    |       |       +-- Part 5 — Operational & Observability Layer
    |       |
    |       +-- Part 5 — Operational & Observability Layer
    |       |
    |       +-- Part 6 — Capability Facade Services / Infrastructure Abstraction
    |
    +-- Part 7 — AI Core Services Layer
    |       |
    |       +-- Part 9 — Learning Layer Architecture
    |
    +-- Part 8 — Agent & Skill Management Layer
    |       |
    |       +-- Part 10 — AI Runtime Architecture (INFERRED)
    |       |
    |       +-- Part 11 — Agent & Cognitive Architecture
    |       |
    |       +-- Part 12 — Multi-Agent Collaboration Architecture
    |
    +-- Part 12 — Multi-Agent Collaboration Architecture
    |       |
    |       +-- Part 13 — Governance Architecture
    |
    +-- Part 13 — Governance Architecture
    |       |
    |       +-- Part 14 — Integration Architecture
    |       |
    |       +-- Part 15 — Architecture Evolution & Extensibility
    |
    +-- Part 14 — Integration Architecture
    |       |
    |       +-- Part 15 — Architecture Evolution & Extensibility
    |
    +-- Part 15 — Architecture Evolution & Extensibility
```

### 5.1 Dependency categories

| Category | Summary | Supported by documentation? |
|----------|---------|-----------------------------|
| Initialization dependencies | Phases 0–8 documented in Part 14 README and Part 3/Part 4 | YES |
| Runtime dependencies | EventBus pub/sub; ServiceRegistry topology; global singleton accessors | YES |
| Communication dependencies | Event-first post-initialization; no direct service-to-service calls | YES |
| Service dependencies | `depends_on` DAG in ServiceRegistry; Engineering Services depend on Core Components/Managers | YES |
| Manager dependencies | Kernel owns managers; services access via global singletons | YES |
| Governance dependencies | Part 13 governs Parts 1–12; Parts 14–15 extend governance | YES |
| External dependencies | MCP transports, model providers, storage systems, deployment infrastructure | PARTIALLY documented in Part 14 external-system/model/storage/deployment chapters |
| Infrastructure dependencies | ResourceManager quotas, MCPManager transports, deployment environment | PARTIALLY documented in Part 13/Part 14 |
| Configuration dependencies | Four-layer merge; immutable after INITIALIZING | YES |

---

## 6. COMMUNICATION ARCHITECTURE

### 6.1 Internal AI-OS Communication

All inter-component communication post-initialization occurs through the **EventBus**.
The architecture explicitly prohibits commands and queries in v1.0; there are no direct service-to-service calls, no synchronous RPC, and no shared mutable state outside `StateManager`.

| Mechanism | Owner | Primary Source |
|-----------|-------|---------------|
| EventBus pub/sub | Part 2 | `ARCHITECTURE_SPEC_PART2.md` |
| Correlation ID / Causation ID | Part 2 | Part 0 §0.3.2 |
| Global singleton accessors (get/set) | Part 3 | `ARCHITECTURE_SPEC_PART3.md` |
| ServiceRegistry topological start/stop | Part 3 / Part 5 | `ARCHITECTURE_SPEC_PART3.md`, `ARCHITECTURE_SPEC_PART5.md` |
| Capability Facade Services (thin event↔manager bridges) | Part 6 | `ARCHITECTURE_SPEC_PART6_*.md` |
| StateManager scoped state | Part 4 | `ARCHITECTURE_SPEC_PART4.md` / `PART4A.md` |
| Failure events | Part 4 / Part 0 | Part 4 RootCauseAnalyzer; Part 0 Principle 9 |

### 6.2 External Integration Communication

External integration is documented in Part 14 and is intentionally limited to boundary contracts:

| Boundary | Primary Source | Chapter |
|----------|---------------|---------|
| External-system integration | Part 14 | `14.5-External-System-Integration.md` |
| Model/provider integration | Part 14 | `14.6-Model-and-Provider-Integration.md` |
| Storage/data integration | Part 14 | `14.7-Storage-and-Data-Integration.md` |
| Deployment/infrastructure integration | Part 14 | `14.9-Deployment-and-Infrastructure-Integration.md` |
| Observability/operations integration | Part 14 | `14.8-Observability-and-Operations-Integration.md` |
| Integration security | Part 14 | `14.10-Integration-Security.md` |

Exact protocol bindings, concrete transports, and third-party API specifics are intentionally UNSPECIFIED in the architecture docs reviewed.

---

## 7. DATA / MEMORY ARCHITECTURE

### 7.1 Memory Layers

| Layer | Primary Source | Related Sources | Storage Notes |
|-------|---------------|-----------------|---------------|
| Working Memory | Part 4.6 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Short-term, session-scoped, volatile |
| Claude Memory | Part 4.6 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Session persistence across restarts |
| Engineering Intelligence | Part 4.6 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Long-term learnings/patterns/decisions |
| Obsidian | Part 4.6 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Knowledge vault / documentation integration |
| Graphify | Part 4.6 / Part 9 | Part 8, Part 10, Part 11, Part 14 | Knowledge graph for entity relationships |

### 7.2 Memory Backends and Relationships

| Concept | Primary Source | Notes |
|---------|---------------|-------|
| MemoryBackend ABC | Part 4.6 | Extension point per Part 0 §0.5.2 |
| InMemoryBackend | Part 4.6 | Built-in backend |
| FileMemoryBackend | Part 4.6 | Built-in backend |
| MemoryManager | Part 4.6 | Central owner; five MemoryType tiers |
| MemoryService (facade) | Part 6 / Part 8 | Event-driven facade over MemoryManager |
| Consolidation pipeline | Part 4.6 | Consolidation from lower to higher memory tiers |
| TTL / retention | Part 4.6 | Tier-specific TTL/retention implied by tier semantics |
| Query API | Part 4.6 | Memory access patterns |
| Obsidian integration | Part 4.6 | Knowledge vault integration; concrete integration details UNSPECIFIED |
| Graphify integration | Part 4.6 | Knowledge graph reasoning; concrete graph backend UNSPECIFIED |

### 7.3 Other Data Stores

| Store / Concern | Primary Source | Notes |
|-----------------|---------------|-------|
| StateManager | Part 4.1 | Scoped state: WORKFLOW / SERVICE / GLOBAL / SESSION |
| CheckpointManager persistence | Part 4.3 | Disk format JSON; retention/pruning policy |
| Configuration system | Part 7 | Four-layer merge; immutable after INITIALIZING |
| Observability stores | Part 5 / Part 9 | Metrics, tracing, structured logs |
| Governance data | Part 13 | Policy records, audit records, risk assessments |

---

## 8. AI AGENCY + COUNCILS

### 8.1 AIAgencyService

| Aspect | Primary Source | Notes |
|--------|---------------|-------|
| Agent lifecycle | Part 4.10 / Part 8 | Spawn, monitor, terminate |
| Autonomy levels | Part 8 / Part 14 | Supervised, guided, autonomous |
| Permission sandboxing | Part 4.10 / Part 8 | Restricted execution environments |
| Resource quotas | Part 4.10 / Part 8 | CPU, memory, tokens, concurrency limits |
| Audit trails | Part 4.10 / Part 8 | Comprehensive logging of agent actions |
| Performance monitoring | Part 4.10 / Part 8 | Utilization, success rates, behavioral analytics |
| 9 specified agents | Part 4.10 | Security, Performance, Chaos, Accessibility, Documentation, Concurrency, BugHunter, Architecture, FinalJudge |

### 8.2 Councils

| Aspect | Primary Source | Notes |
|--------|---------------|-------|
| CouncilManager | Part 4.9 / Part 12 / Part 13 | Consensus mechanisms |
| Council types | Part 4.9 / Part 12 / Part 13 | Claude Council, LLM Council, specialized councils |
| Consensus algorithms | Part 4.9 | MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT |
| Dissent escalation | Part 4.9 / Part 12 / Part 13 | Escalation to human judges (FinalJudge) |
| Voting / quorum | Part 12 | Part 12 council decision architecture |
| Governance councils | Part 13 | Ethics Council, Risk Committee, Compliance Board, etc. |

### 8.3 Governance of Agency/Councils

| Aspect | Primary Source | Notes |
|--------|---------------|-------|
| Agent/capability governance | Part 13 | Regulation of agent lifecycle and behaviors |
| Agent behavior constraints | Part 13 | Capability certification and usage governance |
| Council governance bodies | Part 13 | Oversight, advisory functions |
| Human oversight / FinalJudge | Part 0 / Part 12 / Part 13 | Veto and override rights |

---

## 9. MCP + SKILLS ECOSYSTEM

### 9.1 MCP Ecosystem

| Topic | Primary Source | Notes |
|-------|---------------|-------|
| MCP architecture | Part 4.8 / Part 6 | Manager and service roles |
| MCP lifecycle | Part 4.8 | Connection lifecycle, tool registry |
| Discovery | Part 4.7 / Part 8 | Skill/MCP server discovery protocols |
| Security | Part 4.8 / Part 14 | Authentication, authorization, audit logging of MCP interactions |
| Capability negotiation | Part 14 | Part 14 model/provider integration |
| MCP servers / integrations | Part 4.8 / Part 14 | Server config schema, tool allowlists |
| Transports | Part 4.8 / Part 6 / Part 14 | stdio, HTTP, WebSocket, extension mechanism |

### 9.2 Skills Ecosystem

| Topic | Primary Source | Notes |
|-------|---------------|-------|
| Discovery | Part 4.7 / Part 8 | Central registry with metadata, tags, compatibility |
| Loading | Part 4.7 / Part 8 | Manifest, registration via SkillManager |
| Versioning | Part 8 | Semantic versioning with dependency resolution |
| Sandboxing | Part 4.7 / Part 8 / Part 12 | Isolation model; permission profiles |
| Governance | Part 8 / Part 13 | Community curation, quality gates, deprecation policies |
| Composition | Part 8 | Chaining, parallel execution, conditional workflows |
| External skill ecosystems | Part 8 | Marketplace extension point; external registries |
| Development kit | Part 8 | Templates, testing frameworks, packaging utilities |

---

## 10. REPOSITORY ECOSYSTEM

The repository ecosystem is documented at a conceptual level in `project-knowledge/REPOSITORY_ECOSYSTEM.md`, `project-knowledge/AI_OS_MASTER_CONTEXT.md` §Repository Ecosystem, and `Common/MASTER_ARCHITECTURE_ROADMAP.md`.
No explicit repository names are introduced in the reviewed architecture docs; the architecture specifies categories and roles rather than concrete repositories.

| Category | Role | Core or External | Related Architecture Components |
|----------|------|------------------|--------------------------------|
| Core Architecture | Specifies layers, components, managers, services | Core | All Parts |
| Core Implementation | Reference runtime demonstrating specification compliance | Core | Hermes Kernel, all managers, all services |
| AI Agency | Agent lifecycle, councils, judging/consensus | Core | AIAgencyService, CouncilManager |
| Reference Implementations | Canonical implementation patterns | Core | Parts 10–12 |
| External Integrations | Model providers, storage systems, deployment infrastructure | External | ModelRouter, MCPManager, StorageManager, Part 14 external chapters |
| MCP Integrations | MCP servers and transports | External / Ecosystem | MCPManager, MCPService |
| Skills | Reusable capabilities | Ecosystem | SkillManager, SkillService |
| Development Tools | Linting, typing, testing, pre-commit | External tooling | Part 0 §0.2.2 out-of-scope notes |
| Evaluation Tools | Conformance tests, integration tests, benchmarks | External tooling | Part 11 testing strategy; Part 12/13/14 review checklists |

---

## 11. ARCHITECTURE DECISIONS

### 11.1 ADR locations

| Location | Notes |
|----------|-------|
| `Part12/adrs.md` | Part 12 ADR index |
| `Part13/adrs.md` | Part 13 ADR index |
| `Part14/adrs.md` | Part 14 ADR index |
| `Part15/adrs.md` | Part 15 ADR index |
| `project-knowledge/ARCHITECTURE_DECISIONS.md` | Foundational architectural decisions |
| Part 0 §0.5.3 | ADR process definition |

### 11.2 Categorized ADR summary

| Category | Summarized ADR topics |
|----------|----------------------|
| Foundation ADRs | EventBus design, configuration management, runtime environment isolation |
| Communication ADRs | Async messaging patterns, service-to-service protocols, API contracts |
| Data ADRs | State persistence patterns, knowledge graph structures |
| Security ADRs | Identity and access strategy, zero-trust implementation, audit requirements |
| Observability ADRs | Distributed tracing, logging standards, telemetry aggregation |
| Agent/Cognitive ADRs | Agent lifecycle, memory hierarchy, collaboration/council protocols |
| Governance ADRs | Conformance validation, architecture evolution, versioning |
| Integration ADRs | Integration-specific decisions recorded in Part 14 |

### 11.3 Documented ADR status taxonomy (Part 14)

| Status | Meaning |
|--------|---------|
| EXISTING | Directly present in source Part 0–13 |
| DERIVED | Logically implied; inference path shown |
| ASSUMPTION | Adopted for continuity; flagged for review |
| UNSPECIFIED | Source Parts silent |
| GAP | Partially defined; fields unspecified |
| PROPOSED | Recommendation to resolve a GAP/UNSPECIFIED |
| FUTURE | Explicitly deferred |
| CONFLICT | Sources contradict; must be escalated |

### 11.4 Selected known conflicts / gaps

| ID | Type | Summary | Sources |
|-----|------|---------|---------|
| CONFLICT-P15-01 | CONFLICT | Part 15 classification divergence: roadmap vs TOC appendix model | `MASTER_ARCHITECTURE_ROADMAP.md` §4 vs `ARCHITECTURE_SPEC_TOC.md` §15 |
| CONFLICT-P15-03 | CONFLICT | ROADMAP chapter model vs TOC appendix model for Part 15 content | Same as above |
| GAP-P15-03 | GAP | `context.md` is empty | Part 15 `context.md` |
| GAP-P15-04 | GAP | All 13 chapter documents (15.1–15.13) are empty | Part 15 chapter files |
| GAP-P15-05 | GAP | `runtime-map.md` is empty | Part 15 `runtime-map.md` |
| GAP-P15-06 | GAP | `testing.md` is empty | Part 15 `testing.md` |
| IMP-GAP-01..11 | GAP | Implementation gaps in Event base, EventBus, Kernel, RetryManager, CheckpointManager, RCA, Logger, ServiceInfo, Subscriptions | `Common/ARCHITECTURAL_INVENTORY.md` §10–11; `ARCHITECTURE_SPEC_TOC.md` §16 |

---

## 12. VALIDATION + CONFORMANCE

### 12.1 Global Architecture Principles

Defined in `Common/MASTER_ARCHITECTURE_ROADMAP.md` §7 and Part 0 §0.4.

| Principle | Binding |
|-----------|---------|
| Event-Driven Architecture (EDA) | MUST |
| Loose Coupling | MUST |
| Single Responsibility Principle (SRP) | MUST |
| Security by Design | MUST |
| Zero Trust | MUST |
| Fail Safe | MUST |
| Defense in Depth | MUST |
| Observability | MUST |
| Scalability | SHOULD |
| Reliability | MUST |
| Extensibility | SHOULD |
| Technology Neutrality | MUST |
| Vendor Neutrality | MUST |
| Implementation Independence | MUST |

### 12.2 Global Runtime Invariants

Defined in `Common/MASTER_ARCHITECTURE_ROADMAP.md` §8.

| Invariant | Meaning |
|-----------|---------|
| Data Consistency | All persistent data maintains eventual consistency |
| Secure Communication | All inter-component traffic is encrypted (TLS/mTLS) |
| Authenticated Access | All interfaces require validated identity |
| Authorized Operations | All actions undergo Policy Engine verification |
| Eventual State Convergence | Distributed state guarantees eventual consistency |
| No Single Point of Failure | Redundant deployment for critical services |
| Resource Isolation | Enforced boundaries per component |
| Graceful Degradation | Controlled failure responses under load |
| Idempotent Operations | All state-mutating APIs are idempotent |
| Timely Event Processing | Latency SLAs per event category |
| Auditability | Complete forensic records of security/operational events |
| Compliance with Policies | Real-time adherence to Governance/Security policies |

### 12.3 Conformance Levels

Defined in Part 0 §0.5.1.

| Level | Description | Verification |
|-------|-------------|--------------|
| L1: Structural | Code compiles, imports resolve, base classes implemented | `mypy --strict`, `pytest` collection |
| L2: Contract | Event schemas match spec; interfaces honor signatures | Schema validation tests, interface compliance tests |
| L3: Behavioral | Runtime invariants hold | Integration tests |
| L4: Architectural | No principle violations | Static analysis rules |

### 12.4 MUST / MUST NOT Rules (selected)

These are drawn from Part 0 §0.4 and Part 14 integration principles.

- All inter-component communication MUST occur via EventBus.
- Kernel MUST own exactly four Core Components and MUST NOT contain domain logic.
- Every Service MUST extend BaseService and MUST NOT call other services directly.
- Events MUST carry correlation_id and causation_id and MUST be immutable.
- Failures MUST be communicated via Events; there are no exceptions crossing service boundaries.
- Configuration MUST use the four-layer merge and MUST be immutable after INITIALIZING.
- Extensions MUST use documented Extension Points only; MUST NOT invent new ones.
- Part 14 MUST NOT silently resolve CONFLICTs; MUST record and escalate.

### 12.5 Validation Mechanisms

| Mechanism | Primary Source |
|-----------|---------------|
| Review checklists | Part 12 `review-checklist.md`, Part 13 `review-checklist.md`, Part 14 `review-checklist.md`, Part 15 `review-checklist.md` |
| Runtime invariants/conformance | Part 12 `12.12-*.md`, Part 13 `13.12-*.md`, Part 14 `14.12-*.md` |
| Integration tests | Part 0 §0.5.1 L3; `Common/ARCHITECTURAL_INVENTORY.md` |
| Static analysis | Part 0 §0.5.1 L4 |
| JSON schema validation | Part 12 `12.11-*.md`, Part 14 `14.11-*.md`, Part 09 shared JSON schemas |
| Final gate / readiness | Part 15 README §18–20 (NOT READY) |

---

## 13. DIAGRAM INDEX

Diagrams are stored under `architecture/project-knowledge/diagrams/` and within Part READMEs as embedded Mermaid.

| Diagram | What it explains | Components | Related Part |
|---------|------------------|------------|--------------|
| `OVERALL_ARCHITECTURE.md` | High-level architecture orientation | Kernel, managers, services, extensions | Part 0 / Part 1 |
| `AI_OS_COMPLETE_ARCHITECTURE.md` | Complete system architecture map | All major layers/components | Part 0 / Part 1 |
| `AGENT_FLOW.md` | Agent lifecycle and flow | AIAgencyService, agents | Part 8 / Part 4.10 |
| `MCP_FLOW.md` | MCP integration flow | MCPManager, MCPService, transports | Part 6 / Part 8 |
| `MEMORY_FLOW.md` | Memory data flow | MemoryManager, memory tiers, backends | Part 4.6 / Part 9 |
| `COUNCIL_FLOW.md` | Council decision flow | CouncilManager, councils | Part 4.9 / Part 12 |
| `WORKFLOW_FLOW.md` | Workflow execution flow | WorkflowManager | Part 4.2 / Part 12 |
| `RUNTIME_EXECUTION_FLOW.md` | Runtime execution flow | HermesKernel, initialization phases | Part 3 / Part 10 |
| `PART_FLOW.md` | Part sequencing/flow | All 15 parts | `MASTER_ARCHITECTURE_ROADMAP.md` §3 |
| `REPOSITORY_MAP.md` | Repository ecosystem map | Repositories/tools by category | Part 15 / `project-knowledge/REPOSITORY_ECOSYSTEM.md` |
| Part 13 governance lifecycle | Governance phases loop | Policy, authority, risk, compliance, audit | Part 13 README |
| Part 13 governance domains | Domain map of governance | Governance domains | Part 13 README |
| Cross-part dependency graph | Part layering dependencies | Foundation → Integration → Data → Security → … | `MASTER_ARCHITECTURE_ROADMAP.md` §3 |
| Initialization/shutdown phases | Kernel init/shutdown sequence | Phases 0–8 and reverse shutdown | Part 14 README |
| Specification evolution roadmap | Roadmap chart | Specification milestones | `ROADMAP.md` |
| Ecosystem growth roadmap | Roadmap chart | Skills/MCP/Repository milestones | `ROADMAP.md` |
| Governance evolution roadmap | Roadmap chart | ARB and ecosystem governance milestones | `ROADMAP.md` |

---

## 14. ROADMAP / IMPLEMENTATION CONTEXT

| Document | Location | What it contributes |
|----------|----------|---------------------|
| `ROADMAP.md` | `project-knowledge/ROADMAP.md` | Near/mid/long-term roadmap for specification evolution, ecosystem maturation, reference runtime milestones, governance maturation, community growth, research areas, risks, success criteria, milestones; Mermaid roadmap charts |
| `IMPLEMENTATION_GUIDE.md` | `project-knowledge/IMPLEMENTATION_GUIDE.md` | Conformance guidance for implementations |
| `VALIDATION_ARCHITECTURE.md` | `project-knowledge/VALIDATION_ARCHITECTURE.md` | Methods for assessing specification conformance; pre/during/post execution validation |
| `ENGINEERING_PRINCIPLES.md` | `project-knowledge/ENGINEERING_PRINCIPLES.md` | Foundational engineering principles: architectural integrity, verification-first, observability by design, security/privacy, performance, maintainability, ecosystem awareness |
| `VERSION_HISTORY.md` | `project-knowledge/VERSION_HISTORY.md` | Version history |
| `ARCHITECTURE_EVOLUTION.md` | `project-knowledge/ARCHITECTURE_EVOLUTION.md` | Historical progression to current state |
| `Common/MASTER_ARCHITECTURE_ROADMAP.md` | `Common/MASTER_ARCHITECTURE_ROADMAP.md` | 15-part roadmap table, shared components table, shared JSON schemas table, ADR mapping, global principles, global runtime invariants, naming conventions, document standards, review checklist, progress tracker |
| `Common/ARCHITECTURE_SPEC_TOC.md` | `Common/ARCHITECTURE_SPEC_TOC.md` | Recommended TOC; cross-reference to implementation files; open decisions; conflicting Part 15 classification |

---

## 15. DOCUMENT AUTHORITY

The authority model is recorded as follows across the reviewed documents:

| Source | Authority claim |
|--------|-----------------|
| Part 0 | FROZEN — authoritative source of truth for terminology, principles, scope, conformance levels, extension points, ADR process. All later Parts MUST conform to Part 0. |
| Parts 1–14 | Authoritative for their own architectural domain; domain-based, not numerical. |
| Part 14 | Authoritative for integration patterns, dependency analysis, component inventory, interface catalog, event catalog, ADR index. |
| Part 15 | Implementation-facing layer under Parts 0–14; currently NOT READY. Does not override Parts 0–14. |
| Accepted/Active ADRs | Authoritative for their explicit decisions within stated scope. Draft ADRs do not constrain implementation. |
| `Common/MASTER_ARCHITECTURE_ROADMAP.md` | Authoritative roadmap/index for part classification, shared components, shared schemas. |
| `project-knowledge/AI_OS_MASTER_CONTEXT.md` | Explicitly described as “definitive source of truth” for the architecture narrative; used in conjunction with Parts 1–15. |

There is an explicit conflict that remains unresolved:

- `CONFLICT-P15-01`: `MASTER_ARCHITECTURE_ROADMAP.md` classifies Part 15 as “Architecture Evolution & Extensibility”; `ARCHITECTURE_SPEC_TOC.md` classifies Part 15 as “Appendices”. Part 15 README preserves this conflict and states it must be resolved by ARB.

Otherwise, no single explicit hierarchy beyond “domain-based authority + accepted ADRs + Part 0 foundational authority” is formally stated in the docs reviewed.

---

## 16. CONTRADICTIONS

| Issue | Document A | Document B | Exact conflict |
|-------|-----------|-----------|----------------|
| Part 15 classification | `Common/MASTER_ARCHITECTURE_ROADMAP.md` §4 — Part 15 = “Architecture Evolution & Extensibility” with 13 chapters | `Common/ARCHITECTURE_SPEC_TOC.md` §15 — Part 15 = “Appendices” with 7 appendices (A–G) | Structurally different content models for Part 15 |
| Part 15 chapter numbering | Part 14 README chapters 14.1–14.13 define Part 14 chapter numbering | Part 15 document map uses 15.1–15.13 with different domain focus | Numbering overlap is structurally ambiguous if Part 15 is “Appendices” |
| Part 15 readiness vs. content | Part 15 README states Final Gate = NOT READY because many files are EMPTY | Some supporting documents and `15.7-Communication-and-Event-Implementation.md` exist and are marked EXISTING | README claims incomplete set while some chapter content exists |
| Part 14/15 vs. roadmap TOC authority | `MASTER_ARCHITECTURE_ROADMAP.md` treats Part 14 as “Architecture Governance & Conformance” and Part 15 as “Architecture Evolution & Extensibility” | `ARCHITECTURE_SPEC_TOC.md` treats Part 14 as one of the continuing numbered parts but does not assign the same terminal role to Part 15 | Different interpretation of late-part roles |
| Terminology counts | `AI_OS_MASTER_CONTEXT.md` lists 9 core managers plus CouncilManager and AIAgencyService separately, implying 11 capability-like managers | `MASTER_ARCHITECTURE_ROADMAP.md` §4 and Part 0 list exactly 9 Core Managers; Part 4 defines the 12 manager-like objects including ModelRouter and ResourceManager | “9 Core Managers” vs. “11 capability-like managers” framing |
| Core component/manager counts | `MASTER_ARCHITECTURE_ROADMAP.md` §4 shows 4 Core Components and 9 Core Managers; also lists additional managers in shared-components table | `AI_OS_MASTER_CONTEXT.md` lists 4 kernel core items plus additional managers; Part 0 explicitly distinguishes 4 Core Components from 9 Core Managers | Counts are consistent at 4 CC / 9 CM, but narrative files occasionally present expanded manager lists without clear categorization |

Additional conflicts may exist at the claim level inside Part 14 chapters because Part 14 uses a status taxonomy that can label the same fact as EXISTING in one place and GAP/CONFLICT in another; Part 14 README instructs that such entries must be preserved and escalated.

---

## 17. MASTER NAVIGATION TABLE

| Topic | Primary Source | Supporting Sources | Diagram | ADR | Validation |
|-------|---------------|--------------------|---------|-----|------------|
| Architecture overview / philosophy | Part 0, Part 1 | `AI_OS_MASTER_CONTEXT.md`, `Common/MASTER_ARCHITECTURE_ROADMAP.md` | `OVERALL_ARCHITECTURE.md`, `AI_OS_COMPLETE_ARCHITECTURE.md` | Part 0 §0.5.3 | Part 0 conformance levels |
| Hermes Kernel lifecycle | Part 3 | Part 1, Part 14 | `RUNTIME_EXECUTION_FLOW.md` | NOT SPECIFIED | Part 14 README |
| EventBus / events | Part 2 | Part 0 §0.3, Part 14 | `PART_FLOW.md` | NOT SPECIFIED | Part 2; Part 14 events.md |
| StateManager | Part 4 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 interfaces.md |
| WorkflowManager | Part 4 | Part 12, Part 14 | `WORKFLOW_FLOW.md` | NOT SPECIFIED | Part 14 interfaces.md |
| ResourceManager | Part 4 / Part 13 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 13 components.md |
| RetryManager | Part 4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| CheckpointManager | Part 4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| RootCauseAnalyzer | Part 4 | Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| MemoryManager / Memory tiers | Part 4 / Part 9 | Part 8, Part 10, Part 11, Part 14 | `MEMORY_FLOW.md` | NOT SPECIFIED | Part 14 README |
| SkillManager / SkillService | Part 4 / Part 8 | Part 6, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| MCPManager / MCPService | Part 4 / Part 6 | Part 7, Part 13, Part 14 | `MCP_FLOW.md` | NOT SPECIFIED | Part 14 README |
| CouncilManager / Councils | Part 4 / Part 12 / Part 13 | Part 8, Part 14 | `COUNCIL_FLOW.md` | NOT SPECIFIED | Part 14 README |
| AIAgencyService / Agents | Part 4 / Part 8 | Part 12, Part 14 | `AGENT_FLOW.md` | NOT SPECIFIED | Part 14 README |
| ModelRouter | Part 4 / Part 7 | Part 8, Part 9, Part 10, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| BaseService / ServiceRegistry | Part 3 / Part 5 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| Engineering Services | Part 6 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| Configuration system | Part 7 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README; Part 15 `configuration.md` |
| CLI surface | Part 8 | Part 9 shared schemas | NOT SPECIFIED | NOT SPECIFIED | Part 14 README; Part 15 `configuration.md` |
| Observability / logging / metrics | Part 5 / Part 9 | Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 9 shared schemas; Part 14 observability integration |
| Multi-agent collaboration | Part 12 | Part 14 | Part 12 chapter diagrams | Part 12 `adrs.md` | Part 12 `review-checklist.md` |
| Governance | Part 13 | Part 4, Part 12, Part 14 | Part 13 README diagrams | Part 13 `adrs.md` | Part 13 `review-checklist.md` |
| Integration architecture | Part 14 | Parts 0–13 | Part 14 chapter diagrams | Part 14 `adrs.md` | Part 14 `review-checklist.md` |
| Implementation / extensibility | Part 15 | Parts 0–14 | NOT SPECIFIED | Part 15 `adrs.md` | Part 15 `review-checklist.md` |
| Repository ecosystem | `project-knowledge/REPOSITORY_ECOSYSTEM.md` | `AI_OS_MASTER_CONTEXT.md`, `ROADMAP.md` | `REPOSITORY_MAP.md` | NOT SPECIFIED | NOT SPECIFIED |
| Skills ecosystem | `project-knowledge/SKILLS_ECOSYSTEM.md` | Part 8, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 14 README |
| MCP ecosystem | `project-knowledge/MCP_ECOSYSTEM.md` | Part 4, Part 6, Part 8, Part 14 | `MCP_FLOW.md` | NOT SPECIFIED | Part 14 README |
| Memory architecture | `project-knowledge/MEMORY_ARCHITECTURE.md` | Part 4, Part 9, Part 14 | `MEMORY_FLOW.md` | NOT SPECIFIED | Part 14 README |
| Validation architecture | `project-knowledge/VALIDATION_ARCHITECTURE.md` | Part 0, Part 12, Part 13, Part 14 | NOT SPECIFIED | NOT SPECIFIED | Part 0 §0.5.1 |
| Engineering principles | `project-knowledge/ENGINEERING_PRINCIPLES.md` | Part 0, `Common/MASTER_ARCHITECTURE_ROADMAP.md` | NOT SPECIFIED | NOT SPECIFIED | Part 0 §0.4 |

---

## 18. FINAL ONE-PAGE MAP

### 18.1 What is AI-OS?

AI-OS is an architectural specification and reference implementation for an artificial intelligence operating system designed to enable autonomous, goal-driven engineering workflows through an event-driven kernel (Hermes), governed AI agents, councils, extensible skills/MCP ecosystems, and deterministic recovery. It is structured as a frozen 15-part specification with a reference runtime and explicit extension points.

### 18.2 Major Layers

1. Application layer
2. Platform layer (Engineering Services, Facade Services, CLI)
3. Hermes Kernel layer (EventBus, StateManager, WorkflowManager, ResourceManager)
4. Capability Managers layer (9 kernel-owned managers)
5. Extension Points layer (Skills, MCP, custom events, memory backends, etc.)

### 18.3 Kernel Components

| Component | Role |
|-----------|------|
| EventBus | Sole inter-component communication substrate |
| StateManager | Scoped state persistence and snapshotting |
| WorkflowManager | Workflow definition, DAG validation, orchestration |
| ResourceManager | Resource allocation, quotas, cleanup |

### 18.4 Managers

| Manager | Role |
|---------|------|
| RetryManager | Retry budgets, backoff, dead-letter semantics |
| CheckpointManager | Workflow snapshotting and recovery |
| RootCauseAnalyzer | Failure classification and recovery routing |
| MemoryManager | Five-tier memory system |
| SkillManager | Skill registry, discovery, sandboxed execution |
| MCPManager | External tool integration via Model Context Protocol |
| CouncilManager | Consensus, voting, dissent escalation |
| AIAgencyService | Agent lifecycle, audit, quotas |
| ModelRouter | Capability-based LLM routing and fallback |

### 18.5 Services

| Service type | Examples / role |
|--------------|-----------------|
| Engineering Services (8) | Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory facade |
| Capability Facade Services (4) | SkillService, CouncilService, MCPService, MemoryService |

### 18.6 Agency / Council Systems

- AIAgencyService manages agent lifecycle, permissions, audit, quotas, and performance monitoring.
- 9 specified agents exist, with FinalJudge as a mandatory human oversight gate.
- CouncilManager supports Claude Council, LLM Council, and specialized councils.
- Consensus algorithms: MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT.

### 18.7 Memory Systems

Five tiers owned by MemoryManager:
1. Working Memory
2. Claude Memory
3. Engineering Intelligence
4. Obsidian
5. Graphify

Backends include `MemoryBackend` ABC, `InMemoryBackend`, `FileMemoryBackend`, plus extension points for custom backends.

### 18.8 MCP Ecosystem

MCPManager/MCPService provide transport abstraction, tool registry, capability negotiation, security profiles, state management, discovery, and tool certification. Transports include stdio, HTTP, WebSocket, plus extension mechanisms.

### 18.9 Skills Ecosystem

SkillManager/SkillService provide discovery, loading, semantic versioning, sandboxing, governance, composition (chain/parallel/conditional), development kit, marketplace extension point, and deprecation policies.

### 18.10 Repositories / Tools Involved

Architecture defines categories rather than a fixed repository list:
- Core Architecture, Core Implementation, AI Agency, Reference Implementations, External Integrations, MCP Integrations, Skills, Development Tools, Evaluation Tools.

### 18.11 Where Each Thing Is Documented

| Concern | Primary docs |
|---------|-------------|
| Kernel | Part 3; Part 0 §0.3/§0.4 |
| EventBus / events | Part 2; Part 14 events.md |
| Managers | Part 4; Part 14 interfaces.md |
| Services | Part 5, Part 6; Part 14 interfaces.md |
| Agency | Part 4.10, Part 8, Part 12; Part 14 README |
| Councils | Part 4.9, Part 12, Part 13; Part 14 README |
| Memory | Part 4.6, Part 9; Part 14 README |
| MCP | Part 4.8, Part 6, Part 8, Part 14 |
| Skills | Part 4.7, Part 8, Part 14 |
| Observability | Part 5, Part 9; Part 14 observability integration |
| Recovery | Part 4.3–4.5; Part 14 README |
| Governance | Part 13; Part 14 governance domains |
| Integration rules | Part 14; Part 15 implementation-contracts.md |
| Roadmap / context | `Common/MASTER_ARCHITECTURE_ROADMAP.md`, `project-knowledge/AI_OS_MASTER_CONTEXT.md`, `project-knowledge/ROADMAP.md` |

### 18.12 Major Dependencies

- Part 0 → Parts 1–15
- Part 1 → Parts 2–6
- Part 2 → Part 14
- Part 3 → Part 4, Part 5, Part 14
- Part 4 → Parts 9, 12, 13, 14
- Part 5/6 → Part 14
- Part 8 → Parts 10, 11, 12, 14
- Part 12 → Parts 13, 14
- Part 13 → Parts 14, 15
- Part 14 → Part 15

### 18.13 Major Architectural Invariants

- Event-first communication only; no direct service-to-service calls.
- Kernel owns exactly 4 Core Components and 9 Core Managers.
- Events are immutable with correlation_id and causation_id.
- Services extend BaseService and communicate only via EventBus.
- Configuration is immutable after INITIALIZING.
- All failures are communicated via Events.
- Part 14 MUST NOT silently resolve CONFLICTs.
- Part 15 MUST NOT invent architecture beyond Part 0 §0.5.2 extension points.

---

*This document is an indexing/navigation map only. It does not modify, redesign, or reinterpret the architecture. Where the source documents are silent, this map records NOT SPECIFIED rather than inventing detail.*
