"""
Serialization primitives for the Event core model (Part 2 §2.2.8).

This module provides the low-level canonicalization and checksum helpers used
by ``Event``. It does NOT import ``Event`` (to avoid a cycle); the ``Event``
class composes these primitives.

Canonical JSON (INV-EVT-007, INV-EVT-013, §2.2.8): deterministic,
RFC 8785-style — sorted keys, no whitespace, no ``nan``/``infinity``.
Used both for the wire/dict format and as the explicit input to the checksum.

Checksum (INV-EVT-007): SHA-256 of the canonical JSON of the payload.

UUID format (§2.2.8): lowercase hex with hyphens.
Timestamp format (§2.2.8): ISO 8601 UTC, nanoseconds, ``Z`` suffix.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Produce canonical JSON (sorted keys, no whitespace) per Part 2 §2.2.8.

    ``allow_nan=False`` rejects float ``nan``/``inf`` which are not valid JSON.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _canonical_json_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def compute_checksum(payload_repr: Any) -> str:
    """Compute SHA-256 hex checksum over canonical JSON of the payload.

    Per INV-EVT-007 the checksum is SHA-256 of the canonical JSON *payload*
    (sorted keys, no whitespace). ``payload_repr`` is the payload's canonical
    dict form.

    Returns lowercase hex (64 chars).
    """
    digest = hashlib.sha256(_canonical_json_bytes(payload_repr))
    return digest.hexdigest()


def is_valid_checksum_format(checksum: str) -> bool:
    """Validate that ``checksum`` is a 64-char lowercase hex SHA-256 string."""
    if not isinstance(checksum, str):
        return False
    if len(checksum) != 64:
        return False
    try:
        int(checksum, 16)
    except ValueError:
        return False
    return checksum == checksum.lower()


def to_canonical_dict(event: Any) -> dict[str, Any]:
    """Compose the canonical dict for an Event-like object.

    Field order: base fields first (alphabetical, per §2.2.8), then ``payload``
    field. ``event`` MUST expose the typed accessors defined by the base
    contract (eventId, eventType, ... checksum). Used by ``Event.to_dict``.
    """
    return {
        "category": event.category.value if hasattr(event.category, "value") else event.category,
        "checksum": event.checksum,
        "correlationId": str(event.correlationId),
        "causationId": str(event.causationId) if event.causationId is not None else None,
        "eventId": str(event.eventId),
        "eventType": event.eventType.value if hasattr(event.eventType, "value") else str(event.eventType),
        "eventVersion": str(event.eventVersion),
        "payload": event.payload.to_dict(),
        "priority": event.priority.value if hasattr(event.priority, "value") else int(event.priority),
        "source": event.source.to_dict(),
        "target": event.target.to_dict() if event.target is not None else None,
        "timestamp": event.timestamp,
        "timestampMonotonic": event.timestampMonotonic,
    }


__all__ = [
    "canonical_json",
    "_canonical_json_bytes",
    "compute_checksum",
    "is_valid_checksum_format",
    "to_canonical_dict",
]
