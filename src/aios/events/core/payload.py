"""
EventPayload (Part 2 §2.2.6).

The payload MUST be:
  * an immutable value object (INV-EVT-012, deep immutability),
  * JSON-serializable (INV-EVT-010; no binary blobs, functions, or cycles),
  * free of base-contract fields (INV-EVT-011: no correlationId,
    causationId, eventId, timestamp, or other base fields).

Per INV-EVT-009, payload schemas MUST NOT contain optional fields without
explicit defaults; all fields are required or have documented defaults. The
core model does not hard-code per-event-type payload schemas (those are
defined via the EventTypeRegistry / schema registry, a later component).
Instead, the core payload is a generic immutable container of
JSON-serializable data, supporting both structured sub-schemas and ad-hoc
payloads via the governed extension point.
"""

from __future__ import annotations

import copy
import json
import types
from typing import Any, Iterator, Mapping

from aios.events.core.serialization import _canonical_json_bytes


class EventPayload:
    """Immutable, JSON-serializable event payload (Part 2 §2.2.6)."""

    __slots__ = ("_frozen", "_view")

    # Base-contract field names that MUST NOT appear in a payload (INV-EVT-011).
    _FORBIDDEN_KEYS = frozenset(
        {
            "eventId",
            "event_id",
            "eventType",
            "event_type",
            "eventVersion",
            "event_version",
            "timestamp",
            "timestampMonotonic",
            "timestamp_monotonic",
            "correlationId",
            "correlation_id",
            "causationId",
            "causation_id",
            "source",
            "target",
            "priority",
            "category",
            "checksum",
            "payload",
        }
    )

    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise TypeError(f"payload data must be a mapping, got {type(data).__name__}")
        data = dict(data)
        self._validate_keys(data)
        self._validate_json_safe(data)
        # Deep-freeze into an immutable structure (INV-EVT-012 deep immutability),
        # and keep a one-time reconstructed plain-dict view for read access.
        object.__setattr__(self, "_frozen", _deep_freeze(data))
        object.__setattr__(self, "_view", self._rebuild_view(self._frozen))

    # --- immutability ---------------------------------------------------
    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("EventPayload is immutable")

    # --- validation -----------------------------------------------------
    @staticmethod
    def _validate_keys(data: Mapping[str, Any]) -> None:
        for key in data:
            if not isinstance(key, str):
                raise TypeError(f"payload keys must be strings, got {type(key).__name__}")
            if key in EventPayload._FORBIDDEN_KEYS:
                raise ValueError(
                    f"Payload MUST NOT contain base-contract field {key!r} "
                    f"(INV-EVT-011)."
                )

    @staticmethod
    def _validate_json_safe(data: Any) -> None:
        """Ensure the payload is JSON-serializable (INV-EVT-010)."""
        try:
            json.dumps(data, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Payload MUST be JSON-serializable (INV-EVT-010): {exc}"
            ) from exc

    # --- frozen <-> view ------------------------------------------------
    @staticmethod
    def _deep_freeze_one(value: Any) -> Any:
        return _deep_freeze(value)

    @staticmethod
    def _rebuild_view(frozen: Any) -> Any:
        if isinstance(frozen, tuple):
            # A frozen mapping is encoded as a sorted tuple of (key, frozen_value)
            # pairs. Rebuild as an immutable Mapping proxy so callers cannot
            # mutate the payload through the accessor (INV-EVT-012 deep immut).
            # Check if it's a mapping encoding (all items are 2-tuples with string keys).
            if all(
                isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
                for item in frozen
            ):
                return types.MappingProxyType(
                    {k: EventPayload._rebuild_view(v) for k, v in frozen}
                )
            # Otherwise it's a frozen list/tuple - recurse on elements.
            return tuple(EventPayload._rebuild_view(v) for v in frozen)
        return frozen

    # --- accessors ------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._view.get(key, default)

    def items(self) -> Iterator[tuple[str, Any]]:
        return iter(self._view.items())

    def keys(self) -> Iterator[str]:
        return iter(self._view.keys())

    def values(self) -> Iterator[Any]:
        return iter(self._view.values())

    def __contains__(self, key: object) -> bool:
        return key in self._view

    def __len__(self) -> int:
        return len(self._view)

    def __iter__(self) -> Iterator[str]:
        return iter(self._view)

    def __getitem__(self, key: str) -> Any:
        return self._view[key]

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the underlying data."""
        # Convert mappingproxy to dict to avoid deepcopy issues
        def _to_dict(obj):
            if isinstance(obj, types.MappingProxyType):
                return {k: _to_dict(v) for k, v in obj.items()}
            if isinstance(obj, tuple):
                return tuple(_to_dict(v) for v in obj)
            if isinstance(obj, list):
                return [_to_dict(v) for v in obj]
            if isinstance(obj, frozenset):
                return frozenset(_to_dict(v) for v in obj)
            return obj
        return _to_dict(self._view)

    # --- equality / hash ------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventPayload):
            return NotImplemented
        return self._frozen == other._frozen

    def __hash__(self) -> int:
        # Hash over canonical JSON for stable, order-independent hashing.
        return hash(_canonical_json_bytes(self._view))

    def __repr__(self) -> str:
        return f"EventPayload({self._view!r})"


def _deep_freeze(data: Any) -> Any:
    """Recursively freeze into immutable structures.

    Mappings become a *sorted* tuple of ``(key, frozen_value)`` pairs; lists
    become tuples; scalars are returned unchanged. The sorted tuple form gives
    stable equality and hashing for JSON-equivalent payloads (INV-EVT-013).
    """
    if isinstance(data, Mapping):
        return tuple(
            sorted(((k, _deep_freeze(v)) for k, v in data.items()), key=lambda kv: kv[0])
        )
    if isinstance(data, (list, tuple)):
        return tuple(_deep_freeze(v) for v in data)
    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    if isinstance(data, dict):
        return tuple(
            sorted(((k, _deep_freeze(v)) for k, v in data.items()), key=lambda kv: kv[0])
        )
    # Anything else is not JSON-safe; caught earlier by _validate_json_safe.
    return data


__all__ = ["EventPayload"]
