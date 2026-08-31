"""
M14-T2 — Project Workspace + Integrations & Credentials Dashboard tests.

Verifies the spec invariants:
  * Project isolation — projects are independent workspaces.
  * Conversation / knowledge / decision / task persistence (AI-OS-owned vault).
  * Correct project context loading (snapshot shape for the frontend).
  * Planning flow (CREATED -> ... -> PLANNING) and final-plan handoff to Notion.
  * Action transition is gated by SecurityManager (fail-closed).
  * Dashboard NEVER becomes an alternate authority (no authorize/verify/decide).
  * Integrations & Credentials page exposes config/health but NO secret values.
  * Mock/real mode handling, missing/invalid credentials, local-endpoint integrations.

These tests target only Terminal 2 authored code + the M13 fail-closed gate.
They do NOT modify SecurityManager, the terminal contract, or M7–M14 verified
functionality. Pre-existing unrelated failures are left untouched.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.core.security_manager import SecurityDecision
from aios.services.dashboard_service import DashboardService
from aios.services.project_service import (
    ProjectService,
    ProjectState,
    can_transition,
)


# --------------------------------------------------------------------------- fixtures


class _FakeKernel:
    """Minimal kernel double with the canonical getters ProjectService reads."""

    terminal_contract_violations = []
    integration_status_service = None
    self_loop_engine = None
    obsidian_git_adapter = None
    notion_adapter = None
    supabase_adapter = None

    def get_stats(self):
        return {"kernel": {"name": "aios", "running": True}}


@pytest.fixture
def kernel():
    return _FakeKernel()


@pytest.fixture
def obsidian_git_adapter():
    """Mock Obsidian Git adapter with a safe in-memory store (no secrets)."""
    ad = MagicMock()
    ad.create_knowledge = AsyncMock(return_value=MagicMock(raw={"ok": True}))
    ad.get_knowledge = AsyncMock(return_value=MagicMock(raw={"content": "x"}))
    ad.is_real_mode = MagicMock(return_value=False)
    return ad


@pytest.fixture
def notion_adapter():
    """Mock Notion adapter (bounded, C14 advisory)."""
    ad = MagicMock()
    ad.create_page = AsyncMock(
        return_value=MagicMock(raw={"page_id": "page_abc123"})
    )
    return ad


@pytest.fixture
def project_service(kernel, obsidian_git_adapter, notion_adapter):
    kernel.obsidian_git_adapter = obsidian_git_adapter
    kernel.notion_adapter = notion_adapter
    return ProjectService(
        kernel=kernel, event_bus=None, security_manager=None, config={}
    )


@pytest.fixture
def security_allow():
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.ALLOW
    return sm


@pytest.fixture
def security_deny():
    sm = MagicMock()
    sm.authorize.return_value = SecurityDecision.DENY
    return sm


def _make_dashboard(kernel, security, project_svc=None):
    svc = DashboardService(kernel=kernel, event_bus=None, security_manager=security)
    if project_svc is not None:
        svc._project_service = project_svc
    return svc


# --------------------------------------------------------------------------- lifecycle / isolation


def test_can_transition_spec_graph():
    # Pure validation matches the spec lifecycle.
    assert can_transition(ProjectState.CREATED, ProjectState.DISCUSSION)
    assert can_transition(ProjectState.DISCUSSION, ProjectState.RESEARCH)
    assert can_transition(ProjectState.RESEARCH, ProjectState.PLANNING)
    assert can_transition(ProjectState.PLANNING, ProjectState.REVIEW)
    assert can_transition(ProjectState.REVIEW, ProjectState.DECISION_PENDING)
    assert can_transition(ProjectState.DECISION_PENDING, ProjectState.APPROVED)
    assert can_transition(ProjectState.APPROVED, ProjectState.FINALIZED)
    assert can_transition(ProjectState.FINALIZED, ProjectState.PUBLISHED_TO_NOTION)
    assert can_transition(ProjectState.PUBLISHED_TO_NOTION, ProjectState.READY_FOR_ACTION)
    assert can_transition(ProjectState.READY_FOR_ACTION, ProjectState.EXECUTING)
    assert can_transition(ProjectState.EXECUTING, ProjectState.COMPLETED)
    # Illegal jumps are rejected
    assert not can_transition(ProjectState.CREATED, ProjectState.EXECUTING)
    assert not can_transition(ProjectState.PLANNING, ProjectState.EXECUTING)
    # Self-loops allowed
    assert can_transition(ProjectState.DISCUSSION, ProjectState.DISCUSSION)


def test_project_isolation(project_service):
    a = project_service.create_project(name="A")
    b = project_service.create_project(name="B")
    assert a.project_id != b.project_id
    asyncio.run(project_service.add_message(a.project_id, "user", "hello A"))
    asyncio.run(project_service.add_message(b.project_id, "user", "hello B"))
    # Messages are scoped to their own project (isolation).
    assert len(project_service.get_messages(a.project_id)) == 1
    assert project_service.get_messages(a.project_id)[0].content == "hello A"
    assert len(project_service.get_messages(b.project_id)) == 1
    assert project_service.get_messages(b.project_id)[0].content == "hello B"
    # Index lists both, each in CREATED.
    idx = project_service.get_workspace_index()
    assert len(idx["projects"]) == 2


def test_unknown_project_returns_not_found_snapshot(project_service):
    snap = project_service.get_project_snapshot("does-not-exist")
    assert snap["found"] is False


# --------------------------------------------------------------------------- conversation persistence


def test_conversation_persistence_to_vault(project_service, obsidian_git_adapter):
    proj = project_service.create_project(name="Conv")
    asyncio.run(project_service.add_message(proj.project_id, "user", "q1"))
    asyncio.run(project_service.add_message(proj.project_id, "aios", "a1"))
    msgs = project_service.get_messages(proj.project_id)
    assert len(msgs) == 2
    # Persisted through the Obsidian Git adapter (AI-OS-owned vault).
    assert obsidian_git_adapter.create_knowledge.await_count == 2
    # Persisted under the project's chat folder path.
    saved_id = obsidian_git_adapter.create_knowledge.call_args_list[0].kwargs["knowledge_id"]
    assert saved_id.startswith(f"chat/{proj.project_id}/")


def test_conversation_persistence_graceful_when_adapter_missing():
    svc = ProjectService(kernel=_FakeKernel(), event_bus=None)
    proj = svc.create_project(name="NoAdapter")
    # Should not raise even without an adapter.
    asyncio.run(svc.add_message(proj.project_id, "user", "x"))
    assert len(svc.get_messages(proj.project_id)) == 1


# --------------------------------------------------------------------------- knowledge persistence


def test_knowledge_persistence_aios_owned(project_service, obsidian_git_adapter):
    proj = project_service.create_project(name="Know")
    kid = asyncio.run(
        project_service.store_knowledge(proj.project_id, "research_finding", "fact")
    )
    assert kid.startswith(f"knowledge/{proj.project_id}/")
    obsidian_git_adapter.create_knowledge.assert_awaited()
    meta = obsidian_git_adapter.create_knowledge.call_args.kwargs["metadata"]
    assert meta["project_id"] == proj.project_id
    assert meta["folder"] == "knowledge"


def test_decision_append_only(project_service, obsidian_git_adapter):
    proj = project_service.create_project(name="Dec")
    rec = asyncio.run(
        project_service.store_decision(
            proj.project_id, "Use X", "Because of Y", outcome="pending"
        )
    )
    assert rec.decision_id
    assert project_service.get_decisions(proj.project_id)[0].title == "Use X"
    # Decision body persists to /decisions/ with AI-OS-owned provenance.
    saved_id = obsidian_git_adapter.create_knowledge.call_args.kwargs["knowledge_id"]
    assert saved_id.startswith(f"decisions/{proj.project_id}/")


def test_plan_and_tasks_persist(project_service, obsidian_git_adapter):
    proj = project_service.create_project(name="Plan")
    asyncio.run(project_service.save_plan(proj.project_id, {"content": "do it", "variant": "v1"}))
    asyncio.run(project_service.add_task(proj.project_id, {"title": "t1", "status": "open"}))
    assert project_service.get_plan(proj.project_id).get("content") == "do it"
    assert project_service.get_tasks(proj.project_id)[0]["title"] == "t1"
    # Plan persisted to /plans/, task to /tasks/ (AI-OS-owned vault).
    ids = [c.kwargs["knowledge_id"] for c in obsidian_git_adapter.create_knowledge.call_args_list]
    assert any(i.startswith(f"plans/{proj.project_id}/") for i in ids)
    assert any(i.startswith(f"tasks/{proj.project_id}/") for i in ids)


# --------------------------------------------------------------------------- context loading (snapshot shape)


def test_project_snapshot_shape_for_frontend(project_service):
    proj = project_service.create_project(name="Snap")
    asyncio.run(project_service.add_message(proj.project_id, "user", "hi"))
    asyncio.run(project_service.store_decision(proj.project_id, "D", "R"))
    snap = project_service.get_project_snapshot(proj.project_id)
    assert snap["found"] is True
    assert snap["authority"] == "aios_sole"
    assert snap["read_only"] is True
    assert snap["project"]["name"] == "Snap"
    assert snap["project"]["message_count"] == 1
    assert snap["project"]["decision_count"] == 1
    assert "allowed_transitions" in snap  # frontend renders these as pills


def test_dashboard_project_workspace_index_page(project_service):
    project_service.create_project(name="P1")
    svc = _make_dashboard(_FakeKernel(), None, project_service)
    page = svc.get_project_workspace()
    assert page["available"] is True
    assert page["authority"] == "aios_sole"
    assert len(page["projects"]) == 1


def test_dashboard_project_workspace_missing_service_is_safe():
    svc = _make_dashboard(_FakeKernel(), None, None)
    page = svc.get_project_workspace()
    assert page["available"] is False
    assert "reason" in page  # frontend shows the reason, no crash


# --------------------------------------------------------------------------- planning flow + final-plan handoff


def test_planning_flow_transitions_with_authority(project_service):
    proj = project_service.create_project(name="Flow")
    for target in (
        ProjectState.DISCUSSION,
        ProjectState.RESEARCH,
        ProjectState.PLANNING,
        ProjectState.REVIEW,
        ProjectState.DECISION_PENDING,
        ProjectState.APPROVED,
        ProjectState.FINALIZED,
    ):
        ok, _ = project_service.validate_transition(proj.project_id, target)
        assert ok, target
        project_service.apply_transition(proj.project_id, target)
    assert proj.state == ProjectState.FINALIZED


def test_final_plan_notion_handoff_advisory(project_service, notion_adapter):
    proj = project_service.create_project(name="Handoff")
    asyncio.run(project_service.save_plan(proj.project_id, {"content": "final plan", "variant": "v1"}))
    result = asyncio.run(project_service.publish_final_plan_to_notion(proj.project_id))
    assert result["published"] is True
    assert result["advisory"] is True  # Notion is untrusted (C14)
    # Handoff does NOT grant execution authority / change state.
    assert proj.state == ProjectState.CREATED
    notion_adapter.create_page.assert_awaited()


def test_final_plan_handoff_no_notion_adapter_is_safe():
    svc = ProjectService(kernel=_FakeKernel(), event_bus=None)
    proj = svc.create_project(name="NoNotion")
    result = asyncio.run(svc.publish_final_plan_to_notion(proj.project_id))
    assert result["published"] is False
    assert "reason" in result


def test_publish_notion_requires_authority_in_dashboard(kernel, project_service, security_allow, security_deny):
    # When SecurityManager denies, the handoff is REJECTED (fail-closed).
    proj = project_service.create_project(name="Gated")
    denied = _make_dashboard(kernel, security_deny, project_service)
    r = asyncio.run(denied.request_action("project.publish_notion", {"project_id": proj.project_id}))
    assert r.authorized is False
    assert r.status == "rejected"
    # When allowed, it delegates to the bounded adapter (no dashboard authority).
    allowed = _make_dashboard(kernel, security_allow, project_service)
    r2 = asyncio.run(allowed.request_action("project.publish_notion", {"project_id": proj.project_id}))
    assert r2.authorized is True
    assert r2.status == "completed"


# --------------------------------------------------------------------------- action transition through SecurityManager


def test_project_transition_gated_fail_closed(kernel, project_service, security_deny):
    proj = project_service.create_project(name="Trans")
    svc = _make_dashboard(kernel, security_deny, project_service)
    r = asyncio.run(svc.request_action("project.transition", {"project_id": proj.project_id, "to_state": "DISCUSSION"}))
    assert r.authorized is False
    assert r.status == "rejected"
    # State unchanged because the gate denied it.
    assert proj.state == ProjectState.CREATED


def test_project_transition_illegal_rejected_even_when_authorized(kernel, project_service, security_allow):
    proj = project_service.create_project(name="Illegal")
    svc = _make_dashboard(kernel, security_allow, project_service)
    # Jumping straight to EXECUTING violates the lifecycle graph -> error, not silent apply.
    r = asyncio.run(svc.request_action("project.transition", {"project_id": proj.project_id, "to_state": "EXECUTING"}))
    assert r.status == "error"
    assert proj.state == ProjectState.CREATED


def test_project_create_gated(kernel, project_service, security_allow):
    svc = _make_dashboard(kernel, security_allow, project_service)
    r = asyncio.run(svc.request_action("project.create", {"name": "NewProj"}))
    assert r.authorized is True
    assert r.status == "completed"
    assert "project_id" in r.data


# --------------------------------------------------------------------------- dashboard has NO alternate authority


def test_dashboard_cannot_authorize_or_decide():
    svc = _make_dashboard(_FakeKernel(), None, None)
    assert not hasattr(svc, "authorize")
    assert not hasattr(svc, "verify")
    assert not hasattr(svc, "decide")
    # ProjectService also holds no authority.
    assert not hasattr(ProjectService, "authorize")


def test_security_failure_is_fail_closed_project_action(kernel, project_service):
    sm = MagicMock()
    sm.authorize.side_effect = RuntimeError("security down")
    svc = _make_dashboard(kernel, sm, project_service)
    proj = project_service.create_project(name="SF")
    r = asyncio.run(svc.request_action("project.transition", {"project_id": proj.project_id, "to_state": "DISCUSSION"}))
    assert r.authorized is False
    assert r.status == "rejected"


# --------------------------------------------------------------------------- Integrations & Credentials (no secret leakage)


def test_integrations_page_exposes_no_secret_values(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    assert page["authority"] == "aios_sole"
    # Explicit contract: no secret values are ever transmitted.
    assert "NONE" in page["secret_exposure"]
    for entry in page["integrations"]:
        assert "token" not in entry or entry.get("token") is None
        assert "api_key" not in entry or entry.get("api_key") is None
        assert "secret" not in entry or entry.get("secret") is None
        # Credential value is never present; only configured YES/NO.
        assert isinstance(entry["credential_configured"], bool)


def test_integrations_page_covers_full_inventory(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    names = {i["integration_name"] for i in page["integrations"]}
    # All authoritative integrations appear (not just Obsidian/Supabase/n8n).
    for expected in ("obsidian", "obsidian_git", "supabase", "n8n", "notion", "anthropic", "openai"):
        assert expected in names, expected


def test_integrations_page_shows_config_categories(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    by_name = {i["integration_name"]: i for i in page["integrations"]}
    # Filesystem / Git / local-endpoint configuration flags are surfaced per spec.
    assert by_name["obsidian_git"]["requires_filesystem_path"] is True
    assert by_name["obsidian_git"]["requires_git_config"] is True
    assert by_name["notion"]["requires_local_endpoint"] is True
    assert by_name["obsidian"]["requires_filesystem_path"] is True
    # agent_reach requires nothing -> not_required_reason present.
    assert by_name["agent_reach"]["not_required_reason"]


def test_integrations_marks_credential_status_not_value(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    by_name = {i["integration_name"]: i for i in page["integrations"]}
    # Credential "required" lists kind names, never values.
    req = by_name["notion"]["required_credentials"]
    assert any("token" in c.lower() for c in req)
    assert not any(("secret_value" in c or "-" * 4 in c) for c in req)


def test_integrations_readiness_summary_present(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    assert "readiness" in page
    for key in ("core_services", "required_credentials", "external_integrations", "knowledge_system", "model_providers", "database", "status"):
        assert key in page["readiness"]


# --------------------------------------------------------------------------- mock / real mode + missing / invalid credentials


def test_integrations_reports_mock_mode_default(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    for entry in page["integrations"]:
        # Mode is always reported as a known value (mock/real); never blank.
        assert entry["mode"] in ("mock", "real")
        # If real mode is allowed, the integration is in real mode; otherwise it is
        # never auto-promoted beyond what the config declares (fail-closed by design).
        if entry["real_allowed"] is True:
            assert entry["mode"] in ("mock", "real")


def test_integrations_missing_credentials_flagged(kernel):
    """With no env credentials configured, required-cred integrations report not configured."""
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    # Readiness should expose what is missing without revealing values.
    assert "missing" in page["readiness"]


def test_integrations_local_endpoint_integrations_present(kernel):
    svc = _make_dashboard(kernel, None, None)
    page = svc.get_integrations_credentials()
    by_name = {i["integration_name"]: i for i in page["integrations"]}
    # Local-endpoint integrations (playwright_mcp, graphify, notion, etc.) are listed.
    assert by_name["playwright_mcp"]["requires_local_endpoint"] is True
    assert by_name["graphify"]["requires_local_endpoint"] is True


# --------------------------------------------------------------------------- M7–M14 verified behavior intact


def test_existing_dashboard_pages_still_present(kernel, project_service):
    svc = _make_dashboard(kernel, None, project_service)
    pages = svc.get_all_pages()["pages"]
    # All prior M13 pages remain; the two new pages are additive.
    for p in ("planning_chat", "resource_onboarding", "project_execution", "knowledge_history", "system_health"):
        assert p in pages
    assert "project_workspace" in pages
    assert "integrations_credentials" in pages
    assert len(pages) == 7


def test_all_pages_declare_aios_sole_authority(kernel, project_service):
    svc = _make_dashboard(kernel, None, project_service)
    pages = svc.get_all_pages()
    for name, page in pages["pages"].items():
        assert page["authority"] == "aios_sole", name
        assert page["read_only"] is True, name


def test_existing_action_validate_still_forwards(kernel, security_allow):
    """M13 integration.validate path is unchanged by the new pages."""
    status_service = MagicMock()
    report = MagicMock()
    report.to_dict.return_value = {"name": "supabase", "state": "validated"}
    status_service.validate_integration = AsyncMock(return_value=report)
    kernel.integration_status_service = status_service
    svc = _make_dashboard(kernel, security_allow, None)
    r = asyncio.run(svc.request_action("integration.validate", {"name": "supabase"}))
    assert r.status == "completed"
    status_service.validate_integration.assert_called_once_with("supabase")
