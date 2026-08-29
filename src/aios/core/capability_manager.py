"""
CapabilityManager — the Phase-4 (Execution) Core Manager for AI-OS Hermes Kernel.

CapabilityManager is the capability registry for the kernel. It implements the
ICoreManager Protocol (name / phase / dependencies / initialize / shutdown /
health_ready) so LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 4 (alphabetical within phase:
    CapabilityManager, WorkflowManager — deterministic per Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.capability``
    (Part 4 §4.8 names the identity ``kernel.capability``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.capability``, using the same precedent Task 9/10/11/12/13 established
    for ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health``
    / ``core.resource`` / ``core.security``), using the same "core_manager"
    metadata envelope
  * reads ``kernel.capability.*`` configuration from the frozen
    ConfigurationManager (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 15 mapping, same as Tasks 9–14): Part 4 §4.8.11 names events
like ``CapabilityRegisteredEvent`` / ``CapabilityDeprecatedEvent`` /
``CapabilityRemovedEvent`` / ``CapabilityInvocationEvent`` /
``CapabilityConflictEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1, Task 2). CapabilityManager does NOT invent
new EventTypes. The canonical mappings for the capability domain are (verified
against ``src/aios/events/core/types.py``):

  * Capability registered      -> EventType.SERVICE_STARTED
  * Capability removed         -> EventType.SERVICE_STOPPED
  * Capability invoked         -> EventType.SKILL_EXECUTED
  * Capability invocation error -> EventType.SKILL_FAILED

If a conceptual capability event has no canonical EventType equivalent, that
event emission is omitted rather than invented.

NOTE ON ``core.capability`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.8): Part 4 §4.8 names CapabilityManager's ServiceRegistry identity as
``kernel.capability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle``) and Task 10/11/12/13 resolved for StateManager,
StorageManager, HealthManager, ResourceManager, and SecurityManager. Per that
precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry identity is
``core.capability``. The configuration namespace read from C3 remains
``kernel.capability.*`` (Part 4 §4.8 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 4) is unchanged.

PHASE DEPENDENCY RULE: CapabilityManager is Phase 4. It declares ONLY Phase-1
LifecycleManager as a formal dependency:

    dependencies = ["LifecycleManager"]

It does NOT declare WorkflowManager, SecurityManager, StateManager, or any other
manager as a formal dependency. The (not-yet-implemented) WorkflowManager is a
same-phase sibling (declaring it would be rejected by LifecycleManager's
dependency validator LM-DEP-003 and would break kernel boot, since WorkflowManager
is not currently registered with LifecycleManager); the SecurityManager
authorization gate and StateManager registry backing are operational
relationships that are event-driven (via canonical EventBus), not lifecycle
dependency edges. C1–C4 are always-satisfied base dependencies handled by
LifecycleManager.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as the other Core Managers); these
# modules do not import ``aios.core.capability_manager`` at module scope, so
# there is no circular-import risk.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "CapabilityManager",
    "CapabilityRegistryEntry",
    "CapabilityManagerError",
    "get_capability_manager",
    "set_capability_manager",
    "reset_capability_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "CapabilityManager"
# Part 4 §4.8 names CapabilityManager's ServiceRegistry identity as
# ``kernel.capability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
# as ``core.lifecycle``) and Task 10/11/12/13 resolved for StateManager,
# StorageManager, HealthManager, ResourceManager, and SecurityManager. We follow
# that precedent: the compliant, INV-SR-NS-002-respecting ServiceRegistry id is
# ``core.capability``. The configuration namespace read from C3 remains
# ``kernel.capability.*`` (Part 4 §4.8 config schema), which is unaffected by the
# ServiceRegistry id.
_MANAGER_ID = "core.capability"
_PHASE = 4  # Phase 4 — "Execution"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 15 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–14):
#   * same-phase siblings (WorkflowManager) and cross-phase managers (e.g.
#     SecurityManager, StateManager) are NOT declared as dependencies — they
#     would be rejected by LifecycleManager's dependency validator (LM-DEP-003)
#     and could break kernel boot (WorkflowManager is not currently registered
#     with LifecycleManager). Deterministic alphabetical ordering (Phase 4:
#     CapabilityManager, WorkflowManager) already guarantees correct sequencing,
#     and the operational relationships (authorization gate, registry backing)
#     are event-driven (via canonical EventBus), not lifecycle dependency edges.
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_CAPABILITY_REGISTERED = EventType.SERVICE_STARTED
_CAPABILITY_REMOVED = EventType.SERVICE_STOPPED
_CAPABILITY_INVOKED = EventType.SKILL_EXECUTED
_CAPABILITY_INVOCATION_FAILED = EventType.SKILL_FAILED


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a dotted version string to a comparable int tuple (M8-T5).

    Returns ``(0,)`` for unparseable versions so they sort below any valid
    semver — per spec §16 rule 2, an unparseable-version challenger never
    displaces the first registrant.
    """
    if not version:
        return (0,)
    try:
        return tuple(int(part) for part in str(version).split("."))
    except ValueError:
        return (0,)


# ---------------------------------------------------------------------------
# Enumerations / value objects
# ---------------------------------------------------------------------------


class CapabilityState(str, Enum):  # noqa: UP042 -- matches sibling manager enums
    """Lifecycle state of a registered capability (Part 4 §4.8.2, extended for M8-T5)."""

    REGISTERED = "REGISTERED"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"
    REMOVED = "REMOVED"


class TrustLevel(str, Enum):
    """Trust level for capability precedence (M8-T5)."""

    BUILTIN = "builtin"
    TRUSTED = "trusted"
    TRUSTED_CONTEXTUAL = "trusted_contextual"
    UNTRUSTED = "untrusted"

    @classmethod
    def precedence(cls, level: str) -> int:
        """Return precedence value (higher = more trusted)."""
        mapping = {
            cls.BUILTIN: 4,
            cls.TRUSTED: 3,
            cls.TRUSTED_CONTEXTUAL: 2,
            cls.UNTRUSTED: 1,
        }
        return mapping.get(level, 0)


class AuthorityClassification(str, Enum):
    """Authority classification for capability (M8-T5, non-overridable defaults)."""

    AUTHORITATIVE = "authoritative"
    CONTEXTUAL = "contextual"
    ADVISORY = "advisory"
    ADVISORY_ONLY = "advisory_only"

    @classmethod
    def default_for_trust(cls, trust_level: str) -> str:
        """Default authority classification for a trust level."""
        if trust_level in (TrustLevel.BUILTIN, TrustLevel.TRUSTED):
            return cls.CONTEXTUAL
        return cls.ADVISORY


class CapabilityAvailability(str, Enum):
    """Availability status of a capability (M8-T5)."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class CapabilityRegistryEntry:
    """A registered capability (Part 4 §4.8.2 registry entry, extended for M8-T5)."""

    capability_id: str
    facade: str
    provider_id: str
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    state: CapabilityState = CapabilityState.REGISTERED
    security_context: dict[str, Any] = field(default_factory=dict)
    resource_profile: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    # M8-T5 extensions
    trust_level: str = TrustLevel.UNTRUSTED
    authority_classification: str = AuthorityClassification.ADVISORY
    adapter_binding: dict[str, Any] = field(default_factory=dict)
    operations: tuple[str, ...] = ()
    health_status: str = "unknown"  # unknown, healthy, degraded, unhealthy
    availability: str = CapabilityAvailability.UNAVAILABLE
    enabled: bool = True
    discovered_from: str = ""
    dependencies: tuple[str, ...] = ()
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry to a JSON-safe dict (Part 2 §2.2.8)."""
        return {
            "capability_id": self.capability_id,
            "facade": self.facade,
            "provider_id": self.provider_id,
            "provider_metadata": self.provider_metadata,
            "version": self.version,
            "state": self.state.value,
            "security_context": self.security_context,
            "resource_profile": self.resource_profile,
            "tags": list(self.tags),
            "trust_level": self.trust_level,
            "authority_classification": self.authority_classification,
            "adapter_binding": self.adapter_binding,
            "operations": list(self.operations),
            "health_status": self.health_status,
            "availability": self.availability,
            "enabled": self.enabled,
            "discovered_from": self.discovered_from,
            "dependencies": list(self.dependencies),
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CapabilityManagerError(Exception):
    """CapabilityManager failure (Part 4 §4.8.12).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` / ``ResourceManagerError`` /
    ``SecurityManagerError`` (Tasks 9/10/11/12/13/14).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}:"
                f" {self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# CapabilityManager
# ---------------------------------------------------------------------------


class CapabilityManager:
    """Phase-4 (Execution) capability registry for the Hermes Kernel.

    Provides the kernel capability-management surface:
    - Capability registration / deregistration (single registry; SI-CM-01).
    - Discovery by facade / tags / security level.
    - Invocation routing metadata resolution (returns the bound provider
      endpoint for a registered capability) and execution emission.
    - ICoreManager Core-Manager lifecycle (Task 15 — orchestrated by
      LifecycleManager).

    Architecture contract (mirrors StateManager / StorageManager / HealthManager
    / ResourceManager / SecurityManager):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel).
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
        adapter_factory: Any | None = None,
        security_manager: Any | None = None,
    ) -> None:
        """
        Initialize the Capability Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.

        M8-T5 extensions:
        - adapter_factory: AdapterFactory for instantiating capability adapters
        - security_manager: SecurityManager for capability spec validation gate
        """
        # C2/C3/C4 — injected via DI (Task 15).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.8).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 15).
        self._initialized = False
        self._registered_with_sr = False

        # Capability registry.
        self._registry: dict[str, CapabilityRegistryEntry] = {}
        self._registry_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._enforce_authorization = True
        self._reject_duplicate_provider = True

        # M8-T5: Adapter factory and security manager for capability hardening
        self._adapter_factory: Any | None = adapter_factory
        self._security_manager: Any | None = security_manager

        # M8-T5: Manifest configuration (populated in initialize)
        self._manifest_dir: str = "./config/capabilities"
        self._adapter_allowlist: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 15 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 4 — Execution, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.capability``; Part 4 §4.8 names
        ``kernel.capability`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors the sibling Core Managers' health_ready: ready by construction
        once the manager has completed its own initialization. Returns False
        before ``initialize()`` and after ``shutdown()``.
        """
        return self._initialized and self._event_bus is not None

    # ------------------------------------------------------------------
    # ICoreManager: initialization / shutdown
    # ------------------------------------------------------------------

    def _read_config_str(self, path: str, default: str) -> str:
        """Read a string config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_int(self, path: str, default: int) -> int:
        """Read an int config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 4 initialization (called by LifecycleManager).

        Follows the Core Manager pattern: reads ``kernel.capability.*``
        configuration from the frozen C3, registers this manager with the
        canonical ServiceRegistry (C2) as ``core.capability``, and marks the
        manager initialized/ready.

        M8-T5 extensions: reads capability manifest config, adapter allowlist.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._enforce_authorization = self._read_config_bool(
            "kernel.capability.enforceAuthorization", self._enforce_authorization
        )
        self._reject_duplicate_provider = self._read_config_bool(
            "kernel.capability.rejectDuplicateProvider", self._reject_duplicate_provider
        )

        # M8-T5: Read capability manifest configuration
        self._manifest_dir = self._read_config_str(
            "kernel.capability.manifestDir", "./config/capabilities"
        )
        adapter_allowlist_str = self._read_config_str("kernel.capability.adapterAllowlist", "")
        self._adapter_allowlist = tuple(
            adapter_allowlist_str.split(",") if adapter_allowlist_str else ()
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.capability``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"CapabilityManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 4 (reverse) shutdown (called by LifecycleManager).

        Clears the capability registry, marks ``core.capability`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear the capability registry.
        with self._registry_lock:
            self._registry.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("CapabilityManager shut down.")

    # ------------------------------------------------------------------
    # M8-T5: Dependency injection setters (kernel wires these post-construct)
    # ------------------------------------------------------------------

    def set_adapter_factory(self, adapter_factory: Any) -> None:
        """Set the AdapterFactory instance (M8-T5)."""
        self._adapter_factory = adapter_factory
        self._log_debug("AdapterFactory injected into CapabilityManager")

    def set_security_manager(self, security_manager: Any) -> None:
        """Set the SecurityManager instance (M8-T5)."""
        self._security_manager = security_manager
        self._log_debug("SecurityManager injected into CapabilityManager")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror sibling Core Manager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register CapabilityManager with the ServiceRegistry (C2, Part 4 §4.8).

        Registered as ``core.capability`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering CapabilityManager.")
            return
        try:
            await sr.register(
                self,
                service_id=_MANAGER_ID,
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "kind": "core_manager",
                    "manager": _NAME,
                    "phase": _PHASE,
                    "lifecycle_state": "INITIALIZED",
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.capability`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(
                f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}"
            )

    # ------------------------------------------------------------------
    # Business API — capability registry
    # ------------------------------------------------------------------

    def register(
        self,
        capability_id: str,
        facade: str,
        provider_id: str,
        *,
        provider_metadata: dict[str, Any] | None = None,
        version: str = "1.0.0",
        security_context: dict[str, Any] | None = None,
        resource_profile: dict[str, Any] | None = None,
        tags: tuple[str, ...] = (),
    ) -> CapabilityRegistryEntry:
        """Register a capability (Part 4 §4.8.3).

        Returns the created registry entry and emits the canonical
        ``SERVICE_STARTED`` event (mapping CapabilityRegisteredEvent, CONFLICT E.1).

        S5 (Terminal 2) — single-registry invariant. Capabilities may be
        registered by two paths (kernel ``_init_*`` helpers and the manifest
        loader). To prevent conflicting/asymmetric double-registration:
        - A re-registration with the SAME ``provider_id`` is treated as
          idempotent (returns the existing entry, no error) — legitimate
          registration from either path is preserved.
        - A registration whose ``capability_id`` is already claimed by a
          DIFFERENT ``provider_id`` is rejected (CM-DUP-001) — prevents one
          provider silently displacing another and preserves trust precedence.
        This mirrors the precedence semantics ``register_capability`` already
        enforces, so the two paths can no longer disagree.
        """
        existing = self._registry.get(capability_id)
        if existing is not None:
            if existing.provider_id == provider_id:
                # Idempotent re-registration from the other code path.
                self._log_debug(
                    f"Capability '{capability_id}' already registered by "
                    f"provider '{provider_id}'; treating as idempotent"
                )
                return existing
            if self._reject_duplicate_provider:
                raise CapabilityManagerError(
                    f"Capability '{capability_id}' already registered by provider "
                    f"'{existing.provider_id}'; conflicting provider '{provider_id}' rejected.",
                    rule_id="CM-DUP-001",
                )

        entry = CapabilityRegistryEntry(
            capability_id=capability_id,
            facade=facade,
            provider_id=provider_id,
            provider_metadata=dict(provider_metadata or {}),
            version=version,
            state=CapabilityState.REGISTERED,
            security_context=dict(security_context or {}),
            resource_profile=dict(resource_profile or {}),
            tags=tuple(tags),
            # Legacy (pre-M8-T5) capabilities are always resolvable once registered;
            # they carry no manifest-driven availability gating.
            availability=CapabilityAvailability.AVAILABLE,
        )
        with self._registry_lock:
            self._registry[capability_id] = entry

        self._emit_event(
            _CAPABILITY_REGISTERED,
            {
                "capability_id": capability_id,
                "facade": facade,
                "provider_id": provider_id,
                "version": version,
            },
        )
        self._log_debug(f"Registered capability: {capability_id} (facade={facade})")
        return entry

    # ------------------------------------------------------------------
    # M8-T5 — Capability Registry Hardening (extended business API)
    # ------------------------------------------------------------------

    def register_capability(self, spec: CapabilitySpec) -> CapabilityRegistryEntry:
        """
        Register a capability from a validated CapabilitySpec (M8-T5).

        This is the primary registration path for manifest-discovered capabilities.
        Enforces deterministic collision resolution per §16 precedence rules:
        trust_level > version > first-registered.

        Args:
            spec: Validated CapabilitySpec from CapabilityManifestLoader

        Returns:
            The created/updated CapabilityRegistryEntry

        Raises:
            CapabilityManagerError: If validation fails or collision resolution rejects
        """
        # Validate security context via SecurityManager gate
        if self._security_manager and hasattr(self._security_manager, "validate_capability_spec"):
            validation_result = self._security_manager.validate_capability_spec(spec)
            # CapabilitySpecValidationResult exposes .passed/.violations; accept a
            # legacy boolean or a .valid attribute too for robustness.
            gate_passed = getattr(validation_result, "passed", None)
            if gate_passed is None:
                gate_passed = getattr(validation_result, "valid", validation_result)
            if not gate_passed:
                violations = getattr(validation_result, "violations", None) or []
                detail = "; ".join(
                    str(getattr(v, "description", v)) for v in violations
                )
                raise CapabilityManagerError(
                    f"Capability '{spec.capability_id}' failed security validation: "
                    f"{detail or 'gate rejected the spec'}",
                    rule_id="CM-SEC-001",
                )

        # Deterministic collision resolution
        with self._registry_lock:
            existing = self._registry.get(spec.capability_id)
            if existing is not None:
                # Compare precedence: trust_level > version > first-registered
                existing_precedence = self._compute_precedence(existing)
                new_precedence = self._compute_precedence_from_spec(spec)
                if TrustLevel.precedence(spec.trust_level) < TrustLevel.precedence(
                    existing.trust_level
                ):
                    # Lower-trust attempt to displace a higher-trust registration —
                    # shadowing (spec §16 rule 3).
                    raise CapabilityManagerError(
                        f"Capability '{spec.capability_id}' cannot be shadowed: existing "
                        f"trust={existing.trust_level} > new trust={spec.trust_level}.",
                        rule_id="CM-SHADOW-001",
                    )
                if new_precedence <= existing_precedence:
                    # Equal or lower precedence (same trust, not-higher version) —
                    # first registrant wins (spec §16 rule 2).
                    raise CapabilityManagerError(
                        f"Capability '{spec.capability_id}' already registered with "
                        f"higher or equal precedence (existing trust={existing.trust_level}, "
                        f"version={existing.version}; new trust={spec.trust_level}, "
                        f"version={spec.version}).",
                        rule_id="CM-PREC-001",
                    )
                # New capability wins — log and replace
                self._log_info(
                    f"Capability '{spec.capability_id}' replaced by higher-precedence manifest "
                    f"(old trust={existing.trust_level}, new trust={spec.trust_level})"
                )

        # Build security_context from spec
        security_context = spec.to_security_context()

        # Build provider_metadata from spec
        provider_metadata = spec.to_provider_metadata()

        entry = CapabilityRegistryEntry(
            capability_id=spec.capability_id,
            facade=spec.facade,
            provider_id=spec.provider_id,
            provider_metadata=provider_metadata,
            version=spec.version,
            state=CapabilityState.REGISTERED,
            security_context=security_context,
            resource_profile={},
            tags=spec.tags,
            trust_level=spec.trust_level,
            authority_classification=spec.authority_classification,
            adapter_binding={"class_path": spec.adapter_class_path, "kwargs": dict(spec.adapter_kwargs)},
            operations=spec.allowed_operations,
            health_status="unknown",
            availability=(
                CapabilityAvailability.AVAILABLE if spec.enabled else CapabilityAvailability.DISABLED
            ),
            enabled=spec.enabled,
            discovered_from=spec.discovered_from,
            dependencies=spec.dependencies,
            last_error=None,
        )

        with self._registry_lock:
            self._registry[spec.capability_id] = entry

        self._emit_event(
            _CAPABILITY_REGISTERED,
            {
                "capability_id": spec.capability_id,
                "facade": spec.facade,
                "provider_id": spec.provider_id,
                "version": spec.version,
                "trust_level": spec.trust_level,
                "authority_classification": spec.authority_classification,
                "discovered_from": spec.discovered_from,
            },
        )
        self._log_info(
            f"Registered capability (M8-T5): {spec.capability_id} "
            f"(facade={spec.facade}, trust={spec.trust_level}, "
            f"authority={spec.authority_classification}, discovered_from={spec.discovered_from})"
        )
        return entry

    def _compute_precedence(self, entry: CapabilityRegistryEntry) -> tuple:
        """Compute precedence tuple for collision resolution (trust > version > first-registered).

        Unparseable versions sort below any parseable semver (spec §16 rule 2:
        "unparseable version → first registrant wins" — the existing entry keeps
        precedence over an unparseable challenger).
        """
        trust_precedence = TrustLevel.precedence(entry.trust_level)
        return (trust_precedence, _parse_version(entry.version))

    def _compute_precedence_from_spec(self, spec: CapabilitySpec) -> tuple:
        """Compute precedence tuple from CapabilitySpec."""
        trust_precedence = TrustLevel.precedence(spec.trust_level)
        return (trust_precedence, _parse_version(spec.version))

    # ------------------------------------------------------------------
    # M9-N6 — Capability manifest hot-reload (fail-closed)
    # ------------------------------------------------------------------

    async def reload_capabilities(
        self,
        loader: Any,
        *,
        initialize: bool = True,
    ) -> dict[str, Any]:
        """Hot-reload manifest-discovered capabilities (M9-N6, spec §11.6/§20).

        Re-runs the full M8-T5 pipeline via ``loader.reload()`` (validation +
        allowlist + non-auto-trust gates), then reconciles the registry with
        the validated spec set — every insertion goes through
        :meth:`register_capability`, so the SecurityManager gate, CM-SHADOW-001
        and CM-PREC-001 collision guards apply unchanged. M9 must not bypass
        ``register_capability``'s precedence/collision logic (spec §20).

        Reconciliation semantics:
        * Entries previously registered FROM THE LOADER'S OWN MANIFEST DIR
          (matched by their ``discovered_from`` provenance) are replaced or
          withdrawn as directed by the reloaded manifest set — including
          downgrades, since CM-MANIFEST-001 already caps manifest trust at
          ``trusted_contextual`` (no privilege gain is possible).
        * Foreign entries (kernel/builtin registrations, ``discovered_from``
          outside the loader dir) are NEVER touched; a reloaded manifest that
          collides with one raises CM-SHADOW-001 / CM-PREC-001.

        Fail-closed semantics (spec §18):
        * Any invalid manifest → the loader raises before any registry mutation.
        * Any registration failure → the pre-reload registry state is restored
          atomically and the error is re-raised. The previous valid registry is
          always preserved.

        Args:
            loader: A ``CapabilityManifestLoader`` (or duck-typed equivalent
                exposing ``reload() -> list[spec]`` and optionally
                ``manifest_dir``).
            initialize: When True (default), re-initialize enabled capabilities
                via ``initialize_capability`` (adapter instantiation + health).

        Returns:
            Summary dict: ``{"registered": [...], "initialized": [...],
            "removed": [...]}`` describing the applied delta.

        Raises:
            Exception: Whatever the loader or registration raises; the caller's
                prior registration state is guaranteed intact on raise.
        """
        # 1. Validate everything BEFORE touching the registry (fail-closed).
        specs = loader.reload()

        loader_dir = str(getattr(loader, "manifest_dir", "") or "")

        def _owned_by_loader(discovered_from: str) -> bool:
            if not discovered_from or not loader_dir:
                return False
            return str(discovered_from).startswith(loader_dir)

        with self._registry_lock:
            snapshot = {
                cid: entry for cid, entry in self._registry.items()
            }

        registered: list[str] = []
        initialized: list[str] = []
        removed: list[str] = []

        try:
            # 2. Compute the delta against manifest-owned entries only.
            new_ids = {spec.capability_id for spec in specs}
            owned_ids = {
                cid
                for cid, entry in snapshot.items()
                if _owned_by_loader(getattr(entry, "discovered_from", ""))
            }
            # Vanished / disabled (loader skips enabled:false) → withdraw.
            to_withdraw = sorted(owned_ids - new_ids)
            # Unchanged/changed owned ids → explicit replace (deregister then
            # register): an equal-precedence in-place re-registration would be
            # rejected by CM-PREC-001, and this path can never grant privilege
            # because CM-MANIFEST-001 caps manifest trust at trusted_contextual
            # and every registration re-runs the full security gate.
            to_replace = sorted(owned_ids & new_ids)

            # 3. Apply: withdraw stale / replaced entries, then register fresh.
            for cid in to_withdraw:
                self.deregister(cid)
                removed.append(cid)
            for cid in to_replace:
                self.deregister(cid)

            for spec in specs:
                entry = self.register_capability(spec)  # full security gate
                registered.append(entry.capability_id)

            if initialize:
                for spec in specs:
                    entry = self.get_capability(spec.capability_id)
                    if entry is not None and entry.enabled:
                        ok = await self.initialize_capability(spec.capability_id)
                        if not ok:
                            # Initialization failure is recorded on the entry
                            # (availability=error) but does NOT roll back the
                            # registration — mirrors boot-time behavior where
                            # one unhealthy capability must not block others.
                            self._log_warning(
                                f"Hot-reload: initialization failed for "
                                f"{spec.capability_id}; entry marked unavailable"
                            )
                        else:
                            initialized.append(spec.capability_id)

        except Exception as exc:  # noqa: BLE001 — restore prior state, fail-closed
            with self._registry_lock:
                self._registry.clear()
                self._registry.update(snapshot)
            self._log_error(f"Hot-reload rejected (fail-closed): {exc}")
            raise

        return {
            "registered": registered,
            "initialized": initialized,
            "removed": removed,
        }

    def disable(self, capability_id: str) -> bool:
        """Disable a capability (M8-T5 lifecycle: AVAILABLE -> DISABLED)."""
        with self._registry_lock:
            entry = self._registry.get(capability_id)
            if entry is None:
                return False
            if entry.enabled is False:
                return True  # Idempotent
            entry.enabled = False
            entry.availability = CapabilityAvailability.DISABLED
            entry.state = CapabilityState.DISABLED
            self._log_info(f"Disabled capability: {capability_id}")
        return True

    def enable(self, capability_id: str) -> bool:
        """Enable a capability (M8-T5 lifecycle: DISABLED -> AVAILABLE)."""
        with self._registry_lock:
            entry = self._registry.get(capability_id)
            if entry is None:
                return False
            if entry.enabled is True:
                return True  # Idempotent
            entry.enabled = True
            entry.availability = CapabilityAvailability.AVAILABLE
            entry.state = CapabilityState.REGISTERED
            self._log_info(f"Enabled capability: {capability_id}")
        return True

    def deprecate(self, capability_id: str) -> bool:
        """Deprecate a capability (M8-T5 lifecycle: still resolvable but flagged)."""
        with self._registry_lock:
            entry = self._registry.get(capability_id)
            if entry is None:
                return False
            entry.state = CapabilityState.DEPRECATED
            self._log_info(f"Deprecated capability: {capability_id} (still resolvable)")
        return True

    def set_health(self, capability_id: str, health_status: CapabilityAvailability) -> bool:
        """Set capability health status (M8-T5 health checks)."""
        with self._registry_lock:
            entry = self._registry.get(capability_id)
            if entry is None:
                return False
            entry.health_status = health_status
            if health_status == CapabilityAvailability.UNAVAILABLE:
                entry.availability = CapabilityAvailability.UNAVAILABLE
            elif health_status == CapabilityAvailability.AVAILABLE and entry.enabled:
                entry.availability = CapabilityAvailability.AVAILABLE
            self._log_debug(f"Set health for {capability_id}: {health_status}")
        return True

    def enforce_security_context(
        self,
        capability_id: str,
        caller_context: dict[str, Any] | None = None,
    ) -> CapabilityRegistryEntry:
        """
        Enforce security context at resolution/invocation time (M8-T5).

        Validates caller context against capability's security_context:
        - allowed_operations check
        - sensitive_keys protection
        - max_content_size limits

        Args:
            capability_id: Capability to validate
            caller_context: Optional caller context with operation, content_size, etc.

        Returns:
            The capability entry if validation passes

        Raises:
            CapabilityManagerError: If security validation fails
        """
        with self._registry_lock:
            entry = self._registry.get(capability_id)
        if entry is None:
            raise CapabilityManagerError(
                f"Capability '{capability_id}' not registered",
                rule_id="CM-RES-001",
            )

        security_ctx = entry.security_context
        caller_context = caller_context or {}

        # 1. Allowed-operations check (spec §21: CM-SEC-001)
        allowed_ops = security_ctx.get("allowed_operations", [])
        requested_op = caller_context.get("operation")
        if allowed_ops and requested_op is not None and requested_op not in allowed_ops:
            raise CapabilityManagerError(
                f"Operation '{requested_op}' not allowed for capability '{capability_id}'. "
                f"Allowed: {allowed_ops}",
                rule_id="CM-SEC-001",
            )

        # 2. Sensitive-keys check (spec §21: CM-SEC-002) — denied at the
        # capability layer, not merely logged (fail-closed).
        sensitive_keys = {
            k.lower() for k in security_ctx.get("sensitive_keys", []) if isinstance(k, str)
        }
        if sensitive_keys:
            # Scan both explicit payload keys and nested dict keys of any
            # provided input payload.
            payload = caller_context.get("payload")
            payload_keys: set[str] = set()
            if isinstance(payload, dict):
                def _collect(obj: Any) -> None:
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            payload_keys.add(str(k).lower())
                            _collect(v)
                    elif isinstance(obj, (list, tuple)):
                        for item in obj:
                            _collect(item)

                _collect(payload)
            payload_keys |= {
                str(k).lower() for k in caller_context.get("payload_keys", ())
            }
            hits = sensitive_keys & payload_keys
            if hits:
                raise CapabilityManagerError(
                    f"Payload contains sensitive keys {sorted(hits)} "
                    f"for capability '{capability_id}'",
                    rule_id="CM-SEC-002",
                )

        # 3. Max-content-size check (spec §21: CM-SEC-003)
        max_size = security_ctx.get("max_content_size", 10240)
        content_size = caller_context.get("content_size")
        if content_size is None:
            payload = caller_context.get("payload")
            if isinstance(payload, str):
                content_size = len(payload.encode("utf-8"))
            elif isinstance(payload, (bytes, bytearray)):
                content_size = len(payload)
            elif payload is not None:
                try:
                    import json as _json

                    content_size = len(_json.dumps(payload, default=str))
                except Exception:  # noqa: BLE001
                    content_size = 0
            else:
                content_size = 0
        if content_size > int(max_size):
            raise CapabilityManagerError(
                f"Content size {content_size} exceeds max {max_size} "
                f"for capability '{capability_id}'",
                rule_id="CM-SEC-003",
            )

        return entry

    def resolve(
        self,
        capability_id: str,
        *,
        caller_context: dict[str, Any] | None = None,
    ) -> CapabilityRegistryEntry:
        """Resolve a capability to its bound provider endpoint (Part 4 §4.8.5).

        M8-T5 extension: Enforces security context and availability checks.

        Raises CapabilityManagerError if the capability is not registered,
        disabled, or fails security validation.
        """
        with self._registry_lock:
            entry = self._registry.get(capability_id)
        if entry is None:
            raise CapabilityManagerError(
                f"Capability '{capability_id}' is not registered; cannot resolve.",
                rule_id="CM-RES-001",
            )

        # M8-T5: Check availability/lifecycle before resolving.
        # DEPRECATED stays resolvable but flagged (spec §14).
        if entry.state == CapabilityState.DISABLED or not entry.enabled:
            raise CapabilityManagerError(
                f"Capability '{capability_id}' is disabled",
                rule_id="CM-DIS-001",
            )
        if entry.availability == CapabilityAvailability.UNAVAILABLE:
            raise CapabilityManagerError(
                f"Capability '{capability_id}' is unavailable (health check failed)",
                rule_id="CM-RES-002",
            )
        if entry.state == CapabilityState.DEPRECATED:
            self._log_warning(
                f"Resolved DEPRECATED capability: {capability_id} "
                f"(still resolvable but flagged)"
            )

        # M8-T5: Enforce security context
        self.enforce_security_context(capability_id, caller_context)

        return entry

    async def initialize_capability(self, capability_id: str) -> bool:
        """Initialize a capability (M8-T5: REGISTERED -> INITIALIZE -> HEALTH CHECK -> AVAILABLE).

        Instantiates the bound adapter via the AdapterFactory and runs its
        optional ``initialize()``/``health_check()``. Failures are recorded on
        the entry (``availability=error``, ``last_error``) — the registry dict
        itself is never corrupted (spec §15).

        Returns True on success; False when the capability is unknown or failed
        to initialize.
        """
        with self._registry_lock:
            entry = self._registry.get(capability_id)
        if entry is None:
            return False

        try:
            # Check declared dependencies are registered and available
            for dep_id in entry.dependencies:
                dep_entry = self.get_capability(dep_id)
                if dep_entry is None or dep_entry.availability != CapabilityAvailability.AVAILABLE:
                    raise CapabilityManagerError(
                        f"Dependency '{dep_id}' not available for capability '{capability_id}'",
                        rule_id="CM-INIT-001",
                    )

            # Instantiate adapter via factory if a binding exists
            binding = entry.adapter_binding
            class_path = (
                binding.get("class_path", "") if isinstance(binding, dict) else str(binding or "")
            )
            adapter = None
            if class_path and self._adapter_factory is not None:
                kwargs = binding.get("kwargs", {}) if isinstance(binding, dict) else {}
                adapter = self._adapter_factory.get_adapter(class_path, kwargs=kwargs)
                if hasattr(adapter, "initialize"):
                    result = adapter.initialize()
                    if asyncio.iscoroutine(result):
                        await result

            # Optional health check on the adapter
            health_status = "healthy"
            if adapter is not None and hasattr(adapter, "health_check"):
                hc = adapter.health_check()
                if asyncio.iscoroutine(hc):
                    hc = await hc
                if isinstance(hc, dict):
                    health_status = str(hc.get("status", "healthy"))
                elif isinstance(hc, str):
                    health_status = hc

            with self._registry_lock:
                entry.health_status = health_status
                if entry.enabled:
                    entry.availability = CapabilityAvailability.AVAILABLE
                    entry.state = CapabilityState.REGISTERED
                else:
                    entry.availability = CapabilityAvailability.DISABLED
                entry.last_error = None
            self._log_info(
                f"Initialized capability: {capability_id} (health={health_status})"
            )
            return True

        except Exception as e:  # noqa: BLE001 — record typed failure on the entry
            with self._registry_lock:
                entry.health_status = "unhealthy"
                entry.availability = CapabilityAvailability.ERROR
                entry.last_error = str(e)
            self._log_error(f"Failed to initialize capability {capability_id}: {e}")
            return False

    def deregister(self, capability_id: str) -> bool:
        """Deregister a capability (Part 4 §4.8.3). Returns True if removed."""
        with self._registry_lock:
            entry = self._registry.pop(capability_id, None)
        if entry is None:
            return False
        entry.state = CapabilityState.REMOVED
        self._emit_event(
            _CAPABILITY_REMOVED,
            {
                "capability_id": capability_id,
                "facade": entry.facade,
                "provider_id": entry.provider_id,
            },
        )
        self._log_debug(f"Deregistered capability: {capability_id}")
        return True

    def get_capability(self, capability_id: str) -> CapabilityRegistryEntry | None:
        """Look up a registered capability by id."""
        with self._registry_lock:
            return self._registry.get(capability_id)

    def list_capabilities(self) -> list[CapabilityRegistryEntry]:
        """List all registered capabilities (snapshot)."""
        with self._registry_lock:
            return list(self._registry.values())

    def discover_by_facade(self, facade: str) -> list[CapabilityRegistryEntry]:
        """Discover capabilities matching a facade id (Part 4 §4.8.4)."""
        with self._registry_lock:
            return [e for e in self._registry.values() if e.facade == facade]

    def discover_by_tags(self, required_tags: tuple[str, ...]) -> list[CapabilityRegistryEntry]:
        """Discover capabilities carrying all of the required tags (Part 4 §4.8.4)."""
        if not required_tags:
            with self._registry_lock:
                return list(self._registry.values())
        with self._registry_lock:
            return [
                e
                for e in self._registry.values()
                if all(t in e.tags for t in required_tags)
            ]

    def invoke(
        self,
        capability_id: str,
        *,
        input_payload: dict[str, Any] | None = None,
        caller_context: dict[str, Any] | None = None,
    ) -> CapabilityRegistryEntry:
        """Invoke a capability (Part 4 §4.8.6).

        Resolves the capability (failing if not registered — no bypass,
        SI-CM-05) and emits the canonical ``SKILL_EXECUTED`` event (mapping
        CapabilityInvocationEvent, CONFLICT E.1). Returns the resolved entry.

        The actual provider execution is delegated to the kernel's execution
        layer; this manager owns only the registry/routing/emit contract and does
        not fabricate an execution result. Callers awaiting a result should use
        the resolved entry to drive the owning provider.
        """
        try:
            entry = self.resolve(capability_id, caller_context=caller_context)
        except CapabilityManagerError as exc:
            self._emit_event(
                _CAPABILITY_INVOCATION_FAILED,
                {
                    "capability_id": capability_id,
                    "error": str(exc),
                },
            )
            raise

        self._emit_event(
            _CAPABILITY_INVOKED,
            {
                "capability_id": capability_id,
                "facade": entry.facade,
                "provider_id": entry.provider_id,
                "version": entry.version,
            },
        )
        self._log_debug(f"Invoked capability: {capability_id}")
        return entry

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical capability event via the canonical EventBus.

        The canonical ``EventBus.publish`` is async (returns a coroutine). From a
        synchronous business-API call site we cannot ``await`` it, so this method
        bridges to the async bus deterministically using the architecture-approved
        sync-to-async bridge (FIX-FIND-01) established by the sibling Core
        Managers:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion).
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note — avoiding the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaving a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.8.11 names
        like ``CapabilityRegisteredEvent`` / ``CapabilityConflictEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        full_payload = {
            "manager": _NAME,
            "manager_id": _MANAGER_ID,
            **payload,
        }

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=full_payload,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 15 — replaces stdlib logging)
    # ------------------------------------------------------------------

    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME, **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME, **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME, **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME, **fields)


# ---------------------------------------------------------------------------
# Global CapabilityManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_capability_manager: CapabilityManager | None = None
_capability_singleton_lock = threading.Lock()


def get_capability_manager() -> CapabilityManager:
    """Get or create the global CapabilityManager singleton.

    Uses the same lock-guarded pattern as the other Core Managers (Tasks 9–14)
    and the C1–C4 singletons, so concurrent callers cannot double-construct.
    """
    global _global_capability_manager
    with _capability_singleton_lock:
        if _global_capability_manager is None:
            _global_capability_manager = CapabilityManager()
        return _global_capability_manager


def set_capability_manager(manager: CapabilityManager) -> None:
    """Set the global CapabilityManager singleton."""
    global _global_capability_manager
    with _capability_singleton_lock:
        _global_capability_manager = manager


def reset_capability_manager_singleton() -> None:
    """Reset the process-wide CapabilityManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` / ``reset_state_manager_singleton``
    / ``reset_storage_manager_singleton`` / ``reset_health_manager_singleton`` /
    ``reset_resource_manager_singleton`` / ``reset_security_manager_singleton`` /
    C2–C4 resets.
    """
    global _global_capability_manager
    with _capability_singleton_lock:
        _global_capability_manager = None
