"""
Provider-agnostic model catalog for AI-OS.

Manages model metadata independently of provider lifecycle, allowing
providers to register/unregister models and enabling the ModelRouter
to access model capabilities and availability information.

Responsibilities:
- Registering/unregistering models
- Retrieving model metadata
- Listing models by various criteria
- Maintaining model availability/status
- Thread-safe concurrent access

The ModelCatalog works alongside ProviderRegistry:
- ProviderRegistry = provider lifecycle/health
- ModelCatalog = model metadata/availability
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from aios.core.model_types import ModelMetadata, ModelStatus


@dataclass
class CatalogStats:
    """Statistics about the model catalog."""

    total_models: int = 0
    models_by_provider: dict[str, int] = field(default_factory=dict)
    available_models: int = 0
    unavailable_models: int = 0
    last_updated: str | None = None


class ModelCatalog:
    """
    Provider-agnostic model metadata catalog.

    Maintains a thread-safe registry of model metadata that can be
    queried independently of provider instances. Enables the ModelRouter
    to make informed routing decisions based on model capabilities,
    availability, and other metadata without requiring live provider
    connections.

    The catalog is intentionally separate from ProviderRegistry to
    maintain clear separation of concerns:
    - ProviderRegistry manages provider instances and health
    - ModelCatalog manages model metadata and availability
    """

    def __init__(self):
        """Initialize an empty model catalog."""
        self._lock = threading.RLock()
        self._models: dict[str, ModelMetadata] = {}  # model_id -> ModelMetadata
        self._by_provider: dict[str, set[str]] = {}  # provider_id -> set of model_ids
        self._stats = CatalogStats()
        self._update_stats()

    def register_model(self, model: ModelMetadata) -> bool:
        """
        Register a model in the catalog.

        Args:
            model: Model metadata to register

        Returns:
            True if model was registered, False if it already existed
            with the same model_id

        Thread-safe: Yes.
        """
        with self._lock:
            if model.model_id in self._models:
                return False

            self._models[model.model_id] = model
            if model.provider_id not in self._by_provider:
                self._by_provider[model.provider_id] = set()
            self._by_provider[model.provider_id].add(model.model_id)

            self._update_stats()
            return True

    def unregister_model(self, model_id: str) -> bool:
        """
        Unregister a model from the catalog.

        Args:
            model_id: Identifier of the model to remove

        Returns:
            True if model was found and removed, False if not found

        Thread-safe: Yes.
        """
        with self._lock:
            if model_id not in self._models:
                return False

            model = self._models[model_id]
            del self._models[model_id]

            if model.provider_id in self._by_provider:
                self._by_provider[model.provider_id].discard(model_id)
                if not self._by_provider[model.provider_id]:
                    del self._by_provider[model.provider_id]

            self._update_stats()
            return True

    def get_model(self, model_id: str) -> ModelMetadata | None:
        """
        Retrieve model metadata by ID.

        Args:
            model_id: Identifier of the model to retrieve

        Returns:
            ModelMetadata if found, None otherwise

        Thread-safe: Yes.
        """
        with self._lock:
            return self._models.get(model_id)

    def list_models(self) -> list[ModelMetadata]:
        """
        List all registered models.

        Returns:
            List of all ModelMetadata instances (copy to prevent external modification)

        Thread-safe: Yes.
        """
        with self._lock:
            return list(self._models.values())

    def list_models_by_provider(self, provider_id: str) -> list[ModelMetadata]:
        """
        List all models for a specific provider.

        Args:
            provider_id: Identifier of the provider

        Returns:
            List of ModelMetadata instances for the provider

        Thread-safe: Yes.
        """
        with self._lock:
            if provider_id not in self._by_provider:
                return []
            model_ids = self._by_provider[provider_id]
            return [
                self._models[mid] for mid in model_ids if mid in self._models
            ]

    def get_models_by_capability(self, capability: str) -> list[ModelMetadata]:
        """
        List models that support a specific capability.

        Args:
            capability: Capability to filter by (as string matching ModelCapability enum)

        Returns:
            List of ModelMetadata instances that support the capability

        Thread-safe: Yes.
        """
        with self._lock:
            return [
                model
                for model in self._models.values()
                if any(c.value == capability for c in model.capabilities)
            ]

    def get_available_models(self) -> list[ModelMetadata]:
        """
        List all currently available models.

        Returns:
            List of ModelMetadata instances with status AVAILABLE

        Thread-safe: Yes.
        """
        with self._lock:
            return [
                model
                for model in self._models.values()
                if model.status == ModelStatus.AVAILABLE
            ]

    def is_model_available(self, model_id: str) -> bool:
        """
        Check if a specific model is available.

        Args:
            model_id: Identifier of the model to check

        Returns:
            True if model exists and is available, False otherwise

        Thread-safe: Yes.
        """
        with self._lock:
            model = self._models.get(model_id)
            return model is not None and model.status == ModelStatus.AVAILABLE

    def update_model_metadata(self, model_id: str, **kwargs: Any) -> bool:
        """
        Update metadata for an existing model.

        Args:
            model_id: Identifier of the model to update
            **kwargs: Fields to update on the model metadata

        Returns:
            True if model was found and updated, False if not found

        Thread-safe: Yes.
        """
        with self._lock:
            if model_id not in self._models:
                return False

            model = self._models[model_id]
            model.update(**kwargs)
            self._update_stats()
            return True

    def get_stats(self) -> CatalogStats:
        """
        Get catalog statistics.

        Returns:
            Copy of current catalog statistics

        Thread-safe: Yes.
        """
        with self._lock:
            # Return a copy to prevent external modification
            return CatalogStats(
                total_models=self._stats.total_models,
                models_by_provider=self._stats.models_by_provider.copy(),
                available_models=self._stats.available_models,
                unavailable_models=self._stats.unavailable_models,
                last_updated=self._stats.last_updated,
            )

    def clear(self) -> None:
        """
        Remove all models from the catalog.

        Primarily useful for testing.

        Thread-safe: Yes.
        """
        with self._lock:
            self._models.clear()
            self._by_provider.clear()
            self._update_stats()

    def _update_stats(self) -> None:
        """Update internal statistics (caller must hold lock)."""
        from datetime import UTC, datetime

        self._stats.total_models = len(self._models)
        self._stats.models_by_provider = {
            provider_id: len(model_ids)
            for provider_id, model_ids in self._by_provider.items()
        }
        self._stats.available_models = len(
            [m for m in self._models.values() if m.status == ModelStatus.AVAILABLE]
        )
        self._stats.unavailable_models = len(
            [
                m
                for m in self._models.values()
                if m.status != ModelStatus.AVAILABLE
            ]
        )
        self._stats.last_updated = datetime.now(UTC).isoformat()


__all__ = [
    "ModelCatalog",
    "CatalogStats",
]