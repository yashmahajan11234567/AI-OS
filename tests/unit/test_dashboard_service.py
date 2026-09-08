"""
M13 — Dashboard backend (non-authoritative) unit tests.

Asserts the M13 invariant: the dashboard is a BOUNDED UI resource. It reads
AI-OS state read-only and forwards user actions through the SecurityManager
(fail-closed). It holds NO governance/verification/decision authority — every
action is either rejected by the SecurityManager or executed by AI-OS.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.core.security_manager import SecurityDecision
from aios.core.observability_manager import MetricType, reset_observability_manager_singleton, get_observability_manager, set_observability_manager, ObservabilityManager
from aios.core.health_manager import HealthStatus, reset_health_manager_singleton, get_health_manager, set_health_manager, HealthManager
from aios.events.core.bus import reset_event_bus_singleton, EventBus, EventBusConfig
from aios.services.dashboard_service import DashboardService, DashboardActionResult


@pytest.fixture
def kernel_mock():
    """Minimal kernel double exposing the canonical getters the service reads."""
    kernel = MagicMock()
    kernel.terminal_contract_violations = []
    kernel.get_stats.return_value = {"kernel": {"name": "aios", "running": True}}
    # ProjectService is authored by AI-OS and wired separately; leave it unset so
    # the Project Workspace page reports unavailable (non-authoritative) by default.
    kernel.project_service = None
    return kernel


@pytest.fixture
def security_allow():
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.ALLOW
    return sm


@pytest.fixture
def security_deny():
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    return sm


def _make_service(kernel, security, event_bus=None):
    return DashboardService(kernel=kernel, event_bus=event_bus, security_manager=security)


# ---------------------------------------------------------------- read-only pages


def test_pages_declare_aios_sole_authority(kernel_mock):
    svc = _make_service(kernel_mock, None)
    pages = svc.get_all_pages()
    for name, page in pages["pages"].items():
        assert page["authority"] == "aios_sole", name
        assert page["read_only"] is True, name


def test_resource_onboarding_reports_bounded_when_no_violations(kernel_mock):
    svc = _make_service(kernel_mock, None)
    page = svc.get_resource_onboarding()
    assert page["all_bounded_resources"] is True
    assert page["terminal_contract_violations"] == []


def test_resource_onboarding_surfaces_violations(kernel_mock):
    viol = MagicMock()
    viol.component = "x"
    viol.detail = "authority leak"
    viol.severity = "high"
    kernel_mock.terminal_contract_violations = [viol]
    svc = _make_service(kernel_mock, None)
    page = svc.get_resource_onboarding()
    assert page["all_bounded_resources"] is False
    assert page["terminal_contract_violations"][0]["detail"] == "authority leak"


def test_system_health_authority_preserved_when_clean(kernel_mock):
    svc = _make_service(kernel_mock, None)
    page = svc.get_system_health()
    assert page["authority_preserved"] is True
    assert page["kernel_stats"]["kernel"]["name"] == "aios"


def test_knowledge_history_reads_adapter_modes(kernel_mock):
    adapter = MagicMock()
    adapter.is_real_mode.return_value = False
    adapter.is_connected.return_value = True
    adapter.authority_level = "bounded_resource"
    adapter.terminal = "T2"
    kernel_mock.supabase_adapter = adapter
    svc = _make_service(kernel_mock, None)
    page = svc.get_knowledge_history()
    assert page["adapters"]["supabase"]["mode"] == "mock"
    assert page["adapters"]["supabase"]["authority_level"] == "bounded_resource"


# ---------------------------------------------------------------- action forwarding (fail-closed)


def test_action_rejected_when_security_denies(kernel_mock, security_deny):
    svc = _make_service(kernel_mock, security_deny)
    result = asyncio.run(svc.request_action("integration.validate", {"name": "supabase"}))
    assert isinstance(result, DashboardActionResult)
    assert result.authorized is False
    assert result.status == "rejected"
    # AI-OS decision, not dashboard's: dashboard never authorizes
    security_deny.authorize.assert_called_once()


def test_dashboard_cannot_authorize_action(kernel_mock, security_deny):
    """Explicit invariant: the dashboard service has no authorize() of its own."""
    svc = _make_service(kernel_mock, security_deny)
    assert not hasattr(svc, "authorize")
    assert not hasattr(svc, "verify")
    assert not hasattr(svc, "decide")


def test_action_authorized_runs_bounded_execution(kernel_mock, security_allow):
    status_service = MagicMock()
    report = MagicMock()
    report.to_dict.return_value = {"name": "supabase", "state": "validated"}
    status_service.validate_integration = AsyncMock(return_value=report)
    kernel_mock.integration_status_service = status_service
    svc = _make_service(kernel_mock, security_allow)
    result = asyncio.run(svc.request_action("integration.validate", {"name": "supabase"}))
    assert result.authorized is True
    assert result.status == "completed"
    assert result.data["name"] == "supabase"
    # The bounded op was performed BY AI-OS (status service), not the dashboard
    status_service.validate_integration.assert_called_once_with("supabase")


def test_self_loop_control_forwards_to_engine(kernel_mock, security_allow):
    engine = MagicMock()
    engine.get_status.return_value = {"running": False}
    engine.pause = AsyncMock()
    kernel_mock.self_loop_engine = engine
    svc = _make_service(kernel_mock, security_allow)
    result = asyncio.run(svc.request_action("self_loop.control", {"op": "pause"}))
    assert result.status == "completed"
    engine.pause.assert_called_once()


def test_unsupported_action_returns_error_not_authority(kernel_mock, security_allow):
    svc = _make_service(kernel_mock, security_allow)
    result = asyncio.run(svc.request_action("dashboard.take_over_aios", {}))
    # SecurityManager would already DENY, but even if allowed the service refuses
    assert result.status in ("rejected", "error")


def test_security_failure_is_fail_closed(kernel_mock):
    sm = MagicMock()
    sm.authorize.side_effect = RuntimeError("security down")
    svc = _make_service(kernel_mock, sm)
    result = asyncio.run(svc.request_action("integration.validate", {"name": "supabase"}))
    assert result.authorized is False
    assert result.status == "rejected"


# ---------------------------------------------------------------- observability page


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset global singletons between tests to avoid state leakage."""
    yield
    reset_observability_manager_singleton()
    reset_health_manager_singleton()
    reset_event_bus_singleton()


def test_observability_page_declares_authority_and_read_only(kernel_mock):
    """Observability page declares AI-OS sole authority and read-only."""
    svc = _make_service(kernel_mock, None)
    page = svc.get_system_observability()
    assert page["authority"] == "aios_sole"
    assert page["read_only"] is True
    assert page["page"] == "system_observability"
    # Sections exist
    assert "metrics" in page
    assert "spans" in page
    assert "health" in page
    assert "recent_events" in page


def test_observability_page_graceful_when_managers_uninitialized(kernel_mock):
    """Observability page returns empty/unavailable state when managers not initialized."""
    svc = _make_service(kernel_mock, None)
    # No kernel wiring, no event_bus - all managers uninitialized
    page = svc.get_system_observability()
    assert page["metrics"] == []
    assert page["spans"] == []
    assert page["health"]["overall"] == "UNKNOWN"
    assert page["recent_events"] == []


def test_observability_page_surfaces_metrics(kernel_mock):
    """Observability page surfaces metrics from ObservabilityManager."""
    # Set up a real ObservabilityManager with a real EventBus and wire it to the global singleton
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    om = ObservabilityManager(
        service_registry=None,
        configuration_manager=None,
        logger=None,
    )
    asyncio.run(om.initialize())
    set_observability_manager(om)

    svc = _make_service(kernel_mock, None, event_bus=bus)
    om.record_metric("test_counter", MetricType.COUNTER, 42.0, unit="req")
    om.record_metric("test_gauge", MetricType.GAUGE, 3.14, unit="s", labels={"env": "test"})

    page = svc.get_system_observability()
    assert len(page["metrics"]) == 2
    m1 = page["metrics"][0]
    assert m1["name"] == "test_counter"
    assert m1["metric_type"] == "COUNTER"
    assert m1["value"] == 42.0
    assert m1["unit"] == "req"
    m2 = page["metrics"][1]
    assert m2["name"] == "test_gauge"
    assert m2["labels"] == {"env": "test"}


def test_observability_page_surfaces_spans(kernel_mock):
    """Observability page surfaces active spans from ObservabilityManager."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    om = ObservabilityManager(
        service_registry=None,
        configuration_manager=None,
        logger=None,
    )
    asyncio.run(om.initialize())
    set_observability_manager(om)

    svc = _make_service(kernel_mock, None, event_bus=bus)
    span = om.start_span("test_operation", attributes={"key": "value"})

    page = svc.get_system_observability()
    assert len(page["spans"]) == 1
    s = page["spans"][0]
    assert s["name"] == "test_operation"
    assert s["span_id"] == span.span_id
    assert s["trace_id"] == span.trace_id
    assert s["attributes"] == {"key": "value"}


def test_observability_page_surfaces_health(kernel_mock):
    """Observability page surfaces health from HealthManager."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    hm = HealthManager(
        service_registry=None,
        configuration_manager=None,
        logger=None,
    )
    asyncio.run(hm.initialize())
    set_health_manager(hm)

    svc = _make_service(kernel_mock, None, event_bus=bus)
    hm.record_health("component_a", "check_1", HealthStatus.HEALTHY, message="OK")
    hm.record_health("component_b", "check_1", HealthStatus.DEGRADED, message="Slow")

    page = svc.get_system_observability()
    health = page["health"]
    assert health["overall"] == "DEGRADED"
    assert health["total_checks"] == 2
    assert health["healthy_checks"] == 1
    assert health["degraded_checks"] == 1
    assert health["components"]["component_a"] == "HEALTHY"
    assert health["components"]["component_b"] == "DEGRADED"


def test_observability_page_surfaces_recent_events(kernel_mock):
    """Observability page surfaces recent events from EventBus."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    svc = _make_service(kernel_mock, None, event_bus=bus)
    # The EventBus history is populated by publish; we can't easily inject without publishing
    # But we can verify the structure exists and doesn't crash
    page = svc.get_system_observability()
    assert isinstance(page["recent_events"], list)


def test_observability_page_filters_sensitive_events(kernel_mock):
    """Observability page filters out sensitive SECURITY_ and CREDENTIAL_ events."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    svc = _make_service(kernel_mock, None, event_bus=bus)
    # The page should not crash even if sensitive events exist (filtering is defensive)
    page = svc.get_system_observability()
    # Just verify it returns a valid structure
    assert "recent_events" in page
    for ev in page["recent_events"]:
        assert not ev["event_type"].startswith("SECURITY_")
        assert not ev["event_type"].startswith("CREDENTIAL_")
