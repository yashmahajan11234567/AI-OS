"""
Model Router for AI-OS Hermes Kernel.

Routes LLM requests to appropriate models (Claude, local, cloud) with fallback,
caching, and cost optimization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Model provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"
    OLLAMA = "ollama"
    VLLM = "vllm"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


class ModelCapability(str, Enum):
    """Model capabilities."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"


@dataclass
class ModelConfig:
    """Model configuration."""

    model_id: str
    provider: ModelProvider
    name: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    priority: int = 100
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelRequest:
    """Model request with routing hints."""

    prompt: str
    system_prompt: str | None = None
    required_capabilities: list[ModelCapability] = field(default_factory=list)
    preferred_model: str | None = None
    preferred_provider: ModelProvider | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ModelResponse:
    """Model response."""

    content: str
    model_id: str
    provider: ModelProvider
    tokens_used: dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    """
    Routes model requests to the best available model.

    Features:
    - Capability-based routing
    - Cost optimization
    - Fallback chains
    - Load balancing
    - Usage tracking
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the Model Router.

        Args:
            config: Configuration dictionary
        """
        self._models: dict[str, ModelConfig] = {}
        self._fallback_chains: dict[str, list[str]] = {}
        self._usage_stats: dict[str, dict[str, Any]] = {}
        self._config = config or {}

        # Load default models
        self._load_default_models()

    def _load_default_models(self) -> None:
        """Load default model configurations."""
        defaults = [
            ModelConfig(
                model_id="claude-opus-4",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Opus 4",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.ANALYSIS,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=8192,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                priority=10,
            ),
            ModelConfig(
                model_id="claude-sonnet-4",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Sonnet 4",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=8192,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                priority=20,
            ),
            ModelConfig(
                model_id="claude-haiku-3.5",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Haiku 3.5",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                priority=30,
            ),
            ModelConfig(
                model_id="gpt-4o",
                provider=ModelProvider.OPENAI,
                name="GPT-4o",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                priority=15,
            ),
            ModelConfig(
                model_id="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                name="GPT-4o Mini",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                priority=25,
            ),
        ]

        for model in defaults:
            self.register_model(model)

        # Default fallback chain
        self._fallback_chains["default"] = [
            "claude-sonnet-4",
            "claude-haiku-3.5",
            "gpt-4o-mini",
            "gpt-4o",
        ]

    def register_model(self, model: ModelConfig) -> None:
        """Register a model."""
        self._models[model.model_id] = model
        self._usage_stats[model.model_id] = {
            "requests": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "total_cost": 0.0,
            "errors": 0,
            "avg_latency_ms": 0,
        }
        logger.info(f"Registered model: {model.model_id} ({model.provider.value})")

    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model."""
        if model_id in self._models:
            del self._models[model_id]
            del self._usage_stats[model_id]
            return True
        return False

    def set_fallback_chain(self, name: str, model_ids: list[str]) -> None:
        """Set a fallback chain."""
        # Validate all models exist
        for mid in model_ids:
            if mid not in self._models:
                raise ValueError(f"Model {mid} not registered")
        self._fallback_chains[name] = model_ids

    def route(self, request: ModelRequest) -> ModelConfig:
        """
        Select the best model for a request.

        Args:
            request: Model request with requirements

        Returns:
            Selected model configuration
        """
        # If specific model requested and available
        if request.preferred_model and request.preferred_model in self._models:
            model = self._models[request.preferred_model]
            if model.enabled:
                return model

        # If provider preference
        if request.preferred_provider:
            candidates = [
                m for m in self._models.values()
                if m.provider == request.preferred_provider and m.enabled
            ]
            if candidates:
                return self._select_best(candidates, request)

        # Capability-based routing
        candidates = self._filter_by_capabilities(request.required_capabilities)
        if candidates:
            return self._select_best(candidates, request)

        # Fallback to default chain
        for mid in self._fallback_chains.get("default", []):
            if mid in self._models and self._models[mid].enabled:
                return self._models[mid]

        # Last resort: any enabled model
        enabled = [m for m in self._models.values() if m.enabled]
        if enabled:
            return enabled[0]

        raise ValueError("No available models")

    def _filter_by_capabilities(
        self, capabilities: list[ModelCapability]
    ) -> list[ModelConfig]:
        """Filter models by required capabilities."""
        if not capabilities:
            return list(self._models.values())

        return [
            m for m in self._models.values()
            if m.enabled and all(c in m.capabilities for c in capabilities)
        ]

    def _select_best(
        self, candidates: list[ModelConfig], request: ModelRequest
    ) -> ModelConfig:
        """Select best model from candidates."""
        # Sort by priority, then cost, then capability match
        def score(model: ModelConfig) -> tuple:
            cost = model.cost_per_1k_input + model.cost_per_1k_output
            cap_match = sum(1 for c in request.required_capabilities if c in model.capabilities)
            return (model.priority, cost, -cap_match)

        return min(candidates, key=score)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate response using routed model.

        Args:
            request: Model request

        Returns:
            Model response
        """
        model = self.route(request)
        return await self._call_model(model, request)

    async def _call_model(
        self, model: ModelConfig, request: ModelRequest
    ) -> ModelResponse:
        """Call the selected model (placeholder for actual implementation)."""
        import time

        start = time.perf_counter()

        # This is a placeholder - actual implementation would call APIs
        # For now, return a mock response
        await asyncio.sleep(0.1)  # Simulate latency

        response = ModelResponse(
            content=f"[Mock response from {model.model_id}] {request.prompt[:100]}...",
            model_id=model.model_id,
            provider=model.provider,
            tokens_used={"input": 100, "output": 50},
            cost=0.001,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

        # Update stats
        stats = self._usage_stats[model.model_id]
        stats["requests"] += 1
        stats["tokens_in"] += response.tokens_used.get("input", 0)
        stats["tokens_out"] += response.tokens_used.get("output", 0)
        stats["total_cost"] += response.cost

        return response

    def get_usage_stats(self, model_id: str | None = None) -> dict[str, Any]:
        """Get usage statistics."""
        if model_id:
            return self._usage_stats.get(model_id, {})
        return self._usage_stats

    def get_available_models(
        self, capability: ModelCapability | None = None
    ) -> list[ModelConfig]:
        """Get list of available models."""
        models = [m for m in self._models.values() if m.enabled]
        if capability:
            models = [m for m in models if capability in m.capabilities]
        return sorted(models, key=lambda m: m.priority)

    def estimate_cost(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for a request."""
        model = self._models.get(model_id)
        if not model:
            return 0.0
        return (
            (input_tokens / 1000) * model.cost_per_1k_input
            + (output_tokens / 1000) * model.cost_per_1k_output
        )


import asyncio

# Global model router instance
_global_model_router: ModelRouter | None = None


def get_model_router(config: dict[str, Any] | None = None) -> ModelRouter:
    """Get or create the global model router."""
    global _global_model_router
    if _global_model_router is None:
        _global_model_router = ModelRouter(config)
    return _global_model_router


def set_model_router(router: ModelRouter) -> None:
    """Set the global model router."""
    global _global_model_router
    _global_model_router = router


__all__ = [
    "ModelRouter",
    "ModelConfig",
    "ModelRequest",
    "ModelResponse",
    "ModelProvider",
    "ModelCapability",
    "get_model_router",
    "set_model_router",
]