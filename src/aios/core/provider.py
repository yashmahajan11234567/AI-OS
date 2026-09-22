"""
Abstract base class for AI-OS ModelRouter providers.

Defines the minimal contract that providers must implement to be used
with the ModelRouter through the ProviderRegistry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aios.core.model_router import ModelRequest, ModelResponse


class Provider(ABC):
    """
    Abstract base class for ModelRouter providers.

    Providers implement the generate method to produce responses from
    model requests. This is the minimal contract required for the
    ModelRouter to dispatch to any registered provider.

    Providers may also implement configuration and credential reloading
    capabilities for runtime updates without kernel restart.

    Example:
        class MyProvider(Provider):
            async def generate(self, request: "ModelRequest") -> "ModelResponse":
                # Implementation-specific logic
                return ModelResponse(
                    content="Generated response",
                    model_id=request.preferred_model or "default",
                    provider=ModelProvider.LOCAL,
                )

            def configure(self, config: dict[str, Any]) -> None:
                # Update non-secret configuration
                self._config.update(config)

            async def reload_credentials(self) -> None:
                # Reload credentials from secure store
                await self._refresh_session()
    """

    @abstractmethod
    async def generate(self, request: "ModelRequest") -> "ModelResponse":
        """
        Generate a response for the given model request.

        Args:
            request: Model request containing prompt and parameters

        Returns:
            Model response with generated content and metadata

        Note:
            Providers should handle their own error conditions and return
            appropriate ModelResponse instances even in failure cases.
        """
        pass

    def configure(self, config: dict[str, Any]) -> None:
        """
        Update non-secret provider configuration safely.

        This method is called when non-secret configuration values change
        (e.g., base_url, timeout, default_model). Providers should update
        their internal configuration without exposing secrets.

        Args:
            config: Dictionary containing configuration keys to update
                   (e.g., {"base_url": "https://new-url", "timeout": 30})

        Note:
            The default implementation does nothing. Providers that support
            runtime configuration updates should override this method.
        """
        pass

    async def reload_credentials(self) -> None:
        """
        Apply newly rotated credentials to the live provider instance.

        This method is called when credentials are rotated via the
        ConfigurationManager.Providers should update their credentials
        and ensure existing sessions cannot continue using old credentials.

        Note:
            The default implementation does nothing. Providers that handle
            credentials should override this method to:
            1. Update their internal credential storage
            2. Invalidate/recreate any existing sessions
            3. Ensure subsequent generate() calls use new credentials
        """
        pass