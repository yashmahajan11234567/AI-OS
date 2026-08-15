"""
ComponentIdentity (Part 2 §2.2.2).

Identifies the originating/intended component of an Event:

    ComponentIdentity {
      componentType: 'kernel' | 'core_component' | 'core_manager'
                   | 'engineering_service' | 'capability_facade'
                   | 'application_service' | 'extension'
      componentName: string            // e.g. "EventBus", "PlanningService"
      instanceId: UUID | null          // null for singletons
      version: SemanticVersion         // Component version
    }

The core model does NOT enforce INV-EVT-008 (name must match ServiceRegistry)
because ServiceRegistry is a later component; that invariant is the
responsibility of the publishing/registration layer.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from aios.events.core.types import SemanticVersion


class ComponentType(str, Enum):
    """Discriminant for the kind of component (Part 2 §2.2.2)."""

    KERNEL = "kernel"
    CORE_COMPONENT = "core_component"
    CORE_MANAGER = "core_manager"
    ENGINEERING_SERVICE = "engineering_service"
    CAPABILITY_FACADE = "capability_facade"
    APPLICATION_SERVICE = "application_service"
    EXTENSION = "extension"


class ComponentIdentity:
    """Immutable identity of an event source/target (Part 2 §2.2.2)."""

    __slots__ = ("_component_type", "_component_name", "_instance_id", "_version")

    def __init__(
        self,
        component_type: ComponentType,
        component_name: str,
        instance_id: uuid.UUID | None = None,
        version: SemanticVersion | None = None,
    ) -> None:
        if not isinstance(component_type, ComponentType):
            raise TypeError(
                f"component_type must be ComponentType, got "
                f"{type(component_type).__name__}"
            )
        if not isinstance(component_name, str) or not component_name:
            raise ValueError("component_name must be a non-empty string")
        if instance_id is not None and not isinstance(instance_id, uuid.UUID):
            raise TypeError(
                f"instance_id must be UUID or None, got {type(instance_id).__name__}"
            )
        if version is not None and not isinstance(version, SemanticVersion):
            raise TypeError(
                f"version must be SemanticVersion or None, got {type(version).__name__}"
            )
        object.__setattr__(self, "_component_type", component_type)
        object.__setattr__(self, "_component_name", component_name)
        object.__setattr__(self, "_instance_id", instance_id)
        object.__setattr__(
            self, "_version", version if version is not None else SemanticVersion(1, 0, 0)
        )

    # --- immutability ---------------------------------------------------
    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("ComponentIdentity is immutable")

    # --- accessors ------------------------------------------------------
    @property
    def component_type(self) -> ComponentType:
        return self._component_type

    @property
    def component_name(self) -> str:
        return self._component_name

    @property
    def instance_id(self) -> uuid.UUID | None:
        return self._instance_id

    @property
    def version(self) -> SemanticVersion:
        return self._version

    # --- equality / hash ------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ComponentIdentity):
            return NotImplemented
        return (
            self._component_type == other._component_type
            and self._component_name == other._component_name
            and self._instance_id == other._instance_id
            and self._version == other._version
        )

    def __hash__(self) -> int:
        return hash(
            (
                self._component_type,
                self._component_name,
                self._instance_id,
                self._version,
            )
        )

    # --- serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "componentType": self._component_type.value,
            "componentName": self._component_name,
            "instanceId": str(self._instance_id) if self._instance_id is not None else None,
            "version": str(self._version),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComponentIdentity":
        raw_type = data.get("componentType")
        if raw_type is None:
            raise ValueError("ComponentIdentity.componentType is required")
        try:
            component_type = ComponentType(raw_type)
        except ValueError as exc:
            raise ValueError(f"Invalid componentType: {raw_type!r}") from exc
        raw_version = data.get("version")
        version = SemanticVersion.parse(raw_version) if raw_version is not None else None
        raw_instance = data.get("instanceId")
        instance_id = uuid.UUID(raw_instance) if raw_instance is not None else None
        return cls(
            component_type=component_type,
            component_name=data.get("componentName") or "",
            instance_id=instance_id,
            version=version,
        )

    def __repr__(self) -> str:
        return (
            f"ComponentIdentity(type={self._component_type.value}, "
            f"name={self._component_name!r}, "
            f"instanceId={self._instance_id}, version={self._version})"
        )


__all__ = ["ComponentType", "ComponentIdentity"]
