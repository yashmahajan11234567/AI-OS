"""
Unit tests for the StructuredLogger sink architecture (Part 3 §3.6.10 / §3.6.6).

Covers ConsoleSink, FileSink (+ rotation / compression / retention),
EventBusSink, AuditSink (+ hash chain / tamper detection), NullSink, custom
sink support, sink registration, sink failure, retry, DEGRADED, recovery, and
failure isolation.
"""

from __future__ import annotations

import gzip
import io
import json

import pytest

from aios.core.sinks import (
    AuditSink,
    BaseSink,
    ConsoleSink,
    EventBusSink,
    FileSink,
    NullSink,
    RotationConfig,
    SinkHealth,
)
from aios.core.structured_logger import (
    LogEntry,
    LogLevel,
    StructuredLogger,
    reset_structured_logger_singleton,
)
from aios.events.core.serialization import compute_checksum

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_structured_logger_singleton()
    yield
    reset_structured_logger_singleton()


def _entry(level: str, msg: str, **fields: object) -> dict:
    """Build a serialized LogEntry dict without instantiating the logger."""
    lvl = LogLevel[level]
    entry = LogEntry(
        timestamp="2026-01-01T00:00:00+00:00",
        timestamp_monotonic=1,
        log_id="00000000-0000-0000-0000-000000000000",
        level=lvl.name,
        level_value=int(lvl),
        category="SYSTEM",
        correlation_id=None,
        causation_id=None,
        source="aios",
        logger_name="StructuredLogger",
        message=msg,
        fields=dict(fields),
    )
    return entry.to_dict()


# ---------------------------------------------------------------------------
# 14. ConsoleSink
# ---------------------------------------------------------------------------


async def test_console_sink_writes_json():
    stream = io.StringIO()
    sink = ConsoleSink(name="console", stream=stream, fmt="json")
    sink.write([_entry("INFO", "hello", k="v")])
    out = stream.getvalue().strip()
    assert out.startswith("{")
    parsed = json.loads(out)
    assert parsed["message"] == "hello"
    assert parsed["level"] == "INFO"


async def test_console_sink_pretty():
    stream = io.StringIO()
    sink = ConsoleSink(name="console", stream=stream, fmt="pretty")
    sink.write([_entry("WARN", "warned", a=1)])
    out = stream.getvalue()
    assert "WARN" in out and "warned" in out


async def test_console_sink_level_filter():
    stream = io.StringIO()
    sink = ConsoleSink(name="console", stream=stream, fmt="json", level=LogLevel.ERROR)
    sink.write([_entry("INFO", "low")])
    sink.write([_entry("ERROR", "high")])
    lines = [l for l in stream.getvalue().splitlines() if l.strip()]
    assert len(lines) == 1
    assert "high" in lines[0]


# ---------------------------------------------------------------------------
# 15-18. FileSink + rotation / compression / retention
# ---------------------------------------------------------------------------


async def test_file_sink_writes(tmp_path):
    p = tmp_path / "logs" / "app.log"
    sink = FileSink(p, name="file")
    sink.write([_entry("INFO", "line1"), _entry("ERROR", "line2")])
    sink.close()
    text = p.read_text(encoding="utf-8")
    assert "line1" in text and "line2" in text


async def test_file_rotation_size(tmp_path):
    p = tmp_path / "logs" / "app.log"
    sink = FileSink(
        p,
        name="file",
        rotation=RotationConfig(max_file_size=10, max_files=5, compress=False),
    )
    for i in range(5):
        sink.write([_entry("INFO", "rotating-line-%d" % i)])
    sink.force_rotation()
    sink.close()
    rotated = sink.rotated_paths()
    assert len(rotated) >= 1


async def test_file_compression(tmp_path):
    p = tmp_path / "logs" / "app.log"
    sink = FileSink(
        p,
        name="file",
        rotation=RotationConfig(max_file_size=10, max_files=5, compress=True),
    )
    for i in range(3):
        sink.write([_entry("INFO", "compress-line-%d" % i)])
    sink.force_rotation()
    sink.close()
    gz = [r for r in sink.rotated_paths() if str(r).endswith(".gz")]
    assert gz, "expected at least one compressed rotated file"
    with gzip.open(gz[0], "rt", encoding="utf-8") as fh:
        content = fh.read()
    assert "compress-line" in content


async def test_file_retention(tmp_path):
    p = tmp_path / "logs" / "app.log"
    sink = FileSink(
        p,
        name="file",
        rotation=RotationConfig(max_file_size=10, max_files=2, compress=False),
    )
    for i in range(6):
        sink.write([_entry("INFO", "retain-%d" % i)])
        sink.force_rotation()
    sink.close()
    rotated = sorted(sink.rotated_paths(), key=lambda x: x.name)
    assert len(rotated) <= 2


# ---------------------------------------------------------------------------
# 19. EventBusSink
# ---------------------------------------------------------------------------


async def test_eventbus_sink_publishes():
    bus = _StubBus()
    sink = EventBusSink(bus, name="eventbus", level=LogLevel.WARN)
    sink.write([_entry("WARN", "warn-msg")])
    assert len(bus.published) == 1


async def test_eventbus_sink_level_filter():
    bus = _StubBus()
    sink = EventBusSink(bus, name="eventbus", level=LogLevel.WARN)
    sink.write([_entry("INFO", "ignored")])
    assert len(bus.published) == 0


# ---------------------------------------------------------------------------
# 20-22. AuditSink + hash chain + tamper detection
# ---------------------------------------------------------------------------


async def test_audit_sink_writes(tmp_path):
    p = tmp_path / "audit" / "audit.log"
    sink = AuditSink(p, name="audit")
    sink.write([_entry("AUDIT", "a1", x=1), _entry("AUDIT", "a2", x=2)])
    sink.close()
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["level"] == "AUDIT"
    assert rec["checksum"]
    assert rec["previous_checksum"]


async def test_audit_hash_chain_links(tmp_path):
    p = tmp_path / "audit" / "audit.log"
    sink = AuditSink(p, name="audit")
    for i in range(4):
        sink.write([_entry("AUDIT", "a%d" % i)])
    sink.close()
    assert sink.verify_chain() is True


async def test_audit_tamper_detection(tmp_path):
    p = tmp_path / "audit" / "audit.log"
    sink = AuditSink(p, name="audit")
    for i in range(3):
        sink.write([_entry("AUDIT", "a%d" % i)])
    sink.close()
    lines = p.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["message"] = "TAMPERED"
    rec.pop("checksum")  # leave stale to force mismatch in verification
    lines[0] = json.dumps(rec)
    p.write_text("\n".join(lines), encoding="utf-8")
    assert sink.verify_chain() is False


async def test_audit_never_overwrites_existing(tmp_path):
    p = tmp_path / "audit" / "audit.log"
    sink = AuditSink(p, name="audit")
    sink.write([_entry("AUDIT", "a1")])
    sink.close()
    sink2 = AuditSink(p, name="audit")
    sink2.write([_entry("AUDIT", "a2")])
    sink2.close()
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# 23. NullSink
# ---------------------------------------------------------------------------


async def test_null_sink_discards():
    sink = NullSink()
    sink.write([_entry("INFO", "discard")])
    assert sink.health == SinkHealth.HEALTHY


# ---------------------------------------------------------------------------
# 24. Custom sink support (§3.6.13)
# ---------------------------------------------------------------------------


async def test_custom_sink_supported():
    sl = StructuredLogger()
    sl.register_sink(_CustomSink("custom"))
    sl.register_sink(NullSink())
    await sl.initialize()
    sl.info("via custom")
    sl.flush()
    custom = next(s for s in sl.sinks if s.name == "custom")
    assert isinstance(custom, _CustomSink)
    assert custom.written == 1


# ---------------------------------------------------------------------------
# 25-28. Sink failure / retry / DEGRADED / recovery / isolation
# ---------------------------------------------------------------------------


async def test_sink_failure_isolated():
    good = _CollectSink("good")
    bad = _FlakySink("bad", fail_times=3)
    sl = StructuredLogger()
    sl.register_sink(good)
    sl.register_sink(bad)
    await sl.initialize()
    sl.info("msg")
    sl.flush()
    assert len(good.entries) == 1
    assert bad.health == SinkHealth.DEGRADED


async def test_sink_retry_recovers():
    # Three initial failures exhaust the max-3 retry budget -> DEGRADED.
    flaky = _FlakySink("flaky", fail_times=3)
    sl = StructuredLogger()
    sl.register_sink(flaky)
    await sl.initialize()
    sl.info("msg")
    sl.flush()
    assert flaky.health == SinkHealth.DEGRADED
    # A subsequent successful write recovers the sink (INV-SL-REC-001).
    flaky._fail_remaining = 0
    sl.info("ok")
    sl.flush()
    assert flaky.health == SinkHealth.HEALTHY


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _CollectSink(BaseSink):
    def __init__(self, name: str = "collect") -> None:
        super().__init__(name)
        self.entries: list[dict] = []

    def write(self, entries: list[dict]) -> None:
        self.entries.extend(entries)


class _FlakySink(BaseSink):
    def __init__(self, name: str = "flaky", fail_times: int = 3) -> None:
        super().__init__(name)
        self._fail_remaining = fail_times

    def write(self, entries: list[dict]) -> None:
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise OSError("simulated sink failure")
        return None


class _CustomSink(BaseSink):
    """Custom sink (validates INV-SL-SNK-004 custom-sink support)."""

    def __init__(self, name: str = "custom") -> None:
        super().__init__(name)
        self.written = 0

    def write(self, entries: list[dict]) -> None:
        self.written += len(entries)


class _StubBus:
    def __init__(self) -> None:
        self.published: list = []

    def publish(self, event: object) -> int:
        self.published.append(event)
        return 1
