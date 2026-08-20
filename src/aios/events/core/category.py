"""
EventCategory (Part 2 §2.2.4).

Fixed category model. Each EventType maps to exactly one category per
the Part 2 §2.3.2 mapping (enforced by EventTypeRegistry later; the core
model provides the enum and the canonical mapping table for validation).

    SYSTEM      = 'system'      // Kernel, core component, core manager lifecycle
    CONTROL     = 'control'     // Workflow orchestration, service coordination
    DATA        = 'data'        // State changes, artifacts, checkpoints, memory
    AUDIT       = 'audit'       // Governance, council decisions, AI Agency audits
    DIAGNOSTIC  = 'diagnostic'  // Metrics, traces, health checks, profiling

These five categories are fixed by the architecture; new categories are NOT
invented by the core model.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from aios.events.core.types import EventType


class EventCategory(str, Enum):
    """Immutable event category (Part 2 §2.2.4)."""

    SYSTEM = "system"
    CONTROL = "control"
    DATA = "data"
    AUDIT = "audit"
    DIAGNOSTIC = "diagnostic"

    @classmethod
    def from_name(cls, name: str) -> "EventCategory":
        try:
            return cls(name)
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Invalid EventCategory {name!r}; must be one of [{valid}]"
            ) from exc

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"EventCategory.{self.name}"


# Canonical EventType -> EventCategory mapping (Part 2 §2.3.2).
# INV-ET-001 requires every EventType to have a defined category.
_EVENT_TYPE_CATEGORY: dict[EventType, EventCategory] = {
    # === SYSTEM ===
    EventType.KERNEL_INITIALIZATION_STARTED: EventCategory.SYSTEM,
    EventType.KERNEL_READY: EventCategory.SYSTEM,
    EventType.KERNEL_SHUTDOWN_STARTED: EventCategory.SYSTEM,
    EventType.KERNEL_TERMINATED: EventCategory.SYSTEM,
    EventType.KERNEL_INITIALIZATION_FAILED: EventCategory.SYSTEM,
    EventType.KERNEL_FATAL_ERROR: EventCategory.SYSTEM,
    EventType.CORE_COMPONENT_INITIALIZED: EventCategory.SYSTEM,
    EventType.CORE_COMPONENT_SHUTDOWN: EventCategory.SYSTEM,
    EventType.CORE_COMPONENT_DEGRADED: EventCategory.SYSTEM,
    EventType.CORE_COMPONENT_FAILED: EventCategory.SYSTEM,
    EventType.CORE_MANAGER_INITIALIZED: EventCategory.SYSTEM,
    EventType.CORE_MANAGER_SHUTDOWN: EventCategory.SYSTEM,
    EventType.CORE_MANAGER_DEGRADED: EventCategory.SYSTEM,
    EventType.CORE_MANAGER_FAILED: EventCategory.SYSTEM,
    EventType.HEARTBEAT: EventCategory.SYSTEM,
    EventType.CONFIGURATION_FROZEN: EventCategory.SYSTEM,
    EventType.CONFIGURATION_CHANGED: EventCategory.SYSTEM,
    # === CONTROL ===
    EventType.WORKFLOW_STARTED: EventCategory.CONTROL,
    EventType.WORKFLOW_COMPLETED: EventCategory.CONTROL,
    EventType.WORKFLOW_FAILED: EventCategory.CONTROL,
    EventType.WORKFLOW_PAUSED: EventCategory.CONTROL,
    EventType.WORKFLOW_RESUMED: EventCategory.CONTROL,
    EventType.WORKFLOW_CANCELLED: EventCategory.CONTROL,
    EventType.WORKFLOW_STEP_STARTED: EventCategory.CONTROL,
    EventType.WORKFLOW_STEP_COMPLETED: EventCategory.CONTROL,
    EventType.WORKFLOW_STEP_FAILED: EventCategory.CONTROL,
    EventType.WORKFLOW_STEP_RETRIED: EventCategory.CONTROL,
    EventType.WORKFLOW_STEP_SKIPPED: EventCategory.CONTROL,
    EventType.WORKFLOW_CHECKPOINT_CREATED: EventCategory.CONTROL,
    EventType.WORKFLOW_CHECKPOINT_RESTORED: EventCategory.CONTROL,
    EventType.TASK_CREATED: EventCategory.CONTROL,
    EventType.TASK_ASSIGNED: EventCategory.CONTROL,
    EventType.TASK_STARTED: EventCategory.CONTROL,
    EventType.TASK_COMPLETED: EventCategory.CONTROL,
    EventType.TASK_FAILED: EventCategory.CONTROL,
    EventType.TASK_RETRIED: EventCategory.CONTROL,
    EventType.TASK_CANCELLED: EventCategory.CONTROL,
    EventType.TASK_DEPENDENCY_RESOLVED: EventCategory.CONTROL,
    EventType.RETRY_BUDGET_EXHAUSTED: EventCategory.CONTROL,
    EventType.RETRY_SCHEDULED: EventCategory.CONTROL,
    EventType.RETRY_EXECUTED: EventCategory.CONTROL,
    EventType.ROOT_CAUSE_ANALYZED: EventCategory.CONTROL,
    EventType.RECOVERY_ACTION_DISPATCHED: EventCategory.CONTROL,
    EventType.RECOVERY_ACTION_COMPLETED: EventCategory.CONTROL,
    EventType.RECOVERY_ACTION_FAILED: EventCategory.CONTROL,
    EventType.FAILURE_CLASSIFIED: EventCategory.CONTROL,
    # === DATA ===
    EventType.STATE_CHANGED: EventCategory.DATA,
    EventType.STATE_SNAPSHOT_CREATED: EventCategory.DATA,
    EventType.STATE_RESTORED: EventCategory.DATA,
    EventType.ARTIFACT_CREATED: EventCategory.DATA,
    EventType.ARTIFACT_UPDATED: EventCategory.DATA,
    EventType.ARTIFACT_DELETED: EventCategory.DATA,
    EventType.CHECKPOINT_CREATED: EventCategory.DATA,
    EventType.CHECKPOINT_RESTORED: EventCategory.DATA,
    EventType.CHECKPOINT_PRUNED: EventCategory.DATA,
    EventType.MEMORY_STORED: EventCategory.DATA,
    EventType.MEMORY_RETRIEVED: EventCategory.DATA,
    EventType.MEMORY_UPDATED: EventCategory.DATA,
    EventType.MEMORY_CONSOLIDATED: EventCategory.DATA,
    EventType.MEMORY_PRUNED: EventCategory.DATA,
    EventType.CONTEXT_ASSEMBLED: EventCategory.DATA,
    EventType.CONTEXT_COMPRESSED: EventCategory.DATA,
    # === AUDIT ===
    EventType.PLANNING_REQUESTED: EventCategory.AUDIT,
    EventType.PLANNING_COMPLETED: EventCategory.AUDIT,
    EventType.PLANNING_FAILED: EventCategory.AUDIT,
    EventType.PLAN_REJECTED: EventCategory.AUDIT,
    EventType.CODE_GENERATED: EventCategory.AUDIT,
    EventType.CODING_COMPLETED: EventCategory.AUDIT,
    EventType.CODING_FAILED: EventCategory.AUDIT,
    EventType.CODE_REVIEW_REQUESTED: EventCategory.AUDIT,
    EventType.REVIEW_STARTED: EventCategory.AUDIT,
    EventType.REVIEW_APPROVED: EventCategory.AUDIT,
    EventType.REVIEW_REJECTED: EventCategory.AUDIT,
    EventType.REVIEW_FAILED: EventCategory.AUDIT,
    EventType.SECURITY_ISSUE_FOUND: EventCategory.AUDIT,
    EventType.PERFORMANCE_ISSUE_FOUND: EventCategory.AUDIT,
    EventType.TESTS_GENERATED: EventCategory.AUDIT,
    EventType.TESTS_PASSED: EventCategory.AUDIT,
    EventType.TESTS_FAILED: EventCategory.AUDIT,
    EventType.TESTING_COMPLETED: EventCategory.AUDIT,
    EventType.TESTING_FAILED: EventCategory.AUDIT,
    EventType.DEPLOYMENT_REQUESTED: EventCategory.AUDIT,
    EventType.DEPLOYMENT_STARTED: EventCategory.AUDIT,
    EventType.DEPLOYMENT_COMPLETED: EventCategory.AUDIT,
    EventType.DEPLOYMENT_FAILED: EventCategory.AUDIT,
    EventType.DEPLOYMENT_ROLLED_BACK: EventCategory.AUDIT,
    EventType.COUNCIL_CONVENED: EventCategory.AUDIT,
    EventType.COUNCIL_PROPOSAL_SUBMITTED: EventCategory.AUDIT,
    EventType.COUNCIL_VOTE_CAST: EventCategory.AUDIT,
    EventType.COUNCIL_CONSENSUS_REACHED: EventCategory.AUDIT,
    EventType.COUNCIL_DISSENT_REGISTERED: EventCategory.AUDIT,
    EventType.COUNCIL_DECISION_FINALIZED: EventCategory.AUDIT,
    EventType.AI_AGENT_TASK_REQUESTED: EventCategory.AUDIT,
    EventType.AI_AGENT_TASK_COMPLETED: EventCategory.AUDIT,
    EventType.AI_AGENT_TASK_FAILED: EventCategory.AUDIT,
    EventType.AI_AGENT_AUDIT_EMITTED: EventCategory.AUDIT,
    EventType.FINAL_JUDGE_DECISION: EventCategory.AUDIT,
    EventType.HUMAN_ESCALATION_REQUIRED: EventCategory.AUDIT,
    # === DIAGNOSTIC ===
    EventType.METRIC_EMITTED: EventCategory.DIAGNOSTIC,
    EventType.TRACE_SPAN_STARTED: EventCategory.DIAGNOSTIC,
    EventType.TRACE_SPAN_ENDED: EventCategory.DIAGNOSTIC,
    EventType.HEALTH_CHECK_PASSED: EventCategory.DIAGNOSTIC,
    EventType.HEALTH_CHECK_FAILED: EventCategory.DIAGNOSTIC,
    EventType.SERVICE_STARTED: EventCategory.DIAGNOSTIC,
    EventType.SERVICE_STOPPED: EventCategory.DIAGNOSTIC,
    EventType.SERVICE_DEGRADED: EventCategory.DIAGNOSTIC,
    EventType.SERVICE_FAILED: EventCategory.DIAGNOSTIC,
    EventType.RESOURCE_ALLOCATED: EventCategory.DIAGNOSTIC,
    EventType.RESOURCE_RELEASED: EventCategory.DIAGNOSTIC,
    EventType.RESOURCE_EXHAUSTED: EventCategory.DIAGNOSTIC,
    EventType.QUOTA_EXCEEDED: EventCategory.DIAGNOSTIC,
    EventType.SKILL_EXECUTED: EventCategory.DIAGNOSTIC,
    EventType.SKILL_FAILED: EventCategory.DIAGNOSTIC,
    EventType.MCP_TOOL_CALLED: EventCategory.DIAGNOSTIC,
    EventType.MCP_TOOL_SUCCEEDED: EventCategory.DIAGNOSTIC,
    EventType.MCP_TOOL_FAILED: EventCategory.DIAGNOSTIC,
    EventType.MODEL_ROUTED: EventCategory.DIAGNOSTIC,
    EventType.MODEL_FALLBACK: EventCategory.DIAGNOSTIC,
    EventType.PROMPT_TEMPLATE_RENDERED: EventCategory.DIAGNOSTIC,
    EventType.TOKEN_BUDGET_EXCEEDED: EventCategory.DIAGNOSTIC,
    EventType.PERSONA_OVERRIDE_APPLIED: EventCategory.DIAGNOSTIC,
}


def category_for_event_type(event_type: EventType) -> EventCategory:
    """Return the canonical category for a Part 2 EventType (§2.3.2).

    Raises ValueError if the event type has no registered category
    (should not happen for canonical types).
    """
    try:
        return _EVENT_TYPE_CATEGORY[event_type]
    except KeyError as exc:
        raise ValueError(
            f"No category mapping for EventType {event_type.name}; "
            f"every canonical EventType MUST have a category (INV-ET-001)."
        ) from exc


__all__ = ["EventCategory", "category_for_event_type"]
