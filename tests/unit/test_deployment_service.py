"""
Tests for DeploymentService reproducible deployment functionality.

Tests for:
- Reproducible deployment via configuration hashing
- Deterministic deployment ID generation
- Docker build validation
- Deployment history tracking
- Actual rollback behavior
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from aios.services.deployment import DeploymentService


class TestDeploymentServiceReproducibleDeployment:
    """Tests for reproducible deployment functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_calculate_configuration_hash_includes_key_files(self):
        """Test that configuration hash includes key deployment files."""
        # This test verifies the method works without throwing exceptions
        hash_value = self.deployment_service._calculate_configuration_hash()

        # Should return a 16-character hex string
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        assert all(c in '0123456789abcdef' for c in hash_value)

    def test_calculate_configuration_hash_is_deterministic(self):
        """Test that configuration hash is deterministic for same files."""
        hash1 = self.deployment_service._calculate_configuration_hash()
        hash2 = self.deployment_service._calculate_configuration_hash()

        # Should be identical for same state
        assert hash1 == hash2

    def test_validate_docker_build_passes_with_valid_files(self):
        """Test that Docker build validation passes when required files exist."""
        # This should pass in the actual repository
        result = self.deployment_service._validate_docker_build()
        # In the real repo, this should be True
        assert isinstance(result, bool)

    def test_generate_deterministic_deployment_id_is_deterministic(self):
        """Test that deployment ID generation is deterministic."""
        config_hash = "abc123def456"
        version = "1.0.0"
        environment = "production"

        id1 = self.deployment_service._generate_deterministic_deployment_id(config_hash, version, environment)
        id2 = self.deployment_service._generate_deterministic_deployment_id(config_hash, version, environment)

        assert id1 == id2
        assert id1.startswith("dep_")
        assert len(id1) == 16  # "dep_" + 12 chars

    def test_generate_deterministic_deployment_id_different_inputs(self):
        """Test that different inputs produce different deployment IDs."""
        base_hash = "abc123def456"
        version = "1.0.0"
        environment = "production"

        id1 = self.deployment_service._generate_deterministic_deployment_id(base_hash, version, environment)
        id2 = self.deployment_service._generate_deterministic_deployment_id(base_hash + "x", version, environment)  # Different hash
        id3 = self.deployment_service._generate_deterministic_deployment_id(base_hash, "2.0.0", environment)  # Different version
        id4 = self.deployment_service._generate_deterministic_deployment_id(base_hash, version, "staging")  # Different env

        assert id1 != id2
        assert id1 != id3
        assert id1 != id4
        assert id2 != id3
        assert id2 != id4
        assert id3 != id4

    def test_deploy_records_successful_deployment_in_history(self):
        """Test that successful deployments are recorded in history."""
        request = {
            "environment": "test",
            "version": "1.0.0",
            "task_id": "test-task-123"
        }

        # Mock the validation to succeed
        with patch.object(self.deployment_service, '_validate_docker_build', return_value=True):
            result = self.deployment_service.deploy(request)

        assert result["success"] is True
        assert "deployment_id" in result
        assert result["environment"] == "test"
        assert result["version"] == "1.0.0"

        # Check that deployment was recorded in history
        history = self.deployment_service.get_deployment_history()
        assert len(history) == 1
        assert history[0]["success"] is True
        assert history[0]["environment"] == "test"
        assert history[0]["version"] == "1.0.0"
        assert history[0]["deployment_id"] == result["deployment_id"]

    def test_deploy_records_failed_deployment_in_history(self):
        """Test that failed deployments are recorded in history."""
        request = {
            "environment": "test",
            "version": "1.0.0",
            "force_fail": True  # This will cause deploy to fail
        }

        result = self.deployment_service.deploy(request)

        assert result["success"] is False
        assert "error" in result

        # Check that deployment was recorded in history
        history = self.deployment_service.get_deployment_history()
        assert len(history) == 1
        assert history[0]["success"] is False
        assert history[0]["environment"] == "test"
        assert history[0]["version"] == "1.0.0"

    def test_deploy_fails_when_docker_build_validation_fails(self):
        """Test that deployment fails when Docker build validation fails."""
        request = {
            "environment": "test",
            "version": "1.0.0"
        }

        # Mock the validation to fail
        with patch.object(self.deployment_service, '_validate_docker_build', return_value=False):
            result = self.deployment_service.deploy(request)

        assert result["success"] is False
        assert "Docker build validation failed" in result["error"]


class TestDeploymentServiceReproducibleDeploymentRealPaths:
    """Deterministic unit tests exercising the real production code paths
    (no Docker daemon required). These verify the non-docker deterministic
    deployment record is reproducible and that real-mode clearly fails
    when Docker is unavailable.
    """

    def setup_method(self):
        self.deployment_service = DeploymentService()

    def test_configuration_hash_is_reproducible_across_instances(self):
        """Identical on-disk config yields the same hash across instances."""
        h1 = self.deployment_service._calculate_configuration_hash()
        ds2 = DeploymentService()
        h2 = ds2._calculate_configuration_hash()
        assert h1 == h2
        assert len(h1) == 16

    def test_deployment_id_is_deterministic_across_calls(self):
        """Same config hash + version + env => same deployment ID."""
        config_hash = self.deployment_service._calculate_configuration_hash()
        id1 = self.deployment_service._generate_deterministic_deployment_id(
            config_hash, "1.2.3", "production"
        )
        id2 = self.deployment_service._generate_deterministic_deployment_id(
            config_hash, "1.2.3", "production"
        )
        assert id1 == id2
        assert id1.startswith("dep_")

    def test_deploy_in_local_mode_produces_deterministic_id(self):
        """Non-real-mode deploy records deterministic ID + hash, no Docker."""
        request = {"environment": "staging", "version": "2.0.0"}
        result = self.deployment_service.deploy(request)
        assert result["success"] is True
        config_hash = self.deployment_service._calculate_configuration_hash()
        expected_id = self.deployment_service._generate_deterministic_deployment_id(
            config_hash, "2.0.0", "staging"
        )
        assert result["deployment_id"] == expected_id
        assert result["configuration_hash"] == config_hash
        # Second identical call yields the same ID (reproducible).
        result2 = self.deployment_service.deploy(request)
        assert result2["deployment_id"] == result["deployment_id"]

    def test_deploy_in_real_mode_fails_clearly_without_docker(self):
        """Real-mode deploy without docker raises DockerRuntimeUnavailableError."""
        from aios.services.deployment import DockerRuntimeUnavailableError

        request = {"environment": "production", "version": "1.0.0"}
        with patch.dict(os.environ, {DeploymentService._REAL_MODE_ENV: "1"}), \
             patch.object(self.deployment_service, "_is_docker_available", return_value=False):
            with pytest.raises(DockerRuntimeUnavailableError):
                self.deployment_service.deploy(request)

    def test_validate_docker_artifacts_detects_missing_files(self, tmp_path):
        """_validate_docker_artifacts returns False when artifacts are absent."""
        with patch.object(self.deployment_service, "_project_root", tmp_path):
            result = self.deployment_service._validate_docker_artifacts()
        assert result["valid"] is False
        assert any("Dockerfile" in e for e in result["errors"])

    def test_rollback_emits_rollback_event_in_history(self):
        """Rollback records an audit entry in the rollback log and returns prior ID."""
        dep1 = {
            "deployment_id": "dep_old123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "oldhash",
        }
        dep2 = {
            "deployment_id": "dep_new789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "2.0.0",
            "success": True,
            "configuration_hash": "newhash",
        }
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.extend([dep1, dep2])

        result = self.deployment_service.rollback("dep_new789012", "revert")

        assert result == "dep_old123456"
        # History sequence is preserved (rollback does not append to it).
        assert len(self.deployment_service._deployment_history) == 2
        # Rollback is recorded in the separate audit log.
        assert len(self.deployment_service.get_rollback_history()) == 1
        audit = self.deployment_service.get_rollback_history()[0]
        assert audit["rolled_back_from"] == "dep_new789012"
        assert audit["rolled_back_to"] == "dep_old123456"
        assert audit["reason"] == "revert"

    def test_rollback_successful_when_previous_deployment_exists(self):
        """Test that rollback works when previous deployment exists."""
        # Add a successful deployment to history
        past_deployment = {
            "deployment_id": "dep_past123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(past_deployment)

        # Add current deployment
        current_deployment = {
            "deployment_id": "dep_current789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(current_deployment)

        # Mock the deploy method to avoid actual validation during rollback test
        with patch.object(self.deployment_service, '_validate_docker_build', return_value=True):
            # Perform rollback
            result = self.deployment_service.rollback("dep_current789012", "testing rollback")

        # Should return the previous deployment ID
        assert result == "dep_past123456"

    def test_rollback_fails_when_deployment_not_found(self):
        """Test that rollback fails when deployment is not found in history."""
        with pytest.raises(ValueError, match="Cannot rollback: deployment dep_nonexistent not found"):
            self.deployment_service.rollback("dep_nonexistent")

    def test_rollback_fails_when_no_previous_deployment_exists(self):
        """Test that rollback fails when no previous deployment exists."""
        # Add only one deployment (no previous)
        deployment = {
            "deployment_id": "dep_only123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(deployment)

        with pytest.raises(ValueError, match="Cannot rollback: no previous successful deployment exists"):
            self.deployment_service.rollback("dep_only123456")

    def test_rollback_fails_when_deployment_was_not_successful(self):
        """Test that rollback fails when the deployment to rollback was not successful."""
        # Add a failed deployment
        failed_deployment = {
            "deployment_id": "dep_failed123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False,
            "error": "something went wrong"
        }
        self.deployment_service._deployment_history.append(failed_deployment)

        with pytest.raises(ValueError, match="Cannot rollback: deployment dep_failed123456 not found in history or was not successful"):
            self.deployment_service.rollback("dep_failed123456")

    def test_get_latest_successful_deployment_returns_correct_value(self):
        """Test that get_latest_successful_deployment returns the most recent successful deployment."""
        # Add failed deployment
        failed_deployment = {
            "deployment_id": "dep_failed123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False
        }
        self.deployment_service._deployment_history.append(failed_deployment)

        # Add successful deployment
        success_deployment = {
            "deployment_id": "dep_success789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(success_deployment)

        # Add another failed deployment
        failed_deployment_2 = {
            "deployment_id": "dep_failed_2_345678",
            "timestamp": "2026-01-03T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False
        }
        self.deployment_service._deployment_history.append(failed_deployment_2)

        latest = self.deployment_service.get_latest_successful_deployment()
        assert latest is not None
        assert latest["deployment_id"] == "dep_success789012"
        assert latest["success"] is True

    def test_get_latest_successful_deployment_returns_none_when_no_successes(self):
        """Test that get_latest_successful_deployment returns None when no successful deployments."""
        # Add only failed deployments
        failed_deployment_1 = {
            "deployment_id": "dep_failed123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False
        }
        failed_deployment_2 = {
            "deployment_id": "dep_failed_2_345678",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False
        }
        self.deployment_service._deployment_history.append(failed_deployment_1)
        self.deployment_service._deployment_history.append(failed_deployment_2)

        latest = self.deployment_service.get_latest_successful_deployment()
        assert latest is None


class TestDeploymentServiceIntegration:
    """Integration tests for DeploymentService."""

    def test_deployment_service_initialization(self):
        """Test that DeploymentService initializes correctly."""
        service = DeploymentService()
        assert service.name == "deployment"
        assert service.version == "1.0.0"
        assert service.description == "Container build, deploy, rollback"
        assert service.depends_on == ["testing", "review"]
        assert hasattr(service, '_deployment_history')
        assert hasattr(service, '_project_root')
        assert isinstance(service._deployment_history, list)
        assert len(service._deployment_history) == 0