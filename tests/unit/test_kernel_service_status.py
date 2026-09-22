"""
Unit tests for Kernel get_service_status method.
Focused regression test for ServiceStatus started_at handling.
"""
import pytest
from datetime import datetime, timezone
from aios.core.kernel import HermesKernel, KernelConfig, ServiceStatus


def test_get_service_status_with_none_started_at():
    """Test that get_service_status handles ServiceStatus with started_at=None correctly."""
    # Arrange
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Manually add a service with started_at=None to simulate the edge case
    kernel._services["test_service"] = ServiceStatus(
        name="test_service",
        started=True,
        healthy=True,
        started_at=None,  # This is the case that was causing AttributeError
        last_error=None
    )

    # Act
    status_dict = kernel.get_service_status()

    # Assert
    assert "test_service" in status_dict
    service_status = status_dict["test_service"]
    assert service_status["started"] is True
    assert service_status["healthy"] is True
    assert service_status["started_at"] is None  # Should be None, not raise AttributeError
    assert service_status["last_error"] is None


def test_get_service_status_with_datetime_started_at():
    """Test that get_service_status handles ServiceStatus with datetime started_at correctly."""
    # Arrange
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Fixed datetime for consistent testing
    test_datetime = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Manually add a service with started_at=datetime
    kernel._services["test_service"] = ServiceStatus(
        name="test_service",
        started=True,
        healthy=True,
        started_at=test_datetime,
        last_error=None
    )

    # Act
    status_dict = kernel.get_service_status()

    # Assert
    assert "test_service" in status_dict
    service_status = status_dict["test_service"]
    assert service_status["started"] is True
    assert service_status["healthy"] is True
    assert service_status["started_at"] == test_datetime.isoformat()  # Should be ISO format string
    assert service_status["last_error"] is None


def test_get_service_status_mixed_values():
    """Test that get_service_status handles mixed started_at values correctly."""
    # Arrange
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Add service with None started_at
    kernel._services["service_none"] = ServiceStatus(
        name="service_none",
        started=True,
        healthy=False,
        started_at=None,
        last_error="Some error"
    )

    # Add service with datetime started_at
    test_datetime = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
    kernel._services["service_datetime"] = ServiceStatus(
        name="service_datetime",
        started=False,
        healthy=True,
        started_at=test_datetime,
        last_error=None
    )

    # Act
    status_dict = kernel.get_service_status()

    # Assert
    assert "service_none" in status_dict
    assert "service_datetime" in status_dict

    # Check service with None started_at
    none_status = status_dict["service_none"]
    assert none_status["started"] is True
    assert none_status["healthy"] is False
    assert none_status["started_at"] is None  # Should be None
    assert none_status["last_error"] == "Some error"

    # Check service with datetime started_at
    datetime_status = status_dict["service_datetime"]
    assert datetime_status["started"] is False
    assert datetime_status["healthy"] is True
    assert datetime_status["started_at"] == test_datetime.isoformat()  # Should be ISO format
    assert datetime_status["last_error"] is None