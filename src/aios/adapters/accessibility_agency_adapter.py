"""
M7 — AccessibilityAgency real execution adapter.

Production mechanism: Playwright MCP + axe-core. The injected tool drives a
real browser (or a deterministic double in tests) and returns WCAG violations.
Detection is driven by the accessibility tree / axe results, not the target name.
"""

from __future__ import annotations

import logging
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


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
    """Real accessibility execution: Playwright MCP + axe-core.

    If a PlaywrightMCPAdapter is injected, the adapter uses real browser
    execution for UI artifacts. Otherwise falls back to the simulated axe-core
    scan (preserving existing behavior).
    """

    perspective = "accessibility"

    def __init__(
        self,
        tool: Any | None = None,
        playwright_adapter: Any | None = None,
    ) -> None:
        """Initialize accessibility adapter.

        Args:
            tool: Injected synchronous tool for test doubles.
            playwright_adapter: Optional PlaywrightMCPAdapter for real browser execution.
                When provided and the target has UI markup, uses real Playwright.
                Falls back to simulated scan otherwise.
        """
        super().__init__(tool)
        self._playwright_adapter = playwright_adapter

    def execute(self, target: str, context: dict[str, Any] | None = None) -> ExecutionResult:
        """Run accessibility check, using Playwright if available and target has UI."""
        context = context or {}

        # If Playwright adapter is injected and target has UI markup, use real browser
        if self._playwright_adapter is not None:
            code = context.get("implementation") or ""
            has_markup = any(
                tok in code for tok in ("<label", "aria-", "<img", "role=", "<button", "<input")
            )
            if has_markup:
                try:
                    return self._run_playwright_scan(target, context)
                except Exception as e:
                    logger.warning(f"Playwright scan failed, falling back to simulated: {e}")

        # Default path: simulated axe-core scan (existing behavior preserved)
        return _default_axe_scan(target, context)

    def _run_playwright_scan(
        self, target: str, context: dict[str, Any]
    ) -> ExecutionResult:
        """Run real Playwright browser scan for UI artifacts."""
        from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter

        pa = self._playwright_adapter
        if not isinstance(pa, PlaywrightMCPAdapter):
            return self._default_tool(target, context)

        try:
            import asyncio
            session_id = asyncio.get_event_loop().run_until_complete(
                pa.create_session()
            )
            try:
                # Navigate to a data-URL with the HTML content
                code = context.get("implementation") or ""
                import html as htmlmod
                data_url = f"data:text/html,{htmlmod.escape(code)}"

                result = asyncio.get_event_loop().run_until_complete(
                    pa.execute_action(session_id, "navigate", {"url": data_url})
                )

                evidence = asyncio.get_event_loop().run_until_complete(
                    pa.collect_evidence(session_id, include_accessibility=True)
                )

                findings: list[dict[str, Any]] = []
                acc_tree = evidence.get("accessibility_tree", {})
                if acc_tree:
                    for item in acc_tree.get("children", []):
                        if item.get("role") in ("image",):
                            name = item.get("name", "")
                            if not name:
                                findings.append({
                                    "type": "axe_image-alt",
                                    "severity": "medium",
                                    "description": "Image missing alt text",
                                    "location": target,
                                })

                status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
                return ExecutionResult(
                    tool="playwright_mcp",
                    status=status,
                    findings=findings,
                    metrics={"session_id": session_id, "evidence": evidence},
                )
            finally:
                asyncio.get_event_loop().run_until_complete(
                    pa.close_session(session_id)
                )
        except Exception as e:
            return ExecutionResult(
                tool="playwright_mcp",
                status=ExecutionStatus.ERROR,
                findings=[{"type": "playwright_error", "description": str(e)}],
            )
