"""
Capability Provenance Extensions for AI-OS M10.

Extends CapabilityProvenance with autonomous authority fields and
spoof-proof re-assertion for self-directed actions.

This is M10-N6 implementation per M10-IMPLEMENTATION-SPEC.md §11.6.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.core.capability_provenance import CapabilityProvenance
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class ProvenanceSource(str, Enum):
    """Source of provenance data."""
    EXTERNAL = "external"  # External system (MCP, API, etc.)
    GENERATED = "generated"  # Internally generated
    STORED = "stored"  # Retrieved from storage


class ProvenanceAuthority(str, Enum):
    """Authority levels for capability provenance."""
    HUMAN = "human"  # Human-initiated
    ADVISORY = "advisory"  # Advisory-only (M8/M9)
    AUTONOMOUS = "autonomous"  # Fully autonomous (M10)
    SYSTEM = "system"  # System-internal


@dataclass
class CapabilityProvenanceConfig:
    """Configuration for autonomous provenance extensions."""
    enabled: bool = True
    hmac_secret: str | None = None  # Secret for HMAC signing
    require_autonomous_signature: bool = True  # Require signature for autonomous actions
    max_signature_age_seconds: int = 3600


@dataclass
class SignedProvenanceRecord:
    """Signed provenance record for spoof-proof verification."""
    record_id: str
    capability_id: str
    source: ProvenanceSource
    authority: ProvenanceAuthority
    autonomous: bool
    timestamp: datetime
    signature: str
    payload_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityProvenanceExtensionService(BaseService):
    """
    Extends CapabilityProvenance with M10 autonomous authority fields.

    M10-N6: CapabilityProvenance Extensions (GAP-M10-07)
    - Adds autonomous/authority_level fields to provenance records
    - Implements HMAC-signed records for spoof-proof re-assertion
    - Security test: Asserts tampered provenance fails verification
    """

    name = "capability_provenance_ext"
    version = "1.0.0"
    description = "Autonomous authority extensions for capability provenance"
    depends_on: list[str] = ["memory", "capability_manager"]

    def __init__(
        self,
        config: CapabilityProvenanceConfig | None = None,
        provenance_tracker: CapabilityProvenance | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or CapabilityProvenanceConfig()
        self._provenance_tracker = provenance_tracker
        self._signed_records: list[SignedProvenanceRecord] = []
        self._hmac_secret = config.hmac_secret if config and config.hmac_secret else "aios-m10-provenance-secret"

    @property
    def config(self) -> CapabilityProvenanceConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"CapabilityProvenanceExtensionService.on_start called, enabled={self._config.enabled}")

    async def on_stop(self) -> None:
        logger.info("CapabilityProvenanceExtensionService stopped")

    def _compute_payload_hash(self, payload: dict[str, Any]) -> str:
        """Compute SHA256 hash of payload for signing."""
        import json
        sorted_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(sorted_payload.encode()).hexdigest()

    def _sign_payload(self, payload_hash: str, timestamp: datetime) -> str:
        """Create HMAC signature for payload."""
        message = f"{payload_hash}:{timestamp.isoformat()}"
        return hmac.new(
            self._hmac_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, payload_hash: str, timestamp: datetime, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign_payload(payload_hash, timestamp)
        return hmac.compare_digest(expected, signature)

    def create_autonomous_provenance(
        self,
        capability_id: str,
        authority: ProvenanceAuthority | str = ProvenanceAuthority.AUTONOMOUS,
        source: ProvenanceSource | str = ProvenanceSource.GENERATED,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create provenance record with autonomous authority fields.

        Returns signed provenance record dict.
        """
        # Handle string inputs for authority and source
        if isinstance(authority, str):
            try:
                authority = ProvenanceAuthority(authority)
            except ValueError:
                authority = ProvenanceAuthority.AUTONOMOUS
        if isinstance(source, str):
            try:
                source = ProvenanceSource(source)
            except ValueError:
                source = ProvenanceSource.GENERATED

        record_id = f"prov_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow()

        base_payload = {
            "capability_id": capability_id,
            "source": source.value,
            "authority": authority.value,
            "autonomous": authority == ProvenanceAuthority.AUTONOMOUS,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata or {},
        }

        payload_hash = self._compute_payload_hash(base_payload)
        signature = self._sign_payload(payload_hash, timestamp)

        if self._config.require_autonomous_signature and authority == ProvenanceAuthority.AUTONOMOUS:
            if not signature:
                raise ValueError("Failed to generate signature for autonomous provenance")

        record = SignedProvenanceRecord(
            record_id=record_id,
            capability_id=capability_id,
            source=source,
            authority=authority,
            autonomous=authority == ProvenanceAuthority.AUTONOMOUS,
            timestamp=timestamp,
            signature=signature,
            payload_hash=payload_hash,
            metadata=metadata or {},
        )
        self._signed_records.append(record)

        # Also record in base provenance tracker if available
        if self._provenance_tracker:
            self._provenance_tracker.record_capability_usage(
                capability_id=capability_id,
                source=source,
                metadata={
                    **base_payload,
                    "record_id": record_id,
                    "signature": signature,
                    "payload_hash": payload_hash,
                },
            )

        logger.debug(f"Created autonomous provenance: {record_id} for {capability_id}")
        return {
            "record_id": record_id,
            "capability_id": capability_id,
            "source": source.value,
            "authority": authority.value,
            "autonomous": authority == ProvenanceAuthority.AUTONOMOUS,
            "timestamp": timestamp.isoformat(),
            "signature": signature,
            "payload_hash": payload_hash,
            "metadata": metadata or {},
        }

    def verify_provenance(self, record: dict[str, Any]) -> bool:
        """
        Verify a provenance record's signature (spoof-proof check).

        Returns True if signature is valid, False if tampered.
        """
        try:
            payload_hash = record.get("payload_hash")
            signature = record.get("signature")
            timestamp_str = record.get("timestamp")

            if not all([payload_hash, signature, timestamp_str]):
                logger.warning("Provenance record missing required fields for verification")
                return False

            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            # Recompute hash from record
            verification_payload = {
                "capability_id": record.get("capability_id"),
                "source": record.get("source"),
                "authority": record.get("authority"),
                "autonomous": record.get("autonomous", False),
                "timestamp": timestamp_str,
                "metadata": record.get("metadata", {}),
            }
            computed_hash = self._compute_payload_hash(verification_payload)

            if computed_hash != payload_hash:
                logger.warning(f"Provenance payload hash mismatch: {computed_hash} != {payload_hash}")
                return False

            return self._verify_signature(payload_hash, timestamp, signature)

        except Exception as e:
            logger.error(f"Provenance verification failed: {e}")
            return False

    def get_signed_records(
        self,
        capability_id: str | None = None,
        authority: ProvenanceAuthority | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get signed provenance records."""
        records = self._signed_records

        if capability_id:
            records = [r for r in records if r.capability_id == capability_id]
        if authority:
            records = [r for r in records if r.authority == authority]

        return [
            {
                "record_id": r.record_id,
                "capability_id": r.capability_id,
                "source": r.source.value,
                "authority": r.authority.value,
                "autonomous": r.autonomous,
                "timestamp": r.timestamp.isoformat(),
                "signature": r.signature,
                "payload_hash": r.payload_hash,
                "metadata": r.metadata,
            }
            for r in records[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        autonomous_count = sum(1 for r in self._signed_records if r.autonomous)
        stats.update({
            "enabled": self._config.enabled,
            "total_signed_records": len(self._signed_records),
            "autonomous_records": autonomous_count,
            "human_records": sum(1 for r in self._signed_records if r.authority == ProvenanceAuthority.HUMAN),
            "advisory_records": sum(1 for r in self._signed_records if r.authority == ProvenanceAuthority.ADVISORY),
            "require_autonomous_signature": self._config.require_autonomous_signature,
        })
        return stats


# Global instance
_global_capability_provenance_ext: CapabilityProvenanceExtensionService | None = None


def get_capability_provenance_ext(
    config: CapabilityProvenanceConfig | None = None,
    provenance_tracker=None,
) -> CapabilityProvenanceExtensionService:
    """Get or create the global CapabilityProvenanceExtensionService."""
    global _global_capability_provenance_ext
    if _global_capability_provenance_ext is None:
        _global_capability_provenance_ext = CapabilityProvenanceExtensionService(
            config=config, provenance_tracker=provenance_tracker
        )
    return _global_capability_provenance_ext


def set_capability_provenance_ext(service: CapabilityProvenanceExtensionService) -> None:
    """Set the global CapabilityProvenanceExtensionService."""
    global _global_capability_provenance_ext
    _global_capability_provenance_ext = service


__all__ = [
    "CapabilityProvenanceExtensionService",
    "CapabilityProvenanceConfig",
    "ProvenanceAuthority",
    "SignedProvenanceRecord",
    "get_capability_provenance_ext",
    "set_capability_provenance_ext",
]