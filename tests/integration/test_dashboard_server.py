"""
M13 — Dashboard HTTP server integration tests (T2-authored transport).

Verifies the bounded localhost transport correctly:
  * GET  /api/pages returns the read-only snapshot (authority declared)
  * POST /api/action forwards to the gated DashboardService and never authorizes
  * GET  / serves the static dashboard UI
The server holds NO authority; all actions re-run the SecurityManager gate.
"""

from __future__ import annotations

import asyncio
import threading
import time
import urllib.request

import pytest

from aios.core.security_manager import SecurityDecision
from aios.services.dashboard_service import DashboardService
from aios.services.dashboard_server import DashboardHTTPServer


class _FakeKernel:
    terminal_contract_violations = []
    integration_status_service = None
    self_loop_engine = None


@pytest.fixture
def running_server():
    kernel = _FakeKernel()
    service = DashboardService(kernel=kernel, security_manager=None)
    server = DashboardHTTPServer(service, host="127.0.0.1", port=8799)
    server.start()
    # wait for bind
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:8799/api/pages", timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.05)
    yield server
    server.stop()


def test_get_pages_returns_readonly_snapshot(running_server):
    with urllib.request.urlopen("http://127.0.0.1:8799/api/pages", timeout=2) as resp:
        assert resp.headers.get("X-AIOS-Authority") == "aios_sole"
        data = __import__("json").loads(resp.read())
    assert data["authority_model"] == "aios_sole_authority"
    for name, page in data["pages"].items():
        assert page["read_only"] is True
        assert page["authority"] == "aios_sole"


def test_get_root_serves_ui(running_server):
    with urllib.request.urlopen("http://127.0.0.1:8799/", timeout=2) as resp:
        body = resp.read().decode("utf-8")
    assert "AI-OS Dashboard" in body
    assert "NON-AUTHORITATIVE" in body


def test_post_action_forwards_and_is_fail_closed_without_security(running_server):
    """With no SecurityManager, the gate defaults to DENY — server must not authorize."""
    payload = __import__("json").dumps({"action": "integration.validate", "params": {"name": "supabase"}}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8799/api/action", data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        data = __import__("json").loads(resp.read())
    assert data["authorized"] is False
    assert data["status"] == "rejected"
