"""
M8-T5 — Capability Provenance Helpers.

Provides standardized provenance metadata for capability execution results.
Implements C14-compliant provenance with spoof-proof re-assertion of advisory fields.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Provenance Data Structures
# ---------------------------------------------------------------------------


@dataclass
class CapabilityProvenance:
    """
    Immutable provenance metadata for a capability execution.

    Fields are designed to be spoof-proof: when re-asserted via
    `mark_capability_advisory()`, the C14 constants (source, advisory, authority,
    trust_level) override any externally-provided values.
    """

    source: str
    adapter: str
    operation: str
    correlation_id: str
    execution_id: str | None = None
    task_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    authority: str = "contextual"
    advisory: bool = True
    trust_level: str = "untrusted"
    capability_id: str | None = None
    facade: str | None = None
    provider_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "source": self.source,
            "adapter": self.adapter,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "version": self.version,
            "authority": self.authority,
            "advisory": self.advisory,
            "trust_level": self.trust_level,
        }
        if self.capability_id is not None:
            result["capability_id"] = self.capability_id
        if self.facade is not None:
            result["facade"] = self.facade
        if self.provider_id is not None:
            result["provider_id"] = self.provider_id
        if self.extra:
            result["extra"] = self.extra
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityProvenance":
        """Create from dictionary (used for re-assertion)."""
        # Extract known fields, put rest in extra
        known_fields = {
            "source",
            "adapter",
            "operation",
            "correlation_id",
            "execution_id",
            "task_id",
            "timestamp",
            "request_id",
            "version",
            "authority",
            "advisory",
            "trust_level",
            "capability_id",
            "facade",
            "provider_id",
        }
        extra = {k: v for k, v in data.items() if k not in known_fields}
        return cls(
            source=data.get("source", "unknown"),
            adapter=data.get("adapter", "unknown"),
            operation=data.get("operation", "unknown"),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            execution_id=data.get("execution_id"),
            task_id=data.get("task_id"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            request_id=data.get("request_id", str(uuid.uuid4())),
            version=data.get("version", 1),
            authority=data.get("authority", "contextual"),
            advisory=data.get("advisory", True),
            trust_level=data.get("trust_level", "untrusted"),
            capability_id=data.get("capability_id"),
            facade=data.get("facade"),
            provider_id=data.get("provider_id"),
            extra=extra,
        )


# ---------------------------------------------------------------------------
# Provenance Builders
# ---------------------------------------------------------------------------


def build_capability_provenance(
    *,
    capability_id: str,
    facade: str,
    provider_id: str,
    adapter: str,
    operation: str,
    source: str,
    correlation_id: str | None = None,
    execution_id: str | None = None,
    task_id: str | None = None,
    authority: str = "contextual",
    advisory: bool = True,
    trust_level: str = "untrusted",
    version: int = 1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a standardized capability provenance dictionary.

    This is the primary entry point for creating provenance metadata that
    will be attached to capability execution results.

    Args:
        capability_id: The capability identifier
        facade: The facade interface identifier
        provider_id: The provider identifier
        adapter: The adapter class name
        operation: The operation being performed
        source: The data source (e.g., "notion", "obsidian", "graphify")
        correlation_id: Optional correlation ID for request tracing
        execution_id: Optional execution ID
        task_id: Optional task ID
        authority: Authority classification (default: contextual)
        advisory: Advisory flag (default: True)
        trust_level: Trust level (default: untrusted)
        version: Provenance version (default: 1)
        extra: Additional metadata

    Returns:
        Dictionary containing full provenance metadata
    """
    provenance = CapabilityProvenance(
        source=source,
        adapter=adapter,
        operation=operation,
        correlation_id=correlation_id or str(uuid.uuid4()),
        execution_id=execution_id,
        task_id=task_id,
        authority=authority,
        advisory=advisory,
        trust_level=trust_level,
        capability_id=capability_id,
        facade=facade,
        provider_id=provider_id,
        version=version,
        extra=extra or {},
    )
    return provenance.to_dict()


def mark_capability_advisory(
    metadata: dict[str, Any],
    *,
    source: str,
    operation: str | None = None,
    capability_id: str | None = None,
    facade: str | None = None,
    provider_id: str | None = None,
    adapter: str | None = None,
    authority: str = "contextual",
    trust_level: str = "untrusted",
) -> dict[str, Any]:
    """
    Mark metadata as advisory per C14 with spoof-proof re-assertion.

    This function is the C14 compliance gate — it takes externally-sourced
    metadata (e.g., from an MCP server response) and wraps it with provenance
    that CANNOT be overridden by the external source.

    The following fields are FORCE-SET and cannot be overridden:
    - source: The data source identifier
    - advisory: Always True for external capabilities
    - authority: Always "contextual" for external capabilities
    - trust_level: Always "untrusted" for external capabilities

    Args:
        metadata: The external metadata to mark (may already contain provenance)
        source: The data source identifier (e.g., "notion", "obsidian", "graphify")
        operation: Optional operation name
        capability_id: Optional capability identifier
        facade: Optional facade identifier
        provider_id: Optional provider identifier
        adapter: Optional adapter name
        authority: Authority classification (default: contextual, forced)
        trust_level: Trust level (default: untrusted, forced)

    Returns:
        The input metadata with advisory provenance re-asserted
    """
    marked = dict(metadata)

    # Build base provenance with C14 constants (these CANNOT be overridden)
    base_provenance = {
        "source": source,
        "advisory": True,
        "authority": authority,
        "trust_level": trust_level,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": str(uuid.uuid4()),
    }

    # Add optional identifying fields
    if operation is not None:
        base_provenance["operation"] = operation
    if capability_id is not None:
        base_provenance["capability_id"] = capability_id
    if facade is not None:
        base_provenance["facade"] = facade
    if provider_id is not None:
        base_provenance["provider_id"] = provider_id
    if adapter is not None:
        base_provenance["adapter"] = adapter

    # Merge with existing provenance (caller-supplied takes precedence for non-C14 fields)
    existing_provenance = marked.get("provenance", {})
    merged_provenance = {**existing_provenance, **base_provenance}

    # Re-apply C14 constants to ensure they cannot be overridden
    merged_provenance.update(
        {
            "source": source,
            "advisory": True,
            "authority": authority,
            "trust_level": trust_level,
        }
    )

    marked["provenance"] = merged_provenance
    return marked


def assert_capability_provenance(
    provenance: dict[str, Any],
    expected_source: str | None = None,
    expected_advisory: bool = True,
    expected_authority: str | None = None,
    expected_trust_level: str | None = None,
) -> bool:
    """
    Assert that provenance meets expected C14 requirements.

    Used by consumers (e.g., skill execution layer, testing council) to verify
    that capability results carry the correct provenance markers.

    Args:
        provenance: Provenance dictionary to validate
        expected_source: Expected source (optional)
        expected_advisory: Expected advisory flag (default: True)
        expected_authority: Expected authority (optional)
        expected_trust_level: Expected trust level (optional)

    Returns:
        True if all assertions pass
    """
    if not isinstance(provenance, dict):
        return False

    if expected_source is not None and provenance.get("source") != expected_source:
        return False
    if provenance.get("advisory") != expected_advisory:
        return False
    if expected_authority is not None and provenance.get("authority") != expected_authority:
        return False
    if expected_trust_level is not None and provenance.get("trust_level") != expected_trust_level:
        return False

    # Required fields must be present
    required = ("source", "advisory", "authority", "trust_level", "timestamp", "request_id")
    return all(field in provenance for field in required)


# ---------------------------------------------------------------------------
# Convenience: Provenance enrichment for ExecutionResult
# ---------------------------------------------------------------------------


def enrich_execution_result_provenance(
    result: Any,
    *,
    capability_id: str,
    facade: str,
    provider_id: str,
    adapter: str,
    operation: str,
    source: str,
    authority: str = "contextual",
    trust_level: str = "untrusted",
) -> Any:
    """
    Enrich an ExecutionResult with capability provenance.

    Handles both dict-based raw results and ExecutionResult objects with
    a `raw` attribute. Re-asserts C14 advisory markers on all nested results.

    Args:
        result: ExecutionResult or raw result dict
        capability_id: Capability identifier
        facade: Facade identifier
        provider_id: Provider identifier
        adapter: Adapter name
        operation: Operation name
        source: Data source
        authority: Authority classification
        trust_level: Trust level

    Returns:
        The enriched result (same object, modified in place)
    """
    # Build provenance
    provenance = build_capability_provenance(
        capability_id=capability_id,
        facade=facade,
        provider_id=provider_id,
        adapter=adapter,
        operation=operation,
        source=source,
        authority=authority,
        trust_level=trust_level,
    )

    # Handle ExecutionResult with raw attribute
    if hasattr(result, "raw"):
        if isinstance(result.raw, dict):
            mark_capability_advisory(
                result.raw,
                source=source,
                operation=operation,
                capability_id=capability_id,
                facade=facade,
                provider_id=provider_id,
                adapter=adapter,
                authority=authority,
                trust_level=trust_level,
            )
        elif isinstance(result.raw, list):
            for item in result.raw:
                if isinstance(item, dict):
                    mark_capability_advisory(
                        item,
                        source=source,
                        operation=operation,
                        capability_id=capability_id,
                        facade=facade,
                        provider_id=provider_id,
                        adapter=adapter,
                        authority=authority,
                        trust_level=trust_level,
                    )
    # Handle dict-based raw result
    elif isinstance(result, dict):
        mark_capability_advisory(
            result,
            source=source,
            operation=operation,
            capability_id=capability_id,
            facade=facade,
            provider_id=provider_id,
            adapter=adapter,
            authority=authority,
            trust_level=trust_level,
        )
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                mark_capability_advisory(
                    item,
                    source=source,
                    operation=operation,
                    capability_id=capability_id,
                    facade=facade,
                    provider_id=provider_id,
                    adapter=adapter,
                    authority=authority,
                    trust_level=trust_level,
                )

    # Also ensure top-level provenance on the result object itself
    if hasattr(result, "provenance"):
        result.provenance = provenance
    elif isinstance(result, dict):
        result["provenance"] = provenance

    return result


__all__ = [
    "CapabilityProvenance",
    "build_capability_provenance",
    "mark_capability_advisory",
    "assert_capability_provenance",
    "enrich_execution_result_provenance",
]