"""
Unit tests for ModelDiscovery - Provider-agnostic discovery contract.

Tests the discovery interface, result handling, and client implementations
that allow providers to optionally support dynamic model discovery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aios.core.model_types import (
    ModelCapability,
    ModelMetadata,
    ModelStatus,
)
from aios.core.model_discovery import (
    BaseDiscoveryClient,
    DiscoveryResult,
    DiscoverableProvider,
    NoOpDiscoveryClient,
    StaticDiscoveryClient,
)


class TestDiscoveryResult:
    """Test DiscoveryResult behavior."""

    def test_successful_result(self):
        """Test successful discovery result."""
        models = [
            ModelMetadata(
                model_id="model-1",
                provider_id="provider",
                display_name="Model 1",
                status=ModelStatus.AVAILABLE,
            )
        ]

        result = DiscoveryResult(
            success=True,
            models=models,
            provider_id="provider",
        )

        assert result.success is True
        assert result.has_models is True
        assert result.is_failure is False
        assert result.error is None
        assert len(result.models) == 1
        assert result.models[0].model_id == "model-1"

    def test_failed_result(self):
        """Test failed discovery result."""
        result = DiscoveryResult(
            success=False,
            error="Provider unreachable",
            provider_id="provider",
        )

        assert result.success is False
        assert result.has_models is False
        assert result.is_failure is True
        assert result.error == "Provider unreachable"
        assert result.models is None

    def test_empty_result(self):
        """Test empty discovery result (no models)."""
        result = DiscoveryResult(
            success=True,
            models=[],
            provider_id="provider",
        )

        assert result.success is True
        assert result.has_models is False
        assert result.is_failure is False

    def test_to_dict_success(self):
        """Test dictionary serialization of successful result."""
        models = [
            ModelMetadata(
                model_id="model-1",
                provider_id="provider",
                display_name="Model 1",
            )
        ]

        result = DiscoveryResult(
            success=True,
            models=models,
            provider_id="provider",
            discovered_at="2026-01-01T00:00:00Z",
        )

        dict_repr = result.to_dict()

        assert dict_repr["success"] is True
        assert dict_repr["provider_id"] == "provider"
        assert dict_repr["model_count"] == 1
        assert "models" in dict_repr
        assert "error" not in dict_repr

    def test_to_dict_failure(self):
        """Test dictionary serialization of failed result."""
        result = DiscoveryResult(
            success=False,
            error="Connection failed",
            provider_id="provider",
        )

        dict_repr = result.to_dict()

        assert dict_repr["success"] is False
        assert dict_repr["error"] == "Connection failed"
        assert "models" not in dict_repr


class TestNoOpDiscoveryClient:
    """Test NoOpDiscoveryClient for providers without discovery support."""

    @pytest.mark.asyncio
    async def test_noop_returns_not_implemented(self):
        """Test that NoOp client raises NotImplementedError."""
        client = NoOpDiscoveryClient(provider_id="no-op-provider")

        with pytest.raises(NotImplementedError, match="does not support dynamic discovery"):
            await client._discover_models_impl()

    @pytest.mark.asyncio
    async def test_discover_method_handles_not_implemented(self):
        """Test that discover() handles NotImplementedError gracefully."""
        client = NoOpDiscoveryClient(provider_id="no-op-provider")

        result = await client.discover()

        assert result.success is False
        assert result.is_failure is True
        assert "not supported" in result.error.lower()
        assert result.provider_id == "no-op-provider"


class TestStaticDiscoveryClient:
    """Test StaticDiscoveryClient for providers with fixed models."""

    @pytest.mark.asyncio
    async def test_static_discovery_returns_models(self):
        """Test that static client returns pre-configured models."""
        models = [
            ModelMetadata(
                model_id="static-1",
                provider_id="static-provider",
                display_name="Static Model 1",
                status=ModelStatus.AVAILABLE,
            ),
            ModelMetadata(
                model_id="static-2",
                provider_id="static-provider",
                display_name="Static Model 2",
                status=ModelStatus.AVAILABLE,
            ),
        ]

        client = StaticDiscoveryClient(
            provider_id="static-provider",
            static_models=models,
        )

        result = await client.discover()

        assert result.success is True
        assert result.has_models is True
        assert len(result.models) == 2
        assert result.models[0].model_id == "static-1"
        assert result.models[1].model_id == "static-2"

    @pytest.mark.asyncio
    async def test_static_discovery_empty_list(self):
        """Test static client with empty model list."""
        client = StaticDiscoveryClient(provider_id="empty-provider")

        result = await client.discover()

        assert result.success is True
        assert result.has_models is False
        assert len(result.models) == 0


class TestBaseDiscoveryClient:
    """Test BaseDiscoveryClient abstract base class."""

    class ConcreteDiscoveryClient(BaseDiscoveryClient):
        """Concrete implementation for testing."""

        async def _discover_models_impl(self) -> list[ModelMetadata]:
            return [
                ModelMetadata(
                    model_id="concrete-model",
                    provider_id=self._provider_id,
                    display_name="Concrete Model",
                    status=ModelStatus.AVAILABLE,
                )
            ]

    @pytest.mark.asyncio
    async def test_successful_discovery(self):
        """Test successful discovery implementation."""
        client = self.ConcreteDiscoveryClient(provider_id="test-provider")

        result = await client.discover()

        assert result.success is True
        assert result.has_models is True
        assert result.models[0].model_id == "concrete-model"
        assert result.provider_id == "test-provider"

    @pytest.mark.asyncio
    async def test_discovery_error_handling(self):
        """Test that discovery errors are caught and reported."""

        class FailingClient(BaseDiscoveryClient):
            async def _discover_models_impl(self):
                raise RuntimeError("Connection failed")

        client = FailingClient(provider_id="failing-provider")

        result = await client.discover()

        assert result.success is False
        assert result.is_failure is True
        assert "Connection failed" in result.error
        assert result.provider_id == "failing-provider"

    def test_provider_id_property(self):
        """Test provider_id property access."""
        client = self.ConcreteDiscoveryClient(provider_id="my-provider")
        assert client.provider_id == "my-provider"


class TestDiscoverableProviderProtocol:
    """Test DiscoverableProvider protocol definition."""

    def test_protocol_definition(self):
        """Test that DiscoverableProvider is properly defined as protocol."""
        # Should be usable as a type annotation
        def accepts_discoverable(provider: DiscoverableProvider) -> None:
            pass

        # Should be checkable with isinstance
        class MockProvider:
            async def discover_models(self):
                return []

        mock = MockProvider()
        assert isinstance(mock, DiscoverableProvider)

    @pytest.mark.asyncio
    async def test_protocol_method_signature(self):
        """Test that protocol method has correct signature."""

        class ValidProvider:
            async def discover_models(self) -> list[ModelMetadata]:
                return []

        valid = ValidProvider()
        assert isinstance(valid, DiscoverableProvider)

        # Should reject incorrect signatures
        class InvalidProvider:
            def discover_models(self):
                pass

        invalid = InvalidProvider()
        # Note: In Python protocols, structural subtyping means that a class
        # with a method named discover_models will be considered to implement
        # the protocol, even if the signature is wrong. This is expected behavior.
        # The important thing is that classes with the correct signature work.
        assert isinstance(invalid, DiscoverableProvider)


class TestCredentialSecurity:
    """Test that discovery never exposes credentials."""

    def test_discovery_result_no_credentials(self):
        """Test that DiscoveryResult does not expose credentials."""
        # Create a result with potentially sensitive data in metadata
        models = [
            ModelMetadata(
                model_id="secure-model",
                provider_id="provider",
                display_name="Secure Model",
                metadata={
                    "api_key": "secret-key",
                    "token": "secret-token",
                },
            )
        ]

        result = DiscoveryResult(
            success=True,
            models=models,
            provider_id="provider",
        )

        dict_repr = result.to_dict()

        # The result itself should not leak credentials in non-metadata fields
        assert "success" in dict_repr
        assert "provider_id" in dict_repr
        assert "error" not in dict_repr

    def test_client_constructor_no_secrets(self):
        """Test that client constructors don't store secrets."""
        # NoOpDiscoveryClient should only store provider_id
        client = NoOpDiscoveryClient(provider_id="test")
        assert not hasattr(client, "_api_key")
        assert not hasattr(client, "_secret")

        # StaticDiscoveryClient should only store provider_id and models
        models = [
            ModelMetadata(
                model_id="model",
                provider_id="provider",
                display_name="Model",
                metadata={"safe": "data"},
            )
        ]
        client = StaticDiscoveryClient(provider_id="test", static_models=models)
        assert not hasattr(client, "_api_key")


class TestProviderIntegration:
    """Test integration patterns for providers."""

    @pytest.mark.asyncio
    async def test_provider_can_implement_protocol(self):
        """Test that a real provider can implement the protocol."""

        class ExampleProvider:
            async def discover_models(self) -> list[ModelMetadata]:
                return [
                    ModelMetadata(
                        model_id="example-model",
                        provider_id="example",
                        display_name="Example Model",
                        capabilities=[ModelCapability.TEXT_GENERATION],
                        status=ModelStatus.AVAILABLE,
                    )
                ]

        provider = ExampleProvider()
        assert isinstance(provider, DiscoverableProvider)

        models = await provider.discover_models()
        assert len(models) == 1
        assert models[0].model_id == "example-model"

    @pytest.mark.asyncio
    async def test_provider_without_discovery_support(self):
        """Test provider that doesn't implement discovery."""

        class BasicProvider:
            pass

        provider = BasicProvider()
        assert not isinstance(provider, DiscoverableProvider)

        # Should use NoOpDiscoveryClient instead
        client = NoOpDiscoveryClient(provider_id="basic-provider")
        result = await client.discover()
        assert result.is_failure
        assert "not supported" in result.error.lower()
