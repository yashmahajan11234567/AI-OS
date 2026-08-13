# AI-OS Architecture Specification v1.0
## Part 14: Integration-Oriented Component Inventory

**Version:** 1.0.0
**Status:** DRAFT — Inventory Only
**Date:** 2026-08-11
**Author:** Architecture Documentation (Part 14)
**Classification:** Informative — Cross-Part Component & Dependency Catalog

---

### 14.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART14-COMPONENTS |
| **Classification** | Informative — Inventory and Catalog |
| **Purpose** | Canonical, integration-oriented inventory of components, services, interfaces, external systems, and infrastructure dependencies defined in Parts 1–13; supports dependency analysis and integration review. |
| **Distribution** | All AI-OS engineers, architects, reviewers |
| **Related Documents** | `Part14/interfaces.md`, `Part14/adrs.md`, `Part14/schemas.md`, `Part14/events.md`; `Common/MASTER_ARCHITECTURE_ROADMAP.md`; `Common/ARCHITECTURAL_INVENTORY.md`; Parts 1–13 |

**Scope Rule (binding):** This document inventories only concepts explicitly defined in Parts 1–13. It does **not** create, rename, or redesign any component, service, interface, event, or schema. Where Parts 1–13 define a concept but do not establish a specific field, that field is marked **UNKNOWN / NOT YET DEFINED** rather than guessed. Contradictions between Parts 1–13 are recorded, not silently resolved (see §11).

---

## 1. How to Read This Inventory (Conventions)

### 1.1 The nine entity categories

This document distinguishes nine categories. Each entry is tagged with exactly one category. Confusion between categories is the most common integration defect, so the distinction is enforced throughout. **Two of the nine — `module` and `interface` — are explicitly NOT architectural components** (see the last two rows and the rule below); they are listed here only to prevent misclassification as a component.

| Category | Is it a component? | Definition | AI-OS mapping | Count in Parts 1–13 |
|----------|-------------------|------------|---------------|---------------------|
| **Core Component** | YES | A kernel-owned, foundational runtime primitive with a fixed contract; initialized and owned by `HermesKernel`. | The 4 Core Components per Part 1 §1.8.1. | 4 |
| **Core Manager** | YES | A kernel-owned manager exposing a capability domain via singleton accessor; implements `ICoreManager`. | The 9 Core Managers per Part 1 §1.8.1. | 9 |
| **Service** | YES | A `BaseService` derivative executing a phase or cross-cutting function; communicates EventBus-only. | Engineering Services (Part 5) + Human Interaction (Part 5/6). | 10 (Part 5) |
| **Facade Service** | YES | A `BaseService` that bridges the Definition Plane (a Core Manager) to the Execution Plane consumed by Engineering Services; enforces execution monopoly. | SkillService, CouncilService, MCPService, MemoryService (Part 6). | 4 (Part 6) |
| **External system** | YES (external) | A system outside AI-OS reached across a network/process boundary. | MCP servers, model providers, identity providers, Obsidian/Graphify, web search, regulatory frameworks. | 6 classes |
| **Infrastructure dependency** | YES (infra) | Runtime/platform substrate the system assumes. | In-memory EventBus, filesystem, Python runtime, libs, network. | 7 classes |
| **Logical architecture concept** | YES (logical) | A governance/logical grouping that is NOT a deployment unit and has no standalone lifecycle. | Part 13 governance components G-00..G-15. | 16 |
| **Module** | **NO** | An implementation/namespace unit (Python package, plugin directory, enrichment plugin). Parts 1–13 do **not** define "module" as an architectural component. Modular extension units (skills, MCP servers, AI Agency agents, memory backends, plugins) are inventoried under their correct component category, never as "Modules". | n/a — not a component class | 0 (not a component) |
| **Interface** | **NO** | A contract/surface (`INT-*`, extension-point signature, accessor, event/ schema contract) that a component *exposes or consumes*. An interface is NOT itself a component; it has no lifecycle or ownership independent of its owning component. | `INT-EVT-BUS-001`, `INT-SEC-AUTH-001`, `INT-CFS-BRIDGE-001`, `INT-KERNEL-ACC-001`, `INT-GOV-EVENT-001`, `ICoreManager`, etc. | n/a — not a component |

> **Classification rule (binding):** An **interface** is never classified as a **component**, and an **implementation detail** (e.g., a Python class name, a structlog backend, an in-repo module) is never elevated to an **architectural component**. If a catalog entry has only a contract and no owner/lifecycle, it is an interface, not a component. If it has only code-level existence, it is an implementation detail, recorded as `[Implementation]` and never promoted to a component. (See §9 for the module treatment and §11.11 for interface-vs-component discipline.)

### 1.2 Provenance markers (per field) — status vocabulary

Every field carries exactly one status marker from the canonical 8-status provenance vocabulary defined authoritatively in `adrs.md` Rule 0.5 and `context.md` §0.1. Reviewers use these to judge confidence. This vocabulary is binding for the entire Part 14 inventory; no other status term is used.

| Marker | Meaning | Example usage |
|--------|---------|---------------|
| **[EXISTING]** | Stated verbatim in a Part 1–13 source with a citation. | `[EXISTING] Part 1 §1.8.1` |
| **[DERIVED]** | Logically inferred from Parts 1–13 statements; not a direct quote but not invented. | `[DERIVED] from Part 4 ownership tables` |
| **[ASSUMPTION]** | A placeholder status retained from a source snapshot or inventory where a claim could not be independently confirmed against Parts 1–13 and is recorded as a stated assumption rather than a verified fact. Surfaced for ARB review; never treated as established. | `[ASSUMPTION] — retained from implementation inventory; not confirmed in Parts 1–13` |
| **[UNSPECIFIED]** | The source names the concept but does not define this field. | `[UNSPECIFIED] Part 14 interfaces.md §2.7` |
| **[GAP]** | The field is absent from Parts 1–13 and cannot be derived without guessing. | `[GAP] — no schema field-level definition in Parts 1–13` |
| **[PROPOSED]** | A useful concept, refinement, or component variant suggested for the architecture but **not yet established** in Parts 0–13. MUST NOT be mistaken for current architecture; implementations MUST NOT assume it exists. Recorded, not adopted. | `[PROPOSED] — capability-x façade variant; not in Parts 1–13` |
| **[FUTURE]** | Explicitly deferred to a future architecture version (e.g., v2.0) in a source Part; not part of the current v1.0 scope. | `[FUTURE] — distributed EventBus transport deferred to v2.0 per Part 12 events.md §10.1` |
| **[CONFLICT]** | Two or more source Parts contradict each other on this point. Surfaced in §11; never silently resolved (see directive #3). | `[CONFLICT] Part 1 §1.8.1 vs Part 3 §3.6` |
| **UNKNOWN / NOT YET DEFINED** | Used as the *value* when a field is `[UNSPECIFIED]`, `[GAP]`, `[ASSUMPTION]`, or `[CONFLICT]` and a concrete value cannot be supplied without industry assumption. Never filled by guesswork. | `UNKNOWN / NOT YET DEFINED` |

> **Status vs value:** `EXISTING / DERIVED / ASSUMPTION / UNSPECIFIED / GAP / PROPOSED / FUTURE / CONFLICT` are *statuses* on a field or entry; `UNKNOWN / NOT YET DEFINED` is the *placeholder value* used when the status is UNSPECIFIED/GAP/ASSUMPTION/CONFLICT and no source-establishing fact exists. `PROPOSED` and `FUTURE` describe entries that are intentionally not-yet-established — they carry their own status and do not fall back to `UNKNOWN`.
>
> **Authority (binding):** This vocabulary is defined once and followed identically across Part 14 (`adrs.md` Rule 0.5, `context.md` §0.1, this §1.2, and `glossary.md` Authority Rule 5). Where a sibling Part 14 document omits a status term (e.g., `glossary.md` Rule 5 lists 7 of the 8 and does not enumerate `ASSUMPTION` separately), this inventory treats the full 8-status set from `adrs.md`/`context.md` as authoritative, consistent with directive #3 ("context.md and adrs.md define the correct authority model. Follow them").

### 1.3 Source hierarchy (authority order)

When sources conflict (§11), authority is resolved in this order:

1. **Part 1 (Hermes Kernel)** — authoritative for the Kernel component/manager model (the "exactly 4 / exactly 9" rule).
2. **Per-Part specifications** (Part 2–13) — authoritative for their own domain (e.g., Part 5 for Engineering Services, Part 6 for Facades, Part 13 for governance).
3. **`Common/MASTER_ARCHITECTURE_ROADMAP.md`** — cross-part index; reflects an *older* naming in §4 and may lag the kernel model (see §11.1).
4. **`Common/ARCHITECTURAL_INVENTORY.md`** — an *implementation* snapshot (dated 2026-07-28, marked "architecture being frozen"); used only for implementation names/event detail, clearly tagged `[Implementation]`. It does NOT override the specification.

### 1.4 Source traceability — per-major-component authority & status

Per directive #5, the table below gives the authoritative source (Part + document + section where known) and integration status for every major component class. Detailed field tables follow in §3–§9.

| Component / class | Category | Authoritative source (Part · document · section) | Status |
|-------------------|----------|--------------------------------------------------|--------|
| `EventBus` | Core Component | Part 1 · ARCHITECTURE_SPEC_PART1 · §1.8.1 | EXISTING |
| `ServiceRegistry` | Core Component | Part 1 · §1.8.1; Part 3 · §3.4 | EXISTING |
| `ConfigurationManager` | Core Component | Part 1 · §1.8.1; Part 3 · §3.5 | EXISTING |
| `LifecycleManager` | Core Component | Part 1 · §1.8.1; Part 4 · §4.x Lifecycle Authority | EXISTING (CONFLICT vs Part 3 §3.6 naming — §11.1) |
| `StructuredLogger` | NOT a Core Component (logging substrate) | Part 0 · §0.4 Principle 12; Part 3 · §3.6 (names it "Core Component") | CONFLICT (classification) — §11.1 |
| `MemoryManager` (M1) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `LLMManager` (M2) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `ToolManager` (M3) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `StorageManager` (M4) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `ContextManager` (M5) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `AgentManager` (M6) | Core Manager | Part 1 · §1.8.1 | EXISTING |
| `WorkflowManager` (M7) | Core Manager | Part 1 · §1.8.1; Part 12 · components.md §1 | EXISTING |
| `SecurityManager` (M8) | Core Manager | Part 1 · §1.8.1; Part 4 · §4.7 | EXISTING |
| `ObservabilityManager` (M9) | Core Manager | Part 1 · §1.8.1; Part 4 · §4.11 | EXISTING |
| 10 Engineering Services | Service | Part 5 · §5.2 | EXISTING |
| 4 Capability Facade Services | Facade Service | Part 6 · STEP1–STEP3 | EXISTING |
| G-00..G-15 | Logical architecture concept | Part 13 · components.md | EXISTING |
| MCP servers / model providers / identity providers / Obsidian / Graphify / web search / regulatory frameworks | External system | Part 6 / Part 7 / Part 4 / Part 13 | EXISTING (interface contracts UNSPECIFIED for identity & regulatory) |
| In-memory EventBus, filesystem, Python runtime, libs, network | Infrastructure dependency | Part 0 · §0.2.2; `ARCHITECTURAL_INVENTORY.md` `[Implementation]` | EXISTING / `[Implementation]` |
| "Module" (any) | NOT a component | — | GAP as a category (§9) |

### 1.5 Per-component field checklist (requirement #7)

Every **major component** (the 4 Core Components, the 9 Core Managers, the 10 Engineering Services, the 4 Capability Facade Services, and the 16 Part 13 governance concepts) carries, *where applicable*, the following 12 fields. The mapping to the table rows used in §3–§6 is fixed so reviewers can verify completeness at a glance:

| Required field | Where it appears in each component table | Status vocabulary |
|----------------|-------------------------------------------|-------------------|
| **responsibility** | `Responsibility` row | EXISTING / DERIVED |
| **layer** | `Layer` row | EXISTING |
| **inputs** | `Inputs` row | EXISTING / DERIVED / UNSPECIFIED |
| **outputs** | `Outputs` row | EXISTING / DERIVED / UNSPECIFIED |
| **interfaces** | `Exposed interfaces` + `Consumed interfaces` rows | EXISTING / DERIVED |
| **events** | `Published events` + `Consumed events` rows | EXISTING / DERIVED / UNSPECIFIED |
| **dependencies** | `Dependencies` row | EXISTING / DERIVED |
| **dependents** | `Dependents` row | EXISTING / DERIVED |
| **boundaries** | `Integration boundary` row | EXISTING / DERIVED / UNSPECIFIED |
| **ownership** | `Ownership` row (added this pass) + `Authority & traceability` | EXISTING |
| **source** | `Source documents` row + `Authority & traceability` | citation |
| **status** | `Status` row (added this pass) + `Authority & traceability` | EXISTING / DERIVED / ASSUMPTION / UNSPECIFIED / GAP / PROPOSED / FUTURE / CONFLICT |

Where a field cannot be established from Parts 1–13, its *value* is **UNKNOWN / NOT YET DEFINED** and its *status* is UNSPECIFIED/GAP/CONFLICT — never guessed (requirement #8). Security/trust is carried in a dedicated `Security/trust` row. ADRs are carried in an `ADRs` row.

---

## 2. Architectural Layer Model

Layers are taken from `Common/MASTER_ARCHITECTURE_ROADMAP.md` §2. Each component below is tagged with its primary layer.

Foundation · Integration · Data · Security · Operations · Infrastructure · AI Core · Agent · Learning · Runtime · Cognitive · Collaboration (Orchestration) · Governance · Evolution

---

## 3. Core Components (4) — owned by HermesKernel

> **[EXISTING]** Part 1 §1.8.1: *"The four (4) Core Components: EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager."* The Kernel owns exactly these four; the number is FIXED (Part 1 §1.7.2 / INV-CM-004..006).
>
> **Authority note (directive #1):** Part 1 is the authoritative source for Kernel composition. Other sources that disagree are **not** permitted to override it silently:
> - **Part 0 §3.2 / §0.3.2** names a *different* four: `EventBus, StateManager, WorkflowManager, ResourceManager`. → **CONFLICT** (see §11.1).
> - **Part 3 §3.6 (C4 StructuredLogger)** labels `StructuredLogger` *"the last Core Component"*, yet Part 3 elsewhere names `LifecycleManager` as the Phase-3 core initializer. → **CONFLICT** inside Part 3 and vs Part 1 (see §11.1).
> - **Part 4 §4A/§4B** lists `ConfigurationAuthority` and `IdentityProvider` as *"Core Components"*. → **CONFLICT** (see §11.1, §11.8); `ConfigurationAuthority` is in fact a *role* of `ConfigurationManager` (Part 1 §93), and `IdentityProvider` is an external system (Part 4 §4B).
> - **`interfaces.md` §2.1** substitutes `StructuredLogger` for `LifecycleManager`. → **CONFLICT** (see §11.1).
> - **Roadmap §4** uses older names (`Configuration Service`, `State Manager`). → NAME DIVERGENCE, not authoritative (see §13).
>
> Part 14 follows **Part 1** for the kernel set and records every divergence as a contradiction; it does not merge or rename.

### 3.1 EventBus

| Field | Value |
|-------|-------|
| **Category** | Core Component |
| **Name** | `EventBus` |
| **Purpose** | `[EXISTING]` Central publish/subscribe substrate for all asynchronous communication (Part 1 §1.8.1; Part 2 §2.2). |
| **Layer** | Foundation / Integration |
| **Responsibility** | `[EXISTING]` Publish/subscribe, routing, ordering, priority lanes, retry/dead-letter queues, event history, schema validation — the sole communication mechanism (Part 2 §2.2–2.4; Part 4 states EventBus exclusivity). |
| **Inputs** | `[EXISTING]` `Event` instances + subscription registrations (Part 2 §2.2). |
| **Outputs** | `[EXISTING]` Delivered events; history; stats (Part 2). |
| **Exposed interfaces** | `INT-EVT-BUS-001` `[EXISTING] Part 2 §2.2–2.9`. |
| **Consumed interfaces** | None (it is the substrate). |
| **Published events** | None (infrastructure); it routes all canonical events. |
| **Consumed events** | None (infrastructure). |
| **Dependencies** | `[DERIVED]` ConfigurationManager (capacity/timeout config), StructuredLogger/ObservabilityManager (event logging) — `[UNSPECIFIED]` which exactly. |
| **Dependents** | `[EXISTING]` All Core Components, Core Managers, Services, Facades, governance components. |
| **Integration boundary** | `[EXISTING]` In-process, in-memory bus (v1.0 single-process); distributed bus is `UNRES-EVT-DIST-001`, out of scope (interfaces.md §4.3). |
| **Ownership** | `[EXISTING]` Owned exclusively by `HermesKernel` (Part 1 §1.8.1); exposed via global singleton accessor `kernel.bus`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1 Core Component registry). No conflict on EventBus itself. |
| **Security/trust** | `[UNSPECIFIED]` Bus-level authn/authz is "Unspecified" (interfaces.md §2.6). Governance events carry their own signing/ACL (INT-GOV-EVENT-001); Part 12 events carry their own signing/PII-redaction (INT-C12-EVENT-001). |
| **ADRs** | `[EXISTING]` ADR-001 (Event-First Communication, Roadmap §6 / Part 9 ADR-002); ADR-008 (Immutable Events); ADR-009 (Explicit Failure Handling). `[DERIVED]` Part 10 ADR-003 (Event Delivery Guarantees). |
| **Source documents** | Part 1 §1.7.4, §1.8.1; Part 2 §2.2–2.9; Part 3 §3.3.4; Part 14 interfaces.md §2.6. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (Core Component registry). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None on EventBus itself; only on the *other three* slots of the 4-set (§11.1). |

### 3.2 ServiceRegistry

| Field | Value |
|-------|-------|
| **Category** | Core Component |
| **Name** | `ServiceRegistry` |
| **Purpose** | `[EXISTING]` Authoritative service registration, discovery, dependency topology, health tracking (Part 3 §3.4.4–3.4.7; interfaces.md §2.5). |
| **Layer** | Foundation |
| **Responsibility** | `[EXISTING]` Topological start/stop by `depends_on`; health checks; lifecycle events (Part 3 §3.4). |
| **Inputs** | `[EXISTING]` `ServiceRegistration` records (interfaces.md §2.5). |
| **Outputs** | `[EXISTING]` Service start/stop ordering; `ServiceRegistered` / `ServiceHealthChanged` events. |
| **Exposed interfaces** | `INT-SVC-REG-001` `[EXISTING] Part 3 §3.4.4–3.4.7`. |
| **Consumed interfaces** | `INT-KERNEL-ACC-001`, `INT-CORE-CMP-001` (health), `INT-EVT-BUS-001`. |
| **Published events** | `[EXISTING]` `ServiceRegistered`, `ServiceInitialized`, `ServiceShutdown`, `ServiceHealthChanged`, `ServiceDegraded`, `ServiceFailed` (interfaces.md §2.5). |
| **Consumed events** | `[UNSPECIFIED]` not enumerated in source. |
| **Dependencies** | `[DERIVED]` EventBus; HermesKernel. |
| **Dependents** | `[DERIVED]` LifecycleManager, WorkflowManager, all Services. |
| **Integration boundary** | In-process. |
| **Ownership** | `[EXISTING]` Owned exclusively by `HermesKernel` (Part 1 §1.8.1); accessor `kernel.services`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1). Alias "Service Registry" (Roadmap §4) only. |
| **Security/trust** | `[UNSPECIFIED]` authn/authz "Unspecified" (interfaces.md §2.5). |
| **ADRs** | `[DERIVED]` ADR-001 (Event-First), ADR-004 (Fixed Component Counts). |
| **Source documents** | Part 1 §1.8.1; Part 3 §3.4; Part 14 interfaces.md §2.5. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1. **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None on ServiceRegistry; Roadmap labels it "Service Registry" (alias, §13). |

### 3.3 ConfigurationManager

| Field | Value |
|-------|-------|
| **Category** | Core Component |
| **Name** | `ConfigurationManager` |
| **Purpose** | `[EXISTING]` Centralized, layered, immutable configuration management (Part 1 §1.10.2; Part 3 §3.5; interfaces.md §2.10). |
| **Layer** | Foundation |
| **Responsibility** | `[EXISTING]` 4-layer merge (defaults → app.yaml → env.yaml → env vars); validation; freeze after init (runtime mutation prohibited) (Part 1 §1.10.2; Part 3 §3.5). |
| **Inputs** | `[EXISTING]` Configuration sources (files, env vars). |
| **Outputs** | `[EXISTING]` Immutable configuration view; `ConfigurationFrozen` / `ConfigurationChanged` events. |
| **Exposed interfaces** | `INT-CONFIG-READ-001` `[EXISTING] Part 1 §1.10.2, Part 3 §3.5`. |
| **Consumed interfaces** | `INT-KERNEL-ACC-001`, `INT-EVT-BUS-001`. |
| **Published events** | `[EXISTING]` `ConfigurationFrozen`, `ConfigurationChanged` (interfaces.md §2.10). |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus. |
| **Dependents** | `[DERIVED]` All Core Managers, Services, Facades. |
| **Integration boundary** | In-process; reads local config files/env. |
| **Ownership** | `[EXISTING]` Owned exclusively by `HermesKernel` (Part 1 §1.8.1); accessor `kernel.config`. The *Configuration Authority* **role** (Part 1 §93; `ConfigurationAuthority` in Part 4) belongs to this component — it is a role, not a separate component (§11.8). Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1). Alias "Configuration Service" (Roadmap §4) only. |
| **Security/trust** | `[DERIVED]` Secrets handled via `SecretManager` (Part 4); the config bus itself is not a security boundary. |
| **ADRs** | `[EXISTING]` ADR-010 (Declarative Layered Configuration); ADR-013 (Extension Points Governance). `[DERIVED]` Part 9 ADR-001 (Infrastructure Layering). |
| **Source documents** | Part 1 §1.10.2; Part 3 §3.5; Part 14 interfaces.md §2.10. |
| **Alias note** | Roadmap §4 names this **"Configuration Service"** — same concept, different label (see §11.1). |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1. **Status:** EXISTING. **Part 14 created?** No. **Naming distinction (directive #4):** "Configuration Authority" (Part 1 §93; `ConfigurationAuthority` in Part 4 §4A/§4B/§4C) is a *ROLE/PERMISSION* owned by `ConfigurationManager` — NOT a separate component. Part 14 does **not** rename `ConfigurationManager` to `ConfigurationAuthority` and does **not** promote the role to a component. See §11.8. |

### 3.4 LifecycleManager

| Field | Value |
|-------|-------|
| **Category** | Core Component |
| **Name** | `LifecycleManager` |
| **Purpose** | `[EXISTING]` Kernel lifecycle state machine ownership and recovery coordination (Part 1 §1.8.1; Part 4 §4.x Lifecycle Authority). |
| **Layer** | Foundation |
| **Responsibility** | `[EXISTING]` Exclusive ownership of the kernel lifecycle state machine (states: UNINITIALIZED, INITIALIZING, OPERATIONAL, DEGRADED, SHUTTING_DOWN, TERMINATED, ROLLBACK_IN_PROGRESS, RECOVERY_IN_PROGRESS) (Part 4 §4.x). Coordinates rollback/recovery with HealthManager recommendations. |
| **Inputs** | `[DERIVED]` State restore requests (recovery), shutdown signals. |
| **Outputs** | `[DERIVED]` Lifecycle state transitions; `CoreComponentInitialized` / `CoreManagerInitialized` / shutdown events. |
| **Exposed interfaces** | `INT-CORE-CMP-001` (health), `INT-KERNEL-ACC-001` accessor. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-HEALTH-001` (HealthManager readiness). |
| **Published events** | `[DERIVED]` Lifecycle transition events; `KernelStarted`/`KernelStopped` per implementation inventory `[Implementation]`. |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus, HealthManager, StateManager (for restore). |
| **Dependents** | `[DERIVED]` All managers/services (lifecycle gating). |
| **Integration boundary** | In-process. |
| **Ownership** | `[EXISTING]` Lifecycle state machine owned exclusively by `HermesKernel` (Part 1 §1.8.1; Part 4 §4.x Lifecycle Authority). Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` per Part 1 §1.8.1 — but **[CONFLICT]** on the slot: Part 3 §3.6 + interfaces.md §2.1 substitute `StructuredLogger` (see §11.1 CONFLICT-02/04). Not merged. |
| **Security/trust** | `[DERIVED]` Lifecycle transitions are privileged; per Part 4 `KernelNotReadyError` guards accessor access before RUNNING. |
| **ADRs** | `[DERIVED]` ADR-001; Part 9 ADR-006 (Infrastructure Lifecycle Standardization). |
| **Source documents** | Part 1 §1.8.1; Part 4 §4.x (Lifecycle Authority); Part 14 interfaces.md §2.1–2.3. |
| **Contradiction note** | **[CONFLICT]** `interfaces.md` §2.1 lists `StructuredLogger` as a Core Component instead of `LifecycleManager`. Part 3 §3.6 (C4) *also* labels `StructuredLogger` "the last Core Component" while Part 3 elsewhere depends on `LifecycleManager`. Part 1 is authoritative: the 4 Core Components are EventBus/ServiceRegistry/ConfigurationManager/**LifecycleManager**. `StructuredLogger` is **not** a Core Component in Part 1. Part 14 does **not** merge the two (directive #3) — see §11.1. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (LifecycleManager is the 4th Core Component). **Status:** EXISTING (but CONFLICT on the slot vs Part 3 §3.6 / interfaces.md / Part 0 §3.2). **Part 14 created?** No. **Part 14 position:** Keep `LifecycleManager`; surface `StructuredLogger` as a rival claim, not a synonym. |

---

## 4. Core Managers (9) — owned by HermesKernel

> **[EXISTING]** Part 1 §1.8.1 Core Manager Registry (M1–M9), FIXED count (Part 1 §1.8: *"This number is FIXED and MUST NOT change without ARB approval."*). All implement `ICoreManager` (`INT-CORE-MGR-001`). Each is exposed via a singleton accessor on `HermesKernel.instance`.

### 4.1 MemoryManager (M1)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `MemoryManager` |
| **Purpose** | `[EXISTING]` Episodic, semantic, working memory; context assembly; retention policies (Part 1 §1.8.1 M1; Roadmap §4; Part 9). |
| **Layer** | Learning |
| **Responsibility** | `[DERIVED]` 5 memory types (WORKING, CLAUDE, ENGINEERING, OBSIDIAN, GRAPHIFY per `[Implementation]` inventory); pluggable backends; consolidation pipeline; TTL; stats. |
| **Inputs** | `[DERIVED]` Memory store/retrieve/consolidate requests. |
| **Outputs** | `[DERIVED]` Stored/retrieved/consolidated memory; memory events. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.memory`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`, `INT-CFS-BRIDGE-001` (via MemoryService facade). |
| **Published events** | `[EXISTING]` `MemoryStored`, `MemoryRetrieved`, `MemoryUpdated`, `MemoryConsolidated`, `MemoryPruned` (interfaces.md §2.8). |
| **Consumed events** | `[UNSPECIFIED]` (facade `MemoryService` consumes `LearningCaptured`, `CheckpointCreated` per `[Implementation]`). |
| **Dependencies** | `[DERIVED]` EventBus; external backends Obsidian vault, Graphify graph store (§7). |
| **Dependents** | `[DERIVED]` MemoryService (facade), LearningService, agents. |
| **Integration boundary** | In-process manager; bridges to **external** Obsidian/Graphify backends (§7). |
| **Ownership** | `[EXISTING]` Single-owner of the memory capability domain per ADR-003 / CC-S-001 (Part 4); exposed via `kernel.memory`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M1). Note: Part 0 §3.2 lists a separate `StateManager` as a Core Component; that is CONFLICT-01, not an alias of M1 (§11.1). |
| **Security/trust** | `[DERIVED]` Memory may hold sensitive context; backend access credentialed via `SecretManager` (Part 4). Bus-level authz `[UNSPECIFIED]`. |
| **ADRs** | `[DERIVED]` ADR-005 (Spec/Implementation Separation); Part 9 ADR-005 (Hybrid Consistency Model). |
| **Source documents** | Part 1 §1.8.1; Part 9; Part 14 interfaces.md §2.8. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M1). **Status:** EXISTING. **Part 14 created?** No. **Note:** Part 0 §3.2 lists a separate `StateManager` as a Core Component; Part 1 folds state under Core Managers/accessors. `MemoryManager` is unaffected; `StateManager` is a CONFLICT, not an alias of M1 (§11.1). |

### 4.2 LLMManager (M2)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `LLMManager` |
| **Purpose** | `[EXISTING]` Model routing, prompt templating, token budgeting, provider abstraction (Part 1 §1.8.1 M2; Roadmap §4; Part 7). |
| **Layer** | AI Core |
| **Responsibility** | `[DERIVED]` Capability-based routing; cost optimization; fallback chains across Claude/local/cloud. |
| **Inputs** | `[DERIVED]` Inference requests. |
| **Outputs** | `[DERIVED]` Model responses. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.llm`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`. |
| **Published events** | `[UNSPECIFIED]` (Part 5 §5.1.1 references consuming "ModelRouter" capability — see §11.3). |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus; **external** model providers (§7). |
| **Dependents** | `[DERIVED]` AIAgencyService, agents, ToolManager. |
| **Integration boundary** | In-process manager; bridges to **external** model providers (network boundary). |
| **Ownership** | `[EXISTING]` Single-owner of model-routing capability per ADR-003 (Part 1 M2; Part 4 CC-S-001). Accessor `kernel.llm`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M2). Alias "Model Router" (Roadmap §4) only. |
| **Security/trust** | `[DERIVED]` Provider trust + credentials via `SecretManager`; per Part 10 ADR-005 (Security Model). Bus-level authz `[UNSPECIFIED]`. |
| **ADRs** | `[DERIVED]` Part 10 ADR-005 (Security Model). |
| **Source documents** | Part 1 §1.8.1; Part 7; Roadmap §4. |
| **Alias note** | Roadmap §4 names this **"Model Router"**. Part 1 kernel model uses **`LLMManager`**. Same capability domain; different label (see §11.3). |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M2). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None on M2; only the label `Model Router` diverges (alias, §13). |

### 4.3 ToolManager (M3)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `ToolManager` |
| **Purpose** | `[EXISTING]` Tool registry, execution sandbox, permission mediation, result caching (Part 1 §1.8.1 M3; Roadmap §4; Part 8). |
| **Layer** | Agent |
| **Responsibility** | `[DERIVED]` Tool/skill registration and execution orchestration; permission mediation. |
| **Inputs** | `[DERIVED]` Tool execution requests. |
| **Outputs** | `[DERIVED]` Execution results. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.tools`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`, `INT-SEC-AUTH-001`. |
| **Published events** | `[EXISTING]` `SkillLoaded`, `SkillUnloaded`, `SkillExecuted`, `SkillFailed`, `MCPServerConnected`, `MCPServerDisconnected`, `MCPToolCalled`, `MCPToolResult` `[Implementation]` (Part 6/8). |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus; **external** MCP servers (§7); `SecurityManager` (sandbox/trust). |
| **Dependents** | `[DERIVED]` SkillService/MCPService (facades), agents. |
| **Integration boundary** | In-process manager; bridges to **external** MCP servers (network/process boundary). |
| **Ownership** | `[EXISTING]` Single-owner of the tool/skill/MCP capability domain per ADR-003 (Part 1 M3; Part 4 CC-S-001). Accessor `kernel.tools`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M3). Aliases "Skill Manager" + "MCP Manager" (Roadmap §4 subdomains) only. |
| **Security/trust** | `[EXISTING]` Explicit trust boundary: MCP server trust requires connection verification + tool allow-lists (Part 6 ADR-6.8.4); skill execution requires sandboxing (Part 6 §12.1). |
| **ADRs** | `[EXISTING]` ADR-003 (Capability Manager Ownership — see §10.2); Part 6 ADR-6.8.4, ADR-6.8.5; Part 10 ADR-009 (Plugin Isolation). |
| **Source documents** | Part 1 §1.8.1; Part 6 STEP3_MCP; Part 8; Part 14 interfaces.md §2.2, §2.8. |
| **Alias note** | Roadmap §4 splits this domain into **"Skill Manager"** + **"MCP Manager"**. Part 1 kernel model uses a single **`ToolManager`**. (See §11.3 and §13 duplicate/alias table.) |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M3). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None on M3; `SkillManager`/`MCPManager` are Roadmap subdomain labels (alias, §13). `ToolManager` is NOT renamed to them. |

### 4.4 StorageManager (M4)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `StorageManager` |
| **Purpose** | `[EXISTING]` Persistence abstraction; schemas, migrations, transactions, backups (Part 1 §1.8.1 M4; Roadmap §4; Part 3). |
| **Layer** | Data |
| **Responsibility** | `[DERIVED]` Persistence abstraction across backends. |
| **Inputs** | `[DERIVED]` Persistence requests. |
| **Outputs** | `[DERIVED]` Persisted/retrieved data. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.storage`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`. |
| **Published events** | `[UNSPECIFIED]`. |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus; filesystem/disk (§8). |
| **Dependents** | `[DERIVED]` StateManager, CheckpointManager, WorkflowManager, all stateful services. |
| **Integration boundary** | In-process; persistence to local/network storage. |
| **Ownership** | `[EXISTING]` Single-owner of the persistence capability domain per ADR-003 (Part 1 M4; Part 4 CC-S-001). Accessor `kernel.storage`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M4). Part 0 §3.2's separate `StateManager`/`ResourceManager` are CONFLICT-01, not aliases of M4 (§11.1). |
| **Security/trust** | `[DERIVED]` Persistence confidentiality `[UNSPECIFIED]` at manager level. |
| **ADRs** | `[DERIVED]` Part 9 ADR-006 (Lifecycle Standardization); Part 10 ADR-004 (Checkpoint Storage). |
| **Source documents** | Part 1 §1.8.1; Part 3; Roadmap §4. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M4). **Status:** EXISTING. **Part 14 created?** No. **Note:** Part 0 §3.2 lists a separate `StorageManager`-like `StateManager`/`ResourceManager` as Core Components; Part 4 references `StateManager`/`CheckpointManager`/`RetryManager`; these are NOT in Part 1's fixed 9 Managers and are recorded as CONFLICT/divergence (§11.1, §11.7), not merged into M4. |

### 4.5 ContextManager (M5)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `ContextManager` |
| **Purpose** | `[EXISTING]` Conversation context, window management, compression, relevance scoring (Part 1 §1.8.1 M5; Roadmap §4; Part 11). |
| **Layer** | Cognitive |
| **Responsibility** | `[DERIVED]` Context window management and assembly. |
| **Inputs** | `[DERIVED]` Context update/query requests. |
| **Outputs** | `[DERIVED]` Assembled context windows. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.context`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`. |
| **Published events** | `[UNSPECIFIED]`. |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus; MemoryManager (context assembly). |
| **Dependents** | `[DERIVED]` Agents, services. |
| **Integration boundary** | In-process. |
| **Ownership** | `[EXISTING]` Single-owner of the context capability domain per ADR-003 (Part 1 M5; Part 4 CC-S-001). Accessor `kernel.context`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M5). |
| **Security/trust** | `[UNSPECIFIED]`. |
| **ADRs** | `[UNSPECIFIED]`. |
| **Source documents** | Part 1 §1.8.1; Roadmap §4; Part 11. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M5). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None. |

### 4.6 AgentManager (M6)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `AgentManager` |
| **Purpose** | `[EXISTING]` Agent spawning, lifecycle, communication, resource quotas (Part 1 §1.8.1 M6; Roadmap §4; Part 8). |
| **Layer** | Agent |
| **Responsibility** | `[DERIVED]` Agent registration/lifecycle; resource quota enforcement. |
| **Inputs** | `[DERIVED]` Agent lifecycle events; spawn requests. |
| **Outputs** | `[DERIVED]` Agent state. |
| **Exposed interfaces** | `INT-CORE-MGR-001`; accessor `kernel.agents`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`, `INT-SEC-AUTH-001`. |
| **Published events** | `[EXISTING]` `agent.lifecycle.registered`, `agent.lifecycle.deregistered`, `agent.lifecycle.heartbeat` (INT-C12-EVENT-001). |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` EventBus; `SecurityManager` (authority/quotas). |
| **Dependents** | `[DERIVED]` CouncilService (facade), AIAgencyService, agents. |
| **Integration boundary** | In-process; council decisions may escalate to external human (`HumanInteractionService`). |
| **Ownership** | `[EXISTING]` Single-owner of the agent-lifecycle capability domain per ADR-003 (Part 1 M6; Part 4 CC-S-001). Accessor `kernel.agents`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M6). Alias "AI Agency" (Roadmap §4) only. |
| **Security/trust** | `[DERIVED]` Authority/escalation cross human-oversight boundary (ADR-006). Bus-level authz `[UNSPECIFIED]`. |
| **ADRs** | `[EXISTING]` ADR-003 (Capability Manager Ownership); ADR-006 (Human Oversight). |
| **Source documents** | Part 1 §1.8.1; Part 8; Part 12; Part 14 interfaces.md §2.8. |
| **Alias note** | Roadmap §4 names the agent-orchestration concept **"AI Agency"**; Part 12 references **`ai_agency.py`** as the implementation of AIAgencyService/final-judge. Same domain; Part 1 kernel model uses **`AgentManager`** (see §11.3, §13). |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M6). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** None on M6; `AI Agency` is a label/alias (§13). |

### 4.7 WorkflowManager (M7)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `WorkflowManager` |
| **Purpose** | `[EXISTING]` Workflow definition, execution, checkpointing, compensation (Part 1 §1.8.1 M7; Roadmap §4; Part 12). |
| **Layer** | Collaboration (Orchestration) |
| **Responsibility** | `[EXISTING]` Parse workflow definitions into state machines; decompose into task units; assign to agents; track transitions; checkpoint; enforce timeout/retry/circuit-breaker (Part 12 components.md §1). |
| **Inputs** | `[EXISTING]` `WorkflowDefinition` (from Council Manager, Delegation Manager, or external orchestrator); `CapabilityProfile[]`; `AgentStatus[]`; `SharedContext`; config overrides; `ResourceReservation` (Part 12 components.md §1). |
| **Outputs** | `[EXISTING]` `WorkflowInstance`; `TaskUnit[]` to Communication Bus; `Checkpoint` records; `WorkflowEvent[]` (Part 12). |
| **Exposed interfaces** | `INT-WF-CTRL-001` `[EXISTING] Part 4 §4.6.3, §4.6.11`; `INT-CORE-MGR-001`; accessor `kernel.workflows`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`, `INT-SEC-AUTH-001`, `INT-SVC-REG-001`, `Communication Bus`/`Capability Registry`/`Agent Directory`/`Shared Context Manager`/`Scheduler` (Part 12 — these are Part 12 abstractions; see §11.3). |
| **Published events** | `[EXISTING]` `WorkflowStarted`, `TaskDispatched`, `TaskCompleted`, `WorkflowCompleted`, `WorkflowFailed`, `WorkflowCancelled`, `CheckpointTaken`, `WorkflowPaused`, `WorkflowResumed` (Part 12 components.md §1); also `workflow.lifecycle.*`, `workflow.step.*` (INT-C12-EVENT-001). |
| **Consumed events** | `[DERIVED]` `TaskCreated`, `RetryBudgetExhausted`, `CheckpointRestored` `[Implementation]`. |
| **Dependencies** | `[DERIVED]` StateManager, CheckpointManager, RetryManager, RootCauseAnalyzer `[Implementation]`; SecurityManager, StorageManager, ResourceManager, HealthManager, ObservabilityManager (interfaces.md §2.9). |
| **Dependents** | `[DERIVED]` Engineering Services; LifecycleManager; orchestration layers. |
| **Integration boundary** | In-process manager; external control via `INT-WF-CTRL-001`. |
| **Ownership** | `[EXISTING]` Single-owner of the workflow capability domain per ADR-003 (Part 1 M7; Part 4 CC-S-001). Accessor `kernel.workflows`. Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M7). **Note CONFLICT-01:** Part 0 §3.2 lists `WorkflowManager` as a *Core Component*; Part 1 lists it as a *Core Manager*. Part 14 follows Part 1 (Core Manager) and does not promote it (§11.1). Part 12 abstractions (Communication Bus, etc.) are NOT promoted to components (§11.3). |
| **Security/trust** | `[DERIVED]` Control operations require `SecurityManager` authorization (`INT-SEC-AUTH-001`); specific authz policy `[UNSPECIFIED]`. |
| **ADRs** | `[EXISTING]` ADR-009 (Explicit Failure Handling). `[DERIVED]` Part 9 ADR-006 (Lifecycle Standardization). |
| **Source documents** | Part 1 §1.8.1; Part 4 §4.6; Part 12 components.md §1; Part 14 interfaces.md §2.9. |
| **Alias note** | Roadmap §4 lists **"Workflow Manager"** with *Definition Part = Part 12*, whereas Part 1 lists it as a **Core Manager** (M7). Reconciled in §11.1: WorkflowManager is a Core Manager (Part 1 is authoritative for Kernel composition); Part 12 details its workflow semantics. |
| **Implementation alias** | `[Implementation]` `workflow.py` (`ARCHITECTURAL_INVENTORY.md`). |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M7). **Status:** EXISTING. **Part 14 created?** No. **Conflicts?** Part 0 §3.2 lists `WorkflowManager` as a *Core Component*; Part 1 lists it as a *Core Manager* (M7). This is a classification CONFLICT recorded in §11.1 — Part 14 follows Part 1 (Core Manager) and does NOT promote it to Core Component. Part 12 abstractions (Communication Bus, Capability Registry, etc.) are NOT promoted to components (§11.3). |

### 4.8 SecurityManager (M8)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `SecurityManager` |
| **Purpose** | `[EXISTING]` Authentication, authorization, audit, secrets, encryption (Part 1 §1.8.1 M8; Part 4; Roadmap §4). |
| **Layer** | Security |
| **Responsibility** | `[EXISTING]` ABAC authorization decision point and security enforcement for all protected operations (Part 4 §4.7; interfaces.md §2.7). |
| **Inputs** | `[EXISTING]` Authorization requests: Principal, action, resource, context (interfaces.md §2.7). |
| **Outputs** | `[EXISTING]` Decision: `ALLOW` / `DENY` / `CHALLENGE` (interfaces.md §2.7). |
| **Exposed interfaces** | `INT-SEC-AUTH-001` (`SecurityManager.authorize`) `[EXISTING] Part 4 §4.7.4`; `INT-CORE-MGR-001`; accessor `kernel.security`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-CONFIG-READ-001`, policy evaluation (PolicyEngine / G-02). |
| **Published events** | `[EXISTING]` `AuthorizationDecisionEvent`, `AuthenticationFailedEvent` (interfaces.md §2.7). |
| **Consumed events** | `[UNSPECIFIED]`. |
| **Dependencies** | `[DERIVED]` PolicyEngine / Policy Evaluation Engine (Part 4 / G-02); Identity/Authentication (Part 4); SecretManager. |
| **Dependents** | `[EXISTING]` All Core Managers, Services, WorkflowManager, Facade Services (interfaces.md §2.7). |
| **Integration boundary** | In-process manager; enforcement point for all protected operations. |
| **Ownership** | `[EXISTING]` Single-owner of the security/authorization capability domain per ADR-003 (Part 1 M8; Part 4 §4.7; CC-S-001). Accessor `kernel.security`. `IdentityProvider` (Part 4 §4B) is an *external* authn source, NOT merged into M8 (§11.8). Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M8). |
| **Security/trust** | **[EXISTING] This IS a trust boundary.** Implements zero-trust (every action authorized). Per Part 6 ADR-6.8.2, authorization ownership belongs exclusively to execution facades; ADR-6.8.3, identity ownership belongs exclusively to manager space. Unauthenticated requests rejected before authorization (Roadmap §8 invariants 2–4). |
| **ADRs** | `[EXISTING]` ADR-003 (Capability Manager Ownership); ADR-006 (Human Oversight); Part 6 ADR-6.8.1–6.8.5; P13-ADR-002 (Separation of Policy and Enforcement). |
| **Source documents** | Part 1 §1.8.1; Part 4 §4.7; Part 6 STEP8; Part 14 interfaces.md §2.7. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M8). **Status:** EXISTING. **Part 14 created?** No. **Naming distinction (directive #4):** `SecurityManager` owns authorization (Part 4 §4.7.4). Part 4 §4B references inbound `IdentityProvider` as an *external* authn source and `ConfigurationAuthority` for policy storage. `IdentityProvider` is an **External system** (§7), NOT an internal Core Component; `ConfigurationAuthority` is a *role* of `ConfigurationManager` (§11.8). Neither is merged into M8. |

### 4.9 ObservabilityManager (M9)

| Field | Value |
|-------|-------|
| **Category** | Core Manager |
| **Name** | `ObservabilityManager` |
| **Purpose** | `[EXISTING]` Metrics, tracing, logging, alerting, profiling (Part 1 §1.8.1 M9; Roadmap §4; Part 5). |
| **Layer** | Operations |
| **Responsibility** | `[DERIVED]` Metrics exposition, tracing, health aggregation, alerting; consumes governance events for observability. |
| **Inputs** | `[DERIVED]` Telemetry events; health statuses. |
| **Outputs** | `[DERIVED]` Metrics, traces, alerts. |
| **Exposed interfaces** | `INT-CORE-MGR-001` (init/health/metrics); accessor `kernel.observability`. |
| **Consumed interfaces** | `INT-EVT-BUS-001`, `INT-HEALTH-001`, governance events (`INT-GOV-EVENT-001`). |
| **Published events** | `[EXISTING]` `MetricsAlert` `[Implementation]`. |
| **Consumed events** | `[DERIVED]` Governance events, service health events (interfaces.md §2.5, §2.11). |
| **Dependencies** | `[DERIVED]` EventBus; StructuredLogger (logging backend). |
| **Dependents** | `[DERIVED]` All components (telemetry); governance (alerting). |
| **Integration boundary** | In-process; may export telemetry to external backends (backend selection `[UNKNOWN / NOT YET DEFINED]` — Part 10 ADR-010 planned). |
| **Ownership** | `[EXISTING]` Single-owner of the observability capability domain per ADR-003 (Part 1 M9; Part 4 §4.11; CC-S-001). Accessor `kernel.observability`. `StructuredLogger` is the logging *substrate* it consumes, not a Core Manager (CONFLICT-02, §11.1). Part 14 asserts no ownership. |
| **Status** | `[EXISTING]` (Part 1 §1.8.1, M9). Aliases "Observability" (Roadmap §4) / "Root Cause Analyzer" `[Implementation]` only. |
| **Security/trust** | `[DERIVED]` Telemetry may contain sensitive data; payload redaction required (Part 12 events redact PII/secrets). Manager-level authz `[UNSPECIFIED]`. |
| **ADRs** | `[EXISTING]` Part 9 ADR-007 (Observability-First Design); Part 10 ADR-006 (Telemetry Collection), ADR-010 (Observability Backend Selection, planned). |
| **Source documents** | Part 1 §1.8.1; Part 4 §4.11; Part 5; Part 14 interfaces.md §2.2, §2.5. |
| **Alias note** | Roadmap §4 calls this **"Observability"**; Part 5 diagnostic subset is named **"Root Cause Analyzer"** in `[Implementation]`. `ObservabilityManager` is the canonical spec name. |
| **Authority & traceability** | **Authoritative source:** Part 1 §1.8.1 (M9). **Status:** EXISTING. **Part 14 created?** No. **Note:** `StructuredLogger` (Part 0 Principle 12 / Part 3 §3.6) is the logging *substrate* that ObservabilityManager consumes; it is NOT a Core Manager and is classified CONFLICT-vs-Core-Component in §11.1. Not merged into M9. |

---

## 5. Logical Architecture Concepts — Part 13 Governance Components (G-00 .. G-15)

> **[EXISTING]** Part 13 `components.md`: 16 governance components. These are **logical architecture concepts**, NOT deployment units (Part 13 `components.md` §7.2: logical vs physical is out of scope). They are inventoried here as a distinct category to prevent misclassification as Services or Core Managers.

### 5.1 Governance component table

| ID | Name | Tier | Primary Domain | Classification |
|----|------|------|----------------|----------------|
| G-00 | Governance Manager | 0 Foundation | Orchestration, lifecycle, dispatch | Logical concept |
| G-01 | Policy Manager | 0 Foundation | Policy CRUD, lifecycle, distribution | Logical concept |
| G-02 | Policy Evaluation Engine | 1 Execution | Runtime policy eval, decision records | Logical concept |
| G-03 | Governance Registry | 0 Foundation | Canonical state of governance artifacts | Logical concept |
| G-04 | Governance Council | 1 Execution | Governance body interface, charter, committees | Logical concept |
| G-05 | Decision Authority Manager | 1 Execution | Authority grants, thresholds, constraints | Logical concept |
| G-06 | Delegation Authority Manager | 1 Execution | Delegation chains, revocation, audit trail | Logical concept |
| G-07 | Risk Manager | 1 Execution | Risk life cycle, tolerance, treatment | Logical concept |
| G-08 | Compliance Manager | 1 Execution | Obligation registration, baseline, reporting | Logical concept |
| G-09 | Audit Manager | 1 Execution | Audit records, evidence, findings | Logical concept |
| G-10 | Accountability Manager | 1 Execution | Principal, actor, subject, log linking | Logical concept |
| G-11 | Exception Manager | 1 Execution | Exception cases, expiry, escalation | Logical concept |
| G-12 | Approval Manager | 1 Execution | Request, review, decision, routing | Logical concept |
| G-13 | Control Manager | 2 Oversight | Control design, testing, effectiveness | Logical concept |
| G-14 | Governance Event Manager | 1 Execution | Event schema, ingestion, classification | Logical concept |
| G-15 | Conformance Manager | 2 Oversight | Snapshot evaluation, pass/fail, continuous conformance | Logical concept |

### 5.2 Per-component fields (condensed; canonical source = Part 13 components.md)

**Common governance fields** (apply to all G-00..G-15):

| Field | Value |
|-------|-------|
| **Category** | Logical architecture concept (governance) |
| **Layer** | Governance |
| **Purpose** | Each as named above (G-xx table). |
| **Responsibility** | Per Part 13 `components.md` (Purpose/Responsibilities sections per component). |
| **Inputs** | Governance event subscriptions (`INT-GOV-EVENT-001`). |
| **Outputs** | Governance events; internal manager-to-manager calls documented in Part 13 `components.md` (e.g., `requestEvaluation → G-02`). |
| **Exposed interfaces** | None to external callers — interaction is via `INT-GOV-EVENT-001` (event taxonomy) and internal manager calls (Part 13 `components.md`). |
| **Consumed interfaces** | `INT-GOV-EVENT-001` (emit/subscribe); `INT-EVT-BUS-001` (transport, P13-ADR-005); `INT-SEC-AUTH-001` (authority assertions, P13-ADR-003). |
| **Published events** | `governance.*` taxonomy (interfaces.md §2.11; Part 13 `governance-events.md`). |
| **Consumed events** | `governance.*` taxonomy (same). |
| **Dependencies** | Per Part 13 `components.md` (logical dependency graph; Tier 0/1 writers depend on G-03 Registry; all bind via G-10 Accountability; all record via G-09 Audit). |
| **Dependents** | Per Part 13 `components.md`. |
| **Integration boundary** | Logical/governance-layer; NOT a deployment boundary (Part 13 `components.md` §7.2). |
| **Ownership** | `[EXISTING]` Logical ownership asserted by Part 13 `components.md` (G-00..G-15); these are **logical architecture concepts**, not deployment units and not kernel-owned. Part 14 asserts no ownership and does not promote them to components. |
| **Status** | `[EXISTING]` as logical concepts (Part 13 `components.md`). Naming CONFLICT-05 vs Part 13 README (§11.5) — surfaced, not resolved. |
| **Security/trust** | `[EXISTING]` Governance events are **signed, minimum classification `confidential`, ACL-gated subscription** (`INT-GOV-EVENT-001`). `AuditManager` (G-09) is most sensitive — role-gated, no public access. `AccountabilityManager` (G-10) records treated as PII. Default-deny on evaluation failure (G-02). P13-ADR-002 enforces separation of policy and enforcement. |
| **ADRs** | `[EXISTING]` P13-ADR-001..P13-ADR-010; core ADR-001, ADR-003, ADR-006, ADR-008, ADR-009, ADR-010, ADR-013, ADR-014 (per Part 13 `adrs.md` cross-references). |
| **Source documents** | Part 13 `components.md`, `governance-events.md`, `adrs.md`; Roadmap §4 (Policy Engine, Audit Service referenced as shared components). |
| **Authority & traceability** | **Authoritative source:** Part 13 `components.md` (G-00..G-15). **Status:** EXISTING (as logical concepts). **Part 14 created?** No. **Classification:** These are **logical architecture concepts**, NOT deployment units and NOT Core Components/Managers — they must not be promoted to components (§1.1 rule). Roadmap §4 "Policy Engine / Audit Service" are summary labels for G-01/G-09. |

> **Naming contradiction (§11.5):** Part 13 `README.md` describes conformance components as *"Policy Manager, Authority Delegator, Audit Logger, Compliance Monitor"*, while `Part 13/components.md` uses *"Policy Manager, Decision Authority Manager, Audit Manager, Compliance Manager"*. Both are Part 13; the `components.md` G-xx table is the detailed canonical list used here.

---

## 6. Services (10, per Part 5) and Facade Services (4, per Part 6)

> **[EXISTING]** Part 5 §5.2 defines **10 Engineering Services** (ES-01..ES-12, numbered with two facade services at the end) and Part 6 defines **4 Capability Facade Services**. Classification contradiction noted in §11.6: Part 5 lists CouncilService (ES-11) and HumanInteractionService (ES-12) as Engineering Services, while Part 6 classifies them (and the 4 facades) as Capability Facade Services.

### 6.1 Engineering Services (SDLC + Knowledge)

| ES | Name | Type | Primary Responsibility | Trigger → Completion event |
|----|------|------|------------------------|----------------------------|
| ES-01 | PlanningService | SDLC Phase | Transform requirements into plan artifacts | `PLANNING_REQUESTED` → `PLANNING_COMPLETED`/`PLANNING_FAILED` |
| ES-02 | CodingService | SDLC Phase | Generate code from plan specs | `CODING_REQUESTED` → `CODING_COMPLETED`/`CODING_FAILED` |
| ES-03 | ReviewService | SDLC Phase | Static/architecture/security review with gates | `REVIEW_REQUESTED` → `REVIEW_APPROVED`… |
| ES-04 | TestingService | SDLC Phase | Orchestrate test suites | `TESTING_REQUESTED` → `TESTING_COMPLETED`/`TESTING_FAILED` |
| ES-05 | DeploymentService | SDLC Phase | Deployment lifecycle, rollback, release governance | `DEPLOYMENT_REQUESTED` → `DEPLOYMENT_COMPLETED`/`DEPLOYMENT_FAILED`/`DEPLOYMENT_ROLLED_BACK` |
| ES-06 | OperationsService | SDLC Phase | Runtime ops: monitoring, incident, scaling | `OPERATIONS_REQUESTED` → `OPERATIONS_COMPLETED`/`OPERATIONS_FAILED` |
| ES-07 | LearningService | Knowledge | Extract patterns; refine knowledge base | `LEARNING_REQUESTED` → `LEARNING_COMPLETED`/`LEARNING_FAILED` |
| ES-08 | MemoryService | Knowledge | Synchronize working/episodic/semantic memory across backends | `MEMORY_SYNC_REQUESTED` → `MEMORY_SYNC_COMPLETED`/`MEMORY_SYNC_FAILED` |
| ES-09 | ResearchService | Knowledge | Research workflows; evidence collection | `RESEARCH_REQUESTED` → `RESEARCH_COMPLETED`/`RESEARCH_FAILED` |
| ES-10 | DocumentationService | Knowledge | Generate/version/sync documentation | `DOCUMENTATION_REQUESTED` → `DOCUMENTATION_COMPLETED`/`DOCUMENTATION_FAILED` |

### 6.2 Facade / Governance Services

| ES | Name | Part 5 type | Part 6 type | Purpose |
|----|------|-------------|-------------|---------|
| ES-11 | CouncilService | Engineering (Governance) | Capability Facade | Convene LLM Council; voting, consensus, dissent, escalation (`COUNCIL_CONVENED` → `COUNCIL_CONSENSUS_REACHED`/`COUNCIL_DISSENT_REGISTERED`) |
| ES-12 | HumanInteractionService | Engineering (Governance) | (Human interface) | Human approvals, questions, overrides, feedback, escalations (`HUMAN_ESCALATION_REQUIRED` → `HUMAN_RESPONSE_RECEIVED`/`HUMAN_TIMEOUT`) |

### 6.3 Capability Facade Services (Part 6 — 4)

| Facade | Wraps (Definition Plane) | Execution monopoly | Purpose |
|--------|--------------------------|-------------------|---------|
| SkillService | SkillManager (Roadmap) / ToolManager capability domain (Part 1) | `[EXISTING]` INV-6.3.2: all capability invocations from Engineering Services transit SkillService | Execution facade for skill/tool invocation (Part 6 STEP3) |
| CouncilService | CouncilManager | `[DERIVED]` same facade pattern | Multi-agent deliberation bridge |
| MCPService | MCPManager (Roadmap) / ToolManager MCP domain (Part 1) | `[DERIVED]` same facade pattern | MCP server connection & tool orchestration bridge |
| MemoryService | MemoryManager | `[DERIVED]` same facade pattern | Memory operation bridge (also ES-08 Engineering Service) |

### 6.4 Common Service/Facade fields

| Field | Value |
|-------|-------|
| **Category** | Service (§6.1–6.2) / Facade Service (§6.3) |
| **Layer** | Agent / Operations / Learning / Governance (per service) |
| **Purpose** | Per §6.1–6.3 tables. |
| **Responsibility** | `[EXISTING]` Execute one SDLC/knowledge/governance function; translate inbound request events to outbound result events; never invoke peer services directly (EventBus-only) (Part 5 §5.1; Part 4 EventBus exclusivity). Facades additionally enforce **execution monopoly** (INV-6.3.2). |
| **Inputs** | `[EXISTING]` Phase request events (§6.1); facade invocation events (§6.3). |
| **Outputs** | `[EXISTING]` Result/failure events; follow-up `TaskCreated` where applicable. |
| **Exposed interfaces** | `[EXISTING]` `INT-SVC-BASE-001`; phase event contracts `INT-ENG-EVENT-001` (Part 5 §5.3–5.13); facades `INT-CFS-BRIDGE-001` (Part 6 §6.1.5, §6.2.2). |
| **Consumed interfaces** | `[EXISTING]` `INT-EVT-BUS-001`, `INT-SVC-REG-001`, `INT-CONFIG-READ-001`, `INT-SEC-AUTH-001` (where protected), `INT-CFS-BRIDGE-001` (facades), `HumanInteractionService` (`INT-HUMAN-001`). |
| **Published events** | `[EXISTING]` Per §6.1 trigger/completion columns; facades emit `SKILL_EXECUTED`/`SKILL_FAILED`, `COUNCIL_*`, `MCP_TOOL_*`, `MEMORY_*` (interfaces.md §2.8, §2.14). |
| **Consumed events** | `[EXISTING]` Phase request events + upstream completions; facades consume capability request events. |
| **Dependencies** | `[DERIVED]` Upstream services in SDLC chain + `MemoryManager` (via facade) + `EventBus` + `SecurityManager`. |
| **Dependents** | `[DERIVED]` Downstream services in SDLC chain; orchestration layers. |
| **Integration boundary** | In-process service; communicates only via EventBus (ADR-001). Facades bridge to external MCP/human. |
| **Ownership** | `[EXISTING]` Engineering Services owned/registered by `ServiceRegistry` (Part 5 §5.2); Facade Services own the Execution Plane per Part 6 (SkillService↔SkillManager, etc.), bridging Definition→Execution (INV-6.3.1/6.3.2). Ownership asserted by Part 5/6; Part 14 asserts none and assigns no new responsibility (§11.9). |
| **Status** | `[EXISTING]` (Part 5 §5.2 for 10 Engineering Services; Part 6 for 4 Facade Services). Classification CONFLICT-06 for CouncilService/HumanInteractionService/MemoryService (Part 5 vs Part 6, §11.6) — surfaced, not resolved. |
| **Security/trust** | `[DERIVED]` Protected ops require `SecurityManager` authorization (`INT-SEC-AUTH-001`); human escalation crosses human-oversight boundary via `HumanInteractionService` (`INT-HUMAN-001`, requires `kernel.admin`). Per-service authz policy `[UNSPECIFIED]`. Facades enforce policy at the execution choke point (INV-6.3.4). |
| **ADRs** | `[EXISTING]` ADR-001 (Event-First), ADR-003 (Capability Manager Ownership), ADR-006 (Human Oversight), ADR-009 (Explicit Failure Handling); Part 6 ADR-6.8.4/6.8.5 (facade/skill trust). |
| **Source documents** | Part 4 §4.2 (Service Framework); Part 5 §5.2–5.13; Part 6 STEP1/STEP2/STEP3/STEP3_MCP; Part 14 interfaces.md §2.4, §2.8, §2.14, §2.15. |
| **Authority & traceability** | **Authoritative source:** Part 5 §5.2 (10 Engineering Services) + Part 6 (4 Facade Services). **Status:** EXISTING. **Part 14 created?** No. **Responsibility audit (directive #8):** Engineering Services keep their source-defined phase roles; Facade Services stay thin execution bridges (INV-6.3.1/6.3.2/6.3.4); Part 14 assigns NO new responsibility to any Service/Facade. |
| **Schemas** | `[GAP]` Per-service payload schemas (`PlanArtifact`, `FailureContext`, `FindingPayload`, `LearningPayload`, `ArtifactPayload`, `RiskRegisterSchema`, `EstimationSchema`) are *referenced* in `INT-ENG-EVENT-001` but **not defined as standalone named schemas** in Parts 1–13 → UNKNOWN / NOT YET DEFINED at field level. |

> **Service/Facade responsibility check (§10.3):** Engineering Services MUST NOT call Core Managers directly for capabilities — they go through Facade Services (Part 5 ENG-DG-005; INV-6.3.1). Facades are the sole execution path (INV-6.3.2). Misclassification risk: MemoryService appears as BOTH ES-08 (Engineering/Knowledge) and a Capability Facade (Part 6) — reconciled as dual-role (see §11.6).

---

## 7. External Systems

| External System | Bridges via (internal) | Transport / Trust | Defined in |
|-----------------|------------------------|-------------------|-------------|
| **MCP Servers** | `ToolManager` (M3) / MCPService facade | `[EXISTING]` STDIO/HTTP/SSE/WEBSOCKET; trust via connection verification + tool allow-lists (Part 6 ADR-6.8.4) | Part 6 STEP3_MCP; Part 8; Roadmap §4 |
| **LLM / Model Providers** | `LLMManager` (M2) | `[EXISTING]` Network API; credentialed via `SecretManager`; provider trust (Part 10 ADR-005) | Roadmap §4; Part 7 |
| **Identity Providers** | `SecurityManager` / Identity Service (Part 4) | `[UNSPECIFIED]` Integration contract not defined in Parts 1–13 | Roadmap §4 (Part 4) |
| **Obsidian Vault** | `MemoryManager` (M1, OBSIDIAN memory type) | `[DERIVED]` Local/network filesystem; credentialed via `SecretManager` | Roadmap §4 (Part 9); `[Implementation]` |
| **Graphify Graph Store** | `MemoryManager` (M1, GRAPHIFY memory type) | `[DERIVED]` Network; credentialed via `SecretManager` | Roadmap §4 (Part 9); `[Implementation]` |
| **Web Search** | `ToolManager` (built-in `web_search` skill) | `[EXISTING]` Network; sandboxed (Part 6 §12.1) | `[Implementation]` |
| **External Compliance / Regulatory Frameworks** | Part 13 Compliance Manager (G-08) boundary | `[UNRESOLVED]` No contract in Parts 1–13 (`PRO-GOV-ADAPTER-001`, `PRO-GOV-REPORT-001`, `UNRES-EXT-AUDIT-001`) | Part 13 README boundary descriptions |

> External systems do not "own" AI-OS schemas and do not consume AI-OS interfaces in the in-process sense; they are reached across a network/process boundary by the bridging component. Their internal contracts are out of AI-OS scope.

---

## 8. Infrastructure Dependencies

| Dependency | Provides | Consumed by | Boundary / Notes |
|------------|----------|-------------|------------------|
| **In-memory EventBus (single process)** | Event transport within one process | All components/services | `[EXISTING]` v1.0 single-process only; distributed bus is `UNRES-EVT-DIST-001` (out of scope) (interfaces.md §4.3). |
| **Filesystem / Disk** | Persistence for checkpoints, state, config, audit logs, memory backends | CheckpointManager, StateManager, ConfigurationManager, AuditManager (G-09), MemoryManager | `[DERIVED]` Local disk; audit retention/tiering (P13-ADR-006). |
| **Python 3.12+ runtime** | Execution environment | Entire system | `[Implementation]` ARCHITECTURAL_INVENTORY.md §14. |
| **pydantic (>=2.0), pyyaml, typer, rich** | Config/models/CLI | ConfigurationManager, CLI, components | `[Implementation]` §14. |
| **structlog** (planned) | Structured logging backend | StructuredLogger / ObservabilityManager | `[GAP]` **Planned / NOT YET IMPLEMENTED** (Part 10 ADR-010); currently stdlib `logging` `[Implementation]`. |
| **Network transport** | Reach MCP servers, model providers, Obsidian/Graphify | MCPManager/ToolManager, LLMManager, MemoryManager | `[DERIVED]` Crosses trust boundaries (§7). |
| **Repository Ecosystem / config store** | Policy-as-code storage | Policy Manager (G-01), ConfigurationManager | `[UNKNOWN / NOT YET DEFINED]` concrete store (referenced in P13 ADRs). |

---

## 9. Module Category — Not a First-Class Integration Primitive

**[GAP] — Parts 1–13 do not define "Module" as a distinct integration category.** Per the nine-category taxonomy (§1.1), **Module is explicitly NOT a component class** — it is listed only to prevent misclassification. The specification uses "module" only informally (Python source packages, observability enrichment plugins).

The de-facto modular extension units plug in via existing component categories:
- **Skills** (built-in: shell, file_operations, web_search, code_analysis) → `ToolManager` (M3) capability domain + `SkillService` facade (§4.3, §6.3).
- **MCP server connections** → External System (§7) bridged by `ToolManager`/`MCPService`.
- **AI Agency agents** (9 autonomous review agents + FinalJudge) → `AgentManager` (M6) domain; `ai_agency.py` `[Implementation]`; escalation via CouncilService/HumanInteractionService.
- **Custom memory backends** → extension of `MemoryManager` (M1).
- **Plugin/tool extension interfaces** → `UNRES-PLUGIN-001` (unresolved; Part 11 references only, no contract), §4.

No entry is invented as a "Module". Any "module" referenced in source text is mapped to its real component category (Core Manager / Service / External system / Interface), never left as a floating component.

---

## 10. Ownership Checks (explicit per user requirements 9–11)

### 10.1 Kernel Ownership Check

- **[EXISTING]** HermesKernel owns **exactly 4 Core Components** (EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager) and **exactly 9 Core Managers** (M1–M9) (Part 1 §1.8.1). Counts are FIXED (ARB approval required to change).
- HermesKernel exposes these 13 entities via singleton accessors; accessors throw `KernelNotReadyError` before RUNNING state (`INT-KERNEL-ACC-001`).
- **Part 14 does not own, create, or renumber any component.** It only references the Kernel's owned set. Any component not in the Part 1 set (e.g., StateManager, ResourceManager, HealthManager, CapabilityManager) is **not** a Kernel-owned Core Component/Manager per the authoritative Kernel model (see §11.1).

### 10.2 Capability Manager Ownership Check

- **[EXISTING]** ADR-003 "Capability Manager Ownership" (Part 12 cross-ref ADR table; Part 4 CC-S-001 single-ownership). Each kernel concern SHALL have exactly one owning manager; shared ownership is FORBIDDEN (Part 4 §4.x Single Ownership).
- **Capability Facade pattern (Part 6):** SkillManager owns the *Definition Plane* (registration); SkillService owns the *Execution Plane* (invocation). They MUST NOT couple directly (INV-6.3.1). This is the canonical execution facade; Engineering Services SHALL NOT reference the manager directly (REQ-6.3.1, INV-6.3.2).
- **Ownership reconciliation (alias):** Roadmap §4 splits the tool/skill/MCP domain into `SkillManager` + `MCPManager`; Part 1 kernel model consolidates it as `ToolManager` (M3). For integration inventory, `ToolManager` is the Part 1 canonical owner; `SkillManager`/`MCPManager` are Roadmap-level aliases of its subdomains. The facade `SkillService`/`MCPService` bridge to it. (See §13.)

### 10.3 Service / Facade Responsibility Check

- **[EXISTING]** Engineering Services are `BaseService` derivatives; EventBus-only communication (ADR-001, Part 4 EventBus exclusivity).
- **[EXISTING]** Facade Services enforce **execution monopoly** — all capability invocations transit the facade (INV-6.3.2); policy is enforced at the single choke point (INV-6.3.4).
- **Misclassification guard:** MemoryService is dual-role (ES-08 Engineering/Knowledge AND a Part 6 Capability Facade). HumanInteractionService and CouncilService are classified as Engineering Services in Part 5 but as Facade/Governance in Part 6 — recorded as a contradiction (§11.6), not resolved.

---

## 11. Contradictions Between Parts 0–13 and Part 14 (NOT silently resolved)

This section records every inconsistency found during verification. Part 14 does not resolve them; it surfaces them for the ARB / Part authors.

### 11.1 Core Component set: cross-Part conflict (NOT silently resolved — directive #3)

**Finding:** Five sources disagree on the 4 Core Components. Part 1 is authoritative for Kernel composition; the others are recorded as **CONFLICT** and NOT merged into a single set.

| # | Source | States the 4 Core Components are | Conflict vs Part 1 |
|---|--------|----------------------------------|--------------------|
| 1 | **Part 1 §1.8.1** (authoritative Kernel model) | EventBus, ServiceRegistry, ConfigurationManager, **LifecycleManager** | — (reference set) |
| 2 | **Part 0 §3.2 / §0.3.2** (FROZEN, "supreme") | EventBus, **StateManager, WorkflowManager, ResourceManager** | Disjoint from Part 1 except EventBus. Part 0 is FROZEN yet contradicts Part 1 here → **CONFLICT-01**. |
| 3 | **Part 3 §3.6 (C4 StructuredLogger)** | Names `StructuredLogger` *"the last Core Component"* (C4) | Part 3 itself also depends on `LifecycleManager` as the Phase-3 core initializer → **internal Part 3 inconsistency** and conflict vs Part 1 → **CONFLICT-02**. |
| 4 | **Part 4 §4A/§4B** | Lists `ConfigurationAuthority`, `IdentityProvider` among *"Core Components"* (Phase-1 foundation) | Part 4 introduces two entities not in Part 1's fixed 4 → **CONFLICT-03**; see §11.8 for the roles they actually are. |
| 5 | `Part14/interfaces.md` §2.1 | EventBus, ServiceRegistry, ConfigurationManager, **StructuredLogger** | Substitutes `StructuredLogger` for `LifecycleManager` → **CONFLICT-04** (derivative of CONFLICT-02). |
| 6 | `Common/MASTER_ARCHITECTURE_ROADMAP.md` §4 | "EventBus", "Configuration Service", "State Manager", "Checkpoint Manager", "Retry Manager" | Older naming; no ServiceRegistry/ConfigurationManager/LifecycleManager → NAME DIVERGENCE (aliases, §13), not an authoritative set. |
| 7 | `ARCHITECTURAL_INVENTORY.md` (implementation, dated 2026-07-28) | "EventBus, StateManager, WorkflowManager, ResourceManager" | Implementation snapshot; tagged `[Implementation]`; never overrides the spec. |

**Part 14 position (directive #1 + #3):** Follows **Part 1** for the kernel set: `EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager`. Every other claim is surfaced as a CONFLICT and **not merged**:
- `StructuredLogger` is recorded as a **rival claim** (Part 3 §3.6 + interfaces.md §2.1), NOT as a synonym for `LifecycleManager` and NOT as a Core Component (Part 0 Principle 12 names it the logging *abstraction*, not a component). → CONFLICT-02/04.
- `StateManager`, `WorkflowManager`, `ResourceManager` (Part 0 / Roadmap / inventory): `WorkflowManager` is a **Core Manager (M7)** per Part 1; `StateManager`/`ResourceManager` are **not** in Part 1's fixed 9 Managers either → recorded as CONFLICT/divergence (§11.2 CONFLICT-07), never as Core Components.
- `ConfigurationAuthority` / `IdentityProvider` (Part 4): see §11.8 — neither is a Core Component; one is a *role*, one is *external*.

**ARB action required:** Resolve CONFLICT-01 (Part 0 FROZEN vs Part 1), CONFLICT-02/04 (StructuredLogger vs LifecycleManager), CONFLICT-03 (Part 4's extra "Core Components"). Until resolved, Part 14 uses the Part 1 set and labels the rest CONFLICT.

### 11.2 Core Manager set: Part 1 §1.8.1 vs Part 4 §4.2.1 (requirement #5 — preserved conflict, not merged)

**Finding:** The two authoritative kernel specs enumerate **different sets of "Nine Core Managers."** They overlap on only four names (StorageManager, WorkflowManager, SecurityManager, ObservabilityManager). Part 4 even reclassifies `LifecycleManager` — which Part 1 defines as a **Core Component** — as a *Core Manager*.

| Slot | Part 1 §1.8.1 (M1–M9) | Part 4 §4.2.1 ("The Nine Core Managers") | Verdict |
|------|------------------------|---------------------------------------------|---------|
| 1 | `MemoryManager` (M1) | `LifecycleManager` *(a Part 1 **Core Component**, not a Manager)* | **DISJOINT** |
| 2 | `LLMManager` (M2) | `StateManager` | **DISJOINT** |
| 3 | `ToolManager` (M3) | `StorageManager` | Part 4 keeps StorageManager; Part 1's M4 is also StorageManager → **overlap** |
| 4 | `StorageManager` (M4) | `WorkflowManager` | Part 4 keeps WorkflowManager; Part 1's M7 is also WorkflowManager → **overlap** |
| 5 | `ContextManager` (M5) | `SecurityManager` | Part 4 keeps SecurityManager (Part 1 M8) → **overlap**; Part 1's M5 ContextManager absent from Part 4 |
| 6 | `AgentManager` (M6) | `CapabilityManager` | **DISJOINT** |
| 7 | `WorkflowManager` (M7) | `ResourceManager` | **DISJOINT** |
| 8 | `SecurityManager` (M8) | `HealthManager` | **DISJOINT** |
| 9 | `ObservabilityManager` (M9) | `ObservabilityManager` | **overlap** |

**Exclusive to Part 1 (absent from Part 4's set):** `MemoryManager`, `LLMManager`, `ToolManager`, `ContextManager`, `AgentManager`.
**Exclusive to Part 4 (absent from Part 1's set):** `StateManager`, `CapabilityManager`, `ResourceManager`, `HealthManager` (and `LifecycleManager` used as a Manager, which Part 1 reserves as a Core Component).

**Source of each definition (both cited, neither adopted as canonical here):**
- Part 1 §1.8.1 — *"This number is FIXED and MUST NOT change without ARB approval."* Counts: exactly 4 Core Components + exactly 9 Core Managers, named M1–M9 above.
- Part 4 §4.2.1 — *"The Nine Core Managers"* table (Lifecycle/State/Storage/Workflow/Security/Capability/Resource/Health/Observability), with §4.2.3 init phases and §4.2.6 ownership boundaries.

**Part 14 position (directive #3 / requirement #5):** This is a **genuine, unresolved conflict** — recorded as **CONFLICT-07**. Part 14 does **not** silently merge the two sets and does **not** rename `LifecycleManager` into a Manager. For the working inventory, Part 14 follows **Part 1 §1.8.1** as the authoritative Kernel Manager model (M1–M9) because Part 1 is the authoritative source for Kernel composition (§1.3). The Part 4-exclusive managers (`StateManager`, `CapabilityManager`, `ResourceManager`, `HealthManager`) are recorded as **Part 4-local manager definitions** that are **not** in Part 1's fixed 9; they are surfaced as a conflict, not promoted to canonical Core Managers and not merged into M1–M9.

**ARB action required:** Reconcile whether (a) Part 4's set supersedes Part 1's (requires ARB, since Part 1 states the count is FIXED), or (b) Part 4's extra managers are sub-concerns folded into the Part 1 nine (e.g., `StateManager`→StorageManager/M-state, `CapabilityManager`→ToolManager domain, `ResourceManager`/`HealthManager`→cross-cutting), or (c) both sets coexist as different abstraction levels. Until resolved, Part 14 uses the Part 1 set and labels Part 4's divergent managers CONFLICT-07.

### 11.3 Manager naming divergence: Part 1 vs Roadmap

- Part 1 kernel managers: **LLMManager** (not "Model Router"), **ToolManager** (not "Skill Manager"+"MCP Manager"), **AgentManager** (not "AI Agency").
- Roadmap §4 uses the alternative labels (`Model Router`, `Skill Manager`, `MCP Manager`, `AI Agency`, `Observability`→"Root Cause Analyzer" subset).
- **Part 14 position:** Uses Part 1 canonical names; records Roadmap labels as **aliases** (§13). Both denote the same domains; this is a naming inconsistency, not a component-count change.

### 11.4 Part 12 component abstractions vs Part 1 Kernel model

- Part 12 `components.md` lists Workflow Manager dependencies on **Communication Bus, Capability Registry, Agent Directory, Shared Context Manager, Scheduler** — abstractions not present in the Part 1 Core Manager set.
- These are Part 12's *internal* vocabulary. Part 14 does **not** promote them to Core Components; they are recorded as Part 12-local abstractions (logical, not Kernel-owned). Potential reconciliation needed: are these distinct components or aliases of EventBus/CapabilityManager/AgentManager/ContextManager/ResourceManager? **UNKNOWN / NOT YET DEFINED** — flagged, not resolved.

### 11.5 Part 13 governance component naming

- Part 13 `README.md` conformance list: *"Policy Manager, Authority Delegator, Audit Logger, Compliance Monitor"*.
- Part 13 `components.md`: *G-00..G-15* with names like *Decision Authority Manager, Audit Manager, Compliance Manager*.
- **Part 14 position:** Uses the G-xx `components.md` table as canonical (it is the detailed spec). The README names are treated as a stale/summary variant. Flagged for Part 13 reconciliation.

### 11.6 Service vs Facade classification

- Part 5 §5.2 numbers 10 Engineering Services and lists **CouncilService (ES-11)** and **HumanInteractionService (ES-12)** as Engineering Services.
- Part 6 classifies CouncilService and the 4 facades as **Capability Facade Services**.
- **Part 14 position:** Records both; does not force a single classification. CouncilService/HumanInteractionService are tagged as "Engineering (Governance)" per Part 5 and noted as facade/bridge per Part 6. MemoryService is dual-role (ES-08 + facade). Flagged, not resolved.

### 11.7 Roadmap Part 13 title vs actual Part 13

- Roadmap §2 titles Part 13 as **"Deployment & Platform Operations"** (layer: Operations).
- Actual Part 13 is **"Governance Architecture"** (layer: Governance).
- **Part 14 position:** Follows the actual Part 13 content (Governance). The Roadmap title is stale. Flagged.

### 11.8 Implementation inventory vs specification

- `ARCHITECTURAL_INVENTORY.md` reflects an implementation that predates/diverges from the spec (different 4-core set, different manager names, 12/21 tests passing, critical bugs). It is tagged `[Implementation]` throughout and used only for event-name/implementation detail, never to override the specification.

### 11.9 Naming integrity — `ConfigurationAuthority` vs `IdentityProvider` (directive #4)

These two names appear in Part 4 as if they were internal kernel entities (even "Core Components", see §11.1 #4). They represent **different concepts** and are **not** silently renamed or merged:

| Name | How Part 4 uses it | Actual classification | Part 14 treatment |
|------|--------------------|-----------------------|-------------------|
| **`ConfigurationAuthority`** | Part 4 §4A/§4B/§4C: "ConfigurationAuthority (Part 3)" — single writer of config; inbound dependency of managers. | A **ROLE / PERMISSION** owned by `ConfigurationManager`. Part 1 §93: *"Configuration Authority — Owns the immutable configuration contract via ConfigurationManager."* | **Not a separate component.** It is the configuration-ownership role of the `ConfigurationManager` Core Component. Part 14 does **not** rename `ConfigurationManager` → `ConfigurationAuthority`, and does **not** promote the role to a component. Labeled DERIVED-role, not EXISTING-component. |
| **`IdentityProvider`** | Part 4 §4B: outbound `identity.validate(credentials)`, `identity.getPrincipal(id)`; "IdentityProvider (Core Component, Part 3)". | An **External system** (identity/authn source) reached across a boundary; Part 4 §4B marks it *Outbound*. | **Not an internal Core Component.** Classified as **External system** (§7: "Identity Providers"). Part 14 does **not** list it among the 4 Core Components and does **not** merge it with `SecurityManager` (which performs *authorization*; the IdentityProvider performs *authentication* — distinct concerns). |

**CONFLICT:** Part 4 §4A/§4B calls both `ConfigurationAuthority` and `IdentityProvider` "Core Components," contradicting Part 1's fixed 4-set (and contradicting Part 4's own outbound/external framing of `IdentityProvider`). Recorded as CONFLICT-03 (§11.1). Part 14 preserves the distinction between the two names and does not silently collapse either into `ConfigurationManager` or `SecurityManager`.

### 11.10 Responsibility audit — Kernel owns orchestration; managers/services/facades keep source roles (directive #8)

- **Kernel / HermesKernel = orchestrator only.** It owns exactly the 4 Core Components + 9 Core Managers and the lifecycle state machine. It contains **no domain logic** (Part 0 §0.4 Principle 3; Part 1). Part 14 assigns the Kernel no new responsibility.
- **Core Managers retain source-defined ownership.** Each of M1–M9 keeps the single-ownership domain assigned by Part 1/Part 4 (CC-S-001 single-ownership; ADR-003). No manager's responsibility is expanded or split by Part 14. Where Part 4 names extra managers (`StateManager`, `ResourceManager`, `HealthManager`, `CapabilityManager`), these are recorded as CONFLICT/divergence (§11.2 CONFLICT-07), **not** merged into the fixed 9.
- **Engineering Services retain source-defined roles.** The 10 services (Part 5 §5.2) keep their SDLC/knowledge phase responsibilities. Part 14 adds no responsibility to any service.
- **Facade Services remain thin bridges.** SkillService/CouncilService/MCPService/MemoryService translate Events → Manager calls and enforce the execution monopoly (INV-6.3.1/6.3.2/6.3.4). Part 14 does **not** add business logic or new routing to any facade.
- **Part 14 assigns zero new responsibilities.** All "Responsibility" fields are tagged `[EXISTING]` (source-stated) or `[DERIVED]` (inferred from source ownership). No field is invented by Part 14.

### 11.11 Interface vs component discipline (directive #2)

- **No `INT-*` interface is classified as a component.** `INT-EVT-BUS-001`, `INT-SEC-AUTH-001`, `INT-CFS-BRIDGE-001`, `INT-KERNEL-ACC-001`, `INT-GOV-EVENT-001`, `ICoreManager`, etc. are contracts *of* components (§1.1, category "Interface" = NOT a component). They appear in the "Exposed/Consumed interfaces" rows of component tables, never as standalone components.
- **No implementation detail is elevated to a component.** `structlog`, `pydantic`, `ai_agency.py`, `workflow.py`, `kernel.logger` are `[Implementation]`-tagged code artifacts, recorded only where a source Part or the inventory references them, and never promoted to architectural components.
- **"Module" is not a component class.** Modular extension units (skills, MCP servers, agents, memory backends, plugins) are inventoried under their real category (§9).

---

## 12. Cross-Cutting Dependency Notes (for dependency analysis)

1. **[EXISTING]** No direct service-to-service calls. All inter-service communication is via `INT-EVT-BUS-001` (ADR-001, Part 4 EventBus exclusivity). Dependency edges are *event* edges.
2. **[DERIVED]** Singleton accessor coupling (13 `get_xxx()` accessors) creates hidden coupling — known debt; DI migration is an open decision (TOC Part 16, Decision #1).
3. **[EXISTING]** `INT-SEC-AUTH-001` is a convergence point (every protected op depends on `SecurityManager`); `INT-GOV-EVENT-001` is a convergence point for all governance components.
4. **[EXISTING]** Part 13 governance components (G-00..G-15) are a logical overlay across all Parts; they depend on EventBus + SecurityManager but are not in the SDLC service chain (Part 13 `components.md` §2, §6).
5. **[EXISTING]** The three hard external trust boundaries: MCP servers, model providers, human operators (`HumanInteractionService`). Identity providers and compliance frameworks are referenced but **unresolved** (no contract in Parts 1–13).

---

## 13. Duplicate / Alias Component Names

| Canonical (Part 1 / authoritative) | Alias / alternate label (other Part) | Status |
|------------------------------------|----------------------------------------|--------|
| `LifecycleManager` (Core Component) | `StructuredLogger` (Part 3 §3.6 / interfaces.md §2.1) — **CONFLICT, not a true alias** (§11.1 CONFLICT-02/04) | DO NOT MERGE (directive #3) |
| `ConfigurationManager` (Core Component) | "Configuration Service" (Roadmap §4) | alias |
| `ConfigurationManager` (Core Component) | `ConfigurationAuthority` (Part 1 §93 role; Part 4 §4A/§4B) — **ROLE, not a separate component** (§11.8) | role, not alias; do not rename |
| `LLMManager` (M2) | "Model Router" (Roadmap §4; Part 5 §5.1.1 capability) | alias |
| `ToolManager` (M3) | "Skill Manager" + "MCP Manager" (Roadmap §4) | alias (subdomains) |
| `AgentManager` (M6) | "AI Agency" (Roadmap §4); `ai_agency.py` `[Implementation]` | alias |
| `ObservabilityManager` (M9) | "Observability" (Roadmap §4); "Root Cause Analyzer" `[Implementation]` (diagnostic subset) | alias |
| `WorkflowManager` (M7) | "Workflow Manager" (Roadmap §4, Part 12) | alias (Part 12 details semantics) |
| `MemoryManager` (M1) | "Memory Manager" (Roadmap §4) | alias |
| `SecurityManager` (M8) | "Authorization"/"Authentication"/"Policy Engine" (Roadmap §4 sub-capabilities) | sub-capability |
| `IdentityProvider` | **External system** (Part 4 §4B outbound) — NOT an internal component; NOT merged with `SecurityManager` (§11.8) | external, not alias |
| Part 1 M1–M9 (canonical) | Part 4 §4.2.1 managers `StateManager`, `CapabilityManager`, `ResourceManager`, `HealthManager` (and `LifecycleManager`-as-Manager) — **CONFLICT-07, not aliases** (§11.2) | DO NOT MERGE (directive #3 / req #5) |
| `MemoryService` | ES-08 (Engineering) AND Part 6 Capability Facade | dual-role (§11.6) |
| `CouncilService` / `HumanInteractionService` | ES-11/ES-12 (Engineering) AND Part 6 Facade/Governance | dual-role (§11.6) |

---

## 14. Open / UNKNOWN Summary (GAP register)

Fields explicitly left **UNKNOWN / NOT YET DEFINED** because Parts 1–13 do not establish them:

- Bus-level authentication/authorization on `INT-EVT-BUS-001` (interfaces.md "Unspecified").
- Per-service payload schema field definitions beyond names referenced in `INT-ENG-EVENT-001` (PlanArtifact, FailureContext, etc.) — **[GAP]**.
- Identity Provider integration contract (`IdentityProvider`, Part 4 §4B outbound, classified External §7); Compliance/Regulatory framework adapter contracts (unresolved interfaces §4).
- Plugin/Tool extension contract (`UNRES-PLUGIN-001`).
- Logger-level secret-redaction control; observability backend selection (Part 10 ADR-010 planned).
- Part 12 abstractions (Communication Bus, Capability Registry, Agent Directory, Shared Context Manager, Scheduler) — relationship to Kernel Core Managers **[UNKNOWN]**.
- Module as a first-class integration category — **[GAP]** (§9).
- Exact event lists for several Core Managers where the source only names the interface, not the events (marked `[UNSPECIFIED]` per field).
- **CONFLICT-01:** Part 0 §3.2 (4 Core Components = EventBus/StateManager/WorkflowManager/ResourceManager) vs Part 1 §1.8.1 (EventBus/ServiceRegistry/ConfigurationManager/LifecycleManager) — both FROZEN/authoritative, disjoint sets. **[CONFLICT]** unresolved.
- **CONFLICT-02/04:** `StructuredLogger` claimed as 4th Core Component (Part 3 §3.6 C4; interfaces.md §2.1) vs Part 1's `LifecycleManager`. **[CONFLICT]** unresolved; not merged.
- **CONFLICT-03:** Part 4 §4A/§4B lists `ConfigurationAuthority` + `IdentityProvider` as "Core Components" — contradicting Part 1's fixed 4 and Part 4's own external/outbound framing. **[CONFLICT]** unresolved (see §11.9).
- **CONFLICT-07:** Part 1 §1.8.1 "Nine Core Managers" (M1–M9) vs Part 4 §4.2.1 "The Nine Core Managers" (Lifecycle/State/Storage/Workflow/Security/Capability/Resource/Health/Observability) — nearly disjoint sets; Part 4 even reclassifies `LifecycleManager` (a Part 1 Core Component) as a Manager. **[CONFLICT]** unresolved (see §11.2). Part 14 follows Part 1; Part 4-exclusive managers surfaced, not merged.
- Naming preservation: `ConfigurationAuthority` is a *role* of `ConfigurationManager` (Part 1 §93); `IdentityProvider` is *external* — neither renamed nor merged (directive #4).

---

## 15. Final Component Integrity Statement (directive #10)

This document is an **inventory and derivation artifact**, not an architectural source. The following four points hold by construction and are the binding guarantees of this catalog.

### 15.1 Source authority — every component traces to a Part 1–13 definition

- No entry is authored by Part 14. Every component, service, facade, external system, infrastructure dependency, and governance concept is attributed to a specific Part + document + section (see §1.4 source-traceability table and the per-entry "Authority & traceability" rows in §3–§6).
- Where multiple Parts address the same subject, authority resolves per §1.3: **Part 1** for Kernel composition (the "exactly 4 / exactly 9" rule), the **per-Part spec** for its own domain, the **Roadmap** as a possibly-lagging index, and the **implementation inventory** only as `[Implementation]` detail that never overrides the spec.
- The authoritative Kernel set used throughout this document is **Part 1 §1.8.1**: `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager` (4 Core Components) + M1–M9 (9 Core Managers). This is followed even where Part 0, Part 3, Part 4, `interfaces.md`, the Roadmap, or the implementation inventory disagree (see §11.1).

### 15.2 Unresolved component conflicts — surfaced, never silently resolved

The following genuine conflicts are recorded with both source references and are **NOT** merged or paper-over-resolved (directive #3):

- **CONFLICT-01** — Part 0 §3.2/§0.3.2 (4 Core Components = `EventBus, StateManager, WorkflowManager, ResourceManager`) vs Part 1 §1.8.1 (4 = `EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager`). Disjoint except `EventBus`.
- **CONFLICT-02** — Part 3 §3.6 (C4 `StructuredLogger` = "last Core Component") vs Part 1 §1.8.1 (`LifecycleManager`). Part 3 is internally inconsistent (it also depends on `LifecycleManager`).
- **CONFLICT-03** — Part 4 §4A/§4B lists `ConfigurationAuthority` + `IdentityProvider` as "Core Components" vs Part 1's fixed 4; and `IdentityProvider` is framed outbound/external within Part 4 itself (see §11.8).
- **CONFLICT-04** — `interfaces.md` §2.1 substitutes `StructuredLogger` for `LifecycleManager` (derivative of CONFLICT-02).
- **CONFLICT-05** — Part 13 `README.md` governance names vs Part 13 `components.md` G-xx names (§11.5).
- **CONFLICT-06** — Service-vs-Facade classification of CouncilService/HumanInteractionService/MemoryService (Part 5 vs Part 6, §11.6).
- **CONFLICT-07** — Part 1 §1.8.1 "Nine Core Managers" (M1–M9) vs Part 4 §4.2.1 "The Nine Core Managers" (nearly disjoint set; Part 4 reclassifies `LifecycleManager` as a Manager). Surfaced, not merged (§11.2).

Each is escalated to the ARB; Part 14 adopts the authoritative source for its working set and flags the divergence. No conflict is hidden.

### 15.3 Component taxonomy rules — enforced throughout

The nine categories of §1.1 are enforced; the last two are explicitly **non-components**:

- **Components (real classes):** Core Component, Core Manager, Service, Facade Service, External system, Infrastructure dependency, Logical architecture concept.
- **NOT components (must not be misclassified):** **Module** — not a first-class integration primitive in Parts 1–13 (§9); modular units are inventoried under their true category. **Interface** — an `INT-*`/accessor/extension-point/schema contract is a *surface of* a component, never a component itself (§11.11). **Implementation detail** — code artifacts (`structlog`, `ai_agency.py`, `workflow.py`) stay `[Implementation]`-tagged and are never promoted to architectural components.
- **Naming integrity (directive #4):** `ConfigurationAuthority` is preserved as a *role* of `ConfigurationManager` (Part 1 §93), not renamed to a component; `IdentityProvider` is preserved as an *External system*, not merged into `SecurityManager`. Aliases are recorded in §13; genuine conflicts (§15.2) are never relabeled as aliases.

### 15.4 Part 14 non-invention rule — no new components, no new responsibilities

- **No component created by Part 14.** Zero new Core Components, Core Managers, Services, Facades, External Systems, or Infrastructure Dependencies are introduced. Where source names diverge, Part 14 records the divergence; it does not synthesize a new entity (§11, §13).
- **No responsibility assigned by Part 14.** The Kernel remains orchestrator-only (no domain logic); Core Managers keep source-defined single-ownership domains (CC-S-001 / ADR-003); Engineering Services keep source-defined phase roles; Facade Services stay thin execution bridges (INV-6.3.1/6.3.2/6.3.4). Every "Responsibility" field is `[EXISTING]` or `[DERIVED]`; none is invented (§11.9).
- **No architecture redesigned.** Naming, counts, interfaces, and responsibilities are reported as found. Recommendations (reconcile Roadmap §4 naming, resolve Part 12 abstractions, settle CONFLICT-01..06) are recorded as GAPs/contradictions for the ARB, not applied as changes.
- **Unknown data preserved as unknown.** Where Parts 1–13 do not establish a field, it is marked **UNKNOWN / NOT YET DEFINED** rather than filled by industry assumption (§14).

---

## 16. Relevant Architecture Documents (consolidated)

- **Cross-part:** `Common/MASTER_ARCHITECTURE_ROADMAP.md` (§2 layers, §4 shared components, §5 shared schemas, §6 ADR map, §8 invariants); `Common/ARCHITECTURAL_INVENTORY.md` (`[Implementation]` detail); `Common/ARCHITECTURE_SPEC_TOC.md`.
- **Part 14 siblings:** `interfaces.md`, `adrs.md`, `schemas.md`, `events.md`, `dependency-map.md`.
- **Per-layer:** Part 1 (Kernel/Foundation), Part 2 (EventBus/Integration), Part 3 (Data/State/Registry), Part 4 (Security & managers/ownership), Part 5 (Engineering Services), Part 6 (Facades/MCP/trust), Part 7 (AI Core/model), Part 8 (Agent/Skill/MCP), Part 9 (Learning/memory), Part 11 (Cognitive/context), Part 12 (Workflow/Council/multi-agent events), Part 13 (Governance components & ADRs).

---

## 16. Component Integrity Summary (requirement #12 — concise)

This catalog is a **read-only inventory of Parts 0–13**. The guarantees below are confirmed by the sections cited.

| # | Integrity guarantee | Evidence |
|---|---------------------|----------|
| 1 | **No component invented by Part 14** | §3–§9 + §1.4 traceability; §15.4 non-invention rule. Working set = Part 1 §1.8.1 (4 Core Components + 9 Core Managers). |
| 2 | **Taxonomy is explicit and enforced** | §1.1 (9 categories; `module`/`interface` are NOT components), §1.5 field checklist, §11.11 interface-vs-component discipline. |
| 3 | **Source authority not overridden by Roadmap/Part 14 docs** | §1.3 hierarchy; §11.1 authority note; Part 1 followed even where Part 0/3/4/Roadmap/inventory disagree. |
| 4 | **Core Component identity conflicts recorded, not merged** | §11.1 (CONFLICT-01..04): Part 0 vs Part 1; Part 3 `StructuredLogger` C4 vs Part 1 `LifecycleManager`; Part 4 `ConfigurationAuthority`/`IdentityProvider`; interfaces.md. |
| 5 | **Core Manager set conflict preserved with both sources** | §11.2 (CONFLICT-07): Part 1 §1.8.1 M1–M9 vs Part 4 §4.2.1 set; each source cited; not merged. |
| 6 | **Divergent names preserved, not silently merged** | §11.9: `ConfigurationAuthority` = role of `ConfigurationManager`; `IdentityProvider` = external system; §13 alias table. |
| 7 | **Every major component carries the 12 required fields** | §1.5 checklist; per-entry rows in §3–§6 (responsibility, layer, inputs, outputs, interfaces, events, dependencies, dependents, boundaries, ownership, source, status). |
| 8 | **Silence marked UNKNOWN / NOT YET DEFINED** | §14 GAP register; every `[GAP]`/`[UNSPECIFIED]`/`[CONFLICT]` field uses the placeholder value; never guessed. |
| 9 | **Status vocabulary applied consistently** | §1.2: full 8-status model per `adrs.md` Rule 0.5 / `context.md` §0.1 — EXISTING / DERIVED / ASSUMPTION / UNSPECIFIED / GAP / PROPOSED / FUTURE / CONFLICT — with `UNKNOWN / NOT YET DEFINED` as the placeholder value for UNSPECIFIED/GAP/ASSUMPTION/CONFLICT. |
| 10 | **No new responsibilities assigned** | §11.10 responsibility audit: Kernel=orchestrator-only; Managers/Services/Facades keep source roles; Part 14 adds none. |
| 11 | **Duplicates/aliases identified, not resolved** | §13 alias/duplicate table (DO-NOT-MERGE flags on `LifecycleManager`/`StructuredLogger`, Part 4 managers). |
| 12 | **Conflicts escalated, not hidden** | §15.2 lists CONFLICT-01..07 with both sources; ARB action required on each. |

**Bottom line:** 4 Core Components + 9 Core Managers (per Part 1) + 10 Engineering Services + 4 Capability Facade Services + 16 Part 13 governance concepts + 6 external-system classes + 7 infrastructure dependencies are inventoried with full source traceability. Seven cross-part conflicts (CONFLICT-01..07) are surfaced with both references and deliberately left unresolved for the ARB. No architecture was redesigned and no component was created.

---

*End of Part 14 Component Inventory. This document inventories only concepts established in Parts 1–13, marks all unestablished fields UNKNOWN / NOT YET DEFINED, and surfaces (does not resolve) cross-part contradictions. No new components were created and no architecture was redesigned.*
