"""
Self-Prompt Structure for AI-OS M13.

Defines the canonical self-prompt data structure as specified in
M13_SELF_PROMPT_INTEGRATION_SPEC.md. Self-prompts represent AI-OS's
authoritative internal directives for bounded execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SelfPromptPriority(str, Enum):
    """Execution priority levels for self-prompts."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SelfPromptValidationStatus(str, Enum):
    """Validation status of a self-prompt."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ExecutionBounds:
    """Bounded execution constraints for a self-prompt directive."""
    timeout_seconds: int = 300
    max_retries: int = 3
    resource_limits: dict[str, Any] = field(default_factory=dict)
    allowed_operations: list[str] = field(default_factory=list)
    prohibited_operations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SelfPromptDirective:
    """The execution directive component of a self-prompt."""
    action_type: str
    target_systems: list[str]
    parameters: dict[str, Any]
    success_criteria: dict[str, Any]
    failure_conditions: list[str]
    execution_bounds: ExecutionBounds
    provenance_chain: list[str]
    security_context: dict[str, Any]
    knowledge_bounds: dict[str, Any]
    learning_objectives: list[str]


@dataclass(frozen=True)
class SelfPromptContext:
    """Complete context from all lifecycle phases integrated into self-prompt."""
    user_intent: dict[str, Any] = field(default_factory=dict)
    planning_outcome: dict[str, Any] = field(default_factory=dict)
    research_findings: dict[str, Any] = field(default_factory=dict)
    requirements_spec: dict[str, Any] = field(default_factory=dict)
    council_reviews: dict[str, Any] = field(default_factory=dict)
    approved_plan: dict[str, Any] = field(default_factory=dict)
    task_assignments: dict[str, Any] = field(default_factory=dict)
    prior_execution_results: dict[str, Any] = field(default_factory=dict)
    test_outcomes: dict[str, Any] = field(default_factory=dict)
    review_feedback: dict[str, Any] = field(default_factory=dict)
    verification_status: dict[str, Any] = field(default_factory=dict)
    final_judgment: dict[str, Any] = field(default_factory=dict)
    decision_outcome: dict[str, Any] = field(default_factory=dict)
    evidence_collected: dict[str, Any] = field(default_factory=dict)
    learning_extracted: dict[str, Any] = field(default_factory=dict)
    knowledge_updated: dict[str, Any] = field(default_factory=dict)
    state_persisted: dict[str, Any] = field(default_factory=dict)
    current_aios_state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SelfPromptMetadata:
    """Metadata for self-prompt tracking and lifecycle."""
    version: str = "1.0"
    generated_by: str = "aios_kernel"
    validation_status: SelfPromptValidationStatus = SelfPromptValidationStatus.PENDING
    validation_timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    priority: SelfPromptPriority = SelfPromptPriority.NORMAL
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SelfPrompt:
    """
    Canonical self-prompt structure for AI-OS M13.

    Represents AI-OS's authoritative internal directive for bounded execution,
    encapsulating current state, goals, and context while defining clear
    execution attempts with success/failure criteria.
    """
    prompt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cycle_id: str = field(default_factory=lambda: f"cycle_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: SelfPromptContext = field(default_factory=SelfPromptContext)
    directive: Optional[SelfPromptDirective] = None
    metadata: SelfPromptMetadata = field(default_factory=SelfPromptMetadata)

    def with_directive(self, directive: SelfPromptDirective) -> SelfPrompt:
        """Return new self-prompt with directive set."""
        return SelfPrompt(
            prompt_id=self.prompt_id,
            cycle_id=self.cycle_id,
            timestamp=self.timestamp,
            context=self.context,
            directive=directive,
            metadata=self.metadata,
        )

    def with_validation(self, status: SelfPromptValidationStatus, expires_at: Optional[datetime] = None) -> SelfPrompt:
        """Return new self-prompt with validation status updated."""
        new_metadata = SelfPromptMetadata(
            version=self.metadata.version,
            generated_by=self.metadata.generated_by,
            validation_status=status,
            validation_timestamp=datetime.now(timezone.utc),
            expires_at=expires_at or self.metadata.expires_at,
            priority=self.metadata.priority,
            tags=self.metadata.tags,
        )
        return SelfPrompt(
            prompt_id=self.prompt_id,
            cycle_id=self.cycle_id,
            timestamp=self.timestamp,
            context=self.context,
            directive=self.directive,
            metadata=new_metadata,
        )

    def is_valid(self) -> bool:
        """Check if self-prompt is validated and not expired."""
        if self.metadata.validation_status != SelfPromptValidationStatus.VALIDATED:
            return False
        if self.metadata.expires_at and datetime.now(timezone.utc) > self.metadata.expires_at:
            return False
        return self.directive is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for EventBus publishing."""
        return {
            "prompt_id": self.prompt_id,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self._context_to_dict(self.context),
            "directive": self._directive_to_dict(self.directive) if self.directive else None,
            "metadata": {
                "version": self.metadata.version,
                "generated_by": self.metadata.generated_by,
                "validation_status": self.metadata.validation_status.value,
                "validation_timestamp": self.metadata.validation_timestamp.isoformat() if self.metadata.validation_timestamp else None,
                "expires_at": self.metadata.expires_at.isoformat() if self.metadata.expires_at else None,
                "priority": self.metadata.priority.value,
                "tags": self.metadata.tags,
            }
        }

    def _context_to_dict(self, ctx: SelfPromptContext) -> dict[str, Any]:
        return {
            "user_intent": ctx.user_intent,
            "planning_outcome": ctx.planning_outcome,
            "research_findings": ctx.research_findings,
            "requirements_spec": ctx.requirements_spec,
            "council_reviews": ctx.council_reviews,
            "approved_plan": ctx.approved_plan,
            "task_assignments": ctx.task_assignments,
            "prior_execution_results": ctx.prior_execution_results,
            "test_outcomes": ctx.test_outcomes,
            "review_feedback": ctx.review_feedback,
            "verification_status": ctx.verification_status,
            "final_judgment": ctx.final_judgment,
            "decision_outcome": ctx.decision_outcome,
            "evidence_collected": ctx.evidence_collected,
            "learning_extracted": ctx.learning_extracted,
            "knowledge_updated": ctx.knowledge_updated,
            "state_persisted": ctx.state_persisted,
            "current_aios_state": ctx.current_aios_state,
        }

    def _directive_to_dict(self, directive: SelfPromptDirective) -> dict[str, Any]:
        return {
            "action_type": directive.action_type,
            "target_systems": directive.target_systems,
            "parameters": directive.parameters,
            "success_criteria": directive.success_criteria,
            "failure_conditions": directive.failure_conditions,
            "execution_bounds": {
                "timeout_seconds": directive.execution_bounds.timeout_seconds,
                "max_retries": directive.execution_bounds.max_retries,
                "resource_limits": directive.execution_bounds.resource_limits,
                "allowed_operations": directive.execution_bounds.allowed_operations,
                "prohibited_operations": directive.execution_bounds.prohibited_operations,
            },
            "provenance_chain": directive.provenance_chain,
            "security_context": directive.security_context,
            "knowledge_bounds": directive.knowledge_bounds,
            "learning_objectives": directive.learning_objectives,
        }

    @classmethod
    def create_empty(cls, cycle_id: str) -> SelfPrompt:
        """Create an empty self-prompt for a new cycle."""
        return cls(cycle_id=cycle_id)