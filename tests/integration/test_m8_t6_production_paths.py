"""
M8-T6 — Production-Path Verification (spec §16.1).

Exercises the REAL ``MCPManager`` over stdio subprocesses (the in-repo
``mock_*_server.py`` entry points launched as production-style subprocesses
by the conftest ``RealMCPManagerHarness``). This is distinct from both
in-process doubles (T1-T5) and real-external services (gated). The
``kernel_with_all_capabilities`` fixture boots a real kernel and injects the
connected harness manager into the adapters (D-01 workaround), so every call
below travels the genuine subprocess transport — not an in-process mock.

Markers: ``integration`` (cross-integration), ``real`` (production-style
stdio subprocess via the connected harness), ``slow`` (subprocess startup).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.adapters.base import ExecutionStatus
from aios.core.mcp_manager import MCPManager

pytestmark = [pytest.mark.integration, pytest.mark.real, pytest.mark.slow]


# ===========================================================================
# §16.1 — graphify store / get round-trip over the real subprocess manager
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_graphify_store_via_subprocess(kernel_with_all_capabilities):
    """Graphify store_node + get_node round-trip over the real stdio subprocess."""
    kernel = kernel_with_all_capabilities
    graphify = kernel._graphify_adapter

    # The harness connected this adapter through the real MCPManager (D-01 fix).
    assert graphify.is_connected()

    store = await graphify.store_node("p1", "Node", {"source": "prod"})
    assert store.status == ExecutionStatus.SUCCESS

    # Round-trip: get_node is C14-advisory-marked (D-03 only affects writes).
    got = await graphify.get_node("p1")
    assert got.status == ExecutionStatus.SUCCESS
    prov = got.raw.get("provenance", {})
    assert prov.get("source") == "graphify_inferred"
    assert prov.get("authority") == "advisory_only"


# ===========================================================================
# §16.1 — knowledge adapters answer over the real stdio subprocess
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_notion_search_via_subprocess(kernel_with_all_capabilities):
    """Notion search_pages answered by the real stdio subprocess MCP server."""
    kernel = kernel_with_all_capabilities
    notion = kernel._notion_adapter
    assert notion.is_connected()

    # Mock server is unseeded; SUCCESS (empty list) proves the subprocess answered.
    res = await notion.search_pages("x")
    assert res.status == ExecutionStatus.SUCCESS


@pytest.mark.asyncio
async def test_prod_obsidian_search_via_subprocess(kernel_with_all_capabilities):
    """Obsidian search_notes answered by the real stdio subprocess MCP server."""
    kernel = kernel_with_all_capabilities
    obsidian = kernel._obsidian_adapter
    assert obsidian.is_connected()

    res = await obsidian.search_notes("Architecture")
    assert res.status == ExecutionStatus.SUCCESS


@pytest.mark.asyncio
async def test_prod_claude_mem_retrieve_via_subprocess(kernel_with_all_capabilities):
    """Claude-Mem retrieve_context answered by the real stdio subprocess MCP server."""
    kernel = kernel_with_all_capabilities
    claude_mem = kernel._claude_mem_adapter
    assert claude_mem.is_connected()

    res = await claude_mem.retrieve_context("x")
    assert res.status == ExecutionStatus.SUCCESS


# ===========================================================================
# §16.1 — all adapters connected; harness manager reports connected
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_all_adapters_connected(kernel_with_all_capabilities):
    """Every MCP-bound kernel adapter is connected and the harness reports connected."""
    kernel = kernel_with_all_capabilities

    # Four knowledge adapters (set connected by the fixture's D-01 workaround).
    assert kernel._graphify_adapter.is_connected()
    assert kernel._notion_adapter.is_connected()
    assert kernel._obsidian_adapter.is_connected()
    assert kernel._claude_mem_adapter.is_connected()

    # The Hermes bridge uses the connected harness manager (no is_connected() of its own).
    bridge = kernel._user_simulation_agent._bridge
    mgr = bridge._mcp_manager
    # The four knowledge servers are connected over the real stdio subprocess.
    for sid in ("graphify", "notion", "obsidian", "claude_mem"):
        status = mgr.get_server_status(sid)
        assert status is not None
        assert status.connected is True

    # NOTE — hermes_agent_ext: the Hermes agent MCP server cannot complete its
    # init handshake in CI without the hermes-agent repo (ACP requires a `cwd`
    # path, spec §29.6). The subprocess is launched (present in _processes) but
    # the bridge keeps ACP-default + cwd="" so it resolves to the MCP fallback
    # at session time. Full Hermes subprocess connectivity is out of M8-T6 scope
    # (D-01/D-02 territory); the Hermes bridge path is exercised via the
    # in-process mock in the matrix/E2E suites. We assert the launch, not a
    # connected handshake, here.
    hermes_status = mgr.get_server_status("hermes_agent_ext")
    assert hermes_status is not None


# ===========================================================================
# §16.1 — Hermes bridge worker session over the connected subprocess manager
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_hermes_bridge_mcp_path(kernel_with_all_capabilities):
    """Hermes bridge is wired to the REAL MCPManager; ACP->MCP fallback attempted.

    The kernel constructs the bridge with protocol="acp" + fallback_to_mcp=True and
    cwd="" (no hermes-agent repo in CI). So ``create_worker_session()`` first tries
    ACP (raises ProtocolUnavailableError: "ACP requires cwd parameter") then falls
    back to MCP — but the ``hermes_agent_ext`` stdio subprocess cannot complete its
    init handshake without the hermes-agent repo (spec §29.6 / D-01/D-02). The bridge
    therefore raises a ProtocolError. This test asserts the real transport path is
    wired to the production MCPManager and the documented limitation is honored; the
    bridge's ACP->MCP fallback *semantics* (provenance_protocol="acp_fallback") are
    positively verified in the matrix/E2E suites via the in-process mock path.
    """
    kernel = kernel_with_all_capabilities
    bridge = kernel._user_simulation_agent._bridge

    # The bridge uses the REAL MCPManager (the connected harness manager), not a mock.
    from aios.core.mcp_manager import MCPManager
    from aios.adapters.hermes_bridge import ProtocolError

    assert isinstance(bridge._mcp_manager, MCPManager)

    # ACP->MCP fallback attempted; MCP connect fails in CI (no hermes-agent repo).
    with pytest.raises(ProtocolError):
        await bridge.create_worker_session()


# ===========================================================================
# §16.1 — the injected manager is the REAL MCPManager over subprocesses
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_subprocess_real_mcpmanager_used(kernel_with_all_capabilities):
    """The injected manager is the real MCPManager that launched stdio subprocesses."""
    kernel = kernel_with_all_capabilities
    mgr = kernel._graphify_adapter._mcp_manager

    # Real manager, not the in-process UnifiedMockMCPManager double.
    assert isinstance(mgr, MCPManager)
    assert type(mgr).__name__ != "UnifiedMockMCPManager"

    # It launched real subprocesses for the mock servers.
    assert mgr._processes, "expected real stdio subprocesses to be launched"
    for sid in ("graphify", "notion", "obsidian", "claude_mem", "hermes_agent_ext"):
        assert sid in mgr._processes


# ===========================================================================
# §16.1 — the real SecurityManager gate (C18) passed for the mock config
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_security_gate_passed(kernel_with_all_capabilities):
    """Connection succeeded through the real SecurityManager gate-before-connect (C18).

    The filtered-env mock-server config passed the credential-pattern gate; had it
    failed, the adapter would never be connected.
    """
    kernel = kernel_with_all_capabilities
    assert kernel._graphify_adapter.is_connected() is True

    # Reinforce: the harness manager recorded a connected status (no gate violation).
    mgr = kernel._graphify_adapter._mcp_manager
    status = mgr.get_server_status("graphify")
    assert status is not None
    assert status.connected is True
    assert status.last_error is None


# ===========================================================================
# §16.1 — cross-adapter composition through the real subprocess manager
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_cross_adapter_via_subprocess(kernel_with_all_capabilities):
    """Graphify store + Notion/Obsidian/Claude-Mem retrieval in one subprocess flow."""
    kernel = kernel_with_all_capabilities
    graphify = kernel._graphify_adapter
    notion = kernel._notion_adapter
    obsidian = kernel._obsidian_adapter
    claude_mem = kernel._claude_mem_adapter

    # Graphify write + advisory-marked read (provenance carried on the read path).
    store = await graphify.store_node("cross_1", "Node", {"kind": "subprocess"})
    assert store.status == ExecutionStatus.SUCCESS
    got = await graphify.get_node("cross_1")
    assert got.status == ExecutionStatus.SUCCESS
    assert got.raw.get("provenance", {}).get("source") == "graphify_inferred"

    # Knowledge retrievers all answer over the real subprocess (empty = subprocess replied).
    n = await notion.search_pages("Plan")
    o = await obsidian.search_notes("Architecture")
    c = await claude_mem.retrieve_context("prior")
    assert n.status == ExecutionStatus.SUCCESS
    assert o.status == ExecutionStatus.SUCCESS
    assert c.status == ExecutionStatus.SUCCESS


# ===========================================================================
# §16.1 — disconnect / reconnect recovery over the real subprocess
# ===========================================================================


@pytest.mark.asyncio
async def test_prod_disconnect_reconnect(kernel_with_all_capabilities):
    """Disconnect then reconnect the real stdio subprocess and recover a store."""
    kernel = kernel_with_all_capabilities
    graphify = kernel._graphify_adapter
    mgr = graphify._mcp_manager

    # Baseline write succeeds.
    first = await graphify.store_node("rec_1", "Node", {"seq": 1})
    assert first.status == ExecutionStatus.SUCCESS

    # Tear the subprocess down through the real manager.
    await mgr.disconnect("graphify")
    assert mgr.get_server_status("graphify").connected is False

    # Reconnect through the real manager (re-launches the stdio subprocess).
    reconnected = await mgr.connect("graphify")
    assert reconnected is True
    assert mgr.get_server_status("graphify").connected is True

    # Adapter's connected flag is unchanged; recovery over the new subprocess works.
    assert graphify.is_connected() is True
    second = await graphify.store_node("rec_2", "Node", {"seq": 2})
    assert second.status == ExecutionStatus.SUCCESS
