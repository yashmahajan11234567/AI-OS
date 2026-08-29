"""
M13 Dashboard Backend Service (M13_DASHBOARD_ARCHITECTURE.md).

Non-authoritative, read-only backend surface over AI-OS for the Terminal 3
User Interface (Dashboard). The dashboard is a BOUNDED UI resource: AI-OS
(Terminal 1) retains sole governance, verification, and decision-making
authority. This service ONLY:

  * Reads AI-OS state through canonical kernel getters (self-loop, integration
    status, failure-recovery records, kernel stats, health) — never mutates.
  * Forwards user-initiated actions to AI-OS for authorization + execution.
    Every forwarded action passes through ``SecurityManager.authorize``
    (fail-closed DENY) and is recorded on the canonical EventBus as a
    ``DASHBOARD_ACTION_*`` event. The service itself decides nothing.

Per the M13 terminal contract, Terminal 2 authors this integration code so
Terminal 3 can host/operate the dashboard; Terminal 3 holds no authority.

Pages exposed (read-only data bundles):
  1. Planning Chat        -> self-loop status + last self-prompt + phase map
  2. Resource Onboarding  -> integration status + terminal-contract violations
  3. Project / Execution  -> active cycles + bounded-execution + recovery summary
  4. Knowledge / History  -> durability/persistence adapter stats
  5. System / Health      -> kernel stats + service status + authority summary
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from aios.core.security_manager import SecurityDecision
from aios.events.core.bus import EventBus, EventType
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import SemanticVersion
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class DashboardActionResult:
    """Outcome of a dashboard-forwarded action (AI-OS decides; service reports)."""

    action: str
    authorized: bool
    decision: str
    status: str  # "completed" | "rejected" | "error"
    detail: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "authorized": self.authorized,
            "decision": self.decision,
            "status": self.status,
            "detail": self.detail,
            "data": self.data,
        }


class DashboardService(BaseService):
    """Read-only, non-authoritative dashboard backend over AI-OS.

    The service holds a reference to the kernel and the security manager. It
    exposes page-data getters (pure reads) and a single ``request_action``
    entry point that forwards user intent to AI-OS for authorization + bounded
    execution. It never authorizes, verifies, or decides anything itself.
    """

    name = "dashboard_backend"
    version = "1.0.0"
    description = "Non-authoritative read-only dashboard backend over AI-OS"

    def __init__(
        self,
        kernel: Any = None,
        event_bus: Optional[EventBus] = None,
        security_manager: Any = None,
        config: Optional[dict[str, Any]] = None,
        info: Any = None,
    ) -> None:
        super().__init__(event_bus=event_bus, info=info)
        self._kernel = kernel
        self._security_manager = security_manager
        self._config = config or {}
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="dashboard_backend",
            version=SemanticVersion(1, 0, 0),
        )

    # ------------------------------------------------------------------ helpers

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical dashboard event (C1). Failures are non-fatal."""
        if self._event_bus is None:
            return
        try:
            event = Event(
                eventType=event_type,
                source=self._identity,
                correlationId=uuid.uuid4(),
                payload=payload,
            )
            result = self._event_bus.publish(event)
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # noqa: BLE001 — dashboard must never break AI-OS
            logger.debug("Dashboard event emission skipped: %s", exc)

    # ============================================================
    # PAGE 1 — Planning Chat (self-loop state)
    # ============================================================

    def get_planning_chat(self) -> dict[str, Any]:
        """Read-only view of the authoritative self-loop state."""
        engine = getattr(self._kernel, "self_loop_engine", None) if self._kernel else None
        generator = getattr(self._kernel, "self_prompt_generator", None) if self._kernel else None

        status: dict[str, Any] = {}
        last_prompt: dict[str, Any] = {}
        phase_map: list[dict[str, Any]] = []

        if engine is not None:
            try:
                status = engine.get_status()
            except Exception:  # noqa: BLE001 — defensive read
                status = {}
            cycle = getattr(engine, "_current_cycle", None)
            if cycle is not None:
                phase_results = getattr(cycle, "phase_results", {}) or {}
                phase_order = getattr(engine, "PHASE_ORDER", []) or []
                phase_map = [
                    {
                        "phase": p.value if hasattr(p, "value") else str(p),
                        "completed": p in phase_results,
                        "success": (phase_results.get(p).success if phase_results.get(p) else None),
                    }
                    for p in phase_order
                ]
            # Last self-prompt (read-only)
            try:
                last = getattr(engine, "_last_self_prompt", None)
                if last is not None:
                    last_prompt = _serialize_self_prompt(last)
            except Exception:  # noqa: BLE001
                last_prompt = {}

        gen_config: dict[str, Any] = {}
        if generator is not None:
            try:
                gen_config = generator.get_config()
            except Exception:  # noqa: BLE001
                gen_config = {}

        return {
            "page": "planning_chat",
            "authority": "aios_sole",
            "self_loop": status,
            "generator_config": gen_config,
            "phase_map": phase_map,
            "last_self_prompt": last_prompt,
            "read_only": True,
        }

    # ============================================================
    # PAGE 2 — Resource Onboarding (integration status)
    # ============================================================

    def get_resource_onboarding(self) -> dict[str, Any]:
        """Read-only view of integration onboarding + terminal-contract status."""
        integrations: list[dict[str, Any]] = []
        status_service = (
            getattr(self._kernel, "integration_status_service", None) if self._kernel else None
        )
        if status_service is not None:
            try:
                integrations = status_service.get_all_status_dict(redact_secrets=True)
            except Exception:  # noqa: BLE001
                integrations = []

        violations = []
        if self._kernel is not None:
            try:
                violations = [
                    {
                        "component": getattr(v, "component", None),
                        "detail": getattr(v, "detail", None),
                        "severity": getattr(v, "severity", None),
                    }
                    for v in (self._kernel.terminal_contract_violations or [])
                ]
            except Exception:  # noqa: BLE001
                violations = []

        return {
            "page": "resource_onboarding",
            "authority": "aios_sole",
            "integrations": integrations,
            "terminal_contract_violations": violations,
            "all_bounded_resources": len(violations) == 0,
            "read_only": True,
        }

    # ============================================================
    # PAGE 3 — Project / Execution
    # ============================================================

    def get_project_execution(self) -> dict[str, Any]:
        """Read-only view of execution cycles + bounded execution + recovery."""
        engine = getattr(self._kernel, "self_loop_engine", None) if self._kernel else None
        recovery_manager = (
            getattr(self._kernel, "failure_recovery_manager", None) if self._kernel else None
        )

        cycle: dict[str, Any] = {}
        bounded_execution: dict[str, Any] = {}
        if engine is not None:
            try:
                cycle = engine.get_status()
            except Exception:  # noqa: BLE001
                cycle = {}
            cur = getattr(engine, "_current_cycle", None)
            if cur is not None:
                pr = (getattr(cur, "phase_results", {}) or {}).get("bounded_execution")
                if pr is not None:
                    bounded_execution = {
                        "success": getattr(pr, "success", None),
                        "error": getattr(pr, "error", None),
                        "duration_ms": getattr(pr, "duration_ms", None),
                    }

        recovery: dict[str, Any] = {"records": []}
        if recovery_manager is not None:
            try:
                records = recovery_manager.list_records() or []
                recovery = {
                    "count": len(records),
                    "outcomes": _tally([r.outcome for r in records]),
                    "records": [
                        {
                            "recovery_id": r.recovery_id,
                            "failure_id": r.failure_id,
                            "category": r.category,
                            "component": r.component,
                            "outcome": r.outcome,
                            "attempts": r.attempts,
                            "provenance_authority": (r.provenance or {}).get("authority"),
                        }
                        for r in records
                    ],
                }
            except Exception:  # noqa: BLE001
                recovery = {"records": []}

        return {
            "page": "project_execution",
            "authority": "aios_sole",
            "cycle": cycle,
            "bounded_execution": bounded_execution,
            "failure_recovery": recovery,
            "read_only": True,
        }

    # ============================================================
    # PAGE 4 — Knowledge / History (durability/persistence)
    # ============================================================

    def get_knowledge_history(self) -> dict[str, Any]:
        """Read-only view of durability/persistence adapter stats."""
        adapters: dict[str, Any] = {}

        def _snap(name: str, adapter: Any) -> None:
            if adapter is None:
                return
            try:
                adapters[name] = {
                    "mode": "real" if getattr(adapter, "is_real_mode", lambda: False)() else "mock",
                    "connected": getattr(adapter, "is_connected", lambda: False)(),
                    "authority_level": getattr(adapter, "authority_level", None),
                    "terminal": getattr(adapter, "terminal", None),
                }
            except Exception:  # noqa: BLE001
                adapters[name] = {"mode": "unknown"}

        if self._kernel is not None:
            _snap("supabase", getattr(self._kernel, "supabase_adapter", None))
            _snap("obsidian_git", getattr(self._kernel, "obsidian_git_adapter", None))
            _snap("n8n", getattr(self._kernel, "n8n_adapter", None))

        # Obsidian Git commit history (mock-safe read)
        history: list[str] = []
        og = getattr(self._kernel, "obsidian_git_adapter", None) if self._kernel else None
        if og is not None:
            try:
                store = getattr(og, "_store", None)
                if store is not None and hasattr(store, "history"):
                    history = list(store.history())[:20]
            except Exception:  # noqa: BLE001
                history = []

        return {
            "page": "knowledge_history",
            "authority": "aios_sole",
            "adapters": adapters,
            "obsidian_git_history": history,
            "read_only": True,
        }

    # ============================================================
    # PAGE 5 — System / Health
    # ============================================================

    def get_system_health(self) -> dict[str, Any]:
        """Read-only kernel stats + service status + authority summary."""
        stats: dict[str, Any] = {}
        if self._kernel is not None:
            try:
                stats = self._kernel.get_stats()
            except Exception:  # noqa: BLE001
                stats = {}

        violations = []
        if self._kernel is not None:
            try:
                violations = [getattr(v, "detail", None) for v in (self._kernel.terminal_contract_violations or [])]
            except Exception:  # noqa: BLE001
                violations = []

        return {
            "page": "system_health",
            "authority": "aios_sole",
            "kernel_stats": stats,
            "terminal_contract_violations": violations,
            "authority_preserved": len(violations) == 0,
            "read_only": True,
        }

    # ============================================================
    # Aggregated snapshot for frontend
    # ============================================================

    def get_all_pages(self) -> dict[str, Any]:
        """All five read-only page bundles in one call."""
        return {
            "generated_at": self._now(),
            "authority_model": "aios_sole_authority",
            "pages": {
                "planning_chat": self.get_planning_chat(),
                "resource_onboarding": self.get_resource_onboarding(),
                "project_execution": self.get_project_execution(),
                "knowledge_history": self.get_knowledge_history(),
                "system_health": self.get_system_health(),
            },
        }

    # ============================================================
    # Action forwarding — AI-OS decides, service reports.
    # ============================================================

    async def request_action(
        self,
        action: str,
        params: Optional[dict[str, Any]] = None,
        principal: str = "dashboard_user",
    ) -> DashboardActionResult:
        """Forward a user-initiated action to AI-OS for authorization + execution.

        The dashboard NEVER authorizes or decides. It:
          1. Emits DASHBOARD_ACTION_REQUESTED (audit).
          2. Asks SecurityManager.authorize (fail-closed DENY).
          3. If ALLOW, performs the bounded kernel operation and emits
             DASHBOARD_ACTION_AUTHORIZED then DASHBOARD_ACTION_COMPLETED.
          4. If DENY, emits DASHBOARD_ACTION_REJECTED and reports.

        Supported actions (all bounded, all gated):
          - "integration.validate"   {name}
          - "integration.connect"    {name}
          - "integration.health_check" {name}
          - "self_loop.control"      {op: pause|resume|stop}
          - "self_loop.start_cycle"  {}  (user-initiated trigger; engine validates)
          - "failure_recovery.trigger" {component}
        """
        params = params or {}
        correlation_id = uuid.uuid4().hex
        await self._emit(
            EventType.DASHBOARD_ACTION_REQUESTED,
            {
                "action": action,
                "params": params,
                "principal": principal,
                "correlation_id": correlation_id,
            },
        )

        # --- Gate 1: SecurityManager authorization (fail-closed) ---
        decision = SecurityDecision.DENY
        if self._security_manager is not None:
            try:
                decision = self._security_manager.authorize(
                    principal=principal,
                    action=action,
                    resource=params.get("name") or params.get("component") or action,
                    context={"source": "dashboard", "params": params, "correlation_id": correlation_id},
                )
            except Exception as exc:  # noqa: BLE001 — security failure must block
                logger.warning("Dashboard authorize error (fail-closed): %s", exc)
                decision = SecurityDecision.DENY

        if decision != SecurityDecision.ALLOW:
            await self._emit(
                EventType.DASHBOARD_ACTION_REJECTED,
                {
                    "action": action,
                    "principal": principal,
                    "decision": getattr(decision, "value", str(decision)),
                    "correlation_id": correlation_id,
                },
            )
            return DashboardActionResult(
                action=action,
                authorized=False,
                decision=getattr(decision, "value", str(decision)),
                status="rejected",
                detail="SecurityManager denied the action (fail-closed). AI-OS retains authority.",
            )

        # --- Gate 2: bounded execution (AI-OS performs the work) ---
        await self._emit(
            EventType.DASHBOARD_ACTION_AUTHORIZED,
            {"action": action, "principal": principal, "correlation_id": correlation_id},
        )
        try:
            data = await self._execute_bounded_action(action, params)
            await self._emit(
                EventType.DASHBOARD_ACTION_COMPLETED,
                {"action": action, "principal": principal, "correlation_id": correlation_id, "data": data},
            )
            return DashboardActionResult(
                action=action,
                authorized=True,
                decision=getattr(decision, "value", str(decision)),
                status="completed",
                detail="Action executed under AI-OS authority.",
                data=data,
            )
        except Exception as exc:  # noqa: BLE001 — report, never hide
            logger.warning("Dashboard bounded action error: %s", exc)
            return DashboardActionResult(
                action=action,
                authorized=True,
                decision=getattr(decision, "value", str(decision)),
                status="error",
                detail=f"Bounded execution failed: {exc}",
            )

    async def _execute_bounded_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Perform a gated, bounded kernel operation. No autonomous authority."""
        if self._kernel is None:
            raise RuntimeError("Dashboard backend has no kernel reference")

        if action in ("integration.validate", "integration.connect", "integration.health_check"):
            name = params.get("name")
            status_service = getattr(self._kernel, "integration_status_service", None)
            if status_service is None:
                raise RuntimeError("Integration status service unavailable")
            if action == "integration.validate":
                report = await status_service.validate_integration(name)
            elif action == "integration.connect":
                report = await status_service.connect_integration(name)
            else:
                report = await status_service.health_check_integration(name)
            return _report_to_dict(report)

        if action == "self_loop.control":
            op = params.get("op")
            engine = getattr(self._kernel, "self_loop_engine", None)
            if engine is None:
                raise RuntimeError("Self-loop engine unavailable")
            if op == "pause":
                await engine.pause()
            elif op == "resume":
                await engine.resume()
            elif op == "stop":
                await engine.stop()
            else:
                raise ValueError(f"Unknown self_loop control op: {op}")
            return {"op": op, "status": engine.get_status()}

        if action == "self_loop.start_cycle":
            engine = getattr(self._kernel, "self_loop_engine", None)
            if engine is None:
                raise RuntimeError("Self-loop engine unavailable")
            # User-initiated trigger; the engine validates bounds internally.
            cycle = await engine.execute_cycle()
            return {"cycle_id": getattr(cycle, "cycle_id", None)}

        if action == "failure_recovery.trigger":
            component = params.get("component")
            manager = getattr(self._kernel, "failure_recovery_manager", None)
            if manager is None:
                raise RuntimeError("Failure recovery manager unavailable")
            record = await manager.recover(component)
            return {"recovery_id": record.recovery_id, "outcome": record.outcome}

        raise ValueError(f"Unsupported dashboard action: {action}")


# ------------------------------------------------------------------- serde utils


def _tally(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        key = str(it)
        out[key] = out.get(key, 0) + 1
    return out


def _report_to_dict(report: Any) -> dict[str, Any]:
    if report is None:
        return {}
    if hasattr(report, "to_dict"):
        try:
            return report.to_dict(redact_secrets=True)
        except TypeError:
            return report.to_dict()
    if isinstance(report, dict):
        return report
    return {"raw": str(report)}


def _serialize_self_prompt(prompt: Any) -> dict[str, Any]:
    """Best-effort read-only serialization of a SelfPrompt."""
    try:
        directive = getattr(prompt, "directive", None)
        metadata = getattr(prompt, "metadata", None)
        return {
            "prompt_id": getattr(prompt, "prompt_id", None),
            "cycle_id": getattr(prompt, "cycle_id", None),
            "action_type": getattr(directive, "action_type", None) if directive else None,
            "target_systems": getattr(directive, "target_systems", None) if directive else None,
            "validation_status": getattr(metadata, "validation_status", None) if metadata else None,
            "provenance_chain": getattr(directive, "provenance_chain", None) if directive else None,
        }
    except Exception:  # noqa: BLE001
        return {}


# Service registry key
SERVICE_KEY = "engineering.dashboard_backend"


async def create_dashboard_service(
    kernel: Any, event_bus: EventBus, security_manager: Any = None, config: Optional[dict[str, Any]] = None
) -> "DashboardService":
    """Factory for ServiceRegistry registration."""
    return DashboardService(
        kernel=kernel, event_bus=event_bus, security_manager=security_manager, config=config or {}
    )


__all__ = ["DashboardService", "DashboardActionResult", "SERVICE_KEY", "create_dashboard_service"]
