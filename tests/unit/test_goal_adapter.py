"""Unit tests for the T1 plan-to-workflow adapter.

``plan_to_workflow`` is a PURE function: it takes a plan dict and an
output path, and returns a ``WorkflowDefinition``. It does not touch
the kernel, the WorkflowManager, the filesystem, or any global state.
These tests therefore exercise the adapter in isolation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aios.core.workflow import WorkflowDefinition, WorkflowStep
from aios.goals.adapter import (
    GOAL_HANDLER_SERVICE,
    GOAL_STEP_ID,
    plan_to_workflow,
)


def _make_plan(**overrides: Any) -> dict[str, Any]:
    """Build a representative plan dict for tests.

    The defaults mimic the structure produced by
    ``PlanningService.plan()``: a deterministic plan_id/task_id, a
    short goal, the canonical four planning labels, and an empty
    resources/advisory_context dict.
    """
    plan: dict[str, Any] = {
        "plan_id": "plan_test_abc123",
        "task_id": "task_test_xyz789",
        "goal": "hello world",
        "steps": ["coding", "review", "testing", "deployment"],
        "resources": {},
        "advisory_context": {},
    }
    plan.update(overrides)
    return plan


class TestPlanToWorkflow:
    """Pure-function tests for plan_to_workflow."""

    def test_workflow_id_comes_from_plan_plan_id(self, tmp_path: Path) -> None:
        """workflow_id is the plan's plan_id."""
        plan = _make_plan(plan_id="plan_xyz_unique")
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert wf.workflow_id == "plan_xyz_unique"

    def test_returns_workflow_definition_instance(self, tmp_path: Path) -> None:
        """The return value is a WorkflowDefinition instance."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert isinstance(wf, WorkflowDefinition)

    def test_exactly_one_workflow_step(self, tmp_path: Path) -> None:
        """The definition contains exactly ONE step (T1 invariant)."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert len(wf.steps) == 1

    def test_step_is_workflow_step_instance(self, tmp_path: Path) -> None:
        """The single step is a WorkflowStep."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert isinstance(wf.steps[0], WorkflowStep)

    def test_step_service_is_goal_handler_v1(self, tmp_path: Path) -> None:
        """The single step's service is goal.handler.v1."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert wf.steps[0].service == GOAL_HANDLER_SERVICE
        assert wf.steps[0].service == "goal.handler.v1"

    def test_step_id_is_deterministic(self, tmp_path: Path) -> None:
        """The step_id is the canonical T1 step id."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert wf.steps[0].step_id == GOAL_STEP_ID
        assert wf.steps[0].step_id == "goal_step_1"

    def test_step_depends_on_is_empty(self, tmp_path: Path) -> None:
        """The T1 step has no dependencies (it is the only step)."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert wf.steps[0].depends_on == []

    def test_step_is_required(self, tmp_path: Path) -> None:
        """The T1 step is required (failure fails the workflow)."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert wf.steps[0].required is True

    def test_goal_preserved_in_payload(self, tmp_path: Path) -> None:
        """The goal text is preserved in the step payload."""
        plan = _make_plan(goal="a very specific goal")
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert wf.steps[0].payload["goal"] == "a very specific goal"

    def test_plan_id_preserved_in_payload(self, tmp_path: Path) -> None:
        """The plan_id is preserved in the step payload."""
        plan = _make_plan(plan_id="plan_preserved_id")
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert wf.steps[0].payload["plan_id"] == "plan_preserved_id"

    def test_task_id_preserved_in_payload(self, tmp_path: Path) -> None:
        """The task_id is preserved in the step payload."""
        plan = _make_plan(task_id="task_preserved_id")
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert wf.steps[0].payload["task_id"] == "task_preserved_id"

    def test_output_path_preserved_in_payload(self, tmp_path: Path) -> None:
        """The output_path is preserved in the step payload as a string."""
        out = tmp_path / "subdir" / "goal.txt"
        wf = plan_to_workflow(_make_plan(), out)
        assert wf.steps[0].payload["output_path"] == str(out)

    def test_output_path_accepts_str_input(self, tmp_path: Path) -> None:
        """The output_path parameter accepts a plain string."""
        out = str(tmp_path / "goal.txt")
        wf = plan_to_workflow(_make_plan(), out)  # type: ignore[arg-type]
        assert wf.steps[0].payload["output_path"] == out

    def test_planning_labels_do_not_become_workflow_steps(self, tmp_path: Path) -> None:
        """planning labels (coding/review/testing/deployment) do NOT produce
        additional executable steps. The T1 slice must contain exactly ONE
        step even when the plan has four planning labels.
        """
        plan = _make_plan(steps=["coding", "review", "testing", "deployment"])
        wf = plan_to_workflow(plan, tmp_path / "out.txt")

        # Exactly one executable step, regardless of label count.
        assert len(wf.steps) == 1

        # The labels are preserved in the payload as PLANNING METADATA only.
        assert wf.steps[0].payload["planning_labels"] == [
            "coding",
            "review",
            "testing",
            "deployment",
        ]

        # The single step's service is still goal.handler.v1 — not anything
        # resembling a label-derived service name.
        assert wf.steps[0].service == "goal.handler.v1"

    def test_planning_labels_with_many_entries_still_one_step(self, tmp_path: Path) -> None:
        """Even with an arbitrary number of planning labels, the workflow
        contains exactly ONE step."""
        many_labels = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        plan = _make_plan(steps=many_labels)
        wf = plan_to_workflow(plan, tmp_path / "out.txt")

        assert len(wf.steps) == 1
        assert wf.steps[0].payload["planning_labels"] == many_labels
        assert wf.steps[0].service == "goal.handler.v1"

    def test_planning_labels_with_empty_steps_still_one_step(self, tmp_path: Path) -> None:
        """Even with zero planning labels, the workflow has exactly one step."""
        plan = _make_plan(steps=[])
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert len(wf.steps) == 1
        assert wf.steps[0].payload["planning_labels"] == []

    def test_step_event_type_is_goal_handler(self, tmp_path: Path) -> None:
        """The step's event_type is goal.handler.v1.execute (stable,
        descriptive, and does not imply LLM execution)."""
        wf = plan_to_workflow(_make_plan(), tmp_path / "out.txt")
        assert wf.steps[0].event_type == "goal.handler.v1.execute"

    def test_definition_metadata_contains_plan_id(self, tmp_path: Path) -> None:
        """The WorkflowDefinition's metadata echoes plan_id/task_id for
        observability."""
        plan = _make_plan(plan_id="plan_meta", task_id="task_meta")
        wf = plan_to_workflow(plan, tmp_path / "out.txt")
        assert wf.metadata.get("plan_id") == "plan_meta"
        assert wf.metadata.get("task_id") == "task_meta"
        assert wf.metadata.get("t1_slice") is True

    def test_is_pure_no_side_effects(self, tmp_path: Path) -> None:
        """plan_to_workflow is a pure function: calling it twice with the
        same inputs yields equivalent definitions and produces no
        filesystem side effects."""
        plan = _make_plan()
        out = tmp_path / "out.txt"
        before = list(tmp_path.iterdir())

        wf_a = plan_to_workflow(plan, out)
        wf_b = plan_to_workflow(plan, out)

        after = list(tmp_path.iterdir())

        # No side effects on the filesystem.
        assert before == after
        # Equivalent definitions (workflow_id, name, step count, service).
        assert wf_a.workflow_id == wf_b.workflow_id
        assert wf_a.steps[0].service == wf_b.steps[0].service


class TestPlanToWorkflowInputValidation:
    """Input validation: the adapter must require a plan_id."""

    def test_missing_plan_id_raises_keyerror(self, tmp_path: Path) -> None:
        """A plan without plan_id raises KeyError (we use the value as the
        workflow_id; that is the documented contract)."""
        plan = _make_plan()
        del plan["plan_id"]
        with pytest.raises(KeyError):
            plan_to_workflow(plan, tmp_path / "out.txt")
