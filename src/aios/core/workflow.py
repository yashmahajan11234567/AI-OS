"""
WorkflowManager — the Phase-4 (Execution) Core Manager for AI-OS Hermes Kernel.

WorkflowManager manages workflow state machines with state transitions,
checkpoints, and recovery. It implements the ICoreManager Protocol
(name / phase / dependencies / initialize / shutdown / health_ready) so
LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 4 (alphabetical within phase:
    CapabilityManager, WorkflowManager — deterministic per Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.workflow``
    (Part 4 §4.9 names the identity ``kernel.workflow``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.workflow``, using the same precedent Task 9–15 established for
    ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health`` /
    ``core.resource`` / ``core.security`` / ``core.capability``)
  * reads ``kernel.workflow.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 15 mapping, same as Tasks 9–14): Part 4 §4.9.11 names events
like ``WorkflowRegisteredEvent`` / ``WorkflowStartedEvent`` /
``WorkflowCompletedEvent`` / ``WorkflowFailedEvent`` / ``WorkflowPausedEvent`` /
``WorkflowResumedEvent`` / ``WorkflowCheckpointEvent`` that do NOT exist in the
closed canonical ``EventType`` enum (Part 2 §2.3.1, Task 2). WorkflowManager does
NOT invent new EventTypes. The canonical mappings for the workflow domain are
(verified against ``src/aios/events/core/types.py``):

  * Workflow started        -> EventType.WORKFLOW_STARTED
  * Workflow completed      -> EventType.WORKFLOW_COMPLETED
  * Workflow failed         -> EventType.WORKFLOW_FAILED
  * Workflow paused         -> EventType.WORKFLOW_PAUSED
  * Workflow resumed        -> EventType.WORKFLOW_RESUMED
  * Checkpoint created      -> EventType.CHECKPOINT_CREATED
  * Workflow step started   -> EventType.WORKFLOW_STEP_STARTED
  * Workflow step completed -> EventType.WORKFLOW_STEP_COMPLETED
  * Workflow step failed    -> EventType.WORKFLOW_STEP_FAILED

If a conceptual workflow event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

PHASE DEPENDENCY RULE: WorkflowManager is Phase 4. It declares ONLY Phase-1
LifecycleManager as a formal dependency:

    dependencies = ["LifecycleManager"]

It does NOT declare CapabilityManager, SecurityManager, StateManager, or any other
manager as a formal dependency. The StateManager is a cross-phase dependency
(Phase 2 — below Phase 4) but is an *operational* relationship (workflow state
storage), not a lifecycle dependency edge — it is available by the time Phase 4
initializes (deterministic phase ordering guarantees Phase 2 before Phase 4).
C1–C4 are always-satisfied base dependencies handled by LifecycleManager.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

# Core Components (Tasks 1–8) — consumed, never re-implemented.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.subscription import HandlerPriority
from aios.events.core.types import EventType, SemanticVersion

# C2/C3 are injected; C1 (EventBus) is resolved eagerly from the canonical
# singleton so both the constructor contract (raise if the bus is not up) and the
# sync ``_emit_event`` bridge keep working. StateManager is an optional
# backward-compatible constructor arg (pre-Phase-4 public contract).
from aios.core.state import StateManager, StateScope, get_state_manager
from aios.core.retry import get_retry_manager, RetryPolicy, RetryStrategy
from aios.core.root_cause import RecoveryAction

__all__ = [
    "WorkflowManager",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowStatus",
    "RecoveryAction",
    "get_workflow_manager",
    "set_workflow_manager",
    "reset_workflow_manager_singleton",
]


# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "WorkflowManager"
# Part 4 §4.9 names WorkflowManager's ServiceRegistry identity as
# ``kernel.workflow``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
# as ``core.lifecycle``) and Tasks 10–15 resolved for StateManager, StorageManager,
# HealthManager, ResourceManager, SecurityManager, and CapabilityManager. We follow
# that precedent: the compliant, INV-SR-NS-002-respecting ServiceRegistry id is
# ``core.workflow``. The configuration namespace read from C3 remains
# ``kernel.workflow.*`` (Part 4 §4.9 config schema), which is independent of the
# ServiceRegistry id.
_MANAGER_ID = "core.workflow"
_PHASE = 4  # Phase 4 — "Execution"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 16 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–15):
#   * same-phase siblings (CapabilityManager) and cross-phase managers (e.g.
#     SecurityManager, StateManager) are NOT declared as dependencies — they
#     would be rejected by LifecycleManager's dependency validator (LM-DEP-003)
#     and could break kernel boot ordering. Deterministic alphabetical ordering
#     (Phase 4: CapabilityManager, WorkflowManager) already guarantees correct
#     sequencing, and the operational relationships (state storage, retry
#     budgets) are resolved from canonical singletons at call time, not lifecycle
#     dependency edges.
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)


# ---------------------------------------------------------------------------
# Enumerations / dataclasses / value objects (preserved from original)
# ---------------------------------------------------------------------------


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# RecoveryAction is imported from aios.core.root_cause (canonical definition)


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


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class WorkflowManagerError(Exception):
    """WorkflowManager failure (Part 4 §4.9.12).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``CapabilityManagerError`` /
    ``StateManagerError`` / ``StorageManagerError`` / ``HealthManagerError`` /
    ``ResourceManagerError`` / ``SecurityManagerError`` (Tasks 10–14).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}:"
                f" {self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# WorkflowManager
# ---------------------------------------------------------------------------


class WorkflowManager:
    """Phase-4 (Execution) workflow execution manager for the Hermes Kernel.

    Provides the kernel workflow-management surface:
    - DAG-based workflow execution with state machine semantics
    - State transitions with canonical event emission
    - Checkpointing for recovery
    - Retry policies (via canonical RetryManager)
    - Parallel step execution
    - RecoveryAction routing based on RootCauseAnalysis

    Architecture contract (mirrors StateManager / StorageManager /
    HealthManager / ResourceManager / SecurityManager / CapabilityManager):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel).
    """

    def __init__(
        self,
        state_manager: StateManager | None = None,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the Workflow Manager.

        Backward compatible: the ``state_manager`` positional/None argument is
        preserved from the pre-Phase-4 constructor. The C2/C3/C4 dependencies are
        optional keyword-only injection points; they are resolved at
        ``initialize()`` time (C3 is frozen before LifecycleManager Phase 4 runs,
        so ``initialize()`` reads the frozen configuration).

        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.

        Args:
            state_manager: State manager instance (uses global if None)
        """
        # StateManager — backward-compatible positional arg (pre-Phase-4).
        self._state_manager = state_manager or get_state_manager()

        # C2/C3/C4 — injected via DI (Task 16).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.9).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 16).
        self._initialized = False
        self._registered_with_sr = False

        # Canonical RetryManager (resolved from global singleton; operational
        # dependency, not a lifecycle dependency edge).
        self._retry_manager = get_retry_manager()

        # Workflow runtime state.
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._running_workflows: dict[str, dict[str, Any]] = {}
        self._step_handlers: dict[str, Callable] = {}

        # Subscribe to RootCauseAnalyzed events for recovery routing.
        self._event_bus.subscribe(
            SubscribeOptions(
                subscriber=self._identity,
                event_types=[EventType.ROOT_CAUSE_ANALYZED],
                handler=self._on_root_cause_analyzed,
                priority=HandlerPriority.NORMAL,
                metadata={"service_name": "workflow_manager"},
            )
        )

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 16 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 4 — Execution, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.workflow``; Part 4 §4.9 names
        ``kernel.workflow`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors the sibling Core Managers' health_ready: ready by construction
        once the manager has completed its own initialization. Returns False
        before ``initialize()`` and after ``shutdown()``.
        """
        return self._initialized and self._event_bus is not None

    # ------------------------------------------------------------------
    # ICoreManager: initialization / shutdown
    # ------------------------------------------------------------------

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 4 initialization (called by LifecycleManager).

        Follows the Core Manager pattern: reads ``kernel.workflow.*``
        configuration from the frozen C3, registers this manager with the
        canonical ServiceRegistry (C2) as ``core.workflow``, and marks the
        manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        # (WorkflowManager currently has no configuration overrides; placeholder
        # for future ``kernel.workflow.*`` keys.)

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.workflow``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"WorkflowManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 4 (reverse) shutdown (called by LifecycleManager).

        Clears the workflow runtime state, marks ``core.workflow`` SHUTDOWN in
        the canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear workflow runtime state.
        self._running_workflows.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("WorkflowManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror sibling Core Manager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register WorkflowManager with the ServiceRegistry (C2, Part 4 §4.9).

        Registered as ``core.workflow`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering WorkflowManager.")
            return
        try:
            await sr.register(
                self,
                service_id=_MANAGER_ID,
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "kind": "core_manager",
                    "manager": _NAME,
                    "phase": _PHASE,
                    "lifecycle_state": "INITIALIZED",
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.workflow`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(
                f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}"
            )

    # ------------------------------------------------------------------
    # Business API — workflow registration
    # ------------------------------------------------------------------

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[definition.workflow_id] = definition
        self._log_info(f"Registered workflow: {definition.workflow_id} ({definition.name})")

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

        # Emit events using canonical EventType (CONFLICT E.1)
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
                            self._log_error(
                                f"Required step {step.step_id} failed, marking workflow failed"
                            )
                            raise result
                    else:
                        completed.add(step.step_id)
                        # Store result both as individual key and merge into workflow state
                        self._state_manager.set_state(
                            StateScope.WORKFLOW,
                            execution_id,
                            f"step_results.{step.step_id}",
                            result,
                        )
                        # Update the main workflow state with step_results
                        state = self._state_manager.get_state(
                            StateScope.WORKFLOW, execution_id, "workflow"
                        )
                        if state:
                            step_results = state.get("step_results", {})
                            step_results[step.step_id] = result
                            self._state_manager.set_state(
                                StateScope.WORKFLOW, execution_id, "step_results", step_results
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
        self._log_info(
            f"Executing step {step.step_id} ({step.name}) for workflow {execution_id}"
        )

        # Emit step-started event (CONFLICT E.1 mapping)
        self._emit_event(
            EventType.WORKFLOW_STEP_STARTED,
            {
                "execution_id": execution_id,
                "step_id": step.step_id,
                "name": step.name,
                "service": step.service,
            },
            correlation_id,
        )

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

        # Emit step-completed event (CONFLICT E.1 mapping)
        self._emit_event(
            EventType.WORKFLOW_STEP_COMPLETED,
            {
                "execution_id": execution_id,
                "step_id": step.step_id,
                "name": step.name,
            },
            correlation_id,
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

        self._log_info(f"Step {step.step_id} completed successfully")
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
            # Store minimal state for recovery (not full snapshot to avoid recursion)
            "initial_state": state.get("initial_state", {}),
        }

        self._add_checkpoint(execution_id, checkpoint_data)

        # Emit checkpoint event using canonical EventType (CONFLICT E.1 mapping)
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            checkpoint_data,
            correlation_id,
        )

        self._log_debug(
            f"Created checkpoint {checkpoint_id} for workflow {execution_id} at step {step_id}"
        )

    async def _on_root_cause_analyzed(self, event) -> None:
        """Handle RootCauseAnalyzed event and route recovery action."""
        payload = event.payload
        failure_id = payload.get("failure_id", "")
        execution_id = self._extract_execution_id(failure_id)

        action_str = payload.get("recommended_action", "escalate_to_human")
        try:
            action = RecoveryAction(action_str)
        except ValueError:
            self._log_warning(
                f"Unknown recovery action: {action_str}, defaulting to ESCALATE_TO_HUMAN"
            )
            action = RecoveryAction.ESCALATE_TO_HUMAN

        self._log_info(
            f"Routing recovery action for workflow {execution_id}: {action.value}"
        )

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
            self._log_warning(f"Unhandled recovery action: {action.value}")

    async def _route_to_planning(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Route failure back to planning phase."""
        self._log_info(f"Routing workflow {execution_id} back to planning")
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
        self._log_info(f"Routing workflow {execution_id} back to coding")
        await self._resume_from_latest_checkpoint(execution_id, "coding")

    async def _route_to_review(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Route failure back to review phase."""
        self._log_info(f"Routing workflow {execution_id} back to review")
        await self._resume_from_latest_checkpoint(execution_id, "review")

    async def _escalate_to_human(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Escalate to human intervention."""
        self._log_warning(
            f"Escalating workflow {execution_id} to human: {payload.get('root_cause')}"
        )
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
        await self._fail_workflow(
            execution_id, execution_id, f"Escalated to human: {payload.get('root_cause')}"
        )

    async def _rollback(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Rollback to previous version."""
        self._log_info(f"Rolling back workflow {execution_id}")
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
        self._log_info(f"Restarting service {service} for workflow {execution_id}")
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
        self._log_info(f"Retrying workflow {execution_id} with backoff")
        await self._resume_from_latest_checkpoint(execution_id, "retry")

    async def _skip_step(
        self, execution_id: str, payload: dict[str, Any]
    ) -> None:
        """Skip the failed step and continue workflow."""
        self._log_info(f"Skipping failed step for workflow {execution_id}")
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
            self._log_warning(f"No checkpoints found for workflow {execution_id}")
            return

        # Get latest checkpoint
        latest_checkpoint = max(
            checkpoints,
            key=lambda c: c.get("timestamp", "")
        )

        self._log_info(
            f"Resuming workflow {execution_id} from checkpoint "
            f"{latest_checkpoint.get('checkpoint_id')} to {target_service}"
        )

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

        self._log_info(f"Workflow {execution_id} completed successfully")

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

        self._log_error(f"Workflow {execution_id} failed: {error}")

    def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a canonical workflow event via the canonical EventBus.

        The canonical ``EventBus.publish`` is async (returns a coroutine). From a
        synchronous business-API call site we cannot ``await`` it, so this method
        bridges to the async bus deterministically using the architecture-approved
        sync-to-async bridge (FIX-FIND-01) established by the sibling Core
        Managers:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion).
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note — avoiding the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaving a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.9.11 names
        like ``WorkflowStartedEvent`` / ``WorkflowCheckpointEvent`` have no
        canonical equivalent). Workflow-specific conceptual events map to
        canonical WORKFLOW_* / CHECKPOINT_CREATED types; unmapped concepts are
        omitted, not invented.

        Preserves the ``correlation_id`` argument for traceability (WorkflowManager
        emits correlationId-based payloads, unlike sibling managers that use
        ``uuid.uuid4()``), validating/inverting as needed.
        """
        bus = self._event_bus
        if bus is None:
            return

        # Preserve correlation_id-based payloads (WorkflowManager business logic).
        try:
            correlation_uuid = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        except ValueError:
            self._log_warning(
                f"Invalid UUID string for correlation_id: {correlation_id!r}. "
                f"Generating a new UUID."
            )
            correlation_uuid = uuid.uuid4()

        full_payload = {
            "manager": _NAME,
            "manager_id": _MANAGER_ID,
            **payload,
        }

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=full_payload,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def wait_for_pending_events(self, timeout: float = 5.0) -> None:
        """Wait for all pending event publish tasks to complete.

        This is useful in tests to ensure all events have been published
        before checking for them.
        """
        if self._pending_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._pending_tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self._log_warning(f"Timeout waiting for {len(self._pending_tasks)} pending event tasks")

    # ------------------------------------------------------------------
    # Business API — workflow lifecycle
    # ------------------------------------------------------------------

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

        self._log_info(f"Workflow {execution_id} paused")

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

        self._log_info(f"Workflow {execution_id} resumed")

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

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 16 — replaces stdlib logging)
    # ------------------------------------------------------------------

    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME, **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME, **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME, **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME, **fields)


# ---------------------------------------------------------------------------
# Global WorkflowManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_workflow_manager: WorkflowManager | None = None
_workflow_singleton_lock = threading.Lock()


def get_workflow_manager(
    state_manager: StateManager | None = None,
) -> WorkflowManager:
    """Get or create the global WorkflowManager singleton.

    Uses the same lock-guarded pattern as the other Core Managers (Tasks 9–15)
    and the C1–C4 singletons, so concurrent callers cannot double-construct.

    Args:
        state_manager: State manager instance (uses global if None). Retained
            for backward compatibility; ignored on cache hits.
    """
    global _global_workflow_manager
    with _workflow_singleton_lock:
        if _global_workflow_manager is None:
            _global_workflow_manager = WorkflowManager(state_manager)
        return _global_workflow_manager


def set_workflow_manager(manager: WorkflowManager) -> None:
    """Set the global WorkflowManager singleton."""
    global _global_workflow_manager
    with _workflow_singleton_lock:
        _global_workflow_manager = manager


def reset_workflow_manager_singleton() -> None:
    """Reset the process-wide WorkflowManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` / ``reset_state_manager_singleton``
    / ``reset_storage_manager_singleton`` / ``reset_health_manager_singleton`` /
    ``reset_resource_manager_singleton`` / ``reset_security_manager_singleton`` /
    ``reset_capability_manager_singleton`` / ``reset_observability_manager_singleton``.
    """
    global _global_workflow_manager
    with _workflow_singleton_lock:
        _global_workflow_manager = None
