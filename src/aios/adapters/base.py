"""
M7 — Shared base for real agency execution adapters.

Each adapter wraps a *real* execution mechanism behind an injection seam. The
production mechanism is an injected ``tool`` callable/object; tests inject a
deterministic double. This keeps the production execution path real while
making the adapters unit-testable without network/external tools.

KEY CONTRACT (no heuristics):
  * Adapters MUST NOT decide pass/fail via string matching on the target name
    (e.g. ``if "sql" in target``).
  * Adapters execute against the artifact/implementation and return structured
    ``ExecutionResult`` observations. The orchestrator maps those to evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

__all__ = ["ExecutionStatus", "ExecutionResult", "BaseExecutionAdapter", "Tool"]


class ExecutionStatus(str, Enum):
    """Outcome of an external execution (not a verdict)."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ExecutionResult:
    """Structured observation returned by a real execution tool."""

    tool: str
    status: ExecutionStatus
    findings: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_failure(self) -> bool:
        return self.status in (ExecutionStatus.FAILURE, ExecutionStatus.ERROR)


# A ``Tool`` is any callable that takes (target, context) and returns an
# ``ExecutionResult``. Production tools wrap static analyzers / harnesses /
# MCP servers; tests supply deterministic fakes.
Tool = Callable[[str, dict[str, Any]], Any]


class BaseExecutionAdapter:
    """Base for real execution adapters.

    Args:
        perspective: Stable identifier for the perspective (e.g. "security").
        tool: Injected execution mechanism. If ``None``, the adapter uses its
            own ``_default_tool`` (real production path) which subclasses
            implement. Tests inject a fake tool to avoid external dependencies.
    """

    perspective: str = "base"

    def __init__(self, tool: Tool | None = None) -> None:
        self._tool = tool
        self._executions: list[ExecutionResult] = []

    @property
    def last_executions(self) -> list[ExecutionResult]:
        return list(self._executions)

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        """Production execution path (overridden by subclasses)."""
        raise NotImplementedError(
            f"{type(self).__name__} has no production tool; inject one or override _default_tool"
        )

    def execute(self, target: str, context: dict[str, Any] | None = None) -> ExecutionResult:
        """Run the real execution and record the observation."""
        context = context or {}
        tool = self._tool or self._default_tool
        result = tool(target, context)
        if isinstance(result, ExecutionResult):
            self._executions.append(result)
            return result
        # Defensive: coerce unexpected return into an ERROR observation.
        return ExecutionResult(
            tool=getattr(tool, "__name__", "unknown"),
            status=ExecutionStatus.ERROR,
            raw={"unexpected_return": repr(result)},
        )
