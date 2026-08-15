"""
Errors raised by the Event core model.

Invalid event construction MUST fail validation rather than silently creating
an invalid Event (Part 2 EVT-DG / INV-EVT-*; task requirement #15).
"""

from __future__ import annotations

from typing import Any


class EventModelError(Exception):
    """Base error for the Event core model."""


class EventRegistryError(EventModelError):
    """Raised by the EventTypeRegistry / EventTypeRegistration layer.

    Covers registration rejection (duplicate, malformed, reserved-prefix
    violation per INV-ET-004 / INV-EXT-003 / INV-EXT-004), lifecycle violations,
    and lookup of invalid EventType input. Reuses the EventModelError base so
    it participates in the existing error hierarchy without redesign.
    """


class EventValidationError(EventModelError):
    """Raised when Event construction or deserialization fails validation.

    Aggregates one or more field-level errors so that callers receive a
    complete list of violations rather than failing on the first one.
    """

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors if errors is not None else [message]

    def __str__(self) -> str:
        if len(self.errors) <= 1:
            return super().__str__()
        joined = "\n  - ".join(self.errors)
        return f"{self.args[0]}:\n  - {joined}"


__all__ = ["EventModelError", "EventValidationError", "EventRegistryError"]
