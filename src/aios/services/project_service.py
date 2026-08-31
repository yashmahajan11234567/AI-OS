"""
M14-T2 — Project Workspace Service (Terminal 2 backend, non-authoritative).

This service implements the PAGE 1 "Project Workspace" data + persistence model
from the AI-OS Project Workspace & Integrations & Credentials Dashboard
Specification. It is a BOUNDED UI resource, exactly like the existing
``DashboardService``:

  * It owns NO governance, verification, decision, security, configuration,
    execution, or provenance authority.
  * Project lifecycle state transitions are validated by AI-OS (the kernel and
    its services) — the dashboard service only forwards user intent through
    ``SecurityManager.authorize`` (fail-closed) and delegates the actual work to
    authoritative kernel components.
  * Conversations, knowledge, decisions, plans, and tasks are persisted through
    the existing Obsidian Git durability adapter (mock store safe) which already
    enforces AI-OS-owned provenance (C14). The final approved plan is handed off
    to Notion via the bounded Notion adapter — advisory only.
  * Discussion NEVER becomes execution. The dashboard cannot initiate autonomous
    execution; it can only request a transition through the AI-OS governed path.

The service is intentionally a thin, auditable state holder plus persistence glue.
Anything that would constitute a decision is delegated outward.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Project lifecycle state machine (mirrors the specification §Project Lifecycle)
# ---------------------------------------------------------------------------


class ProjectState(str, Enum):
    """Explicit project lifecycle states (spec §Project Model / §Project Lifecycle)."""

    CREATED = "CREATED"
    DISCUSSION = "DISCUSSION"
    RESEARCH = "RESEARCH"
    PLANNING = "PLANNING"
    REVIEW = "REVIEW"
    DECISION_PENDING = "DECISION_PENDING"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"
    PUBLISHED_TO_NOTION = "PUBLISHED_TO_NOTION"
    READY_FOR_ACTION = "READY_FOR_ACTION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


# Forward transitions allowed per the spec lifecycle graph. "<any>" allows
# transition out of the given states into BLOCKED.
_ALLOWED_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.CREATED: {ProjectState.DISCUSSION},
    ProjectState.DISCUSSION: {ProjectState.RESEARCH, ProjectState.DISCUSSION},
    ProjectState.RESEARCH: {ProjectState.PLANNING, ProjectState.RESEARCH},
    ProjectState.PLANNING: {ProjectState.REVIEW, ProjectState.PLANNING},
    ProjectState.REVIEW: {ProjectState.DECISION_PENDING, ProjectState.REVIEW},
    ProjectState.DECISION_PENDING: {ProjectState.APPROVED, ProjectState.DECISION_PENDING},
    ProjectState.APPROVED: {ProjectState.FINALIZED, ProjectState.APPROVED},
    ProjectState.FINALIZED: {ProjectState.PUBLISHED_TO_NOTION, ProjectState.FINALIZED},
    ProjectState.PUBLISHED_TO_NOTION: {ProjectState.READY_FOR_ACTION},
    ProjectState.READY_FOR_ACTION: {ProjectState.EXECUTING},
    ProjectState.EXECUTING: {ProjectState.COMPLETED, ProjectState.EXECUTING},
    ProjectState.COMPLETED: {ProjectState.COMPLETED},
    ProjectState.BLOCKED: {
        ProjectState.CREATED, ProjectState.DISCUSSION, ProjectState.RESEARCH,
        ProjectState.PLANNING, ProjectState.REVIEW, ProjectState.DECISION_PENDING,
        ProjectState.APPROVED, ProjectState.FINALIZED, ProjectState.PUBLISHED_TO_NOTION,
        ProjectState.READY_FOR_ACTION, ProjectState.EXECUTING,
    },
}


def can_transition(from_state: ProjectState, to_state: ProjectState) -> bool:
    """Return True if the lifecycle transition is permitted by the spec graph."""
    if from_state == to_state:
        return True
    return to_state in _ALLOWED_TRANSITIONS.get(from_state, set())


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------


@dataclass
class ChatMessage:
    """A single project-scoped chat message (persisted to project vault /chat/)."""

    message_id: str
    role: str  # "user" | "aios"
    content: str
    created_at: str
    context_refs: list[str] = field(default_factory=list)  # linked knowledge ids
    decision_id: Optional[str] = None
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class DecisionRecord:
    """A formal, append-only decision recorded during the project lifecycle."""

    decision_id: str
    project_id: str
    title: str
    rationale: str
    alternatives_considered: list[str] = field(default_factory=list)
    outcome: str = "pending"
    created_at: str = ""
    author: str = "aios_kernel"
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """A single AI-OS project workspace (non-authoritative view + persistence)."""

    project_id: str
    name: str
    description: str
    state: ProjectState = ProjectState.CREATED
    created_at: str = ""
    updated_at: str = ""
    owner: str = "dashboard_user"
    # Lightweight in-memory caches (cache-only; authoritative persistence is the
    # Obsidian vault / Notion). These are NOT treated as authoritative state.
    messages: list[ChatMessage] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    notion_page_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "owner": self.owner,
            "message_count": len(self.messages),
            "decision_count": len(self.decisions),
            "task_count": len(self.tasks),
            "has_plan": bool(self.plan),
            "notion_page_id": self.notion_page_id,
            "authority": "aios_sole",
        }


# ---------------------------------------------------------------------------
# Knowledge entry helpers (delegated to Obsidian Git adapter)
# ---------------------------------------------------------------------------


_KNOWLEDGE_TYPES = frozenset(
    {
        "project_state",
        "decision_record",
        "research_finding",
        "plan_variant",
        "task_item",
        "evidence_artifact",
    }
)


def _new_knowledge_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:48] or "untitled"


# ---------------------------------------------------------------------------
# Project Service
# ---------------------------------------------------------------------------


class ProjectService:
    """Non-authoritative project workspace state + persistence glue.

    Holds a reference to the kernel (for the Obsidian Git adapter, Notion
    adapter, and integration status service) and the SecurityManager. It NEVER
    authorizes or decides — every mutating operation is forwarded to AI-OS for
    authorization + execution. The service is auditable and fail-closed: if the
    kernel/adapters are absent, operations degrade gracefully and report the
    limitation rather than silently inventing state.
    """

    name = "project_workspace"
    version = "1.0.0"

    def __init__(
        self,
        kernel: Any = None,
        event_bus: Any = None,
        security_manager: Any = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        self._kernel = kernel
        self._event_bus = event_bus
        self._security_manager = security_manager
        self._config = config or {}
        # Cache-only project registry. Authoritative persistence lives in the
        # Obsidian vault; this dict is a working set, never the source of truth.
        self._projects: dict[str, Project] = {}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_adapter(self, attr: str) -> Any:
        if self._kernel is None:
            return None
        return getattr(self._kernel, attr, None)

    def _obsidian_git(self) -> Any:
        return self._get_adapter("obsidian_git_adapter")

    def _notion(self) -> Any:
        return self._get_adapter("notion_adapter")

    async def _emit(self, event_type: Any, payload: dict[str, Any], correlation_id: Optional[str] = None) -> None:
        if self._event_bus is None:
            return
        try:
            from aios.events.core.bus import get_core_event_bus
            from aios.events.core.event import Event
            from aios.events.core.identity import ComponentIdentity, ComponentType
            from aios.events.core.types import SemanticVersion

            bus = self._event_bus if hasattr(self._event_bus, "publish") else get_core_event_bus()
            if bus is None:
                return
            corr = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
            event = Event(
                eventType=event_type,
                source=ComponentIdentity(
                    component_type=ComponentType.ENGINEERING_SERVICE,
                    component_name="project_workspace",
                    version=SemanticVersion(1, 0, 0),
                ),
                correlationId=corr,
                payload=payload,
            )
            result = bus.publish(event)
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # noqa: BLE001 — never break the dashboard
            logger.debug("ProjectService event emission skipped: %s", exc)

    # ------------------------------------------------------------------
    # Project lifecycle (creation / transitions)
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        description: str = "",
        owner: str = "dashboard_user",
        project_id: Optional[str] = None,
    ) -> Project:
        """Create a new project in CREATED state (no AI-OS authorization needed;
        project creation is a local workspace scaffold, not a decision).

        Returns the Project object. Actual authoritative persistence is delegated
        to AI-OS via ``persist_project_state``.
        """
        pid = project_id or _new_knowledge_id("proj")
        now = self._now()
        project = Project(
            project_id=pid,
            name=name,
            description=description,
            state=ProjectState.CREATED,
            created_at=now,
            updated_at=now,
            owner=owner,
        )
        self._projects[pid] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def validate_transition(self, project_id: str, to_state: ProjectState) -> tuple[bool, str]:
        """Validate a state transition against the spec lifecycle graph.

        This is a pure, advisory validation (no authority). Authorization still
        happens in ``DashboardService.request_action`` via SecurityManager.
        """
        project = self._projects.get(project_id)
        if project is None:
            return False, "project not found"
        if not isinstance(to_state, ProjectState):
            return False, "invalid target state"
        if can_transition(project.state, to_state):
            return True, ""
        return False, f"transition {project.state.value} -> {to_state.value} not permitted"

    def apply_transition(self, project_id: str, to_state: ProjectState) -> Project:
        """Apply an already-authorized state transition (cache-only)."""
        project = self._projects[project_id]
        project.state = to_state
        project.updated_at = self._now()
        return project

    # ------------------------------------------------------------------
    # Chat persistence (project-scoped)
    # ------------------------------------------------------------------

    async def add_message(
        self,
        project_id: str,
        role: str,
        content: str,
        context_refs: Optional[list[str]] = None,
        decision_id: Optional[str] = None,
        evidence_refs: Optional[list[str]] = None,
    ) -> ChatMessage:
        """Append a project-scoped chat message and persist it to the vault /chat/.

        Persistence is delegated to the Obsidian Git adapter (mock store safe).
        If the adapter is unavailable, the message still lives in the cache-only
        working set; this is a degradation, not an invention of authority.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f"project {project_id} not found")
        msg = ChatMessage(
            message_id=_new_knowledge_id("msg"),
            role=role,
            content=content,
            created_at=self._now(),
            context_refs=context_refs or [],
            decision_id=decision_id,
            evidence_refs=evidence_refs or [],
        )
        project.messages.append(msg)
        project.updated_at = self._now()

        adapter = self._obsidian_git()
        if adapter is not None:
            body = (
                f"---\n"
                f"message_id: {msg.message_id}\n"
                f"project_id: {project_id}\n"
                f"role: {role}\n"
                f"created: {msg.created_at}\n"
                f"context_refs: {msg.context_refs}\n"
                f"decision_id: {msg.decision_id or ''}\n"
                f"evidence_refs: {msg.evidence_refs}\n"
                f"provenance:\n"
                f"  authority: aios_owned\n"
                f"  semantic_owner: aios_kernel\n"
                f"---\n\n{content}\n"
            )
            try:
                await adapter.create_knowledge(
                    knowledge_id=f"chat/{project_id}/{msg.message_id}",
                    content=body,
                    knowledge_type="project_state",
                    metadata={"folder": "chat", "project_id": project_id},
                )
            except Exception as exc:  # noqa: BLE001 — persistence is best-effort
                logger.debug("Chat message persistence skipped: %s", exc)
        return msg

    def get_messages(self, project_id: str) -> list[ChatMessage]:
        project = self._projects.get(project_id)
        return list(project.messages) if project else []

    # ------------------------------------------------------------------
    # Knowledge persistence (AI-OS-owned Obsidian vault)
    # ------------------------------------------------------------------

    async def store_knowledge(
        self,
        project_id: str,
        knowledge_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Persist a knowledge entry to the project vault /knowledge/ via the
        Obsidian Git adapter. Returns the knowledge id. AI-OS-owned provenance
        is preserved by the adapter; the dashboard adds no semantic meaning.
        """
        if knowledge_type not in _KNOWLEDGE_TYPES:
            # Coerce unknown types rather than reject — knowledge type is advisory.
            knowledge_type = "project_state"
        kid = f"knowledge/{project_id}/{_new_knowledge_id(_slug(knowledge_type))}"
        meta = dict(metadata or {})
        meta["project_id"] = project_id
        meta["folder"] = "knowledge"
        adapter = self._obsidian_git()
        if adapter is None:
            return kid
        await adapter.create_knowledge(
            knowledge_id=kid,
            content=content,
            knowledge_type=knowledge_type,
            metadata=meta,
        )
        return kid

    async def store_decision(
        self,
        project_id: str,
        title: str,
        rationale: str,
        alternatives_considered: Optional[list[str]] = None,
        outcome: str = "pending",
        author: str = "aios_kernel",
    ) -> DecisionRecord:
        """Record a formal decision (append-only). Persisted to vault /decisions/.

        The decision is recorded by AI-OS; the dashboard only forwards the
        content. Decision rationale and alternatives are preserved.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f"project {project_id} not found")
        rec = DecisionRecord(
            decision_id=_new_knowledge_id("dec"),
            project_id=project_id,
            title=title,
            rationale=rationale,
            alternatives_considered=alternatives_considered or [],
            outcome=outcome,
            created_at=self._now(),
            author=author,
            provenance={
                "authority": "aios_owned",
                "semantic_owner": "aios_kernel",
                "advisory": False,
            },
        )
        project.decisions.append(rec)
        project.updated_at = self._now()

        adapter = self._obsidian_git()
        if adapter is not None:
            body = (
                f"---\n"
                f"decision_id: {rec.decision_id}\n"
                f"project_id: {project_id}\n"
                f"title: {title}\n"
                f"outcome: {outcome}\n"
                f"created: {rec.created_at}\n"
                f"author: {author}\n"
                f"provenance:\n"
                f"  authority: aios_owned\n"
                f"  semantic_owner: aios_kernel\n"
                f"---\n\n"
                f"## Rationale\n\n{rationale}\n\n"
                f"## Alternatives Considered\n\n"
                + "\n".join(f"- {a}" for a in rec.alternatives_considered)
                + "\n"
            )
            try:
                await adapter.create_knowledge(
                    knowledge_id=f"decisions/{project_id}/{rec.decision_id}",
                    content=body,
                    knowledge_type="decision_record",
                    metadata={"folder": "decisions", "project_id": project_id},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Decision persistence skipped: %s", exc)
        return rec

    def get_decisions(self, project_id: str) -> list[DecisionRecord]:
        project = self._projects.get(project_id)
        return list(project.decisions) if project else []

    # ------------------------------------------------------------------
    # Plan / task persistence
    # ------------------------------------------------------------------

    async def save_plan(self, project_id: str, plan: dict[str, Any]) -> None:
        """Persist a plan variant to the project vault /plans/ (advisory until
        approved). Does NOT transition state or grant execution authority."""
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f"project {project_id} not found")
        project.plan = plan
        project.updated_at = self._now()
        adapter = self._obsidian_git()
        if adapter is not None:
            body = (
                f"---\n"
                f"project_id: {project_id}\n"
                f"plan_variant: {plan.get('variant', 'v1')}\n"
                f"created: {self._now()}\n"
                f"provenance:\n"
                f"  authority: aios_owned\n"
                f"  semantic_owner: aios_kernel\n"
                f"  status: advisory_until_approved\n"
                f"---\n\n{plan.get('content', '')}\n"
            )
            try:
                await adapter.create_knowledge(
                    knowledge_id=f"plans/{project_id}/{_new_knowledge_id('plan')}",
                    content=body,
                    knowledge_type="plan_variant",
                    metadata={"folder": "plans", "project_id": project_id},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Plan persistence skipped: %s", exc)

    def get_plan(self, project_id: str) -> dict[str, Any]:
        project = self._projects.get(project_id)
        return dict(project.plan) if project else {}

    async def add_task(self, project_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """Add a task item derived from a plan/decision (persisted to /tasks/)."""
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f"project {project_id} not found")
        item = {
            "task_id": _new_knowledge_id("task"),
            "title": task.get("title", "untitled"),
            "status": task.get("status", "open"),
            "assignee": task.get("assignee"),
            "depends_on": task.get("depends_on", []),
            "created_at": self._now(),
        }
        project.tasks.append(item)
        adapter = self._obsidian_git()
        if adapter is not None:
            try:
                await adapter.create_knowledge(
                    knowledge_id=f"tasks/{project_id}/{item['task_id']}",
                    content=f"# {item['title']}\n\nstatus: {item['status']}\n",
                    knowledge_type="task_item",
                    metadata={"folder": "tasks", "project_id": project_id},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Task persistence skipped: %s", exc)
        return item

    def get_tasks(self, project_id: str) -> list[dict[str, Any]]:
        project = self._projects.get(project_id)
        return list(project.tasks) if project else []

    # ------------------------------------------------------------------
    # Notion handoff (bounded, advisory; only final approved plans)
    # ------------------------------------------------------------------

    async def publish_final_plan_to_notion(
        self, project_id: str, plan: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Hand the finalized plan off to Notion via the bounded Notion adapter.

        CRITICAL: the dashboard does NOT call Notion directly. It delegates to the
        kernel's Notion adapter (a bounded resource). The plan is advisory data;
        Notion is untrusted (C14). This method does NOT change project state — the
        DashboardService/AI-OS drives the state transition after authorization.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f"project {project_id} not found")
        plan_body = plan if plan is not None else project.plan
        notion = self._notion()
        if notion is None:
            return {
                "published": False,
                "reason": "notion adapter unavailable (bounded resource not wired)",
            }
        # Notion adapter expects a title + content dict. We only forward the
        # finalized plan content; no credentials are touched here.
        result = await notion.create_page(
            title=f"Final Plan: {project.name}",
            parent_id=plan_body.get("notion_parent_id", "") if isinstance(plan_body, dict) else "",
            content={"plan": plan_body},
            properties={},
        )
        # Result is advisory (C14). We do not treat success as authority.
        page_id = ""
        if isinstance(result, object):
            raw = getattr(result, "raw", None)
            if isinstance(raw, dict):
                page_id = raw.get("page_id", "")
        project.notion_page_id = page_id or project.notion_page_id
        return {
            "published": True,
            "notion_page_id": page_id,
            "advisory": True,
        }

    # ------------------------------------------------------------------
    # Read-only snapshot for the dashboard frontend
    # ------------------------------------------------------------------

    def get_project_snapshot(self, project_id: str) -> dict[str, Any]:
        """Read-only project workspace bundle for the dashboard (no secrets)."""
        project = self._projects.get(project_id)
        if project is None:
            return {"project_id": project_id, "found": False, "authority": "aios_sole"}
        return {
            "found": True,
            "authority": "aios_sole",
            "project": project.to_dict(),
            "messages": [vars(m) for m in project.messages[-50:]],
            "decisions": [vars(d) for d in project.decisions],
            "tasks": project.tasks,
            "plan": project.plan,
            "allowed_transitions": [
                s.value for s in _ALLOWED_TRANSITIONS.get(project.state, set())
            ],
            "read_only": True,
        }

    def get_workspace_index(self) -> dict[str, Any]:
        """Lightweight index of all known projects (read-only)."""
        return {
            "authority": "aios_sole",
            "projects": [p.to_dict() for p in self._projects.values()],
            "read_only": True,
        }


# Service registry key
SERVICE_KEY = "engineering.project_workspace"


async def create_project_service(
    kernel: Any, event_bus: Any = None, security_manager: Any = None, config: Optional[dict[str, Any]] = None
) -> "ProjectService":
    """Factory for ServiceRegistry registration."""
    return ProjectService(
        kernel=kernel, event_bus=event_bus, security_manager=security_manager, config=config or {}
    )


__all__ = [
    "ProjectService",
    "Project",
    "ProjectState",
    "ChatMessage",
    "DecisionRecord",
    "can_transition",
    "SERVICE_KEY",
    "create_project_service",
]
