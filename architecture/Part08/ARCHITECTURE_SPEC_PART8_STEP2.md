# AI-OS Architecture Specification v1.0
## Part 8: Intelligent Agent & Execution Architecture
### Section 8.2: Capability Discovery & Planning Architecture (Part 1 of 2)

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-29  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  

---

### 8.2 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART8-SEC8.2 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Section 8.2 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (9–N) MUST conform to Section 8.2. Section 8.2 MUST NOT contradict Section 8.1 or Parts 0 through 7. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles, conformance), PART1 (Hermes Kernel), PART2 (Event System), PART3 (Core Managers), PART4 (Service Framework), PART5 (Engineering Services), PART6 (Capability Facade Services), PART7 (Workflow & Orchestration), PART8.1 (Intelligent Agent Architecture Overview), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis), MIGRATION_PLAN.md (phasing), ARCHITECTURE_ANALYSIS.md (architectural decisions) |

**Conformance Requirement:** Every subsequent Part (9–N) of this specification MUST explicitly reference Part 8 Section 8.2 sections for Capability Discovery & Planning terminology, interfaces, and conformance criteria. Any Part that contradicts Section 8.2 is non-conformant and MUST be revised.

**Scope:** This Section defines the authoritative architecture of the **Capability Discovery & Planning subsystem** — the deterministic reasoning layer that transforms raw intent into an executable, validated, governance-compliant Capability Plan through structured intent analysis, capability resolution, dependency resolution, and plan assembly. This subsystem operates purely in the planning phase; it produces plans but does not execute them. Execution is the responsibility of the Execution Engine specified in Section 8.3.

---

## 8.2.1 Purpose

### 8.2.1.1 Why Capability Discovery Exists

The AI-OS architecture separates **intent** (what the user wants) from **capability** (what the system can do) from **execution** (how it gets done). Capability Discovery exists to bridge the semantic gap between natural-language or structured intent and the concrete, versioned, governed capabilities registered in the Capability Registry (Part 6).

Without a dedicated discovery subsystem, the system would suffer from:
- **Tight coupling** between intent parsers and specific capability implementations
- **Inability to substitute** equivalent capabilities when preferred ones are unavailable
- **No systematic handling** of version conflicts, policy violations, or governance constraints
- **Non-deterministic planning** where the same intent produces different capability sets across invocations

### 8.2.1.2 Why Planning Is Separated from Execution

Planning and execution are fundamentally different concerns with different correctness criteria:

| Dimension | Planning (Discovery & Planning) | Execution (Section 8.3) |
|-----------|----------------------------------|-------------------------|
| **Determinism** | MUST be deterministic — same input → same plan | Inherently non-deterministic — external systems, timing, failures |
| **Time horizon** | Stateless, immediate | Long-running, stateful |
| **Rollback** | Trivial (discard plan) | Complex (compensating actions, saga orchestration) |
| **Governance** | Static validation (policy, cost, risk) | Dynamic enforcement (quotas, rate limits, audit) |
| **Optimization** | Graph-theoretic (dependency, parallelism, cost) | Runtime adaptive (retry, fallback, load shedding) |
| **Observability** | Plan artifacts, decision traces | Execution traces, metrics, logs |

Combining them conflates static analysis with dynamic control, making both harder to verify, test, and audit.

### 8.2.1.3 Deterministic Planning vs Non-Deterministic Execution

**Deterministic Planning (this Section):**
- Given identical Intent + Registry State + Policy State → identical Capability Plan
- No external I/O during planning (registry reads are snapshot-isolated)
- Pure function: `Plan = f(Intent, RegistrySnapshot, PolicySnapshot)`
- Enables: reproducibility, caching, offline validation, formal verification

**Non-Deterministic Execution (Section 8.3):**
- External service calls, network latency, partial failures
- Retry with exponential backoff, circuit breakers, fallback chains
- State mutation, side effects, compensation logic
- Enables: resilience, progress under failure, real-world operation

### 8.2.1.4 Planning Philosophy

The Capability Discovery & Planning subsystem operates on the following foundational principles:

| Principle | Statement | Architectural Implication |
|-----------|-----------|---------------------------|
| **Determinism First** | Identical inputs MUST produce identical plans — no exceptions | Pure-function pipeline, snapshot isolation, replay verification |
| **Explicit Over Implicit** | Every decision MUST be recorded with rationale — no silent defaults | Confidence scores, substitution records, policy decisions, governance evidence |
| **Fail Fast, Recover Gracefully** | Blocking failures halt immediately; transient failures retry with checkpoints | 12 failure classes with explicit recovery/fallback/escalation matrix |
| **Governance by Default** | Every capability is governed until proven otherwise | Policy evaluation at resolution, governance gates at planning, evidence at artifacts |
| **Observability by Construction** | Every stage emits correlation-linked events for full traceability | 6 event categories with causation chains, replay verification |
| **Human-in-the-Loop by Design** | Human judgment enters only at designated gates, never ad-hoc | 6 intervention points with audit trails, override scoping |
| **Composability over Monolith** | Capabilities compose via explicit contracts, not implicit coupling | DAG with 5 dependency types, explicit data contracts, explicit triggers |

**Architectural Consequence:** These principles mandate a pure-function planning pipeline with snapshot isolation at the boundary, deterministic tie-breaking everywhere, exhaustive event emission, and governance gates that cannot be bypassed. They are not advisory — they are enforced by the invariants in §8.2.11 and verified by conformance levels L1–L7 in §8.2.12.

### 8.2.1.5 Architectural Responsibilities

The Capability Discovery & Planning subsystem SHALL be responsible for:

| Responsibility | Description |
|----------------|-------------|
| **Intent Analysis** | Decompose, normalize, extract requirements/constraints/risks/governance from raw intent |
| **Capability Resolution** | Map intent requirements to registered capabilities via Project → Global → External Registry order |
| **Skill Discovery** | Discover and validate skill compositions for complex intent patterns |
| **Capability Ranking** | Score and rank candidate capabilities by relevance, cost, risk, policy compliance |
| **Dependency Resolution** | Build and validate the capability dependency graph (DAG) |
| **Version Compatibility** | Resolve version constraints across the capability graph |
| **Duplicate Detection** | Identify and deduplicate equivalent capabilities |
| **Confidence Scoring** | Assign confidence to each resolution decision |
| **Metadata Validation** | Validate capability manifests against schema and policy |
| **Policy Validation** | Enforce organizational, security, cost, and compliance policies |
| **Governance Detection** | Identify capabilities requiring governance review/approval |
| **Capability Classification** | Classify capabilities by type, criticality, data sensitivity, blast radius |
| **Cost Estimation** | Estimate compute, storage, network, API costs for the plan |
| **Risk Classification** | Classify plan risk level (LOW/MEDIUM/HIGH/CRITICAL) |
| **Resource Requirements** | Compute aggregate resource budgets (CPU, memory, GPU, quotas) |
| **Capability Recommendation** | Recommend alternative or complementary capabilities |
| **Capability Plan Assembly** | Produce the final executable Capability Plan with all bindings |
| **Planning Memory** | Track and reuse successful planning patterns, substitutions, and optimizations across planning flows |
| **Optimization Layer** | Apply cost/latency/risk optimization passes to assembled plans with feedback from execution outcomes |
| **AI Council Coordination** | Orchestrate multi-model deliberation for governance decisions and ambiguous resolutions |
| **Model Routing** | Route planning subtasks (classification, ranking, summarization) to appropriate models via Hermes Kernel |
| **Self-Healing Planning** | Automatically recover from transient planning failures via checkpoint recovery and adaptive retry |
| **Optimization Feedback** | Incorporate execution-phase metrics (actual cost, duration, failures) into future planning decisions |

---

## 8.2.2 Scope

### 8.2.2.1 In Scope

The following are **in scope** for Section 8.2:

- **Intent Analysis Pipeline**: Complete decomposition, normalization, extraction, and validation of intent
- **Capability Resolution Algorithm**: Project → Global → External Registry resolution order with conflict resolution
- **Skill Discovery Mechanism**: Composition and validation of skill chains for complex intents
- **Skill Composition Engine**: Declarative skill graphs, parameter binding, and composition validation
- **Capability Ranking Framework**: Multi-dimensional scoring (relevance, cost, risk, policy, performance)
- **Dependency Resolution**: DAG construction, cycle detection, topological ordering
- **Version Compatibility Engine**: Semantic versioning, constraint satisfaction, compatibility matrix
- **Duplicate Detection**: Structural and semantic equivalence detection
- **Confidence Scoring System**: Quantitative confidence for each planning decision with propagation
- **Metadata Validation**: Schema validation, manifest completeness, signature verification
- **Policy Validation Engine**: Policy-as-code evaluation, dynamic policy updates
- **Governance Detection**: Identification of capabilities requiring human/committee approval
- **AI Council Governance**: Multi-model deliberation for approval gates and ambiguous resolutions
- **Capability Classification Taxonomy**: Type, criticality, sensitivity, blast radius classification
- **Cost Estimation Model**: Multi-resource cost modeling with confidence intervals
- **Risk Classification Framework**: Risk level assignment with mitigation tracking
- **Resource Budget Computation**: Aggregate resource requirements with contingency
- **Capability Recommendation Engine**: Alternative and complementary capability suggestions with recommendation graph
- **Capability Plan Assembly**: Final plan serialization with all execution bindings
- **Optimization Layer**: Cost/latency/risk optimization passes with execution feedback integration
- **Planning Memory**: Cross-flow pattern reuse, substitution caching, optimization memoization
- **Model Routing**: Planning subtask routing to appropriate models via Hermes Kernel
- **Self-Healing Planning**: Checkpoint recovery, adaptive retry, and automatic substitution on transient failures
- **Event Emission**: All planning events per Part 2 Event System
- **Traceability**: Decision audit trail linking intent → requirements → capabilities → plan
- **Optimization Feedback**: Execution-phase metrics feeding back into planning cost/risk models

### 8.2.2.2 Out of Scope

The following are **out of scope** for Section 8.2 (handled elsewhere):

| Topic | Handled In |
|-------|------------|
| **Capability Execution** | Section 8.3 (Execution Engine) |
| **Runtime Retry/Fallback** | Section 8.3 (Execution Engine) |
| **Saga/Compensation Orchestration** | Section 8.3 (Execution Engine) |
| **Capability Registry Storage** | Part 6 (Capability Facade Services) |
| **Capability Registration/Publishing** | Part 6 (Capability Facade Services) |
| **Event Transport/Delivery** | Part 2 (Event System) |
| **Kernel Scheduling** | Part 1 (Hermes Kernel) |
| **Workflow Definition/Execution** | Part 7 (Workflow & Orchestration) |
| **State Persistence** | Part 3 (Core Managers – State Manager) |
| **Authentication/Authorization** | Part 5 (Engineering Services – Auth) |
| **Metrics Collection** | Part 5 (Engineering Services – Observability) |
| **Human-in-the-Loop Approval UI** | Part 9+ (User Interaction Layer) |
| **External Registry Protocols** | Part 9+ (Integration Layer) |
| **AI Council UI/Deliberation Interface** | Part 9+ (User Interaction Layer) |
| **Model Registry/Management** | Part 5 (Engineering Services – Model Manager) |
| **External Model Provider Integration** | Part 9+ (Integration Layer) |

### 8.2.2.3 Dependencies

| Dependency | Version | Nature |
|------------|---------|--------|
| Part 0 (Principles) | 1.0.0 | Normative — conformance foundation |
| Part 1 (Hermes Kernel) | 1.0.0 | Required — kernel services, component lifecycle, model routing |
| Part 2 (Event System) | 1.0.0 | Required — event emission, correlation, ordering |
| Part 3 (Core Managers) | 1.0.0 | Required — State Manager, Config Manager, Resource Manager |
| Part 4 (Service Framework) | 1.0.0 | Required — service discovery, health, contracts |
| Part 5 (Engineering Services) | 1.0.0 | Required — Auth, Observability, Policy Engine, Model Manager |
| Part 6 (Capability Facade) | 1.0.0 | Required — Capability Registry, Manifest Schema |
| Part 7 (Workflow) | 1.0.0 | Required — Workflow IR, orchestration primitives |
| Section 8.1 (Agent Overview) | 1.0.0 | Required — agent architecture, terminology |

### 8.2.2.4 Relationship with Other Parts

#### Part 1: Hermes Kernel
- Discovery & Planning runs as a **Kernel Component** (Part 1 §1.3)
- Uses **Kernel Event Bus** for all event emission (Part 2)
- Requests **Resource Quotas** from Resource Manager (Part 3)
- Reads **Configuration** from Config Manager (Part 3)
- **Routes planning subtasks** (classification, ranking, summarization) to appropriate models via **Model Router** (Part 1 §1.4)

#### Part 2: Event System
- Emits `CapabilityDiscoveryStarted`, `CapabilityResolved`, `PlanAssembled`, `PlanValidationFailed` events
- Consumes `RegistryUpdated`, `PolicyChanged`, `CapabilityDeprecated` events for cache invalidation
- All events use **Correlation ID** linking intent to plan

#### Part 3: Core Managers
- **State Manager**: Stores planning snapshots, decision traces
- **Config Manager**: Provides discovery policies, ranking weights, cost models
- **Resource Manager**: Validates resource budgets against quotas

#### Part 5: Engineering Services
- **Auth**: Validates caller permissions for registry access
- **Observability**: Emits planning metrics, traces, audit events
- **Policy Engine**: Evaluates policy-as-code for every resolution decision
- **Model Manager**: Provides model registry, routing hints, token budgets for planning subtasks

#### Part 6: Capability Facade Services
- **Primary data source**: Capability Registry (manifest, versions, metadata)
- **Capability Manifest Schema** defines all fields used in resolution
- **Capability Facade** provides query interface (search, filter, get)

#### Part 7: Workflow & Orchestration
- **Capability Plan** output conforms to Workflow IR (Part 7 §7.3)
- **Execution Graph** maps to Workflow DAG structure
- **Rollback Nodes** align with Workflow Compensation Actions

#### Section 8.1: Intelligent Agent Architecture Overview
- Discovery & Planning is the **Planning Phase** of the Agent Loop (8.1.3)
- Outputs **Capability Plan** consumed by Execution Engine (8.3)
- Uses **Intent Schema** defined in 8.1.4
- Conforms to **Agent Invariants** in 8.1.5

---

## 8.2.3 Capability Discovery Architecture

### 8.2.3.1 Overview

The Capability Discovery subsystem is a **pipeline of deterministic stages** that transforms an `Intent` into a ranked, validated, dependency-resolved set of capability candidates ready for plan assembly.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAPABILITY DISCOVERY PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   INTENT     │───▶│  CAPABILITY  │───▶│  DEPENDENCY  │───▶│  PLAN    │  │
│  │  ANALYSIS    │    │  RESOLUTION  │    │  RESOLUTION  │    │ ASSEMBLY │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│        │                   │                   │                   │        │
│        ▼                   ▼                   ▼                   ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │ • Decompose  │    │ • Project    │    │ • Build DAG  │    │ • Topo   │  │
│  │ • Normalize  │    │ • Global     │    │ • Cycle det. │    │   Order  │  │
│  │ • Extract    │    │ • External   │    │ • Version    │    │ • Parallel│ │
│  │   Req/Con    │    │ • Conflict   │    │   Compat     │    │   Groups │  │
│  │ • Risk/Gov   │    │   Resolution │    │ • Substitute │    │ • Bind   │  │
│  │ • Confidence │    │ • Substitute │    │ • Validate   │    │   Retry  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│                                                                             │
│  CROSS-CUTTING CONCERNS (applied at every stage):                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Confidence Scoring    • Metadata Validation    • Policy Validation │  │
│  │ • Governance Detection  • Capability Classification                  │  │
│  │ • Cost Estimation       • Risk Classification     • Duplicate Detect │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2.3.2 Pipeline Stages

| Stage | Input | Output | Deterministic | Pure Function |
|-------|-------|--------|---------------|---------------|
| **Intent Analysis** | Raw Intent | `AnalyzedIntent` (requirements, constraints, risks, governance) | YES | YES |
| **Capability Resolution** | `AnalyzedIntent` + Registry Snapshot | `ResolvedCapabilities[]` (ranked, deduplicated) | YES | YES |
| **Dependency Resolution** | `ResolvedCapabilities[]` | `CapabilityDAG` (validated, versioned, substituted) | YES | YES |
| **Plan Assembly** | `CapabilityDAG` + Budgets + Policies | `CapabilityPlan` (executable, bound) | YES | YES |

**Invariant DISCOVERY-1 (Pipeline Determinism):**  
Given identical `Intent`, `RegistrySnapshot`, `PolicySnapshot`, `ConfigurationSnapshot` → the pipeline MUST produce identical `CapabilityPlan` including all intermediate artifacts.

**Invariant DISCOVERY-2 (Stage Isolation):**  
Each stage MUST NOT mutate inputs. Outputs are new immutable structures. Stages communicate only via explicit output→input handoff.

**Invariant DISCOVERY-3 (Snapshot Consistency):**  
The Registry Snapshot, Policy Snapshot, and Configuration Snapshot MUST be taken atomically at pipeline start (single logical timestamp). No stage may observe a different snapshot.

### 8.2.3.3 Cross-Cutting Concerns

The following concerns are **not separate stages** but are evaluated at every stage where relevant data exists:

| Concern | Evaluated At | Output |
|---------|--------------|--------|
| **Confidence Scoring** | All stages | `confidence: 0.0–1.0` per decision |
| **Metadata Validation** | Resolution, Dependency | `validationResult: PASS/WARN/FAIL` |
| **Policy Validation** | Resolution, Dependency, Assembly | `policyDecision: ALLOW/DENY/REQUIRE_APPROVAL` |
| **Governance Detection** | Resolution, Assembly | `governanceFlags[]` |
| **Capability Classification** | Resolution | `classification: CapabilityClass` |
| **Cost Estimation** | Resolution, Dependency, Assembly | `costEstimate: CostModel` |
| **Risk Classification** | Intent Analysis, Assembly | `riskLevel: LOW/MEDIUM/HIGH/CRITICAL` |
| **Duplicate Detection** | Resolution | `duplicateGroups[]` |
| **Resource Requirements** | Dependency, Assembly | `resourceBudget: ResourceBudget` |
| **Planning Memory** | All stages | `memoryContext: PlanningMemoryContext` |
| **Discovery Cache** | Resolution | `cacheHit: BOOLEAN, cacheKey: CacheKey` |

### 8.2.3.4 Registry Resolution Order

Capabilities are resolved in **strict priority order**:

```
PRIORITY 1: PROJECT REGISTRY
├── Capabilities defined in the current project/workspace
├── Highest precedence — overrides global/external
├── Version pinned by project manifest
└── Governance: Project-level approval sufficient

        ↓ (fallback if not found or version conflict)

PRIORITY 2: PROJECT SKILL REGISTRY
├── Skill compositions defined in project scope (§8.2.5.3)
├── Precedence for project-specific skill chains
├── Version pinned by project skill manifest
└── Governance: Project-level approval for skill execution

        ↓ (fallback if not found or version conflict)

PRIORITY 3: GLOBAL REGISTRY
├── Organization-wide shared capabilities
├── Version managed by platform team
├── Governance: Organizational policy applies
└── Fallback for project capabilities

        ↓ (fallback if not found or version conflict)

PRIORITY 4: GLOBAL SKILL REGISTRY
├── Organization-wide shared skill compositions
├── Version managed by platform team
├── Governance: Organizational skill policy applies
└── Fallback for project skill compositions

        ↓ (fallback if not found or version conflict)

PRIORITY 5: EXTERNAL REGISTRY
├── Third-party / public registries (configured endpoints)
├── Version resolution via semantic versioning
├── Governance: External dependency policy applies
├── Requires: Network access, trust verification, signature validation
└── Lowest precedence — used only when no project/global match

        ↓ (fallback if not found or version conflict)

PRIORITY 6: EXTERNAL SKILL REGISTRY
├── Third-party skill compositions (verified endpoints)
├── Version resolution via semantic versioning
├── Governance: External skill policy applies
└── Lowest precedence — requires explicit policy opt-in
```

**Invariant DISCOVERY-4 (Resolution Order):**  
A capability from a lower-priority registry MUST NOT be selected if a compatible capability exists in a higher-priority registry, unless explicitly overridden by policy.

**Invariant DISCOVERY-5 (Explicit Override):**  
Policy MAY declare `preferExternal: true` for specific capability IDs, inverting priority for those capabilities only. Such overrides MUST be audited.

**Invariant DISCOVERY-6 (Skill Registry Precedence):**  
Skill registries at each priority level are consulted immediately after their capability registry peer. A skill match at priority N takes precedence over a capability match at priority N+1.

### 8.2.3.5 Model Routing Integration

The Discovery Pipeline integrates with the **Hermes Kernel Model Router** (Part 1 §1.3) for AI-augmented planning subtasks:

| Subtask | Model Route | Purpose |
|---------|-------------|---------|
| **Intent Classification** | `model: planning/intent-classifier` | Categorize raw intent into intentType, extract domain |
| **Risk Assessment** | `model: planning/risk-assessor` | Identify implicit risks not captured by explicit constraints |
| **Capability Ranking** | `model: planning/ranker` | Score candidates on relevance, cost, risk when heuristic ranking is ambiguous |
| **Substitution Suggestion** | `model: planning/substitution-advisor` | Propose alternatives when primary resolution fails |
| **Governance Summarization** | `model: planning/governance-summarizer` | Generate human-readable evidence for approval gates |
| **Plan Optimization** | `model: planning/optimizer` | Suggest cost/latency/risk optimizations on assembled plan |

**Routing Rules:**
- Model routing requests are emitted as `aios.planning.model.route_requested` events
- Hermes Kernel routes to appropriate model based on task type, tenant policy, and model availability
- Responses are captured as `aios.planning.model.response` events with correlation to planning flow
- All model interactions are **deterministically replayable** via snapshot (model version, prompt, temperature=0)

**Invariant DISCOVERY-7 (Model Determinism):**  
All model routing calls MUST use temperature=0 and fixed seed. Identical inputs MUST produce identical outputs for replay verification.

**Invariant DISCOVERY-8 (Model Routing Audit):**  
Every model routing call MUST be recorded with: `modelId`, `modelVersion`, `promptHash`, `responseHash`, `latencyMs`, `tokenUsage`, `correlationId`.

### 8.2.3.6 AI Council for Governance Deliberation

For governance decisions requiring multi-perspective analysis (approval gates, policy exceptions, ambiguous resolutions), the Discovery Pipeline engages the **AI Council** — a quorum of diverse models deliberating under structured protocol:

```
AI Council Protocol:
1. TRIGGER: Policy requires APPROVAL, or resolution ambiguity > threshold (INV-DISC-3)
2. COMPOSITION: 3+ models selected by policy (default: reasoning, safety, cost-optimization)
3. DELIBERATION: Each model receives identical context (intent, candidates, policies, history)
4. VOTING: Models vote ALLOW / DENY / DEFER with rationale
5. QUORUM: ≥2/3 ALLOW → APPROVED; ≥2/3 DENY → REJECTED; else → HUMAN_ESCALATION
6. RECORD: Full deliberation transcript stored in Governance Manifest (§8.2.7.9)
```

**Invariant DISCOVERY-9 (Council Determinism):**  
Given identical context and model versions, AI Council MUST produce identical verdict. Deliberation uses temperature=0, fixed turn order.

**Invariant DISCOVERY-10 (Council Audit):**  
Every council deliberation MUST produce immutable audit record with: `councilId`, `correlationId`, `models[]`, `votes[]`, `verdict`, `transcriptHash`, `timestamp`.

### 8.2.3.7 Discovery Cache Architecture

The Capability Resolution stage employs a **deterministic, snapshot-isolated cache** to accelerate repeated resolutions:

```
Cache Key Structure:
CacheKey = Hash(
    IntentUnit.requirements.hash,      // Capability pattern, interfaces, QoS
    IntentUnit.constraints.hash,       // Version, cost, region, compliance
    RegistrySnapshot.version,          // Immutable snapshot ID
    PolicySnapshot.version,            // Immutable snapshot ID
    ConfigSnapshot.version             // Immutable snapshot ID
)
```

**Cache Behavior:**
- **Write-Through on Miss**: Resolution result (primary + alternatives + confidence) cached on first computation
- **Read-Through on Hit**: Cached `ResolvedUnit` returned with `cacheHit: true`, confidence propagated
- **Invalidation**: On `RegistryUpdated`, `PolicyChanged`, `CapabilityDeprecated` events — effected entries evicted by snapshot version mismatch
- **TTL**: Configurable (`planning.cacheTtl`, default: 5 min). Stale entries serve but trigger async refresh

**Invariant DISCOVERY-11 (Cache Determinism):**  
Cache hits MUST produce bit-identical `ResolvedUnit` to cache misses. Cache is a pure acceleration layer — no semantic difference.

**Invariant DISCOVERY-12 (Cache Isolation):**  
Cache entries are scoped to `RegistrySnapshot` + `PolicySnapshot` + `ConfigSnapshot` triple. Cross-snapshot contamination is impossible by key construction.

### 8.2.3.8 Planning Memory

The Planning Memory subsystem provides **cross-flow pattern reuse** — learning from successful planning outcomes to accelerate and improve future plans:

```
PlanningMemoryContext:
- successfulPatterns[]: { intentSignature, capabilitySequence, optimizationHints }
- substitutionHistory[]: { originalPattern, substitutedCapability, successRate }
- optimizationMemo[]: { planSignature, optimizationApplied, measuredDelta }
- failureSignatures[]: { failureClass, contextSignature, recoveryAction, success }
```

**Usage at Each Stage:**
| Stage | Memory Query | Memory Write |
|-------|--------------|--------------|
| Intent Analysis | Similar intent signatures → risk/governance priors | New intent signature + extracted metadata |
| Capability Resolution | Successful substitutions for failed patterns | Resolution outcome + confidence |
| Dependency Resolution | Known compatible version combos | Validated DAG patterns |
| Plan Assembly | Proven parallel group structures | Execution graph template + metrics |
| Optimization | Historical optimization effectiveness | Applied optimization + predicted vs actual |

**Invariant DISCOVERY-13 (Memory Determinism):**  
Planning Memory is read-only during pipeline execution. Writes occur ONLY at pipeline completion (success or failure) via `PlanningMemoryRecorded` event. No in-flight mutations.

**Invariant DISCOVERY-14 (Memory Scope):**  
Planning Memory is tenant-scoped. Cross-tenant pattern reuse requires explicit policy opt-in (`planning.memory.allowCrossTenant`).

### 8.2.3.9 Capability Discovery Outputs

| Artifact | Schema Reference | Description |
|----------|------------------|-------------|
| `AnalyzedIntent` | §8.2.4 | Decomposed, normalized intent with extracted metadata |
| `ResolvedCapability` | §8.2.5 | Single capability match with version, source, confidence |
| `SkillComposition` | §8.2.5.3 | Validated skill graph with parameter bindings |
| `CapabilityDAG` | §8.2.6 | Validated dependency graph with versions, substitutions |
| `CapabilityPlan` | §8.2.6 | Executable plan with execution order, bindings, budgets |

---

## 8.2.4 Intent Analysis

### 8.2.4.1 Purpose

Intent Analysis transforms raw, potentially ambiguous intent into a structured, normalized `AnalyzedIntent` containing explicit requirements, constraints, risks, and governance markers. This stage is the **single point of semantic interpretation** — all downstream stages operate on the analyzed output, never on raw intent.

### 8.2.4.2 Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `intentId` | UUID | YES | Unique identifier for this intent |
| `rawIntent` | String | YES | Natural language or structured intent text |
| `intentType` | Enum | YES | `COMMAND` \| `QUERY` \| `WORKFLOW` \| `SKILL` |
| `context` | IntentContext | NO | Session, user, environment context |
| `metadata` | Map<String,Any> | NO | Arbitrary metadata (correlation IDs, tags) |

**IntentContext Schema:**
```json
{
  "sessionId": "uuid",
  "userId": "string",
  "tenantId": "string",
  "environment": "DEV|STAGING|PROD",
  "permissions": ["string"],
  "resourceQuotas": "ResourceQuotaRef"
}
```

### 8.2.4.3 Processing Steps

#### Step 1: Intent Decomposition

The raw intent is decomposed into **atomic intent units** — each representing a single, independently executable capability need.

```
Raw Intent: "Deploy the payment service to staging, run integration tests, and notify the team"

Decomposed Units:
├── Unit 1: DEPLOY_SERVICE(service="payment", target="staging")
├── Unit 2: RUN_TESTS(suite="integration", service="payment")
└── Unit 3: NOTIFY_TEAM(channel="slack", message="Deployment complete")
```

**Invariant INTENT-1 (Decomposition Atomicity):**  
Each decomposed unit MUST map to at least one registered capability. A unit that maps to zero capabilities is a **planning error** (not a resolution failure).

**Invariant INTENT-2 (Decomposition Completeness):**  
The union of all decomposed units MUST fully cover the semantics of the raw intent. No semantic loss is permitted.

#### Step 2: Normalization

Each intent unit is normalized to a **canonical form**:

| Normalization | Description |
|---------------|-------------|
| **Parameter Canonicalization** | Map aliases to canonical parameter names (e.g., `env` → `environment`) |
| **Value Normalization** | Normalize values (e.g., `staging` → `STAGING`, `k8s` → `KUBERNETES`) |
| **Implicit Defaults** | Apply defaults from capability manifests for omitted optional parameters |
| **Type Coercion** | Coerce values to manifest-declared types with validation |
| **Reference Resolution** | Resolve context references (e.g., `$SESSION.service` → actual value) |

#### Step 3: Requirement Extraction

For each normalized unit, extract **explicit requirements**:

| Requirement Type | Source | Example |
|------------------|--------|---------|
| **Capability ID Pattern** | Manifest `matchPatterns` | `deploy.*`, `test.*` |
| **Parameter Constraints** | Manifest `parameters` schema | `environment IN [STAGING, PROD]` |
| **Output Requirements** | Manifest `outputs` | `deploymentUrl: URI` |
| **Quality Attributes** | Manifest `qos` | `latency < 5s`, `availability > 99.9%` |
| **Interface Contracts** | Manifest `interfaces` | `implements: DeploymentTarget` |

#### Step 4: Constraint Extraction

Extract **constraints** that limit capability selection:

| Constraint Type | Description | Example |
|-----------------|-------------|---------|
| **Resource Limits** | Max CPU, memory, GPU, network | `maxCPU: "2000m"` |
| **Cost Ceiling** | Maximum estimated cost | `maxCostUSD: 10.00` |
| **Latency Budget** | Maximum execution time | `maxDuration: 300s` |
| **Geographic/Region** | Deployment region constraints | `region: "us-east-1"` |
| **Compliance** | Required certifications | `compliance: ["SOC2", "HIPAA"]` |
| **Dependency Exclusions** | Forbidden capabilities | `exclude: ["legacy-deploy"]` |
| **Version Pinning** | Required version ranges | `version: ">=2.0.0 <3.0.0"` |

#### Step 5: Risk Identification

Identify **inherent risks** in the intent:

| Risk Category | Detection Method | Example |
|---------------|------------------|---------|
| **Data Sensitivity** | Parameter analysis, data flow | PII in parameters |
| **Blast Radius** | Capability metadata, dependency graph | Production deployment |
| **Irreversibility** | Capability `reversible: false` | Database migration |
| **External Dependency** | Capability `external: true` | Third-party API call |
| **Privilege Escalation** | Capability `requiresElevated: true` | Infrastructure provisioning |
| **Cost Uncertainty** | Capability `costModel: variable` | ML training job |

#### Step 6: Governance Identification

Identify **governance requirements**:

| Governance Trigger | Detection | Action |
|--------------------|-----------|--------|
| **Human Approval Required** | Capability `governance.approvalRequired: true` | Flag for approval gate |
| **Compliance Review** | Capability `governance.complianceTags[]` | Route to compliance team |
| **Security Review** | Capability `governance.securityReview: true` | Flag for security team |
| **Cost Threshold** | Estimated cost > policy threshold | Flag for FinOps review |
| **Production Impact** | Target environment = PROD | Flag for change advisory |
| **Data Egress** | Capability `dataEgress: true` | Flag for DLP review |

### 8.2.4.4 Output: AnalyzedIntent

```json
{
  "intentId": "uuid",
  "correlationId": "uuid",
  "timestamp": "ISO8601",
  "units": [
    {
      "unitId": "uuid",
      "action": "DEPLOY_SERVICE",
      "canonicalParameters": {
        "service": "payment",
        "environment": "STAGING",
        "version": "latest"
      },
      "requirements": [
        { "type": "CAPABILITY_PATTERN", "pattern": "deploy.*" },
        { "type": "PARAMETER_CONSTRAINT", "param": "environment", "allowed": ["STAGING"] }
      ],
      "constraints": {
        "maxDuration": 300,
        "maxCostUSD": 5.00,
        "region": "us-east-1"
      },
      "risks": [
        { "category": "BLAST_RADIUS", "level": "MEDIUM", "reason": "Staging deployment" },
        { "category": "EXTERNAL_DEPENDENCY", "level": "LOW", "reason": "Container registry" }
      ],
      "governance": [
        { "trigger": "ENVIRONMENT_STAGING", "approvalRequired": false }
      ],
      "confidence": 0.95
    }
  ],
  "globalConstraints": {
    "maxTotalCostUSD": 20.00,
    "maxTotalDuration": 600,
    "requiredCompliance": ["SOC2"]
  },
  "globalRisks": [
    { "category": "COST_UNCERTAINTY", "level": "LOW" }
  ],
  "globalGovernance": [],
  "overallConfidence": 0.92
}
```

### 8.2.4.5 Confidence Scoring

Each unit and the overall intent receive a **confidence score** (0.0–1.0):

| Factor | Weight | Description |
|--------|--------|-------------|
| **Pattern Match Specificity** | 0.30 | How precisely units match capability patterns |
| **Parameter Completeness** | 0.25 | Required parameters provided vs. defaults used |
| **Constraint Satisfiability** | 0.20 | Constraints compatible with known capabilities |
| **Risk Identifiability** | 0.15 | Risks clearly mapped to known categories |
| **Governance Clarity** | 0.10 | Governance triggers unambiguous |

**Confidence Propagation:** The `overallConfidence` and per-unit `confidence` scores are **forward-propagated** through the entire planning pipeline:
- **Capability Resolution** (§8.2.5): Each resolution decision receives `inputConfidence = unit.confidence` and produces `resolutionConfidence` (see §8.2.5.13)
- **Dependency Resolution** (§8.2.6): Graph validation confidence = `min(resolutionConfidence)` across all edges; substitution reduces confidence by policy-configured penalty
- **Plan Assembly** (§8.2.6): `planConfidence = min(graphConfidence, bindingConfidence, budgetConfidence)`
- **Artifact Generation** (§8.2.7): Artifacts carry `planConfidence` as metadata

**Invariant INTENT-3 (Confidence Threshold):**  
If `overallConfidence < 0.70`, the pipeline MUST emit `IntentAnalysisLowConfidence` event and MAY halt (policy-dependent). The plan MUST NOT be assembled below this threshold without explicit override.

**Invariant INTENT-4 (Confidence Monotonicity):**  
Confidence scores MUST never increase downstream — each stage can only maintain or reduce confidence. The final `planConfidence ≤ overallConfidence`.

### 8.2.4.6 Traceability

Every `AnalyzedIntent` MUST include a **traceability matrix** linking:

| From | To | Relationship |
|------|-----|--------------|
| Raw Intent Text Span | Intent Unit | `DERIVES_FROM` |
| Intent Unit | Requirement | `REQUIRES` |
| Intent Unit | Constraint | `CONSTRAINS` |
| Intent Unit | Risk | `IMPLIES_RISK` |
| Intent Unit | Governance Flag | `TRIGGERS_GOVERNANCE` |

### 8.2.4.7 Events Emitted

| Event | Trigger | Payload |
|-------|---------|---------|
| `IntentAnalysisStarted` | Pipeline entry | `intentId`, `correlationId` |
| `IntentDecomposed` | After Step 1 | `intentId`, `unitCount` |
| `IntentNormalized` | After Step 2 | `intentId`, `units[]` |
| `RequirementsExtracted` | After Step 3 | `intentId`, `requirements[]` |
| `ConstraintsExtracted` | After Step 4 | `intentId`, `constraints` |
| `RisksIdentified` | After Step 5 | `intentId`, `risks[]` |
| `GovernanceIdentified` | After Step 6 | `intentId`, `governance[]` |
| `IntentAnalysisCompleted` | Success | `AnalyzedIntent` |
| `IntentAnalysisFailed` | Any failure | `intentId`, `error`, `stage` |

### 8.2.4.8 Failure Handling

| Failure Mode | Behavior |
|--------------|----------|
| **Unparsable Intent** | Emit `IntentAnalysisFailed`, halt pipeline |
| **Zero Capability Matches** | Emit `IntentAnalysisFailed` (no capable units), halt |
| **Constraint Contradiction** | Emit `IntentAnalysisFailed` (unsatisfiable), halt |
| **Confidence Below Threshold** | Emit `IntentAnalysisLowConfidence`, policy decides continue/halt |
| **Governance Block** | Emit `GovernanceBlock`, halt pending approval (async) |

---

## 8.2.5 Capability Resolution

### 8.2.5.1 Purpose

Capability Resolution maps each intent unit's requirements to concrete, versioned capabilities from the registry, applying the Project → Global → External resolution order, resolving conflicts, substituting equivalents, and validating compatibility and policy compliance.

### 8.2.5.2 Input

- `AnalyzedIntent` (from §8.2.4)
- `RegistrySnapshot` (immutable view of all three registries at pipeline start timestamp)
- `PolicySnapshot` (immutable view of all policies at pipeline start timestamp)

### 8.2.5.3 Resolution Algorithm

For each **Intent Unit** in `AnalyzedIntent.units`:

```
FUNCTION ResolveUnit(unit, registrySnapshot, policySnapshot, planningMemory):
    // CHECK CACHE FIRST (§8.2.3.7)
    cacheKey ← ComputeCacheKey(unit, registrySnapshot, policySnapshot)
    cached ← CacheGet(cacheKey)
    IF cached ≠ NULL:
        RETURN cached WITH cacheHit=true
    
    // CHECK PLANNING MEMORY FOR SUBSTITUTIONS (§8.2.3.8)
    memoryHints ← PlanningMemoryQuery(unit.requirements.pattern)
    
    candidates ← ∅
    
    // PRIORITY 1: PROJECT REGISTRY
    projectMatches ← QueryRegistry(registrySnapshot.project, unit.requirements)
    candidates ← candidates ∪ AnnotateSource(projectMatches, "PROJECT")
    
    // PRIORITY 2: PROJECT SKILL REGISTRY
    projectSkillMatches ← QuerySkillRegistry(registrySnapshot.projectSkills, unit.requirements)
    candidates ← candidates ∪ AnnotateSource(projectSkillMatches, "PROJECT_SKILL")
    
    // PRIORITY 3: GLOBAL REGISTRY
    globalMatches ← QueryRegistry(registrySnapshot.global, unit.requirements)
    candidates ← candidates ∪ AnnotateSource(globalMatches, "GLOBAL")
    
    // PRIORITY 4: GLOBAL SKILL REGISTRY
    globalSkillMatches ← QuerySkillRegistry(registrySnapshot.globalSkills, unit.requirements)
    candidates ← candidates ∪ AnnotateSource(globalSkillMatches, "GLOBAL_SKILL")
    
    // PRIORITY 5: EXTERNAL REGISTRY
    IF policySnapshot.allowExternalResolution:
        externalMatches ← QueryRegistry(registrySnapshot.external, unit.requirements)
        candidates ← candidates ∪ AnnotateSource(externalMatches, "EXTERNAL")
    
    // PRIORITY 6: EXTERNAL SKILL REGISTRY
    IF policySnapshot.allowExternalSkills:
        externalSkillMatches ← QuerySkillRegistry(registrySnapshot.externalSkills, unit.requirements)
        candidates ← candidates ∪ AnnotateSource(externalSkillMatches, "EXTERNAL_SKILL")
    
    // FILTER: Policy validation (early)
    candidates ← FilterByPolicy(candidates, unit.constraints, policySnapshot)
    
    // DEDUPLICATE: Structural + semantic equivalence
    candidates ← Deduplicate(candidates)
    
    // APPLY MEMORY HINTS: Boost confidence for historically successful patterns
    candidates ← ApplyMemoryHints(candidates, memoryHints)
    
    // RANK: Multi-dimensional scoring
    ranked ← RankCandidates(candidates, unit, policySnapshot)
    
    // SELECT: Top candidate + alternatives
    primary ← ranked[0]
    alternatives ← ranked[1:3]  // Top 3 alternatives for fallback
    
    // CONFIDENCE PROPAGATION (§8.2.4.5)
    inputConfidence ← unit.confidence
    resolutionConfidence ← ComputeResolutionConfidence(inputConfidence, primary, ranked, policySnapshot)
    
    result ← ResolvedUnit(unit.unitId, primary, alternatives, ranked, resolutionConfidence)
    
    // CACHE RESULT
    CachePut(cacheKey, result)
    
    RETURN result
```

### 8.2.5.4 Skill Composition Engine

**Skill Compositions** are declarative graphs of capability invocations that implement complex intent patterns. A skill is resolved like a capability but expands into an execution subgraph at planning time.

**Skill Manifest Schema:**
```json
{
  "skillId": "deploy-and-test.v1",
  "version": "1.2.0",
  "source": "GLOBAL_SKILL",
  "description": "Deploy service, run integration tests, notify on result",
  "parameters": {
    "service": { "type": "string", "required": true },
    "environment": { "type": "enum", "values": ["STAGING", "PROD"] },
    "testSuite": { "type": "string", "default": "integration" }
  },
  "graph": {
    "nodes": [
      { "nodeId": "deploy", "capabilityPattern": "deploy.*", "parameters": { "service": "${service}", "environment": "${environment}" } },
      { "nodeId": "test", "capabilityPattern": "test.*", "parameters": { "service": "${service}", "suite": "${testSuite}" }, "dependsOn": ["deploy"], "dependencyType": "HARD" },
      { "nodeId": "notify", "capabilityPattern": "notify.*", "parameters": { "channel": "slack" }, "dependsOn": ["test"], "dependencyType": "HARD" }
    ],
    "outputs": { "deploymentUrl": "$.deploy.output.deploymentUrl", "testResult": "$.test.output.result" }
  },
  "governance": { "approvalRequired": true, "tags": ["DEPLOYMENT", "TESTING"] },
  "costEstimate": { "minUSD": 1.00, "maxUSD": 5.00 }
}
```

**Skill Resolution:**
1. Skill matched via `QuerySkillRegistry` (same criteria as capability query + `manifest.graph` compatibility)
2. Skill parameters bound from intent unit canonical parameters
3. Skill graph nodes resolved recursively via `ResolveUnit` (sub-resolution)
4. Sub-resolution shares parent's `RegistrySnapshot`, `PolicySnapshot`, `cacheKey` prefix
5. Resulting `SkillComposition` includes: expanded DAG, resolved capabilities, aggregated cost/risk, propagated confidence

**Invariant RESOLUTION-4 (Skill Expansion Determinism):**  
A skill composition MUST expand to an identical DAG given identical inputs and snapshots. Skill resolution is a pure function.

**Invariant RESOLUTION-5 (Skill Confidence):**  
Skill confidence = `min(node.confidence for all nodes in expanded graph)`. Skill confidence propagates as a single unit to downstream stages.

### 8.2.5.5 Registry Query

**QueryRegistry(registry, requirements)** returns all capabilities where:

| Match Criterion | Logic |
|-----------------|-------|
| **Capability ID Pattern** | `requirements.capabilityPattern` matches `manifest.id` (glob) |
| **Interface Implementation** | `manifest.implements` satisfies `requirements.interfaces[]` |
| **Parameter Compatibility** | `manifest.parameters` schema accepts `unit.canonicalParameters` |
| **Output Satisfaction** | `manifest.outputs` provides `requirements.outputRequirements[]` |
| **QoS Compliance** | `manifest.qos` meets `requirements.qualityAttributes[]` |

**QuerySkillRegistry(skillRegistry, requirements)** applies the same match criteria to skill manifests, additionally checking:
- Skill graph inputs compatible with `requirements`
- Skill graph outputs satisfy `requirements.outputRequirements[]`

### 8.2.5.5 Conflict Resolution

When multiple capabilities match a unit from the **same registry priority level**:

| Conflict Type | Resolution Rule |
|---------------|-----------------|
| **Same ID, Different Versions** | Select highest version satisfying `unit.constraints.version` (semver) |
| **Different IDs, Same Function** | Rank by: (1) Policy preference, (2) Cost, (3) Risk, (4) Performance, (5) Recency |
| **Exact Duplicate Manifest** | Prefer PROJECT > GLOBAL > EXTERNAL source |

**Invariant RESOLUTION-1 (Priority Preservation):**  
A capability from a lower-priority registry MUST NOT be selected over a compatible higher-priority capability unless the higher-priority capability is explicitly excluded by policy or fails validation.

**Invariant RESOLUTION-2 (Version Selection):**  
Version selection MUST follow semantic versioning (SemVer 2.0.0) with constraint satisfaction. Pre-release versions ONLY selected if explicitly allowed by policy.

### 8.2.5.6 Capability Substitution

If **no compatible capability** is found at any priority level:

1. **Check Substitution Rules** (from policy): `substitutionMap[capabilityPattern] → alternativePattern`
2. **Apply Substitution**: Retry resolution with alternative pattern
3. **Record Substitution**: `ResolvedUnit.substituted = true`, `originalRequirement = pattern`

**Invariant RESOLUTION-3 (Substitution Transparency):**  
Every substitution MUST be recorded in the plan with original requirement, substituted capability, and substitution rule ID. Substitutions MUST NOT be silent.

### 8.2.5.7 Compatibility Validation

Each candidate capability is validated for **compatibility** with the unit:

| Validation | Check |
|------------|-------|
| **Parameter Schema** | `unit.canonicalParameters` validates against `manifest.parameters` (JSON Schema) |
| **Output Schema** | `manifest.outputs` satisfies `unit.requirements.outputRequirements` |
| **Interface Contract** | `manifest.implements` covers `unit.requirements.interfaces` |
| **QoS Guarantees** | `manifest.qos` meets or exceeds `unit.requirements.qualityAttributes` |
| **Runtime Compatibility** | `manifest.runtime` compatible with target environment |

Failures produce `ValidationResult: FAIL` with specific violation details.

### 8.2.5.8 Policy Validation

Policy validation evaluates **organizational policies** against each candidate:

| Policy Dimension | Evaluation |
|------------------|------------|
| **Allowed Registries** | Candidate source ∈ `policy.allowedRegistries` |
| **Cost Ceiling** | `estimateCost(candidate) ≤ unit.constraints.maxCostUSD` |
| **Risk Tolerance** | `candidate.riskLevel ≤ policy.maxRiskLevel` |
| **Compliance** | `candidate.complianceTags ⊇ unit.constraints.requiredCompliance` |
| **Approved Capabilities** | `candidate.id ∈ policy.approvedCapabilities` (allowlist) |
| **Denied Capabilities** | `candidate.id ∉ policy.deniedCapabilities` (denylist) |
| **External Dependency Policy** | If EXTERNAL source, `policy.allowExternal = true` |
| **License Compliance** | `candidate.license` compatible with `policy.allowedLicenses` |

**Policy Decision:**
- `ALLOW`: Candidate passes all policies
- `DENY`: Candidate fails hard policy (denylist, license, compliance)
- `REQUIRE_APPROVAL`: Candidate triggers approval gate (cost threshold, risk, production)

### 8.2.5.9 Fallback Behavior

If **primary candidate** is `DENY` or `REQUIRE_APPROVAL` (and approval not granted):

1. Try **alternatives** in rank order
2. If alternatives exhausted → **substitution** (§8.2.5.6)
3. If substitution fails → **resolution failure** for this unit

### 8.2.5.10 Output: ResolvedCapabilities

```json
{
  "unitId": "uuid",
  "primary": {
    "capabilityId": "deploy.kubernetes.v2",
    "version": "2.3.1",
    "source": "GLOBAL",
    "registryUrl": "registry.ai-os.internal/global",
    "manifest": { ... },  // Full manifest snapshot
    "confidence": 0.94,
    "validation": { "status": "PASS", "checks": [...] },
    "policyDecision": "ALLOW",
    "costEstimate": { "minUSD": 0.50, "maxUSD": 2.00, "confidence": 0.85 },
    "riskLevel": "LOW",
    "classification": "INFRASTRUCTURE_DEPLOYMENT",
    "governanceFlags": [],
    "substituted": false
  },
  "alternatives": [
    { "capabilityId": "deploy.helm.v1", "version": "1.5.0", "source": "PROJECT", "confidence": 0.88, ... },
    { "capabilityId": "deploy.argo.v1", "version": "3.2.0", "source": "EXTERNAL", "confidence": 0.75, ... }
  ],
  "allCandidatesConsidered": 7,
  "resolutionTimestamp": "ISO8601"
}
```

### 8.2.5.11 Events Emitted

| Event | Trigger | Payload |
|-------|---------|---------|
| `CapabilityResolutionStarted` | Stage entry | `intentId`, `unitCount` |
| `CapabilityResolved` | Per unit success | `ResolvedUnit` |
| `CapabilitySubstituted` | Substitution applied | `unitId`, `original`, `substitute`, `ruleId` |
| `CapabilityResolutionFailed` | Unit resolution failure | `unitId`, `reason`, `candidatesTried` |
| `PolicyDeniedCapability` | Policy DENY | `unitId`, `capabilityId`, `policyRule` |
| `ApprovalRequired` | Policy REQUIRE_APPROVAL | `unitId`, `capabilityId`, `approvalType` |
| `CapabilityResolutionCompleted` | All units resolved | `ResolvedCapabilities[]` |

### 8.2.5.12 Confidence Propagation

Confidence scores flow through the pipeline with **multiplicative decay** and **evidence-based updates**:

```
Confidence Propagation Rules:

1. INTENT ANALYSIS → CAPABILITY RESOLUTION:
   unit.confidence_out = unit.confidence_in × resolution.confidence_factor
   where resolution.confidence_factor = 
     - 1.0 if primary candidate confidence ≥ 0.90
     - 0.95 if primary candidate confidence ≥ 0.80
     - 0.85 if primary candidate confidence ≥ 0.70
     - 0.70 if primary candidate confidence < 0.70 (triggers LowConfidence)

2. CAPABILITY RESOLUTION → DEPENDENCY RESOLUTION:
   node.confidence = primary.confidence × (1.0 - 0.1 × substitution_count)
   edge.confidence = min(source.confidence, target.confidence) × compatibility_score

3. PLAN ASSEMBLY:
   plan.overallConfidence = geometric_mean(node.confidences) × governance_factor
   where governance_factor = 1.0 if no gates, 0.95 per pending gate, 0.8 if any gate denied

**Invariant CONF-1 (Confidence Monotonicity):**
Confidence MUST never increase as the pipeline progresses. Each stage can only maintain or decay confidence.

**Invariant CONF-2 (Confidence Threshold):**
If `plan.overallConfidence < 0.60`, the plan MUST be marked `LOW_CONFIDENCE` and require explicit human override to proceed to execution.

**Invariant CONF-3 (Confidence Traceability):**
Every confidence value MUST include: `baseConfidence` (from intent), `decayFactors[]` (stage multipliers), `evidence[]` (supporting observations), `timestamp`.

### 8.2.5.13 Recommendation Graph

The Recommendation Graph captures **alternative and complementary capability relationships** discovered during resolution:

```
Recommendation Graph = (VR, ER) where:
- VR = ResolvedCapabilities ∪ Alternatives ∪ Substitutions
- ER = {RECOMMENDS, COMPLEMENTS, SUBSTITUTES, CONFLICTS_WITH}
```

| Edge Type | Semantics | Use Case |
|-----------|-----------|----------|
| **RECOMMENDS** | "If you use A, consider B" | Alternative with better cost/risk |
| **COMPLEMENTS** | "A works well with B" | Capability pairs with synergy (e.g., deploy + test) |
| **SUBSTITUTES** | "A can replace B" | Fallback chain, policy-driven alternatives |
| **CONFLICTS_WITH** | "A and B cannot co-exist" | Mutual exclusion (same resource, license conflict) |

**Construction:**
- Built during Capability Resolution from: policy substitution rules, manifest `recommends`/`complements`/`conflicts` fields, historical co-selection patterns from Planning Memory
- Scored by: historical success rate, cost delta, risk delta, policy compliance
- Top-K recommendations per node emitted in `ResolvedUnit.recommendations[]`

**Invariant REC-1 (Recommendation Validity):**
Every recommendation edge MUST have `evidence: {source: "policy" | "manifest" | "history", strength: 0.0–1.0}`.

**Invariant REC-2 (Recommendation Non-Blocking):**
Recommendations are advisory. Absence of a recommendation does not constrain resolution. Presence does not mandate selection.

### 8.2.5.14 Skill Composition Engine

For intent units matching `SKILL` intentType or capability patterns with `manifest.type: "SKILL"`, the Skill Composition Engine constructs and validates **skill graphs**:

**Skill Manifest Structure:**
```json
{
  "capabilityId": "skill.ci-cd.v1",
  "type": "SKILL",
  "version": "1.2.0",
  "skillGraph": {
    "nodes": [
      { "stepId": "build", "capabilityId": "build.maven.v1", "parameters": { "project": "${input.project}" } },
      { "stepId": "test", "capabilityId": "test.junit.v1", "parameters": { "artifact": "${steps.build.output.artifact}" }, "dependsOn": ["build"] },
      { "stepId": "deploy", "capabilityId": "deploy.kubernetes.v2", "parameters": { "image": "${steps.build.output.image}" }, "dependsOn": ["test"] }
    ],
    "inputs": { "project": "string", "environment": "string" },
    "outputs": { "deploymentUrl": "uri", "testReport": "uri" }
  },
  "governance": { "approvalRequired": false }
}
```

**Composition Validation:**
| Check | Description |
|-------|-------------|
| **Input Satisfiability** | All skill graph inputs bound to intent unit parameters or previous step outputs |
| **Output Completeness** | All declared skill outputs produced by some step |
| **Acyclicity** | Skill graph step dependencies form a DAG |
| **Parameter Consistency** | Step parameter types match capability manifest schemas |
| **Governance Aggregation** | If any step requires approval → skill requires approval |

**Resolution of Skill Capabilities:**
1. Match intent unit to Skill Manifest (via `matchPatterns` or `type: SKILL`)
2. Resolve skill graph steps as **nested capability resolutions** (recursive, same pipeline)
3. Flatten nested resolutions into parent `CapabilityDAG` with skill boundary markers
4. Aggregate confidence: `skill.confidence = geometric_mean(step.confidences) × skill_graph_validation_score`

**Invariant SKILL-1 (Skill Transparency):**
Skill compositions MUST be fully expanded in the final `CapabilityDAG` with `skillBoundary: { skillId, stepId }` annotations on each node. No opaque skill execution.

**Invariant SKILL-2 (Skill Governance Inheritance):**
A skill inherits the union of governance requirements from all its steps. Approval gates apply at skill entry point.

**Invariant SKILL-3 (Skill Determinism):**
Given identical inputs and snapshots, a skill composition MUST produce identical step resolutions and identical flattened DAG.

### 8.2.5.12 Failure Handling

| Failure Mode | Behavior |
|--------------|----------|
| **Zero Candidates (all registries)** | Emit `CapabilityResolutionFailed`, halt pipeline |
| **All Candidates DENY** | Emit `CapabilityResolutionFailed`, halt |
| **All Candidates REQUIRE_APPROVAL + No Approval** | Emit `ApprovalTimeout`, halt (async wait configurable) |
| **Substitution Loop Detected** | Emit `CapabilityResolutionFailed` (cycle), halt |
| **External Registry Unavailable** | Treat as empty registry; continue with Project/Global only |

---

## 8.2.6 Capability Planning

### 8.2.6.1 Purpose

Capability Planning transforms the flat list of `ResolvedCapabilities` into an **executable Capability Plan** — a validated, topologically ordered, resource-budgeted, governance-bound execution graph with all retry, rollback, loop, and provider bindings resolved.

### 8.2.6.2 Input

- `ResolvedCapabilities[]` (from §8.2.5)
- `AnalyzedIntent` (from §8.2.4) — for global constraints, risks, governance
- `PolicySnapshot` — for planning-time policy (parallelism limits, budget enforcement)
- `ResourceQuotas` (from Resource Manager) — for budget validation

### 8.2.6.3 Planning Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPABILITY PLANNING STAGES                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CAPABILITY GRAPH CONSTRUCTION                                          │
│     ├── Extract declared dependencies from manifests                       │
│     ├── Add implicit dependencies (data flow, ordering)                    │
│     └── Validate: NO CYCLES (Invariant PLAN-1)                             │
│                                    │                                        │
│                                    ▼                                        │
│  2. DEPENDENCY GRAPH VALIDATION & ENRICHMENT                               │
│     ├── Version compatibility across edges                                 │
│     ├── Interface compatibility (output→input)                             │
│     ├── Substitute incompatible edges (policy-driven)                      │
│     └── Annotate edge types: DATA / CONTROL / TRIGGER                      │
│                                    │                                        │
│                                    ▼                                        │
│  3. EXECUTION GRAPH CONSTRUCTION                                           │
│     ├── Topological sort → execution order                                 │
│     ├── Identify parallel groups (independent subgraphs)                   │
│     ├── Insert conditional branches (guard capabilities)                   │
│     ├── Mark optional capabilities (policy: optionalOnFailure)             │
│     └── Insert rollback nodes (compensation for irreversible)              │
│                                    │                                        │
│                                    ▼                                        │
│  4. BINDING RESOLUTION                                                     │
│     ├── Retry bindings (policy + capability manifest)                      │
│     ├── Loop bindings (capability manifest loop spec)                      │
│     ├── Provider requirements (capability manifest provider spec)          │
│     ├── Governance bindings (approval gates at nodes)                      │
│     └── Resource budgets (aggregate + per-node)                            │
│                                    │                                        │
│                                    ▼                                        │
│  5. PLAN VALIDATION & FINALIZATION                                         │
│     ├── Validate against global constraints                                │
│     ├── Validate resource budgets ≤ quotas                                 │
│     ├── Validate governance gates satisfiable                              │
│     ├── Compute success/failure criteria                                   │
│     ├── Assign plan ID, version, timestamp                                 │
│     └── Serialize CapabilityPlan                                           │
│                                    │                                        │
│                                    ▼                                        │
│  6. OPTIMIZATION LAYER (Policy-Gated)                                     │
│     ├── Cost optimization: substitute lower-cost capabilities (policy)     │
│     ├── Latency optimization: restructure parallel groups, reorder nodes   │
│     ├── Risk optimization: add fallback paths, reduce blast radius         │
│     ├── Resource optimization: right-sizeprovider requirements             │
│     ├── Apply Planning Memory optimization hints (§8.2.3.8)                │
│     ├── Validate: all invariants still hold post-optimization              │
│     └── Emit `PlanOptimized` event with before/after metrics               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2.6.4 Capability Graph

**Definition:** A directed graph `G = (V, E)` where:
- `V` = Resolved capabilities (one vertex per `ResolvedUnit.primary`)
- `E` = Dependencies declared in capability manifests (`manifest.dependsOn[]`)

**Dependency Types:**

| Dependency Type | Semantics | Edge Annotation |
|-----------------|-----------|-----------------|
| **Hard Dependency** | Target MUST complete successfully before source starts | `type: HARD`, `required: true` |
| **Soft Dependency** | Target SHOULD complete; source can proceed with degraded function | `type: SOFT`, `required: false` |
| **Data Dependency** | Source consumes target's output as input | `type: DATA`, `dataContract: OutputSchema` |
| **Trigger Dependency** | Source starts on target's event/condition | `type: TRIGGER`, `condition: EventMatch` |
| **Ordering Only** | No data flow; only temporal ordering | `type: ORDERING` |

**Invariant PLAN-1 (Acyclicity):**  
The Capability Graph MUST be a **Directed Acyclic Graph (DAG)**. Cycles are planning errors. Cycle detection uses Tarjan's algorithm. If cycle detected → `PlanningFailed` with cycle path.

**Invariant PLAN-2 (Dependency Completeness):**  
Every `manifest.dependsOn` entry MUST resolve to a vertex in V. Unresolvable dependencies → `PlanningFailed`.

### 8.2.6.5 Dependency Graph (Enriched)

The **Dependency Graph** extends the Capability Graph with:

| Enhancement | Description |
|-------------|-------------|
| **Version Compatibility** | Each edge validated: `source.manifest.versionConstraint` satisfied by `target.manifest.version` |
| **Interface Compatibility** | For DATA edges: `target.manifest.outputs` compatible with `source.manifest.inputs` (schema subsumption) |
| **Substitution Edges** | If incompatible, policy may inject adapter capability → `substituted: true` |
| **Edge Metadata** | `latencyBudget`, `reliabilityRequirement`, `dataSensitivity` |

### 8.2.6.6 Execution Graph

The **Execution Graph** is the Dependency Graph transformed for execution:

```
Execution Graph = Dependency Graph
    + Topological Order (linearization)
    + Parallel Groups (maximal independent sets)
    + Conditional Branches (guard nodes)
    + Optional Nodes (can fail without failing plan)
    + Rollback Nodes (compensation for irreversible)
    + Governance Gates (approval checkpoints)
```

#### Topological Order

Computed via **Kahn's algorithm** on the DAG. Produces a partial order; any linear extension is valid.

**Invariant PLAN-3 (Deterministic Ordering):**  
Given identical DAG, the topological sort MUST produce identical ordering. Tie-breaking: capability ID lexicographic.

#### Parallel Groups

**Definition:** A set of nodes with **no dependency paths between them** (mutually independent).

```
Parallel Groups Algorithm:
1. Compute transitive closure of DAG
2. Nodes u, v in same group ⟺ ¬reachable(u,v) ∧ ¬reachable(v,u)
3. Maximize group size (greedy: largest antichains first)
4. Assign groupId, estimatedParallelDuration = max(node.duration)
```

**Invariant PLAN-4 (Parallelism Correctness):**  
Nodes in the same parallel group MUST have no direct or transitive dependency. Execution of group members in any order (or simultaneously) MUST produce equivalent results.

#### Conditional Branches

Inserted for **guard capabilities** — capabilities that evaluate a condition and produce a boolean output controlling downstream execution.

```
Guard Capability Pattern:
- manifest.outputs: { "conditionMet": Boolean }
- Downstream nodes have: manifest.condition: "$.previous.conditionMet == true"

Planning Transformation:
1. Identify guard capabilities (outputs boolean condition)
2. For each dependent node with condition expression:
   - Add CONDITIONAL edge from guard
   - Mark node as CONDITIONAL (not in default execution path)
3. Else-branch: nodes with negated condition
```

#### Optional Capabilities

Marked via **policy**: `optionalOnFailure: true` or capability manifest `optional: true`.

- Failure of optional node → **warning event**, plan continues
- Failure of required node → **plan failure**, triggers rollback

#### Rollback Nodes

**Inserted automatically** for capabilities with `manifest.reversible: false` (irreversible).

| Rollback Strategy | Trigger | Implementation |
|-------------------|---------|----------------|
| **Compensating Action** | `manifest.compensation.capabilityId` | Execute specified compensation capability |
| **State Restoration** | `manifest.compensation.restoreFrom: "snapshot"` | Restore from pre-execution snapshot |
| **Manual Intervention** | `manifest.compensation.manual: true` | Halt, emit `ManualRollbackRequired`, await operator |

**Invariant PLAN-5 (Rollback Completeness):**  
Every irreversible capability in the plan MUST have a rollback node reachable on failure path. If no compensation defined → `PlanningFailed`.

### 8.2.6.7 Binding Resolution

#### Retry Bindings

Each node receives a **RetryPolicy** composed from:

| Source | Priority | Fields |
|--------|----------|--------|
| Capability Manifest | 1 (base) | `maxAttempts`, `backoff`, `retryableErrors[]` |
| Planning Policy | 2 (override) | `globalMaxAttempts`, `globalBackoffMultiplier` |
| Unit Constraints | 3 (tighten) | `maxDuration` → limits total retry time |

**Computed RetryPolicy:** Most restrictive of all applicable sources.

#### Loop Bindings

For capabilities with `manifest.loop: { type: "FOR_EACH" | "WHILE" | "UNTIL", ... }`:

| Loop Type | Planning Expansion |
|-----------|---------------------|
| **FOR_EACH** | Expand into parallel group (if independent) or sequential chain |
| **WHILE** | Insert loop header (condition check) + body subgraph |
| **UNTIL** | Invert condition, same as WHILE |

**Invariant PLAN-6 (Loop Boundedness):**  
All loops MUST have statically verifiable bounds (max iterations from manifest or policy). Unbounded loops → `PlanningFailed`.

#### Provider Requirements

Each capability declares `manifest.provider: { type: "KUBERNETES" | "AWS" | "AZURE" | "GCP" | "LOCAL", ... }`.

Planning resolves:
1. **Capability → Provider Mapping**: Which provider instance satisfies requirements
2. **Provider Capacity**: Validate provider has capacity (quota, regions, versions)
3. **Provider Affinity**: Co-locate capabilities on same provider when beneficial

#### Governance Bindings

For each governance flag from Intent Analysis + Capability Resolution:

| Governance Type | Binding Location | Enforcement |
|-----------------|------------------|-------------|
| **Pre-Execution Approval** | Before node/group | Execution Engine pauses, emits `ApprovalRequired` |
| **Post-Execution Audit** | After node/group | Execution Engine emits `AuditRecord` |
| **Compliance Check** | Before + After | Validate compliance state unchanged |
| **Cost Gate** | Before node/group | Validate cumulative cost ≤ threshold |

#### Resource Budgets

**Aggregate Budget:** Sum of all node `costEstimate.maxUSD`, `resourceRequirements`.

**Per-Node Budget:** `costEstimate` + `contingency` (policy: 10–20%).

**Validation:** `aggregateBudget ≤ globalConstraints.maxTotalCostUSD` AND `perNodeBudget ≤ quota`.

### 8.2.6.8 Optimization Layer

The Optimization Layer applies **policy-gated, deterministic transformations** to the validated plan to improve cost, latency, risk, or resource efficiency. Optimizations are **advisory** — they must be explicitly enabled by policy and verified invariant-preserving.

| Optimization Type | Description | Policy Gate | Validation |
|-------------------|-------------|-------------|------------|
| **Cost Substitution** | Replace capabilities with lower-cost equivalents (from Recommendation Graph) | `planning.optimization.allowCostSubstitution` | Budget invariants, capability contracts preserved |
| **Parallelism Tuning** | Recompute parallel groups for maximal concurrency within resource limits | `planning.optimization.allowParallelismTuning` | PLAN-4 (Parallelism Correctness), budget ≤ quota |
| **Latency Reordering** | Reorder independent nodes to minimize critical path | `planning.optimization.allowLatencyReordering` | Topological validity, data dependencies preserved |
| **Risk Mitigation** | Add fallback nodes, soften SOFT edges, reduce blast radius | `planning.optimization.allowRiskMitigation` | PLAN-5 (Rollback Completeness), governance gates unchanged |
| **Resource Right-Sizing** | Adjust provider requirements based on Execution Profile baselines | `planning.optimization.allowResourceRightSizing` | Provider capacity validated, budget ≤ quota |

**Optimization Process:**
```
1. LOAD Optimization Hints from Planning Memory (§8.2.3.8) for plan signature
2. GENERATE Candidate Optimizations per enabled type
3. SCORE Candidates using Execution Profile (§8.2.7.8) + historical effectiveness
4. SELECT Top candidates within policy budget (max 3 optimizations per plan)
5. APPLY Optimizations producing new Plan'
6. VERIFY Plan' satisfies ALL invariants (PLAN-1 through PLAN-9)
7. IF all pass: Emit PlanOptimized, return Plan'
   ELSE: Discard, return original Plan, log optimization failure
```

**Invariant OPT-1 (Optimization Determinism):**  
Given identical Plan, Execution Profile, Planning Memory, and Policy → Optimization Layer produces identical Plan' (or identical decision to not optimize).

**Invariant OPT-2 (Optimization Safety):**  
An optimization that violates ANY invariant is automatically rejected. No optimization may weaken guarantees.

**Invariant OPT-3 (Optimization Traceability):**  
Every applied optimization MUST be recorded in Plan with: `optimizationId`, `type`, `beforeMetrics`, `predictedAfterMetrics`, `evidenceRef`, `appliedAt`.

### 8.2.6.9 Confidence Propagation in Planning

Planning-stage confidence propagation extends the resolution-phase confidence:

| Stage | Input Confidence | Output Confidence | Decay Factors |
|-------|------------------|-------------------|---------------|
| **Graph Construction** | `resolutionConfidence` (min across units) | `graphConfidence` | -0.02 per substitution edge, -0.05 per cycle-resolution attempt |
| **Dependency Validation** | `graphConfidence` | `depsConfidence` | -0.03 per version conflict resolved, -0.10 per interface adapter injected |
| **Execution Graph** | `depsConfidence` | `execConfidence` | -0.02 per conditional branch, -0.05 per rollback node added |
| **Binding Resolution** | `execConfidence` | `bindConfidence` | -0.01 per retry/loop binding, -0.03 per provider mismatch |
| **Validation** | `bindConfidence` | `validationConfidence` | -0.05 per budget near-limit, -0.10 per governance gate |
| **Optimization** | `validationConfidence` | `planConfidence` | +0.02 per successful optimization (max +0.05), -0.03 per rejected optimization |

**Final Plan Confidence:** `planConfidence = min(validationConfidence, optimizationConfidence)`

**Invariant PLAN-CONF-1 (Planning Confidence Floor):**  
`planConfidence` MUST be ≥ 0.50 for any plan reaching `CAPABILITY_PLAN_READY`. Below threshold → `PLANNING_FAILED` with `LowConfidence` error.

### 8.2.6.10 Success/Failure Criteria

#### Success Criteria (ALL must hold)

| Criterion | Description |
|-----------|-------------|
| **All Required Nodes Complete** | Every non-optional node reaches `COMPLETED` state |
| **Output Contracts Satisfied** | Final outputs match `AnalyzedIntent` output requirements |
| **Governance Gates Passed** | All approval gates granted, audit records created |
| **Budget Not Exceeded** | Actual cost ≤ `aggregateBudget * (1 + contingency)` |
| **Duration Within Budget** | Actual duration ≤ `estimatedDuration * 1.5` |

#### Failure Criteria (ANY triggers failure)

| Criterion | Description |
|-----------|-------------|
| **Required Node Fails** | Non-optional node reaches `FAILED` after retries exhausted |
| **Governance Denied** | Approval gate explicitly denied |
| **Budget Exceeded** | Actual cost > `aggregateBudget * (1 + hardLimit)` |
| **Timeout** | Plan duration > `globalConstraints.maxTotalDuration` |
| **Rollback Fails** | Compensation action fails for irreversible node |
| **Provider Unavailable** | Required provider becomes unhealthy mid-execution |

### 8.2.6.9 Output: CapabilityPlan

```json
{
  "planId": "uuid",
  "version": 1,
  "intentId": "uuid",
  "correlationId": "uuid",
  "createdAt": "ISO8601",
  "createdBy": "CapabilityPlanner/v1.0.0",
  "registrySnapshotId": "uuid",
  "policySnapshotId": "uuid",
  "nodes": [
    {
      "nodeId": "uuid",
      "capabilityId": "deploy.kubernetes.v2",
      "version": "2.3.1",
      "source": "GLOBAL",
      "executionOrder": 1,
      "parallelGroup": 0,
      "dependencies": ["nodeId-1", "nodeId-2"],
      "dependencyTypes": ["HARD", "DATA"],
      "parameters": { "service": "payment", "environment": "STAGING" },
      "condition": null,
      "optional": false,
      "reversible": false,
      "retryPolicy": { "maxAttempts": 3, "backoff": "EXPONENTIAL", "baseDelayMs": 1000 },
      "loopBinding": null,
      "providerRequirement": { "type": "KUBERNETES", "region": "us-east-1", "version": ">=1.28" },
      "governanceBindings": [
        { "type": "PRE_EXECUTION_APPROVAL", "gateId": "gate-1", "requiredApprovers": ["platform-team"] }
      ],
      "resourceBudget": { "cpu": "1000m", "memory": "512Mi", "maxCostUSD": 2.00 },
      "costEstimate": { "minUSD": 0.50, "maxUSD": 2.00, "confidence": 0.85 },
      "riskLevel": "LOW",
      "classification": "INFRASTRUCTURE_DEPLOYMENT",
      "rollbackNode": {
        "nodeId": "uuid-rollback",
        "capabilityId": "rollback.kubernetes.v1",
        "trigger": "ON_FAILURE",
        "strategy": "COMPENSATING_ACTION"
      },
      "successCriteria": ["deploymentUrl PROVIDED", "podsReady >= 3"],
      "failureCriteria": ["deployment FAILED", "timeout > 300s"],
      "confidence": 0.87,
      "confidenceDecayFactors": [
        { "stage": "resolution", "factor": 0.95, "reason": "primary candidate confidence 0.94" },
        { "stage": "dependency", "factor": 1.0, "reason": "no substitutions" }
      ],
      "recommendationRefs": ["rec-deploy-alternative-1", "rec-deploy-test-complement"]
    }
  ],
  "parallelGroups": [
    { "groupId": 0, "nodes": ["nodeId-1"], "estimatedDurationMs": 120000 },
    { "groupId": 1, "nodes": ["nodeId-2", "nodeId-3"], "estimatedDurationMs": 60000 }
  ],
  "conditionalBranches": [
    { "guardNodeId": "nodeId-4", "condition": "$.nodeId-4.output.conditionMet == true",
      "thenNodes": ["nodeId-5"], "elseNodes": ["nodeId-6"] }
  ],
  "governanceGates": [
    { "gateId": "gate-1", "type": "PRE_EXECUTION_APPROVAL", "nodes": ["nodeId-1"],
      "approvers": ["platform-team"], "timeout": 3600, "autoApprove": false }
  ],
  "aggregateBudget": { "maxCostUSD": 20.00, "maxDurationMs": 600000, "contingency": 0.15 },
  "successCriteria": { "allRequiredComplete": true, "outputsMatch": true, ... },
  "failureCriteria": { "anyRequiredFailed": true, "budgetExceeded": true, ... },
  "overallRiskLevel": "MEDIUM",
  "overallConfidence": 0.89,
  "confidenceDecayTrace": {
    "intentConfidence": 0.92,
    "resolutionConfidence": 0.87,
    "dependencyConfidence": 0.87,
    "assemblyConfidence": 0.85,
    "optimizationConfidence": 0.89,
    "finalConfidence": 0.89
  },
  "optimizationMetadata": {
    "optimized": true,
    "optimizationPasses": 1,
    "beforeMetrics": { "costUSD": 22.50, "durationMs": 650000, "riskScore": 0.62 },
    "afterMetrics": { "costUSD": 20.00, "durationMs": 600000, "riskScore": 0.55 },
    "appliedOptimizations": [
      { "type": "COST_SUBSTITUTION", "node": "nodeId-3", "deltaCostUSD": -2.50 }
    ],
    "optimizationTimestamp": "ISO8601"
  },
  "recommendationGraph": "ref://recommendationGraph-correlationId",
  "traceability": { ... }
}
```

### 8.2.6.10 Invariants

| Invariant | Description |
|-----------|-------------|
| **PLAN-1 (Acyclicity)** | Capability Graph is a DAG |
| **PLAN-2 (Dependency Completeness)** | All declared dependencies resolve |
| **PLAN-3 (Deterministic Ordering)** | Topological sort is deterministic |
| **PLAN-4 (Parallelism Correctness)** | Parallel groups are mutually independent |
| **PLAN-5 (Rollback Completeness)** | Every irreversible node has rollback |
| **PLAN-6 (Loop Boundedness)** | All loops have static max iterations |
| **PLAN-7 (Budget Validity)** | Aggregate budget ≤ quotas |
| **PLAN-8 (Governance Satisfiability)** | All governance gates have valid approvers |
| **PLAN-9 (Traceability Completeness)** | Every plan element traces to intent unit |

### 8.2.6.11 Conformance Requirements

| Requirement ID | Description | Test Criteria |
|----------------|-------------|---------------|
| **CONF-DISC-1** | Pipeline determinism | Same inputs → bit-identical plan |
| **CONF-DISC-2** | Resolution order | Project > Global > External enforced |
| **CONF-DISC-3** | Snapshot isolation | No stage sees different registry state |
| **CONF-DISC-4** | Confidence scoring | All decisions have confidence 0.0–1.0 |
| **CONF-DISC-5** | Policy validation | All policies evaluated, decisions recorded |
| **CONF-DISC-6** | Governance detection | All triggers identified, gates inserted |
| **CONF-DISC-7** | Plan validity | All invariants PLAN-1 through PLAN-9 hold |
| **CONF-DISC-8** | Event emission | All specified events emitted at correct stages |
| **CONF-DISC-9** | Traceability | Full intent→plan traceability matrix complete |

### 8.2.6.12 Events Emitted

| Event | Trigger | Payload |
|-------|---------|---------|
| `CapabilityPlanningStarted` | Stage entry | `intentId`, `resolvedUnitCount` |
| `CapabilityGraphBuilt` | After Stage 1 | `nodeCount`, `edgeCount`, `isDAG` |
| `DependencyGraphValidated` | After Stage 2 | `validationResult`, `substitutions[]` |
| `ExecutionGraphConstructed` | After Stage 3 | `parallelGroups`, `conditionalBranches`, `rollbackNodes` |
| `BindingsResolved` | After Stage 4 | `retryBindings`, `loopBindings`, `providerBindings`, `governanceBindings` |
| `PlanValidated` | After Stage 5 | `validationResult`, `budgetValidation` |
| `PlanOptimized` | After Stage 6 | `planId`, `optimizations[]`, `beforeMetrics`, `afterMetrics` |
| `CapabilityPlanAssembled` | Success | `CapabilityPlan` |
| `CapabilityPlanningFailed` | Any failure | `intentId`, `stage`, `error`, `partialPlan?` |

### 8.2.6.13 Traceability Matrix (Plan Level)

| Plan Element | Traces To | Relationship |
|--------------|-----------|--------------|
| `CapabilityPlan.planId` | `AnalyzedIntent.intentId` | `REALIZES` |
| `Plan.nodes[]` | `ResolvedUnit.unitId` | `BINDS` |
| `Plan.nodes[].parameters` | `IntentUnit.canonicalParameters` | `INSTANTIATES` |
| `Plan.parallelGroups[]` | `DependencyGraph.antichains` | `DERIVES_FROM` |
| `Plan.rollbackNodes[]` | `CapabilityManifest.reversible=false` | `COMPENSATES` |
| `Plan.governanceGates[]` | `AnalyzedIntent.governance` + `ResolvedUnit.governanceFlags` | `ENFORCES` |
| `Plan.resourceBudget` | `AnalyzedIntent.globalConstraints` + `ResolvedUnit.costEstimate` | `AGGREGATES` |
| `Plan.optimizations[]` | `PlanningMemory.optimizationMemo[]` + `ExecutionProfile.baselines[]` | `INFORMED_BY` |
| `Plan.confidence` | `AnalyzedIntent.overallConfidence` + all decay factors | `DERIVES_FROM` |

### 8.2.6.14 State Transitions (Planning Phase)

```
PLANNING_IDLE
    │
    ├─▶ INTENT_ANALYSIS
    │       │
    │       ├─▶ INTENT_ANALYSIS_COMPLETE ──▶ CAPABILITY_RESOLUTION
    │       │                                     │
    │       └─▶ INTENT_ANALYSIS_FAILED ◀──────────┘ (halt)
    │
    ├─▶ CAPABILITY_RESOLUTION
    │       │
    │       ├─▶ CAPABILITY_RESOLUTION_COMPLETE ──▶ DEPENDENCY_RESOLUTION
    │       │                                           │
    │       └─▶ CAPABILITY_RESOLUTION_FAILED ◀──────────┘ (halt)
    │
    ├─▶ DEPENDENCY_RESOLUTION
    │       │
    │       ├─▶ DEPENDENCY_RESOLUTION_COMPLETE ──▶ PLAN_ASSEMBLY
    │       │                                             │
    │       └─▶ DEPENDENCY_RESOLUTION_FAILED ◀────────────┘ (halt)
    │
    ├─▶ PLAN_ASSEMBLY
    │       │
    │       ├─▶ PLAN_ASSEMBLY_COMPLETE ──▶ PLAN_VALIDATION
    │       │                                    │
    │       └─▶ PLAN_ASSEMBLY_FAILED ◀────────────┘ (halt)
    │
    ├─▶ PLAN_VALIDATION
    │       │
    │       ├─▶ PLAN_VALIDATION_PASS ──▶ PLAN_OPTIMIZATION
    │       │                                    │
    │       └─▶ PLAN_VALIDATION_FAIL ◀───────────┘ (halt)
    │
    └─▶ PLAN_OPTIMIZATION
            │
            ├─▶ PLAN_OPTIMIZATION_COMPLETE ──▶ CAPABILITY_PLAN_READY
            │
            └─▶ PLAN_OPTIMIZATION_FAILED ──▶ CAPABILITY_PLAN_READY (unoptimized)
```

**Terminal States:** `CAPABILITY_PLAN_READY` (success), `PLANNING_FAILED` (failure)

---

## 8.2.7 Artifact Generation

### 8.2.7.1 Purpose

Artifact Generation produces the **immutable, versioned, auditable output artifacts** of the Capability Discovery & Planning subsystem. These artifacts are the contract between planning and execution, and between the system and governance/audit processes. Every artifact MUST be deterministic, reproducible, and traceable to its source inputs.

### 8.2.7.2 Artifact Requirements

| Requirement | Description |
|-------------|-------------|
| **Deterministic** | Identical inputs (Intent + Registry Snapshot + Policy Snapshot + Config Snapshot) → bit-identical artifacts |
| **Reproducible** | Any authorized party can regenerate artifacts from source inputs and obtain identical results |
| **Auditable** | Complete provenance chain: artifact → plan → resolved capabilities → analyzed intent → raw intent |
| **Versioned** | Every artifact carries schema version, generator version, and content hash |
| **Immutable** | Once generated, artifacts are write-once; modifications create new artifact versions |
| **Signed** | Artifacts MAY be cryptographically signed by the Planning Component identity |

### 8.2.7.3 Generated Artifacts

| Artifact | Schema Reference | Purpose | Consumers |
|----------|------------------|---------|-----------|
| **Claude.md** | §8.2.7.4 | Human-readable planning summary for operator review | Operators, Auditors, AI Assistants |
| **Project Hooks** | §8.2.7.5 | Executable lifecycle hooks for pre/post execution | Execution Engine, CI/CD |
| **Execution Metadata** | §8.2.7.6 | Runtime hints for scheduler, resource manager | Execution Engine, Scheduler |
| **Capability Manifest** | §8.2.7.7 | Resolved capability manifests with pinned versions | Execution Engine, Registry |
| **Execution Profile** | §8.2.7.8 | Performance baselines, SLOs, tuning parameters | Execution Engine, Observability |
| **Governance Manifest** | §8.2.7.9 | Approval gates, compliance evidence, audit trail | Governance, Compliance, Auditors |

### 8.2.7.4 Claude.md

**Purpose:** Human-readable markdown summary of the plan for operator review, debugging, and AI-assisted analysis.

**Schema:**
```markdown
# Capability Plan: <planId>
**Generated:** <ISO8601>  
**Generator:** CapabilityPlanner/v1.0.0  
**Intent:** <intentId> — <rawIntent summary>  
**Risk Level:** <LOW|MEDIUM|HIGH|CRITICAL>  
**Confidence:** <0.0–1.0>  

## Intent Analysis
- Units: <N>
- Global Constraints: <summary>
- Risks: <risk summary>
- Governance: <governance summary>

## Resolved Capabilities
| # | Capability ID | Version | Source | Confidence | Risk | Cost Est. |
|---|---------------|---------|--------|------------|------|-----------|
| 1 | deploy.kubernetes.v2 | 2.3.1 | GLOBAL | 0.94 | LOW | $0.50–2.00 |

## Execution Plan
- Nodes: <N>
- Parallel Groups: <N>
- Estimated Duration: <ms>
- Estimated Cost: <USD>

## Optimization Summary (if optimized)
- Optimized: <true/false>
- Optimization Passes: <N>
- Cost Delta: <+/- USD>
- Duration Delta: <+/- ms>
- Risk Delta: <+/- score>

## Confidence Trace
| Stage | Input Confidence | Output Confidence | Decay Factors |
|-------|------------------|-------------------|---------------|
| Intent | 0.92 | 0.92 | — |
| Resolution | 0.92 | 0.87 | primary:0.95 |
| Dependency | 0.87 | 0.87 | — |
| Assembly | 0.87 | 0.85 | governance:-0.02 |
| Optimization | 0.85 | 0.89 | +0.04 (cost substitution) |

## Recommendation Graph
- Alternatives: <N>
- Complements: <N>
- Conflicts: <N>
- Top Recommendation: <capabilityId> — <reason>

## Governance Gates
| Gate | Type | Nodes | Approvers | Status |
|------|------|-------|-----------|--------|
| gate-1 | PRE_EXECUTION_APPROVAL | deploy | platform-team | PENDING |

## AI Council Deliberation (if invoked)
- Council ID: <councilId>
- Models: <model list>
- Verdict: <ALLOW|DENY|HUMAN_ESCALATION>
- Transcript: <ref>

## Loop Engine Status
- Max Iterations: <N>
- Current Iteration: <N>
- Retry Budget: <ms>

## Self-Healing Indicators
- Checkpoint Recovery: <true/false>
- Adaptive Substitution: <true/false>
- Fallback Available: <true/false>

## Traceability
- Registry Snapshot: <snapshotId>
- Policy Snapshot: <snapshotId>
- Content Hash: <SHA256>
```

**Invariant ARTIFACT-1 (Claude.md Completeness):**  
Claude.md MUST contain sufficient information for a human operator to understand the plan's purpose, risks, costs, and approval requirements without reading machine-readable artifacts.

### 8.2.7.5 Project Hooks

**Purpose:** Executable scripts/hooks for lifecycle integration (pre-flight checks, post-execution cleanup, notifications).

**Schema:**
```json
{
  "hookVersion": 1,
  "planId": "uuid",
  "hooks": {
    "preExecution": [
      { "name": "validate-quotas", "command": "quota-check --plan ${PLAN_ID}", "timeout": 30, "onFailure": "ABORT" },
      { "name": "notify-stakeholders", "command": "slack-notify --channel deployments --plan ${PLAN_ID}", "timeout": 10, "onFailure": "WARN" }
    ],
    "postExecution": [
      { "name": "record-metrics", "command": "metrics-record --plan ${PLAN_ID} --result ${RESULT}", "timeout": 30, "onFailure": "WARN" },
      { "name": "cleanup-temp", "command": "cleanup --plan ${PLAN_ID}", "timeout": 60, "onFailure": "WARN" }
    ],
    "onRollback": [
      { "name": "execute-compensation", "command": "rollback --plan ${PLAN_ID} --node ${FAILED_NODE}", "timeout": 300, "onFailure": "ALERT" }
    ]
  },
  "environment": { "PLAN_ID": "${planId}", "CORRELATION_ID": "${correlationId}" }
}
```

**Invariant ARTIFACT-2 (Hook Determinism):**  
Hook commands MUST be fully parameterized via environment variables derived from the plan. No external state may influence hook behavior.

### 8.2.7.6 Execution Metadata

**Purpose:** Runtime hints for the Execution Engine, Scheduler, and Resource Manager.

**Schema:**
```json
{
  "metadataVersion": 1,
  "planId": "uuid",
  "scheduling": {
    "priority": "NORMAL",
    "preemptionAllowed": false,
    "affinity": { "provider": "KUBERNETES", "region": "us-east-1" },
    "tolerations": ["dedicated-node"]
  },
  "resources": {
    "perNode": { "nodeId-1": { "cpu": "1000m", "memory": "512Mi", "gpu": 0 } },
    "aggregate": { "cpu": "2000m", "memory": "1Gi", "maxCostUSD": 20.00 }
  },
  "performance": {
    "estimatedDurationMs": 180000,
    "parallelism": 2,
    "bottleneckNodes": ["nodeId-1"],
    "sloTargets": { "p99LatencyMs": 300000, "successRate": 0.99 }
  },
  "reliability": {
    "maxRetries": 3,
    "circuitBreakerThreshold": 5,
    "timeoutMs": 600000
  }
}
```

**Invariant ARTIFACT-3 (Metadata Fidelity):**  
Execution Metadata MUST accurately reflect the plan's resource budgets, parallelism, and timing estimates. Deviations >10% at runtime MUST trigger observability alerts.

### 8.2.7.7 Capability Manifest

**Purpose:** Pinned, resolved capability manifests for each plan node — the exact versions and configurations to execute.

**Schema:**
```json
{
  "manifestVersion": 1,
  "planId": "uuid",
  "capabilities": [
    {
      "nodeId": "uuid",
      "capabilityId": "deploy.kubernetes.v2",
      "version": "2.3.1",
      "source": "GLOBAL",
      "pinnedManifest": { ... },  // Full manifest snapshot from registry
      "resolvedParameters": { "service": "payment", "environment": "STAGING" },
      "dependencyOverrides": [],
      "substituted": false
    }
  ],
  "contentHash": "sha256:...",
  "registrySnapshotId": "uuid"
}
```

**Invariant ARTIFACT-4 (Manifest Pinning):**  
Every capability in the plan MUST reference a fully pinned manifest (exact version, exact content hash). No version ranges or "latest" references permitted in generated artifacts.

### 8.2.7.8 Execution Profile

**Purpose:** Performance baselines, SLOs, and tuning parameters derived from historical executions and capability manifests.

**Schema:**
```json
{
  "profileVersion": 1,
  "planId": "uuid",
  "baselines": [
    { "nodeId": "uuid", "capabilityId": "deploy.kubernetes.v2", "p50Ms": 45000, "p95Ms": 120000, "p99Ms": 180000, "sampleCount": 147 }
  ],
  "slo": {
    "planDurationP99Ms": 300000,
    "nodeSuccessRate": 0.995,
    "costPerExecutionUSD": { "p50": 1.20, "p95": 3.50 }
  },
  "tuning": {
    "nodeId-1": { "recommendedParallelism": 1, "resourceScaleFactor": 1.0 },
    "nodeId-2": { "recommendedParallelism": 2, "resourceScaleFactor": 0.8 }
  },
  "dataSource": "historical-executions-30d"
}
```

**Invariant ARTIFACT-5 (Profile Freshness):**  
Execution Profiles MUST be generated from execution data no older than the configured `profileMaxAge` (default: 30 days). Stale profiles MUST be marked `stale: true` and Execution Engine SHOULD apply conservative defaults.

### 8.2.7.9 Governance Manifest

**Purpose:** Complete governance evidence package for audit, compliance, and approval workflows.

**Schema:**
```json
{
  "governanceVersion": 1,
  "planId": "uuid",
  "approvalGates": [
    {
      "gateId": "gate-1",
      "type": "PRE_EXECUTION_APPROVAL",
      "trigger": "ENVIRONMENT_STAGING",
      "requiredApprovers": ["platform-team"],
      "policyRef": "GOV-DEPLOY-STAGING-v3",
      "evidence": {
        "intentSummary": "Deploy payment service to staging",
        "riskAssessment": "MEDIUM — staging deployment",
        "costEstimate": "$0.50–2.00",
        "complianceTags": ["SOC2"],
        "rollbackPlan": "Compensating action: rollback.kubernetes.v1"
      },
      "status": "PENDING",
      "requestedAt": "ISO8601",
      "expiresAt": "ISO8601"
    }
  ],
  "complianceEvidence": {
    "applicablePolicies": ["GOV-DEPLOY-STAGING-v3", "FINOPS-COST-TIER-1-v2"],
    "policyEvaluations": [
      { "policy": "GOV-DEPLOY-STAGING-v3", "decision": "REQUIRE_APPROVAL", "evaluatedAt": "ISO8601" }
    ],
    "dataHandling": { "pii": false, "egress": false, "encryption": "AES-256" },
    "auditTrail": [
      { "event": "INTENT_RECEIVED", "timestamp": "ISO8601", "actor": "user:jdoe" },
      { "event": "PLAN_GENERATED", "timestamp": "ISO8601", "actor": "CapabilityPlanner/v1.0.0" }
    ]
  },
  "contentHash": "sha256:...",
  "signedBy": "planning-component-key-v1"
}
```

**Invariant ARTIFACT-6 (Governance Completeness):**  
Governance Manifest MUST contain every governance trigger identified during Intent Analysis (§8.2.4.6) and Capability Resolution (§8.2.5.8), with policy evaluations and evidence sufficient for an auditor to independently verify the decision.

### 8.2.7.10 Artifact Generation Process

```
Artifact Generation Pipeline (deterministic, single-pass):

Input: CapabilityPlan + RegistrySnapshot + PolicySnapshot + HistoricalMetrics

┌─────────────────────────────────────────────────────────────────┐
│ 1. COLLECT INPUTS                                               │
│    - Plan, snapshots, metrics                                   │
│    - Validate all inputs present                                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. GENERATE ARTIFACTS (parallel, pure functions)               │
│    ├── Claude.md ← Plan + IntentAnalysis                       │
│    ├── Project Hooks ← Plan + Policy                           │
│    ├── Execution Metadata ← Plan + ResourceQuotas              │
│    ├── Capability Manifest ← Plan + RegistrySnapshot           │
│    ├── Execution Profile ← Plan + HistoricalMetrics            │
│    └── Governance Manifest ← Plan + PolicySnapshot + AuditLog  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. VERSION & HASH                                               │
│    - Assign artifact version = Plan.version                     │
│    - Compute SHA256(content) for each artifact                  │
│    - Record generator version (CapabilityPlanner/x.y.z)         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. OPTIONAL SIGNING                                             │
│    - Sign each artifact with Planning Component key             │
│    - Record key ID and signature in artifact envelope           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. EMIT ARTIFACT GENERATED EVENTS                               │
│    - One event per artifact type                                │
│    - Include content hash for verification                      │
└─────────────────────────────────────────────────────────────────┘
```

**Invariant ARTIFACT-7 (Generation Atomicity):**  
Artifact Generation MUST succeed completely or fail completely. Partial artifact sets MUST NOT be persisted. On failure, emit `ArtifactGenerationFailed` with reason.

**Invariant ARTIFACT-8 (Reproducibility):**  
Given identical `CapabilityPlan`, `RegistrySnapshot`, `PolicySnapshot`, `HistoricalMetricsSnapshot` → artifact generation MUST produce bit-identical outputs.

### 8.2.7.11 Events Emitted

| Event | Trigger | Payload |
|-------|---------|---------|
| `ArtifactGenerationStarted` | Pipeline entry | `planId`, `artifactTypes[]` |
| `ClaudeMdGenerated` | Success | `planId`, `contentHash`, `sizeBytes` |
| `ProjectHooksGenerated` | Success | `planId`, `contentHash`, `hookCount` |
| `ExecutionMetadataGenerated` | Success | `planId`, `contentHash`, `sizeBytes` |
| `CapabilityManifestGenerated` | Success | `planId`, `contentHash`, `capabilityCount` |
| `ExecutionProfileGenerated` | Success | `planId`, `contentHash`, `baselineCount` |
| `GovernanceManifestGenerated` | Success | `planId`, `contentHash`, `gateCount`, `signed` |
| `ArtifactGenerationCompleted` | All artifacts | `planId`, `artifacts[]` |
| `ArtifactGenerationFailed` | Any failure | `planId`, `error`, `partialArtifacts?` |

---

## 8.2.8 Event Architecture

### 8.2.8.1 Event Model

All planning events conform to the **Part 2 Event System** with the following conventions:

| Field | Requirement |
|-------|-------------|
| **eventId** | UUIDv7 (time-ordered) |
| **eventType** | Namespaced: `aios.planning.*` |
| **correlationId** | Links all events for a single intent→plan flow |
| **causationId** | Links to the event that caused this event |
| **timestamp** | ISO8601 with nanosecond precision |
| **source** | Component identifier: `CapabilityDiscovery`, `CapabilityPlanner`, `ArtifactGenerator` |
| **version** | Event schema version (semver) |

### 8.2.8.2 Event Categories

| Category | Prefix | Description | Ordering |
|----------|--------|-------------|----------|
| **Intent Lifecycle** | `aios.planning.intent.*` | Intent reception through analysis | Total order per correlationId |
| **Discovery** | `aios.planning.discovery.*` | Capability resolution events | Total order per correlationId |
| **Planning** | `aios.planning.plan.*` | Graph construction through validation | Total order per correlationId |
| **Governance** | `aios.planning.governance.*` | Approval gates, compliance | Total order per correlationId |
| **Artifacts** | `aios.planning.artifact.*` | Artifact generation events | Total order per correlationId |
| **Control** | `aios.planning.control.*` | Timeout, cancellation, retry | Partial order (interleaved) |
| **Cache** | `aios.planning.cache.*` | Discovery cache hit/miss, invalidation | Partial order |
| **Memory** | `aios.planning.memory.*` | Planning memory read/write | Partial order |
| **Model Routing** | `aios.planning.model.*` | Model router requests/responses | Total order per correlationId |
| **AI Council** | `aios.planning.council.*` | Council deliberation/voting | Total order per councilId |
| **Optimization** | `aios.planning.optimization.*` | Optimization layer decisions | Total order per correlationId |
| **Self-Healing** | `aios.planning.healing.*` | Self-healing triggers/actions | Total order per correlationId |
| **Confidence** | `aios.planning.confidence.*` | Confidence propagation updates | Total order per correlationId |
| **Recommendation** | `aios.planning.recommendation.*` | Recommendation graph updates | Partial order |

### 8.2.8.3 Event Specifications

#### Intent Lifecycle Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.intent.received` | API Gateway / Agent | CapabilityDiscovery | `intentId`, `rawIntent`, `intentType`, `context` |
| `aios.planning.intent.analyzed` | CapabilityDiscovery | CapabilityPlanner, AuditLog | `intentId`, `AnalyzedIntent`, `confidence` |
| `aios.planning.intent.analysis_failed` | CapabilityDiscovery | Agent, Alerting | `intentId`, `error`, `stage`, `partialAnalysis?` |

#### Discovery Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.discovery.started` | CapabilityDiscovery | CapabilityPlanner, Metrics | `intentId`, `unitCount` |
| `aios.planning.discovery.capability_resolved` | CapabilityDiscovery | CapabilityPlanner, AuditLog | `intentId`, `unitId`, `ResolvedUnit` |
| `aios.planning.discovery.capability_substituted` | CapabilityDiscovery | AuditLog | `intentId`, `unitId`, `original`, `substitute`, `ruleId` |
| `aios.planning.discovery.capability_validated` | CapabilityDiscovery | CapabilityPlanner | `intentId`, `unitId`, `validationResult` |
| `aios.planning.discovery.policy_denied` | CapabilityDiscovery | AuditLog, Alerting | `intentId`, `unitId`, `capabilityId`, `policyRule` |
| `aios.planning.discovery.approval_required` | CapabilityDiscovery | Governance, Agent | `intentId`, `unitId`, `capabilityId`, `approvalType` |
| `aios.planning.discovery.completed` | CapabilityDiscovery | CapabilityPlanner | `intentId`, `ResolvedCapabilities[]` |
| `aios.planning.discovery.failed` | CapabilityDiscovery | Agent, Alerting | `intentId`, `unitId`, `reason`, `candidatesTried` |

#### Planning Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.plan.started` | CapabilityPlanner | Metrics, AuditLog | `intentId`, `resolvedUnitCount` |
| `aios.planning.plan.graph_built` | CapabilityPlanner | AuditLog | `intentId`, `nodeCount`, `edgeCount`, `isDAG` |
| `aios.planning.plan.dependencies_validated` | CapabilityPlanner | AuditLog | `intentId`, `validationResult`, `substitutions[]` |
| `aios.planning.plan.execution_graph_constructed` | CapabilityPlanner | ExecutionEngine (pre-fetch) | `intentId`, `parallelGroups`, `conditionalBranches`, `rollbackNodes` |
| `aios.planning.plan.bindings_resolved` | CapabilityPlanner | ExecutionEngine (pre-fetch) | `intentId`, `retryBindings`, `loopBindings`, `providerBindings`, `governanceBindings` |
| `aios.planning.plan.validated` | CapabilityPlanner | ExecutionEngine, AuditLog | `intentId`, `validationResult`, `budgetValidation` |
| `aios.planning.plan.generated` | CapabilityPlanner | ExecutionEngine, ArtifactGenerator, AuditLog | `CapabilityPlan` |
| `aios.planning.plan.approved` | Governance | ExecutionEngine, Agent | `planId`, `gateId`, `approver`, `timestamp` |
| `aios.planning.plan.rejected` | Governance | Agent, Alerting, AuditLog | `planId`, `gateId`, `rejector`, `reason`, `timestamp` |
| `aios.planning.plan.failed` | CapabilityPlanner | Agent, Alerting | `intentId`, `stage`, `error`, `partialPlan?` |

#### Artifact Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.artifact.generated` | ArtifactGenerator | ExecutionEngine, Registry, AuditLog | `planId`, `artifactType`, `contentHash`, `sizeBytes`, `signed` |
| `aios.planning.artifact.generation_failed` | ArtifactGenerator | Agent, Alerting | `planId`, `artifactType`, `error` |
| `aios.planning.artifact.verification_failed` | ExecutionEngine/Registry | Alerting, AuditLog | `planId`, `artifactType`, `expectedHash`, `actualHash` |

#### Control Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.control.timeout` | Scheduler/Planner | CapabilityDiscovery, CapabilityPlanner, Agent | `correlationId`, `stage`, `timeoutMs` |
| `aios.planning.control.cancelled` | Agent/Operator | CapabilityDiscovery, CapabilityPlanner, ArtifactGenerator | `correlationId`, `reason`, `initiator` |
| `aios.planning.control.retry` | CapabilityDiscovery/Planner | Self (re-entry) | `correlationId`, `stage`, `attempt`, `maxAttempts` |
| `aios.planning.control.recovery` | Recovery Manager | CapabilityDiscovery, CapabilityPlanner | `correlationId`, `fromStage`, `recoveryPoint` |

### 8.2.8.4 Correlation & Traceability

```
Single Intent → Plan Flow (correlationId = intentId):

Intent Received
    │
    ├─▶ Intent Analyzed (causationId = intentReceived)
    │       │
    │       ├─▶ Discovery Started (causationId = intentAnalyzed)
    │       │       │
    │       │       ├─▶ Capability Resolved (xN) ← causationId = discoveryStarted
    │       │       ├─▶ Capability Validated (xN)
    │       │       └─▶ Discovery Completed (causationId = lastResolved)
    │       │
    │       ├─▶ Plan Started (causationId = discoveryCompleted)
    │       │       │
    │       │       ├─▶ Graph Built (causationId = planStarted)
    │       │       ├─▶ Dependencies Validated (causationId = graphBuilt)
    │       │       ├─▶ Execution Graph Constructed (causationId = depsValidated)
    │       │       ├─▶ Bindings Resolved (causationId = execGraphConstructed)
    │       │       ├─▶ Plan Validated (causationId = bindingsResolved)
    │       │       └─▶ Plan Generated (causationId = planValidated)
    │       │
    │       ├─▶ Artifact Generation Started (causationId = planGenerated)
    │       │       │
    │       │       ├─▶ Artifact Generated (x6 types) ← causationId = artifactStarted
    │       │       └─▶ Artifact Generation Completed (causationId = lastArtifact)
    │       │
    │       └─▶ Governance Review (async, causationId = planGenerated)
    │               │
    │               ├─▶ Plan Approved / Rejected (causationId = governanceReview)
    │               │
    │               └─▶ Plan Ready for Execution
    │
    └─▶ (Control events interleave at any point)
```

**Invariant EVENT-1 (Correlation Completeness):**  
Every event in a planning flow MUST carry the same `correlationId`. No event MAY be emitted without a `correlationId`.

**Invariant EVENT-2 (Causation Chain):**  
Every event (except `intent.received`) MUST carry a `causationId` referencing the event that directly triggered it. The causation chain MUST be acyclic and traceable to `intent.received`.

### 8.2.8.5 Extended Event Specifications

#### Cache Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.cache.hit` | DiscoveryCache | CapabilityDiscovery, Metrics | `cacheKey`, `cachedValue`, `ttlRemainingMs`, `hitCount` |
| `aios.planning.cache.miss` | DiscoveryCache | CapabilityDiscovery, Metrics | `cacheKey`, `fallbackSource`, `latencyMs` |
| `aios.planning.cache.invalidated` | DiscoveryCache | CapabilityDiscovery, AuditLog | `cacheKey`, `reason`, `invalidatedBy` |
| `aios.planning.cache.invalidated_by_change` | RegistryWatcher | DiscoveryCache, AuditLog | `capabilityId`, `changeType`, `oldVersion`, `newVersion` |
| `aios.planning.cache.warmed` | DiscoveryCache | Metrics | `cacheKey`, `warmedCount`, `latencyMs` |
| `aios.planning.cache.evicted` | DiscoveryCache | Metrics, AuditLog | `cacheKey`, `reason`, `evictionPolicy` |

#### Memory Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.memory.read` | PlanningMemory | CapabilityDiscovery, CapabilityPlanner | `memoryKey`, `entryCount`, `hitCount`, `latencyMs` |
| `aios.planning.memory.write` | PlanningMemory | AuditLog, Metrics | `memoryKey`, `entryCount`, `writeTimestamp`, `ttl` |
| `aios.planning.memory.invalidated` | PlanningMemory | CapabilityDiscovery, CapabilityPlanner | `memoryKey`, `reason`, `invalidatedBy` |
| `aios.planning.memory.compacted` | PlanningMemory | Metrics | `entriesRemoved`, `bytesFreed`, `durationMs` |
| `aios.planning.memory.replay_requested` | CapabilityPlanner | PlanningMemory, Metrics | `correlationId`, `planId`, `replayTimestamp` |
| `aios.planning.memory.replay_completed` | PlanningMemory | CapabilityPlanner, Metrics, AuditLog | `correlationId`, `replayPlanId`, `divergence`, `deterministic` |

#### Model Routing Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.model.routed` | ModelRouter | CapabilityDiscovery, CapabilityPlanner, Metrics | `requestId`, `modelId`, `capabilityId`, `tier`, `latencyMs`, `costEstimate` |
| `aios.planning.model.fallback` | ModelRouter | CapabilityDiscovery, CapabilityPlanner, Alerting | `requestId`, `primaryModel`, `fallbackModel`, `reason`, `latencyMs` |
| `aios.planning.model.timeout` | ModelRouter | CapabilityDiscovery, CapabilityPlanner, Alerting | `requestId`, `modelId`, `timeoutMs`, `retryCount` |
| `aios.planning.model.routed_to_fallback` | ModelRouter | Metrics, Alerting | `requestId`, `modelId`, `fallbackModelId`, `reason`, `attempt` |

#### AI Council Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.council.convened` | AICouncil | AuditLog, Metrics, Agent | `councilId`, `intentId`, `members[]`, `quorum`, `subscriptionTier` |
| `aios.planning.council.deliberation_started` | AICouncil | Metrics, Agent | `councilId`, `topic`, `candidates[]`, `votingMethod` |
| `aios.planning.council.vote_cast` | AICouncil | AuditLog, Metrics | `councilId`, `memberId`, `vote`, `rationale`, `weight` |
| `aios.planning.council.consensus_reached` | AICouncil | CapabilityPlanner, Agent, AuditLog | `councilId`, `decision`, `votes`, `confidence`, `timeoutMs` |
| `aios.planning.council.deadlock` | AICouncil | Agent, Alerting, AuditLog | `councilId`, `topic`, `votes`, `deadlockReason`, `resolution` |
| `aios.planning.council.timeout` | AICouncil | CapabilityPlanner, Agent, Alerting | `councilId`, `topic`, `elapsedMs`, `fallbackDecision` |
| `aios.planning.council.escalated` | AICouncil | HumanGovernance, Agent, Alerting | `councilId`, `topic`, `escalationTier`, `reason` |

#### Optimization Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.optimization.started` | OptimizerLayer | CapabilityPlanner, Metrics | `planId`, `optimizationTier`, `objectives[]` |
| `aios.planning.optimization.candidate_generated` | OptimizerLayer | Metrics, AuditLog | `planId`, `candidateId`, `strategy`, `delta` |
| `aios.planning.optimization.candidate_scored` | OptimizerLayer | Metrics, AuditLog | `planId`, `candidateId`, `scores{}`, `rank` |
| `aios.planning.optimization.applied` | OptimizerLayer | CapabilityPlanner, ArtifactGenerator, AuditLog | `planId`, `candidateId`, `optimizationSummary`, `confidenceDelta` |
| `aios.planning.optimization.rejected` | OptimizerLayer | AuditLog, Metrics | `planId`, `candidateId`, `reason`, `confidenceThreshold` |
| `aios.planning.optimization.cost_analysis` | OptimizerLayer | Metrics, CostTracking | `planId`, `baselineCost`, `optimizedCost`, `savings`, `breakdown` |
| `aios.planning.optimization.latency_analysis` | OptimizerLayer | Metrics, ExecutionEngine | `planId`, `baselineLatency`, `optimizedLatency`, `criticalPathDelta` |

#### Self-Healing Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.healing.triggered` | SelfHealingPlanner | CapabilityPlanner, Metrics, Alerting | `correlationId`, `failureClass`, `failureContext`, `healingStrategy` |
| `aios.planning.healing.alternative_generated` | SelfHealingPlanner | CapabilityPlanner, Metrics | `correlationId`, `alternativePlanId`, `strategy`, `confidence` |
| `aios.planning.healing.validated` | SelfHealingPlanner | CapabilityPlanner, ExecutionEngine | `correlationId`, `alternativePlanId`, `validationResult`, `simulatedOutcome` |
| `aios.planning.healing.applied` | SelfHealingPlanner | CapabilityPlanner, ExecutionEngine, AuditLog | `correlationId`, `alternativePlanId`, `appliedAt`, `confidence` |
| `aios.planning.healing.failed` | SelfHealingPlanner | CapabilityPlanner, Alerting, AuditLog | `correlationId`, `failureClass`, `strategiesAttempted[]`, `escalationTier` |
| `aios.planning.healing.escalated` | SelfHealingPlanner | HumanGovernance, Alerting, AuditLog | `correlationId`, `escalationTier`, `context`, `fallbackDecision` |

#### Confidence Propagation Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.confidence.propagated` | ConfidencePropagator | CapabilityDiscovery, CapabilityPlanner, AuditLog | `correlationId`, `nodeId`, `inputConfidence`, `outputConfidence`, `propagationRule` |
| `aios.planning.confidence.threshold_breach` | ConfidencePropagator | AI Council, SelfHealingPlanner, Alerting | `correlationId`, `nodeId`, `confidence`, `threshold`, `action` |
| `aios.planning.confidence.recalculated` | ConfidencePropagator | CapabilityPlanner, AuditLog | `correlationId`, `planId`, `oldConfidence`, `newConfidence`, `delta`, `trigger` |

#### Recommendation Graph Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.recommendation.generated` | RecommendationBuilder | CapabilityPlanner, CapabilityDiscovery, Agent | `correlationId`, `recommendationGraph`, `nodeCount`, `edgeCount` |
| `aios.planning.recommendation.updated` | RecommendationBuilder | CapabilityPlanner, CapabilityDiscovery | `correlationId`, `recommendationGraph`, `delta` |
| `aios.planning.recommendation.pruned` | RecommendationBuilder | Metrics, AuditLog | `correlationId`, `prunedNodeCount`, `reason`, `confidenceThreshold` |

#### Loop Engine Events

| Event | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `aios.planning.loop.expansion_started` | LoopEngine | CapabilityPlanner, Metrics | `correlationId`, `loopId`, `loopType`, `iterationCount`, `unrolledCount` |
| `aios.planning.loop.expansion_completed` | LoopEngine | CapabilityPlanner, Metrics | `correlationId`, `loopId`, `unrolledCount`, `expandedGraphSize` |
| `aios.planning.loop.validation_failed` | LoopEngine | CapabilityPlanner, Alerting | `correlationId`, `loopId`, `reason`, `invariantViolated` |
| `aios.planning.loop.iteration_validated` | LoopEngine | CapabilityPlanner, ExecutionEngine | `correlationId`, `loopId`, `iteration`, `validationResult` |

**Invariant EVENT-3 (Ordering Guarantee):**  
Within a single `correlationId`, events of the same category MUST be delivered in timestamp order. Cross-category ordering follows the causal flow above.

### 8.2.8.5 Failure Events

| Failure Event | Trigger | Recovery Action |
|---------------|---------|-----------------|
| `intent.analysis_failed` | Unparsable intent, zero matches, contradiction | Human clarification required |
| `discovery.failed` | Zero candidates, all denied, substitution loop | Policy override or intent revision |
| `plan.failed` | Cycle, unresolved dependency, budget exceeded | Graph restructuring, constraint relaxation |
| `artifact.generation_failed` | Template error, signing failure, hash mismatch | Retry with same inputs (deterministic) |
| `plan.rejected` | Governance denial | Intent revision or appeal process |
| `control.timeout` | Stage exceeds `maxStageDuration` | Retry (if transient) or escalate |
| `control.cancelled` | Operator/user cancellation | Cleanup partial state, emit audit record |

---

## 8.2.9 Planning State Machine

### 8.2.9.1 State Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PLANNING STATE MACHINE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌─────────┐                                                                  │
│    │  IDLE   │                                                                  │
│    └────┬────┘                                                                  │
│         │ intent.received                                                       │
│         ▼                                                                       │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐         │
│    │ INTENT_RECEIVED │────▶│INTENT_ANALYSIS  │────▶│DISCOVERY        │         │
│    └─────────────────┘     └────────┬────────┘     └────────┬────────┘         │
│                                     │                       │                   │
│                              ┌──────┴──────┐          ┌──────┴──────┐          │
│                              │             │          │             │          │
│                        analysis.success  │     discovery.success    │
│                              analysis.fail│           discovery.fail │
│                              │             │          │             │          │
│                              ▼             ▼          ▼             ▼          │
│                        ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│                        │  VALIDATION │  │ PLANNING │  │ GOVERNANCE│  │ ARTIFACT │
│                        └──────┬──────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
│                               │              │           │           │       │
│                        ┌──────┴──────┐       │           │           │       │
│                        │             │       │           │           │       │
│                  validation.success    planning.success    │           │
│                  validation.fail       planning.fail       │           │
│                        │             │       │           │           │       │
│                        ▼             ▼       ▼           ▼           ▼       │
│                  ┌────────────┐  ┌────────┐  ┌──────────┐  ┌────────────┐   │
│                  │GOVERNANCE  │  │FAILED  │  │ REVIEW   │  │ GENERATION │   │
│                  │  REVIEW    │  └────────┘  └────┬─────┘  └──────┬─────┘   │
│                  └─────┬─────┘                    │             │          │
│                        │                     ┌────┴────┐        │          │
│                        │                     │         │        │          │
│              ┌────────┴────────┐      approved│  rejected│        │
│              │                 │              │          │        │
│              ▼                 ▼              ▼          ▼        ▼          │
│        ┌─────────────┐   ┌─────────────┐  ┌─────────┐  ┌──────────┐        │
│        │  ARTIFACT   │   │  EXECUTION  │  │  BACK TO │  │ ARTIFACT │        │
│        │ GENERATION  │   │   READY     │  │ IDLE/    │  │ GENERATION│        │
│        └──────┬──────┘   └─────────────┘  │ REVISE  │  └────┬─────┘        │
│               │                            (manual)      │       │           │
│               ▼                                                 ▼           │
│        ┌─────────────┐                                    ┌──────────┐       │
│        │   PLAN      │                                    │  EXECUTION│       │
│        │    READY    │                                    │   READY  │       │
│        └─────────────┘                                    └──────────┘       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2.9.2 State Definitions

| State | Description | Entry Condition | Exit Transitions |
|-------|-------------|-----------------|------------------|
| `IDLE` | No active planning flow | Initial state, or after `PLAN_READY`/`FAILED`/`CANCELLED` | `INTENT_RECEIVED` on `intent.received` |
| `INTENT_RECEIVED` | Intent accepted, queued for analysis | `intent.received` event processed | `INTENT_ANALYSIS` (auto), `IDLE` (cancel) |
| `INTENT_ANALYSIS` | Decomposing, normalizing, extracting | Analysis begins | `DISCOVERY` (success), `FAILED` (fail), `IDLE` (cancel) |
| `DISCOVERY` | Resolving capabilities from registries | `INTENT_ANALYSIS` success | `VALIDATION` (success), `FAILED` (fail), `IDLE` (cancel) |
| `VALIDATION` | Validating dependencies, versions, compatibility | `DISCOVERY` success | `PLANNING` (success), `FAILED` (fail), `IDLE` (cancel) |
| `PLANNING` | Building execution graph, resolving bindings | `VALIDATION` success | `GOVERNANCE_REVIEW` (success), `FAILED` (fail), `IDLE` (cancel) |
| `GOVERNANCE_REVIEW` | Awaiting human/committee approvals | `PLANNING` success (if gates exist) | `ARTIFACT_GENERATION` (approved), `FAILED` (rejected), `IDLE` (cancel) |
| `ARTIFACT_GENERATION` | Generating all six artifact types | `GOVERNANCE_REVIEW` approved or `PLANNING` success (no gates) | `PLAN_READY` (success), `FAILED` (fail), `IDLE` (cancel) |
| `PLAN_READY` | All artifacts generated, plan executable | `ARTIFACT_GENERATION` success | `EXECUTION_READY` (execution triggered), `IDLE` (timeout/cancel) |
| `EXECUTION_READY` | Plan handed to Execution Engine | Execution Engine acknowledges | `IDLE` (terminal for planning) |
| `FAILED` | Terminal failure state | Any stage failure | `IDLE` (after cleanup) |

### 8.2.9.3 Transition Triggers

| Trigger | Source States | Target State | Conditions |
|---------|---------------|--------------|------------|
| `intent.received` | `IDLE` | `INTENT_RECEIVED` | Valid intent schema |
| `analysis.complete` | `INTENT_ANALYSIS` | `DISCOVERY` | `overallConfidence >= 0.70` |
| `analysis.failed` | `INTENT_ANALYSIS` | `FAILED` | Parse error, zero matches, contradiction |
| `discovery.complete` | `DISCOVERY` | `VALIDATION` | All units resolved |
| `discovery.failed` | `DISCOVERY` | `FAILED` | Zero candidates, all denied, substitution loop |
| `validation.complete` | `VALIDATION` | `PLANNING` | DAG valid, versions compatible, budgets OK |
| `validation.failed` | `VALIDATION` | `FAILED` | Cycle, unresolved dep, budget exceeded |
| `planning.complete` | `PLANNING` | `GOVERNANCE_REVIEW` / `ARTIFACT_GENERATION` | Plan built; gates exist? |
| `planning.failed` | `PLANNING` | `FAILED` | Graph construction error, binding failure |
| `governance.approved` | `GOVERNANCE_REVIEW` | `ARTIFACT_GENERATION` | All required gates approved |
| `governance.rejected` | `GOVERNANCE_REVIEW` | `FAILED` | Any required gate rejected |
| `governance.timeout` | `GOVERNANCE_REVIEW` | `FAILED` | Gate timeout exceeded (policy) |
| `artifact.complete` | `ARTIFACT_GENERATION` | `PLAN_READY` | All 6 artifacts generated, hashes verified |
| `artifact.failed` | `ARTIFACT_GENERATION` | `FAILED` | Generation error, hash mismatch, signing failure |
| `execution.triggered` | `PLAN_READY` | `EXECUTION_READY` | Execution Engine accepts plan |
| `cancel.requested` | Any non-terminal | `IDLE` (via `FAILED` cleanup) | Operator/API cancellation |
| `timeout` | Any non-terminal | `FAILED` | Stage exceeds `maxStageDuration` |

### 8.2.9.4 Rollback Transitions

Rollback in the planning phase means **discarding partial planning state** and returning to `IDLE`. No execution-state rollback occurs (that is Section 8.3).

| From State | Rollback Action | Cleanup |
|------------|-----------------|---------|
| `INTENT_ANALYSIS` | Discard `AnalyzedIntent` | Release any temporary analysis resources |
| `DISCOVERY` | Discard `ResolvedCapabilities` | Release registry snapshot references |
| `VALIDATION` | Discard `CapabilityDAG` | Release graph structures |
| `PLANNING` | Discard `ExecutionGraph`, bindings | Release provider reservations (if any) |
| `GOVERNANCE_REVIEW` | Withdraw approval requests | Notify approvers of cancellation |
| `ARTIFACT_GENERATION` | Discard generated artifacts | Delete artifact files, release locks |

**Invariant STATE-1 (Rollback Idempotency):**  
Rollback from any state MUST be idempotent and leave the system in `IDLE` with no residual planning state for that `correlationId`.

**Invariant STATE-2 (No Partial Execution):**  
The planning state machine MUST NEVER transition to `EXECUTION_READY` without passing through `PLAN_READY` with all artifacts verified.

### 8.2.9.5 Timeout Handling

| State | Default Timeout | Configurable Via | On Timeout |
|-------|-----------------|------------------|------------|
| `INTENT_RECEIVED` | 30s | `planning.intentQueueTimeout` | `FAILED` (queue overflow) |
| `INTENT_ANALYSIS` | 60s | `planning.analysisTimeout` | `FAILED` |
| `DISCOVERY` | 120s | `planning.discoveryTimeout` | `FAILED` (retry if transient registry issue) |
| `VALIDATION` | 60s | `planning.validationTimeout` | `FAILED` |
| `PLANNING` | 120s | `planning.planningTimeout` | `FAILED` |
| `GOVERNANCE_REVIEW` | 3600s (1h) | `governance.approvalTimeout` | `FAILED` (configurable per gate) |
| `ARTIFACT_GENERATION` | 60s | `planning.artifactTimeout` | `FAILED` |
| `PLAN_READY` | 86400s (24h) | `planning.planTtl` | `IDLE` (plan expires) |

**Invariant STATE-3 (Timeout Determinism):**  
Timeouts MUST be measured from state entry timestamp. The same plan with same configuration MUST timeout at the same logical time.

### 8.2.9.6 Cancellation Handling

```
Cancellation Flow:

Operator/API → cancel.requested(correlationId, reason, initiator)
                    │
                    ▼
            ┌─────────────────┐
            │  Current State  │
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Pre-Planning  Mid-Planning  Post-Planning
   (IDLE,        (ANALYSIS,    (GOVERNANCE,
    INTENT_       DISCOVERY,    REVIEW,
    RECEIVED)     VALIDATION,   ARTIFACT_GEN,
                  PLANNING)     PLAN_READY)
        │            │            │
        ▼            ▼            ▼
   Immediate     Graceful      Withdraw
   abort         stop:        approvals,
   cleanup       finish       cancel
   current       current     artifact
   stage         stage       generation,
                 then        then
                 abort       abort
        │            │            │
        └────────────┴────────────┘
                     │
                     ▼
              ┌─────────────┐
              │    FAILED   │ (with cleanup)
              │  (cancelled)│
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │     IDLE    │
              └─────────────┘
```

**Invariant STATE-4 (Cancellation Atomicity):**  
Cancellation MUST either complete fully (reach `IDLE`) or not start. Partial cancellation cleanup MUST NOT leave orphaned resources.

### 8.2.9.7 Loop Engine

The **Loop Engine** provides deterministic, bounded iteration constructs within the planning state machine for capabilities with `manifest.loop` specifications.

```
Loop Engine Integration:

CAPABILITY LOOP SPEC (in manifest):
{
  "loop": {
    "type": "FOR_EACH" | "WHILE" | "UNTIL",
    "iterator": "items",           // FOR_EACH: collection reference
    "condition": "$.output.ready", // WHILE/UNTIL: JSONPath condition
    "maxIterations": 100,          // REQUIRED: static upper bound
    "parallel": false,             // FOR_EACH only: parallel vs sequential
    "breakOn": "FAILURE"           // FAILURE | ANY_ERROR | NEVER
  }
}

PLANNING EXPANSION (§8.2.6.7):
- FOR_EACH: Expands to parallel group (if parallel=true, independent) or sequential chain
- WHILE: Inserts loop header node (condition check) + body subgraph + loop back edge
- UNTIL: Same as WHILE with inverted condition

LOOP ENGINE STATE MACHINE EXTENSION:

PLANNING ──▶ LOOP_EXPANSION ──▶ LOOP_VALIDATION ──▶ PLANNING (continue)
                │                    │
                │                    ├── validation.success ──▶ continue
                │                    │
                │                    └── validation.fail ──▶ FAILED
                │         (unbounded, invariant violation, maxIterations < 1)
                │
                └── expansion.complete ──▶ LOOP_VALIDATION
```

**Loop Engine Invariants:**

| Invariant | Statement |
|-----------|-----------|
| **LOOP-1 (Static Boundedness)** | Every loop MUST declare `maxIterations` as positive integer. Unbounded loops → `PlanningFailed`. |
| **LOOP-2 (Deterministic Expansion)** | Given identical loop spec and inputs, expansion produces identical subgraph. |
| **LOOP-3 (No Runtime Mutation)** | Loop structure is fully resolved at planning time. Execution Engine iterates but does not modify graph. |
| **LOOP-4 (Checkpoint Per Iteration)** | Each loop iteration creates a checkpoint for recovery (§8.2.9.11). |

**Configuration:**
- `planning.loop.defaultMaxIterations`: Default bound if manifest omits (default: 100)
- `planning.loop.maxTotalIterationsPerPlan`: Aggregate cap across all loops (default: 1000)

### 8.2.9.8 AI Council State Integration

When governance approval requires multi-model deliberation (§8.2.3.6), the state machine enters **AI Council Deliberation** sub-state:

```
GOVERNANCE_REVIEW
       │
       ├──▶ AI_COUNCIL_DELIBERATION (if policy.aiCouncil.required)
       │       │
       │       ├──▶ AI_COUNCIL_VOTING
       │       │       │
       │       │       ├──▶ APPROVED (≥2/3 ALLOW) ──▶ ARTIFACT_GENERATION
       │       │       │
       │       │       ├──▶ REJECTED (≥2/3 DENY) ──▶ FAILED
       │       │       │
       │       │       └──▶ ESCALATE (split/uncertain) ──▶ GOVERNANCE_REVIEW (human)
       │       │
       │       └──▶ COUNCIL_TIMEOUT ──▶ ESCALATE
       │
       └──▶ (normal) ARTIFACT_GENERATION (if no council required)
```

**AI Council State Fields:**
- `councilId`: UUID
- `models[]`: `{modelId, version, role: "reasoning"|"safety"|"cost"}`
- `deliberationTranscript`: Array of `{turn, modelId, inputHash, outputHash, vote}`
- `verdict`: `APPROVED` | `REJECTED` | `ESCALATED`
- `councilConfidence`: Aggregated model confidence (0.0–1.0)

**Invariant STATE-7 (Council Determinism):**  
Given identical context, model versions, and council composition → identical verdict and transcript.

### 8.2.9.9 Recovery

Recovery applies when a **transient failure** occurs (registry blip, network timeout, resource contention) and the system can resume from a known-good checkpoint.

**Recovery Points (snapshots taken at state exit):**

| State Exit | Checkpoint Data |
|------------|-----------------|
| `INTENT_ANALYSIS` | `AnalyzedIntent` |
| `DISCOVERY` | `ResolvedCapabilities` |
| `VALIDATION` | `ValidatedDependencyGraph` |
| `PLANNING` | `ExecutionGraph` + `Bindings` |
| `GOVERNANCE_REVIEW` | `Plan` + `Approvals` |
| `ARTIFACT_GENERATION` | `Partial Artifacts` |
| `LOOP_EXPANSION` | `ExpandedLoopSubgraph` |
| `AI_COUNCIL_DELIBERATION` | `CouncilTranscript` (partial) |

| Recovery Scenario | Recovery Action |
|-------------------|-----------------|
| `DISCOVERY` timeout (registry transient) | Resume from `AnalyzedIntent` checkpoint, retry discovery |
| `VALIDATION` failure (transient) | Resume from `ResolvedCapabilities`, re-validate |
| `PLANNING` failure (resource contention) | Resume from `ValidatedDependencyGraph`, re-plan |
| `ARTIFACT_GENERATION` failure (signing service down) | Resume from `ExecutionGraph`, regenerate artifacts |
| `GOVERNANCE_REVIEW` timeout (then approved) | Resume from `Plan + Approvals`, generate artifacts |
| `LOOP_VALIDATION` failure | Resume from `LoopExpansion` checkpoint, re-validate |

**Invariant STATE-5 (Recovery Correctness):**  
Recovery MUST resume from the latest valid checkpoint. The recovered flow MUST produce identical outputs to a non-interrupted flow (determinism preserved).

**Invariant STATE-8 (Loop Recovery):**  
Loop iteration checkpoints enable recovery within a loop body. On failure at iteration N, resume from iteration N checkpoint with same loop state.

### 8.2.9.10 Human Intervention

Human intervention points in the planning state machine:

| Intervention Point | State | Action | Authority |
|--------------------|-------|--------|-----------|
| **Intent Clarification** | `INTENT_ANALYSIS` (low confidence) | Provide structured clarification | Intent Originator |
| **Policy Override** | `DISCOVERY` (all denied) | Approve specific capability despite policy | Policy Admin |
| **Governance Approval** | `GOVERNANCE_REVIEW` | Approve/reject gates | Designated Approvers |
| **Plan Revision** | `PLAN_READY` (or `GOVERNANCE_REVIEW` rejected) | Modify intent, re-plan | Intent Originator |
| **Force Cancel** | Any | Immediate cancellation | Platform Admin |
| **Force Approve** | `GOVERNANCE_REVIEW` (timeout) | Override timeout, approve | Platform Admin (audited) |

**Invariant STATE-6 (Human Intervention Audit):**  
Every human intervention MUST generate an audit event with: `interventionId`, `correlationId`, `actor`, `action`, `justification`, `timestamp`, `prevState`, `nextState`.

---

## 8.2.10 Failure Handling

### 8.2.10.1 Failure Taxonomy

| Failure Class | Category | Examples | Severity |
|---------------|----------|----------|----------|
| **F1** | Missing Capability | No capability matches intent unit in any registry | BLOCKING |
| **F2** | Version Conflict | Required version range unsatisfiable across dependencies | BLOCKING |
| **F3** | Invalid Contract | Parameter/output schema mismatch, interface incompatibility | BLOCKING |
| **F4** | Policy Violation | Capability denied by allowlist/denylist, license, compliance | BLOCKING |
| **F5** | Governance Rejection | Required approval gate explicitly rejected | BLOCKING |
| **F6** | Dependency Cycle | Capability graph contains cycle | BLOCKING |
| **F7** | Timeout | Stage exceeds max duration | RETRYABLE |
| **F8** | Registry Unavailable | Registry endpoint unreachable, auth failure | RETRYABLE |
| **F9** | Invalid Metadata | Manifest schema validation failure, missing required fields | BLOCKING |
| **F10** | Ambiguous Resolution | Multiple equally-ranked candidates, no policy tie-break | BLOCKING |
| **F11** | Partial Discovery | Some units resolved, others failed | DEGRADED |
| **F12** | Artifact Generation | Template error, hash mismatch, signing failure | RETRYABLE |

### 8.2.10.2 Failure Handling Matrix

| Failure | Detection Point | Recovery Strategy | Fallback | Escalation |
|---------|-----------------|-------------------|----------|------------|
| **F1: Missing Capability** | Discovery | Substitution rules (§8.2.5.6) | External registry (if policy allows) | Human: provide capability or revise intent |
| **F2: Version Conflict** | Validation | Version relaxation (policy) | Select alternative capability | Human: pin compatible versions |
| **F3: Invalid Contract** | Validation/Discovery | Adapter capability (policy) | Substitute capability | Human: fix manifest or intent |
| **F4: Policy Violation** | Discovery | Policy exception (audited) | Alternative compliant capability | Policy Admin: grant exception |
| **F5: Governance Rejection** | Governance Review | Intent revision | None (hard stop) | Intent Originator: revise and re-submit |
| **F6: Dependency Cycle** | Validation | Graph restructuring (remove/soften edges) | Manual graph edit | Architect: resolve architectural cycle |
| **F7: Timeout** | Any Stage | Retry with backoff (max 3) | Extend timeout (policy) | Alert on-call: investigate stall |
| **F8: Registry Unavailable** | Discovery | Retry with backoff (max 3) | Use cached snapshot (if fresh) | Alert on-call: restore registry |
| **F9: Invalid Metadata** | Discovery/Validation | Reject capability, try alternative | None for primary | Capability Owner: fix manifest |
| **F10: Ambiguous Resolution** | Discovery | Require explicit policy tie-break | Human selection | Policy Admin: define precedence |
| **F11: Partial Discovery** | Discovery | Fail fast (default) | Continue with resolved subset (policy: `allowPartial`) | Alert: incomplete plan |
| **F12: Artifact Generation** | Artifact Generation | Retry (deterministic → should succeed) | None | Alert: generator bug |

### 8.2.10.3 Recovery Procedures

#### Retry with Exponential Backoff (for F7, F8, F12)

```
Retry Policy:
- Max Attempts: 3 (configurable via planning.maxRetries)
- Base Delay: 1s
- Multiplier: 2.0 (1s, 2s, 4s)
- Max Delay: 30s
- Jitter: ±10%
- Retryable Errors: NETWORK_ERROR, TIMEOUT, SERVICE_UNAVAILABLE, TRANSIENT_FAILURE
- Non-Retryable: VALIDATION_ERROR, POLICY_DENY, GOVERNANCE_REJECT, CYCLE_DETECTED
```

#### Checkpoint Recovery (for F7, F8 mid-stage)

```
On Transient Failure:
1. Identify latest valid checkpoint (state exit snapshot)
2. Restore planning state from checkpoint
3. Increment retry counter
4. Re-enter failed stage with same inputs
5. If max retries exhausted → escalate per matrix
```

#### Graceful Degradation (for F11: Partial Discovery)

If `policy.allowPartialDiscovery = true`:

```
1. Partition units: RESOLVED vs UNRESOLVED
2. Build plan for RESOLVED units only
3. Mark plan as PARTIAL with `unresolvedUnits[]`
4. Emit `PlanGeneratedPartial` event
5. Execution Engine MAY execute partial plan (policy: `execution.allowPartial`)
6. Unresolved units → separate intent for later resolution
```

**Invariant FAILURE-1 (Fail-Fast Default):**  
Unless explicitly overridden by policy (`allowPartial`, `allowDegraded`), ANY blocking failure (F1–F6, F9–F10) MUST halt the pipeline immediately with `FAILED` state.

**Invariant FAILURE-2 (Retry Determinism):**  
Retries MUST use identical inputs (including snapshots). A retry that succeeds MUST produce identical outputs to a non-retried run.

**Invariant FAILURE-3 (Escalation Traceability):**  
Every escalation MUST create an audit record linking: `failureId`, `correlationId`, `failureClass`, `recoveryAttempts`, `escalationReason`, `escalatedTo`, `timestamp`.

### 8.2.10.4 Fallback Capabilities

Fallback capabilities are **pre-configured alternatives** for critical capability patterns, defined in policy:

```json
{
  "fallbackMap": {
    "deploy.kubernetes.*": {
      "primary": "deploy.kubernetes.v2",
      "fallbacks": [
        { "capabilityId": "deploy.helm.v1", "condition": "helmAvailable" },
        { "capabilityId": "deploy.manual.v1", "condition": "always", "manual": true }
      ]
    },
    "test.*": {
      "primary": "test.junit.v1",
      "fallbacks": [
        { "capabilityId": "test.pytest.v1", "condition": "pythonAvailable" }
      ]
    }
  }
}
```

**Invariant FAILURE-4 (Fallthrough Exhaustion):**  
If all fallbacks exhausted → `FAILED`. Fallbacks are not recursive (fallback of a fallback not permitted).

### 8.2.10.5 Escalation Paths

| Escalation Level | Trigger | Target | SLA |
|------------------|---------|--------|-----|
| **L0: Self-Healing** | Transient execution signals (timeout, cost overrun, latency spike, registry unavailable) | Automated plan healing | < 30s (§8.2.10.6) |
| **L1: Automatic Retry** | Transient failure (F7, F8, F12) after L0 exhausted | Retry with backoff | Immediate |
| **L2: Policy Override** | Policy violation (F4) with exception criteria | Policy Admin | 15 min |
| **L3: Human Clarification** | Ambiguous/partial (F10, F11, low confidence) | Intent Originator | 30 min |
| **L4: Architectural Review** | Cycle (F6), systemic contract issues (F3) | Platform Architect | 2 hours |
| **L5: Platform Operations** | Registry down (F8 persistent), generator bugs (F12) | On-call Platform Eng | 1 hour |
| **L6: Governance Appeal** | Governance rejection (F5) | Governance Board | Per policy |

### 8.2.10.6 Self-Healing Planning

The **Self-Healing Planning** subsystem automatically adapts planning decisions in response to observed failures, degraded performance, or environmental changes — without human intervention — while preserving determinism and auditability.

```
Self-Healing Planning Loop:

TRIGGER (from Execution Engine via events):
├── F7 timeout → analyze bottleneck node
├── F8 registry unavailable → check snapshot freshness
├── F11 partial discovery → evaluate unresolved units
├── Runtime: cost overrun → compare actual vs estimated
└── Runtime: latency spike → identify critical path

HEALING ACTIONS (deterministic, replayable):
├── SUBSTITUTION: Swap capability per Recommendation Graph (§8.2.5.13)
├── REOPTIMIZATION: Re-run Optimization Layer (§8.2.6.8) with updated metrics
├── PARALLELISM_ADJUST: Recompute parallel groups with observed durations
├── RESOURCE_RESIZE: Adjust provider requirements per Execution Profile actuals
├── FALLBACK_ACTIVATION: Activate pre-configured fallback (not recursive)
└── CONFIDENCE_RECALC: Re-propagate confidence with observed failure evidence

VALIDATION (all must pass):
├── Invariant check: ALL PLAN-1 through PLAN-9 hold
├── Budget check: new aggregate ≤ quotas
├── Governance check: no new gates, no gate weakening
├── Confidence check: new planConfidence ≥ 0.60
└── Determinism check: replay with same inputs → identical healed plan

OUTPUT:
- Healed CapabilityPlan (new planId, incremented version)
- HealingRecord: {trigger, actions, validationResults, confidenceDelta}
- Event: `aios.planning.plan.healed` with correlationId
```

**Self-Healing Triggers from Execution:**

| Execution Signal | Planning Response | Policy Gate |
|------------------|-------------------|-------------|
| Node timeout (F7) | Reoptimize: split, substitute, or add parallelism | `planning.selfHeal.onTimeout` |
| Cost overrun > 20% | Reoptimize: cost substitution, resource right-sizing | `planning.selfHeal.onCostOverrun` |
| Latency p99 > 2× estimate | Reoptimize: parallelism, provider affinity | `planning.selfHeal.onLatencySpike` |
| Registry unavailable (F8) | Use Planning Memory substitution hints (§8.2.3.8) | `planning.selfHeal.onRegistryDown` |
| Capability deprecated | Substitute per substitutionMap + memory hints | `planning.selfHeal.onDeprecation` |

**Healing Constraints:**

| Constraint | Enforcement |
|------------|-------------|
| **Max Healing Rounds** | `planning.selfHeal.maxRounds` (default: 2 per correlationId) |
| **Confidence Floor** | Healed plan confidence MUST ≥ 0.60 (INV-PLAN-CONF-1) |
| **No Gate Weakening** | Healing CANNOT remove or weaken governance gates |
| **Audit Trail** | Every healing action recorded in Governance Manifest + HealingRecord |
| **Replay Verification** | Healed plan MUST pass Replay Verification (§8.2.12.6) |

**Invariant HEAL-1 (Healing Determinism):**  
Given identical plan, execution signals, snapshots, and policy → self-healing MUST produce identical healed plan.

**Invariant HEAL-2 (Healing Safety):**  
A healed plan MUST satisfy ALL invariants of the original plan. Healing only optimizes within the invariant boundary.

**Invariant HEAL-3 (Healing Traceability):**  
Every healing action MUST be traceable to: `triggerEventId`, `originalPlanId`, `healingRuleId`, `appliedOptimizationId`, `validationPassed`.

**Invariant HEAL-4 (Healing Budget):**  
Total healing time (trigger → healed plan ready) MUST NOT exceed `planning.selfHeal.maxHealingTime` (default: 30s). Timeout → escalate to L1 retry / L3 human.

---

## 8.2.11 Architectural Invariants

### 8.2.11.1 Structural Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-STRUCT-1** | Pipeline Stage Isolation | Each pipeline stage (Intent Analysis, Capability Resolution, Dependency Resolution, Plan Assembly, Artifact Generation) is a pure function: `Output = f(Input)`. No stage mutates inputs or shared state. |
| **INV-STRUCT-2** | Snapshot Atomicity | Registry, Policy, and Configuration snapshots are taken at a single logical timestamp at pipeline start. No stage observes a different snapshot version. |
| **INV-STRUCT-3** | DAG Structure | The Capability Graph is always a Directed Acyclic Graph. Cycles are detected and reported as `PlanningFailed`; they are never silently broken. |
| **INV-STRUCT-4** | Manifest Pinning | Every capability in a generated plan references an exact version with content hash. No version ranges, "latest", or mutable references in artifacts. |
| **INV-STRUCT-5** | Artifact Completeness | A `PLAN_READY` state is only reached when all six required artifacts (Claude.md, Project Hooks, Execution Metadata, Capability Manifest, Execution Profile, Governance Manifest) are generated, hashed, and verified. |

### 8.2.11.2 Runtime Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-RUNTIME-1** | Deterministic Planning | Given identical `Intent`, `RegistrySnapshot`, `PolicySnapshot`, `ConfigSnapshot`, `HistoricalMetricsSnapshot` → the pipeline produces bit-identical `CapabilityPlan` and artifacts. |
| **INV-RUNTIME-2** | Bounded Execution | All planning stages complete within configured timeouts. No stage blocks indefinitely. |
| **INV-RUNTIME-3** | Resource Budget Adherence | Aggregate resource budget in `CapabilityPlan` ≤ available quotas from Resource Manager at plan time. |
| **INV-RUNTIME-4** | Idempotent Retries | Retrying any stage with identical inputs produces identical outputs. Retries do not accumulate side effects. |
| **INV-RUNTIME-5** | Cancellation Safety | Cancellation at any point leaves no orphaned resources, partial artifacts, or inconsistent state. System returns to `IDLE`. |

### 8.2.11.3 Discovery Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-DISC-1** | Resolution Order | Project Registry → Global Registry → External Registry. Lower-priority registry capabilities are never selected when a compatible higher-priority capability exists, unless explicit policy override. |
| **INV-DISC-2** | Substitution Transparency | Every capability substitution is recorded with original requirement, substituted capability, and substitution rule ID. No silent substitutions. |
| **INV-DISC-3** | Confidence Scoring | Every resolution decision carries a confidence score 0.0–1.0. Decisions below threshold (0.70) trigger `LowConfidence` event. |
| **INV-DISC-4** | Duplicate Elimination | Structurally or semantically equivalent capabilities are deduplicated. The retained representative is from the highest-priority registry source. |
| **INV-DISC-5** | Policy Decision Recording | Every policy evaluation (ALLOW/DENY/REQUIRE_APPROVAL) is recorded with policy rule ID, evaluation timestamp, and decision rationale. |

### 8.2.11.4 Planning Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-PLAN-1** | Acyclicity | The Capability Graph is a DAG (PLAN-1). |
| **INV-PLAN-2** | Dependency Completeness | All declared dependencies resolve to vertices in the graph (PLAN-2). |
| **INV-PLAN-3** | Deterministic Ordering | Topological sort produces identical ordering for identical DAG (PLAN-3). |
| **INV-PLAN-4** | Parallelism Correctness | Parallel groups contain mutually independent nodes (PLAN-4). |
| **INV-PLAN-5** | Rollback Completeness | Every irreversible capability has a rollback node (PLAN-5). |
| **INV-PLAN-6** | Loop Boundedness | All loops have statically verifiable max iterations (PLAN-6). |
| **INV-PLAN-7** | Budget Validity | Aggregate budget ≤ quotas (PLAN-7). |
| **INV-PLAN-8** | Governance Satisfiability | All governance gates have valid approvers (PLAN-8). |
| **INV-PLAN-9** | Traceability Completeness | Every plan element traces to an intent unit (PLAN-9). |

### 8.2.11.5 Resolution Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-RES-1** | Semantic Versioning | Version selection follows SemVer 2.0.0. Constraints satisfied by highest compatible version. |
| **INV-RES-2** | Pre-Release Control | Pre-release versions selected only if explicitly allowed by policy. |
| **INV-RES-3** | Conflict Determinism | Same-ID/different-version conflicts resolved by highest satisfying version. Different-ID/same-function conflicts resolved by fixed priority: policy → cost → risk → performance → recency. |
| **INV-RES-4** | Validation Before Ranking | Candidates failing compatibility or policy validation are excluded before ranking. |
| **INV-RES-5** | Fallback Exhaustion | If primary, alternatives, and substitutions all fail → resolution fails. No silent fallthrough. |

### 8.2.11.6 Cache Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-CACHE-1** | Cache Determinism | Cache hit produces bit-identical output to cache miss. Cache is pure acceleration. |
| **INV-CACHE-2** | Snapshot Isolation | Cache key includes RegistrySnapshot + PolicySnapshot + ConfigSnapshot versions. Cross-snapshot contamination impossible. |
| **INV-CACHE-3** | Invalidation Correctness | On `RegistryUpdated`/`PolicyChanged`/`CapabilityDeprecated`, all affected entries evicted before next resolution. |
| **INV-CACHE-4** | TTL Determinism | Cache TTL measured from entry creation. Same TTL + same creation time → same expiry. |

### 8.2.11.7 Planning Memory Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-MEM-1** | Read-Only During Pipeline | Planning Memory is read-only during pipeline execution. Writes occur only at pipeline completion via `PlanningMemoryRecorded` event. |
| **INV-MEM-2** | Tenant Isolation | Planning Memory is tenant-scoped. Cross-tenant access requires explicit policy opt-in (`planning.memory.allowCrossTenant`). |
| **INV-MEM-3** | Evidence-Based Entries | Every memory entry includes `sourceCorrelationId`, `successMetric`, `confidenceAtWrite`. No heuristic-only entries. |
| **INV-MEM-4** | Bounded Growth | Planning Memory has configured max entries (`planning.memory.maxEntries`) and TTL (`planning.memory.maxAge`). LRU eviction with metrics. |

### 8.2.11.8 Model Routing Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-MR-1** | Deterministic Routing | All model calls use temperature=0, fixed seed. Identical prompt + model version → identical response. |
| **INV-MR-2** | Replay Capture | Every model routing call records: `modelId`, `modelVersion`, `promptHash`, `responseHash`, `tokenUsage`, `latencyMs`. |
| **INV-MR-3** | Budget Enforcement | Total token usage per planning flow ≤ `planning.modelRouting.tokenBudget` (default: 50k). Exceeded → fallback to heuristic. |
| **INV-MR-4** | Fallback Determinism | Model routing fallback (heuristic) is deterministic and logged. No silent degradation. |

### 8.2.11.9 AI Council Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-AC-1** | Council Determinism | Given identical context, model versions, and council composition → identical verdict and transcript. |
| **INV-AC-2** | Quorum Enforcement | Council verdict requires ≥2/3 ALLOW or ≥2/3 DENY. Split → ESCALATE to human. |
| **INV-AC-3** | Transcript Immutability | Full deliberation transcript (turns, votes, rationales) stored in Governance Manifest. Immutable. |
| **INV-AC-4** | Model Diversity | Council MUST include models with distinct roles (reasoning, safety, cost). Homogeneous councils prohibited. |

### 8.2.11.10 Skill Composition Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-SKILL-1** | Skill Transparency | Skills fully expanded in CapabilityDAG with `skillBoundary` annotations. No opaque execution. |
| **INV-SKILL-2** | Skill Governance Inheritance | Skill inherits union of step governance requirements. Approval gate at skill entry. |
| **INV-SKILL-3** | Skill Deterministic Expansion | Given identical inputs and snapshots, skill expansion produces identical DAG. |
| **INV-SKILL-4** | Skill Confidence Aggregation | Skill confidence = geometric_mean(step.confidences) × validation_score. Propagates as single unit. |

### 8.2.11.11 Optimization Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-OPT-1** | Optimization Safety | Optimization that violates ANY invariant is automatically rejected. No optimization weakens guarantees. |
| **INV-OPT-2** | Optimization Determinism | Given identical plan, profile, memory, policy → identical optimization decisions (or identical rejection). |
| **INV-OPT-3** | Optimization Traceability | Every applied optimization recorded with: `optimizationId`, `type`, `beforeMetrics`, `predictedAfterMetrics`, `evidenceRef`. |
| **INV-OPT-4** | Optimization Budget | Max 3 optimizations per plan. Total optimization time ≤ `planning.optimization.maxTime` (default: 10s). |

### 8.2.11.12 Self-Healing Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-HEAL-1** | Healing Determinism | Identical plan + execution signals + snapshots + policy → identical healed plan. |
| **INV-HEAL-2** | Healing Safety | Healed plan satisfies ALL original plan invariants. Healing only optimizes within invariant boundary. |
| **INV-HEAL-3** | Healing Traceability | Every healing action traces to: `triggerEventId`, `originalPlanId`, `healingRuleId`, `appliedOptimizationId`, `validationPassed`. |
| **INV-HEAL-4** | Healing Budget | Healing trigger → healed plan ready ≤ `planning.selfHeal.maxHealingTime` (default: 30s). Timeout → escalate. |
| **INV-HEAL-5** | Healing Replay | Healed plan MUST pass Replay Verification (§8.2.12.6) against original inputs + healing signals. |

### 8.2.11.6 Artifact Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-ART-1** | Deterministic Generation | Identical inputs → bit-identical artifacts (ARTIFACT-8). |
| **INV-ART-2** | Version Alignment | All artifacts share the same version = `CapabilityPlan.version`. |
| **INV-ART-3** | Content Hashing | Every artifact includes SHA256(content). Verification compares hashes. |
| **INV-ART-4** | Generator Attribution | Every artifact records `generatedBy: "CapabilityPlanner/x.y.z"`. |
| **INV-ART-5** | Governance Evidence | Governance Manifest contains all triggers, policy evaluations, and evidence for independent audit. |

### 8.2.11.7 Determinism Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-DET-1** | Pure Pipeline | The entire discovery-to-planning pipeline is a pure function: `Plan = f(Intent, RegistrySnapshot, PolicySnapshot, ConfigSnapshot, MetricsSnapshot)`. |
| **INV-DET-2** | No Hidden Inputs | No stage reads from external state not captured in the input snapshots. No clocks, random values, or ambient state. |
| **INV-DET-3** | Replay Equivalence | Replaying a planning flow from recorded snapshots produces identical outputs to the original run. |
| **INV-DET-4** | Tie-Breaking Determinism | All tie-breaking (topological sort, candidate ranking, parallel grouping) uses deterministic rules (lexicographic ID, fixed priority order). |

### 8.2.11.8 State Machine Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-SM-1** | Valid Transitions | Only transitions defined in §8.2.9.3 are permitted. Invalid transitions are rejected. |
| **INV-SM-2** | Terminal States | `PLAN_READY` and `EXECUTION_READY` are success terminals. `FAILED` and `IDLE` (after cleanup) are failure/idle terminals. |
| **INV-SM-3** | No Execution Without Artifacts | `EXECUTION_READY` is only reachable from `PLAN_READY` with all artifacts verified. |
| **INV-SM-4** | Governance Gate Enforcement | If `PLANNING` produces governance gates, `GOVERNANCE_REVIEW` is mandatory. Cannot skip to `ARTIFACT_GENERATION`. |
| **INV-SM-5** | Checkpoint Consistency | Checkpoints at state exits capture all data needed to resume. Recovery from checkpoint produces identical forward progress. |

### 8.2.11.9 Event Ordering Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-EVT-1** | Correlation Integrity | All events in a planning flow share the same `correlationId`. |
| **INV-EVT-2** | Causation Acyclicity | The causation graph (edges: `causationId` → `eventId`) is acyclic and rooted at `intent.received`. |
| **INV-EVT-3** | Category Ordering | Within a `correlationId`, events of the same category are delivered in timestamp order. |
| **INV-EVT-4** | Failure Event Completeness | Every transition to `FAILED` state emits a corresponding `*.failed` event with error details. |

### 8.2.11.10 Provider Independence Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-PROV-1** | Registry Abstraction | Discovery queries Capability Facade interface, not concrete registry implementations. |
| **INV-PROV-2** | External Registry Isolation | External registry failures do not block Project/Global resolution. External is optional. |
| **INV-PROV-3** | Provider Neutrality | Planning does not assume specific provider implementations. Provider requirements are declared in manifests, resolved at planning time. |
| **INV-PROV-4** | Capability Portability | Capability manifests are provider-agnostic. Provider-specific configuration is in `providerRequirement` binding, not in capability logic. |

### 8.2.11.11 Human Override Invariants

| Invariant ID | Name | Statement |
|--------------|------|-----------|
| **INV-HUM-1** | Override Audit | Every human override (policy exception, governance approval, force-cancel, force-approve) generates an immutable audit record with actor, justification, and timestamp. |
| **INV-HUM-2** | Override Scope | Overrides apply only to the specific `correlationId` (or explicitly scoped set). They do not modify global policy. |
| **INV-HUM-3** | Approval Authority | Only designated approvers (from governance manifest) can approve gates. Unauthorized approvals are rejected. |
| **INV-HUM-4** | Intent Revision | Human clarification of intent creates a new `correlationId` (new planning flow), not a mutation of the in-flight flow. |
| **INV-HUM-5** | Emergency Override | Platform Admin force-approve/force-cancel is permitted but requires post-incident review within 24 hours. |

---

## 8.2.12 Conformance

### 8.2.12.1 Conformance Levels

| Level | Description | Verification Method |
|-------|-------------|---------------------|
| **L1: Static Verification** | Schema validation, invariant checking on artifacts | Automated (CI/CD) |
| **L2: Runtime Verification** | Invariant monitoring during planning execution | Automated (Observability) |
| **L3: Integration Verification** | End-to-end planning flows with real registries | Automated (Test Harness) |
| **L4: Failure Injection** | Chaos testing of failure modes | Automated (Chaos Framework) |
| **L5: Replay Verification** | Determinism verification via snapshot replay | Automated (Replay Engine) |
| **L6: Audit Verification** | Governance evidence completeness, traceability | Semi-automated + Manual |
| **L7: Performance Verification** | Latency, throughput, resource bounds | Automated (Benchmark) |

### 8.2.12.2 Static Verification

**Scope:** All generated artifacts, configuration, policy files.

| Check | Tool | Pass Criteria |
|-------|------|---------------|
| Schema Validation | JSON Schema Validator | All artifacts validate against their schema versions |
| Invariant Checking | Custom Validator | INV-STRUCT-1 through INV-STRUCT-5 hold on artifacts |
| Manifest Pinning | Manifest Verifier | No version ranges, all content hashes present |
| Policy Syntax | Policy Engine | All policy files parse, no undefined references |
| Governance Completeness | Governance Auditor | Every gate has: type, approvers, policyRef, evidence |
| Traceability Links | Traceability Verifier | Every plan element → intent unit link resolvable |

**Invariant CONF-STATIC-1:**  
Static verification MUST pass for every `PLAN_READY` artifact set. Failure blocks transition to `EXECUTION_READY`.

### 8.2.12.3 Runtime Verification

**Scope:** Planning component behavior during execution.

| Monitor | Invariant | Alert Threshold |
|---------|-----------|-----------------|
| Stage Duration | INV-RUNTIME-2 | > 80% of configured timeout |
| Snapshot Age | INV-STRUCT-2 | Snapshot > `maxSnapshotAge` (default: 5 min) |
| Confidence Scores | INV-DISC-3 | Any decision < 0.70 |
| Budget Utilization | INV-RUNTIME-3 | Aggregate budget > 90% quota |
| Retry Count | INV-RUNTIME-4 | > 2 retries for same stage |
| Event Ordering | INV-EVT-3 | Out-of-order delivery detected |

**Invariant CONF-RUNTIME-1:**  
Runtime verification MUST NOT block planning. Violations emit warnings and metrics; only hard invariant violations (cycle, budget exceed) block.

### 8.2.12.4 Integration Verification

**Scope:** End-to-end planning flows against real registry, policy, and resource manager.

| Test Scenario | Description | Success Criteria |
|---------------|-------------|------------------|
| **Happy Path** | Simple intent → complete plan | `PLAN_READY` in < 30s, all invariants hold |
| **Multi-Unit Intent** | 5+ units with dependencies | Correct DAG, parallel groups identified |
| **Cross-Registry** | Units resolve from Project + Global + External | Resolution order respected |
| **Governance Flow** | Plan with 2+ approval gates | Gates inserted, `GOVERNANCE_REVIEW` entered |
| **Partial Failure** | One unit missing capability | `FAILED` (or `PARTIAL` if policy allows) |
| **Large Plan** | 50+ units, deep dependencies | Completes < 120s, memory < 512MB |
| **Concurrent Planning** | 10 simultaneous flows | All complete, no snapshot interference |

**Invariant CONF-INTEG-1:**  
Integration tests MUST run against real (not mocked) Capability Registry, Policy Engine, and Resource Manager.

### 8.2.12.5 Failure Injection

**Scope:** Verified handling of all failure classes (F1–F12) per §8.2.10.1.

| Injection Point | Failure Injected | Expected Behavior |
|-----------------|------------------|-------------------|
| Registry Query | Return empty (F1) | Substitution → fallback → `FAILED` |
| Registry Query | Return conflicting versions (F2) | Version resolution → highest compatible |
| Manifest Fetch | Invalid schema (F9) | Reject capability, try alternative |
| Policy Engine | DENY all (F4) | `FAILED` with policy denial events |
| Governance | Reject gate (F5) | `FAILED` with rejection event |
| Graph Build | Inject cycle (F6) | `FAILED` with cycle path |
| Stage Execution | Delay > timeout (F7) | Timeout → retry → `FAILED` |
| Registry | HTTP 503 (F8) | Retry → cached snapshot → `FAILED` |
| Ranking | Equal scores (F10) | `FAILED` with ambiguity event |
| Artifact Gen | Signing service down (F12) | Retry → `FAILED` |

**Invariant CONF-FAIL-1:**  
Every failure class F1–F12 MUST have a corresponding chaos test that verifies the exact recovery/fallback/escalation behavior specified in §8.2.10.

### 8.2.12.6 Replay Verification

**Scope:** Determinism verification via snapshot replay (INV-DET-3).

```
Replay Verification Process:

1. CAPTURE: During production planning, persist:
   - Intent + Context
   - RegistrySnapshot (full)
   - PolicySnapshot (full)
   - ConfigSnapshot (full)
   - MetricsSnapshot (full)
   - Output: CapabilityPlan + Artifacts
   - Link: correlationId

2. REPLAY: On schedule (daily) or on-demand:
   - Load captured snapshots
   - Re-run planning pipeline (same code version)
   - Compare outputs: Plan + Artifacts

3. VERIFY:
   - Bit-identical CapabilityPlan (JSON canonicalized)
   - Bit-identical artifacts (content hashes match)
   - All invariants hold on replayed output
   - Same event sequence (types, order, payloads)

4. REPORT:
   - Replay pass/fail
   - Any divergence: field, expected, actual
   - Root cause if divergence (code change, data drift)
```

**Invariant CONF-REPLAY-1:**  
Replay verification MUST pass for 100% of captured planning flows. Any divergence is a **conformance violation** requiring immediate investigation.

**Invariant CONF-REPLAY-2:**  
Replay MUST use the exact same code version (git commit) as the original run. Code changes require re-baseline.

### 8.2.12.7 Audit Verification

**Scope:** Governance evidence completeness, traceability chain integrity.

| Audit Check | Verification Method | Frequency |
|-------------|---------------------|-----------|
| Gate Evidence | Every gate in Governance Manifest has: `policyRef`, `approvers`, `evidence`, `status` | Every `PLAN_READY` |
| Approval Validity | Every `governance.approved` event: approver ∈ designated approvers | Every approval |
| Traceability Chain | Intent → Units → Requirements → Capabilities → Plan Nodes → Artifacts | Every `PLAN_READY` |
| Policy Evaluation | Every capability in plan has recorded policy decision (ALLOW/REQUIRE_APPROVAL) | Every `PLAN_READY` |
| Override Records | Every human override has audit record with justification | Continuous |
| Artifact Integrity | Artifact content hashes match Governance Manifest references | Every `PLAN_READY` |

**Invariant CONF-AUDIT-1:**  
Audit verification MUST be automatable for 90% of checks. Manual review only for: justification quality, approver identity verification.

### 8.2.12.8 Optimization Feedback Conformance

**Scope:** Verification that execution-phase metrics feed back into planning cost, risk, and performance models, and that the Optimization Layer and Self-Healing Planning correctly incorporate this feedback.

| Feedback Loop | Verification Method | Frequency |
|---------------|---------------------|-----------|
| **Cost Model Update** | Compare `ExecutionProfile.costPerExecutionUSD` with `CapabilityPlan.aggregateBudget` across executions; verify planning cost estimates converge | Daily (replay) + Continuous (monitoring) |
| **Duration Model Update** | Compare `ExecutionProfile.baselines` with `Plan.nodes.estimatedDuration`; verify estimation error < 20% P99 | Daily (replay) + Continuous |
| **Risk Calibration** | Track actual vs predicted failure rates per capability/classification; verify risk levels match observed outcomes | Weekly |
| **Optimization Effectiveness** | For each applied optimization, measure actual delta vs predicted delta; verify ≥ 70% of optimizations achieve ≥ 80% of predicted benefit | Per optimization application |
| **Cache Hit Rate** | Measure `planning.cache.hitRate`; verify > 60% for repeated intent patterns | Continuous |
| **Planning Memory Utility** | Track memory-assisted resolutions vs cold resolutions; verify confidence boost and latency reduction | Continuous |
| **Model Routing Accuracy** | For routed subtasks, compare model output quality vs heuristic fallback; audit token usage vs budget | Continuous |
| **AI Council Alignment** | Compare council verdicts with human decisions (when escalated); track agreement rate > 90% | Weekly |
| **Self-Healing Success Rate** | Track healed plans that execute successfully without further intervention; verify > 80% | Continuous |
| **Recommendation Adoption** | Track when recommendations are followed vs ignored; correlate with execution outcomes | Continuous |

**Invariant CONF-FEEDBACK-1 (Feedback Completeness):**  
Every execution of a `CAPABILITY_PLAN_READY` plan MUST produce execution metrics that are captured and available for the next planning replay cycle.

**Invariant CONF-FEEDBACK-2 (Feedback Determinism):**  
The feedback incorporation process (ExecutionProfile update → PlanningMemory update → OptimizationLayer input) MUST be deterministic. Identical execution metrics + identical new data → identical updated models.

**Invariant CONF-FEEDBACK-3 (Feedback Latency):**  
Execution metrics MUST be available for planning feedback within `planning.feedback.maxLatency` (default: 5 min) of execution completion.

**Invariant CONF-FEEDBACK-4 (Feedback Safety):**  
Feedback-driven model updates MUST NOT weaken any invariant. Updated cost/risk models are validated against historical data before use in planning.

### 8.2.12.9 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **End-to-End Latency (P99)** | < 60s | Intent receipt → `PLAN_READY` |
| **Intent Analysis (P99)** | < 5s | Intent receipt → `INTENT_ANALYSIS_COMPLETE` |
| **Capability Discovery (P99)** | < 15s | `DISCOVERY_STARTED` → `DISCOVERY_COMPLETED` |
| **Planning (P99)** | < 20s | `PLANNING_STARTED` → `PLAN_GENERATED` |
| **Artifact Generation (P99)** | < 10s | `ARTIFACT_GENERATION_STARTED` → `ARTIFACT_GENERATION_COMPLETED` |
| **Optimization Layer (P99)** | < 10s | `PLAN_VALIDATION_PASS` → `PLAN_OPTIMIZATION_COMPLETE` |
| **Self-Healing (P99)** | < 30s | Execution trigger → healed plan ready |
| **Throughput** | ≥ 100 plans/min | Concurrent planning flows |
| **Memory (P99)** | < 512MB | Per planning flow |
| **CPU (P99)** | < 2 cores | Per planning flow |
| **Registry Query Latency (P99)** | < 200ms | Per registry query |
| **Snapshot Creation (P99)** | < 5s | Atomic snapshot of all three registries |
| **Model Routing Latency (P99)** | < 5s | Request → response (per call) |
| **Cache Hit Latency (P99)** | < 5ms | Cache lookup → result |

**Invariant CONF-PERF-1:**  
Performance targets MUST be met with registry containing 10,000+ capabilities, policy set with 1,000+ rules, and 10 concurrent planning flows.

**Invariant CONF-PERF-2:**  
Latency budgets include all cross-component calls (Registry, Policy, Resource Manager). No external dependency may exceed its allocated budget.

**Invariant CONF-PERF-3:**  
Optimization Layer and Self-Healing MUST complete within their allocated budgets. Exceeding budget → plan proceeds unoptimized / escalates.

### 8.2.12.9 Conformance Summary Matrix

| Requirement Category | Static | Runtime | Integration | Failure Injection | Replay | Audit | Performance |
|----------------------|--------|---------|-------------|-------------------|--------|-------|-------------|
| **Pipeline Determinism** | ✓ | ✓ | ✓ | | ✓ | | |
| **Resolution Order** | ✓ | ✓ | ✓ | ✓ | ✓ | | |
| **Snapshot Isolation** | ✓ | ✓ | ✓ | | ✓ | | |
| **DAG Validity** | ✓ | ✓ | ✓ | ✓ | ✓ | | |
| **Manifest Pinning** | ✓ | | ✓ | | ✓ | | |
| **Confidence Scoring** | ✓ | ✓ | ✓ | | | | |
| **Confidence Propagation** | ✓ | ✓ | ✓ | | ✓ | | ✓ |
| **Policy Decisions** | ✓ | ✓ | ✓ | ✓ | | ✓ | |
| **Governance Gates** | ✓ | ✓ | ✓ | ✓ | | ✓ | |
| **Rollback Completeness** | ✓ | | ✓ | ✓ | ✓ | | |
| **Loop Boundedness** | ✓ | | ✓ | | ✓ | | |
| **Budget Validation** | ✓ | ✓ | ✓ | ✓ | ✓ | | |
| **Traceability** | ✓ | ✓ | ✓ | | ✓ | ✓ | |
| **Event Ordering** | | ✓ | ✓ | | ✓ | | |
| **Artifact Generation** | ✓ | | ✓ | | ✓ | | |
| **Deterministic Replay** | | | | | ✓ | | |
| **Failure Handling** | | | ✓ | ✓ | | | |
| **Self-Healing Planning** | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Optimization Layer** | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| **Discovery Cache** | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| **Planning Memory** | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ |
| **Model Routing** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **AI Council** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| **Skill Composition** | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| **Recommendation Graph** | ✓ | ✓ | ✓ | | ✓ | | ✓ |
| **Latency Bounds** | | ✓ | ✓ | | | | ✓ |

### 8.2.12.10 Verification Diagrams

#### Static Verification Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                    STATIC VERIFICATION PIPELINE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Artifacts ──▶ Schema Validator ──▶ Invariant Checker          │
│                    │                       │                    │
│                    ▼                       ▼                    │
│              ┌──────────┐           ┌──────────┐               │
│              │ PASS/FAIL│           │ PASS/FAIL│               │
│              └────┬─────┘           └────┬─────┘               │
│                   │                      │                      │
│                   └──────────┬───────────┘                      │
│                              ▼                                   │
│                     ┌──────────────────┐                         │
│                     │  CONFORMANCE     │                         │
│                     │    DECISION      │                         │
│                     └────────┬─────────┘                         │
│                              │                                   │
│                    ┌─────────┴─────────┐                         │
│                    ▼                   ▼                         │
│             ┌─────────────┐     ┌─────────────┐                │
│             │  PLAN_READY │     │   BLOCKED   │                │
│             │  (proceed)  │     │  (fail CI)  │                │
│             └─────────────┘     └─────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Replay Verification Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                      REPLAY VERIFICATION LOOP                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRODUCTION                    REPLAY ENVIRONMENT              │
│  ─────────                    ──────────────────               │
│                                                                 │
│  ┌─────────────┐              ┌─────────────┐                  │
│  │   Capture   │              │   Restore   │                  │
│  │  Snapshots  │─────────────▶│  Snapshots  │                  │
│  └─────────────┘   Git Commit  └──────┬──────┘                  │
│       │                               │                         │
│       │                               ▼                         │
│       │                        ┌─────────────┐                  │
│       │                        │  Re-run     │                  │
│       │                        │  Pipeline   │                  │
│       │                        └──────┬──────┘                  │
│       │                               │                         │
│       │                               ▼                         │
│       │                        ┌─────────────┐                  │
│       └───────────────────────▶│  Compare    │                  │
│                                │  Outputs    │                  │
│                                └──────┬──────┘                  │
│                                       │                         │
│                              ┌────────┴────────┐                │
│                              ▼                 ▼                │
│                       ┌─────────────┐   ┌─────────────┐         │
│                       │   MATCH     │   │  DIVERGENCE │         │
│                       │  (conform)  │   │  (violation)│         │
│                       └─────────────┘   └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### End of Part 8 Section 8.2

**Document Control**

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-29 | Chief Software Architect | Initial freeze — Sections 8.2.1 through 8.2.12 |

**Classification:** FROZEN — Normative Engineering Specification  
**Distribution:** All AI-OS engineers, architects, reviewers, automated conformance tooling

---

**Next:** Section 8.3 — Execution Engine Architecture