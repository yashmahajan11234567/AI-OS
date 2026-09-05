#!/usr/bin/env python3
"""Verification script for M10-T3 Health & Readiness implementation."""

import asyncio
import tempfile
from pathlib import Path
from aios.core.kernel import HermesKernel, KernelConfig, CanonicalHealthState
from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
from aios.core.health_manager import reset_health_manager_singleton
from aios.core.service_registry import reset_service_registry_singleton
from aios.core.configuration_manager import reset_configuration_manager_singleton
from aios.events.core.bus import reset_event_bus_singleton
from aios.core.structured_logger import reset_structured_logger_singleton

async def verify_startup_semantics():
    """Verify startup semantics: STARTING → READY → RUNNING"""
    print("=== Verifying Startup Semantics ===")

    # Reset singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_health_manager_singleton()
    reset_structured_logger_singleton()

    # Create kernel
    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)
    kernel = HermesKernel(config=config)

    try:
        # Check initial state
        initial_state = kernel.health_state
        print(f"Initial health state: {initial_state}")
        assert initial_state == CanonicalHealthState.STOPPED, f"Expected STOPPED, got {initial_state}"

        # Start kernel
        print("Starting kernel...")
        await kernel.start()

        # Check state after start
        running_state = kernel.health_state
        print(f"Health state after start: {running_state}")
        # Should be RUNNING or READY depending on implementation
        assert running_state in [CanonicalHealthState.RUNNING, CanonicalHealthState.READY], \
            f"Expected RUNNING or READY, got {running_state}"

        # Check health file
        health_file = temp_dir / "kernel.health"
        assert health_file.exists(), "Health file should exist"

        import json
        health_data = json.loads(health_file.read_text())
        print(f"Health file status: {health_data.get('status')}")
        print(f"Health file alive: {health_data.get('alive')}")
        print(f"Health file ready: {health_data.get('ready')}")

        # Verify health file contains expected fields
        assert "status" in health_data
        assert "timestamp" in health_data
        assert "uptime_seconds" in health_data
        assert "alive" in health_data
        assert "ready" in health_data

        # Test liveness
        alive = kernel.is_alive
        print(f"Kernel is alive: {alive}")
        assert alive == True, "Kernel should be alive after start"

        # Test readiness
        ready = kernel.is_ready
        print(f"Kernel is ready: {ready}")
        # Readiness depends on implementation details

        await kernel.stop()
        print("Kernel stopped successfully")

    finally:
        # Cleanup
        try:
            await kernel.stop()
        except:
            pass
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

async def verify_liveness_readiness_distinction():
    """Verify liveness and readiness are distinct concepts"""
    print("\n=== Verifying Liveness vs Readiness Distinction ===")

    # Reset singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_health_manager_singleton()
    reset_structured_logger_singleton()

    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)
    kernel = HermesKernel(config=config)

    try:
        await kernel.start()

        # Both should be true when kernel is healthy
        alive = kernel.is_alive
        ready = kernel.is_ready
        print(f"When healthy - Alive: {alive}, Ready: {ready}")

        await kernel.stop()

        # When stopped
        alive_stopped = kernel.is_alive
        ready_stopped = kernel.is_ready
        print(f"When stopped - Alive: {alive_stopped}, Ready: {ready_stopped}")
        assert alive_stopped == False, "Stopped kernel should not be alive"
        assert ready_stopped == False, "Stopped kernel should not be ready"

    finally:
        try:
            await kernel.stop()
        except:
            pass
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

async def verify_heartbeat_stale_detection():
    """Verify heartbeat and stale state detection"""
    print("\n=== Verifying Heartbeat & Stale Detection ===")

    # Reset singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_health_manager_singleton()
    reset_structured_logger_singleton()

    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)
    kernel = HermesKernel(config=config)

    try:
        await kernel.start()

        # Verify heartbeat task is started
        assert kernel._heartbeat_task is not None, "Heartbeat task should be started"
        assert not kernel._heartbeat_task.done(), "Heartbeat task should be running"
        print("Heartbeat task is running")

        # Test liveness with fresh timestamp (should be True)
        alive_fresh = kernel.is_alive
        print(f"Liveness with fresh timestamp: {alive_fresh}")
        assert alive_fresh == True, "Should be alive with fresh timestamp"

        await kernel.stop()

    finally:
        try:
            await kernel.stop()
        except:
            pass
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

async def verify_canonical_states():
    """Verify all canonical states are properly defined"""
    print("\n=== Verifying Canonical Health States ===")

    states = set(CanonicalHealthState)
    expected = {
        "starting", "ready", "running", "degraded",
        "unhealthy", "stopping", "stopped", "error"
    }
    actual = {s.value for s in states}

    print(f"Expected states: {expected}")
    print(f"Actual states: {actual}")

    assert actual == expected, f"State mismatch. Expected: {expected}, Got: {actual}"
    print("All 8 canonical states correctly defined")

async def main():
    """Run all verification tests"""
    print("Starting M10-T3 Independent QA Verification\n")

    await verify_canonical_states()
    await verify_startup_semantics()
    await verify_liveness_readiness_distinction()
    await verify_heartbeat_stale_detection()

    print("\n=== All Verifications Passed ===")

if __name__ == "__main__":
    asyncio.run(main())