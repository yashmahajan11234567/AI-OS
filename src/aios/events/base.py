"""
Base Event Types for AI-OS Hermes Kernel.

All events in the system inherit from the Event base class.
Event types are defined as an enum for type safety and serialization.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """All event types in the AI-OS system."""

    # Task Events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRY_REQUESTED = "task.retry_requested"

    # Workflow Events
    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_STARTED = "workflow.step_started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_STEP_FAILED = "workflow.step_failed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"

    # Planning Events
    PLANNING_REQUESTED = "planning.requested"
    PLANNING_STARTED = "planning.started"
    PLANNING_COMPLETED = "planning.completed"
    PLANNING_FAILED = "planning.failed"
    PLAN_APPROVED = "plan.approved"
    PLAN_REJECTED = "plan.rejected"

    # Coding Events
    CODING_STARTED = "coding.started"
    CODING_COMPLETED = "coding.completed"
    CODING_FAILED = "coding.failed"
    CODE_GENERATED = "code.generated"
    CODE_REVIEW_REQUESTED = "code_review.requested"

    # Review Events
    REVIEW_STARTED = "review.started"
    REVIEW_COMPLETED = "review.completed"
    REVIEW_FAILED = "review.failed"
    REVIEW_APPROVED = "review.approved"
    REVIEW_REJECTED = "review.rejected"
    SECURITY_ISSUE_FOUND = "security.issue_found"
    PERFORMANCE_ISSUE_FOUND = "performance.issue_found"
    ARCHITECTURE_ISSUE_FOUND = "architecture.issue_found"

    # Testing Events
    TESTING_STARTED = "testing.started"
    TESTING_COMPLETED = "testing.completed"
    TESTING_FAILED = "testing.failed"
    TESTS_PASSED = "tests.passed"
    TESTS_FAILED = "tests.failed"
    TEST_GENERATED = "test.generated"

    # Deployment Events
    DEPLOYMENT_REQUESTED = "deployment.requested"
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    DEPLOYMENT_ROLLED_BACK = "deployment.rolled_back"

    # Operations Events
    PRODUCTION_INCIDENT = "production.incident"
    METRICS_ALERT = "metrics.alert"
    LOG_ANOMALY_DETECTED = "log.anomaly_detected"
    USER_FEEDBACK_RECEIVED = "user.feedback_received"

    # Memory Events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # Skill Events
    SKILL_LOADED = "skill.loaded"
    SKILL_UNLOADED = "skill.unloaded"
    SKILL_EXECUTED = "skill.executed"
    SKILL_FAILED = "skill.failed"

    # MCP Events
    MCP_SERVER_CONNECTED = "mcp.server_connected"
    MCP_SERVER_DISCONNECTED = "mcp.server_disconnected"
    MCP_TOOL_CALLED = "mcp.tool_called"
    MCP_TOOL_RESULT = "mcp.tool_result"

    # Council Events
    COUNCIL_CONVENED = "council.convened"
    COUNCIL_DELIBERATED = "council.deliberated"
    COUNCIL_DECIDED = "council.decided"
    COUNCIL_DISSENTED = "council.dissented"

    # AI Agency Events
    SECURITY_AUDIT_REQUESTED = "security.audit_requested"
    SECURITY_AUDIT_COMPLETED = "security.audit_completed"
    PERFORMANCE_AUDIT_REQUESTED = "performance.audit_requested"
    PERFORMANCE_AUDIT_COMPLETED = "performance.audit_completed"
    CHAOS_EXPERIMENT_REQUESTED = "chaos.experiment_requested"
    CHAOS_EXPERIMENT_COMPLETED = "chaos.experiment_completed"
    ACCESSIBILITY_AUDIT_REQUESTED = "accessibility.audit_requested"
    ACCESSIBILITY_AUDIT_COMPLETED = "accessibility.audit_completed"
    DOCUMENTATION_AUDIT_REQUESTED = "documentation.audit_requested"
    DOCUMENTATION_AUDIT_COMPLETED = "documentation.audit_completed"
    CONCURRENCY_AUDIT_REQUESTED = "concurrency.audit_requested"
    CONCURRENCY_AUDIT_COMPLETED = "concurrency.audit_completed"
    BUG_HUNT_REQUESTED = "bug_hunt.requested"
    BUG_HUNT_COMPLETED = "bug_hunt.completed"
    ARCHITECTURE_VALIDATION_REQUESTED = "architecture.validation_requested"
    ARCHITECTURE_VALIDATION_COMPLETED = "architecture.validation_completed"
    FINAL_JUDGMENT_REQUESTED = "final_judgment.requested"
    FINAL_JUDGMENT_COMPLETED = "final_judgment.completed"

    # Checkpoint Events
    CHECKPOINT_CREATED = "checkpoint.created"
    CHECKPOINT_RESTORED = "checkpoint.restored"
    CHECKPOINT_DELETED = "checkpoint.deleted"

    # Retry Events
    RETRY_BUDGET_EXHAUSTED = "retry.budget_exhausted"
    RETRY_SCHEDULED = "retry.scheduled"
    RETRY_EXECUTED = "retry.executed"

    # Root Cause Events
    ROOT_CAUSE_ANALYZED = "root_cause.analyzed"
    ROOT_CAUSE_RESOLVED = "root_cause.resolved"
    FAILURE_CLASSIFIED = "failure.classified"

    # Learning Events
    LEARNING_CAPTURED = "learning.captured"
    PATTERN_EXTRACTED = "pattern.extracted"
    KNOWLEDGE_UPDATED = "knowledge.updated"

    # State Events
    STATE_TRANSITIONED = "state.transitioned"
    STATE_CHECKPOINTED = "state.checkpointed"
    STATE_RESTORED = "state.restored"

    # System Events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_HEALTHY = "service.healthy"
    SERVICE_UNHEALTHY = "service.unhealthy"
    KERNEL_STARTED = "kernel.started"
    KERNEL_STOPPED = "kernel.stopped"
    KERNEL_ERROR = "kernel.error"


@dataclass
class Event:
    """
    Base event class for all AI-OS events.

    Events are immutable once created and carry all context needed
    for services to process them independently.
    """

    event_type: Any = field(default=None)
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str = "unknown"
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate event after creation."""
        if self.event_type is None:
            # Try to get from class attribute
            cls_event_type = getattr(self.__class__, 'event_type', None)
            if cls_event_type is not None:
                self.event_type = cls_event_type
            else:
                raise ValueError("event_type must be provided or defined as class attribute")

        # If event_type is a string, try to convert to EventType enum; if conversion fails, keep as string
        if isinstance(self.event_type, str):
            try:
                self.event_type = EventType(self.event_type)
            except ValueError:
                # Not a known enum value, keep as string
                pass

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": str(self.event_type),
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "timestamp": self.timestamp.isoformat(),
            "source_service": self.source_service,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Create event from dictionary."""
        # Try to convert string to EventType if possible, otherwise keep as string
        et_str = data["event_type"]
        try:
            event_type = EventType(et_str)
        except ValueError:
            # Not a known enum value, keep as string
            event_type = et_str
        return cls(
            event_type=event_type,
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            causation_id=data.get("causation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            source_service=data.get("source_service", "unknown"),
            tags=data.get("tags", {}),
        )

    def with_causation(self, causation_id: str) -> Event:
        """Create new event with causation ID set."""
        return Event(
            event_type=self.event_type,
            payload=self.payload.copy(),
            correlation_id=self.correlation_id,
            causation_id=causation_id,
            timestamp=self.timestamp,
            source_service=self.source_service,
            tags=self.tags.copy(),
        )


def create_event(
    event_type: Any,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    source_service: str = "unknown",
    tags: dict[str, str] | None = None,
) -> Event:
    """Factory function to create events."""
    return Event(
        event_type=event_type,
        payload=payload or {},
        correlation_id=correlation_id or str(uuid.uuid4()),
        causation_id=causation_id,
        source_service=source_service,
        tags=tags or {},
    )

__all__ = [
    "EventType",
    "Event",
    "create_event",
]
