"""Engineering Services for AI-OS.

This package contains the Service Framework and all Engineering Services.
Services are event-driven: they subscribe to events on the shared EventBus
and emit completion/failure events. They never call each other directly.
"""

from aios.services.base import BaseService, ServiceStatus, ServiceInfo
from aios.services.registry import (
    ServiceRegistry,
    ServiceNotFoundError,
    get_service_registry,
    set_service_registry,
)

__all__ = [
    "BaseService",
    "ServiceStatus",
    "ServiceInfo",
    "ServiceRegistry",
    "ServiceNotFoundError",
    "get_service_registry",
    "set_service_registry",
]