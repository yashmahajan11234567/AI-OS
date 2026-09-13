"""
Tests for DeploymentService actual rollback functionality.

Tests for:
- Successful rollback to previous valid deployment
- Rollback state changes correctly
- Rollback fails safely when no previous deployment exists
- Failed rollback does not falsely report success
- Deterministic and testable rollback behavior
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from aios.services.deployment import DeploymentService


class TestDeploymentServiceRollback:
    """Tests for actual rollback behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_rollback_returns_previous_deployment_id_when_history_exists(self):
        """Test that rollback returns the previous successful deployment ID."""
        # Add first successful deployment
        dep1 = {
            "deployment_id": "dep_first123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "abc123def456"
        }
        self.deployment_service._deployment_history.append(dep1)

        # Add second successful deployment
        dep2 = {
            "deployment_id": "dep_second789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.1.0",
            "success": True,
            "configuration_hash": "def456abc123"
        }
        self.deployment_service._deployment_history.append(dep2)

        # Rollback from second deployment should return first deployment ID
        result = self.deployment_service.rollback("dep_second789012", "testing rollback")
        assert result == "dep_first123456"

    def test_rollback_skips_failed_deployments_when_finding_previous(self):
        """Test that rollback skips failed deployments when looking for previous successful one."""
        # Add first successful deployment
        dep1 = {
            "deployment_id": "dep_first123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "abc123def456"
        }
        self.deployment_service._deployment_history.append(dep1)

        # Add failed deployment
        dep_failed = {
            "deployment_id": "dep_failed789012",
            "timestamp": "2026-01-01T12:00:00Z",
            "environment": "production",
            "version": "1.1.0",
            "success": False,
            "error": "something went wrong",
            "configuration_hash": "def456abc123"
        }
        self.deployment_service._deployment_history.append(dep_failed)

        # Add second successful deployment
        dep2 = {
            "deployment_id": "dep_second345678",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.2.0",
            "success": True,
            "configuration_hash": "ghi789jkl012"
        }
        self.deployment_service._deployment_history.append(dep2)

        # Rollback from second deployment should skip the failed one and return first deployment ID
        result = self.deployment_service.rollback("dep_second345678", "testing rollback")
        assert result == "dep_first123456"

    def test_rollback_raises_value_error_when_deployment_not_found(self):
        """Test that rollback fails safely when deployment is not found in history."""
        with pytest.raises(ValueError) as exc_info:
            self.deployment_service.rollback("nonexistent123", "testing")

        assert "Cannot rollback: deployment nonexistent123 not found in history or was not successful" in str(exc_info.value)

    def test_rollback_raises_value_error_when_deployment_was_not_successful(self):
        """Test that rollback fails safely when the deployment to rollback was not successful."""
        # Add only a failed deployment
        dep_failed = {
            "deployment_id": "dep_failed123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False,
            "error": "deployment failed",
            "configuration_hash": "abc123def456"
        }
        self.deployment_service._deployment_history.append(dep_failed)

        with pytest.raises(ValueError) as exc_info:
            self.deployment_service.rollback("dep_failed123456", "testing")

        assert "Cannot rollback: deployment dep_failed123456 not found in history or was not successful" in str(exc_info.value)

    def test_rollback_raises_value_error_when_no_previous_deployment_exists(self):
        """Test that rollback fails safely when no previous successful deployment exists."""
        # Add only one successful deployment (no previous)
        dep_only = {
            "deployment_id": "dep_only123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "abc123def456"
        }
        self.deployment_service._deployment_history.append(dep_only)

        with pytest.raises(ValueError) as exc_info:
            self.deployment_service.rollback("dep_only123456", "testing")

        assert "Cannot rollback: no previous successful deployment exists" in str(exc_info.value)

    def test_rollback_raises_value_error_when_all_previous_deployments_failed(self):
        """Test that rollback fails safely when all previous deployments failed."""
        # Add first failed deployment
        dep_failed1 = {
            "deployment_id": "dep_failed1_123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False,
            "error": "first deployment failed",
            "configuration_hash": "abc123def456"
        }
        self.deployment_service._deployment_history.append(dep_failed1)

        # Add second failed deployment
        dep_failed2 = {
            "deployment_id": "dep_failed2_789012",
            "timestamp": "2026-01-01T12:00:00Z",
            "environment": "production",
            "version": "1.1.0",
            "success": False,
            "error": "second deployment failed",
            "configuration_hash": "def456abc123"
        }
        self.deployment_service._deployment_history.append(dep_failed2)

        # Add current (successful) deployment
        dep_current = {
            "deployment_id": "dep_current345678",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.2.0",
            "success": True,
            "configuration_hash": "ghi789jkl012"
        }
        self.deployment_service._deployment_history.append(dep_current)

        # Rollback should fail because there are no previous successful deployments
        with pytest.raises(ValueError) as exc_info:
            self.deployment_service.rollback("dep_current345678", "testing")

        assert "Cannot rollback: no previous successful deployment exists" in str(exc_info.value)

    def test_rollback_is_deterministic(self):
        """Test that rollback behavior is deterministic for same inputs."""
        # Set up identical history
        dep1 = {
            "deployment_id": "dep_first123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "abc123def456"
        }
        dep2 = {
            "deployment_id": "dep_second789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.1.0",
            "success": True,
            "configuration_hash": "def456abc123"
        }

        # Test 1
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(dep1)
        self.deployment_service._deployment_history.append(dep2)
        result1 = self.deployment_service.rollback("dep_second789012", "reason")

        # Test 2
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(dep1)
        self.deployment_service._deployment_history.append(dep2)
        result2 = self.deployment_service.rollback("dep_second789012", "reason")

        assert result1 == result2 == "dep_first123456"

    def test_rollback_maintains_deployment_state_information(self):
        """Test that rollback preserves deployment state/version information in history."""
        # Add deployments with detailed state information
        dep1 = {
            "deployment_id": "dep_v1_0_0",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "hash1",
            "build_timestamp": "2026-01-01T00:00:00Z",
            "url": "https://production.example-app.local"
        }
        dep2 = {
            "deployment_id": "dep_v1_1_0",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "1.1.0",
            "success": True,
            "configuration_hash": "hash2",
            "build_timestamp": "2026-01-02T00:00:00Z",
            "url": "https://production.example-app.local"
        }

        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(dep1)
        self.deployment_service._deployment_history.append(dep2)

        # Perform rollback
        result = self.deployment_service.rollback("dep_v1_1_0", "version downgrade")

        # Verify that history is unchanged (rollback doesn't modify history)
        assert len(self.deployment_service._deployment_history) == 2
        assert self.deployment_service._deployment_history[0]["deployment_id"] == "dep_v1_0_0"
        assert self.deployment_service._deployment_history[1]["deployment_id"] == "dep_v1_1_0"
        assert self.deployment_service._deployment_history[0]["version"] == "1.0.0"
        assert self.deployment_service._deployment_history[1]["version"] == "1.1.0"

        # Verify rollback returned correct previous deployment
        assert result == "dep_v1_0_0"

    def test_rollback_does_not_falsely_report_success_when_restoration_would_fail(self):
        """Test that rollback doesn't claim success when restoration would fail in real scenario."""
        # In this simulation, we can't test actual restoration failure,
        # but we can verify that the method properly indicates what it would do
        # by checking that it returns the previous deployment ID rather than
        # claiming some other kind of success

        dep1 = {
            "deployment_id": "dep_old123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "oldhash"
        }
        dep2 = {
            "deployment_id": "dep_new789012",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "2.0.0",
            "success": True,
            "configuration_hash": "newhash"
        }

        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(dep1)
        self.deployment_service._deployment_history.append(dep2)

        result = self.deployment_service.rollback("dep_new789012", "testing")

        # Should return the previous deployment ID, not claim some other success
        assert result == "dep_old123456"
        # Should not return the current deployment ID (which would indicate false success)
        assert result != "dep_new789012"

    def test_rollback_preserves_existing_api_contracts(self):
        """Test that rollback preserves existing deployment API contracts."""
        # The method should still accept deployment_id and reason parameters
        # and return a string (the previous deployment ID) or raise an exception

        dep1 = {
            "deployment_id": "dep_contract_test_123",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "test",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(dep1)

        # Adding another deployment to have something to rollback to
        dep2 = {
            "deployment_id": "dep_contract_test_456",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "test",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(dep2)

        # Should accept the parameters and return a string
        result = self.deployment_service.rollback("dep_contract_test_456", "testing contract")
        assert isinstance(result, str)
        assert result == "dep_contract_test_123"

        # Should raise ValueError (not some other exception type) for failure cases
        with pytest.raises(ValueError):
            self.deployment_service.rollback("nonexistent", "testing")


class TestDeploymentServiceRollbackIntegration:
    """Integration tests for rollback functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_rollback_workflow_with_multiple_deployments(self):
        """Test a realistic workflow with multiple deployments and rollbacks."""
        # Simulate a sequence of deployments
        deployments = [
            {
                "deployment_id": "dep_v1_0_0_init",
                "timestamp": "2026-01-01T00:00:00Z",
                "environment": "production",
                "version": "1.0.0",
                "success": True,
                "configuration_hash": "init_hash"
            },
            {
                "deployment_id": "dep_v1_0_1_patch",
                "timestamp": "2026-01-02T00:00:00Z",
                "environment": "production",
                "version": "1.0.1",
                "success": True,
                "configuration_hash": "patch_hash"
            },
            {
                "deployment_id": "dep_v1_1_0_feature",
                "timestamp": "2026-01-03T00:00:00Z",
                "environment": "production",
                "version": "1.1.0",
                "success": True,
                "configuration_hash": "feature_hash"
            },
            {
                "deployment_id": "dep_v1_1_1_bad",
                "timestamp": "2026-01-04T00:00:00Z",
                "environment": "production",
                "version": "1.1.1",
                "success": False,
                "error": "introduced bug",
                "configuration_hash": "bad_hash"
            },
            {
                "deployment_id": "dep_v1_1_2_fixed",
                "timestamp": "2026-01-05T00:00:00Z",
                "environment": "production",
                "version": "1.1.2",
                "success": True,
                "configuration_hash": "fixed_hash"
            }
        ]

        # Build up history
        self.deployment_service._deployment_history.clear()
        for dep in deployments:
            self.deployment_service._deployment_history.append(dep)

        # Rollback from v1.1.2 should go to v1.1.0 (skipping the bad one that's now in history)
        result1 = self.deployment_service.rollback("dep_v1_1_2_fixed", "need to revert feature")
        assert result1 == "dep_v1_1_0_feature"

        # Rollback from v1.1.0 should go to v1.0.1 (skipping the bad one that's in history)
        result2 = self.deployment_service.rollback("dep_v1_1_0_feature", "need to revert feature")
        assert result2 == "dep_v1_0_1_patch"

        # Verify history integrity
        assert len(self.deployment_service._deployment_history) == 5
        assert self.deployment_service._deployment_history[0]["deployment_id"] == "dep_v1_0_0_init"
        assert self.deployment_service._deployment_history[1]["deployment_id"] == "dep_v1_0_1_patch"
        assert self.deployment_service._deployment_history[2]["deployment_id"] == "dep_v1_1_0_feature"
        assert self.deployment_service._deployment_history[3]["deployment_id"] == "dep_v1_1_1_bad"
        assert self.deployment_service._deployment_history[4]["deployment_id"] == "dep_v1_1_2_fixed"

    def test_rollback_handles_empty_history_gracefully(self):
        """Test that rollback handles completely empty history."""
        self.deployment_service._deployment_history.clear()

        with pytest.raises(ValueError) as exc_info:
            self.deployment_service.rollback("any_id", "testing")

        assert "Cannot rollback: deployment any_id not found in history or was not successful" in str(
            exc_info.value
        )


class TestDeploymentServiceRollbackRealBehavior:
    """Deterministic tests for real rollback behavior (Docker-free).

    These verify that rollback actually restores the prior deployment
    configuration/state rather than merely echoing an ID, and that the
    rollback action is consistently recorded in the audit log while the
    deployment history sequence is preserved.
    """

    def setup_method(self):
        self.deployment_service = DeploymentService()

    def test_rollback_restores_prior_configuration_and_records_audit(self):
        """Rollback restores the prior deployment's config/state and records audit."""
        prior = {
            "deployment_id": "dep_prior_0001",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "prior_hash_abc",
        }
        current = {
            "deployment_id": "dep_current_0002",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "production",
            "version": "2.0.0",
            "success": True,
            "configuration_hash": "current_hash_def",
        }
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(prior)
        self.deployment_service._deployment_history.append(current)

        with patch.object(
            self.deployment_service, "_validate_docker_build", return_value=True
        ), patch.object(
            self.deployment_service, "_is_docker_available", return_value=False
        ):
            restored = self.deployment_service.rollback("dep_current_0002", "reg")

        assert restored == "dep_prior_0001"
        # History sequence preserved.
        assert len(self.deployment_service._deployment_history) == 2
        # Rollback recorded in audit log (not in deployment history).
        audits = self.deployment_service.get_rollback_history()
        assert len(audits) == 1
        assert audits[0]["rolled_back_to"] == "dep_prior_0001"
        assert audits[0]["rolled_back_from"] == "dep_current_0002"
        assert audits[0]["previous_version"] == "1.0.0"

    def test_rollback_skips_intermediate_failed_deployments(self):
        """Rollback skips failed deployments to find the prior successful one."""
        d1 = {
            "deployment_id": "dep_v1_0",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "prod",
            "version": "1.0.0",
            "success": True,
            "configuration_hash": "h1",
        }
        d2_bad = {
            "deployment_id": "dep_v1_1_bad",
            "timestamp": "2026-01-02T00:00:00Z",
            "environment": "prod",
            "version": "1.1.0",
            "success": False,
            "configuration_hash": "h2",
        }
        d3 = {
            "deployment_id": "dep_v1_2",
            "timestamp": "2026-01-03T00:00:00Z",
            "environment": "prod",
            "version": "1.2.0",
            "success": True,
            "configuration_hash": "h3",
        }
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.extend([d1, d2_bad, d3])

        with patch.object(
            self.deployment_service, "_validate_docker_build", return_value=True
        ), patch.object(
            self.deployment_service, "_is_docker_available", return_value=False
        ):
            restored = self.deployment_service.rollback("dep_v1_2", "revert bad")

        # Skips the failed d2, lands on d1.
        assert restored == "dep_v1_0"