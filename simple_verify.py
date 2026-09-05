#!/usr/bin/env python3
"""Simple verification of M10-T3 key aspects."""

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

async def test_basic_functionality():
    print("Testing basic M10-T3 functionality...")

    # Reset all singletons
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
        # Test 1: Initial state
        assert kernel.health_state == CanonicalHealthState.STOPPED
        print("[PASS] Initial state is STOPPED")

        # Test 2: Start kernel
        await kernel.start()
        print("[PASS] Kernel started successfully")

        # Test 3: Check state after start
        state_after_start = kernel.health_state
        assert state_after_start in [CanonicalHealthState.RUNNING, CanonicalHealthState.READY]
        print(f"[PASS] State after start: {state_after_start.value}")

        # Test 4: Health file exists
        health_file = temp_dir / "kernel.health"
        assert health_file.exists()
        print("[PASS] Health file created")

        # Test 5: Health file content
        import json
        health_data = json.loads(health_file.read_text())
        assert "status" in health_data
        assert "timestamp" in health_data
        assert "alive" in health_data
        assert "ready" in health_data
        print("[PASS] Health file contains required fields")

        # Test 6: Liveness check
        assert kernel.is_alive == True
        print("[PASS] Liveness check returns True")

        # Test 7: Stop kernel
        await kernel.stop()
        print("[PASS] Kernel stopped successfully")

        # Test 8: Final state
        assert kernel.health_state == CanonicalHealthState.STOPPED
        print("[PASS] Final state is STOPPED")

        print("\n[INFO] All basic functionality tests PASSED!")

    except Exception as e:
        print(f"\n[FAIL] Test FAILED: {e}")
        raise
    finally:
        # Cleanup
        try:
            await kernel.stop()
        except:
            pass
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())