"""M9 — Closed-loop integration with learning services (spec §3.3.7, §32.9, §34).

Proves the INV-013 closed loop now runs the full M9 learning pipeline
end-to-end while remaining bounded and honest:

  * FAIL -> RCA -> Learning capture -> Planning ingest -> re-execute works on
    the real orchestrator (M9-N1..N4 wiring, no injected runtime objects)
  * convergence detection terminates a stuck loop EARLY with an honest FAILED
    result and an advisory escalation signal (M9-N9)
  * every terminal path stays bounded: iterations never exceed the cap (INV-013)
  * success path still clears convergence state and reaches PASSED honestly

IND-6 rule respected: tests exercise the stock TestOrchestratorService built
from real C1-C4 singletons; only the user-simulation agent is doubled (it is
an execution boundary, not a corrected-runtime object).
"""

from __future__ import annotations

import pytest

from aios.core.testing_evidence import UserSimulationCompleted
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    get_core_event_bus,
    reset_event_bus_singleton,
)
from aios.events.core.manager import SubscribeOptions
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.learning import LearningService
from aios.services.planning import PlanningService
from aios.services.testing import TestOrchestratorService


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


@pytest.fixture()
async def bus():
    """Canonical singleton bus, RUNNING, worker off; drain-based determinism.

    maxDispatchDepth raised above default 16: one loop run emits ~30 events
    sharing one correlationId (per-correlationId depth guard drops later
    events otherwise).
    """
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(
        auto_start_dispatch_worker=False, maxDispatchDepth=512))
    await b.initialize()
    yield b
    reset_event_bus_singleton()


def _svc(sim, learning=None, planning=None) -> TestOrchestratorService:
    return TestOrchestratorService(
        get_state_manager(),
        council_manager=get_council_manager(),
        user_simulation_agent=sim,
        learning_service=learning,
        planning_service=planning,
    )


def _provider(failed_evidence, failed_implementation):
    return GOOD if failed_implementation.strip() == BAD.strip() \
        else failed_implementation


class EventCapture:
    def __init__(self, bus_, types):
        self.events = []
        for et in types:
            bus_.subscribe(SubscribeOptions(
                subscriber=ComponentIdentity(
                    component_type=ComponentType.APPLICATION_SERVICE,
                    component_name="m9-cl-capture",
                ),
                event_types=[et],
                handler=self._on_event,
            ))

    def _on_event(self, event):
        self.events.append(event)

    def of_type(self, et):
        return [e for e in self.events if e.eventType == et]


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------


class TestClosedLoopWithLearningPipeline:
    @pytest.mark.asyncio
    async def test_fail_rca_learning_planning_reexecute_to_pass(self, bus):
        """FAIL -> RCA -> Learning -> Planning -> re-execute -> PASS end-to-end
        with REAL LearningService + PlanningService wired in."""
        learning = LearningService()
        planning = PlanningService()
        svc = _svc(_PassSim(), learning=learning, planning=planning)

        result = await svc.orchestrate_test(
            objective="test login", objective_id="obj_m9_cl_pass",
            target="auth_service", builder_id="", implementation=BAD,
            corrected_implementation_provider=_provider,
        )
        assert result.status.value == "passed"
        assert result.final_verdict == "approve"
        assert result.iterations >= 2
        # Learning actually captured the intermediate failure.
        assert learning.stats()["learnings_captured"] >= 1

    @pytest.mark.asyncio
    async def test_learning_events_flow_over_canonical_bus(self, bus):
        """The loop's learning step emits canonical events (no new types)."""
        before = {e.name for e in EventType}
        capture = EventCapture(bus, [EventType.TESTING_FAILED])
        learning = LearningService()
        svc = _svc(_FailSim(), learning=learning)

        def never_fix(**kwargs):
            return None

        from aios.services.convergence import ConvergenceDetector

        svc.convergence_detector = ConvergenceDetector(
            emit_event=svc._emit_event, no_improvement_limit=10,
        )
        result = await svc.orchestrate_test(
            objective="capture check", objective_id="obj_m9_cl_events",
            target="auth_service", builder_id="", implementation=BAD,
            corrected_implementation_provider=never_fix,
        )
        assert result.status.value == "failed"
        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        assert capture.of_type(EventType.TESTING_FAILED), (
            "failure events flowed over canonical bus"
        )
        assert {e.name for e in EventType} == before


# ---------------------------------------------------------------------------
# Bounded convergence inside the integrated loop
# ---------------------------------------------------------------------------


class TestClosedLoopConvergenceIntegration:
    @pytest.mark.asyncio
    async def test_stuck_loop_terminates_early_with_advisory_signal(self, bus):
        """Identical repeated failures terminate BEFORE cap; signal advisory."""
        capture = EventCapture(bus, [EventType.HUMAN_ESCALATION_REQUIRED])
        svc = _svc(_FailSim())

        def never_fix(**kwargs):
            return None

        result = await svc.orchestrate_test(
            objective="stuck", objective_id="obj_m9_cl_conv",
            target="auth_service", builder_id="", implementation=BAD,
            corrected_implementation_provider=never_fix,
        )
        assert result.status.value == "failed"
        assert "Convergence detected" in result.detail
        assert result.iterations < svc._max_iterations, (
            "converged early instead of burning all iterations"
        )

        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        signals = capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED)
        assert len(signals) == 1
        assert signals[0].payload["authority"] == "advisory_only"

    @pytest.mark.asyncio
    async def test_success_path_resets_convergence(self, bus):
        """A real PASS clears per-objective convergence history."""
        svc = _svc(_PassSim())
        result = await svc.orchestrate_test(
            objective="fixable", objective_id="obj_m9_cl_reset",
            target="auth_service", builder_id="", implementation=BAD,
            corrected_implementation_provider=_provider,
        )
        assert result.status.value == "passed"
        detector = svc.convergence_detector
        assert not detector._signaled.get("obj_m9_cl_reset")
