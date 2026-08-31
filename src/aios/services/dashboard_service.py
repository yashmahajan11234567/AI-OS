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
  6. Project Workspace    -> project-scoped chat/knowledge/decisions/plans (NEW)
  7. Integrations & Credentials -> ALL integrations config/credential/health (NEW)
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
from aios.services.project_service import (
    ProjectService,
    ProjectState,
    can_transition,
)

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
        self._project_service = None
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="dashboard_backend",
            version=SemanticVersion(1, 0, 0),
        )

    # ------------------------------------------------------------------ helpers

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _emit(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        """Emit a canonical dashboard event (C1). Failures are non-fatal.

        Correlation is carried on the canonical top-level ``Event.correlationId``
        field (a UUID), never inside the payload. INV-EVT-011 forbids base-contract
        field names (incl. ``correlationId`` / ``correlation_id``) inside an
        EventPayload, so the dashboard-local ``correlation_id`` hex string is
        preserved in the payload under the non-forbidden ``request_id`` key, while
        the same UUID is placed on the Event's top-level ``correlationId`` so the
        event passes validation and reaches the real EventBus.
        """
        if self._event_bus is None:
            return
        try:
            # Canonical correlation: a UUID on the Event's top-level field.
            corr_uuid = (
                uuid.UUID(correlation_id)
                if correlation_id is not None
                else uuid.uuid4()
            )
            event = Event(
                eventType=event_type,
                source=self._identity,
                correlationId=corr_uuid,
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
    # PAGE 6 — Project Workspace (project-scoped chat/knowledge)
    # ============================================================

    def _resolve_project_service(self) -> Optional[ProjectService]:
        """Resolve the bounded ProjectService (authored by AI-OS Terminal 1)."""
        if self._project_service is not None:
            return self._project_service
        if self._kernel is not None:
            return getattr(self._kernel, "project_service", None)
        return None

    def get_project_workspace(self, project_id: Optional[str] = None) -> dict[str, Any]:
        """Read-only view of the project workspace (PAGE 1 of the spec).

        The dashboard visualizes project state, chat, knowledge, decisions, plans,
        and tasks. It NEVER authorizes transitions or executions itself — every
        mutation is forwarded through ``request_action`` -> SecurityManager.
        """
        svc = self._resolve_project_service()
        if svc is None:
            return {
                "page": "project_workspace",
                "authority": "aios_sole",
                "available": False,
                "reason": "project_service not wired (authored by AI-OS Terminal 1)",
                "read_only": True,
                "projects": [],
            }
        if project_id:
            snapshot = svc.get_project_snapshot(project_id)
            snapshot["page"] = "project_workspace"
            snapshot["authority"] = "aios_sole"
            snapshot["read_only"] = True
            snapshot["available"] = True
            return snapshot
        index = svc.get_workspace_index()
        index["page"] = "project_workspace"
        index["authority"] = "aios_sole"
        index["read_only"] = True
        index["available"] = True
        return index

    # ============================================================
    # PAGE 7 — Integrations & Credentials (authoritative inventory)
    # ============================================================

    def get_integrations_credentials(self) -> dict[str, Any]:
        """Central config/credential/connection/health view of ALL integrations.

        For every integration discovered by the authoritative inventory it shows:
        name, purpose, required credentials, whether a credential is configured
        (YES/NO — never the value), filesystem/Git/local-endpoint config, status,
        connection mode (mock/real), and health. No secret value is ever exposed;
        secret redaction is delegated to the existing ``redact_secrets`` and the
        ``IntegrationStatusReport.to_dict(redact_secrets=True)`` path.
        """
        from aios.integrations import CANONICAL_INTEGRATIONS, load_integrations_config
        from aios.integrations.config import IntegrationMode

        status_service = (
            getattr(self._kernel, "integration_status_service", None) if self._kernel else None
        )

        integrations: list[dict[str, Any]] = []
        try:
            if status_service is not None:
                integrations = status_service.get_all_status_dict(redact_secrets=True)
        except Exception:  # noqa: BLE001 — defensive read
            integrations = []

        # Merge authoritative metadata (purpose, required credential kinds, config
        # categories) from the local inventory so the dashboard shows the full
        # picture, not just what the runtime status service happens to expose.
        registry = load_integrations_config()
        meta = _INTEGRATION_INVENTORY
        merged: list[dict[str, Any]] = []
        seen = set()
        for entry in integrations:
            name = entry.get("integration_name") or entry.get("name")
            seen.add(name)
            detail = dict(meta.get(name, {}))
            entry["purpose"] = detail.get("purpose", "")
            entry["required_credentials"] = detail.get("required_credentials", [])
            entry["requires_filesystem_path"] = detail.get("requires_filesystem_path", False)
            entry["requires_git_config"] = detail.get("requires_git_config", False)
            entry["requires_local_endpoint"] = detail.get("requires_local_endpoint", False)
            entry["not_required_reason"] = detail.get("not_required_reason", "")
            entry["credential_configured"] = _infer_credential_configured(name, registry, entry)
            entry["last_verified"] = entry.get("last_health_check") or entry.get("last_validated")
            merged.append(entry)
        # Include authoritative entries not surfaced by the runtime status service.
        # Covers BOTH the canonical registry integrations AND the inventory-only
        # integrations (obsidian_git, supabase, n8n) so the dashboard satisfies the
        # spec requirement to show ALL integrations from the authoritative inventory.
        for name in sorted(set(list(CANONICAL_INTEGRATIONS) + list(meta.keys()))):
            if name in seen:
                continue
            detail = meta.get(name, {})
            entry = registry.get(name)
            mode = entry.mode.value if entry else "mock"
            merged.append({
                "integration_name": name,
                "state": entry.state.value if entry else "absent",
                "mode": mode,
                "real_allowed": entry.real_allowed() if entry else False,
                "user_resource_present": entry.user_resource_present if entry else False,
                "real_gated": entry.real_gated if entry else True,
                "requires_user_resource": entry.requires_user_resource if entry else True,
                "purpose": detail.get("purpose", ""),
                "required_credentials": detail.get("required_credentials", []),
                "requires_filesystem_path": detail.get("requires_filesystem_path", False),
                "requires_git_config": detail.get("requires_git_config", False),
                "requires_local_endpoint": detail.get("requires_local_endpoint", False),
                "not_required_reason": detail.get("not_required_reason", ""),
                "credential_configured": _infer_credential_configured(name, registry, {}),
                "last_verified": None,
            })

        # Go-live readiness summary (architecturally safe: reports config state
        # only, never attempts connections or reveals secrets).
        required_creds = [m for m in meta.values() if m.get("required_credentials")]
        configured = sum(1 for m in merged if m.get("credential_configured"))
        total_creds = len(required_creds)
        missing = [
            m.get("integration_name")
            for m in merged
            if m.get("required_credentials") and not m.get("credential_configured")
        ]
        readiness = {
            "core_services": _kernel_core_ok(self._kernel),
            "required_credentials": f"{configured}/{total_creds}",
            "external_integrations": f"{len(merged)}/{len(merged)}",
            "knowledge_system": _adapter_present(self._kernel, "obsidian_git_adapter"),
            "model_providers": _model_providers_status(),
            "database": _adapter_present(self._kernel, "supabase_adapter"),
            "status": "READY" if not missing and _kernel_core_ok(self._kernel) else "NOT READY",
            "missing": missing,
        }

        return {
            "page": "integrations_credentials",
            "authority": "aios_sole",
            "integrations": merged,
            "secret_exposure": "NONE — values never transmitted; only configured YES/NO",
            "readiness": readiness,
            "read_only": True,
        }

    # ============================================================
    # Aggregated snapshot for frontend
    # ============================================================

    def get_all_pages(self) -> dict[str, Any]:
        """All seven read-only page bundles in one call."""
        return {
            "generated_at": self._now(),
            "authority_model": "aios_sole_authority",
            "pages": {
                "planning_chat": self.get_planning_chat(),
                "resource_onboarding": self.get_resource_onboarding(),
                "project_execution": self.get_project_execution(),
                "knowledge_history": self.get_knowledge_history(),
                "system_health": self.get_system_health(),
                "project_workspace": self.get_project_workspace(),
                "integrations_credentials": self.get_integrations_credentials(),
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
          - "project.create"         {name, description?}  (local workspace scaffold)
          - "project.transition"     {project_id, to_state}  (AI-OS validates lifecycle)
          - "project.publish_notion" {project_id, plan?}    (bounded Notion handoff)
          - "project.clear_action"   {project_id}           (READY_FOR_ACTION transition)
        """
        params = params or {}
        correlation_id = uuid.uuid4().hex
        await self._emit(
            EventType.DASHBOARD_ACTION_REQUESTED,
            {
                "action": action,
                "params": params,
                "principal": principal,
                "request_id": correlation_id,
            },
            correlation_id=correlation_id,
        )

        # --- Gate 1: SecurityManager authorization (fail-closed) ---
        decision = SecurityDecision.DENY
        if self._security_manager is not None:
            try:
                decision = self._security_manager.authorize(
                    principal=principal,
                    action=action,
                    resource=(
                        params.get("name")
                        or params.get("component")
                        or params.get("project_id")
                        or action
                    ),
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
                    "request_id": correlation_id,
                },
                correlation_id=correlation_id,
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
            {"action": action, "principal": principal, "request_id": correlation_id},
            correlation_id=correlation_id,
        )
        try:
            data = await self._execute_bounded_action(action, params)
            await self._emit(
                EventType.DASHBOARD_ACTION_COMPLETED,
                {"action": action, "principal": principal, "request_id": correlation_id, "data": data},
                correlation_id=correlation_id,
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

        # --- Project Workspace actions (PAGE 1) ---
        # All of these delegate to the authoritative ProjectService / kernel. The
        # dashboard service itself decides nothing; it only forwards after the
        # SecurityManager gate (fail-closed) has returned ALLOW.
        if action in (
            "project.create",
            "project.transition",
            "project.publish_notion",
            "project.clear_action",
        ):
            project_service = self._resolve_project_service()
            if project_service is None:
                raise RuntimeError("ProjectService unavailable (authored by AI-OS Terminal 1)")
            return await self._execute_project_action(action, params, project_service)

        raise ValueError(f"Unsupported dashboard action: {action}")

    async def _execute_project_action(
        self,
        action: str,
        params: dict[str, Any],
        project_service: ProjectService,
    ) -> dict[str, Any]:
        """Perform a gated, bounded project operation. No autonomous authority.

        Every transition/handoff is validated by AI-OS (ProjectService lifecycle
        rules + the kernel's adapters). The dashboard never performs execution
        without an explicit, authorized request.
        """
        if action == "project.create":
            project = project_service.create_project(
                name=params.get("name", "Untitled Project"),
                description=params.get("description", ""),
                owner=params.get("owner", "dashboard_user"),
            )
            return {"project_id": project.project_id, "state": project.state.value}

        if action == "project.transition":
            project_id = params.get("project_id")
            to_state_raw = params.get("to_state")
            to_state = ProjectState(to_state_raw) if to_state_raw else None
            if project_id is None or to_state is None:
                raise ValueError("project.transition requires project_id and to_state")
            ok, reason = project_service.validate_transition(project_id, to_state)
            if not ok:
                raise ValueError(f"Lifecycle transition rejected by AI-OS: {reason}")
            project = project_service.apply_transition(project_id, to_state)
            return {"project_id": project_id, "state": project.state.value}

        if action == "project.publish_notion":
            project_id = params.get("project_id")
            if project_id is None:
                raise ValueError("project.publish_notion requires project_id")
            result = await project_service.publish_final_plan_to_notion(
                project_id, plan=params.get("plan")
            )
            return result

        if action == "project.clear_action":
            project_id = params.get("project_id")
            if project_id is None:
                raise ValueError("project.clear_action requires project_id")
            ok, reason = project_service.validate_transition(
                project_id, ProjectState.READY_FOR_ACTION
            )
            if not ok:
                raise ValueError(f"Cannot clear for action: {reason}")
            project = project_service.apply_transition(
                project_id, ProjectState.READY_FOR_ACTION
            )
            return {"project_id": project_id, "state": project.state.value}

        raise ValueError(f"Unsupported project action: {action}")


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


# -------------------------------------------------------------------
# Integrations & Credentials helper tables
# -------------------------------------------------------------------

# Authoritative inventory metadata (spec §Page 2). Purpose, required credential
# kinds, and configuration categories per integration. This augments (never
# replaces) the runtime IntegrationStatusService output. No secret values here.
_INTEGRATION_INVENTORY: dict[str, dict[str, Any]] = {
    "hermes_agent_acp": {
        "purpose": "Agent communication protocol (ACP) — preferred worker path",
        "required_credentials": ["hermes-agent repo path"],
        "requires_filesystem_path": True,
        "requires_git_config": False,
        "requires_local_endpoint": False,
    },
    "hermes_agent_ext": {
        "purpose": "Agent communication protocol (MCP fallback worker path)",
        "required_credentials": ["MCP server config"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "playwright_mcp": {
        "purpose": "Browser execution substrate",
        "required_credentials": ["Node.js + @playwright/mcp + browser"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "obsidian": {
        "purpose": "Knowledge/durability layer (vault)",
        "required_credentials": ["vault path (local)"],
        "requires_filesystem_path": True,
        "requires_git_config": False,
        "requires_local_endpoint": False,
    },
    "graphify": {
        "purpose": "Knowledge/relationship graph",
        "required_credentials": ["endpoint"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "claude_mem": {
        "purpose": "External memory context (advisory)",
        "required_credentials": ["token"],
        "requires_filesystem_path": True,
        "requires_git_config": False,
        "requires_local_endpoint": False,
    },
    "notion": {
        "purpose": "Planning publication target (final approved plans)",
        "required_credentials": ["Notion API token"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "agent_reach": {
        "purpose": "Agent communication protocol (registered-capability only)",
        "required_credentials": [],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": False,
        "not_required_reason": "capability registration only; no external credential",
    },
    "freellmapi": {
        "purpose": "Local LLM provider (dev/test only)",
        "required_credentials": ["API URL + key"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "anthropic": {
        "purpose": "Standard model provider",
        "required_credentials": ["API key (runtime)"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "openai": {
        "purpose": "Standard model provider",
        "required_credentials": ["API key (runtime)"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "supabase": {
        "purpose": "Persistent storage layer",
        "required_credentials": ["URL + anon key"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "n8n": {
        "purpose": "Bounded automation/execution",
        "required_credentials": ["Base URL + API key"],
        "requires_filesystem_path": False,
        "requires_git_config": False,
        "requires_local_endpoint": True,
    },
    "obsidian_git": {
        "purpose": "Git durability for knowledge vault",
        "required_credentials": ["Vault path + Git remote"],
        "requires_filesystem_path": True,
        "requires_git_config": True,
        "requires_local_endpoint": False,
    },
}


def _infer_credential_configured(
    name: str, registry: Any, entry: dict[str, Any]
) -> bool:
    """Infer ONLY whether a credential/required-resource is configured (YES/NO).

    Never returns the value. Uses the existing integration config + env-var
    presence detection (redacted). Falls back to user_resource_present for
    resource-gated integrations.
    """
    from aios.security.secrets import is_secret_env_key

    detail = _INTEGRATION_INVENTORY.get(name, {})
    required = detail.get("required_credentials", [])
    if not required:
        return True  # nothing required -> trivially "configured / NOT REQUIRED"
    # If the runtime status service already computed a user-resource presence,
    # trust it (it never exposes the value).
    if entry.get("user_resource_present"):
        return True
    # Detect env-var presence by key name only (no values touched).
    cfg = registry.get(name) if registry is not None else None
    if cfg is not None:
        # IntegrationConfig may carry flags set by validation.
        if getattr(cfg, "user_resource_present", False):
            return True
    # Conservative env-key presence check (key names only, never values).
    import os

    cand = [c.lower() for c in required]
    for key in os.environ:
        kl = key.lower()
        if any(is_secret_env_key(key) for _ in [0]):
            pass
        # Map known required credential hints to env vars.
        if "api key" in kl or "token" in kl or "anon key" in kl or "api_key" in kl:
            if kl.endswith("_key") or "token" in kl or "secret" in kl or kl.endswith("_anon_key"):
                if is_secret_env_key(key):
                    return True
        if "vault path" in cand or "vault" in kl:
            if kl in ("obsidian_vault_path", "obsidian__vault_path"):
                if os.environ.get(key):
                    return True
        if "git remote" in cand or "remote" in kl:
            if kl in ("obsidian_git_remote_url",):
                if os.environ.get(key):
                    return True
        if "endpoint" in cand or "base url" in cand or "url" in kl:
            if any(t in kl for t in ("url", "endpoint", "base_url")):
                if is_secret_env_key(key) or kl in (
                    "supabase_url", "n8n_base_url", "graphify_endpoint",
                    "freellm_api_endpoint", "notion_parent_id",
                ):
                    if os.environ.get(key):
                        return True
    return False


def _kernel_core_ok(kernel: Any) -> bool:
    if kernel is None:
        return False
    try:
        stats = kernel.get_stats()
        return bool(stats.get("kernel", {}).get("running", False))
    except Exception:  # noqa: BLE001
        return False


def _adapter_present(kernel: Any, attr: str) -> bool:
    if kernel is None:
        return False
    return getattr(kernel, attr, None) is not None


def _model_providers_status() -> str:
    """Report model-provider credential presence as X/Y without exposing values."""
    import os

    from aios.security.secrets import is_secret_env_key

    total = 0
    present = 0
    for key in os.environ:
        if is_secret_env_key(key) and ("ANTHROPIC" in key or "OPENAI" in key or "FREELLM" in key):
            total += 1
            present += 1
    # If no env keys at all, we still report the known provider count (2 standard).
    if total == 0:
        return "0/2"
    return f"{present}/{total}"


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
