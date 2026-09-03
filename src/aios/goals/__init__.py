"""T1 first user-goal vertical slice — public API.

Exposes the synchronous and asynchronous entry points plus the canonical
service name used to register the goal handler with the WorkflowManager.
"""

from aios.goals.adapter import GOAL_HANDLER_SERVICE, plan_to_workflow
from aios.goals.entry_point import run_goal, run_goal_async
from aios.goals.handler import goal_handler

__all__ = [
    "run_goal",
    "run_goal_async",
    "plan_to_workflow",
    "goal_handler",
    "GOAL_HANDLER_SERVICE",
]
