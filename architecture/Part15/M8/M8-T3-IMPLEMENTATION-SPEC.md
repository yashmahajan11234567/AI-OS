# M8-T3 Implementation Specification
## Graphify Relationship / Knowledge Graph Integration — Terminal 2 Blueprint

**Date:** 2026-08-25
**Status:** READY FOR IMPLEMENTATION
**Prerequisites:** M7 (complete), M8-T1 (complete, independently verified), M8-T2 (complete, independently verified)
**Terminal 1 Verdict:** M8-T3 PLANNING COMPLETE — READY FOR IMPLEMENTATION

---

## 1. Executive Summary

M8-T3 integrates **Graphify** as AI-OS's relationship and knowledge graph layer. Graphify stores and retrieves structural relationships between AI-OS entities (tasks, executions, capabilities, evidence, agents) for contextual enrichment.

**What Graphify IS:**
- A derived/indexed relationship graph
- A context retrieval source
- An advisory evidence layer (per C14: "advisory only")
- An MCP-connected external system (same category as Hermes, Playwright)

**What Graphify MUST NOT BE:**
- Decision authority
- Verification authority
- Security authority
- Council / Judge / final reviewer
- Workflow authority
- Approval / rejection authority

**Target conceptual architecture:**

```
AI-OS
  ↓
GraphifyAdapter
  ↓
Graph / Knowledge Layer
  ├── Nodes (entities)
  ├── Relationships (edges)
  ├── Dependencies
  ├── Tasks
  ├── Capabilities
  ├── Executions
  ├── Evidence
  ├── Results
  └── Execution History
  ↓
AI-OS Context (read-only enrichment)
```

Graphify is **additive**. It enriches context; it does not change authority flow.

---

## 2. Current Architecture

### 2.1 Existing Graphify Infrastructure (Already Present)

| Component | Path | Status | Notes |
|-----------|------|--------|-------|
| `GraphifyBackend` | `src/aios/core/memory.py:265-549` | **EXISTS** | MemoryBackend implementation using MCP; stores/retrieves nodes as memory entries; all results marked advisory per C14 |
| `mock_graphify_server.py` | `src/aios/adapters/mock_graphify_server.py` | **EXISTS** | MCP stdio server with 7 tools: `add_node`, `get_node`, `update_node`, `delete_node`, `query_graph`, `shortest_path`, `add_edge` |
| `graphify_mcp.json` | `config/mcp/graphify_mcp.json` | **EXISTS** | MCP config for mock server |
| `graphify-test.json` | `config/mcp/graphify-test.json` | **EXISTS** | Test variant config |
| `graphify-tools.json` | `config/mcp/graphify-tools.json` | **EXISTS** | Tools variant config |
| `MemoryType.GRAPHIFY` | `src/aios/core/memory.py` | **EXISTS** | Enum member for graphify memory type |
| `ArchitectureAgencyAdapter` | `src/aios/adapters/architecture_agency_adapter.py` | **PARTIAL** | References "Graphify MCP" in docstring but uses `_default_graphify_scan` which is a text-scanner, NOT actual graph traversal |
| `SecurityManager._AUTHORIZED_HOSTS` | `src/aios/core/security_manager.py:579` | **EXISTS** | "graphify.local" in authorized hosts list |
| Memory tests | `tests/unit/test_m5_gate.py:509-590` | **EXISTS** | Tests GraphifyBackend connectivity and C14 advisory marking |
| Config tests | `tests/unit/test_m5_gate.py:867-877` | **EXISTS** | Tests graphify_mcp.json exists and is valid |
| Mock server test | `tests/unit/test_m5_gate.py:896-898` | **EXISTS** | Tests mock_graphify_server.py exists |

### 2.2 What Already Works

1. **GraphifyBackend** connects to MCP server, stores nodes, retrieves nodes, queries graph, finds shortest paths
2. **C14 advisory marking** is implemented — all Graphify-sourced data is explicitly marked `source=graphify_inferred`, `advisory=True`, `authority=advisory_only`
3. **Mock server** runs deterministically with in-memory store
4. **MemoryManager** auto-wires GraphifyBackend when MCPManager is available

### 2.3 What Is Missing for M8-T3

| Gap | Severity | Description |
|-----|----------|-------------|
| No `GraphifyAdapter` class | HIGH | No adapter implementing `BaseExecutionAdapter` pattern (like HermesBridge, PlaywrightMCPAdapter) |
| No capability registration | HIGH | Graphify not registered in CapabilityManager |
| No kernel wiring | HIGH | No `_init_graphify()` method in kernel.py |
| No graph-specific error classification | MEDIUM | GraphifyBackend swallows all exceptions silently |
| No relationship-specific operations | MEDIUM | GraphifyBackend stores nodes but doesn't expose relationship-driven queries for AI-OS entities |
| No provenance model for graph ops | MEDIUM | GraphifyBackend operations lack execution_id, correlation_id provenance |
| No context enrichment API | MEDIUM | No method to retrieve related entities, execution history, dependency chains |
| `_default_graphify_scan` is a text scanner | LOW | ArchitectureAgencyAdapter claims "Graphify MCP" but uses regex on code text |

---

## 3. Repository Findings

### 3.1 Inventory

| Category | Status | Details |
|----------|--------|---------|
| 1. Graphify MCP mock server | **EXISTS** | `mock_graphify_server.py` — 7 tools, in-memory store, stdio protocol |
| 2. Graphify MCP configs | **EXISTS** | 3 configs: `graphify_mcp.json`, `graphify-test.json`, `graphify-tools.json` |
| 3. GraphifyBackend (memory) | **EXISTS** | `memory.py:265-549` — node CRUD + query + shortest_path |
| 4. C14 advisory marking | **EXISTS** | `_mark_advisory()` adds provenance headers |
| 5. MemoryType.GRAPHIFY | **EXISTS** | Enum member |
| 6. Graphify integration tests | **EXISTS** | `test_m5_gate.py` — 6 tests covering backend, events, provenance, config |
| 7. GraphifyAdapter (execution) | **MISSING** | No `BaseExecutionAdapter` implementation |
| 8. Graphify capability registration | **MISSING** | Not registered in CapabilityManager |
| 9. Kernel wiring | **MISSING** | No `_init_graphify()` in kernel.py |
| 10. Graphify config section | **MISSING** | No `graphify:` section in `config/defaults.yaml` |
| 11. Relationship query methods | **PARTIAL** | `query_graph()` exists but returns raw dict, not typed results |
| 12. Provenance per operation | **MISSING** | No execution_id/correlation_id on graph operations |
| 13. Error classification | **PARTIAL** | All exceptions become generic warnings |
| 14. Context enrichment API | **MISSING** | No method to get related tasks, executions, evidence |

### 3.2 Key Finding: Graphify Is Already Integrated (Partially)

Graphify is **not a greenfield integration**. It was started in M5 (memory system) and has:
- A working MCP connection path
- A mock server
- Config files
- Test coverage for basic operations
- C14 advisory compliance

**What M8-T3 adds:** The **adapter layer** that makes Graphify a first-class AI-OS relationship/context service, following the same patterns as M8-T1 (HermesBridge) and M8-T2 (PlaywrightMCPAdapter).

### 3.3 Key Finding: ArchitectureAgencyAdapter Uses Text Scanning, Not Graph Traversal

`ArchitectureAgencyAdapter` in `src/aios/adapters/architecture_agency_adapter.py` is documented as "knowledge-graph traversal via Graphify MCP" but its `_default_graphify_scan()` function is a **regex-based text scanner** — it scans Python source code for import patterns and method counts. It does NOT call Graphify MCP.

**M8-T3 must fix this** by either:
- (a) Connecting ArchitectureAgencyAdapter to the real GraphifyAdapter, OR
- (b) Leaving the text scanner as-is and adding a separate GraphifyAdapter for relationship queries

**Recommendation:** Keep the text scanner as a fallback (graceful degradation) and add a new `_graphify_scan()` path that actually queries the graph. This follows the established pattern from M8-T2 (playwright adapter with graceful degradation).

---

## 4. Existing Graph Infrastructure Classification

| Component | Status | File/Class |
|-----------|--------|------------|
| Graph abstraction (MCP tools) | **EXISTS** | `mock_graphify_server.py` — add_node, get_node, update_node, delete_node, query_graph, shortest_path, add_edge |
| Graph store (in-memory) | **EXISTS** | `MockGraphifyServer._nodes`, `_edges` |
| Relationship model | **PARTIAL** | `_edges` list in mock; no typed relationship class |
| Dependency model | **MISSING** | No explicit dependency representation (only implicit via node properties) |
| Knowledge model | **PARTIAL** | `GraphifyBackend` stores MemoryEntry as nodes; no typed knowledge classes |
| Entity model | **MISSING** | No entity type registry (task, execution, capability, etc.) |
| Context retrieval | **PARTIAL** | `query_graph()` and `shortest_path()` exist but return untyped dicts |
| Execution history | **MISSING** | No execution_history tracking in graph |
| Evidence relationships | **MISSING** | No edge-based evidence-to-task linking |
| Capability relationships | **MISSING** | No capability-to-execution linking |

**Conclusion:** The foundational pieces exist (MCP connection, mock server, basic CRUD). M8-T3 fills the gaps: adapter pattern, capability registration, provenance, relationship queries, and context enrichment.

---

## 5. Graphify Investigation

### 5.1 What Graphify Actually Is

Graphify in the current project is:

1. **An MCP server** (`mock_graphify_server.py`) implementing 7 tools over stdio JSON-RPC 2.0
2. **A MemoryBackend** (`GraphifyBackend` in `memory.py`) that wraps the MCP server for the memory system
3. **A configuration entry** (`config/mcp/graphify_mcp.json`) connecting via MCPManager
4. **An authorized host** in SecurityManager (`graphify.local`)
5. **A memory type** (`MemoryType.GRAPHIFY`) in the multi-backend memory system

### 5.2 MCP Interface (from mock_graphify_server.py)

Tools exposed:

| Tool | Purpose | Arguments | Returns |
|------|---------|-----------|---------|
| `add_node` | Create graph node | `node_id`, `label`, `properties` (optional) | `{node_id, created}` |
| `get_node` | Retrieve node | `node_id` | `{id, label, properties}` |
| `update_node` | Update node properties | `node_id`, `properties` | `{node_id, updated}` |
| `delete_node` | Remove node + connected edges | `node_id` | `{node_id, deleted}` |
| `query_graph` | Query all nodes/edges | `query` (string) | `{nodes, edges}` |
| `shortest_path` | BFS between nodes | `from_node`, `to_node`, `max_depth` | `{path, found}` |
| `add_edge` | Create relationship | `from_node`, `to_node`, `relationship`, `properties` (optional) | `{edge, created}` |

### 5.3 Storage Model (Mock Server)

```python
_nodes: dict[str, dict]  # node_id → {id, label, properties}
_edges: list[dict]       # [{from_node, to_node, relationship, properties}]
```

### 5.4 What Is NOT Yet Implemented

1. **Typed node schemas** — all nodes are arbitrary dicts
2. **Namespace isolation** — no concept of AI-OS vs external namespaces
3. **Version tracking** — no version field on nodes/edges
4. **TTL / expiration** — no time-based node eviction
5. **Relationship direction enforcement** — bidirectional edges allowed
6. **Cyclic dependency detection** — not enforced
7. **Size limits** — no property size constraints
8. **Security validation on writes** — no allowlist/denylist on node labels or edge types

---

## 6. Gap Analysis

### 6.1 Complete Gaps

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| GraphifyAdapter (BaseExecutionAdapter) | **MISSING** | No adapter class exists |
| Capability registration | **MISSING** | Zero capabilities registered for graphify |
| Kernel wiring (_init_graphify) | **MISSING** | No initialization method |
| Graph context enrichment API | **MISSING** | No typed query methods for AI-OS entities |
| Per-operation provenance | **MISSING** | GraphifyBackend operations lack execution_id/correlation_id |
| Graph-specific error classification | **PARTIAL** | Only generic exceptions, no typed errors |
| Configuration section | **MISSING** | No `graphify:` in defaults.yaml |
| Relationship model for AI-OS entities | **MISSING** | No entity-specific relationship types |
| Context retrieval with provenance | **MISSING** | Raw query results, no structured enrichment |

### 6.2 Partial Gaps

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| Graph CRUD operations | **EXISTS** | `GraphifyBackend` has store/retrieve/update/delete |
| Graph query | **PARTIAL** | `query_graph()` returns raw dict, not typed |
| Shortest path | **EXISTS** | `shortest_path()` works but untyped |
| C14 advisory marking | **EXISTS** | `_mark_advisory()` present |
| Mock server | **EXISTS** | Full mock with 7 tools |
| MCP config | **EXISTS** | 3 config files |
| Basic tests | **EXISTS** | 6 tests in test_m5_gate.py |

---

## 7. Target Architecture

### 7.1 Architecture Diagram

```
AI-OS Kernel
  │
  ├─ CapabilityManager
  │    └─ register("graphify_context", "graph", "graphify")
  │
  ├─ MCPManager
  │    └─ connect("graphify") → stdio subprocess
  │         └─ mock_graphify_server (or real Graphify)
  │
  ├─ GraphifyAdapter (NEW — implements BaseExecutionAdapter)
  │    ├─ __init__(mcp_manager=None, server_id="graphify")
  │    ├─ _default_tool(target, context) → ExecutionResult
  │    ├─ execute(target, context) → ExecutionResult
  │    ├─ store_node(entity_id, label, properties) → bool
  │    ├─ get_node(entity_id) → dict | None
  │    ├─ update_node(entity_id, properties) → bool
  │    ├─ delete_node(entity_id) → bool
  │    ├─ add_edge(from_id, to_id, relationship, properties) → bool
  │    ├─ get_related_entities(entity_id, relationship_type, limit) → list[dict]
  │    ├─ get_execution_history(execution_id, limit) → list[dict]
  │    ├─ get_dependency_chain(entity_id, max_depth) → list[dict]
  │    └─ _mark_advisory(metadata) → dict  # C14 compliance
  │
  └─ ArchitectureAgency (existing)
       └─ _get_adapter() → GraphifyAdapter()  [ENHANCED]
            ├─ Real path: graph traversal via GraphifyAdapter
            └─ Fallback: regex text scan (existing behavior)
```

### 7.2 Data Flow

```
TestOrchestratorService / Agency.review(request)
  ↓
ArchitectureAgencyAdapter.execute(target, context)
  ↓
GraphifyAdapter._default_tool(target, context)
  ↓
GraphifyAdapter.get_related_entities(target, ...)  # graph query
GraphifyAdapter.get_execution_history(target, ...)  # execution history
GraphifyAdapter.get_dependency_chain(target, ...)   # dependency analysis
  ↓
ExecutionResult (structured observation, NOT verdict)
  ↓
ArchitectureAgency._evidence_to_response()
  ↓
AgencyResponse (observations only)
  ↓
TestOrchestratorService.normalize_evidence()
  ↓
TestingEvidence (verdict computed by AI-OS, not Graphify)
```

### 7.3 Layer Responsibility Matrix

| Layer | Responsibility | Authority |
|-------|---------------|-----------|
| Graphify MCP | Store/retrieve graph data | Data storage ONLY |
| GraphifyAdapter | Translate AI-OS requests to graph queries | Adaptation ONLY |
| MCPManager | Transport layer (stdio JSON-RPC) | Transport ONLY |
| ArchitectureAgency | Orchestrate architecture scan | Observation gathering ONLY |
| TestOrchestratorService | Normalize evidence, coordinate perspectives | Orchestration ONLY |
| TestingCouncil | Synthesize evidence, produce verdict | Decision authority |
| FinalJudgeAgency | Final judgment | Final authority |

### 7.4 How Graphify Differs from Hermes and Playwright

| Aspect | Hermes (M8-T1) | Playwright (M8-T2) | Graphify (M8-T3) |
|--------|---------------|-------------------|-----------------|
| Protocol | ACP preferred, MCP fallback | MCP only | MCP only |
| Transport | stdio | stdio | stdio |
| Purpose | User simulation | Browser execution | Relationship/context storage & retrieval |
| Session model | ACP session registry | Browser context registry | No session model (stateless queries) |
| Evidence | Text observations | Screenshot + DOM | Graph structure + relationships |
| Adapter pattern | `HermesBridge` (thin wrapper) | `PlaywrightMCPAdapter` (implements BaseExecutionAdapter) | `GraphifyAdapter` (implements BaseExecutionAdapter) |
| Integration point | `UserSimulationAgent` | `AccessibilityAgencyAdapter` | `ArchitectureAgencyAdapter` + context enrichment |
| Authority | Observation only | Observation only | Context enrichment only (C14 advisory) |

---

## 8. Graph Data Model

### 8.1 Node Types

Graphify stores nodes representing AI-OS entities. Each node has:

```python
{
    "id": str,              # entity identifier (see §8.4)
    "label": str,           # entity type: "task" | "execution" | "capability" | "agent" | "agency" | "evidence" | "artifact" | "project" | "milestone"
    "properties": dict,     # entity-specific metadata
    "created_at": str,      # ISO 8601 UTC timestamp
    "updated_at": str,      # ISO 8601 UTC timestamp
    "provenance": dict,     # {source, adapter, operation, correlation_id, version}
}
```

### 8.2 Edge Types

```python
{
    "from": str,            # source node ID
    "to": str,              # target node ID
    "relationship": str,    # edge type (see §8.3)
    "properties": dict,     # edge metadata (weight, confidence, timestamp)
    "created_at": str,      # ISO 8601 UTC timestamp
    "provenance": dict,     # {source, adapter, operation, correlation_id}
}
```

### 8.3 Relationship Types

| Relationship | From → To | Meaning |
|-------------|-----------|---------|
| `DEPENDS_ON` | task → task | Task dependency |
| `EXECUTES` | agent → task | Agent executed this task |
| `PRODUCES` | execution → evidence | Execution produced this evidence |
| `RELATES_TO` | task → task | General relationship |
| `CAPABILITY_OF` | capability → agent | Capability owned by agent |
| `PART_OF` | task → project | Task belongs to project |
| `TRACES_TO` | evidence → artifact | Evidence supports artifact |
| `FOLLOWS` | execution → execution | Sequential execution (history) |
| `IMPLEMENTS` | capability → task | Capability satisfies task requirement |

### 8.4 Entity Identifiers

| Entity | Node ID Format | Source |
|--------|---------------|--------|
| task | `task:{task_id}` | AI-OS authoritative |
| execution | `exec:{execution_id}` | AI-OS authoritative |
| capability | `cap:{capability_id}` | CapabilityManager authoritative |
| agent | `agent:{agent_id}` | AI-OS agent registry |
| agency | `agency:{agency_name}` | AI-OS agency registry |
| evidence | `ev:{evidence_id}` | TestingEvidence ID |
| artifact | `artifact:{artifact_id}` | AI-OS artifact registry |
| project | `proj:{project_id}` | AI-OS project registry |
| milestone | `milestone:{milestone_id}` | AI-OS milestone registry |

### 8.5 Properties Schema by Node Type

**Task node:**
```python
{
    "task_id": str,
    "title": str,
    "description": str,
    "status": str,           # "pending" | "active" | "completed" | "failed"
    "priority": int,
    "assigned_to": str,      # agent_id
    "created_at": str,
    "updated_at": str,
}
```

**Execution node:**
```python
{
    "execution_id": str,
    "task_id": str,
    "agent_id": str,
    "agency_id": str,
    "status": str,           # "success" | "failure" | "error" | "timeout"
    "started_at": str,
    "finished_at": str,
    "duration_ms": int,
    "result_summary": str,
}
```

**Capability node:**
```python
{
    "capability_id": str,
    "facade": str,
    "provider_id": str,
    "version": str,
    "tags": list[str],
    "state": str,            # "REGISTERED" | "DEPRECATED" | "REMOVED"
}
```

**Evidence node:**
```python
{
    "evidence_id": str,
    "perspective": str,
    "target": str,
    "test_id": str,
    "severity": str,
    "verdict": str,          # "pass" | "fail" | "inconclusive"
    "confidence": float,
    "provenance": dict,
}
```

**Agent node:**
```python
{
    "agent_id": str,
    "name": str,
    "role": str,             # "architecture" | "security" | "performance" | etc.
    "capabilities": list[str],
}
```

### 8.6 Namespace Isolation

All Graphify operations use the namespace `"ai_os"` to isolate from other systems that might share the same Graphify backend:

```python
# All node IDs are prefixed with namespace
"ai_os:task:abc123"
"ai_os:exec:def456"
"ai_os:cap:ghi789"
```

This prevents cross-system contamination if Graphify is shared.

---

## 9. Source-of-Truth Matrix

This is a critical boundary. Every entity is classified as AI-OS authoritative or Graphify derived/indexed.

| Entity | AI-OS Authoritative | Graphify Derived/Index | Rationale |
|--------|--------------------|----------------------|-----------|
| Task definition | **YES** | No | TaskManager owns task state |
| Task dependencies | No | **YES (derived)** | Graphify stores for traversal; AI-OS may create edges |
| Execution result | **YES** | No | TestOrchestratorService owns execution outcomes |
| Execution history | No | **YES (derived)** | Graphify indexes for context; not authoritative |
| Capability registration | **YES** | No | CapabilityManager owns registry |
| Capability relationships | No | **YES (derived)** | Graphify stores for discovery |
| Evidence | **YES** | No | TestingEvidence is the canonical record |
| Evidence relationships | No | **YES (derived)** | Graphify connects evidence to tasks |
| Security decision | **YES** | No | SecurityManager owns security state |
| Council verdict | **YES** | No | CouncilManager owns synthesis |
| Graph structure | No | **YES (owned)** | Graphify owns its own graph |
| Graph context | No | **YES (derived)** | Retrieved from Graphify, advisory per C14 |
| Node properties | No | **YES (derived)** | Mirror of AI-OS state, may lag |
| Relationship edges | No | **YES (derived)** | Mirrors AI-OS relationships |

**Critical invariant:** Graphify data is always treated as **contextual enrichment**, never as the source of truth. When Graphify data conflicts with AI-OS authoritative state, AI-OS wins.

---

## 10. Synchronization

### 10.1 Direction: AI-OS → Graphify (Write)

Graph mutations are **event-driven**, not periodic sync:

```
AI-OS event (TASK_COMPLETED, EXECUTION_FINISHED, etc.)
  ↓
GraphifyAdapter.on_aios_event(event)
  ↓
Update graph nodes/edges
  ↓
Log operation with provenance
```

**Operations:**

| Trigger | Graph Operation |
|---------|----------------|
| Task created | `store_node("task:{id}", "task", {...})` |
| Task updated | `update_node("task:{id}", {"status": ...})` |
| Task deleted | `delete_node("task:{id}")` |
| Execution started | `store_node("exec:{id}", "execution", {...})` |
| Execution completed | `update_node("exec:{id}", {"status": "success", ...})` |
| Capability registered | `store_node("cap:{id}", "capability", {...})` |
| Evidence produced | `store_node("ev:{id}", "evidence", {...})` |
| Dependency declared | `add_edge("task:{from}", "task:{to}", "DEPENDS_ON")` |

### 10.2 Direction: Graphify → AI-OS (Read)

Reads are **on-demand**, not push-based:

```
AI-OS component requests context
  ↓
GraphifyAdapter.get_related_entities(entity_id, ...)
  ↓
MCP call → Graphify
  ↓
Return structured context (marked advisory per C14)
```

### 10.3 Consistency Model

- **Eventual consistency**: Graph may lag behind AI-OS state by one event cycle
- **No conflict resolution**: AI-OS authoritative state always wins; Graphify updates are re-applied
- **Idempotent writes**: Same input → same graph state (checked via node existence)
- **Stale data handling**: If Graphify is unavailable, context is empty (not error)

### 10.4 Duplicate Prevention

- **Node upsert**: `store_node` checks existence; if exists, `update_node` instead
- **Edge deduplication**: `add_edge` checks if edge already exists before creating
- **Version tracking**: Each node has `updated_at`; concurrent writes use last-write-wins

---

## 11. Provenance

Every graph operation carries provenance metadata:

```python
{
    "source": "ai_os",                           # who initiated the operation
    "adapter": "graphify_adapter",               # which adapter
    "operation": "store_node" | "get_node" | "update_node" | "delete_node" | "add_edge",
    "correlation_id": str,                       # UUID linking to AI-OS event
    "execution_id": str | None,                  # if part of an execution
    "task_id": str | None,                       # if part of a task
    "timestamp": str,                            # ISO 8601 UTC
    "request_id": str,                           # UUID per operation
    "version": int,                              # monotonic version counter
}
```

Provenance is embedded in:
- Node properties (`provenance` key)
- Edge properties (`provenance` key)
- Return values (operation metadata)

---

## 12. Security

### 12.1 Graph-Specific Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Sensitive data in node properties | HIGH | Property validation; redaction of known secret patterns |
| Credentials in graph | HIGH | Denylist on property keys (`password`, `token`, `secret`, `api_key`) |
| Malicious node injection | MEDIUM | Input validation; namespace isolation |
| Oversized properties | MEDIUM | Size limits (max 10KB per property value) |
| Unbounded graph growth | MEDIUM | Node limits per type; TTL on execution nodes |
| Circular dependency loops | LOW | BFS depth limit (max 10); no infinite recursion |
| Unauthorized graph mutation | HIGH | Write operations require explicit AI-OS trigger (no direct MCP writes) |
| Graph injection via query | MEDIUM | Query parameter validation; no raw Cypher execution |
| Excessive graph visibility | LOW | Namespace isolation; no cross-namespace queries |

### 12.2 Required Protections

1. **Property key denylist**: Reject nodes/edges with keys matching secret patterns
2. **Property value size limit**: Max 10,240 bytes per property value
3. **Query length limit**: Max 1,000 characters per query string
4. **Path depth limit**: Max 10 hops for shortest_path
5. **Namespace isolation**: All operations scoped to `"ai_os"` namespace
6. **No raw query execution**: No Cypher/gremlin; only pre-defined tool calls
7. **Input validation**: All string inputs validated for length, encoding, forbidden characters

### 12.3 Redaction Patterns

```python
SENSITIVE_PROPERTY_KEYS = {
    "password", "token", "secret", "api_key", "apikey",
    "authorization", "credential", "private_key", "access_token",
}

SECRET_VALUE_PATTERNS = [
    r"sk[-_]?[a-zA-Z0-9]{20,}",       # API keys
    r"Bearer\s+[a-zA-Z0-9._-]+",       # Bearer tokens
    r"(?:password|passwd|pwd)\s*[:=]\s*\S+",  # password assignments
]
```

---

## 13. Authority Boundaries

### 13.1 Graphify MAY

- Store nodes and edges
- Retrieve nodes and edges
- Query relationships
- Find paths between nodes
- Return structured context
- Mark data as advisory (C14)
- Emit operational logs

### 13.2 Graphify MAY NOT

- Decide PASS/FAIL on any test
- Approve or reject any result
- Issue security verdicts
- Become Council/Judge
- Override AI-OS policy
- Modify governance state
- Independently trigger workflow transitions
- Access kernel managers (SecurityManager, CouncilManager, etc.)
- Emit events directly to EventBus
- Call `CapabilityManager.register()` or modify registry
- Write to disk outside evidence directory
- Access filesystem

### 13.3 AI-OS Retains These Authorities

| Authority | Owner |
|-----------|-------|
| Task lifecycle | `StateManager` |
| Execution orchestration | `TestOrchestratorService` |
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

## 14. Context Retrieval

### 14.1 Query Boundaries

| Query Type | Method | Limit | Ordering |
|-----------|--------|-------|----------|
| Related entities | `get_related_entities()` | 50 per call | By relationship type, then created_at desc |
| Execution history | `get_execution_history()` | 20 per call | By finished_at desc |
| Dependency chain | `get_dependency_chain()` | 100 nodes, depth ≤ 10 | BFS ordered |
| Shortest path | `shortest_path()` | 10 hops max | BFS |
| Full graph query | `query_graph()` | 100 nodes max | By created_at desc |

### 14.2 Result Limits

- Maximum nodes returned per query: **100**
- Maximum edges returned per query: **500**
- Maximum path length: **10 hops**
- Maximum property value size: **10 KB**

### 14.3 Deterministic Ordering

All queries return results in a deterministic order:
- Primary sort: relationship type (alphabetical)
- Secondary sort: creation timestamp (newest first)
- Tertiary sort: node ID (alphabetical)

### 14.4 Stale Data Handling

If Graphify returns stale or missing data:
1. Return empty results (do NOT fabricate data)
2. Log warning with correlation_id
3. Continue with empty context (degrade gracefully)

---

## 15. Failure Model

### 15.1 Failure Scenarios

| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Graphify unavailable | Return empty context | Retry on next request |
| Connection failure | Raise `GraphifyUnavailableError` | Reconnect on next call |
| Timeout | Raise `GraphifyTimeoutError` | Return partial results if available |
| Malformed response | Raise `MalformedGraphifyResponseError` | Log error, return empty |
| Storage failure | Return `False` from write ops | Log warning, continue |
| Query failure | Return empty list | Log warning, continue |
| Backend crash | Raise `GraphifyBackendError` | Reconnect on next call |
| Partial synchronization | Return whatever is available | Log warning, retry writes |

### 15.2 Error Hierarchy

```python
class GraphifyError(Exception):
    """Base error for Graphify adapter."""

class GraphifyUnavailableError(GraphifyError):
    """Graphify MCP server not reachable."""

class GraphifyTimeoutError(GraphifyError):
    """Operation exceeded timeout."""

class GraphifyValidationError(GraphifyError):
    """Invalid input for graph operation."""

class GraphifyStorageError(GraphifyError):
    """Storage/write failure."""

class MalformedGraphifyResponseError(GraphifyError):
    """Malformed response from Graphify MCP."""

class GraphifySecurityError(GraphifyError):
    """Security violation (sensitive data attempt)."""
```

### 15.3 Failure Philosophy

**AI-OS degrades gracefully when Graphify is unavailable.**

- Read operations: return empty context (not error)
- Write operations: log warning, return False (not crash)
- No AI-OS functionality is blocked by Graphify failure
- Graphify is a **context enrichment** layer, not a core dependency

---

## 16. Lifecycle

### 16.1 Full Lifecycle

```
1. START
   ├─ MCPManager.connect("graphify")
   └─ Tool discovery (tools/list)

2. INIT
   ├─ Verify connection
   └─ Log readiness

3. OPERATIONAL
   ├─ Accept graph operations (CRUD, query, path)
   ├─ Mark all results as advisory (C14)
   └─ Track provenance per operation

4. IDLE
   ├─ MCP connection stays alive (auto_reconnect: true)
   └─ Ready for next operation

5. SHUTDOWN
   ├─ MCPManager.disconnect("graphify")
   └─ Clean up resources
```

### 16.2 Cleanup Behavior

| Scenario | Cleanup Action |
|----------|---------------|
| Success | No cleanup needed (stateless operations) |
| Failure | Log error, continue (no state to clean) |
| Timeout | Release connection, log warning |
| Shutdown | Disconnect MCP, clear internal state |

### 16.3 Leak Prevention

```python
# At adapter shutdown:
async def shutdown(self) -> None:
    await self._mcp_manager.disconnect(self._server_id)
    self._connected = False
```

---

## 17. Capability Registry Integration

### 17.1 Registration

Graphify must be registered as a capability in `CapabilityManager`:

```python
# In kernel.py _init_graphify():
capability_manager.register(
    capability_id="graphify_context",
    facade="graph",
    provider_id="graphify",
    provider_metadata={
        "server_id": "graphify",
        "transport": "stdio",
        "timeout_seconds": 30,
        "auto_reconnect": True,
    },
    security_context={
        "requires_validation": True,
        "allowed_operations": [
            "add_node", "get_node", "update_node", "delete_node",
            "query_graph", "shortest_path", "add_edge",
        ],
    },
    tags=("graph", "knowledge", "context", "relationships", "dependency"),
)
```

### 17.2 Why Registration Matters

- **Discovery**: Other components can discover graph capabilities
- **Security gating**: Registered capabilities go through SecurityManager validation
- **Lifecycle**: CapabilityManager tracks registered capabilities for shutdown/cleanup
- **Extensibility**: Future graph-based capabilities follow the same pattern

### 17.3 Kernel Wiring

Add to `kernel.py` `_init_graphify()` method called after `_init_m7_testing()`:

```python
async def _init_graphify(self) -> None:
    """Register M8-T3 Graphify context capability and adapter.

    Connects to the Graphify MCP server (via MCPManager stdio),
    registers the ``graphify_context`` capability in CapabilityManager,
    and wires the adapter for use by architecture testing and context enrichment.
    """
    if not self._capability_manager:
        logger.debug("CapabilityManager not available; skipping Graphify init")
        return

    # Create adapter — passes MCPManager for real path, None for test path
    adapter = GraphifyAdapter(
        mcp_manager=self._mcp_manager if hasattr(self, "_mcp_manager") else None,
        server_id="graphify",
    )
    self._graphify_adapter = adapter

    # Register capability
    self._capability_manager.register(
        capability_id="graphify_context",
        facade="graph",
        provider_id="graphify",
        provider_metadata={
            "server_id": "graphify",
            "transport": "stdio",
            "timeout_seconds": 30,
            "auto_reconnect": True,
        },
        security_context={
            "requires_validation": True,
            "allowed_operations": [
                "add_node", "get_node", "update_node", "delete_node",
                "query_graph", "shortest_path", "add_edge",
            ],
        },
        tags=("graph", "knowledge", "context", "relationships", "dependency"),
    )

    logger.debug("M8-T3 Graphify capability registered (graphify_context)")
```

**Must NOT change:** Kernel phase ordering, LifecycleManager integration, Core Manager lifecycle.

---

## 18. Test Strategy

### 18.1 Test Categories

| Category | Coverage | CI Status |
|----------|----------|-----------|
| Unit tests (mocked MCP) | All adapter logic | **MANDATORY** |
| Unit tests (mock server) | Protocol round-trip | **MANDATORY** |
| Integration tests (mock) | Full flow with mock server | **MANDATORY** |
| Negative tests | Authority boundaries, security | **MANDATORY** |
| Regression tests | M7 + M8-T1 + M8-T2 | **MANDATORY** |

### 18.2 Test Plan (27 Tests)

#### A. Adapter Creation (3 tests)
| # | Test | Scenario |
|---|------|----------|
| A1 | `test_adapter_creation` | Instantiates with default config |
| A2 | `test_adapter_injects_mcp` | Custom MCPManager injected for testing |
| A3 | `test_adapter_default_tool` | `_default_tool` raises NotImplementedError without MCP |

#### B. MCP Connection (3 tests)
| # | Test | Scenario |
|---|------|----------|
| B1 | `test_connect_success` | Connects to mock Graphify server |
| B2 | `test_connect_process_not_found` | Missing Python → raises GraphifyUnavailableError |
| B3 | `test_disconnect` | Disconnect cleans up connection |

#### C. Node Operations (5 tests)
| # | Test | Scenario |
|---|------|----------|
| C1 | `test_store_node` | Store node, verify in graph |
| C2 | `test_get_node` | Retrieve stored node |
| C3 | `test_get_node_not_found` | Missing node → returns None |
| C4 | `test_update_node` | Update node properties |
| C5 | `test_delete_node` | Delete node, verify removed |

#### D. Edge Operations (3 tests)
| # | Test | Scenario |
|---|------|----------|
| D1 | `test_add_edge` | Add edge, verify in graph |
| D2 | `test_add_edge_duplicate` | Duplicate edge → no duplicate created |
| D3 | `test_add_edge_missing_node` | Edge to non-existent node → warning, edge still created |

#### E. Query Operations (3 tests)
| # | Test | Scenario |
|---|------|----------|
| E1 | `test_query_graph` | Query returns nodes and edges |
| E2 | `test_shortest_path` | Path found between connected nodes |
| E3 | `test_shortest_path_not_found` | No path → empty list |

#### F. Context Enrichment (3 tests)
| # | Test | Scenario |
|---|------|----------|
| F1 | `test_get_related_entities` | Returns related nodes with relationship type |
| F2 | `test_get_execution_history` | Returns execution nodes ordered by time |
| F3 | `test_get_dependency_chain` | Returns full dependency chain |

#### G. Provenance (2 tests)
| # | Test | Scenario |
|---|------|----------|
| G1 | `test_provenance_complete` | All mandatory provenance fields present |
| G2 | `test_provenance_no_secrets` | No plaintext secrets in provenance |

#### H. Advisory Marking (C14) (2 tests)
| # | Test | Scenario |
|---|------|----------|
| H1 | `test_advisory_marking_on_retrieve` | Retrieved nodes marked advisory |
| H2 | `test_advisory_marking_on_query` | Queried results marked advisory |

#### I. Security (3 tests)
| # | Test | Scenario |
|---|------|----------|
| I1 | `test_sensitive_property_rejected` | Node with password property → rejected |
| I2 | `test_oversized_property_rejected` | Property > 10KB → rejected |
| I3 | `test_no_verdict_in_result` | ExecutionResult has no verdict field |

#### J. Failure Handling (2 tests)
| # | Test | Scenario |
|---|------|----------|
| J1 | `test_graphify_unavailable` | Server down → returns empty context, no crash |
| J2 | `test_malformed_response` | Bad JSON response → MalformedGraphifyResponseError |

#### K. Capability Registry (1 test)
| # | Test | Scenario |
|---|------|----------|
| K1 | `test_capability_registered` | Graphify capability registered in CapabilityManager |

#### L. Regression (0 new — existing suite)
| # | Test | Scenario |
|---|------|----------|
| L1 | `test_regression_all` | Full `pytest tests/ -q` → all pass |

### 18.3 Expected Test Count

| Before M8-T3 | New M8-T3 Tests | After M8-T3 |
|-------------|-----------------|-------------|
| 1079 (passing) | 27 | **1106** |

---

## 19. File-Level Change Plan

### 19.1 NEW: `src/aios/adapters/graphify_adapter.py`

**Purpose:** Graphify MCP adapter implementing `BaseExecutionAdapter`.

**Changes:** Create from scratch.

**Why necessary:** Core M8-T3 deliverable — bridges MCPManager to Graphify graph operations.

**Dependencies:** `mcp_manager.py`, `base.py`, `uuid`, `hashlib`, `logging`, `asyncio`.

**Interface:**
```python
class GraphifyAdapter(BaseExecutionAdapter):
    perspective = "graphify_context"

    def __init__(
        self,
        mcp_manager: MCPManager | None = None,
        server_id: str = "graphify",
        timeout_seconds: int = 30,
        namespace: str = "ai_os",
    ) -> None: ...

    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def store_node(self, entity_id: str, label: str, properties: dict) -> bool: ...
    async def get_node(self, entity_id: str) -> dict | None: ...
    async def update_node(self, entity_id: str, properties: dict) -> bool: ...
    async def delete_node(self, entity_id: str) -> bool: ...
    async def add_edge(
        self, from_id: str, to_id: str, relationship: str, properties: dict | None = None
    ) -> bool: ...
    async def get_related_entities(
        self, entity_id: str, relationship_type: str | None = None, limit: int = 50
    ) -> list[dict]: ...
    async def get_execution_history(
        self, execution_id: str, limit: int = 20
    ) -> list[dict]: ...
    async def get_dependency_chain(
        self, entity_id: str, max_depth: int = 10
    ) -> list[dict]: ...
    async def query_graph(self, query: str, limit: int = 100) -> dict: ...
    def is_connected(self) -> bool: ...
    async def cleanup(self) -> None: ...
```

**Implementation notes:**
- Inherits from `BaseExecutionAdapter`
- Uses `MCPManager` for tool calls (stdio to Graphify MCP)
- All results marked advisory per C14
- Property validation (size, sensitive keys)
- Namespace prefix on all entity IDs
- Deferred import of MCPManager (not module scope)

### 19.2 MODIFIED: `src/aios/adapters/architecture_agency_adapter.py`

**Purpose:** Enhance ArchitectureAgencyAdapter to use real GraphifyAdapter when available.

**Changes:**
1. Add optional `graphify_adapter` parameter to constructor
2. Replace/add `_graphify_scan()` method that queries GraphifyAdapter
3. Keep existing `_default_graphify_scan` as fallback (graceful degradation)
4. `_graphify_scan` queries graph for dependency violations, circular references, boundary issues

**Why necessary:** M8-T3 deliverable — activates real graph traversal for architecture testing.

**Must NOT change:**
- `perspective = "architecture"` (unchanged)
- Constructor signature pattern (add optional param with default)
- `ExecutionResult` return type (unchanged)
- Existing text-scanner fallback behavior

### 19.3 MODIFIED: `src/aios/core/kernel.py`

**Purpose:** Wire Graphify capability and adapter.

**Changes:**
1. Import `GraphifyAdapter`
2. Add `_init_graphify()` method called after `_init_m7_testing()`
3. Register `graphify_context` capability in CapabilityManager
4. Create `GraphifyAdapter` instance
5. Add config reading for `graphify:` section

**Why necessary:** Kernel-level integration; capability registration.

**Must NOT change:**
- Kernel phase ordering
- LifecycleManager integration
- Existing M7 testing wiring
- Core Manager lifecycle

### 19.4 MODIFIED: `config/defaults.yaml`

**Purpose:** Add Graphify configuration section.

**Changes:** Add:
```yaml
graphify:
  server_id: "graphify"              # MCP server ID
  timeout_seconds: 30                # Default timeout
  auto_reconnect: true               # Auto-reconnect on failure
  max_query_results: 100             # Max nodes per query
  max_path_depth: 10                 # Max hops for path queries
  namespace: "ai_os"                 # Namespace isolation
  property_size_limit: 10240         # Max bytes per property value
  sensitive_keys:                    # Keys to redact
    - "password"
    - "token"
    - "secret"
    - "api_key"
    - "authorization"
```

### 19.5 NEW: `tests/unit/test_graphify_adapter.py`

**Purpose:** Unit tests for GraphifyAdapter (27 tests total across all categories).

**Why necessary:** Verify MCP connection, CRUD operations, queries, provenance, security, authority boundaries.

### 19.6 MODIFIED: `tests/unit/test_agency_adapters.py`

**Purpose:** Update architecture adapter test for Graphify integration.

**Changes:**
- Add test for real Graphify path
- Update existing tests for graceful degradation when Graphify unavailable

### 19.7 NEW: `tests/integration/test_m8_graphify.py`

**Purpose:** Integration tests for Graphify adapter path (8 tests).

**Why necessary:** End-to-end protocol verification with mock Graphify MCP.

---

## 20. Implementation Order

### Step 1: Configuration (5 min)
1. Add `graphify:` section to `config/defaults.yaml`
2. Verify config loads correctly

### Step 2: GraphifyAdapter (30 min)
3. Create `src/aios/adapters/graphify_adapter.py`
4. Implement `__init__` with MCPManager injection
5. Implement `connect()` / `disconnect()`
6. Implement node CRUD: `store_node`, `get_node`, `update_node`, `delete_node`
7. Implement edge operations: `add_edge`
8. Implement query operations: `query_graph`, `shortest_path`
9. Implement context enrichment: `get_related_entities`, `get_execution_history`, `get_dependency_chain`
10. Implement C14 advisory marking
11. Implement property validation (size, sensitive keys)
12. Implement provenance tracking
13. Implement error classification

### Step 3: ArchitectureAgencyAdapter Enhancement (15 min)
14. Modify `src/aios/adapters/architecture_agency_adapter.py`
15. Add `graphify_adapter` optional parameter
16. Add `_graphify_scan()` method
17. Keep text scanner as fallback
18. Wire adapter to use Graphify when available

### Step 4: Kernel Wiring (10 min)
19. Modify `src/aios/core/kernel.py`
20. Import `GraphifyAdapter`
21. Add `_init_graphify()` method
22. Register `graphify_context` capability
23. Wire adapter to kernel

### Step 5: Unit Tests (20 min)
24. Create `tests/unit/test_graphify_adapter.py` (27 tests)
25. Update `tests/unit/test_agency_adapters.py` for Graphify path

### Step 6: Integration Tests (15 min)
26. Create `tests/integration/test_m8_graphify.py` (8 tests)

### Step 7: Regression (10 min)
27. Run full suite: `pytest tests/ -q` → expect 1106 passed
28. Run M7 regression: `pytest tests/integration/test_m7_*.py tests/unit/test_user_simulation_agent.py -v` → all pass
29. Run M8-T1 regression: `pytest tests/unit/test_acp_adapter.py tests/unit/test_hermes_bridge_acp.py tests/integration/test_m8_hermes_acp.py -v` → all pass
30. Run M8-T2 regression: `pytest tests/unit/test_playwright_mcp_adapter.py tests/unit/test_playwright_session.py tests/integration/test_m8_playwright.py -v` → all pass
31. Verify no forbidden words in adapter: `grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/graphify_adapter.py` → zero matches

---

## 21. Acceptance Criteria

### A. Integration
- [ ] `GraphifyAdapter` implements `BaseExecutionAdapter`
- [ ] Adapter connects to Graphify MCP via `MCPManager` (stdio)
- [ ] Tool discovery succeeds (tools/list returns 7 Graphify tools)
- [ ] `ArchitectureAgencyAdapter` uses real Graphify when available
- [ ] Graceful degradation when Graphify unavailable

### B. Graph Operations
- [ ] Node store works
- [ ] Node retrieve works
- [ ] Node update works
- [ ] Node delete works
- [ ] Edge add works
- [ ] Graph query works
- [ ] Shortest path works

### C. Context Enrichment
- [ ] `get_related_entities` returns connected nodes
- [ ] `get_execution_history` returns execution nodes
- [ ] `get_dependency_chain` returns dependency graph
- [ ] All results limited by configured limits

### D. C14 Compliance
- [ ] All retrieved data marked advisory
- [ ] Provenance includes `source=graphify_inferred`
- [ ] Provenance includes `advisory=True`
- [ ] Provenance includes `authority=advisory_only`
- [ ] Provenance includes `graphify_timestamp`

### E. Provenance
- [ ] Every operation has complete provenance
- [ ] Provenance includes execution_id, correlation_id
- [ ] No secrets in provenance
- [ ] Correlation IDs traceable

### F. Security
- [ ] Sensitive property keys rejected
- [ ] Oversized properties rejected
- [ ] No secret leakage in logs
- [ ] Namespace isolation enforced

### G. Failure Handling
- [ ] Graphify unavailable → returns empty context, not crash
- [ ] Timeout → raises GraphifyTimeoutError
- [ ] Malformed response → raises MalformedGraphifyResponseError
- [ ] Connection failure → raises GraphifyUnavailableError

### H. Lifecycle
- [ ] Connect → operational → disconnect works
- [ ] Cleanup on exception path works
- [ ] No resource leaks after tests

### I. Authority Boundaries
- [ ] Adapter never emits verdict/pass/fail
- [ ] Adapter never calls SecurityManager, CouncilManager, StateManager
- [ ] Adapter never writes to disk outside evidence dir
- [ ] No forbidden words in adapter code

### J. Capability Registry
- [ ] `graphify_context` capability registered
- [ ] Capability discoverable by facade "graph"
- [ ] Security validation passes

### K. Backward Compatibility
- [ ] All 1079 existing tests pass
- [ ] M7 tests pass (18 tests)
- [ ] M8-T1 tests pass (33 tests)
- [ ] M8-T2 tests pass (33 tests)
- [ ] `kernel.py` wiring preserves existing behavior
- [ ] No changes to MCPManager, CapabilityManager, TestingEvidence
- [ ] No changes to HermesBridge, UserSimulationAgent
- [ ] No changes to PlaywrightMCPAdapter, PlaywrightSessionRegistry

### L. Real E2E
- [ ] Mock Graphify server used in all tests
- [ ] Real Graphify integration possible via MCP config

---

## 22. Risk Register

| Risk | Likelihood | Impact | Mitigation | Verification |
|------|-----------|--------|------------|-------------|
| Graphify mock server incompatibility | **Medium** | Tests fail | Use existing mock_graphify_server.py; verify tool names match | `test_connect_success` passes |
| Breaking ArchitectureAgencyAdapter | **Medium** | Regression | Keep text scanner as fallback; add Graphify path as optional | `test_agency_adapters` passes with/without Graphify |
| Property validation too strict | **Low** | False positives | Allowlist-based validation; configurable sensitive keys | `test_sensitive_property_rejected` passes |
| Namespace collision | **Low** | Data leakage | Prefix all entity IDs with namespace; validate on write | No cross-namespace queries in tests |
| MCP connection leak | **Low** | Resource exhaustion | `cleanup()` at adapter shutdown; try/finally in tests | `test_disconnect` passes |
| Unbounded graph growth | **Medium** | Memory exhaustion | Node limits per type; TTL on execution nodes (future) | `test_query_graph_limit` passes |
| Stale graph context | **Medium** | Incorrect analysis | Mark all context as advisory; document eventual consistency | C14 tests pass |
| Authority leakage | **Low** | Security violation | Code review; grep for forbidden patterns | `test_no_verdict_in_result` passes |
| Breaking existing GraphifyBackend | **Low** | Memory system regression | GraphifyAdapter is separate class; GraphifyBackend unchanged | `test_m5_gate.py` passes |
| Non-deterministic query results | **Medium** | Flaky tests | Deterministic ordering (relationship type, timestamp, ID) | All query tests pass consistently |

---

## 23. Backward Compatibility

### 23.1 Existing Code Unaffected

| Component | Change | Reason |
|-----------|--------|--------|
| `MCPManager` | **UNCHANGED** | Graphify uses existing MCPManager |
| `CapabilityManager` | **UNCHANGED** | New registration only; no API changes |
| `TestingEvidence` | **UNCHANGED** | Same schema; Graphify context fits |
| `HermesBridge` | **UNCHANGED** | Separate adapter; no cross-dependency |
| `UserSimulationAgent` | **UNCHANGED** | Uses HermesBridge, not Graphify |
| `PlaywrightMCPAdapter` | **UNCHANGED** | Separate adapter; no cross-dependency |
| `PlaywrightSessionRegistry` | **UNCHANGED** | Separate module |
| `GraphifyBackend` | **UNCHANGED** | Existing memory backend preserved |
| `ArchitectureAgencyAdapter` | **MINIMAL** | Optional Graphify path; text scanner fallback preserved |
| `kernel.py` | **MINIMAL** | New `_init_graphify()` method; existing wiring preserved |
| `config/defaults.yaml` | **ADDED** | New `graphify:` section; existing `hermes:` and `playwright:` preserved |

### 23.2 Graceful Degradation

If Graphify is not available:
1. `GraphifyAdapter.__init__()` succeeds (no MCP required at construction)
2. `connect()` raises `GraphifyUnavailableError`
3. `ArchitectureAgencyAdapter` falls back to text scanner `_default_graphify_scan`
4. All existing tests pass (Graphify tests pass with mock server)

### 23.3 Test Baseline

- **Before M8-T3:** 1079 tests passing
- **After M8-T3:** 1106 tests (1079 existing + 27 new)
- **Expected failures:** 0
- **Expected skips:** None

---

## 24. Real E2E Requirements

### 24.1 Prerequisites for Real Graphify

```bash
# 1. Graphify MCP server must be available
#    (either local mock or remote Graphify instance)

# 2. Config must point to correct server
#    config/mcp/graphify_mcp.json updated with real server details
```

### 24.2 E2E Test Gate

```python
# tests/integration/test_m8_graphify.py
@pytest.mark.skipif(
    not os.environ.get("GRAPHIFY_E2E_TEST", "").lower() in ("1", "true", "yes"),
    reason="GRAPHIFY_E2E_TEST not set"
)
async def test_real_graphify_integration():
    """Real Graphify E2E: store, query, path."""
    adapter = GraphifyAdapter()
    await adapter.connect()
    await adapter.store_node("task:e2e1", "task", {"title": "E2E Task"})
    await adapter.store_node("task:e2e2", "task", {"title": "E2E Task 2"})
    await adapter.add_edge("task:e2e1", "task:e2e2", "DEPENDS_ON")
    path = await adapter.get_dependency_chain("task:e2e2")
    assert len(path) > 0
    await adapter.disconnect()
```

### 24.3 CI Behavior

- **Standard CI:** All 1106 tests pass (mock-based only)
- **Real Graphify CI:** Set `GRAPHIFY_E2E_TEST=1` in CI config; run E2E tests separately
- **Local development:** Developer configures real Graphify server; E2E tests available

---

## 25. Do-Not-Implement

### 25.1 Explicitly OUT OF SCOPE for M8-T3

| Item | Belongs To |
|------|-----------|
| Final decision authority | M8-T3 explicitly forbidden |
| Verification authority | M8-T3 explicitly forbidden |
| Council / Judge | M8-T3 explicitly forbidden |
| Security authority | M8-T3 explicitly forbidden |
| Workflow authority | M8-T3 explicitly forbidden |
| LearningService | M9 |
| RCA pipeline | M9 |
| Model router | M9 |
| Convergence detection | M10 |
| Notion integration | M8-T4 |
| Obsidian integration | M8-T4 |
| Claude-Mem integration | M8-T4 |
| M8-T5 broad capability hardening | M8-T5 |
| M8-T6 complete integration testing | M8-T6 |
| M8-T7 final M8 QA | M8-T7 |
| Distributed graph infrastructure | Future |
| Graph visualization | Future |
| Graph persistence (beyond MCP) | Future |
| Real Graphify server dependency | Future (mock sufficient for M8-T3) |
| Graph ML / embedding | Future |
| Cross-project graph sharing | Future |
| Graph-based automated remediation | M9 |

### 25.2 Forbidden Patterns

```python
# FORBIDDEN in GraphifyAdapter code:
from aios.core.security_manager import SecurityManager  # No direct security calls
from aios.core.council_manager import CouncilManager    # No council access
from aios.core.state import StateManager                # No state mutation
self._event_bus.publish(...)                            # No direct event emission
return {"verdict": "pass"}                              # No verdict in results
return {"status": "approved"}                           # No approval language
return {"decision": "reject"}                           # No rejection language
```

---

## 26. Terminal 2 Implementation Prompt

```
Execute M8-T3: Graphify Relationship / Knowledge Graph Integration

READ THESE FILES FIRST (in order):
1. src/aios/adapters/base.py (BaseExecutionAdapter pattern)
2. src/aios/adapters/acp_adapter.py (error classification pattern from M8-T1)
3. src/aios/adapters/mock_graphify_server.py (existing mock server to reuse)
4. src/aios/core/memory.py lines 265-549 (existing GraphifyBackend to understand)
5. src/aios/adapters/architecture_agency_adapter.py (existing adapter to enhance)
6. src/aios/core/kernel.py lines 846-884 (_init_playwright context for pattern)
7. src/aios/core/capability_manager.py (registration pattern)
8. config/defaults.yaml (current config structure)
9. tests/unit/test_m5_gate.py lines 509-590 (existing Graphify tests)
10. tests/unit/test_agency_adapters.py (test pattern for adapters)
11. architecture/Part15/M8/M8-T1-IMPLEMENTATION-SPEC.md (M8-T1 patterns)
12. architecture/Part15/M8/M8-T2-IMPLEMENTATION-SPEC.md (M8-T2 patterns)

THEN FOLLOW THIS EXACT SEQUENCE:

STEP 1: Add graphify configuration to config/defaults.yaml
  - Add graphify: section with server_id, timeout_seconds, auto_reconnect,
    max_query_results, max_path_depth, namespace, property_size_limit, sensitive_keys

STEP 2: Create GraphifyAdapter
  - Create src/aios/adapters/graphify_adapter.py
  - Inherit from BaseExecutionAdapter
  - perspective = "graphify_context"
  - __init__(mcp_manager=None, server_id="graphify", timeout_seconds=30, namespace="ai_os")
  - connect() → bool (via MCPManager)
  - disconnect() → None
  - store_node(entity_id, label, properties) → bool
  - get_node(entity_id) → dict | None
  - update_node(entity_id, properties) → bool
  - delete_node(entity_id) → bool
  - add_edge(from_id, to_id, relationship, properties) → bool
  - get_related_entities(entity_id, relationship_type=None, limit=50) → list[dict]
  - get_execution_history(execution_id, limit=20) → list[dict]
  - get_dependency_chain(entity_id, max_depth=10) → list[dict]
  - query_graph(query, limit=100) → dict
  - is_connected() → bool
  - cleanup() → None
  - _mark_advisory(metadata) → dict  # C14 compliance
  - _validate_properties(properties) → None  # security validation
  - _make_entity_id(entity_id) → str  # namespace prefix
  - Error classification: GraphifyError hierarchy
  - Deferred import of MCPManager (not module scope)
  - All string inputs validated for length/encoding

STEP 3: Enhance ArchitectureAgencyAdapter
  - Modify src/aios/adapters/architecture_agency_adapter.py
  - Add optional graphify_adapter parameter to __init__
  - Add _graphify_scan(target, context) method that queries GraphifyAdapter
  - Keep existing _default_graphify_scan as fallback
  - _graphify_scan queries graph for:
    * Circular dependencies (A→B→A)
    * Boundary violations (cross-layer dependencies)
    * Orphan nodes (tasks with no executions)
  - Return ExecutionResult with graph-based findings

STEP 4: Wire into Kernel
  - Modify src/aios/core/kernel.py
  - Import GraphifyAdapter
  - Add _init_graphify() method after _init_playwright()
  - Register "graphify_context" capability in CapabilityManager
  - Create GraphifyAdapter instance
  - Set self._graphify_adapter = adapter

STEP 5: Write Unit Tests
  - Create tests/unit/test_graphify_adapter.py (27 tests)
  - Categories: adapter creation (3), MCP connection (3), node ops (5),
    edge ops (3), query ops (3), context enrichment (3), provenance (2),
    advisory/C14 (2), security (3), failure handling (2), capability registry (1)

STEP 6: Update Agency Adapter Tests
  - Modify tests/unit/test_agency_adapters.py
  - Add test for real Graphify path
  - Update existing tests for graceful degradation

STEP 7: Write Integration Tests
  - Create tests/integration/test_m8_graphify.py (8 tests)
  - Full flow tests with mock Graphify MCP server

STEP 8: Run Regression
  - pytest tests/ -q → expect 1106 passed, 0 failed
  - pytest tests/integration/test_m7_*.py tests/unit/test_user_simulation_agent.py -v → all pass
  - pytest tests/unit/test_acp_adapter.py tests/unit/test_hermes_bridge_acp.py tests/integration/test_m8_hermes_acp.py -v → all pass
  - pytest tests/unit/test_playwright_mcp_adapter.py tests/unit/test_playwright_session.py tests/integration/test_m8_playwright.py -v → all pass
  - pytest tests/unit/test_m5_gate.py -v → all pass (GraphifyBackend tests)
  - grep -nE 'verdict|approved|rejected|secure|compliant' src/aios/adapters/graphify_adapter.py → zero matches

CRITICAL CONSTRAINTS:
- Do NOT change MCPManager
- Do NOT change CapabilityManager API
- Do NOT change TestingEvidence schema
- Do NOT change HermesBridge or UserSimulationAgent
- Do NOT change PlaywrightMCPAdapter or PlaywrightSessionRegistry
- Do NOT change GraphifyBackend (existing memory backend)
- Do NOT import MCPManager at module scope in graphify_adapter.py (deferred import)
- Do NOT let Graphify become verifier/judge/council
- All new tests must use real protocol round-trips (mock server, not hardcoded returns)
- Regression must stay at 0 failures
- No new EventType values
- Adapters only; no kernel decision logic changes
- ArchitectureAgencyAdapter text scanner fallback MUST be preserved

ACCEPTANCE:
- 1106 tests passing (1079 existing + 27 new)
- Graphify capability registered
- Graph operations work (mock server)
- Context enrichment works
- C14 advisory marking verified
- Provenance complete
- Security verified (no secret leakage, property validation)
- Authority boundaries enforced
- ArchitectureAgencyAdapter enhanced with real graph path
- Graceful degradation when Graphify unavailable
```

---

## Appendix A: Graphify MCP Tool Reference

The `mock_graphify_server.py` exposes these tools:

| Tool | Purpose | Key Arguments | Return |
|------|---------|--------------|--------|
| `add_node` | Create node | `node_id`, `label`, `properties` (optional) | `{node_id, created}` |
| `get_node` | Retrieve node | `node_id` | `{id, label, properties}` |
| `update_node` | Update node | `node_id`, `properties` | `{node_id, updated}` |
| `delete_node` | Remove node | `node_id` | `{node_id, deleted}` |
| `query_graph` | Query graph | `query` (string) | `{nodes, edges}` |
| `shortest_path` | BFS path | `from_node`, `to_node`, `max_depth` | `{path, found}` |
| `add_edge` | Create edge | `from_node`, `to_node`, `relationship`, `properties` (optional) | `{edge, created}` |

## Appendix B: Comparison with M8-T1 and M8-T2

| Aspect | M8-T1 (Hermes ACP) | M8-T2 (Playwright MCP) | M8-T3 (Graphify MCP) |
|--------|-------------------|----------------------|---------------------|
| Protocol | ACP preferred, MCP fallback | MCP only | MCP only |
| Transport | stdio | stdio | stdio |
| Purpose | User simulation | Browser execution | Relationship/context storage & retrieval |
| Session model | ACP session registry | Browser context registry | Stateless (no session model) |
| Evidence | Text observations | Screenshot + DOM | Graph structure + relationships |
| Adapter pattern | `HermesBridge` (thin wrapper) | `PlaywrightMCPAdapter` (implements BaseExecutionAdapter) | `GraphifyAdapter` (implements BaseExecutionAdapter) |
| Integration point | `UserSimulationAgent` | `AccessibilityAgencyAdapter` | `ArchitectureAgencyAdapter` + context enrichment |
| Authority | Observation only | Observation only | Context enrichment only (C14 advisory) |
| Mock server | `mock_hermes_acp_server.py` | `mock_playwright_mcp_server.py` | `mock_graphify_server.py` (EXISTING) |
| Test count added | 33 | 33 | 27 |
| Total after | 1079 | 1112 | 1106 |

## Appendix C: C14 Compliance Notes

Per architecture requirement C14:
- All Graphify-sourced data is **advisory/inferred**
- Must NOT be treated as authoritative/canonical
- Must carry explicit provenance indicating advisory nature
- Must include `graphify_timestamp` in provenance
- Must include `authority=advisory_only` in provenance

The `GraphifyAdapter._mark_advisory()` method ensures all retrieved data carries this provenance.

---

*End of M8-T3 Implementation Specification.*

**Final Status: M8-T3 PLANNING COMPLETE — READY FOR IMPLEMENTATION**
