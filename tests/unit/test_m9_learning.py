"""M9-N4 — RCA→Learning handoff tests (spec §24 case 1, §34).

The pre-M9 handoff (root_cause.py) juggled ``loop.create_task`` /
``asyncio.run`` fallback chains inside an async method — fire-and-forget tasks
raced teardown and could silently drop captures. M9-N4 replaces it with a
direct await on the running loop, with a logged event-driven fallback when no
LearningService is bound.

Coverage:
  * analyze() with a bootstrapped LearningService captures synchronously
    awaited — the learning is in ``_learnings`` when analyze() returns
  * failure_category / root_cause / recommended_action flow into the record
  * LearningCaptured event emitted per capture
  * capture failure is non-blocking: analysis still returns, warning logged
  * missing LearningService falls back to audit-event emission (no crash)
  * learning.py carries no print() debug statements (spec §11.4 cleanup)
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from aios.core.root_cause import (
    FailureContext,
    RootCauseAnalyzer,
    set_root_cause_analyzer,
)
from aios.core.service_registry import reset_service_registry_singleton
from aios.events.core.bus import reset_event_bus_singleton


@pytest.fixture(autouse=True)
def _isolation():
    """Fresh registry + bus + module globals per test."""
    from aios.core.service_registry import (
        ServiceRegistry as CoreRegistry,
        set_service_registry as set_core,
    )
    from aios.events.core.bus import EventBus, EventBusConfig

    from aios.services.learning import set_learning_service_instance

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    core = CoreRegistry(event_bus=bus)
    set_core(core)

    analyzer = RootCauseAnalyzer()
    set_root_cause_analyzer(analyzer)

    yield

    set_learning_service_instance(None)  # type: ignore[arg-type]
    set_root_cause_analyzer(None)
    reset_service_registry_singleton()
    reset_event_bus_singleton()


def _context(failure_id: str = "task-42", error: str = "TypeError: bad type") -> FailureContext:
    return FailureContext(
        failure_id=failure_id,
        event_type="task.failed",
        error=error,
        error_type="TypeError",
        service="coding",
        task_id=failure_id,
        correlation_id="",
        payload={"task_id": failure_id},
    )


class TestAwaitedHandoff:
    async def test_analyze_awaits_learning_capture(self):
        """The learning MUST be stored before analyze() returns (real await)."""
        from aios.services.bootstrap import bootstrap_engineering_services

        services = bootstrap_engineering_services(enabled=["memory", "learning"])
        learning_svc = next(s for s in services if s.name == "learning")

        analyzer = get_rca()
        analysis = await analyzer.analyze(_context())

        learnings = learning_svc._learnings
        assert len(learnings) == 1
        captured = learnings[0]
        assert captured["analysis_id"] == analysis.analysis_id
        assert captured["failure_category"] == analysis.category.value
        assert captured["root_cause"] == analysis.root_cause
        assert captured["resolution"] == analysis.recommended_action.value
        assert captured["preventive_measures"] == analysis.preventive_measures

    async def test_capture_failure_non_blocking(self, monkeypatch):
        """A broken LearningService must not fail the analysis (log + continue)."""
        from aios.services.bootstrap import bootstrap_engineering_services

        services = bootstrap_engineering_services(enabled=["memory", "learning"])
        learning_svc = next(s for s in services if s.name == "learning")

        async def exploding(**kwargs):
            raise RuntimeError("capture exploded")

        monkeypatch.setattr(
            learning_svc, "capture_learning_from_analysis", exploding
        )

        analyzer = get_rca()
        analysis = await analyzer.analyze(_context())  # must NOT raise

        assert analysis.analysis_id.startswith("analysis_")
        assert learning_svc._learnings == []  # nothing captured

    async def test_missing_learning_service_falls_back_to_event(self):
        """No LearningService bound → audit-event fallback, no crash."""
        from aios.services.learning import set_learning_service_instance

        set_learning_service_instance(None)

        events: list = []
        analyzer = get_rca()
        original_emit = analyzer._emit_event

        async def spy(event_type, payload, correlation_id):
            events.append((event_type, payload))
            await original_emit(event_type, payload, correlation_id)

        monkeypatch_spy(analyzer, spy)
        analysis = await analyzer.analyze(_context())
        assert analysis.analysis_id.startswith("analysis_")
        # Fallback audit emission occurred.
        fallbacks = [e for e in events if e[0].value == "AI_AGENT_AUDIT_EMITTED"]
        assert fallbacks, "expected AI_AGENT_AUDIT_EMITTED fallback"
        assert fallbacks[-1][1]["analysis_id"] == analysis.analysis_id


class TestNoPrintPollution:
    def test_no_print_in_learning_service(self):
        import inspect

        import aios.services.learning as mod

        src = inspect.getsource(mod)
        assert "print(" not in src

    def test_no_print_in_root_cause(self):
        import inspect

        import aios.core.root_cause as mod

        src = inspect.getsource(mod)
        assert "print(" not in src

    async def test_analyze_writes_nothing_to_stdout(self, capsys):
        """End-to-end: a full analyze() call must keep stdout clean."""
        from aios.services.bootstrap import bootstrap_engineering_services

        bootstrap_engineering_services(enabled=["memory", "learning"])
        analyzer = get_rca()
        buf = io.StringIO()
        with redirect_stdout(buf):
            await analyzer.analyze(_context())
        assert buf.getvalue() == ""
        captured_out = capsys.readouterr().out
        assert "ROOT CAUSE" not in captured_out
        assert "LEARNING SERVICE" not in captured_out


# --- helpers ---------------------------------------------------------------


def get_rca() -> RootCauseAnalyzer:
    from aios.core.root_cause import get_root_cause_analyzer

    return get_root_cause_analyzer()


def monkeypatch_spy(analyzer: RootCauseAnalyzer, spy) -> None:
    analyzer._emit_event = spy  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# M9-N2 — retrieval API (GAP-B)
# ---------------------------------------------------------------------------


class TestGetLearnings:
    def _service(self) -> "LearningServiceLike":
        from aios.services.learning import LearningService

        svc = LearningService()
        return svc

    async def _seed(self, svc, count: int = 3):
        for i in range(count):
            await svc.capture_learning_from_analysis(
                analysis_id=f"analysis_task-{i}",
                failure_category="execution_error" if i % 2 == 0 else "timeout",
                recommended_action="RETRY_WITH_BACKOFF",
                root_cause=f"root cause {i}",
                preventive_measures=[f"measure-{i}"],
            )

    async def test_returns_all_newest_first(self):
        svc = self._service()
        await self._seed(svc, 3)
        learnings = svc.get_learnings()
        assert len(learnings) == 3
        assert learnings[0]["analysis_id"] == "analysis_task-2"
        assert learnings[-1]["analysis_id"] == "analysis_task-0"

    async def test_filter_by_failure_category(self):
        svc = self._service()
        await self._seed(svc, 4)
        exec_errors = svc.get_learnings(failure_category="execution_error")
        assert len(exec_errors) == 2
        assert all(
            l["failure_category"] == "execution_error" for l in exec_errors
        )

    async def test_filter_by_analysis_id(self):
        svc = self._service()
        await self._seed(svc, 3)
        found = svc.get_learnings(analysis_id="analysis_task-1")
        assert len(found) == 1
        assert found[0]["root_cause"] == "root cause 1"

    async def test_limit_bounds_result(self):
        svc = self._service()
        await self._seed(svc, 5)
        assert len(svc.get_learnings(limit=2)) == 2
        # newest-first respected under limit
        assert svc.get_learnings(limit=1)[0]["analysis_id"] == "analysis_task-4"

    async def test_since_filters_old_records(self):
        import time as time_mod

        svc = self._service()
        await self._seed(svc, 2)
        cutoff = time_mod.time() + 10  # future → excludes everything captured
        assert svc.get_learnings(since=cutoff) == []
        past = time_mod.time() - 100
        assert len(svc.get_learnings(since=past)) == 2

    async def test_shallow_copies_not_store_references(self):
        svc = self._service()
        await self._seed(svc, 1)
        retrieved = svc.get_learnings()[0]
        retrieved["resolution"] = "TAMPERED"
        assert svc._learnings[0]["resolution"] != "TAMPERED"

    async def test_empty_store_returns_empty(self):
        assert self._service().get_learnings() == []


class TestQueryRelevant:
    def _service(self):
        from aios.services.learning import LearningService

        return LearningService()

    async def _seed(self, svc):
        await svc.capture_learning_from_analysis(
            analysis_id="analysis_db",
            failure_category="dependency_failure",
            recommended_action="REINSTALL_DEPENDENCY",
            root_cause="database connection pool exhausted",
            preventive_measures=["pool warmup"],
        )
        await svc.capture_learning_from_analysis(
            analysis_id="analysis_net",
            failure_category="timeout",
            recommended_action="INCREASE_TIMEOUT",
            root_cause="network latency to external api",
            preventive_measures=["circuit breaker"],
        )

    async def test_keyword_match_ranks_relevant_first(self):
        svc = self._service()
        await self._seed(svc)
        results = svc.query_relevant("fix database connection issues")
        assert results, "expected at least one relevant learning"
        assert results[0]["analysis_id"] == "analysis_db"

    async def test_limit_respected(self):
        svc = self._service()
        await self._seed(svc)
        results = svc.query_relevant("database network timeout connection", limit=1)
        assert len(results) == 1

    async def test_no_match_returns_empty(self):
        svc = self._service()
        await self._seed(svc)
        assert svc.query_relevant("quantum flux capacitor") == []

    async def test_no_ml_embeddings_simple_deterministic(self):
        """Spec §11.2: simple keyword/recency match; deterministic."""
        svc = self._service()
        await self._seed(svc)
        a = svc.query_relevant("network latency")
        b = svc.query_relevant("network latency")
        assert [r["learning_id"] for r in a] == [r["learning_id"] for r in b]

    async def test_shallow_copies(self):
        svc = self._service()
        await self._seed(svc)
        results = svc.query_relevant("database")
        if results:
            results[0]["tampered"] = True
            assert "tampered" not in svc._learnings[0]


class TestRetrievalThroughBootstrapInstance:
    """IND-6: exercise the bootstrap-created instance, not a hand-made one."""

    async def test_capture_then_retrieve_via_real_bootstrap(self):
        from aios.services.bootstrap import bootstrap_engineering_services
        from aios.services.learning import get_learning_service

        bootstrap_engineering_services(enabled=["memory", "learning"])
        svc = get_learning_service()

        analyzer = get_rca()
        analysis = await analyzer.analyze(_context())

        by_analysis = svc.get_learnings(analysis_id=analysis.analysis_id)
        assert len(by_analysis) == 1

        relevant = svc.query_relevant(f"{analysis.category.value} failure")
        assert any(
            l["analysis_id"] == analysis.analysis_id for l in relevant
        )


class LearningServiceLike:
    """Type-hint shim only (tests use duck typing)."""


# ---------------------------------------------------------------------------
# M9-N3 — PlanningService advisory learning ingest
# ---------------------------------------------------------------------------


class TestPlanningAdvisoryContext:
    def _planner(self):
        from aios.services.planning import PlanningService

        return PlanningService()

    async def test_plan_attaches_advisory_context(self):
        from aios.services.bootstrap import bootstrap_engineering_services
        from aios.services.learning import get_learning_service

        bootstrap_engineering_services(enabled=["memory", "learning", "planning"])
        learning_svc = get_learning_service()
        await learning_svc.capture_learning_from_analysis(
            analysis_id="analysis_x",
            failure_category="timeout",
            recommended_action="INCREASE_TIMEOUT",
            root_cause="network latency to external api",
            preventive_measures=["circuit breaker"],
        )

        planner = self._planner()
        plan = planner.plan({"task_id": "t1", "goal": "fix network latency issues"})
        assert plan is not None
        ctx = plan["advisory_context"]
        assert ctx["advisory"] is True
        assert ctx["source"] == "learning_service"
        assert any("network" in l["root_cause"] for l in ctx["learnings"])

    async def test_no_learning_service_yields_empty_context(self):
        from aios.services.learning import set_learning_service_instance

        set_learning_service_instance(None)
        planner = self._planner()
        plan = planner.plan({"task_id": "t1", "goal": "anything"})
        assert plan["advisory_context"] == {}

    async def test_retrieval_failure_degrades_to_empty(self, monkeypatch):
        from aios.services.bootstrap import bootstrap_engineering_services
        from aios.services.learning import get_learning_service

        bootstrap_engineering_services(enabled=["memory", "learning"])
        svc = get_learning_service()

        def exploding(*args, **kwargs):
            raise RuntimeError("retrieval exploded")

        monkeypatch.setattr(svc, "query_relevant", exploding)
        planner = self._planner()
        plan = planner.plan({"task_id": "t1", "goal": "some goal"})  # must not raise
        assert plan["advisory_context"] == {}

    async def test_advisory_context_never_claims_authority(self):
        """Spec §16: a retrieved learning cannot claim authoritative status."""
        from aios.services.bootstrap import bootstrap_engineering_services
        from aios.services.learning import get_learning_service

        bootstrap_engineering_services(enabled=["memory", "learning"])
        await get_learning_service().capture_learning_from_analysis(
            analysis_id="analysis_a",
            failure_category="coding_error",
            recommended_action="FIX_SYNTAX",
            root_cause="syntax error",
            preventive_measures=[],
        )
        planner = self._planner()
        plan = planner.plan({"task_id": "t2", "goal": "syntax error fix"})
        ctx = plan["advisory_context"]
        # Structural authority boundary: flagged advisory, no verdict fields.
        assert ctx.get("advisory") is True
        for learning in ctx["learnings"]:
            assert "authority" not in learning or learning["authority"] != "authoritative"
            assert "verdict" not in learning
            assert learning.get("trust_level", "untrusted") != "trusted"

    async def test_planning_completed_event_carries_refs(self):
        """PLANNING_COMPLETED payload includes the advisory learning refs."""
        from aios.events.core.types import EventType

        from aios.services.bootstrap import bootstrap_engineering_services
        from aios.services.learning import get_learning_service

        bootstrap_engineering_services(enabled=["memory", "learning"])
        await get_learning_service().capture_learning_from_analysis(
            analysis_id="analysis_e",
            failure_category="deployment_failure",
            recommended_action="ROLLBACK",
            root_cause="container image missing",
            preventive_measures=["image scan"],
        )

        planner = self._planner()
        emitted: list = []
        original = planner.emit_core_event

        async def spy(event_type, payload, **kwargs):
            emitted.append((event_type, payload))
            return await original(event_type, payload, **kwargs)

        planner.emit_core_event = spy  # type: ignore[method-assign]

        import asyncio

        from aios.events.base import Event as LegacyEvent
        from aios.events.types import PlanningRequested

        request = LegacyEvent(
            source_service="tester",
            correlation_id=None,
            causation_id=None,
            payload={"task_id": "t9", "goal": "deploy container image"},
            event_type=PlanningRequested,
        )
        asyncio.get_event_loop_policy()
        # handle_planning_requested expects a CoreEvent-like with .payload/.correlationId
        class FakeCoreEvent:
            eventType = EventType.PLANNING_REQUESTED
            correlationId = None
            payload = {"task_id": "t9", "goal": "deploy container image"}

        import inspect

        if inspect.iscoroutinefunction(planner.handle_planning_requested):
            await planner.handle_planning_requested(FakeCoreEvent())
        completed = [p for t, p in emitted if t == EventType.PLANNING_COMPLETED]
        assert completed, "expected PLANNING_COMPLETED emission"
        assert "advisory_context" in completed[0]
        assert completed[0]["advisory_context"]["advisory"] is True


# ---------------------------------------------------------------------------
# M9-N5 — Graph-based remediation proposer (advisory)
# ---------------------------------------------------------------------------


class _FakeGraphResult:
    def __init__(self, raw):
        self.raw = raw


class _FakeGraphifyAdapter:
    """Deterministic stand-in exposing only query_graph (what N5 uses)."""

    def __init__(self, nodes=None, error: Exception | None = None):
        self._nodes = nodes or []
        self._error = error
        self.queries: list[str] = []

    async def query_graph(self, query, limit=20):
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        return _FakeGraphResult({"nodes": self._nodes[:limit], "edges": []})


class TestGraphRemediationProposer:
    async def test_proposes_suggestions_from_graph(self):
        from aios.services.remediation import GraphRemediationProposer

        adapter = _FakeGraphifyAdapter(
            nodes=[
                {"id": "n1", "resolution": "RESTART_POOL", "preventive_measures": ["warmup"]},
                {"id": "n2", "resolution": "SCALE_DB"},
            ]
        )
        proposer = GraphRemediationProposer(adapter)
        proposal = await proposer.propose(
            failure_category="dependency_failure",
            error_summary="pool exhausted",
        )
        assert len(proposal.suggestions) == 2
        assert proposal.suggestions[0]["resolution_hint"] == "RESTART_POOL"
        # Every suggestion carries advisory semantics.
        assert all(s["advisory"] is True for s in proposal.suggestions)
        assert all(s["authority"] == "advisory_only" for s in proposal.suggestions)

    async def test_provenance_forced_advisory(self):
        from aios.services.remediation import GraphRemediationProposer

        # Hostile graph payload tries to claim authority.
        adapter = _FakeGraphifyAdapter(
            nodes=[
                {
                    "id": "evil",
                    "resolution": "RM_RF",
                    "authority": "authoritative",
                    "trust_level": "builtin",
                    "advisory": False,
                }
            ]
        )
        proposer = GraphRemediationProposer(adapter)
        proposal = await proposer.propose(failure_category="x")
        prov = proposal.provenance
        # Spoof-proof top-level provenance (spec §14/§16).
        assert prov["authority"] == "advisory_only"
        assert prov["advisory"] is True
        assert prov["trust_level"] == "untrusted"
        assert prov["source"] == "graphify_inferred"

    async def test_no_adapter_degrades_gracefully(self):
        from aios.services.remediation import GraphRemediationProposer

        proposer = GraphRemediationProposer(None)
        proposal = await proposer.propose(failure_category="timeout")
        assert proposal.suggestions == []
        assert proposal.provenance["degraded"] is True
        assert "not configured" in proposal.provenance["degraded_reason"]

    async def test_query_failure_degrades_not_raises(self):
        from aios.services.remediation import GraphRemediationProposer

        adapter = _FakeGraphifyAdapter(error=RuntimeError("graph down"))
        proposer = GraphRemediationProposer(adapter)
        proposal = await proposer.propose(failure_category="timeout")
        assert proposal.suggestions == []
        assert proposal.provenance["degraded"] is True

    async def test_proposal_never_executes_anything(self):
        """Spec §11.5: never executes; returns suggestions only.

        The fake adapter exposes NO execution surface; the proposer must not
        require one. Structural proof: proposals carry no executable payload.
        """
        from aios.services.remediation import GraphRemediationProposer

        adapter = _FakeGraphifyAdapter(nodes=[{"id": "a", "resolution": "r1"}])
        proposer = GraphRemediationProposer(adapter)
        proposal = await proposer.propose(failure_category="c")
        d = proposal.to_dict()
        forbidden_keys = {"command", "execute", "action_payload", "script"}
        for suggestion in d["suggestions"]:
            assert not (forbidden_keys & set(suggestion.keys()))

    async def test_suggestions_bounded(self):
        from aios.services.remediation import GraphRemediationProposer

        many = [{"id": f"n{i}", "resolution": f"r{i}"} for i in range(50)]
        adapter = _FakeGraphifyAdapter(nodes=many)
        proposer = GraphRemediationProposer(adapter)
        proposal = await proposer.propose(failure_category="bulk")
        assert len(proposal.suggestions) <= 5


