"""
Self-Loop Engine for AI-OS M13.

Implements the 19-phase canonical self-loop as the single authoritative
autonomous decision-making engine. All external systems operate as bounded
resources under AI-OS control.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from aios.core.self_prompt import (
    SelfPrompt,
    SelfPromptContext,
    SelfPromptDirective,
    SelfPromptMetadata,
    SelfPromptPriority,
    SelfPromptValidationStatus,
    ExecutionBounds,
)


class SelfLoopPhase(str, Enum):
    """The 19 canonical phases of the AI-OS self-loop."""
    USER_INTENT = "user_intent"
    PLANNING = "planning"
    RESEARCH = "research"
    REQUIREMENTS = "requirements"
    COUNCILS_REVIEWS = "councils_reviews"
    PLAN = "plan"
    TASKS = "tasks"
    SELF_PROMPT = "self_prompt"
    BOUNDED_EXECUTION = "bounded_execution"
    TEST = "test"
    REVIEW = "review"
    VERIFICATION = "verification"
    FINAL_JUDGMENT = "final_judgment"
    DECISION = "decision"
    EVIDENCE = "evidence"
    LEARNING = "learning"
    MEMORY_KNOWLEDGE = "memory_knowledge"
    PERSISTENCE = "persistence"
    NEXT_SELF_PROMPT = "next_self_prompt"


class SelfLoopState(str, Enum):
    """High-level self-loop operational states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED_CYCLE = "completed_cycle"
    FAILED = "failed"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


@dataclass(frozen=True)
class PhaseResult:
    """Result of a single self-loop phase execution."""
    phase: SelfLoopPhase
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    provenance_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SelfLoopCycle:
    """Represents a single iteration of the self-loop."""
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    phase_results: dict[SelfLoopPhase, PhaseResult] = field(default_factory=dict)
    current_phase: Optional[SelfLoopPhase] = None
    state: SelfLoopState = SelfLoopState.IDLE
    self_prompt: Optional[SelfPrompt] = None
    error: Optional[str] = None


class SelfLoopEngine:
    """
    AI-OS Self-Loop Engine — Single Authoritative Autonomous Decision-Making Engine.

    Implements the 19-phase canonical self-loop lifecycle as specified in
    M13_SELF_LOOP_INTEGRATION_SPEC.md. All external systems integrate as
    bounded resources under AI-OS control. AI-OS retains sole governance,
    verification, and decision-making authority.
    """

    # Phase execution order (canonical 19 phases)
    PHASE_ORDER = [
        SelfLoopPhase.USER_INTENT,
        SelfLoopPhase.PLANNING,
        SelfLoopPhase.RESEARCH,
        SelfLoopPhase.REQUIREMENTS,
        SelfLoopPhase.COUNCILS_REVIEWS,
        SelfLoopPhase.PLAN,
        SelfLoopPhase.TASKS,
        SelfLoopPhase.SELF_PROMPT,
        SelfLoopPhase.BOUNDED_EXECUTION,
        SelfLoopPhase.TEST,
        SelfLoopPhase.REVIEW,
        SelfLoopPhase.VERIFICATION,
        SelfLoopPhase.FINAL_JUDGMENT,
        SelfLoopPhase.DECISION,
        SelfLoopPhase.EVIDENCE,
        SelfLoopPhase.LEARNING,
        SelfLoopPhase.MEMORY_KNOWLEDGE,
        SelfLoopPhase.PERSISTENCE,
        SelfLoopPhase.NEXT_SELF_PROMPT,
    ]

    def __init__(
        self,
        kernel: Any = None,
        event_bus: Any = None,
        service_registry: Any = None,
        config_manager: Any = None,
        logger: Any = None,
        security_manager: Any = None,
        capability_manager: Any = None,
        state_manager: Any = None,
        workflow_manager: Any = None,
        resource_manager: Any = None,
        health_manager: Any = None,
        observability_manager: Any = None,
        memory_manager: Any = None,
    ):
        """
        Initialize the Self-Loop Engine.

        All core components are injected to maintain canonical authority
        and avoid singleton duplication. The kernel owns the engine lifecycle.
        """
        self._kernel = kernel
        self._event_bus = event_bus
        self._service_registry = service_registry
        self._config_manager = config_manager
        self._logger = logger
        self._security_manager = security_manager
        self._capability_manager = capability_manager
        self._state_manager = state_manager
        self._workflow_manager = workflow_manager
        self._resource_manager = resource_manager
        self._health_manager = health_manager
        self._observability_manager = observability_manager
        self._memory_manager = memory_manager

        self._current_cycle: Optional[SelfLoopCycle] = None
        self._phase_handlers: dict[SelfLoopPhase, Callable] = {}
        self._running = False
        self._paused = False
        self._cycle_count = 0
        self._max_cycles = 100  # Safety bound
        self._cycle_timeout_seconds = 3600  # 1 hour per cycle max

        # Mock mode for development/testing
        self._mock_mode = True

        # Register default phase handlers (mock implementations)
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register mock phase handlers for all 19 phases."""
        for phase in SelfLoopPhase:
            self._phase_handlers[phase] = self._mock_phase_handler(phase)

    def _mock_phase_handler(self, phase: SelfLoopPhase) -> Callable:
        """Create a mock handler for a phase."""

        async def handler(cycle: SelfLoopCycle, context: dict[str, Any]) -> dict[str, Any]:
            # Simulate phase work
            await asyncio.sleep(0.01)
            return {
                "phase": phase.value,
                "status": "completed",
                "mock": True,
                "output": {f"{phase.value}_result": f"mock_output_for_{phase.value}"},
            }

        return handler

    def register_phase_handler(self, phase: SelfLoopPhase, handler: Callable) -> None:
        """Register a custom handler for a specific phase (replaces mock)."""
        self._phase_handlers[phase] = handler

    @property
    def current_cycle(self) -> Optional[SelfLoopCycle]:
        """Get the currently executing cycle."""
        return self._current_cycle

    @property
    def cycle_count(self) -> int:
        """Get number of completed cycles."""
        return self._cycle_count

    @property
    def is_running(self) -> bool:
        """Check if self-loop is running."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Check if self-loop is paused."""
        return self._paused

    @property
    def mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    def set_mock_mode(self, enabled: bool) -> None:
        """Enable or disable mock mode."""
        self._mock_mode = enabled
        if enabled:
            self._register_default_handlers()

    async def start_cycle(
        self,
        user_intent: dict[str, Any],
        cycle_id: Optional[str] = None,
    ) -> SelfLoopCycle:
        """
        Start a new self-loop cycle.

        Args:
            user_intent: The user intent driving this cycle
            cycle_id: Optional cycle identifier (generated if not provided)

        Returns:
            The created SelfLoopCycle
        """
        if self._running:
            raise RuntimeError("Self-loop already running. Complete or stop current cycle first.")

        cycle_id = cycle_id or f"cycle_{uuid.uuid4().hex[:8]}"
        self._current_cycle = SelfLoopCycle(
            cycle_id=cycle_id,
            start_time=datetime.now(timezone.utc),
            state=SelfLoopState.RUNNING,
        )
        self._running = True
        self._paused = False

        # Initialize context with user intent
        context = SelfPromptContext(user_intent=user_intent)

        # Emit cycle started event
        await self._emit_event("SELF_LOOP_CYCLE_STARTED", {
            "cycle_id": cycle_id,
            "user_intent": user_intent,
        })

        return self._current_cycle

    async def execute_cycle(self, user_intent: dict[str, Any]) -> SelfLoopCycle:
        """
        Execute a complete self-loop cycle through all 19 phases.

        This is the main entry point for autonomous operation. The engine
        executes each phase in canonical order, collecting results and
        building the self-prompt for bounded execution.

        Args:
            user_intent: The user intent driving this cycle

        Returns:
            The completed SelfLoopCycle with all phase results
        """
        cycle = await self.start_cycle(user_intent)

        try:
            # Execute phases 1-7: Cognition phases (context building)
            context = await self._execute_cognition_phases(cycle, user_intent)

            # Phase 8: SELF_PROMPT — Generate authoritative directive
            self_prompt = await self._execute_self_prompt_phase(cycle, context)
            cycle.self_prompt = self_prompt

            # Phase 9: BOUNDED_EXECUTION — Execute directive within bounds
            execution_result = await self._execute_bounded_execution_phase(cycle, self_prompt)

            # Phases 10-19: Evaluation & learning phases
            await self._execute_evaluation_phases(cycle, execution_result)

            # Phase 19: NEXT_SELF_PROMPT — Prepare for next cycle
            await self._execute_next_self_prompt_phase(cycle)

            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.COMPLETED_CYCLE
            self._cycle_count += 1

            await self._emit_event("SELF_LOOP_CYCLE_COMPLETED", {
                "cycle_id": cycle.cycle_id,
                "duration_ms": (cycle.end_time - cycle.start_time).total_seconds() * 1000,
                "phases_completed": len(cycle.phase_results),
            })

            return cycle

        except Exception as e:
            cycle.end_time = datetime.now(timezone.utc)
            cycle.state = SelfLoopState.FAILED
            cycle.error = str(e)

            await self._emit_event("SELF_LOOP_CYCLE_FAILED", {
                "cycle_id": cycle.cycle_id,
                "error": str(e),
                "failed_phase": cycle.current_phase.value if cycle.current_phase else None,
            })

            # Attempt recovery
            await self._attempt_recovery(cycle, e)
            raise

        finally:
            self._running = False
            self._paused = False

    async def _execute_cognition_phases(
        self,
        cycle: SelfLoopCycle,
        user_intent: dict[str, Any],
    ) -> SelfPromptContext:
        """Execute phases 1-7: Context building phases."""
        context = SelfPromptContext(user_intent=user_intent)
        phase_outputs = {}

        for phase in self.PHASE_ORDER[:7]:  # USER_INTENT through TASKS
            cycle.current_phase = phase
            await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
                "cycle_id": cycle.cycle_id,
                "phase": phase.value,
            })

            start_time = datetime.now(timezone.utc)
            try:
                handler = self._phase_handlers.get(phase)
                if handler:
                    output = await handler(cycle, {"context": context, "previous_outputs": phase_outputs})
                else:
                    output = {"phase": phase.value, "status": "no_handler", "output": {}}

                phase_outputs[phase] = output
                context = self._update_context(context, phase, output)

                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=True,
                    output=output,
                    duration_ms=duration_ms,
                )

                await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "duration_ms": duration_ms,
                })

            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                # Continue with partial context — graceful degradation
                await self._emit_event(f"SELF_LOOP_PHASE_FAILED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "error": str(e),
                })

        return context

    def _update_context(self, context: SelfPromptContext, phase: SelfLoopPhase, output: dict[str, Any]) -> SelfPromptContext:
        """Update context with phase output."""
        updates = {}
        phase_key = phase.value

        # Map phase to context field
        field_map = {
            SelfLoopPhase.USER_INTENT: "user_intent",
            SelfLoopPhase.PLANNING: "planning_outcome",
            SelfLoopPhase.RESEARCH: "research_findings",
            SelfLoopPhase.REQUIREMENTS: "requirements_spec",
            SelfLoopPhase.COUNCILS_REVIEWS: "council_reviews",
            SelfLoopPhase.PLAN: "approved_plan",
            SelfLoopPhase.TASKS: "task_assignments",
            SelfLoopPhase.TEST: "test_outcomes",
            SelfLoopPhase.REVIEW: "review_feedback",
            SelfLoopPhase.VERIFICATION: "verification_status",
            SelfLoopPhase.FINAL_JUDGMENT: "final_judgment",
            SelfLoopPhase.DECISION: "decision_outcome",
            SelfLoopPhase.EVIDENCE: "evidence_collected",
            SelfLoopPhase.LEARNING: "learning_extracted",
            SelfLoopPhase.MEMORY_KNOWLEDGE: "knowledge_updated",
            SelfLoopPhase.PERSISTENCE: "state_persisted",
        }

        if phase_key in field_map:
            updates[field_map[phase_key]] = output.get("output", output)

        # Create new context with updates (immutable pattern)
        return SelfPromptContext(
            user_intent=updates.get("user_intent", context.user_intent),
            planning_outcome=updates.get("planning_outcome", context.planning_outcome),
            research_findings=updates.get("research_findings", context.research_findings),
            requirements_spec=updates.get("requirements_spec", context.requirements_spec),
            council_reviews=updates.get("council_reviews", context.council_reviews),
            approved_plan=updates.get("approved_plan", context.approved_plan),
            task_assignments=updates.get("task_assignments", context.task_assignments),
            prior_execution_results=context.prior_execution_results,
            test_outcomes=updates.get("test_outcomes", context.test_outcomes),
            review_feedback=updates.get("review_feedback", context.review_feedback),
            verification_status=updates.get("verification_status", context.verification_status),
            final_judgment=updates.get("final_judgment", context.final_judgment),
            decision_outcome=updates.get("decision_outcome", context.decision_outcome),
            evidence_collected=updates.get("evidence_collected", context.evidence_collected),
            learning_extracted=updates.get("learning_extracted", context.learning_extracted),
            knowledge_updated=updates.get("knowledge_updated", context.knowledge_updated),
            state_persisted=updates.get("state_persisted", context.state_persisted),
            current_aios_state=context.current_aios_state,
        )

    async def _execute_self_prompt_phase(
        self,
        cycle: SelfLoopCycle,
        context: SelfPromptContext,
    ) -> SelfPrompt:
        """Phase 8: Generate authoritative self-prompt directive."""
        cycle.current_phase = SelfLoopPhase.SELF_PROMPT
        await self._emit_event("SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.SELF_PROMPT.value,
        })

        start_time = datetime.now(timezone.utc)

        # Delegate to SelfPromptGenerator (will be wired in)
        if hasattr(self, "_prompt_generator") and self._prompt_generator:
            self_prompt = await self._prompt_generator.generate(cycle.cycle_id, context)
        else:
            # Fallback: create minimal valid self-prompt
            self_prompt = self._create_fallback_self_prompt(cycle.cycle_id, context)

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.SELF_PROMPT] = PhaseResult(
            phase=SelfLoopPhase.SELF_PROMPT,
            success=self_prompt.is_valid(),
            output=self_prompt.to_dict(),
            duration_ms=duration_ms,
        )

        await self._emit_event("SELF_LOOP_PHASE_COMPLETED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.SELF_PROMPT.value,
            "duration_ms": duration_ms,
            "prompt_valid": self_prompt.is_valid(),
        })

        return self_prompt

    def _create_fallback_self_prompt(self, cycle_id: str, context: SelfPromptContext) -> SelfPrompt:
        """Create a minimal valid self-prompt when generator not available."""
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=[],
            execution_bounds=ExecutionBounds(),
            provenance_chain=[f"cycle_{cycle_id}_fallback"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=["cycle_completion"],
        )
        return SelfPrompt.create_empty(cycle_id).with_directive(directive).with_validation(
            SelfPromptValidationStatus.VALIDATED
        )

    async def _execute_bounded_execution_phase(
        self,
        cycle: SelfLoopCycle,
        self_prompt: SelfPrompt,
    ) -> dict[str, Any]:
        """Phase 9: Execute self-prompt directive within bounds."""
        cycle.current_phase = SelfLoopPhase.BOUNDED_EXECUTION
        await self._emit_event("SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.BOUNDED_EXECUTION.value,
        })

        start_time = datetime.now(timezone.utc)

        if not self_prompt.is_valid() or not self_prompt.directive:
            raise ValueError("Invalid or missing self-prompt directive")

        directive = self_prompt.directive

        # Enforce bounds
        timeout = directive.execution_bounds.timeout_seconds
        max_retries = directive.execution_bounds.max_retries

        # Execute with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # In mock mode, simulate execution
                if self._mock_mode:
                    await asyncio.sleep(0.01)
                    execution_result = {
                        "status": "success",
                        "mock": True,
                        "attempt": attempt + 1,
                        "results": {sys: "mock_result" for sys in directive.target_systems},
                    }
                else:
                    # Real execution would go through CapabilityManager
                    execution_result = await self._execute_real_directive(directive)

                # Validate against success criteria (in mock mode, always pass)
                if self._mock_mode or self._validate_success_criteria(execution_result, directive.success_criteria):
                    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    cycle.phase_results[SelfLoopPhase.BOUNDED_EXECUTION] = PhaseResult(
                        phase=SelfLoopPhase.BOUNDED_EXECUTION,
                        success=True,
                        output=execution_result,
                        duration_ms=duration_ms,
                    )
                    await self._emit_event("SELF_LOOP_PHASE_COMPLETED", {
                        "cycle_id": cycle.cycle_id,
                        "phase": SelfLoopPhase.BOUNDED_EXECUTION.value,
                        "duration_ms": duration_ms,
                    })
                    return execution_result

                last_error = "Success criteria not met"

            except Exception as e:
                last_error = str(e)
                await self._emit_event("BOUNDED_EXECUTION_RETRY", {
                    "cycle_id": cycle.cycle_id,
                    "attempt": attempt + 1,
                    "error": str(e),
                })

        # All retries exhausted
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.BOUNDED_EXECUTION] = PhaseResult(
            phase=SelfLoopPhase.BOUNDED_EXECUTION,
            success=False,
            error=last_error or "Execution failed after retries",
            duration_ms=duration_ms,
        )
        raise RuntimeError(f"Bounded execution failed: {last_error}")

    async def _execute_real_directive(self, directive: SelfPromptDirective) -> dict[str, Any]:
        """Execute directive using real capabilities (CapabilityManager)."""
        # Implementation would route through CapabilityManager
        # For now, return mock result
        return {"status": "delegated_to_capability_manager", "target_systems": directive.target_systems}

    def _validate_success_criteria(self, result: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Validate execution result against success criteria."""
        if not criteria:
            return True
        # Simple validation: check all criteria keys present and truthy
        for key, expected in criteria.items():
            if key not in result:
                return False
            if expected is not None and result[key] != expected:
                return False
        return True

    async def _execute_evaluation_phases(
        self,
        cycle: SelfLoopCycle,
        execution_result: dict[str, Any],
    ) -> None:
        """Execute phases 10-18: Evaluation and learning phases."""
        context_updates = {
            SelfLoopPhase.TEST: {"execution_result": execution_result},
            SelfLoopPhase.REVIEW: {"execution_result": execution_result},
            SelfLoopPhase.VERIFICATION: {"execution_result": execution_result},
            SelfLoopPhase.FINAL_JUDGMENT: {"execution_result": execution_result},
            SelfLoopPhase.DECISION: {"execution_result": execution_result},
            SelfLoopPhase.EVIDENCE: {"execution_result": execution_result},
            SelfLoopPhase.LEARNING: {"execution_result": execution_result},
            SelfLoopPhase.MEMORY_KNOWLEDGE: {"execution_result": execution_result},
            SelfLoopPhase.PERSISTENCE: {"execution_result": execution_result},
        }

        for phase in self.PHASE_ORDER[9:18]:  # TEST through PERSISTENCE
            cycle.current_phase = phase
            await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
                "cycle_id": cycle.cycle_id,
                "phase": phase.value,
            })

            start_time = datetime.now(timezone.utc)
            try:
                handler = self._phase_handlers.get(phase)
                mock_context = context_updates.get(phase, {})
                if handler:
                    output = await handler(cycle, mock_context)
                else:
                    output = {"phase": phase.value, "status": "no_handler", "output": {}}

                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=True,
                    output=output,
                    duration_ms=duration_ms,
                )

                await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "duration_ms": duration_ms,
                })

            except Exception as e:
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                cycle.phase_results[phase] = PhaseResult(
                    phase=phase,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                await self._emit_event(f"SELF_LOOP_PHASE_FAILED", {
                    "cycle_id": cycle.cycle_id,
                    "phase": phase.value,
                    "error": str(e),
                })

    async def _execute_next_self_prompt_phase(self, cycle: SelfLoopCycle) -> None:
        """Phase 19: Prepare for next cycle."""
        cycle.current_phase = SelfLoopPhase.NEXT_SELF_PROMPT
        await self._emit_event(f"SELF_LOOP_PHASE_STARTED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.NEXT_SELF_PROMPT.value,
        })

        start_time = datetime.now(timezone.utc)

        # This phase synthesizes learnings for the next cycle's self-prompt
        handler = self._phase_handlers.get(SelfLoopPhase.NEXT_SELF_PROMPT)
        if handler:
            await handler(cycle, {"cycle_results": {p.value: r.output for p, r in cycle.phase_results.items()}})

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        cycle.phase_results[SelfLoopPhase.NEXT_SELF_PROMPT] = PhaseResult(
            phase=SelfLoopPhase.NEXT_SELF_PROMPT,
            success=True,
            output={"next_cycle_ready": True},
            duration_ms=duration_ms,
        )

        await self._emit_event(f"SELF_LOOP_PHASE_COMPLETED", {
            "cycle_id": cycle.cycle_id,
            "phase": SelfLoopPhase.NEXT_SELF_PROMPT.value,
            "duration_ms": duration_ms,
        })

    async def _attempt_recovery(self, cycle: SelfLoopCycle, error: Exception) -> None:
        """Attempt recovery from cycle failure."""
        cycle.state = SelfLoopState.RECOVERING
        await self._emit_event("RECOVERY_INITIATED", {
            "cycle_id": cycle.cycle_id,
            "error": str(error),
        })

        # Recovery logic: checkpoint, state restore, degraded mode
        if self._state_manager:
            try:
                # Would restore from last checkpoint
                pass
            except Exception:
                pass

        cycle.state = SelfLoopState.DEGRADED

    async def pause(self) -> None:
        """Pause the current cycle."""
        if self._running and not self._paused:
            self._paused = True
            await self._emit_event("SELF_LOOP_PAUSED", {"cycle_id": self._current_cycle.cycle_id if self._current_cycle else None})

    async def resume(self) -> None:
        """Resume a paused cycle."""
        if self._running and self._paused:
            self._paused = False
            await self._emit_event("SELF_LOOP_RESUMED", {"cycle_id": self._current_cycle.cycle_id if self._current_cycle else None})

    async def stop(self) -> None:
        """Stop the self-loop engine."""
        self._running = False
        self._paused = False
        await self._emit_event("SELF_LOOP_STOPPED", {"cycle_count": self._cycle_count})

    async def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit event to canonical EventBus."""
        if self._event_bus:
            try:
                from aios.events.core.event import Event
                from aios.events.core.identity import ComponentIdentity, ComponentType
                from aios.events.core.types import EventType as CoreEventType, SemanticVersion

                identity = ComponentIdentity(
                    component_type=ComponentType.CORE_COMPONENT,
                    component_name="SelfLoopEngine",
                    version=SemanticVersion(1, 0, 0),
                )

                # Map to canonical EventType if exists, otherwise use custom
                try:
                    core_event_type = CoreEventType[event_type]
                except KeyError:
                    # Use a generic type for custom events
                    core_event_type = CoreEventType.SYSTEM_HEALTH_CHECK

                event = Event(
                    eventType=core_event_type,
                    source=identity,
                    correlationId=uuid.uuid4(),
                    payload=payload,
                )
                await self._event_bus.publish(event)
            except Exception:
                # Fail silently — event emission should not break self-loop
                pass

    def get_status(self) -> dict[str, Any]:
        """Get current engine status."""
        return {
            "running": self._running,
            "paused": self._paused,
            "cycle_count": self._cycle_count,
            "current_cycle": self._current_cycle.cycle_id if self._current_cycle else None,
            "current_phase": self._current_cycle.current_phase.value if self._current_cycle and self._current_cycle.current_phase else None,
            "mock_mode": self._mock_mode,
        }