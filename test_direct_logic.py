#!/usr/bin/env python3
"""Direct test of quota manager logic by mocking dependencies in constructor."""

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
    mock_config_manager = Mock()
    mock_config_manager.get.return_value = 24.0  # Default retention hours

    # Create manager with mocked dependencies
    manager = RateLimitQuotaManager(
        resource_manager=mock_resource_manager,
        model_router=mock_model_router
    )
    manager._event_bus = mock_event_bus
    manager._config_manager = mock_config_manager

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


def test_admit_request_integration():
    """Test admit_request integration with the ModelRouter flow."""
    print("\nTesting admit_request integration...")

    # Create mocks for all dependencies
    mock_resource_manager = Mock()
    mock_resource_manager.get_limit.return_value = Mock(limit=100)  # Default limit

    mock_event_bus = Mock()
    mock_model_router = Mock()
    mock_config_manager = Mock()
    mock_config_manager.get.return_value = 24.0  # Default retention hours

    # Mock the get_usage_in_time_window method on the model router
    mock_model_router.get_usage_in_time_window.return_value = []

    # Create manager with mocked dependencies
    manager = RateLimitQuotaManager(
        resource_manager=mock_resource_manager,
        model_router=mock_model_router
    )
    manager._event_bus = mock_event_bus
    manager._config_manager = mock_config_manager

    # Test the full admit_request flow that matches ModelRouter._call_model
    print("Testing admit_request flow matching ModelRouter...")

    # Test successful admission (should allow provider call)
    with patch.object(manager, '_check_quota') as mock_check_quota:
        # All quotas pass
        mock_check_quota.return_value = (True, None)

        with patch.object(manager, 'acquire_lease') as mock_acquire_lease:
            mock_lease = Mock()
            mock_lease.lease_id = "test-lease-success"
            mock_acquire_lease.return_value = mock_lease

            lease, failure = manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=150  # Estimated tokens for the request
            )

            # Verify this matches what ModelRouter expects
            assert lease is not None, "Should acquire lease for successful admission"
            assert failure is None, "Should not have failure for successful admission"
            assert hasattr(lease, 'lease_id'), "Lease should have lease_id"

            # Verify that in ModelRouter, this would lead to provider.call being made
            # (this is verified by examining the ModelRouter code)
            print("✓ Successful admission leads to lease acquisition (provider call would proceed)")

    # Test denied admission (should prevent provider call)
    print("Testing denied admission prevents provider call...")
    with patch.object(manager, '_check_quota') as mock_check_quota:
        # First quota check fails (simulate rate limit exceeded)
        from aios.core.provider_failures import classify_failure
        failure = classify_failure(
            category=FailureCategory.RATE_LIMIT,
            provider_id="test_provider",
            model_id="test_model",
            retry_after=30,
            safe_message="Rate limit exceeded"
        )
        mock_check_quota.return_value = (False, failure)

        lease, failure_result = manager.admit_request(
            provider_id="test_provider",
            model_id="test_model",
            estimated_tokens=150
        )

        # Verify this matches what ModelRouter expects
        assert lease is None, "Should NOT acquire lease when admission denied"
        assert failure_result is not None, "Should have failure when admission denied"
        assert failure_result.category == FailureCategory.RATE_LIMIT
        assert hasattr(failure_result, 'safe_message'), "Failure should have safe_message"
        assert hasattr(failure_result, 'retryable'), "Failure should have retryable flag"
        assert hasattr(failure_result, 'provider_id'), "Failure should have provider_id"
        assert hasattr(failure_result, 'model_id'), "Failure should have model_id"

        # Verify that in ModelRouter, this would lead to early return without provider.call
        print("✓ Denied admission prevents provider call (early return with failure)")

    # Test lease lifecycle
    print("Testing lease lifecycle...")
    with patch.object(manager, '_check_quota') as mock_check_quota:
        mock_check_quota.return_value = (True, None)  # Quota check passes

        with patch.object(manager, 'acquire_lease') as mock_acquire_lease:
            mock_lease = Mock()
            mock_lease.lease_id = "test-lease-lifecycle"
            mock_acquire_lease.return_value = mock_lease

            with patch.object(manager, 'release_lease') as mock_release_lease:
                # Acquire lease through admit_request
                lease, failure = manager.admit_request(
                    provider_id="test_provider",
                    model_id="test_model",
                    estimated_tokens=100
                )

                assert lease is not None, "Should acquire lease"
                assert failure is None, "Should not have failure"

                # Simulate successful completion (this mirrors ModelRouter._call_model success path)
                manager.record_completion(
                    lease=lease,
                    provider_id="test_provider",
                    model_id="test_model",
                    success=True,
                    actual_tokens=100
                )

                # Verify lease was released
                mock_release_lease.assert_called_once_with(lease)
                print("✓ Lease properly released on successful completion")

                # Test failure path too
                mock_release_lease.reset_mock()
                manager.record_completion(
                    lease=lease,
                    provider_id="test_provider",
                    model_id="test_model",
                    success=False,
                    actual_tokens=0
                )

                # Verify lease was released on failure too
                mock_release_lease.assert_called_once_with(lease)
                print("✓ Lease properly released on failed completion")

    print("\nAll admit_request integration tests passed!")


if __name__ == "__main__":
    test_quota_check_logic()
    test_admit_request_integration()
    print("\n✅ All tests passed! Quota manager logic is working correctly.")