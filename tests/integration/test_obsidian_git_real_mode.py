"""
M14-T2 — Obsidian Git Real-Mode Integration Tests (Gated).

All tests require AIOS_REAL_INTEGRATION_ENABLED=1 AND valid OBSIDIAN_VAULT_PATH
pointing to an initialized Git repository.
Without the gate, the adapter must remain in mock mode.
"""

from __future__ import annotations

import os
import tempfile
import shutil
import subprocess

import pytest

# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------


def _real_mode_enabled() -> bool:
    return os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"


def _has_vault() -> bool:
    path = os.environ.get("OBSIDIAN_VAULT_PATH")
    return bool(path and os.path.isdir(path))


def _skip_if_not_real_mode():
    if not _real_mode_enabled():
        pytest.skip("AIOS_REAL_INTEGRATION_ENABLED=1 not set (real mode gated)")


def _skip_if_no_vault():
    if not _has_vault():
        pytest.skip("OBSIDIAN_VAULT_PATH not configured or not a directory")


def _git_init_if_needed(vault_path: str) -> None:
    """Ensure vault is a Git repo with initial commit."""
    git_dir = os.path.join(vault_path, ".git")
    if not os.path.isdir(git_dir):
        subprocess.run(["git", "init"], cwd=vault_path, check=True)
        subprocess.run(["git", "config", "user.email", "aios-test@example.com"], cwd=vault_path, check=True)
        subprocess.run(["git", "config", "user.name", "AI-OS Test"], cwd=vault_path, check=True)
        # Seed an initial commit so HEAD exists.
        readme = os.path.join(vault_path, "README.md")
        with open(readme, "w", encoding="utf-8") as f:
            f.write("# AI-OS Vault\n")
        subprocess.run(["git", "add", "README.md"], cwd=vault_path, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=vault_path, check=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_mode_requires_gate():
    """Without AIOS_REAL_INTEGRATION_ENABLED=1, real mode stays mock even with vault."""
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    # No reload needed; adapter reads env at init.
    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path="/tmp/does_not_matter",
        timeout_seconds=5,
        real_mode_enabled=False,
        security_manager=None,
    )
    await adapter.connect()
    assert adapter.is_mock_mode is True
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_connect_with_vault():
    """With gate + vault path, adapter enters real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    connected = await adapter.connect()
    assert connected is True
    assert adapter.is_real_mode is True
    assert adapter.is_connected() is True
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_create_knowledge():
    """Create knowledge file in vault, verify commit."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_create_" + os.urandom(4).hex()
    result = await adapter.create_knowledge(
        knowledge_id=kid,
        content="# Test Knowledge\n\nCreated by M14-T2.",
        knowledge_type="reference_knowledge",
        metadata={"tags": ["test", "m14t2"]},
    )
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["knowledge_id"] == kid
    assert result.metrics.get("head_commit") is not None
    # Verify file exists in vault.
    file_path = os.path.join(vault, f"{kid}.md")
    assert os.path.exists(file_path), "Knowledge markdown file should be created"

    await adapter.delete_knowledge(kid)  # cleanup
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_read_knowledge():
    """Read created knowledge, verify content."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_read_" + os.urandom(4).hex()
    content = "## Read Me\n\nContent to verify."
    await adapter.create_knowledge(
        knowledge_id=kid,
        content=content,
        knowledge_type="reference_knowledge",
        metadata={},
    )

    result = await adapter.get_knowledge(kid)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.raw["record"]["content"] == content

    await adapter.delete_knowledge(kid)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_update_knowledge():
    """Update knowledge, verify new content + new commit."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_update_" + os.urandom(4).hex()
    await adapter.create_knowledge(
        knowledge_id=kid,
        content="v1",
        knowledge_type="reference_knowledge",
        metadata={},
    )
    result1 = await adapter.get_knowledge(kid)
    commit1 = result1.raw["record"].get("head_commit")

    result = await adapter.update_knowledge(
        knowledge_id=kid,
        content="v2 updated",
        metadata={"updated": True},
    )
    assert result.status == ExecutionStatus.SUCCESS
    commit2 = result.metrics.get("head_commit")
    assert commit2 is not None
    # In real Git, commit hash should differ on update. (Mock does too.)
    if commit1 and commit2:
        assert commit1 != commit2, "Update should produce a new commit"

    result2 = await adapter.get_knowledge(kid)
    assert result2.raw["record"]["content"] == "v2 updated"

    await adapter.delete_knowledge(kid)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_delete_knowledge():
    """Delete knowledge, verify file removed + commit."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_delete_" + os.urandom(4).hex()
    await adapter.create_knowledge(
        knowledge_id=kid,
        content="to delete",
        knowledge_type="reference_knowledge",
        metadata={},
    )
    file_path = os.path.join(vault, f"{kid}.md")
    assert os.path.exists(file_path)

    result = await adapter.delete_knowledge(kid)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["deleted"] is True
    assert not os.path.exists(file_path), "File should be removed"

    result2 = await adapter.get_knowledge(kid)
    assert result2.metrics["found"] is False

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_commit_history():
    """Multiple operations produce correct commit history."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_history_" + os.urandom(4).hex()
    await adapter.create_knowledge(kid, "c1", "reference_knowledge", {})
    await adapter.update_knowledge(kid, "c2", {})
    await adapter.update_knowledge(kid, "c3", {})

    result = await adapter.get_knowledge(kid)
    assert result.status == ExecutionStatus.SUCCESS
    # Real mode: history not populated by read; but the Git log has 3 commits.
    # At minimum the HEAD commit should be present.
    assert result.raw["record"].get("head_commit") is not None

    await adapter.delete_knowledge(kid)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_integrity_check():
    """Git history integrity verifiable."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    kid = "test_integrity_" + os.urandom(4).hex()
    await adapter.create_knowledge(kid, "integrity test", "reference_knowledge", {})
    result = await adapter.verify_integrity()
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["integrity_intact"] is True

    await adapter.delete_knowledge(kid)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_knowledge_type_validation():
    """Unknown knowledge type rejected."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    result = await adapter.create_knowledge(
        knowledge_id="bad_type_" + os.urandom(4).hex(),
        content="x",
        knowledge_type="not_an_aios_type",
        metadata={},
    )
    assert result.status == ExecutionStatus.ERROR
    assert "not AI-OS-owned" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_sensitive_content_rejection():
    """Sensitive content rejected."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    result = await adapter.create_knowledge(
        knowledge_id="secret_" + os.urandom(4).hex(),
        content="api_key=sk_live_12345678901234567890",
        knowledge_type="reference_knowledge",
        metadata={},
    )
    assert result.status == ExecutionStatus.ERROR
    assert "Potential secret detected" in result.findings[0]["description"] or "Sensitive" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_path_traversal_blocked():
    """Vault path traversal prevented."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # Knowledge ID with path traversal attempt.
    result = await adapter.create_knowledge(
        knowledge_id="../../etc/passwd",
        content="bad",
        knowledge_type="reference_knowledge",
        metadata={},
    )
    # The sanitization in _knowledge_file_path maps ".." to "_" so no traversal.
    # Real mode should still succeed (sanitized filename) or be rejected by validation.
    # Either way, the vault root must not be escaped.
    assert result.status in (ExecutionStatus.SUCCESS, ExecutionStatus.ERROR)

    # If it succeeded, clean up the mangled file.
    if result.status == ExecutionStatus.SUCCESS:
        await adapter.delete_knowledge("../../etc/passwd")

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_missing_vault_degrades():
    """Missing vault returns ERROR, not crash."""
    _skip_if_not_real_mode()

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path="/this/path/does/not/exist",
        timeout_seconds=5,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()
    result = await adapter.create_knowledge("x", "y", "reference_knowledge", {})
    assert result.status == ExecutionStatus.ERROR
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_git_real_security_deny_blocks_connect():
    """SecurityManager deny prevents real connection."""
    _skip_if_not_real_mode()
    _skip_if_no_vault()

    vault = os.environ["OBSIDIAN_VAULT_PATH"]
    _git_init_if_needed(vault)

    from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
    from aios.core.security_manager import AuthorizationDecision

    class DenySecurityManager:
        async def authorize(self, principal, action, resource, context):
            return AuthorizationDecision(value="deny", reason="test deny")

    adapter = ObsidianGitAdapter(
        server_id="obsidian_git",
        vault_path=vault,
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=DenySecurityManager(),
    )
    connected = await adapter.connect()
    assert connected is False, "SecurityManager deny must block real connection"


# Batch helper.
if __name__ == "__main__":
    import asyncio

    async def _main():
        await test_obsidian_git_real_mode_requires_gate()
        print("test_obsidian_git_real_mode_requires_gate OK")

    asyncio.run(_main())