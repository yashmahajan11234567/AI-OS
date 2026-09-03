"""T1 first user-goal vertical slice — public entry point.

This module composes the existing AI-OS components (PlanningService,
WorkflowManager, kernel lifecycle) to implement the smallest real
user-goal execution path:

    human goal
      -> PlanningService.plan()
      -> plan_to_workflow()             (aios.goals.adapter)
      -> WorkflowManager                (registered step handler)
      -> goal_handler.v1                (aios.goals.handler)
      -> deterministic filesystem write

The handler is registered at RUNTIME by this entry point. The kernel
itself is not modified; the entry point uses the existing public
``kernel_management`` / ``WorkflowManager`` APIs.

A kernel singleton may already be running when the entry point is
called (e.g. from inside a larger test). In that case the entry point
reuses the running kernel. If no kernel is running, the synchronous
``run_goal`` helper boots a fresh kernel, runs the goal, and stops
the kernel before returning.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from aios.core.kernel_management import is_running, run_kernel, stop_kernel
from aios.core.workflow import (
    WorkflowManager,
    WorkflowStatus,
    get_workflow_manager,
)
from aios.services.planning import PlanningService

from aios.goals.adapter import GOAL_HANDLER_SERVICE, plan_to_workflow
from aios.goals.handler import goal_handler


def _resolve_workflow_manager() -> WorkflowManager:
    """Return the global WorkflowManager singleton.

    The singleton is constructed during kernel boot by the kernel's
    Phase-4 initialization. Tests and callers that boot the kernel
    through ``run_kernel`` therefore get a fully-initialized
    WorkflowManager via ``get_workflow_manager()``.
    """
    return get_workflow_manager()


def _resolve_planning_service() -> PlanningService:
    """Construct a PlanningService.

    PlanningService is a plain engineering service with a synchronous
    ``plan()`` method. It does not require a running kernel to produce
    a plan — it only reads from the in-process LearningService if
    available, and falls back gracefully otherwise. We construct a fresh
    instance per call so the entry point has no hidden global state.
    """
    return PlanningService()


async def run_goal_async(
    goal_text: str,
    output_path: Path,
) -> dict[str, Any]:
    """Execute the T1 vertical slice asynchronously.

    This is the primary entry point. It assumes the kernel is already
    running (or has been started by the caller). It:

      1. Calls ``PlanningService.plan({"goal": goal_text})``.
      2. Converts the resulting plan dict to a single-step
         ``WorkflowDefinition`` via ``plan_to_workflow``.
      3. Registers ``"goal.handler.v1"`` with the WorkflowManager.
      4. Registers the generated ``WorkflowDefinition``.
      5. Calls ``await workflow_manager.start_workflow(...)`` which
         blocks until the workflow execution completes.
      6. Reads the workflow status and the recorded step result.
      7. Returns a dict containing the plan, the execution_id, the
         workflow status, and the handler's write result.

    Args:
        goal_text: The user's goal text. Written verbatim to disk.
        output_path: Filesystem path the handler will write to.

    Returns:
        A dict with at minimum::

            {
                "plan": <plan dict>,
                "execution_id": "exec_<...>",
                "status": "completed" | "failed",
                "written": <str or None>,
            }

    Raises:
        RuntimeError: If the kernel is not running.
    """
    if not is_running():
        raise RuntimeError(
            "Kernel is not running. Call run_goal() (synchronous wrapper) "
            "to boot a kernel automatically, or start the kernel via "
            "aios.core.kernel_management.run_kernel() before calling "
            "run_goal_async()."
        )

    # 1. Plan.
    planning_service = _resolve_planning_service()
    plan = planning_service.plan({"goal": goal_text})
    if plan is None:
        raise RuntimeError("PlanningService.plan() returned None")

    # 2. Convert plan -> WorkflowDefinition (pure transformation).
    workflow_definition = plan_to_workflow(plan, output_path)

    # 3-4. Register handler + workflow with the WorkflowManager.
    workflow_manager = _resolve_workflow_manager()
    workflow_manager.register_step_handler(GOAL_HANDLER_SERVICE, goal_handler)
    workflow_manager.register_workflow(workflow_definition)

    # 5. Execute. ``start_workflow`` blocks until execution completes
    #    (see aios.core.workflow.start_workflow), so no extra wait is
    #    required and no events need to be subscribed to.
    execution_id = await workflow_manager.start_workflow(
        workflow_id=workflow_definition.workflow_id,
        initial_payload={"goal": goal_text, "output_path": str(output_path)},
    )

    # 6. Read status.
    state = workflow_manager.get_workflow_status(execution_id)
    status = state.get("status") if state else WorkflowStatus.FAILED.value

    # The handler's return value is recorded by WorkflowManager in
    # ``state["step_results"][step_id]``. Extract it for the caller.
    written: Any = None
    if state:
        step_results = state.get("step_results", {}) or {}
        # The recorded key may be either the bare step_id ("goal_step_1")
        # or a dotted key ("step_results.goal_step_1") depending on
        # the WorkflowManager's storage path. We check both.
        recorded = step_results.get("goal_step_1")
        if isinstance(recorded, dict):
            written = recorded
        else:
            # Fall back: scan dotted keys.
            for key, value in step_results.items():
                if key.endswith("goal_step_1") and isinstance(value, dict):
                    written = value
                    break

    return {
        "plan": plan,
        "execution_id": execution_id,
        "status": status,
        "written": written,
    }


def _run_goal_managed(
    goal_text: str,
    output_path: Path,
) -> dict[str, Any]:
    """Internal helper: drive run_goal_async inside a single event loop.

    This helper exists so the synchronous ``run_goal`` wrapper can boot
    a kernel, execute the goal, and stop the kernel all within the SAME
    event loop. Sharing a single loop is required because the kernel,
    WorkflowManager, and EventBus maintain global state that is bound
    to the loop under which ``run_kernel`` / ``start_workflow`` /
    ``stop_kernel`` were first called.
    """
    kernel_was_running = is_running()
    if not kernel_was_running:
        # Boot a fresh kernel inside this loop.
        asyncio.run(run_kernel())

    try:
        return asyncio.run(run_goal_async(goal_text, output_path))
    finally:
        if not kernel_was_running:
            # Only stop the kernel if we started it.
            asyncio.run(stop_kernel())


def run_goal(
    goal_text: str,
    output_path: Path,
) -> dict[str, Any]:
    """Synchronous entry point for the T1 vertical slice.

    Boots a kernel if one is not already running, runs the goal
    asynchronously, then stops the kernel (only if THIS call started
    it). Existing kernel singletons are not torn down.

    Note: this wrapper uses ``asyncio.run`` internally to bridge sync
    callers into the async world. As a consequence it cannot be invoked
    from inside an already-running event loop — async callers should
    use :func:`run_goal_async` directly.

    Args:
        goal_text: The user's goal text. Written verbatim to disk.
        output_path: Filesystem path the handler will write to.

    Returns:
        See :func:`run_goal_async`.
    """
    return _run_goal_managed(goal_text, output_path)


__all__ = [
    "run_goal",
    "run_goal_async",
    "GOAL_HANDLER_SERVICE",
]
