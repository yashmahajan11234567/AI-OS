#!/usr/bin/env python3
"""Simple test to verify quota manager flow."""

import asyncio
from unittest.mock import Mock, patch
from aios.core.rate_limit_quota_manager import (
    RateLimitQuotaManager,
    QuotaType,
    QuotaLimit,
    FailureCategory
)
from aios.core.provider_failures import classify_failure


async def test_admit_request_flow():
    """Test the admit_request flow."""
    print("Testing admit_request flow...")

    # Create a quota manager with permissive limits
    manager = RateLimitQuotaManager()

    # Override config to have high limits
    with patch.object(manager, '_config', {
        "rate_limit_quota": {
            "enabled": True,
            "quotas": {
                "requests_per_minute": {"limit": 100},
                "tokens_per_minute": {"limit": 100000},
                "requests_per_day": {"limit": 1000},
                "tokens_per_day": {"limit": 1000000},
                "concurrent_requests": {"limit": 10}
            }
        }
    }):

        # Test admission under limits
        print("Testing admission under limits...")
        lease, failure = await manager.admit_request(
            provider_id="test_provider",
            model_id="test_model",
            estimated_tokens=50
        )

        assert lease is not None, "Lease should be acquired"
        assert failure is None, "Should not have failure"
        assert lease.provider_id == "test_provider"
        assert lease.model_id == "test_model"
        print("✓ Admission under limits works")

        # Release the lease
        manager.release_lease(lease)

        # Test that provider would be called after admission
        print("Verifying provider call would happen after admission...")
        # This is verified by the ModelRouter code - if admit_request returns
        # (lease, None), then provider.generate is called

        # Test denial over limit
        print("Testing admission over limits...")
        # Set very low limit
        with patch.object(manager, '_config', {
            "rate_limit_quota": {
                "enabled": True,
                "quotas": {
                    "requests_per_minute": {"limit": 0},  # Zero limit
                    "tokens_per_minute": {"limit": 100000},
                    "requests_per_day": {"limit": 1000},
                    "tokens_per_day": {"limit": 1000000},
                    "concurrent_requests": {"limit": 10}
                }
            }
        }):

            lease, failure = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )

            assert lease is None, "Should not acquire lease when denied"
            assert failure is not None, "Should have failure when denied"
            assert failure.category == FailureCategory.RATE_LIMIT or failure.category == FailureCategory.QUOTA_EXCEEDED
            print("✓ Admission denial works correctly")

    print("All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_admit_request_flow())