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
    RootCauseResolved,
)
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

    def handle_root_cause_resolved(self, event: Event) -> None:
        learning = {
            "learning_id": f"learn_{uuid4().hex[:8]}",
            "type": "failure_resolution",
            "analysis_id": event.payload.get("analysis_id", ""),
            "resolution": event.payload.get("resolution", ""),
            "preventive_measures": event.payload.get("preventive_measures", []),
            "captured_at": time.time(),
        }
        self._learnings.append(learning)
        self.emit(
            LearningCaptured(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=learning,
            )
        )

    def stats(self) -> dict[str, Any]:
        return {"learnings_captured": len(self._learnings)}


__all__ = ["LearningService"]