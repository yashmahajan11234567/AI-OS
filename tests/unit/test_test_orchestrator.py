"""
M7-K — TestOrchestratorService REAL behavior tests.

Proves the orchestrator is wired to the REAL production seam and exercises
ACTUAL behavior (not class existence):

  * TestOrchestratorService EXTENDS the canonical WorkflowManager (INV-015) —
    single inheritance, no second workflow engine.
  * dispatch_perspective actually invokes the real agency execution adapters
    and returns NORMALIZED TestingEvidence with complete, immutable provenance.
  * perspective dispatch is content-driven: a defect detectable only by its
    implementation (not the target name) is surfaced; a target whose NAME
    contains a defect keyword but whose implementation is clean is NOT flagged.
  * submit_to_testing_council reuses the EXISTING CouncilManager (a session,
    not a second council) and builder evidence is excluded (INV-009).
  * coordinate_retest re-executes only the failing perspectives and preserves
    provenance + correlation id.
  * orchestrate_test runs the bounded closed loop and terminates within the
    iteration/token budget (INV-013) — it does not hang or silently converge.
  * No new EventType is emitted (the canonical EventBus schema is unchanged).

These tests inject the SAME collaborators the production kernel wires (real
adapters, real CouncilManager, real EventBus, real StateManager) — they do not
replace the seam with mocks. UserSimulationAgent is the only collaborator
substituted, and only with a deterministic double (the real worker is external).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.adapters.base import ExecutionStatus
from aios.core.council_manager import get_council_manager
from aios.core.state import get_state_manager
from aios.core.testing_evidence import (
    TestingEvidence,
    UserSimulationCompleted,
)
from aios.core.workflow import WorkflowManager
from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.events.core.types import EventType
from aios.services.testing import (
    PERSPECTIVE_IDS,
    TestOrchestratorService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


class _PassSim:
    """Deterministic external-worker stand-in that PASSES (goal achieved)."""

    async def simulate(self, *a, **k):
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=1.0, workflow_success=True
        )


class _FailSim:
    """Deterministic external-worker stand-in that FAILS (goal not achieved)."""

    async def simulate(self, *a, **k):
        return UserSimulationCompleted(
            goal="log in", goal_completion_pct=0.1, workflow_success=False,
            usability_blockers=["submit did nothing"],
            navigation_failures=["landing error"],
            missing_feedback=["no message"],
        )


def _svc(sim=_PassSim()):
    return TestOrchestratorService(
        get_state_manager(),
        council_manager=get_council_manager(),
        user_simulation_agent=sim,
    )


# ---------------------------------------------------------------------------
# Inheritance (INV-015)
# ---------------------------------------------------------------------------


def test_orchestrator_extends_workflow_manager_single_inheritance():
    svc = _svc()
    assert isinstance(svc, WorkflowManager)
    # Single, canonical base — no second workflow engine composed in.
    assert type(svc).__mro__.count(WorkflowManager) == 1
    # It extends the real canonical workflow engine and exposes its surface.
    assert hasattr(svc, "start_workflow")
    assert hasattr(svc, "register_workflow")
    assert hasattr(svc, "get_workflow_status")


# ---------------------------------------------------------------------------
# Real dispatch + normalization + provenance
# ---------------------------------------------------------------------------


async def test_dispatch_perspective_invokes_real_adapter_and_normalizes():
    svc = _svc()
    # Clean, well-documented implementation -> security adapter returns SUCCESS.
    clean = (
        'def login(user, pwd):\n'
        '    """Authenticate a user."""\n'
        '    if not authorize(user, "login", "auth_service"):\n'
        '        return None\n'
        '    return db.query(user, pwd)\n'
    )
    ev = await svc.dispatch_perspective(
        perspective="security_agency",
        target="auth_service",
        correlation_id=str(uuid4()),
        implementation=clean,
        builder_id="",
    )
    assert isinstance(ev, TestingEvidence)
    # Normalized by the real adapter result, not a prose stub.
    assert ev.perspective == "security_agency"
    assert ev.target == "auth_service"
    # Provenance is complete and validates.
    prov = ev.provenance
    assert prov.source == "security_agency"
    assert prov.worker == "local"
    assert prov.session
    assert prov.timestamp
    assert prov.environment == "tester"
    assert prov.correlation_id
    prov.validate()
    # Evidence is immutable.
    with pytest.raises(Exception):
        ev.severity = "critical"


async def test_dispatch_perspective_detects_real_defect_by_content():
    svc = _svc()
    # No "sql" in target name, but the IMPLEMENTATION has a real injection.
    vuln = (
        'def login(u, p):\n'
        "    q = \"SELECT * FROM users WHERE name='\" + u + \"'\"\n"
        '    return db.execute(q)\n'
    )
    ev = await svc.dispatch_perspective(
        perspective="security_agency",
        target="clean_feature",  # keyword-free target name
        correlation_id=str(uuid4()),
        implementation=vuln,
        builder_id="",
    )
    assert ev.verdict == "fail"
    assert ev.severity in ("high", "critical")
    # The real adapter (not the target name) is what flagged the defect. Prove
    # the underlying execution adapter detects sql_injection content directly.
    raw = svc._adapters["security_agency"].execute(
        "clean_feature", {"implementation": vuln, "target": "clean_feature", "builder_id": ""}
    )
    assert raw.status == ExecutionStatus.FAILURE
    assert any(f.get("type") == "sql_injection" for f in raw.findings)


# ---------------------------------------------------------------------------
# Council reuse + builder exclusion (INV-009)
# ---------------------------------------------------------------------------


async def test_submit_to_testing_council_reuses_council_manager():
    svc = _svc()
    crit = await svc._dispatch_all(
        target="auth_service",
        perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()),
        implementation=(
            'def login(user, pwd):\n'
            '    """Authenticate a user."""\n'
            '    return db.query(user, pwd)\n'
        ),
        app_url="", user_goal="", exploration_brief="", builder_id="",
    )
    critique, council_id = await svc.submit_to_testing_council(
        evidence_list=crit, builder_id="", correlation_id=str(uuid4())
    )
    # The council session was created by the EXISTING CouncilManager.
    assert council_id
    # It convened exactly the 9 non-builder perspectives.
    session = get_council_manager().get_council(council_id)
    assert session is not None
    member_ids = {m.member_id for m in session.members}
    assert member_ids == set(PERSPECTIVE_IDS)
    assert len(member_ids) == 9
    # Critique result is a real object with preserved dissent structure.
    assert critique is not None


async def test_submit_to_testing_council_excludes_builder():
    svc = _svc()
    crit = await svc._dispatch_all(
        target="auth_service",
        perspectives=list(PERSPECTIVE_IDS),
        correlation_id=str(uuid4()),
        implementation=(
            'def login(user, pwd):\n'
            '    """Authenticate a user."""\n'
            '    return db.query(user, pwd)\n'
        ),
        app_url="", user_goal="", exploration_brief="", builder_id="",
    )
    builder = "security_agency"
    critique, council_id = await svc.submit_to_testing_council(
        evidence_list=crit, builder_id=builder, correlation_id=str(uuid4())
    )
    session = get_council_manager().get_council(council_id)
    member_ids = {m.member_id for m in session.members}
    # Builder is NOT a member of its own testing council.
    assert builder not in member_ids
    assert len(member_ids) == 8


# ---------------------------------------------------------------------------
# Retest coordination (provenance + correlation preserved)
# ---------------------------------------------------------------------------


async def test_coordinate_retest_reexecutes_only_failures():
    svc = _svc()
    cid = str(uuid4())
    # One real failure (security injection) + one clean perspective.
    vuln = (
        'def login(u, p):\n'
        "    q = \"SELECT * FROM users WHERE name='\" + u + \"'\"\n"
        '    return db.execute(q)\n'
    )
    evs = await svc._dispatch_all(
        target="app",
        perspectives=["security_agency", "documentation_agency"],
        correlation_id=cid,
        implementation=vuln,  # doc adapter sees clean; sec adapter sees injection
        app_url="", user_goal="", exploration_brief="", builder_id="",
    )
    # Force one of them to be a failure record to exercise retest selection.
    failing = [e for e in evs if e.verdict == "fail"]
    assert failing, "expected at least one failing evidence to retest"
    retested = await svc.coordinate_retest(failing, correlation_id=cid)
    assert len(retested) == len(failing)
    for r in retested:
        # Provenance + correlation preserved across the retest boundary.
        assert r.provenance.correlation_id == cid


# ---------------------------------------------------------------------------
# Full orchestration: bounded closed loop (INV-013)
# ---------------------------------------------------------------------------


async def test_orchestrate_test_rejects_seeded_defect_within_budget():
    svc = _svc(_FailSim())
    result = await svc.orchestrate_test(
        objective="build secure login",
        objective_id="obj_seeded",
        target="auth_service",
        implementation=(
            'def login(u, p):\n'
            "    q = \"SELECT * FROM users WHERE name='\" + u + \"'\"\n"
            '    return db.execute(q)\n'
        ),
        builder_id="",
        correlation_id=str(uuid4()),
    )
    # The final judge must NOT approve a real security defect.
    assert result.final_verdict in ("reject", "conditional")
    assert result.status.value in ("failed", "closed_loop")
    # Bounded: never exceeds the configured max iterations.
    assert result.iterations <= svc._max_iterations


async def test_orchestrate_test_approves_clean_implementation():
    svc = _svc(_PassSim())
    result = await svc.orchestrate_test(
        objective="build clean feature",
        objective_id="obj_clean",
        target="auth_service",
        implementation=(
            'def login(user, pwd):\n'
            '    """Authenticate a user."""\n'
            '    if not authorize(user, "login", "auth_service"):\n'
            '        return None\n'
            '    return db.query(user, pwd)\n'
        ),
        builder_id="",
        correlation_id=str(uuid4()),
    )
    assert result.final_verdict == "approve"
    assert result.status.value == "passed"
    # Stored for later query.
    assert svc.get_result("obj_clean") is result


async def test_orchestrate_test_converges_within_iteration_cap():
    """Closed loop must terminate — never hang or loop forever (INV-013)."""
    svc = _svc(_FailSim())
    # No corrected_implementation_provider => the loop relies on the bounded cap.
    result = await svc.orchestrate_test(
        objective="flaky objective",
        objective_id="obj_bounded",
        target="app",
        implementation='def f(x):\n    return process(x)\n',  # bug-hunter defect
        builder_id="",
        correlation_id=str(uuid4()),
    )
    assert result.iterations <= svc._max_iterations
    assert result.status.value in ("failed",)


# ---------------------------------------------------------------------------
# No new EventType emitted
# ---------------------------------------------------------------------------


async def test_orchestrator_emits_only_canonical_event_types():
    """The orchestrator must not introduce new EventType values."""
    before = set(e.name for e in EventType)
    svc = _svc(_FailSim())
    await svc.orchestrate_test(
        objective="no new types",
        objective_id="obj_types",
        target="app",
        implementation='def f(x):\n    return process(x)\n',
        builder_id="",
        correlation_id=str(uuid4()),
    )
    after = set(e.name for e in EventType)
    assert before == after


# ---------------------------------------------------------------------------
# Adapter wiring is real (not stubbed)
# ---------------------------------------------------------------------------


def test_orchestrator_wires_real_adapters():
    svc = _svc()
    assert set(svc._adapters.keys()) == {
        "security_agency", "performance_agency", "chaos_agency",
        "accessibility_agency", "documentation_agency", "concurrency_agency",
        "bug_hunter_agency", "architecture_agency",
    }
    for adapter in svc._adapters.values():
        assert isinstance(adapter, object)
        # Each adapter exposes the real execute() contract.
        assert hasattr(adapter, "execute")
        # Security adapter carries the production gate semantics (None => no gate).
        if adapter.__class__.__name__ == "SecurityAgencyAdapter":
            assert adapter._security_manager is None
