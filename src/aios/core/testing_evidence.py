"""
M7 — Testing Evidence Schema for AI-OS Hermes Kernel.

Defines the structured, machine-checkable evidence types used by the
multi-perspective testing system:

  * ``TestingEvidence``      — the canonical evidence record produced by every
                              testing perspective (9 agencies + user simulation).
  * ``UserSimulationCompleted`` — the structured result returned by the
                              ``UserSimulationAgent`` (10th perspective). It is
                              NOT a verdict; it normalizes into ``TestingEvidence``.
  * ``PerspectiveVerdict``   — pass/fail/inconclusive enum.
  * ``Severity`` / ``Provenance`` helpers — validation + immutability support.

Design rules (per the frozen M7 contract):
  * Every ``TestingEvidence`` MUST carry complete provenance.
  * Evidence is immutable once constructed/normalized.
  * Reproducibility + confidence are bounded floats in [0.0, 1.0].
  * Serialization/deserialization are supported for audit storage.

Uses the canonical ``datetime`` (UTC). No new EventType is introduced here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Imported lazily at module scope to keep the schema importable without a
# running kernel (the schemas are pure data; no EventBus access here).

__all__ = [
    "Severity",
    "PerspectiveVerdict",
    "Provenance",
    "TestingEvidence",
    "UserSimulationCompleted",
    "normalize_user_simulation",
    "VALID_SEVERITIES",
    "VALID_VERDICTS",
]


VALID_SEVERITIES = ("critical", "high", "medium", "low")
VALID_VERDICTS = ("pass", "fail", "inconclusive")


class Severity(str, Enum):
    """Evidence severity levels (invariant ordering for aggregation)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def rank(cls, value: str) -> int:
        """Return a numeric rank (higher = more severe)."""
        order = {cls.CRITICAL.value: 3, cls.HIGH.value: 2, cls.MEDIUM.value: 1, cls.LOW.value: 0}
        return order.get(str(value), -1)


class PerspectiveVerdict(str, Enum):
    """Outcome of a single perspective's testing."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Provenance:
    """
    Immutable provenance chain for a piece of evidence.

    Every evidence item MUST have a complete provenance: who/what produced it
    (``source``, ``worker``), in which isolated session (``session``), when
    (``timestamp``), under which environment (``environment``), and how it ties
    back to the wider test run via ``correlation_id`` / ``test_id``.
    """

    source: str
    worker: str
    session: str
    timestamp: str
    environment: str
    correlation_id: str = ""
    test_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "worker": self.worker,
            "session": self.session,
            "timestamp": self.timestamp,
            "environment": self.environment,
            "correlation_id": self.correlation_id,
            "test_id": self.test_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Provenance":
        return cls(
            source=str(data.get("source", "")),
            worker=str(data.get("worker", "")),
            session=str(data.get("session", "")),
            timestamp=str(data.get("timestamp", "")),
            environment=str(data.get("environment", "")),
            correlation_id=str(data.get("correlation_id", "")),
            test_id=str(data.get("test_id", "")),
        )

    def validate(self) -> None:
        """Raise ``ValueError`` if provenance is incomplete."""
        required = ("source", "worker", "session", "timestamp", "environment")
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(f"Provenance missing required fields: {missing}")


@dataclass(frozen=True)
class TestingEvidence:
    """
    Immutable, machine-checkable evidence record produced by one testing
    perspective (a real agency adapter or the user-simulation agent).

    Once constructed, this object cannot be mutated. Producers that need to
    "modify" evidence must build a new instance. This guarantees the audit
    trail is tamper-evident (INV-007-style evidence integrity).
    """

    perspective: str  # agency name or "user_simulation"
    target: str  # what was tested
    test_id: str  # unique identifier
    actions: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    expected: str = ""
    observed: str = ""
    severity: str = "low"
    confidence: float = 0.0
    proof: list[str] = field(default_factory=list)
    provenance: Provenance = field(default_factory=Provenance)
    environment: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reproducibility: float = 0.0
    verdict: str = "inconclusive"

    # ---- validation -------------------------------------------------------
    def validate(self) -> None:
        """Validate all field constraints; raise ``ValueError`` on violation."""
        if not self.perspective:
            raise ValueError("TestingEvidence.perspective must be non-empty")
        if not self.target:
            raise ValueError("TestingEvidence.target must be non-empty")
        if not self.test_id:
            raise ValueError("TestingEvidence.test_id must be non-empty")

        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {VALID_SEVERITIES}, got {self.severity!r}"
            )
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {VALID_VERDICTS}, got {self.verdict!r}"
            )

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if not (0.0 <= self.reproducibility <= 1.0):
            raise ValueError(
                f"reproducibility must be in [0.0, 1.0], got {self.reproducibility}"
            )

        if not isinstance(self.provenance, Provenance):
            raise ValueError("provenance must be a Provenance instance")
        self.provenance.validate()

        if not isinstance(self.actions, list) or not isinstance(self.observations, list):
            raise ValueError("actions and observations must be lists")
        if not isinstance(self.proof, list):
            raise ValueError("proof must be a list")

    # ---- serialization ----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict (deep-copied).

        S4 (Terminal 2): evidence is the canonical artifact persisted to logs/
        provenance stores, so secrets are redacted centrally here via
        ``aios.security.secrets.redact_secrets``. The in-memory object is left
        untouched; only the serialized form is scrubbed. Imports lazily to keep
        this module importable without a running kernel.
        """
        from aios.security.secrets import redact_secrets

        return redact_secrets(
            {
                "perspective": self.perspective,
                "target": self.target,
                "test_id": self.test_id,
                "actions": copy.deepcopy(self.actions),
                "observations": copy.deepcopy(self.observations),
                "expected": self.expected,
                "observed": self.observed,
                "severity": self.severity,
                "confidence": self.confidence,
                "proof": list(self.proof),
                "provenance": self.provenance.to_dict(),
                "environment": copy.deepcopy(self.environment),
                "timestamp": self.timestamp.isoformat(),
                "reproducibility": self.reproducibility,
                "verdict": self.verdict,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestingEvidence":
        """Deserialize from a dict produced by ``to_dict``."""
        raw_ts = data.get("timestamp")
        if isinstance(raw_ts, datetime):
            ts = raw_ts
        elif isinstance(raw_ts, str) and raw_ts:
            ts = datetime.fromisoformat(raw_ts)
        else:
            ts = datetime.now(timezone.utc)

        prov = data.get("provenance")
        provenance = prov if isinstance(prov, Provenance) else Provenance.from_dict(prov or {})

        return cls(
            perspective=str(data.get("perspective", "")),
            target=str(data.get("target", "")),
            test_id=str(data.get("test_id", "")),
            actions=list(data.get("actions", []) or []),
            observations=list(data.get("observations", []) or []),
            expected=str(data.get("expected", "")),
            observed=str(data.get("observed", "")),
            severity=str(data.get("severity", "low")),
            confidence=float(data.get("confidence", 0.0)),
            proof=list(data.get("proof", []) or []),
            provenance=provenance,
            environment=dict(data.get("environment", {}) or {}),
            timestamp=ts,
            reproducibility=float(data.get("reproducibility", 0.0)),
            verdict=str(data.get("verdict", "inconclusive")),
        )

    def is_failure(self) -> bool:
        """Convenience predicate: this evidence represents a failing test."""
        return self.verdict == "fail"


@dataclass(frozen=True)
class UserSimulationCompleted:
    """
    Structured result from the ``UserSimulationAgent`` (10th perspective).

    This is NOT a verdict. It captures what an external (untrusted) Hermes
    worker observed while attempting to complete a user goal in a browser.
    ``TestOrchestratorService.normalize_evidence`` converts this into a
    ``TestingEvidence`` record for the trusted testing council.
    """

    goal: str
    goal_completion_pct: float = 0.0
    workflow_success: bool = False
    usability_blockers: list[str] = field(default_factory=list)
    confusing_states: list[str] = field(default_factory=list)
    navigation_failures: list[str] = field(default_factory=list)
    missing_feedback: list[str] = field(default_factory=list)
    invalid_input_handling: list[str] = field(default_factory=list)
    recovery_behavior: str = ""
    expected_vs_observed: list[dict[str, Any]] = field(default_factory=list)
    raw_trace: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self) -> None:
        if not self.goal:
            raise ValueError("UserSimulationCompleted.goal must be non-empty")
        if not (0.0 <= self.goal_completion_pct <= 1.0):
            raise ValueError(
                f"goal_completion_pct must be in [0.0, 1.0], got {self.goal_completion_pct}"
            )
        if not isinstance(self.raw_trace, dict):
            raise ValueError("raw_trace must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "goal_completion_pct": self.goal_completion_pct,
            "workflow_success": self.workflow_success,
            "usability_blockers": list(self.usability_blockers),
            "confusing_states": list(self.confusing_states),
            "navigation_failures": list(self.navigation_failures),
            "missing_feedback": list(self.missing_feedback),
            "invalid_input_handling": list(self.invalid_input_handling),
            "recovery_behavior": self.recovery_behavior,
            "expected_vs_observed": copy.deepcopy(self.expected_vs_observed),
            "raw_trace": copy.deepcopy(self.raw_trace),
            "timestamp": self.timestamp.isoformat(),
        }


def normalize_user_simulation(
    sim: UserSimulationCompleted,
    *,
    target: str,
    test_id: str,
    provenance: Provenance,
    reproducibility: float = 1.0,
    confidence: float | None = None,
) -> TestingEvidence:
    """
    Convert a (trusted-side normalized) ``UserSimulationCompleted`` into a
    ``TestingEvidence`` record for the testing council.

    The conversion is performed by AI-OS (trusted), NOT by the external worker.
    The external worker only ever supplies observations; the verdict/severity
    mapping below is computed by AI-OS from the structured fields.

    Rules:
      * Any usability/navigation/feedback failures => verdict ``fail``.
      * Otherwise: verdict ``pass`` if ``workflow_success`` else ``inconclusive``.
      * Severity reflects blocker count (critical if hard blockers, etc.).
    """
    sim.validate()
    if not isinstance(provenance, Provenance):
        raise ValueError("provenance must be a Provenance instance")
    provenance.validate()

    blockers = (
        list(sim.usability_blockers)
        + list(sim.navigation_failures)
        + list(sim.missing_feedback)
    )
    has_blockers = bool(blockers)
    has_confusion = bool(sim.confusing_states)

    if has_blockers:
        verdict = PerspectiveVerdict.FAIL.value
    elif sim.workflow_success:
        verdict = PerspectiveVerdict.PASS.value
    else:
        verdict = PerspectiveVerdict.INCONCLUSIVE.value

    # Severity escalates with blocker volume + low goal completion.
    if has_blockers and (len(blockers) >= 2 or sim.goal_completion_pct < 0.25):
        severity = Severity.CRITICAL.value
    elif has_blockers or sim.goal_completion_pct < 0.5:
        severity = Severity.HIGH.value
    elif has_confusion:
        severity = Severity.MEDIUM.value
    else:
        severity = Severity.LOW.value

    observations = [
        {"type": "goal_completion_pct", "value": sim.goal_completion_pct},
        {"type": "workflow_success", "value": sim.workflow_success},
        {"type": "usability_blockers", "value": list(sim.usability_blockers)},
        {"type": "navigation_failures", "value": list(sim.navigation_failures)},
        {"type": "missing_feedback", "value": list(sim.missing_feedback)},
        {"type": "confusing_states", "value": list(sim.confusing_states)},
        {"type": "invalid_input_handling", "value": list(sim.invalid_input_handling)},
        {"type": "recovery_behavior", "value": sim.recovery_behavior},
    ]

    if confidence is None:
        # Higher completion + no blockers => higher confidence in the result.
        confidence = round(min(1.0, max(0.0, sim.goal_completion_pct)), 3)

    expected = f"User can complete goal: {sim.goal}"
    observed = (
        f"goal_completion_pct={sim.goal_completion_pct:.2f}, "
        f"workflow_success={sim.workflow_success}, "
        f"blockers={len(blockers)}"
    )

    return TestingEvidence(
        perspective="user_simulation",
        target=target,
        test_id=test_id,
        actions=[{"type": "user_goal_attempt", "goal": sim.goal}],
        observations=observations,
        expected=expected,
        observed=observed,
        severity=severity,
        confidence=confidence,
        proof=[f"hermes_session:{provenance.session}"],
        provenance=provenance,
        environment={"worker": "hermes_agent_ext"},
        timestamp=sim.timestamp,
        reproducibility=reproducibility,
        verdict=verdict,
    )
