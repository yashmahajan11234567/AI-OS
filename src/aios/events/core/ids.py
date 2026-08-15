"""
UUIDv7 identifier helper (Part 2 §2.2.1 / INV-EVT-002).

INV-EVT-002 requires ``eventId`` to be a UUIDv7 (RFC 9562) to guarantee global
uniqueness and rough temporal ordering. The Python standard library added
``uuid.uuid7`` only in 3.14; to remain compatible with the project's
``requires-python = ">=3.12"`` floor, the core model generates UUIDv7 directly
from the 48-bit Unix millisecond timestamp and random bits.

INV-EVT-003a: eventId values SHALL NEVER be reused; replay generates new ids
while preserving correlation/causation. This helper only generates new ids.
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a new UUIDv7 (RFC 9562) using the current time.

    Layout (big-endian):
      - 48 bits: unix_ts_ms
      - 4 bits:  version (0b0111)
      - 12 bits: rand_a
      - 2 bits:  variant (0b10)
      - 62 bits: rand_b
    """
    ts_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    value = (
        (ts_ms & 0xFFFFFFFFFFFF) << 80
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return uuid.UUID(int=value)


def is_uuid7(value: uuid.UUID) -> bool:
    """Return True if the UUID is a valid RFC 9562 UUIDv7 (version 7)."""
    return value.version == 7


__all__ = ["uuid7", "is_uuid7"]
