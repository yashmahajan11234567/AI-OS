"""M9-N9 — Bounded convergence detection (spec §3.3.7, §11, §16).

A DETERMINISTIC, advisory-only detector that watches the closed loop
(TestOrchestratorService INV-013) for "no improvement across iterations" and
signals escalation to the existing human-escalation path.

Authority boundary (spec §16 — inviolable):
  * The detector NEVER decides pass/fail, NEVER approves/rejects, NEVER
    re-plans autonomously. It only OBSERVES iteration outcomes and SIGNALS.
  * The signal routes through the canonical HUMAN_ESCALATION_REQUIRED event;
    WorkflowManager._escalate_to_human remains the only escalation executor.

Bounded by construction:
  * Fixed-size sliding window of verdicts per objective.
  * Deterministic rule: N consecutive identical failing verdicts with no
    change in the failure signature = converged/no-improvement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default bound: this many consecutive no-improvement iterations => converged.
DEFAULT_NO_IMPROVEMENT_LIMIT = 2


@dataclass
class IterationObservation:
    """One observed closed-loop iteration outcome (advisory record)."""

    objective_id: str
    iteration: int
    verdict: str
    failure_signature: str  # deterministic digest of WHY it failed
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ConvergenceDetector:
    """Detects no-improvement convergence in the closed loop (bounded).

    Usage: call :meth:`observe` after each failed iteration. When the bounded
    rule fires, ``observe`` returns True and emits the canonical escalation
    signal event; the caller then stops iterating and routes to the existing
    human-escalation path. The detector itself performs NO orchestration.
    """

    def __init__(
        self,
        *,
        emit_event=None,
        no_improvement_limit: int = DEFAULT_NO_IMPROVEMENT_LIMIT,
    ) -> None:
        """
        Args:
            emit_event: Optional callable ``(EventType, payload, correlation_id)``
                used to emit HUMAN_ESCALATION_REQUIRED when converged. Injected
                by TestOrchestratorService as its own ``_emit_event`` so the
                signal flows over the canonical EventBus with zero new plumbing.
            no_improvement_limit: Consecutive identical-outcome failures before
                signaling. Bounded >= 1; lower means "escalate sooner".
        """
        self._emit_event = emit_event
        self._limit = max(1, int(no_improvement_limit))
        # objective_id -> list of recent observations (bounded window).
        self._history: dict[str, list[IterationObservation]] = {}
        # objective_id -> True once signaled (never re-signal spuriously).
        self._signaled: dict[str, bool] = {}

    @property
    def no_improvement_limit(self) -> int:
        return self._limit

    def _failure_signature(self, observation: IterationObservation) -> str:
        """Deterministic signature of the failure (verdict + reason digest).

        Prefers the caller-supplied ``failure_signature`` (content-derived);
        falls back to metadata reasons when absent.
        """
        if observation.failure_signature:
            return observation.failure_signature
        outcome = observation.metadata.get("outcome") or {}
        reasons = outcome.get("reasons") or observation.metadata.get("reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]
        digest = "|".join(sorted(str(r) for r in reasons))
        return f"{observation.verdict}::{digest}"

    def observe(self, observation: IterationObservation) -> bool:
        """Record one failed iteration; return True iff converged (no-improvement).

        Deterministic rule: the last ``no_improvement_limit`` observations for
        this objective share an IDENTICAL failure signature → the loop is not
        making progress. Once signaled, further observations never re-trigger.
        """
        window = self._history.setdefault(observation.objective_id, [])
        window.append(observation)
        # Hard bound on retained history (memory safety).
        del window[:-self._limit]

        if self._signaled.get(observation.objective_id):
            return False

        if len(window) < self._limit:
            return False

        signatures = {self._failure_signature(o) for o in window[-self._limit:]}
        if len(signatures) != 1:
            return False

        # Converged (no improvement). Signal once, advisory-only.
        self._signaled[observation.objective_id] = True
        if self._emit_event is not None:
            try:
                from aios.events.core.types import EventType

                self._emit_event(
                    EventType.HUMAN_ESCALATION_REQUIRED,
                    {
                        "objective_id": observation.objective_id,
                        "reason": "convergence_no_improvement",
                        # Same recovery contract as workflow._escalate_to_human
                        # (workflow.py:869) so downstream consumers treat both
                        # identically.
                        "recovery_action": "escalate_to_human",
                        "iterations_observed": [
                            o.iteration for o in window[-self._limit:]
                        ],
                        "failure_signature": next(iter(signatures)),
                        "advisory": True,
                        "authority": "advisory_only",
                    },
                    observation.correlation_id,
                )
            except Exception:  # noqa: BLE001 — signaling must never break the loop
                logger.warning(
                    "Convergence escalation signal emission failed "
                    "for %s (ignored)",
                    observation.objective_id,
                )
        return True

    def reset(self, objective_id: str | None = None) -> None:
        """Clear state for one objective or all (new run / success)."""
        if objective_id is None:
            self._history.clear()
            self._signaled.clear()
        else:
            self._history.pop(objective_id, None)
            self._signaled.pop(objective_id, None)


__all__ = [
    "ConvergenceDetector",
    "IterationObservation",
    "DEFAULT_NO_IMPROVEMENT_LIMIT",
]
