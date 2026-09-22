#!/usr/bin/env python3
"""
Simple test to verify Ollama Cloud adapter correctly extracts Retry-After values.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from aios.adapters.ollama_cloud import OllamaCloudProvider, OllamaCloudConfig
from aios.core.model_router import ModelRequest
from aios.core.provider_failures import extract_retry_after

async def test_extract_retry_after_function():
    """Test the extract_retry_after function directly"""
    print('=== Testing extract_retry_after function ===')

    # Test from headers
    headers = {'Retry-After': '30'}
    body = {}
    retry_after = extract_retry_after(headers, body)
    print(f'From headers: {retry_after} ms')
    assert retry_after == 30000, f"Expected 30000 ms, got {retry_after}"

    # Test from body when no header
    headers = {}
    body = {'retry_after': 45}
    retry_after = extract_retry_after(headers, body)
    print(f'From body: {retry_after} ms')
    assert retry_after == 45000, f"Expected 45000 ms, got {retry_after}"

    # Test header takes precedence
    headers = {'Retry-After': '30'}
    body = {'retry_after': 45}
    retry_after = extract_retry_after(headers, body)
    print(f'Header precedence: {retry_after} ms')
    assert retry_after == 30000, f"Expected 30000 ms, got {retry_after}"

    # Test None when neither present
    headers = {}
    body = {}
    retry_after = extract_retry_after(headers, body)
    print(f'None when missing: {retry_after}')
    assert retry_after is None, f"Expected None, got {retry_after}"

    print('+ All extract_retry_after tests passed')
    return True

async def test_classify_error_method():
    """Test the _classify_ollama_cloud_error method"""
    print('\\n=== Testing _classify_ollama_cloud_error method ===')

    config = OllamaCloudConfig(api_key='test-key')
    provider = OllamaCloudProvider(config)

    # Create a mock exception with retry_after attribute
    class MockException(Exception):
        def __init__(self, message, retry_after=None):
            super().__init__(message)
            self.retry_after = retry_after

    # Test 429 error with retry_after
    exception = MockException("Ollama Cloud error 429: Rate limit exceeded", retry_after=30)
    failure = provider._classify_ollama_cloud_error(exception)

    print(f'Failure category: {failure.category}')
    print(f'Failure retry_after: {failure.retry_after}')
    print(f'Failure http_status: {failure.http_status}')

    assert failure.category.value == 'rate_limit', f"Expected rate_limit, got {failure.category}"
    assert failure.retry_after == 30, f"Expected 30 seconds, got {failure.retry_after}"
    assert failure.http_status == 429, f"Expected 429 status, got {failure.http_status}"

    print('+ _classify_ollama_cloud_error test passed')
    return True

async def run_tests():
    print('Running simplified Ollama Cloud Retry-After tests...')

    test1 = await test_extract_retry_after_function()
    test2 = await test_classify_error_method()

    print(f'\\n=== Test Results ===')
    print(f'Test 1 (extract_retry_after): {"PASS" if test1 else "FAIL"}')
    print(f'Test 2 (_classify_ollama_cloud_error): {"PASS" if test2 else "FAIL"}')

    if test1 and test2:
        print('\\nAll tests PASSED!')
        return True
    else:
        print('\\nSome tests FAILED!')
        return False

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)