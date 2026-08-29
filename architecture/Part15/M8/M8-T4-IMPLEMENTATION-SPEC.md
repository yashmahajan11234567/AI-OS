# M8-T4 Implementation Specification
## External Knowledge / Planning Integration — Terminal 2 Blueprint

**Date:** 2026-08-25
**Status:** READY FOR IMPLEMENTATION
**Prerequisites:** M7 (complete), M8-T1 (complete, independently verified), M8-T2 (complete, independently verified), M8-T3 (complete, independently verified)
**Terminal 1 Verdict:** M8-T4 PLANNING COMPLETE — READY FOR IMPLEMENTATION

---

## 1. Executive Summary

M8-T4 integrates three external **supporting systems** into AI-OS as contextual, non-authoritative knowledge/planning sources:

| System | Role | Authority | Integration Pattern |
|--------|------|-----------|---------------------|
| **Notion** | Planning / project tracking | Supporting only | MCP server (future) or direct API adapter |
| **Obsidian** | Persistent knowledge vault | Supporting only | Filesystem adapter (existing `MemoryType.OBSIDIAN`) + MCP server (future) |
| **Claude-Mem** | Contextual memory retrieval | Supporting only | MCP server adapter |

These systems are **SUPPORTING SYSTEMS**. They MUST NOT become AI-OS authorities over:
- SecurityManager, StateManager, WorkflowManager, Council, Judge
- Verification, final review, PASS/FAIL decisions
- APPROVE/REJECT decisions, security decisions, governance decisions

All external information returns to AI-OS as **contextual/supporting information**. AI-OS remains authoritative.

This spec follows the established patterns from M8-T1 (Hermes ACP), M8-T2 (Playwright MCP), and M8-T3 (Graphify):
- `BaseExecutionAdapter` pattern from `src/aios/adapters/base.py`
- `MCPManager` from `src/aios/core/mcp_manager.py`
- `CapabilityManager` registration from kernel `_init_*` methods
- Error classification hierarchy per adapter
- Provenance tracking with source/advisor/advisory marking
- Security validation (sensitive key rejection, size limits)
- Graceful degradation on failure

---

## 2. Current Repository State

### 2.1 Existing Memory Infrastructure

| Component | Path | Status | Notes |
|-----------|------|--------|-------|
| `MemoryType` enum | `src/aios/core/memory.py:34-41` | **EXISTS** | Has `WORKING`, `CLAUDE`, `ENGINEERING`, `OBSIDIAN`, `GRAPHIFY` |
| `MemoryManager` | `src/aios/core/memory.py:552-795` | **EXISTS** | File-based backends for all types; GraphifyBackend wired via MCP |
| `MemoryService` | `src/aios/services/memory.py` | **EXISTS** | Event-driven facade; auto-routes `LearningCaptured→ENGINEERING`, `CheckpointCreated→WORKING` |
| `FileMemoryBackend` | `src/aios/core/memory.py:92-201` | **EXISTS** | Default backend for all non-Graphify types |
| `MemoryType.OBSIDIAN` | `src/aios/core/memory.py:40` | **EXISTS** | Enum member defined but **NOT wired** — no ObsidianBackend, no MCP config |
| `MemoryType.CLAUDE` | `src/aios/core/memory.py:38` | **EXISTS** | Enum member defined but **NOT wired** — no ClaudeMemBackend, no MCP config |

### 2.2 Existing Integration Infrastructure

| Component | Path | Status |
|-----------|------|--------|
| `BaseExecutionAdapter` | `src/aios/adapters/base.py` | **EXISTS** — sync pattern with injected test tool |
| `MCPManager` | `src/aios/core/mcp_manager.py` | **EXISTS** — stdio/HTTP/SSE/WebSocket transports |
| `CapabilityManager` | `src/aios/core/capability_manager.py` | **EXISTS** — phase-4 Core Manager |
| Kernel init methods | `src/aios/core/kernel.py:857-936` | **EXISTS** — `_init_graphify()`, `_init_playwright()` |
| MCP configs | `config/mcp/*.json` (7 files) | **EXISTS** — graphify, hermes_agent_ext, agent_reach, test variants |
| `config/defaults.yaml` | `config/defaults.yaml` | **EXISTS** — has `hermes`, `playwright`, `graphify` sections |

### 2.3 Existing Notion/Obsidian/Claude-Mem References

| System | Code References | Doc References | Tests | Config | Status |
|--------|----------------|----------------|-------|--------|--------|
| **Notion** | None in `src/` | `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md:670,1824` | None | None | **ABSENT (C4)** |
| **Obsidian** | `MemoryType.OBSIDIAN` (enum), docstring in `memory.py:8,40,560` | `14.5-External-System-Integration.md §7`, `15.12` §592 | None | None | **STUBBED** (enum member, no backend) |
| **Claude-Mem** | `MemoryType.CLAUDE` (enum), docstring in `memory.py:6` | `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md:734,1834` | None | None | **ABSENT** (no implementation beyond enum) |

### 2.4 Architecture References

- **Part 14.5 §7 (Obsidian Vault Integration):** Documents Obsidian as EXTERNAL system category, integration via MemoryManager (M1). GAP-OBS-01 (mechanism UNSPECIFIED), GAP-OBS-02 (data format UNSPECIFIED).
- **Part 14.5 §1.1:** Lists Obsidian Vault as one of seven external system categories, integrated via MemoryManager (Core Manager direct bridge).
- **Master Plan:** Notion listed as "REFERENCE / Future API/MCP / ABSENT (C4)"; Obsidian as "REFERENCE / Future MCP / NOT WIRED"; Claude-Mem as "REFERENCE/DEV TOOL / NOT INTEGRATED".

---

## 3. Existing Integration Inventory

### 3.1 Full Classification Table

| System | Existing Component | Production Path | Missing | Tests | Status |
|--------|-------------------|-----------------|---------|-------|--------|
| **Notion** | None | None | Full adapter, MCP config, capability, tests | None | **NOT PRESENT (E)** |
| **Obsidian** | `MemoryType.OBSIDIAN` enum | `FileMemoryBackend` → local filesystem | `ObsidianVaultBackend` (vault-aware), MCP config, capability, tests | None | **STUBBED (C)** |
| **Claude-Mem** | `MemoryType.CLAUDE` enum | `FileMemoryBackend` → local filesystem | `ClaudeMemBackend` (remote), MCP config, capability, tests | None | **STUBBED (C)** |

> **Classification rationale:**
> - **Notion**: Zero code references. Only in documentation as a future reference. Classified as NOT PRESENT.
> - **Obsidian**: `MemoryType.OBSIDIAN` enum exists; `FileMemoryBackend` handles it via generic file storage. No vault-aware semantics (no `.obsidian/` folder awareness, no frontmatter handling, no wikilink resolution). Classified as STUBBED.
> - **Claude-Mem**: `MemoryType.CLAUDE` enum exists; same generic file backend. No connection to claude-mem MCP/server. Classified as STUBBED.

### 3.2 What the Existing `MemoryType.OBSIDIAN` Actually Does

With the current implementation, `MemoryType.OBSIDIAN` entries are stored as JSON files under `{data_dir}/obsidian/`. They have NO:
- Vault path awareness (no concept of an Obsidian vault)
- Frontmatter handling
- Wikilink or tag resolution
- Markdown rendering or parsing
- Any integration with an actual Obsidian application

This is a **placeholder stub**, not an integration.

### 3.3 Existing MCP Configuration Pattern

```json
// config/mcp/graphify_mcp.json
{
  "server_id": "graphify",
  "name": "Graphify",
  "transport": "stdio",
  "command": ["python", "-m", "aios.adapters.mock_graphify_server"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 30,
  "auto_reconnect": true,
  "max_retries": 3,
  "metadata": { "description": "Graphify knowledge graph MCP server (mock for testing)" }
}
```

This is the pattern to follow for all three new integrations.

---

## 4. Architecture

### 4.1 Target Conceptual Architecture

```
AI-OS Kernel
  │
  ├── NotionAdapter (BaseExecutionAdapter)
  │     └── MCP Manager → Notion MCP Server (or direct API)
  │           └── notion.so API
  │                 └── Planning / Project Tracking
  │
  ├── ObsidianAdapter (BaseExecutionAdapter) + ObsidianVaultBackend (MemoryBackend)
  │     ├── MCP path: MCP Manager → Obsidian MCP Server → Vault
  │     └── Direct path: FilesystemAdapter → Local Vault Directory
  │           └── Persistent Knowledge / Documentation
  │
  └── ClaudeMemAdapter (BaseExecutionAdapter)
        └── MCP Manager → Claude-Mem MCP Server
              └── Contextual Memory / Retrieval
```

### 4.2 Layer Responsibility Matrix

| Layer | Responsibility |
|-------|---------------|
| **AI-OS Kernel** | Authority, decision-making, orchestration |
| **CapabilityManager** | Registration, discovery, invocation routing |
| **Adapter Layer** | Protocol translation, security validation, error classification |
| **MCP Manager** | Transport (stdio/HTTP/SSE), tool discovery, timeout handling |
| **External System** | Data storage, retrieval, business logic |

### 4.3 Data Flow Diagrams

#### Notion Data Flow

```
AI-OS Planning Request
  ↓
NotionAdapter.execute(target, context)
  ↓
Security validation (sensitive content check)
  ↓
MCPManager.call_tool("notion", "search_pages", {...})
  ↓
Notion MCP Server
  ↓
Notion API (reading/writing pages, databases)
  ↓
Structured results → ExecutionResult
  ↓
AI-OS (planning context, advisory only)
```

#### Obsidian Data Flow

```
AI-OS Knowledge Request
  ↓
ObsidianAdapter.execute(target, context)
  ↓
Security validation
  ↓
Path A: MCPManager.call_tool("obsidian", "search_notes", {...})
       → Obsidian MCP Server → Vault filesystem
Path B: FilesystemAdapter.read(vault_path, target)
       → Local vault directory → markdown parsing
  ↓
Parsed notes with frontmatter extraction
  ↓
ExecutionResult (marked advisory)
  ↓
AI-OS (knowledge context, advisory only)
```

#### Claude-Mem Data Flow

```
AI-OS Context Request
  ↓
ClaudeMemAdapter.execute(target, context)
  ↓
Security validation
  ↓
MCPManager.call_tool("claude_mem", "retrieve_context", {...})
  ↓
Claude-Mem Server
  ↓
Memory store retrieval (contextual, not authoritative)
  ↓
Retrieved context → ExecutionResult
  ↓
AI-OS (contextual memory, advisory only)
```

### 4.4 Capability Registration

Following the M8-T3 pattern in `kernel._init_graphify()`:

```python
# Notion
self._capability_manager.register(
    capability_id="notion_planning",
    facade="planning",
    provider_id="notion",
    provider_metadata={"server_id": "notion", "transport": "stdio", ...},
    security_context={"requires_validation": True, ...},
    tags=("planning", "notion", "project-tracking", "tasks"),
)

# Obsidian
self._capability_manager.register(
    capability_id="obsidian_knowledge",
    facade="knowledge",
    provider_id="obsidian",
    provider_metadata={"server_id": "obsidian", ...},
    security_context={"requires_validation": True, ...},
    tags=("knowledge", "obsidian", "documentation", "persistent"),
)

# Claude-Mem
self._capability_manager.register(
    capability_id="claude_mem_context",
    facade="memory",
    provider_id="claude_mem",
    provider_metadata={"server_id": "claude_mem", ...},
    security_context={"requires_validation": True, ...},
    tags=("memory", "claude-mem", "contextual", "retrieval"),
)
```

---

## 5. Notion Responsibility / Boundary

### 5.1 What Notion MAY Do

- Read/write **project plans, milestones, tasks, and planning metadata**
- Synchronize task status between AI-OS and Notion databases
- Provide planning context for workflow decisions
- Store and retrieve project documentation
- Push checkpoint summaries to Notion pages

### 5.2 What Notion MAY NOT Do

- Make or influence any **PASS/FAIL decision**
- Influence **SecurityManager** authorization decisions
- Override **Council** or **Judge** verdicts
- Control **WorkflowManager** execution flow
- Determine **APPROVE/REJECT** outcomes
- Store or access **security credentials** or **secrets**
- Become the **system of record** for AI-OS state

### 5.3 Notion Trust Model

Notion is classified as **UNTRUSTED CONTEXTUAL DATA**. All data retrieved from Notion:
- Is marked with `provenance.authority = "contextual"`
- Cannot override AI-OS internal state
- Must pass security validation before being used in prompts
- Is subject to size limits and content sanitization

---

## 6. Obsidian Responsibility / Boundary

### 6.1 What Obsidian MAY Do

- Store and retrieve **persistent technical knowledge**
- Provide **architecture notes, design notes, research findings**
- Serve as a **documentation repository**
- Enable cross-reference lookups via wikilinks
- Support markdown-based knowledge organization

### 6.2 What Obsidian MAY NOT Do

- Be the **authoritative source** for AI-OS operational state
- Influence **security decisions** or **verification outcomes**
- Override **governance** or **compliance** determinations
- Store **runtime execution state**
- Replace AI-OS's internal **StateManager** or **StorageManager**

### 6.3 Obsidian Trust Model

Obsidian is classified as **TRUSTED CONTEXTUAL KNOWLEDGE** (higher trust than Notion because it's local/file-based, but still advisory for decision-making). Data from Obsidian:
- Is marked with `provenance.authority = "contextual"`
- Cannot override AI-OS internal decisions
- Is subject to size limits and prompt-injection screening
- Must preserve frontmatter structure

---

## 7. Claude-Mem Responsibility / Boundary

### 7.1 What Claude-Mem MAY Do

- Provide **contextual memory retrieval** for reasoning support
- Return **prior interaction context** when relevant
- Support **historical pattern matching** for planning
- Enhance LLM prompts with relevant prior context

### 7.2 What Claude-Mem MAY NOT Do

- Be the **source of authoritative truth**
- Override **SecurityManager** decisions
- Influence **verification** or **governance** outcomes
- Store **credentials** or **secrets**
- Become **persistent state** for AI-OS (that's `MemoryType.WORKING/ENGINEERING`)

### 7.3 Claude-Mem Trust Model

Claude-Mem is classified as **UNTRUSTED CONTEXTUAL MEMORY**. Data retrieved from Claude-Mem:
- Is marked with `provenance.authority = "contextual"`
- Is treated as hints, not facts
- Cannot override AI-OS internal state
- Must be screened for prompt injection

---

## 8. Data Flows

### 8.1 Unified Flow Pattern

All three systems follow this unified pattern:

```
1. AI-OS component requests data via capability invocation
2. CapabilityManager routes to appropriate adapter
3. Adapter performs security validation on input
4. Adapter calls external system (MCP tool or direct API)
5. External system returns raw data
6. Adapter applies provenance metadata
7. Adapter marks results as advisory/contextual
8. Adapter returns ExecutionResult to AI-OS
9. AI-OS uses results as contextual input only
```

### 8.2 Provenance Field Requirements

Every response from external knowledge systems MUST include:

```python
{
    "source": "notion" | "obsidian" | "claude_mem",
    "adapter": "<adapter_name>",
    "operation": "<operation_name>",
    "correlation_id": "<uuid>",
    "execution_id": "<uuid or None>",
    "task_id": "<string or None>",
    "timestamp": "<ISO 8601>",
    "request_id": "<uuid>",
    "authority": "contextual",       # Never "authoritative"
    "advisory": True,
    "trust_level": "untrusted",      # Follows HermesBridge pattern
}
```

### 8.3 Provenance Reuse

The existing `_make_provenance()` pattern from `GraphifyAdapter` (lines 314-332) should be reused. Each adapter implements its own version with the same field structure but different `source` and `adapter` values.

---

## 9. Adapter Architecture

### 9.1 NotionAdapter

**Pattern:** Follows `BaseExecutionAdapter` exactly like `GraphifyAdapter`.

```python
class NotionAdapter(BaseExecutionAdapter):
    perspective = "notion_planning"

    def __init__(self, mcp_manager=None, server_id="notion", timeout_seconds=30):
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._connected = False

    # Methods:
    #   connect() / disconnect() / is_connected()
    #   search_pages(query, parent=None) → list[Page]
    #   get_page(page_id) → Page
    #   create_page(title, parent_id, content) → Page
    #   update_page(page_id, content) → bool
    #   query_database(db_id, filter=None) → list[Page]
    #   _call_tool(tool_name, args, operation) → dict
    #   _make_provenance(operation, ...) → dict
    #   _validate_content(content) → None  # size + sensitive check
```

**Error hierarchy:** `NotionError` → `NotionUnavailableError`, `NotionTimeoutError`, `NotionValidationError`, `NotionSecurityError`

**Operations exposed:** `search`, `get`, `create`, `update`, `query_db`

### 9.2 ObsidianAdapter

**Pattern:** Dual-path — MCP when available, filesystem fallback.

```python
class ObsidianAdapter(BaseExecutionAdapter):
    perspective = "obsidian_knowledge"

    def __init__(self, mcp_manager=None, server_id="obsidian",
                 vault_path=None, timeout_seconds=30):
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._vault_path = vault_path  # Direct filesystem path
        self._timeout_seconds = timeout_seconds
        self._connected = False  # MCP path

    # Methods:
    #   connect() / disconnect() / is_connected()
    #   search_notes(query) → list[Note]
    #   get_note(path) → Note
    #   list_notes(directory=".") → list[str]
    #   _call_tool(tool_name, args, operation) → dict  # MCP path
    #   _read_local(path) → str  # filesystem path
    #   _parse_frontmatter(content) → tuple[dict, str]
    #   _make_provenance(operation, ...) → dict
    #   _validate_content(content) → None
```

**Note model:**
```python
@dataclass
class Note:
    path: str
    title: str
    content: str      # Body without frontmatter
    frontmatter: dict  # Extracted YAML frontmatter
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    provenance: dict
```

**Error hierarchy:** `ObsidianError` → `ObsidianUnavailableError`, `ObsidianTimeoutError`, `ObsidianValidationError`, `ObsidianSecurityError`, `ObsidianVaultNotFoundError`

### 9.3 ClaudeMemAdapter

**Pattern:** MCP-only (same as GraphifyAdapter — requires MCP connection).

```python
class ClaudeMemAdapter(BaseExecutionAdapter):
    perspective = "claude_mem_context"

    def __init__(self, mcp_manager=None, server_id="claude_mem", timeout_seconds=30):
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._connected = False

    # Methods:
    #   connect() / disconnect() / is_connected()
    #   retrieve_context(query, limit=10) → list[MemoryEntry]
    #   retrieve_recent(hours=24, limit=20) → list[MemoryEntry]
    #   retrieve_by_tag(tag) → list[MemoryEntry]
    #   _call_tool(tool_name, args, operation) → dict
    #   _make_provenance(operation, ...) → dict
    #   _validate_query(query) → None  # size + injection check
```

**Error hierarchy:** `ClaudeMemError` → `ClaudeMemUnavailableError`, `ClaudeMemTimeoutError`, `ClaudeMemValidationError`, `ClaudeMemSecurityError`

### 9.4 Shared Components

All adapters share these patterns from existing code:
- **`_validate_properties` / `_validate_content`**: Reject sensitive keys (`password`, `token`, `secret`, `api_key`, etc.) and oversized content
- **`_make_provenance`**: Same structure as GraphifyAdapter (lines 314-332)
- **Advisory marking**: `source="<adapter>"`, `advisory=True`, `authority="contextual"` (not "advisory_only" — that's Graphify-specific for inferred edges)
- **Mock server**: Each adapter needs a corresponding mock MCP server for testing

---

## 10. Capability Registration

### 10.1 Proposed Capability IDs

| Capability ID | Facade | Provider ID | Tags |
|--------------|--------|-------------|------|
| `notion_planning` | `planning` | `notion` | planning, notion, project-tracking, tasks |
| `obsidian_knowledge` | `knowledge` | `obsidian` | knowledge, obsidian, documentation, persistent |
| `claude_mem_context` | `memory` | `claude_mem` | memory, claude-mem, contextual, retrieval |

### 10.2 Security Context Per Capability

```python
# Common security context structure
security_context = {
    "requires_validation": True,
    "allowed_operations": [...],  # Per adapter
    "sensitive_keys": [...],      # Per adapter
    "max_content_size": 10240,    # 10 KB default
}
```

### 10.3 Kernel Wiring

In `src/aios/core/kernel.py`, add three init methods following the M8-T3 pattern:

```python
async def _init_notion(self) -> None:
    """Register M8-T4 Notion planning capability and adapter."""
    if not self._capability_manager:
        logger.debug("CapabilityManager not available; skipping Notion init")
        return
    adapter = NotionAdapter(
        mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
        server_id="notion",
    )
    self._notion_adapter = adapter
    self._capability_manager.register(
        capability_id="notion_planning",
        facade="planning",
        provider_id="notion",
        provider_metadata={"server_id": "notion", "transport": "stdio", ...},
        security_context={...},
        tags=("planning", "notion", "project-tracking", "tasks"),
    )

async def _init_obsidian(self) -> None:
    """Register M8-T4 Obsidian knowledge capability and adapter."""
    if not self._capability_manager:
        logger.debug("CapabilityManager not available; skipping Obsidian init")
        return
    adapter = ObsidianAdapter(
        mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
        server_id="obsidian",
        vault_path=self._config.get("obsidian.vault_path"),
    )
    self._obsidian_adapter = adapter
    self._capability_manager.register(...)

async def _init_claude_mem(self) -> None:
    """Register M8-T4 Claude-Mem context capability and adapter."""
    if not self._capability_manager:
        logger.debug("CapabilityManager not available; skipping Claude-Mem init")
        return
    adapter = ClaudeMemAdapter(
        mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
        server_id="claude_mem",
    )
    self._claude_mem_adapter = adapter
    self._capability_manager.register(...)
```

Call these from `__init__` after `_init_graphify()` and `_init_playwright()`.

---

## 11. Provenance

### 11.1 Required Fields

| Field | Type | Required | Source |
|-------|------|----------|--------|
| `source` | string | YES | `"notion"`, `"obsidian"`, `"claude_mem"` |
| `adapter` | string | YES | Adapter class name |
| `operation` | string | YES | Operation name |
| `correlation_id` | UUID | YES | Generated per request |
| `execution_id` | UUID \| None | YES | From caller context |
| `task_id` | string \| None | YES | From caller context |
| `timestamp` | ISO 8601 | YES | `datetime.utcnow()` |
| `request_id` | UUID | YES | Generated per request |
| `authority` | string | YES | `"contextual"` (never `"authoritative"`) |
| `advisory` | bool | YES | `True` |
| `trust_level` | string | YES | `"untrusted"` |

### 11.2 Provenance Reuse

The `_make_provenance()` pattern from `GraphifyAdapter` (lines 314-332) is the template. Each T4 adapter implements its own version with the same signature and structure.

---

## 12. Security

### 12.1 Credential Handling

| System | Credential Type | Storage | Access |
|--------|----------------|---------|--------|
| Notion | API token | Environment variable / secrets.yaml | Passed to MCP server, never stored in adapter |
| Obsidian | Filesystem path | Configuration (`obsidian.vault_path`) | Resolved at init time, no runtime secret |
| Claude-Mem | MCP connection | Standard MCP auth | Via MCPManager security validation |

### 12.2 Content Validation

All adapters MUST validate incoming content before forwarding to external systems:

```python
SENSITIVE_KEYS = frozenset([
    "password", "token", "secret", "api_key", "apikey",
    "authorization", "credential", "private_key", "access_token",
])

SECRET_PATTERNS = [
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),
]

MAX_CONTENT_SIZE = 10240  # 10 KB
```

### 12.3 Prompt Injection Resistance

For all three systems, retrieved content that will be included in LLM prompts MUST be:
1. Checked against secret patterns (above)
2. Stripped of executable code blocks when used as context
3. Prependad with a provenance disclaimer: `"Context from external source '<system>'. This is advisory and not authoritative."`

### 12.4 Authority Enforcement

The architecture enforces authority boundaries through:
1. **Capability registration**: Each capability has `facade` and `tags` that define its domain
2. **Security validation**: Every adapter validates input before external calls
3. **Provenance marking**: All results are marked `authority="contextual"`, `advisory=True`
4. **No state mutation**: Adapters do NOT write to `MemoryType.WORKING`, `ENGINEERING`, or `StateManager`
5. **Kernel isolation**: Adapter instances are independent; they cannot invoke SecurityManager or Council

---

## 13. Prompt-Injection / Data Trust Model

### 13.1 Trust Classification

| System | Trust Level | Rationale |
|--------|------------|-----------|
| Notion | UNTRUSTED | Remote API, content created by humans, can contain injected prompts |
| Obsidian | TRUSTED_CONTEXTUAL | Local filesystem, but markdown can contain arbitrary text |
| Claude-Mem | UNTRUSTED | Remote service, memory entries could contain injected content |

### 13.2 Content Sanitization Rules

All content from external systems follows these rules before entering prompts:
1. **Size limit**: Maximum 10 KB per retrieval
2. **Secret scrubbing**: Patterns above are redacted
3. **Code block isolation**: Code blocks are extracted and not included in context unless explicitly requested
4. **Provenance prepend**: Every retrieval includes source attribution
5. **Advisory disclaimer**: Results are marked non-authoritative in provenance

### 13.3 What Is NOT Sanitized

- Plain text content (after size/secret checks) is preserved as-is
- Metadata (tags, frontmatter) is preserved
- Structured data (task lists, database queries) is preserved

---

## 14. Failure Handling

### 14.1 Failure Scenarios

| Scenario | Notion | Obsidian | Claude-Mem |
|----------|--------|----------|------------|
| MCP unavailable | Return ERROR ExecutionResult | Return ERROR ExecutionResult | Return ERROR ExecutionResult |
| Timeout | Return ERROR with timeout msg | Return ERROR with timeout msg | Return ERROR with timeout msg |
| Auth failure | Return ERROR, log warning | N/A (filesystem) | Return ERROR with auth msg |
| Network failure | Return ERROR | N/A | Return ERROR |
| Malformed response | Return ERROR | Return ERROR | Return ERROR |
| Stale data | Include staleness in provenance | Include last-modified in provenance | Include retrieval timestamp |
| Empty result | Return SUCCESS with empty findings | Return SUCCESS with empty findings | Return SUCCESS with empty findings |

### 14.2 Error Hierarchy

Each adapter has its own error hierarchy following the M8-T3 pattern:

```python
class NotionError(Exception): pass
class NotionUnavailableError(NotionError): pass
class NotionTimeoutError(NotionError): pass
class NotionValidationError(NotionError): pass
class NotionSecurityError(NotionError): pass

class ObsidianError(Exception): pass
class ObsidianUnavailableError(ObsidianError): pass
class ObsidianTimeoutError(ObsidianError): pass
class ObsidianValidationError(ObsidianError): pass
class ObsidianSecurityError(ObsidianError): pass
class ObsidianVaultNotFoundError(ObsidianError): pass

class ClaudeMemError(Exception): pass
class ClaudeMemUnavailableError(ClaudeMemError): pass
class ClaudeMemTimeoutError(ClaudeMemError): pass
class ClaudeMemValidationError(ClaudeMemError): pass
class ClaudeMemSecurityError(ClaudeMemError): pass
```

### 14.3 Failure Philosophy

Per Part 14 context.md §13: **Integration failures MUST NOT propagate as exceptions to the caller.**

All adapter methods catch their specific errors and return `ExecutionResult` with `status=ExecutionStatus.ERROR` and appropriate `findings`. The caller (AI-OS) decides how to handle the error — the adapter never raises out of its public API.

---

## 15. Graceful Degradation

### 15.1 Degradation Strategy

| System | Primary Path | Fallback | Degradation Behavior |
|--------|-------------|----------|---------------------|
| Notion | MCP server | None | Return ERROR result; AI-OS continues without planning context |
| Obsidian | MCP server | Filesystem (local vault) | Falls back to local vault read; warns if MCP unavailable |
| Claude-Mem | MCP server | None | Return ERROR result; AI-OS continues without contextual memory |

### 15.2 Obsidian Dual-Path

Obsidian is the only system with a built-in fallback:
1. If MCP server is connected → use MCP path
2. If MCP unavailable but `vault_path` is configured → use filesystem path
3. If neither → return ERROR ExecutionResult

This ensures Obsidian knowledge is available even when the MCP server is down, as long as the vault is accessible locally.

### 15.3 No Silent Failures

Every failure path MUST:
- Log a warning at the adapter level
- Return a structured `ExecutionResult` with error details
- Include the error in provenance for auditability
- Never silently return empty results (always distinguish "not found" from "failed")

---

## 16. Configuration

### 16.1 New MCP Configs

```json
// config/mcp/notion_mcp.json
{
  "server_id": "notion",
  "name": "Notion",
  "transport": "stdio",
  "command": ["python", "-m", "aios.adapters.mock_notion_server"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 30,
  "auto_reconnect": true,
  "max_retries": 3,
  "metadata": { "description": "Notion planning MCP server (mock for testing)" }
}

// config/mcp/obsidian_mcp.json
{
  "server_id": "obsidian",
  "name": "Obsidian",
  "transport": "stdio",
  "command": ["python", "-m", "aios.adapters.mock_obsidian_server"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 30,
  "auto_reconnect": true,
  "max_retries": 3,
  "metadata": { "description": "Obsidian knowledge MCP server (mock for testing)" }
}

// config/mcp/claude_mem_mcp.json
{
  "server_id": "claude_mem",
  "name": "Claude-Mem",
  "transport": "stdio",
  "command": ["python", "-m", "aios.adapters.mock_claude_mem_server"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 30,
  "auto_reconnect": true,
  "max_retries": 3,
  "metadata": { "description": "Claude-Mem context MCP server (mock for testing)" }
}
```

### 16.2 New defaults.yaml Section

```yaml
# M8-T4: External Knowledge Integration
notion:
  server_id: "notion"
  timeout_seconds: 30
  auto_reconnect: true
  max_search_results: 50
  max_page_content_size: 10240

obsidian:
  server_id: "obsidian"
  vault_path: ""               # Empty = use MCP; set for filesystem fallback
  timeout_seconds: 30
  auto_reconnect: true
  max_note_size: 10240
  search_limit: 50

claude_mem:
  server_id: "claude_mem"
  timeout_seconds: 30
  auto_reconnect: true
  max_retrieval_limit: 20
  max_query_size: 1024
```

---

## 17. File-Level Change Plan

### 17.1 NEW Files

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `src/aios/adapters/notion_adapter.py` | Notion MCP adapter | ~350 |
| `src/aios/adapters/obsidian_adapter.py` | Obsidian dual-path adapter | ~400 |
| `src/aios/adapters/claude_mem_adapter.py` | Claude-Mem MCP adapter | ~300 |
| `src/aios/adapters/mock_notion_server.py` | Mock Notion MCP server | ~200 |
| `src/aios/adapters/mock_obsidian_server.py` | Mock Obsidian MCP server | ~200 |
| `src/aios/adapters/mock_claude_mem_server.py` | Mock Claude-Mem MCP server | ~150 |
| `config/mcp/notion_mcp.json` | Notion MCP config | ~15 |
| `config/mcp/obsidian_mcp.json` | Obsidian MCP config | ~15 |
| `config/mcp/claude_mem_mcp.json` | Claude-Mem MCP config | ~15 |
| `tests/unit/test_notion_adapter.py` | Notion adapter unit tests | ~200 |
| `tests/unit/test_obsidian_adapter.py` | Obsidian adapter unit tests | ~250 |
| `tests/unit/test_claude_mem_adapter.py` | Claude-Mem adapter unit tests | ~200 |
| `tests/integration/test_m8_notion.py` | Notion integration tests | ~150 |
| `tests/integration/test_m8_obsidian.py` | Obsidian integration tests | ~150 |
| `tests/integration/test_m8_claude_mem.py` | Claude-Mem integration tests | ~150 |

**Total NEW files: 15**

### 17.2 MODIFIED Files

| File | Changes |
|------|---------|
| `config/defaults.yaml` | Add `notion:`, `obsidian:`, `claude_mem:` sections |
| `src/aios/core/kernel.py` | Add `_init_notion()`, `_init_obsidian()`, `_init_claude_mem()` methods + calls in `__init__` |
| `tests/unit/test_agency_adapters.py` | Add adapter instantiation tests (minimal) |

**Total MODIFIED files: 3**

### 17.3 NOT Modified

- `src/aios/core/memory.py` — No changes to `MemoryType` enum or existing backends
- `src/aios/services/memory.py` — No changes to MemoryService
- `src/aios/adapters/base.py` — No changes to BaseExecutionAdapter
- `src/aios/core/mcp_manager.py` — No changes to MCPManager
- `src/aios/core/capability_manager.py` — No changes to CapabilityManager

---

## 18. Test Plan

### 18.1 Test Categories

| Category | Count | Coverage |
|----------|-------|----------|
| Unit tests (adapter construction) | 9 | Each adapter: connected/disconnected, config validation |
| Unit tests (security validation) | 12 | Sensitive key rejection, size limits, secret patterns |
| Unit tests (error handling) | 15 | Timeout, unavailable, malformed response, auth failure |
| Unit tests (provenance) | 9 | Field presence, advisory marking, authority level |
| Unit tests (Obsidian dual-path) | 8 | MCP path, filesystem fallback, vault not found |
| Integration tests (MCP round-trip) | 9 | Mock server → adapter → result verification |
| Integration tests (capability registration) | 3 | Kernel wiring, capability discoverability |
| **Total** | **64** | |

### 18.2 Expected Test Count by File

| Test File | Count |
|-----------|-------|
| `tests/unit/test_notion_adapter.py` | ~18 |
| `tests/unit/test_obsidian_adapter.py` | ~24 |
| `tests/unit/test_claude_mem_adapter.py` | ~18 |
| `tests/integration/test_m8_notion.py` | ~9 |
| `tests/integration/test_m8_obsidian.py` | ~9 |
| `tests/integration/test_m8_claude_mem.py` | ~9 |
| `tests/unit/test_agency_adapters.py` (additions) | ~7 |
| **Total** | **~94** |

> Note: This is a **planning** estimate. The actual count will be finalized during implementation. The 94 test count is conservative and follows the M8-T3 pattern (27 tests for Graphify alone).

### 18.3 Key Test Scenarios

**NotionAdapter:**
- Connects to mock server successfully
- Searches pages, returns structured results
- Rejects sensitive content (password in page content)
- Returns ERROR on timeout
- Provenance includes all required fields
- Advisory marking is present
- Disconnection cleanup works

**ObsidianAdapter:**
- MCP path: connects and searches notes
- Filesystem fallback: reads vault when MCP unavailable
- Rejects oversized notes
- Handles missing vault gracefully
- Parses frontmatter correctly
- Provenance includes vault path

**ClaudeMemAdapter:**
- Connects to mock server
- Retrieves contextual memory
- Limits result count
- Rejects oversized queries
- Returns empty (not error) when no results
- Provenance marks as contextual

---

## 19. Acceptance Criteria

### A. Integration

- [ ] All three adapters importable without errors
- [ ] All three MCP configs valid JSON with correct schema
- [ ] All three mock servers start and respond to tool calls
- [ ] Kernel initialization calls all three `_init_*` methods
- [ ] All three capabilities registered in CapabilityManager

### B. Adapter Functionality

- [ ] NotionAdapter: search, get, create, update, query_db operations work
- [ ] ObsidianAdapter: MCP path works; filesystem fallback works
- [ ] ClaudeMemAdapter: retrieve_context, retrieve_recent, retrieve_by_tag work
- [ ] All adapters return `ExecutionResult` (never raise unhandled exceptions)

### C. Authority Boundaries

- [ ] No adapter writes to `MemoryType.WORKING` or `MemoryType.ENGINEERING`
- [ ] No adapter invokes SecurityManager, Council, or Judge
- [ ] No adapter modifies kernel state (StateManager, StorageManager)
- [ ] All results marked `authority="contextual"`, `advisory=True`

### D. Provenance

- [ ] Every result includes all 11 required provenance fields
- [ ] Provenance includes `source`, `adapter`, `operation`
- [ ] Provenance includes `authority="contextual"` and `advisory=True`
- [ ] Provenance is present in both success and error results

### E. Security

- [ ] Sensitive keys rejected before external call
- [ ] Oversized content rejected (10 KB limit)
- [ ] Secret patterns detected and rejected
- [ ] No credentials stored in adapter state

### F. Failure Handling

- [ ] MCP unavailable → ERROR ExecutionResult (not exception)
- [ ] Timeout → ERROR ExecutionResult with timeout message
- [ ] Auth failure → ERROR ExecutionResult with auth message
- [ ] Malformed response → ERROR ExecutionResult
- [ ] Empty result → SUCCESS with empty findings (not error)

### G. Graceful Degradation

- [ ] Obsidian falls back to filesystem when MCP unavailable
- [ ] All failures logged at WARNING level
- [ ] AI-OS continues operating when external system unavailable

### H. Capability Registry

- [ ] `notion_planning` capability discoverable by facade "planning"
- [ ] `obsidian_knowledge` capability discoverable by facade "knowledge"
- [ ] `claude_mem_context` capability discoverable by facade "memory"
- [ ] All capabilities have correct tags

### I. Backward Compatibility

- [ ] No changes to existing adapters (Graphify, Playwright, Hermes)
- [ ] No changes to MemoryType enum members
- [ ] No changes to existing tests
- [ ] Existing 1046+ test baseline unaffected

---

## 20. Authority-Boundary Requirements

### 20.1 Hard Boundaries (MUST NOT Cross)

| Boundary | Constraint | Enforcement |
|----------|-----------|-------------|
| Decision authority | Adapters cannot make PASS/FAIL, APPROVE/REJECT decisions | Test: no Council/Judge invocation |
| Security authority | Adapters cannot call SecurityManager.authorize() | Test: no SecurityManager import in adapters |
| State authority | Adapters cannot write to StateManager | Test: no StateManager reference |
| Governance authority | Adapters cannot influence WorkflowManager | Test: no WorkflowManager reference |
| Verification authority | Adapters cannot set verification results | Test: no TestingEvidence write |

### 20.2 Soft Boundaries (SHOULD Respect)

| Boundary | Constraint |
|----------|-----------|
| Memory isolation | Adapters read external systems, don't write to AI-OS memory stores |
| Event domain | Adapters emit events via EventBus but don't consume governance events |
| Provenance chain | All external data carries provenance showing its non-authoritative origin |

### 20.3 Code Enforcement

The following patterns are FORBIDDEN in all three adapters:
```python
# FORBIDDEN
from aios.core.security_manager import SecurityManager
from aios.core.state_manager import StateManager
from aios.core.workflow_manager import WorkflowManager
# Any call to Council, Judge, or TestingService
```

The following patterns are REQUIRED:
```python
# REQUIRED
self._make_provenance(operation, ...)  # Always include provenance
result = ExecutionResult(
    tool="<adapter>",
    status=ExecutionStatus.SUCCESS/ERROR,
    findings=[],
    metrics={...},
    raw=<sanitized>,
)
# Provenance must include authority="contextual", advisory=True
```

---

## 21. Backward Compatibility

### 21.1 Existing Code Unaffected

- No modifications to `src/aios/core/memory.py`
- No modifications to `src/aios/services/memory.py`
- No modifications to `src/aios/adapters/base.py`
- No modifications to `src/aios/core/mcp_manager.py`
- No modifications to `src/aios/core/capability_manager.py`
- No modifications to existing adapter files

### 21.2 Test Baseline Preservation

The existing test baseline of **1046+ passing tests** must remain intact. New tests are additive only.

### 21.3 Configuration Compatibility

New config sections (`notion`, `obsidian`, `claude_mem`) are additive to `config/defaults.yaml`. Existing sections (`hermes`, `playwright`, `graphify`) are unchanged.

### 21.4 Kernel API Compatibility

New `_init_*` methods follow the exact same signature pattern as existing `_init_graphify()` and `_init_playwright()`. No changes to `Kernel.__init__()` or `Kernel.start()` signatures.

---

## 22. Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Notion API rate limiting | MEDIUM | MCP server handles rate limiting; adapter receives errors gracefully |
| Obsidian vault path misconfiguration | LOW | Validation at init time; clear error message if vault not found |
| Claude-Mem server instability | MEDIUM | Circuit-breaker pattern via MCPManager auto-reconnect; adapter returns ERROR |
| Prompt injection via retrieved content | HIGH | Content validation (size + secret patterns) + provenance disclaimer in prompts |
| Credential leakage in logs | HIGH | No credentials in adapter state; sanitized logging |
| Mock server incompatibility | LOW | Follow existing mock server patterns exactly |
| Capability ID collision | LOW | Use domain-prefixed IDs (`notion_planning`, `obsidian_knowledge`, `claude_mem_context`) |

---

## 23. Do-Not-Implement

### 23.1 Explicitly OUT OF SCOPE for M8-T4

- **LearningService** — belongs to M8-T5 capability hardening
- **RCA (Root Cause Analysis)** — belongs to M8-T5
- **Model router** — belongs to M8-T5
- **Convergence detection** — belongs to M8-T6
- **Adaptive replanning** — belongs to M8-T6
- **Real Notion API client** — use mock server for M8-T4; real API in M8-T5+
- **Real Obsidian plugin** — use mock MCP server; real integration in M8-T5+
- **Real Claude-Mem server** — use mock MCP server; real integration in M8-T5+
- **Cross-system synchronization** — NOT planned (each system is independent)
- **Unified search across all three** — NOT planned (separate adapters, separate calls)
- **M8-T5 through M8-T7 work** — separate milestones

### 23.2 Forbidden Patterns

```python
# FORBIDDEN: Direct API calls without MCP wrapper
import requests  # Don't use in adapters

# FORBIDDEN: Writing to AI-OS state stores
self._state_manager.set(...)  # Never

# FORBIDDEN: Making authority decisions
return "PASS" if condition else "FAIL"  # Never

# FORBIDDEN: Silent failures
try:
    result = await self._call_tool(...)
except:
    pass  # Must return ERROR ExecutionResult
```

---

## 24. Implementation Order

### Step 1: Configuration (5 min)
- Add `notion`, `obsidian`, `claude_mem` sections to `config/defaults.yaml`
- Create `config/mcp/notion_mcp.json`, `obsidian_mcp.json`, `claude_mem_mcp.json`

### Step 2: Mock Servers (15 min)
- Create `mock_notion_server.py` (4 tools: search, get, create, query_db)
- Create `mock_obsidian_server.py` (4 tools: search, get, list, read)
- Create `mock_claude_mem_server.py` (3 tools: retrieve, recent, by_tag)

### Step 3: Adapters (45 min)
- Create `notion_adapter.py` (~350 lines)
- Create `obsidian_adapter.py` (~400 lines)
- Create `claude_mem_adapter.py` (~300 lines)

### Step 4: Kernel Wiring (10 min)
- Add `_init_notion()`, `_init_obsidian()`, `_init_claude_mem()` to kernel.py
- Call them in `__init__` after `_init_playwright()`

### Step 5: Unit Tests (30 min)
- Create `test_notion_adapter.py` (~18 tests)
- Create `test_obsidian_adapter.py` (~24 tests)
- Create `test_claude_mem_adapter.py` (~18 tests)

### Step 6: Integration Tests (20 min)
- Create `test_m8_notion.py` (~9 tests)
- Create `test_m8_obsidian.py` (~9 tests)
- Create `test_m8_claude_mem.py` (~9 tests)

### Step 7: Regression (10 min)
- Run full test suite to confirm 1046+ baseline preserved
- Verify new tests pass

**Total estimated implementation time: ~135 minutes**

---

## 25. Terminal 2 Implementation Instructions

When implementing M8-T4, follow these instructions precisely:

### 25.1 Start With
1. Read `src/aios/adapters/graphify_adapter.py` — this is the template for all three adapters
2. Read `src/aios/adapters/mock_graphify_server.py` — this is the template for all three mock servers
3. Read `src/aios/core/kernel.py` lines 857-936 — this is the template for kernel wiring

### 25.2 Implementation Rules
1. **Follow the GraphifyAdapter pattern exactly** — same error hierarchy, same provenance structure, same security validation
2. **Use mock servers for all tests** — do not integrate real APIs in M8-T4
3. **Mark all results as advisory** — never mark as authoritative
4. **Return ExecutionResult on all paths** — never raise unhandled exceptions
5. **Add to config/defaults.yaml** — use the exact structure shown in §16.2
6. **Create MCP configs** — use the exact JSON structure from §16.1

### 25.3 Implementation Order
1. Mock servers first (so adapters have something to test against)
2. Adapters second (using mock servers for unit tests)
3. Kernel wiring third
4. Integration tests fourth
5. Regression test fifth

### 25.4 What to Skip
- Do NOT implement real Notion API client
- Do NOT implement real Obsidian vault scanner
- Do NOT implement real Claude-Mem client
- Do NOT modify `src/aios/core/memory.py`
- Do NOT modify `src/aios/services/memory.py`
- Do NOT add new `MemoryType` enum members

---

## 26. Terminal 3 Verification Requirements

When verifying M8-T4, check the following:

### 26.1 Structural Verification
- [ ] All 15 new files exist at expected paths
- [ ] All 3 modified files have expected changes
- [ ] No unexpected files were modified
- [ ] No existing test files were modified

### 26.2 Functional Verification
- [ ] `python -m pytest tests/unit/test_notion_adapter.py -v` passes
- [ ] `python -m pytest tests/unit/test_obsidian_adapter.py -v` passes
- [ ] `python -m pytest tests/unit/test_claude_mem_adapter.py -v` passes
- [ ] `python -m pytest tests/integration/test_m8_notion.py -v` passes
- [ ] `python -m pytest tests/integration/test_m8_obsidian.py -v` passes
- [ ] `python -m pytest tests/integration/test_m8_claude_mem.py -v` passes

### 26.3 Regression Verification
- [ ] `python -m pytest --tb=short -q` reports no new failures
- [ ] Existing 1046+ test baseline is preserved
- [ ] No existing tests were modified

### 26.4 Security Verification
- [ ] No adapter imports SecurityManager, StateManager, or WorkflowManager
- [ ] All results include provenance with `authority="contextual"`
- [ ] Sensitive content is rejected before external calls
- [ ] No credentials appear in logs or test output

### 26.5 Authority Verification
- [ ] Adapters do not write to any AI-OS state store
- [ ] Adapters do not invoke Council, Judge, or TestingService
- [ ] All external data is marked advisory in provenance

---

## 27. Final Planning Verdict

**M8-T4 PLANNING COMPLETE — READY FOR IMPLEMENTATION**

### Summary of Findings

| System | Code Status | Test Status | Config Status | Integration Pattern |
|--------|------------|-------------|---------------|-------------------|
| **Notion** | NOT PRESENT | None | None | MCP adapter (new) |
| **Obsidian** | STUBBED (enum only) | None | None | MCP adapter + filesystem fallback (new) |
| **Claude-Mem** | STUBBED (enum only) | None | None | MCP adapter (new) |

### Key Design Decisions

1. **Three new adapters** following the GraphifyAdapter pattern exactly
2. **Three mock MCP servers** for deterministic testing
3. **Three new MCP configs** following the graphify_mcp.json pattern
4. **Three new kernel init methods** following the `_init_graphify()` pattern
5. **No changes to existing memory infrastructure** — the `MemoryType.OBSIDIAN`/`CLAUDE` stubs are left as-is; T4 provides the adapter layer on top
6. **Advisory-only results** — all external data marked `authority="contextual"`, `advisory=True`
7. **64-94 new tests** following the M8-T3 test distribution pattern
8. **Zero modifications to existing production code** (except kernel wiring)

### Risk Assessment

- **Low risk**: Pattern is well-established (copy GraphifyAdapter × 3)
- **Low risk**: All integrations use mock servers (no real API dependencies)
- **Medium risk**: Prompt injection via retrieved content — mitigated by content validation
- **Low risk**: Backward compatibility — no changes to existing code paths

### Recommendation

Proceed with implementation. The pattern is proven, the scope is well-bounded, and the authority boundaries are clearly defined.
