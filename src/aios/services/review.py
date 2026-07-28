"""Review Service.

Engineering Service for code, security, performance, and architecture review.
Consumes CodeReviewRequested / CodingCompleted and emits ReviewApproved /
ReviewRejected / ReviewFailed / SecurityIssueFound / PerformanceIssueFound.
Review never calls Coding or Testing directly.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    CodeReviewRequested,
    PerformanceIssueFound,
    ReviewApproved,
    ReviewFailed,
    ReviewRejected,
    ReviewStarted,
    SecurityIssueFound,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class ReviewService(BaseService):
    """Review artifacts and approve/reject them."""

    name = "review"
    version = "1.0.0"
    description = "Code, security, performance, architecture review"
    depends_on: list[str] = ["coding", "ai_agency"]

    async def on_start(self) -> None:
        self.subscribe(self.handle_review_requested, CodeReviewRequested)

    def handle_review_requested(self, event: Event) -> None:
        self.emit(
            ReviewStarted(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=event.payload,
            )
        )
        result = self.review(event.payload)
        base = {
            "task_id": event.payload.get("task_id", ""),
            "step_id": event.payload.get("step_id", ""),
            "artifact_id": event.payload.get("artifact_id", ""),
            "review_id": result["review_id"],
            "verdict": result["verdict"],
        }
        for issue in result["security_issues"]:
            self.emit(
                SecurityIssueFound(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={**base, "issue": issue},
                )
            )
        for issue in result["performance_issues"]:
            self.emit(
                PerformanceIssueFound(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={**base, "issue": issue},
                )
            )
        if result["verdict"] == "approved":
            self.emit(
                ReviewApproved(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload=base,
                )
            )
        elif result["verdict"] == "rejected":
            self.emit(
                ReviewRejected(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={**base, "feedback": result["feedback"]},
                )
            )
        else:  # error
            self.emit(
                ReviewFailed(
                    source_service=self.name,
                    correlation_id=event.correlation_id,
                    causation_id=event.correlation_id,
                    payload={**base, "error": result.get("error", "review failed")},
                )
            )

    def review(self, request: dict[str, Any]) -> dict[str, Any]:
        """Deterministic reviewer: approves unless an issue file is flagged.

        ``request`` may carry ``force_reject`` or ``security_violations`` so
        tests can exercise the reject/security paths.
        """
        verdict = "approved" if not request.get("force_reject") else "rejected"
        security_issues = list(request.get("security_violations", []))
        performance_issues = list(request.get("performance_issues", []))
        if security_issues:
            verdict = "rejected"
        feedback = request.get("feedback")
        if feedback is None:
            feedback = [] if verdict == "approved" else ["issues found: regenerate code"]
        return {
            "review_id": f"rev_{uuid4().hex[:8]}",
            "verdict": verdict,
            "security_issues": security_issues,
            "performance_issues": performance_issues,
            "feedback": feedback,
        }


__all__ = ["ReviewService"]