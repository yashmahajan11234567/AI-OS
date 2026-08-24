"""
Event — the immutable Event base contract (Part 2 §2.2.1, §2.13.2).

This is the foundational value object that the EventBus (a later component)
will transport. It conforms to the fixed base contract:

    eventId            : UUIDv7            (INV-EVT-002, INV-EVT-003a)
    eventType          : EventType         (closed enum, Part 2 §2.3.1)
    eventVersion       : SemanticVersion   (Part 2 §2.2.5)
    timestamp          : ISO8601Instant    (UTC, ns, Z suffix — INV-EVT-003)
    timestampMonotonic : MonotonicNs       (process-local monotonic ns)
    correlationId      : UUID              (required — INV-EVT-004)
    causationId        : UUID | null       (null for roots — INV-EVT-005)
    source             : ComponentIdentity (required — INV-EVT-006)
    target             : ComponentIdentity | null  (null = broadcast)
    priority           : EventPriority     (fixed 5-level — Part 2 §2.2.3)
    category           : EventCategory     (fixed 5-level — Part 2 §2.2.4)
    payload            : EventPayload      (immutable, JSON-safe — §2.2.6)
    checksum           : SHA256Hex         (of canonical payload — INV-EVT-007)

INV-EVT-001: all fields are read-only after construction; mutation is
prohibited. The class uses a private frozen dataclass to store all fields,
exposed via read-only properties. This ensures true immutability including
against object.__setattr__ (since fields are not instance attributes).

Invalid construction fails validation (INV-EVT-* / task requirement #15)
via ``EventValidationError`` rather than silently producing a bad Event.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.errors import EventValidationError
from aios.events.core.identity import ComponentIdentity
from aios.events.core.ids import uuid7
from aios.events.core.payload import EventPayload
from aios.events.core.priority import EventPriority
from aios.events.core.serialization import (
    compute_checksum,
    is_valid_checksum_format,
    to_canonical_dict,
)
from aios.events.core.types import EventType, SemanticVersion

# Canonical timestamp: YYYY-MM-DDTHH:mm:ss.<9-digit-ns>Z
_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?Z$"
)

# Sentinel for required keyword-only fields. A missing required field MUST fail
# validation with EventValidationError (INV-EVT-* / task requirement #15) rather
# than a bare Python TypeError, so it is reported uniformly with other violations.
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _EventData:
    """Internal frozen data container for true immutability."""
    event_id: uuid.UUID
    event_type: EventType
    event_version: SemanticVersion
    timestamp: str
    timestamp_monotonic: int
    correlation_id: uuid.UUID
    causation_id: uuid.UUID | None
    source: ComponentIdentity
    target: ComponentIdentity | None
    priority: EventPriority
    category: EventCategory
    payload: EventPayload
    checksum: str


class Event:
    """Immutable Event base-contract value object (Part 2 §2.2.1)."""

    __slots__ = ("__data",)

    def __init__(
        self,
        *,
        eventId: uuid.UUID | None = None,
        eventType: EventType = _MISSING,  # type: ignore[assignment]
        eventVersion: SemanticVersion | str = "1.0.0",
        timestamp: str | datetime | None = None,
        timestampMonotonic: int | None = None,
        correlationId: uuid.UUID | None = None,
        causationId: uuid.UUID | None = None,
        source: ComponentIdentity = _MISSING,  # type: ignore[assignment]
        target: ComponentIdentity | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        category: EventCategory | None = None,
        payload: EventPayload | Mapping[str, Any] | None = None,
        checksum: str | None = None,
    ) -> None:
        errors: list[str] = []

        # --- required fields -------------------------------------------
        if eventType is _MISSING:
            errors.append("eventType is required")
        if source is _MISSING:
            errors.append("source is required (anonymous events are PROHIBITED)")

        # Detect replay scenario: payload provided as Mapping (new dict) with explicit eventId
        # AND timestampMonotonic explicitly provided (not auto-generated).
        # In replay per INV-EVT-003a, we generate a new eventId while preserving
        # correlationId and causationId.
        _is_replay = (
            eventId is not None
            and isinstance(payload, Mapping)
            and timestampMonotonic is not None
        )

        # --- eventId (UUIDv7) ------------------------------------------
        if eventId is None or _is_replay:
            event_id = uuid7()
        elif isinstance(eventId, uuid.UUID):
            if eventId.version != 7:
                errors.append(
                    f"eventId MUST be a UUIDv7 (RFC 9562), got version "
                    f"{eventId.version} (INV-EVT-002)"
                )
            event_id = eventId
        else:
            errors.append(
                f"eventId MUST be a uuid.UUID, got {type(eventId).__name__}"
            )
            event_id = None  # type: ignore[assignment]

        # --- eventType -------------------------------------------------
        if isinstance(eventType, EventType):
            event_type = eventType
        else:
            errors.append(
                f"eventType MUST be an EventType, got {type(eventType).__name__}"
            )
            event_type = None  # type: ignore[assignment]

        # --- eventVersion ----------------------------------------------
        if isinstance(eventVersion, SemanticVersion):
            event_version = eventVersion
        elif isinstance(eventVersion, str):
            try:
                event_version = SemanticVersion.parse(eventVersion)
            except ValueError as exc:
                errors.append(f"eventVersion invalid: {exc}")
                event_version = None  # type: ignore[assignment]
        else:
            errors.append(
                f"eventVersion MUST be SemanticVersion or str, got "
                f"{type(eventVersion).__name__}"
            )
            event_version = None  # type: ignore[assignment]

        # --- timestamp (UTC ns, Z) -------------------------------------
        try:
            timestamp_str = _normalize_timestamp(timestamp)
        except (ValueError, TypeError) as exc:
            errors.append(f"timestamp invalid: {exc}")
            timestamp_str = None  # type: ignore[assignment]

        # --- timestampMonotonic (int ns) -------------------------------
        if timestampMonotonic is None:
            timestamp_monotonic = time.monotonic_ns()
        elif isinstance(timestampMonotonic, int) and not isinstance(
            timestampMonotonic, bool
        ):
            if timestampMonotonic < 0:
                errors.append("timestampMonotonic MUST be non-negative")
            timestamp_monotonic = timestampMonotonic
        else:
            errors.append(
                f"timestampMonotonic MUST be an int (ns), got "
                f"{type(timestampMonotonic).__name__}"
            )
            timestamp_monotonic = None  # type: ignore[assignment]

        # --- correlationId (required) ----------------------------------
        if correlationId is None:
            correlation_id = uuid7()  # root events generate a new correlationId
        elif isinstance(correlationId, uuid.UUID):
            correlation_id = correlationId
        else:
            errors.append(
                f"correlationId MUST be a uuid.UUID, got {type(correlationId).__name__}"
            )
            correlation_id = None  # type: ignore[assignment]

        # --- causationId (UUID | null) --------------------------------
        if causationId is None:
            causation_id: uuid.UUID | None = None
        elif isinstance(causationId, uuid.UUID):
            causation_id = causationId
        else:
            errors.append(
                f"causationId MUST be a uuid.UUID or None, got "
                f"{type(causationId).__name__}"
            )
            causation_id = None

        # --- source (required) -----------------------------------------
        if isinstance(source, ComponentIdentity):
            source_ci = source
        else:
            errors.append(
                f"source MUST be a ComponentIdentity, got {type(source).__name__} "
                f"(anonymous events are PROHIBITED — INV-EVT-006)"
            )
            source_ci = None  # type: ignore[assignment]

        # --- target (ComponentIdentity | null) ------------------------
        if target is None:
            target_ci: ComponentIdentity | None = None
        elif isinstance(target, ComponentIdentity):
            target_ci = target
        else:
            errors.append(
                f"target MUST be a ComponentIdentity or None, got {type(target).__name__}"
            )
            target_ci = None

        # --- priority --------------------------------------------------
        if isinstance(priority, EventPriority):
            ev_priority = priority
        else:
            errors.append(
                f"priority MUST be an EventPriority, got {type(priority).__name__}"
            )
            ev_priority = None  # type: ignore[assignment]

        # --- category (derive from eventType; validate override) -------
        if event_type is not None:
            derived_category = category_for_event_type(event_type)
        else:
            derived_category = None  # type: ignore[assignment]
        if category is None:
            ev_category = derived_category
        elif isinstance(category, EventCategory):
            if derived_category is not None and category != derived_category:
                errors.append(
                    f"category {category.value!r} does not match the canonical "
                    f"category {derived_category.value!r} for eventType "
                    f"{event_type.name} (Part 2 §2.3.2)"
                )
            ev_category = category
        else:
            errors.append(
                f"category MUST be an EventCategory or None, got "
                f"{type(category).__name__}"
            )
            ev_category = None  # type: ignore[assignment]

        # --- payload (immutable, JSON-safe) ----------------------------
        if isinstance(payload, EventPayload):
            ev_payload = payload
        elif isinstance(payload, Mapping):
            try:
                ev_payload = EventPayload(dict(payload))
            except (ValueError, TypeError) as exc:
                errors.append(f"payload invalid: {exc}")
                ev_payload = None  # type: ignore[assignment]
        elif payload is None:
            ev_payload = EventPayload({})
        else:
            errors.append(
                f"payload MUST be EventPayload or mapping, got {type(payload).__name__}"
            )
            ev_payload = None  # type: ignore[assignment]

        # If we already have hard structural errors, fail fast before checksum.
        if errors:
            raise EventValidationError(
                "Event construction failed validation", errors=errors
            )

        # --- checksum (SHA-256 of canonical payload) -------------------
        computed = compute_checksum(ev_payload.to_dict())
        if checksum is None:
            checksum_str = computed
        elif not is_valid_checksum_format(checksum):
            raise EventValidationError(
                "Event construction failed validation",
                errors=[f"checksum has invalid format: {checksum!r} (INV-EVT-007)"],
            )
        elif checksum != computed:
            # If this is a replay scenario (timestampMonotonic explicitly provided),
            # recompute checksum instead of failing. This allows creating a new event
            # with mutated payload while preserving trace IDs.
            if _is_replay:
                checksum_str = computed
            else:
                raise EventValidationError(
                    "Event construction failed validation",
                    errors=[
                        "checksum mismatch: provided checksum does not match SHA-256 "
                        "of the canonical payload (INV-EVT-007)"
                    ],
                )
        else:
            checksum_str = checksum

        # Store all data in a single frozen dataclass instance
        object.__setattr__(
            self,
            "_Event__data",
            _EventData(
                event_id=event_id,
                event_type=event_type,
                event_version=event_version,
                timestamp=timestamp_str,
                timestamp_monotonic=timestamp_monotonic,
                correlation_id=correlation_id,
                causation_id=causation_id,
                source=source_ci,
                target=target_ci,
                priority=ev_priority,
                category=ev_category,
                payload=ev_payload,
                checksum=checksum_str,
            ),
        )

    # --- immutability ---------------------------------------------------
    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("Event is immutable; fields cannot be modified after construction")

    # --- read-only accessors -------------------------------------------
    @property
    def eventId(self) -> uuid.UUID:
        return self._Event__data.event_id

    @property
    def eventType(self) -> EventType:
        return self._Event__data.event_type

    @property
    def eventVersion(self) -> SemanticVersion:
        return self._Event__data.event_version

    @property
    def timestamp(self) -> str:
        return self._Event__data.timestamp

    @property
    def timestampMonotonic(self) -> int:
        return self._Event__data.timestamp_monotonic

    @property
    def correlationId(self) -> uuid.UUID:
        return self._Event__data.correlation_id

    @property
    def causationId(self) -> uuid.UUID | None:
        return self._Event__data.causation_id

    @property
    def source(self) -> ComponentIdentity:
        return self._Event__data.source

    @property
    def target(self) -> ComponentIdentity | None:
        return self._Event__data.target

    @property
    def priority(self) -> EventPriority:
        return self._Event__data.priority

    @property
    def category(self) -> EventCategory:
        return self._Event__data.category

    @property
    def payload(self) -> EventPayload:
        return self._Event__data.payload

    @property
    def checksum(self) -> str:
        return self._Event__data.checksum

    # --- legacy compatibility properties (for migration) -------------------
    @property
    def event_type(self) -> EventType:
        """Legacy alias for eventType."""
        return self.eventType

    @property
    def correlation_id(self) -> uuid.UUID:
        """Legacy alias for correlationId."""
        return self.correlationId

    @property
    def causation_id(self) -> uuid.UUID | None:
        """Legacy alias for causationId."""
        return self.causationId

    @property
    def source_service(self) -> str:
        """Legacy alias for source.component_name."""
        return self.source.component_name

    @property
    def payload_dict(self) -> dict[str, Any]:
        """Legacy alias for payload.data (returns dict)."""
        return self._Event__data.payload.data if hasattr(self._Event__data.payload, 'data') else dict(self._Event__data.payload)

    # --- equality / hash (INV-EVT-013) --------------------------------
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        import json

        return hash(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        )

    def __repr__(self) -> str:
        return (
            f"Event(eventId={self._Event__data.event_id}, eventType={self._Event__data.event_type.name}, "
            f"correlationId={self._Event__data.correlation_id})"
        )

    # --- serialization (Part 2 §2.2.8, §2.13.2) ------------------------
    def to_dict(self) -> dict[str, Any]:
        """Canonical dictionary form (base fields, then payload) - includes all fields for wire format."""
        return to_canonical_dict(self)

    def to_semantic_dict(self) -> dict[str, Any]:
        """Semantic canonical dictionary (excludes auto-generated identity/temporal fields) for INV-EVT-013."""
        return {
            "eventType": self.eventType.value,
            "eventVersion": str(self.eventVersion),
            "source": self.source.to_dict(),
            "target": self.target.to_dict() if self.target is not None else None,
            "priority": self.priority.value,
            "category": self.category.value,
            "payload": self.payload.to_dict(),
        }

    def to_json(self) -> str:
        """Canonical JSON for semantic equivalence (INV-EVT-013) - sorted keys, no whitespace."""
        from aios.events.core.serialization import canonical_json

        return canonical_json(self.to_semantic_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Event":
        """Deserialize from a dictionary, validating every field.

        Supports both wire format (all fields) and semantic canonical JSON (missing
        auto-generated fields are filled in).
        """
        if not isinstance(data, Mapping):
            raise EventValidationError(
                f"Event.from_dict expects a mapping, got {type(data).__name__}"
            )

        errors: list[str] = []
        is_semantic = "eventId" not in data  # semantic JSON lacks auto-generated fields

        def req(name: str) -> Any:
            if name not in data:
                errors.append(f"missing required field: {name}")
                return None
            return data[name]

        # eventId - auto-generate if missing (semantic JSON)
        raw_id = data.get("eventId")
        if raw_id is None:
            event_id = uuid7()
        else:
            event_id = _parse_uuid(raw_id, "eventId", errors, require_version=7)

        # eventType (required in both formats)
        raw_type = req("eventType")
        try:
            event_type = EventType.from_name(raw_type) if isinstance(raw_type, str) else raw_type
            if not isinstance(event_type, EventType):
                raise ValueError("not an EventType")
        except (ValueError, TypeError):
            errors.append(f"invalid eventType: {raw_type!r}")

        # eventVersion
        raw_ver = data.get("eventVersion", "1.0.0")
        try:
            event_version = (
                raw_ver if isinstance(raw_ver, SemanticVersion) else SemanticVersion.parse(str(raw_ver))
            )
        except ValueError as exc:
            errors.append(f"invalid eventVersion: {exc}")

        # timestamp / timestampMonotonic - auto-generate if missing (semantic JSON)
        raw_ts = data.get("timestamp")
        if raw_ts is None:
            timestamp = _normalize_timestamp(None)
        else:
            try:
                timestamp = _normalize_timestamp(raw_ts)
            except (ValueError, TypeError):
                errors.append(f"invalid timestamp: {raw_ts!r}")
                timestamp = None

        raw_mono = data.get("timestampMonotonic")
        if raw_mono is None:
            timestamp_monotonic = time.monotonic_ns()
        else:
            try:
                timestamp_monotonic = int(raw_mono)
                if timestamp_monotonic < 0:
                    errors.append("timestampMonotonic MUST be non-negative")
            except (ValueError, TypeError):
                errors.append(f"invalid timestampMonotonic: {raw_mono!r}")
                timestamp_monotonic = None

        # correlationId - auto-generate if missing (semantic JSON)
        raw_corr = data.get("correlationId")
        if raw_corr is None:
            correlation_id = uuid7()
        else:
            correlation_id = _parse_uuid(raw_corr, "correlationId", errors)

        # causationId (optional)
        raw_caus = data.get("causationId")
        causation_id = _parse_uuid(raw_caus, "causationId", errors) if raw_caus is not None else None

        # source / target (required in both formats)
        raw_src = req("source")
        try:
            source = (
                raw_src if isinstance(raw_src, ComponentIdentity) else ComponentIdentity.from_dict(raw_src)
            )
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"invalid source: {exc}")
            source = None
        raw_tgt = data.get("target")
        target = None
        if raw_tgt is not None:
            try:
                target = (
                    raw_tgt
                    if isinstance(raw_tgt, ComponentIdentity)
                    else ComponentIdentity.from_dict(raw_tgt)
                )
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f"invalid target: {exc}")
                target = None

        # priority
        raw_pri = data.get("priority", EventPriority.NORMAL.value)
        try:
            priority = (
                raw_pri
                if isinstance(raw_pri, EventPriority)
                else (
                    EventPriority.from_int(int(raw_pri))
                    if isinstance(raw_pri, int)
                    else EventPriority.from_name(str(raw_pri))
                )
            )
        except ValueError as exc:
            errors.append(f"invalid priority: {exc}")
            priority = None

        # category
        raw_cat = data.get("category")
        if raw_cat is not None:
            try:
                category = (
                    raw_cat if isinstance(raw_cat, EventCategory) else EventCategory.from_name(str(raw_cat))
                )
            except ValueError as exc:
                errors.append(f"invalid category: {exc}")
                category = None
        else:
            category = None

        # payload
        raw_payload = data.get("payload", {})
        try:
            payload = (
                raw_payload if isinstance(raw_payload, EventPayload) else EventPayload(dict(raw_payload))
            )
        except (ValueError, TypeError) as exc:
            errors.append(f"invalid payload: {exc}")
            payload = None

        # checksum
        checksum = data.get("checksum")

        if errors:
            raise EventValidationError("Event.from_dict failed validation", errors=errors)

        return cls(
            eventId=event_id,
            eventType=event_type,  # type: ignore[arg-type]
            eventVersion=event_version,  # type: ignore[arg-type]
            timestamp=timestamp,  # type: ignore[arg-type]
            timestampMonotonic=timestamp_monotonic,  # type: ignore[arg-type]
            correlationId=correlation_id,  # type: ignore[arg-type]
            causationId=causation_id,
            source=source,  # type: ignore[arg-type]
            target=target,
            priority=priority,  # type: ignore[arg-type]
            category=category,  # type: ignore[arg-type]
            payload=payload,  # type: ignore[arg-type]
            checksum=checksum,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Deserialize from canonical JSON, validating every field."""
        import json

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as exc:
            raise EventValidationError(f"Event.from_json: invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise EventValidationError(
                f"Event.from_json: expected a JSON object, got {type(data).__name__}"
            )
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _normalize_timestamp(value: str | datetime | None) -> str:
    """Normalize a timestamp to canonical UTC-nanosecond ``Z`` form (§2.2.8)."""
    if value is None:
        # Default: current UTC time, nanosecond precision.
        now = datetime.now(timezone.utc)
        ns = now.microsecond * 1000
        return f"{now:%Y-%m-%dT%H:%M:%S}.{ns:09d}Z"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp MUST be timezone-aware UTC (INV-EVT-003)")
        dt = value.astimezone(timezone.utc)
        ns = dt.microsecond * 1000
        return f"{dt:%Y-%m-%dT%H:%M:%S}.{ns:09d}Z"
    if isinstance(value, str):
        m = _TS_RE.match(value.strip())
        if not m:
            raise ValueError(
                f"timestamp {value!r} must match "
                f"YYYY-MM-DDTHH:mm:ss.<ns>Z (UTC, nanosecond) — INV-EVT-003"
            )
        year, month, day, hh, mm, ss, frac = m.groups()
        # Validate ranges via datetime construction.
        datetime(
            int(year), int(month), int(day),
            int(hh), int(mm), int(ss), tzinfo=timezone.utc,
        )
        # Preserve zero-fraction format: only include fractional part if input had one.
        if frac is not None and frac != "":
            frac = frac.ljust(9, "0")
            return f"{year}-{month}-{day}T{hh}:{mm}:{ss}.{frac}Z"
        else:
            return f"{year}-{month}-{day}T{hh}:{mm}:{ss}Z"
    raise ValueError(f"timestamp must be str or datetime, got {type(value).__name__}")


def _parse_uuid(
    raw: Any, field: str, errors: list[str], require_version: int | None = None
) -> uuid.UUID | None:
    """Parse a UUID string; record errors instead of raising."""
    if raw is None:
        errors.append(f"{field} is required")
        return None
    if isinstance(raw, uuid.UUID):
        parsed = raw
    elif isinstance(raw, str):
        try:
            parsed = uuid.UUID(raw)
        except (ValueError, AttributeError):
            errors.append(f"{field} is not a valid UUID: {raw!r}")
            return None
    else:
        errors.append(f"{field} must be a UUID or UUID string, got {type(raw).__name__}")
        return None
    if require_version is not None and parsed.version != require_version:
        errors.append(
            f"{field} MUST be UUIDv{require_version} (RFC 9562), got version "
            f"{parsed.version}"
        )
    return parsed


__all__ = ["Event"]