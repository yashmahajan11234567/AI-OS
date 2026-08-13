# AI-OS Part 14 — Event Catalog (Integration-Relevant Events)

**Document:** Part 14 Integration Architecture — Event Catalog
**Status:** v1.3 (final production pass — ADR-authority qualification, source-specific schema authority, explicit envelope three-way distinction, universe non-merge guard)
**Layer:** Cross-cutting event catalog / integration surface
**Source documents reviewed:** Part 0 (principles), Part 1, Part 2 (Event System), Part 3, Part 4 (`ARCHITECTURE_SPEC_PART4A.md` §4.3.10/§4.4.9), Part 5, Part 6 (`interfaces.md`), Part 7, Part 8, Part 9, Part 12 (`events.md` §22 catalog + §4 envelope, `components.md`, `adrs.md`, `schemas.md`, `context.md`, `dependency-map.md`), Part 13 (`governance-events.md` §15, `components.md`, `adrs.md`, `schemas.md`), Part 14 (`components.md`, `interfaces.md`, `adrs.md` §0, `schemas.md` §1.1/§11), `Common/ARCHITECTURAL_INVENTORY.md`, `Common/MASTER_ARCHITECTURE_ROADMAP.md`, `project-knowledge/ARCHITECTURE_DECISIONS.md`.
**This document is a CATALOG, not a redesign.** It inventories events defined across Parts 0–13 and classifies them. It does **not** introduce a new bus, broker, protocol, delivery guarantee, ordering guarantee, exactly-once semantic, replay mechanism, or event type. Where sources conflict, the conflict is recorded as UNRESOLVED/GAP/CONFLICT — never resolved by invention here.

---

## 0. Classification Scheme (mandatory for every entry)

Per the review brief, each event is tagged with exactly one primary classification:

| Tag | Definition | How it appears in this catalog |
|---|---|---|
| **EXISTING** | The event type is defined and registered in an authoritative source (Part 2 `EventType` enum, Part 12 §22 catalog, or Part 13 §15 catalog). Canonical name + semantics established. | Catalogs A (§5, Part 2), B (§6, Part 12), C (§7, Part 13). |
| **DERIVED** | A name appears in a source that is *implied by or a variant of* an EXISTING contract (e.g., an implementation-inventory alias for a canonical type). Existence is inferable; the precise contract is not independently ratified. | §8. |
| **UNSPECIFIED** | A name is referenced (e.g., in `components.md` "Events published" lists) with **no schema, payload, producer, or consumer contract** anywhere authoritative. A name without a contract. | §8. |
| **GAP** | A contract that the sources *assume exists* but is missing/divergent (e.g., the two envelope specs disagree; an ADR requires an event type that no registry contains). | §9, §10. |
| **PROPOSED** | Explicitly named as planned/future in prose but without a ratified contract (Part 2 roadmap families, resolver interfaces). | §10.1. |
| **FUTURE** | Out of scope for v1.0 by explicit decision (e.g., distributed EventBus v2.0). | §10.2. |
| **CONFLICT** | Two or more *authoritative* sources document the same conceptual event with **mutually inconsistent identifiers or contracts** (e.g., Part 2 `SCREAMING_SNAKE_CASE` vs Part 4/6/12/13 `PascalCase+Event` vs Part 12's *own* internal verb-object PascalCase that contradicts its dotted §22 catalog). The divergence is recorded, not normalized or resolved here. | §8b (Catalog E). See also §4.1. |

> A single *concept* (e.g., "a workflow step finished") may appear as multiple **EXISTING** types across registries with different names (`WORKFLOW_STEP_COMPLETED` in Part 2, `workflow.step.completed` in Part 12). These are cataloged separately and cross-linked in §4; this is an overlapping-universe condition, not a duplicate. Where the *same concept* is given **inconsistent names by authoritative sources with no mapping**, it is additionally flagged **CONFLICT** in §8b.

---

## 1. Scope Rule and "Do Not Invent" Boundaries

- **Inventories only.** Every event name below traces to a cited source line. No event type, guarantee, broker, fabric, or semantic is introduced.
- **Envelope.** Two envelope specifications exist in the spec set (Part 2 §2.2.1 and Part 12 §4 / Part 14 `schemas.md` §1.1 `EVENT-ENVELOPE-v1`). Both are quoted verbatim in §3. Their divergence is recorded as GAP-ENV (§9.1). This catalog does not merge them.
- **Transit.** The only transport established in Parts 0–13 is the **in-process, in-memory EventBus** (Part 2 §2.1.4, `UNRES-EVT-DIST-001`). Distributed transport is FUTURE (§10).
- **Commands vs events.** Synchronous request/response control surfaces (`INT-WF-CTRL-001`, Part 4 `StateTransitionRequest`/`StateTransitionRequestEvent`, parts of `INT-HUMAN-001`) are **commands**, not events. They are listed in §11 and explicitly excluded from the event counts.
- **Unverified fields** (per-type payload schemas for Part 2 types, per-type producers for some types) are marked **UNSPECIFIED**, never guessed.
- **No other file is modified** by this review.

---

## 2. Source Hierarchy (which source wins on conflict)

1. **ADRs** — normative **only where the ADR is `Accepted`/`Active`/`Experimental` and within its stated scope**. Source of status: `project-knowledge/ARCHITECTURE_DECISIONS.md` (core ADRs 001–016 stated "currently Active", line 709); Part 12 `adrs.md` status table (P12-ADR-001..010 all **Accepted**, lines 522–531); Part 13 `adrs.md` status table (P13-ADR-001..010 all **Draft**, lines 790–799). Both Part 12 §3 and Part 13 §5 define the lifecycle `Draft → Proposed → Accepted`. **`Draft`/`Proposed` ADRs (e.g., all ten P13-ADRs) are under discussion and are NOT mandatory architecture** — they are recorded as context, never treated as ratified constraints. Authoritative normative ADRs used as constraints in this catalog: ADR-001 (event-first, Active), ADR-008 (correlation/causation/immutability, Active), ADR-009 (failure-as-event, Active), ADR-011 (versioning, Active), ADR-013 (extension governance, Active), and the Accepted P12-ADR-001..010.
2. **Part 2 Event System** — authoritative for the *transport* (EventBus), the *base contract*, the *118 enumerated EventTypes* (spec prose claims 97 — see GAP-SPEC-COUNT §9.12), ordering/delivery/retry/failure mechanics, and the `EventType` naming/registration rules (INV-ET-002 SCREAMING_SNAKE_CASE).
3. **Part 12 `events.md`** — authoritative for the *lowercase-dotted multi-agent event taxonomy* (104 types, §22) and its governance/lifecycle/versioning model; its §4 envelope is canonical for dotted events.
4. **Part 13 `governance-events.md`** — authoritative for the *`governance.*` taxonomy* (51 types, §15).
5. **Part 4 `ARCHITECTURE_SPEC_PART4A.md`** — authoritative *within its kernel/state scope* for its own `PascalCase+Event` vocabulary (`KernelLifecycleEvent`, `StateTransitionCommittedEvent`, …). It is **not** one of the three registries in item 2–4 and conflicts with Part 2 naming for overlapping concepts; treated as CONFLICT (§8b).
6. **Part 14 `schemas.md` (`EVENT-ENVELOPE-v1` §1.1)** — **source-specific** authority only: it is the *integration* envelope, and its authority is **derived** — it references the Part 12 §4 envelope as canonical and cites the Part 2 EventBus as transport. It is therefore normative *for Part 14 integration payloads*, **not** a universal envelope for the Part 2 enum or an independent author of envelope semantics. Do not treat `schemas.md` §11 as authoritative where it disagrees with Part 12 §4 (see GAP-P14-ENV §9.13). ⚠️ Its §11 "source authority note" contains two errors corrected in §3.1/§9.13.
7. **`ARCHITECTURAL_INVENTORY.md`** (implementation snapshot, 2026-07-28) — used **only** to surface DERIVED/UNSPECIFIED names; it is explicitly *not* a specification source (Part 14 `components.md` §1.1).
8. **Per-part component docs** (`Part14/components.md`, `interfaces.md`, Part 12 `components.md`, Part 13 `components.md`) — used to **derive** producer/consumer ownership for catalog rows, clearly labelled as derived.

---

## 3. Defined Cross-Cutting Contracts (referenced by every event)

These are established by the cited sources. They are the shared "how events behave" baseline. Where Part 2 and Part 12 disagree, the disagreement is flagged inline and in §9.

### 3.1 Envelope — two coexisting specifications (GAP-ENV)
**Part 2 §2.2.1 `Event` base contract (transport-level):**
`eventId` (UUIDv7, RFC 9562), `eventType` (closed enum), `eventVersion` (SemVer MAJOR.MINOR.PATCH), `timestamp`, `timestampMonotonic`, `correlationId` (UUID), `causationId` (UUID\|null), `source` (ComponentIdentity), `target`, `priority` (CRITICAL=0 / HIGH=1 / NORMAL=2 / LOW=3 / BACKGROUND=4), `category` (SYSTEM / CONTROL / DATA / AUDIT / DIAGNOSTIC), `payload` (immutable value object), `checksum`. Immutable after construction (INV-EVT-001).

**Part 12 §4 / Part 14 `schemas.md` §1.1 `EVENT-ENVELOPE-v1` (integration-level):**
`event_id` (ULID, per Part 12 §4 example line 190), `event_type` (string, lowercase dotted), `event_version` (integer), `produced_at`, `produced_by{actor_id,actor_kind,actor_role}`, `partition_key`, `correlation_id`, `causation_id`, `tenant_id` (present in authoritative Part 12 §4 line 202), `priority` (P0\|P1\|P2\|P3), `trace{trace_id,span_id,parent_span_id}`, `schema_ref` (`<type>@v<major>`), `payload`, `metadata{redacted_fields,classification,encrypted_fields}`, `security{signing_key_id,signature,previous_signature}`.

**Distinction (rubric #4):** the two blocks above are *source-defined* envelopes — each is quoted from its own authoritative source (Part 2 §2.2.1; Part 12 §4 / Part 14 `schemas.md` §1.1). This catalog's §4 reconciliation map and §13 summary are *derived reconciliation*, not a third envelope, and make no new envelope claim. The remaining disagreement between the two source envelopes is an *unresolved conflict* (**GAP-ENV**, §9.1) — recorded, not resolved.

**Conflict:** field names, ID format (Part 2 `eventId` = UUIDv7 vs Part 12 `event_id` = ULID), priority encoding (5-level vs 4-level), and the presence of `partition_key`/`schema_ref`/`tenant_id`/`security` (Part 12) vs `target`/`checksum`/`category` (Part 2) are mutually inconsistent. Recorded as **GAP-ENV** (§9.1). Neither is "the" envelope for all 273 cataloged types.

> **⚠️ Part 14 internal inconsistency (schemas.md §11).** `schemas.md` §11 states the Part 12 §4 envelope "does not include `tenant_id`" and "`produced_by.actor_kind` does not include `governance`." Verification against the *authoritative* Part 12 §4 (read directly, lines 196/202) shows **`tenant_id` IS present** in the Part 12 envelope example, and `actor_kind` enumerates `agent|council|workflow|runtime|scheduler|tool|system` (no `governance`, which is correct). So schemas.md §11's `tenant_id` claim is **wrong**; this catalog follows the authoritative Part 12 §4 and records the discrepancy as GAP-P14-ENV (§9.13). Do not propagate the schemas.md §11 error.

### 3.2 Immutability (ADR-008, INV-EVT-001, INV-ENV-002)
Events are immutable value objects; mutation is prohibited; replay creates a **new** `eventId` preserving `correlationId`/`causationId` (INV-EVT-003a). All listed events are immutable facts, not commands.

### 3.3 Correlation & Causation (ADR-008, Part 2 §2.2.1, INV-EVT-004/005)
- `correlationId` **MUST** be present on every event (root events generate a new one; descendants propagate).
- `causationId` **MUST** be the `eventId` of the directly-causing event, or `null` only for root events.
- The EventBus enforces *causation order* as a **publisher contract** (INV-ORD-003): it does not reorder by causality itself; publishers set `causationId` correctly.
- ADR-008 mandates these fields on **every event crossing integration boundaries**, including converted external formats (webhooks, MCP).

### 3.4 Delivery Semantics (Part 2 §2.4.1, INT-EVT-BUS-001)
- **At-least-once is the default.** At-most-once is a *configured* option, not a default.
- `publish()` returns `ACCEPTED` / `REJECTED_VALIDATION` / `REJECTED_CAPACITY` / `REJECTED_SHUTDOWN` / `REJECTED_DUPLICATE`. Invalid events rejected synchronously; handlers run on the dispatch loop, never inside `publish()`.
- There is **no exactly-once** guarantee anywhere in Parts 0–13. Exactly-once is achieved only at the application layer via idempotent handlers (§3.6). (Do not describe any listed event as "exactly-once".)

### 3.5 Ordering Guarantees (Part 2 §2.4.9, INV-EB-014)
- **Priority order:** CRITICAL → HIGH → NORMAL → LOW → BACKGROUND within a dispatch cycle. Priority does **not** preempt in-flight handlers.
- **Correlation order:** events sharing `correlationId` dispatched FIFO by `timestampMonotonic` within priority.
- **Causation order:** `B.causationId == A.eventId` ⇒ A before B (publisher-enforced).
- **Per-subscriber order:** sequential by HandlerPriority, no reordering.
- **Global total order** is reproducible given identical input + timing (deterministic tie-break by `eventId`).
- ⚠️ Part 12 §29 states ordering is "strict within `partition_key`, unordered across partitions." This is **functionally compatible** with Part 2's correlation-order but uses a different primitive (`partition_key` vs `correlationId`+`timestampMonotonic`). See GAP-ORDER (§9.2).

### 3.6 Idempotency (Part 2 §2.4.7, INT-EVT-BUS-001, Part 12 §18/§30)
- `eventId` (or optional `idempotencyKey`) deduplication at the bus; handlers MUST be idempotent.
- Part 12 adds a **24h `event_id` dedup window** + `correlation_id` grouping + version-stamped projection updates. Reconcile as GAP unless confirmed identical (§9.3).

### 3.7 Retry (Part 2 §2.4 internal queues, INT-EVT-BUS-001)
- Publish queue (default cap 10,000) → Dispatch queue (priority-sorted) → Retry queue (default cap 1,000, priority+nextRetryTime) → Dead Letter queue (default cap 10,000, DROP_OLDEST).
- Per-subscription `retryPolicy` (default = bus default); `REJECTED_CAPACITY` applies backpressure to publisher.
- Part 12 states "5 attempts default, 10 for terminal-state events, exponential backoff 200ms→64s, then DLQ." Recorded as GAP-RETRY (§9.4) pending reconciliation of the two retry models.

### 3.8 Failure Handling / Dead Letter (ADR-009, Part 2 §2.4.1, INT-EVT-BUS-001)
- Failures are **events**, never exceptions crossing boundaries (ADR-009). `on_error()` emits failure events; no exceptions propagate.
- Failed deliveries → retry queue → dead letter after exhaustion. Recursive-event detection is per-`correlationId` (default max depth 50).
- Part 12 names per-family DLQ topics (`workflow.dlq`, `council.dlq`, …, `governance.dlq`). Part 2 models a single DLQ with DROP_OLDEST. GAP-DLQ (§9.5).

### 3.9 Versioning (ADR-011, Part 2 §2.3.4, Part 12 §27)
- SemVer. **MAJOR** = breaking (field removed/retyped/semantic change) → consumers migrate. **MINOR** = backward-compatible addition (new optional field / new enum value). **PATCH** = doc/fix.
- Part 2 EventType version is `eventVersion` (MAJOR.MINOR.PATCH); Part 12 uses `event_version` integer + `schema_ref` `<type>@v<major>`. Same GAP-ENV family.

### 3.10 Compatibility (Part 2 §2.3.6, Part 12 §27, INV-ET-005)
- Backward: new schema reads old events. Forward: old schema reads new (unknown optional fields ignored). Breaking: MAJOR bump + migration path.
- Part 2 INV-ET-005: strict schema validation **mandatory in production**.

### 3.11 Security / Trust (ADR-008, P12-ADR-008, Part 12 §20, INT-GOV-EVENT-001)
- Events carry immutable audit trails; PII/secrets redacted in payloads (Part 12 `metadata.redacted_fields`); `secret`-tier not broadcast to unauthorized subscribers.
- **Part 2 base contract has NO signing/ACL field** — signing lives only in the Part 12 `security.*` envelope block. GAP-SEC (§9.6).
- Governance events (`governance.*`, Part 13) are signed, minimum `confidential`, ACL-gated subscription.

### 3.12 Unknown / Unrecognized Events (Part 2 §2.2.1 closed enum; Part 12 §27)
- Part 2: `EventType` is a **closed enum**; unknown types are rejected at registration/publish.
- Part 12: unknown *fields* within a known type are ignored (forward compat); unknown *types* rejected at admission.
- ⚠️ ADR-013 lists "custom events" as a **permitted extension point** — this appears to conflict with Part 2's *closed* enum + "late registration PROHIBITED in v1.0" (INV-ET-003). GAP-EXT (§9.7).

### 3.13 Replay (Part 12 §16.10, §18–§19, §29; Part 2 §2.4)
- Replay is an **explicit primitive** in Part 12: the WORM log is replayable from any offset to reconstruct state (Part 12 §4.6, line 107: "Replay is a primitive, not an afterthought"). `system.replay.started` / `system.replay.completed` (P1, persisted) are **ratified Part 12 events** (Catalog B §6.12, §22 rows 16.10/16.11) carrying `replay_id`, `from_offset`, `to_offset`, `events_replayed`, `duration_ms`.
- Replayed historical events are tagged `metadata.replay = { from_offset, replay_id }` (Part 12 §30, line 1657); a `causation_id` DAG is preserved across replay.
- **Part 2 scope:** replay is NOT defined as an EventBus operation in Part 2; Part 2's durability/replay story is limited to the in-memory bus + DLQ. The replay guarantee is therefore **source-supported only for Part 12 dotted events**, not for the Part 2 enum (GAP-ENV family). No cataloged event is described as "replayable" unless its source says so.

### 3.14 Partitioning (Part 12 §4, §29; Part 2 §2.4.9)
- **Part 12:** every event carries a `partition_key` (the aggregate ID — `workflow_id`, `session_id`, `council_session_id`, `agent_id`, `policy_id`, …). Ordering is **strict within a partition** (by `produced_at`), **unordered across partitions** (Part 12 §29 lines 2181–2209, broadcast routing §3). `system.*` uses a synthetic partition.
- **Part 2:** does **not** define `partition_key`. Ordering is by priority + `correlationId` + `timestampMonotonic` (§3.5), which is a *different* primitive. Cross-partition (Part 2: cross-`correlationId`) ordering is non-deterministic in both models.
- **Source-supported claim only:** "per-aggregate ordered, cross-aggregate unordered" is a Part 12 guarantee; it is **not** a Part 2 guarantee. Do not assert partitioning for the Part 2 enum.

### 3.15 Source-Supported Guarantee Audit (rubric #5 — only retained claims)
Every guarantee word used in this catalog, with its sole authoritative basis. **No guarantee is asserted for a registry whose source does not state it.**

| Guarantee | Asserted for | Source | Notes |
|---|---|---|---|
| **at-least-once** (default) | Part 2 enum; Part 12 dotted | Part 2 §2.4.1; Part 12 §18 | At-most-once is *configured option* only. |
| **exactly-once** | **NONE** | — | Does not exist anywhere in Parts 0–13. Achieved only via idempotent handlers at app layer (§3.6). No event is labelled exactly-once. |
| **ordering — priority** | Part 2 enum | Part 2 §2.4.9 (CRITICAL→BACKGROUND) | Does not preempt in-flight. |
| **ordering — correlation FIFO** | Part 2 enum | Part 2 §2.4.9 (by `timestampMonotonic`) | |
| **ordering — causation** | Part 2 enum (publisher-enforced) | INV-ORD-003 | Bus does not reorder by causality. |
| **ordering — per-partition** | Part 12 dotted | Part 12 §29 | **Not** a Part 2 guarantee. |
| **global total order** | Part 2 enum (single process) | Part 2 §2.4.9 | Reproducible given identical input+timing; deterministic tie-break by `eventId`. Single-process only. |
| **replay** | Part 12 dotted (`system.replay.*`, log replay) | Part 12 §16.10, §29, §30 | **Not** a Part 2 guarantee (GAP-ENV). |
| **DLQ** | Part 2 (single) + Part 12 (8 topics) + Part 13 (`governance.dlq`) | Part 2 §2.4.1; Part 12 §19; Part 13 | Single-vs-many unreconciled (GAP-DLQ §9.5). |
| **retry** | Part 2 (queue model) + Part 12 (5/10 attempts, 200ms→64s) | Part 2 §2.4; Part 12 §18 | Two models unreconciled (GAP-RETRY §9.4). |
| **partitioning** | Part 12 dotted (`partition_key`) | Part 12 §4, §29 | **Not** a Part 2 concept. |
| **idempotency** | Part 2 (`eventId`/`idempotencyKey`) + Part 12 (24h `event_id` dedup + `correlation_id`) | Part 2 §2.4.7; Part 12 §18/§30 | TTL conflict unreconciled (GAP-DEDUP §9.3). Replayed events tagged `metadata.replay` (Part 12 §30). |

---

## 4. Reconciliation Map — three event universes

| Concept | Part 2 (enum) | Part 12 (dotted) | Part 13 | Notes |
|---|---|---|---|---|
| Kernel ready | `KERNEL_READY` | — | — | Part 2 only |
| Service lifecycle | `SERVICE_STARTED`/`STOPPED`/`DEGRADED`/`FAILED` | — | — | Part 2 only |
| Resource quota | `RESOURCE_ALLOCATED`/`RELEASED`/`EXHAUSTED`, `QUOTA_EXCEEDED` | `system.*` (broker/store) | — | Part 2 only; Part 12 has no resource events |
| Config change | `CONFIGURATION_FROZEN`/`CHANGED` | `system.config.changed` | — | near-equivalent, different name |
| Workflow start | `WORKFLOW_STARTED` | `workflow.lifecycle.started` | — | conceptual overlap |
| Workflow step done | `WORKFLOW_STEP_COMPLETED` | `workflow.step.completed` | — | conceptual overlap |
| Workflow cancel | `WORKFLOW_CANCELLED` (event) | — | — | command counterpart in §11 |
| Task done | `TASK_COMPLETED` | `delegation.task.completed` | — | conceptual overlap |
| Council decision | `COUNCIL_DECISION_FINALIZED` | `council.decision.published` | — | conceptual overlap |
| Memory stored | `MEMORY_STORED` | `knowledge.memory.written` | — | conceptual overlap |
| Skill executed | `SKILL_EXECUTED` | — | — | Part 2/impl only |
| Model routed | `MODEL_ROUTED`/`MODEL_FALLBACK` | `runtime.model.called` | — | conceptual overlap |
| Governance policy | — | — | `governance.policy.*` (16) | Part 13 only |
| Governance decision/authority/approval/risk/compliance/audit/control/agent/capability | — | — | 35 events | Part 13 only |
| Diagnostics/metrics/tracing | `METRIC_EMITTED`,`TRACE_SPAN_*`,`HEALTH_CHECK_*` | `monitoring.*` | — | conceptual overlap |

**Conclusion:** the three registries are **not a single set described three ways** — they are *partially overlapping* and *partially disjoint*. Part 2 covers kernel/service/resource/diagnostic lifecycle absent from Part 12; Part 13 covers governance absent from both; Part 12 covers multi-agent collaboration detail (delegation, communication, runtime streaming) largely absent from Part 2. This is recorded as **GAP-UNIVERSE** (§9.8) and is the single largest unresolved item for an integration catalog.

**Do-not-merge guard (rubric #3):** Part 2 (Transport/EventBus `SCREAMING_SNAKE_CASE`, 118), Part 4 (kernel/state `PascalCase+Event`, §8b E.1/E.2), Part 6 (capability-facade family *labels*, §8d.3), Part 12 (lowercase-dotted, 104), and Part 13 (governance `governance.*`, 51) are **five distinct event universes with incompatible identifiers and envelopes.** This catalog keeps them in separate catalogs (§5–§8d), cross-links overlapping *concepts* in §4, and **never merges** them into one unified type set or one envelope. Reconciling them is an ADR-level decision (GAP-UNIVERSE) this catalog cannot make.

### 4.1 Naming-Convention Conflict — five schemes (A–E), preserved without normalization (rubric #2)

The architecture uses **inconsistent naming conventions across authoritative sources**, and this catalog does **NOT** silently normalize them. All five of the following are real and are kept distinct:

| Scheme | Example | Authoritative source(s) | Used for |
|---|---|---|---|
| **A. `SCREAMING_SNAKE_CASE`** (closed enum, INV-ET-002) | `MEMORY_STORED`, `WORKFLOW_STARTED`, `ACCESS_DENIED` | Part 2 §2.3.1 (canonical transport enum) | Kernel / service / resource / audit / diagnostic lifecycle |
| **B. lowercase-dotted** | `workflow.step.completed`, `governance.policy.created` | Part 12 §22 (canonical dotted catalog), Part 13 §15 | Multi-agent collaboration + governance |
| **C. `PascalCase` + `Event` suffix** | `KernelLifecycleEvent`, `StateTransitionCommittedEvent`, `PolicyCreated` | Part 4 §4.3.10/§4.4.9; `interfaces.md` §2.5/§2.7; Part 13 line 1013 (legacy shorthand) | Kernel/state lifecycle (Part 4), auth/security interfaces, governance legacy labels |
| **D. verb-object `PascalCase` (no `Event`)** | `TaskDelegated`, `SessionRequested`, `AgentMatching`, `WorkflowStarted`, `CapabilityRegistered` | Part 12 *own* `components.md`/`adrs.md`/`README`/`12.1`/`context.md` §557 — **contradicts Part 12's own §22 dotted catalog** | Part 12 component prose / schemas.md "Related Events" |
| **E. `PascalCase` no-suffix lifecycle (FROZEN authoritative)** | `CoreComponentInitialized`, `CoreComponentShutdown`, `ServiceHealthChanged`, `ServiceFailed` | Part 3 (FROZEN — authoritative SoT, §3.4, lines 178–179, 386–396) — **collides with Part 2 `SCREAMING_SNAKE_CASE`** for identical concepts | Part 3 Core Component / Service lifecycle |

**Key integrity points (do not normalize):**
- Scheme A and Scheme B are *coexisting, intentional* registries (Part 2 vs Part 12) and are cataloged separately (§5, §6). Neither is "wrong."
- Scheme C (Part 4 / interfaces / Part 13 legacy) **collides** with Scheme A for the *same concepts* (e.g., `KernelLifecycleEvent` ≈ `KERNEL_*`) and with Scheme B for governance (e.g., `PolicyCreated` ≈ `governance.policy.created`). These collisions are **CONFLICT** (§8b), not aliases to be merged.
- Scheme D is an **internal contradiction inside Part 12**: its prose/component docs (`TaskDelegated`, `SessionRequested`) use PascalCase while its normative §22 catalog uses dotted (`delegation.task.dispatched`, …). The §22 catalog wins as canonical for Part 12; the PascalCase forms are CONFLICT (§8b E.5).
- `integrations.md` FI-005 frames these as "not in Part 2 §2.3.1" — true for B/C/D, but several (the dotted Part 12 events) **do** exist in their own registry; FI-005's framing is therefore partial. This catalog records each name against its *true* authoritative source.

---

## 5. Catalog A — Part 2 Canonical EventType Enum (118 EXISTING)

**Authority:** Part 2 §2.3.1 (closed enum, registered in `EventTypeRegistry` before bus init, INV-ET-003). **Classification of all 118 enumerated types = EXISTING.** ⚠️ Per `GAP-SPEC-COUNT` (§9.12), Part 2 §2.3.1 explicit enumeration contains **118** values (verified by reading lines 267–395), but the prose at Part 2 line 398 states "The above defines **97** canonical event types." This catalog lists all 118 actually-enumerated values; the "97" figure is treated as a **spec error**, not as authority to drop 21 types. Per-type `payload`/`schema` is **UNSPECIFIED** at the type level (only the registration *template* in §2.3.5 exists; per-type payload schemas are not defined in Part 2). Producer/Consumer columns are **DERIVED** from component ownership in Part 14 `components.md` (clearly labelled).

**Family-level established attributes (apply to all 118):** Delivery = at-least-once default; Ordering = priority + correlation + causation (§3.5); Idempotency = `eventId` dedup + idempotent handlers (§3.6); Retry = retry queue → DLQ (§3.7); Failure = event-not-exception (ADR-009); Versioning = SemVer, MAJOR=breaking (§3.9); Compatibility = backward/forward per §3.10; Correlation/Causation = mandatory (ADR-008, INV-EVT-004/005); Security = envelope-level signing **not defined in Part 2** (GAP-SEC); ADRs = ADR-001, ADR-008, ADR-009, ADR-011; Source = Part 2 §2.3.1.

### 5.1 SYSTEM (17)
`KERNEL_INITIALIZATION_STARTED`, `KERNEL_READY`, `KERNEL_SHUTDOWN_STARTED`, `KERNEL_TERMINATED`, `KERNEL_INITIALIZATION_FAILED`, `KERNEL_FATAL_ERROR`, `CORE_COMPONENT_INITIALIZED`, `CORE_COMPONENT_SHUTDOWN`, `CORE_COMPONENT_DEGRADED`, `CORE_COMPONENT_FAILED`, `CORE_MANAGER_INITIALIZED`, `CORE_MANAGER_SHUTDOWN`, `CORE_MANAGER_DEGRADED`, `CORE_MANAGER_FAILED`, `HEARTBEAT`, `CONFIGURATION_FROZEN`, `CONFIGURATION_CHANGED`.
- Producer (derived): HermesKernel / Core Components / Core Managers / ConfigurationManager. Consumers (derived): ServiceRegistry, HealthManager, ObservabilityManager, all.
- Priority: CRITICAL (kernel/lifecycle/fatal), NORMAL (heartbeat), per Part 2 §2.2.3 default mapping.

### 5.2 CONTROL (26)
`WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `WORKFLOW_PAUSED`, `WORKFLOW_RESUMED`, `WORKFLOW_CANCELLED`, `WORKFLOW_STEP_STARTED`, `WORKFLOW_STEP_COMPLETED`, `WORKFLOW_STEP_FAILED`, `WORKFLOW_STEP_RETRIED`, `WORKFLOW_STEP_SKIPPED`, `WORKFLOW_CHECKPOINT_CREATED`, `WORKFLOW_CHECKPOINT_RESTORED`, `TASK_CREATED`, `TASK_ASSIGNED`, `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_RETRIED`, `TASK_CANCELLED`, `TASK_DEPENDENCY_RESOLVED`, `RETRY_BUDGET_EXHAUSTED`, `ROOT_CAUSE_ANALYZED`, `RECOVERY_ACTION_DISPATCHED`, `RECOVERY_ACTION_COMPLETED`, `RECOVERY_ACTION_FAILED`.
- Producer (derived): WorkflowManager, RootCauseAnalyzer, RetryManager. Consumers (derived): PlanningService, CodingService, downstream SDLC services, ObservabilityManager.
- Note: `WORKFLOW_PAUSED/RESUMED/CANCELLED` are the **event** counterparts of the **commands** in §11.

### 5.3 DATA (16)
`STATE_CHANGED`, `STATE_SNAPSHOT_CREATED`, `STATE_RESTORED`, `ARTIFACT_CREATED`, `ARTIFACT_UPDATED`, `ARTIFACT_DELETED`, `CHECKPOINT_CREATED`, `CHECKPOINT_RESTORED`, `CHECKPOINT_PRUNED`, `MEMORY_STORED`, `MEMORY_RETRIEVED`, `MEMORY_UPDATED`, `MEMORY_CONSOLIDATED`, `MEMORY_PRUNED`, `CONTEXT_ASSEMBLED`, `CONTEXT_COMPRESSED`.
- Producer (derived): StateManager, MemoryManager, ContextManager, WorkflowManager (artifacts). Consumers (derived): Prompt Builder, MemoryService, ObservabilityManager.

### 5.4 AUDIT (36)
`PLANNING_REQUESTED`, `PLANNING_COMPLETED`, `PLANNING_FAILED`, `PLAN_REJECTED`, `CODE_GENERATED`, `CODING_COMPLETED`, `CODING_FAILED`, `CODE_REVIEW_REQUESTED`, `REVIEW_STARTED`, `REVIEW_APPROVED`, `REVIEW_REJECTED`, `REVIEW_FAILED`, `SECURITY_ISSUE_FOUND`, `PERFORMANCE_ISSUE_FOUND`, `TESTS_GENERATED`, `TESTS_PASSED`, `TESTS_FAILED`, `TESTING_COMPLETED`, `TESTING_FAILED`, `DEPLOYMENT_REQUESTED`, `DEPLOYMENT_STARTED`, `DEPLOYMENT_COMPLETED`, `DEPLOYMENT_FAILED`, `DEPLOYMENT_ROLLED_BACK`, `COUNCIL_CONVENED`, `COUNCIL_PROPOSAL_SUBMITTED`, `COUNCIL_VOTE_CAST`, `COUNCIL_CONSENSUS_REACHED`, `COUNCIL_DISSENT_REGISTERED`, `COUNCIL_DECISION_FINALIZED`, `AI_AGENT_TASK_REQUESTED`, `AI_AGENT_TASK_COMPLETED`, `AI_AGENT_TASK_FAILED`, `AI_AGENT_AUDIT_EMITTED`, `FINAL_JUDGE_DECISION`, `HUMAN_ESCALATION_REQUIRED`.
- Producer (derived): the 8 Engineering Services, CouncilService, AIAgencyService, HumanInteractionService (per `interfaces.md` §2.15). Consumers (derived): WorkflowManager, downstream services, governance, ObservabilityManager.
- These are "kernel-governed" (Part 2 §2.3.1 justification) — emission/subscription/correlation mandated by Part 0 Principles 3/6/7.

### 5.5 DIAGNOSTIC (23)
`METRIC_EMITTED`, `TRACE_SPAN_STARTED`, `TRACE_SPAN_ENDED`, `HEALTH_CHECK_PASSED`, `HEALTH_CHECK_FAILED`, `SERVICE_STARTED`, `SERVICE_STOPPED`, `SERVICE_DEGRADED`, `SERVICE_FAILED`, `RESOURCE_ALLOCATED`, `RESOURCE_RELEASED`, `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED`, `SKILL_EXECUTED`, `SKILL_FAILED`, `MCP_TOOL_CALLED`, `MCP_TOOL_SUCCEEDED`, `MCP_TOOL_FAILED`, `MODEL_ROUTED`, `MODEL_FALLBACK`, `PROMPT_TEMPLATE_RENDERED`, `TOKEN_BUDGET_EXCEEDED`, `PERSONA_OVERRIDE_APPLIED`.
- Producer (derived): ObservabilityManager, HealthManager, SkillService/MCPService, LLMManager/ModelRouter, ToolManager. Consumers (derived): ObservabilityManager, dashboards, audit.

> **118 EXISTING types cataloged** (17+26+16+36+23). Payload/schema per type = UNSPECIFIED (Part 2 defines only the registration template, §2.3.5). ADR linkage: ADR-001/005/008/009/011/012. The Part 2 prose "97" count (line 398) is inconsistent with its own enumeration (118) — recorded as GAP-SPEC-COUNT (§9.12).

---

## 6. Catalog B — Part 12 Lowercase-Dotted Events (104 EXISTING)

**Authority:** Part 12 `events.md` §22 catalog (verified Total = **104**, line 1886). **Classification of all 104 = EXISTING** (ratified + registered). Per-event attributes below are taken from Part 12; where Part 12 gives a family-level rule, it is stated once and rows cite it. "Components/Interfaces/ADRs" list `Not specified per type in Part 12` when Part 12 does not define them (Part 14 `components.md`/`interfaces.md` are used only to *derive* ownership, labelled).

**Family baseline (all 104):** Delivery = at-least-once (best-effort P3/ephemeral); Idempotency = `event_id` dedup (24h) + `correlation_id` + version-stamped projections; Retry = 5 default / 10 terminal, exp backoff 200ms→64s, then DLQ (Part 12 §18) — *see GAP-RETRY*; Failure = outbox + DLQ + cascade (Part 12 §19); Versioning = `<major>.<minor>` (Part 12 §27); Compatibility = backward/forward (§27); Correlation/Causation = mandatory (§30, ADR-008); Security = signed + classified (§20, GAP-SEC); ADRs = P12-ADR-001..010, ADR-008/009/011; Source = Part 12 `events.md` §22.

### 6.1 Lifecycle (10)
| FQN | Meaning | Producer | Consumers | Priority | Ordering key | Security |
|---|---|---|---|---|---|---|
| `agent.lifecycle.registered` | Agent registered | Agent Manager | Directory, Council Seat Allocator, Workflow, Observability | P2 | `agent_id` | internal; signed |
| `agent.lifecycle.deregistered` | Agent retired | Agent Manager / Admin | Directory, Council Queue, Workflow, Observability | P1 | `agent_id` (after final delegation) | confidential; not user-broadcast |
| `agent.lifecycle.heartbeat` | Liveness ping | Agent supervisor | Health Monitor, Seat Allocator, Workflow | P3 | `agent_id` | internal; signed |
| `workflow.lifecycle.started` | Workflow began | Workflow Engine | Council, Memory, Observability, Billing | P1 | `workflow_id` (first) | signed; tenant-classified |
| `workflow.lifecycle.completed` | Workflow finished | Workflow Engine | Memory, Council, Billing, Observability | P1 | `workflow_id` (last) | signed; reproducible |
| `council.lifecycle.convened` | Council called | Council Orchestrator | Workflow, Observability, Memory | P1 | `council_session_id` (first) | signed; members internal |
| `council.lifecycle.dissolved` | Council concluded | Council Orchestrator | Workflow, Memory, Billing | P1 | `council_session_id` (last) | signed; `decision_ref` pointer |
| `context.lifecycle.snapshot` | Context snapshot | Context Manager | Memory, Replay | P2 | `context_id` (monotonic) | blob encrypted; `hash` integrity |
| `tool.lifecycle.registered` | Tool registered | Tool Registry | Workflow, Security, Observability | P2 | `tool_id` | risk_class confidential |
| `tool.lifecycle.deprecated` | Tool deprecated | Tool Registry / Security | Workflow, Council, Observability | P0 if critical else P1 | `tool_id` | critical→review |

*Payload/schema:* per Part 12 §5 (e.g., `agent.lifecycle.registered` carries `agent_id,name,version,capabilities,model,policy_profile,registered_at`); full field lists in Part 12 §5. *Components/Interfaces/ADRs:* Not specified per type in Part 12 (derived: from Part 14 `components.md` 2.3.7 AgentManager, 2.3.1 WorkflowManager).

### 6.2 Workflow (10)
`workflow.step.scheduled`, `workflow.step.started`, `workflow.step.completed`, `workflow.step.failed`, `workflow.step.retried`, `workflow.step.skipped`, `workflow.step.halted`, `workflow.artifact.published`, `workflow.branch.evaluated`, `workflow.dlq.entry`.
- Ordering key = `workflow_id`; `scheduled`→`started`→`completed`/`failed`→(`retried`/`skipped`); `halted` supersedes pending `scheduled`; `dlq.entry` per `workflow_id`, read-restricted.
- Security: `step.failed` redaction enforced; `step.halted` confidential + audit-logged; `artifact.published` visibility governs access.

### 6.3 Council (10)
`council.motion.filed`, `council.debate.opened`, `council.debate.turn`, `council.debate.closed`, `council.vote.cast`, `council.vote.recalled`, `council.decision.published`, `council.seat.granted`, `council.seat.revoked`, `council.quorum.lost`.
- Ordering key = `council_session_id` (+`motion_id` for motion-scoped). `decision.published` carries cryptographic council seal; before `lifecycle.dissolved`. `quorum.lost` is P0 emergency save.

### 6.4 Delegation (8)
`delegation.task.dispatched`, `delegation.task.accepted`, `delegation.task.rejected`, `delegation.task.rerouted`, `delegation.task.completed`, `delegation.task.failed`, `delegation.task.timeout`, `delegation.load.balanced` (**`@v2`** — added weighted scores; the only Part 12 type with an explicit minor-version note).
- Ordering key = `agent_id` (per `delegation_id` for rerouted). Priority mirrors dispatched.

### 6.5 Knowledge (7)
`knowledge.memory.written`, `knowledge.memory.read`, `knowledge.memory.deleted`, `knowledge.memory.revised`, `knowledge.embedding.computed`, `knowledge.fact.invalidated`, `knowledge.ontology.updated`.
- Ordering key = scope/aggregate ID (`memory_id`, `tenant_id`). `read` is P3 exfiltration-pattern monitored. `deleted` is the RTBF/expungement mechanism (cf. GAP-TOMBSTONE §9.10).

### 6.6 Context (6)
`context.window.rebuilt`, `context.window.trimmed`, `context.window.compressed`, `context.refresh.attempt`, `context.token.budget.exceeded`, `context.grounding.report`.
- Ordering key = `context_id`/`workflow_id`. `grounding.report` ratio <0.85 → council convene.

### 6.7 Runtime (10)
`runtime.tool.invoked`, `runtime.tool.completed`, `runtime.tool.failed`, `runtime.model.called`, `runtime.model.streamed` (**ephemeral, not durable**), `runtime.model.completed`, `runtime.code.executed`, `runtime.sandbox.created`, `runtime.sandbox.destroyed`, `runtime.resource.throttled`.
- Ordering key = `call_id`. Arguments/output redacted/hashed; `code.executed` privileged; `model.streamed` aggregates via `model.completed`.

### 6.8 Communication (8)
`communication.message.sent`, `communication.message.received`, `communication.channel.opened`, `communication.channel.closed`, `communication.bridge.published`, `communication.bridge.failed`, `communication.typing.indicator` (**ephemeral**), `communication.presence.changed`.
- Ordering key = `channel_id`. `visibility` governs downstream; PII redacted.

### 6.9 Security (9)
`security.policy.violated`, `security.identity.authenticated`, `security.identity.revoked`, `security.prompt.injection.detected`, `security.exfiltration.attempt`, `security.secret.accessed`, `security.tool.callsign.revoked`, `security.audit.record` (Merkle chain anchor), `security.quarantine.action`.
- Ordering key = `actor`/`tenant`/`policy_id`. Always signed; `confidential` min (`secret` for credential/key). `prompt.injection.detected` MUST NOT echo payload; `audit.record` chain-anchors all events (§3.11).

### 6.10 Monitoring (8)
`monitoring.trace.span.opened`, `monitoring.trace.span.closed`, `monitoring.metric.scraped`, `monitoring.alert.raised`, `monitoring.alert.resolved`, `monitoring.incident.opened`, `monitoring.incident.closed`, `monitoring.cost.budget.threshold`.
- Ordering key per metric/`alert_id`/`incident_id`. `alert.raised` driven by governance/council/security events; P0 if sev1/2.

### 6.11 Scheduler (7)
`scheduler.job.scheduled`, `scheduler.job.fired`, `scheduler.job.missed`, `scheduler.job.completed`, `scheduler.job.canceled`, `scheduler.queue.depth` (sampled), `scheduler.queue.overloaded`.
- Ordering key = `job_id`/`queue`.

### 6.12 System (11)
`system.broker.overloaded`, `system.broker.recovered`, `system.store.degraded`, `system.store.recovered`, `system.upgrade.applied`, `system.config.changed`, `system.error.persisted`, `system.dlq.entry`, `system.context.quiesced`, `system.replay.started`, `system.replay.completed`.
- Ordering key = `system` (synthetic) or entity ID. `broker.overloaded`/`store.degraded` P0.

> **104 EXISTING types cataloged** (10+10+10+8+7+6+10+8+9+8+7+11). Components/Interfaces/ADRs per type: Not specified in Part 12 (only family-level ownership implied); derived ownership available in Part 14 `components.md`.

---

## 7. Catalog C — Part 13 Governance Events (51 EXISTING)

**Authority:** Part 13 `governance-events.md` §15 catalog (verified Total = **51**, line 1267). **Classification of all 51 = EXISTING** (ratified-candidate; `governance` namespace registered per Part 13 §5, subject to ESC ratification per Part 12 §24/§25 — status noted in §9.9). All use the Part 12 envelope (§3.1) and the Part 2 EventBus transport.

**Family baseline (all 51):** Delivery = at-least-once, ordered per partition key; Idempotency = `event_id` dedup + `correlation_id` + version-stamped projections; Signature = always signed; Classification = `confidential` min (`secret` for credential/authority); Persistence = sealed WORM; Retention = Hot 30d / Warm 1yr / Cold 7yr baseline (governance extension to Part 12 §33 family table, Part 13 §13); DLQ = `governance.dlq` (encrypted, read-restricted); Ownership = Governance domain per aggregate (Part 13 §6); Versioning = Part 12 §27 + Security co-signature for majors (Part 13 §7); Compatibility = Part 12 §27 + frozen `correlation_id`/`causation_id`/`partition_key` within major (Part 13 §8); ADRs = P13-ADR-001..010 (**all Draft per Part 13 `adrs.md` line 790–799 — context only, NOT mandatory architecture**), ADR-008/009/011 (Active); Source = Part 13 `governance-events.md` §15.

| # | FQN | Aggregate | Meaning | Partition key | Priority |
|---|---|---|---|---|---|
| G-1 | `governance.policy.created` | policy | Policy drafted/registered | policy_id | P2 |
| G-2 | `governance.policy.updated` | policy | Policy revised | policy_id | P2 |
| G-3 | `governance.policy.submitted` | policy | Submitted to review | policy_id | P1 |
| G-4 | `governance.policy.approved` | policy | Policy approved | policy_id | P1 |
| G-5 | `governance.policy.activated` | policy | Policy enforceable | policy_id | P1 |
| G-6 | `governance.policy.suspended` | policy | Policy temporarily disabled | policy_id | P0 if emergency else P1 |
| G-7 | `governance.policy.deprecated` | policy | Policy obsolete | policy_id | P1 |
| G-8 | `governance.policy.retired` | policy | Policy withdrawn | policy_id | P1 |
| G-9 | `governance.policy.violation.detected` | policy | Violation recorded (causation-linked to `security.policy.violated`) | policy_id | P0/P1 |
| G-10 | `governance.policy.exception.requested` | policy | Exception requested | policy_id | P1 |
| G-11 | `governance.policy.exception.approved` | policy | Exception granted | policy_id | P1 |
| G-12 | `governance.policy.exception.rejected` | policy | Exception denied | policy_id | P1 |
| G-13 | `governance.policy.exception.expiring` | policy | Exception near expiry | policy_id | P1/P2 |
| G-14 | `governance.policy.override.granted` | policy | Override granted | policy_id | P0 |
| G-15 | `governance.policy.conflict.detected` | policy | Policy conflict found | policy_id | P1 |
| G-16 | `governance.policy.validation.failed` | policy | Validation failed | policy_id | P1/P2 |
| G-17 | `governance.decision.created` | decision | Decision record opened | decision_id | P1 |
| G-18 | `governance.decision.approved` | decision | Decision approved | decision_id | P1 |
| G-19 | `governance.decision.rejected` | decision | Decision rejected | decision_id | P1 |
| G-20 | `governance.authority.delegated` | authority | Authority delegated | authority_id | P1 |
| G-21 | `governance.authority.revoked` | authority | Authority revoked | authority_id | P1 |
| G-22 | `governance.approval.requested` | approval | Approval requested | approval_id | P1 |
| G-23 | `governance.approval.granted` | approval | Approval granted | approval_id | P1 |
| G-24 | `governance.approval.rejected` | approval | Approval rejected | approval_id | P1 |
| G-25 | `governance.risk.identified` | risk | Risk registered | risk_id | P1 |
| G-26 | `governance.risk.escalated` | risk | Risk escalated | risk_id | P0 |
| G-27 | `governance.risk.accepted` | risk | Residual risk accepted | risk_id | P1 |
| G-28 | `governance.compliance.violation.detected` | compliance | Compliance violation | scope_id | P0/P1 |
| G-29 | `governance.audit.started` | audit | Audit commenced | audit_id | P1 |
| G-30 | `governance.audit.completed` | audit | Audit concluded | audit_id | P1 |
| G-31 | `governance.control.evaluated` | control | Control evaluated | control_id | P1 |
| G-32 | `governance.conformance.verified` | control | Conformance verified | control_id | P1 |
| G-33 | `governance.conformance.failed` | control | Conformance failed | control_id | P0/P1 |
| G-34 | `governance.agent.created` | agent | Agent identity registered | agent_id | P1 |
| G-35 | `governance.agent.provisioned` | agent | Capabilities/authority assigned | agent_id | P1 |
| G-36 | `governance.agent.activated` | agent | Agent operational | agent_id | P1 |
| G-37 | `governance.agent.suspended` | agent | Agent suspended | agent_id | P0 if emergency else P1 |
| G-38 | `governance.agent.revoked` | agent | Agent revoked | agent_id | P0 |
| G-39 | `governance.agent.action` | agent | Agent performed action | agent_id | P2 (`internal`) |
| G-40 | `governance.agent.action.denied` | agent | Agent action denied | agent_id | P1 |
| G-41 | `governance.agent.behavior.anomaly` | agent | Anomaly detected | agent_id | P1 |
| G-42 | `governance.agent.accountability.gap` | agent | Accountability gap | agent_id | P0 |
| G-43 | `governance.capability.created` | capability | Capability defined | capability_id | P2 |
| G-44 | `governance.capability.issued` | capability | Capability granted | capability_id | P1 |
| G-45 | `governance.capability.revoked` | capability | Capability revoked | capability_id | P1 |
| G-46 | `governance.capability.expired` | capability | Capability expired | capability_id | P2 |
| G-47 | `governance.capability.suspended` | capability | Capability suspended | capability_id | P0 if emergency else P1 |
| G-48 | `governance.capability.modified` | capability | Capability modified | capability_id | P1 |
| G-49 | `governance.capability.used` | capability | Capability exercised | capability_id | P2 (`internal`) |
| G-50 | `governance.capability.usage.violation` | capability | Constraint breached | capability_id | P1 |
| G-51 | `governance.capability.usage.anomaly` | capability | Anomalous usage | capability_id | P1 |

> **51 EXISTING types cataloged** across 10 aggregates (policy 16, decision 3, authority 2, approval 3, risk 3, compliance 1, audit 2, control 3, agent 9, capability 9). Components = Part 13 G-00..G-15 (per `components.md` §2.5). Interfaces = `INT-GOV-EVENT-001`. Producer/Consumer per type: per Part 13 §3 (each declares 15 attributes); not re-expanded here to avoid duplication — authoritative in Part 13 `governance-events.md` §3.

---

## 8. Catalog D — Implementation-Inventory & Component-Doc Event Names (DERIVED / UNSPECIFIED)

These names appear in `components.md` "Events published" lists and `ARCHITECTURAL_INVENTORY.md` but are **not** in the Part 2 enum, Part 12 §22 catalog, or Part 13 §15 catalog. They are not ratified contracts.

| Name (as referenced) | Appears in | Maps to EXISTING? | Classification |
|---|---|---|---|
| `KernelStarted`, `KernelStopped` | components.md §2.1 | Part 2 has `KERNEL_READY`/`KERNEL_TERMINATED` (near-equivalent, different name) | DERIVED (alias of Part 2 kernel lifecycle) |
| `CoreComponentInitialized`, `CoreComponentShutdown` | components.md §2.1 | Part 2 `CORE_COMPONENT_INITIALIZED`/`SHUTDOWN` | DERIVED (alias) |
| `ServiceRegistered`, `ServiceInitialized`, `ServiceShutdown`, `ServiceHealthChanged`, `ServiceDegraded`, `ServiceFailed` | components.md §2.2.2 | Part 2 `SERVICE_*` set (near-equivalent) | DERIVED (alias) — also see CONFLICT E.3 |
| `ConfigurationFrozen`, `ConfigurationChanged` | components.md §2.2.3 | Part 2 `CONFIGURATION_FROZEN`/`CHANGED` | DERIVED (alias) |
| `LogAnomalyDetected` | components.md §2.2.4 | no canonical equivalent | UNSPECIFIED |
| `LogEvent` | interfaces.md (referenced, not in Part 2 §2.3.1) | no canonical equivalent in any registry | UNSPECIFIED (semantics undefined) |
| `MemoryStored`, `MemoryRetrieved`, `MemoryUpdated`, `MemoryConsolidated`, `MemoryPruned` | components.md §2.3.2 | Part 2 `MEMORY_*` (exact name match) / Part 12 `knowledge.memory.*` | DERIVED (Part 2 type) |
| `WorkflowCreated`, `WorkflowStateChanged`, `WorkflowStepStarted`, `WorkflowStepCompleted`, `WorkflowStepFailed`, `WorkflowCompleted`, `WorkflowFailed`, `WorkflowCancelled` | components.md §2.3.1 | Part 2 `WORKFLOW_*` (near-equivalent, different case) | DERIVED (Part 2 type) |
| `CouncilConvened`, `CouncilDeliberated`, `CouncilDecided`, `CouncilDissented` | components.md §2.3.7 | Part 2 `COUNCIL_*` (near-equivalent) | DERIVED (Part 2 type) |
| `SkillLoaded`, `SkillUnloaded`, `SkillExecuted`, `SkillFailed`, `MCPServerConnected`, `MCPServerDisconnected`, `MCPToolCalled`, `MCPToolResult` | components.md §2.3.6 | Part 2 `SKILL_*`/`MCP_TOOL_*` (near-equivalent) | DERIVED (Part 2 type) |
| `AuthorizationDecisionEvent`, `AuthenticationFailedEvent` | interfaces.md §2.7 | no canonical event type (authn/authz is a command/response via `INT-SEC-AUTH-001`; Part 2 uses `AUTH_FAILED`/`ACCESS_DENIED`) | UNSPECIFIED — also see CONFLICT E.4 |
| `AccessDeniedEvent` | interfaces.md §2.7 | Part 2 `ACCESS_DENIED` | CONFLICT (naming) — see E.4 |
| `MetricsAlert` | components.md §2.3.4 | Part 2 `METRIC_EMITTED` (near-equivalent) / Part 12 `monitoring.alert.raised` | DERIVED (alias) |
| `RootCauseAnalyzed`, `RootCauseResolved`, `FailureClassified` | components.md §2.3.9 | Part 2 `ROOT_CAUSE_ANALYZED` (+ 2 not in enum) | DERIVED / UNSPECIFIED (`Resolved`,`Classified` not in enum) |
| `CheckpointCreated`/`Restored`/`Deleted`, `RetryScheduled`/`Executed`/`BudgetExhausted`, `ResourceAllocated`/etc., `StateTransitioned`/`StateCheckpointed`/`StateRestored` | components.md §2.3.8 | Part 2 `CHECKPOINT_*`,`RETRY_BUDGET_EXHAUSTED`,`RESOURCE_*`,`STATE_*` (near-equivalent) | DERIVED (Part 2 type) |
| `ServiceRegistered`/`HealthChanged` (duplicate listing under ServiceRegistry) | components.md §2.2.2 | Part 2 `SERVICE_*` | DERIVED (alias) |

> **No new types invented.** Every name above traces to a cited line. Where a name has no canonical equivalent it is **UNSPECIFIED**, not filled in. The systematic **UPPER_SNAKE-vs-lowercase-dotted naming drift** between `components.md`/`ARCHITECTURAL_INVENTORY.md` and Part 12/13 is itself **GAP-NAMING** (§9.11).

---

## 8b. Catalog E — CONFLICT (same concept, inconsistent identifiers across authoritative sources)

These are **not** new events. They are documented collisions where two-or-more authoritative sources name the *same concept* differently, with no mapping registry. Listed here so the conflict is exposed (rubric #10), not hidden. No normalization is performed.

| Concept | Source A (identifier) | Source B (identifier) | Source C (identifier) | Conflict type |
|---|---|---|---|---|
| Kernel lifecycle | Part 2 `KERNEL_READY`, `KERNEL_INITIALIZATION_STARTED`, `KERNEL_SHUTDOWN_STARTED`, `KERNEL_TERMINATED` (SCREAMING_SNAKE) | Part 4 `KernelLifecycleEvent`, `KernelPhaseCompletedEvent`, `KernelDegradedEvent`, `KernelRecoveryEvent` (PascalCase+Event) | — | A vs B: same concept, two registries, no mapping. CONFLICT (E.1) |
| State transition | Part 2 `STATE_CHANGED`, `STATE_SNAPSHOT_CREATED`, `STATE_RESTORED` | Part 4 `StateTransitionCommittedEvent`, `StateTransitionDeniedEvent`, `StateSnapshotCreatedEvent`, `StateRecoveryCompletedEvent`, `StateRecoveryFailedEvent` (+ `StateTransitionRequestedEvent` = **command**, see §11) | — | A vs B: CONFLICT (E.2) |
| Service lifecycle | Part 2 `SERVICE_STARTED`/`STOPPED`/`DEGRADED`/`FAILED` | interfaces.md §2.5 `ServiceRegistered`, `ServiceInitialized`, `ServiceHealthChanged`, `ServiceDegraded`, `ServiceFailed`; **Part 3 (FROZEN) `ServiceHealthChanged`, `ServiceFailed`** | — | A vs B vs Part 3: three-way CONFLICT alias (E.3) |
| Auth/security | Part 2 `AUTH_FAILED`, `ACCESS_DENIED` | interfaces.md §2.7 `AuthorizationDecisionEvent`, `AuthenticationFailedEvent`, `AccessDeniedEvent` | — | A vs B: CONFLICT (E.4); `AccessDeniedEvent` overlaps `ACCESS_DENIED` |
| **Part 12 self-contradiction** | Part 12 §22 dotted catalog `delegation.task.dispatched`, `workflow.lifecycle.started`, `agent.lifecycle.registered` | Part 12 *own* prose/components: `TaskDelegated`, `TaskCompleted`, `SessionRequested`, `AgentMatching`, `WorkflowStarted`, `CapabilityRegistered` (verb-object PascalCase) | — | **Within Part 12**: canonical §22 dotted vs its own component/prose PascalCase. §22 wins; PascalCase = CONFLICT (E.5) |
| Governance (schemas.md PascalCase vs Part 13 dotted) | Part 13 §15 dotted `governance.policy.*`, `governance.decision.*`, `governance.authority.*`, `governance.approval.*`, `governance.risk.*`, `governance.compliance.*`, `governance.audit.*`, `governance.exception.*`, `governance.conformance.*` | Part 14 `schemas.md` "Related Events" PascalCase: `EvaluationStarted`/`Completed`/`Denied`/`Permitted`/`ExceptionApplied`, `AuthorityGranted`/`Resolved`/`Denied`/`BoundaryHit`, `DelegationGranted`/`Revoked`/`ChainValidationFailed`, `ConformanceEvaluationCompleted`/`ComplianceGapDetected`/`ConformanceBreachDetected`, `ExceptionRequested`/`Granted`/…, `ApprovalRequested`/`Decided`/…, `BaselinePublished`/`ObligationIdentified`/… | — | B (schemas.md) vs A (Part 13): PascalCase shorthand vs canonical dotted. CONFLICT (E.6) |
| Governance (Part 13 legacy PascalCase) | Part 13 §15 dotted `governance.policy.created`, `governance.policy.distributed`(n/a), `governance.authority.delegated`, `governance.risk.identified`, `governance.compliance.violation.detected`, `governance.audit.completed` | Part 13 line 1013 legacy shorthand `PolicyCreated`, `PolicyDistributed`, `AuthorityDelegated`, `RiskIdentified`, `ComplianceViolation`, `AuditLogGenerated` | — | Part 13 internal: legacy PascalCase vs its own dotted. CONFLICT (E.7) |
| Memory | Part 2 `MEMORY_STORED`/`MEMORY_RETRIEVED`/… | Part 12 `knowledge.memory.written`/`read`/… | Part 14 `schemas.md` §2.9 `memory.stored`/`memory.accessed`/`memory.expired`/`memory.decayed` | Three-way: CONFLICT (E.8); schemas.md §2.9 forms also unresolved (see §8c) |

> **Resolution status:** all eight are **CONFLICT**, not resolved. FI-005 (integrations.md) flags the A-vs-C collisions for ARB; this catalog extends FI-005 by also capturing the **Part 12 internal** (E.5) and **schemas.md-vs-Part13** (E.6/E.7) collisions that FI-005 omitted, and by keeping each identifier distinct rather than picking a winner.

---

## 8c. Catalog F — Referenced-but-not-canonical dotted events (from Part 14 `schemas.md` "Related Events")

`Part 14/schemas.md` lists the following dotted event names in its "Related Events" fields, but **none appear in the authoritative Part 12 §22 catalog** (verified: Part 12 §22 Total = 104, listed line-by-line in §6). They are dangling cross-references — referenced by a Part 14 doc but absent from the canonical Part 12 registry. Marked **UNRESOLVED** (rubric #9).

| Referenced name (schemas.md) | schemas.md § | In Part 12 §22? | Status |
|---|---|---|---|
| `task.created`, `task.assigned`, `task.completed`, `task.failed`, `task.retrying` | §2.4 | No (Part 12 has `delegation.task.*`, not `task.*`) | UNRESOLVED (dangling) |
| `capability.advertised`, `capability.updated` | §2.2 | No (Part 12 has no `capability.*` event family; governance has `governance.capability.*` only) | UNRESOLVED (dangling) |
| `knowledge.ingested`, `knowledge.updated`, `knowledge.accessed`, `knowledge.retired` | §2.8 | No (Part 12 has `knowledge.memory.*`, `knowledge.embedding.*`, `knowledge.fact.*`, `knowledge.ontology.*` — not these four) | UNRESOLVED (dangling) |
| `memory.stored`, `memory.accessed`, `memory.expired`, `memory.decayed` | §2.9 | No (Part 12 has `knowledge.memory.*`; `memory.*` is a schemas.md-only name) | UNRESOLVED (dangling) |
| `plan.created`, `plan.updated`, `plan.approved`, `plan.rejected` | §3.1 | No (Part 12 has no `plan.*` family) | UNRESOLVED (dangling) |

> These names surface only because `schemas.md` echoes them in "Related Events" of domain schemas (`P12-Task`, `P12-Capability`, `P12-KnowledgeObject`, `P12-MemoryObject`, `P5-PlanArtifact`). They are **not** ratified Part 12 event types. Either they must be ratified into the Part 12 §22 catalog (and then migrate to Catalog B) or the schemas.md "Related Events" must be corrected. Recorded as GAP-XREF (§9.14), not silently dropped.

---

## 8d. Catalog G — Event names referenced by Parts 3/5/6 & integrations.md, absent from all canonical registries

Per rubric #1 (verify every event against Parts 0–13) and #9 (cross-reference), these event names are referenced by authoritative Part docs or `integrations.md` but **do not appear** in the Part 2 enum, Part 12 §22 catalog, or Part 13 §15 catalog. Each is classified by what its source says, and kept **unresolved** rather than invented or force-mapped.

### 8d.1 Part 3 (FROZEN) PascalCase lifecycle (Scheme E) — collides with Part 2
| Name | Source | Part 2 equivalent | Status |
|---|---|---|---|
| `CoreComponentInitialized` | Part 3 §3.4 (line 178) | `CORE_COMPONENT_INITIALIZED` (Part 2 enum) | CONFLICT E.1/Scheme-E — same concept, two authoritative names |
| `CoreComponentShutdown` | Part 3 §3.4 (line 179, 157) | `CORE_COMPONENT_SHUTDOWN` | CONFLICT |
| `ServiceHealthChanged` | Part 3 §3.4 (lines 386, 395) | `SERVICE_DEGRADED`/`SERVICE_FAILED` family (Part 2) | CONFLICT E.3 |
| `ServiceFailed` | Part 3 §3.4 (line 387) | `SERVICE_FAILED` | CONFLICT |
> Part 3 is **FROZEN, authoritative Source of Truth** and explicitly "MUST NOT contradict Part 2" — yet it uses a different naming scheme for these lifecycle events. The collision is genuine and unresolved (GAP-NAMING/E). This catalog does not pick a winner.

### 8d.2 Part 5 SDLC trigger / phase events — referenced but not in Part 2 enum
| Name | Source (Part 5) | In Part 2 enum? | In Part 12/13? | Status |
|---|---|---|---|---|
| `CODING_REQUESTED`, `REVIEW_REQUESTED`, `TESTING_REQUESTED`, `DEPLOYMENT_REQUESTED` | Part 5 §5.x tables (lines 308, 424, 556, 710, 871) | No | No | UNRESOLVED (DERIVED from Part 2 `*_REQUESTED` pattern; `*_REQUESTED` suffix not in Part 2 enum) |
| `PLANNING_COMPLETED`, `CODING_COMPLETED`, `REVIEW_APPROVED`, `TESTING_COMPLETED`, `DEPLOYMENT_COMPLETED` | Part 5 §5.x (lines 309, 425, 557, 711, 871) | Part 2 has `PLANNING_COMPLETED`/`CODING_COMPLETED`/`TESTING_COMPLETED`/`DEPLOYMENT_COMPLETED` ✅; `REVIEW_APPROVED` **No** | — | Mixed: most exist in Part 2; `REVIEW_APPROVED` UNRESOLVED |
| `CODING_REQUESTED`, `ENVIRONMENT_PREPARE`, `ENVIRONMENT_READY`, `ENVIRONMENT_PROVISION`, `ENVIRONMENT_TEARDOWN`, `TRAFFIC_SHIFT`, `TRAFFIC_SPLIT`, `ROLLBACK_EXECUTE`, `OBSERVABILITY_DEPLOY`, `MEMORY_SYNC_REQUESTED`/`COMPLETED`/`FAILED`, `LEARNING_REQUESTED`, `RESEARCH_COMPLETED`, `FINDING_EMITTED`, `CONTEXT_ASSEMBLE`, `SKILL_EXECUTE`, `HUMAN_RESPONSE_RECEIVED`, `TestTrendEvent` | Part 5 §5.x (lines 312, 424, 712–713, 871–877, 426–427, 558–561, 714, 734, 556, 308) | **None** of these in Part 2 enum | No | UNRESOLVED — Part 5 invents phase-transition event names not ratified in any registry. Several also use non-Part-2 casing (`CONTEXT_ASSEMBLE` vs Part 2 `CONTEXT_ASSEMBLED`, `SKILL_EXECUTE` vs Part 2 `SKILL_EXECUTED`). |

### 8d.3 Part 6 / interfaces.md capability-facade events
| Name | Source | In registry? | Status |
|---|---|---|---|
| `MEMORY_SYNC_REQUESTED` / `MEMORY_SYNC_COMPLETED` / `MEMORY_SYNC_FAILED` | Part 5 §5.2 ES-08; interfaces.md §2.8 | No (Part 2 has `MEMORY_STORED`/`RETRIEVED`/`UPDATED`/`CONSOLIDATED`/`PRUNED` only) | UNRESOLVED |
| `SkillFacadeEvent`, `MCPFacadeEvent`, `MemoryFacadeEvent`, `CollaborationEvent`, `ServiceEvent`, `MetricEvent`, `GovernanceEvent`, `CoreComponentInitialized{name}`/`CoreComponentShutdown{name}` | Part 6 / interfaces.md §2.5–2.8 | No single type | CONFLICT/UNSPECIFIED — these are *family labels*, not enumerated types; payloads `[UNSPECIFIED]` per interfaces.md |

### 8d.4 integrations.md stale-count note
`integrations.md` line 37 and line 142 state "**97 canonical EventTypes enumerated**" (Part 2 §2.3.1). This is the same spec error as GAP-SPEC-COUNT (§9.12): Part 2 §2.3.1 actually enumerates **118**. `integrations.md` carries the error forward. Recorded here for cross-reference integrity; the authoritative Part 14 position is 118 (verified).

---

## 9. GAPs (contracts assumed but missing / divergent)

### 9.1 GAP-ENV — Two incompatible envelope specifications
Part 2 §2.2.1 (`eventId` UUIDv7, `target`/`checksum`/`category`) and Part 12 §4 / Part 14 `schemas.md` §1.1 (`event_id` ULID, `partition_key`/`schema_ref`/`tenant_id`/`security`) define different envelopes (field names, ID format, priority encoding, signing). No single authoritative envelope for all 273 cataloged types. **Resolution requires a new ADR** (Part 14 `adrs.md` is currently a 39-line index that does not yet contain such an ADR). *No unification attempted here.*

### 9.2 GAP-ORDER — `partition_key` vs `correlationId`+`timestampMonotonic`
Part 12 §29 orders by `partition_key`; Part 2 §2.4.9 orders by priority + `correlationId` + `timestampMonotonic`. Functionally compatible but primitive mismatch; cross-registry events cannot be guaranteed consistent ordering without reconciliation.

### 9.3 GAP-DEDUP — Dedup window source conflict
Part 12 §30 states a **24h `event_id` dedup window**; Part 2 §2.4.7 defines dedup via `eventId`/`idempotencyKey` with no stated TTL. Reconcile.

### 9.4 GAP-RETRY — Two retry models
Part 12 §18 ("5 attempts default, 10 for terminal, exp backoff 200ms→64s") vs Part 2 §2.4 internal-queue model (retry queue cap 1,000, per-subscription `retryPolicy`, no fixed attempt count). Reconcile.

### 9.5 GAP-DLQ — Single DLQ vs per-family DLQ topics
Part 2 models one DLQ (DROP_OLDEST, circular); Part 12 §19 names 8 per-family DLQ topics (`workflow.dlq`, `council.dlq`, `delegation.dlq`, `knowledge.dlq`, `communication.dlq`, `security.dlq` (encrypted), `monitoring.dlq`, `system.dlq`) plus `governance.dlq` (Part 13). Reconcile the single-vs-many model.

### 9.6 GAP-SEC — Signing/ACL absent from Part 2 base contract
Part 2 `Event` has no `security.*` block; signing exists only in the Part 12 envelope. Part 2's security posture for events is unspecified at the transport layer (bus-level authn/authz is "Unspecified" per `interfaces.md` INT-EVT-BUS-001). GAP.

### 9.7 GAP-EXT — Closed enum vs "custom events" extension point
Part 2 INV-ET-003 prohibits late EventType registration in v1.0 (closed enum); ADR-013 lists "custom events" as a permitted extension point. Apparent contradiction. Reconcile via ADR (Part 14 `adrs.md` is currently an incomplete index and does not yet define the reconciling ADR).

### 9.8 GAP-UNIVERSE — Three partially-disjoint event registries
Part 2 (118 enumerated; spec prose says 97 — §9.12), Part 12 (104), Part 13 (51) are not a single reconciled set (§4). Kernel/service/resource/diagnostic lifecycle (Part 2) and governance (Part 13) have no Part 12 counterpart; multi-agent delegation/communication detail (Part 12) has no Part 2 counterpart. **Largest catalog-level risk.** Needs an integration event registry that spans all three. (Part 4's `PascalCase+Event` vocabulary, §8b E.1/E.2, is a *fourth* de-facto registry that should also be reconciled — see GAP-UNIVERSE-4 below.)

### 9.9 GAP-RATIFICATION — `governance.*` ESC ratification pending
Part 13 §5 registers `governance` as a 12th namespace "subject to ESC ratification per Part 12 §24/§25." Until that ratification lands, the 51 types are **ratified-candidate**, not finally ratified. Flagged, not treated as defect.

### 9.10 GAP-TOMBSTONE — `system.event.tombstoned` / `system.event.deleted` referenced but absent
Part 12 §26/§33 deletion narrative references `system.event.tombstoned` (retired-type tombstone) and `system.event.deleted` (cold-tier verifiable deletion / RTBF) but neither is in the Part 12 §22 catalog (System family lists 11 different types). `knowledge.memory.deleted` (6.5) IS ratified and covers memory-level deletion; the *type/catalog* deletion records are missing. **GAP.**

### 9.11 GAP-NAMING — UPPER_SNAKE vs lowercase-dotted drift
`components.md`/`ARCHITECTURAL_INVENTORY.md` use UPPER_SNAKE (`KernelStarted`, `MemoryStored`); Part 12/13 use lowercase dotted (`workflow.step.completed`, `governance.policy.created`); Part 2 uses UPPER_SNAKE enum with `{DOMAIN}_{ACTION}_{OUTCOME?}` rule (INV-ET-002). The implementation vocabulary is not a registered EventType in any canonical registry. GAP. (Superseded in scope by the broader §4.1 / §8b four-scheme conflict, but retained as the label for the impl vocabulary specifically.)

### 9.12 GAP-SPEC-COUNT — Part 2 self-contradiction on canonical type count
Part 2 §2.3.1 enumerates **118** `EventType` values (verified: SYSTEM 17, CONTROL 26, DATA 16, AUDIT 36, DIAGNOSTIC 23) yet its own prose (line 398) claims "97 canonical event types." The catalog lists all 118 enumerated values; the "97" is recorded as a **spec error**, not used to truncate. Resolution requires a Part 2 erratum. GAP.

### 9.13 GAP-P14-ENV — Part 14 `schemas.md` §11 envelope correction is itself wrong
`schemas.md` §11 claims the Part 12 §4 envelope "does not include `tenant_id`" and "`produced_by.actor_kind` does not include `governance`." Direct verification of authoritative Part 12 §4 (lines 196, 202) shows **`tenant_id` IS present** in the Part 12 envelope, and `actor_kind` enumerates `agent|council|workflow|runtime|scheduler|tool|system` (correctly **no** `governance`). Therefore schemas.md §11's `tenant_id` claim is **incorrect**; this catalog follows the authoritative Part 12 §4. Similarly, schemas.md §11 (line 2065) states Part 12 has "64+ event definitions" — contradicting the authoritative Part 12 §22 Total = **104**. Both are Part 14-internal inaccuracies surfaced here (rubric #10), not propagated. (Noted again in §13 count row.)

**Source-specific authority reminder (rubric #2):** `EVENT-ENVELOPE-v1` (`schemas.md` §1.1) is normative **for Part 14 integration payloads only**; its authority is *derived* from Part 12 §4 (canonical dotted envelope) and Part 2 EventBus (transport). It is **not** a universal envelope and is not authoritative where it disagrees with Part 12 §4. Do not let a Part 14 schema description become the global envelope definition.

### 9.14 GAP-XREF — `schemas.md` "Related Events" reference non-canonical dotted names
`Part 14/schemas.md` "Related Events" fields (§2.2 `capability.advertised`, §2.4 `task.*`, §2.8 `knowledge.ingested/updated/accessed/retired`, §2.9 `memory.stored/accessed/expired/decayed`, §3.1 `plan.*`) name dotted events that **do not exist** in the authoritative Part 12 §22 catalog (Catalog F, §8c). These are dangling cross-references within Part 14. Resolution: either ratify the missing types into Part 12 §22 or correct the schemas.md references. GAP.

---

## 10. PROPOSED & FUTURE

### 10.1 PROPOSED (named in prose, no ratified contract)
- **`ADRComplianceViolation`** (Part 12 `adrs.md` Rule G1.5; Part 13 `adrs.md` Rule G3.5 / P13-ADR-009 Conformance Architecture — **P13-ADR-009 is Draft, not mandatory**): an event name required by conformance prose ("ADR compliance violations MUST be reported as `ADRComplianceViolation` events on the EventBus"; "Non-compliance triggers `ADRComplianceViolation` events") that is **not** in any ratified registry (Part 2 enum, Part 12 §22, or Part 13 §15) and violates the Part 12 §25 lowercase-dotted naming RFC (PascalCase). Either map to `governance.conformance.failed` (G-33) or ratify a `governance.adr.compliance.violated` type. **UNRESOLVED — do not emit as-is.** Because the requiring ADR is Draft, this name is context, not a binding contract.
- **Part 2 §37 / Part 12 §37 roadmap families:** multimodal streaming, federated cross-OS events, hardware root-of-trust sealing — named as future event families, no types defined.
- **Resolver interfaces** (`PRO-EXT-ADAPTER-001`, `PRO-GOV-ADAPTER-001`, `PRO-GOV-REPORT-001`, `UNRES-EXT-AUDIT-001`, `UNRES-POLICY-IO-001`) — interfaces without event contracts; their events are PROPOSED-only.

### 10.2 FUTURE (explicitly out of v1.0 scope)
- **Distributed EventBus** (`UNRES-EVT-DIST-001`, Part 2 §2.1.4, Part 1 §1.7.1): v1.0 is single-process in-memory only; cross-process/cross-machine is v2.0. All ordering/replay guarantees are single-process.
- **Cross-process correlation** (not yet defined as a ratified ADR in Part 14 `adrs.md`): correlation/causation propagate only within one process in v1.0; distributed tracing would require an explicit `TraceContextEvent`. FUTURE.
- **Webhook / push inbound bridge**, **external IdP federation**, **multi-tenancy model**, **event schema migration strategy** — their event contracts are FUTURE (Part 14 `adrs.md` does not yet enumerate these as ratified ADRs).

---

## 11. Event / Command / Request / Response / Notification — explicit taxonomy (rubric #6)

The brief requires distinguishing five message kinds. **Crossing a boundary does NOT make something an event.** Each kind is defined and the catalog's separate treatment is stated.

| Kind | Definition (authoritative) | Boundary behavior | In event counts? |
|---|---|---|---|
| **Event** | An immutable fact that *already happened*; emitted after the fact; no return value expected. | One-to-many, async, EventBus. | ✅ Yes |
| **Command** | A synchronous directive to *do* something; sender awaits completion/ack. | Request/response over a sync interface. | ❌ No |
| **Request** | One side of a request/response exchange; asks for an action or data. | Outbound half of a sync pair. | ❌ No |
| **Response** | The answer to a request (decision, result, or rejection). May be emitted as an event on the bus *after* the sync decision, but the sync half is not an event. | Return half of a sync pair (or an emitted result event). | Only the emitted result-event half, if it is in a registry. |
| **Notification** | A one-way, non-durable signal (often ephemeral) that something occurred; subscribers may not act. Distinct from an Event in that it is typically best-effort, non-persisted, and non-causal. | One-to-many, async, often `ephemeral`/P3. | ⚠️ Only if registered as an event type (e.g., Part 12 `communication.typing.indicator`, `runtime.model.streamed`, `monitoring.queue.depth` are *notifications* flagged ephemeral, yet are registered events). |

**Key rule (rubric #6):** An item is an *event* only if an authoritative source defines it as an emitted, immutable, post-fact fact in a registry (Part 2 enum, Part 12 §22, Part 13 §15). A `request`, a `command`, or a synchronous `response` is **never** auto-upgraded to "event" merely because it traverses the bus. Where a source *emits a result event* as the response side (e.g., Part 4 `StateTransitionCommittedEvent`), that emitted fact IS an event; the triggering `StateTransitionRequest`/command is not.

### 11.1 Separated command / request / response surfaces (excluded from event counts)
| Surface | Kind | Interface / Source | Event counterpart(s) |
|---|---|---|---|
| Workflow pause / resume / cancel | **Command** | `INT-WF-CTRL-001` (sync) | `WORKFLOW_PAUSED`/`RESUMED`/`CANCELLED` (Part 2 events) |
| Human escalation / question / approval / override / feedback (request half) | **Request** | `INT-HUMAN-001` | `HUMAN_ESCALATION_REQUIRED` (Part 2 AUDIT event, §5.4) is the only emitted human-lifecycle event in the Part 2 enum; `HUMAN_RESPONSE_RECEIVED` is **not** in any canonical registry (referenced only by Part 5 — UNRESOLVED, §8d.2) and `HUMAN_TIMEOUT` is **not** an enumerated Part 2 type. The *request* half is a request, not an event. |
| `SecurityManager.authorize` | **Command** (sync decision) | `INT-SEC-AUTH-001` | **Response** is a decision; `AuthorizationDecisionEvent` is UNSPECIFIED (§8) — the *response* is not itself a registered event in the canonical registries |
| `StateTransitionRequest` / `StateTransitionRequestEvent` | **Request/Command** | Part 4 §4.4.9 (emit of request; Part4A line 410–415, 488) | **Response events** `StateTransitionCommittedEvent` / `StateTransitionDeniedEvent` / `StateSnapshotCreatedEvent` / `StateRecoveryCompletedEvent` / `StateRecoveryFailedEvent` are events (CONFLICT E.2 vs Part 2 `STATE_*`). Part 4 mandates "every `StateTransitionRequestEvent` produces exactly one response event" (Part4A line 541). |
| `EventBus.publish` / `subscribe` | **Infrastructure op** | `INT-EVT-BUS-001` | not domain messages |

### 11.2 Notifications cataloged as events (registered + flagged ephemeral)
Part 12 explicitly marks several registered types as **ephemeral notifications** (non-durable, best-effort) — they are events *and* notifications: `communication.typing.indicator` (§6.8), `runtime.model.streamed` (§6.7, "ephemeral, not durable"), `scheduler.queue.depth` (sampled, §6.11), `monitoring.queue.*` samples. These remain in Catalog B but are annotated as notifications, not durable facts.

> Per the brief: command-like / request-like / response-like items are **not** auto-classified as events. The catalog counts events only; request/response/command surfaces are enumerated here and excluded.

---

## 12. ADR Conformance Verification (correlation / causation / immutability / failure)

**Authority scope note (rubric #1):** The constraints below apply only to ADRs that are `Accepted`/`Active`/`Experimental` within their stated scope (per Part 12 §3 / Part 13 §5 lifecycle and `project-knowledge/ARCHITECTURE_DECISIONS.md` line 709). `Draft`/`Proposed` ADRs — notably **all ten P13-ADR-001..010** (Part 13 `adrs.md` status table, lines 790–799) — are recorded as context and are **NOT** treated as mandatory architecture in this catalog. The Part 14 `adrs.md` index is a 39-line stub and defines no ratified ADRs of its own.

| ADR | Status (source) | Requirement | Verified against catalog? |
|---|---|---|---|
| **ADR-008** (Immutable Events w/ Correlation & Causation) | Active (`ARCHITECTURE_DECISIONS.md`) | Every event carries `correlation_id`, `causation_id`; immutable | ✅ All 273 EXISTING types inherit these via Part 2 INV-EVT-004/005 + Part 12 §30 + Part 14 `schemas.md` INV-ENV-002/003. External-format conversion required to populate them (ADR-008 integration impact). |
| **ADR-009** (Explicit Failure Handling) | Active | Failures communicated via events; no exceptions across boundaries | ✅ Failure events exist in all registries (`*_FAILED`, `RETRY_BUDGET_EXHAUSTED`, `security.*`, `governance.*` violations). `INT-EVT-BUS-001` routes failed deliveries to retry/DLQ. |
| **ADR-001** (Event-First) | Active | All inter-component comms via EventBus; no direct calls | ✅ All 273 are EventBus events; commands (§11) are the narrow, explicitly-documented exception. |
| **ADR-011** (Versioning First-Class) | Active | Every contract carries version; breaking = MAJOR + migration | ✅ Part 2 `eventVersion` SemVer; Part 12 `event_version`+`schema_ref`. |
| **ADR-013** (Extension Governance) | Active | Custom events permitted; bus/kernel/BaseService locked | ⚠️ Conflicts with Part 2 closed enum (GAP-EXT, §9.7). |
| **P12-ADR-001..010** (collaboration family) | Accepted (Part 12 `adrs.md` lines 522–531) | Event-first collaboration, zero-trust, etc. | ✅ Referenced where relevant (§3.11 P12-ADR-008; §6 baseline). |
| **P13-ADR-001..010** (governance family) | **Draft** (Part 13 `adrs.md` lines 790–799) | Policy/authority/conformance governance | ⛔ **Not enforced** as mandatory architecture — Draft per Part 13 lifecycle; recorded only as context for the 51 governance types. |

**Unverified / conflicting:** GAP-ENV, GAP-ORDER, GAP-DEDUP, GAP-RETRY, GAP-DLQ, GAP-SEC, GAP-EXT, GAP-UNIVERSE, GAP-RATIFICATION, GAP-TOMBSTONE, GAP-NAMING, GAP-SPEC-COUNT, GAP-P14-ENV, GAP-XREF (§9) — none invented away; all escalated.

---

## 13. Counts & Classification Summary

| Bucket | Count | Source |
|---|---|---|
| EXISTING — Part 2 enum | 118 (enumerated; spec prose says 97 — §9.12) | Part 2 §2.3.1 |
| EXISTING — Part 12 dotted | 104 (verified Total line 1886) | Part 12 `events.md` §22 |
| EXISTING — Part 13 governance | 51 (verified Total line 1267) | Part 13 `governance-events.md` §15 |
| **EXISTING subtotal (distinct registries)** | **273** | — |
| DERIVED (impl aliases of EXISTING) | ~30 names | `components.md`/`ARCHITECTURAL_INVENTORY.md` (§8) |
| UNSPECIFIED (named, no contract) | ~7 names | `components.md`/`interfaces.md` (`LogAnomalyDetected`, `LogEvent`, `AuthorizationDecisionEvent`, `AuthenticationFailedEvent`, RootCause `Resolved`/`Classified`) (§8) |
| CONFLICT (same concept, inconsistent identifiers) | 8 collision groups (E.1–E.8), ~45 referenced names; + Part 3 FROZEN Scheme-E added to §4.1/§8b | §4.1, §8b |
| UNRESOLVED (referenced by schemas.md, absent from Part 12 §22) | 18 dotted names | §8c, GAP-XREF |
| UNRESOLVED (referenced by Parts 3/5/6 & integrations.md, absent from all registries) | ~35 names (Part 3 lifecycle ×4, Part 5 SDLC/ops ×~25, Part 6 facade labels) | §8d, GAP-XREF/GAP-NAMING |
| GAP | 14 items | §9 (ENV, ORDER, DEDUP, RETRY, DLQ, SEC, EXT, UNIVERSE, RATIFICATION, TOMBSTONE, NAMING, SPEC-COUNT, P14-ENV, XREF) |
| PROPOSED | `ADRComplianceViolation` + roadmap families + resolver events | §10.1 |
| FUTURE | Distributed EventBus, cross-process correlation, webhook/IdP/multitenancy | §10.2 |
| **Commands (excluded from events)** | 5 surfaces (incl. Part 4 `StateTransitionRequest`) | §11 |

> Distinct EXISTING types ≈ 273, but conceptual overlaps across registries (§4) mean the *unique event concepts* are fewer. The three registries are not deduplicated because doing so would require an ADR-level reconciliation decision (GAP-UNIVERSE) that this catalog is not authorized to make. **ADR-authority note (rubric #1):** the only ADRs enforced as mandatory constraints in this catalog are the `Active` core ADRs (001/008/009/011/013) and the `Accepted` P12-ADR-001..010. The `Draft` P13-ADR-001..010 and the 39-line Part 14 `adrs.md` stub are **context only, not mandatory architecture**. **Count-accuracy note:** Part 14 `schemas.md` §11 understates Part 12 as "64+ event definitions" and mis-states the Part 12 envelope (`tenant_id`); both are corrected above (§9.13) against the authoritative Part 12 §4 / §22. No count in this catalog is hardcoded without a verified source line.

---

## 14. Cross-References

**Every event referenced by `integrations.md` and `schemas.md` is accounted for below (rubric #9):**

- **Part 2 `events.md`** — transport (EventBus), base contract, 118 enumerated EventTypes (spec prose says 97 — §9.12), ordering/delivery/retry/failure, naming/registration. Authoritative for mechanics.
- **Part 12 `events.md`** — 104 dotted events (§22, verified), envelope §4, governance/lifecycle/versioning/registry, DLQ topics.
- **Part 13 `governance-events.md`** — 51 `governance.*` events (§15, verified); defers shared constructs to Part 12.
- **Part 4 `ARCHITECTURE_SPEC_PART4A.md`** — `KernelLifecycleEvent`/`KernelPhaseCompletedEvent`/`KernelDegradedEvent`/`KernelRecoveryEvent` (§4.3.10); `StateTransition*Event` (§4.4.9). CONFLICT vs Part 2 (§8b E.1/E.2). These are **not** in the Part 2/12/13 registries and are recorded as a fourth de-facto vocabulary.
- **Part 14 `schemas.md`** — `EVENT-ENVELOPE-v1` (§1.1, normative integration envelope). ⚠️ Its §11 source-authority note contains two errors corrected in §3.1/§9.13 (`tenant_id` present in Part 12 §4; Part 12 count is 104 not "64+"). Its "Related Events" reference 18 dotted names absent from Part 12 §22 — recorded as UNRESOLVED in §8c / GAP-XREF.
- **Part 14 `components.md`** — ownership used to *derive* producer/consumer in catalog rows.
- **Part 14 `interfaces.md`** — `INT-EVT-BUS-001`, `INT-C12-EVENT-001`, `INT-GOV-EVENT-001`, `INT-WF-CTRL-001` (command), `INT-HUMAN-001` (mixed), `INT-SEC-AUTH-001` (sync decision). FI-005 (§730–743) lists the PascalCase+Event names now captured as CONFLICT in §8b. ⚠️ `interfaces.md` §0 (line 37) and §142 still cite "**97 canonical EventTypes**" — the Part 2 spec error carried forward; this catalog uses the verified 118 (GAP-SPEC-COUNT §9.12, §8d.4).
- **Part 3 (FROZEN)** — authoritative SoT; uses Scheme-E PascalCase lifecycle names (`CoreComponentInitialized`, `ServiceHealthChanged`, `ServiceFailed`) colliding with Part 2 `SCREAMING_SNAKE_CASE` (§8d.1, CONFLICT). Verified directly (Part 3 §3.4).
- **Part 5** — references ~25 SDLC/ops event names (`CODING_REQUESTED`, `ENVIRONMENT_PREPARE`, `TRAFFIC_SHIFT`, `ROLLBACK_EXECUTE`, `MEMORY_SYNC_*`, `HUMAN_RESPONSE_RECEIVED`, …) that are **not** in any canonical registry; captured as UNRESOLVED in §8d.2. Verified directly (Part 5 §5.x tables).
- **Part 6** — capability-facade event *family labels* (`SkillFacadeEvent`, `MCPFacadeEvent`, `MemoryFacadeEvent`, `CollaborationEvent`) with `[UNSPECIFIED]` payloads; captured in §8d.3. Verified directly (Part 6 STEP1/STEP2).
- **Part 12 / Part 13 `adrs.md`** — `ADRComplianceViolation` (PROPOSED/unresolved; Rules G1.5/G3.5, P13-ADR-009) — an event name required by conformance yet absent from every ratified registry and violating the Part 12 §25 naming RFC.
- **`ARCHITECTURAL_INVENTORY.md`** — implementation snapshot; source for DERIVED/UNSPECIFIED names only (not a spec source).

**Integrity summary (rubric #10):** The genuine source conflicts — Part 2 vs Part 4 vs Part 12 vs schemas.md naming (§4.1, §8b), the two envelopes (GAP-ENV), the count discrepancies (GAP-SPEC-COUNT, GAP-P14-ENV), and the dangling schemas.md "Related Events" (GAP-XREF) — are **exposed, never hidden or normalized away**. No event type, guarantee, broker, fabric, or semantic was invented beyond Parts 0–13 (the prior `CACHE_INVALIDATED` invention was removed).

---

*Catalog complete. 273 EXISTING event types across three authoritative registries (Part 2 = 118, Part 12 = 104, Part 13 = 51) documented as integration-relevant and **verified against Parts 0–13** (Part 3 FROZEN lifecycle, Part 5 SDLC/ops names, Part 6 facade labels, Part 4 state/kernel vocabulary, and Part 14 schemas/integrations all audited); 14 GAPs; 8 CONFLICT naming-collision groups (now covering Schemes A–E incl. the Part 3 FROZEN PascalCase and the Part 12 internal PascalCase-vs-dotted contradiction); 18 UNRESOLVED schemas.md dangling references (§8c) + ~35 UNRESOLVED Part 3/5/6/integrations.md names (§8d); 1 PROPOSED unresolved event name; and a 5-surface command/request/response separation (§11). All counts verified against source line numbers; no count hardcoded without a cited authority. Divergences — two envelopes, four-part naming, count discrepancies, dangling refs — are exposed, never hidden or normalized. No event type, guarantee, broker, fabric, or semantic was invented beyond Parts 0–13 (the prior `CACHE_INVALIDATED` invention was removed). No other file was modified.*
