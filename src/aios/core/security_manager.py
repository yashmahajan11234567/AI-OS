"""
SecurityManager — the Phase-3 (Governance) Core Manager for AI-OS Hermes Kernel.

SecurityManager is the governance authority for kernel security policy and
authorization. It implements the ICoreManager Protocol (name / phase /
dependencies / initialize / shutdown / health_ready) so LifecycleManager
(Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 3 (alphabetical within phase:
    HealthManager, ResourceManager, SecurityManager — deterministic per
    Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.security``
    (Part 4 §4.7 names the identity ``kernel.security``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.security``, using the same precedent Task 9/10/11/12/13 established
    for ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health``
    / ``core.resource``), using the same "core_manager" metadata envelope
  * reads ``kernel.security.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 14 mapping, same as Tasks 9–13): Part 4 §4.7.10 names events
like ``SecurityAuditEvent`` / ``AuthenticationFailedEvent`` /
``AuthorizationDecisionEvent`` / ``SecretRotatedEvent`` / ``PolicyUpdatedEvent`` /
``TrustBoundaryViolationEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1, Task 2). SecurityManager does NOT invent new
EventTypes. The canonical mapping for the security domain is:

  * Security issue / violation found   -> EventType.SECURITY_ISSUE_FOUND

If a conceptual security event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

NOTE ON ``core.security`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.7): Part 4 §4.7 names SecurityManager's ServiceRegistry identity as
``kernel.security``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10/11/12/13
resolved for StateManager (``core.state``), StorageManager (``core.storage``),
HealthManager (``core.health``), and ResourceManager (``core.resource``).
Per that precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry
identity is ``core.security`` (the ``core.*`` namespace is not reserved and is
NOT a validator exception). The configuration namespace read from C3 remains
``kernel.security.*`` (Part 4 §4.7 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 3) is unchanged.

PHASE DEPENDENCY RULE: SecurityManager is Phase 3. It does NOT declare
ResourceManager or HealthManager as formal dependencies:

    dependencies = ["LifecycleManager"]

The same-phase siblings are ordered deterministically (alphabetical within
Phase 3: HealthManager, ResourceManager, SecurityManager) and the existing
LifecycleManager dependency validator (LM-DEP-003) does not accept same-phase
sibling dependencies. Relying on deterministic alphabetical ordering guarantees
correct sequencing; the SecurityManager/ResourceManager/HealthManager operational
relationship is event-driven (via canonical EventBus), not a lifecycle dependency
edge. SecurityManager likewise does NOT declare the (not-yet-implemented)
WorkflowManager or CapabilityManager as dependencies, which would otherwise fail
boot via LM-DEP-003.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as LifecycleManager /
# StateManager / StorageManager / HealthManager / ResourceManager); these
# modules do not import ``aios.core.security_manager`` at module scope, so there
# is no circular-import risk.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "SecurityManager",
    "SecurityDecision",
    "SecurityViolation",
    "SecurityManagerError",
    "SkillSpecTorGate",
    "SkillSpecTorResult",
    "MCPServerSecurityGate",
    "MCPServerValidationResult",
    "CapabilitySpecValidationResult",
    "get_security_manager",
    "set_security_manager",
    "reset_security_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "SecurityManager"
# Part 4 §4.7 names SecurityManager's ServiceRegistry identity as
# ``kernel.security``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager
# (registering as ``core.lifecycle`` instead of ``kernel.lifecycle``) and
# Task 10/11/12/13 resolved for StateManager (``core.state``), StorageManager
# (``core.storage``), HealthManager (``core.health``), and ResourceManager
# (``core.resource``). We follow that precedent: the compliant,
# INV-SR-NS-002-respecting ServiceRegistry id is ``core.security``. The
# configuration namespace read from C3 remains ``kernel.security.*`` (Part 4
# §4.7 config schema), which is unaffected by the ServiceRegistry id.
_MANAGER_ID = "core.security"
_PHASE = 3  # Phase 3 — "Governance"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 14 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–13):
#   * same-phase siblings (HealthManager, ResourceManager) are NOT dependencies
#     — same-phase deps would be rejected by LifecycleManager's dependency
#     validator (LM-DEP-003); deterministic alphabetical ordering
#     (HealthManager first, then ResourceManager, then SecurityManager) already
#     guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_SECURITY_ISSUE_FOUND = EventType.SECURITY_ISSUE_FOUND

# M4-ADAPTER: SkillSpecTor Security Gate Configuration
# Per C10 architecture decision: LLM stage DISABLED/self-hosted within trust boundary
# SkillSpecTor is an INTEGRATION GATE, not final authority - AI-OS remains final authority
_SKILLSPECTOR_GATE_ENABLED = True
_SKILLSPECTOR_MCP_SERVER_ID = "skillspector"
_SKILLSPECTOR_LLM_STAGE_ENABLED = False  # C10: MUST be disabled/self-hosted within trust boundary
_SKILLSPECTOR_TIMEOUT_SECONDS = 30


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SecurityDecision(str, Enum):  # noqa: UP042 -- matches HealthStatus pattern in sibling managers
    """Authorization decision (Part 4 §4.7.5: ALLOW | DENY | CHALLENGE)."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    CHALLENGE = "CHALLENGE"


@dataclass
class SecurityViolation:
    """A recorded security violation / issue (Part 4 §4.7 AUDIT category)."""

    violation_id: str
    severity: str
    description: str
    category: str = "security"
    context: dict[str, Any] = field(default_factory=dict)


# M4-ADAPTER: SkillSpecTor Security Gate
# ---------------------------------------------------------------------------

@dataclass
class SkillSpecTorResult:
    """Result of SkillSpecTor security validation.

    Attributes:
        passed: Whether the skill passed security validation
        violations: List of security violations found
        scan_duration_ms: Time taken for validation
        scan_id: Unique identifier for this scan
    """
    passed: bool
    violations: list[SecurityViolation]
    scan_duration_ms: int
    scan_id: str


class SkillSpecTorGate:
    """SkillSpecTor Security Gate for AI-OS M4-ADAPTER.

    This gate validates skills BEFORE installation, checking for malicious behavior.
    Per C10 architecture decision: LLM stage is DISABLED/self-hosted within trust boundary.
    SkillSpecTor is an INTEGRATION GATE (not final authority) - AI-OS SecurityManager
    remains the final authority on skill installation.

    The gate performs static analysis of skill specifications including:
    - Entry point validation (no arbitrary code execution paths)
    - Permission analysis (filesystem, network, process access)
    - Dependency vulnerability scanning
    - Configuration schema safety checks
    - Runtime requirement validation
    """

    def __init__(
        self,
        *,
        enabled: bool = _SKILLSPECTOR_GATE_ENABLED,
        mcp_server_id: str = _SKILLSPECTOR_MCP_SERVER_ID,
        llm_stage_enabled: bool = _SKILLSPECTOR_LLM_STAGE_ENABLED,
        timeout_seconds: int = _SKILLSPECTOR_TIMEOUT_SECONDS,
        logger: StructuredLogger | None = None,
    ) -> None:
        """Initialize the SkillSpecTor gate.

        Args:
            enabled: Whether the gate is active
            mcp_server_id: MCP server identifier for the gate
            llm_stage_enabled: Whether LLM-based analysis is enabled (MUST be False per C10)
            timeout_seconds: Timeout for validation
            logger: Optional StructuredLogger for C4 integration
        """
        self._enabled = enabled
        self._mcp_server_id = mcp_server_id
        self._llm_stage_enabled = llm_stage_enabled
        self._timeout_seconds = timeout_seconds
        self._logger = logger

        # C10 enforcement: LLM stage MUST be disabled
        if self._llm_stage_enabled:
            raise SecurityManagerError(
                "SkillSpecTor LLM stage MUST be disabled per C10 architecture decision. "
                "Self-hosted static analysis only within trust boundary.",
                rule_id="C10-LLM-STAGE-DISABLED",
            )

    @property
    def is_enabled(self) -> bool:
        """Check if the gate is enabled."""
        return self._enabled

    def validate_skill_spec(
        self,
        skill_spec: Any,  # SkillSpec from aios.core.skill_spec
    ) -> SkillSpecTorResult:
        """Validate a skill specification for security issues.

        This is the main entry point for M4-ADAPTER skill validation.
        Performs static analysis without LLM (C10: LLM stage disabled/self-hosted).

        Args:
            skill_spec: Parsed SkillSpec to validate

        Returns:
            SkillSpecTorResult with pass/fail, violations, and metadata
        """
        import time
        import uuid

        scan_id = str(uuid.uuid4())
        start_time = time.time()
        violations: list[SecurityViolation] = []

        if not self._enabled:
            return SkillSpecTorResult(
                passed=True,
                violations=[],
                scan_duration_ms=0,
                scan_id=scan_id,
            )

        self._log_debug(f"SkillSpecTor validation started: {scan_id}")

        # 1. Validate entry_point - no arbitrary execution paths
        violations.extend(self._validate_entry_point(skill_spec))

        # 2. Validate permissions - no excessive privileges
        violations.extend(self._validate_permissions(skill_spec))

        # 3. Validate dependencies - no known vulnerable deps
        violations.extend(self._validate_dependencies(skill_spec))

        # 4. Validate config_schema - no unsafe configurations
        violations.extend(self._validate_config_schema(skill_spec))

        # 5. Validate runtime requirements - safe execution environment
        violations.extend(self._validate_runtime(skill_spec))

        # 6. Validate metadata - no spoofing/falsification
        violations.extend(self._validate_metadata(skill_spec))

        scan_duration_ms = int((time.time() - start_time) * 1000)
        passed = len([v for v in violations if v.severity in ("high", "critical")]) == 0

        self._log_debug(
            f"SkillSpecTor validation completed: {scan_id}, "
            f"passed={passed}, violations={len(violations)}, "
            f"duration_ms={scan_duration_ms}"
        )

        return SkillSpecTorResult(
            passed=passed,
            violations=violations,
            scan_duration_ms=scan_duration_ms,
            scan_id=scan_id,
        )

    def _validate_entry_point(self, spec: Any) -> list[SecurityViolation]:
        """Validate entry point for safety."""
        violations = []
        entry_point = getattr(spec, "entry_point", "") or ""

        if not entry_point:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description="Skill missing entry_point - cannot verify execution path",
                category="skill_validation",
                context={"field": "entry_point", "issue": "missing"},
            ))
            return violations

        # Check for suspicious patterns in entry point
        suspicious_patterns = [
            "eval", "exec", "compile", "__import__", "getattr",
            "subprocess", "os.system", "os.popen", "commands.",
            "importlib", "runpy", "code.interact",
        ]

        for pattern in suspicious_patterns:
            if pattern in entry_point:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="critical",
                    description=f"Suspicious pattern in entry_point: {pattern}",
                    category="skill_validation",
                    context={
                        "field": "entry_point",
                        "pattern": pattern,
                        "entry_point": entry_point,
                    },
                ))

        # Validate format (module:function)
        if ":" not in entry_point:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description="Invalid entry_point format - expected 'module:function'",
                category="skill_validation",
                context={"field": "entry_point", "value": entry_point},
            ))

        return violations

    def _validate_permissions(self, spec: Any) -> list[SecurityViolation]:
        """Validate requested permissions."""
        violations = []
        permissions = getattr(spec, "permissions", []) or []

        dangerous_permissions = {
            "process": "Process execution/spawning",
            "network:raw": "Raw socket access",
            "kernel": "Kernel module access",
            "device": "Direct device access",
            "memory": "Direct memory access",
        }

        for perm in permissions:
            if perm in dangerous_permissions:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="high",
                    description=f"Dangerous permission requested: {perm} ({dangerous_permissions[perm]})",
                    category="skill_validation",
                    context={"permission": perm, "description": dangerous_permissions[perm]},
                ))

        # Check for wildcard permissions
        for perm in permissions:
            if "*" in perm or perm == "all":
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="critical",
                    description="Wildcard/all permission requested - violates least privilege",
                    category="skill_validation",
                    context={"permission": perm},
                ))

        return violations

    def _validate_dependencies(self, spec: Any) -> list[SecurityViolation]:
        """Validate dependencies for known issues."""
        violations = []
        dependencies = getattr(spec, "dependencies", []) or []

        # Known problematic packages/patterns
        suspicious_deps = {
            "pwntools": "CTF/exploitation framework",
            "metasploit": "Exploitation framework",
            "impacket": "Network protocol manipulation",
            "scapy": "Packet manipulation (can be used for attacks)",
            "paramiko": "SSH access (if combined with network access)",
            "fabric": "Remote execution",
            "ansible": "Remote execution/orchestration",
        }

        for dep in dependencies:
            dep_lower = dep.lower()
            for suspicious, reason in suspicious_deps.items():
                if suspicious in dep_lower:
                    violations.append(SecurityViolation(
                        violation_id=str(uuid.uuid4()),
                        severity="medium",
                        description=f"Potentially risky dependency: {dep} ({reason})",
                        category="skill_validation",
                        context={"dependency": dep, "reason": reason},
                    ))

        return violations

    def _validate_config_schema(self, spec: Any) -> list[SecurityViolation]:
        """Validate configuration schema for safety."""
        violations = []
        config_schema = getattr(spec, "config_schema", {}) or {}

        def check_schema(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    # Check for dangerous config keys
                    dangerous_keys = ["command", "script", "code", "eval", "exec", "shell", "cmd"]
                    for dk in dangerous_keys:
                        if dk in key.lower():
                            violations.append(SecurityViolation(
                                violation_id=str(uuid.uuid4()),
                                severity="high",
                                description=f"Potentially dangerous config key: {new_path}",
                                category="skill_validation",
                                context={"config_path": new_path, "key": key},
                            ))
                    check_schema(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_schema(item, f"{path}[{i}]")

        check_schema(config_schema)
        return violations

    def _validate_runtime(self, spec: Any) -> list[SecurityViolation]:
        """Validate runtime requirements."""
        violations = []
        runtime = getattr(spec, "runtime", "") or ""
        runtime_version = getattr(spec, "runtime_version", "") or ""

        # Only allow approved runtimes
        approved_runtimes = {"python", "node", "wasm", "deno", "bun"}
        if runtime and runtime not in approved_runtimes:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description=f"Unapproved runtime: {runtime}",
                category="skill_validation",
                context={"runtime": runtime, "approved": list(approved_runtimes)},
            ))

        return violations

    def _validate_metadata(self, spec: Any) -> list[SecurityViolation]:
        """Validate metadata for spoofing/falsification."""
        violations = []

        # Check for spoofed skill_id (e.g., pretending to be builtin)
        skill_id = getattr(spec, "skill_id", "") or ""
        if skill_id.startswith("builtin.") or skill_id.startswith("core."):
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description=f"Skill ID mimics system namespace: {skill_id}",
                category="skill_validation",
                context={"skill_id": skill_id, "issue": "namespace_spoofing"},
            ))

        # Check maturity/stability claims
        maturity = getattr(spec, "maturity", "") or ""
        stability = getattr(spec, "stability", "") or ""
        test_coverage = getattr(spec, "test_coverage", 0.0) or 0.0

        if maturity == "stable" and test_coverage < 0.8:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description=f"Claims 'stable' maturity but test_coverage={test_coverage:.0%}",
                category="skill_validation",
                context={"maturity": maturity, "test_coverage": test_coverage},
            ))

        return violations

    # C4 StructuredLogger integration
    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, component="SkillSpecTorGate", **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, component="SkillSpecTorGate", **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, component="SkillSpecTorGate", **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, component="SkillSpecTorGate", **fields)


# ---------------------------------------------------------------------------
# M5: MCP Server Security Gate
# ---------------------------------------------------------------------------
#
# M5-GATE-REALIZE: Implements the MCPServerSecurityGate modeled after the M4
# SkillSpecTor gate. Per architecture:
# - Gate executes BEFORE connect (C18: gate-before-connect)
# - Performs static/local checks for malformed configuration, unauthorized hosts,
#   dangerous commands, arbitrary code execution indicators, credential exposure,
#   unsafe environment variables, unsafe headers, invalid transport configuration
# - LLM stage MUST remain disabled (C10)
# - The gate is a FILTER, not a second decision authority
# - AI-OS SecurityManager and kernel remain authoritative


@dataclass
class MCPServerValidationResult:
    """Result of MCP server security validation.

    Attributes:
        passed: Whether the server passed security validation
        violations: List of security violations found
        scan_duration_ms: Time taken for validation
        scan_id: Unique identifier for this scan
    """
    passed: bool
    violations: list[SecurityViolation]
    scan_duration_ms: int
    scan_id: str


@dataclass
class CapabilitySpecValidationResult:
    """Result of capability specification security validation.

    Attributes:
        passed: Whether the capability spec passed security validation
        violations: List of security violations found
        scan_duration_ms: Time taken for validation
        scan_id: Unique identifier for this scan
    """
    passed: bool
    violations: list[SecurityViolation]
    scan_duration_ms: int
    scan_id: str


class MCPServerSecurityGate:
    """MCP Server Security Gate for AI-OS M5-GATE-REALIZE.

    This gate validates MCP server configurations BEFORE connection, checking for
    security issues. Per architecture decisions:
    - Gate executes BEFORE connect (C18: gate-before-connect)
    - Performs static/local checks only (no network/subprocess calls during validation)
    - LLM stage DISABLED/self-hosted within trust boundary (C10)
    - The gate is a FILTER (not final authority) - AI-OS SecurityManager remains final authority
    - Fail closed where security is concerned

    The gate validates:
    - Malformed configuration
    - Unauthorized hosts
    - Dangerous commands
    - Arbitrary code execution indicators
    - Credential exposure
    - Unsafe environment variables
    - Unsafe headers
    - Invalid transport configuration
    """

    # Authorized hosts (can be extended via configuration)
    _AUTHORIZED_HOSTS = {
        "localhost", "127.0.0.1", "::1", "0.0.0.0",
        "graphify.local", "agent-reach.local", "hermes-agent.local",
    }

    # Dangerous command patterns
    _DANGEROUS_PATTERNS = [
        "rm -rf", "sudo ", "chmod 777", "chmod +x", "chown root",
        "curl | sh", "wget | sh", "bash -c", "sh -c", "eval ",
        "exec ", "subprocess", "os.system", "popen", "system(",
        "nc -l", "netcat", "socat", "openssl", "ncat ",
    ]

    # Unsafe environment variable patterns
    _UNSAFE_ENV_PATTERNS = [
        "PASSWORD", "SECRET", "TOKEN", "KEY", "PRIVATE", "CREDENTIAL",
        "AWS_SECRET", "GITHUB_TOKEN", "API_KEY", "DATABASE_URL",
        "POSTGRES_PASSWORD", "MYSQL_PASSWORD", "MONGO_URI",
    ]

    # Dangerous headers
    _DANGEROUS_HEADERS = {
        "authorization", "proxy-authorization", "www-authenticate",
        "x-forwarded-for", "x-real-ip", "xff", "cookie", "set-cookie",
    }

    def __init__(
        self,
        *,
        enabled: bool = True,
        authorized_hosts: set[str] | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """Initialize the MCP Server Security Gate.

        Args:
            enabled: Whether the gate is active
            authorized_hosts: Additional authorized hosts (merged with defaults)
            logger: Optional StructuredLogger for C4 integration
        """
        self._enabled = enabled
        self._authorized_hosts = self._AUTHORIZED_HOSTS.copy()
        if authorized_hosts:
            self._authorized_hosts.update(authorized_hosts)
        self._logger = logger

    @property
    def is_enabled(self) -> bool:
        """Check if the gate is enabled."""
        return self._enabled

    def validate_mcp_server_config(
        self,
        server_config: "MCPServerConfig",  # Type imported locally to avoid circular import
    ) -> MCPServerValidationResult:
        """Validate an MCP server configuration for security issues.

        This is the main entry point for M5 MCP server validation.
        Performs static analysis WITHOUT network/subprocess calls.

        Args:
            server_config: MCPServerConfig to validate

        Returns:
            MCPServerValidationResult with pass/fail, violations, and metadata
        """
        import time
        import uuid
        import hashlib

        # Generate deterministic scan_id based on server config
        config_str = f"{server_config.server_id}:{server_config.name}:{server_config.transport.value if server_config.transport else ''}:{server_config.command}:{server_config.url}:{server_config.timeout_seconds}"
        scan_id = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        start_time = time.time()
        violations: list[SecurityViolation] = []

        if not self._enabled:
            return MCPServerValidationResult(
                passed=True,
                violations=[],
                scan_duration_ms=0,
                scan_id=scan_id,
            )

        self._log_debug(f"MCPServerSecurityGate validation started: {scan_id}")

        # 1. Validate transport configuration
        violations.extend(self._validate_transport(server_config))

        # 2. Validate host/URL for unauthorized hosts
        violations.extend(self._validate_host(server_config))

        # 3. Validate command for dangerous patterns (stdio transport)
        violations.extend(self._validate_command(server_config))

        # 4. Validate environment variables for credential exposure
        violations.extend(self._validate_env(server_config))

        # 5. Validate headers for unsafe values
        violations.extend(self._validate_headers(server_config))

        # 6. Validate timeout and retry configuration
        violations.extend(self._validate_params(server_config))

        scan_duration_ms = int((time.time() - start_time) * 1000)
        passed = len([v for v in violations if v.severity in ("high", "critical")]) == 0

        self._log_debug(
            f"MCPServerSecurityGate validation completed: {scan_id}, "
            f"passed={passed}, violations={len(violations)}, "
            f"duration_ms={scan_duration_ms}"
        )

        return MCPServerValidationResult(
            passed=passed,
            violations=violations,
            scan_duration_ms=scan_duration_ms,
            scan_id=scan_id,
        )

    def _validate_transport(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate transport configuration."""
        from aios.core.mcp_manager import MCPTransport

        violations = []

        # Must have a valid transport
        if not config.transport:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="critical",
                description="MCP server missing transport configuration",
                category="mcp_server_validation",
                context={"field": "transport", "issue": "missing"},
            ))
            return violations

        # Validate transport-specific requirements
        if config.transport == MCPTransport.STDIO:
            if not config.command:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="critical",
                    description="STDIO transport requires command",
                    category="mcp_server_validation",
                    context={"field": "command", "issue": "missing_for_stdio"},
                ))
        elif config.transport in (MCPTransport.HTTP, MCPTransport.SSE, MCPTransport.WEBSOCKET):
            if not config.url:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="critical",
                    description=f"{config.transport.value} transport requires URL",
                    category="mcp_server_validation",
                    context={"field": "url", "issue": f"missing_for_{config.transport.value}"},
                ))
            else:
                # Validate URL format based on transport
                if config.transport == MCPTransport.WEBSOCKET:
                    if not (config.url.startswith("ws://") or config.url.startswith("wss://")):
                        violations.append(SecurityViolation(
                            violation_id=str(uuid.uuid4()),
                            severity="high",
                            description=f"Invalid URL scheme for {config.transport.value}: {config.url}",
                            category="mcp_server_validation",
                            context={"field": "url", "value": config.url},
                        ))
                elif not (config.url.startswith("http://") or config.url.startswith("https://")):
                    violations.append(SecurityViolation(
                        violation_id=str(uuid.uuid4()),
                        severity="high",
                        description=f"Invalid URL scheme for {config.transport.value}: {config.url}",
                        category="mcp_server_validation",
                        context={"field": "url", "value": config.url},
                    ))

        return violations

    def _validate_host(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate host/url for unauthorized hosts."""
        violations = []

        if config.url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(config.url)
                host = parsed.hostname or ""

                # Check if host is authorized
                if host and host not in self._authorized_hosts:
                    # Allow localhost variants
                    if not (host.startswith("localhost") or
                            host.startswith("127.") or
                            host.startswith("::1") or
                            host == "0.0.0.0"):
                        violations.append(SecurityViolation(
                            violation_id=str(uuid.uuid4()),
                            severity="high",
                            description=f"Unauthorized host in MCP server URL: {host}",
                            category="mcp_server_validation",
                            context={"field": "url", "host": host, "authorized": list(self._authorized_hosts)},
                        ))
            except Exception as e:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="medium",
                    description=f"Failed to parse MCP server URL: {e}",
                    category="mcp_server_validation",
                    context={"field": "url", "value": config.url, "error": str(e)},
                ))

        return violations

    def _validate_command(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate command for dangerous patterns."""
        from aios.core.mcp_manager import MCPTransport

        violations = []

        if config.transport == MCPTransport.STDIO and config.command:
            cmd_str = " ".join(config.command)

            # Check for dangerous patterns
            for pattern in self._DANGEROUS_PATTERNS:
                if pattern in cmd_str:
                    violations.append(SecurityViolation(
                        violation_id=str(uuid.uuid4()),
                        severity="critical",
                        description=f"Dangerous command pattern detected: {pattern}",
                        category="mcp_server_validation",
                        context={"field": "command", "pattern": pattern, "command": cmd_str},
                    ))

            # Check for suspicious shell interactions
            if any(shell in cmd_str for shell in ["bash", "sh ", "zsh", "fish", "cmd.exe", "powershell"]):
                # Allow if it's a direct script execution (e.g., "python", "node")
                # but flag if it looks like shell command execution
                if not any(safe in cmd_str for safe in ["python", "node", "deno", "bun", "wasm"]):
                    violations.append(SecurityViolation(
                        violation_id=str(uuid.uuid4()),
                        severity="high",
                        description=f"Shell command execution detected: {cmd_str}",
                        category="mcp_server_validation",
                        context={"field": "command", "command": cmd_str},
                    ))

        return violations

    def _validate_env(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate environment variables for credential exposure.

        M8-T6 D-12 remediation: ``config.env`` may be ``None`` (or an empty
        ``dict``). A ``None`` env previously raised ``AttributeError`` on
        ``.items()`` and crashed the entire security gate-before-connect (C18),
        blocking every MCP connection. We guard the iteration while preserving
        the credential checks *verbatim* for any env that actually carries
        variables — no weakening of the credential-rejection logic.
        """
        violations = []

        # D-12 fix: tolerate None / empty env without weakening credential checks.
        if config.env is None or not config.env:
            return violations

        for key, value in config.env.items():
            key_upper = key.upper()

            # Check for unsafe environment variable names
            for pattern in self._UNSAFE_ENV_PATTERNS:
                if pattern in key_upper:
                    violations.append(SecurityViolation(
                        violation_id=str(uuid.uuid4()),
                        severity="critical",
                        description=f"Potential credential exposure in environment variable: {key}",
                        category="mcp_server_validation",
                        context={"field": "env", "key": key, "pattern": pattern},
                    ))

            # Check for long values that might be secrets
            if len(value) > 100 and any(pattern in key_upper for pattern in ["KEY", "SECRET", "TOKEN", "PASSWORD"]):
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="high",
                    description=f"Possible secret value in environment variable: {key}",
                    category="mcp_server_validation",
                    context={"field": "env", "key": key, "length": len(value)},
                ))

        return violations

    def _validate_headers(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate headers for unsafe values."""
        violations = []

        for key, value in config.headers.items():
            key_lower = key.lower()

            # Check for dangerous headers
            if key_lower in self._DANGEROUS_HEADERS:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="high",
                    description=f"Potentially dangerous header: {key}",
                    category="mcp_server_validation",
                    context={"field": "headers", "key": key},
                ))

            # Check for long header values that might contain secrets
            if len(value) > 200:
                violations.append(SecurityViolation(
                    violation_id=str(uuid.uuid4()),
                    severity="medium",
                    description=f"Unusually long header value: {key}",
                    category="mcp_server_validation",
                    context={"field": "headers", "key": key, "length": len(value)},
                ))

        return violations

    def _validate_params(self, config: "MCPServerConfig") -> list[SecurityViolation]:
        """Validate timeout and retry parameters."""
        violations = []

        if config.timeout_seconds <= 0 or config.timeout_seconds > 300:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description=f"Unreasonable timeout: {config.timeout_seconds}s (must be 1-300)",
                category="mcp_server_validation",
                context={"field": "timeout_seconds", "value": config.timeout_seconds},
            ))

        if config.max_retries < 0 or config.max_retries > 10:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description=f"Unreasonable max_retries: {config.max_retries} (must be 0-10)",
                category="mcp_server_validation",
                context={"field": "max_retries", "value": config.max_retries},
            ))

        return violations

    # C4 StructuredLogger integration
    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, component="MCPServerSecurityGate", **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, component="MCPServerSecurityGate", **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, component="MCPServerSecurityGate", **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, component="MCPServerSecurityGate", **fields)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SecurityManagerError(Exception):
    """SecurityManager failure (Part 4 §4.7.11).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` / ``ResourceManagerError``
    (Tasks 9/10/11/12/13).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}:"
                f" {self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# SecurityManager
# ---------------------------------------------------------------------------


class SecurityManager:
    """Phase-3 (Governance) security authority for the Hermes Kernel.

    Provides the kernel security governance surface:
    - Authorization decision-point (fail-closed): every authorization request
      that cannot be affirmatively allowed returns DENY (Part 4 §4.7.13
      CC-SEC-001).
    - Security violation / issue recording, which emits the canonical
      ``SECURITY_ISSUE_FOUND`` event via the canonical EventBus.
    - ICoreManager Core-Manager lifecycle (Task 14 — orchestrated by
      LifecycleManager).

    Architecture contract (mirrors StateManager / StorageManager / HealthManager
    / ResourceManager):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel).
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the Security Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.
        """
        # C2/C3/C4 — injected via DI (Task 14).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01): coroutines
        # scheduled from synchronous business APIs are awaited on the running loop
        # and held here until complete so they are never garbage-collected or left
        # un-awaited. Mirrors the ConfigurationManager ``_pending_tasks`` pattern
        # (Task 7) / StateManager / StorageManager / HealthManager / ResourceManager.
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.7).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 14).
        self._initialized = False
        self._registered_with_sr = False

        # Authorization policy bookkeeping.
        self._deny_unknown_principal: bool = True  # CC-SEC-001 fail-closed.
        self._recorded_violations: dict[str, SecurityViolation] = {}
        self._violations_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._fail_closed = True
        self._audit_all_denials = True

        # M4-ADAPTER: SkillSpecTor Security Gate (C10: LLM stage disabled, self-hosted within trust boundary)
        # SkillSpecTor is an INTEGRATION GATE, not final authority - AI-OS SecurityManager remains final authority
        self._skillspector_gate = SkillSpecTorGate(
            enabled=_SKILLSPECTOR_GATE_ENABLED,
            mcp_server_id=_SKILLSPECTOR_MCP_SERVER_ID,
            llm_stage_enabled=_SKILLSPECTOR_LLM_STAGE_ENABLED,
            timeout_seconds=_SKILLSPECTOR_TIMEOUT_SECONDS,
            logger=self._logger,
        )

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 14 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 3 — Governance, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.security``; Part 4 §4.7 names
        ``kernel.security`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready / StateManager.health_ready /
        StorageManager.health_ready / HealthManager.health_ready /
        ResourceManager.health_ready: ready by construction once the manager has
        completed its own initialization. Returns False before ``initialize()``
        and after ``shutdown()``.
        """
        return self._initialized and self._event_bus is not None

    # ------------------------------------------------------------------
    # ICoreManager: initialization / shutdown
    # ------------------------------------------------------------------

    def _read_config_str(self, path: str, default: str) -> str:
        """Read a string config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_int(self, path: str, default: int) -> int:
        """Read an int config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 3 initialization (called by LifecycleManager).

        Follows the Core Manager pattern (mirrors LifecycleManager.initialize /
        StateManager.initialize / StorageManager.initialize / HealthManager
        .initialize / ResourceManager.initialize): reads ``kernel.security.*``
        configuration from the frozen C3, wires the StructuredLogger (C4),
        registers this manager with the canonical ServiceRegistry (C2) as
        ``core.security``, and marks the manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._fail_closed = self._read_config_bool(
            "kernel.security.failClosed", self._fail_closed
        )
        self._audit_all_denials = self._read_config_bool(
            "kernel.security.auditAllDenials", self._audit_all_denials
        )
        self._deny_unknown_principal = self._read_config_bool(
            "kernel.security.denyUnknownPrincipal", self._deny_unknown_principal
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.security``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"SecurityManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 3 (reverse) shutdown (called by LifecycleManager).

        Clears recorded violations, marks ``core.security`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear recorded violations.
        with self._violations_lock:
            self._recorded_violations.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("SecurityManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror StateManager / StorageManager /
    # HealthManager / ResourceManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register SecurityManager with the ServiceRegistry (C2, Part 4 §4.7).

        Registered as ``core.security`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering SecurityManager.")
            return
        try:
            await sr.register(
                self,
                service_id=_MANAGER_ID,
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "kind": "core_manager",
                    "manager": _NAME,
                    "phase": _PHASE,
                    "lifecycle_state": "INITIALIZED",
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.security`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister.")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(
                f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}"
            )

    # ------------------------------------------------------------------
    # Business API — authorization & violation recording
    # ------------------------------------------------------------------

    def authorize(
        self,
        principal: str | None,
        action: str,
        resource: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> SecurityDecision:
        """Authorize a protected operation (Part 4 §4.7.5 ABAC PDP).

        Fail-closed (CC-SEC-001): a request with an unknown/``None`` principal,
        or any request that cannot be affirmatively allowed, returns DENY. Only
        an explicitly-recognized allow rule yields ALLOW; ambiguous cases return
        CHALLENGE (which callers must treat as a non-ALLOW).

        This is the minimal, architecture-supported authorization surface. No
        policy engine, identity provider, or secret store is invented here; the
        governance contract lives in the kernel's registered security policy, not
        in this manager's scope. ``audit_all_denials`` records a security issue
        for every DENY via the canonical SECURITY_ISSUE_FOUND event.
        """
        if principal is None or principal == "":
            if self._deny_unknown_principal:
                decision = SecurityDecision.DENY
                if self._audit_all_denials:
                    self.record_violation(
                        severity="high",
                        description=(
                            f"Authorization DENY for {action} on {resource}: "
                            f"unknown principal"
                        ),
                        category="authorization",
                        context={
                            "action": action,
                            "resource": resource,
                            "principal": None,
                            "decision": SecurityDecision.DENY.value,
                            **(context or {}),
                        },
                    )
                return decision
        # No explicit allow rule is defined within this manager's scope; the
        # default governance posture is fail-closed (DENY), unless the kernel's
        # owning policy layer has authorized the operation out-of-band.
        if self._fail_closed:
            return SecurityDecision.DENY
        return SecurityDecision.CHALLENGE

    def record_violation(
        self,
        *,
        severity: str,
        description: str,
        category: str = "security",
        context: dict[str, Any] | None = None,
    ) -> SecurityViolation:
        """Record a security violation / issue and emit SECURITY_ISSUE_FOUND.

        The violation is tracked locally (audit trail, CC-SEC-003 attribution)
        and surfaced on the canonical EventBus via the sync-to-async bridge. Only
        the canonical ``EventType.SECURITY_ISSUE_FOUND`` is emitted (CONFLICT E.1
        — Part 4 §4.7.10 names like ``SecurityAuditEvent`` /
        ``AuthenticationFailedEvent`` / ``TrustBoundaryViolationEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        violation = SecurityViolation(
            violation_id=str(uuid.uuid4()),
            severity=severity,
            description=description,
            category=category,
            context=dict(context or {}),
        )
        with self._violations_lock:
            self._recorded_violations[violation.violation_id] = violation

        self._emit_event(_SECURITY_ISSUE_FOUND, violation)
        self._log_debug(
            f"Security violation recorded: {violation.violation_id} ({severity})",
            category=category,
        )
        return violation

    def get_violation(self, violation_id: str) -> SecurityViolation | None:
        """Look up a recorded security violation by id."""
        with self._violations_lock:
            return self._recorded_violations.get(violation_id)

    def list_violations(self) -> list[SecurityViolation]:
        """List all recorded security violations (snapshot)."""
        with self._violations_lock:
            return list(self._recorded_violations.values())

    # ------------------------------------------------------------------
    # M4-ADAPTER: SkillSpecTor Security Gate Integration
    # ------------------------------------------------------------------

    def validate_skill_before_install(
        self,
        skill_spec: Any,  # SkillSpec from aios.core.skill_spec
    ) -> SkillSpecTorResult:
        """Validate a skill specification through the SkillSpecTor gate before installation.

        This is the M4-ADAPTER security gate entry point. Per architecture:
        - Runs BEFORE skill installation
        - LLM stage DISABLED/self-hosted within trust boundary (C10)
        - SkillSpecTor is an INTEGRATION GATE, not final authority
        - AI-OS SecurityManager remains the final authority on installation

        Args:
            skill_spec: Parsed SkillSpec to validate

        Returns:
            SkillSpecTorResult with pass/fail, violations, and metadata

        Emits:
            SECURITY_ISSUE_FOUND events for any high/critical violations found
        """
        if not self._skillspector_gate.is_enabled:
            self._log_debug("SkillSpecTor gate disabled, allowing skill")
            return SkillSpecTorResult(
                passed=True,
                violations=[],
                scan_duration_ms=0,
                scan_id="disabled",
            )

        # Run SkillSpecTor validation
        result = self._skillspector_gate.validate_skill_spec(skill_spec)

        # Emit SECURITY_ISSUE_FOUND for any high/critical violations (audit trail)
        for violation in result.violations:
            if violation.severity in ("high", "critical"):
                self.record_violation(
                    severity=violation.severity,
                    description=f"SkillSpecTor gate: {violation.description}",
                    category="skill_installation_gate",
                    context={
                        "scan_id": result.scan_id,
                        "duration_ms": result.scan_duration_ms,
                        "skill_id": getattr(skill_spec, "skill_id", "unknown"),
                        "skill_name": getattr(skill_spec, "name", "unknown"),
                        **violation.context,
                    },
                )

        self._log_info(
            f"SkillSpecTor gate validation: skill={getattr(skill_spec, 'skill_id', 'unknown')}, "
            f"passed={result.passed}, violations={len(result.violations)}, "
            f"duration_ms={result.scan_duration_ms}"
        )

        return result

    def is_skillspector_gate_enabled(self) -> bool:
        """Check if the SkillSpecTor gate is enabled."""
        return self._skillspector_gate.is_enabled

    # ------------------------------------------------------------------
    # M5-GATE-REALIZE: MCP Server Security Gate Integration
    # ------------------------------------------------------------------

    def validate_mcp_server_before_connect(
        self,
        server_config: "MCPServerConfig",
    ) -> "MCPServerValidationResult":
        """Validate an MCP server configuration through the MCPServerSecurityGate before connection.

        This is the M5-GATE-REALIZE security gate entry point. Per architecture:
        - Runs BEFORE MCP connection (C18: gate-before-connect)
        - Performs static/local checks ONLY (no network/subprocess calls)
        - LLM stage DISABLED/self-hosted within trust boundary (C10)
        - MCPServerSecurityGate is an INTEGRATION FILTER, not final authority
        - AI-OS SecurityManager remains the final authority on connection
        - Fail closed where security is concerned

        Args:
            server_config: MCPServerConfig to validate

        Returns:
            MCPServerValidationResult with pass/fail, violations, and metadata

        Emits:
            SECURITY_ISSUE_FOUND events for any high/critical violations found
            MCP_SERVER_VALIDATION_FAILED event if validation fails
        """
        # Lazy initialization of the MCP gate (to avoid circular imports)
        if not hasattr(self, "_mcp_security_gate"):
            self._mcp_security_gate = MCPServerSecurityGate(
                enabled=True,
                logger=self._logger,
            )

        if not self._mcp_security_gate.is_enabled:
            self._log_debug("MCPServerSecurityGate disabled, allowing connection")
            return MCPServerValidationResult(
                passed=True,
                violations=[],
                scan_duration_ms=0,
                scan_id="disabled",
            )

        # Run MCP server validation
        result = self._mcp_security_gate.validate_mcp_server_config(server_config)

        # Emit SECURITY_ISSUE_FOUND for any high/critical violations (audit trail)
        for violation in result.violations:
            if violation.severity in ("high", "critical"):
                self.record_violation(
                    severity=violation.severity,
                    description=f"MCPServerSecurityGate: {violation.description}",
                    category="mcp_server_connection_gate",
                    context={
                        "scan_id": result.scan_id,
                        "duration_ms": result.scan_duration_ms,
                        "server_id": getattr(server_config, "server_id", "unknown"),
                        "server_name": getattr(server_config, "name", "unknown"),
                        **violation.context,
                    },
                )

        # Emit MCP_SERVER_VALIDATION_FAILED if validation failed
        if not result.passed:
            self._emit_general_event(
                EventType.MCP_SERVER_VALIDATION_FAILED,
                {
                    "server_id": getattr(server_config, "server_id", "unknown"),
                    "server_name": getattr(server_config, "name", "unknown"),
                    "scan_id": result.scan_id,
                    "violations": [
                        {
                            "violation_id": v.violation_id,
                            "severity": v.severity,
                            "description": v.description,
                            "category": v.category,
                            "context": v.context,
                        }
                        for v in result.violations
                    ],
                },
                result.scan_id,
            )

        self._log_info(
            f"MCPServerSecurityGate validation: server={getattr(server_config, 'server_id', 'unknown')}, "
            f"passed={result.passed}, violations={len(result.violations)}, "
            f"duration_ms={result.scan_duration_ms}"
        )

        return result

    # ------------------------------------------------------------------
    # M8-T5: Capability Spec Validation Gate
    # ------------------------------------------------------------------

    def validate_capability_spec(
        self,
        spec: Any,  # CapabilitySpec from aios.core.capability_manifest
    ) -> "CapabilitySpecValidationResult":
        """Validate a capability specification through the capability gate before registration.

        This is the M8-T5 capability security gate entry point. Per architecture:
        - Runs BEFORE capability registration
        - Performs static/local checks ONLY
        - Validates: trust/authority non-escalation, adapter allowlist, manifest integrity,
          operation/security context constraints, no authority claims
        - Capability gate is an INTEGRATION FILTER, not final authority
        - AI-OS SecurityManager remains the final authority on registration
        - Fail closed where security is concerned

        Args:
            spec: CapabilitySpec to validate

        Returns:
            CapabilitySpecValidationResult with pass/fail, violations, and metadata

        Emits:
            SECURITY_ISSUE_FOUND events for any high/critical violations found
        """
        import time
        import uuid

        scan_id = str(uuid.uuid4())[:16]
        start_time = time.time()
        violations: list[SecurityViolation] = []

        self._log_debug(f"CapabilitySpec validation started: {scan_id}")

        # 1. Validate trust_level cannot claim builtin/trusted (external manifest)
        trust_level = getattr(spec, "trust_level", "untrusted")
        if trust_level in ("builtin", "trusted"):
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="critical",
                description=f"External capability cannot claim trust_level={trust_level}",
                category="capability_validation",
                context={"field": "trust_level", "value": trust_level, "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 2. Validate authority_classification cannot claim authoritative
        authority_classification = getattr(spec, "authority_classification", "advisory")
        if authority_classification == "authoritative":
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="critical",
                description="External capability cannot claim authority_classification=authoritative",
                category="capability_validation",
                context={"field": "authority_classification", "value": authority_classification, "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 3. Validate adapter class_path against allowlist (delegated to AdapterFactory)
        adapter_class_path = getattr(spec, "adapter_class_path", "")
        if not adapter_class_path:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description="Capability missing adapter_class_path",
                category="capability_validation",
                context={"field": "adapter_class_path", "issue": "missing", "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 4. Validate allowed_operations are reasonable
        allowed_operations = getattr(spec, "allowed_operations", ())
        if not isinstance(allowed_operations, (list, tuple)):
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description="allowed_operations must be a list or tuple",
                category="capability_validation",
                context={"field": "allowed_operations", "issue": "invalid_type", "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 5. Validate sensitive_keys are reasonable
        sensitive_keys = getattr(spec, "sensitive_keys", ())
        if not isinstance(sensitive_keys, (list, tuple)):
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description="sensitive_keys must be a list or tuple",
                category="capability_validation",
                context={"field": "sensitive_keys", "issue": "invalid_type", "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 6. Validate max_content_size is reasonable
        max_content_size = getattr(spec, "max_content_size", 10240)
        if not isinstance(max_content_size, int) or max_content_size <= 0 or max_content_size > 10485760:  # 10MB max
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="medium",
                description=f"max_content_size must be a positive integer <= 10MB: {max_content_size}",
                category="capability_validation",
                context={"field": "max_content_size", "value": max_content_size, "spec_id": getattr(spec, "capability_id", "unknown")},
            ))

        # 7. Validate capability_id format (no path traversal, no special chars)
        capability_id = getattr(spec, "capability_id", "")
        if not capability_id:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description="Capability missing capability_id",
                category="capability_validation",
                context={"field": "capability_id", "issue": "missing"},
            ))
        elif ".." in capability_id or capability_id.startswith("/") or capability_id.startswith("\\"):
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="critical",
                description=f"Path traversal in capability_id: {capability_id}",
                category="capability_validation",
                context={"field": "capability_id", "value": capability_id},
            ))

        # 8. Validate facade and provider_id
        facade = getattr(spec, "facade", "")
        provider_id = getattr(spec, "provider_id", "")
        if not facade:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description="Capability missing facade",
                category="capability_validation",
                context={"field": "facade", "issue": "missing", "spec_id": capability_id},
            ))
        if not provider_id:
            violations.append(SecurityViolation(
                violation_id=str(uuid.uuid4()),
                severity="high",
                description="Capability missing provider_id",
                category="capability_validation",
                context={"field": "provider_id", "issue": "missing", "spec_id": capability_id},
            ))

        scan_duration_ms = int((time.time() - start_time) * 1000)
        passed = len([v for v in violations if v.severity in ("high", "critical")]) == 0

        # Emit SECURITY_ISSUE_FOUND for any high/critical violations (audit trail)
        for violation in violations:
            if violation.severity in ("high", "critical"):
                self.record_violation(
                    severity=violation.severity,
                    description=f"CapabilitySpec gate: {violation.description}",
                    category="capability_registration_gate",
                    context={
                        "scan_id": scan_id,
                        "duration_ms": scan_duration_ms,
                        "capability_id": capability_id,
                        **violation.context,
                    },
                )

        self._log_info(
            f"CapabilitySpec validation: capability={capability_id}, "
            f"passed={passed}, violations={len(violations)}, "
            f"duration_ms={scan_duration_ms}"
        )

        return CapabilitySpecValidationResult(
            passed=passed,
            violations=violations,
            scan_duration_ms=scan_duration_ms,
            scan_id=scan_id,
        )

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_event(
        self, event_type: EventType, violation: SecurityViolation
    ) -> None:
        """Emit a canonical security event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (``record_violation``) we cannot
        ``await`` it, so this method bridges to the async bus deterministically
        using the architecture-approved sync-to-async bridge established in
        ``ConfigurationManager._run_emission`` (Task 7) and mirrored by
        StateManager / StorageManager / HealthManager / ResourceManager:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion). The event is enqueued on the bus deterministically before
          the next ``await`` yields.
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note. The canonical bus requires a running loop to enqueue;
          synchronously dropping here avoids the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaves a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.7.10 names
        like ``SecurityAuditEvent`` / ``TrustBoundaryViolationEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload={
                "manager": _NAME,
                "manager_id": _MANAGER_ID,
                "issue_id": violation.violation_id,
                "severity": violation.severity,
                # 'category' is a reserved base-contract field (INV-EVT-011);
                # the payload key is 'violation_category' instead.
                "violation_category": violation.category,
                "description": violation.description,
                "context": violation.context,
            },
        )

        # FIX-FIND-01: deterministic sync→async bridge. ONLY create the publish
        # coroutine when there is a loop to drive it; never hand an un-awaited
        # coroutine to the GC (that is the bug under FIND-01).
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — there is nowhere to enqueue the coroutine.
            # Skip rather than leak an un-awaited coroutine.
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        # Strong reference so the task is never GC'd before the bus drains it.
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def _emit_general_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a general canonical event via the canonical EventBus (for non-violation events)."""
        bus = self._event_bus
        if bus is None:
            return

        # Ensure correlation_id is a valid UUID - generate one if it's not
        try:
            corr_uuid = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        except ValueError:
            # Not a valid UUID, generate a deterministic one from the string
            corr_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, correlation_id)

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=corr_uuid,
            payload=payload,
        )
        result = bus.publish(event)

        # FIX-FIND-01: deterministic sync→async bridge
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = result
        task = asyncio.ensure_future(coro, loop=loop)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 14 — replaces stdlib logging)
    # ------------------------------------------------------------------

    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME, **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME, **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME, **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME, **fields)


# ---------------------------------------------------------------------------
# Global SecurityManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_security_manager: SecurityManager | None = None
_security_singleton_lock = threading.Lock()


def get_security_manager() -> SecurityManager:
    """Get or create the global SecurityManager singleton.

    Uses the same lock-guarded pattern as StateManager / StorageManager /
    HealthManager / ResourceManager (Tasks 10/11/12/13) and the C1–C4
    singletons, so concurrent callers cannot double-construct.
    """
    global _global_security_manager
    with _security_singleton_lock:
        if _global_security_manager is None:
            _global_security_manager = SecurityManager()
        return _global_security_manager


def set_security_manager(manager: SecurityManager) -> None:
    """Set the global SecurityManager singleton."""
    global _global_security_manager
    with _security_singleton_lock:
        _global_security_manager = manager


def reset_security_manager_singleton() -> None:
    """Reset the process-wide SecurityManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` /
    ``reset_state_manager_singleton`` / ``reset_storage_manager_singleton`` /
    ``reset_health_manager_singleton`` / ``reset_resource_manager_singleton`` /
    C2–C4 resets.
    """
    global _global_security_manager
    with _security_singleton_lock:
        _global_security_manager = None
