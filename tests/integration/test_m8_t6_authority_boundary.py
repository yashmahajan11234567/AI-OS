"""
M8-T6 — Authority-Boundary Validation (spec §10).

Asserts the six external-capability adapters CANNOT exercise verdict
authority. Each A-x below is one independent test:

  A-1  No adapter can PASS/FAIL a test (verdict reserved to Council/
       FinalJudgeAgency).
  A-2  No adapter emits approve/reject language in result dicts.
  A-3  Adapters cannot override Council/Judge — they never set a
       "verdict" provenance key.
  A-4  (cross-cutting import-seam) No adapter imports any
       decision-authority module (security_manager / state / workflow /
       council / testing / ai_agency).
  A-5  Injecting authority="authoritative" provenance is overwritten.
  A-6  Spoofing trust_level="builtin" provenance is overwritten.
  A-7  SecurityManager.authorize fail-closed (None/"" -> DENY) and
       validate_capability_spec rejects builtin/trusted/authoritative.
  A-8  Capability shadowing (lower-trust displacing trusted) is blocked
       (CM-SHADOW-001).

Spec boundary (§17/§25): NO production source is modified. These tests
reuse the shared conftest fixtures only. Hermetic.

Markers: integration (split-authority surface), security (authority/
provenance guarantees).
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter
from aios.adapters.hermes_bridge import HermesBridge
from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter

from tests.integration.conftest import build_attacker_provenance

pytestmark = [pytest.mark.integration, pytest.mark.security]


# ---------------------------------------------------------------------------
# Adapter inventory under test
# ---------------------------------------------------------------------------

_ADAPTER_MODULES = {
    "hermes_bridge": "aios.adapters.hermes_bridge",
    "playwright_mcp_adapter": "aios.adapters.playwright_mcp_adapter",
    "graphify_adapter": "aios.adapters.graphify_adapter",
    "notion_adapter": "aios.adapters.notion_adapter",
    "obsidian_adapter": "aios.adapters.obsidian_adapter",
    "claude_mem_adapter": "aios.adapters.claude_mem_adapter",
    "architecture_agency_adapter": "aios.adapters.architecture_agency_adapter",
}

_VERDICT_METHODS = ("issue_verdict", "adjudicate", "render_verdict", "vote")

# Forbidden decision-authority module tokens (A-4). Matched as import
# targets only — `aios.core.mcp_manager` and `aios.core.capability_*`
# are explicitly allowed.
_FORBIDDEN_IMPORT_TOKENS = (
    r"security_manager",
    r"aios\.core\.state\b",
    r"core\.state\b",
    r"aios\.core\.workflow\b",
    r"core\.workflow\b",
    r"council_manager",
    r"services\.testing\b",
    r"core\.testing\b",
    r"ai_agency",
)


def _build_adapters():
    """Instantiate every external adapter directly (no connection needed)."""
    return {
        "graphify": GraphifyAdapter(),
        "notion": NotionAdapter(),
        "obsidian": ObsidianAdapter(),
        "claude_mem": ClaudeMemAdapter(),
        "hermes": HermesBridge(),
        "playwright": PlaywrightMCPAdapter(),
    }


# ---------------------------------------------------------------------------
# A-1 — No adapter may hold verdict authority
# ---------------------------------------------------------------------------


def test_a1_adapters_have_no_verdict_methods():
    """No adapter exposes issue_verdict/adjudicate/render_verdict/vote."""
    adapters = _build_adapters()
    for name, adapter in adapters.items():
        for method in _VERDICT_METHODS:
            assert not hasattr(adapter, method), (
                f"{name} adapter MUST NOT carry verdict authority "
                f"(found forbidden method '{method}')"
            )


def test_a1_verdict_authority_lives_in_final_judge():
    """Verdict authority is reserved to FinalJudgeAgency.review."""
    from aios.core.ai_agency import FinalJudgeAgency

    assert hasattr(FinalJudgeAgency, "review"), (
        "Verdict authority must live in FinalJudgeAgency.review"
    )
    # The adapter layer must NOT shadow/duplicate it.
    adapters = _build_adapters()
    for name, adapter in adapters.items():
        assert not hasattr(adapter, "review"), (
            f"{name} adapter must not redefine FinalJudgeAgency.review"
        )


# ---------------------------------------------------------------------------
# A-2 — No approve/reject language in adapter result dicts
# ---------------------------------------------------------------------------


def test_a2_no_approve_reject_verdict_tokens_in_source():
    """Adapter module sources never emit approve/reject/verdict result keys."""
    pattern = re.compile(r'["\'](verdict|approved|rejected)["\']')
    for label, modname in _ADAPTER_MODULES.items():
        module = importlib.import_module(modname)
        src_path = inspect.getsourcefile(module)
        assert src_path is not None, f"cannot locate source for {modname}"
        source = Path(src_path).read_text(encoding="utf-8")
        matches = pattern.findall(source)
        assert not matches, (
            f"{label} adapter source MUST NOT contain approve/reject/verdict "
            f"result keys (found: {matches})"
        )


# ---------------------------------------------------------------------------
# A-3 — Adapters never set a "verdict" provenance key
# ---------------------------------------------------------------------------


def test_a3_adapters_set_no_verdict_provenance_key():
    """Advisory-marked provenance carries no builder-origin verdict key."""
    adapters = _build_adapters()
    attacker = build_attacker_provenance()
    for name, adapter in adapters.items():
        if not hasattr(adapter, "_mark_advisory"):
            continue
        try:
            result = adapter._mark_advisory({"provenance": dict(attacker)})
        except TypeError:
            result = adapter._mark_advisory(
                {"provenance": dict(attacker)}, operation="external_read"
            )
        provenance = result.get("provenance", {})
        assert "verdict" not in provenance, (
            f"{name} adapter provenance MUST NOT carry a 'verdict' key "
            f"(builder-exclusion enforced at TestOrchestratorService)"
        )


# ---------------------------------------------------------------------------
# A-4 — cross-cutting import-seam test
# ---------------------------------------------------------------------------


# Adapters explicitly allowed to import security_manager for gate-before-connect
# (Terminal 2 S1/S2: ACP and Playwright must route through SecurityManager).
_AUTHORIZED_SECURITY_IMPORTS = frozenset({"playwright_mcp_adapter", "acp_adapter"})


def test_a4_adapters_import_no_decision_authority_modules():
    """No M8 adapter imports security_manager/state/workflow/council/testing/ai_agency,
    except adapters explicitly authorized for gate-before-connect (Terminal 2 S1/S2)."""
    bad_import = re.compile(
        r"^\s*(import|from)\s+([\w\.]+)", re.MULTILINE
    )
    for label, modname in _ADAPTER_MODULES.items():
        module = importlib.import_module(modname)
        src_path = inspect.getsourcefile(module)
        assert src_path is not None, f"cannot locate source for {modname}"
        source = Path(src_path).read_text(encoding="utf-8")
        for line in source.splitlines():
            m = bad_import.match(line)
            if not m:
                continue
            target = m.group(2)
            for token in _FORBIDDEN_IMPORT_TOKENS:
                if re.search(token, target):
                    # Allow known authorized exceptions (gate-before-connect).
                    if label in _AUTHORIZED_SECURITY_IMPORTS and token == r"security_manager":
                        continue
                    assert False, (
                        f"{label} adapter MUST NOT import decision-authority module "
                        f"matching /{token}/ (import line: '{line.strip()}')"
                    )


# ---------------------------------------------------------------------------
# A-5 — injected authority="authoritative" is overwritten
# ---------------------------------------------------------------------------


def test_a5_injected_authoritative_overwritten():
    """_mark_advisory overwrites an attacker authority='authoritative' claim."""
    for adapter in (GraphifyAdapter(), NotionAdapter(),
                    ObsidianAdapter(), ClaudeMemAdapter()):
        attacker = build_attacker_provenance(authority="authoritative")
        try:
            result = adapter._mark_advisory({"provenance": dict(attacker)})
        except TypeError:
            result = adapter._mark_advisory(
                {"provenance": dict(attacker)}, operation="external_read"
            )
        prov = result.get("provenance", {})
        assert prov.get("advisory") is True, (
            "advisory MUST be re-asserted True"
        )
        assert prov.get("authority") != "authoritative", (
            "attacker authority='authoritative' MUST be overwritten "
            f"(got {prov.get('authority')!r})"
        )
        assert prov.get("authority") in ("advisory_only", "contextual"), (
            f"authority must be demoted to advisory_only/contextual "
            f"(got {prov.get('authority')!r})"
        )


# ---------------------------------------------------------------------------
# A-6 — spoofed trust_level="builtin" is overwritten
# ---------------------------------------------------------------------------


def test_a6_spoofed_builtin_trust_overwritten():
    """An attacker trust_level='builtin' claim is overwritten (advisory demotion)."""
    from aios.core.capability_provenance import mark_capability_advisory

    # Adapters that self-set trust_level must overwrite the spoofed value.
    self_setting = {
        "notion": NotionAdapter(),
        "obsidian": ObsidianAdapter(),
        "claude_mem": ClaudeMemAdapter(),
    }
    for name, adapter in self_setting.items():
        attacker = build_attacker_provenance(trust_level="builtin")
        result = adapter._mark_advisory(
            {"provenance": dict(attacker)}, operation="external_read"
        )
        prov = result.get("provenance", {})
        assert prov.get("trust_level") != "builtin", (
            f"{name} adapter MUST overwrite spoofed trust_level='builtin' "
            f"(got {prov.get('trust_level')!r})"
        )

    # The C14 gate force-demotes any externally-sourced provenance to
    # untrusted regardless of the adapter's own marking (spoof resistance).
    for adapter in (GraphifyAdapter(), NotionAdapter(),
                    ObsidianAdapter(), ClaudeMemAdapter()):
        attacker = build_attacker_provenance(trust_level="builtin")
        try:
            result = adapter._mark_advisory({"provenance": dict(attacker)})
        except TypeError:
            result = adapter._mark_advisory(
                {"provenance": dict(attacker)}, operation="external_read"
            )
        marked = mark_capability_advisory(
            dict(result), source="ext_source"
        )
        marked_prov = marked.get("provenance", {})
        assert marked_prov.get("trust_level") != "builtin", (
            "mark_capability_advisory C14 gate MUST NOT preserve builtin trust"
        )
        assert marked_prov.get("trust_level") == "untrusted", (
            "C14 gate MUST demote external trust_level to 'untrusted' "
            f"(got {marked_prov.get('trust_level')!r})"
        )


# ---------------------------------------------------------------------------
# A-7 — SecurityManager fail-closed + spec validation
# ---------------------------------------------------------------------------


async def test_a7_authorize_fail_closed_and_spec_rejects_escalation(kernel_with_all_capabilities):
    """authorize(None/'') -> DENY; validate_capability_spec rejects escalation."""
    from aios.core.security_manager import (
        SecurityDecision,
        get_security_manager,
    )
    from aios.core.capability_manifest import (
        AuthorityClassification,
        CapabilitySpec,
        TrustLevel,
    )

    sm = get_security_manager()

    # Fail-closed: anonymous / empty principal cannot be allowed.
    assert sm.authorize(None, "read", "x") == SecurityDecision.DENY
    assert sm.authorize("", "read", "x") == SecurityDecision.DENY

    # validate_capability_spec rejects builtin/trusted/authoritative claims (C-5).
    spec = CapabilitySpec(
        capability_id="ext.test_shadow",
        facade="external",
        provider_id="external",
        adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
        trust_level=TrustLevel.BUILTIN,
        authority_classification=AuthorityClassification.AUTHORITATIVE,
        discovered_from="integration-test",
    )
    result = sm.validate_capability_spec(spec)
    gate_passed = getattr(result, "passed", None)
    if gate_passed is None:
        gate_passed = getattr(result, "valid", result)
    assert not gate_passed, (
        "validate_capability_spec MUST reject builtin+authoritative spec (C-5)"
    )


# ---------------------------------------------------------------------------
# A-8 — capability shadowing blocked (CM-SHADOW-001)
# ---------------------------------------------------------------------------


async def test_a8_lower_trust_shadow_of_trusted_blocked(kernel_with_all_capabilities):
    """Registering a lower-trust cap over a trusted one raises CM-SHADOW-001."""
    from aios.core.capability_manager import CapabilityManagerError
    from aios.core.capability_manifest import (
        AuthorityClassification,
        CapabilitySpec,
        TrustLevel,
    )
    from aios.core.capability_manager import get_capability_manager

    cm = get_capability_manager()
    cap_id = "ext.shadow_block"

    trusted = CapabilitySpec(
        capability_id=cap_id,
        facade="external",
        provider_id="external",
        adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
        trust_level=TrustLevel.TRUSTED_CONTEXTUAL,
        authority_classification=AuthorityClassification.CONTEXTUAL,
        discovered_from="integration-test",
    )
    cm.register_capability(trusted)

    untrusted = CapabilitySpec(
        capability_id=cap_id,
        facade="external",
        provider_id="external",
        adapter_class_path="aios.adapters.notion_adapter.NotionAdapter",
        trust_level=TrustLevel.UNTRUSTED,
        authority_classification=AuthorityClassification.ADVISORY,
        discovered_from="integration-test",
    )
    with pytest.raises(CapabilityManagerError) as exc:
        cm.register_capability(untrusted)
    assert exc.value.rule_id == "CM-SHADOW-001", (
        f"lower-trust shadow MUST raise CM-SHADOW-001 (got {exc.value.rule_id})"
    )
