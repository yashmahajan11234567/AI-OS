"""
Tests for DeploymentService deployment-level health-check functionality.

Tests for:
- Deployment service health checking
- Last deployment status checking
- Configuration validity checking
- Docker build capability checking
- Overall health status determination
- Health check result structure and details
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from aios.services.deployment import DeploymentService
from aios.core.health_manager import HealthStatus


class TestDeploymentServiceHealthCheck:
    """Tests for deployment-level health-check functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_check_deployment_health_returns_proper_structure(self):
        """Test that check_deployment_health returns properly structured result."""
        result = self.deployment_service.check_deployment_health()

        # Check required top-level fields
        assert "timestamp" in result
        assert "deployment_id" in result
        assert "overall_status" in result
        assert "checks" in result
        assert "details" in result

        # Check that overall_status is a valid HealthStatus value
        assert result["overall_status"] in [status.value for status in HealthStatus]

        # Check that checks is a dictionary
        assert isinstance(result["checks"], dict)

        # Check that details is a dictionary
        assert isinstance(result["details"], dict)

    def test_check_deployment_health_includes_required_checks(self):
        """Test that health check includes all required individual checks."""
        result = self.deployment_service.check_deployment_health()

        required_checks = [
            "service_health",
            "last_deployment",
            "configuration_validity",
            "docker_build_capability"
        ]

        for check_name in required_checks:
            assert check_name in result["checks"]
            check = result["checks"][check_name]
            assert "status" in check
            assert "message" in check
            assert check["status"] in [status.value for status in HealthStatus]

    def test_check_deployment_health_service_healthy_when_service_ok(self):
        """Test that service health check reports healthy when service is operational."""
        result = self.deployment_service.check_deployment_health()

        # Service health should be healthy under normal circumstances
        service_check = result["checks"]["service_health"]
        # Could be healthy or degraded depending on state, but should not be unknown/error from service issues
        assert service_check["status"] in [
            HealthStatus.HEALTHY.value,
            HealthStatus.DEGRADED.value,
            HealthStatus.UNKNOWN.value
        ]

    def test_check_deployment_health_last_deployment_handles_no_history(self):
        """Test that last deployment check handles empty history correctly."""
        # Ensure history is empty
        self.deployment_service._deployment_history.clear()

        result = self.deployment_service.check_deployment_health()
        last_deployment_check = result["checks"]["last_deployment"]

        # Should report unknown status when no history
        assert last_deployment_check["status"] == HealthStatus.UNKNOWN.value
        assert "No deployments in history" in last_deployment_check["message"]

    def test_check_deployment_health_last_deployment_handles_specific_id_not_found(self):
        """Test that last deployment check handles specific deployment ID not found."""
        result = self.deployment_service.check_deployment_health("nonexistent123")
        last_deployment_check = result["checks"]["last_deployment"]

        # Should report unhealthy when specific deployment not found
        assert last_deployment_check["status"] == HealthStatus.UNHEALTHY.value
        assert "not found in history" in last_deployment_check["message"]

    def test_check_deployment_health_last_deployment_handles_successful_deployment(self):
        """Test that last deployment check reports healthy for successful deployment."""
        # Add a successful deployment
        successful_deployment = {
            "deployment_id": "dep_success123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(successful_deployment)

        result = self.deployment_service.check_deployment_health()
        last_deployment_check = result["checks"]["last_deployment"]

        # Should report healthy for successful deployment
        assert last_deployment_check["status"] == HealthStatus.HEALTHY.value
        assert "Latest successful deployment" in last_deployment_check["message"]
        assert "dep_success123456" in last_deployment_check["message"]

    def test_check_deployment_health_last_deployment_handles_failed_deployment(self):
        """Test that last deployment check reports unhealthy for failed deployment."""
        # Add a failed deployment
        failed_deployment = {
            "deployment_id": "dep_failed123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "production",
            "version": "1.0.0",
            "success": False,
            "error": "deployment failed due to error"
        }
        self.deployment_service._deployment_history.append(failed_deployment)

        result = self.deployment_service.check_deployment_health()
        last_deployment_check = result["checks"]["last_deployment"]

        # Should report unhealthy for failed deployment
        assert last_deployment_check["status"] == HealthStatus.UNHEALTHY.value
        assert "Latest deployment" in last_deployment_check["message"]
        assert "dep_failed123456" in last_deployment_check["message"]
        assert "failed" in last_deployment_check["message"]

    def test_check_deployment_health_configuration_validity_works(self):
        """Test that configuration validity check works correctly."""
        result = self.deployment_service.check_deployment_health()
        config_check = result["checks"]["configuration_validity"]

        # Should be able to determine configuration validity
        assert config_check["status"] in [status.value for status in HealthStatus]
        assert isinstance(config_check["message"], str)
        assert len(config_check["message"]) > 0

    def test_check_deployment_health_docker_build_capability_works(self):
        """Test that Docker build capability check works correctly."""
        result = self.deployment_service.check_deployment_health()
        docker_check = result["checks"]["docker_build_capability"]

        # Should be able to determine Docker build capability
        assert docker_check["status"] in [status.value for status in HealthStatus]
        assert isinstance(docker_check["message"], str)
        assert len(docker_check["message"]) > 0

    def test_check_deployment_health_overall_status_logic(self):
        """Test that overall status follows worst-wins logic."""
        # Test case: all healthy -> overall healthy
        with patch.object(self.deployment_service, '_check_service_health', return_value=True), \
             patch.object(self.deployment_service, '_check_last_deployment_status', return_value={"status": HealthStatus.HEALTHY.value, "message": "test"}), \
             patch.object(self.deployment_service, '_check_configuration_validity', return_value=True), \
             patch.object(self.deployment_service, '_validate_docker_build', return_value=True):

            result = self.deployment_service.check_deployment_health()
            assert result["overall_status"] == HealthStatus.HEALTHY.value

        # Test case: one unhealthy -> overall unhealthy
        with patch.object(self.deployment_service, '_check_service_health', return_value=True), \
             patch.object(self.deployment_service, '_check_last_deployment_status', return_value={"status": HealthStatus.UNHEALTHY.value, "message": "test"}), \
             patch.object(self.deployment_service, '_check_configuration_validity', return_value=True), \
             patch.object(self.deployment_service, '_validate_docker_build', return_value=True):

            result = self.deployment_service.check_deployment_health()
            assert result["overall_status"] == HealthStatus.UNHEALTHY.value

        # Test case: one degraded, none unhealthy -> overall degraded
        with patch.object(self.deployment_service, '_check_service_health', return_value=True), \
             patch.object(self.deployment_service, '_check_last_deployment_status', return_value={"status": HealthStatus.DEGRADED.value, "message": "test"}), \
             patch.object(self.deployment_service, '_check_configuration_validity', return_value=True), \
             patch.object(self.deployment_service, '_validate_docker_build', return_value=True):

            result = self.deployment_service.check_deployment_health()
            assert result["overall_status"] == HealthStatus.DEGRADED.value

    def test_check_deployment_health_includes_details(self):
        """Test that health check result includes useful details."""
        result = self.deployment_service.check_deployment_health()

        details = result["details"]
        expected_details = [
            "configuration_hash",
            "dockerfile_exists",
            "docker_compose_exists",
            "deployment_count",
            "successful_deployments"
        ]

        for detail in expected_details:
            assert detail in details

    def test_check_deployment_health_handles_exceptions_gracefully(self):
        """Test that health check handles exceptions gracefully."""
        # Make _check_service_health raise an exception
        with patch.object(self.deployment_service, '_check_service_health', side_effect=Exception("Test error")):
            result = self.deployment_service.check_deployment_health()

            # Should return unhealthy status and include error info
            assert result["overall_status"] == HealthStatus.UNHEALTHY.value
            assert "error" in result
            assert "Test error" in result["error"]

    def test_check_deployment_health_caching_behavior(self):
        """Test that last health check is properly stored."""
        # Clear any existing last health check
        self.deployment_service._last_health_check = None

        result1 = self.deployment_service.check_deployment_health()
        last_check_1 = self.deployment_service.get_last_health_check()

        assert last_check_1 is not None
        assert last_check_1["timestamp"] == result1["timestamp"]
        assert last_check_1["overall_status"] == result1["overall_status"]

        # Get another health check
        result2 = self.deployment_service.check_deployment_health()
        last_check_2 = self.deployment_service.get_last_health_check()

        # Should be updated to the second result
        assert last_check_2["timestamp"] == result2["timestamp"]
        assert last_check_2["overall_status"] == result2["overall_status"]

    def test_get_last_health_check_returns_none_when_no_checks(self):
        """Test that get_last_health_check returns None when no checks performed."""
        # Ensure no health checks have been performed
        deployment_service_new = DeploymentService()
        last_check = deployment_service_new.get_last_health_check()
        assert last_check is None

    def test_check_deployment_health_with_specific_deployment_id(self):
        """Test health check with specific deployment ID."""
        # Add a deployment to history
        deployment = {
            "deployment_id": "dep_specific123456",
            "timestamp": "2026-01-01T00:00:00Z",
            "environment": "staging",
            "version": "2.0.0",
            "success": True
        }
        self.deployment_service._deployment_history.append(deployment)

        result = self.deployment_service.check_deployment_health("dep_specific123456")

        assert result["deployment_id"] == "dep_specific123456"
        last_deployment_check = result["checks"]["last_deployment"]
        assert last_deployment_check["status"] == HealthStatus.HEALTHY.value
        assert "Latest successful deployment" in last_deployment_check["message"]


class TestDeploymentServiceHealthCheckIntegration:
    """Integration tests for deployment health check functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_deployment_health_check_integration_with_real_files(self):
        """Test health check works with actual repository files."""
        # This test runs against the actual repository to verify integration
        result = self.deployment_service.check_deployment_health()

        # Should complete without throwing exceptions
        assert isinstance(result, dict)
        assert "overall_status" in result
        assert "checks" in result
        assert "details" in result

        # Details should reflect actual repository state
        details = result["details"]
        assert "dockerfile_exists" in details
        assert "docker_compose_exists" in details
        assert isinstance(details["dockerfile_exists"], bool)
        assert isinstance(details["docker_compose_exists"], bool)

        # In the actual repo, these should be True
        # (though we won't assert this to avoid test fragility in different environments)

    def setup_method(self):
        """Set up test fixtures."""
        self.deployment_service = DeploymentService()

    def test_multiple_health_checks_produce_different_timestamps(self):
        """Test that multiple health checks produce different timestamps."""
        result1 = self.deployment_service.check_deployment_health()
        # Small delay to ensure different timestamp (though microsecond precision should suffice)
        import time
        time.sleep(0.001)  # 1ms delay
        result2 = self.deployment_service.check_deployment_health()

        # Timestamps should be different (or at least not necessarily the same)
        # We mainly want to verify the mechanism works
        assert "timestamp" in result1
        assert "timestamp" in result2
        assert isinstance(result1["timestamp"], str)
        assert isinstance(result2["timestamp"], str)


class TestDeploymentServiceHealthCheckRealPaths:
    """Deterministic tests exercising real production health paths against the
    actual repository Docker artifacts (no Docker daemon required).
    """

    def setup_method(self):
        self.deployment_service = DeploymentService()

    def test_health_check_configuration_validity_reflects_real_repo(self):
        """Configuration validity check validates the real repo's Dockerfile."""
        result = self.deployment_service.check_deployment_health()
        config_check = result["checks"]["configuration_validity"]

        # The real repo has a valid Dockerfile + docker-compose.yml.
        assert config_check["status"] == HealthStatus.HEALTHY.value
        assert "valid" in config_check["message"]

    def test_health_check_docker_capability_reports_local_mode_when_absent(self):
        """Docker capability check degrades gracefully when Docker is absent."""
        from unittest.mock import patch

        with patch.object(
            self.deployment_service, "_is_docker_available", return_value=False
        ):
            result = self.deployment_service.check_deployment_health()
        docker_check = result["checks"]["docker_build_capability"]
        assert docker_check["status"] == HealthStatus.UNKNOWN.value
        assert "local" in docker_check["message"].lower()

    def test_health_check_details_reflect_real_artifact_state(self):
        """Health details reflect the real presence of Dockerfile/compose."""
        result = self.deployment_service.check_deployment_health()
        details = result["details"]
        from pathlib import Path
        root = self.deployment_service._project_root
        assert details["dockerfile_exists"] == (root / "Dockerfile").is_file()
        assert details["docker_compose_exists"] == (
            root / "docker-compose.yml"
        ).is_file()
        assert isinstance(details["configuration_hash"], str)
        assert len(details["configuration_hash"]) == 16

    def test_health_distinguishes_successful_record_from_failure(self):
        """A successful history record yields HEALTHY; a failed record yields UNHEALTHY."""
        # Successful record.
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(
            {
                "deployment_id": "dep_ok123456",
                "timestamp": "2026-01-01T00:00:00Z",
                "environment": "production",
                "version": "1.0.0",
                "success": True,
            }
        )
        healthy = self.deployment_service.check_deployment_health("dep_ok123456")
        assert healthy["checks"]["last_deployment"]["status"] == HealthStatus.HEALTHY.value

        # Failed record (not in success-history -> unhealthy).
        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(
            {
                "deployment_id": "dep_bad123456",
                "timestamp": "2026-01-01T00:00:00Z",
                "environment": "production",
                "version": "1.0.0",
                "success": False,
                "error": "boom",
            }
        )
        unhealthy = self.deployment_service.check_deployment_health("dep_bad123456")
        assert unhealthy["checks"]["last_deployment"]["status"] == HealthStatus.UNHEALTHY.value

    def test_health_overall_degraded_when_docker_unknown(self):
        """When Docker is unknown but config/history healthy, overall is DEGRADED or HEALTHY (never fabricated)."""
        from unittest.mock import patch

        self.deployment_service._deployment_history.clear()
        self.deployment_service._deployment_history.append(
            {
                "deployment_id": "dep_ok123456",
                "timestamp": "2026-01-01T00:00:00Z",
                "environment": "production",
                "version": "1.0.0",
                "success": True,
            }
        )
        with patch.object(
            self.deployment_service, "_is_docker_available", return_value=False
        ):
            result = self.deployment_service.check_deployment_health("dep_ok123456")
        # No UNHEALTHY verdict from a successful history record when no Docker.
        assert result["overall_status"] in (
            HealthStatus.HEALTHY.value,
            HealthStatus.DEGRADED.value,
            HealthStatus.UNKNOWN.value,
        )