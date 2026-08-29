"""
Self-Prompt Generator for AI-OS M13.

Generates authoritative internal directives (self-prompts) from
synthesized lifecycle context. Validates all directives before
they enter bounded execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from aios.core.self_prompt import (
    SelfPrompt,
    SelfPromptContext,
    SelfPromptDirective,
    SelfPromptMetadata,
    SelfPromptPriority,
    SelfPromptValidationStatus,
    ExecutionBounds,
)


@dataclass
class GenerationResult:
    """Result of self-prompt generation attempt."""
    success: bool
    self_prompt: Optional[SelfPrompt] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SelfPromptGenerator:
    """
    AI-OS Self-Prompt Generator — Authoritative Directive Generation.

    Synthesizes the complete 19-phase lifecycle context into a validated
    SelfPrompt directive for bounded execution. Implements validation
    gates per M13_SELF_PROMPT_INTEGRATION_SPEC.md.
    """

    DEFAULT_TIMEOUT = 300  # 5 minutes
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MAX_CYCLES = 3
    DEFAULT_MAX_DEPTH = 5

    def __init__(
        self,
        kernel: Any = None,
        event_bus: Any = None,
        config_manager: Any = None,
        logger: Any = None,
        security_manager: Any = None,
        capability_manager: Any = None,
        state_manager: Any = None,
        workflow_manager: Any = None,
    ):
        """
        Initialize the Self-Prompt Generator.

        All core components injected to maintain canonical authority.
        """
        self._kernel = kernel
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._logger = logger
        self._security_manager = security_manager
        self._capability_manager = capability_manager
        self._state_manager = state_manager
        self._workflow_manager = workflow_manager

        # Configuration (from kernel config or defaults)
        self._max_cycles = self.DEFAULT_MAX_CYCLES
        self._max_depth = self.DEFAULT_MAX_DEPTH
        self._convergence_action = "escalate"  # escalate | pause | degrade

        # Validation rules
        self._required_context_fields = [
            "user_intent",
            "approved_plan",
            "task_assignments",
        ]
        self._required_directive_fields = [
            "action_type",
            "target_systems",
            "success_criteria",
            "failure_conditions",
            "execution_bounds",
        ]

    def configure(
        self,
        max_cycles: int = 3,
        max_depth: int = 5,
        convergence_action: str = "escalate",
    ) -> None:
        """Configure generator behavior from kernel config."""
        self._max_cycles = max_cycles
        self._max_depth = max_depth
        self._convergence_action = convergence_action

    async def generate(
        self,
        cycle_id: str,
        context: SelfPromptContext,
    ) -> SelfPrompt:
        """
        Generate a validated self-prompt for the given cycle and context.

        This is the main entry point called by SelfLoopEngine at phase 8
        (SELF_PROMPT). Performs full validation before returning.

        Args:
            cycle_id: The self-loop cycle identifier
            context: Complete lifecycle context from phases 1-7

        Returns:
            Validated SelfPrompt ready for bounded execution
        """
        # Generate initial prompt
        result = await self._generate_prompt(cycle_id, context)

        if not result.success:
            # Generate fallback noop prompt on failure
            fallback = self._create_fallback_prompt(cycle_id, context, result.errors)
            await self._emit_generation_event(cycle_id, fallback, result.errors)
            return fallback

        # Validate the generated prompt
        validation_result = await self._validate_prompt(result.self_prompt)

        if not validation_result.success:
            # Generate fallback with validation errors
            fallback = self._create_fallback_prompt(
                cycle_id, context, validation_result.errors
            )
            await self._emit_generation_event(cycle_id, fallback, validation_result.errors)
            return fallback

        # Validation passed — emit event and return
        await self._emit_generation_event(cycle_id, result.self_prompt, [])
        return result.self_prompt

    async def _generate_prompt(
        self,
        cycle_id: str,
        context: SelfPromptContext,
    ) -> GenerationResult:
        """Internal prompt generation logic."""
        errors = []
        warnings = []

        # 1. Validate required context
        context_errors = self._validate_context(context)
        errors.extend(context_errors)

        # 2. Synthesize directive from context
        directive = await self._synthesize_directive(cycle_id, context)

        if not directive:
            errors.append("Failed to synthesize directive from context")
            return GenerationResult(success=False, errors=errors, warnings=warnings)

        # 3. Create self-prompt with directive
        metadata = SelfPromptMetadata(
            version="1.0",
            generated_by="SelfPromptGenerator",
            validation_status=SelfPromptValidationStatus.PENDING,
            validation_timestamp=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            priority=SelfPromptPriority.NORMAL,
            tags=[f"cycle_{cycle_id}", "auto_generated"],
        )

        self_prompt = SelfPrompt(
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc),
            context=context,
            directive=directive,
            metadata=metadata,
        )

        return GenerationResult(success=True, self_prompt=self_prompt, warnings=warnings)

    def _validate_context(self, context: SelfPromptContext) -> list[str]:
        """Validate that context has minimum required fields."""
        errors = []

        if not context.user_intent:
            errors.append("Missing required context: user_intent")
        if not context.approved_plan:
            errors.append("Missing required context: approved_plan")
        if not context.task_assignments:
            errors.append("Missing required context: task_assignments")

        # Check for convergence indicators
        if context.approved_plan and context.approved_plan.get("convergence_detected"):
            warnings = []
            if context.approved_plan.get("cycle_count", 0) >= self._max_cycles:
                errors.append(f"Max cycles exceeded: {context.approved_plan.get('cycle_count')}")
            if context.approved_plan.get("depth", 0) >= self._max_depth:
                errors.append(f"Max depth exceeded: {context.approved_plan.get('depth')}")

        return errors

    async def _synthesize_directive(
        self,
        cycle_id: str,
        context: SelfPromptContext,
    ) -> Optional[SelfPromptDirective]:
        """
        Synthesize execution directive from lifecycle context.

        This is the core intelligence: mapping context → bounded directive.
        In mock mode, returns a safe noop directive.
        """
        # Determine action type from approved plan
        action_type = context.approved_plan.get("action_type", "noop")
        target_systems = context.approved_plan.get("target_systems", [])
        parameters = context.approved_plan.get("parameters", {})

        # If no systems specified, infer from task assignments
        if not target_systems and context.task_assignments:
            target_systems = list(context.task_assignments.values())

        # Success criteria from requirements spec
        success_criteria = {
            "completed": True,
            "all_tasks_succeeded": True,
        }
        if context.requirements_spec:
            success_criteria["requirements_met"] = True

        # Failure conditions
        failure_conditions = [
            "timeout",
            "resource_exhausted",
            "security_violation",
            "validation_failed",
        ]
        risk_assessment = context.approved_plan.get("risk_assessment")
        if risk_assessment:
            failure_conditions.extend(risk_assessment.get("failure_modes", []))

        # Execution bounds
        execution_bounds = ExecutionBounds(
            timeout_seconds=context.approved_plan.get("timeout_seconds", self.DEFAULT_TIMEOUT),
            max_retries=context.approved_plan.get("max_retries", self.DEFAULT_MAX_RETRIES),
            resource_limits=context.approved_plan.get("resource_limits", {}),
            allowed_operations=context.approved_plan.get("allowed_operations", ["execute", "read", "write"]),
            prohibited_operations=context.approved_plan.get("prohibited_operations", ["delete", "admin", "system"]),
        )

        # Provenance chain
        provenance_chain = [
            f"cycle_{cycle_id}",
            f"intent_{context.user_intent.get('intent_id', 'unknown')}",
            f"plan_{context.approved_plan.get('plan_id', 'unknown')}",
        ]

        # Security context from security_manager if available
        security_context = {}
        if self._security_manager and hasattr(self._security_manager, "get_security_context"):
            try:
                security_context = await self._security_manager.get_security_context()
            except Exception:
                pass

        # Knowledge bounds
        knowledge_bounds = {
            "domains": list(context.research_findings.keys()) if context.research_findings else [],
            "data_sources": list(context.evidence_collected.keys()) if context.evidence_collected else [],
        }

        # Learning objectives
        learning_objectives = context.learning_extracted.get("objectives", []) if context.learning_extracted else [
            "cycle_completion",
            "pattern_recognition",
        ]

        return SelfPromptDirective(
            action_type=action_type,
            target_systems=target_systems,
            parameters=parameters,
            success_criteria=success_criteria,
            failure_conditions=failure_conditions,
            execution_bounds=execution_bounds,
            provenance_chain=provenance_chain,
            security_context=security_context,
            knowledge_bounds=knowledge_bounds,
            learning_objectives=learning_objectives,
        )

    async def _validate_prompt(self, self_prompt: SelfPrompt) -> GenerationResult:
        """
        Validate a self-prompt against all M13 gates.

        Gates:
        1. Structure validation (all required fields present)
        2. Security validation (SecurityManager authorization)
        3. Capability validation (CapabilityManager can route)
        4. Bounds validation (execution bounds within limits)
        5. Provenance validation (chain integrity)
        6. Convergence validation (not stuck in loop)
        """
        errors = []
        warnings = []

        # Gate 1: Structure validation
        structure_errors = self._validate_structure(self_prompt)
        errors.extend(structure_errors)

        # Gate 2: Security validation
        if self._security_manager:
            security_errors = await self._validate_security(self_prompt)
            errors.extend(security_errors)

        # Gate 3: Capability validation
        if self._capability_manager:
            capability_errors = await self._validate_capabilities(self_prompt)
            errors.extend(capability_errors)

        # Gate 4: Bounds validation
        bounds_errors = self._validate_bounds(self_prompt)
        errors.extend(bounds_errors)

        # Gate 5: Provenance validation
        provenance_errors = self._validate_provenance(self_prompt)
        errors.extend(provenance_errors)

        # Gate 6: Convergence validation
        convergence_errors = self._validate_convergence(self_prompt)
        errors.extend(convergence_errors)

        if errors:
            return GenerationResult(success=False, errors=errors, warnings=warnings)

        # Update metadata to validated
        validated_prompt = self_prompt.with_validation(SelfPromptValidationStatus.VALIDATED)
        return GenerationResult(success=True, self_prompt=validated_prompt, warnings=warnings)

    def _validate_structure(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate self-prompt structure completeness."""
        errors = []

        if not self_prompt.directive:
            errors.append("Missing directive")
            return errors

        directive = self_prompt.directive

        if not directive.action_type:
            errors.append("Directive missing action_type")
        if not directive.target_systems:
            errors.append("Directive missing target_systems (empty)")
        if not directive.success_criteria:
            errors.append("Directive missing success_criteria")
        if not directive.failure_conditions:
            errors.append("Directive missing failure_conditions")
        if not directive.execution_bounds:
            errors.append("Directive missing execution_bounds")
        if not directive.provenance_chain:
            errors.append("Directive missing provenance_chain")

        # Validate execution bounds
        if directive.execution_bounds:
            if directive.execution_bounds.timeout_seconds <= 0:
                errors.append("execution_bounds.timeout_seconds must be positive")
            if directive.execution_bounds.max_retries < 0:
                errors.append("execution_bounds.max_retries must be non-negative")

        return errors

    async def _validate_security(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate directive against security policy."""
        errors = []

        if not self._security_manager or not self_prompt.directive:
            return errors

        directive = self_prompt.directive

        # Check if security manager can authorize this action
        try:
            authorized = await self._security_manager.authorize(
                action=directive.action_type,
                targets=directive.target_systems,
                context=directive.security_context,
            )
            if not authorized:
                errors.append(f"SecurityManager denied authorization for {directive.action_type} on {directive.target_systems}")
        except Exception as e:
            errors.append(f"Security validation error: {e}")

        return errors

    async def _validate_capabilities(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate all target systems have registered capabilities."""
        errors = []

        if not self._capability_manager or not self_prompt.directive:
            return errors

        directive = self_prompt.directive

        for system in directive.target_systems:
            try:
                capability = await self._capability_manager.get_capability(system)
                if not capability:
                    errors.append(f"No registered capability for target system: {system}")
            except Exception:
                errors.append(f"Capability lookup failed for: {system}")

        return errors

    def _validate_bounds(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate execution bounds are within system limits."""
        errors = []

        if not self_prompt.directive or not self_prompt.directive.execution_bounds:
            return errors

        bounds = self_prompt.directive.execution_bounds

        # System-wide limits
        MAX_TIMEOUT = 3600  # 1 hour
        MAX_RETRIES = 10

        if bounds.timeout_seconds > MAX_TIMEOUT:
            errors.append(f"timeout_seconds {bounds.timeout_seconds} exceeds max {MAX_TIMEOUT}")

        if bounds.max_retries > MAX_RETRIES:
            errors.append(f"max_retries {bounds.max_retries} exceeds max {MAX_RETRIES}")

        # Resource limits validation
        if bounds.resource_limits:
            for resource, limit in bounds.resource_limits.items():
                if not isinstance(limit, (int, float)) or limit < 0:
                    errors.append(f"Invalid resource limit for {resource}: {limit}")

        return errors

    def _validate_provenance(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate provenance chain integrity."""
        errors = []

        if not self_prompt.directive or not self_prompt.directive.provenance_chain:
            errors.append("Missing provenance chain")
            return errors

        chain = self_prompt.directive.provenance_chain

        # Check chain is not empty
        if not chain:
            errors.append("Provenance chain is empty")
            return errors

        # Check for expected patterns (cycle, intent, plan)
        has_cycle = any("cycle_" in p for p in chain)
        has_intent = any("intent_" in p for p in chain)
        has_plan = any("plan_" in p for p in chain)

        if not has_cycle:
            errors.append("Provenance chain missing cycle reference")
        if not has_intent:
            errors.append("Provenance chain missing intent reference")
        if not has_plan:
            errors.append("Provenance chain missing plan reference")

        return errors

    def _validate_convergence(self, self_prompt: SelfPrompt) -> list[str]:
        """Validate self-prompt doesn't indicate convergence/stuck loop."""
        errors = []

        if not self_prompt.context or not self_prompt.context.approved_plan:
            return errors

        plan = self_prompt.context.approved_plan

        cycle_count = plan.get("cycle_count", 0)
        depth = plan.get("depth", 0)

        if cycle_count >= self._max_cycles:
            errors.append(f"Convergence detected: cycle_count {cycle_count} >= max_cycles {self._max_cycles}")

        if depth >= self._max_depth:
            errors.append(f"Convergence detected: depth {depth} >= max_depth {self._max_depth}")

        # Check for duplicate recent directives (simplified)
        if plan.get("duplicate_directive_detected"):
            errors.append("Duplicate directive detected in recent history")

        return errors

    def _create_fallback_prompt(
        self,
        cycle_id: str,
        context: SelfPromptContext,
        errors: list[str],
    ) -> SelfPrompt:
        """Create a safe fallback noop prompt when generation fails."""
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={"reason": "generation_failed", "errors": errors},
            success_criteria={"completed": True},
            failure_conditions=["none"],
            execution_bounds=ExecutionBounds(
                timeout_seconds=30,
                max_retries=0,
                allowed_operations=["noop"],
            ),
            provenance_chain=[f"cycle_{cycle_id}_fallback"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=["error_recovery"],
        )

        metadata = SelfPromptMetadata(
            version="1.0",
            generated_by="SelfPromptGenerator",
            validation_status=SelfPromptValidationStatus.REJECTED,
            validation_timestamp=datetime.now(timezone.utc),
            priority=SelfPromptPriority.LOW,
            tags=[f"cycle_{cycle_id}", "fallback", "generation_failed"],
        )

        return SelfPrompt(
            cycle_id=cycle_id,
            timestamp=datetime.now(timezone.utc),
            context=context,
            directive=directive,
            metadata=metadata,
        )

    async def _emit_generation_event(
        self,
        cycle_id: str,
        self_prompt: SelfPrompt,
        errors: list[str],
    ) -> None:
        """Emit self-prompt generation event to EventBus."""
        if self._event_bus:
            try:
                from aios.events.core.event import Event
                from aios.events.core.identity import ComponentIdentity, ComponentType
                from aios.events.core.types import EventType as CoreEventType, SemanticVersion

                identity = ComponentIdentity(
                    component_type=ComponentType.CORE_COMPONENT,
                    component_name="SelfPromptGenerator",
                    version=SemanticVersion(1, 0, 0),
                )

                event = Event(
                    eventType=CoreEventType.SYSTEM_HEALTH_CHECK,
                    source=identity,
                    correlationId=uuid.uuid4(),
                    payload={
                        "event_subtype": "SELF_PROMPT_GENERATED",
                        "cycle_id": cycle_id,
                        "prompt_id": self_prompt.prompt_id,
                        "validated": self_prompt.metadata.validation_status == SelfPromptValidationStatus.VALIDATED,
                        "errors": errors,
                        "action_type": self_prompt.directive.action_type if self_prompt.directive else "none",
                    },
                )
                await self._event_bus.publish(event)
            except Exception:
                # Fail silently
                pass

    def get_config(self) -> dict[str, Any]:
        """Get current generator configuration."""
        return {
            "max_cycles": self._max_cycles,
            "max_depth": self._max_depth,
            "convergence_action": self._convergence_action,
        }