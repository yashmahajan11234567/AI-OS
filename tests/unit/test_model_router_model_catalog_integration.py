"""
Unit tests for ModelRouter integration with ModelCatalog.

Tests that the ModelRouter properly integrates with the ModelCatalog
to leverage provider-agnostic model metadata while maintaining
backward compatibility with existing ModelConfig-based routing.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.model_types import (
    ModelCapability,
    ModelCost,
    ModelHealth,
    ModelLimits,
    ModelMetadata,
    ModelStatus,
)
from aios.core.model_catalog import ModelCatalog
from aios.core.model_router import (
    ModelCapability as RouterCapability,
    ModelConfig,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelRouter,
)


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, name="mock", response_content="mock response"):
        self.name = name
        self.response_content = response_content
        self.generate_calls = 0

    async def generate(self, request):
        self.generate_calls += 1
        return ModelResponse(
            content=f"{self.response_content}: {request.prompt[:20]}",
            model_id=request.preferred_model or "mock-default",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 5, "output": 10},
            cost=0.001,
            latency_ms=5,
        )


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider()


@pytest.fixture
def provider_registry():
    """Create a provider registry with mock provider."""
    from aios.core.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    registry.register_provider("mock-provider", MockProvider())
    return registry


@pytest.fixture
def model_catalog():
    """Create a fresh model catalog."""
    catalog = ModelCatalog()
    # Clear any default models that might have been registered
    catalog.clear()
    return catalog


@pytest.fixture
def router(provider_registry, model_catalog):
    """Create a ModelRouter with provider registry and model catalog."""
    return ModelRouter(
        provider_registry=provider_registry,
        model_catalog=model_catalog,
    )


@pytest.fixture
def router_without_catalog(provider_registry):
    """Create a ModelRouter without model catalog (backward compatibility test)."""
    return ModelRouter(provider_registry=provider_registry)


def test_router_accepts_model_catalog(router, model_catalog):
    """Test that ModelRouter accepts and stores model catalog."""
    assert router.model_catalog is model_catalog


def test_router_without_model_catalog_still_works(router_without_catalog):
    """Test that ModelRouter works without model catalog (backward compatibility)."""
    assert router_without_catalog.model_catalog is None


def test_register_model_updates_catalog(router, model_catalog):
    """Test that registering a model also updates the catalog."""
    model = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )

    router.register_model(model)

    # Check that model exists in catalog
    catalog_model = model_catalog.get_model("test-model")
    assert catalog_model is not None
    assert catalog_model.model_id == "test-model"
    assert catalog_model.provider_id == "local"
    assert catalog_model.display_name == "Test Model"
    assert catalog_model.status == ModelStatus.AVAILABLE


def test_unregister_model_updates_catalog(router, model_catalog):
    """Test that unregistering a model also updates the catalog."""
    model = ModelConfig(
        model_id="test-model-unreg",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )

    router.register_model(model)
    router.unregister_model("test-model-unreg")

    # Check that model is removed from catalog
    catalog_model = model_catalog.get_model("test-model-unreg")
    assert catalog_model is None


def test_sync_model_from_catalog(router, model_catalog):
    """Test syncing model status from catalog to router."""
    # Register model in router
    model = ModelConfig(
        model_id="sync-test",
        provider=ModelProvider.LOCAL,
        name="Sync Test Model",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )
    router.register_model(model)

    # Initially should be enabled
    assert router._models["sync-test"].enabled is True

    # Update in catalog to unavailable
    model_catalog.update_model_metadata(
        "sync-test",
        status=ModelStatus.UNAVAILABLE,
    )

    # Sync from catalog
    result = router.sync_model_from_catalog("sync-test")
    assert result is True

    # Router model should now be disabled
    assert router._models["sync-test"].enabled is False


def test_sync_nonexistent_model_from_catalog(router, model_catalog):
    """Test syncing a model that doesn't exist in router."""
    result = router.sync_model_from_catalog("nonexistent")
    assert result is False


def test_sync_with_no_catalog(router_without_catalog):
    """Test sync when no catalog is configured."""
    result = router_without_catalog.sync_model_from_catalog("any-model")
    assert result is False


async def test_generate_still_works_with_catalog(router, mock_provider, provider_registry):
    """Test that generation still works with catalog integration."""
    # Register the mock provider in the registry
    provider_registry.register_provider("mock", mock_provider)

    # Register a model that uses the mock provider
    model = ModelConfig(
        model_id="generated-model",
        provider=ModelProvider.LOCAL,
        name="Generated Model",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "mock"},  # Tells router to use ProviderRegistry
    )
    router.register_model(model)

    request = ModelRequest(prompt="test prompt", preferred_model="generated-model")
    response = await router.generate(request)

    assert mock_provider.generate_calls == 1
    assert "mock response:" in response.content
    assert response.model_id == "generated-model"


async def test_disabled_provider_still_respected(router_without_catalog, mock_provider):
    """Test that disabled providers are still respected with catalog integration."""
    from aios.core.provider_registry import ProviderRegistry

    # Create a separate registry for this test to avoid interference
    registry = ProviderRegistry()
    mock_provider_instance = MockProvider()
    registry.register_provider("test-provider", mock_provider_instance)

    router = ModelRouter(provider_registry=registry)

    # Register model using this provider
    model = ModelConfig(
        model_id="disabled-test",
        provider=ModelProvider.LOCAL,
        name="Disabled Test",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "test-provider"},
    )
    router.register_model(model)

    # Verify it works when enabled
    request = ModelRequest(prompt="test", preferred_model="disabled-test")
    response = await router.generate(request)
    assert mock_provider_instance.generate_calls == 1

    # Disable the provider
    registry.disable_provider("test-provider")

    # Reset call count
    mock_provider_instance.generate_calls = 0

    # Should fall back to mock when provider disabled
    response = await router.generate(request)
    assert mock_provider_instance.generate_calls == 0  # Not called
    assert "[Mock response from" in response.content


def test_catalog_based_model_listing(router, model_catalog):
    """Test that catalog provides additional model listing capabilities."""
    # Get initial count of default models
    initial_count = len(model_catalog.list_models())

    # Register some models in router
    model1 = ModelConfig(
        model_id="catalog-test-1",
        provider=ModelProvider.LOCAL,
        name="Catalog Test 1",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )
    model2 = ModelConfig(
        model_id="catalog-test-2",
        provider=ModelProvider.LOCAL,
        name="Catalog Test 2",
        capabilities=[RouterCapability.CODE_GENERATION],
        enabled=False,  # Disabled in router
    )

    router.register_model(model1)
    router.register_model(model2)

    # Add corresponding models to catalog with different statuses
    catalog_model1 = ModelMetadata(
        model_id="catalog-test-1",
        provider_id="local",
        display_name="Catalog Test 1",
        capabilities=[ModelCapability.TEXT_GENERATION],
        status=ModelStatus.AVAILABLE,
    )
    catalog_model2 = ModelMetadata(
        model_id="catalog-test-2",
        provider_id="local",
        display_name="Catalog Test 2",
        capabilities=[ModelCapability.CODE_GENERATION],
        status=ModelStatus.UNAVAILABLE,  # Unavailable in catalog
    )
    catalog_model3 = ModelMetadata(
        model_id="catalog-test-3",
        provider_id="local",
        display_name="Catalog Test 3",
        capabilities=[ModelCapability.REASONING],
        status=ModelStatus.AVAILABLE,
    )
    model_catalog.register_model(catalog_model1)
    model_catalog.register_model(catalog_model2)
    model_catalog.register_model(catalog_model3)

    # Router should list its enabled models (including defaults + catalog-test-1)
    router_available = router.get_available_models()
    assert len(router_available) > initial_count  # Should have more than defaults
    assert any(m.model_id == "catalog-test-1" for m in router_available)

    # Catalog provides richer metadata - should have more models
    catalog_available = model_catalog.get_available_models()
    assert len(catalog_available) > initial_count  # Should have more than defaults
    catalog_ids = {m.model_id for m in catalog_available}
    assert "catalog-test-1" in catalog_ids
    assert "catalog-test-3" in catalog_ids


def test_model_catalog_statistics_integration(router, model_catalog):
    """Test that catalog statistics reflect registered models."""
    # Catalog starts with default models from ModelRouter
    initial_stats = model_catalog.get_stats()
    initial_count = initial_stats.total_models
    assert initial_count >= 5  # At least the default models

    # Register additional models
    model1 = ModelConfig(
        model_id="stats-test-add-1",
        provider=ModelProvider.LOCAL,
        name="Stats Test Add 1",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )
    model2 = ModelConfig(
        model_id="stats-test-add-2",
        provider=ModelProvider.LOCAL,
        name="Stats Test Add 2",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )

    router.register_model(model1)
    router.register_model(model2)

    # Check that statistics increased
    stats = model_catalog.get_stats()
    assert stats.total_models == initial_count + 2

    # Register more models with different providers
    models = [
        ModelConfig(
            model_id=f"stats-test-{i}",
            provider=ModelProvider.LOCAL if i % 2 == 0 else ModelProvider.ANTHROPIC,
            name=f"Stats Test {i}",
            capabilities=[RouterCapability.TEXT_GENERATION],
            enabled=(i % 3 != 0),  # Some enabled, some disabled
        )
        for i in range(5)
    ]

    for model in models:
        router.register_model(model)

    # Check catalog statistics
    stats = model_catalog.get_stats()
    # Should have initial + 2 + 5 = initial + 7 total models
    assert stats.total_models == initial_count + 7


def test_backward_compatibility_no_catalog():
    """Test that existing code without catalog still works exactly as before."""
    from aios.core.provider_registry import ProviderRegistry
    from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig

    # This mimics the existing test pattern
    provider_registry = ProviderRegistry()
    router = ModelRouter(provider_registry=provider_registry)

    # Should work without any catalog
    assert router.model_catalog is None

    # Basic model registration should work
    model = ModelConfig(
        model_id="backward-test",
        provider=ModelProvider.LOCAL,
        name="Backward Compat Test",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )
    router.register_model(model)

    assert "backward-test" in router._models
    assert router._models["backward-test"].enabled is True


def test_no_credentials_exposed_through_integration(router, model_catalog):
    """Test that the integration doesn't expose credentials."""
    # Register a model
    model = ModelConfig(
        model_id="cred-test",
        provider=ModelProvider.LOCAL,
        name="Credential Test",
        capabilities=[RouterCapability.TEXT_GENERATION],
        enabled=True,
    )
    router.register_model(model)

    # Check catalog entry
    catalog_model = model_catalog.get_model("cred-test")
    assert catalog_model is not None

    # The catalog model should not contain any credential information
    dict_repr = catalog_model.to_dict()
    secret_indicators = ["key", "token", "secret", "password", "credential"]

    # Check top-level fields
    for key in dict_repr.keys():
        lower_key = key.lower()
        assert not any(indicator in lower_key for indicator in secret_indicators), (
            f"Potential credential exposure in catalog field: {key}"
        )

    # Check metadata field if it exists
    if "metadata" in dict_repr:
        metadata = dict_repr["metadata"]
        if isinstance(metadata, dict):
            for key in metadata.keys():
                lower_key = key.lower()
                assert not any(indicator in lower_key for indicator in secret_indicators), (
                    f"Potential credential exposure in metadata: {key}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])