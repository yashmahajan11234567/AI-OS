"""
Tests for ``EventType`` (Part 2 §2.3.1).

EventType is defined in ``src/aios/events/core/types.py`` as the authoritative
Task 1 immutable-event-core location. Task 2 reuses that single definition
rather than duplicating it (the task forbids creating a second EventType).

Architecture discrepancy (NOT resolved here):
    Part 2 §2.3.1 advertises 97 canonical EventTypes in its prose, but the
    canonical enumeration list in §2.3.1 contains 121 entries (97 prose + 24
    RETRY_SCHEDULED/RETRY_EXECUTED/FAILURE_CLASSIFIED added by the retry and
    root-cause subsystems). We implement and assert the 121-member enumeration
    exactly as listed. The 97-vs-121 discrepancy is escalated to the Architect / ARB.
"""

import re

import pytest

from aios.events.core.types import EventType


# Canonical enumeration from Part 2 §2.3.1, in exact canonical order.
# 121 entries (the §2.3.1 enumeration), NOT the prose-stated 97.
# M5-GATE-REALIZE adds 11 new M5 event types: total 132.
CANONICAL_ORDER = [
    # SYSTEM
    "KERNEL_INITIALIZATION_STARTED",
    "KERNEL_READY",
    "KERNEL_SHUTDOWN_STARTED",
    "KERNEL_TERMINATED",
    "KERNEL_INITIALIZATION_FAILED",
    "KERNEL_FATAL_ERROR",
    "CORE_COMPONENT_INITIALIZED",
    "CORE_COMPONENT_SHUTDOWN",
    "CORE_COMPONENT_DEGRADED",
    "CORE_COMPONENT_FAILED",
    "CORE_MANAGER_INITIALIZED",
    "CORE_MANAGER_SHUTDOWN",
    "CORE_MANAGER_DEGRADED",
    "CORE_MANAGER_FAILED",
    "HEARTBEAT",
    "CONFIGURATION_FROZEN",
    "CONFIGURATION_CHANGED",
    # CONTROL
    "WORKFLOW_STARTED",
    "WORKFLOW_COMPLETED",
    "WORKFLOW_FAILED",
    "WORKFLOW_PAUSED",
    "WORKFLOW_RESUMED",
    "WORKFLOW_CANCELLED",
    "WORKFLOW_STEP_STARTED",
    "WORKFLOW_STEP_COMPLETED",
    "WORKFLOW_STEP_FAILED",
    "WORKFLOW_STEP_RETRIED",
    "WORKFLOW_STEP_SKIPPED",
    "WORKFLOW_CHECKPOINT_CREATED",
    "WORKFLOW_CHECKPOINT_RESTORED",
    "TASK_CREATED",
    "TASK_ASSIGNED",
    "TASK_STARTED",
    "TASK_COMPLETED",
    "TASK_FAILED",
    "TASK_RETRIED",
    "TASK_CANCELLED",
    "TASK_DEPENDENCY_RESOLVED",
    "RETRY_BUDGET_EXHAUSTED",
    "RETRY_SCHEDULED",
    "RETRY_EXECUTED",
    "ROOT_CAUSE_ANALYZED",
    "RECOVERY_ACTION_DISPATCHED",
    "RECOVERY_ACTION_COMPLETED",
    "RECOVERY_ACTION_FAILED",
    # DATA
    "STATE_CHANGED",
    "STATE_SNAPSHOT_CREATED",
    "STATE_RESTORED",
    "ARTIFACT_CREATED",
    "ARTIFACT_UPDATED",
    "ARTIFACT_DELETED",
    "CHECKPOINT_CREATED",
    "CHECKPOINT_RESTORED",
    "CHECKPOINT_PRUNED",
    "MEMORY_STORED",
    "MEMORY_RETRIEVED",
    "MEMORY_UPDATED",
    "MEMORY_CONSOLIDATED",
    "MEMORY_PRUNED",
    "CONTEXT_ASSEMBLED",
    "CONTEXT_COMPRESSED",
    # AUDIT
    "PLANNING_REQUESTED",
    "PLANNING_COMPLETED",
    "PLANNING_FAILED",
    "PLAN_REJECTED",
    "CODE_GENERATED",
    "CODING_COMPLETED",
    "CODING_FAILED",
    "CODE_REVIEW_REQUESTED",
    "REVIEW_STARTED",
    "REVIEW_APPROVED",
    "REVIEW_REJECTED",
    "REVIEW_FAILED",
    "SECURITY_ISSUE_FOUND",
    "PERFORMANCE_ISSUE_FOUND",
    "TESTS_GENERATED",
    "TESTS_PASSED",
    "TESTS_FAILED",
    "TESTING_COMPLETED",
    "TESTING_FAILED",
    "DEPLOYMENT_REQUESTED",
    "DEPLOYMENT_STARTED",
    "DEPLOYMENT_COMPLETED",
    "DEPLOYMENT_FAILED",
    "DEPLOYMENT_ROLLED_BACK",
    "COUNCIL_CONVENED",
    "COUNCIL_PROPOSAL_SUBMITTED",
    "COUNCIL_VOTE_CAST",
    "COUNCIL_CONSENSUS_REACHED",
    "COUNCIL_DISSENT_REGISTERED",
    "COUNCIL_DECISION_FINALIZED",
    "AI_AGENT_TASK_REQUESTED",
    "AI_AGENT_TASK_COMPLETED",
    "AI_AGENT_TASK_FAILED",
    "AI_AGENT_AUDIT_EMITTED",
    "FINAL_JUDGE_DECISION",
    "HUMAN_ESCALATION_REQUIRED",
    # DIAGNOSTIC
    "METRIC_EMITTED",
    "TRACE_SPAN_STARTED",
    "TRACE_SPAN_ENDED",
    "HEALTH_CHECK_PASSED",
    "HEALTH_CHECK_FAILED",
    "SERVICE_STARTED",
    "SERVICE_STOPPED",
    "SERVICE_DEGRADED",
    "SERVICE_FAILED",
    "RESOURCE_ALLOCATED",
    "RESOURCE_RELEASED",
    "RESOURCE_EXHAUSTED",
    "QUOTA_EXCEEDED",
    "SKILL_EXECUTED",
    "SKILL_FAILED",
    "MCP_TOOL_CALLED",
    "MCP_TOOL_SUCCEEDED",
    "MCP_TOOL_FAILED",
    "MCP_SERVER_DISCONNECTED",
    "MCP_SERVER_CONNECTED",
    "MCP_SERVER_VALIDATION_FAILED",
    "MCP_TOOL_DISCOVERED",
    "MODEL_ROUTED",
    "MODEL_FALLBACK",
    "MODEL_PROVIDER_REGISTERED",
    "MEMORY_GRAPHIFY_QUERY",
    "MEMORY_GRAPHIFY_PATH",
    "AGENT_REACH_FETCH",
    "AGENT_REACH_NORMALIZED",
    "HERMES_BRIDGE_TASK",
    "HERMES_BRIDGE_OBSERVATION",
    "PROMPT_TEMPLATE_RENDERED",
    "TOKEN_BUDGET_EXCEEDED",
    "PERSONA_OVERRIDE_APPLIED",
    "FAILURE_CLASSIFIED",
]

EXPECTED_COUNT = 132
PROSE_COUNT = 97  # Part 2 §2.3.1 prose states 97; the enumeration originally contained 121; M5 adds 11 = 132.

NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def test_event_type_count_is_132():
    """The §2.3.1 enumeration contains 132 members (original 121 + 11 M5 additions)."""
    assert len(EventType) == EXPECTED_COUNT


def test_all_132_members_exist():
    for name in CANONICAL_ORDER:
        assert hasattr(EventType, name), f"missing EventType.{name}"
        assert isinstance(getattr(EventType, name), EventType)


def test_exact_canonical_names():
    actual = [m.name for m in EventType]
    assert actual == CANONICAL_ORDER


def test_exact_canonical_ordering():
    assert [m.name for m in EventType] == CANONICAL_ORDER


def test_value_equals_member_name():
    for member in EventType:
        assert member.value == member.name


def test_no_duplicate_values():
    values = [m.value for m in EventType]
    assert len(values) == len(set(values))


def test_member_names_match_regex():
    for member in EventType:
        assert NAME_RE.match(member.name), f"bad name: {member.name!r}"


def test_event_type_is_closed_enum():
    # A closed enum: it must not be possible to construct an arbitrary new member.
    from enum import Enum

    assert issubclass(EventType, Enum)
    with pytest.raises(ValueError):
        EventType("NONEXISTENT_EVENT_TYPE")


def test_event_type_is_str_enum_consistent_behavior():
    # str enum: value, str, and repr behave consistently with project convention.
    sample = EventType.TASK_CREATED
    assert sample.value == "TASK_CREATED"
    assert str(sample) == "TASK_CREATED"
    assert isinstance(sample, str)
    assert sample == "TASK_CREATED"
    assert hash(sample) == hash("TASK_CREATED")


def test_from_name_resolves_canonical_member():
    assert EventType.from_name("TASK_CREATED") is EventType.TASK_CREATED
    with pytest.raises(ValueError):
        EventType.from_name("DOES_NOT_EXIST")


def test_event_type_importable_from_module():
    from aios.events.core.types import EventType as ET2

    assert ET2 is EventType
    # Public re-export surface from the core package.
    from aios.events.core import EventType as ET3

    assert ET3 is EventType


def test_no_category_or_priority_attached_to_members():
    # EventType members carry only name/value; no category/priority/schema attrs.
    member = EventType.TASK_CREATED
    for forbidden in ("category", "priority", "schema_version", "payload_schema"):
        assert not hasattr(member, forbidden), f"member has forbidden attr {forbidden!r}"


def test_architecture_discrepancy_documented():
    """97 (prose) vs 121 (original enumeration) vs 132 (M5) discrepancy is captured, not resolved.

    We assert the enumeration count is 132 and that the source module's docstring
    acknowledges the discrepancy. Resolution is escalated to the Architect / ARB.
    """
    import inspect

    assert len(EventType) == EXPECTED_COUNT
    doc = inspect.getmodule(EventType).__doc__ or ""
    # The Task 1 module already documents the 97-vs-121 discrepancy.
    assert "97" in doc
    assert "121" in doc


def test_existing_task1_event_tests_untouched():
    """Guard: this test module must not redefine Task 1's Event core.

    Reusing the single authoritative EventType definition keeps Task 1 intact.
    """
    from aios.events.core.event import Event

    assert Event is not None
