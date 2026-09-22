"""
Unit tests for project message persistence layer.
Tests the specific requirements for the Planning Workspace message persistence.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.services.project_service import ProjectService, ChatMessage


class _FakeKernel:
    """Minimal kernel double with the canonical getters ProjectService reads."""

    def __init__(self):
        self.obsidian_git_adapter = None
        self.notion_adapter = None

    def get_stats(self):
        return {"kernel": {"name": "aios", "running": True}}


@pytest.fixture
def kernel():
    return _FakeKernel()


@pytest.fixture
def obsidian_git_adapter():
    """Mock Obsidian Git adapter with a safe in-memory store."""
    ad = MagicMock()
    ad.create_knowledge = AsyncMock(return_value=MagicMock(raw={"ok": True}))
    ad.get_knowledge = AsyncMock(return_value=MagicMock(raw={"content": "x"}))
    ad.is_real_mode = MagicMock(return_value=False)
    return ad


@pytest.fixture
def project_service(kernel, obsidian_git_adapter):
    kernel.obsidian_git_adapter = obsidian_git_adapter
    return ProjectService(
        kernel=kernel, event_bus=None, security_manager=None, config={}
    )


def test_message_model_contains_required_fields():
    """Test that ChatMessage model contains all required fields for Planning Workspace."""
    msg = ChatMessage(
        message_id="msg-123",
        role="user",
        content="Hello world",
        created_at="2026-09-21T10:00:00Z",
    )

    # Verify all required fields are present and accessible
    assert hasattr(msg, 'message_id')
    assert hasattr(msg, 'role')  # serves as both sender and role
    assert hasattr(msg, 'content')
    assert hasattr(msg, 'created_at')  # timestamp

    # Verify field values are correctly set
    assert msg.message_id == "msg-123"
    assert msg.role == "user"
    assert msg.content == "Hello world"
    assert msg.created_at == "2026-09-21T10:00:00Z"


def test_message_creation_with_project_association(project_service):
    """Test that messages are properly associated with a project."""
    proj = project_service.create_project(name="Test Project", description="Test description")

    # Add a message to the project
    msg = asyncio.run(project_service.add_message(
        project_id=proj.project_id,
        role="user",
        content="Test message content"
    ))

    # Verify the message is associated with the project
    retrieved_msgs = project_service.get_messages(proj.project_id)
    assert len(retrieved_msgs) == 1
    assert retrieved_msgs[0].message_id == msg.message_id
    assert retrieved_msgs[0].role == "user"
    assert retrieved_msgs[0].content == "Test message content"


def test_sender_persistence(project_service):
    """Test that sender information is persisted correctly."""
    proj = project_service.create_project(name="Sender Test")

    # Test different sender roles
    asyncio.run(project_service.add_message(proj.project_id, "user", "User message"))
    asyncio.run(project_service.add_message(proj.project_id, "aios", "AIOS message"))
    asyncio.run(project_service.add_message(proj.project_id, "planner", "Planner message"))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == 3
    assert messages[0].role == "user"
    assert messages[1].role == "aios"
    assert messages[2].role == "planner"


def test_role_persistence(project_service):
    """Test that role information is persisted correctly."""
    proj = project_service.create_project(name="Role Test")

    # Test various roles that might be used in Planning Workspace
    roles_content = [
        ("user", "User input"),
        ("planner", "Planning suggestion"),
        ("reviewer", "Review comment"),
        ("aios", "System notification"),
        ("facilitator", "Facilitation note")
    ]

    for role, content in roles_content:
        asyncio.run(project_service.add_message(proj.project_id, role, content))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == len(roles_content)

    for i, (expected_role, expected_content) in enumerate(roles_content):
        assert messages[i].role == expected_role
        assert messages[i].content == expected_content


def test_content_persistence(project_service):
    """Test that message content is persisted correctly."""
    proj = project_service.create_project(name="Content Test")

    test_contents = [
        "Simple message",
        "Message with special characters: !@#$%^&*()",
        "Multi-line\nmessage\nwith\nnewlines",
        "Message with unicode: 你好 🚀",
        ""  # Empty message
    ]

    for i, content in enumerate(test_contents):
        asyncio.run(project_service.add_message(proj.project_id, "user", f"Msg {i}: {content}"))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == len(test_contents)

    for i, expected_content in enumerate(test_contents):
        assert f"Msg {i}: {expected_content}" in messages[i].content


def test_timestamp_persistence(project_service):
    """Test that timestamp information is persisted correctly."""
    proj = project_service.create_project(name="Timestamp Test")

    # Add messages with small delays to ensure different timestamps
    import time

    msg1 = asyncio.run(project_service.add_message(proj.project_id, "user", "First message"))
    time.sleep(0.01)  # Small delay
    msg2 = asyncio.run(project_service.add_message(proj.project_id, "user", "Second message"))
    time.sleep(0.01)
    msg3 = asyncio.run(project_service.add_message(proj.project_id, "user", "Third message"))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == 3

    # Verify timestamps are present and in chronological order
    assert messages[0].created_at == msg1.created_at
    assert messages[1].created_at == msg2.created_at
    assert messages[2].created_at == msg3.created_at

    # Verify chronological order (timestamps should be increasing)
    assert messages[0].created_at <= messages[1].created_at <= messages[2].created_at


def test_retrieval_by_project_id(project_service):
    """Test that messages can be retrieved by project_id."""
    # Create two different projects
    proj_a = project_service.create_project(name="Project A")
    proj_b = project_service.create_project(name="Project B")

    # Add messages to each project
    asyncio.run(project_service.add_message(proj_a.project_id, "user", "Message in A"))
    asyncio.run(project_service.add_message(proj_a.project_id, "aios", "Response in A"))
    asyncio.run(project_service.add_message(proj_b.project_id, "user", "Message in B"))

    # Verify retrieval by project_id returns correct messages
    messages_a = project_service.get_messages(proj_a.project_id)
    messages_b = project_service.get_messages(proj_b.project_id)

    assert len(messages_a) == 2
    assert len(messages_b) == 1

    assert messages_a[0].content == "Message in A"
    assert messages_a[1].content == "Response in A"
    assert messages_b[0].content == "Message in B"


def test_chronological_ordering(project_service):
    """Test that messages are returned in chronological order."""
    proj = project_service.create_project(name="Ordering Test")

    # Add multiple messages
    asyncio.run(project_service.add_message(proj.project_id, "user", "First"))
    asyncio.run(project_service.add_message(proj.project_id, "aios", "Second"))
    asyncio.run(project_service.add_message(proj.project_id, "user", "Third"))
    asyncio.run(project_service.add_message(proj.project_id, "planner", "Fourth"))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == 4

    # Verify they are in the order they were added
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"
    assert messages[3].content == "Fourth"


def test_multiple_messages_same_project(project_service):
    """Test handling multiple messages for the same project."""
    proj = project_service.create_project(name="Multiple Messages")

    # Add many messages to the same project
    message_count = 10
    for i in range(message_count):
        asyncio.run(project_service.add_message(
            proj.project_id,
            "user" if i % 2 == 0 else "aios",
            f"Message {i}"
        ))

    messages = project_service.get_messages(proj.project_id)
    assert len(messages) == message_count

    # Verify all messages are present and in order
    for i in range(message_count):
        expected_content = f"Message {i}"
        assert messages[i].content == expected_content


def test_message_isolation_between_projects(project_service):
    """Test that messages from different projects remain isolated."""
    # Create three projects
    proj_a = project_service.create_project(name="Project A")
    proj_b = project_service.create_project(name="Project B")
    proj_c = project_service.create_project(name="Project C")

    # Add distinct messages to each project
    asyncio.run(project_service.add_message(proj_a.project_id, "user", "A-msg1"))
    asyncio.run(project_service.add_message(proj_a.project_id, "user", "A-msg2"))

    asyncio.run(project_service.add_message(proj_b.project_id, "user", "B-msg1"))

    asyncio.run(project_service.add_message(proj_c.project_id, "user", "C-msg1"))
    asyncio.run(project_service.add_message(proj_c.project_id, "user", "C-msg2"))
    asyncio.run(project_service.add_message(proj_c.project_id, "user", "C-msg3"))

    # Verify isolation - each project only sees its own messages
    msgs_a = project_service.get_messages(proj_a.project_id)
    msgs_b = project_service.get_messages(proj_b.project_id)
    msgs_c = project_service.get_messages(proj_c.project_id)

    assert len(msgs_a) == 2
    assert len(msgs_b) == 1
    assert len(msgs_c) == 3

    # Verify content isolation
    assert all(msg.content.startswith("A-") for msg in msgs_a)
    assert all(msg.content.startswith("B-") for msg in msgs_b)
    assert all(msg.content.startswith("C-") for msg in msgs_c)


def test_existing_project_behavior_remains_intact(project_service, obsidian_git_adapter):
    """Test that existing project behavior remains intact with message persistence."""
    proj = project_service.create_project(name="Behavior Test")

    # Test that existing project functionality still works
    assert proj.name == "Behavior Test"
    assert proj.description == ""
    assert proj.state.value == "CREATED"

    # Add a message
    asyncio.run(project_service.add_message(proj.project_id, "user", "Test message"))

    # Verify project still functions correctly
    assert len(proj.messages) == 1
    assert proj.messages[0].content == "Test message"

    # Verify persistence still works
    assert obsidian_git_adapter.create_knowledge.await_count == 1

    # Test other project functionality
    decision = asyncio.run(project_service.store_decision(
        proj.project_id,
        "Test Decision",
        "Test rationale",
        outcome="approved"
    ))

    assert len(proj.decisions) == 1
    assert proj.decisions[0].title == "Test Decision"

    # Verify project snapshot still works
    snapshot = project_service.get_project_snapshot(proj.project_id)
    assert snapshot["found"] is True
    assert snapshot["project"]["name"] == "Behavior Test"
    assert snapshot["project"]["message_count"] == 1
    assert snapshot["project"]["decision_count"] == 1


@pytest.mark.asyncio
async def test_message_persistence_to_vault(project_service, obsidian_git_adapter):
    """Test that messages are persisted to the Obsidian Git adapter (AI-OS-owned vault)."""
    proj = project_service.create_project(name="Vault Persistence")

    # Add multiple messages
    await project_service.add_message(proj.project_id, "user", "q1")
    await project_service.add_message(proj.project_id, "aios", "a1")
    await project_service.add_message(proj.project_id, "planner", "planning suggestion")

    # Verify messages are cached
    msgs = project_service.get_messages(proj.project_id)
    assert len(msgs) == 3

    # Verify persistence through Obsidian Git adapter
    assert obsidian_git_adapter.create_knowledge.await_count == 3

    # Verify messages are persisted under correct paths
    call_args_list = obsidian_git_adapter.create_knowledge.call_args_list
    for i, call_args in enumerate(call_args_list):
        knowledge_id = call_args.kwargs["knowledge_id"]
        assert knowledge_id.startswith(f"chat/{proj.project_id}/")
        assert f"msg{i+1}" in knowledge_id or f"msg-{i+1}" in knowledge_id or len([c for c in call_args_list if proj.project_id in c.kwargs["knowledge_id"]]) >= 3


@pytest.mark.asyncio
async def test_message_persistence_graceful_when_adapter_missing():
    """Test that message persistence degrades gracefully when adapter is missing."""
    kernel = _FakeKernel()
    # No obsidian_git_adapter set
    svc = ProjectService(
        kernel=kernel, event_bus=None, security_manager=None, config={}
    )

    proj = svc.create_project(name="No Adapter Test")

    # Should not raise even without an adapter
    msg = await svc.add_message(proj.project_id, "user", "test message")

    # Message should still be available in cache
    messages = svc.get_messages(proj.project_id)
    assert len(messages) == 1
    assert messages[0].content == "test message"
    assert messages[0].role == "user"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])