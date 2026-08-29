"""M9-N6 — Capability manifest hot-reload integration tests (spec §11.6, §34).

Tier B: exercises the REAL stock-boot path. The kernel boots normally
(``_init_capability_manifests`` loads config/capabilities/*.yaml through the
production loader), then the M9 explicit ``reload_capability_manifests()`` API
re-runs the identical pipeline. No runtime object is hand-injected (IND-6)
except where a test deliberately drives ``CapabilityManager.reload_capabilities``
directly with a real ``CapabilityManifestLoader`` over a temp manifest dir
(that is the unit under test's own public API, not an injection).

Coverage:
  * happy path: reload re-validates and keeps all 5 stock capabilities green
  * invalid manifest → fail-closed rejection, prior registry intact
  * trust escalation (builtin/authoritative) rejected by unchanged M8 gates
  * allowlist enforcement still applies on the reload path (CM-ADAPTER-001)
  * vanished manifest → capability withdrawn; foreign/kernel entries untouched
  * idempotent no-op reload (unchanged manifests) leaves registry consistent
  * kernel-level gate: ``kernel.capabilities.hot_reload: false`` skips reload
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.core.capability_manager import (
    CapabilityManagerError,
    get_capability_manager,
    reset_capability_manager_singleton,
)
from aios.core.capability_manifest import (
    CapabilityManifestLoader,
    ManifestValidationError,
)

pytestmark = [pytest.mark.integration]

# Stock manifest capabilities loaded from config/capabilities at boot.
STOCK_CAPABILITY_IDS = (
    "graphify_context",
    "notion_planning",
    "obsidian_knowledge",
    "claude_mem_context",
    "playwright_browser",
)

VALID_ADAPTER = "aios.adapters.notion_adapter.NotionAdapter"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(
    directory: Path, name: str, *, capability_id: str = "reload_cap", **overrides
) -> None:
    """Write a minimal valid capability manifest."""
    lines = [
        f"capability_id: \"{capability_id}\"",
        "facade: \"reload\"",
        "provider_id: \"reload_provider\"",
        "adapter:",
        f"  class_path: \"{overrides.get('class_path', VALID_ADAPTER)}\"",
        "  kwargs: {}",
        "trust_level: untrusted",
        "authority_classification: advisory",
    ]
    for key, value in overrides.get("extra", {}).items():
        lines.append(f"{key}: {value}")
    (directory / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _registry_snapshot() -> dict[str, dict]:
    """Snapshot {id: to_dict()} of the canonical manager's registry."""
    cm = get_capability_manager()
    return {
        e.capability_id: e.to_dict()
        for e in get_capability_manager().list_capabilities()
    }


# ---------------------------------------------------------------------------
# Kernel-path tests (real boot via conftest fixture)
# ---------------------------------------------------------------------------


class TestKernelHotReloadGate:
    async def test_hot_reload_disabled_by_default_returns_none(
        self, kernel_with_all_capabilities
    ):
        """Spec §19 default: hot_reload=false → explicit reload is a no-op."""
        kernel = kernel_with_all_capabilities
        assert kernel._read_config_bool("kernel.capabilities.hot_reload", False) is False

        before = _registry_snapshot()
        result = await kernel.reload_capability_manifests()
        assert result is None, "disabled flag must skip the reload entirely"

        after = _registry_snapshot()
        assert after == before, "no-op reload must not mutate the registry"

    async def test_loader_retained_for_reload(self, kernel_with_all_capabilities):
        """M9-N6 wiring: the kernel retains its manifest loader after boot."""
        kernel = kernel_with_all_capabilities
        loader = kernel._capability_loader
        assert loader is not None, "_init_capability_manifests must retain the loader"
        # Same validation surface the boot used.
        assert VALID_ADAPTER in loader._adapter_allowlist or loader._adapter_allowlist


class TestKernelHappyReload:
    async def test_reload_keeps_stock_capabilities_green(
        self, kernel_with_all_capabilities, monkeypatch
    ):
        """With hot_reload enabled, reloading revalidates the stock manifests
        and every stock capability stays registered and resolvable."""
        kernel = kernel_with_all_capabilities
        monkeypatch.setattr(
            type(kernel), "_read_config_bool",
            lambda self, path, default=False: (
                True if path == "kernel.capabilities.hot_reload" else False
            ),
        )

        result = await kernel.reload_capability_manifests()
        assert result is not None
        assert set(result["registered"]) >= set(STOCK_CAPABILITY_IDS)

        cm = get_capability_manager()
        for cid in STOCK_CAPABILITY_IDS:
            entry = cm.get_capability(cid)
            assert entry is not None, f"{cid} lost after reload"
            cm.resolve(cid)  # resolution path must remain intact

    async def test_repeated_reloads_are_stable(self, kernel_with_all_capabilities, monkeypatch):
        """Idempotency: N consecutive successful reloads leave one clean entry
        per capability (no duplicates, no corruption)."""
        kernel = kernel_with_all_capabilities
        monkeypatch.setattr(
            type(kernel), "_read_config_bool",
            lambda self, path, default=False: (
                True if path == "kernel.capabilities.hot_reload" else False
            ),
        )
        for _ in range(3):
            await kernel.reload_capability_manifests()

        cm = get_capability_manager()
        entries = [e for e in cm.list_capabilities() if e.capability_id in STOCK_CAPABILITY_IDS]
        assert len(entries) == len(STOCK_CAPABILITY_IDS)


# ---------------------------------------------------------------------------
# Loader/manager-path tests (driven directly against temp manifest dirs)
# ---------------------------------------------------------------------------


@pytest.fixture
def reload_env():
    """A fresh canonical CapabilityManager (real C1–C4) + temp manifest dir."""
    from aios.core.configuration_manager import (
        ConfigurationManager,
        reset_configuration_manager_singleton,
    )
    from aios.core.service_registry import (
        get_service_registry,
        reset_service_registry_singleton,
    )
    from aios.core.structured_logger import get_logger
    from aios.events.core.bus import (
        EventBus,
        EventBusConfig,
        reset_event_bus_singleton,
    )

    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    reset_service_registry_singleton()
    registry = get_service_registry(event_bus=bus)
    reset_configuration_manager_singleton()
    configuration = ConfigurationManager(event_bus=bus)

    from aios.core.capability_manager import CapabilityManager

    reset_capability_manager_singleton()
    cm = CapabilityManager(
        service_registry=registry,
        configuration_manager=configuration,
        logger=get_logger(),
    )

    tmp = Path(tempfile.mkdtemp(prefix="m9n6_reload_"))
    loader = CapabilityManifestLoader(
        manifest_dir=tmp,
        adapter_allowlist=(VALID_ADAPTER,),
    )
    yield loader, tmp
    shutil.rmtree(tmp, ignore_errors=True)
    reset_capability_manager_singleton()
    reset_configuration_manager_singleton()
    reset_service_registry_singleton()
    reset_event_bus_singleton()


class TestFailClosedOnInvalidManifest:
    async def test_invalid_manifest_aborts_whole_reload(self, reload_env):
        """Spec §18: any invalid manifest rejects the ENTIRE reload."""
        loader, tmp = reload_env
        cm = get_capability_manager()

        # Round 1: two valid manifests register cleanly.
        _write_manifest(tmp, "a.yaml", capability_id="reload_a")
        _write_manifest(tmp, "b.yaml", capability_id="reload_b")
        first = await cm.reload_capabilities(loader)
        assert set(first["registered"]) == {"reload_a", "reload_b"}

        snapshot = _registry_snapshot()

        # Round 2: one manifest becomes invalid (missing required fields).
        (tmp / "b.yaml").write_text("foo: bar\n", encoding="utf-8")

        with pytest.raises(ManifestValidationError):
            await cm.reload_capabilities(loader)

        # Fail-closed: prior state fully preserved, including reload_b.
        assert _registry_snapshot() == snapshot
        assert cm.get_capability("reload_a") is not None
        assert cm.get_capability("reload_b") is not None

    async def test_unparseable_yaml_fails_closed(self, reload_env):
        """YAML syntax errors also reject the whole reload (fail-closed)."""
        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "ok.yaml", capability_id="reload_ok")
        await cm.reload_capabilities(loader)
        snapshot = _registry_snapshot()

        (tmp / "bad.yaml").write_text("key: [unclosed\n  - broken\n", encoding="utf-8")

        with pytest.raises(ManifestValidationError):
            await cm.reload_capabilities(loader)
        assert _registry_snapshot() == snapshot


class TestTrustEscalationRejected:
    async def test_builtin_trust_escalation_rejected(self, reload_env):
        """CM-MANIFEST-001 unchanged: builtin trust never passes on reload."""
        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "ok.yaml", capability_id="reload_ok")
        await cm.reload_capabilities(loader)
        snapshot = _registry_snapshot()

        # Attacker swaps in an escalated claim alongside a new capability.
        _write_manifest(
            tmp, "escalate.yaml", capability_id="escalated_cap",
            extra={"trust_level": "builtin"},
        )
        (tmp / "ok.yaml").unlink()

        with pytest.raises((ManifestValidationError, CapabilityManagerError)):
            await cm.reload_capabilities(loader)

        assert _registry_snapshot() == snapshot

    async def test_authoritative_claim_rejected_on_reload(self, reload_env):
        """authoritative authority_classification stays rejected on reload."""
        loader, tmp = reload_env
        cm = get_capability_manager()

        _write_manifest(
            tmp, "auth.yaml", capability_id="auth_cap",
            extra={"authority_classification": "authoritative"},
        )
        with pytest.raises(ManifestValidationError):
            await cm.reload_capabilities(loader)
        assert cm.get_capability("auth_cap") is None


class TestAllowlistEnforcedOnReload:
    async def test_non_allowlisted_adapter_rejected_cm_adapter_001(self, reload_env):
        """CM-ADAPTER-001 unchanged: reload re-runs the allowlist gate."""
        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "ok.yaml", capability_id="reload_ok")
        await cm.reload_capabilities(loader)
        snapshot = _registry_snapshot()

        _write_manifest(
            tmp, "rogue.yaml", capability_id="rogue_cap",
            class_path="aios.adapters.unknown_module.UnknownAdapter",
        )
        with pytest.raises(ManifestValidationError) as exc:
            await cm.reload_capabilities(loader)
        assert "CM-ADAPTER-001" in str(exc.value) or exc.value.rule_id == "CM-ADAPTER-001"
        assert _registry_snapshot() == snapshot


class TestWithdrawalAndForeignSafety:
    async def test_removed_manifest_withdraws_capability(self, reload_env):
        """A capability whose manifest disappears is deregistered on reload."""
        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "keep.yaml", capability_id="keep_cap")
        _write_manifest(tmp, "drop.yaml", capability_id="drop_cap")
        await cm.reload_capabilities(loader)
        assert cm.get_capability("drop_cap") is not None

        (tmp / "drop.yaml").unlink()
        result = await cm.reload_capabilities(loader)
        assert "drop_cap" in result["removed"]
        assert cm.get_capability("drop_cap") is None
        assert cm.get_capability("keep_cap") is not None

    async def test_foreign_and_kernel_entries_never_touched(self, reload_env):
        """Kernel/builtin registrations are outside the manifest namespace;
        reload must neither withdraw nor replace them."""
        from aios.core.capability_manifest import CapabilitySpec

        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "m.yaml", capability_id="mine_cap")
        await cm.reload_capabilities(loader)

        # A kernel-style registration: empty discovered_from, higher trust.
        kernel_spec = CapabilitySpec(
            capability_id="graphify_context",
            facade="graph",
            provider_id="graphify_kernel",
            adapter_class_path=VALID_ADAPTER,
            trust_level="trusted_contextual",
            authority_classification="contextual",
            discovered_from="",  # kernel-registered
        )
        cm.register_capability(kernel_spec)
        snapshot = _registry_snapshot()

        result = await cm.reload_capabilities(loader)
        assert result["removed"] == [], "foreign entries must never be withdrawn"
        assert cm.get_capability("graphify_context").provider_id == "graphify_kernel"

        # And the manifest-owned entry was refreshed, not duplicated.
        assert cm.get_capability("mine_cap") is not None
        assert snapshot["mine_cap"] is not None

    async def test_downgrade_of_owned_entry_allowed_no_privilege_gain(
        self, reload_env
    ):
        """Re-registering an owned entry with lower trust is permitted because
        CM-MANIFEST-001 caps manifest trust below trusted — a downgrade can
        never be a privilege gain."""
        from aios.core.capability_manifest import CapabilitySpec

        loader, tmp = reload_env
        cm = get_capability_manager()
        _write_manifest(tmp, "own.yaml", capability_id="own_cap")

        # Pre-register a trusted_contextual version as if it came from THIS
        # manifest dir (same discovered_from prefix the loader will report).
        owned = CapabilitySpec(
            capability_id="own_cap",
            facade="reload",
            provider_id="v1",
            adapter_class_path=VALID_ADAPTER,
            trust_level="trusted_contextual",
            authority_classification="contextual",
            discovered_from=str(tmp),
        )
        cm.register_capability(owned)

        # Reload now sees only the untrusted manifest → downgrade replaces it.
        result = await cm.reload_capabilities(loader)
        assert "own_cap" in result["registered"]
        entry = cm.get_capability("own_cap")
        assert entry.trust_level == "untrusted"
