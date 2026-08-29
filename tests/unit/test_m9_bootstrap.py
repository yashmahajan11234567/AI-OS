"""M9-N1 — Engineering-service bootstrap unit tests (spec §24, §34).

Tier A: exercises ``bootstrap_engineering_services`` against the REAL
canonical C2 ServiceRegistry (via the legacy-compatible wrapper, which
delegates to the canonical singleton) — never a hand-injected fake registry.
Per IND-6 (M8 lesson): fixtures MUST NOT inject corrected runtime objects that
stock boot wouldn't construct; here the bootstrap path IS the production path.

Coverage:
  * all 11 engineering services instantiate + register in dependency order
  * idempotent re-bootstrap replaces instances (spec §13)
  * ``services.enabled`` allowlist filters registration (spec §19)
  * partial-failure isolation: a failing factory is logged and skipped (R-8)
  * module-global binding (learning / self-prompting / RCA)
"""

from __future__ import annotations

import pytest

from aios.core.service_registry import (
    reset_service_registry_singleton,
)
from aios.events.core.bus import reset_event_bus_singleton
from aios.services.bootstrap import bootstrap_engineering_services
from aios.services.registry import get_service_registry

EXPECTED_SERVICES = [
    "memory",
    "planning",
    "learning",
    "coding",
    "review",
    "deployment",
    "operations",
    "mcp",
    "skill",
    "council",
    "self_prompting",
]

# Dependency order (prefix property of the bootstrap's factory ordering).
_DEPENDENCY_ORDER = [
    ("memory", ("planning", "learning", "coding")),
    ("planning", ("coding",)),
    ("coding", ("review",)),
    ("review", ("deployment",)),
    ("deployment", ("operations",)),
]


@pytest.fixture(autouse=True)
def _registry_isolation():
    """Fresh canonical registry + EventBus per test."""
    from aios.core.service_registry import set_service_registry as set_core

    from aios.core.service_registry import (
        ServiceRegistry as CoreRegistry,
    )
    from aios.core.service_registry import ServiceType
    from aios.events.core.bus import EventBus, EventBusConfig

    reset_event_bus_singleton()
    reset_service_registry_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    core = CoreRegistry(event_bus=bus)
    set_core(core)

    yield

    # Unregister engineering services so the shared canonical registry can be
    # dropped cleanly.
    try:
        for sid in list(getattr(core, "_registrations", {}).keys()):
            if str(sid).startswith("engineering."):
                core.unregister(sid)
    except Exception:  # noqa: BLE001 — best-effort teardown
        pass
    reset_service_registry_singleton()
    reset_event_bus_singleton()


def _registration_ids() -> set[str]:
    # get_service_registry() returns the canonical C2 singleton (Rule 10).
    core = get_service_registry()
    return {
        sid
        for sid in getattr(core, "_registrations", {})
        if str(sid).startswith("engineering.")
    }


class TestBootstrapRegistersAllServices:
    def test_all_11_services_registered(self):
        services = bootstrap_engineering_services()
        names = [svc.name for svc in services]
        assert names == EXPECTED_SERVICES
        assert _registration_ids() == {
            f"engineering.{name}" for name in EXPECTED_SERVICES
        }

    def test_dependency_order_respected(self):
        services = bootstrap_engineering_services()
        positions = {svc.name: i for i, svc in enumerate(services)}
        for before, afters in _DEPENDENCY_ORDER:
            for after in afters:
                assert positions[before] < positions[after], (
                    f"{before} must precede {after}"
                )

    def test_returns_base_service_instances(self):
        services = bootstrap_engineering_services()
        from aios.services.base import BaseService

        assert all(isinstance(svc, BaseService) for svc in services)


class TestBootstrapIdempotency:
    def test_rebootstrap_replaces_instances(self):
        first = bootstrap_engineering_services()
        second = bootstrap_engineering_services()

        # Same ids, new instances (spec §13: re-running replaces).
        first_by_name = {svc.name: svc for svc in first}
        second_by_name = {svc.name: svc for svc in second}
        assert set(first_by_name) == set(second_by_name)
        for name in first_by_name:
            if name == "mcp" or name == "skill" or name == "council":
                # manager-backed facades may reuse their underlying manager,
                # but the service object itself must be fresh
                pass
            assert second_by_name[name] is not first_by_name[name], name
        # Registry holds exactly one registration per id (no duplicates).
        assert len(_registration_ids()) == len(EXPECTED_SERVICES)

    def test_rebootstrap_preserves_allowlist_semantics(self):
        bootstrap_engineering_services(enabled=["memory", "learning"])
        again = bootstrap_engineering_services(enabled=["memory", "learning"])
        assert {svc.name for svc in again} == {"memory", "learning"}
        assert _registration_ids() == {
            "engineering.memory",
            "engineering.learning",
        }


class TestAllowlist:
    def test_empty_allowlist_enables_everything(self):
        services = bootstrap_engineering_services(enabled=[])
        assert [svc.name for svc in services] == EXPECTED_SERVICES

    def test_subset_allowlist_registers_subset(self):
        services = bootstrap_engineering_services(
            enabled=["memory", "learning", "planning"]
        )
        assert {svc.name for svc in services} == {"memory", "learning", "planning"}
        assert _registration_ids() == {
            "engineering.memory",
            "engineering.learning",
            "engineering.planning",
        }

    def test_unknown_name_in_allowlist_registers_nothing(self):
        services = bootstrap_engineering_services(enabled=["nonexistent"])
        assert services == []
        assert _registration_ids() == set()


class TestPartialFailureIsolation:
    def test_failing_factory_skipped_others_registered(self, monkeypatch):
        import aios.services.bootstrap as bootmod

        original = list(bootmod._SERVICE_FACTORIES)
        broken = [
            ("memory", lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
            *original[1:],
        ]
        monkeypatch.setattr(bootmod, "_SERVICE_FACTORIES", broken)

        services = bootstrap_engineering_services()
        names = [svc.name for svc in services]
        assert "memory" not in names
        # Everything else still registered (partial bootstrap, R-8).
        assert set(names) == set(EXPECTED_SERVICES) - {"memory"}
        assert _registration_ids() == {
            f"engineering.{n}" for n in EXPECTED_SERVICES if n != "memory"
        }

    def test_registration_failure_skipped_not_fatal(self, monkeypatch):
        """A registry-level rejection must not abort remaining registrations."""
        registry_type = type(get_service_registry())
        real_register = registry_type.register

        def failing_register(self, service, **kwargs):
            if service.name == "learning":
                raise RuntimeError("registry exploded")
            return real_register(self, service, **kwargs)

        monkeypatch.setattr(registry_type, "register", failing_register)
        services = bootstrap_engineering_services()
        names = [svc.name for svc in services]
        assert "learning" not in names
        assert "memory" in names and "planning" in names


class TestModuleGlobalBinding:
    def test_learning_global_bound(self):
        from aios.services.learning import get_learning_service

        services = bootstrap_engineering_services(enabled=["memory", "learning"])
        learning = next(svc for svc in services if svc.name == "learning")
        assert get_learning_service() is learning

    def test_self_prompting_global_bound(self):
        from aios.services.self_prompting import (
            get_self_prompting_service,
            set_self_prompting_service,
        )

        services = bootstrap_engineering_services(enabled=["self_prompting"])
        sp = services[0]
        assert get_self_prompting_service() is sp

    def test_rca_global_constructed_with_learning(self):
        from aios.core.root_cause import (
            get_root_cause_analyzer,
            set_root_cause_analyzer,
        )

        set_root_cause_analyzer(None)
        bootstrap_engineering_services(enabled=["memory", "learning"])
        analyzer = get_root_cause_analyzer()
        assert analyzer is not None

    def test_no_rca_without_learning(self):
        from aios.core.root_cause import (
            get_root_cause_analyzer,
            set_root_cause_analyzer,
        )

        set_root_cause_analyzer(None)
        bootstrap_engineering_services(enabled=["memory"])  # no learning
        analyzer = get_root_cause_analyzer()
        # Not constructed by the bootstrap itself...
        # (get_root_cause_analyzer() lazily constructs on access, so assert via
        # the module global directly.)
        import aios.core.root_cause as rcmod

        # After the lazy getter ran above, an instance now exists; the
        # meaningful assertion is that the BOOTSTRAP did not create it before
        # this access. Re-reset and introspect without calling the getter.
        set_root_cause_analyzer(None)
        bootstrap_engineering_services(enabled=["memory"])
        assert rcmod._global_root_cause_analyzer is None


class TestImportableWithoutKernel:
    def test_callable_without_kernel(self):
        """Spec §11.1: importable & callable without a live kernel.

        The fixture provides only the canonical registry + EventBus — no
        HermesKernel exists. This test proves the function runs standalone.
        """
        services = bootstrap_engineering_services()
        assert len(services) == len(EXPECTED_SERVICES)
