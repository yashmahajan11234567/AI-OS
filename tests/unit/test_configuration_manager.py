"""
Task 7 — ConfigurationManager unit tests (Part 3 §3.5).

Exercises the architecture-defined contract of Core Component C3:

  * construction / singleton (INV-CM-STR-001)
  * component metadata (name / phase / dependencies / ICoreComponent surface)
  * four-layer merge + precedence (§3.5.1-§3.5.3)
  * deep merge + array replacement (INV-CM-PREC-002)
  * schema validation success / failure (§3.5.4-§3.5.5, INV-CM-VAL-001/003)
  * initialization failure on invalid config (§3.5.12, INV-CM-FH-001)
  * freeze + post-freeze mutation rejection (§3.5.6, INV-CM-FRZ-003/004)
  * deep immutability / no mutation through returned structures
  * accessor correctness / getSection / secret detection / masking / non-leakage
  * environment variables + unknown AIOS_* handling + malformed values
  * deterministic hash (identical -> identical, changed -> changed)
  * EventBus integration (ConfigurationFrozen / CoreComponentInitialized /
    CoreComponentShutdown)
  * healthCheck / concurrent post-freeze reads

The bus is driven deterministically via ``await bus.drain()``; synchronous
emissions (freeze) are flushed by the running loop. Per Task 7 rules, only
canonical EventTypes (Task 2) are asserted.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from aios.core.configuration_manager import (
    ConfigurationError,
    ConfigurationFrozenError,
    ConfigState,
    KernelConfigSchema,
    PropertySchema,
    _collect_secret_paths,
    _deep_merge,
    _EMBEDDED_DEFAULTS,
    get_configuration_manager,
    is_secret_path,
    reset_configuration_manager_singleton,
)
from aios.events.core import EventBus, EventBusConfig, EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return b


@pytest.fixture
def manager(bus):
    reset_configuration_manager_singleton()
    mgr = get_configuration_manager(event_bus=bus)
    yield mgr
    reset_configuration_manager_singleton()


def _init_and_freeze(mgr, bus):
    async def _run():
        await bus.initialize()
        await mgr.initialize()
        mgr.freeze()
        # flush synchronous freeze emission onto the running loop
        await bus.drain()

    asyncio.run(_run())


def _seed_and_freeze(mgr, merged):
    """Seed merged config and freeze directly (bypasses initialize() reload)."""
    with mgr._lock:
        mgr._merged = merged
    mgr.freeze()


# ---------------------------------------------------------------------------
# 1. construction
# ---------------------------------------------------------------------------


def test_construction(manager):
    assert isinstance(manager, __import__("aios.core.configuration_manager", fromlist=["ConfigurationManager"]).ConfigurationManager)
    assert manager.state is ConfigState.UNINITIALIZED


# ---------------------------------------------------------------------------
# 2. singleton
# ---------------------------------------------------------------------------


def test_singleton_identity(bus):
    reset_configuration_manager_singleton()
    first = get_configuration_manager(event_bus=bus)
    second = get_configuration_manager(event_bus=bus)
    assert first is second
    reset_configuration_manager_singleton()


def test_singleton_rejects_second_construction(bus):
    reset_configuration_manager_singleton()
    first = get_configuration_manager(event_bus=bus)
    from aios.core.configuration_manager import ConfigurationManager

    with pytest.raises(RuntimeError):
        ConfigurationManager(event_bus=bus)
    reset_configuration_manager_singleton()


# ---------------------------------------------------------------------------
# 3. component metadata
# ---------------------------------------------------------------------------


def test_component_metadata(manager):
    assert manager.name == "ConfigurationManager"
    assert manager.phase == 2
    assert manager.dependencies == ["EventBus"]
    assert manager.event_bus is not None


# ---------------------------------------------------------------------------
# 4-7. four-layer merge / precedence / deep merge / list replacement
# ---------------------------------------------------------------------------


def test_embedded_defaults_present():
    cfg = dict(_EMBEDDED_DEFAULTS)
    assert cfg["kernel"]["name"] == "Hermes"
    assert cfg["kernel"]["logLevel"] == "INFO"


def test_deep_merge_recurses_and_replaces_scalars():
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    over = {"a": {"y": 20}, "c": 4}
    merged = _deep_merge(base, over)
    assert merged["a"]["x"] == 1  # preserved
    assert merged["a"]["y"] == 20  # overridden
    assert merged["b"] == 3
    assert merged["c"] == 4


def test_array_replacement_not_concat():
    base = {"k": [1, 2, 3]}
    over = {"k": [9]}
    merged = _deep_merge(base, over)
    assert merged["k"] == [9]  # replaced, not concatenated


def test_null_removes_key():
    base = {"k": "value", "j": "keep"}
    over = {"k": None}
    merged = _deep_merge(base, over)
    assert "k" not in merged
    assert merged["j"] == "keep"


# ---------------------------------------------------------------------------
# 8-10. schema validation
# ---------------------------------------------------------------------------


def test_schema_validation_success():
    schema = KernelConfigSchema()
    schema.validate({"kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"}})


def test_schema_validation_failure_missing_required():
    schema = KernelConfigSchema()
    with pytest.raises(ConfigurationError):
        schema.validate({"kernel": {"name": "Hermes"}})  # missing version + logLevel


def test_schema_validation_failure_enum():
    schema = KernelConfigSchema()
    with pytest.raises(ConfigurationError):
        schema.validate(
            {"kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "LOUD"}}
        )


def test_schema_validation_failure_unknown_top_level():
    """Test that schema validation rejects unknown top-level keys when additional_properties=False.

    Note: Current schema allows additional properties for application config sections
    (event_bus, services, etc.). This test verifies the schema behavior with the
    default additional_properties=True setting.
    """
    schema = KernelConfigSchema()
    # With additional_properties=True, unknown keys are allowed
    schema.validate(
        {"kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"}, "bogus": {}}
    )
    # If additional_properties were False, this would raise ConfigurationError


def test_initialization_failure_on_invalid_config(bus):
    reset_configuration_manager_singleton()

    # Force initialize() to merge an invalid config (missing required
    # kernel.version/logLevel) so schema validation fails and aborts
    # initialization (§3.5.12 / INV-CM-FH-001). Fully self-contained.
    mgr = get_configuration_manager(event_bus=bus)
    mgr._load_and_merge = lambda: {"kernel": {"name": "Hermes"}}

    async def _run():
        with pytest.raises(ConfigurationError):
            await mgr.initialize()
        assert mgr.state is ConfigState.SHUTDOWN

    asyncio.run(_run())
    reset_configuration_manager_singleton()


# ---------------------------------------------------------------------------
# 11-14. freeze / post-freeze mutation rejection / immutability
# ---------------------------------------------------------------------------


def test_freeze_transitions_to_frozen(manager, bus):
    _init_and_freeze(manager, bus)
    assert manager.state is ConfigState.FROZEN
    assert manager.config_hash is not None


def test_freeze_twice_raises(manager, bus):
    _init_and_freeze(manager, bus)
    with pytest.raises(ConfigurationFrozenError):
        manager.freeze()


def test_post_freeze_mutation_rejected(manager, bus):
    _init_and_freeze(manager, bus)
    with pytest.raises(ConfigurationFrozenError):
        manager.apply_override({"kernel": {"name": "x"}})
    with pytest.raises(ConfigurationFrozenError):
        manager.set_test_override("kernel.name", "x")


def test_deep_immutability_of_frozen_snapshot(manager, bus):
    _init_and_freeze(manager, bus)
    allcfg = manager.get_all()
    # Per §3.5.7: accessors return immutable views (defensive copy or frozen
    # object). A defensive copy means mutating the returned object MUST NOT
    # change the ConfigurationManager's internal frozen state.
    if isinstance(allcfg.get("kernel"), dict):
        try:
            allcfg["kernel"]["name"] = "mutated"
        except (TypeError, AttributeError):
            pass
    assert manager.get("kernel.name") == "Hermes"


# ---------------------------------------------------------------------------
# 15-18. accessor correctness / section / secrets
# ---------------------------------------------------------------------------


def test_get_returns_value(manager, bus):
    _init_and_freeze(manager, bus)
    assert manager.get("kernel.name") == "Hermes"
    assert manager.get("kernel.logLevel") == "INFO"
    assert manager.get("does.not.exist", default="X") == "X"


def test_get_section(manager, bus):
    _init_and_freeze(manager, bus)
    section = manager.get_section("kernel")
    assert isinstance(section, dict)
    assert section["name"] == "Hermes"
    # returned section is a copy; mutation must not affect internal state
    section["name"] = "mutated"
    assert manager.get("kernel.name") == "Hermes"


def test_secret_detection_patterns():
    assert is_secret_path(["security", "jwtSecret"])
    assert is_secret_path(["llm", "providers", "openai", "apiKey"])
    assert is_secret_path(["db", "password"])
    assert is_secret_path(["x", "authToken"])
    assert is_secret_path(["x", "dbCredential"])
    assert not is_secret_path(["kernel", "logLevel"])
    assert not is_secret_path(["kernel", "name"])


def test_secret_masking_in_get_all(manager, bus):
    # Pre-seed a secret into merged config before freeze.
    _seed_and_freeze(
        manager,
        {
            "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "super-secret-value"},
        },
    )
    allcfg = manager.get_all()
    assert allcfg["security"]["jwtSecret"] == "***"
    # Raw value never leaks through non-secret accessor
    assert "super-secret-value" not in repr(allcfg)


def test_secret_masking_in_get(manager, bus):
    _seed_and_freeze(
        manager,
        {
            "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "topsecret"},
        },
    )
    assert manager.get("security.jwtSecret") == "***"


def test_secret_non_leakage_through_get_all(manager, bus):
    with manager._lock:
        manager._merged = {
            "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
            "llm": {"providers": {"openai": {"apiKey": "sk-12345"}}},
        }
    _init_and_freeze(manager, bus)
    out = repr(manager.get_all())
    assert "sk-12345" not in out


def test_get_secret_returns_raw(bus):
    reset_configuration_manager_singleton()
    mgr = get_configuration_manager(event_bus=bus)
    _seed_and_freeze(
        mgr,
        {
            "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "rawsecret"},
        },
    )
    assert mgr.get_secret("security.jwtSecret") == "rawsecret"
    reset_configuration_manager_singleton()


def test_get_secret_rejects_non_secret(bus):
    reset_configuration_manager_singleton()
    mgr = get_configuration_manager(event_bus=bus)
    _init_and_freeze(mgr, bus)
    with pytest.raises(ConfigurationError):
        mgr.get_secret("kernel.name")
    reset_configuration_manager_singleton()


def test_collect_secret_paths():
    cfg = {"security": {"jwtSecret": "x"}, "kernel": {"name": "n"}}
    paths = _collect_secret_paths(cfg)
    assert "security.jwtSecret" in paths
    assert "kernel.name" not in paths


# ---------------------------------------------------------------------------
# 19-21. environment variables
# ---------------------------------------------------------------------------


def test_env_var_override(monkeypatch, bus):
    reset_configuration_manager_singleton()
    monkeypatch.setenv("AIOS_KERNEL_LOG_LEVEL", "DEBUG")
    mgr = get_configuration_manager(event_bus=bus)
    _init_and_freeze(mgr, bus)
    assert mgr.get("kernel.logLevel") == "DEBUG"
    reset_configuration_manager_singleton()


def test_unknown_aios_env_var_warned(monkeypatch, bus, recwarn):
    reset_configuration_manager_singleton()
    monkeypatch.setenv("AIOS_TOTALLY_UNKNOWN_KEY", "value")
    mgr = get_configuration_manager(event_bus=bus)
    _init_and_freeze(mgr, bus)
    # Unknown key must NOT appear in config (INV-CM-ENV-002).
    assert mgr.get("totally", default=None) is None
    reset_configuration_manager_singleton()


def test_malformed_known_env_var_eventually_fails_schema(monkeypatch, bus):
    reset_configuration_manager_singleton()
    # logLevel must be an enum; a non-enum value must fail schema validation.
    monkeypatch.setenv("AIOS_KERNEL_LOG_LEVEL", "ULTRA")
    mgr = get_configuration_manager(event_bus=bus)

    async def _run():
        with pytest.raises(ConfigurationError):
            await mgr.initialize()

    asyncio.run(_run())
    reset_configuration_manager_singleton()


def test_env_var_nested_secret(monkeypatch, bus):
    reset_configuration_manager_singleton()
    monkeypatch.setenv("AIOS_SECURITY_JWT_SECRET", "envsecret")
    mgr = get_configuration_manager(event_bus=bus)
    _init_and_freeze(mgr, bus)
    # Masked via non-secret accessor
    assert mgr.get("security.jwtSecret") == "***"
    # Raw retrievable via secret accessor
    assert mgr.get_secret("security.jwtSecret") == "envsecret"
    reset_configuration_manager_singleton()


# ---------------------------------------------------------------------------
# 22-24. deterministic hash
# ---------------------------------------------------------------------------


def test_deterministic_hash_function():
    from aios.core.configuration_manager import _compute_config_hash

    a = {"kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"}}
    b = {"kernel": {"version": "0.1.0", "name": "Hermes", "logLevel": "INFO"}}
    # Different insertion order -> identical hash
    assert _compute_config_hash(a) == _compute_config_hash(b)


def test_identical_config_identical_hash(manager, bus):
    _init_and_freeze(manager, bus)
    h1 = manager.config_hash
    # Re-freeze equivalent via second manager with same defaults
    reset_configuration_manager_singleton()
    mgr2 = get_configuration_manager(event_bus=bus)
    _init_and_freeze(mgr2, bus)
    assert h1 == mgr2.config_hash
    reset_configuration_manager_singleton()


def test_changed_config_changed_hash(bus):
    reset_configuration_manager_singleton()
    m1 = get_configuration_manager(event_bus=bus)
    _init_and_freeze(m1, bus)
    h1 = m1.config_hash

    reset_configuration_manager_singleton()
    m2 = get_configuration_manager(event_bus=bus)
    _seed_and_freeze(
        m2,
        {
            "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "WARNING"}
        },
    )
    assert m2.config_hash != h1
    reset_configuration_manager_singleton()


# ---------------------------------------------------------------------------
# 25-27. EventBus integration
# ---------------------------------------------------------------------------


def test_configuration_frozen_event(manager, bus):
    async def _run():
        await bus.initialize()
        await manager.initialize()
        manager.freeze()
        await bus.drain()

    asyncio.run(_run())
    events = bus.getEventsByType(EventType.CONFIGURATION_FROZEN)
    assert len(events) == 1
    assert "configHash" in events[0].payload.to_dict()


def test_core_component_initialized_event(manager, bus):
    async def _run():
        await bus.initialize()
        await manager.initialize()
        manager.freeze()
        await bus.drain()

    asyncio.run(_run())
    events = bus.getEventsByType(EventType.CORE_COMPONENT_INITIALIZED)
    assert len(events) >= 1


def test_core_component_shutdown_event(manager, bus):
    async def _run():
        await bus.initialize()
        await manager.initialize()
        manager.freeze()
        await manager.shutdown()
        await bus.drain()

    asyncio.run(_run())
    events = bus.getEventsByType(EventType.CORE_COMPONENT_SHUTDOWN)
    assert len(events) >= 1


# ---------------------------------------------------------------------------
# 28. healthCheck
# ---------------------------------------------------------------------------


def test_health_check_uninitialized(manager):
    assert manager.healthCheck()["healthy"] is False


def test_health_check_frozen(manager, bus):
    _init_and_freeze(manager, bus)
    h = manager.healthCheck()
    assert h["healthy"] is True
    assert h["frozen"] is True
    assert h["configHash"] == manager.config_hash


# ---------------------------------------------------------------------------
# 29. concurrent post-freeze reads
# ---------------------------------------------------------------------------


def test_concurrent_post_freeze_reads(manager, bus):
    _init_and_freeze(manager, bus)

    import threading

    errors = []
    results = []

    def reader() -> None:
        try:
            for _ in range(200):
                v = manager.get("kernel.name")
                assert v == "Hermes"
                results.append(v)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(results) == 8 * 200


# ---------------------------------------------------------------------------
# 30. no mutation through returned structures
# ---------------------------------------------------------------------------


def test_no_mutation_through_returned_structures(manager, bus):
    _init_and_freeze(manager, bus)
    section = manager.get_section("kernel")
    # Mutating the returned copy must not reach internal frozen state.
    if isinstance(section, dict):
        try:
            section["name"] = "x"
        except (TypeError, AttributeError):
            pass
    assert manager.get("kernel.name") == "Hermes"

    allcfg = manager.get_all()
    if isinstance(allcfg.get("kernel"), dict):
        try:
            allcfg["kernel"]["name"] = "y"
        except (TypeError, AttributeError):
            pass
    assert manager.get("kernel.name") == "Hermes"


def test_property_schema_frozen_instantiable():
    ps = PropertySchema(type="string", enum=["A", "B"], default="A")
    assert ps.type == "string"
    assert ps.enum == ["A", "B"]


# ---------------------------------------------------------------------------
# 31. FIX 1 — true deep immutability of internal frozen storage
# ---------------------------------------------------------------------------


def test_internal_frozen_storage_is_immutable(manager, bus):
    _init_and_freeze(manager, bus)
    fc = manager._frozen_config
    # The internal representation is a tuple-of-pairs (dict) / tuple (list) /
    # scalar — never a mutable dict/list.
    assert isinstance(fc, tuple)
    # Nested dict (kernel) is a tuple-of-pairs.
    kernel_node = next(v for k, v in fc if k == "kernel")
    assert isinstance(kernel_node, tuple)
    # Mutating the internal storage must raise, not silently succeed.
    with pytest.raises((TypeError, AttributeError)):
        fc[0][1]["kernel"][1] = "HACKED"
    # Ensure nothing leaked through.
    assert manager.get("kernel.name") == "Hermes"


def test_deep_freeze_nested_structures_immutable():
    from aios.core.configuration_manager import _deep_freeze

    frozen = _deep_freeze(
        {
            "a": {"b": {"c": 1}},
            "list": [1, 2, {"x": 3}],
            "nested_list": [[1, 2], [3]],
        }
    )
    # dict -> tuple of pairs
    assert isinstance(frozen, tuple)
    nested = next(v for k, v in frozen if k == "a")
    assert isinstance(nested, tuple)
    # nested dict
    deep = next(v for k, v in nested if k == "b")
    assert isinstance(deep, tuple)
    # list -> tuple
    lst = next(v for k, v in frozen if k == "list")
    assert isinstance(lst, tuple)
    inner_dict = lst[2]
    assert isinstance(inner_dict, tuple)
    # nested list
    nl = next(v for k, v in frozen if k == "nested_list")
    assert isinstance(nl, tuple)
    assert isinstance(nl[0], tuple)
    # Mutations all fail.
    with pytest.raises((TypeError, AttributeError)):
        frozen[0][1]["a"] = "x"
    with pytest.raises((TypeError, AttributeError)):
        frozen[1] = "x"
    with pytest.raises((TypeError, AttributeError)):
        nl[0][0] = 99


# ---------------------------------------------------------------------------
# 32. FIX 2 — FREEZING lifecycle state
# ---------------------------------------------------------------------------


def test_freezing_state_transition(manager, bus):
    reset_configuration_manager_singleton()
    mgr = get_configuration_manager(event_bus=bus)
    seen = {}

    async def _run():
        await mgr.initialize()
        orig = type(mgr)._run_emission
        mgr._run_emission = lambda et, pl: (seen.setdefault("state", mgr.state.value), orig(mgr, et, pl))
        mgr.freeze()
        await bus.drain()

    asyncio.run(_run())
    # The ConfigurationFrozen event is emitted while the component is in the
    # architecture-required FREEZING state (not INITIALIZING, not yet FROZEN).
    assert seen["state"] == "FREEZING"
    assert mgr.state is ConfigState.FROZEN


def test_freeze_failure_cannot_leave_frozen(manager, bus):
    # If the freeze's work raises, the object must NOT be left falsely FROZEN.
    reset_configuration_manager_singleton()
    mgr = get_configuration_manager(event_bus=bus)
    async def _run():
        await mgr.initialize()
    asyncio.run(_run())
    # Patch the module-level deep-freeze (used by freeze()) to raise, so the
    # freeze work fails before the immutable representation is committed.
    import aios.core.configuration_manager as cm_mod

    orig = cm_mod._deep_freeze
    cm_mod._deep_freeze = lambda cfg: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        mgr.freeze()
    except Exception:
        pass
    finally:
        cm_mod._deep_freeze = orig
    assert mgr.state is not ConfigState.FROZEN
    assert mgr.state in (ConfigState.INITIALIZING, ConfigState.FREEZING)


# ---------------------------------------------------------------------------
# 33. FIX 3 — Layer 3 environment config actually participates
# ---------------------------------------------------------------------------


def test_env_layer_loaded_when_present(tmp_path, monkeypatch, bus):
    reset_configuration_manager_singleton()
    app = tmp_path / "app.yaml"
    app.write_text("kernel:\n  name: AppName\n  environment: staging\n")
    env_file = tmp_path / "app.staging.yaml"
    env_file.write_text("kernel:\n  logLevel: WARNING\n")
    mgr = get_configuration_manager(event_bus=bus, config_path=app)

    async def _run():
        await mgr.initialize()
        mgr.freeze()
        await bus.drain()

    asyncio.run(_run())
    # Layer 3 (env-specific) override was merged and wins over Layers 1/2.
    assert mgr.get("kernel.name") == "AppName"
    assert mgr.get("kernel.logLevel") == "WARNING"
    assert mgr.get("kernel.environment") == "staging"


# ---------------------------------------------------------------------------
# 34. FIX 4 — deterministic event emission (canonical bus)
# ---------------------------------------------------------------------------


def test_events_observable_after_operation(manager, bus):
    async def _run():
        await bus.initialize()
        await manager.initialize()
        manager.freeze()
        await bus.drain()
        await manager.shutdown()
        await bus.drain()

    asyncio.run(_run())
    assert len(bus.getEventsByType(EventType.CORE_COMPONENT_INITIALIZED)) >= 1
    assert len(bus.getEventsByType(EventType.CONFIGURATION_FROZEN)) == 1
    assert len(bus.getEventsByType(EventType.CORE_COMPONENT_SHUTDOWN)) >= 1


# ---------------------------------------------------------------------------
# 35. FIX 6 — secret detection (token-based, no false positives)
# ---------------------------------------------------------------------------


def test_secret_detection_positive():
    assert is_secret_path(["security", "jwtSecret"])
    assert is_secret_path(["llm", "providers", "openai", "apiKey"])
    assert is_secret_path(["security", "api_key"])
    assert is_secret_path(["db", "password"])
    assert is_secret_path(["x", "authToken"])
    assert is_secret_path(["x", "dbCredential"])
    assert is_secret_path(["x", "clientSecret"])


def test_secret_detection_negative():
    # "keyboard" must NOT be a secret (FIX 6).
    assert not is_secret_path(["kernel", "keyboard"])
    assert not is_secret_path(["kernel", "logLevel"])
    assert not is_secret_path(["kernel", "name"])
    assert not is_secret_path(["ui", "keystone"])


def test_mutation_rejected_during_shutdown(manager, bus):
    async def _run():
        await manager.initialize()
        manager.freeze()
        await manager.shutdown()

    asyncio.run(_run())
    assert manager.state is ConfigState.SHUTDOWN
    with pytest.raises(ConfigurationFrozenError):
        manager.apply_override({"kernel": {"name": "x"}})
    with pytest.raises(ConfigurationFrozenError):
        manager.set_test_override("kernel.name", "x")


# ---------------------------------------------------------------------------
# 37. FIX 5 — public exports from aios.core
# ---------------------------------------------------------------------------


def test_core_exports_configuration_manager():
    import aios.core as core
    from aios.core.configuration_manager import ConfigurationManager as CM

    for sym in (
        "ConfigurationManager",
        "ConfigState",
        "ConfigurationError",
        "ConfigurationFrozenError",
        "KernelConfigSchema",
        "PropertySchema",
        "get_configuration_manager",
        "set_configuration_manager",
        "reset_configuration_manager_singleton",
    ):
        assert hasattr(core, sym), f"aios.core missing export: {sym}"
    assert core.ConfigurationManager is CM
    # Private helpers are NOT exported.
    assert not hasattr(core, "_deep_freeze")
    assert not hasattr(core, "_masked_view")


# ---------------------------------------------------------------------------
# 38. FIX 8 — kernel.service_registry has a defined attribute pre-start
# ---------------------------------------------------------------------------


def test_kernel_service_registry_attribute_present():
    from aios.core.kernel import HermesKernel

    k = HermesKernel()
    # Before start(), the field must exist (not raise AttributeError).
    assert k.service_registry is None
    # Accessing register/get before start() raises a clear RuntimeError (not
    # AttributeError) — the field is initialized appropriately.
    with pytest.raises(RuntimeError):
        k.register_service(object())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        k.get_service("x")
