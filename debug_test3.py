#!/usr/bin/env python3

import asyncio
import os
from unittest.mock import patch
from aios.core.model_router import ModelRouter, ModelRequest, ModelConfig, ModelProvider, ModelCapability
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig, register_freellmapi_provider

async def test_scenario():
    print("=== Testing scenario with NO env vars ===")

    router = ModelRouter()

    # Create and register FreeLLMAPI model
    freellmapi_model = ModelConfig(
        model_id="freellmapi-test",
        provider=ModelProvider.LOCAL,
        name="FreeLLMAPI Test",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
    )
    router.register_model(freellmapi_model)
    print(f"Registered models: {list(router._models.keys())}")

    # Test with no env vars
    env_vars = {}
    print(f"Environment vars: {env_vars}")

    with patch.dict(os.environ, env_vars, clear=True):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env
        config = get_freellmapi_config_from_env()
        print(f"Config from env: base_url='{config.base_url}', api_key='{config.api_key}'")

        # Register provider
        provider = register_freellmapi_provider(router, config)
        print(f"Provider registered: {router._freellmapi_provider is provider}")
        print(f"Has _freellmapi_provider: {hasattr(router, '_freellmapi_provider')}")

        # Test the dispatch
        request = ModelRequest(prompt="test prompt 1", preferred_model="freellmapi-test")
        print(f"Making request: {request.prompt}")
        response = await router.generate(request)
        print(f"Response: {response}")
        print(f"Response content: '{response.content}'")
        print(f"Response content repr: {repr(response.content)}")
        print(f"Is mock response? {'[Mock response from' in response.content}")
        print(f"Content length: {len(response.content)}")

        # Cleanup
        if hasattr(router, '_freellmapi_provider'):
            delattr(router, '_freellmapi_provider')
        if "freellmapi-test" in router._models:
            del router._models["freellmapi-test"]

if __name__ == "__main__":
    asyncio.run(test_scenario())