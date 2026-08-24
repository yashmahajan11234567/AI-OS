"""
M7-A — TestingEvidence schema unit tests.

Covers immutability, validation, provenance integrity, serialization round-trip,
and the UserSimulationCompleted → TestingEvidence normalization path
(M7-D integration boundary).
"""

from __future__ import annotations

import pytest

from aios.core.testing_evidence import (
    Provenance,
    TestingEvidence,
    UserSimulationCompleted,
    normalize_user_simulation,
    Severity,
    PerspectiveVerdict,
    VALID_SEVERITIES,
    VALID_VERDICTS,
)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def test_provenance_requires_all_mandatory_fields():
    with pytest.raises(ValueError):
        Provenance(source="", worker="w", session="s", timestamp="t", environment="e").validate()


def test_provenance_roundtrip():
    p = Provenance(
        source="security_agency",
        worker="local",
        session="sec_abc12345",
        timestamp="2026-08-24T00:00:00+00:00",
        environment="tester",
        correlation_id="cid-1",
        test_id="t1",
    )
    p.validate()
    d = p.to_dict()
    assert d["source"] == "security_agency"
    assert Provenance.from_dict(d) == p


# ---------------------------------------------------------------------------
# TestingEvidence
# ---------------------------------------------------------------------------

def _valid_evidence(**overrides) -> TestingEvidence:
    prov = Provenance(
        source="security_agency",
        worker="local",
        session="sec_abc12345",
        timestamp="2026-08-24T00:00:00+00:00",
        environment="tester",
        correlation_id="cid-1",
        test_id="t1",
    )
    base = dict(
        perspective="security_agency",
        target="auth_service",
        test_id="t1",
        severity="medium",
        confidence=0.9,
        reproducibility=1.0,
        verdict="fail",
        provenance=prov,
    )
    return TestingEvidence(**{**base, **overrides})


def test_evidence_immutable():
    ev = _valid_evidence()
    with pytest.raises(Exception):  # frozen dataclass -> cannot assign
        ev.severity = "critical"


def test_evidence_rejects_bad_severity():
    ev = _valid_evidence(severity="catastrophic")
    with pytest.raises(ValueError):
        ev.validate()


def test_evidence_rejects_bad_verdict():
    ev = _valid_evidence(verdict="maybe")
    with pytest.raises(ValueError):
        ev.validate()


def test_evidence_rejects_out_of_range_confidence():
    ev = _valid_evidence(confidence=1.5)
    with pytest.raises(ValueError):
        ev.validate()


def test_evidence_rejects_out_of_range_reproducibility():
    ev = _valid_evidence(reproducibility=-0.1)
    with pytest.raises(ValueError):
        ev.validate()


def test_evidence_rejects_missing_provenance():
    ev = TestingEvidence(
        perspective="x", target="y", test_id="z",
        severity="low", verdict="pass", provenance=None,
    )
    with pytest.raises(ValueError):
        ev.validate()


def test_evidence_serialization_roundtrip():
    ev = _valid_evidence()
    ev.validate()
    restored = TestingEvidence.from_dict(ev.to_dict())
    assert restored == ev
    restored.validate()


def test_evidence_is_failure_helper():
    assert _valid_evidence(verdict="fail").is_failure() is True
    assert _valid_evidence(verdict="pass").is_failure() is False


def test_severity_rank_ordering():
    assert Severity.rank("critical") > Severity.rank("high") > Severity.rank("medium") > Severity.rank("low")


def test_valid_constants_exhaustive():
    assert set(VALID_SEVERITIES) == {"critical", "high", "medium", "low"}
    assert set(VALID_VERDICTS) == {"pass", "fail", "inconclusive"}


# ---------------------------------------------------------------------------
# UserSimulationCompleted -> TestingEvidence normalization
# ---------------------------------------------------------------------------

def _sim(**overrides) -> UserSimulationCompleted:
    base = dict(
        goal="log in",
        goal_completion_pct=0.0,
        workflow_success=False,
        usability_blockers=[],
        navigation_failures=["could not load"],
        missing_feedback=[],
    )
    return UserSimulationCompleted(**{**base, **overrides})


def _sim_provenance() -> Provenance:
    return Provenance(
        source="user_simulation",
        worker="hermes_agent_ext",
        session="hermes_abc12345def",
        timestamp="2026-08-24T00:00:00+00:00",
        environment="ai_os_hermes_bridge",
        correlation_id="cid-2",
        test_id="usim_1",
    )


def test_normalize_blocked_goal_is_fail():
    sim = _sim(goal_completion_pct=0.1, usability_blockers=["submit missing"])
    ev = normalize_user_simulation(sim, target="app", test_id="t", provenance=_sim_provenance())
    assert ev.verdict == PerspectiveVerdict.FAIL.value
    assert ev.severity in (Severity.CRITICAL.value, Severity.HIGH.value)
    assert ev.perspective == "user_simulation"
    assert ev.provenance.source == "user_simulation"


def test_normalize_success_is_pass():
    sim = _sim(goal_completion_pct=1.0, workflow_success=True, usability_blockers=[], navigation_failures=[])
    ev = normalize_user_simulation(sim, target="app", test_id="t", provenance=_sim_provenance())
    assert ev.verdict == PerspectiveVerdict.PASS.value
    assert ev.severity == Severity.LOW.value


def test_normalize_requires_valid_provenance():
    sim = _sim()
    with pytest.raises(ValueError):
        normalize_user_simulation(sim, target="app", test_id="t", provenance=None)
