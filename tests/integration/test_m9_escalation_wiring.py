"""M9-N11 — Human escalation wiring tests (spec §3.3.9, §32.11, §34).

Bound exhaustion in learning-adjacent bounded loops must route to the
EXISTING human-escalation path. Coverage:

  * SelfPromptingService (ADR #10 bounds): depth/token/citation bound errors
    are still raised fail-closed (SelfPromptBoundExceededError), AND a canonical
    HUMAN_ESCALATION_REQUIRED event with recovery_action=escalate_to_human is
    emitted (best-effort; emission failure never masks the raise)
  * closed loop (INV-013 bounds): iteration-cap / budget-exhausted terminal
    paths invoke WorkflowManager._escalate_to_human — observable via the
    CHECKPOINT_CREATED event carrying recovery_action="escalate_to_human"
  * no new EventType is introduced by any of this wiring
  * advisory-only: escalation signals carry authority=advisory_only and never
    mutate verdicts or bypass Council/Judge/SecurityManager
"""

from __future__ import annotations

from uuid import uuid4

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
from aios.core.council_manager import get_council_manager, set_council_manager
from aios.services.self_prompting import (
    SelfPromptConfig,
    SelfPromptingService,
    SelfPromptBoundExceededError,
)
from aios.services.testing import TestOrchestratorService


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
async def bus():
    """Canonical singleton bus, RUNNING, worker off; tests drain explicitly.

    maxDispatchDepth raised above default 16 because one closed-loop run emits
    ~30 events sharing a single correlationId (per-correlationId recursive-
    depth guard would otherwise silently drop later events).
    """
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(
        auto_start_dispatch_worker=False, maxDispatchDepth=512))
    await b.initialize()
    yield b
    reset_event_bus_singleton()


class EventCapture:
    def __init__(self, bus_, types):
        self.events = []
        for et in types:
            bus_.subscribe(SubscribeOptions(
                subscriber=ComponentIdentity(
                    component_type=ComponentType.APPLICATION_SERVICE,
                    component_name="m9n11-capture",
                ),
                event_types=[et],
                handler=self._on_event,
            ))

    def _on_event(self, event):
        self.events.append(event)

    def of_type(self, et):
        return [e for e in self.events if e.eventType == et]


class StubLLMCouncil:
    """Minimal LLMCouncil double for prompt-loop construction."""

    async def deliberate(self, *a, **k):
        class S:
            council_id = "c_stub"

        return S()

    async def deliberate_and_propose(self, *a, **k):
        class P:
            proposal_id = "p_stub"
            proposer = "alpha"
            description = "text"
            options = []
            metadata = {}

        class S:
            council_id = "c_stub"

        return S(), [P()]


def make_sp_service(**config) -> SelfPromptingService:
    return SelfPromptingService(council=StubLLMCouncil(),
                                config=SelfPromptConfig(**config))


class _FailSim:
    async def simulate(self, *a, **k):
        return UserSimulationCompleted(goal="g", goal_completion_pct=0.2,
                                       workflow_success=False,
                                       usability_blockers=["b"])


def _svc(sim=None) -> TestOrchestratorService:
    return TestOrchestratorService(
        get_state_manager(),
        council_manager=get_council_manager(),
        user_simulation_agent=sim or _FailSim(),
    )


# ---------------------------------------------------------------------------
# SelfPrompting bound exhaustion → escalation signal
# ---------------------------------------------------------------------------


class TestSelfPromptingBoundsEscalation:
    @pytest.mark.asyncio
    async def test_token_bound_raises_and_signals(self, bus):
        capture = EventCapture(bus, [EventType.HUMAN_ESCALATION_REQUIRED])
        svc = make_sp_service(token_budget=10)

        with pytest.raises(SelfPromptBoundExceededError, match="token budget"):
            await svc.prompt(
                objective="an objective far exceeding ten tokens of budget",
                objective_id="obj-t", seed_questions=["Q1"],
            )
        await svc.wait_for_pending_signals()
        await get_core_event_bus().drain()

        events = capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED)
        assert len(events) >= 1
        payload = events[0].payload
        assert payload["service"] == "self_prompting"
        assert payload["reason"] == "bound_exhaustion"
        assert payload["recovery_action"] == "escalate_to_human"
        assert payload["authority"] == "advisory_only"

    @pytest.mark.asyncio
    async def test_depth_bound_raises_and_signals(self, bus):
        capture = EventCapture(bus, [EventType.HUMAN_ESCALATION_REQUIRED])
        svc = make_sp_service()

        with pytest.raises(SelfPromptBoundExceededError, match="depth"):
            await svc.prompt(
                objective="o", objective_id="obj-d", seed_questions=["Q1"],
                depth=svc.config.max_depth + 1,
            )
        await svc.wait_for_pending_signals()
        await get_core_event_bus().drain()
        assert len(capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED)) >= 1

    @pytest.mark.asyncio
    async def test_citation_bound_raises_and_signals(self, bus):
        capture = EventCapture(bus, [EventType.HUMAN_ESCALATION_REQUIRED])
        svc = make_sp_service()

        with pytest.raises(SelfPromptBoundExceededError, match="objective_id"):
            await svc.prompt(objective="o", objective_id="", seed_questions=["Q1"])
        await svc.wait_for_pending_signals()
        await get_core_event_bus().drain()
        assert len(capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED)) >= 1

    @pytest.mark.asyncio
    async def test_error_is_valueerror_subclass(self):
        """Existing callers catching ValueError keep working (fail-closed)."""
        assert issubclass(SelfPromptBoundExceededError, ValueError)
        svc = make_sp_service(token_budget=5)
        with pytest.raises(ValueError):  # broad contract preserved
            await svc.prompt(objective="o" * 100, objective_id="x",
                             seed_questions=[])

    @pytest.mark.asyncio
    async def test_no_bound_error_no_escalation(self, bus):
        """Normal successful prompts emit NO escalation signal."""
        from unittest.mock import patch

        capture = EventCapture(bus, [EventType.HUMAN_ESCALATION_REQUIRED])
        svc = make_sp_service(token_budget=100_000)
        with patch("aios.services.self_prompting._score_via_model_router",
                   side_effect=AssertionError("router not used in this test")):
            # Router failure inside scoring degrades per-proposal; force the
            # loop to complete by stubbing council manager stages instead.
            pass
        # Simplest honest run: tiny budget that FITS.
        results = await svc.prompt(objective="ok", objective_id="obj-ok",
                                   seed_questions=[])
        assert isinstance(results, list)
        await get_core_event_bus().drain()
        assert capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED) == []

    @pytest.mark.asyncio
    async def test_signal_failure_does_not_mask_raise(self):
        """If the escalation signal itself fails, the bound error still raises."""
        reset_event_bus_singleton()  # no bus -> signal path returns quietly
        svc = make_sp_service(token_budget=10)
        with pytest.raises(SelfPromptBoundExceededError):
            await svc.prompt(
                objective="an objective far exceeding ten tokens of budget",
                objective_id="o", seed_questions=["Q1"],
            )


# ---------------------------------------------------------------------------
# Closed-loop bound exhaustion → _escalate_to_human
# ---------------------------------------------------------------------------


class TestClosedLoopBoundsEscalation:
    @pytest.mark.asyncio
    async def test_iteration_cap_triggers_escalate_to_human(self, bus):
        """Loop exhausting the ITERATION CAP routes to _escalate_to_human.

        Isolation: the convergence detector's limit is raised above the
        iteration cap so ONLY the iteration-bound terminal is under test (the
        convergence terminal has its own dedicated test below). This is test
        scoping, not a production change.
        """
        capture = EventCapture(bus, [EventType.CHECKPOINT_CREATED])

        def never_fix(**kwargs):
            return None

        svc = _svc(_FailSim())
        from aios.services.convergence import ConvergenceDetector

        svc.convergence_detector = ConvergenceDetector(
            emit_event=svc._emit_event, no_improvement_limit=10,
        )
        result = await svc.orchestrate_test(
            objective="stuck", objective_id="obj_n11_cap",
            target="auth_service",
            implementation='def f(x):\n    return x\n',
            builder_id="", corrected_implementation_provider=never_fix,
        )
        assert result.status.value == "failed"
        assert result.detail == "Iteration cap reached without PASS."
        assert result.iterations == svc._max_iterations

        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        escalations = [
            e for e in capture.of_type(EventType.CHECKPOINT_CREATED)
            if e.payload.get("recovery_action") == "escalate_to_human"
        ]
        assert len(escalations) == 1, (
            "exactly one human-escalation checkpoint on cap exhaustion"
        )
        assert "Iteration cap reached" in escalations[0].payload.get("reason", "")

    @pytest.mark.asyncio
    async def test_convergence_terminal_also_escalates(self, bus):
        """The M9-N9 convergence terminal shares the escalation contract."""
        capture = EventCapture(bus, [
            EventType.CHECKPOINT_CREATED, EventType.HUMAN_ESCALATION_REQUIRED,
        ])

        def never_fix(**kwargs):
            return None

        svc = _svc(_FailSim())
        result = await svc.orchestrate_test(
            objective="converged stuck", objective_id="obj_n11_conv",
            target="auth_service", implementation='def f(x):\n    return x\n',
            builder_id="", corrected_implementation_provider=never_fix,
        )
        assert result.status.value == "failed"
        assert "Convergence detected" in result.detail

        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        assert capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED), (
            "advisory convergence signal emitted"
        )

    @pytest.mark.asyncio
    async def test_no_new_event_types_introduced(self, bus):
        before = {e.name for e in EventType}

        def never_fix(**kwargs):
            return None

        svc = _svc(_FailSim())
        await svc.orchestrate_test(
            objective="types", objective_id="obj_n11_types",
            target="auth_service", implementation='def f(x):\n    return x\n',
            builder_id="", corrected_implementation_provider=never_fix,
        )
        assert {e.name for e in EventType} == before

    @pytest.mark.asyncio
    async def test_advisory_marker_on_all_m9_escalation_payloads(self, bus):
        """Every M9 escalation signal declares advisory-only authority."""
        capture = EventCapture(bus, [
            EventType.HUMAN_ESCALATION_REQUIRED, EventType.CHECKPOINT_CREATED,
        ])

        def never_fix(**kwargs):
            return None

        svc = _svc(_FailSim())
        await svc.orchestrate_test(
            objective="advisory check", objective_id="obj_n11_adv",
            target="auth_service", implementation='def f(x):\n    return x\n',
            builder_id="", corrected_implementation_provider=never_fix,
        )
        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        her_signals = capture.of_type(EventType.HUMAN_ESCALATION_REQUIRED)
        assert her_signals, "escalation signal present"
        for e in her_signals:
            assert e.payload.get("authority") == "advisory_only"
            assert e.payload.get("recovery_action") == "escalate_to_human"
