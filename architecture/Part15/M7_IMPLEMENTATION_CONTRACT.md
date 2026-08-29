# M7 — Terminal 1 Implementation Contract (Frozen)

**Project:** AI-OS V2
**Milestone:** M7 — Multi-Perspective Testing & User Simulation
**Predecessor:** M6 (Council Synthesis & Self-Prompting) — PASS, 98/100 QA
**Status:** FROZEN SCOPE — ready for Terminal 2 execution
**Date:** 2026-08-24
**Authority:** FINAL_AI_OS_V2_ARCHITECTURE.md (authoritative), M4/M5/M6 dependency docs

---

## 1. OBJECTIVE

M7 delivers the complete V2 multi-perspective testing and user simulation realization. Every `BaseAgency.review()` in V1 is currently a heuristic/string-matching placeholder. M7 replaces those with real execution behind existing seams, adding the `UserSimulationAgent` (10th perspective), structured `TestingEvidence` schema, `TestOrchestratorService` (extends `WorkflowManager`), `FinalJudgeAgency` independent verdict, `SimplificationGate`, isolation/sandbox, adversarial security integration, and closed-loop retest. M7 is the **final V2 milestone** — no M8+ is defined in the authoritative architecture.

---

## 2. FROZEN M7 SCOPE

### 2.1 M7 Sub-Tasks (Internal Order)

| ID | Component | Classification | Description |
|----|-----------|---------------|-------------|
| **M7-A** | `TestingEvidence` schema | MUST IMPLEMENT | Typed dataclass replacing loose `findings[]` dicts |
| **M7-B** | `TestOrchestratorService` | MUST IMPLEMENT | Extends `WorkflowManager` — plan→dispatch→collect→normalize→critique |
| **M7-C** | Real agency execution | MUST IMPLEMENT | Replace 9 V1 heuristic stubs with real execution adapters |
| **M7-D** | `UserSimulationAgent` | MUST IMPLEMENT | 10th perspective — discovery-first, goal-driven via `hermes-agent`(EXT) ACP |
| **M7-E** | Isolation/Sandbox | MUST IMPLEMENT | Builder env ≠ Tester env; builder excluded from TestingCouncil |
| **M7-F** | Testing Council `critique()` | MUST IMPLEMENT | Anonymized cross-ranking + dissent + dissenter-override (reuses M6) |
| **M7-G** | `FinalJudgeAgency` verdict | MUST IMPLEMENT | Independent APPROVE/REJECT/CONDITIONAL verdict |
| **M7-H** | Adversarial/Security | MUST IMPLEMENT | SkillSpecTor gate + Trail of Bits + agency-agents pentester |
| **M7-I** | Closed-loop integration | MUST IMPLEMENT | FAIL→RCA→Learning→Replan→Re-execute→Retest (reuses M3/M6) |
| **M7-J** | `SimplificationGate` + seeded defects | MUST IMPLEMENT | Pre-acceptance complexity gate; 9 seeded defects detected; all 17 acceptance criteria pass |

### 2.2 Dependencies on Prior Milestones

| Dependency | Delivered By | M7 Reuse |
|-----------|-------------|----------|
| `CouncilManager` + 5 consensus algos | M4 (via M6 critique extension) | §6.1 — TestingCouncil membership, dissent |
| `CouncilManager.critique()` (KKC/EVC) | M6 | §6.2 — anonymized cross-ranking, dissenter-override |
| `LLMCouncil` façade (6 roles) | M6 | §6.3 — reasoning domain only; NOT reused for TestingCouncil |
| `SelfPromptingService` (bounded) | M6 | §6.4 — bounded self-questioning; NOT reused for TestingCouncil flow |
| `AIAgencyService` + 9 agencies | V1 | §6.5 — extend `review()` methods with real execution |
| `WorkflowManager` | V1 | §6.6 — `TestOrchestratorService` extends |
| `SecurityManager` + `SkillSpecTorGate` | M4/M5 | §6.7 — security gate for skills; NOT decision authority |
| `RootCauseAnalyzer` | V1/M3 | §6.8 — failure classification for closed loop |
| `LearningService` | V1/M3 | §6.9 — pattern capture from failures |
| `PlanningService` | V1 | §6.10 — replan after RCA |
| `ModelRouter` | V1 | §6.11 — model selection for agency LLM calls |
| `HermesBridge` | M5 | §6.12 — `hermes-agent`(EXT) ACP bridge for UserSimulationAgent |
| `EventType` enum (121 members) | V1 | §6.13 — reuse existing types; do NOT invent new |
| Canonical `EventBus` (C1) | V1 | §6.14 — all emissions via single bus |

---

## 3. COMPONENT CLASSIFICATION

### 3.1 MUST IMPLEMENT IN M7 (New Code)

| # | Component | File | Description |
|---|-----------|------|-------------|
| 1 | `TestingEvidence` | `src/aios/core/testing_evidence.py` | Typed dataclass: perspective, target, test_id, actions[], observations[], expected, observed, severity, confidence, proof[], provenance(source/worker/session/ts/env), environment, timestamp, reproducibility, verdict |
| 2 | `UserSimulationCompleted` | `src/aios/core/testing_evidence.py` | Extension schema: goal_completion_pct, workflow_success, usability_blockers[], confusing_states[], navigation_failures[], missing_feedback[], invalid_input_handling[], recovery_behavior, expected_vs_observed |
| 3 | `TestOrchestratorService` | `src/aios/services/testing.py` | Extends `WorkflowManager`; adds test-specific workflow registration, per-perspective step handlers, evidence normalization, provenance preservation, council submission, retest coordination |
| 4 | `UserSimulationAgent` | `src/aios/core/user_simulation_agent.py` | 10th perspective; receives app_url/target + user_goal + exploration_brief; NO source code access; drives `hermes-agent`(EXT) via ACP; returns `UserSimulationCompleted` |
| 5 | `SimplificationGate` | `src/aios/core/simplification_gate.py` | Mandatory pre-acceptance complexity governance; blocks over-engineered implementations |
| 6 | Real agency execution adapters | `src/aios/adapters/` (new) | Replace each V1 `BaseAgency.review()` heuristic with real execution |

### 3.2 MAY MODIFY ONLY IF REQUIRED BY M7

| # | File | Change |
|---|------|--------|
| 1 | `src/aios/core/ai_agency.py` | Extend `AgencyRequest`/`AgencyResponse` to support `TestingEvidence` fields; wire real execution into 9 agency `review()` methods |
| 2 | `src/aios/core/kernel.py` | Register `TestOrchestratorService`, `UserSimulationAgent`, `SimplificationGate`; wire `FinalJudgeAgency` with real verdict logic |
| 3 | `src/aios/core/__init__.py` | Export new M7 components |
| 4 | `src/aios/services/__init__.py` | Export `TestOrchestratorService` |
| 5 | `src/aios/events/core/types.py` | Add M7-specific EventType members ONLY if none of existing 121 cover them (prefer reuse) |

### 3.3 ALREADY EXISTS — MUST BE REUSED (No Modification)

| # | Component | File | M7 Usage |
|---|-----------|------|----------|
| 1 | `CouncilManager` | `core/council_manager.py` | TestingCouncil convene/critique/synthesize |
| 2 | `CouncilManager.critique()` | `core/council_manager.py:524` | KKC anonymized cross-ranking, EVC dissenter-override |
| 3 | `LLMCouncil` | `core/llm_council.py` | Reasoning domain only (NOT TestingCouncil) |
| 4 | `SelfPromptingService` | `services/self_prompting.py` | Bounded self-questioning (NOT TestingCouncil flow) |
| 5 | `AIAgencyService` | `core/ai_agency.py:548` | Agency registry and dispatch |
| 6 | 9 `BaseAgency` subclasses | `core/ai_agency.py:161-504` | Extend `review()` with real execution |
| 7 | `FinalJudgeAgency` | `core/ai_agency.py:507` | Replace simulated with real verdict aggregation |
| 8 | `WorkflowManager` | `core/workflow.py` | Base for `TestOrchestratorService` |
| 9 | `SecurityManager` | `core/security_manager.py` | Final security authority; SkillSpecTor integration |
| 10 | `SkillSpecTorGate` | `core/security_manager.py:194` | Skill validation gate (integration gate, not authority) |
| 11 | `ModelRouter` | `core/model_router.py` | Model selection for agency LLM calls |
| 12 | `HermesBridge` | `adapters/hermes_bridge.py` | `hermes-agent`(EXT) ACP communication |
| 13 | `RootCauseAnalyzer` | `core/root_cause.py` | Failure analysis for closed loop |
| 14 | `LearningService` | `services/learning.py` | Pattern capture from RCA |
| 15 | `PlanningService` | `services/planning.py` | Replan after RCA |
| 16 | `EventType` (121 members) | `events/core/types.py` | Reuse existing; no new types unless gap is unfillable |
| 17 | Canonical `EventBus` | `events/core/bus.py` | Single event bus for all emissions |
| 18 | `TestingService` (stub) | `services/testing.py:29` | Replace with `TestOrchestratorService` |

### 3.4 EXPLICITLY FORBIDDEN IN M7

| # | Forbidden Item | Rationale |
|---|---------------|-----------|
| 1 | Second `CouncilManager` instance/facade for testing | Single canonical council system (C5 resolved) |
| 2 | Second orchestrator service (duplicate of `WorkflowManager`) | ADR #4 — `TestOrchestratorService` extends, never duplicates |
| 3 | `hermes-agent`(EXT) as final decision maker | External-worker principle: workers execute, AI-OS decides |
| 4 | Native AI-OS browser / in-house browser farm | Architecture forbids; use `hermes-agent`(EXT) only |
| 5 | Source-code access for `UserSimulationAgent` | INV-008: agent gets app purpose/goal only |
| 6 | Builder self-approval in TestingCouncil | INV-009: builder excluded from own target's council |
| 7 | Imported Karpathy/evisoft council subsystems | KKC/EVC are techniques, not vendored code |
| 8 | Uncontrolled recursive loops | All recursion bounded (ADR #10) |
| 9 | Second `ModelRouter` instance | Single canonical ModelRouter |
| 10 | Second skill format (non-Vercel `SKILL.md`) | Vercel `SKILL.md` is canonical |
| 11 | `VerificationService` (does not exist, must not be created) | Architecture C2 note: gates exist in existing components |
| 12 | New `EventType` values without gap analysis | 121 existing types; prefer reuse |

### 3.5 RESERVED FOR M8+ (Do NOT Implement)

| # | Reserved Item | Rationale |
|---|--------------|-----------|
| 1 | Production hardening / SLA contracts | Post-V2 |
| 2 | Autonomous evolution / self-improvement beyond closed loop | Post-V2 |
| 3 | Additional deployment pipelines | Post-V2 |
| 4 | MOA synthesis (multi-operator agent) as opt-in | Future enhancement |
| 5 | Caveman compression | Future enhancement |
| 6 | Second AI-OS kernel | Architecture invariant: ONE kernel |
| 7 | Notion integration (C4 — adopted-or-dropped decision pending) | C4 unresolved |
| 8 | Native graphify knowledge graph operations beyond MCP bridge | M5 boundary |

---

## 4. REQUIRED FILES TO CREATE

```
src/aios/core/testing_evidence.py          # TestingEvidence + UserSimulationCompleted schemas
src/aios/core/user_simulation_agent.py     # UserSimulationAgent (10th perspective)
src/aios/core/simplification_gate.py       # SimplificationGate
src/aios/adapters/security_agency_adapter.py    # Real SecurityAgency execution
src/aios/adapters/performance_agency_adapter.py # Real PerformanceAgency execution
src/aios/adapters/chaos_agency_adapter.py         # Real ChaosAgency execution
src/aios/adapters/accessibility_agency_adapter.py # Real AccessibilityAgency execution
src/aios/adapters/documentation_agency_adapter.py # Real DocumentationAgency execution
src/aios/adapters/concurrency_agency_adapter.py   # Real ConcurrencyAgency execution
src/aios/adapters/bug_hunter_agency_adapter.py    # Real BugHunterAgency execution
src/aios/adapters/architecture_agency_adapter.py  # Real ArchitectureAgency execution
tests/unit/test_testing_evidence.py
tests/unit/test_test_orchestrator.py
tests/unit/test_user_simulation_agent.py
tests/unit/test_simplification_gate.py
tests/unit/test_agency_adapters.py
tests/unit/test_final_judge_agency.py
tests/unit/test_m7_closed_loop.py
tests/integration/test_m7_multi_perspective.py
tests/integration/test_m7_isolation.py
tests/integration/test_m7_evidence_integrity.py
tests/integration/test_m7_seeded_defects.py
```

---

## 5. EXISTING FILES ALLOWED TO MODIFY

| File | Allowed Change |
|------|---------------|
| `src/aios/core/ai_agency.py` | Extend `AgencyRequest`/`AgencyResponse` for TestingEvidence; wire real execution into 9 agency `review()` methods |
| `src/aios/core/kernel.py` | Register new services/managers; wire `FinalJudgeAgency` real verdict |
| `src/aios/core/__init__.py` | Export new M7 components |
| `src/aios/services/testing.py` | Replace stub `TestingService` with `TestOrchestratorService` extending `WorkflowManager` |
| `src/aios/services/__init__.py` | Export `TestOrchestratorService` |
| `src/aios/__init__.py` | Export new top-level components |
| `src/aios/events/core/types.py` | Add M7 EventTypes ONLY after exhausting existing 121-type reuse |

---

## 6. PROTECTED FILES (NO MODIFICATIONS)

| File | Reason |
|------|--------|
| `src/aios/core/council_manager.py` | M6 complete; M7 calls `critique()` but does not modify it |
| `src/aios/core/llm_council.py` | M6 complete; reasoning domain only |
| `src/aios/services/self_prompting.py` | M6 complete; separate from TestingCouncil |
| `src/aios/core/security_manager.py` | M4/M5 complete; M7 integrates via gate calls |
| `src/aios/core/model_router.py` | M1/V1 complete; M7 routes through it |
| `src/aios/core/root_cause.py` | V1 complete; M7 consumes RCA output |
| `src/aios/services/learning.py` | V1 complete; M7 emits Learning events |
| `src/aios/core/workflow.py` | V1 complete; M7 extends via TestOrchestratorService |
| `src/aios/events/core/types.py` | Protected unless gap analysis proves addition required |
| `src/aios/events/core/bus.py` | Protected; single bus invariant |
| `src/aios/core/mcp_manager.py` | M5 complete; M7 uses via HermesBridge |
| `src/aios/adapters/hermes_bridge.py` | M5 complete; M7 consumes, does not modify |

---

## 7. REQUIRED INTERFACES / CLASSES / METHODS

### 7.1 `TestingEvidence` (dataclass)

```python
@dataclass
class TestingEvidence:
    perspective: str           # Agency name or "user_simulation"
    target: str                # What was tested
    test_id: str               # Unique identifier
    actions: list[dict]        # Actions taken during test
    observations: list[dict]   # Raw observations
    expected: str              # What was expected
    observed: str              # What was actually observed
    severity: str              # "critical"|"high"|"medium"|"low"
    confidence: float          # 0.0-1.0
    proof: list[str]           # Proof artifacts (screenshots, logs, traces)
    provenance: dict           # {source, worker, session, timestamp, environment}
    environment: dict          # Test environment details
    timestamp: datetime
    reproducibility: float     # 0.0-1.0
    verdict: str               # "pass"|"fail"|"inconclusive"
```

### 7.2 `UserSimulationCompleted` (dataclass)

```python
@dataclass
class UserSimulationCompleted:
    goal: str
    goal_completion_pct: float       # 0.0-1.0
    workflow_success: bool
    usability_blockers: list[str]
    confusing_states: list[str]
    navigation_failures: list[str]
    missing_feedback: list[str]
    invalid_input_handling: list[str]
    recovery_behavior: str
    expected_vs_observed: list[dict]
    raw_trace: dict                  # Full hermes-agent(EXT) trace
    timestamp: datetime
```

### 7.3 `TestOrchestratorService` (extends WorkflowManager)

```python
class TestOrchestratorService(WorkflowManager):
    async def orchestrate_test(
        self,
        objective: str,
        objective_id: str,
        target: str,
        perspectives: list[str],
        builder_id: str,
    ) -> TestingResult:
        """Plan → dispatch → collect → normalize → submit to council."""

    async def dispatch_perspective(
        self,
        perspective: str,
        target: str,
        correlation_id: str,
    ) -> TestingEvidence:
        """Execute a single perspective's testing and return normalized evidence."""

    def normalize_evidence(
        self,
        raw_response: AgencyResponse | UserSimulationCompleted,
        perspective: str,
        target: str,
    ) -> TestingEvidence:
        """Normalize any raw agency output into TestingEvidence schema."""

    async def submit_to_testing_council(
        self,
        evidence_list: list[TestingEvidence],
        builder_id: str,
    ) -> CritiqueResult:
        """Submit normalized evidence to CouncilManager.critique()."""

    async def coordinate_retest(
        self,
        failed_evidence: list[TestingEvidence],
        correlation_id: str,
    ) -> list[TestingEvidence]:
        """Re-execute failed perspectives and return updated evidence."""
```

### 7.4 `UserSimulationAgent`

```python
class UserSimulationAgent:
    async def simulate(
        self,
        app_url: str,
        user_goal: str,
        exploration_brief: str,
    ) -> UserSimulationCompleted:
        """Discovery-first user simulation via hermes-agent(EXT)."""
        # NO source code access
        # Returns UserSimulationCompleted, not a verdict
```

### 7.5 `SimplificationGate`

```python
class SimplificationGate:
    async def evaluate(
        self,
        implementation: str,
        test_evidence: list[TestingEvidence],
    ) -> GateResult:
        """Return PASS/FAIL with complexity findings."""
```

### 7.6 `FinalJudgeAgency.review()` extension

```python
# In core/ai_agency.py — extend FinalJudgeAgency:
async def review(self, request: AgencyRequest) -> AgencyResponse:
    # Aggregate TestingEvidence from all perspectives
    # Return APPROVE/REJECT/CONDITIONAL based on evidence
    # Builder MUST NOT be in evidence source
```

---

## 8. REQUIRED CONTROL FLOW

```
[TEST OBJECTIVE]
    │
    ▼
[TestOrchestratorService.orchestrate_test()]
    │  objective, objective_id, target, perspectives, builder_id
    ▼
[PLAN] — workflow registration, perspective dispatch order
    │
    ▼
[DISPATCH — parallel per perspective]
    ├── SecurityAgency.review()         → TestingEvidence (real adapter)
    ├── PerformanceAgency.review()      → TestingEvidence (real adapter)
    ├── ChaosAgency.review()            → TestingEvidence (real adapter)
    ├── AccessibilityAgency.review()    → TestingEvidence (real adapter)
    ├── DocumentationAgency.review()    → TestingEvidence (real adapter)
    ├── ConcurrencyAgency.review()      → TestingEvidence (real adapter)
    ├── BugHunterAgency.review()        → TestingEvidence (real adapter)
    ├── ArchitectureAgency.review()     → TestingEvidence (real adapter)
    └── UserSimulationAgent.simulate()  → UserSimulationCompleted → TestingEvidence
    │
    ▼
[NORMALIZE] — TestOrchestratorService.normalize_evidence() for each result
    │  All outputs → TestingEvidence schema with provenance
    ▼
[COLLECT] — list[TestingEvidence]
    │
    ▼
[TESTING COUNCIL] — CouncilManager.convene()
    │  Members: 9 agency perspectives + UserSimulationAgent
    │  Builder EXCLUDED (INV-009)
    ▼
[STAGE 1 — Independent Proposals] — each perspective submits blind
    │
    ▼
[STAGE 2 — Critique] — CouncilManager.critique()  [REUSES M6]
    │  anonymized cross-ranking (KKC)
    │  dissenter override (EVC)
    │  dissent preserved as metadata
    ▼
[STAGE 3 — Synthesis] — CouncilManager.synthesize(critique=...)  [REUSES M6]
    │
    ▼
[FINAL JUDGE] — FinalJudgeAgency.review(evidence=list[TestingEvidence])
    │  verdict: APPROVE | REJECT | CONDITIONAL
    │  builder excluded from evidence source
    ▼
[VERIFICATION GATE] — SimplificationGate.evaluate() if APPROVE
    │
    ▼
[PASS] → TESTING_COMPLETED event
    [REJECT/CONDITIONAL] → FAIL path
    │
    ▼
[CLOSED LOOP] — RootCauseAnalyzer → LearningService → PlanningService
    │  → WorkflowManager (re-execute) → TestOrchestratorService (retest)
    │  bounded by: iteration cap, token budget, convergence check, regression guard
    ▼
[RETEST] → back to DISPATCH
```

---

## 9. REQUIRED DATA FLOW

### 9.1 Evidence Flow

```
Agency.review() or UserSimulationAgent.simulate()
    │
    ├── raw output: AgencyResponse (dict findings[])
    │             OR UserSimulationCompleted (structured)
    │
    ▼
TestOrchestratorService.normalize_evidence()
    │
    ├── strips: loose dict structure, unprovenanced data
    ├── builds: TestingEvidence dataclass with all required fields
    ├── attaches: provenance{source, worker, session, ts, env}
    └── sets: verdict from agency output
    │
    ▼
list[TestingEvidence] → CouncilManager.critique()
    │
    ▼
CritiqueResult → CouncilManager.synthesize()
    │
    ▼
CouncilDecision → FinalJudgeAgency.review()
    │
    ▼
Verdict (APPROVE/REJECT/CONDITIONAL) + TestingEvidence audit trail
```

### 9.2 Event Flow

```
orchestrate_test() starts    → WORKFLOW_STARTED (existing)
perspective dispatch starts  → WORKFLOW_STEP_STARTED (existing)
evidence collected           → TESTING_COMPLETED / TESTING_FAILED (existing)
council convened             → COUNCIL_CONVENED (existing)
critique runs                → COUNCIL_DISSENT_REGISTERED (existing)
synthesize runs              → COUNCIL_DECISION_FINALIZED (existing)
final judge verdict          → TESTING_COMPLETED (existing)
closed loop fails            → WORKFLOW_FAILED (existing) → RCA → LEARNING_* events
```

---

## 10. SECURITY REQUIREMENTS

### 10.1 Security Gates (in order)

| Gate | Component | Authority | M7 Action |
|------|-----------|-----------|-----------|
| 1 | `SecurityManager` | **FINAL** | All external worker calls routed through SecurityManager authorization |
| 2 | `SkillSpecTorGate` | Integration gate (NOT final) | Validate any new skills/adapters before use |
| 3 | Builder exclusion | INV-009 | TestingCouncil MUST exclude builder from membership |
| 4 | External worker isolation | External-worker principle | `hermes-agent`(EXT) returns observations only; no verdict authority |
| 5 | No new EventType creation | C1 invariant | Reuse existing 121 EventTypes |
| 6 | Single EventBus | C1 invariant | All emissions via canonical bus |
| 7 | Single SecurityManager | Invariant | M7 does not create parallel security authority |

### 10.2 Trust Boundaries

```
┌─────────────────────────────────────────────────────┐
│ AI-OS Kernel (trusted)                              │
│  • TestOrchestratorService                          │
│  • CouncilManager (TestingCouncil)                  │
│  • FinalJudgeAgency                                 │
│  • SimplificationGate                               │
│  • SecurityManager (final authority)                │
└─────────────────────────────────────────────────────┘
                      │
                      │ ACP/MCP (untrusted channel)
                      ▼
┌─────────────────────────────────────────────────────┐
│ External Workers (UNTRUSTED — observations only)    │
│  • hermes-agent(EXT) — browser user simulation      │
│  • Playwright MCP — deterministic browser tests      │
│  • Agency adapters — real execution                 │
└─────────────────────────────────────────────────────┘
```

**Rule:** External outputs = untrusted observations until AI-OS normalizes to `TestingEvidence`.

---

## 11. EVENT REQUIREMENTS

### 11.1 Reuse Existing EventTypes (NO NEW TYPES unless gap is unfillable)

| Phase | EventType | Source |
|-------|-----------|--------|
| Test orchestration start | `WORKFLOW_STARTED` | TestOrchestratorService |
| Perspective dispatch | `WORKFLOW_STEP_STARTED` | TestOrchestratorService |
| Evidence collection | `TESTING_COMPLETED` | TestOrchestratorService / FinalJudgeAgency |
| Test failure | `TESTING_FAILED` | TestOrchestratorService |
| Council convened | `COUNCIL_CONVENED` | CouncilManager |
| Dissent registered | `COUNCIL_DISSENT_REGISTERED` | CouncilManager.critique() |
| Decision finalized | `COUNCIL_DECISION_FINALIZED` | CouncilManager.synthesize() |
| Workflow step failed | `WORKFLOW_STEP_FAILED` | TestOrchestratorService |
| Workflow failed | `WORKFLOW_FAILED` | Closed loop |
| Learning captured | `LEARNING_*` (existing legacy) | LearningService |
| Security issue | `SECURITY_ISSUE_FOUND` | SecurityManager / SkillSpecTor |

### 11.2 EventType Addition Rules

1. Check all 121 existing types first
2. If no suitable existing type covers the semantic, add to `EventType` enum
3. Document the new type in `events/core/types.py` with category, version, and description
4. Emit via canonical `EventBus` only — never bypass

---

## 12. EVIDENCE / PROVENANCE REQUIREMENTS

### 12.1 TestingEvidence Integrity Rules

1. **Every evidence item MUST have provenance** — source, worker, session, timestamp, environment
2. **Builder origin is excluded** from evidence that reaches FinalJudgeAgency
3. **Provenance chain must be unbroken** — no orphaned evidence
4. **Evidence is immutable once normalized** — no post-hoc modification
5. **Reproducibility score** must be attached to every evidence item
6. **Proof artifacts** (screenshots, logs, traces) must be referenced, not embedded

### 12.2 Provenance Schema

```python
provenance = {
    "source": "security_agency|performance_agency|...|user_simulation",
    "worker": "hermes_agent_ext|playwright|local|mock",
    "session": "hermes_<uuid>|<session_id>",
    "timestamp": "ISO8601",
    "environment": {"os": "...", "python": "...", "target": "..."},
    "correlation_id": "<uuid>",
    "test_id": "<uuid>",
}
```

---

## 13. INTEGRATION REQUIREMENTS

### 13.1 EventBus Integration

- All M7 components emit events via `get_core_event_bus()` (C1)
- No direct event bus bypass
- Event correlation IDs preserved through the entire test flow

### 13.2 ModelRouter Integration

- Each agency's real execution may call an LLM
- Model selection via `get_model_router().route(ModelRequest(...))`
- No direct model API calls from agencies
- Token counting for budget enforcement

### 13.3 SecurityManager Integration

- All external worker calls (`hermes-agent`, Playwright, agency adapters) must pass through `SecurityManager.authorize()`
- `SkillSpecTorGate` validates any new skills/adapters
- SecurityManager is the FINAL authority — not SkillSpecTor

### 13.4 CouncilManager Integration

- TestingCouncil = one `CouncilManager` session (NOT a second council)
- Members: 9 agencies + UserSimulationAgent (builder excluded)
- Uses existing `critique()` and `synthesize()` methods (M6)
- Builder exclusion enforced at convene() time

### 13.5 WorkflowManager Integration

- `TestOrchestratorService` IS-A `WorkflowManager` (inheritance, not composition)
- Reuses existing workflow lifecycle (created→running→completed/failed)
- Adds test-specific step handlers and evidence normalization

### 13.6 HermesBridge Integration

- `UserSimulationAgent` uses `HermesBridge` for all browser interaction
- Session isolation: each simulation gets a unique `hermes_<uuid>` session
- Observations are untrusted until normalized to `TestingEvidence`

---

## 14. TEST REQUIREMENTS

### 14.1 Unit Tests (must test REAL behavior, not class existence)

| Test File | Coverage |
|-----------|----------|
| `test_testing_evidence.py` | Schema construction, serialization, provenance validation, immutable fields |
| `test_test_orchestrator.py` | Dispatch, normalize, council submit, retest coordination |
| `test_user_simulation_agent.py` | No-source-code access, hermes integration, goal completion measurement |
| `test_simplification_gate.py` | Complexity detection, pass/fail logic, safeguard preservation |
| `test_agency_adapters.py` | Real execution paths (mocked workers), heuristic-free behavior |
| `test_final_judge_agency.py` | Evidence aggregation, builder exclusion, verdict logic |
| `test_m7_closed_loop.py` | FAIL→RCA→Learning→Replan→Re-execute→Retest cycle |

### 14.2 Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_m7_multi_perspective.py` | Full 9+1 perspective orchestration, parallel execution, evidence collection |
| `test_m7_isolation.py` | Builder env ≠ tester env, builder excluded from TestingCouncil |
| `test_m7_evidence_integrity.py` | Provenance chain, immutability, reproducibility scoring |
| `test_m7_seeded_defects.py` | 9 seeded defects detected across perspectives |

### 14.3 Architectural Invariant Tests

| Test | Requirement |
|------|-------------|
| Single kernel | No second kernel instantiated |
| Single ModelRouter | Only one `ModelRouter` global |
| Single EventBus | Only one canonical bus; no bypass |
| Single CouncilManager | TestingCouncil uses existing instance |
| No new EventType without justification | Event type addition audit |
| Builder exclusion | TestingCouncil convene excludes builder |
| No external verdict authority | hermes-agent(EXT) cannot return verdict |
| SimplificationGate runs pre-acceptance | Gate blocks over-engineered implementations |
| Closed-loop bounded | Max iterations enforced; no infinite loop |
| Evidence provenance complete | Every TestingEvidence has valid provenance |

### 14.4 Security Tests

| Test | Requirement |
|------|-------------|
| No security bypass | All external calls go through SecurityManager |
| No source code for user simulation | UserSimulationAgent constructor rejects source_code param |
| SkillSpecTor gate respected | Gate is integration gate; SecurityManager is final |
| No duplicate council framework | Only one CouncilManager in system |
| No external egress without auth | All outbound calls authorized |

### 14.5 Regression Tests

All existing tests must continue to pass:
- `tests/unit/test_m6_council_synthesis.py` — M6 functionality unchanged
- `tests/unit/test_m4_adapter.py` — M4 functionality unchanged
- `tests/unit/test_m5_gate.py` — M5 functionality unchanged
- `tests/integration/test_integration.py` — existing integration paths
- `tests/unit/test_closed_loop.py` — existing closed-loop behavior
- All 836 existing unit tests
- All 101 existing integration tests

---

## 15. M8+ CONTAMINATION PROHIBITIONS

| # | Prohibited Item | Why |
|---|----------------|-----|
| 1 | Production deployment pipelines | Post-V2 |
| 2 | SLA / performance contracts for models | Post-V2 |
| 3 | Autonomous self-evolution beyond closed loop | Post-V2 |
| 4 | Second kernel or governance system | Architecture invariant |
| 5 | External decision authority | External-worker principle |
| 6 | Second ModelRouter | Single canonical router |
| 7 | Second EventBus | Single canonical bus |
| 8 | Second SecurityManager | Single canonical authority |
| 9 | Notion integration | C4 unresolved |
| 10 | Native browser implementation | Architecture forbids; use hermes-agent(EXT) |
| 11 | MOA synthesis | Future enhancement |
| 12 | Caveman compression | Future enhancement |
| 13 | FreeLLMAPI production contracts | Post-V2 hardening |
| 14 | CLI 9.4-9.12 features | Deferred from M1 baseline |
| 15 | Singleton reduction across core | Deferred |

---

## 16. ARCHITECTURAL INVARIANTS (M7-Relevant)

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-001 | Single kernel | `HermesKernel` is sole orchestrator |
| INV-005 | Single ModelRouter | `get_model_router()` global singleton |
| INV-007 | Single EventBus | `get_core_event_bus()` global singleton; no bypass |
| INV-008 | UserSimulationAgent has NO source code access | Constructor enforces; tests verify |
| INV-009 | Builder cannot self-approve | TestingCouncil `convene()` excludes builder; verified by test |
| INV-010 | Evidence-first | All claims require `TestingEvidence`; prose-only verdicts rejected |
| INV-011 | External-worker principle | Workers execute; AI-OS decides; hermes-agent(EXT) observations untrusted |
| INV-012 | One governance system | Single `CouncilManager`; TestingCouncil is a session, not a hierarchy |
| INV-013 | Closed loop bounded | Iteration cap + token budget + convergence check + regression guard |
| INV-014 | SecurityManager final authority | No component overrides SecurityManager decisions |
| INV-015 | No duplicate orchestrator | `TestOrchestratorService` extends `WorkflowManager`; never duplicates |
| INV-016 | No new EventType without gap analysis | 121 existing types; additions require justification |
| INV-017 | KKC/EVC are techniques only | Re-implemented in `CouncilManager.critique()`; never vendored |

---

## 17. ACCEPTANCE CRITERIA

M7 is accepted when ALL of the following are true:

| # | Criterion | How Verified |
|---|-----------|-------------|
| 1 | 9 seeded defects are detected | `test_m7_seeded_defects.py` — all 9 found |
| 2 | False positive is challenged | TestingCouncil dissent preserved in critique |
| 3 | Minority disagreement is preserved | `dissent_preserved` in `CritiqueResult` |
| 4 | Builder cannot self-approve | Builder excluded from TestingCouncil; test verifies |
| 5 | Failed test enters closed loop | `test_m7_closed_loop.py` — FAIL→RCA→PASS cycle |
| 6 | Corrected implementation is retested | Retest coordination in `TestOrchestratorService` |
| 7 | System eventually reaches verified PASS | Closed-loop bounded convergence |
| 8 | All 17 acceptance criteria verified | SimplificationGate approval; all security/verification gates; closed-loop bounded |
| 9 | All existing tests pass | 836 unit + 101 integration + 57 M6 dedicated |
| 10 | `TestingEvidence` schema is machine-checkable | Serialization/deserialization tests |
| 11 | `UserSimulationAgent` has no source code access | Constructor test; no source_code parameter |
| 12 | `hermes-agent`(EXT) returns observations only | Bridge test; no verdict field in `HermesObservation` |
| 13 | No second CouncilManager | Import audit; only one `CouncilManager` global |
| 14 | No second EventBus | Import audit; only one canonical bus |
| 15 | No new `EventType` without documentation | EventType audit |
| 16 | Evidence provenance is complete | Every `TestingEvidence` has valid provenance dict |
| 17 | `FinalJudgeAgency` verdict is independent of builder | Verdict test with builder in target context |

---

## 18. DEFINITION OF DONE

M7 is Done when:

1. **All M7-A through M7-J sub-tasks implemented** per this contract
2. **All required files created** per §4
3. **All allowed modifications made** per §5; no protected files touched
4. **All M7 unit tests pass** (7 test files)
5. **All M7 integration tests pass** (4 test files)
6. **All architectural invariant tests pass** (10 tests)
7. **All security tests pass** (5 tests)
8. **All regression tests pass** (836 unit + 101 integration + 57 M6)
9. **No M8+ contamination** detected (audit per §15)
10. **All 17 acceptance criteria met** (per §16)
11. **Independent QA score ≥ 90/100** (M7 QA contract, §20)
12. **Documentation updated** — architecture doc reflects M7 state

---

## 19. SCORING RUBRIC (100 points)

| Category | Max Points | Criteria |
|----------|-----------|----------|
| **Architecture Compliance** | 15 | Follows FINAL_AI_OS_V2_ARCHITECTURE.md; no Frankenstein components; correct inheritance (TestOrchestratorService → WorkflowManager); single council; single kernel |
| **Functional Correctness** | 15 | All 9 seeded defects detected; closed loop reaches PASS; critique produces correct rankings; FinalJudge verdict matches evidence |
| **Testing Realization** | 12 | Real execution replaces all 9 heuristic stubs; evidence normalized correctly; council critique/synthesis functional |
| **Multi-Perspective Behavior** | 10 | 9 agencies + UserSimulationAgent all execute; parallel dispatch works; evidence from each perspective distinct |
| **User Simulation** | 8 | Agent gets goal only, not source code; discovers via browser; measures goal completion; no API access |
| **Evidence Integrity** | 8 | Every TestingEvidence has complete provenance; immutable after normalization; reproducibility scored; proof referenced |
| **Security** | 8 | SecurityManager final authority; builder excluded; no external verdict; SkillSpecTor gate respected; no security bypass |
| **EventBus/Invariants** | 6 | Single bus; single ModelRouter; single CouncilManager; no new EventTypes without justification; all emissions canonical |
| **Integration** | 6 | M6 critique/synthesis reused; M5 HermesBridge used; M4 SkillSpecTor integrated; closed loop wired correctly |
| **Regression Safety** | 5 | All 836 unit + 101 integration + 57 M6 tests pass; no behavior change in M1-M6 components |
| **Scope Discipline** | 4 | No M8+ features implemented; no unnecessary complexity; no second orchestrator; no vendor imports |
| **Test Quality** | 3 | Tests assert REAL behavior; negative/failure paths covered; boundary conditions tested |

**Minimum passing score: 85/100**
**Independent QA target: 95/100**

---

## 20. TERMINAL 3 QA CONTRACT

### 20.1 What Terminal 3 Must Verify

Terminal 3 (Independent QA) must verify the following after Terminal 2 completes M7:

#### A. Functional Verification
1. Run `pytest tests/unit/test_testing_evidence.py` — all pass
2. Run `pytest tests/unit/test_test_orchestrator.py` — all pass
3. Run `pytest tests/unit/test_user_simulation_agent.py` — all pass
4. Run `pytest tests/unit/test_simplification_gate.py` — all pass
5. Run `pytest tests/unit/test_agency_adapters.py` — all pass
6. Run `pytest tests/unit/test_final_judge_agency.py` — all pass
7. Run `pytest tests/unit/test_m7_closed_loop.py` — all pass
8. Run `pytest tests/integration/test_m7_multi_perspective.py` — all pass
9. Run `pytest tests/integration/test_m7_isolation.py` — all pass
10. Run `pytest tests/integration/test_m7_evidence_integrity.py` — all pass
11. Run `pytest tests/integration/test_m7_seeded_defects.py` — all pass (9 defects detected)

#### B. Regression Verification
12. Run `pytest tests/unit/` — all 836+ existing tests pass
13. Run `pytest tests/integration/` — all 101+ existing tests pass
14. Run `pytest tests/unit/test_m6_council_synthesis.py` — all 57 M6 tests pass
15. Run `pytest tests/integration/test_integration.py` — passes

#### C. Architectural Invariant Verification
16. Verify single `CouncilManager` — grep for `CouncilManager()` instantiations (should be 1 global + test instances)
17. Verify single `EventBus` — grep for `EventBus()` instantiations (should be 1 global)
18. Verify single `ModelRouter` — grep for `ModelRouter()` instantiations (should be 1 global)
19. Verify `TestOrchestratorService` extends `WorkflowManager` (not duplicates)
20. Verify `UserSimulationAgent` has no `source_code` parameter
21. Verify builder exclusion in TestingCouncil convene
22. Verify no new `EventType` added without documentation
23. Verify no second `SecurityManager` created

#### D. Security Verification
24. Verify all external calls go through `SecurityManager.authorize()`
25. Verify `hermes-agent`(EXT) returns `HermesObservation` (not verdict)
26. Verify `SkillSpecTorGate` is integration gate, not authority
27. Verify no source code accessible to `UserSimulationAgent`

#### E. Evidence Integrity Verification
28. Verify every `TestingEvidence` has `provenance` dict with required fields
29. Verify `TestingEvidence` is immutable after construction
30. Verify `UserSimulationCompleted` normalizes to `TestingEvidence`
31. Verify builder-origin evidence is excluded from FinalJudgeAgency input

#### F. Scoring
32. Score against 100-point rubric (§19)
33. Minimum pass: 85/100
34. Target: 95/100

### 20.2 QA Report Format

Terminal 3 must produce:
- `M7_INDEPENDENT_QA_REPORT.md` with:
  - Test execution results (pass/fail counts)
  - Rubric scoring breakdown
  - Findings (critical/high/medium/low/none)
  - Remediation recommendations (if any)
  - GO/NO-GO decision

---

## 21. IMPLEMENTATION NOTES

### 21.1 Agency Real Execution Strategy

Each V1 agency currently has a heuristic `review()` (e.g., `if "sql" in target: finding = sql_injection`). M7 must replace these with real execution:

| Agency | Real Execution Mechanism |
|--------|-------------------------|
| SecurityAgency | Static analysis + SecurityManager integration |
| PerformanceAgency | Benchmark harness execution |
| ChaosAgency | Fault injection via ChaosEngine adapter |
| AccessibilityAgency | Playwright MCP + axe-core |
| DocumentationAgency | Docstring analysis + LLM review via ModelRouter |
| ConcurrencyAgency | Static analysis + dynamic race detection |
| BugHunterAgency | Fuzz generation + property-based testing |
| ArchitectureAgency | Knowledge graph traversal via Graphify MCP |
| FinalJudgeAgency | Evidence aggregation + weighted scoring |

### 21.2 UserSimulationAgent Behavior

The `UserSimulationAgent` MUST:
- Receive ONLY: `app_url`, `user_goal`, `exploration_brief`
- NEVER receive: source code, internal API contracts, implementation details
- Explore via `hermes-agent`(EXT) browser session
- Attempt goal completion as a confused user would
- Report `goal_completion_pct`, `usability_blockers`, `confusing_states`
- Return `UserSimulationCompleted`, which normalizes to `TestingEvidence`

### 21.3 TestingCouncil Composition

```python
members = [
    CouncilMember(member_id="security_agency", name="Security", expertise=["security"]),
    CouncilMember(member_id="performance_agency", name="Performance", expertise=["performance"]),
    CouncilMember(member_id="chaos_agency", name="Chaos", expertise=["chaos"]),
    CouncilMember(member_id="accessibility_agency", name="Accessibility", expertise=["accessibility"]),
    CouncilMember(member_id="documentation_agency", name="Documentation", expertise=["docs"]),
    CouncilMember(member_id="concurrency_agency", name="Concurrency", expertise=["concurrency"]),
    CouncilMember(member_id="bug_hunter_agency", name="BugHunter", expertise=["bugs"]),
    CouncilMember(member_id="architecture_agency", name="Architecture", expertise=["architecture"]),
    CouncilMember(member_id="user_simulation", name="UserSimulation", expertise=["ux"]),
    # NOTE: builder_id is deliberately EXCLUDED (INV-009)
]
```

### 21.4 SimplificationGate Placement

`SimplificationGate.evaluate()` runs AFTER `FinalJudgeAgency` returns APPROVE but BEFORE the final `TESTING_COMPLETED` is emitted. If the gate detects unnecessary complexity, it returns FAIL with findings, and the closed loop restarts from planning.

---

## 22. KNOWN CONFLICTS / OPEN ITEMS

| ID | Conflict | Resolution |
|----|----------|------------|
| **C1** | "Hermes" naming collision (`HermesKernel` vs `hermes-agent`(EXT)) | BLOCKING — rename external to `hermes-agent`(EXT); rewrite INV-009 |
| **C2** | Verification gate count (12/12 vs 11-layer) | RESOLVED — replaced ambiguous "12/12 gates" with "all 17 acceptance criteria verified"; no `VerificationService` in src/ (gates exist in existing components) |
| **C3** | Lifecycle state count (narrative 5 vs code 8) | RESOLVED — M12 updated 15.3 narrative to 8-state FSM (OPERATIONAL, DEGRADED, ROLLBACK_IN_PROGRESS, RECOVERY_IN_PROGRESS); code truth = 8 LifecycleState members |
| **C4** | Notion absent from repo | RESOLVED — Notion adapter implemented in M8-T4; adopted as external integration via MCP bridge |
| **R1** | Test execution unverified this session | Fresh `pytest` run required before M7 sign-off |

---

## END OF TERMINAL 1 IMPLEMENTATION CONTRACT — M7 FROZEN

**Next:** Terminal 2 executes this contract.
**After Terminal 2:** Terminal 3 performs independent QA per §20.
