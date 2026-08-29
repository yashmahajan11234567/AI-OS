"""
M8-T6 — Session Isolation (spec §12, S-1..S-7).

Verifies that simultaneous and sequential sessions across Hermes, Playwright,
Graphify, and the external knowledge adapters remain isolated — distinct
session/entity IDs, no shared/cross-contaminated state, correct cleanup, and
no leakage of interrupted/partial state into subsequent sessions.

Spec boundary (§17/§25): NO production source is modified. This suite reuses
the shared conftest fixtures only (in-process mock MCP managers).

Markers: ``integration`` (session-isolation), async via pytest-asyncio
(asyncio_mode="auto").
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.adapters.base import ExecutionStatus
from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter
from aios.adapters.hermes_bridge import HermesBridge
from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter
from aios.adapters.mock_graphify_server import MockGraphifyServer
from aios.adapters.mock_notion_server import MockNotionServer
from aios.adapters.mock_obsidian_server import MockObsidianServer
from aios.adapters.mock_claude_mem_server import MockClaudeMemServer
from aios.adapters.mock_hermes_server import MockHermesServer
from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer
from aios.core.testing_evidence import Provenance, TestingEvidence

from tests.integration.conftest import (
    seed_notion,
    seed_obsidian,
    seed_claude_mem,
)

pytestmark = [pytest.mark.integration]


# ===========================================================================
# Helpers — direct adapter construction over an in-process mock MCP manager
# (re-implemented identically to test_m8_t6_cross_adapter_matrix.py so this
# suite stays self-contained and hermetic).
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
# S-1 — Two concurrent Hermes worker sessions → no shared state, distinct IDs
# ===========================================================================


@pytest.mark.asyncio
async def test_s1_concurrent_hermes_sessions_isolated(unified_mock_mcp_manager):
    """S-1: two concurrent Hermes worker sessions are distinct & isolated."""
    hermes = HermesBridge(
        mcp_manager=unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="mcp",
    )

    # Concurrent session creation.
    sid1, sid2 = await asyncio.gather(
        hermes.create_worker_session(),
        hermes.create_worker_session(),
    )

    # Distinct session IDs.
    assert sid1 != sid2

    # Both tracked independently with MCP provenance protocol.
    assert sid1 in hermes._active_sessions
    assert sid2 in hermes._active_sessions
    assert hermes._active_sessions[sid1]["provenance_protocol"] == "mcp"
    assert hermes._active_sessions[sid2]["provenance_protocol"] == "mcp"

    # No shared state — exactly two independent active sessions.
    assert len(hermes._active_sessions) == 2
    assert hermes._active_sessions[sid1] is not hermes._active_sessions[sid2]

    # Provenance `session` matches the owning session for each.
    obs1 = await hermes.navigate(sid1, "https://example.com/a")
    obs2 = await hermes.navigate(sid2, "https://example.com/b")
    assert obs1.provenance.get("session_id") == sid1
    assert obs2.provenance.get("session_id") == sid2
    assert obs1.session_id == sid1
    assert obs2.session_id == sid2

    await hermes.close_worker_session(sid1)
    await hermes.close_worker_session(sid2)


# ===========================================================================
# S-2 — Concurrent Playwright sessions (ephemeral contexts) → no leakage
# ===========================================================================


@pytest.mark.asyncio
async def test_s2_concurrent_playwright_sessions_isolated(unified_mock_mcp_manager):
    """S-2: two concurrent Playwright sessions; closing one leaves the other."""
    pw = PlaywrightMCPAdapter(
        mcp_manager=unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp"),
        server_id="playwright_mcp",
    )
    await pw.connect()

    # Concurrent session creation.
    sid1, sid2 = await asyncio.gather(
        pw.create_session(),
        pw.create_session(),
    )

    # Distinct, isolated sessions.
    assert sid1 != sid2
    assert pw.is_session_active(sid1)
    assert pw.is_session_active(sid2)
    assert sid1 in pw.get_active_sessions()
    assert sid2 in pw.get_active_sessions()

    # Close session 1 only — session 2 must remain unaffected.
    await pw.close_session(sid1)
    assert not pw.is_session_active(sid1)
    assert sid1 not in pw.get_active_sessions()
    assert pw.is_session_active(sid2)
    assert sid2 in pw.get_active_sessions()

    await pw.close_session(sid2)


# ===========================================================================
# S-3 — Concurrent Graphify operations → `ai_os:` namespace isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_s3_graphify_namespace_isolation(unified_mock_mcp_manager):
    """S-3: Graphify entity IDs are `ai_os:`-prefixed and instance-isolated."""
    ga = GraphifyAdapter(
        mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"),
        server_id="graphify",
    )
    gb = GraphifyAdapter(
        mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"),
        server_id="graphify",
    )
    await ga.connect()
    await gb.connect()

    # Namespace prefix is enforced on every entity id.
    assert ga._make_entity_id("alpha") == "ai_os:alpha"
    assert gb._make_entity_id("alpha") == "ai_os:alpha"

    # Concurrent store of the *same logical* id "alpha" into two instances.
    sa, sb = await asyncio.gather(
        ga.store_node("alpha", "TypeA", {"v": 1}),
        gb.store_node("alpha", "TypeB", {"v": 2}),
    )
    assert sa.status == ExecutionStatus.SUCCESS
    assert sb.status == ExecutionStatus.SUCCESS

    # Stored under the namespaced id on each instance's own server.
    assert "ai_os:alpha" in ga._mcp_manager._server._nodes
    assert "ai_os:alpha" in gb._mcp_manager._server._nodes

    # Retrieve independently — instance B must NOT overwrite instance A.
    ra = await ga.get_node("alpha")
    rb = await gb.get_node("alpha")
    assert ra.status == ExecutionStatus.SUCCESS
    assert rb.status == ExecutionStatus.SUCCESS
    assert ra.raw.get("label") == "TypeA"
    assert rb.raw.get("label") == "TypeB"

    await ga.disconnect()
    await gb.disconnect()


# ===========================================================================
# S-4 — Concurrent Notion/Obsidian/Claude-Mem retrieval → no contamination
# ===========================================================================


@pytest.mark.asyncio
async def test_s4_knowledge_retrieval_no_cross_leak(unified_mock_mcp_manager):
    """S-4: two in-process managers per knowledge source return only own data."""
    # --- Notion: two independent managers, each seeded with a distinct page ---
    notion_a = NotionAdapter(
        mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"),
        server_id="notion",
    )
    notion_b = NotionAdapter(
        mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"),
        server_id="notion",
    )
    await notion_a.connect()
    await notion_b.connect()
    seed_notion(notion_a._mcp_manager._server, "pA", "AlphaPage", {"summary": "alpha"}, "root")
    seed_notion(notion_b._mcp_manager._server, "pB", "BetaPage", {"summary": "beta"}, "root")

    res_na = await notion_a.search_pages("Alpha")
    res_nb = await notion_b.search_pages("Beta")
    assert res_na.status == ExecutionStatus.SUCCESS
    assert res_nb.status == ExecutionStatus.SUCCESS
    titles_na = [p["title"] for p in res_na.raw["pages"]]
    titles_nb = [p["title"] for p in res_nb.raw["pages"]]
    assert "AlphaPage" in titles_na and "BetaPage" not in titles_na
    assert "BetaPage" in titles_nb and "AlphaPage" not in titles_nb

    # --- Obsidian: two independent managers, each seeded with a distinct note ---
    obs_a = ObsidianAdapter(
        mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"),
        server_id="obsidian",
    )
    obs_b = ObsidianAdapter(
        mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"),
        server_id="obsidian",
    )
    await obs_a.connect()
    await obs_b.connect()
    seed_obsidian(obs_a._mcp_manager._server, "a/alpha.md", "AlphaNote", ["x"], "alpha body")
    seed_obsidian(obs_b._mcp_manager._server, "b/beta.md", "BetaNote", ["y"], "beta body")

    res_oa = await obs_a.search_notes("alpha")
    res_ob = await obs_b.search_notes("beta")
    assert res_oa.status == ExecutionStatus.SUCCESS
    assert res_ob.status == ExecutionStatus.SUCCESS
    titles_oa = [n["title"] for n in res_oa.raw["notes"]]
    titles_ob = [n["title"] for n in res_ob.raw["notes"]]
    assert "AlphaNote" in titles_oa and "BetaNote" not in titles_oa
    assert "BetaNote" in titles_ob and "AlphaNote" not in titles_ob

    # --- Claude-Mem: two independent managers, each seeded with a distinct memory ---
    mem_a = ClaudeMemAdapter(
        mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"),
        server_id="claude_mem",
    )
    mem_b = ClaudeMemAdapter(
        mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"),
        server_id="claude_mem",
    )
    await mem_a.connect()
    await mem_b.connect()
    seed_claude_mem(mem_a._mcp_manager._server, "m1", "alpha memory content", ["a"], 0.0)
    seed_claude_mem(mem_b._mcp_manager._server, "m2", "beta memory content", ["b"], 0.0)

    res_ma = await mem_a.retrieve_context("alpha")
    res_mb = await mem_b.retrieve_context("beta")
    assert res_ma.status == ExecutionStatus.SUCCESS
    assert res_mb.status == ExecutionStatus.SUCCESS
    contents_ma = [m["content"] for m in res_ma.raw["memories"]]
    contents_mb = [m["content"] for m in res_mb.raw["memories"]]
    assert any("alpha" in c for c in contents_ma) and not any("beta" in c for c in contents_ma)
    assert any("beta" in c for c in contents_mb) and not any("alpha" in c for c in contents_mb)


# ===========================================================================
# S-5 — Cross-task evidence leakage (frozen, independent provenance)
# ===========================================================================


@pytest.mark.asyncio
async def test_s5_evidence_provenance_independent_and_frozen():
    """S-5: two TestingEvidence carry independent session/correlation_id and are frozen."""
    ts = datetime.now(timezone.utc).isoformat()
    prov_a = Provenance(
        source="agency_a", worker="w_a", session="sess_a",
        timestamp=ts, environment="env", correlation_id="corr_a", test_id="t_a",
    )
    prov_b = Provenance(
        source="agency_b", worker="w_b", session="sess_b",
        timestamp=ts, environment="env", correlation_id="corr_b", test_id="t_b",
    )

    ev_a = TestingEvidence(
        perspective="agency_a", target="tgt", test_id="t_a",
        provenance=prov_a, verdict="pass",
    )
    ev_b = TestingEvidence(
        perspective="agency_b", target="tgt", test_id="t_b",
        provenance=prov_b, verdict="fail",
    )

    # Independent provenance per task.
    assert ev_a.provenance is not ev_b.provenance
    assert ev_a.provenance.session != ev_b.provenance.session
    assert ev_a.provenance.correlation_id != ev_b.provenance.correlation_id
    assert ev_a.provenance.session == "sess_a"
    assert ev_b.provenance.session == "sess_b"

    # Provenance is frozen — cannot mutate one to match the other.
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev_a.provenance.session = ev_b.provenance.session
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev_a.provenance.correlation_id = "tampered"


# ===========================================================================
# S-6 — Correct cleanup clears _connected / _active_sessions
# ===========================================================================


@pytest.mark.asyncio
async def test_s6_cleanup_clears_state(unified_mock_mcp_manager):
    """S-6: close_worker_session clears _active_sessions; disconnect clears _connected."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    hermes = adapters["hermes"]
    graphify = adapters["graphify"]

    # Hermes: create then clean up a worker session.
    sid = await hermes.create_worker_session()
    assert sid in hermes._active_sessions
    await hermes.close_worker_session(sid)
    assert sid not in hermes._active_sessions
    assert hermes.is_session_active(sid) is False

    # Graphify: connect then disconnect flips _connected to False.
    assert graphify.is_connected() is False
    await graphify.connect()
    assert graphify.is_connected() is True
    await graphify.disconnect()
    assert graphify.is_connected() is False


# ===========================================================================
# S-7 — Recovery after interrupted execution (no partial-state leak)
# ===========================================================================


@pytest.mark.asyncio
async def test_s7_interrupted_session_no_leak(unified_mock_mcp_manager):
    """S-7: an interrupted Hermes session's state does not leak into a new one."""
    hermes = HermesBridge(
        mcp_manager=unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="mcp",
    )

    # First (interrupted) session.
    sid1 = await hermes.create_worker_session()
    assert sid1 in hermes._active_sessions

    # Simulate interrupted execution: partial state is dropped without a clean
    # close (mirrors a crashed/disconnected worker).
    hermes._active_sessions.pop(sid1, None)
    assert sid1 not in hermes._active_sessions

    # Subsequent session must be a fresh, distinct, tracked session.
    sid2 = await hermes.create_worker_session()
    assert sid2 != sid1
    assert sid1 not in hermes._active_sessions
    assert sid2 in hermes._active_sessions

    # The new session operates cleanly and is fully isolated.
    obs = await hermes.navigate(sid2, "https://example.com/recovered")
    assert obs.provenance.get("session_id") == sid2

    await hermes.close_worker_session(sid2)
