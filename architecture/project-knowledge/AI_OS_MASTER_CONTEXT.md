# AI-OS Master Context Document

## Document Overview

This document serves as the definitive source of truth for the AI-OS (Artificial Intelligence Operating System) architecture. It consolidates the essential architectural concepts, principles, and current state to provide engineers and AI models with a comprehensive understanding of the system. This document should be read in conjunction with the detailed specification parts (Parts 1-15), ecosystem documents, and implementation guides for complete understanding.

## Table of Contents
1. [Introduction](#introduction)
2. [Core Architectural Philosophy](#core-architectural-philosophy)
3. [System Overview](#system-overview)
4. [Hermes Kernel Architecture](#hermes-kernel-architecture)
5. [Core Managers](#core-managers)
6. [Engineering Services](#engineering-services)
7. [Service Framework](#service-framework)
8. [Configuration System](#configuration-system)
9. [Event System](#event-system)
10. [AI Agency and Governance](#ai-agency-and-governance)
11. [Memory Architecture](#memory-architecture)
12. [Skills Ecosystem](#skills-ecosystem)
13. [MCP Ecosystem](#mcp-ecosystem)
14. [Repository Ecosystem](#repository-ecosystem)
15. [Observability & Telemetry](#observability--telemetry)
16. [Fault Tolerance & Recovery](#fault-tolerance--recovery)
17. [Goal-Driven Execution & Agentic Systems](#goal-driven-execution--agentic-systems)
18. [Validation Architecture](#validation-architecture)
19. [Learning Architecture](#learning-architecture)
20. [Runtime Architecture & Deployment](#runtime-architecture--deployment)
21. [Engineering Principles](#engineering-principles)
22. [Current Status & Roadmap](#current-status--roadmap)
23. [Migration & Compatibility](#migration--compatibility)
24. [Glossary of Key Terms](#glossary-of-key-terms)

---

## Introduction

This document provides the definitive context for AI-OS (Artificial Intelligence Operating System). It distinguishes between:

- **AI-OS Architecture Specification**: The frozen normative specification defining what AI-OS must be (Parts 1-15)
- **Reference Runtime (Hermes)**: The canonical Python implementation demonstrating specification compliance  
- **Reference Implementation**: Specific implementations of core capabilities (e.g., AI Agency Service)
- **Production Implementations**: Deployments conforming to the specification (may differ from reference)

AI-OS is an architectural specification and reference implementation for an artificial intelligence operating system designed to enable autonomous, goal-driven engineering workflows. Originating from the Hermes kernel concept, AI-OS has evolved from a product-focused implementation to a platform/reference architecture that emphasizes specification-driven development, ecosystem extensibility, and implementation independence.

The system is designed to orchestrate complete software development lifecycle (SDLC) processes through event-driven AI agents operating under structured governance, with built-in observability, fault tolerance, and continuous learning capabilities.

### Related Documents
- [AI-OS Architecture Specification, Part 0: Overview](./specifications/part0_overview.md)
- [AI-OS Architecture Specification, Part 1: Hermes Kernel](./specifications/part1_hermes_kernel.md)
- [AI-OS Architecture Specification, Part 2: Core Managers](./specifications/part2_core_managers.md)
- [AI-OS Architecture Specification, Part 3: Engineering Services](./specifications/part3_engineering_services.md)
- [AI-OS Architecture Specification, Part 4: Service Framework](./specifications/part4_service_framework.md)
- [AI-OS Architecture Specification, Part 5: Configuration System](./specifications/part5_configuration_system.md)
- [AI-OS Architecture Specification, Part 6: Event System](./specifications/part6_event_system.md)
- [AI-OS Architecture Specification, Part 7: AI Agency and Governance](./specifications/part7_ai_agency_governance.md)
- [AI-OS Architecture Specification, Part 8: Memory Architecture](./specifications/part8_memory_architecture.md)
- [AI-OS Architecture Specification, Part 9: Skills Ecosystem](./specifications/part9_skills_ecosystem.md)
- [AI-OS Architecture Specification, Part 10: MCP Ecosystem](./specifications/part10_mcp_ecosystem.md)
- [AI-OS Architecture Specification, Part 11: Repository Ecosystem](./specifications/part11_repository_ecosystem.md)
- [AI-OS Architecture Specification, Part 12: Observability & Telemetry](./specifications/part12_observability_telemetry.md)
- [AI-OS Architecture Specification, Part 13: Fault Tolerance & Recovery](./specifications/part13_fault_tolerance_recovery.md)
- [AI-OS Architecture Specification, Part 14: Goal-Driven Execution & Agentic Systems](./specifications/part14_goal_driven_agentic.md)
- [AI-OS Architecture Specification, Part 15: Validation Architecture](./specifications/part15_validation_architecture.md)
- [Hermes Reference Implementation Guide](./reference-implementation/hermes_guide.md)
- [Production Deployment Guide](./deployment/production_guide.md)
- [Ecosystem Contribution Guidelines](./ecosystem/contribution_guidelines.md)

### Prerequisites
- Familiarity with event-driven architecture concepts
- Understanding of autonomous agent systems
- Basic knowledge of software development lifecycle (SDLC) processes
- Experience with microservices and distributed systems (helpful but not required)

### Read Next
For implementation details, refer to the Hermes Reference Implementation Guide.
For specification compliance information, see the Architecture Review Board documentation.
For extending AI-OS through Skills, MCP, or Repository ecosystems, see the Ecosystem Contribution Guidelines.

---

## Core Architectural Philosophy

AI-OS is guided by these fundamental architectural principles:

### 1. **Event-First Communication Principle**
All inter-component communication occurs exclusively through the EventBus (post-initialization), enabling observability, loose coupling, and replay debugging capabilities.

### 2. **Kernel as Pure Orchestrator**
The Hermes Kernel contains zero domain logic, serving only as an orchestration core that manages core components and capability managers.

### 3. **Capability Manager Ownership**
The kernel instantiates and owns exactly nine (9) Core Managers that provide cross-cutting capabilities (memory, LLM routing, tool management, etc.).

### 4. **Fixed Component Counts**
Architectural stability is maintained by fixing the kernel at precisely four (4) Core Components and nine (9) Core Managers, with variability handled through extension points.

### 5. **Specification/Implementation Separation**
AI-OS distinguishes between the architecture specification (what the system must be) and any particular implementation (how it is built), enabling technology neutrality.

### 6. **Validation-First Execution**
All agentic operations undergo pre-execution, during-execution, and post-execution validation to ensure safety, correctness, and goal alignment.

### 7. **Ecosystem-Centric Evolution**
Extensibility is achieved through formalized ecosystems (Skills, MCP, Repository) with discovery mechanisms, versioning, and governance models.

### 8. **Goal-Driven & Agentic Evolution**
The system supports autonomous agentic behavior with self-looping, reflection, and adaptive planning to handle ambiguous engineering goals.

### 9. **Human-Governed AI**
AI agents operate under Council governance structures with human oversight capabilities (FinalJudge) for critical decisions.

### 10. **Deterministic Recovery & Long-Term Maintainability**
Built-in checkpointing, retry budgets, and failure recovery mechanisms ensure system reliability and maintainability over time.

## System Overview

AI-OS follows a layered architectural model:

```
�┌─────────────────────────────────�┐
│         Application Layer       │
│  (Domain-specific services,     │
│   custom engineering workflows) │
�└─────────────────────�┬───────────�┘
                      │
�┌─────────────────────�▼───────────�┐
│         Platform Layer          │
│  (Engineering Services,         │
│   Facade Services, CLI)         │
�└─────────────────────�┬───────────�┘
                      │
�┌─────────────────────�▼───────────�┐
│       Kernel Layer (Hermes)     │
│  (EventBus, StateManager,       │
│   WorkflowManager, ResourceMgr) │
�└─────────────────────�┬───────────�┘
                      │
�┌─────────────────────�▼───────────�┐
│   Capability Managers (9)       │
│  (Memory, ModelRouter, ToolMgr, │
│   Storage, Context, Agent,      │
│   Retry, Checkpoint, RootCause, │
│   Council, AI Agency)           │
�└─────────────────────�┬───────────�┘
                      │
�┌─────────────────────�▼───────────�┐
│        Extension Points         │
│  (Skills, MCP, Repository,      │
│   Custom Events, Memory Backends)│
�└─────────────────────────────────�┘
```

## Hermes Kernel Architecture

The Hermes Kernel is the orchestration core of AI-OS, consisting of exactly four (4) Core Components:

### 1. **EventBus**
The sole communication substrate for all inter-component communication. Enforces the Event-First Communication Principle, providing:
- Immutable events with correlation and causation IDs
- Schema versioning and evolution mechanisms
- Support for synchronous and asynchronous event handling
- Event interception capabilities for observability and testing

### 2. **StateManager**
Centralized state persistence with scoping capabilities:
- Hierarchical state organization (global, workflow, session, agent scopes)
- Transactional state updates with rollback capabilities
- State snapshotting for checkpointing and recovery
- Query interfaces for state inspection

### 3. **WorkflowManager**
Orchestration of engineering processes through:
- Workflow definition and execution engine
- Dependency management and topological ordering
- Parallel and sequential workflow execution patterns
- Workflow state tracking and progress reporting

### 4. **ResourceManager**
Resource allocation and quota management:
- CPU, memory, and token budget tracking
- Agent and workflow resource quotas
- Resource reservation and release mechanisms
- Usage monitoring and enforcement

## Core Managers

The Hermes Kernel owns exactly nine (9) Core Managers, each exposed via global singleton accessors:

### 1. **MemoryManager**
Manages the five-tier memory system:
- Working Memory: Short-term, session-scoped, volatile
- Claude Memory: Session persistence across restarts
- Engineering Intelligence: Long-term learnings, patterns, decisions
- Obsidian: Knowledge vault integration for documentation
- Graphify: Knowledge graph for entity relationships and reasoning

### 2. **ModelRouter**
Provider-agnostic LLM capability routing:
- Dynamic provider selection based on capability requirements
- Fallback chains for reliability
- Provider health monitoring and load balancing
- Capability-based abstraction over LLM provider SDKs

### 3. **ToolManager**
Tool registry, execution sandbox, and permission mediation:
- Tool discovery and registration
- Sandboxed execution environments
- Permission profiles and mediation
- Tool execution telemetry and monitoring

### 4. **StorageManager**
Persistence abstraction, schemas, and migrations:
- Structured data persistence with schema validation
- Migration frameworks for schema evolution
- Query interfaces and indexing capabilities
- Backup and recovery mechanisms

### 5. **ContextManager**
Conversation context, window management, and relevance scoring:
- Context window management and truncation strategies
- Relevance scoring for context selection
- Conversation history and summarization
- Multi-modal context handling

### 6. **AgentManager**
Agent spawning, lifecycle, communication, and quotas:
- Agent lifecycle management (spawn, monitor, terminate)
- Communication facilitation between agents
- Resource quota enforcement per agent
- Agent performance and usage tracking

### 7. **RetryManager**
Automatic retry with exponential backoff and budgets:
- Configurable retry budgets per task type
- Exponential backoff with jitter algorithms
- Dead letter queue for permanently failed tasks
- Integration with RootCauseManager for intelligent retry decisions

### 8. **CheckpointManager**
Workflow execution snapshots for recovery:
- Workflow state snapshotting at configurable intervals
- Selective checkpointing based on workflow criticality
- Fast recovery mechanisms from checkpoints
- Checkpoint pruning and storage management

### 9. **RootCauseManager**
Automated failure classification and recovery routing:
- Failure pattern recognition and classification
- Automated recovery procedure selection
- Escalation protocols for complex failures
- Integration with RetryManager for intelligent retry decisions

### 10. **CouncilManager**
Consensus mechanisms for AI governance:
- Multiple council types (Claude Council, LLM Council, etc.)
- Voting algorithms (MAJORITY, UNANIMOUS, WEIGHTED)
- Dissent escalation to human judges (FinalJudge)
- Audit trail generation for all governance decisions

### 11. **AIAgencyService**
AI agent lifecycle management and audit trails:
- Agent spawning with configurable autonomy levels
- Permission sandboxing and resource quotas
- Communication facilitation and monitoring
- Comprehensive audit logging of all agent actions
- Performance monitoring and resource usage tracking

## Engineering Services

AI-OS implements eight (8) event-driven Engineering Services that follow the SDLC phases:

### 1. **Planning Service**
- Goal decomposition and task breakdown
- Resource estimation and planning
- Risk assessment and mitigation planning
- Workflow initiation and coordination

### 2. **Coding Service**
- Code generation and implementation
- Syntax validation and basic correctness checks
- Code style enforcement and formatting
- Integration with version control systems

### 3. **Review Service**
- Code quality analysis and review
- Security vulnerability scanning
- Performance anti-pattern detection
- Review comment generation and disposition

### 4. **Testing Service**
- Test strategy development and test case generation
- Test execution and result analysis
- Coverage measurement and gap identification
- Test automation and continuous testing integration

### 5. **Deployment Service**
- Deployment planning and environment preparation
- Release management and version control
- Deployment execution and validation
- Rollback procedures and failure handling

### 6. **Operations Service**
- System monitoring and health checking
- Incident detection and response coordination
- Performance optimization and tuning
- Log aggregation and analysis

### 7. **Learning Service**
- Experience collection from completed workflows
- Pattern extraction and generalization
- Knowledge consolidation into Engineering Intelligence
- Skill generation from recurring patterns

### 8. **Memory Service**
- Long-term memory management and persistence
- Memory consolidation and optimization
- Cross-session knowledge retention
- Memory access control and security

## Service Framework

All services in AI-OS extend the BaseService contract, providing:
- Standardized lifecycle management (INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED)
- Dependency injection and topological initialization/shutdown
- Event-driven communication through emit()/subscribe() methods
- Configuration access and health check capabilities
- Standardized error handling and reporting
- Service discovery and registration mechanisms

## Configuration System

AI-OS employs a four-layer merge configuration system:
1. **Defaults Layer**: Built-in default values
2. **app.yaml Layer**: Application-specific configuration
3. **env.yaml Layer**: Environment-specific configuration
4. **Environment Variables Layer**: Runtime overrides

Configuration is immutable after the INITIALIZING phase, ensuring runtime stability. Schema versioning and migration paths are provided for configuration evolution.

## Event System

The Event System defines:
- **Event Types**: Strongly typed events with schema validation
- **Schemas**: Versioned event schemas with backward/forward compatibility
- **Routing**: Publish-subscribe pattern with filtering capabilities
- **Correlation/Causation**: Every event carries traceability IDs for end-to-end tracing
- **Versioning Strategy**: Clear evolution paths for event schemas with deprecation periods

## AI Agency and Governance

AI-OS implements structured AI governance through:

### Council Mechanisms
- **Claude Council**: Reviews AI agent proposals and architectural decisions
- **LLM Council**: Focuses on model selection, token budgeting, and safety
- **Specialized Councils**: Domain-specific governance bodies as needed
- **Voting Algorithms**: MAJORITY, UNANIMOUS, WEIGHTED consensus mechanisms
- **Human Oversight**: FinalJudge service provides veto and override capabilities

### AI Agency
- **Agent Lifecycle Management**: Spawning, monitoring, and terminating agents
- **Resource Quotas**: Configurable limits on CPU, memory, tokens, and concurrent agents
- **Permission Sandboxing**: Restricted execution environments with capability-based permissions
- **Audit Trails**: Comprehensive logging of all agent actions, decisions, and resource usage
- **Performance Monitoring**: Resource utilization, success rates, and behavioral analytics

## Memory Architecture

The five-tier memory system provides:

### 1. Working Memory
- Short-term, session-scoped storage for active context
- Volatile storage cleared on session end
- Optimized for rapid access during active processing

### 2. Claude Memory
- Session persistence across restarts and interruptions
- Stores conversation history and working state
- Enables seamless session resumption

### 3. Engineering Intelligence
- Long-term storage of learned patterns, decisions, and best practices
- Consolidated from workflow experiences and reflections
- Used to inform future planning and decision-making

### 4. Obsidian
- Knowledge vault integration for documentation and knowledge artifacts
- Structured storage of architectural decisions, design documents, and wikis
- Versioned knowledge artifacts with change tracking

### 5. Graphify
- Knowledge graph for entity relationships and reasoning
- Enables complex relationship traversal and inference
- Supports semantic queries and knowledge discovery

## Skills Ecosystem

The Skills Ecosystem provides reusable AI capabilities through:

### Discovery
- Central registry with search, filtering, and recommendation capabilities
- Skill metadata including descriptions, tags, and usage examples
- Compatibility checking against kernel and platform versions

### Versioning
- Semantic versioning (MAJOR.MINOR.PATCH) with dependency resolution
- Backward compatibility guarantees within major versions
- Clear deprecation and migration paths

### Sandboxing
- Standardized execution environments with configurable permission profiles
- Resource isolation and limits enforcement
- Security scanning and vulnerability assessment

### Composition
- Skill chaining for sequential execution
- Parallel execution patterns for independent skills
- Conditional workflows based on skill outcomes
- Skill parameterization and template mechanisms

### Governance
- Community curation and contribution processes
- Security scanning and vulnerability assessment
- Quality gates and certification programs
- Deprecation and retirement policies

### Development Kit
- Templates, testing frameworks, and documentation generators
- Local development and testing tools
- Packaging and distribution utilities

## MCP Ecosystem

The MCP (Model Context Protocol) Ecosystem enables external tool integration:

### Transports
- Standardized implementations for stdio, HTTP, WebSocket, and other transports
- Secure communication channels with authentication and encryption
- Flow control and backpressure mechanisms
- Connection pooling and reuse optimization

### Capabilities
- Well-defined capability profiles for common functions (file access, web search, code execution, etc.)
- Capability negotiation and discovery
- Granular permission models for capability access
- Capability versioning and evolution

### Security
- Standardized security profiles and permission models
- Authentication and authorization frameworks
- Audit logging of all MCP interactions
- Secure credential and secret management

### State Management
- Synchronization patterns for shared state between AI and external tools
- Conflict resolution strategies for concurrent access
- Consistency models and transaction support
- State persistence and recovery mechanisms

### Discovery
- Registry for finding and evaluating MCP servers
- Server metadata including capabilities, versions, and reliability metrics
- Health checking and monitoring capabilities
- Trust scoring and reputation systems

### Tool Certification
- Validation programs for MCP server compliance
- Test suites for capability verification
- Security assessment and penetration testing
- Certification badges and trust indicators

## Repository Ecosystem

The Repository Ecosystem enables sharing and reuse of engineering assets:

### Workflow Templates
- Reusable SDLC patterns for common project types (web applications, microservices, data pipelines, etc.)
- Parameterizable workflows with variable substitution
- Best practice guidance and standardization
- Domain-specific customization points

### Component Libraries
- Shareable services, managers, and extensions
- Versioned components with dependency management
- Compatibility testing and validation
- Documentation and usage examples

### Reference Architectures
- Proven solutions for specific domains (web, mobile, embedded, IoT, etc.)
- Architecture decision records and trade-off analyses
- Implementation guidelines and patterns
- Performance and scalability characteristics

### Best Practices
- Codified engineering guidelines and heuristics
- Architecture and design principles
- Coding standards and style guides
- Security and compliance frameworks

### Learning Materials
- Tutorials, examples, and educational content
- Getting started guides and onboarding materials
- Advanced topics and expert-level content
- Video demonstrations and interactive labs

### Community Hub
- Forums, chat, and collaboration spaces
- Knowledge sharing and question answering
- Contribution guidelines and processes
- Event calendars and community activities

## Observability & Telemetry

Built-in observability capabilities include:

### Metrics
- Counter, gauge, histogram, and summary metric types
- Custom metric definition and registration
- Predefined metrics for kernel operations, services, and agentic behavior
- Export to multiple backends (Prometheus, Datadog, etc.)

### Tracing
- OpenTelemetry-compatible distributed tracing
- Automatic instrumentation of kernel operations and service calls
- Manual instrumentation points for custom tracing
- Trace context propagation across asynchronous boundaries
- Export to tracing backends (Jaeger, Zipkin, Tempo)

### Logging
- Structured logging with consistent field schemas
- Correlation ID propagation across all log entries
- Configurable log levels and output formats
- Structured fields for service, agent, workflow, and operation context
- Integration with log aggregation systems (ELK, Splunk, etc.)

### Health Checks
- Liveness and readiness probes for all services
- Deep health checks including dependency validation
- Configurable health check intervals and timeouts
- Health status reporting and alerting integration

## Fault Tolerance & Recovery

AI-OS implements comprehensive fault tolerance through:

### Retry Mechanisms
- Configurable retry budgets per operation type
- Exponential backoff with jitter algorithms
- Selective retry based on error classification
- Dead letter queue for permanently failed operations

### Checkpointing
- Workflow execution snapshots at configurable intervals
- Selective checkpointing based on workflow criticality and cost
- Fast recovery mechanisms with minimal data loss
- Checkpoint storage optimization and pruning

### Failure Classification
- TRANSIENT: Temporary failures safe to retry
- DEGRADED: Reduced functionality but operational state
- CRITICAL: Requires immediate attention but not system-terminating
- FATAL: System-terminating requiring restart or intervention

### Recovery Routing
- Automatic selection of recovery procedures based on failure type
- Escalation paths for complex or repeated failures
- Integration with RootCauseManager for intelligent decisions
- Manual intervention and override capabilities

### Deterministic Recovery
- Recovery point objectives (RPO) and recovery time objectives (RTO)
- Consistent recovery state across distributed components
- Verification of recovery completeness and correctness
- Recovery testing and validation mechanisms

## Goal-Driven Execution & Agentic Systems

Modern AI-OS transcends predefined workflows through:

### Goal-Driven Execution Engine
- Accepts high-level engineering goals (e.g., "implement user authentication with OAuth 2.0")
- AI-powered planning that decomposes goals into actionable work
- Dynamic plan adaptation based on intermediate results and feedback
- Continues until goal validation criteria are met or intervention requested

### Autonomous Agentic Behavior
- Configurable autonomy levels (supervised, guided, autonomous)
- Self-initiated task creation based on goal progress and obstacle detection
- Inter-agent collaboration and negotiation for complex objectives
- Resource-aware operation with automatic quota management
- Environment awareness and context preservation across sessions

### Self-Looping & Reflection
- Continuous observation of own behavior and outcomes
- Automated retrospectives after significant actions or milestones
- Pattern extraction from successes and failures
- Hypothesis generation about improved approaches
- Knowledge consolidation into Engineering Intelligence memory

### Validation-First Execution
- Pre-execution validation of plans, resource availability, and safety constraints
- Continuous verification during execution (process and intermediate results)
- Post-execution validation against goal criteria and quality standards
- Automatic rollback or correction when validation fails
- Audit trail of all validation attempts and outcomes

## Validation Architecture

The validation architecture ensures system correctness and safety through:

### Pre-Execution Validation
- Goal feasibility and resource availability assessment
- Safety constraint checking and risk assessment
- Plan correctness and completeness validation
- Dependency and prerequisite verification

### During-Execution Validation
- Process compliance and procedural validation
- Intermediate result correctness checking
- Resource utilization monitoring and anomaly detection
- Deviation detection from expected execution paths

### Post-Execution Validation
- Goal criterion verification and outcome assessment
- Quality standard compliance checking
- Regression detection and prevention
- Side-effect and unintended consequence identification

### Validation Mechanisms
- Automated validation scripts and checklists
- Human-in-the-loop validation for complex judgments
- Adversarial validation to challenge assumptions
- Property-based validation for invariant checking
- Statistical validation for probabilistic outcomes

## Learning Architecture

The learning architecture enables continuous improvement through:

### Experience Collection
- Structured capture of workflow execution data
- Decision points, actions taken, and outcomes observed
- Contextual information and environmental factors
- Performance metrics and resource utilization

### Pattern Extraction
- Statistical analysis for pattern recognition
- Sequence mining for temporal patterns
- Association rule learning for correlated events
- Clustering for similarity-based pattern grouping

### Knowledge Consolidation
- Extraction of generalizable principles from specific experiences
- Integration with existing knowledge in Engineering Intelligence
- Conflict resolution for contradictory knowledge
- Confidence tracking and knowledge decay mechanisms

### Skill Generation
- Identification of recurring patterns suitable for skill creation
- Automatic skill template generation from workflow patterns
- Parameterization and generalization of specific implementations
- Documentation and usage example generation

### Model Improvement
- Fine-tuning triggers based on accumulated experience
- Prompt engineering improvements from successful patterns
- Routing optimization based on provider performance
- Architecture evolution proposals from systemic patterns

## Runtime Architecture & Deployment

AI-OS supports multiple deployment models:

### Reference Runtime (Hermes)
- Python 3.12+ implementation using asyncio
- Modular architecture with clear separation of concerns
- Production-quality implementation with comprehensive testing
- Extensible through plugin system for skills, MCPs, and memory backends

### Deployment Options
- Single-process deployment for development and testing
- Containerized deployment using Docker for isolation
- Orchestrated deployment using Kubernetes for scaling
- Hybrid deployments combining local and cloud components

### Technology Stack
- Core language: Python 3.12+
- Framework dependencies: Typer (CLI), Rich (terminal formatting), Pydantic (data validation), PyYAML (configuration)
- Observability: OpenTelemetry SDK and API
- Testing: Pytest, coverage.py, and property-based testing libraries
- Development: Ruff (linting), MyPy (type checking), and pre-commit hooks

### Extension Mechanisms
- Plugin system for skills and MCP transports
- Custom memory backend registration
- Extension point interfaces for variability
- Versioned contracts with clear evolution paths

## Engineering Principles

AI-OS development follows these engineering principles:

### 1. **Architectural Integrity**
- Preserve specification conformance as the highest priority
- Respect architectural invariants and boundaries
- Prevent architectural erosion through disciplined development
- Maintain separation of concerns and modularity

### 2. **Verification-First Development**
- Write tests before implementation (test-driven development)
- Validate assumptions through experimentation and measurement
- Implement comprehensive error handling and edge case coverage
- Perform regular architectural conformance checking

### 3. **Observability by Design**
- Implement structured logging with correlation IDs from the start
- Export metrics for all significant operations
- Instrument code for distributed tracing
- Design for monitorability and debuggability

### 4. **Security and Privacy**
- Implement least privilege access controls
- Validate and sanitize all inputs
- Protect sensitive data through encryption and access controls
- Conduct regular security assessments and penetration testing

### 5. **Performance and Efficiency**
- Optimize for resource utilization (CPU, memory, tokens)
- Implement caching strategies where appropriate
- Use asynchronous patterns for I/O-bound operations
- Profile performance and identify bottlenecks systematically

### 6. **Maintainability and Clarity**
- Write self-documenting code with clear intent
- Follow consistent coding standards and style guides
- Refactor regularly to prevent technical debt accumulation
- Document complex algorithms and non-obvious behavior

### 7. **Ecosystem Awareness**
- Design extension points with clear contracts
- Maintain backward compatibility within version constraints
- Provide clear documentation for consumers and contributors
- Participate in ecosystem governance and quality processes

## Current Status & Roadmap

### Current Status (as of 2026-08-06)
- **Architecture Specification**: Parts 0-12+ are FROZEN normative specifications
- **Reference Implementation**: Hermes Runtime working toward v1.0 conformance (current v0.1.x)
- **Ecosystems**: Skills, MCP, and Repository ecosystems establishing governance models
- **Conformance Testing**: Automated test suites validating specification adherence
- **Governance**: Architecture Review Board (ARB) active for specification evolution
- **Documentation**: Comprehensive documentation preserved and maintained

### Near-Term Roadmap (v1.1 - v1.3)
- Enhanced distribution: First-class support for distributed EventBus and microservices
- Improved goal reasoning: More sophisticated planning and risk assessment
- Standardized agent interfaces: Common protocols for multi-agent collaboration
- Evolutionary architecture: Mechanisms for the specification to evolve itself
- Performance profiling: Built-in optimization guidance based on execution patterns

### Mid-Term Exploration (v2.0)
- Formal verification: Mechanisms for proving architectural properties
- Adaptive specification: Parts that can evolve based on usage patterns and feedback
- Pluggable kernels: Alternative kernel implementations for different domains
- Formal marketplace: Discovery, trust, and transaction mechanisms for ecosystems
- Cognitive architecture: Deeper integration of cognitive science principles

### Long-Term Vision
- Ubiquitous AI Engineering: AI-OS as the invisible substrate for all engineering work
- Self-Evolving Systems: Architectures that improve themselves through use
- Universal Engineering Language: Common representation for engineering intent across domains
- Human-AI Symbiosis: Seamless partnership where each party performs to their strengths
- Planetary-Scale Engineering: Coordinated effort addressing global challenges through AI-OS

## Migration & Compatibility

### From Historical Implementations to Current Specification

| Area | Historical Approach | Current Specification Approach | Migration Guidance |
|------|-------------------|------------------------------|-------------------|
| Kernel Instantiation | Multiple instances possible | Singleton enforced (create() throws on second call) | Ensure single kernel instance per process; remove accidental duplicates |
| Component Counts | Variable (3-5 CC, 6-11 CM) | Exactly 4 Core Components, 9 Core Managers | Remove non-standard components; use extension points for variability |
| Initialization Order | Ad-hoc, some parallel | Strict phases (0→3 sequential, 4→8 parallel-within-phase) | Refactor dependencies to match specification phase assignments |
| Configuration | Runtime mutation permitted | Immutable after INITIALIZING phase | Move all configuration to startup; use four-layer merge strategy |
| Communication | Mixed direct calls and events | EventBus only (post-initialization) | Replace service calls with event emission/subscription patterns |
| Failure Handling | Try-catch, inconsistent handling | Event-based classification (TRANSIENT/DEGRADED/CRITICAL/FATAL) | Migrate to event-based failure publishing and handling |
| State Machine | Implicit 3-state model | Explicit 5-state FSM (UNINITIALIZED→INITIALIZED→RUNNING→SHUTTING_DOWN→TERMINATED) | Implement full state machine with transition events |
| Extension Points | Ad-hoc mechanisms | Formalized, versioned, governed ecosystems | Migrate to official extension points; register through proper channels |
| Observability | Bolted-on logging/metrics | Built-in structured logging, correlation IDs, health checks | Enhance to meet specification requirements; remove redundant instrumentation |

### Backward Compatibility Guarantees
1. **Specification Versioning**: Clear, semantic versioning of the Architecture Specification
2. **Interface Stability**: Defined evolution paths for interfaces with deprecation periods
3. **Conformance Levels**: Multiple compliance levels (L1-L4) allowing gradual adoption
4. **Extension Point Stability**: Core extension mechanisms preserved across versions
5. **Reference Runtime Hermes**: Continues as compliance target for each specification version
6. **Migration Documentation**: Explicit guidance for moving between specification versions

## Glossary of Key Terms

- **AI-OS**: Artificial Intelligence Operating System - the architectural specification and reference implementation
- **Hermes Kernel**: The orchestration core of AI-OS consisting of 4 Core Components and 9 Core Managers
- **EventBus**: The sole communication substrate enforcing event-first communication
- **Core Components**: The four fundamental elements of the Hermes Kernel (EventBus, StateManager, WorkflowManager, ResourceManager)
- **Core Managers**: The nine capability managers owned by the Hermes Kernel
- **Engineering Services**: The eight event-driven services covering SDLC phases (Planning through Memory)
- **Facade Services**: Thin event-driven bridges over Kernel Capability Managers
- **Extension Points**: Formalized mechanisms for variability (Skills, MCP, Repository, Custom Events, etc.)
- **Goal-Driven Execution**: Accepting high-level goals and dynamically adapting plans to achieve them
- **Agentic Behavior**: Autonomous agent operation with self-looping, reflection, and collaboration
- **Validation-First Execution**: Pre-, during-, and post-execution validation of all operations
- **Five-Tier Memory**: Working, Claude, Engineering Intelligence, Obsidian, and Graphify memory systems
- **MCP**: Model Context Protocol for standardized external tool integration
- **Skills Ecosystem**: Reusable AI capability packages with discovery, versioning, and sandboxing
- **Repository Ecosystem**: Shareable engineering assets including workflow templates, component libraries, and reference architectures
- **Conformance Level**: Compliance tiers (L1-L4) specifying degree of specification adherence
- **Architecture Review Board (ARB)**: Governing body responsible for specification evolution and change approval
- **FinalJudge**: Human oversight capability providing veto and override rights over AI agent decisions
- **Council Mechanisms**: Governance structures for AI decision-making including Claude Council and LLM Council
- **Retry Budget**: Configurable limits on retry attempts for different operation types
- **Checkpointing**: Workflow execution snapshotting for recovery and fault tolerance
- **RootCauseManager**: Automated failure classification and recovery routing system
- **ModelRouter**: Provider-agnostic LLM capability routing system
- **ToolManager**: Tool registry, execution sandbox, and permission mediation system

---

*Document Version: 1.0.0 (Master Context)*  
*Last Updated: 2026-08-06*  
*Status: ACTIVE - Definitive Source of Truth for AI-OS Architecture*  
*Next Review: 2026-09-06*