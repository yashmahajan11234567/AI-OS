"""
Agent-Reach Adapter for AI-OS M5-GATE-REALIZE.

Provides web/social content ingestion via Agent-Reach MCP server.
Returns untrusted observations that must be normalized before use.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.core.mcp_manager import get_mcp_manager


@dataclass
class AgentReachObservation:
    """Normalized observation from Agent-Reach."""

    content: str
    source: str  # "web", "social", "news", etc.
    source_url: str | None
    fetched_at: datetime
    provenance: dict[str, Any]
    raw_response: dict[str, Any] = field(default_factory=dict)
    trust_level: str = "untrusted"  # Always "untrusted" for external content


class AgentReachAdapter:
    """AI-OS-side Agent-Reach adapter for web/social content ingestion.

    Responsibilities:
    - Invoke Agent-Reach through MCP
    - Obtain web/social content
    - Normalize the returned result
    - Mark result as external/untrusted observation
    - Preserve provenance

    External content MUST NOT automatically become an AI-OS decision.
    Malformed or malicious responses must fail safely.
    """

    def __init__(
        self,
        mcp_manager=None,
        server_id: str = "agent_reach",
    ) -> None:
        """Initialize Agent-Reach adapter.

        Args:
            mcp_manager: MCPManager instance (uses global if None)
            server_id: MCP server identifier for Agent-Reach
        """
        self._mcp_manager = mcp_manager or get_mcp_manager()
        self._server_id = server_id

    async def _ensure_connected(self) -> bool:
        """Ensure connection to Agent-Reach MCP server."""
        status = self._mcp_manager.get_server_status(self._server_id)
        if not status or not status.connected:
            return await self._mcp_manager.connect(self._server_id)
        return True

    def _create_provenance(self, tool_name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create provenance metadata for an observation."""
        provenance = {
            "session_id": f"agent_reach_{datetime.utcnow().timestamp()}",
            "worker": "agent_reach",
            "server": self._server_id,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "ai_os_mcp",
            "interaction": tool_name,
            "source": "agent_reach_adapter",
        }
        if extra:
            provenance.update(extra)
        return provenance

    async def fetch_web(
        self,
        query: str,
        max_results: int = 10,
        source_filter: list[str] | None = None,
    ) -> AgentReachObservation:
        """Fetch web content via Agent-Reach.

        Args:
            query: Search query
            max_results: Maximum number of results
            source_filter: Optional list of sources to include

        Returns:
            Normalized AgentReachObservation (untrusted)
        """
        if not await self._ensure_connected():
            raise RuntimeError("Agent-Reach server not connected")

        arguments = {
            "query": query,
            "max_results": max_results,
        }
        if source_filter:
            arguments["sources"] = source_filter

        call_id = f"web_fetch_{datetime.utcnow().timestamp()}"
        provenance = self._create_provenance("fetch_web", {"query": query})

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "web_search",
                arguments,
                call_id=call_id,
            )

            # Normalize response
            observation = self._normalize_web_result(result, provenance)
            observation.trust_level = "untrusted"

            return observation

        except Exception as e:
            # Return failed observation with error info
            return AgentReachObservation(
                content=f"Fetch failed: {e}",
                source="web",
                source_url=None,
                fetched_at=datetime.utcnow(),
                provenance=provenance,
                raw_response={"error": str(e)},
                trust_level="untrusted",
            )

    async def fetch_social(
        self,
        query: str,
        platform: str | None = None,
        max_results: int = 10,
    ) -> AgentReachObservation:
        """Fetch social media content via Agent-Reach.

        Args:
            query: Search query
            platform: Specific platform (twitter, reddit, linkedin, etc.)
            max_results: Maximum number of results

        Returns:
            Normalized AgentReachObservation (untrusted)
        """
        if not await self._ensure_connected():
            raise RuntimeError("Agent-Reach server not connected")

        arguments = {
            "query": query,
            "max_results": max_results,
        }
        if platform:
            arguments["platform"] = platform

        call_id = f"social_fetch_{datetime.utcnow().timestamp()}"
        provenance = self._create_provenance("fetch_social", {"query": query, "platform": platform})

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "social_search",
                arguments,
                call_id=call_id,
            )

            observation = self._normalize_social_result(result, provenance)
            observation.trust_level = "untrusted"

            return observation

        except Exception as e:
            return AgentReachObservation(
                content=f"Social fetch failed: {e}",
                source="social",
                source_url=None,
                fetched_at=datetime.utcnow(),
                provenance=provenance,
                raw_response={"error": str(e)},
                trust_level="untrusted",
            )

    async def fetch_news(
        self,
        query: str,
        max_results: int = 10,
    ) -> AgentReachObservation:
        """Fetch news content via Agent-Reach.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            Normalized AgentReachObservation (untrusted)
        """
        if not await self._ensure_connected():
            raise RuntimeError("Agent-Reach server not connected")

        arguments = {
            "query": query,
            "max_results": max_results,
        }

        call_id = f"news_fetch_{datetime.utcnow().timestamp()}"
        provenance = self._create_provenance("fetch_news", {"query": query})

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "news_search",
                arguments,
                call_id=call_id,
            )

            observation = self._normalize_news_result(result, provenance)
            observation.trust_level = "untrusted"

            return observation

        except Exception as e:
            return AgentReachObservation(
                content=f"News fetch failed: {e}",
                source="news",
                source_url=None,
                fetched_at=datetime.utcnow(),
                provenance=provenance,
                raw_response={"error": str(e)},
                trust_level="untrusted",
            )

    def _normalize_web_result(self, result: dict[str, Any], provenance: dict[str, Any]) -> AgentReachObservation:
        """Normalize web search result."""
        raw = result.get("result", {}) if result.get("success") else {}
        items = raw.get("results", []) if isinstance(raw, dict) else []

        # Extract content from results
        content_parts = []
        urls = []
        for item in items:
            if isinstance(item, dict):
                title = item.get("title", "")
                snippet = item.get("snippet", item.get("description", ""))
                url = item.get("url", item.get("link", ""))
                if title or snippet:
                    content_parts.append(f"{title}: {snippet}")
                if url:
                    urls.append(url)

        content = "\n\n".join(content_parts) if content_parts else "No results found"
        primary_url = urls[0] if urls else None

        return AgentReachObservation(
            content=content,
            source="web",
            source_url=primary_url,
            fetched_at=datetime.utcnow(),
            provenance=provenance,
            raw_response=raw,
        )

    def _normalize_social_result(self, result: dict[str, Any], provenance: dict[str, Any]) -> AgentReachObservation:
        """Normalize social media search result."""
        raw = result.get("result", {}) if result.get("success") else {}
        items = raw.get("posts", raw.get("results", [])) if isinstance(raw, dict) else []

        content_parts = []
        urls = []
        for item in items:
            if isinstance(item, dict):
                author = item.get("author", item.get("username", ""))
                text = item.get("text", item.get("content", ""))
                url = item.get("url", item.get("link", ""))
                platform = item.get("platform", "")
                if author or text:
                    prefix = f"[{platform}] " if platform else ""
                    content_parts.append(f"{prefix}{author}: {text}")
                if url:
                    urls.append(url)

        content = "\n\n".join(content_parts) if content_parts else "No social results found"
        primary_url = urls[0] if urls else None

        return AgentReachObservation(
            content=content,
            source="social",
            source_url=primary_url,
            fetched_at=datetime.utcnow(),
            provenance=provenance,
            raw_response=raw,
        )

    def _normalize_news_result(self, result: dict[str, Any], provenance: dict[str, Any]) -> AgentReachObservation:
        """Normalize news search result."""
        raw = result.get("result", {}) if result.get("success") else {}
        items = raw.get("articles", raw.get("results", [])) if isinstance(raw, dict) else []

        content_parts = []
        urls = []
        for item in items:
            if isinstance(item, dict):
                title = item.get("title", "")
                description = item.get("description", item.get("content", ""))
                url = item.get("url", item.get("link", ""))
                source = item.get("source", {}).get("name", "") if isinstance(item.get("source"), dict) else item.get("source", "")
                if title or description:
                    prefix = f"[{source}] " if source else ""
                    content_parts.append(f"{prefix}{title}: {description}")
                if url:
                    urls.append(url)

        content = "\n\n".join(content_parts) if content_parts else "No news results found"
        primary_url = urls[0] if urls else None

        return AgentReachObservation(
            content=content,
            source="news",
            source_url=primary_url,
            fetched_at=datetime.utcnow(),
            provenance=provenance,
            raw_response=raw,
        )


def get_agent_reach_adapter(
    mcp_manager=None,
    server_id: str = "agent_reach",
) -> AgentReachAdapter:
    """Get or create Agent-Reach adapter instance."""
    return AgentReachAdapter(mcp_manager=mcp_manager, server_id=server_id)