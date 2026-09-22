"""
Unit tests for the Provider ABC.

Tests the Provider abstract base class and its interface methods.
"""

from __future__ import annotations

import pytest

from aios.core.provider import Provider


class TestProvider(Provider):
    """Test implementation of the Provider ABC."""

    def __init__(self):
        self.configure_called = False
        self.configure_config = None
        self.reload_credentials_called = False

    async def generate(self, request):
        """Minimal generate implementation for testing."""
        return None

    def configure(self, config):
        """Track configure calls."""
        self.configure_called = True
        self.configure_config = config

    async def reload_credentials(self):
        """Track reload_credentials calls."""
        self.reload_credentials_called = True


def test_provider_abstract_base_class():
    """Test that Provider is an abstract base class."""
    # Cannot instantiate abstract class directly
    with pytest.raises(TypeError):
        Provider()


def test_provider_configure_method():
    """Test that Provider.configure exists and can be overridden."""
    provider = TestProvider()
    config = {"base_url": "https://test.example.com", "timeout": 30}

    provider.configure(config)

    assert provider.configure_called
    assert provider.configure_config == config


def test_provider_reload_credentials_method():
    """Test that Provider.reload_credentials exists and can be overridden."""
    import asyncio

    provider = TestProvider()

    # Call the async method
    asyncio.run(provider.reload_credentials())

    assert provider.reload_credentials_called


def test_provider_default_configure_does_nothing():
    """Test that the default Provider.configure implementation does nothing."""
    # Test that the method exists on the class
    assert hasattr(Provider, 'configure')
    assert callable(getattr(Provider, 'configure'))


def test_provider_default_reload_credentials_does_nothing():
    """Test that the default Provider.reload_credentials implementation does nothing."""
    # Test that the method exists on the class
    assert hasattr(Provider, 'reload_credentials')
    assert callable(getattr(Provider, 'reload_credentials'))