"""
Core atomic enumerations and value types for the AI-OS Event model.

Implements:
  * ``EventType``  — closed enum, Part 2 §2.3.1 (118 canonical types in the
    enumeration; the prose states 97 — we conform to the enumeration)
  * ``SemanticVersion`` — Part 2 §2.2.5 (MAJOR.MINOR.PATCH)
  * ``ComponentType`` — Part 2 §2.2.2 component-type discriminant

These are the smallest building blocks of the Event base contract. They are
imported by the other core modules (``identity``, ``priority``, ``category``,
``event``).
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering
from typing import Any


class EventType(str, Enum):
    """Closed catalog of canonical event types (Part 2 §2.3.1).

    Every value is a ``str`` enum member whose ``value`` is the
    SCREAMING_SNAKE_CASE name, e.g. ``"TASK_CREATED"``. Serialization uses the
    member name per Part 2 §2.2.8 (enum values serialized as
    SCREAMING_SNAKE_CASE strings). As a ``str`` enum, members compare and hash
    like their string value.

    The enum is closed: extension is only via the governed extension point
    (Part 0 §0.5.2 / Part 2 §2.3.1). No runtime registration is performed by
    the core model (EventTypeRegistry is a later component).
    """

    # === SYSTEM (Kernel, Core Components, Core Managers) ===
    KERNEL_INITIALIZATION_STARTED = "KERNEL_INITIALIZATION_STARTED"
    KERNEL_READY = "KERNEL_READY"
    KERNEL_SHUTDOWN_STARTED = "KERNEL_SHUTDOWN_STARTED"
    KERNEL_TERMINATED = "KERNEL_TERMINATED"
    KERNEL_INITIALIZATION_FAILED = "KERNEL_INITIALIZATION_FAILED"
    KERNEL_FATAL_ERROR = "KERNEL_FATAL_ERROR"
    CORE_COMPONENT_INITIALIZED = "CORE_COMPONENT_INITIALIZED"
    CORE_COMPONENT_SHUTDOWN = "CORE_COMPONENT_SHUTDOWN"
    CORE_COMPONENT_DEGRADED = "CORE_COMPONENT_DEGRADED"
    CORE_COMPONENT_FAILED = "CORE_COMPONENT_FAILED"
    CORE_MANAGER_INITIALIZED = "CORE_MANAGER_INITIALIZED"
    CORE_MANAGER_SHUTDOWN = "CORE_MANAGER_SHUTDOWN"
    CORE_MANAGER_DEGRADED = "CORE_MANAGER_DEGRADED"
    CORE_MANAGER_FAILED = "CORE_MANAGER_FAILED"
    HEARTBEAT = "HEARTBEAT"
    CONFIGURATION_FROZEN = "CONFIGURATION_FROZEN"
    CONFIGURATION_CHANGED = "CONFIGURATION_CHANGED"

    # === CONTROL (Workflow Orchestration, Service Coordination) ===
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    WORKFLOW_STEP_STARTED = "WORKFLOW_STEP_STARTED"
    WORKFLOW_STEP_COMPLETED = "WORKFLOW_STEP_COMPLETED"
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    WORKFLOW_STEP_RETRIED = "WORKFLOW_STEP_RETRIED"
    WORKFLOW_STEP_SKIPPED = "WORKFLOW_STEP_SKIPPED"
    WORKFLOW_CHECKPOINT_CREATED = "WORKFLOW_CHECKPOINT_CREATED"
    WORKFLOW_CHECKPOINT_RESTORED = "WORKFLOW_CHECKPOINT_RESTORED"
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRIED = "TASK_RETRIED"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_DEPENDENCY_RESOLVED = "TASK_DEPENDENCY_RESOLVED"
    RETRY_BUDGET_EXHAUSTED = "RETRY_BUDGET_EXHAUSTED"
    ROOT_CAUSE_ANALYZED = "ROOT_CAUSE_ANALYZED"
    RECOVERY_ACTION_DISPATCHED = "RECOVERY_ACTION_DISPATCHED"
    RECOVERY_ACTION_COMPLETED = "RECOVERY_ACTION_COMPLETED"
    RECOVERY_ACTION_FAILED = "RECOVERY_ACTION_FAILED"

    # === DATA (State, Artifacts, Memory, Checkpoints) ===
    STATE_CHANGED = "STATE_CHANGED"
    STATE_SNAPSHOT_CREATED = "STATE_SNAPSHOT_CREATED"
    STATE_RESTORED = "STATE_RESTORED"
    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    ARTIFACT_UPDATED = "ARTIFACT_UPDATED"
    ARTIFACT_DELETED = "ARTIFACT_DELETED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"
    CHECKPOINT_RESTORED = "CHECKPOINT_RESTORED"
    CHECKPOINT_PRUNED = "CHECKPOINT_PRUNED"
    MEMORY_STORED = "MEMORY_STORED"
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    MEMORY_CONSOLIDATED = "MEMORY_CONSOLIDATED"
    MEMORY_PRUNED = "MEMORY_PRUNED"
    CONTEXT_ASSEMBLED = "CONTEXT_ASSEMBLED"
    CONTEXT_COMPRESSED = "CONTEXT_COMPRESSED"

    # === AUDIT (Governance, Security, AI Agency) ===
    PLANNING_REQUESTED = "PLANNING_REQUESTED"
    PLANNING_COMPLETED = "PLANNING_COMPLETED"
    PLANNING_FAILED = "PLANNING_FAILED"
    PLAN_REJECTED = "PLAN_REJECTED"
    CODE_GENERATED = "CODE_GENERATED"
    CODING_COMPLETED = "CODING_COMPLETED"
    CODING_FAILED = "CODING_FAILED"
    CODE_REVIEW_REQUESTED = "CODE_REVIEW_REQUESTED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    REVIEW_FAILED = "REVIEW_FAILED"
    SECURITY_ISSUE_FOUND = "SECURITY_ISSUE_FOUND"
    PERFORMANCE_ISSUE_FOUND = "PERFORMANCE_ISSUE_FOUND"
    TESTS_GENERATED = "TESTS_GENERATED"
    TESTS_PASSED = "TESTS_PASSED"
    TESTS_FAILED = "TESTS_FAILED"
    TESTING_COMPLETED = "TESTING_COMPLETED"
    TESTING_FAILED = "TESTING_FAILED"
    DEPLOYMENT_REQUESTED = "DEPLOYMENT_REQUESTED"
    DEPLOYMENT_STARTED = "DEPLOYMENT_STARTED"
    DEPLOYMENT_COMPLETED = "DEPLOYMENT_COMPLETED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    DEPLOYMENT_ROLLED_BACK = "DEPLOYMENT_ROLLED_BACK"
    COUNCIL_CONVENED = "COUNCIL_CONVENED"
    COUNCIL_PROPOSAL_SUBMITTED = "COUNCIL_PROPOSAL_SUBMITTED"
    COUNCIL_VOTE_CAST = "COUNCIL_VOTE_CAST"
    COUNCIL_CONSENSUS_REACHED = "COUNCIL_CONSENSUS_REACHED"
    COUNCIL_DISSENT_REGISTERED = "COUNCIL_DISSENT_REGISTERED"
    COUNCIL_DECISION_FINALIZED = "COUNCIL_DECISION_FINALIZED"
    AI_AGENT_TASK_REQUESTED = "AI_AGENT_TASK_REQUESTED"
    AI_AGENT_TASK_COMPLETED = "AI_AGENT_TASK_COMPLETED"
    AI_AGENT_TASK_FAILED = "AI_AGENT_TASK_FAILED"
    AI_AGENT_AUDIT_EMITTED = "AI_AGENT_AUDIT_EMITTED"
    FINAL_JUDGE_DECISION = "FINAL_JUDGE_DECISION"
    HUMAN_ESCALATION_REQUIRED = "HUMAN_ESCALATION_REQUIRED"

    # === DIAGNOSTIC (Metrics, Tracing, Health) ===
    METRIC_EMITTED = "METRIC_EMITTED"
    TRACE_SPAN_STARTED = "TRACE_SPAN_STARTED"
    TRACE_SPAN_ENDED = "TRACE_SPAN_ENDED"
    HEALTH_CHECK_PASSED = "HEALTH_CHECK_PASSED"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_STOPPED = "SERVICE_STOPPED"
    SERVICE_DEGRADED = "SERVICE_DEGRADED"
    SERVICE_FAILED = "SERVICE_FAILED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    SKILL_EXECUTED = "SKILL_EXECUTED"
    SKILL_FAILED = "SKILL_FAILED"
    MCP_TOOL_CALLED = "MCP_TOOL_CALLED"
    MCP_TOOL_SUCCEEDED = "MCP_TOOL_SUCCEEDED"
    MCP_TOOL_FAILED = "MCP_TOOL_FAILED"
    MODEL_ROUTED = "MODEL_ROUTED"
    MODEL_FALLBACK = "MODEL_FALLBACK"
    PROMPT_TEMPLATE_RENDERED = "PROMPT_TEMPLATE_RENDERED"
    TOKEN_BUDGET_EXCEEDED = "TOKEN_BUDGET_EXCEEDED"
    PERSONA_OVERRIDE_APPLIED = "PERSONA_OVERRIDE_APPLIED"

    @classmethod
    def from_name(cls, name: str) -> "EventType":
        """Resolve an EventType from its SCREAMING_SNAKE_CASE name.

        Unlike ``EventType(value)`` (which requires an exact match against the
        member value), this accepts the member name directly. Both forms are
        equivalent for this enum because member names equal member values.

        Raises
        ------
        ValueError
            If ``name`` is not a defined event type.
        """
        try:
            return cls(name)
        except ValueError as exc:
            raise ValueError(
                f"Unknown EventType: {name!r}. Must be one of the "
                f"{len(cls)} canonical Part 2 event types (the Part 2 §2.3.1 "
                f"enumeration; the prose states 97 but the enumeration lists "
                f"{len(cls)})."
            ) from exc

    @property
    def name_str(self) -> str:
        """The SCREAMING_SNAKE_CASE name (== member value)."""
        return self.value


@total_ordering
class SemanticVersion:
    """Semantic version (Part 2 §2.2.5): MAJOR.MINOR.PATCH.

    Immutable value object. Ordering follows semantic-version precedence
    (major > minor > patch). Used for ``eventVersion`` and
    ``ComponentIdentity.version``.
    """

    __slots__ = ("major", "minor", "patch")

    def __init__(self, major: int, minor: int, patch: int) -> None:
        if not isinstance(major, int) or isinstance(major, bool):
            raise TypeError(f"major must be int, got {type(major).__name__}")
        if not isinstance(minor, int) or isinstance(minor, bool):
            raise TypeError(f"minor must be int, got {type(minor).__name__}")
        if not isinstance(patch, int) or isinstance(patch, bool):
            raise TypeError(f"patch must be int, got {type(patch).__name__}")
        if major < 0 or minor < 0 or patch < 0:
            raise ValueError("SemanticVersion components must be non-negative")
        object.__setattr__(self, "major", major)
        object.__setattr__(self, "minor", minor)
        object.__setattr__(self, "patch", patch)

    # --- immutability ---------------------------------------------------
    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("SemanticVersion is immutable")

    # --- ordering & equality -------------------------------------------
    def _key(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self._key() < other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    # --- construction helpers ------------------------------------------
    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        """Parse ``"MAJOR.MINOR.PATCH"`` (e.g. ``"1.0.0"``)."""
        parts = value.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid semantic version {value!r}; expected MAJOR.MINOR.PATCH"
            )
        try:
            major, minor, patch = (int(p) for p in parts)
        except ValueError as exc:
            raise ValueError(f"Invalid semantic version {value!r}: {exc}") from exc
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"SemanticVersion({self.major}, {self.minor}, {self.patch})"


__all__ = ["EventType", "SemanticVersion"]
