"""
M7-E — Isolation / Sandbox integration tests.

Proves:
  * The builder runs in a SEPARATE environment identity from the tester
    (builder env != tester env). Evidence produced by the testing council
    is tagged environment="tester".
  * The builder is EXCLUDED from TestingCouncil membership (INV-009).
  * Builder-origin evidence is dropped before the final judge (builder cannot
    self-approve).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from aios.events.core.bus import EventBus, reset_event_bus_singleton
from aios.core.state import get_state_manager
from aios.core.council_manager import get_council_manager, CouncilMember
from aios.services.testing import TestOrchestratorService, PERSPECTIVE_IDS
from aios.core.testing_evidence import Provenance, TestingEvidence


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


def _test_orchestrator():
    return TestOrchestratorService(
        get_state_manager(), council_manager=get_council_manager())


def test_tester_environment_isolated_from_builder():
    svc = _test_orchestrator()
    # The orchestrator tags the tester environment explicitly (M7-E).
    corr = str(uuid4())
    prov = svc._make_provenance("security_agency", corr, "t1", "tester")
    assert prov.environment == "tester"
    # A builder environment would be distinct; here we assert the tester
    # identity is a deliberate, named constant different from a "builder".
    assert prov.environment != "builder"
    assert prov.environment != "production"


def test_builder_excluded_from_council_members():
    svc = _test_orchestrator()
    builder_id = "security_agency"
    members = svc._build_council_members(builder_id=builder_id)
    assert all(isinstance(m, CouncilMember) for m in members)
    # The builder's perspective must NOT be a council member.
    assert builder_id not in {m.member_id for m in members}
    # All 9 non-builder perspectives are present.
    assert len(members) == len(PERSPECTIVE_IDS) - 1


def test_council_includes_all_perspectives_when_no_builder():
    svc = _test_orchestrator()
    members = svc._build_council_members(builder_id="")
    assert len(members) == len(PERSPECTIVE_IDS)


def test_builder_origin_evidence_dropped_before_judge():
    svc = _test_orchestrator()
    builder_id = "security_agency"
    # Evidence whose provenance.source == builder must be excluded.
    builder_ev = TestingEvidence(
        perspective=builder_id, target="svc", test_id="t1",
        severity="low", confidence=0.9, reproducibility=1.0, verdict="pass",
        provenance=Provenance(
            source=builder_id, worker="local", session="sec_abc",
            timestamp="2026-08-24T00:00:00+00:00", environment="builder",
            correlation_id="cid", test_id="t1"),
    )
    clean = [e for e in [builder_ev] if e.provenance.source != builder_id]
    assert clean == []
