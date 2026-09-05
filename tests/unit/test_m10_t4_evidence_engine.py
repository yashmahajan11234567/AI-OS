"""
M10-T4 Evidence Engine Unit Tests.

Tests for EvidenceEngine and EvidenceStore per M10-T4 spec §1-2.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from aios.core.evidence_engine import (
    EvidenceEngine,
    EvidenceStore,
    EvidenceType,
    EvidenceEntry,
    get_evidence_engine,
    set_evidence_engine,
    reset_evidence_engine_singleton,
)
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, reset_service_registry_singleton, get_service_registry
from aios.core.structured_logger import StructuredLogger, get_logger, set_logger
from aios.events.core.bus import EventBus, EventBusConfig, get_core_event_bus, reset_core_event_bus_singleton
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion


@pytest.fixture
def temp_path():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def core_components(temp_path):
    """Create core components for testing."""
    # Reset singletons
    reset_core_event_bus_singleton()
    reset_service_registry_singleton()
    from aios.core.configuration_manager import reset_configuration_manager_singleton
    reset_configuration_manager_singleton()
    reset_evidence_engine_singleton()

    # EventBus
    event_bus_config = EventBusConfig(auto_start_dispatch_worker=False)
    event_bus = EventBus(config=event_bus_config)
    await event_bus.initialize()

    # ServiceRegistry
    service_registry = get_service_registry(event_bus=event_bus)

    # ConfigurationManager
    from aios.core.configuration_manager import get_configuration_manager
    config_manager = get_configuration_manager(event_bus=event_bus, config_path=None)
    await config_manager.initialize()
    config_manager.freeze()

    # StructuredLogger
    logger = get_logger()
    await logger.initialize(MagicMock())

    yield {
        'event_bus': event_bus,
        'service_registry': service_registry,
        'configuration': config_manager,
        'logger': logger,
        'temp_path': temp_path,
    }

    # Cleanup
    await event_bus.shutdown()


@pytest.fixture
async def evidence_engine(core_components):
    """Create an EvidenceEngine instance."""
    reset_evidence_engine_singleton()
    engine = EvidenceEngine(
        service_registry=core_components['service_registry'],
        configuration_manager=core_components['configuration'],
        logger=core_components['logger'],
        base_path=core_components['temp_path'],
    )
    await engine.initialize()
    yield engine
    await engine.shutdown()
    reset_evidence_engine_singleton()


class TestEvidenceEntry:
    """Tests for EvidenceEntry data class."""

    def test_create_entry(self):
        """Test creating an EvidenceEntry."""
        entry = EvidenceEntry(
            evidence_id="test-123",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test_component",
            service_id="engineering.test_service",
            correlation_id="corr-456",
            payload={"error": "test error"},
            metadata={"key": "value"},
        )

        assert entry.evidence_id == "test-123"
        assert entry.evidence_type == EvidenceType.SERVICE_FAILURE
        assert entry.component == "test_component"
        assert entry.service_id == "engineering.test_service"
        assert entry.correlation_id == "corr-456"
        assert entry.payload == {"error": "test error"}
        assert entry.metadata == {"key": "value"}

    def test_to_dict(self):
        """Test EvidenceEntry.to_dict()."""
        entry = EvidenceEntry(
            evidence_id="test-123",
            evidence_type=EvidenceType.HEALTH_DEGRADATION,
            component="health_manager",
        )
        data = entry.to_dict()

        assert data["evidence_id"] == "test-123"
        assert data["evidence_type"] == "health_degradation"
        assert "timestamp" in data

    def test_from_dict(self):
        """Test EvidenceEntry.from_dict()."""
        data = {
            "evidence_id": "test-123",
            "evidence_type": "security_violation",
            "component": "security_manager",
            "service_id": "engineering.test",
            "correlation_id": "corr-789",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"violation": "test"},
            "metadata": {"meta": "data"},
        }
        entry = EvidenceEntry.from_dict(data)

        assert entry.evidence_id == "test-123"
        assert entry.evidence_type == EvidenceType.SECURITY_VIOLATION
        assert entry.component == "security_manager"
        assert entry.service_id == "engineering.test"
        assert entry.correlation_id == "corr-789"
        assert entry.payload == {"violation": "test"}
        assert entry.metadata == {"meta": "data"}


class TestEvidenceStore:
    """Tests for EvidenceStore persistence layer."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, temp_path):
        """Test storing and retrieving evidence."""
        store = EvidenceStore(base_path=temp_path)
        await store.initialize()

        entry = EvidenceEntry(
            evidence_id="test-123",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test_component",
            correlation_id="corr-456",
            payload={"error": "test"},
        )

        await store.store(entry)
        retrieved = await store.retrieve("test-123")

        assert retrieved is not None
        assert retrieved.evidence_id == "test-123"
        assert retrieved.evidence_type == EvidenceType.SERVICE_FAILURE
        assert retrieved.component == "test_component"
        assert retrieved.correlation_id == "corr-456"
        assert retrieved.payload == {"error": "test"}

    @pytest.mark.asyncio
    async def test_query_by_correlation(self, temp_path):
        """Test querying by correlation ID."""
        store = EvidenceStore(base_path=temp_path)
        await store.initialize()

        corr_id = "corr-789"
        entries = [
            EvidenceEntry(
                evidence_id=f"entry-{i}",
                evidence_type=EvidenceType.SERVICE_FAILURE,
                component="test",
                correlation_id=corr_id,
                payload={"num": i},
            )
            for i in range(3)
        ]

        for entry in entries:
            await store.store(entry)

        results = await store.query_by_correlation(corr_id)

        assert len(results) == 3
        assert all(e.correlation_id == corr_id for e in results)

    @pytest.mark.asyncio
    async def test_query_by_type(self, temp_path):
        """Test querying by evidence type."""
        store = EvidenceStore(base_path=temp_path)
        await store.initialize()

        await store.store(EvidenceEntry(
            evidence_id="a",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test",
        ))
        await store.store(EvidenceEntry(
            evidence_id="b",
            evidence_type=EvidenceType.HEALTH_DEGRADATION,
            component="test",
        ))
        await store.store(EvidenceEntry(
            evidence_id="c",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test",
        ))

        failures = await store.query_by_type(EvidenceType.SERVICE_FAILURE)
        degradations = await store.query_by_type(EvidenceType.HEALTH_DEGRADATION)

        assert len(failures) == 2
        assert len(degradations) == 1

    @pytest.mark.asyncio
    async def test_query_by_component(self, temp_path):
        """Test querying by component."""
        store = EvidenceStore(base_path=temp_path)
        await store.initialize()

        await store.store(EvidenceEntry(
            evidence_id="a",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="component_a",
        ))
        await store.store(EvidenceEntry(
            evidence_id="b",
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="component_b",
        ))

        results = await store.query_by_component("component_a")

        assert len(results) == 1
        assert results[0].component == "component_a"

    @pytest.mark.asyncio
    async def test_query_recent(self, temp_path):
        """Test querying recent entries."""
        store = EvidenceStore(base_path=temp_path)
        await store.initialize()

        for i in range(5):
            await store.store(EvidenceEntry(
                evidence_id=f"entry-{i}",
                evidence_type=EvidenceType.SERVICE_FAILURE,
                component="test",
                payload={"index": i},
            ))
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)

        recent = await store.query_recent(limit=3)

        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0].payload["index"] == 4
        assert recent[1].payload["index"] == 3
        assert recent[2].payload["index"] == 2


class TestEvidenceEngine:
    """Tests for EvidenceEngine main access layer."""

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self, core_components):
        """Test EvidenceEngine initialization and shutdown."""
        reset_evidence_engine_singleton()
        engine = EvidenceEngine(
            service_registry=core_components['service_registry'],
            configuration_manager=core_components['configuration'],
            logger=core_components['logger'],
            base_path=core_components['temp_path'],
        )

        assert not engine.is_initialized

        await engine.initialize()

        assert engine.is_initialized
        assert engine.health_ready()
        assert engine.name == "EvidenceEngine"
        assert engine.phase == 3
        assert engine.manager_id == "core.evidence_engine"

        await engine.shutdown()

        assert not engine.is_initialized
        reset_evidence_engine_singleton()

    @pytest.mark.asyncio
    async def test_record_evidence(self, evidence_engine):
        """Test recording evidence via EvidenceEngine."""
        entry = evidence_engine.record(
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test_service",
            service_id="engineering.test_service",
            correlation_id="corr-123",
            payload={"error": "connection failed"},
            metadata={"attempt": 3},
        )

        assert entry is not None
        assert entry.evidence_type == EvidenceType.SERVICE_FAILURE
        assert entry.component == "test_service"
        assert entry.service_id == "engineering.test_service"
        assert entry.correlation_id == "corr-123"
        assert entry.payload == {"error": "connection failed"}
        assert entry.metadata == {"attempt": 3}

    @pytest.mark.asyncio
    async def test_retrieve_evidence(self, evidence_engine):
        """Test retrieving evidence by ID."""
        entry = evidence_engine.record(
            evidence_type=EvidenceType.HEALTH_DEGRADATION,
            component="health_manager",
            payload={"status": "DEGRADED"},
        )

        # Allow async persistence to complete
        await asyncio.sleep(0.1)

        retrieved = await evidence_engine.retrieve(entry.evidence_id)

        assert retrieved is not None
        assert retrieved.evidence_id == entry.evidence_id
        assert retrieved.evidence_type == EvidenceType.HEALTH_DEGRADATION

    @pytest.mark.asyncio
    async def test_query_by_correlation(self, evidence_engine):
        """Test querying evidence by correlation ID."""
        corr_id = "test-corr-789"
        for i in range(3):
            evidence_engine.record(
                evidence_type=EvidenceType.SERVICE_FAILURE,
                component="service",
                correlation_id=corr_id,
                payload={"seq": i},
            )

        # Allow async persistence to complete
        await asyncio.sleep(0.1)

        results = await evidence_engine.query_by_correlation(corr_id)

        assert len(results) == 3
        assert all(r.correlation_id == corr_id for r in results)

    @pytest.mark.asyncio
    async def test_query_by_type(self, evidence_engine):
        """Test querying evidence by type."""
        evidence_engine.record(
            evidence_type=EvidenceType.SECURITY_VIOLATION,
            component="security_manager",
        )
        evidence_engine.record(
            evidence_type=EvidenceType.RESOURCE_EXHAUSTION,
            component="resource_manager",
        )

        await asyncio.sleep(0.1)

        security = await evidence_engine.query_by_type(EvidenceType.SECURITY_VIOLATION)
        resource = await evidence_engine.query_by_type(EvidenceType.RESOURCE_EXHAUSTION)

        assert len(security) == 1
        assert len(resource) == 1

    @pytest.mark.asyncio
    async def test_query_by_component(self, evidence_engine):
        """Test querying evidence by component."""
        evidence_engine.record(
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="service_a",
        )
        evidence_engine.record(
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="service_b",
        )

        await asyncio.sleep(0.1)

        results = await evidence_engine.query_by_component("service_a")

        assert len(results) == 1
        assert results[0].component == "service_a"

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, core_components):
        """Test EvidenceEngine singleton pattern."""
        reset_evidence_engine_singleton()

        engine1 = get_evidence_engine()
        # Need to initialize manually since we bypass constructor
        engine1._service_registry = core_components['service_registry']
        engine1._configuration = core_components['configuration']
        engine1._logger = core_components['logger']
        engine1._base_path = core_components['temp_path']
        await engine1.initialize()

        engine2 = get_evidence_engine()

        assert engine1 is engine2

        await engine1.shutdown()
        reset_evidence_engine_singleton()


class TestEvidenceEngineIntegration:
    """Integration tests for EvidenceEngine with M10RecoveryManager."""

    @pytest.mark.asyncio
    async def test_evidence_survives_engine_restart(self, core_components, temp_path):
        """Test that persisted evidence survives engine restart."""
        # Create first engine and record evidence
        reset_evidence_engine_singleton()
        engine1 = EvidenceEngine(
            service_registry=core_components['service_registry'],
            configuration_manager=core_components['configuration'],
            logger=core_components['logger'],
            base_path=temp_path,
        )
        await engine1.initialize()

        entry = engine1.record(
            evidence_type=EvidenceType.SERVICE_FAILURE,
            component="test_service",
            correlation_id="persist-test",
            payload={"important": "data"},
        )
        await asyncio.sleep(0.1)  # Allow persistence

        await engine1.shutdown()
        reset_evidence_engine_singleton()

        # Create second engine with same path
        engine2 = EvidenceEngine(
            service_registry=core_components['service_registry'],
            configuration_manager=core_components['configuration'],
            logger=core_components['logger'],
            base_path=temp_path,
        )
        await engine2.initialize()

        retrieved = await engine2.retrieve(entry.evidence_id)

        assert retrieved is not None
        assert retrieved.payload == {"important": "data"}
        assert retrieved.correlation_id == "persist-test"

        await engine2.shutdown()
        reset_evidence_engine_singleton()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])