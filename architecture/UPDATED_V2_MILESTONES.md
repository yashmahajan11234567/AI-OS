# UPDATED AI-OS NEXT DEVELOPMENT MILESTONES (V2) — TESTING EXTENSION

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Re-evaluate M4/M5/M6 against the new multi-perspective testing + User Simulation requirement, and propose the smallest meaningful milestone set.

> No implementation performed. All external capabilities consumed via `mcp_manager` (or ACP for Hermes). No kernel/council/verification change. `[AI-OS SOURCE]`

---

## 1. DECISION: KEEP M4/M5/M6, ADD M7 (smallest meaningful set)

The existing M4→M6 sequence (Skill standard+security gate → Integration backbone → Council synthesis/quality) is **still optimal** as a foundation. The testing requirement does **not** replace it — it *depends on it*:

- **M4** (canonical `SKILL.md` + SkillSpecTor gate) is the *prerequisite* for safely importing agency-agents testing personas and gating test-target MCPs.
- **M5** (integration backbone: Graphify, Agent-Reach, FreeLLMAPI, **Hermes bridge**) is the *prerequisite* for the User Simulation Agent (Hermes cloud-browser) and for driving Hermes tester workers.
- **M6** (MOA council technique + token compression) is the *prerequisite* for CouncilManager synthesis enrichment.

The testing layer therefore becomes **M7**, sequenced **after** M5 (needs the Hermes bridge) and **after** M6 (needs synthesis technique). It does NOT need to be split — it is one coherent "Multi-Perspective Testing & User Simulation" milestone that intensifies the existing `AIAgencyService` scaffold.

**Final set = M4, M5, M6, M7** (4 milestones). This is the smallest count that respects the dependency chain and the task's conceptual progression:
`V1 → Skill standard+security → Integration backbone → Council synthesis → Multi-perspective testing/User Sim → V2`.

---

## 2. M7 — MULTI-PERSPECTIVE TESTING & USER SIMULATION (P1, the new requirement)

**Objective:** Turn the simulated `AIAgencyService` + `TestingService` scaffold into a real, independent, multi-perspective testing system with a User Simulation Agent, feeding the existing verification + CouncilManager + closed loop.

**Architecture requirements:**
- Realize the 9 `AIAgencyService` agencies: replace heuristic string-matching with subagent/Hermes-worker execution. Each agency becomes a *perspective* emitting typed `TestingEvidence`. `[AI-OS SOURCE]`
- Add a **`UserSimulationAgent`** (new) — an AI Agency persona that drives the target app as a *user* (not developer) via **Hermes cloud-browser (ACP/MCP)**. `[LOCAL]`
- Add a **`TestOrchestratorService`** (new) — plans test perspectives, dispatches agencies (in parallel), collects evidence, normalizes, and convenes a testing council. `[AI-OS SOURCE]` `[INFERENCE]`
- Add a **structured `TestingEvidence` schema** (dataclass) replacing loose `findings[]` dicts. `[AI-OS SOURCE]`
- Extend `CouncilManager` with a **critique stage** adopting KKC (anonymized two-axis cross-ranking) + EVC (relabel-then-review + side-with-dissenter). `[EXTERNAL]`
- Enforce the **independence model** (PART 13): builder ≠ test-generator ≠ executor ≠ user-simulator ≠ judge. `[INFERENCE]`
- Test-environment isolation: per-run worktree/container. `[REFERENCE]`

**Components involved:** `core/ai_agency.py` (intensify), `services/testing.py` (intensify), `core/council_manager.py` (critique stage), new `core/test_orchestrator.py` + `core/user_simulation.py`, `events/types.py` (new evidence events), `mcp_manager` (Hermes). `[AI-OS SOURCE]`
**Repositories involved:** Hermes (INTEGRATION — browser/workers via ACP), agency-agents (SKILL/PERSONA SOURCE — curated tester personas), Karpathy LLM Council + evisoft Council (TECHNIQUE — critique stage), SkillSpecTor (INTEGRATION — security gate), Graphify (INTEGRATION — evidence graph). `[LOCAL]` `[EXTERNAL]`
**Dependencies:** M4 (persona adapter + SkillSpecTor gate), M5 (Hermes bridge + Agent-Reach), M6 (MOA/critique technique baseline).
**Implementation scope (future, not now):**
- Typed `TestingEvidence` + new events (`TestingEvidenceCollected`, `UserSimulationCompleted`, `TestPerspectiveFailed`).
- `UserSimulationAgent` driving Hermes `browser_*` tools via ACP session.
- `TestOrchestratorService` dispatching the 9 agencies + User Simulation in parallel, normalizing evidence, convening a `TestingCouncil`.
- `CouncilManager.critique()` stage (anonymized ranking + dissenter rule).
- Per-run isolation (worktree/container) for tester workers.
**Tests (future):** each agency produces real (non-heuristic) evidence for a fixture app; User Simulation completes a known workflow + reports a seeded usability defect; CouncilManager critique stage resolves a disagreement with dissenter-override; independence enforced (builder agent cannot vote in its own test council).
**QA requirements:** all V1 gates green; new unit + integration tests; no self-approval path.
**Acceptance criteria:** AI-OS can (a) run ≥9 independent testing perspectives against a target, (b) simulate a user via browser and report structured UX evidence, (c) synthesize perspectives through CouncilManager with blind cross-review, (d) route any FAIL into the existing RCA→Learning→Replan→Re-execute loop.
**Deliberately does NOT implement:** a second kernel/council/council-synthesis subsystem (Ruflo/KKC/EVC rejected as cores); replacing AI-OS verification; a production browser farm (Hermes cloud-browser is the substrate); importing all 230+ agency-agents personas (curate ~10).

---

## 3. REVISED MILESTONE DEPENDENCY GRAPH

```
V1 (verified, M0–M3)
   │
   ├─► M4  SKILL.md standard + SkillSpecTor gate      (foundation + persona import)
   │        │
   ├────────┼─► M5  Integration backbone                (Graphify / Agent-Reach /
   │        │        FreeLLMAPI / HERMES bridge via MCP/ACP)
   │        │              │
   │        │              └─► M6  Council synthesis (MOA technique) + Caveman (opt)
   │        │                          │
   │        └──────────────────────────┴─► M7  MULTI-PERSPECTIVE TESTING
   │                                            & USER SIMULATION
   │                                            (intensify AIAgencyService +
   │                                             UserSim Agent + TestOrchestrator +
   │                                             CouncilManager critique stage)
   ▼
V2
```

M4 is the foundation (standard + gate reused by M5/M6/M7). M5 delivers the Hermes bridge (required for M7's User Simulation). M6 delivers synthesis technique (required for M7's council critique). M7 is the testing realization — the new requirement.

---

## 4. WHAT THESE MILESTONES DELIBERATELY EXCLUDE

- **Ruflo** — competitor kernel; REFERENCE only.
- **Karpathy LLM Council / evisoft Council** — TECHNIQUE only (critique stage), never imported as subsystems.
- **Loop Engineering** — pattern cross-check (sandbox/worktree) only.
- **Free Claude Code** — OPTIONAL provider launcher.
- **Any second kernel / council layer / skill format / model router** — forbidden (consolidation rules).
- **Production browser farm** — Hermes cloud-browser is the substrate; no in-house farm.

---

## 5. OPEN QUESTIONS (evidence gaps)

1. Hermes `LICENSE` text not read verbatim — confirm permissive terms before M5/M7 bridge. `[LOCAL]` (unverified)
2. KKC/EVC are **unlicensed** (no LICENSE file) — adopt *techniques* only, do not vendor code. `[EXTERNAL]`
3. Hermes cloud-browser requires third-party credentials (Browserbase etc.) — CI/dev only, never production without SLA. `[LOCAL]`
4. agency-agents personas are MIT but must be *curated* — full import risks persona drift. `[EXTERNAL]`
5. Test reproducibility needs a fixture/seed model not yet designed. `[INFERENCE]`

---

*End of updated milestones. Smallest meaningful set = M4→M5→M6→M7 (4 milestones).*
