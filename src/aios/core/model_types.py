"""
Provider-agnostic model metadata types for AI-OS.

Defines the canonical model information structure used by the ModelCatalog
and passed through discovery contracts without exposing provider-specific
implementation details or credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelStatus(str, Enum):
    """Availability status of a model."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class ProviderSelectionPolicy(str, Enum):
    """Provider selection policies for provider groups."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"


class ModelCapability(str, Enum):
    """Generic model capabilities recognized by AI-OS."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    AUDIO = "audio"
    MULTI_MODAL = "multi_modal"


@dataclass
class ModelLimits:
    """Optional resource limits for a model."""

    max_tokens: int | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    rate_limit_per_minute: int | None = None
    rate_limit_per_day: int | None = None
    concurrent_requests: int | None = None


@dataclass
class ModelCost:
    """Optional cost metadata for billing/estimation."""

    input_per_1k: float | None = None
    output_per_1k: float | None = None
    currency: str = "USD"
    cached_input_per_1k: float | None = None


@dataclass
class ModelHealth:
    """Health/status information for a model."""

    status: ModelStatus = ModelStatus.UNKNOWN
    last_check_at: str | None = None
    error_message: str | None = None
    uptime_percentage: float | None = None
    avg_latency_ms: float | None = None


@dataclass
class ModelMetadata:
    """
    Provider-agnostic model metadata.

    Represents a model in a way that is independent of any particular
    provider adapter implementation. Does not contain credentials or
    secrets.
    """

    model_id: str
    provider_id: str
    display_name: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    status: ModelStatus = ModelStatus.UNKNOWN
    health: ModelHealth | None = None
    limits: ModelLimits | None = None
    cost: ModelCost | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "capabilities": [c.value for c in self.capabilities],
            "status": self.status.value,
        }

        if self.health:
            result["health"] = {
                "status": self.health.status.value,
                "last_check_at": self.health.last_check_at,
                "error_message": self.health.error_message,
                "uptime_percentage": self.health.uptime_percentage,
                "avg_latency_ms": self.health.avg_latency_ms,
            }

        if self.limits:
            result["limits"] = {
                "max_tokens": self.limits.max_tokens,
                "max_input_tokens": self.limits.max_input_tokens,
                "max_output_tokens": self.limits.max_output_tokens,
                "rate_limit_per_minute": self.limits.rate_limit_per_minute,
                "rate_limit_per_day": self.limits.rate_limit_per_day,
                "concurrent_requests": self.limits.concurrent_requests,
            }

        if self.cost:
            result["cost"] = {
                "input_per_1k": self.cost.input_per_1k,
                "output_per_1k": self.cost.output_per_1k,
                "currency": self.cost.currency,
                "cached_input_per_1k": self.cost.cached_input_per_1k,
            }

        if self.metadata:
            result["metadata"] = self.metadata.copy()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMetadata":
        """Create ModelMetadata from dictionary."""
        capabilities = [
            ModelCapability(c) if isinstance(c, str) else c
            for c in data.get("capabilities", [])
        ]

        health = None
        if "health" in data:
            health_data = data["health"]
            health = ModelHealth(
                status=ModelStatus(health_data.get("status", "unknown")),
                last_check_at=health_data.get("last_check_at"),
                error_message=health_data.get("error_message"),
                uptime_percentage=health_data.get("uptime_percentage"),
                avg_latency_ms=health_data.get("avg_latency_ms"),
            )

        limits = None
        if "limits" in data:
            limits_data = data["limits"]
            limits = ModelLimits(
                max_tokens=limits_data.get("max_tokens"),
                max_input_tokens=limits_data.get("max_input_tokens"),
                max_output_tokens=limits_data.get("max_output_tokens"),
                rate_limit_per_minute=limits_data.get("rate_limit_per_minute"),
                rate_limit_per_day=limits_data.get("rate_limit_per_day"),
                concurrent_requests=limits_data.get("concurrent_requests"),
            )

        cost = None
        if "cost" in data:
            cost_data = data["cost"]
            cost = ModelCost(
                input_per_1k=cost_data.get("input_per_1k"),
                output_per_1k=cost_data.get("output_per_1k"),
                currency=cost_data.get("currency", "USD"),
                cached_input_per_1k=cost_data.get("cached_input_per_1k"),
            )

        return cls(
            model_id=data["model_id"],
            provider_id=data["provider_id"],
            display_name=data["display_name"],
            capabilities=capabilities,
            status=ModelStatus(data.get("status", "unknown")),
            health=health,
            limits=limits,
            cost=cost,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def update(self, **kwargs: Any) -> None:
        """Update fields dynamically."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


__all__ = [
    "ModelMetadata",
    "ModelStatus",
    "ModelCapability",
    "ModelLimits",
    "ModelCost",
    "ModelHealth",
]
