# Architecture Specification Part 6 — Step 8: Capability Security Architecture

## 6.8 Capability Security Architecture

### 6.8.1 Purpose

The **Capability Security Architecture** exists to establish a unified security model governing all execution facades within the Capability Space: **SkillService**, **MCPService**, **MemoryService**, and **CouncilService**.

Each execution facade operates as an independently owned, independently versioned architectural subsystem with its own Execution Contract, execution index, policy enforcement boundary, failure containment domain, and lifecycle (Sections 6.3–6.6). Cross-Capability Coordination (Section 6.7) enables composition across these facades while preserving their autonomy. Capability Security Architecture ensures that this composition — and every individual facade operation — occurs within a coherent, architecturally grounded security model.

Without a unified Capability Security Architecture, the following architectural risks would arise:

- **Capability isolation failure** — operations in one facade could inadvertently or maliciously affect the execution state, data, or policy context of another facade, violating the autonomy invariant
- **Privilege escalation** — a Consumer authorized for one capability could transitively acquire unauthorized access to another through cross-facade composition
- **Execution protection gaps** — the Execution Plane could lack consistent protection against malformed, malicious, or unauthorized execution requests across facade boundaries
- **Policy enforcement inconsistency** — cross-cutting policies (audit, quota, data residency, content filtering) could be applied in one facade but omitted or contradicted in another
- **Boundary erosion** — the architectural separation between Capability Space, Manager Space, and Event Space could degrade as security concerns leak across planes
- **Consumer trust deficit** — Consumers (Engineering Services and AI Agents) could not rely on predictable, verifiable security behavior when composing capabilities

The Capability Security Architecture addresses these risks by defining architectural security principles, a conceptual security model, and the security relationships that MUST hold across all execution facades and their compositions.

### 6.8.2 Architectural Role

Capability Security Architecture is an **architectural concern** that cross-cuts all execution facades within the Capability Space. It is not a component, service, or infrastructure element. It does not execute, store, or mediate. It defines the security invariants that the architecture MUST satisfy and the relationships that MUST hold.

#### Relationship with Capability Space

The Capability Space (Section 5.1) comprises the four execution facades and their Coordination Bus. Capability Security Architecture governs:

- **Internal security** — how each facade protects its own execution boundary, enforces its own policies, and manages its own authorization context
- **Cross-facade security** — how security context propagates (or is intentionally not propagated) when the Coordination Bus composes facades
- **Facade autonomy preservation** — ensuring that security mechanisms do not create hidden dependencies between facades that would violate Section 6.3–6.6 autonomy invariants

The Capability Space MUST NOT depend on Capability Security Architecture for its internal structure. Rather, Capability Security Architecture constrains how the Capability Space is structured and composed.

#### Relationship with Manager Space

The Manager Space (Part 4) owns platform-level security concerns: identity management, authentication, platform policy, tenant isolation, and infrastructure protection. Capability Security Architecture:

- **Consumes** Manager Space security primitives (identities, tokens, platform policies) as opaque inputs
- **MUST NOT** redefine, extend, or bypass Manager Space security mechanisms
- **MUST** map Manager Space decisions into Capability Space authorization contexts without alteration
- **MUST** ensure that Capability Space operations cannot elevate privileges beyond what Manager Space has granted

The boundary between Manager Space and Capability Space is a **security architectural boundary**. Capability Security Architecture defines how this boundary is respected within Capability Space operations.

#### Relationship with Event Space

The Event Space (Part 4) is the sole coordination substrate for asynchronous interaction (Section 6.7). Capability Security Architecture governs:

- **Event authorization** — which principals may publish or subscribe to which event streams within Capability Space operations
- **Event integrity** — ensuring events traversing the Coordination Bus cannot be forged, replayed, or tampered with in ways that violate facade security boundaries
- **Event policy** — cross-cutting policies (retention, encryption, jurisdiction) as they apply to Capability Space event flows

Event Space infrastructure security (transport encryption, broker authentication) remains a Manager Space concern. Capability Security Architecture addresses only the Capability Space semantics of event exchange.

#### Relationship with Consumers

Consumers — **Engineering Services** (Part 4) and **AI Agents** (Part 3) — invoke capabilities through the Capability Facade (Section 5.1). Capability Security Architecture ensures:

- **Consumer authorization** — a Consumer's effective permissions are the intersection of Manager Space grants and Capability Space policy
- **Consumer isolation** — one Consumer's capability execution cannot observe or affect another Consumer's capability execution unless explicitly composed
- **Consumer trust** — Consumers can reason about capability composition security using only the architectural model, without knowledge of facade internals

### 6.8.3 Security Principles

The following principles are architectural invariants. They apply to every execution facade, every cross-facade composition, and every Coordination Bus interaction. Each principle is expressed using RFC 2119 language.

#### Least Privilege

> **PRINCIPLE-SEC-001:** Every capability execution **MUST** operate with the minimum set of permissions necessary to fulfill its requested operation.

No facade **SHALL** grant ambient authority. Permissions **MUST** be scoped to the specific capability, the specific operation, and the specific Consumer context. Cross-facade compositions **MUST NOT** accumulate permissions beyond what each individual facade operation requires.

#### Deny-by-Default

> **PRINCIPLE-SEC-002:** All capability invocations **MUST** be denied unless explicitly authorized by both Manager Space and Capability Space policy.

Absence of an explicit allow policy **SHALL** be treated as denial. No facade **SHALL** implement implicit allow behaviors based on network topology, deployment zone, or historical precedent. The Coordination Bus **MUST** enforce deny-by-default for all cross-facade event flows.

#### Execution Boundary Protection

> **PRINCIPLE-SEC-003:** Each execution facade **MUST** maintain an execution boundary that cannot be crossed by any operation not explicitly authorized for that facade.

The execution boundary encompasses: the facade's execution index, its policy enforcement point, its failure containment domain, and its lifecycle state. No other facade, no Coordination Bus path, and no Consumer **SHALL** directly access or modify another facade's execution boundary internals. Cross-facade interaction **MUST** occur exclusively through the Coordination Bus's declared contracts.

#### Policy Locality

> **PRINCIPLE-SEC-004:** Security policy **MUST** be defined, owned, and enforced at the architectural layer closest to the resource it protects.

Each facade **MUST** own and enforce policies governing its own capabilities, data, and execution semantics. Cross-cutting policies **MUST** be expressed as composable policy fragments that each facade evaluates independently. No central policy engine **SHALL** supersede a facade's local policy authority. The Coordination Bus **MUST NOT** centrally evaluate policies on behalf of facades.

#### Independent Authorization

> **PRINCIPLE-SEC-005:** Authorization decisions **MUST** be made independently by each facade for its own operations, using only the authorization context explicitly provided to that facade.

A facade **MUST NOT** delegate its authorization decision to another facade. A facade **MUST NOT** assume that another facade's authorization implies its own. Cross-facade compositions **MUST** present each facade with its own authorization context derived from the Consumer's original request and the composition contract. The Coordination Bus **MUST NOT** perform authorization on behalf of facades.

#### Trust Minimization

> **PRINCIPLE-SEC-006:** No facade **SHALL** trust another facade's internal state, policy decisions, or execution integrity beyond what is explicitly declared in their Coordination Bus contracts.

Trust **MUST** be limited to: (a) the validity of events received over the Coordination Bus per the Event Space contract, (b) the identity of the originating Consumer as asserted by Manager Space, and (c) the declared semantics of the invoked capability per the Capability Definition. A facade **MUST NOT** assume another facade's policy enforcement is correct, complete, or current.

#### Auditability

> **PRINCIPLE-SEC-007:** Every capability execution and every cross-facade coordination event **MUST** produce an auditable record sufficient to reconstruct the authorization context, the policy evaluation, and the execution outcome.

Audit records **MUST** be produced at the facade that owns the operation. The Coordination Bus **MUST** produce audit records for cross-facade event flows. Audit records **MUST NOT** depend on facade internals — they **MUST** be derivable from declared contracts and authorization contexts alone.

#### Capability Autonomy

> **PRINCIPLE-SEC-008:** Security mechanisms **MUST NOT** create architectural dependencies between facades that would violate the autonomy invariants of Sections 6.3–6.6.

Each facade **MUST** be independently versionable, independently deployable, and independently policy-configurable without requiring coordinated changes to other facades. Security architecture **MUST NOT** introduce shared libraries, shared policy stores, shared key material, or shared runtime dependencies between facades that are not explicitly declared in the Coordination Bus contract.

### 6.8.4 Security Model

The Capability Security Model defines the conceptual relationships among principals, resources, policies, and boundaries within the Capability Space. It does not specify mechanisms, protocols, or implementations.

#### Trust Relationships

The model recognizes three categories of trust relationship:

**Manager Space → Capability Space (Delegation Trust)**
Manager Space authenticates Consumers and issues authorization tokens. Capability Space **MUST** treat these tokens as opaque assertions of Manager Space decisions. Capability Space **MUST NOT** validate token cryptography, **MUST NOT** introspect token claims beyond what is required for authorization mapping, and **MUST NOT** make authorization decisions that contradict Manager Space assertions.

**Capability Space ↔ Capability Facade (Contract Trust)**
The Capability Facade (Section 5.1) presents a unified invocation surface to Consumers. Each facade **MUST** trust that the Capability Facade correctly routes requests per the Capability Registry (Section 5.2). The Capability Facade **MUST** trust that each facade honors its Execution Contract. This trust is **contractual**, not transitive — it extends only to declared contracts.

**Facade ↔ Facade (Coordination Trust)**
Facades interacting via the Coordination Bus **MUST** trust only: (a) event authenticity as guaranteed by Event Space, (b) event schema conformance as guaranteed by the Coordination Bus contract, and (c) the identity of the originating Consumer as propagated in the coordination context. No facade **SHALL** trust another facade's internal policy state, execution state, or authorization decisions.

#### Security Domains

Each execution facade constitutes a **distinct security domain**. A security domain is defined by:

- **Boundary** — the execution boundary (PRINCIPLE-SEC-003)
- **Policy authority** — the facade's exclusive right to define and enforce policy for its capabilities (PRINCIPLE-SEC-004)
- **Authorization context** — the set of claims, permissions, and constraints applicable within the domain
- **Audit scope** — the set of operations subject to the domain's audit requirements (PRINCIPLE-SEC-007)

Security domains **MUST NOT** overlap. A capability **MUST** belong to exactly one security domain (its owning facade). Cross-facade compositions **MUST** traverse domain boundaries exclusively through the Coordination Bus.

#### Policy Boundaries

A **policy boundary** is the architectural seam where policy authority transitions. The model defines three policy boundaries:

**Manager Space Policy Boundary**
The boundary where Manager Space platform policies (tenant isolation, identity validation, platform quotas) are mapped into Capability Space authorization contexts. This boundary is **unidirectional** — Manager Space policies flow in; Capability Space policies do not flow out.

**Facade Policy Boundary**
The boundary surrounding each facade's security domain. Within this boundary, the facade **MUST** evaluate all applicable policies: its local policies, inherited cross-cutting policy fragments, and the mapped Manager Space authorization context. The facade **MUST** produce a single allow/deny decision. No external entity **SHALL** participate in this evaluation.

**Coordination Policy Boundary**
The boundary governing event flows on the Coordination Bus. Events crossing this boundary **MUST** be evaluated against coordination policies: event schema validity, Consumer identity propagation, cross-facade quota, and audit requirements. The Coordination Bus **MUST** enforce these policies without evaluating facade-local policies.

#### Execution Boundaries

An **execution boundary** is the runtime manifestation of a security domain's boundary. It encompasses:

- The facade's execution index and its integrity
- The facade's policy enforcement point and its integrity
- The facade's failure containment domain and its isolation
- The facade's lifecycle state and its integrity

Execution boundaries **MUST** be enforced by the facade's own runtime. The Coordination Bus **MUST NOT** mediate execution boundary enforcement. A facade **MUST** reject any operation that would violate its execution boundary, regardless of Coordination Bus authorization.

#### Identity Propagation

**Consumer identity** originates in Manager Space and propagates through the architecture as follows:

1. **Manager Space → Capability Facade** — via opaque authorization token
2. **Capability Facade → Target Facade** — via authorization context in the invocation request
3. **Facade → Coordination Bus** — via coordination context in cross-facade events
4. **Coordination Bus → Target Facade** — via coordination context in delivered events

At each step, identity **MUST** be propagated without modification, without augmentation, and without attenuation beyond what the propagation contract explicitly specifies. A facade **MUST NOT** infer additional identity claims. The Coordination Bus **MUST NOT** re-identify Consumers.

**Correlation identity** — a system-generated identifier linking related operations across facades within a single logical composition — **MAY** be introduced by the Coordination Bus. Correlation identity **MUST NOT** be usable for authorization. It **MUST** be distinct from Consumer identity.

#### Authorization Ownership

**Authorization ownership** is the architectural principle that each facade is the sole authority for authorizing operations within its security domain.

- **SkillService** owns authorization for skill invocations, skill data access, and skill execution policies
- **MCPService** owns authorization for external capability invocations, connection policies, and credential use policies
- **MemoryService** owns authorization for memory reads, writes, queries, and retention policies
- **CouncilService** owns authorization for council executions, participant policies, and deliberation policies

The Coordination Bus **does not own authorization** for any facade operation. It owns authorization only for Coordination Bus event flows (publish/subscribe/router operations).

Authorization ownership **MUST NOT** be delegated, shared, or centralized. A facade **MUST** make its own authorization decision using only its policy authority and the authorization context provided. A facade **MUST NOT** query another facade for authorization advice.

### 6.8.5 Trust Boundaries

The Capability Security Architecture defines six architectural trust boundaries within Capability Space. Each boundary represents a seam where trust assumptions change, security ownership transitions, and information flow is constrained. These boundaries are architectural — they exist regardless of deployment topology or technology choices.

#### Consumer ↔ Capability Facade Boundary

This boundary separates Consumers (Engineering Services and AI Agents) from the unified Capability Facade invocation surface.

- **Trust assumptions**: Consumers trust the Capability Facade to route invocations to the correct facade per the Capability Registry. The Capability Facade trusts Manager Space to authenticate Consumers and issue valid authorization tokens. Neither party trusts the other's internal implementation.
- **Security ownership**: Manager Space owns Consumer authentication and platform-level authorization. Capability Facade owns request routing, capability resolution, and invocation contract validation. Each facade owns its own operation authorization.
- **Information flow**: Consumer identity and authorization context flow inward from Manager Space through Capability Facade to the target facade. Capability metadata (schema, contracts, availability) flows outward to Consumers via the Capability Registry. Execution results flow back to Consumers. No facade internal state flows across this boundary.
- **Authorization boundary**: Manager Space authorization is evaluated at the Manager Space Policy Boundary. Capability Facade performs no authorization on facade operations — it validates only that the requested capability exists and the Consumer holds a valid token. Facade-level authorization occurs at the Facade Policy Boundary within the target facade.
- **Isolation expectations**: One Consumer's invocation MUST NOT influence another Consumer's invocation. The Capability Facade MUST NOT leak invocation context, capability metadata beyond Registry declarations, or execution state between Consumers.

#### Capability Facade ↔ Execution Facades Boundary

This boundary separates the unified Capability Facade from the four execution facades (SkillService, MCPService, MemoryService, CouncilService).

- **Trust assumptions**: The Capability Facade trusts each facade to honor its Execution Contract (Sections 6.3–6.6). Each facade trusts the Capability Facade to route only valid, contract-conformant requests. No facade trusts another facade's internal behavior.
- **Security ownership**: Capability Facade owns request validation, capability resolution, and routing correctness. Each execution facade owns its execution boundary enforcement, policy evaluation, and authorization decision for its operations.
- **Information flow**: Invocation requests with authorization context flow from Capability Facade to target facade. Execution results, capability metadata updates, and contract acknowledgments flow from facade to Capability Facade. Cross-facade coordination requests flow from facade to Coordination Bus (not directly to other facades).
- **Authorization boundary**: The Facade Policy Boundary resides entirely within each execution facade. The Capability Facade does not participate in facade-level authorization decisions.
- **Isolation expectations**: Each facade's execution boundary MUST be impermeable to other facades. A facade MUST NOT directly invoke another facade's internal APIs, access its execution index, or observe its policy state. All cross-facade interaction MUST traverse the Coordination Bus.

#### Execution Facade ↔ Event Space Boundary

This boundary separates each execution facade from the Event Space infrastructure that implements the Coordination Bus.

- **Trust assumptions**: Facades trust Event Space to deliver events authentically, in order per stream, and without duplication beyond at-least-once semantics. Event Space trusts facades to publish only schema-conformant events and to honor subscription contracts. Neither trusts the other's internal state.
- **Security ownership**: Event Space owns event transport integrity, broker authentication, and infrastructure-level access control. Each facade owns event content authorization (what events it may publish/subscribe), event schema conformance, and coordination context propagation.
- **Information flow**: Coordination events flow from publishing facade to Event Space to subscribing facade(s). Coordination context (Consumer identity, correlation identity, authorization context fragments) flows with events. Infrastructure metrics and health signals flow from Event Space to Manager Space (not to facades).
- **Authorization boundary**: The Coordination Policy Boundary governs event flows. Facades authorize their own publish/subscribe actions against local policy. Event Space authorizes infrastructure-level access (can this principal connect to this broker). Neither evaluates the other's policy domain.
- **Isolation expectations**: Event streams MUST be isolated by security domain. A facade MUST NOT subscribe to events it is not authorized to receive. Event Space MUST NOT route events across security domains without Coordination Bus contract authorization. Correlation identity MUST NOT leak Consumer identity across unauthorized boundaries.

#### Execution Facade ↔ Manager Space Boundary

This boundary separates each execution facade from the Manager Space platform services (identity, policy, quota, audit infrastructure).

- **Trust assumptions**: Facades trust Manager Space to provide valid identity assertions, platform policy decisions, and infrastructure services. Manager Space trusts facades to correctly map and enforce Manager Space decisions within Capability Space. Neither trusts the other's internal implementation.
- **Security ownership**: Manager Space owns identity authentication, platform policy definition, tenant isolation, resource quotas, and audit infrastructure. Each facade owns the mapping of Manager Space decisions into its local authorization context, local policy evaluation, and local audit record production.
- **Information flow**: Identity tokens and platform policy assertions flow from Manager Space to facades (unidirectional). Facade audit records and policy evaluation outcomes flow to Manager Space audit infrastructure. Facade health and quota consumption metrics flow to Manager Space.
- **Authorization boundary**: The Manager Space Policy Boundary is unidirectional. Manager Space decisions flow into Capability Space; Capability Space decisions do not flow out to alter Manager Space state.
- **Isolation expectations**: Facade internal state (execution index, policy rules, failure domain) MUST NOT be visible to Manager Space. Manager Space policy internals (identity provider configuration, platform rule engine) MUST NOT be visible to facades. The boundary is opaque in both directions.

#### Execution Facade ↔ External Providers Boundary

This boundary separates MCPService (and only MCPService) from external capability providers accessed via the Model Context Protocol or equivalent external capability interfaces.

- **Trust assumptions**: MCPService trusts external providers only to the extent declared in the Capability Definition and governed by the MCP Connection Contract. External providers trust MCPService to present valid credentials and conform to protocol contracts. No behavioral trust beyond contract conformance.
- **Security ownership**: MCPService owns connection policy, credential management, request authorization, response validation, and audit of external calls. External providers own their own authentication, authorization, and execution integrity.
- **Information flow**: Capability invocations flow from MCPService to external provider. Results, errors, and capability metadata flow back. Credentials and authentication artifacts flow from MCPService credential store to external provider (unidirectional). No MCPService internal state flows to external providers.
- **Authorization boundary**: MCPService authorizes each external invocation against its Facade Policy Boundary before egress. External provider authorization decisions are opaque to MCPService — MCPService does not delegate its authorization to the provider.
- **Isolation expectations**: External provider failures, compromises, or policy changes MUST NOT propagate into MCPService execution boundary or other facades. MCPService MUST enforce connection isolation, credential isolation, and quota isolation per external provider. No shared state, shared credentials, or shared failure domains across providers.

#### Cross-Facade Coordination Boundary

This boundary governs interactions between execution facades mediated exclusively by the Coordination Bus (Section 6.7).

- **Trust assumptions**: Facades trust the Coordination Bus to deliver events per the Coordination Bus contract (schema validity, ordering guarantees, delivery semantics). Facades do not trust each other's internal state, policy decisions, or execution integrity. The Coordination Bus trusts facades to publish valid events and honor subscription contracts.
- **Security ownership**: Coordination Bus owns event routing, schema validation, coordination policy enforcement (quota, audit, jurisdiction), and correlation identity management. Each facade owns its local policy evaluation for publish/subscribe actions, its authorization context contribution to coordination events, and its consumption authorization for received events.
- **Information flow**: Coordination events flow facade → Coordination Bus → facade(s). Coordination context (Consumer identity, correlation identity, authorization context fragments) flows with events. No facade internal state, policy state, or execution state flows across this boundary.
- **Authorization boundary**: Three authorization boundaries intersect here: (1) publishing facade's Facade Policy Boundary for publish authorization, (2) Coordination Policy Boundary for event flow authorization, (3) consuming facade's Facade Policy Boundary for consume authorization. All three MUST allow for the event to be delivered.
- **Isolation expectations**: Cross-facade compositions MUST NOT create transitive trust. Facade A invoking Facade B which publishes an event to Facade C does not grant Facade A any trust relationship with Facade C. Each facade pair interacts only through explicitly declared Coordination Bus contracts. Correlation identity links operations but conveys no authorization.

### 6.8.6 Identity & Authorization Architecture

The Capability Security Architecture defines an identity and authorization model that is decentralized, boundary-aligned, and composition-safe. It does not define authentication mechanisms, token formats, or cryptographic protocols — those are Manager Space concerns. It defines the architectural relationships among identity, authorization, and execution boundaries.

#### Identity Ownership

**Manager Space owns identity.** Manager Space authenticates principals (Consumers, system components), issues identity assertions, and manages identity lifecycle. Capability Space does not create, validate, or modify identities.

**Capability Space consumes identity.** Each facade receives Consumer identity as an opaque assertion from Manager Space via the Capability Facade. The facade treats identity as an input to its authorization evaluation, not as an object it manages.

**No facade owns identity.** No execution facade maintains identity stores, performs authentication, or issues identity tokens. Identity is exclusively a Manager Space concern.

#### Authorization Ownership

**Each facade owns authorization for its operations.** As defined in Section 6.8.4, SkillService, MCPService, MemoryService, and CouncilService each hold exclusive authorization authority within their security domains.

**Authorization ownership is non-delegable.** A facade MUST NOT delegate its authorization decision to another facade, to the Coordination Bus, to the Capability Facade, or to Manager Space. Manager Space provides the authorization context; the facade makes the decision.

**Authorization ownership is non-shared.** No two facades share authorization authority for the same operation. No central authorization service evaluates facade-local policies.

**The Coordination Bus owns authorization only for event flows.** It authorizes publish/subscribe/router operations against coordination policies. It does not authorize facade operations.

#### Authorization Context

**Authorization context** is the set of claims, permissions, constraints, and environmental attributes that a facade uses to make its authorization decision. It is derived from:

- Manager Space identity assertion (opaque token)
- Capability Definition declared requirements
- Composition contract (for cross-facade invocations)
- Local policy configuration
- Environmental constraints (quotas, jurisdictions, time windows)

**Authorization context is facade-local.** Each facade receives and evaluates its own authorization context. The Coordination Bus does not construct, merge, or evaluate authorization contexts for facade operations.

**Authorization context is immutable per invocation.** Once an invocation enters a facade's Facade Policy Boundary, the authorization context for that invocation does not change. Cross-facade coordination events carry coordination context fragments, not full authorization contexts.

#### Identity Propagation

**Identity propagates unidirectionally and unmodified.** Consumer identity flows: Manager Space → Capability Facade → Target Facade → Coordination Bus → Target Facade(s). At each hop, the identity assertion is passed without modification, augmentation, or attenuation.

**Facades do not enrich identity.** A facade MUST NOT add claims, roles, or attributes to the identity it received. It MUST NOT look up additional identity information from external sources during authorization.

**Coordination Bus does not re-identify.** The Coordination Bus propagates the Consumer identity it receives in coordination context. It does not validate, transform, or substitute identity.

**Correlation identity is distinct.** The Coordination Bus may introduce a correlation identity to link related operations across facades. Correlation identity is a system-generated opaque identifier. It is not usable for authorization. It does not replace Consumer identity. It must not be confused with Consumer identity by any facade.

#### Least Privilege

**Authorization decisions enforce least privilege.** Each facade evaluates whether the authorization context permits the specific operation on the specific resource in the specific context. Ambient or role-based permissions that exceed the operation's requirements are not sufficient.

**Cross-facade composition does not accumulate privilege.** When Facade A invokes Facade B via the Coordination Bus which delivers an event to Facade C, Facade C's authorization decision is based solely on Facade C's policy and the coordination context provided. It does not inherit Facade A's permissions, nor does it assume Facade B's authorization was sufficient for Facade C.

**Coordination context carries minimum necessary authorization fragments.** The Coordination Bus includes in coordination events only the authorization context fragments explicitly declared in the Coordination Bus contract for that event type. No facade receives more context than the contract specifies.

#### Policy Locality

**Policy evaluation is local to each facade's Facade Policy Boundary.** A facade evaluates all applicable policies — local, cross-cutting fragments, and mapped Manager Space context — within its own boundary. No external entity participates.

**Cross-cutting policies are fragmentized.** Platform-wide policies (audit, quota, data residency, content filtering) are expressed as policy fragments that each facade independently incorporates into its local evaluation. There is no central policy evaluation engine.

**Policy configuration is facade-autonomous.** Each facade manages its own policy configuration, versioning, and deployment independently. Security architecture does not require coordinated policy deployment across facades.

#### Authorization Independence

**Each facade makes its authorization decision independently.** Given the same authorization context, two facades may reach different allow/deny decisions based on their respective policies. This is architecturally correct — each facade protects its own resources.

**No facade queries another for authorization.** Facade A MUST NOT ask Facade B "would you allow this?" before making its own decision. Facade B MUST NOT ask Facade A "did you authorize this?" before making its own decision.

**Coordination Bus does not pre-authorize.** The Coordination Bus evaluates coordination policies for event flows only. It does not evaluate facade operation policies. A Coordination Bus allow decision does not imply any facade allow decision.

#### Capability Autonomy

**Authorization autonomy is a facet of capability autonomy.** The ability to independently authorize operations is essential to the facade autonomy invariants of Sections 6.3–6.6. Security mechanisms that would centralize or coordinate authorization violate capability autonomy.

**Facade versioning includes authorization logic.** When a facade versions its Execution Contract, it may also version its authorization logic. Other facades do not need to coordinate — they interact via declared contracts and Coordination Bus contracts.

#### Authorization Consistency

**Authorization consistency is achieved through architectural constraints, not coordination.** The architecture ensures consistent security behavior by:

- Requiring all facades to consume the same Manager Space identity assertions
- Requiring all facades to enforce the same security principles (Section 6.8.3)
- Requiring cross-facade compositions to traverse the Coordination Bus with explicit contracts
- Requiring audit records to be produced at each facade for its own decisions

**No global authorization state exists.** There is no single source of truth for "what is authorized." Authorization is a local decision at each Facade Policy Boundary, producing a local audit record. Consistency is an emergent property of architectural conformance, not a centralized computation.

### 6.8.7 Security Invariants

The following invariants are architectural laws that MUST hold in every valid architecture instantiation. They are expressed using RFC 2119 language and prefixed **INV-SEC**. They complement but do not repeat the principles of Section 6.8.3.

> **INV-SEC-001 (Execution Boundary Integrity):** Each execution facade's execution boundary **MUST** remain intact under all circumstances — including normal operation, cross-facade composition, failure conditions, and Coordination Bus events. No operation originating outside the facade's declared contracts **SHALL** modify the facade's execution index, policy enforcement point, failure containment domain, or lifecycle state.

> **INV-SEC-002 (Authorization Locality):** Every authorization decision for a facade operation **MUST** be made within that facade's Facade Policy Boundary by that facade's policy evaluation logic, using only the authorization context explicitly provided to that facade. No authorization decision for a facade operation **SHALL** be made by any other facade, the Coordination Bus, the Capability Facade, or Manager Space.

> **INV-SEC-003 (Policy Completeness):** For every capability operation defined in a facade's Execution Contract, that facade **MUST** have a defined policy evaluation that produces an allow/deny decision. There **SHALL NOT** exist operations that bypass policy evaluation, default to allow, or rely on external policy evaluation.

> **INV-SEC-004 (Trust Minimization):** No facade **SHALL** depend on the correctness, completeness, or currentness of another facade's policy enforcement, execution state, or internal data structures. Trust **SHALL** be limited to: (a) Coordination Bus contract conformance, (b) Event Space delivery guarantees, (c) Manager Space identity assertions, and (d) Capability Definition declared semantics.

> **INV-SEC-005 (Least Privilege Enforcement):** Every capability execution **MUST** be authorized against a permission set that is minimal for that specific operation, capability, and Consumer context. No facade **SHALL** grant permissions that exceed the operation's declared requirements. Cross-facade compositions **SHALL NOT** result in effective permissions exceeding the union of individually authorized operations.

> **INV-SEC-006 (Facade Autonomy Preservation):** Security mechanisms **SHALL NOT** introduce architectural couplings between facades (shared libraries, shared policy stores, shared key material, shared runtime dependencies, synchronized deployment requirements, or shared failure domains) that are not explicitly declared in Coordination Bus contracts. Each facade **SHALL** remain independently versionable, deployable, and policy-configurable.

> **INV-SEC-007 (Security Domain Isolation):** Security domains **SHALL NOT** overlap. Each capability **SHALL** belong to exactly one security domain (its owning facade). No operation **SHALL** simultaneously reside in multiple security domains. Cross-domain operations **SHALL** traverse domain boundaries exclusively through Coordination Bus contracts.

> **INV-SEC-008 (Event Space Mediation):** All asynchronous cross-facade interactions **SHALL** be mediated by the Coordination Bus operating over Event Space. No facade **SHALL** directly invoke another facade's internal APIs, share memory, exchange signals, or synchronize state outside the Coordination Bus. The Coordination Bus **SHALL** enforce coordination policies on all mediated event flows.

> **INV-SEC-009 (Audit Completeness):** Every capability execution and every Coordination Bus event flow **SHALL** produce an audit record at the owning facade or Coordination Bus respectively. Audit records **SHALL** capture: the invoking identity, the operation requested, the authorization context, the policy evaluation outcome, and the execution result. Audit records **SHALL** be derivable from declared contracts and authorization contexts without dependence on facade internals.

> **INV-SEC-010 (Identity Integrity):** Consumer identity **SHALL** propagate from Manager Space through Capability Facade to target facade(s) and through Coordination Bus without modification, augmentation, or attenuation. No facade **SHALL** alter the identity assertion. The Coordination Bus **SHALL NOT** re-identify or synthesize Consumer identity.

> **INV-SEC-011 (Authorization Independence):** Each facade's authorization decision **SHALL** be functionally independent of other facades' authorization decisions. A facade **SHALL NOT** require, request, or wait for another facade's authorization decision before producing its own. A facade's allow decision **SHALL NOT** imply another facade's allow decision, and vice versa.

> **INV-SEC-012 (Correlation Identity Separation):** Correlation identity **SHALL** be architecturally distinct from Consumer identity. Correlation identity **SHALL NOT** appear in authorization contexts. Correlation identity **SHALL NOT** be used for access control decisions. Correlation identity **SHALL** be usable only for operational correlation (tracing, debugging, audit linkage) within the Coordination Bus and consuming facades.

> **INV-SEC-013 (No Privilege Escalation):** No composition of capabilities, no Coordination Bus event flow, and no Manager Space mapping **SHALL** result in a Consumer acquiring effective permissions in any facade that exceed the intersection of Manager Space grants and that facade's local policy for the specific operation.

> **INV-SEC-014 (No Hidden Trust Relationships):** The architecture **SHALL NOT** contain trust relationships that are not explicitly declared in: (a) Capability Definitions, (b) Execution Contracts (Sections 6.3–6.6), (c) Coordination Bus contracts (Section 6.7), or (d) the security model of this section. Implicit trust arising from deployment topology, shared infrastructure, historical behavior, or organizational boundaries **SHALL NOT** be architecturally valid.

> **INV-SEC-015 (Manager Space Boundary Unidirectionality):** Manager Space policy decisions **SHALL** flow into Capability Space authorization contexts. Capability Space policy decisions, execution outcomes, or internal state **SHALL NOT** flow back to alter Manager Space policy, identity, or quota state. The Manager Space Policy Boundary is architecturally unidirectional.

> **INV-SEC-016 (Coordination Policy Independence):** Coordination Bus policy evaluation **SHALL NOT** depend on facade-local policy state. Coordination Bus policy evaluation **SHALL NOT** duplicate facade-local policy evaluation. Coordination Bus policy evaluation **SHALL** address only: event schema validity, Consumer identity propagation conformance, cross-facade quota, jurisdiction, and audit requirements.

> **INV-SEC-017 (Credential Boundary Containment):** Credentials for external providers (MCPService) **SHALL** be confined to MCPService's security domain. No other facade **SHALL** access, observe, or use external provider credentials. Credential lifecycle, rotation, and revocation **SHALL** be managed exclusively within MCPService's Facade Policy Boundary.

> **INV-SEC-018 (Failure Containment Security):** A security failure in one facade (policy misconfiguration, credential compromise, audit gap) **SHALL NOT** compromise the execution boundary, policy enforcement, or authorization integrity of any other facade. Failure containment domains (Sections 6.3–6.6) **SHALL** align with security domains.

### 6.8.8 Failure & Isolation

The Capability Security Architecture defines architectural isolation guarantees that hold under all operational conditions, including partial failures, security incidents, and cross-facade composition errors. These guarantees are structural — they derive from boundary definitions, ownership assignments, and mediation requirements — not from runtime detection or recovery mechanisms.

#### Security Domain Containment

Each facade constitutes a security domain (Section 6.8.4). The architecture guarantees that a security violation, policy misconfiguration, credential compromise, or audit failure within one security domain **SHALL NOT** propagate into another security domain. Containment is achieved through:

- **Execution boundary enforcement** — each facade's execution boundary is enforced by that facade alone (INV-SEC-001)
- **Authorization locality** — authorization decisions are made locally within each Facade Policy Boundary (INV-SEC-002)
- **Trust minimization** — facades do not depend on each other's internal security state (INV-SEC-004)
- **Credential boundary containment** — external provider credentials are confined to MCPService (INV-SEC-017)

No shared state, shared policy store, shared key material, or shared runtime component exists between security domains that would allow cross-domain contamination.

#### Authorization Failure Isolation

An authorization failure in one facade (deny decision, policy evaluation error, missing policy fragment) **SHALL NOT** cause, mask, or alter authorization behavior in any other facade. Each facade's authorization decision is functionally independent (INV-SEC-011). A Coordination Bus event flow may be rejected at the Coordination Policy Boundary without affecting the publishing facade's prior authorization or the consuming facade's local policy state.

Authorization failure isolation means:

- Facade A's deny decision does not constrain Facade B's allow decision
- Facade A's policy evaluation timeout does not block Facade B's policy evaluation
- Facade A's audit gap does not create an authorization gap in Facade B
- Coordination Bus reject decisions do not cascade into facade authorization logic

#### Policy Evaluation Isolation

Policy evaluation within each Facade Policy Boundary **SHALL** be architecturally isolated from all other policy evaluations. This isolation is achieved through:

- **Policy fragment independence** — cross-cutting policies are expressed as independent fragments evaluated locally by each facade (PRINCIPLE-SEC-004)
- **No central policy engine** — there is no shared policy evaluation runtime whose failure could affect multiple facades
- **Local policy configuration** — each facade manages its own policy versioning, deployment, and rollback (Section 6.8.6)

Policy evaluation isolation ensures that a policy syntax error, evaluation loop, or resource exhaustion in one facade's policy engine cannot affect policy evaluation in another facade.

#### Identity Integrity During Failures

Consumer identity propagation **SHALL** maintain integrity regardless of failure conditions in any facade or the Coordination Bus. Identity integrity is guaranteed by:

- **Unidirectional flow** — identity flows only from Manager Space inward (INV-SEC-010, INV-SEC-015)
- **No identity enrichment** — facades never modify identity assertions (Section 6.8.6)
- **Coordination Bus pass-through** — the Coordination Bus propagates identity without validation or transformation (INV-SEC-010)
- **Opaque token model** — Manager Space tokens are treated as opaque; facade failures cannot cause token validation bypasses because facades do not validate tokens

Even under partial system failure (Coordination Bus unavailable, one facade unreachable, Manager Space latency), the identity assertions that do reach facades remain authentic and unmodified.

#### Audit Continuity

Audit record production **SHALL** continue at each facade and the Coordination Bus independently of failures elsewhere. Audit continuity is guaranteed by:

- **Local audit ownership** — each facade produces its own audit records (PRINCIPLE-SEC-007, INV-SEC-009)
- **No cross-facade audit dependencies** — Facade A's audit pipeline does not depend on Facade B's availability
- **Coordination Bus independent audit** — the Coordination Bus audits event flows regardless of facade audit status
- **Manager Space infrastructure independence** — audit transport to Manager Space audit infrastructure is a Manager Space concern; facade audit record generation does not require Manager Space availability

A facade experiencing a security failure (credential compromise, policy bypass) **MUST** still produce audit records for subsequent operations. Audit continuity is an architectural requirement, not an operational best practice.

#### Execution Boundary Preservation

The execution boundary of each facade (INV-SEC-001) **MUST** remain intact under all failure conditions. Specifically:

- Cross-facade Coordination Bus events **SHALL NOT** carry operations that modify another facade's execution index, policy enforcement point, failure containment domain, or lifecycle state
- A compromised or malfunctioning facade **SHALL NOT** be able to issue Coordination Bus events that violate another facade's execution boundary — the Coordination Bus contract schema and coordination policy enforcement prevent this
- Manager Space operations **SHALL NOT** directly modify facade execution boundaries — the Manager Space Policy Boundary is unidirectional (INV-SEC-015)
- External provider interactions via MCPService **SHALL NOT** affect other facades' execution boundaries — credential boundary containment (INV-SEC-017) and MCPService's exclusive external provider ownership enforce this

Execution boundary preservation means that the set of operations that can legally mutate a facade's execution state is fixed by its Execution Contract and Coordination Bus contracts, and cannot be expanded by any failure condition.

#### Trust Boundary Preservation

The six trust boundaries defined in Section 6.8.5 **SHALL** maintain their trust assumptions, security ownership, and isolation expectations under all failure conditions. Trust boundary preservation means:

- A failure in one trust domain does not cause another trust domain to expand its trust assumptions
- A facade does not begin trusting another facade's internal state due to Coordination Bus failure
- The Capability Facade does not begin performing facade-level authorization due to target facade unavailability
- Event Space infrastructure failure does not cause facades to bypass the Coordination Policy Boundary
- External provider failure does not cause MCPService to relax connection policy or credential isolation

Trust boundaries are architectural constructs, not runtime conditions. Their preservation is a property of the architecture's structure, not of runtime monitoring.

#### Coordination Independence During Failures

The Coordination Bus **SHALL** continue to enforce coordination policies on event flows independently of facade failures. Coordination independence means:

- Coordination Policy Boundary evaluation does not require facade availability
- Event schema validation, quota enforcement, jurisdiction checking, and audit record production at the Coordination Bus proceed regardless of individual facade state
- Correlation identity management continues independently of facade health
- The Coordination Bus does not enter a "degraded trust" mode that relaxes coordination policies when facades fail

Conversely, facade policy evaluation **SHALL** continue independently of Coordination Bus availability. A facade receiving a direct invocation (not via Coordination Bus) evaluates its Facade Policy Boundary normally even if the Coordination Bus is unavailable. Cross-facade compositions simply do not complete until the Coordination Bus recovers — no facade substitutes local evaluation for Coordination Bus mediation.

### 6.8.9 Architecture Decision Records

The following Architecture Decision Records capture the key security architectural decisions and their rationale. Each ADR follows the format: Decision, Rationale, Consequences.

#### ADR-6.8.1: Security Enforced by Architectural Boundaries

**Decision:** Security is enforced by architectural boundaries (execution boundaries, policy boundaries, trust boundaries) rather than by a centralized runtime enforcement component.

**Rationale:** A centralized security runtime would create a single point of failure, a single point of policy bottleneck, and an architectural dependency that violates facade autonomy (Sections 6.3–6.6). Architectural boundaries distribute enforcement to the owners of the resources being protected, aligning security ownership with resource ownership. This follows the Policy Locality principle (PRINCIPLE-SEC-004) and the Capability Autonomy principle (PRINCIPLE-SEC-008).

**Consequences:**
- Each facade implements its own policy enforcement point
- No central policy decision point exists to query, cache, or synchronize
- Policy changes deploy independently per facade
- Consistency is achieved through architectural constraints, not centralized coordination
- Audit records are produced locally at each enforcement point

#### ADR-6.8.2: Authorization Ownership Belongs Exclusively to Execution Facades

**Decision:** Each execution facade (SkillService, MCPService, MemoryService, CouncilService) is the sole authority for authorizing operations within its security domain. Authorization ownership cannot be delegated, shared, or centralized.

**Rationale:** Authorization is the mechanism by which a facade protects its resources. Delegating authorization would require the facade to trust another component's decisions about its own resources, violating Trust Minimization (PRINCIPLE-SEC-006) and creating hidden dependencies. Independent authorization enables facade autonomy — each facade can evolve its authorization logic with its Execution Contract without coordinating with other facades.

**Consequences:**
- Facades never ask each other for authorization decisions
- The Coordination Bus does not pre-authorize facade operations
- Manager Space provides identity and platform policy context but does not make facade-level authorization decisions
- Authorization logic versions with the facade's Execution Contract
- Cross-facade compositions present each facade with its own authorization context

#### ADR-6.8.3: Identity Ownership Belongs Exclusively to Manager Space

**Decision:** Manager Space exclusively owns identity: authentication, identity assertions, identity lifecycle, and identity provider integration. Capability Space consumes identity as opaque assertions; no facade creates, validates, enriches, or manages identities.

**Rationale:** Separating identity from authorization cleanly partitions platform concerns (Manager Space) from capability concerns (Capability Space). If facades managed identity, they would need identity infrastructure, creating shared dependencies and violating autonomy. If Manager Space made authorization decisions, it would need capability-specific policy knowledge, violating Policy Locality.

**Consequences:**
- Facades treat identity tokens as opaque assertions
- Facades do not perform token validation, introspection, or claim enrichment
- Identity propagation is unidirectional and unmodified
- Correlation identity (system-generated) is distinct from Consumer identity (Manager Space-owned)
- Manager Space can evolve identity infrastructure without Capability Space changes

#### ADR-6.8.4: Trust Relationships Are Explicit and Contract-Based

**Decision:** All trust relationships within Capability Space are explicitly declared in Capability Definitions, Execution Contracts, Coordination Bus contracts, or this security model. No implicit trust based on deployment topology, shared infrastructure, organizational boundaries, or historical behavior is architecturally valid.

**Rationale:** Implicit trust creates hidden dependencies that violate facade autonomy and make security reasoning impossible at the architectural level. Explicit contracts enable independent verification, versioning, and composition. The INV-SEC-014 invariant (No Hidden Trust Relationships) codifies this decision.

**Consequences:**
- Three trust relationship categories: Delegation Trust, Contract Trust, Coordination Trust (Section 6.8.4)
- Each trust assumption is traceable to a declared contract
- Deployment changes (colocation, network zones) do not alter trust assumptions
- Security reviews can enumerate all trust relationships from architecture documents
- New compositions require explicit contract declaration

#### ADR-6.8.5: Capability Security Preserves Facade Autonomy

**Decision:** The Capability Security Architecture is constrained to preserve the facade autonomy invariants of Sections 6.3–6.6. Security mechanisms must not introduce shared libraries, shared policy stores, shared key material, shared runtime dependencies, synchronized deployment requirements, or shared failure domains between facades.

**Rationale:** Facade autonomy is a foundational architectural invariant of the Execution Plane (Sections 6.3–6.6). If security mechanisms compromised autonomy, the Execution Plane would lose its defining property: independently versioned, independently deployable, independently operable subsystems. The Capability Autonomy principle (PRINCIPLE-SEC-008) and INV-SEC-006 codify this constraint.

**Consequences:**
- Each facade implements its own policy enforcement logic
- Policy configuration is per-facade, not centralized
- Credential management is per-facade (MCPService owns external credentials; other facades do not use them)
- Audit record format and content are per-facade (though derived from common contract principles)
- Cross-facade security coordination occurs only through Coordination Bus contracts

### 6.8.10 Conformance Requirements

An architecture instantiation conforms to the Capability Security Architecture if and only if all the following requirements are satisfied. Requirements are expressed using RFC 2119 language.

#### Security Domain Isolation

- **REQ-SEC-001:** Each execution facade **SHALL** constitute a distinct security domain with a non-overlapping boundary, exclusive policy authority, dedicated authorization context, and isolated audit scope.
- **REQ-SEC-002:** No capability **SHALL** belong to more than one security domain.
- **REQ-SEC-003:** Cross-domain operations **SHALL** traverse domain boundaries exclusively through Coordination Bus contracts.
- **REQ-SEC-004:** No shared state, shared policy store, shared key material, or shared runtime component **SHALL** exist between security domains.

#### Trust Boundary Preservation

- **REQ-SEC-005:** The six trust boundaries defined in Section 6.8.5 **SHALL** be preserved in the architecture instantiation with their declared trust assumptions, security ownership, information flow constraints, authorization boundaries, and isolation expectations.
- **REQ-SEC-006:** No trust relationship **SHALL** exist that is not explicitly declared in a Capability Definition, Execution Contract, Coordination Bus contract, or this security model.
- **REQ-SEC-007:** Deployment topology, shared infrastructure, and organizational boundaries **SHALL NOT** create or imply trust relationships beyond those declared.

#### Execution Boundary Integrity

- **REQ-SEC-008:** Each facade's execution boundary **SHALL** be enforceable by that facade alone, without mediation by the Coordination Bus, Capability Facade, or any other facade.
- **REQ-SEC-009:** No operation originating outside a facade's declared contracts **SHALL** be capable of modifying the facade's execution index, policy enforcement point, failure containment domain, or lifecycle state.
- **REQ-SEC-010:** Coordination Bus event schemas **SHALL NOT** include operations that mutate another facade's execution boundary internals.

#### Authorization Locality

- **REQ-SEC-011:** Every facade operation **SHALL** be authorized by that facade's policy evaluation logic within that facade's Facade Policy Boundary.
- **REQ-SEC-012:** No facade **SHALL** delegate its authorization decision to another facade, the Coordination Bus, the Capability Facade, or Manager Space.
- **REQ-SEC-013:** No central policy evaluation component **SHALL** evaluate facade-local policies on behalf of facades.
- **REQ-SEC-014:** The Coordination Bus **SHALL** evaluate only coordination policies (event schema, identity propagation, quota, jurisdiction, audit) and **SHALL NOT** evaluate facade operation policies.

#### Identity Propagation Correctness

- **REQ-SEC-015:** Consumer identity **SHALL** propagate unidirectionally from Manager Space through Capability Facade to target facade(s) and through Coordination Bus to target facade(s) without modification, augmentation, or attenuation.
- **REQ-SEC-016:** No facade **SHALL** enrich, validate, transform, or substitute the Consumer identity assertion it receives.
- **REQ-SEC-017:** The Coordination Bus **SHALL NOT** re-identify Consumers or synthesize identity assertions.
- **REQ-SEC-018:** Correlation identity **SHALL** be architecturally distinct from Consumer identity, **SHALL NOT** appear in authorization contexts, and **SHALL NOT** be used for access control decisions.

#### No Privilege Escalation

- **REQ-SEC-019:** For every capability operation, the effective permissions **SHALL** be the intersection of Manager Space grants and the target facade's local policy for that specific operation.
- **REQ-SEC-020:** Cross-facade compositions **SHALL NOT** result in effective permissions exceeding the union of individually authorized operations.
- **REQ-SEC-021:** Coordination context **SHALL** carry only the authorization context fragments explicitly declared in the Coordination Bus contract for that event type.

#### Event Space Mediation

- **REQ-SEC-022:** All asynchronous cross-facade interactions **SHALL** be mediated by the Coordination Bus operating over Event Space.
- **REQ-SEC-023:** No facade **SHALL** directly invoke another facade's internal APIs, share memory, exchange signals, or synchronize state outside the Coordination Bus.
- **REQ-SEC-024:** The Coordination Bus **SHALL** enforce coordination policies on all mediated event flows.
- **REQ-SEC-025:** Event streams **SHALL** be isolated by security domain; Event Space **SHALL NOT** route events across security domains without Coordination Bus contract authorization.

#### Audit Completeness

- **REQ-SEC-026:** Every capability execution **SHALL** produce an audit record at the owning facade capturing: invoking identity, operation requested, authorization context, policy evaluation outcome, and execution result.
- **REQ-SEC-027:** Every Coordination Bus event flow **SHALL** produce an audit record at the Coordination Bus capturing: publishing facade, event type, coordination context, coordination policy evaluation outcome, and delivery disposition.
- **REQ-SEC-028:** Audit records **SHALL** be derivable from declared contracts and authorization contexts without dependence on facade internals.
- **REQ-SEC-029:** Audit record production **SHALL** be independent across facades and the Coordination Bus — no audit pipeline dependency on another component's availability.

#### Facade Autonomy

- **REQ-SEC-030:** Each facade **SHALL** be independently versionable, independently deployable, and independently policy-configurable without requiring coordinated changes to other facades.
- **REQ-SEC-031:** Security mechanisms **SHALL NOT** introduce shared libraries, shared policy stores, shared key material, shared runtime dependencies, synchronized deployment requirements, or shared failure domains between facades beyond what is declared in Coordination Bus contracts.
- **REQ-SEC-032:** Facade authorization logic **SHALL** version with the facade's Execution Contract without requiring other facades to coordinate.

#### Policy Completeness

- **REQ-SEC-033:** For every capability operation defined in a facade's Execution Contract, that facade **SHALL** have a defined policy evaluation that produces an allow/deny decision.
- **REQ-SEC-034:** No operation **SHALL** bypass policy evaluation, default to allow, or rely on external policy evaluation.
- **REQ-SEC-035:** Cross-cutting policies **SHALL** be expressed as composable policy fragments that each facade evaluates independently.

#### Invariant Preservation

- **REQ-SEC-036:** All invariants defined in Section 6.8.7 (INV-SEC-001 through INV-SEC-018) **SHALL** hold in the architecture instantiation.
- **REQ-SEC-037:** All principles defined in Section 6.8.3 (PRINCIPLE-SEC-001 through PRINCIPLE-SEC-008) **SHALL** be satisfied by the architecture instantiation.
- **REQ-SEC-038:** The security model defined in Section 6.8.4 (trust relationships, security domains, policy boundaries, execution boundaries, identity propagation, authorization ownership) **SHALL** be structurally realized in the architecture instantiation.
- **REQ-SEC-039:** The trust boundaries defined in Section 6.8.5 **SHALL** be preserved with their declared properties.
- **REQ-SEC-040:** The isolation guarantees defined in Section 6.8.8 **SHALL** be architecturally guaranteed, not merely operationally implemented.