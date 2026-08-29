# M8-T7 DEF-01 Remediation Report — Terminal 2

**Defect**: DEF-01 — MCP transport configuration crashes on stock boot (P1 production blocker)
**Terminal**: 2 (implementation/remediation)
**Date**: 2026-08-26
**Verdict issued**: NONE — Terminal 2 does NOT issue the final GO/NO-GO. Terminal 3 owns verification.
**M7 status**: COMPLETE/FROZEN — untouched (verified below).

---

## 1. Executive Summary

DEF-01 is fixed at its single production root cause. `MCPServerConfig` now normalizes raw
transport values to `MCPTransport` at construction time via `__post_init__` → `coerce_transport()`
(`src/aios/core/mcp_manager.py`). Every construction path — the JSON config loader
(`_load_configs()`), `add_server()`, and direct programmatic construction — flows through this one
boundary, so `"transport": "stdio"` from any stock `config/mcp/*.json` becomes
`MCPTransport.STDIO` before SecurityManager's gate (which accesses `.value`) ever sees it.

SecurityManager was NOT modified. The 5 existing xfails are untouched and verified genuine.
32 new focused regression tests were added. The full suite passes: **1570 passed, 3 skipped,
5 xfailed, exit code 0**. Stock-boot reproduction of the exact original crash condition was
performed pre-fix (4 failing probes) and re-run post-fix (all probes pass), including a real
stdio MCP subprocess connection through the full production chain.

## 2. Original DEF-01 Reproduction

Reproduction script preserved at `architecture/Part15/M8/evidence/m8_t7_def01_repro.py`.
Executed against the pre-fix working tree:

```
=== REPRO 1: stock JSON -> MCPServerConfig.transport type ===
       transport repr='stdio' type=str
[FAIL] R1 JSON 'stdio' -> MCPTransport.STDIO: got str
[FAIL] R1 .value access: AttributeError: 'str' object has no attribute 'value'

=== REPRO 2: security gate on string-transport vs enum-transport config ===
[FAIL] R2 gate on string-transport config: AttributeError: 'str' object has no attribute 'value'
[PASS] R2 gate on enum config: no crash

=== REPRO 3: full connect() through the production chain ===
[FAIL] R3 connect() via stock JSON: AttributeError: 'str' object has no attribute 'value' (DEF-01)

PRE-FIX REPRODUCTION RESULT: 4 failing probe(s)
```

This matches the authoritative QA finding exactly (`M8_T7_INDEPENDENT_QA_REPORT.md`;
`architecture/Part15/M8/evidence/m8_t7_p6_live_boot.md`). The reproduction used a real kernel
boot (`HermesKernel.start()` via the canonical EventBus/SecurityManager path) for the gate probes
— no fixture injection anywhere in the chain.

Post-fix, the identical script reports all probes PASS, including a real stdio connection to the
in-repo mock Graphify server launched from a stock-shaped JSON file:
`R3 connect() via stock JSON: connected=True, last_error=None`.

## 3. Root Cause

1. `mcp_manager.py` `_load_configs()` (pre-fix line 131) built configs with `MCPServerConfig(**data)`
   where `data["transport"]` is the plain JSON string `"stdio"`. The dataclass stored it verbatim;
   although `MCPTransport(str, Enum)` makes `'stdio' == MCPTransport.STDIO` true, the value is NOT
   an enum instance (`isinstance('stdio', MCPTransport) == False`).
2. `security_manager.py:665` (`validate_mcp_server_config`) constructs the deterministic scan id
   via `server_config.transport.value if server_config.transport else ''`. A plain `str` has no
   `.value` → **AttributeError: 'str' object has no attribute 'value'**.
3. `security_manager.py:1478` (`validate_mcp_server_before_connect`) does not catch it; the
   exception propagates out of `MCPManager.connect()` (`mcp_manager.py`, gate-before-connect call).
4. Blast radius: every MCP-backed integration on stock boot — Hermes, Graphify, Notion, Obsidian,
   Claude-Mem, Playwright — crashed at first `connect()` (measured in P6 live-boot evidence).

The defect class is *type erosion at the configuration boundary*: the enum existed and was correct;
the loading path never produced it.

### Why existing tests hid it (IND-6 mock-only trap)

`tests/integration/conftest.py` (`RealMCPManagerHarness._build_config`, lines ~229–237)
constructed typed `MCPServerConfig` objects with `MCPTransport.STDIO` directly and registered them
via `add_server()`, explicitly bypassing `_load_configs()`. Its docstring documented the dodge
verbatim ("avoids the JSON-loader path… without tripping the D-11 crash that the string-transport
JSON config path would hit"). Consequently no test exercised the broken path while every
"production-path" test passed.

## 4. Exact Production Files/Lines Changed

**One production file changed: `src/aios/core/mcp_manager.py`** (+51/−1 total in working tree; the
fix itself is 3 hunks — see note on the pre-existing D-12 hunk under §14):

| Change | Location (post-fix line numbers) | Purpose |
|---|---|---|
| `coerce_transport(value)` added | `src/aios/core/mcp_manager.py:41–74` | Single normalization function: enum passthrough / string coercion / deterministic `ValueError` |
| `MCPServerConfig.__post_init__` added | `src/aios/core/mcp_manager.py:91–96` | Applies coercion on EVERY construction path |
| `coerce_transport` exported | `src/aios/core/mcp_manager.py` (`__all__`) | Public boundary for callers/tests |

No other production file was modified. **SecurityManager was not modified** (constraint 7 honored):
the architectural contract holds — MCPManager owns MCP transport normalization, SecurityManager
keeps expecting enum semantics and keeps enforcing its validation rules unchanged.

## 5. Why the Previous D-11 Verification Was a False Positive

The M8-T6 remediation report marked D-11 ("MCP config transport loading") as VERIFIED citing only
the *declaration* `class MCPTransport(str, Enum)` at `mcp_manager.py:32`. That verifies the enum
type exists — not that the JSON loader produces instances of it. Because `MCPTransport(str, Enum)`
inherits from `str`, three masking effects compound:

1. **Equality masking**: `'stdio' == MCPTransport.STDIO` is `True`, so equality-based assertions
   pass on string values.
2. **Fixture bypass**: the integration harness injected enum-typed configs, never exercising
   `_load_configs()` (IND-6 trap, see §3).
3. **Verification-at-declaration**: checking "does the enum exist" instead of "does the loaded
   config carry the enum".

Runtime behavior — the only evidence class that could have caught DEF-01 — was never run against
the stock JSON path until M8-T7's live-boot checkpoint. Per Terminal 3's directive, D-11 must be
considered FAILED until independently re-verified against this remediation.

## 6. Remediation Design

**Chosen boundary**: `MCPServerConfig.__post_init__` → `coerce_transport()`.

Rationale:
- **Single chokepoint**: dataclass construction is the one place every config-producing path
  converges — `_load_configs()` (`MCPServerConfig(**data)`), `add_server(config)`,
  `_save_config()` round-trips, and direct programmatic use (adapters, harnesses). Coercing here
  means no caller can forget it, and future loaders inherit the guarantee.
- **Not SecurityManager**: hardening the gate to accept strings would have widened SecurityManager's
  accepted input domain to hide an upstream type violation — exactly what constraint 7 forbids.
  The gate's contract ("I receive normalized configs") stays strict.
- **Not `_load_configs()` alone**: fixing only the loader leaves `add_server()` and direct
  construction able to reintroduce string transports; the defect would survive half-fixed.

`coerce_transport()` semantics (constraint 4/5/6):
- Existing `MCPTransport` member → returned **unchanged** (same object identity).
- String matching any enum value exactly (`"stdio"`, `"http"`, `"sse"`, `"websocket"`) → coerced.
  All four handled generically via `MCPTransport(value)` — nothing hardcoded to stdio only.
- Any other string → `ValueError("Invalid MCP transport {v!r}; expected one of: stdio, http, sse,
  websocket")`. Case-sensitive by design: `"STDIO"`/`"Stdio"` are rejected (config format is
  lowercase across all 11 committed JSON files; accepting case variants silently would be
  inventing leniency not present in any contract).
- Non-string non-enum (`None`, numbers, lists, dicts) → `ValueError` naming the offending type.
- No transport is ever silently invented; failure is deterministic and immediate at load time
  rather than deferred to connect time.

`ValueError` was chosen over `ConfigurationError` because `aios.core.configuration_manager`
imports create a layering inversion risk and because `ValueError` is this module's established
transport-error semantics (`"STDIO transport requires command"`, `"Unsupported transport: …"`,
both `ValueError` in `mcp_manager.py`). Note: pre-fix, invalid transports failed *silently* (loader
caught everything with a warning); post-fix they fail loudly at construction.

## 7. Tests Added/Modified

**Added**: `tests/integration/test_m8_t7_def01_transport.py` — 32 tests, all passing. Coverage map
to the mandatory-test requirements:

| Req | Test(s) | What is proven |
|---|---|---|
| A | `TestStockConfigCoercion` (3 tests) | Stock-shaped JSON loads as `MCPTransport.STDIO`; ALL 11 committed `config/mcp/*.json` files coerce correctly; loader status entries carry the enum |
| B | `TestKernelBootPath` + `TestProductionChain` | `MCPManager` init over stock configs completes without the DEF-01 error; kernel-booted SecurityManager singleton reachable |
| C | `TestSecurityGateReceivesEnum` (2 tests) | Gate scan-id construction succeeds on JSON-loaded config (16-char deterministic scan_id); gate still REJECTS genuinely bad configs (empty stdio command) — fail-closed intact |
| D | `TestProductionChain::test_stock_json_config_connects_via_stdio_subprocess` | Real stdio connection to in-repo mock server from stock JSON: connected=True, tools discovered over protocol, status carries enum |
| E | `test_enum_members_pass_through_unchanged[stdio/http/sse/websocket]` + default-value test | All 4 enum members pass through with object identity preserved; omitted transport defaults to the enum |
| F | `test_invalid_*_fail_deterministically` (10 parametrized cases) + error-message test | Unknown/case-mismatched/non-string values raise `ValueError` deterministically, message lists valid values |
| Roundtrip | `test_json_loader_roundtrip_preserves_enum` | add_server→saved JSON→reload keeps enum semantics end-to-end |
| G | `TestNoFixtureWorkaroundReliance` (2 tests) | Module imports no harness symbols; documents the workaround's status |
| H | `TestOriginalDefectCondition` (2 tests) | Verbatim pre-fix crash expression from security_manager.py:665 now evaluates safely; full chain (load→gate→connect) survives where it previously raised |

Every test constructs its own `MCPManager` from raw JSON files via the real loading path — none
uses `RealMCPManagerHarness` or injects pre-built configs (constraint G).

**Modified**: no existing tests. No fixtures changed. The historical conftest workaround docstring
was left in place deliberately (constraint 8: do not rewrite unrelated historical tests) — it is
now documentation of a closed defect; `tests/integration/conftest.py` code itself was NOT modified.

**Evidence artifact**: `architecture/Part15/M8/evidence/m8_t7_def01_repro.py` (QA-only repro
script, outside the test suite).

## 8. Stock-Boot Verification

The production chain was verified WITHOUT substituting fixtures for the configuration-loading
portion:

```
stock config JSON ("transport": "stdio")
    ↓ MCPManager._load_configs()          ← real repo loader, real temp config dir
    ↓ MCPServerConfig.__post_init__        ← NEW coercion boundary
    ↓ MCPTransport.STDIO                   ← isinstance verified, identity-checked
    ↓ get_security_manager().validate_mcp_server_before_connect()
    ↓ MCPServerSecurityGate.validate_mcp_server_config()   ← .value access OK (scan_id derived)
    ↓ MCPManager.connect() → _connect_stdio()
    ↓ asyncio.create_subprocess_exec(python -m aios.adapters.mock_graphify_server)
    ↓ MCP initialize handshake → tools/list discovery
    → connected=True, tools discovered, MCP_SERVER_CONNECTED semantics reached
```

Kernel-level boot also re-verified through the existing suite:
`test_kernel_lifecycle_e2e.py` + `test_integration.py` + `test_configuration_manager_phase.py`:
**41 passed** (kernel boots, all 9 managers construct, MCPManager assigned at boot per D-01).

## 9. MCP Production-Style Path Verification

Real subprocess connections through the fixed chain (not mocks at the configuration layer):

- New regression `TestProductionChain` and `TestOriginalDefectCondition`: two independent
  stock-JSON→connect runs against `mock_graphify_server`, both `connected=True` with tools listed.
- Evidence repro R3: same result standalone (`connected=True, last_error=None`).
- M6/T6 production-path suites still green through the REAL manager:
  `test_m8_t6_production_paths.py` + `test_m8_t6_cross_adapter_matrix.py`: **21 passed**
  (~6 min, subprocess-heavy). These continue using their own typed configs (unmodified), which is
  acceptable: they are no longer *masking* anything, because the JSON path is now independently
  covered by the new regression module.

## 10. Full Regression Results

Environment: Windows 11, repo venv Python 3, pytest 8.x, asyncio_mode=auto.
Full suite ran ONCE cleanly (no rerun needed — not flaky in this session):

| Suite | Result | Exit code |
|---|---|---|
| **FULL: unit + integration + performance** | **collected 1578 · passed 1570 · failed 0 · skipped 3 · xfailed 5 · xpassed 0** · 717.61 s (11:57) | **0** |
| DEF-01 focused regression (new file) | 32 passed · 1.61 s | 0 |
| MCPManager/gate/transport units (`-k "mcp or gate or transport or def01"`) | 138 passed | 0 |
| Full M5 gate suite (SecurityManager+MCP integration) | 51 passed | 0 |
| Kernel lifecycle E2E + integration + config phase | 41 passed | 0 |
| M8-T1..T4 adapters (graphify/notion/obsidian/claude_mem/playwright/hermes_acp) | 86 passed, 2 skipped | 0 |
| M8-T5 (dynamic loading + security) | 22 passed | 0 |
| M8-T6 batch 1 (authority_boundary, capability_registry, degraded_mode, e2e_workflows) | 31 passed · 4:47 | 0 |
| M8-T6 batch 2 (failure_injection, recovery, security_integration, session_isolation) | 63 passed | 0 |
| M8-T6 production_paths + cross_adapter_matrix | 21 passed · 6:20 | 0 |
| M8-T6 evidence_provenance (holds the 5 xfails) | 8 passed, **5 xfailed** | 0 |
| M7 + M6 council regression (closed_loop, council_synthesis, multi_perspective, isolation, security, seeded_defects, evidence_integrity) | 83 passed | 0 |
| Agency adapters + UserSimulationAgent + logger perf (files touched in working tree) | 33 passed, 1 skipped | 0 |

Skips (all pre-existing environment gates, unrelated to this fix):
`PLAYWRIGHT_E2E_TEST not set`, `HERMES_ACP_TEST not set`, `psutil not installed` (known env gap
from baseline QA).

Baseline comparison: prior recorded full-suite state was 1,416 passed / 2 skipped (M8-T5 close-out);
this run shows 1,570 passed / 3 skipped / 5 xfailed = +154 passed (≈ +101 M8-T6 suite tests landed
since then + 32 new DEF-01 tests + others already in tree), consistent with intervening commits —
zero failures introduced.

## 11. M7 Freeze Verification

- Zero modifications to any M7 source or test file. Working-tree changes touching M7-adjacent files
  (`agency_adapters`, `user_simulation_agent`, hermes bridge/mock) pre-date this session (present in
  git status snapshot before work began) and were NOT touched by this remediation; their suites pass.
- M7/M6 regression: **83 passed, 0 failed** (suite list in §10).
- No EventTypes added; no agency internals modified; no authority boundaries altered; provenance
  semantics unchanged (only additive config-normalization inside `MCPServerConfig`).

## 12. XFAIL Verification

The 5 known xfails (`test_m8_t6_evidence_provenance.py`: D-03 graphify-write-unmarked,
D-04 correlation-not-propagated ×2, D-05 playwright-no-advisory, D-06 obsidian-fallback-unmarked):

1. Standard run: **8 passed, 5 xfailed** — none converted, none removed, markers untouched.
2. `--runxfail` verification: **5 failed, 8 passed** — every xfail is a GENUINE failure when the
   marker is disabled, proving none was accidentally fixed into xpass territory by this change
   (none of them touch transport typing; all concern C14 advisory provenance/correlation gaps).

Constraint honored: xfails neither weakened nor repaired as a side effect.

## 13. Security/Authority Impact

- **Fail-closed preserved**: coercion happens strictly BEFORE the gate; the gate's decision logic,
  allowlists, violation emission, and scan-id derivation are byte-for-byte unchanged. A coerced
  config still fails the gate for real reasons (verified: empty-command stdio config rejected).
- **No new trust surface**: strings cannot smuggle past the gate — they either match an enum value
  exactly or the process refuses to construct the config at all.
- **Authority boundaries intact**: MCPManager owns transport normalization (its own config domain);
  SecurityManager remains final connection authority (C18 gate-before-connect unchanged);
  SecurityManager input contract actually TIGHTENED de facto (can no longer receive un-coerced
  strings from the loader path).
- **Attack surface delta**: invalid transport values now fail at config-load time with explicit
  errors instead of surfacing later as confusing AttributeErrors — strictly better fail-fast
  posture. No new event types, no new capabilities, no provenance changes.

## 14. Backward Compatibility

- **Stock configs**: all 11 committed `config/mcp/*.json` files use lowercase valid values → all
  verified loading correctly (`test_all_repo_stock_configs_load_with_enum_transports`).
- **Programmatic enum users** (integration harness, adapters, M5 tests): unchanged behavior —
  enums pass through with identity preserved.
- **String-passing callers**: previously "worked" by accident until the gate crashed; now work
  correctly (coerced). This is the bug fix itself.
- **Case-sensitivity note**: a hypothetical external caller passing `"STDIO"` previously crashed
  with AttributeError at the gate; now crashes earlier with ValueError. Both are failures; the new
  failure is clearer and earlier. No working input became invalid.
- **Diff hygiene disclosure**: `git diff` on `mcp_manager.py` shows +51/−1, but 3 hunks of that
  (the `launch_env` D-12 subprocess-env hardening in `_connect_stdio`) PRE-DATE this session —
  they were already in the working tree (visible in the session-start git status) and belong to
  M8-T6 remediation, not this fix. Terminal 2's DEF-01 footprint is exactly: `coerce_transport()`
  (lines 41–74), `__post_init__` (lines 91–96), `__all__` export. Nothing else in src/ was touched.

## 15. Files Changed

**Production (root-cause fix):**
- `src/aios/core/mcp_manager.py` — `coerce_transport()` + `MCPServerConfig.__post_init__` +
  `__all__` export (see §4/§14)

**Tests added:**
- `tests/integration/test_m8_t7_def01_transport.py` — 32 focused regression tests

**Evidence artifacts (non-suite):**
- `architecture/Part15/M8/evidence/m8_t7_def01_repro.py` — pre/post-fix reproduction script

**Report:**
- `M8_T7_DEF01_REMEDIATION_REPORT.md` (this document)

**Explicitly NOT modified:** `src/aios/core/security_manager.py`, `tests/integration/conftest.py`,
any M7 file, any M8-T1..T6 adapter, any xfail marker, `config/mcp/*.json`.

## 16. Remaining Known Issues

None blocking DEF-01 closure. Carried-forward items owned elsewhere (NOT introduced by this fix):

1. **D-11 formal re-verification** — Terminal 3 must independently confirm D-11 (M8-T6 register)
   as RESOLVED based on this remediation; per directive it stayed FAILED until that re-verification.
2. **The 5 genuine xfails** (C14 advisory-provenance gaps D-03/D-04/D-05/D-06) remain open gaps by
   design — untouched per constraint.
3. **Pre-existing warnings** (not defects): `utcnow()` deprecations across several modules;
   unawaited `EventBus.publish` coroutine in SecurityManager's general-event emit path
   (`security_manager.py:1498`, observed as RuntimeWarning in gate-failure tests). Both pre-date
   this session.
4. **psutil env gap** — one perf test skip due to missing module in this environment.
5. Root-convenience scripts (`reproduce_def01*.py`, `test_def01_integration.py`) are stale
   diagnostic artifacts from earlier triage; left untouched (out of scope).

## 17. Terminal 3 Handoff Instructions

Independent verification steps, in order:

1. **Reproduce the ORIGINAL defect condition independently** (do not trust §2): check out/stash the
   fix (revert `MCPServerConfig.__post_init__` + `coerce_transport` in
   `src/aios/core/mcp_manager.py` only), run
   `python architecture/Part15/M8/evidence/m8_t7_def01_repro.py` → expect the 4-probe failure
   output of §2 including `AttributeError: 'str' object has no attribute 'value'`.
2. **Restore the fix**, re-run the same script → expect all probes PASS including
   `R3 connect() via stock JSON: connected=True`.
3. **Verify the stock path without fixtures**: run
   `pytest tests/integration/test_m8_t7_def01_transport.py -v` → 32 passed. Confirm the module
   contains zero references to `RealMCPManagerHarness` usage (requirement G).
4. **Confirm SecurityManager untouched**: `git diff src/aios/core/security_manager.py` relative to
   the pre-remediation working tree → expect NO diff attributable to Terminal 2 (file was already
   dirty pre-session; compare against the session-start snapshot, not HEAD).
5. **XFAIL integrity**: run
   `pytest tests/integration/test_m8_t6_evidence_provenance.py -q` → expect `8 passed, 5 xfailed`;
   then with `--runxfail` → expect `5 failed, 8 passed`.
6. **Regression**: full suite `pytest tests/unit tests/integration tests/performance -q` → expect
   ≈1570 passed / 3 skipped / 5 xfailed / exit 0 (allow minor count drift if unrelated tree state
   changed since 2026-08-26).
7. **Scope audit**: `git diff src/aios/core/mcp_manager.py` → confirm only the 3 hunks described in
   §14 plus the pre-existing D-12 `launch_env` hunk; confirm no other src/ file changed by
   Terminal 2 in this session.

Decision authority: Terminal 3 issues GO/NO-GO. Terminal 2 claims only: DEF-01 root cause fixed,
regressions green, constraints honored as itemized above.

## 18. Terminal 2 Final Statement

**Terminal 2 does NOT issue the final GO verdict.** This report provides implementation evidence
and honest regression data only. Terminal 3 owns independent reproduction, stock-path verification,
and the final GO/NO-GO disposition for M8-T7.

---

*Report generated by Terminal 2 (implementation/remediation). All counts and outputs quoted
verbatim from executed commands on 2026-08-26.*
