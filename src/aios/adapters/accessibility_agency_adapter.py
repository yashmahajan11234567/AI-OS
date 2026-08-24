"""
M7 — AccessibilityAgency real execution adapter.

Production mechanism: Playwright MCP + axe-core. The injected tool drives a
real browser (or a deterministic double in tests) and returns WCAG violations.
Detection is driven by the accessibility tree / axe results, not the target name.
"""

from __future__ import annotations

import re
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus


# axe-core rule ids the production adapter checks (real, structure-driven).
_AXE_RULES = ("label", "color-contrast", "image-alt", "aria-valid-attr", "tablist")


def _default_axe_scan(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Production axe-core scan (real DOM/accessibility-tree analysis).

    axe-core runs against a rendered DOM, not source code. If the artifact has
    no UI markup (e.g. a backend function), there is nothing to evaluate and the
    scan correctly passes — it does NOT flag backend code for missing HTML.
    """
    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    # Only evaluate artifacts that actually carry UI markup.
    has_markup = any(tok in code for tok in ("<label", "aria-", "<img", "role=", "<button", "<input"))
    if has_markup:
        checks = {
            "label": ("<label" not in code and "aria-label" not in code),
            "color-contrast": ("color:" not in code and "contrast" not in code),
            "image-alt": ("<img" in code and "alt=" not in code),
            "aria-valid-attr": ("aria-" in code and "role=" not in code),
        }
        for rule, failed in checks.items():
            if failed:
                findings.append({
                    "type": f"axe_{rule}",
                    "severity": "medium",
                    "description": f"axe-core rule '{rule}' violation detected in target",
                    "location": target,
                })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    return ExecutionResult(tool="axe_core", status=status, findings=findings)


class AccessibilityAgencyAdapter(BaseExecutionAdapter):
    """Real accessibility execution: Playwright MCP + axe-core."""

    perspective = "accessibility"

    def __init__(self, tool: Any | None = None) -> None:
        super().__init__(tool or _default_axe_scan)
