"""Skill Service.

Engineering Service wrapping the Kernel's SkillManager behind an event-driven
facade. Exposes load/unload/list/execute and emits SkillLoaded/SkillUnloaded/
SkillExecuted/SkillFailed. On KernelStarted it auto-discovers skills.
M4-ADAPTER: Adds SKILL.md specification support for portable skill ingestion.
M4-ADAPTER: Integrates SkillSpecTor security gate for pre-install validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aios.core.skill_manager import Skill, SkillManager, get_skill_manager
from aios.core.skill_spec import SkillSpec
from aios.core.security_manager import SecurityManager, SkillSpecTorResult, get_security_manager
from aios.events.base import Event
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType as CanonicalEventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
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

    async def load_skill(self, skill_id: str) -> bool:
        ok = self._manager.load_skill(skill_id)
        await self._emit_legacy_event(
            SkillLoaded(
                source_service=self.name,
                correlation_id=skill_id,
                payload={"skill_id": skill_id, "success": ok},
            )
        )
        return ok

    # M4-ADAPTER: SKILL.md specification methods
    def load_skill_spec(self, spec_path: str | Path) -> Skill | None:
        """Load a skill from a SKILL.md specification file (M4-ADAPTER).

        Per M4-ADAPTER: Runs SkillSpecTor security gate validation BEFORE installation.
        SkillSpecTor is an integration gate (LLM stage disabled per C10);
        AI-OS SecurityManager remains final authority.
        """
        # Parse the spec first
        from aios.core.skill_spec import SkillSpecParser
        parser = SkillSpecParser()
        spec = parser.parse_file(spec_path)
        if not spec:
            return None

        # M4-ADAPTER: Run SkillSpecTor security gate validation before install
        security_manager = get_security_manager()
        if security_manager.is_initialized:
            gate_result = security_manager.validate_skill_before_install(spec)
            if not gate_result.passed:
                # Log the rejection but don't raise - let the manager decide
                logger.warning(
                    f"SkillSpecTor gate REJECTED skill {spec.skill_id}: "
                    f"{len(gate_result.violations)} violations, "
                    f"high/critical: {sum(1 for v in gate_result.violations if v.severity in ('high', 'critical'))}"
                )
                # Emit a skill failed event for the security rejection
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._emit_legacy_event(
                        SkillFailed(
                            source_service=self.name,
                            correlation_id=spec.skill_id,
                            payload={
                                "skill_id": spec.skill_id,
                                "error": f"SkillSpecTor security gate rejected: {len(gate_result.violations)} violations",
                                "gate_result": {
                                    "scan_id": gate_result.scan_id,
                                    "duration_ms": gate_result.scan_duration_ms,
                                    "violations": [
                                        {"severity": v.severity, "description": v.description, "category": v.category}
                                        for v in gate_result.violations
                                    ],
                                },
                            },
                        )
                    ))
                except RuntimeError:
                    pass  # No running loop

                # SecurityManager is final authority - return None to reject
                return None

        # Gate passed or not initialized - proceed with loading
        return self._manager.load_skill_spec(spec_path)

    def discover_skill_specs(self, specs_dir: str | Path | None = None) -> list[Skill]:
        """Discover and register skills from SKILL.md specifications in a directory (M4-ADAPTER).

        Each discovered skill spec is validated through SkillSpecTor gate before registration.
        """
        if specs_dir:
            return self._manager.discover_skill_specs_from_dir(specs_dir)
        return []

    def discover_and_validate_skill_specs(self, specs_dir: str | Path) -> tuple[list[Skill], list[SkillSpecTorResult]]:
        """Discover, validate through SkillSpecTor, and register skills from SKILL.md specs (M4-ADAPTER).

        Returns:
            Tuple of (registered_skills, gate_results)
        """
        from pathlib import Path
        from aios.core.skill_spec import discover_skill_specs

        path = Path(specs_dir)
        specs = discover_skill_specs(path)

        registered_skills = []
        gate_results = []

        security_manager = get_security_manager()

        for spec in specs:
            # Run SkillSpecTor validation
            if security_manager.is_initialized and security_manager.is_skillspector_gate_enabled():
                gate_result = security_manager.validate_skill_before_install(spec)
                gate_results.append(gate_result)

                if not gate_result.passed:
                    logger.warning(
                        f"SkillSpecTor gate REJECTED skill {spec.skill_id} during discovery"
                    )
                    continue  # Skip registration for failed skills

            # Gate passed - register the skill
            skill = spec.to_skill()
            self._manager.register_skill(skill)
            registered_skills.append(skill)
            logger.info(f"Registered skill from SKILL.md (validated): {skill.skill_id}")

        return registered_skills, gate_results

    def get_skill_spec(self, skill_id: str) -> SkillSpec | None:
        """Get the parsed SKILL.md specification for a skill (M4-ADAPTER)."""
        return self._manager._spec_parser.get_spec(skill_id)

    def validate_skill_spec(self, spec_path: str | Path) -> tuple[bool, list[str]]:
        """Validate a SKILL.md specification file (M4-ADAPTER).

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        from aios.core.skill_spec import SkillSpecParser
        parser = SkillSpecParser()
        spec = parser.parse_file(spec_path)
        if spec is None:
            return False, ["Failed to parse SKILL.md file"]

        errors = []
        if not spec.name:
            errors.append("Missing required field: name")
        if not spec.version:
            errors.append("Missing required field: version")
        if not spec.description:
            errors.append("Missing required field: description")
        if not spec.entry_point:
            errors.append("Missing required field: entry_point")

        return len(errors) == 0, errors

    async def unload_skill(self, skill_id: str) -> bool:
        ok = self._manager.unload_skill(skill_id)
        await self._emit_legacy_event(
            SkillUnloaded(
                source_service=self.name,
                correlation_id=skill_id,
                payload={"skill_id": skill_id, "success": ok},
            )
        )
        return ok

    def list_skills(self, category: str | None = None, tags: list[str] | None = None):
        return self._manager.list_skills(category=category, tags=tags)

    async def execute_skill(self, skill_id: str, inputs: dict[str, Any] | None = None) -> Any:
        skill = self._manager.get_skill(skill_id)
        if skill is None:
            await self._emit_legacy_event(
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
            await self._emit_legacy_event(
                SkillExecuted(
                    source_service=self.name,
                    correlation_id=skill_id,
                    payload={"skill_id": skill_id, "inputs": inputs or {}},
                )
            )
            return {"skill_id": skill_id, "status": "executed"}
        except Exception as e:  # noqa: BLE001
            await self._emit_legacy_event(
                SkillFailed(
                    source_service=self.name,
                    correlation_id=skill_id,
                    payload={"skill_id": skill_id, "error": str(e)},
                )
            )
            raise

    async def _emit_legacy_event(self, event: Event) -> int:
        """Emit a legacy event by converting to CoreEvent."""
        from aios.services.base import BaseService
        from aios.events.core.types import EventType as CanonicalEventType
        from aios.events.base import EventType as LegacyEventType

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
        logger.info(f"SkillService emit legacy event {legacy_event_type} -> {canonical_type}: {result}")
        return result

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        base["manager"] = self._manager.get_stats()
        return base


__all__ = ["SkillService"]
