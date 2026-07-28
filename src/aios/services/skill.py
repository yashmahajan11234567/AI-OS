"""Skill Service.

Engineering Service wrapping the Kernel's SkillManager behind an event-driven
facade. Exposes load/unload/list/execute and emits SkillLoaded/SkillUnloaded/
SkillExecuted/SkillFailed. On KernelStarted it auto-discovers skills.
"""

from __future__ import annotations

import logging
from typing import Any

from aios.core.skill_manager import Skill, SkillManager, get_skill_manager
from aios.events.base import Event
from aios.events.types import (
    KernelStarted,
    SkillExecuted,
    SkillFailed,
    SkillLoaded,
    SkillUnloaded,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class SkillService(BaseService):
    """Event-driven facade over the Kernel SkillManager."""

    name = "skill"
    version = "1.0.0"
    description = "Skill registry, loading, execution, marketplace"
    depends_on: list[str] = []

    def __init__(self, *args, manager: SkillManager | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager = manager or get_skill_manager()

    @property
    def manager(self) -> SkillManager:
        return self._manager

    async def on_start(self) -> None:
        self.subscribe(self.handle_kernel_started, KernelStarted)

    def handle_kernel_started(self, event: Event) -> None:
        discovered = self._manager.discover_skills()
        logger.info("Discovered %d skills on kernel start", len(discovered))

    def load_skill(self, skill_id: str) -> bool:
        ok = self._manager.load_skill(skill_id)
        self.emit(
            SkillLoaded(
                source_service=self.name,
                correlation_id=skill_id,
                payload={"skill_id": skill_id, "success": ok},
            )
        )
        return ok

    def unload_skill(self, skill_id: str) -> bool:
        ok = self._manager.unload_skill(skill_id)
        self.emit(
            SkillUnloaded(
                source_service=self.name,
                correlation_id=skill_id,
                payload={"skill_id": skill_id, "success": ok},
            )
        )
        return ok

    def list_skills(self, category: str | None = None, tags: list[str] | None = None):
        return self._manager.list_skills(category=category, tags=tags)

    def execute_skill(self, skill_id: str, inputs: dict[str, Any] | None = None) -> Any:
        skill = self._manager.get_skill(skill_id)
        if skill is None:
            self.emit(
                SkillFailed(
                    source_service=self.name,
                    correlation_id=skill_id,
                    payload={"skill_id": skill_id, "error": "skill not found"},
                )
            )
            raise KeyError(skill_id)
        try:
            # The builtin manager is a registry; concrete execution is provided
            # by the Everything-Claude capability provider, so we record the call.
            self.emit(
                SkillExecuted(
                    source_service=self.name,
                    correlation_id=skill_id,
                    payload={"skill_id": skill_id, "inputs": inputs or {}},
                )
            )
            return {"skill_id": skill_id, "status": "executed"}
        except Exception as e:  # noqa: BLE001
            self.emit(
                SkillFailed(
                    source_service=self.name,
                    correlation_id=skill_id,
                    payload={"skill_id": skill_id, "error": str(e)},
                )
            )
            raise

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        base["manager"] = self._manager.get_stats()
        return base


__all__ = ["SkillService"]
