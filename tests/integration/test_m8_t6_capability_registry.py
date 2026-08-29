"""
M8-T6 — Capability-Registry Validation (spec §11, C-1..C-9).

Exercises the T5 capability-registry hardening flow with dynamically loaded
capabilities alongside the kernel-built adapters — without kernel-specific
branching. Covers the spec §11 assertions C-1 through C-9:

  * C-1  All 5 manifest capabilities load & register on a booted kernel.
  * C-2  A malformed manifest is skipped (loader skip-not-raise); boot continues.
  * C-3  Path traversal in adapter class_path -> CM-ADAPTER-001 rejected.
  * C-4  Non-allowlisted adapter -> CM-ADAPTER-001 rejected.
  * C-5  Capability claiming builtin trust / authoritative -> CM-MANIFEST-001 /
         CM-SEC-001 rejected.
  * C-6  Lower-trust shadow of a trusted registration -> CM-SHADOW-001 blocked.
  * C-7  Sensitive-key payload -> CM-SEC-002 denied (fail-closed).
  * C-8  Dynamically loaded capability coexists (same registry) with the 5
         kernel-built adapters (no special-casing).
  * C-9  Double-registration collision (equal precedence) resolves by
         precedence and keeps a single, uncorrupted registry entry.

Spec boundary (§17/§25): NO production source is modified. These tests reuse
the shared conftest fixtures only. Hermetic — no real network.

Markers: ``integration``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.core.capability_manifest import (
    CapabilitySpec,
    CapabilityManifestLoader,
    ManifestValidationError,
    AuthorityClassification,
    TrustLevel,
)
from aios.core.capability_manager import (
    CapabilityManagerError,
    get_capability_manager,
)

pytestmark = [pytest.mark.integration]

# The 5 kernel-built manifest capabilities (config/capabilities/*.yaml).
MANIFEST_CAPABILITY_IDS = (
    "graphify_context",
    "notion_planning",
    "obsidian_knowledge",
    "claude_mem_context",
    "playwright_browser",
)

# A valid, allowlisted adapter class path used by the standalone loader tests
# and the dynamically-registered specs (the security gate only requires a
# non-empty class_path; allowlist is enforced at instantiation time, not here).
SAMPLE_ADAPTER_PATH = "aios.adapters.notion_adapter.NotionAdapter"


# ---------------------------------------------------------------------------
# C-1: All 5 manifest capabilities load & register on a booted kernel.
# ---------------------------------------------------------------------------


async def test_c1_all_five_manifest_capabilities_load(kernel_with_all_capabilities):
    """C-1: the booted kernel registers all 5 manifest capabilities."""
    cm = get_capability_manager()
    for cid in MANIFEST_CAPABILITY_IDS:
        entry = cm.get_capability(cid)
        assert entry is not None, f"capability '{cid}' not registered on boot"
        assert entry.capability_id == cid
        # Manifest capabilities are registered as trusted_contextual via the
        # non-auto-trust default.
        assert entry.trust_level == TrustLevel.TRUSTED_CONTEXTUAL


# ---------------------------------------------------------------------------
# C-2: A malformed manifest is skipped (loader skip-not-raise); valid ones load.
# ---------------------------------------------------------------------------


def test_c2_malformed_manifest_skipped_not_raised():
    """C-2: a malformed manifest is skipped and the valid one still loads."""
    with tempfile.TemporaryDirectory(prefix="m8t6_c2_") as tmp:
        tmp_path = Path(tmp)
        # Valid manifest (allowlisted adapter) — must load cleanly.
        (tmp_path / "valid.yaml").write_text(
            "capability_id: valid_cap\n"
            "facade: valid\n"
            "provider_id: valid_provider\n"
            "adapter:\n"
            f"  class_path: {SAMPLE_ADAPTER_PATH}\n"
            "  kwargs: {}\n"
            "trust_level: untrusted\n"
            "authority_classification: advisory\n",
            encoding="utf-8",
        )
        # Malformed manifest: parses as YAML but is missing required fields
        # (no adapter block) -> ManifestValidationError, must be skipped.
        (tmp_path / "broken.yaml").write_text(
            "foo: bar\nname: not-a-capability\n",
            encoding="utf-8",
        )

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=(SAMPLE_ADAPTER_PATH,),
        )

        # load_all must NOT raise; it skip-not-raises the malformed manifest.
        specs = loader.load_all()
        assert len(specs) == 1, "exactly the valid manifest should load"
        assert specs[0].capability_id == "valid_cap"

        # And loading the broken manifest directly raises (caught by load_all).
        with pytest.raises(ManifestValidationError):
            loader.load_manifest(tmp_path / "broken.yaml")


# ---------------------------------------------------------------------------
# C-3: Path traversal in adapter class_path -> CM-ADAPTER-001 rejected.
# ---------------------------------------------------------------------------


def test_c3_path_traversal_adapter_rejected():
    """C-3: path traversal in adapter class_path -> CM-ADAPTER-001."""
    with tempfile.TemporaryDirectory(prefix="m8t6_c3_") as tmp:
        tmp_path = Path(tmp)
        bad_path = "aios.adapters.evil..traversal.Attacker"
        (tmp_path / "evil.yaml").write_text(
            "capability_id: evil_cap\n"
            "facade: evil\n"
            "provider_id: evil_provider\n"
            "adapter:\n"
            f"  class_path: {bad_path}\n"
            "  kwargs: {}\n"
            "trust_level: untrusted\n"
            "authority_classification: advisory\n",
            encoding="utf-8",
        )

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=(bad_path,),
        )
        with pytest.raises(ManifestValidationError) as exc:
            loader.load_manifest(tmp_path / "evil.yaml")
        assert exc.value.rule_id == "CM-ADAPTER-001"


# ---------------------------------------------------------------------------
# C-4: Non-allowlisted adapter -> CM-ADAPTER-001 rejected.
# ---------------------------------------------------------------------------


def test_c4_non_allowlisted_adapter_rejected():
    """C-4: a non-allowlisted adapter class_path -> CM-ADAPTER-001."""
    with tempfile.TemporaryDirectory(prefix="m8t6_c4_") as tmp:
        tmp_path = Path(tmp)
        unknown_path = "aios.adapters.unknown_module.UnknownAdapter"
        (tmp_path / "unknown.yaml").write_text(
            "capability_id: unknown_cap\n"
            "facade: unknown\n"
            "provider_id: unknown_provider\n"
            "adapter:\n"
            f"  class_path: {unknown_path}\n"
            "  kwargs: {}\n"
            "trust_level: untrusted\n"
            "authority_classification: advisory\n",
            encoding="utf-8",
        )

        # Empty allowlist -> any adapter class_path is rejected.
        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=(),
        )
        with pytest.raises(ManifestValidationError) as exc:
            loader.load_manifest(tmp_path / "unknown.yaml")
        assert exc.value.rule_id == "CM-ADAPTER-001"


# ---------------------------------------------------------------------------
# C-5: builtin trust / authoritative classification -> CM-MANIFEST-001 / CM-SEC-001.
# ---------------------------------------------------------------------------


async def test_c5_builtin_or_authoritative_rejected(kernel_with_all_capabilities):
    """C-5: a spec claiming builtin trust or authoritative authority is rejected."""
    cm = get_capability_manager()
    sm = kernel_with_all_capabilities._security_manager
    assert sm is not None, "kernel must wire a SecurityManager into this test"

    # (a) builtin trust_level -> security gate reports failure (critical violation).
    builtin_spec = CapabilitySpec(
        capability_id="reject_builtin",
        facade="test",
        provider_id="test_provider",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.BUILTIN,
        authority_classification=AuthorityClassification.ADVISORY,
    )
    gate = sm.validate_capability_spec(builtin_spec)
    assert gate.passed is False, "builtin trust must fail the capability security gate"

    # register_capability routes through the gate -> CM-SEC-001.
    with pytest.raises(CapabilityManagerError) as exc:
        cm.register_capability(builtin_spec)
    assert exc.value.rule_id == "CM-SEC-001"

    # (b) authoritative authority_classification -> also rejected by the gate.
    authoritative_spec = CapabilitySpec(
        capability_id="reject_authoritative",
        facade="test",
        provider_id="test_provider",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.AUTHORITATIVE,
    )
    gate2 = sm.validate_capability_spec(authoritative_spec)
    assert gate2.passed is False, "authoritative classification must fail the gate"

    with pytest.raises(CapabilityManagerError) as exc2:
        cm.register_capability(authoritative_spec)
    assert exc2.value.rule_id == "CM-SEC-001"


# ---------------------------------------------------------------------------
# C-6: Lower-trust shadow of a trusted registration -> CM-SHADOW-001 blocked.
# ---------------------------------------------------------------------------


async def test_c6_lower_trust_shadow_blocked(kernel_with_all_capabilities):
    """C-6: an untrusted shadow of a trusted_contextual cap -> CM-SHADOW-001."""
    cm = get_capability_manager()

    # graphify_context is registered by the kernel at trusted_contextual (prec 2).
    existing = cm.get_capability("graphify_context")
    assert existing is not None
    assert existing.trust_level == TrustLevel.TRUSTED_CONTEXTUAL

    # Attempt to shadow it with a lower-trust (untrusted, prec 1) registration.
    shadow_spec = CapabilitySpec(
        capability_id="graphify_context",
        facade="graph",
        provider_id="evil",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
    )
    with pytest.raises(CapabilityManagerError) as exc:
        cm.register_capability(shadow_spec)
    assert exc.value.rule_id == "CM-SHADOW-001"

    # The trusted registration is still intact.
    still = cm.get_capability("graphify_context")
    assert still is not None
    assert still.trust_level == TrustLevel.TRUSTED_CONTEXTUAL
    assert still.provider_id != "evil"


# ---------------------------------------------------------------------------
# C-7: Sensitive-key payload -> CM-SEC-002 denied (fail-closed).
# ---------------------------------------------------------------------------


async def test_c7_sensitive_key_payload_denied(kernel_with_all_capabilities):
    """C-7: a payload carrying sensitive_keys -> CM-SEC-002 (fail-closed)."""
    cm = get_capability_manager()

    spec = CapabilitySpec(
        capability_id="sensitive_cap",
        facade="test",
        provider_id="test_provider",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
        sensitive_keys=("password", "token", "secret"),
    )
    entry = cm.register_capability(spec)
    assert entry is not None
    assert "password" in entry.security_context["sensitive_keys"]

    # A caller payload containing a sensitive key must be denied.
    with pytest.raises(CapabilityManagerError) as exc:
        cm.enforce_security_context(
            "sensitive_cap",
            caller_context={"payload": {"username": "a", "password": "hunter2"}},
        )
    assert exc.value.rule_id == "CM-SEC-002"

    # A benign payload is allowed (sanity check that the gate is precise).
    allowed = cm.enforce_security_context(
        "sensitive_cap",
        caller_context={"payload": {"username": "a", "query": "b"}},
    )
    assert allowed.capability_id == "sensitive_cap"


# ---------------------------------------------------------------------------
# C-8: Dynamically loaded capability coexists with the kernel-built adapters.
# ---------------------------------------------------------------------------


async def test_c8_dynamic_capability_coexists_with_builtins(kernel_with_all_capabilities):
    """C-8: a dynamically registered cap lives in the same registry as the 5."""
    cm = get_capability_manager()

    dynamic_spec = CapabilitySpec(
        capability_id="dynamic_cap",
        facade="dynamic",
        provider_id="dynamic_provider",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
        tags=("dynamic",),
    )
    cm.register_capability(dynamic_spec)
    cm.resolve("dynamic_cap")  # same resolution path as the builtins

    # The dynamic cap is registered alongside all 5 kernel-built capabilities.
    all_ids = {e.capability_id for e in cm.list_capabilities()}
    for cid in MANIFEST_CAPABILITY_IDS:
        assert cid in all_ids, f"kernel-built '{cid}' missing from registry"
    assert "dynamic_cap" in all_ids
    assert cm.get_capability("dynamic_cap") is not None


# ---------------------------------------------------------------------------
# C-9: Double-registration collision (equal precedence) -> CM-PREC-001, single entry.
# ---------------------------------------------------------------------------


async def test_c9_double_registration_collision_resolves(kernel_with_all_capabilities):
    """C-9: identical-ids at equal precedence -> CM-PREC-001; registry stays single."""
    cm = get_capability_manager()

    spec_v1 = CapabilitySpec(
        capability_id="collide_cap",
        facade="collide",
        provider_id="provider_one",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
    )
    first = cm.register_capability(spec_v1)
    assert first is not None
    assert first.adapter_binding.get("class_path") == SAMPLE_ADAPTER_PATH

    # Equal precedence (same trust_level + same version) -> first registrant wins.
    spec_v2 = CapabilitySpec(
        capability_id="collide_cap",
        facade="collide",
        provider_id="provider_two",
        adapter_class_path=SAMPLE_ADAPTER_PATH,
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
    )
    with pytest.raises(CapabilityManagerError) as exc:
        cm.register_capability(spec_v2)
    assert exc.value.rule_id == "CM-PREC-001"

    # The registry holds exactly ONE entry for the id, uncorrupted.
    assert cm.get_capability("collide_cap") is not None
    matches = [e for e in cm.list_capabilities() if e.capability_id == "collide_cap"]
    assert len(matches) == 1, "collision left a duplicate/duplicate-free single entry"
    assert matches[0].provider_id == "provider_one"
    assert matches[0].adapter_binding.get("class_path") == SAMPLE_ADAPTER_PATH
