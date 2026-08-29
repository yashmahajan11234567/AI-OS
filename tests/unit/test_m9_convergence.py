"""M9-N9 — Bounded convergence-detection tests (spec §3.3.7, §32.9, §34).

The closed loop gains a deterministic, advisory-only no-improvement detector
that routes to the existing human-escalation semantics via the canonical
HUMAN_ESCALATION_REQUIRED event. Coverage:

  * detection rule: N consecutive identical failure signatures => converged;
    any change in evidence content resets the window (real improvement)
  * bounding: fixed sliding window; once signaled, never re-signals spuriously
  * advisory-only: the detector never decides pass/fail — it only emits the
    canonical escalation signal and returns a boolean; orchestrator terminates
    with an honest FAILED result (no false PASS)
  * canonical event only: HUMAN_ESCALATION_REQUIRED (no new EventType), with
    recovery_action="escalate_to_human" matching workflow.py:869 contract
  * integration: TestOrchestratorService loop converges early on repeated
    identical failures and still respects the iteration cap (INV-013)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.core.testing_evidence import TestingEvidence
from aios.events.core.bus import EventBus, reset_event_bus_singleton, get_core_event_bus
from aios.events.core.manager import SubscribeOptions
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager
from aios.services.convergence import (
    ConvergenceDetector,
    DEFAULT_NO_IMPROVEMENT_LIMIT,
    IterationObservation,
)
from aios.services.testing import TestOrchestratorService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FailSim:
    """User-simulation double that always fails."""

    async def simulate(self, *a, **k):
        from aios.core.testing_evidence import UserSimulationCompleted

        return UserSimulationCompleted(
            goal="g", goal_completion_pct=0.2, workflow_success=False,
            usability_blockers=["submit button missing"],
        )


def _obs(obj="o", iteration=1, verdict="reject", sig="same", cid="") -> IterationObservation:
    return IterationObservation(
        objective_id=obj, iteration=iteration, verdict=verdict,
        failure_signature=sig, correlation_id=cid,
    )


class EventCapture:
    """Records events emitted through the detector's emit hook."""

    def __init__(self):
        self.events: list[tuple] = []

    def __call__(self, event_type, payload, correlation_id):
        self.events.append((event_type, payload, correlation_id))


# ---------------------------------------------------------------------------
# Detector rule + bounding
# ---------------------------------------------------------------------------


class TestDetectionRule:
    def test_no_signal_before_limit(self):
        capture = EventCapture()
        det = ConvergenceDetector(emit_event=capture)

        assert det.observe(_obs(iteration=1)) is False

        assert capture.events == []

    def test_signal_at_identical_signatures(self):
        capture = EventCapture()
        det = ConvergenceDetector(emit_event=capture)  # limit = 2

        assert det.observe(_obs(iteration=1, sig="A")) is False
        assert det.observe(_obs(iteration=2, sig="A")) is True
        assert len(capture.events) == 1

    def test_changing_signature_resets_window(self):
        """Real improvement (different evidence content) resets convergence."""
        det = ConvergenceDetector()

        assert det.observe(_obs(iteration=1, sig="A")) is False
        assert det.observe(_obs(iteration=2, sig="B")) is False  # changed → reset
        assert det.observe(_obs(iteration=3, sig="B")) is True  # now stable-failing

    def test_verdict_part_of_signature(self):
        """Verdict participates via the metadata-derived signature path
        (no explicit failure_signature supplied)."""
        det = ConvergenceDetector()
        assert det.observe(IterationObservation(
            objective_id="o", iteration=1, verdict="reject",
            failure_signature="", metadata={"reasons": ["boom"]},
        )) is False
        # Same reasons but different verdict = different signature.
        assert det.observe(IterationObservation(
            objective_id="o", iteration=2, verdict="conditional",
            failure_signature="", metadata={"reasons": ["boom"]},
        )) is False

    def test_objectives_tracked_independently(self):
        det = ConvergenceDetector()
        assert det.observe(_obs(obj="x", iteration=1, sig="A")) is False
        assert det.observe(_obs(obj="y", iteration=1, sig="A")) is False
        assert det.observe(_obs(obj="x", iteration=2, sig="A")) is True
        assert det.observe(_obs(obj="y", iteration=2, sig="A")) is True

    def test_custom_limit_bounded(self):
        det = ConvergenceDetector(no_improvement_limit=3)
        assert det.no_improvement_limit == 3
        assert det.observe(_obs(iteration=1)) is False
        assert det.observe(_obs(iteration=2)) is False
        assert det.observe(_obs(iteration=3)) is True

    def test_limit_floor_of_one(self):
        det = ConvergenceDetector(no_improvement_limit=0)
        assert det.no_improvement_limit == 1
        assert det.observe(_obs(iteration=1)) is True


class TestBoundedAndAdvisory:
    def test_never_re_signals_after_converged(self):
        capture = EventCapture()
        det = ConvergenceDetector(emit_event=capture)
        det.observe(_obs(iteration=1))
        assert det.observe(_obs(iteration=2)) is True
        for i in range(3, 10):  # further failures: silent, bounded
            assert det.observe(_obs(iteration=i)) is False
        assert len(capture.events) == 1, "exactly one escalation signal"

    def test_window_memory_is_hard_bounded(self):
        det = ConvergenceDetector()  # limit 2
        for i in range(1000):
            det.observe(_obs(obj="z", iteration=i, sig=f"s{i}"))
        assert len(det._history["z"]) <= det.no_improvement_limit

    def test_emit_failure_does_not_break_detection(self):
        def broken_emit(*a, **k):
            raise RuntimeError("bus down")

        det = ConvergenceDetector(emit_event=broken_emit)
        det.observe(_obs(iteration=1))
        assert det.observe(_obs(iteration=2)) is True, (
            "signaling path must be exception-safe"
        )

    def test_reset_clears_state(self):
        det = ConvergenceDetector()
        det.observe(_obs(iteration=1))
        det.reset("o")
        assert det._history == {}
        assert det._signaled == {}
        det.observe(_obs(iteration=1))
        det.reset(None)
        assert det._history == {}

    def test_payload_carries_advisory_contract(self):
        capture = EventCapture()
        det = ConvergenceDetector(emit_event=capture)
        det.observe(_obs(iteration=1, cid="corr-1"))
        det.observe(_obs(iteration=2, cid="corr-1"))

        event_type, payload, correlation_id = capture.events[0]
        assert event_type.name == "HUMAN_ESCALATION_REQUIRED"
        assert payload["reason"] == "convergence_no_improvement"
        assert payload["recovery_action"] == "escalate_to_human"
        assert payload["advisory"] is True
        assert payload["authority"] == "advisory_only"
        assert payload["iterations_observed"] == [1, 2]
        assert correlation_id == "corr-1"

    def test_default_limit_value(self):
        assert DEFAULT_NO_IMPROVEMENT_LIMIT == 2


# ---------------------------------------------------------------------------
# Orchestrator integration (closed-loop wiring)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def _bus():
    """Canonical singleton bus, initialized RUNNING, dispatch worker OFF so
    events enqueue deterministically; tests drain explicitly (INV-EB-012).

    maxDispatchDepth raised above its default 16: a full closed-loop run emits
    ~30 canonical events sharing ONE correlationId, which trips the bus's
    per-correlationId recursive-depth guard (bus.py:780) and silently drops
    later events — including the escalation signal under test.
    """
    from aios.events.core.bus import EventBusConfig

    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(
        auto_start_dispatch_worker=False, maxDispatchDepth=512,
    ))
    await b.initialize()
    yield b
    reset_event_bus_singleton()


def _svc(sim=None) -> TestOrchestratorService:
    return TestOrchestratorService(
        get_state_manager(),
        council_manager=get_council_manager(),
        user_simulation_agent=sim or _FailSim(),
    )


def _evidence(perspective: str, observed: str, verdict: str = "fail") -> TestingEvidence:
    from aios.core.testing_evidence import Provenance

    return TestingEvidence(
        perspective=perspective, target="t", test_id=str(uuid4()),
        observed=observed, verdict=verdict,
        provenance=Provenance(
            source=perspective, worker="local", session="s",
            timestamp="2026-08-26T00:00:00+00:00", environment="tester",
            correlation_id="c",
        ),
    )


class TestOrchestratorConvergence:
    def test_detector_attached_and_wired(self, _bus):
        svc = _svc()
        assert isinstance(svc.convergence_detector, ConvergenceDetector)
        assert svc.convergence_detector._emit_event == svc._emit_event

    async def test_signature_content_derived_not_identity(self, _bus):
        """Signature depends on failing-evidence CONTENT, not iteration count."""
        svc = _svc()
        ev = [_evidence("security_agency", "SQL injection found")]

        s1 = "|".join(sorted(
            f"{e.perspective}:{(e.observed or '')[:120]}" for e in ev
        ))
        obs1 = IterationObservation(objective_id="o", iteration=1,
                                    verdict="reject", failure_signature=s1)
        obs2 = IterationObservation(objective_id="o", iteration=99,
                                    verdict="reject", failure_signature=s1)
        d = svc.convergence_detector
        assert d.observe(obs1) is False
        assert d.observe(obs2) is True, "identical content converges regardless of iteration"

    async def test_observe_iteration_builds_signature_from_evidence(self, _bus):
        svc = _svc()
        ev = [
            _evidence("performance_agency", "latency 900ms"),
            _evidence("security_agency", "ok", verdict="pass"),  # passing ignored
        ]
        converged = svc._observe_iteration("obj-c", 1, "reject", ev, "cid")

        assert converged is False
        window = svc.convergence_detector._history["obj-c"]
        assert len(window) == 1
        assert "performance_agency:" in window[0].failure_signature
        assert "security_agency" not in window[0].failure_signature

    async def test_loop_terminates_early_on_convergence(self, _bus):
        """Repeated identical failures terminate BEFORE the iteration cap."""
        svc = _svc(_FailSim())

        def never_fix(**kwargs):  # provider contract: keyword-only
            return None

        result = await svc.orchestrate_test(
            objective="stuck objective", objective_id="obj_conv",
            target="auth_service", implementation='def f(x):\n    return x\n',
            builder_id="",
            corrected_implementation_provider=never_fix,
        )
        assert result.status.value == "failed"
        assert "Convergence detected" in result.detail
        # With limit=2, convergence fires by iteration 2 — strictly earlier
        # than the cap of 5.
        assert result.iterations < svc._max_iterations

    async def test_convergence_emits_canonical_event_only(self, _bus):
        """HUMAN_ESCALATION_REQUIRED flows over the bus; no new EventType."""
        before = {e.name for e in EventType}
        svc = _svc(_FailSim())

        received: list = []
        get_core_event_bus().subscribe(SubscribeOptions(
            subscriber=ComponentIdentity(
                component_type=ComponentType.APPLICATION_SERVICE,
                component_name="m9n9-test-capture",
            ),
            event_types=[EventType.HUMAN_ESCALATION_REQUIRED],
            handler=lambda e: received.append(e),
        ))

        await svc.orchestrate_test(
            objective="escalate me", objective_id="obj_esc",
            target="auth_service", implementation='def f(x):\n    return x\n',
            builder_id="",
        )
        # The sync _emit_event bridge enqueues publishes via ensure_future:
        # wait for those tasks FIRST so events are on the bus, then drain.
        await svc.wait_for_pending_events()
        await get_core_event_bus().drain()

        names = {e.eventType.name for e in received}
        assert "HUMAN_ESCALATION_REQUIRED" in names
        assert {e.name for e in EventType} == before, "no new EventType"

    async def test_success_resets_history(self, _bus):
        """A real PASS clears convergence state (improvement happened)."""
        from tests.unit.test_m7_closed_loop import BAD, GOOD, _PassSim

        svc = _svc(_PassSim())

        def provider(failed_evidence, failed_implementation):
            return GOOD if failed_implementation.strip() == BAD.strip() \
                else failed_implementation

        result = await svc.orchestrate_test(
            objective="fixable objective", objective_id="obj_fix",
            target="auth_service", implementation=BAD,
            corrected_implementation_provider=provider,
        )
        assert result.status.value == "passed"
        assert svc.convergence_detector._history.get("obj_fix") in (None, [])
        assert not svc.convergence_detector._signaled.get("obj_fix")
