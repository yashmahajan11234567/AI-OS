# M6 SCOPE RECONCILIATION

**Terminal 1 — Architecture / Implementation Scope Reconciliation**
**Date:** 2026-08-24
**Authoritative basis:** `architecture/FINAL_AI_OS_V2_ARCHITECTURE.md` (frozen, 2026-08-24)
**Supporting:** `UPDATED_V2_MILESTONES.md`, `COUNCIL_SYNTHESIS_ARCHITECTURE.md`, `TERMINAL_1_V2_IMPLEMENTATION_PLAN.md`, `TERMINAL_1_V2_FREEZE_RECONCILIATION_REPORT.md`
**M5 status:** COMPLETE — independent verification confirmed (884 tests pass, MCP gate-before-connect wired, GraphifyBackend via MemoryManager, C14 advisory semantics, M5 gate + closed-loop + full suite green).

> Scope rule applied: M6 is implemented ONLY per the frozen architecture. No architectural decisions invented. M7+ is explicitly excluded. No code was modified for this reconciliation.

---

## 1. M6 Identity

- **Milestone name:** **M6 — Council Synthesis & Self-Prompting**
- **Architectural purpose:** Deliver the *reasoning/synthesis technique layer* that M7's Testing Council depends on. Concretely: (a) extend the single `CouncilManager` with a `critique()` stage adopting KKC/EVC *techniques only*; (b) add an `LLMCouncil` façade (6 cognitive roles) over the existing `CouncilManager` for the governance/reasoning domain; (c) add a bounded, traceable `SelfPromptingService` that routes self-questioning into the `LLMCouncil`.
- **Position in lifecycle:** Third of four V2 milestones: **M4 (skill/security) → M5 (integration backbone) → M6 (council synthesis/self-prompt) → M7 (real multi-perspective testing + user simulation)**. M6 is a *prerequisite enabler* for M7; it contains NO testing realization, NO agencies, NO orchestrator, NO user simulation.

---

## 2. M4 → M5 → M6 Dependency Chain

```
M4  Skill & Security Standardization
    ├─ canonical SKILL.md adapter (SkillService)            [DONE in M4]
    └─ SkillSpecTor gate in SecurityManager                 [DONE in M4]
            │  M4 provides the safety prerequisite reused by M5/M6/M7.
            ▼
M5  Knowledge-Graph Memory & Integration Backbone
    ├─ Graphify MCP → memory tier                           [DONE in M5]
    ├─ Agent-Reach MCP                                       [DONE in M5]
    ├─ FreeLLMAPI via ModelRouter                           [DONE in M5]
    └─ hermes-agent(EXT) ACP/MCP bridge                      [DONE in M5]
            │  M5 provides external execution + provenance backbone.
            │  M6 is "parallel-capable after M5 bridge" — it does NOT need
            │  M5 at runtime to function, but shares the frozen infra.
            ▼
M6  Council Synthesis & Self-Prompting        ← THIS MILESTONE
    ├─ CouncilManager.critique()   (KKC/EVC techniques)     [NEW]
    ├─ LLMCouncil façade (6 roles)                          [NEW]
    └─ SelfPromptingService (bounded, traceable)            [NEW]
            │  M6 delivers the synthesis technique that M7-F
            │  (Testing Council critique synthesis) consumes.
            ▼
M7  Multi-Perspective Testing & User Simulation
    └─ reuses M6 critique() for the Testing Council critique stage (M7-F)
```

**Hard dependency facts from the architecture:**
- M6 "Depends on: M4, M5 (parallel-capable after M5 bridge)" (FINAL §XXXI).
- M6 "Required for M7 Testing Council critique stage" (FINAL §XXXI).
- M7 "Depends on … M6 (critique technique)" (FINAL §XXXI).
- M6 must NOT implement the Testing Council itself — that is M7-F, which *reuses* M6's `critique()`.

---

## 3. M6 Components

| Component | Purpose | Existing? | Modify/Create | Dependency | M6 Required? |
|---|---|---|---|---|---|
| `CouncilManager.critique()` | New stage: anonymized two-axis cross-ranking + relabel-then-review + dissenter-override, adopting KKC/EVC *techniques* | **No** (`critique` absent) | **Modify** `core/council_manager.py` | `CouncilManager.propose/vote/decide/dissent` (existing) | **YES** |
| `LLMCouncil` façade | 6 roles (Analyst, Contrarian, Outsider, Skeptic, Specialist, Simplifier) over `CouncilManager` for reasoning/self-prompting domain | **No** | **Create** `core/llm_council.py` | `CouncilManager` (existing) | **YES** |
| `SelfPromptingService` | Bounded, traceable, objective-linked self-questioning; routes into `LLMCouncil` | **No** | **Create** `services/self_prompting.py` | `LLMCouncil`, `CouncilManager` | **YES** |
| `CouncilManager.synthesize()` | Chairman/synthesis merge (weighted by expertise/confidence) | **No** (`synthesize` absent) | **Modify** `core/council_manager.py` (additive) | `decide()` (existing) | **YES** (synthesis role named in COUNCIL_SYNTHESIS §2/§3) |
| COUNCIL_* event set | Existing canonical events already cover convene/propose/vote/dissent/decide | Yes (7 events) | No change | — | Emitted by M6 flows |
| `CouncilMember.expertise` / `CouncilVote` / `CouncilDecision.metadata` / `dissent()` | Existing substrate used by critique/synthesis | Yes | No change (reused) | — | Reused |
| `FinalJudgeAgency` | Verdict aggregation (M7-G) | Yes (`ai_agency.py:507`) | **NO** (M7 scope) | — | NO — M7 |
| `TestingEvidence` | Typed evidence schema (M7-A) | No | **NO** (M7 scope) | — | NO — M7 |
| `TestOrchestratorService` | Orchestrator extending `WorkflowManager` (M7-B) | No | **NO** (M7 scope) | — | NO — M7 |
| `UserSimulationAgent` | 10th perspective (M7-D) | No | **NO** (M7 scope) | — | NO — M7 |
| Real 9-agency execution | M7-C | Simulated | **NO** (M7 scope) | — | NO — M7 |
| `SimplificationGate` | Pre-acceptance gate (M7-J) | No | **NO** (M7 scope) | — | NO — M7 |
| `AIAgencyService` 9 roles | M7-C realization | Simulated | **NO** (M7 scope) | — | NO — M7 |
| Isolation/sandbox layer | M7-E | No | **NO** (M7 scope) | — | NO — M7 |
| Hermes/Graphify/FreeLLMAPI/MCP wiring | M5 (done) | Yes | **NO** | — | Already M5 |

**Repository state confirmation:** A repo-wide grep for `LLMCouncil`, `SelfPrompting`, `SelfPrompt`, `def critique`, `def synthesize` across `src/` and `tests/` returned **zero matches**. M6 has **no partial implementation, no accidental code, no scaffolding** present. The only `critique`/`synthesize` references are in architecture docs. `CouncilManager` already provides `convene/propose/vote/decide/dissent` + `CouncilMember.expertise`, `CouncilVote`, `CouncilDecision` — exactly the substrate the architecture says to extend (COUNCIL_SYNTHESIS §1).

---

## 4. Exact Files

### Authorized to CREATE (Terminal 2 only):
- `src/aios/core/llm_council.py` — `LLMCouncil` façade (6 roles) over `CouncilManager`.
- `src/aios/services/self_prompting.py` — `SelfPromptingService` (bounded).
- Tests (new, unit + integration):
  - `tests/unit/test_council_critique.py`
  - `tests/unit/test_llm_council.py`
  - `tests/unit/test_self_prompting.py`
  - `tests/integration/test_self_prompting_loop.py` (bounded-loop + dissent integration)

### Authorized to MODIFY (Terminal 2 only):
- `src/aios/core/council_manager.py` — **add** `critique()` stage (anonymized two-axis cross-ranking + relabel-then-review + dissenter-override) and **add** `synthesize()` chairman/synthesis role. ADDITIVE ONLY — retain every existing method, dataclass, and event emission. No signature changes to existing public methods.
- `src/aios/core/__init__.py` — export `LLMCouncil` (and its role enum) if the module's public surface requires it. ONLY additive exports.
- `src/aios/services/__init__.py` — export `SelfPromptingService` if required. ONLY additive.

### MUST NOT be modified during M6:
- `kernel.py`, `lifecycle_manager.py`, `security_manager.py`, `state.py`, `storage.py`, `resource_manager.py`, `health_manager.py`, `observability_manager.py`, `capability_manager.py`, `configuration_manager.py`.
- `events/*` (the 121 canonical `EventType`s) — no new council events are required for M6; reuse existing `COUNCIL_*` events.
- `root_cause.py` (loop logic), `workflow.py` (extend-don't-rewrite — and M6 does not touch it).
- `model_router.py` (FreeLLMAPI done in M5).
- `ai_agency.py` (9 agencies + `FinalJudgeAgency` — pure M7 scope).
- `services/testing.py`, `core/test_orchestrator.py`, `core/user_simulation.py`, `core/testing_evidence.py`, `core/simplification.py` — these are M7/M7-A/M7-D/M7-J artifacts; do NOT create them in M6.
- `mcp_manager.py` — MCP wiring is M5 (done) / M7.
- `memory.py` / `services/memory.py` — M5 (done).
- `services/council.py` — the existing event-driven facade over `CouncilManager`. M6 does NOT require changes here (critique/synthesis are added to the core `CouncilManager`; the service may optionally expose them later in M7, not M6).

---

## 5. Interfaces

All names below are taken from the frozen architecture (FINAL §XXX / PART XXX / COUNCIL_SYNTHESIS / IMPLEMENTATION_PLAN §24). Terminal 2 MUST use these exact names.

### 5.1 `CouncilManager` additions (`core/council_manager.py`)

```python
# --- NEW dataclasses (additive) ---

@dataclass
class CritiqueRanking:
    """Anonymized two-axis cross-ranking of a member's proposal."""
    member_label: str            # anonymized label (e.g. "P-A"), NOT member_id
    accuracy: float              # axis 1 (KKC)
    insight: float               # axis 2 (KKC)
    relabel_round: int           # which relabel-then-review round (EVC)

@dataclass
class CritiqueResult:
    """Output of the critique() stage."""
    council_id: str
    rankings: list[CritiqueRanking]          # anonymized, two-axis
    dissent_preserved: list[dict[str, Any]]  # dissent captured, not averaged
    dissenter_override: bool                 # True if minority insight outranked majority
    override_member_label: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class CouncilManager:
    # ... ALL existing methods unchanged ...

    async def critique(
        self,
        council_id: str,
        *,
        accuracy_scores: dict[str, float],   # member_id -> accuracy (0..1)
        insight_scores: dict[str, float],    # member_id -> insight  (0..1)
        dissent: list[dict[str, Any]] | None = None,
        relabel_rounds: int = 1,             # EVC relabel-then-review passes
    ) -> CritiqueResult:
        """
        STAGE 2 of council synthesis (PART XVII).
        - Anonymizes member identities for the ranking pass (KKC blind review).
        - Cross-ranks peers on two axes: accuracy + insight (KKC).
        - Relabel-then-review: shuffle member labels before cross-review
          (EVC) to break authority bias; repeat `relabel_rounds` times.
        - Dissenter-override (EVC): if a dissenting member's `insight`
          outranks the majority on the insight axis, flag override.
        - PRESERVES dissent as metadata; never silently averages it away.
        - Emits (reuses) COUNCIL_DISSENT_REGISTERED / COUNCIL_DECISION_FINALIZED
          as appropriate. NO new EventType.
        """

    async def synthesize(
        self,
        council_id: str,
        *,
        critique: CritiqueResult | None = None,
        algorithm: ConsensusAlgorithm | None = None,
    ) -> CouncilDecision:
        """
        Chairman/synthesis merge (COUNCIL_SYNTHESIS §2/§3).
        - Weights votes by expertise (CouncilMember.expertise) + confidence.
        - Honors dissenter_override from critique() when present.
        - Delegates to existing decide()/consensus math. Additive wrapper.
        """
```

### 5.2 `LLMCouncil` façade (`core/llm_council.py`)

```python
class LLMRole(str, Enum):
    ANALYST = "analyst"
    CONTRARIAN = "contrarian"
    OUTSIDER = "outsider"
    SKEPTIC = "skeptic"
    SPECIALIST = "specialist"
    SIMPLIFIER = "simplifier"

class LLMCouncil:
    """
    Façade over CouncilManager for the REASONING / SELF-PROMPTING domain
    (COUNCIL 1 LLM Council, FINAL PART XVI). SIX roles only.
    Does NOT replace Verification or the Testing Council.
    Single CouncilManager substrate; this is one council session family.
    """
    def __init__(self, manager: CouncilManager | None = None): ...

    async def deliberate(
        self,
        topic: str,
        *,
        objective_id: str,          # self-prompt must cite objective (ADR #10)
        roles: list[LLMRole] | None = None,   # default: all 6
        builder_excluded: bool = True,        # builder excluded from own council
    ) -> CouncilSession:
        """Convene with 6 role members; each proposes independently (blind)."""

    # Reuses manager.propose / critique / dissent / synthesize.
```

### 5.3 `SelfPromptingService` (`services/self_prompting.py`)

```python
@dataclass
class SelfPromptConfig:
    max_depth: int = 5            # ADR #10 bound
    token_budget: int = 4000      # ADR #10 bound
    require_objective_cite: bool = True   # must cite objective (ADR #10)
    allow_open_recursion: bool = False    # explicitly forbidden

class SelfPromptingService(BaseService):
    """Bounded, traceable, objective-linked self-questioning (FINAL PART VI)."""
    name = "self_prompting"
    version = "1.0.0"

    def __init__(self, council: LLMCouncil | None = None,
                 config: SelfPromptConfig | None = None, **kwargs): ...

    async def prompt(
        self,
        objective: str,
        objective_id: str,
        *,
        seed_questions: list[str] | None = None,
        depth: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Bounded self-questioning loop routed into LLMCouncil.
        - Depth hard-capped at config.max_depth; token budget enforced.
        - Every prompt MUST cite objective_id (raises if require_objective_cite
          and missing).
        - No open recursion (allow_open_recursion=False always; ADR #10).
        - Returns traceable record of prompts + council outcomes.
        """
```

### 5.4 Events / Contracts
- **No new `EventType`s** for M6. Reuse existing: `COUNCIL_CONVENED`, `COUNCIL_PROPOSAL_SUBMITTED`, `COUNCIL_VOTE_CAST`, `COUNCIL_CONSENSUS_REACHED`, `COUNCIL_DISSENT_REGISTERED`, `COUNCIL_DECISION_FINALIZED` (all in `events/core/types.py:132-137`).
- `CouncilMember.expertise` (existing, `council_manager.py:54`) carries role/stance for diverse perspectives (EVC worldview-diverse advisors).
- `CouncilDecision.metadata` (existing) carries `dissent_preserved` and `dissenter_override` flags so synthesis surfaced dissent.

---

## 6. Control / Data Flow

### M6 reasoning flow (LLM Council domain — FINAL PART VI / XVII Stage 1–7 subset):
```
INTENT → PLANNING → SELF-PROMPT / REASONING
   SelfPromptingService.prompt(objective, objective_id)
     → bounded loop (depth ≤ max_depth, token ≤ budget, cites objective)
     → for each seed question: LLMCouncil.deliberate(topic, objective_id)
         → convene 6 roles (Analyst/Contrarian/Outsider/Skeptic/Specialist/Simplifier)
         → STAGE 1: each role propose() independently (blind)
         → STAGE 2: CouncilManager.critique()  [anonymized 2-axis + relabel + dissenter-override]
         → dissent() preserved as metadata
         → STAGE 3: CouncilManager.synthesize() → CouncilDecision
     → record traceable prompt→council outcome
   → feeds planning / design / replanning (NOT verification)
```

### M6 technique reuse relationship to M7:
- M6's `critique()` is the **same method** M7-F calls for the Testing Council critique stage. M6 delivers the method; M7-F convenes the Testing Council (9 agencies + UserSimulation) and calls `critique()` on it. M6 contains **no agency, no orchestrator, no testing council convening of testers**.

### Provenance:
- Every `CritiqueResult`, `CouncilDecision`, and self-prompt record carries `metadata` with session_id / worker / timestamp / environment where applicable (FINAL PART VII evidence model; INV-007 provenance mandatory). M6 does not emit external observations, so provenance here is internal kernel provenance.

---

## 7. Security Model

- **Single security authority:** `SecurityManager` (kernel) — M6 adds NO security mechanism; it must not weaken or bypass existing gates (FINAL PART XIX, ADR #18).
- **Builder exclusion (independence model, FINAL PART XVIII):** `LLMCouncil.deliberate(..., builder_excluded=True)` defaults to excluding the builder from its own council. M6 enforces this in the façade; it does NOT implement the full TestingCouncil independence matrix (that is M7-E/M7-G). For M6's reasoning domain, the builder (the planning/self-prompt originator) must not be a voting member of the council it convenes — enforce via role assignment.
- **Fail-closed / bounded (ADR #10):** `SelfPromptingService` MUST raise/abort if `max_depth`, `token_budget`, or objective-citation constraints are violated. No open recursion (WHAT-MUST-NOT #7 uncontrolled recursive loops, #8 uncontrolled self-modification).
- **No unauthorized LLM-stage egress:** M6's council/self-prompt operate within the trust boundary using `ModelRouter` (FINAL ADR #12). M6 must NOT introduce direct provider calls or external egress. (C10 — SkillSpecTor/FreeLLMAPI LLM-stage egress — is an M5/M4 concern; M6 inherits the boundary, does not alter it.)
- **Anonymity at critique:** `critique()` strips `member_id` for the ranking pass — authority-bias reduction (KKC/EVC). This is a privacy/integrity property of the synthesis, not a security gate; preserve it.
- **Advisory vs authoritative:** M6 reasoning/self-prompt output is **advisory input to planning**, never authoritative state (FINAL PART VII "learning is advisory, not authoritative" — same principle extends to self-prompting). M6 must not write to any source-of-truth state.
- **Provenance:** retained on all M6 artifacts (INV-007).

---

## 8. Invariants

M6 MUST preserve every frozen invariant (FINAL PART XXXIX + INV set):

1. **Single kernel** — no second `HermesKernel`; M6 touches only `CouncilManager` + new façade/service. (ADR #1)
2. **Single `CouncilManager`** — M6 extends the ONE existing `CouncilManager`. It does NOT create a second council framework, second synthesis subsystem, or second LLM council (WHAT-MUST-NOT #1, #2; ADR #2). `LLMCouncil` is a façade over it, not a parallel manager.
3. **No imported council subsystems** — KKC / evisoft code is NOT vendored; only techniques re-implemented inside `CouncilManager` (ADR #15, WHAT-MUST-NOT #3, #4).
4. **Security authority** — `SecurityManager` remains sole security authority; M6 adds no gate and bypasses none. (ADR #18)
5. **Single `ModelRouter`** — FreeLLMAPI via `ModelRouter` is canonical; M6 uses it, creates no second router. (ADR #12, WHAT-MUST-NOT #20)
6. **External-worker boundaries** — M6 operates inside the kernel trust boundary; `hermes-agent`(EXT) is NOT invoked by M6 (it is M5/M7). M6 emits no external observations.
7. **Memory authority** — M6 does not alter memory authority; it does not write provenance-free or advisory-as-fact data into memory. (PART VII)
8. **Provenance (INV-007)** — all M6 `CritiqueResult`/`CouncilDecision`/self-prompt records carry provenance metadata.
9. **Advisory vs authoritative** — M6 reasoning output is advisory to planning; never merged into authoritative/source-of-truth state.
10. **Gate-before-use/connect** — not directly M6's concern, but M6 must not circumvent M4/M5 gates.
11. **No unauthorized LLM-stage egress** — M6 stays within `ModelRouter` trust boundary.
12. **Bounded self-loop (ADR #10)** — `SelfPromptingService` hard-bounded (max-depth, token budget, objective-cited, no open recursion). The M3 closed loop remains the FINAL control loop; M6 does not create a competing loop (WHAT-MUST-NOT #17; ADR #8).
13. **Dissent preservation** — `critique()` preserves minority disagreement as metadata; never silently averaged away (FINAL PART XVII Stage 5, PART XVI COUNCIL 2).
14. **Builder cannot self-approve** — `LLMCouncil` excludes the builder from its own council (WHAT-MUST-NOT #10; PART XVIII).
15. **No second verification authority** — M6 reasoning does not produce verification verdicts; `FinalJudgeAgency`/AI-OS Verification remain M7/final (WHAT-MUST-NOT #16).
16. **V1 core protected** — `kernel.py`, event types, `root_cause.py`, `workflow.py` unchanged (ADR #19).

---

## 9. Testing Strategy

### 9.1 Unit tests (new `tests/unit/`)
- **`test_council_critique.py`**
  - Anonymized two-axis cross-ranking: `critique()` returns `rankings` keyed by anonymized label, not `member_id`.
  - Accuracy + insight axes both scored and present.
  - Relabel-then-review: with `relabel_rounds > 1`, label shuffling occurs and rankings are stable per round.
  - **Dissent preserved:** a registered `dissent()` is present in `CritiqueResult.dissent_preserved` and in `CouncilDecision.metadata`.
  - **Dissenter-override:** when a dissenting member's `insight` outranks majority on insight axis, `dissenter_override == True` and `override_member_label` set.
  - Additive: existing `convene/propose/vote/decide/dissent` still work unchanged.
- **`test_llm_council.py`**
  - `deliberate()` convenes exactly the 6 roles (Analyst/Contrarian/Outsider/Skeptic/Specialist/Simplifier) by default.
  - Builder exclusion: with `builder_excluded=True`, the convening originator is not a voting member.
  - Each role `propose()`s independently (blind) → 6 proposals.
  - Uses the SAME `CouncilManager` instance (single-substrate assertion).
- **`test_self_prompting.py`**
  - Bounded depth: `prompt()` with `depth` exceeding `max_depth` raises/stops at cap.
  - Token budget enforced: simulated over-budget aborts.
  - Objective citation required: `prompt()` without `objective_id` raises when `require_objective_cite=True`.
  - No open recursion: cannot exceed bounds even with recursive self-calls.
  - Returns traceable records (prompt → council outcome).

### 9.2 Integration tests (new `tests/integration/`)
- **`test_self_prompting_loop.py`**
  - Full flow: `SelfPromptingService.prompt()` → `LLMCouncil.deliberate()` → `critique()` → `synthesize()` → traceable outcome, within kernel event bus.
  - Bounded-loop integration: confirms loop terminates at cap and emits no spurious events.
  - Dissent integration: a dissenter in the council is preserved through to `CouncilDecision.metadata`.

### 9.3 Negative / security tests
- `critique()` with empty/invalid score dicts → handled fail-closed (no crash, no silent pass).
- `SelfPromptingService` violation of any bound → raises, never silently continues.
- `LLMCouncil` builder-exclusion tamper attempt → builder still excluded.
- Confirm **no new `EventType`** is required/introduced (grep-level assertion in CI or test).

### 9.4 Regression tests
- Full existing suite (currently **884 passed**) MUST remain green after M6. `tests/integration/test_closed_loop.py`, `test_kernel_lifecycle_e2e.py`, `test_failure_recovery.py`, `test_integration.py` untouched and passing.
- `CouncilManager` existing API (convene/propose/vote/decide/dissent/list/close/stats) behavior unchanged — add a regression assertion test reusing existing flows.

### 9.5 Closed-loop tests
- M6's self-prompting may *route into* the M3 closed loop on FAIL, but M6 does NOT implement the loop (exists). Test that a `SelfPromptingService` outcome can hand a replan trigger to existing planning — without creating a second loop. (Light-touch; the loop itself is M3/M5-verified.)

### Concrete acceptance criteria (tests):
- `critique()` produces an anonymized two-axis cross-ranking and applies dissenter-override when a minority insight outranks. (Mirrors COUNCIL_SYNTHESIS §6 #2, adapted to M6 reasoning domain.)
- Minority disagreement is preserved (dissent captured). (FINAL acceptance #3)
- Self-prompt is depth-capped and budget-capped; objective-cited; no open recursion. (FINAL PART VI, ADR #10)
- Builder excluded from its own council. (FINAL acceptance #4)
- Single `CouncilManager` substrate used (no second manager instantiated). (ADR #2)

---

## 10. Explicit Non-Goals (M6 MUST NOT implement)

The following belong to **M7 or later** and are PROHIBITED in M6:

- **`TestingEvidence`** dataclass / schema (M7-A) — do NOT create `core/testing_evidence.py` in M6.
- **`TestOrchestratorService`** extending `WorkflowManager` (M7-B) — do NOT create `services/test_orchestrator.py` in M6.
- **Real 9-agency execution** (`AIAgencyService` realization, M7-C) — do NOT modify `ai_agency.py` review bodies in M6.
- **`UserSimulationAgent`** + `hermes-agent`(EXT) browser (M7-D) — do NOT create `core/user_simulation.py` in M6.
- **Isolation/sandbox layer** (M7-E) — do NOT build per-run worktree/container infra in M6.
- **Testing Council critique synthesis convening testers** (M7-F) — M6 delivers `critique()`; M7-F is the one that convenes 9 agencies + UserSim and calls it. M6 does NOT convene a testing council of agencies.
- **`FinalJudgeAgency`** independent verdict (M7-G) — leave `ai_agency.py:507` untouched.
- **Adversarial / SkillSpecTor realization** (M7-H) — security gate is M4/M5; adversarial testing realization is M7.
- **Closed-loop integration / RCA→Learning→Replan→Re-execute→Retest realization** (M7-I) — loop exists (M3); M6 only may route into it.
- **`SimplificationGate`** + seeded-defect acceptance (M7-J) — do NOT create `core/simplification.py` in M6.
- **Any real multi-perspective testing, browser testing, or user-simulation functionality** — all M7.
- **Any second kernel / second council framework / KKC-or-evisoft subsystem / production browser farm / second skill format / second model router** (WHAT-MUST-NOT #1–21).

> Note on CouncilManager role: The architecture places `critique()` as a **shared stage** used by BOTH the LLM Council (M6) and the Testing Council (M7-F). M6 implements the stage + the LLM Council façade + self-prompting. M7-F reuses the stage for testers. M6 must NOT convene tester councils or emit `TestingEvidence`.

---

## 11. Scope Boundary

**M6 IN SCOPE:**
- `CouncilManager.critique()` stage (anonymized 2-axis + relabel-then-review + dissenter-override), KKC/EVC techniques only.
- `CouncilManager.synthesize()` chairman/synthesis wrapper (additive).
- `LLMCouncil` façade (6 roles) over `CouncilManager` for the reasoning/self-prompting domain.
- `SelfPromptingService` (bounded, traceable, objective-linked).
- Reuse of existing `COUNCIL_*` events and existing `CouncilMember`/`CouncilVote`/`CouncilDecision`/`dissent()`.
- Unit + integration + negative + regression tests for the above.

**M6 OUT OF SCOPE:**
- All M7 deliverables (TestingEvidence, TestOrchestratorService, 9-agency realization, UserSimulationAgent, isolation, Testing Council convening, FinalJudge verdict, adversarial realization, SimplificationGate, seeded-defect acceptance).
- Any new `EventType`.
- Any MCP/Hermes/Graphify/FreeLLMAPI wiring (M5 done).
- Any change to kernel, security_manager, event types, root_cause, workflow, model_router, ai_agency, services/testing.
- Any second kernel/council/verification/loop/subsystem.

---

## 12. Terminal 2 Implementation Contract

Implement M6 **exactly** as specified. No architectural decisions beyond this contract.

**Create:**
1. `src/aios/core/llm_council.py`
   - `LLMRole(str, Enum)` with exactly: `ANALYST, CONTRARIAN, OUTSIDER, SKEPTIC, SPECIALIST, SIMPLIFIER`.
   - `LLMCouncil` class with `__init__(self, manager: CouncilManager | None = None)` (defaults to `get_council_manager()`), and `async def deliberate(self, topic: str, *, objective_id: str, roles: list[LLMRole] | None = None, builder_excluded: bool = True) -> CouncilSession`.
   - `deliberate` convenes a `CouncilSession` with one `CouncilMember` per role (each with `expertise` describing the role's stance), builder-originator excluded when `builder_excluded=True`. Returns the session; caller invokes `manager.propose/vote/critique/synthesize`.
   - Must use the SAME `CouncilManager` instance; never instantiate a competing manager.
2. `src/aios/services/self_prompting.py`
   - `SelfPromptConfig` dataclass with `max_depth: int = 5`, `token_budget: int = 4000`, `require_objective_cite: bool = True`, `allow_open_recursion: bool = False`.
   - `SelfPromptingService(BaseService)` with `name = "self_prompting"`, `__init__(self, council: LLMCouncil | None = None, config: SelfPromptConfig | None = None, **kwargs)`, and `async def prompt(self, objective: str, objective_id: str, *, seed_questions: list[str] | None = None, depth: int = 0) -> list[dict[str, Any]]`.
   - Hard bounds: stop at `max_depth`; enforce `token_budget`; require non-empty `objective_id` when `require_objective_cite`; `allow_open_recursion` is always effectively False (raise on attempt to recurse unbounded); raise on any violation.
   - Each iteration routes into `LLMCouncil.deliberate(topic=question, objective_id=objective_id)`.
   - Returns traceable list of `{prompt, depth, council_id, outcome}` records.
3. Tests: `tests/unit/test_council_critique.py`, `tests/unit/test_llm_council.py`, `tests/unit/test_self_prompting.py`, `tests/integration/test_self_prompting_loop.py` — covering §9 exactly.

**Modify (additive only):**
4. `src/aios/core/council_manager.py`
   - Add dataclasses `CritiqueRanking`, `CritiqueResult` (see §5.1).
   - Add `async def critique(self, council_id, *, accuracy_scores, insight_scores, dissent=None, relabel_rounds=1) -> CritiqueResult` (see §5.1). Anonymize for ranking; two-axis; relabel-then-review; dissenter-override; preserve dissent in metadata; reuse existing COUNCIL_* events (NO new EventType).
   - Add `async def synthesize(self, council_id, *, critique=None, algorithm=None) -> CouncilDecision` (additive wrapper over `decide()`/consensus math, weighted by expertise + confidence, honors `dissenter_override`).
   - DO NOT change signatures or behavior of `convene/propose/vote/decide/dissent/get_council/list_councils/close_council/get_stats`.
5. `src/aios/core/__init__.py` and `src/aios/services/__init__.py` — ADDITIVE exports only (`LLMCouncil`, `LLMRole`, `SelfPromptingService`, `SelfPromptConfig` as needed).

**Do NOT touch:** everything in §4 "MUST NOT be modified".

**Definition of DONE (per-file):** all new methods present with the exact signatures above; all existing methods byte-for-byte behavior preserved; full suite 884→green plus new M6 tests green; zero new `EventType`; single `CouncilManager` substrate verified.

---

## 13. Terminal 3 QA Contract

Terminal 3 MUST independently verify AFTER Terminal 2 implementation:

1. **Architectural compliance:** `LLMCouncil` is a façade over `get_council_manager()`; no second `CouncilManager` instantiated anywhere; no KKC/evisoft code vendored (grep `karpathy|evisoft` in `src/` → zero).
2. **Scope compliance:** `grep -rln "TestingEvidence\|TestOrchestrator\|UserSimulation\|SimplificationGate" src/` returns ONLY M7-planned files (i.e., NONE created in M6). `ai_agency.py`, `services/testing.py`, `mcp_manager.py`, `kernel.py`, `security_manager.py`, event types, `root_cause.py`, `workflow.py`, `model_router.py` are UNCHANGED (git diff confirms).
3. **Functional correctness:** `critique()` returns anonymized two-axis rankings + dissent preserved + dissenter-override correct; `LLMCouncil.deliberate` yields 6 role members + builder excluded; `SelfPromptingService.prompt` bounded + objective-cited + no open recursion + traceable.
4. **Security correctness:** no new LLM-stage egress outside `ModelRouter`; `SecurityManager` untouched; self-prompt fails closed on bound violation; builder cannot self-approve in its own council.
5. **Test quality:** all §9 tests exist and pass; negative/security tests present; coverage of dissent-preservation + dissenter-override + bound enforcement.
6. **Regression safety:** full prior suite still 884 passed (or equivalent green); no M6 change broke existing council flows (add regression assertion reusing existing `convene/propose/vote/decide/dissent`).
7. **Integration correctness:** `test_self_prompting_loop.py` exercises prompt→LLMCouncil→critique→synthesize on the live event bus and terminates at bounds.
8. **Code quality:** additive-only modifications; no duplication of `WorkflowManager`/`CouncilManager`; follows surrounding code style/comment density.
9. **No M7+ contamination:** confirms none of the M7 artifacts (§10) were implemented; confirms `critique()` is shared-stage-ready but NOT used to convene tester councils in M6.
10. **Event integrity:** exactly the existing 7 `COUNCIL_*` EventTypes are used; `EventType` enum count remains 121 (no new type added).

---

## 14. Scoring (100-point acceptance rubric)

| # | Dimension | Points | Criteria |
|---|---|---|---|
| 1 | Architectural compliance | 12 | Single `CouncilManager` substrate; `LLMCouncil` façade only; no KKC/evisoft vendored; matches FINAL §XXXI/XXXIX. |
| 2 | Scope compliance | 12 | Only M6 components built; zero M7 artifacts created; files in §4 respected. |
| 3 | Functional correctness | 14 | `critique()` anonymized 2-axis + relabel + dissenter-override correct; `LLMCouncil` 6 roles + builder-excluded; `SelfPromptingService` bounded + cited + traceable. |
| 4 | Security correctness | 10 | No egress outside `ModelRouter`; `SecurityManager` untouched; self-prompt fail-closed; builder cannot self-approve. |
| 5 | Test quality | 12 | All §9 unit/integration/negative/regression tests present, meaningful, passing. |
| 6 | Regression safety | 10 | Full prior suite green (884); existing `CouncilManager` API behavior unchanged. |
| 7 | Integration correctness | 8 | `test_self_prompting_loop.py` passes on live event bus; loop terminates at bounds. |
| 8 | Code quality | 7 | Additive-only; no duplication; matches repo style. |
| 9 | Documentation | 5 | Docstrings/comments for new public APIs; no architecture doc contradiction. |
| 10 | No M7+ contamination | 10 | Grep confirms no `TestingEvidence`/`TestOrchestrator`/`UserSimulation`/`SimplificationGate`; `EventType` count == 121; no second council/loop/kernel. |
| | **TOTAL** | **100** | |

**Pass threshold:** ≥ 90/100 AND no single dimension scoring 0 AND zero M7-contamination failures (dimension 10 must be ≥ 9/10).

---

## FINAL VERDICT

# READY FOR TERMINAL 2

The M6 scope is fully reconciled and unambiguous:
- **Authoritative source** (`FINAL_AI_OS_V2_ARCHITECTURE.md` §XXX/XXXI/XXXIX, PART VI/XVI/XVII, COUNCIL_SYNTHESIS, UPDATED_V2_MILESTONES, IMPLEMENTATION_PLAN §24) consistently defines M6 as exactly three deliverables: `CouncilManager.critique()` + `LLMCouncil` façade + `SelfPromptingService`.
- **Repository state verified:** no partial/accidental M6 code exists (grep for `LLMCouncil`/`SelfPrompt`/`def critique`/`def synthesize` → zero). M5 is independently verified complete (884 tests green).
- **Dependencies clear:** M6 depends on M4+M5 as enablers; delivers `critique()` that M7-F reuses. No M7 work required.
- **Non-goals explicit:** all M7+ functionality enumerated and prohibited.
- **Invariants enumerated** (single kernel/manager/router, security authority, provenance, advisory-vs-authoritative, bounded loop, dissent preservation, builder-exclusion, no second council/verification/loop).

Terminal 2 may implement M6 without making any architectural decision.
