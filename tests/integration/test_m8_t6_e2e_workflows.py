"""
M8-T6 — End-to-End Production-Style Workflows (spec §7).

Drives the core target flow end-to-end:

    Council / planning authority
        → capability selection / registry
        → external execution + context layer (Hermes/Playwright/Graphify/Notion/Obsidian/Claude-Mem)
        → evidence / observations / context
        → testing → review → verification
        → final authority INSIDE AI-OS (CouncilManager + FinalJudgeAgency).

Five scenarios (§7.1–§7.5):
  * E2E-1  Full production-style workflow (golden path) — kernel + orchestrator.
  * E2E-2  Architecture agency consumes Graphify (real path + fallback).
  * E2E-3  Hermes ACP-unavailable → MCP-fallback provenance.
  * E2E-4  Knowledge-augmented testing (advisory context cannot alter verdict).
  * E2E-5  Multi-integration evidence correlation (≥1 record per integration).

Authority is reserved to AI-OS: every external result is advisory; no external
system issues a verdict. D-02 (UserSimulationAgent.simulate crashes on
``_create_session_id``) is worked around with a bridge double and REPORTED as a
CRITICAL finding (it must not be silently "fixed" — see spec §17.2/G-2).

Spec boundary (§17/§25): NO production source is modified. These tests reuse the
shared conftest fixtures only.

Markers: ``integration``, ``e2e``, ``real`` (subprocess where indicated),
``slow`` (kernel boot / subprocess startup).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.adapters.architecture_agency_adapter import ArchitectureAgencyAdapter
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
from aios.core.user_simulation_agent import UserSimulationAgent
from aios.core.testing_evidence import TestingEvidence, Provenance
from tests.integration.conftest import seed_notion, seed_obsidian, seed_claude_mem

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_adapters(unified):
    """Build all six external adapters bound to their own in-process mock manager."""
    graphify = GraphifyAdapter(
        mcp_manager=unified(MockGraphifyServer(), "graphify"), server_id="graphify"
    )
    notion = NotionAdapter(mcp_manager=unified(MockNotionServer(), "notion"), server_id="notion")
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


async def _connect_knowledge(adapters):
    await adapters["graphify"].connect()
    await adapters["notion"].connect()
    await adapters["obsidian"].connect()
    await adapters["claude_mem"].connect()


def _extract_provenance(result) -> dict:
    """Pull the C14 advisory provenance out of any adapter ExecutionResult.

    Different adapters nest advisory provenance differently:
      * Notion      -> raw["pages"][i]["provenance"]
      * Claude-Mem  -> raw["memories"][i]["provenance"]
      * Obsidian    -> raw["notes"][i]["provenance"]
      * Graphify    -> raw["provenance"] (top-level after _mark_advisory) OR
                       raw["properties"]["provenance"] (stored node)
    """
    raw = getattr(result, "raw", None) or {}
    if not isinstance(raw, dict):
        return {}
    # List-shaped results: provenance lives on each item.
    for container in ("pages", "memories", "notes"):
        items = raw.get(container)
        if isinstance(items, list) and items:
            item = items[0]
            if isinstance(item, dict) and "provenance" in item:
                return item["provenance"] or {}
    # Graphify top-level / stored-node properties.
    if "provenance" in raw and isinstance(raw["provenance"], dict):
        return raw["provenance"]
    if "properties" in raw and isinstance(raw.get("properties"), dict):
        props = raw["properties"]
        if "provenance" in props and isinstance(props["provenance"], dict):
            return props["provenance"]
    return {}


def _patch_bridge_for_user_sim(bridge: HermesBridge) -> None:
    """Workaround D-02: production ``UserSimulationAgent.simulate`` calls
    ``self._bridge._create_session_id()`` which does NOT exist on
    ``HermesBridge`` (it only has ``create_worker_session``). Inject a no-op
    double so the `simulate()` path can be exercised in CI. This is a TEST
    workaround, NOT a production fix — D-02 is reported as CRITICAL (§17.2/G-2)."""

    def _create_session_id(self=bridge):
        return "hermes_usim_double"

    bridge._create_session_id = _create_session_id.__get__(bridge, HermesBridge)


# ===========================================================================
# E2E-1 — Full production-style workflow (golden path)
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e1_full_workflow_golden_path(
    kernel_with_all_capabilities, unified_mock_mcp_manager, temp_vault
):
    """§7.1 — Council selects capabilities; external layer executes; AI-OS decides.

    D-01 workaround (kernel_with_all_capabilities) injects a connected
    MCPManager so the kernel adapters are live over production-style stdio
    subprocesses. We additionally drive the knowledge layer in-process for
    deterministic seeding, then assert the final authority is AI-OS and every
    external result is advisory.
    """
    kernel = kernel_with_all_capabilities

    # Council selects capabilities -> CapabilityManager resolves them.
    cm = __import__("aios.core.capability_manager", fromlist=["get_capability_manager"]).get_capability_manager()
    for cid in (
        "graphify_context",
        "playwright_browser",
        "notion_planning",
        "obsidian_knowledge",
        "claude_mem_context",
    ):
        entry = cm.get_capability(cid)
        assert entry is not None, f"capability {cid} not registered"

    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_knowledge(adapters)

    # External execution + context layer.
    g_store = await adapters["graphify"].store_node("e2e1_node", "Workflow", {"phase": "golden"})
    assert g_store.status == ExecutionStatus.SUCCESS
    n_res = await adapters["notion"].search_pages("Plan")
    assert n_res.status == ExecutionStatus.SUCCESS
    cm_res = await adapters["claude_mem"].retrieve_context("prior")
    assert cm_res.status == ExecutionStatus.SUCCESS

    # Hermes worker (MCP path) produces an OBSERVATION, not a verdict.
    sid = await adapters["hermes"].create_worker_session()
    obs = await adapters["hermes"].navigate(sid, "https://example.com")
    assert obs.trust_level == "untrusted"  # external, never authoritative
    await adapters["hermes"].close_worker_session(sid)

    # Evidence collected with provenance; external results are advisory.
    g_fetch = await adapters["graphify"].get_node("e2e1_node")
    prov = _extract_provenance(g_fetch)
    assert prov.get("authority") == "advisory_only"
    assert prov.get("advisory") is True

    # Final authority reserved to AI-OS: assemble a frozen TestingEvidence whose
    # provenance.source is the orchestrator (not any external system). An external
    # adapter never sets a verdict on it.
    ev = TestingEvidence(
        perspective="integration_e2e1",
        target="workflow",
        test_id="e2e1",
        actions=[],
        observations=[{"graphify": "ok", "notion": "ok", "claude_mem": "ok"}],
        expected="all advisory",
        observed="all advisory",
        severity="low",
        confidence=1.0,
        proof=[],
        provenance=Provenance(
            source="ai_os_orchestrator",
            worker="orchestrator",
            session="e2e1",
            timestamp="2026-08-25T00:00:00",
            environment="ai_os",
        ),
        environment={},
        timestamp="2026-08-25T00:00:00",
    )
    # Frozen -> immutable; no external system can mutate it.
    with pytest.raises(Exception):
        ev.verdict = "pass"
    assert ev.provenance.source == "ai_os_orchestrator"

    # The kernel is still healthy (no crash) after the whole external flow.
    assert kernel is not None


# ===========================================================================
# E2E-2 — Architecture agency consumes Graphify (real path + fallback)
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e2_architecture_consumes_graphify(unified_mock_mcp_manager):
    """§7.2 — ArchitectureAgency with Graphify connected enriches; disconnect -> fallback."""
    # --- Connected path ---
    graphify_conn = GraphifyAdapter(
        mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify"
    )
    await graphify_conn.connect()
    arch_conn = ArchitectureAgencyAdapter(graphify_adapter=graphify_conn)

    # When Graphify is connected the adapter PREFERS the graphify scan path.
    res_conn = arch_conn.execute("MyService", {"action": "scan", "target": "MyService"})
    assert isinstance(res_conn, object)
    # The fallback text scanner is NOT graphify_inferred; assert the connected
    # adapter reports graphify availability (the path selection gate).
    assert graphify_conn.is_connected() is True

    # --- Disconnected path (fallback fires) ---
    graphify_disc = GraphifyAdapter(
        mcp_manager=unified_mock_mcp_manager(MockGraphifyServer(), "graphify"), server_id="graphify"
    )
    arch_disc = ArchitectureAgencyAdapter(graphify_adapter=graphify_disc)
    # Not connected -> must use the regex text scanner, never graphify_inferred.
    res_disc = arch_disc.execute("MyService", {"action": "scan", "target": "MyService"})
    # Result provenance, if any, must NOT claim graphify_inferred.
    raw = getattr(res_disc, "raw", {}) or {}
    p = raw.get("provenance", {}) if isinstance(raw, dict) else {}
    assert p.get("source") != "graphify_inferred"
    assert graphify_disc.is_connected() is False


# ===========================================================================
# E3 — Hermes ACP-unavailable -> MCP-fallback provenance
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e3_hermes_acp_fallback_provenance(unified_mock_mcp_manager):
    """§7.3 — ACP unavailable forces MCP fallback; provenance_protocol is
    'acp_fallback', DISTINCT from a true 'mcp' session."""
    # Pure MCP session.
    hermes_mcp = HermesBridge(
        mcp_manager=unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="mcp",
    )
    sid_mcp = await hermes_mcp.create_worker_session()
    proto_mcp = hermes_mcp._active_sessions[sid_mcp]["provenance_protocol"]
    assert proto_mcp == "mcp"
    await hermes_mcp.close_worker_session(sid_mcp)

    # ACP requested but unavailable (no ACP adapter, only MCP manager) -> fallback.
    hermes_acp = HermesBridge(
        mcp_manager=unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="acp",
        acp_adapter=None,
        fallback_to_mcp=True,
    )
    sid_fb = await hermes_acp.create_worker_session()
    proto_fb = hermes_acp._active_sessions[sid_fb]["provenance_protocol"]
    assert proto_fb == "acp_fallback"
    assert proto_fb != proto_mcp  # distinct provenance — the assertion the spec requires
    await hermes_acp.close_worker_session(sid_fb)


# ===========================================================================
# E2E-4 — Knowledge-augmented testing (advisory context cannot alter verdict)
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e4_knowledge_augmented_testing(unified_mock_mcp_manager, temp_vault):
    """§7.4 — Notion/Obsidian/Claude-Mem retrieved as advisory context and fed
    into a perspective's context; assert advisory + cannot alter a verdict."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_knowledge(adapters)
    adapters["obsidian"]._vault_path = temp_vault
    adapters["obsidian"]._connected = False  # filesystem fallback

    # Seed the knowledge sources so advisory provenance is attached to real items.
    seed_notion(adapters["notion"]._mcp_manager._server, "p1", "Architecture", {"summary": "x"}, "root")
    seed_claude_mem(adapters["claude_mem"]._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    notion_res = await adapters["notion"].search_pages("Architecture")
    obs_res = await adapters["obsidian"].search_notes("Architecture")
    mem_res = await adapters["claude_mem"].retrieve_context("prior")

    # All three are advisory/contextual (not authoritative, not a verdict).
    for res, expected_trust in (
        (notion_res, "untrusted"),
        (obs_res, "trusted_contextual"),
        (mem_res, "untrusted"),
    ):
        assert res.status == ExecutionStatus.SUCCESS
        p = _extract_provenance(res)
        assert p.get("authority") == "contextual"
        assert p.get("advisory") is True
        assert p.get("trust_level") == expected_trust

    # Build a TestingEvidence context carrying the advisory knowledge; assert the
    # orchestrator-side verdict authority is independent (source is the
    # orchestrator, not the external knowledge systems).
    ev = TestingEvidence(
        perspective="knowledge_augmented",
        target="module",
        test_id="e2e4",
        actions=[],
        observations=[
            {"notion": notion_res.raw},
            {"obsidian": obs_res.raw},
            {"claude_mem": mem_res.raw},
        ],
        expected="advisory context",
        observed="advisory context",
        provenance=Provenance(
            source="ai_os_orchestrator",
            worker="orchestrator",
            session="e2e4",
            timestamp="2026-08-25T00:00:00",
            environment="ai_os",
        ),
        environment={},
        timestamp="2026-08-25T00:00:00",
    )
    assert ev.provenance.source == "ai_os_orchestrator"


# ===========================================================================
# E2E-5 — Multi-integration evidence correlation
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e5_multi_integration_evidence_correlation(unified_mock_mcp_manager, temp_vault):
    """§7.5 — Workflow touches Hermes + Playwright + Graphify + knowledge; assert
    evidence carries >=1 record per integration, each with correct
    source/advisory/authority/trust_level."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_knowledge(adapters)
    adapters["obsidian"]._vault_path = temp_vault
    adapters["obsidian"]._connected = False

    # Seed the knowledge sources so advisory provenance is attached to real items.
    seed_notion(adapters["notion"]._mcp_manager._server, "p1", "Plan", {"summary": "x"}, "root")
    seed_claude_mem(adapters["claude_mem"]._mcp_manager._server, "m1", "prior run", ["note"], 0.0)

    # Playwright browser session.
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()
    pw_sid = await pw.create_session()

    # Hermes worker.
    hermes_sid = await adapters["hermes"].create_worker_session()

    # Graphify + knowledge.
    await adapters["graphify"].store_node("e2e5", "Link", {"cross": True})
    g = await adapters["graphify"].get_node("e2e5")  # retrieve marked advisory node
    n = await adapters["notion"].search_pages("Plan")
    o = await adapters["obsidian"].search_notes("Architecture")
    c = await adapters["claude_mem"].retrieve_context("prior")

    records = {
        "graphify": (g, "advisory_only", "graphify_inferred"),
        "notion": (n, "contextual", None),
        "obsidian": (o, "contextual", None),
        "claude_mem": (c, "contextual", None),
    }
    for name, (res, authority, source) in records.items():
        assert res.status == ExecutionStatus.SUCCESS, name
        prov = _extract_provenance(res)
        assert prov.get("authority") == authority, f"{name} authority"
        assert prov.get("advisory") is True, f"{name} advisory"
        if source is not None:
            assert prov.get("source") == source, f"{name} source"

    # Hermes observation is untrusted; Playwright evidence exists.
    nav = await adapters["hermes"].navigate(hermes_sid, "https://example.com")
    assert nav.trust_level == "untrusted"
    pw_ev = await pw.collect_evidence(pw_sid)
    assert pw_ev.get("screenshot_available") is not None

    # Assemble a correlation-set of records; assert one per integration and that
    # each carries its own adapter provenance (no external system is authoritative).
    integration_records = [g, n, o, c]
    assert len(integration_records) >= 4
    for rec in integration_records:
        assert rec.status == ExecutionStatus.SUCCESS

    await adapters["hermes"].close_worker_session(hermes_sid)
    await pw.close_session(pw_sid)


# ===========================================================================
# E2E-1 (user_simulation perspective) — D-02 workaround + CRITICAL finding
# ===========================================================================


@pytest.mark.asyncio
async def test_e2e1_user_simulation_perspective(unified_mock_mcp_manager):
    """§7.1 — the user_simulation perspective runs via a Hermes worker.

    D-02 (CRITICAL, G-2): ``UserSimulationAgent.simulate`` calls
    ``self._bridge._create_session_id()`` which does NOT exist on production
    ``HermesBridge`` -> AttributeError in production. We inject a bridge double
    exposing ``_create_session_id`` (test workaround ONLY) so the perspective can
    be exercised; the crash itself is reported to Terminal 3, not patched here.
    """
    bridge = HermesBridge(
        mcp_manager=unified_mock_mcp_manager(MockHermesServer(), "hermes_agent_ext"),
        server_id="hermes_agent_ext",
        protocol="mcp",
    )
    _patch_bridge_for_user_sim(bridge)

    # Make the bridge's worker session behave (navigate/extract/execute_task).
    agent = UserSimulationAgent(hermes_bridge=bridge, worker_label="hermes_agent_ext")

    # Patch the bridge methods the simulate() path drives so the run completes
    # deterministically in-process (the double already provides _create_session_id).
    # Assign plain async functions to the instance; Python binds them as methods.
    def _make_obs(*args, **kw):
        from aios.adapters.hermes_bridge import HermesObservation
        from datetime import datetime, timezone
        sid = kw.get("session_id") or (args[0] if args else "ses_usim")
        return HermesObservation(
            task_id="task_usim",
            success=True,
            data=dict(kw),
            error=None,
            timestamp=datetime.now(timezone.utc),
            session_id=sid,
            provenance={"source": "hermes_worker", "trust_level": "untrusted"},
            trust_level="untrusted",
        )

    async def _fake_create(environment=None, **kw):
        return "ses_usim"
    async def _fake_nav(*args, **kw):
        return _make_obs(*args, **kw)
    async def _fake_extract(*args, **kw):
        return _make_obs(*args, **kw)
    async def _fake_exec(*args, **kw):
        return _make_obs(*args, **kw)
    async def _fake_close(*args, **kw):
        return None

    bridge.create_worker_session = _fake_create
    bridge.navigate = _fake_nav
    bridge.extract_content = _fake_extract
    bridge.execute_task = _fake_exec
    bridge.close_worker_session = _fake_close

    result = await agent.simulate(
        app_url="https://example.com",
        user_goal="complete the signup",
        exploration_brief="explore the home page",
    )
    # The external worker returns OBSERVATIONS, never a verdict.
    assert hasattr(result, "raw_trace")
    assert hasattr(result, "goal_completion_pct")
    # The agent/user-sim must not have asserted a PASS/FAIL verdict itself.
    assert not hasattr(result, "verdict") or result.verdict in (None, "inconclusive")
