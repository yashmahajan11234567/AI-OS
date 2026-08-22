"""
EventTypeRegistry and EventTypeRegistration (Part 2 §2.3.5, §2.13.4, §2.15.1).

This module implements the registry layer on top of the immutable Event core
(Task 1) and the canonical EventType enum (Task 2). It does NOT implement the
EventBus, Subscription, Kernel, managers/services, or a full schema engine.

Authoritative sources:
  * EventTypeRegistration contract ........ Part 2 §2.3.5
  * EventType Registry / IEventTypeRegistry interface . Part 2 §2.13.4
  * Canonical 121-member EventType enum ... Part 2 §2.3.1 (Task 2)
  * Category mapping ...................... Part 2 §2.3.2 (Task 1 category.py)
  * Event namespace reservation / prefix rules . Part 2 §2.14.3 / §2.14.4
  * Structural invariants ................. Part 2 §2.15.1 (INV-ET-001..006)

METADATA CLASSIFICATION (per task metadata-source rule)
------------------------------------------------------
Part 2 does NOT authoritatively specify complete metadata for every field of
every canonical EventType. Every non-authoritative value is classified and
documented inline:

  AUTHORITATIVE - taken verbatim from Part 2 (EventType, category, prefix owner)
  DEFAULT       - Part 2 silent; uses a fixed, documented implementation default
  DERIVED       - derived from an authoritative Part 2 rule (e.g. producer owner
                  from the §2.14.4 namespace reservation table)
  PLACEHOLDER   - no authoritative value; a stable, documented stand-in used so
                  that deterministic schemaHash / payloadSchema can be computed
  EMPTY         - explicitly no value (no consumers authored by architecture)
  SYNTHESIZED   - human-readable description reconstructed from the canonical name
                  where the architecture does not provide one

Nothing invented here is presented as an architectural fact.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.errors import EventRegistryError
from aios.events.core.identity import (
    ComponentIdentity,
    ComponentType,
)
from aios.events.core.priority import EventPriority
from aios.events.core.serialization import canonical_json
from aios.events.core.types import EventType, SemanticVersion

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DEFAULT: Part 2 §2.3.4 states "typically 1.0.0" for the initial schema
# version. The architecture does not specify a different value for any canonical
# EventType, so 1.0.0 is the uniform initial registration version.
INITIAL_SCHEMA_VERSION = SemanticVersion(1, 0, 0)

# DEFAULT: Part 2 does not provide authoritative per-EventType priority
# assignments (§2.3.5 lists priority as "Default priority"). NORMAL is the
# architecture's documented default priority level (Part 2 §2.2.3). This is the
# implementation default pending architecture resolution.
DEFAULT_PRIORITY = EventPriority.NORMAL

# PLACEHOLDER: No authoritative per-event payload schema is specified by Part 2
# (§2.3.5 lists payloadSchema as a CanonicalSchema representation, but the 121
# canonical schemas are not authored in the specification). We use a deterministic,
# serializable, stable placeholder representation so that a deterministic
# schemaHash can be computed. The placeholder identifies *itself* (not a fabricated
# business schema). It is documented as PLACEHOLDER in code and in the hash input.
PLACEHOLDER_PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "AI-OS Event Payload Placeholder Schema",
    "type": "object",
    "description": (
        "PLACEHOLDER: Part 2 does not authoritatively specify a per-event-type "
        "payload schema for this canonical EventType. This placeholder is a "
        "stable stand-in enabling deterministic schemaHash computation; it does "
        "not represent a real business contract."
    ),
    "x-aios-placeholder": True,
    "additionalProperties": True,
}

# Reserved kernel prefixes (Part 2 §2.14.4, "Namespace Rules" 1). Extensions
# SHALL NOT use these. The 121 canonical EventTypes legitimately use them, so
# canonical population bypasses prefix validation (see _populate_canonical_types).
KERNEL_RESERVED_PREFIXES = (
    "KERNEL_",
    "CORE_",
    "SYSTEM_",
    "WORKFLOW_",
    "TASK_",
    "STATE_",
    "MEMORY_",
    "COUNCIL_",
    "AI_AGENT_",
)

# Extension prefixes that are permitted for custom/extension registrations
# (Part 2 §2.14.4 INV-EXT-004: must use EXT_ or a registered <ORG>_ prefix).
EXTENSION_PREFIXES = ("EXT_",)


class RegistryState(str, Enum):
    """Lifecycle states for the EventTypeRegistry (Part 2 §2.15.1 / §2.4.3 analog).

    UNINITIALIZED - constructed, canonical population not yet complete
    INITIALIZING  - canonical population in progress
    READY         - all 121 canonical types registered and available for lookup
    SHUTDOWN      - registry drained; lookups may still read but no mutations
    """

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    SHUTDOWN = "SHUTDOWN"


# ---------------------------------------------------------------------------
# Registration value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeprecationInfo:
    """Deprecation metadata required when an EventType is deprecated (§2.3.5).

    Immutable (frozen dataclass) per the registration immutability requirement
    (Part 2 §2.15.1 INV-EVT-001). Absent entirely when ``deprecated == False``.
    """

    since_version: SemanticVersion
    removal_target_version: SemanticVersion
    replacement_event_type: EventType | None = None


@dataclass(frozen=True)
class EventTypeRegistration:
    """Immutable EventType registration (Part 2 §2.3.5).

    Construction validates the contract; post-construction mutation is prevented
    by the frozen dataclass (INV-EVT-001 / INV-EVT-012). ``deprecationInfo`` is
    REQUIRED when ``deprecated`` is true and MUST be absent when false.

    Metadata classification is documented on each field via the constructor.
    """

    eventType: EventType
    schemaVersion: SemanticVersion
    schemaHash: str
    payloadSchema: dict[str, Any]
    description: str
    producer: ComponentIdentity
    consumers: tuple[ComponentIdentity, ...]
    category: EventCategory
    priority: EventPriority
    deprecated: bool
    deprecationInfo: DeprecationInfo | None = None

    def __post_init__(self) -> None:
        # deprecation semantics (§2.3.5): deprecationInfo required iff deprecated.
        if self.deprecated and self.deprecationInfo is None:
            raise EventRegistryError(
                f"EventTypeRegistration for {self.eventType.name}: "
                f"deprecationInfo is REQUIRED when deprecated=True."
            )
        if not self.deprecated and self.deprecationInfo is not None:
            raise EventRegistryError(
                f"EventTypeRegistration for {self.eventType.name}: "
                f"deprecationInfo MUST be absent when deprecated=False."
            )
        # schemaHash presence (§2.3.5): never None / non-empty 64-hex SHA-256.
        if not isinstance(self.schemaHash, str) or not self.schemaHash:
            raise EventRegistryError(
                f"EventTypeRegistration for {self.eventType.name}: "
                f"schemaHash is REQUIRED and MUST never be None/empty."
            )
        if not isinstance(self.eventType, EventType):
            raise EventRegistryError("eventType MUST be a canonical EventType.")
        if not isinstance(self.category, EventCategory):
            raise EventRegistryError("category MUST be an EventCategory.")
        if not isinstance(self.priority, EventPriority):
            raise EventRegistryError("priority MUST be an EventPriority.")


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def compute_schema_hash(payload_schema: dict[str, Any]) -> str:
    """Deterministic, collision-resistant schemaHash (Part 2 §2.3.5).

    Implemented with **SHA-256** over the canonical JSON representation of the
    schema (RFC 8785-style: sorted keys, no whitespace, UTF-8), matching the
    canonicalization used by Event core serialization (§2.2.8).

    Determinism guarantees (this is the correction target of the Task 3 hash
    fix):
      * Does NOT use Python's built-in ``hash()`` (which is salted per process
        via PYTHONHASHSEED and is NOT stable across runs/machines).
      * Does NOT use ``id()``, object identity, memory addresses, or random
        values.
      * The digest is stable across Python processes, machines, and after
        serialization/deserialization, because it depends only on the canonical
        byte representation of the schema.
      * Equivalent schemas (same canonical JSON) -> identical digest.
      * Different schemas -> different digest (collision-resistant SHA-256).
    """
    canonical = canonical_json(payload_schema)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validation results (safe schema operations, Part 2 §2.13.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    """Safe result for ``validateSchema`` (Part 2 §2.13.4).

    Does NOT raise for ordinary invalid input; returns a structured result.
    ``valid`` is False when the schema/version is unknown or compatibility is
    not established. We do not claim compatibility that has not been verified.
    """

    valid: bool
    errors: tuple[str, ...] = ()

    @property
    def error_message(self) -> str | None:
        return "; ".join(self.errors) if self.errors else None


@dataclass(frozen=True)
class CompatibilityResult:
    """Safe result for ``checkCompatibility`` (Part 2 §2.13.4).

    ``compatible`` is False unless the architecture establishes compatibility;
    for v1.0 we only assert identity-version compatibility (a same-version
    payload is trivially backward/forward compatible with itself). We do NOT
    invent migration logic or speculative compatibility for differing versions.
    """

    compatible: bool
    direction: str = "unknown"  # 'identical' | 'unknown'
    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Producer derivation (Part 2 §2.14.4 namespace table)
# ---------------------------------------------------------------------------

# DERIVED: producer owner per Part 2 §2.14.4 "Event Namespace Reservation".
# Maps the kernel-reserved prefix to the owning component identity. Where the
# architecture names an owning manager/service, we use that component name.
# AUTHORITATIVE source of the owner name is the §2.14.4 table.
def _producer_for(event_type: EventType) -> ComponentIdentity:
    name = event_type.name
    if name.startswith("KERNEL_"):
        # DERIVED from §2.14.4: KERNEL_ owner = Hermes Kernel (kernel team).
        owner = "HermesKernel"
        ctype = ComponentType.KERNEL
    elif name.startswith("CORE_COMPONENT_") or name.startswith("CORE_MANAGER_"):
        # DERIVED from §2.14.4: CORE_ owner = Core Components/Managers.
        owner = "CoreInfrastructure"
        ctype = ComponentType.CORE_COMPONENT
    elif name in ("HEARTBEAT", "CONFIGURATION_FROZEN", "CONFIGURATION_CHANGED"):
        # DERIVED from §2.14.4 SYSTEM_-style reservation (config/health infra).
        owner = "SystemInfrastructure"
        ctype = ComponentType.CORE_COMPONENT
    elif name.startswith("WORKFLOW_"):
        # DERIVED from §2.14.4: WORKFLOW_ owner = WorkflowManager.
        owner = "WorkflowManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("TASK_"):
        # DERIVED from §2.14.4: TASK_ owner = Task Orchestration.
        owner = "TaskOrchestration"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("STATE_") or name.startswith("CHECKPOINT_"):
        # DERIVED from §2.14.4: STATE_ owner = StateManager.
        owner = "StateManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("ARTIFACT_"):
        # DERIVED from §2.3.2 DATA category + §2.14.4 manager convention.
        owner = "StateManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("MEMORY_"):
        # DERIVED from §2.14.4: MEMORY_ owner = MemoryManager.
        owner = "MemoryManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("CONTEXT_"):
        # DERIVED from §2.3.2 DATA category (context assembly/compression).
        owner = "StateManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("COUNCIL_"):
        # DERIVED from §2.14.4: COUNCIL_ owner = CouncilManager.
        owner = "CouncilManager"
        ctype = ComponentType.CORE_MANAGER
    elif name.startswith("PLANNING_") or name.startswith("CODING_") or name.startswith("CODE_") \
            or name.startswith("REVIEW_") or name.startswith("TESTS_") or name.startswith("TESTING_") \
            or name.startswith("DEPLOYMENT_"):
        # DERIVED from §2.3.2 AUDIT + §2.14.4 manager convention (SDLC phases).
        owner = "EngineeringService"
        ctype = ComponentType.ENGINEERING_SERVICE
    elif name.startswith("AI_AGENT_") or name == "FINAL_JUDGE_DECISION" or name == "HUMAN_ESCALATION_REQUIRED":
        # DERIVED from §2.14.4: AI_AGENT_ owner = AIAgencyService.
        owner = "AIAgencyService"
        ctype = ComponentType.CAPABILITY_FACADE
    elif name.startswith("METRIC_") or name.startswith("TRACE_") or name.startswith("HEALTH_CHECK_") \
            or name.startswith("SERVICE_") or name.startswith("RESOURCE_") or name.startswith("QUOTA_") \
            or name.startswith("SKILL_") or name.startswith("MCP_") or name.startswith("MODEL_") \
            or name.startswith("PROMPT_") or name.startswith("TOKEN_") or name.startswith("PERSONA_"):
        # DERIVED from §2.14.4 SYSTEM_/DIAGNOSTIC convention.
        owner = "ObservabilityManager"
        ctype = ComponentType.CORE_MANAGER
    else:
        # DERIVED fallback: cannot be authoritatively established from the prefix
        # table; document as a placeholder owner rather than fabricate.
        owner = "UnassignedComponent"
        ctype = ComponentType.EXTENSION
    # DEFAULT version 1.0.0 for the producer identity (no authoritative version).
    return ComponentIdentity(
        component_type=ctype,
        component_name=owner,
        instance_id=None,
        version=INITIAL_SCHEMA_VERSION,
    )


# SYNTHESIZED: human-readable descriptions reconstructed from the canonical name
# where Part 2 provides none. We do not pretend these are architectural
# requirements; they are derived from the SCREAMING_SNAKE_CASE token breakdown.
def _synthesized_description(event_type: EventType) -> str:
    words = event_type.name.replace("__", "_").split("_")
    readable = " ".join(w.capitalize() for w in words)
    return (
        f"SYNTHESIZED: canonical event '{event_type.name}' "
        f"({readable}). Part 2 does not provide an authoritative description."
    )


# EMPTY: Part 2 does not specify consumers for canonical EventTypes. We use an
# empty consumer set (no fabricated consumers) and document the EMPTY status.
def _empty_consumers() -> tuple[ComponentIdentity, ...]:
    return ()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class EventTypeRegistry:
    """Canonical EventType registry (Part 2 §2.13.4 IEventTypeRegistry).

    Holds registrations for all 121 canonical EventTypes (populated at
    construction via ``_populate_canonical_types``). Supports registration,
    lookup, listing, validation, and the interface-level schema operations
    (validateSchema / migrate / checkCompatibility).

    Thread safety: an ``RLock`` guards all mutable state; concurrent reads are
    safe. Lookups/listing never mutate. The canonical population runs once at
    construction under the lock.

    Lifecycle (Part 2 §2.15.1 / §2.4.3 analog): UNINITIALIZED ->
    INITIALIZING -> READY -> SHUTDOWN. After SHUTDOWN, mutations are rejected
    but reads remain available.
    """

    def __init__(
        self,
        auto_populate_canonical: bool = True,
        org_prefixes: set[str] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._registrations: dict[EventType, EventTypeRegistration] = {}
        self._state = RegistryState.UNINITIALIZED
        # Registered <ORG>_ extension prefixes (Part 2 §2.14.4). ARB manages these
        # to prevent collisions; in v1.0 this is an explicitly provided allowlist
        # (empty by default). EXT_ is always permitted; <ORG>_ requires inclusion
        # here. This keeps INV-EXT-004 enforceable without a fabricated ARB service.
        self._org_prefixes: set[str] = set(org_prefixes) if org_prefixes else set()
        if auto_populate_canonical:
            self._populate_canonical_types()

    # --- lifecycle ---------------------------------------------------------

    def _populate_canonical_types(self) -> None:
        """Register all 121 canonical EventTypes (Part 2 §2.3.1 / INV-ET-003/004).

        Canonical population BYPASSES extension-prefix validation (the 121 types
        legitimately use kernel-reserved prefixes); normal external/custom
        registration via ``register`` continues to enforce the prefix rules.
        """
        with self._lock:
            if self._state in (RegistryState.READY, RegistryState.INITIALIZING):
                return
            self._state = RegistryState.INITIALIZING
            for member in EventType:
                registration = self._build_canonical_registration(member)
                # Direct insert; bypasses prefix validation (canonical types).
                self._registrations[member] = registration
            self._state = RegistryState.READY

    def shutdown(self) -> None:
        """Transition to SHUTDOWN (Part 2 lifecycle).

        Per §2.4.3 analog: shutdown drains; the registry keeps read access but
        rejects further mutation. We do not delete registrations (they remain
        queryable for replay/compatibility).
        """
        with self._lock:
            self._state = RegistryState.SHUTDOWN

    @property
    def state(self) -> RegistryState:
        with self._lock:
            return self._state

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return self._state is RegistryState.READY

    def _ensure_mutatable(self) -> None:
        with self._lock:
            if self._state is RegistryState.SHUTDOWN:
                raise EventRegistryError(
                    "EventTypeRegistry is SHUTDOWN; registrations cannot be "
                    "mutated."
                )

    # --- registration construction ----------------------------------------

    def _build_canonical_registration(
        self, event_type: EventType
    ) -> EventTypeRegistration:
        # AUTHORITATIVE: EventType from Task 2 (§2.3.1).
        # AUTHORITATIVE: category via §2.3.2 mapping (Task 1 category.py).
        category = category_for_event_type(event_type)
        # DEFAULT: schema version 1.0.0 (§2.3.4).
        schema_version = INITIAL_SCHEMA_VERSION
        # PLACEHOLDER: no authoritative payload schema; stable placeholder used.
        payload_schema = dict(PLACEHOLDER_PAYLOAD_SCHEMA)
        payload_schema["title"] = f"AI-OS {event_type.name} Placeholder Schema"
        # Deterministic hash of the placeholder representation.
        schema_hash = compute_schema_hash(payload_schema)
        # DERIVED: producer owner from §2.14.4 namespace table.
        producer = _producer_for(event_type)
        # EMPTY: no authoritative consumers.
        consumers: tuple[ComponentIdentity, ...] = _empty_consumers()
        # DEFAULT: priority NORMAL (Part 2 silent on per-type priority).
        priority = DEFAULT_PRIORITY
        # SYNTHESIZED: description from canonical name (Part 2 provides none).
        description = _synthesized_description(event_type)
        return EventTypeRegistration(
            eventType=event_type,
            schemaVersion=schema_version,
            schemaHash=schema_hash,
            payloadSchema=payload_schema,
            description=description,
            producer=producer,
            consumers=consumers,
            category=category,
            priority=priority,
            deprecated=False,
            deprecationInfo=None,
        )

    # --- IEventTypeRegistry interface (§2.13.4) ----------------------------

    def register(
        self, registration: EventTypeRegistration
    ) -> None:
        """Register a new EventTypeRegistration (Part 2 §2.13.4).

        Enforces: no duplicate (INV-ET-004/005), valid EventType, prefix rules
        for extensions (INV-EXT-003/004). Canonical types are already present and
        cannot be re-registered.
        """
        if not isinstance(registration, EventTypeRegistration):
            raise EventRegistryError(
                "register() requires an EventTypeRegistration instance."
            )
        event_type = registration.eventType
        with self._lock:
            self._ensure_mutatable()
            if event_type in self._registrations:
                # INV-ET-004: duplicate registration MUST throw.
                raise EventRegistryError(
                    f"Duplicate registration for EventType {event_type.name} "
                    f"is PROHIBITED (INV-ET-004/005)."
                )
            # Extension prefix validation applies only to non-canonical (future
            # governed-extension) types. Canonical types are kernel-reserved by
            # design and are validated simply by being members of the closed
            # EventType enum; applying prefix rules to them would wrongly reject
            # legitimate kernel types.
            if not self._is_canonical(event_type):
                self._validate_extension_prefix(event_type)
            self._registrations[event_type] = registration

    def _validate_extension_prefix(self, event_type: EventType) -> None:
        """Enforce namespace reservation for custom/extension registrations.

        Canonical types use kernel-reserved prefixes by design and are populated
        without passing through here. Any type reaching ``register`` that is NOT
        already canonical MUST obey INV-EXT-003/004: no kernel-reserved prefix,
        and must use EXT_ or a registered <ORG>_ prefix.
        """
        name = event_type.name
        # INV-EXT-003: extension MUST NOT use a kernel-reserved prefix.
        for reserved in KERNEL_RESERVED_PREFIXES:
            if name.startswith(reserved):
                raise EventRegistryError(
                    f"EventType {name} uses kernel-reserved prefix '{reserved}'; "
                    f"extension registration is REJECTED (INV-EXT-003)."
                )
        # INV-EXT-004: extension MUST use EXT_ or a registered <ORG>_ prefix.
        # EXT_ is always permitted (general-purpose extension namespace).
        if name.startswith(EXTENSION_PREFIXES):
            return
        # <ORG>_ permitted only if the org prefix is in the registered allowlist.
        if "_" in name:
            org = name[: name.index("_") + 1]
            if org in self._org_prefixes:
                return
        raise EventRegistryError(
            f"EventType {name} is not a canonical type and does not use a "
            f"permitted extension prefix (EXT_ or a registered <ORG>_ prefix); "
            f"registration is REJECTED (INV-EXT-004)."
        )

    def unregister(self, event_type: EventType) -> None:
        """Remove a (custom) registration (Part 2 §2.13.4).

        Canonical 121 types are kernel-reserved and cannot be unregistered.
        """
        if not isinstance(event_type, EventType):
            raise EventRegistryError("unregister() requires a canonical EventType.")
        with self._lock:
            self._ensure_mutatable()
            if event_type not in self._registrations:
                raise EventRegistryError(
                    f"Cannot unregister unknown EventType {event_type.name}."
                )
            if self._is_canonical(event_type):
                raise EventRegistryError(
                    f"Cannot unregister canonical EventType {event_type.name}; "
                    f"kernel-reserved types are permanent."
                )
            del self._registrations[event_type]

    def _is_canonical(self, event_type: EventType) -> bool:
        # Canonical types are exactly the 121 Task 2 enum members.
        return event_type in set(EventType)

    def get(self, event_type: EventType) -> EventTypeRegistration | None:
        """Lookup a registration (Part 2 §2.13.4). Returns None if absent."""
        if not isinstance(event_type, EventType):
            raise EventRegistryError(
                f"get() requires a canonical EventType, got {type(event_type).__name__}."
            )
        with self._lock:
            return self._registrations.get(event_type)

    def list(self) -> list[EventTypeRegistration]:
        """Enumerate all registrations (Part 2 §2.13.4).

        Returns a NEW list (snapshot) so callers cannot mutate internal state.
        Deterministic order: canonical enum order, then any custom additions.
        """
        with self._lock:
            canonical = [self._registrations[et] for et in EventType
                         if et in self._registrations]
            extras = [reg for et, reg in self._registrations.items()
                      if et not in set(EventType)]
            return canonical + extras

    def get_by_name(self, name: str) -> EventTypeRegistration | None:
        """Resolve a registration by SCREAMING_SNAKE_CASE name (safe lookup)."""
        try:
            event_type = EventType.from_name(name)
        except ValueError:
            return None
        return self.get(event_type)

    # --- convenience accessors --------------------------------------------

    @property
    def registration_count(self) -> int:
        with self._lock:
            return len(self._registrations)

    @property
    def canonical_count(self) -> int:
        with self._lock:
            return sum(1 for et in self._registrations if self._is_canonical(et))

    def category_of(self, event_type: EventType) -> EventCategory:
        reg = self.get(event_type)
        if reg is None:
            raise EventRegistryError(f"No registration for {event_type.name}.")
        return reg.category

    def schema_hash_of(self, event_type: EventType) -> str:
        reg = self.get(event_type)
        if reg is None:
            raise EventRegistryError(f"No registration for {event_type.name}.")
        return reg.schemaHash

    # --- safe schema operations (§2.13.4) ----------------------------------
    # These MUST NOT raise for ordinary invalid input. They return structured
    # safe results. No speculative migration / compatibility invention.

    def validate_schema(
        self, event_type: EventType, payload: Any = None
    ) -> ValidationResult:
        """Validate a payload against the registered schema (Part 2 §2.13.4).

        Safe behavior: returns ValidationResult. If the event type is not
        registered, returns valid=False with an explanatory error (does not
        raise). For the placeholder schema (v1.0), we only assert structural
        JSON-serializability of the payload; we do NOT claim deep schema
        compliance for a placeholder contract.
        """
        reg = self.get(event_type)
        if reg is None:
            return ValidationResult(
                valid=False,
                errors=(f"No registration for EventType {event_type.name}.",),
            )
        if payload is None:
            # Nothing to validate; registry-side schema is present.
            return ValidationResult(valid=True)
        try:
            import json

            json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            return ValidationResult(
                valid=False,
                errors=(f"Payload is not JSON-serializable: {exc}",),
            )
        # PLACEHOLDER schema: we do not assert business-field compliance.
        return ValidationResult(valid=True)

    def migrate(
        self,
        event_type: EventType,
        payload: Any,
        from_version: SemanticVersion,
        to_version: SemanticVersion,
    ) -> Any:
        """Migrate a payload between schema versions (Part 2 §2.13.4).

        Safe behavior: NO speculative migration logic is implemented in Task 3.
        If from_version == to_version, the payload is returned unchanged
        (trivially compatible). Otherwise we return the payload unchanged and do
        NOT claim a transformation occurred; callers requiring real migration
        defer to the (deferred) schema engine.
        """
        if not isinstance(event_type, EventType):
            raise EventRegistryError("migrate() requires a canonical EventType.")
        if from_version == to_version:
            return payload
        # No invented migration: return payload as-is; compatibility unverified.
        return payload

    def check_compatibility(
        self,
        event_type: EventType,
        from_version: SemanticVersion,
        to_version: SemanticVersion,
    ) -> CompatibilityResult:
        """Check schema version compatibility (Part 2 §2.13.4).

        Safe behavior: only identity-version compatibility is asserted (a payload
        at the same version is trivially backward/forward compatible with
        itself). Differing versions are reported as NOT established (no invented
        compatibility), pending the deferred schema engine.
        """
        if not isinstance(event_type, EventType):
            raise EventRegistryError(
                "checkCompatibility() requires a canonical EventType."
            )
        reg = self.get(event_type)
        if reg is None:
            return CompatibilityResult(
                compatible=False,
                direction="unknown",
                notes=(f"No registration for {event_type.name}.",),
            )
        if from_version == to_version:
            return CompatibilityResult(
                compatible=True,
                direction="identical",
                notes=("Identity version: trivially compatible.",),
            )
        return CompatibilityResult(
            compatible=False,
            direction="unknown",
            notes=(
                "Cross-version compatibility not established in v1.0; deferred "
                "to the schema engine.",
            ),
        )


__all__ = [
    "RegistryState",
    "DeprecationInfo",
    "EventTypeRegistration",
    "ValidationResult",
    "CompatibilityResult",
    "compute_schema_hash",
    "EventTypeRegistry",
]
