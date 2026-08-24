"""
M7-H — Security integration tests.

Proves:
  * SecurityAgencyAdapter's analysis path is authorized by SecurityManager
    (the final authority); a DENY yields SKIPPED, never a fabricated verdict.
  * SkillSpecTorGate is an INTEGRATION GATE, not the final authority.
  * The external hermes-agent(EXT) worker never receives source code / internal
    API contracts (INV-008) and never issues a verdict (observations only).
  * The builder cannot self-approve (INV-009) — enforced through the final judge.
"""

from __future__ import annotations

import inspect
from uuid import uuid4

import pytest

from aios.adapters.security_agency_adapter import SecurityAgencyAdapter
from aios.adapters.hermes_bridge import HermesObservation, HermesTask
from aios.core.security_manager import SecurityManager, SecurityDecision, SkillSpecTorGate
from aios.core.user_simulation_agent import UserSimulationAgent
from aios.core.testing_evidence import Provenance, TestingEvidence
from aios.core.ai_agency import FinalJudgeAgency, AgencyRequest, AgencyType, Verdict
from aios.events.core.bus import EventBus, reset_event_bus_singleton


@pytest.fixture(autouse=True)
def _bus():
    reset_event_bus_singleton()
    EventBus()
    yield
    reset_event_bus_singleton()


# ---------------------------------------------------------------------------
# SecurityManager is the final authority for the analysis path
# ---------------------------------------------------------------------------

def test_security_adapter_skips_when_manager_denies():
    sm = SecurityManager()
    adapter = SecurityAgencyAdapter(security_manager=sm)
    # SecurityManager.authorize is fail-closed (DENY for unknown principal).
    r = adapter.execute("auth_service", {"implementation": "x = 1", "target": "t", "builder_id": ""})
    assert r.status.value == "skipped"
    assert r.raw.get("authorization") == SecurityDecision.DENY.value


def test_security_manager_allow_required_for_analysis():
    sm = SecurityManager()
    # No explicit allow rule -> DENY (fail-closed). The final authority governs.
    decision = sm.authorize("testing_council", "security_scan", "auth_service", context={})
    assert decision != SecurityDecision.ALLOW


# ---------------------------------------------------------------------------
# SkillSpecTorGate is an integration gate, not final authority
# ---------------------------------------------------------------------------

def test_skillspectortor_is_integration_gate_not_final_authority():
    gate = SkillSpecTorGate(llm_stage_enabled=False)
    # It must NOT be the SecurityManager (the final authority).
    assert not isinstance(gate, SecurityManager)
    # It exposes an enable flag (integration gate semantics), not a verdict of
    # last resort over the whole testing pipeline.
    assert isinstance(gate.is_enabled, bool)


def test_skillspectortor_rejects_llm_stage_enabled():
    with pytest.raises(Exception):
        SkillSpecTorGate(llm_stage_enabled=True)


# ---------------------------------------------------------------------------
# No source-code exposure to the external worker; observations only
# ---------------------------------------------------------------------------

def test_user_simulation_agent_has_no_source_code_param():
    sig = inspect.signature(UserSimulationAgent.__init__)
    assert "source_code" not in sig.parameters
    assert "implementation" not in sig.parameters
    sim_sig = inspect.signature(UserSimulationAgent.simulate)
    assert "source_code" not in sim_sig.parameters
    assert "implementation" not in sim_sig.parameters


class _RecordingBridge:
    def __init__(self):
        self.sent = []

    def _create_session_id(self):
        return "hermes_deadbeef"

    async def create_worker_session(self, environment=None):
        return "hermes_deadbeef"

    async def navigate(self, session_id, url):
        return HermesObservation(task_id="nav_1", success=True, data={}, error=None,
                                 timestamp=None, session_id=session_id, provenance={})

    async def extract_content(self, session_id, selector=None):
        return HermesObservation(task_id="ex_1", success=True, data={}, error=None,
                                 timestamp=None, session_id=session_id, provenance={})

    async def execute_task(self, task: HermesTask):
        self.sent.append(task)
        return HermesObservation(task_id="t_1", success=True, data={}, error=None,
                                timestamp=None, session_id=task.session_id, provenance={})

    async def close_worker_session(self, session_id):
        return True


async def test_external_worker_receives_no_source_code():
    bridge = _RecordingBridge()
    agent = UserSimulationAgent(bridge)
    await agent.simulate(app_url="http://app", user_goal="log in", exploration_brief="explore")
    # Scan every task parameter blob for any source-like content.
    for task in bridge.sent:
        dumped = str(task.parameters)
        assert "def " not in dumped
        assert "import " not in dumped


async def test_external_worker_returns_observations_not_verdict():
    bridge = _RecordingBridge()
    agent = UserSimulationAgent(bridge)
    result = await agent.simulate(app_url="http://app", user_goal="log in", exploration_brief="explore")
    assert not hasattr(result, "verdict")


# ---------------------------------------------------------------------------
# Builder cannot self-approve (INV-009)
# ---------------------------------------------------------------------------

async def test_builder_cannot_self_approve_via_final_judge():
    builder_id = "security_agency"
    ev = TestingEvidence(
        perspective=builder_id, target="svc", test_id="t1",
        severity="low", confidence=0.9, reproducibility=1.0, verdict="pass",
        provenance=Provenance(
            source=builder_id, worker="local", session="sec_abc",
            timestamp="2026-08-24T00:00:00+00:00", environment="builder",
            correlation_id="cid", test_id="t1"))
    judge = FinalJudgeAgency()
    resp = await judge.review_evidence([ev], builder_id=builder_id)
    assert resp.verdict == Verdict.REJECT
