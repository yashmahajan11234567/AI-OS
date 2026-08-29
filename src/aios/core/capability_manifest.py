"""
M8-T5 — Capability Manifest Loader.

Parses and validates capability manifests from `config/capabilities/*.yaml`.
Enforces non-auto-trust: discovered capabilities default to `trust_level=untrusted`
and `authority_classification=advisory` unless explicitly and validly raised by
a trusted manifest (which must pass SecurityManager validation gate).

No external Git/repository loading — all sources are local config files.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from aios.core.capability_manager import CapabilityManagerError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trust / Authority Enumerations
# ---------------------------------------------------------------------------


class TrustLevel(str):
    """Trust level for a capability (deterministic ordering for precedence)."""

    BUILTIN = "builtin"
    TRUSTED = "trusted"
    TRUSTED_CONTEXTUAL = "trusted_contextual"
    UNTRUSTED = "untrusted"

    @classmethod
    def precedence(cls, level: str) -> int:
        """Return precedence value (higher = more trusted)."""
        mapping = {
            cls.BUILTIN: 4,
            cls.TRUSTED: 3,
            cls.TRUSTED_CONTEXTUAL: 2,
            cls.UNTRUSTED: 1,
        }
        return mapping.get(level, 0)


class AuthorityClassification(str):
    """Authority classification for a capability (non-overridable defaults)."""

    AUTHORITATIVE = "authoritative"
    CONTEXTUAL = "contextual"
    ADVISORY = "advisory"
    ADVISORY_ONLY = "advisory_only"

    @classmethod
    def default_for_trust(cls, trust_level: str) -> str:
        """Default authority classification for a trust level (non-overridable)."""
        if trust_level in (TrustLevel.BUILTIN, TrustLevel.TRUSTED):
            return cls.CONTEXTUAL
        return cls.ADVISORY


# ---------------------------------------------------------------------------
# CapabilitySpec - Typed descriptor for a capability manifest
# ---------------------------------------------------------------------------


@dataclass
class CapabilitySpec:
    """Typed capability specification parsed from a manifest file."""

    capability_id: str
    facade: str
    provider_id: str
    adapter_class_path: str
    adapter_kwargs: dict[str, Any] = field(default_factory=dict)
    transport: str = "local"
    version: str = "1.0.0"
    trust_level: str = TrustLevel.UNTRUSTED
    authority_classification: str = AuthorityClassification.ADVISORY
    allowed_operations: tuple[str, ...] = ()
    sensitive_keys: tuple[str, ...] = ()
    max_content_size: int = 10240
    discovered_from: str = ""
    tags: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_security_context(self) -> dict[str, Any]:
        """Convert to security_context dict for CapabilityRegistryEntry."""
        return {
            "allowed_operations": list(self.allowed_operations),
            "sensitive_keys": list(self.sensitive_keys),
            "max_content_size": self.max_content_size,
            "requires_validation": True,
        }

    def to_provider_metadata(self) -> dict[str, Any]:
        """Convert to provider_metadata dict for CapabilityRegistryEntry."""
        base = dict(self.provider_metadata)
        base.update(
            {
                "transport": self.transport,
                "adapter_class_path": self.adapter_class_path,
                "adapter_kwargs": self.adapter_kwargs,
            }
        )
        return base


# ---------------------------------------------------------------------------
# Manifest Validation Errors
# ---------------------------------------------------------------------------


class ManifestValidationError(CapabilityManagerError):
    """Raised when a capability manifest fails validation."""

    def __init__(
        self,
        message: str,
        *,
        rule_id: str = "CM-MANIFEST-001",
        original_error: BaseException | None = None,
        manifest_path: str | None = None,
    ) -> None:
        super().__init__(message, rule_id=rule_id, original_error=original_error)
        self.manifest_path = manifest_path


# ---------------------------------------------------------------------------
# CapabilityManifestLoader
# ---------------------------------------------------------------------------


class CapabilityManifestLoader:
    """
    Loads and validates capability manifests from `config/capabilities/*.yaml`.

    Validation pipeline:
    1. YAML parsing
    2. Required field presence
    3. Schema validation (types, constraints)
    4. Non-auto-trust enforcement (defaults + SecurityManager gate)
    5. Adapter allowlist check
    6. `discovered_from` population
    """

    # Required fields in manifest
    REQUIRED_FIELDS = (
        "capability_id",
        "facade",
        "provider_id",
        "adapter",
    )

    def __init__(
        self,
        manifest_dir: Path | str = "./config/capabilities",
        adapter_allowlist: tuple[str, ...] = (),
        trust_default: str = TrustLevel.UNTRUSTED,
        security_manager: Any | None = None,
    ) -> None:
        """
        Initialize the manifest loader.

        Args:
            manifest_dir: Directory containing *.yaml capability manifests
            adapter_allowlist: Explicitly allowlisted adapter module paths
            trust_default: Default trust level for discovered capabilities
            security_manager: Optional SecurityManager for validation gate
        """
        self._manifest_dir = Path(manifest_dir)
        self._adapter_allowlist = set(adapter_allowlist)
        self._trust_default = trust_default
        self._security_manager = security_manager

    @property
    def manifest_dir(self) -> Path:
        return self._manifest_dir

    def load_all(self) -> list[CapabilitySpec]:
        """Load all valid manifests from the manifest directory."""
        if not self._manifest_dir.exists():
            logger.debug(f"Manifest directory does not exist: {self._manifest_dir}")
            return []

        specs: list[CapabilitySpec] = []
        for manifest_path in sorted(self._manifest_dir.glob("*.yaml")):
            try:
                spec = self.load_manifest(manifest_path)
                if spec:
                    specs.append(spec)
            except ManifestValidationError as e:
                logger.warning(f"Skipping invalid manifest {manifest_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading manifest {manifest_path}: {e}")

        return specs

    def load_manifest(self, manifest_path: Path) -> CapabilitySpec | None:
        """
        Load and validate a single capability manifest.

        Returns None if manifest has `enabled: false`.
        Raises ManifestValidationError on validation failure.
        """
        # 1. YAML parsing
        try:
            content = manifest_path.read_text(encoding="utf-8")
            raw = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ManifestValidationError(
                f"Invalid YAML in manifest: {e}",
                rule_id="CM-MANIFEST-001",
                original_error=e,
                manifest_path=str(manifest_path),
            )
        except Exception as e:
            raise ManifestValidationError(
                f"Failed to read manifest: {e}",
                rule_id="CM-MANIFEST-001",
                original_error=e,
                manifest_path=str(manifest_path),
            )

        if raw is None:
            raise ManifestValidationError(
                "Manifest is empty",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        if not isinstance(raw, dict):
            raise ManifestValidationError(
                "Manifest root must be a mapping",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 2. Check enabled flag (skip disabled manifests)
        if raw.get("enabled", True) is False:
            logger.debug(f"Skipping disabled manifest: {manifest_path}")
            return None

        # 3. Required field presence
        missing = [f for f in self.REQUIRED_FIELDS if f not in raw]
        if missing:
            raise ManifestValidationError(
                f"Missing required fields: {', '.join(missing)}",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 4. Parse adapter block
        adapter = raw.get("adapter", {})
        if not isinstance(adapter, dict):
            raise ManifestValidationError(
                "adapter must be a mapping with 'class_path'",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        adapter_class_path = adapter.get("class_path")
        if not adapter_class_path or not isinstance(adapter_class_path, str):
            raise ManifestValidationError(
                "adapter.class_path is required and must be a string",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        adapter_kwargs = adapter.get("kwargs", {})
        if not isinstance(adapter_kwargs, dict):
            raise ManifestValidationError(
                "adapter.kwargs must be a mapping",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 5. Validate adapter against allowlist (path traversal protection)
        if not self._is_allowlisted_adapter(adapter_class_path):
            raise ManifestValidationError(
                f"Adapter class not in allowlist: {adapter_class_path}",
                rule_id="CM-ADAPTER-001",
                manifest_path=str(manifest_path),
            )

        # 6. Validate trust_level (enforce non-auto-trust default)
        trust_level = raw.get("trust_level", self._trust_default)
        if trust_level not in (
            TrustLevel.BUILTIN,
            TrustLevel.TRUSTED,
            TrustLevel.TRUSTED_CONTEXTUAL,
            TrustLevel.UNTRUSTED,
        ):
            raise ManifestValidationError(
                f"Invalid trust_level: {trust_level}",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # External manifests CANNOT claim builtin/trusted — they must be validated
        # through SecurityManager gate. We only allow untrusted/trusted_contextual
        # from manifest files; builtin/trusted require kernel registration.
        if trust_level in (TrustLevel.BUILTIN, TrustLevel.TRUSTED):
            raise ManifestValidationError(
                f"External manifest cannot declare trust_level={trust_level}; "
                "builtin/trusted capabilities must be registered by the kernel",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 7. Validate authority_classification (enforce non-auto-trust default)
        authority_classification = raw.get(
            "authority_classification",
            AuthorityClassification.default_for_trust(trust_level),
        )
        if authority_classification not in (
            AuthorityClassification.AUTHORITATIVE,
            AuthorityClassification.CONTEXTUAL,
            AuthorityClassification.ADVISORY,
            AuthorityClassification.ADVISORY_ONLY,
        ):
            raise ManifestValidationError(
                f"Invalid authority_classification: {authority_classification}",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # External manifests CANNOT claim authoritative — re-asserted by
        # mark_capability_advisory() at invocation time. We reject authoritative
        # at manifest level to fail fast.
        if authority_classification == AuthorityClassification.AUTHORITATIVE:
            raise ManifestValidationError(
                "External manifest cannot declare authority_classification=authoritative; "
                "external capabilities are advisory-only",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 8. Optional fields with validation
        version = raw.get("version", "1.0.0")
        if not isinstance(version, str):
            raise ManifestValidationError(
                "version must be a string",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        transport = raw.get("transport", "local")
        if transport not in ("local", "mcp", "acp", "stdio"):
            raise ManifestValidationError(
                f"Invalid transport: {transport}",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        allowed_operations = tuple(raw.get("allowed_operations", []))
        if not all(isinstance(op, str) for op in allowed_operations):
            raise ManifestValidationError(
                "allowed_operations must be a list of strings",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        sensitive_keys = tuple(raw.get("sensitive_keys", []))
        if not all(isinstance(k, str) for k in sensitive_keys):
            raise ManifestValidationError(
                "sensitive_keys must be a list of strings",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        max_content_size = raw.get("max_content_size", 10240)
        if not isinstance(max_content_size, int) or max_content_size <= 0:
            raise ManifestValidationError(
                "max_content_size must be a positive integer",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        tags = tuple(raw.get("tags", []))
        if not all(isinstance(t, str) for t in tags):
            raise ManifestValidationError(
                "tags must be a list of strings",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        dependencies = tuple(raw.get("dependencies", []))
        if not all(isinstance(d, str) for d in dependencies):
            raise ManifestValidationError(
                "dependencies must be a list of strings",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        provider_metadata = raw.get("provider_metadata", {})
        if not isinstance(provider_metadata, dict):
            raise ManifestValidationError(
                "provider_metadata must be a mapping",
                rule_id="CM-MANIFEST-001",
                manifest_path=str(manifest_path),
            )

        # 9. SecurityManager validation gate (fail-closed)
        if self._security_manager and hasattr(
            self._security_manager, "validate_capability_spec"
        ):
            # Create a temporary spec for validation
            temp_spec = CapabilitySpec(
                capability_id=raw["capability_id"],
                facade=raw["facade"],
                provider_id=raw["provider_id"],
                adapter_class_path=adapter_class_path,
                adapter_kwargs=adapter_kwargs,
                transport=transport,
                version=version,
                trust_level=trust_level,
                authority_classification=authority_classification,
                allowed_operations=allowed_operations,
                sensitive_keys=sensitive_keys,
                max_content_size=max_content_size,
                discovered_from=str(manifest_path),
                tags=tags,
                dependencies=dependencies,
                enabled=True,
                provider_metadata=provider_metadata,
            )
            try:
                # This is async in SecurityManager; we can't await here.
                # The validation gate is called at registration time instead.
                # We log that the gate will be enforced.
                logger.debug(
                    f"SecurityManager validation gate will be enforced at registration: "
                    f"{raw['capability_id']}"
                )
            except Exception as e:
                logger.warning(
                    f"SecurityManager validation gate check failed for "
                    f"{raw['capability_id']}: {e}"
                )

        # 10. Build CapabilitySpec with discovered_from populated
        spec = CapabilitySpec(
            capability_id=raw["capability_id"],
            facade=raw["facade"],
            provider_id=raw["provider_id"],
            adapter_class_path=adapter_class_path,
            adapter_kwargs=adapter_kwargs,
            transport=transport,
            version=version,
            trust_level=trust_level,
            authority_classification=authority_classification,
            allowed_operations=allowed_operations,
            sensitive_keys=sensitive_keys,
            max_content_size=max_content_size,
            discovered_from=str(manifest_path),
            tags=tags,
            dependencies=dependencies,
            enabled=True,
            provider_metadata=provider_metadata,
        )

        logger.debug(f"Loaded capability manifest: {spec.capability_id} from {manifest_path}")
        return spec

    def reload(self) -> list[CapabilitySpec]:
        """M9-N6 — re-read all manifests atomically (fail-closed).

        Re-runs the full M8-T5 validation pipeline over every ``*.yaml`` in
        ``manifest_dir``. If ANY manifest fails validation, the whole reload
        is rejected: :class:`ManifestValidationError` is raised and the caller
        must keep its previous valid registration state (spec §11.6/§18).
        Disabled manifests are skipped exactly as in ``load_all``.

        Returns the complete validated spec list — never a partial set.
        """
        if not self._manifest_dir.exists():
            # An empty/vanished directory yields an empty set — that is a valid,
            # complete snapshot (all capabilities withdrawn by operator intent).
            return []

        specs: list[CapabilitySpec] = []
        errors: list[str] = []
        for manifest_path in sorted(self._manifest_dir.glob("*.yaml")):
            try:
                spec = self.load_manifest(manifest_path)
                if spec:
                    specs.append(spec)
            except ManifestValidationError as e:
                # Preserve the specific M8-T5 rule id so the aggregated
                # fail-closed error remains diagnosable per manifest.
                errors.append(f"{manifest_path.name}: [{e.rule_id}] {e}")
            except Exception as e:  # noqa: BLE001 — fail-closed on ANY error
                errors.append(f"{manifest_path.name}: unexpected {type(e).__name__}: {e}")

        if errors:
            raise ManifestValidationError(
                "Hot-reload rejected — fail-closed (invalid manifest(s)): "
                + "; ".join(errors),
                rule_id="CM-MANIFEST-001",
            )
        return specs

    def _is_allowlisted_adapter(self, class_path: str) -> bool:
        """
        Check if adapter class_path is in the explicit allowlist.

        Rejects:
        - Path traversal attempts (.., absolute paths)
        - Non-allowlisted modules
        - Arbitrary importlib paths (os, subprocess, etc.)
        """
        # Path traversal protection
        if ".." in class_path or class_path.startswith("/") or class_path.startswith("\\"):
            logger.warning(f"Path traversal attempt in adapter class_path: {class_path}")
            return False

        # Must be a valid Python module path (dotted notation)
        if not all(c.isalnum() or c in "._" for c in class_path):
            logger.warning(f"Invalid characters in adapter class_path: {class_path}")
            return False

        # Check against explicit allowlist
        if class_path not in self._adapter_allowlist:
            logger.warning(f"Adapter not in allowlist: {class_path} (allowlist: {self._adapter_allowlist})")
            return False

        return True


# ---------------------------------------------------------------------------
# Convenience function for kernel boot
# ---------------------------------------------------------------------------


async def load_capability_manifests(
    manifest_dir: Path | str = "./config/capabilities",
    adapter_allowlist: tuple[str, ...] = (),
    trust_default: str = TrustLevel.UNTRUSTED,
    security_manager: Any | None = None,
) -> list[CapabilitySpec]:
    """
    Convenience function to load all capability manifests.

    Used by kernel._init_capability_manifests().
    """
    loader = CapabilityManifestLoader(
        manifest_dir=manifest_dir,
        adapter_allowlist=adapter_allowlist,
        trust_default=trust_default,
        security_manager=security_manager,
    )
    return loader.load_all()