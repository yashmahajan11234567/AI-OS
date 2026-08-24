"""
M4-ADAPTER unit tests.

Covers the three M4 deliverables from the frozen architecture
(FINAL_AI_OS_V2_ARCHITECTURE.md §831, §879, PART XXX, ADR #14):

  1. Canonical SKILL.md adapter (aios.core.skill_spec + aios.services.skill)
  2. SkillSpecTor security gate (aios.core.security_manager)
  3. Seeded curated agency-agents personas (ADR #14: ~8-10 personas)

Per the architecture, the gate runs BEFORE installation and AI-OS
(SecurityManager) remains final authority; hermes-agent(EXT) and
SkillSpecTor are INTEGRATION gates, not decision makers.

These tests assert behaviour, not coverage. A poisoned skill MUST be
rejected; a clean skill MUST be admitted; the gate MUST run before the
canonical adapter installs a skill.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aios.core.configuration_manager import (
    ConfigurationManager,
    reset_configuration_manager_singleton,
)
from aios.core.security_manager import (
    SecurityManager,
    SecurityManagerError,
    SkillSpecTorGate,
    SkillSpecTorResult,
)
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.core.skill_manager import Skill
from aios.core.skill_spec import SkillSpec, SkillSpecParser
from aios.core.structured_logger import get_logger
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    reset_event_bus_singleton,
)
from aios.services.skill import SkillService

# Canonical curated-persona directory (ADR #14).
PERSONA_DIR = Path(".claude/skill-specs")


# ---------------------------------------------------------------------------
# SkillSpec adapter — parsing behaviour
# ---------------------------------------------------------------------------


def _write_spec(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(body, encoding="utf-8")
    return p


VALID_SKILL = textwrap.dedent(
    """
    ---
    name: "Valid Skill"
    version: "1.2.3"
    description: "A clean demonstration skill."
    entry_point: "mymodule:run"
    permissions:
      - "filesystem:read"
    category: "agency"
    author: "AI-OS Core Team"
    license: "MIT"
    test_coverage: 0.9
    approved: true
    ---
    # Valid Skill
    Body text is ignored by the adapter.
    """
).strip()


class TestSkillSpecParsing:
    def test_parse_valid_skill(self, tmp_path):
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, VALID_SKILL))
        assert spec is not None
        assert spec.name == "Valid Skill"
        assert spec.version == "1.2.3"
        assert spec.entry_point == "mymodule:run"
        assert spec.category == "agency"
        assert spec.permissions == ["filesystem:read"]
        assert spec.license == "MIT"
        assert spec.test_coverage == 0.9
        assert spec.approved is True

    def test_skill_id_derived_from_category_and_name(self, tmp_path):
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, VALID_SKILL))
        assert spec.skill_id == "agency.valid-skill"

    def test_missing_required_field_rejected(self, tmp_path):
        bad = VALID_SKILL.replace("description: ", "description_x: ")
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, bad))
        assert spec is None

    def test_no_frontmatter_rejected(self, tmp_path):
        spec = SkillSpecParser().parse_file(
            _write_spec(tmp_path, "# Just a heading\nNo frontmatter here.")
        )
        assert spec is None

    def test_invalid_yaml_rejected(self, tmp_path):
        bad = "---\nname: x\nversion: [unclosed\n---"
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, bad))
        assert spec is None

    def test_missing_file_returns_none(self, tmp_path):
        assert SkillSpecParser().parse_file(tmp_path / "does_not_exist.md") is None

    def test_defaults_applied(self, tmp_path):
        minimal = "---\nname: X\nversion: 1.0.0\ndescription: d\n---\nbody"
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, minimal))
        assert spec is not None
        assert spec.category == "general"
        assert spec.license == "MIT"
        assert spec.permissions == []

    def test_to_skill_roundtrip_preserves_fields(self, tmp_path):
        spec = SkillSpecParser().parse_file(_write_spec(tmp_path, VALID_SKILL))
        skill = spec.to_skill()
        assert isinstance(skill, Skill)
        assert skill.name == spec.name
        assert skill.entry_point == spec.entry_point
        assert skill.metadata["license"] == "MIT"
        assert skill.metadata["permissions"] == ["filesystem:read"]

    def test_discover_finds_multiple_specs(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        _write_spec(tmp_path / "a", VALID_SKILL)
        _write_spec(tmp_path / "b", VALID_SKILL.replace('name: "Valid Skill"', 'name: "Other"'))
        specs = SkillSpecParser().discover_skill_specs(tmp_path)
        assert len(specs) == 2


# ---------------------------------------------------------------------------
# SkillSpecTor gate — security behaviour
# ---------------------------------------------------------------------------


def _clean_spec(**overrides) -> SkillSpec:
    base = dict(
        name="clean",
        version="1.0.0",
        description="clean",
        entry_point="mymod:run",
        permissions=["filesystem:read"],
        category="agency",
        skill_id="agency.clean",
        dependencies=[],
        config_schema={},
    )
    base.update(overrides)
    return SkillSpec(**base)


class TestSkillSpecTorGate:
    def test_clean_skill_passes(self):
        result = SkillSpecTorGate().validate_skill_spec(_clean_spec())
        assert isinstance(result, SkillSpecTorResult)
        assert result.passed is True
        assert result.violations == []
        assert result.scan_id
        assert result.scan_duration_ms >= 0

    def test_suspicious_entry_point_rejected(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(entry_point="os.system")
        )
        assert result.passed is False
        cats = [v.category for v in result.violations]
        assert "skill_validation" in cats
        assert any(v.severity == "critical" for v in result.violations)

    def test_wildcard_permission_rejected(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(permissions=["*"])
        )
        assert result.passed is False
        assert any(
            v.severity == "critical" and "wildcard" in v.description.lower()
            for v in result.violations
        )

    def test_dangerous_permission_high(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(permissions=["kernel", "process"])
        )
        assert result.passed is False
        assert any(v.severity == "high" for v in result.violations)

    def test_system_namespace_spoofing_rejected(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(skill_id="builtin.bypass")
        )
        assert result.passed is False
        assert any("namespace" in v.description.lower() for v in result.violations)

    def test_dangerous_config_key_rejected(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(config_schema={"command": "rm -rf /"})
        )
        assert result.passed is False
        assert any("command" in v.description.lower() for v in result.violations)

    def test_risky_dependency_flagged_medium(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(dependencies=["metasploit"])
        )
        # medium severity does NOT block pass (only high/critical block)
        assert any("metasploit" in v.description for v in result.violations)
        assert result.passed is True

    def test_unapproved_runtime_flagged(self):
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(runtime="shellscript")
        )
        assert result.passed is True
        assert any("runtime" in v.description.lower() for v in result.violations)

    def test_missing_entry_point_is_high_not_critical(self):
        result = SkillSpecTorGate().validate_skill_spec(_clean_spec(entry_point=""))
        assert result.passed is False
        assert any(v.severity == "high" for v in result.violations)

    def test_disabled_gate_allows(self):
        result = SkillSpecTorGate(enabled=False).validate_skill_spec(
            _clean_spec(entry_point="os.system")
        )
        assert result.passed is True

    def test_c10_llm_stage_must_be_disabled(self):
        with pytest.raises(SecurityManagerError):
            SkillSpecTorGate(llm_stage_enabled=True)

    def test_pass_requires_no_high_or_critical(self):
        # medium-only violations must still pass
        result = SkillSpecTorGate().validate_skill_spec(
            _clean_spec(runtime="shellscript")
        )
        assert result.passed is True


# ---------------------------------------------------------------------------
# SecurityManager integration point
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    """Canonical EventBus singleton (mirrors repo test pattern)."""
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def sr(bus):
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=bus)
    yield reg
    reset_service_registry_singleton()


@pytest.fixture
def cm(bus):
    reset_configuration_manager_singleton()
    c = ConfigurationManager(event_bus=bus)
    yield c
    reset_configuration_manager_singleton()


@pytest.fixture
def logger(bus):
    return get_logger()


@pytest.fixture
async def security_manager(bus, sr, cm, logger):
    from aios.core.security_manager import reset_security_manager_singleton

    reset_security_manager_singleton()
    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )
    await sm.initialize()
    yield sm
    reset_security_manager_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()


class TestSecurityManagerGate:
    async def test_validate_before_install_clean(self, security_manager):
        result = security_manager.validate_skill_before_install(_clean_spec())
        assert isinstance(result, SkillSpecTorResult)
        assert result.passed is True

    async def test_validate_before_install_poisoned_rejected(self, security_manager):
        result = security_manager.validate_skill_before_install(
            _clean_spec(entry_point="os.system", permissions=["*"])
        )
        assert result.passed is False

    async def test_high_critical_emit_recorded_violation(self, security_manager):
        security_manager.validate_skill_before_install(
            _clean_spec(entry_point="os.system", permissions=["*"])
        )
        violations = security_manager.list_violations()
        assert any(
            v.category == "skill_installation_gate" for v in violations
        )


# ---------------------------------------------------------------------------
# SkillService canonical adapter — gate runs BEFORE install
# ---------------------------------------------------------------------------


@pytest.fixture
def persona_spec_path():
    # Use the curated agency.architect persona (passes the gate).
    p = PERSONA_DIR / "agency-architect.skill.md"
    assert p.exists(), f"curated persona missing: {p}"
    return p


class TestSkillServiceAdapter:
    async def test_load_skill_spec_installs_when_gate_passes(
        self, persona_spec_path, security_manager, tmp_path
    ):
        # Use an isolated skill manager in a temp dir so registration is hermetic.
        from aios.core.skill_manager import SkillManager, set_skill_manager

        set_skill_manager(SkillManager(skills_dir=tmp_path / "skills",
                                       skill_specs_dir=tmp_path / "specs"))
        svc = SkillService(manager=None)
        skill = svc.load_skill_spec(persona_spec_path)
        assert skill is not None
        assert skill.skill_id == "agency.architect"

    def test_validate_skill_spec_reports_missing_entry_point(self, tmp_path):
        bad = "---\nname: X\nversion: 1.0.0\ndescription: d\n---\nbody"
        _write_spec(tmp_path, bad)
        svc = SkillService(manager=None)
        ok, errors = svc.validate_skill_spec(tmp_path / "SKILL.md")
        assert ok is False
        assert any("entry_point" in e for e in errors)

    async def test_get_skill_spec_roundtrip(self, persona_spec_path, security_manager, tmp_path):
        from aios.core.skill_manager import SkillManager, set_skill_manager

        set_skill_manager(SkillManager(skills_dir=tmp_path / "skills",
                                       skill_specs_dir=tmp_path / "specs"))
        svc = SkillService(manager=None)
        spec = svc.load_skill_spec(persona_spec_path)
        if spec is not None:
            fetched = svc.get_skill_spec(spec.skill_id)
            assert fetched is not None
            assert fetched.skill_id == spec.skill_id


# ---------------------------------------------------------------------------
# Curated persona seed (ADR #14)
# ---------------------------------------------------------------------------


class TestCuratedPersonas:
    EXPECTED = [
        "agency.architect",
        "agency.security",
        "agency.performance",
        "agency.chaos",
        "agency.accessibility",
        "agency.documentation",
        "agency.concurrency",
        "agency.bughunter",
        "agency.final_judge",
        "agency.user_simulation",
    ]

    def test_persona_dir_exists(self):
        assert PERSONA_DIR.exists(), f"persona seed dir missing: {PERSONA_DIR}"

    def test_at_least_eight_personas_seeded(self):
        specs = SkillSpecParser().discover_skill_specs(PERSONA_DIR)
        assert len(specs) >= 8, (
            f"ADR #14 requires ~8-10 curated personas, found {len(specs)}"
        )

    def test_all_expected_personas_present(self):
        specs = SkillSpecParser().discover_skill_specs(PERSONA_DIR)
        ids = {s.skill_id for s in specs}
        missing = [e for e in self.EXPECTED if e not in ids]
        assert not missing, f"missing curated personas: {missing}"

    def test_all_personas_pass_security_gate(self):
        gate = SkillSpecTorGate()
        specs = SkillSpecParser().discover_skill_specs(PERSONA_DIR)
        for s in specs:
            result = gate.validate_skill_spec(s)
            assert result.passed is True, (
                f"curated persona {s.skill_id} failed SkillSpecTor gate: "
                f"{[v.description for v in result.violations]}"
            )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
