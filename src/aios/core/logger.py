"""
Structured Logger for AI-OS Hermes Kernel (Core Component C4, Part 3 §3.6).

This module is now a thin re-export of :mod:`aios.core.structured_logger`, the
authoritative Task 8 implementation of the StructuredLogger Core Component. The
public names previously defined here (``StructuredLogger``, ``BoundLogger``,
``LogContext``, ``JsonFormatter``, ``get_logger``) are preserved so existing
imports and the package ``__init__`` surface remain stable. No behavior is
defined in this file — see ``aios.core.structured_logger`` for the
implementation.
"""

from aios.core.structured_logger import (
    BoundLogger,
    JsonFormatter,
    LogContext,
    StructuredLogger,
    get_logger,
)

__all__ = [
    "StructuredLogger",
    "BoundLogger",
    "LogContext",
    "JsonFormatter",
    "get_logger",
]
