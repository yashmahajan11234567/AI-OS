# AI-OS Architecture Decision Records (ADR)

This document serves as the permanent Architecture Decision Record (ADR) index for AI-OS. It captures the major irreversible architectural decisions that define the AI-OS Hermes Kernel v1.0 architecture.

Each ADR follows a consistent format:
- **ADR Number**: Sequential identifier
- **Title**: Concise description of the decision
- **Context**: The situation motivating the decision
- **Problem**: The specific issue to be addressed
- **Alternatives Considered**: Other options evaluated
- **Decision**: The chosen approach
- **Rationale**: Why this decision was made
- **Trade-offs**: Benefits and drawbacks accepted
- **Consequences**: Impact on the system
- **Current Status**: Whether the decision is active, superseded, or deprecated
- **Related Parts**: References to architecture specification parts (Part 1–15)

---

## ADR 001: Event-First Communication Principle

**Title**: All inter-component communication MUST occur via the EventBus

**Context**: AI-OS is designed as a distributed, observable orchestration system where components need to communicate without tight coupling.

**Problem**: Traditional direct service-to-service calls create tight coupling, hinder observability, prevent replay/debugging, and complicate failure handling.

**Alternatives Considered**:
- Direct method calls between services
- Shared mutable state for communication
- Request/response RPC mechanisms
- Message queues with point-to-point channels

**Decision**: All inter-component communication MUST occur via the EventBus. There are NO direct service-to-service calls, NO synchronous RPC, and NO shared mutable state outside StateManager.

**Rationale**: 
- Decouples component lifecycles
- Enables observability through event tracing
- Enables replay/debugging capabilities
- Supports future distributed evolution (v2.0)
- Provides uniform failure handling through events

**Trade-offs**:
- Increased latency compared to direct calls
- Requires event-driven design mindset
- Additional complexity in event serialization/deserialization

**Consequences**:
- All services must extend BaseService and use emit()/subscribe()
- EventBus becomes the central communication substrate
- Failure handling must be event-based
- Observability is built-in through correlation/causation IDs
- Enables event sourcing and audit trails

**Current Status**: Active

**Related Parts**: Part 0 (Principles), Part 2 (Event System), Part 3 (Kernel), Part 5-6 (Services), Part 12 (Observability)

---

## ADR 002: Kernel as Pure Orchestrator

**Title**: The Kernel MUST own exactly four Core Components and MUST NOT contain domain logic

**Context**: The Hermes Kernel needs to provide stable orchestration primitives while allowing domain logic to evolve independently.

**Problem**: Mixing orchestration logic with domain logic creates tight coupling, reduces kernel stability, and makes it difficult to evolve either aspect independently.

**Alternatives Considered**:
- Kernel containing both orchestration and domain logic
- Multiple specialized kernels for different domains
- Plugin-based architecture for extending kernel functionality

**Decision**: The Kernel MUST own exactly four (4) Core Components (EventBus, StateManager, WorkflowManager, ResourceManager) and MUST NOT contain domain logic (planning, coding, review, testing, deployment, operations, learning).

**Rationale**:
- Kernel stability equals system stability
- Domain logic evolves rapidly; orchestration primitives evolve slowly
- Clear separation of concerns enables independent evolution
- Prevents kernel from becoming a "god object"

**Trade-offs**:
- Requires careful interface design between kernel and services
- Slightly more indirection in service-to-service communication
- Kernel functionality is limited to orchestration primitives

**Consequences**:
- Kernel source files must not import any service modules
- Nine Capability Managers are kernel-owned but provide cross-cutting capabilities
- Services implement all domain-specific logic
- Kernel provides lifecycle management and coordination only

**Current Status**: Active

**Related Parts**: Part 0 (Principle 2), Part 3 (Kernel), Part 4 (Capability Managers), Part 5-6 (Engineering Services)

---

## ADR 003: Capability Manager Ownership

**Title**: The nine Capability Managers are instantiated, owned, and lifecycle-managed by the Kernel

**Context**: Capabilities like retry, checkpoint, memory, and skills are cross-cutting concerns that need consistent system-wide policies.

**Problem**: Allowing services to instantiate their own capability managers leads to inconsistent policies, duplicated functionality, and configuration drift.

**Alternatives Considered**:
- Services instantiate their own capability managers
- Dependency injection framework for capability managers
- Singleton pattern with lazy initialization

**Decision**: The nine Capability Managers (Retry, Checkpoint, RootCause, Memory, Skill, MCP, Council, AI Agency, ModelRouter) are instantiated, owned, and lifecycle-managed by the Kernel and exposed via Global Singleton Accessors.

**Rationale**:
- Central ownership prevents duplication and ensures consistent policy
- Capabilities are cross-cutting infrastructure concerns
- Kernel can manage lifecycle and dependencies properly
- Global accessors provide system-wide availability

**Trade-offs**:
- Creates global state (managed through explicit accessors)
- Requires kernel to know about all capability types
- Capability managers cannot have service-specific configurations easily

**Consequences**:
- Exactly one instance of each capability manager exists
- Global singleton accessors provide process-global access
- Services must use capability managers via accessors
- Kernel controls initialization order and lifecycle
- Enables mocking for testing via setter functions

**Current Status**: Active

**Related Parts**: Part 0 (Principle 3), Part 3.4 (Global Accessors), Part 4 (Capability Managers)

---

## ADR 004: Global Singleton Accessors

**Title**: The 13 get_xxx()/set_xxx() accessor pairs are architectural fixtures, not implementation shortcuts

**Context**: The system needs deterministic access to kernel components and capability managers for coordination and testing.

**Problem**: Ad-hoc access patterns create hidden dependencies, make testing difficult, and obscure system architecture.

**Alternatives Considered**:
- Dependency injection container
- Service locator pattern
- Direct instantiation by consumers
- Static class members

**Decision**: The 13 global accessor pairs are architectural fixtures that MUST be documented, initialized in deterministic order, and testable via set_xxx(mock).

**Rationale**:
- Dependency injection frameworks add complexity without benefit in single-process kernel
- Explicit globals are testable, debuggable, and auditable
- Deterministic initialization order prevents race conditions
- Stady interface enables mocking for testing

**Trade-offs**:
- Global state considerations (mitigated through explicit architecture)
- Requires discipline to maintain accessor contracts
- Initialization ordering complexity

**Consequences**:
- Part 3.4 specifies the complete registry and initialization order
- All accessors must be callable and documented
- Testing protocol requires set_xxx(mock) capability
- Accessors cannot be changed without ADR
- Enables straightforward testing with mocks

**Current Status**: Active

**Related Parts**: Part 0 (Principle 4), Part 3.4 (Global Singleton Accessors), Part 4 (Capability Managers)

---

## ADR 005: Event-Driven Services

**Title**: Every Service MUST extend BaseService, declare depends_on, subscribe in on_start(), emit typed Events, and MUST NOT call other services directly

**Context**: Services need a consistent lifecycle, dependency management, and communication model to enable composition and replacement.

**Problem**: Services with ad-hoc lifecycles, direct communication, and inconsistent event usage create an unreliable, non-composable system.

**Alternatives Considered**:
- Services with custom lifecycle methods
- Direct service-to-service communication
- Shared state coordination
- Hybrid event/direct communication

**Decision**: Every Service MUST extend BaseService, declare depends_on for its dependencies, subscribe to events in on_start(), emit typed Events for its outputs, and MUST NOT call other services directly.

**Rationale**:
- Uniform lifecycle enables topological start/stop
- Dependency declaration enables correct startup ordering
- Event-only communication enables loose coupling
- BaseService provides standard emit()/subscribe() helpers
- Enables service replacement without system changes

**Trade-offs**:
- Requires learning BaseService patterns
- Event design overhead for simple interactions
- Indirection for service-to-service communication

**Consequences**:
- ServiceRegistry validates depends_on DAG for acyclic dependencies
- Services communicate exclusively through EventBus
- Health checks and monitoring are standardized
- Services can be developed and tested in isolation
- Failure handling is uniform through event emission

**Current Status**: Active

**Related Parts**: Part 0 (Principle 5), Part 5-6 (Services), Part 3.3 (ServiceRegistry), Part 2 (Events)

---

## ADR 006: Engineering Service SDLC Pipeline

**Title**: The eight Engineering Services form a strict linear pipeline: Planning → Coding → Review → Testing → Deployment → Operations → Learning → Memory

**Context**: AI-OS needs to automate the full software development lifecycle while maintaining phase boundaries and enabling checkpointing.

**Problem**: Arbitrary service organization makes it difficult to enforce phase boundaries, implement checkpointing, and trace work through the SDLC.

**Alternatives Considered**:
- Fully parallel service execution
- Ad-hoc service organization based on current task
- Hierarchical service trees
- Circular service dependencies

**Decision**: The eight Engineering Services form a strict linear pipeline where each phase emits exactly one "Completed" event that triggers the next phase.

**Rationale**:
- Mirrors human SDLC processes engineers understand
- Enables checkpointing and phase-boundary recovery
- Supports learning and process improvement at phase boundaries
- Provides clear work progression tracking
- Enables workflow management through distinct phases

**Trade-offs**:
- Less flexibility for parallel execution within phases
- Requires workflow manager for intra-phase parallelism
- May not fit all development methodologies perfectly

**Consequences**:
- WorkflowManager handles parallel execution within phases
- Each service focuses on a single SDLC concern
- Phase transitions are explicit events
- Checkpoints can be taken at phase boundaries
- Learning service captures improvements for future iterations

**Current Status**: Active

**Related Parts**: Part 0 (Principle 6), Part 5-6 (Engineering Services), Part 3.2 (WorkflowManager), Part 13 (Recovery)

---

## ADR 007: Capability Facade Services

**Title**: The four Capability Facade Services MUST translate incoming Events into Manager calls and emit result Events, and MUST NOT contain business logic

**Context**: Services need access to capability managers but should not depend on the event system internally to keep managers pure and testable.

**Problem**: Direct service-to-manager coupling makes managers difficult to test and creates inconsistent event usage patterns.

**Alternatives Considered**:
- Services calling managers directly
- Managers depending on EventBus
- Hybrid approach with some direct calls
- Services implementing their own capability logic

**Decision**: The four Capability Facade Services (SkillService, CouncilService, MCPService, MemoryService) MUST translate incoming Events into Manager calls and emit result Events. They MUST NOT contain business logic.

**Rationale**:
- Keeps Managers pure (no EventBus dependency) for unit testing
- Keeps Services thin; enables Manager unit testing without EventBus
- Separates concerns: Managers provide capabilities, Services handle event translation
- Enables capability manager reuse across different contexts

**Trade-offs**:
- Additional الخدمات layer adds slight indirection
- Requires careful event-to-manager mapping
- Facade services must be kept deliberately thin

**Consequences**:
- Managers can be unit tested without EventBus mocking
- Services remain focused on event translation only
- Capability managers have clean, testable interfaces
- EventBus dependency is isolated to facade services
- Enables capability manager evolution without service changes

**Current Status**: Active

**Related Parts**: Part 0 (Principle 7), Part 6 (Capability Facade Services), Part 4 (Capability Managers)

---

## ADR 008: Immutable Events with Correlation & Causation

**Title**: Every Event MUST carry correlation_id (workflow trace) and causation_id (direct cause). Events MUST be immutable.

**Context**: Distributed tracing, replay debugging, and causal analysis require tracking workflows and direct event relationships.

**Problem**: Without correlation and causation tracking, it's impossible to trace workflows across services or understand event causality for debugging.

**Alternatives Considered**:
- Logging-based tracing with thread IDs
- Distributed tracing protocols (OpenTelemetry/Zipkin)
- Causation-only tracking without correlation
- Mutable events with versioning

**Decision**: Every Event MUST carry correlation_id (UUID) for workflow trace and causation_id (UUID) for direct cause. Events MUST be immutable (frozen dataclass, kw_only=True).

**Rationale**:
- Enables distributed tracing without log parsing
- Supports replay debugging by reconstructing event sequences
- Allows causal analysis for root cause determination
- Works across service and process boundaries
- Immutability ensures event integrity for audit trails

**Trade-offs**:
- Slightly larger event payloads
- Requires UUID generation for each event
- Immutability requires new instances for modifications
- UUID generation overhead

**Consequences**:
- Part 2.1 specifies Event base contract with required fields
- Part 2.2 defines EventType catalog
- Correlation ID tracks logical workflow from start to finish
- Causation ID enables building event causality chains
- Supports distributed tracing and observability tooling
- Enables event replay for testing and debugging
- Provides foundation for audit trails and compliance

**Current Status**: Active

**Related Parts**: Part 0 (Principle 8), Part 2 (Event System), Part 12 (Observability), Part 14 (Audit)

---

## ADR 009: Explicit Failure Handling via Events

**Title**: Failures MUST be communicated via Events (TaskFailed, RetryBudgetExhausted, RootCauseAnalyzed). There are NO exceptions crossing service boundaries.

**Context**: Distributed systems require failure handling as data to maintain eventual consistency and enable centralized error handling.

**Problem**: Exceptions crossing service boundaries break encapsulation, prevent uniform error handling, and complicate failure analysis in event-driven systems.

**Alternatives Considered**:
- Exception propagation across service boundaries
- Error codes returned from service calls
- Hybrid approach with events for some failures
- Service-specific error handling mechanisms

**Decision**: Failures MUST be communicated via Events. There are NO exceptions crossing service boundaries. BaseService on_error() MUST emit failure events and MUST NOT raise exceptions.

**Rationale**:
- Exceptions are control flow; events are data for eventual consistency
- Eventual consistency requires failure information as data
- Enables centralized failure handling and routing
- Supports automated recovery through event processing
- Facilitates failure correlation across services

**Trade-offs**:
- Requires designing comprehensive failure event types
- Slightly more verbose than exception throwing
- Requires handling failure events in event processors
- May increase event volume for failure scenarios

**Consequences**:
- Part 2.2 defines failure-related EventTypes
- BaseService provides standardized failure handling
- Failure events flow through EventBus like any other event
- Enables retry budgets and exhaustion detection
- Supports root cause analysis automation
- Allows failure routing to specialized services (operations, learning)
- Enables circuit breaker patterns through event observation

**Current Status**: Active

**Related Parts**: Part 0 (Principle 9), Part 2 (Events), Part 4.4 (RetryManager), Part 4.5 (RootCauseManager), Part 6 (Operations/Learning Services)

---

## ADR 010: Declarative Layered Configuration

**Title**: Configuration MUST use the four-layer merge (defaults → app.yaml → env.yaml → env vars). No hardcoded defaults in Kernel or Manager code.

**Context**: The system needs to support multiple deployment environments while maintaining configuration consistency and enabling secret management.

**Problem**: Hardcoded configuration creates deployment rigidity, prevents environment-specific customization, and complicates secret management.

**Alternatives Considered**:
- Single configuration file per environment
- Environment variables only
- Configuration service/database
- Hardcoded defaults with override mechanisms
- Configuration inheritance hierarchies

**Decision**: Configuration MUST use the four-layer merge (defaults → app.yaml → env.yaml → env vars) with later layers overriding earlier ones. No hardcoded defaults in Kernel or Manager code.

**Rationale**:
- Environment parity between development, testing, and production
- Secrets management through environment variables
- Reproducible deployments with version-controlled configs
- Clear precedence hierarchy reduces configuration confusion
- Enables configuration drift detection

**Trade-offs**:
- Requires configuration merge implementation
- Slightly more complex configuration lookup
- Potential for obscure override conflicts
- File-based configuration may not suit all deployment targets

**Consequences**:
- Part 7 specifies configuration schema and merge semantics
- All configuration must be accessible through layered system
- Default values must come from default configuration files
- Environment variables override file-based configuration
- Enables configuration validation at startup
- Supports hot-reload through configuration change events
- Provides foundation for multi-tenancy through layered overrides

**Current Status**: Active

**Related Parts**: Part 0 (Principle 10), Part 7 (Configuration), Part 3 (Kernel Initialization)

---

## ADR 011: Version & Compatibility First-Class

**Title**: Event schemas, configuration schemas, and APIs MUST carry version identifiers. Breaking changes require major version bump and migration path.

**Context**: Production systems evolve over time and need backward compatibility guarantees while allowing necessary improvements.

**Problem**: Without explicit versioning, breaking changes cause silent failures, make upgrades risky, and prevent safe evolution of the system.

**Alternatives Considered**:
- No versioning; breaking changes allowed freely
- Timestamp-based versioning
- Semantic versioning only for public APIs
- Client-side version tolerance only
- Protocol negotiation mechanisms

**Decision**: Event schemas, configuration schemas, and APIs MUST carry version identifiers. Breaking changes require major version bump and documented migration path.

**Rationale**:
- Production systems require stability and predictability
- Explicit versioning enables safe evolution
- Migration paths reduce upgrade risk and effort
- Consumers can adapt to changes on their own schedule
- Supports multiple version coexistence during transitions

**Trade-offs**:
- Version management overhead
- Requires maintaining multiple versions during transitions
- Migration path development and testing effort
- Slightly more complex schema definitions

**Consequences**:
- Part 2.6 specifies event schema versioning strategy
- Configuration schemas include version fields
- API contracts are versioned explicitly
- Breaking changes trigger major version increments
- Migration documentation is required for breaking changes
- Enables canary releases and blue/green deployments
- Supports semantic versioning for consumer expectations

**Current Status**: Active

**Related Parts**: Part 0 (Principle 11), Part 2.6 (Event Versioning), Part 7 (Configuration Schemas)

---

## ADR 012: Built-In Observability

**Title**: Every component MUST emit structured logs (JSON, correlation IDs) and Events for state transitions. StructuredLogger is the single logging abstraction.

**Context**: Debugging distributed event flows requires correlation from the start, and observability cannot be an afterthought in a complex orchestration system.

**Problem**: Bolted-on observability creates gaps in coverage, inconsistent formatting, and missed correlation between logs and events.

**Alternatives Considered":
- Logging-only observability approach
- Metrics-only observability approach
- Multiple logging frameworks for different components
- Observability as optional add-on service
- After-the-fact log correlation and analysis

**Decision**: Every component MUST emit structured logs (JSON format with correlation IDs) and Events for state transitions. StructuredLogger is the single logging abstraction used throughout the system.

**Rationale**:
- Debugging distributed event flows requires end-to-end correlation
- Structured logs enable machine processing and analysis
- Single logging abstraction ensures consistency
- Built-in observability prevents coverage gaps
- Correlation IDs link logs to events for complete picture

**Trade-offs":
- Structured logging may be less human-readable than plain text
- Requires JSON serialization for all log entries
- Single abstraction may not fit all component needs perfectly
- Slight performance overhead vs. direct logging

**Consequences":
- Part 12 specifies StructuredLogger interface and usage
- All log entries include correlation_id and causation_id when applicable
- Events and logs can be correlated for debugging
- Metrics emission is standardized through events
- Health checks emit events for monitoring systems
- Enables distributed tracing systems to correlate logs and events
- Supports log-based audit trails and compliance reporting

**Current Status": Active

**Related Parts": Part 0 (Principle 12), Part 12 (Observability), Part 2 (Events), Part 3 (Kernel Logging)

---

## ADR 013: Extension Points Governance

**Title**: Specific extension points are explicitly permitted for variability while core architecture remains fixed

**Context**: AI-OS needs to support customization for different domains and use cases while maintaining architectural integrity and upgradability.

**Problem**: Unrestricted extension leads to architectural erosion, upgrade incompatibilities, and maintenance nightmares.

**Alternatives Considered":
- Completely closed architecture with no extensions
- Fully open architecture with no restrictions
- Plugin system with unrestricted access to internals
- Configuration-only customization approach

**Decision": Specific extension points are explicitly permitted (custom events, memory backends, skills, MCP transports, consensus algorithms, AI agents, model providers, resource types) while non-extension points (EventBus interface, Kernel lifecycle, BaseService contract, etc.) MUST NOT vary.

**Rationale":
- Enables domain-specific customization without breaking core
- Provides clear boundaries for what can be customized
- Maintains upgradability of core platform
- Protects architectural integrity while allowing flexibility
- Reduces support burden through well-defined contracts

**Trade-offs":
- Some desired customizations may not be possible through permitted points
- Requires careful design of extension point contracts
- Extension points may need evolution over time
- Risk of extension points becoming de facto core components

**Consequences":
- Part 0.5.2 enumerates all permitted extension points
- Non-extension points are locked and require ADR to change
- Extension points must follow specified contracts and interfaces
- Registration mechanisms exist for each extension type
- Governance ensures extensions don't violate core principles
- Enables ecosystem development around AI-OS platform
- Provides upgrade path for extensions through versioning

**Current Status": Active

**Related Parts": Part 0.5.2 (Extension Points), Part 2 (Custom Events), Part 4.6 (Memory Backends), Part 4.7 (Skills), Part 4.8 (MCP), Part 4.9 (Consensus), Part 4.10 (AI Agency), Part 4.11 (Model Router), Part 4.12 (Resource Types)

---

## ADR 014: Architecture Decision Record Process

**Title**: Any deviation from Principles or Non-Extension Points MUST be documented in an ADR following the specified format

**Context**: Architectural governance requires tracking intentional deviations from the established principles with clear rationale and sunset plans.

**Problem**: Undocumented deviations accumulate architectural debt, make conformance checking impossible, and obscure system evolution rationale.

**Alternatives Considered":
- No formal ADR process; deviations tracked informally
- ADRs only for major breaking changes
- Centralized architecture board approval without documentation
- Wiki-based architectural decision tracking

**Decision": Any deviation from Principles (0.4) or Non-Extension Points (0.5.2) MUST be documented in an ADR in docs/DECISIONS.md with Decision, Rationale, Impact, Mitigation, and Expiry fields.

**Rationale":
- Provides historical record of architectural decisions
- Enables conformance checking against approved deviations
- Forces consideration of impact and mitigation strategies
- Creates accountability for architectural decisions
- Supports evolutionary architecture with explicit timelines
- Makes architectural debt visible and manageable

**Trade-offs":
- Process overhead for documenting deviations
- Requires discipline to maintain ADR quality
- May slow down permissible deviations slightly
- Risk of ADR becoming bureaucratic without enforcement

**Consequences":
- Part 0.5.3 specifies ADR requirements and process
- Architecture Review Board (ARB) reviews all ADRs
- ADRs are part of conformance evidence
- Expiry dates force revisiting temporary deviations
- Impact analysis prevents unconsidered consequences
- Mitigation planning reduces risk of deviations
- Enables architectural evolution with governance

**Current Status": Active

**Related Parts": Part 0.5.3 (ADR Process), Part 0 (All Principles), Project Governance

---

## ADR 015: AI-OS vs Hermes Kernel Distinction

**Title**: AI-OS is the complete engineering operating system; Hermes is the orchestration kernel component

**Context**: Clear terminology is needed to distinguish between the complete platform and its kernel component to prevent architectural confusion.

**Problem": Blurring the distinction between platform and kernel leads to incorrect assumptions about responsibilities, boundaries, and extensibility points.

**Alternatives Considered":
- Using the terms interchangeably
- Defining Hermes as the complete platform
- Creating entirely new terminology for both concepts
- Kernel-centric naming with platform as extension

**Decision": AI-OS is the complete engineering operating system (kernel + services + capability managers + CLI + extensions). Hermes is the orchestration kernel component that owns exactly four Core Components and manages nine Capability Managers.

**Rationale":
- Prevents category errors in architectural discussions
- Clarifies scope of kernel vs platform responsibilities
- Enables precise communication about boundaries and interfaces
- Supports correct layering and dependency understanding
- Matches mental model of platform = kernel + ecosystem

**Trade-offs":
- Requires consistent terminology enforcement
- May cause initial confusion during transition period
- Need to update existing documentation and code comments
- Slight cognitive overhead maintaining two related concepts

**Consequences":
- Part 0.2.3 explicitly defines and distinguishes the terms
- Architectural discussions must use correct terminology
- Code comments and documentation must distinguish kernel/platform
- Enables precise scoping of architectural decisions
- Prevents kernel from taking on platform responsibilities
- Clarifies what belongs in kernel vs service/service extension

**Current Status": Active

**Related Parts": Part 0 (Definitions), Part 3 (Kernel), Part 4-6 (Platform Components), Terminology Guidelines

---

## ADR 016: Memory Architecture Five-Tier Hierarchy

**Title**: The system implements five distinct memory types (WORKING, CLAUDE, ENGINEERING, OBSIDIAN, GRAPHIFY) with specific purposes and backends

**Context": Different types of information have different access patterns, retention requirements, and consistency needs in an AI engineering system.

**Problem": A monolithic memory system cannot optimally serve the diverse memory requirements of workflow state, agent reasoning, engineering artifacts, semantic knowledge, and relationship mapping.

**Alternatives Considered":
- Single memory system with different TTL policies
- Memory system with Pluggable backends only
- Database-per-memory-type approach
- In-memory only with persistence as optional layer
- Memory hierarchy based on access frequency only (LRU/LFU)

**Decision": Five distinct memory types are implemented:
- WORKING: Short-term, in-memory, workflow-scoped state
- CLAUDE: Agent conversation history and context (TTL-based)
- ENGINEERING: Persistent engineering artifacts (code, docs, models)
- OBSIDIAN: Semi-structured knowledge with linking capabilities
- GRAPHIFY: Relationship and dependency graph storage

**Rationale":
- Enables optimal storage characteristics for each memory type
- Supports different access patterns (frequent vs infrequent)
- Matches data consistency requirements (strong vs eventual)
- Enables specialized querying capabilities per type
- Supports different lifecycle and retention policies
- Prevents memory type interference and contamination

**Trade-offs":
- Increased complexity in memory management
- Requires cross-memory type coordination mechanisms
- More complex application code to select appropriate type
- Potential for data duplication across memory types
- Backup and recovery complexity increases

**Consequences":
- Part 4.6 specifies MemoryManager and memory type contracts
- Each memory type has appropriate backend (in-memory, persistent, graph, etc.)
- MemoryType enum provides type safety
- Services declare which memory types they use
- Cross-memory queries require explicit coordination
- Enables specialized tools for each memory type (IDE for ENGINEERING, graph explorer for GRAPHIFY, etc.)
- Supports different backup and archiving strategies per type

**Current Status": Active

**Related Parts": Part 0 (Memory Type Definition), Part 4.6 (MemoryManager), Part 5-6 (Service Memory Usage), Part 10 (Engineering Services)

---

## Current Status Summary

All 16 ADRs documented above are currently **Active** and represent the foundational architectural decisions for AI-OS Hermes Kernel v1.0. These decisions establish the principles, constraints, and extension points that govern the platform's evolution.

The ADR index serves as:
1. Historical record of why key architectural decisions were made
2. Reference for current conformance requirements
3. Guide for future architectural evolution
4. Tool for architectural review and governance
5. Foundation for onboarding new AI-OS engineers

Future deviations from these decisions will require new ADRs following the process defined in ADR 014, ensuring continued architectural governance and transparency.

---
*Last Updated: 2026-08-06*
*AI-OS Architecture Specification v1.0*