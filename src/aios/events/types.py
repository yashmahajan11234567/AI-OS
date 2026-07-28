"""
Concrete Event Type Definitions for AI-OS.

Each event type is a specific dataclass with typed payload fields.
This provides type safety and IDE support for event-driven programming.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event, EventType


# =============================================================================
# Core Kernel Events
# =============================================================================


@dataclass(kw_only=True)
class KernelStarted(Event):
    """Kernel has started successfully."""

    event_type: EventType = EventType.KERNEL_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {"version": "0.1.0"})


@dataclass(kw_only=True)
class KernelStopped(Event):
    """Kernel has stopped."""

    event_type: EventType = EventType.KERNEL_STOPPED
    payload: dict[str, Any] = field(default_factory=lambda: {"reason": "shutdown"})


@dataclass(kw_only=True)
class KernelError(Event):
    """Kernel encountered an error."""

    event_type: EventType = EventType.KERNEL_ERROR
    payload: dict[str, Any] = field(default_factory=lambda: {"error": "", "fatal": False})


# =============================================================================
# Task/Workflow Events
# =============================================================================


@dataclass(kw_only=True)
class TaskCreated(Event):
    """A new task has been created."""

    event_type: EventType = EventType.TASK_CREATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "task_type": "",
        "description": "",
        "priority": "normal",
        "assigned_service": "",
    })


@dataclass(kw_only=True)
class TaskStarted(Event):
    """A task has started execution."""

    event_type: EventType = EventType.TASK_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
    })


@dataclass(kw_only=True)
class TaskCompleted(Event):
    """A task has completed successfully."""

    event_type: EventType = EventType.TASK_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "result": {},
        "duration_ms": 0,
    })


@dataclass(kw_only=True)
class TaskFailed(Event):
    """A task has failed."""

    event_type: EventType = EventType.TASK_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "error": "",
        "error_type": "",
        "retryable": True,
        "retry_count": 0,
    })


@dataclass(kw_only=True)
class TaskRetryRequested(Event):
    """A retry has been requested for a failed task."""

    event_type: EventType = EventType.TASK_RETRY_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "retry_count": 0,
        "delay_ms": 0,
    })


@dataclass(kw_only=True)
class TaskCancelled(Event):
    """A task has been cancelled."""

    event_type: EventType = EventType.TASK_CANCELLED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "reason": "",
    })


@dataclass(kw_only=True)
class WorkflowCreated(Event):
    """A new workflow has been created."""

    event_type: EventType = EventType.WORKFLOW_CREATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "name": "",
        "initial_state": "",
        "tasks": [],
    })


@dataclass(kw_only=True)
class WorkflowStarted(Event):
    """A workflow has started execution."""

    event_type: EventType = EventType.WORKFLOW_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "initial_task_id": "",
    })


@dataclass(kw_only=True)
class WorkflowCompleted(Event):
    """A workflow has completed successfully."""

    event_type: EventType = EventType.WORKFLOW_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "final_state": "",
        "duration_ms": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
    })


@dataclass(kw_only=True)
class WorkflowFailed(Event):
    """A workflow has failed."""

    event_type: EventType = EventType.WORKFLOW_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "error": "",
        "failed_task_id": "",
        "rollback_initiated": False,
    })


@dataclass(kw_only=True)
class WorkflowPaused(Event):
    """A workflow has been paused."""

    event_type: EventType = EventType.WORKFLOW_PAUSED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "reason": "",
        "current_state": "",
    })


@dataclass(kw_only=True)
class WorkflowResumed(Event):
    """A workflow has been resumed."""

    event_type: EventType = EventType.WORKFLOW_RESUMED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "checkpoint_id": "",
    })


# =============================================================================
# Planning Events
# =============================================================================


@dataclass(kw_only=True)
class PlanningRequested(Event):
    """Planning has been requested."""

    event_type: EventType = EventType.PLANNING_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "planning_id": "",
        "objective": "",
        "constraints": [],
        "context": {},
    })


@dataclass(kw_only=True)
class PlanningCompleted(Event):
    """Planning has completed successfully."""

    event_type: EventType = EventType.PLANNING_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "planning_id": "",
        "plan": {},
        "tasks": [],
        "estimated_duration": 0,
    })


@dataclass(kw_only=True)
class PlanningFailed(Event):
    """Planning has failed."""

    event_type: EventType = EventType.PLANNING_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "planning_id": "",
        "error": "",
        "retryable": True,
    })


@dataclass(kw_only=True)
class PlanApproved(Event):
    """A plan has been approved."""

    event_type: EventType = EventType.PLAN_APPROVED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "plan_id": "",
        "approved_by": "human",
        "modifications": [],
    })


@dataclass(kw_only=True)
class PlanRejected(Event):
    """A plan has been rejected."""

    event_type: EventType = EventType.PLAN_REJECTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "plan_id": "",
        "reason": "",
        "revision_requested": True,
    })


# =============================================================================
# Coding Events
# =============================================================================


@dataclass(kw_only=True)
class CodingStarted(Event):
    """Coding task has started."""

    event_type: EventType = EventType.CODING_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "coding_id": "",
        "task_id": "",
        "language": "python",
        "specification": {},
    })


@dataclass(kw_only=True)
class CodingCompleted(Event):
    """Coding task has completed successfully."""

    event_type: EventType = EventType.CODING_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "coding_id": "",
        "files_created": [],
        "files_modified": [],
        "summary": "",
    })


@dataclass(kw_only=True)
class CodingFailed(Event):
    """Coding task has failed."""

    event_type: EventType = EventType.CODING_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "coding_id": "",
        "error": "",
        "partial_results": {},
    })


@dataclass(kw_only=True)
class CodeGenerated(Event):
    """Code has been generated."""

    event_type: EventType = EventType.CODE_GENERATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "generation_id": "",
        "file_path": "",
        "content": "",
        "language": "",
        "metadata": {},
    })


@dataclass(kw_only=True)
class CodeReviewRequested(Event):
    """Code review has been requested."""

    event_type: EventType = EventType.CODE_REVIEW_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "files": [],
        "review_type": "full",
    })


# =============================================================================
# Review Events
# =============================================================================


@dataclass(kw_only=True)
class ReviewStarted(Event):
    """Code review has started."""

    event_type: EventType = EventType.REVIEW_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "files": [],
        "reviewers": [],
    })


@dataclass(kw_only=True)
class ReviewCompleted(Event):
    """Code review has completed."""

    event_type: EventType = EventType.REVIEW_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "approved": True,
        "comments": [],
        "issues_found": 0,
    })


@dataclass(kw_only=True)
class ReviewFailed(Event):
    """Code review has failed."""

    event_type: EventType = EventType.REVIEW_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "error": "",
    })


@dataclass(kw_only=True)
class ReviewApproved(Event):
    """Code review approved."""

    event_type: EventType = EventType.REVIEW_APPROVED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "approver": "",
    })


@dataclass(kw_only=True)
class ReviewRejected(Event):
    """Code review rejected."""

    event_type: EventType = EventType.REVIEW_REJECTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "review_id": "",
        "reason": "",
        "required_changes": [],
    })


# =============================================================================
# Testing Events
# =============================================================================


@dataclass(kw_only=True)
class TestingStarted(Event):
    """Testing has started."""

    event_type: EventType = EventType.TESTING_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "test_run_id": "",
        "test_types": [],
        "target": "",
    })


@dataclass(kw_only=True)
class TestingCompleted(Event):
    """Testing has completed."""

    event_type: EventType = EventType.TESTING_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "test_run_id": "",
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "coverage": 0.0,
    })


@dataclass(kw_only=True)
class TestingFailed(Event):
    """Testing has failed."""

    event_type: EventType = EventType.TESTING_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "test_run_id": "",
        "error": "",
    })


@dataclass(kw_only=True)
class TestsPassed(Event):
    """All tests passed."""

    event_type: EventType = EventType.TESTS_PASSED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "test_run_id": "",
    })


@dataclass(kw_only=True)
class TestsFailed(Event):
    """Some tests failed."""

    event_type: EventType = EventType.TESTS_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "test_run_id": "",
        "failed_tests": [],
    })


@dataclass(kw_only=True)
class TestGenerated(Event):
    """Tests were generated for an artifact."""

    event_type: EventType = EventType.TEST_GENERATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "artifact_id": "",
        "tests": [],
    })


@dataclass(kw_only=True)
class SecurityIssueFound(Event):
    """Security issue found during testing/review."""

    event_type: EventType = EventType.SECURITY_ISSUE_FOUND
    payload: dict[str, Any] = field(default_factory=lambda: {
        "issue_id": "",
        "severity": "high",
        "description": "",
        "file": "",
        "line": 0,
        "cve": None,
    })


@dataclass(kw_only=True)
class PerformanceIssueFound(Event):
    """Performance issue found."""

    event_type: EventType = EventType.PERFORMANCE_ISSUE_FOUND
    payload: dict[str, Any] = field(default_factory=lambda: {
        "issue_id": "",
        "metric": "",
        "value": 0.0,
        "threshold": 0.0,
        "description": "",
    })


# =============================================================================
# Deployment Events
# =============================================================================


@dataclass(kw_only=True)
class DeploymentRequested(Event):
    """Deployment has been requested."""

    event_type: EventType = EventType.DEPLOYMENT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "deployment_id": "",
        "environment": "staging",
        "version": "",
        "artifacts": [],
    })


@dataclass(kw_only=True)
class DeploymentStarted(Event):
    """Deployment has started."""

    event_type: EventType = EventType.DEPLOYMENT_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "deployment_id": "",
        "stage": "",
    })


@dataclass(kw_only=True)
class DeploymentCompleted(Event):
    """Deployment has completed successfully."""

    event_type: EventType = EventType.DEPLOYMENT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "deployment_id": "",
        "environment": "",
        "url": "",
        "health_check_passed": True,
    })


@dataclass(kw_only=True)
class DeploymentFailed(Event):
    """Deployment has failed."""

    event_type: EventType = EventType.DEPLOYMENT_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "deployment_id": "",
        "stage": "",
        "error": "",
        "rollback_initiated": False,
    })


@dataclass(kw_only=True)
class DeploymentRolledBack(Event):
    """Deployment has been rolled back."""

    event_type: EventType = EventType.DEPLOYMENT_ROLLED_BACK
    payload: dict[str, Any] = field(default_factory=lambda: {
        "deployment_id": "",
        "reason": "",
        "previous_version": "",
    })


# =============================================================================
# Operations Events
# =============================================================================


@dataclass(kw_only=True)
class ProductionIncident(Event):
    """Production incident detected."""

    event_type: EventType = EventType.PRODUCTION_INCIDENT
    payload: dict[str, Any] = field(default_factory=lambda: {
        "incident_id": "",
        "severity": "critical",
        "title": "",
        "description": "",
        "affected_services": [],
        "detected_by": "monitoring",
    })


@dataclass(kw_only=True)
class MetricsAlert(Event):
    """Metrics alert triggered."""

    event_type: EventType = EventType.METRICS_ALERT
    payload: dict[str, Any] = field(default_factory=lambda: {
        "alert_id": "",
        "metric": "",
        "value": 0.0,
        "threshold": 0.0,
        "severity": "warning",
    })


@dataclass(kw_only=True)
class LogAnomalyDetected(Event):
    """Log anomaly detected."""

    event_type: EventType = EventType.LOG_ANOMALY_DETECTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "anomaly_id": "",
        "pattern": "",
        "count": 0,
        "time_window": "",
    })


@dataclass(kw_only=True)
class UserFeedbackReceived(Event):
    """User feedback received."""

    event_type: EventType = EventType.USER_FEEDBACK_RECEIVED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "feedback_id": "",
        "type": "bug",
        "description": "",
        "severity": "medium",
        "user_id": "",
    })


# =============================================================================
# Memory Events
# =============================================================================


@dataclass(kw_only=True)
class MemoryStored(Event):
    """Memory has been stored."""

    event_type: EventType = EventType.MEMORY_STORED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "memory_id": "",
        "memory_type": "working",
        "key": "",
        "tags": [],
    })


@dataclass(kw_only=True)
class MemoryRetrieved(Event):
    """Memory has been retrieved."""

    event_type: EventType = EventType.MEMORY_RETRIEVED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "memory_id": "",
        "memory_type": "working",
        "key": "",
        "found": True,
    })


@dataclass(kw_only=True)
class MemoryUpdated(Event):
    """Memory has been updated."""

    event_type: EventType = EventType.MEMORY_UPDATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "memory_id": "",
        "memory_type": "working",
        "key": "",
        "changes": {},
    })


@dataclass(kw_only=True)
class MemoryConsolidated(Event):
    """Memories have been consolidated."""

    event_type: EventType = EventType.MEMORY_CONSOLIDATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "source_type": "working",
        "target_type": "engineering",
        "count": 0,
    })


# =============================================================================
# Skill Events
# =============================================================================


@dataclass(kw_only=True)
class SkillLoaded(Event):
    """Skill has been loaded."""

    event_type: EventType = EventType.SKILL_LOADED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "skill_id": "",
        "name": "",
        "version": "",
        "source": "",
    })


@dataclass(kw_only=True)
class SkillUnloaded(Event):
    """Skill has been unloaded."""

    event_type: EventType = EventType.SKILL_UNLOADED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "skill_id": "",
        "reason": "",
    })


@dataclass(kw_only=True)
class SkillExecuted(Event):
    """Skill has been executed."""

    event_type: EventType = EventType.SKILL_EXECUTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "skill_id": "",
        "execution_id": "",
        "input": {},
        "output": {},
        "duration_ms": 0,
    })


@dataclass(kw_only=True)
class SkillFailed(Event):
    """Skill execution failed."""

    event_type: EventType = EventType.SKILL_FAILED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "skill_id": "",
        "execution_id": "",
        "error": "",
        "input": {},
    })


# =============================================================================
# MCP Events
# =============================================================================


@dataclass(kw_only=True)
class MCPServerConnected(Event):
    """MCP server connected."""

    event_type: EventType = EventType.MCP_SERVER_CONNECTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "server_id": "",
        "name": "",
        "transport": "stdio",
        "tools": [],
    })


@dataclass(kw_only=True)
class MCPServerDisconnected(Event):
    """MCP server disconnected."""

    event_type: EventType = EventType.MCP_SERVER_DISCONNECTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "server_id": "",
        "reason": "",
    })


@dataclass(kw_only=True)
class MCPToolCalled(Event):
    """MCP tool called."""

    event_type: EventType = EventType.MCP_TOOL_CALLED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "call_id": "",
        "server_id": "",
        "tool_name": "",
        "arguments": {},
    })


@dataclass(kw_only=True)
class MCPToolResult(Event):
    """MCP tool result received."""

    event_type: EventType = EventType.MCP_TOOL_RESULT
    payload: dict[str, Any] = field(default_factory=lambda: {
        "call_id": "",
        "success": True,
        "result": {},
        "error": None,
    })


# =============================================================================
# Council Events
# =============================================================================


@dataclass(kw_only=True)
class CouncilConvened(Event):
    """Council has been convened."""

    event_type: EventType = EventType.COUNCIL_CONVENED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "council_id": "",
        "topic": "",
        "members": [],
        "consensus_required": True,
    })


@dataclass(kw_only=True)
class CouncilDeliberated(Event):
    """Council has deliberated."""

    event_type: EventType = EventType.COUNCIL_DELIBERATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "council_id": "",
        "round": 0,
        "arguments": [],
    })


@dataclass(kw_only=True)
class CouncilDecided(Event):
    """Council has reached a decision."""

    event_type: EventType = EventType.COUNCIL_DECIDED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "council_id": "",
        "decision": "",
        "consensus": True,
        "votes": {},
    })


@dataclass(kw_only=True)
class CouncilDissented(Event):
    """Council member dissented."""

    event_type: EventType = EventType.COUNCIL_DISSENTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "council_id": "",
        "member": "",
        "reason": "",
    })


# =============================================================================
# AI Agency Events
# =============================================================================


@dataclass(kw_only=True)
class SecurityAuditRequested(Event):
    """Security audit requested."""

    event_type: EventType = EventType.SECURITY_AUDIT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "target": "",
        "scope": "full",
    })


@dataclass(kw_only=True)
class SecurityAuditCompleted(Event):
    """Security audit completed."""

    event_type: EventType = EventType.SECURITY_AUDIT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "findings": [],
        "risk_score": 0,
    })


@dataclass(kw_only=True)
class PerformanceAuditRequested(Event):
    """Performance audit requested."""

    event_type: EventType = EventType.PERFORMANCE_AUDIT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "target": "",
        "metrics": [],
    })


@dataclass(kw_only=True)
class PerformanceAuditCompleted(Event):
    """Performance audit completed."""

    event_type: EventType = EventType.PERFORMANCE_AUDIT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "metrics": {},
        "bottlenecks": [],
    })


@dataclass(kw_only=True)
class ChaosExperimentRequested(Event):
    """Chaos experiment requested."""

    event_type: EventType = EventType.CHAOS_EXPERIMENT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "experiment_id": "",
        "type": "latency",
        "target": "",
        "intensity": 0.5,
    })


@dataclass(kw_only=True)
class ChaosExperimentCompleted(Event):
    """Chaos experiment completed."""

    event_type: EventType = EventType.CHAOS_EXPERIMENT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "experiment_id": "",
        "result": "passed",
        "observations": [],
    })


@dataclass(kw_only=True)
class AccessibilityAuditRequested(Event):
    """Accessibility audit requested."""

    event_type: EventType = EventType.ACCESSIBILITY_AUDIT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "target": "",
        "standards": ["WCAG 2.1 AA"],
    })


@dataclass(kw_only=True)
class AccessibilityAuditCompleted(Event):
    """Accessibility audit completed."""

    event_type: EventType = EventType.ACCESSIBILITY_AUDIT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "violations": [],
        "score": 100,
    })


@dataclass(kw_only=True)
class DocumentationAuditRequested(Event):
    """Documentation audit requested."""

    event_type: EventType = EventType.DOCUMENTATION_AUDIT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "target": "",
        "check_readme": True,
        "check_docstrings": True,
    })


@dataclass(kw_only=True)
class DocumentationAuditCompleted(Event):
    """Documentation audit completed."""

    event_type: EventType = EventType.DOCUMENTATION_AUDIT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "coverage": 0.0,
        "missing": [],
    })


@dataclass(kw_only=True)
class ConcurrencyAuditRequested(Event):
    """Concurrency audit requested."""

    event_type: EventType = EventType.CONCURRENCY_AUDIT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "target": "",
        "check_race_conditions": True,
    })


@dataclass(kw_only=True)
class ConcurrencyAuditCompleted(Event):
    """Concurrency audit completed."""

    event_type: EventType = EventType.CONCURRENCY_AUDIT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "audit_id": "",
        "issues": [],
    })


@dataclass(kw_only=True)
class BugHuntRequested(Event):
    """Bug hunt requested."""

    event_type: EventType = EventType.BUG_HUNT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "hunt_id": "",
        "target": "",
        "strategy": "fuzzing",
    })


@dataclass(kw_only=True)
class BugHuntCompleted(Event):
    """Bug hunt completed."""

    event_type: EventType = EventType.BUG_HUNT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "hunt_id": "",
        "bugs_found": [],
    })


@dataclass(kw_only=True)
class ArchitectureValidationRequested(Event):
    """Architecture validation requested."""

    event_type: EventType = EventType.ARCHITECTURE_VALIDATION_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "validation_id": "",
        "target": "",
        "principles": [],
    })


@dataclass(kw_only=True)
class ArchitectureValidationCompleted(Event):
    """Architecture validation completed."""

    event_type: EventType = EventType.ARCHITECTURE_VALIDATION_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "validation_id": "",
        "compliant": True,
        "violations": [],
    })


@dataclass(kw_only=True)
class FinalJudgmentRequested(Event):
    """Final judgment requested."""

    event_type: EventType = EventType.FINAL_JUDGMENT_REQUESTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "judgment_id": "",
        "artifact": "",
        "criteria": [],
    })


@dataclass(kw_only=True)
class FinalJudgmentCompleted(Event):
    """Final judgment completed."""

    event_type: EventType = EventType.FINAL_JUDGMENT_COMPLETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "judgment_id": "",
        "verdict": "approve",
        "reasoning": "",
    })


# =============================================================================
# Checkpoint Events
# =============================================================================


@dataclass(kw_only=True)
class CheckpointCreated(Event):
    """Checkpoint has been created."""

    event_type: EventType = EventType.CHECKPOINT_CREATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "checkpoint_id": "",
        "workflow_id": "",
        "state": {},
        "step": 0,
    })


@dataclass(kw_only=True)
class CheckpointRestored(Event):
    """Checkpoint has been restored."""

    event_type: EventType = EventType.CHECKPOINT_RESTORED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "checkpoint_id": "",
        "workflow_id": "",
        "restored_state": {},
    })


@dataclass(kw_only=True)
class CheckpointDeleted(Event):
    """Checkpoint has been deleted."""

    event_type: EventType = EventType.CHECKPOINT_DELETED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "checkpoint_id": "",
        "reason": "",
    })


# =============================================================================
# Retry Events
# =============================================================================


@dataclass(kw_only=True)
class RetryBudgetExhausted(Event):
    """Retry budget has been exhausted."""

    event_type: EventType = EventType.RETRY_BUDGET_EXHAUSTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "max_retries": 0,
        "attempts": 0,
    })


@dataclass(kw_only=True)
class RetryScheduled(Event):
    """Retry has been scheduled."""

    event_type: EventType = EventType.RETRY_SCHEDULED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "retry_count": 0,
        "delay_ms": 0,
    })


@dataclass(kw_only=True)
class RetryExecuted(Event):
    """Retry has been executed."""

    event_type: EventType = EventType.RETRY_EXECUTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "task_id": "",
        "service": "",
        "retry_count": 0,
    })


# =============================================================================
# Root Cause Events
# =============================================================================


@dataclass(kw_only=True)
class RootCauseAnalyzed(Event):
    """Root cause has been analyzed."""

    event_type: EventType = EventType.ROOT_CAUSE_ANALYZED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "analysis_id": "",
        "failure_event_id": "",
        "root_cause": "",
        "category": "transient",
        "responsible_service": "",
        "recommended_action": "retry",
    })


@dataclass(kw_only=True)
class RootCauseResolved(Event):
    """Root cause has been resolved."""

    event_type: EventType = EventType.ROOT_CAUSE_RESOLVED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "analysis_id": "",
        "resolution": "",
        "preventive_measures": [],
    })


@dataclass(kw_only=True)
class FailureClassified(Event):
    """Failure has been classified."""

    event_type: EventType = EventType.FAILURE_CLASSIFIED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "failure_id": "",
        "category": "transient",
        "severity": "medium",
        "service": "",
    })


# =============================================================================
# Learning Events
# =============================================================================


@dataclass(kw_only=True)
class LearningCaptured(Event):
    """Learning has been captured."""

    event_type: EventType = EventType.LEARNING_CAPTURED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "learning_id": "",
        "category": "pattern",
        "description": "",
        "context": {},
        "applicability": [],
    })


@dataclass(kw_only=True)
class PatternExtracted(Event):
    """Pattern has been extracted."""

    event_type: EventType = EventType.PATTERN_EXTRACTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "pattern_id": "",
        "pattern_type": "success",
        "description": "",
        "frequency": 1,
        "examples": [],
    })


@dataclass(kw_only=True)
class KnowledgeUpdated(Event):
    """Engineering knowledge has been updated."""

    event_type: EventType = EventType.KNOWLEDGE_UPDATED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "knowledge_id": "",
        "topic": "",
        "content": "",
        "source": "project",
    })


# =============================================================================
# State Events
# =============================================================================


@dataclass(kw_only=True)
class StateTransitioned(Event):
    """State has transitioned."""

    event_type: EventType = EventType.STATE_TRANSITIONED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "from_state": "",
        "to_state": "",
        "trigger": "",
    })


@dataclass(kw_only=True)
class StateCheckpointed(Event):
    """State has been checkpointed."""

    event_type: EventType = EventType.STATE_CHECKPOINTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "state": {},
        "checkpoint_id": "",
    })


@dataclass(kw_only=True)
class StateRestored(Event):
    """State has been restored."""

    event_type: EventType = EventType.STATE_RESTORED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "workflow_id": "",
        "checkpoint_id": "",
        "restored_state": {},
    })


# =============================================================================
# Service Lifecycle Events
# =============================================================================
@dataclass(kw_only=True)
class ServiceRegistered(Event):
    """An Engineering Service has been registered with the registry."""

    event_type: EventType = EventType.SERVICE_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "service": "",
        "version": "",
    })


@dataclass(kw_only=True)
class ServiceStarted(Event):
    """An Engineering Service has started."""

    event_type: EventType = EventType.SERVICE_STARTED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "service": "",
        "version": "",
    })


@dataclass(kw_only=True)
class ServiceStopped(Event):
    """An Engineering Service has stopped."""

    event_type: EventType = EventType.SERVICE_STOPPED
    payload: dict[str, Any] = field(default_factory=lambda: {
        "service": "",
        "reason": "",
    })


@dataclass(kw_only=True)
class ServiceHealthy(Event):
    """An Engineering Service passed its health check."""

    event_type: EventType = EventType.SERVICE_HEALTHY
    payload: dict[str, Any] = field(default_factory=lambda: {
        "service": "",
    })


@dataclass(kw_only=True)
class ServiceUnhealthy(Event):
    """An Engineering Service failed its health check or failed to start."""

    event_type: EventType = EventType.SERVICE_UNHEALTHY
    payload: dict[str, Any] = field(default_factory=lambda: {
        "service": "",
        "error": "",
    })



__all__ = [
    # Kernel
    "KernelStarted",
    "KernelStopped",
    "KernelError",
    # Task/Workflow
    "TaskCreated",
    "TaskStarted",
    "TaskCompleted",
    "TaskFailed",
    "TaskRetryRequested",
    "TaskCancelled",
    "WorkflowCreated",
    "WorkflowStarted",
    "WorkflowCompleted",
    "WorkflowFailed",
    "WorkflowPaused",
    "WorkflowResumed",
    # Planning
    "PlanningRequested",
    "PlanningCompleted",
    "PlanningFailed",
    "PlanApproved",
    "PlanRejected",
    # Coding
    "CodingStarted",
    "CodingCompleted",
    "CodingFailed",
    "CodeGenerated",
    "CodeReviewRequested",
    # Review
    "ReviewStarted",
    "ReviewCompleted",
    "ReviewFailed",
    "ReviewApproved",
    "ReviewRejected",
    # Testing
    "TestingStarted",
    "TestingCompleted",
    "TestingFailed",
    "TestsPassed",
    "TestsFailed",
    "TestGenerated",
    "SecurityIssueFound",
    "PerformanceIssueFound",
    # Deployment
    "DeploymentRequested",
    "DeploymentStarted",
    "DeploymentCompleted",
    "DeploymentFailed",
    "DeploymentRolledBack",
    # Operations
    "ProductionIncident",
    "MetricsAlert",
    "LogAnomalyDetected",
    "UserFeedbackReceived",
    # Memory
    "MemoryStored",
    "MemoryRetrieved",
    "MemoryUpdated",
    "MemoryConsolidated",
    # Skill
    "SkillLoaded",
    "SkillUnloaded",
    "SkillExecuted",
    "SkillFailed",
    # MCP
    "MCPServerConnected",
    "MCPServerDisconnected",
    "MCPToolCalled",
    "MCPToolResult",
    # Council
    "CouncilConvened",
    "CouncilDeliberated",
    "CouncilDecided",
    "CouncilDissented",
    # AI Agency
    "SecurityAuditRequested",
    "SecurityAuditCompleted",
    "PerformanceAuditRequested",
    "PerformanceAuditCompleted",
    "ChaosExperimentRequested",
    "ChaosExperimentCompleted",
    "AccessibilityAuditRequested",
    "AccessibilityAuditCompleted",
    "DocumentationAuditRequested",
    "DocumentationAuditCompleted",
    "ConcurrencyAuditRequested",
    "ConcurrencyAuditCompleted",
    "BugHuntRequested",
    "BugHuntCompleted",
    "ArchitectureValidationRequested",
    "ArchitectureValidationCompleted",
    "FinalJudgmentRequested",
    "FinalJudgmentCompleted",
    # Checkpoint
    "CheckpointCreated",
    "CheckpointRestored",
    "CheckpointDeleted",
    # Retry
    "RetryBudgetExhausted",
    "RetryScheduled",
    "RetryExecuted",
    # Root Cause
    "RootCauseAnalyzed",
    "RootCauseResolved",
    "FailureClassified",
    # Learning
    "LearningCaptured",
    "PatternExtracted",
    "KnowledgeUpdated",
    # State
    "StateTransitioned",
    "StateCheckpointed",
    "StateRestored",
    # Service
    "ServiceRegistered",
    "ServiceStarted",
    "ServiceStopped",
    "ServiceHealthy",
    "ServiceUnhealthy",
]