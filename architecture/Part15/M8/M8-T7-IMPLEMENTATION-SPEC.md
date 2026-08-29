# M8-T7 — Independent QA / Regression

**Author**: Terminal 1 — M8-T7 Independent QA / Regression Planning Agent
**Status**: PLANNING-ONLY SPECIFICATION (no code changes, no remediation, no GO authority)
**Date**: 2026-08-26
**Upstream gates claimed**: M7 FROZEN · M8-T1..T6 = GO (per task brief)
**M8-T7 purpose**: Independent final QA of the entire M8 scope, then hand off to Terminal 2 (execute) and Terminal 3 (verify).

> This document is grounded in the **current repository state** as inspected on 2026-08-26. Where the task brief's claims diverge from the repository, the repository wins. Discrepancies are called out as findings, not assumed away.

---

## 0. CRITICAL REPOSITORY FACTS DISCOVERED DURING PLANNING

These were found by direct inspection and materially shape the QA strategy.

### F-0.1 Contradictory M8-T6 verdicts in the repo

Two artifacts in the working tree disagree about M8-T6:

- `FINAL_M8_T6_QA_VERDICT.txt` → **`VERDICT: NO-GO — M8-T6 NOT VERIFIED`**, names **D-01 and D-02 as P0/Critical blockers**, and states *"M8-T7 READINESS: NO - Blocked until D-01 and D-02 are resolved"*.
- `M8_T6_INDEPENDENT_QA_REPORT.md` → **NO-GO**, confirms D-01/D-02 by code inspection, notes fixtures manually inject connected managers ("workarounds").
- `M8_T6_REMEDIATION_REPORT.md` → claims **all 12 defects (D-01..D-12) REMEDIATED**, with D-01/D-02/D-03/D-10/D-11/D-12 code-fixed, and D-04..D-09 "verified not applicable."
- The **task brief** asserts M8-T6 = GO/VERIFIED with D-01..D-12 resolved.

**Resolution by source inspection (authoritative):** The remediations **are present in the current source code**:

- `kernel.py:713-734` `_init_mcp_manager()` assigns `self._mcp_manager = get_mcp_manager()` and is called at `kernel.py:422` → **D-01 remediated in code**.
- `user_simulation_agent.py:155` now calls `await self._bridge.create_worker_session(...)` (no more `_create_session_id()`) → **D-02 remediated in code**.
- `graphify_adapter.py:474/550/580/633` write paths now call `self._mark_advisory(result)` → **D-03 remediated in code**.

So the source is post-remediation. **BUT** the remediation report's own sign-off says *"READY FOR INDEPENDENT QA RE-VERIFICATION (TERMINAL 3)"* — i.e. Terminal 3 never issued a GO on the remediated code. The `FINAL_M8_T6_QA_VERDICT.txt` is the **pre-remediation** NO-GO and is stale but still present in the tree.

**M8-T7 implication:** The production call paths that D-01/D-02/D-03 fixed MUST be independently re-verified against the *real* boot path — not via fixtures that inject `mcp_manager` manually. The prior QA explicitly warned that fixtures paper over production defects. M8-T7 must use live `HermesKernel.start()` and `run_kernel()` paths.

### F-0.2 Stale xfail markers contradict the remediation claim

`tests/integration/test_m8_t6_evidence_provenance.py` still contains **5 `xfail(strict=False)` markers** (lines 165, 411, 428, 443, 461) encoding D-03..D-06 as *open gaps*:

- L165 D-04 — "orchestrator correlation_id not propagated into adapter provenance"
- L411 D-03 — "Graphify write paths (store_node) return results without C14 advisory markers"
- L428 D-04 — repeated
- L443 D-05 — "Playwright results carry no advisory provenance marker"
- L461 D-06 — "Obsidian list_notes filesystem fallback bypasses _mark_advisory"

Yet `M8_T6_REMEDIATION_REPORT.md` claims D-03 was **fixed in code** and D-04..D-06 were "verified not applicable." **If D-03 is truly fixed, the L411 xfail is wrong and would now FAIL-to-xfail (strict=False so it just passes silently but is mislabeled).** M8-T7 must independently determine whether these gaps are genuinely closed in behavior or merely relabeled in the report. These xfail markers are a credibility gap and must be re-tested as positive assertions.

### F-0.3 "Production" configs point at MOCK servers

Inspection of `config/mcp/*.json` shows the kernel's MCP server configs launch **in-tree mock servers**, not real external systems:

- `graphify_mcp.json` → `python -m aios.adapters.mock_graphify_server`
- `notion_mcp.json`, `obsidian_mcp.json`, `claude_mem_mcp.json` → corresponding `mock_*_server` modules
- `hermes_agent_ext_mcp.json` → mock hermes MCP; ACP path points at `acp_adapter.entry`

Node/npx **are installed** (`C:\Program Files\nodejs`), so a real `@playwright/mcp` subprocess *could* be launched, but **no real Notion/Obsidian/Claude-Mem/Graphify credentials or instances exist**. Therefore:

- **mock/in-process** = adapter logic driven by `Mock*Server` coroutines via `unified_mock_mcp_manager` fixture.
- **production-style local subprocess** = kernel launches a real stdio subprocess that happens to be an in-tree mock server (`mock_graphify_server` etc.). This is the strongest verification available here; it exercises the *real* MCPManager→subprocess→transport→adapter→provenance path without mocking the transport.
- **real external integration** = NOT ACHIEVABLE in this environment for Notion/Obsidian/Claude-Mem/Graphify/Hermes. M8-T7 must NOT claim real external execution.

### F-0.4 Full suite runtime is long but completes (NOT a hang)

During planning a full `pytest -q` run **completed** in 766.74s (12m46s) with exit 0 — `1539 passed, 2 skipped, 5 xfailed`. An early read of the background output showed empty because the run was still in progress; it was a read-timeout artifact, not a hang. The individual M8-T6 subprocess-driven suites (Hermes ACP, Playwright, production_paths) are the slow ones (stdio subprocess launches). M8-T7 must still capture per-suite wall-clock and use timeouts, but a complete full regression IS achievable in this environment.

---

## 1. CURRENT REPOSITORY BASELINE (grounded)

### 1.1 Collection + execution counts (measured via `pytest --collect-only` and a full `pytest -q` run)

| Bucket | Count | Source |
|--------|-------|--------|
| Total collected | **1546** | `pytest --collect-only -q` |
| unit | **1185** | `tests/unit --collect-only` |
| integration | **357** | `tests/integration --collect-only` |
| performance | **4** | `tests/performance --collect-only` |
| **Total executed (full run)** | **1546** | `pytest -q` (exit 0, 766.74s) |
| **passed** | **1539** | full run |
| **skipped** | **2** | full run |
| **xfailed** | **5** | full run (all in `test_m8_t6_evidence_provenance.py`, D-03..D-06) |
| **failed** | **0** | full run |

> The full suite **was** run to completion during planning: `1539 passed, 2 skipped, 5 xfailed, 2713 warnings in 766.74s (0:12:46)`, exit code 0. So executed/passed/skip/xfail counts ARE independently confirmed. The earlier "hang" observation (F-0.4) was a read-timeout artifact, not a real hang — the run completed in ~12.8 min. Terminal 2 should still budget per-suite timeouts because individual M8-T6 subprocess suites are slow (stdio subprocess launches).

### 1.2 M8-specific suites discovered (integration)

- `test_m8_hermes_acp.py`, `test_m8_playwright.py`, `test_m8_graphify.py`, `test_m8_notion.py`, `test_m8_obsidian.py`, `test_m8_claude_mem.py`
- `test_m8_t5_dynamic_loading.py`, `test_m8_t5_security.py`
- `test_m8_t6_*`: `e2e_workflows`, `session_isolation`, `security_integration`, `recovery`, `production_paths`, `degraded_mode`, `cross_adapter_matrix`, `authority_boundary`, `failure_injection`, `capability_registry`, `evidence_provenance`

### 1.3 Skipped/xfail markers (grep evidence)

Skipped (explicit): `test_agency_adapters.py` (2), `test_capability_manifest.py::test_disabled_manifest_skipped`, `test_lifecycle_manager.py::test_registration_skipped_when_no_registry`, `test_m7_security.py::test_security_adapter_skips_when_manager_denies`, `test_m8_t5_security.py` (2 — malformed manifest fields), `test_m8_t6_capability_registry.py::test_c2_malformed_manifest_skipped_not_raised`. Plus the 5 xfail in evidence_provenance.

Known flaky (per prior reports, must be confirmed): `test_structured_logger_perf.py` correlation test (pre-existing, not M8).

### 1.4 Git status (relevant)

- Working tree is **dirty**: M7/M8 source modified (not committed), many M8 files untracked.
- `config/capabilities/*.yaml` (5 manifests: claude_mem, graphify, notion, obsidian, playwright), `config/mcp/*.json` present.
- Deleted: `M5/M6/M7_*.md` reports (git rm -style deletes, untracked recreated versions exist in tree).

### 1.5 Explicitly NOT asserted

- I do **not** assert any M8-T1..T6 GO — only that remediations are present in source (F-0.1) and the full suite currently passes (1539/2/5).
- I do **not** claim real external integration is achievable (F-0.3).
- Execution DID complete: 1539 passed, 2 skipped, 5 xfailed (see §1.1). The 5 xfails encode D-03..D-06 and are still open markers (F-0.2).

---

## 2. M8 IMPLEMENTATION INVENTORY (inspected)

| Task | Files (inspected) | Key facts |
|------|-------------------|-----------|
| **T1 Hermes/ACP** | `hermes_bridge.py`, `acp_adapter.py`, `acp_session.py`, `mock_hermes_server.py`, `mock_hermes_acp_server.py` | ACP stdio subprocess transport; MCP fallback; `HermesObservation.trust_level="untrusted"`; `ProtocolUnavailableError`, `SecretLeakDetectedError` defined. |
| **T2 Playwright** | `playwright_mcp_adapter.py` (773 ln), `playwright_session.py`, `mock_playwright_mcp_server.py` | `BaseExecutionAdapter`; `PlaywrightSessionRegistry`; env-scrub patterns; security error classes. |
| **T3 Graphify** | `graphify_adapter.py`, `mock_graphify_server.py` | `_mark_advisory()` called on read+write paths (write paths added by D-03). `SENSITIVE_PROPERTY_KEYS`, `SECRET_VALUE_PATTERNS`, size limits. |
| **T4 Notion/Obsidian/Claude-Mem** | `notion_adapter.py`, `obsidian_adapter.py`, `claude_mem_adapter.py`, `mock_*_server.py` | All `BaseExecutionAdapter`; advisory marking; filesystem fallback in Obsidian adapter. |
| **T5 Capability hardening** | `capability_manager.py` (1280 ln), `capability_manifest.py` (524), `capability_provenance.py` (422), `adapter_factory.py` (196) | Manifest loader + registry + provenance + allowlisted factory. Non-auto-trust enforced; builtin/trusted rejected from manifest; authoritative rejected at manifest level. |
| **T6 Production wiring** | `kernel.py` (`_init_mcp_manager` L713-734, wired at L422, adapters at L909..1241), `user_simulation_agent.py` (L155 fixed), `mcp_manager.py`, `security_manager.py` | D-01 kernel MCP assignment; D-02 session creation; D-12 env null-safety. |

### 2.1 Call-path map (production, post-D-01)

```
HermesKernel.start()
  └─ _init_mcp_manager()  → self._m_manager = get_mcp_manager()        (D-01)
  └─ _init_graphify/playwright/notion/obsidian/claude_mem()
        each: AdapterClass(mcp_manager=self._mcp_manager)             (real manager injected)
  └─ _init_capability_manifests()
        → CapabilityManifestLoader.load_all()  (config/capabilities/*.yaml)
        → CapabilityManager.register_capability()  (SecurityManager gate CM-SEC-001)
        → initialize_capability() → AdapterFactory.get_adapter()      (allowlist + path-traversal)

Adapter.execute()
  └─ _call_tool() → MCPManager.call_tool(server_id, tool, args)
        → SecurityManager.gate_before_connect (C18)  ← env null-safety (D-12)
        → stdio subprocess (mock_*_server)   [mock/in-process = Mock*Server coroutine]
        → result → adapter._mark_advisory(result)  (C14)
        → ExecutionResult
```

### 2.2 Authority boundaries (as coded)

- `CapabilityProvenance` defaults `authority="contextual"`, `advisory=True`, `trust_level="untrusted"`.
- `mark_capability_advisory()` **force-sets** `source/advisory/authority/trust_level` (cannot be overridden by external input) — spoof-proof re-assertion.
- `capability_manifest.py` rejects external `trust_level=builtin|trusted` and `authority_classification=authoritative`.
- `CapabilityManager.register_capability` raises `CM-SHADOW-001` (lower-trust shadow attempt) and `CM-PREC-001` (equal/lower precedence) — collision/shadow protection.
- `HermesObservation.trust_level="untrusted"` hardcoded; Hermes returns observations only.

---

## 3. COMPLETE M8 QA MATRIX

### 3.A Functional validation

| ID | Area | Independent check | Path class |
|----|------|-------------------|------------|
| FA-1 | Hermes ACP session create/exec/close | Drive `AcpAdapter` against mock hermes ACP subprocess; assert session id + observation trust=untrusted | prod-style subprocess |
| FA-2 | Hermes MCP fallback | Force ACP unavailable → assert MCP fallback used | prod-style |
| FA-3 | Playwright browser exec | Launch real `@playwright/mcp` if possible, else mock; assert evidence captured | prod-style / mock |
| FA-4 | Graphify CRUD + context | store/get/update/delete_node, add_edge, get_dependency_chain | prod-style (mock server) |
| FA-5 | Notion ops | search/get/create/update/query | prod-style (mock) |
| FA-6 | Obsidian ops | read/write/list + filesystem fallback | prod-style (mock) |
| FA-7 | Claude-Mem ops | context/recent/by_tag | prod-style (mock) |
| FA-8 | Capability discovery/load/resolve | manifest → register → resolve | in-process + prod-style |
| FA-9 | Agency integration | ArchitectureAgency + Graphify (D-10 real traversal) | in-process |
| FA-10 | UserSimulationAgent | create session via bridge (D-02) | prod-style kernel |

### 3.B Cross-integration golden + failure flows

End-to-end chain (§ from task): Kernel → Capability Registry → selection → Adapter → MCP/ACP → External (mock) → Observation → Evidence/prov → Testing → Review. Test **at least** these flows:

- **GI-1 (golden)**: kernel boot → capability manifest auto-discovery → resolve external capability → adapter executes via MCP → result carries C14 provenance → recorded as evidence.
- **GI-2 (golden)**: ArchitectureAgency uses Graphify real traversal (D-10) — assert graph data returned, **not** text fallback.
- **GI-3 (golden)**: UserSimulationAgent creates isolated `hermes_<uuid>` session, runs, closes.
- **GI-4 (failure)**: capability unavailable → `CM-RES-001` raised, no execution.
- **GI-5 (failure)**: adapter subprocess dies mid-execution → typed error, no verdict leakage.

### 3.C Failure & recovery (independent)

| ID | Scenario | Expected |
|----|----------|----------|
| FR-1 | adapter/MCP unavailable | connection error, no crash |
| FR-2 | ACP unavailable → MCP fallback | fallback used, provenance.protocol reflects |
| FR-3 | malformed external response | `MalformedResponseError`, not silently trusted |
| FR-4 | timeout | `ExecutionTimeout`, cleanup |
| FR-5 | subprocess failure | typed infra error, session cleaned |
| FR-6 | session creation failure | `SessionCreationTimeout`, no leaked session |
| FR-7 | session cleanup failure | error recorded, no hang |
| FR-8 | Graphify/Notion/Obsidian/Claude-Mem unavailable | each adapter own UnavailableError |
| FR-9 | capability initialization failure | `availability=ERROR`, `last_error` set, registry intact |
| FR-10 | invalid manifest | `ManifestValidationError`, skipped not raised |
| FR-11 | security gate rejection | `CM-SEC-001` raised |
| FR-12 | collision/shadow attempt | `CM-SHADOW-001` / `CM-PREC-001` |
| FR-13 | partial execution | partial result, no authoritative verdict |
| FR-14 | recovery after failure | re-init capability → AVAILABLE |

### 3.D Provenance / evidence integrity

Assert each field present and correct on real execution results: `task_id`, `execution_id`, `session_id`, `correlation_id`, `adapter`, `protocol`, `operation`, `timestamp`, `target`, `errors`, `environment`, parameter hash, secret scrubbed, evidence bound. **Explicitly test**: external system cannot set `authority`/`trust_level`/`advisory` to authoritative/trusted (spoof attempt → force-overridden).

### 3.E Authority boundaries (search for leakage)

Verify each: Hermes observation-only; Playwright substrate-only; Graphify advisory-only; Notion planning-only; Obsidian knowledge-only; Claude-Mem memory-only; Agent Reach untrusted; external skills non-authoritative; **no external adapter can emit PASS/FAIL**; SecurityManager retains security authority; StateManager state authority; WorkflowManager workflow authority; Council/Judge decision authority. Scan both code and runtime results for verdict-language injection.

---

## 4. SESSION ISOLATION

- SI-1 concurrent sessions (Hermes `hermes_<uuid>`) — no id collision.
- SI-2 separate session IDs, no state leakage between.
- SI-3 Playwright browser-context isolation per session.
- SI-4 external capability isolation (separate provenance).
- SI-5 cleanup on success and on failure.
- SI-6 repeated execution idempotency.
- SI-7 failure during cleanup → no hang, no leaked process.
- SI-8 stale session reaping.

---

## 5. SECURITY INTEGRATION (sanity only, not M11 audit)

- SEC-1 secret scrubbing (env + param patterns).
- SEC-2 environment validation (null `env` — D-12).
- SEC-3 parameter hashing present.
- SEC-4 sensitive-key rejection (`SENSITIVE_PROPERTY_KEYS`, capability `sensitive_keys`).
- SEC-5 payload size limits (`MAX_PROPERTY_VALUE_SIZE`, `max_content_size`).
- SEC-6 URL restrictions (navigation allowlist).
- SEC-7 DOM/content redaction.
- SEC-8 filesystem traversal (Obsidian fallback path sandbox).
- SEC-9 namespace isolation.
- SEC-10 manifest validation (`capability_manifest.py` reject builtin/trusted/authoritative).
- SEC-11 capability collision (`CM-SHADOW-001`).
- SEC-12 external repo restrictions (manifest loader = local only, no Git).
- SEC-13 MCP/ACP boundary (factory allowlist + path traversal).
- SEC-14 least privilege.
- SEC-15 malformed/untrusted external response handling.
- SEC-16 prompt/injection-like external content neutralized (no authority escalation).

---

## 6. PRODUCTION-PATH VERIFICATION (honest classification)

| Adapter | Production instantiation | How obtained | Subprocess | Session | Exec | Result | Provenance | Failure prop |
|---------|--------------------------|--------------|-----------|---------|-------|--------|-----------|--------------|
| Graphify | `GraphifyAdapter(mcp_manager=kernel._mcp_manager)` | `get_mcp_manager()` | `mock_graphify_server` (in-tree) | n/a | `_call_tool` | raw→`_mark_advisory` | C14 | error raised |
| Playwright | `PlaywrightMCPAdapter(...)` | kernel | mock or real `@playwright/mcp` | `PlaywrightSessionRegistry` | browser action | evidence | C14 | typed |
| Notion | `NotionAdapter(...)` | kernel | `mock_notion_server` | n/a | crud | advisory | C14 | UnavailableError |
| Obsidian | `ObsidianAdapter(...)` | kernel | `mock_obsidian_server` | n/a | crud + fs | advisory | C14 | UnavailableError |
| Claude-Mem | `ClaudeMemAdapter(...)` | kernel | `mock_claude_mem_server` | n/a | query | advisory | C14 | UnavailableError |
| Hermes (MCP) | `HermesBridge(mcp_manager=..., protocol="mcp")` | kernel | `mock_hermes_server` | `create_worker_session` | task | observation trust=untrusted | C14 | typed |
| Hermes (ACP) | `AcpAdapter` | bridge | `acp_adapter.entry` subprocess | `AcpSession` | task | observation | C14 | typed |

**Classification rule for every check:** tag as (1) mock/in-process, (2) production-style local subprocess, (3) real external. **No check may be labeled (3) unless a real external credentialed service is actually connected.** In this environment, max achievable = (2). Terminal 2 must state this limitation explicitly per adapter.

---

## 7. DYNAMIC CAPABILITY LOADING (M8-T5 claim)

**Claim to verify**: "A new external capability should not require modifying the AI-OS kernel merely because the capability is new."

Independent test (DL-series), using the existing hermetic strategy from `test_m8_t5_dynamic_loading.py`:

- DL-1 create valid external manifest in a fresh temp `config/capabilities/` (NOT the repo dir).
- DL-2 boot real kernel via `run_kernel(KernelConfig(data_dir=tmp))`.
- DL-3 assert auto-discovery + registration + resolve + execute succeed.
- DL-4 assert provenance marked (C14 spoof-proof).
- DL-5 disable/enable/deregister; confirm kernel source **unchanged** (git diff of `src/aios/core/kernel.py` empty after test).
- DL-6 malicious manifest (path traversal in class_path) → `CM-ADAPTER-001` rejected.
- DL-7 invalid manifest (missing required field) → `ManifestValidationError`.
- DL-8 collision with built-in capability id → `CM-SHADOW-001`/`CM-PREC-001`.
- DL-9 precedence manipulation (lower-trust displacing higher) → rejected.
- DL-10 unauthorized adapter (not in allowlist) → rejected.
- DL-11 unsupported operation → `CM-SEC-001`.
- DL-12 lifecycle failure (adapter `initialize()` raises) → `availability=ERROR`, registry intact.

---

## 8. M7 FREEZE VALIDATION

M7 is COMPLETE/FROZEN. M8-T7 must confirm M8 did not regress M7.

- MF-1 run `tests/integration/test_m7_*.py` (security, isolation, multi_perspective, evidence_integrity, seeded_defects, closed_loop) — all must pass.
- MF-2 run `tests/unit/test_m7_closed_loop.py`, `test_final_judge_agency.py`, `test_m6_council_synthesis.py`, `test_agency_review_production_path.py` — pass.
- MF-3 assert `TestingEvidence`, `TestOrchestratorService`, `CouncilManager`, `AIAgencyService` + 9 agencies, `Provenance` schema unchanged (import + smoke).
- MF-4 assert no production adapter boundary change that lets an external adapter emit authoritative PASS/FAIL.
- MF-5 **do not modify M7** files.

---

## 9. CROSS-CUTTING ARCHITECTURAL VALIDATION

- XA-1 no circular import among adapters/core (verify import graph clean).
- XA-2 no capability-specific kernel branching (kernel wires generic adapters only).
- XA-3 `BaseExecutionAdapter` consistency across all 6 adapters.
- XA-4 `MCPManager` lifecycle correct (singleton, gate-before-connect, connect/disconnect).
- XA-5 ACP/MCP separation preserved.
- XA-6 config correctness (`config/mcp/*.json`, `config/capabilities/*.yaml` load).
- XA-7 graceful degradation (degraded-mode suite).
- XA-8 typed errors (no bare `except:` swallowing authority).
- XA-9 timeout behavior (per-adapter timeouts).
- XA-10 cleanup behavior (sessions/processes).
- XA-11 observability/correlation propagation (re-test the 5 xfail claims F-0.2 as positive).
- XA-12 evidence consistency across adapters.
- XA-13 dead/bypassed code paths (search for `asyncio.run` misuse, discarded coroutines, `pass` after error).

---

## 10. TEST EXECUTION ORDER (staged)

| Phase | Scope | Evidence required to advance |
|-------|-------|------------------------------|
| P1 | Static/source inspection (this spec's F-0 findings) | Discrepancy log written |
| P2 | Focused M8 adapter unit tests (tests/unit/test_*adapter*, test_capability_*) | 0 unexpected failures |
| P3 | Cross-integration (test_m8_* T1..T4) | golden + failure flows green |
| P4 | Failure/recovery (test_m8_t6_failure_injection, recovery, degraded_mode) | FR-1..FR-14 covered |
| P5 | Security/authority (test_m8_t6_security_integration, authority_boundary, SEC-1..16) | no boundary leak |
| P6 | Production-style execution (prod_paths, hermes ACP subprocess, DL-series) | live kernel boot verified |
| P7 | M7 regression (MF-1..5) | M7 suites green |
| P8 | Full regression (`pytest -q` to completion) | complete run, counts |
| P9 | Terminal 3 independent re-verification | GO issued |

Each phase emits a checkpoint artifact before advancing. Any genuinely hanging suite (not merely slow — F-0.4) blocks advance until root-caused; the full suite is known to complete in ~13 min, so a single suite exceeding that is a real anomaly.

---

## 11. TEST INDEPENDENCE (anti-false-positive)

M8-T7 must not merely replay implementation-agent assertions. Add:

- **IND-1** source-level asserts: grep that `_mark_advisory` is called on all write paths (not just trust the report).
- **IND-2** negative tests: external provenance spoof attempt force-overridden.
- **IND-3** adversarial: manifest with `trust_level: trusted` → rejected; `authority_classification: authoritative` → rejected.
- **IND-4** runtime call-path: trace a real `run_kernel()` boot and assert `kernel.mcp_manager is not None` (D-01) and adapters received it — **not** via injected fixture.
- **IND-5** architecture compliance: assert no `kernel.py` capability-specific `if capability_id ==` branching.
- **IND-6** mock-only trap: any test that "passes" only because `mcp_manager` was injected manually while production boot leaves it None must be flagged. (This is exactly what the prior QA warned about.)

---

## 12. NO-GO CONDITIONS

**P0/P1 (block):**

- Authoritative decision leakage (external adapter emits PASS/FAIL or sets `authority=authoritative`).
- Security boundary bypass (secret leak, env validation crash, sensitive-key accepted).
- Broken production execution path (kernel boot leaves `mcp_manager=None` — D-01 regression).
- MCP/ACP transport fundamentally disconnected.
- Capability isolation bypass (shadow/collision succeeds).
- Evidence/provenance spoofing (external can forge `correlation_id`/`task_id` provenance).
- Secret leakage in logs/evidence.
- **M7 regression** (any M7 suite fails that passed before M8).
- Cross-system state corruption.

**P2/P3 (track, may not block if graceful degradation specified):**

- Non-critical observability gap.
- Isolated flaky test (allowed only if reproducible pre-existing and quarantined; a *new* flaky M8 test requires investigation).
- Optional dependency (real `@playwright/mcp`) unavailable where mock fallback is specified.

**Flaky-test rule:** a test is "acceptable flaky" only if (a) it existed before M8, (b) it is quarantined/retried, (c) root cause is documented and not M8-related. Any M8-introduced non-determinism is P1 until fixed.

---

## 13. TERMINAL 2 HANDOFF PROMPT

```
You are Terminal 2 — M8-T7 QA Execution Agent.

OBJECTIVE: Execute the M8-T7 independent QA plan defined in
architecture/Part15/M8/M8-T7-IMPLEMENTATION-SPEC.md against the CURRENT repo.

HARD CONSTRAINTS:
- DO NOT modify production source (src/aios/**).
- DO NOT modify existing tests.
- DO NOT modify M7.
- DO NOT silently fix or "repair" anything discovered.
- DO NOT declare GO/NO-GO. That is Terminal 3's authority only.
- DO NOT claim real external integration unless a real credentialed service is connected.

STEPS:
1. Re-establish baseline: run `pytest --collect-only -q` and record total/unit/integration/perf/skip/xfail. Then run the FULL suite with per-suite timeouts (e.g. 300s) and capture pass/fail/skip/xfail. If the suite hangs, isolate the hanging suite, report it, and continue with the rest.
2. Execute Phases P1-P8 from the spec in order. For each phase produce a checkpoint.
3. For every check, classify as (1) mock/in-process, (2) production-style local subprocess, (3) real external. State environment limitations per adapter honestly (F-0.3: configs point at in-tree mocks; no real Notion/Obsidian/Claude-Mem/Graphify/Hermes available).
4. INDEPENDENTLY re-verify the F-0 findings:
   - F-0.1: boot the REAL kernel (run_kernel) and assert kernel.mcp_manager is not None and adapters received it (D-01). Drive UserSimulationAgent session creation against the real bridge (D-02). Assert Graphify write paths return _mark_advisory results (D-03).
   - F-0.2: Re-test the 5 xfail claims (D-03..D-06) as POSITIVE assertions. Report whether each is genuinely closed in behavior or merely relabeled. If an xfail now passes (strict=False), flag it as a mislabeled test.
5. Run the DL-series dynamic-loading tests; confirm kernel.py is unmodified by `git diff --stat src/aios/core/kernel.py` after the suite.
6. Run M7 regression (MF-1..5).
7. Produce architecture/Part15/M8/M8_T7_QA_REPORT.md with:
   - baseline counts (collected vs executed vs passed vs skipped vs xfailed vs failed)
   - per-phase results
   - independent re-verification of F-0 findings with evidence
   - every defect classified P0/P1/P2/P3 with file:line
   - explicit mock vs prod-style vs real-external classification table
   - preserved evidence (command outputs, logs)
   - explicit statement: "Terminal 2 does NOT issue GO/NO-GO."
Hand the report to Terminal 3.
```

---

## 14. TERMINAL 3 HANDOFF PROMPT

```
You are Terminal 3 — M8-T7 Independent Verification Agent (final authority).

OBJECTIVE: Independently verify M8 completion. Do NOT accept Terminal 2's
conclusion. Re-derive your own evidence.

HARD CONSTRAINTS:
- Independently inspect the repository (do not trust reports).
- Independently re-run CRITICAL tests (do not trust Terminal 2's rerun).
- Challenge evidence: if a claim lacks file:line + a reproduced command, treat it as unverified.
- You issue the final GO / NO-GO verdict. Terminal 2 cannot.

VERIFY:
1. Production call paths: boot real kernel; assert mcp_manager wired (D-01); UserSimulationAgent session (D-02); Graphify write-path provenance (D-03). Reproduce, do not trust.
2. The 5 xfail (D-03..D-06): run them as positive tests; decide if gaps are real. If real → P1.
3. Authority boundaries: prove no external adapter can emit PASS/FAIL or set authority=authoritative (code + runtime).
4. Provenance/evidence: prove external spoof of authority/trust_level is force-overridden.
5. M7 freeze: run M7 suites; any regression = NO-GO.
6. Failure/recovery: rerun FR-1..FR-14 subset; confirm typed errors, no leak.
7. Dynamic loading: confirm kernel.py unmodified after DL tests.
8. Identify false positives: any test that passes only via manually-injected mcp_manager while production boot leaves it None = flag.

VERDICT: issue GO only if ALL of:
- complete M8 implementation inspected
- critical production paths verified (live boot, not fixture)
- cross-integration, failure/recovery, provenance, authority, security sanity verified
- dynamic capability loading verified
- M7 regression verified
- full regression executed to completion (no unexplained hang)
- no unresolved P0/P1
Otherwise: NO-GO with RCA, remediation path, retest requirement.

Write architecture/Part15/M8/M8_T7_VERIFICATION_VERDICT.md with your independent findings and the authoritative verdict.
```

---

## 15. ACCEPTANCE GATE

M8-T7 passes only when ALL hold:

- [ ] Complete M8 implementation inspected (T1..T6 source + configs).
- [ ] Critical production paths verified via **live kernel boot** (D-01/02/03 re-confirmed, not fixture-injected).
- [ ] Cross-integration flows verified (GI-1..5).
- [ ] Failure/recovery verified (FR-1..14).
- [ ] Provenance/evidence verified (no spoofing).
- [ ] Authority boundaries verified (no verdict leakage).
- [ ] Security sanity verified (SEC-1..16).
- [ ] Dynamic capability loading verified (DL-1..12; kernel.py unmodified).
- [ ] M7 regression verified (MF-1..5).
- [ ] Full regression executed to completion (no hang left unexplained).
- [ ] No unresolved P0/P1.
- [ ] Terminal 3 independently confirms and issues **GO**.

Then: **M8-T7 GO → M8 COMPLETE**.
Else: **M8-T7 NO-GO → RCA → remediation → retest → Terminal 3 re-verification**.

---

## 16. M8-T7 MUST NOT BECOME M9

Prohibited in M8-T7: LearningService, RCA learning pipeline, model routing, FreeLLMAPI integration, convergence detection, adaptive replanning, autonomous learning, any M9 feature. M8-T7 validates M8 only.

---

## 17. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| R-1 Stale NO-GO verdict (FINAL_M8_T6_QA_VERDICT.txt) misread as current | Med | High | Spec records F-0.1; Terminal 3 re-derives. |
| R-2 5 xfail gaps are real but relabeled fixed | Med | High (P1) | IND/F-0.2 positive re-test. |
| R-3 Full suite slow but completes (F-0.4) | Med | Low | budget ~13 min + per-suite timeouts; quarantine any genuinely hanging suite. |
| R-4 Fixtures inject mcp_manager, hiding D-01 in prod | Med | High | IND-4 live-boot check. |
| R-5 Real external services unavailable → overclaim (3) | High | High | F-0.3 classification enforced. |
| R-6 M7 regression from T6 wiring | Low | High (P1) | MF-1..5 gate. |

---

## 18. EVIDENCE REQUIREMENTS

Terminal 2/3 must preserve: command invocations + raw output, `git diff --stat` after dynamic-loading, per-phase checkpoint files, the live-kernel-boot transcript proving `mcp_manager is not None`, the re-run of the 5 xfail as positive assertions, and the M7 regression run output.

---

## 19. FINAL VERIFICATION GATE

See §15. Gate is binary: all bullets satisfied + Terminal 3 GO → M8 COMPLETE.

---

# M8-T7 PLANNING VERDICT

**READY FOR QA EXECUTION**

Rationale: The repository baseline is established (1546 collected: 1185 unit / 357 integration / 4 perf; ≥10 skipped; 5 xfailed). All M8-T1..T6 implementations are present and inspected; D-01/D-02/D-03 remediations are confirmed in current source. The QA matrix, production-path classification, dynamic-loading verification, M7 freeze, staged order, independence methodology, no-go criteria, and Terminal 2/3 handoffs are defined and grounded in observed code (including the contradictions in F-0.1/F-0.2 and the mock-server reality in F-0.3, which are explicitly built into the plan rather than assumed away).

**Caveats that Terminal 2/3 must resolve (not blockers to planning, but mandatory verification items):**
1. The pre-remediation `FINAL_M8_T6_QA_VERDICT.txt` (NO-GO) is stale and contradicts the task brief's GO claim; Terminal 3 must re-derive the T6 verdict from the remediated source.
2. The 5 xfail markers (D-03..D-06) contradict the remediation report's "fixed/not-applicable" claims and must be re-tested as positive assertions.
3. Real external integration is NOT achievable in this environment; only mock/in-process and production-style local-subprocess verification is possible. Terminal 2 must not claim real external execution.
4. The full suite's long runtime (F-0.4, ~13 min) must be captured with per-suite timeouts; any single suite exceeding that is a real anomaly to root-cause.
