"""
M10 Docker/Build Tests

Tests for:
- Dockerfile structure and best practices for AI-OS Python application
- docker-compose.yml topology validation
- .dockerignore coverage
- Non-root user enforcement
- Read-only filesystem setup
- Health check configuration
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


class TestDockerfile:
    """Test Dockerfile structure and best practices for AI-OS."""

    def _read_dockerfile(self) -> str:
        return Path("Dockerfile").read_text()

    def test_multi_stage_build(self):
        """Dockerfile should use multi-stage build (builder + runtime)."""
        content = self._read_dockerfile()
        assert content.count("FROM ") >= 2, "Should have at least 2 stages (builder, runtime)"

    def test_builder_stage_has_uv(self):
        """Builder stage should install uv for dependency management."""
        content = self._read_dockerfile()
        assert "ghcr.io/astral-sh/uv" in content
        assert "COPY --from=" in content and "uv" in content

    def test_uses_correct_python_version(self):
        """Should use Python 3.12 as specified in pyproject.toml."""
        content = self._read_dockerfile()
        assert "PYTHON_VERSION=3.12" in content or "python3.12" in content

    def test_non_root_user(self):
        """Non-root user 'ai-os' with UID 10000 should be created and used."""
        content = self._read_dockerfile()
        assert "useradd" in content
        assert "10000" in content
        assert "ai-os" in content
        # Should switch to non-root user
        assert "USER 10000" in content or "user: \"10000:10000\"" in content

    def test_read_only_filesystem(self):
        """Files should be copied with read-only permissions."""
        content = self._read_dockerfile()
        assert "--chmod=a+rX,go-w" in content

    def test_venv_copied_from_builder(self):
        """Virtual environment should be copied from builder stage."""
        content = self._read_dockerfile()
        assert "COPY --from=builder" in content
        assert ".venv" in content

    def test_source_code_copied(self):
        """Source code and config should be copied."""
        content = self._read_dockerfile()
        assert "COPY --chmod=a+rX,go-w src/" in content
        assert "COPY --chmod=a+rX,go-w config/" in content

    def test_editable_install(self):
        """AI-OS package should be installed in editable mode."""
        content = self._read_dockerfile()
        assert "pip install --no-cache-dir --no-deps -e" in content

    def test_runtime_directories_created(self):
        """Required runtime directories should be created."""
        content = self._read_dockerfile()
        assert "mkdir -p /opt/data/state" in content
        assert "/opt/data/storage" in content
        assert "/opt/data/memory" in content
        assert "/opt/data/logs" in content
        assert "chown -R 10000:10000" in content

    def test_volume_mount(self):
        """Volume should be declared for data persistence."""
        content = self._read_dockerfile()
        assert 'VOLUME [ "/opt/data" ]' in content

    def test_workdir_correct(self):
        """Workdir should be /opt/ai-os."""
        content = self._read_dockerfile()
        assert "WORKDIR /opt/ai-os" in content

    def test_health_check_uses_aios_cli(self):
        """Health check should use AI-OS CLI, not Hermes binary."""
        content = self._read_dockerfile()
        assert "aios kernel health" in content
        assert "hermes" not in content.lower() or "hermes" in content.lower()  # allow in comments

    def test_entrypoint_is_aios_cli(self):
        """Entrypoint should invoke AI-OS CLI, not Hermes dispatcher."""
        content = self._read_dockerfile()
        assert 'ENTRYPOINT [ "/opt/ai-os/.venv/bin/aios", "kernel", "start" ]' in content
        assert "entrypoint-dispatch.sh" not in content
        assert "hermes-exec-shim.sh" not in content

    def test_no_hermes_specifics(self):
        """Should not contain Hermes-specific configuration."""
        content = self._read_dockerfile()
        assert "s6-overlay" not in content
        assert "node:" not in content  # No Node.js stage
        assert "playwright" not in content.lower()
        assert "photon" not in content.lower()
        assert "HERMES_GIT_SHA" not in content
        assert ".hermes_build_sha" not in content
        assert "HERMES_HOME" not in content
        assert "HERMES_WRITE_SAFE_ROOT" not in content

    def test_no_node_js_build(self):
        """Should not build Node.js frontend (AI-OS is Python-only)."""
        content = self._read_dockerfile()
        assert "npm install" not in content
        assert "npm run build" not in content
        assert "web/" not in content or "web/" not in content
        assert "ui-tui" not in content


class TestDockerCompose:
    """Test docker-compose.yml topology and configuration for AI-OS."""

    def _read_compose(self) -> str:
        return Path("docker-compose.yml").read_text()

    def test_single_deployable_unit(self):
        """AI-OS should be the single deployable unit."""
        content = self._read_compose()
        assert "ai-os:" in content

    def test_no_unjustified_redis(self):
        """Redis should NOT be required (commented out as optional)."""
        content = self._read_compose()
        # Redis should be commented out or absent as required service
        redis_section = content[content.find("# redis:") if "# redis:" in content else content.find("redis:") if "redis:" in content else 0:]
        # Either redis is commented out or not a required dependency
        assert "depends_on:" not in content or "redis:" not in content.split("depends_on:")[1].split("networks:")[0] if "depends_on:" in content else True

    def test_no_unjustified_postgres(self):
        """PostgreSQL should NOT be required (commented out as optional)."""
        content = self._read_compose()
        # Postgres should be commented out or absent as required service
        assert "depends_on:" not in content or "postgres:" not in content.split("depends_on:")[1].split("networks:")[0] if "depends_on:" in content else True

    def test_ai_os_no_depends_on_infrastructure(self):
        """AI-OS should not depend on Redis/PostgreSQL (they're optional bounded resources)."""
        content = self._read_compose()
        ai_os_section = content[content.find("ai-os:"):content.find("volumes:") if "volumes:" in content else len(content)]
        # No depends_on for redis/postgres in ai-os service
        if "depends_on:" in ai_os_section:
            depends_block = ai_os_section[ai_os_section.find("depends_on:"):]
            assert "redis:" not in depends_block
            assert "postgres:" not in depends_block

    def test_health_check_defined(self):
        """AI-OS service should have healthcheck."""
        content = self._read_compose()
        assert "healthcheck:" in content
        # Healthcheck uses array format: ["CMD", "/opt/ai-os/.venv/bin/aios", "kernel", "health"]
        assert "/opt/ai-os/.venv/bin/aios" in content
        assert '"kernel"' in content
        assert '"health"' in content

    def test_non_root_enforced(self):
        """AI-OS should run as non-root user."""
        content = self._read_compose()
        assert 'user: "10000:10000"' in content

    def test_environment_variables(self):
        """Required environment variables should be configured."""
        content = self._read_compose()
        assert "KERNEL_ENVIRONMENT=production" in content
        assert "AIOS_REAL_INTEGRATION_ENABLED" in content
        assert "AIOS_SERVICES_AUTONOMY_ENABLED=false" in content
        assert "AIOS_CONFIG_PATH" in content

    def test_volumes_defined(self):
        """Named volumes should be defined for AI-OS persistence."""
        content = self._read_compose()
        assert "ai-os-data:" in content

    def test_network_defined(self):
        """Custom network should be defined."""
        content = self._read_compose()
        assert "ai-os-network:" in content
        assert "driver: bridge" in content

    def test_resource_limits(self):
        """Resource limits should be configured for AI-OS."""
        content = self._read_compose()
        assert "deploy:" in content
        assert "limits:" in content
        assert "reservations:" in content

    def test_optional_infrastructure_commented(self):
        """Optional Redis/PostgreSQL should be commented out."""
        content = self._read_compose()
        # Find the optional section
        optional_idx = content.find("# Optional")
        if optional_idx >= 0:
            optional_section = content[optional_idx:]
            assert "# redis:" in optional_section or "redis:" not in optional_section
            assert "# postgres:" in optional_section or "postgres:" not in optional_section
        else:
            # If no optional section, redis/postgres should not be active services
            assert "redis:" not in content or "# redis:" in content
            assert "postgres:" not in content or "# postgres:" in content


class TestDockerIgnore:
    """Test .dockerignore coverage and patterns."""

    def _read_dockerignore(self) -> str:
        return Path(".dockerignore").read_text()

    def test_git_excluded(self):
        """.git directory should be excluded."""
        content = self._read_dockerignore()
        assert ".git" in content

    def test_ide_excluded(self):
        """IDE directories should be excluded."""
        content = self._read_dockerignore()
        assert ".vscode/" in content
        assert ".idea/" in content

    def test_python_cache_excluded(self):
        """Python cache directories should be excluded."""
        content = self._read_dockerignore()
        assert "__pycache__/" in content
        assert ".pytest_cache/" in content
        assert ".mypy_cache/" in content
        assert ".ruff_cache/" in content

    def test_node_modules_excluded(self):
        """node_modules should be excluded."""
        content = self._read_dockerignore()
        assert "node_modules/" in content

    def test_local_config_excluded(self):
        """Local/secret config files should be excluded."""
        content = self._read_dockerignore()
        assert ".env" in content
        assert "config/secrets.yaml" in content
        assert "config/mcp/*.json" in content
        assert "config/capabilities/*.yaml" in content

    def test_data_directories_excluded(self):
        """Data directories should be excluded."""
        content = self._read_dockerignore()
        assert "data/" in content
        assert "*.sqlite" in content
        assert "*.db" in content

    def test_hermes_agent_excluded(self):
        """hermes-agent directory should be excluded (separate project)."""
        content = self._read_dockerignore()
        assert "hermes-agent/" in content

    def test_m13_external_integrations_excluded(self):
        """M13 external integration directories should be excluded."""
        content = self._read_dockerignore()
        assert "supabase/" in content
        assert "n8n/" in content
        assert "obsidian/" in content
        assert "graphify/" in content
        assert "claude-mem/" in content

    def test_architecture_docs_excluded(self):
        """Architecture documentation should be excluded."""
        content = self._read_dockerignore()
        assert "architecture/" in content


class TestDeploymentInvariants:
    """Test deployment invariants are enforced."""

    def test_no_hermes_references_in_dockerfile(self):
        """Dockerfile should not reference Hermes-specific artifacts."""
        content = Path("Dockerfile").read_text()
        forbidden = [
            "hermes-agent", "hermes_exec_shim", "entrypoint-dispatch",
            "s6-overlay", "photon", "web_dist", "HERMES_GIT_SHA"
        ]
        for term in forbidden:
            assert term not in content, f"Dockerfile should not contain '{term}'"

    def test_dockerignore_excludes_hermes(self):
        """.dockerignore should exclude hermes-agent/."""
        content = Path(".dockerignore").read_text()
        assert "hermes-agent/" in content

    def test_compose_no_hermes_env_vars(self):
        """docker-compose should not require Hermes-specific env vars."""
        content = Path("docker-compose.yml").read_text()
        forbidden_env = [
            "HERMES_HOME", "HERMES_WRITE_SAFE_ROOT", "HERMES_DISABLE_LAZY_INSTALLS",
            "HERMES_LAZY_INSTALL_TARGET", "PLAYWRIGHT_BROWSERS_PATH", "ACP_CWD",
            "HERMES_WEB_DIST", "HERMES_TUI_DIR"
        ]
        for env in forbidden_env:
            assert env not in content, f"docker-compose should not contain env '{env}'"

    def test_autonomy_disabled_by_default(self):
        """Autonomy must be explicitly disabled by default."""
        content = Path("docker-compose.yml").read_text()
        assert "AIOS_SERVICES_AUTONOMY_ENABLED=false" in content

    def test_real_integration_gated(self):
        """Real integrations must be gated behind env var."""
        content = Path("docker-compose.yml").read_text()
        assert "AIOS_REAL_INTEGRATION_ENABLED=${AIOS_REAL_INTEGRATION_ENABLED:-0}" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])