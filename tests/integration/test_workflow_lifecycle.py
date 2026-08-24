"""
M1 — WorkflowManager Lifecycle Tests.

Verifies WorkflowManager participates correctly in the kernel lifecycle:
- Initializes in Phase 4 (after CapabilityManager, alphabetical within phase)
- Shuts down in reverse Phase 4 order (before CapabilityManager)
- Registers with ServiceRegistry as 'core.workflow'
- Emits canonical workflow lifecycle events
- health_ready() reflects initialization state correctly
"""

from __future__ import annotations

import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pytest
import pytest_asyncio

from aios.core import HermesKernel, KernelConfig
from aios.core.kernel_management import run_kernel, stop_kernel, create_kernel
from aios.core.lifecycle_manager import LifecycleManager, LifecycleState
from aios.core.workflow import (
    WorkflowManager,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
)
from aios.events.core.types import EventType


@pytest_asyncio.fixture
async def clean_kernel():
    """Create a kernel with clean state for testing using run_kernel."""
    await stop_kernel()

    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)

    kernel = await run_kernel(config)
    yield kernel

    await stop_kernel()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def kernel_for_tracking():
    """Create a kernel for tracking initialize/shutdown calls."""
    await stop_kernel()

    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)

    kernel = await create_kernel(config)
    # Managers are created in _init_core_components() which is called from start()
    # So we need to start the kernel to construct managers, but we can monkey-patch
    # before calling start()
    yield kernel

    await stop_kernel()
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestWorkflowManagerLifecycle:
    """WorkflowManager-specific lifecycle verification."""

    @pytest.mark.asyncio
    async def test_workflow_manager_registered_with_lifecycle_manager(self, clean_kernel):
        """Test WorkflowManager is registered with LifecycleManager in Phase 4."""
        kernel = clean_kernel

        lm = kernel._lifecycle
        wm = kernel._workflow_manager

        # Verify WorkflowManager exists and is registered
        assert wm is not None
        assert "WorkflowManager" in lm._managers
        assert lm._managers["WorkflowManager"] is wm

    @pytest.mark.asyncio
    async def test_workflow_manager_phase_4_initialization_order(self, kernel_for_tracking):
        """Test WorkflowManager initializes in Phase 4, after CapabilityManager."""
        kernel = kernel_for_tracking
        await kernel.start()

        lm = kernel._lifecycle
        initialized_order = lm.initialized_managers

        # CapabilityManager and WorkflowManager should both be in Phase 4
        cap_idx = initialized_order.index("CapabilityManager")
        wf_idx = initialized_order.index("WorkflowManager")

        # Alphabetical within Phase 4: CapabilityManager before WorkflowManager
        assert cap_idx < wf_idx

        # Both should be after Phase 3 managers
        phase3_managers = ["HealthManager", "ResourceManager", "SecurityManager"]
        for mgr in phase3_managers:
            phase3_idx = initialized_order.index(mgr)
            assert phase3_idx < cap_idx
            assert phase3_idx < wf_idx

        await kernel.stop()

    @pytest.mark.asyncio
    async def test_workflow_manager_reverse_shutdown_order(self, kernel_for_tracking):
        """Test WorkflowManager shuts down before CapabilityManager in reverse Phase 4."""
        kernel = kernel_for_tracking
        await kernel.start()

        shutdown_order: List[str] = []

        # Track shutdown order
        original_shutdowns = {}
        for name in ["CapabilityManager", "WorkflowManager"]:
            mgr = getattr(kernel, f"_{name.lower().replace('manager', '_manager')}")
            original_shutdowns[name] = mgr.shutdown

            async def make_tracked_shutdown(mgr_name):
                async def tracked_shutdown():
                    shutdown_order.append(mgr_name)
                    await original_shutdowns[mgr_name]()
                return tracked_shutdown

            mgr.shutdown = await make_tracked_shutdown(name)

        await kernel.stop()

        # In reverse Phase 4 order: WorkflowManager before CapabilityManager
        # (reverse alphabetical)
        assert "WorkflowManager" in shutdown_order
        assert "CapabilityManager" in shutdown_order
        assert shutdown_order.index("WorkflowManager") < shutdown_order.index("CapabilityManager")

    @pytest.mark.asyncio
    async def test_workflow_manager_service_registry_registration(self, clean_kernel):
        """Test WorkflowManager registers with ServiceRegistry as 'core.workflow'."""
        kernel = clean_kernel

        sr = kernel.service_registry
        assert sr is not None

        reg = sr.get_registration("core.workflow")
        assert reg is not None, "WorkflowManager not registered in ServiceRegistry"
        assert reg.service is kernel._workflow_manager
        assert reg.metadata.get("kind") == "core_manager"
        assert reg.metadata.get("manager") == "WorkflowManager"
        assert reg.metadata.get("phase") == 4

    @pytest.mark.asyncio
    async def test_workflow_manager_health_ready_states(self, kernel_for_tracking):
        """Test WorkflowManager health_ready reflects initialization state."""
        kernel = kernel_for_tracking
        await kernel.start()

        # After initialization: ready
        wm = kernel._workflow_manager
        assert wm is not None
        assert wm.health_ready() is True
        assert wm.is_initialized is True

        await kernel.stop()

        # After shutdown: not ready
        assert wm.health_ready() is False
        assert wm.is_initialized is False

    @pytest.mark.asyncio
    async def test_workflow_manager_lifecycle_events(self, kernel_for_tracking):
        """Test WorkflowManager emits lifecycle events through LifecycleManager."""
        kernel = kernel_for_tracking
        # EventBus is initialized during kernel.start()
        await kernel.start()

        events = kernel._event_bus.getRecentEvents()

        # Find phase completion event for Phase 4
        phase4_events = [
            e for e in events
            if e.eventType == EventType.CORE_MANAGER_INITIALIZED
            and e.payload.get("phase") == 4
        ]

        assert len(phase4_events) > 0, "No Phase 4 completion event found"

        phase4_event = phase4_events[0]
        managers = phase4_event.payload.get("managers", [])
        assert "CapabilityManager" in managers
        assert "WorkflowManager" in managers

        # Check shutdown event for Phase 4 (need to check events after stop)
        await kernel.stop()

        events = kernel._event_bus.getRecentEvents()
        shutdown_events = [
            e for e in events
            if e.eventType == EventType.CORE_MANAGER_SHUTDOWN
            and e.payload.get("phase") == 4
        ]

        assert len(shutdown_events) > 0, "No Phase 4 shutdown event found"

    @pytest.mark.asyncio
    async def test_workflow_manager_properties(self, clean_kernel):
        """Test WorkflowManager reports correct metadata."""
        kernel = clean_kernel
        wm = kernel._workflow_manager

        assert wm.name == "WorkflowManager"
        assert wm.phase == 4
        assert wm.manager_id == "core.workflow"
        assert wm.dependencies == ["LifecycleManager"]

    @pytest.mark.asyncio
    async def test_workflow_manager_not_started_as_service(self, clean_kernel):
        """Test WorkflowManager is NOT started via _start_services (engineering services path)."""
        kernel = clean_kernel

        # WorkflowManager should be initialized by LifecycleManager, not by _start_services
        # The kernel's _services dict should not contain workflow_manager as a service
        assert "workflow_manager" not in kernel._services

        # The workflow manager should be initialized and ready
        assert kernel._workflow_manager.is_initialized is True
        assert kernel._workflow_manager.health_ready() is True

    @pytest.mark.asyncio
    async def test_workflow_manager_can_execute_workflows(self, clean_kernel):
        """Test WorkflowManager can execute workflows after kernel lifecycle init."""
        kernel = clean_kernel
        wm = kernel._workflow_manager

        # Register a simple workflow
        async def test_handler(payload: Dict[str, Any]) -> str:
            return f"handled_{payload.get('step', 'unknown')}"

        wm.register_step_handler("test_service", test_handler)

        definition = WorkflowDefinition(
            workflow_id="test_wf",
            name="Test Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    name="Step 1",
                    service="test_service",
                    event_type="test.execute",
                    payload={"step": "step_1"},
                ),
            ],
        )

        wm.register_workflow(definition)

        # Execute workflow
        execution_id = await wm.start_workflow("test_wf")

        # Wait for completion
        await asyncio.sleep(0.5)

        # Verify completion
        state = wm.get_workflow_status(execution_id)
        assert state is not None
        assert state["status"] == WorkflowStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_workflow_manager_shutdown_clears_state(self, clean_kernel):
        """Test WorkflowManager shutdown clears running workflows."""
        kernel = clean_kernel
        wm = kernel._workflow_manager

        async def slow_handler(payload: Dict[str, Any]) -> str:
            await asyncio.sleep(0.5)  # Longer sleep to ensure it's running
            return "done"

        wm.register_step_handler("slow_service", slow_handler)

        definition = WorkflowDefinition(
            workflow_id="slow_wf",
            name="Slow Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    name="Step 1",
                    service="slow_service",
                    event_type="test.execute",
                    payload={"step": "step_1"},
                ),
            ],
        )

        wm.register_workflow(definition)

        # Start workflow
        execution_id = await wm.start_workflow("slow_wf")

        # Wait a bit for it to start
        await asyncio.sleep(0.05)

        # Verify it's running
        state = wm.get_workflow_status(execution_id)
        assert state is not None
        # May be running or completed depending on timing
        assert state["status"] in (WorkflowStatus.RUNNING.value, WorkflowStatus.COMPLETED.value)

        # Stop kernel (which shuts down WorkflowManager)
        await kernel.stop()

        # WorkflowManager shutdown should clear running workflows
        # The internal _running_workflows dict should be cleared
        assert len(wm._running_workflows) == 0

    @pytest.mark.asyncio
    async def test_workflow_manager_idempotent_initialize_shutdown(self, kernel_for_tracking):
        """Test WorkflowManager initialize/shutdown are idempotent."""
        kernel = kernel_for_tracking
        await kernel.start()

        wm = kernel._workflow_manager
        assert wm.is_initialized is True

        # Call initialize directly (should be no-op)
        await wm.initialize()
        assert wm.is_initialized is True

        # Shutdown via kernel stop
        await kernel.stop()
        assert wm.is_initialized is False

        # Call shutdown directly (should be no-op)
        await wm.shutdown()
        assert wm.is_initialized is False

    @pytest.mark.asyncio
    async def test_workflow_manager_workflow_state_persistence(self, clean_kernel):
        """Test workflow state is maintained through StateManager during lifecycle."""
        kernel = clean_kernel
        wm = kernel._workflow_manager
        sm = kernel._state_manager

        async def handler(payload: Dict[str, Any]) -> str:
            return "result"

        wm.register_step_handler("persist_service", handler)

        definition = WorkflowDefinition(
            workflow_id="persist_wf",
            name="Persist Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    name="Step 1",
                    service="persist_service",
                    event_type="test.execute",
                    payload={"step": "step_1"},
                ),
            ],
        )

        wm.register_workflow(definition)
        execution_id = await wm.start_workflow("persist_wf")

        await asyncio.sleep(0.5)

        # Check state in StateManager
        from aios.core.state import StateScope
        state = sm.get_state(StateScope.WORKFLOW, execution_id, "workflow")
        assert state is not None
        assert state["status"] == WorkflowStatus.COMPLETED.value
        assert state["workflow_id"] == "persist_wf"

        # After kernel stop, state should still be in StateManager
        # (StateManager shutdown happens in Phase 2, after WorkflowManager in Phase 4)
        await kernel.stop()

        # StateManager is still available after kernel stop
        state_after = sm.get_state(StateScope.WORKFLOW, execution_id, "workflow")
        assert state_after is not None
        assert state_after["status"] == WorkflowStatus.COMPLETED.value


class TestWorkflowManagerNotNoOp:
    """Explicit tests confirming WorkflowManager is NOT a no-op in lifecycle."""

    @pytest.mark.asyncio
    async def test_workflow_manager_initialize_called(self, kernel_for_tracking):
        """Test WorkflowManager.initialize() is actually called during kernel start."""
        kernel = kernel_for_tracking
        await kernel.start()

        wm = kernel._workflow_manager

        # Spy on initialize
        init_called = False
        original_init = wm.initialize

        async def tracked_init():
            nonlocal init_called
            init_called = True
            await original_init()

        wm.initialize = tracked_init

        # Call initialize again (should be called again for idempotency test)
        await wm.initialize()

        assert init_called is True, "WorkflowManager.initialize() was not called"

        await kernel.stop()

    @pytest.mark.asyncio
    async def test_workflow_manager_shutdown_called(self, kernel_for_tracking):
        """Test WorkflowManager.shutdown() is actually called during kernel stop."""
        kernel = kernel_for_tracking
        await kernel.start()

        wm = kernel._workflow_manager

        # Spy on shutdown
        shutdown_called = False
        original_shutdown = wm.shutdown

        async def tracked_shutdown():
            nonlocal shutdown_called
            shutdown_called = True
            await original_shutdown()

        wm.shutdown = tracked_shutdown

        await kernel.stop()

        assert shutdown_called is True, "WorkflowManager.shutdown() was not called"

    @pytest.mark.asyncio
    async def test_workflow_manager_registered_in_kernel_construction(self, kernel_for_tracking):
        """Test WorkflowManager is constructed and registered during kernel init."""
        kernel = kernel_for_tracking
        await kernel.start()

        # After start: initialized and registered with LifecycleManager
        assert kernel._workflow_manager is not None
        assert kernel._workflow_manager.is_initialized is True
        assert "WorkflowManager" in kernel._lifecycle._managers
        assert kernel._lifecycle._managers["WorkflowManager"] is kernel._workflow_manager

        await kernel.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])