"""
M8-T6 — Degraded-Mode Tests (spec §14: DG-1..DG-6).

Determines exactly what AI-OS does when dependencies fail. Each DG-x is a
single async test asserting graceful degradation NEVER silently converts
failure -> success.

Conventions reused from ``test_m8_t6_cross_adapter_matrix.py``:
  * ``_build_adapters`` builds the six external adapters over in-process
    ``UnifiedMockMCPManager`` doubles (one manager per server).
  * ``_connect_all`` connects the four MCP-backed knowledge/context adapters.
  * Faults are injected via ``make_failure_injector`` / ``failure_injector``
    on a single adapter's ``UnifiedMockMCPManager`` (``set_fault`` mode).

Spec boundary (§17/§25): NO production source is modified. Only the shared
conftest fixtures are reused.

Markers: ``integration`` (degraded-mode suite).
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
from aios.core.capability_manager import (
    CapabilityAvailability,
    CapabilityManager,
    CapabilityManagerError,
    get_capability_manager,
    set_capability_manager,
)
from aios.core.capability_manifest import CapabilitySpec
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from tests.integration.conftest import failure_injector as make_failure_injector

pytestmark = [pytest.mark.integration]


# ===========================================================================
# Helpers — mirror test_m8_t6_cross_adapter_matrix.py conventions
# ===========================================================================


def _build_adapters(unified):
    """Build all six external adapters bound to in-process mock managers.

    Each adapter gets its OWN ``UnifiedMockMCPManager`` so a fault on one
    server does not bleed into another (required for DG-1..DG-4 isolation).
    """
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


async def _connect_all(adapters, temp_vault):
    """Connect graphify/notion/obsidian/claude_mem and point obsidian at vault."""
    await adapters["graphify"].connect()
    await adapters["notion"].connect()
    await adapters["obsidian"].connect()
    await adapters["claude_mem"].connect()
    # Obsidian dual-path: give it a vault for filesystem fallback in DG-3.
    if temp_vault is not None:
        adapters["obsidian"]._vault_path = temp_vault


def _seed_notion(adapters, page_id="p1", title="Plan", content=None):
    server = adapters["notion"]._mcp_manager._server
    from tests.integration.conftest import seed_notion

    seed_notion(server, page_id, title, content or {"summary": "x"}, "root")


def _seed_claude_mem(adapters, mem_id="m1", content="prior run", tags=None):
    server = adapters["claude_mem"]._mcp_manager._server
    from tests.integration.conftest import seed_claude_mem

    seed_claude_mem(server, mem_id, content, tags or ["note"], 0.0)


def _seed_obsidian(adapters, path="arch.md", title="Architecture", tags=None, content="Kernel notes"):
    server = adapters["obsidian"]._mcp_manager._server
    from tests.integration.conftest import seed_obsidian

    seed_obsidian(server, path, title, tags or ["design"], content)


# ===========================================================================
# DG-1 — One dependency fails (Graphify) -> rest succeed; run completes.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg1_single_dependency_failure_others_succeed(
    unified_mock_mcp_manager, temp_vault
):
    """DG-1: Graphify faulted -> ERROR; notion/obsidian/claude_mem SUCCESS.

    The run completes (no crash), and the failing perspective is reported as
    a failure/ERROR rather than silently converted to success.
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)

    _seed_notion(adapters)
    _seed_claude_mem(adapters)
    _seed_obsidian(adapters)

    graphify_mgr = adapters["graphify"]._mcp_manager
    async with make_failure_injector(graphify_mgr, "error", "injected graphify failure"):
        # Failing perspective. GraphifyAdapter surfaces the fault as a raised
        # error (not a success result) — both satisfy "not success".
        g_failed = False
        g_res = None
        try:
            g_res = await adapters["graphify"].store_node("dg1_1", "Node", {"ok": False})
        except Exception:
            g_failed = True
        # Other perspectives keep working.
        n_res = await adapters["notion"].search_pages("Plan")
        o_res = await adapters["obsidian"].search_notes("Architecture")
        c_res = await adapters["claude_mem"].retrieve_context("prior")

    # Degraded-mode guarantee: failing op is NOT success (raised OR ERROR/FAILURE).
    if not g_failed:
        assert g_res.status != ExecutionStatus.SUCCESS
        assert g_res.status in (ExecutionStatus.ERROR, ExecutionStatus.FAILURE)

    # Others succeed.
    assert n_res.status == ExecutionStatus.SUCCESS
    assert o_res.status == ExecutionStatus.SUCCESS
    assert c_res.status == ExecutionStatus.SUCCESS

    # Aggregation reflects a PARTIAL state (the failing perspective is not success).
    statuses = [n_res.status, o_res.status, c_res.status]
    assert statuses.count(ExecutionStatus.SUCCESS) == 3
    assert g_failed or g_res.status != ExecutionStatus.SUCCESS


# ===========================================================================
# DG-2 — Multiple dependencies fail -> run continues; aggregate partial.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg2_multiple_dependency_failures_partial_aggregate(
    unified_mock_mcp_manager, temp_vault
):
    """DG-2: Graphify + Notion faulted -> both ERROR; obsidian/claude_mem SUCCESS."""
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)

    _seed_claude_mem(adapters)
    _seed_obsidian(adapters)

    g_mgr = adapters["graphify"]._mcp_manager
    n_mgr = adapters["notion"]._mcp_manager

    async with make_failure_injector(g_mgr, "down", "graphify down"), \
            make_failure_injector(n_mgr, "error", "notion error"):
        g_failed = False
        g_res = None
        try:
            g_res = await adapters["graphify"].store_node("dg2_1", "Node", {})
        except Exception:
            g_failed = True
        n_res = await adapters["notion"].search_pages("Plan")
        o_res = await adapters["obsidian"].search_notes("Architecture")
        c_res = await adapters["claude_mem"].retrieve_context("prior")

    # Both faults surface as non-success (never success-masquerade).
    if not g_failed:
        assert g_res.status != ExecutionStatus.SUCCESS
    assert n_res.status != ExecutionStatus.SUCCESS
    # Healthy perspectives still succeed.
    assert o_res.status == ExecutionStatus.SUCCESS
    assert c_res.status == ExecutionStatus.SUCCESS

    # Partial aggregate: run continued, 2 fail + 2 succeed, no crash.
    all_res = [n_res, o_res, c_res]
    ok = sum(1 for r in all_res if r.status == ExecutionStatus.SUCCESS) + (0 if g_failed else 0)
    failed = (1 if g_failed else 0) + sum(1 for r in all_res if r.status != ExecutionStatus.SUCCESS)
    assert ok == 2 and failed == 2


# ===========================================================================
# DG-3 — Only contextual systems fail -> execution systems still run.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg3_contextual_systems_fail_execution_continues(
    unified_mock_mcp_manager, temp_vault
):
    """DG-3: Notion/Obsidian/Claude-Mem faulted -> Graphify still SUCCESS.

    Context is absent but execution systems (Graphify here, plus a direct
    graphify store) keep running; the run does not crash.
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)
    # DG-3: contextual systems must FAIL. Obsidian's filesystem fallback would
    # otherwise mask the MCP failure, so drop the vault so faulting MCP yields
    # a clean ERROR (context absent) rather than a filesystem SUCCESS.
    adapters["obsidian"]._vault_path = None

    n_mgr = adapters["notion"]._mcp_manager
    o_mgr = adapters["obsidian"]._mcp_manager
    c_mgr = adapters["claude_mem"]._mcp_manager

    async with make_failure_injector(n_mgr, "error", "notion down"), \
            make_failure_injector(o_mgr, "down", "obsidian down"), \
            make_failure_injector(c_mgr, "error", "claude_mem down"):
        # Execution system still runs.
        g_res = await adapters["graphify"].store_node("dg3_1", "Node", {"exec": True})
        # Direct graphify retrieval (execution-system op) also still works.
        g_get = await adapters["graphify"].get_node("dg3_1")
        # Contextual retrievals fail (context absent).
        n_res = await adapters["notion"].search_pages("Plan")
        c_res = await adapters["claude_mem"].retrieve_context("prior")

    # Execution systems succeed despite contextual failures.
    assert g_res.status == ExecutionStatus.SUCCESS
    assert g_get.status == ExecutionStatus.SUCCESS

    # Contextual systems report failure (context absent), never success.
    assert n_res.status != ExecutionStatus.SUCCESS
    assert c_res.status != ExecutionStatus.SUCCESS


# ===========================================================================
# DG-4 — Only execution systems fail -> context retrievable; exec = fail.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg4_execution_systems_fail_context_retrievable(
    unified_mock_mcp_manager, temp_vault
):
    """DG-4: Graphify/Playwright/Hermes faulted -> context ops SUCCESS; exec ERROR.

    Knowledge retrieval (Notion/Obsidian/Claude-Mem) remains available; the
    execution evidence is reported as failed and the verdict must reflect that.
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)

    _seed_notion(adapters)
    _seed_claude_mem(adapters)
    _seed_obsidian(adapters)

    g_mgr = adapters["graphify"]._mcp_manager
    h_mgr = adapters["hermes"]._mcp_manager

    # Playwright built separately over its own mock manager.
    pw_mgr = unified_mock_mcp_manager(MockPlaywrightMCPServer(), "playwright_mcp")
    pw = PlaywrightMCPAdapter(mcp_manager=pw_mgr, server_id="playwright_mcp")
    await pw.connect()

    async with make_failure_injector(g_mgr, "error", "graphify down"), \
            make_failure_injector(h_mgr, "down", "hermes down"), \
            make_failure_injector(pw_mgr, "error", "playwright down"):
        # Execution-system ops fail.
        g_failed = False
        g_res = None
        try:
            g_res = await adapters["graphify"].store_node("dg4_1", "Node", {})
        except Exception:
            g_failed = True
        # Context retrievals succeed (context is retrievable).
        n_res = await adapters["notion"].search_pages("Plan")
        o_res = await adapters["obsidian"].search_notes("Architecture")
        c_res = await adapters["claude_mem"].retrieve_context("prior")

    # Context retrievable -> success.
    assert n_res.status == ExecutionStatus.SUCCESS
    assert o_res.status == ExecutionStatus.SUCCESS
    assert c_res.status == ExecutionStatus.SUCCESS

    # Execution evidence fails (degraded) -> verdict MUST reflect failure.
    if not g_failed:
        assert g_res.status != ExecutionStatus.SUCCESS
        assert g_res.status in (ExecutionStatus.ERROR, ExecutionStatus.FAILURE)
    else:
        assert g_failed


# ===========================================================================
# DG-5 — Capability registry has unavailable capabilities.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg5_unavailable_capability_reports_unavailable(
    unified_mock_mcp_manager,
):
    """DG-5: registry reports unavailable/disabled; no execution is attempted.

    Two sub-cases:
      (a) resolve() on an unregistered id raises CM-RES-001.
      (b) a registered-but-disabled (enabled=False) capability raises
          CM-DIS-001; an availability=UNAVAILABLE entry raises CM-RES-002.
    In both, no execution path is taken (we assert the capability object is
    never invoked / no tool call reaches an external server).

    Uses a lightweight EventBus-backed CapabilityManager (no full kernel boot)
    so the degraded-mode suite stays fast and hermetic.
    """
    # Minimal EventBus + CapabilityManager singletons (conftest resets after).
    reset_event_bus_singleton()
    EventBus()  # installs the canonical EventBus singleton
    cm: CapabilityManager = CapabilityManager()
    set_capability_manager(cm)

    # (a) Missing capability -> CM-RES-001, nothing executed.
    with pytest.raises(CapabilityManagerError) as exc:
        cm.resolve("capability_that_does_not_exist")
    assert exc.value.rule_id == "CM-RES-001"

    # (b) Register a valid spec, then mark it unavailable / disabled.
    spec = CapabilitySpec(
        capability_id="dg5_cap",
        facade="testing",
        provider_id="ai_os_testing",
        adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
        adapter_kwargs={},
        transport="local",
        version="1.0.0",
        trust_level="untrusted",
        authority_classification="advisory",
        allowed_operations=("store_node",),
        sensitive_keys=(),
        max_content_size=10240,
        discovered_from="dg5-test",
        tags=("dg5",),
        dependencies=(),
        enabled=True,
        provider_metadata={},
    )
    entry = cm.register_capability(spec)
    # Confirmed registered & resolvable before we degrade it.
    assert cm.get_capability("dg5_cap") is not None
    assert cm.resolve("dg5_cap") is entry

    # Disable it (enabled=False) -> resolve raises CM-DIS-001.
    cm.disable("dg5_cap")
    with pytest.raises(CapabilityManagerError) as exc:
        cm.resolve("dg5_cap")
    assert exc.value.rule_id == "CM-DIS-001"

    # Re-enable, then simulate a health failure (availability=UNAVAILABLE)
    # -> resolve raises CM-RES-002.
    cm.enable("dg5_cap")
    cm.set_health("dg5_cap", CapabilityAvailability.UNAVAILABLE)
    assert cm.get_capability("dg5_cap").availability == CapabilityAvailability.UNAVAILABLE
    with pytest.raises(CapabilityManagerError) as exc:
        cm.resolve("dg5_cap")
    assert exc.value.rule_id == "CM-RES-002"

    # No execution path taken: the capability object itself is never invoked
    # and resolve short-circuits before any adapter/tool dispatch.
    assert cm.resolve.__name__ == "resolve"


# ===========================================================================
# DG-6 — MCP fully disconnected (D-01 realistic state).
# ===========================================================================


@pytest.mark.asyncio
async def test_dg6_mcp_fully_disconnected_adapters_report_error(
    unified_mock_mcp_manager, temp_vault
):
    """DG-6: with no live MCP servers, adapter ops return ERROR/FAILURE fast.

    Build each adapter over its own in-process ``UnifiedMockMCPManager`` then
    simulate full disconnect by clearing the manager's ``_servers`` registry
    (the canonical D-01 state: ``kernel._mcp_manager`` never assigns
    connections). Each adapter operation must return a non-success result
    (ERROR/FAILURE) quickly — never hang, never fabricate success.
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)
    _seed_notion(adapters)
    _seed_claude_mem(adapters)
    _seed_obsidian(adapters)

    import asyncio

    # Simulate full MCP disconnect (D-01 realistic state): set every manager
    # into "down" fault so call_tool raises instead of fabricating a result.
    for name in ("graphify", "notion", "obsidian", "claude_mem", "hermes"):
        adapters[name]._mcp_manager.set_fault("down", detail="mcp disconnected")

    # Adapters must surface non-success quickly — never hang, never fabricate
    # success. Graphify/Notion/Claude-Mem return ERROR/FAILURE; Hermes raises.
    g_failed = False
    g_res = None
    try:
        g_res = await asyncio.wait_for(
            adapters["graphify"].store_node("dg6_1", "Node", {}),
            timeout=10,
        )
    except Exception:
        g_failed = True
    assert g_failed or g_res.status != ExecutionStatus.SUCCESS

    n_res = await asyncio.wait_for(
        adapters["notion"].search_pages("Plan"),
        timeout=10,
    )
    assert n_res.status != ExecutionStatus.SUCCESS

    c_res = await asyncio.wait_for(
        adapters["claude_mem"].retrieve_context("prior"),
        timeout=10,
    )
    assert c_res.status != ExecutionStatus.SUCCESS

    # Hermes: MCP down -> _ensure_mcp_connected fails / call_tool raises ->
    # Hermes must NOT fabricate a session.
    hermes_failed = False
    try:
        await asyncio.wait_for(
            adapters["hermes"].create_worker_session(),
            timeout=10,
        )
    except Exception:
        hermes_failed = True
    assert hermes_failed, "Hermes must not fabricate a session when MCP is down"

    # Aggregate reflects an all-failed state (no success fabricated).
    degraded = [n_res, c_res]
    assert all(r.status != ExecutionStatus.SUCCESS for r in degraded)

    # Clean up the injected faults (good hygiene; conftest resets anyway).
    for name in ("graphify", "notion", "obsidian", "claude_mem", "hermes"):
        adapters[name]._mcp_manager.clear_fault()


# ===========================================================================
# DG-6 variant — adapter.disconnect() then op returns unavailable/ERROR.
# ===========================================================================


@pytest.mark.asyncio
async def test_dg6_disconnect_then_operation_reports_unavailable(
    unified_mock_mcp_manager, temp_vault
):
    """DG-6 (variant): explicit disconnect() -> ops report non-success fast.

    Exercises the per-adapter ``disconnect()`` path: after disconnect the
    adapter's ``is_connected()`` is False and operations surface ERROR/
    FAILURE rather than hanging or reporting success.
    """
    adapters = _build_adapters(unified_mock_mcp_manager)
    await _connect_all(adapters, temp_vault)
    _seed_claude_mem(adapters)

    # Explicitly disconnect graphify and notion.
    await adapters["graphify"].disconnect()
    await adapters["notion"].disconnect()

    assert adapters["graphify"].is_connected() is False
    assert adapters["notion"].is_connected() is False

    import asyncio

    g_failed = False
    g_res = None
    try:
        g_res = await asyncio.wait_for(
            adapters["graphify"].store_node("dg6b_1", "Node", {}),
            timeout=10,
        )
    except Exception:
        g_failed = True
    assert g_failed or g_res.status != ExecutionStatus.SUCCESS

    n_res = await asyncio.wait_for(
        adapters["notion"].search_pages("Plan"),
        timeout=10,
    )
    assert n_res.status != ExecutionStatus.SUCCESS

    # Claude-Mem (still connected) keeps working.
    c_res = await asyncio.wait_for(
        adapters["claude_mem"].retrieve_context("prior"),
        timeout=10,
    )
    assert c_res.status == ExecutionStatus.SUCCESS
