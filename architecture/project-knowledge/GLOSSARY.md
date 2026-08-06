# AI-OS Architecture Reference Dictionary

## 1. Introduction

### Purpose
This document serves as the definitive AI-OS Architecture Reference Dictionary, providing precise, canonical definitions for every architectural term used in the AI-OS ecosystem. It functions as the single source of truth for terminology, ensuring consistent understanding and communication across all stakeholders while maintaining strict alignment with the frozen AI-OS Architecture Specification (Parts 1-15).

### Scope
This reference dictionary covers all architectural terms defined in the AI-OS Architecture Specification and used throughout AI-OS project knowledge, documentation, code, discussions, and implementations. It includes terms from all architectural domains: core architecture, runtime, AI agency, execution, memory, skills, MCP, engineering services, governance, validation, security, repository ecosystem, observability, recovery, documentation, conformance, and versioning.

### Audience
- Software architects and engineers ensuring AI-OS conformance
- Technical writers and documentation specialists
- Quality assurance engineers and auditors
- AI Agency developers and skill contributors
- System administrators and deployment engineers
- Anyone seeking authoritative understanding of AI-OS terminology

### Relationship to the Architecture Specification
This dictionary is derived from and fully aligned with the AI-OS Architecture Specification (Parts 1-15), which remains the normative, frozen source for architectural requirements, constraints, and invariants. This document does not override, contradict, or extend the specification; it serves as an authoritative companion reference that clarifies and standardizes terminology usage.

### Relationship to other project-knowledge documents
This dictionary supports all other project-knowledge documents (IMPLEMENTATION_GUIDE.md, ENGINEERING_PRINCIPLES.md, ARCHITECTURE_DECISIONS.md, etc.) by providing standardized definitions. When a term is used in those documents, its meaning is as defined herein. Ownership of specific terms is documented where applicable.

## 2. Dictionary Organization

### Architectural Domains
Terms are organized into logical architectural domains that reflect the AI-OS layered architecture and functional areas. Within each domain, terms are ordered alphabetically for easy lookup.

### Structured Entries
Major architectural terms include structured metadata:
- **Category**: Architectural domain classification
- **Canonical Definition**: Precise, AI-OS-specific definition
- **Owner Document**: Primary document defining the term
- **Related Terms**: Semantically connected concepts
- **Related Architecture Parts**: Specification parts where term is defined
- **Status**: Current terminology status (Standard, Deprecated, etc.)
- **Notes**: Additional context, usage guidance, or historical information

Minor terms retain simple dictionary format for readability.

### Cross References
Definitions use [[double brackets]] for internal cross-references to help build understanding of interconnected concepts. Major concepts include precise ownership references to specific documents rather than generic part numbers.

### Indices
Multiple indices provide different navigation paths:
- Category Index: Terms grouped by architectural domain
- Alphabetical Index: Complete A-Z listing
- Acronym Index: All AI-OS acronyms with expansions
- Deprecated Terminology: Deprecated terms with preferred replacements
- Naming Conventions: Standards for AI-OS terminology
- Concept Ownership: Matrix showing which document owns each major concept

### Naming Conventions
- **Component Names**: PascalCase (e.g., Core Manager, Capability Manager)
- **Interfaces and Protocols**: PascalCase (e.g., Model Context Protocol)
- **Configuration Parameters**: snake_case (e.g., max_token_budget)
- **File Names**: kebab-case (e.g., architecture-decision-record.md)
- **Code Identifiers**: Language-appropriate conventions with semantic clarity
- **Acronyms**: Expanded on first use, then acronym consistently

## 3. Architectural Domains

### 3.1 Core Architecture

| Term | Definition |
|------|------------|
| [[Architecture]] | The fundamental structure and organizing principles of the AI-OS system, defining its essential components, their relationships, interaction patterns, and the constraints governing its design and evolution as specified in Parts 1-15 of the Architecture Specification. |
| [[Architecture Specification]] | The frozen, normative document (Parts 0-15) that establishes the authoritative requirements, constraints, and invariants for AI-OS conformance. Part 0 provides overview; Parts 1-15 define specific architectural domains. |
| [[Architecture Decision Record (ADR)]] | A document capturing a significant architectural decision, including its context, alternatives considered, decision rationale, and consequences. Owned by ARCHITECTURE_DECISIONS.md and referenced throughout the specification. |
| [[Architectural Invariant]] | A condition that MUST always hold true in a conforming AI-OS system, regardless of state, execution context, or implementation technology. Defined in Part 1 and enforced throughout the system lifecycle. |
| [[Architectural Constraint]] | A restriction or limitation imposed on AI-OS implementations to preserve architectural integrity, system properties, and specification compliance. Defined in Part 1 and governing all design and implementation decisions. |
| [[Conformance]] | The state of adhering to all architectural requirements, constraints, and invariants defined in the AI-OS Architecture Specification. Validated through the Validation Architecture (Part 15) and measured across conformance levels (L1-L4). |
| [[Extension Point]] | A designated, governed location in the AI-OS architecture where additional functionality can be added through formalized ecosystems (Skills, MCP, Repository) without violating core constraints or requiring specification changes. |

### 3.2 Runtime and Kernel

| Term | Definition |
|------|------------|
| [[Reference Runtime (Hermes)]] | The canonical Python 3.12+ implementation demonstrating AI-OS Architecture Specification compliance. Provides the EventBus, StateManager, WorkflowManager, ResourceManager, and nine Core Managers as the compliance target for all implementations. |
| [[Production Runtime]] | An implementation of the AI-OS Architecture Specification deployed in operational environments, prioritizing performance, security, and reliability while maintaining specification conformance. May differ from Reference Runtime in optimization and technology choices. |
| [[Hermes Kernel]] | The orchestration core of AI-OS consisting of exactly four Core Components (EventBus, StateManager, WorkflowManager, ResourceManager) that provides pure orchestration without domain logic, enforcing the Event-First Communication Principle. |
| [[Core Component]] | One of the four fundamental elements of the Hermes Kernel: EventBus (communication substrate), StateManager (state persistence), WorkflowManager (execution orchestration), or ResourceManager (quota management). |
| [[Core Manager]] | One of the nine capability managers owned and lifecycle-managed by the Hermes Kernel: MemoryManager, ModelRouter, ToolManager, StorageManager, ContextManager, AgentManager, RetryManager, CheckpointManager, RootCauseManager, CouncilManager, or AIAgencyService. |
| [[EventBus]] | The sole communication substrate for all inter-component communication in AI-OS, enforcing the Event-First Communication Principle through immutable events with correlation/causation IDs, schema versioning, and interception capabilities. |
| [[StateManager]] | The Core Component providing centralized state persistence with hierarchical scoping (global, workflow, session, agent), transactional updates, snapshotting for checkpointing, and query interfaces. |
| [[WorkflowManager]] | The Core Component orchestrating engineering processes through workflow definition/execution, dependency management, topological ordering, parallel/sequential patterns, and state tracking/progress reporting. |
| [[ResourceManager]] | The Core Component managing resource allocation and quotas for CPU, memory, tokens, and computational resources through tracking, reservation, release mechanisms, and usage monitoring/enforcement. |
| [[Event-First Communication Principle]] | The architectural principle requiring ALL inter-component communication to occur exclusively through the EventBus post-initialization, enabling observability, loose coupling, and replay debugging capabilities. |
| [[Kernel as Pure Orchestrator]] | The architectural principle stating the Hermes Kernel contains zero domain logic, serving only as an orchestration core managing core components and capability managers. |
| [[Fixed Component Counts]] | The architectural principle maintaining stability by fixing the kernel at precisely four Core Components and nine Core Managers, with variability handled through formalized extension points. |

### 3.3 AI Agency and Governance

| Term | Definition |
|------|------------|
| [[AI Agency]] | The AIAgencyService Core Manager responsible for orchestrating autonomous AI agents that perform engineering tasks. It manages agent lifecycle, execution, goal decomposition, planning, reflection, validation integration, and governance oversight while maintaining the Kernel's pure orchestrator role. |
| [[Agent]] | An autonomous entity within AI-OS that perceives context, makes decisions, and executes actions to achieve goals. Agents operate under configurable autonomy levels (supervised, guided, autonomous) and are managed by the AI Agency Service. |
| [[Agent Lifecycle]] | The sequence of states an agent transitions through: CREATED → INITIALIZING → RUNNING → {COMPLETED, FAILED, CANCELLED, TERMINATED}, exclusively managed by the AIAgencyService with audit event generation. |
| [[Goal]] | A high-level engineering objective expressed in natural language (e.g., "implement user authentication with OAuth 2.0") that drives the creation and execution of workflows within AI-OS's Goal-Driven Execution Engine. |
| [[Goal-Driven Execution Engine]] | The AI-OS subsystem that accepts high-level goals, AI-powered planning that decomposes goals into actionable work, dynamic plan adaptation based on feedback, and continues until validation criteria are met or intervention requested. |
| [[Plan]] | A predefined sequence of tasks and workflows designed to achieve a particular objective, used by the Goal-Driven Execution Engine for initial goal decomposition and by the AI Agency for adaptive replanning. |
| [[Task]] | A unit of work within a workflow or plan representing a specific action to be performed, characterized by defined inputs, outputs, preconditions, postconditions, and resource requirements. |
| [[Workflow]] | A structured sequence of executions designed to achieve a specific goal, orchestrated by the WorkflowManager through definition, execution, dependency management, and state tracking. |
| [[Execution]] | The runtime instantiation and processing of a workflow step, task, or agent action within the AI-OS environment, subject to validation, resource constraints, and governance oversight. |
| [[Reflection]] | The mechanism by which AI-OS agents introspect and adapt their behavior based on execution outcomes, system state, and learned patterns, contributing to knowledge consolidation in Engineering Intelligence memory. |
| [[Validation-First Execution]] | The architectural principle requiring pre-execution, during-execution, and post-execution validation of all agentic operations to ensure safety, correctness, and goal alignment. |
| [[Council]] | A governance body within AI-OS responsible for architectural decisions, standards approval, policy oversight, and system evolution. Includes Claude Council (architectural/agent decisions) and LLM Council (model/safety decisions) with voting algorithms and FinalJudge integration. |
| [[Claude Council]] | The governance body reviewing AI agent proposals, architectural decisions, and policy compliance, operating under MAJORITY, UNANIMOUS, or WEIGHTED voting algorithms with dissent escalation to FinalJudge. |
| [[LLM Council]] | The governance body focusing on model selection, token budgeting, safety considerations, and provider reliability for LLM interactions within AI-OS. |
| [[FinalJudge]] | The human oversight capability providing veto and override rights over AI agent decisions when required by governance policy, enabling human-in-the-loop validation for critical judgments. |
| [[AIAgencyService]] | The Core Manager (one of nine) providing AI agent lifecycle management, execution orchestration, resource governance, capability integration, audit generation, Council integration, FinalJudge coordination, health monitoring, goal management, planning, reflection, replanning, delegation, multi-agent collaboration, communication, memory integration, and validation framework coordination. |

### 3.4 Memory and Knowledge

| Term | Definition |
|------|------------|
| [[Memory]] | The AI-OS subsystem responsible for persistent storage and retrieval of information, experiences, and learned patterns through a five-tier hierarchical system designed for knowledge progression from immediate processing to organizational intelligence. |
| [[Working Memory]] | The volatile, session-scoped memory tier providing high-bandwidth storage for active agent reasoning context, current task state, recent observations, and short-term computational workspace, cleared on session end. |
| [[Claude Memory]] | The semi-persistent, agent-type scoped memory tier storing agent-specific learned behaviors, preferences, conversation history, and working state to enable seamless session resumption across restarts. |
| [[Engineering Intelligence]] | The persistent, system-wide memory tier storing organizational knowledge including validated solution patterns, architectural decisions, reusable components, and best practices accessible to all agents and engineering services. |
| [[Obsidian Memory]] | The persistent, system-wide memory tier providing linked knowledge graph capabilities for semantic relationship mapping, architectural decisions, design documents, wikis, and documentation vault integration with versioned artifacts. |
| [[Graphify Memory]] | The persistent, system-wide memory tier storing structured knowledge for reasoning, executable knowledge, validation rules, logical constraints, machine-executable procedures, and decision trees supporting automated inference and constraint satisfaction. |
| [[Knowledge]] | The structured information and learned patterns stored in AI-OS memory tiers that inform decision-making, behavior, and system intelligence, progressing from episodic experiences to generalizable principles through validated consolidation. |
| [[Memory Hierarchy]] | The five-tier organization of AI-OS memory (Working → Claude → Engineering Intelligence → Obsidian → Graphify) representing a volatility gradient and knowledge progression from volatile working memory to persistent organizational intelligence. |
| [[Knowledge Consolidation]] | The governed process validating, transforming, and promoting knowledge from lower to higher memory tiers based on utility, reliability, and relevance thresholds, enabling progression from specific experiences to reusable patterns. |
| [[Memory Lifecycle]] | The complete knowledge journey from acquisition through classification, validation, initial storage, consolidation, application, maintenance, and eventual archival or deletion, with audit event generation at each transition. |
| [[Contextual Primacy]] | The memory architecture principle requiring retrieval and storage operations to prioritize relevance to current execution context, active goals, and task requirements for effective agent decision-making. |
| [[Progressive Consolidation]] | The memory architecture principle describing knowledge flow from volatile working memory to persistent long-term storage through validated, governed processes ensuring quality before promotion. |
| [[Isolation Boundaries]] | The memory architecture principle enforcing strict separation between memory tiers and agent contexts through mediated access controls to prevent unauthorized access, data leakage, and privilege escalation. |

### 3.5 Skills and Ecosystems

| Term | Definition |
|------|------------|
| [[Skill]] | A modular, reusable unit of expertise or functionality that can be dynamically loaded and executed by AI-OS components through standardized interfaces, metadata, contracts, and governance, enabling capability extension without core modification. |
| [[Skills Ecosystem]] | The architectural framework governing reusable engineering capabilities within AI-OS, providing discovery, versioning, sandboxing, composition, governance, and development kit mechanisms for skill creation, distribution, and consumption. |
| [[Skill Registry]] | The central repository storing skill metadata and managing skill lifecycle through registration, version storage, indexing, lifecycle state management, governance tracking, and dependency resolution assistance. |
| [[Skill Catalog]] | The curated, searchable view of the Skill Registry optimized for discovery through faceted browsing, search functionality, recommendations, version visibility, compatibility information, and trust indicators. |
| [[Skill Discovery]] | The mechanisms enabling both human and AI Agency consumers to find relevant skills through metadata search, capability matching, contextual discovery, recommendation engines, and federated discovery across multiple registries. |
| [[Skill Composition]] | The process of combining skills in flexible ways (chaining, orchestration, parallel execution, conditional workflows, parameterization) to create more complex behaviors from primitive capabilities. |
| [[Skill Versioning]] | The semantic versioning (MAJOR.MINOR.PATCH) system for skills with backward compatibility guarantees within major versions, clear deprecation paths, and dependency resolution. |
| [[Skill Sandboxing]] | The standardized execution environments with configurable permission profiles, resource isolation/enforcement, and security scanning that provide secure execution contexts for skills. |
| [[MCP (Model Context Protocol)]] | The standardized interface enabling AI-OS components to interact with external AI models, tools, and services through well-defined capability profiles, secure transports, granular permissions, and state management patterns. |
| [[MCP Ecosystem]] | The framework governing external tool integration in AI-OS through standardized transports, capability profiles, security frameworks, state management, discovery mechanisms, and certification programs for MCP servers. |
| [[MCP Transport]] | The standardized implementations for stdio, HTTP, WebSocket, and other communication channels enabling secure, authenticated, encrypted interactions between AI-OS and external tools with flow control and connection pooling. |
| [[MCP Capability]] | Well-defined profiles for common functions (file access, web search, code execution, etc.) featuring capability negotiation/discovery, granular permission models, and versioning for evolution. |
| [[Repository Ecosystem]] | The framework enabling sharing and reuse of engineering assets in AI-OS through workflow templates, component libraries, reference architectures, best practices, learning materials, and community hub mechanisms. |
| [[Workflow Template]] | Reusable SDLC patterns for common project types (web applications, microservices, data pipelines) that are parameterizable with variable substitution, provide best practice guidance, and include domain-specific customization points. |
| [[Component Library]] | Shareable services, managers, and extensions that are versioned with dependency management, undergo compatibility testing/validation, and provide documentation and usage examples. |
| [[Reference Architecture]] | Proven solutions for specific domains (web, mobile, embedded, IoT) that include architecture decision records, trade-off analyses, implementation guidelines/patterns, and performance/scalability characteristics. |

### 3.6 Engineering Services

| Term | Definition |
|------|------------|
| [[Engineering Service]] | One of the eight event-driven services covering SDLC phases (Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory) that extends the BaseService contract and communicates exclusively through the EventBus post-initialization. |
| [[Planning Service]] | The Engineering Service responsible for goal decomposition, task breakdown, resource estimation, risk assessment, mitigation planning, and workflow initiation to transform high-level objectives into executable work. |
| [[Coding Service]] | The Engineering Service handling code generation, implementation, syntax validation, basic correctness checks, code style enforcement, formatting, and version control integration for AI-generated code. |
| [[Review Service]] | The Engineering Service performing code quality analysis, security vulnerability scanning, performance anti-pattern detection, and review comment generation/disposition to ensure generated code meets standards. |
| [[Testing Service]] | The Engineering Service developing test strategies, generating test cases, executing tests, analyzing results, measuring coverage, identifying gaps, and integrating with test automation and continuous testing systems. |
| [[Deployment Service]] | The Engineering Service managing deployment planning, environment preparation, release management, version control, deployment execution, validation, rollback procedures, and failure handling for AI-OS system releases. |
| [[Operations Service]] | The Engineering Service providing system monitoring, health checking, incident detection/response coordination, performance optimization/tuning, and log aggregation/analysis for operational AI-OS systems. |
| [[Learning Service]] | The Engineering Service collecting experience from completed workflows, extracting patterns, generalizing knowledge into Engineering Intelligence, and generating skills from recurring patterns for continuous system improvement. |
| [[Memory Service]] | The Engineering Service managing long-term memory persistence, consolidation, optimization, cross-session knowledge retention, and access control/security for the Engineering Intelligence memory tier. |
| [[BaseService Contract]] | The standardized interface requiring all AI-OS services to implement lifecycle management (INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED), dependency injection, event-driven communication, configuration access, health checks, error handling, and service discovery/registration. |
| [[Event-Driven Communication]] | The communication pattern requiring all services to interact exclusively through event emission and subscription via the EventBus post-initialization, enabling loose coupling, observability, and deterministic behavior. |

### 3.7 Validation and Quality

| Term | Definition |
|------|------------|
| [[Validation Architecture]] | The comprehensive framework ensuring system correctness, safety, and reliability through layered defense (Architectural, Goal, Workflow, Capability, Memory, Security, AI, Human, Runtime, Artifact, Output validation), continuous validation, and evidence-based assurance. |
| [[Validation-First Approach]] | The architectural principle integrating validation throughout the system lifecycle rather than as a separate phase, incorporating shift-left, continuous validation, layered defense, technology neutrality, and evidence-based assurance. |
| [[Validation Layer]] | One of the eleven validation domains (Architectural through Output validation) providing defense-in-depth verification at different abstraction levels to ensure comprehensive system correctness. |
| [[Validation Mechanism]] | The specific techniques and approaches used within validation layers (static analysis, runtime monitoring, functional testing, human review, property-based validation, etc.) to verify system properties. |
| [[Conformance Level]] | One of four tiers (L1-L4) specifying the rigor and scope of validation applied, ranging from Basic (syntax/format) to Rigorous (formal methods, chaos engineering, comprehensive expert review). |
| [[Quality Gate]] | A validation checkpoint that MUST be passed before allowing progression to subsequent lifecycle stages, featuring clearly defined criteria, automated/manual evaluation, explicit pass/fail logic, and documented escalation paths. |
| [[Validation Pipeline]] | The orchestration system managing validation activities across the lifecycle through triggers (code commit, deployment), orchestrators, execution engines, result aggregators, decision engines, and feedback mechanisms. |
| [[Failure Classification]] | The systematic categorization of validation failures into Blocking (prevents progression), Warning (allows progression with risks), and Informational (provides insights only) to guide remediation workflows. |
| [[Validation Report]] | The auditable evidence documenting validation activities, including scope/criteria, timestamps, pass/fail status, supporting evidence, remediation guidance, and references to standards/policies. |
| [[Validation Governance]] | The oversight structure ensuring consistent validation application and continuous improvement through Validation Architecture Board, Domain Validation Leads, Practitioners Community, and Audit/Compliance functions. |
| [[FinalJudge]] | See [[FinalJudge]] in AI Agency and Governance section - provides human-in-the-loop validation capabilities for complex judgments requiring human oversight. |
| [[Human Validation]] | The validation mechanism incorporating expert review panels, user acceptance testing, usability studies, ethical evaluations, and inter-rater reliability measurements for complex validations requiring human judgment. |

### 3.8 Observability and Recovery

| Term | Definition |
|------|------------|
| [[Observability]] | The AI-OS capability to monitor, trace, and analyze internal state and behavior through metrics, logs, and tracing, featuring structured logging with correlation IDs, custom metric definition, distributed tracing, and health checks for operational insight. |
| [[Metrics]] | The observability pillar providing counter, gauge, histogram, and summary metric types with custom metric registration, predefined metrics for kernel/services/agentic behavior, and export to multiple backends (Prometheus, Datadog, etc.). |
| [[Tracing]] | The observability pillar delivering OpenTelemetry-compatible distributed tracing with automatic instrumentation of kernel/service calls, manual instrumentation points, trace context propagation across asynchronous boundaries, and export to tracing backends (Jaeger, Zipkin, Tempo). |
| [[Logging]] | The observability pillar supplying structured logging with consistent field schemas, correlation ID propagation, configurable levels/output formats, and structured fields for service/agent/workflow/operation context for integration with aggregation systems (ELK, Splunk, etc.). |
| [[Health Checks]] | The observability mechanism providing liveness/readiness probes for all services, deep health checks including dependency validation, configurable intervals/timeouts, and health status reporting for alerting integration. |
| [[Fault Tolerance]] | The AI-OS capability to maintain normal operation despite faults, errors, or unexpected conditions through retry mechanisms, checkpointing, failure classification, recovery routing, and deterministic recovery principles. |
| [[Retry Mechanism]] | The fault tolerance component providing configurable retry budgets per operation type, exponential backoff with jitter, error classification-based selective retry, and dead letter queues for permanently failed operations. |
| [[Checkpointing]] | The fault tolerance mechanism creating workflow execution snapshots at configurable intervals, selective checkpointing based on criticality/cost, fast recovery with minimal data loss, and storage optimization/pruning for system resilience. |
| [[Failure Classification]] | The fault tolerance system categorizing failures as TRANSIENT (temporary/retry-safe), DEGRADED (reduced functionality), CRITICAL (requires attention), or FATAL (system-terminating) to guide recovery routing decisions. |
| [[Recovery Routing]] | The fault tolerance component automatically selecting recovery procedures based on failure type, featuring escalation paths for complex failures, RootCauseManager integration, and manual intervention/override capabilities. |
| [[Deterministic Recovery]] | The fault tolerance principle ensuring consistent recovery state across distributed components, verification of recovery completeness/correctness, and recovery testing/validation mechanisms for long-term reliability. |
| [[RootCauseManager]] | The Core Manager providing automated failure classification and recovery routing through pattern recognition, recovery procedure selection, escalation protocols, and integration with RetryManager for intelligent retry decisions. |
| [[CheckpointManager]] | The Core Manager managing workflow execution snapshotting at intervals, selective checkpointing based on criticality, fast recovery mechanisms, and checkpoint pruning/storage management for fault tolerance. |
| [[RetryManager]] | The Core Manager implementing automatic retry with exponential backoff/jitter, configurable retry budgets per task type, dead letter queue for failed tasks, and RootCauseManager integration for intelligent decisions. |

### 3.9 Configuration and Extension

| Term | Definition |
|------|------------|
| [[Configuration System]] | The four-layer merge configuration system in AI-OS comprising Defaults Layer (built-in values), app.yaml (application-specific), env.yaml (environment-specific), and Environment Variables Layer (runtime overrides) that becomes immutable after the INITIALIZING phase. |
| [[Configuration Layer]] | One of the four layers in the AI-OS Configuration System: Defaults (built-in), app.yaml (application), env.yaml (environment), or Environment Variables (runtime overrides) that are merged with defined precedence. |
| [[Extension Point]] | See [[Extension Point]] in Core Architecture section - a designated, governed location for adding functionality through formalized ecosystems without violating core constraints. |
| [[Schema Versioning]] | The mechanism managing evolution paths for configuration and event schemas with backward/forward compatibility, clear deprecation periods, and migration capabilities to enable system evolution while maintaining compatibility. |
| [[Immutability after INITIALIZING]] | The architectural principle stating AI-OS configuration becomes immutable after the INITIALIZING phase to ensure runtime stability, requiring all configuration to be set during startup via the four-layer merge strategy. |

### 3.10 Documentation and Versioning

| Term | Definition |
|------|------------|
| [[Documentation]] | The tangible products of the AI-OS development or operational process including architecture specifications, implementation guides, design documents, wikis, and reference materials that enable knowledge transfer and system understanding. |
| [[Versioning]] | The AI-OS approach to tracking system evolution through time-based versioning aligned with architectural evolution phases rather than strict semantic versioning, where MAJOR increments reflect paradigm shifts, MINOR significant feature additions, and PATCH bug fixes/security updates. |
| [[Architecture Specification Version]] | The version number of the AI-OS Architecture Specification reflecting architectural maturity, with MAJOR versions indicating fundamental paradigm shifts requiring Architecture Review Board approval when affecting frozen specifications. |
| [[Reference Runtime Version]] | The version number of the Hermes Reference Runtime tracking progress toward specification conformance, with version numbers indicating implementation maturity and compatibility with specific specification versions. |
| [[Semantic Versioning]] | The version format MAJOR.MINOR.PATCH used within AI-OS for Skills, MCP, Repository ecosystems, and Reference Runtime where MAJOR indicates breaking changes, MINOR backward-compatible features, and PATCH backward-compatible fixes. |
| [[Architecture Review Board (ARB)]] | The governance body responsible for AI-OS Architecture Specification evolution, change approval, and ensuring specification stability, integrity, and long-term viability through formal review processes. |

## 4. Indices

### 4.1 Category Index

**Core Architecture**: Architecture, Architecture Specification, Architecture Decision Record (ADR), Architectural Invariant, Architectural Constraint, Conformance, Extension Point  
**Runtime and Kernel**: Reference Runtime (Hermes), Production Runtime, Hermes Kernel, Core Component, Core Manager, EventBus, StateManager, WorkflowManager, ResourceManager, Event-First Communication Principle, Kernel as Pure Orchestrator, Fixed Component Counts  
**AI Agency and Governance**: AI Agency, Agent, Agent Lifecycle, Goal, Goal-Driven Execution Engine, Plan, Task, Workflow, Execution, Reflection, Validation-First Execution, Council, Claude Council, LLM Council, FinalJudge, AIAgencyService  
**Memory and Knowledge**: Memory, Working Memory, Claude Memory, Engineering Intelligence, Obsidian Memory, Graphify Memory, Knowledge, Memory Hierarchy, Knowledge Consolidation, Memory Lifecycle, Contextual Primacy, Progressive Consolidation, Isolation Boundaries  
**Skills and Ecosystems**: Skill, Skills Ecosystem, Skill Registry, Skill Catalog, Skill Discovery, Skill Composition, Skill Versioning, Skill Sandboxing, MCP (Model Context Protocol), MCP Ecosystem, MCP Transport, MCP Capability, Repository Ecosystem, Workflow Template, Component Library, Reference Architecture  
**Engineering Services**: Engineering Service, Planning Service, Coding Service, Review Service, Testing Service, Deployment Service, Operations Service, Learning Service, Memory Service, BaseService Contract, Event-Driven Communication  
**Validation and Quality**: Validation Architecture, Validation-First Approach, Validation Layer, Validation Mechanism, Conformance Level, Quality Gate, Validation Pipeline, Failure Classification, Validation Report, Validation Governance, FinalJudge, Human Validation  
**Observability and Recovery**: Observability, Metrics, Tracing, Logging, Health Checks, Fault Tolerance, Retry Mechanism, Checkpointing, Failure Classification, Recovery Routing, Deterministic Recovery, RootCauseManager, CheckpointManager, RetryManager  
**Configuration and Extension**: Configuration System, Configuration Layer, Extension Point, Schema Versioning, Immutability after INITIALIZING  
**Documentation and Versioning**: Documentation, Versioning, Architecture Specification Version, Reference Runtime Version, Semantic Versioning, Architecture Review Board (ARB)  

### 4.2 Alphabetical Index

A: AI Agency, AIAgencyService, Architecture, Architecture Specification, Architecture Decision Record (ADR), Architectural Constraint, Architectural Invariant  
B: BaseService Contract  
C: CheckpointManager, Checkpointing, Claude Memory, Coding Service, Conformance, Conformance Level, Configuration System, Configuration Layer, Council, Claude Council, LLM Council  
D: Deployment Service, Deterministic Recovery, Documentation  
E: Engineering Service, Engineering Intelligence, EventBus, Event-Driven Communication, Event-First Communication Principle, Execution, Extension Point  
F: FinalJudge, Fault Tolerance  
G: Goal, Goal-Driven Execution Engine, Graphify Memory  
H: Hermes Kernel, Hermes Reference Runtime, Health Checks  
I: Isolation Boundaries  
L: Learning Service, Logging  
M: MCP (Model Context Protocol), MCP Ecosystem, MCP Transport, MCP Capability, Memory, Memory Hierarchy, Memory Lifecycle, Memory Service, Metrics  
N:  
O: Obsidian Memory, Observability, Operations Service  
P: Planning Service, Production Runtime  
Q: Quality Gate  
R: Reference Runtime (Hermes), RetryManager, Retry Mechanism, ResourceManager, Repository Ecosystem, Review Service, RootCauseManager  
S: Skills Ecosystem, Skill, Skill Catalog, Skill Discovery, Skill Composition, Skill Registry, Skill Sandboxing, Skill Versioning, StateManager  
T: Testing Service, Tracing  
U:  
V: Validation Architecture, Validation-First Approach, Validation Layer, Validation Mechanism, Validation Pipeline, Validation Report, Validation Governance, Versioning  
W: Working Memory  
Y:  
Z:  

### 4.3 Acronym Index

| Acronym | Expansion |
|---------|-----------|
| ADR | Architecture Decision Record |
| AI-OS | Artificial Intelligence Operating System |
| ARB | Architecture Review Board |
| CLI | Command Line Interface |
| CPU | Central Processing Unit |
| MCP | Model Context Protocol |
| RAM | Random Access Memory |
| SDLC | Software Development Lifecycle |
| TLS | Transport Layer Security |

### 4.4 Deprecated Terminology

| Deprecated Term | Preferred Replacement | Notes |
|-----------------|----------------------|-------|
| Hermes Kernel | Reference Runtime (Hermes) | "Hermes Kernel" refers specifically to the orchestration core; "Reference Runtime" includes the full compliance implementation |
| Core AI Service | AI Agency Service | Previous naming used in early architectural phases |
| Knowledge Base | Engineering Intelligence | More specific term for organizational knowledge storage |
| Skill Library | Skills Ecosystem | "Ecosystem" encompasses registry, catalog, discovery, governance, and development aspects |
| MCP Interface | Model Context Protocol (MCP) | Full protocol name preferred over interface shorthand |
| Validation Framework | Validation Architecture | "Architecture" better encompasses the comprehensive layered framework |
| Event System | EventBus | Specific component name preferred over general system reference |

### 4.5 Naming Conventions

**Component Names**: Use PascalCase for core subsystems (e.g., Core Manager, Capability Manager, EventBus, StateManager)  
**Interfaces and Protocols**: Use PascalCase with meaningful suffixes (e.g., Model Context Protocol, Software Development Lifecycle)  
**Configuration Parameters**: Use snake_case for keys in configuration files (e.g., max_token_budget, retry_timeout_ms)  
**File Names**: Use kebab-case for markdown and documentation files (e.g., architecture-decision-record.md, engineering-service-guide.md)  
**Code Identifiers**: Follow the naming conventions of the implementation language while maintaining semantic clarity and AI-OS domain relevance  
**Acronyms**: Expand on first use in documents, then use the acronym consistently throughout the document  
**Terms**: Use precise, unambiguous terminology that reflects AI-OS-specific meanings rather than generic software engineering definitions  
**Cross References**: Use [[double brackets]] for internal references to other glossary terms to enable navigation and relationship understanding  

### 4.6 Concept Ownership Matrix

| Concept | Primary Owning Document | Secondary References |
|---------|-------------------------|----------------------|
| Architecture Specification | SPECIFICATIONS/parts/.*_overview.md | AI_OS_MASTER_CONTEXT.md, VERSION_HISTORY.md |
| Hermes Kernel / Reference Runtime | AI_OS_MASTER_CONTEXT.md Section 6, SPECIFICATIONS/part1_hermes_kernel.md | ENGINEERING_PRINCIPLES.md, IMPLEMENTATION_GUIDE.md |
| Core Managers (9) | AI_OS_MASTER_CONTEXT.md Section 6, SPECIFICATIONS/part2_core_managers.md | AI_AGENCY.md, MEMORY_ARCHITECTURE.md |
| AI Agency Service | AI_AGENCY.md, SPECIFICATIONS/part4_service_framework.md | AI_OS_MASTER_CONTEXT.md, ENGINEERING_PRINCIPLES.md |
| Memory Architecture | MEMORY_ARCHITECTURE.md, SPECIFICATIONS/part8_memory_architecture.md | AI_OS_MASTER_CONTEXT.md, VALIDATION_ARCHITECTURE.md |
| Skills Ecosystem | SKILLS_ECOSYSTEM.md, SPECIFICATIONS/part9_skills_ecosystem.md | AI_OS_MASTER_CONTEXT.md, AI_AGENCY.md |
| MCP Ecosystem | MCP_ECOSYSTEM.md, SPECIFICATIONS/part10_mcp_ecosystem.md | AI_OS_MASTER_CONTEXT.md, AI_AGENCY.md |
| Repository Ecosystem | REPOSITORY_ECOSYSTEM.md, SPECIFICATIONS/part11_repository_ecosystem.md | AI_OS_MASTER_CONTEXT.md, ENGINEERING_PRINCIPLES.md |
| Engineering Services (8) | ENGINEERING_PRINCIPLES.md, SPECIFICATIONS/part3_engineering_services.md | AI_OS_MASTER_CONTEXT.md, IMPLEMENTATION_GUIDE.md |
| Validation Architecture | VALIDATION_ARCHITECTURE.md, SPECIFICATIONS/part15_validation_architecture.md | AI_OS_MASTER_CONTEXT.md, ENGINEERING_PRINCIPLES.md |
| Observability & Telemetry | SPECIFICATIONS/part12_observability_telemetry.md | AI_OS_MASTER_CONTEXT.md, VALIDATION_ARCHITECTURE.md |
| Fault Tolerance & Recovery | SPECIFICATIONS/part13_fault_tolerance_recovery.md | AI_OS_MASTER_CONTEXT.md, VALIDATION_ARCHITECTURE.md |
| Goal-Driven Execution | SPECIFICATIONS/part14_goal_driven_agentic.md | AI_OS_MASTER_CONTEXT.md, AI_AGENCY.md |
| Learning Architecture | SPECIFICATIONS/part19_learning_architecture.md | AI_OS_MASTER_CONTEXT.md, MEMORY_ARCHITECTURE.md |
| Configuration System | SPECIFICATIONS/part5_configuration_system.md | AI_OS_MASTER_CONTEXT.md, ENGINEERING_PRINCIPLES.md |
| Event System | SPECIFICATIONS/part6_event_system.md | AI_OS_MASTER_CONTEXT.md, ALL SERVICE DOCUMENTS |
| Service Framework | SPECIFICATIONS/part4_service_framework.md | AI_OS_MASTER_CONTEXT.md, ALL SERVICE DOCUMENTS |
| Architecture Decision Record (ADR) | ARCHITECTURE_DECISIONS.md | AI_OS_MASTER_CONTEXT.md, VALIDATION_ARCHITECTURE.md |
| Conformance | ENGINEERING_PRINCIPLES.md, SPECIFICATIONS/part1_validation_and_conformance.md | IMPLEMENTATION_GUIDE.md, ARCHITECTURE_DECISIONS.md |

## 5. Conclusion

This AI-OS Architecture Reference Dictionary provides the authoritative, canonical definitions for every architectural term used in the AI-OS ecosystem. By organizing terms into logical architectural domains, providing structured metadata for major concepts, ensuring precise AI-OS-focused definitions, maintaining strict specification alignment, improving cross-references with precise document ownership, enhancing navigation through multiple indices, expanding terminology from all project-knowledge documents, and employing professional reference tables, this document functions as the definitive reference manual for AI-OS terminology.

The dictionary ensures consistent understanding and communication across all stakeholders while preserving implementation independence, technology neutrality, and architectural integrity. As the single source of truth for AI-OS architectural terminology, it enables precise communication, reduces ambiguity, and supports conformance to the frozen AI-OS Architecture Specification (Parts 1-15).

*Document Version: 1.0.0*  
*Last Updated: 2026-08-06*  
*Status: ACTIVE - Authoritative Source for AI-OS Architectural Terminology*  
*Next Review: 2026-09-06*