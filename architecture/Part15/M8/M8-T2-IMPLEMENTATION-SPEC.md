# M8-T2 Implementation Specification
## Playwright MCP Browser Integration — Terminal 2 Blueprint

**Date:** 2026-08-25
**Status:** READY FOR IMPLEMENTATION
**Prerequisites:** M7 (complete), M8-T1 (complete, independently verified)
**Terminal 1 Verdict:** M8-T2 PLANNING COMPLETE — READY FOR IMPLEMENTATION

---

## 1. Executive Summary

M8-T2 integrates **real Playwright MCP browser execution** into AI-OS as a deterministic browser testing substrate. Playwright provides:

- **Deterministic browser actions** (navigate, click, type, wait, screenshot, DOM capture)
- **Browser context isolation** (independent cookies, localStorage, sessionStorage per context)
- **Structured evidence** (screenshots, DOM snapshots, accessibility trees, page metadata)
- **Provenance-tracked execution** (execution_id, correlation_id, session_id per action)

Playwright is an **execution substrate only**. It MUST NOT become:
- verifier, judge, council, approval authority, rejection authority, security authority, or workflow authority

AI-OS retains all those authorities. Playwright returns **observations**; AI-OS decides.

This specification builds on the established patterns from M8-T1 (Hermes ACP integration):
- `BaseExecutionAdapter` pattern from `src/aios/adapters/base.py`
- `MCPManager` from `src/aios/core/mcp_manager.py` (existing, unchanged)
- `HermesBridge` provenance model from M8-T1
- `CapabilityManager` registration pattern from Task 15
- Error classification from M8-T1 (`ProtocolError` hierarchy)

---

## 2. Current Architecture

### 2.1 Existing Playwright References

| Location | What Exists |
|----------|-------------|
| `src/aios/adapters/accessibility_agency_adapter.py` | Uses `_default_axe_scan()` as production tool — **simulated, not real Playwright**. No actual browser launch. |
| `src/aios/core/ai_agency.py:400` | Comment references "Playwright MCP + axe-core" but no actual Playwright import |
| `config/mcp/` | No Playwright MCP server config exists |
| `pyproject.toml` | No `playwright` dependency declared |
| `tests/unit/test_agency_adapters.py` | Tests `AccessibilityAgencyAdapter` but against simulated axe-core, not real browser |

### 2.2 Existing MCP Infrastructure

| Component | Path | Status |
|-----------|------|--------|
| `MCPManager` | `src/aios/core/mcp_manager.py` | EXISTS — stdio/HTTP/SSE/WebSocket transports, tool discovery, tool call, provenance |
| `MCPService` | `src/aios/services/mcp.py` | EXISTS — event-driven facade over MCPManager |
| MCP configs | `config/mcp/*.json` | 8 configs exist (hermes_agent_ext, graphify, agent_reach, test variants) |
| Security validation | `src/aios/core/security_manager.py:1408` | `validate_mcp_server_before_connect()` exists |

### 2.3 Existing Adapter Pattern

```
BaseExecutionAdapter (src/aios/adapters/base.py)
  ├─ perspective: str
  ├─ __init__(tool=None)
  ├─ _default_tool(target, context) -> ExecutionResult
  ├─ execute(target, context) -> ExecutionResult
  └─ last_executions: list[ExecutionResult]

Concrete adapters (all follow this pattern):
  ├─ SecurityAgencyAdapter
  ├─ PerformanceAgencyAdapter
  ├─ AccessibilityAgencyAdapter     ← Playwright reference point (currently simulated)
  ├─ DocumentationAgencyAdapter
  ├─ ConcurrencyAgencyAdapter
  ├─ BugHunterAgencyAdapter
  ├─ ArchitectureAgencyAdapter
  ├─ ChaosAgencyAdapter
  └─ (M8-T1 added AcPAdapter, HermesBridge for hermes-agent)
```

### 2.4 Existing Capability Registry

```
CapabilityManager (src/aios/core/capability_manager.py)
  ├─ register(capability_id, facade, provider_id, ...) -> CapabilityRegistryEntry
  ├─ deregister(capability_id) -> bool
  ├─ get_capability(capability_id) -> CapabilityRegistryEntry | None
  ├─ discover_by_facade(facade) -> list[CapabilityRegistryEntry]
  └─ invoke(capability_id, input_payload) -> CapabilityRegistryEntry

No capabilities are currently registered at kernel startup.
```

### 2.5 Existing Evidence Model

```
TestingEvidence (src/aios/core/testing_evidence.py)
  ├─ perspective: str
  ├─ target: str
  ├─ test_id: str
  ├─ actions: list[dict]
  ├─ observations: list[dict]
  ├─ expected: str
  ├─ observed: str
  ├─ severity: str ("critical"|"high"|"medium"|"low")
  ├─ confidence: float [0.0, 1.0]
  ├─ proof: list[str]
  ├─ provenance: Provenance
  ├─ environment: dict
  ├─ timestamp: datetime
  ├─ reproducibility: float [0.0, 1.0]
  └─ verdict: str ("pass"|"fail"|"inconclusive")
```

### 2.6 Existing Session/Provenance Model (from M8-T1)

```python
# HermesObservation.provenance (M8-T1 established this schema)
{
    "task_id": str,
    "execution_id": str,       # UUID per execute call
    "session_id": str,         # server-generated session ID
    "correlation_id": str,     # UUID linking request→response
    "protocol": str,           # "acp" | "mcp" | "acp_fallback"
    "adapter": str,            # "acp_adapter" | "mcp_manager"
    "timestamp": str,          # ISO 8601 UTC
    "request_metadata": {
        "task_type": str,
        "description": str,    # truncated to 200 chars
        "parameters_hash": str,  # SHA-256, no secrets
    },
    "target": {"server_id": str},
    "exit_status": str,        # "completed" | "cancelled" | "error" | "timeout"
    "errors": list[str],
    "environment": str,
}
```

---

## 3. Repository Findings

### 3.1 Inventory

| Category | Status | Details |
|----------|--------|---------|
| 1. Existing Playwright code | **MISSING** | No `playwright` import anywhere in `src/`. `accessibility_agency_adapter.py` references it but uses simulated axe-core only. |
| 2. Existing MCP infrastructure | **EXISTS** | `MCPManager` fully implemented with stdio/HTTP/SSE/WebSocket, tool discovery, provenance tracking |
| 3. Existing browser capability | **MISSING** | No browser capability registered; no browser adapter exists |
| 4. Existing capability registry | **EXISTS** | `CapabilityManager` fully implemented; zero capabilities registered |
| 5. Existing adapter interfaces | **EXISTS** | `BaseExecutionAdapter` with `execute()`, `ExecutionResult`, `ExecutionStatus` |
| 6. Existing evidence model | **EXISTS** | `TestingEvidence`, `Provenance`, `normalize_user_simulation()` |
| 7. Existing session model | **PARTIAL** | `HermesBridge` has session tracking; no browser-specific session model |
| 8. Existing provenance model | **EXISTS** | M8-T1 established provenance schema; Playwright needs same pattern |
| 9. Existing testing hooks | **EXISTS** | `TestOrchestratorService`, `FinalJudgeAgency`, council synthesis |
| 10. Existing mock servers | **EXISTS** | `mock_hermes_server.py` (MCP), `mock_hermes_acp_server.py` (ACP) |
| 11. Existing integration tests | **EXISTS** | `test_m8_hermes_acp.py` (9 tests), `test_m7_*.py` (18 tests) |
| 12. Existing external capability loading | **MISSING** | No mechanism to load external MCP servers as capabilities |
| 13. Existing configuration system | **EXISTS** | `config/defaults.yaml` has hermes section; no playwright section |
| 14. Existing security controls | **EXISTS** | `SecurityManager.validate_mcp_server_before_connect()`, env scrubbing, provenance hashing |

### 3.2 Key Finding: Playwright MCP Is Not Installed

```bash
# Playwright is NOT in pyproject.toml dependencies
# pip show playwright → NOT FOUND in clean environment
# playwright install → not run
```

The project uses `mcp` package (Python MCP SDK) for MCP client-server communication. Playwright MCP is a separate Node.js-based MCP server (`@playwright/mcp`).

### 3.3 How Playwright MCP Works

Playwright MCP is an **MCP server** provided by Microsoft:
- Package: `@playwright/mcp` (Node.js)
- Transport: stdio (JSON-RPC 2.0 over stdin/stdout)
- Tools exposed: `browser_navigate`, `browser_click`, `browser_type_text`, `browser_snapshot`, `browser_press_key`, `browser_take_screenshot`, `browser_close`, etc.
- Sessions managed via `browser_new_context`, `browser_close_context`

AI-OS connects to it the **same way** it connects to `mock_hermes_server`: via `MCPManager` with stdio transport.

---

## 4. Existing Playwright/MCP Infrastructure

### 4.1 What EXISTS (reusable)

1. **MCPManager** — Full stdio/HTTP/SSE/WebSocket MCP client. Handles:
   - Process lifecycle (`asyncio.create_subprocess_exec`)
   - JSON-RPC 2.0 framing
   - Tool discovery (`tools/list`)
   - Tool invocation (`tools/call`)
   - Provenance tracking per call
   - Security validation gate (`validate_mcp_server_before_connect`)
   - Multi-transport support

2. **BaseExecutionAdapter** — Pattern for all agency adapters:
   - Injected `tool` callable for testability
   - `_default_tool()` for production path
   - `execute(target, context)` returns `ExecutionResult`
   - `ExecutionResult` carries `tool`, `status`, `findings`, `metrics`, `raw`, `executed_at`

3. **CapabilityManager** — Registry for external capabilities:
   - `register(capability_id, facade, provider_id, ...)`
   - `invoke(capability_id, input_payload)`
   - Uses canonical EventTypes (SERVICE_STARTED, SKILL_EXECUTED, etc.)

4. **SecurityManager** — MCP server validation:
   - `validate_mcp_server_before_connect(config)` enforces security gates
   - MCP server configs validated before connection

5. **TestingEvidence schema** — Evidence record format for all perspectives

6. **HermesBridge provenance model** — Established pattern for execution provenance

### 4.2 What is MISSING for Playwright

1. **Playwright MCP adapter** — New class implementing `BaseExecutionAdapter`
2. **Playwright MCP server config** — `config/mcp/playwright_mcp.json`
3. **Playwright capability registration** — Register in CapabilityManager
4. **Browser session isolation** — Browser context management
5. **Playwright mock server** — For unit tests without real browser
6. **Configuration section** — `playwright:` in `config/defaults.yaml`
7. **Playwright dependency** — `playwright` Python package + browser binaries

---

## 5. Gap Analysis

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| Real Playwright browser execution | Simulated axe-core only | **COMPLETE GAP** — no Playwright import, no browser launch |
| Playwright MCP server connection | Not configured | **COMPLETE GAP** — no `config/mcp/playwright_mcp.json` |
| Browser session isolation | Not implemented | **COMPLETE GAP** — no browser context management |
| Deterministic browser actions | Not implemented | **COMPLETE GAP** — no selector-based actions |
| Screenshot evidence capture | Not implemented | **COMPLETE GAP** — no screenshot infrastructure |
| DOM / accessibility evidence | Not implemented | **COMPLETE GAP** — no snapshot infrastructure |
| Page state tracking | Not implemented | **COMPLETE GAP** |
| Network event capture | Not implemented | **COMPLETE GAP** (optional) |
| Provenance for browser actions | Not implemented | **COMPLETE GAP** — must follow M8-T1 pattern |
| Capability registration | Zero capabilities registered | **COMPLETE GAP** |
| Security validation for browser | Partial (MCPManager validates) | **PARTIAL** — needs Playwright-specific rules |
| Error classification for browser | Not implemented | **COMPLETE GAP** — navigation timeout, selector not found, etc. |
| Mock Playwright MCP server | Not implemented | **COMPLETE GAP** — needed for CI without browser |
| Real browser E2E tests | Not implemented | **COMPLETE GAP** |

---

## 6. Target Architecture

### 6.1 Architecture Diagram

```
AI-OS Kernel
  │
  ├─ CapabilityManager
  │    └─ register("playwright_browser", "browser", "playwright_mcp")
  │
  ├─ MCPManager
  │    └─ connect("playwright_mcp") → stdio subprocess
  │         └─ @playwright/mcp (Node.js MCP server)
  │
  ├─ PlaywrightMCPAdapter (NEW — implements BaseExecutionAdapter)
  │    ├─ __init__(tool=None) — injected for testability
  │    ├─ _default_tool(target, context) — real Playwright MCP execution
  │    ├─ execute(target, context) → ExecutionResult
  │    └─ BrowserSessionManager (internal) — session isolation
  │
  └─ AccessibilityAgency (existing)
       └─ _get_adapter() → PlaywrightMCPAdapter()  [CHANGE]
```

### 6.2 Data Flow

```
TestOrchestratorService
  ↓ dispatches to AccessibilityAgency
AccessibilityAgency.review(request)
  ↓ calls _run_adapter()
AccessibilityAgencyAdapter.execute(target, context)
  ↓ calls _default_tool()
PlaywrightMCPAdapter._default_tool(target, context)
  ↓ resolves to Playwright MCP tool
MCPManager.call_tool("playwright_mcp", tool_name, arguments)
  ↓ stdio JSON-RPC
@playwright/mcp server
  ↓ executes in isolated browser context
returns tool result (screenshot, DOM, navigation status, etc.)
  ↓
ExecutionResult (structured observation, NOT verdict)
  ↓
AccessibilityAgency._evidence_to_response()
  ↓
AgencyResponse (observations only)
  ↓
TestOrchestratorService.normalize_evidence()
  ↓
TestingEvidence (with verdict computed by AI-OS, not Playwright)
```

### 6.3 Layer Responsibility Matrix

| Layer | Responsibility | Authority |
|-------|---------------|-----------|
| Playwright MCP | Execute browser actions, capture evidence | Execution ONLY |
| PlaywrightMCPAdapter | Translate AI-OS requests to MCP tool calls | Adaptation ONLY |
| MCPManager | Transport layer (stdio JSON-RPC) | Transport ONLY |
| AccessibilityAgency | Orchestrate accessibility scan | Observation gathering ONLY |
| TestOrchestratorService | Normalize evidence, coordinate perspectives | Orchestration ONLY |
| TestingCouncil | Synthesize evidence, produce verdict | Decision authority |
| FinalJudgeAgency | Final judgment | Final authority |

---

## 7. Capability Registry Integration

### 7.1 Registration

Playwright MCP must be registered as a capability in `CapabilityManager`. This follows the same pattern as other capabilities (none currently registered, but the mechanism exists).

```python
# In kernel.py _init_m7_testing() or new _init_playwright() method:
capability_manager.register(
    capability_id="playwright_browser",
    facade="browser",
    provider_id="playwright_mcp",
    provider_metadata={
        "server_id": "playwright_mcp",
        "transport": "stdio",
        "command": ["node", "<path>/node_modules/@playwright/mcp/index.js"],
        "timeout_seconds": 60,
    },
    security_context={
        "requires_validation": True,
        "allowed_actions": ["navigate", "click", "type", "snapshot", "screenshot"],
    },
    tags=("browser", "playwright", "accessibility", "deterministic"),
)
```

### 7.2 Why Registration Matters

- **Discovery**: Other components can discover browser capabilities by facade
- **Security gating**: Registered capabilities go through SecurityManager validation
- **Lifecycle**: CapabilityManager tracks registered capabilities for shutdown/cleanup
- **Extensibility**: Future capabilities (Graphify, SkillSpecTor) follow the same pattern

### 7.3 Kernel Wiring

Add to `kernel.py` `_init_m7_testing()` or new `_init_capabilities()` method:

```python
# After existing capability manager initialization:
if self._capability_manager:
    self._capability_manager.register(
        capability_id="playwright_browser",
        facade="browser",
        provider_id="playwright_mcp",
        ...
    )
```

**Must NOT change:** Kernel phase ordering, LifecycleManager integration, Core Manager lifecycle.

---

## 8. Browser Session Architecture

### 8.1 Isolation Hierarchy

```
Execution
  ↓
Browser Session (one per task execution)
  ↓
Browser Context (isolated: cookies, localStorage, sessionStorage, cache)
  ↓
Page (isolated: DOM, navigation state, cookies inherit from context)
```

### 8.2 Session Identity

Each browser session carries these identifiers for provenance:

```python
{
    "execution_id": str,      # UUID — unique per AI-OS execution call
    "session_id": str,        # UUID — unique per browser context
    "correlation_id": str,    # UUID — links request → response
    "task_id": str,           # Caller-provided task identifier
    "browser_context_id": str, # Playwright browser context ID (if available)
    "page_id": str,           # Playwright page ID (if available)
}
```

### 8.3 Isolation Requirements

**Must be isolated between sessions:**

| State | Isolated? | Mechanism |
|-------|-----------|-----------|
| Cookies | YES | New browser context per session |
| localStorage | YES | New browser context per session |
| sessionStorage | YES | New browser context per session |
| Authentication state | YES | New browser context per session |
| Cache | YES | New browser context per session |
| Page state | YES | New page per context |
| Downloads | YES | Each context has its own download directory |
| Screenshots | YES | Written to session-specific directory |
| Network logs | YES | Captured per-context, not shared |

**Must NOT leak between sessions:**
- No shared cookie jars
- No shared localStorage
- No shared authentication
- No shared navigation history
- No shared DOM

### 8.4 Session Lifecycle

```
create_session(execution_id) → session_id
  ├─ Creates new BrowserContext (isolated)
  ├─ Creates new Page within context
  ├─ Records session metadata
  └─ Returns session_id

execute_action(session_id, action, args) → result
  ├─ Validates session is active
  ├─ Calls MCP tool via MCPManager
  ├─ Collects evidence (screenshot, DOM snapshot)
  └─ Returns ExecutionResult

collect_evidence(session_id) → evidence
  ├─ Screenshot (required)
  ├─ DOM snapshot (required)
  ├─ Page metadata (required: URL, title, status)
  └─ Optional: accessibility tree, network events

close_session(session_id) → None
  ├─ Closes page
  ├─ Closes context
  ├─ Removes from active sessions
  └─ Cleans up resources
```

### 8.5 Context Reuse vs. Creation

- **Default**: Create new context per session (maximum isolation)
- **Optional**: Reuse context within a single execution for performance
- **Configurable**: `playwright.context_reuse: false` (default)

---

## 9. Deterministic Execution

### 9.1 Determinism Requirements

Playwright actions MUST be deterministic. The adapter enforces:

1. **Explicit selectors** — No auto-wait heuristics that vary by timing
2. **Stable element identification** — Use `data-testid`, `role`, or explicit XPath
3. **Explicit waits** — `wait_for_selector()`, `wait_for_url()`, not arbitrary sleeps
4. **Navigation waits** — `wait_until="networkidle"` or `"domcontentloaded"`
5. **Action timeouts** — Configurable per-action timeout (default: 30s)
6. **Deterministic ordering** — Actions executed in exact order specified
7. **Page readiness** — Verify page is loaded before taking evidence
8. **Screenshot timing** — After explicit readiness check, not during navigation
9. **DOM capture timing** — After explicit readiness check

### 9.2 Forbidden Patterns

```python
# FORBIDDEN — arbitrary sleep
time.sleep(5)

# FORBIDDEN — hidden retry with random backoff
for i in range(10):
    try:
        return click(selector)
    except:
        time.sleep(random.uniform(0.1, 1.0))  # nondeterministic

# FORBIDDEN — implicit wait
page.click(selector)  # without explicit wait

# FORBIDDEN — non-deterministic action ordering
actions = shuffled(actions)  # random order
```

### 9.3 Enforced Patterns

```python
# REQUIRED — explicit wait
page.wait_for_selector(selector, state="visible", timeout=30000)

# REQUIRED — navigation wait
page.goto(url, wait_until="networkidle", timeout=30000)

# REQUIRED — screenshot after readiness
page.wait_for_load_state("networkidle")
screenshot = page.screenshot()

# REQUIRED — deterministic action ordering
for action in ordered_actions:
    execute_deterministic(action)
```

### 9.4 Timeout Configuration

| Timeout | Default | Config Key |
|---------|---------|------------|
| Navigation timeout | 30s | `playwright.timeout.navigate` |
| Action timeout | 30s | `playwright.timeout.action` |
| Screenshot timeout | 10s | `playwright.timeout.screenshot` |
| Context creation timeout | 15s | `playwright.timeout.context_create` |
| Overall execution timeout | 120s | `playwright.timeout.execution` |

---

## 10. Evidence Architecture

### 10.1 Required Evidence

Every browser execution MUST produce:

| Evidence | Source | Format | Purpose |
|----------|--------|--------|---------|
| **Screenshot** | `page.screenshot()` | base64 PNG | Visual proof of page state |
| **URL** | `page.url` | string | Navigation target verification |
| **Title** | `page.title()` | string | Page identity verification |
| **DOM Snapshot** | `page.inner_html()` or `page.evaluate()` | string | Content verification |
| **Page State** | `{url, title, status, load_state}` | dict | Readiness verification |
| **Action Result** | MCP tool response | dict | Execution outcome |
| **Timing** | `{started_at, finished_at, duration_ms}` | dict | Performance verification |

### 10.2 Optional Evidence

| Evidence | Source | Format | When Included |
|----------|--------|--------|---------------|
| **Accessibility Tree** | `page.accessibility.snapshot()` | dict | When `accessibility=True` in context |
| **Network Events** | `page.on('request')`, `page.on('response')` | list[dict] | When `capture_network=True` |
| **Console Messages** | `page.on('console')` | list[dict] | When `capture_console=True` |
| **Element State** | `page.get_attribute()`, `page.is_visible()` | dict | When specific element queried |

### 10.3 Sensitive Evidence

Evidence that MUST be redacted or excluded:

| Evidence | Treatment |
|----------|-----------|
| URLs containing tokens/credentials | Redact query parameters |
| DOM containing passwords/API keys | Redact via pattern matching |
| Screenshots containing sensitive data | Flag but include (verifier decides) |
| Network headers with auth tokens | Redact `Authorization`, `Cookie` headers |
| localStorage with secrets | Exclude from evidence |

### 10.4 Forbidden Evidence

The following MUST NEVER be captured:

- Full localStorage contents (only checked for presence/absence)
- Full sessionStorage contents
- Browser cookie jar contents (only checked for specific cookies)
- Downloaded file contents
- Console error stack traces containing internal paths

### 10.5 Evidence-to-Provenance Binding

Every evidence item binds to:

```python
{
    "task_id": str,
    "execution_id": str,
    "session_id": str,
    "correlation_id": str,
    "timestamp": str,  # ISO 8601 UTC
    "adapter": "playwright_mcp",
    "protocol": "mcp",
    "action": str,     # "navigate" | "click" | "type" | "screenshot" | "snapshot"
    "target": str,     # selector or URL
    "result_summary": str,  # truncated result description
}
```

---

## 11. Provenance

### 11.1 Mandatory Fields

Playwright browser execution provenance extends the M8-T1 provenance schema:

```python
{
    # M8-T1 base fields
    "task_id": str,
    "execution_id": str,
    "session_id": str,
    "correlation_id": str,
    "protocol": "mcp",
    "adapter": "playwright_mcp",
    "timestamp": str,
    "request_metadata": {
        "task_type": str,      # "browser_navigate" | "browser_click" | etc.
        "description": str,    # truncated to 200 chars
        "parameters_hash": str,  # SHA-256 of parameters
    },
    "target": {"server_id": "playwright_mcp"},
    "exit_status": str,        # "completed" | "cancelled" | "error" | "timeout"
    "errors": list[str],
    "environment": "ai_os_playwright_mcp",

    # Playwright-specific fields
    "browser": {
        "type": str,           # "chromium" | "firefox" | "webkit"
        "headless": bool,
        "version": str,        # browser version
    },
    "context": {
        "context_id": str,     # Playwright browser context ID
        "storage_state": str,  # "isolated" | "persistent" | "none"
    },
    "page": {
        "page_id": str,        # Playwright page ID
        "url": str,            # final URL after navigation
        "title": str,          # page title
        "load_state": str,     # "load" | "domcontentloaded" | "networkidle"
    },
    "action": {
        "tool_name": str,      # MCP tool name
        "selector": str | None,# CSS selector if applicable
        "timeout_ms": int,     # timeout used
    },
    "evidence": {
        "screenshot_available": bool,
        "snapshot_available": bool,
        "network_captured": bool,
        "evidence_count": int,
    },
}
```

### 11.2 Parameter Hashing

Same pattern as M8-T1 — SHA-256 hash of sorted JSON parameters:

```python
def _hash_parameters(self, params: dict[str, Any]) -> str:
    serialized = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
```

---

## 12. Security

### 12.1 Browser-Specific Security Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Credentials in URLs | HIGH | Redact query parameters containing `token`, `key`, `secret`, `password` |
| Credentials in localStorage | HIGH | Do not capture localStorage contents; only check presence |
| Credentials in cookies | HIGH | Do not include cookie jar in evidence; only check specific cookies |
| Screenshots containing secrets | MEDIUM | Flag sensitive content; include but mark for reviewer attention |
| DOM containing secrets | MEDIUM | Redact patterns: `sk-.*`, `Bearer .*`, `password.*`, `api_key.*` |
| Arbitrary navigation | HIGH | Restrict navigation to configured allowed domains |
| File upload/download | MEDIUM | Disable file downloads in headless mode; block file:// protocols |
| Cross-origin access | MEDIUM | Same-origin policy enforced by browser; do not bypass |
| Browser persistence | LOW | Use ephemeral contexts; clean up all contexts on session close |
| Process escape via MCP | HIGH | MCPManager validates server config before connect; stdio only |
| Environment variable leakage | MEDIUM | Scrub env vars matching `(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)` |

### 12.2 Required Protections

1. **URL Redaction**: Strip sensitive query parameters before logging/capturing
   ```python
   SENSITIVE_QUERY_PARAMS = {"token", "key", "secret", "password", "auth", "credential"}
   ```

2. **DOM Redaction**: Redact common secret patterns in captured HTML
   ```python
   SECRET_PATTERNS = [
       r'(?:sk[-_]?[a-zA-Z0-9]{20,})',      # API keys
       r'(?:Bearer\s+[a-zA-Z0-9._-]+)',      # Bearer tokens
       r'(?:password\s*[:=]\s*\S+)',          # password assignments
       r'(?:api[_-]?key\s*[:=]\s*\S+)',       # API key assignments
   ]
   ```

3. **Allowed Domain Restriction**: If `playwright.allowed_domains` is configured, reject navigation to non-matching domains

4. **No File Protocol**: Reject `file://` URLs (prevents local file access)

5. **Headless by Default**: Browser runs headless unless `playwright.headed=true`

6. **Ephemeral Storage**: Use `browser.new_context(storage_state=None)` for full isolation

7. **Download Blocking**: Disable downloads via `set_ignore_https_errors(False)` and block download events

### 12.3 Network Header Redaction

When capturing network events:
- Redact `Authorization` header
- Redact `Cookie` header
- Redact `Proxy-Authorization` header
- Keep all other headers

---

## 13. Authority Boundaries

### 13.1 Playwright MCP MAY

- Navigate to URLs
- Click elements
- Type text
- Submit forms
- Take screenshots
- Capture DOM snapshots
- Wait for selectors
- Press keys
- Execute JavaScript (via `evaluate()`)
- Return structured observations

### 13.2 Playwright MCP MAY NOT

- Decide whether a test passed or failed
- Approve or reject any result
- Issue security verdicts
- Become the final reviewer
- Modify AI-OS governance state
- Access kernel managers (SecurityManager, CouncilManager, etc.)
- Emit events directly to EventBus
- Call `CapabilityManager.register()` or modify registry
- Write to disk outside evidence directory
- Access filesystem (no `fs` tools exposed)

### 13.3 AI-OS Retains These Authorities

| Authority | Owner |
|-----------|-------|
| Testing decision | `TestOrchestratorService` |
| Evidence normalization | `TestOrchestratorService.normalize_evidence()` |
| Council synthesis | `CouncilManager.synthesize()` |
| Final verdict | `FinalJudgeAgency` |
| Security validation | `SecurityManager` |
| Capability registration | `CapabilityManager` |
| Lifecycle management | `LifecycleManager` |

### 13.4 Code Enforcement

The adapter MUST NOT contain any of these patterns:
```python
# FORBIDDEN in adapter code:
from aios.core.security_manager import ...  # No direct security calls
from aios.core.council_manager import ...   # No council access
from aios.core.state import ...             # No state mutation
self._event_bus.publish(...)                # No direct event emission
return {"verdict": "pass"}                  # No verdict in results
```

---

## 14. Error Model

### 14.1 Error Classification

| Error | Category | Retryable | Observation |
|-------|----------|-----------|-------------|
| `ProtocolUnavailableError` | Infrastructure | No | Raised (not observed) |
| `TransportConnectionError` | Infrastructure | Yes (max 3) | Raised (not observed) |
| `SessionCreationTimeout` | Infrastructure | Yes (once) | Raised (not observed) |
| `SessionNotFoundError` | Session | No | `success=False`, error recorded |
| `NavigationTimeout` | Browser Action | No | `success=False`, error="navigation_timeout" |
| `SelectorNotFound` | Browser Action | No | `success=False`, error="selector_not_found" |
| `ActionTimeout` | Browser Action | Yes (once) | `success=False`, error="action_timeout" |
| `PageCrashed` | Browser | No | `success=False`, error="page_crashed" |
| `BrowserCrashed` | Infrastructure | No | Raised |
| `MalformedResponseError` | Protocol | No | `success=False`, error="malformed_response" |
| `TransportDisconnectError` | Infrastructure | Yes (max 3) | Raised (not observed) |
| `ExecutionCancelled` | User | No | `success=False`, error="cancelled" |
| `CleanupTimeout` | Cleanup | No | Logged warning, continues |
| `SecretLeakDetectedError` | Security | No | Raised (security-critical) |

### 14.2 Error Hierarchy

```python
class PlaywrightError(Exception):
    """Base error for Playwright MCP adapter."""

class PlaywrightInfrastructureError(PlaywrightError):
    """MCP connection, process, or transport failures."""

class PlaywrightSessionError(PlaywrightError):
    """Session lifecycle failures."""

class PlaywrightActionError(PlaywrightError):
    """Browser action failures (navigation, click, type, etc.)."""

class PlaywrightEvidenceError(PlaywrightError):
    """Evidence capture failures."""

class PlaywrightSecurityError(PlaywrightError):
    """Security violations (secret leakage, unauthorized navigation)."""
```

### 14.3 Distinction: Execution Failure vs. Verification Result

```
Browser action fails (selector not found)
  → ExecutionResult(status=FAILURE, findings=[...])
  → NOT a verification verdict

Application is inaccessible (navigation timeout)
  → ExecutionResult(status=ERROR, findings=[...])
  → NOT a verification verdict

Test council determines pass/fail from evidence
  → TestingEvidence(verdict="fail")
  → This IS a verification verdict
```

**Critical:** `ExecutionResult.is_failure()` returns True for infrastructure errors. The council/verifier maps these to evidence but does NOT treat them as application defects.

---

## 15. Lifecycle / Cleanup

### 15.1 Full Lifecycle

```
1. START
   ├─ MCPManager.connect("playwright_mcp")
   ├─ Tool discovery (tools/list)
   └─ Capability registration (optional)

2. INIT
   ├─ Browser launch (headless Chromium)
   └─ Default context created

3. SESSION CREATE
   ├─ browser.new_context() → isolated context
   ├─ context.new_page() → isolated page
   ├─ Session metadata recorded
   └─ Return session_id

4. EXECUTE
   ├─ Validate session active
   ├─ Call MCP tool (navigate/click/type/screenshot/snapshot)
   ├─ Collect evidence
   └─ Return ExecutionResult

5. EVIDENCE COLLECT
   ├─ Screenshot (base64)
   ├─ DOM snapshot
   ├─ Page metadata
   └─ Timing data

6. SESSION CLOSE
   ├─ page.close()
   ├─ context.close()
   ├─ Remove from active sessions
   └─ Clean up resources

7. SHUTDOWN
   ├─ Close all remaining sessions
   ├─ MCPManager.disconnect("playwright_mcp")
   └─ Process terminated
```

### 15.2 Cleanup Behavior

| Scenario | Cleanup Action |
|----------|---------------|
| Success | Close page, close context, remove session |
| Failure | Close page (if open), close context, remove session, log error |
| Timeout | Cancel in-flight action, close page, close context, remove session |
| Cancellation | Cancel in-flight action, close page, close context, remove session |
| Process crash | Catch exception, attempt graceful close, log fatal |
| Cleanup failure | Log warning, mark session as closed anyway (idempotent) |

### 15.3 Leak Prevention

```python
# At adapter shutdown:
async def cleanup_all(self) -> None:
    for session_id in list(self._active_sessions.keys()):
        try:
            await self.close_session(session_id)
        except Exception as e:
            logger.warning(f"Cleanup failed for session {session_id}: {e}")
    # Verify no processes left
    assert len(self._active_sessions) == 0
```

---

## 16. Test Strategy

### 16.1 Test Categories

| Category | Coverage | CI Status |
|----------|----------|-----------|
| Unit tests (mocked MCP) | All adapter logic | **MANDATORY** |
| Unit tests (mock server) | Protocol round-trip | **MANDATORY** |
| Integration tests (mock) | Full flow with mock server | **MANDATORY** |
| Integration tests (real browser) | E2E with real Playwright | **CONDITIONAL** |
| Negative tests | Authority boundaries, security | **MANDATORY** |
| Regression tests | M7 + M8-T1 | **MANDATORY** |

### 16.2 Test Plan (33 Tests)

#### A. Adapter Creation (3 tests)
| # | Test | Scenario |
|---|------|----------|
| A1 | `test_adapter_creation` | Instantiates with default config |
| A2 | `test_adapter_injects_tool` | Custom tool injected for testing |
| A3 | `test_adapter_default_tool` | `_default_tool` raises NotImplementedError without injection |

#### B. MCP Connection (4 tests)
| # | Test | Scenario |
|---|------|----------|
| B1 | `test_mcp_connect_success` | Connects to mock MCP server |
| B2 | `test_mcp_connect_process_not_found` | Missing node → raises ProtocolUnavailableError |
| B3 | `test_mcp_connect_timeout` | Server doesn't respond → raises SessionCreationTimeout |
| B4 | `test_mcp_disconnect` | Disconnect cleans up process |

#### C. Tool Discovery (2 tests)
| # | Test | Scenario |
|---|------|----------|
| C1 | `test_tool_discovery` | Discovers Playwright MCP tools |
| C2 | `test_tool_not_found` | Calls unknown tool → raises ValueError |

#### D. Browser Launch (2 tests)
| # | Test | Scenario |
|---|------|----------|
| D1 | `test_browser_launch` | Mock server responds to launch |
| D2 | `test_browser_launch_failure` | Server returns error → raises PlaywrightInfrastructureError |

#### E. Context Isolation (3 tests)
| # | Test | Scenario |
|---|------|----------|
| E1 | `test_context_isolation` | Two contexts don't share state |
| E2 | `test_context_no_shared_cookies` | Cookies isolated between contexts |
| E3 | `test_context_no_shared_storage` | localStorage isolated between contexts |

#### F. Page Isolation (2 tests)
| # | Test | Scenario |
|---|------|----------|
| F1 | `test_page_isolation` | Two pages in different contexts are independent |
| F2 | `test_page_navigation_isolation` | Navigating one page doesn't affect another |

#### G. Deterministic Navigation (2 tests)
| # | Test | Scenario |
|---|------|----------|
| G1 | `test_navigation_success` | Navigate to URL, verify URL in result |
| G2 | `test_navigation_timeout` | Navigate to unreachable URL → timeout error |

#### H. Click (2 tests)
| # | Test | Scenario |
|---|------|----------|
| H1 | `test_click_success` | Click element, verify action recorded |
| H2 | `test_click_selector_not_found` | Click missing selector → SelectorNotFound error |

#### I. Typing (2 tests)
| # | Test | Scenario |
|---|------|----------|
| I1 | `test_type_text_success` | Type text, verify in result |
| I2 | `test_type_selector_not_found` | Type into missing selector → error |

#### J. Form Interaction (2 tests)
| # | Test | Scenario |
|---|------|----------|
| J1 | `test_form_submit` | Fill form and submit, verify navigation |
| J2 | `test_form_validation` | Submit invalid form, observe validation message |

#### K. Screenshot Capture (2 tests)
| # | Test | Scenario |
|---|------|----------|
| K1 | `test_screenshot_capture` | Screenshot returned as base64 |
| K2 | `test_screenshot_full_page` | Full-page screenshot works |

#### L. DOM Evidence (2 tests)
| # | Test | Scenario |
|---|------|----------|
| L1 | `test_dom_snapshot` | DOM snapshot captured |
| L2 | `test_dom_snapshot_selector` | DOM snapshot for specific selector |

#### M. Network Evidence (1 test)
| # | Test | Scenario |
|---|------|----------|
| M1 | `test_network_events_optional` | Network events captured when enabled |

#### N. Provenance (2 tests)
| # | Test | Scenario |
|---|------|----------|
| N1 | `test_provenance_complete` | All mandatory provenance fields present |
| N2 | `test_provenance_no_secrets` | No plaintext secrets in provenance |

#### O. Timeout (2 tests)
| # | Test | Scenario |
|---|------|----------|
| O1 | `test_navigation_timeout` | Navigation timeout handled gracefully |
| O2 | `test_action_timeout` | Action timeout handled gracefully |

#### P. Cancellation (1 test)
| # | Test | Scenario |
|---|------|----------|
| P1 | `test_cancellation` | Cancel in-flight action, session remains usable |

#### Q. Browser Crash (1 test)
| # | Test | Scenario |
|---|------|----------|
| Q1 | `test_browser_crash` | Server crash mid-execution → proper error |

#### R. MCP Crash (1 test)
| # | Test | Scenario |
|---|------|----------|
| R1 | `test_mcp_crash` | MCP process dies → TransportDisconnectError |

#### S. Malformed Response (1 test)
| # | Test | Scenario |
|---|------|----------|
| S1 | `test_malformed_response` | Bad JSON response → MalformedResponseError |

#### T. Cleanup (1 test)
| # | Test | Scenario |
|---|------|----------|
| T1 | `test_cleanup_all` | cleanup_all removes all sessions |

#### U. Session Leakage (1 test)
| # | Test | Scenario |
|---|------|----------|
| U1 | `test_no_session_leakage` | After close, session not in active list |

#### V. Secret Leakage (1 test)
| # | Test | Scenario |
|---|------|----------|
| V1 | `test_no_secret_leakage` | URLs with tokens are redacted in evidence |

#### W. Authority Boundary (1 test)
| # | Test | Scenario |
|---|------|----------|
| W1 | `test_no_verdict_in_result` | ExecutionResult has no verdict field |

#### X. Capability Registry (1 test)
| # | Test | Scenario |
|---|------|----------|
| X1 | `test_capability_registered` | Playwright capability registered in CapabilityManager |

#### Y. Real Browser E2E (1 test)
| # | Test | Scenario |
|---|------|----------|
| Y1 | `test_real_browser_e2e` | If `PLAYWRIGHT_E2E_TEST=1`, run real browser test |

#### Z. Regression (0 new — existing suite)
| # | Test | Scenario |
|---|------|----------|
| Z1 | `test_regression_all` | Full `pytest tests/ -q` → all pass |

### 16.3 Expected Test Count

| Before M8-T2 | New M8-T2 Tests | After M8-T2 |
|-------------|-----------------|-------------|
| 1046 (passing) | 33 | **1079** |

### 16.4 Mock Server

Create `src/aios/adapters/mock_playwright_mcp_server.py` — a minimal MCP server that simulates Playwright MCP tools:

```python
# Tools exposed:
# - browser_navigate
# - browser_click
# - browser_type_text
# - browser_snapshot
# - browser_press_key
# - browser_take_screenshot
# - browser_new_context
# - browser_close_context
# - browser_close
# - get_playwright_version

# Behavior:
# - In-memory session store (like mock_hermes_server)
# - Returns deterministic responses
# - Supports HERMES_MOCK_PLAYWRIGHT=1 env flag
```

---

## 17. File-Level Change Plan

### 17.1 NEW: `src/aios/adapters/playwright_mcp_adapter.py`

**Purpose:** Playwright MCP adapter implementing `BaseExecutionAdapter`.

**Changes:** Create from scratch.

**Why necessary:** Core M8-T2 deliverable — bridges MCPManager to Playwright browser actions.

**Dependencies:** `mcp_manager.py`, `base.py`, `uuid`, `hashlib`, `logging`, `asyncio`.

**Interface:**
```python
class PlaywrightMCPAdapter(BaseExecutionAdapter):
    perspective = "playwright_browser"

    def __init__(
        self,
        tool: Tool | None = None,
        server_id: str = "playwright_mcp",
        timeout_seconds: int = 30,
        allowed_domains: tuple[str, ...] | None = None,
        headless: bool = True,
    ) -> None: ...

    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def create_session(self, execution_id: str) -> str: ...
    async def close_session(self, session_id: str) -> None: ...
    async def execute_action(
        self, session_id: str, action: str, args: dict[str, Any]
    ) -> dict[str, Any]: ...
    async def collect_evidence(
        self, session_id: str, *, include_accessibility: bool = False
    ) -> dict[str, Any]: ...
    def is_session_active(self, session_id: str) -> bool: ...
    def get_active_sessions(self) -> list[str]: ...
    async def cleanup_all(self) -> None: ...
```

**Implementation notes:**
- Inherits from `BaseExecutionAdapter`
- Uses `MCPManager` for tool calls (stdio to `@playwright/mcp`)
- Manages browser sessions via MCP tools (`browser_new_context`, `browser_close_context`)
- Returns `ExecutionResult` with structured findings
- Env scrubbing for secrets
- URL redaction for sensitive query params
- DOM redaction for secret patterns

### 17.2 NEW: `src/aios/adapters/mock_playwright_mcp_server.py`

**Purpose:** Minimal Playwright MCP mock server for testing without real browser.

**Changes:** Create from scratch.

**Why necessary:** CI tests need deterministic mock; real browser requires `playwright install`.

**Behavior:**
- Implements MCP stdio JSON-RPC protocol
- Exposes Playwright-like tools (`browser_navigate`, `browser_click`, etc.)
- In-memory session store
- Deterministic responses
- Enabled via `HERMES_MOCK_PLAYWRIGHT=1` env flag

### 17.3 MODIFIED: `src/aios/adapters/accessibility_agency_adapter.py`

**Purpose:** Switch from simulated axe-core to real Playwright MCP.

**Changes:**
1. Add optional `playwright_adapter` parameter to constructor
2. Replace `_default_axe_scan` with `_default_playwright_scan`
3. `_default_playwright_scan` calls `PlaywrightMCPAdapter` for real browser execution
4. Fall back to simulated scan if Playwright unavailable (graceful degradation)

**Why necessary:** M8-T2 deliverable — activates real Playwright for accessibility testing.

**Must NOT change:**
- `perspective = "accessibility"` (unchanged)
- Constructor signature pattern (add optional param with default)
- `ExecutionResult` return type (unchanged)

### 17.4 NEW: `src/aios/adapters/playwright_session.py`

**Purpose:** Session registry for Playwright browser contexts with isolation validation.

**Changes:** Create from scratch.

**Why necessary:** Centralizes session lifecycle; prevents cross-session state leakage.

**Interface:**
```python
class PlaywrightSessionRegistry:
    def __init__(self, adapter: PlaywrightMCPAdapter) -> None: ...
    async def create(self, execution_id: str) -> str: ...
    async def close(self, session_id: str) -> None: ...
    def is_active(self, session_id: str) -> bool: ...
    def get_active(self) -> list[str]: ...
    async def cleanup_all(self) -> None: ...
    async def validate_isolation(self, session_id: str) -> None: ...
```

### 17.5 MODIFIED: `src/aios/core/kernel.py`

**Purpose:** Wire Playwright capability and adapter.

**Changes:**
1. Import `PlaywrightMCPAdapter`
2. Add `_init_playwright()` method called after `_init_m7_testing()`
3. Register `playwright_browser` capability in CapabilityManager
4. Create `PlaywrightMCPAdapter` instance (injected into AccessibilityAgencyAdapter)
5. Add config reading for `playwright:` section

**Why necessary:** Kernel-level integration; capability registration.

**Must NOT change:**
- Kernel phase ordering
- LifecycleManager integration
- Existing M7 testing wiring
- Core Manager lifecycle

### 17.6 MODIFIED: `config/defaults.yaml`

**Purpose:** Add Playwright configuration section.

**Changes:** Add:
```yaml
playwright:
  server_id: "playwright_mcp"           # MCP server ID
  timeout_seconds: 30                   # Default timeout
  headless: true                        # Headless by default
  allowed_domains: []                   # Empty = allow all; list specific domains
  context_reuse: false                  # Create new context per session
  capture_network: false                # Optional network capture
  capture_console: false                # Optional console capture
  screenshot_format: "png"              # png | jpeg
  screenshot_full_page: false           # Full page screenshot
```

### 17.7 MODIFIED: `pyproject.toml`

**Purpose:** Add Playwright dependency.

**Changes:**
```toml
[project.optional-dependencies]
browser = [
    "playwright>=1.40",
]
dev = [
    ...existing...
    "playwright>=1.40",  # for browser testing
]
```

**Why necessary:** `playwright` Python package required for browser automation; `@playwright/mcp` Node.js package required for MCP server.

### 17.8 NEW: `tests/unit/test_playwright_mcp_adapter.py`

**Purpose:** Unit tests for PlaywrightMCPAdapter (15 tests).

**Why necessary:** Verify MCP connection, session lifecycle, tool routing, provenance, security.

### 17.9 NEW: `tests/unit/test_playwright_session.py`

**Purpose:** Unit tests for PlaywrightSessionRegistry (5 tests).

**Why necessary:** Verify session isolation, cleanup, idempotent close.

### 17.10 NEW: `tests/integration/test_m8_playwright.py`

**Purpose:** Integration tests for Playwright MCP path (13 tests).

**Why necessary:** End-to-end protocol verification with real/mock Playwright MCP.

### 17.11 MODIFIED: `tests/unit/test_agency_adapters.py`

**Purpose:** Update accessibility adapter test for Playwright integration.

**Changes:**
- Add test for real Playwright path
- Update existing tests for graceful degradation when Playwright unavailable

### 17.12 MODIFIED: `config/mcp/playwright_mcp.json`

**Purpose:** MCP server configuration for Playwright.

**Content:**
```json
{
  "server_id": "playwright_mcp",
  "name": "Playwright MCP",
  "transport": "stdio",
  "command": ["node", "node_modules/@playwright/mcp/index.js"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 60,
  "auto_reconnect": false,
  "max_retries": 1,
  "metadata": {
    "description": "Playwright MCP server for deterministic browser testing"
  }
}
```

---

## 18. Implementation Order

### Step 1: Dependency Setup (5 min)
1. Add `playwright>=1.40` to `pyproject.toml` dev dependencies
2. Verify: `pip install -e ".[dev]"` succeeds

### Step 2: Mock Server (15 min)
3. Create `src/aios/adapters/mock_playwright_mcp_server.py`
4. Implements MCP stdio with Playwright-like tools
5. Supports `HERMES_MOCK_PLAYWRIGHT=1` env flag
6. Verify: Run mock server manually, confirm tool discovery

### Step 3: Session Registry (10 min)
7. Create `src/aios/adapters/playwright_session.py`
8. Session lifecycle with isolation validation
9. Double-close idempotency
10. Stale session cleanup

### Step 4: Playwright MCP Adapter (30 min)
11. Create `src/aios/adapters/playwright_mcp_adapter.py`
12. Inherits `BaseExecutionAdapter`
13. MCP connection via `MCPManager`
14. Session management via `PlaywrightSessionRegistry`
15. Tool routing (navigate, click, type, screenshot, snapshot)
16. Evidence collection (screenshot, DOM, page state)
17. Provenance tracking (extends M8-T1 pattern)
18. Error classification
19. Security: URL redaction, DOM redaction, env scrubbing
20. Allowed domain restriction

### Step 5: Accessibility Adapter Update (10 min)
21. Modify `src/aios/adapters/accessibility_agency_adapter.py`
22. Add `playwright_adapter` optional parameter
23. Replace `_default_axe_scan` with `_default_playwright_scan`
24. Graceful degradation if Playwright unavailable

### Step 6: Kernel Wiring (10 min)
25. Modify `src/aios/core/kernel.py`
26. Import `PlaywrightMCPAdapter`
27. Add `_init_playwright()` method
28. Register `playwright_browser` capability
29. Wire adapter to kernel

### Step 7: Configuration (5 min)
30. Update `config/defaults.yaml` with `playwright:` section
31. Create `config/mcp/playwright_mcp.json`

### Step 8: Unit Tests (20 min)
32. Create `tests/unit/test_playwright_mcp_adapter.py` (15 tests)
33. Create `tests/unit/test_playwright_session.py` (5 tests)

### Step 9: Integration Tests (25 min)
34. Create `tests/integration/test_m8_playwright.py` (13 tests)
35. Update `tests/unit/test_agency_adapters.py` for Playwright path

### Step 10: Regression (10 min)
36. Run full suite: `pytest tests/ -q` → expect 1079 passed
37. Run M7 regression: `pytest tests/integration/test_m7_*.py tests/unit/test_user_simulation_agent.py -v` → all pass
38. Run M8-T1 regression: `pytest tests/unit/test_acp_adapter.py tests/unit/test_hermes_bridge_acp.py tests/integration/test_m8_hermes_acp.py -v` → all pass
39. Verify no forbidden words in adapter: `grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/playwright_mcp_adapter.py` → zero matches

---

## 19. Acceptance Criteria

### A. Integration
- [ ] `PlaywrightMCPAdapter` implements `BaseExecutionAdapter`
- [ ] Adapter connects to Playwright MCP via `MCPManager` (stdio)
- [ ] Tool discovery succeeds (tools/list returns Playwright tools)
- [ ] `AccessibilityAgencyAdapter` uses real Playwright when available
- [ ] Graceful degradation when Playwright unavailable

### B. Browser Execution
- [ ] Navigate to URL works
- [ ] Click element works
- [ ] Type text works
- [ ] Screenshot capture works
- [ ] DOM snapshot capture works
- [ ] All actions are deterministic (explicit waits, no hidden retries)

### C. Session Isolation
- [ ] Each session gets isolated browser context
- [ ] Cookies isolated between sessions
- [ ] localStorage isolated between sessions
- [ ] Authentication state isolated between sessions
- [ ] No cross-session state leakage

### D. Evidence
- [ ] Screenshot produced for every execution
- [ ] DOM snapshot produced
- [ ] Page metadata (URL, title, status) captured
- [ ] Evidence bound to provenance (execution_id, session_id, correlation_id)
- [ ] Provenance complete (all mandatory fields present)

### E. Provenance
- [ ] Every observation has complete provenance
- [ ] Provenance includes Playwright-specific fields (browser type, context ID, page ID)
- [ ] No secrets in provenance (parameters hashed, URLs redacted)
- [ ] Correlation IDs traceable (request → response)

### F. Security
- [ ] No secret leakage in provenance or logs
- [ ] URLs with tokens redacted
- [ ] DOM with secrets redacted
- [ ] Environment variables scrubbed
- [ ] `file://` protocol blocked
- [ ] No subprocess escape via MCP

### G. Failure Handling
- [ ] MCP unavailable → raises `ProtocolUnavailableError`
- [ ] Navigation timeout → observation with error, not crash
- [ ] Selector not found → observation with error, not crash
- [ ] Browser crash → proper error, session cleaned up
- [ ] MCP crash → proper error, reconnect attempted
- [ ] Malformed response → error observation, not exception

### H. Lifecycle
- [ ] Session create → execute → close works end-to-end
- [ ] Cleanup on exception path works
- [ ] `cleanup_all()` removes all sessions
- [ ] No session leaks after tests

### I. Authority Boundaries
- [ ] Adapter never emits verdict/pass/fail
- [ ] Adapter never calls SecurityManager, CouncilManager, StateManager
- [ ] Adapter never writes to disk outside evidence dir
- [ ] No forbidden words in adapter code

### J. Capability Registry
- [ ] `playwright_browser` capability registered
- [ ] Capability discoverable by facade "browser"
- [ ] Security validation passes

### K. Backward Compatibility
- [ ] All 1046 existing tests pass
- [ ] M7 tests pass (18 tests)
- [ ] M8-T1 tests pass (33 tests)
- [ ] `kernel.py` wiring preserves existing behavior
- [ ] No changes to `MCPManager`, `CapabilityManager`, `TestingEvidence`

### L. Real E2E
- [ ] `PLAYWRIGHT_E2E_TEST=1` enables real browser test
- [ ] Real browser test navigates, clicks, types, captures screenshot
- [ ] Evidence captured correctly

---

## 20. Risk Register

| Risk | Likelihood | Impact | Mitigation | Verification |
|------|-----------|--------|------------|-------------|
| Playwright not installed in CI | **High** | Tests fail | Mock server for CI; real browser gated behind `PLAYWRIGHT_E2E_TEST=1` | Unit tests pass without browser |
| Node.js not available | **Medium** | MCP server can't launch | Check Node.js availability at connect time; raise clear error | `test_mcp_connect_process_not_found` passes |
| `@playwright/mcp` version mismatch | **Medium** | Tool names change | Lock version in config; document minimum version | Mock server covers protocol |
| Browser launch slow (>30s) | **Medium** | CI timeout | Configurable timeout; mock server fast | Mock tests complete in <5s |
| Session leak on crash | **Low** | Resource exhaustion | `cleanup_all()` at adapter shutdown; try/finally in tests | `test_no_session_leakage` passes |
| Secret in screenshot | **Low** | Credential leak | Flag in evidence metadata; redact in provenance | `test_no_secret_leakage` passes |
| MCP process persists after test | **Low** | Resource leak | `asyncio.ensure_future` cleanup; pytest fixture cleanup | Process count stable after tests |
| Breaking AccessibilityAgency | **Medium** | Regression | Graceful degradation; adapter optional | `test_agency_adapters` passes with/without Playwright |
| Non-deterministic browser behavior | **Medium** | Flaky tests | Explicit waits; no arbitrary sleeps; deterministic selectors | All tests pass consistently |
| Cross-session contamination | **Low** | Data leakage | Isolated contexts; validated in tests | `test_context_isolation` passes |

---

## 21. Backward Compatibility

### 21.1 Existing Code Unaffected

| Component | Change | Reason |
|-----------|--------|--------|
| `MCPManager` | **UNCHANGED** | Playwright uses existing MCPManager |
| `CapabilityManager` | **UNCHANGED** | New registration only; no API changes |
| `TestingEvidence` | **UNCHANGED** | Same schema; Playwright evidence fits |
| `HermesBridge` | **UNCHANGED** | Separate adapter; no cross-dependency |
| `UserSimulationAgent` | **UNCHANGED** | Uses HermesBridge, not Playwright |
| `AccessibilityAgency` | **MINIMAL** | Optional Playwright path; simulated fallback |
| `kernel.py` | **MINIMAL** | New `_init_playwright()` method; existing wiring preserved |
| `config/defaults.yaml` | **ADDED** | New `playwright:` section; existing `hermes:` preserved |

### 21.2 Graceful Degradation

If Playwright is not available:
1. `PlaywrightMCPAdapter.__init__()` succeeds (no browser required at construction)
2. `connect()` raises `ProtocolUnavailableError`
3. `AccessibilityAgencyAdapter` falls back to simulated `_default_axe_scan`
4. All existing tests pass (Playwright tests gated behind env flag)

### 21.3 Test Baseline

- **Before M8-T2:** 1046 tests passing
- **After M8-T2:** 1079 tests (1046 existing + 33 new)
- **Expected failures:** 0
- **Expected skips:** Tests gated behind `PLAYWRIGHT_E2E_TEST=1` or `HERMES_MOCK_PLAYWRIGHT=1`

---

## 22. Real E2E Requirements

### 22.1 Prerequisites for Real Browser Testing

```bash
# 1. Node.js 18+ installed
node --version  # must be >= 18.0.0

# 2. @playwright/mcp installed
npm install -g @playwright/mcp

# 3. Playwright browsers installed
npx playwright install chromium

# 4. Python playwright package installed
pip install playwright
npx playwright install  # installs Python-compatible browsers
```

### 22.2 E2E Test Gate

```python
# tests/integration/test_m8_playwright.py
@pytest.mark.skipif(
    not os.environ.get("PLAYWRIGHT_E2E_TEST", "").lower() in ("1", "true", "yes"),
    reason="PLAYWRIGHT_E2E_TEST not set"
)
async def test_real_browser_navigation():
    """Real browser E2E: navigate, click, type, screenshot."""
    adapter = PlaywrightMCPAdapter()
    await adapter.connect()
    session_id = await adapter.create_session(str(uuid.uuid4()))
    try:
        result = await adapter.execute_action(session_id, "browser_navigate", {"url": "https://example.com"})
        assert result["status"] == "success"
        # ... more real browser actions
    finally:
        await adapter.close_session(session_id)
        await adapter.disconnect()
```

### 22.3 CI Behavior

- **Standard CI:** All 1079 tests pass (mock-based only)
- **Real browser CI:** Set `PLAYWRIGHT_E2E_TEST=1` in CI config; run E2E tests separately
- **Local development:** Developer installs Playwright manually; E2E tests available

---

## 23. Do-Not-Implement

### 23.1 Explicitly OUT OF SCOPE for M8-T2

| Item | Belongs To |
|------|-----------|
| Graphify MCP connection | M8-T3 (per M8-T1 spec) |
| SkillSpecTor MCP | M8-T4 |
| FreeLLMAPI MCP | M8-T5 |
| Notion/Obsidian MCP | M8-T4 |
| Feature flags for optional integrations | M8-T4 |
| E2E tests with real external services (beyond mock + `PLAYWRIGHT_E2E_TEST`) | M8-T5 |
| Independent QA report | M8-T6 |
| LearningService integration | M9 |
| ModelRouter real integration | M9 |
| Deployment/Docker/health checks | M10 |
| Security hardening (provenance signing, etc.) | M11 |
| Complete documentation closure | M12 |
| Full-system validation | Post-M12 |
| Playwright over network transport (HTTP/SSE/WebSocket) | Future |
| Playwright session persistence/resumption | Future |
| Multi-browser load balancing | M10 |
| Prometheus/OpenTelemetry metrics export | M10 |
| Refactor TestOrchestratorService | Forbidden |
| Refactor CouncilManager/FinalJudgeAgency | Forbidden |
| Refactor SecurityManager | Forbidden |
| Add new managers to kernel | Forbidden |
| Change MCPManager | Forbidden |
| Change workflow.py | Forbidden |
| Import `playwright` at module scope in adapter (defer import) | Forbidden |
| Make mock server speak real Playwright (use separate mock) | Forbidden |
| Increase baseline test failure rate | Forbidden |
| Browser as verifier/judge/council | Forbidden (authority boundary) |
| Browser-initiated kernel state changes | Forbidden |

---

## 24. Terminal 2 Implementation Prompt

```
Execute M8-T2: Playwright MCP Browser Integration

READ THESE FILES FIRST (in order):
1. src/aios/adapters/base.py (BaseExecutionAdapter pattern)
2. src/aios/adapters/accessibility_agency_adapter.py (existing Playwright reference)
3. src/aios/core/mcp_manager.py (MCP infrastructure to reuse)
4. src/aios/adapters/acp_adapter.py (error classification pattern from M8-T1)
5. src/aios/adapters/mock_hermes_server.py (mock server pattern to follow)
6. src/aios/core/kernel.py lines 793-834 (_init_m7_testing context)
7. src/aios/core/capability_manager.py (registration pattern)
8. config/defaults.yaml (current config structure)
9. pyproject.toml (dependency declaration pattern)
10. tests/unit/test_agency_adapters.py (test pattern for adapters)
11. tests/unit/test_acp_adapter.py (M8-T1 test pattern)
12. tests/integration/test_m8_hermes_acp.py (M8-T1 integration pattern)
13. architecture/Part15/M8/M8-T1-IMPLEMENTATION-SPEC.md (M8-T1 patterns to follow)

THEN FOLLOW THIS EXACT SEQUENCE:

STEP 1: Add playwright dependency to pyproject.toml
  - Add "playwright>=1.40" to [project.optional-dependencies.dev]
  - Add [project.optional-dependencies.browser] section with "playwright>=1.40"

STEP 2: Create mock Playwright MCP server
  - Create src/aios/adapters/mock_playwright_mcp_server.py
  - Implement MCP stdio with tools: browser_navigate, browser_click, browser_type_text,
    browser_snapshot, browser_press_key, browser_take_screenshot, browser_new_context,
    browser_close_context, browser_close, get_playwright_version
  - In-memory session store, deterministic responses
  - Enable via HERMES_MOCK_PLAYWRIGHT=1 env flag

STEP 3: Create PlaywrightSessionRegistry
  - Create src/aios/adapters/playwright_session.py
  - Session lifecycle: create, close, validate_isolation, cleanup_all
  - Double-close idempotent
  - Stale session cleanup

STEP 4: Create PlaywrightMCPAdapter
  - Create src/aios/adapters/playwright_mcp_adapter.py
  - Inherit from BaseExecutionAdapter
  - perspective = "playwright_browser"
  - MCP connection via MCPManager (stdio to @playwright/mcp)
  - Session management via PlaywrightSessionRegistry
  - Tool routing: navigate, click, type, screenshot, snapshot, press_key
  - Evidence collection: screenshot (base64 PNG), DOM snapshot, page metadata
  - Provenance tracking (extend M8-T1 pattern with Playwright fields)
  - Security: URL redaction, DOM redaction, env scrubbing, allowed_domains
  - Error classification (PlaywrightError hierarchy)
  - Deferred import of playwright (not module scope)

STEP 5: Update AccessibilityAgencyAdapter
  - Add optional playwright_adapter parameter to __init__
  - Replace _default_axe_scan with _default_playwright_scan
  - _default_playwright_scan uses PlaywrightMCPAdapter when available
  - Graceful degradation to simulated scan when Playwright unavailable

STEP 6: Wire into Kernel
  - Import PlaywrightMCPAdapter in kernel.py
  - Add _init_playwright() method after _init_m7_testing()
  - Register "playwright_browser" capability in CapabilityManager
  - Create PlaywrightMCPAdapter instance
  - Pass adapter to AccessibilityAgencyAdapter

STEP 7: Add Configuration
  - Add playwright: section to config/defaults.yaml
  - Create config/mcp/playwright_mcp.json

STEP 8: Write Unit Tests
  - Create tests/unit/test_playwright_mcp_adapter.py (15 tests)
  - Create tests/unit/test_playwright_session.py (5 tests)

STEP 9: Write Integration Tests
  - Create tests/integration/test_m8_playwright.py (13 tests)
  - Update tests/unit/test_agency_adapters.py for Playwright path

STEP 10: Run Regression
  - pytest tests/ -q → expect 1079 passed, 0 failed
  - pytest tests/integration/test_m7_*.py tests/unit/test_user_simulation_agent.py -v → all pass
  - pytest tests/unit/test_acp_adapter.py tests/unit/test_hermes_bridge_acp.py tests/integration/test_m8_hermes_acp.py -v → all pass
  - grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/playwright_mcp_adapter.py → zero matches

CRITICAL CONSTRAINTS:
- Do NOT change MCPManager
- Do NOT change CapabilityManager API
- Do NOT change TestingEvidence schema
- Do NOT change HermesBridge or UserSimulationAgent
- Do NOT import playwright at module scope (deferred import only)
- Do NOT let Playwright become verifier/judge/council
- All new tests must use real protocol round-trips (mock server, not hardcoded returns)
- Regression must stay at 0 failures
- No new EventType values
- Adapters only; no kernel decision logic changes

ACCEPTANCE:
- 1079 tests passing (1046 existing + 33 new)
- Playwright capability registered
- Browser execution works (mock and real via PLAYWRIGHT_E2E_TEST=1)
- Session isolation verified
- Evidence capture verified
- Provenance complete
- Security verified (no secret leakage)
- Authority boundaries enforced
```

---

## Appendix A: Playwright MCP Tool Reference

The `@playwright/mcp` server exposes these tools (may vary by version):

| Tool | Purpose | Key Arguments |
|------|---------|--------------|
| `browser_navigate` | Navigate to URL | `url`, `waitUntil`, `timeout` |
| `browser_click` | Click element | `selector`, `element` |
| `browser_type_text` | Type text | `selector`, `text`, `element` |
| `browser_press_key` | Press keyboard key | `key`, `element` |
| `browser_snapshot` | Get accessibility snapshot | `element`, `maxDepth` |
| `browser_take_screenshot` | Capture screenshot | `element`, `type`, `ref` |
| `browser_close` | Close browser | — |
| `browser_resize` | Resize viewport | `width`, `height` |
| `browser_wait_for` | Wait for condition | `text`, `time`, `selector` |
| `browser_select_option` | Select dropdown option | `selector`, `value` |
| `browser_hover` | Hover element | `selector`, `element` |
| `get_playwright_version` | Get version | — |

**Note:** Tool names may vary slightly by `@playwright/mcp` version. The adapter should discover available tools via `tools/list` and adapt accordingly.

## Appendix B: Playwright MCP Server Command

```bash
# Standard installation
npm install -g @playwright/mcp

# Run as stdio MCP server
node_modules/.bin/playwright-mcp

# Or via npx
npx @playwright/mcp
```

AI-OS config:
```json
{
  "command": ["node", "node_modules/@playwright/mcp/index.js"]
}
```

The exact path depends on where `@playwright/mcp` is installed. M8-T2 should support configurable path via `playwright.server_path` in config.

## Appendix C: Comparison with M8-T1

| Aspect | M8-T1 (Hermes ACP) | M8-T2 (Playwright MCP) |
|--------|-------------------|----------------------|
| Protocol | ACP preferred, MCP fallback | MCP only |
| Transport | stdio (ACP JSON-RPC) | stdio (MCP JSON-RPC) |
| Purpose | Exploratory user simulation | Deterministic browser testing |
| Session model | ACP session registry | Browser context registry |
| Evidence | Text observations | Screenshot + DOM + metadata |
| Adapter pattern | `HermesBridge` (thin wrapper) | `PlaywrightMCPAdapter` (implements BaseExecutionAdapter) |
| Integration point | `UserSimulationAgent` | `AccessibilityAgencyAdapter` |
| Security | Env scrubbing, provenance hashing | URL redaction, DOM redaction, env scrubbing, provenance hashing |
| Mock server | `mock_hermes_acp_server.py` | `mock_playwright_mcp_server.py` |
| Test count added | 33 | 33 |
| Total after | 1079 | 1112 |

---

*End of M8-T2 Implementation Specification.*

**Final Status: M8-T2 PLANNING COMPLETE — READY FOR IMPLEMENTATION**
