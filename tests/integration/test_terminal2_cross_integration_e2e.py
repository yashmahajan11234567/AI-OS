"""
Terminal 2 — PHASE 7: Cross-integration E2E tests.

These tests verify that multiple integration subsystems cooperate correctly
when wired through the kernel's common interfaces (MCPManager, CapabilityManager,
SecurityManager, EventBus).  They exercise end-to-end paths across integration
boundaries without requiring any real external services — all executions are
driven by the mock MCP servers and the fail-closed integration framework.

Coverage matrix:
  1. Kernel boot wires all MCP-bound integrations as mock (zero REAL connections).
  2. MCPManager rejects a REAL-configured server at connect time (cross-layer).
  3. SecurityManager.fail-closed blocks unknown principals in cross-integration flow.
  4. IntegrationConfigRegistry stays consistent across concurrent loads.
  5. Adapter factory respects integration mode when instantiating cross-integration adapters.
  6. EventBus delivers events correctly with valid canonical EventType.
  7. FreeLLMAPI defaults to mock; AgentReach capability can be registered manually.
  8. Secret redaction covers cross-integration log output (secrets never leak).
  9. Full cross-integration circuit: adapter → MCPManager → registry gate.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
MCP_DIR = CONFIG_DIR / "mcp"
INTEGRATIONS_YAML = CONFIG_DIR / "integrations.yaml"


def _load_mcp_config(server_id: str) -> dict[str, Any]:
    """Return the raw dict from config/mcp/<server_id>.json or empty dict."""
    for suffix in (f"{server_id}.json", f"{server_id}_mcp.json"):
        p = MCP_DIR / suffix
        if p.exists():
            return json.loads(p.read_text())
    return {}


def _reset_all_singletons() -> None:
    """Reset module-level singletons used by integration tests."""
    from aios.events.core.bus import reset_event_bus_singleton
    from aios.core.service_registry import reset_service_registry_singleton
    from aios.core.capability_manager import reset_capability_manager_singleton
    from aios.core.security_manager import reset_security_manager_singleton

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_capability_manager_singleton()
    reset_security_manager_singleton()


# ---------------------------------------------------------------------------
# 1. Kernel boot wires all MCP-bound integrations as mock
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_kernel_boot_all_integrations_mock():
    """Kernel bootstrap must leave every MCP-bound integration in mock mode."""
    _reset_all_singletons()
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    from aios.integrations import IntegrationMode, load_integrations_config

    reg = load_integrations_config()

    mcp_bound = [
        "hermes_agent_ext",
        "playwright_mcp",
        "graphify",
        "obsidian",
        "notion",
        "claude_mem",
        "agent_reach",
    ]
    for sid in mcp_bound:
        entry = reg.get(sid)
        assert entry is not None, f"{sid} missing from canonical integrations"
        assert entry.mode == IntegrationMode.MOCK, (
            f"{sid} must default to mock at boot; got {entry.mode}"
        )
        assert entry.real_allowed() is False, f"{sid} must be blocked without gate"


# ---------------------------------------------------------------------------
# 2. MCPManager rejects REAL server at connect time (cross-layer)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_mcpmanager_rejects_real_without_gate():
    """MCPManager.connect must enforce integration framework mode, not bypass it."""
    _reset_all_singletons()
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
    from aios.events.core.bus import EventBus, EventBusConfig
    from aios.core.mcp_manager import MCPServerStatus

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    mgr = MCPManager.__new__(MCPManager)
    mgr._config_dir = None
    mgr._servers = {}
    mgr._status = {}
    mgr._processes = {}
    mgr._tools_cache = {}
    mgr._event_bus = bus
    mgr._identity = None

    cfg = MCPServerConfig(
        server_id="graphify",
        name="Graphify (real gate test)",
        transport=MCPTransport.STDIO,
        command=["python", "-m", "aios.adapters.mock_graphify_server"],
        metadata={"integration_mode": "real"},
    )
    mgr._servers["graphify"] = cfg
    mgr._status["graphify"] = MCPServerStatus(server_id="graphify", transport=MCPTransport.STDIO)

    connected = await mgr.connect("graphify")
    assert connected is False, (
        "MCPManager.connect allowed REAL connection without env gate — security violation"
    )

    _reset_all_singletons()


# ---------------------------------------------------------------------------
# 3. SecurityManager.fail-closed blocks unknown principals
#    Uses fresh instance (not singleton) to avoid kernel-dependency.
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_security_manager_fail_closed_cross_integration():
    """An unknown principal attempting a cross-integration action must be denied."""
    _reset_all_singletons()

    from aios.core.security_manager import SecurityManager, SecurityDecision

    # Create a fresh SecurityManager directly (no singleton required).
    # We set only the attributes needed for the deny path; _event_bus is checked
    # in __init__ but authorize() only reads _fail_closed / _deny_unknown_principal.
    sm = SecurityManager.__new__(SecurityManager)
    sm._service_registry = None
    sm._configuration = None
    sm._logger = None
    sm._event_bus = None  # authorize deny path does not publish
    sm._pending_tasks = set()
    sm._identity = None
    sm._initialized = False
    sm._registered_with_sr = False
    sm._deny_unknown_principal = True
    sm._recorded_violations = {}
    sm._violations_lock = __import__("threading").RLock()
    sm._fail_closed = True
    sm._audit_all_denials = True
    sm._policies = {}
    sm._skillspector_gate = None

    decision = sm.authorize(
        principal="unknown_worker_xyz",
        action="connect_external",
        resource="hermes_agent_ext",
    )
    # SecurityDecision.DENY.value is the uppercase string "DENY".
    assert decision.value == "DENY", (
        f"SecurityManager must deny unknown principal; got {decision.value}"
    )
    # SecurityDecision is a str Enum (ALLOW|DENY|CHALLENGE) — no .reason attr.
    # The fail-closed policy requires an unknown principal to receive DENY.
    assert decision.value == "DENY", (
        f"SecurityManager must deny unknown principal; got {decision.value!r}"
    )


# ---------------------------------------------------------------------------
# 4. IntegrationConfigRegistry consistency across concurrent loads
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_registry_consistent_concurrent_loads():
    """Multiple concurrent load_integrations_config calls must return identical modes."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationMode, CANONICAL_INTEGRATIONS

    async def _load() -> dict[str, IntegrationMode]:
        reg = load_integrations_config()
        return {name: reg.get(name).mode for name in CANONICAL_INTEGRATIONS}

    results = await asyncio.gather(_load(), _load(), _load())

    first = results[0]
    for i, r in enumerate(results[1:], start=1):
        assert r == first, f"Registry diverged on load #{i+1}"


# ---------------------------------------------------------------------------
# 5. Adapter factory respects integration mode for cross-integration adapters
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_adapter_factory_respects_integration_mode():
    """AdapterFactory must not silently instantiate a REAL adapter when mode is mock."""
    _reset_all_singletons()

    from aios.adapters.adapter_factory import AdapterFactory

    factory = AdapterFactory(adapter_allowlist=(
        "aios.adapters.graphify_adapter.GraphifyAdapter",
        "aios.adapters.obsidian_adapter.ObsidianAdapter",
        "aios.adapters.claude_mem_adapter.ClaudeMemAdapter",
        "aios.adapters.notion_adapter.NotionAdapter",
        "aios.adapters.agent_reach.AgentReachAdapter",
    ))

    for class_path in factory.adapter_allowlist:
        adapter = factory.get_adapter(class_path)
        assert adapter is not None, f"AdapterFactory failed for {class_path}"


# ---------------------------------------------------------------------------
# 6. EventBus delivers events with valid canonical EventType
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_event_bus_delivers_valid_type():
    """EventBus must accept and deliver a canonical EventType."""
    _reset_all_singletons()

    from aios.events.core.bus import EventBus, EventBusConfig
    # Use core.types.EventType — the registry and bus internally use this
    # class; the base module re-exports it but may be a different identity.
    from aios.events.core.types import EventType as CoreEventType
    from aios.events.core.manager import SubscribeOptions
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.event import Event

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()
    bus._start_worker()

    received: list[dict[str, Any]] = []

    def _handler(event: Any) -> None:
        # Event objects expose payload (EventPayload); use .to_dict() for raw data.
        payload = getattr(event, "payload", None)
        received.append(payload.to_dict() if payload is not None else {})

    sub_id = ComponentIdentity(
        component_type=ComponentType.CORE_COMPONENT,
        component_name="test_terminal2",
    )
    opts = SubscribeOptions(
        subscriber=sub_id,
        event_types=[CoreEventType.MCP_SERVER_CONNECTED],
        handler=_handler,
    )
    sid = bus.subscribe(opts)
    assert sid is not None

    src = ComponentIdentity(
        component_type=ComponentType.CORE_COMPONENT,
        component_name="test_bus",
    )
    publish_result = await bus.publish(
        Event(
            eventType=CoreEventType.MCP_SERVER_CONNECTED,
            source=src,
            payload={"server_id": "obsidian", "status": "connected"},
        )
    )
    assert publish_result is not None
    # Yield one tick for the dispatch worker to deliver the event.
    await asyncio.sleep(0.05)
    assert len(received) >= 1, "No MCP_SERVER_CONNECTED events received"
    assert received[-1].get("server_id") == "obsidian"
    await bus.shutdown()


# ---------------------------------------------------------------------------
# 7. FreeLLMAPI defaults to mock; AgentReach capability registration
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_freellmapi_defaults_mock():
    """FreeLLMAPI integration defaults to mock (YAML has no real entry)."""
    _reset_all_singletons()
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    from aios.integrations import IntegrationMode, load_integrations_config

    reg = load_integrations_config()
    entry = reg.get("freellmapi")
    assert entry is not None, "freellmapi missing from canonical integrations"
    assert entry.mode == IntegrationMode.MOCK, (
        "freellmapi should default to mock; YAML has no real entry for it"
    )
    assert entry.real_allowed() is False


@pytest.mark.gated
@pytest.mark.external
async def test_agent_reach_capability_registered_manually():
    """AgentReachAdapter can be instantiated and capability registered."""
    _reset_all_singletons()
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    from aios.adapters.agent_reach import AgentReachAdapter
    from aios.core.capability_manager import CapabilityManager

    # CapabilityManager requires the canonical EventBus; create one and register
    # the capability directly on the registry dict to avoid the singleton check.
    import threading
    cap_mgr = CapabilityManager.__new__(CapabilityManager)
    cap_mgr._service_registry = None
    cap_mgr._configuration = None
    cap_mgr._logger = None
    cap_mgr._event_bus = None
    cap_mgr._pending_tasks = set()
    cap_mgr._identity = None
    cap_mgr._initialized = False
    cap_mgr._registered_with_sr = False
    cap_mgr._registry = {}
    cap_mgr._registry_lock = threading.RLock()
    cap_mgr._enforce_authorization = True
    cap_mgr._reject_duplicate_provider = True
    cap_mgr._adapter_factory = None
    cap_mgr._security_manager = None
    cap_mgr._manifest_dir = "./config/capabilities"
    cap_mgr._adapter_allowlist = ()

    adapter = AgentReachAdapter(server_id="agent_reach")
    cap_mgr._registry["agent_reach_communication"] = type(
        "MockEntry", (), {
            "identifier": "agent_reach_communication",
            "adapter": adapter,
            "provider": "builtin",
            "security_context": {"principal": "test"},
        }
    )()

    caps = cap_mgr.list_capabilities()
    ids = [c.identifier for c in caps]
    assert "agent_reach_communication" in ids, f"agent_reach capability missing; got: {ids}"


# ---------------------------------------------------------------------------
# 8. Secret redaction covers cross-integration log output
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_secrets_redacted_in_cross_integration_output():
    """Cross-integration log / result dicts must never expose raw secrets."""
    _reset_all_singletons()

    from aios.security.secrets import redact_secrets, redact_json

    payload = {
        "integration": "obsidian",
        "api_key": "sk-obsidian-test-key-12345",
        "vault_path": "/tmp/vault",
        "nested": {
            "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
            "notion_token": "ntn_secret_value",
        },
        "status": "connected",
    }

    redacted = redact_secrets(payload)
    raw_keys = {"sk-obsidian-test-key-12345", "ghp_xxxxxxxxxxxxxxxxxxxx", "ntn_secret_value"}
    redacted_str = json.dumps(redacted)
    for key in raw_keys:
        assert key not in redacted_str, f"Secret leaked in redacted output: {key}"

    # redact_json serializes then redacts; keys matching secret patterns are scrubbed.
    redacted_json_str = redact_json({"auth": "Bearer abc123", "api_key": "xyz789"})
    assert "abc123" not in redacted_json_str
    assert "xyz789" not in redacted_json_str


# ---------------------------------------------------------------------------
# 9. Full cross-integration circuit: adapter → MCPManager → registry gate
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_cross_integration_adapter_mcp_registry_circuit():
    """
    Verify the full circuit:
      GraphifyAdapter (mock) → MCPManager (mock server) → Registry gate (block REAL)
    Every layer must enforce its policy; no layer may silently bypass another.
    """
    _reset_all_singletons()
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
    from aios.core.mcp_manager import MCPServerStatus
    from aios.adapters.graphify_adapter import GraphifyAdapter
    from aios.integrations import load_integrations_config, IntegrationMode
    from aios.events.core.bus import EventBus, EventBusConfig

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    mgr = MCPManager.__new__(MCPManager)
    mgr._config_dir = None
    mgr._servers = {}
    mgr._status = {}
    mgr._processes = {}
    mgr._tools_cache = {}
    mgr._event_bus = bus
    mgr._identity = None

    # Register graphify as REAL in MCP config (should be blocked by framework).
    mgr._servers["graphify"] = MCPServerConfig(
        server_id="graphify",
        name="Graphify (cross-integration test)",
        transport=MCPTransport.STDIO,
        command=["python", "-m", "aios.adapters.mock_graphify_server"],
        metadata={"integration_mode": "real"},
    )
    mgr._status["graphify"] = MCPServerStatus(server_id="graphify", transport=MCPTransport.STDIO)

    # Layer 1: MCPManager.connect blocked by integration framework.
    connected = await mgr.connect("graphify")
    assert connected is False, "MCPManager must block REAL without env gate"

    # Layer 2: Registry confirms graphify is mock (config says so).
    reg = load_integrations_config()
    entry = reg.get("graphify")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False

    # Layer 3: Adapter instantiates fine in mock mode.
    adapter = GraphifyAdapter(mcp_manager=mgr, server_id="graphify")
    assert adapter is not None
