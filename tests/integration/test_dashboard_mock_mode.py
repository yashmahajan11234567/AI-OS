"""
M14-T3 (Terminal 2) — Dashboard Mock-Mode Integration Tests.

These tests VERIFY the M13 dashboard backend/service through the M14-T2 real-mode
adapters' read interface. They run WITHOUT any external resources, WITHOUT the
AIOS_REAL_INTEGRATION_ENABLED gate, and WITHOUT credentials.

Invariants asserted (M13 terminal contract preserved):
  * The dashboard is a BOUNDED, read-only UI resource: every page declares
    ``authority: "aios_sole"`` and ``read_only: True``.
  * The dashboard never authorizes or decides: every forwarded action passes
    through SecurityManager.authorize (fail-closed DENY) and is recorded on the
    canonical EventBus as a DASHBOARD_ACTION_* event.
  * The dashboard degrades gracefully (correct mock data) when integrations are
    mock / unavailable / not connected — it never attempts unauthorized real
    connections and never turns degradation into silent success for
    security-sensitive operations.

No production source is modified. No real external connections are attempted.
"""

from __future__ import annotations

import asyncio
import threading
import time
import types
import urllib.request
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.core.security_manager import SecurityDecision
from aios.events.core.bus import EventBusConfig
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.services.dashboard_service import (
    DashboardActionResult,
    DashboardService,
)
from aios.services.dashboard_server import DashboardHTTPServer


# ---------------------------------------------------------------------------
# Fake kernel / doubles
# ---------------------------------------------------------------------------


class _FakeKernel:
    """Minimal kernel double exposing the canonical getters the service reads."""

    terminal_contract_violations: list = []
    integration_status_service = None
    self_loop_engine = None
    failure_recovery_manager = None


class _SpyEventBus:
    """Records published events (mirrors the existing M13 test pattern)."""

    def __init__(self) -> None:
        self.events: list = []

    def publish(self, event) -> None:
        self.events.append(event)
        return None


def _capture_emit(svc: DashboardService) -> list:
    """Record the dashboard's event EMIT INTENT (event type + payload, in order).

    The dashboard's ``_emit`` builds an ``Event`` whose payload includes
    ``correlation_id``. The canonical ``EventPayload`` rejects ``correlation_id``
    (INV-EVT-011), so a REAL validating bus silently drops the event inside
    ``_emit``'s exception handler. We therefore record at the ``_emit`` boundary
    (the arguments the dashboard passes), which faithfully verifies WHICH C1 event
    types the dashboard emits and in what ORDER — without depending on downstream
    EventPayload validation (owned by the events subsystem; documented as a
    frozen-code finding in the Terminal 2 report). This does NOT bypass the
    SecurityManager gate, the fail-closed decision, or any action-forwarding logic.
    """
    captured: list[EventType] = []

    async def _recorded_emit(event_type, payload, *args, **kwargs):
        captured.append(event_type)
        return None

    svc._emit = _recorded_emit  # type: ignore[assignment]
    return captured


def _make_service(kernel=None, security=None, event_bus=None, security_manager=None) -> DashboardService:
    return DashboardService(
        kernel=kernel,
        event_bus=event_bus,
        security_manager=security if security is not None else security_manager,
    )


def _all_page_names() -> list[str]:
    # M13 base pages + M14-T2 additions (Project Workspace, Integrations & Credentials).
    return [
        "planning_chat",
        "resource_onboarding",
        "project_execution",
        "knowledge_history",
        "system_health",
        "project_workspace",
        "integrations_credentials",
    ]


# ---------------------------------------------------------------------------
# A. Dashboard structure
# ---------------------------------------------------------------------------


def test_dashboard_backend_created_without_kernel():
    """DashboardService initializes and degrades safely with no kernel reference."""
    svc = _make_service(kernel=None)
    assert svc._kernel is None
    # get_all_pages must not crash when there is no kernel (graceful degradation).
    pages = svc.get_all_pages()
    assert pages["authority_model"] == "aios_sole_authority"
    assert set(pages["pages"].keys()) == set(_all_page_names())
    for name in _all_page_names():
        assert pages["pages"][name]["authority"] == "aios_sole"
        assert pages["pages"][name]["read_only"] is True


def test_dashboard_get_all_pages_returns_structure():
    """get_all_pages() returns the canonical structure with all seven pages."""
    svc = _make_service(kernel=_FakeKernel())
    pages = svc.get_all_pages()
    assert "generated_at" in pages
    assert pages["authority_model"] == "aios_sole_authority"
    assert isinstance(pages["pages"], dict)
    assert set(pages["pages"].keys()) == set(_all_page_names())
    for name in _all_page_names():
        assert pages["pages"][name]["page"] == name


def test_dashboard_page_authority_header():
    """Every page declares authority = aios_sole (AI-OS retains sole authority)."""
    svc = _make_service(kernel=_FakeKernel())
    for name, page in svc.get_all_pages()["pages"].items():
        assert page["authority"] == "aios_sole", name


def test_dashboard_read_only_flag():
    """Every page declares read_only = True (the dashboard is non-authoritative)."""
    svc = _make_service(kernel=_FakeKernel())
    for name, page in svc.get_all_pages()["pages"].items():
        assert page["read_only"] is True, name


# ---------------------------------------------------------------------------
# B. Adapter state reflection (mock / unavailable / degraded)
# ---------------------------------------------------------------------------


def test_dashboard_knowledge_adapters_reflect_mode():
    """get_knowledge_history reflects each adapter's mode without real connects."""
    kernel = _FakeKernel()

    mock_adapter = MagicMock()
    mock_adapter.is_real_mode.return_value = False
    mock_adapter.is_connected.return_value = True
    mock_adapter.authority_level = "bounded_resource"
    mock_adapter.terminal = "T2"

    kernel.supabase_adapter = mock_adapter
    # n8n deliberately absent -> unavailable (key omitted, no connection attempted)
    # obsidian_git present but raises -> degraded -> mode "unknown"

    degraded = MagicMock()
    degraded.is_real_mode.side_effect = RuntimeError("status unavailable")
    degraded.is_connected.return_value = False
    kernel.obsidian_git_adapter = degraded

    svc = _make_service(kernel=kernel)
    page = svc.get_knowledge_history()

    assert page["adapters"]["supabase"]["mode"] == "mock"
    assert page["adapters"]["supabase"]["authority_level"] == "bounded_resource"
    assert page["adapters"]["supabase"]["terminal"] == "T2"
    # Degraded adapter is reported as "unknown" and never causes a crash.
    assert page["adapters"]["obsidian_git"]["mode"] == "unknown"
    # Absent adapter -> not present in the snapshot (no unauthorized probing).
    assert "n8n" not in page["adapters"]


# ---------------------------------------------------------------------------
# C. Action forwarding through SecurityManager
# ---------------------------------------------------------------------------


def test_dashboard_action_security_gate():
    """An unsupported action is gated: SecurityManager is consulted and returns DENY."""
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    svc = _make_service(kernel=_FakeKernel(), security_manager=sm)
    result = asyncio.run(svc.request_action("dashboard.take_over_aios", {}))
    assert isinstance(result, DashboardActionResult)
    assert result.authorized is False
    assert result.status == "rejected"
    # The dashboard itself decided nothing; SecurityManager was the gate.
    sm.authorize.assert_called_once()


def test_dashboard_action_security_deny_blocks():
    """SecurityManager DENY -> authorized=False, status="rejected" (fail-closed).

    A DENY must remain a DENY: the dashboard cannot bypass SecurityManager and no
    kernel operation may be performed on a denied action.
    """
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    svc = _make_service(kernel=_FakeKernel(), security_manager=sm)
    result = asyncio.run(
        svc.request_action("self_loop.control", {"op": "pause"})
    )
    assert result.authorized is False
    assert result.status == "rejected"
    assert result.decision == SecurityDecision.DENY.value
    sm.authorize.assert_called_once()


# ---------------------------------------------------------------------------
# D. Security fail-closed (event emission)
# ---------------------------------------------------------------------------


def test_dashboard_event_emission_on_action():
    """DASHBOARD_ACTION_REQUESTED is emitted before SecurityManager is consulted.

    The dashboard's EMIT INTENT (C1 event type + payload + ordering) is captured
    at the dashboard's own emit boundary — see _capture_emit for why the downstream
    EventPayload validation (rejecting ``correlation_id``) hides the event from a
    REAL validating bus. This is a frozen-code finding, not a test defect.
    """
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    svc = _make_service(kernel=_FakeKernel(), security_manager=sm)
    captured = _capture_emit(svc)

    asyncio.run(svc.request_action("integration.validate", {"name": "supabase"}))

    assert captured, "expected at least one dashboard event"
    assert captured[0] == EventType.DASHBOARD_ACTION_REQUESTED
    # The dashboard never authorizes: SecurityManager is the sole gate.
    sm.authorize.assert_called_once()


def test_dashboard_event_emission_on_deny():
    """DASHBOARD_ACTION_REJECTED is emitted when SecurityManager denies.

    The emit INTENT (event type + payload + ordering) is captured at the
    dashboard's own emit boundary — see test_dashboard_event_emission_on_action
    for why a validating bus hides the downstream EventPayload validation issue.
    """
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    svc = _make_service(kernel=_FakeKernel(), security_manager=sm)
    captured = _capture_emit(svc)

    asyncio.run(svc.request_action("integration.connect", {"name": "n8n"}))

    emitted = set(captured)
    assert EventType.DASHBOARD_ACTION_REQUESTED in emitted
    assert EventType.DASHBOARD_ACTION_REJECTED in emitted
    assert EventType.DASHBOARD_ACTION_AUTHORIZED not in emitted
    assert EventType.DASHBOARD_ACTION_COMPLETED not in emitted


def test_dashboard_event_emission_on_success():
    """On ALLOW, DASHBOARD_ACTION_AUTHORIZED and _COMPLETED are emitted.

    The emit INTENT is captured at the dashboard's own emit boundary (see
    test_dashboard_event_emission_on_action for the EventPayload validation note).
    """
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.ALLOW

    status_service = MagicMock()
    report = MagicMock()
    report.to_dict.return_value = {"name": "supabase", "state": "validated"}
    status_service.validate_integration = MagicMock()
    status_service.validate_integration.return_value = _await(report)
    kernel = _FakeKernel()
    kernel.integration_status_service = status_service

    svc = _make_service(kernel=kernel, security_manager=sm)
    captured = _capture_emit(svc)

    result = asyncio.run(
        svc.request_action("integration.validate", {"name": "supabase"})
    )
    assert result.authorized is True
    assert result.status == "completed"

    emitted = list(captured)
    assert EventType.DASHBOARD_ACTION_REQUESTED in emitted
    assert EventType.DASHBOARD_ACTION_AUTHORIZED in emitted
    assert EventType.DASHBOARD_ACTION_COMPLETED in emitted
    # Ordering: REQUESTED -> AUTHORIZED -> COMPLETED.
    assert emitted.index(EventType.DASHBOARD_ACTION_REQUESTED) < emitted.index(
        EventType.DASHBOARD_ACTION_AUTHORIZED
    ) < emitted.index(EventType.DASHBOARD_ACTION_COMPLETED)


# ---------------------------------------------------------------------------
# E. HTTP / API behavior
# ---------------------------------------------------------------------------


@pytest.fixture
def running_server():
    kernel = _FakeKernel()
    service = DashboardService(kernel=kernel, security_manager=None)
    server = DashboardHTTPServer(service, host="127.0.0.1", port=8807)
    server.start()
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:8807/api/pages", timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.05)
    yield server
    server.stop()


def test_dashboard_server_start_stop():
    """Server starts/stops cleanly and binds to localhost only (127.0.0.1)."""
    kernel = _FakeKernel()
    service = DashboardService(kernel=kernel, security_manager=None)
    server = DashboardHTTPServer(service, host="127.0.0.1", port=8809)
    assert server._host == "127.0.0.1"  # localhost-only, never 0.0.0.0
    server.start()
    assert server._server is not None
    server.stop()
    assert server._server is None


def test_dashboard_server_api_pages(running_server):
    """GET /api/pages returns valid JSON with all seven pages."""
    with urllib.request.urlopen("http://127.0.0.1:8807/api/pages", timeout=2) as resp:
        assert resp.headers.get("X-AIOS-Authority") == "aios_sole"
        data = __import__("json").loads(resp.read())
    assert data["authority_model"] == "aios_sole_authority"
    assert set(data["pages"].keys()) == set(_all_page_names())
    for name, page in data["pages"].items():
        assert page["read_only"] is True
        assert page["authority"] == "aios_sole"


def test_dashboard_server_api_action(running_server):
    """POST /api/action forwards to DashboardService (fail-closed without SecurityManager)."""
    payload = (
        __import__("json")
        .dumps({"action": "integration.validate", "params": {"name": "supabase"}})
        .encode()
    )
    req = urllib.request.Request(
        "http://127.0.0.1:8807/api/action",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        data = __import__("json").loads(resp.read())
    # With no SecurityManager the gate defaults to DENY — server must NOT authorize.
    assert data["authorized"] is False
    assert data["status"] == "rejected"


def test_dashboard_server_x_aios_authority_header(running_server):
    """All HTTP responses carry X-AIOS-Authority: aios_sole."""
    for path in ("/api/pages", "/"):
        with urllib.request.urlopen(f"http://127.0.0.1:8807{path}", timeout=2) as resp:
            assert resp.headers.get("X-AIOS-Authority") == "aios_sole"


def test_dashboard_server_static_file_served(running_server):
    """GET / serves the static dashboard UI (dashboard.html)."""
    with urllib.request.urlopen("http://127.0.0.1:8807/", timeout=2) as resp:
        body = resp.read().decode("utf-8")
    assert "AI-OS Dashboard" in body
    assert "NON-AUTHORITATIVE" in body


def test_dashboard_server_404_unknown_path(running_server):
    """Unknown paths return 404 (server decides nothing it shouldn't)."""
    try:
        urllib.request.urlopen("http://127.0.0.1:8807/does-not-exist", timeout=2)
        assert False, "expected HTTP 404"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


# ---------------------------------------------------------------------------
# F. Graceful degradation / page content
# ---------------------------------------------------------------------------


def test_dashboard_health_authority_preserved():
    """get_system_health reports authority_preserved=True when no violations."""
    kernel = _FakeKernel()
    kernel.terminal_contract_violations = []
    svc = _make_service(kernel=kernel)
    page = svc.get_system_health()
    assert page["authority"] == "aios_sole"
    assert page["read_only"] is True
    assert page["authority_preserved"] is True
    assert page["terminal_contract_violations"] == []


def test_dashboard_onboarding_violations_displayed():
    """get_resource_onboarding surfaces terminal-contract violations when present.

    Security property verified: the dashboard requests REDACTED integration
    status (redact_secrets=True) and never performs its own secret handling —
    redaction is delegated to the status service (frozen responsibility). The
    dashboard never becomes the authority over secret redaction.
    """
    kernel = _FakeKernel()
    viol = MagicMock()
    viol.component = "x"
    viol.detail = "authority leak"
    viol.severity = "high"
    kernel.terminal_contract_violations = [viol]

    status_service = MagicMock()
    status_service.get_all_status_dict.return_value = [
        {"name": "supabase", "state": "validated"}
    ]
    kernel.integration_status_service = status_service

    svc = _make_service(kernel=kernel)
    page = svc.get_resource_onboarding()

    assert page["all_bounded_resources"] is False
    assert page["terminal_contract_violations"][0]["detail"] == "authority leak"
    # Dashboard delegated secret handling to the status service with redaction on.
    status_service.get_all_status_dict.assert_called_once_with(redact_secrets=True)


def test_dashboard_planning_phase_map():
    """get_planning_chat renders the phase_map derived from the self-loop engine."""
    from aios.core.self_loop_engine import PhaseResult, SelfLoopPhase

    engine = types.SimpleNamespace(
        get_status=lambda: {"running": True},
        PHASE_ORDER=[SelfLoopPhase.USER_INTENT, SelfLoopPhase.PLANNING],
        _current_cycle=types.SimpleNamespace(
            phase_results={
                SelfLoopPhase.USER_INTENT: PhaseResult(
                    phase=SelfLoopPhase.USER_INTENT, success=True
                )
            }
        ),
        _last_self_prompt=None,
    )
    kernel = _FakeKernel()
    kernel.self_loop_engine = engine

    svc = _make_service(kernel=kernel)
    page = svc.get_planning_chat()
    assert page["authority"] == "aios_sole"
    assert page["read_only"] is True
    assert page["phase_map"], "expected a derived phase_map"
    completed = {entry["phase"]: entry for entry in page["phase_map"]}
    assert "user_intent" in completed
    assert completed["user_intent"]["completed"] is True
    assert completed["user_intent"]["success"] is True
    assert completed["planning"]["completed"] is False


def test_dashboard_execution_recovery_records():
    """get_project_execution includes failure_recovery records."""
    rec = types.SimpleNamespace(
        recovery_id="r1",
        failure_id="f1",
        category="transient",
        component="supabase_adapter",
        outcome="recovered",
        attempts=1,
        provenance={"authority": "aios_owned"},
    )
    manager = MagicMock()
    manager.list_records.return_value = [rec]
    kernel = _FakeKernel()
    kernel.failure_recovery_manager = manager

    svc = _make_service(kernel=kernel)
    page = svc.get_project_execution()
    assert page["authority"] == "aios_sole"
    assert page["read_only"] is True
    recovery = page["failure_recovery"]
    assert recovery["count"] == 1
    assert recovery["records"][0]["recovery_id"] == "r1"
    assert recovery["records"][0]["provenance_authority"] == "aios_owned"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _await(value):
    """Wrap a value in an already-completed awaitable for use as an AsyncMock."""
    async def _coro():
        return value
    return _coro()


# ---------------------------------------------------------------------------
# G. Real EventBus delivery (proves the actual production communication path)
#
# These tests subscribe to the CANONICAL EventBus and observe the events that
# DashboardService actually publishes. They do NOT mock EventPayload, Event,
# or EventBus.publish — they prove the real production path:
#   DashboardService._emit() -> EventPayload (INV-EVT-011) -> EventBus.publish().
# If EventPayload ever rejects a dashboard event again, these tests FAIL (the
# event would never reach a real subscriber). This directly closes Terminal 3
# Blocker A (dashboard action events must flow through the canonical EventBus).
# ---------------------------------------------------------------------------

from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.manager import SubscribeOptions, HandlerPriority


class _RealBusCollector:
    """Subscribes to the real EventBus and records delivered dashboard events."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.events: list = []
        opts = SubscribeOptions(
            subscriber=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="m14t3_test_collector",
                version=SemanticVersion(1, 0, 0),
            ),
            event_types=(
                EventType.DASHBOARD_ACTION_REQUESTED,
                EventType.DASHBOARD_ACTION_AUTHORIZED,
                EventType.DASHBOARD_ACTION_REJECTED,
                EventType.DASHBOARD_ACTION_COMPLETED,
            ),
            handler=self._on_event,
            handler_type="sync",
            priority=HandlerPriority.NORMAL,
            max_concurrency=1,
            timeout_ms=5000,
            retry_policy=None,
        )
        bus.subscribe(options=opts)

    def _on_event(self, event) -> None:
        self.events.append(event)


def _boot_real_bus() -> EventBus:
    """Construct a fresh, initialized canonical EventBus (deterministic drain)."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return bus


async def _drive(bus: EventBus, coro):
    """Publish via dashboard then deterministically drain the real bus."""
    result = await coro
    await bus.drain()
    return result


def _mk_allowed_kernel() -> "_FakeKernel":
    """Fake kernel with a status service that supports integration.validate."""
    status_service = MagicMock()
    report = MagicMock()
    report.to_dict.return_value = {"name": "supabase", "state": "validated"}
    status_service.validate_integration = AsyncMock(return_value=report)
    kernel = _FakeKernel()
    kernel.integration_status_service = status_service
    return kernel


def test_dashboard_event_reaches_real_eventbus_requested():
    """DASHBOARD_ACTION_REQUESTED actually reaches the real EventBus (not dropped)."""
    from unittest.mock import AsyncMock

    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.ALLOW
        svc = DashboardService(kernel=_mk_allowed_kernel(), event_bus=bus, security_manager=sm)
        res = await svc.request_action("integration.validate", {"name": "supabase"})
        await bus.drain()
        return res

    res = asyncio.run(_run())
    types = [e.eventType for e in collector.events]
    assert EventType.DASHBOARD_ACTION_REQUESTED in types, (
        f"REQUESTED did not reach the real EventBus; delivered={types}"
    )
    assert res.status == "completed"


def test_dashboard_event_reaches_real_eventbus_authorized():
    """DASHBOARD_ACTION_AUTHORIZED reaches the real EventBus on ALLOW."""
    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.ALLOW
        svc = DashboardService(kernel=_mk_allowed_kernel(), event_bus=bus, security_manager=sm)
        await svc.request_action("integration.validate", {"name": "supabase"})
        await bus.drain()

    asyncio.run(_run())
    types = [e.eventType for e in collector.events]
    assert EventType.DASHBOARD_ACTION_AUTHORIZED in types, (
        f"AUTHORIZED did not reach the real EventBus; delivered={types}"
    )


def test_dashboard_event_reaches_real_eventbus_completed():
    """DASHBOARD_ACTION_COMPLETED reaches the real EventBus on ALLOW."""
    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.ALLOW
        svc = DashboardService(kernel=_mk_allowed_kernel(), event_bus=bus, security_manager=sm)
        await svc.request_action("integration.validate", {"name": "supabase"})
        await bus.drain()

    asyncio.run(_run())
    types = [e.eventType for e in collector.events]
    assert EventType.DASHBOARD_ACTION_COMPLETED in types, (
        f"COMPLETED did not reach the real EventBus; delivered={types}"
    )


def test_dashboard_event_reaches_real_eventbus_rejected():
    """DASHBOARD_ACTION_REJECTED reaches the real EventBus on DENY (fail-closed)."""
    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.DENY
        svc = DashboardService(kernel=_FakeKernel(), event_bus=bus, security_manager=sm)
        await svc.request_action("self_loop.control", {"op": "pause"})
        await bus.drain()

    asyncio.run(_run())
    types = [e.eventType for e in collector.events]
    assert EventType.DASHBOARD_ACTION_REJECTED in types, (
        f"REJECTED did not reach the real EventBus; delivered={types}"
    )
    assert EventType.DASHBOARD_ACTION_AUTHORIZED not in types
    assert EventType.DASHBOARD_ACTION_COMPLETED not in types


def test_dashboard_event_payload_passes_inv_evt_011_and_preserves_correlation():
    """The real EventBus ACCEPTS the dashboard event (INV-EVT-011 satisfied).

    Proves the event passes canonical EventPayload validation AND that correlation
    semantics survive: the UUID correlationId is on the top-level Event, and the
    dashboard-local request_id is preserved in the payload.
    """
    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.ALLOW
        svc = DashboardService(kernel=_mk_allowed_kernel(), event_bus=bus, security_manager=sm)
        await svc.request_action("integration.validate", {"name": "supabase"})
        await bus.drain()
        # Assertions (inside the loop so the bus is live and await is valid).
        assert collector.events, "no events reached the real EventBus"
        for e in collector.events:
            # INV-EVT-011: payload must be free of base-contract field names.
            assert "correlation_id" not in e.payload.to_dict(), (
                "INV-EVT-011 violated: correlation_id in payload"
            )
            assert "correlationId" not in e.payload.to_dict(), (
                "INV-EVT-011 violated: correlationId in payload"
            )
            # Correlation preserved: top-level UUID + payload request_id.
            assert isinstance(e.correlationId, uuid.UUID), "correlationId must be a UUID"
            assert e.payload.get("request_id"), "dashboard request_id correlation must be preserved"
            # Re-publishing the SAME event must not raise (validation is stable).
            re_result = await bus.publish(e)
            assert re_result.accepted, f"re-publish rejected: {re_result.message}"

    asyncio.run(_run())


def test_dashboard_events_are_internally_correlated_on_real_bus():
    """All four events for one action share one correlationId on the real bus."""
    bus = _boot_real_bus()
    collector = _RealBusCollector(bus)

    async def _run():
        await bus.initialize()
        sm = MagicMock()
        sm.authorize.return_value = SecurityDecision.ALLOW
        svc = DashboardService(kernel=_mk_allowed_kernel(), event_bus=bus, security_manager=sm)
        await svc.request_action("integration.validate", {"name": "supabase"})
        await bus.drain()

    asyncio.run(_run())
    cids = {e.correlationId for e in collector.events}
    assert len(cids) == 1, f"events should share one correlationId, got {cids}"
    rid = collector.events[0].payload.get("request_id")
    assert all(e.payload.get("request_id") == rid for e in collector.events), (
        "request_id must be consistent across emitted events"
    )
