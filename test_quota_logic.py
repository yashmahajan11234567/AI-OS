#!/usr/bin/env python3
"""Test to verify quota manager logic without full initialization."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import Mock, patch
from aios.core.rate_limit_quota_manager import (
    RateLimitQuotaManager,
    QuotaType,
    QuotaLimit
)
from aios.core.provider_failures import FailureCategory


def test_quota_check_logic():
    """Test the quota checking logic directly."""
    print("Testing quota check logic...")

    # Create mocks for all dependencies
    mock_resource_manager = Mock()
    mock_resource_manager.get_limit.return_value = Mock(limit=100)  # Default limit

    mock_event_bus = Mock()
    mock_model_router = Mock()

    # Patch the singleton functions to return our mocks
    with patch('aios.core.rate_limit_quota_manager.get_resource_manager', return_value=mock_resource_manager), \
         patch('aios.core.rate_limit_quota_manager.get_core_event_bus', return_value=mock_event_bus), \
         patch('aios.core.rate_limit_quota_manager.get_model_router', return_value=mock_model_router), \
         patch('aios.core.configuration_manager.get_configuration_manager', return_value=Mock()):

        manager = RateLimitQuotaManager()

        # Mock the get_usage_in_time_window method on the model router
        mock_model_router.get_usage_in_time_window.return_value = []

        # Test REQUESTS_PER_MINUTE -> RATE_LIMIT mapping
        print("Testing REQUESTS_PER_MINUTE -> RATE_LIMIT mapping...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.REQUESTS_PER_MINUTE,
                limit=100,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 50  # Currently at 50
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=50):
                    allowed, failure = manager._check_quota(
                        QuotaType.REQUESTS_PER_MINUTE,
                        "test_provider",
                        "test_model",
                        requested_amount=60  # Would put us at 110, over limit of 100
                    )

                    assert not allowed, "Should deny request"
                    assert failure is not None, "Should have failure"
                    assert failure.category == FailureCategory.RATE_LIMIT, f"Expected RATE_LIMIT, got {failure.category}"
                    assert failure.retryable == True, "Minute-based quotas should be retryable"
                    print("✓ REQUESTS_PER_MINUTE correctly maps to RATE_LIMIT and is retryable")

        # Test REQUESTS_PER_DAY -> QUOTA_EXCEEDED mapping
        print("Testing REQUESTS_PER_DAY -> QUOTA_EXCEEDED mapping...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.REQUESTS_PER_DAY,
                limit=1000,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 950  # Currently at 950
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=950):
                    allowed, failure = manager._check_quota(
                        QuotaType.REQUESTS_PER_DAY,
                        "test_provider",
                        "test_model",
                        requested_amount=100  # Would put us at 1050, over limit of 1000
                    )

                    assert not allowed, "Should deny request"
                    assert failure is not None, "Should have failure"
                    assert failure.category == FailureCategory.QUOTA_EXCEEDED, f"Expected QUOTA_EXCEEDED, got {failure.category}"
                    assert failure.retryable == False, "Daily quotas should not be retryable"
                    print("✓ REQUESTS_PER_DAY correctly maps to QUOTA_EXCEEDED and is not retryable")

        # Test TOKENS_PER_MINUTE -> RATE_LIMIT mapping
        print("Testing TOKENS_PER_MINUTE -> RATE_LIMIT mapping...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.TOKENS_PER_MINUTE,
                limit=50000,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 40000  # Currently at 40k
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=40000):
                    allowed, failure = manager._check_quota(
                        QuotaType.TOKENS_PER_MINUTE,
                        "test_provider",
                        "test_model",
                        requested_amount=15000  # Would put us at 55k, over limit of 50k
                    )

                    assert not allowed, "Should deny request"
                    assert failure is not None, "Should have failure"
                    assert failure.category == FailureCategory.RATE_LIMIT, f"Expected RATE_LIMIT, got {failure.category}"
                    assert failure.retryable == True, "Minute-based quotas should be retryable"
                    print("✓ TOKENS_PER_MINUTE correctly maps to RATE_LIMIT and is retryable")

        # Test TOKENS_PER_DAY -> QUOTA_EXCEEDED mapping
        print("Testing TOKENS_PER_DAY -> QUOTA_EXCEEDED mapping...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.TOKENS_PER_DAY,
                limit=1000000,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 900000  # Currently at 900k
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=900000):
                    allowed, failure = manager._check_quota(
                        QuotaType.TOKENS_PER_DAY,
                        "test_provider",
                        "test_model",
                        requested_amount=150000  # Would put us at 1.05M, over limit of 1M
                    )

                    assert not allowed, "Should deny request"
                    assert failure is not None, "Should have failure"
                    assert failure.category == FailureCategory.QUOTA_EXCEEDED, f"Expected QUOTA_EXCEEDED, got {failure.category}"
                    assert failure.retryable == False, "Daily quotas should not be retryable"
                    print("✓ TOKENS_PER_DAY correctly maps to QUOTA_EXCEEDED and is not retryable")

        # Test CONCURRENT_REQUESTS -> QUOTA_EXCEEDED mapping
        print("Testing CONCURRENT_REQUESTS -> QUOTA_EXCEEDED mapping...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.CONCURRENT_REQUESTS,
                limit=10,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 8  # Currently at 8
                mock_usage.concurrent_count = 8
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=0):  # Not used for concurrent
                    allowed, failure = manager._check_quota(
                        QuotaType.CONCURRENT_REQUESTS,
                        "test_provider",
                        "test_model",
                        requested_amount=5  # Would put us at 13, over limit of 10
                    )

                    assert not allowed, "Should deny request"
                    assert failure is not None, "Should have failure"
                    assert failure.category == FailureCategory.QUOTA_EXCEEDED, f"Expected QUOTA_EXCEEDED, got {failure.category}"
                    assert failure.retryable == True, "Concurrent quotas should be retryable"
                    print("✓ CONCURRENT_REQUESTS correctly maps to QUOTA_EXCEEDED and is retryable")

        # Test that requests under limit are allowed
        print("Testing requests under limit are allowed...")
        with patch.object(manager, '_get_quota_limit') as mock_get_limit:
            mock_get_limit.return_value = QuotaLimit(
                quota_type=QuotaType.REQUESTS_PER_MINUTE,
                limit=100,
                enabled=True
            )

            with patch.object(manager, '_get_or_create_usage_tracking') as mock_get_usage:
                mock_usage = Mock()
                mock_usage.current_usage = 50  # Currently at 50
                mock_get_usage.return_value = mock_usage

                with patch.object(manager, '_update_usage_from_records', return_value=50):
                    allowed, failure = manager._check_quota(
                        QuotaType.REQUESTS_PER_MINUTE,
                        "test_provider",
                        "test_model",
                        requested_amount=30  # Would put us at 80, under limit of 100
                    )

                    assert allowed, "Should allow request"
                    assert failure is None, "Should not have failure"
                    print("✓ Requests under limit are correctly allowed")

    print("\nAll quota logic tests passed!")


def test_admit_request_lease_behavior():
    """Test admit_request lease behavior."""
    print("\nTesting admit_request lease behavior...")

    # Create mocks for all dependencies
    mock_resource_manager = Mock()
    mock_resource_manager.get_limit.return_value = Mock(limit=100)  # Default limit

    mock_event_bus = Mock()
    mock_model_router = Mock()
    mock_model_router.get_usage_in_time_window.return_value = []
    mock_config_manager = Mock()
    mock_config_manager.get.return_value = 24.0  # Default retention hours

    # Patch the singleton functions to return our mocks
    with patch('aios.core.rate_limit_quota_manager.get_resource_manager', return_value=mock_resource_manager), \
         patch('aios.core.rate_limit_quota_manager.get_core_event_bus', return_value=mock_event_bus), \
         patch('aios.core.rate_limit_quota_manager.get_model_router', return_value=mock_model_router), \
         patch('aios.core.configuration_manager.get_configuration_manager', return_value=mock_config_manager):

        manager = RateLimitQuotaManager()

        # Test that lease is acquired when all quotas pass
        print("Testing lease acquisition when quotas pass...")
        with patch.object(manager, '_check_quota') as mock_check_quota:
            # All quotas pass
            mock_check_quota.return_value = (True, None)

            with patch.object(manager, 'acquire_lease') as mock_acquire_lease:
                mock_lease = Mock()
                mock_lease.lease_id = "test-lease-123"
                mock_acquire_lease.return_value = mock_lease

                lease, failure = manager.admit_request(
                    provider_id="test_provider",
                    model_id="test_model",
                    estimated_tokens=100
                )

                assert lease is not None, "Should acquire lease"
                assert failure is None, "Should not have failure"
                assert lease.lease_id == "test-lease-123"
                print("✓ Lease acquired when quotas pass")

        # Test that no lease is acquired when quota check fails
        print("Testing no lease acquisition when quota check fails...")
        with patch.object(manager, '_check_quota') as mock_check_quota:
            # First quota fails
            from aios.core.provider_failures import classify_failure
            failure = classify_failure(
                category=FailureCategory.RATE_LIMIT,
                provider_id="test_provider",
                model_id="test_model"
            )
            mock_check_quota.return_value = (False, failure)

            lease, failure_result = manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=100
            )

            assert lease is None, "Should not acquire lease when quota check fails"
            assert failure_result is not None, "Should have failure"
            assert failure_result.category == FailureCategory.RATE_LIMIT
            print("✓ No lease acquired when quota check fails")

        # Test that lease is released on success
        print("Testing lease release on success...")
        with patch.object(manager, '_check_quota') as mock_check_quota:
            mock_check_quota.return_value = (True, None)

            with patch.object(manager, 'acquire_lease') as mock_acquire_lease:
                mock_lease = Mock()
                mock_lease.lease_id = "test-lease-456"
                mock_acquire_lease.return_value = mock_lease

                with patch.object(manager, 'release_lease') as mock_release_lease:
                    # Simulate successful completion
                    manager.record_completion(
                        lease=mock_lease,
                        provider_id="test_provider",
                        model_id="test_model",
                        success=True,
                        actual_tokens=100
                    )

                    mock_release_lease.assert_called_once_with(mock_lease)
                    print("✓ Lease released on successful completion")

        # Test that lease is released on failure
        print("Testing lease release on failure...")
        with patch.object(manager, '_check_quota') as mock_check_quota:
            mock_check_quota.return_value = (True, None)

            with patch.object(manager, 'acquire_lease') as mock_acquire_lease:
                mock_lease = Mock()
                mock_lease.lease_id = "test-lease-789"
                mock_acquire_lease.return_value = mock_lease

                with patch.object(manager, 'release_lease') as mock_release_lease:
                    # Simulate failed completion
                    manager.record_completion(
                        lease=mock_lease,
                        provider_id="test_provider",
                        model_id="test_model",
                        success=False,
                        actual_tokens=0
                    )

                    mock_release_lease.assert_called_once_with(mock_lease)
                    print("✓ Lease released on failed completion")

    print("\nAll admit_request lease behavior tests passed!")


if __name__ == "__main__":
    test_quota_check_logic()
    test_admit_request_lease_behavior()
    print("\n✅ All tests passed! Quota manager logic is working correctly.")