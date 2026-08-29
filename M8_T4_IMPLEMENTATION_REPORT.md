# M8-T4 External Knowledge / Planning Integration — Implementation Report

**Date:** 2026-08-25
**Status:** ✅ IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT QA
**Spec:** `architecture/Part15/M8/M8-T4-IMPLEMENTATION-SPEC.md`

---

## Executive Summary

M8-T4 successfully integrates three external supporting systems into AI-OS:

- **Notion** — planning / project-tracking (UNTRUSTED contextual)
- **Obsidian** — persistent knowledge vault (TRUSTED_CONTEXTUAL, dual-path)
- **Claude-Mem** — contextual memory retrieval (UNTRUSTED contextual)

All three are integrated as **non-authoritative advisory sources** per constraint C14: every retrieved datum carries full provenance with `authority=contextual`, `advisory=True`, and a per-system `trust_level`. No adapter touches SecurityManager, StateManager, WorkflowManager, Council, or Judge.

The implementation adds **75 unit tests + 38 integration tests = 113 new tests**, bringing the total suite to **1,315 passing tests (2 skipped)**. Full regression is green; one unrelated flaky test (`test_correlation_propagation_end_to_end`, structured-logger phase) failed once under full-suite ordering and passes consistently in isolation and on suite re-run.

---

## Scope Delivered

### NEW Files (12)

| File | Purpose | Lines |
|------|---------|-------|
| `src/aios/adapters/notion_adapter.py` | Notion MCP adapter | 631 |
| `src/aios/adapters/obsidian_adapter.py` | Obsidian dual-path adapter (MCP primary, filesystem fallback) | 950 |
| `src/aios/adapters/claude_mem_adapter.py` | Claude-Mem memory retrieval adapter | 539 |
| `src/aios/adapters/mock_notion_server.py` | Mock Notion MCP server (in-process) | 318 |
| `src/aios/adapters/mock_obsidian_server.py` | Mock Obsidian MCP server (in-process) | 264 |
| `src/aios/adapters/mock_claude_mem_server.py` | Mock Claude-Mem MCP server (in-process) | 245 |
| `config/mcp/notion_mcp.json` | Notion MCP server config | 15 |
| `config/mcp/obsidian_mcp.json` | Obsidian MCP server config | 15 |
| `config/mcp/claude_mem_mcp.json` | Claude-Mem MCP server config | 15 |
| `tests/unit/test_notion_adapter.py` | 24 unit tests | 461 |
| `tests/unit/test_obsidian_adapter.py` | 29 unit tests | 551 |
| `tests/unit/test_claude_mem_adapter.py` | 22 unit tests | 461 |

### NEW Integration Test Files (3)

| File | Tests | Lines |
|------|-------|-------|
| `tests/integration/test_m8_notion.py` | 13 | 328 |
| `tests/integration/test_m8_obsidian.py` | 12 | 340 |
| `tests/integration/test_m8_claude_mem.py` | 13 | 345 |

### MODIFIED Files (2)

| File | Changes |
|------|---------|
| `config/defaults.yaml` | Added `notion:`, `obsidian:`, `claude_mem:` sections (enabled, timeout_seconds, auto_reconnect, obsidian.vault_path) |
| `src/aios/core/kernel.py` | `_init_notion()` (kernel.py:965), `_init_obsidian()` (kernel.py:1012), `_init_claude_mem()` (kernel.py:1066); called from `start()` at kernel.py:433-435 after `_init_playwright()` |

**Total new code:** ~5,433 lines

---

## Architecture Compliance

### C14 Advisory Boundary (verified by test)

Every result from all three adapters carries complete provenance:

```python
{
    "source": "notion" | "obsidian" | "claude_mem",
    "adapter": "<name>_adapter",
    "operation": "<operation_name>",
    "correlation_id": "<uuid>",
    "execution_id": ..., "task_id": ...,
    "timestamp": "<utcnow isoformat>",
    "request_id": "<uuid>",
    "version": <monotonic int>,
    "authority": "contextual",
    "advisory": True,
    "trust_level": "untrusted"          # Notion, Claude-Mem
                  | "trusted_contextual"  # Obsidian (local filesystem)
}
```

Obsidian additionally records `retrieval_path` (`mcp` or `filesystem_fallback`) in every result's metrics and provenance. C14 constants cannot be overridden by externally-supplied data — the marking pass re-applies them last.

### Trust Levels

| System | trust_level | Rationale |
|--------|-------------|-----------|
| Notion | `untrusted` | Remote SaaS; content authored outside AI-OS |
| Obsidian | `trusted_contextual` | Local filesystem vault, but markdown may contain arbitrary text |
| Claude-Mem | `untrusted` | Memory entries can carry injected content |

### Authority Boundaries (MUST-NOT-ACCESS)

No M8-T4 adapter imports or calls: SecurityManager, StateManager, WorkflowManager, TestingCouncil, FinalJudge. Adapters receive only `MCPManager` and configuration.

### Security Validation

Shared pattern across all three adapters (constants defined per-file):

- `SENSITIVE_PROPERTY_KEYS`: password/token/secret/api_key/apikey/authorization/credential/private_key/access_token — rejected before any external call
- `SECRET_VALUE_PATTERNS`: API-key, Bearer-token, password-assignment regexes
- Size limits: 10 KB content (Notion/Obsidian), 1 KB query + 10 KB entry (Claude-Mem)
- Claude-Mem logs potential prompt-injection patterns without rejecting (content filtering happens downstream); oversized retrieved entries are dropped individually rather than failing the batch
- Obsidian `_validate_path()`: resolves against vault root and rejects traversal via `is_relative_to`; blocks `.obsidian` internal directory access

### Failure Semantics

Operations degrade gracefully to `ExecutionResult(status=ERROR)` with typed findings — no exceptions escape to callers for remote failures (validation errors still raise, since they indicate caller bugs). Claude-Mem drops individual oversized entries with a warning instead of failing retrieval. Obsidian falls back MCP → filesystem transparently mid-operation.

---

## Dual-Path Routing (Obsidian)

```
search_notes/get_note/list_notes/read_note
        │
        ├─ MCP connected? ──► call mock/real Obsidian MCP server ──► mark advisory
        │        │ failure (Unavailable/Timeout/Malformed)
        │        ▼
        └─ vault_path exists? ──► direct filesystem read ──► mark advisory
                 │ missing
                 ▼
              ERROR result ("unavailable" finding)
```

Filesystem path includes frontmatter parsing (YAML safe_load), tag extraction (frontmatter list/string + body hashtags), and per-note file-stat timestamps.

---

## Kernel Wiring

Each init method follows the established M8 pattern (Graphify/Playwright):

1. Guard on CapabilityManager availability (test kernels skip gracefully)
2. Construct adapter with injected `self._mcp_manager`
3. Register capability:

| capability_id | facade | tags |
|---------------|--------|------|
| `notion_planning` | planning | planning, notion, project-tracking, tasks |
| `obsidian_knowledge` | knowledge | knowledge, obsidian documentation, persistent |
| `claude_mem_context` | memory | memory, claude-mem, contextual, retrieval |

Each registration includes `security_context` with allowed operations, sensitive keys, and max content size.

---

## Test Results

### Unit Tests (75)

| Suite | Tests | Coverage |
|-------|-------|----------|
| `test_notion_adapter.py` | 24 | Creation(3), connection(3), page ops(6), database ops(2), provenance(2), advisory(2), security(3), failures(2), dispatch(1) |
| `test_obsidian_adapter.py` | 29 | Creation(3), MCP connection(3), filesystem fallback(3), note ops(7), dual-path(3), provenance(3), advisory(2), security(4+2 direct validators), frontmatter(2) |
| `test_claude_mem_adapter.py` | 22 | Creation(3), connection(3), retrieval(6), provenance(2), advisory(2), validation/security(4), failures(2) |

### Integration Tests (38)

Pattern: in-process mock MCP servers behind a thin `MockMCPManager` (same as M8-T3 Graphify).

| Suite | Tests | Key scenarios |
|-------|-------|---------------|
| `test_m8_notion.py` | 13 | Initialize/tools-list handshake; full page lifecycle (create→get→search→update); missing-page graceful; empty search; query_database; C14 advisory on retrieval; provenance completeness; secret-leak scan; sensitive-key rejection end-to-end; oversized rejection; server-failure → ERROR result; disconnected behavior |
| `test_m8_obsidian.py` | 12 | Initialize/tools handshake; dual-path routing (mcp priority, fallback-only, mid-session degradation); full flow over MCP; missing note; directory scoping; C14 both paths; provenance completeness; path-traversal blocked; `.obsidian` protection |
| `test_m8_claude_mem.py` | 13 | Initialize/tools handshake; full retrieval flow (context/recent/by-tag with time windows); empty store; tag filtering; limit capping; C14 untrusted marking; provenance completeness; secret-leak scan; injection-tolerant retrieval; query validation; server-failure → ERROR result; disconnected behavior |

### Full Regression

```
tests/ -q : 1315 passed, 2 skipped (44.63s first run, 42.87s confirmation run)
```

One transient failure (`tests/integration/test_structured_logger_phase.py::test_correlation_propagation_end_to_end`) occurred only in the first full-suite run — order-dependent sink/context interference, unrelated to M8-T4 (no shared code paths). It passes in isolation, in its module, and in the confirmation full-suite run.

---

## Spec Deviations & Notes

1. **Test count: 113 delivered vs ~94 planned.** Deliberate over-delivery following M8-T3 practice; spec §907 explicitly marks 94 as a conservative estimate.
2. **`tests/unit/test_agency_adapters.py` additions (~7 tests) not added.** The spec lists them as minimal instantiation checks; equivalent coverage exists in the dedicated per-adapter suites. Can be added if QA requires exact spec conformance.
3. **Provenance hardening beyond spec:** initial `_mark_advisory` implementations merged only the C14 markers onto externally-sourced dicts, leaving results without `adapter`/`operation`/`correlation_id`. Fixed during TDD: `_mark_advisory` now seeds a full provenance base, lets caller data fill optional fields, then re-applies C14 constants so external data can never override authority markings.
4. **Graceful-degradation hardening beyond spec:** Notion/Claude-Mem operations initially propagated adapter exceptions; now wrapped to return `ERROR` ExecutionResults with typed findings, matching the Obsidian pattern and the spec's resilience requirement.
5. **Search-title casing fix:** `_search_local` was lowercasing stored titles before returning them; fixed so matching uses lowercased copies while returned notes preserve original casing.
6. **Deprecation warnings:** adapters use `datetime.utcnow()` consistent with the existing codebase baseline (kernel.py, workflow.py, resource_manager.py share this). Migration to `datetime.UTC` is a codebase-wide cleanup, out of M8-T4 scope.

---

## Acceptance Criteria Status

| Criterion (spec §19) | Status |
|---------------------|--------|
| Three adapters implement BaseExecutionAdapter | ✅ |
| All results marked advisory per C14 with full provenance | ✅ (tested per-path) |
| Trust levels correct per system | ✅ untrusted ×2, trusted_contextual ×1 |
| No access to authoritative core managers | ✅ (imports limited to base + mcp) |
| Sensitive keys / secrets / sizes rejected pre-call | ✅ (unit + integration) |
| Obsidian dual-path with traversal + `.obsidian` protection | ✅ |
| Graceful degradation to ERROR results | ✅ (integration) |
| Kernel wiring + capability registration ×3 | ✅ |
| Mock servers implement MCP initialize/tools/list/tools/call | ✅ |
| Full regression green | ✅ 1315 passed, 2 skipped |
| New test count ≥ plan | ✅ 113 vs ~94 |

---

## Handoff to Independent QA

Suggested QA focus areas:

1. **C14 override resistance** — verify externally-supplied `provenance` dicts in mock-server payloads cannot flip `advisory`/`authority`/`trust_level`.
2. **Dual-path consistency** — same vault served over MCP and filesystem should yield equivalent shapes.
3. **Claude-Mem injection posture** — confirm log-only detection matches spec intent (no silent rejection).
4. **Kernel wiring isolation** — kernel start with MCP servers absent must not fail (guards verified).
5. **Flaky-test note** — `test_correlation_propagation_end_to_end` shows order sensitivity independent of this task; recommend separate investigation.
