"""
M7 — Integration: Multi-perspective dispatch + provenance.

Proves the orchestrator dispatches ALL 9 agency perspectives + the
UserSimulationAgent (10th) in parallel, that every evidence record carries
complete, immutable provenance, and that the assembly is evidence-first.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.core.testing_evidence import (
    Provenance, UserSimulationCompleted, PerspectiveVerdict,
)
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.testing import (
    TestOrchestratorService, PERSPECTIVE_IDS,
)


class _PassSim:
    async def simulate(self, *a, **k):
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=1.0, workflow_success=True)


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


def _clean_impl():
    return (
        'def login(user, pwd):\n'
        '    """Authenticate a user."""\n'
        '    if not authorize(user, "login", "auth_service"):\n'
        '        return None\n'
        '    return db.query(user, pwd)\n'
    )


async def test_all_perspectives_dispatched():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    perspectives = {e.perspective for e in evidence}
    assert len(evidence) == len(PERSPECTIVE_IDS)
    assert perspectives == set(PERSPECTIVE_IDS)


async def test_every_evidence_has_complete_provenance():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    for e in evidence:
        prov = e.provenance
        assert prov.source
        assert prov.worker
        assert prov.session
        assert prov.timestamp
        assert prov.environment
        assert prov.correlation_id
        # Provenance is validated (complete).
        prov.validate()


async def test_user_simulation_evidence_is_observations_only():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=["user_simulation"],
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="http://app", user_goal="log in",
        exploration_brief="explore", builder_id="")
    assert len(evidence) == 1
    assert evidence[0].perspective == "user_simulation"
    # Normalized to a verdict by AI-OS (trusted), from observations only.
    assert evidence[0].verdict in {v.value for v in PerspectiveVerdict}


async def test_evidence_is_immutable_after_normalization():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=["security_agency"],
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    ev = evidence[0]
    with pytest.raises(Exception):
        ev.severity = "critical"
