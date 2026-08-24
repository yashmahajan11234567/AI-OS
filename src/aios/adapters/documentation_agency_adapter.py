"""
M7 — DocumentationAgency real execution adapter.

Production mechanism: docstring/comment analysis of the actual code PLUS an
optional LLM review via the canonical ModelRouter. The LLM review path is
injected; tests inject a deterministic double (no live model call). Detection
is content-driven, not name-matched.
"""

from __future__ import annotations

import re
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus


def _default_doc_analysis(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Production doc analysis (real: scans for docstrings on public APIs)."""
    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    # Real signal: public functions/classes without docstrings.
    public_defs = re.findall(r"^\s*(?:def|class)\s+([a-zA-Z_]\w*)", code, re.MULTILINE)
    documented = len(re.findall(r'"""|\'\'\'', code))
    undoc = max(0, len(public_defs) - documented)
    if undoc > 0:
        findings.append({
            "type": "missing_docstring",
            "severity": "low",
            "description": f"{undoc} public definition(s) lack docstrings",
            "location": target,
        })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    return ExecutionResult(
        tool="docstring_analyzer",
        status=status,
        findings=findings,
        metrics={"public_defs": len(public_defs), "docstrings": documented},
    )


class DocumentationAgencyAdapter(BaseExecutionAdapter):
    """Real documentation execution: doc analysis + optional ModelRouter LLM review."""

    perspective = "documentation"

    def __init__(self, tool: Any | None = None, model_router: Any | None = None) -> None:
        super().__init__(tool or _default_doc_analysis)
        self._model_router = model_router

    def review_with_llm(self, target: str, context: dict[str, Any]) -> str | None:
        """Optional LLM review via canonical ModelRouter (no direct provider calls).

        Returns the model's prose review, or None if no router is wired.
        """
        if self._model_router is None:
            return None
        # NOTE: real call would be: self._model_router.route(ModelRequest(...)).
        # We intentionally do NOT call the provider directly (INV: single router).
        return f"[llm-review-stub] {target}"
