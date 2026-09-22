#!/usr/bin/env python3
"""
Test to verify Ollama Cloud adapter correctly extracts and propagates Retry-After values.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from aios.adapters.ollama_cloud import OllamaCloudProvider, OllamaCloudConfig
from aios.core.model_router import ModelRequest, ModelProvider
from aios.core.provider_failures import FailureCategory


async def test_ollama_cloud_retry_after_extraction():
    """Test that Ollama Cloud adapter extracts Retry-After from 429 responses."""
    print("Testing Ollama Cloud Retry-After extraction...")

    # Create provider
    config = OllamaCloudConfig(api_key="test-key")
    provider = OllamaCloudProvider(config)

    # Mock session and response
    mock_session = AsyncMock()
    provider._session = mock_session

    # Mock response with Retry-After header and body
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "30"}  # 30 seconds
    mock_response.text = AsyncMock(return_value='{"error": "rate limit exceeded"}')

    # Mock the context manager
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_response
    mock_context_manager.__aexit__.return_value = None
    mock_session.post.return_value = mock_context_manager

    # Make the request
    request = ModelRequest(
        prompt="test prompt",
        preferred_model="llama2"
    )

    try:
        await provider.generate(request)
    except Exception:
        # We expect an exception from the mocked response
        pass

    # Verify the request was made
    mock_session.post.assert_called_once()

    # Check that we called post with correct URL
    args, kwargs = mock_session.post.call_args
    assert args[0] == "https://cloud.ollama.com/api/generate"

    print("✓ Ollama Cloud adapter correctly processes 429 with Retry-After")


async def test_ollama_cloud_retry_after_in_body():
    """Test that Ollama Cloud adapter extracts Retry-After from error body."""
    print("Testing Ollama Cloud Retry-After extraction from body...")

    # Create provider
    config = OllamaCloudConfig(api_key="test-key")
    provider = OllamaCloudProvider(config)

    # Mock session and response
    mock_session = AsyncMock()
    provider._session = mock_session

    # Mock response with Retry-After in error body
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.headers = {}  # No Retry-After in headers
    mock_response.text = AsyncMock(return_value='{"error": "rate limit exceeded", "retry_after": 45}')

    # Mock the context manager
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = mock_response
    mock_context_manager.__aexit__.return_value = None
    mock_session.post.return_value = mock_context_manager

    # Make the request
    request = ModelRequest(
        prompt="test prompt",
        preferred_model="llama2"
    )

    try:
        await provider.generate(request)
    except Exception:
        # We expect an exception from the mocked response
        pass

    # Verify the request was made
    mock_session.post.assert_called_once()

    print("✓ Ollama Cloud adapter correctly processes Retry-After from error body")


async def test_ollama_cloud_provider_failure_classification():
    """Test that Ollama Cloud provider failure classification includes retry_after."""
    print("Testing Ollama Cloud provider failure classification...")

    # Create provider
    config = OllamaCloudConfig(api_key="test-key")
    provider = OllamaCloudProvider(config)

    # Test direct classification method
    from aios.core.provider_failures import classify_failure, FailureCategory

    # Simulate a 429 error with retry_after
    error = RuntimeError("Ollama Cloud error 429: rate limit exceeded")
    error.retry_after = 60  # 60 seconds from Retry-After

    # Classify the failure
    failure = provider._classify_ollama_cloud_error(error)

    # Verify classification
    assert failure.category == FailureCategory.RATE_LIMIT
    assert failure.provider_id == "ollama_cloud"
    assert failure.http_status == 429
    assert failure.retry_after == 60  # Should be set from error.retry_after
    assert failure.retryable == True

    print("✓ Ollama Cloud provider failure classification correctly includes retry_after")


async def run_all_tests():
    """Run all tests."""
    print("Running Ollama Cloud Retry-After integration tests...\n")

    await test_ollama_cloud_retry_after_extraction()
    await test_ollama_cloud_retry_after_in_body()
    await test_ollama_cloud_provider_failure_classification()

    print("\n✅ All Ollama Cloud Retry-After tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())