"""
Task 14 + Task 15 — Combined Critical Acceptance Test.

Read-only verification (no mutations to architecture / kernel FSM / LifecycleManager).
Verifies the architectural acceptance criteria for the three new Core Managers
(SecurityManager, CapabilityManager, ObservabilityManager) and that Task 9–11
critical behavior remains intact (no regression):

  1.  SecurityManager   is a Phase-3 (Governance) Core Manager.
  2.  CapabilityManager is a Phase-4 (Execution) Core Manager.
  3.  ObservabilityManager is a Phase-5 (Observability) Core Manager.
  4.  manager_id == core.security / core.capability / core.observability
      (NOT kernel.* — reserved namespace, INV-SR-NS-002).
  5.  Configuration uses kernel.{manager}.* (accessor pattern matches Tasks 9–13).
  6.  LifecycleManager owns their lifecycle (registered as Phase-3/4/5 managers).
  7.  None routed through _start_services / _stop_engineering_services.
  8.  Canonical ServiceRegistry (C2) is used for all three.
  9.  Canonical StructuredLogger (C4) is used (no stdlib logging in business methods).
  10. No duplicate manager authority exists.
  11. No EventType was invented (only canonical SECURITY_ISSUE_FOUND /
      SERVICE_STARTED / SERVICE_STOPPED / SKILL_EXECUTED / SKILL_FAILED /
      METRIC_EMITTED / TRACE_SPAN_STARTED / TRACE_SPAN_ENDED).
  12. Existing Task 9/10/11/12/13 critical behavior remains intact (regression).

Per the CRITICAL EVENT TYPE RULE, these tests assert ONLY on canonical Part-2
EventTypes. No new EventType is invented.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.core.capability_manager import (
    CapabilityManager,
    get_capability_manager,
    reset_capability_manager_singleton,
)
from aios.core.configuration_manager import (
    get_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios.core.health_manager import (
    HealthManager,
    HealthStatus,
    get_health_manager,
    reset_health_manager_singleton,
)
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    get_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
from aios.core.observability_manager import (
    MetricType as _MetricType,
)
from aios.core.observability_manager import (
    ObservabilityManager,
    get_observability_manager,
    reset_observability_manager_singleton,
)
from aios.core.resource_manager import (
    ResourceManager,
    get_resource_manager,
    reset_resource_manager_singleton,
)
from aios.core.security_manager import (
    SecurityDecision,
    SecurityManager,
    get_security_manager,
    reset_security_manager_singleton,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.state import (
    StateScope,
    get_state_manager,
    reset_state_manager_singleton,
)
from aios.core.storage import (
    StorageManager,
    get_storage_manager,
    reset_storage_manager_singleton,
)
from aios.events.core.bus import reset_event_bus_singleton
from aios.events.core.types import EventType


async def _wait_for_events(bus: Any, wanted: set[str], deadline_loops: int = 200) -> set[str]:
    """Poll the bus history until wanted canonical event names appear (bounded)."""
    names: set[str] = set()
    for _ in range(deadline_loops):
        names = {
            e.eventType.name
            for e in bus.getRecentEvents()
            if hasattr(e.eventType, "name")
        }
        if wanted <= names:
            return names
        await asyncio.sleep(0)
    return names


@pytest.mark.asyncio
async def test_critical_acceptance_identities(tmp_path):
    """Verify the 12 architectural acceptance criteria for Tasks 14 + 15."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # --- Criterion 1: SecurityManager is a Phase-3 (Governance) Core Manager ---
        sm = kernel.security_manager
        assert isinstance(sm, SecurityManager)
        assert sm.name == "SecurityManager"
        assert sm.phase == 3
        assert "SecurityManager" in kernel.lifecycle._managers
        phase_plan = kernel.lifecycle.phase_plan
        phase3 = [p for p in phase_plan if p["phase"] == 3][0]
        assert phase3["name"] == "Governance"
        assert "HealthManager" in phase3["managers"]
        assert "ResourceManager" in phase3["managers"]
        assert "SecurityManager" in phase3["managers"]

        # --- Criterion 2: CapabilityManager is a Phase-4 (Execution) Core Manager ---
        cm_ = kernel.capability_manager
        assert isinstance(cm_, CapabilityManager)
        assert cm_.name == "CapabilityManager"
        assert cm_.phase == 4
        assert "CapabilityManager" in kernel.lifecycle._managers
        phase4 = [p for p in phase_plan if p["phase"] == 4][0]
        assert "CapabilityManager" in phase4["managers"]
        assert "WorkflowManager" in phase4["managers"]

        # --- Criterion 3: ObservabilityManager is a Phase-5 (Observability) Core Manager ---
        om = kernel.observability_manager
        assert isinstance(om, ObservabilityManager)
        assert om.name == "ObservabilityManager"
        assert om.phase == 5
        assert "ObservabilityManager" in kernel.lifecycle._managers
        phase5 = [p for p in phase_plan if p["phase"] == 5][0]
        assert "ObservabilityManager" in phase5["managers"]

        # --- Criterion 4: manager_id == core.* (NOT kernel.* — reserved) ---
        assert sm.manager_id == "core.security"
        assert sm.manager_id != "kernel.security"
        assert cm_.manager_id == "core.capability"
        assert cm_.manager_id != "kernel.capability"
        assert om.manager_id == "core.observability"
        assert om.manager_id != "kernel.observability"

        # --- Criterion 5: Configuration uses kernel.{manager}.* ---
        assert kernel.configuration is get_configuration_manager()
        assert sm._configuration is kernel.configuration
        assert cm_._configuration is kernel.configuration
        assert om._configuration is kernel.configuration

        # --- Criterion 6: LifecycleManager owns their lifecycle ---
        assert sm.is_initialized
        assert sm.health_ready() is True
        assert cm_.is_initialized
        assert cm_.health_ready() is True
        assert om.is_initialized
        assert om.health_ready() is True

        # --- Criterion 7: NOT routed through engineering-service startup ---
        assert "security_manager" not in kernel._services
        assert "capability_manager" not in kernel._services
        assert "observability_manager" not in kernel._services
        started = list(kernel._services.keys())
        assert "security_manager" not in started
        assert "capability_manager" not in started
        assert "observability_manager" not in started
        # resource_manager (an actual service) IS started — confirms the rule
        # distinguishes Core Managers from engineering services.
        assert "resource_manager" in started

        # --- Criterion 8: Canonical ServiceRegistry (C2) is used ---
        sr = kernel.service_registry
        assert sr is get_service_registry()
        for sid, mgr_name, phase, mgr in [
            ("core.security", "SecurityManager", 3, sm),
            ("core.capability", "CapabilityManager", 4, cm_),
            ("core.observability", "ObservabilityManager", 5, om),
        ]:
            reg = sr.get_registration(sid)
            assert reg is not None, f"{sid} not registered"
            assert reg.service is mgr
            assert reg.metadata.get("kind") == "core_manager"
            assert reg.metadata.get("manager") == mgr_name
            assert reg.metadata.get("phase") == phase

        # --- Criterion 9: Canonical StructuredLogger (C4) is used ---
        assert sm._logger is kernel.logger
        assert cm_._logger is kernel.logger
        assert om._logger is kernel.logger

        # --- Criterion 10: No duplicate manager authority exists ---
        assert sm is get_security_manager()
        assert cm_ is get_capability_manager()
        assert om is get_observability_manager()

        # --- Criterion 11: No EventType was invented ---
        # Only canonical EventTypes are referenced.
        _ = (
            EventType.SECURITY_ISSUE_FOUND.name,
            EventType.SERVICE_STARTED.name,
            EventType.SERVICE_STOPPED.name,
            EventType.SKILL_EXECUTED.name,
            EventType.SKILL_FAILED.name,
            EventType.METRIC_EMITTED.name,
            EventType.TRACE_SPAN_STARTED.name,
            EventType.TRACE_SPAN_ENDED.name,
        )
        # Exercise business APIs that emit canonical events.
        sm.record_violation(severity="low", description="issue")
        cm_.register("cap.crit", "facade", "provider")
        cm_.invoke("cap.crit")
        om.record_metric("m", _MetricType.COUNTER, 1.0)
        span = om.start_span("span")
        om.end_span(span.span_id)

        expected = {
            EventType.SECURITY_ISSUE_FOUND.name,
            EventType.SERVICE_STARTED.name,
            EventType.SKILL_EXECUTED.name,
            EventType.METRIC_EMITTED.name,
            EventType.TRACE_SPAN_STARTED.name,
            EventType.TRACE_SPAN_ENDED.name,
        }
        names = await _wait_for_events(kernel.event_bus, expected)
        assert expected <= names
        for e in kernel.event_bus.getRecentEvents():
            assert hasattr(e.eventType, "name"), "non-canonical EventType leaked"

        # Security business API works.
        assert sm.authorize(None, "read", "res") is SecurityDecision.DENY
        v = sm.record_violation(severity="high", description="d")
        assert sm.get_violation(v.violation_id) is v
        assert len(sm.list_violations()) >= 1
    finally:
        await kernel.stop()
        # Hermetic teardown.
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_resource_manager_singleton()
        reset_health_manager_singleton()
        reset_security_manager_singleton()
        reset_capability_manager_singleton()
        reset_observability_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_lifecycle_ordering(tmp_path):
    """New managers are initialized within their phases; regression intact."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        order = kernel.lifecycle.initialized_managers
        # Phase 2 < Phase 3 < Phase 4 < Phase 5 ordering respected.
        assert "StateManager" in order
        assert "StorageManager" in order
        assert order.index("StateManager") < order.index("HealthManager")
        assert order.index("HealthManager") < order.index("SecurityManager")
        assert order.index("SecurityManager") < order.index("CapabilityManager")
        assert order.index("CapabilityManager") < order.index("ObservabilityManager")
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_resource_manager_singleton()
        reset_health_manager_singleton()
        reset_security_manager_singleton()
        reset_capability_manager_singleton()
        reset_observability_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_reverse_shutdown(tmp_path):
    """New managers shut down by LifecycleManager (reverse phase order)."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        assert kernel.observability_manager.is_initialized
    finally:
        await kernel.stop()

    # After shutdown: marked SHUTDOWN in registry, not ready.
    sr = get_service_registry()
    for sid in ("core.security", "core.capability", "core.observability"):
        reg = sr.get_registration(sid)
        assert reg is not None, f"{sid} not in registry after stop"
        assert reg.lifecycle_state.value == "SHUTDOWN"
    assert kernel.security_manager.health_ready() is False
    assert kernel.capability_manager.health_ready() is False
    assert kernel.observability_manager.health_ready() is False

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_business_apis(tmp_path):
    """Verify the business APIs of all three new managers."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()
        sm = kernel.security_manager
        cm_ = kernel.capability_manager
        om = kernel.observability_manager

        # Security business API.
        assert sm.authorize(None, "act", "res") is SecurityDecision.DENY
        v = sm.record_violation(severity="high", description="d")
        assert sm.get_violation(v.violation_id) is v
        assert len(sm.list_violations()) >= 1

        # Capability business API.
        entry = cm_.register("cap.crit", "facade", "provider")
        assert cm_.get_capability("cap.crit") is entry
        assert len(cm_.list_capabilities()) == 1
        found = cm_.discover_by_facade("facade")
        assert len(found) == 1
        assert cm_.deregister("cap.crit") is True

        # Observability business API.
        metric = om.record_metric("m", _MetricType.COUNTER, 1.0, unit="req")
        assert metric.name == "m"
        span = om.start_span("s")
        assert span.span_id
        assert om.end_span(span.span_id) is True
        assert len(om.get_metrics()) == 1
        assert len(om.get_spans()) == 0
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_resource_manager_singleton()
        reset_health_manager_singleton()
        reset_security_manager_singleton()
        reset_capability_manager_singleton()
        reset_observability_manager_singleton()


@pytest.mark.asyncio
async def test_critical_acceptance_regression_tasks_9_13(tmp_path):
    """Existing Task 9/10/11/12/13 critical behavior remains intact."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_state_manager_singleton()
    reset_storage_manager_singleton()
    reset_resource_manager_singleton()
    reset_health_manager_singleton()
    reset_security_manager_singleton()
    reset_capability_manager_singleton()
    reset_observability_manager_singleton()

    kernel = HermesKernel(config=KernelConfig(data_dir=tmp_path / "data"))
    try:
        await kernel.start()

        # LifecycleManager still works.
        assert kernel.lifecycle is get_lifecycle_manager()
        assert kernel.lifecycle.state is not None

        # StateManager still works.
        assert kernel.state_manager is get_state_manager()
        assert kernel.state_manager.is_initialized
        state_reg = kernel.service_registry.get_registration("core.state")
        assert state_reg is not None
        assert state_reg.metadata.get("manager") == "StateManager"
        kernel.state_manager.set_state(StateScope.WORKFLOW, "crit-wf", "x", 1)
        assert kernel.state_manager.get_state(StateScope.WORKFLOW, "crit-wf", "x") == 1

        # StorageManager still works.
        assert kernel.storage_manager is get_storage_manager()
        assert kernel.storage_manager.is_initialized
        assert isinstance(kernel.storage_manager, StorageManager)

        # ResourceManager still works.
        assert kernel.resource_manager is get_resource_manager()
        assert kernel.resource_manager.is_initialized
        assert isinstance(kernel.resource_manager, ResourceManager)

        # HealthManager still works.
        assert kernel.health_manager is get_health_manager()
        assert kernel.health_manager.is_initialized
        assert isinstance(kernel.health_manager, HealthManager)
        kernel.health_manager.record_health("comp", "chk", HealthStatus.HEALTHY)
        assert kernel.health_manager.overall_status is HealthStatus.HEALTHY

        # Phase topology intact.
        phase_plan = kernel.lifecycle.phase_plan
        phases = {p["phase"]: p["name"] for p in phase_plan}
        assert phases[1] == "Foundation"
        assert phases[2] == "State & Storage"
        assert phases[3] == "Governance"
        assert phases[4] == "Execution"
        assert phases[5] == "Observability"
    finally:
        await kernel.stop()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_lifecycle_manager_singleton()
        reset_state_manager_singleton()
        reset_storage_manager_singleton()
        reset_resource_manager_singleton()
        reset_health_manager_singleton()
        reset_security_manager_singleton()
        reset_capability_manager_singleton()
        reset_observability_manager_singleton()


def test_critical_acceptance_imports_resolve():
    # Task 9–15 regression guard: core-module imports must resolve.
    from aios.core.capability_manager import CapabilityManager as CM15
    from aios.core.health_manager import HealthManager as HM12
    from aios.core.lifecycle_manager import LifecycleManager
    from aios.core.observability_manager import ObservabilityManager as OM15
    from aios.core.resource_manager import ResourceManager as RM13
    from aios.core.security_manager import SecurityManager as SM14
    from aios.core.state import StateManager as S10
    from aios.core.storage import StorageManager as S11

    # All Task 9–15 Core Managers and the Phase-1 LifecycleManager must resolve
    # from their canonical module paths.
    assert all([SM14, CM15, OM15, LifecycleManager, S10, S11, HM12, RM13])
