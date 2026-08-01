# PART 8 CONTEXT — Engineering Reference for Future Sections

**Status:** FROZEN — Authoritative Source of Truth  
**Version:** 1.0.0  
**Date:** 2026-07-29

---

## 1. Part 8 Purpose

The Intelligent Agent & Execution Architecture is the **capability-driven execution substrate** of AI-OS. It transforms intent into observable outcomes through coordinated capability invocation, multi-perspective reasoning, hierarchical retry with strategic rollback, continuous learning, optimization, and self-healing recovery.

**Key Principles:**
- **Hermes is the central orchestrator** — all execution flows through Hermes Kernel
- **AI-OS is an operating environment, not a single AI agent** — execution contexts are correlation-scoped bundles
- **Execution is capability-driven, not agent-driven** — capabilities are first-class architectural components
- **Global → Project scope resolution** — Project overrides Global overrides External Registry
- **Claude Code is one execution provider** — vendor independence is mandatory
- **Local + Cloud + Hybrid providers** — all treated identically through abstraction layers

---

## 2. Architectural Scope

### In Scope (Part 8)
- 8.1 Purpose (FROZEN)
- 8.2 Capability Discovery & Planning (FROZEN)
- 8.3 Execution Context & Plan Architecture
- 8.4 Council Governance Architecture
- 8.5 Loop Engine Architecture
- 8.6 Learning Layer Architecture
- 8.7 Optimization Layer Architecture
- 8.8 Self-Healing Layer Architecture
- 8.9 Human Intervention Architecture
- 8.10 Vendor Independence Architecture
- 8.11 Provider Selection Architecture
- 8.12 Execution Conformance

### Out of Scope
- Implementation code, APIs, technology-specific details
- Core Manager internals (Parts 1, 3, 4)
- Engineering Service behavior (Part 5)
- Workflow orchestration logic (Part 7)
- Event System contracts (Part 2)
- Capability Facade Service internals (Part 6)

---

## 3. Frozen Architectural Decisions

| Decision | Mandate |
|----------|---------|
| **9 Execution Layers** | Fixed count; no addition/removal without ARB approval (INV-EXEC-STR-001) |
| **EventBus-first** | All layer communication via EventBus; no direct method calls in RUNNING state (INV-EXEC-LAYER-001) |
| **5 Hierarchical Loops** | Research → Planning → Implementation → Testing → Deployment (INV-EXEC-STR-007) |
| **Strategic Retry** | NEVER identical execution; every retry modifies strategy (INV-EXEC-STR-008) |
| **Cross-loop Rollback** | Exhaustion → rollback to previous loop, not termination (INV-EXEC-STR-009) |
| **2 Governance Pathways** | Claude Council (standard) + LLM Council (HIGH_IMPACT/HIGH_RISK) (INV-EXEC-STR-005) |
| **Project → Global → External** | Strict resolution hierarchy; no cross-scope leakage (INV-EXEC-STR-015) |
| **Deterministic Planning** | Pure function: `Plan = f(Intent, RegistrySnapshot, PolicySnapshot, ConfigSnapshot)` (INV-DET-1) |
| **Snapshot Isolation** | Atomic snapshots at pipeline start; no stage observes different version (INV-STRUCT-2) |
| **Manifest Pinning** | Exact versions with content hashes; no ranges or "latest" (INV-STRUCT-4) |
| **6 Required Artifacts** | Claude.md, Project Hooks, Execution Metadata, Capability Manifest, Execution Profile, Governance Manifest (INV-STRUCT-5) |
| **Human Override** | Synchronous hooks at every layer; acknowledgment ≤5s default (INV-EXEC-STR-013, INV-EXEC-RT-007) |
| **Learning Artifacts** | Must have provenance, confidence, versioning, rollback capability, namespace scope (INV-EXEC-STR-010) |
| **Optimization Policies** | Versioned, auditable, applied before subsequent planning (INV-EXEC-STR-011, INV-EXEC-RT-012) |
| **9-Stage Healing Pipeline** | Detect → Diagnose → RCA → Strategy Adaptation → Capability Substitution → Model Substitution → Workflow Adjustment → Recovery → Learning (INV-EXEC-STR-012) |

---

## 4. Terminology

| Term | Definition |
|------|------------|
| **Intent** | Raw user request or structured trigger |
| **AnalyzedIntent** | Decomposed, normalized intent with requirements, constraints, risks, governance |
| **IntentUnit** | Atomic capability need from decomposition |
| **Capability** | First-class architectural component with declared contract |
| **Capability Plan** | Executable data structure: capability graph + bindings + budgets + governance |
| **Execution Context** | Correlation-scoped environment bound to single execution |
| **Registry Snapshot** | Immutable view of Project/Global/External registries at pipeline start |
| **Policy Snapshot** | Immutable view of all policies at pipeline start |
| **Governance Gate** | Approval checkpoint (PRE_EXECUTION_APPROVAL, POST_EXECUTION_AUDIT, COMPLIANCE_CHECK, COST_GATE) |
| **Loop Iteration** | Single pass through a hierarchical loop with checkpoint |
| **Checkpoint** | Serializable execution state enabling deterministic restoration |
| **Learning Artifact** | Versioned, provenance-tracked improvement record with rollback |
| **Optimization Policy** | Synthesized policy for model/skill/workflow/retry/council/MCP/resource selection |
| **Healing Action** | One of 9 pipeline stages executed by Self-Healing Layer |

---

## 5. Naming Conventions

| Element | Convention |
|---------|------------|
| **Event Types** | `aios.planning.*`, `aios.execution.*`, `aios.loop.*`, `aios.learning.*`, `aios.optimization.*`, `aios.healing.*`, `aios.governance.*`, `aios.intervention.*` |
| **Component Identity** | `CapabilityDiscovery`, `CapabilityPlanner`, `ArtifactGenerator`, `ExecutionEngine`, `LoopEngine`, `LearningLayer`, `OptimizationLayer`, `HealingLayer`, `GovernanceRouter`, `InterventionHooks` |
| **Correlation ID** | UUIDv7 — links all events in single intent→execution flow |
| **Causation ID** | UUIDv7 — links event to its direct trigger |
| **Plan ID** | UUID — unique per `CapabilityPlan` |
| **Node ID** | UUID — unique per execution graph vertex |
| **Gate ID** | UUID — unique per governance gate |
| **Snapshot ID** | UUID — unique per Registry/Policy/Config snapshot triple |

---

## 6. Capability Model

**Capability Manifest Fields (Part 6):**
```json
{
  "capabilityId": "string",
  "version": "semver",
  "type": "CAPABILITY | SKILL",
  "source": "PROJECT | GLOBAL | EXTERNAL",
  "matchPatterns": ["glob"],
  "implements": ["interface"],
  "parameters": "JSON Schema",
  "outputs": "JSON Schema",
  "qos": { "latency", "availability", "reliability" },
  "dependsOn": ["capabilityId"],
  "reversible": "boolean",
  "compensation": { "capabilityId" | "restoreFrom" | "manual" },
  "provider": { "type", "region", "version" },
  "loop": { "type", "iterator", "condition", "maxIterations", "parallel", "breakOn" },
  "governance": { "approvalRequired", "complianceTags", "securityReview" },
  "costModel": { "minUSD", "maxUSD", "confidence" },
  "riskLevel": "LOW | MEDIUM | HIGH | CRITICAL"
}
```

**Resolution Priority (INV-DISC-1):**
1. PROJECT Registry
2. PROJECT Skill Registry
3. GLOBAL Registry
4. GLOBAL Skill Registry
5. EXTERNAL Registry (if policy allows)
6. EXTERNAL Skill Registry (if policy allows)

---

## 7. Planning Model

### Pipeline Stages (Pure Functions)
1. **Intent Analysis** → `AnalyzedIntent`
2. **Capability Resolution** → `ResolvedCapabilities[]`
3. **Dependency Resolution** → `CapabilityDAG`
4. **Plan Assembly** → `CapabilityPlan`
5. **Optimization Layer** (policy-gated) → Optimized `CapabilityPlan`
6. **Artifact Generation** → 6 artifacts

### CapabilityPlan Structure
```json
{
  "planId": "uuid",
  "version": "int",
  "intentId": "uuid",
  "correlationId": "uuid",
  "nodes": [{ "nodeId", "capabilityId", "version", "executionOrder", "parallelGroup", "dependencies", "dependencyTypes", "parameters", "condition", "optional", "reversible", "retryPolicy", "loopBinding", "providerRequirement", "governanceBindings", "resourceBudget", "costEstimate", "rollbackNode", "successCriteria", "failureCriteria", "confidence", "confidenceDecayFactors", "recommendationRefs" }],
  "parallelGroups": [{ "groupId", "nodes[]", "estimatedDurationMs" }],
  "conditionalBranches": [{ "guardNodeId", "condition", "thenNodes[]", "elseNodes[]" }],
  "governanceGates": [{ "gateId", "type", "nodes[]", "approvers[]", "timeout", "autoApprove" }],
  "aggregateBudget": { "maxCostUSD", "maxDurationMs", "contingency" },
  "overallRiskLevel": "LOW|MEDIUM|HIGH|CRITICAL",
  "overallConfidence": "0.0-1.0"
}
```

### Invariants (INV-PLAN-1 through INV-PLAN-9)
- DAG acyclicity
- Dependency completeness
- Deterministic topological ordering
- Parallel group independence
- Rollback completeness for irreversible nodes
- Loop boundedness (static maxIterations)
- Budget validity (≤ quotas)
- Governance satisfiability
- Traceability completeness

---

## 8. Execution Pipeline Overview (Layer Interaction)

```
Layer 1: Planning & Capability Discovery     → CAPABILITY_PLAN_READY
Layer 2: Provider Selection                  → EXECUTION_PROFILE_READY
Layer 3: Governance Gates                    → GOVERNANCE_APPROVED / GOVERNANCE_REQUIRED
Layer 4: Capability Execution                → CAPABILITY_FAILED / DEGRADED / LOOP_ITERATION_COMPLETE
Layer 5: Loop Engine                         → RETRY_STRATEGY_SELECTED / LOOP_ROLLBACK_INITIATED / CHECKPOINT_RESTORED
Layer 6: Learning Layer                      ← EXECUTION_OUTCOME → LEARNING_ARTIFACT_PUBLISHED
Layer 7: Optimization Layer                  ← LEARNING_BATCH_READY → OPTIMIZATION_POLICY_PUBLISHED
Layer 8: Self-Healing Layer                  ← ANOMALY_DETECTED → HEALING_ACTION_EXECUTED / RCA_COMPLETE
Layer 9: Human Intervention                  ← HUMAN_INTERVENTION_REQUESTED → INTERVENTION_OVERRIDE
```

**Layer Invariant (INV-EXEC-LAYER-003):** Layer ordering is architectural, not temporal. Layers execute concurrently for different correlation IDs.

---

## 9. Event Architecture Overview

### Event Envelope (Part 2)
| Field | Requirement |
|-------|-------------|
| eventId | UUIDv7 (time-ordered) |
| eventType | Namespaced: `aios.<subsystem>.*` |
| correlationId | Links all events for single flow |
| causationId | Links to triggering event |
| timestamp | ISO8601 with ns precision |
| source | Component identifier |
| version | Event schema version (semver) |
| payload | Type-specific |

### Event Categories (Planning + Execution)
| Category | Prefix | Ordering |
|----------|--------|----------|
| Intent Lifecycle | `aios.planning.intent.*` | Total per correlationId |
| Discovery | `aios.planning.discovery.*` | Total per correlationId |
| Planning | `aios.planning.plan.*` | Total per correlationId |
| Governance | `aios.planning.governance.*` | Total per correlationId |
| Artifacts | `aios.planning.artifact.*` | Total per correlationId |
| Control | `aios.planning.control.*` | Partial |
| Cache | `aios.planning.cache.*` | Partial |
| Memory | `aios.planning.memory.*` | Partial |
| Model Routing | `aios.planning.model.*` | Total per correlationId |
| AI Council | `aios.planning.council.*` | Total per councilId |
| Optimization | `aios.planning.optimization.*` | Total per correlationId |
| Self-Healing | `aios.planning.healing.*` | Total per correlationId |
| Confidence | `aios.planning.confidence.*` | Total per correlationId |
| Recommendation | `aios.planning.recommendation.*` | Partial |
| Loop Engine | `aios.planning.loop.*` | Total per correlationId |

**Invariants:**
- INV-EVT-1: All events in flow share correlationId
- INV-EVT-2: Causation graph acyclic, rooted at intent.received
- INV-EVT-3: Same-category events delivered in timestamp order per correlationId
- INV-EVT-4: Every FAILED transition emits *.failed event

---

## 10. State Model Overview

### Planning State Machine (Section 8.2.9)
```
IDLE → INTENT_RECEIVED → INTENT_ANALYSIS → DISCOVERY → VALIDATION → PLANNING 
    → [GOVERNANCE_REVIEW] → ARTIFACT_GENERATION → PLAN_READY → EXECUTION_READY
    ↘ FAILED (from any state)
```

**Terminal States:** `PLAN_READY` (success), `EXECUTION_READY` (handoff), `FAILED` (failure), `IDLE` (after cleanup)

### Execution State Machine (Section 8.3 — to be defined)
- Execution contexts are ephemeral, correlation-scoped
- Lifecycle bound to single execution unless explicitly persisted
- Checkpoint per loop iteration for recovery

### Loop Engine State (5 Hierarchical Loops)
Each loop has: Retry Budget, Rollback Target, Checkpoint, Timeout, Adaptive Strategy

| Loop | Rollback Target |
|------|-----------------|
| Research | Start |
| Planning | Research |
| Implementation | Planning |
| Testing | Implementation |
| Deployment | Testing |

---

## 11. Capability Artifacts (6 Required)

| Artifact | Purpose | Schema Ref |
|----------|---------|------------|
| **Claude.md** | Human-readable plan summary | §8.2.7.4 |
| **Project Hooks** | Executable lifecycle hooks | §8.2.7.5 |
| **Execution Metadata** | Runtime hints for scheduler/resources | §8.2.7.6 |
| **Capability Manifest** | Pinned resolved capability manifests | §8.2.7.7 |
| **Execution Profile** | Performance baselines, SLOs, tuning | §8.2.7.8 |
| **Governance Manifest** | Approval gates, compliance evidence, audit trail | §8.2.7.9 |

**Generation Invariants:**
- INV-ART-1: Deterministic — identical inputs → bit-identical artifacts
- INV-ART-2: All share `CapabilityPlan.version`
- INV-ART-3: All include SHA256(content)
- INV-ART-4: All record `generatedBy: "CapabilityPlanner/x.y.z"`
- INV-ART-5: Governance Manifest contains all triggers, evaluations, evidence

---

## 12. Capability Facades (Part 6)

**Interfaces used by Planning/Execution:**
- **Capability Registry** — query, search, get manifests
- **Skill Service** — load, validate, execute skills
- **MCP Service** — discover, connect, invoke MCP servers
- **Memory Service** — store/query learning artifacts, execution context
- **Council Service** — convene and manage council deliberations

**Key Contract:** Planning/Execution layers invoke capabilities **exclusively** through Capability Facade Services. No direct Core Manager access (INV-EXEC-STR-006).

---

## 13. Engineering Services (Part 5)

| Service | Role in Part 8 |
|---------|----------------|
| **Auth** | Validates permissions for registry access |
| **Observability** | Emits planning/execution metrics, traces, audit events |
| **Policy Engine** | Evaluates policy-as-code for every resolution decision |
| **Model Manager** | Provides model registry, routing hints, token budgets |
| **Resource Manager** | Validates resource budgets against quotas |

---

## 14. AI Council Integration

### Two Council Types
| Council | Trigger | Composition | Verdict |
|---------|---------|-------------|---------|
| **Claude Council** | Standard governance | Configured personas (Architect, Security, Perf, PO, User Advocate) | Quorum-based (≥3 default) |
| **LLM Council** | HIGH_IMPACT or HIGH_RISK | 3+ diverse models (reasoning, safety, cost) | Statistical consensus (≥2/3) |

### Invariants
- INV-AC-1: Deterministic given identical context/models
- INV-AC-2: Quorum enforced (≥2/3 ALLOW/DENY; split → ESCALATE)
- INV-AC-3: Full transcript immutable in Governance Manifest
- INV-AC-4: Model diversity mandatory (reasoning, safety, cost roles)

### Deliberation Protocol
1. TRIGGER: Policy requires APPROVAL or ambiguity > threshold
2. COMPOSITION: 3+ models selected by policy
3. DELIBERATION: Identical context to all models
4. VOTING: ALLOW / DENY / DEFER with rationale
5. QUORUM: ≥2/3 ALLOW → APPROVED; ≥2/3 DENY → REJECTED; else → HUMAN_ESCALATION
6. RECORD: Full transcript in Governance Manifest

---

## 15. Model Router Integration (Hermes Kernel Part 1 §1.4)

### Planning Subtasks Routed
| Subtask | Model Route |
|---------|-------------|
| Intent Classification | `planning/intent-classifier` |
| Risk Assessment | `planning/risk-assessor` |
| Capability Ranking | `planning/ranker` |
| Substitution Suggestion | `planning/substitution-advisor` |
| Governance Summarization | `planning/governance-summarizer` |
| Plan Optimization | `planning/optimizer` |

### Invariants
- INV-MR-1: All calls use temperature=0, fixed seed
- INV-MR-2: Every call records modelId, version, promptHash, responseHash, tokenUsage, latencyMs
- INV-MR-3: Total tokens/flow ≤ `planning.modelRouting.tokenBudget` (default 50k)
- INV-MR-4: Heuristic fallback deterministic and logged

---

## 16. Memory Integration

### Memory Managers (Core Manager M1)
- **Planning Memory** — cross-flow pattern reuse (successful patterns, substitutions, optimization memos, failure signatures)
- **Learning Artifacts Store** — outcome observations correlated with context
- **Optimization Policy Store** — versioned policies for model/skill/workflow/retry/council/MCP/resource

### Invariants
- INV-MEM-1: Read-only during pipeline; writes only at completion via `PlanningMemoryRecorded` event
- INV-MEM-2: Tenant-scoped; cross-tenant requires explicit policy opt-in
- INV-MEM-3: Every entry has sourceCorrelationId, successMetric, confidenceAtWrite
- INV-MEM-4: Bounded growth (maxEntries, maxAge TTL, LRU eviction)

---

## 17. Governance Principles

### Impact Classification (3 Levels)
| Level | Governance Pathway |
|-------|-------------------|
| **LOW** | No council; direct execution |
| **HIGH_IMPACT** | LLM Council (statistical consensus) |
| **HIGH_RISK** | LLM Council (statistical consensus) |

### Governance Gate Types
- **PRE_EXECUTION_APPROVAL** — before node/group execution
- **POST_EXECUTION_AUDIT** — after node/group execution
- **COMPLIANCE_CHECK** — before + after
- **COST_GATE** — before node/group

### Invariants
- INV-EXEC-GOV-001: Claude Council quorum mandatory (≥3 default)
- INV-EXEC-GOV-002: LLM Council ONLY for HIGH_IMPACT/HIGH_RISK or explicit human request
- INV-EXEC-GOV-003: Dissent recorded as `COUNCIL_DISSENT_REGISTERED` (AUDIT); triggers escalation if no quorum
- INV-EXEC-GOV-004: Governance decisions reversible via human ESCALATE override
- INV-EXEC-GOV-005: Capability plan MUST declare governance per capability; undeclared defaults to standard

---

## 18. Deterministic Replay Principles

### From Part 2 §2.11
- **Replay** = re-execution from captured event log + snapshots
- **Identical inputs** → **bit-for-bit identical capability invocation sequence**
- External side effects excluded from determinism guarantee

### Requirements for All Layers
- INV-EXEC-RT-009: All layers participate in deterministic replay
- INV-DET-3: Replay from recorded snapshots produces identical outputs
- INV-DET-2: No hidden inputs (no clocks, random values, ambient state)
- INV-DET-4: All tie-breaking deterministic (lexicographic ID, fixed priority)

### Replay Capture (CONF-REPLAY-1, CONF-REPLAY-2)
- Capture: Intent + RegistrySnapshot + PolicySnapshot + ConfigSnapshot + MetricsSnapshot + Output Plan/Artifacts
- Replay: Same code version (git commit), same snapshots, compare outputs bit-identical

---

## 19. Provider Independence

### Four Vendor Abstraction Boundaries (INV-EXEC-STR-014)
| Boundary | Manager | Supports |
|----------|---------|----------|
| **LLM** | LLMManager | Local, Cloud, Hybrid |
| **MCP** | MCPManager | Any MCP-compliant server |
| **Skill** | SkillManager | Any skill conforming to Skill Contract |
| **Council** | CouncilManager | Any council implementation |

### Invariants
- INV-PROV-1: Registry abstraction — discovery queries Capability Facade, not concrete implementations
- INV-PROV-2: External registry failures don't block Project/Global resolution
- INV-PROV-3: Planning assumes no specific provider; requirements declared in manifests
- INV-PROV-4: Capability manifests provider-agnostic; provider config in `providerRequirement` binding
- INV-EXEC-RT-010: Vendor interchange requires zero execution layer code changes

---

## 20. EventBus-First Architecture

### Core Principle (EXEC-P-003, INV-EXEC-LAYER-001)
**All execution coordination flows through EventBus.** No direct layer-to-layer method calls in RUNNING state.

### Communication Protocol
- Layer N → Layer N+1: Emits CONTROL/DATA events
- Layer N+1 → Layer N: Responds via events with causationId
- Cross-layer: Events only; no RPC, no shared memory, no direct invocations

### EventBus (Core Component C1, Part 1)
- Owned by Hermes Kernel
- Provides: publish, subscribe, correlation ordering, causation tracking
- Event categories: CONTROL, DATA, AUDIT, DIAGNOSTIC

---

## 21. Checkpoint Philosophy

### Purpose
Enable deterministic restoration for: retry, cross-loop rollback, self-healing recovery, deterministic replay.

### Checkpoint Points (Section 8.2.9.9)
| State Exit | Checkpoint Data |
|------------|-----------------|
| INTENT_ANALYSIS | AnalyzedIntent |
| DISCOVERY | ResolvedCapabilities |
| VALIDATION | ValidatedDependencyGraph |
| PLANNING | ExecutionGraph + Bindings |
| GOVERNANCE_REVIEW | Plan + Approvals |
| ARTIFACT_GENERATION | Partial Artifacts |
| LOOP_EXPANSION | ExpandedLoopSubgraph |
| AI_COUNCIL_DELIBERATION | CouncilTranscript (partial) |
| **Per Loop Iteration** | Full execution context |

### Invariants
- INV-EXEC-RT-011: Loop Engine maintains checkpoint per iteration; restoration reproduces identical context
- INV-STATE-5: Recovery from latest valid checkpoint produces identical forward progress
- INV-STATE-8: Loop iteration checkpoints enable recovery within loop body

---

## 22. Loop Architecture Assumptions

### Five Hierarchical Loops (Fixed)
1. **Research Loop** — rollback to Start
2. **Planning Loop** — rollback to Research
3. **Implementation Loop** — rollback to Planning
4. **Testing Loop** — rollback to Implementation
5. **Deployment Loop** — rollback to Testing

### Per-Loop Parameters
```json
{
  "retryBudget": "int",
  "rollbackTarget": "previous_loop_id",
  "checkpoint": "CheckpointRef",
  "timeoutMs": "int",
  "adaptiveStrategy": "StrategySpec"
}
```

### Strategy Hierarchy (on failure)
1. Parameter adjustment
2. Capability substitution
3. Model substitution
4. Workflow restructure
5. Escalation

### Mandatory Invariants
- INV-EXEC-STR-007: All five loops defined with required parameters
- INV-EXEC-STR-008: NEVER identical retry — strategy hash must differ per attempt
- INV-EXEC-STR-009: Exhaustion → rollback to previous loop (not termination)
- INV-LOOP-1: Static boundedness — maxIterations required positive integer
- INV-LOOP-2: Deterministic expansion
- INV-LOOP-3: No runtime graph mutation
- INV-LOOP-4: Checkpoint per iteration

---

## 23. Learning Layer Assumptions

### Scope
Observes: success/failure, latency, resource consumption, governance decisions, human interventions
Correlates with: capability set, input characteristics, environment state

### Produces Learning Artifacts Improving:
1. Workflow Selection
2. Capability Selection
3. Model Routing
4. Council Composition
5. Retry Policies
6. Skill Ranking
7. MCP Selection
8. Execution Planning
9. Failure Recovery
10. Prompt Optimization
11. Provider Selection
12. Council Effectiveness
13. Confidence Calibration
14. Environment Optimization

### Artifact Requirements (INV-EXEC-STR-010)
- Provenance (source correlationId, generator, timestamp)
- Confidence (0.0–1.0)
- Versioning (semantic)
- Rollback capability (registered procedure)
- Namespace scope (tenant/execution context)

### Invariants
- INV-EXEC-RT-005: Application reversible — every artifact has rollback procedure
- INV-EXEC-FL-003: No artifact application during active recovery (RETRY/HEALING/ROLLBACK in progress)
- CONF-FEEDBACK-1: Every execution produces metrics for next planning cycle
- CONF-FEEDBACK-2: Feedback incorporation deterministic
- CONF-FEEDBACK-3: Metrics available within 5 min default
- CONF-FEEDBACK-4: Updates never weaken invariants

---

## 24. Self-Healing Assumptions

### Nine-Stage Pipeline (Fixed)
1. **Detect** — ObservabilityManager metrics, EventBus diagnostics, capability heartbeats
2. **Diagnose** — Classify anomaly
3. **Root Cause Analysis** — Identify causal chain
4. **Strategy Adaptation** — Select healing action
5. **Capability Substitution** — Swap capability per Recommendation Graph
6. **Model Substitution** — Switch model provider
7. **Workflow Adjustment** — Restructure execution graph
8. **Recovery** — Restore execution
9. **Learning** — Emit healing record to Learning Layer

### Healing Actions (Not Limited to Restarts)
- Capability substitution
- Model substitution
- Workflow adjustment
- Strategic adaptation

### Constraints
- INV-EXEC-FL-004: Bounded attempts (default 3 per scope); excess → CRITICAL escalation
- INV-HEAL-4: Trigger → healed plan ≤ 30s default; timeout → escalate
- INV-HEAL-2: Healed plan satisfies ALL original invariants
- INV-HEAL-3: Full traceability to triggerEventId, originalPlanId, healingRuleId
- INV-HEAL-5: Healed plan passes Replay Verification

### Trigger Sources
- Execution: timeout, cost overrun >20%, latency p99 >2× estimate
- Environment: registry unavailable, capability deprecated
- Planning: partial discovery, ambiguous resolution

---

## 25. Optimization Assumptions

### Seven Optimization Domains (Fixed)
1. Best Model
2. Best Skills
3. Best Workflow
4. Best Retry Strategy
5. Best Councils
6. Best MCP Combinations
7. Resource Optimization

### Architecture (Layer 7)
**Learning Evaluator** → **Policy Synthesizer** → **Optimization Applicator** → **Optimization Policy Store** (MemoryManager)

### Process (Policy-Gated, Deterministic)
1. Load hints from Planning Memory
2. Generate candidate optimizations per enabled type
3. Score using Execution Profile + historical effectiveness
4. Select top candidates (max 3 per plan)
5. Apply producing new Plan'
6. Verify ALL invariants hold
7. Emit `PlanOptimized` with before/after metrics

### Invariants
- INV-OPT-1: Safety — violation of ANY invariant → auto-reject
- INV-OPT-2: Determinism — identical inputs → identical decisions
- INV-OPT-3: Traceability — every optimization recorded with before/predicted/evidence
- INV-OPT-4: Budget — max 3 optimizations, ≤10s default

### Optimization Types (Policy-Gated)
| Type | Policy Gate | Validates |
|------|-------------|-----------|
| Cost Substitution | `planning.optimization.allowCostSubstitution` | Budget, contracts |
| Parallelism Tuning | `planning.optimization.allowParallelismTuning` | PLAN-4, budget |
| Latency Reordering | `planning.optimization.allowLatencyReordering` | Topological, data deps |
| Risk Mitigation | `planning.optimization.allowRiskMitigation` | PLAN-5, gates unchanged |
| Resource Right-Sizing | `planning.optimization.allowResourceRightSizing` | Provider capacity, budget |

---

## 26. Architectural Invariants (Consolidated Reference)

### Structural (INV-EXEC-STR-001 through INV-EXEC-STR-015)
- 9 layers fixed; Service/Core Manager implementation; Capability Discovery Layer mandatory; 6 artifacts; dual governance; Capability Facade only; 5 loops with params; strategic retry; cross-loop rollback; learning artifacts with provenance/confidence/versioning/rollback/namespace; optimization policies versioned/auditable; 9-stage healing; human hooks at every layer; vendor logic encapsulated; Project→Global→External resolution

### Runtime (INV-EXEC-RT-001 through INV-EXEC-RT-012)
- 100% event coverage; discovery before invocation; governance before invocation; strategy hash differs per retry; learning reversible; healing emits AUDIT; human override suspends within bound; resource budgets enforced at invocation; replay determinism; vendor swap zero code changes; checkpoint restoration reproduces context; optimization policies fresh

### Failure (INV-EXEC-FL-001 through INV-EXEC-FL-005)
- Classification before retry; loop exhaustion → cross-loop rollback; no learning during recovery; healing bounded; human can terminate any in-flight with compensation

### Governance (INV-EXEC-GOV-001 through INV-EXEC-GOV-005)
- Quorum enforced; LLM Council gated; dissent recorded + escalation; reversible via human; governance declared per capability

### Discovery/Planning/Resolution/Cache/Memory/Model/Council/Skill/Optimization/Healing/Artifact/Determinism/StateMachine/Event/Provider/Human — see Sections 8.2.11.1 through 8.2.11.11

---

## 27. JSON Schema Conventions

- All schemas use JSON Schema Draft 2020-12
- Version field: `"schemaVersion": "1.0.0"` (semver)
- IDs: UUIDv7 strings (`"format": "uuid"`)
- Timestamps: ISO8601 with nanoseconds (`"format": "date-time"`)
- Confidence: `"type": "number", "minimum": 0.0, "maximum": 1.0`
- Enums: PascalCase values (`"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"`)
- Content hashes: `"sha256:<hex>"`
- All artifacts include: `version`, `contentHash`, `generatedBy`, `timestamp`
- Event envelopes include: `eventId`, `eventType`, `correlationId`, `causationId`, `timestamp`, `source`, `version`, `payload`

---

## 28. Mermaid Diagram Conventions

| Element | Style |
|---------|-------|
| **Layers** | `┌────────────────┐` boxes with layer name |
| **Flow** | `│` vertical, `▼` down, `◄────` EventBus feedback |
| **Stage Pipelines** | Horizontal `┌──┐ ──▶ └──┘` with cross-cutting concerns box below |
| **State Machines** | `┌─────┐` states, `▶` transitions, `└────┘` sub-states indented |
| **Graphs** | DAG with `nodeId`, `edgeType` labels |
| **Color/Style** | ASCII-only; no Mermaid-specific syntax; monospace aligned |

---

## 29. RFC-2119 Conventions

| Keyword | Meaning |
|---------|---------|
| **MUST** | Absolute requirement; violation = non-conformant |
| **MUST NOT** | Absolute prohibition |
| **SHOULD** | Recommended; deviation requires justification |
| **SHOULD NOT** | Discouraged; allowed only with justification |
| **MAY** | Optional; implementation choice |

All conformance criteria use RFC-2119 language. "Invariants" are MUST-level requirements.

---

## 30. Cross-Reference Conventions

| Reference Format | Example |
|------------------|---------|
| **Part/Section** | Part 1 §1.3, Part 2 §2.11, Part 6 §6.2 |
| **Invariant** | INV-EXEC-STR-001, INV-DISC-1, INV-PLAN-4 |
| **Event** | `aios.planning.discovery.capability_resolved` |
| **State** | `PLANNING`, `DISCOVERY`, `FAILED` |
| **Artifact** | `Claude.md`, `Governance Manifest` |
| **Table Row** | `| Research Loop | Rollback → Start |` |

---

## 31. Remaining Part 8 Roadmap

| Section | Title | Key Deliverables |
|---------|-------|------------------|
| **8.3** | Execution Context & Plan Architecture | ExecutionContext model, CapabilityPlan binding, ExecutionContextManager, resource budgets, checkpoint hooks |
| **8.4** | Council Governance Architecture | CouncilManager, Claude Council protocol, LLM Council protocol, impact classifier, escalation paths |
| **8.5** | Loop Engine Architecture | LoopEngine, RetryManager, 5 loop specs, strategy hierarchy, cross-loop rollback, checkpoint integration |
| **8.6** | Learning Layer Architecture | LearningService, OutcomeObserver, ArtifactGenerator, ArtifactStore, provenance/confidence/versioning/rollback/namespace |
| **8.7** | Optimization Layer Architecture | OptimizationService, LearningEvaluator, PolicySynthesizer, OptimizationApplicator, 7 domain policies |
| **8.8** | Self-Healing Layer Architecture | HealingService, 9-stage pipeline, detector/diagnosis/RCA/strategy/substitution/recovery/learning |
| **8.9** | Human Intervention Architecture | InterventionHookRegistry, OverrideExecutor, StatePreservation, 5 intervention types, ≤5s yield |
| **8.10** | Vendor Independence Architecture | 4 abstraction boundaries, adapter contracts, pluggability conformance, local/cloud/hybrid parity |
| **8.11** | Provider Selection Architecture | ModelSelector, RoutingPolicyEngine, CouncilSelector, ExecutionProfileResolver, intelligent routing |
| **8.12** | Execution Conformance | Static (L1), Runtime (L2), Integration (L3), Failure Injection (L4), Replay (L5), Audit (L6), Performance (L7) |

---

END OF PART8_CONTEXT.md