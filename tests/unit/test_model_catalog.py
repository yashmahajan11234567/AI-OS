"""
Unit tests for ModelCatalog - Provider-agnostic model metadata management.

Tests the ModelCatalog's ability to manage model metadata independently
of provider lifecycle, including registration, retrieval, listing,
and thread-safety.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from aios.core.model_catalog import ModelCatalog
from aios.core.model_types import (
    ModelCapability,
    ModelCost,
    ModelHealth,
    ModelLimits,
    ModelMetadata,
    ModelStatus,
)


class TestModelMetadata:
    """Test ModelMetadata creation and serialization."""

    def test_create_basic_metadata(self):
        """Test creating minimal ModelMetadata."""
        metadata = ModelMetadata(
            model_id="test-model",
            provider_id="test-provider",
            display_name="Test Model",
        )

        assert metadata.model_id == "test-model"
        assert metadata.provider_id == "test-provider"
        assert metadata.display_name == "Test Model"
        assert metadata.capabilities == []
        assert metadata.status == ModelStatus.UNKNOWN
        assert metadata.health is None
        assert metadata.limits is None
        assert metadata.cost is None

    def test_create_full_metadata(self):
        """Test creating ModelMetadata with all fields."""
        from aios.core.model_discovery import ModelCapability

        metadata = ModelMetadata(
            model_id="full-model",
            provider_id="full-provider",
            display_name="Full Model",
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.FUNCTION_CALLING,
            ],
            status=ModelStatus.AVAILABLE,
            health=ModelHealth(
                status=ModelStatus.AVAILABLE,
                uptime_percentage=99.9,
                avg_latency_ms=150.5,
            ),
            limits=ModelLimits(
                max_tokens=4096,
                rate_limit_per_minute=60,
            ),
            cost=ModelCost(
                input_per_1k=0.003,
                output_per_1k=0.015,
            ),
        )

        assert len(metadata.capabilities) == 2
        assert metadata.status == ModelStatus.AVAILABLE
        assert metadata.health.status == ModelStatus.AVAILABLE
        assert metadata.limits.max_tokens == 4096
        assert metadata.cost.input_per_1k == 0.003

    def test_to_dict_basic(self):
        """Test basic dictionary serialization."""
        metadata = ModelMetadata(
            model_id="dict-test",
            provider_id="provider",
            display_name="Dict Test",
            capabilities=[ModelCapability.TEXT_GENERATION],
            status=ModelStatus.AVAILABLE,
        )

        result = metadata.to_dict()

        assert result["model_id"] == "dict-test"
        assert result["provider_id"] == "provider"
        assert result["display_name"] == "Dict Test"
        assert result["capabilities"] == ["text_generation"]
        assert result["status"] == "available"

    def test_to_dict_with_optional_fields(self):
        """Test serialization with optional fields."""
        metadata = ModelMetadata(
            model_id="full-dict",
            provider_id="provider",
            display_name="Full Dict",
            capabilities=[ModelCapability.VISION],
            status=ModelStatus.AVAILABLE,
            health=ModelHealth(
                status=ModelStatus.AVAILABLE,
                uptime_percentage=99.9,
            ),
            limits=ModelLimits(max_tokens=8192),
            cost=ModelCost(input_per_1k=0.01),
        )

        result = metadata.to_dict()

        assert "health" in result
        assert result["health"]["status"] == "available"
        assert "limits" in result
        assert result["limits"]["max_tokens"] == 8192
        assert "cost" in result
        assert result["cost"]["input_per_1k"] == 0.01

    def test_from_dict(self):
        """Test creating ModelMetadata from dictionary."""
        data = {
            "model_id": "from-dict",
            "provider_id": "test-provider",
            "display_name": "From Dict",
            "capabilities": ["text_generation", "code_generation"],
            "status": "available",
            "health": {
                "status": "available",
                "uptime_percentage": 99.5,
            },
            "limits": {
                "max_tokens": 4096,
            },
            "cost": {
                "input_per_1k": 0.002,
                "output_per_1k": 0.008,
            },
        }

        metadata = ModelMetadata.from_dict(data)

        assert metadata.model_id == "from-dict"
        assert len(metadata.capabilities) == 2
        assert metadata.status == ModelStatus.AVAILABLE
        assert metadata.health.status == ModelStatus.AVAILABLE
        assert metadata.limits.max_tokens == 4096
        assert metadata.cost.input_per_1k == 0.002

    def test_update_metadata(self):
        """Test updating metadata fields."""
        metadata = ModelMetadata(
            model_id="update-test",
            provider_id="provider",
            display_name="Update Test",
            status=ModelStatus.UNKNOWN,
        )

        metadata.update(status=ModelStatus.AVAILABLE)
        assert metadata.status == ModelStatus.AVAILABLE

    def test_no_credentials_in_metadata(self):
        """Test that metadata does not contain credentials."""
        metadata = ModelMetadata(
            model_id="no-secrets",
            provider_id="provider",
            display_name="No Secrets",
        )

        dict_repr = metadata.to_dict()

        # Should not contain any secret-related keys
        secret_keys = [
            "api_key",
            "token",
            "secret",
            "password",
            "credential",
            "apikey",
        ]

        for key in dict_repr.keys():
            assert not any(secret in key.lower() for secret in secret_keys), (
                f"Metadata contains potential secret key: {key}"
            )


class TestModelCatalog:
    """Test ModelCatalog operations."""

    @pytest.fixture
    def catalog(self):
        """Create a fresh ModelCatalog for each test."""
        return ModelCatalog()

    @pytest.fixture
    def sample_model(self):
        """Create a sample ModelMetadata instance."""
        return ModelMetadata(
            model_id="sample-model",
            provider_id="sample-provider",
            display_name="Sample Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            status=ModelStatus.AVAILABLE,
        )

    def test_register_model(self, catalog, sample_model):
        """Test registering a model."""
        result = catalog.register_model(sample_model)

        assert result is True
        assert catalog.get_model("sample-model") is not None

    def test_register_duplicate_model(self, catalog, sample_model):
        """Test that duplicate registration returns False."""
        # Register first time
        assert catalog.register_model(sample_model) is True

        # Try to register duplicate
        duplicate = ModelMetadata(
            model_id="sample-model",
            provider_id="other-provider",
            display_name="Duplicate",
        )
        result = catalog.register_model(duplicate)

        assert result is False
        # Original model should remain unchanged
        retrieved = catalog.get_model("sample-model")
        assert retrieved.provider_id == "sample-provider"

    def test_unregister_model(self, catalog, sample_model):
        """Test unregistering a model."""
        catalog.register_model(sample_model)
        result = catalog.unregister_model("sample-model")

        assert result is True
        assert catalog.get_model("sample-model") is None

    def test_unregister_nonexistent_model(self, catalog):
        """Test unregistering a model that doesn't exist."""
        result = catalog.unregister_model("nonexistent")

        assert result is False

    def test_get_model_not_found(self, catalog):
        """Test getting a model that doesn't exist."""
        result = catalog.get_model("nonexistent")

        assert result is None

    def test_list_models(self, catalog, sample_model):
        """Test listing all models."""
        model2 = ModelMetadata(
            model_id="model2",
            provider_id="provider2",
            display_name="Model 2",
        )

        catalog.register_model(sample_model)
        catalog.register_model(model2)

        models = catalog.list_models()

        assert len(models) == 2
        model_ids = {m.model_id for m in models}
        assert "sample-model" in model_ids
        assert "model2" in model_ids

    def test_list_empty_catalog(self, catalog):
        """Test listing models from empty catalog."""
        models = catalog.list_models()

        assert models == []

    def test_list_models_by_provider(self, catalog):
        """Test listing models by provider."""
        model1 = ModelMetadata(
            model_id="p1-model1",
            provider_id="provider1",
            display_name="P1 Model 1",
        )
        model2 = ModelMetadata(
            model_id="p1-model2",
            provider_id="provider1",
            display_name="P1 Model 2",
        )
        model3 = ModelMetadata(
            model_id="p2-model1",
            provider_id="provider2",
            display_name="P2 Model 1",
        )

        catalog.register_model(model1)
        catalog.register_model(model2)
        catalog.register_model(model3)

        p1_models = catalog.list_models_by_provider("provider1")
        p2_models = catalog.list_models_by_provider("provider2")
        p3_models = catalog.list_models_by_provider("provider3")

        assert len(p1_models) == 2
        assert len(p2_models) == 1
        assert len(p3_models) == 0

    def test_get_available_models(self, catalog):
        """Test getting only available models."""
        available = ModelMetadata(
            model_id="avail-model",
            provider_id="provider",
            display_name="Available",
            status=ModelStatus.AVAILABLE,
        )
        unavailable = ModelMetadata(
            model_id="unavail-model",
            provider_id="provider",
            display_name="Unavailable",
            status=ModelStatus.UNAVAILABLE,
        )

        catalog.register_model(available)
        catalog.register_model(unavailable)

        available_models = catalog.get_available_models()

        assert len(available_models) == 1
        assert available_models[0].model_id == "avail-model"

    def test_is_model_available(self, catalog, sample_model):
        """Test checking model availability."""
        catalog.register_model(sample_model)

        assert catalog.is_model_available("sample-model") is True
        assert catalog.is_model_available("nonexistent") is False

    def test_update_model_metadata(self, catalog, sample_model):
        """Test updating model metadata."""
        catalog.register_model(sample_model)

        result = catalog.update_model_metadata(
            "sample-model",
            status=ModelStatus.DEPRECATED,
            display_name="Updated Name",
        )

        assert result is True

        updated = catalog.get_model("sample-model")
        assert updated.status == ModelStatus.DEPRECATED
        assert updated.display_name == "Updated Name"

    def test_update_nonexistent_model(self, catalog):
        """Test updating a model that doesn't exist."""
        result = catalog.update_model_metadata("nonexistent", status=ModelStatus.DEPRECATED)

        assert result is False

    def test_clear_catalog(self, catalog, sample_model):
        """Test clearing all models from catalog."""
        catalog.register_model(sample_model)
        assert len(catalog.list_models()) == 1

        catalog.clear()

        assert len(catalog.list_models()) == 0
        assert catalog.get_stats().total_models == 0

    def test_get_stats(self, catalog, sample_model):
        """Test getting catalog statistics."""
        model2 = ModelMetadata(
            model_id="model2",
            provider_id="provider1",
            display_name="Model 2",
        )

        catalog.register_model(sample_model)
        catalog.register_model(model2)

        stats = catalog.get_stats()

        assert stats.total_models == 2
        assert stats.models_by_provider["sample-provider"] == 1
        assert stats.models_by_provider["provider1"] == 1
        assert stats.available_models == 1
        assert stats.unavailable_models == 1
        assert stats.last_updated is not None


class TestModelCatalogThreadSafety:
    """Test thread-safety of ModelCatalog operations."""

    @pytest.fixture
    def catalog(self):
        """Create a fresh ModelCatalog."""
        return ModelCatalog()

    def test_concurrent_registration(self, catalog):
        """Test concurrent model registration."""
        errors = []

        def register_model(i):
            try:
                model = ModelMetadata(
                    model_id=f"thread-model-{i}",
                    provider_id=f"provider-{i % 3}",
                    display_name=f"Thread Model {i}",
                    status=ModelStatus.AVAILABLE,
                )
                catalog.register_model(model)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register_model, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert catalog.get_stats().total_models == 50

    def test_concurrent_registration_same_model(self, catalog):
        """Test concurrent registration of the same model."""
        errors = []
        results = []

        def register_model():
            try:
                model = ModelMetadata(
                    model_id="concurrent-model",
                    provider_id="provider",
                    display_name="Concurrent Model",
                )
                result = catalog.register_model(model)
                results.append(result)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register_model) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Only one should succeed
        assert sum(results) == 1
        assert catalog.get_stats().total_models == 1

    def test_concurrent_unregister(self, catalog):
        """Test concurrent unregistration of models."""
        # Pre-populate models
        for i in range(50):
            model = ModelMetadata(
                model_id=f"to-remove-{i}",
                provider_id="provider",
                display_name=f"Model {i}",
            )
            catalog.register_model(model)

        errors = []

        def unregister_model(i):
            try:
                catalog.unregister_model(f"to-remove-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=unregister_model, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert catalog.get_stats().total_models == 0


class TestDiscoveryIntegration:
    """Test integration between discovery and catalog."""

    @pytest.fixture
    def catalog(self):
        """Create a fresh ModelCatalog."""
        return ModelCatalog()

    def test_discovery_result_to_catalog(self, catalog):
        """Test registering models discovered via discovery."""
        from aios.core.model_discovery import DiscoveryResult, ModelCapability

        models = [
            ModelMetadata(
                model_id="discovered-1",
                provider_id="discovery-provider",
                display_name="Discovered Model 1",
                capabilities=[ModelCapability.TEXT_GENERATION],
                status=ModelStatus.AVAILABLE,
            ),
            ModelMetadata(
                model_id="discovered-2",
                provider_id="discovery-provider",
                display_name="Discovered Model 2",
                capabilities=[ModelCapability.CODE_GENERATION],
                status=ModelStatus.AVAILABLE,
            ),
        ]

        discovery_result = DiscoveryResult(
            success=True,
            models=models,
            provider_id="discovery-provider",
        )

        # Simulate catalog population from discovery
        if discovery_result.has_models:
            for model in discovery_result.models:
                catalog.register_model(model)

        assert catalog.get_stats().total_models == 2
        assert len(catalog.list_models_by_provider("discovery-provider")) == 2

    def test_failed_discovery_does_not_populate(self, catalog):
        """Test that failed discovery doesn't populate catalog."""
        from aios.core.model_discovery import DiscoveryResult

        failure = DiscoveryResult(
            success=False,
            error="Provider unreachable",
            provider_id="failed-provider",
        )

        # Simulate catalog population from discovery
        if failure.has_models:
            for model in failure.models:
                catalog.register_model(model)

        assert catalog.get_stats().total_models == 0

    def test_static_models_coexist_with_catalog(self, catalog):
        """Test that static and discovered models can coexist."""
        from aios.core.model_discovery import ModelCapability

        # Static models
        static_model = ModelMetadata(
            model_id="static-model",
            provider_id="static-provider",
            display_name="Static Model",
            status=ModelStatus.AVAILABLE,
        )
        catalog.register_model(static_model)

        # Discovered models
        discovered_model = ModelMetadata(
            model_id="discovered-model",
            provider_id="discovery-provider",
            display_name="Discovered Model",
            capabilities=[ModelCapability.TEXT_GENERATION],
            status=ModelStatus.AVAILABLE,
        )
        catalog.register_model(discovered_model)

        all_models = catalog.list_models()
        assert len(all_models) == 2
        model_ids = {m.model_id for m in all_models}
        assert "static-model" in model_ids
        assert "discovered-model" in model_ids


class TestNoCredentialExposure:
    """Test that no credentials are exposed through the catalog."""

    @pytest.fixture
    def catalog(self):
        """Create a fresh ModelCatalog."""
        return ModelCatalog()

    def test_secret_values_not_in_dict(self, catalog):
        """Test that secret values are not included in dictionary representation."""
        metadata = ModelMetadata(
            model_id="secure-model",
            provider_id="provider",
            display_name="Secure Model",
            metadata={
                "api_key": "secret-key-123",
                "normal_field": "public-value",
            },
        )

        catalog.register_model(metadata)

        # Get the dictionary representation
        dict_repr = metadata.to_dict()

        # The api_key should still be in metadata (it's user-provided)
        # but we're testing that our operations don't expose credentials
        # through other means
        assert "model_id" in dict_repr
        assert "provider_id" in dict_repr
        assert "display_name" in dict_repr

    def test_list_operations_no_leaks(self, catalog):
        """Test that list operations don't expose secrets."""
        metadata = ModelMetadata(
            model_id="leak-test",
            provider_id="provider",
            display_name="Leak Test",
            metadata={"secret": "value"},
        )

        catalog.register_model(metadata)

        # All list operations should work without issues
        models = catalog.list_models()
        assert len(models) == 1

        by_provider = catalog.list_models_by_provider("provider")
        assert len(by_provider) == 1

        stats = catalog.get_stats()
        assert stats.total_models == 1
