"""
Terminal 2 — PHASE 2 configuration framework verification.

Proves the MOCK/REAL distinction and fail-closed semantics:
- default mode is mock
- a `mode: real` integration is still blocked unless the env gate + user
  resource are present (fail-closed)
- assert_real_allowed raises when not permitted, passes when permitted
- load_integrations_config honors config/integrations.yaml
- MCPManager.connect blocks an ungated REAL server before connecting
"""

from __future__ import annotations

import asyncio

import pytest

from aios.integrations import (
    IntegrationConfig,
    IntegrationConfigRegistry,
    IntegrationMode,
    REAL_OPERATION_ENV,
    assert_real_allowed,
    load_integrations_config,
)


def test_default_mode_is_mock():
    reg = IntegrationConfigRegistry()
    reg.add(IntegrationConfig(name="x"))
    assert reg.resolve_mode("x") == IntegrationMode.MOCK
    assert reg.real_allowed("x") is False


def test_unknown_integration_fail_closed():
    reg = IntegrationConfigRegistry()
    # No entry at all -> fail-closed mock.
    assert reg.resolve_mode("never_defined") == IntegrationMode.MOCK
    assert reg.real_allowed("never_defined") is False


def test_real_blocked_without_env_gate():
    reg = IntegrationConfigRegistry()
    reg.add(IntegrationConfig(name="obsidian", mode=IntegrationMode.REAL,
                              user_resource_present=True, real_gated=True))
    # Env gate closed by default.
    import os
    os.environ.pop(REAL_OPERATION_ENV, None)
    assert reg.real_allowed("obsidian") is False
    with pytest.raises(RuntimeError):
        assert_real_allowed(reg, "obsidian")


def test_real_blocked_without_user_resource():
    reg = IntegrationConfigRegistry()
    reg.add(IntegrationConfig(name="graphify", mode=IntegrationMode.REAL,
                              user_resource_present=False, real_gated=False))
    # Even ungated + mode real, missing user resource blocks (fail-closed).
    assert reg.real_allowed("graphify") is False
    with pytest.raises(RuntimeError):
        assert_real_allowed(reg, "graphify")


def test_real_allowed_with_gate_and_resource(monkeypatch):
    reg = IntegrationConfigRegistry()
    reg.add(IntegrationConfig(name="obsidian", mode=IntegrationMode.REAL,
                              user_resource_present=True, real_gated=True))
    monkeypatch.setenv(REAL_OPERATION_ENV, "1")
    assert reg.real_allowed("obsidian") is True
    # Should NOT raise.
    assert_real_allowed(reg, "obsidian")


def test_load_integrations_config_defaults_mock():
    reg = load_integrations_config()
    # Canonical integrations seeded; defaults are mock + not real-allowed.
    for name in ("hermes_agent_acp", "playwright_mcp", "obsidian", "graphify",
                 "claude_mem", "notion", "agent_reach", "freellmapi"):
        assert reg.resolve_mode(name) == IntegrationMode.MOCK, name
        assert reg.real_allowed(name) is False, name


def test_status_label_describes_block():
    cfg = IntegrationConfig(name="notion", mode=IntegrationMode.REAL,
                            user_resource_present=False)
    assert "BLOCKED" in cfg.status_label()
    assert "user resource" in cfg.status_label().lower()


def test_mcp_connect_blocks_ungated_real_server(monkeypatch):
    """MCPManager.connect must refuse a REAL server lacking env gate (fail-closed)."""
    from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
    from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton

    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    mgr = MCPManager.__new__(MCPManager)
    mgr._config_dir = None  # type: ignore[assignment]
    mgr._servers = {}
    mgr._status = {}
    mgr._processes = {}
    mgr._tools_cache = {}
    mgr._event_bus = bus
    mgr._identity = None  # type: ignore[assignment]

    # A server whose metadata declares mode=real but the framework says mock.
    cfg = MCPServerConfig(
        server_id="obsidian",
        name="Obsidian",
        transport=MCPTransport.STDIO,
        command=["python", "-m", "aios.adapters.mock_obsidian_server"],
        metadata={"integration_mode": "real"},
    )
    mgr._servers["obsidian"] = cfg
    from aios.core.mcp_manager import MCPServerStatus

    mgr._status["obsidian"] = MCPServerStatus(server_id="obsidian", transport=MCPTransport.STDIO)
    from aios.core.mcp_manager import MCPTransport as _T  # noqa: F401

    # No env gate set -> framework blocks before any real connection attempt.
    import os
    os.environ.pop(REAL_OPERATION_ENV, None)
    connected = asyncio.get_event_loop().run_until_complete(mgr.connect("obsidian"))
    assert connected is False
    reset_event_bus_singleton()
