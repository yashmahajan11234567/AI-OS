"""
Unit tests for ModelRouter timestamped usage accounting.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from aios.core.model_router import ModelRouter, UsageRecord


def test_usage_record_creation():
    """Test UsageRecord dataclass creation."""
    now = datetime.now(timezone.utc)
    record = UsageRecord(
        timestamp=now,
        provider_id="test-provider",
        model_id="test-model",
        request_count=1,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost=0.001,
        latency_ms=100,
        success=True,
    )

    assert record.timestamp == now
    assert record.provider_id == "test-provider"
    assert record.model_id == "test-model"
    assert record.request_count == 1
    assert record.input_tokens == 100
    assert record.output_tokens == 50
    assert record.total_tokens == 150
    assert record.cost == 0.001
    assert record.latency_ms == 100
    assert record.success is True


def test_model_router_usage_recording():
    """Test that ModelRouter records usage correctly."""
    router = ModelRouter()

    # Initially no records
    assert len(router._usage_records) == 0

    # Record usage manually
    router._record_usage(
        model_id="claude-sonnet-4",
        provider_id="anthropic",
        input_tokens=100,
        output_tokens=50,
        cost=0.002,
        latency_ms=150,
        success=True,
    )

    assert len(router._usage_records) == 1
    record = router._usage_records[0]
    assert record.model_id == "claude-sonnet-4"
    assert record.provider_id == "anthropic"
    assert record.input_tokens == 100
    assert record.output_tokens == 50
    assert record.cost == 0.002
    assert record.latency_ms == 150
    assert record.success is True
    # Verify timestamp is timezone-aware UTC
    assert record.timestamp.tzinfo is not None


def test_get_usage_in_time_window():
    """Test time-window query functionality."""
    router = ModelRouter()
    now = datetime.now(timezone.utc)

    # Add a recent record
    router._record_usage(
        model_id="test-model",
        provider_id="test-provider",
        input_tokens=10,
        output_tokens=5,
        cost=0.0001,
        latency_ms=50,
        success=True,
    )

    # Query for records in the last minute
    recent_records = router.get_usage_in_time_window(
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(minutes=1),
    )
    assert len(recent_records) == 1
    assert recent_records[0].model_id == "test-model"

    # Query for records in the distant past (should be empty)
    past_records = router.get_usage_in_time_window(
        start_time=now - timedelta(days=1),
        end_time=now - timedelta(hours=23),
    )
    assert len(past_records) == 0

    # Query with model filter
    filtered_records = router.get_usage_in_time_window(
        model_id="test-model",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(minutes=1),
    )
    assert len(filtered_records) == 1

    # Query with non-matching model filter
    filtered_records = router.get_usage_in_time_window(
        model_id="nonexistent-model",
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(minutes=1),
    )
    assert len(filtered_records) == 0


def test_usage_record_timestamp_is_utc_aware():
    """Test that usage records have timezone-aware UTC timestamps."""
    router = ModelRouter()
    router._record_usage(
        model_id="test-model",
        provider_id="test-provider",
        input_tokens=10,
        output_tokens=5,
        cost=0.0001,
        latency_ms=50,
        success=True,
    )

    assert len(router._usage_records) == 1
    record = router._usage_records[0]
    # Should be timezone-aware
    assert record.timestamp.tzinfo is not None
    # Should be UTC (offset should be equivalent to timezone.utc)
    assert record.timestamp.utcoffset() == datetime.now(timezone.utc).utcoffset()


def test_retention_cleanup_mechanism():
    """Test that the retention cleanup mechanism exists and can be called."""
    router = ModelRouter()
    # Set very short retention for testing
    router._retention_hours = 0.0001  # ~0.36 seconds

    now = datetime.now(timezone.utc)

    # Add a record
    router._record_usage(
        model_id="test-model",
        provider_id="test-provider",
        input_tokens=10,
        output_tokens=5,
        cost=0.0001,
        latency_ms=50,
        success=True,
    )

    assert len(router._usage_records) == 1

    # Call cleanup directly
    router._cleanup_expired_records()

    # The record should still be there since it's very recent
    assert len(router._usage_records) == 1

    # Test that calling cleanup multiple times doesn't break anything
    router._cleanup_expired_records()
    router._cleanup_expired_records()
    assert len(router._usage_records) == 1


def test_existing_usage_stats_preserved():
    """Test that existing _usage_stats functionality is preserved alongside new usage records."""
    router = ModelRouter()

    # Check initial stats
    initial_stats = router.get_usage_stats("claude-sonnet-4")
    assert initial_stats["requests"] == 0
    assert initial_stats["tokens_in"] == 0
    assert initial_stats["tokens_out"] == 0
    assert initial_stats["total_cost"] == 0.0
    assert initial_stats["errors"] == 0
    assert initial_stats["avg_latency_ms"] == 0

    # Manually record usage (this should not affect _usage_stats)
    router._record_usage(
        model_id="claude-sonnet-4",
        provider_id="anthropic",
        input_tokens=100,
        output_tokens=50,
        cost=0.002,
        latency_ms=150,
        success=True,
    )

    # _usage_stats should still be zero since we didn't go through the normal update path
    stats_after_manual_record = router.get_usage_stats("claude-sonnet-4")
    assert stats_after_manual_record["requests"] == 0
    assert stats_after_manual_record["tokens_in"] == 0
    assert stats_after_manual_record["tokens_out"] == 0
    assert stats_after_manual_record["total_cost"] == 0.0
    assert stats_after_manual_record["errors"] == 0
    assert stats_after_manual_record["avg_latency_ms"] == 0

    # But we should have a usage record
    assert len(router._usage_records) == 1


if __name__ == "__main__":
    test_usage_record_creation()
    test_model_router_usage_recording()
    test_get_usage_in_time_window()
    test_usage_record_timestamp_is_utc_aware()
    test_retention_cleanup_mechanism()
    test_existing_usage_stats_preserved()
    print("\nAll timestamped usage accounting tests passed!")