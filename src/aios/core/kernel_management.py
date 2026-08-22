"""
Kernel Management for AI-OS Hermes Kernel.

Provides functions to start, stop, and manage the kernel lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from aios.core import HermesKernel, KernelConfig
from aios.config.loader import load_config

# Import singleton reset functions for all core components and managers
from aios.events.core.bus import reset_event_bus_singleton as reset_core_event_bus_singleton
from aios.core.service_registry import reset_service_registry_singleton as reset_core_service_registry_singleton
from aios.core.configuration_manager import reset_configuration_manager_singleton
from aios.core.structured_logger import reset_structured_logger_singleton
from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
from aios.core.state import reset_state_manager_singleton
from aios.core.storage import reset_storage_manager_singleton
from aios.core.workflow import reset_workflow_manager_singleton
from aios.core.resource_manager import reset_resource_manager_singleton
from aios.core.health_manager import reset_health_manager_singleton
from aios.core.security_manager import reset_security_manager_singleton
from aios.core.capability_manager import reset_capability_manager_singleton
from aios.core.observability_manager import reset_observability_manager_singleton
from aios.core.checkpoint import set_checkpoint_manager

logger = logging.getLogger(__name__)

# Global kernel instance
_kernel: HermesKernel | None = None


async def run_kernel(config: KernelConfig | None = None) -> HermesKernel:
    """
    Start the Hermes Kernel.

    Args:
        config: Optional kernel configuration

    Returns:
        Started HermesKernel instance
    """
    global _kernel

    if _kernel and _kernel._running:
        logger.warning("Kernel already running")
        return _kernel

    # Load config if not provided
    if config is None:
        config = KernelConfig()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load app config
    app_config = None
    if config.config_path:
        try:
            app_config = load_config(config.config_path)
        except Exception as e:
            logger.warning(f"Failed to load app config: {e}")

    # Create kernel
    _kernel = HermesKernel(
        config=config,
        app_config=app_config,
    )

    # Start kernel
    await _kernel.start()

    logger.info("Hermes Kernel started successfully")
    return _kernel


async def stop_kernel() -> None:
    """Stop the Hermes Kernel and reset all singletons for test isolation."""
    global _kernel

    if _kernel and _kernel._running:
        await _kernel.stop()
        _kernel = None
        logger.info("Hermes Kernel stopped")
    else:
        logger.warning("Kernel not running")

    # Reset all canonical singletons to ensure test isolation
    # Order: managers first (reverse phase order), then core components
    reset_observability_manager_singleton()
    reset_capability_manager_singleton()
    reset_security_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()
    reset_workflow_manager_singleton()
    reset_storage_manager_singleton()
    reset_state_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()
    reset_core_service_registry_singleton()
    reset_core_event_bus_singleton()

    # Also reset checkpoint manager if it exists
    set_checkpoint_manager(None)


def get_kernel() -> HermesKernel | None:
    """Get the current kernel instance."""
    return _kernel


def is_running() -> bool:
    """Check if kernel is running."""
    return _kernel is not None and _kernel._running


async def create_kernel(config: KernelConfig | None = None) -> HermesKernel:
    """
    Create a kernel instance without starting it.

    Args:
        config: Optional kernel configuration

    Returns:
        HermesKernel instance
    """
    if config is None:
        config = KernelConfig()

    app_config = None
    if config.config_path:
        try:
            app_config = load_config(config.config_path)
        except Exception as e:
            logger.warning(f"Failed to load app config: {e}")

    return HermesKernel(config=config, app_config=app_config)


async def execute_with_kernel(
    func: Any,
    config: KernelConfig | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Execute a function with a kernel lifecycle.

    Args:
        func: Async function to execute
        config: Optional kernel configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func
    """
    kernel = await run_kernel(config)
    try:
        return await func(kernel, *args, **kwargs)
    finally:
        await stop_kernel()


__all__ = [
    "run_kernel",
    "stop_kernel",
    "get_kernel",
    "is_running",
    "create_kernel",
    "execute_with_kernel",
]