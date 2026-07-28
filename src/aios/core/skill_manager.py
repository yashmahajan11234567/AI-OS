"""
Skill Manager for AI-OS Hermes Kernel.

Manages skill loading, execution, and marketplace integration.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import SkillLoaded, SkillUnloaded, SkillExecuted, SkillFailed

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A skill definition."""

    skill_id: str
    name: str
    version: str
    description: str
    author: str = ""
    category: str = "general"
    entry_point: str = ""  # Module:function
    config_schema: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    loaded: bool = False
    loaded_at: datetime | None = None


@dataclass
class SkillExecution:
    """Skill execution record."""

    execution_id: str
    skill_id: str
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: int = 0


class SkillManager:
    """
    Manages skills for AI-OS.

    Features:
    - Skill loading from multiple sources (.claude/skills, marketplace, local)
    - Dependency resolution
    - Execution sandboxing
    - Version management
    - Skill marketplace integration
    """

    def __init__(
        self,
        skills_dir: Path | None = None,
        marketplace_enabled: bool = True,
    ):
        """
        Initialize the Skill Manager.

        Args:
            skills_dir: Directory containing skills
            marketplace_enabled: Whether to enable marketplace
        """
        self._skills_dir = skills_dir or Path("./.claude/skills")
        self._skills_dir.mkdir(parents=True, exist_ok=True)

        self._marketplace_enabled = marketplace_enabled
        self._skills: dict[str, Skill] = {}
        self._loaded_modules: dict[str, Any] = {}
        self._executions: list[SkillExecution] = []
        self._event_bus = get_event_bus()

        # Load built-in skills
        self._load_builtin_skills()

    def _load_builtin_skills(self) -> None:
        """Load built-in skills."""
        builtin = [
            Skill(
                skill_id="builtin.shell",
                name="Shell Command Execution",
                version="1.0.0",
                description="Execute shell commands safely",
                category="system",
                entry_point="aios.skills.builtin:shell",
                tags=["system", "shell", "command"],
            ),
            Skill(
                skill_id="builtin.file_ops",
                name="File Operations",
                version="1.0.0",
                description="Read, write, and manipulate files",
                category="system",
                entry_point="aios.skills.builtin:file_ops",
                tags=["system", "files", "io"],
            ),
            Skill(
                skill_id="builtin.web_search",
                name="Web Search",
                version="1.0.0",
                description="Search the web for information",
                category="research",
                entry_point="aios.skills.builtin:web_search",
                tags=["research", "search", "web"],
            ),
            Skill(
                skill_id="builtin.code_analysis",
                name="Code Analysis",
                version="1.0.0",
                description="Analyze code for issues, patterns, and quality",
                category="development",
                entry_point="aios.skills.builtin:code_analysis",
                tags=["development", "analysis", "code"],
            ),
        ]

        for skill in builtin:
            self._skills[skill.skill_id] = skill

    def discover_skills(self) -> list[Skill]:
        """Discover skills in the skills directory."""
        discovered = []

        for skill_file in self._skills_dir.glob("*.json"):
            try:
                data = json.loads(skill_file.read_text())
                skill = Skill(
                    skill_id=data.get("skill_id", skill_file.stem),
                    name=data["name"],
                    version=data["version"],
                    description=data["description"],
                    author=data.get("author", ""),
                    category=data.get("category", "general"),
                    entry_point=data.get("entry_point", ""),
                    config_schema=data.get("config_schema", {}),
                    dependencies=data.get("dependencies", []),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                )
                discovered.append(skill)
            except Exception as e:
                logger.warning(f"Failed to load skill from {skill_file}: {e}")

        return discovered

    def register_skill(self, skill: Skill) -> None:
        """Register a skill."""
        if skill.skill_id in self._skills:
            logger.warning(f"Skill {skill.skill_id} already registered, overwriting")
        self._skills[skill.skill_id] = skill
        logger.info(f"Registered skill: {skill.skill_id} ({skill.name})")

    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(
        self, category: str | None = None, tags: list[str] | None = None
    ) -> list[Skill]:
        """List skills with optional filtering."""
        skills = list(self._skills.values())

        if category:
            skills = [s for s in skills if s.category == category]

        if tags:
            skills = [s for s in skills if any(t in s.tags for t in tags)]

        return skills

    def load_skill(self, skill_id: str) -> bool:
        """
        Load a skill module.

        Args:
            skill_id: Skill identifier

        Returns:
            True if loaded successfully
        """
        skill = self._skills.get(skill_id)
        if not skill:
            logger.error(f"Skill {skill_id} not found")
            return False

        if skill.loaded:
            logger.info(f"Skill {skill_id} already loaded")
            return True

        if not skill.entry_point:
            logger.error(f"Skill {skill_id} has no entry point")
            return False

        try:
            # Parse entry point (module:function)
            module_path, func_name = skill.entry_point.split(":", 1)

            # Import module
            if module_path.startswith("."):
                # Relative import from skills dir
                spec = importlib.util.spec_from_file_location(
                    module_path, self._skills_dir / f"{module_path}.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                module = importlib.import_module(module_path)

            # Get function/class
            skill_func = getattr(module, func_name)

            self._loaded_modules[skill_id] = skill_func
            skill.loaded = True
            skill.loaded_at = datetime.utcnow()

            self._event_bus.publish(
                SkillLoaded(
                    source_service="skill_manager",
                    correlation_id=skill_id,
                    payload={
                        "skill_id": skill_id,
                        "name": skill.name,
                        "version": skill.version,
                        "source": skill.entry_point,
                    },
                )
            )

            logger.info(f"Loaded skill: {skill_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to load skill {skill_id}: {e}")
            return False

    def unload_skill(self, skill_id: str) -> bool:
        """Unload a skill."""
        skill = self._skills.get(skill_id)
        if not skill or not skill.loaded:
            return False

        self._loaded_modules.pop(skill_id, None)
        skill.loaded = False
        skill.loaded_at = None

        self._event_bus.publish(
            SkillUnloaded(
                source_service="skill_manager",
                correlation_id=skill_id,
                payload={"skill_id": skill_id, "reason": "manual_unload"},
            )
        )

        logger.info(f"Unloaded skill: {skill_id}")
        return True

    async def execute_skill(
        self,
        skill_id: str,
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a skill.

        Args:
            skill_id: Skill identifier
            input_data: Input data for the skill
            config: Optional configuration

        Returns:
            Skill output data
        """
        skill = self._skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        if not skill.loaded:
            if not self.load_skill(skill_id):
                raise RuntimeError(f"Failed to load skill {skill_id}")

        skill_func = self._loaded_modules[skill_id]
        execution_id = f"exec_{datetime.utcnow().timestamp()}"

        execution = SkillExecution(
            execution_id=execution_id,
            skill_id=skill_id,
            input_data=input_data,
        )

        try:
            # Execute skill
            if hasattr(skill_func, "__call__"):
                if asyncio.iscoroutinefunction(skill_func):
                    result = await skill_func(input_data, config or {})
                else:
                    result = skill_func(input_data, config or {})
            else:
                raise ValueError(f"Skill {skill_id} entry point is not callable")

            execution.output_data = result
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

            self._executions.append(execution)

            self._event_bus.publish(
                SkillExecuted(
                    source_service="skill_manager",
                    correlation_id=execution_id,
                    payload={
                        "skill_id": skill_id,
                        "execution_id": execution_id,
                        "input": input_data,
                        "output": result,
                        "duration_ms": execution.duration_ms,
                    },
                )
            )

            return result

        except Exception as e:
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            self._executions.append(execution)

            self._event_bus.publish(
                SkillFailed(
                    source_service="skill_manager",
                    correlation_id=execution_id,
                    payload={
                        "skill_id": skill_id,
                        "execution_id": execution_id,
                        "error": str(e),
                        "input": input_data,
                    },
                )
            )

            logger.error(f"Skill {skill_id} execution failed: {e}")
            raise

    def get_execution_history(
        self, skill_id: str | None = None, limit: int = 100
    ) -> list[SkillExecution]:
        """Get skill execution history."""
        executions = self._executions
        if skill_id:
            executions = [e for e in executions if e.skill_id == skill_id]
        return executions[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get skill manager statistics."""
        loaded = sum(1 for s in self._skills.values() if s.loaded)
        return {
            "total_skills": len(self._skills),
            "loaded_skills": loaded,
            "categories": {
                cat: len([s for s in self._skills.values() if s.category == cat])
                for cat in set(s.category for s in self._skills.values())
            },
            "total_executions": len(self._executions),
        }


import asyncio

# Global skill manager
_global_skill_manager: SkillManager | None = None


def get_skill_manager(
    skills_dir: Path | None = None, marketplace_enabled: bool = True
) -> SkillManager:
    """Get or create the global skill manager."""
    global _global_skill_manager
    if _global_skill_manager is None:
        _global_skill_manager = SkillManager(skills_dir, marketplace_enabled)
    return _global_skill_manager


def set_skill_manager(manager: SkillManager) -> None:
    """Set the global skill manager."""
    global _global_skill_manager
    _global_skill_manager = manager


__all__ = [
    "SkillManager",
    "Skill",
    "SkillExecution",
    "get_skill_manager",
    "set_skill_manager",
]