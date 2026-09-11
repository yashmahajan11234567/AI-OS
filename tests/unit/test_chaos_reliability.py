"""
M12-T6 — Chaos/reliability testing for Section 37.5 #22.

Implements chaos engineering principles to verify system reliability under
controlled fault injection. Every test injects a failure through a REAL
AI-OS execution path and asserts the system's ACTUAL designed response to
that failure (propagation, rollback, partial-start tolerance, failure-state
recording, or aggregate health degradation) — never merely that an
exception "can be raised".

Test map (against the inspected implementations):

1. test_kernel_configuration_manager_failure_aborts_boot_before_phase3
   — Fault: ConfigurationManager.initialize() fails inside the real
     HermesKernel._init_core_components() path (C3, kernel.py ~1174).
   — Kernel contract verified: boot ABORTS loudly (fail-fast); the failed
     C3 is left in its own terminal state (ConfigState) and the Phase-2->3
     freeze boundary is NEVER reached (no ConfigState.FROZEN, no C4 logger
     constructed, no Core Manager constructed).

2. test_kernel_service_registry_failure_aborts_boot
   — Fault: ServiceRegistry (C2) acquisition fails at the kernel's actual
     C2 acquisition point (get_core_service_registry, kernel.py ~1166)
     inside the real _init_core_components() path.
   — Finding from kernel.py: the boot path never calls
     ServiceRegistry.initialize() — C2 is obtained via the singleton
     getter and used lazily (register() only rejects SHUTDOWN state).
     The genuine C2 boot failure therefore occurs at its acquisition
     point, which is where the fault is injected.
   — Kernel contract verified: boot aborts before C3 exists; the kernel
     does NOT silently proceed with a dead registry (no half-initialized
     C3/C4/Managers).

3. test_lifecycle_manager_handles_core_manager_failure
   — RETAINED (Terminal 3 marked it genuine). Real phase loop -> injected
     Core Manager initialize failure -> rollback coordination ->
     LifecycleManagerError carrying the original fault. Strengthened only
     to assert the actual post-rollback lifecycle state (UNINITIALIZED)
     and the carried original_error context.

4. test_workflow_step_failure_marks_execution_failed
   — Fault: step handler raises during REAL WorkflowManager execution.
   — Contract verified against workflow.py's actual state model: the
     required step exhausts its RetryPolicy, the execution state is marked
     WorkflowStatus.FAILED with the error recorded, completed steps are
     retained, and the failed execution is no longer listed as running.

5. test_kernel_continues_after_non_critical_service_start_failure
   — Fault: an Engineering Service's start() raises inside the kernel's
     REAL _start_services() loop (kernel.py ~2974-3047, R-8 partial-start
     tolerance).
   — Contract verified: kernel start() completes; the failing service is
     recorded as started=False/healthy=False with last_error; core
     components keep running and core kernel operations still work.

6. test_health_manager_unhealthy_result_degrades_aggregate_status
   — Fault: component reports HealthStatus.UNHEALTHY through the real
     HealthManager.record_health() path.
   — Contract verified: worst-wins aggregation (UNHEALTHY > DEGRADED >
     HEALTHY > UNKNOWN) — overall_status flips to UNHEALTHY, the
     component snapshot reports it, and get_all_health() counts it.

All tests are deterministic, offline, and safe to run repeatedly.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    LifecycleManager,
    LifecycleState,
    LifecycleManagerError,
)
from aios.core.workflow import (
    WorkflowManager,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
)
from aios.core.health_manager import HealthManager, HealthStatus
from aios.core.state import StateManager, StateScope
from aios.events.core.bus import (
    EventBus,
    reset_core_event_bus_singleton,
    set_core_event_bus,
)
from aios.core.service_registry import (
    ServiceRegistry,
    set_service_registry,
    reset_service_registry_singleton,
)
from aios.core.configuration_manager import (
    ConfigurationManager,
    set_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios.core.structured_logger import (
    StructuredLogger,
    set_logger,
    reset_structured_logger_singleton,
)
from aios.core.state import reset_state_manager_singleton, set_state_manager
from aios.core.workflow import (
    reset_workflow_manager_singleton,
    set_workflow_manager,
)
from aios.events.core.types import EventType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_all_singletons() -> None:
    """Reset every canonical singleton this suite touches (before AND after)."""
    reset_core_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_structured_logger_singleton()
    reset_state_manager_singleton()
    reset_workflow_manager_singleton()


class FailingStateManager:
    """A Core Manager test double whose initialize() raises (Test 3).

    Implements the minimal ICoreManager surface LifecycleManager actually
    uses (name/phase/dependencies/initialize/shutdown/health_ready) with the
    name 'StateManager' so it is accepted by the declared phase topology
    (LM-REG-001 rejects unknown manager names).
    """

    def __init__(self, fail_during_init: bool = True):
        self.fail_during_init = fail_during_init
        self.initialize_called = False
        self.shutdown_called = False
        self.persistence_path: Path | None = None
        self.service_registry = None
        self.configuration_manager = None
        self.logger = None

        # Required for ICoreManager interface
        self._name = "StateManager"
        self._phase = 2
        self._dependencies = ["LifecycleManager"]

    @property
    def name(self) -> str:
        return self._name

    @property
    def phase(self) -> int:
        return self._phase

    @property
    def dependencies(self) -> list[str]:
        return self._dependencies

    async def initialize(self):
        self.initialize_called = True
        if self.fail_during_init:
            raise RuntimeError("Simulated state manager initialization failure")

    async def shutdown(self):
        self.shutdown_called = True

    def health_ready(self) -> bool:
        return not self.fail_during_init or not self.initialize_called


async def _build_real_core_components(temp_dir: Path):
    """Build the real C1-C4 stack + StateManager the way the kernel does.

    Used by the workflow/lifecycle tests that need a functioning substrate
    beneath the component under fault-injection.
    """
    event_bus = EventBus()
    await event_bus.initialize()
    set_core_event_bus(event_bus)

    service_registry = ServiceRegistry(event_bus=event_bus)
    await service_registry.initialize()
    set_service_registry(service_registry)

    configuration_manager = ConfigurationManager(event_bus=event_bus)
    await configuration_manager.initialize()
    configuration_manager.freeze()
    set_configuration_manager(configuration_manager)

    structured_logger = StructuredLogger()
    await structured_logger.initialize(None)
    set_logger(structured_logger)

    state_manager = StateManager(
        persistence_path=temp_dir / "state",
        service_registry=service_registry,
        configuration_manager=configuration_manager,
        logger=structured_logger,
    )
    await state_manager.initialize()
    set_state_manager(state_manager)

    return {
        "event_bus": event_bus,
        "service_registry": service_registry,
        "configuration_manager": configuration_manager,
        "structured_logger": structured_logger,
        "state_manager": state_manager,
    }


# ---------------------------------------------------------------------------
# Test 1 — Kernel C3 (ConfigurationManager) failure during real boot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kernel_configuration_manager_failure_aborts_boot_before_phase3():
    """Fault injection into C3 through the REAL kernel boot path.

    The kernel acquires C3 via get_configuration_manager() and initializes
    it inside _init_core_components() (kernel.py C3 block). We patch the
    getter at the kernel module's actual import site so the failure travels
    through the real boot path, then assert the kernel's DESIGNED response:
    loud fail-fast boot abort — the failed C3 never reaches the frozen
    boundary, and nothing downstream of C3 (C4 logger, Core Managers,
    kernel start) is constructed.
    """
    _reset_all_singletons()
    try:
        kernel = HermesKernel(config=KernelConfig(data_dir=Path(tempfile.mkdtemp())))

        class FailingConfigurationManager(ConfigurationManager):
            """Real C3 subclass whose initialize() raises at the Phase-2 step."""

            async def initialize(self, kernel=None):
                raise RuntimeError("Simulated configuration manager initialization failure")

        failing_cm = FailingConfigurationManager()

        # Patch the exact name the kernel imports (kernel.py line ~32:
        # `get_configuration_manager as ...`). The failure is therefore
        # injected where the kernel ACTUALLY acquires C3 during boot.
        with patch(
            "aios.core.kernel.get_configuration_manager", return_value=failing_cm
        ):
            # The kernel contract: core-component initialization failure is
            # FATAL (fail-fast). It must propagate, not be swallowed.
            with pytest.raises(
                RuntimeError,
                match="Simulated configuration manager initialization failure",
            ):
                await kernel._init_core_components()

        # --- Assert the kernel's actual post-failure state ---------------

        # 1. Boot aborted at C3: everything downstream of C3 in the
        #    deterministic boot sequence must NOT exist.
        assert kernel._configuration is failing_cm
        assert kernel._structured_logger is None, (
            "C4 StructuredLogger must not be constructed when C3 failed "
            "(boot must abort at the Phase-2 boundary, not limp onward)"
        )
        assert kernel._state_manager is None, (
            "No Core Manager may be constructed when C3 failed"
        )
        assert kernel._workflow_manager is None
        assert kernel._health_manager is None

        # 2. The failed C3 itself never crossed the Phase-2->3 freeze
        #    boundary: it must not be FROZEN (a frozen config after a failed
        #    initialize would be a contract violation — freeze happens only
        #    after successful initialize() in _init_core_components).
        from aios.core.configuration_manager import ConfigState

        assert failing_cm.state is not ConfigState.FROZEN
        assert failing_cm.state is not ConfigState.SHUTDOWN

        # 3. The kernel did not silently mark itself running despite the
        #    failed boot (start() was never reached; _init_core_components
        #    is what start() calls first).
        assert kernel._running is False

        # 4. A retry of the whole boot with a HEALTHY C3 still works — the
        #    kernel recovers cleanly from the aborted attempt. Note: the
        #    failed attempt published the failing CM as the global C3
        #    singleton (set_configuration_manager runs BEFORE initialize()
        #    in _init_core_components), so a clean retry requires resetting
        #    that poisoned singleton — which is exactly what the kernel
        #    does on every boot via its own reset calls. Resetting here
        #    mirrors the next boot's starting conditions.
        reset_configuration_manager_singleton()
        await kernel._init_core_components()
        assert kernel._configuration is not failing_cm
        assert kernel._configuration.state is ConfigState.FROZEN
        assert kernel._structured_logger is not None
        assert kernel._state_manager is not None
        # Cleanly tear down what the successful retry constructed.
        await kernel._configuration.shutdown()
        await kernel._event_bus.shutdown()
        await kernel._service_registry.shutdown()

    finally:
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Test 2 — Kernel C2 (ServiceRegistry) failure during real boot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kernel_service_registry_failure_aborts_boot():
    """Fault injection into C2 through the REAL kernel boot path.

    Code inspection of kernel.py: the boot path never calls
    ServiceRegistry.initialize() — the kernel obtains C2 at ~line 1166 via
    `get_core_service_registry(event_bus=...)` (imported into the kernel
    module as `get_service_registry as get_core_service_registry`) and
    uses it lazily from there. The genuine C2 boot failure therefore
    happens at that ACQUISITION point, which is where this test injects:
    the patched getter raises where the kernel actually acquires C2
    during _init_core_components(). The kernel's designed response is a
    loud boot abort — it must not proceed to Phase 2 (C3) with no C2.
    """
    _reset_all_singletons()
    try:
        kernel = HermesKernel(config=KernelConfig(data_dir=Path(tempfile.mkdtemp())))

        def failing_get_registry(event_bus=None):
            # C2 construction/acquisition itself fails (e.g. corrupted
            # registry state, failed internal wiring) at the exact point
            # the kernel boot path obtains its registry.
            raise RuntimeError("Simulated service registry acquisition failure")

        # Patch the exact symbol the kernel module binds at import time
        # (kernel.py line ~32). The failure therefore travels through the
        # real boot path — not around it.
        with patch(
            "aios.core.kernel.get_core_service_registry", failing_get_registry
        ):
            with pytest.raises(
                RuntimeError,
                match="Simulated service registry acquisition failure",
            ):
                await kernel._init_core_components()

        # --- Assert the kernel's actual post-failure state ---------------

        # 1. Boot aborted at the C2 boundary: the kernel never obtained a
        #    registry, and nothing downstream was constructed.
        assert kernel._service_registry is None, (
            "Kernel must not hold a registry after its acquisition failed"
        )
        # Phase-2 C3 was never reached (assigned only after C2 in
        # _init_core_components()).
        assert kernel._configuration is None, (
            "Kernel must not proceed to Phase 2 (C3) when C2 acquisition failed"
        )
        assert kernel._structured_logger is None
        assert kernel._state_manager is None
        assert kernel._workflow_manager is None
        assert kernel._health_manager is None
        assert kernel._running is False

        # 2. No poisoned global state: the failing boot left no registry
        #    singleton behind for a later boot to inherit.
        from aios.core import service_registry as sr_module

        assert sr_module._INSTANCE is None, (
            "Failed C2 acquisition must not publish a registry singleton"
        )

        # 3. The kernel's public engineering-service surface fails CLOSED
        #    (clear RuntimeError, not a silent wrong answer) when C2 is
        #    absent — the pre-start contract (register before start).
        with pytest.raises(RuntimeError):
            kernel.register_service(_FailingEngineeringService())
        with pytest.raises(RuntimeError):
            kernel.get_service("anything")

        # 4. A clean retry with a healthy C2 acquisition still succeeds —
        #    the aborted boot did not wedge the kernel object.
        await kernel._init_core_components()
        assert kernel._service_registry is not None
        assert kernel._configuration is not None
        assert kernel._state_manager is not None
        assert kernel._running is False  # start() not called; boot path only
        # Cleanly tear down what the successful retry constructed.
        await kernel._configuration.shutdown()
        await kernel._event_bus.shutdown()
        await kernel._service_registry.shutdown()

    finally:
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Test 3 — LifecycleManager Core Manager failure (RETAINED, genuine)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifecycle_manager_handles_core_manager_failure():
    """RETAINED per Terminal 3 (marked genuine) — strengthened assertions only.

    Exercises the real LifecycleManager.initialize() phase loop with a
    registered Core Manager whose initialize() fails, and asserts the
    manager's ACTUAL designed response: rollback coordination to the
    UNINITIALIZED rollback target and a typed LifecycleManagerError that
    carries the injected fault as original_error (LM-INIT-FAIL-001).
    """
    _reset_all_singletons()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            components = await _build_real_core_components(Path(tmp))

            lifecycle_manager = LifecycleManager(
                event_bus=components["event_bus"],
                service_registry=components["service_registry"],
                configuration_manager=components["configuration_manager"],
                logger=components["structured_logger"],
            )

            # Register a Core Manager whose initialize() fails, injected at
            # the real registration point (LM-REG-001 validates topology).
            failing_state_manager = FailingStateManager(fail_during_init=True)
            lifecycle_manager.register_manager(failing_state_manager)

            # Act — the real phase loop hits the injected failure.
            with pytest.raises(LifecycleManagerError) as exc_info:
                await lifecycle_manager.initialize()

            assert failing_state_manager.initialize_called

            # --- Assert the ACTUAL designed failure response -------------
            # The typed error must carry the injected fault (rule LM-INIT-
            # FAIL-001 wraps the original exception).
            assert exc_info.value.rule_id == "LM-INIT-FAIL-001"
            assert isinstance(exc_info.value.original_error, RuntimeError)
            assert (
                "Simulated state manager initialization failure"
                in str(exc_info.value.original_error)
            )

            # Rollback coordination (§4.3.7) must have run and returned the
            # lifecycle to its rollback target — NOT left it stuck in
            # INITIALIZING.
            assert lifecycle_manager.state is LifecycleState.UNINITIALIZED, (
                "Rollback must return the lifecycle to its rollback target "
                "(UNINITIALIZED) after an init failure, not leave it "
                "INITIALIZING"
            )

            # Rollback shut down the phase-2 managers it had already
            # initialized, in reverse order — visible on our registered
            # double only if it got that far; but the phase-completed book
            # keeping must be cleared either way.
            assert lifecycle_manager._initialized_order == []

    finally:
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Test 4 — Workflow step failure through real execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_step_failure_marks_execution_failed():
    """Fault injection into a workflow step through REAL WorkflowManager execution.

    A registered step handler raises during start_workflow()'s real
    execution loop. Assert the actual failure policy from workflow.py's
    state model:

      * the failing step's RetryPolicy is exhausted (max_retries + 1
        attempts recorded by the real RetryManager),
      * the required-step failure propagates to _fail_workflow(), which
        marks the execution WorkflowStatus.FAILED and records the error,
      * the completed first step is retained in state (partial progress),
      * the failed execution is removed from the running set.
    """
    _reset_all_singletons()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            components = await _build_real_core_components(Path(tmp))

            workflow_manager = WorkflowManager(
                state_manager=components["state_manager"],
                service_registry=components["service_registry"],
                configuration_manager=components["configuration_manager"],
                logger=components["structured_logger"],
            )
            await workflow_manager.initialize()
            set_workflow_manager(workflow_manager)

            # Definition: step1 (healthy) -> step2 (required, will fail).
            test_definition = WorkflowDefinition(
                workflow_id="test_workflow_with_failure",
                name="Test Workflow with Failure",
                description="Chaos test: injected failing step",
                steps=[
                    WorkflowStep(
                        step_id="step1",
                        name="First Step",
                        service="test_service",
                        event_type=EventType.WORKFLOW_STEP_STARTED,
                        payload={"test": "data"},
                        depends_on=[],
                    ),
                    WorkflowStep(
                        step_id="step2",
                        name="Second Step (will fail)",
                        service="failing_service",
                        event_type=EventType.WORKFLOW_STEP_STARTED,
                        payload={"test": "data"},
                        depends_on=["step1"],
                        # Explicit tight retry policy keeps the test fast and
                        # deterministic (jitter off; 20ms base delay).
                        retry_policy={"max_retries": 2, "delay_seconds": 0.02, "jitter": False},
                    ),
                ],
                initial_state={},
            )
            workflow_manager.register_workflow(test_definition)

            healthy_calls = 0

            async def healthy_step_handler(payload: dict[str, Any]) -> dict[str, Any]:
                nonlocal healthy_calls
                healthy_calls += 1
                return {"status": "success", "data": payload.get("test", "")}

            failing_calls = 0

            async def failing_step_handler(payload: dict[str, Any]) -> dict[str, Any]:
                nonlocal failing_calls
                failing_calls += 1
                raise RuntimeError("Simulated service failure in failing_service")

            workflow_manager.register_step_handler("test_service", healthy_step_handler)
            workflow_manager.register_step_handler("failing_service", failing_step_handler)

            # Act — real execution path with the injected step fault.
            execution_id = await workflow_manager.start_workflow(
                "test_workflow_with_failure"
            )

            # --- Assert the ACTUAL workflow failure policy ----------------

            # 1. The step really executed: healthy step ran once; the
            #    failing handler was attempted exactly max_retries + 1
            #    times (initial attempt + 2 retries) by the real
            #    RetryManager — proving the retry policy processed the
            #    fault rather than the error merely propagating.
            assert healthy_calls == 1
            assert failing_calls == 3, (
                "RetryManager must attempt the failing step max_retries + 1 "
                f"times (got {failing_calls})"
            )

            # 2. The execution state is marked FAILED with the error
            #    recorded (workflow.py _fail_workflow contract).
            status = workflow_manager.get_workflow_status(execution_id)
            assert status is not None
            assert status["status"] == WorkflowStatus.FAILED.value
            assert "Simulated service failure in failing_service" in status["error"]
            assert "failed_at" in status

            # 3. Partial progress is retained: the first step completed
            #    BEFORE the failure is recorded in the same state.
            assert status["completed_steps"] == ["step1"]
            assert status["step_results"]["step1"]["status"] == "success"

            # 4. The failed execution is no longer tracked as running.
            assert execution_id not in workflow_manager._running_workflows
            assert workflow_manager.list_running() == []

            # 5. The manager itself survived and stays usable (a second
            #    execution of a healthy workflow still completes).
            ok_definition = WorkflowDefinition(
                workflow_id="healthy_retry_workflow",
                name="Healthy Retry",
                description="Post-failure usability",
                steps=[
                    WorkflowStep(
                        step_id="only",
                        name="Only Step",
                        service="test_service",
                        event_type=EventType.WORKFLOW_STEP_STARTED,
                        payload={"test": "data"},
                        depends_on=[],
                    )
                ],
                initial_state={},
            )
            workflow_manager.register_workflow(ok_definition)
            ok_exec = await workflow_manager.start_workflow("healthy_retry_workflow")
            ok_status = workflow_manager.get_workflow_status(ok_exec)
            assert ok_status["status"] == WorkflowStatus.COMPLETED.value

            await workflow_manager.shutdown()

    finally:
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Test 5 — Kernel partial-failure tolerance for non-critical services
# ---------------------------------------------------------------------------


class _FailingEngineeringService:
    """Minimal Engineering Service whose start() always raises.

    Matches the surface the kernel's _start_services() loop actually uses:
    ``name`` (for the ``engineering.`` registration id), and async
    ``start()``. It is registered through the kernel's real
    register_service() path (canonical C2, ``engineering.`` namespace).
    """

    name = "chaos_failing_service"
    version = "1.0.0"
    description = "A service that always fails to start"

    async def start(self) -> None:
        raise RuntimeError("Simulated engineering service start failure")

    async def stop(self) -> None:
        pass


class _HealthyEngineeringService:
    """Companion service that starts cleanly — proves the loop continued."""

    name = "chaos_healthy_service"
    version = "1.0.0"
    description = "A service that starts cleanly"

    def __init__(self):
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False


@pytest.mark.asyncio
async def test_kernel_continues_after_non_critical_service_start_failure():
    """Fault injection into a non-critical service through the REAL start loop.

    The kernel's documented reliability contract (R-8, kernel.py
    _start_services ~2974-3047) is partial-start tolerance: an Engineering
    Service whose start() raises is recorded as failed and SKIPPED — the
    kernel itself keeps starting and other services keep running.

    We inject a failing Engineering Service at the kernel's REAL
    registration point, drive the REAL _start_services() loop, and assert
    the actual tolerance contract — not attribute survival on unrelated
    objects.
    """
    _reset_all_singletons()
    try:
        kernel = HermesKernel(
            config=KernelConfig(
                data_dir=Path(tempfile.mkdtemp()),
                # The kernel must not auto-start the full engineering fleet:
                # we are testing the start loop in isolation.
                auto_start_services=False,
            )
        )
        # Real core-component initialization (C1-C4 + Core Managers) —
        # the substrate the start loop runs on.
        await kernel._init_core_components()
        await kernel._init_lifecycle_manager()

        # Register through the kernel's real registration path (canonical
        # C2, ``engineering.`` namespace, INV-SR-NS-001) — order matters:
        # the failing service comes FIRST so a non-tolerant loop would
        # never reach the healthy one.
        failing_service = _FailingEngineeringService()
        healthy_service = _HealthyEngineeringService()
        kernel.register_service(failing_service)
        kernel.register_service(healthy_service)

        # Act — the REAL start-services loop with the injected fault.
        # R-8 partial-start tolerance means this must NOT raise.
        await kernel._start_services()

        # --- Assert the ACTUAL partial-start tolerance contract ----------

        # 1. The failing service is recorded as failed WITH the error —
        #    the loop processed the fault, it did not skip it silently.
        svc_status = kernel._services.get("chaos_failing_service")
        assert svc_status is not None, "Failing service must be tracked in kernel._services"
        assert svc_status.started is False
        assert svc_status.healthy is False
        assert "Simulated engineering service start failure" in (svc_status.last_error or "")

        # 2. The loop CONTINUED past the failure: the healthy sibling
        #    service was started (it was registered after the failing one).
        assert healthy_service.started is True, (
            "Kernel must continue starting subsequent services after a "
            "non-critical service failure (R-8 partial-start tolerance)"
        )
        healthy_status = kernel._services.get("chaos_healthy_service")
        assert healthy_status is not None and healthy_status.started is True

        # 3. Core kernel operation still works after the fault: resolve a
        #    service through the canonical C2 registry and confirm the
        #    registry still serves lookups (real operation, not attribute
        #    presence).
        resolved = kernel.get_service("chaos_healthy_service")
        assert resolved is healthy_service

        # 4. Lifecycle is OPERATIONAL — the kernel did not degrade its own
        #    lifecycle state due to a non-critical service failure.
        assert kernel._lifecycle.state is LifecycleState.OPERATIONAL
        assert kernel.is_ready is True

        # Clean teardown of what we started.
        await kernel._lifecycle.shutdown()
        await kernel._configuration.shutdown()
        await kernel._event_bus.shutdown()
        await kernel._service_registry.shutdown()

    finally:
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Test 6 — HealthManager aggregate-status degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_manager_unhealthy_result_degrades_aggregate_status():
    """Fault injection into a component's health through the real HealthManager.

    Record an UNHEALTHY result through the real record_health() entry point
    and assert the ACTUAL aggregation contract (health_manager.py
    _recompute_overall: worst-wins UNHEALTHY > DEGRADED > HEALTHY >
    UNKNOWN) via the real public accessors — overall_status property,
    per-component snapshot, and get_all_health() counts.
    """
    _reset_all_singletons()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            components = await _build_real_core_components(Path(tmp))

            health_manager = HealthManager(
                service_registry=components["service_registry"],
                configuration_manager=components["configuration_manager"],
                logger=components["structured_logger"],
            )
            await health_manager.initialize()

            # Baseline: a healthy component first, so the test proves the
            # aggregate FLIPS due to the injected unhealthy result rather
            # than trivially being unhealthy from the start.
            health_manager.record_health(
                component="healthy_component",
                check_id="check_ok",
                status=HealthStatus.HEALTHY,
            )
            assert health_manager.overall_status is HealthStatus.HEALTHY

            # Act — inject the fault through the real entry point.
            result = health_manager.record_health(
                component="failing_health_component",
                check_id="health_check_1",
                status=HealthStatus.UNHEALTHY,
                error="Simulated health check failure",
            )
            assert result.status is HealthStatus.UNHEALTHY
            assert result.error == "Simulated health check failure"

            # --- Assert the ACTUAL aggregate-health response --------------

            # 1. Worst-wins aggregation: the aggregate status itself must
            #    now be UNHEALTHY (this fails if aggregation stops
            #    recognizing unhealthy components).
            assert health_manager.overall_status is HealthStatus.UNHEALTHY, (
                "Aggregate status must degrade to UNHEALTHY once any "
                "recorded check is UNHEALTHY (worst-wins precedence)"
            )

            # 2. The unhealthy component is visible through the real
            #    component snapshot with its error recorded.
            component_health = health_manager.get_component_health(
                "failing_health_component"
            )
            assert component_health is not None
            assert component_health["status"] == "UNHEALTHY"
            assert component_health["error"] == "Simulated health check failure"

            # 3. The full aggregate snapshot counts the unhealthy check and
            #    reports the degraded overall status.
            snapshot = health_manager.get_all_health()
            assert snapshot["overall"] == HealthStatus.UNHEALTHY.value
            assert snapshot["unhealthy_checks"] == 1
            assert snapshot["healthy_checks"] == 1
            assert snapshot["components"]["failing_health_component"] == "UNHEALTHY"
            assert snapshot["components"]["healthy_component"] == "HEALTHY"

            # 4. Consecutive-failure tracking processed the fault: the
            #    registered check recorded the failure count.
            check = health_manager.get_check(
                "failing_health_component", "health_check_1"
            )
            assert check is not None
            assert check.consecutive_failures == 1

            await health_manager.shutdown()

    finally:
        _reset_all_singletons()
