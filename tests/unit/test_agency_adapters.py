"""
M7-C — Real agency execution adapter unit tests.

Proves each adapter performs REAL, content-driven detection (no target-name
heuristics) and returns a properly-shaped ExecutionResult. Also proves the
SecurityAgencyAdapter defers to SecurityManager authorization.

M8-T3: ArchitectureAgencyAdapter enhanced with optional GraphifyAdapter path.
"""

from __future__ import annotations

import pytest

from aios.adapters.base import ExecutionResult, ExecutionStatus
from aios.adapters.security_agency_adapter import SecurityAgencyAdapter, _default_static_analysis
from aios.adapters.performance_agency_adapter import PerformanceAgencyAdapter
from aios.adapters.chaos_agency_adapter import ChaosAgencyAdapter
from aios.adapters.accessibility_agency_adapter import AccessibilityAgencyAdapter
from aios.adapters.documentation_agency_adapter import DocumentationAgencyAdapter
from aios.adapters.concurrency_agency_adapter import ConcurrencyAgencyAdapter
from aios.adapters.bug_hunter_agency_adapter import BugHunterAgencyAdapter
from aios.adapters.architecture_agency_adapter import ArchitectureAgencyAdapter
from aios.core.security_manager import SecurityDecision


_CTX = lambda code: {"implementation": code, "target": "thing", "builder_id": ""}


# ---------------------------------------------------------------------------
# Security adapter: real content detection + SecurityManager integration
# ---------------------------------------------------------------------------

def test_security_detects_sql_injection():
    r = _default_static_analysis("t", _CTX("db.execute('SELECT * FROM users WHERE x=' + y)"))
    assert r.status == ExecutionStatus.FAILURE
    types = {f["type"] for f in r.findings}
    assert "sql_injection" in types


def test_security_reports_auth_surface_informational_not_failure():
    # A (secure) auth surface is desirable, not a defect.
    r = _default_static_analysis("t", _CTX("def login(u):\n    if not authorize(u): return None\n"))
    assert r.status == ExecutionStatus.SUCCESS
    assert r.metrics.get("auth_surface_present") is True


def test_security_adapter_defers_to_security_manager_denied():
    denied = {"security_scan": SecurityDecision.DENY}
    def fake_authorize(principal, action, resource, context=None):
        return denied.get(action, SecurityDecision.ALLOW)
    adapter = SecurityAgencyAdapter(security_manager=type("SM", (), {"authorize": staticmethod(fake_authorize)})())
    r = adapter.execute("auth_service", _CTX("x=1"))
    assert r.status == ExecutionStatus.SKIPPED
    assert r.raw.get("authorization") == SecurityDecision.DENY.value


def test_security_adapter_perspective_attribute():
    assert SecurityAgencyAdapter().perspective == "security"


# ---------------------------------------------------------------------------
# Performance adapter
# ---------------------------------------------------------------------------

def test_performance_detects_blocking_io_in_loop():
    r = PerformanceAgencyAdapter().execute("t", _CTX("while True:\n    requests.get(url)\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any(f["type"] == "blocking_io_in_loop" for f in r.findings)


def test_performance_clean_passes():
    r = PerformanceAgencyAdapter().execute("t", _CTX("return sum(xs)"))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Chaos adapter
# ---------------------------------------------------------------------------

def test_chaos_flags_swallowed_exception():
    r = ChaosAgencyAdapter().execute("t", _CTX("try:\n    risky()\nexcept:\n    pass\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("swallow" in f["type"] for f in r.findings)


def test_chaos_clean_passes():
    # No swallowed exception => graceful handling assumed present.
    r = ChaosAgencyAdapter().execute("t", _CTX("def f():\n    return compute()\n"))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Accessibility adapter
# ---------------------------------------------------------------------------

def test_accessibility_skips_non_ui_code():
    # Backend Python must NOT be flagged for missing HTML <label>.
    r = AccessibilityAgencyAdapter().execute("t", _CTX("def handler(req):\n    return req.json()\n"))
    assert r.status == ExecutionStatus.SUCCESS


def test_accessibility_flags_missing_alt_on_img():
    html = "<html><body><img src='a.png'></body></html>"
    r = AccessibilityAgencyAdapter().execute("t", _CTX(html))
    assert r.status == ExecutionStatus.FAILURE
    assert any("image-alt" in f["type"] for f in r.findings)


def test_accessibility_skips_playwright_when_none():
    # No playwright adapter injected → falls back to simulated scan
    adapter = AccessibilityAgencyAdapter()
    assert adapter._playwright_adapter is None
    html = "<html><body><img src='a.png'></body></html>"
    r = adapter.execute("t", _CTX(html))
    assert r.status == ExecutionStatus.FAILURE
    assert r.tool == "axe_core"  # Uses simulated, not playwright


def test_accessibility_with_playwright_fallback():
    # Playwright adapter provided but target has no markup → uses simulated
    class FakePA:
        pass
    adapter = AccessibilityAgencyAdapter(playwright_adapter=FakePA())
    r = adapter.execute("t", _CTX("def handler(req):\n    return req.json()\n"))
    assert r.status == ExecutionStatus.SUCCESS
    assert r.tool == "axe_core"  # Falls back to simulated for non-UI


# ---------------------------------------------------------------------------
# Documentation adapter
# ---------------------------------------------------------------------------

def test_documentation_flags_missing_docstring():
    r = DocumentationAgencyAdapter().execute("t", _CTX("def handler(req):\n    return 1\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any(f["type"] == "missing_docstring" for f in r.findings)


def test_documentation_clean_passes():
    r = DocumentationAgencyAdapter().execute(
        "t", _CTX('def handler(req):\n    """Doc."""\n    return 1\n'))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Concurrency adapter
# ---------------------------------------------------------------------------

def test_concurrency_flags_unsafe_shared_state():
    r = ConcurrencyAgencyAdapter().execute("t", _CTX("shared = 0\ndef inc():\n    global shared\n    shared += 1\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("unsynchronized_shared_state" in f["type"] for f in r.findings)


def test_concurrency_flags_await_outside_async():
    r = ConcurrencyAgencyAdapter().execute("t", _CTX("def f():\n    x = await get()\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("await_outside_async" in f["type"] for f in r.findings)


def test_concurrency_clean_passes():
    r = ConcurrencyAgencyAdapter().execute("t", _CTX("import asyncio\nasync def f(q):\n    return await q.get()\n"))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Bug hunter adapter
# ---------------------------------------------------------------------------

def test_bug_hunter_flags_unvalidated_entrypoint():
    r = BugHunterAgencyAdapter().execute("t", _CTX("def f(x):\n    return process(x)\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("fuzz_crash" in f["type"] for f in r.findings)


def test_bug_hunter_validated_passes():
    r = BugHunterAgencyAdapter().execute(
        "t", _CTX("def f(x):\n    if not isinstance(x, int): raise ValueError\n    return process(x)\n"))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Architecture adapter
# ---------------------------------------------------------------------------

def test_architecture_flags_broad_coupling():
    r = ArchitectureAgencyAdapter().execute("t", _CTX("import os\nimport sys\nimport subprocess\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("broad_coupling" in f["type"] for f in r.findings)


def test_architecture_clean_passes():
    r = ArchitectureAgencyAdapter().execute("t", _CTX("import math\n\ndef f():\n    return math.pi\n"))
    assert r.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# M8-T3: ArchitectureAgencyAdapter with Graphify integration
# ---------------------------------------------------------------------------

def test_architecture_adapter_accepts_graphify_adapter():
    """ArchitectureAgencyAdapter accepts optional GraphifyAdapter parameter."""
    class FakeGraphifyAdapter:
        def is_connected(self):
            return True

    adapter = ArchitectureAgencyAdapter(graphify_adapter=FakeGraphifyAdapter())
    assert adapter._graphify_adapter is not None
    assert adapter._graphify_adapter.is_connected() is True


def test_architecture_adapter_graceful_degradation_when_graphify_unavailable():
    """When GraphifyAdapter is provided but not connected, falls back to text scanner."""
    class FakeGraphifyAdapter:
        def is_connected(self):
            return False

    adapter = ArchitectureAgencyAdapter(graphify_adapter=FakeGraphifyAdapter())
    # Should fall back to text scanner (broad_coupling detection)
    r = adapter.execute("t", _CTX("import os\nimport sys\nimport subprocess\n"))
    assert r.status == ExecutionStatus.FAILURE
    assert any("broad_coupling" in f["type"] for f in r.findings)
    # Tool name should indicate fallback
    assert "text_fallback" in r.tool or r.tool == "graphify_mcp_text_fallback"


def test_architecture_adapter_without_graphify_still_works():
    """ArchitectureAgencyAdapter works without GraphifyAdapter (backward compatibility)."""
    adapter = ArchitectureAgencyAdapter()
    r = adapter.execute("t", _CTX("import math\n\ndef f():\n    return math.pi\n"))
    assert r.status == ExecutionStatus.SUCCESS
    assert adapter._graphify_adapter is None


# ---------------------------------------------------------------------------
# ExecutionResult shape invariant
# ---------------------------------------------------------------------------

def test_execution_result_shape():
    r = ExecutionResult(tool="t", status=ExecutionStatus.SUCCESS, findings=[], metrics={"a": 1})
    assert r.status == ExecutionStatus.SUCCESS
    assert r.findings == []
    assert r.metrics["a"] == 1
