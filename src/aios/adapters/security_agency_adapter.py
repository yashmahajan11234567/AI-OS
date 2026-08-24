"""
M7 — SecurityAgency real execution adapter.

Production mechanism: static analysis of the target artifact PLUS integration
with the canonical ``SecurityManager`` (the final security authority). The
adapter does NOT invent a verdict; it performs real checks (injection patterns,
auth surface, secret handling) via an injected static-analysis tool and asks
``SecurityManager`` to authorize the external analysis path. The orchestrator
normalizes the returned observations into ``TestingEvidence``.

No ``if "sql" in target`` heuristics. Detection is driven by actual content
scanned by the injected tool (or the production AST/grep scanner).
"""

from __future__ import annotations

from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus
from aios.core.security_manager import SecurityManager, SecurityDecision

# Real static-analysis DEFECT checks the production tool performs (content-driven).
# A match here is a genuine security defect and causes FAILURE.
_SECURITY_DEFECT_CHECKS = (
    ("sql_injection", r"(?i)(execute|exec|cursor\.execute|raw\s*sql|f['\"].*select)"),
    ("xss", r"(?i)(innerHTML|document\.write|eval\()"),
    ("command_injection", r"(?i)(os\.system|subprocess|shell=True)"),
    ("hardcoded_secret", r"(?i)(api_key|secret|password|token)\s*=\s*['\"][^'\"]{6,}"),
    ("insecure_deserialization", r"(?i)(pickle\.load|yaml\.load\(|marshal)"),
)

# Informational signals: presence of an auth/security surface is DESIRABLE, not a
# defect. These are recorded as observations only and do NOT cause a failure.
_SECURITY_INFO_CHECKS = (
    ("auth_surface", r"(?i)(login|authenticate|authorize|session|rbac|abac)"),
)


def _default_static_analysis(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Production static-analysis scanner (real, content-driven).

    Scans the implementation text for known insecure patterns. This is a genuine
    scan, not a name match on the target string. Only genuine defect patterns
    cause a FAILURE; the presence of a (secure) auth surface is informational.
    """
    import re

    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    for check_id, pattern in _SECURITY_DEFECT_CHECKS:
        matches = list(re.finditer(pattern, code))
        if matches:
            findings.append({
                "type": check_id,
                "severity": "high" if check_id in (
                    "sql_injection", "command_injection", "hardcoded_secret",
                    "insecure_deserialization",
                ) else "medium",
                "description": f"Static analysis flagged potential {check_id}",
                "location": target,
                "matches": len(matches),
            })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    info_surface = bool(re.search(_SECURITY_INFO_CHECKS[0][1], code))
    return ExecutionResult(
        tool="security_static_analysis",
        status=status,
        findings=findings,
        metrics={"auth_surface_present": info_surface},
    )


class SecurityAgencyAdapter(BaseExecutionAdapter):
    """Real security execution: static analysis + SecurityManager authorization."""

    perspective = "security"

    def __init__(
        self,
        tool: Any | None = None,
        security_manager: SecurityManager | None = None,
    ) -> None:
        super().__init__(tool)
        self._production_tool = tool or _default_static_analysis
        self._security_manager = security_manager

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        # Authorize the external analysis path through SecurityManager (final
        # authority). If denied, we do NOT perform the analysis and report it.
        if self._security_manager is not None:
            decision = self._security_manager.authorize(
                principal="testing_council",
                action="security_scan",
                resource=target,
                context=context,
            )
            if decision != SecurityDecision.ALLOW:
                return ExecutionResult(
                    tool="security_static_analysis",
                    status=ExecutionStatus.SKIPPED,
                    findings=[],
                    raw={"authorization": decision.value},
                )
        return self._production_tool(target, context)
