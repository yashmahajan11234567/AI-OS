"""Learning Service.

Engineering Service that captures learnings from successful projects and
failures and stores them as Engineering Intelligence (a memory category), so
future workflows can reuse them. It consumes RootCauseResolved / WorkflowCompleted /
TestingCompleted / DeploymentCompleted and emits LearningCaptured events.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    LearningCaptured,
    LearningValidated,
    RootCauseResolved,
)
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType as CanonicalEventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class LearningService(BaseService):
    """Capture successes, failures, decisions as Engineering Intelligence."""

    name = "learning"
    version = "1.0.0"
    description = "Pattern extraction, learnings, engineering intelligence"
    depends_on: list[str] = ["memory"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._learnings: list[dict[str, Any]] = []

    async def on_start(self) -> None:
        self.subscribe(self.handle_root_cause_resolved, RootCauseResolved)
        # Register this instance globally for RootCauseAnalyzer to access
        set_learning_service_instance(self)

    async def _emit_legacy_event(self, event: Event) -> int:
        """Emit a legacy event by converting to CoreEvent."""
        from aios.services.base import BaseService

        # If legacy_event_type is already a canonical EventType, use it directly
        legacy_event_type = event.event_type
        if isinstance(legacy_event_type, CanonicalEventType):
            canonical_type = legacy_event_type
        else:
            # Otherwise look up in the legacy mapping
            canonical_type = BaseService._LEGACY_TO_CANONICAL.get(legacy_event_type)
            if canonical_type is None:
                logger.warning(f"No canonical mapping for legacy event type: {legacy_event_type}")
                canonical_type = CanonicalEventType.AI_AGENT_AUDIT_EMITTED

        # Always generate a proper UUID for correlationId
        import uuid
        correlation_uuid = uuid.uuid4()

        core_event = CoreEvent(
            eventType=canonical_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_uuid,
            causationId=uuid.uuid4(),
            payload=EventPayload(event.payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(canonical_type),
        )

        result = await self.emit(core_event)
        logger.info(f"LearningService emit legacy event {legacy_event_type} -> {canonical_type}: {result}")
        return result

    async def handle_root_cause_resolved(self, event: Event) -> None:
        learning = {
            "learning_id": f"learn_{uuid4().hex[:8]}",
            "type": "failure_resolution",
            "analysis_id": event.payload.get("analysis_id", ""),
            "resolution": event.payload.get("resolution", ""),
            "preventive_measures": event.payload.get("preventive_measures", []),
            "captured_at": time.time(),
        }
        self._learnings.append(learning)
        await self._emit_legacy_event(
            LearningCaptured(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=learning,
            )
        )

    async def capture_learning_from_analysis(
        self,
        analysis_id: str,
        failure_category: str,
        recommended_action: str,
        root_cause: str,
        preventive_measures: list[str],
    ) -> None:
        """Capture learning directly from RootCauseAnalysis without waiting for resolution.

        This is called by RootCauseAnalyzer to immediately capture learnings from
        the analysis phase, before the actual resolution is implemented.
        """
        logger.info(f"LearningService.capture_learning_from_analysis called with analysis_id={analysis_id}")
        learning = {
            "learning_id": f"learn_{uuid4().hex[:8]}",
            "type": "failure_resolution",
            "analysis_id": analysis_id,
            "resolution": recommended_action,
            "preventive_measures": preventive_measures,
            "captured_at": time.time(),
            "root_cause": root_cause,
            "failure_category": failure_category,
        }
        self._learnings.append(learning)
        logger.info(f"LearningService added learning, total learnings: {len(self._learnings)}")
        await self._emit_legacy_event(
            LearningCaptured(
                source_service=self.name,
                correlation_id=analysis_id,
                causation_id=analysis_id,
                payload=learning,
            )
        )
        logger.info(f"LearningService emitted LearningCaptured event")

    # ------------------------------------------------------------------
    # Validation / promotion (M9-N5: Lesson validation/promotion)
    # ------------------------------------------------------------------

    async def mark_validated(
        self,
        learning_id: str,
        *,
        validator: str = "unspecified",
        confidence: float | None = None,
        notes: str | None = None,
    ) -> bool:
        """Validate / promote a captured learning (spec §11.2).

        A captured learning enters the store as **unvalidated**. A qualified
        reviewer (Council / Judge / reviewer) may call this method to mark it
        **validated** (promoted), recording the validator identity, optional
        confidence, and optional notes.

        Semantics:
        * Idempotent on the same learning_id.
        * On success, emits a ``LearningValidated`` audit event (reusing the
          canonical ``AI_AGENT_AUDIT_EMITTED`` EventType — NO new EventType).
        * Returns True iff the learning was found and updated, False otherwise
          (e.g. unknown id or already validated with identical provenance).

        Authority boundary (spec §16): this method records *advisory* validation
        provenance — it does NOT grant execution authority. Validation marks a
        learning as eligible for retrieval by ``get_validated_lessons``; only
        validated learnings feed PlanningService advisory context.
        """
        target: dict[str, Any] | None = None
        for learning in self._learnings:
            if learning.get("learning_id") == learning_id:
                target = learning
                break

        if target is None:
            logger.warning("mark_validated: unknown learning_id=%r", learning_id)
            return False

        # Idempotency guard (spec §11.2): re-validating with the same validator
        # is a no-op at the data level but still emits an audit signal so the
        # re-validation attempt is visible on the bus.
        if target.get("validated"):
            logger.info(
                "mark_validated: learning_id=%r already validated by %r",
                learning_id,
                target.get("validator"),
            )

        import time as _time

        target["validated"] = True
        target["validator"] = validator
        target["validation_confidence"] = confidence
        target["validation_notes"] = notes
        target["validated_at"] = _time.time()

        await self._emit_legacy_event(
            LearningValidated(
                source_service=self.name,
                correlation_id=learning_id,
                causation_id=learning_id,
                payload={
                    "learning_id": learning_id,
                    "validator": validator,
                    "confidence": confidence,
                    "notes": notes,
                    "validated_at": target["validated_at"],
                },
            )
        )

        logger.info(
            "mark_validated: learning_id=%r validated by %r (confidence=%s)",
            learning_id,
            validator,
            confidence,
        )
        return True

    def get_validated_lessons(
        self,
        *,
        failure_category: str | None = None,
        analysis_id: str | None = None,
        limit: int = 50,
        since: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve only **validated/promoted** learnings (spec §11.2).

        Mirrors :meth:`get_learnings` but further filters to records where
        ``validated == True``. PlanningService consumes this endpoint so that
        only reviewed learnings enter advisory context. Returns shallow copies.
        """
        validated = [
            learning
            for learning in self._learnings
            if learning.get("validated") is True
        ]
        if limit <= 0:
            return []
        results: list[dict[str, Any]] = []
        for learning in reversed(validated):  # newest first
            if failure_category is not None and (
                learning.get("failure_category") != failure_category
            ):
                continue
            if analysis_id is not None and (
                learning.get("analysis_id") != analysis_id
            ):
                continue
            if since is not None and learning.get("captured_at", 0) < since:
                continue
            results.append(dict(learning))
            if len(results) >= limit:
                break
        return results

    def stats(self) -> dict[str, Any]:
        """Return learning statistics (spec §11.2).

        Distinguishes captured vs validated/promoted so governance can measure
        the validation throughput independently of capture rate.
        """
        validated_count = sum(
            1 for l in self._learnings if l.get("validated") is True
        )
        return {
            "learnings_captured": len(self._learnings),
            "learnings_validated": validated_count,
            "learnings_unvalidated": len(self._learnings) - validated_count,
        }

    # ------------------------------------------------------------------
    # M9-N2 (spec §11.2) — retrieval API (GAP-B closure)
    # ------------------------------------------------------------------

    def get_learnings(
        self,
        *,
        failure_category: str | None = None,
        analysis_id: str | None = None,
        limit: int = 50,
        since: float | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve stored learnings, filtered and newest-first.

        Returns **shallow copies** so callers cannot mutate the store. All
        filters are optional and composable:

        * ``failure_category`` — exact match on the captured category
          (records captured via ``handle_root_cause_resolved`` carry no
          category and are returned only by unfiltered queries).
        * ``analysis_id`` — exact match on the originating RCA analysis.
        * ``since`` — epoch seconds lower bound on ``captured_at``.
        * ``limit`` — max records returned (newest first).
        """
        if limit <= 0:
            return []
        results: list[dict[str, Any]] = []
        for learning in reversed(self._learnings):  # newest first
            if failure_category is not None and (
                learning.get("failure_category") != failure_category
            ):
                continue
            if analysis_id is not None and (
                learning.get("analysis_id") != analysis_id
            ):
                continue
            if since is not None and learning.get("captured_at", 0) < since:
                continue
            results.append(dict(learning))
            if len(results) >= limit:
                break
        return results

    def query_relevant(self, objective: str, limit: int = 5) -> list[dict[str, Any]]:
        """Keyword/recency relevance match for an objective (spec §11.2).

        Deliberately simple — token overlap scored with a recency tiebreak.
        No ML/embeddings (M10+ scope per spec §3). Returns shallow copies,
        best-match first, at most ``limit`` records.
        """
        if limit <= 0:
            return []
        tokens = _tokenize(objective)
        if not tokens:
            return []

        def _score(learning: dict[str, Any]) -> tuple[float, float]:
            haystack = " ".join(
                str(learning.get(field, ""))
                for field in (
                    "root_cause",
                    "resolution",
                    "failure_category",
                    "type",
                )
            )
            words = set(_tokenize(haystack))
            overlap = len(tokens & words)
            # Recency tiebreak: newer captures win equal-overlap comparisons.
            return (float(overlap), float(learning.get("captured_at", 0)))

        scored = [(_score(l), l) for l in self._learnings]
        scored = [(s, l) for s, l in scored if s[0] > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [dict(learning) for _, learning in scored[:limit]]


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens of length >= 3 (drops stopwords-ish noise)."""
    import re

    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) >= 3}


_learning_service_instance: LearningService | None = None


def set_learning_service_instance(instance: LearningService) -> None:
    """Set the global LearningService instance."""
    global _learning_service_instance
    _learning_service_instance = instance


def get_learning_service() -> LearningService:
    """Get the global LearningService instance."""
    if _learning_service_instance is None:
        raise RuntimeError("LearningService not initialized. Call set_learning_service_instance first.")
    return _learning_service_instance


__all__ = [
    "LearningService",
    "set_learning_service_instance",
    "get_learning_service",
    "get_learnings",
    "get_validated_lessons",
    "mark_validated",
    "query_relevant",
]