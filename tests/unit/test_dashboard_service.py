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
