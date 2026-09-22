import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from aios.core.rate_limit_quota_manager import (
    RateLimitQuotaManager,
    QuotaType,
    QuotaLimit,
    get_rate_limit_quota_manager
)
from aios.events.core.identity import ComponentIdentity
from aios.events.core.types import SemanticVersion


class TestRateLimitQuotaManager:
    """Test the RateLimitQuotaManager implementation."""

    def test_singleton_pattern(self):
        """Test that get_rate_limit_quota_manager returns the same instance."""
        manager1 = get_rate_limit_quota_manager()
        manager2 = get_rate_limit_quota_manager()
        assert manager1 is manager2

    def test_quota_types_exist(self):
        """Test that all expected quota types exist."""
        assert hasattr(QuotaType, 'REQUESTS_PER_MINUTE')
        assert hasattr(QuotaType, 'REQUESTS_PER_DAY')
        assert hasattr(QuotaType, 'TOKENS_PER_MINUTE')
        assert hasattr(QuotaType, 'TOKENS_PER_DAY')
        assert hasattr(QuotaType, 'CONCURRENT_REQUESTS')

    def test_quota_limit_creation(self):
        """Test creating quota limits."""
        limit = QuotaLimit(
            quota_type=QuotaType.REQUESTS_PER_MINUTE,
            limit=100
        )
        assert limit.quota_type == QuotaType.REQUESTS_PER_MINUTE
        assert limit.limit == 100

    @pytest.mark.asyncio
    async def test_admit_request_under_limit(self):
        """Test admitting a request when under quota limits."""
        manager = RateLimitQuotaManager()

        # Configure a high limit to allow the request
        config = {
            "rate_limit_quota": {
                "enabled": True,
                "quotas": {
                    "requests_per_minute": {
                        "limit": 1000,
                        "window_seconds": 60
                    },
                    "tokens_per_minute": {
                        "limit": 100000,
                        "window_seconds": 60
                    },
                    "concurrent_requests": {
                        "limit": 100,
                        "window_seconds": 60
                    }
                }
            }
        }

        with patch.object(manager, '_config', config):
            lease, failure = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )

            # Should succeed with a lease
            assert lease is not None
            assert failure is None
            assert lease.provider_id == "test_provider"
            assert lease.model_id == "test_model"

            # Release the lease
            manager.release_lease(lease)

    @pytest.mark.asyncio
    async def test_admit_request_over_limit(self):
        """Test admitting a request when over quota limits."""
        manager = RateLimitQuotaManager()

        # Configure a low limit that will be exceeded
        config = {
            "rate_limit_quota": {
                "enabled": True,
                "quotas": {
                    "requests_per_minute": {
                        "limit": 1,  # Very low limit
                        "window_seconds": 60
                    },
                    "tokens_per_minute": {
                        "limit": 100000,
                        "window_seconds": 60
                    },
                    "concurrent_requests": {
                        "limit": 100,
                        "window_seconds": 60
                    }
                }
            }
        }

        with patch.object(manager, '_config', config):
            # First request should succeed
            lease1, failure1 = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )
            assert lease1 is not None
            assert failure1 is None

            # Second request should fail due to quota exceeded
            lease2, failure2 = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )
            assert lease2 is None
            assert failure2 is not None
            assert failure2.category.value == "quota_exceeded"

            # Clean up
            if lease1:
                manager.release_lease(lease1)

    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self):
        """Test concurrent request limiting."""
        manager = RateLimitQuotaManager()

        # Configure low concurrent limit
        config = {
            "rate_limit_quota": {
                "enabled": True,
                "quotas": {
                    "requests_per_minute": {
                        "limit": 1000,
                        "window_seconds": 60
                    },
                    "tokens_per_minute": {
                        "limit": 100000,
                        "window_seconds": 60
                    },
                    "concurrent_requests": {
                        "limit": 2,  # Only allow 2 concurrent requests
                        "window_seconds": 60
                    }
                }
            }
        }

        with patch.object(manager, '_config', config):
            # Acquire two leases (should succeed)
            lease1, failure1 = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )
            assert lease1 is not None
            assert failure1 is None

            lease2, failure2 = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )
            assert lease2 is not None
            assert failure2 is None

            # Third request should fail due to concurrent limit
            lease3, failure3 = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )
            assert lease3 is None
            assert failure3 is not None
            assert failure3.category.value == "rate_limit"

            # Clean up
            if lease1:
                manager.release_lease(lease1)
            if lease2:
                manager.release_lease(lease2)

    @pytest.mark.asyncio
    async def test_quota_manager_disabled(self):
        """Test behavior when quota manager is disabled."""
        manager = RateLimitQuotaManager()

        # Disable the quota manager
        config = {
            "rate_limit_quota": {
                "enabled": False
            }
        }

        with patch.object(manager, '_config', config):
            lease, failure = await manager.admit_request(
                provider_id="test_provider",
                model_id="test_model",
                estimated_tokens=50
            )

            # Should succeed with a lease when disabled
            assert lease is not None
            assert failure is None

            # Clean up
            if lease:
                manager.release_lease(lease)

    def test_release_lease(self):
        """Test releasing a lease."""
        manager = RateLimitQuotaManager()
        lease = manager._create_lease("test_provider", "test_model")

        # Should not raise an exception
        manager.release_lease(lease)

        # Releasing same lease twice should not raise an exception
        manager.release_lease(lease)

    def test_cleanup_old_leases(self):
        """Test that old leases are cleaned up."""
        manager = RateLimitQuotaManager()

        # Create a lease and manually make it old
        lease = manager._create_lease("test_provider", "test_model")
        lease.acquired_at = time.time() - 7200  # 2 hours old

        # Manually add to active leases
        manager._active_leases.append(lease)

        # Admit a new request to trigger cleanup
        import asyncio
        async def test_cleanup():
            config = {
                "rate_limit_quota": {
                    "enabled": True,
                    "quotas": {
                        "requests_per_minute": {
                            "limit": 1000,
                            "window_seconds": 60
                        },
                        "tokens_per_minute": {
                            "limit": 100000,
                            "window_seconds": 60
                        },
                        "concurrent_requests": {
                            "limit": 100,
                            "window_seconds": 60
                        }
                    }
                }
            }

            with patch.object(manager, '_config', config):
                lease2, failure = await manager.admit_request(
                    provider_id="test_provider",
                    model_id="test_model",
                    estimated_tokens=50
                )

                # Old lease should have been cleaned up
                assert len(manager._active_leases) == 1  # Only the new lease

                if lease2:
                    manager.release_lease(lease2)

        asyncio.run(test_cleanup())

    def test_instantiation_without_model_router(self):
        """Test that RateLimitQuotaManager can be instantiated without explicitly passing model_router.

        This is a regression test for the NameError: name 'get_model_router' is not defined
        that occurred when the get_model_router import was missing.
        """
        # This should not raise a NameError
        # Mock the dependencies that cause circular import issues during testing
        with patch('aios.core.rate_limit_quota_manager.get_configuration_manager'), \
             patch('aios.core.rate_limit_quota_manager.get_resource_manager'), \
             patch('aios.core.rate_limit_quota_manager.get_core_event_bus'), \
             patch('aios.core.rate_limit_quota_manager.ComponentIdentity'):
            manager = RateLimitQuotaManager()
            assert manager is not None
            # Verify that the model_router attribute was set (via get_model_router())
            assert hasattr(manager, '_model_router')
            assert manager._model_router is not None

    def test_component_identity_version_type(self):
        """Test that RateLimitQuotaManager creates ComponentIdentity with correct SemanticVersion type.

        This is a regression test for the TypeError: version must be SemanticVersion or None, got str
        that occurred when RateLimitQuotaManager passed a string instead of SemanticVersion to ComponentIdentity.
        """
        # This should not raise a TypeError
        manager = RateLimitQuotaManager()

        # Verify that the identity was created correctly
        assert hasattr(manager, '_identity')
        assert isinstance(manager._identity, ComponentIdentity)

        # Verify that the version is a SemanticVersion object, not a string
        assert isinstance(manager._identity.version, SemanticVersion)
        assert manager._identity.version.major == 1
        assert manager._identity.version.minor == 0
        assert manager._identity.version.patch == 0

        # Verify the string representation is correct
        assert str(manager._identity.version) == "1.0.0"

def test_component_identity_version_type(self):
        """Test that RateLimitQuotaManager creates ComponentIdentity with correct SemanticVersion type.

        This is a regression test for the TypeError: version must be SemanticVersion or None, got str
        that occurred when RateLimitQuotaManager passed a string instead of SemanticVersion to ComponentIdentity.
        """
        # This should not raise a TypeError
        manager = RateLimitQuotaManager()

        # Verify that the identity was created correctly
        assert hasattr(manager, '_identity')
        assert isinstance(manager._identity, ComponentIdentity)

        # Verify that the version is a SemanticVersion object, not a string
        assert isinstance(manager._identity.version, SemanticVersion)
        assert manager._identity.version.major == 1
        assert manager._identity.version.minor == 0
        assert manager._identity.version.patch == 0

        # Verify the string representation is correct
        assert str(manager._identity.version) == "1.0.0"

if __name__ == "__main__":
    pytest.main([__file__])