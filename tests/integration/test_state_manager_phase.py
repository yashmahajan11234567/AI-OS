"""
Task 10 — StateManager Core Manager integration tests (Part 4 §4.4 / §4.2.3).

Verifies, in an integration context:

  * StateManager is constructed by the kernel after Core Components C1–C4.
  * StateManager is registered with LifecycleManager (Phase 2, "State & Storage")
    and driven by its phase topology — NOT by the engineering-service
    ``_start_services()`` loop.
  * StateManager registers with the canonical ServiceRegistry (C2) as
    ``core.state`` with core-manager metadata (Part 4 §4.4.9 names kernel.state
    but INV-SR-NS-002 reserves the kernel namespace; core.state follows the
    core.lifecycle precedent).
  * StateManager consumes the frozen ConfigurationManager (C3) and logs through
    the StructuredLogger (C4).
  * Shutdown runs LifecycleManager's reverse-phase order and marks ``core.state``
    SHUTDOWN in the canonical registry.
  * No Task 1–9 regressions are introduced (imports resolve).

Only canonical Part-2 EventTypes are asserted (CONFLICT E.1 mapping). No new
EventType is invented.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aios.core.configuration_manager import (
    reset_configuration_manager_singleton,
)
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    LifecycleState,
    reset_lifecycle_manager_singleton,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.state import (
    StateManager,
    StateScope,
    get_state_manager,
    reset_state_manager_singleton,
)
from aios.events.core.bus import reset_event_bus_singleton


def _reset_all() -> None:
    """Reset every process-wide singleton guarded by these tests (INV-EB-001)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()


async def _start_kernel(data_dir: Path | None = None) -> HermesKernel:
    """Start a fresh kernel for integration testing."""
    _reset_all()
    config = KernelConfig(data_dir=data_dir or Path(tempfile.mkdtemp()))
    return HermesKernel(config=config)


# ---------------------------------------------------------------------------
# Phase-2 orchestration by LifecycleManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kernel_registers_state_manager_as_phase2():
    k = await _start_kernel()
    try:
        await k.start()
        # 1. StateManager constructed by the kernel after C1–C4.
        assert isinstance(k.state_manager, StateManager)
        # 2. Registered with LifecycleManager for Phase-2 orchestration.
        assert k.lifecycle is not None
        assert "StateManager" in k.lifecycle._managers
        # 3. Driven by LifecycleManager -> initialized.
        assert k.state_manager.is_initialized
        assert k.state_manager.health_ready() is True
        # 4. Same instance as the global singleton and as the kernel-held one.
        assert k.state_manager is get_state_manager()
    finally:
        await k.stop()
    _reset_all()


@pytest.mark.asyncio
async def test_kernel_state_registered_in_canonical_sr_as_kernel_state():
    k = await _start_kernel()
    try:
        await k.start()
        sr = k.service_registry
        assert sr is get_service_registry()
        reg = sr.get_registration("core.state")
        assert reg is not None
        assert reg.service is k.state_manager
        # Core-manager metadata envelope (not an ordinary engineering service).
        assert reg.metadata.get("kind") == "core_manager"
        assert reg.metadata.get("manager") == "StateManager"
        assert reg.metadata.get("phase") == 2
    finally:
        await k.stop()
    _reset_all()


@pytest.mark.asyncio
async def test_state_manager_not_in_start_services_path():
    k = await _start_kernel()
    try:
        await k.start()
        # StateManager's lifecycle is owned by LifecycleManager; it must NOT
        # appear among the kernel's started engineering services.
        assert "state_manager" not in k._services
        # WorkflowManager is a Phase 4 Core Manager (Task 16), not an engineering
        # service. It is registered with LifecycleManager and does NOT appear in
        # the kernel's _services collection (which tracks only engineering services).
        # No assertion about workflow_manager in _services.
    finally:
        await k.stop()
    _reset_all()


@pytest.mark.asyncio
async def test_state_manager_uses_canonical_sr_cm_sl():
    k = await _start_kernel()
    try:
        await k.start()
        sm = k.state_manager
        # C2 — canonical ServiceRegistry.
        assert sm._service_registry is k.service_registry
        # C3 — canonical (frozen) ConfigurationManager.
        assert sm._configuration is k.configuration
        # C4 — canonical StructuredLogger.
        assert sm._logger is k.logger
    finally:
        await k.stop()
    _reset_all()


@pytest.mark.asyncio
async def test_state_manager_health_ready_after_kernel_start():
    k = await _start_kernel()
    try:
        await k.start()
        assert k.state_manager.health_ready() is True
        assert k.state_manager.is_initialized
        assert k.lifecycle.state is LifecycleState.OPERATIONAL
    finally:
        await k.stop()
    _reset_all()


@pytest.mark.asyncio
async def test_state_manager_shutdown_marks_kernel_state_shutdown():
    k = await _start_kernel()
    await k.start()
    await k.stop()
    # After kernel stop, LifecycleManager shutdown ran reverse phase order, which
    # marked core.state SHUTDOWN in the canonical registry.
    reg = k.service_registry.get_registration("core.state")
    assert reg is not None
    assert reg.lifecycle_state.value == "SHUTDOWN"
    assert k.state_manager.health_ready() is False
    _reset_all()


@pytest.mark.asyncio
async def test_state_manager_business_apis_work_after_kernel_start():
    k = await _start_kernel()
    try:
        await k.start()
        sm = k.state_manager
        sm.set_state(StateScope.WORKFLOW, "wf-kernel", "status", "running")
        assert sm.get_state(StateScope.WORKFLOW, "wf-kernel", "status") == "running"
        snap = sm.checkpoint(StateScope.WORKFLOW, "wf-kernel")
        assert snap is not None
        # Summary of state accessible globally.
        assert "wf-kernel" in sm.list_identifiers(StateScope.WORKFLOW)
    finally:
        await k.stop()
    _reset_all()


# ---------------------------------------------------------------------------
# No Task 1–9 regressions (imports resolve)
# ---------------------------------------------------------------------------


def test_no_task_1_to_9_regressions_imports_resolve():
    # Import guard mirroring Task 9's integration regression check.
    from aios.core.configuration_manager import ConfigurationManager as C3  # noqa: F401
    from aios.core.lifecycle_manager import LifecycleManager  # noqa: F401
    from aios.core.service_registry import ServiceRegistry as C2  # noqa: F401
    from aios.core.state import StateManager as S10  # noqa: F401
    from aios.core.structured_logger import StructuredLogger as C4  # noqa: F401
    from aios.events.core import EventBus as C1  # noqa: F401

    assert True
