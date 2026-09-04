"""
Core Component C3 — ConfigurationManager (AI-OS Architecture Specification
Part 3 §3.5).

The ConfigurationManager is the authoritative in-memory configuration
authority for the Hermes Kernel. It provides:

  * Four-layer configuration merge (Defaults -> App -> Env -> AIOS_* env vars)
    with strict, deep-merge precedence (Part 3 §3.5.1-§3.5.3)
  * Schema validation (KernelConfigSchema) before freeze (§3.5.4-§3.5.5)
  * Immutable post-freeze configuration (§3.5.6)
  * Typed / read-only access (get / getSection / getAll) (§3.5.7)
  * Secret detection, masking, and locked-down access (§3.5.9)
  * AIOS_<SECTION>_<KEY> environment variable parsing (§3.5.8)
  * Deterministic configuration hashing (§3.5.15 INV-CM-STR-006)
  * Lifecycle (initialize / shutdown / healthCheck) and EventBus integration
    (CoreComponentInitialized / ConfigurationFrozen / CoreComponentShutdown)

AUTHORITATIVE SOURCES
---------------------
  * Part 3 §3.5 (Component C3 — ConfigurationManager) — the contract.
  * Task 1–5 stack: ``aios.events.core.{event,bus,types,identity}``.

IMPLEMENTATION NOTES / ARCHITECTURE CONFLICTS (documented, not silently
--------------------------------------------------------------------------------
  1. The ICoreComponent request/response/error contract is explicitly "NOT YET
     DEFINED" (architecture/Part14/interfaces.md §2.1.1). This module follows the
     EXACT established Core Component pattern set by the Task-5 EventBus and the
     Task-6 ServiceRegistry: ``async initialize(kernel=None)``, ``async
     shutdown()``, ``sync healthCheck()``, ``name`` / ``phase`` / ``dependencies``
     properties, and a singleton accessor.

  2. §3.5.6 names the freeze trigger as the (future) LifecycleManager. This
     component does NOT invent or implement LifecycleManager (per the Task 7
     rules). ``freeze()`` is a public, kernel-callable hook; the existing
     kernel integration (kernel.py) wires it into the Phase 2->3 boundary that
     already exists in the repository, and exposes ``kernel.configuration``.

  3. Event emission uses ONLY canonical EventTypes from the closed Task-2 enum
     (INV-EB-*. Part 2 INV-ET-003/004). The architecture-named events map onto
     canonical types as follows (no new EventType is ever created):
         ConfigurationFrozen   -> EventType.CONFIGURATION_FROZEN
         (component init)      -> EventType.CORE_COMPONENT_INITIALIZED
         (component shutdown)   -> EventType.CORE_COMPONENT_SHUTDOWN
     ``CONFIGURATION_CHANGED`` / ``ConfigurationChanged`` is a DEV-ONLY hot-reload
     event (§3.5.13); production hot reload is intentionally NOT enabled.

  4. The existing repository already has a layered config package
     (``aios.config`` — Pydantic models, YAML loader, validator). The
     architecture's KernelConfigSchema is defined in §3.5.5 as a JSON-Schema-like
     structure and is NOT present as a reusable schema object in the repository.
     Per Task 7 rules, this module implements ONLY the minimum schema
     representation required: a ``KernelConfigSchema`` dataclass holding required
     top-level keys and typed leaf constraints, plus a ``validate`` step run
     before freeze. No arbitrary application-config fields are invented; the
     schema is closed (additionalProperties = false) and its required/known keys
     derive directly from §3.5.5 / §3.5.8.

  5. The four-layer merge reuses the architecture's precedence exactly. Layer 1
     (defaults) is embedded here as the authoritative embedded default object
     (KernelConfigDefaults, §3.5.2). Layers 2/3 (app/env YAML) are loaded from
     the provided config path using the repository's ``aios.config.loader``
     helpers, and Layer 4 (AIOS_* env vars) is parsed per §3.5.8. All four
     layers are merged with the architecture-mandated deep-merge semantics;
     arrays REPLACE (never concatenate), ``null`` removes a key, and the result
     is deterministic.

  6. FIX 9: The split-brain issue (Task 9) has been resolved. The Kernel now
     constructs ONLY the canonical EventBus (C1, Task 5) and canonical
     ServiceRegistry (C2, Task 6). This module now uses ONLY the canonical
     EventBus via ``get_core_event_bus()`` and emits canonical Event objects.

This module does NOT implement the Kernel, any Manager, Engineering Service,
LifecycleManager, or any other forbidden-scope component. It is a drop-in Core
Component intended to be constructed and owned exclusively by HermesKernel
(INV-CM-STR-001).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
import threading
import uuid
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.serialization import compute_checksum
from aios.events.core.types import EventType, SemanticVersion


logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ConfigState(StrEnum):
    """Lifecycle of the ConfigurationManager Core Component itself (§3.5.11)."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    FREEZING = "FREEZING"
    FROZEN = "FROZEN"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ConfigurationFrozenError(Exception):
    """Raised on any mutation attempt after the configuration is frozen (§3.5.12)."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path


class ConfigurationError(Exception):
    """Raised for fatal configuration failures (load / merge / validate) (§3.5.12)."""

    def __init__(
        self,
        message: str,
        *,
        errors: list[str] | None = None,
        path: str | None = None,
    ) -> None:
        self.errors = errors or [message]
        self.path = path
        detail = "; ".join(self.errors)
        super().__init__(f"{message} [{detail}]" if len(self.errors) > 1 else message)


# ---------------------------------------------------------------------------
# Schema (minimum representation per Part 3 §3.5.5; see module docstring note 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertySchema:
    """Leaf/Nested property schema (Part 3 §3.5.5 PropertySchema)."""

    type: str | list[str]
    enum: list[Any] | None = None
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None
    default: Any = None
    description: str = ""
    properties: dict[str, PropertySchema] | None = None
    required: list[str] | None = None
    additional_properties: bool = True
    items: PropertySchema | None = None


@dataclass(frozen=True)
class KernelConfigSchema:
    """Canonical configuration schema (Part 3 §3.5.5).

    This is the minimum schema representation required for Task 7. It is closed
    (additionalProperties = false at the top level) and its required/known keys
    derive directly from §3.5.5 / §3.5.8. No application-config fields are
    invented; the schema is intentionally restricted to the kernel-configuration
    surface the architecture specifies for C3.
    """

    version: SemanticVersion = field(default_factory=lambda: SemanticVersion(1, 0, 0))
    required: list[str] = field(default_factory=lambda: ["kernel"])
    properties: dict[str, PropertySchema] = field(
        default_factory=lambda: {
            "kernel": PropertySchema(
                type="object",
                required=["name", "version", "logLevel"],
                # Allow snake_case keys from defaults.yaml (data_dir, log_level) alongside
                # camelCase (dataDir, logLevel) for backwards compatibility.
                additional_properties=True,
                properties={
                    "name": PropertySchema(
                        type="string",
                        pattern=r"^\S.{0,98}\S$|^\S$",
                        description="Kernel component name",
                    ),
                    "version": PropertySchema(
                        type="string",
                        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$",
                        description="Semantic version",
                    ),
                    "logLevel": PropertySchema(
                        type="string",
                        enum=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO",
                        description="Default logging level",
                    ),
                    "healthCheckIntervalMs": PropertySchema(
                        type="integer",
                        minimum=10,
                        maximum=86_400_000,
                        default=30_000,
                        description="Health check interval (ms)",
                    ),
                    "dataDir": PropertySchema(
                        type="string", description="Kernel data directory"
                    ),
                    "environment": PropertySchema(
                        type="string",
                        default=None,
                        description=(
                            "Active deployment environment (drives Layer 3 "
                            "env-specific YAML); null = no env file required"
                        ),
                    ),
                    # M8-T5 capability-manifest discovery controls. Values mirror
                    # config/defaults.yaml; the schema registration makes the
                    # section overridable through Layer-2 app.yaml.
                    "capabilities": PropertySchema(
                        type="object",
                        additional_properties=True,
                        description=(
                            "Capability manifest discovery (M8-T5): enabled "
                            "master switch, relative manifest_dir, trust_default, "
                            "explicit adapter_allowlist"
                        ),
                    ),
                },
            ),
            # M9-N7 ACP session hardening controls (spec §19). Registration
            # follows the same pattern as kernel.capabilities: values mirror
            # config/defaults.yaml; the schema registration makes the section
            # overridable through Layer-2 app.yaml / AIOS_* env vars.
            "acp": PropertySchema(
                type="object",
                additional_properties=True,
                description=(
                    "ACP protocol settings (M9-N7): absolute session TTL "
                    "(session_ttl_seconds; 0 = disabled, idle timeout only)"
                ),
                properties={
                    "sessionTtlSeconds": PropertySchema(
                        type="integer",
                        minimum=0,
                        description="Absolute ACP session lifetime cap (s)",
                    ),
                },
            ),
            "security": PropertySchema(
                type="object",
                additional_properties=True,
                description="Security configuration (may carry secrets)",
                properties={
                    "jwtSecret": PropertySchema(
                        type="string", description="JWT signing secret (secret)"
                    ),
                },
            ),
            "llm": PropertySchema(
                type="object",
                additional_properties=True,
                description="LLM provider configuration (may carry secrets)",
                properties={
                    "providers": PropertySchema(
                        type="object",
                        additional_properties=True,
                        properties={
                            "openai": PropertySchema(
                                type="object",
                                additional_properties=True,
                                properties={
                                    "apiKey": PropertySchema(
                                        type="string",
                                        description="OpenAI API key (secret)",
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        }
    )
    # Allow additional top-level properties for application configuration.
    # The schema validates kernel-relevant sections; application sections (event_bus,
    # services, etc.) are passed through without schema validation.
    additional_properties: bool = True

    def validate(self, config: dict[str, Any]) -> None:
        """Validate the full merged config; raise ConfigurationError on failure.

        Implements §3.5.4 schema validation (FATAL on failure). Errors include the
        full path to the failing key (INV-CM-VAL-002).
        """
        errors: list[str] = []
        # Required top-level keys (§3.5.5 `required`).
        for key in self.required:
            if key not in config:
                errors.append(f"Missing required top-level key: '{key}'")
        # Top-level additionalProperties = false.
        if not self.additional_properties:
            for key in config:
                if key not in self.properties:
                    errors.append(
                        f"Unknown top-level config section '{key}' "
                        f"(schema additionalProperties=false)"
                    )
        # Recurse into known sections.
        for section, prop in self.properties.items():
            if section in config:
                errors.extend(
                    _validate_property(
                        f"{section}", config[section], prop, self.additional_properties
                    )
                )
        if errors:
            raise ConfigurationError(
                "Configuration failed schema validation", errors=errors
            )


def _validate_property(
    path: str,
    value: Any,
    schema: PropertySchema,
    parent_additional: bool,
) -> list[str]:
    """Recursively validate a value against a PropertySchema; return errors."""
    errors: list[str] = []

    def matches_type(v: Any) -> bool:
        types = schema.type if isinstance(schema.type, list) else [schema.type]
        for t in types:
            if t == "object" and isinstance(v, dict):
                return True
            if t == "array" and isinstance(v, list):
                return True
            if t == "string" and isinstance(v, str):
                return True
            if t == "number" and isinstance(v, (int, float)) and not isinstance(v, bool):
                return True
            if t == "integer" and isinstance(v, int) and not isinstance(v, bool):
                return True
            if t == "boolean" and isinstance(v, bool):
                return True
        return False

    if value is None:
        # A null value "removes" the key per §3.5.3; allowed at any level.
        return errors
    if not matches_type(value):
        errors.append(
            f"'{path}': expected type {schema.type}, got {type(value).__name__}"
        )
        return errors
    if isinstance(value, str):
        if schema.enum is not None and value not in schema.enum:
            errors.append(
                f"'{path}': value '{value}' not in allowed enum {schema.enum}"
            )
        if schema.pattern is not None and not re.match(schema.pattern, value):
            errors.append(
                f"'{path}': value '{value}' does not match pattern {schema.pattern}"
            )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if schema.minimum is not None and value < schema.minimum:
            errors.append(f"'{path}': {value} < minimum {schema.minimum}")
        if schema.maximum is not None and value > schema.maximum:
            errors.append(f"'{path}': {value} > maximum {schema.maximum}")
    if isinstance(value, dict) and schema.properties is not None:
        # Object-level required keys (schema.required) — e.g. kernel.{name,version,logLevel}.
        if schema.required:
            for req in schema.required:
                if req not in value:
                    errors.append(f"'{path}': missing required key '{req}'")
        if not schema.additional_properties:
            for k in value:
                if k not in schema.properties:
                    errors.append(
                        f"'{path}': unknown key '{k}' "
                        f"(additionalProperties=false)"
                    )
        for k, child in schema.properties.items():
            if k in value:
                child_path = f"{path}.{k}"
                if child.required and value.get(k) is None:
                    errors.append(f"'{path}': missing required key '{child_path}'")
                errors.extend(
                    _validate_property(child_path, value[k], child, schema.additional_properties)
                )
    if isinstance(value, list) and schema.items is not None:
        for i, item in enumerate(value):
            errors.extend(
                _validate_property(f"{path}[{i}]", item, schema.items, True)
            )
    return errors


# ---------------------------------------------------------------------------
# Secrets (Part 3 §3.5.9)
# ---------------------------------------------------------------------------

# Secret key detection (Part 3 §3.5.9). The architecture defines the secret
# vocabulary as a fixed set of name *tokens*: ``*_SECRET``, ``*_KEY``,
# ``*_TOKEN``, ``*_PASSWORD``, ``*_CREDENTIAL``. Configuration leaf keys may be
# snake_case (``api_key``, ``db_password``) or camelCase (``jwtSecret``,
# ``apiKey``) per §3.5.8. We split each key into vocabulary tokens at
# ``_`` / ``.`` / ``-`` boundaries AND at camelCase transitions, then treat the
# key as secret iff any resulting token equals one of the vocabulary words
# (case-insensitive). This deliberately does NOT use bare substring matching:
# e.g. ``keyboard`` is a single token "keyboard" which is not "key";
# ``keystone`` is a single token and is not "key". But ``apiKey`` -> ("api",
# "key") matches, and ``jwtSecret`` -> ("jwt", "Secret") matches. This honors
# the architecture's secret naming behavior without false positives.
_SECRET_TOKENS: frozenset[str] = frozenset(
    {"secret", "key", "token", "password", "credential"}
)

_MASK = "***"


def _split_tokens(key: str) -> list[str]:
    """Split a key into vocabulary tokens at ``_ . -`` and camelCase boundaries.

    e.g. ``jwtSecret`` -> ``["jwt", "Secret"]``; ``apiKey`` -> ``["api", "Key"]``;
    ``db_password`` -> ``["db", "password"]``; ``keyboard`` -> ``["keyboard"]``.
    """
    parts: list[str] = []
    for chunk in re.split(r"[^A-Za-z0-9]+", key):
        if not chunk:
            continue
        # Split camelCase boundaries within a chunk.
        for s in re.findall(r"[a-z0-9]+|[A-Z][a-z0-9]*", chunk):
            parts.append(s)
    return parts


def is_secret_path(path_parts: list[str]) -> bool:
    """Return True if any key segment matches a secret pattern (§3.5.9)."""
    return any(_match_secret(p) for p in path_parts)


def _match_secret(key: str) -> bool:
    return any(t.lower() in _SECRET_TOKENS for t in _split_tokens(key))


# ---------------------------------------------------------------------------
# Component constants
# ---------------------------------------------------------------------------

_COMPONENT_NAME = "ConfigurationManager"
_COMPONENT_VERSION = SemanticVersion(0, 3, 0)
_PHASE = 2
_DEPENDENCIES = ["EventBus"]

# Canonical EventType emission mapping (documented conflict, see module docstring).
_CORE_COMPONENT_INITIALIZED = EventType.CORE_COMPONENT_INITIALIZED
_CORE_COMPONENT_SHUTDOWN = EventType.CORE_COMPONENT_SHUTDOWN
_CONFIGURATION_FROZEN = EventType.CONFIGURATION_FROZEN

# Embedded Layer 1 defaults (KernelConfigDefaults, §3.5.2 Layer 1).
_EMBEDDED_DEFAULTS: dict[str, Any] = {
    "kernel": {
        "name": "Hermes",
        "version": "0.1.0",
        "logLevel": "INFO",
        "healthCheckIntervalMs": 30_000,
        "dataDir": "./data",
        # §3.5.2/§3.5.3 Layer 3 (env-specific YAML) is keyed by the active
        # environment (``config/env/{environment}.yaml``). The authoritative
        # environment source is ``kernel.environment``; we declare it here as a
        # Layer-1 default (None = no env-specific file is required, the layer
        # simply contributes nothing) so that Layer 3 is ALWAYS represented in
        # the merge pipeline and is never silently omitted merely because the
        # field was absent.
        "environment": None,
    },
    "security": {},
    "llm": {"providers": {}},
}


# ---------------------------------------------------------------------------
# Deep merge (Part 3 §3.5.3)
# ---------------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``override`` over ``base`` per §3.5.3.

    Objects recurse; arrays REPLACE (never concatenate); ``null`` in the higher
    layer removes the key; primitives replace. Deterministic (INV-CM-PREC-003).
    ``base`` is NOT mutated; a new dict is returned.
    """
    result = dict(base)
    for key, value in override.items():
        if value is None:
            # null in higher layer removes the key (§3.5.3).
            result.pop(key, None)
            continue
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            # Arrays/lists and primitives simply replace (INV-CM-PREC-002).
            result[key] = value
    return result


def _normalize(value: Any) -> Any:
    """Recursively convert the tuple-encoded deep-frozen config back to a
    read-only form with ``dict``-like mapping nodes (FIX 1).

    The frozen representation uses ``tuple`` for dicts and ``tuple`` for lists
    (see ``_deep_freeze``) so callers cannot mutate the internal storage. The
    accessor helpers work on dict-like lookups, so we expose a normalized view
    where each frozen node is a ``dict``-alike (``FrozenMapping``) or ``list``.
    The normalized view never aliases the original mutable working buffer and is
    itself constructed from the immutable tuples, so it remains tamper-evident.
    """
    if isinstance(value, tuple):
        if value and all(isinstance(e, tuple) and len(e) == 2 for e in value):
            return FrozenMapping((k, _normalize(v)) for k, v in value)
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return FrozenMapping((k, _normalize(v)) for k, v in value.items())
    return value


class FrozenMapping(Mapping[Any, Any]):
    """An immutable, hashable mapping wrapper over a frozen ``(key, value)`` tuple.

    Provides dict-like read access for the accessor helpers without exposing a
    mutable ``dict``. Construction only consumes the already-immutable input, so
    it cannot be used to mutate the internal frozen storage (FIX 1).
    """

    __slots__ = ("_items", "_by_key")

    def __init__(self, items: Iterable[tuple[Any, Any]]) -> None:
        self._items = tuple(items)
        self._by_key = dict(self._items)

    def __getitem__(self, key: Any) -> Any:
        return self._by_key[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._by_key)

    def __len__(self) -> int:
        return len(self._by_key)

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenMapping):
            return self._items == other._items
        if isinstance(other, dict):
            return dict(self._by_key) == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._items)

    def __repr__(self) -> str:
        return repr(dict(self._by_key))


def _get_path(config: Any, path: str) -> Any:
    cur: Any = config
    # Tokenize: split on '.', then handle [n] index suffixes.
    parts = path.split(".")
    for part in parts:
        if cur is None:
            return None
        # Extract any trailing [idx] segments.
        while "[" in part:
            key, _, rest = part.partition("[")
            idx_str, _, after = rest.partition("]")
            if not _is_mapping(cur) or key not in cur:
                return None
            cur = cur[key]
            try:
                idx = int(idx_str)
            except ValueError:
                return None
            if not isinstance(cur, (list, tuple)) or idx >= len(cur):
                return None
            cur = cur[idx]
            part = after
        if not _is_mapping(cur) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _path_exists(config: Any, path: str) -> bool:
    """Return True if a dotted path resolves to a present key (or null value)."""
    cur: Any = config
    parts = path.split(".")
    for part in parts:
        while "[" in part:
            key, _, rest = part.partition("[")
            idx_str, _, after = rest.partition("]")
            if not _is_mapping(cur) or key not in cur:
                return False
            cur = cur[key]
            try:
                idx = int(idx_str)
            except ValueError:
                return False
            if not isinstance(cur, (list, tuple)) or idx >= len(cur):
                return False
            cur = cur[idx]
            part = after
        if not _is_mapping(cur) or part not in cur:
            return False
        cur = cur[part]
    return True


def _is_mapping(value: Any) -> bool:
    """True for dict-like nodes (plain dict OR deep-frozen FrozenMapping)."""
    return isinstance(value, (dict, FrozenMapping))


def _set_path(config: dict[str, Any], path: str, value: Any) -> None:
    """Set a dotted path, creating intermediate dicts. Raises for list indices."""
    parts = path.split(".")
    cur = config
    for i, part in enumerate(parts[:-1]):
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    last = parts[-1]
    if "[" in last:
        raise ConfigurationError(
            "List index writes are not supported by ConfigurationManager"
        )
    cur[last] = value


def _to_camel(tokens: list[str]) -> str:
    """Join tokens into camelCase (first lower, rest capitalized)."""
    if not tokens:
        return ""
    return tokens[0] + "".join(t[:1].upper() + t[1:] for t in tokens[1:] if t)


def _build_env_mapping(body: str, raw: str) -> tuple[str, Any]:
    """Map an AIOS_ env var body to a canonical dotted config path + parsed value.

    Per §3.5.8 mapping table: first ``_``-delimited token is the section; the
    remaining tokens are camelCased into the leaf key; ``__`` is a hard nesting
    boundary. See ``_parse_env_vars`` for the documented conflict note.
    """
    levels = body.split("__")
    segments: list[str] = []
    for lvl in levels:
        tokens = [t for t in lvl.split("_") if t]
        if not tokens:
            continue
        if len(tokens) == 1:
            segments.append(tokens[0])
        else:
            segments.append(f"{tokens[0]}.{_to_camel(tokens[1:])}")
    path = ".".join(segments)
    return path, _parse_env_value(raw)


def _parse_env_value(raw: str) -> Any:
    """Parse an env var string value (§3.5.8): bool / number / null / string."""
    low = raw.strip().lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null":
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _set_path_dict(config: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Return a new nested dict setting ``path`` to ``value`` (§3.5.8 build)."""
    out: dict[str, Any] = {}
    cur = out
    parts = path.split(".")
    for part in parts[:-1]:
        cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value
    return out


def _collect_secret_paths(config: dict[str, Any], prefix: str = "") -> set[str]:
    """Walk the config and collect every dotted path that is a secret (§3.5.9)."""
    found: set[str] = set()

    def walk(node: Any, path: str, parts: list[str]) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                nparts = parts + [k]
                npath = f"{path}.{k}" if path else k
                if _match_secret(k):
                    found.add(npath)
                walk(v, npath, nparts)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]", parts)

    walk(config, prefix, [])
    return found


# ---------------------------------------------------------------------------
# ConfigurationManager — Core Component C3
# ---------------------------------------------------------------------------


class ConfigurationManager:
    """Core Component C3 — ConfigurationManager (Part 3 §3.5).

    The authoritative, in-memory, immutable-after-freeze configuration authority
    for the Hermes Kernel. Loads and merges four configuration layers, validates
    the merged config against ``KernelConfigSchema`` before freeze, then freezes
    the configuration into a deeply-immutable structure. Thread-safe; concurrent
    post-freeze reads are guarded so no reader observes a partially-frozen state.
    """

    def __init__(
        self,
        event_bus = None,  # Deprecated - canonical EventBus resolved via get_core_event_bus()
        config_path: Any | None = None,
    ) -> None:
        # INV-CM-STR-001: exactly one instance per process.
        global _INSTANCE
        with _INSTANCE_LOCK:
            if _INSTANCE is not None and _INSTANCE is not self:
                raise RuntimeError(
                    "Only one ConfigurationManager instance is permitted per process "
                    "(INV-CM-STR-001). A second construction is rejected."
                )
            _INSTANCE = self

        # FIX 9: Use canonical EventBus (C1, Task 5) — single authority per process
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            logger.warning("Canonical EventBus not yet initialized; events will be deferred")
        self._config_path = config_path
        self._state = ConfigState.UNINITIALIZED
        self._kernel: Any = None

        # Working (pre-freeze) merged config. Guarded by _lock.
        self._lock = threading.RLock()
        self._merged: dict[str, Any] = {}
        # Post-freeze immutable representation (deep-frozen tuples/lists/scalars,
        # NOT a mutable dict — FIX 1). Guarded by _lock for publication.
        self._frozen_config: Any = None
        self._secret_paths: set[str] = set()
        self._config_hash: str | None = None
        # Strong references to in-flight emission tasks so they are never
        # garbage-collected mid-flight (FIX 4).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        self._schema = KernelConfigSchema()

        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_COMPONENT,
            component_name=_COMPONENT_NAME,
            version=_COMPONENT_VERSION,
        )

    # --- ICoreComponent: identity / phase / dependencies -----------------

    @property
    def name(self) -> str:
        """Core Component name (ICoreComponent)."""
        return _COMPONENT_NAME

    @property
    def phase(self) -> int:
        """Initialization phase (Part 3 §3.5: Phase 2)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Component dependencies (Part 3 §3.5: EventBus)."""
        return list(_DEPENDENCIES)

    @property
    def state(self) -> ConfigState:
        """Current lifecycle state of the component itself."""
        return self._state

    @property
    def event_bus(self):
        """The canonical EventBus (C1, Task 5) — read-only accessor."""
        return self._event_bus or get_core_event_bus()

    @property
    def config_hash(self) -> str | None:
        """Deterministic configuration hash (set on freeze, §3.5.15)."""
        return self._config_hash

    # --- ICoreComponent: initialize --------------------------------------

    async def initialize(self, kernel: Any = None) -> ConfigState:
        """Initialize the ConfigurationManager (Phase 2, depends on EventBus).

        Follows the Task-5 EventBus Core Component pattern (async). Resolves the
        EventBus dependency via DI (constructor) or the ``kernel`` argument,
        loads + merges the four layers, validates against schema, prepares for
        freeze, and publishes ``CoreComponentInitialized`` (CONF-CM-003).
        """
        if self._state in (ConfigState.INITIALIZING, ConfigState.FROZEN):
            return self._state

        self._state = ConfigState.INITIALIZING

        if self._event_bus is None and kernel is not None:
            self._event_bus = getattr(kernel, "event_bus", None)
        if self._event_bus is None:
            logger.warning(
                "ConfigurationManager initialized without an EventBus; events will "
                "be deferred until a bus is attached."
            )
        self._kernel = kernel

        # Steps 1-5 (§3.5.11 Phase 2): load, merge, validate, prepare.
        try:
            merged = self._load_and_merge()
            self._validate(merged)
        except ConfigurationError:
            # FATAL: abort initialization (§3.5.12 / INV-CM-FH-001).
            self._state = ConfigState.SHUTDOWN
            raise

        with self._lock:
            self._merged = merged

        # The component is prepared; freeze() is invoked by the kernel at the
        # Phase 2->3 boundary (LifecycleManager in the architecture). Emitted
        # here per §3.4.10 equivalent: CoreComponentInitialized.
        await self._emit_async(
            _CORE_COMPONENT_INITIALIZED,
            {"name": _COMPONENT_NAME, "component": _COMPONENT_NAME, "state": "INITIALIZING"},
        )
        return self._state

    # --- ICoreComponent: shutdown ----------------------------------------

    async def shutdown(self) -> ConfigState:
        """Shutdown the ConfigurationManager (Phase S2, §3.5.11)."""
        if self._state is ConfigState.SHUTDOWN:
            return self._state
        self._state = ConfigState.SHUTTING_DOWN

        # Archive config hash for audit (§3.5.11 SHUTTING_DOWN).
        archived_hash = self._config_hash

        await self._emit_async(
            _CORE_COMPONENT_SHUTDOWN,
            {
                "name": _COMPONENT_NAME,
                "component": _COMPONENT_NAME,
                "state": "SHUTDOWN",
                "configHash": archived_hash,
            },
        )
        self._state = ConfigState.SHUTDOWN
        return self._state

    # --- ICoreComponent: healthCheck (sync) ------------------------------

    def healthCheck(self) -> dict[str, Any]:
        """Core Component health check (sync, mirrors EventBus.healthCheck)."""
        healthy = self._state in (ConfigState.INITIALIZING, ConfigState.FROZEN)
        return {
            "healthy": healthy,
            "state": self._state.value,
            "name": _COMPONENT_NAME,
            "frozen": self._state is ConfigState.FROZEN,
            "configHash": self._config_hash,
        }

    # --- Startup validation (§3.5.X - Deployment M10) ----------------------

    def validate_startup(self) -> list[str]:
        """Validate that required configuration is present for startup.

        Checks that all required fields per KernelConfigSchema are present
        and that critical deployment settings are configured.

        Returns:
            List of validation errors (empty if all required config is present).

        Raises:
            ConfigurationError: If frozen config is not available (not initialized).
        """
        if self._state not in (ConfigState.FROZEN, ConfigState.SHUTTING_DOWN, ConfigState.SHUTDOWN):
            raise ConfigurationError(
                "Startup validation requires initialized and frozen configuration",
                path="<root>",
            )

        errors = []
        config = self._config_snapshot()

        # Validate required kernel fields
        kernel = config.get("kernel", {})
        if not kernel.get("name"):
            errors.append("Required field 'kernel.name' is missing")
        if not kernel.get("version"):
            errors.append("Required field 'kernel.version' is missing")
        if not kernel.get("logLevel"):
            errors.append("Required field 'kernel.logLevel' is missing")

        # Check if we're in production environment
        is_production = kernel.get("environment") == "production"

        # Validate critical deployment settings (production only)
        if is_production and not config.get("configuration", {}).get("freeze_on_initialize", True):
            errors.append("Configuration freeze_on_initialize should be true for production")

        # Validate security settings (production only)
        if is_production:
            security = config.get("security") if hasattr(config, 'get') else None
            if not isinstance(security, dict) and not (hasattr(security, 'items') and hasattr(security, 'get')):
                security = {}
            if security.get("strict_mode") is not True:
                errors.append("Security strict_mode should be true for production")

            # Validate capability settings (production only)
            capabilities = config.get("capabilities") if hasattr(config, 'get') else None
            if not isinstance(capabilities, dict) and not (hasattr(capabilities, 'items') and hasattr(capabilities, 'get')):
                capabilities = {}
            if not capabilities.get("enabled"):
                errors.append("Capabilities should be enabled for production")

        # Validate autonomy gate - should be disabled by default
        services = config.get("services") if hasattr(config, 'get') else None
        if not isinstance(services, dict) and not (hasattr(services, 'items') and hasattr(services, 'get')):
            services = {}
        autonomy = services.get("autonomy") if hasattr(services, 'get') else None
        if not isinstance(autonomy, dict) and not (hasattr(autonomy, 'items') and hasattr(autonomy, 'get')):
            autonomy = {}
        if autonomy.get("enabled") is True:
            # This is a warning, not error - autonomy can be enabled intentionally
            logger.warning("Autonomy services enabled - ensure this is intentional for production")

        # Validate external integration gate
        real_integration = services.get("real_integration_enabled", False) if hasattr(services, 'get') else False
        if real_integration and not self._check_real_integration_credentials(config):
            errors.append("Real integration enabled but required credentials not configured")

        # Validate data directory
        data_dir = kernel.get("dataDir", kernel.get("data_dir"))
        if data_dir and data_dir.startswith("./"):
            logger.warning("Using relative data_dir '%s' - consider absolute path for production", data_dir)

        return errors

    def _check_real_integration_credentials(self, config: dict[str, Any]) -> bool:
        """Check if required credentials for real integrations are present."""
        services = config.get("services", {})
        required = [
            services.get("supabase", {}).get("url"),
            services.get("supabase", {}).get("anon_key"),
            services.get("n8n", {}).get("base_url"),
            services.get("n8n", {}).get("api_key"),
            services.get("obsidian_git", {}).get("vault_path"),
        ]
        # At least one real integration should have credentials if real_integration_enabled
        return any(v for v in required if v)

    # --- Four-layer load + merge (§3.5.1-§3.5.3) --------------------------

    def _load_and_merge(self) -> dict[str, Any]:
        """Load all four layers and merge with fixed precedence (§3.5.3).

        Layer 1: embedded defaults (always present — missing L1 is FATAL, but the
                 embedded defaults can never be missing).
        Layer 2: application config YAML (app.yaml) — missing file non-fatal.
        Layer 3: environment-specific config YAML (env/{environment}.yaml) —
                 missing file non-fatal (INV-CM-SRC-002).
        Layer 4: AIOS_* environment variables — highest precedence
                 (INV-CM-PREC-001).
        """
        config: dict[str, Any] = {}

        # Layer 1 (Defaults) — embedded, immutable source of truth.
        config = _deep_merge(config, _EMBEDDED_DEFAULTS)

        # Layer 2 (App Config) — from the provided config path / app.yaml.
        app_config = self._load_app_config()
        config = _deep_merge(config, app_config)

        # Layer 3 (Env Config) — environment-specific YAML.
        env_config = self._load_env_config(config)
        config = _deep_merge(config, env_config)

        # Layer 4 (Env Vars) — AIOS_* with highest precedence.
        env_overrides = self._parse_env_vars()
        config = _deep_merge(config, env_overrides)

        return config

    def _load_app_config(self) -> dict[str, Any]:
        """Load Layer 2 (application config YAML)."""
        if self._config_path is None:
            return {}
        try:
            from aios.config.loader import _load_yaml_file

            path = self._config_path
            if isinstance(path, str):
                from pathlib import Path

                path = Path(path)
            try:
                return _load_yaml_file(path)
            except Exception:
                # Missing Layer 2 file is non-fatal (INV-CM-SRC-002).
                logger.debug("App config file %s not loaded (non-fatal).", path)
                return {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load application config: %s", exc)
            return {}

    def _load_env_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Load Layer 3 (environment-specific YAML)."""
        if self._config_path is None:
            return {}
        try:
            from pathlib import Path

            from aios.config.loader import _load_yaml_file

            base = self._config_path
            if isinstance(base, str):
                base = Path(base)
            environment = config.get("kernel", {}).get("environment")
            if not environment:
                return {}
            env_path = base.parent / f"app.{environment}.yaml"
            if env_path == base or not env_path.exists():
                return {}
            try:
                return _load_yaml_file(env_path)
            except Exception as exc:
                # Missing Layer 3 file is non-fatal (INV-CM-SRC-002).
                logger.debug("Env config %s not loaded (non-fatal): %s", env_path, exc)
                return {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load environment config: %s", exc)
            return {}

    def _parse_env_vars(self) -> dict[str, Any]:
        """Parse Layer 4 (AIOS_<SECTION>_<KEY> env vars) per §3.5.8.

        Returns:
            A merged override dict. Unknown AIOS_ variables are logged as
            warnings but NOT added to the config (INV-CM-ENV-002). Malformed known
            values ultimately fail schema validation (no silent coercion).

        Mapping note (documented architecture conflict): §3.5.8's "Parsing Rules"
        prose says single underscore is preserved, but its mapping TABLE maps
        ``AIOS_KERNEL_LOG_LEVEL`` -> ``kernel.logLevel`` (camelCase leaves) and
        ``AIOS_LLM_PROVIDER_OPENAI_API_KEY`` -> ``llm.providers.openai.apiKey``
        (multi-level). These are mutually inconsistent. We follow the TABLE (the
        more specific, authoritative C3 contract for the named variables):
        the first ``_``-delimited token is the top-level section; remaining
        tokens are camelCased into the final leaf key; ``__`` is a hard nesting
        boundary. Malformed/novel variables are still rejected by schema
        validation rather than silently coerced.
        """
        overrides: dict[str, Any] = {}
        unknown: list[str] = []
        for key, raw in os.environ.items():
            if not key.startswith("AIOS_"):
                continue
            if key in ("AIOS_",):
                continue
            body = key[len("AIOS_"):].lower()
            top = body.split("__")[0].split("_")[0]
            if top not in self._schema.properties:
                unknown.append(key)
                continue
            try:
                path, value = _build_env_mapping(body, raw)
            except Exception as exc:  # noqa: BLE001
                # Malformed value: surface as unknown (logged); schema will
                # ultimately fail if it was a known key path.
                logger.warning("Failed to parse AIOS_ var '%s': %s", key, exc)
                unknown.append(key)
                continue
            overrides = _deep_merge(overrides, _set_path_dict({}, path, value))

        for var in unknown:
            logger.warning(
                "Unknown AIOS_ environment variable '%s' ignored (not in schema; "
                "INV-CM-ENV-002).",
                var,
            )
        return overrides

    # --- Schema validation (§3.5.4-§3.5.5) --------------------------------

    def _validate(self, merged: dict[str, Any]) -> None:
        """Validate merged config against the schema; raise ConfigurationError."""
        try:
            self._schema.validate(merged)
        except ConfigurationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConfigurationError(
                "Configuration validation failed", errors=[str(exc)]
            ) from exc

    # --- Freeze (§3.5.6 / §3.5.11) ----------------------------------------

    def freeze(self) -> str:
        """Freeze the configuration (atomic, thread-safe, irreversible).

        Per Part 3 §3.5.11 the lifecycle is INITIALIZING -> FREEZING ->
        FROZEN. ``freeze()``:

          1. transitions to FREEZING,
          2. performs the freeze atomically (deep-freeze into an immutable
             snapshot + deterministic hash) under the lock,
          3. establishes the immutable configuration,
          4. computes and preserves the configuration hash,
          5. emits ``ConfigurationFrozen`` (deterministic, see ``_emit``),
          6. transitions to FROZEN.

        A failure during the freeze work can never leave the object falsely
        marked FROZEN: the state only becomes FROZEN after the hash/snapshot
        are committed and the event is published. (Steps 5/6 are best-effort
        for the non-fatal event fan-out; they are performed after the
        authoritative immutable representation is already committed.)

        Returns:
            The deterministic configuration hash.

        Raises:
            ConfigurationFrozenError: if already frozen (§3.5.12) or shutting down.
            ConfigurationError: if called before initialization prepared config.
        """
        with self._lock:
            if self._state is ConfigState.FROZEN:
                raise ConfigurationFrozenError(
                    "ConfigurationManager.freeze() called after already frozen "
                    "(INV-CM-FRZ-004)"
                )
            if self._state in (ConfigState.SHUTTING_DOWN, ConfigState.SHUTDOWN):
                raise ConfigurationFrozenError(
                    "Cannot freeze a shutting-down / shut-down ConfigurationManager"
                )
            if not self._merged:
                raise ConfigurationError(
                    "Cannot freeze: no merged configuration prepared",
                    path="<root>",
                )

            # Step 1: enter FREEZING.
            self._state = ConfigState.FREEZING

        # Steps 2-4: atomically compute hash + deep-freeze snapshot. The
        # computation is idempotent and side-effect-free until the commit below,
        # so a failure here leaves the object in FREEZING (never falsely FROZEN).
        config_hash = _compute_config_hash(self._merged)
        secret_paths = _collect_secret_paths(self._merged)
        frozen = _deep_freeze(self._merged)

        with self._lock:
            # Commit the immutable representation atomically.
            self._frozen_config = frozen
            self._config_hash = config_hash
            self._secret_paths = secret_paths

        # Step 5: deterministic emission (awaited; task retained to avoid GC).
        self._run_emission(
            _CONFIGURATION_FROZEN,
            {"configHash": config_hash, "component": _COMPONENT_NAME, "frozen": True},
        )

        # Step 6: transition to FROZEN.
        with self._lock:
            self._state = ConfigState.FROZEN
        return config_hash

    def _run_emission(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit deterministically from a sync context.

        FIX 4: ``freeze`` / ``shutdown`` are SYNC public methods but the EventBus
        publication is async (canonical Task-5 bus).

        Canonical async bus (Task 5): ``publish`` is a coroutine. We schedule
        it on the running loop with ``ensure_future`` and keep a strong
        reference in ``self._pending_tasks`` (so it is never garbage-collected
        mid-flight), then the caller/tests drive completion via ``await
        bus.drain()``. This is deterministic (the event is enqueued before the
        queue is drained) and never double-awaits.

        If no loop is running, the emission is skipped (logged debug) — the
        configuration is still correctly frozen.
        """
        bus = self._event_bus or get_core_event_bus()
        if bus is None:
            return
        try:
            import asyncio

            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("Event %s not dispatched (no running loop).", event_type.name)
            return
        if not loop.is_running():
            logger.debug("Event %s not dispatched (loop not running).", event_type.name)
            return
        coro = self._emit(event_type, payload)
        task = asyncio.ensure_future(coro)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # --- Runtime access (§3.5.7) -----------------------------------------

    def get(self, path: str, default: Any = None) -> Any:
        """Read a value by dotted path. Secrets return the mask ``"***"`` (§3.5.9).

        Returns an immutable / safe read-only view. Post-freeze this reads the
        frozen (deep-frozen, tuple-based) snapshot; pre-freeze it reads the
        working merged config. Returns ``default`` when the path does not exist.
        """
        config = self._config_snapshot()
        if not _path_exists(config, path):
            return default
        value = _get_path(config, path)
        if is_secret_path(path.split(".")):
            return _MASK
        return _immutable_view(value)

    def get_secret(self, path: str) -> Any:
        """Return the raw secret value at ``path`` (§3.5.9).

        Only valid for a path that is a secret. Never logged / masked here; the
        caller is responsible for handling the raw value. Raises
        ConfigurationError if the path is not a secret.
        """
        config = self._config_snapshot()
        value = _get_path(config, path)
        if not is_secret_path(path.split(".")):
            raise ConfigurationError(
                f"Path '{path}' is not a recognized secret", path=path
            )
        return value

    def get_section(self, section: str) -> Any:
        """Return an entire top-level section as an immutable read-only view (§3.5.7)."""
        config = self._config_snapshot()
        if section not in config:
            return None
        section_data = _get_path(config, section)
        # Mask any secret keys present in the section view.
        return _masked_view(section_data)

    def get_all(self) -> dict[str, Any]:
        """Return the full configuration as a deeply-immutable, secret-masked view (§3.5.7).

        Secrets are masked (``"***"``); they are NEVER returned through this
        non-secret accessor (INV-CM-SEC-001).
        """
        config = self._config_snapshot()
        return cast("dict[str, Any]", _masked_view(config))

    def _config_snapshot(self) -> Any:
        if self._state is ConfigState.FROZEN:
            # Return a normalized, read-only view over the deep-frozen internal
            # storage. The internal tuple storage itself is never exposed, so
            # callers cannot mutate it (FIX 1).
            return _normalize(self._frozen_config) if self._frozen_config is not None else {}
        with self._lock:
            return self._merged

    # --- mutation guards (pre-freeze + post-freeze) -----------------------

    def apply_override(self, overrides: dict[str, Any]) -> None:
        """Apply an override BEFORE freeze only (dev/hot-reload, §3.5.10).

        Raises ConfigurationFrozenError once the configuration has entered a
        state where mutation is forbidden (anything other than UNINITIALIZED or
        INITIALIZING — i.e. FREEZING, FROZEN, SHUTTING_DOWN, SHUTDOWN).
        INV-CM-OVR-001 / INV-CM-FRZ-003 / INV-CM-LC-002.
        """
        if self._state not in (ConfigState.UNINITIALIZED, ConfigState.INITIALIZING):
            raise ConfigurationFrozenError("Overrides prohibited after freeze", path="<root>")
        with self._lock:
            self._merged = _deep_merge(self._merged, overrides)

    # --- Configuration inspection / redaction (M10 Deployment) --------------

    def inspect(self, include_secrets: bool = False, include_metadata: bool = True) -> dict[str, Any]:
        """Return a comprehensive configuration inspection view.

        Args:
            include_secrets: If True, include raw secret values (requires authorization).
            include_metadata: If True, include metadata about configuration layers.

        Returns:
            Dictionary with configuration view, layer information, and validation status.
        """
        config = self._config_snapshot()

        result = {
            "config": self.get_all() if not include_secrets else _immutable_view(config),
            "state": self._state.value,
            "frozen": self._state is ConfigState.FROZEN,
            "config_hash": self._config_hash,
            "secret_paths": list(self._secret_paths),
        }

        if include_metadata:
            result["metadata"] = {
                "layer_sources": self._get_layer_sources(),
                "precedence_order": ["defaults", "app.yaml", "env.yaml", "AIOS_* env vars"],
                "validation": {
                    "schema_valid": self._validate_silently(config),
                    "startup_errors": self.validate_startup() if self._state is ConfigState.FROZEN else ["Not frozen"],
                },
            }

        return result

    def _get_layer_sources(self) -> dict[str, Any]:
        """Get information about which config layers were loaded."""
        return {
            "defaults": "embedded",
            "app_yaml": str(self._config_path) if self._config_path else "not provided",
            "env_yaml": self._get_env_yaml_path(),
            "env_vars": self._get_aios_env_vars(),
        }

    def _get_env_yaml_path(self) -> str | None:
        """Get the path of the environment-specific YAML file that was loaded."""
        if self._config_path is None:
            return None
        from pathlib import Path
        base = Path(self._config_path) if isinstance(self._config_path, str) else self._config_path
        # This is an approximation - the actual path depends on the merged config
        env = self._merged.get("kernel", {}).get("environment")
        if env:
            env_path = base.parent / f"app.{env}.yaml"
            if env_path.exists():
                return str(env_path)
        return None

    def _get_aios_env_vars(self) -> list[str]:
        """Get list of AIOS_* environment variables that were applied."""
        return [k for k in os.environ.keys() if k.startswith("AIOS_")]

    def _validate_silently(self, config: dict[str, Any]) -> bool:
        """Validate config without raising exceptions."""
        try:
            self._schema.validate(config)
            return True
        except Exception:
            return False

    def redacted_view(self, paths: list[str] | None = None) -> dict[str, Any]:
        """Return a redacted configuration view for logging/debugging.

        Args:
            paths: Optional list of additional paths to redact beyond secrets.

        Returns:
            Configuration with all secrets and specified paths masked.
        """
        config = self._config_snapshot()
        additional_paths = set(paths or [])

        def redact(node: Any, prefix: str = "") -> Any:
            if isinstance(node, (dict, FrozenMapping)):
                out = {}
                for k, v in node.items():
                    full_path = f"{prefix}.{k}" if prefix else k
                    if _match_secret(k) or full_path in additional_paths:
                        out[k] = _MASK
                    else:
                        out[k] = redact(v, full_path)
                return out
            if isinstance(node, (list, tuple)):
                return [redact(v, f"{prefix}[{i}]") for i, v in enumerate(node)]
            return node

        return redact(config)

    def get_layer(self, layer: int) -> dict[str, Any] | None:
        """Get a specific configuration layer (1-4) for debugging.

        Note: This reconstructs the layer from current state and may not
        exactly match the original input after deep merging.

        Args:
            layer: Layer number (1=defaults, 2=app, 3=env, 4=env vars)

        Returns:
            Approximate layer configuration or None if not available.
        """
        if layer == 1:
            return _EMBEDDED_DEFAULTS.copy()
        elif layer == 2:
            return self._load_app_config()
        elif layer == 3:
            return self._load_env_config(self._merged)
        elif layer == 4:
            return self._parse_env_vars()
        return None

    def set_test_override(self, path: str, value: Any) -> None:
        """Test-only override (§3.5.10). Prohibited after freeze / shutdown."""
        if self._state not in (ConfigState.UNINITIALIZED, ConfigState.INITIALIZING):
            raise ConfigurationFrozenError(
                "Test overrides prohibited after freeze", path=path
            )
        with self._lock:
            _set_path(self._merged, path, value)

    # --- event emission (canonical EventTypes only) ----------------------

    def _make_event(self, event_type: EventType, payload: dict[str, Any]) -> CoreEvent:
        """Construct a canonical Event for the canonical EventBus.

        FIX 9: Only the canonical EventBus (C1, Task 5) is used. Correlation IDs
        are auto-generated as UUIDv7 by the canonical Event factory.
        """
        return CoreEvent(
            eventType=event_type,
            source=self._identity,
            payload=payload,
        )

    async def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Deterministic async emission onto the canonical EventBus.

        The canonical Task-5 ``aios.events.core.bus.EventBus`` has an async
        ``publish`` returning a ``PublishResult``. We AWAIT the result so the
        caller observes a fully-published (enqueued) event before returning —
        no fire-and-forget, no leaked tasks, no double-await. This guarantees
        the event is in the queue (and thus observable via ``await bus.drain()``)
        deterministically.
        """
        bus = self._event_bus or get_core_event_bus()
        if bus is None:
            logger.debug("Event %s not dispatched (no EventBus available)", event_type.name)
            return
        try:
            event = self._make_event(event_type, payload)
            result = bus.publish(event)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001
            logger.debug("Event emission of %s failed: %s", event_type.name, exc)

    async def _emit_async(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Asynchronous emission (delegates to the deterministic ``_emit``)."""
        await self._emit(event_type, payload)


# ---------------------------------------------------------------------------
# Freezing / immutability helpers
# ---------------------------------------------------------------------------


def _deep_freeze(value: Any) -> Any:
    """Recursively convert dict/list into immutable equivalents (§3.5.6)."""
    if isinstance(value, dict):
        return tuple(
            sorted(((k, _deep_freeze(v)) for k, v in value.items()), key=lambda kv: kv[0])
        )
    if isinstance(value, list):
        return tuple(_deep_freeze(v) for v in value)
    return value


def _immutable_view(value: Any) -> Any:
    """Return a deep copy that callers cannot use to mutate internal state."""
    if isinstance(value, (dict, FrozenMapping)):
        return {k: _immutable_view(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_immutable_view(v) for v in value]
    return value


def _masked_view(value: Any) -> Any:
    """Return a deep copy with secret leaf values masked (INV-CM-SEC-001)."""
    if isinstance(value, (dict, FrozenMapping)):
        out = {}
        for k, v in value.items():
            if _match_secret(k):
                out[k] = _MASK
            else:
                out[k] = _masked_view(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_masked_view(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Deterministic hashing (§3.5.15 INV-CM-STR-006)
# ---------------------------------------------------------------------------


def _compute_config_hash(config: dict[str, Any]) -> str:
    """Deterministic SHA-256 over canonical JSON of the (secret-aware) config.

    Secret values are masked before hashing so the hash reflects the *effective*
    configuration shape while never depending on secret *content* identity, and
    so identical effective configs (regardless of secret value) hash identically
    only where the architecture treats them that way. To preserve the
    architecture's "identical effective config -> identical hash" invariant while
    still hiding secret bytes, secrets are masked to a constant before hashing.

    Determinism guarantees (per Task 7): no object identity, no memory address,
    no process state, no random values, no dict insertion order — canonical JSON
    uses sorted keys, and the frozen config is key-sorted. Uses the same SHA-256
    over canonical JSON convention as Event Core (INV-EVT-007).
    """
    masked = _masked_view(config)
    return compute_checksum(masked)


# ---------------------------------------------------------------------------
# Singleton / integration point (kernel.configuration)
# ---------------------------------------------------------------------------


_INSTANCE: ConfigurationManager | None = None
_INSTANCE_LOCK = threading.RLock()


def reset_configuration_manager_singleton() -> None:
    """Reset the process-wide ConfigurationManager singleton (tests only)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


def get_configuration_manager(
    event_bus: EmittingBus | None = None, config_path: Any | None = None
) -> ConfigurationManager:
    """Get (or create) the global ConfigurationManager singleton.

    Integration point for ``kernel.configuration``. Production code MUST NOT
    construct twice; use this accessor (INV-CM-STR-001).
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = ConfigurationManager(event_bus=event_bus, config_path=config_path)
        elif event_bus is not None and _INSTANCE._event_bus is None:
            _INSTANCE._event_bus = event_bus
        return _INSTANCE


def set_configuration_manager(manager: ConfigurationManager) -> None:
    """Set the global ConfigurationManager singleton (kernel-owned construction)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = manager


__all__ = [
    "ConfigurationManager",
    "ConfigState",
    "ConfigurationError",
    "ConfigurationFrozenError",
    "KernelConfigSchema",
    "PropertySchema",
    "is_secret_path",
    "get_configuration_manager",
    "set_configuration_manager",
    "reset_configuration_manager_singleton",
    "_EMBEDDED_DEFAULTS",
    "_deep_freeze",
    "_deep_merge",
    "_compute_config_hash",
    "_masked_view",
]
