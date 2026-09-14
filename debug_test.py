#!/usr/bin/env python3

import asyncio
from aios.core.model_router import ModelRouter, ModelRequest, ModelConfig, ModelProvider, ModelCapability
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig, register_freellmapi_provider


class DebugProvider:
    def __init__(self):
        self.called = False

    async def generate(self, request):
        self.called = True
        print(f"Provider called with request: {request.prompt}")
        # Return a simple mock response
        from aios.core.model_router import ModelResponse
        return ModelResponse(
            content="debug-response",
            model_id=request.preferred_model or "debug-model",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 1, "output": 1},
            cost=0.0,
            latency_ms=1
        )


async def test_dispatch():
    print("Creating router...")
    router = ModelRouter()

    print("Creating FreeLLMAPI model config...")
    freellmapi_model = ModelConfig(
        model_id="freellmapi-debug",
        provider=ModelProvider.LOCAL,
        name="FreeLLMAPI Debug",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
    )

    print("Registering model...")
    router.register_model(freellmapi_model)

    print(f"Models registered: {list(router._models.keys())}")
    print(f"FreeLLMAPI model config: {router._models['freellmapi-debug'].config}")

    print("Creating provider...")
    provider = DebugProvider()

    print("Registering provider...")
    registered = register_freellmapi_provider(router, FreeLLMAPIConfig())

    print(f"Provider registered: {router._freellmapi_provider is registered}")
    print(f"Has _freellmapi_provider attr: {hasattr(router, '_freellmapi_provider')}")
    if hasattr(router, '_freellmapi_provider'):
        print(f"_freellmapi_provider value: {router._freellmapi_provider}")

    print("Testing route...")
    request = ModelRequest(prompt="test", preferred_model="freellmapi-debug")
    model = router.route(request)
    print(f"Routed to model: {model.model_id}")
    print(f"Model config: {model.config}")
    print(f"Model config has freellmapi: {model.config.get('freellmapi')}")

    print("Testing generate...")
    response = await router.generate(request)
    print(f"Response: {response}")
    print(f"Provider called: {provider.called}")


if __name__ == "__main__":
    asyncio.run(test_dispatch())