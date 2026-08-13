# Part 14: Integration Schema Catalog

**Version:** 1.0.0
**Status:** Working Draft — Integration Reference
**Date:** 2026-08-11
**Classification:** Integration Contract Reference (not authoritative architecture; derived from Parts 0–13)

---

## 0. How to Read This Catalog

This catalog documents **integration-relevant schemas, contracts, payload shapes, configuration structures, and data models** that cross architectural boundaries across AI-OS Parts 1–13. It is organized by category:

1. **Event Envelope & Metadata Schemas** — canonical wrappers carried by every cross-boundary message
2. **Domain / Internal Models** — schemas that represent state within a single subsystem and are not normally serialized across boundaries
3. **Integration Contracts** — request/response and coordination schemas exchanged between subsystems
4. **Event Payloads** — body schemas for published events
5. **API Request/Response Schemas** — surface-level contracts for externally reachable operations
6. **Configuration Schemas** — structures governing system behavior
7. **Metadata / Context Schemas** — tracing, correlation, classification, and observability carriers

### Schema Classification

Every schema entry is labeled with one of the following statuses:

| Status | Meaning |
|--------|---------|
| **EXISTING** | Defined as a schema in source Parts 1–13 (`schemas.md`, `components.md`, `events.md`, architecture specs). |
| **DERIVED** | Not published as a standalone schema in source Parts, but reconstructable from interface signatures, event payload snippets, or component contracts in Parts 1–13. |
| **UNSPECIFIED** | Referenced by name or described in prose, but no field-level definition exists in Parts 1–13. |
| **GAP** | Required by an interface/event/component contract but absent from Parts 1–13; must be published before implementation. |
| **PROPOSED** | Not referenced in Parts 1–13; suggested by cross-part analysis but not yet approved. |
| **FUTURE** | Explicitly deferred in source Parts to a named future horizon (e.g., v2.0); must not be introduced as v1.0 behavior. |
| **CONFLICT** | Two or more authoritative sources disagree on this point. Both sources must be preserved; Part 14 must not silently resolve, override, or invent a compromise. |

### Notation
- `[P12-Agent]` means “see Part 12 Agent Schema.”
- `[GAP]` marks missing definitions.
- `[DERIVED]` marks reconstructed contracts.
- `[PROPOSED]` marks suggestions not grounded in source architecture.
- `[FUTURE]` marks items deferred beyond v1.0 in source.
- `[CONFLICT]` marks disagreements between authoritative sources that must be preserved.

---

## 1. Event Envelope & Metadata Schemas

### 1.1 Part 12 Canonical Event Envelope (EXISTING)

> **Authority & Scope:** This envelope schema is canonical within the **Part 12 multi-agent collaboration event architecture** (`Part12/events.md` §4). It is **not** a universal AI-OS envelope. Part 2 defines a separate `Event`/`EventBus` transport contract with its own envelope fields (`eventId` UUIDv7, `category`, `target`, `checksum`, 5-level priority). The divergence between the two envelope specifications is cataloged in `Part14/events.md` §3.1 as **GAP-ENV** and must not be silently resolved by this catalog.

| Field | Value |
|-------|-------|
| **Schema ID** | `EVENT-ENVELOPE-v1` |
| **Name** | Part 12 Canonical Event Envelope |
| **Classification** | EXISTING |
| **Purpose** | Mandatory outer wrapper for every event emitted across the Part 12 EventBus. Provides observability, routing, schema identification, and integrity for cross-boundary messages within the Part 12 multi-agent collaboration architecture. This envelope does **not** replace or override the Part 2 `Event`/`EventBus` contract. |
| **Owner** | Part 12 — Event Architecture (`events.md` §4) |
| **Producer** | Any event-emitting actor in Part 12: Agent, Council, Workflow, Runtime, Scheduler, Tool, System |
| **Consumer(s)** | EventBus subscribers, downstream processors, audit/telemetry pipelines, Part 13 Governance Event Manager (G-14) |
| **Boundary crossed** | Producer subsystem → EventBus → subscriber subsystems |
| **Source** | `Part12/events.md` §4 (envelope example, field semantics §4 lines 224-235); `Part12/events.md` §20 (security/signing); `Part12/events.md` §29 (ordering via `partition_key`); `Part12/events.md` §30 (correlation/causation); `Part12/events.md` §31 (trace/OpenTelemetry); `Part12/schemas.md` Event Envelope section |

#### Fields / Concepts

| Field | Type | Required | Description | Source Provenance |
|-------|------|----------|-------------|-------------------|
| `event_id` | string | Yes | ULID per `01HZX5KQ…` format; globally unique; used for idempotency and dedup. | `Part12/events.md` §4 field semantics: "`event_id` — ULID, not UUID." |
| `event_type` | string | Yes | Dotted topic name, e.g. `workflow.step.completed`. | `Part12/events.md` §4 envelope example. |
| `$schema` | string | No | URI identifying the envelope schema version. | `Part12/events.md` §4 envelope example includes `"$schema": "https://ai-os.dev/schemas/event-envelope/v1.json"`. |
| `event_version` | integer | Yes | Integer envelope version within an `event_type`; distinct from `schema_ref` `<major>.<minor>` payload versioning. | `Part12/events.md` §4 envelope example shows `"event_version": 1`; §27 describes payload schema versioning separately as `<major>.<minor>`. |
| `produced_at` | string | Yes | ISO 8601 emission timestamp. | `Part12/events.md` §4 envelope example. |
| `produced_by` | object | Yes | Originating actor identity. | `Part12/events.md` §4 envelope example. |
| `produced_by.actor_id` | string | Yes | Actor identifier. | `Part12/events.md` §4 envelope example. |
| `produced_by.actor_kind` | enum | Yes | `agent` \| `council` \| `workflow` \| `runtime` \| `scheduler` \| `tool` \| `system` | `Part12/events.md` §4 envelope example. **Note:** `governance` is NOT in this enum; governance events use the emitting component's actual `actor_kind`. |
| `produced_by.actor_role` | string | Yes | Role of the actor, e.g. `executor`, `arbiter`, `planner`, `observer`. Source does not define a closed enum; roles are open strings. — `Part12/events.md` §4 envelope example. |
| `partition_key` | string | Yes | Guarantees per-aggregate ordering within a partition. | `Part12/events.md` §4 envelope example; ordering model §29. |
| `correlation_id` | string | Yes | Ties all events belonging to one user-visible action/workflow. | `Part12/events.md` §4 envelope example; §30 correlation model. |
| `causation_id` | string | Yes | Immediate parent event that caused this one; forms a DAG. | `Part12/events.md` §4 envelope example; §30 causation model. |
| `tenant_id` | string | Yes | Tenant identifier in multi-tenant deployments. | `Part12/events.md` §4 envelope example includes `"tenant_id": "ten_acme"`. |
| `priority` | enum | Yes | `P0` \| `P1` \| `P2` \| `P3` | `Part12/events.md` §4 envelope example; §29 priority lanes. **Note:** Part 2 EventBus uses a different 5-level priority model (`CRITICAL`/`HIGH`/`NORMAL`/`LOW`/`BACKGROUND`). this envelope follows the Part 12 P0–P3 model. |
| `trace` | object | No | Distributed trace identifiers, mapped to OpenTelemetry. | `Part12/events.md` §4 envelope example; §31 trace model. |
| `trace.trace_id` | string | No | Trace identifier. | `Part12/events.md` §4 / §31. |
| `trace.span_id` | string | No | Span identifier. | `Part12/events.md` §4 / §31. |
| `trace.parent_span_id` | string | No | Parent span identifier. | `Part12/events.md` §4 / §31. |
| `schema_ref` | string | Yes | Fully qualified schema reference, e.g. `workflow.step.completed@v1.2`. | `Part12/events.md` §4 envelope example; §27 shows `<major>.<minor>` format, e.g. `workflow.step.completed@v1.2`. |
| `payload` | object | Yes | Domain-specific body; structure governed by `schema_ref`. | `Part12/events.md` §4 envelope example. |
| `metadata` | object | No | Arbitrary metadata including `redacted_fields`, `classification`, `encrypted_fields`. | `Part12/events.md` §4 envelope example; §20 security classification. |
| `metadata.classification` | enum | No | `internal` \| `confidential` \| `secret` | `Part12/events.md` §20 classification model. |
| `metadata.redacted_fields` | array[string] | No | JSON pointers to fields that were redacted in `payload`. | `Part12/events.md` §20 redaction policy. |
| `metadata.encrypted_fields` | array[string] | No | JSON pointers to fields that are encrypted in `payload`. | `Part12/events.md` §20 encryption metadata. |
| `security` | object | No | Signature material for event integrity; chain verification is provided by periodic `security.audit.record` events rather than enforced per-event `previous_signature` chaining. | `Part12/events.md` §4 envelope example; §20 security model. |
| `security.signing_key_id` | string | No | Key identifier for the signing key used for this event. | `Part12/events.md` §4 / §20. |
| `security.signature` | string | No | Ed25519 signature over canonicalized envelope payload. | `Part12/events.md` §20 Ed25519 signing. |
| `security.previous_signature` | string | No | Retained prior signature material for audit continuity; periodic Merkle chain verification is emitted via `security.audit.record` events. | `Part12/events.md` §20 chain anchoring model. |

#### Required vs Optional
- **Required:** `$schema`, `event_id`, `event_type`, `event_version`, `produced_at`, `produced_by`, `partition_key`, `correlation_id`, `tenant_id`, `priority`, `schema_ref`, `payload`
- **Conditional:** `causation_id` — required for non-root events; may be `null` for root causal events. — `Part12/events.md` §30 causation model.
- **Optional:** `trace.*`, `metadata.*`, `security.*`

> **Source basis for required fields:** `Part12/events.md` §4 envelope example includes `$schema`, `event_id`, `event_type`, `event_version`, `produced_at`, `produced_by`, `partition_key`, `correlation_id`, `tenant_id`, `priority`, `schema_ref`, and `payload`. `Part12/events.md` §30 states `correlation_id` is mandatory and `causation_id` is mandatory for non-root causal events; root causal events may set it to `null`. The event catalog in `Part12/events.md` §22 assigns a `priority` to every documented event type; absence in a future type would be a schema extension.

#### Validation Rules
- `event_id` must be a valid ULID string matching the Crockford base32 format. — `Part12/events.md` §4 field semantics.
- `event_version` must be a positive integer. — `Part12/events.md` §4 envelope example; §27 versioning model.
- `produced_at` must be a valid ISO 8601 timestamp. — `Part12/events.md` §4 envelope example.
- `produced_by.actor_kind` must be one of: `agent`, `council`, `workflow`, `runtime`, `scheduler`, `tool`, `system`. — `Part12/events.md` §4 envelope example. **`governance` is NOT a valid `actor_kind`; governance components emit under their actual actor kind.**
- `produced_by.actor_role` must be a non-empty string. — `Part12/events.md` §4 envelope example; source does not define a closed enum for roles.
- `partition_key` must be stable for events belonging to the same logical workflow/entity. — `Part12/events.md` §29 ordering model.
- `correlation_id` must be a valid identifier tying events in the same causal chain. — `Part12/events.md` §30 correlation model.
- `causation_id`, when present, must reference a known prior event in the same `correlation_id` chain, or be `null` for root causal events. — `Part12/events.md` §30 causation model.
- `priority` must be one of: `P0`, `P1`, `P2`, `P3`. — `Part12/events.md` §4 / §29 priority lanes.
- `schema_ref` must resolve to a registered schema in the Schema Registry in the format `<event_type>@v<major>.<minor>`. — `Part12/events.md` §4 / §27 schema registry reference format.
- `payload` must validate against the schema identified by `schema_ref`. — `Part12/events.md` §27 schema validation rule.
- `metadata.classification`, when present, must be one of: `internal`, `confidential`, `secret`. — `Part12/events.md` §20 classification model.
- `metadata.redacted_fields` and `metadata.encrypted_fields` entries must be valid JSON pointers or field names. — `Part12/events.md` §20 redaction/encryption metadata.
- `security.signature` must verify against `signing_key_id` when present. — `Part12/events.md` §20 Ed25519 signing model.
- `security.previous_signature`, when present, retains prior signature material for audit continuity; periodic Merkle chain verification is emitted via `security.audit.record` events rather than enforced per event. — `Part12/events.md` §20 chain anchoring model.

#### Invariants
- **INV-ENV-001:** Every event crossing a subsystem boundary MUST carry a valid envelope. — `Part12/events.md` §4; Part 0 Principle 1.
- **INV-ENV-002:** Events MUST be immutable after publication. — `Part12/events.md` §4; Part 0 Principle 8; ADR-008.
- **INV-ENV-003:** `causation_id`, when present, MUST reference an existing event in the same `correlation_id` chain; root causal events MUST set it to `null`. — `Part12/events.md` §30.
- **INV-ENV-004:** `security.signature` MUST be present for events at `confidential` or `secret` classification. — `Part12/events.md` §20 signing policy.

#### Version
This section distinguishes three distinct version concepts used across the AI-OS event system.

##### Envelope Schema Version (`$schema` URI)
Identifies the version of the envelope structure itself, expressed as a URI such as `https://ai-os.dev/schemas/event-envelope/v1.json`. This value is set in the `$schema` field and is used by consumers to determine which envelope-level contract applies to a given event. **Source:** `Part12/events.md` §4 envelope example.

##### Envelope Event Version (`event_version` field)
An integer carried in the `event_version` field representing the envelope's own evolution. Distinct from payload schema versioning. **Source:** `Part12/events.md` §4 envelope example uses `"event_version": 1` as an integer.

##### Payload Schema Reference Version (`schema_ref`)
The version of the specific event payload schema, expressed in `<major>.<minor>` format within the `schema_ref` field (e.g., `workflow.step.completed@v1.2`). Managed under Semantic Versioning 2.0.0 as defined in `Part12/events.md` §27. Consumers pin major versions; minor and patch versions are additive within a major version. **Source:** `Part12/events.md` §27.

##### This Envelope Schema's Version
- **`1.0.0` (derived):** Initial envelope schema reconstructed from the authoritative envelope example in `Part12/events.md` §4.

##### Explicit Version Terminology
This catalog uses the following distinct terms. They are not interchangeable.

| Term | Meaning | Example |
|------|---------|---------|
| **event_version** | Integer carried in the `event_version` envelope field; evolves the envelope contract for a given `event_type`. | `"event_version": 2` |
| **schema_version / `schema_ref` version** | `<major>.<minor>` payload schema version referenced by `schema_ref`; governed by Semantic Versioning 2.0.0. | `workflow.step.completed@v1.2` |
| **`$schema` URI version** | Version of the envelope structure itself, expressed as a URI. | `https://ai-os.dev/schemas/event-envelope/v1.json` |
| **implementation_version** | Version of the producing/consuming runtime component; not carried in the envelope. | `EventBus 1.4.0` |

- **Source basis for terminology:** `Part12/events.md` §4 (`event_version` integer, `schema_ref` format); `Part12/events.md` §27 (SemVer for payload schemas); `Part12/schemas.md` schema governance model; `Part14/context.md` version-distinction rule.

#### Compatibility
This section distinguishes four compatibility domains. A change may be compatible in one domain and incompatible in another.

##### Schema Compatibility
- Backward: older consumers ignore unknown envelope fields. — `Part12/events.md` §27 backward-compatible additions rule.
- Forward: producers MUST NOT remove envelope fields; only additive changes permitted without envelope version bump. — `Part12/events.md` §27 forward compatibility rule.
- Payload schema compatibility is governed by `Part12/events.md` §27 and `Part12/schemas.md` §§17-21 (SemVer, breaking/non-breaking change policy).

##### Event Compatibility
- At-least-once delivery is the default for Part 12 events; at-most-once is a configured option, not the default. — `Part12/events.md` §18; `Part14/events.md` §3.4.
- Exactly-once delivery does not exist in Parts 0–13; application-layer idempotency is the only exactly-once mechanism. — `Part14/events.md` §3.4; `Part14/events.md` §3.15 guarantee audit.
- Replay is a Part 12 primitive for dotted events via WORM log; it is not defined for the Part 2 EventBus enum. — `Part12/events.md` §16.10, §18–§19, §29; `Part14/events.md` §3.13.

##### API Compatibility
- Envelope field contracts are additive within a major `$schema` version; removal or retype requires a new `$schema` URI. — `Part12/events.md` §27.
- Consumers pin payload schema major versions in `schema_ref`; minor/patch versions are additive within a major version. — `Part12/events.md` §27.

##### Implementation Compatibility
- Source does not define implementation compatibility guarantees for the envelope. Compatibility claims about specific runtime behaviors, serializer versions, or transport bindings are UNSPECIFIED unless stated in the consuming implementation's own documentation.

#### Evolution Rules
- New optional envelope fields may be added in MINOR. — `Part12/events.md` §27.
- Envelope structural changes require MAJOR and a new `$schema` URI.
- `event_type` namespace is governed by Part 12/13 registries; new types require registration. — `Part12/events.md` §25 registry model.
- Payload schema changes follow `Part12/schemas.md` §20 (Breaking Change Policy) and §21 (Non-Breaking Change Policy).

#### Related Interfaces
- Part 2 EventBus publish/subscribe APIs (`INT-EVT-BUS-001`)
- G-14 Governance Event Manager `emit(event)` / `getEventStream(filter)`

#### Related Events
- Every event emitted in the Part 12 multi-agent collaboration system uses this envelope.

#### Related Components
- EventBus, all Producers/Consumers, G-14 Governance Event Manager

#### Related ADRs
- Part 12 event architecture (`P12-ADR-001` Event-First Collaboration, `P12-ADR-008` Zero-Trust Security)
- Part 0 Principle 1 (Event-First Communication), Principle 8 (Immutable Events with Correlation & Causation)

#### Cross-Part Notes
- Part 2 EventBus defines a separate base `Event` contract (`eventId` UUIDv7, `category`, `target`, `checksum`, 5-level priority). This envelope follows the Part 12 integration envelope. The divergence is cataloged in `Part14/events.md` §3.1 as **GAP-ENV**.
- Governance events (`governance.*`, Part 13) also use this envelope via G-14. Part 13 §7 requires Security-domain co-signature for major version bumps to governance event schemas.

---

### 1.2 Trace Context (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-TraceContext` |
| **Name** | Trace Context |
| **Classification** | EXISTING |
| **Purpose** | Distributed trace identifiers attached to events and messages, mapped to OpenTelemetry. |
| **Owner** | Part 12 — Event Architecture (`events.md` §31) |
| **Producer** | Any event-producing actor |
| **Consumer(s)** | ObservabilityManager, audit pipelines, debugging tools |
| **Boundary crossed** | Embedded in every event/message envelope |
| **Source** | `Part12/events.md` §31 |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_id` | string | No | Trace identifier. |
| `span_id` | string | No | Span identifier. |
| `parent_span_id` | string | No | Parent span identifier. |

#### Required vs Optional
- All fields are optional in the sense that events without distributed tracing still validate; however, any event that participates in a trace MUST populate all three.

#### Validation Rules
- All three fields must be non-empty strings when present. — `Part12/events.md` §31 trace model.

#### Source Provenance
- Field definitions: `Part12/events.md` §4 envelope example (`trace` block) and §31 (trace/OpenTelemetry mapping).

#### Invariants
- **INV-TRC-001:** Within a single trace, `span_id` values MUST be unique. — `Part12/events.md` §31.

#### Version
- `1.0.0` (implicit from envelope version): Trace context structure is defined inline in the envelope; no standalone trace schema version exists in source. Catalog assigns `1.0.0` by reference to the envelope version.
  - **Source basis:** `Part12/events.md` §4 envelope example includes a `trace` block; §31 maps it to OpenTelemetry. No separate trace schema version document is provided.

#### Compatibility
- Additive: events without trace context are still valid.

#### Evolution Rules
- Stable; no breaking changes expected.

#### Related Interfaces
- Event envelope `trace` block

#### Related Events
- All events carrying trace context

#### Related Components
- ObservabilityManager, EventBus

#### Related ADRs
- Part 12 observability model

---

### 1.3 Classification Metadata (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-ClassificationMetadata` |
| **Name** | Classification Metadata |
| **Classification** | EXISTING |
| **Purpose** | Security classification and redaction metadata attached to events and payloads. |
| **Owner** | Part 12 — Event Architecture (`events.md` §2, §20) |
| **Producer** | Event producers, SecurityManager |
| **Consumer(s)** | EventBus, audit pipelines, downstream handlers |
| **Boundary crossed** | Embedded in every event envelope |
| **Source** | `Part12/events.md` §2, §20 |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `classification` | enum | No | `internal` \| `confidential` \| `secret` |
| `redacted_fields` | array[string] | No | Fields that were redacted in the payload. |
| `encrypted_fields` | array[string] | No | Fields that are encrypted in the payload. |

#### Required vs Optional
- All fields optional; absence implies default classification per environment policy.

#### Validation Rules
- `classification`, when present, must be one of: `internal`, `confidential`, `secret`. — `Part12/events.md` §20 classification model.
- `redacted_fields` and `encrypted_fields` entries must be valid JSON pointers or field names identifying fields in `payload`. — `Part12/events.md` §20 redaction/encryption metadata.

#### Source Provenance
- Field definitions: `Part12/events.md` §4 envelope example (`metadata` block) and §20 (security classification, redaction, encryption).

#### Invariants
- **INV-CLS-001:** Encrypted fields MUST NOT appear in plaintext in `payload`. — `Part12/events.md` §20 encryption policy.
- **INV-CLS-002:** Redacted fields MUST be replaced with a redaction marker in `payload`. — `Part12/events.md` §20 redaction policy.

#### Version
- `1.0.0` (implicit from envelope version): Classification metadata fields are defined inline in the envelope; no standalone classification metadata schema version exists in source. Catalog assigns `1.0.0` by reference to the envelope version.
  - **Source basis:** `Part12/events.md` §4 envelope example includes `metadata.classification`; §20 defines classification model and redaction/encryption metadata. No separate metadata schema version document is provided.

#### Compatibility
- Additive classification levels are non-breaking if consumers treat unknown levels as most-restrictive.

#### Evolution Rules
- MINOR: add new classification levels.
- MAJOR: change classification semantics.

#### Related Interfaces
- Event envelope `metadata` and `security` blocks

#### Related Events
- All events carrying classification metadata

#### Related Components
- SecurityManager, G-14 Governance Event Manager

#### Related ADRs
- Part 12 security model; Part 13 data classification model

---

## 2. Domain / Internal Models

> These models represent state within a single subsystem. They are documented here because they are referenced by integration contracts or because their persistence/serialization shape crosses storage boundaries.

### 2.1 Agent Descriptor (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Agent` |
| **Name** | Agent Descriptor |
| **Classification** | EXISTING |
| **Purpose** | Represents an agent identity, capabilities, status, and metadata for registration, discovery, and capability advertisement. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Agent Schema) |
| **Producer** | AgentManager, agents themselves during registration |
| **Consumer(s)** | ServiceRegistry, discovery queries, Council composition, governance registry |
| **Boundary crossed** | Agent runtime ↔ ServiceRegistry/Discovery; agent ↔ governance registry |
| **Source** | `Part12/schemas.md` Agent Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agentId` | UUID | Yes | Unique agent identifier. |
| `name` | string | Yes | Human-readable agent name. |
| `version` | SemVer | Yes | Agent implementation version. |
| `description` | string | No | Agent purpose/functionality. |
| `capabilities` | array[CapabilityDescriptor] | Yes | Advertised capabilities. |
| `endpoints` | object | No | Communication endpoints. |
| `status` | enum | Yes | `active` \| `inactive` \| `maintenance` \| `error` |
| `metadata` | object | No | Arbitrary metadata. |
| `tags` | array[string] | No | Discovery/categorization tags. |
| `createdAt` | ISO 8601 | Yes | Registration timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `agentId`, `name`, `version`, `capabilities`, `status`, `createdAt`, `updatedAt`
- **Optional:** `description`, `endpoints`, `metadata`, `tags`

#### Validation Rules
- `agentId` matches UUID v4 pattern.
- `version` matches SemVer pattern.
- `status` must be one of defined enum values.
- `updatedAt >= createdAt`.
- Each `capabilities[*]` must conform to CapabilityDescriptor schema.

#### Source Provenance
- `agentId` UUID v4: `Part12/schemas.md` Agent Schema section.
- `version` SemVer: `Part12/schemas.md` Agent Schema section; Part 12 schema governance §20.
- `status` enum: `Part12/schemas.md` Agent Schema section (`active` \| `inactive` \| `maintenance` \| `error`).
- `updatedAt >= createdAt`: `Part12/schemas.md` Agent Schema invariant; common timestamp ordering rule.
- CapabilityDescriptor conformance: `Part12/schemas.md` Capability Schema section.

#### Invariants
- **INV-AGT-001:** An agent MUST NOT register with an empty `capabilities` array.
- **INV-AGT-002:** Status transitions must be reflected in `updatedAt`.

#### Version
- Instance versioned by agent implementation; schema version governed by Part 12 schema governance.

#### Compatibility
- Backward: new optional fields added in MINOR.
- Forward: consumers ignore unknown fields.

#### Evolution Rules
- Add optional fields in MINOR.
- Making optional fields required or removing fields requires MAJOR.
- Deprecated fields follow 6-month deprecation lifecycle per Part 12 schema governance.

#### Related Interfaces
- Agent registration/discovery APIs
- Capability advertisement interfaces

#### Related Events
- `agent.lifecycle.registered`, `agent.lifecycle.deregistered`, `agent.lifecycle.heartbeat`

#### Related Components
- AgentManager (Part 1), ServiceRegistry (Part 1), GovernanceRegistry G-03 (Part 13)

#### Related ADRs
- P12-ADR-002 (discovery), P12-ADR capability advertisement model

---

### 2.2 Capability Descriptor (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Capability` |
| **Name** | Capability Descriptor |
| **Classification** | EXISTING |
| **Purpose** | Describes a specific capability an agent or tool provides, including input/output contract. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Capability Schema) |
| **Producer** | Agent, Tool, Plugin |
| **Consumer(s)** | Workflow planner, Council, governance evaluator, capability router |
| **Boundary crossed** | Provider runtime → consumer discovery/planning |
| **Source** | `Part12/schemas.md` Capability Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `capabilityId` | string | Yes | Unique capability identifier. |
| `name` | string | Yes | Human-readable capability name. |
| `version` | SemVer | Yes | Capability version. |
| `description` | string | No | Capability description. |
| `inputSchema` | object \| null | No | JSON Schema for capability input. |
| `outputSchema` | object \| null | No | JSON Schema for capability output. |
| `parameters` | object | No | Default/additional parameters (open schema). |

#### Required vs Optional
- **Required:** `capabilityId`, `name`, `version`
- **Optional:** `description`, `inputSchema`, `outputSchema`, `parameters`

#### Validation Rules
- `capabilityId` must be non-empty string.
- `version` must match SemVer pattern.
- `inputSchema` and `outputSchema`, when present, must be valid JSON Schema objects.

#### Source Provenance
- `capabilityId` non-empty string: `Part12/schemas.md` Capability Schema section.
- `version` SemVer: `Part12/schemas.md` Capability Schema section.
- `inputSchema`/`outputSchema` JSON Schema validation: `Part12/schemas.md` Capability Schema `inputSchema`/`outputSchema` fields.

#### Invariants
- **INV-CAP-001:** A capability MUST declare its input/output contract if it is invoked programmatically.

#### Version
- SemVer per capability.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) applies SemVer to capability versioning.

#### Compatibility
- Additive changes to `parameters` are non-breaking.
- Changes to `inputSchema`/`outputSchema` structure are breaking if consumers validate against them.

#### Evolution Rules
- New optional parameters in MINOR.
- Input/output schema changes require MAJOR unless backward-compatible.

#### Related Interfaces
- Capability discovery APIs
- Workflow step binding

#### Related Events
- `capability.advertised`, `capability.updated`

#### Related Components
- AgentManager, ToolManager, WorkflowManager

#### Related ADRs
- P12-ADR capability model

---

### 2.3 Workflow Descriptor (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Workflow` |
| **Name** | Workflow Descriptor |
| **Classification** | EXISTING |
| **Purpose** | Defines a collaborative workflow including steps, agents, councils, and execution policy. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Workflow Schema) |
| **Producer** | Planning service, workflow authoring tools |
| **Consumer(s)** | WorkflowManager, Runtime, Scheduler, governance evaluator |
| **Boundary crossed** | Authoring → execution runtime; planning → governance |
| **Source** | `Part12/schemas.md` Workflow Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflowId` | UUID | Yes | Unique workflow identifier. |
| `name` | string | Yes | Workflow name. |
| `version` | SemVer | Yes | Workflow definition version. |
| `description` | string | No | Workflow description. |
| `steps` | array[WorkflowStep] | Yes | Ordered execution steps. |
| `agents` | array[AgentReference] | No | Agents participating in this workflow. |
| `councils` | array[CouncilReference] | No | Councils involved. |
| `executionPolicy` | object | No | Retry, timeout, parallelization policy. |
| `status` | enum | Yes | `draft` \| `active` \| `paused` \| `completed` \| `failed` \| `cancelled` |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `workflowId`, `name`, `version`, `steps`, `status`, `createdAt`, `updatedAt`
- **Optional:** `description`, `agents`, `councils`, `executionPolicy`

#### Validation Rules
- `workflowId` must be UUID v4.
- `steps` must be non-empty array.
- Step IDs within `steps` must be unique.
- `executionPolicy` when present must define valid timeout/retry constraints.

#### Source Provenance
- `workflowId` UUID v4: `Part12/schemas.md` Workflow Schema section.
- `steps` non-empty array: `Part12/schemas.md` Workflow Schema section.
- Step ID uniqueness: `Part12/schemas.md` Workflow Schema `steps` field definition.
- `executionPolicy` constraints: `Part12/schemas.md` Workflow Schema `executionPolicy` field definition.

#### Invariants
- **INV-WF-001:** A workflow MUST have at least one step.
- **INV-WF-002:** Referenced `agents` and `councils` must exist in the registry at activation time.

#### Version
- SemVer per workflow definition.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) applies SemVer to workflow versioning.

#### Compatibility
- Adding steps is breaking for existing execution plans unless execution plan is regenerated.
- Adding optional metadata is non-breaking.

#### Evolution Rules
- Structural changes to steps require MAJOR.
- Additive metadata changes allowed in MINOR.

#### Related Interfaces
- WorkflowManager create/update/activate APIs

#### Related Events
- `workflow.lifecycle.started`, `workflow.lifecycle.completed`, `workflow.step.scheduled`, `workflow.step.started`, `workflow.step.completed`

#### Related Components
- WorkflowManager, Scheduler, Runtime, CouncilService

#### Related ADRs
- P12-ADR workflow execution model

---

### 2.4 Task Descriptor (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Task` |
| **Name** | Task Descriptor |
| **Classification** | EXISTING |
| **Purpose** | Represents a unit of work assigned to an agent within a workflow or independently. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Task Schema) |
| **Producer** | WorkflowManager, Planning service |
| **Consumer(s)** | AgentManager, RetryManager, CheckpointManager, Scheduler |
| **Boundary crossed** | Workflow planner → executor agent; workflow → retry/checkpoint subsystems |
| **Source** | `Part12/schemas.md` Task Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `taskId` | UUID | Yes | Unique task identifier. |
| `workflowId` | UUID \| null | No | Parent workflow identifier. |
| `name` | string | Yes | Task name. |
| `description` | string | No | Task description. |
| `assignedAgentId` | UUID \| null | No | Agent assigned to execute the task. |
| `input` | object | No | Task input payload. |
| `expectedOutput` | object \| null | No | Expected output schema hint. |
| `status` | enum | Yes | `pending` \| `assigned` \| `running` \| `completed` \| `failed` \| `retrying` \| `cancelled` |
| `priority` | enum | No | `P0` \| `P1` \| `P2` \| `P3` |
| `retryBudget` | object | No | Retry constraints. |
| `checkpointPolicy` | object | No | Checkpoint frequency/policy. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `taskId`, `name`, `status`, `createdAt`, `updatedAt`
- **Optional:** `workflowId`, `description`, `assignedAgentId`, `input`, `expectedOutput`, `priority`, `retryBudget`, `checkpointPolicy`

#### Validation Rules
- `taskId` must be UUID v4.
- `workflowId` when present must be UUID v4.
- `assignedAgentId` when present must be UUID v4.
- `status` must be one of defined enum values.

#### Source Provenance
- `taskId` UUID v4: `Part12/schemas.md` Task Schema section.
- `workflowId` UUID v4 when present: `Part12/schemas.md` Task Schema section.
- `assignedAgentId` UUID v4 when present: `Part12/schemas.md` Task Schema section.
- `status` enum: `Part12/schemas.md` Task Schema section.

#### Invariants
- **INV-TASK-001:** A task MUST have a non-empty `name`.
- **INV-TASK-002:** `updatedAt >= createdAt`.

#### Version
- SemVer per task template; runtime task instances inherit template version.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) applies SemVer to task template versioning.

#### Compatibility
- Non-structural additions are non-breaking.
- Changing `status` enum is breaking.

#### Evolution Rules
- New optional statuses/fields in MINOR.
- Required field additions or removals in MAJOR.

#### Related Interfaces
- Task creation/update APIs
- Retry/checkpoint manager APIs

#### Related Events
- `task.created`, `task.assigned`, `task.completed`, `task.failed`, `task.retrying`

#### Related Components
- WorkflowManager, AgentManager, RetryManager, CheckpointManager

#### Related ADRs
- P12-ADR task lifecycle

---

### 2.5 Council Descriptor (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Council` |
| **Name** | Council Descriptor |
| **Classification** | EXISTING |
| **Purpose** | Represents a governance/decision council including member agents, charter, and quorum rules. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Council Schema) |
| **Producer** | Council service, governance components |
| **Consumer(s)** | Workflow engine, governance evaluator, Decision Authority Manager (G-05) |
| **Boundary crossed** | Governance configuration → execution runtime |
| **Source** | `Part12/schemas.md` Council Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `councilId` | UUID | Yes | Unique council identifier. |
| `name` | string | Yes | Council name. |
| `version` | SemVer | Yes | Council definition version. |
| `description` | string | No | Council description. |
| `charter` | object | No | Governance charter/rules. |
| `memberIds` | array[UUID] | Yes | Agent IDs that are council members. |
| `quorum` | integer | Yes | Minimum members required for valid deliberation. |
| `consensusAlgorithm` | enum | Yes | Consensus algorithm. |
| `status` | enum | Yes | `active` \| `inactive` \| `dissolved` |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `councilId`, `name`, `version`, `memberIds`, `quorum`, `consensusAlgorithm`, `status`, `createdAt`, `updatedAt`
- **Optional:** `description`, `charter`

#### Validation Rules
- `councilId` must be UUID v4.
- `memberIds` entries must be valid UUIDs.
- `quorum` must be positive integer <= `memberIds.length`.
- `consensusAlgorithm` must be one of: `MAJORITY`, `UNANIMOUS`, `WEIGHTED`, `RANKED_CHOICE`, `CONSENT`.

#### Source Provenance
- `councilId` UUID v4: `Part12/schemas.md` Council Schema section.
- `memberIds` UUID entries: `Part12/schemas.md` Council Schema section.
- `quorum` constraint: `Part12/schemas.md` Council Schema `quorum` field definition.
- `consensusAlgorithm` enum values: `Part12/schemas.md` Council Schema `consensusAlgorithm` field definition.

#### Invariants
- **INV-COUNCIL-001:** `quorum <= len(memberIds)`.
- **INV-COUNCIL-002:** A council MUST have at least one member.

#### Version
- SemVer per council definition.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) applies SemVer to council definition versioning.

#### Compatibility
- Additive member/charter changes are non-breaking.
- Changing quorum or consensus algorithm is breaking for in-flight deliberations.

#### Evolution Rules
- MINOR: add optional metadata, new optional algorithms.
- MAJOR: change required fields, remove algorithms.

#### Related Interfaces
- Council registration APIs
- Voting APIs

#### Related Events
- `council.lifecycle.convened`, `council.lifecycle.dissolved`, `council.decision.published`

#### Related Components
- G-04 Governance Council, CouncilService, WorkflowManager

#### Related ADRs
- P12-ADR council model; P13-ADR council governance integration

---

### 2.6 Vote Record (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Vote` |
| **Name** | Vote Record |
| **Classification** | EXISTING |
| **Purpose** | Records an individual agent's vote within a council deliberation. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Vote Schema) |
| **Producer** | Agent acting as council member |
| **Consumer(s)** | Council tally engine, governance audit trail |
| **Boundary crossed** | Member agent → council aggregation; council → governance audit |
| **Source** | `Part12/schemas.md` Vote Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `voteId` | UUID | Yes | Unique vote identifier. |
| `councilId` | UUID | Yes | Council receiving the vote. |
| `decisionId` | UUID \| null | No | Associated decision identifier. |
| `agentId` | UUID | Yes | Voting agent identifier. |
| `vote` | enum | Yes | `approve` \| `reject` \| `abstain` \| `delegate` |
| `reasoning` | string | No | Justification for vote. |
| `weight` | number | No | Vote weight for weighted algorithms. |
| `castAt` | ISO 8601 | Yes | Vote timestamp. |

#### Required vs Optional
- **Required:** `voteId`, `councilId`, `agentId`, `vote`, `castAt`
- **Optional:** `decisionId`, `reasoning`, `weight`

#### Validation Rules
- `voteId`, `councilId`, `agentId` must be valid UUIDs.
- `vote` must be one of defined enum values.
- `weight` when present must be non-negative number.

#### Source Provenance
- `voteId`, `councilId`, `agentId` UUID v4: `Part12/schemas.md` Vote Schema section.
- `vote` enum: `Part12/schemas.md` Vote Schema section.
- `weight` non-negative number: `Part12/schemas.md` Vote Schema section.

#### Invariants
- **INV-VOTE-001:** An agent MUST NOT vote more than once per council deliberation per `decisionId`.

#### Version
- Stable; schema changes require MAJOR.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) governs vote schema changes.

#### Compatibility
- Backward: ignore unknown fields.
- Forward: no removal of existing fields.

#### Evolution Rules
- Add optional fields in MINOR.
- Structural changes in MAJOR.

#### Related Interfaces
- Vote casting APIs
- Tally APIs

#### Related Events
- `council.vote.cast`

#### Related Components
- G-04 Governance Council, CouncilService

#### Related ADRs
- P12-ADR voting model

---

### 2.7 Shared Context (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-SharedContext` |
| **Name** | Shared Context |
| **Classification** | EXISTING |
| **Purpose** | Carries read/write shared state between collaborating agents within a workflow or council. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Shared Context Schema) |
| **Producer** | Any participating agent or workflow step |
| **Consumer(s)** | Downstream agents, workflow steps, governance audit |
| **Boundary crossed** | Between collaborating agents/steps |
| **Source** | `Part12/schemas.md` Shared Context Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contextId` | UUID | Yes | Unique shared context identifier. |
| `correlationId` | UUID | Yes | Parent workflow correlation identifier. |
| `ownerAgentId` | UUID | Yes | Agent with write authority. |
| `readers` | array[UUID] | Yes | Agents with read access. |
| `writers` | array[UUID] | No | Agents with write access. |
| `state` | object | Yes | Current shared state. |
| `version` | integer | Yes | Monotonic context version. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `contextId`, `correlationId`, `ownerAgentId`, `readers`, `state`, `version`, `createdAt`, `updatedAt`
- **Optional:** `writers`

#### Validation Rules
- `contextId`, `correlationId`, `ownerAgentId`, `readers[*]` must be valid UUIDs.
- `version` must be a positive integer.
- `state` must be valid JSON object.

#### Source Provenance
- `contextId`, `correlationId`, `ownerAgentId` UUID v4: `Part12/schemas.md` Shared Context Schema section.
- `readers[*]` UUID entries: `Part12/schemas.md` Shared Context Schema section.
- `version` positive integer: `Part12/schemas.md` Shared Context Schema section.
- `state` valid JSON object: `Part12/schemas.md` Shared Context Schema section.

#### Invariants
- **INV-CTX-001:** `ownerAgentId` MUST be in `readers`.
- **INV-CTX-002:** Context version MUST be monotonically increasing.

#### Version
- Versioned per usage; structure versioning follows Part 12 schema governance.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) governs Shared Context schema versioning.

#### Compatibility
- Additive state changes are non-breaking if consumers tolerate unknown keys.

#### Evolution Rules
- MINOR: add optional keys to `state`.
- MAJOR: change required keys or access-control model.

#### Related Interfaces
- Shared context read/write APIs

#### Related Events
- `context.lifecycle.snapshot`

#### Related Components
- ContextManager, AgentManager, WorkflowManager

#### Related ADRs
- P12-ADR shared state model

---

### 2.8 Knowledge Object (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-KnowledgeObject` |
| **Name** | Knowledge Object |
| **Classification** | EXISTING |
| **Purpose** | Represents a retrievable unit of knowledge with provenance, embeddings, and access policy. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Knowledge Object Schema) |
| **Producer** | Knowledge ingestion services, agents |
| **Consumer(s)** | Memory service, retrieval-augmented workflows, governance audit |
| **Boundary crossed** | Ingestion → retrieval; producer → knowledge store |
| **Source** | `Part12/schemas.md` Knowledge Object Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `knowledgeId` | UUID | Yes | Unique knowledge object identifier. |
| `title` | string | Yes | Knowledge title. |
| `content` | object | Yes | Knowledge content. |
| `embedding` | array[number] \| null | No | Vector embedding. |
| `provenance` | object | No | Source/traceability metadata. |
| `accessPolicy` | object | No | Access control metadata. |
| `classification` | enum | Yes | `public` \| `internal` \| `confidential` \| `restricted` |
| `version` | SemVer | Yes | Knowledge object version. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `knowledgeId`, `title`, `content`, `classification`, `version`, `createdAt`, `updatedAt`
- **Optional:** `embedding`, `provenance`, `accessPolicy`

#### Validation Rules
- `knowledgeId` must be UUID v4.
- `classification` must be one of defined enum values.
- `content` must be valid JSON object.

#### Source Provenance
- `knowledgeId` UUID v4: `Part12/schemas.md` Knowledge Object Schema section.
- `classification` enum: `Part12/schemas.md` Knowledge Object Schema section.
- `content` valid JSON object: `Part12/schemas.md` Knowledge Object Schema section.

#### Invariants
- **INV-KNO-001:** Classification MUST NOT be weaker than the source data classification.
- **INV-KNO-002:** `updatedAt >= createdAt`.

#### Version
- SemVer per object.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) applies SemVer to knowledge object versioning.

#### Compatibility
- Additive metadata fields are non-breaking.
- Content schema changes may break retrieval consumers.

#### Evolution Rules
- MINOR: add optional metadata.
- MAJOR: change content schema or classification model.

#### Related Interfaces
- Knowledge store APIs
- Retrieval APIs

#### Related Events
- `knowledge.ingested`, `knowledge.updated`, `knowledge.accessed`, `knowledge.retired`

#### Related Components
- MemoryManager, Knowledge/Graphify memory types, GovernanceRegistry G-03

#### Related ADRs
- P12-ADR knowledge model

---

### 2.9 Memory Object (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-MemoryObject` |
| **Name** | Memory Object |
| **Classification** | EXISTING |
| **Purpose** | Represents an entry in an agent/system memory store with type, retention policy, and content. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Memory Object Schema) |
| **Producer** | MemoryManager, agents, learning services |
| **Consumer(s)** | Context assembly, workflow planning, governance audit |
| **Boundary crossed** | Memory store → context assembly; learning service → memory store |
| **Source** | `Part12/schemas.md` Memory Object Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `memoryId` | UUID | Yes | Unique memory object identifier. |
| `memoryType` | enum | Yes | `WORKING` \| `CLAUDE` \| `ENGINEERING` \| `OBSIDIAN` \| `GRAPHIFY` |
| `content` | object | Yes | Memory content. |
| `agentId` | UUID \| null | No | Owner agent identifier. |
| `workflowId` | UUID \| null | No | Associated workflow identifier. |
| `tags` | array[string] | No | Tags. |
| `retentionPolicy` | object | No | TTL/retention rules. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `expiresAt` | ISO 8601 \| null | No | Expiration timestamp. |

#### Required vs Optional
- **Required:** `memoryId`, `memoryType`, `content`, `createdAt`
- **Optional:** `agentId`, `workflowId`, `tags`, `retentionPolicy`, `expiresAt`

#### Validation Rules
- `memoryId` must be UUID v4.
- `memoryType` must be one of defined MemoryType enum values.
- `content` must be valid JSON object.

#### Source Provenance
- `memoryId` UUID v4: `Part12/schemas.md` Memory Object Schema section.
- `memoryType` enum values: `Part12/schemas.md` Memory Object Schema section.
- `content` valid JSON object: `Part12/schemas.md` Memory Object Schema section.

#### Invariants
- **INV-MEM-001:** `WORKING` memory MUST expire or be explicitly cleared before context overflow.

#### Version
- Stable; structure changes require MAJOR.
- Source provenance: Part 12 schema governance model (`Part12/schemas.md` §20) governs Memory Object schema versioning.

#### Compatibility
- Backward: ignore unknown fields.
- Forward: do not remove fields without deprecation.

#### Evolution Rules
- MINOR: add optional tags/metadata.
- MAJOR: change type enum or content structure.

#### Related Interfaces
- Memory store read/write APIs
- Context assembly APIs

#### Related Events
- `memory.stored`, `memory.accessed`, `memory.expired`, `memory.decayed`

#### Related Components
- MemoryManager, ContextManager, Learning services

#### Related ADRs
- P12-ADR memory model

---

### 2.10 Governance Risk (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-Risk` |
| **Name** | Governance Risk |
| **Classification** | EXISTING |
| **Purpose** | Represents a risk identified within the governance system including category, source, likelihood, impact, and treatment state. |
| **Owner** | Part 13 — Governance Tier (`schemas.md` §Risk Schema) |
| **Producer** | G-07 Risk Manager, risk identification workflows |
| **Consumer(s)** | G-07 Risk Manager, G-15 Conformance Manager, governance audit, council deliberation |
| **Boundary crossed** | Risk identification → risk management → conformance evaluation |
| **Source** | `Part13/schemas.md` Risk Schema section; `Part13/components.md` G-07 |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `riskId` | UUID | Yes | Unique risk identifier. |
| `name` | string | Yes | Risk name. |
| `version` | SemVer | Yes | Risk record version. |
| `description` | string | No | Risk description. |
| `riskCategory` | enum | Yes | `strategic` \| `operational` \| `financial` \| `compliance` \| `reputational` \| `security` |
| `riskSource` | enum | Yes | `internal` \| `external` \| `threat` \| `vulnerability` |
| `likelihood` | enum | Yes | `rare` \| `unlikely` \| `possible` \| `likely` \| `almost_certain` |
| `impact` | enum | Yes | `insignificant` \| `minor` \| `moderate` \| `major` \| `catastrophic` |
| `riskRating` | enum | Yes | `low` \| `medium` \| `high` \| `extreme` |
| `status` | enum | Yes | `identified` \| `assessed` \| `treated` \| `closed` \| `reopened` |
| `ownerId` | string | Yes | Owner identifier. |
| `ownerType` | string | Yes | Owner type. |
| `effectiveFrom` | ISO 8601 | Yes | Effective start timestamp. |
| `effectiveUntil` | ISO 8601 \| null | No | Effective end timestamp. |
| `createdBy` | string | Yes | Creator identifier. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |

#### Required vs Optional
- **Required:** `riskId`, `name`, `version`, `riskCategory`, `riskSource`, `likelihood`, `impact`, `riskRating`, `status`, `ownerId`, `ownerType`, `effectiveFrom`, `createdBy`, `createdAt`, `updatedAt`
- **Optional:** `description`, `effectiveUntil`

#### Validation Rules
- `riskId` must be UUID v4.
- `version` must match SemVer.
- `effectiveUntil` when present must be > `effectiveFrom`.
- `updatedAt >= createdAt`.

#### Source Provenance
- `riskId` UUID v4: `Part13/schemas.md` Risk Schema section.
- `version` SemVer: `Part13/schemas.md` Risk Schema section.
- `effectiveUntil` ordering: `Part13/schemas.md` Risk Schema section.
- `updatedAt >= createdAt`: `Part13/schemas.md` Risk Schema invariant; common timestamp ordering rule.

#### Invariants
- **INV-RISK-001:** `riskRating` MUST be consistent with `likelihood` × `impact` matrix defined in P13 governance rules.
- **INV-RISK-002:** Risk MUST NOT be closed while open treatments exist.

#### Version
- SemVer per risk record.
- Source provenance: `Part13/schemas.md` Risk Schema section; Part 13 federated schema governance applies SemVer.

#### Compatibility
- Additive metadata fields are non-breaking.
- Changing status enum or rating semantics is breaking.

#### Evolution Rules
- MINOR: add optional metadata or new enum values.
- MAJOR: change required fields or rating semantics.

#### Related Interfaces
- G-07 Risk Manager APIs: `submitRisk`, `submitTreatment`, `queryAppetite`

#### Related Events
- `risk.identified`, `risk.assessed`, `treatment.proposed`, `treatment.approved`, `risk.closed`, `risk.reopened`

#### Related Components
- G-07 Risk Manager, G-15 Conformance Manager, G-08 Compliance Manager

#### Related ADRs
- P13-ADR risk appetite model

---

## 3. Integration Contracts

### 3.1 Plan Artifact (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P5-PlanArtifact` |
| **Name** | Plan Artifact |
| **Classification** | EXISTING |
| **Purpose** | Output contract of the Planning service; consumed by Coding, Review, Testing, Deployment, and Governance services. |
| **Owner** | Part 5 — Engineering Services (`ARCHITECTURE_SPEC_PART5.md`) |
| **Producer** | PlanningService |
| **Consumer(s)** | CodingService, ReviewService, TestingService, DeploymentService, G-02 Policy Evaluation Engine, G-12 Approval Manager |
| **Boundary crossed** | Planning phase → subsequent SDLC phases; planning → governance |
| **Source** | `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `planId` | UUID | Yes | Unique plan identifier. |
| `correlationId` | UUID | Yes | Workflow correlation identifier. |
| `requirements` | RequirementsSpec | Yes | Requirements specification. |
| `tasks` | array[TaskSpec] | Yes | Task specifications. |
| `dependencies` | array[TaskDependency] | Yes | Task dependency graph. |
| `estimates` | EstimationSpec | Yes | Estimation data. |
| `risks` | array[RiskSpec] | Yes | Identified risks. |
| `acceptanceCriteria` | array[Criterion] | Yes | Acceptance criteria. |
| `architectureDecisionRefs` | array[ADR] | Yes | Referenced ADRs. |
| `councilDecision` | CouncilDecisionRecord \| null | No | Optional council decision record. |
| `humanApproval` | HumanApprovalRecord \| null | No | Optional human approval record. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `version` | SemVer | Yes | Plan version. |

#### Required vs Optional
- **Required:** `planId`, `correlationId`, `requirements`, `tasks`, `dependencies`, `estimates`, `risks`, `acceptanceCriteria`, `architectureDecisionRefs`, `createdAt`, `version`
- **Optional:** `councilDecision`, `humanApproval`

#### Validation Rules
- `planId`, `correlationId` must be UUID v4.
- `tasks` must be non-empty.
- `dependencies` must reference valid task IDs within the same plan.
- `version` must match SemVer.

#### Source Provenance
- `planId`, `correlationId` UUID v4: `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section.
- `tasks` non-empty: `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section.
- `dependencies` references: `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section.
- `version` SemVer: `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section.

#### Invariants
- **INV-PLAN-001:** Every task in `tasks` MUST appear in `dependencies` or be a root task.
- **INV-PLAN-002:** A plan MUST have at least one acceptance criterion.

#### Version
- SemVer per plan.
- Source provenance: `Part05/ARCHITECTURE_SPEC_PART5.md` PlanArtifact section.

#### Compatibility
- Additive task/criterion additions are non-breaking.
- Structural changes to task spec or dependency model are breaking.

#### Evolution Rules
- MINOR: add optional fields or new criterion types.
- MAJOR: change required fields or dependency model.

#### Related Interfaces
- PlanningService emit/subscribe APIs
- G-02 evaluation request interface
- G-12 approval submission interface

#### Related Events
- `plan.created`, `plan.updated`, `plan.approved`, `plan.rejected`

#### Related Components
- PlanningService, G-02 Policy Evaluation Engine, G-12 Approval Manager

#### Related ADRs
- P5 planning architecture decisions

---

### 3.2 Governance Trigger Payload (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-GovernanceTrigger` |
| **Name** | Governance Trigger Event Payload |
| **Classification** | DERIVED |
| **Purpose** | Payload for events that trigger governance evaluation from non-governance subsystems. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | Any Part 1–12 subsystem emitting a trigger event |
| **Consumer(s)** | G-00 Governance Manager |
| **Boundary crossed** | Non-governance subsystem → governance tier |
| **Source** | `Part13/components.md` G-00 inbound interface; `Part13/events.md` governance trigger events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `triggerType` | enum | Yes | Type of trigger. |
| `triggerType` values | | | `policy.evaluation.requested`, `decision.authority.requested`, `risk.identified`, `compliance.baseline.published`, `approval.requested`, `exception.requested`, `audit.manifest.requested`, `conformance.evaluation.requested` |
| `subject` | GovernanceSubject \| null | No | Subject of the governance action. |
| `context` | object | No | Execution context. |
| `requestedBy` | string | Yes | Requester identifier. |
| `requestedAt` | ISO 8601 | Yes | Request timestamp. |

#### Required vs Optional
- **Required:** `triggerType`, `requestedBy`, `requestedAt`
- **Optional:** `subject`, `context`

#### Validation Rules
- `triggerType` must be one of defined governance trigger enum values.
- `requestedAt` must be valid ISO 8601 timestamp.
- `subject` when present must conform to GovernanceSubject schema.

#### Source Provenance
- `triggerType` enum values: `Part13/components.md` G-00 inbound interface; `Part13/events.md` governance trigger events.
- `requestedAt` ISO 8601: `Part13/components.md` G-00 inbound interface.
- GovernanceSubject conformance: `Part13/schemas.md` GovernanceSubject Schema section.

#### Invariants
- **INV-TRIG-001:** Every governance-triggering event MUST carry a valid `triggerType`.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-00 interface; `Part13/events.md` governance trigger events. No explicit versioning scheme is defined for this payload shape in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- New trigger types are additive and non-breaking.
- Source provenance: `Part13/events.md` governance event architecture; additive event types are non-breaking per Part 12/13 event registry model.
- Removing or renaming trigger types is breaking.

#### Evolution Rules
- MINOR: add new `triggerType` values.
- MAJOR: remove/rename trigger types or change required fields.

#### Related Interfaces
- G-00 `onGovernanceTrigger(event)` inbound interface

#### Related Events
- `GovernanceTrigger` (canonical wrapper event carrying this payload)

#### Related Components
- G-00 Governance Manager, all governance components

#### Related ADRs
- P13-ADR governance event architecture

---

### 3.3 Evaluation Decision (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-EvaluationDecision` |
| **Name** | Evaluation Decision |
| **Classification** | DERIVED |
| **Purpose** | Output of policy evaluation performed by G-02 Policy Evaluation Engine. Consumed by G-00, G-05, G-12, and caller subsystems. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-02 Policy Evaluation Engine |
| **Consumer(s)** | G-00 Governance Manager, G-05 Decision Authority Manager, G-12 Approval Manager, requesting subsystem |
| **Boundary crossed** | G-02 → governance orchestrator and caller subsystem |
| **Source** | `Part13/components.md` G-02 output contract; `Part13/events.md` evaluation events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `evaluationId` | UUID | Yes | Unique evaluation identifier. |
| `decision` | enum | Yes | `permitted` \| `denied` \| `exception_applied` |
| `policySetId` | UUID | Yes | Evaluated policy set identifier. |
| `matchedPolicies` | array[UUID] | Yes | Policies that matched during evaluation. |
| `appliedRules` | array[object] | Yes | Rules that were applied. |
| `exceptions` | array[UUID] \| null | No | Applied exceptions. |
| `reasoning` | string | Yes | Human-readable reasoning. |
| `evaluatedAt` | ISO 8601 | Yes | Evaluation timestamp. |

#### Required vs Optional
- **Required:** `evaluationId`, `decision`, `policySetId`, `matchedPolicies`, `appliedRules`, `reasoning`, `evaluatedAt`
- **Optional:** `exceptions`

#### Validation Rules
- `evaluationId`, `policySetId` must be UUID v4.
- `matchedPolicies[*]` must be valid policy IDs.
- `decision` must be one of defined enum values.

#### Source Provenance
- `evaluationId`, `policySetId` UUID v4: `Part13/components.md` G-02 output contract; `Part13/events.md` evaluation events.
- `matchedPolicies[*]` policy IDs: `Part13/components.md` G-02 output contract.
- `decision` enum: `Part13/components.md` G-02 output contract; `Part13/events.md` evaluation events.

#### Invariants
- **INV-EVAL-001:** `matchedPolicies` MUST be non-empty when `decision != denied` due to no-match.
- **INV-EVAL-002:** When `exceptions` is non-empty, each entry must reference a valid Exception ID.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-02 output contract; `Part13/events.md` evaluation events. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- Additive fields are non-breaking.
- Source provenance: `Part13/events.md` evaluation event architecture; Part 12/13 event registry model treats additive payload fields as non-breaking.
- Changing `decision` enum is breaking.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields or decision semantics.

#### Related Interfaces
- G-02 evaluation APIs
- G-00 `requestEvaluation` interface

#### Related Events
- `EvaluationStarted`, `EvaluationCompleted`, `EvaluationDenied`, `EvaluationPermitted`, `EvaluationExceptionApplied`

#### Related Components
- G-02 Policy Evaluation Engine, G-00 Governance Manager, G-12 Approval Manager

#### Related ADRs
- P13-ADR policy evaluation model

---

### 3.4 Authority Decision (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-AuthorityDecision` |
| **Name** | Authority Decision |
| **Classification** | DERIVED |
| **Purpose** | Output of authority resolution performed by G-05 Decision Authority Manager. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-05 Decision Authority Manager |
| **Consumer(s)** | G-00 Governance Manager, requesting subsystem, governance audit |
| **Boundary crossed** | G-05 → governance orchestrator and caller subsystem |
| **Source** | `Part13/components.md` G-05 output contract; `Part13/events.md` authority events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requestId` | UUID | Yes | Unique request identifier. |
| `authorityDecision` | enum | Yes | `GRANTED` \| `DENIED` \| `BOUNDARY` \| `UNAVAILABLE` |
| `grant` | object \| null | No | Granted authority details when `GRANTED`. |
| `grant.expiresAt` | ISO 8601 \| null | No | Grant expiration. |
| `grant.constraints` | array[object] \| null | No | Constraints on the grant. |
| `boundaryReason` | string \| null | No | Reason when `BOUNDARY`. |
| `resolvedAt` | ISO 8601 | Yes | Resolution timestamp. |

#### Required vs Optional
- **Required:** `requestId`, `authorityDecision`, `resolvedAt`
- **Optional:** `grant`, `boundaryReason`

#### Validation Rules
- `requestId` must be UUID v4.
- `authorityDecision` must be one of defined enum values.
- `grant` when present must contain valid constraint objects.
- `resolvedAt` must be valid ISO 8601 timestamp.

#### Source Provenance
- `requestId` UUID v4: `Part13/components.md` G-05 output contract; `Part13/events.md` authority events.
- `authorityDecision` enum: `Part13/components.md` G-05 output contract; `Part13/events.md` authority events.
- `grant` constraint objects: `Part13/components.md` G-05 output contract.
- `resolvedAt` ISO 8601: `Part13/components.md` G-05 output contract.

#### Invariants
- **INV-AUTH-001:** `grant` MUST be present when `authorityDecision == GRANTED`.
- **INV-AUTH-002:** `boundaryReason` MUST be present when `authorityDecision == BOUNDARY`.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-05 output contract; `Part13/events.md` authority events. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- Additive fields are nonbreaking.
- Source provenance: `Part13/events.md` authority event architecture; Part 12/13 event registry model.
- Changing authority decision enum is breaking.

#### Evolution Rules
- MINOR: add optional metadata or new constraint types.
- MAJOR: change decision enum or required fields.

#### Related Interfaces
- G-05 `resolveAuthority(request) → decision`

#### Related Events
- `AuthorityGranted`, `AuthorityResolved`, `AuthorityDenied`, `AuthorityBoundaryHit`

#### Related Components
- G-05 Decision Authority Manager, G-00 Governance Manager

#### Related ADRs
- P13-ADR authority model

---

### 3.5 Delegation Chain Validation (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-DelegationChain` |
| **Name** | Delegation Chain Validation Result |
| **Classification** | DERIVED |
| **Purpose** | Output of delegation chain validation performed by G-06 Delegation Authority Manager. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-06 Delegation Authority Manager |
| **Consumer(s)** | G-05 Decision Authority Manager, G-00 Governance Manager, requesting subsystem |
| **Boundary crossed** | G-06 → governance orchestrator and caller subsystem |
| **Source** | `Part13/components.md` G-06 output contract |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `valid` | boolean | Yes | Whether the delegation chain is valid. |
| `grant` | object \| null | No | Current grant details if valid. |
| `previous` | object \| null | No | Previous grant in chain. |
| `constraintsApplied` | array[object] | Yes | Constraints applied during validation. |
| `validatedAt` | ISO 8601 | Yes | Validation timestamp. |

#### Required vs Optional
- **Required:** `valid`, `constraintsApplied`, `validatedAt`
- **Optional:** `grant`, `previous`

#### Validation Rules
- `valid` must be boolean.
- `constraintsApplied` must be array of constraint objects.
- `validatedAt` must be valid ISO 8601 timestamp.

#### Source Provenance
- `valid` boolean: `Part13/components.md` G-06 output contract.
- `constraintsApplied` array of constraint objects: `Part13/components.md` G-06 output contract.
- `validatedAt` ISO 8601: `Part13/components.md` G-06 output contract.

#### Invariants
- **INV-DEL-001:** When `valid == true`, `grant` MUST be present and non-null.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-06 output contract. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- Additive constraint types are nonbreaking.
- Source provenance: `Part13/components.md` G-06 output contract; Part 12/13 event registry model.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields.

#### Related Interfaces
- G-06 `validateChain(actorId, action, target) → ChainValidation`

#### Related Events
- `DelegationGranted`, `DelegationRevoked`, `ChainValidationFailed`

#### Related Components
- G-06 Delegation Authority Manager, G-05 Decision Authority Manager

#### Related ADRs
- P13-ADR delegation chain model

---

### 3.6 Conformance Evaluation Report (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-ConformanceReport` |
| **Name** | Conformance Evaluation Report |
| **Classification** | DERIVED |
| **Purpose** | Output of conformance evaluation produced by G-15 Conformance Manager for governance councils and audit. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-15 Conformance Manager |
| **Consumer(s)** | G-04 Governance Council, G-09 Audit Manager, G-00 Governance Manager, Parts 14–15 |
| **Boundary crossed** | G-15 → governance oversight and downstream consumers |
| **Source** | `Part13/components.md` G-15 output contract; `Part13/13.12-Governance-Invariants-and-Conformance.md` |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reportId` | UUID | Yes | Unique report identifier. |
| `scope` | object | Yes | Evaluation scope. |
| `scope.entityId` | string | Yes | Evaluated entity identifier. |
| `scope.entityType` | enum | Yes | `agent` \| `workflow` \| `system` \| `data` \| `knowledge` |
| `baselineId` | UUID | Yes | Baseline identifier used for evaluation. |
| `conformanceState` | enum | Yes | `COMPLIANT` \| `PARTIALLY_COMPLIANT` \| `NON_COMPLIANT` \| `NOT_ASSESSED` |
| `gaps` | array[object] | Yes | Identified compliance gaps. |
| `findings` | array[object] | Yes | Findings. |
| `recommendations` | array[string] | No | Recommendations. |
| `evaluatedAt` | ISO 8601 | Yes | Evaluation timestamp. |

#### Required vs Optional
- **Required:** `reportId`, `scope`, `baselineId`, `conformanceState`, `gaps`, `findings`, `evaluatedAt`
- **Optional:** `recommendations`

#### Validation Rules
- `reportId`, `baselineId` must be UUID v4.
- `scope.entityType` must be one of defined enum values.
- `conformanceState` must be one of defined enum values.

#### Source Provenance
- `reportId`, `baselineId` UUID v4: `Part13/components.md` G-15 output contract; `Part13/13.12-Governance-Invariants-and-Conformance.md`.
- `scope.entityType` enum values: `Part13/components.md` G-15 output contract.
- `conformanceState` enum values: `Part13/components.md` G-15 output contract; `Part13/13.12-Governance-Invariants-and-Conformance.md`.

#### Invariants
- **INV-CONF-001:** `gaps` MUST be non-empty when `conformanceState != COMPLIANT`.
- **INV-CONF-002:** `findings` MUST reference valid obligations or controls.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-15 output contract; `Part13/13.12-Governance-Invariants-and-Conformance.md`. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- Additive findings/recommendations are nonbreaking.
- Source provenance: `Part13/13.12-Governance-Invariants-and-Conformance.md`; Part 13 federated governance model.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change conformance state enum or required fields.

#### Related Interfaces
- G-15 `requestConformanceEvaluation`, `publishReport`

#### Related Events
- `ConformanceEvaluationCompleted`, `ComplianceGapDetected`, `ConformanceBreachDetected`

#### Related Components
- G-15 Conformance Manager, G-04 Governance Council, G-09 Audit Manager

#### Related ADRs
- P13-ADR conformance model

---

### 3.7 Exception Grant (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-ExceptionGrant` |
| **Name** | Exception Grant |
| **Classification** | DERIVED |
| **Purpose** | Output of exception management; grants temporary deviation from policy with monitoring requirements. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-11 Exception Manager |
| **Consumer(s)** | G-02 Policy Evaluation Engine, G-15 Conformance Manager, G-00 Governance Manager, requesting subsystem |
| **Boundary crossed** | G-11 → evaluation/conformance engines and caller subsystem |
| **Source** | `Part13/components.md` G-11 output contract; `Part13/events.md` exception events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `exceptionId` | UUID | Yes | Unique exception identifier. |
| `scope` | object | Yes | Exception scope. |
| `scope.policyId` | UUID | Yes | Policy to which exception applies. |
| `scope.subjectId` | UUID \| string | Yes | Subject of the exception. |
| `conditions` | array[string] | Yes | Conditions under which exception is valid. |
| `validPeriod` | object | Yes | Validity window. |
| `validPeriod.validFrom` | ISO 8601 | Yes | Start timestamp. |
| `validPeriod.validUntil` | ISO 8601 | Yes | End timestamp. |
| `monitoringRequirements` | array[string] | Yes | Monitoring obligations. |
| `grantedBy` | string | Yes | Granter identifier. |
| `grantedAt` | ISO 8601 | Yes | Grant timestamp. |

#### Required vs Optional
- **Required:** `exceptionId`, `scope`, `conditions`, `validPeriod`, `monitoringRequirements`, `grantedBy`, `grantedAt`
- **Optional:** None beyond required fields.

#### Validation Rules
- `exceptionId` must be UUID v4.
- `scope.policyId` must be valid policy ID.
- `validPeriod.validUntil > validPeriod.validFrom`.
- `conditions` must be non-empty array.
- `monitoringRequirements` must be non-empty array.

#### Source Provenance
- `exceptionId` UUID v4: `Part13/components.md` G-11 output contract; `Part13/events.md` exception events.
- `scope.policyId` valid policy ID: `Part13/components.md` G-11 output contract.
- `validPeriod` ordering: `Part13/components.md` G-11 output contract.
- `conditions` non-empty array: `Part13/components.md` G-11 output contract.
- `monitoringRequirements` non-empty array: `Part13/components.md` G-11 output contract.

#### Invariants
- **INV-EXC-001:** Exception MUST NOT exceed maximum duration defined by governance policy.
- **INV-EXC-002:** Exception MUST be linked to an active, published policy.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-11 output contract; `Part13/events.md` exception events. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- Additive monitoring requirements are nonbreaking.
- Source provenance: `Part13/events.md` exception event architecture; Part 12/13 event registry model.

#### Evolution Rules
- MINOR: add optional metadata.
- MAJOR: change required fields or scope model.

#### Related Interfaces
- G-11 `requestException(request)`, `notifyEvaluator(exceptionId) → G-02`

#### Related Events
- `ExceptionRequested`, `ExceptionGranted`, `ExceptionDenied`, `ExceptionExpiring`, `ExceptionExpired`

#### Related Components
- G-11 Exception Manager, G-02 Policy Evaluation Engine, G-15 Conformance Manager

#### Related ADRs
- P13-ADR exception lifecycle

---

### 3.8 Approval Decision Record (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-ApprovalDecision` |
| **Name** | Approval Decision Record |
| **Classification** | DERIVED |
| **Purpose** | Output of approval workflow managed by G-12 Approval Manager. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-12 Approval Manager |
| **Consumer(s)** | G-00 Governance Manager, requesting subsystem, governance audit |
| **Boundary crossed** | G-12 → governance orchestrator and caller subsystem |
| **Source** | `Part13/components.md` G-12 output contract; `Part13/events.md` approval events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requestId` | UUID | Yes | Unique approval request identifier. |
| `decision` | enum | Yes | `approved` \| `rejected` \| `escalated` \| `expired` \| `withdrawn` |
| `decidedBy` | string | Yes | Decider identifier. |
| `reasoning` | string | No | Decision reasoning. |
| `decidedAt` | ISO 8601 | Yes | Decision timestamp. |

#### Required vs Optional
- **Required:** `requestId`, `decision`, `decidedBy`, `decidedAt`
- **Optional:** `reasoning`

#### Validation Rules
- `requestId` must be UUID v4.
- `decision` must be one of defined enum values.
- `decidedAt` must be valid ISO 8601 timestamp.

#### Source Provenance
- `requestId` UUID v4: `Part13/components.md` G-12 output contract; `Part13/events.md` approval events.
- `decision` enum values: `Part13/components.md` G-12 output contract.
- `decidedAt` ISO 8601: `Part13/components.md` G-12 output contract.

#### Invariants
- **INV-APPR-001:** `decidedAt` MUST be >= request submission timestamp.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.
- Versioning basis: `Part13/components.md` G-12 output contract; `Part13/events.md` approval events. No explicit versioning scheme is defined in source; 1.0.0 is catalog reconstruction.

#### Compatibility
- New decision reasons/outcomes are additive and nonbreaking.
- Source provenance: `Part13/events.md` approval event architecture; Part 12/13 event registry model.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields.

#### Related Interfaces
- G-12 `submitForApproval`, `recordDecision`

#### Related Events
- `ApprovalRequested`, `ApprovalDecided`, `ApprovalRejected`, `ApprovalEscalated`

#### Related Components
- G-12 Approval Manager, G-00 Governance Manager

#### Related ADRs
- P13-ADR approval workflow

---

### 3.9 Baseline Publication Record (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-ComplianceBaseline` |
| **Name** | Compliance Baseline Publication Record |
| **Classification** | DERIVED |
| **Purpose** | Output of baseline publication by G-08 Compliance Manager; consumed by G-15 Conformance Manager and registries. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-08 Compliance Manager |
| **Consumer(s)** | G-15 Conformance Manager, G-03 Governance Registry, governance audit |
| **Boundary crossed** | G-08 → conformance evaluation and registry |
| **Source** | `Part13/components.md` G-08 output contract; `Part13/events.md` compliance events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `baselineId` | UUID | Yes | Unique baseline identifier. |
| `name` | string | Yes | Baseline name. |
| `version` | SemVer | Yes | Baseline version. |
| `obligations` | array[object] | Yes | Embedded obligations. |
| `controls` | array[object] | No | Embedded controls. |
| `scope` | object | Yes | Baseline scope. |
| `effectiveFrom` | ISO 8601 | Yes | Effective start timestamp. |
| `effectiveUntil` | ISO 8601 \| null | No | Effective end timestamp. |
| `publishedBy` | string | Yes | Publisher identifier. |
| `publishedAt` | ISO 8601 | Yes | Publication timestamp. |

#### Required vs Optional
- **Required:** `baselineId`, `name`, `version`, `obligations`, `scope`, `effectiveFrom`, `publishedBy`, `publishedAt`
- **Optional:** `controls`, `effectiveUntil`

#### Validation Rules
- `baselineId` must be UUID v4.
- `version` must match SemVer.
- `effectiveUntil` when present must be > `effectiveFrom`.
- `obligations` must be non-empty array.

#### Source Provenance
- `baselineId` UUID v4: `Part13/components.md` G-08 output contract; `Part13/events.md` compliance events.
- `version` SemVer: `Part13/components.md` G-08 output contract.
- `effectiveUntil` ordering: `Part13/components.md` G-08 output contract.
- `obligations` non-empty array: `Part13/components.md` G-08 output contract.

#### Invariants
- **INV-BASE-001:** `obligations` MUST be non-empty.
- **INV-BASE-002:** Baseline MUST be registered in G-03 before publication.

#### Version
- SemVer per baseline.

#### Compatibility
- Additive obligations/controls are nonbreaking.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields.

#### Related Interfaces
- G-08 `publishBaseline(baseline) → G-03`, `notifyConformanceEngine(baseline) → G-15`

#### Related Events
- `BaselinePublished`, `ObligationIdentified`, `ObligationImported`

#### Related Components
- G-08 Compliance Manager, G-15 Conformance Manager, G-03 Governance Registry

#### Related ADRs
- P13-ADR compliance baseline model

---

## 4. Event Payloads

> Event payloads are the domain-specific `payload` objects carried inside the Canonical Event Envelope (`EVENT-ENVELOPE-v1`). This section documents the major cross-boundary payload shapes.

### 4.1 Governance Event Payload Families (UNSPECIFIED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-GovernanceEventPayloads` |
| **Name** | Governance Event Payload Families |
| **Classification** | UNSPECIFIED |
| **Purpose** | Documents the aggregate families for 51 governance events under the `governance.*` namespace. Individual payload schemas are not published in Parts 1–13. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | G-00 through G-15 governance components |
| **Consumer(s)** | G-14 Governance Event Manager, audit pipelines, governance councils, Parts 14–15 consumers |
| **Boundary crossed** | Governance components → EventBus → subscribers |
| **Source** | `Part13/events.md`; `Part13/13.13-Cross-References-and-ADR-Summary.md` |

#### Aggregate Families

| Aggregate | Event Types | Payload Reference |
|-----------|-------------|-------------------|
| `policy.*` | `created`, `updated`, `submitted`, `approved`, `rejected`, `published`, `deprecated`, `retired` | `P13-Policy` |
| `policySet.*` | lifecycle events | `P13-PolicySet` |
| `decision.*` | lifecycle events | `P13-Decision` |
| `authority.*` | `granted`, `resolved`, `denied`, `boundaryHit`, `suspended`, `revoked`, `thresholdConsumed` | `P13-Authority` |
| `capability.*` | lifecycle events | `P13-GovernanceCapability` |
| `delegation.*` | `granted`, `revoked`, `chainValidated`, `chainFailed` | `P13-Delegation` |
| `approval.*` | workflow events | `P13-Approval` |
| `risk.*` | `identified`, `assessed`, `treated`, `closed`, `reopened`, `postureProduced` | `P13-Risk` |
| `compliance.*` | `obligationIdentified`, `obligationImported`, `evidenceStale`, `baselinePublished`, `findingIssued`, `gapDetected`, `reviewDue` | `P13-Compliance` |
| `audit.*` | `eventRecorded`, `integrityVerified`, `integrityBreachDetected`, `manifestSealed`, `manifestArchived`, `accessDenied`, `accessGranted`, `retentionExpired` | `P13-Audit` |
| `exception.*` | `requested`, `granted`, `denied`, `expiring`, `expired`, `renewed`, `closed` | `P13-Exception` |
| `override.*` | override events | `P13-Override` |
| `conformance.*` | conformance events | `P13-ConformanceReport` |
| `subject.*` | subject events | `P13-GovernanceSubject` |

#### Required vs Optional
- **Required:** envelope fields per `EVENT-ENVELOPE-v1`
- **Optional:** `trace.*`, `metadata.*`, `security.*`

#### Validation Rules
- `schema_ref` MUST resolve to a registered governance event payload schema.
- `produced_by.actor_kind` MUST be `system` for governance events emitted by governance infrastructure, or the emitting component's actual kind.
- `payload` MUST validate against the schema identified by `schema_ref`.

#### Source Provenance
- `schema_ref` registration requirement: `Part12/events.md` §4; `Part13/events.md` governance event architecture; P13-ADR governance event architecture.
- `produced_by.actor_kind` requirement: `Part12/events.md` §4 `produced_by.actor_kind` enum (`agent`, `council`, `workflow`, `runtime`, `scheduler`, `tool`, `system`); governance components emit under their actual actor kind, not `governance`.
- `payload` schema validation: `Part12/events.md` §27 schema validation rule.

#### Invariants
- **INV-GEV-001:** All governance events MUST carry a valid `schema_ref` resolving to a governance payload schema.
- **INV-GEV-002:** Governance event payloads MUST reference valid governance aggregate IDs.

#### Version
- `1.0.0` (reconstructed): Aggregate family catalog reconstructed from `Part13/events.md` governance event taxonomy. Individual payload schemas are not published in Parts 1–13.
  - **Source basis:** `Part13/events.md`; `Part13/13.13-Cross-References-and-ADR-Summary.md` enumerate governance event families. No standalone governance event payload schema version document is provided in Parts 1–13; catalog assigns `1.0.0` as reconstruction.

#### Compatibility
- New event types are additive and nonbreaking.
- Changing payload structure of an existing event type requires version bump for that `schema_ref`.

#### Evolution Rules
- MINOR: add new event types or new optional payload fields.
- MAJOR: change required payload fields or remove event types.

#### Related Interfaces
- G-14 `emit(event)`, `getEventStream(filter)`

#### Related Events
- All 51 governance events enumerated in Part 13 §13.9 and §13.13

#### Related Components
- G-00 through G-15, G-14 Governance Event Manager

#### Related ADRs
- P13-ADR governance event architecture

---

### 4.2 Kernel Lifecycle Event Payloads (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P1-KernelLifecyclePayloads` |
| **Name** | Kernel Lifecycle Event Payloads |
| **Classification** | EXISTING |
| **Purpose** | Payload shapes for kernel lifecycle state transition events. |
| **Owner** | Part 1 — Hermes Kernel Architecture (`ARCHITECTURE_SPEC_PART1.md` §1.9–1.11) |
| **Producer** | HermesKernel / LifecycleManager |
| **Consumer(s)** | ObservabilityManager, ServiceRegistry, configuration audit, external monitoring |
| **Boundary crossed** | Kernel core → observability/monitoring subsystems |
| **Source** | `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2 |

#### Fields / Concepts
| Event Type | Payload Fields |
|------------|----------------|
| `KernelInitializationStarted` | `timestamp`, `configHash` |
| `KernelReady` | `timestamp`, `initializationDurationMs`, `componentCount`, `managerCount`, `serviceCount` |
| `KernelShutdownStarted` | `timestamp`, `reason` (`graceful` \| `error` \| `forced`), `error?` |
| `KernelTerminated` | `timestamp`, `shutdownDurationMs`, `errors[]` |

#### Required vs Optional
- Each payload has required fields as listed above; `error` is optional in `KernelShutdownStarted`; `errors` is required in `KernelTerminated` but may be empty array.

#### Validation Rules
- All timestamps must be valid ISO 8601.
- `reason` must be one of defined enum values.
- `errors` entries must be valid error objects.

#### Source Provenance
- Timestamp ISO 8601: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2 kernel lifecycle events.
- `reason` enum values: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2 (`graceful` \| `error` \| `forced`).
- `errors` entries: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2 kernel lifecycle events.

#### Invariants
- **INV-KL-001:** Every lifecycle transition MUST emit exactly one lifecycle event.
- **INV-KL-002:** `KernelTerminated` MUST include all errors collected during shutdown.

#### Version
- `1.0.0` (DERIVED): Kernel lifecycle payload catalog reconstructed from `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2. No standalone payload schema version is defined in source.
  - **Source basis:** `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2 kernel lifecycle events. No explicit versioning scheme is defined in source for these payload shapes; catalog assigns `1.0.0` as reconstruction.

#### Compatibility
- Additive fields are nonbreaking.
- Source provenance: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.9.2; additive payload fields are non-breaking per Part 12 event registry model.

#### Evolution Rules
- MINOR: add optional telemetry fields.
- MAJOR: change lifecycle state machine.

#### Related Interfaces
- EventBus publish interface
- LifecycleManager state machine

#### Related Events
- `KernelInitializationStarted`, `KernelReady`, `KernelShutdownStarted`, `KernelTerminated`

#### Related Components
- HermesKernel, LifecycleManager, ObservabilityManager

#### Related ADRs
- Part 1 kernel lifecycle design

---

### 4.3 Multi-Agent Communication Message Payloads (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-MultiAgentMessagePayloads` |
| **Name** | Multi-Agent Communication Message Payloads |
| **Classification** | EXISTING |
| **Purpose** | Payload shapes for direct agent-to-agent messages routed through the EventBus. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`events.md` §12) |
| **Producer** | Agents, Council, Workflow steps |
| **Consumer(s)** | Target agents, Council, governance audit |
| **Boundary crossed** | Sender agent → receiver agent via EventBus |
| **Source** | `Part12/events.md` §12 Communication Events |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messageId` | UUID | Yes | Unique message identifier. |
| `conversationId` | UUID | Yes | Conversation/workflow identifier. |
| `senderId` | UUID | Yes | Sender agent identifier. |
| `recipientId` | UUID \| null | No | Direct recipient agent identifier; null for broadcast. |
| `messageType` | string | Yes | Message type identifier. |
| `content` | object | Yes | Message content. |
| `inReplyTo` | UUID \| null | No | Message identifier being replied to. |
| `priority` | enum | No | Message priority. |
| `sentAt` | ISO 8601 | Yes | Send timestamp. |

#### Required vs Optional
- **Required:** `messageId`, `conversationId`, `senderId`, `messageType`, `content`, `sentAt`
- **Optional:** `recipientId`, `inReplyTo`, `priority`

#### Validation Rules
- `messageId`, `conversationId`, `senderId` must be valid UUIDs.
- `recipientId` when present must be valid UUID.
- `inReplyTo` when present must reference an existing message in the same `conversationId`.

#### Source Provenance
- `messageId`, `conversationId`, `senderId` UUID v4: `Part12/events.md` §12 Communication Events.
- `recipientId` UUID when present: `Part12/events.md` §12 Communication Events.
- `inReplyTo` reference requirement: `Part12/events.md` §12 Communication Events; `causation_id` model from §30.

#### Invariants
- **INV-MSG-001:** Every message MUST belong to a valid `conversationId`.
- **INV-MSG-002:** `senderId` MUST be a registered agent.

#### Version
- `1.0.0` (DERIVED): Multi-agent message payload catalog reconstructed from `Part12/events.md` §12 Communication Events. No standalone payload schema version is defined in source.
  - **Source basis:** `Part12/events.md` §12 Communication Events. No explicit versioning scheme is defined in source for these payload shapes; catalog assigns `1.0.0` as reconstruction.

#### Compatibility
- Additive message types are nonbreaking.

#### Evolution Rules
- MINOR: add new message types or optional fields.
- MAJOR: change required fields.

#### Related Interfaces
- Agent communication APIs
- EventBus message routing

#### Related Events
- `communication.message.sent`, `communication.message.received`, `communication.message.replied`

#### Related Components
- AgentManager, EventBus

#### Related ADRs
- P12-ADR multi-agent communication model

---

## 5. API Request/Response Schemas

### 5.1 Governance Evaluation Request (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P13-EvaluationRequest` |
| **Name** | Governance Evaluation Request |
| **Classification** | DERIVED |
| **Purpose** | Request payload for policy evaluation submitted by non-governance subsystems to G-02 via G-00. |
| **Owner** | Part 13 — Governance Tier |
| **Producer** | Any Part 1–12 subsystem |
| **Consumer(s)** | G-00 Governance Manager, G-02 Policy Evaluation Engine |
| **Boundary crossed** | Non-governance subsystem → governance tier |
| **Source** | `Part13/components.md` G-00 `requestEvaluation(policySet, context)` interface |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requestId` | UUID | Yes | Unique request identifier. |
| `policySetId` | UUID | Yes | Policy set to evaluate against. |
| `context` | object | Yes | Evaluation context. |
| `subject` | GovernanceSubject | Yes | Subject being evaluated. |
| `effectiveAsOf` | ISO 8601 | No | Evaluation timestamp; defaults to now. |
| `requestedBy` | string | Yes | Requester identifier. |
| `requestedAt` | ISO 8601 | Yes | Request timestamp. |

#### Required vs Optional
- **Required:** `requestId`, `policySetId`, `context`, `subject`, `requestedBy`, `requestedAt`
- **Optional:** `effectiveAsOf`

#### Validation Rules
- `requestId`, `policySetId` must be UUID v4.
- `subject` must conform to GovernanceSubject schema.
- `context` must be valid JSON object.
- `effectiveAsOf` when present must be valid ISO 8601 timestamp.

#### Source Provenance
- `requestId`, `policySetId` UUID v4: `Part13/components.md` G-00 `requestEvaluation(policySet, context)` interface.
- `subject` GovernanceSubject conformance: `Part13/components.md` G-00 interface; `Part13/schemas.md` GovernanceSubject Schema section.
- `context` valid JSON object: `Part13/components.md` G-00 interface.
- `effectiveAsOf` ISO 8601: `Part13/components.md` G-00 interface.

#### Invariants
- **INV-EVALREQ-001:** `policySetId` MUST reference a published policy set.

#### Version
- Not assigned in source; catalog assigns 1.0.0 as reconstruction.

#### Compatibility
- Additive context fields are nonbreaking.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields.

#### Related Interfaces
- G-00 `requestEvaluation(policySet, context) → G-02`

#### Related Events
- `EvaluationStarted`, `EvaluationCompleted`

#### Related Components
- G-00 Governance Manager, G-02 Policy Evaluation Engine, G-03 Governance Registry

#### Related ADRs
- P13-ADR policy evaluation request model

---

## 6. Configuration Schemas

### 6.1 Kernel Configuration Interface (DERIVED)

| Field | Value |
|-------|-------|
| **Schema ID** | `P1-KernelConfig` |
| **Name** | Kernel Configuration Interface |
| **Classification** | DERIVED |
| **Purpose** | Configuration contract for HermesKernel initialization, reconstructed from interface signatures and prose. |
| **Owner** | Part 1 — Hermes Kernel Architecture |
| **Producer** | Configuration layer / deployment manifest |
| **Consumer(s)** | HermesKernel, ConfigurationManager, Core Components, Core Managers, Services |
| **Boundary crossed** | Deployment/config layer → kernel runtime |
| **Source** | `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1; `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3 |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `environment` | enum | Yes | `development` \| `staging` \| `production` |
| `serviceDiscoveryPaths` | array[string] | Yes | Paths for service discovery. |
| `initializationTimeouts` | object \| null | No | Per-phase initialization timeouts. |
| `shutdownTimeouts` | object \| null | No | Per-phase shutdown timeouts. |
| `healthCheckIntervalMs` | integer \| null | No | Health check interval. |
| `heartbeatIntervalMs` | integer \| null | No | Heartbeat interval. |
| `maxRecoveryAttempts` | integer \| null | No | Maximum recovery attempts. |
| `features` | object \| null | No | Feature flags. |
| `features.enableHotReload` | boolean \| null | No | Hot reload flag. |
| `features.enableProfiling` | boolean \| null | No | Profiling flag. |
| `features.strictConformance` | boolean \| null | No | Strict conformance flag. |

#### Required vs Optional
- **Required:** `environment`, `serviceDiscoveryPaths`
- **Optional:** `initializationTimeouts`, `shutdownTimeouts`, `healthCheckIntervalMs`, `heartbeatIntervalMs`, `maxRecoveryAttempts`, `features.*`

#### Validation Rules
- `environment` must be one of defined enum values.
- `serviceDiscoveryPaths` must be non-empty array of strings.
- Numeric fields when present must be positive integers.

#### Source Provenance
- `environment` enum values: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1; `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.
- `serviceDiscoveryPaths` non-empty array: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1.
- Numeric fields positive integers: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1; `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.

#### Invariants
- **INV-KCFG-001:** KernelConfig MUST be immutable after `INITIALIZING` phase completes.

#### Version
- Not assigned in source; this catalog documents the interface shape only.
- Versioning basis: `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3; `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1. No explicit versioning scheme is defined in source for the configuration interface shape.

#### Compatibility
- Additive feature flags and optional numeric fields are nonbreaking.

#### Evolution Rules
- MINOR: add optional configuration fields.
- MAJOR: change required fields or environment semantics.

#### Related Interfaces
- ConfigurationManager schema validation
- HermesKernel.initialize(config) entry point

#### Related Events
- `KernelInitializationStarted`, `ConfigurationFrozen`

#### Related Components
- ConfigurationManager, HermesKernel, all Core Components/Managers

#### Related ADRs
- Part 1 configuration architecture

---

### 6.2 Runtime Configuration Record (EXISTING)

| Field | Value |
|-------|-------|
| **Schema ID** | `P12-Configuration` |
| **Name** | Runtime Configuration Record |
| **Classification** | EXISTING |
| **Purpose** | Generic configuration record for agents, workflows, tasks, system, and plugins. |
| **Owner** | Part 12 — Multi-Agent Collaboration (`schemas.md` §Configuration Schema) |
| **Producer** | Configuration system, policy-derived config, user config |
| **Consumer(s)** | Agents, WorkflowManager, TaskManager, PluginManager, Runtime |
| **Boundary crossed** | Configuration system → runtime entities |
| **Source** | `Part12/schemas.md` Configuration Schema section |

#### Fields / Concepts
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `configId` | UUID | Yes | Unique configuration identifier. |
| `name` | string | Yes | Configuration name. |
| `version` | SemVer | Yes | Configuration version. |
| `description` | string | No | Configuration description. |
| `configType` | enum | Yes | `agent` \| `workflow` \| `task` \| `system` \| `plugin` |
| `targetId` | UUID \| string | Yes | Target entity identifier. |
| `settings` | object | Yes | Key-value settings. |
| `schema` | string \| null | No | JSON Schema URI validating `settings`. |
| `tags` | array[string] | No | Tags. |
| `createdBy` | string | Yes | Creator identifier. |
| `createdAt` | ISO 8601 | Yes | Creation timestamp. |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp. |
| `effectiveFrom` | ISO 8601 | Yes | Effective start timestamp. |
| `effectiveUntil` | ISO 8601 \| null | No | Effective end timestamp. |
| `source` | enum | Yes | `user` \| `system` \| `policy` \| `environment` |
| `metadata` | object | No | Arbitrary metadata. |

#### Required vs Optional
- **Required:** `configId`, `name`, `version`, `configType`, `targetId`, `settings`, `createdBy`, `createdAt`, `updatedAt`, `effectiveFrom`
- **Optional:** `description`, `schema`, `tags`, `effectiveUntil`, `source`, `metadata`

#### Validation Rules
- `configId` must be UUID v4.
- `version` must match SemVer.
- `targetId` must be valid identifier for the specified `configType`.
- `settings` when `schema` is present must validate against referenced schema.
- `effectiveUntil` when present must be > `effectiveFrom`.

#### Source Provenance
- `configId` UUID v4: `Part12/schemas.md` Configuration Schema section.
- `version` SemVer: `Part12/schemas.md` Configuration Schema section.
- `targetId` valid identifier: `Part12/schemas.md` Configuration Schema section.
- `settings` JSON Schema validation when `schema` present: `Part12/schemas.md` Configuration Schema section.
- `effectiveUntil` ordering: `Part12/schemas.md` Configuration Schema section.

#### Invariants
- **INV-CFG-001:** `updatedAt >= createdAt`.

#### Version
- SemVer per configuration record.
- Source provenance: `Part12/schemas.md` Configuration Schema section; Part 12 schema governance model applies SemVer.

#### Compatibility
- Additive settings keys are nonbreaking.

#### Evolution Rules
- MINOR: add optional fields.
- MAJOR: change required fields or `configType` enum.

#### Related Interfaces
- Configuration CRUD APIs
- Runtime configuration lookup APIs

#### Related Events
- `configuration.created`, `configuration.updated`, `configuration.effective`

#### Related Components
- ConfigurationManager, Runtime, AgentManager, WorkflowManager, PluginManager

#### Related ADRs
- P12-ADR configuration model

---

### 6.3 Configuration Layer Merge Semantics (UNSPECIFIED)

| Field | Value |
|-------|-------|
| **Schema ID** | `CONFIG-Layer` |
| **Name** | Configuration Layer Merge Semantics |
| **Classification** | UNSPECIFIED |
| **Purpose** | Documents the four-layer merge model for configuration files. No formal schema is published in Parts 1–13. |
| **Owner** | Part 7 — Configuration System (referenced in Part 0 §0.3.4, Part 1 §1.10.1) |
| **Producer** | Deployment, environment provisioning |
| **Consumer(s)** | ConfigurationManager, HermesKernel, all runtime entities |
| **Boundary crossed** | Deployment/config layer → kernel runtime |
| **Source** | `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.4; `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1 |

#### Known Structure
| Layer | File/Variable | Purpose |
|-------|---------------|---------|
| Defaults | `defaults.yaml` | Baseline defaults for all configurable parameters. |
| Application | `app.yaml` | Application-level overrides. |
| Environment | `env.yaml` | Environment-specific overrides. |
| Environment Variables | `AIOS_<SECTION>_<KEY>` | Secret/override values. |

- `app.yaml` observed structure: `name`, `version`, `environment`, `workspace`, `logs`, `config`
- `defaults.yaml` exists at `C:\Development\AI-OS\config\defaults.yaml` but contents were not readable in this review.

#### Validation Rules
- Merge order: defaults → app → env → env vars (last wins).
- Immutable after `INITIALIZING` phase completes.
- Environment variables take highest precedence.

#### Source Provenance
- Merge order and precedence: `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.4; `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1.
- Immutability after INITIALIZING: `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1.

#### Invariants
- **INV-CFGLAYER-001:** Configuration MUST be fully resolved before `INITIALIZING` phase completes.

#### Version
- N/A

#### Compatibility
- Layer semantics are fixed; adding layers requires kernel modification.

#### Evolution Rules
- Adding new layers is breaking.
- Adding new keys within layers is nonbreaking if defaults are provided.

#### Related Interfaces
- ConfigurationManager load/merge/freeze APIs

#### Related Events
- `ConfigurationFrozen`

#### Related Components
- ConfigurationManager, HermesKernel

#### Related ADRs
- Part 7 configuration architecture

#### Gaps
- **[GAP]** Full JSON Schema for `defaults.yaml` is not published in Parts 1–13 architecture docs.
- **[GAP]** Full schema for environment YAML layer is not published.
- **[GAP]** Canonical environment variable naming schema (`AIOS_<SECTION>_<KEY>`) is defined by convention but not fully enumerated.

---

## 7. Metadata / Context Schemas

### 7.1 Trace Context (EXISTING)

See §1.2 above. This schema is documented as a metadata/context schema because it is attached to events and messages as a carrier, not as a standalone event type.

### 7.2 Classification Metadata (EXISTING)

See §1.3 above. Documented here as a metadata/context schema for the same reason.

---

## 8. Governance Aggregate Schemas (Part 13 — EXISTING Summary)

> The following 14 schemas are defined in full in `Part13/schemas.md`. They are listed here as integration-relevant contracts because they are produced by the governance tier and consumed by Parts 14–15 and by cross-boundary events. Full field-level documentation is in `Part13/schemas.md`; this section provides the catalog index and cross-reference map.

| Schema ID | Name | Classification | Source |
|-----------|------|----------------|--------|
| `P13-Policy` | Policy | EXISTING | `Part13/schemas.md` §Policy Schema |
| `P13-PolicySet` | Policy Set | EXISTING | `Part13/schemas.md` §PolicySet Schema |
| `P13-Decision` | Decision | EXISTING | `Part13/schemas.md` §Decision Schema |
| `P13-Authority` | Authority | EXISTING | `Part13/schemas.md` §Authority Schema |
| `P13-GovernanceCapability` | Capability (Governance) | EXISTING | `Part13/schemas.md` §Capability Schema |
| `P13-Delegation` | Delegation | EXISTING | `Part13/schemas.md` §Delegation Schema |
| `P13-Approval` | Approval | EXISTING | `Part13/schemas.md` §Approval Schema |
| `P13-Risk` | Risk | EXISTING | `Part13/schemas.md` §Risk Schema |
| `P13-Compliance` | Compliance | EXISTING | `Part13/schemas.md` §Compliance Schema |
| `P13-Audit` | Audit | EXISTING | `Part13/schemas.md` §Audit Schema |
| `P13-Exception` | Exception | EXISTING | `Part13/schemas.md` §Exception Schema |
| `P13-Override` | Override | EXISTING | `Part13/schemas.md` §Override Schema |
| `P13-RiskAssessment` | Risk Assessment | EXISTING | `Part13/schemas.md` §RiskAssessment Schema |
| `P13-GovernanceSubject` | Governance Subject | EXISTING | `Part13/schemas.md` §GovernanceSubject Schema |

### Part 13 Schema Cross-References

- **Policy** ↔ PolicySet, Decision, Authority, GovernanceSubject, Approval, Exception, Override, Compliance, Audit
- **PolicySet** ↔ Policy, Decision, EvaluationDecision
- **Decision** ↔ Policy, Authority, Council, Approval, Audit
- **Authority** ↔ Decision, Delegation, GovernanceSubject
- **Delegation** ↔ Authority, GovernanceSubject
- **Approval** ↔ Decision, Exception, Override
- **Risk** ↔ RiskAssessment, Treatment, Compliance, ConformanceReport
- **Compliance** ↔ Baseline, Obligation, Control, Audit, ConformanceReport
- **Audit** ↔ Manifest, Evidence, Decision, Integrity record
- **Exception** ↔ Policy, EvaluationDecision
- **Override** ↔ Decision, Approval
- **RiskAssessment** ↔ Risk, Treatment, GovernanceSubject
- **GovernanceSubject** ↔ Policy, Delegation, Authority, Risk, Compliance

---

## 9. Cross-Part Boundary Summary Matrix

| Source Part | Target Part | Primary Contracts |
|-------------|-------------|-------------------|
| Part 0 | Part 1, Part 12 | Terminology, principles, event-first mandate, BaseService concept |
| Part 1 | Part 12, Part 13 | KernelConfig [DERIVED], ICoreComponent/ICoreManager interfaces [UNSPECIFIED], lifecycle events |
| Part 2 | Part 12, Part 13 | Event Envelope [EXISTING], EventBus contracts [UNSPECIFIED] |
| Part 5 | Part 12, Part 13 | PlanArtifact [EXISTING], TaskSpec [UNSPECIFIED], RequirementsSpec [GAP], Criterion [GAP] |
| Part 12 | Part 13 | Agent [EXISTING], Capability [EXISTING], Workflow [EXISTING], Task [EXISTING], Council [EXISTING], Vote [EXISTING], SharedContext [EXISTING], KnowledgeObject [EXISTING], MemoryObject [EXISTING], Runtime [UNSPECIFIED], Scheduler [UNSPECIFIED], Plugin [UNSPECIFIED], Tool [EXISTING in events.md as `tool.lifecycle.*`], Message [UNSPECIFIED], Event [EXISTING as envelope], ExecutionPlan [UNSPECIFIED], Checkpoint [UNSPECIFIED], Configuration [EXISTING], HealthReport [UNSPECIFIED] |
| Part 12 | Part 14 | All Part 12 schemas cataloged above |
| Part 13 | Part 14 | All 14 governance schemas [EXISTING in Part13/schemas.md], governance event payload families [UNSPECIFIED], governance component interfaces [UNSPECIFIED] |
| Part 13 | Part 15 | Governance contracts, conformance reports [DERIVED], audit records [UNSPECIFIED] |

---

## 10. Identified Gaps

| Gap ID | Description | Classification | Source Gap | Recommendation |
|--------|-------------|----------------|------------|---------------|
| **[GAP-1]** | `BaseService` contract schema is referenced in Parts 0/1 but not formally defined as a JSON Schema or data model. | GAP | `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.2; `Part01/ARCHITECTURE_SPEC_PART1.md` §1.5 | Publish `BaseService` schema including `depends_on`, `on_start`, `on_error`, `emit`, `subscribe` interfaces. |
| **[GAP-2]** | `HealthStatus` and `ManagerMetrics` schemas are referenced by `ICoreManager.healthCheck()` and `getMetrics()` but not defined in Parts 1–13. | GAP | `Part01/ARCHITECTURE_SPEC_PART1.md` §1.8.2; `Part12/components.md` | Publish `HealthStatus` and `ManagerMetrics` schemas in Part 1 or Part 12. |
| **[GAP-3]** | `ServiceRegistry` data model (service metadata, dependency DAG shape) is not defined as a schema. | GAP | `Part01/ARCHITECTURE_SPEC_PART1.md` §1.7.2; `Part12/components.md` | Publish `ServiceRegistry` snapshot schema. |
| **[GAP-4]** | `StateManager` scope/state schema is referenced (`WORKFLOW`/`SERVICE`/`GLOBAL`/`SESSION`) but not defined as a serializable schema. | GAP | `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.2 | Publish `StateScope` and `StateRecord` schemas. |
| **[GAP-5]** | `RetryBudget` and `RootCauseAnalysis` schemas are referenced in Part 0/4 but not defined as published schemas. | GAP | `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.2 | Publish `RetryBudget` and `RootCauseAnalysis` schemas in Part 4 or Part 12. |
| **[GAP-6]** | 51 governance event payloads are enumerated by type in Part 13 but not individually JSON-schematized. | UNSPECIFIED | `Part13/events.md`; `Part13/13.13-Cross-References-and-ADR-Summary.md` | Publish individual payload schemas per governance event aggregate if machine-validable contracts are required. |
| **[GAP-7]** | `defaults.yaml`, environment YAML, and environment variable layer schemas are not fully enumerated. | UNSPECIFIED | `Part00/ARCHITECTURE_SPEC_PART0.md` §0.3.4; `Part01/ARCHITECTURE_SPEC_PART1.md` §1.10.1 | Publish full configuration layer schemas in Part 7. |
| **[GAP-8]** | `RequirementsSpec`, `TaskSpec`, `TaskDependency`, `EstimationSpec`, `RiskSpec`, `Criterion`, `CouncilDecisionRecord`, `HumanApprovalRecord` sub-schemas are referenced by PlanArtifact but not individually defined in published docs. | UNSPECIFIED | `Part05/ARCHITECTURE_SPEC_PART5.md` | Publish sub-schemas in Part 5 or Part 12. |
| **[GAP-9]** | `Runtime`, `Scheduler`, `Plugin`, `Message`, `ExecutionPlan`, `Checkpoint`, `HealthReport` schemas from Part 12 are referenced in TOC and component interfaces but not fully documented in this catalog. | GAP | `Part12/schemas.md` TOC; `Part12/components.md` | Full entries should be added to this catalog or a companion Part 12 schema reference. |
| **[GAP-10]** | `Event` schema (distinct from envelope) is listed in Part 12 `schemas.md` TOC but its field-level definition was not read during catalog construction. | GAP | `Part12/schemas.md` TOC | Read and catalog the Event schema body. |
| **[GAP-11]** | `BaseService`, `ServiceRegistry`, `ICoreComponent`, `ICoreManager`, `StateManager` are described in prose in Parts 0–1 but lack formal schema/interface contracts in Parts 1–13. | UNSPECIFIED | `Part00/ARCHITECTURE_SPEC_PART0.md`; `Part01/ARCHITECTURE_SPEC_PART1.md` | Publish formal interface contracts as schemas or IDL. |
| **[GAP-12]** | Part 11 conformance levels L8–L11 are referenced in Part 13 but their exact criteria are defined in Part 11, not Part 13. | DERIVED | `Part13/13.12-Governance-Invariants-and-Conformance.md`; Part 11 STEP07/STEP08 | Cross-reference Part 11 definitions when cataloging conformance-related schemas. |

---

## 11. Source Authority Notes

This catalog is a **reference document derived from Parts 0–13**. It is not itself an authoritative architecture Part. The following source documents were consulted:

- `Part00/ARCHITECTURE_SPEC_PART0.md` — terminology, principles, configuration model
- `Part01/ARCHITECTURE_SPEC_PART1.md` — kernel architecture, lifecycle events, KernelConfig interface
- `Part05/ARCHITECTURE_SPEC_PART5.md` — PlanArtifact and SDLC service contracts
- `Part12/schemas.md` — 18 core multi-agent collaboration schemas and schema governance model
- `Part12/events.md` — authoritative event envelope, 64+ event definitions, topic naming, delivery guarantees
- `Part12/components.md` — component interfaces, inputs/outputs, events
- `Part12/12.13-Cross-References-ADR-Summary.md` — Part 12 ADR index, maturity notes
- `Part13/schemas.md` — 14 governance schemas with JSON Schema definitions
- `Part13/components.md` — 16 governance component specifications with interfaces
- `Part13/events.md` — 51 governance events across 10 aggregates
- `Part13/13.12-Governance-Invariants-and-Conformance.md` — 20 invariants, conformance levels L8–L11
- `Part13/13.13-Cross-References-and-ADR-Summary.md` — cross-reference matrix, ADR summaries
- `C:\Development\AI-OS\config\app.yaml` — observed application configuration structure
- `C:\Development\AI-OS\config\global.yaml` — empty; no additional structure found

### Important Source Limitations

1. **Part 14 itself is not an authoritative source.** It is a catalog derived from Parts 0–13. Claims about schema versions, compatibility windows, and evolution rules are reconstructions unless the source Part explicitly states them.

2. **Event envelope authority is `Part12/events.md` §4**, not `Part12/schemas.md`. The `events.md` envelope defines `event_id` as ULID, not UUID; `produced_by.actor_kind` does not include `governance`; and `tenant_id` IS present in the authoritative envelope example. This catalog corrects earlier reconstructions to match the authoritative source.

3. **Part 13 governance schemas are EXISTING** in `Part13/schemas.md` with full JSON Schema definitions. They are listed in §8 with a cross-reference index; implementers should consult `Part13/schemas.md` for field-level detail.

4. **Part 12 schema governance model** (`Part12/schemas.md` §§1–34) applies to schemas published in Part 12. Part 13 schemas are governed by Part 13's federated governance model. This catalog does not unilaterally extend Part 12 schema governance to Part 13.

5. **Conformance levels L8–L11** are defined in Part 11, not Part 13. Part 13 references them. This catalog cross-references Part 11 rather than redefining them.

---

## 12. Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-REF-v1.0-PART14 |
| **Classification** | Integration Contract Reference (derived, not authoritative) |
| **Change Control** | This document is a working reference. Updates must be traceable to changes in Parts 0–13. |
| **Distribution** | All AI-OS engineers, architects, reviewers, integration teams, Parts 14–15 implementers |
| **Supersedes** | Prior informal integration schema notes |
| **Review History** | v1.0.0 — Initial working draft (2026-08-11) |

**Usage Note:** Gaps identified in §10 must be resolved by publishing the missing schemas in their authoritative Parts before implementation. This catalog does not create schemas; it catalogs what exists and identifies what is missing.

---

*End of Part 14 Integration Schema Catalog*
