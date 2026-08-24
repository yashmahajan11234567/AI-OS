"""
M7-J — Seeded defect detection integration tests.

Defines 9 seeded defects, each detectable by a real agency adapter / perspective
(NOT by name matching). The orchestrator must surface each as a failing
``TestingEvidence`` record. This proves the multi-perspective system catches
genuine, varied defects rather than heuristics.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.core.testing_evidence import UserSimulationCompleted, Provenance, TestingEvidence
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.testing import TestOrchestratorService, PERSPECTIVE_IDS


class _FailSim:
    async def simulate(self, *a, **k):
        # A broken app from the user's perspective.
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=0.1, workflow_success=False,
            usability_blockers=["submit button did nothing"],
            navigation_failures=["landing page error"],
            missing_feedback=["no error message shown"])


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


# 9 seeded defects, each mapped to the perspective that detects it.
SEEDED_DEFECTS = {
    "security_agency": (
        'def login(u, p):\n'
        "    q = \"SELECT * FROM users WHERE name='\" + u + \"'\"\n"
        '    return db.execute(q)\n'
    ),
    "performance_agency": (
        'def poll():\n'
        '    while True:\n'
        '        requests.get("http://slow")\n'
    ),
    "chaos_agency": (
        'def risky():\n'
        '    try:\n'
        '        do_thing()\n'
        '    except:\n'
        '        pass\n'
    ),
    "accessibility_agency": (
        '<html><body><img src="avatar.png"></body></html>\n'
    ),
    "documentation_agency": (
        'def handler(req):\n'
        '    return 1\n'
    ),
    "concurrency_agency": (
        'shared = 0\n'
        'def inc():\n'
        '    global shared\n'
        '    shared += 1\n'
    ),
    "bug_hunter_agency": (
        'def f(x):\n'
        '    return process(x)\n'
    ),
    "architecture_agency": (
        'import os\n'
        'import sys\n'
        'import subprocess\n'
    ),
    "user_simulation": (
        'def broken_app():\n'
        '    raise RuntimeError("cannot start")\n'
    ),
}


async def _dispatch_single(svc, perspective, impl):
    return (await svc._dispatch_all(
        target="app", perspectives=[perspective],
        correlation_id=str(uuid4()), implementation=impl,
        app_url="http://app", user_goal="log in",
        exploration_brief="explore", builder_id=""))[0]


async def test_all_nine_seeded_defects_are_detected():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_FailSim())
    failures = {}
    for perspective, impl in SEEDED_DEFECTS.items():
        ev = await _dispatch_single(svc, perspective, impl)
        if ev.verdict != "fail":
            failures[perspective] = ev.verdict
    assert not failures, f"Seeded defects not detected by: {failures}"
    assert len(SEEDED_DEFECTS) == 9


async def test_defect_evidence_has_provenance():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_FailSim())
    ev = await _dispatch_single(svc, "security_agency", SEEDED_DEFECTS["security_agency"])
    assert ev.verdict == "fail"
    assert ev.severity in ("high", "critical")
    assert ev.provenance.source == "security_agency"
    ev.provenance.validate()


async def test_clean_implementation_passes_all_perspectives():
    clean = (
        'def login(user, pwd):\n'
        '    """Authenticate a user."""\n'
        '    if not authorize(user, "login", "auth_service"):\n'
        '        return None\n'
        '    return db.query(user, pwd)\n'
    )
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_FailSim())
    # Use a passing sim so user_simulation perspective is clean.
    class _PassSim:
        async def simulate(self, *a, **k):
            return UserSimulationCompleted(
                goal="log in", goal_completion_pct=1.0, workflow_success=True)
    svc._user_sim = _PassSim()
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=clean,
        app_url="", user_goal="", exploration_brief="", builder_id="")
    # With the clean impl, the 8 adapters + passing sim should all be clean.
    failing = [e for e in evidence if e.verdict == "fail"]
    assert failing == [], f"Unexpected failures on clean impl: {[e.perspective for e in failing]}"
