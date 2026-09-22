#!/usr/bin/env python3
"""
Simple test to verify other providers correctly extract Retry-After values.
"""

import asyncio
from aios.core.provider_failures import extract_retry_after, classify_failure, FailureCategory

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

async def test_classify_failure_with_retry_after():
    """Test classify_failure with retry_after parameter"""
    print('\\n=== Testing classify_failure with retry_after ===')

    # Test 429 error with retry_after
    failure = classify_failure(
        category=FailureCategory.RATE_LIMIT,
        provider_id="test_provider",
        http_status=429,
        provider_error_code="test_error",
        retry_after=30,
        safe_message="Rate limit exceeded"
    )

    print(f'Failure category: {failure.category}')
    print(f'Failure retry_after: {failure.retry_after}')
    print(f'Failure http_status: {failure.http_status}')

    assert failure.category == FailureCategory.RATE_LIMIT, f"Expected RATE_LIMIT, got {failure.category}"
    assert failure.retry_after == 30, f"Expected 30 seconds, got {failure.retry_after}"
    assert failure.http_status == 429, f"Expected 429 status, got {failure.http_status}"

    print('+ classify_failure with retry_after test passed')
    return True

async def run_tests():
    print('Running simplified other providers Retry-After tests...')

    test1 = await test_extract_retry_after_function()
    test2 = await test_classify_failure_with_retry_after()

    print(f'\\n=== Test Results ===')
    print(f'Test 1 (extract_retry_after): {"PASS" if test1 else "FAIL"}')
    print(f'Test 2 (classify_failure with retry_after): {"PASS" if test2 else "FAIL"}')

    if test1 and test2:
        print('\\nAll tests PASSED!')
        return True
    else:
        print('\\nSome tests FAILED!')
        return False

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)