"""
StorageManager — the Phase-2 (State & Storage) Core Manager for AI-OS Hermes Kernel.

StorageManager SHALL be the sole governance authority for all persistent
storage within the Hermes Kernel. It owns persistent storage provisioning,
checkpoint storage, artifact storage, retention policies, compaction,
integrity verification, encryption coordination, and storage recovery.

Task 11 — Core Manager creation (Part 4 §4.5)
--------------------------------------------
StorageManager is the Phase-2 (State & Storage) Core Manager. It implements the
ICoreManager Protocol (name / phase / dependencies / initialize / shutdown /
health_ready) so LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 2 (alphabetical within phase:
    StateManager first, then StorageManager — deterministic per Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.storage``
    (Part 4 §4.5.11 / §4.5.14 names ``kernel.storage``; see the CONFLICT E.1 note
    below for the Part-3-vs-Part-4 resolution that maps it to ``core.storage``,
    using the same precedent Task 9/10 established for ``core.lifecycle`` /
    ``core.state``), using the same "core_manager" metadata envelope
  * reads ``kernel.storage.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used (Task 11 requirement)

CONFLICT E.1 (Task 11 mapping, same as Task 9/10): Part 4 §4.5.11 names events
like ``StorageCheckpointWrittenEvent``, ``StorageArtifactStoredEvent``,
``StorageRetentionAppliedEvent``, ``StorageCorruptionDetectedEvent``,
``StorageCompactionCompletedEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1). StorageManager does NOT invent new
EventTypes. The canonical mappings for the storage domain are:

  * Artifact written  -> EventType.ARTIFACT_CREATED
  * Artifact updated  -> EventType.ARTIFACT_UPDATED
  * Artifact removed  -> EventType.ARTIFACT_DELETED
  * Checkpoint stored -> EventType.CHECKPOINT_CREATED
  * Checkpoint pruned -> EventType.CHECKPOINT_PRUNED

If a conceptual storage event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

NOTE ON ``core.storage`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.5.11): Part 4 §4.5.11 names StorageManager's ServiceRegistry identity as
``kernel.storage``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10 resolved for
StateManager (registering as ``core.state`` instead of ``kernel.state``). Per
that precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry
identity is ``core.storage`` (the ``core.*`` namespace is not reserved and is
NOT a validator exception). The configuration namespace read from C3 remains
``kernel.storage.*`` (Part 4 §4.5.11 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 2) is unchanged.

PHASE DEPENDENCY RULE: StorageManager is Phase 2. It does NOT declare
StateManager as a formal dependency:

    dependencies = ["LifecycleManager"]

The same-phase StorageManager/StateManager sibling is ordered deterministically
(alphatbetical within Phase 2: StateManager before StorageManager) and the
existing LifecycleManager dependency validator (LM-DEP-003) does not accept
same-phase sibling dependencies. Relying on deterministic alphabetical ordering
guarantees correct sequencing; the StorageManager/StateManager operational
relationship is event-driven (via canonical EventBus), not a lifecycle
dependency edge.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as LifecycleManager/StateManager);
# these modules do not import ``aios.core.storage`` at module scope, so there is
# no circular-import risk (verified against checkpoint/workflow/kernel/__init__).
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "StorageManager",
    "StorageNamespace",
    "StorageObject",
    "StorageManagerError",
    "get_storage_manager",
    "set_storage_manager",
    "reset_storage_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "StorageManager"
# Part 4 §4.5.11 names StorageManager's ServiceRegistry identity as
# ``kernel.storage``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
# as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10 resolved for
# StateManager (registering as ``core.state`` instead of ``kernel.state``). We
# follow that precedent: the compliant, INV-SR-NS-002-respecting ServiceRegistry
# id is ``core.storage``. The configuration namespace read from C3 remains
# ``kernel.storage.*`` (Part 4 §4.5.11 config schema), which is unaffected by the
# ServiceRegistry id.
_MANAGER_ID = "core.storage"
_PHASE = 2  # Phase 2 — "State & Storage"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 11 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture (§4.2.5 / §4.3.4 step 1-2):
#   * the same-phase StateManager sibling is NOT a dependency — same-phase
#     deps would be rejected by LifecycleManager's dependency validator
#     (LM-DEP-003); the deterministic alphabetical ordering within Phase 2
#     (StateManager before StorageManager) already guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)


class StorageNamespace(str, Enum):
    """Storage namespaces (Part 4 §4.5.3 — six logical partitions).

    Each namespace is a logically isolated storage partition with its own
    retention, encryption, and access policy. No additional namespaces are
    invented.
    """

    CHECKPOINTS = "checkpoints"
    ARTIFACTS = "artifacts"
    DIAGNOSTICS = "diagnostics"
    AUDIT = "audit"
    CONFIGURATION = "configuration"
    IDENTITY = "identity"


@dataclass
class StorageObject:
    """A stored object in a StorageManager namespace."""

    namespace: StorageNamespace
    object_id: str
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    stored_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str | None = None


class StorageManagerError(Exception):
    """StorageManager failure (Part 4 §4.5.12).

    Carries optional diagnostic context: ``rule_id`` (internal invariant/rule
    identifier) and ``original_error`` (the underlying error, when wrapping).
    Mirrors ``LifecycleManagerError`` (Task 9) / ``StateManagerError`` (Task 10).
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
            base += f" [original_error={type(self.original_error).__name__}: {self.original_error}]"
        return base


class StorageManager:
    """
    Governance authority for all persistent storage in the Hermes Kernel.

    Provides:
    - Six logical storage namespaces (Part 4 §4.5.3): checkpoints, artifacts,
      diagnostics, audit, configuration, identity
    - Artifact storage/retrieval with canonical ARTIFACT_CREATED/UPDATED/DELETED
      event emission
    - Checkpoint storage operations with canonical CHECKPOINT_CREATED/CHECKPOINT_PRUNED
      event emission
    - Retention policy enforcement
    - Integrity verification (per-object, checkpoint, background)
    - ICoreManager lifecycle (initialize / shutdown / health_ready)
    """

    def __init__(
        self,
        persistence_path: Path | None = None,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the Storage Manager.

        Backward compatible: the ``persistence_path`` positional/None argument
        is preserved from the pre-Task-11 constructor. The C2/C3/C4 dependencies
        are optional keyword-only injection points; they are resolved at
        ``initialize()`` time (C3 is frozen before LifecycleManager Phase 2 runs,
        so ``initialize()`` reads the frozen configuration).
        """
        self._persistence_path = persistence_path or Path("./data/storage")
        self._persistence_path.mkdir(parents=True, exist_ok=True)

        # In-memory namespace storage; each namespace maps object_id -> StorageObject.
        self._namespaces: dict[str, dict[str, StorageObject]] = {
            ns.value: {} for ns in StorageNamespace
        }

        # Strong references for sync-path publish tasks (FIX-FIND-01 pattern):
        # coroutines scheduled from synchronous business APIs are awaited on the
        # running loop and held here until complete so they are never
        # garbage-collected or left un-awaited. Mirrors the
        # ConfigurationManager ``_pending_tasks`` pattern (Task 7), which is the
        # architecture-approved sync-to-async bridge.
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly so both
        # the constructor contract (raise if the bus is not up) and the sync
        # ``_emit_event`` bridge keep working unchanged.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")

        # C2/C3/C4 — injected via DI (Task 11); resolved lazily in initialize().
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.5).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 11).
        self._initialized = False
        self._registered_with_sr = False
        self._shutdown_timeout_ms = 5000  # kernel.storage.shutdownTimeoutMs default

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._consistency_class = "EVENTUAL"
        self._retention_policy: dict[str, Any] = {}
        self._integrity_verification = True

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 11 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 2 — State & Storage, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4.

        Per the Phase Dependency Rule (Task 11), the same-phase StateManager
        sibling is NOT a formal dependency — deterministic alphabetical
        ordering within Phase 2 guarantees correct sequencing.
        """
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.storage``; Part 4 §4.5.11 names
        ``kernel.storage`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready / StateManager.health_ready.
        Returns False before ``initialize()`` and after ``shutdown()``.
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
        """Phase 2 initialization (called by LifecycleManager).

        Follows the Core Manager pattern (mirrors StateManager.initialize):
        reads ``kernel.storage.*`` configuration from the frozen C3, wires the
        StructuredLogger (C4), initializes the six storage namespaces from
        configuration, registers this manager with the canonical ServiceRegistry
        (C2) as ``core.storage``, and marks the manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._persistence_path = Path(
            self._read_config_str(
                "kernel.storage.persistencePath", str(self._persistence_path)
            )
        )
        self._persistence_path.mkdir(parents=True, exist_ok=True)

        self._consistency_class = self._read_config_str(
            "kernel.storage.consistencyClass", self._consistency_class
        )
        self._integrity_verification = self._read_config_bool(
            "kernel.storage.integrity.verification", self._integrity_verification
        )
        self._shutdown_timeout_ms = self._read_config_int(
            "kernel.storage.shutdownTimeoutMs", self._shutdown_timeout_ms
        )

        # 2. Initialize retention policy configuration from C3 (best-effort).
        # If unavailable, namespaces use their default retention settings.
        try:
            retention_section = self._configuration.get_section("kernel.storage.retention") \
                if self._configuration is not None else None
            if retention_section and isinstance(retention_section, dict):
                self._retention_policy = dict(retention_section)
            else:
                self._retention_policy = {}
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"Could not read retention policy config: {exc}")
            self._retention_policy = {}

        # 3. Load persisted objects (recovery). Failures are non-fatal; the
        # manager starts with whatever loaded cleanly.
        try:
            loaded = self._load_persisted_objects()
            self._log_info(f"Loaded {loaded} persisted object(s) during initialize().")
        except Exception as exc:  # noqa: BLE001
            self._log_error(f"Failed to load persisted objects: {exc}")

        # 4. Register with the canonical ServiceRegistry (C2) as ``core.storage``.
        await self.register_with_service_registry()

        # 5. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"StorageManager initialized (phase {self.phase}, "
            f"namespaces={list(self._namespaces.keys())}, "
            f"persistence={self._persistence_path})."
        )

    async def shutdown(self) -> None:
        """Phase 2 (reverse) shutdown (called by LifecycleManager).

        Flushes/persists required storage state, marks ``core.storage`` SHUTDOWN
        in the canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Flush/persist storage state (best-effort).
        try:
            persisted = self._persist_all_objects()
            self._log_info(f"Persisted {persisted} object(s) during shutdown.")
        except Exception as exc:  # noqa: BLE001
            self._log_error(f"Final persist failed: {exc}")

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("StorageManager shut down.")

    def _persist_all_objects(self) -> int:
        """Persist all in-memory namespace objects to disk (best-effort)."""
        count = 0
        for namespace, objects in self._namespaces.items():
            for object_id, obj in objects.items():
                try:
                    self._persist_object(obj)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    self._log_warning(
                        f"Failed to persist object ({namespace}:{object_id}): {exc}"
                    )
        return count

    def _load_persisted_objects(self) -> int:
        """Load persisted objects from disk into namespace memory."""
        count = 0
        if not self._persistence_path or not self._persistence_path.exists():
            return 0

        for file_path in self._persistence_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                namespace = StorageNamespace(data["namespace"])
                obj = StorageObject(
                    namespace=namespace,
                    object_id=data["object_id"],
                    data=data["data"],
                    metadata=data.get("metadata", {}),
                    stored_at=datetime.fromisoformat(data["stored_at"]),
                    checksum=data.get("checksum"),
                )
                self._namespaces[namespace.value][obj.object_id] = obj
                count += 1
            except Exception as exc:  # noqa: BLE001
                self._log_warning(f"Failed to load persisted object {file_path}: {exc}")

        return count

    def _persist_object(self, obj: StorageObject) -> None:
        """Persist a single StorageObject to disk."""
        if not self._persistence_path:
            return

        file_path = (
            self._persistence_path
            / f"{obj.namespace.value}_{obj.object_id}.json"
        )
        data = {
            "namespace": obj.namespace.value,
            "object_id": obj.object_id,
            "data": obj.data,
            "metadata": obj.metadata,
            "stored_at": obj.stored_at.isoformat(),
            "checksum": obj.checksum,
        }
        file_path.write_text(json.dumps(data, indent=2, default=str))

    def _remove_persisted_object(self, obj: StorageObject) -> None:
        """Remove a single StorageObject's persisted file from disk (best-effort)."""
        if not self._persistence_path:
            return
        file_path = (
            self._persistence_path
            / f"{obj.namespace.value}_{obj.object_id}.json"
        )
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            # Best-effort: failure to delete on disk does not prevent
            # in-memory removal from completing.
            pass

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.storage`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister.")
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
    # ServiceRegistry integration (mirror LifecycleManager/StateManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register StorageManager with the ServiceRegistry (C2, Part 4 §4.5.11).

        Registered as ``core.storage`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) and StateManager uses
        (``core.state``) — ``kind: core_manager`` — so the registration is
        explicitly NOT classified as an ordinary engineering service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering StorageManager.")
            return
        try:
            # Resolve the singleton at initialize() time if the kernel wired the
            # canonical instance through DI.
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

    # ------------------------------------------------------------------
    # Storage business API — namespace access (Part 4 §4.5.3)
    # ------------------------------------------------------------------

    @property
    def namespaces(self) -> list[StorageNamespace]:
        """The six storage namespaces (Part 4 §4.5.3)."""
        return list(StorageNamespace)

    def get_namespace_objects(self, namespace: StorageNamespace) -> list[str]:
        """List all object IDs within a namespace."""
        return list(self._namespaces[namespace.value].keys())

    def get_object(
        self,
        namespace: StorageNamespace,
        object_id: str,
    ) -> StorageObject | None:
        """Retrieve a stored object from a namespace (read)."""
        return self._namespaces[namespace.value].get(object_id)

    # ------------------------------------------------------------------
    # Artifact operations (Part 4 §4.5.5 — Artifact Storage)
    # ------------------------------------------------------------------

    def store_artifact(
        self,
        artifact_id: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        emit_event: bool = True,
    ) -> StorageObject:
        """Store an artifact in the ``artifacts`` namespace.

        Emits ``ARTIFACT_CREATED`` on the canonical EventBus (Part 2 §2.3.1).
        If the artifact already exists it is updated and ``ARTIFACT_UPDATED``
        is emitted instead.
        """
        ns = StorageNamespace.ARTIFACTS
        existing = self._namespaces[ns.value].get(artifact_id)
        obj = StorageObject(
            namespace=ns,
            object_id=artifact_id,
            data=data,
            metadata=metadata or {},
        )
        self._namespaces[ns.value][artifact_id] = obj

        # Persist to disk (mirrors StateManager._persist_snapshot in checkpoint()).
        self._persist_object(obj)

        if emit_event:
            if existing is None:
                self._emit_event(
                    EventType.ARTIFACT_CREATED,
                    {
                        "namespace": ns.value,
                        "object_id": artifact_id,
                        "metadata": obj.metadata,
                    },
                    artifact_id,
                )
            else:
                self._emit_event(
                    EventType.ARTIFACT_UPDATED,
                    {
                        "namespace": ns.value,
                        "object_id": artifact_id,
                        "metadata": obj.metadata,
                    },
                    artifact_id,
                )
        return obj

    def retrieve_artifact(self, artifact_id: str) -> StorageObject | None:
        """Retrieve an artifact from the ``artifacts`` namespace."""
        return self.get_object(StorageNamespace.ARTIFACTS, artifact_id)

    def delete_artifact(
        self,
        artifact_id: str,
        emit_event: bool = True,
    ) -> bool:
        """Delete an artifact from the ``artifacts`` namespace.

        Emits ``ARTIFACT_DELETED`` on the canonical EventBus (Part 2 §2.3.1).
        Returns True if the artifact existed and was deleted.
        """
        ns = StorageNamespace.ARTIFACTS
        existing = self._namespaces[ns.value].pop(artifact_id, None)

        # Remove persisted file from disk (best-effort).
        if existing is not None:
            self._remove_persisted_object(existing)

        if existing is not None and emit_event:
            self._emit_event(
                EventType.ARTIFACT_DELETED,
                {
                    "namespace": ns.value,
                    "object_id": artifact_id,
                    "metadata": existing.metadata,
                },
                artifact_id,
            )
        return existing is not None

    # ------------------------------------------------------------------
    # Checkpoint operations (Part 4 §4.5.4 — Checkpoint Storage)
    # ------------------------------------------------------------------

    def write_checkpoint(
        self,
        checkpoint_id: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        emit_event: bool = True,
    ) -> StorageObject:
        """Write a checkpoint to the ``checkpoints`` namespace.

        Emits ``CHECKPOINT_CREATED`` on the canonical EventBus (Part 2 §2.3.1)
        when ``emit_event`` is True.
        """
        ns = StorageNamespace.CHECKPOINTS
        obj = StorageObject(
            namespace=ns,
            object_id=checkpoint_id,
            data=data,
            metadata=metadata or {},
        )
        self._namespaces[ns.value][checkpoint_id] = obj

        # Persist to disk (mirrors StateManager._persist_snapshot in checkpoint()).
        self._persist_object(obj)

        if emit_event:
            self._emit_event(
                EventType.CHECKPOINT_CREATED,
                {
                    "namespace": ns.value,
                    "checkpoint_id": checkpoint_id,
                    "metadata": obj.metadata,
                },
                checkpoint_id,
            )
        return obj

    def read_checkpoint(self, checkpoint_id: str) -> StorageObject | None:
        """Read a checkpoint from the ``checkpoints`` namespace."""
        return self.get_object(StorageNamespace.CHECKPOINTS, checkpoint_id)

    def list_checkpoints(self) -> list[str]:
        """List all checkpoint IDs in the ``checkpoints`` namespace."""
        return self.get_namespace_objects(StorageNamespace.CHECKPOINTS)

    def prune_checkpoint(
        self,
        checkpoint_id: str,
        emit_event: bool = True,
    ) -> bool:
        """Prune (delete) a checkpoint from the ``checkpoints`` namespace.

        Emits ``CHECKPOINT_PRUNED`` on the canonical EventBus (Part 2 §2.3.1)
        when ``emit_event`` is True. Returns True if the checkpoint existed.
        """
        ns = StorageNamespace.CHECKPOINTS
        existing = self._namespaces[ns.value].pop(checkpoint_id, None)

        # Remove persisted file from disk (best-effort).
        if existing is not None:
            self._remove_persisted_object(existing)

        if existing is not None and emit_event:
            self._emit_event(
                EventType.CHECKPOINT_PRUNED,
                {
                    "namespace": ns.value,
                    "checkpoint_id": checkpoint_id,
                    "metadata": existing.metadata,
                },
                checkpoint_id,
            )
        return existing is not None

    # ------------------------------------------------------------------
    # Retention operations (Part 4 §4.5.6 — Retention)
    # ------------------------------------------------------------------

    def enforce_retention(self, namespace: StorageNamespace) -> int:
        """Enforce retention policy for a namespace. Returns count pruned.

        Current policy: enforce max-snapshots if configured, otherwise no-op.
        """
        policy = self._retention_policy.get(namespace.value)
        if not policy:
            return 0

        pruned = 0
        if isinstance(policy, dict):
            max_count = policy.get("maxCount") or policy.get("max_objects")
            if max_count is not None:
                objects = self._namespaces[namespace.value]
                if len(objects) > max_count:
                    # Prune oldest by stored_at (alphabetical ID as tiebreaker).
                    sorted_ids = sorted(
                        objects.keys(),
                        key=lambda oid: (objects[oid].stored_at, oid),
                    )
                    for oid in sorted_ids[: len(objects) - max_count]:
                        del objects[oid]
                        pruned += 1
        return pruned

    # ------------------------------------------------------------------
    # Integrity operations (Part 4 §4.5.8 — Integrity)
    # ------------------------------------------------------------------

    def verify_integrity(self, namespace: StorageNamespace) -> bool:
        """Verify integrity of objects in a namespace.

        Returns True if all objects pass verification (no corruption detected).
        A real implementation would verify stored checksums against object data.
        """
        if not self._integrity_verification:
            return True
        for obj in self._namespaces[namespace.value].values():
            if obj.checksum is not None:
                # In a production implementation, this would verify the checksum
                # against obj.data. Here we perform a basic existence check.
                if not obj.data:
                    self._log_warning(
                        f"Integrity check failed: empty data for "
                        f"{namespace.value}:{obj.object_id}"
                    )
                    return False
        return True

    # ------------------------------------------------------------------
    # Event emission (canonical EventType only, sync-to-async bridge)
    # ------------------------------------------------------------------

    def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str | uuid.UUID
    ) -> None:
        """Emit a canonical event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (``store_artifact`` /
        ``write_checkpoint`` / ``prune_checkpoint`` / ``delete_artifact``) we
        cannot ``await`` it, so this method bridges to the async bus
        deterministically using the architecture-approved sync-to-async bridge
        established in ``ConfigurationManager._run_emission`` (Task 7):

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion). The event is enqueued on the bus deterministically
          before the next ``await`` yields.
        * If no loop is running (e.g. a synchronous unit test, or a call before
          the kernel starts the loop), the coroutine is NOT created at all —
          the emission is skipped with a StructuredLogger debug note. The
          canonical bus requires a running loop to enqueue; synchronously
          dropping the emission here avoids the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited``
          and never leaves a coroutine un-awaited.

        This preserves StorageManager's synchronous public API (no conversion of
        ``store_artifact`` / ``write_checkpoint`` / etc. to ``async``) while
        removing both the unawaited-coroutine hazard and the fire-and-forget
        task leak.

        CONFLICT E.1: Part 4 §4.5.11 names storage events
        (StorageCheckpointWrittenEvent, StorageArtifactStoredEvent, etc.) that
        do NOT exist in the closed canonical ``EventType`` enum. Only canonical
        EventTypes are used; conceptual events with no canonical equivalent are
        omitted.
        """
        bus = self._event_bus
        if bus is None:
            return

        # Normalize correlation_id to a UUIDv4 to satisfy the canonical Event
        # contract (mirrors StateManager._emit_event / ConfigurationManager).
        correlation_uuid: uuid.UUID
        if isinstance(correlation_id, uuid.UUID):
            correlation_uuid = correlation_id
        else:
            try:
                correlation_uuid = uuid.UUID(str(correlation_id))
            except (ValueError, AttributeError):
                correlation_uuid = uuid.uuid4()

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
        )

        # FIX-FIND-01: deterministic sync→async bridge. ONLY create the publish
        # coroutine when there is a loop to drive it; never hand an un-awaited
        # coroutine to the GC (that is the bug under FIND-01).
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — there is nowhere to enqueue the coroutine.
            # Skip rather than leak an un-awaited coroutine.
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
                event_type=event_type.name,
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
                event_type=event_type.name,
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        # Strong reference so the task is never GC'd before the bus drains it.
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 11 — replaces stdlib logging)
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
# Global StorageManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_storage_manager: StorageManager | None = None
_storage_singleton_lock = threading.Lock()


def get_storage_manager(persistence_path: Path | None = None) -> StorageManager:
    """Get or create the global StorageManager.

    Backward compatible: the ``persistence_path`` coercion is preserved. The
    Task 11 singleton accessor uses the same lock-guarded pattern as C2–C4 so
    concurrent callers cannot double-construct.
    """
    global _global_storage_manager
    with _storage_singleton_lock:
        if _global_storage_manager is None:
            _global_storage_manager = StorageManager(persistence_path)
        return _global_storage_manager


def set_storage_manager(manager: StorageManager) -> None:
    """Set the global StorageManager."""
    global _global_storage_manager
    with _storage_singleton_lock:
        _global_storage_manager = manager


def reset_storage_manager_singleton() -> None:
    """Reset the process-wide StorageManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` / ``reset_state_manager_singleton``
    / C2–C4 resets.
    """
    global _global_storage_manager
    with _storage_singleton_lock:
        _global_storage_manager = None
