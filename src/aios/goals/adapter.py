"""T1 first user-goal vertical slice: plan-to-workflow adapter.

This module contains a single pure transformation:

    plan_to_workflow(plan, output_path) -> WorkflowDefinition

The function is intentionally minimal: it takes a plan dict produced by
``PlanningService.plan()`` and the output path supplied by the entry point,
and produces a ``WorkflowDefinition`` containing exactly ONE
``WorkflowStep`` whose ``service`` is ``"goal.handler.v1"``.

Per the T1 vertical-slice specification, the planning labels in
``plan["steps"]`` (e.g. ``["coding", "review", "testing", "deployment"]``)
are treated as PLANNING METADATA only and are NOT converted into
executable workflow steps. This keeps the T1 slice to a single deterministic
filesystem write and prevents it from becoming a multi-stage workflow.

The function does not touch global state, does not perform I/O, and does
not import or instantiate any managers. It is a pure function of its
inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aios.core.workflow import WorkflowDefinition, WorkflowStep

# The service name that the WorkflowManager will resolve to the goal_handler.
# Kept as a module-level constant so the integration test, the entry point,
# and the handler all agree on a single string.
GOAL_HANDLER_SERVICE: str = "goal.handler.v1"

# A deterministic step_id for the single T1 step. The T1 slice always has
# exactly one step, so a fixed id is appropriate and easier to assert on.
GOAL_STEP_ID: str = "goal_step_1"

# A deterministic workflow name. Combined with the plan_id (used as
# workflow_id) this is purely descriptive.
_GOAL_WORKFLOW_NAME: str = "T1 Goal Vertical Slice"


def plan_to_workflow(
    plan: dict[str, Any],
    output_path: str | Path,
) -> WorkflowDefinition:
    """Convert a plan dict into a single-step WorkflowDefinition.

    This is a pure transformation:

      * ``workflow_id`` is taken from ``plan["plan_id"]``.
      * The returned definition contains exactly one ``WorkflowStep``.
      * The step's ``service`` is ``"goal.handler.v1"`` (resolved at runtime
        to ``goal_handler`` in :mod:`aios.goals.entry_point`).
      * The original goal, plan_id, and task_id are preserved in the step
        payload so the handler can verify the request.
      * The ``output_path`` is included in the step payload so the handler
        knows where to write the goal text deterministically.
      * ``plan["steps"]`` (planning labels) are NOT used to create
        additional workflow steps. They are preserved in the step payload
        as ``planning_labels`` for observability only.

    Args:
        plan: The plan dict produced by ``PlanningService.plan()``.
        output_path: Filesystem path the handler will write the goal text
            to. Supplied explicitly to keep the transformation pure.

    Returns:
        A ``WorkflowDefinition`` containing exactly one step.
    """
    # Normalize output_path to a string for payload transport. The handler
    # will accept either str or Path; we send a string for clean JSON
    # serialization in any event/state logging.
    output_path_str = str(Path(output_path))

    payload: dict[str, Any] = {
        "goal": plan.get("goal", ""),
        "plan_id": plan.get("plan_id", ""),
        "task_id": plan.get("task_id", ""),
        "output_path": output_path_str,
        # Planning labels are PLANNING METADATA ONLY for T1.
        # They are preserved here purely for observability/audit; the
        # T1 slice contains exactly one executable step regardless of
        # how many planning labels are present.
        "planning_labels": list(plan.get("steps", [])),
    }

    step = WorkflowStep(
        step_id=GOAL_STEP_ID,
        name="Goal Handler",
        service=GOAL_HANDLER_SERVICE,
        event_type="goal.handler.v1.execute",
        payload=payload,
        depends_on=[],
        required=True,
    )

    return WorkflowDefinition(
        workflow_id=plan["plan_id"],
        name=_GOAL_WORKFLOW_NAME,
        description=(
            "T1 first user-goal vertical slice: deterministic filesystem "
            "write of the goal text. Planning labels are metadata only."
        ),
        steps=[step],
        metadata={
            "t1_slice": True,
            "plan_id": plan.get("plan_id", ""),
            "task_id": plan.get("task_id", ""),
        },
    )


__all__ = [
    "plan_to_workflow",
    "GOAL_HANDLER_SERVICE",
    "GOAL_STEP_ID",
]
