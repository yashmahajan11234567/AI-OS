# Architecture Rules

**Version:** 1.0  
**Scope:** AI-OS Architecture Parts 10–20  
**Purpose:** Define mandatory architectural rules for AI-generated architecture sections to prevent drift, inconsistency, over-engineering, contradictions, and undocumented design decisions.

---

## 1. Purpose

This document establishes the architectural governance framework for the AI-OS Architecture Specification (Parts 10–20). It defines binding rules that all architecture contributors (human and AI) must follow to ensure:
- Conceptual integrity across the specification
- Prevention of architectural drift and entropy
- Consistency with established patterns in Parts 1–9
- Traceability of design decisions to requirements
- Production-ready quality and implementability

These rules are mandatory for any architecture section generation, review, or improvement process. Violations must be justified and documented as exceptions.

---

## 2. Rule Hierarchy

Architectural governance follows a strict priority order where higher-level rules constrain and inform lower-level guidelines:

```
Architecture Specification (Parts 1–20)
          ↓
Architecture Decisions (recorded in ADRs)
          ↓
Architecture Rules (this document)
          ↓
Style Guide (formatting, naming conventions)
          ↓
Author Preferences (individual, non-binding)
```

### 2.1 Priority Enforcement
- **Architecture Specification**: The definitive source of truth for AI-OS architecture. All rules must align with and support the specification.
- **Architecture Decisions**: Documented choices that constrain future design (e.g., technology selections, patterns). Rules must not contradict recorded decisions.
- **Architecture Rules**: Mandatory constraints defined in this document. Higher priority than style or preferences.
- **Style Guide**: Guidelines for presentation (markdown formatting, diagram standards). Lower priority than rules.
- **Author Preferences**: Individual choices that may be overridden by any higher level.

### 2.2 Conflict Resolution
When conflicts arise between levels:
1. Specification always wins
2. Decisions win over rules
3. Rules win over style/preferences
4. Style wins over preferences

Exceptions to this hierarchy must be formally documented as Architecture Decisions.

---

## 3. Core Architectural Principles

These principles form the philosophical foundation of AI-OS and must be evident in all architecture sections.

### 3.1 Single Responsibility Principle (SRP)
Every component, service, module, or function must have one, and only one, reason to change. Responsibilities must be clearly delineated and not combined unless tightly coupled by nature.

**Application**:
- Components must encapsulate a single business capability or technical concern
- Services must expose a single coherent interface
- Functions must perform one logical operation

### 3.2 Loose Coupling
Components must minimize dependencies on other components. Changes in one component should not necessitate changes in another.

**Application**:
- Dependencies must be explicit and injected
- Communication must occur through well-defined interfaces or the EventBus
- Avoid direct instantiated dependencies; prefer dependency injection or service lookup

### 3.3 High Cohesion
Elements within a component must be strongly related and focused on a single purpose. Cohesion within a component should be maximized.

**Application**:
- Group related data and behaviors together
- Separate unrelated concerns into different components
- Component internals should exhibit strong internal relationships

### 3.4 Explicit Ownership
Every piece of state, resource, or responsibility must have a single, explicit owner. Ownership must be clear, traceable, and non-ambiguous.

**Application**:
- State must be owned by exactly one component
- Resources (memory, file handles, connections) must have explicit acquisition and release by the owner
- Ownership must be documented in component contracts

### 3.5 EventBus-first Communication
Components must communicate primarily through the EventBus. Direct point-to-point communication is prohibited unless explicitly justified.

**Application**:
- All inter-component events must be published to and consumed from the EventBus
- Synchronous RPC or direct method calls between components are forbidden
- EventBus provides decoupling, observability and tracing mechanism for inter-component communication

### 3.6 Deterministic Runtime
Given identical inputs and initial state, the system must produce identical outputs and state transitions. Non-determinism must be isolated and explicitly managed.

**Application**:
- Race conditions must be prevented through proper synchronization
- External inputs (timing, hardware) must be treated as events
- Pseudo-random number generation must be seedable and controllable for testing

### 3.7 Security-first
Security considerations must be integrated at every architectural level, not added as an afterthought.

**Application**:
- Threat modeling must inform component boundaries
- Authentication and authorization must be enforced at trust boundaries
- Data must be encrypted in transit and at rest by default
- Principle of least privilege must guide permission assignments

### 3.8 Interface-first Design
Components must be defined by their interfaces before implementation. Contracts must be explicit, versioned, and backward-compatible where possible.

**Application**:
- Define interfaces (APIs, events, schemas) before implementation
- Interface changes must follow semantic versioning
- Implementations must adhere strictly to interfaces without relying on implementation details

### 3.9 Contract-first Development
All interactions between components must be governed by explicit, verifiable contracts. Contracts include data schemas, behavioral expectations, and performance characteristics.

**Application**:
- Every EventBus event must have a JSON Schema
- Every service interface must have an OpenAPI/Swagger specification
- Contracts must be tested as part of the build process
- Contract evolution must follow defined compatibility rules

### 3.10 Failure-first Thinking
Assume failures will occur and design for graceful degradation, recovery, and fault isolation from the outset.

**Application**:
- Every component must define failure modes and recovery strategies
- Timeouts, retries, and circuit breakers must be configured by default
- Fallback behaviors must be specified for critical operations
- Failure handling must not compromise system invariants

### 3.11 Observable by Default
All components must emit sufficient telemetry to enable monitoring, debugging, and observability without additional instrumentation.

**Application**:
- Components must emit structured logs with correlation IDs
- Key metrics (latency, error rates, throughput) must be automatically collected
- Health checks must be exposed for all services
- Distributed tracing must be enabled for all EventBus interactions

### 3.12 Production-first
Design decisions must prioritize production operational characteristics over development convenience or theoretical elegance.

**Application**:
- Resource usage (memory, CPU, disk) must be bounded and predictable
- Diagnosability must be built-in (logging, metrics, tracing)
- Deployment and rollback procedures must be considered
- Performance characteristics must be estimated and validated

---

## 4. AI-OS Architectural Invariants

These are unchangeable rules that define the core nature of AI-OS. Violations require exceptional justification and Architecture Decision documentation.

### 4.1 No Direct Component Communication Bypassing EventBus
Components must never communicate directly (via method calls, shared memory, or direct messaging) without using the EventBus as the intermediary.

**Justification**:
- Ensures loose coupling and independent deployability
- Provides uniform observability and tracing
- Enables interception, transformation, and dead-letter handling
- Prevents hidden dependencies

### 4.2 Every Component Owns Its State
No component may modify state owned by another component. State mutation must occur only through the owning component's interface.

**Justification**:
- Prevents race conditions and inconsistent state
- Enables clear responsibility boundaries
- Simplifies debugging and testing
- Supports eventual consistency models

### 4.3 Runtime Behaviour Must Be Deterministic
Given identical event sequences and initial conditions, the system must produce identical state transitions and outputs.

**Justification**:
- Enables reproducible testing and debugging
- Supports formal verification and model checking
- Ensures predictable behavior in production
- Required for safety-critical AI operations

### 4.4 Every Component Has Explicit Contracts
Each component must publish explicit contracts for:
- Input events it consumes
- Output events it produces
- Services it provides (if any)
- Configuration it expects
- Failure modes it handles

**Justification**:
- Enables independent development and testing
- Supports contract testing and verification
- Documents assumptions and guarantees
- Facilitates integration and replacement

### 4.5 Every Component Has Explicit Lifecycle
Components must define and document:
- Initialization sequence and dependencies
- Runtime behavior and event handling
- Graceful shutdown procedures
- Error states and recovery paths

**Justification**:
- Enables predictable startup and shutdown
- Supports rolling updates and blue-green deployments
- Prevents resource leaks during lifecycle transitions
- Clarifies component responsibilities

### 4.6 Every Event Has an Owner
Each event type must have exactly one owning component responsible for:
- Defining the event schema
- Publishing the event (if applicable)
- Documenting semantics and usage
- Maintaining backward compatibility

**Justification**:
- Prevents schema conflicts and ambiguity
- Ensures clear responsibility for event evolution
- Enables centralized event documentation
- Supports schema registry and validation

### 4.7 Every Resource Has Ownership
All resources (memory, file handles, network connections, hardware accelerators) must have explicit acquisition and release by a single owning component.

**Justification**:
- Prevents resource leaks
- Enables predictable resource cleanup
- Supports RAII (Resource Acquisition Is Initialization) patterns
- Clarifies responsibility in failure scenarios

### 4.8 Every Failure Has Recovery
For every identified failure mode, there must be a defined recovery strategy, including:
- Detection mechanism
- Containment procedure
- Recovery actions
- Verification of restoration
- Escalation path if recovery fails

**Justification**:
- Ensures system resilience
- Prevents cascading failures
- Supports autonomous operation
- Required for production reliability

### 4.9 Every Runtime State Must Be Observable
All significant runtime state must be exposed through:
- Structured logging
- Metrics collection
- Health check endpoints
- Distributed tracing spans

**Justification**:
- Enables effective monitoring and alerting
- Supports root cause analysis
- Required for SLO/SLI measurement
- Facilitates capacity planning and optimization

---

## 5. Architecture Anti-Patterns

These patterns are strictly prohibited in AI-OS architecture unless explicitly justified as exceptions with architectural decision documentation.

### 5.1 God Objects
Components that know too much or do too much, violating SRP and creating central points of failure.

**Indicators**:
- Component has >5 distinct responsibilities
- Component depends on >7 other components
- Component modifies state owned by multiple other components
- Component is difficult to test in isolation

### 5.2 Hidden Dependencies
Dependencies that are not explicit in the component's interface or contracts, creating unexpected coupling.

**Indicators**:
- Direct instantiation of concrete classes instead of interface dependence
- Access to global state or singletons without injection
- Implicit timing assumptions
- Undocumented EventBus subscriptions

### 5.3 Shared Mutable State
State that is mutable and accessible by multiple components without synchronization or ownership clarity.

**Indicators**:
- Global variables accessible to multiple components
- Shared caches without clear invalidation ownership
- Mutable configuration objects passed between components
- Shared database tables without clear ownership boundaries

### 5.4 Circular Dependencies
Component A depends on Component B, which depends on Component A (directly or through a chain).

**Indicators**:
- Import/include cycles in code
- Mutual EventBus subscriptions creating feedback loops
- Service dependencies that cannot be resolved
- Deadlock potential during initialization

### 5.5 Tight Coupling
Components that are excessively dependent on each other's implementation details rather than interfaces.

**Indicators**:
- Components must change together for unrelated feature changes
- One component accesses internal fields/methods of another
- High correlation in change frequency between components
- Difficulty in replacing one component without affecting others

### 5.6 Runtime Leakage
Accumulation of resources or state over time without proper cleanup, leading to exhaustion.

**Indicators**:
- Unbounded growth in memory usage
- Increasing file descriptor or network socket counts
- Accumulation of unresolved promises or callbacks
- Gradual degradation in performance over time

### 5.7 Undefined Ownership
State, resources, or responsibilities that lack a clear, single owner.

**Indicators**:
- Ambiguous documentation about who modifies what
- Multiple components claiming responsibility for the same function
- No clear entity to contact when issues arise
- Race conditions due to unclear modification rights

### 5.8 Duplicate Responsibilities
Two or more components claiming ownership of the same responsibility or capability.

**Indicators**:
- Similar or identical functionality in multiple components
- Conflicting documentation about which component handles a task
- Redundant event handlers for the same event type
- Multiple components updating the same state without coordination

### 5.9 Over Engineering
Introducing complexity, abstractions, or generality not justified by current requirements.

**Indicators**:
- Abstraction layers with only one implementation
- Generic solutions for specific problems
- Plugin architectures without planned extension points
- Performance optimizations without measured bottlenecks

### 5.10 Premature Optimization
Optimizing for performance, scalability, or other non-functional aspects before establishing need through measurement.

**Indicators**:
- Complex caching mechanisms before characterizing access patterns
- Async/sync conversions without blocking operation measurements
- Micro-optimizations in code with low execution frequency
- Optimization of code paths that are not on critical path

### 5.11 Configuration Explosion
Excessive configurability that increases complexity without proportional benefit.

**Indicators**:
- More than 3 configuration options per component
- Configuration options that interact in complex ways
- Default configurations that require expert knowledge to understand
- Configuration that duplicates functionality available through conventions

### 5.12 Implicit State
State that is not explicitly managed but inferred from context, history, or implementation details.

**Indicators**:
- Behavior depending on call sequence without explicit state tracking
- Use of static variables to track invocation counts
- Reliance on initialization order for correct behavior
- State hidden in closures or callbacks or callback or promise chains

---

## 6. Architecture Decision Rules

These rules govern when new architectural elements may be introduced. All proposals must satisfy these criteria.

### 6.1 New Components
A new component may be introduced only when:
- **Single Responsibility**: It encapsulates one distinct business capability or technical concern not covered by existing components
- **Cohesion**: Its internal elements are highly related and would suffer if split
- **Coupling Reduction**: It reduces dependencies between existing components rather than increasing them
- **Ownership Clarity**: It provides clear ownership for state or resources currently ambiguously owned
- **Scalability Need**: It enables independent scaling of a specific capability
- **Failure Isolation**: It isolates failures that would otherwise affect multiple capabilities
- **Team Ownership**: It aligns with a clear team or organizational boundary

**Prohibition**: Do not create components for:
- Technical concerns that could be addressed as libraries or utilities
- Hypothetical future requirements without current need
- Mere code organization without architectural benefit
- Workarounds for existing design flaws (refactor instead)

### 6.2 New Services
A new service (deployable unit with network interface) may be introduced only when:
- **Independent Deployability**: It requires independent scaling, versioning, or deployment cadence
- **Trust Boundary**: It crosses a security or trust boundary requiring isolation
- **Technology Heterogeneity**: It requires a different runtime, language, or framework than existing services
- **External Facing**: It provides functionality to external systems or users
- **Operational Independence**: It has distinct operational characteristics (uptime requirements, monitoring needs)

**Prohibition**: Do not create services for:
- Internal communication that could use the EventBus
- Convenience of deployment without operational need
- Separation of concerns that doesn't justify operational overhead
- ML models that could be invoked as libraries within existing services

### 6.3 New Interfaces
A new interface (API, event type, service contract) may be introduced only when:
- **Contract Clarity**: It provides a clearer, more specific contract than existing interfaces
- **Consumer Need**: It serves a distinct set of consumers with different needs
- **Provider Focus**: It allows the provider to evolve independently for a specific capability
- **Versioning Path**: It enables backward-compatible evolution of related functionality
- **Semantic Distinction**: It represents a semantically distinct concept not covered by existing interfaces

**Prohibition**: Do not create interfaces for:
- Minor variations that could be handled with optional parameters
- Implementation details leaked through the interface
- Duplication of existing functionality with different naming
- Temporary workarounds for missing features

### 6.4 New Abstractions
A new abstraction layer may be introduced only when:
- **Multiple Implementations**: There are at least two (or planned) distinct implementations
- **Complexity Hiding**: It hides significant complexity that would otherwise leak
- **Interface Stability**: It provides a stable interface despite implementation changes
- **Cross-cutting Concern**: It addresses a concern that spans multiple components (logging, security, etc.)
- **Testability Benefit**: It significantly improves testability of dependent code

**Prohibition**: Do not create abstractions for:
- Single implementation cases (use concrete classes directly)
- Minor code deduplication without interface stability benefits
- Premature generalization for hypothetical cases
- Abstractions that add indirection without clear benefit

### 6.5 New Events
A new EventBus event type may be introduced only when:
- **Business Significance**: It represents a distinct business fact or state change
- **Consumer Clarity**: It has clear, distinct consumers with different processing needs
- **Producer Ownership**: It has a single, clear producer responsible for its semantics
- **Immutability**: It represents a fact that cannot be changed (only new events can correct)
- **Observability Value**: It provides significant diagnostic or monitoring value
- **Schema Stability**: Its schema is unlikely to change frequently

**Prohibition**: Do not create events for:
- Internal component state transitions not significant to other components
- Control flow signals that could be handled via direct interfaces (prohibited anyway)
- Debugging or tracing information that should go through logging/metrics
- Events that duplicate information available in other events
- High-frequency, fine-grained state changes that would overwhelm the EventBus

### 6.6 New Lifecycle States
A new lifecycle state may be introduced only when:
- **Behavioral Distinction**: It requires distinct behavior, event handling, or resource management
- **Clarity in Transitions**: It clarifies otherwise ambiguous transition conditions
- **Operational Significance**: It corresponds to a meaningful operational or user-visible state
- **Recovery Relevance**: It enables distinct failure detection or recovery strategies
- **Contract Impact**: It changes the component's contract or capabilities in a significant way

**Prohibition**: Do not create lifecycle states for:
- Minor internal variations that don't affect behavior or contracts
- Temporary states during transitions that could be modeled differently
- States that could be represented as combinations of existing states with flags
- States that don't change the component's observable behavior or responsibilities

---

## 7. Documentation Rules

All architecture documentation must follow these rules to ensure consistency, traceability, and usability.

### 7.1 Numbering
- **Section Numbers**: Use decimal notation (1, 1.1, 1.1.1) that matches the part and section hierarchy
- **Component IDs**: Use uppercase letters with underscores (e.g., AUTH_SERVICE, EVENT_BUS)
- **Event Types**: Use PascalCase for event names (e.g., UserRegistered, ModelTrainingCompleted)
- **Interface Names**: Use camelCase for interface names (e.g., iUserRepository, iModelTrainer)
- **Configuration Keys**: Use lowercase with underscores (e.g., max_concurrent_tasks, timeout_ms)
- **Constants**: Use uppercase with underscores (e.g., DEFAULT_TIMEOUT, MAX_RETRIES)

---

## 8. Consistency Rules

These rules ensure internal and cross-part consistency within the AI-OS Architecture Specification.

### 8.1 Internal Consistency
- **Terminology**: The same term must always mean the same thing within a single section
- **Numbering**: Section numbers must be sequential and hierarchical without gaps
- **Cross References**: All internal links must resolve to existing sections
- **Diagram Consistency**: Diagrams within a section must use consistent notation and symbols
- **Contract Alignment**: Component contracts must align with its responsibilities and events
- **State Machine Coverage**: State machines must specify behavior for all relevant events
- **Principle Adherence**: All content must demonstrate adherence to core architectural principles

### 8.2 Cross-Part Consistency
- **Terminology Alignment**: Terms used in Parts 10–20 must match definitions in Parts 1–9
- **Pattern Consistency**: Architectural patterns used must be consistent with those established earlier
- **Reference Integrity**: References to earlier parts must be accurate and up to date
- **Evolution Compatibility**: New concepts must be compatible with or properly extend existing ones
- **Numbering Continuity**: Section numbering must continue logically from previous parts
- **Style Uniformity**: Formatting, diagram styles, and notation must match earlier parts

### 8.3 Cross-reference Consistency
- **Reference Resolution**: Every reference must point to a valid section, figure, table, or external document
- **Reference Context**: References must clearly state what is being referenced and why
- **Reference Updates**: When referenced content changes, all references must be reviewed
- **Broken Reference Prevention**: Use automated validation to detect broken references before publication
- **External Reference Stability**: Prefer references to stable, versioned documents over unstable URLs

### 8.4 Terminology Consistency
- **Governing Glossary**: The AI-OS Glossary (Parts 1–9) is the authoritative source for terminology
- **Term Introduction**: New terms must be proposed as glossary updates before use
- **Contextual Consistency**: The same term must not have different meanings in different contexts
- **Acronym Expansion**: All acronyms must be expanded at first use in each section
- **Synonym Prevention**: Actively avoid introducing synonyms for established terms
- **Internationalization**: Use terminology that translates well and avoids culturally specific idioms

---

## 9. Runtime Rules

These rules govern the runtime behavior and operational characteristics of AI-OS components.

### 9.1 Scheduling
- **Deterministic Scheduling**: Task scheduling must be deterministic given identical inputs
- **Priority Inversion Prevention**: Implement priority inheritance or ceiling protocols for shared resources
- **Real-time Guarantees**: Hard real-time tasks must have bounded execution times validated by analysis
- **CPU Affinity**: Allow specification of CPU affinities for latency-critical components
- **Preemption**: Tasks must be preemptible unless explicitly declared non-preemptible for critical sections
- **Load Balancing**: Work distribution must consider current load and processing capabilities

### 9.2 Concurrency
- **Shared State Protection**: All shared mutable state must be protected by appropriate synchronization primitives
- **Lock Ordering**: Establish and document global lock ordering to prevent deadlocks
- **Lock-free Preferences**: Prefer lock-free data structures where performance-critical and feasible
- **Actor Model**: Components should ideally follow the actor model (single-threaded message processing)
- **Thread Safety**: All public interfaces must be thread-safe unless explicitly documented otherwise
- **Async Boundaries**: Clearly mark asynchronous boundaries in interfaces and contracts

### 9.3 Isolation
- **Failure Isolation**: Component failures must not propagate to cause cascading failures
- **Resource Isolation**: Components must not exhaust shared resources (memory, file descriptors, etc.)
- **Security Isolation**: Components operating at different trust levels must be isolated by hardware or software mechanisms
- **Technology Isolation**: Different technologies/runtimes should not share memory address spaces
- **Fault Containment**: Use bulkheads or similar patterns to isolate failure domains
- **Recovery Independence**: Recovery procedures for one component should not depend on others

### 9.4 Recovery
- **Automatic Recovery**: Components must attempt automatic recovery for transient failures
- **Manual Intervention**: Clearly document when manual intervention is required
- **Recovery Time Objectives (RTOs)**: Define and target specific recovery times for different failure types
- **Recovery Point Objectives (RPOs)**: Define acceptable data loss for different failure scenarios
- **Circuit Breakers**: Implement circuit breaker patterns for external dependencies
- **Retry Logic**: Use exponential backoff with jitter for retries; avoid thundering herd problems
- **Fallbacks**: Define graceful degradation paths when primary functionality is unavailable

### 9.5 Resource Management
- **Resource Acquisition**: Resources must be acquired using RAII patterns or equivalent
- **Resource Limits**: Enforce hard and soft limits on resource consumption (memory, CPU, etc.)
- **Resource Monitoring**: Emit metrics for resource usage and availability
- **Resource Cleanup**: Guarantee cleanup of all resources on both normal and exceptional paths
- **Resource Pooling**: Use pooling for expensive resources (database connections, etc.) with proper sizing
- **Leak Detection**: Implement automated detection for common resource leaks during testing

### 9.6 Lifecycle
- **Explicit States**: Define clear lifecycle states (CREATED, INITIALIZING, RUNNING, STOPPING, TERMINATED, ERROR)
- **State Transitions**: Document all valid transitions and the events/actions that trigger them
- **Initialization Order**: Specify dependencies and initialization order for dependent components
- **Graceful Shutdown**: Components must stop accepting new work and complete in-flight operations
- **Forced Termination**: Document behavior and resource state when termination is forced
- **Health Checks**: Expose health endpoints that accurately reflect component readiness
- **Startup Dependencies**: Declare external dependencies required for successful startup

---

## 10. Security Rules

These rules ensure security is built into the architecture from the foundation.

### 10.1 Trust Boundaries
- **Explicit Definition**: Clearly define and document all trust boundaries in the system
- **Boundary Enforcement**: Implement strict validation and sanitization at all trust boundary crossings
- **Least Privilege**: Components must operate with the minimum privileges necessary
- **Boundary Monitoring**: Log and alert on all trust boundary violations or suspicious activities
- **Boundary Testing**: Perform penetration testing focused on trust boundary defenses
- **Dynamic Boundaries**: Support dynamic trust establishment where appropriate (e.g., OAuth)

### 10.2 Authentication
- **Universal Requirement**: All interfaces (APIs, EventBus, management) must require authentication
- **Strong Authentication**: Prefer multi-factor authentication for administrative interfaces
- **Token Standards**: Use industry-standard tokens (JWT, OAuth 2.0) with proper validation
- **Session Management**: Implement secure session handling with timeout and invalidation
- **Credential Storage**: Never store credentials in plaintext; use secure vaults or HSMs
- **Authentication Failures**: Log and rate-limit failed authentication attempts

### 10.3 Authorization
- **Explicit Permissions**: Define explicit permissions for all resources and operations
- **Role-Based Access Control (RBAC)**: Implement RBAC as the default authorization model
- **Attribute-Based Access Control (ABAC)**: Use ABAC for fine-grained, context-dependent decisions
- **Permission Least Privilege**: Grant only the specific permissions required for a task
- **Authorization Failures**: Log authorization failures with sufficient detail for investigation
- **Regular Review**: Periodically review and prune excessive permissions

### 10.4 Audit
- **Immutable Logs**: Security-relevant events must be written to immutable, append-only logs
- **Log Integrity**: Implement cryptographic hashing or signing to detect log tampering
- **Log Retention**: Maintain audit logs for legally and organizationally required periods
- **Log Monitoring**: Implement real-time alerting on suspicious patterns in audit logs
- **Log Access**: Restrict audit log access to authorized personnel only
- **Log Content**: Include sufficient context (user, timestamp, resource, outcome) in all audit entries

### 10.5 Secrets
- **Vault Usage**: All secrets (API keys, passwords, certificates) must be stored in a secure vault
- **Zero Plaintext**: Secrets must never appear in plaintext in logs, configuration, or source code
- **Secret Rotation**: Implement automated rotation for secrets with defined expiration
- **Access Logging**: Log all access to secrets for audit and anomaly detection
- **Secret Segregation**: Use different secrets for different environments and components
- **Secret Injection**: Inject secrets at runtime rather than baking them into artifacts

### 10.6 Least Privilege
- **Default Deny**: Default to denying access unless explicitly permitted
- **Privilege Bracketing**: Elevate privileges only for the minimum necessary time and scope
- **Privilege Separation**: Separate high-privilege operations into isolated components with minimal interfaces
- **Capability Model**: Consider capability-based security models where appropriate
- **Privilege Creep**: Regularly review privileges to prevent accumulation over time
- **Just-in-Time Access**: Implement just-in-time privilege elevation for administrative tasks

---

## 11. EventBus Rules

These rules govern the use of the EventBus as the primary communication mechanism in AI-OS.

### 11.1 Publishing
- **Explicit Ownership**: Each event type must have exactly one publishing component
- **Immutability**: Events must be immutable after publication
- **Timeliness**: Publish events immediately after the corresponding state change occurs
- **Reliability**: Use persistent storage for events to survive broker restarts
- **Ordering**: Publish events in the order they occur; do not reorder for performance
- **Duplicate Prevention**: Implement deduplication mechanisms to prevent accidental duplicate publications
- **Schema Validation**: Validate events against their JSON Schema before publication
- **Correlation IDs**: Include correlation IDs to trace event chains across components

### 11.2 Subscription
- **Explicit Declaration**: Components must explicitly declare which event types they consume
- **At-least-once Delivery**: Assume at-least-once delivery and design idempotent handlers
- **Ordering Guarantees**: Do not assume ordering unless explicitly provided by the EventBus
- **Filtering**: Perform filtering as early as possible in the subscription pipeline
- **Error Handling**: Define explicit error handling strategies for event processing failures
- **Dead Letter Queues**: Configure dead letter queues for repeatedly failing events
- **Monitoring**: Emit metrics for event processing latency, throughput, and error rates

### 11.3 Ordering
- **Event Ordering**: The EventBus does not guarantee global ordering of events
- **Per-key Ordering**: Use partitioning keys to guarantee ordering for related events (e.g., per-user-id)
- **Sequence Numbers**: Include sequence numbers in events when ordering is critical for consumers
- **Sequence Validation**: Consumers should validate sequence numbers when ordering guarantees are required
- **Gap Detection**: Implement mechanisms to detect and handle gaps in event sequences
- **Replay Safety**: Event handlers must be idempotent to safely handle event replays

### 11.4 Replay
- **Replay Capability**: The EventBus must support replaying events for debugging and recovery
- **Replay Safety**: All event handlers must be idempotent to safely handle replays
- **Replay Scope**: Define clear boundaries for what events can be replayed and under what conditions
- **Replay Ordering**: Replay must preserve original event ordering guarantees
- **Replay Monitoring**: Replay operations must be observable and measurable
- **Replay Consent**: Components must explicitly opt-in to receiving replayed events when required

### 11.5 Dead Letter
- **Dead Letter Configuration**: Each event type must have a configured dead letter queue
- **Delivery Attempts**: Define the number of delivery attempts before dead-lettering
- **Dead Letter Inspection**: Provide mechanisms to inspect and analyze dead-lettered events
- **Dead Letter Replay**: Allow manual replay of dead-lettered events after issue resolution
- **Dead Letter Alerting**: Alert on patterns in dead-lettered events indicating systemic issues
- **Dead Letter Schema**: Dead-lettered events must retain their original schema and metadata

### 11.6 Correlation IDs
- **Correlation ID Propagation**: Correlation IDs must be preserved and propagated across all event handling
- **Correlation ID Generation**: Generate correlation IDs at the entry point of external requests
- **Correlation ID Uniqueness**: Correlation IDs must be sufficiently unique to avoid collisions
- **Correlation ID Logging**: All logs must include correlation IDs for request tracing
- **Correlation ID Metrics**: Metrics must be taggable by correlation ID for request-level analysis
- **Correlation ID Extraction**: Provide standardized methods for extracting correlation IDs from events

---

## 12. Rule Enforcement

Explain how future architecture should validate compliance.

### 12.1 Automated Validation
- **Rule Engine**: Implement an automated rule engine that validates architecture documents against these rules
- **CI Integration**: Integrate rule validation into the continuous integration pipeline
- **Pre-commit Hooks**: Provide pre-commit hooks that check for obvious rule violations
- **Rule Documentation**: Maintain machine-readable versions of these rules for automated processing
- **Violation Reporting**: Generate detailed reports showing exactly which rules were violated and where
- **Exclusion Mechanisms**: Allow documented exceptions to be marked and excluded from automated checks

### 12.2 Review Process
- **Rule Checklist**: Architecture reviews must include a checklist based on these rules
- **Expert Reviewers**: Include architects familiar with these rules in review processes
- **Rule Rationale**: Reviewers must reference specific rules when flagging issues
- **Exception Documentation**: Any exceptions to rules must be documented as Architecture Decisions
- **Follow-up Verification**: Verify that noted issues are resolved in subsequent revisions
- **Training Requirements**: Require reviewers to complete training on these rules

### 12.3 Metrics and Monitoring
- **Rule Compliance Metrics**: Track percentage of sections compliant with each rule
- **Trend Analysis**: Monitor compliance trends over time to identify improving or degrading areas
- **Hotspot Identification**: Identify sections or rule categories with repeated violations
- **Improvement Tracking**: Track how long violations remain open before being resolved
- **Feedback Loops**: Use metrics to improve both the rules and the review process
- **Executive Reporting**: Provide summary compliance metrics to architecture governance boards

### 12.4 Education and Training
- **Onboarding**: Require new architecture contributors to study these rules before contributing
- **Regular Refreshers**: Provide periodic refresher training on these rules
- **Workshops**: Conduct workshops on applying these rules to real architecture problems
- **Mentoring**: Pair new contributors with experienced architects familiar with these rules
- **Resources**: Maintain easily accessible references, examples, and FAQs
- **Community**: Foster a community practice around these rules through forums and discussions

---

## 13. Exceptions

Explain when a rule may be violated and how such exceptions must be documented.

### 13.1 Justification for Exceptions
Exceptions to these rules may be granted only when:
- **Compelling Business Need**: There is a documented, significant business justification
- **Technical Necessity**: No reasonable alternative exists that complies with the rules
- **Limited Scope**: The exception is tightly scoped to a specific, well-defined problem
- **Temporary Nature**: The exception is intended to be temporary with a clear remediation plan
- **Risk Assessment**: The risks of the exception have been identified and mitigated
- **Stakeholder Approval**: Appropriate stakeholders have reviewed and approved the exception

### 13.2 Documentation Requirements
All exceptions must be documented as Architecture Decision Records (ADRs) that include:
- **Rule Violated**: Specific identification of which rule(s) are being violated
- **Decision Description**: Clear description of what is being decided and why
- **Alternatives Considered**: Documentation of alternative approaches that were considered and rejected
- **Justification**: Detailed explanation of why the exception is necessary
- **Impact Analysis**: Analysis of the impacts (positive and negative) of the exception
- **Mitigation Plans**: Plans to mitigate any negative consequences of the exception
- **Review Schedule**: Schedule for reviewing whether the exception is still necessary
- **Sunset Condition**: Conditions under which the exception will be removed

### 13.3 Approval Process
Exceptions must follow this approval process:
1. **Proposal**: Submit exception proposal with initial justification
2. **Review**: Architecture review board evaluates the proposal
3. **Revision**: Address feedback from the review board
4. **Approval**: Formal approval by the architecture governance board
5. **Documentation**: Create formal ADR documenting the exception
6. **Implementation**: Implement the exception according to the approved plan
7. **Monitoring**: Monitor the exception for issues and effectiveness
8. **Review**: Regular review according to the established schedule
9. **Sunset**: Remove the exception when sunset conditions are met

### 13.4 Transparency
- **Exception Register**: Maintain a register of all active exceptions
- **Public Visibility**: Make exception documentation visible to all stakeholders
- **Impact Communication**: Communicate the existence and impact of exceptions to affected parties
- **Audit Trail**: Maintain a complete audit trail of exception proposals, discussions, and decisions
- **Regular Reporting**: Report on exception status in regular architecture governance reports
- **Lessons Learned**: Document lessons learned from exceptions for future reference

---

## Quality Requirements

This document should read like an enterprise architecture governance document. It should be reusable for Parts 10–20. Target approximately 400–600 lines.