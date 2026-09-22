"""
Rate Limit Quota Manager for AI-OS Hermes Kernel.

Provides pre-routing rate-limit and quota enforcement for model/provider calls,
integrating with the existing timestamped usage accounting foundation and
ResourceManager infrastructure.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from aios.core.configuration_manager import get_configuration_manager
from aios.core.provider_failures import ProviderFailure, FailureCategory, classify_failure
from aios.core.resource_manager import (
    ResourceManager,
    ResourceType,
    get_resource_manager,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion


class QuotaType(Enum):
    """Types of quotas that can be enforced."""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_DAY = "requests_per_day"
    TOKENS_PER_MINUTE = "tokens_per_minute"
    TOKENS_PER_DAY = "tokens_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"


@dataclass
class QuotaLimit:
    """Configuration for a specific quota limit."""
    quota_type: QuotaType
    limit: int
    enabled: bool = True
    provider_id: Optional[str] = None  # None means applies to all providers
    model_id: Optional[str] = None     # None means applies to all models
    description: str = ""


@dataclass
class QuotaUsage:
    """Tracks current usage against a quota."""
    quota_type: QuotaType
    provider_id: str
    model_id: str
    current_usage: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    concurrent_count: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Lease:
    """Represents an acquired lease for concurrent request limiting."""
    lease_id: str
    provider_id: str
    model_id: str
    acquired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class RateLimitQuotaManager:
    """
    Pre-routing rate-limit and quota enforcement for model/provider calls.

    Integrates with existing ModelRouter, ResourceManager, and timestamped usage
    accounting to enforce limits before provider invocation.

    Architecture:
    ModelRouter -> RateLimitQuotaManager.check/admit -> Provider invocation
                                      |
                                      +-> Usage accounting (existing)
                                      |
                                      +-> ResourceManager (existing)
                                      |
                                      +-> ConfigurationManager (existing)
                                      |
                                      +-> ProviderRegistry (existing)
                                      |
                                      +-> Failure/Event infrastructure (existing)
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        resource_manager: Optional[ResourceManager] = None,
        model_router: Any = None,
    ):
        """
        Initialize the Rate Limit Quota Manager.

        Args:
            config: Configuration dictionary (uses ConfigurationManager if None)
            resource_manager: ResourceManager instance (uses singleton if None)
            model_router: ModelRouter instance (uses singleton if None)
        """
        # Dependencies - use singletons if not provided
        self._config_manager = get_configuration_manager()
        self._resource_manager = resource_manager or get_resource_manager()
        self._event_bus = get_core_event_bus()
        # Set model_router - use injected instance if provided, otherwise defer to lazy resolution
        self._model_router = model_router

        # Configuration
        self._config = config or {}
        self._enabled = self._config.get("enabled", True)

        # Quota limits - loaded from configuration
        self._quota_limits: Dict[str, QuotaLimit] = {}  # key: f"{provider}:{model}:{quota_type}"
        self._load_quota_limits()

        # Usage tracking
        self._usage_tracking: Dict[str, QuotaUsage] = {}  # key: f"{provider}:{model}:{quota_type}"
        self._usage_lock = threading.RLock()

        # Concurrent request leases
        self._active_leases: Dict[str, Lease] = {}  # key: lease_id
        self._lease_lock = threading.RLock()
        self._next_lease_id = 1

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="RateLimitQuotaManager",
            version=SemanticVersion(1, 0, 0),
        )

        # Lazily initialized model router - will be fetched on first use
        self._model_router_lazy = None

    def _get_model_router(self):
        """Get the ModelRouter instance via lazy resolution.

        Imports get_model_router only when called, not at module load time.
        If an explicit instance was injected, returns it directly.
        Otherwise resolves the singleton at runtime.

        Returns:
            ModelRouter instance
        """
        if self._model_router is not None:
            return self._model_router

        from aios.core.model_router import get_model_router
        return get_model_router()

    def _load_configuration(self) -> None:
        """Load rate limit and quota configuration from ConfigurationManager."""
        try:
            # Load enabled flag
            self._enabled = self._config_manager.get("rate_limit_quota.enabled", self._enabled)

            # Load quota limits configuration
            quota_configs = self._config_manager.get("rate_limit_quota.limits", [])
            if quota_configs:
                self._quota_limits.clear()
                for quota_dict in quota_configs:
                    quota_limit = self._dict_to_quota_limit(quota_dict)
                    if quota_limit:
                        key = self._get_quota_key(quota_limit)
                        self._quota_limits[key] = quota_limit

        except Exception as e:
            # Log but don't fail - use defaults if configuration loading fails
            pass

    def _load_quota_limits(self) -> None:
        """Load quota limits from internal configuration."""
        # This method is kept for backward compatibility with direct config dict
        pass

    def _initialize_default_limits(self) -> None:
        """Initialize default quota limits based on existing ResourceManager limits."""
        # Get default limits from ResourceManager
        resource_manager = get_resource_manager()

        # Default requests per minute limit (from ResourceManager.RATE_LIMIT)
        rate_limit = resource_manager.get_limit(ResourceType.RATE_LIMIT)
        if rate_limit:
            self.add_quota_limit(QuotaLimit(
                quota_type=QuotaType.REQUESTS_PER_MINUTE,
                limit=int(rate_limit.limit),
                description="Default requests per minute limit"
            ))

        # Default requests per day limit (from ResourceManager.API_QUOTA)
        api_quota = resource_manager.get_limit(ResourceType.API_QUOTA)
        if api_quota:
            # Convert daily quota to requests per day
            self.add_quota_limit(QuotaLimit(
                quota_type=QuotaType.REQUESTS_PER_DAY,
                limit=int(api_quota.limit),
                description="Default requests per day limit"
            ))

        # Default concurrent requests limit (conservative default)
        self.add_quota_limit(QuotaLimit(
            quota_type=QuotaType.CONCURRENT_REQUESTS,
            limit=10,
            description="Default concurrent request limit"
        ))

        # Token limits - estimate based on typical usage patterns
        # These are conservative defaults that can be overridden via configuration
        self.add_quota_limit(QuotaLimit(
            quota_type=QuotaType.TOKENS_PER_MINUTE,
            limit=10000,
            description="Default tokens per minute limit"
        ))
        self.add_quota_limit(QuotaLimit(
            quota_type=QuotaType.TOKENS_PER_DAY,
            limit=1000000,
            description="Default tokens per day limit"
        ))

    def _dict_to_quota_limit(self, quota_dict: Dict[str, Any]) -> Optional[QuotaLimit]:
        """Convert a dictionary to a QuotaLimit object."""
        try:
            quota_type_str = quota_dict.get("quota_type", "").lower()
            quota_type = None

            # Map string to QuotaType enum
            for qt in QuotaType:
                if qt.value == quota_type_str:
                    quota_type = qt
                    break

            if not quota_type:
                return None

            return QuotaLimit(
                quota_type=quota_type,
                limit=int(quota_dict.get("limit", 0)),
                enabled=quota_dict.get("enabled", True),
                provider_id=quota_dict.get("provider_id"),
                model_id=quota_dict.get("model_id"),
                description=quota_dict.get("description", "")
            )
        except (ValueError, KeyError, TypeError):
            return None

    def _get_quota_key(self, quota_limit: QuotaLimit) -> str:
        """Generate a unique key for a quota limit."""
        provider_part = quota_limit.provider_id or "*"
        model_part = quota_limit.model_id or "*"
        return f"{provider_part}:{model_part}:{quota_limit.quota_type.value}"

    def add_quota_limit(self, quota_limit: QuotaLimit) -> None:
        """
        Add or update a quota limit.

        Args:
            quota_limit: The quota limit to add/update
        """
        if not quota_limit.enabled:
            # Remove if exists
            key = self._get_quota_key(quota_limit)
            self._quota_limits.pop(key, None)
            return

        key = self._get_quota_key(quota_limit)
        self._quota_limits[key] = quota_limit

    def remove_quota_limit(self, quota_type: QuotaType,
                          provider_id: Optional[str] = None,
                          model_id: Optional[str] = None) -> bool:
        """
        Remove a quota limit.

        Args:
            quota_type: Type of quota to remove
            provider_id: Provider ID (None for all providers)
            model_id: Model ID (None for all models)

        Returns:
            True if a quota limit was removed, False otherwise
        """
        key = f"{provider_id or '*'}:{model_id or '*'}:{quota_type.value}"
        if key in self._quota_limits:
            del self._quota_limits[key]
            return True
        return False

    def get_quota_limit(self, quota_type: QuotaType,
                       provider_id: Optional[str] = None,
                       model_id: Optional[str] = None) -> Optional[QuotaLimit]:
        """
        Get the quota limit for a specific provider/model/quota_type combination.
        Returns the most specific match (provider/model > provider/* > */* etc).
        """
        # Check in order of specificity: exact match, provider wildcard, model wildcard, both wildcards
        keys_to_check = [
            f"{provider_id or '*'}:{model_id or '*'}:{quota_type.value}",  # Exact or wildcards
            f"{provider_id or '*'}:{model_id or '*'}:{quota_type.value}",  # This handles the logic below
        ]

        # Build list of possible keys in order of preference
        provider_part = provider_id or "*"
        model_part = model_id or "*"

        candidates = [
            f"{provider_part}:{model_part}:{quota_type.value}",           # Specific provider/model
            f"{provider_part}*:{quota_type.value}",                     # Provider-specific, any model
            f"*:{model_part}:{quota_type.value}",                       # Model-specific, any provider
            f"*:*:{quota_type.value}",                                  # Any provider, any model (default)
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique_candidates.append(candidate)

        # Check each candidate in order
        for key in unique_candidates:
            if key in self._quota_limits:
                quota_limit = self._quota_limits[key]
                if quota_limit.enabled:
                    return quota_limit

        return None

    def _get_current_window_start(self, quota_type: QuotaType) -> datetime:
        """Get the start of the current time window for a quota type."""
        now = datetime.now(timezone.utc)

        if quota_type in [QuotaType.REQUESTS_PER_MINUTE, QuotaType.TOKENS_PER_MINUTE]:
            # Minute window: start at the beginning of the current minute
            return now.replace(second=0, microsecond=0)
        elif quota_type in [QuotaType.REQUESTS_PER_DAY, QuotaType.TOKENS_PER_DAY]:
            # Day window: start at the beginning of the current day (UTC)
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # For concurrent requests, we don't use time windows
            return now

    def _is_in_window(self, timestamp: datetime, window_start: datetime,
                     quota_type: QuotaType) -> bool:
        """Check if a timestamp falls within the current window."""
        if quota_type in [QuotaType.REQUESTS_PER_MINUTE, QuotaType.TOKENS_PER_MINUTE]:
            # Minute window: check if within same minute
            return (timestamp >= window_start and
                   timestamp < window_start + timedelta(minutes=1))
        elif quota_type in [QuotaType.REQUESTS_PER_DAY, QuotaType.TOKENS_PER_DAY]:
            # Day window: check if within same day
            return (timestamp >= window_start and
                   timestamp < window_start + timedelta(days=1))
        else:
            # For concurrent requests, always return True (no time window)
            return True

    def _get_usage_key(self, quota_type: QuotaType, provider_id: str, model_id: str) -> str:
        """Generate a key for usage tracking."""
        return f"{provider_id}:{model_id}:{quota_type.value}"

    def _update_usage_from_records(self, quota_type: QuotaType,
                                 provider_id: str, model_id: str) -> int:
        """
        Update current usage based on timestamped usage records.

        Returns:
            The current usage count for the quota type
        """
        # Get the window start time
        window_start = self._get_current_window_start(quota_type)

        # Get usage records from the model router (lazy initialization to avoid circular import)
        model_router = self._get_model_router()
        usage_records = model_router.get_usage_in_time_window(
            model_id=model_id,
            start_time=window_start
        )

        # Filter records for this provider/model combination
        relevant_records = [
            record for record in usage_records
            if record.provider_id == provider_id and record.model_id == model_id
        ]

        # Calculate usage based on quota type
        if quota_type == QuotaType.REQUESTS_PER_MINUTE or quota_type == QuotaType.REQUESTS_PER_DAY:
            # Count requests
            total_usage = sum(record.request_count for record in relevant_records)
        elif quota_type == QuotaType.TOKENS_PER_MINUTE or quota_type == QuotaType.TOKENS_PER_DAY:
            # Count tokens
            total_usage = sum(record.total_tokens for record in relevant_records)
        else:
            # For concurrent requests, we track separately
            total_usage = 0

        return total_usage

    def _cleanup_expired_usage(self) -> None:
        """Clean up expired usage tracking entries to prevent memory leaks."""
        with self._usage_lock:
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(hours=25)  # Keep slightly more than 24h for safety

            keys_to_remove = []
            for key, usage in self._usage_tracking.items():
                if usage.window_start < cutoff_time:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._usage_tracking[key]

    def _get_or_create_usage_tracking(self, quota_type: QuotaType,
                                    provider_id: str, model_id: str) -> QuotaUsage:
        """Get existing usage tracking or create new entry."""
        with self._usage_lock:
            # Cleanup old entries periodically
            if len(self._usage_tracking) > 1000:
                self._cleanup_expired_usage()

            key = self._get_usage_key(quota_type, provider_id, model_id)
            usage = self._usage_tracking.get(key)

            if usage is None:
                # Create new usage tracking
                window_start = self._get_current_window_start(quota_type)
                usage = QuotaUsage(
                    quota_type=quota_type,
                    provider_id=provider_id,
                    model_id=model_id,
                    window_start=window_start
                )
                self._usage_tracking[key] = usage
            elif not self._is_in_window(datetime.now(timezone.utc), usage.window_start, quota_type):
                # Window has expired, reset usage
                usage.window_start = self._get_current_window_start(quota_type)
                usage.current_usage = 0

            return usage

    def _check_quota(self, quota_type: QuotaType, provider_id: str, model_id: str,
                    requested_amount: int = 1) -> Tuple[bool, Optional[ProviderFailure]]:
        """
        Check if a request would exceed a quota.

        Args:
            quota_type: Type of quota to check
            provider_id: Provider identifier
            model_id: Model identifier
            requested_amount: Amount being requested (for tokens, this would be token count)

        Returns:
            Tuple of (allowed, failure) where allowed is True if request is allowed,
            and failure is a ProviderFailure if the request would be denied
        """
        if not self._enabled:
            return True, None

        # Get the quota limit for this provider/model combination
        quota_limit = self.get_quota_limit(quota_type, provider_id, model_id)
        if not quota_limit or not quota_limit.enabled:
            return True, None  # No limit configured = allowed

        # Get current usage
        usage = self._get_or_create_usage_tracking(quota_type, provider_id, model_id)

        # Update usage from timestamped records for request/token based quotas
        if quota_type in [
            QuotaType.REQUESTS_PER_MINUTE, QuotaType.REQUESTS_PER_DAY,
            QuotaType.TOKENS_PER_MINUTE, QuotaType.TOKENS_PER_DAY
        ]:
            usage.current_usage = self._update_usage_from_records(quota_type, provider_id, model_id)

        # Check if adding the requested amount would exceed the limit
        new_usage = usage.current_usage + requested_amount
        if new_usage > quota_limit.limit:
            # Quota exceeded - create appropriate failure
            if quota_type == QuotaType.REQUESTS_PER_MINUTE or quota_type == QuotaType.TOKENS_PER_MINUTE:
                failure_category = FailureCategory.RATE_LIMIT
                safe_message = f"{quota_limit.limit} {quota_type.value.replace('_', ' ')} exceeded"
            elif quota_type == QuotaType.REQUESTS_PER_DAY or quota_type == QuotaType.TOKENS_PER_DAY:
                failure_category = FailureCategory.QUOTA_EXCEEDED
                safe_message = f"{quota_limit.limit} {quota_type.value.replace('_', ' ')} exceeded"
            else:
                failure_category = FailureCategory.QUOTA_EXCEEDED
                safe_message = f"Quota exceeded: {quota_limit.description}"

            # Calculate reset time for retry-after header
            reset_time = self._get_reset_time(quota_type, usage.window_start)
            retry_after = int(max(0, (reset_time - datetime.now(timezone.utc)).total_seconds()))

            failure = classify_failure(
                category=failure_category,
                provider_id=provider_id,
                model_id=model_id,
                retry_after=retry_after,
                safe_message=safe_message
            )

            # Override retryable based on quota type
            # REQUESTS_PER_MINUTE and TOKENS_PER_MINUTE are retryable (they reset)
            # REQUESTS_PER_DAY and TOKENS_PER_DAY are not retryable until next day
            if quota_type in [QuotaType.REQUESTS_PER_DAY, QuotaType.TOKENS_PER_DAY]:
                failure.retryable = False
            else:
                failure.retryable = True

            return False, failure

        return True, None

    def _get_reset_time(self, quota_type: QuotaType, window_start: datetime) -> datetime:
        """Get the time when the quota will reset."""
        if quota_type in [QuotaType.REQUESTS_PER_MINUTE, QuotaType.TOKENS_PER_MINUTE]:
            return window_start + timedelta(minutes=1)
        elif quota_type in [QuotaType.REQUESTS_PER_DAY, QuotaType.TOKENS_PER_DAY]:
            return window_start + timedelta(days=1)
        else:
            # For concurrent requests, reset when leases are released
            return window_start

    def acquire_lease(self, provider_id: str, model_id: str) -> Optional[Lease]:
        """
        Acquire a lease for concurrent request limiting.

        Args:
            provider_id: Provider identifier
            model_id: Model identifier

        Returns:
            Lease object if acquired, None if limit exceeded
        """
        if not self._enabled:
            # Still create a lease for tracking even when disabled
            lease_id = f"lease-{self._next_lease_id}"
            self._next_lease_id += 1
            lease = Lease(
                lease_id=lease_id,
                provider_id=provider_id,
                model_id=model_id
            )
            with self._lease_lock:
                self._active_leases[lease_id] = lease
            return lease

        # Check concurrent request limit
        quota_limit = self.get_quota_limit(QuotaType.CONCURRENT_REQUESTS, provider_id, model_id)
        if not quota_limit or not quota_limit.enabled:
            # No limit configured = allow unlimited concurrent requests
            lease_id = f"lease-{self._next_lease_id}"
            self._next_lease_id += 1
            lease = Lease(
                lease_id=lease_id,
                provider_id=provider_id,
                model_id=model_id
            )
            with self._lease_lock:
                self._active_leases[lease_id] = lease
            return lease

        # Count current active leases for this provider/model
        with self._lease_lock:
            current_count = sum(
                1 for lease in self._active_leases.values()
                if lease.provider_id == provider_id and lease.model_id == model_id
            )

            if current_count >= quota_limit.limit:
                # Limit exceeded
                return None

            # Acquire the lease
            lease_id = f"lease-{self._next_lease_id}"
            self._next_lease_id += 1
            lease = Lease(
                lease_id=lease_id,
                provider_id=provider_id,
                model_id=model_id
            )
            self._active_leases[lease_id] = lease
            return lease

    def release_lease(self, lease: Lease) -> bool:
        """
        Release a previously acquired lease.

        Args:
            lease: The lease to release

        Returns:
            True if lease was released, False if not found
        """
        with self._lease_lock:
            if lease.lease_id in self._active_leases:
                del self._active_leases[lease.lease_id]
                return True
        return False

    async def check_and_admit(self, request: Any) -> Tuple[bool, Optional[ProviderFailure]]:
        """
        Check if a request should be admitted based on rate limits and quotas.
        This is the main entry point for pre-routing enforcement.

        Args:
            request: ModelRequest object containing provider/model information

        Returns:
            Tuple of (admitted, failure) where admitted is True if request should proceed,
            and failure is a ProviderFailure if request should be denied
        """
        if not self._enabled:
            return True, None

        # Extract provider and model information from request
        # This assumes the request has been routed to a specific model/provider
        # In practice, this would be called after ModelRouter.route() but before ModelRouter._call_model()

        # For now, we'll need to get this information from the ModelRouter's routing decision
        # Since we don't have direct access to the routing result here, we'll implement
        # this to be called from within the ModelRouter flow

        # Placeholder implementation - this will be integrated into ModelRouter
        return True, None

    def admit_request(self, provider_id: str, model_id: str,
                     estimated_tokens: int = 0) -> Tuple[Optional[Lease], Optional[ProviderFailure]]:
        """
        Admit a request by checking quotas and acquiring necessary leases.

        Args:
            provider_id: Provider identifier
            model_id: Model identifier
            estimated_tokens: Estimated token count for token-based quotas

        Returns:
            Tuple of (lease, failure) where lease is the acquired lease (if concurrent limiting enabled),
            and failure is a ProviderFailure if request should be denied
        """
        if not self._enabled:
            # Still acquire lease for tracking even when disabled
            lease = self.acquire_lease(provider_id, model_id)
            return lease, None

        # Check all applicable quotas
        quotas_to_check = [
            QuotaType.REQUESTS_PER_MINUTE,
            QuotaType.REQUESTS_PER_DAY,
            QuotaType.TOKENS_PER_MINUTE,
            QuotaType.TOKENS_PER_DAY,
        ]

        # For token-based quotas, use estimated tokens
        token_request_amount = max(1, estimated_tokens)  # At least 1 for non-token quotas

        for quota_type in quotas_to_check:
            # Determine request amount based on quota type
            if quota_type in [QuotaType.TOKENS_PER_MINUTE, QuotaType.TOKENS_PER_DAY]:
                request_amount = token_request_amount
            else:
                request_amount = 1  # One request

            allowed, failure = self._check_quota(quota_type, provider_id, model_id, request_amount)
            if not allowed:
                return None, failure

        # If all quotas passed, acquire concurrent request lease if needed
        lease = None
        concurrent_quota = self.get_quota_limit(QuotaType.CONCURRENT_REQUESTS, provider_id, model_id)
        if concurrent_quota and concurrent_quota.enabled:
            lease = self.acquire_lease(provider_id, model_id)
            if lease is None:
                # Concurrent limit exceeded
                failure = classify_failure(
                    category=FailureCategory.QUOTA_EXCEEDED,
                    provider_id=provider_id,
                    model_id=model_id,
                    safe_message=f"Concurrent request limit exceeded: {concurrent_quota.limit}"
                )
                failure.retryable = True  # Concurrent limits are typically retryable
                return None, failure

        return lease, None

    def record_completion(self, lease: Optional[Lease], provider_id: str, model_id: str,
                         success: bool, actual_tokens: int = 0) -> None:
        """
        Record the completion of a request and release associated resources.

        Args:
            lease: The lease acquired during admission (if any)
            provider_id: Provider identifier
            model_id: Model identifier
            success: Whether the request was successful
            actual_tokens: Actual token count used
        """
        # Release the lease if we have one
        if lease:
            self.release_lease(lease)

        # Note: Actual usage recording is handled by the ModelRouter's existing
        # timestamped usage accounting - we don't duplicate that here
        # Our quota checking uses the existing get_usage_in_time_window() method

    def get_quota_status(self, provider_id: str, model_id: str) -> Dict[str, Any]:
        """
        Get current quota usage status for monitoring/observability.

        Args:
            provider_id: Provider identifier
            model_id: Model identifier

        Returns:
            Dictionary with quota usage information
        """
        status = {
            "provider_id": provider_id,
            "model_id": model_id,
            "quotas": {},
            "active_leases": 0
        }

        # Get usage for each quota type
        quota_types = [
            QuotaType.REQUESTS_PER_MINUTE,
            QuotaType.REQUESTS_PER_DAY,
            QuotaType.TOKENS_PER_MINUTE,
            QuotaType.TOKENS_PER_DAY,
            QuotaType.CONCURRENT_REQUESTS
        ]

        for quota_type in quota_types:
            quota_limit = self.get_quota_limit(quota_type, provider_id, model_id)
            usage = self._get_or_create_usage_tracking(quota_type, provider_id, model_id)

            # Update usage from records for request/token based quotas
            if quota_type in [
                QuotaType.REQUESTS_PER_MINUTE, QuotaType.REQUESTS_PER_DAY,
                QuotaType.TOKENS_PER_MINUTE, QuotaType.TOKENS_PER_DAY
            ]:
                usage.current_usage = self._update_usage_from_records(quota_type, provider_id, model_id)

            status["quotas"][quota_type.value] = {
                "limit": quota_limit.limit if quota_limit else 0,
                "current_usage": usage.current_usage,
                "available": max(0, (quota_limit.limit - usage.current_usage) if quota_limit else 0),
                "unit": "requests" if "request" in quota_type.value else "tokens",
                "window_start": usage.window_start.isoformat(),
                "enabled": quota_limit.enabled if quota_limit else False
            }

        # Count active leases
        with self._lease_lock:
            status["active_leases"] = sum(
                1 for lease in self._active_leases.values()
                if lease.provider_id == provider_id and lease.model_id == model_id
            )

        return status

    def get_stats(self) -> Dict[str, Any]:
        """Get overall manager statistics."""
        with self._usage_lock:
            with self._lease_lock:
                return {
                    "enabled": self._enabled,
                    "quota_limits_configured": len(self._quota_limits),
                    "usage_tracking_entries": len(self._usage_tracking),
                    "active_leases": len(self._active_leases),
                    "configuration_source": "ConfigurationManager"
                }


# Global rate limit quota manager instance
_global_rate_limit_quota_manager: RateLimitQuotaManager | None = None
_rate_limit_singleton_lock = threading.Lock()


def get_rate_limit_quota_manager(
    config: Optional[Dict[str, Any]] = None,
    resource_manager: Optional[ResourceManager] = None,
    model_router: Any = None,
) -> RateLimitQuotaManager:
    """
    Get or create the global RateLimitQuotaManager singleton.

    Uses the same lock-guarded pattern as other Core Component singletons.
    """
    global _global_rate_limit_quota_manager
    with _rate_limit_singleton_lock:
        if _global_rate_limit_quota_manager is None:
            _global_rate_limit_quota_manager = RateLimitQuotaManager(
                config=config,
                resource_manager=resource_manager,
                model_router=model_router,
            )
        return _global_rate_limit_quota_manager


def set_rate_limit_quota_manager(manager: RateLimitQuotaManager) -> None:
    """Set the global RateLimitQuotaManager singleton (kernel-owned construction)."""
    global _global_rate_limit_quota_manager
    with _rate_limit_singleton_lock:
        _global_rate_limit_quota_manager = manager


def reset_rate_limit_quota_manager_singleton() -> None:
    """Reset the process-wide RateLimitQuotaManager singleton (tests only)."""
    global _global_rate_limit_quota_manager
    with _rate_limit_singleton_lock:
        _global_rate_limit_quota_manager = None


__all__ = [
    "RateLimitQuotaManager",
    "QuotaType",
    "QuotaLimit",
    "QuotaUsage",
    "Lease",
    "get_rate_limit_quota_manager",
    "set_rate_limit_quota_manager",
    "reset_rate_limit_quota_manager_singleton",
]