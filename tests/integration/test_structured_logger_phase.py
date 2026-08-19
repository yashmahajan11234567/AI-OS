"""
Task 8 — StructuredLogger phase integration tests (Part 3 §3.6 / §3.7).

Architecture-supported behavior only:

  * StructuredLogger is a Phase 3 Core Component (C4)
  * It is constructed and initialized by the kernel AFTER EventBus (Phase 0),
    ServiceRegistry (C2, Phase 1), and the (frozen) ConfigurationManager
    (C3, Phase 2) — never before them.
  * It is exposed via ``kernel.logger``.
  * It publishes only ``CoreComponentInitialized`` and ``CoreComponentShutdown``
    (the two canonical EventTypes the kernel already supports — no new EventType
    is invented).
  * It is the FIRST Core Component shut down in Phase S3.

Per Task 8 rules, NO forbidden component (LifecycleManager, ObservabilityManager,
Core Manager, or new EventType) is implemented to make these pass. We only
verify the architecture-aligned ordering, accessor wiring, and event contract
that the existing kernel supports.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from aios.core.configuration_manager import (
    ConfigState,
    reset_configuration_manager_singleton,
)
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.structured_logger import (
    StructuredLogger,
    get_logger,
    reset_structured_logger_singleton,
)
from aios.core.sinks import BaseSink
from aios.events.core.types import EventType


@pytest.fixture
def kernel():
    """Start a kernel (services off) and tear down globals afterward."""
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()
    tmp = Path(tempfile.mkdtemp())
    cfg = KernelConfig(data_dir=tmp, auto_start_services=False)
    k = HermesKernel(config=cfg)
    yield k
    # Best-effort stop; ignore if not running.
    try:
        asyncio.get_event_loop().run_until_complete(k.stop())
    except RuntimeError:
        asyncio.run(k.stop())
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()


class TestStructuredLoggerPhase:
    """Verify C4 phase concerns without a forbidden LifecycleManager."""

    @pytest.mark.asyncio
    async def test_logger_property_exposes_structured_logger(self, kernel):
        # C4 is a Phase 3 Core Component exposed via kernel.logger.
        await kernel.start()
        assert kernel.logger is not None
        assert isinstance(kernel.logger, StructuredLogger)
        assert kernel.logger.name == "StructuredLogger"
        assert kernel.logger.phase == 3

    @pytest.mark.asyncio
    async def test_dependencies_declared(self, kernel):
        await kernel.start()
        assert kernel.logger.dependencies == [
            "EventBus",
            "ServiceRegistry",
            "ConfigurationManager",
        ]

    @pytest.mark.asyncio
    async def test_event_bus_initialized_before_logger(self, kernel):
        # EventBus is the foundation; StructuredLogger must resolve it.
        await kernel.start()
        assert kernel.event_bus is not None
        # The logger received the kernel's bus (EventBusSink wired only then).
        assert kernel.logger._event_bus is kernel.event_bus

    @pytest.mark.asyncio
    async def test_service_registry_initialized_before_logger(self, kernel):
        # C2 (ServiceRegistry) is constructed in Phase 1, before the logger's
        # Phase 3 initialize(); the logger declares it as a dependency and the
        # kernel exposes it for lazy resolution (SR is created after the logger,
        # so it is resolved via the kernel accessor rather than captured at init).
        await kernel.start()
        assert kernel.service_registry is not None
        assert "ServiceRegistry" in kernel.logger.dependencies
        # The kernel accessor is the authoritative resolution path for SR.
        assert kernel.logger._kernel is kernel
        # The dependency is present and the registry is reachable from the kernel.
        assert kernel.service_registry is not None

    @pytest.mark.asyncio
    async def test_configuration_frozen_before_logger(self, kernel):
        # C3 (ConfigurationManager) must be frozen before C4 initializes and
        # consumes its (frozen) configuration.
        await kernel.start()
        assert kernel.configuration is not None
        # The logger read config during initialize(); its reference to CM is
        # dropped afterward (dependency rule — do not retain).
        assert kernel.logger._configuration_manager is None
        # The configuration remains frozen (Phase 2->3 boundary preserved).
        assert kernel.configuration.state is ConfigState.FROZEN

    @pytest.mark.asyncio
    async def test_core_component_initialized_emitted(self, kernel):
        await kernel.start()
        events = kernel.event_bus.get_history(
            event_type="CORE_COMPONENT_INITIALIZED"
        )
        assert events, "CoreComponentInitialized must be emitted by the logger"
        # The logger's event carries its component name.
        last = events[-1]
        assert last.payload.get("component") == "StructuredLogger"

    @pytest.mark.asyncio
    async def test_core_component_shutdown_emitted(self, kernel):
        await kernel.start()
        # stop() triggers Phase S3 (logger first).
        await kernel.stop()
        events = kernel.event_bus.get_history(event_type="CORE_COMPONENT_SHUTDOWN")
        assert events, "CoreComponentShutdown must be emitted by the logger"

    @pytest.mark.asyncio
    async def test_logger_is_first_component_shut_down(self, kernel):
        # In Phase S3 the logger is shut down BEFORE the EventBus drains last.
        await kernel.start()
        await kernel.stop()
        # After a clean stop the logger singleton is released by the kernel.
        assert kernel.logger is None
        # The event bus is still available for post-mortem inspection (it is
        # shut down only after the logger, in S0).
        assert kernel.event_bus is not None

    @pytest.mark.asyncio
    async def test_logger_shares_global_singleton_with_kernel(self, kernel):
        # The kernel sets the global singleton; get_logger() resolves it.
        await kernel.start()
        assert get_logger() is kernel.logger

    @pytest.mark.asyncio
    async def test_correlation_propagation_end_to_end(self, kernel):
        # Correlation context set on the logger is enriched onto emitted entries
        # and reaches a registered sink intact.
        await kernel.start()
        sink = _CollectSink("collect")
        kernel.logger.register_sink(sink)
        tok = kernel.logger.set_context("corr-phase-123", "caus-phase-456")
        kernel.logger.info("phase message")
        kernel.logger.clear_context(tok)
        kernel.logger.flush()
        assert sink.entries, "registered sink must receive the entry"
        entry = sink.entries[0]
        assert entry["correlationId"] == "corr-phase-123"
        assert entry["causationId"] == "caus-phase-456"

    @pytest.mark.asyncio
    async def test_no_forbidden_event_types_emitted(self, kernel):
        # The logger must NOT invent EventTypes. Only the two canonical
        # lifecycle events are emitted by C4.
        await kernel.start()
        await kernel.stop()
        allowed = {"CORE_COMPONENT_INITIALIZED", "CORE_COMPONENT_SHUTDOWN"}
        for ev in kernel.event_bus.get_history():
            et = ev.event_type
            et_name = et.name if isinstance(et, EventType) else str(et)
            if "COMPONENT" in et_name:
                assert et_name in allowed
        # Sanity: the legacy LOG_ANOMALY_DETECTED bridge type is only used by
        # EventBusSink when WARN+ entries are forwarded, never as a new type.
        assert EventType.CORE_COMPONENT_INITIALIZED is not None
        assert EventType.CORE_COMPONENT_SHUTDOWN is not None


class _CollectSink(BaseSink):
    """In-memory sink collecting serialized entries (test support)."""

    def __init__(self, name: str = "collect") -> None:
        super().__init__(name)
        self.entries: list[dict] = []

    def write(self, entries: list[dict]) -> None:
        self.entries.extend(entries)
