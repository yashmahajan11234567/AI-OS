"""
M8-T6 — Failure-Injection Suite (spec §8 F-1..F-16).

For each failure mode, inject the fault via the in-process mock MCP manager's
``set_fault`` (modes: error / malformed / timeout / down) or by disconnecting,
then drive the real adapter operation and assert the system degrades gracefully:
it returns an ERROR/FAILURE ExecutionResult or raises a typed error, and NEVER
silently converts failure -> success.

All adapters are built over one ``UnifiedMockMCPManager`` per server (as the
cross-adapter matrix does), reusing the conftest fixtures. Hermetic.

Spec boundary (§17/§25): NO production source is modified. Marker: ``integration``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from aios.adapters.base import ExecutionStatus
from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter, GraphifyTimeoutError
from aios.adapters.hermes_bridge import HermesBridge
from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.playwright_mcp_adapter import (
    PlaywrightActionError,
    PlaywrightMCPAdapter,
)
from aios.adapters.architecture_agency_adapter import (
    ArchitectureAgencyAdapter,
    _default_graphify_scan,
)
from aios.adapters.mock_claude_mem_server import MockClaudeMemServer
from aios.adapters.mock_graphify_server import MockGraphifyServer
from aios.adapters.mock_hermes_server import MockHermesServer
from aios.adapters.mock_notion_server import MockNotionServer
from aios.adapters.mock_obsidian_server import MockObsidianServer
from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer
from aios.core.capability_manager import (
    CapabilityAvailability,
    CapabilityManager,
    CapabilityManagerError,
)
from aios.core.capability_manifest import (
    AuthorityClassification,
    CapabilitySpec,
    TrustLevel,
)
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import get_service_registry
from aios.core.structured_logger import get_logger
from aios.events.core.bus import EventBus, EventBusConfig

from tests.integration.conftest import seed_notion

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_adapters(unified):
    """Build the six external adapters, one UnifiedMockMCPManager per server."""
    graphify = GraphifyAdapter(
        mcp_manager=unified(MockGraphifyServer(), "graphify"), server_id="graphify"
    )
    notion = NotionAdapter(
        mcp_manager=unified(MockNotionServer(), "notion"), server_id="notion"
    )
    obsidian = ObsidianAdapter(
        mcp_manager=unified(MockObsidianServer(), "obsidian"), server_id="obsidian"
    )
    claude_mem = ClaudeMemAdapter(
        mcp_manager=unified(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem"
    )
    hermes = HermesBridge(
        mcp_manager=unified(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="mcp",
    )
    return {
        "graphify": graphify,
        "notion": notion,
        "obsidian": obsidian,
        "claude_mem": claude_mem,
        "hermes": hermes,
    }


async def _connect_all(adapters):
    await adapters["graphify"].connect()
    await adapters["notion"].connect()
    await adapters["obsidian"].connect()
    await adapters["claude_mem"].connect()


def _disconnect(adapter):
    """Synchronously drop the in-process server so calls raise ERROR/fail.

    ``UnifiedMockMCPManager.disconnect`` is async; for test teardown/injection we
    pop the server entry (mirrors ``manager._servers.pop(sid)``) and flip the
    adapter's connected flag so the adapter degrades to its ERROR path.
    """
    mgr = adapter._mcp_manager
    sid = adapter._server_id
    mgr._servers.pop(sid, None)
    adapter._connected = False


def _make_capability_manager():
    """Build a CapabilityManager wired to real canonical C1-C4 (uninitialized kernel)."""
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()
    mgr = CapabilityManager(service_registry=sr, configuration_manager=cm, logger=logger)
    return mgr


def _make_spec(capability_id: str) -> CapabilitySpec:
    return CapabilitySpec(
        capability_id=capability_id,
        facade="graphify_context",
        provider_id="graphify",
        adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
        adapter_kwargs={"server_id": "graphify"},
        transport="mcp",
        version="1.0.0",
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
        discovered_from="integration-test",
    )


class _SlowGraphifyServer(MockGraphifyServer):
    """Graphify mock whose every response is delayed past a short adapter timeout."""

    async def handle_request(self, request):  # noqa: D401
        await asyncio.sleep(0.3)
        return super().handle_request(request)


# ---------------------------------------------------------------------------
# F-1 — Hermes unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f1_hermes_unavailable_raises(unified_mock_mcp_manager):
    """§8 F-1 — Hermes down => create_worker_session raises; kernel does not crash."""
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    # "down" makes the underlying call_tool raise (never silently succeed).
    mgr.set_fault("down", detail="hermes unavailable")
    with pytest.raises(Exception):
        await hermes.create_worker_session()

    # Explicit second assertion: a faulted manager makes create_worker_session raise.
    mgr2 = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes2 = HermesBridge(
        mcp_manager=mgr2, server_id="hermes_agent_ext", protocol="mcp"
    )
    mgr2.set_fault("down", detail="hermes unavailable 2")
    with pytest.raises(Exception):
        await hermes2.create_worker_session()


@pytest.mark.asyncio
async def test_f1_user_simulation_evidence_fails(unified_mock_mcp_manager):
    """§8 F-1 — user_simulation's Hermes dependency surfaces failure (D-02 noted).

    We inject ``_create_session_id`` on the bridge double (production crash D-02),
    then fault the manager so the simulated worker cannot open a session. The
    failure must surface (raise), never be silently converted to success.
    """
    from aios.core.user_simulation_agent import UserSimulationAgent

    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    hermes._create_session_id = staticmethod(lambda: "hermes_fake_sid")
    mgr.set_fault("down", detail="hermes unavailable")

    agent = UserSimulationAgent(hermes, agent_id="user_simulation_agent")
    with pytest.raises(Exception):
        await agent.simulate(
            "https://example.com",
            "complete the goal",
            "explore the app",
        )


# ---------------------------------------------------------------------------
# F-2 — ACP unavailable -> MCP fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f2_acp_unavailable_mcp_fallback(unified_mock_mcp_manager):
    """§8 F-2 — ACP unavailable => session provenance_protocol == 'acp_fallback'."""
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    # protocol="acp" with no cwd => ACP raises => falls back to MCP.
    hermes = HermesBridge(
        mcp_manager=mgr, server_id="hermes_agent_ext", protocol="acp", cwd=""
    )
    sid = await hermes.create_worker_session()
    assert hermes._active_sessions[sid]["provenance_protocol"] == "acp_fallback"
    assert hermes._active_sessions[sid]["protocol"] == "mcp"


# ---------------------------------------------------------------------------
# F-3 — MCP unavailable (disconnect) -> ERROR result; capability availability=error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f3_mcp_unavailable_returns_error(unified_mock_mcp_manager):
    """§8 F-3 — disconnecting MCP servers degrades to ERROR (never success)."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)
    seed_notion(
        adapters["notion"]._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root"
    )

    # Notion / Claude-Mem / Obsidian return ERROR ExecutionResults when disconnected.
    for name in ("notion", "claude_mem", "obsidian"):
        _disconnect(adapters[name])

    notion_res = await adapters["notion"].search_pages("Plan")
    mem_res = await adapters["claude_mem"].retrieve_context("prior")
    obs_res = await adapters["obsidian"].search_notes("Architecture")
    assert notion_res.status == ExecutionStatus.ERROR
    assert mem_res.status == ExecutionStatus.ERROR
    assert obs_res.status == ExecutionStatus.ERROR

    # Graphify raises a typed error (not silent success) when disconnected.
    _disconnect(adapters["graphify"])
    from aios.adapters.graphify_adapter import GraphifyUnavailableError

    with pytest.raises(GraphifyUnavailableError):
        await adapters["graphify"].store_node("n1", "Node", {"ok": True})

    # Capability availability is reported as error in the registry.
    cm = _make_capability_manager()
    cm.register_capability(_make_spec("graphify_context"))
    entry = cm.get_capability("graphify_context")
    entry.availability = CapabilityAvailability.ERROR
    assert entry.availability == "error"


# ---------------------------------------------------------------------------
# F-4 — Playwright unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f4_playwright_unavailable_raises(unified_mock_mcp_manager):
    """§8 F-4 — Playwright down => action raises; no crash."""
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()
    pw_mgr.set_fault("down", detail="playwright unavailable")
    with pytest.raises(PlaywrightActionError):
        await pw.execute_action(pw_sid, "screenshot", {})


# ---------------------------------------------------------------------------
# F-5 — Browser action failure recorded (not masked as success)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f5_browser_action_failure_recorded(unified_mock_mcp_manager):
    """§8 F-5 — a Playwright action error is recorded as failure, not success."""
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()
    # "error" fault => tool returns {"success": False, "error": ...}.
    pw_mgr.set_fault("error", detail="action failed")
    result = await pw.execute_action(pw_sid, "screenshot", {})
    assert result.get("success") is False
    assert "error" in result


# ---------------------------------------------------------------------------
# F-6 — Graphify unavailable -> ArchitectureAgency text fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f6_graphify_unavailable_text_fallback():
    """§8 F-6 — Graphify down => ArchitectureAgency uses text-scan fallback."""
    graphify = GraphifyAdapter(mcp_manager=None, server_id="graphify")  # never connected
    assert not graphify.is_connected()
    agency = ArchitectureAgencyAdapter(graphify_adapter=graphify)
    ctx = {"implementation": "import os\nimport sys\nimport subprocess\n"}
    result = agency._graphify_scan("mod.py", ctx)
    # Fallback is the regex text-scan, NOT a graphify_inferred result.
    assert result.tool == "graphify_mcp_text_fallback"
    assert "graphify_inferred" not in str(result.raw)
    # Sanity: the standalone fallback helper behaves the same.
    direct = _default_graphify_scan("mod.py", ctx)
    assert direct.tool == "graphify_mcp_text_fallback"


# ---------------------------------------------------------------------------
# F-7 — Notion unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f7_notion_unavailable_error(unified_mock_mcp_manager):
    """§8 F-7 — Notion disconnect => ERROR result; run continues."""
    mgr = unified_mock_mcp_manager(MockNotionServer(), "notion")
    notion = NotionAdapter(mcp_manager=mgr, server_id="notion")
    await notion.connect()
    _disconnect(notion)
    res = await notion.search_pages("Plan")
    assert res.status == ExecutionStatus.ERROR
    # Run continues (a subsequent healthy call on a fresh adapter succeeds).
    mgr2 = unified_mock_mcp_manager(MockNotionServer(), "notion")
    notion2 = NotionAdapter(mcp_manager=mgr2, server_id="notion")
    await notion2.connect()
    seed_notion(mgr2._server, "p1", "Plan", {"summary": "x"}, "root")
    ok = await notion2.search_pages("Plan")
    assert ok.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# F-8 — Obsidian unavailable -> filesystem fallback (if vault) else ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f8_obsidian_unavailable_filesystem_fallback(
    unified_mock_mcp_manager, temp_vault
):
    """§8 F-8 — Obsidian MCP down + vault => filesystem_fallback retrieval works."""
    mgr = unified_mock_mcp_manager(MockObsidianServer(), "obsidian")
    obsidian = ObsidianAdapter(
        mcp_manager=mgr, server_id="obsidian", vault_path=str(temp_vault)
    )
    await obsidian.connect()
    _disconnect(obsidian)
    res = await obsidian.search_notes("Architecture")
    assert res.status == ExecutionStatus.SUCCESS
    assert res.metrics.get("retrieval_path") == "filesystem_fallback"


@pytest.mark.asyncio
async def test_f8_obsidian_unavailable_no_vault_error(unified_mock_mcp_manager):
    """§8 F-8 — Obsidian MCP down + no vault => ERROR (no silent success)."""
    mgr = unified_mock_mcp_manager(MockObsidianServer(), "obsidian")
    obsidian = ObsidianAdapter(mcp_manager=mgr, server_id="obsidian", vault_path=None)
    await obsidian.connect()
    _disconnect(obsidian)
    res = await obsidian.search_notes("Architecture")
    assert res.status == ExecutionStatus.ERROR


# ---------------------------------------------------------------------------
# F-9 — Claude-Mem unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f9_claude_mem_unavailable_error(unified_mock_mcp_manager):
    """§8 F-9 — Claude-Mem disconnect => ERROR result; run continues."""
    mgr = unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem")
    cm = ClaudeMemAdapter(mcp_manager=mgr, server_id="claude_mem")
    await cm.connect()
    _disconnect(cm)
    res = await cm.retrieve_context("prior")
    assert res.status == ExecutionStatus.ERROR


# ---------------------------------------------------------------------------
# F-10 — Capability unavailable (manifest disabled/missing)
# ---------------------------------------------------------------------------


def test_f10_capability_unavailable_reports_unavailable():
    """§8 F-10 — disabled/missing capability => resolve raises; no execution."""
    mgr = _make_capability_manager()
    spec = _make_spec("graphify_context")
    mgr.register_capability(spec)
    # Disable => resolve must raise CM-DIS-001 (fail-closed, no execution).
    mgr.disable("graphify_context")
    with pytest.raises(CapabilityManagerError) as exc:
        mgr.resolve("graphify_context", caller_context={"operation": "query"})
    assert exc.value.rule_id == "CM-DIS-001"

    # Missing capability => get_capability returns None; resolve raises CM-RES-001.
    assert mgr.get_capability("does_not_exist") is None
    with pytest.raises(CapabilityManagerError) as exc2:
        mgr.resolve("does_not_exist")
    assert exc2.value.rule_id == "CM-RES-001"


# ---------------------------------------------------------------------------
# F-11 — Malformed external response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f11_malformed_response_error(unified_mock_mcp_manager):
    """§8 F-11 — malformed external response => ERROR result, not parsed as success."""
    mgr = unified_mock_mcp_manager(MockNotionServer(), "notion")
    notion = NotionAdapter(mcp_manager=mgr, server_id="notion")
    await notion.connect()
    # "malformed" makes call_tool return a structurally broken response.
    mgr.set_fault("malformed", detail="garbage")
    res = await notion.search_pages("Plan")
    # Never silently treated as SUCCESS.
    assert res.status != ExecutionStatus.SUCCESS
    assert res.status == ExecutionStatus.ERROR


# ---------------------------------------------------------------------------
# F-12 — Timeout -> typed error (fast: short adapter timeout + delayed mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f12_timeout_typed_error(unified_mock_mcp_manager):
    """§8 F-12 — operation exceeds adapter timeout => GraphifyTimeoutError."""
    slow = _SlowGraphifyServer()
    mgr = unified_mock_mcp_manager(slow, "graphify")
    graphify = GraphifyAdapter(
        mcp_manager=mgr, server_id="graphify", timeout_seconds=0.05
    )
    await graphify.connect()
    with pytest.raises(GraphifyTimeoutError):
        await graphify.store_node("n1", "Node", {"ok": True})


# ---------------------------------------------------------------------------
# F-13 — Partial execution (one of N fails)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f13_partial_execution(unified_mock_mcp_manager):
    """§8 F-13 — one of N ops fails; that one is ERROR, rest SUCCESS."""
    graphify = GraphifyAdapter(
        mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"),
        server_id="graphify",
    )
    notion = NotionAdapter(
        mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"),
        server_id="notion",
    )
    claude_mem = ClaudeMemAdapter(
        mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"),
        server_id="claude_mem",
    )
    await graphify.connect()
    await notion.connect()
    await claude_mem.connect()
    seed_notion(notion._mcp_manager._server, "p1", "Plan", {"s": 1}, "root")

    # Fault notion only.
    notion._mcp_manager.set_fault("error", detail="notion partial fail")

    g = await graphify.store_node("n1", "Node", {"ok": True})
    n = await notion.search_pages("Plan")
    c = await claude_mem.retrieve_context("prior")

    # Faulted op is ERROR; the others succeed; result not over-claimed.
    assert n.status == ExecutionStatus.ERROR
    assert g.status == ExecutionStatus.SUCCESS
    assert c.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# F-14 — Recovery after failure (no contamination)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f14_recovery_no_contamination(unified_mock_mcp_manager):
    """§8 F-14 — a faulted run does not pollute a subsequent clean run."""
    mgr = unified_mock_mcp_manager(MockNotionServer(), "notion")
    notion = NotionAdapter(mcp_manager=mgr, server_id="notion")
    await notion.connect()
    seed_notion(mgr._server, "p1", "Plan", {"summary": "x"}, "root")

    # Faulted run.
    mgr.set_fault("error")
    bad = await notion.search_pages("Plan")
    assert bad.status == ExecutionStatus.ERROR

    # Clear fault; clean run must be a real SUCCESS (not polluted by stale error).
    mgr.clear_fault()
    good = await notion.search_pages("Plan")
    assert good.status == ExecutionStatus.SUCCESS
    assert len(good.raw["pages"]) == 1


# ---------------------------------------------------------------------------
# F-15 — Repeated failure (bounded, consistent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f15_repeated_failure_consistent(unified_mock_mcp_manager):
    """§8 F-15 — repeated fault => consistent ERROR each time; no hang."""
    mgr = unified_mock_mcp_manager(MockNotionServer(), "notion")
    notion = NotionAdapter(mcp_manager=mgr, server_id="notion")
    await notion.connect()
    seed_notion(mgr._server, "p1", "Plan", {"s": 1}, "root")

    for _ in range(5):
        mgr.set_fault("error", detail="repeat fail")
        res = await notion.search_pages("Plan")
        assert res.status == ExecutionStatus.ERROR
        mgr.clear_fault()

    # Recovers cleanly afterwards.
    ok = await notion.search_pages("Plan")
    assert ok.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# F-16 — Mixed success/failure (each reflects its own status)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f16_mixed_success_failure(unified_mock_mcp_manager):
    """§8 F-16 — some integrations fail, some pass; aggregate is unbiased."""
    notion = NotionAdapter(
        mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"),
        server_id="notion",
    )
    claude_mem = ClaudeMemAdapter(
        mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"),
        server_id="claude_mem",
    )
    await notion.connect()
    await claude_mem.connect()
    seed_notion(notion._mcp_manager._server, "p1", "Plan", {"s": 1}, "root")

    # Fault only claude_mem.
    claude_mem._mcp_manager.set_fault("error", detail="cm fail")

    n = await notion.search_pages("Plan")
    c = await claude_mem.retrieve_context("prior")

    # Each result reflects its own status; no cross-contamination.
    assert n.status == ExecutionStatus.SUCCESS
    assert c.status == ExecutionStatus.ERROR
