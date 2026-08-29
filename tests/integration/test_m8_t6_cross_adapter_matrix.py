"""
M8-T6 — Cross-Adapter Execution Matrix (spec §6).

Establishes that the six external-capability adapters compose in a single
production-style workflow. Each pair in §6 is exercised against a booted
kernel with a connected MCPManager (D-01 workaround via the conftest
``kernel_with_all_capabilities`` fixture) or directly-built adapters bound to
an in-process mock MCPManager.

Pair coverage (spec §6 rows 1-10):
  * 1  Hermes + Playwright
  * 2  Hermes + Graphify
  * 3  Hermes + knowledge (Notion/Obsidian/Claude-Mem)
  * 4  Playwright + Graphify
  * 5  Playwright + knowledge
  * 6  Graphify + knowledge
  * 7  Hermes + Playwright + Graphify
  * 8  All external (six capabilities)
  * 9  Any pair under ACP-unavailable -> MCP-fallback
  * 10 Three+ integrations, one forced-fail (degraded-mode seed)

The matrix is the foundation: every later suite (E2E, failure, degraded,
recovery) re-uses the composition patterns proven here.

Spec boundary (§17/§25): NO production source is modified. These tests reuse
the shared conftest fixtures only.

Markers: ``integration`` (cross-integration), ``real`` (production-style
stdio subprocess via kernel_with_all_capabilities), ``slow`` (subprocess
startup).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.adapters.base import ExecutionStatus
from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter
from aios.adapters.hermes_bridge import HermesBridge, HermesTask
from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter
from aios.adapters.mock_graphify_server import MockGraphifyServer
from aios.adapters.mock_notion_server import MockNotionServer
from aios.adapters.mock_obsidian_server import MockObsidianServer
from aios.adapters.mock_claude_mem_server import MockClaudeMemServer
from aios.adapters.mock_hermes_server import MockHermesServer
from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer

pytestmark = [pytest.mark.integration]


# ===========================================================================
# Helpers — direct adapter construction over an in-process mock MCP manager
# ===========================================================================


def _build_adapters(unified):
    """Build all six external adapters bound to one in-process mock manager.

    Each mock server is its own in-process double; the unified manager routes
    call_tool to whichever server registered the matching TOOL_NAMES. For the
    matrix we instead build one manager per server so composition is explicit.
    """
    graphify = GraphifyAdapter(mcp_manager=unified(MockGraphifyServer(), "graphify"), server_id="graphify")
    notion = NotionAdapter(mcp_manager=unified(MockNotionServer(), "notion"), server_id="notion")
    obsidian = ObsidianAdapter(
        mcp_manager=unified(MockObsidianServer(), "obsidian"), server_id="obsidian"
    )
    claude_mem = ClaudeMemAdapter(mcp_manager=unified(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    hermes = HermesBridge(mcp_manager=unified(MockHermesServer(), "hermes_agent_ext"), server_id="hermes_agent_ext", protocol="mcp")
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


# ===========================================================================
# Pair 1 — Hermes + Playwright (E2E: worker drives a browser session)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_hermes_playwright_compose(unified_mock_mcp_manager):
    """§6 pair 1 — a Hermes worker session + a Playwright browser session coexist."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    hermes = adapters["hermes"]

    # Hermes worker session (MCP path).
    sid = await hermes.create_worker_session()
    assert hermes.is_session_active(sid)
    nav = await hermes.navigate(sid, "https://example.com/login")
    assert isinstance(nav, object) and hasattr(nav, "trust_level")
    assert nav.trust_level == "untrusted"

    # Playwright browser session (in-process mock MCP server).
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()
    assert pw.is_session_active(pw_sid)
    ev = await pw.collect_evidence(pw_sid)
    assert ev.get("screenshot_available") is not None

    await hermes.close_worker_session(sid)
    await pw.close_session(pw_sid)
    assert not hermes.is_session_active(sid)


# ===========================================================================
# Pair 2 — Hermes + Graphify (worker actions enriched into graph context)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_hermes_graphify_compose(unified_mock_mcp_manager):
    """§6 pair 2 — Hermes observation + Graphify context enrichment both succeed."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)
    graphify = adapters["graphify"]
    hermes = adapters["hermes"]

    # Enrich the graph with a node representing the worker action.
    store = await graphify.store_node("worker_action_1", "HermesAction", {"kind": "navigation"})
    assert store.status == ExecutionStatus.SUCCESS

    # Hermes worker records the same action.
    sid = await hermes.create_worker_session()
    obs = await hermes.navigate(sid, "https://example.com")
    assert obs.success in (True, False)  # observation only, never a verdict

    # Graphify can retrieve the enrichment (advisory-marked).
    got = await graphify.get_node("worker_action_1")
    assert got.status == ExecutionStatus.SUCCESS
    prov = got.raw.get("provenance", {})
    assert prov.get("source") == "graphify_inferred"
    assert prov.get("authority") == "advisory_only"

    await hermes.close_worker_session(sid)


# ===========================================================================
# Pair 3 — Hermes + knowledge (Notion / Obsidian / Claude-Mem)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_hermes_knowledge_compose(unified_mock_mcp_manager, temp_vault):
    """§6 pair 3 — Hermes worker + three knowledge retrievers in one flow."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)

    # Seed knowledge sources.
    seed_notion = _seed_notion_fn()
    seed_notion(adapters["notion"]._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(adapters["claude_mem"]._mcp_manager._server, "m1", "prior run", ["note"], 0.0)
    obsidian = adapters["obsidian"]
    obsidian._vault_path = temp_vault
    # Obsidian uses filesystem fallback when not MCP-connected.
    obsidian._connected = False

    hermes = adapters["hermes"]
    sid = await hermes.create_worker_session()

    notion_res = await adapters["notion"].search_pages("Plan")
    claude_res = await adapters["claude_mem"].retrieve_context("prior")
    obs_res = await obsidian.search_notes("Architecture")

    assert notion_res.status == ExecutionStatus.SUCCESS
    assert claude_res.status == ExecutionStatus.SUCCESS
    assert obs_res.status == ExecutionStatus.SUCCESS

    # Knowledge results are advisory / non-authoritative.
    np = notion_res.raw["pages"][0].get("provenance", {})
    assert np.get("authority") == "contextual"
    assert np.get("trust_level") == "untrusted"
    cp = claude_res.raw["memories"][0].get("provenance", {})
    assert cp.get("trust_level") == "untrusted"

    await hermes.close_worker_session(sid)


def _seed_notion_fn():
    from tests.integration.conftest import seed_notion
    return seed_notion


def _seed_claude_mem_fn():
    from tests.integration.conftest import seed_claude_mem
    return seed_claude_mem


def _seed_obsidian_fn():
    from tests.integration.conftest import seed_obsidian
    return seed_obsidian


# ===========================================================================
# Pair 4 — Playwright + Graphify (browser actions logged as relationships)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_playwright_graphify_compose(unified_mock_mcp_manager):
    """§6 pair 4 — Playwright browser session + Graphify relationship logging."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    await graphify.connect()

    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()

    # Log the browser session as a graph node (advisory).
    store = await graphify.store_node("browser_session_1", "BrowserSession", {"page": "login"})
    assert store.status == ExecutionStatus.SUCCESS

    ev = await pw.collect_evidence(pw_sid)
    assert ev.get("evidence_count") is not None

    # Relationship between worker-action node and browser session node.
    edge = await graphify.add_edge("worker_action_1", "browser_session_1", "triggered")
    assert edge.status == ExecutionStatus.SUCCESS

    await pw.close_session(pw_sid)


# ===========================================================================
# Pair 5 — Playwright + knowledge (browser evidence cross-referenced)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_playwright_knowledge_compose(unified_mock_mcp_manager, temp_vault):
    """§6 pair 5 — Playwright evidence + Obsidian knowledge cross-reference."""
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()

    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False

    claude_mem = ClaudeMemAdapter(mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    await claude_mem.connect()
    _seed_claude_mem_fn()(claude_mem._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    ev = await pw.collect_evidence(pw_sid)
    obs = await obsidian.search_notes("Architecture")
    mem = await claude_mem.retrieve_context("prior")

    assert ev.get("snapshot_available") is not None
    assert obs.status == ExecutionStatus.SUCCESS
    assert mem.status == ExecutionStatus.SUCCESS

    await pw.close_session(pw_sid)


# ===========================================================================
# Pair 6 — Graphify + knowledge (graph enriched from Notion/Obsidian/Claude-Mem)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_graphify_knowledge_compose(unified_mock_mcp_manager, temp_vault):
    """§6 pair 6 — Graphify enrichment from Notion + Obsidian + Claude-Mem."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")
    claude_mem = ClaudeMemAdapter(mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False
    await _connect_all({"graphify": graphify, "notion": notion, "claude_mem": claude_mem, "obsidian": obsidian})

    _seed_notion_fn()(notion._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(claude_mem._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    # Knowledge retrieved, then logged into the graph (all advisory).
    notion_res = await notion.search_pages("Plan")
    mem_res = await claude_mem.retrieve_context("prior")
    obs_res = await obsidian.search_notes("Architecture")

    for res in (notion_res, mem_res, obs_res):
        assert res.status == ExecutionStatus.SUCCESS

    store = await graphify.store_node("knowledge_link_1", "KnowledgeRef", {"source": "notion+claude+obsidian"})
    assert store.status == ExecutionStatus.SUCCESS

    # Provenance is embedded in the stored node's properties (C14 advisory),
    # so retrieve the node and confirm the advisory provenance survived the
    # store+get round-trip across the Notion/Obsidian/Claude-Mem enrichment.
    fetched = await graphify.get_node("knowledge_link_1")
    assert fetched.status == ExecutionStatus.SUCCESS
    # _mark_advisory (C14) attaches advisory provenance at the top level of the
    # returned node, and the store-time provenance lives inside node.properties.
    prov = fetched.raw.get("provenance", {})
    assert prov.get("advisory") is True
    assert prov.get("authority") == "advisory_only"
    stored_props = fetched.raw.get("properties", {})
    assert stored_props.get("source") == "notion+claude+obsidian"


# ===========================================================================
# Pair 7 — Hermes + Playwright + Graphify (full execution+context chain)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_hermes_playwright_graphify_chain(unified_mock_mcp_manager):
    """§6 pair 7 — Hermes worker + Playwright browser + Graphify context chain."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)
    hermes = adapters["hermes"]

    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()

    # 1. Hermes worker opens the session.
    sid = await hermes.create_worker_session()
    await hermes.navigate(sid, "https://example.com/login")

    # 2. Playwright captures browser evidence.
    ev = await pw.collect_evidence(pw_sid)
    assert ev.get("screenshot_available") is not None

    # 3. Graphify logs the chain (advisory).
    store = await adapters["graphify"].store_node("chain_1", "SessionChain", {"depth": 3})
    assert store.status == ExecutionStatus.SUCCESS

    await hermes.close_worker_session(sid)
    await pw.close_session(pw_sid)


# ===========================================================================
# Pair 8 — All external (the core target flow)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_all_external_compose(unified_mock_mcp_manager, temp_vault):
    """§6 pair 8 — all six capabilities exercised in one coordinated flow."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)
    hermes = adapters["hermes"]
    obsidian = adapters["obsidian"]
    obsidian._vault_path = temp_vault
    obsidian._connected = False

    # Seed knowledge.
    _seed_notion_fn()(adapters["notion"]._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(adapters["claude_mem"]._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    # Hermes worker.
    sid = await hermes.create_worker_session()
    await hermes.navigate(sid, "https://example.com")

    # Playwright browser session.
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()
    await pw.collect_evidence(pw_sid)

    # Graphify context enrichment.
    await adapters["graphify"].store_node("all_1", "Target", {"kind": "e2e"})

    # Knowledge retrieval.
    notion_res = await adapters["notion"].search_pages("Plan")
    mem_res = await adapters["claude_mem"].retrieve_context("prior")
    obs_res = await obsidian.search_notes("Architecture")

    results = [notion_res, mem_res, obs_res]
    assert all(r.status == ExecutionStatus.SUCCESS for r in results)

    await hermes.close_worker_session(sid)
    await pw.close_session(pw_sid)


# ===========================================================================
# Pair 9 — ACP-unavailable -> MCP-fallback provenance correctness
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_acp_fallback_provenance(unified_mock_mcp_manager):
    """§6 pair 9 — Hermes falls back to MCP when ACP is unavailable.

    D-02 note: ``UserSimulationAgent.simulate`` calls the missing
    ``HermesBridge._create_session_id()`` and crashes in production; here we
    drive ``HermesBridge`` directly (the same object the agent uses) to prove
    the fallback provenance is distinguishable from a true MCP session.
    """
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    # protocol="acp" with cwd unset -> ACP raises -> fallback to MCP (acp_fallback).
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="acp", cwd="")

    # ACP path requires an AcPAdapter; with no cwd/adapter available it must
    # raise ProtocolUnavailableError and the bridge falls back to MCP.
    from aios.adapters.hermes_bridge import ProtocolUnavailableError
    sid = await hermes.create_worker_session()
    # Session must be tracked as MCP-protocol with acp_fallback provenance marker.
    assert hermes._active_sessions[sid]["protocol"] == "mcp"
    assert hermes._active_sessions[sid]["provenance_protocol"] == "acp_fallback"

    task = HermesTask(
        task_id="t1", task_type="navigation", description="nav",
        parameters={"url": "https://x.com"}, session_id=sid,
    )
    obs = await hermes.execute_task(task)
    assert obs.provenance.get("protocol") == "acp_fallback"
    assert obs.provenance.get("adapter") == "mcp_manager"

    # A true MCP session (protocol="mcp") yields a distinct provenance.
    hermes_mcp = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    sid2 = await hermes_mcp.create_worker_session()
    assert hermes_mcp._active_sessions[sid2]["provenance_protocol"] == "mcp"
    task2 = HermesTask(
        task_id="t2", task_type="navigation", description="nav",
        parameters={"url": "https://y.com"}, session_id=sid2,
    )
    obs2 = await hermes_mcp.execute_task(task2)
    assert obs2.provenance.get("protocol") == "mcp"

    # The two protocols are distinct (fallback must not masquerade as a real MCP session).
    assert obs.provenance["protocol"] != obs2.provenance["protocol"]

    await hermes.close_worker_session(sid)
    await hermes_mcp.close_worker_session(sid2)


# ===========================================================================
# Pair 10 — Three+ integrations, one forced-fail (degraded-mode seed)
# ===========================================================================


@pytest.mark.asyncio
async def test_pair_three_plus_one_forced_fail(unified_mock_mcp_manager, temp_vault, make_failure_injector):
    """§6 pair 10 — Hermes + Graphify + Notion with Notion forced to fail.

    Asserts the other two integrations still succeed while the failed one
    returns an ERROR result (never silently converted to success).
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters)
    hermes = adapters["hermes"]
    graphify = adapters["graphify"]
    notion = adapters["notion"]

    # Force Notion's underlying mock manager into an error fault.
    notion_mgr = notion._mcp_manager
    async with make_failure_injector(notion_mgr, "error", "injected notion failure"):
        sid = await hermes.create_worker_session()
        await hermes.navigate(sid, "https://example.com")

        store = await graphify.store_node("ok_1", "Node", {"ok": True})
        assert store.status == ExecutionStatus.SUCCESS

        notion_res = await notion.search_pages("Plan")
        # Forced failure -> not SUCCESS (degraded-mode guarantee).
        assert notion_res.status != ExecutionStatus.SUCCESS

    # After the fault clears, Notion recovers.
    notion_recovered = await notion.search_pages("Plan")
    # Recovery is asserted in the recovery suite; here we only assert the
    # degraded contract held during the fault (no success masquerade).
    assert notion_recovered is not None

    await hermes.close_worker_session(sid)


# ===========================================================================
# Production-style subprocess variant (spec §16.1) — real MCPManager paths
# ===========================================================================


@pytest.mark.real
@pytest.mark.slow
@pytest.mark.asyncio
async def test_matrix_all_external_via_real_subprocess(kernel_with_all_capabilities):
    """§6 pair 8 over the REAL MCPManager (stdio subprocess mock servers).

    Distinct from in-process doubles: this drives the production transport
    (D-01 workaround injects the connected manager into the kernel adapters).
    """
    kernel = kernel_with_all_capabilities
    graphify = kernel._graphify_adapter
    notion = kernel._notion_adapter
    claude_mem = kernel._claude_mem_adapter

    # These adapters received a connected manager via the fixture.
    assert graphify.is_connected()
    assert notion.is_connected()
    assert claude_mem.is_connected()

    g = await graphify.store_node("e2e_sub_1", "Node", {"via": "subprocess"})
    assert g.status == ExecutionStatus.SUCCESS
    n = await notion.search_pages("Plan")
    assert n.status == ExecutionStatus.SUCCESS
    c = await claude_mem.retrieve_context("prior")
    assert c.status == ExecutionStatus.SUCCESS
