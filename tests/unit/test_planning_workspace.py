"""
Focused tests for the Planning Workspace behavior.
Tests the specific requirements for the ChatGPT-style Planning Workspace implementation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.services.dashboard_service import DashboardService
from aios.services.project_service import ProjectService, ChatMessage


class _FakeKernel:
    """Minimal kernel double with the canonical getters DashboardService reads."""

    def __init__(self):
        self.obsidian_git_adapter = None
        self.notion_adapter = None
        self.self_loop_engine = None
        self.self_prompt_generator = None
        self.project_service = None
        self.integration_status_service = None
        self.terminal_contract_violations = []

    def get_stats(self):
        return {"kernel": {"name": "aios", "running": True}}

    def get_planning_chat(self):
        return {"test": "data"}

    def get_resource_onboarding(self):
        return {"test": "data"}

    def get_project_execution(self):
        return {"test": "data"}

    def get_knowledge_history(self):
        return {"test": "data"}

    def get_system_health(self):
        return {"test": "data"}

    def get_system_observability(self):
        return {"test": "data"}


@pytest.fixture
def kernel():
    return _FakeKernel()


@pytest.fixture
def project_service(kernel):
    svc = ProjectService(
        kernel=kernel, event_bus=None, security_manager=None, config={}
    )
    kernel.project_service = svc
    return svc


@pytest.fixture
def obsidian_git_adapter():
    """Mock Obsidian Git adapter with a safe in-memory store."""
    ad = MagicMock()
    ad.create_knowledge = AsyncMock(return_value=MagicMock(raw={"ok": True}))
    ad.get_knowledge = AsyncMock(return_value=MagicMock(raw={"content": "x"}))
    ad.is_real_mode = MagicMock(return_value=False)
    return ad


@pytest.fixture
def dashboard_service(kernel, project_service, obsidian_git_adapter):
    kernel.obsidian_git_adapter = obsidian_git_adapter
    kernel.project_service = project_service
    return DashboardService(
        kernel=kernel, event_bus=None, security_manager=None, config={}
    )


def test_planning_chat_without_project_id_returns_basic_data(dashboard_service):
    """Test that get_planning_chat() without project_id returns basic self-loop data."""
    # Setup mock kernel responses
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": True,
        "paused": False,
        "mock_mode": True,
        "cycle_count": 5
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = None
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 10,
        "max_depth": 3,
        "convergence_action": "continue"
    }

    result = dashboard_service.get_planning_chat()

    # Verify basic structure is preserved
    assert result["page"] == "planning_chat"
    assert result["authority"] == "aios_sole"
    assert result["read_only"] is True
    assert "self_loop" in result
    assert "generator_config" in result
    assert "phase_map" in result
    assert "last_self_prompt" in result

    # Verify new fields are present but empty when no project_id
    assert "project_context" in result
    assert "messages" in result
    assert result["project_context"] == {}
    assert result["messages"] == []


def test_planning_chat_with_project_id_includes_context_and_messages(
    dashboard_service, project_service, obsidian_git_adapter
):
    """Test that get_planning_chat(project_id) includes project context and message history."""
    # Setup project and add messages
    proj = project_service.create_project(
        name="Test Project",
        description="A test project for planning workspace"
    )

    # Add some messages
    asyncio.run(project_service.add_message(
        proj.project_id, "user", "Hello AI-OS"
    ))
    asyncio.run(project_service.add_message(
        proj.project_id, "aios", "Hello user! How can I help with your planning?"
    ))

    # Setup kernel mocks for self-loop data
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": True,
        "paused": False,
        "mock_mode": True,
        "cycle_count": 3
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = None
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 10,
        "max_depth": 3,
        "convergence_action": "continue"
    }

    # Call get_planning_chat with project_id
    result = dashboard_service.get_planning_chat(proj.project_id)

    # Verify basic structure is preserved
    assert result["page"] == "planning_chat"
    assert result["authority"] == "aios_sole"
    assert result["read_only"] is True
    assert "self_loop" in result
    assert "generator_config" in result
    assert "phase_map" in result
    assert "last_self_prompt" in result

    # Verify project context is included
    assert result["project_context"]["project_id"] == proj.project_id
    assert result["project_context"]["name"] == "Test Project"
    assert result["project_context"]["state"] == "CREATED"
    assert result["project_context"]["message_count"] == 2

    # Verify message history is included
    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "user"
    assert result["messages"][0]["content"] == "Hello AI-OS"
    assert result["messages"][1]["role"] == "aios"
    assert result["messages"][1]["content"] == "Hello user! How can I help with your planning?"

    # Verify messages are in chronological order
    assert result["messages"][0]["created_at"] <= result["messages"][1]["created_at"]


def test_planning_chat_handles_nonexistent_project_gracefully(dashboard_service):
    """Test that get_planning_chat() handles nonexistent project gracefully."""
    # Setup kernel mocks for self-loop data
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": True,
        "paused": False,
        "mock_mode": True,
        "cycle_count": 1
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = None
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 5,
        "max_depth": 2,
        "convergence_action": "summarize"
    }

    # Call with nonexistent project ID
    result = dashboard_service.get_planning_chat("nonexistent-project-id")

    # Should still return basic data but with empty project context
    assert result["page"] == "planning_chat"
    assert result["authority"] == "aios_sole"
    assert result["read_only"] is True
    assert result["project_context"] == {}
    assert result["messages"] == []


def test_planning_chat_preserves_existing_self_loop_data_when_project_selected(
    dashboard_service, project_service
):
    """Test that selecting a project doesn't lose self-loop data."""
    # Setup project
    proj = project_service.create_project(name="Test Project")

    # Setup kernel mocks with specific self-loop data
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": False,
        "paused": True,
        "mock_mode": False,
        "cycle_count": 42
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = MagicMock()
    dashboard_service._kernel.self_loop_engine._current_cycle.phase_results = {
        "initialization": MagicMock(success=True),
        "validation": MagicMock(success=False)
    }
    dashboard_service._kernel.self_loop_engine.PHASE_ORDER = [
        "initialization",
        "validation",
        "execution"
    ]
    # Mock the _last_self_prompt properly to match _serialize_self_prompt expectations
    mock_directive = MagicMock()
    mock_directive.action_type = "analyze"
    mock_directive.target_systems = ["supabase"]
    mock_metadata = MagicMock()
    mock_metadata.validation_status = "pending"
    mock_last_prompt = MagicMock()
    mock_last_prompt.directive = mock_directive
    mock_last_prompt.metadata = mock_metadata
    dashboard_service._kernel.self_loop_engine._last_self_prompt = mock_last_prompt
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 100,
        "max_depth": 10,
        "convergence_action": "optimize"
    }

    # Get planning chat with project
    result = dashboard_service.get_planning_chat(proj.project_id)

    # Verify self-loop data is preserved
    assert result["self_loop"]["running"] is False
    assert result["self_loop"]["paused"] is True
    assert result["self_loop"]["mock_mode"] is False
    assert result["self_loop"]["cycle_count"] == 42

    # Verify phase map is correct
    assert len(result["phase_map"]) == 3
    assert result["phase_map"][0]["phase"] == "initialization"
    assert result["phase_map"][0]["completed"] is True
    assert result["phase_map"][0]["success"] is True
    assert result["phase_map"][1]["phase"] == "validation"
    assert result["phase_map"][1]["completed"] is True
    assert result["phase_map"][1]["success"] is False
    assert result["phase_map"][2]["phase"] == "execution"
    assert result["phase_map"][2]["completed"] is False

    # Verify last self-prompt is preserved (matches _serialize_self_prompt output)
    assert result["last_self_prompt"]["action_type"] == "analyze"
    assert result["last_self_prompt"]["target_systems"] == ["supabase"]
    assert result["last_self_prompt"]["validation_status"] == "pending"

    # Verify generator config is preserved
    assert result["generator_config"]["max_cycles"] == 100
    assert result["generator_config"]["max_depth"] == 10
    assert result["generator_config"]["convergence_action"] == "optimize"

    # Verify project context is also present
    assert result["project_context"]["name"] == "Test Project"
    assert len(result["messages"]) == 0  # No messages added yet


def test_multiple_projects_maintain_isolation_in_planning_chat(
    dashboard_service, project_service
):
    """Test that multiple projects maintain isolation in planning chat view."""
    # Create two projects
    proj_a = project_service.create_project(name="Project Alpha")
    proj_b = project_service.create_project(name="Project Beta")

    # Add distinct messages to each project
    asyncio.run(project_service.add_message(
        proj_a.project_id, "user", "Alpha message 1"
    ))
    asyncio.run(project_service.add_message(
        proj_a.project_id, "aios", "Alpha response 1"
    ))

    asyncio.run(project_service.add_message(
        proj_b.project_id, "user", "Beta message 1"
    ))
    asyncio.run(project_service.add_message(
        proj_b.project_id, "user", "Beta message 2"
    ))
    asyncio.run(project_service.add_message(
        proj_b.project_id, "aios", "Beta response 1"
    ))

    # Setup kernel mocks
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": True,
        "paused": False,
        "mock_mode": True,
        "cycle_count": 1
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = None
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 5,
        "max_depth": 2,
        "convergence_action": "continue"
    }

    # Get planning chat for project A
    result_a = dashboard_service.get_planning_chat(proj_a.project_id)

    # Get planning chat for project B
    result_b = dashboard_service.get_planning_chat(proj_b.project_id)

    # Verify project A context and messages
    assert result_a["project_context"]["name"] == "Project Alpha"
    assert result_a["project_context"]["message_count"] == 2
    assert len(result_a["messages"]) == 2
    assert result_a["messages"][0]["content"] == "Alpha message 1"
    assert result_a["messages"][1]["content"] == "Alpha response 1"

    # Verify project B context and messages
    assert result_b["project_context"]["name"] == "Project Beta"
    assert result_b["project_context"]["message_count"] == 3
    assert len(result_b["messages"]) == 3
    assert result_b["messages"][0]["content"] == "Beta message 1"
    assert result_b["messages"][1]["content"] == "Beta message 2"
    assert result_b["messages"][2]["content"] == "Beta response 1"

    # Verify isolation - no cross-contamination
    alpha_messages = [msg["content"] for msg in result_a["messages"]]
    beta_messages = [msg["content"] for msg in result_b["messages"]]

    assert all("Alpha" in msg for msg in alpha_messages)
    assert all("Beta" in msg for msg in beta_messages)
    assert not any("Beta" in msg for msg in alpha_messages)
    assert not any("Alpha" in msg for msg in beta_messages)


def test_empty_project_shows_appropriate_state(dashboard_service, project_service):
    """Test that projects with no messages show appropriate empty state."""
    proj = project_service.create_project(name="Empty Project")

    # Setup kernel mocks
    dashboard_service._kernel.self_loop_engine = MagicMock()
    dashboard_service._kernel.self_loop_engine.get_status.return_value = {
        "running": True,
        "paused": False,
        "mock_mode": True,
        "cycle_count": 0
    }
    dashboard_service._kernel.self_loop_engine._current_cycle = None
    dashboard_service._kernel.self_prompt_generator = MagicMock()
    dashboard_service._kernel.self_prompt_generator.get_config.return_value = {
        "max_cycles": 10,
        "max_depth": 3,
        "convergence_action": "continue"
    }

    result = dashboard_service.get_planning_chat(proj.project_id)

    # Verify project context is correct
    assert result["project_context"]["name"] == "Empty Project"
    assert result["project_context"]["message_count"] == 0

    # Verify messages array is empty
    assert result["messages"] == []
    assert len(result["messages"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])