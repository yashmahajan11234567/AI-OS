# M8-T1 — Wire Hermes ACP Protocol

**Milestone:** M8 — Production Integration  
**Task:** T1 — Hermes ACP Protocol  
**Mode:** Architecture / Implementation Plan  
**Current Checkpoint:** POST-M7 — M7 COMPLETE / GO  
**Plan Date:** 2026-08-25  
**Status:** DRAFT — PENDING IMPLEMENTATION (Terminal 2)

---

## Document Control

| Field | Value |
|-------|-------|
| Plan Version | 1.0 |
| Authoritative Source | `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md` §42 and §1720–§1763 |
| Repository Truth | `src/aios/adapters/hermes_bridge.py`, `hermes-agent/acp_adapter/server.py`, `hermes-agent/acp_adapter/entry.py`, `hermes-agent/acp_adapter/provenance.py` |
| External Repo | `hermes-agent/` — **INTEGRATION + REFERENCE** (gitignored, on-disk, NOT AI-OS-owned) |
| Status | DRAFT |

---

## 1. Executive Summary

M8-T1 upgrades the Hermes integration so that **ACP becomes the preferred execution protocol** and MCP becomes an explicit fallback. The current state is:

- `HermesBridge` exists but is **MCP-only today** (docstring: "Supports ACP upgrade later").
- No source file imports `acp` (the `agent-client-protocol` package) — ACP wiring is entirely new code in AI-OS.
- `UserSimulationAgent` calls `_bridge._create_session_id()` and passes that ID to methods, but `create_worker_session()` **returns an unrelated server-generated ID and the caller discards it** — this is a defect even under the current mock.
- `mock_hermes_server.py` offers MCP tools (`browser_navigate`, `browser_click`, …); it does not speak ACP.
- `config/mcp/hermes_agent_ext_mcp.json` launches the mock; `config/mcps.yaml` is empty.
- Kernel wires the bridge via `HermesBridge(mcp_manager=None, server_id="hermes_agent_ext")` (the `_mcp_manager` attribute does not exist on the kernel instance; the `hasattr` guard at `kernel.py:822` confirms this).

The work for M8-T1 is bounded to:
1. An **ACP transport adapter** inside `src/aios/adapters/` that can drive a local hermes-agent process over stdio using the `acp` SDK.
2. An **ACP-first / MCP-fallback policy** in `HermesBridge`.
3. Provenance completion: every `HermesObservation` must record the protocol actually used.
4. The known **psutil test-hygiene fix** (`test_memory_bounded_under_load`).
5. Unit + integration tests covering ACP primary, MCP fallback, session isolation, provenance completeness, failure behavior, and regression.

**Invariants that MUST NOT change:** Hermes remains an external untrusted worker; Hermes returns **observations only**, never verdicts; AI-OS retains final authority; the existing `HermesObservation` / `Provenance` / `TestingEvidence` data models remain compatible; kernel wiring in `_init_m7_testing` is preserved.

---

## 2. Current Implementation (Inspection Findings)

### 2.1 `src/aios/adapters/hermes_bridge.py` (310 lines)

- Dataclasses: `HermesTask`, `HermesObservation`.
- `HermesBridge`:
  - `__init__(mcp_manager=None, server_id="hermes_agent_ext")` — accepts an optional MCP manager (currently unused by the kernel).
  - `_ensure_connected()` → delegates to MCP manager.
  - `_create_session_id()` → `f"hermes_{uuid.uuid4().hex[:12]}"`.
  - `_create_provenance(task, extra)` → builds a provenance dict with `session_id`, `worker`, `server`, `timestamp`, `environment`, `interaction`, `source`, `task_id`.
  - `create_worker_session(environment)` → calls MCP `create_session` tool, stores result keyed by the **MCP-returned** session ID, not the caller's pre-generated ID.
  - `close_worker_session(session_id)` → calls MCP `close_session`.
  - `execute_task(task)` → calls MCP `execute_task`; wraps any exception in a failed observation.
  - Convenience methods: `navigate`, `click`, `type_text`, `screenshot`, `extract_content`, `wait_for`.
  - `is_session_active(session_id)`, `get_active_sessions()`.
- **Gap:** `_create_session_id` and `create_worker_session` are not synchronized — the caller's generated ID is thrown away, and `close_worker_session` would look up a key never inserted.

### 2.2 `src/aios/core/user_simulation_agent.py` (307 lines)

- Constructor takes `HermesBridge`.
- `simulate(app_url, user_goal, exploration_brief, *, correlation_id=None)` → `UserSimulationCompleted`.
- **Defect:** line 151 calls `self._bridge._create_session_id()` and uses that ID as `session_id`. But line 166 calls `await self._bridge.create_worker_session(environment={...})` and ignores the returned session ID. The actual remote session is created with a different ID; cleanup on line 197 uses the *caller's* ID which never existed on the remote side.
- `_obs_to_dict` drops `provenance` — the returned `raw_trace.observations[i]` lacks provenance fields.
- Defense-in-depth INV-008 is preserved (no `source_code` parameter).

### 2.3 `src/aios/core/kernel.py` (line ~821)

```python
hermes_bridge = HermesBridge(
    mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
    server_id="hermes_agent_ext",
)
self._user_simulation_agent = UserSimulationAgent(hermes_bridge)
```

`self._mcp_manager` does not exist — `_mcp_manager` is assigned nowhere on `Kernel`. The condition is a defensive no-op. The bridge always receives `mcp_manager=None`.

### 2.4 `src/aios/adapters/mock_hermes_server.py` (331 lines)

- Pure-MCP stdio server simulating browser/worker actions.
- Tools: `browser_navigate`, `browser_click`, `browser_type`, `browser_extract`, `browser_screenshot`, `worker_execute`.
- **Does not speak ACP.**

### 2.5 `config/mcp/hermes_agent_ext_mcp.json`

- stdio transport pointing to `python -m aios.adapters.mock_hermes_server`.

### 2.6 Test baseline

- Full suite: **1046 passed** (matching the stated baseline).
- M7 security + user_sim unit tests: **13 passed** in 0.20s.
- `test_memory_bounded_under_load` passes when `psutil 7.2.2` is installed but is **not declared** in `pyproject.toml`.

---

## 3. Current Hermes Architecture

```
AI-OS Kernel
  └─ _init_m7_testing()
       ├─ TestOrchestratorService (council, gate, judge, etc.)
       └─ HermesBridge(mcp_manager=None, server_id="hermes_agent_ext")
            └─ MCPManager (global singleton)
                 └─ config/mcp/hermes_agent_ext_mcp.json
                      └─ subprocess: python -m aios.adapters.mock_hermes_server
```

No direct call from AI-OS code imports `acp`. `hermes-agent/` is gitignored but present on disk and can be launched as a separate stdio process.

---

## 4. ACP Requirements

Per `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md` §42 (§1720–§1763):

1. Read `src/aios/adapters/hermes_bridge.py` (done — this doc).
2. Read `hermes-agent/acp_adapter/` (done — inspected all 11 modules).
3. Upgrade `HermesBridge` to support ACP (preferred) with MCP fallback.
4. Add ACP session management (isolated `hermes_<uuid>` sessions).
5. Ensure `HermesObservation` still returns observations only.
6. Write `tests/integration/test_m8_hermes_acp.py`.

**Additional requirements from the Terminal 1 charter:**

- ACP-first / MCP-fallback selection policy.
- Session isolation (per-task correlation IDs, no cross-contamination).
- Provenance-complete observations (WHAT, WHO, WHEN, WHERE, WHICH PROTOCOL, etc.).
- Observation ≠ verdict boundary preservation.
- Error / failure model covering timeout, disconnect, malformed response, cleanup failure.
- Security boundaries (least privilege, no secret leakage, trust boundary enforcement).
- Configuration (endpoint, enablement flags, timeouts, retries).
- Observability (structured logging + EventBus events).
- psutil dependency fix.
- Complete test suite (unit + integration + regression + negative + concurrency).

---

## 5. Target Architecture

```
AI-OS Kernel
  └─ HermesBridge
       ├─ [_protocol] == "acp"  or  "mcp"   (read from config)
       ├─ AcPAdapter      ← NEW: stdio-driven via agent-client-protocol SDK
       │    └─ launches hermes-agent via subprocess
       │    └─ new_session / prompt / cancel / close_session
       │    └─ records protocol="acp" in provenance
       └─ McpBridge       ← existing MCPManager path
            └─ launches mock_hermes_server (or real) via subprocess
            └─ records protocol="mcp" in provenance

Policy:
  if config.hermes.protocol == "acp" AND acp available → ACP
  elif config.hermes.protocol == "mcp" OR acp unavailable → MCP
  else → error (deterministic failure, no silent fallback)
```

ACP is selected **explicitly**. The selected protocol is **recorded in provenance** on every observation.

### 5.1 New Module: `src/aios/adapters/acp_adapter.py`

Responsibilities:
- Subprocess lifecycle for `hermes-agent`.
- ACP client interaction via the `acp` SDK (or raw stdio JSON-RPC if SDK unavailable in test env).
- Session create / prompt / cancel / close.
- Error mapping (timeout, disconnect, malformed response) to AI-OS exceptions.
- Provenance attachment for every response.

### 5.2 Modified: `src/aios/adapters/hermes_bridge.py`

Responsibilities:
- Accept `protocol: str = "acp"` and optional `acp_adapter` / `mcp_manager` deps.
- Implement protocol selection based on availability + config.
- Delegate to `AcPAdapter` or `McpBridge` as appropriate.
- Normalize the underlying response into `HermesObservation` (already the target type).
- Fix the session-ID mismatch with `UserSimulationAgent`: `create_worker_session` must return the ID that subsequent calls use.

### 5.3 Modified: `src/aios/core/user_simulation_agent.py`

Responsibilities:
- Stop calling `self._bridge._create_session_id()` directly — use `await self._bridge.create_worker_session(...)` and consume the returned session ID.
- Preserve all existing defense-in-depth INV-008 logic.
- Preserve observation-only invariant (verify the returned `UserSimulationCompleted.raw_trace` records `protocol` at the observation level).

### 5.4 Modified: `config/mcps.yaml` (empty → add ACP section)

Add:
```yaml
hermes:
  protocol: acp          # acp | mcp
  endpoint: ""           # reserved for future network transport; empty means local subprocess
  timeout_seconds: 30
  retry_attempts: 3
  fallback_to_mcp: true  # only if acp explicitly requested but unavailable
```

### 5.5 New: `config/mcp/hermes_agent_ext_acp.json`

ACP configuration:
```json
{
  "server_id": "hermes_agent_ext_acp",
  "name": "Hermes Agent External (ACP)",
  "transport": "stdio",
  "command": ["python", "-m", "acp_adapter.entry"],
  "cwd": "<path-to-hermes-agent-repo>",
  "env": {},
  "timeout_seconds": 30,
  "metadata": {
    "description": "Hermes Agent via ACP stdio protocol"
  }
}
```

---

## 6. Adapter Contract

### 6.1 `HermesBridge` (AI-OS-facing interface — NOT changed in signature)

```python
class HermesBridge:
    def __init__(
        self,
        mcp_manager=None,
        server_id: str = "hermes_agent_ext",
        protocol: str = "acp",  # NEW: "acp" preferred, "mcp" as alternate
    ) -> None: ...

    async def create_worker_session(self, environment=None) -> str:
        """Returns the session ID the caller MUST use in subsequent calls."""

    async def close_worker_session(self, session_id: str) -> bool: ...
    async def execute_task(self, task: HermesTask) -> HermesObservation: ...
    async def navigate(self, session_id, url) -> HermesObservation: ...
    async def click(self, session_id, selector) -> HermesObservation: ...
    async def type_text(self, session_id, selector, text) -> HermesObservation: ...
    async def screenshot(self, session_id, full_page=False) -> HermesObservation: ...
    async def extract_content(self, session_id, selector=None) -> HermesObservation: ...
    async def wait_for(self, session_id, condition, timeout=30) -> HermesObservation: ...
    def is_session_active(self, session_id) -> bool: ...
    def get_active_sessions(self) -> list[str]: ...
```

### 6.2 `HermesObservation` (unchanged schema — NEW field for provenance)

```python
@dataclass
class HermesObservation:
    task_id: str
    success: bool
    data: dict[str, Any]
    error: str | None
    timestamp: datetime
    session_id: str
    provenance: dict[str, Any]
    trust_level: str = "untrusted"
    # PROVENANCE EXTENSION (NEW — no schema break):
    # protocol: str  # "acp" | "mcp" — recorded at normalization time
    # call_id: str   # ACP session id or MCP call id
```

### 6.3 `AcPAdapter` (internal — hidden from kernel)

```python
class AcPAdapter:
    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def new_session(self, cwd: str) -> str: ...   # returns ACP session_id
    async def prompt(self, session_id: str, text: str, timeout: float) -> dict[str, Any]: ...
    async def cancel(self, session_id: str) -> None: ...
    async def close_session(self, session_id: str) -> None: ...
    def is_connected(self) -> bool: ...
```

### 6.4 Provenance fields recorded on EVERY observation

| Field | Source |
|-------|--------|
| `task_id` | caller |
| `session_id` | hermes bridge (ACP std session or MCP create_session return) |
| `correlation_id` | generated by bridge (UUID) |
| `protocol` | `"acp"` or `"mcp"` |
| `adapter` | `"acp_adapter"` or `"mcp_manager"` |
| `timestamp` | `datetime.now(timezone.utc)` |
| `worker` | `"hermes_agent_ext"` |
| `server` | server id from config |
| `request_metadata` | task description, parameters hash (NO secrets) |
| `raw_result` | referenced by provenance key, not serialized inline |
| `normalized_result` | `success`, `data` snapshot |
| `exit_status` | from prompt response or exception |
| `errors` | list of non-fatal warnings (empty if none) |
| `environment` | environment overlay passed to `create_worker_session` |

---

## 7. ACP / MCP Selection Policy

```
1. Read config: hermes.protocol (default "acp").
2. If protocol == "acp":
   a. Verify `agent-client-protocol` package is importable.
   b. Verify hermes-agent is reachable (command exists at configured cwd or PATH).
   c. If both true → use ACP.
   d. If config.hermes.fallback_to_mcp is true AND ACP unavailable → use MCP with protocol="acp_fallback" in provenance.
   e. Otherwise → raise ProtocolUnavailableError (non-retryable, non-fallback).
3. If protocol == "mcp" → use MCP path directly (provenance.protocol = "mcp").
4. Any other value → log error, raise ValueError.
```

**Provenance records the actual protocol used**, not the requested one. Example: if ACP was requested but unavailable and MCP fallback was used, provenance contains `protocol: "acp_fallback"`.

**No silent switching.** The selection and outcome are always logged and always recorded.

---

## 8. Session Isolation

### 8.1 Session lifecycle

```
create_worker_session(env) → ACP new_session(cwd=...) → returns ACP session_id
...
execute_task(session_id, ...)
...
close_worker_session(session_id) → ACP cancel + resource release
```

### 8.2 Isolation guarantees

- Each call to `create_worker_session` produces a **unique** ACP session ID.
- The ID is stored in `self._active_sessions[session_id]` keyed by the **returned** ID, not a caller-supplied one.
- Subsequent calls MUST use the returned ID; the bridge validates the ID against its active set and raises `ValueError("unknown session")` for stale/foreign IDs.
- On `close_worker_session`, the entry is removed and the remote session is cancelled.
- Timeout: session creation must complete within `config.hermes.timeout_seconds`; otherwise raise `SessionCreationTimeout`.
- Cancellation: `cancel(session_id)` sends an ACP cancel; double-close is no-op, not error.
- Concurrency: multiple independent bridges (each with their own `AcPAdapter`) can run simultaneously; sessions are isolated by UUID.

### 8.3 Defect fix required before production

`UserSimulationAgent` currently:
1. Generates `session_id = self._bridge._create_session_id()`.
2. Calls `create_worker_session` and **ignores** the return value.
3. Uses the locally-generated ID in `navigate`, `execute_task`, and `close_worker_session`.

This is a bug: the remote-side session key is the MCP/ACP server-generated ID; the bridge's active-session map is keyed by that server-generated ID. Fix: `UserSimulationAgent` must consume the returned session ID and pass it to all subsequent calls. This is a behavior-preserving fix — not an architectural change.

---

## 9. Provenance

### 9.1 Minimum provenance per observation

Every `HermesObservation.provenance` MUST contain at minimum:

```python
{
    "task_id": "...",
    "execution_id": str(uuid.uuid4()),   # unique per execute_task call
    "session_id": "...",                  # hermes side
    "correlation_id": str(uuid.uuid4()),  # AI-OS side, links request → response
    "adapter": "acp_adapter" | "mcp_manager",
    "protocol": "acp" | "mcp" | "acp_fallback",
    "timestamp": "<ISO 8601 UTC>",
    "request_metadata": {
        "task_type": "...",
        "description": "...",             # truncated to safe length
        "parameters_hash": "<sha256 of parameters>",  # no secret values
    },
    "target": {"server_id": "...", "cwd": "..."},
    "raw_result_ref": "<key or url into structured log>",  # do NOT inline blobs
    "normalized_result": {"success": bool, "data_keys": list},
    "exit_status": "completed" | "cancelled" | "error" | "timeout",
    "errors": [],
    "environment": {...},
}
```

### 9.2 Secrets policy

Never include in provenance:
- API keys, tokens, credentials (even hashed).
- Full parameter values that could contain secrets (hash them instead).
- Raw screenshots or large binary artifacts (reference them via log key).

### 9.3 Observation ≠ Verdict

The bridge emits `HermesObservation` with:
- `success: bool` — did the execution complete without error? (boolean fact)
- `data` — what the worker returned.

It MUST NOT emit:
- `verdict`, `pass`, `fail`, `approved`, `rejected`, `secure`, `compliant` — these are AI-OS decisions derived later by `TestOrchestratorService` / `FinalJudgeAgency`.

Verification: search every return path in `HermesBridge` for forbidden words (`verdict`, `pass`, `fail`, `approved`, `rejected`, `secure`, `compliant`, `decision`) and confirm none appear in observation construction.

---

## 10. Observation Model

### 10.1 Current model (unchanged shape)

```python
@dataclass
class HermesObservation:
    task_id: str
    success: bool
    data: dict[str, Any]
    error: str | None
    timestamp: datetime
    session_id: str
    provenance: dict[str, Any]
    trust_level: str = "untrusted"
```

### 10.2 Extension (adding fields, not changing existing)

Add the following to provenance dict (not top-level, to avoid schema breakage):
- `protocol: str` — "acp" | "mcp" | "acp_fallback"
- `call_id: str` — ACP session ID or MCP tool-call ID
- `exit_status: str` — "completed" | "cancelled" | "error" | "timeout"

### 10.3 Normalization

`HermesBridge._normalize_acp_response(raw)` and `_normalize_mcp_response(raw)` produce identical `HermesObservation` shapes, differing only in provenance metadata. The normalizer:
- Maps ACP `PromptResponse.stop_reason` → `exit_status`: `"end_turn"` → `"completed"`, `"cancelled"` → `"cancelled"`, anything else → `"error"`.
- Extracts assistant text chunks from ACP stream events into `data["output_text"]`.
- Extracts tool-call artifacts into `data["artifacts"]`.
- Preserves `success = (exit_status == "completed" and len(error or "") == 0)`.

---

## 11. Error Model

| Error class | Retryable? | Fallback eligible? | Category |
|-------------|------------|---------------------|----------|
| `ProtocolUnavailableError` | No | Yes, to MCP if policy permits | FATAL |
| `TransportConnectionError` | Yes (up to max_retries) | Yes | RETRYABLE |
| `SessionCreationTimeout` | Yes (once) | Yes | RETRYABLE |
| `SessionNotFoundError` | No | No | NON-RETRYABLE |
| `ExecutionTimeout` | Yes (once) | Yes | RETRYABLE |
| `ExecutionCancelled` | No | No | OBSERVATION (success=False) |
| `MalformedResponseError` | No | No | EVIDENCE-INCOMPLETE |
| `TransportDisconnectError` | Yes (up to max_retries) | Yes | RETRYABLE |
| `CleanupTimeout` | No | No | WARN (log + evidence incomplete) |
| `DuplicateExecutionError` | No | No | SECURITY-CRITICAL |
| `SecretLeakDetectedError` | No | No | SECURITY-CRITICAL |

**Non-fallback errors** (must surface to AI-OS as-is, no silent replacement):
- `ProtocolUnavailableError` (when fallback disabled).
- `MalformedResponseError`.
- `DuplicateExecutionError`.
- `SecretLeakDetectedError`.

### 11.1 Retry semantics

- Max retries = `config.hermes.retry_attempts` (default 3).
- Backoff: exponential, capped at 5 s.
- Each retry attempt is recorded in provenance as a new `execution_id`.

### 11.2 Timeout semantics

- Connection timeout: `config.hermes.timeout_seconds` (default 30 s).
- Per-prompt timeout: configurable per task; default 60 s.
- On timeout, observation `success=False`, `error="timeout"`, `exit_status="cancelled"`.

---

## 12. Security

### 12.1 Trust boundary

```
AI-OS Kernel (trusted)
  │
  │  HermesBridge (authorization boundary)
  ▼
Hermes ACP / MCP transport (untrusted)
  │
  ▼
hermes-agent subprocess (untrusted external worker)
```

The bridge is the authorization boundary. All interactions are:
- Validated through existing `SecurityManager.validate_mcp_server_before_connect` equivalent for ACP (new method `validate_acp_server`).
- Logged with provenance.
- Subject to secret-scrubbing before provenance attachment.

### 12.2 New attack surfaces introduced by ACP

| Surface | Risk | Mitigation |
|---------|------|------------|
| Subprocess cwd | hermes-agent may operate outside intended workspace | Explicit `cwd` parameter; never use `.` or `/`; validate path exists and is under allowed root |
| ACP session_id collision | malicious actor reuses another task's session | UUID-generated; bridge validates ownership before routing |
| Prompt injection in `user_goal` / `exploration_brief` | ACP client sends arbitrary text to LLM | Input size limit (e.g., 4 KB); escape/control characters; logged and hashed but not blocked — the LLM handles intent |
| Stdio protocol framing | malformed frames confuse the reader | Frame-based parser with length prefix; hard timeout per frame |
| Process persistence | hermes-agent survives parent exit | SIGTERM on close; `process.terminate()` + wait; tracked via `asyncio.subprocess.Process` |
| Environment leakage | hermes-agent inherits AI-OS env vars (secrets) | Explicit `env` dict passed to subprocess; never inherit `os.environ` wholesale; scrub known secret prefixes (`API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`) |
| Cross-session contamination | tool state leaks between tasks | ACP creates a new session per call; no shared mutable state across sessions |
| Provenance tampering | tampered provenance falsifies traceability | Provenance computed by bridge, never by the remote side; signed hash if audit requires (future M11) |

### 12.3 Secrets handling

- `HermesBridge` scrubs any env var matching `re.compile(r"(?i)^(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)")` before passing to subprocess.
- Parameters are hashed (SHA-256) for provenance; raw values are never written to provenance.
- Screenshots and large binaries are referenced, not embedded.

---

## 13. Configuration

Reuse existing AI-OS configuration conventions.

### 13.1 `config/defaults.yaml` additions

```yaml
hermes:
  protocol: "acp"           # acp | mcp
  cwd: ""                   # path to hermes-agent repo root; empty means auto-detect or skip
  timeout_seconds: 30
  retry_attempts: 3
  fallback_to_mcp: true     # only when ACP is requested but unavailable
  allowed_root: ""          # if set, restrict subprocess cwd underneath this path
  session_idle_timeout_seconds: 300
```

### 13.2 Validation rules

- `protocol` must be one of `acp`, `mcp`.
- If `protocol == "acp"` and `cwd` is empty → warn; attempt to detect hermes-agent relative to AI-OS repo root (`../../hermes-agent` or similar — configurable).
- If `fallback_to_mcp == false` and ACP unavailable → error, do not silently switch.
- `timeout_seconds > 0` and `retry_attempts >= 0`.

---

## 14. Observability

### 14.1 Logging

Structured logs (via `StructuredLogger`) for:
- `protocol_selected` — "acp" | "mcp" | "acp_fallback", reason.
- `session_created` — session_id, cwd, elapsed_ms.
- `session_closed` — session_id, elapsed_ms.
- `execution_started` — task_id, session_id, protocol.
- `execution_completed` — task_id, protocol, success, elapsed_ms.
- `execution_failed` — task_id, protocol, error, retry_count.
- `fallback_triggered` — reason, previous_protocol, new_protocol.
- `cleanup_failed` — session_id, error.

**No secrets in logs.** Hash parameters; truncate descriptions > 200 chars.

### 14.2 EventBus events

Reuse existing `EventType.HERMES_BRIDGE_TASK` and `HERMES_BRIDGE_OBSERVATION` (lines 175–176 of `events/core/types.py`). Add no new event types to avoid Part-0 §0.5.2 extension overhead outside this task.

### 14.3 Metrics

If `StructuredLogger` exposes counters, increment:
- `hermes.executions.total`
- `hermes.executions.success`
- `hermes.executions.failed`
- `hermes.executions.timeout`
- `hermes.executions.fallback`
- `hermes.sessions.active`
- `hermes.sessions.closed`

---

## 15. Files / Modules Affected

### 15.1 New files

| Path | Purpose |
|------|---------|
| `src/aios/adapters/acp_adapter.py` | ACP stdio transport layer |
| `src/aios/adapters/acp_session.py` | ACP session manager (wrap `AcPAdapter`) |
| `tests/unit/test_acp_adapter.py` | Unit tests for ACP adapter |
| `tests/integration/test_m8_hermes_acp.py` | Integration tests for ACP primary + fallback |
| `tests/unit/test_hermes_bridge_acp.py` | Unit tests for bridge protocol selection |
| `config/mcp/hermes_agent_ext_acp.json` | ACP server config (for MCPManager compatibility layer, optional) |

### 15.2 Modified files

| Path | Change |
|------|--------|
| `src/aios/adapters/hermes_bridge.py` | Add ACP support; fix session-ID lifecycle bug |
| `src/aios/core/user_simulation_agent.py` | Fix session ID consumption bug; preserve provenance |
| `src/aios/adapters/mock_hermes_server.py` | Extend to also speak ACP (minimal mock) for integration tests |
| `src/aios/adapters/__init__.py` | Export new classes if needed |
| `src/aios/events/core/types.py` | No changes (reuse HERMES_BRIDGE_TASK / HERMES_BRIDGE_OBSERVATION) |
| `pyproject.toml` | Add `psutil` to `[project.optional-dependencies.dev]` |
| `config/defaults.yaml` | Add `hermes:` section |
| `tests/performance/test_structured_logger_perf.py` | Guard `import psutil` with `pytest.importorskip` |

### 15.3 Unchanged (must not touch)

- `src/aios/core/kernel.py` — keep wiring as-is; `_init_m7_testing` works through DI.
- `src/aios/core/testing_evidence.py` — `UserSimulationCompleted`, `Provenance`, `TestingEvidence` schema unchanged.
- `src/aios/services/testing.py` — `TestOrchestratorService` orchestration unchanged.
- `src/aios/adapters/base.py` — base adapter unchanged.
- All agency adapters (`security_agency_adapter.py`, etc.) — unchanged.
- `src/aios/core/mcp_manager.py` — unchanged (still serves MCP path).
- `src/aios/adapters/mock_hermes_server.py` — keep the existing MCP mock; extend only.

---

## 16. Implementation Sequence

### Phase 1 — Foundation (parallelizable)

1. **Dependency hygiene** — add `psutil` to dev deps + guard `test_memory_bounded_under_load` import.
2. **Confirm adapter contract** — freeze `HermesObservation` + `HermesTask` signatures; draft `AcPAdapter` interface.
3. **Update `config/defaults.yaml`** with `hermes:` section.

### Phase 2 — ACP transport layer

4. **Implement `acp_adapter.py`** — subprocess management, ACP client via `acp` SDK, `new_session` / `prompt` / `cancel` / `close_session`.
5. **Implement `acp_session.py`** — session registry, timeout handling, isolation validation.
6. **Write `tests/unit/test_acp_adapter.py`** — mock stdio, verify protocol framing, timeout, cancel.

### Phase 3 — Bridge integration

7. **Update `hermes_bridge.py`** — accept `protocol`, wire to `AcPAdapter` or `McpBridge`, normalize responses, fix session-ID lifecycle bug.
8. **Fix `user_simulation_agent.py`** — consume `create_worker_session` return ID; preserve provenance in `_obs_to_dict`.
9. **Write `tests/unit/test_hermes_bridge_acp.py`** — protocol selection, fallback trigger, provenance completeness, error mapping.

### Phase 4 — Integration + regression

10. **Extend `mock_hermes_server.py`** to also speak minimal ACP (a second stdio mode or separate mock — `mock_hermes_acp_server.py`) for tests that need real protocol behavior.
11. **Write `tests/integration/test_m8_hermes_acp.py`** — real protocol tests where feasible; MCP fallback tests; session isolation tests; failure injection tests.
12. **Run regression** — verify all 1046 existing tests still pass.
13. **Run M7 regression** — `tests/integration/test_m7_security.py` + `tests/unit/test_user_simulation_agent.py`.

### Phase 5 — Documentation + handoff

14. Update `README` / `CHANGELOG` with M8-T1 completion note.
15. Produce M8-T1 QA checklist.
16. Handoff to Terminal 2 implementation and Terminal 3 QA.

---

## 17. Test Plan

### 17.1 Unit tests — `tests/unit/test_acp_adapter.py`

| Test | Scenario |
|------|----------|
| `test_connect_success` | Stdio ACP handshake completes; returns True |
| `test_connect_process_not_found` | subprocess.CalledProcessError on missing hermes-agent; raises ProtocolUnavailableError |
| `test_new_session_returns_uuid` | `new_session()` returns a non-empty UUID string |
| `test_new_session_timeout` | `new_session()` exceeds timeout; raises SessionCreationTimeout |
| `test_prompt_success` | `prompt()` returns dict with `stop_reason="end_turn"` and text |
| `test_prompt_timeout` | `prompt()` exceeds per-prompt timeout; raises ExecutionTimeout |
| `test_prompt_cancelled` | `prompt()` cancelled mid-flight; returns `stop_reason="cancelled"` |
| `test_cancel_unknown_session` | `cancel()` on unknown ID raises SessionNotFoundError |
| `test_close_session` | `close_session()` releases resource; double-close is no-op |
| `test_disconnect_clears_state` | `disconnect()` sets not-connected; subsequent calls fail |
| `test_scrubs_secrets_in_env` | Env var `API_KEY=secret` is removed before subprocess launch |
| `test_validates_cwd` | `new_session(cwd="/etc")` raises if cwd not under allowed_root |

### 17.2 Unit tests — `tests/unit/test_hermes_bridge_acp.py`

| Test | Scenario |
|------|----------|
| `test_protocol_selection_acp_preferred` | `protocol="acp"`, ACP available → uses ACP, provenance says "acp" |
| `test_protocol_selection_mcp_explicit` | `protocol="mcp"` → uses MCP, provenance says "mcp" |
| `test_fallback_acp_unavailable_mcp_used` | ACP unavailable + `fallback=True` → uses MCP, provenance says "acp_fallback" |
| `test_no_fallback_acp_unavailable_raises` | ACP unavailable + `fallback=False` → raises ProtocolUnavailableError |
| `test_create_worker_session_tracks_id` | Return value stored in active dict; subsequent calls use it |
| `test_close_worker_session_removes_id` | Session removed from active dict after close |
| `test_provenance_complete` | Every observation has all mandatory provenance fields |
| `test_provenance_no_secrets` | Provenance dict contains no plaintext secrets |
| `test_normalize_acks_acp_stop_reason` | "end_turn" → success=True; "cancelled" → success=False |
| `test_error_wraps_as_observation` | Exception during execute → HermesObservation(success=False, error=...) |
| `test_observe_not_verdict` | Result data contains no forbidden words |

### 17.3 Integration tests — `tests/integration/test_m8_hermes_acp.py`

| Test | Scenario |
|------|----------|
| `test_acp_real_mock_server` | Use extended mock that speaks ACP; end-to-end connect → session → prompt → close |
| `test_mcp_fallback_path` | Explicit `protocol="mcp"` through mock MCP server |
| `test_session_isolation` | Two concurrent sessions; operations on one do not leak to the other |
| `test_correlation_id_traceability` | Request → response correlation via provenance.correlation_id |
| `test_cleanup_on_exception` | `execute_task` raises; `close_worker_session` still succeeds |
| `test_timeout_execution` | Mock server sleeps > timeout; observation records timeout |
| `test_disconnected_server` | Server dies mid-session; next call raises TransportDisconnectError |
| `test_concurrent_sessions` | 5 concurrent sessions; all isolated; all cleaned up |
| `test_real_hermes_acp` | If `HERMES_ACP_TEST=1` env set, launch real hermes-agent ACP adapter and run a lightweight prompt |

### 17.4 Regression tests

Must rerun after every phase:
- `tests/integration/test_m7_security.py` (13 tests)
- `tests/unit/test_user_simulation_agent.py` (5 tests)
- `tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load`
- Full suite `tests/ -q` (expect 1046 + N_new)

### 17.5 Negative tests (Hermes must not be able to)

| Test | Forbidden behavior |
|------|-------------------|
| `test_hermes_cannot_produce_verdict` | Observation does not contain `verdict`/`pass`/`fail`/`approved` |
| `test_hermes_cannot_bypass_verification` | Bridge always returns `trust_level="untrusted"` |
| `test_hermes_cannot_mutate_protected_state` | No writes to kernel state outside observation normalization |
| `test_hermes_cannot_access_secrets` | Provenance excludes API keys, tokens |
| `test_malformed_response_does_not_crash` | Bad JSON / incomplete frames → error observation, not exception |
| `test_duplicate_execution_detected` | Two prompt calls with same session_id before close → duplicate execution error |

### 17.6 Mock / fake policy

| Layer | Must use | Reason |
|-------|----------|--------|
| Unit — ACP protocol framing | Mock stdio (in-memory StreamReader/StreamWriter) | Fast, deterministic |
| Unit — bridge selection logic | Fake bridge / fake AcPAdapter | Isolate policy |
| Integration — ACP path | Extended mock ACP server (separate process, or same-process via monkeypatch) | Real protocol semantics without hermes-agent dependency |
| Integration — MCP fallback | Existing `mock_hermes_server.py` | Already works |
| Integration — real ACP | Flag-gated (`HERMES_ACP_TEST=1`) | Requires hermes-agent + `acp` installed |

---

## 18. Regression Plan

Before declaring M8-T1 complete:

1. **Full suite**: `pytest tests/ -q` — expect **1046 + N_new** passed, zero failures.
2. **M7 regression**: `pytest tests/integration/test_m7_security.py tests/unit/test_user_simulation_agent.py -v` — expect **13 + 5 = 18** passed.
3. **Hermes adapter tests**: `pytest tests/unit/test_hermes_bridge_acp.py tests/unit/test_acp_adapter.py -v` — expect all new tests pass.
4. **Integration tests**: `pytest tests/integration/test_m8_hermes_acp.py -v` — expect all pass.
5. **Dependency-clean env test**: `python -c "import pytest; import psutil"` — verify `psutil` importable after fix.
6. **No-regression baseline**: track `PASS / FAIL / SKIPPED / ENVIRONMENTAL` for each suite; document.

---

## 19. Acceptance Criteria

### ACP
- [ ] ACP is the preferred protocol (`protocol="acp"` in defaults).
- [ ] ACP connection established with local hermes-agent subprocess.
- [ ] Session lifecycle works: create → use → close.
- [ ] Real execution path works through ACP (verified via extended mock or real).
- [ ] Cleanup works (session removed from active set, subprocess terminated).

### MCP
- [ ] MCP fallback is controlled (explicit config flag).
- [ ] Fallback is explicit (provenance says `"acp_fallback"`).
- [ ] Provenance identifies MCP execution (`protocol="mcp"`).

### Isolation
- [ ] Sessions are isolated (no cross-session contamination).
- [ ] Correlation IDs are correct and traceable.
- [ ] No cross-task contamination (concurrent sessions tested).

### Evidence
- [ ] Observations are provenance-complete (all mandatory fields present).
- [ ] Raw execution can be traced back to request.
- [ ] Normalization is deterministic.
- [ ] No unsupported claims (verdict, pass/fail) in observation.

### Authority
- [ ] Hermes cannot declare AI-OS verdicts (verified by negative tests).
- [ ] Hermes cannot bypass verification (trust_level always untrusted).
- [ ] Hermes cannot bypass governance (bridge validates through SecurityManager).

### Reliability
- [ ] Timeout handling works (connection, session, execution).
- [ ] Cancellation propagates to subprocess.
- [ ] Disconnect handled gracefully.
- [ ] Retry/fallback behavior correct.
- [ ] Cleanup on exception path works.

### Security
- [ ] No secret leakage in provenance or logs.
- [ ] Least privilege — subprocess env is scrubbed.
- [ ] Session boundaries maintained under concurrency.

### Testing
- [ ] All unit tests pass.
- [ ] M8 integration tests pass.
- [ ] Existing regression suite passes (1046 baseline + new).
- [ ] Dependency-clean environment test passes (psutil declared).

### Dependency
- [ ] `psutil` declared in `pyproject.toml` dev deps (or guarded with `importorskip`).
- [ ] `test_memory_bounded_under_load` passes deterministically.

---

## 20. Definition of Done

M8-T1 is DONE only when **all** of the following are true:

1. ACP is the preferred Hermes protocol in configuration.
2. MCP fallback works according to the explicit policy (fallback flag + provenance marker).
3. Real execution has been demonstrated through the intended ACP path (either via extended mock or real hermes-agent with `HERMES_ACP_TEST=1`).
4. Session isolation is verified: concurrent sessions do not share state.
5. Observations contain complete provenance (all mandatory fields populated).
6. Hermes cannot produce AI-OS verdicts (negative tests pass).
7. Failure behavior is deterministic (timeouts, cancellations, disconnects all produce expected observations, not exceptions escaping to caller).
8. Security boundaries are preserved (no secret leakage; subprocess env scrubbed).
9. M8 integration tests pass.
10. Existing regression tests pass (1046 baseline).
11. psutil dependency/test hygiene is resolved.
12. Independent QA can reproduce the result (handoff docs sufficient).
13. No architecture boundary has been violated (kernel unchanged except for `_init_m7_testing` wiring if needed for ACP config reading).

---

## 21. Terminal 2 Implementation Handoff

### 21.1 Objective

Upgrade `HermesBridge` to support ACP as the preferred protocol while preserving MCP as an explicit fallback. Fix the session-ID lifecycle bug in `UserSimulationAgent`. Resolve the `psutil` dependency test hygiene issue. Add tests proving the above.

### 21.2 Exact files to inspect (read fully before editing)

```
src/aios/adapters/hermes_bridge.py
src/aios/adapters/mock_hermes_server.py
src/aios/core/user_simulation_agent.py
src/aios/core/kernel.py (only _init_m7_testing section, lines 793–834)
src/aios/core/testing_evidence.py
src/aios/services/testing.py
src/aios/events/core/types.py (HERMES_BRIDGE_TASK, HERMES_BRIDGE_OBSERVATION)
src/aios/events/core/bus.py
config/defaults.yaml
config/mcp/hermes_agent_ext_mcp.json
pyproject.toml
tests/unit/test_user_simulation_agent.py
tests/integration/test_m7_security.py
tests/performance/test_structured_logger_perf.py
```

### 21.3 Exact files to create

```
src/aios/adapters/acp_adapter.py         # ACP stdio transport layer
src/aios/adapters/acp_session.py         # Session registry / timeout / isolation
tests/unit/test_acp_adapter.py
tests/unit/test_hermes_bridge_acp.py
tests/integration/test_m8_hermes_acp.py
config/mcp/hermes_agent_ext_acp.json     # Optional: config for ACP via MCPManager compat layer
```

### 21.4 Exact interfaces

**`AcPAdapter`** (internal, in `acp_adapter.py`):
```python
class AcPAdapter:
    def __init__(self, cwd: str, timeout_seconds: int = 30, allowed_root: str | None = None, env_scrub_patterns: tuple[str, ...] | None = None): ...
    async def connect(self) -> bool: ...           # launches subprocess, completes ACP initialize
    async def disconnect(self) -> None: ...        # terminates subprocess
    async def new_session(self, cwd: str) -> str: ...  # returns ACP session_id (UUID)
    async def prompt(self, session_id: str, text: str, timeout: float) -> dict[str, Any]: ...
    async def cancel(self, session_id: str) -> None: ...
    async def close_session(self, session_id: str) -> None: ...
    def is_connected(self) -> bool: ...
```

**Modified `HermesBridge` constructor:**
```python
def __init__(
    self,
    mcp_manager=None,
    server_id: str = "hermes_agent_ext",
    protocol: str = "acp",  # "acp" or "mcp"
    acp_adapter=None,       # injectable for tests
    fallback_to_mcp: bool = True,
): ...
```

### 21.5 Exact implementation sequence (Terminal 2 should follow)

1. Add `psutil` to `[project.optional-dependencies.dev]` in `pyproject.toml`.
2. Guard `import psutil` in `tests/performance/test_structured_logger_perf.py` with `pytest.importorskip("psutil")`.
3. Create `src/aios/adapters/acp_adapter.py` with `AcPAdapter` class.
4. Create `src/aios/adapters/acp_session.py` with session registry + timeout + isolation validation.
5. Update `src/aios/adapters/hermes_bridge.py`:
   - Accept `protocol`, `acp_adapter`, `fallback_to_mcp`.
   - Implement selection policy per §7.
   - Wire `AcPAdapter` for ACP path.
   - Fix `create_worker_session` to store and return the **server-generated** session ID (not the pre-generated one).
   - Add provenance completion (add `protocol`, `call_id`, `exit_status` to provenance dict).
   - Add `_normalize_*` methods for ACP and MCP responses.
6. Update `src/aios/core/user_simulation_agent.py`:
   - Line 151: call `await self._bridge.create_worker_session(...)` and consume the return value as `session_id` (stop calling `_create_session_id()` directly).
   - Line 166: use the consumed `session_id`.
   - Line 197: close the consumed `session_id`.
   - `_obs_to_dict`: include `provenance` from the observation (currently dropped).
7. Update `config/defaults.yaml` with `hermes:` section.
8. Update `tests/unit/test_user_simulation_agent.py` to cover the new session-ID behavior.
9. Write `tests/unit/test_acp_adapter.py`.
10. Write `tests/unit/test_hermes_bridge_acp.py`.
11. Write `tests/integration/test_m8_hermes_acp.py`.
12. Run full regression suite.

### 21.6 Exact constraints

- **DO NOT** change `HermesObservation` dataclass fields (only extend provenance dict).
- **DO NOT** change `UserSimulationCompleted` dataclass fields.
- **DO NOT** change `Provenance` dataclass fields (extend via dict inside observation provenance, not via new dataclass field).
- **DO NOT** change the kernel constructor or service wiring beyond reading new config.
- **DO NOT** add new `EventType` values (reuse `HERMES_BRIDGE_TASK` and `HERMES_BRIDGE_OBSERVATION`).
- **DO NOT** import `acp` at module scope in `hermes_bridge.py` (defer import to avoid `ModuleNotFoundError` when `acp` is not installed in test env).
- **DO NOT** make `mock_hermes_server.py` speak ACP unless the test explicitly requests it; create a separate `mock_hermes_acp_server.py` if needed.
- **DO NOT** increase the baseline test count failure rate — regression must stay at 0 failures.

### 21.7 Exact tests to create/update

**Create:**
- `tests/unit/test_acp_adapter.py`
- `tests/unit/test_hermes_bridge_acp.py`
- `tests/integration/test_m8_hermes_acp.py`

**Update:**
- `tests/unit/test_user_simulation_agent.py` — adjust assertions for new session-ID lifecycle; add test for provenance inclusion in `_obs_to_dict`.
- `tests/performance/test_structured_logger_perf.py` — guard `import psutil`.
- `tests/integration/test_m7_security.py` — verify still passes (no behavioral change expected).

### 21.8 Exact acceptance criteria (same as §19)

See §19.

### 21.9 Forbidden changes

- Do NOT refactor `TestOrchestratorService`.
- Do NOT refactor `CouncilManager` / `FinalJudgeAgency`.
- Do NOT refactor `SecurityManager`.
- Do NOT add new managers to the kernel.
- Do NOT change the subprocess launch strategy for the existing MCP mock (keep it working).
- Do NOT change any agency adapter (`security_agency_adapter.py`, `performance_agency_adapter.py`, etc.).
- Do NOT touch `src/aios/core/mcp_manager.py`.
- Do NOT touch `src/aios/core/workflow.py`.
- Do NOT touch `src/aios/core/council_manager.py`.
- Do NOT touch `src/aios/core/model_router.py`.

### 21.10 Expected evidence

After implementation, the following must be observable:
1. `pytest tests/ -q` — 1046 + N_new passed.
2. `pytest tests/unit/test_user_simulation_agent.py -v` — 5 passed.
3. `pytest tests/integration/test_m7_security.py -v` — 13 passed.
4. `pytest tests/unit/test_acp_adapter.py -v` — all pass.
5. `pytest tests/unit/test_hermes_bridge_acp.py -v` — all pass.
6. `pytest tests/integration/test_m8_hermes_acp.py -v` — all pass.
7. `grep -n "psutil" pyproject.toml` — shows declaration.
8. `grep -rn "verdict\|pass\|fail\|approved\|rejected\|secure\|compliant" src/aios/adapters/hermes_bridge.py` — zero matches in observation construction paths.

### 21.11 Expected final report format (for Terminal 2 to produce)

```
M8-T1 Implementation Report
===========================
1. Summary of changes (file, line range, purpose)
2. Test results:
   - Full suite: PASS / FAIL count
   - M7 regression: PASS / FAIL count
   - New unit tests: PASS / FAIL count
   - New integration tests: PASS / FAIL count
   - psutil test: PASS / FAIL
3. Provenance sample (redacted): paste one HermesObservation.provenance dict
4. Protocol selection sample (log line or test assertion)
5. Defects found and resolved (if any)
6. Open items / follow-ups for M8-T2..T6
```

---

## 22. Terminal 3 Independent QA Handoff

### 22.1 What must be independently verified

Terminal 3 must verify M8-T1 **without trusting Terminal 2's report**. Use the following checklist:

1. **ACP actually used**: Run `pytest tests/unit/test_hermes_bridge_acp.py::test_protocol_selection_acp_preferred -v` — assert provenance contains `protocol == "acp"`.
2. **MCP fallback used correctly**: Run `pytest tests/unit/test_hermes_bridge_acp.py::test_fallback_acp_unavailable_mcp_used -v` — assert provenance contains `protocol == "acp_fallback"`.
3. **Provenance completeness**: For every test in `tests/unit/test_hermes_bridge_acp.py` that constructs an observation, assert all mandatory fields are present (see §9.1).
4. **Session isolation**: Run `pytest tests/integration/test_m8_hermes_acp.py::test_session_isolation -v` and `::test_concurrent_sessions -v`. Verify no cross-session ID reuse.
5. **No verdicts from Hermes**: Grep `src/aios/adapters/hermes_bridge.py` and `src/aios/adapters/acp_adapter.py` for forbidden words (`verdict`, `pass`, `fail`, `approved`, `rejected`, `secure`, `compliant`, `decision`). Zero matches allowed in observation construction code.
6. **No fake execution**: Confirm `tests/integration/test_m8_hermes_acp.py::test_acp_real_mock_server` uses a real protocol round-trip (not a mock returning hardcoded values). Look for `mock_hermes_acp_server.py` or equivalent.
7. **No regression**: Run full suite; compare against baseline of 1046.
8. **psutil resolved**: Run `pytest tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load -v` in a clean env (no `psutil` installed) — should skip gracefully; with `psutil` installed — should pass.
9. **Hermes cannot mutate protected state**: Inspect `src/aios/adapters/acp_adapter.py` and `hermes_bridge.py` for any calls to `SecurityManager`, `CouncilManager`, `StateManager`, or kernel state mutation. Zero direct calls allowed (bridge talks only through `HermesObservation` which is consumed by trusted code).

### 22.2 What evidence must be collected

- Full test output log (all 1046 + new tests).
- One sample `HermesObservation.provenance` dict from a real ACP run (redact any secrets).
- Log excerpt showing protocol selection decision.
- Proof that `UserSimulationAgent` session ID now matches the bridge's active session key (inspect or add a test asserting `result.raw_trace["session_id"] == bridge.last_created_session_id`).

### 22.3 Which tests must be rerun

- All tests in `tests/unit/test_acp_adapter.py`.
- All tests in `tests/unit/test_hermes_bridge_acp.py`.
- All tests in `tests/integration/test_m8_hermes_acp.py`.
- All tests in `tests/unit/test_user_simulation_agent.py`.
- All tests in `tests/integration/test_m7_security.py`.
- `tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load`.
- Full suite `pytest tests/ -q`.

### 22.4 How to verify ACP was actually used

- Inspect `pytest tests/unit/test_hermes_bridge_acp.py::test_protocol_selection_acp_preferred` assertion: `assert obs.provenance["protocol"] == "acp"`.
- In integration test, verify the mock or real server received an ACP `initialize` request (check captured stdout/stderr or log).
- If using real hermes-agent (`HERMES_ACP_TEST=1`), verify hermes-agent logs show `Starting hermes-agent ACP adapter`.

### 22.5 How to verify MCP fallback

- Inspect `pytest tests/unit/test_hermes_bridge_acp.py::test_fallback_acp_unavailable_mcp_used` assertion: `assert obs.provenance["protocol"] == "acp_fallback"`.
- Verify `tests/unit/test_hermes_bridge_acp.py::test_no_fallback_acp_unavailable_raises` raises `ProtocolUnavailableError`.

### 22.6 How to verify provenance

For every observation produced in tests:
```python
required = {"task_id", "execution_id", "session_id", "correlation_id",
            "adapter", "protocol", "timestamp", "request_metadata",
            "target", "normalized_result", "exit_status", "errors", "environment"}
assert required.issubset(obs.provenance.keys())
```

### 22.7 How to verify session isolation

- Spawn two bridges concurrently.
- Call `create_worker_session` on each.
- Call `execute_task` with each session ID.
- Assert the results contain different session IDs.
- Assert `bridge1.get_active_sessions()` does not contain bridge2's session ID.

### 22.8 How to detect fake / heuristic execution

- Inspect `tests/integration/test_m8_hermes_acp.py::test_acp_real_mock_server` — it must construct a real subprocess or real in-memory stdio pair, not return hardcoded values.
- Assert the mock server received the exact request bytes and produced a response matching ACP framing (JSON-RPC `id` matching request).

### 22.9 How to verify Hermes cannot produce verdicts

- Source grep (automated):
  ```bash
  grep -RInE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/hermes_bridge.py src/aios/adapters/acp_adapter.py
  ```
- Expected output: only comments/docstrings referencing the invariant; zero code-path assignments.

### 22.10 How to verify no regression

- `pytest tests/ -q --tb=no` — count passed. Must equal 1046 + new_test_count.
- `pytest tests/unit/test_user_simulation_agent.py tests/integration/test_m7_security.py -v` — 18 passed.

### 22.11 How to verify the psutil issue is truly resolved

- Run in a venv **without** `psutil`: `python -m pytest tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load -v` — should result in `SKIPPED`, not `FAILED`.
- Run in a venv **with** `psutil`: should `PASS`.

---

## 23. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `agent-client-protocol` not installable in test env | High | Tests block | Defer `import acp` to runtime; unit tests use in-memory stdio mock |
| hermes-agent subprocess startup slow (>30s) | Medium | CI timeout | Configurable timeout; integration tests use mock by default |
| ACP stdio framing complexity | Medium | Bugs in transport | Start with a thin wrapper; add integration tests early |
| Session ID lifecycle regression | Medium | Existing UserSim breaks | Fix `user_simulation_agent.py` as part of T1; add test |
| hermes-agent repo layout changes | Low | `cwd` / command path breaks | Document exact path resolution strategy; allow env override |
| Mock ACP server insufficient for E2E | Medium | Coverage gap | Build `mock_hermes_acp_server.py` with minimal ACP conformance |
| Provenance schema drift from Part 15 contracts | Low | Audit failure | Lock provenance fields in doc; enforce with tests |

---

## 24. Out of Scope

**Explicitly out of scope for M8-T1** (defer to later milestones):

- **M8-T2** Graphify MCP connection.
- **M8-T3** Playwright MCP integration.
- **M8-T4** Feature flags for optional integrations (though `fallback_to_mcp` config flag is IN scope).
- **M8-T5** E2E integration tests with real external services (beyond the mock + optional real hermes-agent gated by `HERMES_ACP_TEST`).
- **M8-T6** Independent QA report.
- **M9** Learning & Optimization.
- **M10** Deployment & Operations.
- **M11** Security hardening (beyond the basic scrubs and process isolation defined here).
- **M12** Documentation & closure.

**Future / deferred:**

- ACP-over-network transport (HTTP/SSE/WebSocket) — ACP currently stdio-only in hermes-agent; AI-OS bridge should not invent network transport.
- ACP session persistence / resumption — Hermes manages this internally; AI-OS only needs create/use/close.
- Provenance signing / attestation — M11 security hardening.
- Multi-hermes-agent load balancing — M10 deployment.
- Hermes-specific metrics export (Prometheus / OpenTelemetry) — M10.

---

## 25. Final Recommendation

**GO for implementation with three prerequisite clarifications:**

1. **ACP runtime dependency**: `agent-client-protocol` must be available in the runtime environment where M8-T1 is exercised. Since it is NOT installed in the current AI-OS venv (confirmed: `ModuleNotFoundError`), Terminal 2 MUST:
   - Either install it in CI / test env (`pip install agent-client-protocol`), or
   - Gate ACP integration tests behind `HERMES_ACP_TEST=1` and run MCP fallback tests in standard CI.

   **Recommendation**: gate real-ACP tests behind `HERMES_ACP_TEST=1`; run all unit and fallback tests in standard CI.

2. **hermes-agent path resolution**: The ACP adapter must locate the hermes-agent subprocess. Since hermes-agent is gitignored but present at `<repo-root>/hermes-agent/`, and AI-OS runs from `<repo-root>`, the default `cwd` should resolve relative to the AI-OS package root. Add a config override `hermes.cwd` to `defaults.yaml`.

3. **Session-ID lifecycle fix is mandatory, not optional**: `UserSimulationAgent` line 151–166 must be fixed as part of M8-T1. Without this fix, even the existing mock path is broken (session created ≠ session closed). The fix is small and behavior-preserving.

**Implementation order recommendation (parallel where possible):**

```
Day 1:     Fix psutil (hygiene) + define AcPAdapter interface + defaults.yaml
Day 2:     Implement AcPAdapter (stdio mock tests first) + acp_session.py
Day 3:     Update HermesBridge + fix UserSimulationAgent + unit tests
Day 4:     Integration tests (mock ACP server) + regression suite
Day 5:     Optional: real hermes-agent ACP E2E test (HERMES_ACP_TEST=1)
Day 6:     Final regression + report + handoff
```

**Acceptance gates before handoff:**

- Full suite green (1046 + new).
- M7 regression green.
- Provenance sample reviewed.
- Negative tests green.
- Terminal 2 report produced per §21.11.
- Terminal 3 QA handoff received.

---

## Appendix A — ACP Protocol Quick Reference (from hermes-agent)

| ACP Method | AI-OS Equivalent | Notes |
|------------|-----------------|-------|
| `initialize` | connect() | Handshake; returns protocol version, capabilities |
| `session/new` | new_session(cwd) | Returns `session_id` (UUID) |
| `session/prompt` | prompt(session_id, text, timeout) | Streams events; returns `PromptResponse(stop_reason, usage)` |
| `session/cancel` | cancel(session_id) | Interrupts in-flight prompt |
| `session/close` | close_session(session_id) | Terminates session |

**Stop reasons:**
- `"end_turn"` — normal completion.
- `"cancelled"` — interrupt received.
- `"refusal"` — session not found or auth failure.

**Auth:** Hermes advertises `hermes-setup` terminal auth method (for initial provider config). For headless AI-OS usage, auth may be skipped if no provider is configured (terminal setup method suffices).

---

## Appendix B — Existing EventTypes Reused

From `src/aios/events/core/types.py`:

- `EventType.HERMES_BRIDGE_TASK` — emitted when `execute_task` starts.
- `EventType.HERMES_BRIDGE_OBSERVATION` — emitted when observation is produced.

No new event types added.

---

## Appendix C — Test Count Projection

| Suite | Current | New | Projected |
|-------|---------|-----|-----------|
| `tests/unit/test_acp_adapter.py` | 0 | 11 | 11 |
| `tests/unit/test_hermes_bridge_acp.py` | 0 | 11 | 11 |
| `tests/integration/test_m8_hermes_acp.py` | 0 | 9 | 9 |
| `tests/unit/test_user_simulation_agent.py` | 5 | +2 | 7 |
| `tests/integration/test_m7_security.py` | 13 | 0 | 13 |
| Other existing | 1028 | 0 | 1028 |
| **Total** | **1046** | **+33** | **1079** |

---

## Appendix D — Defects Found During Inspection

| ID | Location | Description | Severity | Fix in M8-T1? |
|----|----------|-------------|----------|---------------|
| DEF-001 | `hermes_bridge.py:119–139` | `create_worker_session` stores result under MCP-returned session ID, not the pre-generated one passed by caller | Medium | Yes — fix lifecycle |
| DEF-002 | `user_simulation_agent.py:151–166` | Agent calls `_create_session_id()` locally but ignores `create_worker_session()` return; subsequent calls use wrong ID | Medium | Yes — consume return value |
| DEF-003 | `user_simulation_agent.py:298–306` | `_obs_to_dict` drops `provenance` field from observation | Low | Yes — include provenance |
| DEF-004 | `kernel.py:822` | `self._mcp_manager` does not exist; defensive `hasattr` is always False | Informational | Not a bug (defensive), but clarifies that MCP manager is global-only |
| DEF-005 | `pyproject.toml` | `psutil` not declared; test passes only when installed | Low | Yes — add to dev deps |

---

*End of M8-T1 Planning Document.*
