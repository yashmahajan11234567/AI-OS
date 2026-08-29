# M8-T1 Implementation Specification
## Hermes ACP Protocol Integration — Terminal 2 Blueprint

**Date:** 2026-08-25
**Status:** READY FOR IMPLEMENTATION
**Prerequisites:** M7 (complete, 95/100 score, 1046 tests passing)

---

## 1. CURRENT IMPLEMENTATION

### 1.1 HermesBridge (`src/aios/adapters/hermes_bridge.py`, 310 lines)

**What exists:**
- `HermesTask` dataclass: `task_id`, `task_type`, `description`, `parameters`, `session_id`, `provenance`
- `HermesObservation` dataclass: `task_id`, `success`, `data`, `error`, `timestamp`, `session_id`, `provenance`, `trust_level="untrusted"`
- `HermesBridge` class with MCP-only path:
  - `__init__(mcp_manager=None, server_id="hermes_agent_ext")`
  - `_ensure_connected()` → delegates to MCPManager
  - `_create_session_id()` → `f"hermes_{uuid.uuid4().hex[:12]}"`
  - `_create_provenance(task, extra)` → dict with 8 fields
  - `create_worker_session(environment)` → calls MCP `create_session` tool (NOTE: this tool does NOT exist on mock_hermes_server — it returns error)
  - `close_worker_session(session_id)` → calls MCP `close_session` tool (same issue)
  - `execute_task(task)` → calls MCP `execute_task` tool (does NOT exist on mock — returns error)
  - Convenience methods: `navigate`, `click`, `type_text`, `screenshot`, `extract_content`, `wait_for`
  - `is_session_active(session_id)`, `get_active_sessions()`

**What's missing:**
- No ACP protocol support
- No session-ID lifecycle sync between create and close
- No protocol selection policy
- No provenance completeness (missing `protocol`, `call_id`, `exit_status`, `execution_id`, `correlation_id`)
- No error classification (all exceptions become generic `str(e)`)
- No timeout handling per-task
- No cancellation support

### 1.2 UserSimulationAgent (`src/aios/core/user_simulation_agent.py`, 307 lines)

**What exists:**
- Constructor takes `HermesBridge`
- `simulate(app_url, user_goal, exploration_brief, *, correlation_id=None)` → `UserSimulationCompleted`
- Defense-in-depth INV-008 (no source_code parameter)
- Returns observations only (never verdict)

**Defects (must be fixed in M8-T1):**
1. **DEF-002** (line 151): Calls `self._bridge._create_session_id()` directly — bypasses bridge's session management
2. **DEF-002** (line 166): Ignores return value of `create_worker_session()` — the returned session ID is the one the remote side actually created
3. **DEF-003** (line 298-306): `_obs_to_dict` drops `provenance` field from observations

### 1.3 Mock Hermes Server (`src/aios/adapters/mock_hermes_server.py`, 331 lines)

- Pure-MCP stdio server with 6 tools: `browser_navigate`, `browser_click`, `browser_type`, `browser_extract`, `browser_screenshot`, `worker_execute`
- In-memory session store with history tracking
- **Does NOT speak ACP**
- Has `create_session` and `close_session` tools? **NO** — they are not in the tools list, but the bridge calls them anyway. This means `create_worker_session` and `close_worker_session` always fail with the current mock.

### 1.4 Kernel Wiring (`src/aios/core/kernel.py:821-825`)

```python
hermes_bridge = HermesBridge(
    mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
    server_id="hermes_agent_ext",
)
self._user_simulation_agent = UserSimulationAgent(hermes_bridge)
```

`self._mcp_manager` does not exist on Kernel — bridge always gets `mcp_manager=None` (uses global singleton).

### 1.5 MCP Config (`config/mcp/hermes_agent_ext_mcp.json`)

```json
{
  "server_id": "hermes_agent_ext",
  "transport": "stdio",
  "command": ["python", "-m", "aios.adapters.mock_hermes_server"],
  "timeout_seconds": 30
}
```

### 1.6 psutil Issue

`tests/performance/test_structured_logger_perf.py:121`:
```python
import psutil  # type: ignore
```
- `psutil` not in `pyproject.toml` dev deps
- Test fails when `psutil` not installed: `ModuleNotFoundError`
- Test passes when `psutil` IS installed (current dev environment)

### 1.7 Test Baseline

- **1046 tests passing**, 1 failing (`test_memory_bounded_under_load` due to psutil)
- M7 tests: `tests/integration/test_m7_security.py` (13), `tests/unit/test_user_simulation_agent.py` (5)
- Zero ACP/MCP integration tests exist

---

## 2. GAP ANALYSIS

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| ACP-preferred execution | Not implemented | **COMPLETE GAP** — no ACP code exists |
| MCP fallback | Only path available | Works but has session lifecycle bug |
| Session isolation | Partial (UUID-based) | DEF-001: create_worker_session returns different ID than caller generates |
| Structured execution requests | Partial (HermesTask) | Needs protocol-agnostic request model |
| Structured observations/results | Partial (HermesObservation) | Missing `protocol`, `call_id`, `exit_status`, `execution_id` |
| Complete provenance | Partial (8 fields) | Needs 13+ fields per §9.1 of Part15 plan |
| Error propagation | Generic `str(e)` | No error classification (retryable vs non-retryable) |
| Timeout handling | None | Per-task timeout not supported |
| Cancellation/recovery | None | No cancel support |
| Capability detection | None | No tools/list or capability check for ACP |
| Health/status reporting | None | No health endpoint |
| Deterministic testability | Mock exists (MCP only) | Need ACP mock server for tests |
| No hidden state leakage | Partial | Session ID mismatch causes leakage risk |
| No fabricated observations | Yes (trust_level="untrusted") | Preserved |
| No fabricated success/failure | Yes | Preserved |
| No heuristic "looks successful" | Yes | Preserved |

---

## 3. ARCHITECTURE

### 3.1 Target Flow

```
AI-OS Kernel
  └─ HermesBridge(protocol="acp", fallback_to_mcp=True)
       ├─ Protocol Selector
       │    ├─ ACP path → AcPAdapter
       │    │    └─ subprocess: python -m acp_adapter.entry (from hermes-agent/)
       │    │         ├─ acp.run_agent() (requires `acp` SDK)
       │    │         ├─ new_session(cwd) → session_id
       │    │         ├─ prompt(session_id, text, timeout) → PromptResponse
       │    │         ├─ cancel(session_id)
       │    │         └─ close_session(session_id)
       │    └─ MCP path → MCPManager (existing)
       │         └─ mock_hermes_server (or real hermes-agent MCP)
       │
       ├─ Session Registry (internal)
       │    └─ _active_sessions: dict[session_id, session_metadata]
       │
       └─ Response Normalizer
            ├─ _normalize_acp_response(raw) → HermesObservation
            └─ _normalize_mcp_response(raw) → HermesObservation
```

### 3.2 Protocol Selection Policy

```
1. Read config: hermes.protocol (default "acp")
2. If protocol == "acp":
   a. Try to import `acp` SDK (deferred import, not module-scope)
   b. If import succeeds AND hermes-agent process launchable → use ACP
   c. If config.hermes.fallback_to_mcp == True AND ACP unavailable → use MCP,
      record provenance.protocol = "acp_fallback"
   d. If config.hermes.fallback_to_mcp == False AND ACP unavailable →
      raise ProtocolUnavailableError
3. If protocol == "mcp" → use MCP path directly
4. Any other value → log error, raise ValueError("unsupported protocol: ...")
```

**Key principle:** Protocol selection is **explicit and logged**. No silent switching.

### 3.3 Session Lifecycle (Fixed)

```
Current (BUGGY):
  1. Agent calls _bridge._create_session_id() → "hermes_abc123"
  2. Agent calls create_worker_session(env) → server returns "hermes_xyz789"
  3. Agent uses "hermes_abc123" for all operations
  4. close_worker_session("hermes_abc123") → looks up wrong key → fails

Fixed:
  1. Agent calls create_worker_session(env) → returns "hermes_xyz789"
  2. Agent uses "hermes_xyz789" for all operations
  3. close_worker_session("hermes_xyz789") → finds key, closes correctly
```

### 3.4 Provenance Flow

Every `HermesObservation.provenance` MUST contain:
```python
{
    "task_id": "<caller-provided>",
    "execution_id": str(uuid.uuid4()),        # unique per execute_task call
    "session_id": "<hermes-side session>",     # from create_worker_session return
    "correlation_id": str(uuid.uuid4()),       # links request → response
    "protocol": "acp" | "mcp" | "acp_fallback",
    "adapter": "acp_adapter" | "mcp_manager",
    "timestamp": "<ISO 8601 UTC>",
    "request_metadata": {
        "task_type": "<...>",
        "description": "<truncated to 200 chars>",
        "parameters_hash": "<sha256 of parameters>",  # no secrets
    },
    "target": {"server_id": "<...>"},
    "exit_status": "completed" | "cancelled" | "error" | "timeout",
    "errors": [],                              # non-fatal warnings
    "environment": "<...>",                    # session environment overlay
}
```

### 3.5 Error Classification

| Error | Retryable | Fallback | Observation |
|-------|-----------|----------|-------------|
| ProtocolUnavailableError | No | Conditional | N/A (raised) |
| TransportConnectionError | Yes (max 3) | Yes | N/A (raised) |
| SessionCreationTimeout | Yes (once) | Yes | N/A (raised) |
| SessionNotFoundError | No | No | success=False |
| ExecutionTimeout | Yes (once) | Yes | success=False, error="timeout" |
| ExecutionCancelled | No | No | success=False, error="cancelled" |
| MalformedResponseError | No | No | success=False, error="malformed" |
| TransportDisconnectError | Yes (max 3) | Yes | N/A (raised) |
| CleanupTimeout | No | No | Log warning, observation still returned |
| DuplicateExecutionError | No | No | SECURITY-CRITICAL, raised |
| SecretLeakDetectedError | No | No | SECURITY-CRITICAL, raised |

---

## 4. FILE-LEVEL CHANGE PLAN

### 4.1 NEW: `src/aios/adapters/acp_adapter.py`

**Purpose:** ACP stdio transport layer for hermes-agent.

**Changes:** Create from scratch.

**Why necessary:** ACP is the preferred protocol; no ACP client code exists in AI-OS yet.

**Dependencies:** `acp` SDK (optional at import time, deferred import), `asyncio`, `uuid`, `hashlib`, `logging`.

**Interface:**
```python
class AcPAdapter:
    def __init__(
        self,
        cwd: str,
        timeout_seconds: int = 30,
        allowed_root: str | None = None,
        env_scrub_patterns: tuple[str, ...] | None = None,
    ) -> None: ...

    async def connect(self) -> bool:
        """Launch hermes-agent subprocess, complete ACP initialize handshake."""

    async def disconnect(self) -> None:
        """Terminate subprocess."""

    async def new_session(self, cwd: str) -> str:
        """Create ACP session. Returns session_id (UUID)."""

    async def prompt(self, session_id: str, text: str, timeout: float) -> dict[str, Any]:
        """Send prompt, return raw ACP response dict."""

    async def cancel(self, session_id: str) -> None:
        """Cancel in-flight prompt for session."""

    async def close_session(self, session_id: str) -> None:
        """Close ACP session."""

    def is_connected(self) -> bool: ...
```

**Implementation notes:**
- Use `asyncio.create_subprocess_exec` to launch `python -m acp_adapter.entry` from hermes-agent repo
- Scrub env vars matching `(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)` before passing to subprocess
- Validate `cwd` is under `allowed_root` if set
- Defer `import acp` to runtime (not module scope) — catch `ModuleNotFoundError`
- If `acp` SDK not available, raise `ProtocolUnavailableError`
- Use `acp.run_agent()` pattern from hermes-agent tests for client connection

### 4.2 NEW: `src/aios/adapters/acp_session.py`

**Purpose:** Session registry with timeout, isolation validation, and cleanup.

**Changes:** Create from scratch.

**Why necessary:** Centralizes session lifecycle management; prevents cross-session leakage.

**Dependencies:** `acp_adapter.py`, `asyncio`, `uuid`.

**Interface:**
```python
class AcPSessionRegistry:
    def __init__(self, adapter: AcPAdapter) -> None: ...

    async def create(self, cwd: str, timeout_seconds: int) -> str:
        """Create session, register, return session_id."""

    async def close(self, session_id: str) -> None:
        """Close session, unregister. Double-close is no-op."""

    def is_active(self, session_id: str) -> bool: ...

    def get_active(self) -> list[str]: ...

    async def cleanup_all(self) -> None:
        """Close all active sessions."""
```

### 4.3 MODIFIED: `src/aios/adapters/hermes_bridge.py`

**Purpose:** Add ACP support, fix session lifecycle, enhance provenance.

**Changes:**
1. Add `protocol: str = "acp"` and `fallback_to_mcp: bool = True` to `__init__`
2. Accept optional `acp_adapter` parameter (for test injection)
3. Implement protocol selection logic
4. Wire `AcPAdapter` for ACP path
5. Fix `create_worker_session` to store and return the **server-generated** session ID
6. Extend provenance with: `protocol`, `execution_id`, `correlation_id`, `exit_status`, `adapter`
7. Add `_normalize_acp_response()` and `_normalize_mcp_response()` methods
8. Add `_scrub_env()` method for secret removal
9. Add `_hash_parameters()` for provenance-safe parameter representation
10. Add error classification helpers

**Why necessary:** Core M8-T1 deliverable; fixes DEF-001 session lifecycle bug.

**Dependencies:** `acp_adapter.py`, `mcp_manager.py` (existing).

**Must NOT change:**
- `HermesTask` dataclass fields
- `HermesObservation` dataclass fields (only extend `provenance` dict)
- Method signatures (except adding optional params with defaults)
- Public interface contract

### 4.4 MODIFIED: `src/aios/core/user_simulation_agent.py`

**Purpose:** Fix session-ID lifecycle bug (DEF-002) and provenance drop (DEF-003).

**Changes:**
1. Line 151: Replace `session_id = self._bridge._create_session_id()` with:
   ```python
   session_id = await self._bridge.create_worker_session(environment={"app_url": app_url})
   ```
2. Line 166: Remove the separate `create_worker_session` call (now done above)
3. Lines 169-197: Use the consumed `session_id` (already correct)
4. Line 298-306 (`_obs_to_dict`): Add `"provenance": o.provenance`

**Why necessary:** Fixes two defects that break even the current mock path.

**Must NOT change:**
- Constructor signature
- `simulate()` signature
- INV-008 defense-in-depth logic
- Return type (`UserSimulationCompleted`)

### 4.5 NEW: `src/aios/adapters/mock_hermes_acp_server.py`

**Purpose:** Minimal ACP-compliant mock server for integration testing without real hermes-agent.

**Changes:** Create from scratch.

**Why necessary:** Tests need a real ACP protocol round-trip without requiring hermes-agent installation.

**Behavior:**
- Implements ACP stdio JSON-RPC protocol (initialize, session/new, session/prompt, session/cancel, session/close)
- In-memory session store (like existing mock_hermes_server)
- Returns deterministic responses for testing
- Supports `HERMES_MOCK_ACP=1` env flag for enabling

### 4.6 MODIFIED: `src/aios/adapters/mock_hermes_server.py`

**Purpose:** Add missing `create_session` and `close_session` tools that the bridge currently calls.

**Changes:**
- Add `create_session` tool to the tools list
- Add `close_session` tool to the tools list
- Add `execute_task` tool to the tools list
- These tools are called by the existing bridge but don't exist on the mock — causing silent failures

**Why necessary:** The existing bridge already calls these tools; the mock was incomplete.

### 4.7 MODIFIED: `config/defaults.yaml`

**Purpose:** Add Hermes ACP configuration section.

**Changes:** Add:
```yaml
hermes:
  protocol: "acp"           # acp | mcp
  cwd: ""                   # path to hermes-agent repo root; empty = auto-detect
  timeout_seconds: 30
  retry_attempts: 3
  fallback_to_mcp: true     # only when ACP requested but unavailable
  allowed_root: ""          # if set, restrict subprocess cwd underneath
  session_idle_timeout_seconds: 300
```

### 4.8 MODIFIED: `pyproject.toml`

**Purpose:** Fix psutil dependency issue (DEF-005).

**Changes:**
- Add `"psutil>=5.9"` to `[project.optional-dependencies.dev]`
- Also add to `[project.optional-dependencies.test]` if that section exists

**Why necessary:** `test_memory_bounded_under_load` requires psutil; undeclared dependency causes CI failure.

### 4.9 MODIFIED: `tests/performance/test_structured_logger_perf.py`

**Purpose:** Guard psutil import with `pytest.importorskip`.

**Changes:**
```python
# Before:
import psutil  # type: ignore

# After:
psutil = pytest.importorskip("psutil")
```

**Why necessary:** Test should skip gracefully when psutil not installed, not fail with ModuleNotFoundError.

### 4.10 NEW: `tests/unit/test_acp_adapter.py`

**Purpose:** Unit tests for AcPAdapter (11 tests).

**Why necessary:** Verify ACP protocol framing, timeout, cancel, env scrubbing, session lifecycle.

### 4.11 NEW: `tests/unit/test_hermes_bridge_acp.py`

**Purpose:** Unit tests for HermesBridge protocol selection and provenance (11 tests).

**Why necessary:** Verify ACP preference, MCP fallback, session ID lifecycle fix, provenance completeness, no verdict leakage.

### 4.12 NEW: `tests/integration/test_m8_hermes_acp.py`

**Purpose:** Integration tests for ACP + MCP paths (9 tests).

**Why necessary:** End-to-end protocol verification with real mock servers.

### 4.13 MODIFIED: `tests/unit/test_user_simulation_agent.py`

**Purpose:** Update for fixed session lifecycle; add provenance test.

**Changes:**
- Adjust `FakeHermesBridge` to match new session lifecycle (no more `_create_session_id()` call from agent)
- Add test for provenance inclusion in `_obs_to_dict`

---

## 5. TEST PLAN

### 5.1 Unit Tests — `test_acp_adapter.py` (11 tests)

| Test | Scenario |
|------|----------|
| `test_connect_success` | Subprocess launches, ACP handshake completes |
| `test_connect_acp_not_installed` | `ModuleNotFoundError` → raises `ProtocolUnavailableError` |
| `test_connect_process_not_found` | Missing hermes-agent → raises `ProtocolUnavailableError` |
| `test_new_session_returns_uuid` | Returns non-empty UUID string |
| `test_new_session_timeout` | Exceeds timeout → raises `SessionCreationTimeout` |
| `test_prompt_success` | Returns dict with `stop_reason="end_turn"` and text |
| `test_prompt_timeout` | Exceeds per-prompt timeout → raises `ExecutionTimeout` |
| `test_cancel_unknown_session` | `cancel()` on unknown ID → raises `SessionNotFoundError` |
| `test_close_session_double_close` | Double-close is no-op, not error |
| `test_scrubs_secrets_in_env` | `API_KEY=secret` removed before subprocess launch |
| `test_validates_cwd` | `new_session(cwd="/etc")` raises if not under `allowed_root` |

### 5.2 Unit Tests — `test_hermes_bridge_acp.py` (11 tests)

| Test | Scenario |
|------|----------|
| `test_protocol_selection_acp_preferred` | `protocol="acp"`, ACP available → provenance says `"acp"` |
| `test_protocol_selection_mcp_explicit` | `protocol="mcp"` → provenance says `"mcp"` |
| `test_fallback_acp_unavailable_mcp_used` | ACP unavailable + `fallback=True` → provenance says `"acp_fallback"` |
| `test_no_fallback_acp_unavailable_raises` | ACP unavailable + `fallback=False` → raises `ProtocolUnavailableError` |
| `test_create_worker_session_tracks_id` | Return value stored in active dict; subsequent calls use it |
| `test_close_worker_session_removes_id` | Session removed from active dict after close |
| `test_provenance_complete` | Every observation has all mandatory provenance fields |
| `test_provenance_no_secrets` | Provenance dict contains no plaintext secrets |
| `test_normalize_acp_stop_reason` | `"end_turn"` → success=True; `"cancelled"` → success=False |
| `test_error_wraps_as_observation` | Exception during execute → HermesObservation(success=False) |
| `test_observe_not_verdict` | Result data contains no forbidden words |

### 5.3 Integration Tests — `test_m8_hermes_acp.py` (9 tests)

| Test | Scenario |
|------|----------|
| `test_acp_mock_server_roundtrip` | Extended mock speaks ACP; connect → session → prompt → close |
| `test_mcp_fallback_path` | Explicit `protocol="mcp"` through mock MCP server |
| `test_session_isolation` | Two concurrent sessions; no cross-contamination |
| `test_correlation_id_traceability` | Request → response correlation via provenance.correlation_id |
| `test_cleanup_on_exception` | `execute_task` raises; `close_worker_session` still succeeds |
| `test_timeout_execution` | Mock server sleeps > timeout; observation records timeout |
| `test_disconnected_server` | Server dies mid-session; next call raises TransportDisconnectError |
| `test_concurrent_sessions` | 5 concurrent sessions; all isolated; all cleaned up |
| `test_real_hermes_acp` | If `HERMES_ACP_TEST=1` env set, launch real hermes-agent ACP adapter |

### 5.4 Regression Tests

Must pass after every phase:
- `tests/integration/test_m7_security.py` (13 tests)
- `tests/unit/test_user_simulation_agent.py` (5→7 tests after update)
- `tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load`
- Full suite `pytest tests/ -q` (expect 1046 + 33 = 1079)

### 5.5 Negative Tests (Hermes must NOT be able to)

| Test | Forbidden Behavior |
|------|-------------------|
| `test_hermes_cannot_produce_verdict` | Observation has no `verdict`/`pass`/`fail`/`approved` |
| `test_hermes_cannot_bypass_verification` | `trust_level` always `"untrusted"` |
| `test_hermes_cannot_mutate_protected_state` | No writes to kernel state |
| `test_hermes_cannot_access_secrets` | Provenance excludes API keys |
| `test_malformed_response_does_not_crash` | Bad JSON → error observation, not exception |
| `test_duplicate_execution_detected` | Two prompts same session before close → error |

---

## 6. PSUTIL FIX

### 6.1 Recommended Approach

**Both** changes are required (complementary, not alternative):

1. **Declare `psutil` in `pyproject.toml`** dev dependencies:
   ```toml
   [project.optional-dependencies.dev]
   psutil>=5.9
   ```
   This ensures anyone installing dev dependencies gets psutil.

2. **Guard the import in the test** with `pytest.importorskip`:
   ```python
   psutil = pytest.importorskip("psutil")
   ```
   This ensures the test **skips gracefully** in environments where psutil is not installed (CI, fresh checkout), rather than failing with `ModuleNotFoundError`.

### 6.2 Why This Matches Repository Conventions

- The project already uses `pytest.importorskip` patterns elsewhere
- `pyproject.toml` declares all test-time dependencies
- Other performance tests don't import third-party libs at module scope
- The existing pattern in the file (`import psutil  # type: ignore`) was clearly an oversight

---

## 7. SECURITY / FAILURE ANALYSIS

### 7.1 Protocol Failures

| Failure Mode | Detection | Handling |
|-------------|-----------|----------|
| ACP handshake timeout | `asyncio.wait_for` around initialize | Raise `SessionCreationTimeout` |
| MCP connection lost | `MCPManager` already handles disconnect | Re-connect or raise `TransportDisconnectError` |
| Unknown ACP method | JSON-RPC error response | Log warning, raise `MalformedResponseError` |
| Subprocess crash | `process.wait()` non-zero exit | Raise `TransportDisconnectError` |

### 7.2 Malformed Responses

- All responses parsed with `json.loads()` inside `try/except json.JSONDecodeError`
- Missing required fields → `MalformedResponseError` (non-retryable)
- Extra fields → ignored (forward-compatible)
- Empty responses → `MalformedResponseError`

### 7.3 Timeout Behavior

- Connection timeout: `config.hermes.timeout_seconds` (default 30s)
- Per-prompt timeout: configurable, default 60s
- On timeout: `HermesObservation(success=False, error="timeout", exit_status="cancelled")`
- Timeout does NOT leak state — session remains active for potential retry

### 7.4 Stale Sessions

- Bridge validates session_id against `_active_sessions` dict before every call
- Unknown session_id → `SessionNotFoundError` (raised, not swallowed)
- `close_worker_session` on unknown session → logs warning, returns False (not error)
- Double-close → no-op (idempotent)

### 7.5 State Leakage Risks

| Risk | Mitigation |
|------|------------|
| Cross-session contamination | Each `create_worker_session` creates isolated ACP session; bridge validates ownership |
| Environment variable leakage | `_scrub_env()` removes `API_KEY*`, `SECRET*`, `TOKEN*`, `PASSWORD*`, `CREDENTIAL*` |
| Provenance secret leakage | Parameters hashed with SHA-256; raw values never in provenance |
| Large artifact leakage | Screenshots/binaries referenced by key, not embedded |
| Process persistence | `disconnect()` calls `process.terminate()` + `await process.wait()` |

### 7.6 Authority Leakage

- `HermesObservation.trust_level` is ALWAYS `"untrusted"` — cannot be overridden
- No verdict/pass/fail/approved/rejected/secure/compliant words in observation construction paths
- Bridge does NOT call SecurityManager, CouncilManager, StateManager, or any kernel state mutator
- All observations flow through `TestOrchestratorService.normalize_evidence` before becoming evidence

### 7.7 Retry Hazards

- Max retries: `config.hermes.retry_attempts` (default 3)
- Exponential backoff, capped at 5s
- Each retry gets a new `execution_id` in provenance
- Non-retryable errors (ProtocolUnavailableError, MalformedResponseError) bypass retry

---

## 8. BACKWARD COMPATIBILITY

### 8.1 Existing Callers

- `kernel.py:821-825`: `HermesBridge(mcp_manager=..., server_id="hermes_agent_ext")` — still works; new params have defaults
- `UserSimulationAgent`: After DEF-002 fix, session lifecycle is corrected but the public API is unchanged
- All 9 agency adapters: Unaffected (they use `base.py`, not HermesBridge)

### 8.2 Existing Adapters

- `agent_reach.py`, `security_agency_adapter.py`, etc.: Unchanged
- `mock_hermes_server.py`: Extended (not replaced) — existing MCP tools still work

### 8.3 MCP Behavior

- MCP path preserved exactly as-is
- `MCPManager` unchanged
- Existing `config/mcp/hermes_agent_ext_mcp.json` still works
- `mock_hermes_server.py` extended with missing tools (`create_session`, `close_session`, `execute_task`)

### 8.4 Existing Tests

- All 1046 existing tests must pass
- `test_user_simulation_agent.py` updated for session lifecycle fix (behavior-preserving)
- `test_m7_security.py` must still pass (13 tests)
- `test_memory_bounded_under_load` must pass or skip (not fail)

---

## 9. M8-T1 ACCEPTANCE CRITERIA

### ACP
- [ ] `HermesBridge` supports ACP protocol (`protocol="acp"` is default)
- [ ] ACP connection established with local hermes-agent subprocess (via mock or real)
- [ ] Session lifecycle works: `create_worker_session` returns ID that subsequent calls use
- [ ] Real execution path works through ACP (verified via mock ACP server or `HERMES_ACP_TEST=1`)
- [ ] Cleanup works: session removed from active set, subprocess terminated

### MCP
- [ ] MCP fallback controlled by `fallback_to_mcp` config flag
- [ ] Fallback is explicit: provenance records `"acp_fallback"` not `"mcp"`
- [ ] Direct MCP path works: provenance records `"mcp"`

### Isolation
- [ ] Sessions isolated: concurrent sessions don't share state
- [ ] Correlation IDs correct and traceable in provenance
- [ ] No cross-task contamination (verified by concurrent session test)

### Evidence
- [ ] Observations provenance-complete (all 13 mandatory fields present)
- [ ] Raw execution traceable back to request via `correlation_id`
- [ ] Normalization deterministic (same input → same output shape)
- [ ] No unsupported claims in observation (no verdict/pass/fail)

### Authority
- [ ] Hermes cannot declare AI-OS verdicts (negative tests pass)
- [ ] Hermes cannot bypass verification (`trust_level` always `"untrusted"`)
- [ ] Hermes cannot access secrets (provenance excludes API keys)

### Reliability
- [ ] Timeout handling works (connection, session, execution)
- [ ] Cancellation propagates to subprocess
- [ ] Disconnect handled gracefully
- [ ] Retry/fallback behavior correct per error classification
- [ ] Cleanup on exception path works

### Security
- [ ] No secret leakage in provenance or logs
- [ ] Subprocess env scrubbed (no API_KEY/SECRET/TOKEN/PASSWORD/CREDENTIAL)
- [ ] Session boundaries maintained under concurrency

### Testing
- [ ] All unit tests pass (`test_acp_adapter.py`, `test_hermes_bridge_acp.py`)
- [ ] M8 integration tests pass (`test_m8_hermes_acp.py`)
- [ ] Regression: 1046 existing tests pass
- [ ] M7 regression: 18 tests pass (13 security + 5 user_sim)
- [ ] `test_memory_bounded_under_load` passes or skips (not fails)

### Dependency
- [ ] `psutil` declared in `pyproject.toml` dev deps
- [ ] `pytest.importorskip("psutil")` used in performance test

---

## 10. IMPLEMENTATION ORDER

**Terminal 2 should follow this exact sequence:**

### Step 1: Dependency hygiene (5 min)
1. Add `psutil>=5.9` to `[project.optional-dependencies.dev]` in `pyproject.toml`
2. Replace `import psutil  # type: ignore` with `psutil = pytest.importorskip("psutil")` in `tests/performance/test_structured_logger_perf.py`
3. Verify: `pytest tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load -v` → PASS or SKIP

### Step 2: Extend mock server (10 min)
4. Add `create_session`, `close_session`, `execute_task` tools to `mock_hermes_server.py`
5. Verify existing tests still pass

### Step 3: Create ACP mock server (20 min)
6. Create `src/aios/adapters/mock_hermes_acp_server.py` — minimal ACP stdio server
7. Supports: `initialize`, `session/new`, `session/prompt`, `session/cancel`, `session/close`
8. In-memory session store; deterministic responses
9. Enables via `HERMES_MOCK_ACP=1` env flag

### Step 4: Implement AcPAdapter (30 min)
10. Create `src/aios/adapters/acp_adapter.py`
11. Subprocess management for hermes-agent
12. Deferred `import acp` (catch `ModuleNotFoundError`)
13. `connect()`, `disconnect()`, `new_session()`, `prompt()`, `cancel()`, `close_session()`
14. Env scrubbing, cwd validation
15. Error classification

### Step 5: Implement AcPSessionRegistry (15 min)
16. Create `src/aios/adapters/acp_session.py`
17. Session registry with timeout, isolation validation
18. Double-close idempotency

### Step 6: Update HermesBridge (30 min)
19. Modify `src/aios/adapters/hermes_bridge.py`:
    - Add `protocol`, `acp_adapter`, `fallback_to_mcp` params
    - Protocol selection logic
    - Fix `create_worker_session` to use returned session ID
    - Add `_normalize_acp_response()`, `_normalize_mcp_response()`
    - Extend provenance with 5 new fields
    - Add `_scrub_env()`, `_hash_parameters()`
20. Verify: existing tests still pass

### Step 7: Fix UserSimulationAgent (10 min)
21. Modify `src/aios/core/user_simulation_agent.py`:
    - Line 151: Use `await self._bridge.create_worker_session(...)` and consume return
    - Line 166: Remove duplicate `create_worker_session` call
    - Line 298-306: Add `"provenance": o.provenance` to `_obs_to_dict`
22. Update `tests/unit/test_user_simulation_agent.py` for new session lifecycle

### Step 8: Add config (5 min)
23. Update `config/defaults.yaml` with `hermes:` section

### Step 9: Write unit tests (30 min)
24. Create `tests/unit/test_acp_adapter.py` (11 tests)
25. Create `tests/unit/test_hermes_bridge_acp.py` (11 tests)

### Step 10: Write integration tests (30 min)
26. Create `tests/integration/test_m8_hermes_acp.py` (9 tests)

### Step 11: Regression (15 min)
27. Run full suite: `pytest tests/ -q` → expect 1079 passed, 0 failed
28. Run M7 regression: `pytest tests/integration/test_m7_security.py tests/unit/test_user_simulation_agent.py -v` → 18 passed
29. Verify no forbidden words in bridge code: `grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/hermes_bridge.py src/aios/adapters/acp_adapter.py`

---

## 11. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation | Verification |
|------|-----------|--------|------------|-------------|
| `acp` SDK not installable in test env | **High** | Tests block | Defer import to runtime; unit tests use in-memory stdio mock; gate real-ACP tests behind `HERMES_ACP_TEST=1` | Unit tests pass without `acp` installed |
| hermes-agent subprocess startup slow (>30s) | **Medium** | CI timeout | Configurable timeout; integration tests use mock by default | Mock tests complete in <5s |
| ACP stdio framing complexity | **Medium** | Bugs in transport | Start with thin wrapper; add integration tests early; use hermes-agent's own test patterns as reference | `test_acp_adapter.py` covers framing |
| Session ID lifecycle regression | **Medium** | Existing UserSim breaks | Fix `user_simulation_agent.py` as part of T1; add regression test | `test_user_simulation_agent.py` passes |
| hermes-agent repo layout changes | **Low** | `cwd`/command path breaks | Document exact path resolution; allow `hermes.cwd` config override | Config test covers path resolution |
| Mock ACP server insufficient for E2E | **Medium** | Coverage gap | Build `mock_hermes_acp_server.py` with minimal ACP conformance | Integration tests use mock |
| Provenance schema drift | **Low** | Audit failure | Lock provenance fields in spec; enforce with tests | `test_provenance_complete` asserts all fields |
| Breaking existing MCP-only tests | **Low** | Regression | Protocol selection is opt-in; MCP path unchanged | Full regression suite green |

---

## 12. FUTURE COMPATIBILITY

### 12.1 Councils
- ACP adapter does not reference any council system
- Observations flow through existing `TestOrchestratorService.normalize_evidence`
- Future LLM Council / Review Council can consume `HermesObservation` without bridge changes

### 12.2 Reviewing
- Bridge returns observations only; review council operates on normalized evidence
- No hard-coding of review logic in bridge

### 12.3 Testing
- `TestOrchestratorService` unchanged
- `HermesObservation` shape unchanged (only provenance dict extended)
- `TestingEvidence` schema compatible

### 12.4 Learning
- `LearningService` (M9) will consume evidence, not bridge output directly
- Bridge provenance provides sufficient audit trail for lesson extraction

### 12.5 Autonomy/Escalation
- Bridge does not implement autonomy or escalation logic
- Observations flow up through existing verification pipeline
- No authority leakage possible (enforced by `trust_level="untrusted"`)

### 12.6 Code Simplification
- Future simplification gate operates on normalized evidence, not raw observations
- Bridge provenance completeness supports traceability through simplification

### 12.7 Future External Integrations
- Adapter pattern (`AcPAdapter` internal, `HermesBridge` external-facing) allows future ACP providers
- Protocol selection policy is config-driven, not hardcoded
- No external repository names hardcoded in AI-OS kernel

---

## 13. DO-NOT-IMPLEMENT LIST

**Explicitly OUT OF SCOPE for M8-T1:**

| Item | Belongs To |
|------|-----------|
| Graphify MCP connection | M8-T2 |
| Playwright MCP integration | M8-T3 |
| Feature flags for optional integrations (beyond `fallback_to_mcp`) | M8-T4 |
| E2E tests with real external services (beyond mock + `HERMES_ACP_TEST`) | M8-T5 |
| Independent QA report | M8-T6 |
| LearningService implementation | M9 |
| ModelRouter real integration | M9 |
| Deployment/Docker/health checks | M10 |
| Security hardening (provenance signing, etc.) | M11 |
| Complete documentation closure | M12 |
| Full-system validation | Post-M12 |
| ACP-over-network transport (HTTP/SSE/WebSocket) | Future |
| ACP session persistence/resumption | Future |
| Multi-hermes-agent load balancing | M10 |
| Prometheus/OpenTelemetry metrics export | M10 |
| Refactor TestOrchestratorService | Forbidden |
| Refactor CouncilManager/FinalJudgeAgency | Forbidden |
| Refactor SecurityManager | Forbidden |
| Add new managers to kernel | Forbidden |
| Change MCPManager | Forbidden |
| Change workflow.py | Forbidden |
| Change any agency adapter | Forbidden |
| Import `acp` at module scope in `hermes_bridge.py` | Forbidden |
| Make `mock_hermes_server.py` speak ACP (use separate mock) | Forbidden |
| Increase baseline test failure rate | Forbidden |

---

## 14. FINAL M8-T1 VERDICT

### **READY FOR IMPLEMENTATION**

**No blockers.** All prerequisites verified:
- M7 complete (95/100, 1046 tests passing)
- Repository inspection complete
- Gap analysis complete
- Architecture validated against existing codebase
- Implementation specification detailed enough for Terminal 2 to execute without further clarification
- All defects (DEF-001 through DEF-005) identified and mapped to fixes
- Test coverage plan accounts for all requirements
- Backward compatibility preserved
- Security boundaries maintained
- Future compatibility ensured

**One conditional note:** Real ACP E2E testing requires `agent-client-protocol` SDK and hermes-agent to be installed. These are gated behind `HERMES_ACP_TEST=1` env flag. Standard CI runs mock-based tests only. Terminal 2 should NOT attempt to install hermes-agent as a dependency — it remains an external gitignored repo.

---

## TERMINAL 2 IMPLEMENTATION PROMPT

```
Execute M8-T1: Hermes ACP Protocol Integration

READ THESE FILES FIRST (in order):
1. src/aios/adapters/hermes_bridge.py (current implementation)
2. src/aios/adapters/mock_hermes_server.py (existing mock)
3. src/aios/core/user_simulation_agent.py (DEF-002, DEF-003)
4. src/aios/core/kernel.py lines 815-835 (wiring context)
5. src/aios/adapters/agent_reach.py (adapter pattern reference)
6. config/defaults.yaml (currently empty)
7. pyproject.toml (dependency declaration pattern)
8. tests/unit/test_user_simulation_agent.py (existing tests to update)
9. tests/performance/test_structured_logger_perf.py (psutil fix)
10. architecture/Part15/M8/M8-T1-Hermes-ACP-Protocol.md (detailed spec)

THEN FOLLOW THIS EXACT SEQUENCE:

STEP 1: Fix psutil (pyproject.toml + test guard)
STEP 2: Extend mock_hermes_server.py with create_session/close_session/execute_task tools
STEP 3: Create mock_hermes_acp_server.py (minimal ACP stdio mock)
STEP 4: Create acp_adapter.py (ACP transport layer)
STEP 5: Create acp_session.py (session registry)
STEP 6: Update hermes_bridge.py (ACP support + session fix + provenance)
STEP 7: Fix user_simulation_agent.py (DEF-002 + DEF-003)
STEP 8: Update config/defaults.yaml
STEP 9: Write test_acp_adapter.py (11 tests)
STEP 10: Write test_hermes_bridge_acp.py (11 tests)
STEP 11: Write test_m8_hermes_acp.py (9 tests)
STEP 12: Update test_user_simulation_agent.py
STEP 13: Run full regression: pytest tests/ -q
STEP 14: Run M7 regression: pytest tests/integration/test_m7_security.py tests/unit/test_user_simulation_agent.py -v
STEP 15: Verify: grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/hermes_bridge.py src/aios/adapters/acp_adapter.py → zero matches

CRITICAL CONSTRAINTS:
- Do NOT change HermesObservation dataclass fields
- Do NOT change UserSimulationCompleted dataclass fields
- Do NOT change kernel.py wiring
- Do NOT import acp at module scope
- Do NOT modify mcp_manager.py, kernel.py, any agency adapter
- Do NOT add new EventType values
- All new tests must use real protocol round-trips (not hardcoded mock returns)
- Regression must stay at 0 failures
```

---

*End of M8-T1 Implementation Specification.*
