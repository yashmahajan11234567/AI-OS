"""
AI-OS Event Core Model (Part 2 — Event System Architecture).

This subpackage implements ONLY the foundational, immutable Event model
defined by AI-OS Architecture Specification Part 2 §2.2 (Event Base Contract).

It is intentionally isolated from the pre-architecture event scaffolding in
``aios.events.base`` / ``aios.events.types`` / ``aios.events.bus`` so that the
conformant core model can be developed and tested without modifying unrelated
code. Components that depend on the legacy scaffolding continue to work
unchanged. Later architecture components (EventBus, Subscription, Kernel,
EventTypeRegistry, schema registry) will build on this core model.

See ``architecture/Part02/ARCHITECTURE_SPEC_PART2.md`` §2.2 for the
authoritative contract.
"""

from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.priority import EventPriority
from aios.events.core.category import EventCategory
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.payload import EventPayload
from aios.events.core.errors import (
    EventValidationError,
    EventModelError,
)
from aios.events.core.serialization import (
    canonical_json,
    to_canonical_dict,
)

__all__ = [
    "Event",
    "ComponentIdentity",
    "ComponentType",
    "EventPriority",
    "EventCategory",
    "EventType",
    "SemanticVersion",
    "EventPayload",
    "EventValidationError",
    "EventModelError",
    "canonical_json",
    "to_canonical_dict",
]
