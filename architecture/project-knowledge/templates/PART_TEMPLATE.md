# PART TEMPLATE: AI-OS Architecture Part

> This template defines the standard structure for every AI-OS Architecture Part (Parts 1–15).  
> It is implementation-independent and publication-quality.  
> **Do not include implementation details, specific technologies, or code samples in this template.**

---

# Purpose

> Clearly state the intent and objectives of this part. What problem does it solve? What value does it provide?

[Describe the purpose of this architecture part in one or two paragraphs.]

> **Placeholder for diagram:**  
> ```mermaid
> flowchart TD
>     A[Problem] --> B[Solution Provided by This Part]
>     B --> C[Value Delivered]
> ```
> *Figure: Purpose and value proposition*

---

# Scope

> Define the boundaries of this part. What is included and what is explicitly excluded?

**In Scope:**  
- [List what is covered]  

**Out of Scope:**  
- [List what is deliberately excluded]  

> **Placeholder for table:**  
> | Aspect | In Scope | Out of Scope |  
> |--------|----------|--------------|  
> | [Example] | [Yes/No] | [Yes/No] |  

---

# Audience

> Identify the primary readers and consumers of this document.

- [e.g., System Architects, Lead Developers, Operations Engineers, Security Auditors]  
- [e.g., Product Managers, Technical Writers]  

> **Notes:**  
> - Different audiences may focus on different sections.  
> - Consider what each audience needs to know or decide.

---

# Normative Language (RFC 2119)

> Specify the meaning of key terms used in this document.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

> **Example usage:**  
> - "The system MUST encrypt data at rest." (Requirement)  
> - "Components SHOULD use asynchronous communication where latency permits." (Recommendation)  
> - "Implementations MAY add additional logging for debugging." (Permission)

---

# Architecture Principles

> List the guiding principles that informed the design of this part.

- **Principle 1:** [Description]  
  *Why:* [Rationale for this principle]  
  *How to apply:* [Guidance on applying this principle]  

- **Principle 2:** [Description]  
  *Why:* [Rationale]  
  *How to apply:* [Guidance]  

> **Placeholder for principles table:**  
> | Principle | Description | Rationale | Application Guidance |  
> |-----------|-------------|-----------|----------------------|  
> | [Name]    | [Text]      | [Text]    | [Text]               |  

---

# Architecture Overview

> Provide a high-level view of the architecture described in this part. Use a summary diagram if helpful.

[High-level description of the architecture's structure and key interactions.]

> **Placeholder for overview diagram:**  
> ```mermaid
> flowchart LR
>     subgraph Part [Part Name: Brief Description]
>         A[Component A] --> B[Component B]
>         B --> C[Component C]
>     end
>     D[External System] -->|Interface| A
>     C -->|Interface| E[Another Part]
> ```
> *Figure: High-level overview of [Part Name] architecture*

---

# Component Model

> Define the structural building blocks, their responsibilities, and relationships.

## Components

> **Placeholder for components table:**  
> | Component | Responsibility | Type |  
> |-----------|----------------|------|  
> | [Name]    | [Description]  | [e.g., Service, Library, Database, Module] |  
> | ...       | ...            | ...  |  

## Component Relationships

> **Placeholder for component diagram:**  
> ```mermaid
> graph TD
>     A[Component A] -->|Provides| B[Interface X]  
>     B -->|Required by| C[Component B]  
>     C -->|Depends on| D[Data Store Y]  
> ```
> *Figure: Relationships between components*

---

# Interfaces

> Specify the contracts between components, including protocols, data formats, and interaction patterns.

## Interface: [Name]

> - **Purpose:** [What it enables]  
> - **Direction:** [Provided/Required]  
> - **Protocol:** [e.g., HTTP/2, gRPC, Async Message, Shared Memory]  
> - **Data Format:** [e.g., JSON, Protobuf, Avro, XML]  
> - **Operations:**  
>   - [Operation 1]: [Description]  
>   - [Operation 2]: [Description]  
>  
> **Versioning:** [Strategy, e.g., Semantic Versioning, URL versioning]  
> **Security:** [Authentication, Authorization, Encryption requirements]  
> **Performance:** [Latency, Throughput, Availability targets]  
>  
> **Sequence Diagram Placeholder:**  
> ```mermaid
> sequenceDiagram
>     participant A as Component A  
>     participant B as Component B  
>     A->>B: Request (operation)  
>     B-->>A: Response (result/data)  
> ```

> **Placeholder for additional interfaces:**  
> Repeat the above structure for each interface.

---

# Responsibilities

> Detail what each component is accountable for. Avoid describing *how* responsibilities are fulfilled.

## Component Responsibilities

> **Placeholder for responsibilities list:**  
> - **Component A:**  
>   - Responsibility 1: [What it does]  
>   - Responsibility 2: [What it does]  
>  
> - **Component B:**  
>   - Responsibility 1: [What it does]  
>   - Responsibility 2: [What it does]  
>  
> - **Part-Level Responsibilities:**  
>   - [Overall responsibility of this part]  
>   - [Another overall responsibility]  

> **Notes:**  
> - Responsibilities should be clear, non-overlapping, and collectively complete.  
> - Use strong verbs: ensures, provides, manages, coordinates, validates, etc.

---

# Architectural Constraints

> List the non-negotiable limitations or requirements that shape the architecture.

- **Constraint 1:** [e.g., "Must operate within 100ms latency SLA for 95th percentile requests"]  
  *Rationale:* [Why this constraint exists]  
- **Constraint 2:** [e.g., "Must be compatible with legacy system X using protocol Y"]  
  *Rationale:* [Why this constraint exists]  
- **Constraint 3:** [e.g., "Must comply with GDPR Article 32 (security of processing)"]  
  *Rationale:* [Why this constraint exists]  
- **Constraint 4:** [e.g., "Must not use public cloud services for data storage"]  
  *Rationale:* [Why this constraint exists]  

> **Placeholder for constraints table:**  
> | Constraint | Description | Rationale | Type (Hard/Preference) |  
> |------------|-------------|-----------|------------------------|  
> | [Text]     | [Text]      | [Text]    | [Hard/Preference]      |  

---

# Design Principles

> Elaborate on specific design guidelines derived from the architecture principles.

- **Loose Coupling:** Components interact via well-defined interfaces with minimal shared state.  
  *Application:* [How to achieve loose coupling in this part]  
- **High Cohesion:** Each component has a single, well-defined purpose.  
  *Application:* [How to ensure high cohesion]  
- **Technology Neutrality:** Design avoids prescribing specific vendors, languages, or frameworks.  
  *Application:* [How to maintain technology neutrality]  
- **Evolutionary Architecture:** Supports incremental change without breaking existing contracts.  
  *Application:* [How to support evolution]  
- **Security by Design:** Security considerations are integrated throughout the design process.  
  *Application:* [How to implement security by design]  

> **Placeholder for design principles table:**  
> | Principle | Guidance | How to Verify |  
> |-----------|----------|---------------|  
> | Loose Coupling | [Text] | [Text] |  
> | High Cohesion | [Text] | [Text] |  
> | ...         | ...    | ...         |  

---

# Runtime Behaviour

> Describe how the system behaves during execution, including concurrency, state management, and error propagation.

- **Initialization:** [How components start up and discover dependencies]  
- **Steady State:** [Normal operation patterns, request handling, background tasks]  
- **Concurrency Model:** [e.g., Event-driven, Actor model, Thread pools, Reactive streams]  
- **State Management:** [Where state is stored, consistency guarantees, partitioning strategy]  
- **Error Propagation:** [How errors are handled, reported, and recovered]  
- **Performance Characteristics:**  
  - Latency: [Target, e.g., P95 < 100ms]  
  - Throughput: [Target, e.g., 10K requests/second]  
  - Availability: [Target, e.g., 99.9%]  
- **Resource Usage:** [Memory, CPU, Storage, Network consumption patterns]  

> **State Diagram Placeholder (if applicable):**  
> ```mermaid
> stateDiagram-v2
>     [*] --> Idle  
>     Idle --> Processing: Start task  
>     Processing --> Idle: Task complete  
>     Processing --> Failed: Error  
>     Failed --> [*]: Recovery  
> ```

> **Placeholder for performance table:**  
> | Metric | Target | Measurement Method |  
> |--------|--------|-------------------|  
> | Latency (P95) | < 100ms | [Method] |  
> | Throughput | > 10K req/s | [Method] |  
> | Availability | 99.9% | [Method] |  

---

# Security Considerations

> Address authentication, authorization, data protection, and threat mitigation.

- **Authentication:** [Mechanism for verifying identity, e.g., OAuth2, Mutual TLS, API Keys]  
- **Authorization:** [How access rights are determined and enforced, e.g., RBAC, ABAC, ACLs]  
- **Data Protection:**  
  - At Rest: [Encryption standard, key management]  
  - In Transit: [Protocol, e.g., TLS 1.3, mTLS]  
- **Threat Mitigation:**  
  - Input Validation: [Approach to prevent injection attacks]  
  - Output Encoding: [Approach to prevent XSS]  
  - Rate Limiting: [Strategy to prevent DoS]  
  - Security Headers: [HTTP headers for browser security]  
- **Secrets Management:** [How credentials, API keys, certificates are handled]  
- **Audit Logging:** [What security-relevant events are logged, format, retention]  
- **Vulnerability Management:** [Process for identifying and addressing vulnerabilities]  

> **Threat Model Diagram Placeholder:**  
> ```mermaid
> flowchart LR
>     A[External Threat Actor] -->|Attack Vector (e.g., Phishing)| B[Component]  
>     B -->|Mitigation (e.g., Input Validation)| C[Control]  
>     C --> D[Residual Risk]  
>     style A fill:#f9f,stroke:#333  
>     style C fill:#9f9,stroke:#333  
>     style D fill:#ff9,stroke:#333  
> ```

> **Placeholder for security table:**  
> | Security Aspect | Mechanism | Standard/Protocol |  
> |-----------------|-----------|-------------------|  
> | Authentication  | [Text]    | [e.g., OAuth2.0]  |  
> | Authorization   | [Text]    | [e.g., RBAC]      |  
> | Encryption at Rest | [Text] | [e.g., AES-256-GCM] |  
> | Encryption in Transit | [Text] | [TLS 1.3] |  

---

# Validation Requirements

> Specify how compliance with this architecture will be verified.

- **Design-Time Checks:**  
  - Architecture reviews  
  - Dependency analysis  
  - Interface compliance testing  
  - Contract testing (consumer-driven)  
- **Runtime Checks:**  
  - Health checks (liveness, readiness)  
  - Contract tests in production  
  - Performance benchmarks  
  - Chaos engineering experiments  
- **Automated Validation:**  
  - CI/CD pipeline checks  
  - Automated architecture compliance tools  
  - Contract test suites  
- **Acceptance Criteria:**  
  - [Condition that must be met for sign-off]  
  - [Another condition]  
  - [Performance threshold]  

> **Placeholder for validation checklist:**  
> | Check | Method | Frequency | Responsible |  
> |-------|--------|-----------|-------------|  
> | Interface compliance | Contract testing | Per commit | Developer |  
> | Performance benchmark | Load testing | Nightly | Performance team |  
> | Security scan | SAST/DAST | Per release | Security team |  
> | Architecture review | Peer review | Per major change | Architect |  

---

# Failure Handling

> Define how the system responds to and recovers from failures.

- **Failure Detection:**  
  - Timeouts  
  - Health checks  
  - Circuit breaker states  
  - Anomaly detection  
- **Isolation:**  
  - Bulkheads (thread pools, semaphores)  
  - Fault containment zones  
  - Failure domains (availability zones, regions)  
- **Recovery Strategies:**  
  - Retry with exponential backoff and jitter  
  - Failover to standby instances  
  - Graceful degradation (reduced functionality)  
  - Cache-aside patterns  
- **Compensation:**  
  - Saga patterns for distributed transactions  
  - Manual intervention procedures  
  - Data reconciliation processes  
- **Alerting:**  
  - Critical failures -> PagerDuty/Opsgenie  
  - Warnings -> Slack/Email  
  - Metrics -> Monitoring system (Prometheus/DataDog)  

> **Failure Flow Diagram Placeholder:**  
> ```mermaid
> flowchart TD
>     A[Request Received] --> B{Healthy?}  
>     B -->|Yes| C[Process Normally]  
>     B -->|No| D[Trigger Circuit Breaker]  
>     D --> E[Return Fallback/Cached Response]  
>     E --> F[Log Incident with Correlation ID]  
>     F --> G{Alert Threshold Exceeded?}  
>     G -->|Yes| H[Notify On-Call Engineer]  
>     G -->|No| I[Continue Monitoring]  
> ```

> **Placeholder for failure handling table:**  
> | Failure Type | Detection Method | Recovery Strategy | Alert Level |  
> |--------------|------------------|-------------------|-------------|  
> | Timeout      | [Method]         | [Retry strategy]  | [Warning/Critical] |  
> | Dependency down | [Method]     | [Circuit breaker] | [Critical] |  
> | Data corruption | [Method]      | [Compensation]    | [Critical] |  

---

# Observability

> Describe how the system's internal state is made visible for monitoring, debugging, and insights.

- **Metrics:**  
  - Key performance indicators (latency, throughput, error rates, saturation)  
  - Business metrics (if applicable)  
  - Resource utilization (CPU, memory, disk, network)  
  - Custom metrics for domain-specific insights  
- **Logging:**  
  - Structured log format (JSON)  
  - Correlation IDs for request tracing  
  - Standard log levels (DEBUG, INFO, WARN, ERROR)  
  - Sampling strategy for high-volume logs  
- **Tracing:**  
  - Distributed tracing context propagation (W3C TraceContext)  
  - Span attributes for rich context  
  - Trace sampling strategy  
- **Health Checks:**  
  - Liveness probes (is the application running?)  
  - Readiness probes (is the application ready to serve traffic?)  
  - Dependency health checks  
- **Dashboards & Alerting:**  
  - Pre-built views for operators (real-time and historical)  
  - Pre-built views for developers (debugging focus)  
  - Alert routing policies (by severity, team, time of day)  
  - Runbook links in alerts  

> **Observability Pipeline Diagram Placeholder:**  
> ```mermaid
> flowchart LR
>     A[Component] -->|Metrics (Prometheus)| B[Monitoring System]  
>     A -->|Logs (Structured JSON)| C[Log Aggregator (ELK/Loki)]  
>     A -->|Traces (OpenTelemetry)| D[Tracing Backend (Jaeger/Tempo)]  
>     B --> E[Dashboard (Grafana)]  
>     C --> E  
>     D --> E  
>     E --> F[Alerting System (Alertmanager/PagerDuty)]  
>     F --> G[On-Call Engineer]  
> ```

> **Placeholder for observability table:**  
> | Signal Type | What It Measures | Tool/Format | Sampling Rate |  
> |-------------|------------------|-------------|---------------|  
> | Latency     | Request duration | Histogram   | 100%          |  
> | Error Rate  | Failed requests  | Counter     | 100%          |  
> | CPU Usage   | Processor utilization | Gauge   | 100%          |  
> | Logs        | Diagnostic events | JSON        | [e.g., 10%]   |  
> | Traces      | Request paths    | OpenTelemetry | [e.g., 1%]    |  

---

# Relationships to Other Parts

> Explain how this part interacts with, depends on, or is utilized by other parts in the AI-OS architecture.

- **Depends On:**  
  - Part [Y]: [Nature of dependency, e.g., "Provides authentication service via Interface X"]  
  - Part [Z]: [Nature of dependency]  
- **Used By:**  
  - Part [A]: [How this part is consumed, e.g., "Part A calls Interface Y to perform Z"]  
  - Part [B]: [How this part is consumed]  
- **Peer Relationships:**  
  - Part [C]: [Nature of peer relationship, e.g., "Collaborates on workflow W"]  
  - Part [D]: [Nature of peer relationship]  
- **Data Flows:**  
  - [Description of data flowing to/from other parts]  
  - [Format, frequency, volume]  

> **Dependency Diagram Placeholder:**  
> ```mermaid
> graph TD
>     subgraph AI-OS Parts  
>         PartX[Part X: This Part]  
>         PartY[Part Y: Authentication Service]  
>         PartZ[Part Z: Data Processing Pipeline]  
>         PartA[Part A: User Interface Layer]  
>     end  
>     PartY -->|Provides| PartX  
>     PartX -->|Used by| PartA  
>     PartX -->|Sends data to| PartZ  
>     PartZ -->|Returns results to| PartX  
> ```

> **Placeholder for relationships table:**  
> | Related Part | Relationship Type | Interface Used | Data Flow Direction |  
> |--------------|-------------------|----------------|---------------------|  
> | Part Y       | Depends On        | AuthZ Interface | Part Y → Part X     |  
> | Part A       | Used By           | UI API         | Part A ← Part X     |  
> | Part Z       | Peer/Data Sharing | Data Exchange  | Bidirectional       |  

---

# Conformance Requirements

> State the conditions under which an implementation can claim conformance to this part.

An implementation conforms to this architecture part if it:  
1. Satisfies all **MUST** and **REQUIRED** requirements listed herein.  
2. Passes all validation checks defined in the *Validation Requirements* section.  
3. Documents any deviations in an Architecture Decision Record (ADR) with appropriate justification.  
4. Maintains backward compatibility with specified interfaces unless explicitly versioned.  
5. Achieves the performance, availability, and security targets specified in *Runtime Behaviour* and *Security Considerations*.  

> **Placeholder for conformance checklist:**  
> | Requirement | Metric/Target | Measurement Method | Evidence Required |  
> |-------------|---------------|-------------------|-------------------|  
> | MUST encrypt data at rest | AES-256-GCM | Configuration review | Key management docs |  
> | SHOULD achieve <100ms P95 latency | <100ms | Load testing | Test report |  
> | MAY implement caching | [Optional] | Design review | Architecture diagram |  

---

# Architecture Decision Records

> Link to ADRs that capture significant decisions made during the development of this part.

> **Placeholder for ADR list:**  
> - [ADR-001: Choosing Async Messaging over Synchronous RPC](link/to/adr)  
>   *Decided:* 2024-01-15  
>   *Status:* ACCEPTED  
>  
> - [ADR-002: Adopting Zero-Trust Network Architecture](link/to/adr)  
>   *Decided:* 2024-03-22  
>   *Status:* ACCEPTED  
>  
> - [ADR-003: Implementing Circuit Breaker Pattern for Resilience](link/to/adr)  
>   *Decided:* 2024-05-10  
>   *Status:* ACCEPTED  
>  
> *See the `decisions/` directory for the complete list.*  

> **Notes:**  
> - Each ADR should follow the AI-OS ADR template.  
> - ADRs are stored in the `architecture/decisions/` directory.  
> - Only architecturally significant decisions warrant an ADR.

---

# Cross References

> Reference related standards, guidelines, and external documents.

- [AI-OS Master Context](link/to/master_context)  
- [AI Agency Framework](link/to/ai_agency)  
- [Memory Architecture](link/to/memory_arch)  
- [Validation Architecture](link/to/validation_arch)  
- [Engineering Principles](link/to/eng_principles)  
- [Architecture Decisions](link/to/arch_decisions)  
- [Glossary](link/to/glossary)  
-  
> **External Standards & References:**  
> - [RFC 2119: Key Words for Use in RFCs to Indicate Requirement Levels](https://www.rfc-editor.org/rfc/rfc2119)  
> - [ISO/IEC 42010:2022 Systems and software engineering — Architecture description](https://www.iso.org/standard/77867.html)  
> - [TOGAF Standard, 10th Edition](https://www.opengroup.org/togaf)  
> - [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)  
> - [OWASP Top Ten 2021](https://owasp.org/www-project-top-ten/)  
> - [CNCF Cloud Native Interactive Landscape](https://landscape.cncf.io/)  
>  
> **Placeholder for additional references:**  
> 1. [Author, *Title*, Publisher, Year]  
> 2. [Organization, *Standard Name*, Version, Year]  
> 3. [Author(s), "Paper Title", *Journal/Conference*, Volume, Pages, Year, DOI]  

> **Notes:**  
> - Prefer linking to AI-OS internal documents using `[[Document Name]]` syntax.  
> - Avoid duplicating content that is authoritatively defined elsewhere.

---

# Future Evolution

> Discuss anticipated changes, extensions, or deprecations.

- **Near Term (0–6 months):**  
  - [Planned enhancement, e.g., "Add support for mutual TLS authentication"]  
  - [Planned refinement, e.g., "Improve error messaging for Interface X"]  
  - [Planned optimization, e.g., "Reduce memory footprint by 20%"]  
- **Medium Term (6–18 months):**  
  - [Evolving requirement, e.g., "Prepare for quantum-resistant cryptography"]  
  - [Anticipated scale need, e.g., "Horizontal sharding for Component Y"]  
  - [Expected integration, e.g., "Support for new data format Z"]  
- **Long Term (18+ months):**  
  - [Strategic shift, e.g., "Evaluate migration to event-driven architecture"]  
  - [Architectural reconsideration, e.g., "Reassess centralized vs. decentralized model"]  
  - [Technology evolution, e.g., "Assess impact of emerging standard W"]  
- **Deprecation Notices:**  
  - [Feature planned for removal, with timeline and migration path]  
  - [Interface planned for sunset, with versioning strategy]  

> **Placeholder for evolution roadmap:**  
> ```mermaid
> gantt
>     title Architecture Evolution Roadmap  
>     dateFormat  YYYY-MM-DD  
>     section Near Term  
>     TLS Enhancement       :a1, 2024-09-01, 3m  
>     Error Messaging       :after a1, 2m  
>     section Medium Term  
>     Quantum-Resistant Crypto :crit, 2025-03-01, 6m  
>     Horizontal Sharding   :after crit, 4m  
>     section Long Term  
>     Event-Driven Eval     :crit, 2025-09-01, 4m  
>     Model Reassessment    :after crit, 3m  
> ```

---

# References

> List all documents, standards, and resources cited in this part.

> **Placeholder for references list (using consistent citation style):**  
>  
> 1. Fielding, R.T., et al. *Hypertext Transfer Protocol (HTTP/1.1): Semantics and Content*. RFC 7231, June 2014.  
>  
> 2. Newman, Sam. *Building Microservices: Designing Fine-Grained Systems*. O'Reilly Media, 2015.  
>  
> 3. Gamma, Erich, et al. *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley, 1994.  
>  
> 4. [OWASP Top Ten 2021](https://owasp.org/www-project-top-ten/)  
>  
> 5. [CNCF Cloud Native Interactive Landscape](https://landscape.cncf.io/)  
>  
> 6. [AI-OS Master Context](link/to/master_context)  
>  
> 7. [Engineering Principles](link/to/eng_principles)  
>  
> *Add references as needed, following a consistent citation style (e.g., IEEE, ACM, APA).*  
>  
> **Notes:**  
> - Include access dates for online resources: [Accessed: YYYY-MM-DD]  
> - Include version numbers for standards and specifications  
> - Reference AI-OS master documents using `[[Document Name]]` syntax  

---

# Authoring Guidelines

> Follow these rules when writing any AI-OS Architecture Part.

## How Architecture Should Be Written

- **Write for the Reader:** Assume the reader is a competent architect or engineer but may not be familiar with this specific part. Define acronyms on first use.
- **Be Precise and Unambiguous:** Avoid vague terms like "may", "could", or "might" when stating requirements. Use RFC 2119 keywords deliberately.
- **Focus on *What* and *Why*, Not *How*:** Describe the architecture's structure, responsibilities, and constraints. Omit implementation details, code snippets, or technology choices.
- **Use Diagrams Judiciously:** Include diagrams only when they clarify relationships, flows, or structures that are difficult to convey in text. Prefer Mermaid syntax for version-controllable diagrams.
- **Reference, Don't Duplicate:** If a concept is defined elsewhere (e.g., in another part or a standard), reference it rather than repeating the definition.
- **Maintain Consistency:** Use the same terminology throughout the document. Consult the AI-OS glossary if available.
- **Version Assumptions:** If the part assumes specific versions of dependencies, state them explicitly in the *Scope* or *Architectural Constraints* sections.

## What Should Never Be Included

- **Implementation Details:** No code samples, specific library names, database schema, API endpoints (unless abstracted as interface examples), or infrastructure-as-code snippets.
- **Technology Choices:** Avoid prescribing programming languages, frameworks, cloud providers, or specific tools unless they are inherent to the architectural concept (e.g., "This part assumes a service mesh for service-to-service communication").
- **Project Management Artifacts:** No timelines, resource estimates, task assignments, or sprint plans.
- **Operational Procedures:** No runbooks, troubleshooting steps, or incident response guides (these belong in operational documentation).
- **Marketing Language:** Avoid hyperbolic claims, buzzwords without substance, or sales-oriented phrasing.
- **Temporary Notes:** Remove all TODO comments, placeholders that are not part of the template structure, or informal annotations before publication.
- **Redundancy:** Do not restate the same requirement in multiple sections unless emphasizing different aspects (e.g., a security constraint vs. a performance constraint).

## Implementation Independence

- The architecture must be realizable using a variety of technologies, languages, and platforms.  
- Avoid tying the design to specific vendor products, proprietary protocols, or platform-specific features unless absolutely necessary (and then justify in an ADR).  
- When referencing real-world technologies for clarity, do so generically (e.g., "a message broker supporting AMQP 1.0" not "RabbitMQ").

## Technology Neutrality

- Architectural decisions should not favor one technology stack over another without clear, documented justification rooted in the architecture principles.  
- Where multiple options are equally valid, state that the architecture is technology-neutral and list viable alternatives.  
- If a specific technology is assumed for illustrative purposes, label it clearly as an *example* and not a requirement.

## Architecture-First Philosophy

- All subsequent design, implementation, and validation work must be derived from and compliant with this architecture.  
- Any deviation must be formally recorded as an Architecture Decision Record (ADR) with impact analysis and approval.  
- This part defines the "what" and "why"; detailed design and implementation define the "how". Never reverse this relationship.

## Diagram Best Practices

- Use Mermaid syntax for all diagrams to ensure version control and consistent rendering.  
- Keep diagrams readable at typical zoom levels (aim for immediate comprehension).  
- Ensure diagram elements are clearly labeled and legends are provided where needed.  
- Maintain consistent styling across all diagrams in the document (colors, line styles, fonts).  
- Consider accessibility: ensure sufficient color contrast and provide alternative text descriptions where possible.  
- Update diagrams when the architecture evolves to avoid drift between text and visuals.

---

# Publication Checklist

> Use this checklist before promoting a draft to a published state.

- [ ] Purpose, Scope, and Audience sections are complete and clear.  
- [ ] Normative language block is present and correctly references RFC 2119.  
- [ ] All RFC 2119 keywords (MUST, SHOULD, MAY, etc.) are used deliberately and consistently.  
- [ ] Architecture Principles are listed and traceable to higher-level doctrines (e.g., AI Agency).  
- [ ] Architecture Overview includes a high-level diagram (if helpful) and summarizes the part's essence.  
- [ ] Component Model defines all major components, their responsibilities, and relationships (with diagram if complex).  
- [ ] Interfaces are fully specified (purpose, protocol, data format, binding, operations).  
- [ ] Responsibilities are allocated to components without describing implementation.  
- [ ] Architectural Constraints are enumerated and justified.  
- [ ] Design Principles elaborate on the Architecture Principles with actionable guidance.  
- [ ] Runtime Behaviour describes initialization, steady state, concurrency, state management, and failure propagation.  
- [ ] Security Considerations cover authentication, authorization, data protection, threat mitigation, secrets management, and audit logging.  
- [ ] Validation Requirements specify how compliance will be checked (design-time, runtime, automated).  
- [ ] Failure Handling details detection, isolation, recovery, compensation, and alerting.  
- [ ] Observability describes metrics, logging, tracing, health checks, and dashboards.  
- [ ] Relationships to Other Parts are explicit, with dependency and usage statements and a diagram if helpful.  
- [ ] Conformance Requirements are clear and achievable.  
- [ ] Architecture Decision Records section lists all relevant ADRs (or notes if none exist).  
- [ ] Cross References point to related AI-OS parts, standards, and external documents.  
- [ ] Future Evolution section outlines near, medium, and long-term expectations.  
- [ ] References list is complete and formatted consistently.  
- [ ] No implementation details, technology choices, code snippets, or project management artifacts remain.  
- [ ] Spelling, grammar, and formatting have been checked (use AI-OS markdown linter if available).  
- [ ] Document builds successfully in the documentation pipeline (no broken links or missing images).  
- [ ] Reviewed by at least one peer architect for correctness and completeness.  
- [ ] Approved by the Architecture Review Board (or designated authority).  

---

# Freeze Checklist

> Use this checklist when declaring a part version as frozen (i.e., no further changes without a formal revision process).

- [ ] All Publication Checklist items are satisfied.  
- [ ] The part has been subjected to architecture review by the Authority (or delegated reviewers).  
- [ ] All review comments have been resolved and documented.  
- [ ] The part version number has been incremented according to semantic versioning (or AI-OS versioning policy).  
- [ ] A changelog entry has been written summarizing the rationale for the freeze and any significant changes since the last version.  
- [ ] The frozen version has been tagged in the repository (e.g., `v1.0.0-partX`).  
- [ ] Deprecation notices (if any) are clearly stated in the Future Evolution section.  
- [ ] Migration guidance for consumers of previous versions is provided (if applicable).  
- [ ] The part has been communicated to all stakeholders (teams that depend on or implement this part).  
- [ ] Training or enablement materials have been prepared (if significant changes warrant).  
- [ ] A process for granting exceptions or issuing errata has been defined and communicated.  
- [ ] The frozen part is the sole source of truth for its domain until a new version is released.  

---
*End of PART_TEMPLATE.md*