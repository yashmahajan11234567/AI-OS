"""
M8-T5 — Capability Provenance unit tests.

Tests for capability_provenance helpers:
- build_capability_provenance() includes the mandatory provenance contract
- mark_capability_advisory() re-asserts source/advisory/authority/trust_level
  even when caller supplies conflicting values (spoof-proof, mirrors adapter
  _mark_advisory)
- caller cannot set authority=authoritative via merge
- trust_level cannot be escalated via merge
- extra metadata (capability_version/protocol/target/errors) round-trips via
  the `extra` channel
"""

from __future__ import annotations

import pytest

from aios.core.capability_provenance import (
    assert_capability_provenance,
    build_capability_provenance,
    mark_capability_advisory,
)


def _base_kwargs(**overrides) -> dict:
    """Standard kwargs for build_capability_provenance."""
    base = dict(
        capability_id="test_cap",
        facade="test",
        provider_id="test_provider",
        adapter="TestAdapter",
        operation="execute",
        source="capability",
        correlation_id="corr-123",
        execution_id="exec-456",
        authority="advisory",
        trust_level="untrusted",
    )
    base.update(overrides)
    return base


class TestBuildCapabilityProvenance:
    """Tests for build_capability_provenance()."""

    def test_includes_all_mandatory_fields(self):
        """build_capability_provenance() includes all mandatory fields."""
        prov = build_capability_provenance(**_base_kwargs())

        mandatory = [
            "capability_id", "source", "adapter", "operation",
            "task_id", "execution_id", "correlation_id",
            "timestamp", "trust_level", "authority",
        ]
        for field in mandatory:
            assert field in prov, f"Missing mandatory field: {field}"

    def test_fields_have_correct_values(self):
        """Fields carry the values passed in."""
        prov = build_capability_provenance(
            **_base_kwargs(
                facade="test_facade",
                operation="query",
                extra={"capability_version": "2.0.0", "protocol": "mcp"},
            ),
        )

        assert prov["capability_id"] == "test_cap"
        assert prov["facade"] == "test_facade"
        assert prov["provider_id"] == "test_provider"
        assert prov["adapter"] == "TestAdapter"
        assert prov["operation"] == "query"
        assert prov["source"] == "capability"
        assert prov["correlation_id"] == "corr-123"
        assert prov["execution_id"] == "exec-456"
        assert prov["extra"]["capability_version"] == "2.0.0"
        assert prov["extra"]["protocol"] == "mcp"
        assert prov["trust_level"] == "untrusted"
        assert prov["authority"] == "advisory"

    def test_timestamp_is_iso_format(self):
        """Timestamp is an ISO timestamp string."""
        prov = build_capability_provenance(**_base_kwargs())
        assert "T" in prov["timestamp"]

    def test_auto_generated_correlation_and_request_ids(self):
        """Absent correlation/request ids are auto-generated (UUID)."""
        prov = build_capability_provenance(
            capability_id="c",
            facade="f",
            provider_id="p",
            adapter="A",
            operation="op",
            source="capability",
        )
        assert len(prov["correlation_id"]) >= 32  # UUID-shaped
        assert len(prov["request_id"]) >= 32


class TestMarkCapabilityAdvisory:
    """Tests for mark_capability_advisory() - spoof-proof re-assertion."""

    def _mark(self, result: dict, **overrides) -> dict:
        kwargs = dict(
            source="capability",
            operation="execute",
            capability_id="test_cap",
            facade="test",
            provider_id="test_provider",
            adapter="TestAdapter",
            authority="advisory",
            trust_level="untrusted",
        )
        kwargs.update(overrides)
        return mark_capability_advisory(result, **kwargs)

    def test_re_asserts_source(self):
        """mark_capability_advisory() re-asserts source."""
        marked = self._mark({"data": "t", "provenance": {"source": "malicious"}})
        assert marked["provenance"]["source"] == "capability"

    def test_re_asserts_advisory_flag(self):
        """mark_capability_advisory() re-asserts advisory=True."""
        marked = self._mark({"data": "t", "provenance": {"advisory": False}})
        assert marked["provenance"]["advisory"] is True

    def test_re_asserts_authority(self):
        """Existing authoritative claim is overwritten with the asserted value."""
        marked = self._mark(
            {"data": "t", "provenance": {"authority": "authoritative"}}
        )
        assert marked["provenance"]["authority"] == "advisory"

    def test_trust_level_cannot_be_escalated(self):
        """trust_level cannot be escalated via merge."""
        marked = self._mark({"data": "t", "provenance": {"trust_level": "trusted"}})
        assert marked["provenance"]["trust_level"] == "untrusted"

    def test_preserves_other_fields(self):
        """Non-C14 caller fields preserved; C14 fields re-asserted."""
        marked = self._mark(
            {"data": "t", "provenance": {"custom_field": "value", "source": "bad"}}
        )
        assert marked["provenance"]["custom_field"] == "value"
        assert marked["provenance"]["source"] == "capability"

    def test_carries_identity_fields(self):
        """Result provenance carries capability identity + correlation."""
        marked = self._mark({"data": "t"}, operation="query")
        prov = marked["provenance"]
        assert prov["capability_id"] == "test_cap"
        assert prov["facade"] == "test"
        assert prov["provider_id"] == "test_provider"
        assert prov["adapter"] == "TestAdapter"
        assert prov["operation"] == "query"
        assert prov["request_id"]
        assert prov["timestamp"]

    def test_extra_metadata_channel(self):
        """Structured extras ride through the extra channel and survive marking."""
        base_prov = build_capability_provenance(
            **_base_kwargs(
                extra={
                    "capability_version": "2.0.0",
                    "protocol": "mcp",
                    "target": "graphify",
                    "errors": [],
                }
            )
        )
        result = {"data": "t", "provenance": base_prov}
        marked = mark_capability_advisory(result, source="capability")

        prov = marked["provenance"]
        # Caller-supplied non-C14 fields preserved through the merge.
        assert prov["extra"]["capability_version"] == "2.0.0"
        assert prov["extra"]["protocol"] == "mcp"
        assert prov["extra"]["target"] == "graphify"
        assert prov["extra"]["errors"] == []
        # C14 fields still forced.
        assert prov["advisory"] is True


class TestProvenanceSpoofProof:
    """Provenance cannot be spoofed."""

    def test_multiple_calls_are_consistent(self):
        """Chained calls produce identical C14 assertions."""
        marked1 = mark_capability_advisory(
            {"data": "t"},
            source="capability",
            operation="execute",
            capability_id="test_cap",
            trust_level="untrusted",
        )
        marked2 = mark_capability_advisory(marked1, source="capability")

        for key in ["source", "advisory", "trust_level"]:
            assert marked1["provenance"][key] == marked2["provenance"][key]

    def test_assert_helper_validates_contract(self):
        """assert_capability_provenance validates the C14 contract."""
        good = mark_capability_advisory(
            {"data": "t"}, source="capability", trust_level="untrusted"
        )["provenance"]
        assert assert_capability_provenance(good, expected_source="capability") is True
        assert assert_capability_provenance(good, expected_trust_level="untrusted") is True

        spoofed = dict(good, advisory=False)
        assert assert_capability_provenance(spoofed) is False
        bad_missing = {k: v for k, v in good.items() if k != "timestamp"}
        assert assert_capability_provenance(bad_missing) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
