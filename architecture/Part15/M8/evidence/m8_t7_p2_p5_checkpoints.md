# M8-T7 — P2–P5 Checkpoints: Staged Suite Results + Security/Authority Spot-Checks

**Terminal**: 2 · **Date**: 2026-08-26

## P2 — Focused unit tests
| Command | Result |
|---|---|
| `pytest tests/unit -k "adapter or capability" -q` | **327 passed** (3.18s) |
| `pytest tests/unit -q` (full unit suite) | **1185 passed** (22.34s, exit 0) |

## P3 — Cross-integration (T1..T4 + GI flows)
| Command | Result | Wall |
|---|---|---|
| `pytest tests/integration/test_m8_hermes_acp.py test_m8_playwright.py -q` | **31 passed, 2 skipped** | 0.54s |
| `pytest test_m8_graphify.py test_m8_notion.py test_m8_obsidian.py test_m8_claude_mem.py -q` | **55 passed** | 1.23s |
| `pytest test_m8_t6_cross_adapter_matrix.py -q` (GI matrix incl. subprocess paths) | **11 passed** | 32.64s |
| `pytest test_m8_t6_e2e_workflows.py -q` (golden e2e chains GI-1..5) | **6 passed** | 32.50s |
| `pytest test_m8_t6_evidence_provenance.py -q` | 8 passed, 5 xfailed (see xfail revalidation checkpoint) | 0.69s |

## P4 — Failure/recovery (FR series)
| Command | Result |
|---|---|
| `pytest test_m8_t6_failure_injection.py -q` (F-1..F-16 injections) | **18 passed** (0.65s) |
| `pytest test_m8_t6_recovery.py -q` (FR-14 recovery) | **5 passed** (0.38s) |
| `pytest test_m8_t6_degraded_mode.py -q` (XA-7 graceful degradation) | **7 passed** (0.46s) |

Independent FR spot-checks (runtime):
- Graphify unconnected → `GraphifyUnavailableError` raised (typed) ✅
- Notion unconnected → returns `ExecutionStatus.ERROR` result w/ typed finding "Not connected to Notion server" — deliberate API-boundary conversion (`search_pages` catches `NotionError` hierarchy at :430-433); `NotionUnavailableError(NotionError)` still exists and fires inside `_call_tool:389`. Same pattern for Claude-Mem. **Design difference vs Graphify's raise-through is documented, both honest; no defect.**
- `GraphifyTimeoutError`, `PlaywrightActionError`, malformed-response types all present (FR-3/4/5 types).

## P5 — Security/authority
| Command | Result |
|---|---|
| `pytest test_m8_t6_security_integration.py -q` (SEC integration) | **33 passed** (0.71s) |
| `pytest test_m8_t6_authority_boundary.py -q` (authority boundaries) | **9 passed** (64.58s) |
| `pytest test_m8_t6_capability_registry.py -q` (CM-* registry rules) | **9 passed** (192.02s) |
| `pytest test_m8_t5_security.py -q` (manifest security) | **14 passed** (1.37s) |

Independent SEC spot-checks (runtime probes):
- **SEC-4** sensitive keys: `api_key/secret/token/password/private_key/credential/authorization/apikey/access_token` rejected by Graphify `_validate_properties` ✅
- **SEC-1** secret patterns: `password=hunter2` in property value rejected ✅
- **SEC-5** payload limit: >10240-byte property value rejected ✅
- **SEC-1b** Playwright `_scrub_env()`: ANTHROPIC_AUTH_TOKEN / CLAUDE_CODE_MESSAGING_TOKEN values replaced with `***REDACTED***`; zero sensitive-pattern keys retain real values ✅
- **SEC-6** Playwright file:// blocked (PlaywrightSessionNotFoundError before nav; explicit `file:// protocol is blocked` check at playwright_mcp_adapter.py:397-400) ✅
- **SEC-8** Obsidian path traversal: `../outside.md`, `../../windows`, `/etc`, `C:/Windows` all detected ("Path traversal attempt detected") → ERROR results, no content returned ✅

Architecture checks:
- **XA-1** circular imports: all 17 core+adapter+service modules import cleanly ✅
- **XA-2** no capability-specific kernel branching (`capability_id ==` scan: none) ✅
- **XA-6** config correctness: 5 capability manifests load with the kernel allowlist (claude_mem_context, graphify_context, notion_planning, obsidian_knowledge, playwright_browser — all enabled, trust=trusted_contextual); without allowlist the loader correctly skips all 5 (allowlist enforcement works) ✅
- **XA-8/XA-13** bare-except scan across adapters: none ✅

— P2–P5 complete.
