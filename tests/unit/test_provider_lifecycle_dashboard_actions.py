"""
Unit tests for NVIDIA NIM provider lifecycle and dashboard actions.
Tests the complete flow: Dashboard → SecurityManager → ProviderRegistry → NimProvider
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from aios.core.provider_registry import ProviderRegistry
from aios.services.dashboard_service import DashboardService, DashboardActionResult
from aios.core.security_manager import SecurityManager, SecurityDecision
from aios.adapters.nim import NimProvider
from aios.core.provider import Provider
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import SemanticVersion


@pytest.fixture
def mock_kernel():
    """Create a mock kernel with required components."""
    kernel = Mock()
    kernel.provider_registry = ProviderRegistry()
    kernel.configuration = Mock()
    kernel.security_manager = Mock()
    kernel.event_bus = Mock()
    return kernel


@pytest.fixture
def dashboard_service(mock_kernel):
    """Create a DashboardService instance."""
    return DashboardService(
        kernel=mock_kernel,
        event_bus=mock_kernel.event_bus,
        security_manager=mock_kernel.security_manager
    )


@pytest.fixture
def nim_provider():
    """Create a NimProvider instance."""
    return NimProvider()


class TestProviderRegistryLifecycle:
    """Test ProviderRegistry lifecycle methods."""

    def test_enable_provider_success(self):
        """Test enabling a registered provider."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        # Providers are enabled by default, so first disable it
        registry.disable_provider("nim")

        # Now enable it
        result = registry.enable_provider("nim")
        assert result is True

        # Verify provider is enabled
        health = registry._provider_health["nim"]
        assert health.enabled is True

    def test_enable_provider_already_enabled(self):
        """Test enabling an already-enabled provider."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        # Enable first time
        registry.enable_provider("nim")
        # Try to enable again
        result = registry.enable_provider("nim")
        assert result is False  # Already enabled

    def test_enable_unknown_provider(self):
        """Test enabling an unknown provider."""
        registry = ProviderRegistry()
        result = registry.enable_provider("unknown")
        assert result is False

    def test_disable_provider_success(self):
        """Test disabling a registered provider."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        result = registry.disable_provider("nim")
        assert result is True

        # Verify provider is disabled
        health = registry._provider_health["nim"]
        assert health.enabled is False

    def test_disable_provider_already_disabled(self):
        """Test disabling an already-disabled provider."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        # Disable first time
        registry.disable_provider("nim")
        # Try to disable again
        result = registry.disable_provider("nim")
        assert result is False  # Already disabled

    def test_disable_unknown_provider(self):
        """Test disabling an unknown provider."""
        registry = ProviderRegistry()
        result = registry.disable_provider("unknown")
        assert result is False

    def test_reconfigure_provider_success(self):
        """Test reconfiguring a provider."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        config = {"base_url": "https://custom.nim.url", "default_model": "custom-model"}
        result = registry.reconfigure_provider("nim", config)
        assert result is True

        # Verify configuration was updated
        assert provider._config.base_url == "https://custom.nim.url"
        assert provider._config.default_model == "custom-model"

    def test_reconfigure_unknown_provider(self):
        """Test reconfiguring an unknown provider."""
        registry = ProviderRegistry()
        result = registry.reconfigure_provider("unknown", {"key": "value"})
        assert result is False

    def test_reconfigure_provider_invalid_config(self):
        """Test reconfiguring with invalid config."""
        registry = ProviderRegistry()
        provider = NimProvider()
        registry.register_provider("nim", provider)

        # Test None config
        result = registry.reconfigure_provider("nim", None)
        assert result is False

        # Test non-dict config
        result = registry.reconfigure_provider("nim", "invalid")
        assert result is False

        # Test empty dict - actually returns False due to 'if not config' check
        result = registry.reconfigure_provider("nim", {})
        assert result is False  # Empty config is considered invalid


class TestDashboardServiceProviderActions:
    """Test DashboardService provider lifecycle actions."""

    @pytest.mark.asyncio
    async def test_provider_configure_success(self, dashboard_service, mock_kernel):
        """Test successful provider configuration through dashboard."""
        # Setup: Register NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Configure provider
        result = await dashboard_service.request_action(
            action="provider.configure",
            params={
                "provider_id": "nim",
                "config": {
                    "base_url": "https://test.nim.url",
                    "default_model": "test-model",
                    "timeout_seconds": 60
                }
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["provider_id"] == "nim"
        assert "base_url" in result.data["updated_config"]
        assert "default_model" in result.data["updated_config"]
        assert "timeout_seconds" in result.data["updated_config"]

        # Verify: Provider was actually reconfigured
        assert provider._config.base_url == "https://test.nim.url"
        assert provider._config.default_model == "test-model"
        assert provider._config.timeout_seconds == 60

    @pytest.mark.asyncio
    async def test_provider_configure_credentials_rejected(self, dashboard_service, mock_kernel):
        """Test that provider.configure rejects credential parameters."""
        # Setup: Register NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Try to configure with credentials (should fail)
        result = await dashboard_service.request_action(
            action="provider.configure",
            params={
                "provider_id": "nim",
                "config": {
                    "base_url": "https://test.nim.url",
                    "api_key": "sk-test-key"  # This should be rejected
                }
            }
        )

        # Verify: Action failed due to credential rejection
        assert result.status == "error"
        assert "Credentials must be configured via secret.rotate" in result.detail

    @pytest.mark.asyncio
    async def test_provider_enable_success(self, dashboard_service, mock_kernel):
        """Test successful provider enable through dashboard."""
        # Setup: Register NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Enable provider
        result = await dashboard_service.request_action(
            action="provider.enable",
            params={
                "provider_id": "nim"
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["provider_id"] == "nim"

        # Verify: Provider was actually enabled
        assert mock_kernel.provider_registry._provider_health["nim"].enabled is True

    @pytest.mark.asyncio
    async def test_provider_enable_already_enabled(self, dashboard_service, mock_kernel):
        """Test enabling an already-enabled provider."""
        # Setup: Register and enable NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)
        mock_kernel.provider_registry.enable_provider("nim")  # Pre-enable

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Enable provider (should report already enabled)
        result = await dashboard_service.request_action(
            action="provider.enable",
            params={
                "provider_id": "nim"
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["provider_id"] == "nim"
        assert result.data.get("already_enabled") is True

    @pytest.mark.asyncio
    async def test_provider_disable_success(self, dashboard_service, mock_kernel):
        """Test successful provider disable through dashboard."""
        # Setup: Register NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Disable provider
        result = await dashboard_service.request_action(
            action="provider.disable",
            params={
                "provider_id": "nim"
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["provider_id"] == "nim"

        # Verify: Provider was actually disabled
        assert mock_kernel.provider_registry._provider_health["nim"].enabled is False

    @pytest.mark.asyncio
    async def test_provider_disable_already_disabled(self, dashboard_service, mock_kernel):
        """Test disabling an already-disabled provider."""
        # Setup: Register and disable NIM provider
        provider = NimProvider()
        mock_kernel.provider_registry.register_provider("nim", provider)
        mock_kernel.provider_registry.disable_provider("nim")  # Pre-disable

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Disable provider (should report already disabled)
        result = await dashboard_service.request_action(
            action="provider.disable",
            params={
                "provider_id": "nim"
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["provider_id"] == "nim"
        assert result.data.get("already_disabled") is True

    @pytest.mark.asyncio
    async def test_secret_rotate_success(self, dashboard_service, mock_kernel):
        """Test successful secret rotation through dashboard."""
        # Setup: Mock ConfigurationManager to simulate successful rotation
        mock_config_manager = Mock()
        mock_config_manager.rotate_secret.return_value = True
        mock_kernel.configuration = mock_config_manager

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Rotate secret
        result = await dashboard_service.request_action(
            action="secret.rotate",
            params={
                "path": "config:llm.providers.nim.apiKey",
                "new_value": "sk-new-test-key"
            }
        )

        # Verify: Action completed successfully
        assert result.status == "completed"
        assert result.authorized is True
        assert result.data["success"] is True
        assert result.data["path"] == "config:llm.providers.nim.apiKey"
        assert result.data.get("redacted") is True

        # Verify: ConfigurationManager.rotate_secret was called
        mock_config_manager.rotate_secret.assert_called_once_with(
            "config:llm.providers.nim.apiKey",
            "sk-new-test-key"
        )

    @pytest.mark.asyncio
    async def test_secret_rotate_wrong_path_rejected(self, dashboard_service, mock_kernel):
        """Test that secret.rotate rejects non-NIM paths."""
        # Setup: Mock ConfigurationManager
        mock_config_manager = Mock()
        mock_config_manager.rotate_secret.return_value = True
        mock_kernel.configuration = mock_config_manager

        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Try to rotate non-NIM secret (should fail)
        result = await dashboard_service.request_action(
            action="secret.rotate",
            params={
                "path": "config:llm.providers.other.apiKey",  # Wrong path
                "new_value": "sk-test-key"
            }
        )

        # Verify: Action failed due to invalid path
        assert result.status == "error"
        assert "Only 'config:llm.providers.nim.apiKey' path allowed" in result.detail

    @pytest.mark.asyncio
    async def test_unsupported_provider_rejected(self, dashboard_service, mock_kernel):
        """Test that unsupported providers are rejected."""
        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Try to configure unsupported provider (should fail)
        result = await dashboard_service.request_action(
            action="provider.configure",
            params={
                "provider_id": "unsupported",
                "config": {"base_url": "http://test.url"}
            }
        )

        # Verify: Action failed due to unsupported provider
        assert result.status == "error"
        assert "Provider 'unsupported' not found" in result.detail

    @pytest.mark.asyncio
    async def test_unauthorized_action_denied(self, dashboard_service, mock_kernel):
        """Test that unauthorized actions are denied."""
        # Mock the authorization to return DENY
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.DENY

        # Execute: Try any provider action
        result = await dashboard_service.request_action(
            action="provider.enable",
            params={"provider_id": "nim"}
        )

        # Verify: Action was rejected
        assert result.status == "rejected"
        assert result.authorized is False
        assert "SecurityManager denied the action" in result.detail

    @pytest.mark.asyncio
    async def test_unknown_provider_rejected(self, dashboard_service, mock_kernel):
        """Test that unknown providers are handled correctly."""
        # Mock the authorization to return ALLOW
        mock_kernel.security_manager.authorize.return_value = SecurityDecision.ALLOW

        # Execute: Try to configure unknown provider (should fail gracefully)
        result = await dashboard_service.request_action(
            action="provider.configure",
            params={
                "provider_id": "unknown",
                "config": {"base_url": "http://test.url"}
            }
        )

        # Verify: Action failed due to provider not supported
        assert result.status == "error"
        assert "Provider 'unknown' not found" in result.detail


class TestNimProviderABC:
    """Test that NimProvider properly subclasses Provider."""

    def test_nim_provider_is_provider(self, nim_provider):
        """Test that NimProvider is instance of Provider."""
        assert isinstance(nim_provider, Provider)

    def test_nim_provider_has_generate_method(self, nim_provider):
        """Test that NimProvider has the required generate method."""
        assert hasattr(nim_provider, "generate")
        assert callable(getattr(nim_provider, "generate"))

    @pytest.mark.asyncio
    async def test_nim_provider_generate_signature(self, nim_provider):
        """Test that NimProvider.generate has correct signature."""
        from aios.core.model_router import ModelRequest

        # Create a minimal model request
        request = ModelRequest(
            prompt="test prompt",
            preferred_model=None,
            system_prompt=None,
            max_tokens=None,
            temperature=None
        )

        # Mock the session to avoid actual HTTP calls
        with patch.object(nim_provider, '_ensure_session'):
            # Create a proper async context manager mock
            response_mock = Mock()
            response_mock.status = 200
            response_mock.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "test response"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3}
            })

            # Create a context manager mock that properly yields the response
            class AsyncContextManagerMock:
                async def __aenter__(self):
                    return response_mock
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            # Mock the post method to return our context manager
            nim_provider._session = Mock()
            nim_provider._session.post = Mock(return_value=AsyncContextManagerMock())

            # Execute generate
            result = await nim_provider.generate(request)

            # Verify: Returns ModelResponse
            from aios.core.model_router import ModelResponse
            assert isinstance(result, ModelResponse)
            assert result.content == "test response"