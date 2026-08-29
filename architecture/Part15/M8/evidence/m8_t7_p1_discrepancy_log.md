# M8-T7 — P1 Checkpoint: Static / Source Inspection Discrepancy Log

**Terminal**: 2 (QA Execution)
**Date**: 2026-08-26
**Method**: Direct source inspection (Read/Grep on working tree). No reports trusted without code evidence.
**Spec**: architecture/Part15/M8/M8-T7-IMPLEMENTATION-SPEC.md §0, §11 (IND-1)

---

## 1. F-0.1 — Contradictory T6 verdicts → re-derived from source

### 1.1 The three artifacts (verbatim verdicts)

| Artifact | Verdict | Position |
|---|---|---|
| `FINAL_M8_T6_QA_VERDICT.txt` | "NO-GO — M8-T6 NOT VERIFIED"; names D-01 + D-02 as P0/Critical; "Blocked until D-01 and D-02 are resolved" | Pre-remediation snapshot |
| `M8_T6_INDEPENDENT_QA_REPORT.md` L170 | "**NO-GO — M8-T6 NOT VERIFIED**" — confirms D-01 (kernel never assigns `_mcp_manager`) and D-02 (`_create_session_id()` AttributeError) by code inspection; warns fixtures manually inject connected managers ("workarounds") | Pre-remediation QA |
| `M8_T6_REMEDIATION_REPORT.md` | Claims all 12 defects resolved: D-01/02/03/10/11/12 FIXED in code; D-04..D-09 "verified not applicable". Sign-off: "READY FOR INDEPENDENT QA RE-VERIFICATION (TERMINAL 3)" | Post-remediation claim |

**Contradiction is real**: two NO-GO artifacts remain in the tree alongside a remediation report claiming resolution, and Terminal 3 never issued a post-remediation GO.

### 1.2 Source-of-truth status of each defect (this inspection)

| ID | Claimed status (remediation report) | Independent source check | Evidence (file:line) |
|---|---|---|---|
| **D-01** kernel `_mcp_manager` lifecycle | FIXED | ✅ **PRESENT IN SOURCE** — `_init_mcp_manager()` assigns `self._mcp_manager = get_mcp_manager()`; called in `start()` after core components; property `mcp_manager` returns it | `src/aios/core/kernel.py:422`, `kernel.py:713-734`, `kernel.py:342-344`; singleton import `kernel.py:112` |
| **D-02** UserSimulationAgent session creation | FIXED | ✅ **PRESENT IN SOURCE** — calls `await self._bridge.create_worker_session(environment={"app_url": app_url})`; comment documents removal of non-existent `_create_session_id()`; returned id stored in `self._active_session` | `src/aios/core/user_simulation_agent.py:151-156` |
| **D-03** Graphify write-path C14 provenance | FIXED | ✅ **PRESENT IN SOURCE** — `_mark_advisory` invoked on all four write paths: store_node, update_node, delete_node, add_edge (plus read paths) | `src/aios/adapters/graphify_adapter.py:474, 505, 550, 580, 633` (+ reads 658-659, 740-741, 787, 819-820) |
| **D-04** orchestrator correlation_id propagation into adapter provenance | "Verified not applicable" | ⚠️ **STILL AN OPEN BEHAVIORAL GAP** — adapters generate per-call uuid correlation_ids; external ids are NOT propagated. The xfail test at line 165 asserts desired behavior and still fails. "Not applicable" is a relabeling, not a fix. Classified per spec §12 as observability gap (P2-class), but the xfail label must be corrected (see §2). | `test_m8_t6_evidence_provenance.py:165-177` vs adapter `_make_provenance` implementations |
| **D-05** Playwright advisory provenance marker | "Verified not applicable" | ⚠️ To be re-tested positively (Phase P3/xpass check) — xfail at line 443 may now XPASS if remediation added markers to execute_action results | `test_m8_t6_evidence_provenance.py:443-457` |
| **D-06** Obsidian list_notes fs fallback bypassing _mark_advisory | "Verified not applicable" | ⚠️ To be re-tested positively — xfail at line 461 | `test_m8_t6_evidence_provenance.py:461-473` |
| **D-07..D-09** | "Verified not applicable" | Not independently re-derived yet; will confirm via targeted suites (P2-P5) | TBD |
| **D-10** ArchitectureAgencyAdapter async Graphify traversal | FIXED | ✅ **PRESENT IN SOURCE** — `asyncio.run(...)` around `get_dependency_chain` and `get_related_entities`; traversal results consumed into findings (graph data, not text fallback when graph connected) | `src/aios/adapters/architecture_agency_adapter.py:109-139` |
| **D-11** MCP config transport loading | VERIFIED | ✅ **CONFIRMED IN SOURCE** — `class MCPTransport(str, Enum)` accepts plain JSON string values like `"stdio"` via str inheritance | `src/aios/core/mcp_manager.py:32` |
| **D-12** SecurityManager env validation with None | FIXED | ✅ **PRESENT IN SOURCE** — `_validate_env` guards `if config.env is None or not config.env: return violations` BEFORE iteration; credential checks preserved for populated env; plus `mcp_manager.py:322` `launch_env = config.env if config.env else None` | `src/aios/core/security_manager.py:842-858`; `src/aios/core/mcp_manager.py:322` |

**Conclusion**: D-01/D-02/D-03/D-10/D-12 remediations are genuinely present in current source. The stale NO-GO artifacts describe a repository state that no longer exists. D-04 remains a REAL behavioral gap (relabeled "not applicable"); D-05/D-06 pending positive re-test.

---

## 2. F-0.2 — Stale xfail markers contradict remediation claims (IND-1 grep evidence)

5 `xfail(strict=False)` markers confirmed at `tests/integration/test_m8_t6_evidence_provenance.py`:

| Line | Test | Encoded defect |
|---|---|---|
| 165 | `test_p3_correlation_id_propagation_xfail` | D-04 |
| 411 | `test_p9_d03_graphify_write_unmarked` | D-03 |
| 428 | `test_p9_d04_correlation_not_propagated_notion` | D-04 |
| 443 | `test_p9_d05_playwright_no_advisory` | D-05 |
| 461 | `test_p9_d06_obsidian_list_fallback_unmarked` | D-06 |

Because remediation added `_mark_advisory` to Graphify write paths, the D-03 xfail (line 411) is expected to XPASS (strict=False → silent pass while mislabeled). All 5 will be re-run as positive assertions in Phase P3 (task #3). **No test weakening permitted; conversion only where behavior is genuinely closed.**

---

## 3. F-0.3 — "Production" configs point at MOCK servers

Enumerated all 11 files in `config/mcp/*.json` (command + server_id extracted programmatically):

| File | server_id | command | Classification ceiling |
|---|---|---|---|
| agent_reach_mcp.json | agent_reach | `python -m aios.adapters.mock_agent_reach_server` | Tier B (prod-style subprocess of in-tree mock) |
| claude_mem_mcp.json | claude_mem | `python -m aios.adapters.mock_claude_mem_server` | Tier B |
| graphify_mcp.json | graphify | `python -m aios.adapters.mock_graphify_server` | Tier B |
| graphify-test.json | graphify-test | mock_graphify_server | Tier B (test-only) |
| graphify-tools.json | graphify-tools | mock_graphify_server | Tier B (test-only) |
| hermes_agent_ext_mcp.json | hermes_agent_ext | `python -m aios.adapters.mock_hermes_server` | Tier B |
| notion_mcp.json | notion | `python -m aios.adapters.mock_notion_server` | Tier B |
| obsidian_mcp.json | obsidian | `python -m aios.adapters.mock_obsidian_server` | Tier B |
| test-gate-first.json | test-gate-first | mock_graphify_server | Tier B (security-test fixture) |
| test-reject.json | test-reject | *(no command)* | security-test fixture |
| test_mcp.json | test_mcp | `echo mock` | security-test fixture |

**Additional finding**: there is NO `config/mcp/playwright_mcp.json`. Playwright wiring differs from other adapters:
- Kernel constructs `PlaywrightMCPAdapter(server_id="playwright_mcp", mcp_manager=self._mcp_manager)` (`kernel.py:1099-1102`) → injected-manager path connects only if a server with that id is registered in MCPManager (none is, by default config).
- Adapter's direct path (`_find_playwright_command`, `playwright_mcp_adapter.py:642-665`) uses mock server iff `HERMES_MOCK_PLAYWRIGHT` ∈ {1,true,yes}; otherwise tries `node node_modules/@playwright/mcp/index.js` then `npx @playwright/mcp`.
- Environment check: Node v24.12.0 / npx 11.6.2 installed; **`@playwright/mcp` NOT installed globally** (`npm ls -g` shows no @playwright scope).

⇒ Real `@playwright/mcp` execution would require an npx download at test time; treat as environment-limited. Max production-path class achievable in this environment = **Tier B** (production-style local subprocess running in-tree mock servers). **No Tier C claims will be made.**

---

## 4. F-0.4 — Full suite runtime

Planning measured complete run: 1539 passed / 2 skipped / 5 xfailed, exit 0, 766.74s (~12m47s). Fresh execution happens in Phase P8 (baseline collection first, task #2).

---

## 5. Discrepancies introduced to the record

1. **DISC-T2-01 (documented)**: `FINAL_M8_T6_QA_VERDICT.txt` is stale (pre-remediation) but retained in tree — NOT deleted (per task brief §3: do not silently delete historical QA artifacts).
2. **DISC-T2-02 (defect-classification)**: Remediation report labels D-04 "verified not applicable," but the behavior gap (orchestrator correlation_id not propagated into adapter provenance) demonstrably persists — the xfail test asserting desired behavior fails. Relabel ≠ fix. Severity per spec §12: observability/correlation gap = P2 track (non-blocking IF graceful degradation specified); xfail label itself = mislabeled-test finding.
3. **DISC-T2-03 (environment)**: No `playwright_mcp.json`; Playwright prod path depends on env var or npm package that is absent. Honest classification enforced downstream.

— P1 checkpoint complete. Proceeding to fresh baseline collection.
