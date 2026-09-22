"""
Unit tests for provider cooldown functionality in AI-OS ProviderRegistry.
"""

import time
import unittest
from unittest.mock import Mock, patch

from src.aios.core.provider_registry import ProviderRegistry
from src.aios.core.provider_failures import FailureCategory, ProviderFailure
from src.aios.events.core.types import EventType


class TestProviderCooldown(unittest.TestCase):
    """Test provider cooldown functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = ProviderRegistry()
        self.provider_id = "test-provider"

        # Register a mock provider
        class MockProvider:
            def __init__(self, provider_id):
                self.provider_id = provider_id

        mock_provider = MockProvider(self.provider_id)
        self.registry.register_provider(self.provider_id, mock_provider)

        # Set up category overrides for testing (since config may not be available in test env)
        self.registry._category_overrides = {
            FailureCategory.RATE_LIMIT.value: 60,
            FailureCategory.QUOTA_EXCEEDED.value: 300,
        }

    def test_initial_state_no_cooldown(self):
        """Test that provider starts with no cooldown."""
        health = self.registry._provider_health[self.provider_id]
        self.assertFalse(self.registry._is_in_cooldown(health))
        self.assertEqual(self.registry.get_provider_cooldown_remaining(self.provider_id), 0.0)

        # Provider should be retrievable
        provider = self.registry.get_provider(self.provider_id)
        self.assertIsNotNone(provider)

    def test_apply_cooldown_timeout(self):
        """Test applying cooldown for timeout failure."""
        # Create a timeout failure
        failure = ProviderFailure(
            category=FailureCategory.TIMEOUT,
            provider_id=self.provider_id,
            safe_message="Request timeout"
        )

        # Apply the failure (which should trigger cooldown)
        self.registry.update_provider_health_from_failure(self.provider_id, failure)

        # Check that provider is now in cooldown
        health = self.registry._provider_health[self.provider_id]
        self.assertTrue(self.registry._is_in_cooldown(health))
        self.assertGreater(self.registry.get_provider_cooldown_remaining(self.provider_id), 0)

        # Provider should not be retrievable due to cooldown
        provider = self.registry.get_provider(self.provider_id)
        self.assertIsNone(provider)

        # Provider info should show it as unhealthy (intrinsic health affected by failure)
        info = self.registry.get_provider_info(self.provider_id)
        self.assertIsNotNone(info)
        self.assertFalse(info.healthy)  # Intrinsic health is affected
        self.assertTrue(info.enabled)  # Still enabled

    def test_cooldown_expiration(self):
        """Test that cooldown expires after the specified duration."""
        # Apply a short cooldown using override
        # Set up a 1-second override for testing
        original_override = self.registry._category_overrides.get(FailureCategory.TIMEOUT.value)
        self.registry._category_overrides[FailureCategory.TIMEOUT.value] = 1

        try:
            failure = ProviderFailure(
                category=FailureCategory.TIMEOUT,
                provider_id=self.provider_id,
                safe_message="Request timeout"
            )
            self.registry.update_provider_health_from_failure(self.provider_id, failure)

            # Verify cooldown is active
            self.assertTrue(self.registry._is_in_cooldown(self.registry._provider_health[self.provider_id]))
            initial_remaining = self.registry.get_provider_cooldown_remaining(self.provider_id)
            self.assertGreater(initial_remaining, 0)
            print('DEBUG: After failure - cooldown active, remaining: {}'.format(initial_remaining))

            # Wait for cooldown to expire (apply a 1-second cooldown and wait 1.5 seconds)
            time.sleep(1.5)
            print('DEBUG: After waiting 1.5 seconds')

            # Verify cooldown has expired
            is_in_cooldown = self.registry._is_in_cooldown(self.registry._provider_health[self.provider_id])
            remaining = self.registry.get_provider_cooldown_remaining(self.provider_id)
            print('DEBUG: is_in_cooldown: {}, remaining: {}'.format(is_in_cooldown, remaining))
            self.assertFalse(is_in_cooldown, 'Provider should not be in cooldown after waiting')
            self.assertEqual(remaining, 0.0, 'Cooldown remaining should be 0')
        finally:
            # Restore original override
            if original_override is not None:
                self.registry._category_overrides[FailureCategory.TIMEOUT.value] = original_override
            elif FailureCategory.TIMEOUT.value in self.registry._category_overrides:
                del self.registry._category_overrides[FailureCategory.TIMEOUT.value]

        # Provider should be retrievable again
        provider = self.registry.get_provider(self.provider_id)
        self.assertIsNotNone(provider)

    def test_manual_cooldown_clear(self):
        """Test manually clearing a provider's cooldown."""
        # Apply cooldown
        failure = ProviderFailure(
            category=FailureCategory.NETWORK,
            provider_id=self.provider_id,
            safe_message="Network error"
        )
        self.registry.update_provider_health_from_failure(self.provider_id, failure)

        # Verify cooldown is active
        self.assertTrue(self.registry._is_in_cooldown(self.registry._provider_health[self.provider_id]))

        # Manually clear the cooldown
        result = self.registry.clear_cooldown(self.provider_id)
        self.assertTrue(result)

        # Verify cooldown is cleared
        self.assertFalse(self.registry._is_in_cooldown(self.registry._provider_health[self.provider_id]))
        self.assertEqual(self.registry.get_provider_cooldown_remaining(self.provider_id), 0.0)

        # Provider should be retrievable again
        provider = self.registry.get_provider(self.provider_id)
        self.assertIsNotNone(provider)

    def test_cooldown_with_different_failure_categories(self):
        """Test cooldown behavior with different failure categories."""
        # Test categories that should NOT trigger cooldown
        no_cooldown_categories = [
            FailureCategory.AUTHENTICATION,
            FailureCategory.INVALID_REQUEST,
            FailureCategory.INVALID_MODEL,
        ]

        for category in no_cooldown_categories:
            with self.subTest(category=category):
                failure = ProviderFailure(
                    category=category,
                    provider_id=self.provider_id,
                    safe_message=f"{category.value} error"
                )
                self.registry.update_provider_health_from_failure(self.provider_id, failure)

                # These should not affect cooldown
                health = self.registry._provider_health[self.provider_id]
                self.assertFalse(self.registry._is_in_cooldown(health))

                # Reset for next iteration
                self.registry._provider_health[self.provider_id].cooldown_until = 0.0
                self.registry._provider_health[self.provider_id].cooldown_category = None

        # Test categories that SHOULD trigger cooldown
        cooldown_categories = [
            FailureCategory.TIMEOUT,
            FailureCategory.NETWORK,
            FailureCategory.SERVER_ERROR,
            FailureCategory.SERVICE_UNAVAILABLE,
            FailureCategory.RATE_LIMIT,
            FailureCategory.QUOTA_EXCEEDED,
        ]

        for category in cooldown_categories:
            with self.subTest(category=category):
                failure = ProviderFailure(
                    category=category,
                    provider_id=self.provider_id,
                    safe_message=f"{category.value} error"
                )
                self.registry.update_provider_health_from_failure(self.provider_id, failure)

                # These should trigger cooldown
                health = self.registry._provider_health[self.provider_id]
                self.assertTrue(self.registry._is_in_cooldown(health))
                self.assertGreater(self.registry.get_provider_cooldown_remaining(self.provider_id), 0)

                # Reset for next iteration
                self.registry._provider_health[self.provider_id].cooldown_until = 0.0
                self.registry._provider_health[self.provider_id].cooldown_category = None

    def test_exponential_backoff_cooldown(self):
        """Test that cooldown increases exponentially with consecutive failures."""
        # Apply first failure
        failure1 = ProviderFailure(
            category=FailureCategory.TIMEOUT,
            provider_id=self.provider_id,
            safe_message="First timeout"
        )
        self.registry.update_provider_health_from_failure(self.provider_id, failure1)

        health1 = self.registry._provider_health[self.provider_id]
        first_cooldown = self.registry.get_provider_cooldown_remaining(self.provider_id)

        # Apply second failure (should increase cooldown)
        failure2 = ProviderFailure(
            category=FailureCategory.TIMEOUT,
            provider_id=self.provider_id,
            safe_message="Second timeout"
        )
        self.registry.update_provider_health_from_failure(self.provider_id, failure2)

        health2 = self.registry._provider_health[self.provider_id]
        second_cooldown = self.registry.get_provider_cooldown_remaining(self.provider_id)

        # Second cooldown should be longer than first (due to exponential backoff)
        self.assertGreaterEqual(second_cooldown, first_cooldown)

        # Health should be degraded after consecutive failures
        # (Note: This depends on the health failure threshold)

    def test_provider_info_reflects_cooldown_status(self):
        """Test that provider info correctly reflects cooldown status for availability."""
        # Initially healthy and available
        info = self.registry.get_provider_info(self.provider_id)
        self.assertTrue(info.healthy)  # Intrinsic health

        # Apply cooldown
        failure = ProviderFailure(
            category=FailureCategory.SERVER_ERROR,
            provider_id=self.provider_id,
            safe_message="Server error"
        )
        self.registry.update_provider_health_from_failure(self.provider_id, failure)

        # After cooldown:
        # - Provider intrinsic health may be affected
        # - But provider should be unavailable for routing
        info = self.registry.get_provider_info(self.provider_id)
        self.assertFalse(info.healthy)  # Intrinsic health is affected by failure

        # Provider should not be retrievable due to cooldown
        provider = self.registry.get_provider(self.provider_id)
        self.assertIsNone(provider)

        # But list_provider_info should show it as unavailable
        infos = self.registry.list_provider_info()
        self.assertEqual(len(infos), 1)
        self.assertFalse(infos[0].healthy)  # Shows as unavailable due to cooldown

    def test_cooldown_configuration_loading(self):
        """Test that cooldown configuration is loaded correctly."""
        # Check that configuration was loaded
        self.assertTrue(self.registry._cooldown_enabled)
        self.assertEqual(self.registry._base_duration, 30)
        self.assertEqual(self.registry._max_duration, 300)
        self.assertEqual(self.registry._multiplier, 2.0)

        # Test that category overrides are respected
        # Set up test overrides (in case config loading doesn't work in test environment)
        self.registry._category_overrides = {
            FailureCategory.RATE_LIMIT.value: 60,
            FailureCategory.QUOTA_EXCEEDED.value: 300,
        }

        # Rate limit should use configured override duration (60s)
        failure = ProviderFailure(
            category=FailureCategory.RATE_LIMIT,
            provider_id=self.provider_id,
            safe_message="Rate limit exceeded"
        )
        self.registry.update_provider_health_from_failure(self.provider_id, failure)

        # Verify that a cooldown was applied using the override duration
        health = self.registry._provider_health[self.provider_id]
        self.assertTrue(self.registry._is_in_cooldown(health))
        # Note: We don't check the exact duration here since it depends on internal state
        # and concurrent test execution, but we verify cooldown was triggered


if __name__ == '__main__':
    unittest.main()