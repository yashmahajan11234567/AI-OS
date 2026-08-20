"""
Task 9 Critical Acceptance Test (read-only verification).
"""
from __future__ import annotations

import asyncio

import pytest

from aios.core.configuration_manager import get_configuration_manager
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.lifecycle_manager import (
    get_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.core.structured_logger import get_logger
from aios.events.bus import get_event_bus
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.services.registry import get_service_registry as legacy_get_sr


@pytest.mark.asyncio
async def test_critical_acceptance_identities():
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_lifecycle_manager_singleton()

    kernel = HermesKernel(config=KernelConfig())
    try:
        await kernel.start()
        assert kernel.event_bus is get_event_bus()
        assert kernel.event_bus is get_core_event_bus()
        assert kernel.service_registry is get_service_registry()
        assert kernel.service_registry is legacy_get_sr()
        assert kernel.lifecycle._event_bus is kernel.event_bus
        assert kernel.lifecycle._service_registry is kernel.service_registry
        assert kernel.lifecycle._logger is kernel.logger
        assert kernel.configuration is get_configuration_manager()
        assert kernel.logger is get_logger()
        assert kernel.lifecycle is get_lifecycle_manager()
    finally:
        await kernel.stop()
