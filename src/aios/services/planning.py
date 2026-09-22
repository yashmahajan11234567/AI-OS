"""Planning Service.

Engineering Service responsible for task decomposition, scheduling, and
resource allocation. Consumes PlanningRequested / PlanRejected events and
emits PlanningCompleted / PlanningFailed. Planning never calls other services
directly; it relies on the Memory service (via events) and kernel managers.

B1-R1 remediation (2026-09-22): PlanningService now routes deterministic plans
through the existing LLMCouncil for multi-perspective advisory review before
emitting PlanningCompleted. Council results are advisory-only per ADR #10 and
authority boundary requirements.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4, UUID

from aios.events.base import Event
from aios.events.types import (
    PlanningCompleted,
    PlanningFailed,
    PlanningRequested,
    PlanRejected,
    TaskCreated,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.priority import EventPriority
from aios.services.base import BaseService
from aios.core.llm_council import LLMCouncil, LLMRole

logger = logging.getLogger(__name__)


class PlanningService(BaseService):
    """Decompose a task into a plan (ordered steps + resources)."""

    name = "planning"
    version = "1.0.0"
    description = "Task decomposition, scheduling, resource allocation"
    depends_on: list[str] = ["memory"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._llm_council = None  # Defer initialization until needed

    @property
    def llm_council(self) -> LLMCouncil:
        """Get the LLMCouncil instance, initializing on first access."""
        if self._llm_council is None:
            self._llm_council = LLMCouncil()
        return self._llm_council

    async def on_start(self) -> None:
        logger.info(f"PlanningService.on_start called")
        self.subscribe(self.handle_planning_requested, PlanningRequested)
        self.subscribe(self.handle_plan_rejected, PlanRejected)
        logger.info(f"PlanningService.on_start completed")

    # ----- event handlers -------------------------------------------
    async def handle_planning_requested(self, event: CoreEvent) -> None:
        """Handle PlanningRequested event and emit PlanningCompleted."""
        logger.info(f"PlanningService received event: {event.eventType}, correlationId: {event.correlationId}")
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)

        # Extract information from the planning request
        planning_id = payload.get("planning_id", "")
        objective = payload.get("objective", "")
        constraints = payload.get("constraints", [])
        context = payload.get("context", {})

        # Extract self-prompt and other B1-specific information from context
        self_prompt = context.get("self_prompt", {})
        project_id = context.get("project_id", "")
        correlation_id_from_context = context.get("correlation_id", "")
        lifecycle_context = {
            "user_intent": context.get("user_intent", {}),
            "planning_outcome": context.get("planning_outcome", {}),
            "research_findings": context.get("research_findings", {}),
            "requirements_spec": context.get("requirements_spec", {}),
            "approved_plan": context.get("approved_plan", {}),
            "task_assignments": context.get("task_assignments", {}),
        }

        # Enhance the planning request with B1-specific information
        enhanced_payload = {
            **payload,
            "planning_id": planning_id,
            "objective": objective,
            "constraints": constraints,
            "context": {
                **context,
                "b1_planning_metadata": {
                    "self_prompt": self_prompt,
                    "project_id": project_id,
                    "correlation_id": correlation_id_from_context or event.correlationId,
                    "lifecycle_context": lifecycle_context,
                    "provenance": "B1_T1_Governed_Intelligent_Planning_Pipeline",
                    "advisory_status": True  # SelfPromptGenerator output is advisory per audit
                }
            }
        }

        # Generate deterministic plan (B1-T1 requirement: preserve deterministic planner)
        plan = self.plan(enhanced_payload)

        if plan is None:
            await self.emit_core_event(
                EventType.PLANNING_FAILED,
                {
                    "planning_id": planning_id,
                    "reason": "planning produced no steps",
                },
                correlation_id=correlation_id,
                causation_id=correlation_id,
            )
            return

        # B1-R1: Route deterministic plan through LLMCouncil for advisory review
        # Council results are advisory-only per ADR #10 - never override deterministic planning
        council_advisory = None
        try:
            # Get LLMCouncil instance (may fail if kernel not fully initialized)
            llm_council = self.llm_council

            # Prepare plan summary for council review with B2 context
            context_summary = ""
            if context:
                # Extract B2 context information for council review
                project_info = context.get("project_id", "unknown")
                obsidian_info = f"{len(context.get('obsidian_context', {}).get('data', {}).get('notes', []))} notes" if context.get('obsidian_context') else "0 notes"
                graphify_info = f"{len(context.get('graphify_context', {}).get('data', {}).get('nodes', []))} nodes" if context.get('graphify_context') else "0 nodes"
                claude_mem_info = f"{len(context.get('claude_mem_context', {}).get('data', {}).get('memories', []))} memories" if context.get('claude_mem_context') else "0 memories"
                git_info = "available" if context.get('git_context', {}).get('data') else "unavailable"
                history_info = "available" if context.get('history_context', {}).get('data') else "unavailable"

                context_summary = f"\nB2 Context: Project={project_info}, Obsidian={obsidian_info}, Graphify={graphify_info}, Claude-Mem={claude_mem_info}, Git={git_info}, History={history_info}"

            plan_summary = f"Objective: {objective}\nPlan: {plan.get('steps', [])}\nConstraints: {constraints}{context_summary}"

            # Convene council session and get independent proposals from all six roles
            council_session, proposals = await llm_council.deliberate_and_propose(
                topic=f"Review deterministic plan for: {objective}",
                proposal_title=f"Deterministic Plan Review: {planning_id}",
                proposal_description=plan_summary,
                objective_id=planning_id or str(uuid4()),
                options=[  # Simple approve/reject options for advisory review
                    {"id": "approve", "description": "Approve the deterministic plan as advisory guidance"},
                    {"id": "reject", "description": "Reject the deterministic plan"},
                    {"id": "conditional", "description": "Approve with conditions/advisory notes"}
                ],
                roles=list(LLMRole),  # All six cognitive roles
                builder_excluded=True  # INV-009: builder cannot self-approve
            )

            # Extract advisory feedback from council proposals
            advisory_notes = []
            for proposal in proposals:
                if hasattr(proposal, 'options') and proposal.options:
                    # Extract the selected option/advice from each role
                    selected_option = getattr(proposal, 'selected_option', None) or \
                                    getattr(proposal, 'option_id', None) or \
                                    (proposal.options[0] if proposal.options else None)
                    if selected_option:
                        advisory_notes.append(f"{proposal.metadata.get('llm_role', 'unknown')}: {selected_option}")

            council_advisory = {
                "council_session_id": getattr(council_session, 'council_id', None),
                "council_role_feedback": advisory_notes,
                "council_metadata": {
                    "provenance": "LLMCouncil",
                    "advisory_status": True,  # Explicitly mark as advisory per ADR #10
                    "authority": "advisory_only",  # Never overrides deterministic planner
                    "roles_consulted": [role.value for role in LLMRole],
                    "builder_excluded": True
                }
            }

        except Exception as exc:
            # B1-R1 requirement: Handle LLMCouncil failures without fabricating successful review
            # Log failure but continue with deterministic plan (advisory context is optional)
            logger.warning(f"LLMCouncil advisory review failed (continuing with deterministic plan only): {exc}")
            council_advisory = {
                "error": str(exc),
                "council_metadata": {
                    "provenance": "LLMCouncil",
                    "advisory_status": True,
                    "authority": "advisory_only",
                    "review_failed": True
                }
            }

        correlation_id = event.correlationId

        if plan is None:
            await self.emit_core_event(
                EventType.PLANNING_FAILED,
                {
                    "planning_id": planning_id,
                    "reason": "planning produced no steps",
                },
                correlation_id=correlation_id,
                causation_id=correlation_id,
            )
            return

        # Prepare the planning completed event with preserved information
        planning_completed_payload = {
            "planning_id": planning_id,
            "plan": {
                "plan_id": plan["plan_id"],
                "task_id": plan["task_id"],
                "goal": plan["goal"],
                "steps": plan["steps"],
                "resources": plan["resources"],
                "advisory_context": plan.get("advisory_context", {}),
                # B1-specific preserved information
                "b1_planning_metadata": {
                    "self_prompt": self_prompt,
                    "project_id": project_id,
                    "original_objective": objective,
                    "correlation_id": correlation_id_from_context or event.correlationId,
                    "lifecycle_context": lifecycle_context,
                    "provenance": "B1_T1_Governed_Intelligent_Planning_Pipeline",
                    "advisory_status": True
                }
            },
            "tasks": [],  # Will be populated by downstream services
            "estimated_duration": 0,  # Will be calculated by downstream services
            # B1-R1: Attach LLMCouncil advisory results (advisory-only, never overrides plan)
            "llm_council_advisory": council_advisory,
            # Preserve the original planning context for transparency
            "original_request": {
                "planning_id": planning_id,
                "objective": objective,
                "constraints": constraints,
                "context": context
            }
        }

        await self.emit_core_event(
            EventType.PLANNING_COMPLETED,
            planning_completed_payload,
            correlation_id=correlation_id,
            causation_id=correlation_id,
        )

    async def handle_plan_rejected(self, event: CoreEvent) -> None:
        """Handle PlanRejected event and re-plan with feedback."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        correlation_id = event.correlationId

        await self.emit_core_event(
            EventType.PLANNING_REQUESTED,
            {
                "task_id": payload.get("task_id", ""),
                "reason": "plan rejected",
                "feedback": payload.get("feedback", {}),
                "previous_plan": payload.get("plan_id", ""),
            },
            correlation_id=correlation_id,
            causation_id=correlation_id,
        )

    async def emit_core_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> int:
        """Emit a canonical CoreEvent."""
        if correlation_id is None:
            correlation_id = uuid4()
        if causation_id is None:
            causation_id = correlation_id

        logger.info(f"PlanningService emitting event: {event_type}, correlation_id: {correlation_id}, payload: {payload}")
        core_event = CoreEvent(
            eventType=event_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=causation_id,
            payload=EventPayload(payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(event_type),
        )
        logger.info(f"PlanningService created event: eventId={core_event.eventId}, checksum={core_event.checksum}")
        result = await self.emit(core_event)
        logger.info(f"PlanningService emit result: {result}")
        return result

    # ----- API ------------------------------------------------------
    def plan(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Produce a simple, deterministic plan from a request.

        This is a deterministic planner suitable for tests and demos; it
        emits the canonical SDLC sequence so the Workflow Manager can drive
        the pipeline through events.

        M9-N3 (spec §11.3): relevant learnings are attached as
        ``advisory_context`` — advisory input only. They NEVER override
        Council/Judge authority or alter plan semantics; when no learning
        service is bound (minimal kernels) planning proceeds unchanged.
        """
        task_id = request.get("task_id", f"task_{uuid4().hex[:8]}")
        goal = request.get("goal") or request.get("description") or "undefined"
        steps = request.get("steps") or ["coding", "review", "testing", "deployment"]
        return {
            "plan_id": f"plan_{uuid4().hex[:8]}",
            "task_id": task_id,
            "goal": goal,
            "steps": list(steps),
            "resources": request.get("resources", {}),
            "advisory_context": self._collect_advisory_context(goal),
        }

    def _collect_advisory_context(self, objective: str) -> dict[str, Any]:
        """Gather advisory learnings for an objective (M9-N3).

        Guarded: the global LearningService may be absent in minimal kernels,
        and any retrieval failure must never block planning. The result is a
        plain payload field — consumers treat it as advisory context, not as
        instructions or verdicts (M9 §16 authority boundaries).

        M9-N5 validation/promotion: PlanningService PREFERS validated/promoted
        learnings (``get_validated_lessons``) so only reviewed intelligence
        enters advisory context. If no validated learnings exist, it falls back
        to ``query_relevant`` over ALL captured learnings so an empty store
        never starves planning — but the advisory flag is preserved either way.
        """
        try:
            from aios.services.learning import get_learning_service

            service = get_learning_service()
        except RuntimeError:
            return {}
        try:
            learnings = service.get_validated_lessons(limit=5)
            if not learnings:
                # No validated learnings yet — fall back to keyword-relevant
                # captured learnings so advisory context is still populated.
                learnings = service.query_relevant(objective, limit=5)
        except Exception as exc:  # noqa: BLE001 — advisory must not block planning
            logger.warning("Advisory learning retrieval failed (ignored): %s", exc)
            return {}
        # Advisory-only markers (spec §16): this data informs but never decides.
        for learning in learnings:
            learning.setdefault("advisory", True)
            learning.setdefault("authority", "advisory_only")
            learning.setdefault("trust_level", "untrusted")
        return {
            "learnings": learnings,
            "source": "learning_service",
            "advisory": True,
        }


__all__ = ["PlanningService"]