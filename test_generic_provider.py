#!/usr/bin/env python3
"""Test that the provider actions now work generically with any registered provider."""

import sys
import asyncio
sys.path.insert(0, 'C:\Development\AI-OS')

from unittest.mock import Mock
from aios.core.provider_registry import ProviderRegistry
from aios.services.dashboard_service import DashboardService
from aios.core.security_manager import SecurityManager, SecurityDecision
from aios.adapters.nim import NimProvider


class TestProvider:
    """A test provider to verify generic functionality."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self._config = Mock()
        self._config.base_url = f"https://{provider_id}.example.com"

    async def generate(self, request):
        from aios.core.model_router import ModelResponse
        return ModelResponse(
            content=f"Test response from {self.provider_id}",
            model_id="test-model",
            provider=self.provider_id,
            tokens_used={"input": 5, "output": 3},
            cost=0.001,
            latency_ms=10
        )

    def configure(self, config):
        print(f"Configuring {self.provider_id} with {list(config.keys())}")
        for key, value in config.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    async def reload_credentials(self):
        print(f"Reloading credentials for {self.provider_id}")


async def test_generic_provider_functionality():
    """Test that provider actions work with any registered provider, not just NIM."""

    # Setup kernel with ProviderRegistry
    mock_kernel = Mock()
    mock_kernel.provider_registry = ProviderRegistry()
    mock_kernel.configuration = Mock()
    mock_kernel.configuration.rotate_secret.return_value = True
    mock_kernel.security_manager = Mock()
    mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW
    mock_kernel.event_bus = Mock()

    # Create dashboard service
    dashboard_service = DashboardService(
        kernel=mock_kernel,
        event_bus=mock_kernel.event_bus,
        security_manager=mock_kernel.security_manager
    )

    print("=== Testing Generic Provider Functionality ===")

    # Test 1: Register and configure a custom provider
    print("\n1. Registering and configuring custom provider...")
    custom_provider = TestProvider("custom-llm")
    mock_kernel.provider_registry.register_provider("custom-llm", custom_provider)

    result = await dashboard_service.request_action(
        action="provider.configure",
        params={
            "provider_id": "custom-llm",
            "config": {
                "base_url": "https://api.custom-llm.com",
                "timeout_seconds": 30
            }
        }
    )

    assert result.status == "completed"
    assert result.data["provider_id"] == "custom-llm"
    assert "base_url" in result.data["updated_config"]
    assert "timeout_seconds" in result.data["updated_config"]
    print("[PASS] Custom provider configuration successful")

    # Test 2: Enable the custom provider
    print("\n2. Enabling custom provider...")
    result = await dashboard_service.request_action(
        action="provider.enable",
        params={
            "provider_id": "custom-llm"
        }
    )

    assert result.status == "completed"
    assert result.data["provider_id"] == "custom-llm"
    assert result.data["success"] is True
    print("[PASS] Custom provider enable successful")

    # Test 3: Disable the custom provider
    print("\n3. Disabling custom provider...")
    result = await dashboard_service.request_action(
        action="provider.disable",
        params={
            "provider_id": "custom-llm"
        }
    )

    assert result.status == "completed"
    assert result.data["provider_id"] == "custom-llm"
    assert result.data["success"] is True
    print("[PASS] Custom provider disable successful")

    # Test 4: Secret rotation with custom provider
    print("\n4. Testing secret rotation with custom provider...")
    result = await dashboard_service.request_action(
        action="secret.rotate",
        params={
            "provider_id": "custom-llm",
            "new_value": "sk-custom-test-key-123"
        }
    )

    assert result.status == "completed"
    # For secret.rotate, the result contains the path, not provider_id
    expected_path = f"config:llm.providers.custom-llm.apiKey"
    assert result.data["path"] == expected_path
    assert result.data.get("redacted") is True
    print("[PASS] Custom provider secret rotation successful")

    # Test 5: Verify backward compatibility - default to "nim" when specified
    print("\n5. Testing backward compatibility with explicit NIM provider...")
    nim_provider = NimProvider()
    mock_kernel.provider_registry.register_provider("nim", nim_provider)

    result = await dashboard_service.request_action(
        action="provider.configure",
        params={
            "provider_id": "nim",
            "config": {
                "base_url": "https://api.nim.example.com",
                "default_model": "test-model"
            }
        }
    )

    assert result.status == "completed"
    assert result.data["provider_id"] == "nim"
    assert "base_url" in result.data["updated_config"]
    assert "default_model" in result.data["updated_config"]
    print("[PASS] NIM provider configuration still works")

    print("\n=== All tests passed! Provider actions are now generic ===")


if __name__ == "__main__":
    asyncio.run(test_generic_provider_functionality())