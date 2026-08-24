"""
M7-I — Closed-loop integration (bounded).

Proves:
  * STATUS PASSED / verdict APPROVE is reached once the seeded defect is fixed
    (FAIL -> RCA -> Learning -> Planning -> re-execute -> retest -> PASS).
  * The loop is BOUNDED: without a corrected implementation it terminates at
    STATUS FAILED with REAL evidence (honest failure, not a false PASS).
  * Iteration cap is respected (INV-013).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from aios.core.testing_evidence import UserSimulationCompleted
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.testing import TestOrchestratorService, PERSPECTIVE_IDS


BAD = '''def login(user, pwd):
    q = "SELECT * FROM users WHERE name='" + user + "'"
    return db.execute(q)
'''

GOOD = '''def login(user, pwd):
    """Authenticate a user against the auth service."""
    if not authorize(user, 'login', 'auth_service'):
        return None
    return db.query(user, pwd)
'''


class _PassSim:
    async def simulate(self, *a, **k):
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=1.0, workflow_success=True)


class _FailSim:
    async def simulate(self, *a, **k):
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=0.2, workflow_success=False,
            usability_blockers=["submit button missing"])


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


def _svc(sim, **kw):
    return TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=sim, **kw)


def _provider(failed_evidence, failed_implementation):
    return GOOD if failed_implementation.strip() == BAD.strip() else failed_implementation


async def test_closed_loop_converges_to_pass():
    svc = _svc(_PassSim())
    result = await svc.orchestrate_test(
        objective="test login", objective_id="obj_bad", target="auth_service",
        builder_id="", implementation=BAD,
        corrected_implementation_provider=_provider,
    )
    assert result.status.value == "passed"
    assert result.final_verdict == "approve"
    assert result.iterations >= 2  # at least one rejection + one corrected pass


async def test_closed_loop_honest_failure_without_provider():
    svc = _svc(_FailSim())
    result = await svc.orchestrate_test(
        objective="test login", objective_id="obj_bad2", target="auth_service",
        builder_id="", implementation=BAD,
    )
    assert result.status.value == "failed"
    # Real evidence is surfaced (never silently empty / false PASS).
    assert len(result.evidence) > 0
    assert any(e.verdict == "fail" for e in result.evidence)


async def test_closed_loop_respects_iteration_cap():
    # Provider that never fixes -> bounded termination.
    def never_fix(failed_evidence, failed_implementation):
        return None
    svc = _svc(_FailSim())
    result = await svc.orchestrate_test(
        objective="test login", objective_id="obj_cap", target="auth_service",
        builder_id="", implementation=BAD,
        corrected_implementation_provider=never_fix,
    )
    assert result.iterations <= svc._max_iterations
    assert result.status.value == "failed"
