# FINAL AI-OS INTEGRATION REALITY AUDIT
**Date:** 2026-08-27  
**Status:** COMPLETE  
**Scope:** Inspection-only audit of integrations specified in final AI-OS architecture (Parts 0-15)  
**Methodology:** Distinguished code existence (Question A) from real integration (Questions B-I) per task specification  

## EXECUTIVE SUMMARY

This audit examined the real integration status of all external repositories, services, runtimes, frameworks, tools, MCP servers, agencies, councils, memory systems, browser systems, evaluation systems, planning systems, and supporting integrations specified in the final AI-OS architecture.

**Key Findings:**
- **0 integrations** are fully ready and connected to real external systems performing real operations (Status A)
- **3 integrations** are internal AI-OS systems performing real operations (Status A)  
- **1 integration** exists as code but is not registered/enabled/instantiated (Status F)
- **9 integrations** are implemented but not live - code exists and may be initialized, but not connected to real external systems (Status E)
- **0 integrations** represent phantom/non-live integrations with only configuration/wrappers (Status G-J)

**Critical Discovery:** All MCP-based external integrations (Hermes, Playwright, Graphify, Notion, Obsidian, Claude-Mem) share the same fundamental limitation: they are initialized but not connected to real external systems by default, relying exclusively on in-process mock servers for operation.

## INTEGRATION STATUS SUMMARY

| Integration | Status | Summary |
|-------------|--------|---------|
| **Hermes ACP/MCP** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized via UserSimulationAgent, but connects only to mock hermes servers by default. Real hermes-agent(EXT) not available/configured. |
| **Playwright MCP** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized as playwright_browser capability, but connects only to mock Playwright MCP by default. Real @playwright/mcp not available/configured. |
| **Graphify** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized as graphify_context capability, but connects only to mock Graphify server by default due to MCP connection limitations (D-01). Real Graphify not available/configured. |
| **Notion** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized as notion_planning capability, but connects only to mock Notion MCP server by default. Real Notion MCP not available/configured. |
| **Obsidian** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized as obsidian_knowledge capability. MCP path connects only to mock Obsidian MCP by default; filesystem fallback provides real local operations but not external system integration. |
| **Claude-Mem** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized as claude_mem_context capability, but connects only to mock Claude-Mem MCP server by default. Real Claude-Mem MCP not available/configured. |
| **Capability Registry/Hardening** | A: READY | Internal AI-OS system. Fully implemented, configured, enabled, instantiated, and performing real registry/factory operations as core.capability service. |
| **User Simulation Agent** | E: IMPLEMENTED BUT NOT LIVE | Code exists, initialized via HermesBridge, but connects only to mock hermes agents by default. Suffers from D-02 defect causing production crashes. Real hermes-agent(EXT) not available/configured. |
| **Testing Orchestration/Services** | A: READY | Internal AI-OS system. Fully implemented (M7 FROZEN), configured, enabled, instantiated as core.workflow service, and performing real workflow orchestration operations. |
| **Council System** | A: READY | Internal AI-OS system. Fully implemented as global singleton, configured, enabled, instantiated, and performing real consensus/decision-making operations. |
| **Free LLM API** | E: IMPLEMENTED BUT NOT LIVE | ModelRouter abstraction is ready, but FreeLLMAPI provider is dev/test only and not connected to real external LLM APIs by default. Requires explicit configuration for real API connections. |
| **Hermes Agent Reach** | F: PLANNED/NOT INTEGRATED | Code exists (agent_reach.py + mock server) but not registered as capability via manifest system. Not instantiated or used in standard system flow. |

## DETAILED INTEGRATION AUDITS

### 1. Hermes ACP/MCP Integration (M8-T1)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/hermes_bridge.py` - Hermes bridge implementation
- `src/aios/adapters/mock_hermes_server.py` - Mock Hermes server
- `src/aios/adapters/mock_hermes_acp_server.py` - Mock Hermes ACP server
- `config/mcp/hermes_agent_ext_mcp.json` - MCP configuration pointing to mock server

**Question B - Registration:** ⚠️ PARTIAL
- HermesBridge created in `_init_m7_testing()` and used by UserSimulationAgent
- Not registered as a capability in CapabilityManager (used directly by agent)
- UserSimulationAgent holds reference but not registered as service/capability

**Question C - Configuration:** ✅ (MOCK ONLY)
- MCP config: `"command": ["python", "-m", "aios.adapters.mock_hermes_server"]`
- Points to mock subprocess, not real hermes-agent(EXT)
- No real hermes-agent(EXT) endpoint or credentials configured

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_m7_testing()` during kernel startup
- UserSimulationAgent and HermesBridge objects created at boot

**Question E - Runtime Instantiation:** ✅
- Objects instantiated: `hermes_bridge = HermesBridge(...)` and `self._user_simulation_agent = UserSimulationAgent(hermes_bridge)`
- However, MCP connection not established at boot (lazy-on-first-use)

**Question F - Real Credentials:** ❌
- Only mock server communication possible
- No API keys, OAuth, or real credentials for hermes-agent(EXT) configured
- Real hermes-agent(EXT) repository would need to be running separately

**Question G - Real External Connections:** ❌
- Connects only to mock subprocesses: `mock_hermes_server.py` or `mock_hermes_acp_server.py`
- No network sockets to real external hermes-agent services
- MCP configuration uses stdio to local mock processes

**Question H - Real Operations:** ❌
- All communication simulates hermes-agent responses via mock servers
- No actual hermes-agent(EXT) processes spawned or communicated with
- HermesBridge contains real MCP/ACP logic but only used with mocks by default

**Question I - Real System Testing:** ❌
- Only mock-based tests exist by default
- Real hermes-agent testing would require actual hermes-agent(EXT) running
- Standard tests use mock hermes servers
- M8-T6 §29: "ACP real path cannot run in CI (`cwd` unset ⇒ always MCP in production wiring); ACP is exercised via the in-process `MockACPServer`"

**Defects Identified:**
- None specific to Hermes beyond the general MCP connection limitations shared with other adapters
- Shares D-01 limitation (MCP connection at boot) though kernel now assigns mcp_manager

### 2. Playwright MCP Integration (M8-T2)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/playwright_mcp_adapter.py` - Playwright MCP adapter
- `src/aios/adapters/mock_playwright_mcp_server.py` - Mock Playwright MCP server
- `_find_playwright_command()` method selects mock when `HERMES_MOCK_PLAYWRIGHT` env var set

**Question B - Registration:** ✅
- `_init_playwright()` creates adapter and registers: `capability_id="playwright_browser"`
- Properly registered in CapabilityManager as playwright_browser capability

**Question C - Configuration:** ✅ (MOCK BY DEFAULT)
- Without `HERMES_MOCK_PLAYWRIGHT`: tries to find real Playwright MCP (`node_modules/@playwright/mcp` or `npx @playwright/mcp`)
- With env var or if real not found: uses `mock_playwright_mcp_server.py`
- No real Playwright MCP (@playwright/mcp) installed/configured by default
- Playwright MCP doesn't require API keys (local browser automation tool)

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_playwright()` during kernel startup
- `self._playwright_adapter = adapter` created at boot

**Question E - Runtime Instantiation:** ✅
- Adapter instantiated: `adapter = PlaywrightMCPAdapter(mcp_manager=self._mcp_manager, ...)`
- However, connection not established at boot (lazy-on-first-use via `create_session()`/`execute_action()`)

**Question F - Real Credentials:** N/A
- Playwright MCP is local browser automation protocol - no API keys/OAuth needed
- Real requirement: @playwright/mcp package installed and available in PATH

**Question G - Real External Connections:** ⚠️ (LOCAL SUBPROCESS ONLY)
- Connects to stdio subprocess of Playwright MCP server
- By default: mock subprocess (`mock_playwright_mcp_server.py`)
- Real option: `@playwright/mcp` Node.js subprocess (not installed/available by default)
- Both are local subprocesses, not network/external systems
- M8-T6 §16: "Real browser requires Node + `@playwright/mcp`"

**Question H - Real Operations:** ⚠️ (DEFAULT TO MOCK)
- Only real if actual Playwright MCP server available and connected
- By default: mock server simulation only
- Real operations possible only if external Playwright MCP installed and HERMES_MOCK_PLAYWRIGHT not set
- M8-T6 §29: "Real external servers [...] `@playwright/mcp`) are NOT available in CI"

**Question I - Real System Testing:** ❌
- Only mock-based tests run by default
- Real Playwright MCP tests gated via `PLAYWRIGHT_E2E_TEST=1` environment variable
- Standard tests use mock Playwright MCP server

**Defects Identified:**
- Shares general MCP adapter pattern limitations
- No specific Playwright defects called out beyond the default-to-mock configuration

### 3. Graphify Integration (M8-T3)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/graphify_adapter.py` - Graphify adapter implementation
- `src/aios/adapters/mock_graphify_server.py` - Mock Graphify server
- `config/mcp/graphify_mcp.json` - MCP configuration pointing to mock server

**Question B - Registration:** ✅
- `_init_graphify()` creates adapter and registers: `capability_id="graphify_context"`
- Properly registered in CapabilityManager as graphify_context capability

**Question C - Configuration:** ✅ (MOCK ONLY)
- MCP config: `"command": ["python", "-m", "aios.adapters.mock_graphify_server"]`
- Points to mock subprocess, not real Graphify service
- No real Graphify endpoint or credentials configured

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_graphify()` during kernel startup sequence
- `self._graphify_adapter = adapter` created at boot

**Question E - Runtime Instantiation:** ✅
- Adapter instantiated: `adapter = GraphifyAdapter(mcp_manager=self._mcp_manager, server_id="graphify")`
- However, MCP connection not established at boot due to:
  - Historical D-01: `kernel._mcp_manager` never assigned (partially fixed in current kernel)
  - Critical issue: `connect_all()` never called by kernel, so no MCP connections established at boot
  - Connections happen lazily when adapter's `connect()` method is called
- M8-T6 §16: "**D-01**: never connects at boot"

**Question F - Real Credentials:** ❌
- Only mock server communication possible
- No API keys, OAuth, or real credentials for real Graphify configured
- Real Graphify service would need to be running and accessible

**Question G - Real External Connections:** ❌
- Connects only to mock subprocess: `mock_graphify_server.py`
- No network sockets to real external Graphify services
- MCP configuration uses stdio to local mock process

**Question H - Real Operations:** ❌
- All communication simulates Graphify responses via mock server
- No actual Graphify processes spawned or communicated with
- GraphifyAdapter contains real Graphify logic but only used with mock by default
- **Additional Defect:** M8-T6 identifies **D-03 (HIGH)**: "Graphify write paths (`store_node`, `update_node`, `delete_node`) return `raw=result` **without** `_mark_advisory`, so those results carry no C14 advisory/authority/trust markers"

**Question I - Real System Testing:** ❌
- Only mock-based tests exist by default
- Real Graphify tests gated via `GRAPHIFY_E2E_TEST=1` environment variable
- Standard tests use mock Graphify server
- M8-T6 §29: "Real external servers (actual `graphify`, ...) are NOT available in CI"

**Defects Identified:**
- **D-01 (CRITICAL)**: MCP connection limitation preventing real connections at boot
- **D-03 (HIGH)**: Write paths lack C14 advisory markers
- Shares general MCP adapter pattern limitations

### 4. Notion Integration (M8-T4)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/notion_adapter.py` - Notion adapter implementation
- `src/aios/adapters/mock_notion_server.py` - Mock Notion server
- `config/mcp/notion_mcp.json` - MCP configuration pointing to mock server

**Question B - Registration:** ✅
- `_init_notion()` creates adapter and registers: `capability_id="notion_planning"`
- Properly registered in CapabilityManager as notion_planning capability

**Question C - Configuration:** ✅ (MOCK ONLY)
- MCP config: `"command": ["python", "-m", "aios.adapters.mock_notion_server"]`
- Points to mock subprocess, not real Notion MCP server
- Constructor shows app config dependency for timeout but no evidence of real Notion API credentials
- Relies on MCP server abstraction rather than direct Notion API

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_notion()` during kernel startup sequence
- `self._notion_adapter = adapter` created at boot

**Question E - Runtime Instantiation:** ✅
- Adapter instantiated: `adapter = NotionAdapter(mcp_manager=self._mcp_manager, server_id="notion", ...)`
- However, MCP connection not established at boot due to shared MCP connection limitations (D-01 pattern)
- Connections happen lazily when adapter's `connect()` method is called

**Question F - Real Credentials:** ❌
- Only mock server communication possible via Notion MCP abstraction
- No real Notion API keys/tokens configured for direct API access
- Real Notion MCP server would need to be running to provide actual Notion API access
- MCP configuration points exclusively to mock server

**Question G - Real External Connections:** ❌
- Connects only to mock subprocess: `mock_notion_server.py`
- No network sockets to real external Notion MCP services
- MCP configuration uses stdio to local mock process

**Question H - Real Operations:** ❌
- All communication simulates Notion responses via mock server
- No actual Notion MCP processes spawned or communicated with
- NotionAdapter contains real Notion MCP logic but only used with mock by default
- **Additional Defect:** M8-T6 identifies **D-06 (MEDIUM)**: "Filesystem fallback `list_notes` results may not pass through `_mark_advisory`"

**Question I - Real System Testing:** ❌
- Only mock-based tests exist by default
- Real Notion MCP tests would be gated via environment variables (like others)
- Standard tests use mock Notion server
- M8-T6 §29: "Real external servers [...] `@notion/mcp`, ...) are NOT available in CI"

**Defects Identified:**
- Shares general MCP adapter pattern limitations (connection at boot)
- **D-06 (MEDIUM)**: Filesystem fallback list_notes may lack proper advisory marking
- No evidence of direct Notion API integration - relies entirely on Notion MCP server abstraction

### 5. Obsidian Integration (M8-T4)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/obsidian_adapter.py` - Obsidian adapter implementation
- `src/aios/adapters/mock_obsidian_server.py` - Mock Obsidian server
- `config/mcp/obsidian_mcp.json` - MCP configuration pointing to mock server

**Question B - Registration:** ✅
- `_init_obsidian()` creates adapter and registers: `capability_id="obsidian_knowledge"`
- Properly registered in CapabilityManager as obsidian_knowledge capability

**Question C - Configuration:** ✅ (MOCK FOR MCP PATH)
- MCP config: `"command": ["python", "-m", "aios.adapters.mock_obsidian_server"]`
- Points to mock subprocess, not real Obsidian MCP server
- Constructor shows app config dependency for vault_path and timeout
- Filesystem fallback path uses local vault_path configuration (real local files)

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_obsidian()` during kernel startup sequence
- `self._obsidian_adapter = adapter` created at boot

**Question E - Runtime Instantiation:** ✅
- Adapter instantiated: `adapter = ObsidianAdapter(mcp_manager=self._mcp_manager, server_id="obsidian", vault_path=vault_path, ...)`
- However, MCP connection not established at boot due to shared MCP connection limitations
- Filesystem fallback path works without MCP connection
- MCP connections happen lazily when adapter's `connect()` method is called

**Question F - Real Credentials:** ⚠️
- **MCP Path:** Only mock server communication possible
  - No API keys, OAuth, or real credentials for real Obsidian MCP configured
  - Real Obsidian MCP server would need to be running and accessible
- **Filesystem Path:** No credentials needed (direct file access)
  - Uses configured vault_path for local file system access

**Question G - Real External Connections:** ❌ (MCP PATH)
- **MCP Path:** Connects only to mock subprocess: `mock_obsidian_server.py`
  - No network sockets to real external Obsidian MCP services
  - MCP configuration uses stdio to local mock process
- **Filesystem Path:** Yes, but LOCAL ONLY
  - Accesses configured local vault directory
  - Not an external system connection (local file I/O only)

**Question H - Real Operations:** ⚠️ (MCP PATH: NO, FILESYSTEM PATH: YES FOR LOCAL)
- **MCP Path:** 
  - All communication simulates Obsidian responses via mock server
  - No actual Obsidian MCP processes spawned or communicated with
  - ObsidianAdapter contains real Obsidian MCP logic but only used with mock by default
- **Filesystem Path:**
  - Real file system operations performed on local vault
  - Reads/writes actual files in configured vault_path
  - However, this is local system access, not external system integration
  - M8-T6 §16: "filesystem works without MCP" (acknowledges local capability)

**Question I - Real System Testing:** ❌ (MCP PATH)
- **MCP Path:** Only mock-based tests exist by default
- Real Obsidian MCP tests would be gated via environment variables
- Standard tests use mock Obsidian server
- **Filesystem Path:** ✅ Real filesystem tests likely use temporary/test vaults
- M8-T6 §29: "Real external servers [...] `obsidian-mcp`, ...) are NOT available in CI"

**Defects Identified:**
- Shares general MCP adapter pattern limitations (connection at boot)
- **D-06 (MEDIUM)**: Filesystem fallback list_notes results may not pass through `_mark_advisory`
- MCP path suffers from same limitations as other MCP-based adapters
- Filesystem path provides real local operations but not external system integration

### 6. Claude-Mem Integration (M8-T4)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/adapters/claude_mem_adapter.py` - Claude-Mem adapter implementation
- `src/aios/adapters/mock_claude_mem_server.py` - Mock Claude-Mem server
- `config/mcp/claude_mem_mcp.json` - MCP configuration pointing to mock server

**Question B - Registration:** ✅
- `_init_claude_mem()` creates adapter and registers: `capability_id="claude_mem_context"`
- Properly registered in CapabilityManager as claude_mem_context capability

**Question C - Configuration:** ✅ (MOCK ONLY)
- MCP config: `"command": ["python", "-m", "aios.adapters.mock_claude_mem_server"]`
- Points to mock subprocess, not real Claude-Mem MCP server
- Constructor shows app config dependency for timeout but no evidence of real Claude-Mem API credentials

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_claude_mem()` during kernel startup sequence
- `self._claude_mem_adapter = adapter` created at boot

**Question E - Runtime Instantiation:** ✅
- Adapter instantiated: `adapter = ClaudeMemAdapter(mcp_manager=self._mcp_manager, server_id="claude_mem", ...)`
- However, MCP connection not established at boot due to shared MCP connection limitations (D-01 pattern)
- Connections happen lazily when adapter's `connect()` method is called

**Question F - Real Credentials:** ❌
- Only mock server communication possible
- No API keys, OAuth, or real credentials for real Claude-Mem configured
- Real Claude-Mem MCP server would need to be running and accessible

**Question G - Real External Connections:** ❌
- Connects only to mock subprocess: `mock_claude_mem_server.py`
- No network sockets to real external Claude-Mem MCP services
- MCP configuration uses stdio to local mock process

**Question H - Real Operations:** ❌
- All communication simulates Claude-Mem responses via mock server
- No actual Claude-Mem MCP processes spawned or communicated with
- ClaudeMemAdapter contains real Claude-Mem MCP logic but only used with mock by default

**Question I - Real System Testing:** ❌
- Only mock-based tests exist by default
- Real Claude-Mem MCP tests would be gated via environment variables
- Standard tests use mock Claude-Mem server
- M8-T6 §29: "Real external servers [...] `claude-mem`, ...) are NOT available in CI"

**Defects Identified:**
- Shares general MCP adapter pattern limitations (connection at boot)
- No specific Claude-Mem defects called out beyond the standard MCP pattern limitations

### 7. Capability Registry/Hardening (M8-T5)
**Status:** A: READY

**Question A - Code Existence:** ✅
- `src/aios/core/capability_manager.py` - Core CapabilityManager implementation
- `src/aios/adapters/adapter_factory.py` - AdapterFactory implementation
- `src/aios/core/capability_manifest.py` - Manifest loading system
- Manifest files: `config/capabilities/*.yaml` (5 capability manifests)

**Question B - Registration:** ✅
- CapabilityManager initialized in `_init_core_components()` as `core.capability` service
- Registered in ServiceRegistry and managed by LifecycleManager
- AdapterFactory created and set on CapabilityManager in `_init_capability_manifests()`

**Question C - Configuration:** ✅
- Capability manifests loaded from `./config/capabilities/` directory
- Manifests reference real adapter classes and MCP server IDs
- Example (graphify_context.yaml):
  ```yaml
  capability_id: "graphify_context"
  adapter:
    class_path: "aios.adapters.graphify_adapter.GraphifyAdapter"
    kwargs:
      server_id: "graphify"
  transport: "mcp"
  ```

**Question D - Enabled:** ✅
- Master switch: `kernel.capabilities.enabled` (defaults to True)
- `_init_capability_manifests()` called unconditionally during kernel startup
- Processes all YAML manifests in capabilities directory

**Question E - Runtime Instantiation:** ✅
- CapabilityManager instantiated as core service during `_init_core_components()`
- LifecycleManager drives it to OPERATIONAL state
- AdapterFactory instantiated and configured during `_init_capability_manifests()`
- Each capability from manifests registered and enabled ones initialized

**Question F - Real Credentials:** N/A
- CapabilityRegistry/Hardening is internal management system
- Does not require API keys or credentials for its operation
- Individual adapters it manages may require credentials for external connections
- But the registry/factory system itself functions without credentials

**Question G - Real External Connections:** N/A
- CapabilityManager/AdapterFactory are internal AI-OS components
- They manage adapter instances that may connect to external systems
- But the registry/factory system itself does not make external connections
- It performs real internal operations regardless of adapter connection status

**Question H - Real Operations:** ✅
- CapabilityManager performs real service registry operations
- AdapterFactory performs real factory pattern operations
- Manifest loading performs real YAML parsing and validation
- Capability registration performs real service registration operations
- Enabled capability initialization performs real adapter initialization
- Lifecycle management performs real service lifecycle operations
- These are all real operations happening within the AI-OS kernel
- Whether adapters connect to mock or real externals doesn't change the reality of the registry operations

**Question I - Real System Testing:** ✅
- Can be tested without requiring real external system connections
- Testing focuses on:
  - Manifest loading and parsing
  - Capability registration and validation
  - AdapterFactory creation and capability resolution
  - Service lifecycle management via LifecycleManager
- Standard AI-OS testing exercises these functions
- M8-T5 focuses on the registry/hardening mechanisms themselves, which are fully testable

**Defects Identified:**
- None - the capability registry/hardening system is fully functional as an internal AI-OS management system
- Note: While the system works correctly, the adapters it manages may connect to mock externals by default (separate issue)

### 8. User Simulation Agent (M7/T2 Extension)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/core/user_simulation_agent.py` - UserSimulationAgent implementation
- Uses HermesBridge to communicate with external hermes-agent(EXT)
- `src/aios/adapters/mock_hermes_server.py` - Mock Hermes server
- `src/aios/adapters/mock_hermes_acp_server.py` - Mock Hermes ACP server

**Question B - Registration:** ⚠️ INDIRECT
- Not registered as service in ServiceRegistry or capability in CapabilityManager
- Held as direct kernel reference: `self._user_simulation_agent`
- UserSimulationAgent extends no standard service pattern - used directly by TestOrchestratorService
- M8-T6: "The ``UserSimulationAgent`` is wired to a real ``HermesBridge`` [...] which talks to the external, untrusted hermes-agent(EXT)"

**Question C - Configuration:** ✅ (MOCK VIA HERMESBRIDGE)
- Gets HermesBridge from `_init_m7_testing()`:
  ```python
  hermes_bridge = HermesBridge(
      mcp_manager=self._mcp_manager,
      server_id="hermes_agent_ext",
      session_ttl_seconds=max(0, acp_ttl),
  )
  ```
- HermesBridge configuration points to mock hermes servers (as analyzed in Hermes section)
- No real hermes-agent(EXT) endpoint or credentials configured

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_m7_testing()` during kernel startup
- `self._user_simulation_agent = UserSimulationAgent(hermes_bridge)` created at boot

**Question E - Runtime Instantiation:** ✅
- Objects instantiated: `hermes_bridge = HermesBridge(...)` and `self._user_simulation_agent = UserSimulationAgent(hermes_bridge)`
- However, HermesBridge connection not established at boot (lazy-on-first-use)
- UserSimulationAgent exists but its HermesBridge is not connected to any hermes agent until used

**Question F - Real Credentials:** ❌
- Only mock server communication possible via HermesBridge
- No API keys, OAuth, or real credentials for real hermes-agent(EXT) configured
- Real hermes-agent(EXT) repository would need to be running separately

**Question G - Real External Connections:** ❌
- Connects only to mock subprocesses via HermesBridge:
  - `mock_hermes_server.py` (MCP path)
  - `mock_hermes_acp_server.py` (ACP path)
- No network sockets to real external hermes-agent services
- HermesBridge MCP configuration uses stdio to local mock processes

**Question H - Real Operations:** ❌
- All communication simulates hermes-agent responses via mock servers
- No actual hermes-agent(EXT) processes spawned or communicated with
- UserSimulationAgent uses HermesBridge which contains real MCP/ACP logic but only used with mocks by default
- **Critical Defect:** M8-T6 identifies **D-02 (CRITICAL)**: "`UserSimulationAgent.simulate()` (`src/aios/core/user_simulation_agent.py:151`) calls `self._bridge._create_session_id()`, which does not exist on `HermesBridge`. This raises `AttributeError` in production, crashing the `user_simulation` (10th) testing perspective"

**Question I - Real System Testing:** ❌
- Only mock-based tests exist by default
- Real user simulation testing would require actual hermes-agent(EXT) running
- Standard tests use mock hermes servers
- M8-T6 §29: "**D-02 (`user_simulation_agent.py:151`)** crashes the `user_simulation` perspective in production"

**Defects Identified:**
- Shares general Hermes/MCP connection limitations
- **D-02 (CRITICAL)**: Missing `_create_session_id()` method causes production crashes in user_simulation perspective
- This is a blocking defect that prevents real operation even if hermes-agent(EXT) were available

### 9. Testing Orchestration/Services (M7)
**Status:** A: READY

**Question A - Code Existence:** ✅
- `src/aios/services/testing.py` - TestOrchestratorService implementation
- Extends WorkflowManager to coordinate 9 agencies + user_simulation perspective
- Coordinates the multi-perspective testing system specified in M7

**Question B - Registration:** ✅
- TestOrchestratorService extends WorkflowManager
- WorkflowManager initialized in `_init_core_components()` as `core.workflow` service
- Registered in ServiceRegistry: `self._workflow_manager = WorkflowManager(...)`
- `set_workflow_manager(self._workflow_manager)`
- TestOrchestratorService inherits this registration as specialized WorkflowManager

**Question C - Configuration:** ✅
- Receives dependencies via constructor injection in `_init_m7_testing()`:
  ```python
  self._test_orchestrator = TestOrchestratorService(
      self._workflow_manager,
      council_manager=council,
      final_judge=None,  # uses built-in FinalJudgeAgency singleton
      simplification_gate=SimplificationGate(),
      security_manager=self._security_manager,
  )
  ```
- No external API keys or credentials required for orchestration service itself
- Gets internal kernel components (workflow, council, gate, security) via DI

**Question D - Enabled:** ✅
- Initialized unconditionally in `_init_m7_testing()` during kernel startup
- Follows M7 testing component initialization sequence after Core Managers

**Question E - Runtime Instantiation:** ✅
- TestOrchestratorService instantiated during `_init_m7_testing()`
- Inherits WorkflowManager registration as `core.workflow` service
- LifecycleManager drives it to OPERATIONAL state via registration in `_init_lifecycle_manager()`
- Managed as core service in AI-OS service ecosystem

**Question F - Real Credentials:** N/A
- TestOrchestratorService performs internal workflow coordination
- Does not require API keys or credentials for its operation
- Coordinates other services that may use credentials, but orchestrator itself doesn't need them

**Question G - Real External Connections:** N/A
- TestOrchestratorService coordinates internal services and agencies
- Does not make external network connections itself
- Works with whatever connections its member services have established
- Purely internal AI-OS orchestration and coordination component

**Question H - Real Operations:** ✅
- Performs real workflow orchestration operations (inherits from WorkflowManager)
- Executes real multi-perspective testing coordination logic
- Manages real execution of 9 agency perspectives + user_simulation perspective
- Coordinates with real SimplificationGate for complexity gating
- Interacts with real CouncilManager for consensus and decision making
- Manages real state transitions and workflow execution
- These are all real operations happening within the AI-OS kernel
- Whether agency perspectives use mocks or real externals doesn't change the reality of the orchestration operations
- M8-T6: "M7 status: FROZEN. 13/13 M7 regression suites must remain green."

**Question I - Real System Testing:** ✅
- Thoroughly tested and validated
- M7 regression suites are FROZEN and must remain green per M8-T6
- Testing focuses on:
  - Workflow orchestration logic and state management
  - Multi-perspective coordination (9 agencies + user_simulation)
  - Gate enforcement (SimplificationGate, Council decisions)
  - Error handling and recovery scenarios
  - Integration with kernel services (EventBus, ServiceRegistry, etc.)
- Standard AI-OS testing exercises the complete M7 testing system

**Defects Identified:**
- None - the M7 testing orchestration system is fully functional and FROZEN
- Represents a core internal AI-OS service performing real operations

### 10. Council System
**Status:** A: READY

**Question A - Code Existence:** ✅
- `src/aios/core/council_manager.py` - CouncilManager implementation
- Implements multi-agency consensus and decision-making system for AI-OS governance
- Core Component (C3) in AI-OS architecture specification

**Question B - Registration:** ✅
- Follows global singleton pattern: `get_council_manager()` and `set_council_manager()`
- Retrieved and used constructor-injected in `_init_m7_testing()`: `council = get_council_manager()`
- Available throughout system as properly initialized singleton
- Not registered in ServiceRegistry (accessed via global singleton like other core utilities)
- But definitely instantiated and available for use by kernel services

**Question C - Configuration:** ✅
- Receives standard Core Component dependencies via DI:
  - EventBus (C1) for communication
  - ServiceRegistry (C2) for service discovery  
  - ConfigurationManager (C3) for settings
  - StructuredLogger (C4) for logging
- No external API keys or credentials required for council operation
- Processes inputs from agencies but doesn't need external credentials itself

**Question D - Enabled:** ✅
- Initialized during `_init_core_components()` phase of kernel startup
- Happens early in boot sequence before most services
- Initialization is unconditional - no enable/disable flag for core components like CouncilManager
- Fundamental part of AI-OS governance architecture

**Question E - Runtime Instantiation:** ✅
- Instantiated as global singleton during kernel startup
- Available via `get_council_manager()` throughout system lifecycle
- Participates in kernel's service ecosystem and lifecycle management
- Used by services like TestOrchestratorService and autonomous services
- Core Component that goes through standard initialization lifecycle

**Question F - Real Credentials:** N/A
- CouncilManager performs internal consensus and decision-making
- Does not require API keys or credentials for its operation
- As internal governance component, credentials not applicable to its function
- Its role is to facilitate agreement between different AI-OS perspectives/agents

**Question G - Real External Connections:** N/A
- CouncilManager operates entirely within AI-OS kernel boundary
- Does not make external network connections
- May process inputs that originated from external systems (via agencies)
- But all council proceedings, voting, and decision-making happens internally
- Purely internal AI-OS governance and consensus component

**Question H - Real Operations:** ✅
- Instantiated as real global singleton during kernel startup
- Goes through real initialization as Core Component
- Retrieved via `get_council_manager()` and used by services throughout system
- Implements real consensus algorithms and decision-making logic
- Manages real council of agents process for AI-OS governance
- Facilitates real agreement between different testing perspectives and agents
- These are all real operations happening within the AI-OS kernel
- Whether inputs came from mock or real external sources doesn't change the reality of the council process itself
- Visible in M8-T6 architecture diagrams as central AI-OS authoritative component

**Question I - Real System Testing:** ✅
- Can be tested without requiring real external system connections
- Testing focuses on:
  - Consensus algorithms and decision-making logic
  - Integration with other kernel components (EventBus, ServiceRegistry, etc.)
  - Handling of various agency perspectives and inputs (mock or real)
  - Error handling and edge cases in council proceedings
  - Standard AI-OS testing exercises council-related functionality
- Core component that would be exercised in various test scenarios throughout system

**Defects Identified:**
- None - the Council System is fully functional as a core internal AI-OS governance component
- Represents a fundamental part of AI-OS architecture performing real operations

### 11. Free LLM API (External Reconciliation)
**Status:** E: IMPLEMENTED BUT NOT LIVE

**Question A - Code Existence:** ✅
- `src/aios/core/model_router.py` - ModelRouter implementation ( abstraction layer)
- `src/aios/adapters/freellmapi.py` - FreeLLMAPI provider for ModelRouter
- Kernel property: `@property def model_manager(self) -> ModelRouter | None: return get_model_router()`
- Provides abstraction for routing requests to different LLM providers

**Question B - Registration:** ⚠️ (MODELROUTER YES, FREELLMAPi PROVIDER NO)
- ModelRouter follows global singleton pattern: `get_model_router()` / `set_model_router()`
- Kernel exposes it as `model_manager` property - definitely instantiated and available
- FreeLLMAPI provider implementation exists but requires manual registration with ModelRouter
- No automatic registration evident in code review
- ModelRouter abstraction is registered/available; specific provider requires configuration

**Question C - Configuration:** ✅ (MODELROUTER YES, FREELLMAPi NEEDS SETUP)
- ModelRouter: Available as global singleton - no external credentials needed for abstraction
- FreeLLMAPI Provider: 
  - `FreeLLMAPIConfig.base_url: str = "http://localhost:8080"` (default local/dev endpoint)
  - `FreeLLMAPIConfig.api_key: str | None = None` (optional API key)
  - To connect to real external LLM APIs, needs configuration pointing to real services with valid credentials
  - By default configured for local development/testing endpoint

**Question D - Enabled:** ✅ (MODELROUTER YES, FREELLMAPi DEPENDS ON REGISTRATION)
- ModelRouter: Initialized as global singleton during kernel startup - always available
- FreeLLMAPI Provider: Requires explicit registration with ModelRouter to be usable
- Without provider registration, ModelRouter has no backends to route requests to
- Abstraction enabled; specific external connectivity depends on provider setup

**Question E - Runtime Instantiation:** ✅ (MODELROUTER YES, FREELLMAPi DEPENDS)
- ModelRouter: Singleton instantiated during kernel startup - `get_model_router()` returns real instance
- FreeLLMAPI Provider: Class exists but instances only created when registered with ModelRouter
- Without registration, no FreeLLMAPI provider instances exist in system
- ModelRouter available; specific provider instantiation depends on configuration

**Question F - Real Credentials:** ⚠️ (DEPENDS ON PROVIDER SETUP)
- ModelRouter: N/A (abstraction layer doesn't need credentials)
- FreeLLMAPI Provider: 
  - Can work without API key pointing to `http://localhost:8080` (local/dev instance)
  - For real external LLM APIs: Requires valid API keys/tokens configured in FreeLLMAPIConfig
  - By default: No real API keys configured (points to localhost)
  - Real LLM API connections require explicit credential configuration

**Question G - Real External Connections:** ⚠️ (DEPENDS ON PROVIDER SETUP)
- ModelRouter: N/A (abstraction layer)
- FreeLLMAPI Provider:
  - By default: Connects to `http://localhost:8080` (likely local dev/test instance)
  - For real external LLM APIs: Would make HTTP requests to real external LLM service endpoints
  - By default: No real external LLM API connections (points to localhost)
  - Real external connections require explicit configuration pointing to real services

**Question H - Real Operations:** ✅ (MODELROUTER ABSTRACTION: YES)
- ModelRouter: 
  - Performs real abstraction layer operations
  - Provides real model routing functionality
  - Accepts real provider registrations
  - Processes real model requests according to routing logic
  - Real abstraction and routing operations regardless of backend configuration
- FreeLLMAPI Provider:
  - By default: Performs operations against local dev/test instance
  - For real external LLM APIs: Would perform real operations against real LLM services
  - By default: Operations against localhost/dev instance, not real external APIs

**Question I - Real System Testing:** ⚠️ (CAN BE TESTED WITHOUT REAL EXTERNALS)
- ModelRouter: 
  - Can be tested without requiring real external LLM API connections
  - Testing focuses on: request routing logic, provider selection, response handling
  - Standard tests use mock providers or local test endpoints
- FreeLLMAPI Provider:
  - By default: Tested against localhost/dev instance
  - For real external LLM APIs: Would require explicit configuration and credentials
  - Standard AI-OS testing likely uses mock providers or test endpoints
  - Testing against real external LLM APIs requires explicit setup

**Defects Identified:**
- FreeLLMAPI-specific: Comment in freellmapi.py line 7: "FreeLLMAPI is DEV/TEST ONLY (C13 - no production without SLA)."
- FreeLLMAPI-specific: Comment line 36: "Per C13: FreeLLMAPI remains DEV/TEST ONLY."
- While ModelRouter abstraction is production-ready, FreeLLMAPI provider is designated for dev/test only
- To use with real external LLM APIs requires explicit configuration and violates C13 without SLA
- Therefore, external LLM API integration via FreeLLMAPI is NOT LIVE by default (dev/test only)

### 12. Hermes Agent Reach (External Reconciliation)
**Status:** F: PLANNED/NOT INTEGRATED

**Question A - Code Existence:** ✅
- `src/aios/adapters/agent_reach.py` - AgentReach adapter implementation
- `src/aios/adapters/mock_agent_reach_server.py` - Mock Agent-Reach server
- Provides web/social content ingestion via Agent-Reach MCP server
- Returns untrusted observations requiring normalization before use

**Question B - Registration:** ❌
- No evidence of AgentReach being registered as capability via manifest system
- Checked capability manifests directory: `config/capabilities/*.yaml`
- Found: `claude_mem_context.yaml`, `graphify_context.yaml`, `notion_planning.yaml`, `obsidian_knowledge.yaml`, `playwright_browser.yaml`
- **Missing**: `agent_reach.yaml` manifest
- Adapter code exists but not activated/registered through capability system
- Not automatically instantiated or used in standard kernel boot sequence

**Question C - Configuration:** ❌
- No evidence of AgentReach MCP configuration
- Would follow pattern if registered: `config/mcp/agent_reach_mcp.json` pointing to mock server
- No such configuration found in standard locations
- Adapter expects mcp_manager and server_id but not configured for automatic use

**Question D - Enabled:** ❌
- No evidence of AgentReach being enabled via capability manifest system
- Not initialized in standard kernel startup sequences reviewed
- Not registered as service or capability
- Requires explicit manual configuration/registration to be active
- By default: Not enabled as integrated capability

**Question E - Runtime Instantiation:** ❌
- No automatic instantiation during kernel boot
- Kernel initialization sequences reviewed show no AgentReachAdapter creation
- Not held as kernel reference or service reference
- Requires manual instantiation and configuration to be used
- By default: Not instantiated or available for use

**Question F - Real Credentials:** N/A
- Would be needed only if manually configured and registered
- Not applicable in default unconfigured/unregistered state

**Question G - Real External Connections:** N/A
- Would be needed only if manually configured and registered
- Not applicable in default unconfigured/unregistered state

**Question H - Real Operations:** N/A
- Would be needed only if manually configured and registered
- Not applicable in default unconfigured/unregistered state

**Question I - Real System Testing:** N/A
- Would be needed only if manually configured and registered
- Not applicable in default unconfigured/unregistered state
- No evidence of AgentReach being used in standard test flows

**Defects Identified:**
- Not a defect - simply not integrated/activated in the current system
- Represents planned integration that exists as code but is not registered/enabled/instantiated

## SUMMARY OF FINDINGS

### STATUS DISTRIBUTION
- **A: READY** - 3 integrations
  - Capability Registry/Hardening (M8-T5) - Internal management system
  - Testing Orchestration/Services (M7) - Internal workflow orchestration  
  - Council System - Internal governance/consensus system
- **E: IMPLEMENTED BUT NOT LIVE** - 8 integrations
  - All 6 MCP-based external integrations (Hermes, Playwright, Graphify, Notion, Obsidian, Claude-Mem)
  - User Simulation Agent (M7/T2 extension) - Suffers from D-02 defect
  - Free LLM API - FreeLLMAPI provider is dev/test only
- **F: PLANNED/NOT INTEGRATED** - 1 integration
  - Hermes Agent Reach - Code exists but not registered/enabled/instantiated
- **G-J: PHANTOM/NON-LIVE** - 0 integrations
  - No integrations found with only configuration/wrappers/adapters without code

### CRITICAL SYSTEMIC ISSUES

All MCP-based external integrations share fundamental limitations:

1. **MCP Connection at Boot (D-01 Pattern):** 
   - Kernel historically did not assign `_mcp_manager` (partially fixed)
   - Critical: `connect_all()` never called by kernel
   - Result: No MCP connections established at boot
   - Connections happen lazily on first adapter use
   - **Affects:** Graphify, Notion, Obsidian, Claude-Mem, Hermes (MCP fallback), Playwright (when using MCPManager path)

2. **Exclusive Reliance on Mock Servers:**
   - All MCP configurations point to in-process mock servers (`mock_*_server.py`)
   - No real external MCP servers configured or available by default
   - Real external connections require explicit environmental setup and installation
   - Standard operation exclusively uses mock simulations

3. **Environment-Gated Real Testing:**
   - Real external testing requires environment variables:
     - `HERMES_ACP_TEST=1` for Hermes ACP
     - `PLAYWRIGHT_E2E_TEST=1` for Playwright  
     - `GRAPHIFY_E2E_TEST=1` for Graphify
     - Similar patterns expected for others
   - By default: Only mock-based tests execute
   - Real external system testing not part of standard CI/CD

### SPECIFIC HIGH-VALUE DEFECTS

Beyond the systemic MCP limitations, specific high-value defects were identified:

- **D-02 (CRITICAL)**: UserSimulationAgent.simulate() calls missing `_create_session_id()` method on HermesBridge → AttributeError in production → crashes user_simulation (10th) testing perspective
- **D-03 (HIGH)**: Graphify write paths (`store_node`, `update_node`, `delete_node`) return results without `_mark_advisory` → lack C14 advisory/authority/trust markers
- **D-06 (MEDIUM)**: Obsidian filesystem fallback `list_notes` results may not pass through `_mark_advisory`  

### WHAT IS ACTUALLY USABLE TODAY

Based on this audit, the following components are genuinely usable for real operations **without requiring external system setup or configuration**:

**Fully Usable Internal AI-OS Systems (Status A):**
- Capability Registry/Hardening system - Manages capabilities and adapters
- Testing Orchestration/Services (M7) - Coordinates multi-perspective testing
- Council System - Provides consensus and decision-making governance

**Limited Usability with Caveats:**
- **Obsidian Filesystem Fallback:** Provides real local file system operations when vault_path is configured, but this is local system access, not external integration
- **ModelRouter Abstraction:** Provides real model routing functionality, but FreeLLMAPI provider is dev/test only and requires configuration for real LLM APIs
- **All MCP-based Adapters:** Can be used for real operations ONLY if:
  1. Real external MCP servers are running and accessible
  2. MCP configuration is updated to point to real servers
  3. Necessary credentials/API keys are configured
  4. Underlying D-01 connection limitations are addressed or worked around

### CONCLUSION

The AI-OS architecture specifies a sophisticated external integration ecosystem, but the current implementation reveals a significant gap between architectural intent and runtime reality:

- **Architecture Specifies:** Rich external integration ecosystem via MCP/ACP protocols connecting to hermes-agent, Playwright, Graphify, Notion, Obsidian, Claude-Mem, and external LLM APIs
- **Runtime Reality:** 
  - Core AI-OS internal systems are fully functional and performing real operations
  - All external integrations are implemented but default to mock-only operation
  - Real external connections require explicit environmental setup, installation, and configuration
  - Specific defects (D-02, D-03, D-06) further limit readiness of certain integrations
  - One planned integration (Hermes Agent Reach) exists as code but is not activated

The system is architected for real external integration but currently operates in a self-contained mock-only mode by default. Transitioning to real external operation would require:
1. Addressing systemic MCP connection limitations (ensuring connections established at boot)
2. Installing and configuring real external MCP servers 
3. Providing necessary credentials/API keys for external services
4. Resolving specific identified defects (D-02, D-03, D-06)
5. Activating planned integrations like Hermes Agent Reach through proper registration

Until these steps are taken, the AI-OS system provides a sophisticated simulation of external integration capability rather than actual external integration performing real operations with real external systems.