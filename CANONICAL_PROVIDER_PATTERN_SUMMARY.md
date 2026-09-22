# Canonical Provider Pattern in AI-OS
## Established Through Analysis of NIM and FreeLLMAPI Implementations
**Terminal 1 - AI-OS Architecture Analysis**
**Date: 2026-09-17**

## Overview

This document summarizes the canonical provider pattern that new providers must follow to integrate with the AI-OS architecture without modifying existing closed work. The pattern was established by analyzing the existing NVIDIA NIM and FreeLLMAPI provider implementations.

## Core Components

### 1. Provider Abstract Base Class (`src/aios/core/provider.py`)
All providers must inherit from `Provider` and implement:

```python
class Provider(ABC):
    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate response from the provider."""
        pass
    
    def configure(self, config: dict[str, Any]) -> None:
        """Update non-secret provider configuration."""
        # Default implementation updates _config attributes
        pass
        
    async def reload_credentials(self) -> None:
        """Apply newly rotated credentials to live provider instance."""
        # Default implementation closes session to force recreation
        pass
```

### 2. Provider Registration Pattern
Providers are registered with the existing infrastructure:

#### Kernel Initialization (`src/aios/core/kernel.py:818-822`)
```python
# G1 (M8-T4) — register FreeLLMAPI provider with ModelRouter (dev/test)
await self._init_freellmapi()

# Register NVIDIA NIM provider with ModelRouter (production ready)  
await self._init_nim()
```

#### Provider Registration Functions
Each provider implements registration functions that:
1. Register with `ProviderRegistry`
2. Register model with existing `ModelRouter` 
3. Maintain backward compatibility

Example from FreeLLMAPI (`src/aios/adapters/freellmapi.py:160-216`):
```python
def register_freellmapi_provider(
    model_router,
    config: FreeLLMAPIConfig | None = None,
) -> FreeLLMAPIProvider:
    # 1. Create provider instance
    provider = FreeLLMAPIProvider(config)
    
    # 2. Register model in existing ModelRouter
    model_config = ModelConfig(
        model_id="freellmapi-default",
        provider=ModelProvider.LOCAL,  # or custom provider enum
        name="FreeLLMAPI Default",
        capabilities=[...],
        config={
            "provider": "freellmapi",  # References provider by ID in registry
            "freellmapi": True,        # Backward compatibility flag
        },
    )
    model_router.register_model(model_config)
    
    # 3. Register provider with ProviderRegistry
    provider_registry = getattr(model_router, "_provider_registry", None)
    if provider_registry is None:
        provider_registry = get_default_provider_registry()
    provider_registry.register_provider("freellmapi", provider)
    
    # 4. Backward compatibility
    if not hasattr(model_router, "_freellmapi_provider"):
        model_router._freellmapi_provider = provider
        
    return provider
```

### 3. ModelRouter Dispatch Mechanism (`src/aios/core/model_router.py:379-398`)
The ModelRouter dispatches to providers using this pattern:

```python
async def _call_model(self, model: ModelConfig, request: ModelRequest) -> ModelResponse:
    # Extract provider ID from model config
    provider_id = model.config.get("provider")
    provider = None

    if provider_id and self._provider_registry:
        provider = self._provider_registry.get_provider(provider_id)
        # Check if provider is enabled/healthy
        if provider is not None:
            provider_health = self._provider_registry._provider_health.get(provider_id)
            if provider_health is not None and not provider_health.enabled:
                provider = None

    # Backward compatibility check (for FreeLLMAPI)
    if provider is None:
        freellmapi_provider = getattr(self, "_freellmapi_provider", None)
        if freellmapi_provider is not None and model.config.get("freellmapi"):
            provider = freellmapi_provider

    if provider is not None:
        response = await provider.generate(request)
    else:
        # Fallback to mock response
        response = await self._generate_mock_response(model, request)
    
    return response
```

### 4. Configuration Pattern
Providers use isolated configuration loaded from environment variables:

Example from NIM (`src/aios/adapters/nim.py:213-220`):
```python
def get_nim_config_from_env() -> NimConfig:
    return NimConfig(
        base_url=os.getenv("NIM_API_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NIM_API_KEY"),
        timeout_seconds=int(os.getenv("NIM_TIMEOUT", "30")),
        default_model=os.getenv("NIM_DEFAULT_MODEL", "nemotron-3-8b-chat"),
    )
```

Provider config dataclass example:
```python
@dataclass
class NimConfig:
    base_url: str = "https://integrate.api.nvidia.com/v1"
    api_key: str | None = None
    timeout_seconds: int = 30
    default_model: str = "nemotron-3-8b-chat"
```

### 5. Health and Lifecycle Management
Providers are managed as engineering services:

#### ProviderRegistry Health Tracking (`src/aios/core/provider_registry.py`)
- Tracks health via `_provider_health: dict[str, _ProviderHealth]`
- Updates health via `update_provider_health()`
- Exposes health status via `get_provider_info()` and `list_provider_info()`

#### Credential Reload
When credentials are rotated via ConfigurationManager:
```python
def reload_provider_credentials(self, provider_id: str) -> bool:
    with self._lock:
        if provider_id not in self._providers:
            return False
        provider = self._providers[provider_id]
        if hasattr(provider, 'reload_credentials'):
            # Trigger async credential reload
            asyncio.create_task(provider.reload_credentials())
            return True
        return False
```

### 6. Security and Credential Handling
Key security properties:
- **No Secret Exposure**: Credentials never appear in logs, diagnostics, or error messages
- **Fail-Closed Sessions**: `reload_credentials()` closes existing sessions to prevent old credential use
- **Lazy Session Recreation**: New sessions created with fresh credentials in `_ensure_session()`
- **Gate-Before-Connect**: SecurityManager validates all connection attempts

Example credential handling (`src/aios/adapters/nim.py:79-92`):
```python
async def reload_credentials(self) -> None:
    # Close existing session if it exists to prevent use of old credentials
    if self._session and not self._session.closed:
        await self._session.close()
        self._session = None
    # Session recreation with new credentials happens lazily in _ensure_session()
```

### 7. Discovery Integration (Optional)
Providers can optionally implement model discovery:

#### Discovery Protocol (`src/aios/core/model_discovery.py:71-91`)
```python
@runtime_checkable
class DiscoverableProvider(Protocol):
    async def discover_models(self) -> list[ModelMetadata]:
        """Discover available models for this provider."""
        ...
```

#### Discovery Result Handling
```python
async def discover(self) -> DiscoveryResult:
    try:
        models = await self._discover_models_impl()
        return DiscoveryResult(
            success=True,
            models=models,
            provider_id=self._provider_id,
        )
    except Exception as exc:
        return DiscoveryResult(
            success=False,
            error=str(exc),
            provider_id=self._provider_id,
        )
```

### 8. Dashboard Integration
Providers appear in the dashboard via:

#### Integration Status Service (`src/aios/services/integration_status.py`)
- Reports configuration status (YES/NO for credentials) without exposing secrets
- Shows health status and connection mode (mock/real)
- Integrated via `get_integrations_credentials()` in DashboardService

Example from DashboardService (`src/aios/services/dashboard_service.py:425-495`):
```python
def get_integrations_credentials(self) -> dict[str, Any]:
    status_service = getattr(self._kernel, "integration_status_service", None)
    integrations = []
    if status_service is not None:
        integrations = status_service.get_all_status_dict(redact_secrets=True)
    # ... merge with authoritative inventory ...
    return {"page": "integrations_credentials", "integrations": integrations}
```

## Verification Against INV-002 and C10 Constraints

### INV-002: One Model Router Constraint
✅ **SATISFIED**
- All providers register with the **existing** ModelRouter singleton
- No parallel ModelRouter instances are created
- Dispatch uses single `get_model_router()` instance

### C10: No Unmanaged LLM-Stage External Egress  
✅ **SATISFIED**
- All egress goes through provider `generate()` methods
- Providers follow standardized request/response patterns
- No bypass of ModelRouter abstraction
- External calls are managed within provider implementations

## Implementation Template for New Providers

To implement a new provider following the canonical pattern:

### 1. Create Adapter File
`src/aios/adapters/{provider_name}.py`

### 2. Implement Configuration
```python
@dataclass
class {ProviderName}Config:
    base_url: str = "https://api.{provider}.com/v1"
    api_key: str | None = None
    timeout_seconds: int = 30
    default_model: str = "{default-model}"

def get_{provider_name}_config_from_env() -> {ProviderName}Config:
    return {ProviderName}Config(
        base_url=os.getenv("{PROVIDER}_API_URL", "https://api.{provider}.com/v1"),
        api_key=os.getenv("{PROVIDER}_API_KEY"),
        timeout_seconds=int(os.getenv("{PROVIDER}_TIMEOUT", "30")),
        default_model=os.getenv("{PROVIDER}_DEFAULT_MODEL", "{default-model}"),
    )
```

### 3. Implement Provider Class
```python
class {ProviderName}Provider(Provider):
    def __init__(self, config: {ProviderName}Config | None = None):
        self._config = config or {ProviderName}Config()
        self._session = None
    
    async def _ensure_session(self):
        # Create/recreate aiohttp session with current config
        pass
        
    async def close(self):
        # Close session
        pass
        
    def configure(self, config: dict[str, Any]) -> None:
        # Update non-secret config
        pass
        
    async def reload_credentials(self) -> None:
        # Close session to force recreation with new credentials
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def generate(self, request: ModelRequest) -> ModelResponse:
        # Map ModelRequest to provider format
        # Call provider API
        # Normalize response to ModelResponse
        pass
```

### 4. Implement Registration Function
```python
def register_{provider_name}_provider(
    model_router,
    config: {ProviderName}Config | None = None,
) -> {ProviderName}Provider:
    # Create provider instance
    provider = {ProviderName}Provider(config)
    
    # Register model in ModelRouter
    model_config = ModelConfig(
        model_id="{provider_name}-default",
        provider=ModelProvider.{PROVIDER_ENUM},  # or LOCAL
        name="{Provider Name} Default",
        capabilities=[...],
        config={
            "provider": "{provider_name}",
            "{provider_name}": True,  # Backward compatibility
        },
    )
    model_router.register_model(model_config)
    
    # Register with ProviderRegistry
    provider_registry = getattr(model_router, "_provider_registry", None)
    if provider_registry is None:
        provider_registry = get_default_provider_registry()
    provider_registry.register_provider("{provider_name}", provider)
    
    # Backward compatibility
    if not hasattr(model_router, f"_{provider_name}_provider"):
        setattr(model_router, f"_{provider_name}_provider", provider)
        
    return provider
```

### 5. Register in Kernel Startup
Add to `src/aios/core/kernel.py` in the startup sequence:
```python
# Register {Provider Name} provider with ModelRouter
await self._init_{provider_name}()
```

Where `_init_{provider_name}()` follows the pattern of `_init_freellmapi()` and `_init_nim()`.

## Conclusion

The canonical provider pattern established by NIM and FreeLLMAPI provides a robust, secure, and scalable foundation for adding new providers to AI-OS. New providers following this pattern can be integrated without modifying existing closed work, ensuring architectural stability while enabling expansion of the model provider ecosystem.