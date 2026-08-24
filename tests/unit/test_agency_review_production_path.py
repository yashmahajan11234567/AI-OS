"""
M7-C — Agency production-path tests (anti-cheating).

These tests exercise the REAL production seam end-to-end:

    AIAgencyService.review(agency_type, request)
        -> Agency.review(request)
            -> BaseAgency._run_adapter(request)
                -> real M7 execution adapter (.execute)
            -> BaseAgency._evidence_to_response(...)
        -> AgencyResponse

They do NOT bypass the seam with a mock adapter or inject a test-only DI. No
canned evidence, no keyword detection. Two anti-cheating guarantees per agency:

  * ANTI-CHEAT (name without defect): a target whose NAME contains no defect
    keyword, but whose IMPLEMENTATION carries the real defect, MUST be detected
    (detection is content-driven, not name-matched).
  * CLEAN (name with keyword): a target whose NAME contains a defect keyword,
    but whose IMPLEMENTATION is clean, MUST NOT be flagged (name is not evidence).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.core.ai_agency import (
    AgencyRequest,
    AgencyType,
    AIAgencyService,
    Verdict,
)
from aios.core.security_manager import SecurityManager
from aios.events.core.bus import EventBus, reset_event_bus_singleton


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


def _request(target: str, impl: str, agency: AgencyType) -> AgencyRequest:
    return AgencyRequest(
        request_id=f"req_{uuid4().hex[:12]}",
        agency_type=agency,
        target=target,
        context={"implementation": impl, "builder_id": ""},
        correlation_id=str(uuid4()),
    )


def _service() -> AIAgencyService:
    # Explicit None security_manager => no gate, matching production adapter
    # semantics (the adapter runs its tool directly). This is the real seam.
    return AIAgencyService(security_manager=None)


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------


async def test_security_anticheat_name_without_keyword_but_vuln_detected():
    svc = _service()
    # Target name is harmless; implementation has a real SQL injection.
    req = _request(
        "clean_feature_handler",
        "q = \"SELECT * FROM users WHERE name='\" + u + \"'\"; db.execute(q)",
        AgencyType.SECURITY,
    )
    resp = await svc.review(AgencyType.SECURITY, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("sql_injection" in f["type"] for f in resp.findings)


async def test_security_clean_name_with_keyword_but_safe():
    svc = _service()
    # Target name mentions "sql" but implementation contains no SQL/XSS/secret/
    # cmd-injection/deserialization patterns the real adapter scans for.
    req = _request(
        "sql_repository_clean",
        "def get(uid):\n    return lookup_user(uid)\n",
        AgencyType.SECURITY,
    )
    resp = await svc.review(AgencyType.SECURITY, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("sql_injection" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# PERFORMANCE
# ---------------------------------------------------------------------------


async def test_performance_anticheat_name_without_keyword_but_blocking():
    svc = _service()
    req = _request(
        "quiet_worker",
        "while True:\n    requests.get(url)\n",
        AgencyType.PERFORMANCE,
    )
    resp = await svc.review(AgencyType.PERFORMANCE, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("blocking_io_in_loop" in f["type"] for f in resp.findings)


async def test_performance_clean_name_with_keyword_but_fast():
    svc = _service()
    req = _request(
        "slow_report_generator",  # name suggests slowness, impl is fine
        "return [x * 2 for x in items]",
        AgencyType.PERFORMANCE,
    )
    resp = await svc.review(AgencyType.PERFORMANCE, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("blocking_io_in_loop" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# CHAOS
# ---------------------------------------------------------------------------


async def test_chaos_anticheat_name_without_keyword_but_swallowed():
    svc = _service()
    req = _request(
        "normalizer_service",
        "try:\n    risky()\nexcept:\n    pass\n",
        AgencyType.CHAOS,
    )
    resp = await svc.review(AgencyType.CHAOS, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("swallow" in f["type"] for f in resp.findings)


async def test_chaos_clean_name_with_keyword_but_handled():
    svc = _service()
    req = _request(
        "chaos_experiment_runner",  # name suggests chaos, impl handles errors
        "def f():\n    try:\n        return compute()\n    except ValueError:\n        return None\n",  # noqa: E501
        AgencyType.CHAOS,
    )
    resp = await svc.review(AgencyType.CHAOS, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("swallow" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# ACCESSIBILITY
# ---------------------------------------------------------------------------


async def test_accessibility_anticheat_name_without_keyword_but_missing_alt():
    svc = _service()
    req = _request(
        "card_component",  # not named "accessibility"
        "<html><body><img src='avatar.png'></body></html>",
        AgencyType.ACCESSIBILITY,
    )
    resp = await svc.review(AgencyType.ACCESSIBILITY, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("image-alt" in f["type"] or "axe" in f["type"] for f in resp.findings)


async def test_accessibility_clean_name_with_keyword_but_ok():
    svc = _service()
    req = _request(
        "accessibility_util",  # name mentions accessibility, backend only
        "def handler(req):\n    return req.json()\n",
        AgencyType.ACCESSIBILITY,
    )
    resp = await svc.review(AgencyType.ACCESSIBILITY, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("image-alt" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# DOCUMENTATION
# ---------------------------------------------------------------------------


async def test_documentation_anticheat_name_without_keyword_but_undocumented():
    svc = _service()
    req = _request(
        "router",  # not named "docs"
        "def handler(req):\n    return 1\n",
        AgencyType.DOCUMENTATION,
    )
    resp = await svc.review(AgencyType.DOCUMENTATION, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any(f["type"] == "missing_docstring" for f in resp.findings)


async def test_documentation_clean_name_with_keyword_but_documented():
    svc = _service()
    req = _request(
        "documentation_generator",  # name mentions docs, impl is documented
        'def handler(req):\n    """Doc."""\n    return 1\n',
        AgencyType.DOCUMENTATION,
    )
    resp = await svc.review(AgencyType.DOCUMENTATION, req)
    assert resp.verdict != Verdict.REJECT
    assert not any(f["type"] == "missing_docstring" for f in resp.findings)


# ---------------------------------------------------------------------------
# CONCURRENCY
# ---------------------------------------------------------------------------


async def test_concurrency_anticheat_name_without_keyword_but_unsafe_shared():
    svc = _service()
    req = _request(
        "counter",
        "shared = 0\ndef inc():\n    global shared\n    shared += 1\n",
        AgencyType.CONCURRENCY,
    )
    resp = await svc.review(AgencyType.CONCURRENCY, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("unsynchronized_shared_state" in f["type"] for f in resp.findings)


async def test_concurrency_clean_name_with_keyword_but_safe():
    svc = _service()
    req = _request(
        "concurrency_helper",  # name mentions concurrency, impl is safe
        "import asyncio\nasync def f(q):\n    return await q.get()\n",
        AgencyType.CONCURRENCY,
    )
    resp = await svc.review(AgencyType.CONCURRENCY, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("unsynchronized_shared_state" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# BUG HUNTER
# ---------------------------------------------------------------------------


async def test_bug_hunter_anticheat_name_without_keyword_but_unvalidated():
    svc = _service()
    req = _request(
        "transform",
        "def f(x):\n    return process(x)\n",
        AgencyType.BUG_HUNTER,
    )
    resp = await svc.review(AgencyType.BUG_HUNTER, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("fuzz_crash" in f["type"] or "unvalidated" in f["type"] for f in resp.findings)


async def test_bug_hunter_clean_name_with_keyword_but_validated():
    svc = _service()
    req = _request(
        "fuzzer_harness",  # name suggests fuzzing, impl validates input
        "def f(x):\n    if not isinstance(x, int): raise ValueError\n    return process(x)\n",
        AgencyType.BUG_HUNTER,
    )
    resp = await svc.review(AgencyType.BUG_HUNTER, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("fuzz_crash" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# ARCHITECTURE
# ---------------------------------------------------------------------------


async def test_architecture_anticheat_name_without_keyword_but_broad_coupling():
    svc = _service()
    req = _request(
        "helper",
        "import os\nimport sys\nimport subprocess\n",
        AgencyType.ARCHITECTURE,
    )
    resp = await svc.review(AgencyType.ARCHITECTURE, req)
    assert resp.verdict in (Verdict.REJECT, Verdict.CONDITIONAL)
    assert any("broad_coupling" in f["type"] for f in resp.findings)


async def test_architecture_clean_name_with_keyword_but_focused():
    svc = _service()
    req = _request(
        "architecture_diagram_tool",  # name mentions architecture, impl is focused
        "import math\n\ndef f():\n    return math.pi\n",
        AgencyType.ARCHITECTURE,
    )
    resp = await svc.review(AgencyType.ARCHITECTURE, req)
    assert resp.verdict != Verdict.REJECT
    assert not any("broad_coupling" in f["type"] for f in resp.findings)


# ---------------------------------------------------------------------------
# SecurityAgency honors an explicit SecurityManager gate (DENY => CONDITIONAL
# via SKIP, never a fabricated APPROVE)
# ---------------------------------------------------------------------------


async def test_security_agency_respects_explicit_deny_gate():
    sm = SecurityManager()  # fail-closed by default -> DENY for testing_council
    svc = AIAgencyService(security_manager=sm)
    req = _request(
        "auth_service",
        "q = \"SELECT * FROM users WHERE name='\" + u + \"'\"; db.execute(q)",
        AgencyType.SECURITY,
    )
    resp = await svc.review(AgencyType.SECURITY, req)
    # The gate DENIES the scan, so no evidence is produced; the verdict must
    # never be a clean APPROVE of a known-vulnerable target.
    assert resp.verdict != Verdict.APPROVE
