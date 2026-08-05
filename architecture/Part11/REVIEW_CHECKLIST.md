# AI-OS Part 11 Architecture Review Checklist

## 1. Architecture Structure
- [ ] Layered architecture boundaries are explicitly defined and justified
  Pass: Architecture documentation clearly defines layers (e.g., domain, application, infrastructure) with explicit dependency rules preventing violations (e.g., no direct domain-to-infrastructure calls).
  Reviewer Notes: Examine layered architecture diagrams (C4 Container/Component), dependency constraint documents, and Architecture Decision Records (ADRs) defining layer responsibilities.
  Evidence Required: Layered architecture diagrams, dependency matrix showing allowed/invalid dependencies, ADRs documenting layering decisions.
  Severity: High - Undefined or violated layers create tight coupling and impede independent evolution.

- [ ] Architectural components have single, well-defined responsibilities (SRP)
  Pass: Component responsibilities are documented in architecture specifications with clear, singular purposes without overlap or ambiguity.
  Reviewer Notes: Review component descriptions in architecture documents (component catalogs, interface specifications) for clarity and focus.
  Evidence Required: Component responsibility statements in architecture documentation, interface definition documents, component cohesion analysis in ADRs.
  Severity: Medium - Poorly defined responsibilities increase architectural complexity and reduce maintainability.

- [ ] Architectural patterns are consistently applied and justified
  Pass: Use of architectural patterns (e.g., Hexagonal, CQRS, Event Sourcing) is documented with rationale, and deviations are explicitly justified.
  Reviewer Notes: Check pattern documentation in ADRs, verify consistency through diagram notation and component responsibilities.
  Evidence Required: Architecture Decision Records, pattern specification documents, annotated architecture diagrams showing pattern application.
  Severity: Medium - Inconsistent pattern application increases cognitive load and integration risk.

## 2. Completeness of Architectural Specification
- [ ] All required components from Part 11 specification are specified in the architecture
  Pass: 100% of specified components appear in the architectural model with clear responsibilities, interfaces, and relationships.
  Reviewer Notes: Trace each component from the Part 11 specification to the architecture documentation (component catalogs, diagrams, interface specs).
  Evidence Requirements: Requirements traceability matrix, component inventory in architecture documentation, gap analysis report comparing spec vs. architecture.
  Severity: Critical - Missing core components render the architecture incomplete and unimplementable.

- [ ] All inter-component interfaces are fully specified in the architecture
  Pass: Interface contracts (protocols, data formats, interaction protocols, performance characteristics) are completely specified for all component interactions.
  Reviewer Notes: Verify that all connections shown in component diagrams have corresponding interface specifications with sufficient detail for implementation.
  Evidence Requirements: Interface definition documents (IDLs, AsyncAPI, OpenAPI), message schema definitions, interaction diagrams (sequence, communication), protocol specifications.
  Severity: High - Unspecified interfaces create implementation ambiguity and integration gaps.

- [ ] Architecturally significant configuration options are completely documented
  Pass: All configuration options affecting architectural behavior (deployment topology, feature toggles, resource limits) are documented with purpose, valid values, and impact analysis.
  Reviewer Notes: Review configuration management documentation for completeness, clarity, and traceability to architectural decisions.
  Evidence Requirements: Configuration schema documentation, configuration impact analysis, environment-specific configuration guides, feature toggle registry.
  Severity: Medium - Incomplete configuration documentation leads to deployment errors and operational misconfiguration.

## 3. Runtime Behavioral Specification
- [ ] Critical runtime invariants are explicitly documented in the architecture
  Pass: Invariants (safety properties, liveness properties, resource constraints) are clearly stated in architecture documentation with rationale and scope.
  Reviewer Notes: Look for invariant declarations in architectural specifications, design contracts, or ADRs under "Runtime Constraints" or "Invariants" sections.
  Evidence Requirements: Invariant specification documents, design by contract specifications, architectural invariants section in component specifications.
  Severity: High - Undocumented invariants lead to unspecified behavior and integration risks.

- [ ] Resource management strategies are defined in the architecture
  Pass: Strategies for managing lifetime of resources (connections, memory, file handles, threads) are documented with acquisition/release patterns and ownership semantics.
  Reviewer Notes: Review resource management patterns in architectural guidelines and component responsibilities (e.g., "components must not retain resources beyond scope").
  Evidence Requirements: Resource management guidelines, lifecycle documentation in component specs, acquisition/release pattern specifications, ownership transfer policies.
  Severity: High - Undefined resource management leads to leaks and instability in implementations.

- [ ] State machines and behavioral protocols are completely specified
  Pass: All state-dependent behavior is documented with state transition diagrams, preconditions, postconditions, invariants, and timing constraints.
  Reviewer Notes: Verify that state machine specifications cover all relevant states and transitions for stateful components (e.g., protocol handlers, workflow engines).
  Evidence Requirements: State transition diagrams (statecharts, activity diagrams), protocol specifications, behavior models, temporal logic constraints.
  Severity: Medium - Underspecified state machines lead to inconsistent behavior and integration issues.

## 4. Behavioral Contracts and Interface Specifications
- [ ] All component interfaces have behavioral contracts documented in the architecture
  Pass: Preconditions, postconditions, side effects, performance characteristics, and error conditions are specified for all interfaces.
  Reviewer Notes: Check interface documentation for formal or semi-formal behavioral specifications (e.g., using Eiffel-style contracts or structured natural language).
  Evidence Requirements: Interface specification documents, design by contract specifications, API behavioral documentation, message exchange patterns.
  Severity: High - Missing behavioral contracts lead to misuse, incorrect implementations, and integration failures.

- [ ] Behavioral contracts are verifiable through architectural analysis
  Pass: Contracts are expressed in a form that enables static analysis, model checking, or architectural verification (e.g., pre/post conditions, state invariants).
  Reviewer Notes: Assess whether contracts are sufficiently formal to enable verification (avoiding vague terms like "reasonable time" without definition).
  Evidence Requirements: Contract specification language definition, verification tool configuration, analysis reports showing contract compliance checking.
  Severity: Medium - Informal contracts cannot be verified and rely solely on post-implementation testing.

- [ ] Behavioral contracts are maintained across architectural versions
  Pass: Changes to behavioral constraints are documented with backward/forward compatibility assessments and versioning strategy.
  Reviewer Notes: Review version history of interface specifications and compatibility analysis in ADRs (e.g., "v2 maintains backward compatibility with v1 except for...").
  Evidence Requirements: Versioned interface specifications, compatibility matrices, API evolution documentation, deprecation policies for behavioral changes.
  Severity: High - Breaking contract changes without notice break dependent components and violate consumer trust.

## 5. Authority and Security Boundaries
- [ ] Authority boundaries align with architectural layers and security domains
  Pass: Authority boundaries are explicitly defined in security architecture and align with layer/trust boundaries (e.g., presentation layer cannot assert domain-level privileges).
  Reviewer Notes: Verify that authority assignments in security models respect architectural decomposition and least privilege principles.
  Evidence Requirements: Security architecture documents, authority matrix showing permissions per layer/component, trust boundary diagrams, access control policy specifications.
  Severity: Critical - Misaligned authority creates privilege escalation vectors and violates fundamental security principles.

- [ ] Cross-boundary interactions require explicit authorization in the architecture
  Pass: All cross-trust-boundary interactions are mediated by authorized gateways (e.g., API gateways, trust brokers) with defined authorization policies.
  Reviewer Notes: Check for mediation points (gateways, proxies, services) at trust boundaries with explicit authorization logic in interface specifications.
  Evidence Requirements: Authorization policy specifications (XACML, OPA, RBAC matrices), access control models, security gateway designs, threat models showing mediation points.
  Severity: High - Missing authorization mediation enables unauthorized access and data leakage across trust boundaries.

- [ ] Authority delegation follows principle of least privilege in the architecture
  Pass: Delegated authority specifications show minimal necessary privileges for each delegated role, component, or service account,service, or API token.
  Reviewer Notes: Review privilege specifications in authorization models (e.g., AWS IAM policies, Kubernetes RBAC) for unnecessary excess privileges.
  Evidence Requirements: Principle of least privilege analyses, role-based access control definitions, privilege minimization documentation, permission audits in architecture.
  Severity: Medium - Excessive authority increases attack surface and potential damage from compromised components.

## 6. Ownership and Stewardship
- [ ] Every architectural element has a clear owner documented in the architecture
  Pass: Components, interfaces, data stores, and architectural decisions have explicitly assigned owners (teams or individuals) in ownership documentation.
  Reviewer Notes: Check ownership registers, responsibility assignment matrices (RACI), and stewardship assignments in architecture governance documents.
  Evidence Requirements: Ownership registry, RACI matrices for architectural elements, stewardship documentation, governance records showing accountability.
  Severity: Medium - Unclear ownership leads to neglected components, ambiguous responsibility, and architectural decay.

- [ ] Ownership responsibilities include architectural governance and evolution
  Pass: Owner responsibilities explicitly include maintaining architectural integrity, approving changes consistent with the architecture, and participating in governance processes.
  Reviewer Notes: Verify that ownership definitions include architectural decision participation, change approval authority, and evolution responsibilities.
  Evidence Requirements: Governance documents, owner responsibility definitions (including architecture board duties), change approval procedures, architecture review charter.
  Severity: Low - While important for operations, unclear architectural governance responsibilities don't directly affect structural integrity but risk misalignment.

- [ ] Ownership boundaries minimize cross-team architectural dependencies
  Pass: Component ownership aligns with architectural boundaries to minimize required cross-team coordination for changes that affect architecture.
  Reviewer Notes: Analyze ownership maps against dependency graphs to identify unnecessary cross-team dependencies that could be resolved through better boundaries.
  Evidence Requirements: Ownership vs. dependency mapping matrices, team topology documentation (Conway's Law analysis), communication overhead forecasts for proposed boundaries.
  Severity: Low - Misaligned ownership creates coordination overhead but doesn't violate architectural integrity if boundaries are respected.

## 7. Security Isolation and Protection
- [ ] Security domains (trust zones) are explicitly defined and isolated in the architecture
  Pass: Trust boundaries and security zones (e.g., public, DMZ, internal, restricted) are clearly defined with enforced isolation mechanisms specified.
  Reviewer Notes: Examine threat models, trust zone diagrams (showing data flows between zones), and isolation mechanism specifications (firewalls, sandboxing, encryption).
  Evidence Requirements: Trust boundary diagrams with data flow labels, isolation mechanism specifications (VPC/security groups, container runtime specs, hardware enclaves), threat models showing trust boundaries.
  Severity: Critical - Poor isolation enables cross-domain data leakage, privilege escalation, and lateral movement.

- [ ] Sandboxing and isolation mechanisms are specified in the architecture
  Pass: Mechanisms for isolating untrusted or less-trusted components (sandboxes, containers, hardware isolation, process separation) are explicitly specified with trust level mappings.
  Reviewer Notes: Verify that isolation mechanisms match the threat model and sensitivity of contained components (e.g., untrusted input parsers in sandboxes).
  Evidence Requirements: Isolation technology specifications (gVisor, Kata Containers, SGX enclaves), sandbox configuration guides, hardware enforcement documentation, process isolation policies.
  Severity: High - Inadequate isolation specification allows circumvention of security boundaries and increases attack surface.

- [ ] Security domains leverage hardware/enforced isolation where appropriate
  Pass: Architecture specifies use of hardware-enforced isolation (MMU-based process isolation, TPM, SGX, VT-x, SEV) for high-risk components when justified by threat model.
  Reviewer Notes: Check for hardware root of trust utilization and isolation hardware use in security architecture diagrams and component specifications.
  Evidence Requirements: Hardware security specifications (TPM usage, confidential computing plans), trusted computing base documentation, isolation mechanism justification, side-channel mitigation descriptions in threat models.
  Severity: Medium - Software-only isolation can be bypassed; hardware enforcement increases assurance against sophisticated attacks.

## 8. EventBus Integration and Event-Driven Architecture
- [ ] EventBus follows publish-subscribe pattern with loose coupling in the architecture
  Pass: Architecture documents event-driven topology showing publishers/subscribers with no direct dependencies (only via event topics) and asynchronous communication.
  Reviewer Notes: Examine event flow diagrams for absence of synchronous coupling and presence of intermediary brokers/topics; verify publishers don't reference subscribers.
  Evidence Requirements: Event flow diagrams (showing only topic connections), topic/subscription descriptions in event schema registry, coupling analysis reports (zero direct pub-sub dependencies), event storming outputs.
  Severity: Medium - Tight coupling in event propagation reduces system resilience, evolvability, and creates unintended dependencies.

- [ ] Event schemas are versioned, governed, and backward-compatible in the architecture
  Pass: Schema evolution strategy (backward/forward compatibility, versioning) is documented, enforced via schema registry, and includes clear deprecation policies.
  Reviewer Notes: Review schema registry policies, version compatibility matrices (e.g., "v2 consumers can read v1 events"), and evolution guidelines in architecture documentation.
  Evidence Requirements: Schema registry documentation (validation rules, compatibility modes), version compatibility policies, evolutionary change guidelines, deprecation notices with sunset timelines.
  Severity: High - Unmanaged schema evolution breaks consumers, creates data interpretation errors, and leads to data loss or processing failures.

- [ ] Event handling idempotency requirements are specified where required in the architecture
  Pass: Idempotency requirements for event processors are explicitly stated in event processing specifications where duplicate delivery is possible (at-least-once systems).
  Reviewer Notes: Check for idempotency markers in event processing specifications (e.g., "handlers MUST be idempotent") and duplicate handling guidance.
  Evidence Requirements: Idempotency requirements specification in handler contracts, duplicate handling patterns (idempotency keys, state checks), exactly-once processing guarantees where claimed, event processor implementation guidelines.
  Severity: Medium - Missing idempotency causes inconsistent state, duplicate side effects, and data corruption in at-least-once delivery systems.

## 9. Cross-Part Consistency and Integration
- [ ] Part 11 architecture is consistent with patterns established in previous Parts (1-10)
  Pass: Architectural decisions align with established patterns in Parts 1-10 unless explicitly overridden with justification in an ADR.
  Reviewer Notes: Compare architectural patterns, notation conventions, and interaction styles against prior parts for unexplained deviations (e.g., switching from REST to gRPC without justification).
  Evidence Requirements: Cross-part pattern compliance matrix, architecture decision record review showing justification for deviations, convention adherence checklists.
  Severity: Medium - Inconsistencies increase learning curve, reduce predictability, and create integration friction across the system.

- [ ] Data formats and conventions are uniformly specified and shared across Parts
  Pass: Shared data definitions use identical formats, schemas, and semantics with explicit versioning; common data models are referenced or reused.
  Reviewer Notes: Verify that data dictionaries and schema definitions reference canonical models or are consistently replicated with transformation specifications where needed.
  Evidence Requirements: Shared data dictionaries or canonical data model references, schema sharing mechanisms (import/include), data contract specifications, anti-corruption layer definitions where bridges are needed.
  Severity: Low - Format inconsistencies create translation overhead but can be managed with anti-corruption layers; ideal is shared canonical models.

- [ ] Error handling approaches are consistently architected across Parts
  Pass: Error handling model (error types, propagation mechanisms, handling strategies, fault boundaries) is uniform unless divergence is justified and documented.
  Reviewer Notes: Check for consistent use of error models (e.g., hierarchical error codes, exception hierarchies), fault containment boundaries, and retry/circuit breaker policies.
  Evidence Requirements: Error model specifications (error code registries, exception hierarchies), fault handling guidelines, resilience patterns documentation (bulkhead, timeout, retry), fault taxonomy documents.
  Severity: Low - Inconsistent error modeling increases cognitive load but doesn't break architectural integrity if boundaries are respected; consistency improves operability.

## 10. Deterministic Behavior and Predictability
- [ ] Algorithms with deterministic requirements are specified as such in the architecture
  Pass: Components requiring deterministic behavior (e.g., consensus protocols, financial calculations) are identified with determinism constraints and isolation requirements.
  Reviewer Notes: Look for determinism annotations in component specifications (e.g., "this component MUST be deterministic") and isolation boundary specifications (no external side effects).
  Evidence Requirements: Determinism requirement specifications in component contracts, isolation boundary definitions (no network/database access during critical sections), purity annotations in functional components.
  Severity: High - Undocumented determinism requirements lead to unpredictable behavior, validation failures, and inconsistent outcomes in critical paths.

- [ ] External dependencies affecting determinism are isolated and controlled in the architecture
  Pass: Nondeterministic sources (clocks, random numbers, external services, user input) are encapsulated behind controllable interfaces with mock/stub capabilities specified.
  Reviewer Notes: Check for abstraction of time sources (insertable clock interfaces), random generators (pluggable RNG), and external services (ports/adapters) with test double capabilities.
  Evidence Requirements: Dependency isolation patterns (ports/adapters, dependency injection), controllability specifications (ability to inject fixed time/rand), mockability guarantees in interface contracts, time abstraction descriptions.
  Severity: Medium - Uncontrolled nondeterministic dependencies prevent reproducible behavior, hinder testing, and cause elusive bugs in production.

- [ ] Race conditions are prevented through architectural synchronization mechanisms
  Pass: Shared state access is synchronized via documented mechanisms (locks, transactions, actors, STM, immutable data) with clear ownership and scope.
  Reviewer Notes: Examine concurrency control specifications in component interfaces (e.g., "this method requires the X lock") and shared data descriptions (ownership, locking protocol).
  Evidence Requirements: Concurrency control specifications (locking protocols, transaction isolation levels), synchronization mechanism descriptions (actor mailbox bounds, STM retry limits), race condition prevention guidelines, locking protocol documents with deadlock avoidance.
  Severity: Critical - Unprotected shared state leads to data corruption, undefined behavior, and security vulnerabilities (TOCTOU, etc.).

## 11. Scalability and Performance Characterization
- [ ] Architecture supports horizontal scaling for stateless components
  Pass: Stateless components are designed for horizontal scaling with explicit load balancing, session independence, and partitioning strategies.
  Reviewer Notes: Verify statelessness assertions (no in-memory session state) and load balancing mechanisms (consistent hashing, round-robin) in component specifications.
  Evidence Requirements: Scalability patterns documentation (shared-nothing architecture), load balancing specifications (algorithms, health checks), session statelessness guarantees, horizontal scaling guidelines in architecture.
  Severity: Medium - Lack of horizontal scaling design creates bottlenecks, limits throughput capacity, and forces vertical scaling limits.

- [ ] Stateful components have explicit scaling strategies in the architecture
  Pass: Scaling approaches (sharding, replication, partitioning, split-brain avoidance) are specified with consistency, availability, and partition tolerance tradeoffs.
  Reviewer Notes: Review consistency models (strong, eventual, causal), partition strategies (consistent hashing, range-based), and rebalancing mechanisms for stateful components.
  Evidence Requirements: Scaling strategy documents (sharding keys, replication factors), consistency model specifications (CAP tradeoffs), partitioning schemes, replication protocols (Raft, gossip), conflict resolution policies (last-write-wins, vector clocks).
  Severity: High - Poorly specified scaling strategies lead to data loss, inconsistency, availability issues during scaling, and split-brain scenarios.

- [ ] Resource usage growth is characterized and bounded in the architecture
  Pass: Resource complexity (time, space, IO) is analyzed and bounded for all components under expected loads with clear growth characteristics (O(1), O(n), etc.).
  Reviewer Notes: Check for complexity analysis, resource bounds (e.g., "cache size bounded by 10% of RAM"), and growth characterization in performance/scalability specifications.
  Evidence Requirements: Resource complexity analysis (Big O notation per component), scalability profiles (response time vs. load curves), load response characterization, bottleneck identification documents with mitigation strategies.
  Severity: Medium - Uncharacterized resource growth leads to unpredictable performance, capacity planning difficulties, and potential resource exhaustion under load.

## 12. Reliability, Fault Tolerance, and Recovery
- [ ] Architecture includes graceful degradation modes for partial failures
  Pass: Degraded modes are specified with trigger conditions (failure thresholds), available functionality (core vs. optional features), and degradation pathways (fallback implementations).
  Reviewer Notes: Examine failure mode specifications (circuit breaker thresholds, timeout values), degradation logic (feature toggles, reduced functionality modes), and fallback mechanism descriptions (cached responses, default values).
  Evidence Requirements: Degradation mode specifications (feature flag mappings, circuit breaker configs), failure threshold definitions (error rates, latency SLOs), fallback mechanism descriptions (stale data allowance, static fallbacks), graceful degradation patterns (strangler fig, parallel run).
  Severity: Medium - Lack of graceful degradation turns partial failures (e.g., dependency latency) into total system unavailability for affected features.

- [ ] Critical paths have redundancy and failover mechanisms in the architecture
  Pass: Redundancy (active/passive, active/active, N+1) and failover mechanisms (automatic leader election, health checks) are specified for all identified single points of failure.
  Reviewer Notes: Analyze redundancy diagrams (showing replicas), failover triggers (heartbeat timeouts, health check failures), and recovery time objectives (RTOs) for critical paths (e.g., request processing, data writes).
  Evidence Requirements: Redundancy architecture diagrams (showing standby instances), failover mechanism specifications (leader election protocols, health check intervals), recovery time objectives (RTO/RPO targets), split-brain avoidance descriptions (quorum requirements, fencing mechanisms).
  Severity: High - Single points of failure without redundancy create systemic fragility, unavoidable downtime during component failures, and data loss risks.

- [ ] Timeout and retry policies are defined and bounded in the architecture
  Pass: All external interactions (database, service calls, messaging) have bounded timeouts, idempotency requirements where applicable, and retry strategies with backoff and jitter.
  Reviewer Notes: Verify timeout values (connection vs. request), idempotency markers in interface specs, and retry policies (exponential backoff, max attempts) in integration specifications.
  Evidence Requirements: Timeout specification documents (connect/read timeouts per service), retry policy guidelines (backoff algorithms, jitter, circuit breaker integration), idempotency requirements (when RETRY is safe), circuit breaker patterns (failure thresholds, timeout durations).
  Severity: Medium - Unbounded retries and missing timeouts cause resource exhaustion (thread pools, connections), cascading failures, and unstable system behavior under partial failure.

## 13. Performance Characteristics and Requirements
- [ ] Critical operations have latency and throughput targets defined in the architecture
  Pass: Performance requirements (latency percentiles, throughput, jitter) are specified for all architecturally significant operations (e.g., 95th percentile read latency < 10ms).
  Reviewer Notes: Verify that performance goals are documented in non-functional requirements (NFRs) and traced to architectural mechanisms (caching, indexing, async processing).
  Evidence Requirements: Performance requirements specifications (SLA/SLI documents), latency budgets (per-hop allocations), throughput targets (req/sec, msg/sec), performance allocation models (how latency budget is split across components).
  Severity: High - Missing performance targets prevent verification against requirements and lead to unsatisfactory user experience or SLA violations.

- [ ] Resource utilization is optimized and characterized in the architecture
  Pass: Resource usage patterns (CPU, memory, storage, IO) are analyzed and optimized for common workflows with documented tradeoffs (e.g., "we prioritize latency over memory usage").
  Reviewer Notes: Look for resource efficiency analysis (e.g., "object pooling reduces GC pressure"), bottleneck identification ("DB connection pool is bottleneck"), and optimization strategies in performance documentation.
  Evidence Requirements: Resource utilization profiles (baseline consumption per transaction), efficiency analysis documents (tradeoff studies: latency vs. cost), optimization tradeoff studies (caching effectiveness), bottleneck resolution records (solutions applied).
  Severity: Medium - Suboptimal resource utilization increases operational costs (cloud spend), reduces system headroom for traffic spikes, and limits scalability efficiency.

- [ ] Caching strategies are specified with consistency and invalidation policies
  Pass: Caching layers (local, distributed, CDN), strategies (cache-aside, read-through, write-through), consistency models (strong, eventual, time-based), and invalidation mechanisms (TTR, event-based, manual) are explicitly documented.
  Reviewer Notes: Examine cache specifications for coherence protocols (if applicable), TTL policies, cache-aside patterns, and cache warming/preloading strategies.
  Evidence Requirements: Caching strategy documents (cache tiers, population strategies), consistency model specifications (staleness bounds, reconciliation), invalidation mechanism descriptions (TTL, pub/sub invalidation), cache warming procedures (preload scripts, warm-up endpoints).
  Severity: Low - Underspecified caching causes stale data serving (if TTR too high) or excessive reloads (if TTR too low) but doesn't break correctness; impacts performance and user experience.

## 14. Observability and Monitorability
- [ ] Observability (metrics, logging, tracing) is specified in the architectural design
  Pass: Observable points (metrics to collect, log events to emit, trace spans to generate) are specified with collection mechanisms, formats, and correlation approaches (e.g., request IDs propagated across services).
  Reviewer Notes: Verify that observability is designed in (instrumentation points defined), not bolted on, with clear specifications for what, when, and how to observe.
  Evidence Requirements: Observability architecture diagrams (showing metric/log/trace flow paths), instrumentation specifications (what to measure at component boundaries), telemetry data models (metric names, log fields, trace attributes), correlation ID propagation rules (headers, baggage, context passing).
  Severity: High - Poor observability design prevents effective production monitoring, slows incident response, and hinders capacity planning and debugging.

- [ ] Key metrics (latency, error rates, saturation) are specified and collectable
  Pass: RED metrics (Rate/requests per second, Errors/error rate, Duration/latency) are defined with collection points (where to measure), aggregation strategies (percentiles, rates), and alerting thresholds (SLO-based).
  Reviewer Notes: Check for metric specifications (what constitutes an "error"), collection mechanisms (agent-side vs. server-side), and alerting rules (page if 99th percentile latency > 1s for 5m).
  Evidence Requirements: Metric specification documents (metric names, descriptions, units), collection agent configurations (Prometheus scrapes, OTLP endpoints), alerting rule definitions (alert conditions, severity, runbooks), dashboard specifications (pre-built views for common investigations).
  Severity: Medium - Missing metrics delay issue detection ("we didn't know it was slow"), hinder root cause analysis ("was it GC or network?"), and prevent proactive capacity planning.

- [ ] Distributed tracing is specified with context propagation mechanisms
  Pass: Trace context propagation mechanisms (W3C TraceContext, baggage) are specified for all async boundaries (message queues, RPC calls, futures/process hops) and process hops.
  Reviewer Notes: Verify trace context forwarding at message queues (headers), RPC boundaries (trailers/metadata), and asynchronous handoffs (thread-local storage propagation, reactive context).
  Evidence Requirements: Tracing specification documents (required headers, baggage propagation), context propagation headers (traceparent, tracestate), trace ID formatting rules (W3C compliance), span correlation guidelines (how to link parent/child spans across services).
  Severity: Medium - Incomplete trace propagation obscures end-to-end latency ("where did the 2s go?"), error propagation ("which service failed?"), and makes performance optimization guesswork.

## 15. Architectural Documentation Quality
- [ ] Architecture documentation is complete and internally consistent
  Pass: Documentation covers all architectural elements (components, interfaces, decisions, rationales), dependencies, and constraints with no contradictions between artifacts (e.g., diagram vs. spec).
  Reviewer Notes: Perform consistency checks between diagrams (C4, flow), specifications (interface, and decision records (ADRs) - e.g., "does the component diagram match the interface spec?".
  Evidence Requirements: Documentation completeness matrix (% of elements documented), cross-artifact consistency reports (diagram-spec mismatches, ADR-implementation gaps), version synchronization logs (are diagrams and specs at same version?).
  Severity: Medium - Incomplete or inconsistent documentation leads to misunderstanding, incorrect implementation assumptions, and integration rework.

- [ ] Architectural decisions are recorded with context, alternatives, and consequences
  Pass: Significant decisions (tech stack, patterns, decomposition) have ADRs documenting problem statement, considered options, selected option, and consequences (tradeoffs).
  Reviewer Notes: Verify ADR completeness (always has context/decision/consequences) and traceability to architectural elements in diagrams and specifications (e.g., "this ADR explains why we chose Event Sourcing for the order service").
  Evidence Requirements: Architecture Decision Record repository (searchable by topic/date), decision traceability matrix (which ADR affects which component/diagram), stakeholder review records (approvals, concerns raised), supersession links (when ADR is updated).
  Severity: Low - Poor decision documentation hinders evolution ("why did we choose this?") but doesn't invalidate current architecture; increases maintenance burden.

- [ ] Documentation follows established architectural templates and standards
  Pass: Templates for views (context, container, component), specifications (interface, component), and reports (ADRs, architecture overviews) are consistently applied across all documentation.
  Reviewer Notes: Check for adherence to chosen architectural documentation standards (e.g., arc42 sections, C4 model levels, Viewpoints and Perspectives) and section completeness.
  Evidence Requirements: Template compliance reports (missing sections per template), documentation style guides (terminology, diagram standards), peer review checklists (did reviewers find missing sections?), tooling conformation reports (do diagrams parse correctly with selected tools?).
  Severity: Low - Non-standard documentation reduces usability (harder to navigate) but doesn't compromise architectural correctness or completeness; increases onboarding friction.

## 16. Architectural Diagrams and Visualization
- [ ] Architectural diagrams accurately reflect the documented architecture
  Pass: Diagram elements (components, interfaces, data stores, trust zones) correspond to documented components, interfaces, and relationships with no omissions (missing components) or additions (undocumented elements).
  Reviewer Notes: Conduct diagram-to-documentation traceability checks for all major views (context, container, component, deployment, data flow) - "does every box in the diagram have a spec?".
  Evidence Requirements: Diagram-to-specification traceability matrices (each diagram element links to a spec/ADR), model consistency checks (do component and deployment diagrams agree on element count?), diagram review logs (reviewer notes on omissions/additions).
  Severity: High - Inaccurate diagrams mislead implementers ("I built X because the diagram showed it"), create incorrect mental models, and cause integration errors when reality doesn't match the picture.

- [ ] Diagrams use consistent notation and adhere to chosen architectural views
  Pass: Notation (C4, UML, ArchiMate, SysML, custom) is uniformly applied with clear legends, view-specific conventions (e.g., C4 Level 2 shows components, not classes), and standardized symbols.
  Reviewer Notes: Verify notation consistency across diagram sets (are all component diagrams using the same box notation?) and clarity of visual encoding (do colors/shapes mean the same thing everywhere?).
  Evidence Requirements: Notation standardization documents (we use C4 with blue for components), legend specifications (what do dashed lines mean?), diagram readability assessments (can newcomers understand the diagram?), style guide compliance reports (are fonts/colors consistent?).
  Severity: Mixed notation increases cognitive load ("is this a dependency or a data flow?") and misinterpretation risk but doesn't invalidate diagrams if legends are clear; consistency improves comprehension speed.

- [ ] Diagrams are versioned and traceable to architecture documentation versions
  Pass: Diagrams include version numbers, timestamps, or Git SHAs matching the documentation baseline they represent (e.g., "diagram v2.1 matches docs tag v2.1").
  Reviewer Notes: Check for version labels on diagrams (title/footer) and correspondence with document versions in README or architecture manifest (e.g., "see ARCHITECTURE.md v2.1").
  Evidence Requirements: Diagram versioning scheme (semantic version in corner), version correlation logs (diagram v1.2 docs v1.2), change tracking diagrams (diff from previous version), baseline alignment records (CI job that verifies versions match).
  Severity: Low - Undated diagrams cause confusion ("is this the current architecture?") but can be reconciled with documentation if versions are tracked elsewhere; explicit versioning prevents drift.

## 17. Terminology and Communication Clarity
- [ ] Domain-specific terminology is defined and consistently used in documentation
  Pass: Glossary exists with definitions for all domain terms (e.g., "aggregate", "saga", "bounded context"), and usage is consistent across documents (no overloading like "session" meaning both HTTP and UI).
  Reviewer Notes: Audit term usage in documentation against glossary definitions for conflicts (e.g., "ledger" means financial record in one doc, blockchain in another) or ambiguities.
  Evidence Requirements: Glossary completeness reports (% of terms defined), term usage consistency matrices (does "event" always mean the same thing?), ambiguity detection logs (reviewer flags for overloaded terms), definition traceability (where is "aggregate" defined?).
  Severity: Medium - Inconsistent terminology causes miscommunication ("I thought you meant X"), incorrect assumptions in implementation ("I modeled it as Y"), and lengthy clarification meetings.

- [ ] Acronyms are expanded on first use and documented in the glossary
  Pass: Every acronym (HTTP, ACID, GDPR, SLA) has its expansion at first occurrence in each document ("Hypertext Transfer Protocol (HTTP)") and appears in the glossary.
  Reviewer Notes: Verify first-use expansions (scan documents for "HTTP" without prior definition) and glossary coverage (is "ACRONYM" in the glossary?).
  Evidence Requirements: Acronym first-use audit reports (percentage of first uses expanded), glossary coverage analysis (what percentage of used acronyms are defined?), expansion consistency checks (is "HTTP" always expanded the same way?).
  Severity: Low - Unexplained acronyms reduce readability ("what's Idempotency-Key?") but don't affect architectural correctness; increases reading time and confusion for newcomers.

- [ ] Terminology aligns with industry standards where applicable
  Pass: Standard terms (from TOGAF, ISO/IEC 42010, IEEE 1471, domain-specific RFCs) are used for common concepts with deviations justified and documented (e.g., we use "service" where TOGAF says "building block" because of team familiarity).
  Reviewer Notes: Compare terminology against reference frameworks for unnecessary divergence ("do we really need to call it a 'doodad' instead of a 'component'?").
  Evidence Requirements: Standards compliance reports (% of terms matching TOGAF/IEEE), term mapping documents ("our 'aggregate' = DDD aggregate"), expert review of terminology choices (does domain expert agree with our usage?).
  Severity: Low - Non-standard terminology increases onboarding overhead ("what's a doodad?") but doesn't alter technical meaning if well-defined; consistency with standards reduces training burden.

## 18. Backward Compatibility, Evolution, and Lifecycle
- [ ] Backward compatibility requirements are explicitly specified in the architecture
  Pass: Compatibility levels (backward, forward, none) are defined for all interfaces (APIs, events, configs) with versioning strategies (semantic versioning, date-based) and deprecation policies.
  Reviewer Notes: Check compatibility declarations in interface specifications ("v2 API is backward compatible with v1") and versioning policies in API design guidelines or ADRs.
  Evidence Requirements: Compatibility level specifications (GET /users v2 reads v1 schema), versioning strategy documents (when to bump major/minor/patch), backward compatibility test plans (how we verify v2 reads v1).
  Severity: High - Missing compatibility specifications lead to breaking changes, consumer integration failures, and loss of trust in the platform.

- [ ] Architectural evolution pathways are documented and governed
  Pass: Paths for evolving the architecture (adopting new patterns, technologies, or decomposition strategies) are described with decision gates (ADR required), review processes (architecture board), and obsolescence criteria for legacy approaches.
  Reviewer Notes: Examine architectural roadmaps ("Q3: evaluate migration to event-driven architecture"), technology radar (adopt/trial/assess/hold quadrants), and evolution guidance documents (how to propose a change).
  Evidence Requirements: Architecture evolution roadmaps (timeline for major changes), technology adoption frameworks (how we evaluate new tech), deprecation policies (sunset timeline for tech X), sunset timelines (legacy protocol removed by date).
  Severity: Medium - Undocumented evolution leads to technical debt accumulation ("we're stuck on old tech"), architectural decay ("the diagram doesn't match reality"), and friction when trying to improve.

- [ ] Deprecation and removal policies are specified for architectural elements
  Pass: Clear timelines (deprecation date, removal date), notification methods (announcements, deprecation logs), and removal criteria (usage < 1%) are defined for deprecated components, interfaces, or protocols.
  Reviewer Notes: Review deprecation notices (headers, logs, docs), sunset timelines (removal scheduled for Q4), and migration guides (how to move from old to new) for obsolete elements.
  Evidence Requirements: Deprecation policy documents (minimum deprecation period), sunset timelines (feature flag removal by date), migration assistance guides (scripts, tutorials), removal approval processes (architecture board sign-off to remove).
  Severity: Low - Poor deprecation practices cause unexpected breakage ("my integration stopped working!"), erode trust in architectural stability ("they change things without warning"), and increase support burden; good practices can be mitigated with monitoring.

## 19. Cross-Cutting Concerns and Variability
- [ ] Cross-cutting concerns (logging, security, transactions, observability) are addressed through architectural mechanisms
  Concerns are handled via documented patterns (interceptors, aspects, middleware, decorators) rather than scattered implementation or reliance on developer discipline.
  Reviewer Notes: Identify cross-cutting concern handling mechanisms in architectural patterns (e.g., "all logging goes through a central auditor") and components (framework-provided vs. hand-rolled).
  Evidence Requirements: Cross-cutting concern pattern documentation (how we do correlation IDs), mechanism specifications (where the interceptor plugs in), implementation template examples (starter code for new services).
  Severity: Medium - Tangled concerns ("each service implements logging differently") increase complexity, violate separation of concerns, and make system-wide changes (e.g., switch logging vendors) difficult and error-prone.

- [ ] Variability mechanisms (feature flags, plugins, extensions, strategies) are architecturally specified
  Points of variability and extension mechanisms are clearly documented with contracts, extension points, and versioning/compatibility guarantees for extensibility.
  Reviewer Notes: Examine plugin architectures (where do plugins hook in?), extension point specifications (what interfaces must they implement?), and variability management approaches (how do we version plugins?).
  Evidence Requirements: Extension point specifications (API contracts for plugins), plugin contract definitions (required interfaces, lifecycle methods), feature flag management systems (how flags are defined/rolled out), hot-swap capabilities (can we reload plugins without restart?).
  Severity: Medium - Poorly specified volatile leads to fragile extension mechanisms ("plugins break on every update"), plug-in version conflicts (" plugin A needs v1 of lib, B needs v2"), and uncontrolled variability ("anyone can drop a JAR in libs/ and it loads").

- [ ] Mobility and deployment characteristics are specified in the architecture
  Deployment models (cloud regions, on-premises, edge locations), mobility patterns (workload migration, burst-to-cloud), and installation characteristics (helm charts, operators, immutable images) are documented.
  Reviewer Notes: Examine deployment diagrams (showing regions/zones), environment specifications (dev/stage/prod differences), and mobility patterns in non-functional requirements (can we shift load from AWS to Azure?).
  Evidence Requirements: Deployment models documentation (multi-cloud strategy), environment-specific configuration guides (secrets handling per environment), mobility pattern descriptions (how to drain a node), installation characteristics (image size, startup time).
  Severity: Low - Underspecified deployment leads to environment-specific failures ("it works in dev but not prod"), operational difficulties ("how do we update 1000 nodes?"), and vendor lock-in; characteristics help with capacity planning and disaster recovery.

## 20. Resilience, Fault Tolerance, and Data Guarantees
- [ ] Fault tolerance mechanisms (replication, redundancy, failover, bulkheads) are specified in the architecture
  Pass: Mechanisms for handling component failures (replication for state, standby for stateless, circuit breakers for dependencies, bulkheads for resource isolation) are documented with activation conditions (failure thresholds, health check results).
  Reviewer Notes: Examine redundancy patterns (active-active vs. active-passive), failure detection mechanisms (heartbeats, health check frequency/criteria), and recovery procedures (automated failover, manual intervention steps).
  Evidence Requirements: Fault tolerance pattern descriptions (how we do leader election), redundancy specifications (replica count, quorum size), failure detector specifications (timeout, missing heartbeat count), recovery orchestration details (steps, approvals needed).
  Severity: High - Missing fault tolerance leads to cascading failures (one slow DB brings down all services), low availability (99% instead of 99.9%), and data loss risks during component failure.

- [ ] Graceful degradation and circuit breaker patterns are specified where appropriate
  Pass: Degradation strategies (feature toggles, reduced fidelity modes) and circuit breaker configurations (failure threshold, timeout, retry logic) are documented for external dependencies (payment gateways, APIs) and internal services (with clear ownership).
  Reviewer Notes: Check for circuit breaker parameters (fail after 5 timeouts in 10s, half-open after 30s), fallback specifications (return cached data, show error page), and degradation trigger conditions (dependency latency > 2s for 1m).
  Evidence Requirements: Circuit breaker configuration guides (per-service tuning), fallback mechanism definitions (stale data TTL, default values), degradation pathway descriptions (which features disable first), timeout and retry policies (how long we wait before giving up).
  Severity: Medium - Missing degradation strategies cause total failure upon partial dependency loss (payment gateway slows -> checkout completely fails), frustrated users, and lost revenue; degradation preserves core functionality.

- [ ] Data durability and consistency guarantees are specified in the architecture
  Pass: Persistence models (write-behind, write-through, event sourcing), replication strategies (leader-follower, multi-leader, quorum), and consistency levels (strong, eventual, causal, read-your-writes) are defined for all data stores with conflict resolution mechanisms.
  Reviewer Notes: Examine durability specifications (fsync frequency, journaling), consistency models (what anomalies are allowed?), and conflict resolution mechanisms (last-write-wins, application-specific mergers).
  Evidence Requirements: Durability specifications (write-ahead log, sync to disk), consistency model documentation (anomalies allowed: stale reads, lost updates), replication factor definitions (how many copies), conflict resolution policies (vector clocks, CRDTs, manual intervention).
  Severity: High - Unclear data guarantees lead to data loss (unflushed writes on power loss), inconsistency issues (users see different values), and corruption risks; clarity enables correct application logic and user expectations.

## 21. Performance Characteristics and Non-Functional Requirements
- [ ] Performance characteristics (latency, throughput, scalability) are specified and bounded
  Pass: Non-functional requirements for performance are quantified with measurement points (95th percentile latency of API endpoint), acceptance criteria (< 200ms), and load profiles (peak 10k RPM).
  Reviewer Notes: Verify that performance SLAs/SLOs are documented (e.g., "search latency P95 < 500ms") and traceable to architectural decisions (caching layer, DB indexing, async processing).
  Evidence Requirements: Performance requirement specifications (SLA/SLI documents with numbers), latency histograms (measured vs. target), throughput benchmarks (requests/sec under load), scalability curves (response time vs. concurrent users), load test profiles (defined peak/average/burst loads).
  Severity: High - Missing performance specifications prevent capacity planning ("how many servers do we need for Black Friday?"), SLA adherence ("we didn't know we had to be this fast"), and performance optimization efforts ("where do we even start?").

- [ ] Resource efficiency and utilization targets are defined in the architecture
  Pass: Targets for CPU, memory, storage, and network utilization are specified with optimization goals (e.g., "keep average CPU < 60% to handle spikes") and constraints (hard limits from cost or SLA).
  Reviewer Notes: Check for resource budgets (per-service or per-instance), utilization goals (avoid over-provisioning), and efficiency metrics (requests per watt, jobs per core) in non-functional requirements.
  Evidence Requirements: Resource utilization targets (CPU% per pod, IOPS per volume), efficiency benchmarks (baseline vs. optimized), waste minimization goals (identify and eliminate idle resources), capacity planning models (how load maps to resource needs).
  Severity: Medium - Poor resource efficiency increases operational costs (cloud waste, over-provisioning), limits scalability efficiency (need more instances than necessary), and reduces headroom for unexpected load; optimization saves money and improves responsiveness.

- [ ] Performance isolation and resource partitioning are specified where needed
  Pass: Mechanisms for preventing resource starvation (quotas, priorities, CPU/memory isolation, QoS bands) are documented for shared infrastructure (shared DB, shared network, shared node pools).
  Reviewer Notes: Examine resource allocation policies (namespace quotas), QoS mechanisms (net niceness, ionice), and isolation techniques (cgroups, VMs, separate clusters) in architecture documentation.
  Evidence Requirements: Resource quota specifications (max CPU per namespace), QoS policy descriptions (best effort vs. burstable vs. guaranteed), priority scheduling algorithms (CFS settings, nice values), isolation mechanism details (cgroup limits, VM placement rules).
  Severity: Low - Lack of resource isolation causes noisy neighbor problems ("job A slowed down because job B spiked CPU"), unpredictable performance ("why is latency variable?"), and unfair resource sharing; isolation improves predictability and SLAs.

## 22. Security Characteristics and Protection Mechanisms
- [ ] Security requirements (confidentiality, integrity, authentication, authorization) are specified
  Pass: Protection levels for data at rest (AES-256-GCM) and in transit (TLS 1.3, mutual TLS) are defined with mechanisms (encryption algorithms, signature schemes, protocols) and key lifecycle requirements.
  Reviewer Notes: Verify that security requirements are documented (e.g., "PII at rest MUST be encrypted") and mapped to specific security mechanisms (AES-256, RSA-OAEP, TLS 1.3 with specific cipher suites).
  Evidence Requirements: Security requirements specifications (classification handling: public/internal/confidential/restricted), threat models (what are we protecting against?), control mappings (how we meet each requirement), vulnerability assessments (scan results, penetration test scopes), compliance evidence (SOC 2, ISO 27001 artifacts if applicable).
  Severity: High - Missing security requirements leave the architecture vulnerable to exploitation (data theft, privilege escalation, service disruption) and regulatory non-compliance; explicit requirements enable verification and assurance.

- [ ] Security mechanisms (encryption, authentication, etc.) are specified with algorithms and key management
  Pass: Cryptographic algorithms (AES-256, XChaCha20-Poly1305), key lifecycle (rotation every 90 days), protocol details (TLS 1.3 withPerfect Forward Secrecy), and authentication mechanisms are documented for all security mechanisms (data encryption, service-to-service auth, user auth).
  Reviewer Notes: Check for algorithm specifications (why AES-256 over ChaCha20?), key strength requirements (2048-bit RSA minimum), and key management practices (how are keys stored/rotated?).
  Evidence Requirements: Cryptographic suite specifications (approved algorithms for each use case), key management protocols (Vault integration, automatic rotation), algorithm strength justifications (NIST compliance), certificate policies (allowed CAs, key lengths), protocol details (TLS versions, cipher suites).
  Severity: Medium - Weak or unspecified cryptography enables brute-force attacks (small key size), protocol downgrade attacks (forcing TLS 1.0), and key mismanagement (hardcoded keys, no rotation); strong crypto with good management increases assurance against cryptographic and implementation attacks.

- [ ] Security boundaries and threat models are documented and validated
  Pass: Trust zones (internet-facing DMZ, internal services, database layer), attack surfaces (exposed ports, public APIs), and threat models (STRIDE: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) are explicitly defined with validation evidence (penetration test scope, threat model review).
  Reviewer Notes: Examine threat models (what threats did we consider?), attack surface analysis (what's exposed to the internet?), and penetration test scope definitions (what was tested, what was out of scope?).
  Evidence Requirements: Threat model documents (STRIDE or PASTA model applied), attack surface summaries (open ports, public endpoints by service), penetration test scope definitions (in-scope: auth API, out-of-scope: internal monitoring tools), vulnerability assessment reports (what we found and fixed).
  Severity: Medium - Undefined threat models lead to incomplete security coverage ("we didn't consider SQLi"), unknown vulnerabilities ("we got hit by a zero-day we didn't think was relevant"), and misaligned defenses; regular review keeps security posture aligned with evolving threats.

## 23. Final Approval Checklist for Architecture
- [ ] All critical and high severity architecture findings have been resolved or accepted with justification
  Pass: No outstanding critical/high findings; medium/low items have documented risk acceptance where justified by business context or technical constraints (e.g., "we accept this medium risk due to legacy integration deadline").
  Reviewer Notes: Verify that risk acceptance records exist for any remaining issues, are approved by the appropriate governance body (Architecture Review Board), and include clear justification and expiration/review dates.
  Evidence Requirements: Severity breakdown report (counts by severity), exception register with justifications (why we accepted risk X), architecture review board sign-off on residuals (meeting minutes or approval record).
  Severity: Blocking - Architecture cannot be approved with unresolved critical/high risks as they pose unacceptable threats to security, reliability, or correctness.

- [ ] Review encompasses all architecture categories with sufficient depth and evidence from architectural artifacts
  Pass: Each category has been evaluated with documented findings based specifically on architecture artifacts (diagrams, specs, ADRs, contracts), not implementation details.
  Reviewer Notes: Check for superficial treatment of categories (just "looks okay") and validate depth of evidence examined (did we actually read the interface specs or just glance at the diagram?).
  Evidence Requirements: Category coverage matrix (did we look at EventBus? Security?), evidence traceability to artifacts (finding #42 is supported by ADR-123 and Interface Spec v2), review depth assessment notes (spent 20 mins reviewing security specs, not just 5).
  Severity: Medium - Incomplete review risks missing significant architectural issues (e.g., we didn't notice the EventBus lacks schema versioning) that could cause major problems downstream.

- [ ] Architecture demonstrates internal consistency and implementation independence
  Pass: No contradictions between architectural views (context, container, component, deployment, data flow); components depend only on interfaces (or abstract contracts), not concrete implementations or implementation-specific details.
  Reviewer Notes: Check for cross-view consistency (does the component count match between container and deployment diagrams?) and verify dependency directionality (do components depend on interfaces marked as "provides" or "contract" in specs?).
  Evidence Requirements: Consistency check reports between diagrams (component vs. deployment element count match), dependency inversion validation (dependence on abstractions, not concretions), abstraction boundary specifications (interfaces are clearly marked as contracts in documentation).
  Severity: High - Inconsistent or implementation-dependent architectures ("service A calls service B's internal utility class") mislead implementers, create tight coupling, impede evolution (can't change B's internals without breaking A), and increase fragility.

- [ ] Architecture is publication-ready for stakeholder consumption
  Pass: Documentation is complete, accurate, technically correct, and suitable for review by intended stakeholders (developers, architects, operations, security, business) with appropriate detail levels per audience.
  Reviewer Notes: Verify completeness (all sections filled), clarity (no jargon without explanation), accuracy (diagrams match specs), and accessibility (can a new hire understand the core concepts? can ops see deployment details? can security see controls?).
  Evidence Requirements: Documentation completeness score (% of required sections filled), readability assessments (Flesch-Kincaid grade level for executive summary), stakeholder review feedback (comments from architects, devs, ops, security), accessibility checks (alternative text for diagrams, logical heading structure).
  Severity: Medium - Poor publishability ("this doc is useless for planning our migration") hinders adoption, creates misalignment between technical and business views ("I thought it could do X but the diagram shows Y"), and leads to rework based on misunderstandings.

- [ ] Architecture review artifacts are complete and archived for traceability
  Pass: All review materials (review comments, evidence links, decisions, action items) are preserved with persistent links to the source architecture artifacts they evaluated (specific ADR versions, diagram versions, spec sections).
  Reviewer Notes: Ensure review records are stored with the architecture baseline they evaluated (e.g., "review for architecture v2.1") and that evidence is verifiable (links don't rot).
  Evidence Requirements: Review archive package (comments, decisions, action items), artifact traceability links (comment #15 links to ADR-45 section 3.1), decision log with evidence references ("accepted risk based on threat model v2"), review timeline (when was it reviewed, by whom, for what version?).
  Severity: Low - Lost audit trail ("what did we decide in the March review?") impedes future reassessment ("has this risk changed?"), accountability ("who approved this?"), and regulatory compliance; traceability enables confident evolution and auditing.

- [ ] Architecture has clear owners and governance for maintenance and evolution
  Pass: Responsibility for maintaining architectural integrity is assigned with defined processes for evolution (how to propose a change), exception handling (when can we violate the architecture?), and periodic review (architecture council meetings).
  Reviewer Notes: Verify ownership matrix (who owns the event bus schema?), governance procedures (ADR submission and approval workflow), change advisory board charters (who attends, quorum, voting rules), and exception handling policies (how do we get a temporary override?).
  Evidence Requirements: Ownership registry (team/service owns component X), governance documentation (ARCHITECTURE GOVERNANCE.md), change control procedures (how to submit an ADR), architecture board meeting records (attendance, decisions, action items).
  Severity: Medium - Unowned architecture ("nobody is responsible for the event bus") decays without oversight, becomes misaligned with the actual system ("we changed it but didn't update the diagram"), and leads to technical debt; clear ownership enables intentional evolution and accountability.

- [ ] Architecture is ready to guide implementation and evolution
  Provides sufficient detail for teams to implement components (interface contracts are clear), make evolutionary changes (how to extend the event schema), and resolve ambiguities (who owns what, what patterns to use) without requiring constant architectural clarification.
  Reviewer Notes: Check for implementable specifications (can a team build a service from the interface spec alone?), decision rationale (why did we choose event sourcing here?), and extension guidelines (how do I add a new event type?).
  Evidence Requirements: Implementation readiness survey (teams report "I have what I need to build this"), team comprehension tests (can newcomers explain the architecture from the docs?), gap analysis for missing guidance (we need a doc on how to add a saga).
  Severity: Low - Poor implementability ("the spec is missing the retry policy") leads to inconsistent development ("each team does retries differently"), architectural erosion ("we added a sync call because the async way was unclear"), and reliance on tribal knowledge; good documentation enables autonomous, aligned work.

---
*Generated for AI-OS Part 11 Architecture Review*
*Target: 500-700 lines*
*Last Reviewed: 2026-08-05*