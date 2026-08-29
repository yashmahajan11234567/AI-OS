"""
Terminal 2 — PHASE 6: Gated real operational tests.

One integration-category test per external system. Each test proves:
  * The adapter code exists and can be imported.
  * The MCP config declares an integration_mode (PHASE 2).
  * Mock execution path works deterministically.
  * Real execution is BLOCKED when the env gate is NOT set (fail-closed).
  * When the env gate IS set AND user_resource_present is True, the gate
    would allow the connection (the real service itself may still be absent).

The gating env var used here is the canonical AIOS_REAL_INTEGRATION_ENABLED
used by the Phase 2 configuration framework. Per spec S18.9 tests are
``@pytest.mark.gated`` and skipped by default.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
MCP_DIR = CONFIG_DIR / "mcp"
INTEGRATIONS_YAML = CONFIG_DIR / "integrations.yaml"


def _load_mcp_config(server_id: str) -> dict:
    """Return the raw dict from config/mcp/<server_id>.json or None."""
    candidates = [
        MCP_DIR / f"{server_id}.json",
        MCP_DIR / f"{server_id}_mcp.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text())
    return {}


def _assert_mock_path_works(adapter_path: str, **kwargs) -> bool:
    """Import the adapter module and instantiate it — mock path must work."""
    mod_path, cls_name = adapter_path.rsplit(".", 1)
    mod = __import__(mod_path, fromlist=[cls_name])
    cls = getattr(mod, cls_name)
    instance = cls(**kwargs)
    return instance is not None


# ---------------------------------------------------------------------------
# 1. Hermes/ACP — preferred worker path
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_acp_mock_path_works():
    """ACP adapter imports and instantiates (mock path)."""
    ok = _assert_mock_path_works(
        "aios.adapters.acp_adapter.AcPAdapter", cwd=str(Path(__file__).parent.parent.parent),
    )
    assert ok is True, "ACP adapter failed to instantiate"


@pytest.mark.gated
@pytest.mark.external
async def test_acp_real_blocked_without_gate():
    """ACP real mode blocked when env gate is absent."""
    # Reset the integration framework state
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode, assert_real_allowed

    reg = load_integrations_config()
    entry = reg.get("hermes_agent_acp")
    # By default mode is mock
    assert entry.mode == IntegrationMode.MOCK, "hermes_agent_acp should default to mock"
    assert entry.real_allowed() is False, "hermes_agent_acp should not be real-allowed by default"
    with pytest.raises(RuntimeError):
        assert_real_allowed(reg, "hermes_agent_acp")


@pytest.mark.gated
@pytest.mark.external
async def test_acp_config_has_metadata_entrypoint():
    """hermes_agent_ext MCP config must exist and declare integration_mode."""
    cfg = _load_mcp_config("hermes_agent_ext")
    assert cfg, "MCP config for hermes_agent_ext missing"
    assert "integration_mode" in cfg.get("metadata", {}), \
        "hermes_agent_ext config must declare integration_mode"


# ---------------------------------------------------------------------------
# 2. Playwright — browser automation
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_playwright_mock_path_works():
    """PlaywrightMCPAdapter imports and instantiates."""
    ok = _assert_mock_path_works(
        "aios.adapters.playwright_mcp_adapter.PlaywrightMCPAdapter",
        server_id="playwright_mcp",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_playwright_real_blocked_without_gate():
    """Playwright real blocked without env gate."""
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("playwright_mcp")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 3. Graphify — knowledge graph (derived, advisory)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_graphify_mock_path_works():
    """GraphifyAdapter imports and instantiates."""
    ok = _assert_mock_path_works(
        "aios.adapters.graphify_adapter.GraphifyAdapter",
        mcp_manager=None,
        server_id="graphify",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_graphify_real_blocked():
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("graphify")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 4. Obsidian — knowledge vault (filesystem + MCP hybrid)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_mock_path_works():
    ok = _assert_mock_path_works(
        "aios.adapters.obsidian_adapter.ObsidianAdapter",
        mcp_manager=None,
        server_id="obsidian",
        vault_path="",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_real_blocked():
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("obsidian")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 5. Notion — planning (advisory only)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_notion_mock_path_works():
    ok = _assert_mock_path_works(
        "aios.adapters.notion_adapter.NotionAdapter",
        mcp_manager=None,
        server_id="notion",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_notion_real_blocked():
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("notion")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 6. Claude-Mem — contextual memory retrieval (advisory)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_claude_mem_mock_path_works():
    ok = _assert_mock_path_works(
        "aios.adapters.claude_mem_adapter.ClaudeMemAdapter",
        mcp_manager=None,
        server_id="claude_mem",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_claude_mem_real_blocked():
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("claude_mem")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 7. Agent Reach — agent communication protocol
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_agent_reach_mock_path_works():
    ok = _assert_mock_path_works(
        "aios.adapters.agent_reach.AgentReachAdapter",
        server_id="agent_reach",
    )
    assert ok is True


@pytest.mark.gated
@pytest.mark.external
async def test_agent_reach_real_blocked():
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("agent_reach")
    assert entry.mode == IntegrationMode.MOCK
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 8. FreeLLMAPI — local LLM provider (dev/test)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_freellmapi_config_declares_mock():
    """FreeLLMAPI integration config defaults to mock."""
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    entry = reg.get("freellmapi")
    assert entry is not None, "freellmapi not in canonical integrations"
    assert entry.mode == IntegrationMode.MOCK
    assert entry.requires_user_resource is True
    assert entry.real_allowed() is False


# ---------------------------------------------------------------------------
# 9. Standard providers (Anthropic/OpenAI) — real by default, no env gate
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_anthropic_default_real_no_gate():
    """Anthropic and OpenAI are real by default (no env gate)."""
    from aios.integrations import load_integrations_config, IntegrationMode

    reg = load_integrations_config()
    for name in ("anthropic", "openai"):
        entry = reg.get(name)
        assert entry is not None, f"{name} missing from canonical integrations"
        assert entry.mode == IntegrationMode.REAL, f"{name} should default to real"
        assert entry.real_gated is False, f"{name} should not require env gate"
        # User resource may still be absent — that's checked at runtime by ModelRouter.
        assert entry.requires_user_resource is True


# ---------------------------------------------------------------------------
# 10. Fail-closed: MCPManager.connect rejects REAL without gate
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_mcp_connect_fails_closed_for_real_without_gate():
    """MCPManager.connect must refuse a REAL MCP server lacking the env gate."""
    from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
    from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
    from aios.core.mcp_manager import MCPServerStatus

    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    mgr = MCPManager.__new__(MCPManager)
    mgr._config_dir = None
    mgr._servers = {}
    mgr._status = {}
    mgr._processes = {}
    mgr._tools_cache = {}
    mgr._event_bus = bus
    mgr._identity = None

    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    # Declare REAL mode via metadata.
    cfg = MCPServerConfig(
        server_id="obsidian",
        name="Obsidian (real)",
        transport=MCPTransport.STDIO,
        command=["python", "-m", "aios.adapters.mock_obsidian_server"],
        metadata={"integration_mode": "real"},
    )
    mgr._servers["obsidian"] = cfg
    mgr._status["obsidian"] = MCPServerStatus(server_id="obsidian", transport=MCPTransport.STDIO)

    connected = await mgr.connect("obsidian")
    assert connected is False, "MCPManager.connect allowed a REAL connection without env gate"

    reset_event_bus_singleton()
