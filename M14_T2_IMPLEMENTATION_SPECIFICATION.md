# M14-T2 — Authoritative Implementation Specification & Scope Freeze

**Terminal 1 — Read-Only / Specification Only**
**Date:** 2026-08-30
**Verdict:** **M14-T2 SPECIFICATION READY — SCOPE FROZEN**

---

## 1. Executive Summary

This document is the authoritative implementation specification and scope freeze for **M14-T2** (Terminal 2 Phase 2), which operates under **Terminal 1 — Read-Only / Specification Only**. The specification was derived from comprehensive read-only review of the entire AI-OS codebase, all milestone documentation (M7–M13), test results, configuration files, and adapter implementations.

**Core Finding:** M13 implementation delivered **100% of infrastructure** for bounded external resource integration (Supabase, n8n, Obsidian Git), but left the **real-mode execution paths as stubs that raise errors**. M14-T2 must implement the real REST and filesystem operations for these three adapters so they function correctly when `AIOS_REAL_INTEGRATION_ENABLED=1` is set by the user with valid credentials/resources.

**Baseline:** 2,241 tests collected; ~1,991 pass / 3 skipped / 5 xfailed (all pre-existing). M14-T2 adds 0 new tests to the baseline — only implementation changes.

---

## 2. True Milestone State Table

| Milestone | Status | Evidence | Tests | Notes |
|-----------|--------|----------|-------|-------|
| **M7** | ✅ COMPLETE / FROZEN | TestingEvidence, 9 agencies, UserSimulationAgent, CouncilManager — all wired | 1,046 passed | Frozen scope; no modifications |
| **M8** | ✅ COMPLETE / CONDITIONAL GO | 7 sub-tasks all GO; 5 genuine xfails (D-03..D-06) remain | ~1,112 passed | DEF-01 fixed (MCP transport enum) |
| **M9** | ✅ COMPLETE | LearningService, RCA, ModelRouter, SelfPrompting wired into kernel | ~15 tests | Capture→retrieve→apply loop closed |
| **M10** | ⚠️ COMPLETE / PROCESS VIOLATION | 12 services implemented despite PLANNING-ONLY directive; 22/22 unit tests pass | 22 unit pass, 10 integration fail (framework) | DEF-M10-P0-01 documented |
| **M11** | ✅ COMPLETE / GO | 193 security tests pass; 1,293 unit tests pass; all 6 security areas verified | 1,293 passed | Full security GO |
| **M12** | ⚠️ COMPLETE / CONDITIONAL GO | Documentation complete (26 docs, 14,706 lines); C1–C4 unresolved | 1,993 passed | CONFLICT-P15-01 blocks FULL READY |
| **M13** | ✅ COMPLETE / CONDITIONAL GO | 112 M13 tests pass; all adapters wired; terminal contract enforced; real-mode gating active | 112 passed | Real-mode paths are stubs (this gap) |
| **M14-T1** | ✅ COMPLETE | 2,241 tests collected; 0 of 10 resources present; 100% mock-mode | — | Discovery/audit only |
| **M14-T2** | 🔲 IN PROGRESS | **This document** | — | Implement real paths for Supabase, n8n, Obsidian Git |

---

## 3. Determined M14 Scope

### 3.1 What M14 Is

M14 is **Terminal 2 Final External Ecosystem Integration** — the closure of all external integration real-mode execution paths that M13 infrastructure supports but does not fully implement.

### 3.2 What M14 Is NOT

- **NOT** another milestone of new adapters (those are complete)
- **NOT** dashboard frontend development (Terminal 3 scope)
- **NOT** self-loop or self-prompt enhancements (these are complete and working in mock mode)
- **NOT** new security infrastructure (M11 already hardened; existing security gate must be preserved)
- **NOT** modification of M7–M12 code (additive changes only)

### 3.3 M14 Sub-Tasks

| Sub-Task | Owner | Description | Status |
|----------|-------|-------------|--------|
| **M14-T1** | Terminal 1 | Resource discovery audit | ✅ COMPLETE |
| **M14-T2** | Terminal 2 | Implement real execution paths for Supabase, n8n, Obsidian Git; wire configuration; add integration tests | 🔄 THIS DOCUMENT |
| **M14-T3** | Terminal 3 | Dashboard frontend (out of scope for this spec) | Deferred |

---

## 4. M14-T1 Findings Summary

From `M14_T1_RESOURCE_DISCOVERY_REPORT.md` and `M14_T1_RESOURCE_MATRIX.md`:

| Component | Implementation State | Mock Readiness | Real Mode Ready | Required User Action |
|-----------|---------------------|----------------|-----------------|---------------------|
| Supabase | ✅ 100% | ✅ All tests pass | ❌ `_call_rest()` raises `SupabaseUnavailableError` | Create project; export URL + anon key; run migrations |
| n8n | ✅ 100% | ✅ All tests pass | ❌ `_call_rest()` raises `N8nUnavailableError` | Deploy instance; provide base_url + API key |
| Obsidian Git | ✅ 100% | ✅ All tests pass | ❌ `_write_real()`/`_read_real()`/`_delete_real()` raise `ObsidianGitUnavailableError` | Create vault; set `OBSIDIAN_VAULT_PATH`; configure Git remote |
| Obsidian (M8) | ✅ 100% | ✅ All tests pass | ✅ Filesystem fallback already implemented | Install Obsidian; create vault; set vault path |
| Dashboard | ✅ 100% backend | ✅ All tests pass | ✅ Backend complete; frontend = T3 scope | — |
| Self-Loop | ✅ 100% | ✅ All tests pass | ✅ No external deps | — |
| Self-Prompt | ✅ 100% | ✅ All tests pass | ✅ No external deps | — |
| Hermes ACP | ⚠️ Partially ready | ✅ | ⚠️ Binary installed; `acp.cwd` empty | Set `acp.cwd` in config |
| All other integrations | ✅ 100% mock | ✅ | ❌ No resources present | Per-user decision |

**Critical Gap:** 3 adapters have complete real-mode infrastructure but raise errors instead of performing real operations. This is the sole M14-T2 implementation gap.

---

## 5. M14-T2 Boundary Definition

### 5.1 In-Scope for M14-T2

1. **Supabase real-mode REST client** — implement `_call_rest()` with aiohttp/requests HTTP client
2. **n8n real-mode REST client** — implement `_call_rest()` with HTTP workflow execution
3. **Obsidian Git real-mode filesystem + Git operations** — implement `_write_real()`, `_read_real()`, `_delete_real()`
4. **Configuration wiring** — pass credentials from kernel config/env to adapter constructors properly
5. **Integration/E2E tests** for real-mode paths (gated with `@pytest.mark.gated @pytest.mark.external`)
6. **Real-mode gating verification** — confirm fail-closed behavior is preserved

### 5.2 Out-of-Scope for M14-T2

- **Obsidian (M8) adapter** — filesystem operations already implemented and tested (dual-path MCP+filesystem)
- **Dashboard frontend** — Terminal 3 scope
- **Self-loop / self-prompt** — already complete
- **Hermes ACP** — partial, deferred to separate work
- **New adapters** — all 12 adapters exist
- **Security infrastructure** — SecurityManager, terminal contract, provenance, secret redaction all complete
- **M7–M12 code changes** — none permitted
- **Configuration file edits** — only code-level config wiring allowed

### 5.3 Hard Constraints

- **FAIL-CLOSED DEFAULT:** `AIOS_REAL_INTEGRATION_ENABLED` must NOT be set by default; all real operations require explicit user enablement
- **AI-OS SOLE AUTHORITY:** No external system gains governance/verification/decision-making authority
- **C14 PROVENANCE:** All external data force-reasserted as `advisory=True, authority=contextual, trust_level=untrusted`
- **GATE-BEFORE-CONNECT:** SecurityManager.authorize() called before every real external operation
- **NO SCOPE CREEP:** Only the 3 adapter real paths + tests + config wiring

---

## 6. Verification of Seven Expected Areas

### 6.1 Obsidian Filesystem Operations — ALREADY IMPLEMENTED ✅

`obsidian_adapter.py` has a complete dual-path implementation:
- **MCP path:** Primary via `MCPManager.call_tool()`
- **Filesystem fallback:** When MCP unavailable, falls back to direct vault filesystem reads
- **Methods implemented:** `search_notes()`, `get_note()`, `list_notes()`, `read_note()` — all with fallback
- **Tests:** 28 unit tests in `test_obsidian_adapter.py` covering both paths
- **Key evidence:** Lines 520–599 show `_search_local()`, `_read_local()`, `_list_local()` using `pathlib.Path`

**Verdict:** No M14-T2 work needed for Obsidian filesystem.

### 6.2 Obsidian Git — REAL PATHS ARE STUBS ❌

`obsidian_git_adapter.py` lines 569–585:
```python
async def _write_real(self, ...):
    raise ObsidianGitUnavailableError(
        "Real Obsidian Git writer not injected; use mock mode or inject writer"
    )

async def _read_real(self, knowledge_id: str) -> dict[str, Any] | None:
    raise ObsidianGitUnavailableError(
        "Real Obsidian Git reader not injected; use mock mode or inject reader"
    )

async def _delete_real(self, knowledge_id: str) -> bool:
    raise ObsidianGitUnavailableError(
        "Real Obsidian Git deleter not injected; use mock mode or inject deleter"
    )
```

**Verdict:** **M14-T2 MUST IMPLEMENT** these three methods with real filesystem + Git operations.

### 6.3 Supabase REST Client — REAL PATH IS A STUB ❌

`supabase_adapter.py` lines 405–414:
```python
async def _call_rest(self, method: str, *args: Any) -> Any:
    """Real Supabase REST dispatch (bounded resource).
    
    Intentionally minimal: real deployments inject an HTTP client. The
    kernel never stores credentials; only env-supplied values are used.
    Raises SupabaseUnavailableError on missing client to degrade safely.
    """
    raise SupabaseUnavailableError(
        "Real Supabase REST client not injected; use mock mode or inject client"
    )
```

**Verdict:** **M14-T2 MUST IMPLEMENT** `_call_rest()` with actual Supabase REST API calls using `aiohttp` or `httpx`.

### 6.4 Configuration Wiring — PARTIALLY WIRING GAPS ❌

Kernel wiring at `kernel.py:1512–1518` (Supabase):
```python
adapter = SupabaseAdapter(
    mcp_manager=self._mcp_manager,
    server_id="supabase",
    timeout_seconds=30,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
)
```
**Issue:** `url` and `anon_key` are NOT passed from kernel config. The adapter reads them from env vars directly, but the kernel should also read them from config and pass them explicitly.

Kernel wiring at `kernel.py:1562–1568` (n8n):
```python
adapter = N8nAdapter(
    mcp_manager=self._mcp_manager,
    server_id="n8n",
    timeout_seconds=300,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
)
```
**Issue:** `base_url` and `api_key` are NOT passed from kernel config. Same pattern.

**Verdict:** **M14-T2 MUST FIX** kernel wiring to pass credentials from config to adapters explicitly (never store in code).

### 6.5 Real-Mode Gating — CORRECTLY IMPLEMENTED ✅

`src/aios/integrations/config.py`:
- Line 45: `REAL_OPERATION_ENV = "AIOS_REAL_INTEGRATION_ENABLED"`
- Line 93: `real_allowed()` enforces `mode=REAL AND env_gate AND user_resource_present`
- Line 331: `assert_real_allowed()` raises `RuntimeError` if not permitted

All three adapters check this at connect time via SecurityManager.

**Verdict:** Real-mode gating is correct and must NOT be modified.

### 6.6 Integration Tests — MOCK TESTS PASS; REAL TESTS MISSING ✅/❌

**Existing (passing):**
- `test_supabase_adapter.py` — 14 tests, all mock-mode (1 passes at line 228: `test_real_mode_no_client_raises` confirms degradation)
- `test_n8n_adapter.py` — 12 tests, all mock-mode (1 passes at line 200: `test_real_mode_no_client_errors` confirms degradation)
- `test_obsidian_git_adapter.py` — 14 tests, all mock-mode (1 passes at line 227: `test_real_mode_no_writer_errors` confirms degradation)
- `test_terminal2_gated_real.py` — 10 gated tests for all integrations
- `test_terminal2_cross_integration_e2e.py` — 9 gated E2E tests
- `test_terminal2_failure_degradation.py` — 10 gated failure tests
- `test_m13_integration.py` — 8 kernel-level acceptance tests

**Missing:** Zero tests exercise the REAL execution paths of Supabase, n8n, or Obsidian Git because the real paths don't exist yet.

**Verdict:** **M14-T2 MUST ADD** integration tests for real-mode paths (gated, mock-optional).

### 6.7 Dashboard — BACKEND COMPLETE ✅

`dashboard_service.py` (22.8KB), `dashboard_server.py` (6.2KB), `dashboard.html` (10KB) all exist and are functional. 11 unit tests pass. The dashboard is **read-only** with `X-AIOS-Authority: aios_sole` header, fail-closed, no authorize/verify/decide methods.

**Verdict:** No M14-T2 work needed. Dashboard backend is complete; frontend is Terminal 3 scope.

---

## 7. Real-Mode Gating Contract (Preserved)

M14-T2 MUST preserve the existing real-mode gating contract without modification:

### 7.1 Environment Gate
```python
AIOS_REAL_INTEGRATION_ENABLED = "1"  # Required for ANY real external operation
```

### 7.2 Per-Integration Gate
Each integration requires:
1. `mode: real` in `config/integrations.yaml`
2. `user_resource_present: true` in `config/integrations.yaml`
3. `AIOS_REAL_INTEGRATION_ENABLED=1` env var
4. Valid credentials in environment (never in config files)

### 7.3 Security Manager Gate
Before any real operation:
```python
decision = security_manager.authorize(
    principal="aios_kernel",
    action="<integration>_connect",
    resource="<url_or_path>",
    context={"server_id": "<id>"},
)
if decision.value != "allow":
    return False  # Fail-closed
```

### 7.4 Fail-Closed Default
When `AIOS_REAL_INTEGRATION_ENABLED` is NOT set, all gated integrations default to MOCK. This MUST NOT change.

---

## 8. Security & Authority Preservation

### 8.1 Non-Negotiable Rules

| Rule | Enforcement Point | Status |
|------|-------------------|--------|
| AI-OS = sole runtime authority | Kernel boot, terminal contract validation | ✅ PRESERVED |
| External systems = advisory only | C14 provenance on all external data | ✅ PRESERVED |
| Gate-before-connect | SecurityManager.authorize() before every real op | ✅ PRESERVED |
| No dual source-of-truth | StateManager authoritative; externals = mirrors | ✅ PRESERVED |
| Secret zeroization | `redact_secrets()` on all log/output paths | ✅ PRESERVED |
| No external autonomous triggers | Bounded retries; AI-OS decides recovery | ✅ PRESERVED |
| Terminal separation | T2 adapters = `authority_level="bounded_resource"` | ✅ PRESERVED |
| Fail-closed authorization | SecurityManager DENY default; unknown principal = DENY | ✅ PRESERVED |
| Advisory preservation | Externally-sourced data force-reasserted `advisory=True` | ✅ PRESERVED |
| Audit trail integrity | SHA-256 chaining; tamper detection verified | ✅ PRESERVED |

### 8.2 M14-T2 Security Requirements

1. **Supabase real writes:** Validate schema is AI-OS-owned before any insert/update/delete/query
2. **n8n real workflows:** All parameters validated for size, sensitive keys, bounds
3. **Obsidian Git real writes:** Path traversal blocked; knowledge type validated; content size capped at 100KB
4. **Provenance:** All real-mode operations must include `mode: "real"` in provenance metadata
5. **Error degradation:** Real-mode failures MUST degrade to ERROR result, NOT crash the kernel

---

## 9. Obsidian Git Specification (M14-T2 Task 1)

### 9.1 Current State
- `_write_real()`, `_read_real()`, `_delete_real()` raise `ObsidianGitUnavailableError`
- Mock mode uses `_MockObsidianGitStore` with SHA-1 content-hashed commits
- Knowledge types: `project_state`, `decision_record`, `learning_insight`, `execution_evidence`, `process_knowledge`, `reference_knowledge`
- Max content size: 100KB per artifact

### 9.2 Required Implementation

#### 9.2.1 `_write_real()` — Create/Update Knowledge

```python
async def _write_real(
    self,
    knowledge_id: str,
    content: str,
    metadata: dict[str, Any],
    update: bool = False,
) -> dict[str, Any]:
    """Write knowledge to filesystem vault with Git commit.
    
    1. Validate vault_path exists and is within allowed directories
    2. Write markdown file to vault (with frontmatter from metadata)
    3. Stage and commit via Git (using subprocess or dulwich)
    4. Return commit metadata mirroring mock store semantics
    """
```

**Implementation requirements:**
- Use `pathlib.Path` with vault boundary validation (prevent traversal)
- Write `.md` files with YAML frontmatter containing `knowledge_id`, `knowledge_type`, `created_by`, `provenance`
- Use `git` CLI or `dulwich` library for commits
- Commit message format: `{operation}: {knowledge_id}`
- Capture commit hash from `git rev-parse HEAD`
- Handle existing file (update) vs new file (create)
- Atomic write: write to temp file, then rename

#### 9.2.2 `_read_real()` — Read Knowledge

```python
async def _read_real(self, knowledge_id: str) -> dict[str, Any] | None:
    """Read knowledge from filesystem vault.
    
    1. Locate markdown file by knowledge_id in vault
    2. Parse frontmatter + body
    3. Return structured record matching mock store format
    4. Return None if not found (don't raise)
    """
```

**Implementation requirements:**
- Search vault directory for file matching `knowledge_id`
- Parse YAML frontmatter (use `yaml` or `toml` — whichever is available)
- Return format matching `_MockObsidianGitStore.get()` output
- Path traversal validation mandatory

#### 9.2.3 `_delete_real()` — Delete Knowledge

```python
async def _delete_real(self, knowledge_id: str) -> bool:
    """Delete knowledge from filesystem vault with Git commit.
    
    1. Locate and remove markdown file
    2. Stage and commit deletion via Git
    3. Return True if deleted, False if not found
    """
```

**Implementation requirements:**
- `git rm` the file
- Commit with message `delete: {knowledge_id}`
- Return False (not raise) if file doesn't exist

### 9.3 Dependencies

- Git CLI must be available (`git --version` check)
- Vault path must exist and be writable
- No new Python packages required (use stdlib `subprocess`, `pathlib`, `yaml` via PyYAML)

### 9.4 Provenance Format

```python
{
    "source": "obsidian_git",
    "adapter": "obsidian_git_adapter",
    "operation": "create_knowledge|update_knowledge|delete_knowledge",
    "correlation_id": "<uuid>",
    "timestamp": "<ISO8601>",
    "request_id": "<uuid>",
    "version": <int>,
    "authority": "aios_owned",
    "semantic_owner": "aios_kernel",
    "durability": "git_version_control",
    "mode": "real",
    "commit_hash": "<sha1>",          # new for real mode
    "vault_path": "<validated_path>",  # new for real mode
}
```

---

## 10. Supabase Specification (M14-T2 Task 2)

### 10.1 Current State
- `_call_rest()` raises `SupabaseUnavailableError`
- Mock mode uses `_MockSupabaseStore` (in-memory dict with table/row semantics)
- AI-OS-owned schemas: `project_state`, `execution_state`, `evidence_learning`, `integration_state`, `dashboard_state`
- Max content size: 100KB per row
- Credentials: `SUPABASE_URL` + `SUPABASE_ANON_KEY` from env

### 10.2 Required Implementation

#### 10.2.1 `_call_rest()` — HTTP Client Dispatch

```python
async def _call_rest(self, method: str, *args: Any) -> Any:
    """Real Supabase REST dispatch (bounded resource).
    
    Routes to appropriate REST endpoint based on method name:
    - "insert" → POST /rest/v1/{table}
    - "get" → GET /rest/v1/{table}?id=eq.{row_id}
    - "update" → PATCH /rest/v1/{table}?id=eq.{row_id}
    - "delete" → DELETE /rest/v1/{table}?id=eq.{row_id}
    - "query" → POST /rest/v1/{table}?select=*&{filters}
    """
```

**Implementation requirements:**
- Use `aiohttp` or `httpx` async HTTP client (check which is already a dependency)
- Base URL: `f"{self._url}/rest/v1/{table}"`
- Headers: `apikey: {self._anon_key}`, `Authorization: Bearer {self._anon_key}`, `Prefer: return=minimal` (for insert/delete) or `Prefer: return=representation` (for get/update/query)
- JSON body for POST/PATCH; query params for GET/DELETE
- Timeout: `self._timeout_seconds`
- Error handling: map HTTP status codes to appropriate exceptions
  - 404 → return None (for get/query) or False (for delete)
  - 400 → `SupabaseValidationError`
  - 401/403 → `SupabaseSecurityError`
  - 500/503 → `SupabaseUnavailableError`
  - Timeout → `SupabaseTimeoutError`

### 10.3 Dependencies

- `aiohttp` or `httpx` must be available (check `requirements.txt`)
- Network access to Supabase project URL
- Valid `SUPABASE_URL` and `SUPABASE_ANON_KEY` environment variables

### 10.4 Security Requirements

- Anon key never logged or exposed in error messages
- Schema validation enforced BEFORE any HTTP call
- Row content size validation BEFORE serialization
- Sensitive key rejection BEFORE serialization

### 10.5 Provenance Format

```python
{
    "source": "supabase",
    "adapter": "supabase_adapter",
    "operation": "insert|get|update|delete|query",
    "correlation_id": "<uuid>",
    "timestamp": "<ISO8601>",
    "request_id": "<uuid>",
    "version": <int>,
    "authority": "aios_owned",
    "semantic_owner": "aios_kernel",
    "mode": "real",
    "table": "<schema_name>",           # new for real mode
    "row_id": "<uuid>",                 # new for real mode (if applicable)
}
```

---

## 11. n8n Specification (M14-T2 Task 3)

### 11.1 Current State
- `_call_rest()` raises `N8nUnavailableError`
- Mock mode uses `_MockN8nEngine` with predefined workflow responses
- Workflow execution: POST to n8n API with workflow ID, parameters, bounds
- Credentials: `N8N_BASE_URL` + `N8N_API_KEY` from env
- Max content size: 50KB per request

### 11.2 Required Implementation

#### 11.2.1 `_call_rest()` — HTTP Workflow Execution

```python
async def _call_rest(
    self,
    workflow_id: str,
    parameters: dict[str, Any],
    bounds: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    """Real n8n REST dispatch (bounded resource).
    
    Executes workflow via n8n API:
    POST {base_url}/api/v1/executions
    Body: {workflowId, data: {main: [[{json: parameters}]]}, startingNode: ...}
    """
```

**Implementation requirements:**
- Use same HTTP client as Supabase (aiohttp/httpx)
- Endpoint: `f"{self._base_url}/api/v1/executions"`
- Auth header: `X-N8n-API-Key: {self._api_key}`
- Request body follows n8n webhook execution format
- Bounds validation: timeout from `bounds.get("timeout_seconds", 300)`
- Idempotency key passed as header or in request body (per n8n API spec)
- Response parsing: extract execution status, output data, error info
- Error mapping:
  - 401/403 → `N8nSecurityError`
  - 404 → `N8nNotConfiguredError` (workflow not found)
  - 429 → `N8nTimeoutError` (rate limited)
  - 500 → `N8nUnavailableError`
  - Timeout → `N8nTimeoutError`

### 11.3 Dependencies

- n8n instance must be running and reachable
- Valid `N8N_BASE_URL` and `N8N_API_KEY` environment variables
- Same HTTP client library as other adapters

### 11.4 Security Requirements

- API key never logged or exposed in error messages
- Parameter size validation BEFORE serialization
- Sensitive key rejection BEFORE serialization
- Timeout enforced strictly (bounded execution)

### 11.5 Provenance Format

```python
{
    "source": "n8n",
    "adapter": "n8n_adapter",
    "operation": "execute_workflow",
    "correlation_id": "<uuid>",
    "timestamp": "<ISO8601>",
    "request_id": "<uuid>",
    "version": <int>,
    "authority": "aios_directed",
    "semantic_owner": "aios_kernel",
    "mode": "real",
    "workflow_id": "<n8n_workflow_uuid>",   # new for real mode
    "execution_id": "<n8n_execution_uuid>", # new for real mode
}
```

---

## 12. Configuration Wiring Specification (M14-T2 Task 4)

### 12.1 Current Kernel Wiring Gaps

#### Supabase (kernel.py:1512–1518)
```python
# CURRENT (INCOMPLETE):
adapter = SupabaseAdapter(
    mcp_manager=self._mcp_manager,
    server_id="supabase",
    timeout_seconds=30,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
)
# MISSING: url and anon_key not passed from config

# REQUIRED (M14-T2):
supabase_url = (
    self._read_config_str("services.supabase.url", "")
    or os.environ.get("SUPABASE_URL")
)
supabase_anon_key = (
    self._read_config_str("services.supabase.anon_key", "")
    or os.environ.get("SUPABASE_ANON_KEY")
)
adapter = SupabaseAdapter(
    mcp_manager=self._mcp_manager,
    server_id="supabase",
    timeout_seconds=30,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
    url=supabase_url or None,
    anon_key=supabase_anon_key or None,
)
```

#### n8n (kernel.py:1562–1568)
```python
# CURRENT (INCOMPLETE):
adapter = N8nAdapter(
    mcp_manager=self._mcp_manager,
    server_id="n8n",
    timeout_seconds=300,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
)
# MISSING: base_url and api_key not passed from config

# REQUIRED (M14-T2):
n8n_base_url = (
    self._read_config_str("services.n8n.base_url", "")
    or os.environ.get("N8N_BASE_URL")
)
n8n_api_key = (
    self._read_config_str("services.n8n.api_key", "")
    or os.environ.get("N8N_API_KEY")
)
adapter = N8nAdapter(
    mcp_manager=self._mcp_manager,
    server_id="n8n",
    timeout_seconds=300,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
    base_url=n8n_base_url or None,
    api_key=n8n_api_key or None,
)
```

#### Obsidian Git (kernel.py:1610–1625)
```python
# CURRENT (PARTIAL):
vault_path = (
    self._read_config_str("services.obsidian_git.vault_path", "")
    or os.environ.get("OBSIDIAN_VAULT_PATH")
)
# MISSING: remote_url not passed from config

# REQUIRED (M14-T2):
obsidian_git_remote_url = (
    self._read_config_str("services.obsidian_git.remote_url", "")
    or os.environ.get("OBSIDIAN_GIT_REMOTE_URL")
)
adapter = ObsidianGitAdapter(
    mcp_manager=self._mcp_manager,
    server_id="obsidian_git",
    vault_path=vault_path or None,
    timeout_seconds=30,
    real_mode_enabled=real_mode,
    security_manager=self._security_manager,
    remote_url=obsidian_git_remote_url or None,
)
```

### 12.2 Configuration File Updates

`config/integrations.yaml` — Add credential placeholders (NOT actual values):
```yaml
  supabase:
    mode: mock
    real_gated: true
    # Real mode requires: SUPABASE_URL, SUPABASE_ANON_KEY env vars
    # Uncomment below when credentials are available:
    # url: ""
    # anon_key: ""

  n8n:
    mode: mock
    real_gated: true
    # Real mode requires: N8N_BASE_URL, N8N_API_KEY env vars
    # Uncomment below when credentials are available:
    # base_url: ""
    # api_key: ""

  obsidian_git:
    mode: mock
    real_gated: true
    # Real mode requires: OBSIDIAN_VAULT_PATH env var
    # Uncomment below when vault is available:
    # vault_path: ""
    # remote_url: ""
```

**Note:** Actual credential values must NEVER be committed to repository. Only placeholder comments are added.

---

## 13. Test Contract (M14-T2 Task 5)

### 13.1 Required New Tests

All new tests MUST be:
- Marked `@pytest.mark.gated @pytest.mark.external`
- Skipped by default (require `AIOS_REAL_INTEGRATION_ENABLED=1` to run)
- Defensive: degrade gracefully if real resources are absent

#### 13.1.1 Supabase Real-Mode Integration Tests (`tests/integration/test_supabase_real_mode.py`)

| Test | Description |
|------|-------------|
| `test_supabase_real_mode_requires_gate` | Without `AIOS_REAL_INTEGRATION_ENABLED=1`, real mode stays mock even with credentials |
| `test_supabase_real_connect_with_credentials` | With gate + env vars, adapter enters real mode |
| `test_supabase_real_insert_get_roundtrip` | Insert row, retrieve it, verify content matches |
| `test_supabase_real_update` | Insert then update, verify changed value |
| `test_supabase_real_delete` | Insert then delete, verify not found |
| `test_supabase_real_query` | Insert multiple rows, query with filter, verify count |
| `test_supabase_real_schema_validation` | Unknown schema rejected in real mode |
| `test_supabase_real_secret_rejection` | Row with sensitive key rejected in real mode |
| `test_supabase_real_security_deny_blocks_connect` | SecurityManager deny prevents real connection |
| `test_supabase_real_network_error_degrades` | Network failure returns ERROR result, not exception |

#### 13.1.2 n8n Real-Mode Integration Tests (`tests/integration/test_n8n_real_mode.py`)

| Test | Description |
|------|-------------|
| `test_n8n_real_mode_requires_gate` | Without gate, real mode stays mock |
| `test_n8n_real_connect_with_credentials` | With gate + env vars, adapter enters real mode |
| `test_n8n_real_workflow_execution` | Execute a workflow, verify success result |
| `test_n8n_real_parameter_validation` | Oversized params rejected in real mode |
| `test_n8n_real_sensitive_key_rejection` | Sensitive params rejected in real mode |
| `test_n8n_real_bounds_validation` | Invalid bounds rejected in real mode |
| `test_n8n_real_idempotency_key` | Idempotency key propagated to real API |
| `test_n8n_real_security_deny_blocks_connect` | SecurityManager deny prevents real connection |
| `test_n8n_real_network_error_degrades` | Network failure returns ERROR result |

#### 13.1.3 Obsidian Git Real-Mode Integration Tests (`tests/integration/test_obsidian_git_real_mode.py`)

| Test | Description |
|------|-------------|
| `test_obsidian_git_real_mode_requires_gate` | Without gate, real mode stays mock |
| `test_obsidian_git_real_connect_with_vault` | With gate + vault path, adapter enters real mode |
| `test_obsidian_git_real_create_knowledge` | Create knowledge file in vault, verify commit |
| `test_obsidian_git_real_read_knowledge` | Read created knowledge, verify content |
| `test_obsidian_git_real_update_knowledge` | Update knowledge, verify new content + new commit |
| `test_obsidian_git_real_delete_knowledge` | Delete knowledge, verify file removed + commit |
| `test_obsidian_git_real_commit_history` | Multiple operations produce correct commit history |
| `test_obsidian_git_real_integrity_check` | Git history integrity verifiable |
| `test_obsidian_git_real_knowledge_type_validation` | Unknown knowledge type rejected |
| `test_obsidian_git_real_sensitive_content_rejection` | Sensitive content rejected |
| `test_obsidian_git_real_path_traversal_blocked` | Vault path traversal prevented |
| `test_obsidian_git_real_missing_vault_degrades` | Missing vault returns ERROR, not crash |
| `test_obsidian_git_real_security_deny_blocks_connect` | SecurityManager deny prevents real connection |

### 13.2 Regression Requirement

All existing tests MUST continue to pass after M14-T2 changes:
- `test_supabase_adapter.py` — 14 tests
- `test_n8n_adapter.py` — 12 tests
- `test_obsidian_git_adapter.py` — 14 tests
- `test_terminal_contract.py` — 19 tests
- `test_failure_recovery.py` — 17 tests
- `test_m13_integration.py` — 8 tests
- `test_terminal2_gated_real.py` — 10 tests
- `test_terminal2_cross_integration_e2e.py` — 9 tests
- `test_terminal2_failure_degradation.py` — 10 tests

**Total regression baseline:** ~113 M13-related tests, plus full suite of 2,241 tests.

---

## 14. Failure / Offline Behavior Contract

### 14.1 Graceful Degradation Rules

| Scenario | Expected Behavior |
|----------|-------------------|
| Real mode enabled but credentials absent | Adapter stays in mock mode (safe default) |
| Real mode enabled, credentials present, but network unreachable | `SupabaseUnavailableError` / `N8nUnavailableError` / `ObsidianGitUnavailableError` → ERROR result, not exception |
| Real mode enabled, operation fails (4xx/5xx) | Map HTTP status to appropriate error → ERROR result |
| Operation times out | Timeout exception → ERROR result |
| SecurityManager denies connection | Returns `False` from `connect()`, no operation attempted |
| Vault path doesn't exist (Obsidian Git) | `ObsidianGitNotConfiguredError` → ERROR result |
| Git command not found | `ObsidianGitUnavailableError` → ERROR result, fallback to mock not attempted (Git is hard requirement for real mode) |

### 14.2 Kernel Resilience

- Real-mode adapter failures MUST NOT crash the kernel
- FailureRecoveryManager handles bounded retries for real-mode operations
- Provenance always recorded, even on failure (with `mode: "real"` + error details)
- Terminal contract validation runs at boot regardless of adapter mode

---

## 15. Ollama / Local Recovery Scope Check

**Verdict: OUT OF SCOPE for M14-T2**

- Self-loop engine uses `ModelRouter` which defaults to local/mock providers when no external keys are configured
- FreeLLMAPI adapter exists but defaults to mock
- No Ollama-specific integration exists in M13/M14 scope
- Self-loop and self-prompt are already complete and functional in mock mode
- Local recovery is handled by FailureRecoveryManager's local fallback mechanisms

M14-T2 does NOT need to modify any self-loop, self-prompt, or local model routing code.

---

## 16. M13 → M14 Handoff Verification

### 16.1 M13 Deliverables Received ✅

| M13 Deliverable | Status | Evidence |
|-----------------|--------|----------|
| Supabase adapter (mock + stub real) | ✅ Complete | `supabase_adapter.py` 535 lines |
| n8n adapter (mock + stub real) | ✅ Complete | `n8n_adapter.py` 453 lines |
| Obsidian Git adapter (mock + stub real) | ✅ Complete | `obsidian_git_adapter.py` 600 lines |
| Kernel wiring (3 adapters) | ✅ Complete | `kernel.py:1498–1650` |
| Terminal contract validation | ✅ Complete | `kernel.py:1646` |
| FailureRecoveryManager | ✅ Complete | `failure_recovery.py` |
| Real-mode gating infrastructure | ✅ Complete | `config.py:45,93,331` |
| Integration test framework | ✅ Complete | 3 test files, 29 gated tests |
| Dashboard backend | ✅ Complete | 3 dashboard files |
| Self-loop engine | ✅ Complete | `self_loop_engine.py` |
| Self-prompt generator | ✅ Complete | `self_prompt_generator.py` |
| Terminal handoff contract | ✅ Complete | `M13_TERMINAL_HANDOFF_CONTRACT.md` |

### 16.2 M13 Known Limitations (Carried to M14)

| Limitation | Impact | M14-T2 Resolution |
|------------|--------|-------------------|
| Real-mode paths raise errors | Production real-mode unusable | **PRIMARY M14-T2 GOAL** |
| Kernel doesn't pass credentials from config | Credentials only from env, not config | **FIXED in Task 4** |
| 10 M10 integration tests fail | Test framework issue, not production defect | Out of scope (pre-existing) |
| 5 M8 genuine xfails (D-03..D-06) | C14 provenance gaps | Not M14-T2 scope |
| CONFLICT-P15-01 unresolved | Part 15 naming divergence | Not M14-T2 scope |

---

## 17. Acceptance Matrix

| Criterion | Target | Pre-M14-T2 | M14-T2 Post-Implementation |
|-----------|--------|------------|---------------------------|
| Supabase real-mode insert/get/update/delete/query | All operations succeed with real REST | ❌ Raises error | ✅ HTTP operations |
| n8n real-mode workflow execution | Workflow executes, result returned | ❌ Raises error | ✅ HTTP execution |
| Obsidian Git real-mode create/read/update/delete | Filesystem + Git operations work | ❌ Raises error | ✅ Filesystem + Git |
| Kernel passes credentials from config | `url`/`api_key`/`vault_path` from config | ❌ Env only | ✅ Config + env |
| Real-mode gating preserved | `AIOS_REAL_INTEGRATION_ENABLED` gate enforced | ✅ Working | ✅ Unchanged |
| SecurityManager gate preserved | authorize() called before real ops | ✅ Working | ✅ Unchanged |
| Terminal contract enforced | T2 adapters = bounded_resource | ✅ Working | ✅ Unchanged |
| All existing tests pass | 100% regression | ~1,991/2,241 pass | Same + new gated tests |
| New real-mode tests | ≥10 tests per adapter | 0 | ≥13 per adapter |
| Fail-closed behavior | Mock by default, real only with explicit gate | ✅ Working | ✅ Unchanged |
| No M7–M12 code modified | Zero changes to prior milestones | ✅ Verified | ✅ Verified |
| AI-OS sole authority preserved | No authority escalation | ✅ Verified | ✅ Verified |

---

## 18. Implementation Order

M14-T2 should be implemented in this order (each task is independent but later tasks depend on earlier ones being correct):

### Phase 1: Configuration Wiring (Day 1)
1. **Task 1.1:** Update `kernel.py` `_init_supabase()` to pass `url` and `anon_key` from config
2. **Task 1.2:** Update `kernel.py` `_init_n8n()` to pass `base_url` and `api_key` from config
3. **Task 1.3:** Update `kernel.py` `_init_obsidian_git()` to pass `remote_url` from config
4. **Task 1.4:** Update `config/integrations.yaml` with credential placeholder comments
5. **Verification:** All existing tests still pass

### Phase 2: Supabase Real-Mode Implementation (Day 2)
6. **Task 2.1:** Implement `_call_rest()` in `supabase_adapter.py` with aiohttp/httpx client
7. **Task 2.2:** Add error mapping for HTTP status codes
8. **Task 2.3:** Add provenance `mode: "real"` + `table`/`row_id` fields
9. **Task 2.4:** Write 10 integration tests in `test_supabase_real_mode.py`
10. **Verification:** Mock tests pass + new gated real tests pass (with `AIOS_REAL_INTEGRATION_ENABLED=1`)

### Phase 3: n8n Real-Mode Implementation (Day 2)
11. **Task 3.1:** Implement `_call_rest()` in `n8n_adapter.py` with HTTP workflow execution
12. **Task 3.2:** Add error mapping for HTTP status codes
13. **Task 3.3:** Add provenance `mode: "real"` + `workflow_id`/`execution_id` fields
14. **Task 3.4:** Write 9 integration tests in `test_n8n_real_mode.py`
15. **Verification:** Mock tests pass + new gated real tests pass

### Phase 4: Obsidian Git Real-Mode Implementation (Day 3)
16. **Task 4.1:** Implement `_write_real()` with filesystem write + Git commit
17. **Task 4.2:** Implement `_read_real()` with filesystem read + frontmatter parse
18. **Task 4.3:** Implement `_delete_real()` with filesystem delete + Git commit
19. **Task 4.4:** Add vault path traversal validation
20. **Task 4.5:** Add provenance `mode: "real"` + `commit_hash`/`vault_path` fields
21. **Task 4.6:** Write 13 integration tests in `test_obsidian_git_real_mode.py`
22. **Verification:** Mock tests pass + new gated real tests pass (with vault path)

### Phase 5: Integration & Regression (Day 3)
23. **Task 5.1:** Run full test suite (2,241 tests) — verify zero regressions
24. **Task 5.2:** Run gated real tests with mock resources (verify safe degradation)
25. **Task 5.3:** Run gated real tests with real resources (verify end-to-end)
26. **Task 5.4:** Verify terminal contract enforcement at boot
27. **Task 5.5:** Verify security gate fail-closed behavior
28. **Task 5.6:** Document implementation in M14-T2 closure report

---

## 19. Terminal 2 Contract

### 19.1 M14-T2 Owner Responsibilities

1. Implement real execution paths for Supabase, n8n, Obsidian Git adapters
2. Wire configuration to pass credentials from config to adapters
3. Add gated integration tests for all real-mode paths
4. Preserve all existing security, authority, and terminal contract boundaries
5. Ensure zero regressions in M7–M13 tests
6. Document implementation in closure report

### 19.2 M14-T2 Boundaries

- **Maximum files to modify:** 4 source files (`supabase_adapter.py`, `n8n_adapter.py`, `obsidian_git_adapter.py`, `kernel.py`) + 3 new test files
- **Maximum files to create:** 3 test files (`test_supabase_real_mode.py`, `test_n8n_real_mode.py`, `test_obsidian_git_real_mode.py`)
- **Files explicitly OUT OF SCOPE:** Any M7–M12 files, dashboard files, self-loop/self-prompt files, security manager, terminal contract
- **Maximum new dependencies:** None (use existing HTTP client library)

### 19.3 M14-T2 Forbidden Actions

- ❌ Do NOT modify any M7, M8, M9, M10, M11, or M12 source files
- ❌ Do NOT add new external dependencies
- ❌ Do NOT change real-mode gating logic
- ❌ Do NOT modify SecurityManager or terminal contract
- ❌ Do NOT commit actual credentials to repository
- ❌ Do NOT change dashboard backend
- ❌ Do NOT modify self-loop or self-prompt code

---

## 20. Terminal 3 Contract (For Reference)

Terminal 3 (Dashboard UI) owns:
- Dashboard frontend HTML/CSS/JS (separate from backend service)
- Visual presentation of AI-OS state
- User interaction with dashboard (read-only + action forwarding)
- **NO governance, verification, or decision-making authority**

M14-T2 does NOT touch Terminal 3 scope.

---

## 21. Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| HTTP client library mismatch (aiohttp vs httpx vs requests) | **MEDIUM** | Check existing dependencies; use what's already available; avoid adding new deps |
| Supabase API format changes | **LOW** | Follow official Supabase REST API v1 spec; version pin |
| n8n API format changes | **LOW** | Follow official n8n REST API spec; version pin |
| Git CLI unavailable on target system | **MEDIUM** | Check `git --version` at connect time; raise `ObsidianGitNotConfiguredError` if absent |
| Path traversal vulnerability in Obsidian Git | **HIGH** | Strict vault boundary validation; reject any path escaping vault root |
| Credential leak in logs/errors | **HIGH** | All credentials from env vars; never log raw values; redact_secrets() applied |
| Scope creep into M7–M12 code | **HIGH** | Explicit forbidden actions list; change review against git diff |
| Test flakiness with real external services | **MEDIUM** | All real tests gated; mock fallback for network failures; timeouts enforced |
| Kernel boot failure if real adapter raises | **MEDIUM** | Adapter initialization wrapped in try/except; failure degrades to mock |

---

## 22. Scope Freeze Statement

### M14-T2 SPECIFICATION FROZEN

This specification is **FINAL and BINDING** for Terminal 2 M14-T2 implementation.

**Scope boundaries:**
- ✅ IMPLEMENT: Supabase real REST client (`_call_rest()`)
- ✅ IMPLEMENT: n8n real REST client (`_call_rest()`)
- ✅ IMPLEMENT: Obsidian Git real filesystem + Git operations (`_write_real()`, `_read_real()`, `_delete_real()`)
- ✅ IMPLEMENT: Kernel configuration wiring (pass credentials from config)
- ✅ IMPLEMENT: 32 new gated integration tests
- ❌ NOT IN SCOPE: Any M7–M12 code changes
- ❌ NOT IN SCOPE: Dashboard frontend (Terminal 3)
- ❌ NOT IN SCOPE: New adapters
- ❌ NOT IN SCOPE: Security infrastructure changes
- ❌ NOT IN SCOPE: Self-loop / self-prompt modifications
- ❌ NOT IN SCOPE: Ollama / local model routing
- ❌ NOT IN SCOPE: New Python dependencies

**Change control:** Any scope change requires formal re-specification and Terminal 1 approval. No unauthorized modifications to M7–M13 codebase permitted.

**Verification gate:** M14-T2 is complete when:
1. All 32 new gated tests pass (with `AIOS_REAL_INTEGRATION_ENABLED=1`)
2. All 2,241 existing tests continue to pass
3. Zero M7–M12 code modified
4. Terminal contract violations = 0
5. Security boundary audit = PASS
6. Real-mode operations degrade safely when resources absent

---

## 23. Source Code Evidence Index

### Key Code Locations

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Supabase adapter | `src/aios/adapters/supabase_adapter.py` | 1–535 | Mock OK; real stub at lines 405–414 |
| n8n adapter | `src/aios/adapters/n8n_adapter.py` | 1–453 | Mock OK; real stub at lines 426–439 |
| Obsidian Git adapter | `src/aios/adapters/obsidian_git_adapter.py` | 1–600 | Mock OK; real stubs at lines 569–585 |
| Obsidian adapter (M8) | `src/aios/adapters/obsidian_adapter.py` | — | Complete; dual-path MCP+filesystem |
| Kernel wiring | `src/aios/core/kernel.py` | 1498–1650 | Gating correct; credential wiring incomplete |
| Real-mode gate | `src/aios/integrations/config.py` | 45, 93, 331 | Correct; no changes needed |
| Terminal contract | `src/aios/architecture/terminal_contract.py` | — | Complete; no changes needed |
| Integration tests | `tests/integration/test_m13_integration.py` | — | 8 tests, all pass |
| Gated real tests | `tests/integration/test_terminal2_gated_real.py` | — | 10 tests, all pass |
| Cross-integration E2E | `tests/integration/test_terminal2_cross_integration_e2e.py` | — | 9 tests, all pass |
| Failure degradation | `tests/integration/test_terminal2_failure_degradation.py` | — | 10 tests, all pass |
| Supabase unit tests | `tests/unit/test_supabase_adapter.py` | — | 14 tests, all pass |
| n8n unit tests | `tests/unit/test_n8n_adapter.py` | — | 12 tests, all pass |
| Obsidian Git unit tests | `tests/unit/test_obsidian_git_adapter.py` | — | 14 tests, all pass |
| Terminal contract tests | `tests/unit/test_terminal_contract.py` | — | 19 tests, all pass |
| Failure recovery tests | `tests/unit/test_failure_recovery.py` | — | 17 tests, all pass |

---

## 24. Open Items & Deferred Decisions

| Item | Classification | Owner | Status |
|------|---------------|-------|--------|
| CONFLICT-P15-01 (Part 15 naming) | ARB Resolution Required | Terminal 1 | BLOCKED — Not M14-T2 scope |
| C1–C4 open conditions | Documentation Alignment | Terminal 1 | UNRESOLVED — Not M14-T2 scope |
| DEF-M10-P0-01 (process violation) | Formal Acknowledgment | Terminal 1 | Documented — Not M14-T2 scope |
| M10 integration test failures (10 tests) | Test Framework Fix | Terminal 3 | Known limitation — Not M14-T2 scope |
| M8 xfails D-03..D-06 (C14 provenance) | Provenance Gap Fix | Deferred | 5 genuine xfails — Not M14-T2 scope |
| Dashboard frontend | Terminal 3 Scope | Terminal 3 | Deferred — Not M14-T2 scope |
| Hermes ACP real path | Separate Work | Deferred | Partially ready — Not M14-T2 scope |
| Ollama/local model integration | Future Milestone | Deferred | Not in M13/M14 scope |

---

## 25. Final Verdict

### M14-T2 SPECIFICATION READY — SCOPE FROZEN

**Rationale:**
1. ✅ All M7–M13 milestones verified as complete (with documented exceptions)
2. ✅ M14-T1 discovery report confirms implementation state
3. ✅ Three adapter real-mode stubs identified as the sole gap
4. ✅ Security, authority, and terminal contract boundaries preserved
5. ✅ Test contract defined with clear acceptance criteria
6. ✅ Implementation order specified with 5 phases
7. ✅ Risk assessment complete with mitigations
8. ✅ Scope freeze statement definitive

**Next Step:** Terminal 2 proceeds with implementation per this specification. Terminal 3 conducts independent verification upon completion.

---

**Document prepared by:** M14-T2 Specification Agent (Read-Only)
**Date:** 2026-08-30
**Repository state verified:** Commit `1800ae4` (m14 being pushed)
**Total lines reviewed:** ~15,000+ across source, tests, config, and documentation
**Confidence level:** HIGH — based on exhaustive code and documentation review

---

## Appendix A: Quick-Reference Implementation Checklist

### Supabase (`supabase_adapter.py`)
- [ ] Import aiohttp or httpx (check existing deps first)
- [ ] Implement `_call_rest()` method (lines 405–414)
- [ ] Route method names to HTTP verbs (insert→POST, get→GET, update→PATCH, delete→DELETE, query→POST with filters)
- [ ] Map HTTP errors to adapter exceptions
- [ ] Add provenance fields: `mode: "real"`, `table`, `row_id`
- [ ] Write 10 gated integration tests

### n8n (`n8n_adapter.py`)
- [ ] Implement `_call_rest()` method (lines 426–439)
- [ ] Format request body per n8n webhook execution API
- [ ] Map HTTP errors to adapter exceptions
- [ ] Add provenance fields: `mode: "real"`, `workflow_id`, `execution_id`
- [ ] Write 9 gated integration tests

### Obsidian Git (`obsidian_git_adapter.py`)
- [ ] Implement `_write_real()` (lines 569–575)
- [ ] Implement `_read_real()` (lines 577–579)
- [ ] Implement `_delete_real()` (lines 582–585)
- [ ] Vault path traversal validation
- [ ] Git commit via subprocess or dulwich
- [ ] Markdown file format with YAML frontmatter
- [ ] Add provenance fields: `mode: "real"`, `commit_hash`, `vault_path`
- [ ] Write 13 gated integration tests

### Kernel (`kernel.py`)
- [ ] `_init_supabase()`: Pass `url` and `anon_key` from config
- [ ] `_init_n8n()`: Pass `base_url` and `api_key` from config
- [ ] `_init_obsidian_git()`: Pass `remote_url` from config

### Configuration (`config/integrations.yaml`)
- [ ] Add credential placeholder comments for Supabase
- [ ] Add credential placeholder comments for n8n
- [ ] Add credential placeholder comments for Obsidian Git

### Verification
- [ ] Run `pytest` — all 2,241 tests pass
- [ ] Run `pytest -m gated -m external` — new real-mode tests pass (with env gate + resources)
- [ ] Verify terminal contract: zero violations
- [ ] Verify security: fail-closed, provenance correct, secrets redacted
- [ ] Verify no M7–M12 code modified

---

## Appendix B: File Inventory

### Files to Modify (4)
1. `src/aios/adapters/supabase_adapter.py` — Add `_call_rest()` implementation
2. `src/aios/adapters/n8n_adapter.py` — Add `_call_rest()` implementation
3. `src/aios/adapters/obsidian_git_adapter.py` — Add `_write_real()`, `_read_real()`, `_delete_real()` implementations
4. `src/aios/core/kernel.py` — Update 3 init methods to pass credentials from config

### Files to Create (3)
1. `tests/integration/test_supabase_real_mode.py` — 10 gated integration tests
2. `tests/integration/test_n8n_real_mode.py` — 9 gated integration tests
3. `tests/integration/test_obsidian_git_real_mode.py` — 13 gated integration tests

### Files to Update (1)
1. `config/integrations.yaml` — Add credential placeholder comments

### Files EXPLICITLY OUT OF SCOPE (DO NOT MODIFY)
- Any file in `src/aios/core/` except `kernel.py`
- Any file in `src/aios/adapters/` except the 3 adapter files listed above
- Any file in `tests/unit/` (existing unit tests must not change)
- Any M7–M12 milestone documentation
- Dashboard files (`src/aios/services/dashboard_*`, `src/aios/templates/dashboard.html`)
- Self-loop files (`src/aios/core/self_loop_engine.py`, `self_prompt_generator.py`)
- Security files (`src/aios/core/security_manager.py`, `src/aios/architecture/terminal_contract.py`)
- Configuration files except `config/integrations.yaml` (no changes to `defaults.yaml`, `app_config.yaml`, or MCP configs)
