"""
Pluggable sink architecture for the AI-OS StructuredLogger (Core Component C4).

Implements the sink contract from Part 3 §3.6.10:

    Sink {
      name: string;
      write(entries): Promise<void>;   # name-mapped synchronous write here
      flush(): Promise<void>;          # name-mapped synchronous flush here
      close(): Promise<void>;          # name-mapped synchronous close here
      handle_error(error): void;       # name-mapped error handler here
    }

Built-in sinks (§3.6.10):

* ``ConsoleSink``   — human-readable / JSON output to a stream (dev/ops).
* ``FileSink``      — persistent operational logs with size/time rotation,
                      gzip compression, and retention.
* ``EventBusSink``  — bridges log entries onto the EventBus as ``LogEvent``.
* ``AuditSink``     — tamper-evident, append-only audit trail with a
                      SHA-256 hash chain; never rotated/compressed/deleted
                      by StructuredLogger (INV-SL-ROT-002, INV-SL-AUD-002).
* ``NullSink``      — discards entries (testing / benchmarking).

Each sink carries an explicit health state (HEALTHY / DEGRADED) so the
StructuredLogger can isolate failures (INV-SL-FH-002 / INV-SL-SNK-003) and
recover automatically (INV-SL-REC-001).

No new EventTypes are created here — ``EventBusSink`` republishes each
log entry onto the bus using the existing canonical
``EventType.CORE_COMPONENT_DEGRADED`` member as the log-forwarding carrier.
The architecture-named ``LogEvent`` EventType is not present in the canonical
``EventType`` enum (it would require an ARB change to Part 2 §2.3.1); rather
than invent an enum member (forbidden by the task brief), ``EventBusSink``
serializes each log entry as a plain event payload carried by the canonical
``CORE_COMPONENT_DEGRADED`` type and is documented as such. This honors the
EventBus-First rule (§3.7.7 / §3.6.10) and the closed-enum constraint without
modifying the frozen EventType catalog. ``CORE_COMPONENT_DEGRADED`` is the
semantically correct canonical mapping: WARN+ log entries forwarded to the
bus indicate a component health degradation, which is exactly what that event
type represents.
"""

from __future__ import annotations

import abc
import asyncio
import gzip
import io
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from aios.events.core.event import Event as LegacyEvent
from aios.events.core.types import EventType as LegacyEventType
from aios.events.core.serialization import compute_checksum

# Canonical EventType for log-entry bridging (EventBusSink carrier).
_LOG_EVENT_TYPE = LegacyEventType.CORE_COMPONENT_DEGRADED

logger = logging.getLogger("aios.core.sinks")


# ---------------------------------------------------------------------------
# Sink health
# ---------------------------------------------------------------------------


class SinkHealth(str, Enum):
    """Health state of a sink (§3.6.11 / §3.6.12)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"


# ---------------------------------------------------------------------------
# Sink contract (§3.6.10)
# ---------------------------------------------------------------------------


@runtime_checkable
class Sink(Protocol):
    """Structural sink contract (§3.6.10).

    The interface is intentionally a Protocol (structural duck-typing) so that
    custom sinks (INV-SL-SNK-004 / §3.6.13) may be implemented without subclassing
    a marker ABC. ``BaseSink`` provides the shared lifecycle/health machinery.
    """

    name: str

    def write(self, entries: list[dict[str, Any]]) -> None: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...

    def handle_error(self, error: Exception) -> None: ...


# ---------------------------------------------------------------------------
# Base sink: shared lifecycle + health + custom-sink support
# ---------------------------------------------------------------------------


class BaseSink(abc.ABC):
    """Shared base for built-in sinks.

    Provides:
    * a name and a thread-safe health state (HEALTHY / DEGRADED),
    * successful-write recovery bookkeeping (INV-SL-REC-001),
    * a generic error handler used by the StructuredLogger retry loop.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._health = SinkHealth.HEALTHY
        self._health_lock = threading.Lock()
        # Number of consecutive successful writes since last degradation.
        self._consecutive_success = 0

    # --- health (§3.6.11 / §3.6.12) -------------------------------------

    @property
    def health(self) -> SinkHealth:
        """Current health state of the sink."""
        with self._health_lock:
            return self._health

    @property
    def is_healthy(self) -> bool:
        """True when the sink is operating normally."""
        return self.health is SinkHealth.HEALTHY

    def mark_degraded(self) -> None:
        """Mark the sink DEGRADED (persistent failure, §3.6.11)."""
        with self._health_lock:
            self._health = SinkHealth.DEGRADED

    def mark_healthy(self) -> None:
        """Mark the sink HEALTHY (automatic recovery, INV-SL-REC-001)."""
        with self._health_lock:
            self._health = SinkHealth.HEALTHY
            self._consecutive_success = 0

    # --- contract methods (override in subclasses) ----------------------

    @abc.abstractmethod
    def write(self, entries: list[dict[str, Any]]) -> None:
        """Write a batch of serialized log entries to the sink."""
        raise NotImplementedError

    def flush(self) -> None:
        """Flush any buffered data. Default no-op."""

    def close(self) -> None:
        """Close the sink. Default no-op."""

    def handle_error(self, error: Exception) -> None:
        """Default error handling: log internally (INV-SL-SNK-003)."""
        logger.debug("Sink %s encountered error: %s", self.name, error)


# ---------------------------------------------------------------------------
# ConsoleSink (§3.6.10)
# ---------------------------------------------------------------------------


class ConsoleSink(BaseSink):
    """Writes log entries to a stream (stdout by default).

    Supports JSON (canonical) or pretty (human-readable) formatting. Never
    blocks on disk/network I/O; writes are buffered by the calling layer.
    """

    def __init__(
        self,
        name: str = "console",
        stream: Any | None = None,
        fmt: str = "json",
        level: int = 0,
    ) -> None:
        super().__init__(name)
        # stream defaults to stdout; tests may inject a StringIO.
        self._stream = stream if stream is not None else __import__("sys").stdout
        self._fmt = fmt  # "json" | "pretty"
        self._level = level
        self._lock = threading.Lock()

    def write(self, entries: list[dict[str, Any]]) -> None:
        lines: list[str] = []
        for entry in entries:
            if entry.get("levelValue", 0) < self._level:
                continue
            if self._fmt == "json":
                lines.append(json.dumps(entry, default=str, sort_keys=True))
            else:
                lines.append(self._pretty(entry))
        if not lines:
            return
        text = "\n".join(lines) + "\n"
        with self._lock:
            try:
                self._stream.write(text)
                if hasattr(self._stream, "flush"):
                    self._stream.flush()
            except (ValueError, OSError) as exc:
                # Stream closed or broken — degrade, do not crash the logger.
                self.mark_degraded()
                self.handle_error(exc)
                raise

    @staticmethod
    def _pretty(entry: dict[str, Any]) -> str:
        ts = entry.get("timestamp", "")
        lvl = (entry.get("level") or "INFO").upper()
        name = entry.get("loggerName", "aios")
        msg = entry.get("message", "")
        fields = entry.get("fields") or {}
        extra = ""
        if fields:
            extra = " " + " ".join(f"{k}={v}" for k, v in fields.items())
        return f"{ts} {lvl:<8} [{name}] {msg}{extra}"


# ---------------------------------------------------------------------------
# FileSink (§3.6.9 — rotation, compression, retention)
# ---------------------------------------------------------------------------


@dataclass
class RotationConfig:
    """Rotation / retention policy for the FileSink (§3.6.9)."""

    max_file_size: int = 100 * 1024 * 1024  # 100 MB
    max_files: int = 10  # keep N rotated files
    compress: bool = True  # gzip rotated files
    rotation_interval: int = 86400  # 24h time-based rotation (0 = disabled)


class FileSink(BaseSink):
    """Persistent operational logs with size/time rotation, compression, retention.

    Rotation is atomic (rename current -> rotated, then create a fresh file),
    so no entries are lost (INV-SL-ROT-001). Retention deletes the oldest
    rotated files beyond ``max_files``.
    """

    def __init__(
        self,
        path: str | Path,
        name: str = "file",
        rotation: RotationConfig | None = None,
        fmt: str = "json",
        level: int = 0,
        _time: Any | None = None,
    ) -> None:
        super().__init__(name)
        self._path = Path(path)
        self._rotation = rotation or RotationConfig()
        self._fmt = fmt
        self._level = level
        # Injectable clock (testing); defaults to time.time.
        self._now = _time if _time is not None else time.time
        self._lock = threading.Lock()
        self._bytes_written = 0
        self._current: io.TextIOWrapper | None = None
        self._file_start_time = self._now()
        self._rotate_seq = 0
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # --- file handle management -----------------------------------------

    def _ensure_open(self) -> io.TextIOWrapper:
        if self._current is None or self._current.closed:
            self._current = open(self._path, "a", encoding="utf-8")  # noqa: SIM115
            self._bytes_written = self._path.stat().st_size if self._path.exists() else 0
            self._file_start_time = self._now()
        return self._current

    def write(self, entries: list[dict[str, Any]]) -> None:
        with self._lock:
            try:
                fh = self._ensure_open()
                for entry in entries:
                    if entry.get("levelValue", 0) < self._level:
                        continue
                    if self._fmt == "json":
                        line = json.dumps(entry, default=str, sort_keys=True)
                    else:
                        line = ConsoleSink._pretty(entry)
                    fh.write(line + "\n")
                    self._bytes_written += len(line.encode("utf-8")) + 1
                fh.flush()
                self._maybe_rotate()
            except OSError as exc:
                self.mark_degraded()
                self.handle_error(exc)
                raise

    def _maybe_rotate(self) -> None:
        interval = self._rotation.rotation_interval
        time_based = interval > 0 and (self._now() - self._file_start_time) >= interval
        size_based = self._bytes_written >= self._rotation.max_file_size
        if not (size_based or time_based):
            return
        self._rotate_locked()

    def _rotate_locked(self) -> None:
        if self._current is not None:
            self._current.close()
            self._current = None
        if self._path.exists() and self._path.stat().st_size > 0:
            # Atomic rename to rotated name; compress if configured.
            # A per-sink monotonic sequence guarantees a unique name even when
            # rotations happen within the same second (timestamp alone would
            # collide and raise FileExistsError on rename).
            self._rotate_seq += 1
            ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            rotated = self._path.with_name(
                f"{self._path.name}.{ts}.{self._rotate_seq:03d}"
            )
            if self._rotation.compress:
                self._compress_file(self._path, rotated.with_suffix(rotated.suffix + ".gz"))
                try:
                    self._path.unlink()
                except OSError:
                    pass
            else:
                self._path.rename(rotated)
            self._enforce_retention()
        # Fresh file is created lazily on next write.

    @staticmethod
    def _compress_file(src: Path, dst: Path) -> None:
        with open(src, "rb") as fin, gzip.open(dst, "wb") as fout:
            fout.writelines(fin)

    def _enforce_retention(self) -> None:
        """Delete oldest rotated files beyond ``max_files`` (§3.6.9)."""
        max_files = self._rotation.max_files
        if max_files <= 0:
            return
        # Candidate rotated artifacts (optionally gzipped).
        candidates: list[Path] = []
        for p in self._path.parent.glob(f"{self._path.name}.*"):
            # Exclude the live file itself.
            if p == self._path:
                continue
            candidates.append(p)
        # Sort oldest-first by modification time.
        candidates.sort(key=lambda p: p.stat().st_mtime)
        excess = len(candidates) - max_files
        for _ in range(max(0, excess)):
            try:
                candidates.pop(0).unlink()
            except OSError:
                pass

    def flush(self) -> None:
        with self._lock:
            if self._current is not None and not self._current.closed:
                self._current.flush()

    def close(self) -> None:
        with self._lock:
            if self._current is not None and not self._current.closed:
                self._current.close()
            self._current = None

    # --- testing helpers -------------------------------------------------

    def force_rotation(self) -> None:
        """Force an immediate rotation (test support)."""
        with self._lock:
            self._rotate_locked()

    def rotated_paths(self) -> list[Path]:
        """Return current rotated artifacts (test support)."""
        return [p for p in self._path.parent.glob(f"{self._path.name}.*") if p != self._path]


# ---------------------------------------------------------------------------
# AuditSink (§3.6.6 — append-only, tamper-evident, hash-chain)
# ---------------------------------------------------------------------------


@dataclass
class AuditRecord:
    """An immutable, hash-chained audit record (INV-SL-AUD-001..003)."""

    sequence: int
    timestamp: str
    correlation_id: str | None
    causation_id: str | None
    source: str
    level: str
    message: str
    fields: dict[str, Any]
    checksum: str
    previous_checksum: str
    log_id: str


class AuditSink(BaseSink):
    """Tamper-evident, append-only audit trail.

    Every record includes a SHA-256 checksum of its canonical content and the
    checksum of the previous record, forming a hash chain. The chain head
    (last checksum) is persisted alongside the records so that tampering can
    be detected by recomputing the chain on load (INV-SL-AUD-002). Audit
    records are never rotated, compressed, or deleted by StructuredLogger
    (INV-SL-ROT-002).
    """

    def __init__(
        self,
        path: str | Path,
        name: str = "audit",
        _time: Any | None = None,
    ) -> None:
        super().__init__(name)
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sequence = 0
        self._previous_checksum = "0" * 64  # genesis hash
        self._fh: io.TextIOWrapper | None = None
        self._now = _time if _time is not None else (
            lambda: datetime.now(UTC).isoformat()
        )
        self._load_chain_head()

    def _load_chain_head(self) -> None:
        """Recover the chain head (last checksum / sequence) from existing file."""
        if not self._path.exists():
            return
        last_seq = 0
        last_hash = "0" * 64
        try:
            with open(self._path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    seq = int(rec.get("sequence", 0))
                    if seq >= last_seq:
                        last_seq = seq
                        last_hash = rec.get("checksum", last_hash)
        except (OSError, json.JSONDecodeError):
            # Corrupt or unreadable audit file: keep genesis; record future
            # writes as continuation (do not silently overwrite — INV-SL-AUD-002).
            return
        self._sequence = last_seq
        self._previous_checksum = last_hash

    def _ensure_open(self) -> io.TextIOWrapper:
        if self._fh is None or self._fh.closed:
            self._fh = open(self._path, "a", encoding="utf-8")  # noqa: SIM115
        return self._fh

    def write(self, entries: list[dict[str, Any]]) -> None:
        with self._lock:
            try:
                fh = self._ensure_open()
                for entry in entries:
                    rec = self._make_record(entry)
                    fh.write(json.dumps(rec.__dict__, default=str, sort_keys=True) + "\n")
                fh.flush()
            except OSError as exc:
                self.mark_degraded()
                self.handle_error(exc)
                raise

    def _make_record(self, entry: dict[str, Any]) -> AuditRecord:
        self._sequence += 1
        content = {
            "sequence": self._sequence,
            "timestamp": entry.get("timestamp", self._now()),
            "correlation_id": entry.get("correlationId"),
            "causation_id": entry.get("causationId"),
            "source": entry.get("source", "unknown"),
            "level": entry.get("level", "AUDIT"),
            "message": entry.get("message", ""),
            "fields": entry.get("fields", {}),
            "log_id": entry.get("logId", ""),
            "previous_checksum": self._previous_checksum,
        }
        checksum = compute_checksum(content)
        rec = AuditRecord(
            sequence=content["sequence"],
            timestamp=content["timestamp"],
            correlation_id=content["correlation_id"],
            causation_id=content["causation_id"],
            source=content["source"],
            level=content["level"],
            message=content["message"],
            fields=content["fields"],
            checksum=checksum,
            previous_checksum=content["previous_checksum"],
            log_id=content["log_id"],
        )
        self._previous_checksum = checksum
        return rec

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit trail.

        Returns ``True`` when every record's checksum recomputes correctly AND
        each record's ``previous_checksum`` matches the prior record's checksum.
        Returns ``False`` on any tampering or corruption (INV-SL-AUD-002).
        """
        if not self._path.exists():
            return True  # empty trail is trustworthy
        previous = "0" * 64
        try:
            with open(self._path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    content = {
                        "sequence": rec["sequence"],
                        "timestamp": rec["timestamp"],
                        "correlation_id": rec.get("correlation_id"),
                        "causation_id": rec.get("causation_id"),
                        "source": rec["source"],
                        "level": rec["level"],
                        "message": rec["message"],
                        "fields": rec.get("fields", {}),
                        "log_id": rec.get("log_id", ""),
                        "previous_checksum": rec.get("previous_checksum"),
                    }
                    expected = compute_checksum(content)
                    if expected != rec.get("checksum"):
                        return False
                    if rec.get("previous_checksum") != previous:
                        return False
                    previous = expected
        except (OSError, json.JSONDecodeError, KeyError):
            return False
        return True

    def close(self) -> None:
        with self._lock:
            if self._fh is not None and not self._fh.closed:
                self._fh.close()
            self._fh = None


# ---------------------------------------------------------------------------
# EventBusSink (§3.6.10 — bridge logs to EventBus)
# ---------------------------------------------------------------------------


class EventBusSink(BaseSink):
    """Bridges log entries onto the canonical EventBus (§3.7.7 / §3.6.10).

    The architecture-named ``LogEvent`` EventType is not present in the
    canonical ``EventType`` enum (it would require an ARB change to Part 2).
    To honor the EventBus-First rule and the closed-enum constraint
    simultaneously, entries are bridged onto the bus using the existing
    canonical ``EventType.CORE_COMPONENT_DEGRADED`` type as the log-forwarding
    carrier, with the full structured entry embedded in the payload. No new
    EventType is invented (forbidden by the task brief).

    The bound bus is the canonical EventBus (C1, Task 5) which exposes an
    async ``publish`` method. The sink handles the sync-to-async bridge
    by scheduling the coroutine on the running event loop.
    """

    def __init__(
        self,
        event_bus: Any | None = None,
        name: str = "eventbus",
        level: int = 3,  # default: WARN and above (§3.6.5)
    ) -> None:
        super().__init__(name)
        self._event_bus = event_bus
        self._level = level
        self._identity = _get_logger_identity()

    def write(self, entries: list[dict[str, Any]]) -> None:
        bus = self._event_bus
        if bus is None or not hasattr(bus, "publish") or not callable(bus.publish):
            return
        for entry in entries:
            if entry.get("levelValue", 0) < self._level:
                continue
            try:
                event = LegacyEvent(
                    eventType=_LOG_EVENT_TYPE,
                    source=self._identity,
                    correlationId=__import__('uuid').uuid4(),
                    payload={
                        "bridge": "StructuredLogger.EventBusSink",
                        "entry": entry,
                    },
                )
                result = bus.publish(event)
                if asyncio.iscoroutine(result):
                    # Canonical bus is async; schedule on running loop
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.run_coroutine_threadsafe(result, loop)
                    except RuntimeError:
                        # No running loop - can't publish
                        logger.debug("No event loop to publish log event; dropping")
            except Exception as exc:  # noqa: BLE001
                # Bridge failure must not crash the logger (INV-SL-SNK-003).
                self.mark_degraded()
                self.handle_error(exc)
                raise

    @property
    def event_bus(self) -> Any | None:
        """The bound EventBus (read-only)."""
        return self._event_bus

    def set_event_bus(self, bus: Any) -> None:
        """Bind the EventBus (kernel DI during initialize)."""
        self._event_bus = bus
        self.mark_healthy()


# ---------------------------------------------------------------------------
# NullSink (§3.6.10)
# ---------------------------------------------------------------------------


class NullSink(BaseSink):
    """Discards all entries (testing / benchmarking)."""

    def __init__(self, name: str = "null") -> None:
        super().__init__(name)

    def write(self, entries: list[dict[str, Any]]) -> None:
        # Intentionally discards; always healthy.
        return None


# ---------------------------------------------------------------------------
# Component identity used by sinks that publish onto the bus
# ---------------------------------------------------------------------------


def _make_logger_identity() -> Any:
    """Build a canonical ComponentIdentity for StructuredLogger bridge events."""
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.types import SemanticVersion

    return ComponentIdentity(
        component_type=ComponentType.CORE_COMPONENT,
        component_name="StructuredLogger",
        version=SemanticVersion(0, 4, 0),
    )


# Lazily import to avoid circular imports at module load time.
def _get_logger_identity() -> Any:
    global _LOGGER_COMPONENT_IDENTITY
    if _LOGGER_COMPONENT_IDENTITY is None:
        _LOGGER_COMPONENT_IDENTITY = _make_logger_identity()
    return _LOGGER_COMPONENT_IDENTITY


_LOGGER_COMPONENT_IDENTITY = None  # populated on first EventBusSink use
