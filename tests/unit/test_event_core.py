"""
Focused tests for the AI-OS Event core model (Part 2 §2.2).

Run with:  pytest tests/unit/test_event_core.py
"""

from __future__ import annotations

import uuid

import pytest

from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.errors import EventValidationError
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion


# --- fixtures / helpers ---------------------------------------------------
def _source() -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.CORE_MANAGER,
        component_name="WorkflowManager",
        version=SemanticVersion(1, 0, 0),
    )


def _target() -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name="PlanningService",
        version=SemanticVersion(1, 2, 0),
    )


def _valid_kwargs(**overrides) -> dict:
    base = dict(
        eventType=EventType.TASK_CREATED,
        source=_source(),
        payload={"taskId": str(uuid.uuid4()), "title": "build"},
    )
    base.update(overrides)
    return base


def make_event(**overrides) -> Event:
    return Event(**_valid_kwargs(**overrides))


# --- 1. Valid Event construction ----------------------------------------
def test_valid_event_construction():
    ev = make_event()
    assert isinstance(ev.eventId, uuid.UUID)
    assert ev.eventType == EventType.TASK_CREATED
    assert ev.eventVersion == SemanticVersion(1, 0, 0)
    assert ev.priority == EventPriority.NORMAL
    assert ev.category == EventCategory.CONTROL
    assert ev.source.component_name == "WorkflowManager"
    assert ev.target is None  # broadcast by default
    assert ev.checksum is not None
    # correlation/causation sanity
    assert isinstance(ev.correlationId, uuid.UUID)
    assert ev.causationId is None  # root event


# --- 2. Missing required fields rejected ---------------------------------
def test_missing_required_fields_rejected():
    # eventType is required
    with pytest.raises(EventValidationError) as exc:
        Event(source=_source(), payload={})  # type: ignore[call-arg]
    assert any("eventType" in e for e in exc.value.errors)
    # source is required
    with pytest.raises(EventValidationError):
        Event(eventType=EventType.TASK_CREATED, payload={})  # type: ignore[arg-type]


# --- 3. Invalid field values rejected ------------------------------------
def test_invalid_field_values_rejected():
    bad_type = "not a real type"
    with pytest.raises(EventValidationError) as exc:
        Event(
            eventType=bad_type,  # type: ignore[arg-type]
            source=_source(),
            payload={},
        )
    assert any("eventType" in e for e in exc.value.errors)


# --- 4. Event immutability -----------------------------------------------
def test_event_immutability():
    ev = make_event()
    with pytest.raises(AttributeError):
        ev.priority = EventPriority.HIGH  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ev.category = EventCategory.AUDIT  # type: ignore[misc]


# --- 5. Attempted post-construction mutation fails -----------------------
def test_post_construction_mutation_fails():
    ev = make_event()
    with pytest.raises(AttributeError):
        object.__setattr__(ev, "_event_id", uuid.uuid4())
    with pytest.raises(AttributeError):
        ev._checksum = "x"  # type: ignore[attr-defined]


# --- 6. Event ID validation ----------------------------------------------
def test_event_id_validation():
    # UUIDv7 accepted
    v7 = uuid.UUID("018f6e2a-1c3d-7b4a-8c5e-9f1a2b3c4d5e")  # valid v7 layout
    ev = make_event(eventId=v7)
    assert ev.eventId == v7
    # Non-v7 rejected
    v4 = uuid.uuid4()  # version 4
    with pytest.raises(EventValidationError) as exc:
        make_event(eventId=v4)
    assert any("UUIDv7" in e for e in exc.value.errors)
    # Auto-generated when omitted
    ev2 = make_event()
    assert ev2.eventId.version == 7


# --- 7. Correlation ID handling ------------------------------------------
def test_correlation_id_handling():
    # Provided correlationId is preserved
    corr = uuid.uuid4()
    ev = make_event(correlationId=corr)
    assert ev.correlationId == corr
    # Auto-generated when omitted
    ev2 = make_event()
    assert isinstance(ev2.correlationId, uuid.UUID)
    # Invalid type rejected
    with pytest.raises(EventValidationError):
        make_event(correlationId="not-a-uuid")  # type: ignore[arg-type]


# --- 8. Causation ID handling --------------------------------------------
def test_causation_id_handling():
    # null for root events (default)
    ev = make_event()
    assert ev.causationId is None
    # Set to a valid UUID
    cause = uuid.uuid4()
    ev2 = make_event(causationId=cause)
    assert ev2.causationId == cause
    # Invalid type rejected
    with pytest.raises(EventValidationError):
        make_event(causationId="not-a-uuid")  # type: ignore[arg-type]


# --- 9. Event version handling -------------------------------------------
def test_event_version_handling():
    ev = make_event(eventVersion="2.3.1")
    assert ev.eventVersion == SemanticVersion(2, 3, 1)
    with pytest.raises(EventValidationError):
        make_event(eventVersion="not-a-version")


# --- 10. Priority handling ------------------------------------------------
def test_priority_handling():
    ev = make_event(priority=EventPriority.CRITICAL)
    assert ev.priority == EventPriority.CRITICAL
    assert ev.priority.value == 0
    # default NORMAL
    assert make_event().priority == EventPriority.NORMAL


# --- 11. Category handling ------------------------------------------------
def test_category_handling():
    ev = make_event()
    # derived from eventType per Part 2 §2.3.2
    assert ev.category == category_for_event_type(EventType.TASK_CREATED)
    # explicit matching category accepted
    ev2 = make_event(category=EventCategory.CONTROL)
    assert ev2.category == EventCategory.CONTROL
    # mismatched category rejected
    with pytest.raises(EventValidationError) as exc:
        make_event(category=EventCategory.AUDIT)
    assert any("category" in e for e in exc.value.errors)


# --- 12. Source/target handling ------------------------------------------
def test_source_target_handling():
    # source required
    with pytest.raises(EventValidationError):
        Event(eventType=EventType.TASK_CREATED, payload={})  # type: ignore[arg-type]
    # anonymous (non-ComponentIdentity) rejected
    with pytest.raises(EventValidationError):
        Event(eventType=EventType.TASK_CREATED, source="Kernel", payload={})  # type: ignore[arg-type]
    # target null and target set
    ev = make_event()
    assert ev.target is None
    ev2 = make_event(target=_target())
    assert ev2.target is not None
    assert ev2.target.component_name == "PlanningService"


# --- 13. Payload handling -------------------------------------------------
def test_payload_handling():
    ev = make_event(payload={"k": "v", "n": 1})
    assert ev.payload["k"] == "v"
    assert ev.payload["n"] == 1
    # empty payload allowed
    ev2 = make_event(payload={})
    assert len(ev2.payload) == 0
    # base-contract fields forbidden in payload
    with pytest.raises(EventValidationError):
        make_event(payload={"correlationId": str(uuid.uuid4())})
    # non-JSON-safe payload rejected
    with pytest.raises(EventValidationError):
        make_event(payload={"fn": lambda: 1})  # type: ignore[arg-type]


# --- 13b. Deep immutability of payload -----------------------------------
def test_payload_is_deeply_immutable():
    data = {"a": 1, "b": {"c": 2}, "d": [3, 4]}
    ev = make_event(payload=data)
    with pytest.raises((TypeError, AttributeError)):
        ev.payload["b"]["c"] = 99  # type: ignore[index]
    with pytest.raises((TypeError, AttributeError)):
        ev.payload["d"].append(5)  # type: ignore[attr-defined]


# --- 14. Checksum generation ---------------------------------------------
def test_checksum_generation():
    ev = make_event(payload={"x": 1})
    # checksum format: 64-char lowercase hex (SHA-256)
    assert len(ev.checksum) == 64
    assert ev.checksum == ev.checksum.lower()
    int(ev.checksum, 16)  # parseable hex
    # deterministic: same payload -> same checksum
    ev2 = make_event(payload={"x": 1})
    assert ev.checksum == ev2.checksum


# --- 15. Checksum validation ---------------------------------------------
def test_checksum_validation():
    ev = make_event(payload={"x": 1})
    # correct checksum accepted
    ev_ok = make_event(payload={"x": 1}, checksum=ev.checksum)
    assert ev_ok.checksum == ev.checksum
    # wrong checksum rejected
    with pytest.raises(EventValidationError) as exc:
        make_event(payload={"x": 2}, checksum=ev.checksum)
    assert any("checksum" in e for e in exc.value.errors)
    # malformed checksum rejected
    with pytest.raises(EventValidationError):
        make_event(payload={"x": 1}, checksum="deadbeef")


# --- 16. to_dict round trip ----------------------------------------------
def test_to_dict_round_trip():
    ev = make_event(target=_target(), causationId=uuid.uuid4(), priority=EventPriority.HIGH)
    d = ev.to_dict()
    assert d["eventType"] == "TASK_CREATED"
    assert d["priority"] == EventPriority.HIGH.value
    assert d["category"] == "control"
    assert d["target"]["componentName"] == "PlanningService"
    ev2 = Event.from_dict(d)
    assert ev2 == ev
    assert ev2.to_dict() == d


# --- 17. canonical JSON round trip ---------------------------------------
def test_canonical_json_round_trip():
    ev = make_event(target=_target(), causationId=uuid.uuid4())
    js = ev.to_json()
    assert "\n" not in js and " " not in js  # no whitespace
    ev2 = Event.from_json(js)
    assert ev2 == ev
    assert ev2.to_json() == js


# --- 18. from_dict rejects invalid data ----------------------------------
def test_from_dict_rejects_invalid_data():
    with pytest.raises(EventValidationError):
        Event.from_dict({"eventType": "NOPE", "source": {}, "timestamp": "x",
                         "timestampMonotonic": -1, "correlationId": "bad"})
    # missing required keys
    with pytest.raises(EventValidationError):
        Event.from_dict({"eventType": "TASK_CREATED"})


# --- 19. from_json rejects invalid data ----------------------------------
def test_from_json_rejects_invalid_data():
    with pytest.raises(EventValidationError):
        Event.from_json('{"eventType": "TASK_CREATED", "source": 123}')
    # malformed JSON
    with pytest.raises(EventValidationError):
        Event.from_json('{not json')


# --- 20. Serialization preserves all required fields ---------------------
def test_serialization_preserves_all_fields():
    corr = uuid.uuid4()
    caus = uuid.uuid4()
    ev = Event(
        eventType=EventType.STATE_CHANGED,
        source=_source(),
        target=_target(),
        correlationId=corr,
        causationId=caus,
        priority=EventPriority.LOW,
        payload={"delta": "x"},
        timestamp="2026-07-28T14:30:00.123456789Z",
        timestampMonotonic=987654321,
    )
    d = ev.to_dict()
    # all required base fields present
    for f in [
        "eventId", "eventType", "eventVersion", "timestamp",
        "timestampMonotonic", "correlationId", "causationId", "source",
        "target", "priority", "category", "payload", "checksum",
    ]:
        assert f in d, f"missing field {f}"
    assert d["correlationId"] == str(corr)
    assert d["causationId"] == str(caus)
    assert d["timestamp"] == "2026-07-28T14:30:00.123456789Z"
    assert d["timestampMonotonic"] == 987654321
    assert d["priority"] == EventPriority.LOW.value
    assert d["category"] == "data"  # STATE_CHANGED -> DATA
    # round-trip preserves exact values
    ev2 = Event.from_dict(d)
    assert ev2.correlationId == corr
    assert ev2.causationId == caus
    assert ev2.timestamp == "2026-07-28T14:30:00.123456789Z"


# --- Additional: timestamp normalization ---------------------------------
def test_timestamp_normalization():
    # datetime with tz -> canonical UTC ns Z
    from datetime import datetime, timezone
    dt = datetime(2026, 7, 28, 14, 30, 0, 123456, tzinfo=timezone.utc)
    ev = make_event(timestamp=dt)
    assert ev.timestamp == "2026-07-28T14:30:00.123456000Z"
    # naive datetime rejected (must be UTC-aware)
    with pytest.raises(EventValidationError):
        make_event(timestamp=datetime(2026, 7, 28, 14, 30, 0))
    # bad string rejected
    with pytest.raises(EventValidationError):
        make_event(timestamp="2026/07/28 14:30")


# --- Additional: EventType closed enum count -----------------------------
def test_event_type_catalog_complete():
    # Part 2 §2.3.1's enumeration defines 118 canonical event types (the prose
    # says "97"; we conform to the authoritative enumeration, not the prose).
    assert len(list(EventType)) == 118
    # base-contract-style names are normalized (str enum)
    assert EventType.TASK_COMPLETED.value == "TASK_COMPLETED"


# --- Additional: INV-EVT-013 canonical determinism -----------------------
def test_canonical_determinism():
    a = make_event(payload={"b": 1, "a": 2})
    b = make_event(payload={"a": 2, "b": 1})
    assert a.to_json() == b.to_json()


# ===========================================================================
# Reviewer-requested tests (TASK 1 FIX)
# ===========================================================================

# --- Replay scenario (INV-EVT-003a: new eventId, preserve correlation/
#     causation; original event MUST NOT be mutated). No replay engine is
#     implemented; this tests only the Event contract behavior. -------------
def test_replay_receives_new_event_id_and_preserves_trace():
    # A root/descendant event with a known correlation/causation chain.
    corr = uuid.uuid4()
    cause = uuid.uuid4()
    original = Event(
        eventType=EventType.WORKFLOW_STEP_COMPLETED,
        source=_source(),
        correlationId=corr,
        causationId=cause,
        payload={"step": 3},
    )
    original_id = original.eventId

    # Simulate a replay: serialize, then reconstruct a NEW event with a fresh
    # eventId (per INV-EVT-003a) while preserving correlation/causation for
    # trace continuity.
    d = original.to_dict()
    d.pop("eventId")  # force a new UUIDv7 (replay must not reuse ids)
    replayed = Event(**{**_dict_to_ctor(d)})

    assert replayed.eventId != original_id  # new id
    assert replayed.eventId.version == 7  # still UUIDv7
    assert replayed.correlationId == corr  # preserved exactly
    assert replayed.causationId == cause  # preserved exactly
    # Replayed event is otherwise semantically equivalent.
    assert replayed.eventType == original.eventType
    assert replayed.payload.to_dict() == original.payload.to_dict()


def test_replay_does_not_mutate_original():
    corr = uuid.uuid4()
    cause = uuid.uuid4()
    original = Event(
        eventType=EventType.TASK_CREATED,
        source=_source(),
        correlationId=corr,
        causationId=cause,
        payload={"title": "x"},
    )
    # Derive a replayed view from the original's dict; mutate the dict copy
    # before constructing to prove the original event is untouched.
    d = original.to_dict()
    d["payload"] = {"title": "mutated"}
    replayed = Event(**{**_dict_to_ctor(d)})
    assert replayed.payload.to_dict() == {"title": "mutated"}
    # Original remains immutable and unchanged.
    assert original.payload.to_dict() == {"title": "x"}
    assert original.eventId != replayed.eventId
    # And direct post-construction mutation is still prohibited.
    with pytest.raises(AttributeError):
        original.correlationId = uuid.uuid4()  # type: ignore[misc]


def test_replay_root_event_preserves_null_causation():
    # Root events have null causation; replay must preserve that exactly.
    corr = uuid.uuid4()
    original = Event(
        eventType=EventType.KERNEL_READY,
        source=ComponentIdentity(ComponentType.KERNEL, "HermesKernel",
                                 version=SemanticVersion(1, 0, 0)),
        correlationId=corr,
        causationId=None,
        payload={},
    )
    d = original.to_dict()
    d.pop("eventId")
    replayed = Event(**{**_dict_to_ctor(d)})
    assert replayed.eventId != original.eventId
    assert replayed.correlationId == corr
    assert replayed.causationId is None  # preserved: still a root


# --- Canonical JSON determinism (INV-EVT-013) -----------------------------
def test_canonical_json_deterministic_across_constructors():
    # Equivalent data built in different field order yields identical JSON.
    a = Event(
        eventType=EventType.TASK_CREATED,
        source=_source(),
        payload={"z": 1, "a": 2},
        priority=EventPriority.HIGH,
    )
    b = Event(
        eventType=EventType.TASK_CREATED,
        priority=EventPriority.HIGH,
        source=_source(),
        payload={"a": 2, "z": 1},
    )
    assert a.to_json() == b.to_json()


def test_canonical_json_payload_key_order_independent():
    # Payload key insertion order must not affect canonical JSON (sorted keys).
    x = make_event(payload={"alpha": 1, "beta": 2, "gamma": 3})
    y = make_event(payload={"gamma": 3, "alpha": 1, "beta": 2})
    assert x.to_json() == y.to_json()
    assert x.to_dict()["payload"] == y.to_dict()["payload"]


# --- Timestamp normalization edge cases (Part 2 §2.2.8) --------------------
def test_timestamp_string_accepts_full_nanosecond_precision():
    ev = make_event(timestamp="2026-07-28T14:30:00.123456789Z")
    assert ev.timestamp == "2026-07-28T14:30:00.123456789Z"


def test_timestamp_string_zero_fraction_accepted():
    ev = make_event(timestamp="2026-07-28T14:30:00Z")
    assert ev.timestamp == "2026-07-28T14:30:00Z"


def test_timestamp_string_sub_nanosecond_fraction_padded():
    # 3-digit (millisecond) fraction is right-padded to 9 digits.
    ev = make_event(timestamp="2026-07-28T14:30:00.123Z")
    assert ev.timestamp == "2026-07-28T14:30:00.123000000Z"


def test_timestamp_rejects_non_utc_suffix():
    # Missing Z / wrong zone rejected (must be UTC Z-suffix, INV-EVT-003).
    with pytest.raises(EventValidationError):
        make_event(timestamp="2026-07-28T14:30:00.123+02:00")
    with pytest.raises(EventValidationError):
        make_event(timestamp="2026-07-28T14:30:00.123")


def test_timestamp_rejects_out_of_range_components():
    with pytest.raises(EventValidationError):
        make_event(timestamp="2026-13-01T00:00:00Z")  # month 13 invalid
    with pytest.raises(EventValidationError):
        make_event(timestamp="2026-07-28T25:00:00Z")  # hour 25 invalid


def test_timestamp_datetime_converted_to_utc_ns():
    from datetime import datetime, timezone, timedelta

    # Non-UTC tzinfo is converted to UTC (INV-EVT-003: UTC output).
    tz_plus2 = timezone(timedelta(hours=2))
    dt = datetime(2026, 7, 28, 16, 30, 0, 0, tzinfo=tz_plus2)  # == 14:30 UTC
    ev = make_event(timestamp=dt)
    assert ev.timestamp == "2026-07-28T14:30:00.000000000Z"


# --- Empty payload behavior (Part 2 §2.2.6) --------------------------------
def test_empty_payload_is_valid():
    ev = make_event(payload={})
    assert len(ev.payload) == 0
    assert ev.payload.to_dict() == {}
    # checksum still computed over the empty payload
    assert len(ev.checksum) == 64


def test_empty_payload_round_trips():
    ev = make_event(payload={})
    d = ev.to_dict()
    ev2 = Event.from_dict(d)
    assert ev2.payload.to_dict() == {}
    assert ev2.checksum == ev.checksum


def test_payload_with_base_contract_key_rejected_empty_or_not():
    # Whether or not other fields present, a base-contract key is forbidden.
    with pytest.raises(EventValidationError):
        make_event(payload={"eventId": str(uuid.uuid4())})
    with pytest.raises(EventValidationError):
        make_event(payload={"correlationId": str(uuid.uuid4())})


# --- helper: canonical dict -> Event(**kwargs) ----------------------------
def _dict_to_ctor(d: dict) -> dict:
    """Convert an Event.to_dict() mapping into keyword args for Event()."""
    out: dict = {}
    if "eventId" in d:
        out["eventId"] = uuid.UUID(d["eventId"])
    out["eventType"] = EventType.from_name(d["eventType"])
    out["eventVersion"] = d.get("eventVersion", "1.0.0")
    out["timestamp"] = d["timestamp"]
    out["timestampMonotonic"] = d["timestampMonotonic"]
    out["correlationId"] = uuid.UUID(d["correlationId"])
    if d.get("causationId") is not None:
        out["causationId"] = uuid.UUID(d["causationId"])
    out["source"] = ComponentIdentity.from_dict(d["source"])
    if d.get("target") is not None:
        out["target"] = ComponentIdentity.from_dict(d["target"])
    out["priority"] = EventPriority.from_int(int(d["priority"]))
    out["category"] = EventCategory.from_name(d["category"])
    out["payload"] = d.get("payload", {})
    out["checksum"] = d.get("checksum")
    return out

