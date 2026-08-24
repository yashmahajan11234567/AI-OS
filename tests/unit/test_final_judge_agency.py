"""
M7-G — FinalJudgeAgency independent, evidence-first verdict tests.

Proves:
  * REJECT on any critical failure (never APPROVE)
  * CONDITIONAL on high / remaining failures
  * APPROVE only when all evidence passes
  * Evidence-first: no evidence -> REJECT (no prose-only verdicts, INV-010)
  * Builder-origin evidence is EXCLUDED (INV-009 — builder cannot self-approve)
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from aios.core.ai_agency import FinalJudgeAgency, AgencyRequest, AgencyType, Verdict
from aios.core.testing_evidence import Provenance, TestingEvidence
from aios.events.core.bus import EventBus, reset_event_bus_singleton


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()  # set the canonical singleton (INV-EB-001)
    yield
    reset_event_bus_singleton()


def _prov(source="security_agency"):
    return Provenance(
        source=source, worker="local", session=f"{source}_abc12345",
        timestamp="2026-08-24T00:00:00+00:00", environment="tester",
        correlation_id="cid", test_id="t1",
    )


def _ev(verdict="pass", severity="low", perspective="security_agency"):
    return TestingEvidence(
        perspective=perspective, target="svc", test_id="t1",
        severity=severity, confidence=0.9, reproducibility=1.0,
        verdict=verdict, provenance=_prov(perspective),
    )


def _request(evidence):
    return AgencyRequest(
        request_id="fj_1", agency_type=AgencyType.FINAL_JUDGE,
        target="svc", context={"testing_evidence": list(evidence)},
        correlation_id=str(uuid4()),
    )


async def test_judge_approves_when_all_pass():
    judge = FinalJudgeAgency()
    resp = await judge.review(_request([_ev("pass", "low"), _ev("pass", "low", "performance_agency")]))
    assert resp.verdict == Verdict.APPROVE
    assert resp.metadata.get("evidence_first") is True


async def test_judge_rejects_on_critical_failure():
    judge = FinalJudgeAgency()
    resp = await judge.review(_request([_ev("fail", "critical", "security_agency")]))
    assert resp.verdict == Verdict.REJECT


async def test_judge_conditional_on_high_failure():
    judge = FinalJudgeAgency()
    resp = await judge.review(_request([
        _ev("pass", "low", "performance_agency"),
        _ev("fail", "high", "security_agency"),
    ]))
    assert resp.verdict == Verdict.CONDITIONAL


async def test_judge_conditional_on_remaining_failures():
    judge = FinalJudgeAgency()
    resp = await judge.review(_request([
        _ev("pass", "low", "performance_agency"),
        _ev("fail", "medium", "accessibility_agency"),
    ]))
    assert resp.verdict == Verdict.CONDITIONAL


async def test_judge_rejects_empty_evidence():
    judge = FinalJudgeAgency()
    resp = await judge.review(_request([]))
    assert resp.verdict == Verdict.REJECT
    assert any(f["type"] == "no_evidence" for f in resp.findings)


async def test_judge_excludes_builder_origin_evidence():
    # Builder is "builder_x"; all evidence originates from builder_x.
    builder_ev = [_ev("pass", "low", "builder_x"), _ev("pass", "low", "builder_x")]
    judge = FinalJudgeAgency()
    resp = await judge.review_evidence(builder_ev, builder_id="builder_x")
    # All builder evidence dropped -> treated as no evidence -> REJECT.
    assert resp.verdict == Verdict.REJECT
    assert resp.metadata.get("builder_excluded") is True


async def test_judge_approves_with_non_builder_evidence_only():
    # Builder is excluded but independent evidence is clean -> APPROVE.
    judge = FinalJudgeAgency()
    resp = await judge.review_evidence(
        [_ev("pass", "low", "security_agency"), _ev("pass", "low", "performance_agency")],
        builder_id="builder_x",
    )
    assert resp.verdict == Verdict.APPROVE
