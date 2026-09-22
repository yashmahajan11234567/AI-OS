"""
Debug test for ModelRouter model registration.
"""

from __future__ import annotations

from aios.core.model_router import ModelRouter, ModelConfig, ModelProvider, ModelCapability


def test_model_registration():
    """Test that models are registered correctly."""
    router = ModelRouter()

    # Register a model
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.NIM,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "nim"}
    )
    router.register_model(model_config)

    # Check that it's registered
    assert "test-model" in router._models
    registered_model = router._models["test-model"]
    assert registered_model.model_id == "test-model"
    assert registered_model.provider == ModelProvider.NIM
    assert registered_model.enabled == True
    assert ModelCapability.TEXT_GENERATION in registered_model.capabilities

    # Check usage stats were initialized
    stats = router.get_usage_stats("test-model")
    assert stats["requests"] == 0
    assert stats["tokens_in"] == 0
    assert stats["tokens_out"] == 0
    assert stats["total_cost"] == 0.0

    print("Model registration test passed!")


if __name__ == "__main__":
    test_model_registration()