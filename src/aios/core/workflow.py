"""
Workflow Manager for AI-OS Hermes Kernel.

Manages workflow state machines with state transitions, checkpoints, and recovery.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.subscription import HandlerPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.core.state import StateManager, StateScope, get_state_manager
from aios.core.retry import get_retry_manager, RetryPolicy, RetryStrategy

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryAction(str, Enum):
    """Recommended recovery actions."""

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETURN_TO_PLANNING = "return_to_planning"
    RETURN_TO_CODING = "return_to_coding"
    RETURN_TO_REVIEW = "return_to_review"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ROLLBACK = "rollback"
    RESTART_SERVICE = "restart_service"
    SKIP_STEP = "skip_step"


@dataclass
class WorkflowStep:
    """A step in a workflow."""

    step_id: str
    name: str
    service: str
    event_type: str
    payload: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    retry_policy: dict[str, Any] | None = None
    timeout_seconds: int = 300
    required: bool = True


@dataclass
class WorkflowDefinition:
    """Definition of a workflow."""

    workflow_id: str
    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    initial_state: dict[str, Any] = field(default_factory=dict)
    global_retry_policy: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowManager:
    """
    Manages workflow execution with state machine semantics.

    Features:
    - DAG-based workflow execution
    - State transitions with event emission
    - Checkpointing for recovery
    - Retry policies
    - Parallel step execution
    - RecoveryAction routing based on RootCauseAnalysis
    """

    def __init__(self, state_manager: StateManager | None = None):
        """
        Initialize the Workflow Manager.

        Args:
            state_manager: State manager instance (uses global if None)
        """
        self._state_manager = state_manager or get_state_manager()
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._running_workflows: dict[str, dict[str, Any]] = {}
        self._step_handlers: dict[str, Callable] = {}
        self._retry_manager = get_retry_manager()

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="WorkflowManager",
            version=SemanticVersion.parse("0.1.0"),
        )

        # Subscribe to RootCauseAnalyzed events for recovery routing
        self._event_bus.subscribe(
            SubscribeOptions(
                subscriber=self._identity,
                event_types=[EventType.ROOT_CAUSE_ANALYZED],
                handler=self._on_root_cause_analyzed,
                priority=HandlerPriority.NORMAL,
                metadata={"service_name": "workflow_manager"},
            )
        )

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[definition.workflow_id] = definition
        logger.info(f"Registered workflow: {definition.workflow_id} ({definition.name})")

    def register_step_handler(
        self, service: str, handler: Callable[[dict[str, Any]], Any]
    ) -> None:
        """Register a handler for a service's steps."""
        self._step_handlers[service] = handler

    def _extract_execution_id(self, failure_id: str) -> str:
        """Extract execution_id from failure_id format: exec_<id>_<step_id>"""
        if failure_id.startswith("exec_"):
            parts = failure_id.split("_", 2)
            if len(parts) >= 2:
                return f"{parts[0]}_{parts[1]}"
        return failure_id

    def _get_checkpoints(self, execution_id: str) -> list[dict]:
        """Get checkpoints from workflow state."""
        state = self._state_manager.get_state(StateScope.WORKFLOW, execution_id, "workflow")
        if not state:
            return []
        return state.get("checkpoints", [])

    def _add_checkpoint(self, execution_id: str, checkpoint_data: dict) -> None:
        """Add a checkpoint to workflow state."""
        state = self._state_manager.get_state(StateScope.WORKFLOW, execution_id, "workflow")
        if not state:
            return
        checkpoints = state.get("checkpoints", [])
        checkpoints.append(checkpoint_data)
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "checkpoints", checkpoints
        )

    async def start_workflow(
        self,
        workflow_id: str,
        initial_payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """Start a workflow execution."""
        definition = self._workflows.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow {workflow_id} not registered")

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        correlation_id = correlation_id or str(uuid.uuid4())

        # Initialize workflow state
        initial_state = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "status": WorkflowStatus.RUNNING.value,
            "current_step": None,
            "completed_steps": [],
            "failed_steps": [],
            "step_results": {},
            "checkpoints": [],
            "started_at": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            **definition.initial_state,
            **(initial_payload or {}),
        }

        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", initial_state
        )
        self._running_workflows[execution_id] = {
            "definition": definition,
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.utcnow(),
        }

        # Emit events using canonical CoreEvent
        self._emit_event(
            EventType.WORKFLOW_STARTED,
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "name": definition.name,
            },
            correlation_id,
        )

        # Execute workflow
        await self._execute_workflow(execution_id, definition, correlation_id)

        return execution_id

    async def _execute_workflow(
        self,
        execution_id: str,
        definition: WorkflowDefinition,
        correlation_id: str,
    ) -> None:
        """Execute workflow steps."""
        try:
            # Load existing state to resume from completed steps
            state = self._state_manager.get_state(
                StateScope.WORKFLOW, execution_id, "workflow"
            )
            completed = set(state.get("completed_steps", [])) if state else set()
            failed = set(state.get("failed_steps", [])) if state else set()

            step_map = {step.step_id: step for step in definition.steps}


            while True:
                ready_steps = [
                    step
                    for step in definition.steps
                    if step.step_id not in completed
                    and step.step_id not in failed
                    and all(dep in completed for dep in step.depends_on)
                ]

                if not ready_steps:
                    break

                tasks = [
                    self._execute_step(execution_id, step, correlation_id)
                    for step in ready_steps
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for step, result in zip(ready_steps, results):
                    if isinstance(result, Exception):
                        failed.add(step.step_id)
                        if step.required:
                            logger.error(
                                f"Required step {step.step_id} failed, marking workflow failed"
                            )
                            raise result
                    else:
                        completed.add(step.step_id)
                        self._state_manager.set_state(
                            StateScope.WORKFLOW,
                            execution_id,
                            f"step_results.{step.step_id}",
                            result,
                        )

                required_failed = [s for s in failed if step_map[s].required]
                if required_failed:
                    raise Exception(f"Required steps failed: {required_failed}")

                # Persist completed/failed steps to state for recovery
                self._state_manager.set_state(
                    StateScope.WORKFLOW, execution_id, "completed_steps", list(completed)
                )
                self._state_manager.set_state(
                    StateScope.WORKFLOW, execution_id, "failed_steps", list(failed)
                )

            all_completed = all(
                s.step_id in completed or not s.required for s in definition.steps
            )
            if all_completed:
                await self._complete_workflow(execution_id, correlation_id)
            else:
                await self._complete_workflow(execution_id, correlation_id)

        except Exception as e:
            await self._fail_workflow(execution_id, correlation_id, str(e))

    async def _execute_step(
        self,
        execution_id: str,
        step: WorkflowStep,
        correlation_id: str,
    ) -> Any:
        """Execute a single workflow step."""
        logger.info(f"Executing step {step.step_id} ({step.name}) for workflow {execution_id}")

        # Update state
        self._state_manager.update_state(
            StateScope.WORKFLOW,
            execution_id,
            {
                "current_step": step.step_id,
                "status": WorkflowStatus.RUNNING.value,
            },
        )

        # Get handler
        handler = self._step_handlers.get(step.service)
        if not handler:
            raise ValueError(f"No handler registered for service: {step.service}")

        # Prepare payload
        payload = {
            **step.payload,
            "execution_id": execution_id,
            "step_id": step.step_id,
            "correlation_id": correlation_id,
        }

        # Execute with retries using RetryManager
        task_id = f"{execution_id}_{step.step_id}"
        retry_policy = step.retry_policy or {}
        policy = RetryPolicy(
            max_retries=retry_policy.get("max_retries", 3),
            base_delay_ms=retry_policy.get("delay_seconds", 1) * 1000,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=retry_policy.get("jitter", True),
        )

        async def execute_handler() -> Any:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)

        result = await self._retry_manager.execute_with_retry(
            task_id=task_id,
            service=step.service,
            func=execute_handler,
            correlation_id=correlation_id,
            policy=policy,
        )

        # Create checkpoint after successful step completion
        await self._create_checkpoint(execution_id, step.step_id, correlation_id)

        # Update workflow state with completed step
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if state:
            completed = state.get("completed_steps", [])
            if step.step_id not in completed:
                completed.append(step.step_id)
                self._state_manager.set_state(
                    StateScope.WORKFLOW, execution_id, "completed_steps", completed
                )

        logger.info(f"Step {step.step_id} completed successfully")
        return result

    async def _create_checkpoint(
        self,
        execution_id: str,
        step_id: str,
        correlation_id: str,
    ) -> None:
        """Create a checkpoint after step completion for recovery."""
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state:
            return

        checkpoint_id = f"checkpoint_{execution_id}_{step_id}_{uuid.uuid4().hex[:8]}"
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "execution_id": execution_id,
            "workflow_id": state.get("workflow_id"),
            "step_id": step_id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            # Store minimal state for recovery (not full snapshot to avoid recursion)
            "workflow_id": state.get("workflow_id"),
            "initial_state": state.get("initial_state", {}),
        }

        self._add_checkpoint(execution_id, checkpoint_data)

        # Emit checkpoint event using canonical CoreEvent
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            checkpoint_data,
            correlation_id,
        )

        logger.debug(f"Created checkpoint {checkpoint_id} for workflow {execution_id} at step {step_id}")

    async def _on_root_cause_analyzed(self, event) -> None:
        """Handle RootCauseAnalyzed event and route recovery action."""
        payload = event.payload
        failure_id = payload.get("failure_id", "")
        execution_id = self._extract_execution_id(failure_id)

        action_str = payload.get("recommended_action", "escalate_to_human")
        try:
            action = RecoveryAction(action_str)
        except ValueError:
            logger.warning(f"Unknown recovery action: {action_str}, defaulting to ESCALATE_TO_HUMAN")
            action = RecoveryAction.ESCALATE_TO_HUMAN

        logger.info(f"Routing recovery action for workflow {execution_id}: {action.value}")

        if action == RecoveryAction.RETURN_TO_PLANNING:
            await self._route_to_planning(execution_id, payload)
        elif action == RecoveryAction.RETURN_TO_CODING:
            await self._route_to_coding(execution_id, payload)
        elif action == RecoveryAction.RETURN_TO_REVIEW:
            await self._route_to_review(execution_id, payload)
        elif action == RecoveryAction.ESCALATE_TO_HUMAN:
            await self._escalate_to_human(execution_id, payload)
        elif action == RecoveryAction.ROLLBACK:
            await self._rollback(execution_id, payload)
        elif action == RecoveryAction.RESTART_SERVICE:
            await self._restart_service(execution_id, payload)
        elif action == RecoveryAction.RETRY_WITH_BACKOFF:
            await self._retry_with_backoff(execution_id, payload)
        elif action == RecoveryAction.SKIP_STEP:
            await self._skip_step(execution_id, payload)
        else:
            logger.warning(f"Unhandled recovery action: {action.value}")

    async def _route_to_planning(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Route failure back to planning phase."""
        logger.info(f"Routing workflow {execution_id} back to planning")
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            {
                "execution_id": execution_id,
                "recovery_action": "return_to_planning",
                "reason": payload.get("root_cause", "Configuration issue"),
                "responsible_service": "planning",
            },
            execution_id,
        )
        await self._fail_workflow(execution_id, execution_id, "Returned to planning for revision")

    async def _route_to_coding(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Route failure back to coding phase."""
        logger.info(f"Routing workflow {execution_id} back to coding")
        await self._resume_from_latest_checkpoint(execution_id, "coding")

    async def _route_to_review(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Route failure back to review phase."""
        logger.info(f"Routing workflow {execution_id} back to review")
        await self._resume_from_latest_checkpoint(execution_id, "review")

    async def _escalate_to_human(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Escalate to human intervention."""
        logger.warning(f"Escalating workflow {execution_id} to human: {payload.get('root_cause')}")
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            {
                "execution_id": execution_id,
                "recovery_action": "escalate_to_human",
                "reason": payload.get("root_cause", "Unknown failure"),
                "confidence": payload.get("confidence", 0.0),
            },
            execution_id,
        )
        await self._fail_workflow(execution_id, execution_id, f"Escalated to human: {payload.get('root_cause')}")

    async def _rollback(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Rollback to previous version."""
        logger.info(f"Rolling back workflow {execution_id}")
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            {
                "execution_id": execution_id,
                "recovery_action": "rollback",
                "reason": payload.get("root_cause", "Deployment failure"),
            },
            execution_id,
        )
        await self._fail_workflow(execution_id, execution_id, "Rollback initiated")

    async def _restart_service(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Restart the failing service."""
        service = payload.get("responsible_service", "unknown")
        logger.info(f"Restarting service {service} for workflow {execution_id}")
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            {
                "execution_id": execution_id,
                "recovery_action": "restart_service",
                "service": service,
            },
            execution_id,
        )
        await self._resume_from_latest_checkpoint(execution_id, service)

    async def _retry_with_backoff(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Retry the failed step with exponential backoff."""
        logger.info(f"Retrying workflow {execution_id} with backoff")
        await self._resume_from_latest_checkpoint(execution_id, "retry")

    async def _skip_step(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Skip the failed step and continue workflow."""
        logger.info(f"Skipping failed step for workflow {execution_id}")
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if state:
            state["skipped_steps"] = state.get("skipped_steps", [])
            state["skipped_steps"].append(payload.get("failure_id", "unknown"))
            self._state_manager.set_state(
                StateScope.WORKFLOW, execution_id, "workflow", state
            )
        definition = self._running_workflows.get(execution_id, {}).get("definition")
        if definition:
            await self._execute_workflow(execution_id, definition, execution_id)

    async def _resume_from_latest_checkpoint(
        self, execution_id: str, target_service: str
    ) -> None:
        """Resume workflow from the latest checkpoint."""
        checkpoints = self._get_checkpoints(execution_id)
        if not checkpoints:
            logger.warning(f"No checkpoints found for workflow {execution_id}")
            return

        # Get latest checkpoint
        latest_checkpoint = max(
            checkpoints,
            key=lambda c: c.get("timestamp", "")
        )

        logger.info(f"Resuming workflow {execution_id} from checkpoint {latest_checkpoint.get('checkpoint_id')} to {target_service}")

        # Restore workflow state (just status and metadata)
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state:
            return

        state["status"] = WorkflowStatus.RUNNING.value
        state["resumed_at"] = datetime.utcnow().isoformat()
        state["recovery_from"] = target_service

        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", state
        )

        # Get workflow definition and re-execute
        definition = self._running_workflows.get(execution_id, {}).get("definition")
        if definition:
            self._running_workflows[execution_id]["status"] = WorkflowStatus.RUNNING
            await self._execute_workflow(execution_id, definition, execution_id)

    async def _complete_workflow(
        self,
        execution_id: str,
        correlation_id: str,
    ) -> None:
        """Mark workflow as completed."""
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state:
            return

        state["status"] = WorkflowStatus.COMPLETED.value
        state["completed_at"] = datetime.utcnow().isoformat()
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", state
        )

        self._running_workflows.pop(execution_id, None)

        self._emit_event(
            EventType.WORKFLOW_COMPLETED,
            {
                "execution_id": execution_id,
                "workflow_id": state.get("workflow_id"),
            },
            correlation_id,
        )

        logger.info(f"Workflow {execution_id} completed successfully")

    async def _fail_workflow(
        self,
        execution_id: str,
        correlation_id: str,
        error: str,
    ) -> None:
        """Mark workflow as failed."""
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state:
            return

        state["status"] = WorkflowStatus.FAILED.value
        state["error"] = error
        state["failed_at"] = datetime.utcnow().isoformat()
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", state
        )

        self._running_workflows.pop(execution_id, None)

        self._emit_event(
            EventType.WORKFLOW_FAILED,
            {
                "execution_id": execution_id,
                "workflow_id": state.get("workflow_id"),
                "error": error,
            },
            correlation_id,
        )

        logger.error(f"Workflow {execution_id} failed: {error}")

    def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a canonical event via the canonical EventBus."""
        import uuid as uuid_mod

        # Handle invalid UUID strings by generating a new one
        try:
            correlation_uuid = uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4()
        except ValueError:
            logger.warning(f"Invalid UUID string for correlation_id: {correlation_id!r}. Generating a new UUID.")
            correlation_uuid = uuid_mod.uuid4()

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
        )
        result = self._event_bus.publish(event)
        # Fire and forget - result handling is async
        if hasattr(result, "__await__"):
            # Schedule on the event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    async def pause_workflow(
        self, execution_id: str, correlation_id: str | None = None
    ) -> None:
        """Pause a running workflow."""
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state or state.get("status") != WorkflowStatus.RUNNING.value:
            raise ValueError(f"Workflow {execution_id} not running")

        state["status"] = WorkflowStatus.PAUSED.value
        state["paused_at"] = datetime.utcnow().isoformat()
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", state
        )

        correlation_id = correlation_id or state.get("correlation_id", execution_id)

        self._emit_event(
            EventType.WORKFLOW_PAUSED,
            {
                "execution_id": execution_id,
                "workflow_id": state.get("workflow_id"),
            },
            correlation_id,
        )

        logger.info(f"Workflow {execution_id} paused")

    async def resume_workflow(
        self, execution_id: str, correlation_id: str | None = None
    ) -> None:
        """Resume a paused workflow."""
        state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not state or state.get("status") != WorkflowStatus.PAUSED.value:
            raise ValueError(f"Workflow {execution_id} not paused")

        state["status"] = WorkflowStatus.RUNNING.value
        state["resumed_at"] = datetime.utcnow().isoformat()
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", state
        )

        correlation_id = correlation_id or state.get("correlation_id", execution_id)
        definition = self._workflows.get(state.get("workflow_id"))

        self._emit_event(
            EventType.WORKFLOW_RESUMED,
            {
                "execution_id": execution_id,
                "workflow_id": state.get("workflow_id"),
            },
            correlation_id,
        )

        logger.info(f"Workflow {execution_id} resumed")

        if definition:
            await self._execute_workflow(execution_id, definition, correlation_id)

    def get_workflow_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get workflow execution status."""
        return self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )

    def list_workflows(self) -> list[dict[str, Any]]:
        """List registered workflow definitions."""
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "steps": len(w.steps),
            }
            for w in self._workflows.values()
        ]

    def list_running(self) -> list[dict[str, Any]]:
        """List currently running workflows."""
        results = []
        for exec_id in self._running_workflows:
            state = self.get_workflow_status(exec_id)
            if state:
                results.append(state)
        return results


# Global workflow manager instance
_global_workflow_manager: WorkflowManager | None = None


def get_workflow_manager(
    state_manager: StateManager | None = None,
) -> WorkflowManager:
    """Get or create the global workflow manager."""
    global _global_workflow_manager
    if _global_workflow_manager is None:
        _global_workflow_manager = WorkflowManager(state_manager)
    return _global_workflow_manager


def set_workflow_manager(manager: WorkflowManager) -> None:
    """Set the global workflow manager."""
    global _global_workflow_manager
    _global_workflow_manager = manager


def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a canonical event via the canonical EventBus."""
        import uuid as uuid_mod

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4(),
            payload=payload,
        )
        result = self._event_bus.publish(event)
        # Fire and forget - result handling is async
        if hasattr(result, "__await__"):
            # Schedule on the event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass


__all__ = [
    "WorkflowManager",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowStatus",
    "RecoveryAction",
    "get_workflow_manager",
    "set_workflow_manager",
]
