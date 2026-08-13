# Part 14 — Integration Glossary

> **Purpose:** This glossary provides standardized terminology for Part 14 integration documentation. It defines how terms are used within the integration context and records terminology conflicts where source Parts use different meanings.
>
> **Authority:** This glossary does not create architectural authority and does not override terminology defined by an authoritative source Part. When an AI-OS-specific meaning is defined by an authoritative Part, that source remains authoritative.
>
> **Status:** ACTIVE
>
> **Version:** 1.1.0
>
> **Scope:** Integration terminology only. This document does not create new architecture, interfaces, schemas, events, protocols, guarantees, or implementation requirements.

---

## 1. Glossary Authority

### 1.1 Source Authority

Terminology defined by an authoritative Part remains authoritative within that Part's architectural domain.

Part 14 uses terminology from source Parts to document integration relationships.

This glossary:

- MUST NOT override an authoritative source Part.
- MUST NOT invent architectural terminology.
- MUST NOT promote proposed terminology to existing architecture.
- MUST preserve unresolved terminology conflicts.
- MUST distinguish source-defined terminology from Part 14-derived terminology.

### 1.2 AI-OS-Specific Meaning

When an AI-OS-specific meaning is explicitly sourced to an authoritative Part, that source-defined meaning should be used in AI-OS documentation.

The glossary does not override the authoritative source.

Industry-standard terminology may be used for explanatory purposes when it does not conflict with source-defined AI-OS terminology.

### 1.3 Term Existence vs Mechanism Existence

The existence of a term in documentation does not prove that the corresponding mechanism exists in the implemented architecture.

For example:

- Defining "RPC" does not establish that AI-OS uses RPC.
- Defining "Schema Registry" does not establish that AI-OS implements a Schema Registry.
- Defining "Circuit Breaker" does not establish that AI-OS implements circuit breakers.
- Defining "Event Fabric" does not establish an Event Fabric architecture.

Where a mechanism is not established by source Parts, the term MUST be classified appropriately.

---

# 2. Status Taxonomy

Part 14 uses the following terminology-status classifications.

| Status | Meaning |
|---|---|
| **EXISTING** | Explicitly defined by an authoritative source Part or accepted/active ADR within its scope. |
| **DERIVED** | Inferred from one or more authoritative sources without introducing new architecture. |
| **ASSUMPTION** | A stated assumption required for integration analysis but not established as architecture. |
| **UNSPECIFIED** | The source mentions the concept but does not define its complete meaning or contract. |
| **GAP** | Information required for integration is absent from the authoritative sources. |
| **PROPOSED** | A Part 14 recommendation or future design concept; not current architecture. |
| **FUTURE** | Explicitly deferred or planned for a later architectural stage. |
| **CONFLICT** | Authoritative sources define materially different meanings or contracts. |

### 2.1 Classification Rule

A term MUST NOT be classified as `EXISTING` merely because:

- it appears in a Part 14 document;
- it is common industry terminology;
- it is technically reasonable;
- it would be useful for implementation;
- it is inferred from an architectural pattern;
- it appears in a draft ADR.

`EXISTING` requires source evidence.

---

# 3. Core Architectural Terms

## 3.1 AI-OS

**Status:** EXISTING

The overall architectural system documented by source Parts and integrated by Part 14.

Part 14 documents relationships among its architectural domains but does not redefine AI-OS architecture.

---

## 3.2 Architecture Part

**Status:** DERIVED

A numbered architectural specification defining a particular architectural domain, subsystem, governance area, or cross-cutting concern within AI-OS.

Each Part is authoritative within its explicitly defined domain.

A later-numbered Part does not automatically override an earlier-numbered Part.

---

## 3.3 Architectural Domain

**Status:** DERIVED

The scope within which a specific Part defines authoritative architectural decisions.

Domain-specific authority prevents Part numbering from being treated as a universal precedence hierarchy.

---

## 3.4 Architectural Boundary

**Status:** DERIVED

A defined separation between architectural components, services, systems, trust domains, or external systems.

A boundary may be:

- internal;
- service-level;
- capability-level;
- integration-level;
- external.

The exact boundary semantics remain source-dependent.

---

## 3.5 Component

**Status:** EXISTING

A named architectural unit defined by the source Parts.

The exact meaning of Component is source-dependent. Source authority: Part 1 §1.7.1 (Core Components), Part 3 §3.4 (ServiceRegistration).

Part 14 does not merge distinct component definitions merely because their names appear similar.

Component-to-component communication flows through declared interfaces and the EventBus (Part 0 §0.4 Principle 1, Part 1 §1.7.4 CC-IR-001). Lifecycle, registration, discovery, and accessor interactions may be defined separately by source Parts and are not subsumed under the EventBus communication path.

---

## 3.6 Core Component

**Status:** EXISTING

A component explicitly identified as part of the AI-OS core architecture.

The authoritative source Part defines the component's actual responsibility and boundary.

Source authority: Part 1 §1.7.1 (C1 EventBus, C2 ServiceRegistry, C3 ConfigurationManager, C4 LifecycleManager, etc.).

---

## 3.7 Core Manager

**Status:** EXISTING

A manager responsible for a defined architectural capability within the core system.

- Existing source-defined behavior: Core Managers and their responsibilities are defined by source Parts — **EXISTING** (Part 1 §1.7.1–1.7.2).
- Conflict: where source Parts define different Core Manager sets or responsibilities, the difference remains a documented `CONFLICT` (recorded without normalization).

Source authority: Part 1 §1.7.1–1.7.2 (Core Manager definitions).

---

## 3.8 Service

**Status:** EXISTING

An architectural service responsible for a defined workflow, capability, or operational role.

Service responsibilities remain source-defined.

Source authority: Part 5 (Engineering Services), Part 06 (Capability Facade Services).

---

## 3.9 Engineering Service

**Status:** EXISTING

A service associated with an engineering or software-development lifecycle capability as defined by the relevant source Parts.

Source authority: Part 05 §5.1–5.12 (Eight Engineering Services).

---

## 3.10 Capability Facade Service

**Status:** EXISTING

A thin service-level integration boundary that exposes or bridges underlying capabilities without taking ownership of the underlying kernel capability.

The facade MUST remain consistent with the source-defined facade architecture.

Source authority: Part 06 §6.1–6.7.

---

## 3.11 Plugin

**Status:** EXISTING

A dynamically loaded component that extends platform functionality through declared extension points.

- Existing source-defined behavior: extensions connect through documented Extension Points (Part 00 §0.5.2); per-domain registries (SkillRegistry, MemoryBackendRegistry, MCPTransportRegistry, etc.) with per-domain isolation; capability-based isolation (Part 06 §6.7, Part 07 §7) — **EXISTING**.
- Derived/proposed: "plugin registry" (standalone distribution mechanism) and "ExtensionRegistry API pattern" — **DERIVED/PROPOSED** (Part 14.3 is empty; not established in Parts 1–13).
- Retraction/CORRECTED: this glossary previously referenced "plugin registry" as an existing distribution mechanism — **RETRACTED/CORRECTED** (not a source conflict; disagreement was between this glossary's prior wording and authoritative sources; not established in Parts 1–13; per-domain registries are used instead).

Source authority: Part 00 §0.5.2 (Extension Points), Part 06 §6.7 (failure isolation), Part 07 §7 (capability isolation).

**CORRECTED**: This glossary previously referenced "plugin registry" as a distribution mechanism. That wording was incorrect. Parts 1–13 establish per-domain registries and extension points; a standalone universal "plugin registry" is not established.

---

## 3.12 Manager

**Status:** EXISTING

A named architectural unit responsible for a specific capability within the AI-OS core system.

The exact set of managers and their responsibilities are source-dependent. Source authority: Part 1 §1.7.1–1.7.2.

Part 14 does not merge or normalize manager definitions from different source Parts.

Where managers appear with different names or responsibilities across Parts, the distinction is preserved as `CONFLICT` or `UNSPECIFIED`.

---

## 3.13 Schema

**Status:** EXISTING

A machine-readable description of the structure, constraints, and semantics of data exchanged across an integration boundary.

- Existing source-defined behavior: AI-OS schemas use JSON Schema (Part 12 schemas.md §3); schemas are immutable once published — changes require a new version (Part 12 schemas.md §196); versioning enforced via Schema Registry compatibility rules (Part 12 schemas.md §142, §171–18) — **EXISTING**.
- Proposed: semantic annotations (units, privacy classification, PII markers) and invariant links as structured schema extensions — **PROPOSED** (not formally established in Parts 1–13).

Source authority: Part 12 `schemas.md` §3–142 (JSON Schema conformance, semver, immutability, compatibility rules).

---

## 3.14 Event

**Status:** EXISTING

An immutable, timestamped record of a fact that occurred in the system, emitted by a producer and consumed by zero or more consumers.

- Existing source-defined behavior: Event base contract with `eventId`, `eventType`, `eventVersion`, `payload`, `metadata`, `timestamp`, `correlationId`, `causationId` (Part 2 §2.2.1); per-correlation ordering guarantee (INV-EVT-004); at-least-once delivery default (Part 12 events.md §34); replayability — **EXISTING**.
- Conflict: Part 2 uses PascalCase field names (`eventId`, `eventType`, etc.) while Part 12 uses lowercase snake_case (`event_id`, `event_type`, etc.) — **CONFLICT** (recorded without normalization; each source Part's naming remains authoritative within its domain).
- Clarification: exactly-once is NOT a transport-layer guarantee (see Idempotency and Transactional Idempotency entries).

Source authority: Part 2 §2.2.1 (Event base contract), Part 12 `events.md` §34 (delivery guarantees), Part 12 `schemas.md` §46 (Schema Registry).

---

## 3.15 Interface

**Status:** EXISTING

A named, versioned set of events and schemas that a component exposes for consumption by other components.

- Existing source-defined behavior: interfaces expose events (via EventBus), schemas (Part 12 schemas.md), invariants (Part 12.12), SLIs (Part 12 §12.3), and compatibility rules (Part 12 §12.3) — **EXISTING**.
- Part 14 inference: interfaces are *discoverable* via capability registry patterns (Part 12 §12.3 step 1) — **DERIVED**.
- Unsupported claim: interfaces are "negotiable at connection time" — **RETRACTED** (Part 12 §12.3 negotiation is agent-level, not connection-time interface negotiation).
- Proposed: structured declaration of SLIs, preconditions/postconditions, and compatibility rules as part of a formal interface schema — **PROPOSED** (Part 14.3 is empty; not source-established).

**RETRACTED**: Claims that interfaces declare "operations (RPC)" are **incorrect** — AI-OS has no RPC mechanism (see RPC entry).

Source authority: Part 12 `12.3-Agent-Discovery-Capability-Management.md` §5, Part 00 §0.4 Principle 1, Part 1 §1.7.4 CC-IR-001, Part 2 §2.2 (EventBus).

---

## 3.16 Consumer

**Status:** EXISTING

A component that consumes events emitted by a producer, or a component that depends on another component's interface for contract compliance.

- Existing source-defined behavior: consumers declare *dependencies* in registration via `dependsOn` (Part 3 §3.4.4) — **EXISTING**.
- Proposed: consumers declare *requirements* (minimum contract version, required invariants, expected SLIs, fallback behavior) in a manifest — **PROPOSED** (not formalized in Parts 1–13).
- Proposed: consumers include a *human-facing agent* category — **PROPOSED** (Part 5 §5.12 is a service type, not a consumer role classification).

Source authority: Part 3 §3.4.4 (ServiceRegistration — `dependsOn`).

---

## 3.17 Producer

**Status:** EXISTING

A component that emits events or serves as the authoritative source for one or more interfaces.

- Existing source-defined behavior: at-least-once is the default delivery guarantee (Part 12 events.md §34; Part 12 12.7 §9.1); best-effort and exactly-once are configurable per message (Part 12 12.7 §9.1) — **EXISTING**.
- Clarification: exactly-once delivery is **not** a transport-layer guarantee. It requires idempotent producer AND consumer (application-layer semantics) — **EXISTING** fact from Part 12 events.md §34.
- Proposed: producers "declare guarantees in their manifest" — **PROPOSED** (Parts 1–13 define per-message guarantees but do not establish a manifest-driven declaration).
- Retracted: claims that producers are "service providers (exposing RPC operations)" and "RPC layer for sync operations" — **RETRACTED** (no RPC mechanism in AI-OS; see RPC entry).

Source authority: Part 12 `events.md` §34, Part 12 `12.7-Multi-Agent-Communication.md` §9.1, Part 00 §0.5.2 (model providers).

---

## 3.18 Provider

**Status:** EXISTING

A component that implements an interface and fulfills the obligations of its contract for consumers.

- Existing source-defined behavior: providers register instances with ServiceRegistry (Part 1 §1.7.1 C2; Part 3 §3.4) via the `ServiceRegistration` schema (Part 3 §3.4.4) — **EXISTING**.
- Retraction: previous reference to "topology manager" for provider registration is **CORRECTED** (Parts 1–13 use ServiceRegistry, not a "topology manager").
- Derived/proposed: `provider` as a formal role distinct from component type — **DERIVED** (Part 14.3, currently empty).
- Retraction: claims of "capacity" and "health endpoint" as registration fields are **RETRACTED** (ServiceRegistration includes `capabilities`, `critical`, `dependsOn`, `tags`, `metadata` but does not explicitly list capacity or health endpoint fields).

Source authority: Part 3 §3.4.4 (ServiceRegistration schema), Part 1 §1.7.1 C2 (ServiceRegistry).

---

## 3.19 ServiceRegistry

**Status:** EXISTING

A core component responsible for service registration, discovery, and dependency validation.

Source authority: Part 1 §1.7.1 C2, Part 3 §3.4.

---

## 3.20 StateManager

**Status:** EXISTING

A core component responsible for state management.

- Existing source-defined behavior: `StateManager` is referenced as a state-management concept in Parts 0–1 — **EXISTING** (referenced).
- Gap: the integration surface and canonical Core Manager mapping are not documented in source Parts — **GAP** (component referenced but integration contract not specified).

Source authority: Part 00 §0.2.1 (referenced), Part 01 (referenced).

---

# 4. Communication Terms

## 4.1 EventBus

**Status:** EXISTING

The event-mediated communication mechanism defined by the applicable source architecture.

EventBus usage MUST NOT be interpreted as requiring every AI-OS interaction to be asynchronous.

EventBus is the established event-mediated communication mechanism for internal component communication. Source-defined synchronous lifecycle, registration, discovery, accessor, or control interactions remain governed by their respective source contracts.

**RETRACTED**: The glossary previously claimed the platform provides an "RPC substrate." This is **incorrect** — Parts 1–13 establish EventBus as the sole communication substrate (Part 00 §0.4 Principle 1; Part 1 §1.7.4 CC-IR-001). There is no RPC mechanism in AI-OS.

Source authority: Part 1 §1.7.1 C1, Part 2 §2.2, Part 00 §0.4 Principle 1.

---

## 4.2 Event-First Communication

**Status:** EXISTING

The architectural principle that event-driven communication is preferred/required within the scope defined by the foundational architecture.

The exact scope and exceptions remain governed by the authoritative source.

It does NOT automatically imply that every boundary interaction uses events.

Source authority: Part 00 §0.4 Principle 1 (Event-First Communication).

---

## 4.3 Synchronous Integration

**Status:** EXISTING

An integration pattern where the producer blocks until the consumer completes processing and returns a result.

- Existing source-defined behavior: synchronous integration is permitted only for external system adapters (Part 11 §9.3) and user-facing request/response (Part 5 §5.12); synchronous patterns are prohibited for inter-component communication (Part 1 §1.7.4 CC-IR-001) — **EXISTING**.
- Retracted: claim that synchronous integration is "opt-in and requires explicit justification in ADRs" is **RETRACTED** (Parts 1–13 do not specifically mandate this).
- Unspecified: distributed transaction patterns requiring immediate consistency are **UNSPECIFIED** (Parts 1–13 do not define synchronous transaction patterns).

No context envelope reference appears here. The structured Context Envelope is classified as PROPOSED (§5.5) and is not used to describe synchronous integration.

Source authority: Part 1 §1.7.4 CC-IR-001, Part 11 §9.3, Part 5 §5.12, Part 12 `12.9-Reliability-Recovery-Performance.md`.

---

## 4.4 Asynchronous Integration

**Status:** EXISTING

An integration pattern where the producer and consumer operate independently in time; the producer emits events or messages without blocking on consumer processing.

AI-OS treats asynchronous integration as the default for cross-boundary communication. The Event Bus (Part 2 §2.2) provides ordering guarantees per correlation ID (Part 2 §2.2.1 INV-EVT-004). At-least-once delivery is the default (Part 12 events.md §34; Part 12 12.7 §9.1). Idempotency is achieved at the application layer via `event_id` deduplication within a bounded window (Part 12 events.md §34).

Source authority: Part 2 §2.2–2.4, §2.8, §2.9, Part 2 §2.2.1 (INV-EVT-004), Part 12 `events.md` §34, Part 12 `12.7-Multi-Agent-Communication.md` §9.1.

---

## 4.5 Correlation

**Status:** EXISTING

The ability to trace a logical operation across multiple integration boundaries using a shared identifier.

AI-OS mandates *correlation IDs* on all cross-boundary messages (Part 2 §2.2.1 INV-EVT-004). The platform generates a correlation ID at the originating boundary and propagates it through the Event Bus for all cross-boundary events.

- Retracted: claim that correlation IDs propagate through "RPC calls" is **RETRACTED** (AI-OS has no RPC; propagation is via EventBus only — Part 2 §2.2.1).
- Proposed: structured format `{tenant}:{session}:{request}:{sequence}` for correlation IDs — **PROPOSED** (Part 2 §2.2.1 defines `correlationId` as a string field but does not specify a structured format).

Correlation is distinct from *causation* (which tracks cause-effect); AI-OS tracks both (Part 00 §0.4 Principle 8). They enable distributed tracing (Part 12.12 RI-010), causal ordering in the EventBus, and idempotency key derivation (Part 12 events.md §34).

Source authority: Part 2 §2.2.1 (Event envelope, INV-EVT-004), Part 12 `12.12-Runtime-Invariants-Conformance.md` (RI-010), Part 00 §0.4 Principle 8.

---

## 4.6 Causation

**Status:** EXISTING

The tracking of cause-and-effect relationships between events — which event caused the current event to be emitted.

AI-OS tracks causation IDs alongside correlation IDs in the Event envelope (Part 2 §2.2.1). Causation links an event to its immediate parent event.

Source authority: Part 2 §2.2.1 (Event envelope structure), Part 00 §0.4 Principle 8 (correlation/causation IDs).

---

## 4.7 RPC

**Status:** UNSPECIFIED

Remote Procedure Call — a protocol that allows a program to execute procedures on a remote system as if calling a local function.

RPC is a generic industry term. In AI-OS source material it appears only in prohibited-pattern statements such as "no synchronous RPC." AI-OS does not establish an RPC mechanism.

- Existing source-defined behavior: "RPC" appears in source Parts only as a **prohibited** communication pattern (Part 1 §1.7.4 CC-IR-001 states "no synchronous RPC"; context.md line 243 repeats "no synchronous RPC"; integrations.md lists no RPC protocols in Parts 1–13).
- Retraction: claims that the platform provides an "RPC substrate" and that interfaces declare "operations (RPC)" are **RETRACTED** — AI-OS communication is exclusively event-first via EventBus (Part 00 §0.4 Principle 1, Part 1 §1.7.4 CC-IR-001).

Source authority: Part 1 §1.7.4 CC-IR-001 (no synchronous RPC), Part 00 §0.4 Principle 1 (Event-First Communication), context.md line 243, integrations.md.

---

## 4.8 Event Fabric

**Status:** UNSPECIFIED

A messaging infrastructure layer that provides event routing, transformation, and delivery semantics across distributed systems.

"Event Fabric" is a generic industry term for distributed event infrastructure. The term "Event Fabric" does **not appear** anywhere in Parts 1–13 or Part 14. AI-OS uses "Event Bus" as its formal term for the event routing substrate (Part 2 §2.2). Source Parts never establish "Event Fabric" as an AI-OS concept.

Source authority: NOT FOUND in source Parts. Part 2 §2.2 (EventBus — the established term), Part 1 §1.7.1 C1.

---

## 4.9 Event Producer

**Status:** EXISTING

A component or service that publishes an event.

Source authority: Part 2 §2.2.1 (Event base contract), Part 14.8.

---

## 4.10 Event Consumer

**Status:** EXISTING

A component or service that consumes an event.

Source authority: Part 2 §2.2.1 (Event base contract), Part 14.8.

---

## 4.11 Event Flow

**Status:** DERIVED

A communication path represented conceptually as:

```text
Producer → EventBus → Consumer
```

Source authority: Part 2 §2.2 (EventBus), Part 2 §2.2.1 (Event base contract).

---

# 5. Integration Terms

## 5.1 Adapter

**Status:** EXISTING

A component that translates between two incompatible interfaces, enabling a consumer to interact with a provider whose interface does not match the consumer's expectations.

- Existing source-defined behavior: Adapter Pattern appears in Part 11 §9.3 for instrumenting third-party libraries; adapters are referenced as thin integration bridges for external systems (context.md §6.5/§6.7) — **EXISTING**.
- Proposed: "adapters as first-class integration primitives," "deployed as plugins," "schema transformation," and "separating structural from semantic adaptation" — **PROPOSED** (Parts 1–13 do not establish these as formal architecture).

Adapters wrapping external tools follow sandboxing rules (Part 00 §0.5.2).

Source authority: Part 11 §9.3 (Adapter Pattern), Part 00 §0.5.2 (sandboxing), context.md §6.5/§6.7.

---

## 5.2 External Integration

**Status:** EXISTING

Integration between AI-OS components and systems outside the AI-OS trust boundary (third-party APIs, legacy systems, user devices).

- Existing source-defined behavior: circuit breakers (Part 12 §12.9 §8.1, RI-028), rate limiting (Part 12 §12.9 line 57), schema validation via Schema Registry (Part 12 schemas.md §46), audit logging (Part 12 events.md §46, Part 13 governance) — **EXISTING**.
- Derived: Part 14.5 and Part 14.10 are empty — External Integration concepts are **DERIVED** from Part 12 reliability and Part 13 governance architecture.

Source authority: Part 12 `12.9-Reliability-Recovery-Performance.md`, Part 12 `12.12-Runtime-Invariants-Conformance.md`, Part 12 `schemas.md` §46, Part 13 `governance-events.md`.

---

## 5.3 Internal Integration

**Status:** EXISTING

Integration between components within the AI-OS trust boundary, governed by platform contracts and policies.

- Existing source-defined behavior: automatic schema validation (Part 12 schemas.md §46; Part 12.12 RI-012), correlation propagation (Part 2 §2.2.1 INV-EVT-004), distributed tracing (Part 12.12 RI-010), contract conformance monitoring (Part 12.12 contract tests), and mutual TLS (Part 12.12 CM-015) — **EXISTING**.
- Retracted: claim of "zero-trust mutual TLS" is **RETRACTED** (Parts 1–13 establish mTLS per CM-015 but do not characterize it as zero-trust).
- Retracted: claim of "RPC substrate" is **RETRACTED** (EventBus is the established event-mediated communication mechanism for internal component communication; see RPC entry).

Internal integration contracts are evolved collaboratively via ADRs (Part 00 §0.5.3); breaking changes require coordinated migration windows (Part 12 §12.3 deprecation workflows).

Source authority: Part 2 §2.2.1, Part 12 `12.9-Reliability-Recovery-Performance.md`, Part 12 `12.12-Runtime-Invariants-Conformance.md`, Part 00 §0.5.3, Part 1 §1.7.4 CC-IR-001.

---

## 5.4 Context

**Status:** EXISTING

The implicit or explicit state that accompanies an integration request.

- Existing source-defined behavior: context is propagated across integration boundaries via `correlationId` and `causationId` fields embedded in every Event envelope (Part 2 §2.2.1), present on all cross-boundary messages per INV-EVT-004 — **EXISTING**.
- Proposed: structured "Context Envelope" as a single envelope object wrapping every cross-boundary call with additional fields (tenant identity, authentication principal, feature flags, locale, trace flags, deadlines) — **PROPOSED** (not established in Parts 1–13 as a structured envelope).
- Conflict: "context envelope" in Part 13 §13.2 refers to a governance operating context for governance components (G-00..G-15), which is distinct from cross-boundary call context — **CONFLICT** (recorded without normalization).

Source authority: Part 2 §2.2.1 (Event envelope structure), Part 00 §0.4 Principle 8, Part 13 §13.2 (governance context envelope — different concept).

---

## 5.5 Context Envelope

**Status:** PROPOSED

A structured wrapper that carries cross-cutting context (tenant identity, authentication principal, correlation/causation IDs, feature flags, locale, trace flags, deadlines) across integration boundaries.

The structured Context Envelope (as a single envelope object wrapping every cross-boundary call with the specific fields listed above) is **not established in Parts 1–13**. While Part 14.3 and Part 14.8 reference context propagation (tenant identity, deadlines, feature flags), these are not structured as a single named envelope object in source documents.

**CONFLICT**: "Context envelope" in Part 13 §13.2 refers to a governance context (opaque to G-00), which is a different concept from cross-boundary call context. The term is recorded without normalization.

This entry is marked PROPOSED pending source-document establishment. It is useful as an integration concept but is not an existing AI-OS platform guarantee.

Source authority: NOT FOUND in Parts 1–13 as a structured envelope. Part 13 §13.2 (governance context envelope — different concept), Part 2 §2.2.1 (Event envelope — existing propagation mechanism).

---

## 5.6 Boundary

**Status:** DERIVED

A delineation between two integration domains where contracts are enforced, translations occur, and invariants are verified.

- Existing source-referenced concepts: Process Boundary (context.md §5), Trust Boundary (Part 13 §13.2), Version Boundary (Part 12 schemas.md §46) — **EXISTING** references.
- Proposed: the structured three-type boundary classification (Process/Trust/Version) as a unified architectural classification — **PROPOSED** (source Parts reference individual boundary types but do not formally establish the unified classification).

Source authority: Part 14 context.md §5 (process boundary), Part 13 §13.2 (trust boundary), Part 12 schemas.md §46 (version boundary).

---

## 5.7 Control Plane

**Status:** DERIVED

The set of platform services that manage, coordinate, and govern the data plane — including service discovery, configuration, policy enforcement, and topology management.

In AI-OS (Part 14.2), the control plane is *itself a set of components* with declared interfaces, not a privileged monolith. The control plane communicates with the data plane via the same EventBus used by application components.

- Existing source-defined: Schema Registry is established (Part 12 schemas.md §46); policy evaluation occurs within SecurityManager (Part 1 M8, Part 4 §4.7) — **EXISTING**.
- Proposed: Control Plane as a unified architectural subsystem — **PROPOSED** (not a named subsystem in Parts 0–13). Also proposed: Contract Broker, Topology Manager, and Deployment Orchestrator as control-plane components — **PROPOSED** (not established in Parts 1–13).
- Derived: "data-plane components are unaware of the control plane" — **DERIVED** (Part 14.2 analytical concept, not source-established).

Source authority: Part 12 `schemas.md` §46 (Schema Registry), Part 1 §1.8.1 M8 (SecurityManager), Part 4 §4.7 (policy evaluation), Part 12.12 (RI-014).

---

## 5.8 Data Plane

**Status:** DERIVED

The path through which application data flows between components — the runtime execution of business logic and data transformation.

In AI-OS (Part 14.2), the data plane consists of *component-to-component communication* via declared interfaces.

- Retracted: claim of an "RPC substrate" is **RETRACTED** — source Parts establish EventBus as the sole communication substrate (Part 00 §0.4 Principle 1; Part 1 §1.7.4 CC-IR-001); communication flows exclusively through EventBus (Part 2) or external system adapters (Part 11 §9.3).
- Derived: "data plane components are unaware of the control plane" — **DERIVED** (Part 14.2 analytical concept; not source-established as a formal architectural principle).

Source authority: Part 00 §0.4 Principle 1, Part 1 §1.7.4 CC-IR-001, context.md line 243, Part 2 §2.2 (EventBus), Part 11 §9.3.

---

## 5.9 Dependency

**Status:** EXISTING

A relationship where one component requires another component's interface to fulfill its obligations.

- Existing source-defined behavior: `dependsOn` graph MUST be acyclic (Part 3 SR-REG-003); version constraints in `ComponentIdentity.version` (Part 2 §2.2.2, Part 00 §0.4 Principle 11); capability health cascades (Part 12 §12.3) — **EXISTING**.
- Proposed: *criticality levels* (required, optional, fallback) and *dependency closure analysis* for detecting version conflicts and single points of failure — **PROPOSED** (not formally structured in Parts 1–13).

Source authority: Part 3 §3.4.4 (ServiceRegistration), Part 3 SR-REG-003 (acyclic dependency graph), Part 2 §2.2.2 (ComponentIdentity.version), Part 12 §12.3 (capability health cascades).

---

# 6. Operational Terms

## 6.1 Idempotency

**Status:** EXISTING

The property that applying an operation multiple times produces the same result as applying it once.

- Existing source-defined behavior: at-least-once is the default delivery guarantee (Part 12 events.md §34; Part 12 12.7 §9.1); idempotency is achieved at the application layer via `eventId` deduplication within a bounded window (Part 12 events.md §34) — **EXISTING**.
- Clarification: exactly-once delivery is **not** a transport-level guarantee (Part 12 events.md §34). Exactly-once requires idempotent producer AND consumer (application-layer semantics). This applies only to *delivery guarantee* and *processing guarantee*, not transport guarantee.
- Proposed: classification of idempotency levels (Natural, Keyed, Transactional), "platform-required idempotency declarations in contracts," and "platform coordinates distributed transactions" — **PROPOSED**.

Source authority: Part 12 `events.md` §34, Part 12 `12.7-Multi-Agent-Communication.md` §9.1, Part 12 `12.12-Runtime-Invariants-Conformance.md` (CM-004).

---

## 6.2 Transactional Idempotency

**Status:** PROPOSED

A distributed idempotency guarantee where the platform coordinates across all participants in a transaction to ensure exactly-once semantics.

- Existing fact: exactly-once delivery is **not** a transport-layer guarantee (Part 12 events.md §34) — **EXISTING**.
- Proposed concept: "transactional idempotency" as a platform-level mechanism coordinating distributed transactions — **PROPOSED** (not established in Parts 1–13; useful for application-layer design only).

Source authority: Part 12 `events.md` §34, Part 12 `12.7-Multi-Agent-Communication.md` §9.1.

---

## 6.3 Invariant

**Status:** EXISTING

A condition that must hold true across all valid states of a system or component.

- Existing source-defined behavior: invariants are executable assertions organized by domain (Collaboration Invariants CI-, Communication Invariants CM-, Workflow Invariants WI-, Security Invariants SeI-, Resource Invariants RI-, Knowledge Invariants KI-) and enforced through schema validation, policy checks, runtime assertions, and circuit breakers — **EXISTING**.
- Proposed: the "three categories" classification (Structural, Temporal, Semantic) — **PROPOSED** (Parts 1–13 organize invariants by architectural domain, not by these three categories).

Invariants are checked in CI, staging, and continuously in production (Part 12.12 §16). Circuit-breaker recovery is defined by RI-028. This glossary does not infer that every invariant violation automatically triggers circuit-breaker activation; rollback applies where defined by WI-011 (workflow state recovery).

Source authority: Part 12.12-Runtime-Invariants-Conformance.md, Part 00 §0.4 (principles).

---

## 6.4 Circuit Breaker

**Status:** EXISTING

A reliability pattern that prevents cascading failures by temporarily stopping requests to a failing service.

Circuit breakers exist in Part 12 (12.9 §8.1 three-state Closed/Open/Half-Open; Part 12.12 RI-028 Circuit Breaker Recovery).

**RETRACTED**: Claims that circuit breakers are "automatically triggered by conformance violations" are **PROPOSED** — Parts 1–13 do not establish automatic circuit-breaking triggered by conformance violations. Circuit breakers are triggered by operational failures, not conformance checks.

Source authority: Part 12 `12.9-Reliability-Recovery-Performance.md` §8, Part 12.12 (RI-028).

---

## 6.5 Rollback

**Status:** EXISTING

A recovery mechanism that reverts a system to a previously known-good state after a failure or detected error.

Rollback exists in Part 12 for workflow state recovery (WI-011). It is **NOT** automatically triggered by conformance violations.

**RETRACTED**: Claims that "non-conformance triggers automatic rollback" are **PROPOSED** — Parts 1–13 do not establish automatic rollback triggered by conformance violations. Rollback is an operational recovery mechanism, not an automated conformance response.

Source authority: Part 12.12 (WI-011 Compensating Actions).

---

## 6.6 Termination

**Status:** UNSPECIFIED

In distributed systems, a termination strategy determines when and how a process or operation reaches a final state.

"Termination" as a distinct architectural concept **does not appear** in Parts 1–13. This entry is kept for reference only; no architectural meaning is claimed. Related operational concepts in AI-OS (workflow completion, shutdown sequences) are governed by Part 2 lifecycle patterns and Part 12.12 invariant verification, not by a "termination" framework.

Source authority: NOT FOUND in Parts 1–13.

---

## 6.7 Conformance

**Status:** EXISTING

The property that an implementation satisfies its declared contract, schema, and invariants.

- Existing source-defined behavior: four conformance levels (L1 Structural, L2 Contract, L3 Behavioral, L4 Architectural) per Part 00 §0.5.1; verification via static analysis, runtime assertions, policy checks, circuit breakers, invariant enforcement — **EXISTING**.
- Retracted: claim that "non-conformance triggers automatic circuit-breaking and rollback" — **RETRACTED** (Parts 1–13 establish verification but do not mandate automatic circuit-breaking/rollback as a conformance violation response).

Source authority: Part 00 §0.5.1 (conformance model), Part 12.12 (RI-028, WI-011), Part 12 §12.9.

---

## 6.8 Versioning

**Status:** EXISTING

The practice of assigning unique identifiers to successive releases of components, interfaces, schemas, and contracts to manage evolution and compatibility.

- Existing source-defined behavior: Component Version (semver, `ComponentIdentity.version`, Part 2 §2.2.2), Schema Version (`eventVersion` in Event Base Contract, Part 2 §2.2.1), Interface Version (Part 00 §0.4 Principle 11, Part 12 components.md §11.6) — **EXISTING**.
- Proposed: "three independent versioning axes" as a platform-enforced model — **PROPOSED** (not formally established in Parts 1–13; the axes are **DERIVED** from combining source Parts).
- Traceability note: This glossary previously referenced "Part 14.11" for versioning axes. Part 14.11 is empty; axes are derived from Parts 0, 2, and 12 — a **TRACEABILITY ISSUE**, not an architectural conflict.

Source authority: Part 00 §0.4 Principle 11, Part 2 §2.2.1, Part 2 §2.2.2, Part 12 components.md §11.6.

---

## 6.9 Compatibility

**Status:** EXISTING

The ability of two versions of a component, interface, or schema to work together without modification.

- Existing source-defined behavior: conformance levels (Part 00 §0.5.1) and backward/forward schema compatibility (Part 2 §2.10; Part 12 schemas.md §18–19, §26) — **EXISTING**.
- Proposed: "four compatibility *modes*" (Structural, Behavioral, Temporal, Semantic) as a platform-level classification — **PROPOSED** (Parts 1–13 use conformance levels and backward/forward schema compatibility, not "modes").

Compatibility is *asymmetric* in schema evolution (producers backward-compatible with older consumers per Part 12 schemas.md §26).

Source authority: Part 00 §0.5.1 (conformance model), Part 2 §2.10, Part 12.12 §14.2 (conformance levels), Part 12 schemas.md §18–19, §26, Part 12.12 (RI-013).

---

## 6.10 ADR (Architecture Decision Record)

**Status:** EXISTING

A documented decision addressing a significant architectural concern.

- Existing source-defined behavior: ADRs document Decision, Rationale, Impact, Mitigation, Expiry (Part 00 §0.5.3); ADRs are "part of the conformance evidence" and reviewed by the Architecture Review Board — **EXISTING**.
- Proposed: ADRs are machine-readable (Markdown with YAML frontmatter), declare `affected_components`/`affected_interfaces`/`boundary_crossings`/`invariants_impacted`/`migration_strategy`, are validated by the platform, and are immutable — **PROPOSED** (Part 00 §0.5.3 only establishes 5 content fields; Parts 1–13 do not establish machine-readable formats or platform validation).

Source authority: Part 00 §0.5.3 (authoritative ADR format), adrs.md.

---

## 6.11 Contract

**Status:** EXISTING

A machine-enforceable specification of the obligations and guarantees between a provider and its consumers.

- Existing source-defined behavior: contracts reference schemas (Part 12 schemas.md) and are versioned via semantic versioning (Part 00 §0.4 Principle 11); Schema Registry is established (Part 12 schemas.md §46) — **EXISTING**.
- Proposed: contracts written in "OpenAPI 3.1 extended with preconditions/postconditions, idempotency declarations, and invariant references" with platform-level breach events — **PROPOSED** (not established in Parts 1–13).

Source authority: Part 12 `schemas.md` §46 (Schema Registry), §142 (semantic versioning), Part 00 §0.4 Principle 11, Part 12.12 (contract tests, invariants).

---

## 6.12 Schema Registry

**Status:** EXISTING

A centralized, versioned repository for all formal schemas.

Source authority: Part 12 `schemas.md` §46.

---

## 6.13 Distributed Tracing

**Status:** EXISTING

The collection of telemetry data about request flow through distributed systems.

Enabled by correlation/causation ID propagation (Part 12.12 RI-010).

Source authority: Part 12.12 (RI-010 Trace Propagation), Part 2 §2.2.1 (Event envelope).

---

## 6.14 Observability

**Status:** EXISTING

The ability to understand system behavior from externally observable outputs (logs, metrics, traces).

Part 00 §0.4 Principle 12 establishes observability as built-in via StructuredLogger and events. Observability events flow into the EventBus as data-plane events.

Source authority: Part 00 §0.4 Principle 12, Part 14.8 (observability integration — DERIVED).

---

# 7. Cross-Reference Index

| Term | Section | Primary Source | Status |
|------|---------|---------------|--------|
| Adapter | 5.1 | Part 11 §9.3 | EXISTING |
| ADR | 6.10 | Part 00 §0.5.3 | EXISTING |
| Asynchronous Integration | 4.4 | Part 2 §2.2 | EXISTING |
| Boundary | 5.6 | Part 14 context.md §5 | DERIVED |
| Capability Facade Service | 3.10 | Part 06 | EXISTING |
| Circuit Breaker | 6.4 | Part 12 12.9, 12.12 RI-028 | EXISTING |
| Component | 3.5 | Part 1 §1.7.1 | EXISTING |
| Compatibility | 6.9 | Part 00 §0.5.1, Part 12 | EXISTING |
| Compatibility (Four Modes) | — | 14.11 | PROPOSED |
| Component Version | 6.8 | Part 2 §2.2.2 | EXISTING |
| Conformance | 6.7 | Part 00 §0.5.1, Part 12.12 | EXISTING |
| Context | 5.4 | Part 2 §2.2.1, Part 13 §13.2 | EXISTING |
| Context Envelope | 5.5 | — | PROPOSED |
| Control Plane | 5.7 | Part 12 schemas.md §46 | DERIVED |
| Core Component | 3.6 | Part 1 §1.7.1 | EXISTING |
| Core Manager | 3.7 | Part 1 §1.7.1–1.7.2 | EXISTING |
| Correlation | 4.5 | Part 2 §2.2.1 | EXISTING |
| Causation | 4.6 | Part 2 §2.2.1 | EXISTING |
| Consumer | 3.16 | Part 3 §3.4.4 | EXISTING |
| Contract | 6.11 | Part 12 schemas.md §46 | EXISTING |
| Data Plane | 5.8 | 14.2 | DERIVED |
| Dependency | 5.9 | Part 3 §3.4.4 | EXISTING |
| Event | 3.14 | Part 2 §2.2.1 | EXISTING |
| Event Fabric | 4.8 | — | UNSPECIFIED |
| Event Consumer | 4.10 | Part 2 §2.2.1 | EXISTING |
| Event Flow | 4.11 | Part 2 §2.2 | DERIVED |
| Event Producer | 4.9 | Part 2 §2.2.1 | EXISTING |
| EventBus | 4.1 | Part 1 §1.7.1 C1, Part 2 §2.2 | EXISTING |
| Event-First Communication | 4.2 | Part 00 §0.4 P1 | EXISTING |
| Engineering Service | 3.9 | Part 05 | EXISTING |
| Idempotency | 6.1 | Part 12 events.md §34 | EXISTING |
| Interface | 3.15 | Part 12 §12.3 | EXISTING |
| Internal Integration | 5.3 | Part 2 §2.2, Part 12.12 | EXISTING |
| Invariant | 6.3 | Part 12.12 | EXISTING |
| Manager | 3.12 | Part 1 §1.7.1–1.7.2 | EXISTING |
| Plugin | 3.11 | Part 00 §0.5.2 | EXISTING |
| Producer | 3.17 | Part 12 events.md §34 | EXISTING |
| Provider | 3.18 | Part 3 §3.4.4 | EXISTING |
| RPC | 4.7 | Part 1 §1.7.4 CC-IR-001 | UNSPECIFIED |
| Rollback | 6.5 | Part 12.12 WI-011 | EXISTING |
| Schema | 3.13 | Part 12 schemas.md §46 | EXISTING |
| Schema Registry | 6.12 | Part 12 schemas.md §46 | EXISTING |
| Service | 3.8 | Part 05, Part 06 | EXISTING |
| ServiceRegistry | 3.19 | Part 1 §1.7.1 C2, Part 3 §3.4 | EXISTING |
| StateManager | 3.20 | Part 00 §0.2.1, Part 01 | EXISTING |
| Synchronous Integration | 4.3 | Part 1 §1.7.4 | EXISTING |
| Termination | 6.6 | — | UNSPECIFIED |
| Transactional Idempotency | 6.2 | Part 12 events.md §34 | PROPOSED |
| Versioning | 6.8 | Part 00 §0.4 P11, Part 2 §2.2 | EXISTING |
| Observability | 6.14 | Part 00 §0.4 P12 | EXISTING |
| Distributed Tracing | 6.13 | Part 12.12 RI-010 | EXISTING |

---

## Conflict Log

Genuine conflicts require two authoritative source definitions that materially disagree. Entries below are classified accordingly:

| Conflict | Source A | Source B | Classification |
|----------|----------|----------|----------------|
| Event field naming | Part 2 (PascalCase `eventId`, `correlationId`) | Part 12 (snake_case `event_id`, `partition_key`) | CONFLICT — genuine (material field-name disagreement) |
| Core Manager set | Part 1 §1.7.1 | Part 1 §1.7.2 | CONFLICT — genuine (different manager definitions within same Part series) |
| Context Envelope | Part 13 §13.2 (governance operating context) | Cross-boundary call context propagation (Part 2 §2.2.1) | CONFLICT — genuine (same term, materially different concepts) |
| Component definition | Part 1 §1.7.1 | Part 09 §3.1 | CONFLICT — genuine (domain-specific definitions) |
| Versioning (three axes) vs Part 14.11 | Versioning axes derived from Parts 0, 2, 12 | Part 14.11 (empty) | TRACEABILITY — not a conflict (derivation vs empty section) |
| Plugin registry | Per-domain registries (Parts 0–13) | Part 14.3 ExtensionRegistry API | TRACEABILITY — not a conflict (per-domain vs derived pattern) |
| Topology Manager | ServiceRegistry (Part 3 §3.4.4) | Previous glossary (incorrect) | RETRACTED — not a conflict (error corrected) |
| Synchronous integration | External adapters (Part 11 §9.3) | HumanInteractionService (Part 5 §5.12) | TRACEABILITY — not a conflict (both source-defined, complementary) |

---

## Retraction Log

| Term | Retracted Claim | Status | Source Authority for Correction |
|------|-----------------|--------|-------------------------------|
| Data Plane | "Platform provides RPC substrate" | RETRACTED | Part 1 §1.7.4 CC-IR-001, Part 00 §0.4 P1, context.md line 243 |
| Correlation | "Propagates through RPC calls" | RETRACTED | Part 2 §2.2.1 (EventBus propagation only), Part 1 §1.7.4 CC-IR-001 |
| Interface | "Declares operations (RPC)" | RETRACTED | Part 1 §1.7.4 CC-IR-001, Part 00 §0.4 P1 |
| Producer | "Service provider exposing RPC operations" | RETRACTED | Part 1 §1.7.4 CC-IR-001 |
| Idempotency | "RPC layer for sync operations" | RETRACTED | Part 1 §1.7.4 CC-IR-001, see RPC entry |
| Internal Integration | "Zero-trust mutual TLS" | CORRECTED | Part 12.12 CM-015 (mTLS, not zero-trust) |
| Interface | "Negotiable at connection time" | CORRECTED | Part 12 §12.3 §125 (agent-level, not connection-time) |
| Synchronous Integration | "Permitted for distributed transactions" | UNSPECIFIED | Parts 1–13 do not define this pattern |
| Component | "Machine-readable component manifest" | DERIVED | Part 09 §6.1 (ConfigManifest), not component manifest |
| Provider | "Capacity and health endpoint fields" | DERIVED | Part 3 §3.4.4 (ServiceRegistration schema fields) |

---

## Notes for AI Agents

1. **Source Authority**: Use the exact terms from source Parts. This glossary records how Part 14 uses those terms in an integration context; it does not define authoritative terminology. When a source Part defines a term, that definition is authoritative within that Part's domain.

2. **Context Awareness**: When a term has an "AI-OS-Specific Meaning" section, that meaning applies in Part 14 integration documents to the extent it is supported by the cited source Part. When in conflict, the authoritative source Part takes precedence over this glossary's framing.

3. **Cross-References**: The `Section` and `Source Document(s)` fields form a traversable knowledge graph. Follow them to maintain consistency.

4. **Retractions**: **RETRACTED** claims document historical corrections for traceability. They MUST NOT be interpreted as current architecture or terminology authority.

5. **Evolution**: New terms or modified definitions should be proposed via an ADR. Part 14 does not establish new terminology by definition — it only documents how source-part terms apply in integration contexts. New terms must cite their source authority or be classified as PROPOSED.

---

*Version 1.1.0 — Complete rewrite with structured sections, conflict log, and retraction log for full transparency.*