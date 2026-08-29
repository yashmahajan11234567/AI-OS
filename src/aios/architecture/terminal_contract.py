"""
M13 — Terminal Architecture & Separation contract enforcement.

Implements the four-terminal authority model defined in
``M13_TERMINAL_HANDOFF_CONTRACT.md``. The contract is the *code-side* authority
boundary that keeps AI-OS as the SOLE governance, verification, decision-making,
judgment, execution, and resource authority across the distributed system.

Terminals (per the contract):

  * T1 (AI-OS Core Orchestration / Hermes Kernel) — SOLE AUTHORITATIVE AUTHORITY.
    Hosts the kernel, core managers, BaseExecutionAdapter framework, MCP manager,
    SecurityManager, canonical event system, self-loop and self-prompt engines.
  * T2 (External Integration Endpoints) — BOUNDED EXECUTION/RESOURCE authority only,
    under AI-OS direction. Hosts the external system adapters (Supabase, n8n,
    Obsidian Git, Notion, Obsidian, Graphify, Claude-Mem, Playwright, Agent Reach,
    FreeLLMAPI) which are BOUNDED RESOURCES.
  * T3 (User Interface & Interaction) — USER INTERFACE ONLY. Hosts the dashboard;
    collects/forwards user approvals; has NO governance/verification/decision
    authority.
  * T4 (Development & Testing) — DEVELOPMENT/TESTING ONLY; no operational authority.

This module is intentionally dependency-light (stdlib + dataclasses/enums) so it
can be imported from adapters, services, the kernel, and tests without pulling in
heavy subsystems. Adapters import ``TERMINAL_ASSIGNMENTS`` to declare which
terminal hosts them; the kernel consults this module to validate that no
external/bounded resource can ever claim a T1 authority.

Authority levels (immutable taxonomy):
  * AUTHORITATIVE — sole AI-OS authority (T1 only)
  * BOUNDED_EXECUTION — may execute only as directed by AI-OS (T2 adapters)
  * BOUNDED_RESOURCE — persistence/knowledge/automation resource under AI-OS (T2)
  * USER_INTERFACE — display + approval collection only (T3)
  * DEVELOPMENT_TESTING — no operational authority (T4)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final

__all__ = [
    "TerminalId",
    "AuthorityLevel",
    "TERMINAL_ASSIGNMENTS",
    "TERMINAL_AUTHORITY",
    "BOUNDED_RESOURCE_ADAPTERS",
    "AuthorityViolation",
    "describe_terminal",
    "adapter_terminal",
    "authority_level_for_adapter",
    "validate_authority_preservation",
    "TerminalContract",
]


class TerminalId(str, Enum):
    """The four M13 terminals."""

    T1_CORE = "T1"
    T2_EXTERNAL = "T2"
    T3_UI = "T3"
    T4_DEV = "T4"


class AuthorityLevel(str, Enum):
    """Authority level a terminal (or component) may hold.

    Only T1 may hold AUTHORITATIVE. Every other level is bounded and explicitly
    denies governance/verification/decision/judgment authority.
    """

    AUTHORITATIVE = "authoritative"          # sole AI-OS authority (T1 only)
    BOUNDED_EXECUTION = "bounded_execution"  # T2: execute only as directed
    BOUNDED_RESOURCE = "bounded_resource"    # T2: persistence/knowledge/automation
    USER_INTERFACE = "user_interface"        # T3: display + approval collection
    DEVELOPMENT_TESTING = "development_testing"  # T4: no operational authority


# Authority level each terminal is permitted to hold.
TERMINAL_AUTHORITY: Final[dict[TerminalId, AuthorityLevel]] = {
    TerminalId.T1_CORE: AuthorityLevel.AUTHORITATIVE,
    TerminalId.T2_EXTERNAL: AuthorityLevel.BOUNDED_RESOURCE,
    TerminalId.T3_UI: AuthorityLevel.USER_INTERFACE,
    TerminalId.T4_DEV: AuthorityLevel.DEVELOPMENT_TESTING,
}

# Which terminal hosts each external integration adapter (T2 = bounded resource).
# These are the BOUNDED RESOURCE components from M13_TERMINAL_HANDOFF_CONTRACT.md.
TERMINAL_ASSIGNMENTS: Final[dict[str, TerminalId]] = {
    "aios.adapters.supabase_adapter.SupabaseAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.n8n_adapter.N8nAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.obsidian_git_adapter.ObsidianGitAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.notion_adapter.NotionAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.obsidian_adapter.ObsidianAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.graphify_adapter.GraphifyAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.claude_mem_adapter.ClaudeMemAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.playwright_mcp_adapter.PlaywrightMCPAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.acp_adapter.ACPAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.agent_reach.AgentReachAdapter": TerminalId.T2_EXTERNAL,
    "aios.adapters.freellmapi.FreeLLMAPIAdapter": TerminalId.T2_EXTERNAL,
}

# Set view for fast membership checks.
BOUNDED_RESOURCE_ADAPTERS: Final[frozenset[str]] = frozenset(TERMINAL_ASSIGNMENTS.keys())

# Authority levels that explicitly DO NOT hold governance/verification/decision
# authority. Used by validation: any component asserting one of these is fine;
# any claiming AUTHORITATIVE outside T1 is a violation.
_NON_AUTHORITATIVE_LEVELS: Final[frozenset[AuthorityLevel]] = frozenset(
    {
        AuthorityLevel.BOUNDED_EXECUTION,
        AuthorityLevel.BOUNDED_RESOURCE,
        AuthorityLevel.USER_INTERFACE,
        AuthorityLevel.DEVELOPMENT_TESTING,
    }
)


@dataclass(frozen=True)
class AuthorityViolation:
    """A detected breach of the terminal authority contract."""

    terminal: str
    component: str
    claimed_level: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminal": self.terminal,
            "component": self.component,
            "claimed_level": self.claimed_level,
            "detail": self.detail,
        }


def describe_terminal(terminal: TerminalId) -> str:
    """Human-readable role description for a terminal."""
    return {
        TerminalId.T1_CORE: "AI-OS Core Orchestration (sole authoritative authority)",
        TerminalId.T2_EXTERNAL: "External Integration Endpoints (bounded resource)",
        TerminalId.T3_UI: "User Interface & Interaction (no authority)",
        TerminalId.T4_DEV: "Development & Testing (no operational authority)",
    }[terminal]


def adapter_terminal(adapter_class_path: str) -> TerminalId | None:
    """Return the terminal that hosts an adapter by its class path, or None."""
    return TERMINAL_ASSIGNMENTS.get(adapter_class_path)


def authority_level_for_adapter(adapter_class_path: str) -> AuthorityLevel:
    """Return the authority level an adapter is permitted to hold.

    External/bounded-resource adapters return BOUNDED_RESOURCE. T1-native
    components (kernel/core managers) are not in TERMINAL_ASSIGNMENTS; callers
    should treat their absence as T1/AUTHORITATIVE.
    """
    term = TERMINAL_ASSIGNMENTS.get(adapter_class_path)
    if term is None:
        return AuthorityLevel.AUTHORITATIVE  # T1-native component
    return TERMINAL_AUTHORITY[term]


def validate_authority_preservation(
    component: str,
    terminal: TerminalId,
    claimed_level: AuthorityLevel,
) -> AuthorityViolation | None:
    """Validate that a component's claimed authority matches its terminal.

    Returns an :class:`AuthorityViolation` if the claim is illegal, else ``None``.

    Rules enforced:
      * Only T1 may hold AUTHORITATIVE. Any other terminal claiming AUTHORITATIVE
        is a hard violation.
      * A terminal may only hold the authority level assigned to it
        (``TERMINAL_AUTHORITY``).
    """
    permitted = TERMINAL_AUTHORITY.get(terminal)
    if permitted is None:
        return AuthorityViolation(
            terminal=terminal.value,
            component=component,
            claimed_level=claimed_level.value,
            detail=f"Unknown terminal {terminal.value}",
        )
    if claimed_level == AuthorityLevel.AUTHORITATIVE and terminal != TerminalId.T1_CORE:
        return AuthorityViolation(
            terminal=terminal.value,
            component=component,
            claimed_level=claimed_level.value,
            detail=(
                "Only T1 (AI-OS Core) may hold AUTHORITATIVE authority; "
                f"{terminal.value} is not permitted to claim it"
            ),
        )
    if claimed_level != permitted:
        return AuthorityViolation(
            terminal=terminal.value,
            component=component,
            claimed_level=claimed_level.value,
            detail=(
                f"{terminal.value} may only hold {permitted.value}; "
                f"claimed {claimed_level.value}"
            ),
        )
    return None


@dataclass
class TerminalContract:
    """Runtime terminal-contract validator and registry.

    The kernel instantiates one of these (or imports the module-level helpers) to
    assert, during boot, that every bounded-resource adapter is hosted on T2 and
    that nothing outside T1 claims AI-OS authority.
    """

    violations: list[AuthorityViolation] = field(default_factory=list)

    def check_adapter(self, adapter_class_path: str) -> AuthorityViolation | None:
        """Validate an adapter's terminal placement.

        Adapters are bounded resources and must be placed on T2. Claims
        AUTHORITATIVE (illegal for a T2 resource) or placement on any terminal
        other than T2 is a violation.
        """
        term = TERMINAL_ASSIGNMENTS.get(adapter_class_path, TerminalId.T2_EXTERNAL)
        violation = validate_authority_preservation(
            component=adapter_class_path,
            terminal=term,
            claimed_level=authority_level_for_adapter(adapter_class_path),
        )
        if violation is not None:
            self.violations.append(violation)
        return violation

    def check_all_adapters(self) -> list[AuthorityViolation]:
        """Validate every known bounded-resource adapter placement."""
        self.violations.clear()
        for adapter_path in TERMINAL_ASSIGNMENTS:
            self.check_adapter(adapter_path)
        return list(self.violations)

    def is_compliant(self) -> bool:
        """No authority violations recorded."""
        return not self.violations
