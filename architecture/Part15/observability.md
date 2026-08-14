# AI-OS Part 15 — Observability Architecture

## 1. Document Identity

`observability.md` is the **AI-OS Part 15 Observability Architecture** specification.

It defines architectural observability requirements and telemetry semantics. It does **not** prescribe a specific observability product or implementation technology unless authoritative architecture explicitly requires one.

This document does **NOT** replace:

- runtime architecture (`runtime-map.md` — currently EMPTY)
- communication/event architecture (`Part 12 events.md`)
- deployment architecture (`deployment.md`)
- security architecture (`Part 14 §8.2`, `Part 4 §4.7`)
- testing architecture (`testing.md` — currently EMPTY)

## 2. Purpose

Observability is a built-in architectural requirement established by **Part 00 §0.4 Principle 12**:

> **Part 00 §0.4 Principle 12:** "Every component MUST emit structured logs (JSON, correlation IDs) and Events for state transitions. StructuredLogger is the single logging abstraction. ObservabilityManager receives metrics from all managers."

### 2.1 Why Observability is Required

Observability in AI-OS serves these essential purposes:

- **Runtime Operation Support:** Provides visibility into component state, execution flow, and system health for operational teams.
- **Debugging Capability:** Enables tracing of issues through correlation IDs and causation chains across event boundaries.
- **Security and Governance:** Supports audit requirements, security monitoring, and compliance verification.
- **Failure Detection:** Makes component failures and degradations observable via Events (observability of a failure is distinct from recovery — see §23).
- **Performance Management:** Captures metrics for capacity planning and optimization.

### 2.2 What This Document Establishes

This document establishes the **AI-OS observability architecture and the implementation-facing observability requirements** for AI-OS. It defines:

- what must be observable (signals, identifiers, relationships)
- required observability concepts and their source-backed semantics
- security and privacy restrictions on observability
- verification expectations for conformance

It deliberately distinguishes **Observability Architecture** (what must be observable, required identifiers, required relationships, security restrictions) from **Observability Implementation Technology** (the specific logging library, metrics backend, tracing system, or storage chosen at implementation time). This document defines the former. It MUST NOT select an implementation technology — no monitoring platform (Prometheus, Grafana, OpenTelemetry, Jaeger, Zipkin, ELK, Splunk, Datadog, CloudWatch, Azure Monitor, GCP Cloud Monitoring, Loki, New Relic, etc.) is required by AI-OS unless Parts 0–14 explicitly mandate it, which they do not.

### 2.3 Support for Developers and AI Coding Agents

This architecture guides developers and AI coding agents in:

- Implementing required structured logging with correlation ID propagation
- Publishing state transitions as Events following Part 00 §0.4 Principle 12 requirements
- Supporting ObservabilityManager metrics collection
- Respecting security and privacy restrictions from Part 13 / Part 14
- Implementing observability without inventing new monitoring platforms
- Ensuring observability does not alter system semantics

### 2.4 Scope

Observability scope covers:

- **Runtime components:** All Core Components and Core Managers (Part 01 §1.8.1)
- **Agents and councils:** Part 12 multi-agent collaboration domain (P12-ADR-008)
- **Workflows:** WorkflowManager and TaskUnit execution (Part 12)
- **Memory and knowledge:** MemoryManager and ContextManager operations (Part 13)
- **Communication and events:** EventBus publication/consumption (Part 00 §0.4 Principle 1)
- **Plugins and integrations:** Extension point implementations (Part 00 §0.5.2)
- **Security and governance:** P13-ADR-006 (Draft) governance auditability (Part 13)
- **Configuration:** Four-layer merge via ConfigurationManager (Part 00 §0.4 Principle 10)
- **Deployment:** HermesKernel initialization and lifecycle (Part 01 §1.9.1)
- **External dependencies:** Obsidian, Graphify, LLM providers, MCP servers (Part 14 §7)

Only areas actually supported by the architecture are included, no invented observability requirements.

## 3. Authority Boundary

### 3.1 Observability Authority Model

Part 15 observability does not create requirements; it derives them. The authority chain is:

```
Authoritative Architecture (Parts 0–14)
        ↓
Observability Requirements (this document)
        ↓
Implementation Contracts (implementation-contracts.md)
        ↓
Implementation
        ↓
Observability Verification (testing.md — currently EMPTY)
```

### 3.2 Authority Rules

1. **Parts 0–14 remain authoritative.** observability.md does not override them.
2. **Translation only.** observability.md translates supported requirements into implementation-facing observability constraints.
3. **No new architecture.** observability.md MUST NOT create new architecture.
4. **No invented platforms.** observability.md MUST NOT invent telemetry platforms.
5. **No silent conflict resolution.** Where authoritative sources conflict (e.g. CONFLICT-03 on SecurityManager authorization scope), the conflict is **preserved**, not silently resolved.
6. **Unspecified remains unspecified.** Unspecified observability implementation details remain UNSPECIFIED.

- `observability.md` does **not** override Parts 0–14. Where a source Part is silent, the requirement is **UNSPECIFIED**, not invented.
- `implementation-contracts.md` does **not** gain authority merely by listing an observability requirement. A contract is only as valid as its architectural source.
- Where authoritative sources conflict, the conflict is **preserved**, not silently resolved.

## 4. Observability Definition

### 4.1 Observability

Observability is the architectural capability to infer system state and behavior from externally observable telemetry (Logs, Events, Metrics, Traces, Audit Records). It is a property of the system's design, not of any particular tool.

### 4.2 Distinct Concepts — MUST NOT be Conflated

| Concept | Definition | In AI-OS |
|---------|------------|----------|
| **Observability** | Capability to infer internal state from external telemetry | Architectural property (this document) |
| **Monitoring** | Ongoing checking of known conditions against thresholds | Not separately defined; folded into Events/Metrics semantics |
| **Logging** | Emission of structured log records via StructuredLogger | Part 00 §0.4 Principle 12 |
| **Metrics** | Aggregated numeric measurements owned by ObservabilityManager (M9) | Part 01 §1.8.1 M9 (responsibility only; see §11) |
| **Tracing** | Span hierarchy reconstruction via event-envelope `trace` object | Part 12 events.md §4 (concepts only; see §10) |
| **Auditing** | Tamper-evident governance audit trail (WORM) | P13-ADR-006 (Draft); §13 |
| **Debugging** | Use of telemetry to diagnose a fault | Enabled by correlation/causation, not a separate signal |

These are not identical concepts. Observability is the umbrella; logging, metrics, tracing, events, and auditing are distinct signals/activities within it. Audit records are explicitly **separate** from operational logs (see §13).

## 5. Observability Signal Model

### 5.1 Established Signal Types

| Signal | Purpose | Architectural Requirement | Source | Status |
|--------|---------|---------------------------|--------|--------|
| **Logs** | Component-level debugging via StructuredLogger | MUST be structured JSON with `correlation_id` | Part 00 §0.4 Principle 12 | EXISTING |
| **Events** | State transitions / failures over EventBus | MUST carry `correlation_id`/`causation_id`; immutable | Part 00 §0.4 Principles 1, 8, 9 | EXISTING |
| **Metrics** | Aggregated system measurements | ObservabilityManager (M9) receives metrics | Part 01 §1.8.1 M9 | RESPONSIBILITY DEFINED; schema/backend UNSPECIFIED |
| **Traces** | Distributed-trace span hierarchy via event envelope `trace` object | `trace_id`/`span_id`/`parent_span_id` (W3C Trace Context) | Part 12 events.md §4; 12.7 §1.2 | CONCEPTS DEFINED; backend UNSPECIFIED |
| **Audit Records** | Governance, tamper-evident, WORM trail | Per P13-ADR-006 (Draft) | Part 13 §11; P13-ADR-006 | PROPOSED (Draft) |
| **Health Signals** | Liveness/readiness probes | Defined for collaboration domain | Part 12 §12.9, §12.12 (RI-005/RI-006) | EXISTING (collaboration domain); endpoint technology UNSPECIFIED |

### 5.2 Distinctness Rule

These signal types are distinct and MUST NOT be merged.

- **Event-Centric (for Events):** State transitions and failures are communicated as Events over EventBus (Principle 1). EventBus governs **event** communication. It does NOT govern every telemetry channel: structured logs are emitted via StructuredLogger, metrics are aggregated by ObservabilityManager, audit records are written to the governance audit trail, and health is reported via probes. Do not imply that all logs, all metrics, all traces, or all audit records must physically pass through EventBus.
- **Correlation-Centric (for Events):** Events carry `correlation_id` and `causation_id` (Principle 8). Logs reference a `correlation_id`; metrics/traces/audit records are correlated through the same identifiers where the source defines it, but they are not each required to embed every identifier.
- **Single Source:** StructuredLogger is the sole logging abstraction; ObservabilityManager is the single metrics aggregation point.

(Failure events and component state transitions are *Events*, not a separate "Diagnostics" signal type.)

## 6. Logging Architecture

### 6.1 Logging Responsibilities

**Status:** DERIVED from Part 00 §0.4 Principle 12

- **StructuredLogger:** The single logging abstraction for all components
- **ObservabilityManager:** Consumes logs and metrics for aggregation
- **Core Components/Managers:** Emit logs for state transitions

### 6.2 Log Categories

Based on existing AI-OS categories:

- **Lifecycle Events:** Component initialization, shutdown, state changes
- **Failure Events:** TRANSIENT, DEGRADED, CRITICAL, FATAL failures (Part 01 §1.12.1)
- **Security Events:** Authorization decisions, authentication attempts (Part 14 §5.2)
- **Performance Events:** Metrics collection, health monitoring
- **Operational Events:** Configuration changes, deployment events

### 6.3 Log Severity

**Status:** UNSPECIFIED in Parts 0–13

Severity levels are not defined by the AI-OS architecture. Implementers MUST follow the kernel failure classification (Part 01 §1.12.1):

- **TRANSIENT:** Retry with exponential backoff (max 3)
- **DEGRADED:** ComponentDegraded event; continue operation
- **CRITICAL:** ComponentFailed event; isolate; restart (max 2)
- **FATAL:** Emergency shutdown

This classification governs *failure handling semantics*, not a mandated log-severity field on every StructuredLogger call.

### 6.4 Structured Logging

**Status:** EXISTING (Part 00 §0.4 Principle 12)

- **Format:** JSON; MUST include `correlation_id` (Part 00 §0.4 Principle 12: "structured logs (JSON, correlation IDs)").
- **Required Fields — MUST:** `correlation_id` (per Principle 12).
- **Required Fields — Source-Defined Elsewhere:** Event envelope fields such as `event_type`, `produced_at` (timestamp), `event_id`, `causation_id`, `partition_key` are defined by the Part 12 event schema (events.md §4) for **Events**, not as mandated log-line fields for every StructuredLogger call. Observability MUST NOT upgrade those into universal structured-log MUST fields unless the implementation contract does so.
- **Producer:** StructuredLogger abstraction (Part 00 §0.4 Principle 12) — the single logging abstraction.
- **Not Invented:** Part 00 §0.4 Principle 12 does NOT mandate fields such as `component`, `hostname`, `process_id`, `thread_id`, `trace_id`, `user_id`, or `request_id` on every log line. These MUST NOT be presented as AI-OS observability MUST requirements.

### 6.5 Error / Failure Logging

**Status:** EXISTING

Failure events MUST be communicated via Events:

- Part 01 §1.12.4 defines ComponentDegraded, ComponentFailed, CoreManagerFailed, KernelFatalError
- Part 12 defines workflow.lifecycle.failed, agent.lifecycle.error

(See §23 for the full Failure Observability matrix.)

### 6.6 Security Logging

**Status:** EXISTING (Part 12 events.md §4/§5/§20; P13-ADR-005 Draft; INT-GOV-EVENT-001 referenced in Part 14 §14.11)

- **Governance Events — signed:** Part 12 events carry `security.signature` over the canonicalized payload (events.md §4); lifecycle events such as `agent.lifecycle.registered` require a signature (events.md §5).
- **Governance Events — classified:** Every event MUST declare `metadata.classification` ∈ {`internal`, `confidential`, `secret`} (events.md §20); unclassified events are rejected.
- **Access Control:** `secret`-tier events MUST NOT be broadcast to unauthorized subscribers (events.md §3.11). Broader ACL-gating of governance events is referenced via INT-GOV-EVENT-001 (Part 14 §14.11) but its enforcement scope is affected by CONFLICT-03.
- **Authentication/Authorization:** Authorization for protected operations uses INT-SEC-AUTH-001 (SecurityManager.authorize); whether authentication is required in v1.0 is subject to CONFLICT-03 (Part 00 §0.2.2 defers AuthN/AuthZ to v2.0). Observability MUST NOT assume an active AuthN layer in v1.0.

### 6.7 Sensitive Information in Logs

**Status:** PARTIALLY SPECIFIED (EXISTING: Part 00 §0.4 Principle 12 prohibition, P12-ADR-008 payload redaction, events.md §20 classification + §3.11 broadcast restriction; UNSPECIFIED: handling procedures, secret-logging mechanism per configuration.md §13.5)

- **Content:** Model reasoning, prompts, responses, context, memory, user information, tool results MUST NOT be logged unless explicitly required by architecture (Part 00 §0.4 Principle 12).
- **PII/Secrets:** P12-ADR-008 requires "PII and secrets redacted in payloads" for Part 12 domain events. This is a payload-level redaction requirement on events, not a generic StructuredLogger field-redaction rule. The specific redaction mechanism is **UNSPECIFIED** (implementation-contracts.md DAT.MUST.1 is DERIVED for this reason; configuration.md §13.5 states secret-logging restrictions are not specified in Parts 0–14).
- **Classified data:** Every event declares `metadata.classification` ∈ {`internal`, `confidential`, `secret`} (events.md §20); unclassified events are rejected. The `secret`-tier MUST NOT be broadcast to unauthorized subscribers (events.md §3.11). These are source-defined. Part 14 §8.2 confirms the value set is source-defined but notes that handling procedures beyond the `secret`-tier broadcast restriction are **UNSPECIFIED**.
- **Security Restrictions:** Observability must respect security boundaries (Part 14 §8.2 — Confidentiality UNSPECIFIED). Observability MUST NOT invent classification-handling rules or secret-logging mechanisms.

## 7. Correlation Semantics

**Status:** EXISTING (Part 00 §0.4 Principle 8; Part 12 events.md §4)

Part 00 §0.4 Principle 8 requires every Event to carry both identifiers. Part 12 events.md §4 defines their semantics:

- **`correlation_id`** (DEFINED): Groups all events belonging to one user-visible action (workflow, prompt, council session, delegation, user request, system operation). Used for per-action idempotency and reconstruction (events.md §4, §22).
- **`causation_id`** (DEFINED): Points to the immediate parent event that caused this one; forms a directed acyclic graph (DAG) of causality (events.md §4). Root events have no `causation_id`.

**Distinction (preserve, do not conflate):**
`correlation_id` answers "what action is this part of?"; `causation_id` answers "what event directly caused this one?". They are NOT interchangeable.

| Property | `correlation_id` | `causation_id` |
|----------|------------------|----------------|
| What it identifies | One user-visible action group | The immediate parent event |
| When created | When the action/session begins | On each derived event |
| Propagates to | All events in the action group | The single event that caused this one |
| Present on logs? | REQUIRED (per Principle 12) | Source-defined for Events; not mandated on every log line |
| Present on events? | REQUIRED (Principle 8) | REQUIRED (Principle 8) |
| Present on traces? | Correlated where source defines | Correlated where source defines |

**Generation algorithm:** NOT specified by the architecture. This document MUST NOT prescribe UUID or any other generation scheme.

**Logs are associated with:**
- **Requests:** Through correlation_id in EventBus events
- **Tasks:** Via TaskCreated/TaskCompleted events (Part 12 events.md §5+)
- **Workflows:** Through workflow lifecycle events (Part 12 events.md)
- **Executions:** Via agent.lifecycle.registered events (Part 12 events.md §5)
- **Agents:** Through agent lifecycle events (Part 12 events.md §5)
- **Councils:** Through council.decision.published events (Part 12 events.md §5)

**Cross-component propagation contract:** Part 12 events.md §4, §22 and 12.7 define correlation grouping and causation DAG semantics, but the cross-component **correlation propagation contract** (how a `correlation_id` is created, inherited, replaced, or terminated across service boundaries) is only partially defined. Treat the full propagation model as **PARTIALLY SPECIFIED** rather than fully defined (see §9 and §33).

## 8. Causation Semantics

**Status:** EXISTING (Part 00 §0.4 Principle 8; Part 12 events.md §4)

- **What it identifies:** The event that directly caused the current event.
- **How it relates to correlation:** `correlation_id` groups the whole action; `causation_id` links one event to its immediate predecessor. A single `correlation_id` spans many events; each event has at most one direct `causation_id`.
- **When present:** On every derived (non-root) event, per Principle 8.
- **When absent:** Root events have no `causation_id`.
- **How it propagates:** Each emitted event sets `causation_id` to the `event_id` of the event that triggered it, forming a DAG (events.md §4).

No invention of causation semantics beyond events.md §4. Causation is defined for **Events**; it is not defined as a required property of every log line or metric.

## 9. Observability Context Propagation

**Status:** PARTIALLY SPECIFIED (identifiers defined in Part 12 events.md §4, §22; 12.7 §1.2). Context schema depends on `context.md`, which is **EMPTY**.

| Context Element | Source | Required? | Propagation | Status |
|-----------------|--------|-----------|-------------|--------|
| `correlation_id` | Part 00 §0.4 Principle 8; events.md §4 | REQUIRED (Events) | Via EventBus event envelope | DEFINED |
| `causation_id` | Part 00 §0.4 Principle 8; events.md §4 | REQUIRED (Events) | Via EventBus event envelope | DEFINED |
| `trace` object (`trace_id`/`span_id`/`parent_span_id`) | events.md §4; 12.7 §1.2 (W3C) | Defined on Events | Via EventBus event envelope | CONCEPTS DEFINED |
| General context propagation schema (e.g. request context, tenant context, propagation headers) | `context.md` | — | — | **SOURCE VERIFICATION REQUIRED** (`context.md` EMPTY) |

**Critical:**

`context.md` is currently **EMPTY**. Therefore this document MUST NOT claim that context propagation is fully specified where the source architecture depends on `context.md`. The correlation and causation *identifiers* are defined independently in events.md; a broader context-propagation *schema* is not. Observability context propagation beyond the defined identifiers is **UNSPECIFIED / SOURCE VERIFICATION REQUIRED**.

Cross-document note: `configuration.md §16` (`"Context is defined in context.md"`) references a document that is currently EMPTY. This is a **cross-document inconsistency** (see §37). Observability.md does not resolve it; it is recorded.

Cross-document note: `implementation-contracts.md §12 CTX.MUST.1` ("Context propagation MUST be immutable and auditable", source Part 7 Principle 5; Part 12 events.md) is classified **DERIVED**; correlation propagation is listed as a **GAP** in implementation-contracts.md §27. Observability.md reflects the same state: identifiers DEFINED, propagation contract PARTIALLY SPECIFIED / GAP.

## 10. Trace Architecture

**Status:** PARTIALLY SPECIFIED (Part 12 events.md §4; 12.7 §1.2)

Tracing *concepts* are defined by the architecture, but a tracing *backend/technology* is not:

- Each event carries a `trace` object: `trace_id` (W3C Trace Context), `span_id`, `parent_span_id` (events.md §4; 12.7 §1.2 maps these to W3C Trace Context).
- The span hierarchy is reconstructable by following `trace.parent_span_id` (events.md §22).

A tracing system, collector, propagator, or sampling policy is **NOT specified** by Parts 0–13. Do NOT select OpenTelemetry, Jaeger, Zipkin, or any other framework.

| Element | Status |
|---------|--------|
| Trace Concepts (`trace_id`/`span_id`/`parent_span_id` in event envelope) | DEFINED |
| Trace Backend / Propagation Mechanism / Sampling | UNSPECIFIED |

Distinguish clearly: `correlation_id` (action grouping) ≠ `causation_id` (parent event) ≠ `trace_id`/`span_id` (distributed-trace span hierarchy).

## 11. Metrics Architecture

**Status:** UNSPECIFIED (responsibility is defined; names, schema, units, backend are not)

The AI-OS architecture defines a metrics **responsibility**, not a metric **schema**:

- **Responsibility (DEFINED):** ObservabilityManager (M9) "receives metrics from all managers" (Part 01 §1.8.1 M9; INV-RT-008) and owns metrics aggregation (Part 01 §1.8.1 lists "Metrics" among M9 responsibilities).
- **Metric schema (UNSPECIFIED):** No metric *names*, *fields*, *units*, *label dimensions*, or *collection intervals* are established by Parts 0–13.
- **Metric backend (UNSPECIFIED):** No metrics store, exporter, or collection system is specified.

| Aspect | Status | Source |
|--------|--------|--------|
| Metrics responsibility (M9 aggregates metrics) | DEFINED | Part 01 §1.8.1 M9; INV-RT-008 |
| Metric names / categories | UNSPECIFIED | — none in Parts 0–13 |
| Metric schema / fields / units | UNSPECIFIED | — none in Parts 0–13 |
| Metric backend / storage | UNSPECIFIED | — none in Parts 0–13 |

No specific metric category (e.g. "system metrics", "component metrics", "health metrics", "event metrics", "failure metrics") is labeled REQUIRED by the architecture. Any such named category would be an invention. Conformance requires that the metrics *responsibility* exists (M9 receives metrics), not that any named metric is produced.

**Architectural vs implementation/runtime metrics:** Only the M9 aggregation *responsibility* is architectural. CPU/memory/request-latency/throughput metrics and similar are NOT defined and MUST NOT be invented.

## 12. Event Observability

**Status:** EXISTING (Part 00 §0.4 Principle 1; Part 12 events.md; 15.7-Communication-and-Event-Implementation.md)

| Communication / Event Signal | Producer | Purpose | Correlation | Failure Visibility | Source |
| ---------------------------- | -------- | ------- | ----------- | ------------------ | ------ |
| Event publication | All components | Event emission | `correlation_id` + `causation_id` (on emitted event) | EventBus routing | Part 00 §0.4 Principle 1; events.md §4 |
| Event subscription | All components | Event reception | `correlation_id` (consumed) | EventBus errors | Part 00 §0.4 Principle 1 |
| Message routing | EventBus | Topic routing | `correlation_id` | EventBus failures | Part 00 §0.4 Principle 1 |
| Delivery confirmation | EventBus | Acknowledgment | `correlation_id` | EventBus nack (delivery guarantees defined in events.md §18/§21) | events.md §18 |
| Subscription management | ServiceRegistry | Service lifecycle | `correlation_id` | Registration failures | Part 01 §1.7.2 |

**Event envelope (source-defined, events.md §4):** `event_type`, `produced_at` (timestamp), `event_id`, `correlation_id`, `causation_id`, `partition_key`, `metadata.classification`, `security.signature`, `trace` object. These fields are defined for **Events**, not invented for logs.

**Not Invented:** Event replay telemetry, schema-registry metrics, broker/queue-depth metrics, and delivery-guarantee dashboards are NOT required unless a source Part defines them. The events.md §18/§21 delivery model (idempotency window, ordering, priority) is the authoritative basis; observability around it is limited to what those sections state.

## 13. Audit and Observability Boundary

**Status:** PROPOSED (P13-ADR-006 Draft; supported by Part 13 §11 Auditability and Accountability)

Auditability is proposed in P13-ADR-006 (Draft) and elaborated in Part 13 §11:

- All governance-relevant actions recorded in an immutable, tamper-evident audit trail (§11).
- G-09 Audit Manager owns/operates the audit trail; G-10 Accountability Manager binds actions to accountable principals (§11; Part 13 §1.1 component model).
- Audit store is write-once, read-many (WORM) (§11).
- Retention is policy-driven: G-01 defines retention policies; examples include "Data Audit" retained 7 years (§11). Retention is therefore **DEFINED as policy-driven**, not "implementation-defined".

**Distinction (preserve):** Operational Logs (StructuredLogger output) are NOT audit records. Audit Records are the governance-specific, tamper-evident, WORM-stored evidence produced per P13-ADR-006/§11. Observability.md MUST NOT conflate the two.

**Auditable Records (source-accurate):**

| Auditable Action | Producer | Required Record | Retention | Access | Source |
| ---------------- | -------- | --------------- | --------- | ------ | ------ |
| Governance decisions | Governance Components | Decision records with voting history | Per G-01 retention policy (e.g. 7y data audit) | G-10 / audit scope | P13-ADR-006 Draft; §11 |
| Authorization decisions | SecurityManager (M8) | Decision with context | Per G-01 retention policy | Audit scope (CONFLICT-03 affects v1.0 auth) | Part 14 §5.2 (INT-SEC-AUTH-001) |

Do NOT invent: SIEM products, compliance-standard mappings (SOC2/ISO), audit databases, or retention periods beyond those defined in §11.

## 14. Observability Security

**Status:** EXISTING (Part 12 events.md §4/§20; P12-ADR-008; Part 14 §8.2; Part 13 governance)

| Information Category | Observability Allowed? | Restriction | Protection | Source |
| -------------------- | ---------------------- | ----------- | ---------- | ------ |
| Governance events | Yes | Signed; classified; `secret`-tier not broadcast to unauthorized subscribers | Event signature + classification + subscriber authorization (events.md §3.11) | Part 12 events.md §4/§20 |
| PII/secrets | No (in payloads) | Redacted in Part 12 domain event payloads | Payload redaction per P12-ADR-008 | Part 12 P12-ADR-008 |
| Model reasoning | No | Not logged per Part 00 §0.4 Principle 12 | Content filtering | Part 00 §0.4 Principle 12 |
| Classified data | Depends on tier | Every event declares `metadata.classification` ∈ {`internal`,`confidential`,`secret`}; unclassified events rejected | Classification-based access; handling procedures beyond `secret`-tier broadcast UNSPECIFIED (Part 14 §8.2) | Part 12 events.md §20; Part 14 §8.2 |

Observability MUST NOT reproduce real secret values, credentials, tokens, or keys. Classification value set and `secret`-tier broadcast restriction are source-defined; other handling procedures are UNSPECIFIED.

## 15. Telemetry Redaction

**Status:** PARTIALLY SPECIFIED (EXISTING: P12-ADR-008 payload redaction of PII/secrets in Part 12 domain event payloads; UNSPECIFIED: generic log-line redaction mechanism, masking format, omission format)

Distinguish carefully:

| Category | Meaning | Status |
|----------|---------|--------|
| **Prohibited data** | Data that MUST NOT appear in logs/telemetry at all (e.g. real secrets, credentials, model reasoning) | EXISTING (Principle 12; events.md §20) |
| **Sensitive data** | PII/secrets in Part 12 domain event payloads | Redacted per P12-ADR-008 |
| **Redacted data** | Data replaced by a redaction transform in event payloads | P12-ADR-008 (payload-level) |
| **Masked data** | Data partially obscured | Mechanism UNSPECIFIED |
| **Omitted data** | Data dropped before emission | Mechanism UNSPECIFIED |

No specific masking format (e.g. `***`, `[REDACTED]`) is defined by the architecture. If a mechanism is unspecified, state: **"Redaction mechanism: UNSPECIFIED."** This document MUST NOT invent a redaction library or logging filter implementation.

## 16. Observability Ownership

**Status:** UNSPECIFIED (per components.md §5.1, all components list Observability Owner = UNSPECIFIED)

| Component / Domain | Observability Responsibility | Signal | Source | Status |
|--------------------|------------------------------|--------|--------|--------|
| StructuredLogger (C4) | Sole logging abstraction; emits structured logs | Logs | Part 00 §0.4 Principle 12; Part 3 §3.3 | Logging responsibility DEFINED; ownership UNSPECIFIED |
| ObservabilityManager (M9) | Aggregates metrics from all managers; owns metrics collection | Metrics | Part 01 §1.8.1 M9 | Aggregation responsibility DEFINED; ownership UNSPECIFIED |
| EventBus (C1) | Carries Events with correlation/causation | Events | Part 00 §0.4 Principles 1, 8 | Channel DEFINED; ownership UNSPECIFIED |
| All Components / Managers | Emit logs and Events | Logs / Events | Principle 12 / Principle 1 | Emission responsibility DEFINED; ownership UNSPECIFIED |
| Audit trail (G-09 / G-10) | Operates WORM governance audit trail | Audit Records | Part 13 §11; P13-ADR-006 | DEFINED (proposed) |

Cross-checked against `components.md §5.1`: every component row lists **Observability Owner = UNSPECIFIED**. Therefore observability *ownership* is not architecturally assigned. This document does NOT invent per-component observability owners.

Distinguish:
- **telemetry emission** (components emit via StructuredLogger / EventBus) — DEFINED
- **telemetry collection** (ObservabilityManager receives metrics) — DEFINED (responsibility)
- **telemetry storage** — UNSPECIFIED
- **telemetry analysis** — UNSPECIFIED

## 17. Runtime Observability

**Status:** EXISTING where defined; UNSPECIFIED for lifecycle telemetry (`runtime-map.md` is EMPTY)

`runtime-map.md` is currently **EMPTY**. Therefore runtime *lifecycle* observability (startup/shutdown metrics, phase telemetry, kernel lifecycle events) is **NOT fully specified** by the source architecture.

What is explicitly established:
- Component failure events: ComponentDegraded, ComponentFailed, CoreManagerFailed, KernelFatalError (Part 01 §1.12.4).
- Lifecycle transition Events are emitted (Part 00 §0.4 Principle 12 — "Events for state transitions").
- Health/liveness/readiness probes for the collaboration domain (Part 12 §12.9, §12.12; RI-005/RI-006).

What is NOT established (do not invent):
- Startup/shutdown *metrics* (not defined)
- Kernel phase *telemetry* (runtime-map.md empty)
- Per-phase observability contracts (RT.MUST.1 in implementation-contracts.md is SOURCE VERIFICATION REQUIRED due to empty runtime-map.md)

Runtime observability is **CONDITIONALLY SPECIFIED**: failure and lifecycle *Events* are required; lifecycle *metrics/telemetry* remain UNSPECIFIED pending runtime-map.md.

## 18. Agent and Council Observability

**Status:** EXISTING (Part 12 P12-ADR-008, P12-ADR-003, P12-ADR-010)

### 18.1 Agent Observability

**Existing Observability Requirements:**

- Part 12 events.md §4 event envelope fields: `correlation_id`, `causation_id`, and a `trace` object carrying `trace_id`, `span_id`, `parent_span_id` (W3C Trace Context; 12.7 §1.2).
- Lifecycle events: `agent.lifecycle.registered`, `agent.lifecycle.deregistered`, `agent.lifecycle.heartbeat` (events.md §5; P12-ADR-010 runtime contracts cover liveness/readiness, capabilities, lifecycle hooks — NOT a `healthCheck()` method).
- `AgentHeartbeat` maintains active status; `HealthReport` carries liveness, responsiveness, trust metrics (Part 12 components.md).

| Agent Signal | Producer | Purpose | Required? | Source |
|-------------|----------|---------|----------|--------|
| Agent registration | AgentManager | Agent lifecycle tracking | Required | Part 12 events.md §5 (agent.lifecycle.registered) |
| Agent heartbeat | AgentManager | Health/liveness monitoring | Required | Part 12 events.md §5; components.md (AgentHeartbeat) |
| Agent task assignment | WorkflowManager | Task delegation tracking | Required | Part 12 events.md; P12-ADR-004 |
| Agent decision records | CouncilService | Council decisions | Required | Part 12 events.md; P12-ADR-003 |
| Agent failures | WorkflowManager | Failure reporting | Required | Part 12 events.md (workflow/agent error events) |

### 18.2 Council Observability

**Existing Observability Requirements:**

- CouncilDecisionRecord events per P12-ADR-003 (immutable, voting history, dissent tracking)
- Council lifecycle events (Part 12 events.md §5)

| Council Signal | Producer | Purpose | Required? | Source |
|---------------|----------|---------|----------|--------|
| Council convening | CouncilService | Decision initiation | Required | Part 12 events.md §5; P12-ADR-003 |
| Council consensus | CouncilService | Decision outcomes | Required | Part 12 events.md §5; P12-ADR-003 |
| Council dissent | CouncilService | Disagreement tracking | Required | Part 12 events.md §5; P12-ADR-003 |
| Council failures | CouncilService | Decision failures | Required | Part 12 events.md §5 |
| Council escalations | HumanInteractionService | Human oversight | Required | Part 12 events.md §5 |

**Not Invented:** No telemetry events for internal model chain-of-thought or hidden reasoning. Only externally observable execution metadata supported by events.md is documented. Observability MUST NOT log internal agent reasoning.

## 19. Workflow Observability

**Status:** EXISTING (Part 12 P12-ADR-004)

| Workflow Signal | Producer | Purpose | Required? | Source |
|---------------|----------|---------|----------|--------|
| Workflow start | WorkflowManager | Workflow initiation | Required | Part 12 events.md §5 (workflow.lifecycle.started) |
| Workflow completion | WorkflowManager | Workflow completion | Required | Part 12 events.md §5 |
| Workflow state | WorkflowManager | Workflow progress tracking | Required | Part 12 events.md §5 |
| Workflow failures | WorkflowManager | Failure reporting | Required | Part 12 events.md (workflow.lifecycle.failed) |
| Task execution | WorkflowManager | Task lifecycle tracking | Required | Part 12 events.md (task events) |

No invented workflow states or state-transition metrics beyond those in events.md §5.

## 20. Memory and Knowledge Observability

**Status:** UNSPECIFIED (no telemetry/observability requirement defined by Parts 0–13)

Part 12 events.md §10 defines *context events* (`context.window.*`, `context.refresh.*`, `context.token.budget.exceeded`) as part of the event architecture, but these are domain Events, not a Memory/Knowledge observability/telemetry requirement. Parts 0–13 do not define:

- memory access metrics
- knowledge operation metrics
- retrieval/persistence telemetry
- memory usage dashboards

Observability of memory/knowledge is therefore **UNSPECIFIED**. Memory tracking/access-pattern behavior (if any) is a MemoryManager behavior contract, not an observability/metric requirement, and is not asserted as telemetry here. Sensitive memory content MUST NOT be exposed through telemetry (per §14).

## 21. Plugin and Integration Observability

**Status:** UNSPECIFIED (Part 00 §0.5.2; Part 14 §14.4/§14.5; 15.8-Plugin-and-Integration-Implementation.md)

Observability requirements for plugins/integrations are not defined by Parts 0–13 beyond generic event emission (Part 00 §0.4 Principle 1) and the security restrictions in §14. Specifically NOT defined:

- provider-specific telemetry
- MCP invocation metrics
- integration success/failure dashboards
- external-system health probes

Observability MUST NOT invent integration telemetry. Plugin/integration observability remains **UNSPECIFIED**.

## 22. Deployment Observability

**Status:** UNSPECIFIED (deployment.md; 15.10-Deployment-and-Operations-Implementation.md)

Deployment-specific observability (rollout metrics, canary metrics, infrastructure monitoring, deployment dashboards, health endpoints, readiness probes as Kubernetes primitives, container metrics, cloud monitoring) is not defined by Parts 0–13. Observability MUST NOT invent deployment telemetry. Deployment observability remains **UNSPECIFIED**.

Note: This is consistent with `implementation-contracts.md` (DEP deployment technology = UNSPECIFIED; no deployment observability backend mandated). Health/liveness/readiness *probe semantics* are defined only for the collaboration domain (§23 / §17), not as a deployment-infrastructure observability requirement.

## 23. Failure Observability

**Status:** EXISTING (Part 00 §0.4 Principle 9; Part 01 §1.12.1/§1.12.4; cross-checked runtime-map.md [EMPTY], deployment.md, testing.md [EMPTY])

Failure observability means a failure is **made visible via an Event**. It does NOT imply a retry/fallback mechanism exists — observability and recovery are distinct. The architecture defines these failure signals:

| Failure Domain | Observable Signal | Required? | Source | Status |
|---------------|-------------------|-----------|--------|--------|
| Component degradation | `ComponentDegraded` event | Required | Part 01 §1.12.4 | EXISTING |
| Component failure | `ComponentFailed` event | Required | Part 01 §1.12.4 | EXISTING |
| Core Manager failure | `CoreManagerFailed` event | Required | Part 01 §1.12.4 | EXISTING |
| Kernel fatal error | `KernelFatalError` event | Required | Part 01 §1.12.4 | EXISTING |
| Workflow failure | `workflow.lifecycle.failed` | Required | Part 12 events.md | EXISTING |
| Agent error | `agent.lifecycle.error` | Required | Part 12 events.md | EXISTING |
| Participant liveness failure | `HealthCheckFailed` | Required | Part 12 components.md | EXISTING |

Startup, configuration, dependency, security, and persistence failures are observable only insofar as the architecture emits an Event for them; where no Event is defined, failure observability is **UNSPECIFIED**. Observability MUST NOT invent retry/fallback merely because a failure is observable.

## 24. Telemetry Lifecycle

**Status:** UNSPECIFIED for collection/storage/query/retention (Emit and Metrics-Collect are declared; rest UNSPECIFIED)

The lifecycle of observability data — Emit → Propagate → Collect → Process → Store → Query/Analysis:

| Stage | Architectural Requirement | Source | Status |
|-------|---------------------------|--------|--------|
| Emission | Components emit structured logs and Events | Part 00 §0.4 Principle 12 | DEFINED |
| Propagation | Events carry correlation/causation via EventBus | Part 00 §0.4 Principles 1, 8 | DEFINED (identifiers) |
| Collection | ObservabilityManager (M9) receives metrics | Part 01 §1.8.1 M9 / INV-RT-008 | DEFINED (metrics responsibility) |
| Processing | — | — | UNSPECIFIED |
| Storage | — | — | UNSPECIFIED |
| Query/Analysis | — | — | UNSPECIFIED |

The audit trail (§13) has WORM + policy-driven retention, but that is governance audit data, not general observability data. Do NOT invent collection agents, storage backends, retention periods, or query systems.

## 25. Retention

**Status:** UNSPECIFIED (general observability data); DEFINED as policy-driven for governance audit data

No retention period is defined for general observability data (logs, metrics, traces, events) by Parts 0–13.

- **General observability data:** Retention policy is **UNSPECIFIED**. Do not infer retention from compliance or common practice.
- **Governance audit records:** Retention is policy-driven per G-01 (e.g. "Data Audit" retained 7 years, Part 13 §11). This is audit data, not general observability data.

"Telemetry retention policy is UNSPECIFIED" for all non-audit observability signals.

## 26. Sampling

**Status:** UNSPECIFIED

The architecture does **NOT** define log sampling, trace sampling, or any sampling percentage (head/tail/1%/10%).

If no sampling is defined by authoritative sources, sampling is **UNSPECIFIED**. Do not prescribe sampling rates or policies.

## 27. Performance Constraints

**Status:** UNSPECIFIED (except collaboration-domain probe latency)

The architecture does not define numerical observability overhead limits (e.g. max log volume, max trace cardinality, max metrics cost) for general observability.

- The only numerical performance constraint tied to observability is the collaboration-domain health probe response: liveness/readiness probes MUST respond within 100ms (RI-005/RI-006; Part 12 §12.9/§12.12). That is a probe-latency contract, not a general observability-overhead limit.
- "Observability overhead constraints are UNSPECIFIED" for all other dimensions. Do not invent numerical limits.

## 28. Configuration Relationship

**Status:** UNSPECIFIED (configuration.md defines four-layer merge via ConfigurationManager; no observability/telemetry configuration schema defined by Parts 0–13)

| Observability Configuration | Source | Status |
|-----------------------------|--------|--------|
| Four-layer config merge domain exists | Part 00 §0.4 Principle 10; configuration.md | EXISTING (domain) |
| `kernel.observability.*` configuration item | configuration.md §8/§9 | Listed but Type/Required/Default = "Not Specified" |
| Observability config schema (log levels, metric scrape, trace sampling, redaction rules) | — | UNSPECIFIED |

`configuration.md §7.10` lists an "Observability Configuration" domain (metrics collection settings, tracing configuration, health check parameters) "as defined in Part 11," but the actual configuration registry items are "Not Specified." Observability configuration (log levels, metric intervals, trace sampling, redaction rules) is therefore **UNSPECIFIED**. The configuration *domain* exists; the observability *configuration schema* and *backend* are UNSPECIFIED. Do not invent configuration keys (e.g. `observability.log.level`, `metrics.interval`).

## 29. Dependency Relationship

**Status:** UNSPECIFIED (no external observability dependency mandated)

Observability dependencies (external systems, storage, collectors) are not defined by the AI-OS architecture. ObservabilityManager (M9) is the in-kernel aggregation point; no external dependency is mandated.

Distinguish:

- **Component → Telemetry abstraction:** DEFINED (StructuredLogger, EventBus, ObservabilityManager are in-kernel).
- **Component → Monitoring product:** NOT defined; MUST NOT be invented.

Cross-checked against `dependency-map.md`: no observability-specific external dependency is established by authoritative sources. Implementations MAY choose a backend, but AI-OS architecture does not require one.

## 30. Observability Invariants

**Status:** EXISTING (derived from Part 00 §0.4 Principles 8, 12; Part 12 events.md §4/§20)

| ID | Invariant | Source | Status | Verification |
|----|-----------|--------|--------|--------------|
| OBS-INV-1 | Structured logs MUST be JSON and include `correlation_id` | Part 00 §0.4 Principle 12 | EXISTING | Log schema validation (OBS.MUST.1) |
| OBS-INV-2 | Events MUST carry `correlation_id` and `causation_id` and be immutable | Part 00 §0.4 Principles 8; EVT.MUST.1/2 | EXISTING | Event envelope validation |
| OBS-INV-3 | Sensitive information MUST NOT appear in logs/telemetry where architecture prohibits it | Part 00 §0.4 Principle 12; P12-ADR-008; events.md §20 | EXISTING (partial) | Redaction / content test (DAT.MUST.1) |
| OBS-INV-4 | Telemetry MUST remain attributable to the correct architectural operation via `correlation_id` where required | Part 12 events.md §4/§22 | EXISTING | Correlation propagation test |
| OBS-INV-5 | Observability MUST NOT alter system semantics (additive only) | Part 00 §0.4 Principles 8, 12 | EXISTING | Behavioral/contract test |

All invariants are source-backed. No invariant is invented.

## 31. Observability Verification

**Status:** DERIVED (Part 00 §0.4 Principles; cross-checked against testing.md [EMPTY] and implementation-contracts.md §23)

| Requirement | Verification Method | Test Exists? | Status | Source |
|-------------|---------------------|--------------|--------|--------|
| Structured logs with `correlation_id` | Log field/schema validation | NO (PROPOSED in contract test matrix) | DERIVED | Part 00 §0.4 Principle 12; OBS.MUST.1 |
| Events carry `correlation_id`/`causation_id` | Event envelope validation | NO (PROPOSED) | DERIVED | Principle 8; EVT.MUST.1 |
| Events immutable | Event schema validation | NO (PROPOSED) | DERIVED | Principle 8; EVT.MUST.2 / SEC.MUST.2 |
| Failures observable via Events | Failure-event generation test | NO (PROPOSED) | DERIVED | Principle 9; §23 |
| PII/secrets redacted in payloads | Payload redaction test | NO (PROPOSED) | DERIVED | P12-ADR-008; DAT.MUST.1 |
| No real secrets in logs | Log sanitization test | NO (PROPOSED) | DERIVED | Principle 12; DAT.MUST.1 |
| Health/liveness/readiness probes | Probe-latency test (≤100ms) | NO (PROPOSED) | DERIVED | RI-005/RI-006; §17 |
| Metric collection by M9 | Metrics reception test | NO (PROPOSED) | DERIVED | Part 01 §1.8.1 M9; MET.MUST.1 |

**Important:** `testing.md` is currently **EMPTY**. No test framework or passing test is asserted. Proposed verification methods are recorded; none are claimed to exist or pass. Where a requirement is UNSPECIFIED (e.g. metric schema, trace backend, retention, sampling), no verification can be defined — that gap is recorded, not fabricated.

## 32. Observability Conformance

**Status:** DERIVED (from Part 00 §0.4 Principles)

An implementation conforms when:

1. required telemetry signals exist (structured logs JSON + `correlation_id` per Principle 12; Events with `correlation_id`/`causation_id` per Principle 8);
2. required fields are present (`correlation_id` on logs; `correlation_id`/`causation_id` on Events);
3. correlation/causation semantics are preserved where required (identifiers present and consistent; full cross-component propagation contract remains PARTIALLY SPECIFIED — conformance requires only presence/consistency, not every propagation edge);
4. security constraints are preserved (no sensitive data in logs; PII/secrets redacted in event payloads; classification declared; `secret`-tier not broadcast);
5. sensitive data is handled according to architecture (prohibited data excluded; payload redaction per P12-ADR-008);
6. telemetry does not introduce unsupported coupling (no mandated monitoring platform, no Component → Monitoring product dependency);
7. verification evidence exists where required (tests proposed; none yet exist per empty testing.md).

**Make clear:** Telemetry implementation technology is independent from architectural conformance unless architecture explicitly constrains it. Conformance does **NOT** require a metrics backend, a tracing system, a log aggregation platform, retention/lifecycle tooling, or observability-specific configuration — those are UNSPECIFIED and out of conformance scope.

## 33. Observability Gaps and Unspecified Areas

| Area | Current State | Source | Impact | Status |
|------|---------------|--------|--------|--------|
| Telemetry backend | No backend mandated | Parts 0–13 silent | Implementation choice | UNSPECIFIED |
| Collection architecture | M9 receives metrics (responsibility) | Part 01 §1.8.1 M9 | Storage/processing unspecified | PARTIALLY SPECIFIED |
| Storage | No store defined | Parts 0–13 silent | Implementation choice | UNSPECIFIED |
| Retention (general) | No period defined | Parts 0–13 silent | Implementation choice | UNSPECIFIED |
| Sampling | No policy defined | Parts 0–13 silent | Implementation choice | UNSPECIFIED |
| Schema evolution | Event schema versioning GAP cited | implementation-contracts.md §27 | Versioning undefined | GAP |
| Runtime lifecycle observability | runtime-map.md EMPTY | runtime-map.md | Phase telemetry undefined | SOURCE VERIFICATION REQUIRED |
| Deployment observability | No infra telemetry defined | deployment.md | Implementation choice | UNSPECIFIED |
| Context propagation | context.md EMPTY; identifiers defined in events.md | context.md; events.md §4 | Broad context schema undefined | SOURCE VERIFICATION REQUIRED / PARTIALLY SPECIFIED |
| Metric catalog | No names/fields defined | Parts 0–13 silent | Implementation choice | UNSPECIFIED |
| Trace semantics (backend) | Concepts defined; backend not | events.md §4; 12.7 §1.2 | Implementation choice | PARTIALLY SPECIFIED |
| Correlation propagation contract | Identifiers + grouping defined; cross-boundary contract partial | events.md §4/§22 | Full propagation undefined | GAP / PARTIALLY SPECIFIED |
| Sensitive-data handling procedures | Classification + broadcast restriction defined; procedures not | events.md §20; Part 14 §8.2 | Handling procedures undefined | PARTIALLY SPECIFIED |
| Health endpoint technology | Probe semantics + 100ms defined; platform not | Part 12 §12.9/§12.12 | Platform-specific contract undefined | PARTIALLY SPECIFIED |

Only items the architecture *requires but leaves undefined* are classified as GAP. The remainder are UNSPECIFIED (architecture silent) — not promoted to GAP.

## 34. Observability-to-Contract Traceability

**Status:** DERIVED (cross-checked against implementation-contracts.md §17, §20, §21)

| Observability Requirement | Contract ID | Contract Status | Source | Verification |
|---------------------------|-------------|-----------------|--------|--------------|
| Structured logs with `correlation_id` | OBS.MUST.1 | VALID | Part 00 §0.4 Principle 12 | Log parsing |
| Events carry `correlation_id`/`causation_id` | EVT.MUST.1 | VALID | Part 00 §0.4 Principle 8; events.md §4 | Event validation |
| Events delivered via EventBus | EVT.MUST.2 | VALID | Part 00 Principle 1 | Event tracing |
| Metrics collected from all managers | MET.MUST.1 | DERIVED | Part 01 §1.8.1 M9 | Metrics validation |
| Sensitive fields in logs MUST NOT contain real secrets | DAT.MUST.1 | DERIVED | Part 00 §0.4 Principle 12; events.md §20 | Log sanitization |
| PII/secrets redacted in event payloads | SEC.MUST.5 | DERIVED | P12-ADR-008 | Event validation |

**Consistency findings:**

- `OBS.MUST.1` ("Structured logs with correlation_id") — **SUPPORTED**, status VALID. observability.md §6.4 requires only `correlation_id` as a mandated field; `OBS.MUST.1` should not be read as mandating `component`, `timestamp`, `event_type`, etc. on every log line. The §17 table does not enumerate such fields, so the two are consistent.
- `EVT.MUST.1` ("Events carry correlation/causation") — **SUPPORTED**, status VALID. Matches observability.md §7 and OBS-INV-2.
- `MET.MUST.1` ("Metrics collected from all managers") — **SUPPORTED**, status DERIVED. Matches observability.md §11 (responsibility defined; schema UNSPECIFIED).
- `DAT.MUST.1` / `SEC.MUST.5` — **SUPPORTED**, status DERIVED. Match observability.md §14/§15 (redaction mechanism UNSPECIFIED).
- No `LOG.MUST.1` or `MEM.MUST.1` contract exists in implementation-contracts.md (verified). A prior draft referenced these; they are NOT present in the authoritative contract set and MUST NOT be invented here.

No TRACEABILITY CONFLICT detected: observability.md establishes exactly the requirements its contracts assert, and no contract exceeds the architecture. Where a contract is stronger than the architecture, the inconsistency is recorded rather than silently "fixed."

## 35. Observability-to-ADR Traceability

**Status:** No formal ADR records exist (adrs.md §4/§5: "No formal ADR records currently identified").

Observability decisions in AI-OS trace to **inline architectural decisions in Parts 0–14**, referenced as Part-scoped decision identifiers (e.g. `P12-ADR-008`, `P13-ADR-006`). These are **not** formal `adrs.md` ADR records — `adrs.md` currently holds zero formal ADRs. They are indexed as architectural decisions from Parts 0–14.

| Observability Decision | Source (Part-scoped decision / section) | Type | Source | Status |
|------------------------|------------------------------------------|------|--------|--------|
| Structured logging + correlation_id | Part 00 §0.4 Principle 12 | Architectural Principle | Part 0 | EXISTING |
| Events carry correlation/causation; immutable | Part 00 §0.4 Principle 8 | Architectural Principle | Part 0 | EXISTING |
| Event-First communication (EventBus) | Part 00 §0.4 Principle 1 | Architectural Principle | Part 0 | EXISTING |
| Failures via Events | Part 00 §0.4 Principle 9 | Architectural Principle | Part 0 | EXISTING |
| M9 receives/aggregates metrics | Part 01 §1.8.1 M9 | Component responsibility | Part 1 | EXISTING |
| Event envelope (trace object, classification, signature) | Part 12 events.md §4/§20 | Event schema | Part 12 | EXISTING |
| PII/secrets redacted in payloads | P12-ADR-008 | Part-scoped decision | Part 12 | EXISTING (as Part decision) |
| Governance audit trail (WORM) | P13-ADR-006 (Draft) | Part-scoped decision (Draft) | Part 13 | PROPOSED (Draft) |
| Liveness/readiness probes (100ms) | RI-005/RI-006; Part 12 §12.9/§12.12 | Reliability contract | Part 12 | EXISTING |

Do NOT cite `ADR-XXX` as a formal record; none exist (adrs.md §9 confirms no ADR-007 either). Where a decision is a Draft (P13-ADR-006), its status is preserved as PROPOSED, not upgraded to accepted.

## 36. Source Traceability

Every normative observability requirement MUST have a source document, section where practical, and status.

| Requirement ID | Requirement | Source | Section | Status | Evidence |
|----------------|-------------|--------|---------|--------|----------|
| OBS-R-1 | Structured logs JSON + `correlation_id` | Part 00 §0.4 | Principle 12 | EXISTING | Direct citation |
| OBS-R-2 | Events for state transitions | Part 00 §0.4 | Principle 12 | EXISTING | Direct citation |
| OBS-R-3 | Events carry `correlation_id`/`causation_id`, immutable | Part 00 §0.4 | Principle 8 | EXISTING | Direct citation |
| OBS-R-4 | EventBus is communication substrate | Part 00 §0.4 | Principle 1 | EXISTING | Direct citation |
| OBS-R-5 | Failures observable via Events | Part 00 §0.4 | Principle 9 | EXISTING | Direct citation |
| OBS-R-6 | Four-layer config merge | Part 00 §0.4 | Principle 10 | EXISTING | Direct citation |
| OBS-R-7 | M9 receives/aggregates metrics | Part 01 §1.8.1 | M9; INV-RT-008 | EXISTING | Direct citation |
| OBS-R-8 | Event envelope (trace, classification, signature) | Part 12 events.md | §4, §20 | EXISTING | Direct citation |
| OBS-R-9 | PII/secrets redacted in payloads | P12-ADR-008 | events.md | EXISTING (Part decision) | Direct citation |
| OBS-R-10 | `secret`-tier not broadcast | Part 12 events.md | §3.11 | EXISTING | Direct citation |
| OBS-R-11 | INT-SEC-AUTH-001 authorize | Part 14 §5.2 | INT-SEC-AUTH-001 | EXISTING | Direct citation |
| OBS-R-12 | Governance audit WORM + retention | P13-ADR-006; Part 13 §11 | §11 | PROPOSED (Draft) | Direct citation |
| OBS-R-13 | Liveness/readiness 100ms | Part 12 §12.9/§12.12 | RI-005/RI-006 | EXISTING | Direct citation |
| OBS-R-14 | Correlation propagation contract | Part 12 events.md | §4, §22 | PARTIALLY SPECIFIED | Partial citation |
| OBS-R-15 | Context propagation schema | context.md | — | SOURCE VERIFICATION REQUIRED (empty) | Empty document |

No vague references such as "architecture" or "Part 15" are used where a precise source is available.

## 37. Cross-Document Consistency

Cross-checked WITHOUT MODIFYING other files:

| Document | Checked Item | Result |
|----------|--------------|--------|
| README.md | Observability scope/identity | Consistent (observability.md is the Part 15 observability spec) |
| adrs.md | No formal ADRs | Consistent — observability.md cites Part-scoped decisions, not formal ADRs (§35) |
| components.md | Observability Owner column = UNSPECIFIED for all | Consistent — §16 reflects UNSPECIFIED ownership |
| configuration.md | §7.10 observability config domain; §13.5 secret-logging UNSPECIFIED | Consistent — domain listed, schema UNSPECIFIED (§28) |
| configuration.md | §16 "Context is defined in context.md" | **CONFLICT / INCONSISTENCY** — context.md is EMPTY (§9, recorded) |
| dependency-map.md | No external observability dependency | Consistent — §29 reflects no mandated backend |
| deployment.md | No deployment observability backend | Consistent — §22 UNSPECIFIED |
| implementation-contracts.md | OBS.MUST.1, EVT.MUST.1/2, MET.MUST.1, DAT.MUST.1, SEC.MUST.5 | Consistent — §34 |
| glossary.md | `correlation_id`/`causation_id` terminology | Consistent (no conflicting spelling invented) |
| review-checklist.md | 10/10 quality expectations | Consistent — anti-invention rules enforced |
| context.md | Context schema source | **EMPTY** — observability context propagation not fully specified (§9) |
| runtime-map.md | Runtime lifecycle telemetry | **EMPTY** — runtime observability partially unspecified (§17) |
| testing.md | Test framework / evidence | **EMPTY** — verification methods proposed, none exist (§31) |

**Conflicts preserved (not resolved):**
- **CONFLICT-03:** AuthN/AuthZ scope in v1.0 vs v2.0 (Part 00 §0.2.2 defers to v2.0; Part 13/14 assume active v1.0). Affects whether authorization-based observability is active in v1.0.
- **GAP-SEC:** Confidentiality handling procedures UNSPECIFIED (Part 14 §8.2).
- **UNRES-05:** Referenced as an unresolved item in prior drafts; preserved.
- **Cross-document (newly recorded):** `configuration.md §16` references an EMPTY `context.md`; observability.md does not resolve it.

No silent resolution of any conflict.

## 38. AI Coding Agent Rules

**Status:** DERIVED (from Part 00 §0.4 Principles; required by Part 15 quality pass)

An AI coding agent that adds or modifies telemetry, logging, metrics, tracing, or audit support in AI-OS MUST follow these rules. These rules exist because AI agents tend to over-specify observability by importing generic best-practice patterns; AI-OS deliberately does not adopt them.

**MUST:**

1. Inspect observability.md before changing telemetry-related code.
2. Inspect source architecture before adding telemetry requirements.
3. Preserve exact `correlation_id`/`causation_id` semantics (events.md §4/§22).
4. Never invent telemetry fields.
5. Never invent metric names.
6. Never invent event envelope fields.
7. Never invent trace semantics or backends.
8. Never invent logging backends.
9. Never invent monitoring platforms.
10. Never log secrets or sensitive information when architecture prohibits it (Principle 12; events.md §20).
11. Never invent redaction mechanisms.
12. Never assume OpenTelemetry.
13. Never assume Prometheus.
14. Never assume Grafana.
15. Never assume a tracing backend.
16. Distinguish observability from recovery (observability ≠ retry/fallback).
17. Distinguish audit from operational telemetry (§13).
18. Report UNSPECIFIED observability areas (do not fill them with invention).
19. Stop when an implementation requires an unresolved observability decision (SOURCE VERIFICATION REQUIRED).

**MUST NOT (extended):**

6b. Invent fields such as `component`, `hostname`, `process_id`, `thread_id`, `user_id`, `request_id`, `trace_id` (on logs) as universal log MUSTs unless the source mandates them (§6.4).
7b. Invent metrics (names, schemas, units, intervals) — metrics are UNSPECIFIED (§11).
8b. Invent trace semantics or backends (OpenTelemetry, Jaeger, collector, sampling policy) — only the event-envelope `trace` object is defined (§10).
9b. Invent dashboards, alerts, or notification channels.
10b. Invent retention or lifecycle tooling for general observability data (§25). (Audit retention is policy-driven per §13 only.)
11b. Invent observability infrastructure (Prometheus, Grafana, ELK, Splunk, Datadog, CloudWatch, Azure Monitor, GCP Cloud Monitoring, Loki, New Relic, etc.).
12b. Invent configuration keys (`observability.log.level`, `metrics.interval`, trace sampling flags, redaction-rule schemas) (§28).
13b. Use "industry standard" / "best practice" as justification for a new MUST — only an authoritative source Part may justify a MUST.
14b. Silently resolve CONFLICT-03, GAP-SEC, UNRES-05, or UNSPECIFIED items. Record them.
15b. Alter system semantics for observability — observability is additive; never change component behavior, routing, or failure handling to satisfy a telemetry need.

## 39. Final Observability Architecture Audit

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Authority boundary | PASS | §3 — Parts 0–14 authoritative; no new architecture; no invented platforms |
| Signal model | PASS | §5 — Logs/Events/Metrics/Traces/Audits/Health; distinctness rule |
| Logging architecture | PASS | §6 — JSON + `correlation_id` only; no invented fields |
| Correlation semantics | PASS | §7 — `correlation_id` DEFINED; propagation PARTIALLY SPECIFIED, not over-claimed |
| Causation semantics | PASS | §8 — `causation_id` DEFINED per events.md §4 |
| Context propagation | PASS | §9 — identifiers DEFINED; schema SOURCE VERIFICATION REQUIRED (empty context.md) |
| Trace architecture | PASS | §10 — concepts DEFINED; backend UNSPECIFIED |
| Metrics architecture | PASS | §11 — responsibility DEFINED; names/schema/backend UNSPECIFIED |
| Event observability | PASS | §12 — matches events.md envelope; no invented fields |
| Security/redaction | PASS | §14/§15 — source-backed; redaction mechanism UNSPECIFIED, not invented |
| Ownership | PASS | §16 — reflects components.md UNSPECIFIED; no invented owners |
| Runtime observability | PASS | §17 — failure/lifecycle Events required; lifecycle metrics UNSPECIFIED (empty runtime-map.md) |
| Deployment observability | PASS | §22 — UNSPECIFIED; no infrastructure invented |
| Verification | PASS | §31 — methods proposed; none claimed to exist (testing.md empty) |
| Source traceability | PASS | §36 — every requirement has precise source/section |
| Contract traceability | PASS | §34 — OBS.MUST.1/EVT.MUST.1/2/MET.MUST.1/DAT.MUST.1/SEC.MUST.5 consistent; no TRACEABILITY CONFLICT |
| ADR traceability | PASS | §35 — no formal ADRs; Part-scoped decisions cited correctly |
| Anti-invention | PASS | §38 — 19 MUST + 10 MUST NOT rules; no platform/metric/field invented |

No row is auto-marked PASS without evidence. All PASS rows cite a source-backed section.

## 40. Observability Architecture Readiness

**Status: CONDITIONALLY READY**

**Reasoning:**

The observability *architecture* is well-defined for the signal model, structured logging, correlation/causation semantics, event observability, security/redaction boundaries, audit boundary, failure observability, and AI-agent guardrails. These are source-backed and implementation-safe.

However, full observability conformance readiness CANNOT be claimed because required source documents are empty or draft:

1. **`context.md` = EMPTY** — broad context-propagation schema is SOURCE VERIFICATION REQUIRED (§9). The correlation/causation *identifiers* are defined, but context propagation beyond them is not.
2. **`runtime-map.md` = EMPTY** — runtime lifecycle observability (phase telemetry, startup/shutdown metrics) is not specified (§17); RT.MUST.1 is SOURCE VERIFICATION REQUIRED in implementation-contracts.md.
3. **`testing.md` = EMPTY** — no test framework or verification evidence exists; all proposed verification methods are PROPOSED, none passing (§31).
4. **P13-ADR-006 is Draft** — auditability (WORM audit trail) is PROPOSED, not accepted (§13).
5. **CONFLICT-03 / GAP-SEC / UNRES-05 preserved** — authorization-based observability scope in v1.0 is unresolved (§37).

Therefore the document is **CONDITIONALLY READY**: the architecture it defines is sound and source-backed, but it depends on empty/draft source documents that must be completed before full conformance readiness can be asserted. No false "complete" or "10/10" claim is made.

---

**Document Status:** CONDITIONALLY READY — architecture-defined and source-backed; dependent on empty `context.md` / `runtime-map.md` / `testing.md` and Draft P13-ADR-006.

**Signals:** Logs (EXISTING), Events (EXISTING), Metrics (responsibility DEFINED; schema/backend UNSPECIFIED), Traces (concepts DEFINED; backend UNSPECIFIED), Audit Records (PROPOSED, P13-ADR-006 Draft), Health Signals (EXISTING collaboration domain; endpoint technology UNSPECIFIED).

**Known Gaps / Unspecified:** metric schema, trace backend, correlation propagation contract, retention (general), sampling, storage/query, observability configuration, health endpoint technology, runtime lifecycle telemetry, deployment observability, context propagation schema, sensitive-data handling procedures.

**Conflicts Preserved:** CONFLICT-03 (auth scope v1.0 vs v2.0), GAP-SEC (confidentiality), UNRES-05, and the newly recorded `configuration.md §16` → empty `context.md` inconsistency.

**Consistency Safeguards:** No monitoring platform introduced; no metrics invented; no log fields invented; no tracing technology assumed; no health endpoints invented; no retention/sampling invented; no observability tooling specified; AI-agent invention rules enforced (§38).
