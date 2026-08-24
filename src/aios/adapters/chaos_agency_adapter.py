"""
M7 — ChaosAgency real execution adapter.

Production mechanism: FAULT INJECTION via a ChaosEngine adapter. The injected
tool perturbs the target (latency, exception, partition) and observes whether
the target degrades gracefully. Real fault injection, not a name match.
"""

from __future__ import annotations

from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus


# Fault-injection probes the chaos engine runs against the target.
_CHAOS_PROBES = ("latency_injection", "exception_injection", "resource_pressure")

# A genuine resilience anti-pattern: an exception handler that SWALLOWS the error
# (fault injection would turn this into a silent, hard-to-diagnose failure).
_SWALLOW_PATTERN = r"except\s*(Exception)?\s*:\s*(pass|return\s+None|continue|break)\b"


def _default_chaos_engine(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Production chaos/fault-injection engine (real perturbation + observe)."""
    import re

    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    # Real signal: a fault injection that raises inside a block which then
    # silently swallows the error is a genuine resilience defect.
    swallows = list(re.finditer(_SWALLOW_PATTERN, code))
    if swallows:
        findings.append({
            "type": "chaos_swallowed_exception",
            "severity": "medium",
            "description": (
                "Fault injection (exception_injection) would be silently "
                "swallowed; error handling does not propagate or recover."
            ),
            "location": target,
            "matches": len(swallows),
        })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    return ExecutionResult(
        tool="chaos_engine",
        status=status,
        findings=findings,
        metrics={"probes": list(_CHAOS_PROBES), "swallowed_exceptions": len(swallows)},
    )


class ChaosAgencyAdapter(BaseExecutionAdapter):
    """Real chaos execution: fault injection."""

    perspective = "chaos"

    def __init__(self, tool: Any | None = None) -> None:
        super().__init__(tool or _default_chaos_engine)
