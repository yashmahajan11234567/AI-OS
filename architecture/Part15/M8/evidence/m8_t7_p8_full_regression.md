# M8-T7 — P8 Checkpoint: Full Regression + Performance + Flaky-Test Protocol

**Terminal**: 2 · **Date**: 2026-08-26

## Full suite (P8)

Command: `python -m pytest -q -p no:cacheprovider` (backgrounded; run to completion)
Result: **1539 passed, 2 skipped, 5 xfailed, 2713 warnings in 719.86s (0:11:59), exit code 0**

- No hang. Runtime consistent with planning's F-0.4 (~12–13 min).
- Counts identical to the planning-phase baseline (1539/2/5) — zero drift.
- Teardown-only warnings observed: `PytestUnraisableExceptionWarning … ValueError("I/O operation on closed pipe")` from subprocess-based suites (windows_utils.fileno). Non-fatal, occurs at interpreter teardown after final results are tallied. Logged as cosmetic (P3-track observation).

## Performance tests

Command: `python -m pytest tests/performance -q`
Result: **4 passed in 2.21s**.

## Flaky-test protocol (spec §8) — structured-logger correlation test

Target: the historically flaky correlation behavior (`test_structured_logger_phase.py::test_correlation_propagation_end_to_end`, D-09's named test).

| Run | Command | Result |
|---|---|---|
| Isolation | single-test invocation | **passed** (12 passed incl. class context, 2.08s) |
| Suite repeat ×3 | full file, back-to-back | **11 passed / 11 passed / 11 passed** |
| Perf suite ×6 | tests/performance, repeated | **4 passed every time** |

Verdict: **not flaky in this environment today** — 10 consecutive green runs across isolation and repeat patterns. D-09's concern does not reproduce on current source; no quarantine required. Classified per spec §12 flaky rule as acceptable (pre-existing, root cause not M8-related, currently stable).

## Skip inventory reconciliation (runtime)

- 2 skipped = `test_m8_hermes_acp.py` + `test_m8_playwright.py` environment-gated skips (31 passed + 2 skipped in P3), matching planning's "≥10 skipped markers" being conditional runtime skips that mostly execute.
- 5 xfailed = D-03..D-06 encodings (see xfail revalidation checkpoint).
