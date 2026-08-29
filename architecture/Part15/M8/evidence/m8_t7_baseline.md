# M8-T7 — Baseline Checkpoint (fresh measurement, pre-modification)

**Terminal**: 2 · **Date**: 2026-08-26 · **Method**: live pytest collection

## Commands executed
```
python -m pytest --collect-only -q                      # total
python -m pytest tests/unit --collect-only -q           # unit
python -m pytest tests/integration --collect-only -q    # integration
python -m pytest tests/performance --collect-only -q    # performance
python -m pytest --collect-only -q -m xfail             # xfail inventory
```

## Measured results

| Bucket | Planning baseline | Fresh measurement | Δ |
|---|---|---|---|
| Total collected | 1546 | **1546** (1.51s) | none |
| unit | 1185 | **1185** (0.74s) | none |
| integration | 357 | **357** (0.81s) | none |
| performance | 4 | **4** (0.44s) | none |
| xfail-marked (collection) | 5 | **5** (`-m xfail` → "5/1546 tests collected") | none |
| skipped (runtime) | ≥10 (planning) | measured at P8 execution | — |
| collection errors | 0 implied | **0** | — |
| hangs during collection | n/a | **none** | — |

One non-fatal warning noted at collection:
`PytestCollectionWarning: cannot collect test class 'TestingEvidence' because it has a __init__ constructor (from: tests/integration/test_m8_t6_session_isolation.py)` — cosmetic, does not affect counts.

## Xfail inventory (marker-selected)
All 5 reside in `tests/integration/test_m8_t6_evidence_provenance.py`:
1. `test_p3_correlation_id_propagation_xfail` (D-04)
2. `test_p9_d03_graphify_write_unmarked` (D-03)
3. `test_p9_d04_correlation_not_propagated_notion` (D-04)
4. `test_p9_d05_playwright_no_advisory` (D-05)
5. `test_p9_d06_obsidian_list_fallback_unmarked` (D-06)

## Conclusion
Repository state matches the planning baseline exactly at collection level. Proceeding to positive re-run of the 5 xfails.
