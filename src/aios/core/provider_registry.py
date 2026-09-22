"""
Core Component C? — ProviderRegistry (AI-OS Architecture Specification).

The ProviderRegistry is a core component that manages the registration
and retrieval of providers for the ModelRouter. It enables the ModelRouter
to be provider-agnostic while maintaining all existing behavior.

Features:
    - Provider registration by stable provider identifier
    - Provider retrieval and existence checking
    - Provider enumeration where appropriate
    - Prevention of accidental duplicate/conflicting registration
    - Thread-safe concurrent access
    - Integration with AI-OS service lifecycle management
    - Provider cooldown management for flaky providers
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

from aios.core.provider import Provider
from aios.core.provider_failures import FailureCategory
from aios.events.core.bus import EventBus
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.core.configuration_manager import get_configuration_manager
from aios.core.model_types import ProviderSelectionPolicy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core Component Event Constants
# ---------------------------------------------------------------------------

_CORE_COMPONENT_INITIALIZED = EventType.CORE_COMPONENT_INITIALIZED
_CORE_COMPONENT_SHUTDOWN = EventType.CORE_COMPONENT_SHUTDOWN


# ---------------------------------------------------------------------------
# Singleton / integration point (kernel.providerRegistry)
# ---------------------------------------------------------------------------

_INSTANCE: ProviderRegistry | None = None
_INSTANCE_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProviderRegistryState(str, Enum):
    """Lifecycle of the ProviderRegistry Core Component itself."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


# Default cooldown durations (in seconds) - can be overridden via configuration
_DEFAULT_COOLDOWN_DURATIONS = {
    FailureCategory.RATE_LIMIT: 60,      # 1 minute
    FailureCategory.QUOTA_EXCEEDED: 300, # 5 minutes
    FailureCategory.TIMEOUT: 30,         # 30 seconds
    FailureCategory.NETWORK: 30,         # 30 seconds
    FailureCategory.SERVER_ERROR: 60,    # 1 minute
    FailureCategory.SERVICE_UNAVAILABLE: 60, # 1 minute
    FailureCategory.AUTHENTICATION: 0,   # No cooldown - auth issues need manual fix
    FailureCategory.INVALID_REQUEST: 0,  # No cooldown - client issue
    FailureCategory.INVALID_MODEL: 0,    # No cooldown - client issue
    FailureCategory.UNKNOWN: 30,         # 30 seconds default
}

# Consecutive health failures before a provider is marked unhealthy.
_HEALTH_FAILURE_THRESHOLD = 3


# Singleton accessor name used by the integration point (kernel.providerRegistry).
_REGISTRY_NAME = "ProviderRegistry"
_REGISTRY_VERSION = SemanticVersion(0, 1, 0)


# ---------------------------------------------------------------------------
# ProviderRegistry — Core Component
# ---------------------------------------------------------------------------


@dataclass
class _ProviderHealth:
    """Internal health tracking for a provider."""

    healthy: bool = True
    consecutive_failures: int = 0
    last_error: str | None = None
    last_health_check_at: str | None = field(
        default_factory=lambda: _now().isoformat()
    )
    # Lifecycle state: whether provider is enabled for use
    enabled: bool = True
    # Cooldown tracking
    cooldown_until: float = 0.0  # Unix timestamp when cooldown expires
    cooldown_category: Optional[FailureCategory] = None  # Reason for cooldown


@dataclass
class ProviderRegistryHealth:
    """Health snapshot of the ProviderRegistry Core Component."""

    healthy: bool
    state: ProviderRegistryState
    total_providers: int
    healthy_providers: int
    unhealthy_providers: int
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "state": self.state.value,
            "total_providers": self.total_providers,
            "healthy_providers": self.healthy_providers,
            "unhealthy_providers": self.unhealthy_providers,
            "details": self.details,
        }


@dataclass
class ProviderInfo:
    """Structured information about a registered provider."""

    id: str
    display_name: str
    enabled: bool
    healthy: bool
    error: str | None
    configured: bool


@dataclass
class ProviderGroup:
    """Configuration for a provider group with load distribution policy."""

    id: str
    label: str
    provider_ids: list[str]
    policy: ProviderSelectionPolicy
    weights: dict[str, float] = field(default_factory=dict)  # provider_id -> weight
    # Round-robin state
    _rr_index: int = field(default=0, init=False)
    # Least connections state
    _connection_counts: dict[str, int] = field(default_factory=dict, init=False)
    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def __post_init__(self):
        """Initialize weights with equal values for all providers if not already set.
        Initialize connection counts for all providers to support connection tracking."""
        if not self.weights and self.provider_ids:
            # Set equal weights for all providers
            self.weights = {provider_id: 1.0 for provider_id in self.provider_ids}
        # Initialize connection counts for all providers (used by LEAST_CONNECTIONS policy)
        if not self._connection_counts and self.provider_ids:
            self._connection_counts = {provider_id: 0 for provider_id in self.provider_ids}


def _now():
    """Get current UTC time for consistent timestamp generation."""
    from datetime import UTC, datetime

    return datetime.now(UTC)


class ProviderRegistry:
    """
    Core Component — ProviderRegistry.

    Owns the authoritative directory of registered providers: their instances
    and health state. Communicates through the injected EventBus.
    Thread-safe.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        # INV-SR-STR-001: exactly one *initialized* instance per process.
        # Allow multiple basic instances for backward compatibility/testing.
        global _INSTANCE
        with _INSTANCE_LOCK:
            if _INSTANCE is not None and _INSTANCE is not self and _INSTANCE.state == ProviderRegistryState.RUNNING:
                raise RuntimeError(
                    "Only one ProviderRegistry instance is permitted per process "
                    "(INV-SR-STR-001). A single constructed instance is rejected."
                )
            _INSTANCE = self

        self._event_bus = event_bus
        self._state = ProviderRegistryState.UNINITIALIZED

        # Provider data (guarded by _lock).
        self._lock = threading.RLock()
        self._providers: dict[str, Provider] = {}
        self._provider_health: dict[str, _ProviderHealth] = {}
        self._provider_groups: dict[str, ProviderGroup] = {}
        self._subscriptions: list[Any] = []  # subscription ids from the bus

        # Cooldown configuration (will be loaded by _load_cooldown_config)
        self._cooldown_enabled = True
        self._base_duration = 30
        self._max_duration = 300
        self._multiplier = 2.0
        self._category_overrides = {}

        # Identity used as the Event ``source`` for registry-emitted events.
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_COMPONENT,
            component_name=_REGISTRY_NAME,
            version=_REGISTRY_VERSION,
        )

        # Load cooldown configuration
        self._load_cooldown_config()

    def _load_cooldown_config(self) -> None:
        """Load cooldown durations from configuration."""
        try:
            config_manager = get_configuration_manager()
            # Load cooldown configuration
            cooldown_config = config_manager.get("provider.cooldown", {})

            # Check if cooldown is enabled
            self._cooldown_enabled = cooldown_config.get("enabled", True)

            # Load base cooldown configuration
            self._base_duration = cooldown_config.get("base_duration_seconds", 30)
            self._max_duration = cooldown_config.get("max_duration_seconds", 300)
            self._multiplier = cooldown_config.get("multiplier", 2.0)

            # Load category-specific overrides
            self._category_overrides = cooldown_config.get("category_overrides", {})

            logger.debug(
                "Loaded provider cooldown configuration: enabled=%s, base_duration=%ds, "
                "max_duration=%ds, multiplier=%.1f",
                self._cooldown_enabled,
                self._base_duration,
                self._max_duration,
                self._multiplier,
            )
        except Exception as e:
            logger.debug("Could not load cooldown configuration: %s", e)
            # Set defaults
            self._cooldown_enabled = True
            self._base_duration = 30
            self._max_duration = 300
            self._multiplier = 2.0
            self._category_overrides = {}

    # --- ICoreComponent: identity / phase / dependencies -----------------

    @property
    def name(self) -> str:
        """Core Component name (ICoreComponent)."""
        return _REGISTRY_NAME

    @property
    def phase(self) -> int:
        """Initialization phase (Part 3 §3.4.3: Phase 1)."""
        return 1

    @property
    def dependencies(self) -> list[str]:
        """Core Component dependencies (Part 3 §3.4.3: EventBus)."""
        return ["EventBus"]

    @property
    def state(self) -> ProviderRegistryState:
        """Current lifecycle state of the registry itself."""
        return self._state

    @property
    def event_bus(self) -> EventBus | None:
        """The injected EventBus (read-only accessor)."""
        return self._event_bus

    # --- ICoreComponent: initialize --------------------------------------

    async def initialize(self, kernel: Any = None) -> ProviderRegistryState:
        """Initialize the registry (Phase 1, depends on EventBus).

        Follows the Core Component pattern (async). Resolves the EventBus
        dependency via DI (constructor) or via the ``kernel`` argument,
        registers internal subscriptions, and publishes ``CoreComponentInitialized``.
        """
        if self._state in (
            ProviderRegistryState.RUNNING,
            ProviderRegistryState.INITIALIZING,
        ):
            return self._state

        self._state = ProviderRegistryState.INITIALIZING

        # Resolve EventBus dependency (INV-SR-INIT-001: operational before any
        # provider accesses). Support DI via constructor or via kernel.
        if self._event_bus is None and kernel is not None:
            self._event_bus = getattr(kernel, "event_bus", None)
        if self._event_bus is None:
            # Defer hard failure: registrations queue, but publishing is a no-op
            # until a bus is attached.
            logger.warning(
                "ProviderRegistry initialized without an EventBus; events will be "
                "deferred until a bus is attached."
            )
        self._kernel = kernel

        # Register internal subscriptions. The registry reacts to
        # ConfigurationFrozen and ProviderFailed to drive health tracking.
        self._register_internal_subscriptions()

        self._state = ProviderRegistryState.RUNNING

        # Publish CoreComponentInitialized{name:"ProviderRegistry"}.
        await self._emit_async(
            _CORE_COMPONENT_INITIALIZED,
            {
                "name": _REGISTRY_NAME,
                "component": _REGISTRY_NAME,
                "state": "RUNNING",
            },
        )
        return self._state

    # --- ICoreComponent: shutdown ----------------------------------------

    async def shutdown(self) -> ProviderRegistryState:
        """Shutdown the registry (Phase S1).

        Deregisters subscriptions, publishes ``CoreComponentShutdown``, then
        transitions to SHUTDOWN.
        """
        if self._state is ProviderRegistryState.SHUTDOWN:
            return self._state
        self._state = ProviderRegistryState.SHUTTING_DOWN

        # Deregister internal subscriptions.
        self._deregister_internal_subscriptions()

        # Publish CoreComponentShutdown.
        await self._emit_async(
            _CORE_COMPONENT_SHUTDOWN,
            {
                "name": _REGISTRY_NAME,
                "component": _REGISTRY_NAME,
                "state": "SHUTDOWN",
            },
        )

        # Registry enters SHUTDOWN.
        self._state = ProviderRegistryState.SHUTDOWN
        return self._state

    # --- ICoreComponent: healthCheck (sync, per pattern) -----------------

    def healthCheck(self) -> ProviderRegistryHealth:
        """Core Component health check (sync).
        
        Also cleans up expired cooldowns to prevent accumulation.
        """
        with self._lock:
            # Clean up expired cooldowns
            self._cleanup_expired_cooldowns()
            
            total = len(self._providers)
            # A provider is considered healthy if:
            # 1. It's marked healthy in health tracking
            # 2. It hasn't exceeded consecutive failure threshold
            # 3. It's not currently in cooldown
            healthy = sum(
                1
                for h in self._provider_health.values()
                if h.healthy
                and h.consecutive_failures < _HEALTH_FAILURE_THRESHOLD
                and not self._is_in_cooldown(h)
            )
            unhealthy = total - healthy

        healthy_state = self._state in (
            ProviderRegistryState.RUNNING,
            ProviderRegistryState.INITIALIZING,
        )
        details = ""
        if unhealthy:
            details = f"{unhealthy} provider(s) unhealthy"

        return ProviderRegistryHealth(
            healthy=healthy_state and unhealthy == 0,
            state=self._state,
            total_providers=total,
            healthy_providers=healthy,
            unhealthy_providers=unhealthy,
            details=details,
        )

    # --- provider management --------------------------------------------

    def register_provider(self, provider_id: str, provider: Provider) -> None:
        """Register a provider with the registry.

        Args:
            provider_id: Stable identifier for the provider
            provider: Provider instance to register

        Raises:
            RuntimeError: If provider_id is already registered
            ValueError: If provider_id is empty or provider is None
        """
        if not provider_id:
            raise ValueError("provider_id must be a non-empty string")
        if provider is None:
            raise ValueError("provider must not be None")

        with self._lock:
            if provider_id in self._providers:
                raise RuntimeError(
                    f"Provider '{provider_id}' is already registered"
                )

            self._providers[provider_id] = provider
            self._provider_health[provider_id] = _ProviderHealth()

        logger.debug("Registering provider '%s' (instance: %s)", provider_id, id(self))
        logger.debug("Registered provider '%s'", provider_id)

    def get_provider(self, provider_id: str) -> Provider | None:
        """Retrieve a registered provider by ID.

        Args:
            provider_id: Identifier of the provider to retrieve

        Returns:
            Provider instance if found, None otherwise
        """
        with self._lock:
            provider = self._providers.get(provider_id)
            # Return None if provider is in cooldown
            if provider is not None:
                health = self._provider_health.get(provider_id)
                if health is not None and self._is_in_cooldown(health):
                    return None
            return provider

    def get_provider_info(self, provider_id: str) -> ProviderInfo | None:
        """Get structured information for a registered provider.

        Args:
            provider_id: Identifier of the provider

        Returns:
            ProviderInfo if provider is found, None otherwise
        """
        with self._lock:
            if provider_id not in self._providers:
                return None

            provider = self._providers[provider_id]
            health = self._provider_health.get(provider_id)
            if health is None:
                # Should not happen in normal operation, but handle gracefully
                health = _ProviderHealth()

            # Determine display name - try to get from provider config or use ID-based derivation
            display_name = self._get_provider_display_name(provider_id, provider)

            # Determine if provider is configured - check if it has necessary configuration
            configured = self._is_provider_configured(provider_id, provider)

            # Determine if provider is currently available (not in cooldown, enabled, healthy)
            available = (
                health.enabled
                and health.healthy
                and health.consecutive_failures < _HEALTH_FAILURE_THRESHOLD
                and not self._is_in_cooldown(health)
            )

            return ProviderInfo(
                id=provider_id,
                display_name=display_name,
                enabled=health.enabled,
                healthy=health.healthy,
                error=health.last_error,
                configured=configured,
            )

    def has_provider(self, provider_id: str) -> bool:
        """Check if a provider is registered.

        Args:
            provider_id: Identifier to check

        Returns:
            True if provider is registered, False otherwise
        """
        with self._lock:
            return provider_id in self._providers

    def list_providers(self) -> list[str]:
        """List all registered provider IDs.

        Returns:
            List of provider IDs (copy to prevent external modification)
        """
        with self._lock:
            return list(self._providers.keys())

    def list_provider_info(self) -> List[ProviderInfo]:
        """List structured information for all registered providers.

        Returns:
            List of ProviderInfo objects for all registered providers
        """
        with self._lock:
            result = []
            for provider_id, provider in self._providers.items():
                health = self._provider_health.get(provider_id)
                if health is None:
                    # Should not happen in normal operation, but handle gracefully
                    health = _ProviderHealth()

                # Determine display name - try to get from provider config or use ID-based derivation
                display_name = self._get_provider_display_name(provider_id, provider)

                # Determine if provider is configured - check if it has necessary configuration
                configured = self._is_provider_configured(provider_id, provider)

                # Determine if provider is currently available (not in cooldown, enabled, healthy)
                available = (
                    health.enabled
                    and health.healthy
                    and health.consecutive_failures < _HEALTH_FAILURE_THRESHOLD
                    and not self._is_in_cooldown(health)
                )

                result.append(ProviderInfo(
                    id=provider_id,
                    display_name=display_name,
                    enabled=health.enabled,
                    healthy=available,
                    error=health.last_error,
                    configured=configured,
                ))
            return result

    def unregister_provider(self, provider_id: str) -> bool:
        """Unregister a provider from the registry.

        Args:
            provider_id: Identifier of the provider to remove

        Returns:
            True if provider was removed, False if not found
        """
        with self._lock:
            if provider_id not in self._providers:
                return False

            del self._providers[provider_id]
            del self._provider_health[provider_id]
            logger.debug("Unregistered provider '%s'", provider_id)
            return True

    def enable_provider(self, provider_id: str) -> bool:
        """Enable a registered provider for normal use.

        Args:
            provider_id: Identifier of the provider to enable

        Returns:
            True if provider was enabled, False if not found or already enabled
        """
        with self._lock:
            if provider_id not in self._providers:
                logger.warning("Attempted to enable unknown provider '%s'", provider_id)
                return False
            health = self._provider_health[provider_id]
            if health.enabled:
                return False
            health.enabled = True
            logger.debug("Enabled provider '%s'", provider_id)
            return True

    def disable_provider(self, provider_id: str) -> bool:
        """Disable a registered provider, preventing normal use.

        Preserves the provider's registration and configuration.
        A disabled provider remains in the registry but is not available
        for ModelRouter dispatch.

        Args:
            provider_id: Identifier of the provider to disable

        Returns:
            True if provider was disabled, False if not found or already disabled
        """
        with self._lock:
            if provider_id not in self._providers:
                logger.warning("Attempted to disable unknown provider '%s'", provider_id)
                return False
            health = self._provider_health[provider_id]
            if not health.enabled:
                return False
            health.enabled = False
            logger.debug("Disabled provider '%s'", provider_id)
            return True

    def reconfigure_provider(self, provider_id: str, config: dict[str, Any]) -> bool:
        """Safely update a provider's runtime configuration.

        Args:
            provider_id: Identifier of the provider to reconfigure
            config: Configuration dict with keys to update (e.g., base_url,
                default_model, timeout_seconds)

        Returns:
            True if provider was reconfigured, False if not found or invalid config
        """
        if not config or not isinstance(config, dict):
            logger.warning("Invalid config for reconfigure_provider: %r", config)
            return False

        with self._lock:
            if provider_id not in self._providers:
                logger.warning("Attempted to reconfigure unknown provider '%s'", provider_id)
                return False

            provider = self._providers[provider_id]
            # Update provider configuration safely by modifying its _config attribute
            if hasattr(provider, "_config") and hasattr(provider._config, "__dict__"):
                for key, value in config.items():
                    if hasattr(provider._config, key):
                        setattr(provider._config, key, value)
                logger.debug("Reconfigured provider '%s' with %s", provider_id, list(config.keys()))
                return True
            else:
                logger.warning("Provider '%s' has no mutable _config; cannot reconfigure", provider_id)
                return False

    def reload_provider_credentials(self, provider_id: str) -> bool:
        """
        Notify a registered provider to reload its credentials.

        This method is called when credentials are rotated via the
        ConfigurationManager to ensure live providers use the new credentials.

        Args:
            provider_id: Identifier of the provider to notify

        Returns:
            True if provider was notified and processed the reload,
                   False if provider not found or does not support credential reload
        """
        with self._lock:
            if provider_id not in self._providers:
                logger.warning("Attempted to reload credentials for unknown provider '%s'", provider_id)
                return False

            provider = self._providers[provider_id]
            # Call the provider's reload_credentials method if it exists
            if hasattr(provider, 'reload_credentials'):
                # Create a task to run the async method without blocking
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule the coroutine to run
                        asyncio.create_task(provider.reload_credentials())
                    else:
                        # Run it directly if no loop is running
                        loop.run_until_complete(provider.reload_credentials())
                except RuntimeError:
                    # No event loop available, try to run synchronously if possible
                    # Note: This assumes reload_credentials can be called synchronously
                    # or we skip it in environments without async support
                    pass
                logger.debug("Triggered credential reload for provider '%s'", provider_id)
                return True
            else:
                logger.debug("Provider '%s' does not support credential reload", provider_id)
                return False

    # --- provider group management --------------------------------------------

    def create_provider_group(
        self,
        group_id: str,
        label: str,
        provider_ids: list[str],
        policy: ProviderSelectionPolicy,
        weights: dict[str, float] | None = None,
    ) -> bool:
        """
        Create a new provider group.

        Args:
            group_id: Unique identifier for the group
            label: Human-readable label for the group
            provider_ids: List of provider IDs that belong to this group
            policy: Selection policy to use for this group
            weights: Optional provider weights for WEIGHTED policy

        Returns:
            True if group was created, False if group ID already exists
        """
        if not group_id:
            logger.warning("Attempted to create provider group with empty ID")
            return False

        if not label:
            logger.warning("Attempted to create provider group with empty label")
            return False

        if not provider_ids:
            logger.warning("Attempted to create provider group with empty provider list")
            return False

        # Validate that all providers exist (warning only, not failure)
        with self._lock:
            unknown_providers = [pid for pid in provider_ids if pid not in self._providers]
            if unknown_providers:
                logger.warning("Attempted to create group with non-existent provider(s): %s", unknown_providers)
                # Continue anyway - providers may be registered later

            if group_id in self._provider_groups:
                logger.warning("Provider group '%s' already exists", group_id)
                return False

            # Initialize weights if not provided (equal weights for all providers)
            if weights is None:
                weights = {provider_id: 1.0 for provider_id in provider_ids}
            elif policy != ProviderSelectionPolicy.WEIGHTED:
                # Weights only make sense for WEIGHTED policy
                logger.warning("Weights provided for non-WEIGHTED policy; ignoring weights")
                weights = {provider_id: 1.0 for provider_id in provider_ids}
            else:
                # Validate weights for WEIGHTED policy
                for provider_id in provider_ids:
                    if provider_id not in weights:
                        weights[provider_id] = 1.0  # Default weight
                    elif weights[provider_id] < 0:
                        logger.warning("Negative weight for provider '%s'; setting to 0", provider_id)
                        weights[provider_id] = 0.0

            # Create the provider group
            group = ProviderGroup(
                id=group_id,
                label=label,
                provider_ids=provider_ids.copy(),
                policy=policy,
                weights=weights.copy(),
            )

            # Initialize connection counts for LEAST_CONNECTIONS
            group._connection_counts = {provider_id: 0 for provider_id in provider_ids}

            self._provider_groups[group_id] = group
            logger.debug("Created provider group '%s' with policy %s", group_id, policy.value)
            return True

    def update_provider_group(
        self,
        group_id: str,
        label: str | None = None,
        policy: ProviderSelectionPolicy | None = None,
        weights: dict[str, float] | None = None,
    ) -> bool:
        """
        Update an existing provider group.

        Args:
            group_id: Identifier of the group to update
            label: New label for the group (optional)
            policy: New selection policy for the group (optional)
            weights: New provider weights for WEIGHTED policy (optional)

        Returns:
            True if group was updated, False if not found
        """
        if not group_id:
            logger.warning("Attempted to update provider group with empty ID")
            return False

        with self._lock:
            if group_id not in self._provider_groups:
                logger.warning("Attempted to update unknown provider group '%s'", group_id)
                return False

            group = self._provider_groups[group_id]

            if label is not None:
                if not label:
                    logger.warning("Attempted to set empty label for provider group '%s'", group_id)
                    return False
                group.label = label

            if policy is not None:
                group.policy = policy
                # Reset weights when policy changes to/from WEIGHTED
                if policy != ProviderSelectionPolicy.WEIGHTED:
                    group.weights = {provider_id: 1.0 for provider_id in group.provider_ids}
                elif weights is None:
                    # Ensure weights exist for WEIGHTED policy
                    group.weights = {provider_id: 1.0 for provider_id in group.provider_ids}

            if weights is not None:
                if group.policy != ProviderSelectionPolicy.WEIGHTED:
                    logger.warning("Weights provided for non-WEIGHTED policy '%s'; ignoring weights", group.policy.value)
                else:
                    # Validate and update weights
                    for provider_id in group.provider_ids:
                        if provider_id in weights:
                            if weights[provider_id] < 0:
                                logger.warning("Negative weight for provider '%s'; setting to 0", provider_id)
                                group.weights[provider_id] = 0.0
                            else:
                                group.weights[provider_id] = weights[provider_id]
                        else:
                            group.weights[provider_id] = 1.0  # Default weight

            logger.debug("Updated provider group '%s'", group_id)
            return True

    def remove_provider_group(self, group_id: str) -> bool:
        """
        Remove a provider group.

        Args:
            group_id: Identifier of the group to remove

        Returns:
            True if group was removed, False if not found
        """
        if not group_id:
            logger.warning("Attempted to remove provider group with empty ID")
            return False

        with self._lock:
            if group_id not in self._provider_groups:
                logger.warning("Attempted to remove unknown provider group '%s'", group_id)
                return False

            del self._provider_groups[group_id]
            logger.debug("Removed provider group '%s'", group_id)
            return True

    def add_provider_to_group(self, group_id: str, provider_id: str) -> bool:
        """
        Add a provider to an existing group.

        Args:
            group_id: Identifier of the group
            provider_id: Identifier of the provider to add

        Returns:
            True if provider was added, False if group or provider not found
        """
        if not group_id:
            logger.warning("Attempted to add provider to group with empty group ID")
            return False

        if not provider_id:
            logger.warning("Attempted to add provider with empty provider ID to group")
            return False

        with self._lock:
            if group_id not in self._provider_groups:
                logger.warning("Attempted to add provider to unknown group '%s'", group_id)
                return False

            # Validate that provider exists (warning only, not failure)
            # Allow forward references - providers may be registered later
            if provider_id not in self._providers:
                logger.warning("Attempted to add unknown provider '%s' to group '%s'; adding anyway", provider_id, group_id)
                # Continue anyway - provider may be registered later

            group = self._provider_groups[group_id]

            if provider_id in group.provider_ids:
                logger.debug("Provider '%s' already in group '%s'", provider_id, group_id)
                return False  # Already in group

            group.provider_ids.append(provider_id)

            # Initialize weight for new provider
            if group.policy == ProviderSelectionPolicy.WEIGHTED:
                group.weights[provider_id] = group.weights.get(provider_id, 1.0)
            else:
                # For non-weighted policies, ensure weight exists
                group.weights[provider_id] = 1.0

            # Initialize connection count for all policies (used by LEAST_CONNECTIONS)
            if provider_id not in group._connection_counts:
                group._connection_counts[provider_id] = 0

            logger.debug("Added provider '%s' to group '%s'", provider_id, group_id)
            return True

    def remove_provider_from_group(self, group_id: str, provider_id: str) -> bool:
        """
        Remove a provider from an existing group.

        Args:
            group_id: Identifier of the group
            provider_id: Identifier of the provider to remove

        Returns:
            True if provider was removed, False if group or provider not found
        """
        if not group_id:
            logger.warning("Attempted to remove provider from group with empty group ID")
            return False

        if not provider_id:
            logger.warning("Attempted to remove provider with empty provider ID from group")
            return False

        with self._lock:
            if group_id not in self._provider_groups:
                logger.warning("Attempted to remove provider from unknown group '%s'", group_id)
                return False

            group = self._provider_groups[group_id]

            if provider_id not in group.provider_ids:
                logger.debug("Provider '%s' not in group '%s'", provider_id, group_id)
                return False  # Not in group

            group.provider_ids.remove(provider_id)

            # Clean up weight
            group.weights.pop(provider_id, None)

            # Clean up connection count
            group._connection_counts.pop(provider_id, None)

            logger.debug("Removed provider '%s' from group '%s'", provider_id, group_id)
            return True
        """
        Notify a registered provider to reload its credentials.

        This method is called when credentials are rotated via the
        ConfigurationManager to ensure live providers use the new credentials.

        Args:
            provider_id: Identifier of the provider to notify

        Returns:
            True if provider was notified and processed the reload,
                   False if provider not found or does not support credential reload
        """
        with self._lock:
            if provider_id not in self._providers:
                logger.warning("Attempted to reload credentials for unknown provider '%s'", provider_id)
                return False

            provider = self._providers[provider_id]
            # Call the provider's reload_credentials method if it exists
            if hasattr(provider, 'reload_credentials'):
                # Create a task to run the async method without blocking
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule the coroutine to run
                        asyncio.create_task(provider.reload_credentials())
                    else:
                        # Run it directly if no loop is running
                        loop.run_until_complete(provider.reload_credentials())
                except RuntimeError:
                    # No event loop available, try to run synchronously if possible
                    # Note: This assumes reload_credentials can be called synchronously
                    # or we skip it in environments without async support
                    pass
                logger.debug("Triggered credential reload for provider '%s'", provider_id)
                return True
            else:
                logger.debug("Provider '%s' does not support credential reload", provider_id)
                return False

    def update_provider_health(
        self, provider_id: str, healthy: bool, error: str | None = None
    ) -> None:
        """Update the health status of a provider.

        Args:
            provider_id: Identifier of the provider
            healthy: Whether the provider is healthy
            error: Error message if unhealthy (optional)
        """
        with self._lock:
            if provider_id not in self._provider_health:
                logger.warning("Attempted to update health for unknown provider '%s'", provider_id)
                return

            health = self._provider_health[provider_id]
            if healthy:
                health.healthy = True
                health.consecutive_failures = 0
                # Clear cooldown when health is restored
                # Emit provider cooldown expired event if there was an active cooldown
                if health.cooldown_until > 0:
                    try:
                        event = Event(
                            eventType=EventType.PROVIDER_COOLDOWN_EXPIRED,
                            source=self._identity,
                            payload={
                                "provider_id": provider_id,
                                "previous_category": health.cooldown_category.value if health.cooldown_category else None,
                                "expired_at": time.time(),
                            },
                        )
                        self._event_bus.publish(event)
                    except Exception as e:
                        logger.debug("Failed to emit provider cooldown expired event: %s", e)

                health.cooldown_until = 0.0
                health.cooldown_category = None
            else:
                health.healthy = False
                health.consecutive_failures += 1
                health.last_error = error
            health.last_health_check_at = _now().isoformat()

            # Track consecutive failures
            if health.consecutive_failures >= _HEALTH_FAILURE_THRESHOLD:
                logger.warning(
                    "Provider '%s' marked unhealthy after %d consecutive failures",
                    provider_id,
                    health.consecutive_failures,
                )

    def update_provider_health_from_failure(
        self, provider_id: str, failure: ProviderFailure
    ) -> None:
        """
        Update provider health based on a structured failure classification.

        This method applies the appropriate health impact based on failure type:
        - AUTHENTICATION, INVALID_REQUEST, INVALID_MODEL: Do not affect health
          (configuration/request issues, not provider faults)
        - RATE_LIMIT, QUOTA_EXCEEDED: May affect health but not treated as permanent failure
        - TIMEOUT, NETWORK, SERVER_ERROR, SERVICE_UNAVAILABLE: Affect health as transient issues
        - UNKNOWN: Conservative approach - does not affect health by default

        Additionally, applies cooldown for appropriate failure types to prevent
        hammering flaky providers. Cooldown duration increases exponentially with
        consecutive failures up to a maximum duration for applicable categories.

        Args:
            provider_id: Identifier of the provider
            failure: Structured failure information
        """
        # Determine if this failure should affect provider health
        should_affect_health = False
        base_cooldown_duration = 0  # Default no cooldown

        if failure.category in (
            FailureCategory.AUTHENTICATION,
            FailureCategory.INVALID_REQUEST,
            FailureCategory.INVALID_MODEL,
        ):
            # These are configuration/request issues, not provider faults
            should_affect_health = False
            # Use override if present and non-zero, otherwise fall back to default
            override_duration = self._category_overrides.get(failure.category.value)
            if override_duration is not None:
                base_cooldown_duration = int(override_duration)
            else:
                # Fall back to default duration for this category
                base_cooldown_duration = _DEFAULT_COOLDOWN_DURATIONS.get(failure.category, 0)
        elif failure.category in (
            FailureCategory.RATE_LIMIT,
            FailureCategory.QUOTA_EXCEEDED,
        ):
            # These may indicate temporary issues but we're conservative with health impact
            # For now, we'll not count them as health-affecting to avoid prematurely marking
            # providers unhealthy due to client-side rate limiting/quota issues
            should_affect_health = False
            # For rate limit and quota exceeded, we use the override if present, otherwise fall back to default
            # (no exponential backoff for these categories)
            override_duration = self._category_overrides.get(failure.category.value)
            if override_duration is not None:
                base_cooldown_duration = int(override_duration)
            else:
                # Fall back to default duration for this category
                base_cooldown_duration = _DEFAULT_COOLDOWN_DURATIONS.get(failure.category, 0)
        elif failure.category in (
            FailureCategory.TIMEOUT,
            FailureCategory.NETWORK,
            FailureCategory.SERVER_ERROR,
            FailureCategory.SERVICE_UNAVAILABLE,
        ):
            # These are transient infrastructure issues that should affect health
            should_affect_health = True
            # For these categories, we calculate exponential backoff based on base duration
            override_duration = self._category_overrides.get(failure.category.value)
            if override_duration is not None:
                base_cooldown_duration = int(override_duration)
            else:
                # Fall back to configured base duration for calculation
                base_cooldown_duration = self._base_duration
        elif failure.category == FailureCategory.UNKNOWN:
            # Conservative approach for unknown failures - don't affect health by default
            should_affect_health = False
            # For unknown failures, we use the override if present, otherwise fall back to default
            override_duration = self._category_overrides.get(failure.category.value)
            if override_duration is not None:
                base_cooldown_duration = int(override_duration)
            else:
                # Fall back to default duration for this category
                base_cooldown_duration = _DEFAULT_COOLDOWN_DURATIONS.get(failure.category, 0)

        # Update health using the existing method
        self.update_provider_health(
            provider_id=provider_id,
            healthy=not should_affect_health,
            error=failure.safe_message if should_affect_health else None,
        )

        # Apply cooldown if cooldown is enabled and base duration is > 0
        if self._cooldown_enabled and base_cooldown_duration > 0:
            # For certain categories (rate_limit, quota_exceeded, unknown), use the configured duration directly
            # For others (timeout, network, server_error, service_unavailable), apply exponential backoff
            if failure.category in (
                FailureCategory.RATE_LIMIT,
                FailureCategory.QUOTA_EXCEEDED,
                FailureCategory.UNKNOWN,
            ):
                cooldown_duration = base_cooldown_duration
            else:
                # Calculate exponential backoff: base * (multiplier ^ consecutive_failures)
                # but cap at max_duration
                health = self._provider_health[provider_id]
                # Note: consecutive_failures has already been incremented by update_provider_health
                # So we use (consecutive_failures - 1) to get the failure count that led to this cooldown
                exponential_backoff = base_cooldown_duration * (self._multiplier ** max(0, health.consecutive_failures - 1))
                cooldown_duration = min(int(exponential_backoff), self._max_duration)

                # Ensure minimum cooldown of base_duration if we have consecutive failures
                if health.consecutive_failures > 0:
                    cooldown_duration = max(cooldown_duration, base_cooldown_duration)

            self._apply_cooldown(provider_id, failure.category, cooldown_duration)

    def _apply_cooldown(
        self, provider_id: str, category: FailureCategory, duration_seconds: int
    ) -> None:
        """Apply a cooldown to a provider.

        Args:
            provider_id: Identifier of the provider
            category: Failure category that triggered the cooldown
            duration_seconds: Duration of cooldown in seconds
        """
        with self._lock:
            if provider_id not in self._provider_health:
                logger.warning("Attempted to apply cooldown to unknown provider '%s'", provider_id)
                return

            health = self._provider_health[provider_id]
            health.cooldown_until = time.time() + duration_seconds
            health.cooldown_category = category
            logger.info(
                "Applied %d-second cooldown to provider '%s' due to %s failure",
                duration_seconds,
                provider_id,
                category.value,
            )
            # Emit provider cooldown started event
            try:
                event = Event(
                    eventType=EventType.PROVIDER_COOLDOWN_STARTED,
                    source=self._identity,
                    payload={
                        "provider_id": provider_id,
                        "category": category.value,
                        "duration_seconds": duration_seconds,
                        "cooldown_until": health.cooldown_until,
                    },
                )
                self._event_bus.publish(event)
            except Exception as e:
                logger.debug("Failed to emit provider cooldown started event: %s", e)

    def _cleanup_expired_cooldowns(self) -> None:
        """Remove expired cooldowns from providers.
        
        This method should be called periodically to clean up expired cooldowns
        and make providers available again.
        """
        with self._lock:
            current_time = time.time()
            cleaned_count = 0
            
            for provider_id, health in self._provider_health.items():
                if self._is_in_cooldown(health) and health.cooldown_until <= current_time:
                    # Cooldown has expired
                    # Emit provider cooldown expired event
                    try:
                        event = Event(
                            eventType=EventType.PROVIDER_COOLDOWN_EXPIRED,
                            source=self._identity,
                            payload={
                                "provider_id": provider_id,
                                "previous_category": health.cooldown_category.value if health.cooldown_category else None,
                                "expired_at": time.time(),
                            },
                        )
                        self._event_bus.publish(event)
                    except Exception as e:
                        logger.debug("Failed to emit provider cooldown expired event: %s", e)

                    health.cooldown_until = 0.0
                    health.cooldown_category = None
                    cleaned_count += 1
                    logger.debug("Cleared expired cooldown for provider '%s'", provider_id)
            
            if cleaned_count > 0:
                logger.info("Cleaned up %d expired provider cooldowns", cleaned_count)

    def _is_in_cooldown(self, health: _ProviderHealth) -> bool:
        """Check if a provider is currently in cooldown.

        Args:
            health: Provider health object to check

        Returns:
            True if provider is in cooldown, False otherwise
        """
        if health.cooldown_until <= 0:
            return False
        return time.time() < health.cooldown_until

    def clear_cooldown(self, provider_id: str) -> bool:
        """Manually clear a provider's cooldown.

        Args:
            provider_id: Identifier of the provider

        Returns:
            True if cooldown was cleared, False if provider not found or not in cooldown
        """
        with self._lock:
            if provider_id not in self._provider_health:
                logger.warning("Attempted to clear cooldown for unknown provider '%s'", provider_id)
                return False

            health = self._provider_health[provider_id]
            if not self._is_in_cooldown(health):
                return False

            # Emit provider cooldown expired event for manual clear
            try:
                event = Event(
                    eventType=EventType.PROVIDER_COOLDOWN_EXPIRED,
                    source=self._identity,
                    payload={
                        "provider_id": provider_id,
                        "previous_category": health.cooldown_category.value if health.cooldown_category else None,
                        "expired_at": time.time(),
                        "manual_clear": True,
                    },
                )
                self._event_bus.publish(event)
            except Exception as e:
                logger.debug("Failed to emit provider cooldown expired event: %s", e)

            health.cooldown_until = 0.0
            health.cooldown_category = None
            logger.info("Cleared cooldown for provider '%s'", provider_id)
            return True

    def get_provider_cooldown_remaining(self, provider_id: str) -> float:
        """Get remaining cooldown time for a provider in seconds.

        Args:
            provider_id: Identifier of the provider

        Returns:
            Remaining cooldown time in seconds, 0 if not in cooldown or provider not found
        """
        with self._lock:
            if provider_id not in self._provider_health:
                return 0.0

            health = self._provider_health[provider_id]
            if not self._is_in_cooldown(health):
                return 0.0

            remaining = health.cooldown_until - time.time()
            return max(0.0, remaining)

    # --- provider group management ---

    def has_provider_group(self, group_id: str) -> bool:
        """
        Check if a provider group exists.

        Args:
            group_id: Identifier of the group to check

        Returns:
            True if group exists, False otherwise
        """
        if not group_id:
            return False
        with self._lock:
            return group_id in self._provider_groups

    def get_provider_group(self, group_id: str) -> ProviderGroup | None:
        """
        Get a provider group by its identifier.

        Args:
            group_id: Identifier of the group to retrieve

        Returns:
            ProviderGroup instance if found, None otherwise
        """
        if not group_id:
            return None
        with self._lock:
            return self._provider_groups.get(group_id)

    def list_provider_groups(self) -> list[ProviderGroup]:
        """
        List all provider groups.

        Returns:
            List of all ProviderGroup instances
        """
        with self._lock:
            return list(self._provider_groups.values())

    def select_provider_from_group(
        self,
        group_id: str,
        model_id: str | None = None
    ) -> str | None:
        """
        Select a provider from a provider group using the group's selection policy.

        Args:
            group_id: Identifier of the group to select from
            model_id: Optional model ID for context (used in logging)

        Returns:
            Selected provider ID, or None if group not found or no providers available
        """
        if not group_id:
            logger.warning("Attempted to select provider from group with empty ID")
            return None

        with self._lock:
            group = self._provider_groups.get(group_id)
            if group is None:
                logger.warning("Attempted to select provider from unknown group '%s'", group_id)
                return None

            if not group.provider_ids:
                logger.warning("Attempted to select provider from empty group '%s'", group_id)
                return None

            # Filter out unavailable providers (health check, cooldown, etc.)
            available_providers = []
            for provider_id in group.provider_ids:
                # Check if provider exists
                if provider_id not in self._providers:
                    logger.debug("Provider '%s' in group '%s' not found in registry", provider_id, group_id)
                    continue

                # Check if provider is enabled and healthy
                provider_health = self._provider_health.get(provider_id)
                if provider_health is None:
                    logger.debug("Provider '%s' in group '%s' has no health record", provider_id, group_id)
                    continue

                if not provider_health.enabled:
                    logger.debug("Provider '%s' in group '%s' is disabled", provider_id, group_id)
                    continue

                # Check if provider is in cooldown
                if self._is_in_cooldown(provider_health):
                    logger.debug("Provider '%s' in group '%s' is in cooldown", provider_id, group_id)
                    continue

                available_providers.append(provider_id)

            if not available_providers:
                logger.warning("No available providers in group '%s' for model '%s'", group_id, model_id or "unknown")
                return None

            # Apply selection policy
            selected_provider = None
            if group.policy == ProviderSelectionPolicy.ROUND_ROBIN:
                # Round-robin selection
                selected_provider = available_providers[group._rr_index % len(available_providers)]
                group._rr_index = (group._rr_index + 1) % len(available_providers)

            elif group.policy == ProviderSelectionPolicy.WEIGHTED:
                # Weighted selection
                total_weight = sum(group.weights.get(pid, 1.0) for pid in available_providers)
                if total_weight <= 0:
                    # Fallback to round-robin if weights are invalid
                    selected_provider = available_providers[group._rr_index % len(available_providers)]
                    group._rr_index = (group._rr_index + 1) % len(available_providers)
                else:
                    import random
                    r = random.uniform(0, total_weight)
                    weight_sum = 0
                    for provider_id in available_providers:
                        weight_sum += group.weights.get(provider_id, 1.0)
                        if weight_sum >= r:
                            selected_provider = provider_id
                            break
                    # Fallback (should not happen with proper weights)
                    if selected_provider is None:
                        selected_provider = available_providers[0]

            elif group.policy == ProviderSelectionPolicy.LEAST_CONNECTIONS:
                # Least connections selection
                min_connections = float('inf')
                selected_provider = None
                for provider_id in available_providers:
                    connections = group._connection_counts.get(provider_id, 0)
                    if connections < min_connections:
                        min_connections = connections
                        selected_provider = provider_id
                    elif connections == min_connections and selected_provider is None:
                        # Tie-breaker: pick the first one
                        selected_provider = provider_id

                # Increment connection count for selected provider
                if selected_provider is not None:
                    group._connection_counts[selected_provider] = group._connection_counts.get(selected_provider, 0) + 1

            else:
                # Unknown policy, fallback to first available
                logger.warning("Unknown selection policy '%s' for group '%s'; using first available", group.policy, group_id)
                selected_provider = available_providers[0]

            if selected_provider is not None:
                logger.debug(
                    "Selected provider '%s' from group '%s' (policy: %s, model: %s)",
                    selected_provider, group_id, group.policy.value, model_id or "unknown"
                )
                return selected_provider
            else:
                logger.warning("No provider selected from group '%s'", group_id)
                return None

    # --- introspection ---------------------------------------------------

    def __contains__(self, provider_id: str) -> bool:
        with self._lock:
            return provider_id in self._providers

    def __len__(self) -> int:
        with self._lock:
            return len(self._providers)

    def get_stats(self) -> dict[str, Any]:
        """Registry statistics."""
        h = self.healthCheck()
        with self._lock:
            by_status: dict[str, int] = {"healthy": 0, "unhealthy": 0}
            for health in self._provider_health.values():
                key = "healthy" if health.healthy and health.consecutive_failures < _HEALTH_FAILURE_THRESHOLD and not self._is_in_cooldown(health) else "unhealthy"
                by_status[key] += 1
        return {
            "name": self.name,
            "state": self._state.value,
            "total_providers": h.total_providers,
            "healthy_providers": h.healthy_providers,
            "unhealthy_providers": h.unhealthy_providers,
        }

    def _get_provider_display_name(self, provider_id: str, provider: Provider) -> str:
        """Get display name for a provider.

        Attempts to derive a human-readable display name from the provider.
        Falls back to a deterministic transformation of the provider ID.

        Args:
            provider_id: The provider identifier
            provider: The provider instance

        Returns:
            A human-readable display name
        """
        # Try to get display name from provider attributes
        if hasattr(provider, 'display_name') and isinstance(provider.display_name, str):
            return provider.display_name

        # Try to get display name from provider config
        if hasattr(provider, '_config'):
            config = getattr(provider, '_config', None)
            if config and hasattr(config, 'display_name') and isinstance(config.display_name, str):
                return config.display_name

        # Fallback: derive display name from provider ID
        # Convert snake_case or kebab-case to space-separated uppercase words
        # Examples: "nim" -> "NIM", "freellmapi" -> "FREELLM API", "test-provider" -> "TEST PROVIDER"
        parts = provider_id.replace('-', '_').split('_')
        return ' '.join(part.upper() for part in parts if part)

    def _is_provider_configured(self, provider_id: str, provider: Provider) -> bool:
        """Determine if a provider is configured for use.

        Checks if the provider has the necessary configuration to be usable,
        without exposing any secret values.

        Args:
            provider_id: The provider identifier
            provider: The provider instance

        Returns:
            True if provider appears to be configured, False otherwise
        """
        # A provider is considered configured if it's successfully registered
        # More sophisticated configuration checking would require provider-specific logic
        # or access to credential stores, which we avoid to prevent exposing secrets
        # or creating tight coupling.

        # For now, consider a registered provider as configured by default
        # Individual providers can implement more specific logic in their own ways
        # if needed, but that would be internal to the provider itself
        return True

    # =====================================================================
    # Internal helpers
    # =====================================================================

    def _register_internal_subscriptions(self) -> None:
        """Register internal subscriptions for health coordination."""
        if self._event_bus is None:
            return
        try:
            from aios.events.core.manager import SubscribeOptions

            # Subscribe to ConfigurationFrozen and ProviderHealthUpdated
            sub_inits = [
                (
                    EventType.CONFIGURATION_FROZEN,
                    self._on_configuration_frozen,
                ),
                # Note: ProviderHealthUpdated would be a custom event type
                # For now, we rely on explicit health updates via update_provider_health
            ]
            for et, handler in sub_inits:
                try:
                    sub_id = self._event_bus.subscribe(
                        SubscribeOptions(
                            subscriber=self._identity,
                            event_types=(et,),
                            handler=handler,
                            handler_type="sync",
                        )
                    )
                    self._subscriptions.append(sub_id)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Internal subscription to %s skipped: %s", et, exc)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Internal subscriptions not registered: %s", exc)

    def _deregister_internal_subscriptions(self) -> None:
        """Deregister internal subscriptions."""
        if self._event_bus is None:
            return
        for sub_id in self._subscriptions:
            try:
                self._event_bus.unsubscribe(sub_id)
            except Exception:  # noqa: BLE001
                pass
        self._subscriptions.clear()

    def _on_configuration_frozen(self, event: Event) -> None:
        """React to ConfigurationFrozen."""
        logger.debug("ProviderRegistry observed ConfigurationFrozen.")
        # Reload cooldown configuration when configuration is frozen
        self._load_cooldown_config()

    # --- event emission (canonical EventTypes only) ----------------------

    def _make_event(self, event_type: EventType, payload: dict[str, Any]) -> Event:
        """Build a canonical Event with this registry as the source identity."""
        return Event(
            eventType=event_type,
            source=self._identity,
            correlationId=self._generate_correlation_id(),
            payload=payload,
        )

    def _generate_correlation_id(self):
        """Generate a correlation ID for events."""
        import uuid

        return uuid.uuid4()

    def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event from a SYNCHRONOUS call site."""
        bus = self._event_bus
        if bus is None:
            return
        try:
            event = self._make_event(event_type, payload)
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Inside a running loop: schedule without blocking the lock.
                    loop.create_task(bus.publish(event))
                    return
            except RuntimeError:
                pass
            # No running loop: defer publication
            logger.debug(
                "Event %s not dispatched (no running loop); bus will not see it "
                "from this synchronous call site.",
                event_type.name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Event emission of %s failed: %s", event_type.name, exc)

    async def _emit_async(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event from an ASYNCHRONOUS call site."""
        bus = self._event_bus
        if bus is None:
            return
        try:
            event = self._make_event(event_type, payload)
            await bus.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Async event emission of %s failed: %s", event_type.name, exc)


# ---------------------------------------------------------------------------
# Singleton / integration point (kernel.providerRegistry)
# ---------------------------------------------------------------------------


_INSTANCE: ProviderRegistry | None = None
_INSTANCE_LOCK = threading.RLock()


def reset_provider_registry_singleton() -> None:
    """Reset the process-wide ProviderRegistry singleton (tests only)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


def get_provider_registry(event_bus: EventBus | None = None) -> ProviderRegistry:
    """Get (or create) the global ProviderRegistry singleton.

    Integration point for ``kernel.providerRegistry``. Production code MUST NOT
    construct twice; use this accessor.
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = ProviderRegistry(event_bus=event_bus)
        elif event_bus is not None and _INSTANCE._event_bus is None:
            _INSTANCE._event_bus = event_bus
        return _INSTANCE


def set_provider_registry(registry: ProviderRegistry) -> None:
    """Set the global ProviderRegistry singleton (kernel-owned construction)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = registry


# ---------------------------------------------------------------------------
# Default provider registry accessor
# ---------------------------------------------------------------------------


def get_default_provider_registry() -> ProviderRegistry:
    """Get the default ProviderRegistry instance for backward compatibility.

    Returns a ProviderRegistry instance that may not be fully initialized
    but can be used for basic provider registration/retrieval.
    """
    return ProviderRegistry()


__all__ = [
    "ProviderRegistry",
    "ProviderRegistryState",
    "ProviderRegistryHealth",
    "get_provider_registry",
    "set_provider_registry",
    "reset_provider_registry_singleton",
    "get_default_provider_registry",
]