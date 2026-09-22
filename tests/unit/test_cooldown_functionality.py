"""
Comprehensive test for ProviderRegistry cooldown functionality.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from aios.core.provider_registry import (
    ProviderRegistry,
    ProviderRegistryState,
    reset_provider_registry_singleton,
)
from aios.core.provider_failures import ProviderFailure, FailureCategory
from aios.core.provider import Provider
from aios.core.model_router import ModelRequest, ModelResponse, ModelProvider


class TestProvider(Provider):
    """Simple provider for testing."""

    def __init__(self, content="from-test"):
        self.calls = 0
        self._content = content
        self.reload_credentials_called = False

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            content=f"{self._content}: {request.prompt[:40]}",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
        )

    async def reload_credentials(self) -> None:
        """Mock implementation of reload_credentials for testing."""
        self.reload_credentials_called = True


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before each test for isolation."""
    reset_provider_registry_singleton()
    yield
    reset_provider_registry_singleton()


class TestCooldownConfiguration:
    """Test configuration-driven cooldown functionality."""

    def test_default_cooldown_configuration(self):
        """Test that default cooldown configuration is loaded correctly."""
        registry = ProviderRegistry()

        # Verify default configuration values are set
        assert registry._cooldown_enabled is True
        assert registry._base_duration == 30
        assert registry._max_duration == 300
        assert registry._multiplier == 2.0

    @patch('aios.core.provider_registry.get_configuration_manager')
    def test_custom_cooldown_configuration(self, mock_get_config):
        """Test that custom cooldown configuration is loaded from config."""
        # Mock configuration manager
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "enabled": True,
            "base_duration_seconds": 45,
            "max_duration_seconds": 600,
            "multiplier": 3.0,
            "category_overrides": {
                "rate_limit": 120,
                "timeout": 60,
            }
        }
        mock_get_config.return_value = mock_config

        registry = ProviderRegistry()

        # Verify custom configuration values are loaded
        assert registry._cooldown_enabled is True
        assert registry._base_duration == 45
        assert registry._max_duration == 600
        assert registry._multiplier == 3.0

        # Verify category overrides are stored separately (do not modify global defaults)
        assert registry._category_overrides[FailureCategory.RATE_LIMIT.value] == 120
        assert registry._category_overrides[FailureCategory.TIMEOUT.value] == 60

    @patch('aios.core.provider_registry.get_configuration_manager')
    def test_disabled_cooldown_configuration(self, mock_get_config):
        """Test that cooldown can be disabled via configuration."""
        # Mock configuration manager
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "enabled": False,
            "base_duration_seconds": 30,
            "max_duration_seconds": 300,
            "multiplier": 2.0,
        }
        mock_get_config.return_value = mock_config

        registry = ProviderRegistry()

        # Verify cooldown is disabled
        assert registry._cooldown_enabled is False

    def test_cooldown_with_disabled_flag(self):
        """Test that cooldown is not applied when disabled."""
        registry = ProviderRegistry()
        registry._cooldown_enabled = False

        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Create a timeout failure that would normally trigger cooldown
        failure = ProviderFailure(
            category=FailureCategory.TIMEOUT,
            provider_id="test-provider",
            safe_message="Timeout"
        )

        registry.update_provider_health_from_failure("test-provider", failure)

        # Cooldown should not be applied
        remaining = registry.get_provider_cooldown_remaining("test-provider")
        assert remaining == 0.0


class TestExponentialBackoff:
    """Test exponential backoff in cooldown durations."""

    def test_exponential_backoff_with_consecutive_failures(self):
        """Test that cooldown duration increases with consecutive failures."""
        registry = ProviderRegistry()
        registry._base_duration = 10
        registry._max_duration = 100
        registry._multiplier = 2.0

        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # First failure - base duration
        failure1 = ProviderFailure(
            category=FailureCategory.NETWORK,
            provider_id="test-provider",
            safe_message="Network error 1"
        )
        registry.update_provider_health_from_failure("test-provider", failure1)
        remaining1 = registry.get_provider_cooldown_remaining("test-provider")
        assert 8 <= remaining1 <= 12  # Allow some timing variance

        # Wait for cooldown to expire
        time.sleep(10.1)  # Wait longer than base duration
        assert registry.get_provider_cooldown_remaining("test-provider") == 0.0

        # Second failure - should have longer cooldown due to consecutive failures
        failure2 = ProviderFailure(
            category=FailureCategory.NETWORK,
            provider_id="test-provider",
            safe_message="Network error 2"
        )
        registry.update_provider_health_from_failure("test-provider", failure2)
        remaining2 = registry.get_provider_cooldown_remaining("test-provider")
        # With multiplier=2.0 and 1 consecutive failure, should be at least base * 2
        assert remaining2 >= 18  # 10 * 2^1 = 20, allow some variance

        # Wait for cooldown to expire
        time.sleep(20.1)  # Wait longer than second cooldown duration
        assert registry.get_provider_cooldown_remaining("test-provider") == 0.0

        # Third failure - should have even longer cooldown
        failure3 = ProviderFailure(
            category=FailureCategory.NETWORK,
            provider_id="test-provider",
            safe_message="Network error 3"
        )
        registry.update_provider_health_from_failure("test-provider", failure3)
        remaining3 = registry.get_provider_cooldown_remaining("test-provider")
        # With multiplier=2.0 and 2 consecutive failures, should be at least base * 4
        assert remaining3 >= 38  # 10 * 2^2 = 40, allow some variance

    def test_cooldown_capped_at_max_duration(self):
        """Test that cooldown duration is capped at max_duration."""
        registry = ProviderRegistry()
        registry._base_duration = 10
        registry._max_duration = 50
        registry._multiplier = 2.0

        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply multiple failures to trigger exponential backoff
        for i in range(5):
            failure = ProviderFailure(
                category=FailureCategory.NETWORK,
                provider_id="test-provider",
                safe_message=f"Network error {i+1}"
            )
            registry.update_provider_health_from_failure("test-provider", failure)

            # Wait for cooldown to expire
            time.sleep(0.15)

        # The last cooldown should be capped at max_duration (50 seconds)
        remaining = registry.get_provider_cooldown_remaining("test-provider")
        assert remaining <= 52  # Should be close to 50, allow some variance
        assert remaining > 40  # Should not be much less than 50


class TestCooldownCleanup:
    """Test automatic cleanup of expired cooldowns."""

    def test_expired_cooldown_cleanup(self):
        """Test that expired cooldowns are automatically cleaned up."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply a short cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 0.1)

        # Should be in cooldown initially
        assert registry.get_provider_cooldown_remaining("test-provider") > 0
        assert registry.get_provider("test-provider") is None

        # Wait for cooldown to expire
        time.sleep(0.15)

        # Call health check which should trigger cleanup
        health = registry.healthCheck()

        # Should no longer be in cooldown
        assert registry.get_provider_cooldown_remaining("test-provider") == 0.0
        assert registry.get_provider("test-provider") is provider

    def test_health_check_triggers_cleanup(self):
        """Test that healthCheck triggers cooldown cleanup."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply a short cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 0.1)

        # Call health check
        health = registry.healthCheck()

        # Wait for cooldown to expire and check again
        time.sleep(0.15)
        health = registry.healthCheck()

        # Should no longer be in cooldown after second health check
        assert registry.get_provider_cooldown_remaining("test-provider") == 0.0


class TestConfigurationIntegration:
    """Test integration with ConfigurationManager."""

    @patch('aios.core.provider_registry.get_configuration_manager')
    def test_reload_cooldown_on_config_frozen(self, mock_get_config):
        """Test that cooldown configuration is reloaded when config is frozen."""
        # First call returns default config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "enabled": True,
            "base_duration_seconds": 30,
            "max_duration_seconds": 300,
            "multiplier": 2.0,
        }
        mock_get_config.return_value = mock_config

        registry = ProviderRegistry()
        assert registry._base_duration == 30

        # Simulate configuration change
        mock_config.get.return_value = {
            "enabled": True,
            "base_duration_seconds": 60,
            "max_duration_seconds": 600,
            "multiplier": 3.0,
        }

        # Call the config reload method
        registry._load_cooldown_config()
        assert registry._base_duration == 60
        assert registry._multiplier == 3.0


class TestThreadSafety:
    """Test thread-safe implementation of cooldown functionality."""

    def test_concurrent_cooldown_operations(self):
        """Test that cooldown operations are thread-safe."""
        import threading

        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        results = []

        def apply_cooldown():
            for i in range(10):
                failure = ProviderFailure(
                    category=FailureCategory.NETWORK,
                    provider_id="test-provider",
                    safe_message=f"Network error {i}"
                )
                registry.update_provider_health_from_failure("test-provider", failure)
                remaining = registry.get_provider_cooldown_remaining("test-provider")
                results.append(remaining)
                # Clear cooldown to allow next iteration
                registry.clear_cooldown("test-provider")

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=apply_cooldown)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations completed without errors
        assert len(results) == 50
        # All results should be non-negative
        assert all(r >= 0 for r in results)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_duration_cooldown(self):
        """Test that zero duration cooldown is handled correctly."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply zero-duration cooldown
        registry._apply_cooldown("test-provider", FailureCategory.AUTHENTICATION, 0)

        # Should not be in cooldown
        remaining = registry.get_provider_cooldown_remaining("test-provider")
        assert remaining == 0.0

    def test_negative_duration_cooldown(self):
        """Test that negative duration cooldown is handled correctly."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply negative-duration cooldown (should be treated as 0)
        registry._apply_cooldown("test-provider", FailureCategory.AUTHENTICATION, -10)

        # Should not be in cooldown
        remaining = registry.get_provider_cooldown_remaining("test-provider")
        assert remaining == 0.0

    def test_already_in_cooldown_override(self):
        """Test that applying a new cooldown overrides existing cooldown."""
        registry = ProviderRegistry()
        provider = TestProvider()
        registry.register_provider("test-provider", provider)

        # Apply first cooldown
        registry._apply_cooldown("test-provider", FailureCategory.NETWORK, 5.0)
        remaining1 = registry.get_provider_cooldown_remaining("test-provider")
        assert remaining1 > 4.0

        # Apply second cooldown while first is still active
        registry._apply_cooldown("test-provider", FailureCategory.TIMEOUT, 10.0)
        remaining2 = registry.get_provider_cooldown_remaining("test-provider")

        # Should now have the new cooldown duration
        assert remaining2 > 9.0
        assert remaining2 > remaining1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
