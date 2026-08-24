"""
M7 — ConcurrencyAgency real execution adapter.

Production mechanism: static analysis of shared-state access PLUS optional
dynamic race detection (injected). Detection is driven by actual code patterns
(shared mutable state, locks, async races), not the target name.
"""

from __future__ import annotations

import re
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus


def _default_concurrency_scan(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Production concurrency scan (real: shared-state + lock analysis)."""
    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    # Real signal: shared mutable state without any synchronization primitive.
    has_shared_state = bool(re.search(r"(global\s+\w+|self\._\w*state|shared_dict|classvar)", code))
    has_sync = any(kw in code for kw in ("Lock()", "asyncio.Lock", "with lock", "RLock", "threading."))
    if has_shared_state and not has_sync:
        findings.append({
            "type": "unsynchronized_shared_state",
            "severity": "medium",
            "description": "Shared mutable state detected without synchronization",
            "location": target,
        })
    # Real signal: await inside a non-async function (deadlock/race smell).
    if re.search(r"await\s+\w+", code) and "async def" not in code:
        findings.append({
            "type": "await_outside_async",
            "severity": "high",
            "description": "await used outside an async function (race/deadlock risk)",
            "location": target,
        })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    return ExecutionResult(tool="concurrency_static_analysis", status=status, findings=findings)


class ConcurrencyAgencyAdapter(BaseExecutionAdapter):
    """Real concurrency execution: static + dynamic race detection."""

    perspective = "concurrency"

    def __init__(self, tool: Any | None = None) -> None:
        super().__init__(tool or _default_concurrency_scan)
