"""AI-OS security utilities package.

Holds shared, architecture-supported security helpers (secret redaction, etc.)
so that no subsystem re-implements redaction ad hoc. These helpers are
fail-safe: if a value cannot be safely inspected it is redacted.
"""
