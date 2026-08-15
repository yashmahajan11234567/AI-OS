"""
EventPriority (Part 2 §2.2.3).

Fixed, ordered priority model. Numeric values define dispatch precedence:
lower numeric value = higher priority (dispatched first).

    CRITICAL   = 0   // Kernel lifecycle, fatal errors, security events
    HIGH       = 1   // Workflow control, retry/exhaustion, RCA results
    NORMAL     = 2   // Standard SDLC events — default
    LOW        = 3   // Telemetry, metrics, heartbeats
    BACKGROUND = 4   // Maintenance, consolidation, cleanup

These five levels are fixed by the architecture; new levels are NOT invented
by the core model.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class EventPriority(IntEnum):
    """Immutable, ordered event priority (Part 2 §2.2.3)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

    @classmethod
    def from_int(cls, value: int) -> "EventPriority":
        try:
            return cls(value)
        except ValueError as exc:
            valid = ", ".join(str(m.value) for m in cls)
            raise ValueError(
                f"Invalid EventPriority {value!r}; must be one of [{valid}]"
            ) from exc

    @classmethod
    def from_name(cls, name: str) -> "EventPriority":
        try:
            return cls[name]
        except KeyError as exc:
            valid = ", ".join(m.name for m in cls)
            raise ValueError(
                f"Invalid EventPriority name {name!r}; must be one of [{valid}]"
            ) from exc

    @property
    def value_int(self) -> int:
        return int(self.value)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"EventPriority.{self.name}"


__all__ = ["EventPriority"]
