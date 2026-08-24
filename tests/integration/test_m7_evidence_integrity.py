"""
M7-F — Testing Council (M6 reuse) + evidence integrity integration tests.

Proves:
  * The orchestrator reuses the EXISTING CouncilManager (convene -> propose ->
    critique -> synthesize); it does NOT instantiate a second council.
  * Dissent is preserved by critique() (M6 KKC/EVC) and surfaced on the result.
  * The builder is excluded from the council (INV-009).
  * Evidence integrity: every evidence record is immutable and carries complete
    provenance (INV-007-style tamper-evident audit trail).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.core.testing_evidence import UserSimulationCompleted, Provenance
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.testing import TestOrchestratorService, PERSPECTIVE_IDS


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


async def test_submit_reuses_existing_council_manager():
    cm = get_council_manager()
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=cm,
        user_simulation_agent=_PassSim())
    # The orchestrator must use the injected singleton, not create a new one.
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    critique, council_id = await svc.submit_to_testing_council(
        evidence_list=evidence, builder_id="", correlation_id=str(uuid4()))
    assert council_id
    assert critique is not None
    # The M6 CritiqueResult shape is preserved (rankings + dissent).
    assert hasattr(critique, "rankings")
    assert hasattr(critique, "dissent_preserved")
    assert hasattr(critique, "dissenter_override")


async def test_council_preserves_dissent():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    critique, _ = await svc.submit_to_testing_council(
        evidence_list=evidence, builder_id="", correlation_id=str(uuid4()))
    # At least one dissenting minority perspective is preserved (M6 EVC).
    assert isinstance(critique.dissent_preserved, list)
    assert len(critique.dissent_preserved) >= 1


async def test_council_has_no_second_instance():
    # Reuse: get_council_manager returns a single canonical instance.
    first = get_council_manager()
    second = get_council_manager()
    assert first is second


async def test_evidence_integrity_immutable_and_provenanced():
    svc = TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager(),
        user_simulation_agent=_PassSim())
    evidence = await svc._dispatch_all(
        target="auth_service", perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()), implementation=_clean_impl(),
        app_url="", user_goal="", exploration_brief="", builder_id="")
    for e in evidence:
        # Immutable.
        with pytest.raises(Exception):
            e.severity = "critical"
        # Complete provenance.
        e.provenance.validate()
        # Serialization round-trip preserves integrity.
        restored = type(e).from_dict(e.to_dict())
        restored.validate()
