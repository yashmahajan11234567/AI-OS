"""
Central secret redaction for AI-OS (S4 — Terminal 2).

The spec requires secret redaction to be centrally enforced across external
integration errors, exceptions, TestingEvidence, provenance, structured logs,
subprocess failures, and MCP errors. Previously each adapter re-implemented its
own ad-hoc redaction (acp_adapter.py, hermes_bridge.py, playwright_mcp_adapter.py).
This module provides the single canonical utility.

Design constraints (from the FINAL_EXTERNAL_ECOSYSTEM_INTEGRATION_SPEC §4 and the
non-negotiable rules):
- Never expose actual secret values.
- Do not weaken existing secret tests.
- Fail-safe: an unknown/uninspectable value is redacted, never leaked.
- No secrets are persisted into evidence/provenance/logs/exceptions.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Environment-variable name patterns that always hold secrets.
REDACT_ENV_PATTERNS = (
    re.compile(r"(.*_)?(api[_-]?key)(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?secret(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?token(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?password(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?credential(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?private[_-]?key(_.*)?$", re.IGNORECASE),
    re.compile(r"(AWS_SECRET|GITHUB_TOKEN|POSTGRES_PASSWORD|MYSQL_PASSWORD|MONGO_URI|DATABASE_URL)", re.IGNORECASE),
)

# Patterns that reveal a secret *value* inside text (logs, errors, provenance).
REDACT_VALUE_PATTERNS = (
    re.compile(r"(sk-[A-Za-z0-9]{8,})"),                  # OpenAI-style keys
    re.compile(r"(sk-[A-Za-z0-9_-]{20,})"),
    re.compile(r"\b(Bearer\s+[A-Za-z0-9._-]+)"),
    re.compile(r"(password\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)\S+", re.IGNORECASE),
    re.compile(r"(AKIA[0-9A-Z]{16})"),                    # AWS access key id
)

REDACTED = "***REDACTED***"
_REDACT_REPLACEMENTS = {
    "password": r"\1" + REDACTED,
    "api[_-]?key": r"\1" + REDACTED,
    "secret": r"\1" + REDACTED,
    "token": r"\1" + REDACTED,
}


def is_secret_env_key(key: str) -> bool:
    """Return True if an environment variable name almost certainly holds a secret."""
    return any(pattern.match(key) for pattern in REDACT_ENV_PATTERNS)


def redact_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``env`` with secret-valued variables replaced by REDACTED.

    If ``env`` is None, the current ``os.environ`` is used. Never mutates input.
    """
    import os

    source = env if env is not None else dict(os.environ)
    scrubbed: dict[str, str] = {}
    for key, value in source.items():
        if is_secret_env_key(key):
            scrubbed[key] = REDACTED
        else:
            scrubbed[key] = value
    return scrubbed


def redact_text(text: str) -> str:
    """Redact secret *values* appearing inline in free text (logs/errors/provenance)."""
    if not text:
        return text
    result = text
    for pattern in REDACT_VALUE_PATTERNS:
        result = pattern.sub(lambda m: _redact_match(m), result)
    return result


def _redact_match(match: re.Match) -> str:
    """Redact the secret portion of a matched group, preserving the label when present."""
    raw = match.group(0)
    for label_pattern, replacement in _REDACT_REPLACEMENTS.items():
        compiled = re.compile(f"({label_pattern}\\s*[:=]\\s*)\\S+", re.IGNORECASE)
        if compiled.fullmatch(raw):
            return compiled.sub(replacement, raw)
    # Unlabeled secret-shaped token (e.g. sk-... or Bearer ...)
    return REDACTED


def redact_secrets(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact secrets in arbitrary structures (dict/list/tuple/str).

    Used for provenance, evidence, structured-log payloads, and exception
    context. Strings are value-redacted; dict keys that look like secret env
    names have their values replaced; everything else is passed through (or
    stringified + redacted at max depth). Fail-safe: on any inspection error the
    node is replaced with REDACTED rather than leaking.
    """
    if _depth > 12:
        return REDACTED
    try:
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, (bytes, bytearray)):
            return REDACTED
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                kk = str(k)
                if is_secret_env_key(kk) or any(
                    p.match(kk) for p in REDACT_VALUE_PATTERNS
                ):
                    out[kk] = REDACTED
                else:
                    out[kk] = redact_secrets(v, _depth=_depth + 1)
            return out
        if isinstance(value, (list, tuple)):
            out_seq = [redact_secrets(v, _depth=_depth + 1) for v in value]
            return out_seq if isinstance(value, list) else tuple(out_seq)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        # Unknown scalar — stringify and value-redact rather than leak raw form.
        return redact_text(str(value))
    except Exception:
        return REDACTED


def redact_exception(exc: BaseException) -> str:
    """Format an exception message with secrets redacted (for safe logging/evidence)."""
    return redact_text(str(exc))


def redact_json(obj: Any) -> str:
    """Serialize ``obj`` to JSON with secrets redacted; fall back safely on error."""
    try:
        return json.dumps(redact_secrets(obj), default=str)
    except Exception:
        return REDACTED
