"""
Provider failure classification for AI-OS ModelRouter.

Provides a structured way to classify provider failures without exposing
sensitive information, enabling proper retry/fallback decisions and
health tracking.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# Retry-After parsing utilities (ported from FreeLLMAPI TypeScript implementation)
MAX_RETRY_AFTER_MS = 24 * 60 * 60 * 1000  # 24 hours

PROTOBUF_DURATION = re.compile(r'^(\d+(?:\.\d+)?)s$')
PROSE_RETRY = re.compile(
    r'(?:try again|retry)\s+(?:in|after)\s+(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hour|hours)\b',
    re.IGNORECASE
)

UNIT_MS = {
    'ms': 1, 's': 1000, 'sec': 1000, 'secs': 1000, 'second': 1000, 'seconds': 1000,
    'm': 60_000, 'min': 60_000, 'mins': 60_000, 'minute': 60_000, 'minutes': 60_000,
    'h': 3_600_000, 'hour': 3_600_000, 'hours': 3_600_000,
}


def parse_retry_after_ms(value: Optional[str]) -> Optional[int]:
    """Parse HTTP Retry-After header into milliseconds.

    Handles both delta-seconds ("120") and HTTP-date ("Wed, 21 Oct 2015 07:28:00 GMT")
    Clamped to MAX_RETRY_AFTER_MS (24 hours)
    """
    if not value:
        return None
    trimmed = value.strip()
    if trimmed.isdigit():
        return min(int(trimmed) * 1000, MAX_RETRY_AFTER_MS)
    try:
        # Try ISO format first
        when = datetime.fromisoformat(trimmed.replace('Z', '+00:00')).timestamp() * 1000
        delay = max(0, int(when - datetime.now().timestamp() * 1000))
        return min(delay, MAX_RETRY_AFTER_MS)
    except (ValueError, AttributeError):
        # Try RFC 1123 / HTTP-date format
        try:
            from email.utils import parsedate_to_datetime
            when = parsedate_to_datetime(trimmed).timestamp() * 1000
            delay = max(0, int(when - datetime.now().timestamp() * 1000))
            return min(delay, MAX_RETRY_AFTER_MS)
        except (ValueError, TypeError, ImportError):
            return None


def clamp_retry_ms(ms: float) -> Optional[int]:
    """Clamp retry delay in milliseconds to valid range."""
    if not isinstance(ms, (int, float)) or ms < 0 or not (ms == ms):  # NaN check
        return None
    return min(int(ms), MAX_RETRY_AFTER_MS)


def find_stated_delay_ms(node: Any, depth: int = 0) -> Optional[int]:
    """DFS search for retryDelay/retry_after fields in error body."""
    if depth > 6 or node is None or not isinstance(node, (dict, list)):
        return None
    if isinstance(node, list):
        for item in node:
            found = find_stated_delay_ms(item, depth + 1)
            if found is not None:
                return found
        return None
    for key, value in node.items():
        normalized = key.lower().replace('_', '').replace('-', '')
        if normalized in ('retrydelay', 'retryafter', 'retryafterseconds'):
            if isinstance(value, str):
                m = PROTOBUF_DURATION.match(value.strip())
                if m:
                    return clamp_retry_ms(float(m.group(1)) * 1000)
                if re.match(r'^\d+(\.\d+)?$', value.strip()):
                    return clamp_retry_ms(float(value) * 1000)
            if isinstance(value, (int, float)):
                return clamp_retry_ms(value * 1000)
        found = find_stated_delay_ms(value, depth + 1)
        if found is not None:
            return found
    return None


def parse_stated_retry_ms(body: Any) -> Optional[int]:
    """Extract stated retry delay from error body (structured + prose).

    1. Structured: google.rpc.RetryInfo retryDelay ("17s"), bare seconds
    2. Prose patterns: "try again in 7.66s", "retry after 30 seconds", "try again in 2m"
    Units supported: ms, s/sec/secs/second/seconds, m/min/mins/minute/minutes, h/hour/hours
    """
    if body is None:
        return None
    if not isinstance(body, str):
        structured = find_stated_delay_ms(body)
        if structured is not None:
            return structured
    text = body if isinstance(body, str) else str(body)
    m = PROSE_RETRY.search(text)
    if m:
        unit = UNIT_MS.get(m.group(2).lower())
        if unit:
            return clamp_retry_ms(float(m.group(1)) * unit)
    return None


def extract_retry_after(headers: dict, body: Any) -> Optional[int]:
    """Main entry: parse Retry-After header first, then body.

    Priority: Retry-After header WINS over body-stated delay
    """
    header_retry = parse_retry_after_ms(headers.get('Retry-After'))
    if header_retry is not None:
        return header_retry
    return parse_stated_retry_ms(body)


class FailureCategory(str, Enum):
    """Provider failure categories."""

    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    INVALID_MODEL = "invalid_model"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout"
    NETWORK = "network"
    SERVER_ERROR = "server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


@dataclass
class ProviderFailure:
    """
    Structured provider failure representation containing only safe
    diagnostic information.

    This class enables provider-agnostic failure handling while preserving
    information needed for retry decisions, fallback eligibility, and
    health tracking.
    """

    category: FailureCategory
    provider_id: str
    model_id: Optional[str] = None
    retryable: bool = False
    fallback_eligible: bool = False
    http_status: Optional[int] = None
    provider_error_code: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds
    safe_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        """Validate failure data after initialization."""
        if self.category == FailureCategory.UNKNOWN and self.retryable:
            # UNKNOWN failures should default to non-retryable unless explicitly set
            # This maintains backward compatibility with existing retry behavior
            pass


# Classification rules mapping
FAILURE_CLASSIFICATION_RULES = {
    FailureCategory.AUTHENTICATION: {
        "retryable": False,
        "fallback_eligible": True,
    },
    FailureCategory.INVALID_REQUEST: {
        "retryable": False,
        "fallback_eligible": False,
    },
    FailureCategory.INVALID_MODEL: {
        "retryable": False,
        "fallback_eligible": True,
    },
    FailureCategory.RATE_LIMIT: {
        "retryable": True,
        "fallback_eligible": True,
    },
    FailureCategory.QUOTA_EXCEEDED: {
        "retryable": False,
        "fallback_eligible": True,
    },
    FailureCategory.TIMEOUT: {
        "retryable": True,
        "fallback_eligible": True,
    },
    FailureCategory.NETWORK: {
        "retryable": True,
        "fallback_eligible": True,
    },
    FailureCategory.SERVER_ERROR: {
        "retryable": True,
        "fallback_eligible": True,
    },
    FailureCategory.SERVICE_UNAVAILABLE: {
        "retryable": True,
        "fallback_eligible": True,
    },
    FailureCategory.UNKNOWN: {
        "retryable": False,  # Default to non-retryable for safety
        "fallback_eligible": False,
    },
}


def classify_failure(
    category: FailureCategory,
    provider_id: str,
    model_id: Optional[str] = None,
    http_status: Optional[int] = None,
    provider_error_code: Optional[str] = None,
    retry_after: Optional[int] = None,
    safe_message: str = "",
) -> ProviderFailure:
    """
    Classify a provider failure according to standardized rules.

    Args:
        category: The failure category
        provider_id: Identifier of the provider that failed
        model_id: Model ID where available
        http_status: HTTP status code where available
        provider_error_code: Provider-specific error code where available
        retry_after: Retry-After value where available (seconds)
        safe_message: Safe diagnostic message (no secrets)

    Returns:
        ProviderFailure instance with classification applied
    """
    rules = FAILURE_CLASSIFICATION_RULES.get(category, FAILURE_CLASSIFICATION_RULES[FailureCategory.UNKNOWN])

    return ProviderFailure(
        category=category,
        provider_id=provider_id,
        model_id=model_id,
        retryable=rules["retryable"],
        fallback_eligible=rules["fallback_eligible"],
        http_status=http_status,
        provider_error_code=provider_error_code,
        retry_after=retry_after,
        safe_message=safe_message,
    )