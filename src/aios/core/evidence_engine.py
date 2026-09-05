"""
Evidence Engine — Recovery Evidence Storage/Retrieval for M10-T4.

Provides canonical evidence storage and retrieval for M10RecoveryManager.
The engine does NOT interpret evidence — it only stores and retrieves.
Interpretation is exclusively the responsibility of M10RecoveryManager
and RootCauseAnalyzer (M9).

Part 4 §4.6/§4.7 alignment: Consumes Core Components C1-C4 via DI.
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

from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "EvidenceType",
    "EvidenceEntry",
    "EvidenceStore",
    "EvidenceEngineError",
    "get_evidence_engine",
    "set_evidence_engine",
    "reset_evidence_engine_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "EvidenceEngine"
_MANAGER_ID = "core.evidence_engine"  # core.* namespace (not reserved per INV-SR-NS-002)
_PHASE = 3  # Phase 3 — Governance (same as HealthManager)
_VERSION = SemanticVersion(1, 0, 0)


# ---------------------------------------------------------------------------
# Enumerations / data classes
# ---------------------------------------------------------------------------


class EvidenceType(str, Enum):
    """Canonical evidence types for M10 recovery."""

    SERVICE_FAILURE = "service_failure"      # M10 service crash/failure
    HEALTH_DEGRADATION = "health_degradation"  # HealthManager DEGRADED/UNHEALTHY
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # ResourceManager quota/bound hit
    SECURITY_VIOLATION = "security_violation"  # SecurityManager gate failure
    CAPABILITY_FAILURE = "capability_failure"  # CapabilityManager init/exec failure
    WORKFLOW_FAILURE = "workflow_failure"    # WorkflowManager DAG execution failure
    STATE_INCONSISTENCY = "state_inconsistency"  # StateManager checkpoint/restore mismatch
    AUTONOMY_TRIGGER = "autonomy_trigger"    # N10/N12 trigger activation
    MANUAL_OVERRIDE = "manual_override"      # Human override activation
    ROOT_CAUSE_CORRELATION = "root_cause_correlation"  # RootCauseAnalyzer correlationId


@dataclass
class EvidenceEntry:
    """Single immutable evidence record."""

    evidence_id: str
    evidence_type: EvidenceType
    component: str
    service_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "component": self.component,
            "service_id": self.service_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceEntry:
        return cls(
            evidence_id=data["evidence_id"],
            evidence_type=EvidenceType(data["evidence_type"]),
            component=data["component"],
            service_id=data.get("service_id"),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )


class EvidenceStoreError(Exception):
    """Evidence store failure."""

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


class EvidenceEngineError(Exception):
    """EvidenceEngine failure."""

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


# ---------------------------------------------------------------------------
# EvidenceStore — persistence layer
# ---------------------------------------------------------------------------


class EvidenceStore:
    """File-backed evidence persistence (StateManager-backed per M10-T4 spec §2).

    Uses StateManager checkpoint directory for persistence. Each EvidenceEntry
    is stored as a JSON file. Queries use in-memory index for speed.
    """

    def __init__(
        self,
        base_path: Path,
        logger: StructuredLogger | None = None,
        configuration: ConfigurationManager | None = None,
    ) -> None:
        self._base_path = base_path / "evidence"
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._logger = logger
        self._configuration = configuration
        self._index: dict[str, EvidenceEntry] = {}  # evidence_id -> EvidenceEntry
        self._index_lock = threading.RLock()
        self._by_correlation: dict[str, list[str]] = {}  # correlation_id -> [evidence_id]
        self._by_type: dict[EvidenceType, list[str]] = {}  # evidence_type -> [evidence_id]
        self._by_component: dict[str, list[str]] = {}  # component -> [evidence_id]
        self._initialized = False

    def _log(self, level: str, message: str, **fields: Any) -> None:
        if self._logger:
            getattr(self._logger, level)(message, component=_NAME, **fields)

    async def initialize(self) -> None:
        """Load existing evidence from disk into index."""
        if self._initialized:
            return
        self._log("debug", "Initializing EvidenceStore index...")
        for file_path in self._base_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                entry = EvidenceEntry.from_dict(data)
                self._index_entry(entry)
            except Exception as exc:  # noqa: BLE001
                self._log("warning", f"Failed to load evidence file {file_path}: {exc}")
        self._initialized = True
        self._log("info", f"EvidenceStore initialized with {len(self._index)} entries")

    def _index_entry(self, entry: EvidenceEntry) -> None:
        with self._index_lock:
            self._index[entry.evidence_id] = entry
            if entry.correlation_id:
                self._by_correlation.setdefault(entry.correlation_id, []).append(entry.evidence_id)
            self._by_type.setdefault(entry.evidence_type, []).append(entry.evidence_id)
            self._by_component.setdefault(entry.component, []).append(entry.evidence_id)

    def _write_entry(self, entry: EvidenceEntry) -> None:
        file_path = self._base_path / f"{entry.evidence_id}.json"
        file_path.write_text(json.dumps(entry.to_dict(), indent=2))

    async def store(self, entry: EvidenceEntry) -> None:
        """Persist an EvidenceEntry to disk and update index."""
        self._index_entry(entry)
        # Write to disk (fire-and-forget in thread to avoid blocking)
        await asyncio.to_thread(self._write_entry, entry)
        self._log("debug", f"Stored evidence {entry.evidence_id} [{entry.evidence_type.value}]")

    async def retrieve(self, evidence_id: str) -> EvidenceEntry | None:
        """Retrieve a single EvidenceEntry by ID."""
        with self._index_lock:
            return self._index.get(evidence_id)

    async def query_by_correlation(self, correlation_id: str) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries sharing a correlation ID."""
        with self._index_lock:
            ids = self._by_correlation.get(correlation_id, [])
            return [self._index[eid] for eid in ids if eid in self._index]

    async def query_by_type(self, evidence_type: EvidenceType) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries of a given type."""
        with self._index_lock:
            ids = self._by_type.get(evidence_type, [])
            return [self._index[eid] for eid in ids if eid in self._index]

    async def query_by_component(self, component: str) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries for a component."""
        with self._index_lock:
            ids = self._by_component.get(component, [])
            return [self._index[eid] for eid in ids if eid in self._index]

    async def query_recent(
        self,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[EvidenceEntry]:
        """Retrieve most recent EvidenceEntries, optionally filtered by time."""
        with self._index_lock:
            entries = list(self._index.values())
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries[:limit]


# ---------------------------------------------------------------------------
# EvidenceEngine — main access layer
# ---------------------------------------------------------------------------


class EvidenceEngine:
    """Evidence Engine for M10 recovery (M10-T4 spec §1).

    Consumes Core Components C1-C4 via DI. Registers with ServiceRegistry as
    core.evidence_engine. Does NOT interpret evidence — only stores and retrieves.
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
        base_path: Path | None = None,
    ) -> None:
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger
        self._base_path = base_path or Path("./data")

        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")

        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        self._initialized = False
        self._registered_with_sr = False
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Evidence store (persistence layer)
        self._store = EvidenceStore(
            base_path=self._base_path,
            logger=self._logger,
            configuration=self._configuration,
        )

    # ---- ICoreManager surface ------------------------------------------------

    @property
    def name(self) -> str:
        return _NAME

    @property
    def phase(self) -> int:
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        return ["LifecycleManager"]

    @property
    def manager_id(self) -> str:
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def health_ready(self) -> bool:
        return self._initialized and self._event_bus is not None

    # ---- ICoreManager: initialization / shutdown ----------------------------

    def _read_config_int(self, path: str, default: int) -> int:
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 3 initialization (called by LifecycleManager)."""
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # Initialize evidence store
        await self._store.initialize()

        # Register with ServiceRegistry
        await self.register_with_service_registry()

        self._initialized = True
        self._log_info(f"EvidenceEngine initialized (phase {self.phase}, manager_id={_MANAGER_ID})")

    async def shutdown(self) -> None:
        """Phase 3 shutdown (called by LifecycleManager)."""
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        await self._deregister_from_service_registry()
        self._initialized = False
        self._log_info("EvidenceEngine shut down.")

    # ---- ServiceRegistry integration ----------------------------------------

    async def register_with_service_registry(self) -> None:
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering EvidenceEngine.")
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
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister.")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}")

    # ---- Evidence business API ----------------------------------------------

    def record(
        self,
        evidence_type: EvidenceType,
        component: str,
        *,
        service_id: str | None = None,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceEntry:
        """Record a new evidence entry (sync API, async persistence).

        This is the primary entry point for M10RecoveryManager, RootCauseAnalyzer,
        HealthManager, and other components to record evidence.
        """
        entry = EvidenceEntry(
            evidence_id=uuid.uuid4().hex[:16],
            evidence_type=evidence_type,
            component=component,
            service_id=service_id,
            correlation_id=correlation_id,
            payload=payload or {},
            metadata=metadata or {},
        )

        # Async persist (sync-to-async bridge)
        self._schedule_persist(entry)

        self._log_debug(
            f"Evidence recorded: {entry.evidence_type.value} for {component}",
            evidence_id=entry.evidence_id,
            component=component,
            evidence_type=entry.evidence_type.value,
        )

        return entry

    def _schedule_persist(self, entry: EvidenceEntry) -> None:
        bus = self._event_bus
        if bus is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(f"Evidence {entry.evidence_id} not persisted (no running event loop).")
            return
        if not loop.is_running():
            self._log_debug(f"Evidence {entry.evidence_id} not persisted (event loop not running).")
            return

        coro = self._store.store(entry)
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def retrieve(self, evidence_id: str) -> EvidenceEntry | None:
        """Retrieve a single EvidenceEntry by ID."""
        return await self._store.retrieve(evidence_id)

    async def query_by_correlation(self, correlation_id: str) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries sharing a correlation ID."""
        return await self._store.query_by_correlation(correlation_id)

    async def query_by_type(self, evidence_type: EvidenceType) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries of a given type."""
        return await self._store.query_by_type(evidence_type)

    async def query_by_component(self, component: str) -> list[EvidenceEntry]:
        """Retrieve all EvidenceEntries for a component."""
        return await self._store.query_by_component(component)

    async def query_recent(
        self,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[EvidenceEntry]:
        """Retrieve most recent EvidenceEntries."""
        return await self._store.query_recent(limit=limit, since=since)

    # ---- Event emission (sync-to-async bridge) -------------------------------

    def _emit_evidence_event(self, event_type: EventType, entry: EvidenceEntry) -> None:
        bus = self._event_bus
        if bus is None:
            return

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload={
                "evidence_id": entry.evidence_id,
                "evidence_type": entry.evidence_type.value,
                "component": entry.component,
                "service_id": entry.service_id,
                "correlation_id": entry.correlation_id,
                "timestamp": entry.timestamp.isoformat(),
                "manager": _NAME,
                "manager_id": _MANAGER_ID,
            },
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(f"Event {event_type.name} not dispatched (no running event loop).")
            return
        if not loop.is_running():
            self._log_debug(f"Event {event_type.name} not dispatched (event loop not running).")
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ---- StructuredLogger integration ----------------------------------------

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
# Global EvidenceEngine singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_evidence_engine: EvidenceEngine | None = None
_evidence_singleton_lock = threading.Lock()


def get_evidence_engine() -> EvidenceEngine:
    """Get or create the global EvidenceEngine singleton."""
    global _global_evidence_engine
    with _evidence_singleton_lock:
        if _global_evidence_engine is None:
            _global_evidence_engine = EvidenceEngine()
        return _global_evidence_engine


def set_evidence_engine(engine: EvidenceEngine) -> None:
    """Set the global EvidenceEngine singleton (kernel-owned construction)."""
    global _global_evidence_engine
    with _evidence_singleton_lock:
        _global_evidence_engine = engine


def reset_evidence_engine_singleton() -> None:
    """Reset the process-wide EvidenceEngine singleton (tests only)."""
    global _global_evidence_engine
    with _evidence_singleton_lock:
        _global_evidence_engine = None