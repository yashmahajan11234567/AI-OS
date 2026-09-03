"""Integration test: T1 first user-goal vertical slice.

This test exercises the COMPLETE vertical slice through the REAL kernel,
REAL ``PlanningService``, REAL ``WorkflowManager``, and a REAL registered
``goal.handler.v1`` step handler that performs a deterministic filesystem
write.

The slice under test:

    "hello world"  (goal text)
      -> PlanningService.plan({"goal": "hello world"})
      -> plan_to_workflow(plan, tmp_path / "goal.txt")
      -> WorkflowManager.register_step_handler("goal.handler.v1", goal_handler)
      -> WorkflowManager.register_workflow(definition)
      -> WorkflowManager.start_workflow(definition.workflow_id)
      -> goal_handler writes "hello world" to tmp_path / "goal.txt"
      -> workflow status == "completed"

It must NOT mock any of: PlanningService, WorkflowManager, the goal
handler, or the WorkflowManager DAG executor.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio

from aios.core import KernelConfig
from aios.core.kernel_management import (
    is_running,
    run_kernel,
    stop_kernel,
)
from aios.core.workflow import (
    WorkflowStatus,
    get_workflow_manager,
    reset_workflow_manager_singleton,
)
from aios.goals.entry_point import run_goal_async


EXPECTED_GOAL: str = "hello world"
EXPECTED_SHA256: str = hashlib.sha256(b"hello world").hexdigest()


@pytest_asyncio.fixture
async def booted_kernel() -> AsyncIterator[None]:
    """Boot a real kernel for the test and tear it down afterwards.

    Uses a temporary data directory so the test does not pollute any
    persistent state. Resets the WorkflowManager singleton around the
    boot so prior tests cannot leak step handlers or workflow
    definitions into this slice.
    """
    # Defensive: tear down anything that might already be running.
    if is_running():
        await stop_kernel()
    reset_workflow_manager_singleton()

    temp_dir = Path(tempfile.mkdtemp(prefix="t1_goal_vertical_"))
    config = KernelConfig(data_dir=temp_dir)

    try:
        await run_kernel(config)
        yield
    finally:
        if is_running():
            await stop_kernel()
        # Belt-and-suspenders: reset the workflow singleton in case
        # ``stop_kernel`` did not (e.g. if a test errored before stop).
        reset_workflow_manager_singleton()
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestT1GoalVerticalSlice:
    """End-to-end exercise of the T1 first user-goal vertical slice."""

    @pytest.mark.asyncio
    async def test_run_goal_async_writes_goal_to_disk(
        self, booted_kernel: None, tmp_path: Path
    ) -> None:
        """The full vertical slice writes 'hello world' to disk and
        returns a completed workflow status."""
        output_path = tmp_path / "goal.txt"
        assert not output_path.exists(), (
            "Pre-condition: output file must not exist before the test."
        )

        result = await run_goal_async(EXPECTED_GOAL, output_path)

        # 1. run_goal_async returned a result dict.
        assert isinstance(result, dict)

        # 2. The result contains a plan dict.
        assert "plan" in result
        assert isinstance(result["plan"], dict)
        assert result["plan"]["goal"] == EXPECTED_GOAL

        # 3. The result contains an execution_id.
        assert "execution_id" in result
        assert isinstance(result["execution_id"], str)

        # 4. The execution_id starts with "exec_".
        assert result["execution_id"].startswith("exec_"), (
            f"execution_id should start with 'exec_', "
            f"got: {result['execution_id']!r}"
        )

        # 5. Workflow status is "completed".
        assert result["status"] == WorkflowStatus.COMPLETED.value
        assert result["status"] == "completed"

        # 6. The output file exists.
        assert output_path.exists(), (
            f"output file should exist at {output_path} after vertical slice."
        )

        # 7. The file contents equal the original goal.
        assert output_path.read_text(encoding="utf-8") == EXPECTED_GOAL, (
            f"file contents should be {EXPECTED_GOAL!r}, "
            f"got: {output_path.read_text(encoding='utf-8')!r}"
        )

        # 8. The handler's reported byte count is correct.
        written = result["written"]
        assert isinstance(written, dict), (
            f"result['written'] should be a dict from the handler, "
            f"got: {written!r}"
        )
        assert written["bytes"] == len(EXPECTED_GOAL.encode("utf-8"))
        assert written["bytes"] == len("hello world")

        # 9. The handler's reported SHA-256 is correct.
        assert written["sha256"] == EXPECTED_SHA256
        assert written["sha256"] == hashlib.sha256(b"hello world").hexdigest()

        # 10. The reported 'written' path matches the requested output path.
        assert written["written"] == str(output_path)

    @pytest.mark.asyncio
    async def test_run_goal_async_uses_real_workflow_manager(
        self, booted_kernel: None, tmp_path: Path
    ) -> None:
        """The slice must go through the REAL WorkflowManager (DAG
        execution), not a mock or stub."""
        output_path = tmp_path / "another_goal.txt"

        # Sanity: the WorkflowManager singleton is real and initialized.
        wm = get_workflow_manager()
        assert wm is not None
        assert wm.is_initialized is True

        result = await run_goal_async("another goal", output_path)

        # The workflow status comes from the WorkflowManager state dict,
        # which only exists if start_workflow actually ran.
        assert result["status"] == "completed"

        # The execution_id corresponds to a real workflow state entry.
        state = wm.get_workflow_status(result["execution_id"])
        assert state is not None
        assert state["status"] == "completed"
        assert state["workflow_id"] == result["plan"]["plan_id"]

        # The step was recorded as completed.
        completed_steps = state.get("completed_steps", [])
        assert "goal_step_1" in completed_steps

        # File was written by the registered handler.
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "another goal"

    @pytest.mark.asyncio
    async def test_run_goal_async_creates_parent_directory(
        self, booted_kernel: None, tmp_path: Path
    ) -> None:
        """The handler must create intermediate parent directories if
        they do not exist (deterministic, idempotent)."""
        nested_output = tmp_path / "a" / "b" / "c" / "goal.txt"
        assert not nested_output.parent.exists()

        result = await run_goal_async("nested goal", nested_output)

        assert result["status"] == "completed"
        assert nested_output.exists()
        assert nested_output.read_text(encoding="utf-8") == "nested goal"
        assert result["written"]["sha256"] == hashlib.sha256(
            b"nested goal"
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_run_goal_async_planning_labels_remain_metadata(
        self, booted_kernel: None, tmp_path: Path
    ) -> None:
        """The planning labels emitted by PlanningService.plan() (which
        default to ['coding', 'review', 'testing', 'deployment']) must
        NOT become four workflow steps. The T1 slice always contains
        exactly one step whose service is 'goal.handler.v1'."""
        from aios.core.workflow import (
            WorkflowDefinition,
        )

        output_path = tmp_path / "labels_goal.txt"

        result = await run_goal_async("labels goal", output_path)

        assert result["status"] == "completed"

        # The plan we built contains the canonical 4 planning labels.
        plan_steps = result["plan"]["steps"]
        assert plan_steps == ["coding", "review", "testing", "deployment"]

        # But the workflow registered against the WorkflowManager
        # contains EXACTLY ONE step.
        wm = get_workflow_manager()
        workflows = wm.list_workflows()
        matching = [
            wf for wf in workflows if wf["workflow_id"] == result["plan"]["plan_id"]
        ]
        assert len(matching) == 1
        assert matching[0]["steps"] == 1, (
            "T1 slice must register exactly one workflow step, "
            "regardless of how many planning labels are in the plan."
        )

    @pytest.mark.asyncio
    async def test_run_goal_async_executes_real_registered_handler(
        self, booted_kernel: None, tmp_path: Path
    ) -> None:
        """The handler is registered at RUNTIME by the entry point under
        the service name 'goal.handler.v1', and the workflow step
        dispatches to that registration."""
        output_path = tmp_path / "registered_goal.txt"

        # The handler is registered each time run_goal_async is called.
        # We verify this indirectly: if the handler were not registered
        # for the requested service, the workflow would fail with
        # ``No handler registered for service: goal.handler.v1``.
        result = await run_goal_async("registered goal", output_path)

        assert result["status"] == "completed"
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "registered goal"
