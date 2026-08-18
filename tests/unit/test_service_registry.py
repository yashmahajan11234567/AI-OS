"""
Task 6 — ServiceRegistry unit tests (Part 3 §3.4).

These tests exercise the architecture-defined contract of Core Component C2:

  * ICoreComponent surface (name / phase / dependencies / initialize /
    shutdown / healthCheck)
  * registration (uniqueness, namespace, capability uniqueness, cycle rejection)
  * discovery (by id / type / capability / tag / composite query)
  * dependency topology (acyclic DAG, topological init / reverse shutdown plans)
  * lifecycle coordination (REGISTERED -> INITIALIZING -> RUNNING -> SHUTDOWN)
  * health tracking (DEGRADED / FAILED thresholds)
  * EventBus integration (event emission via the Task-5 bus)
  * thread safety / duplicates / invalid input

Per Task 6 rules, only canonical EventTypes (Task 2) are emitted; §3.4 event
names are mapped to them, and the tests assert on the canonical types emitted.
The bus is driven deterministically via ``await bus.drain()``.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.service_registry import (
    Capability,
    ServiceLifecycleState,
    ServiceNamespace,
    ServiceRegistration,
    ServiceRegistry,
    ServiceRegistryError,
    ServiceRegistryState,
    ServiceType,
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.events.core import (
    EventBus,
    EventBusConfig,
    EventType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return b


@pytest.fixture
def registry(bus):
    reset_service_registry_singleton()
    reg = ServiceRegistry(event_bus=bus)
    return reg




class _Service:
    """Minimal duck-typed service used by the tests.

    Acts as a SPY for the INV-SR-STR-006 regression test: it records whether
    any lifecycle method (initialize/start/shutdown/stop) was ever invoked.
    The corrected ServiceRegistry must NEVER call these — that ownership
    belongs to the future LifecycleManager.
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.initialized = False
        self.started = False
        self.stopped = False
        self.shutdown_called = False
        self.health_ok = True
        # Recorded lifecycle invocations for the no-call regression test.
        self.lifecycle_calls: list[str] = []

    async def initialize(self) -> None:
        self.lifecycle_calls.append("initialize")
        self.initialized = True

    async def start(self) -> None:
        self.lifecycle_calls.append("start")
        self.started = True

    async def shutdown(self) -> None:
        self.lifecycle_calls.append("shutdown")
        self.shutdown_called = True

    async def stop(self) -> None:
        self.lifecycle_calls.append("stop")
        self.stopped = True

    async def health_check(self) -> bool:
        return self.health_ok


# ---------------------------------------------------------------------------
# 1. construction / ICoreComponent surface
# ---------------------------------------------------------------------------


def test_construction(registry):
    assert isinstance(registry, ServiceRegistry)
    assert registry.name == "ServiceRegistry"
    assert registry.phase == 1
    assert registry.dependencies == ["EventBus"]
    assert registry.state is ServiceRegistryState.UNINITIALIZED


def test_singleton_enforced():
    reset_service_registry_singleton()
    first = get_service_registry(event_bus=None)
    second = get_service_registry(event_bus=None)
    # The accessor returns the same singleton instance.
    assert second is first
    reset_service_registry_singleton()


def test_double_instance_rejected():
    reset_service_registry_singleton()
    ServiceRegistry(event_bus=None)
    # A second DISTINCT instance construction must be rejected (INV-SR-STR-001).
    with pytest.raises(RuntimeError):
        ServiceRegistry(event_bus=None)
    reset_service_registry_singleton()


@pytest.mark.asyncio
async def test_initialize_transitions_to_running(registry, bus):
    await bus.initialize()
    assert await registry.initialize() is ServiceRegistryState.RUNNING
    assert registry.state is ServiceRegistryState.RUNNING


@pytest.mark.asyncio
async def test_shutdown_transitions_to_shutdown(registry, bus):
    await bus.initialize()
    await registry.initialize()
    assert await registry.shutdown() is ServiceRegistryState.SHUTDOWN
    assert registry.state is ServiceRegistryState.SHUTDOWN


# ---------------------------------------------------------------------------
# 2. ICoreComponent / healthCheck
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_operational_after_initialize(registry, bus):
    await bus.initialize()
    h = registry.healthCheck()
    assert h.healthy is False  # UNINITIALIZED
    await registry.initialize()
    h = registry.healthCheck()
    assert h.healthy is True
    assert h.state is ServiceRegistryState.RUNNING
    assert h.total_services == 0


def test_healthcheck_shape(registry):
    h = registry.healthCheck()
    assert set(h.to_dict().keys()) >= {
        "healthy",
        "state",
        "total_services",
        "running_services",
        "degraded_services",
        "failed_services",
    }


# ---------------------------------------------------------------------------
# 3. registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_and_discover(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Alpha")
    reg = await registry.register(svc)
    assert isinstance(reg, ServiceRegistration)
    assert reg.service_id == "engineering.Alpha"
    assert registry.get_service("engineering.Alpha") is svc
    assert "engineering.Alpha" in registry
    assert len(registry) == 1


@pytest.mark.asyncio
async def test_register_with_explicit_fields(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Beta")
    reg = await registry.register(
        svc,
        service_type=ServiceType.APPLICATION,
        depends_on=[],
        capabilities=[Capability(name="cap.x", version="1.0.0")],
        critical=True,
        tags=["t1"],
    )
    assert reg.service_type is ServiceType.APPLICATION
    assert reg.critical is True
    assert reg.capabilities[0].name == "cap.x"
    assert reg.tags == ["t1"]


@pytest.mark.asyncio
async def test_register_accepts_registration_object(registry, bus):
    await bus.initialize()
    await registry.initialize()
    reg_in = ServiceRegistration(
        service=_Service("facade.Gamma"),
        service_id="facade.Gamma",
        service_type=ServiceType.CAPABILITY_FACADE,
    )
    reg = await registry.register(reg_in)
    assert reg.service_id == "facade.Gamma"
    assert registry.get_services_by_type(ServiceType.CAPABILITY_FACADE)


# ---------------------------------------------------------------------------
# 4. duplicate registration (SR-REG-001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_registration_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.Dup"))
    with pytest.raises(ServiceRegistryError):
        await registry.register(_Service("engineering.Dup"))


# ---------------------------------------------------------------------------
# 5. namespace validation (INV-SR-NS-001/002)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registration_requires_namespace_prefix(registry, bus):
    await bus.initialize()
    await registry.initialize()
    with pytest.raises(ServiceRegistryError):
        await registry.register(_Service("NoPrefix"))


@pytest.mark.asyncio
async def test_kernel_namespace_reserved(registry, bus):
    await bus.initialize()
    await registry.initialize()
    with pytest.raises(ServiceRegistryError):
        await registry.register(_Service("kernel.Evil"))


# ---------------------------------------------------------------------------
# 6. capability uniqueness (SR-CAP-002)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_capability_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(
        _Service("engineering.A"), capabilities=[Capability(name="shared.cap")]
    )
    with pytest.raises(ServiceRegistryError):
        await registry.register(
            _Service("engineering.B"), capabilities=[Capability(name="shared.cap")]
        )


# ---------------------------------------------------------------------------
# 7. discovery (§3.4.5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discovery_by_type_capability_tag(registry, bus):
    await bus.initialize()
    await registry.initialize()
    a = _Service("engineering.A")
    b = _Service("application.B")
    await registry.register(
        a,
        service_type=ServiceType.ENGINEERING,
        capabilities=[Capability(name="cap.search")],
        tags=["search"],
    )
    await registry.register(
        b, service_type=ServiceType.APPLICATION, tags=["search"]
    )
    assert registry.get_services_by_type(ServiceType.ENGINEERING) == [a]
    assert registry.get_services_by_capability("cap.search") == [a]
    assert set(registry.get_services_by_tag("search")) == {a, b}
    assert set(registry.get_all_services()) == {a, b}
    # composite query: type ∩ capability ∩ tag
    assert registry.query(service_type=ServiceType.APPLICATION, tag="search") == [b]


@pytest.mark.asyncio
async def test_discovery_hides_failed_services(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Hidden")
    await registry.register(svc)
    with registry._lock:
        registry._registrations["engineering.Hidden"].lifecycle_state = (
            ServiceLifecycleState.FAILED
        )
    assert registry.get_service("engineering.Hidden") is None  # INV-SR-DISC-003


# ---------------------------------------------------------------------------
# 8. dependency topology / cycle detection (SR-REG-003)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_topology_and_plan(registry, bus):
    await bus.initialize()
    await registry.initialize()
    # db <- svc <- api  (api depends on svc, svc depends on db)
    await registry.register(_Service("engineering.db"))
    await registry.register(_Service("engineering.svc"), depends_on=["engineering.db"])
    await registry.register(
        _Service("engineering.api"),
        depends_on=["engineering.svc", "engineering.db"],
    )
    plan = registry.compute_initialization_plan()
    # Flatten and verify dependency-before-dependent ordering.
    flat = [sid for batch in plan for sid in batch]
    assert flat.index("engineering.db") < flat.index("engineering.svc")
    assert flat.index("engineering.svc") < flat.index("engineering.api")
    assert plan[0] == ["engineering.db"]


@pytest.mark.asyncio
async def test_missing_dependency_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.a"), depends_on=["engineering.missing"])
    with pytest.raises(ServiceRegistryError):
        registry.compute_initialization_plan()


@pytest.mark.asyncio
async def test_cycle_detection_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.x"), depends_on=["engineering.y"])
    with pytest.raises(ServiceRegistryError):
        await registry.register(_Service("engineering.y"), depends_on=["engineering.x"])


@pytest.mark.asyncio
async def test_reverse_shutdown_plan(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.db"))
    await registry.register(_Service("engineering.svc"), depends_on=["engineering.db"])
    init = registry.compute_initialization_plan()
    sd = registry.compute_shutdown_plan()
    assert sd == list(reversed(init))  # INV-SR-STR-005


# ---------------------------------------------------------------------------
# 9. lifecycle coordination (state recording only — INV-SR-STR-006 / INV-SR-OWN-003)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifecycle_state_recording_without_service_invocation(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Life")
    await registry.register(svc)

    # ServiceRegistry only RECORDS the transition; the service is never called.
    await registry.mark_service_initializing("engineering.Life")
    assert (
        registry.get_registration("engineering.Life").lifecycle_state
        is ServiceLifecycleState.INITIALIZING
    )
    await registry.mark_service_running("engineering.Life")
    assert (
        registry.get_registration("engineering.Life").lifecycle_state
        is ServiceLifecycleState.RUNNING
    )
    assert svc.lifecycle_calls == []  # no initialize/start/shutdown/stop called

    await registry.mark_service_shutting_down("engineering.Life")
    assert (
        registry.get_registration("engineering.Life").lifecycle_state
        is ServiceLifecycleState.SHUTTING_DOWN
    )
    await registry.mark_service_shutdown("engineering.Life")
    assert (
        registry.get_registration("engineering.Life").lifecycle_state
        is ServiceLifecycleState.SHUTDOWN
    )
    assert svc.lifecycle_calls == []  # nothing invoked throughout

    # ServiceInitialized (RUNNING) and ServiceShutdown events were emitted.
    await bus.drain()
    assert len(bus.getEventsByType(EventType.SERVICE_STARTED)) >= 1
    assert len(bus.getEventsByType(EventType.SERVICE_STOPPED)) >= 1


@pytest.mark.asyncio
async def test_mark_service_records_initializing_then_running_and_dependent_order(registry, bus):
    await bus.initialize()
    await registry.initialize()
    db = _Service("engineering.db")
    svc = _Service("engineering.svc")
    # register dependent first
    await registry.register(svc, depends_on=["engineering.db"])
    await registry.register(db)

    # db not RUNNING/REGISTERED enough (it IS registered, so dependent allowed
    # to *mark* initializing only if dependency is RUNNING/REGISTERED). db is
    # REGISTERED -> svc.mark_initializing is permitted by topology validation.
    await registry.mark_service_initializing("engineering.svc")
    await registry.mark_service_initializing("engineering.db")
    await registry.mark_service_running("engineering.db")
    await registry.mark_service_running("engineering.svc")

    assert (
        registry.get_registration("engineering.db").lifecycle_state
        is ServiceLifecycleState.RUNNING
    )
    assert (
        registry.get_registration("engineering.svc").lifecycle_state
        is ServiceLifecycleState.RUNNING
    )
    # Still, no service method was executed by the registry.
    assert db.lifecycle_calls == []
    assert svc.lifecycle_calls == []


@pytest.mark.asyncio
async def test_mark_service_failed_records_state_and_emits(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Fail")
    await registry.register(svc)
    await registry.mark_service_running("engineering.Fail")
    await registry.mark_service_failed("engineering.Fail", error="kaboom")
    assert (
        registry.get_registration("engineering.Fail").lifecycle_state
        is ServiceLifecycleState.FAILED
    )
    assert (
        registry.get_registration("engineering.Fail").last_error == "kaboom"
    )
    assert svc.lifecycle_calls == []  # ServiceRegistry did not invoke anything
    await bus.drain()
    assert len(bus.getEventsByType(EventType.SERVICE_FAILED)) >= 1


@pytest.mark.asyncio
async def test_registry_never_invokes_service_lifecycle_methods(registry, bus):
    """Regression test for INV-SR-STR-006.

    Exercises the fullregistry-surface used during normal operation and asserts
    that no service ``initialize``/``start``/``shutdown``/``stop`` method is ever
    called by ServiceRegistry. The future LifecycleManager owns execution; the
    registry only records/coordinates state.
    """
    await bus.initialize()
    await registry.initialize()

    db = _Service("engineering.db")
    svc = _Service("engineering.svc", version="2.0.0")
    api = _Service("application.api")
    await registry.register(db)
    await registry.register(svc, depends_on=["engineering.db"])
    await registry.register(api, depends_on=["engineering.svc", "engineering.db"])

    # Topology / planning APIs (authoritative) — no service calls expected.
    plan = registry.compute_initialization_plan()
    flat = [sid for batch in plan for sid in batch]
    assert flat.index("engineering.db") < flat.index("engineering.svc")
    assert flat.index("engineering.svc") < flat.index("application.api")

    # State-coordination APIs — record transitions, never execute services.
    for sid in flat:
        await registry.mark_service_initializing(sid)
        await registry.mark_service_running(sid)
    await registry.mark_service_failed("engineering.svc", error="x")
    await registry.mark_service_shutting_down("engineering.svc")
    await registry.mark_service_shutdown("engineering.svc")

    # Health tracking (only permitted healthCheck is the service's own poll;
    # registry does not call it here) — never a lifecycle method.
    await registry.update_health("engineering.db", True)

    # The definitive assertion: NO lifecycle method was ever invoked.
    for svc_obj in (db, svc, api):
        assert (
            svc_obj.lifecycle_calls == []
        ), f"ServiceRegistry invoked {svc_obj.lifecycle_calls} on {svc_obj.name}"



# ---------------------------------------------------------------------------
# 10. health tracking (§3.4.12)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_degraded_then_failed(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Health")
    await registry.register(svc)
    await registry.mark_service_running("engineering.Health")
    # 1st failure -> DEGRADED
    await registry.update_health("engineering.Health", False, error="boom")
    assert (
        registry.get_registration("engineering.Health").lifecycle_state
        is ServiceLifecycleState.DEGRADED
    )
    # 2nd failure -> still DEGRADED
    await registry.update_health("engineering.Health", False, error="boom")
    assert (
        registry.get_registration("engineering.Health").lifecycle_state
        is ServiceLifecycleState.DEGRADED
    )
    # 3rd failure -> FAILED (threshold)
    await registry.update_health("engineering.Health", False, error="boom")
    assert (
        registry.get_registration("engineering.Health").lifecycle_state
        is ServiceLifecycleState.FAILED
    )


@pytest.mark.asyncio
async def test_health_recovery(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.Health2")
    await registry.register(svc)
    await registry.mark_service_running("engineering.Health2")
    await registry.update_health("engineering.Health2", False, error="x")
    await registry.update_health("engineering.Health2", False, error="x")
    await registry.update_health("engineering.Health2", False, error="x")
    assert (
        registry.get_registration("engineering.Health2").lifecycle_state
        is ServiceLifecycleState.FAILED
    )
    await registry.update_health("engineering.Health2", True)
    assert (
        registry.get_registration("engineering.Health2").lifecycle_state
        is ServiceLifecycleState.RUNNING
    )


# ---------------------------------------------------------------------------
# 11. EventBus integration / events emitted (canonical EventTypes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_core_initialized_event_emitted(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await bus.drain()
    events = bus.getEventsByType(EventType.CORE_COMPONENT_INITIALIZED)
    assert len(events) == 1
    assert events[0].payload.to_dict()["name"] == "ServiceRegistry"


@pytest.mark.asyncio
async def test_shutdown_event_emitted(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await bus.drain()
    await registry.shutdown()
    await bus.drain()
    events = bus.getEventsByType(EventType.CORE_COMPONENT_SHUTDOWN)
    assert len(events) == 1
    assert events[0].payload.to_dict()["name"] == "ServiceRegistry"


@pytest.mark.asyncio
async def test_service_registered_event_emitted(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.Evt"))
    await bus.drain()
    # §3.4 ServiceRegistered -> canonical SERVICE_STARTED
    events = bus.getEventsByType(EventType.SERVICE_STARTED)
    assert any(
        e.payload.to_dict().get("service") == "engineering.Evt" for e in events
    )


@pytest.mark.asyncio
async def test_service_health_events_emitted(registry, bus):
    await bus.initialize()
    await registry.initialize()
    svc = _Service("engineering.HlthEvt")
    await registry.register(svc)
    await registry.mark_service_running("engineering.HlthEvt")
    await bus.drain()
    # healthy emission -> HEALTH_CHECK_PASSED
    await registry.update_health("engineering.HlthEvt", True)
    await bus.drain()
    assert len(bus.getEventsByType(EventType.HEALTH_CHECK_PASSED)) >= 1
    # failed -> SERVICE_FAILED after 3
    await registry.update_health("engineering.HlthEvt", False, error="x")
    await registry.update_health("engineering.HlthEvt", False, error="x")
    await registry.update_health("engineering.HlthEvt", False, error="x")
    await bus.drain()
    assert len(bus.getEventsByType(EventType.SERVICE_FAILED)) >= 1


# ---------------------------------------------------------------------------
# 12. shutdown ordering / registration after shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_after_shutdown_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.shutdown()
    with pytest.raises(ServiceRegistryError):
        await registry.register(_Service("engineering.Late"))


@pytest.mark.asyncio
async def test_shutdown_plan_respects_topology(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.db"))
    await registry.register(_Service("engineering.svc"), depends_on=["engineering.db"])
    plan = registry.compute_shutdown_plan()
    flat = [sid for batch in plan for sid in batch]
    # db (dependency) must shut down AFTER svc (dependent)
    assert flat.index("engineering.svc") < flat.index("engineering.db")


# ---------------------------------------------------------------------------
# 13. concurrency / thread safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_registration_unique(registry, bus):
    await bus.initialize()
    import threading

    await registry.initialize()

    def worker(i: int) -> None:
        try:
            asyncio.run(registry.register(_Service(f"engineering.T{i}")))
        except ServiceRegistryError:
            pass

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At most 20 distinct services (no duplicates, no corruption).
    assert len(registry) == 20
    # No internal inconsistency: every registered service is discoverable.
    for i in range(20):
        assert registry.get_service(f"engineering.T{i}") is not None


# ---------------------------------------------------------------------------
# 14. invalid input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_without_id_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()

    class _NoName:
        pass

    with pytest.raises(ServiceRegistryError):
        await registry.register(_NoName())


@pytest.mark.asyncio
async def test_unregister_with_dependents_rejected(registry, bus):
    await bus.initialize()
    await registry.initialize()
    await registry.register(_Service("engineering.db"))
    await registry.register(_Service("engineering.svc"), depends_on=["engineering.db"])
    with pytest.raises(ServiceRegistryError):
        registry.unregister("engineering.db")
    # dependent removed first -> then ok
    assert registry.unregister("engineering.svc") is True
    assert registry.unregister("engineering.db") is True


@pytest.mark.asyncio
async def test_capability_requires_name(registry, bus):
    await bus.initialize()
    await registry.initialize()
    with pytest.raises(ValueError):
        Capability(name="")


def test_service_namespace_enum_values():
    assert ServiceNamespace.KERNEL.value == "kernel"
    assert ServiceNamespace.ENGINEERING.value == "engineering"


@pytest.mark.asyncio
async def test_reset_singleton(registry, bus):
    await bus.initialize()
    reset_service_registry_singleton()
    fresh = ServiceRegistry(event_bus=None)
    assert fresh is not registry  # only because singleton was reset
    reset_service_registry_singleton()
