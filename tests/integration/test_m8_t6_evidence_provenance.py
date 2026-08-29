"""
M8-T6 — Evidence / Provenance Validation (spec §9 P-1..P-9).

Validates that the six external-capability adapters preserve correct authority
/ advisory / trust-level / provenance markings on every result, that
``TestingEvidence`` is tamper-evident (frozen + serializable), and that the
D-03/D-04/D-05/D-06 provenance gaps are captured as ``xfail`` findings rather
than silently passing.

Markers: ``integration`` (cross-integration provenance). Async tests use the
auto-applied asyncio mode; ``@pytest.mark.asyncio`` is added to match the
shared conftest convention.

Spec boundary (§17/§25): NO production source is modified. In-process mock
adapters are built via ``unified_mock_mcp_manager(MockXServer(), "x")`` only.
"""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, asdict
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
from aios.adapters.mock_graphify_server import MockGraphifyServer
from aios.adapters.mock_notion_server import MockNotionServer
from aios.adapters.mock_obsidian_server import MockObsidianServer
from aios.adapters.mock_claude_mem_server import MockClaudeMemServer
from aios.adapters.mock_hermes_server import MockHermesServer
from aios.adapters.mock_playwright_mcp_server import MockPlaywrightMCPServer
from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter
from aios.core.testing_evidence import Provenance, TestingEvidence

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_notion_fn():
    from tests.integration.conftest import seed_notion

    return seed_notion


def _seed_claude_mem_fn():
    from tests.integration.conftest import seed_claude_mem

    return seed_claude_mem


# ===========================================================================
# P-1 — Provenance survives across adapter boundaries
# ===========================================================================


@pytest.mark.asyncio
async def test_p1_provenance_survives_boundaries(unified_mock_mcp_manager, temp_vault):
    """§9 P-1 — source/authority/advisory (and adapter/operation/trust_level
    where the adapter emits them) survive the store/search/retrieve round-trip."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")
    claude_mem = ClaudeMemAdapter(mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False  # filesystem fallback path

    await graphify.connect()
    await notion.connect()
    await claude_mem.connect()
    _seed_notion_fn()(notion._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(claude_mem._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    # Graphify write + read round-trip.
    await graphify.store_node("p1_node", "Node", {"kind": "test"})
    g_res = await graphify.get_node("p1_node")
    assert g_res.status == ExecutionStatus.SUCCESS
    g_prov = g_res.raw.get("provenance", {})
    # Graphify advisory provenance carries source/authority/advisory.
    assert g_prov.get("source") == "graphify_inferred"
    assert g_prov.get("authority") == "advisory_only"
    assert g_prov.get("advisory") is True

    # Notion search -> advisory provenance with full C14 field set.
    n_res = await notion.search_pages("Plan")
    n_prov = n_res.raw["pages"][0].get("provenance", {})
    for field in ("source", "adapter", "operation", "authority", "advisory", "trust_level"):
        assert field in n_prov, f"Notion provenance missing {field}"
    assert n_prov["authority"] == "contextual"
    assert n_prov["advisory"] is True

    # Claude-Mem retrieve -> advisory provenance.
    c_res = await claude_mem.retrieve_context("prior")
    c_prov = c_res.raw["memories"][0].get("provenance", {})
    for field in ("source", "adapter", "operation", "authority", "advisory", "trust_level"):
        assert field in c_prov, f"Claude-Mem provenance missing {field}"

    # Obsidian filesystem-fallback search -> advisory provenance.
    o_res = await obsidian.search_notes("Architecture")
    o_prov = o_res.raw["notes"][0].get("provenance", {})
    for field in ("source", "adapter", "operation", "authority", "advisory", "trust_level"):
        assert field in o_prov, f"Obsidian provenance missing {field}"


# ===========================================================================
# P-2 — execution_id consistent within a single adapter operation across retries
# ===========================================================================


@pytest.mark.asyncio
async def test_p2_execution_id_consistent(unified_mock_mcp_manager):
    """§9 P-2 — Graphify ``_make_provenance`` preserves a passed ``execution_id``;
    a ``None`` execution_id is consistently ``None`` (no fabricated stability)."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")

    # Passed execution_id is preserved across repeated calls (idempotent arg).
    p1 = graphify._make_provenance("store_node", execution_id="EXEC-1")
    p2 = graphify._make_provenance("store_node", execution_id="EXEC-1")
    assert p1["execution_id"] == "EXEC-1"
    assert p2["execution_id"] == "EXEC-1"

    # None passed -> None consistently (not silently regenerated).
    p3 = graphify._make_provenance("store_node", execution_id=None)
    p4 = graphify._make_provenance("store_node", execution_id=None)
    assert p3["execution_id"] is None
    assert p4["execution_id"] is None


# ===========================================================================
# P-3 — correlation_id consistency (current behavior + D-04 gap flag)
# ===========================================================================


@pytest.mark.asyncio
async def test_p3_correlation_id_per_call_distinct(unified_mock_mcp_manager):
    """§9 P-3 — assert CURRENT behavior: each adapter call regenerates a fresh
    ``correlation_id`` (per-call uuid4). This is the D-04 gap made explicit."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")

    a = graphify._make_provenance("store_node")
    b = graphify._make_provenance("store_node")
    # Distinct per call — correlation_id is never propagated/injected from outside.
    assert a["correlation_id"] != b["correlation_id"]

    c = notion._make_provenance("search_pages")
    d = notion._make_provenance("search_pages")
    assert c["correlation_id"] != d["correlation_id"]


@pytest.mark.asyncio
async def test_p3_correlation_id_propagation_xfail(unified_mock_mcp_manager):
    """§9 P-3 / D-04 — CLOSED (M9-N8): an orchestrator-supplied
    ``correlation_id`` now survives into the adapter operation result via the
    canonical C4 CorrelationContext (contextvars) that adapters consult when
    building provenance. Assertion unchanged from the original xfail."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    await graphify.connect()

    known = "orchestrator-corr-123"
    from aios.core.structured_logger import (
        CorrelationContext,
        clear_correlation_context,
        set_correlation_context,
    )

    token = set_correlation_context(
        CorrelationContext(correlation_id=known)
    )
    try:
        await graphify.store_node("p3_node", "Node", {})
        got = await graphify.get_node("p3_node")
        # The adapter carries the orchestrator's correlation_id through.
        assert got.raw["provenance"]["correlation_id"] == known
    finally:
        clear_correlation_context(token)


# ===========================================================================
# P-4 — task_id / session_id correctly associated (Hermes)
# ===========================================================================


@pytest.mark.asyncio
async def test_p4_hermes_session_id_associated(unified_mock_mcp_manager):
    """§9 P-4 — Hermes ``session_id`` matches ``provenance.session_id`` and the
    session is tracked with a ``provenance_protocol`` marker."""
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")

    sid = await hermes.create_worker_session()
    assert hermes.is_session_active(sid)
    # Session tracked with a provenance_protocol marker.
    assert hermes._active_sessions[sid]["provenance_protocol"] == "mcp"

    task = HermesTask(
        task_id="task-xyz",
        task_type="navigation",
        description="nav",
        parameters={"url": "https://example.com"},
        session_id=sid,
    )
    obs = await hermes.execute_task(task)
    prov = obs.provenance
    # session_id + task_id are associated in the observation provenance.
    assert prov["session_id"] == sid
    assert prov["task_id"] == "task-xyz"
    assert obs.trust_level == "untrusted"

    await hermes.close_worker_session(sid)


# ===========================================================================
# P-5 — Protocol / adapter provenance accurate
# ===========================================================================


@pytest.mark.asyncio
async def test_p5_protocol_provenance_accurate(unified_mock_mcp_manager):
    """§9 P-5 — a true ``mcp`` session and an ``acp_fallback`` session produce
    distinct, accurate ``protocol`` / ``adapter`` provenance values."""
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")

    # ACP unavailable (no cwd) -> honest fallback to MCP (provenance=acp_fallback).
    h_fb = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="acp", cwd="")
    sid_fb = await h_fb.create_worker_session()
    obs_fb = await h_fb.execute_task(
        HermesTask(task_id="t1", task_type="navigation", description="nav",
                   parameters={"url": "https://x.com"}, session_id=sid_fb)
    )
    assert obs_fb.provenance["protocol"] == "acp_fallback"
    assert obs_fb.provenance["adapter"] == "mcp_manager"

    # True MCP session (protocol="mcp") yields a distinct provenance.
    h_mcp = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    sid_mcp = await h_mcp.create_worker_session()
    obs_mcp = await h_mcp.execute_task(
        HermesTask(task_id="t2", task_type="navigation", description="nav",
                   parameters={"url": "https://y.com"}, session_id=sid_mcp)
    )
    assert obs_mcp.provenance["protocol"] == "mcp"
    assert obs_mcp.provenance["adapter"] == "mcp_manager"

    # The fallback must NOT masquerade as a real MCP session.
    assert obs_fb.provenance["protocol"] != obs_mcp.provenance["protocol"]

    await h_fb.close_worker_session(sid_fb)
    await h_mcp.close_worker_session(sid_mcp)


# ===========================================================================
# P-6 — TestingEvidence is frozen + serializable
# ===========================================================================


@pytest.mark.asyncio
async def test_p6_testing_evidence_frozen_serialization():
    """§9 P-6 — ``TestingEvidence`` is ``@dataclass(frozen=True)``: attribute
    assignment raises, and serialization round-trips preserve fields."""
    prov = Provenance(
        source="ai_os_agency",
        worker="worker_1",
        session="sess_1",
        timestamp="2026-08-25T00:00:00",
        environment="test",
    )
    ev = TestingEvidence(
        perspective="architecture_agency",
        target="cap_graphify_context",
        test_id="T-001",
        observations=[{"type": "ok"}],
        provenance=prov,
        verdict="pass",
    )

    # Immutability: setting an attribute must raise FrozenInstanceError.
    with pytest.raises(FrozenInstanceError):
        ev.perspective = "other"

    # dataclasses.asdict round-trip preserves core fields.
    d = asdict(ev)
    assert d["perspective"] == "architecture_agency"
    assert d["test_id"] == "T-001"
    assert d["provenance"]["source"] == "ai_os_agency"

    # to_dict / from_dict round-trip preserves fields.
    d2 = ev.to_dict()
    ev2 = TestingEvidence.from_dict(d2)
    assert ev2.target == ev.target
    assert ev2.test_id == ev.test_id
    assert ev2.provenance.source == "ai_os_agency"
    assert ev2.verdict == "pass"


# ===========================================================================
# P-7 — External data stays advisory / contextual / untrusted (exact values)
# ===========================================================================


@pytest.mark.asyncio
async def test_p7_external_advisory_exact(unified_mock_mcp_manager, temp_vault):
    """§9 P-7 — exact authority/advisory/trust_level/source per integration."""
    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")
    claude_mem = ClaudeMemAdapter(mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")

    await notion.connect()
    await claude_mem.connect()
    await graphify.connect()
    _seed_notion_fn()(notion._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(claude_mem._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    # Notion: contextual / advisory / untrusted.
    n_prov = (await notion.search_pages("Plan")).raw["pages"][0]["provenance"]
    assert n_prov["authority"] == "contextual"
    assert n_prov["advisory"] is True
    assert n_prov["trust_level"] == "untrusted"

    # Claude-Mem: contextual / untrusted.
    c_prov = (await claude_mem.retrieve_context("prior")).raw["memories"][0]["provenance"]
    assert c_prov["authority"] == "contextual"
    assert c_prov["trust_level"] == "untrusted"

    # Obsidian: contextual / trusted_contextual.
    o_prov = (await obsidian.search_notes("Architecture")).raw["notes"][0]["provenance"]
    assert o_prov["authority"] == "contextual"
    assert o_prov["trust_level"] == "trusted_contextual"

    # Graphify: advisory_only / graphify_inferred.
    await graphify.store_node("p7_node", "Node", {})
    g_prov = (await graphify.get_node("p7_node")).raw["provenance"]
    assert g_prov["authority"] == "advisory_only"
    assert g_prov["source"] == "graphify_inferred"

    # Hermes: trust_level forced to untrusted.
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    sid = await hermes.create_worker_session()
    obs = await hermes.execute_task(
        HermesTask(task_id="t", task_type="navigation", description="nav",
                   parameters={"url": "https://e.com"}, session_id=sid)
    )
    assert obs.trust_level == "untrusted"
    await hermes.close_worker_session(sid)


# ===========================================================================
# P-8 — No adapter is ever authoritative
# ===========================================================================


@pytest.mark.asyncio
async def test_p8_never_authoritative(unified_mock_mcp_manager, temp_vault):
    """§9 P-8 — Graphify/Hermes/Playwright/Notion/Obsidian/Claude-Mem never set
    ``authority`` in {authoritative, builtin}."""
    forbidden = {"authoritative", "builtin"}

    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")
    claude_mem = ClaudeMemAdapter(mcp_manager=unified_mock_mcp_manager(MockClaudeMemServer(), "claude_mem"), server_id="claude_mem")
    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")

    await notion.connect()
    await claude_mem.connect()
    await graphify.connect()
    _seed_notion_fn()(notion._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    _seed_claude_mem_fn()(claude_mem._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    n_auth = (await notion.search_pages("Plan")).raw["pages"][0]["provenance"]["authority"]
    c_auth = (await claude_mem.retrieve_context("prior")).raw["memories"][0]["provenance"]["authority"]
    o_auth = (await obsidian.search_notes("Architecture")).raw["notes"][0]["provenance"]["authority"]
    await graphify.store_node("p8_node", "Node", {})
    g_auth = (await graphify.get_node("p8_node")).raw["provenance"]["authority"]

    for name, auth in (("notion", n_auth), ("claude_mem", c_auth), ("obsidian", o_auth), ("graphify", g_auth)):
        assert auth not in forbidden, f"{name} must never be {auth}"

    # Hermes provenance carries no authority field at all (untrusted by default).
    mgr = unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext")
    hermes = HermesBridge(mcp_manager=mgr, server_id="hermes_agent_ext", protocol="mcp")
    sid = await hermes.create_worker_session()
    obs = await hermes.execute_task(
        HermesTask(task_id="t", task_type="navigation", description="nav",
                   parameters={"url": "https://e.com"}, session_id=sid)
    )
    assert "authority" not in obs.provenance or obs.provenance.get("authority") not in forbidden
    await hermes.close_worker_session(sid)

    # Playwright results carry no authority (no provenance dict at all).
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()
    res = await pw.execute_action(pw_sid, "screenshot", {})
    assert "authority" not in res
    await pw.close_session(pw_sid)


# ===========================================================================
# P-9 — Regression assertions for D-03 / D-04 / D-05 / D-06 (xfail findings)
# ===========================================================================


@pytest.mark.asyncio
async def test_p9_d03_graphify_write_unmarked(unified_mock_mcp_manager):
    """§9 P-9 / D-03 — CLOSED (M9-N8): Graphify write-path stored node
    provenance now carries C14 advisory markers (``authority="advisory_only"``,
    ``advisory=True``) because the adapter marks the STORED properties block,
    not just the returned result. Assertions unchanged from the original xfail."""
    graphify = GraphifyAdapter(mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify")
    await graphify.connect()

    await graphify.store_node("d03_node", "Node", {"k": 1})
    node = graphify._mcp_manager._server._nodes["ai_os:d03_node"]
    node_prov = node["properties"]["provenance"]
    assert node_prov.get("authority") == "advisory_only"
    assert node_prov.get("advisory") is True


@pytest.mark.asyncio
async def test_p9_d04_correlation_not_propagated_notion(unified_mock_mcp_manager):
    """§9 P-9 / D-04 — CLOSED (M9-N8): an orchestrator ``correlation_id``
    surfaces in the Notion result provenance via the ambient C4
    CorrelationContext. Assertion unchanged from the original xfail."""
    notion = NotionAdapter(mcp_manager=unified_mock_mcp_manager(MockNotionServer(), "notion"), server_id="notion")
    await notion.connect()
    _seed_notion_fn()(notion._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")

    known = "corr-orchestrator-xyz"
    from aios.core.structured_logger import (
        CorrelationContext,
        clear_correlation_context,
        set_correlation_context,
    )

    token = set_correlation_context(
        CorrelationContext(correlation_id=known)
    )
    try:
        page_prov = (await notion.search_pages("Plan")).raw["pages"][0]["provenance"]
        assert page_prov["correlation_id"] == known
    finally:
        clear_correlation_context(token)


@pytest.mark.asyncio
async def test_p9_d05_playwright_no_advisory(unified_mock_mcp_manager):
    """§9 P-9 / D-05 — CLOSED (M9-N8): ``PlaywrightMCPAdapter.execute_action``
    now returns a provenance-marked result (C14 advisory under the
    ``provenance`` key). Assertions unchanged from the original xfail."""
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()

    res = await pw.execute_action(pw_sid, "screenshot", {})
    # The result should carry an advisory provenance marker.
    assert isinstance(res, dict)
    assert res.get("provenance", {}).get("advisory") is True
    await pw.close_session(pw_sid)


@pytest.mark.asyncio
async def test_p9_d06_obsidian_list_fallback_unmarked(unified_mock_mcp_manager, temp_vault):
    """§9 P-9 / D-06 — CLOSED (M9-N8): Obsidian ``list_notes``
    filesystem-fallback results now pass through ``_mark_advisory`` (adding the
    ``obsidian_timestamp`` C14 marker). Assertion unchanged from the xfail."""
    obsidian = ObsidianAdapter(mcp_manager=unified_mock_mcp_manager(MockObsidianServer(), "obsidian"), server_id="obsidian")
    obsidian._vault_path = temp_vault
    obsidian._connected = False

    res = await obsidian.list_notes(".")
    notes = res.raw["notes"]
    assert notes, "expected at least one listed note in the temp vault"
    for note in notes:
        prov = note.get("provenance", {})
        # _mark_advisory is the canonical C14 marker; it adds obsidian_timestamp.
        assert "obsidian_timestamp" in prov
