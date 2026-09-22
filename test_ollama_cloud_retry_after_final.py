#!/usr/bin/env python3
"""
Test to verify Ollama Cloud adapter correctly extracts and propagates Retry-After values.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from aios.adapters.ollama_cloud import OllamaCloudProvider, OllamaCloudConfig
from aios.core.model_router import ModelRequest

# Let's create a proper mock that acts as an async context manager
class MockAsyncContextManager:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

async def test_retry_after_from_headers():
    """Test that Retry-After from headers is correctly processed"""
    print('=== Testing Retry-After from Headers ===')

    config = OllamaCloudConfig(api_key='test-key')
    provider = OllamaCloudProvider(config)

    # Patch _ensure_session to do nothing (since we'll set _session directly)
    with patch.object(provider, '_ensure_session', return_value=None):
        # Set up our mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        provider._session = mock_session

        # Create our proper mock response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {'Retry-After': '30'}  # 30 seconds
        mock_response.text = AsyncMock(return_value='{"error": "rate limit exceeded"}')

        # Create our proper mock context manager that returns the mock_response
        mock_context_manager = MockAsyncContextManager(mock_response)

        # Make post return our context manager (not coroutine)
        async def mock_post(*args, **kwargs):
            return mock_context_manager
        mock_session.post = mock_post

        request = ModelRequest(prompt='test', preferred_model='llama2')

        try:
            result = await provider.generate(request)
            print(f'Result content: {result.content}')
            print(f'Result metadata keys: {list(result.metadata.keys())}')

            # Check if we got the retry_after in the metadata
            if 'failure_retry_after' in result.metadata:
                retry_after = result.metadata['failure_retry_after']
                print(f'SUCCESS: failure_retry_after in metadata: {retry_after} seconds')
                if retry_after == 30:
                    print('CORRECT: Value matches expected 30 seconds from header')
                    return True
                else:
                    print(f'ERROR: Expected 30, got {retry_after}')
                    return False
            else:
                print('ERROR: No failure_retry_after in metadata')
                return False

        except Exception as e:
            print(f'EXCEPTION: {e}')
            import traceback
            traceback.print_exc()
            return False

async def test_retry_after_from_body():
    """Test that Retry-After from body is correctly processed when no header"""
    print('\\n=== Testing Retry-After from Body (no header) ===')

    config = OllamaCloudConfig(api_key='test-key')
    provider = OllamaCloudProvider(config)

    # Patch _ensure_session to do nothing (since we'll set _session directly)
    with patch.object(provider, '_ensure_session', return_value=None):
        # Set up our mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        provider._session = mock_session

        # Create our proper mock response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {}  # No Retry-After header
        mock_response.text = AsyncMock(return_value='{"error": "rate limit exceeded", "retry_after": 45}')

        # Create our proper mock context manager that returns the mock_response
        mock_context_manager = MockAsyncContextManager(mock_response)

        # Make post return our context manager (not coroutine)
        async def mock_post(*args, **kwargs):
            return mock_context_manager
        mock_session.post = mock_post

        request = ModelRequest(prompt='test', preferred_model='llama2')

        try:
            result = await provider.generate(request)
            print(f'Result content: {result.content}')
            print(f'Result metadata keys: {list(result.metadata.keys())}')

            # Check if we got the retry_after in the metadata
            if 'failure_retry_after' in result.metadata:
                retry_after = result.metadata['failure_retry_after']
                print(f'SUCCESS: failure_retry_after in metadata: {retry_after} seconds')
                if retry_after == 45:
                    print('CORRECT: Value matches expected 45 seconds from body')
                    return True
                else:
                    print(f'ERROR: Expected 45, got {retry_after}')
                    return False
            else:
                print('ERROR: No failure_retry_after in metadata')
                return False

        except Exception as e:
            print(f'EXCEPTION: {e}')
            import traceback
            traceback.print_exc()
            return False

async def test_no_retry_after():
    """Test that when there's no Retry-After, we handle it gracefully"""
    print('\\n=== Testing No Retry-After ===')

    config = OllamaCloudConfig(api_key='test-key')
    provider = OllamaCloudProvider(config)

    # Patch _ensure_session to do nothing (since we'll set _session directly)
    with patch.object(provider, '_ensure_session', return_value=None):
        # Set up our mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        provider._session = mock_session

        # Create our proper mock response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {}  # No Retry-After header
        mock_response.text = AsyncMock(return_value='{"error": "rate limit exceeded"}')

        # Create our proper mock context manager that returns the mock_response
        mock_context_manager = MockAsyncContextManager(mock_response)

        # Make post return our context manager (not coroutine)
        async def mock_post(*args, **kwargs):
            return mock_context_manager
        mock_session.post = mock_post

        request = ModelRequest(prompt='test', preferred_model='llama2')

        try:
            result = await provider.generate(request)
            print(f'Result content: {result.content}')
            print(f'Result metadata keys: {list(result.metadata.keys())}')

            # Check if we got the retry_after in the metadata (should be None)
            if 'failure_retry_after' in result.metadata:
                retry_after = result.metadata['failure_retry_after']
                print(f'Result: failure_retry_after in metadata: {retry_after}')
                if retry_after is None:
                    print('CORRECT: failure_retry_after is None when not present')
                    return True
                else:
                    print(f'ERROR: Expected None, got {retry_after}')
                    return False
            else:
                print('INFO: No failure_retry_after key in metadata (also acceptable)')
                return True

        except Exception as e:
            print(f'EXCEPTION: {e}')
            import traceback
            traceback.print_exc()
            return False

async def run_all_tests():
    print('Running Ollama Cloud Retry-After integration tests...')

    test1 = await test_retry_after_from_headers()
    test2 = await test_retry_after_from_body()
    test3 = await test_no_retry_after()

    print(f'\\n=== Test Results ===')
    print(f'Test 1 (Headers): {"PASS" if test1 else "FAIL"}')
    print(f'Test 2 (Body): {"PASS" if test2 else "FAIL"}')
    print(f'Test 3 (No Header): {"PASS" if test3 else "FAIL"}')

    if test1 and test2 and test3:
        print('\\nAll tests PASSED!')
        return True
    else:
        print('\\nSome tests FAILED!')
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)