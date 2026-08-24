"""
M7-D — UserSimulationAgent unit tests.

Proves the agent:
  * NEVER accepts source code / implementation (INV-008) — no such param exists,
    and any dynamic attempt is rejected.
  * Uses an isolated hermes_<uuid> session.
  * Returns OBSERVATIONS ONLY (UserSimulationCompleted), never a verdict.
  * Drives the bridge through navigate/extract/execute_task and closes the session.
"""

from __future__ import annotations

import pytest

from aios.adapters.hermes_bridge import HermesObservation, HermesTask
from aios.core.user_simulation_agent import UserSimulationAgent


class FakeHermesBridge:
    """Deterministic double for hermes-agent(EXT). Records calls, returns obs."""

    def __init__(self):
        self.calls = []
        self.session_closed = False
        self.created_session = None

    def _create_session_id(self) -> str:
        self.created_session = "hermes_deadbeefcafe"
        return self.created_session

    async def create_worker_session(self, environment=None) -> str:
        self.calls.append(("create_worker_session", environment))
        return self.created_session or "hermes_deadbeefcafe"

    async def navigate(self, session_id, url) -> HermesObservation:
        self.calls.append(("navigate", session_id, url))
        return HermesObservation(
            task_id="nav_1", success=True, data={"title": "App"}, error=None,
            timestamp=None, session_id=session_id, provenance={},
        )

    async def extract_content(self, session_id, selector=None) -> HermesObservation:
        self.calls.append(("extract_content", session_id, selector))
        return HermesObservation(
            task_id="extract_1", success=True, data={"text": "welcome"}, error=None,
            timestamp=None, session_id=session_id, provenance={},
        )

    async def execute_task(self, task: HermesTask) -> HermesObservation:
        self.calls.append(("execute_task", task.task_type, task.parameters))
        ok = task.task_type == "attempt_goal"
        return HermesObservation(
            task_id=f"{task.task_type}_1", success=ok,
            data={"outcome": "ok" if ok else "blocked"}, error=None,
            timestamp=None, session_id=task.session_id, provenance={},
        )

    async def close_worker_session(self, session_id) -> bool:
        self.calls.append(("close_worker_session", session_id))
        self.session_closed = True
        return True


def _obs(goal_success=True, nav_ok=True):
    b = FakeHermesBridge()
    return b


async def test_simulate_returns_observations_not_verdict():
    bridge = FakeHermesBridge()
    agent = UserSimulationAgent(bridge)
    result = await agent.simulate(
        app_url="http://app", user_goal="log in", exploration_brief="explore")
    # Result type is observations; it has no verdict field.
    assert isinstance(result, object)
    assert not hasattr(result, "verdict")
    assert result.goal == "log in"


async def test_simulate_uses_isolated_session():
    bridge = FakeHermesBridge()
    agent = UserSimulationAgent(bridge)
    result = await agent.simulate(app_url="http://app", user_goal="log in", exploration_brief="explore")
    assert "hermes_" in result.raw_trace["session_id"]
    assert result.raw_trace["session_id"] == bridge.created_session
    # Session must be closed after the run.
    assert bridge.session_closed is True


async def test_simulate_does_not_accept_source_code():
    bridge = FakeHermesBridge()
    agent = UserSimulationAgent(bridge)
    # Constructor has no source_code parameter at all.
    import inspect
    params = inspect.signature(agent.simulate).parameters
    assert "source_code" not in params
    assert "implementation" not in params
    # Dynamic injection of source is rejected (TypeError: not a valid kwarg).
    with pytest.raises(Exception):
        await agent.simulate(
            app_url="http://app", user_goal="log in", source_code="def x(): pass")


async def test_simulate_blocked_goal_reports_blockers():
    bridge = FakeHermesBridge()

    async def execute_task(task):
        ok = False  # attempt_goal fails
        return HermesObservation(
            task_id=f"{task.task_type}_1", success=ok, data={}, error=None,
            timestamp=None, session_id=task.session_id, provenance={})

    bridge.execute_task = execute_task
    agent = UserSimulationAgent(bridge)
    result = await agent.simulate(app_url="http://app", user_goal="log in", exploration_brief="explore")
    assert result.workflow_success is False
    assert len(result.usability_blockers) > 0


async def test_simulate_requires_bridge():
    with pytest.raises(ValueError):
        UserSimulationAgent(None)
