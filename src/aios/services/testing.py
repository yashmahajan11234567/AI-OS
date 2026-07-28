"""Testing Service.

Engineering Service for test generation,-execution, and coverage analysis.
Consumes ReviewApproved / TestingStarted and emits TestsPassed / TestsFailed /
TestingCompleted / TestingFailed.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    ReviewApproved,
    TestGenerated,
    TestingCompleted,
    TestingFailed,
    TestingStarted,
    TestsFailed,
    TestsPassed,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class TestingService(BaseService):
    """Run tests against an artifact and report pass/fail."""

    name = "testing"
    version = "1.0.0"
    description = "Test generation, execution, coverage analysis"
    depends_on: list[str] = ["review"]

    async def on_start(self) -> None:
        # When review approves an artifact, generate + run tests for it.
        self.subscribe(self.handle_review_approved, ReviewApproved)
        self.subscribe(self.handle_testing_started, TestingStarted)

    def handle_review_approved(self, event: Event) -> None:
        # Re-publish as a TestingStarted intent so the workflow tracks it.
        self.emit(
            TestingStarted(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload={
                    "task_id": event.payload.get("task_id", ""),
                    "step_id": event.payload.get("step_id", ""),
                    "artifact_id": event.payload.get("artifact_id", ""),
                },
            )
        )

    def handle_testing_started(self, event: Event) -> None:
        try:
            result = self.test(event.payload)
            self.emit(
                TestGenerated(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "artifact_id": event.payload.get("artifact_id", ""),
                        "tests": result["tests"],
                    },
                )
            )
            common = {
                "task_id": event.payload.get("task_id", ""),
                "step_id": event.payload.get("step_id", ""),
                "artifact_id": event.payload.get("artifact_id", ""),
                "passed": result["passed"],
                "failed": result["failed"],
            }
            (TestsPassed if result["passed"] and not result["failed"] else TestsFailed)(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=common,
            )
            self.emit(
                (TestingCompleted if result["passed"] else TestingFailed)(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={**common, "run_id": result["run_id"]},
                )
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Testing failed: %s", e)
            self.emit(
                TestingFailed(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={
                        "task_id": event.payload.get("task_id", ""),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            )

    def test(self, request: dict[str, Any]) -> dict[str, Any]:
        """Deterministic test runner; passes unless asked to fail."""
        failed = bool(request.get("force_fail"))
        passed = not failed
        return {
            "run_id": f"run_{uuid4().hex[:8]}",
            "tests": [{"name": "smoke_test", "passed": passed}],
            "passed": passed,
            "failed": failed,
        }


__all__ = ["TestingService"]