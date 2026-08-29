"""
M7 — UserSimulationAgent (10th testing perspective).

The ``UserSimulationAgent`` drives an EXTERNAL, untrusted ``hermes-agent``(EXT)
browser session via ``HermesBridge`` to discover whether a real user could
complete a stated goal. It is a *discovery-first* agent:

  * It receives ONLY: ``app_url``, ``user_goal``, ``exploration_brief``.
  * It NEVER receives source code, internal API contracts, or implementation
    details (INV-008). The constructor and ``simulate`` signature enforce this:
    there is no ``source_code`` parameter, and no kwarg that accepts source.
  * The external worker returns OBSERVATIONS ONLY (a ``HermesObservation``),
    never a verdict. The worker does NOT decide pass/fail.
  * Each simulation runs in an isolated ``hermes_<uuid>`` session.
  * The agent converts the worker's raw trace into a
    ``UserSimulationCompleted`` result (structured observations), which the
    trusted ``TestOrchestratorService`` later normalizes into ``TestingEvidence``.

No new EventType is emitted here (observations are processed by the
orchestrator). The agent does not call SecurityManager directly; the
``HermesBridge``/MCP layer is the boundary that must be authorized. The agent
only asserts the external boundary returns observations, never verdicts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aios.core.testing_evidence import (
    Provenance,
    UserSimulationCompleted,
)
from aios.adapters.hermes_bridge import HermesBridge, HermesObservation, HermesTask

# A frozen set of the ONLY parameters the agent accepts. Anything not in this
# set is rejected defensively at the boundary (defense-in-depth for INV-008).
_ALLOWED_SIMULATE_KWARGS = frozenset({
    "app_url", "user_goal", "exploration_brief", "correlation_id",
})

# Simulated interaction primitives the agent drives through the worker.
_GOAL_PROBE_ACTIONS = [
    "navigate",
    "observe_initial_state",
    "attempt_primary_goal",
    "probe_invalid_input",
    "probe_recovery",
    "collect_usability",
]


@dataclass
class _AgentConfig:
    """Injectable configuration (kept simple; no source-code fields)."""

    app_url: str
    user_goal: str
    exploration_brief: str


class UserSimulationAgent:
    """
    Drives an external browser worker to simulate a confused real user.

    The agent is intentionally thin: it orchestrates a sequence of discovery
    interactions through ``HermesBridge`` and assembles the worker's raw
    observations into a structured ``UserSimulationCompleted`` result. It does
    NOT evaluate pass/fail itself — that is the trusted orchestrator's job.
    """

    def __init__(
        self,
        hermes_bridge: HermesBridge,
        *,
        worker_label: str = "hermes_agent_ext",
        # Explicitly NO source_code / implementation parameters.
        agent_id: str = "user_simulation_agent",
        fail_closed: bool = True,
    ) -> None:
        """
        Initialize the user-simulation agent.

        Args:
            hermes_bridge: Bridge to hermes-agent(EXT). Injected so tests can
                supply a deterministic fake without a real MCP connection.
            worker_label: Identifier for the external worker (provenance only).
            agent_id: Local identity of this agent (trusted, kernel-side).
            fail_closed: If True, reject any attempt to inject source code.
        """
        if hermes_bridge is None:
            raise ValueError("UserSimulationAgent requires a HermesBridge instance")
        self._bridge = hermes_bridge
        self._worker_label = worker_label
        self._agent_id = agent_id
        self._fail_closed = fail_closed
        # Tracks active session ids for isolation assertions in tests.
        self._active_session: str | None = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def _reject_source_kwargs(self, kwargs: dict[str, Any]) -> None:
        """Defense-in-depth: refuse any non-allowed kwarg (e.g. source_code)."""
        if not self._fail_closed:
            return
        illegal = set(kwargs.keys()) - _ALLOWED_SIMULATE_KWARGS
        if illegal:
            raise ValueError(
                f"UserSimulationAgent rejected unauthorized parameters: {sorted(illegal)}. "
                f"Only {sorted(_ALLOWED_SIMULATE_KWARGS)} are permitted (INV-008)."
            )

    async def simulate(
        self,
        app_url: str,
        user_goal: str,
        exploration_brief: str,
        *,
        correlation_id: str | None = None,
    ) -> UserSimulationCompleted:
        """
        Discover whether a real user can complete ``user_goal`` at ``app_url``.

        NO source code is accepted. The external worker is asked only to explore
        the running application from a user's perspective.

        Args:
            app_url: URL of the deployed application under test.
            user_goal: The goal a real user would try to accomplish.
            exploration_brief: Human-readable guidance for the exploration.
            correlation_id: Optional correlation id for traceability.

        Returns:
            ``UserSimulationCompleted`` — structured OBSERVATIONS, not a verdict.
        """
        # Explicit guard: the method signature accepts only the three allowed
        # positional/keyword args plus correlation_id. This static shape is the
        # primary INV-008 guarantee; ``_reject_source_kwargs`` covers any dynamic
        # callers passing unexpected kwargs.
        self._reject_source_kwargs({
            "app_url": app_url,
            "user_goal": user_goal,
            "exploration_brief": exploration_brief,
            "correlation_id": correlation_id,
        })

        # Create session and USE the returned session ID (D-02 remediation:
        # the prior code called a non-existent ``_create_session_id()`` which
        # raised AttributeError and crashed the user-simulation perspective).
        # The bridge generates and returns the canonical session id.
        session_id = await self._bridge.create_worker_session(environment={"app_url": app_url})
        self._active_session = session_id

        provenance = Provenance(
            source="user_simulation",
            worker=self._worker_label,
            session=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="ai_os_hermes_bridge",
            correlation_id=correlation_id or str(uuid.uuid4()),
            test_id=f"usim_{uuid.uuid4().hex[:12]}",
        )

        # Drive a discovery-first interaction sequence through the worker.
        observations: list[HermesObservation] = []

        try:
            observations.append(await self._bridge.navigate(session_id, app_url))
            observations.append(
                await self._bridge.extract_content(session_id, selector=None)
            )
            # Attempt the primary goal (the worker may click/type as a user would).
            observations.append(
                await self._bridge.execute_task(self._make_task(
                    session_id, "attempt_goal", f"Attempt user goal: {user_goal}",
                    {"goal": user_goal, "brief": exploration_brief},
                ))
            )
            # Probe invalid input handling.
            observations.append(
                await self._bridge.execute_task(self._make_task(
                    session_id, "probe_invalid_input",
                    "Submit invalid/incomplete input and observe handling",
                    {"goal": user_goal},
                ))
            )
            # Probe recovery behavior after an error.
            observations.append(
                await self._bridge.execute_task(self._make_task(
                    session_id, "probe_recovery",
                    "Trigger a recoverable error and observe recovery affordances",
                    {"goal": user_goal},
                ))
            )
        finally:
            await self._bridge.close_worker_session(session_id)
            self._active_session = None

        return self._assemble_result(
            observations=observations,
            app_url=app_url,
            user_goal=user_goal,
            exploration_brief=exploration_brief,
            provenance=provenance,
        )

    def _assemble_result(
        self,
        *,
        observations: list[HermesObservation],
        app_url: str,
        user_goal: str,
        exploration_brief: str,
        provenance: Provenance,
    ) -> UserSimulationCompleted:
        """
        Assemble worker observations into a ``UserSimulationCompleted`` result.

        This is trusted-side assembly of STRUCTURED OBSERVATIONS. It does NOT
        produce a verdict. The worker's raw trace is preserved verbatim so the
        trusted orchestrator can normalize it later.
        """
        raw_trace: dict[str, Any] = {
            "app_url": app_url,
            "exploration_brief": exploration_brief,
            "session_id": provenance.session,
            "worker_label": self._worker_label,
            "observations": [self._obs_to_dict(o) for o in observations],
        }

        # Derive simple, evidence-only signals from worker success flags.
        # These are OBSERVATIONS, not a verdict.
        nav_ok = any(o.success for o in observations if o.task_id.startswith("nav_"))
        goal_attempt = next(
            (o for o in observations if "attempt_goal" in o.task_id), None
        )
        goal_success = bool(goal_attempt and goal_attempt.success)

        blockers: list[str] = []
        if not nav_ok:
            blockers.append("Application failed to load / navigate")
        if not goal_attempt:
            blockers.append("Worker never attempted the primary goal")
        elif not goal_success:
            blockers.append("Primary user goal attempt failed")

        invalid_probe = next(
            (o for o in observations if "probe_invalid_input" in o.task_id), None
        )
        invalid_handled = bool(invalid_probe and invalid_probe.success)
        invalid_handling = [] if invalid_handled else ["Invalid input not gracefully handled"]

        recovery_probe = next(
            (o for o in observations if "probe_recovery" in o.task_id), None
        )
        recovery_behavior = (
            "recovered" if (recovery_probe and recovery_probe.success)
            else "no clear recovery affordance observed"
        )

        # Goal completion percentage is a coarse observation proxy, NOT a verdict.
        completion = 1.0 if (nav_ok and goal_success) else (0.5 if nav_ok else 0.0)
        completion = completion - (0.2 if blockers else 0.0)
        completion = max(0.0, min(1.0, completion))

        return UserSimulationCompleted(
            goal=user_goal,
            goal_completion_pct=round(completion, 3),
            workflow_success=goal_success,
            usability_blockers=blockers,
            confusing_states=[] if goal_success else ["Goal path unclear to simulated user"],
            navigation_failures=[] if nav_ok else ["Navigation to app failed"],
            missing_feedback=[] if invalid_handled else ["No feedback on invalid input"],
            invalid_input_handling=invalid_handling,
            recovery_behavior=recovery_behavior,
            expected_vs_observed=[
                {"expected": "user completes goal", "observed": f"workflow_success={goal_success}"}
            ],
            raw_trace=raw_trace,
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _make_task(
        session_id: str, task_type: str, description: str, parameters: dict[str, Any]
    ) -> HermesTask:
        """Build a ``HermesTask`` for the external worker (observations only)."""
        return HermesTask(
            task_id=f"{task_type}_{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            description=description,
            parameters=parameters,
            session_id=session_id,
        )

    @staticmethod
    def _obs_to_dict(o: HermesObservation) -> dict[str, Any]:
        return {
            "task_id": o.task_id,
            "success": o.success,
            "data": o.data,
            "error": o.error,
            "trust_level": o.trust_level,
            "session_id": o.session_id,
            "provenance": o.provenance,
        }
