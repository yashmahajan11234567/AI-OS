# M8-T7 — XFAIL Re-validation Checkpoint (positive re-run, F-0.2 / spec §0.F-0.2 + §11 XA-11)

**Terminal**: 2 · **Date**: 2026-08-26

## Commands executed
```
python -m pytest tests/integration/test_m8_t6_evidence_provenance.py -v --no-header
python -m pytest tests/integration/test_m8_t6_evidence_provenance.py --runxfail -v --no-header -k "xfail or d03 or d04 or d05 or d06"
python -m pytest "tests/integration/test_m8_t6_evidence_provenance.py::test_p3_correlation_id_propagation_xfail" --runxfail -v --no-header
```

## Results (all 5 run as positive assertions with --runxfail)

| # | Test (line) | Defect | Positive-run outcome | Root cause of failure |
|---|---|---|---|---|
| 1 | `test_p3_correlation_id_propagation_xfail` (:165) | D-04 | **FAILS** — `KeyError: 'correlation_id'` at :177 (`got.raw["provenance"]` has no correlation_id) | Graphify `get_node` marks the envelope via `_mark_advisory` but correlation_id is per-call uuid, never propagated from orchestrator |
| 2 | `test_p9_d03_graphify_write_unmarked` (:411) | D-03 | **FAILS** — `assert None == 'advisory_only'` at :423 | Remediation marked only the **adapter return envelope** (`raw=self._mark_advisory(result)` at graphify_adapter.py:474). The test inspects **server-side persisted** node properties (`graphify._mcp_manager._server._nodes[...]["properties"]["provenance"]`), which still carry `_make_provenance` output: `source="ai_os"`, no `authority="advisory_only"`, no `advisory=True`. The D-03 fix is real but boundary-limited; server-persisted write provenance remains unmarked. |
| 3 | `test_p9_d04_correlation_not_propagated_notion` (:428) | D-04 | **FAILS** — `'adf2f0a7-…' != 'corr-orchestrator-xyz'` | Notion adapter regenerates per-call uuid; external correlation_id not accepted/propagated. Gap REAL. |
| 4 | `test_p9_d05_playwaywright_no_advisory` (:443) | D-05 | **FAILS** — `res.get("provenance", {}).get("advisory") is True` → `None is True` | `playwright_mcp_adapter.py` contains ZERO occurrences of `_mark_advisory`/`mark_capability_advisory` (grep evidence). `execute_action` returns the bare tool dict (:411-412). Gap REAL. |
| 5 | `test_p9_d06_obsidian_list_fallback_unmarked` (:461) | D-06 | **FAILS** — `assert 'obsidian_timestamp' in prov` where prov = `{'adapter': 'obsidian_adapter', 'advisory': True, 'authority': 'contextual', ...}` | Filesystem-fallback `_list_local` (obsidian_adapter.py:583-617) builds notes with `_make_provenance` only — carries partial markers (`advisory=True, authority=contextual`) but NOT the full C14 `_mark_advisory` treatment (`authority="advisory_only"`, `obsidian_timestamp`). Gap PARTIALLY open. |

Full-suite context run: `7 passed, 5 xfailed` in same file — the 5 xfail markers are all still genuinely failing as positive tests. **No silent XPASS exists; nothing was mislabeled as fixed-and-passing.**

## Verdicts

| Defect | Remediation-report claim | T2 source+behavior verdict |
|---|---|---|
| D-03 | FIXED | **PARTIALLY FIXED** — return-envelope marking present and correct (graphify_adapter.py:474/550/580/633); server-side persisted provenance still unmarked (the exact assertion in the D-03 xfail). Not convertible to positive. |
| D-04 | "Verified not applicable" | **RELABELING — GAP IS REAL.** Orchestrator correlation_id propagation does not exist in any adapter. Two xfails encode it; both fail positively. |
| D-05 | "Verified not applicable" | **RELABELING — GAP IS REAL.** No advisory marking anywhere in Playwright adapter results. |
| D-06 | "Verified not applicable" | **PARTIALLY OPEN** — fallback path has partial provenance but not full C14 `_mark_advisory`. |

### Classification per spec §12 (NO-GO conditions)
- None of these constitute authoritative-decision leakage, secret leakage, or spoofing (external input cannot SET these fields; the gap is that AI-OS's own advisory stamping is incomplete on some paths).
- D-04/D-05/D-06 = observability/provenance-consistency gaps → **P2 track items** (spec §12 P2/P3 list: "Non-critical observability gap"), provided graceful degradation is documented.
- The stale xfail labels themselves remain accurate as *gap encodings* (they correctly still fail); the remediation report's "not applicable" wording is contradicted by behavior. DISC-T2-02 stands.

### Conversion decision (per task brief §4)
- **No conversion performed.** All 5 underlying gaps demonstrably persist; converting any to a positive passing assertion would require either weakening the assertion or implementing M9-scope features — both prohibited. Tests remain honest xfail(strict=False) encodings of real gaps.
