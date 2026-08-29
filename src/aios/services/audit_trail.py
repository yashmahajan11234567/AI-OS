"""
Autonomous Audit Trail for AI-OS M10.

Provides tamper-evident logging of all M10 autonomous decisions with
chained hashes for integrity verification.

This is M10-N11 implementation per M10-IMPLEMENTATION-SPEC.md §11.11.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.base import Event
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of autonomous audit events."""
    OBJECTIVE_GENERATED = "objective_generated"
    REPLAN_TRIGGERED = "replan_triggered"
    JUDGMENT_EMITTED = "judgment_emitted"
    AUTONOMY_DISABLED = "autonomy_disabled"
    AUTONOMY_ENABLED = "autonomy_enabled"
    FALLBACK_ACTIVATED = "fallback_activated"
    FALLBACK_RECOVERED = "fallback_recovered"
    QUOTA_EXHAUSTED = "quota_exhausted"
    LEARNING_APPLIED = "learning_applied"
    STATE_VERIFIED = "state_verified"


@dataclass
class AuditConfig:
    """Configuration for audit trail."""
    enabled: bool = True
    chain_hashes: bool = True  # Enable hash chaining for tamper evidence
    max_entries: int = 10000
    hash_algorithm: str = "sha256"


@dataclass
class AuditEntry:
    """Single tamper-evident audit entry."""
    entry_id: str
    event_type: AuditEventType
    timestamp: datetime
    service_name: str
    action: str
    details: dict[str, Any]
    previous_hash: str
    current_hash: str
    sequence_number: int
    autonomous: bool = True
    authority_level: str = "autonomous"


class AuditTrailService(BaseService):
    """
    Tamper-evident audit trail for all M10 autonomous decisions.

    M10-N11: Autonomous Audit Trail (GAP-M10-11)
    - Logs all autonomous actions with chained hashes
    - Uses SHA-256 hash chain for tamper evidence
    - Security test: Asserts tampered audit log fails verification
    """

    name = "audit_trail"
    version = "1.0.0"
    description = "Tamper-evident audit trail for autonomous operations"
    depends_on: list[str] = ["memory", "security"]

    def __init__(
        self,
        config: AuditConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AuditConfig()
        self._event_bus = get_core_event_bus()
        self._audit_log: list[AuditEntry] = []
        self._last_hash: str = "0" * 64  # Genesis hash
        self._sequence_number: int = 0
        self._Genesis = "GENESIS"

    @property
    def config(self) -> AuditConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"AuditTrailService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled and self._config.chain_hashes:
            # Log genesis entry
            self._log_genesis()

    async def on_stop(self) -> None:
        logger.info("AuditTrailService stopped")

    def _log_genesis(self) -> None:
        """Log the genesis audit entry."""
        genesis_entry = AuditEntry(
            entry_id="genesis",
            event_type=AuditEventType.STATE_VERIFIED,
            timestamp=datetime.utcnow(),
            service_name="audit_trail",
            action="genesis",
            details={"message": "Audit trail initialized"},
            previous_hash="0" * 64,
            current_hash=self._compute_hash("genesis", "0" * 64, {}),
            sequence_number=0,
        )
        self._audit_log.append(genesis_entry)
        self._last_hash = genesis_entry.current_hash
        logger.info("Audit trail genesis entry created")

    def _compute_hash(
        self,
        entry_id: str,
        previous_hash: str,
        data: dict[str, Any],
    ) -> str:
        """Compute tamper-evident hash for an entry."""
        # Create deterministic string representation
        content = {
            "entry_id": entry_id,
            "previous_hash": previous_hash,
            "data": data,
        }
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode()).hexdigest()

    async def log_audit_event(
        self,
        event_type: AuditEventType,
        service_name: str,
        action: str,
        details: dict[str, Any],
    ) -> AuditEntry:
        """Log an autonomous audit event with hash chaining."""
        if not self._config.enabled:
            return AuditEntry(
                entry_id="disabled",
                event_type=event_type,
                timestamp=datetime.utcnow(),
                service_name=service_name,
                action=action,
                details=details,
                previous_hash="",
                current_hash="",
                sequence_number=-1,
            )

        self._sequence_number += 1
        entry_id = f"audit_{uuid.uuid4().hex[:12]}"

        # Prepare data for hashing
        hash_data = {
            "event_type": event_type.value,
            "service_name": service_name,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "sequence": self._sequence_number,
        }

        current_hash = self._compute_hash(entry_id, self._last_hash, hash_data)

        entry = AuditEntry(
            entry_id=entry_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            service_name=service_name,
            action=action,
            details=details,
            previous_hash=self._last_hash,
            current_hash=current_hash,
            sequence_number=self._sequence_number,
        )

        self._audit_log.append(entry)
        self._last_hash = current_hash

        # Trim if exceeding max entries
        if len(self._audit_log) > self._config.max_entries:
            self._audit_log = self._audit_log[-self._config.max_entries:]

        # Emit event
        await self._emit_audit_event(entry)

        logger.debug(f"Audit logged: {entry_id} ({event_type.value})")
        return entry

    async def _emit_audit_event(self, entry: AuditEntry) -> None:
        """Emit audit trail event."""
        if self._event_bus is None:
            return

        import uuid as uuid_module
        correlation_id = uuid_module.uuid4()

        core_event = CoreEvent(
            eventType=EventType.AI_AGENT_AUDIT_EMITTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "entry_id": entry.entry_id,
                "event_type": entry.event_type.value,
                "service_name": entry.service_name,
                "action": entry.action,
                "details": entry.details,
                "previous_hash": entry.previous_hash,
                "current_hash": entry.current_hash,
                "sequence_number": entry.sequence_number,
                "autonomous": entry.autonomous,
                "authority_level": entry.authority_level,
            }),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(EventType.AI_AGENT_AUDIT_EMITTED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit audit event: {e}")

    def verify_integrity(self, start_index: int = 0) -> tuple[bool, list[dict[str, Any]]]:
        """
        Verify the integrity of the audit log by checking hash chain.

        Returns (is_valid, list of mismatches).
        """
        mismatches = []

        for i in range(start_index + 1, len(self._audit_log)):
            entry = self._audit_log[i]
            prev_entry = self._audit_log[i - 1]

            # Recompute hash
            hash_data = {
                "event_type": entry.event_type.value,
                "service_name": entry.service_name,
                "action": entry.action,
                "details": entry.details,
                "timestamp": entry.timestamp.isoformat(),
                "sequence": entry.sequence_number,
            }
            expected_current = self._compute_hash(entry.entry_id, prev_entry.current_hash, hash_data)

            # Check previous hash matches
            if entry.previous_hash != prev_entry.current_hash:
                mismatches.append({
                    "index": i,
                    "entry_id": entry.entry_id,
                    "issue": "previous_hash_mismatch",
                    "expected": prev_entry.current_hash,
                    "actual": entry.previous_hash,
                })

            # Check current hash is correct
            if entry.current_hash != expected_current:
                mismatches.append({
                    "index": i,
                    "entry_id": entry.entry_id,
                    "issue": "current_hash_mismatch",
                    "expected": expected_current,
                    "actual": entry.current_hash,
                })

        is_valid = len(mismatches) == 0
        return is_valid, mismatches

    def get_audit_log(self, limit: int = 100, event_type: AuditEventType | None = None) -> list[dict[str, Any]]:
        """Get audit log entries."""
        entries = self._audit_log

        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        return [
            {
                "entry_id": e.entry_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "service_name": e.service_name,
                "action": e.action,
                "details": e.details,
                "previous_hash": e.previous_hash,
                "current_hash": e.current_hash,
                "sequence_number": e.sequence_number,
            }
            for e in entries[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        is_valid, mismatches = self.verify_integrity()
        stats.update({
            "enabled": self._config.enabled,
            "total_entries": len(self._audit_log),
            "chain_integrity": is_valid,
            "mismatch_count": len(mismatches),
            "last_hash": self._last_hash,
            "sequence_number": self._sequence_number,
        })
        return stats


# Global instance
_global_audit_trail: AuditTrailService | None = None


def get_audit_trail(
    config: AuditConfig | None = None,
) -> AuditTrailService:
    """Get or create the global AuditTrailService."""
    global _global_audit_trail
    if _global_audit_trail is None:
        _global_audit_trail = AuditTrailService(config=config)
    return _global_audit_trail


def set_audit_trail(service: AuditTrailService) -> None:
    """Set the global AuditTrailService."""
    global _global_audit_trail
    _global_audit_trail = service


__all__ = [
    "AuditTrailService",
    "AuditConfig",
    "AuditEventType",
    "AuditEntry",
    "get_audit_trail",
    "set_audit_trail",
]