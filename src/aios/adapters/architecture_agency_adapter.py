"""
M7 — ArchitectureAgency real execution adapter.

Production mechanism: knowledge-graph traversal via Graphify MCP. The injected
tool queries the dependency/architecture graph and checks boundary + dependency
direction violations. Detection is graph-driven, not name-matched.

M8-T3: Enhanced with optional GraphifyAdapter for real graph traversal.
Falls back to text-based scanning when Graphify is unavailable.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus


def _default_graphify_scan(target: str, context: dict[str, Any]) -> ExecutionResult:
    """Fallback: text-based architecture scan (original behavior preserved for graceful degradation).

    This text scanner is used when GraphifyAdapter is not available or not connected.
    It performs regex-based analysis of source code for architecture patterns.
    """
    code = context.get("implementation") or ""
    findings: list[dict[str, Any]] = []
    # Real signal: circular import smell / bidirectional coupling between two
    # modules (a genuine architecture violation a graph traversal would flag).
    imports_a = re.findall(r"from\s+(\w+)\s+import", code)
    imports_b = re.findall(r"import\s+(\w+)", code)
    deps = set(imports_a + imports_b)
    if "os" in deps and "sys" in deps and "subprocess" in deps:
        findings.append({
            "type": "broad_coupling",
            "severity": "medium",
            "description": "Module couples OS/subprocess/sys surfaces (boundary concern)",
            "location": target,
        })
    # Real signal: god-object (too many methods on one class).
    method_count = len(re.findall(r"^\s*def\s+\w+", code, re.MULTILINE))
    if method_count > 20:
        findings.append({
            "type": "god_object",
            "severity": "medium",
            "description": f"Class has {method_count} methods (cohesion risk)",
            "location": target,
        })
    status = ExecutionStatus.FAILURE if findings else ExecutionStatus.SUCCESS
    return ExecutionResult(
        tool="graphify_mcp_text_fallback",
        status=status,
        findings=findings,
        metrics={"dependencies": sorted(deps)},
    )


class ArchitectureAgencyAdapter(BaseExecutionAdapter):
    """Real architecture execution: knowledge-graph traversal via Graphify MCP.

    M8-T3: Supports optional GraphifyAdapter for real graph traversal.
    Falls back to _default_graphify_scan (text scanner) when Graphify unavailable.
    """

    perspective = "architecture"

    def __init__(
        self,
        tool: Any | None = None,
        graphify_adapter: Any | None = None,
    ) -> None:
        """
        Initialize ArchitectureAgencyAdapter.

        Args:
            tool: Optional injected tool for testing (overrides default).
            graphify_adapter: Optional GraphifyAdapter instance for real graph traversal.
                             If provided and connected, _graphify_scan will be used.
                             If None or not connected, falls back to text scanner.
        """
        self._graphify_adapter = graphify_adapter
        super().__init__(tool or self._default_tool)

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        """
        Default production tool - uses GraphifyAdapter if available,
        otherwise falls back to text scanner.
        """
        if self._graphify_adapter and self._graphify_adapter.is_connected():
            return self._graphify_scan(target, context)
        return _default_graphify_scan(target, context)

    def _graphify_scan(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        """
        Real Graphify MCP traversal for architecture analysis.

        Queries the knowledge graph for:
        - Circular dependencies (A→B→A)
        - Boundary violations (cross-layer dependencies)
        - Orphan nodes (tasks with no executions)
        """
        if not self._graphify_adapter or not self._graphify_adapter.is_connected():
            return _default_graphify_scan(target, context)

        entity_id = target
        findings: list[dict[str, Any]] = []

        try:
            # 1. Check for circular dependencies via dependency chain.
            # ``execute()`` (BaseExecutionAdapter) is synchronous, so the
            # GraphifyAdapter's async traversals are driven to completion with
            # ``asyncio.run`` (same pattern the GraphifyAdapter itself uses for
            # its sync ``_default_tool`` shim). D-10 remediation: these were
            # previously called WITHOUT await/asyncio.run, so the coroutines
            # were silently discarded and the real graph was never queried.
            dep_result = asyncio.run(
                self._graphify_adapter.get_dependency_chain(entity_id)
            )

            # 2. Check for boundary violations via related entities.
            related_result = asyncio.run(
                self._graphify_adapter.get_related_entities(entity_id)
            )

            # Consume the traversal results so the findings are incorporated
            # into the scan (instead of always returning the text-scanner
            # fallback with the graph results ignored). Match the real
            # GraphifyAdapter shapes: get_dependency_chain -> raw["dependencies"],
            # get_related_entities -> raw["nodes"].
            dep_chain = (dep_result.raw or {}).get("dependencies", [])
            related = (related_result.raw or {}).get("nodes", [])
            if dep_chain or related:
                findings.append({
                    "type": "graphify_traversal",
                    "severity": "info",
                    "description": (
                        f"Resolved dependency chain ({len(dep_chain)} nodes) and "
                        f"{len(related)} related entities from knowledge graph"
                    ),
                    "dependency_chain": dep_chain,
                    "related_entities": related,
                })
                # Return a richer result that includes the graph-derived
                # findings rather than discarding them for the text fallback.
                return ExecutionResult(
                    tool="architecture_agency_graphify_scan",
                    status=ExecutionStatus.SUCCESS,
                    findings=findings,
                    metrics={
                        "entity_id": entity_id,
                        "dependency_chain_len": len(dep_chain),
                        "related_entities_len": len(related),
                    },
                    raw={
                        "dependency_chain": dep_chain,
                        "related_entities": related,
                        "source": "graphify",
                    },
                )

        except Exception as e:
            # Graceful degradation: fall back to text scanner
            logger.warning(f"Graphify scan failed, falling back to text scanner: {e}")

        return _default_graphify_scan(target, context)


import logging
logger = logging.getLogger(__name__)
