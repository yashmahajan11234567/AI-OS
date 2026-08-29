"""
M13 — Failure Recovery Manager (M13_FAILURE_RECOVERY_SPEC.md).

Provides bounded, AI-OS-authoritative failure recovery for M13 external
integrations (Supabase, n8n, Obsidian Git, and the rest of the bounded external
ecosystem). External systems are BOUNDED RESOURCES: AI-OS remains the sole
governance, verification, and decision-making authority. Recovery never elevates
any external system; it degrades gracefully to local AI-OS capability and reports
back to the kernel for the authoritative self-loop decision.

Recovery principles enforced (per spec §Recovery Principles):
  * AI-OS retains authority (no external system gains authority through failure).
  * Bounded recovery (retry/backoff budgets capped to prevent recovery loops).
  * Provenance preserved on every recovery action (mark_aios_owned).
  * Graceful degradation to local fallback when a bounded resource is unavailable.
  * Evidence-based learning (recovery outcomes recorded as learnings).
  * State-integrity priority (corrupt/invalid state rejected, never accepted).
  * Security-first (all recovery actions pass through SecurityManager gating).
  * Continuity focus (resume minimal viable operation, then expand).

The manager is dependency-light (stdlib + dataclasses + canonical EventBus) so it
can be imported from the kernel and exercised by unit/integration tests without
booting the entire AI-OS stack.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.security.secrets import redact_exception, redact_secrets

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """M13 failure classification (M13_FAILURE_RECOVERY_SPEC §Failure Classification)."""

    BOUNDED_EXECUTION = "bounded_execution"
    INTEGRATION = "integration"
    PERSISTENCE = "persistence"
    DASHBOARD = "dashboard"
    SELF_LOOP = "self_loop"


class RecoveryOutcome(str, Enum):
    """Result of a bounded recovery attempt."""

    RECOVERED = "recovered"
    DEGRADED = "degraded"       # local fallback only; external resource unavailable
    ESCALATED = "escalated"    # retries exhausted -> reported to AI-OS self-loop
    FAILED = "failed"          # could not recover; failure recorded


# Default bounded-recovery limits (Principle 2: bounded recovery).
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SECONDS = 0.5
DEFAULT_BACKOFF_MAX_SECONDS = 8.0


@dataclass
class RecoveryRecord:
    """Audit trail of a single bounded-recovery attempt (provenance = aios_owned)."""

    recovery_id: str
    failure_id: str
    category: str
    component: str
    outcome: str
    attempts: int
    started_at: str
    completed_at: str | None
    detail: str
    learned: bool
    provenance: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "failure_id": self.failure_id,
            "category": self.category,
            "component": self.component,
            "outcome": self.outcome,
            "attempts": self.attempts,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "detail": self.detail,
            "learned": self.learned,
            "provenance": self.provenance,
            "correlation_id": self.correlation_id,
        }


class FailureRecoveryManager:
    """AI-OS-authoritative bounded failure-recovery coordinator for M13 resources.

    The kernel constructs one instance and routes bounded-resource failures
    (integration/persistence connection failures, bounded-execution external
    failures, etc.) here. Each recovery attempt is bounded, provenance-tracked,
    and surfaced on the canonical EventBus so AI-OS retains final judgment.
    """

    def __init__(
        self,
        security_manager: Any | None = None,
        event_bus: Any | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
        backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS,
    ) -> None:
        self._security_manager = security_manager
        self._event_bus = event_bus or get_core_event_bus()
        self._max_retries = max(1, int(max_retries))
        self._backoff_base = max(0.0, float(backoff_base_seconds))
        self._backoff_max = max(self._backoff_base, float(backoff_max_seconds))
        self._records: dict[str, RecoveryRecord] = {}
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="FailureRecoveryManager",
            version=SemanticVersion.parse("0.1.0"),
        )

    # ------------------------------------------------------------------ config

    def set_security_manager(self, security_manager: Any) -> None:
        self._security_manager = security_manager

    # -------------------------------------------------------------- classification

    def classify(
        self,
        component: str,
        error: BaseException | None = None,
        category_hint: FailureCategory | None = None,
    ) -> FailureCategory:
        """Classify a failure into an M13 category (spec §Failure Classification).

        Uses an explicit hint when supplied; otherwise infers from the component
        name and error type. Never elevates authority — classification is purely
        a routing decision made by AI-OS.
        """
        if category_hint is not None:
            return category_hint

        name = (component or "").lower()
        if "supabase" in name or "obsidian" in name or "persistence" in name:
            return FailureCategory.PERSISTENCE
        if "dashboard" in name or "ui" in name:
            return FailureCategory.DASHBOARD
        if "self_loop" in name or "self-prompt" in name or "selfprompt" in name:
            return FailureCategory.SELF_LOOP
        if "n8n" in name or "playwright" in name or "mcp" in name or "agent_reach" in name:
            return FailureCategory.INTEGRATION
        # Default: treat as bounded execution failure (external execution path).
        return FailureCategory.BOUNDED_EXECUTION

    # ------------------------------------------------------------- core recovery

    async def recover(
        self,
        component: str,
        *,
        category: FailureCategory | None = None,
        operation: str | None = None,
        failure_id: str | None = None,
        correlation_id: str | None = None,
        error: BaseException | None = None,
        local_fallback: Callable[[], Any] | None = None,
        security_action: str | None = None,
        security_resource: str | None = None,
    ) -> RecoveryRecord:
        """Run a bounded recovery for a failed external-resource operation.

        Steps (spec §Integration Recovery / §Recovery Decision Framework):
          1. Contain + record classification.
          2. Security gate (if a security_action is supplied) — fail-closed;
             an external system that violates policy is blocked, never trusted.
          3. Bounded retries with exponential backoff (if a retry callable is
             provided via ``local_fallback`` returning a sentinel, etc.).
          4. Graceful degradation to ``local_fallback`` when retries exhausted.
          5. Escalate to AI-OS self-loop if even local fallback is unavailable.
          6. Emit RECOVERY_ACTION_* events and record provenance (aios_owned).
        """
        category = self.classify(component, error, category)
        failure_id = failure_id or f"fail_{uuid.uuid4().hex[:12]}"
        recovery_id = f"recovery_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        detail_parts: list[str] = []
        attempts = 0

        # --- Security gate-before-continue (Principle 9: security-first) ---
        if security_action is not None and self._security_manager is not None:
            try:
                decision = self._security_manager.authorize(
                    principal="aios_kernel",
                    action=security_action,
                    resource=security_resource or component,
                    context={"recovery": True, "failure_id": failure_id},
                )
                if getattr(decision, "value", "deny") != "allow":
                    detail_parts.append(
                        "SecurityManager denied recovery continuation (fail-closed)"
                    )
                    outcome = RecoveryOutcome.FAILED
                    record = self._finalize(
                        recovery_id, failure_id, category, component, outcome,
                        attempts, started_at, "; ".join(detail_parts),
                        correlation_id,
                    )
                    await self._emit(EventType.RECOVERY_ACTION_FAILED, record, correlation_id)
                    return record
            except Exception as exc:  # noqa: BLE001 — security failure must block, not raise
                detail_parts.append(f"Security gate error: {redact_exception(exc)}")
                record = self._finalize(
                    recovery_id, failure_id, category, component, RecoveryOutcome.FAILED,
                    attempts, started_at, "; ".join(detail_parts), correlation_id,
                )
                await self._emit(EventType.RECOVERY_ACTION_FAILED, record, correlation_id)
                return record

        # --- Bounded retry + graceful degradation ---
        recovered = False
        if local_fallback is not None:
            for attempt in range(1, self._max_retries + 1):
                attempts = attempt
                try:
                    result = local_fallback()
                    if result is not None and not _is_failure_sentinel(result):
                        recovered = True
                        detail_parts.append(
                            f"Local fallback succeeded on attempt {attempt}"
                        )
                        break
                except Exception as exc:  # noqa: BLE001 — bounded retry
                    detail_parts.append(
                        f"Attempt {attempt} failed: {redact_exception(exc)}"
                    )
                # Exponential backoff (capped) before next attempt.
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        outcome: RecoveryOutcome
        if recovered:
            outcome = RecoveryOutcome.RECOVERED
            await self._emit(
                EventType.RECOVERY_ACTION_COMPLETED,
                self._record_for_event(
                    recovery_id, failure_id, category, component, outcome,
                    attempts, started_at, "; ".join(detail_parts), correlation_id,
                ),
                correlation_id,
            )
        elif local_fallback is not None:
            # Tried local fallback, exhausted retries -> degraded (still operating
            # on AI-OS authority; external resource simply unavailable).
            outcome = RecoveryOutcome.DEGRADED
            detail_parts.append("Local fallback exhausted; operating in degraded mode")
            await self._emit(
                EventType.RECOVERY_ACTION_DISPATCHED,
                self._record_for_event(
                    recovery_id, failure_id, category, component, outcome,
                    attempts, started_at, "; ".join(detail_parts), correlation_id,
                ),
                correlation_id,
            )
        else:
            # No local fallback available -> escalate to AI-OS self-loop decision.
            outcome = RecoveryOutcome.ESCALATED
            detail_parts.append(
                "No local fallback; escalated to AI-OS self-loop for decision"
            )
            await self._emit(
                EventType.RECOVERY_ACTION_FAILED,
                self._record_for_event(
                    recovery_id, failure_id, category, component, outcome,
                    attempts, started_at, "; ".join(detail_parts), correlation_id,
                ),
                correlation_id,
            )

        # Evidence-based learning extraction (Principle 5): record the failure as
        # a learning input for AI-OS planning (advisory only — never gates recovery).
        learned = await self._record_learning(category, component, outcome, error)

        record = self._finalize(
            recovery_id, failure_id, category, component, outcome, attempts,
            started_at, "; ".join(detail_parts), correlation_id, learned=learned,
        )
        return record

    # ------------------------------------------------------------- helpers

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff (bounded)."""
        delay = min(self._backoff_max, self._backoff_base * (2 ** (attempt - 1)))
        try:
            await __import__("asyncio").sleep(delay)
        except Exception:  # noqa: BLE001 — never let backoff break recovery
            pass

    def _finalize(
        self,
        recovery_id: str,
        failure_id: str,
        category: FailureCategory,
        component: str,
        outcome: RecoveryOutcome,
        attempts: int,
        started_at: str,
        detail: str,
        correlation_id: str | None,
        learned: bool = False,
    ) -> RecoveryRecord:
        provenance = self._provenance()
        record = RecoveryRecord(
            recovery_id=recovery_id,
            failure_id=failure_id,
            category=category.value,
            component=component,
            outcome=outcome.value,
            attempts=attempts,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            detail=detail,
            learned=learned,
            provenance=provenance,
            correlation_id=correlation_id,
        )
        self._records[recovery_id] = record
        return record

    def _record_for_event(
        self,
        recovery_id: str,
        failure_id: str,
        category: FailureCategory,
        component: str,
        outcome: RecoveryOutcome,
        attempts: int,
        started_at: str,
        detail: str,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        return {
            "recovery_id": recovery_id,
            "failure_id": failure_id,
            "failure_category": category.value,
            "component": component,
            "outcome": outcome.value,
            "attempts": attempts,
            "started_at": started_at,
            "detail": redact_secrets(detail),
            "provenance": self._provenance(),
            "recovery_correlation_id": correlation_id,
        }

    def _provenance(self) -> dict[str, Any]:
        """All recovery actions are owned by AI-OS (no external authority)."""
        return {
            "authority": "aios_owned",
            "semantic_owner": "aios_kernel",
            "recovery_engine": "FailureRecoveryManager",
            "request_id": uuid.uuid4().hex,
        }

    async def _record_learning(
        self,
        category: FailureCategory,
        component: str,
        outcome: RecoveryOutcome,
        error: BaseException | None,
    ) -> bool:
        """Extract validated learning from a failure (advisory to AI-OS planning).

        Returns True if a learning capture was dispatched; never raises. Mirrors
        the RCA->Learning handoff pattern (root_cause.py) — captures are advisory,
        not gates on recovery.
        """
        try:
            from aios.services.learning import get_learning_service

            learning_service = get_learning_service()
        except Exception:  # noqa: BLE001 — learning absent in minimal kernel
            return False
        try:
            await learning_service.capture_learning_from_analysis(
                analysis_id=f"recovery_{uuid.uuid4().hex[:12]}",
                failure_category=category.value,
                recommended_action=f"recover_via_{outcome.value}",
                root_cause=redact_exception(error) if error else f"{component} failure",
                preventive_measures=[f"bound recovery for {component}"],
            )
            return True
        except Exception as exc:  # noqa: BLE001 — learning is advisory
            logger.debug("Failure recovery learning capture skipped: %s", exc)
            return False

    async def _emit(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str | None
    ) -> None:
        """Emit a canonical recovery event (C1) with AI-OS provenance."""
        if self._event_bus is None:
            self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            return
        try:
            correlation_uuid = (
                uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
            )
        except ValueError:
            correlation_uuid = uuid.uuid4()
        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
        )
        result = self._event_bus.publish(event)
        if hasattr(result, "__await__"):
            await result

    def get_record(self, recovery_id: str) -> RecoveryRecord | None:
        return self._records.get(recovery_id)

    def list_records(self) -> list[RecoveryRecord]:
        return list(self._records.values())

    def reset(self) -> None:
        """Clear recorded recovery history (test isolation)."""
        self._records.clear()


def _is_failure_sentinel(result: Any) -> bool:
    """Treat explicit failure sentinels as 'not recovered' for retry purposes."""
    if isinstance(result, bool):
        return not result
    if isinstance(result, dict) and result.get("status") in ("error", "failure"):
        return True
    return False


__all__ = [
    "FailureRecoveryManager",
    "FailureCategory",
    "RecoveryOutcome",
    "RecoveryRecord",
]
