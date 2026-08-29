"""M9-N5 — Graph-based remediation proposer (spec §11.5).

``GraphRemediationProposer`` consults the Graphify relationship/knowledge
graph (via the M8-T3 ``GraphifyAdapter``) for prior failure/resolution
patterns related to a current failure and returns **advisory suggestions**.
It never executes anything, never mutates state, and never issues verdicts:
every proposal is force-marked advisory through ``mark_capability_advisory``
(spoof-proof re-assertion of source/advisory/authority/trust_level per C14),
so even a hostile graph payload cannot claim authoritative status.

Authority boundary (M9 spec §16): proposals are *input* to PlanningService —
the Councils/Judge remain the sole decision authority and the
WorkflowManager the sole orchestration authority. This service is stateless
per failure; it holds no store of its own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.core.capability_provenance import mark_capability_advisory

logger = logging.getLogger(__name__)

#: Maximum graph nodes consulted per proposal (bounded consultation).
_MAX_GRAPH_NODES = 20

#: Cap on returned suggestions to keep proposals bounded.
_MAX_SUGGESTIONS = 5


@dataclass
class AdvisoryRemediation:
    """An advisory remediation suggestion (never executable).

    ``provenance`` carries C14 fields with ``authority=advisory_only``,
    ``advisory=True``, ``trust_level=untrusted`` — forced via
    :func:`mark_capability_advisory` so external graph data cannot spoof them.
    """

    remediation_id: str
    failure_category: str
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "remediation_id": self.remediation_id,
            "failure_category": self.failure_category,
            "suggestions": list(self.suggestions),
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }


class GraphRemediationProposer:
    """Proposes advisory remediations from the relationship graph.

    Args:
        graphify_adapter: A connected :class:`GraphifyAdapter` (M8-T3). When
            ``None`` or unavailable, every propose call degrades gracefully to
            an empty advisory result (learning/remediation is never load-
            bearing).
    """

    def __init__(self, graphify_adapter: Any | None = None) -> None:
        self._adapter = graphify_adapter

    async def propose(
        self,
        *,
        failure_category: str,
        error_summary: str = "",
        execution_id: str | None = None,
        task_id: str | None = None,
        correlation_id: str | None = None,
    ) -> AdvisoryRemediation:
        """Build an advisory remediation from graph-derived context.

        Queries the graph for related failure/resolution nodes, converts each
        match into a suggestion, and wraps everything in spoof-proof advisory
        provenance. Failures degrade to an empty advisory result — logged, not
        raised (learning must stay non-blocking).
        """
        remediation_id = f"rem_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        suggestions: list[dict[str, Any]] = []
        graph_nodes_consulted = 0
        degraded_reason: str | None = None

        if self._adapter is None:
            degraded_reason = "graphify adapter not configured"
        else:
            try:
                query = self._build_query(failure_category, error_summary)
                result = await self._adapter.query_graph(query, limit=_MAX_GRAPH_NODES)
                nodes = (getattr(result, "raw", None) or {}).get("nodes", [])
                graph_nodes_consulted = len(nodes)
                suggestions = self._extract_suggestions(nodes)
            except Exception as exc:  # noqa: BLE001 — degrade, never block (M9 §24)
                logger.warning(
                    "Graph remediation query failed (degraded to empty): %s",
                    exc,
                )
                degraded_reason = f"graph query failed: {exc}"

        proposal_payload = {
            "remediation_id": remediation_id,
            "failure_category": failure_category,
            "suggestions": suggestions,
            "created_at": datetime.utcnow().isoformat(),
            "graph_nodes_consulted": graph_nodes_consulted,
            "degraded": degraded_reason is not None,
        }
        if degraded_reason:
            proposal_payload["degraded_reason"] = degraded_reason
        del proposal_payload  # payload folded into provenance below

        # Spoof-proof advisory marking (C14): authority/advisory/trust_level
        # are FORCE-SET here regardless of what the graph contained.
        provenance = mark_capability_advisory(
            {
                "operation": "propose_remediation",
                "execution_id": execution_id,
                "task_id": task_id,
                "correlation_id": correlation_id or remediation_id,
                "graph_nodes_consulted": graph_nodes_consulted,
                "degraded": degraded_reason is not None,
                **({"degraded_reason": degraded_reason} if degraded_reason else {}),
            },
            source="graphify_inferred",
            operation="propose_remediation",
            adapter="GraphRemediationProposer",
            capability_id="m9_graph_remediation",
        )
        # Spec §11.5: output forced to advisory_only authority classification.
        # mark_capability_advisory nests its C14 constants under a
        # ``provenance`` key; promote them to the top level too so consumers
        # (and audits) see one flat, consistent provenance block.
        nested = provenance.get("provenance", {})
        for key, value in nested.items():
            provenance.setdefault(key, value)
        for level in (provenance, provenance.get("provenance", {})):
            level["authority"] = "advisory_only"
            level["trust_level"] = "untrusted"
            level["advisory"] = True

        return AdvisoryRemediation(
            remediation_id=remediation_id,
            failure_category=failure_category,
            suggestions=suggestions,
            provenance=provenance,
        )

    def _build_query(self, failure_category: str, error_summary: str) -> str:
        """Deterministic graph query for related failure patterns."""
        category_token = failure_category.replace("'", "")
        summary_token = error_summary.replace("'", "")[:120]
        return (
            "MATCH (n {type: 'failure_resolution'}) "
            f"WHERE n.failure_category = '{category_token}' "
            f"OR n.summary CONTAINS '{summary_token}' "
            f"RETURN n LIMIT {_MAX_GRAPH_NODES}"
        )

    def _extract_suggestions(
        self, nodes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert graph nodes into bounded, non-executable suggestions."""
        suggestions: list[dict[str, Any]] = []
        for node in nodes[:_MAX_SUGGESTIONS]:
            if not isinstance(node, dict):
                continue
            suggestions.append(
                {
                    "source_node_id": node.get("id") or node.get("node_id"),
                    "resolution_hint": node.get("resolution")
                    or node.get("recommended_action"),
                    "preventive_measures": node.get("preventive_measures", []),
                    # Every suggestion inherits advisory semantics explicitly.
                    "advisory": True,
                    "authority": "advisory_only",
                }
            )
        return suggestions


__all__ = ["AdvisoryRemediation", "GraphRemediationProposer"]
