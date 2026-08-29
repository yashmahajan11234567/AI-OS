# M8-T6 — Production Integration Testing

**Authoritative Planning Specification (Terminal 1 — Architecture / Planning / Inspection)**

- **Status:** PLANNING ONLY — no source or test modification in this task.
- **Depends on:** M7 (FROZEN), M8-T1 (VERIFIED GO), M8-T2 (VERIFIED GO), M8-T3 (VERIFIED GO), M8-T4 (VERIFIED GO), M8-T5 (VERIFIED GO).
- **Objective:** Cross-integration validation of the production AI-OS system — prove the integrated workflow coordinates all external capabilities together while preserving authority boundaries, provenance, evidence integrity, security, isolation, failure handling, recovery, and backward compatibility.
- **Verdict:** `M8-T6 PLANNING VERDICT: READY FOR IMPLEMENTATION` (with mandatory regression-reporting of the defects enumerated in §3, §9, §17, and §29).

---

## 1. Executive Summary

M8-T6 is the capstone integration milestone. M8-T1 through M8-T5 each added one external integration (Hermes ACP/MCP, Playwright, Graphify, Notion/Obsidian/Claude-Mem, and the capability-registry hardening layer). Each was tested in isolation against an in-process mock server. **No test in the repository exercises two or more of these integrations coordinating a single production-style workflow under one kernel.** M8-T6 closes that gap.

The plan specifies:

1. A **cross-adapter execution matrix** (Hermes × Playwright, × Graphify, × knowledge systems; Playwright × Graphify; etc.).
2. **End-to-end production-style workflows** following the core target flow (Council → capability selection → external execution/context → evidence → testing → review → verification → final authority inside AI-OS).
3. **Failure-injection**, **security-integration**, **degraded-mode**, **recovery**, **concurrency**, and **session-isolation** suites.
4. A **new marker scheme** (`integration`, `e2e`, `gated`, `security`, `slow`, `external`, `real`) and a **shared integration `conftest.py`** that promotes the currently-duplicated `MockMCPManager` and singleton-reset harness.
5. A strict **mock vs production vs real-external test boundary** so a passing mock is never mistaken for a passing production integration.

### 1.1 Planning-mode caveat (read before implementation)

This task is inspection-only. During inspection, **four concrete architectural defects were discovered** that M8-T6 must surface as regression/finding reports. They are NOT to be fixed in M8-T6 planning or implementation without Terminal-3 awareness — they are reported as findings. The most severe:

- **D-01 (CRITICAL):** `kernel._mcp_manager` is never assigned. Every MCP-bound adapter (`GraphifyAdapter`, `NotionAdapter`, `ObsidianAdapter`, `ClaudeMemAdapter`) receives `mcp_manager=None` at boot and can therefore never connect to its server. The production integration chain is a **disconnected skeleton** (see §3, §16, §29).
- **D-02 (CRITICAL/blocker for one perspective):** `UserSimulationAgent.simulate()` (`src/aios/core/user_simulation_agent.py:151`) calls `self._bridge._create_session_id()`, which does not exist on `HermesBridge`. This raises `AttributeError` in production, crashing the `user_simulation` (10th) testing perspective (see §3, §9).
- **D-03 (HIGH):** Graphify write paths (`store_node`, `update_node`, `delete_node`) return `raw=result` **without** `_mark_advisory`, so those results carry no C14 advisory/authority/trust markers (see §3, §9).
- **D-04 (MEDIUM):** `correlation_id` / `execution_id` / `task_id` are regenerated per adapter call and are **never propagated** from the orchestrator into the capability adapters; there is no end-to-end traceability through adapter provenance (see §9).

These are documented in §17 (Architectural Boundaries / Gaps) and §29 (Known Limitations) with exact file:line references.

---

## 2. Current Repository State

- **Baseline test count (measured, not invented):** `1418` tests collected at `pytest 8.4.2` via `python -m pytest --collect-only -q` on a clean working tree.
  - `tests/unit`: **1185**
  - `tests/integration`: **230**
  - `tests/performance`: **4**
  - (Note: the collection emits `PytestCollectionWarning` for `TestingEvidence` / `TestOrchestratorService` dataclasses with `__init__`; these are not test classes — expected, harmless.)
- **Authoritative cumulative total (per independent QA, most reliable):** `1416 passed / 2 skipped` after M8-T5.
- **pytest config:** `pyproject.toml` `[tool.pytest.ini_options]` = `{ asyncio_mode = "auto", testpaths = ["tests/unit","tests/integration","tests/performance"] }`. **No `[tool.pytest.ini_options] markers` are registered.**
- **Markers in use:** only `pytest.mark.asyncio` (auto-applied by a collection hook in `tests/unit/conftest.py`). No `integration`/`e2e`/`gated`/`security`/`external` markers exist. Real-external tests are gated ad-hoc via `pytest.skip(...)` inside the body using env vars (`HERMES_ACP_TEST=1`, `PLAYWRIGHT_E2E_TEST=1`, `GRAPHIFY_E2E_TEST=1`).
- **Conftests:** exactly one — `tests/unit/conftest.py` (EventBus singleton reset + asyncio auto-mark hook). **No shared root or integration conftest.**
- **M7 status:** FROZEN. 13/13 M7 regression suites must remain green.
- **M8-T1..T5 status:** all VERIFIED GO by independent Terminal-3 QA; no P0/P1 open.

### 2.1 Baseline reconciliation warning

The per-task "new test" prose counts for T1 (31) and T2 (33) do **not** reconcile with cumulative deltas; only T3→T4 (+113) and T4→T5 (+101) reconcile exactly. **Terminal 2 MUST re-run `pytest` on a clean checkout before and after M8-T6 and record the true before/after numbers.** Do not trust prose counts.

---

## 3. M8-T1 through M8-T5 Integration Inventory

| Task | Integration | Adapter(s) | Capability id (facade) | C14 marking | QA |
|---|---|---|---|---|---|
| T1 | Hermes ACP (preferred) + MCP (fallback) | `HermesBridge`, `AcPAdapter`, `AcPSession` | — (kernel property) | `trust_level="untrusted"` forced; `protocol∈{acp,mcp,acp_fallback}` | GO |
| T2 | Playwright MCP browser | `PlaywrightMCPAdapter`, `PlaywrightSessionRegistry` | `playwright_browser` (browser) | **No `_mark_advisory`; no provenance dict at all** | GO |
| T3 | Graphify relationship/knowledge graph | `GraphifyAdapter` | `graphify_context` (graph) | `authority="advisory_only"`, `source="graphify_inferred"`; **write paths skip marking** | GO |
| T4 | Notion / Obsidian / Claude-Mem | `NotionAdapter`, `ObsidianAdapter`, `ClaudeMemAdapter` | `notion_planning` (planning), `obsidian_knowledge` (knowledge), `claude_mem_context` (memory) | `authority="contextual"`; Obsidian=`trusted_contextual`; Notion/Claude-Mem=`untrusted`; `_mark_advisory` re-asserts C14 constants last | GO |
| T5 | Capability / external integration hardening | `CapabilityManager`, `CapabilityManifestLoader`, `AdapterFactory`, `capability_provenance` | manifest-driven (`config/capabilities/*.yaml`) | `mark_capability_advisory()` re-asserts C14; manifest rejects builtin/trusted/authoritative | GO |

### 3.1 Per-task integration points relevant to M8-T6

- **T1:** ACP-primary / MCP-fallback lives entirely inside `HermesBridge` (`fallback_to_mcp=True` default). On ACP `ProtocolUnavailableError` it falls back to MCP and records `provenance.protocol="acp_fallback"`. Honest fallback must be distinguishable from a true MCP session (`"mcp"`). `UserSimulationAgent` is wired to a real `HermesBridge`.
- **T2:** `PlaywrightMCPAdapter` produces `ExecutionResult` observations only (screenshot/snapshot/page_state); it has **no `_mark_advisory` and no advisory/authority/trust provenance field**. This is a gap to assert (§9, D-05-adjacent).
- **T3:** `ArchitectureAgencyAdapter` is the **only** adapter that consumes another adapter — it routes to `GraphifyAdapter` when connected, else its text-scanner fallback (`graphify_mcp_text_fallback`). No other adapter invokes another.
- **T4:** C14 override-resistant advisory — `NotionAdapter/ObsidianAdapter/ClaudeMemAdapter._mark_advisory` seed a base, merge caller data into optional fields, then **re-apply C14 constants last** so externally-supplied `authority`/`advisory`/`trust_level` cannot flip AI-OS markings (verified by T4 QA). Obsidian has a dual MCP→filesystem fallback (`_read_local`/`_search_local`/`_list_local`) with `retrieval_path` recorded.
- **T5:** `AdapterFactory` is an explicit allowlist (rejects arbitrary importlib paths + path traversal). Manifests are loaded from `config/capabilities/*.yaml`; the kernel registers the same five capabilities **twice** (manually in `_init_*` then via manifest), with the manifest's higher precedence (`trusted_contextual` > `untrusted`) replacing the manual entry and attaching `adapter_binding`.

### 3.2 Defects discovered during inspection (must be reported, not fixed in planning)

| ID | Severity | Location | Description |
|---|---|---|---|
| **D-01** | CRITICAL | `src/aios/core/kernel.py` (read at 873/969/1023/1065/1104/1157/1205; never assigned) | `self._mcp_manager` is never set. All MCP-bound adapters receive `None` → `connect()` returns `False` → cannot reach any MCP server at boot. |
| **D-02** | CRITICAL | `src/aios/core/user_simulation_agent.py:151` | Calls `_bridge._create_session_id()` — method does not exist on `HermesBridge` (has `create_worker_session`/`_create_acp_session`/`_create_mcp_session`). `AttributeError` in production → `user_simulation` perspective crashes. |
| **D-03** | HIGH | `src/aios/adapters/graphify_adapter.py:471,547,576` | `store_node`/`update_node`/`delete_node` return `raw=result` without `_mark_advisory` → no C14 advisory markers. |
| **D-04** | MEDIUM | `src/aios/adapters/{notion,obsidian,claude_mem,graphify}_adapter.py` `_make_provenance` | `correlation_id`/`execution_id`/`task_id` generated per call via `uuid.uuid4()`; orchestrator correlation_id never injected downstream. |
| **D-05** | MEDIUM | `src/aios/adapters/playwright_mcp_adapter.py` | No `_mark_advisory` / no advisory provenance dict on Playwright results. |
| **D-06** | MEDIUM | `src/aios/adapters/obsidian_adapter.py` (`list_notes`/`_list_local`) | Filesystem fallback `list_notes` results may not pass through `_mark_advisory`. |
| **D-07** | LOW | `src/aios/core/capability_provenance.py:263` | `assert_capability_provenance()` (the only spoof-verifier) is **never called** anywhere — no runtime validation that C14 marking survived. |
| **D-08** | LOW | `src/aios/adapters/hermes_bridge.py:224-264` | `HermesObservation.provenance` lacks `advisory`/`authority` flags (only `trust_level="untrusted"`). An `assert_capability_provenance`-style check would fail for Hermes/User-Sim. |
| **D-09** | LOW | `tests/integration/test_structured_logger_phase.py::test_correlation_propagation_end_to_end` | Pre-existing flaky test (order-dependent sink/context interference), cross-task, unrelated to M8; quarantine or fix in logging subsystem before relying on full-suite stability. |

---

## 4. Production Call-Path Map

> All paths traced by direct source inspection (kernel.py wiring + adapter constructors). "Production" means the path the kernel wires at boot.

| Integration | Adapter class | Kernel construct site | `mcp_manager` at boot | Execution entry | Transport (production) |
|---|---|---|---|---|---|
| Hermes | `HermesBridge` | `kernel.py:872` | `None` → uses global `get_mcp_manager()` | `create_worker_session` / `execute_task` (+ `navigate`/`click`/`type_text`/`screenshot`/`extract_content`) | ACP direct subprocess (fallback→MCP); `cwd` unset ⇒ **always MCP** |
| Playwright | `PlaywrightMCPAdapter` | `kernel.py:1063` | `None` | `create_session` / `execute_action` / `collect_evidence` | Direct stdio `@playwright/mcp` (bypasses MCPManager) |
| Graphify | `GraphifyAdapter` | `kernel.py:1022` | **`None` — cannot connect** | `execute(target, ctx)` → action methods | MCPManager `server_id="graphify"` |
| Notion | `NotionAdapter` | `kernel.py:1103` | **`None` — cannot connect** | `execute(target, ctx)` → action methods | MCPManager `server_id="notion"` |
| Obsidian | `ObsidianAdapter` | `kernel.py:1156` | `None` but has filesystem fallback | `execute(target, ctx)` → action methods | MCP `server_id="obsidian"` → **filesystem fallback** |
| Claude-Mem | `ClaudeMemAdapter` | `kernel.py:1204` | **`None` — cannot connect** | `execute(target, ctx)` → action methods | MCPManager `server_id="claude_mem"` |
| Dynamic caps | `CapabilityManager`+`AdapterFactory` | `kernel.py:924` | factory `mcp_manager=None` | `register_capability`/`initialize_capability`/`resolve`/`invoke` | adapter built per manifest; `mcp_manager=None` |

### 4.1 Kernel init order (from `kernel.start()`)

```
_init_lifecycle_manager()      (kernel.py:419)
_init_m7_testing()             (kernel.py:424)  → HermesBridge + UserSimulationAgent + TestOrchestratorService
_init_graphify()               (kernel.py:427)  → GraphifyAdapter + graphify_context capability
_init_playwright()             (kernel.py:430)  → PlaywrightMCPAdapter + playwright_browser capability
_init_notion()                 (kernel.py:433)  → NotionAdapter + notion_planning capability
_init_obsidian()               (kernel.py:434)  → ObsidianAdapter + obsidian_knowledge capability
_init_claude_mem()             (kernel.py:435)  → ClaudeMemAdapter + claude_mem_context capability
_init_capability_manifests()   (kernel.py:438)  → dynamic manifest load (re-registers the 5 caps)
_start_services()              (kernel.py:441, if auto_start_services)
```

### 4.2 Shared `MCPManager` lifecycle

- Global singleton `get_mcp_manager()` (`mcp_manager.py:920`). `__init__(config_dir=./config/mcp)` auto-loads every `*.json` into `MCPServerConfig` (known but **disconnected**).
- `connect(server_id)` gate-before-connect via `SecurityManager.validate_mcp_server_before_connect`, then transport launch (`_connect_stdio/http/sse/websocket`) + MCP `initialize` + `tools/list`.
- `call_tool(server_id, tool_name, args)` dispatches by transport; raises if not connected.
- **`connect_all()` is never called by the kernel** (`_start_services` only starts resource + engineering services; `MCPService` is not registered). So even the global `MCPManager`'s servers stay disconnected at boot; Hermes connects lazily on first `create_worker_session`.
- Adapters sharing it: Graphify, Notion, Obsidian, Claude-Mem (via `self._mcp_manager.call_tool`) + Hermes MCP-fallback. Playwright and ACP-primary do **not** (direct subprocess).

### 4.3 Mock-only paths that exist in tests but NOT in production

- `config/mcp/*_mcp.json` `command` fields point at `aios.adapters.mock_*_server` — **test doubles**, not real servers.
- `HERMES_MOCK_PLAYWRIGHT=1` branch in `PlaywrightMCPAdapter._find_playwright_command` (test-only selector).
- Adapter `tool=` injection / `BaseExecutionAdapter._default_tool` sync path — test-only.
- `AdapterFactory` allowlist is real production code but only invoked from the dynamic manifest path; the kernel's manual `_init_*` wiring **bypasses the factory** and constructs adapters directly.

---

## 5. Cross-Integration Architecture

```
                       ┌─────────────────────────────────────────┐
                       │            AI-OS (authoritative)          │
                       │  CouncilManager · FinalJudgeAgency ·     │
                       │  SecurityManager · SimplificationGate    │
                       └───────────────┬─────────────────────────┘
                                       │ capability selection / registry
                  ┌────────────────────┴───────────────────────────┐
                  │            CapabilityManager (T5)               │
                  │  manifest → validate → register → policy →      │
                  │  available → execute → result (C14 advisory)    │
                  └────────────────────┬───────────────────────────┘
        ┌──────────────────────────────┼───────────────────────────────────┐
        │            MCPManager (shared, stdio)            │  direct subprocess │
        ├──────────┬──────────┬──────────┬──────────┬──────┼────────┬──────────┤
      Graphify   Notion   Obsidian   Claude-Mem  Hermes(MCP)  Hermes(ACP)  Playwright
        │          │         │           │            │           │           │
   [mock/proto] [mock] [mock/fs]  [mock]      [mock/proto]  [proto]   [@playwright]
        └──────────┴──────────┴──────────┴────────────┴───────────┴───────────┘
                  ▲  all results flow back as advisory / ExecutionResult
                  │  (never authoritative, never a verdict)
                  └──────────────► evidence → testing → review → verification → AI-OS
```

**Key architectural facts for M8-T6:**

- All six adapters are `BaseExecutionAdapter` subclasses, wired into the **same** kernel, sharing the **same** `MCPManager` (where applicable).
- The **only** adapter-to-adapter relationship is `ArchitectureAgencyAdapter → GraphifyAdapter` (T3), with a text-scanner fallback. M8-T6 must test that Graphify-unavailable degrades gracefully to the fallback and that the fallback result is correctly *not* marked `graphify_inferred`.
- Every integration self-registers a capability at boot; T5's manifest loader now wraps every T1–T4 integration uniformly with `trust_level` / `authority_classification` / `allowed_operations` / `security_context`.
- The **orchestrator-level `correlation_id`** is the only ID threaded through the whole run (`testing.py:226` → `_dispatch_all` → `dispatch_perspective`). It is **never injected into the capability adapters** (D-04).

---

## 6. Integration Matrix (cross-adapter execution)

Combinations to exercise. "Meaningful" = the two integrations are used together in the core target flow.

| # | Pair | Meaningful | Test type | Notes |
|---|---|---|---|---|
| 1 | Hermes + Playwright | ✅ | E2E | Worker drives a browser session; evidence from both |
| 2 | Hermes + Graphify | ✅ | E2E/Integration | Worker actions enriched into graph context |
| 3 | Hermes + knowledge (Notion/Obsidian/Claude-Mem) | ✅ | E2E/Integration | Worker retrieves planning/knowledge context |
| 4 | Playwright + Graphify | ✅ | Integration | Browser actions logged as graph relationships |
| 5 | Playwright + knowledge | ✅ | Integration | Browser evidence cross-referenced with knowledge |
| 6 | Graphify + knowledge | ✅ | Integration | Graph relationships enriched from Notion/Obsidian/Claude-Mem |
| 7 | Hermes + Playwright + Graphify | ✅ | E2E | Full execution+context chain |
| 8 | All external (Hermes, Playwright, Graphify, Notion, Obsidian, Claude-Mem) | ✅ | E2E | The core target flow |
| 9 | Any pair under ACP-unavailable→MCP-fallback | ✅ | Failure-injection | Fallback provenance correctness |
| 10 | Three+ integrations, one forced-fail | ✅ | Degraded-mode | Graceful partial degradation |

---

## 7. End-to-End Scenarios

Each E2E scenario drives the **core target flow**: Council / planning authority → capability selection/registry → external execution/context layer → evidence/observations/context → testing → review → verification → final authority inside AI-OS.

### 7.1 E2E-1: Full production-style workflow (golden path)
1. Boot kernel with **all capabilities available** (inject a real/connected `MCPManager` to overcome D-01 for the happy path; see §16).
2. Council selects capabilities → CapabilityManager resolves `graphify_context`, `playwright_browser`, `notion_planning`, `obsidian_knowledge`, `claude_mem_context`.
3. `TestOrchestratorService.orchestrate_test(...)` runs the 9 agencies + user_simulation.
4. External layer executes: Hermes worker (browser), Playwright actions, Graphify context enrichment, Notion/Obsidian/Claude-Mem context retrieval.
5. Evidence collected with complete provenance; testing council + final judge decide.
6. **Assert:** final authority = AI-OS (Council/Judge); every external result marked advisory; `execution_id`/`correlation_id` consistent where the code allows; no external system issued a verdict.

### 7.2 E2E-2: Architecture agency consumes Graphify (real path)
Drive `ArchitectureAgencyAdapter` with Graphify **connected** → assert `graphify_inferred` enrichment + advisory marking + namespace `ai_os:` prefix. Then disconnect Graphify → assert text-scanner fallback fires and result is **not** `graphify_inferred`.

### 7.3 E2E-3: Hermes fallback path
Force ACP unavailable (`cwd=None` + mock ACP unavailable) → assert `protocol="acp_fallback"` and a **distinct** provenance from a true `"mcp"` session.

### 7.4 E2E-4: Knowledge-augmented testing
`notion_planning` + `obsidian_knowledge` + `claude_mem_context` retrieved as advisory context, then fed into a perspective's context; assert context is marked advisory/contextual and cannot alter the verdict.

### 7.5 E2E-5: Multi-integration evidence correlation
Run a workflow touching Hermes + Playwright + Graphify + knowledge; assert evidence set carries ≥1 record per integration, each with correct `source`/`advisory`/`authority`/`trust_level`, and orchestrator `correlation_id` present on each `TestingEvidence.provenance`.

---

## 8. Failure Matrix

Inject each failure and assert the system degrades gracefully, never silently converting failure→success.

| # | Failure | Inject via | Expected behavior |
|---|---|---|---|
| F-1 | Hermes unavailable | mock hermes returns connection error / `ProtocolUnavailableError` | user_simulation evidence = fail; run continues; no crash |
| F-2 | ACP unavailable | `cwd=None` + ACP adapter raises | MCP fallback; `protocol="acp_fallback"` |
| F-3 | MCP unavailable | disconnect graphify/notion/obsidian/claude_mem server | `ERROR` ExecutionResult; capability `availability=error`; kernel does not crash |
| F-4 | Playwright unavailable | mock playwright returns infra error | Playwright evidence = fail / skipped; accessibility falls back |
| F-5 | Browser action failure | mock playwright returns action error | observation records failure; not masked as success |
| F-6 | Graphify unavailable | disconnect graphify | ArchitectureAgency → text-scanner fallback |
| F-7 | Notion unavailable | disconnect notion | `ERROR` result; planning context absent; run continues |
| F-8 | Obsidian unavailable | disconnect obsidian MCP | filesystem fallback (if vault_path) else `ERROR` |
| F-9 | Claude-Mem unavailable | disconnect claude_mem | `ERROR` result; memory context absent; run continues |
| F-10 | Capability unavailable | manifest missing/disabled | CapabilityManager reports unavailable; no execution |
| F-11 | Malformed external response | mock returns malformed JSON | `Malformed*ResponseError` / `ERROR`; not parsed as success |
| F-12 | Timeout | mock `asyncio.sleep` > timeout | `TimeoutError` → typed error result |
| F-13 | Partial execution | one of N operations fails | partial `ERROR`; rest succeed; result not over-claimed |
| F-14 | Recovery after failure | F-x then re-run | stale session/evidence does not contaminate new run |
| F-15 | Repeated failure | F-x repeated N times | bounded; no infinite loop; consistent error |
| F-16 | Mixed success/failure | some integrations fail, some pass | each result reflects its own status; aggregate verdict unbiased |

---

## 9. Evidence / Provenance Validation

**Two provenance schemas exist and M8-T6 must understand both:**

- **`Provenance`** (`testing_evidence.py:74`) — testing evidence chain: `source, worker, session, timestamp, environment, correlation_id, test_id`. Carries **no** `execution_id`/`task_id`/`protocol`/`adapter`/`trust_level`/`advisory`. Authority is implicit (produced by trusted orchestrator).
- **`CapabilityProvenance`** (`capability_provenance.py:21`) — capability result: `source, adapter, operation, correlation_id, execution_id, task_id, timestamp, request_id, version, authority, advisory, trust_level` (+ optional `capability_id/facade/provider_id`). The advisory/`trust_level`/`authority` fields ARE the authority markers.

### 9.1 Assertions

- **P-1** Provenance survives across adapter boundaries for `source`/`adapter`/`operation`/`authority`/`advisory`/`trust_level`.
- **P-2** `execution_id` remains consistent within a single adapter operation across retries.
- **P-3** `correlation_id` remains consistent where the code path preserves it (orchestrator-level; see D-04 for the gap — assert current behavior and flag).
- **P-4** `task_id`/`session_id` correctly associated (Hermes `session_id` matches `provenance.session_id`).
- **P-5** Protocol/adapter provenance accurate (`acp`/`mcp`/`acp_fallback`/`mcp_manager`/`graphify_adapter`/…).
- **P-6** Evidence cannot be silently replaced/fabricated — `TestingEvidence` is `@dataclass(frozen=True)`; assert immutability + serialization round-trip.
- **P-7** External data remains marked advisory/contextual/untrusted:
  - Notion: `authority="contextual"`, `advisory=True`, `trust_level="untrusted"`.
  - Obsidian: `authority="contextual"`, `trust_level="trusted_contextual"`.
  - Claude-Mem: `authority="contextual"`, `trust_level="untrusted"`.
  - Graphify: `authority="advisory_only"`, `source="graphify_inferred"`.
  - Hermes: `trust_level="untrusted"` (forced).
- **P-8** Graphify **never** authoritative; Hermes **never**; Playwright **never**; Notion/Obsidian/Claude-Mem **never**.
- **P-9** Regression assertions for D-03/D-05/D-06: Graphify write paths and Obsidian `list_notes` fallback must be marked advisory (these **currently fail** — report as findings, do not silently "fix").

### 9.2 Silent-loss gaps (assert current behavior, flag as defects)

- **D-04:** `correlation_id` not propagated into capability adapters — assert the gap and recommend injection.
- **D-08:** Hermes/User-Sim provenance lacks `advisory`/`authority` — flag.
- **normalize_evidence** (`testing.py:448`) collapses adapter provenance into `observations`/`raw`; assert a Graphify-sourced architecture finding retains `graphify_inferred`/`untrusted` **somewhere auditable**, not collapsed to `"architecture_agency"`.

---

## 10. Authority-Boundary Validation

Assert external integrations **cannot**:

- **A-1** PASS/FAIL a test (verdict authority reserved to CouncilManager + FinalJudgeAgency).
- **A-2** approve/reject (no `approve`/`reject` language emitted by any adapter).
- **A-3** override Council/Judge (builder-origin evidence dropped at `testing.py:645`; external worker observations only).
- **A-4** modify authoritative AI-OS state improperly (no adapter imports SecurityManager/StateManager/WorkflowManager/Council/Judge — add a cross-cutting import-seam test).
- **A-5** inject authority through provenance (C14 re-assertion last wins; attempt to inject `authority="authoritative"` → overwritten).
- **A-6** spoof trust level (attempt `trust_level="builtin"` → overwritten to untrusted/contextual).
- **A-7** alter security/policy decisions (`SecurityManager.authorize` fail-closed: principal None/"" → DENY; `validate_capability_spec` rejects builtin/trusted/authoritative).
- **A-8** escalate via capability shadowing (`CM-SHADOW-001`, `CM-PREC-001` collision rules).

**A-4 cross-cutting test (new, recommended):** a single module-level test that greps/imports each M8 adapter and asserts it does not import `security_manager`, `state`, `workflow`, `council_manager`, `testing` (decision-authority modules). This closes the "authority guarantee is code-enforced, not runtime-verified cross-suite" gap noted in T1–T5 QA.

---

## 11. Capability-Registry Validation

Exercise the T5 flow with dynamically loaded capabilities alongside the existing adapters — **without kernel-specific branching**:

```
DISCOVERY (load config/capabilities/*.yaml)
   ↓
VALIDATION (SecurityManager.validate_capability_spec gate)
   ↓
REGISTRY (CapabilityRegistryEntry; collision resolution)
   ↓
POLICY (enforce_security_context: allowed_operations / sensitive_keys / max_content_size)
   ↓
AVAILABLE (initialize_capability for enabled caps)
   ↓
EXECUTION (AdapterFactory.get_adapter → adapter.execute)
   ↓
RESULT (C14 advisory re-asserted)
```

Assertions:
- **C-1** All 5 manifest capabilities load and register on a booted kernel (chdir to temp `./config/capabilities`).
- **C-2** A malformed manifest → skipped (loader skip-not-raise), boot continues.
- **C-3** Path traversal in adapter class_path → `CM-ADAPTER-001` rejected.
- **C-4** Non-allowlisted adapter → rejected.
- **C-5** Capability claiming `trust_level=builtin` / `authority_classification=authoritative` → rejected.
- **C-6** Lower-trust shadow of a trusted registration → `CM-SHADOW-001` blocked.
- **C-7** Sensitive-key payload → `CM-SEC-002` denied (fail-closed).
- **C-8** Dynamically loaded capability executes together with the kernel-built adapters through the same registry (no special-casing).
- **C-9** Double-registration collision (manual `_init_*` + manifest) resolves by precedence and attaches `adapter_binding` without corruption.

---

## 12. Session-Isolation Validation

Simultaneous/sequential sessions across Hermes, Playwright, Graphify, external knowledge.

- **S-1** Two concurrent Hermes worker sessions → no shared state; `session_id` distinct; `provenance.session_id` matches.
- **S-2** Concurrent Playwright sessions (ephemeral contexts) → no cross-context leakage.
- **S-3** Concurrent Graphify operations → namespace `ai_os:` isolation; entity IDs from session A not visible/overwritten in session B.
- **S-4** Concurrent Notion/Obsidian/Claude-Mem retrieval → no credential/session contamination.
- **S-5** Cross-task evidence leakage → each `TestingEvidence.provenance.session`/`correlation_id` independent.
- **S-6** Correct cleanup → `disconnect()`/`close_worker_session()` clears `_connected`/`_active_sessions`.
- **S-7** Recovery after interrupted execution → interrupted session's partial state does not leak into a subsequent session.

---

## 13. Security Integration Tests

- **SEC-1** Secret scrubbing — adapter `_validate_content`/`_validate_properties` reject `SENSITIVE_PROPERTY_KEYS`; `SECRET_VALUE_PATTERNS` (API key/Bearer/password) detected and raised.
- **SEC-2** Parameter hashing — `HermesBridge._hash_parameters` / `PlaywrightMCPAdapter._hash_parameters` SHA-256 (no secrets in provenance).
- **SEC-3** Sensitive-key rejection at capability layer — `CM-SEC-002` fail-closed nested scan.
- **SEC-4** URL/DOM redaction — `PlaywrightMCPAdapter._redact_url` (token/key/secret/…) + `_redact_dom`.
- **SEC-5** Filesystem boundary enforcement — `ObsidianAdapter._validate_path` blocks traversal (`is_relative_to`) and `.obsidian` dir.
- **SEC-6** Graphify namespace isolation — all entity IDs prefixed `ai_os:`.
- **SEC-7** Capability security context — `allowed_operations` enforced; unauthorized op denied.
- **SEC-8** Provenance spoof resistance — inject `authority="authoritative"`/`trust_level="builtin"` → overwritten.
- **SEC-9** Malicious/malformed external responses — fuzzed JSON → `ERROR`/typed error, no crash.
- **SEC-10** Prompt/injection-like external content — Notion/Obsidian/Claude-Mem body containing "ignore previous instructions" → treated as data, never executed.
- **SEC-11** Oversized payloads — `MAX_CONTENT_SIZE` (10KB) / `MAX_PROPERTY_VALUE_SIZE` rejected.
- **SEC-12** Unauthorized operations — capability invoked outside `allowed_operations` → denied.

---

## 14. Degraded-Mode Tests

Determine exactly what AI-OS does when dependencies fail; assert graceful degradation never silently converts failure→success.

- **DG-1** One dependency fails (e.g., Graphify) → rest succeed; run completes; failing perspective = fail/ERROR.
- **DG-2** Multiple dependencies fail → run continues; aggregate reflects partial state.
- **DG-3** Only contextual systems fail (Notion/Obsidian/Claude-Mem) → execution systems still run; context absent; no crash.
- **DG-4** Only execution systems fail (Hermes/Playwright/Graphify) → context retrievable; execution evidence = fail; verdict reflects.
- **DG-5** Capability registry has unavailable capabilities → resolve reports unavailable; no execution attempted.
- **DG-6** MCP fully disconnected (D-01 realistic state) → assert adapters report unavailable/ERROR rather than hanging or fabricating success.

---

## 15. Recovery Tests

```
failure → cleanup → retry/recovery → new execution → evidence → verification
```

- **RC-1** After F-3 (MCP down) then reconnect → new execution succeeds; stale `ERROR` evidence not reused.
- **RC-2** After F-6 (Graphify down) then reconnect → ArchitectureAgency uses Graphify again, not stale fallback.
- **RC-3** Stale sessions cleaned (S-6) before retry — no ghost sessions.
- **RC-4** Stale evidence excluded from the new run's council (fresh `correlation_id`).
- **RC-5** Stale capability state (`availability=error`) recovered to `AVAILABLE` after reconnect.

---

## 16. Production-Path Verification

Identify the **actual** production call paths (from §4) and remaining mock-only/unverified assumptions:

| Integration | Production path | Currently mock-only? | Unverified assumption |
|---|---|---|---|
| Hermes | `HermesBridge` MCP path (global `get_mcp_manager`) | Yes (mock server) | Real ACP subprocess (`cwd` unset ⇒ always MCP in prod) |
| Playwright | Direct stdio `@playwright/mcp` | Yes (`HERMES_MOCK_PLAYWRIGHT`) | Real browser requires Node + `@playwright/mcp` |
| Graphify | MCPManager `server_id="graphify"` | Yes (`config/mcp/graphify_mcp.json` → `mock_graphify_server`) | **D-01**: never connects at boot |
| Notion | MCPManager `server_id="notion"` | Yes | **D-01** |
| Obsidian | MCP→filesystem fallback | Yes (mock + temp vault) | **D-01**; filesystem works without MCP |
| Claude-Mem | MCPManager `server_id="claude_mem"` | Yes | **D-01** |
| Dynamic caps | `AdapterFactory` → `register_capability` | No (real kernel boot) | Real server connect still gated by D-01 |

### 16.1 M8-T6 production-injection harness (to overcome D-01 for real-path tests)

Terminal 2 MUST construct a `RealMCPManagerHarness` that:
1. Instantiates the real `MCPManager(config_dir=tmp/config/mcp)`.
2. Re-points `config/mcp/*.json` `command` fields to the in-repo `mock_*_server.py` **entry points** (so the "production" stdio transport launches a controllable mock — a production-style subprocess, not an in-process double).
3. Calls `connect_all()` (or per-server `connect`) before exercising adapters.
4. Injects the connected manager into the kernel's adapters (since the kernel won't do it — D-01).

This distinguishes **mock/in-process** (current T1–T5) from **production-style subprocess** (M8-T6 new) while staying hermetic (no external network).

---

## 17. Architectural Boundaries (Do-Not-Implement & Gaps)

### 17.1 M9 functionality explicitly excluded (do NOT implement in M8-T6)
- No `LearningService` convergence/pattern learning beyond what already exists.
- No RCA pipeline expansion (reuse existing `RootCauseAnalyzer` only).
- No model router (reuse `ModelRouter` singleton; no new selection logic).
- No convergence detection.
- No adaptive replanning.

### 17.2 Discovered architectural gaps (report as findings, do NOT fix in M8-T6 planning/implementation without Terminal-3 coordination)

- **G-1 (D-01):** `kernel._mcp_manager` never assigned → production chain disconnected. **Highest-priority finding.** Reported to Terminal 3; blocks true real-path integration until resolved (or worked around via the §16.1 harness).
- **G-2 (D-02):** `UserSimulationAgent.simulate()` crashes in production (`_create_session_id` missing). Blocks the `user_simulation` perspective end-to-end.
- **G-3 (D-03):** Graphify write paths unmarked.
- **G-4 (D-04):** No cross-adapter correlation_id/execution_id propagation.
- **G-5 (D-05):** Playwright results carry no advisory provenance.
- **G-6 (D-07):** `assert_capability_provenance` dead code — no runtime C14 verification.
- **G-7:** `MCPService` not registered/started by kernel → `connect_all` never called.

---

## 18. Required Fixtures

Promote to a new **`tests/integration/conftest.py`** (and optionally root `conftest.py`):

1. **`integration_mcp_manager`** — real `MCPManager` pointed at temp `config/mcp` (mock-server commands), `connect_all()` in fixture setup, `disconnect_all()` teardown.
2. **`unified_mock_mcp_manager`** — single duck-typed `MockMCPManager` accepting an injectable mock server (replaces the 10+ duplicated per-file copies); one instance per adapter type.
3. **`kernel_with_all_capabilities`** — boots real kernel via `run_kernel(KernelConfig(data_dir=tmp))` with chdir to temp `./config/capabilities`; injects the connected `integration_mcp_manager` into the adapters (works around D-01).
4. **`reset_singletons`** (autouse) — `_reset_all_singletons()` before/after (promote from `test_kernel_lifecycle_e2e.py` / `test_m8_t5_*`).
5. **`temp_vault`** — real temp filesystem vault (reuse Obsidian test pattern).
6. **`seeded_*` helpers** — `seed_notion(server, ...)`, `seed_obsidian(vault, ...)`, `seed_claude_mem(server, ...)`, `seed_graphify(server, ...)` (reuse existing module helpers).
7. **`failure_injector`** — context manager to flip a mock server into error/timeout/malformed modes (F-1..F-16).
8. **`mock_observation_factory`** — builds `HermesObservation` / `ExecutionResult` with attacker-controlled provenance to test spoof resistance (SEC-8).
9. **`gated_marker`** — formalize `HERMES_ACP_TEST` / `PLAYWRIGHT_E2E_TEST` / `GRAPHIFY_E2E_TEST` into `@pytest.mark.gated` + env check.

---

## 19. Required Test Files

> Place under `tests/integration/` (cross-integration) unless noted. All new. Do NOT modify existing T1–T5 test files (only reuse fixtures).

| File | Covers | Est. tests |
|---|---|---|
| `test_m8_t6_cross_adapter_matrix.py` | §6 pairs 1–10 (Hermes×Playwright, ×Graphify, ×knowledge; Playwright×Graphify; Graphify×knowledge; all-external) | 22 |
| `test_m8_t6_e2e_workflows.py` | §7 E2E-1..E2E-5 full target flow | 12 |
| `test_m8_t6_failure_injection.py` | §8 F-1..F-16 failure injection | 18 |
| `test_m8_t6_evidence_provenance.py` | §9 P-1..P-9 + D-03/D-04/D-05/D-06 regression flags | 16 |
| `test_m8_t6_authority_boundary.py` | §10 A-1..A-8 + A-4 cross-cutting import-seam test | 12 |
| `test_m8_t6_capability_registry.py` | §11 C-1..C-9 with dynamic manifests | 12 |
| `test_m8_t6_session_isolation.py` | §12 S-1..S-7 concurrent/sequential sessions | 12 |
| `test_m8_t6_security_integration.py` | §13 SEC-1..SEC-12 | 16 |
| `test_m8_t6_degraded_mode.py` | §14 DG-1..DG-6 | 8 |
| `test_m8_t6_recovery.py` | §15 RC-1..RC-5 | 7 |
| `test_m8_t6_production_paths.py` | §16 real-MCPManager subprocess harness (mock-server commands) | 10 |
| `tests/integration/conftest.py` | §18 shared fixtures + marker registration | — |
| `pyproject.toml` (EDIT) | register markers `integration/e2e/gated/security/slow/external/real` | — |

**Total estimated new M8-T6 tests: ~145.**

> Note: 145 is an estimate based on the matrices above; Terminal 2 should right-size during implementation but should not drop below coverage of every row in §6–§15.

---

## 20. Test-Count Baseline

- **Measured baseline (this task):** `1418` collected (`1185` unit + `230` integration + `4` performance).
- **Authoritative cumulative (post-T5, per QA):** `1416 passed / 2 skipped`.
- **Estimated new M8-T6:** ~`145`.
- **Projected total:** ~`1561` collected (`1418 + 145`); `1563` counting a couple of parametrizations.
- **Exact files to create:** 12 files listed in §19 (11 test files + 1 conftest). `pyproject.toml` marker registration is the only existing file to modify (additive; does not alter T1–T5 behavior).
- Terminal 2 MUST record the true before/after `pytest` totals (see §2.1).

---

## 21. Acceptance Criteria

M8-T6 is **NOT complete merely because all individual adapter tests pass.** It is complete when:

1. Every row in §6 (Integration Matrix) has ≥1 passing test.
2. Every E2E scenario §7.1–§7.5 passes.
3. Every failure mode F-1..F-16 is exercised and degrades gracefully (no silent failure→success).
4. P-1..P-9 provenance assertions pass where the code supports them; D-03/D-04/D-05/D-06 are **documented as findings** with failing/xfail tests that prove the gap (not silently skipped).
5. A-1..A-8 authority-boundary assertions pass (including the new cross-cutting import-seam test).
6. C-1..C-9 capability-registry assertions pass.
7. S-1..S-7 session-isolation assertions pass.
8. SEC-1..SEC-12 security-integration assertions pass.
9. DG-1..DG-6 degraded-mode and RC-1..RC-5 recovery assertions pass.
10. The §16.1 production-path harness exercises real `MCPManager` stdio subprocess startup (mock-server commands) for Graphify/Notion/Obsidian/Claude-Mem — not just in-process doubles.
11. New markers (`integration`/`e2e`/`gated`/`security`/`external`/`real`/`slow`) registered; gated real-external tests selectable/deselectable.
12. **Backward compatibility:** full `pytest` run shows M7 FROZEN suites + T1–T5 suites still green (no regression). Any regression is REPORTED, not fixed in M8-T6.
13. Findings D-01..D-09 and G-1..G-7 are each recorded in the M8-T6 implementation/QA report with severity and recommended owner (Terminal 3 or a follow-up task).

---

## 22. Failure Severity Classification

| Severity | Definition | Examples |
|---|---|---|
| CRITICAL | Breaks production integration or one whole perspective; must be reported to Terminal 3 | D-01 (disconnected chain), D-02 (user_sim crash) |
| HIGH | Provenance/security guarantee violated in a path | D-03 (Graphify unmarked writes) |
| MEDIUM | Integrity gap that weakens auditability | D-04 (no correlation propagation), D-05 (Playwright unmarked), D-06 (Obsidian list_notes), D-09 (flaky test) |
| LOW | Hygiene / dead code / schema inconsistency | D-07 (dead verifier), D-08 (Hermes missing flags) |

---

## 23. Implementation Order (Terminal 2)

1. **Scaffold:** create `tests/integration/conftest.py`; register markers in `pyproject.toml`; promote `reset_singletons`, `unified_mock_mcp_manager`, `kernel_with_all_capabilities`, `temp_vault`, `failure_injector` fixtures.
2. **Cross-adapter matrix** (`test_m8_t6_cross_adapter_matrix.py`) — establishes that adapters compose. (Pairs §6.)
3. **Capability registry** (`test_m8_t6_capability_registry.py`) — T5 flow with dynamic manifests.
4. **Evidence/provenance** (`test_m8_t6_evidence_provenance.py`) — P-1..P-9; encode D-03/D-04/D-05/D-06 as `xfail(strict=False)` findings.
5. **Authority boundary** (`test_m8_t6_authority_boundary.py`) — A-1..A-8 + import-seam test.
6. **Session isolation** (`test_m8_t6_session_isolation.py`) — S-1..S-7.
7. **Security integration** (`test_m8_t6_security_integration.py`) — SEC-1..SEC-12.
8. **Failure injection** (`test_m8_t6_failure_injection.py`) — F-1..F-16.
9. **Degraded mode** (`test_m8_t6_degraded_mode.py`) — DG-1..DG-6.
10. **Recovery** (`test_m8_t6_recovery.py`) — RC-1..RC-5.
11. **E2E workflows** (`test_m8_t6_e2e_workflows.py`) — §7.1–§7.5 (depends on all above).
12. **Production paths** (`test_m8_t6_production_paths.py`) — §16.1 real-MCPManager harness (highest risk; do last).
13. **Run full suite**; record before/after totals; confirm no M7/T1–T5 regression.

---

## 24. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| D-01 blocks real-path tests | High | Critical | §16.1 harness injects connected MCPManager; report to Terminal 3 |
| D-02 blocks user_sim E2E | High | High | Test user_sim path with workaround; report crash as CRITICAL finding |
| Flaky D-09 destabilizes full run | Medium | Medium | Quarantine D-09 or run in isolation; flag to logging subsystem |
| Real subprocess harness flakiness (stdio) | Medium | Medium | Use mock-server commands; generous timeouts; CI retry |
| Over-claiming "production integration" | Medium | High | Strict §17 boundary; mock vs production vs real-external separation |
| M7/T1–T5 regression during suite | Low | High | Full-suite baseline gate; report, don't fix |

---

## 25. Do-Not-Implement List (M8-T6 scope guard)

- No modification of `src/aios/**` production code (this is a test-planning + test-implementation task; the test files themselves are in-scope, production fixes are NOT).
- No M9 features (LearningService convergence, RCA expansion, model router, convergence detection, adaptive replanning).
- No "fixing" of D-01..D-09 / G-1..G-7 inside M8-T6 — these are **reported findings**.
- No alteration of M7 FROZEN suites or T1–T5 tests (only fixture reuse; new shared conftest is additive).
- No new EventType (reuse canonical bus).
- No real external network calls (harness uses in-repo mock-server commands over stdio — hermetic).

---

## 26. Terminal 2 Implementation Instructions

1. Follow §23 order. Create the 12 files in §19. Do NOT touch production source.
2. Reuse existing mocks: `src/aios/adapters/mock_{hermes,hermes_acp,graphify,playwright_mcp,notion,obsidian,claude_mem}_server.py`.
3. Promote duplicated fixtures into `tests/integration/conftest.py` (§18); keep per-file fixtures only where truly local.
4. Implement the §16.1 `RealMCPManagerHarness` to launch mock servers as **production-style stdio subprocesses** (re-point `config/mcp/*.json` `command` to the mock entry points in a temp dir).
5. Encode provenance/spoof/authority assertions exactly as §9/§10/§13 specify. For confirmed gaps (D-03/D-04/D-05/D-06), write `xfail(strict=False)` tests that **demonstrate** the gap and cite the issue ID; never silently pass them.
6. Register markers in `pyproject.toml`; convert ad-hoc `pytest.skip(env-check)` into `@pytest.mark.gated` + env helper.
7. Run `pytest` on a clean checkout before and after; record true totals (§2.1, §20).
8. On any M7/T1–T5 regression: STOP, report to Terminal 3, do not patch production.

---

## 27. Terminal 3 Independent QA Instructions

1. Verify every row in §6–§15 has corresponding tests (traceability matrix).
2. Independently re-measure baseline (§20) and confirm no regression vs post-T5 `1416/2`.
3. Confirm M8-T6 does NOT implement M9 (§17.1, §25).
4. Validate that findings D-01..D-09 / G-1..G-7 are each recorded with severity + owner; the spec does not hide them.
5. Stress the §16.1 harness: confirm it exercises real `MCPManager` stdio startup, not in-process doubles (otherwise §16 acceptance fails).
6. Attempt to "fake" a production integration with a passing mock — confirm the marker scheme + test architecture prevents this (§17 boundary, §20 mock-vs-production separation).
7. Issue `M8-T6 PLANNING VERDICT` confirmation (READY FOR IMPLEMENTATION → VERIFIED) or NO-GO with specifics.

---

## 28. Verification Gate

| Gate | Condition |
|---|---|
| G1 Baseline | True before/after `pytest` totals recorded (§20). |
| G2 Coverage | §6–§15 every row covered (traceability matrix in QA report). |
| G3 Backward compat | M7 + T1–T5 suites green; zero un-reported regressions. |
| G4 Findings | D-01..D-09 / G-1..G-7 each recorded; no silent passes. |
| G5 Authority | A-1..A-8 pass (incl. import-seam test). |
| G6 Production path | §16.1 harness runs real stdio subprocess for ≥ Graphify/Notion/Obsidian/Claude-Mem. |
| G7 Scope | No M9, no production-source edits, no M7/T1–T5 test edits. |

All gates must pass for `VERIFIED`.

---

## 29. Known Limitations

1. **D-01 is a pre-existing production defect**, not introduced by M8-T6. The production integration chain is disconnected at boot. M8-T6 works around it for real-path tests via the §16.1 harness and reports it as the top finding. Resolution likely belongs to a follow-up kernel task (assign `self._mcp_manager` + call `connect_all`).
2. **D-02 (`user_simulation_agent.py:151`)** crashes the `user_simulation` perspective in production. M8-T6 can test the perspective only via a workaround (inject a bridge double exposing `_create_session_id`, or patch) and must report it as CRITICAL.
3. Real external servers (actual `graphify`, `@notion/mcp`, `obsidian-mcp`, `claude-mem`, `hermes-agent`, `@playwright/mcp`) are NOT available in CI; the harness uses in-repo mock-server **commands over stdio** to emulate the production transport without external network. This is "production-style subprocess," distinct from both in-process mocks and true real-external (which remain `@pytest.mark.gated` + env-gated and unexecuted by default).
4. `correlation_id` end-to-end traceability (D-04) is currently broken; M8-T6 asserts current behavior and flags the gap rather than fabricating a passing assertion.
5. D-09 (pre-existing flaky structured-logger test) may intermittently affect full-suite runs; quarantine or isolate before relying on the green baseline.
6. ACP real path cannot run in CI (`cwd` unset ⇒ always MCP in production wiring); ACP is exercised via the in-process `MockACPServer` and the `acp_fallback` provenance path.

---

## 30. Final Planning Verdict

### M8-T6 PLANNING VERDICT: READY FOR IMPLEMENTATION

The repository contains a complete, inspectable production integration surface (six adapters wired into one kernel + a hardened capability registry), rich in-process mock infrastructure (7 mock servers + duplicated `MockMCPManager`), and a strong kernel-boot/singleton-reset pattern — all reusable for M8-T6. The plan specifies concrete cross-adapter, E2E, failure-injection, security, degraded-mode, recovery, session-isolation, and authority-boundary suites, a new marker scheme, a shared integration conftest, and a production-path subprocess harness that distinguishes mock from production from real-external.

**However, inspection surfaced CRITICAL pre-existing defects (D-01 disconnected MCP chain; D-02 user_sim crash) and MEDIUM integrity gaps (D-03/D-04/D-05/D-06) that M8-T6 must surface as reported findings — not fix.** These do not block planning (the harness works around D-01; D-02 is testable via a bridge double), but they are the single most important output of this planning task and must reach Terminal 3 and the follow-up kernel owner.

M8-T6 is NOT complete merely because individual adapter tests pass. Completion requires demonstrating that the **integrated** AI-OS workflow coordinates multiple external capabilities while preserving authority boundaries, provenance, evidence integrity, security, isolation, failure handling, recovery, and backward compatibility — exactly the 18-point acceptance principle in the task brief.
