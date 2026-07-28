"""Coding Service.

Engineering Service for code generation, refactoring, and implementation.
Consumes CodingStarted (and ReviewApproved-from-coding) events and emits
CodeGenerated / CodingCompleted / CodingFailed. Never calls Review or
Testing directly - it only publishes events.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    CodeGenerated,
    CodeReviewRequested,
    CodingCompleted,
    CodingFailed,
    CodingStarted,
    ReviewApproved,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class CodingService(BaseService):
    """Generate artifacts requested by a plan step."""

    name = "coding"
    version = "1.0.0"
    description = "Code generation, refactoring, implementation"
    depends_on: list[str] = ["planning", "memory"]

    async def on_start(self) -> None:
        self.subscribe(self.handle_coding_start, CodingStarted)
        # A plan step that targets us, approved by review, restarts coding.
        self.subscribe(self.handle_review_approved, ReviewApproved)

    def handle_coding_start(self, event: Event) -> None:
        try:
            artifact = self.implement(event.payload)
            self.emit(
                CodeGenerated(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload=artifact,
                )
            )
            self.emit(
                CodingCompleted(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "step_id": event.payload.get("step_id", ""),
                        "artifact_id": artifact["artifact_id"],
                        "files": artifact["files"],
                    },
                )
            )
            # Request a review of the produced code.
            self.emit(
                CodeReviewRequested(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "step_id": event.payload.get("step_id", ""),
                        "artifact_id": artifact["artifact_id"],
                    },
                )
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Coding failed: %s", e)
            self.emit(
                CodingFailed(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "step_id": event.payload.get("step_id", ""),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            )

    def handle_review_approved(self, event: Event) -> None:
        # ReviewApproved is published by the review service after it approves.
        # Coding does nothing on approval itself - testing does. We only
        # subscribe so the type expectation is satisfied; no-op here.
        return

    # ----- API ------------------------------------------------------
    def implement(self, request: dict[str, Any]) -> dict[str, Any]:
        """Produce a deterministic artifact for a coding request.

        Returns a dict with artifact_id + files. In production this would
        invoke the Model Router to generate code; here it returns a stub.
        """
        task_id = request.get("task_id", "unknown")
        step_id = request.get("step_id", "unknown")
        spec = request.get("spec") or request.get("description") or f"implement {step_id}"
        artifact_id = f"art_{uuid4().hex[:8]}"
        files = request.get("files") or [{"path": (step_id or "module") + ".py", "content": str(spec)}]
        # Convert a list/dict of files into a stable representation.
        if isinstance(files, dict):
            files = [{"path": p, "content": c} for p, c in files.items()]
        else:
            files = [{"path": (step_id or "module") + ".py", "content": str(spec)}]
        return {
            "artifact_id": artifact_id,
            "task_id": task_id,
            "step_id": step_id,
            "files": files,
        }


__all__ = ["CodingService"]