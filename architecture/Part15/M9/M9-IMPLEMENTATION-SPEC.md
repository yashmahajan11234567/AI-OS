# M9 — Learning / Adaptive Systems — IMPLEMENTATION SPECIFICATION

**Author**: Terminal 1 — Architecture / Planning / Inspection ONLY
**Date**: 2026-08-26
**Authority Chain**: Parts 0–14 > Accepted ADRs > Part 15 > M8 Closure Audit > Implementation > Tests
**Status of this document**: AUTHORITATIVE PLANNING OUTPUT for Terminal 2 (implementation) and Terminal 3 (independent QA).
**Constraint honored**: No production code was modified during planning. M7 FROZEN. M8 COMPLETE (Conditional GO) treated as a compatibility boundary.

> This specification is repository-grounded. Every scope claim is traced to a source file, line, or authoritative milestone document. Where the repository contains contradictory M9 definitions, the contradiction is documented (§3.2) and the authoritative source is named per the architecture hierarchy.

---

## 1. Executive Summary

M9 is the **Learning / Adaptive Systems** milestone. Its authority is the most recent authoritative planning artifact — `architecture/Part15/M8/M8_CLOSURE_AUDIT.md` §13 (2026-08-26):

> **M9 — Learning / Adaptive Systems** (per M9+ scope, explicitly excluded from M8): LearningService, RCA learning pipeline, model routing (FreeLLMAPI), convergence detection, adaptive replanning, autonomous learning.

**The single most important finding of this inspection:** M9 is **NOT** "build learning from scratch." The learning/adaptive *infrastructure largely already exists* as source classes in the repository:

- `LearningService` (`src/aios/services/learning.py`) — captures learnings, emits `LearningCaptured`.
- `RootCauseAnalyzer` (`src/aios/core/root_cause.py`) — classifies failures, recommends recovery.
- `ModelRouter` (`src/aios/core/model_router.py`) — routes LLM requests by capability/cost.
- `SelfPromptingService` (`src/aios/services/self_prompting.py`) — bounded, council-routed self-questioning (ADR #10).
- `TestOrchestratorService` closed-loop hook (`src/aios/services/testing.py:667-740`) — FAIL → RCA → Learning → Planning → re-execute, bounded.

**The genuine M9 gaps** span two integration/completeness gaps plus several bounded feature gaps that the master plan explicitly assigns to M9:

1. **GAP-A — Services are never wired into the running kernel.** No bootstrap code instantiates or registers any Engineering Service (`LearningService`, `PlanningService`, `CodingService`, `ReviewService`, `TestingService`, `DeploymentService`, `OperationsService`, `MemoryService`, `CouncilService`, `MCPService`, `SkillService`) into the canonical `ServiceRegistry`. The kernel only `start()`s services already present in the registry (`kernel.py:1314-1361`). A `register_service()` API exists (`kernel.py:371-395`) but is never called for engineering services. **Consequence:** `LearningService.on_start()` never runs, `RootCauseAnalyzer` is never constructed by the kernel, and the closed loop described in `testing.py` only fires if a caller manually injects singletons.

2. **GAP-B — Learning is capture-only; nothing reuses it.** `LearningService` stores learnings in a private in-memory `_learnings` list (`learning.py:43`) and emits `LearningCaptured` events, but exposes **no retrieval/apply accessor** (no `get_learnings()`, no query, no planning integration). RootCauseAnalyzer → LearningService wiring is fragile (`root_cause.py:367-416`: synchronous call into an async coroutine via `loop.create_task`, bare `except`, `print()` debug noise). **Consequence:** failures are captured but never retrieved to inform future planning/replanning — the "adaptive" half of M9 does not function.

3. **GAP-C — Convergence detection absent.** `grep -rniE "convergen" src/aios/` returns ZERO matches. The closed loop has no "no-improvement / converged" signal. Per master plan §1124 + closure audit §239, convergence IS in M9 (bounded, advisory; signals escalate, does not assume authority).

4. **GAP-D — SelfPromptingService uses mock scoring.** `self_prompting.py:228-242` derives accuracy/insight scores from `hash(mid)%30`. Per master plan §1123, M9 replaces mock scores with real LLM-council/ModelRouter-derived scoring, keeping ADR #10 bounds (`max_depth=5`, `token_budget=4000`).

5. **GAP-E — Human escalation not bound-triggered.** `_escalate_to_human` (`workflow.py:858-876`) exists but is not triggered by learning/self-prompting/closed-loop bound exhaustion. Per master plan §1125, M9 wires "bounds exhausted → escalate to human".

M9 = **wire the existing services into the kernel lifecycle (GAP-A)** + **close the capture→retrieve→apply loop with bounded, authority-preserving learning (GAP-B)** + **convergence detection (GAP-C)** + **SelfPrompting real scoring (GAP-D)** + **human-escalation wiring (GAP-E)** + **consume the M8-provenance/evidence substrate** + **address the M8-deferred items that are genuinely M9** (Graphify-based automated remediation; capability manifest hot-reload; ACP session-TTL hardening; 5 C14 provenance xfails).

**Explicitly quarantined to M10+** (see §3.5/§3.6): **adaptive replanning** (autonomous loop authority — contradicts §16), autonomous PASS/FAIL decisions, deployment/ops, security-hardening audit. Convergence detection is IN M9 (bounded/advisory) per the master plan + closure audit; only M8-T3's per-task note pushed it to M10, which this spec overrides (§3.5).

---

## 2. M9 Objective

Enable AI-OS to **capture, retain, retrieve, and boundedly apply** engineering intelligence (learnings) from execution outcomes — failures and successes — through the existing `LearningService` / `RootCauseAnalyzer` / `PlanningService` services, wired into the real kernel lifecycle, while preserving all M8 authority/trust boundaries (Councils/Judge retain sole decision authority; externals remain advisory/observation-only). Model routing (`ModelRouter`) is made available to services that need LLM selection. Learning must be **traceable, bounded, and non-escalating** — it informs planning; it never issues PASS/FAIL/approve/reject verdicts or modifies authoritative state.

---

## 3. Authoritative Scope

### 3.1 Authoritative M9 definition

| Source | Statement | Status |
|--------|-----------|--------|
| `architecture/Part15/M8/M8_CLOSURE_AUDIT.md` §13 | "M9 — Learning / Adaptive Systems … LearningService, RCA learning pipeline, model routing (FreeLLMAPI), convergence detection, adaptive replanning, autonomous learning." | **AUTHORITATIVE** — most recent, purpose-written milestone definition. |
| `architecture/Part15/M8/M8_CLOSURE_AUDIT.md` §9 | "LearningService / RCA pipeline / model routing / convergence / adaptive replanning — M9+ scope. Explicitly out of M8." | Confirms M9 ownership. |
| `architecture/Part15/M8/M8-T3-IMPLEMENTATION-SPEC.md` §1355-1371 | LearningService/RCA/model router → **M9**; Convergence detection → **M10**; Graph-based automated remediation → **M9**; Adaptive replanning → **M10**. | **AUTHORITATIVE per-task boundary** for the M9/M10 split. |
| `M8-T1/T2/T3/T5 IMPLEMENTATION-SPEC.md` (Non-goals) | Each M8 task lists "LearningService integration / ModelRouter real integration / RCA pipeline = M9" as out of scope. | Confirms M9 is the consumer milestone. |

### 3.2 CONTRADICTION (documented, not silently resolved)

The label "M9" appears in **two incompatible senses** in the repository:

- **Sense 1 (Milestone M9):** "Learning / Adaptive Systems" — `M8_CLOSURE_AUDIT.md` §13. This is the milestone definition used throughout this spec.
- **Sense 2 (Component slot M9):** In `architecture/Part15/context.md:424` and `architecture/Part15/runtime-map.md` (lines 150, 227, 246, 343, 532), "M9" denotes the **9th Core Manager = ObservabilityManager** (Phase 8, last to init). This is a *component-numbering* usage inside the unresolved `CONFLICT-CM-01` (Part 0/Part 1/Part 4 manager-slot mapping disagreement).

**Resolution per architecture hierarchy:** The *milestone* "M9" is authoritative from the Closure Audit (a milestone-planning document written after the Part 15 component docs and explicitly scoped to name the next milestone). The *component* "M9 = ObservabilityManager" is a pre-existing, unresolved naming conflict (`CONFLICT-CM-01`) that this spec does **not** resolve — ObservabilityManager is already implemented (`src/aios/core/observability_manager.py`) and is **explicitly out of M9 scope**. Terminal 2 and Terminal 3 must not conflate the two; when this spec says "M9" it means the *milestone*.

### 3.3 REQUIRED FOR M9 (derived scope)

1. **Wire Engineering Services into the kernel lifecycle (GAP-A).** Add a kernel bootstrap that instantiates and registers the engineering services into the canonical `ServiceRegistry` (under `engineering.<name>`), honoring dependency order (`learning` depends on `memory` per `learning.py:39`; `testing` depends on security/learning/planning/RCA per `testing.py:123`). Kernel `start()` then starts them (`kernel.py:1314-1361` already does this for registered services).
2. **Close the capture→retrieve→apply loop (GAP-B).** Add a retrieval/query API to `LearningService` (bounded, in-memory or MemoryManager-backed) and integrate it so `PlanningService` can read relevant prior learnings when producing a plan/replan. Replace the fragile `root_cause.py:367-416` sync-into-async call with a correct async handoff.
3. **Make `ModelRouter` available to services needing LLM selection** (it already exists; ensure it is registered/accessible and optionally exercised by FreeLLMAPI capability — see §7.4). No new provider SDK required (Tier C unavailable — see §26).
4. **SelfPromptingService → bounded adaptive reasoning** is already implemented (ADR #10); M9 must ensure it is registered and its bounds (`max_depth=5`, `token_budget=4000`) are enforced and observable, not altered.
5. **Graph-based automated remediation (M8-T3 §1371 = M9):** consume the M8 Graphify adapter (`graphify_adapter.py`) to propose remediation actions from the knowledge graph — **as advisory input to PlanningService/RCA, never as autonomous execution**.
6. **M8-deferred items that are genuinely M9:** capability manifest **hot-reload** (`M8_CLOSURE_AUDIT.md:158`), ACP **session-TTL hardening** (`M8_CLOSURE_AUDIT.md:159`), and the **5 C14 provenance xfails (D-03..D-06)** — bring correlation_id propagation + advisory markers to the missing paths (Playwright D-05, Obsidian-fallback D-06, Graphify-write D-03, orchestrator→adapter correlation D-04).
7. **Convergence detection (bounded, advisory)** — `src/aios/` contains ZERO convergence logic (verified grep). Per master plan §1124 + closure audit §239, IN M9. Implement as a **bounded** detector in the closed loop that signals "no-improvement / escalate" and routes to the existing human-escalation path (`workflow.py:858-876`); must NOT assume autonomous authority.
8. **SelfPromptingService real scoring** — `self_prompting.py:228-242` uses **mock** accuracy/insight scores (`hash(mid)%30`). Per master plan §1123, M9 replaces mock scores with real LLM-council/ModelRouter-derived scoring, keeping ADR #10 bounds (`max_depth=5`, `token_budget=4000`) intact.
9. **Human escalation path** — `_escalate_to_human` (`workflow.py:858-876`) exists but is not triggered by learning/self-prompting bound exhaustion. Per master plan §1125, M9 wires "bounds exhausted → escalate to human" from the learning/self-prompting/closed-loop bounds.

### 3.4 SUPPORTING INFRASTRUCTURE ALREADY PRESENT (consume, do not rebuild)

- `LearningService` (`services/learning.py`) — capture + `LearningCaptured` emit.
- `RootCauseAnalyzer` (`core/root_cause.py`) — classification + recovery recommendation.
- `ModelRouter` (`core/model_router.py`) — capability/cost-based routing.
- `SelfPromptingService` (`services/self_prompting.py`) — bounded council-routed self-questioning.
- `TestOrchestratorService` closed-loop hook (`testing.py:667-740`).
- `CapabilityProvenance` + `mark_capability_advisory` (`capability_provenance.py`) — spoof-proof advisory provenance (M8-T5).
- `TestingEvidence` (`testing_evidence.py`) — structured evidence schema (M7).
- `GraphifyAdapter` (`adapters/graphify_adapter.py`) — advisory knowledge graph (M8-T3).
- Structured logging / correlation IDs (`structured_logger.py`, `observability_manager.py`).

### 3.5 CONVERGENCE / ADAPTIVE-REPLAN — CONFLICT RESOLVED WITH DOCUMENTATION

The M9/M10 boundary for **convergence detection** and **adaptive replanning** is genuinely contested across authoritative sources. Documented, not silently resolved:

| Item | Source says | Verdict for this spec |
|------|-------------|----------------------|
| **Convergence detection** | `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md` §1116-1145: **M9** (component 4, "Closed loop detects convergence/no-improvement"). `M8_CLOSURE_AUDIT.md` §239: **M9** ("convergence detection"). `M8-T3-IMPLEMENTATION-SPEC.md` §1358: **M10**. | **IN M9** (2 of 3 authoritative milestone docs place it in M9; M8-T3's "M10" was a per-task *non-implementation* note for M8-T3, not a final milestone verdict). Must be **bounded & advisory** — it signals "no further improvement / escalate", it does NOT grant autonomous authority. |
| **Adaptive replanning** | `M8_CLOSURE_AUDIT.md` §239: **M9** ("adaptive replanning"). `M8-T3` §1371 / `M8-T4` §1099-1100 / `M8-T6` §413-414: **M10**. | **M10+** (quarantine). "Autonomously re-plan when stuck" requires convergence signal + autonomous loop authority M9 must not assume. M9 *feeds* learnings/remediation to `PlanningService` (advisory); it must NOT run an autonomous replan loop. This is the one item where the closure audit over-lists M9 vs the per-task specs; quarantined to M10+ per the stricter per-task boundary and the authority-preservation rule (§16). |

**Resolution principle:** The master plan (highest-level milestone roadmap, post-M7) + closure audit govern milestone *naming*; convergence is IN M9. Adaptive replanning is quarantined to M10+ because it is the only item that would require M9 to assume autonomous loop authority, which contradicts the inviolable authority boundary (§16). Terminal 3 must verify convergence is implemented bounded/advisory and that no autonomous replan loop exists.

### 3.6 DEFERRED TO M10+ (quarantine — NOT M9)

| Item | Source | Why deferred |
|------|--------|--------------|
| **Adaptive replanning** (autonomous loop) | M8-T3 §1371 / M8-T4 §1099 / M8-T6 §413 | Requires autonomous loop authority; contradicts §16. M9 feeds learnings, does not replan autonomously. |
| Autonomous PASS/FAIL decisions | M8 Closure §3 | Councils/Judge authority is inviolable. |
| Distributed graph infra / graph ML / embeddings | M8-T3 §1365-1369 | Future. |
| Deployment/ops (Docker, health, CLI) | Master Plan M10 | M10. |
| Security hardening audit | Master Plan M11 | M11. |
| Real external services (Tier C) | M8 Closure §7 | No credentials/instances in this environment. |

---

## 4. Non-Goals

M9 MUST NOT:
- Modify or reopen M7 agency internals, `CouncilManager`, `final_judge_agency.py`, `TestingEvidence` semantics, or provenance semantics (additive config only).
- Modify `mcp_manager.py`, `acp_adapter.py`, Playwright/Graphify/Notion/Obsidian/Claude-Mem adapters (M8 COMPLETE boundary) except for the narrow advisory-marker/correlation_id additions on the D-03..D-06 paths (§3.3.6) — and even those are compatibility fixes, not re-architecture.
- Implement convergence detection or adaptive replanning (M10+).
- Implement autonomous approval/rejection, authority escalation, or unrestricted external code execution.
- Vendor or adopt external learning subsystems (Ruflo/KKC/EVC are REFERENCE/TECHNIQUE only — per V2 ADR).
- Add new EventTypes (reuse canonical types; `LearningCaptured` already exists at `events/types.py:1212`).
- Build a production browser farm, real FreeLLMAPI calls, or any Tier-C external execution.

---

## 5. Current Repository State

- **Branch**: `main`. **M7**: COMPLETE/FROZEN. **M8**: COMPLETE (Conditional GO, Terminal 3 final GO on T7, 2026-08-26).
- **Kernel**: `HermesKernel` (`core/kernel.py`), 9 Core Managers registered (LifecycleManager, StateManager, StorageManager, HealthManager, ResourceManager, SecurityManager, CapabilityManager, WorkflowManager, ObservabilityManager).
- **Engineering services**: defined in `src/aios/services/` but **not instantiated/registered by any bootstrap** (GAP-A).
- **Test baseline (M8 Closure §8, 2026-08-26)**: `collected 1578 · passed 1570 · failed 0 · skipped 3 · xfailed 5 · exit 0`. Reproduced via `python -m pytest --collect-only -q` → **1578 collected**.
- **Known flaky**: `tests/performance/test_structured_logger_perf.py` order-dependent correlation test (pre-existing, quarantine/retry).
- **Known xfails (5, genuine, non-blocking)**: D-03 (Graphify-write advisory), D-04 (orchestrator→adapter correlation_id), D-05 (Playwright advisory), D-06 (Obsidian-fallback advisory).

---

## 6. Completed-Milestone Dependencies

| Milestone | What M9 consumes | Evidence |
|-----------|------------------|----------|
| M7 (FROZEN) | `TestingEvidence`, `TestOrchestratorService`, 9 agencies, `CouncilManager`, `UserSimulationAgent`, `AIAgencyService`, `Provenance` | `M8_CLOSURE_AUDIT.md` §8 |
| M8-T1 | `AcpAdapter`/`AcpSession`/`HermesBridge` (observation-only, `trust_level="untrusted"`) | `hermes_bridge.py` |
| M8-T2 | `PlaywrightMCPAdapter` (execution substrate, never verdicts) | `playwright_mcp_adapter.py:98` |
| M8-T3 | `GraphifyAdapter` (advisory, `_mark_advisory`) — used for graph-based remediation (§3.3.5) | `graphify_adapter.py` |
| M8-T4 | Notion/Obsidian/Claude-Mem adapters (advisory knowledge/context) | 3 adapters |
| M8-T5 | `CapabilityProvenance`, `capability_manifest.py`, `adapter_factory.py`, capability security gate (INTEGRATION FILTER, not authority) | `capability_manager.py` |
| M8-T6 | D-01..D-12 production-path remediation | source |
| M8-T7 | DEF-01 fixed (MCP transport coercion); 32 regression tests; full regression green | `M8_CLOSURE_AUDIT.md` §4 |

---

## 7. M8→M9 Handoff

### 7.1 What M8 made available to M9
- A spoof-proof, advisory-marked provenance substrate (`CapabilityProvenance.mark_capability_advisory`) — M9 learning records must reuse it.
- A real Graphify knowledge-graph adapter (advisory) for graph-based remediation.
- Capability manifest loading/registry with security context (M9 hot-reload extends this).
- Production-path (Tier B) MCP/ACP connection chain, verified end-to-end.

### 7.2 What M8 deliberately did NOT implement (and M9 owns)
- LearningService/RCA/model-routing **integration/wiring** (M8-T1/T2/T3/T5 Non-goals).
- **Convergence detection / adaptive replanning** (deferred to M10 — M8-T3/T4/T6).
- Capability manifest **hot-reload**, ACP **session-TTL** tuning (M8 Closure §9 deferred to M9+).
- The 5 C14 provenance xfails (M8 Closure C1: "track to M9+ if desired").

### 7.3 Compatibility boundary M9 must respect
M9 MUST keep all M8 acceptance gates green:
- Authority: Councils/Judge sole decision authority; externals advisory/observation only (`M8_CLOSURE_AUDIT.md` §3).
- Fail-closed security; capability gate rejects `authoritative`; manifests reject `trust_level=builtin|trusted` (`M8_CLOSURE_AUDIT.md` §3).
- No new `EventType` members.

### 7.4 ModelRouter / FreeLLMAPI
`ModelRouter` exists and is kernel-accessible (`kernel.py:337-339`, `model_router.py`). M9 makes it available to services that select LLMs. **FreeLLMAPI** is an external MCP server (M5 design) with **no credentials/Tier-C availability** in this environment — M9 may register a FreeLLMAPI capability manifest (advisory) but must NOT require a live call to pass. Model routing selection is exercised via in-process routing logic + mock, not real provider egress.

---

## 8. Existing Components (consume)

| Component | File | Role in M9 |
|-----------|------|-----------|
| `LearningService` | `services/learning.py` | Capture learnings; **extend with retrieval API (GAP-B)** |
| `RootCauseAnalyzer` | `core/root_cause.py` | Classify failures; **fix async handoff to LearningService (GAP-B)** |
| `ModelRouter` | `core/model_router.py` | LLM selection; register/accessible |
| `SelfPromptingService` | `services/self_prompting.py` | Bounded self-questioning; register + enforce bounds |
| `PlanningService` | `services/planning.py` | **Consume retrieved learnings for plans/replans (GAP-B)** |
| `TestOrchestratorService` | `services/testing.py` | Closed-loop hook already present; wire via bootstrap |
| `CouncilManager` / `FinalJudge` | `core/council_manager.py`, `core/final_judge_agency.py` | **FROZEN** — sole decision authority |
| `CapabilityProvenance` | `core/capability_provenance.py` | M9 learning/advisory records reuse `mark_capability_advisory` |
| `GraphifyAdapter` | `adapters/graphify_adapter.py` | Graph-based remediation input (advisory) |
| `ServiceRegistry` | `core/service_registry.py`, `services/registry.py` | Target of bootstrap registration |
| `HermesKernel.register_service` | `core/kernel.py:371` | API to register engineering services |

---

## 9. Missing Components (to create / complete)

| ID | Component | Type | Notes |
|----|-----------|------|-------|
| M9-N1 | Engineering-service bootstrap | NEW (in kernel or `services/bootstrap.py`) | Instantiate + register all engineering services in dependency order (GAP-A). Must be idempotent & testable without a live kernel. |
| M9-N2 | `LearningService.get_learnings()` / query API | NEW method | Bounded retrieval by `failure_category`, `analysis_id`, recency. Returns copies (no external mutation of authoritative state). |
| M9-N3 | `PlanningService` learning-ingest hook | NEW integration | On plan/replan, query M9-N2 for relevant learnings; attach as advisory context. **Does not alter Council/Judge authority.** |
| M9-N4 | Correct RCA→Learning async handoff | FIX in `root_cause.py` | Replace `root_cause.py:367-416` sync-into-async with proper `await`/task scheduling; remove `print()` noise; narrow `except`. |
| M9-N5 | Graph-based remediation proposer | NEW (advisory) | Uses `GraphifyAdapter` to propose remediation from failure context; output is advisory input to PlanningService/RCA. |
| M9-N6 | Capability manifest hot-reload | EXTEND `capability_manifest.py` | Watch/reload manifest files; re-register with security gate; fail-closed. |
| M9-N7 | ACP session-TTL hardening | EXTEND `acp_adapter.py`/`acp_session.py` | Enforce/extend session TTL; do not alter observation-only boundary. |
| M9-N8 | C14 provenance closure (D-03..D-06) | FIX on M8 adapters | correlation_id propagation + advisory markers on Graphify-write/Playwright/Obsidian-fallback/orchestrator→adapter paths. Convert xfails → passes only if genuine (no assertion weakening). |
| M9-N9 | Convergence detection (bounded, advisory) | NEW | Detect "no-improvement / converged" in the closed loop; signal escalate; route to human-escalation path. Zero existing logic (verified). Bounded, advisory-only. |
| M9-N10 | SelfPromptingService real scoring | FIX in `self_prompting.py:228-242` | Replace mock `hash(mid)%30` scores with real LLM-council/ModelRouter-derived scoring; keep ADR #10 bounds. |
| M9-N11 | Human-escalation wiring | FIX in `workflow.py` + closed loop | Trigger `_escalate_to_human` (`workflow.py:858-876`) from learning/self-prompting/closed-loop bound exhaustion. |

---

## 10. Production Call-Path Architecture

### 10.1 Bootstrap path (GAP-A) — NEW
```
HermesKernel.start()
  └─ _start_services()                      # kernel.py:1274
       └─ bootstrap_engineering_services(registry)   # M9-N1 (NEW)
            ├─ PlanningService()  → registry.register(engineering.planning)
            ├─ LearningService()  → registry.register(engineering.learning)   # depends_on memory
            ├─ CodingService() / ReviewService() / TestingService() / ...
            ├─ ModelRouter already a singleton (get_model_router())
            └─ SelfPromptingService() → registry.register(engineering.self_prompting)
       └─ for svc in registry(ENGINEERING): await svc.start()   # kernel.py:1342 (existing)
            └─ LearningService.on_start() → subscribe(RootCauseResolved) + set_learning_service_instance(self)
```

### 10.2 Capture path (existing, wired by M9)
```
Failure occurs
  → WorkflowManager / TestOrchestratorService emits WORKFLOW_FAILED / TESTING_FAILED
  → RootCauseAnalyzer._on_task_failed / _on_retry_budget_exhausted   # root_cause.py:210
  → RootCauseAnalyzer.analyze(ctx) → RootCauseAnalyzed event
  → M9-N4 (corrected) → LearningService.capture_learning_from_analysis(...)  # async, awaited
  → LearningService stores in _learnings + emits LearningCaptured
```

### 10.3 Retrieve/apply path (GAP-B) — NEW
```
PlanningService.plan(objective)
  → M9-N3: query LearningService.get_learnings(failure_category=…, limit=k)
  → attach retrieved learnings as ADVISORY context to the plan
  → CouncilManager retains decision authority; learnings are input only
```

### 10.4 Remediation proposal path (M9-N5) — NEW, advisory
```
RootCauseAnalyzed
  → GraphRemediationProposer.propose(failure_context)   # queries GraphifyAdapter (advisory)
  → returns AdvisoryRemediation(suggestions=[…], authority=advisory_only)
  → fed to PlanningService as advisory context (same channel as M9-N3)
```

---

## 11. Component-by-Component Implementation Plan

### 11.1 M9-N1 — Engineering-service bootstrap (GAP-A)
- Create `src/aios/services/bootstrap.py` (or extend `kernel.py:_start_services`) with `bootstrap_engineering_services(registry: ServiceRegistry) -> list[BaseService]`.
- Instantiate each engineering service once; call `registry.register(svc)` (uses `engineering.<name>` id per `services/registry.py:78`).
- Honor `depends_on` (see `learning.py:39` → `memory` must be available; `memory` is a Core Manager, already registered).
- Make it importable & callable without a full kernel (for unit tests): accept an injected registry.
- Do NOT change `kernel.py:1314-1361` start loop; it already starts registered services.
- **Frozen check:** no change to `CouncilManager`, `final_judge_agency.py`, agency internals.

### 11.2 M9-N2 — LearningService retrieval API (GAP-B)
- Add `get_learnings(self, *, failure_category=None, analysis_id=None, limit=50, since=None) -> list[dict]` returning **shallow copies**.
- Add `query_relevant(self, objective: str, limit=5) -> list[dict]` (simple keyword/recency match; no ML/embedding — embeddings are M10+).
- Keep `_learnings` as the store; optionally persist to MemoryManager (Engineering Intelligence category) — advisory only.
- No new EventType.

### 11.3 M9-N3 — PlanningService learning ingest
- In `PlanningService.plan()` / replan path, call `get_learning_service().get_learnings(...)` (guarded — service may be absent in minimal kernels).
- Attach as `advisory_context` field on the plan payload; **never** as a directive that overrides Council/Judge.
- Emit `PlanGenerated` with advisory learning refs (reuse existing canonical type if present; else `AI_AGENT_AUDIT_EMITTED` like `learning.py:63`).

### 11.4 M9-N4 — RCA→Learning correct handoff
- Replace `root_cause.py:367-416` block: await `capture_learning_from_analysis` via the running event loop properly (or emit `LearningCaptured` and let `LearningService.handle_root_cause_resolved` do the capture — cleaner, event-driven).
- Remove all `print()` debug statements in `root_cause.py` and `learning.py` (replace with `logger`).
- Narrow `except Exception` → specific exceptions; never swallow learning failures silently (log + continue is acceptable but must be logged).

### 11.5 M9-N5 — Graph-based remediation proposer (advisory)
- New `src/aios/services/remediation.py` (or `core/graph_remediation.py`): `GraphRemediationProposer`.
- Uses `GraphifyAdapter.query_graph`/`shortest_path` (M8-T3). Output `AdvisoryRemediation` forced `authority=advisory_only` via `mark_capability_advisory`.
- Never executes; returns suggestions only.

### 11.6 M9-N6 — Capability manifest hot-reload
- Extend `capability_manifest.py`: file-watch (or explicit `reload()` API) re-reads manifests, re-registers via `CapabilityManager.register_capability`, re-runs the M8-T5 security gate. Fail-closed on invalid manifest.
- Guard against trust escalation (reuse M8-T5 `CM-SHADOW-001`/`CM-PREC-001`).

### 11.7 M9-N7 — ACP session-TTL hardening
- Extend `acp_session.py` session TTL enforcement; do not change observation-only docstring/boundary (`HermesObservation.trust_level="untrusted"` stays).

### 11.8 M9-N8 — C14 provenance closure (D-03..D-06)
- D-03: Graphify-write path — assert `mark_capability_advisory` on write results.
- D-04: propagate `correlation_id` from orchestrator into adapter `ExecutionResult.provenance`.
- D-05: Playwright adapter — assert advisory marker on all results.
- D-06: Obsidian-filesystem fallback — assert advisory marker.
- Convert xfails (`test_m8_t6_evidence_provenance.py:165,411,428,443,461`) to passing **only if the gap is genuinely closed**; otherwise keep `xfail(strict=False)`.

---

## 12. Data Flow

```
Execution outcome (success/failure)
   │
   ├─► RootCauseAnalyzer (on failure) ─► RootCauseResolved / RootCauseAnalyzed
   │        └─► LearningService.capture (M9-N4 fixed) ─► _learnings + LearningCaptured
   │
   ├─► GraphRemediationProposer (M9-N5, on failure) ─► AdvisoryRemediation (advisory_only)
   │
   └─► Next PlanningService.plan(objective)
            ├─ M9-N3: get_learnings(relevant)  ──┐
            ├─ M9-N5: AdvisoryRemediation        ──┤ (advisory context)
            └─► Plan payload (advisory_context=[learnings, remediation])
                     └─► CouncilManager (DECISION AUTHORITY — unchanged)
                              └─► WorkflowManager executes (unchanged)
```

All learning/remediation data is **advisory input**; Councils/Judge/WorkflowManager authority is unchanged from M8.

---

## 13. State / Lifecycle Model

- **Learning store**: in-memory `_learnings` (M9-N2) + optional MemoryManager persistence (advisory). Lifecycle tied to `LearningService` instance (kernel-bound singleton via `set_learning_service_instance`).
- **Service lifecycle**: `CREATED → RUNNING` via `BaseService.start()` (`base.py:158`); kernel starts registered services in dependency order (`kernel.py:1342`). `STOPPED` on `_stop_engineering_services` (`kernel.py:1382`).
- **Bootstrap idempotency**: re-running `bootstrap_engineering_services` replaces existing instances (`registry.register` re-registers, `services/registry.py:78`).
- **Remediation proposals**: stateless, per-failure, advisory.
- **No new FSM states** in kernel; reuse existing lifecycle.

---

## 14. Provenance Requirements

- Every M9 learning record and advisory remediation MUST carry `CapabilityProvenance` fields: `task_id`, `execution_id`, `session_id`, `correlation_id`, `adapter`, `operation`, `timestamp`, `request_id`, `protocol`, `source`, `advisory=True`, `authority`, `trust_level=untrusted` (`capability_provenance.py`, `M8_CLOSURE_AUDIT.md` §5).
- External/Graphify-derived data MUST be re-marked advisory via `mark_capability_advisory` (force-reasserts after merge — spoof-proof).
- M9-N8 closes the 5 C14 gaps so correlation_id propagates and advisory markers appear on all paths.
- **Provenance cannot be spoofed by external data** — preserved by construction (M8-T5).

---

## 15. Evidence Requirements

- `TestingEvidence` (M7) remains the structured evidence schema; M9 learning capture references `execution_id`/`correlation_id` from evidence.
- `LearningCaptured` event (`events/types.py:1212`) is the evidence emission for a captured learning.
- Graph remediation proposals carry graph-query provenance (source=graphify, advisory).
- All M9 evidence must be reproducible in CI (Tier A/B; no Tier C).

---

## 16. Authority / Trust Boundaries

**Inviolable (from M8 Closure §3):**
- Councils/Judge = sole decision authority (`council_manager.py`, `final_judge_agency.py` FROZEN).
- SecurityManager = security authority; capability gate = INTEGRATION FILTER, not final authority.
- WorkflowManager = orchestration authority.
- StateManager = source of truth; no external adapter writes authoritative state.
- Externals (Hermes/Playwright/Graphify/Notion/Obsidian/Claude-Mem) = advisory/observation only.
- **M9 learning/remediation output is advisory input to PlanningService, never a verdict or state mutation.**

M9 MUST add an authority test asserting: a retrieved learning or graph remediation proposal cannot set `authority=authoritative` or `trust_level=trusted/builtin`.

---

## 17. Security Requirements

- Fail-closed: manifest hot-reload (M9-N6) rejects invalid/escalating manifests.
- No `trust_level=builtin|trusted` or `authority_classification=authoritative` from any M9-generated manifest (`capability_manifest.py` already rejects; reuse).
- Secret scrubbing preserved (M8-T5 env-scrub + `SENSITIVE_PROPERTY_KEYS`).
- Session isolation preserved (Hermes/Playwright session registries).
- SelfPromptingService bounds (`max_depth=5`, `token_budget=4000`) enforced and observable (ADR #10) — M9 registers it but does not relax bounds.
- Learning store must not expose secrets: scrub before storing (reuse SecurityManager scrubbing patterns).

---

## 18. Failure / Recovery Model

- Learning capture failure is **best-effort, non-blocking** (per `testing.py:715` comment) — but MUST be logged, not silently swallowed (fixes M9-N4).
- RCA failure → does not block the workflow; escalation path (`workflow.py:863` "Escalating to human") unchanged.
- Manifest hot-reload failure → keep previous valid registry; fail-closed.
- Bootstrap failure for one service → kernel logs and continues with others (`kernel.py:1354` pattern); does not crash kernel.
- No new retry/escalation authority assumed by M9.

---

## 19. Configuration Requirements

- Engineering-service bootstrap enabled by default in full kernel; optional `services.enabled` allowlist in `config/defaults.yaml` (additive — do not remove existing keys).
- ModelRouter configuration (`model_router.py`) already present; M9 may add a `free_llm_api` advisory capability manifest under `config/mcp/` (no live call required).
- Manifest hot-reload: `capability.hot_reload: bool` (default false) in `config/defaults.yaml`.
- ACP session TTL: `acp.session_ttl_seconds` (default preserved from M8) in `config/defaults.yaml`.
- No change to `config/capabilities/` schema beyond what M8-T5 defined.

---

## 20. Capability Integration Requirements

- M9 reuses `CapabilityManager` + `capability_manifest.py` (M8-T5). New advisory capabilities (FreeLLMAPI, graph-remediation) register through the **existing** manifest path with `authority=advisory_only`.
- Hot-reload (M9-N6) must re-run the M8-T5 security gate and collision/shadow guards (`CM-SHADOW-001`, `CM-PREC-001`).
- M9 must not bypass `register_capability`'s precedence/collision logic.

---

## 21. MCP / ACP Integration Requirements

- **ACP (M8-T1):** M9-N7 hardens session TTL only; observation-only boundary (`trust_level="untrusted"`) unchanged.
- **MCP (M8-T5):** FreeLLMAPI capability registered advisory; no live call required (Tier C unavailable). ModelRouter usable in-process.
- No change to `mcp_manager.py` transport coercion (DEF-01 fixed in M8-T7) except if a genuine M9 bug is proven (document as finding, not fix during planning).
- M9-N8 advisory-marker fixes touch adapter result construction only — compatibility fixes.

---

## 22. Agency / Agent Integration Requirements

- **M7 FROZEN.** M9 does not modify any agency adapter, `AIAgencyService`, `CouncilManager`, `UserSimulationAgent`, or `TestingEvidence` semantics.
- `TestOrchestratorService` closed-loop hook (`testing.py:667-740`) is exercised via the bootstrap (M9-N1) — it already references `self._learning`/`self._rca`/`self._planning` injected singletons. M9 ensures those singletons are populated by the kernel (GAP-A), so the loop fires in a real kernel without manual injection.
- Independence model (PART 13: builder ≠ tester ≠ judge) preserved — M9 learning is consumed by PlanningService, not by the judge.

---

## 23. Memory / Learning Integration Requirements

- `LearningService` depends on `memory` (`learning.py:39`); MemoryManager is a Core Manager, available before engineering services start.
- Optional persistence of learnings to MemoryManager "Engineering Intelligence" category (advisory).
- Retrieval (M9-N2) is the missing half; PlanningService ingest (M9-N3) closes the loop.
- **Convergence/adaptive-replan (M10+) explicitly out of scope** — learnings feed planning but do not trigger autonomous replan loops.

---

## 24. Testing Strategy

Tier classification (per M8 IND-6 lesson + Closure §7):
- **Tier A — in-process mock:** adapter logic, LearningService capture/retrieve, RCA classification, planner ingest, remediation proposer (Graphify mock).
- **Tier B — production-style local subprocess:** bootstrap registers services into a real `ServiceRegistry` constructed via the canonical API; kernel `start()` path exercised against in-tree mocks (no live externals).
- **Tier C — real external service:** NOT achievable (no credentials/instances). Do NOT claim Tier C.

**M8 IND-6 lesson (mandatory):** A test fixture MUST NOT silently inject corrected runtime objects that stock boot would fail to construct. For GAP-A tests, construct the registry via the **real** `register_service`/`bootstrap` path, not a hand-injected singleton. For GAP-B, exercise the **real** `LearningService` instance created by the bootstrap, not a pre-seeded mock.

Required test categories (all mandatory):
1. Unit — capture/retrieve/query, RCA classification, planner ingest, remediation proposer, manifest hot-reload, ACP TTL.
2. Integration — bootstrap registers all services; kernel `start()` starts them; closed loop fires (FAIL→RCA→Learning→Planning→re-execute) with real instances.
3. Production-style subprocess (Tier B) — full kernel boot with engineering services, no live externals.
4. Failure/recovery — learning capture failure non-blocking; manifest reload fail-closed; bootstrap partial failure.
5. Security — advisory/trust cannot escalate; secret scrubbing in learning store; manifest rejects `authoritative`.
6. Provenance — correlation_id propagates (D-04); advisory markers on all paths (D-03/05/06); spoof-proof re-mark.
7. Authority-boundary — learning/remediation cannot set `authoritative`/`trusted`; Councils/Judge unchanged.
8. Session/isolation — per-session provenance; ACP session TTL.
9. Configuration — `services.enabled` allowlist; `hot_reload` flag; `acp.session_ttl`.
10. Regression — full existing suite remains green (1570 passed baseline).
11. M7 freeze — no M7 file modified; M7 regression (83 passed) intact.
12. M8 compatibility — all M8 acceptance gates green; DEF-01 32 tests pass; 5 xfails genuine.
13. Adversarial — attempt to inject `authoritative`/`trusted` via learning or manifest → rejected; attempt to spoof provenance via external data → force-reasserted advisory.

**No assertion weakening. No test-fixture masking of production defects.**

---

## 25. Test Inventory and Measured Baseline

**Measured baseline (reproduced 2026-08-26, `python -m pytest --collect-only -q`):**
- **Total collected: 1578**
- Passed: 1570 · Failed: 0 · Skipped: 3 · xfailed: 5 · exit 0
- 3 skips: `PLAYWRIGHT_E2E_TEST`, `HERMES_ACP_TEST`, `psutil` env gates (pre-existing).
- 5 xfails: D-03..D-06 C14 provenance gaps (genuine, non-blocking).
- Known flaky: `tests/performance/test_structured_logger_perf.py` correlation test (pre-existing, quarantine/retry).

**Projected M9 additions (Terminal 2 to measure, not assert):** new `tests/unit/test_m9_learning.py`, `tests/unit/test_m9_bootstrap.py`, `tests/integration/test_m9_closed_loop.py`, `tests/integration/test_m9_provenance_closure.py`, `tests/security/test_m9_authority.py`, `tests/integration/test_m9_manifest_hot_reload.py`. Count to be measured by Terminal 2; do not fabricate.

---

## 26. Regression Strategy

- Full suite must remain green: `python -m pytest` → 0 failed, 0 new collection errors.
- M7 regression: `tests/integration/test_m7_*` (83 passed per M8 Closure §8) must be untouched and green.
- M8 regression: DEF-01 32 tests, T1–T6 suites green; 5 xfails remain genuine.
- Quarantine the structured-logger flake; do not interpret it as M9 regression.
- `git status src/aios/` must show **no M7-named file modified** (freeze proof).
- `git diff` on `mcp_manager.py`, `acp_adapter.py`, M8 adapters must be empty except the narrow M9-N8 compatibility fixes.

---

## 27. M7 Freeze Requirements

M7 remains COMPLETE/FROZEN (M8 Closure §8). M9 MUST NOT modify:
- `core/testing_evidence.py` (semantics), `core/user_simulation_agent.py`
- `services/testing.py` agency orchestration internals (M9 may rely on its existing closed-loop hook but not alter it)
- `core/council_manager.py`, `core/final_judge_agency.py`, `core/ai_agency.py`, the 9 agency adapters
- `core/provenance.py` semantics (additive config only)
- Any `test_m7_*` test

Verification: `git status` + `git diff --stat` show no M7-path changes after M9.

---

## 28. M8 Freeze / Compatibility Requirements

M8 COMPLETE (Conditional GO) is a compatibility boundary. Frozen unless a genuine M9 requirement cannot be met otherwise (then document as a finding, §29):
- `core/mcp_manager.py` (DEF-01 fixed; do not revert)
- `adapters/acp_adapter.py`, `acp_session.py`, `hermes_bridge.py`
- `adapters/playwright_mcp_adapter.py`, `playwright_session.py`
- `adapters/graphify_adapter.py`
- `adapters/notion_mcp_adapter.py`, `obsidian_adapter.py`, `claude_mem_adapter.py`
- `core/capability_manager.py`, `capability_manifest.py`, `capability_provenance.py`, `adapter_factory.py` (M8-T5)
- `security_manager.py` authority unchanged (M8-T5 additive gate only)

M9-N8 (D-03..D-06) is the **only** permitted M8-adapter touching, and it is compatibility-only (advisory markers + correlation_id), not re-architecture.

---

## 29. Known Risks / Existing Defects

| ID | Risk | Class | Mitigation |
|----|------|-------|------------|
| R-1 | GAP-A: services never wired → closed loop silent | CRITICAL (pre-existing) | M9-N1 bootstrap + integration test proving loop fires in real kernel |
| R-2 | GAP-B: learnings captured but never reused | HIGH (pre-existing) | M9-N2/N3 retrieval + planner ingest + test |
| R-3 | RCA→Learning sync-into-async fragility (`root_cause.py:367-416`) | MEDIUM | M9-N4 event-driven handoff |
| R-4 | `print()` debug noise in `learning.py`/`root_cause.py` | LOW | M9-N4 replace with logger |
| R-5 | 5 C14 xfails (D-03..D-06) | Non-blocking limitation | M9-N8 closes where genuine |
| R-6 | Structured-logger flake | Non-blocking (quarantine) | retry, exclude from M9 regression |
| R-7 | Convergence/adaptive-replan scope creep | HIGH (process) | §3.5 quarantine; Terminal 3 checks |
| R-8 | M9 bootstrap could destabilize kernel start | MEDIUM | per-service try/except (kernel.py:1354 pattern); partial-start test |
| R-9 | psutil env gap (1 perf skip) | Environment | pre-existing, not M9 |
| R-10 | Tier C (real externals) unavailable | Environment | no Tier C claims; mock-only |

**Blocking findings for this plan:** NONE. M9 is READY FOR IMPLEMENTATION.

---

## 30. Terminal 2 Implementation Order

1. **M9-N1** (bootstrap) — wire services into kernel; unit + integration test that kernel `start()` registers & starts them. (Unblocks everything.)
2. **M9-N4** (RCA→Learning fix) — correct async handoff, remove `print()`. Prerequisite for reliable capture.
3. **M9-N2** (LearningService retrieval) — `get_learnings`/`query_relevant`. Unit tests.
4. **M9-N3** (PlanningService ingest) — consume learnings as advisory context. Integration test.
5. **M9-N5** (Graph remediation proposer) — advisory, Graphify-backed. Unit + advisory-bound test.
6. **M9-N8** (C14 provenance closure D-03..D-06) — convert xfails where genuine. Provenance + authority tests.
7. **M9-N6** (manifest hot-reload) — config flag + fail-closed reload. Unit + integration.
8. **M9-N7** (ACP session-TTL) — hardening only. Unit.
9. **M9-N10** (SelfPrompting real scoring) — replace mock scores; bounds intact. Unit + scoring test.
10. **M9-N9** (Convergence detection, bounded/advisory) — closed-loop signal → escalate. Unit + integration (bounded).
11. **M9-N11** (Human escalation wiring) — bounds-exhausted → `_escalate_to_human`. Integration test.
12. **Full regression** — `python -m pytest` green; M7/M8 gates intact.

Order rationale: GAP-A (1) first (structural blocker); capture correctness (2) before retrieval (3); retrieval before ingest (4); remediation (5) independent; provenance closure (6) + hardening (7,8) compatibility fixes; SelfPrompting scoring (9) + convergence (10) + escalation (11) complete the master-plan M9 component set; regression (12) last.

---

## 31. Terminal 3 Independent QA Strategy

Terminal 3 is the **final verification authority**; Terminal 2 MUST NOT declare M9 complete. Terminal 3 independently verifies:

- **Source implementation**: read `services/bootstrap.py` (M9-N1), `learning.py` (N2/N4), `planning.py` (N3), `remediation.py` (N5), `capability_manifest.py` (N6), `acp_session.py` (N7), adapter D-03..D-06 fixes (N8). Confirm no M7 file changed; confirm M8 adapters changed only per N8.
- **Production call paths**: reproduce GAP-A (real ServiceRegistry via bootstrap, not injected singletons — IND-6). Reproduce closed loop: FAIL→RCA→Learning→Planning→re-execute with real kernel instances.
- **Security boundaries**: adversarial tests inject `authoritative`/`trusted` via learning + manifest → assert rejected. Confirm Councils/Judge authority unchanged (diff vs M8).
- **Provenance**: D-04 correlation_id propagates orchestrator→adapter; D-03/05/06 advisory markers present; external spoof re-asserted advisory.
- **Authority**: learning/remediation output cannot set `authority=authoritative`.
- **Failure handling**: learning-capture failure non-blocking + logged; manifest reload fail-closed; bootstrap partial failure.
- **Regression**: full suite 0 failed; M7 (83) + M8 (DEF-01 32, T1–T6) intact; 5 xfails genuine (re-run `--runxfail` → 5 failed expected).
- **M7 freeze**: `git status src/aios/` shows no M7-named file modified.
- **M8 compatibility**: `git diff` on frozen M8 files empty except N8.
- **Acceptance (§32)**: all criteria met.

Terminal 3 issues the final GO/NO-GO.

---

## 32. Acceptance Criteria

M9 is COMPLETE when ALL are true:

1. **Bootstrap (GAP-A):** `HermesKernel.start()` instantiates & registers all engineering services into the canonical `ServiceRegistry`; `LearningService.on_start()` runs; `get_learning_service()` returns a live instance in a real kernel boot (proven by integration test, Tier B).
2. **Capture→retrieve→apply (GAP-B):** A failure in a real kernel flows RCA→LearningService (correct async, M9-N4); `LearningService.get_learnings()` returns captured learnings; `PlanningService.plan()` ingests relevant learnings as **advisory** context (proven by integration test).
3. **Closed loop fires:** `TestOrchestratorService._closed_loop_step` executes with real RCA/Learning/Planning singletons (no manual injection) in a kernel boot.
4. **Graph remediation (M9-N5):** `GraphRemediationProposer` returns advisory-only suggestions from Graphify; cannot set `authoritative`.
5. **ModelRouter available** to services needing LLM selection; FreeLLMAPI registered advisory (no live call required).
6. **Provenance closure (M9-N8):** D-03..D-06 closed where genuine; xfails converted only with real fixes; correlation_id propagates; advisory markers on all paths.
7. **Hot-reload (M9-N6):** manifest hot-reload re-registers via security gate, fail-closed.
8. **ACP TTL (M9-N7):** session TTL enforced; observation-only boundary intact.
9. **Convergence (M9-N9):** closed loop detects no-improvement/convergence and routes to escalation; bounded; advisory-only (no autonomous authority).
10. **SelfPrompting real scoring (M9-N10):** scores derived from real LLM-council/ModelRouter, not `hash()`; ADR #10 bounds enforced and observable.
11. **Human escalation (M9-N11):** learning/self-prompting/closed-loop bound exhaustion triggers `_escalate_to_human`.
12. **Authority intact:** Councils/Judge/SecurityManager/WorkflowManager authority unchanged (diff vs M8); M9 output is advisory-only (authority test passes).
10. **Regression green:** full suite 0 failed, 0 new collection errors; M7 (83) + M8 gates intact; 5 xfails genuine.
11. **M7 freeze:** no M7-named file modified.
12. **M8 compatibility:** frozen M8 files unchanged except N8.
13. **No Tier C claims; no scope creep into M10+ (convergence/adaptive-replan).**

---

## 33. P0/P1/P2/P3 No-Go Criteria

- **P0 (hard No-Go if violated):** M7 file modified; Councils/Judge authority altered; security gate bypassed; `authoritative`/`trusted` achievable via M9; assertion weakened to pass; production defect masked by fixture.
- **P1 (No-Go):** GAP-A not closed (services still unwired); closed loop still requires manual singleton injection; full suite has new failures; M8 DEF-01 32 tests broken.
- **P2 (No-Go if unresolved):** D-03..D-06 xfails silently removed without genuine fix; manifest hot-reload not fail-closed; secret leakage into learning store.
- **P3 (conditional):** structured-logger flake not quarantined; `print()` noise not removed; Tier C claimed; convergence/adaptive-replan implemented (M10+ creep).

---

## 34. Evidence Requirements (QA artifacts)

Terminal 2 must produce, for Terminal 3:
- `tests/integration/test_m9_closed_loop.py` — real-kernel closed loop (GAP-A + GAP-B proof).
- `tests/unit/test_m9_learning.py` — capture/retrieve/query.
- `tests/integration/test_m9_bootstrap.py` — bootstrap registration (Tier B).
- `tests/integration/test_m9_provenance_closure.py` — D-03..D-06 closure.
- `tests/security/test_m9_authority.py` — advisory/trust escalation rejected.
- `tests/integration/test_m9_manifest_hot_reload.py` — fail-closed reload.
- A reproduction log: `python -m pytest` → 0 failed; `--runxfail` → 5 xfailed expected.
- `git status` + `git diff --stat` proving M7 frozen + M8 compatibility.

---

## 35. Final Verification Gate

Terminal 3 runs the independent QA (§31) and issues **GO** only if §32 all true AND §33 P0/P1 clean. Until then, M9 is NOT complete. Terminal 2 is implementation-only and may not self-certify.

---

## 36. Explicit Implementation Handoff

**To Terminal 2 (implementation only):**
- Implement §30 order (M9-N1 → N8). Do NOT modify M7 internals or M8 files except M9-N8 compatibility fixes. Preserve all authority/trust boundaries (§16). No new EventTypes. No Tier C. No M10+ scope (§3.5). Run full regression; produce §34 artifacts. You MAY NOT declare M9 complete.

**To Terminal 3 (independent QA / final authority):**
- Verify §31 independently. Reproduce GAP-A/B with real registry (IND-6: no injected singletons). Check M7 freeze + M8 compatibility via git. Adversarial authority/provenance tests. Issue GO/NO-GO per §32/§33.

**Explicit statement:** No production implementation was performed during this Terminal 1 planning task. Only inspection, this specification, and a memory record were produced.

---

*End of M9 Implementation Specification. Authority: M8 Closure Audit §13 (milestone scope) + repository source verification (2026-08-26). Contradiction in "M9" naming (milestone vs component slot) documented at §3.2; milestone definition is authoritative.*
