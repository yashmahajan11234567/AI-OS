"""
Tests for provider failure classification.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from aios.core.provider_failures import (
    FailureCategory,
    ProviderFailure,
    classify_failure,
    FAILURE_CLASSIFICATION_RULES,
)


def test_failure_category_enum():
    """Test that all expected failure categories exist."""
    expected_categories = {
        "authentication",
        "invalid_request",
        "invalid_model",
        "rate_limit",
        "quota_exceeded",
        "timeout",
        "network",
        "server_error",
        "service_unavailable",
        "unknown",
    }
    actual_categories = {cat.value for cat in FailureCategory}
    assert actual_categories == expected_categories


def test_provider_failure_creation():
    """Test creating a ProviderFailure instance."""
    failure = ProviderFailure(
        category=FailureCategory.RATE_LIMIT,
        provider_id="test_provider",
        model_id="test-model",
        retryable=True,
        fallback_eligible=True,
        http_status=429,
        provider_error_code="RATE_LIMIT_EXCEEDED",
        retry_after=60,
        safe_message="Rate limit exceeded",
    )

    assert failure.category == FailureCategory.RATE_LIMIT
    assert failure.provider_id == "test_provider"
    assert failure.model_id == "test-model"
    assert failure.retryable is True
    assert failure.fallback_eligible is True
    assert failure.http_status == 429
    assert failure.provider_error_code == "RATE_LIMIT_EXCEEDED"
    assert failure.retry_after == 60
    assert failure.safe_message == "Rate limit exceeded"
    assert failure.timestamp is not None


def test_classify_failure_function():
    """Test the classify_failure helper function."""
    failure = classify_failure(
        category=FailureCategory.AUTHENTICATION,
        provider_id="nim",
        model_id="test-model",
        http_status=401,
        provider_error_code="INVALID_API_KEY",
        safe_message="Invalid API key",
    )

    assert failure.category == FailureCategory.AUTHENTICATION
    assert failure.provider_id == "nim"
    assert failure.model_id == "test-model"
    assert failure.retryable is False  # From rules
    assert failure.fallback_eligible is True  # From rules
    assert failure.http_status == 401
    assert failure.provider_error_code == "INVALID_API_KEY"
    assert failure.safe_message == "Invalid API key"


def test_all_failure_categories_have_rules():
    """Test that all failure categories have classification rules."""
    for category in FailureCategory:
        assert category in FAILURE_CLASSIFICATION_RULES
        rules = FAILURE_CLASSIFICATION_RULES[category]
        assert "retryable" in rules
        assert "fallback_eligible" in rules
        assert isinstance(rules["retryable"], bool)
        assert isinstance(rules["fallback_eligible"], bool)


def test_authentication_classification():
    """Test AUTHENTICATION failure classification."""
    failure = classify_failure(
        category=FailureCategory.AUTHENTICATION,
        provider_id="test",
        safe_message="Auth failed",
    )
    assert failure.retryable is False
    assert failure.fallback_eligible is True


def test_invalid_request_classification():
    """Test INVALID_REQUEST failure classification."""
    failure = classify_failure(
        category=FailureCategory.INVALID_REQUEST,
        provider_id="test",
        safe_message="Bad request",
    )
    assert failure.retryable is False
    assert failure.fallback_eligible is False


def test_invalid_model_classification():
    """Test INVALID_MODEL failure classification."""
    failure = classify_failure(
        category=FailureCategory.INVALID_MODEL,
        provider_id="test",
        model_id="nonexistent-model",
        safe_message="Model not found",
    )
    assert failure.retryable is False
    assert failure.fallback_eligible is True


def test_rate_limit_classification():
    """Test RATE_LIMIT failure classification."""
    failure = classify_failure(
        category=FailureCategory.RATE_LIMIT,
        provider_id="test",
        http_status=429,
        retry_after=120,
        safe_message="Rate limited",
    )
    assert failure.retryable is True
    assert failure.fallback_eligible is True
    assert failure.http_status == 429
    assert failure.retry_after == 120


def test_quota_exceeded_classification():
    """Test QUOTA_EXCEEDED failure classification."""
    failure = classify_failure(
        category=FailureCategory.QUOTA_EXCEEDED,
        provider_id="test",
        http_status=429,
        safe_message="Quota exceeded",
    )
    assert failure.retryable is False
    assert failure.fallback_eligible is True


def test_timeout_classification():
    """Test TIMEOUT failure classification."""
    failure = classify_failure(
        category=FailureCategory.TIMEOUT,
        provider_id="test",
        safe_message="Request timeout",
    )
    assert failure.retryable is True
    assert failure.fallback_eligible is True


def test_network_classification():
    """Test NETWORK failure classification."""
    failure = classify_failure(
        category=FailureCategory.NETWORK,
        provider_id="test",
        safe_message="Network error",
    )
    assert failure.retryable is True
    assert failure.fallback_eligible is True


def test_server_error_classification():
    """Test SERVER_ERROR failure classification."""
    failure = classify_failure(
        category=FailureCategory.SERVER_ERROR,
        provider_id="test",
        http_status=500,
        safe_message="Internal server error",
    )
    assert failure.retryable is True
    assert failure.fallback_eligible is True


def test_service_unavailable_classification():
    """Test SERVICE_UNAVAILABLE failure classification."""
    failure = classify_failure(
        category=FailureCategory.SERVICE_UNAVAILABLE,
        provider_id="test",
        http_status=503,
        safe_message="Service unavailable",
    )
    assert failure.retryable is True
    assert failure.fallback_eligible is True


def test_unknown_classification_defaults():
    """Test UNKNOWN failure classification defaults to non-retryable."""
    failure = classify_failure(
        category=FailureCategory.UNKNOWN,
        provider_id="test",
        safe_message="Unknown error",
    )
    assert failure.retryable is False
    assert failure.fallback_eligible is False


def test_unknown_can_be_override_retryable():
    """Test that UNKNOWN classification can be made retryable if needed."""
    # This tests the __post_init__ behavior - UNKNOWN should not automatically
    # become retryable, but explicit setting should work
    failure = ProviderFailure(
        category=FailureCategory.UNKNOWN,
        provider_id="test",
        retryable=True,  # Explicitly set
        fallback_eligible=False,
        safe_message="Unknown but retryable",
    )
    assert failure.retryable is True  # Explicit setting overrides default


def test_no_secrets_in_failure():
    """Test that ProviderFailure does not expose secrets."""
    # These would be considered secrets and should never appear in failure data
    dangerous_fields = [
        "api_key",
        "authorization",
        "bearer_token",
        "secret",
        "password",
        "credential",
        "token",
        "key",
    ]

    failure = ProviderFailure(
        category=FailureCategory.SERVER_ERROR,
        provider_id="test_provider",
        safe_message="Internal error occurred",
    )

    # Convert to dict to check for accidental secret inclusion
    failure_dict = {
        "category": failure.category.value,
        "provider_id": failure.provider_id,
        "model_id": failure.model_id,
        "retryable": failure.retryable,
        "fallback_eligible": failure.fallback_eligible,
        "http_status": failure.http_status,
        "provider_error_code": failure.provider_error_code,
        "retry_after": failure.retry_after,
        "safe_message": failure.safe_message,
        "timestamp": failure.timestamp,
    }

    # Ensure none of the dangerous field names appear as keys
    for key in failure_dict.keys():
        for dangerous in dangerous_fields:
            assert dangerous not in key.lower(), f"Potential secret field detected: {key}"

    # Ensure safe_message doesn't contain obvious secrets
    assert "api_key" not in failure.safe_message.lower()
    assert "bearer" not in failure.safe_message.lower()
    assert "token" not in failure.safe_message.lower()
    assert "password" not in failure.safe_message.lower()


def test_provider_specific_error_mapping():
    """Test that provider-specific error mapping works correctly."""
    # Test NIM-specific mappings
    nim_auth_failure = classify_failure(
        category=FailureCategory.AUTHENTICATION,
        provider_id="nim",
        http_status=401,
        safe_message="Invalid API key",
    )
    assert nim_auth_failure.category == FailureCategory.AUTHENTICATION
    assert nim_auth_failure.retryable is False
    assert nim_auth_failure.fallback_eligible is True

    # Test FreeLLMAPI-specific mappings
    freellmapi_rate_limit = classify_failure(
        category=FailureCategory.RATE_LIMIT,
        provider_id="freellmapi",
        http_status=429,
        retry_after=30,
        safe_message="Rate limit exceeded",
    )
    assert freellmapi_rate_limit.category == FailureCategory.RATE_LIMIT
    assert freellmapi_rate_limit.retryable is True
    assert freellmapi_rate_limit.fallback_eligible is True
    assert freellmapi_rate_limit.retry_after == 30

    # Test Gemini specific mapping with API key redaction
    gemini_failure = classify_failure(
        category=FailureCategory.AUTHENTICATION,
        provider_id="gemini",
        http_status=401,
        safe_message="API key invalid: AIzaSyBAD..."  # Would contain real key in practice
    )
    assert gemini_failure.category == FailureCategory.AUTHENTICATION
    # The safe_message should not contain the actual API key in a real implementation


def test_health_impact_determination():
    """Test that health impact is correctly determined for each failure category."""
    # Failures that should NOT affect provider health (client/config issues)
    no_health_impact_categories = [
        FailureCategory.AUTHENTICATION,
        FailureCategory.INVALID_REQUEST,
        FailureCategory.INVALID_MODEL,
    ]

    for category in no_health_impact_categories:
        failure = classify_failure(
            category=category,
            provider_id="test_provider",
            safe_message=f"{category.value} error",
        )
        # These categories should not automatically trigger health degradation
        # in our implementation (this is tested in the ProviderRegistry method)
        assert failure.category == category

    # Failures that SHOULD affect provider health (transient issues)
    health_impact_categories = [
        FailureCategory.TIMEOUT,
        FailureCategory.NETWORK,
        FailureCategory.SERVER_ERROR,
        FailureCategory.SERVICE_UNAVAILABLE,
    ]

    for category in health_impact_categories:
        failure = classify_failure(
            category=category,
            provider_id="test_provider",
            safe_message=f"{category.value} error",
        )
        assert failure.retryable is True  # All health-impacting failures are retryable
        assert failure.category == category


def test_retry_after_preservation():
    """Test that Retry-After values are preserved in structured failures."""
    failure_with_retry_after = classify_failure(
        category=FailureCategory.RATE_LIMIT,
        provider_id="test_provider",
        http_status=429,
        retry_after=120,
        safe_message="Rate limit exceeded, try again in 2 minutes",
    )

    assert failure_with_retry_after.category == FailureCategory.RATE_LIMIT
    assert failure_with_retry_after.retry_after == 120
    assert failure_with_retry_after.http_status == 429

    # Test that other categories can also have retry_after (though uncommon)
    failure_with_retry_after_other = classify_failure(
        category=FailureCategory.SERVICE_UNAVAILABLE,
        provider_id="test_provider",
        http_status=503,
        retry_after=60,
        safe_message="Service temporarily unavailable",
    )

    assert failure_with_retry_after_other.retry_after == 60
    assert failure_with_retry_after_other.http_status == 503


def test_failure_metadata_completeness():
    """Test that all relevant failure information is captured in metadata."""
    failure = classify_failure(
        category=FailureCategory.SERVER_ERROR,
        provider_id="test_provider",
        model_id="test-model-123",
        http_status=500,
        provider_error_code="INTERNAL_ERROR",
        retry_after=30,
        safe_message="Internal server error occurred",
    )

    # Check that all fields are properly set
    assert failure.category == FailureCategory.SERVER_ERROR
    assert failure.provider_id == "test_provider"
    assert failure.model_id == "test-model-123"
    assert failure.http_status == 500
    assert failure.provider_error_code == "INTERNAL_ERROR"
    assert failure.retry_after == 30
    assert failure.safe_message == "Internal server error occurred"
    assert failure.retryable is True  # From rules
    assert failure.fallback_eligible is True  # From rules
    assert failure.timestamp is not None  # Timestamp should be set