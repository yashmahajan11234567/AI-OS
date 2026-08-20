"""
Retry Manager for AI-OS Hermes Kernel.

Manages retry budgets and policies for services to prevent infinite retry loops.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.subscription import HandlerPriority, RetryPolicy as CoreRetryPolicy
import uuid

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategy types."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 60000
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    non_retryable_exceptions: tuple[type[Exception], ...] = ()


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""

    attempt: int
    task_id: str
    service: str
    error: str
    error_type: str
    delay_ms: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    succeeded: bool = False


@dataclass
class RetryBudget:
    """Tracks remaining retries for a task."""

    task_id: str
    service: str
    policy: RetryPolicy
    attempts: list[RetryAttempt] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        """Number of retries remaining."""
        return max(0, self.policy.max_retries - len(self.attempts))

    @property
    def exhausted(self) -> bool:
        """True if no retries remain."""
        return len(self.attempts) >= self.policy.max_retries

    def record_attempt(self, error: Exception, error_type: str) -> RetryAttempt:
        attempt_num = len(self.attempts) + 1
        delay = self._calculate_delay(attempt_num)

        attempt = RetryAttempt(
            attempt=attempt_num,
            task_id=self.task_id,
            service=self.service,
            error=str(error),
            error_type=error_type,
            delay_ms=delay,
        )
        self.attempts.append(attempt)
        return attempt

    def _calculate_delay(self, attempt: int) -> int:
        policy = self.policy
        if policy.strategy == RetryStrategy.FIXED:
            delay = policy.base_delay_ms
        elif policy.strategy == RetryStrategy.LINEAR:
            delay = policy.base_delay_ms * attempt
        elif policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = policy.base_delay_ms * (2 ** (attempt - 1))
        elif policy.strategy == RetryStrategy.FIBONACCI:
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            delay = policy.base_delay_ms * a
        else:
            delay = policy.base_delay_ms

        delay = min(delay, policy.max_delay_ms)
        if policy.jitter:
            import random
            delay = int(delay * (0.5 + random.random()))

        return delay


class RetryManager:
    """
    Manages retry budgets and executes retries for services.

    Features:
    - Per-task retry budgets
    - Configurable retry policies per service
    - Automatic retry scheduling
    - Integration with Root Cause Analyzer on budget exhaustion
    """

    def __init__(self):
        # Use canonical EventBus singleton (C1, Task 5)
        self._event_bus = get_core_event_bus()
        self._policies: dict[str, RetryPolicy] = {}
        self._budgets: dict[str, RetryBudget] = {}
        self._default_policy = RetryPolicy()
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="RetryManager",
            version=SemanticVersion.parse("0.1.0"),
        )

    def _ensure_bus(self):
        """Ensure EventBus is available."""
        if self._event_bus is None:
            self._event_bus = get_core_event_bus()
            # Don't raise error if EventBus not initialized yet - allow deferred initialization
            if self._event_bus is None:
                logger.debug("Canonical EventBus not yet initialized; event emission will be deferred")
        return self._event_bus

    def set_policy(self, service: str, policy: RetryPolicy) -> None:
        """Set retry policy for a service."""
        self._policies[service] = policy
        logger.info(f"Set retry policy for {service}: {policy}")

    def get_policy(self, service: str) -> RetryPolicy:
        """Get retry policy for a service."""
        return self._policies.get(service, self._default_policy)

    def create_budget(self, task_id: str, service: str, policy: RetryPolicy | None = None) -> RetryBudget:
        """Create a retry budget for a task."""
        policy = policy or self.get_policy(service)
        budget = RetryBudget(task_id=task_id, service=service, policy=policy)
        key = f"{task_id}:{service}"
        self._budgets[key] = budget
        return budget

    def get_budget(self, task_id: str, service: str) -> RetryBudget | None:
        """Get retry budget for a task."""
        key = f"{task_id}:{service}"
        return self._budgets.get(key)

    def retry_budget_exhausted(self, task_id: str, service: str, budget: RetryBudget, correlation_id: str) -> None:
        """Handle retry budget exhaustion."""
        key = f"{task_id}:{service}"
        if key in self._budgets:
            del self._budgets[key]
        logger.warning(f"Retry budget exhausted for task {task_id}: {budget}")
        # Publish canonical event
        self._emit_event(
            EventType.RETRY_BUDGET_EXHAUSTED,
            {
                "task_id": task_id,
                "service": service,
                "max_retries": budget.policy.max_retries,
                "attempts": len(budget.attempts),
            },
            correlation_id=correlation_id,
        )

    async def execute_with_retry(
        self,
        task_id: str,
        service: str,
        func: Callable[..., Any],
        policy: RetryPolicy | None = None,
        correlation_id: str | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            task_id: Unique task identifier
            service: Service name for policy lookup
            func: Async function to execute
            policy: Optional override policy
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of the function call

        Raises:
            The last exception if all retries exhausted
        """
        policy = policy or self.get_policy(service)
        budget = self.create_budget(task_id, service, policy)

        last_exception: Exception | None = None

        # Initial attempt + retries = max_retries + 1 total attempts
        for attempt_num in range(policy.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                # Success - mark the last attempt as succeeded if there were retries
                if budget.attempts:
                    budget.attempts[-1].succeeded = True
                return result
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # Check if exception is retryable
                if isinstance(e, policy.non_retryable_exceptions):
                    logger.info(f"Non-retryable exception {error_type} for task {task_id}")
                    raise

                if not isinstance(e, policy.retryable_exceptions):
                    logger.info(f"Exception {error_type} not in retryable list for task {task_id}")
                    raise

                # Record the attempt
                if attempt_num < policy.max_retries:
                    attempt = budget.record_attempt(e, error_type)

                    # Publish retry scheduled event
                    self._emit_event(
                        EventType.RETRY_SCHEDULED,
                        {
                            "task_id": task_id,
                            "service": service,
                            "retry_count": attempt.attempt,
                            "delay_ms": attempt.delay_ms,
                        },
                        correlation_id=correlation_id,
                    )

                    # Wait before retry
                    await asyncio.sleep(attempt.delay_ms / 1000.0)

                    # Publish retry executed event
                    self._emit_event(
                        EventType.RETRY_EXECUTED,
                        {
                            "task_id": task_id,
                            "service": service,
                            "retry_count": attempt.attempt,
                        },
                        correlation_id=task_id,
                    )
                else:
                    # Max retries reached
                    break

        # All retries exhausted
        self.retry_budget_exhausted(task_id, service, budget, correlation_id)

        # Publish task failed event
        self._emit_event(
            EventType.TASK_FAILED,
            {
                "task_id": task_id,
                "service": service,
                "error": str(last_exception),
                "error_type": type(last_exception).__name__,
                "retryable": True,
                "retry_count": policy.max_retries,
            },
            correlation_id=task_id,
        )

        raise last_exception

    def _emit_event(self, event_type: EventType, payload: dict[str, Any], correlation_id: str) -> None:
        """Emit a canonical event via the canonical EventBus."""
        bus = self._ensure_bus()
        if bus is None:
            # EventBus not available, skip event emission
            logger.debug("EventBus not available, skipping event emission")
            return
        import uuid as uuid_mod
        # Handle invalid UUID strings by generating a new one
        try:
            correlation_uuid = uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4()
        except ValueError:
            logger.warning(f"Invalid UUID string for correlation_id: {correlation_id!r}. Generating a new UUID.")
            correlation_uuid = uuid_mod.uuid4()

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
        )
        result = bus.publish(event)
        # Fire and forget - result handling is async
        if hasattr(result, "__await__"):
            # Schedule on the event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass


# Global retry manager instance
_global_retry_manager: RetryManager | None = None


def get_retry_manager() -> RetryManager:
    """Get or create the global retry manager."""
    global _global_retry_manager
    if _global_retry_manager is None:
        _global_retry_manager = RetryManager()
    return _global_retry_manager


def set_retry_manager(manager: RetryManager) -> None:
    """Set the global retry manager."""
    global _global_retry_manager
    _global_retry_manager = manager


__all__ = [
    "RetryManager",
    "RetryPolicy",
    "RetryStrategy",
    "RetryBudget",
    "RetryAttempt",
    "get_retry_manager",
    "set_retry_manager",
]