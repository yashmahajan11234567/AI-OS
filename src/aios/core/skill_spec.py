"""
SKILL.md Specification Parser for AI-OS.

Implements the canonical Vercel Skills SKILL.md format for portable skill ingestion.
Per M4-ADAPTER requirements: canonical SKILL.md adapter in SkillService/SkillManager
for portable safe skill ingestion.
"""

from __future__ import annotations

import re
import yaml
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aios.core.skill_manager import Skill

logger = logging.getLogger(__name__)


@dataclass
class SkillSpec:
    """
    Parsed SKILL.md specification following Vercel Skills format.

    The SKIELD.md format consists of:
    - YAML frontmatter with metadata
    - Markdown body with description, usage, examples
    """

    # Required fields (per Vercel Skills spec)
    name: str
    version: str
    description: str

    # Optional metadata fields
    author: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""

    # Skill interface definition
    entry_point: str = ""  # Module:function format
    config_schema: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    # Execution requirements
    runtime: str = "python"  # python, node, wasm, etc.
    runtime_version: str = ">=3.10"
    permissions: list[str] = field(default_factory=list)  # filesystem, network, etc.

    # Quality attributes
    maturity: str = "alpha"  # alpha, beta, stable
    stability: str = "experimental"  # experimental, stable, deprecated
    test_coverage: float = 0.0

    # Governance
    approved: bool = False
    certifications: list[str] = field(default_factory=list)

    # Extended fields for AI-OS
    skill_id: str = ""
    source_path: str = ""
    parsed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_skill(self) -> "Skill":
        """Convert SkillSpec to internal Skill object."""
        # Import here to avoid circular import
        from aios.core.skill_manager import Skill

        skill_id = self.skill_id or f"{self.category}.{self.name.lower().replace(' ', '-').replace('_', '-')}"
        skill_id = re.sub(r'[^a-z0-9\.\-]', '', skill_id)

        return Skill(
            skill_id=skill_id,
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            category=self.category,
            entry_point=self.entry_point,
            config_schema=self.config_schema,
            dependencies=self.dependencies,
            tags=self.tags,
            metadata={
                "license": self.license,
                "homepage": self.homepage,
                "repository": self.repository,
                "runtime": self.runtime,
                "runtime_version": self.runtime_version,
                "permissions": self.permissions,
                "maturity": self.maturity,
                "stability": self.stability,
                "test_coverage": self.test_coverage,
                "approved": self.approved,
                "certifications": self.certifications,
                "source_path": self.source_path,
                "parsed_at": self.parsed_at.isoformat(),
            },
        )


class SkillSpecParser:
    """
    Parser for SKILL.md files following the Vercel Skills specification.

    Supports:
    - YAML frontmatter parsing
    - Markdown body extraction
    - Validation against required fields
    - Conversion to internal Skill objects
    """

    FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)

    REQUIRED_FIELDS = {"name", "version", "description"}

    def __init__(self):
        self._parsed_specs: dict[str, SkillSpec] = {}

    def parse_file(self, file_path: Path | str) -> SkillSpec | None:
        """Parse a SKILL.md file and return a SkillSpec."""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"SKILL.md file not found: {path}")
            return None

        try:
            content = path.read_text(encoding="utf-8")
            return self.parse_content(content, source_path=str(path))
        except Exception as e:
            logger.error(f"Failed to parse SKILL.md {path}: {e}")
            return None

    def parse_content(self, content: str, source_path: str = "") -> SkillSpec | None:
        """Parse SKILL.md content string."""
        # Extract frontmatter
        frontmatter_match = self.FRONTMATTER_PATTERN.match(content)
        if not frontmatter_match:
            logger.warning(f"No frontmatter found in SKILL.md: {source_path}")
            return None

        frontmatter_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():].strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML frontmatter in {source_path}: {e}")
            return None

        if not isinstance(frontmatter, dict):
            logger.error(f"Frontmatter must be a mapping in {source_path}")
            return None

        # Validate required fields
        missing = self.REQUIRED_FIELDS - set(frontmatter.keys())
        if missing:
            logger.error(f"Missing required fields in {source_path}: {missing}")
            return None

        # Create SkillSpec from frontmatter
        spec = SkillSpec(
            name=frontmatter.get("name", ""),
            version=frontmatter.get("version", ""),
            description=frontmatter.get("description", ""),
            author=frontmatter.get("author", ""),
            category=frontmatter.get("category", "general"),
            tags=frontmatter.get("tags", []) or [],
            license=frontmatter.get("license", "MIT"),
            homepage=frontmatter.get("homepage", ""),
            repository=frontmatter.get("repository", ""),
            entry_point=frontmatter.get("entry_point", ""),
            config_schema=frontmatter.get("config_schema", {}) or {},
            dependencies=frontmatter.get("dependencies", []) or [],
            runtime=frontmatter.get("runtime", "python"),
            runtime_version=frontmatter.get("runtime_version", ">=3.10"),
            permissions=frontmatter.get("permissions", []) or [],
            maturity=frontmatter.get("maturity", "alpha"),
            stability=frontmatter.get("stability", "experimental"),
            test_coverage=float(frontmatter.get("test_coverage", 0.0)),
            approved=frontmatter.get("approved", False),
            certifications=frontmatter.get("certifications", []) or [],
            source_path=source_path,
        )

        # Generate skill_id if not provided
        if "skill_id" in frontmatter:
            spec.skill_id = frontmatter["skill_id"]
        else:
            spec.skill_id = f"{spec.category}.{spec.name.lower().replace(' ', '-').replace('_', '-')}"
            spec.skill_id = re.sub(r'[^a-z0-9\.\-]', '', spec.skill_id)

        # Store parsed spec
        self._parsed_specs[spec.skill_id] = spec

        logger.info(f"Parsed SKILL.md: {spec.skill_id} v{spec.version}")
        return spec

    def discover_skill_specs(self, skills_dir: Path | str) -> list[SkillSpec]:
        """Discover and parse all SKILL.md files in a directory."""
        path = Path(skills_dir)
        if not path.exists():
            logger.warning(f"Skills directory not found: {path}")
            return []

        specs = []
        for skill_file in path.rglob("SKILL.md"):
            spec = self.parse_file(skill_file)
            if spec:
                specs.append(spec)

        # Also check for .skill.md files
        for skill_file in path.rglob("*.skill.md"):
            spec = self.parse_file(skill_file)
            if spec:
                specs.append(spec)

        logger.info(f"Discovered {len(specs)} SKILL.md specifications in {path}")
        return specs

    def get_spec(self, skill_id: str) -> SkillSpec | None:
        """Get a previously parsed spec by skill_id."""
        return self._parsed_specs.get(skill_id)


def parse_skill_spec(file_path: Path | str) -> SkillSpec | None:
    """Convenience function to parse a single SKILL.md file."""
    parser = SkillSpecParser()
    return parser.parse_file(file_path)


def discover_skill_specs(skills_dir: Path | str) -> list[SkillSpec]:
    """Convenience function to discover all SKILL.md files in a directory."""
    parser = SkillSpecParser()
    return parser.discover_skill_specs(skills_dir)


__all__ = [
    "SkillSpec",
    "SkillSpecParser",
    "parse_skill_spec",
    "discover_skill_specs",
]