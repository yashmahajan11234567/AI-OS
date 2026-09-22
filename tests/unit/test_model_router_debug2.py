"""
Debug test for ModelRouter routing.
"""

from __future__ import annotations

from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelProvider, ModelCapability


def test_model_routing():
    """Test that model routing works correctly."""
    router = ModelRouter()

    # Register two models
    model1_config = ModelConfig(
        model_id="model-1",
        provider=ModelProvider.NIM,
        name="Model 1",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "nim"},
        priority=10  # Higher priority
    )
    router.register_model(model1_config)

    model2_config = ModelConfig(
        model_id="model-2",
        provider=ModelProvider.KILO,
        name="Model 2",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "kilo"},
        priority=20  # Lower priority (higher number = lower priority)
    )
    router.register_model(model2_config)

    # Test routing for text_generation capability
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )

    selected_model = router.route(request)
    print(f"Selected model: {selected_model.model_id} (provider: {selected_model.provider})")

    # Should select model-1 due to higher priority (lower priority number)
    assert selected_model.model_id == "model-1"
    assert selected_model.provider == ModelProvider.NIM

    print("Model routing test passed!")


if __name__ == "__main__":
    test_model_routing()