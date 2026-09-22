"""
Provider-agnostic model discovery contract for AI-OS.

Defines the minimal interface that providers can implement to support
dynamic model discovery. Providers that do not support discovery can
still register models statically through the ModelCatalog.

This module ensures:
- Discovery failure is represented safely (not an exception)
- Credentials are never exposed during discovery
- Static and dynamic discovery can coexist
- Provider-specific implementation details remain hidden
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from aios.core.model_types import ModelCapability, ModelMetadata, ModelStatus

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """
    Result of a model discovery attempt.

    Represents either a successful discovery with models or a safe
    failure indication that allows the system to continue operating
    with static model configurations.
    """

    success: bool
    models: list[ModelMetadata] | None = None
    error: str | None = None
    provider_id: str | None = None
    discovered_at: str | None = None

    @property
    def has_models(self) -> bool:
        """Check if discovery returned any models."""
        return self.success and self.models is not None and len(self.models) > 0

    @property
    def is_failure(self) -> bool:
        """Check if discovery failed."""
        return not self.success

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "success": self.success,
            "provider_id": self.provider_id,
            "discovered_at": self.discovered_at,
        }

        if self.has_models:
            result["model_count"] = len(self.models)
            result["models"] = [m.to_dict() for m in self.models]

        if self.is_failure and self.error:
            result["error"] = self.error

        return result


@runtime_checkable
class DiscoverableProvider(Protocol):
    """
    Protocol for providers that support dynamic model discovery.

    Providers implementing this protocol can discover available models
    without exposing credentials or implementation details.
    """

    async def discover_models(self) -> list[ModelMetadata]:
        """
        Discover available models for this provider.

        Returns:
            List of discovered model metadata (may be empty).

        Raises:
            NotImplementedError: If provider does not support discovery.
            RuntimeError: If discovery fails due to authentication or connectivity issues.
        """
        ...


class BaseDiscoveryClient(ABC):
    """
    Base class for model discovery clients.

    Provides a standard interface for discovering models from providers.
    Subclasses implement provider-specific discovery logic while
    maintaining the contract for safe error handling.
    """

    def __init__(self, provider_id: str):
        """
        Initialize discovery client.

        Args:
            provider_id: Identifier of the provider being discovered
        """
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        """Get the provider ID."""
        return self._provider_id

    async def discover(self) -> DiscoveryResult:
        """
        Perform model discovery.

        Returns:
            DiscoveryResult with models or error information.
        """
        try:
            models = await self._discover_models_impl()
            return DiscoveryResult(
                success=True,
                models=models,
                provider_id=self._provider_id,
            )
        except NotImplementedError:
            logger.debug(
                "Provider %s does not support dynamic discovery", self._provider_id
            )
            return DiscoveryResult(
                success=False,
                error="Discovery not supported by provider",
                provider_id=self._provider_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Model discovery failed for provider %s: %s",
                self._provider_id,
                exc,
            )
            return DiscoveryResult(
                success=False,
                error=str(exc),
                provider_id=self._provider_id,
            )

    @abstractmethod
    async def _discover_models_impl(self) -> list[ModelMetadata]:
        """
        Implementation of model discovery.

        Must be implemented by subclasses to perform provider-specific
        discovery logic. Should not expose credentials.

        Returns:
            List of discovered ModelMetadata instances.

        Raises:
            NotImplementedError: If discovery is not supported.
        """
        ...


class NoOpDiscoveryClient(BaseDiscoveryClient):
    """
    Discovery client for providers that don't support dynamic discovery.

    Always returns an empty result without errors, allowing the system
    to fall back to static model configurations.
    """

    async def _discover_models_impl(self) -> list[ModelMetadata]:
        """Return empty list for providers without discovery support."""
        raise NotImplementedError(
            f"Provider {self._provider_id} does not support dynamic discovery"
        )


class StaticDiscoveryClient(BaseDiscoveryClient):
    """
    Discovery client that returns pre-configured static models.

    Useful for providers that have a fixed set of models or for testing.
    """

    def __init__(
        self,
        provider_id: str,
        static_models: list[ModelMetadata] | None = None,
    ):
        """
        Initialize static discovery client.

        Args:
            provider_id: Identifier of the provider
            static_models: Optional list of static models to return
        """
        super().__init__(provider_id)
        self._static_models = static_models or []

    async def _discover_models_impl(self) -> list[ModelMetadata]:
        """Return static models."""
        return self._static_models.copy()


__all__ = [
    "DiscoveryResult",
    "DiscoverableProvider",
    "BaseDiscoveryClient",
    "NoOpDiscoveryClient",
    "StaticDiscoveryClient",
]
