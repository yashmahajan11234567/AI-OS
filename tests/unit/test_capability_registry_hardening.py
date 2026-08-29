"""
M8-T5 — Capability Registry Hardening unit tests.

Tests for CapabilityManager extended registry functionality:
- register_capability(spec) populates extended fields
- disable() → state=DISABLED, enabled=False, entry retained; resolve() raises when disabled (CM-DIS-001)
- enable() reverses disable
- deprecate() → state=DEPRECATED, still resolvable but flagged
- set_health() updates health_status; availability transitions
- enforce_security_context() rejects operation not in allowed_operations (CM-SEC-001)
- enforce_security_context() rejects payload containing sensitive_keys (CM-SEC-002)
- enforce_security_context() rejects oversized payload (CM-SEC-003)
- duplicate id, same trust + equal version → reject (CM-DUP-001 / CM-PREC-001)
- duplicate id, external untrusted vs built-in trusted → external rejected (CM-SHADOW-001)
- equal trust, higher version → wins; unparseable version → first wins
- initialize_capability() instantiates adapter via factory; failure → availability=error, registry intact
- deregister() still → REMOVED (unchanged)
- existing register()/deregister()/resolve()/invoke() behavior unchanged (regression guards)
"""

from __future__ import annotations

import pytest

from aios.core.capability_manager import (
    CapabilityAvailability,
    CapabilityManager,
    CapabilityManagerError,
    CapabilityRegistryEntry,
    CapabilityState,
    TrustLevel,
    AuthorityClassification,
)
from aios.core.capability_manifest import CapabilitySpec
from aios.core.configuration_manager import (
    ConfigurationManager,
    reset_configuration_manager_singleton,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.structured_logger import get_logger
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton


@pytest.fixture
def bus():
    """A canonical EventBus singleton."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def sr(bus):
    """A canonical ServiceRegistry wired to the bus."""
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=bus)
    yield reg
    reset_service_registry_singleton()


@pytest.fixture
def cm(bus):
    """A canonical ConfigurationManager (empty/frozen)."""
    reset_configuration_manager_singleton()
    c = ConfigurationManager(event_bus=bus)
    yield c
    reset_configuration_manager_singleton()


@pytest.fixture
def logger(bus):
    """A canonical StructuredLogger."""
    return get_logger()


@pytest.fixture
def cmgr(bus, sr, cm, logger):
    """A CapabilityManager wired to real canonical C1–C4, uninitialized."""
    from aios.core.capability_manager import reset_capability_manager_singleton

    reset_capability_manager_singleton()
    mgr = CapabilityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    yield mgr
    reset_capability_manager_singleton()
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()


def make_spec(
    capability_id: str,
    trust_level: str = "untrusted",
    version: str = "1.0.0",
    **kwargs,
) -> CapabilitySpec:
    """Helper to create a CapabilitySpec."""
    defaults: dict = {
        "capability_id": capability_id,
        "facade": "test",
        "provider_id": "test_provider",
        "adapter_class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
        "adapter_kwargs": {"server_id": "test"},
        "transport": "mcp",
        "version": version,
        "trust_level": trust_level,
        "authority_classification": "advisory",
        "allowed_operations": ("query", "read"),
        "sensitive_keys": ("password", "token", "secret"),
        "max_content_size": 10240,
        "tags": ("test",),
        "discovered_from": f"config/capabilities/{capability_id}.yaml",
        "dependencies": (),
    }
    # Allow list-form overrides too (callers pass lists for ops/keys).
    for key, value in kwargs.items():
        if key in ("allowed_operations", "sensitive_keys", "tags", "dependencies") and isinstance(
            value, list
        ):
            value = tuple(value)
        defaults[key] = value
    return CapabilitySpec(**defaults)


class TestRegisterCapability:
    """Tests for register_capability(spec) with extended fields."""

    @pytest.mark.asyncio
    async def test_register_capability_populates_extended_fields(self, cmgr):
        """register_capability(spec) populates trust_level, authority, adapter_binding, etc."""
        await cmgr.initialize()
        spec = make_spec("test_extended", trust_level="trusted_contextual")

        entry = cmgr.register_capability(spec)

        assert isinstance(entry, CapabilityRegistryEntry)
        assert entry.capability_id == "test_extended"
        assert entry.trust_level == TrustLevel.TRUSTED_CONTEXTUAL
        assert entry.authority_classification == AuthorityClassification.ADVISORY
        # adapter_binding carries the class path (+ kwargs) from the spec
        assert entry.adapter_binding["class_path"] == (
            "aios.adapters.graphify_adapter.GraphifyAdapter"
        )
        assert entry.operations == ("query", "read")
        assert entry.enabled is True
        assert entry.discovered_from == "config/capabilities/test_extended.yaml"
        assert entry.dependencies == ()
        # Enabled + registered → available
        assert entry.availability == CapabilityAvailability.AVAILABLE

    @pytest.mark.asyncio
    async def test_register_capability_disabled_starts_unavailable(self, cmgr):
        """A disabled spec registers non-enabled and does not resolve."""
        await cmgr.initialize()
        spec = make_spec("test_disabled_spec", enabled=False)
        cmgr.register_capability(spec)

        entry = cmgr.get_capability("test_disabled_spec")
        assert entry.enabled is False
        assert entry.availability == CapabilityAvailability.DISABLED

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.resolve("test_disabled_spec")
        assert exc.value.rule_id == "CM-DIS-001"


class TestDisableEnable:
    """Tests for disable/enable functionality."""

    @pytest.mark.asyncio
    async def test_disable_sets_state_disabled(self, cmgr):
        """disable() → state=DISABLED, enabled=False, entry retained."""
        await cmgr.initialize()
        spec = make_spec("test_disable")
        cmgr.register_capability(spec)

        assert cmgr.disable("test_disable") is True

        entry = cmgr.get_capability("test_disable")
        assert entry is not None  # entry retained
        assert entry.state == CapabilityState.DISABLED
        assert entry.enabled is False

    @pytest.mark.asyncio
    async def test_disable_resolve_raises(self, cmgr):
        """resolve() on disabled capability raises CM-DIS-001."""
        await cmgr.initialize()
        spec = make_spec("test_disable_resolve")
        cmgr.register_capability(spec)
        cmgr.disable("test_disable_resolve")

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.resolve("test_disable_resolve")
        assert exc.value.rule_id == "CM-DIS-001"

    @pytest.mark.asyncio
    async def test_disable_missing_returns_false(self, cmgr):
        """disable() of unknown capability returns False."""
        await cmgr.initialize()
        assert cmgr.disable("missing") is False

    @pytest.mark.asyncio
    async def test_enable_reverses_disable(self, cmgr):
        """enable() reverses disable."""
        await cmgr.initialize()
        spec = make_spec("test_enable")
        cmgr.register_capability(spec)
        cmgr.disable("test_enable")

        assert cmgr.enable("test_enable") is True

        entry = cmgr.get_capability("test_enable")
        assert entry.state == CapabilityState.REGISTERED
        assert entry.enabled is True
        resolved = cmgr.resolve("test_enable")
        assert resolved.capability_id == "test_enable"

    @pytest.mark.asyncio
    async def test_disable_is_idempotent(self, cmgr):
        """Double disable stays True (idempotent)."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("test_dis_idem"))

        assert cmgr.disable("test_dis_idem") is True
        assert cmgr.disable("test_dis_idem") is True


class TestDeprecate:
    """Tests for deprecate functionality."""

    @pytest.mark.asyncio
    async def test_deprecate_sets_state_deprecated(self, cmgr):
        """deprecate() → state=DEPRECATED, still resolvable but flagged."""
        await cmgr.initialize()
        spec = make_spec("test_deprecate")
        cmgr.register_capability(spec)

        assert cmgr.deprecate("test_deprecate") is True

        entry = cmgr.get_capability("test_deprecate")
        assert entry is not None
        assert entry.state == CapabilityState.DEPRECATED
        # Still resolvable (spec §14)
        resolved = cmgr.resolve("test_deprecate")
        assert resolved.capability_id == "test_deprecate"

    @pytest.mark.asyncio
    async def test_deprecate_missing_returns_false(self, cmgr):
        """deprecate() of unknown capability returns False."""
        await cmgr.initialize()
        assert cmgr.deprecate("missing") is False


class TestHealthAvailability:
    """Tests for health and availability."""

    @pytest.mark.asyncio
    async def test_set_health_healthy(self, cmgr):
        """set_health(AVAILABLE) marks the capability healthy."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("test_health"))
        cmgr.disable("test_health")

        assert cmgr.set_health("test_health", CapabilityAvailability.AVAILABLE) is True

        entry = cmgr.get_capability("test_health")
        assert entry.health_status == CapabilityAvailability.AVAILABLE

    @pytest.mark.asyncio
    async def test_set_health_degraded(self, cmgr):
        """set_health(DEGRADED) records degraded health."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("test_health_deg"))

        assert cmgr.set_health("test_health_deg", CapabilityAvailability.DEGRADED) is True

        entry = cmgr.get_capability("test_health_deg")
        assert entry.health_status == CapabilityAvailability.DEGRADED

    @pytest.mark.asyncio
    async def test_set_health_unavailable_marks_unavailable(self, cmgr):
        """set_health(UNAVAILABLE) flips availability to UNAVAILABLE."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("test_health_unavail"))

        assert cmgr.set_health(
            "test_health_unavail", CapabilityAvailability.UNAVAILABLE
        ) is True

        entry = cmgr.get_capability("test_health_unavail")
        assert entry.availability == CapabilityAvailability.UNAVAILABLE

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.resolve("test_health_unavail")
        assert exc.value.rule_id == "CM-RES-002"

    @pytest.mark.asyncio
    async def test_set_health_missing_returns_false(self, cmgr):
        """set_health of unknown capability returns False."""
        await cmgr.initialize()
        assert cmgr.set_health("missing", "healthy") is False


class TestSecurityContextEnforcement:
    """Tests for enforce_security_context(capability_id, caller_context)."""

    @pytest.mark.asyncio
    async def test_enforce_rejects_disallowed_operation(self, cmgr):
        """Operation not in allowed_operations → CM-SEC-001."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_op", allowed_operations=["read"]))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context("sec_op", {"operation": "write"})
        assert exc.value.rule_id == "CM-SEC-001"

    @pytest.mark.asyncio
    async def test_enforce_allows_allowed_operation(self, cmgr):
        """Operation in allowed_operations passes."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_op_ok", allowed_operations=["read", "write"]))

        entry = cmgr.enforce_security_context("sec_op_ok", {"operation": "write"})
        assert entry.capability_id == "sec_op_ok"

    @pytest.mark.asyncio
    async def test_enforce_rejects_sensitive_key_in_payload(self, cmgr):
        """Payload containing a declared sensitive key → CM-SEC-002."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_sens", sensitive_keys=["password", "secret"]))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context(
                "sec_sens", {"operation": "read", "payload": {"password": "hunter2"}}
            )
        assert exc.value.rule_id == "CM-SEC-002"

    @pytest.mark.asyncio
    async def test_enforce_rejects_nested_sensitive_key(self, cmgr):
        """Sensitive key nested inside the payload is still detected."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_nested", sensitive_keys=["api_key"]))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context(
                "sec_nested",
                {"operation": "read", "payload": {"config": {"nested": {"api_key": "k"}}}},
            )
        assert exc.value.rule_id == "CM-SEC-002"

    @pytest.mark.asyncio
    async def test_enforce_allows_non_sensitive_payload(self, cmgr):
        """Payload without sensitive keys passes."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_safe", sensitive_keys=["password"]))

        entry = cmgr.enforce_security_context(
            "sec_safe", {"operation": "read", "payload": {"username": "user"}}
        )
        assert entry.capability_id == "sec_safe"

    @pytest.mark.asyncio
    async def test_enforce_rejects_payload_keys_hint(self, cmgr):
        """caller_context payload_keys hint containing a sensitive key → CM-SEC-002."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_keys_hint", sensitive_keys=["token"]))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context(
                "sec_keys_hint", {"payload_keys": ["user", "token"]}
            )
        assert exc.value.rule_id == "CM-SEC-002"

    @pytest.mark.asyncio
    async def test_enforce_rejects_oversized_payload(self, cmgr):
        """Payload exceeding max_content_size → CM-SEC-003."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_size", max_content_size=100))

        big = "x" * 200
        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context("sec_size", {"operation": "read", "payload": big})
        assert exc.value.rule_id == "CM-SEC-003"

    @pytest.mark.asyncio
    async def test_enforce_rejects_explicit_content_size(self, cmgr):
        """Explicit content_size exceeding the limit → CM-SEC-003."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_size2", max_content_size=50))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context("sec_size2", {"content_size": 500})
        assert exc.value.rule_id == "CM-SEC-003"

    @pytest.mark.asyncio
    async def test_enforce_allows_sized_payload(self, cmgr):
        """Payload within size limit passes."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("sec_size_ok", max_content_size=1000))

        entry = cmgr.enforce_security_context(
            "sec_size_ok", {"operation": "read", "payload": "x" * 100}
        )
        assert entry.capability_id == "sec_size_ok"

    @pytest.mark.asyncio
    async def test_enforce_unknown_capability_raises_res(self, cmgr):
        """enforce_security_context of unregistered capability → CM-RES-001."""
        await cmgr.initialize()
        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.enforce_security_context("missing", {})
        assert exc.value.rule_id == "CM-RES-001"


class TestDuplicateAndCollision:
    """Tests for duplicate registration and collision handling (spec §16)."""

    @pytest.mark.asyncio
    async def test_duplicate_id_same_trust_equal_version_rejected(self, cmgr):
        """Same id, same trust, same version → rejected (first wins)."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("dup_eq", trust_level="untrusted", version="1.0.0"))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.register_capability(
                make_spec(
                    "dup_eq",
                    trust_level="untrusted",
                    version="1.0.0",
                    provider_id="other_provider",
                )
            )
        assert exc.value.rule_id == "CM-PREC-001"

    @pytest.mark.asyncio
    async def test_external_untrusted_cannot_shadow_builtin_trusted(self, cmgr):
        """External untrusted vs built-in trusted → external rejected CM-SHADOW-001."""
        await cmgr.initialize()
        # Register a built-in trusted capability first.
        cmgr.register_capability(make_spec("shadow_test", trust_level="builtin"))

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.register_capability(
                make_spec("shadow_test", trust_level="untrusted", provider_id="external")
            )
        assert exc.value.rule_id == "CM-SHADOW-001"

        # Built-in remains intact.
        entry = cmgr.get_capability("shadow_test")
        assert entry.provider_id == "test_provider"  # first registrant kept
        assert entry.trust_level == TrustLevel.BUILTIN

    @pytest.mark.asyncio
    async def test_equal_trust_higher_version_wins(self, cmgr):
        """Equal trust, higher semver → challenger replaces first registrant."""
        await cmgr.initialize()
        cmgr.register_capability(
            make_spec("ver_win", trust_level="untrusted", version="1.0.0")
        )
        cmgr.register_capability(
            make_spec(
                "ver_win",
                trust_level="untrusted",
                version="2.0.0",
                provider_id="provider2",
            )
        )

        entry = cmgr.get_capability("ver_win")
        assert entry.provider_id == "provider2"
        assert entry.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_higher_trust_can_replace_lower(self, cmgr):
        """Higher trust replaces lower trust regardless of version (spec §16 rule 1)."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("trust_up", trust_level="untrusted", version="2.0.0"))
        cmgr.register_capability(
            make_spec(
                "trust_up",
                trust_level="trusted_contextual",
                version="1.0.0",
                provider_id="provider2",
            )
        )

        entry = cmgr.get_capability("trust_up")
        assert entry.trust_level == TrustLevel.TRUSTED_CONTEXTUAL
        assert entry.provider_id == "provider2"

    @pytest.mark.asyncio
    async def test_unparseable_version_first_wins(self, cmgr):
        """Equal trust, unparseable versions sort below parseable ones."""
        await cmgr.initialize()
        # First registrant has a valid semver.
        cmgr.register_capability(
            make_spec("ver_unparseable", trust_level="untrusted", version="1.2.3")
        )
        # Challenger has an unparseable version — must NOT displace.
        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.register_capability(
                make_spec(
                    "ver_unparseable",
                    trust_level="untrusted",
                    version="not-a-version",
                    provider_id="provider2",
                )
            )
        assert exc.value.rule_id == "CM-PREC-001"

        entry = cmgr.get_capability("ver_unparseable")
        assert entry.provider_id == "test_provider"


class TestInitializeCapability:
    """Tests for initialize_capability()."""

    @pytest.mark.asyncio
    async def test_initialize_capability_instantiates_adapter(self, cmgr):
        """initialize_capability() instantiates the bound adapter via factory."""
        await cmgr.initialize()

        created = {}

        class FakeAdapter:
            def __init__(self, **kwargs):
                created.update(kwargs)

            async def initialize(self):
                created["initialized"] = True

            async def health_check(self):
                return {"status": "healthy"}

        class FakeFactory:
            def get_adapter(self, class_path, kwargs=None):
                assert class_path == "aios.adapters.graphify_adapter.GraphifyAdapter"
                return FakeAdapter(**(kwargs or {}))

        cmgr.set_adapter_factory(FakeFactory())
        cmgr.register_capability(make_spec("init_ok"))

        assert await cmgr.initialize_capability("init_ok") is True
        assert created.get("server_id") == "test"
        assert created.get("initialized") is True

        entry = cmgr.get_capability("init_ok")
        assert entry.availability == CapabilityAvailability.AVAILABLE
        assert entry.last_error is None

    @pytest.mark.asyncio
    async def test_initialize_failure_sets_availability_error(self, cmgr):
        """initialize failure → availability=error, last_error recorded, registry intact."""
        await cmgr.initialize()

        class ExplodingFactory:
            def get_adapter(self, class_path, kwargs=None):
                raise RuntimeError("factory exploded")

        cmgr.set_adapter_factory(ExplodingFactory())
        cmgr.register_capability(make_spec("init_fail"))

        result = await cmgr.initialize_capability("init_fail")
        assert result is False

        entry = cmgr.get_capability("init_fail")  # registry intact
        assert entry is not None
        assert entry.availability == CapabilityAvailability.ERROR
        assert "factory exploded" in (entry.last_error or "")

    @pytest.mark.asyncio
    async def test_initialize_adapter_initialize_failure_recorded(self, cmgr):
        """Adapter initialize() raising is recorded, availability becomes error."""
        await cmgr.initialize()

        class BadAdapter:
            async def initialize(self):
                raise ConnectionError("MCP unavailable")

        class Factory:
            def get_adapter(self, class_path, kwargs=None):
                return BadAdapter()

        cmgr.set_adapter_factory(Factory())
        cmgr.register_capability(make_spec("init_conn_fail"))

        assert await cmgr.initialize_capability("init_conn_fail") is False

        entry = cmgr.get_capability("init_conn_fail")
        assert entry.availability == CapabilityAvailability.ERROR
        assert "MCP unavailable" in (entry.last_error or "")

    @pytest.mark.asyncio
    async def test_initialize_dependency_not_available_fails(self, cmgr):
        """Declared dependency that is not AVAILABLE → initialization fails."""
        await cmgr.initialize()
        cmgr.register_capability(
            make_spec("dep_child", dependencies=("dep_missing",))
        )

        result = await cmgr.initialize_capability("dep_child")
        assert result is False

        entry = cmgr.get_capability("dep_child")
        assert entry.availability == CapabilityAvailability.ERROR
        assert "dep_missing" in (entry.last_error or "")

    @pytest.mark.asyncio
    async def test_initialize_unknown_returns_false(self, cmgr):
        """initialize_capability of unknown id returns False."""
        await cmgr.initialize()
        assert await cmgr.initialize_capability("missing") is False


class TestDeregisterUnchanged:
    """Regression tests for existing deregister behavior."""

    @pytest.mark.asyncio
    async def test_deregister_still_removed(self, cmgr):
        """deregister() still → REMOVED (unchanged behavior)."""
        await cmgr.initialize()
        cmgr.register_capability(make_spec("dereg_test"))

        assert cmgr.deregister("dereg_test") is True
        assert cmgr.get_capability("dereg_test") is None
        assert cmgr.deregister("dereg_test") is False


class TestRegressionGuards:
    """Regression guards: legacy register/deregister/resolve/invoke unchanged."""

    @pytest.mark.asyncio
    async def test_original_register_unchanged(self, cmgr):
        """Original register() signature and behavior unchanged."""
        await cmgr.initialize()
        entry = cmgr.register("cap.orig", "facade", "provider", version="1.0.0")

        assert entry.capability_id == "cap.orig"
        assert entry.facade == "facade"
        assert entry.provider_id == "provider"
        assert entry.state == CapabilityState.REGISTERED

    @pytest.mark.asyncio
    async def test_original_register_duplicate_rejected(self, cmgr):
        """Legacy register() duplicate rejection unchanged (CM-DUP-001)."""
        await cmgr.initialize()
        cmgr.register("cap.dup", "facade", "provider")

        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.register("cap.dup", "facade2", "provider2")
        assert exc.value.rule_id == "CM-DUP-001"

    @pytest.mark.asyncio
    async def test_original_deregister_unchanged(self, cmgr):
        """Original deregister() unchanged."""
        await cmgr.initialize()
        cmgr.register("cap.orig2", "facade", "provider")

        assert cmgr.deregister("cap.orig2") is True
        assert cmgr.get_capability("cap.orig2") is None

    @pytest.mark.asyncio
    async def test_original_resolve_unchanged(self, cmgr):
        """Original resolve() resolves legacy entries (they are always available)."""
        await cmgr.initialize()
        cmgr.register("cap.resolve", "facade", "provider")

        entry = cmgr.resolve("cap.resolve")
        assert entry.capability_id == "cap.resolve"

    @pytest.mark.asyncio
    async def test_original_resolve_unregistered_raises(self, cmgr):
        """resolve() of unregistered id raises CM-RES-001 (unchanged)."""
        await cmgr.initialize()
        with pytest.raises(CapabilityManagerError) as exc:
            cmgr.resolve("nope")
        assert exc.value.rule_id == "CM-RES-001"

    @pytest.mark.asyncio
    async def test_original_invoke_unchanged(self, cmgr):
        """Original invoke() unchanged."""
        await cmgr.initialize()
        cmgr.register("cap.invoke", "facade", "provider")

        entry = cmgr.invoke("cap.invoke", input_payload={}, caller_context={})
        assert entry.capability_id == "cap.invoke"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
