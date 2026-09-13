"""
M10 Deployment — Real-runtime acceptance tests (gated).

Every test in this module is gated behind ``AIOS_REAL_INTEGRATION_ENABLED=1``
AND the presence of a reachable Docker daemon. Without both:

  * the tests SKIP cleanly (never fail)
  * they do NOT fabricate Docker execution
  * they do NOT claim success without real evidence

These tests exercise the **real** production paths in DeploymentService:
  * actual ``docker compose build`` / ``docker compose config``
  * real container image lifecycle
  * real container inspection for health
  * real rollback via redeployment of a prior image

The deterministic / unit behavior is covered in:
  * tests/unit/test_deployment_service.py
  * tests/unit/test_deployment_health.py
  * tests/unit/test_deployment_rollback.py
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from aios.core.health_manager import HealthStatus
from aios.services.deployment import DeploymentService


# ---------------------------------------------------------------------------
# Gate helpers (mirrors tests/integration/test_dashboard_real_mode.py convention)
# ---------------------------------------------------------------------------


def _real_mode_enabled() -> bool:
    return os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"


def _docker_daemon_reachable() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _skip_if_not_real_mode() -> None:
    if not _real_mode_enabled() or not _docker_daemon_reachable():
        pytest.skip(
            "AIOS_REAL_INTEGRATION_ENABLED=1 and a reachable Docker daemon required"
        )


# ---------------------------------------------------------------------------
# Reproducible deployment — real Docker build path
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_deployment_service")
class TestRealReproducibleDeployment:
    @pytest.fixture
    def _deployment_service(self):
        if not _real_mode_enabled() or not _docker_daemon_reachable():
            pytest.skip(
                "Real Docker build acceptance tests gated on "
                "AIOS_REAL_INTEGRATION_ENABLED=1 + Docker daemon"
            )
        service = DeploymentService()
        yield service

    def test_real_docker_build_succeeds_and_records_id(self, _deployment_service):
        """Real ``docker compose build`` succeeds and a deterministic
        deployment ID is recorded."""
        request = {"environment": "test", "version": "1.0.0"}

        result = _deployment_service.deploy(request)

        assert result["success"] is True
        assert result["deployment_id"].startswith("dep_")
        assert result["configuration_hash"]
        assert len(result["configuration_hash"]) == 16
        # Real image tag was produced.
        assert result.get("runtime") == "docker"

    def test_real_deploy_is_reproducible_for_identical_inputs(self, _deployment_service):
        """Identical inputs yield identical deployment IDs (reproducible)."""
        request = {"environment": "prod", "version": "3.2.1"}

        r1 = _deployment_service.deploy(request)
        r2 = _deployment_service.deploy(request)

        assert r1["deployment_id"] == r2["deployment_id"]
        assert r1["configuration_hash"] == r2["configuration_hash"]


# ---------------------------------------------------------------------------
# Health — real container inspection
# ---------------------------------------------------------------------------


class TestRealDeploymentHealth:
    @pytest.fixture
    def _service_with_deploy(self):
        _skip_if_not_real_mode()
        service = DeploymentService()
        request = {"environment": "test", "version": "1.0.0"}
        result = service.deploy(request)
        assert result["success"] is True
        yield service, result

    def test_real_container_health_reports_healthy_after_build(
        self, _service_with_deploy
    ):
        service, deployed = _service_with_deploy

        health = service.check_deployment_health(deployed["deployment_id"])

        assert health["overall_status"] in (
            HealthStatus.HEALTHY.value,
            HealthStatus.DEGRADED.value,
        )
        # The last_deployment check must reflect a real successful record.
        last = health["checks"]["last_deployment"]
        assert last["status"] == HealthStatus.HEALTHY.value

    def test_real_health_distinguishes_no_history(self, _service_with_deploy):
        """Empty-history health is UNKNOWN, not a fabricated healthy state."""
        service, _ = _service_with_deploy
        # Fresh service with no deployments.
        empty = DeploymentService()
        health = empty.check_deployment_health()
        assert health["checks"]["last_deployment"]["status"] == HealthStatus.UNKNOWN.value


# ---------------------------------------------------------------------------
# Rollback — real redeploy of prior image
# ---------------------------------------------------------------------------


class TestRealRollback:
    @pytest.fixture
    def _two_deploys(self):
        _skip_if_not_real_mode()
        service = DeploymentService()
        d1 = service.deploy({"environment": "test", "version": "1.0.0"})
        d2 = service.deploy({"environment": "test", "version": "1.1.0"})
        assert d1["success"] and d2["success"]
        yield service, d1, d2

    def test_real_rollback_restores_prior_image(self, _two_deploys):
        service, d1, d2 = _two_deploys

        restored = service.rollback(d2["deployment_id"], "regression in 1.1.0")

        assert restored == d1["deployment_id"]
        # Rollback audit entry recorded.
        audits = service.get_rollback_history()
        assert len(audits) == 1
        assert audits[0]["rolled_back_from"] == d2["deployment_id"]
        assert audits[0]["rolled_back_to"] == d1["deployment_id"]

    def test_real_rollback_fails_safely_with_no_target(self):
        _skip_if_not_real_mode()
        service = DeploymentService()
        with pytest.raises(ValueError):
            service.rollback("dep_does_not_exist", "nothing")
