"""Deployment Service.

Engineering Service for build, deploy, and rollback. Consumes
DeploymentRequested (driven by TestingCompleted from the workflow) and emits
DeploymentStarted / DeploymentSucceeded / DeploymentFailed /
DeploymentRolledBack.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.events.base import Event
from aios.events.types import (
    DeploymentCompleted,
    DeploymentFailed,
    DeploymentRequested,
    DeploymentRolledBack,
    DeploymentStarted,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class DeploymentService(BaseService):
    """Build + deploy artifacts to a target environment."""

    name = "deployment"
    version = "1.0.0"
    description = "Container build, deploy, rollback"
    depends_on: list[str] = ["testing", "review"]

    async def on_start(self) -> None:
        self.subscribe(self.handle_deployment_requested, DeploymentRequested)

    def handle_deployment_requested(self, event: Event) -> None:
        self.emit(
            DeploymentStarted(
                source_service=self.name,
                correlation_id=event.correlation_id,
                causation_id=event.correlation_id,
                payload=event.payload,
            )
        )
        try:
            result = self.deploy(event.payload)
            if result["success"]:
                self.emit(
                    DeploymentCompleted(
                        source_service=self.name,
                        correlation_id=event.correlation_id,
                        causation_id=event.correlation_id,
                        payload={
                            "task_id": event.payload.get("task_id", ""),
                            "environment": result["environment"],
                            "url": result.get("url"),
                            "version": result["version"],
                        },
                    )
                )
            else:
                self.emit(
                    DeploymentFailed(
                        source_service=self.name,
                        correlation_id=event.correlation_id,
                        causation_id=event.correlation_id,
                        payload={
                            "task_id": event.payload.get("task_id", ""),
                            "error": result.get("error", "deployment failed"),
                        },
                    )
                )
        except Exception as e:  # noqa: BLE001
            logger.exception("Deployment failed: %s", e)
            self.emit(
                DeploymentFailed(
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

    def deploy(self, request: dict[str, Any]) -> dict[str, Any]:
        env = request.get("environment", "production")
        success = not request.get("force_fail", False)
        out = {
            "environment": env,
            "version": request.get("version", "1.0.0"),
            "success": success,
        }
        if success:
            out["deployment_id"] = f"dep_{uuid4().hex[:8]}"
            out["url"] = f"https://{env}.example-app.local"
        else:
            out["error"] = request.get("failure_reason", "deployment failed")
        return out

    def rollback(self, deployment_id: str, reason: str = "") -> str:
        return deployment_id  # events emitted by caller via emit()


__all__ = ["DeploymentService"]