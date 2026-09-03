"""T1 goal handler — deterministic filesystem write of the goal text.

This module defines the single T1 executable step:

    goal_handler(payload: dict) -> dict

The handler:

  1. Reads the goal text from ``payload["goal"]``.
  2. Reads the output path from ``payload["output_path"]``.
  3. Creates the parent directory if necessary.
  4. Writes the goal text as UTF-8 to ``pathlib.Path(output_path)``.
  5. Computes the SHA-256 of the written content.
  6. Returns ``{"written": path, "bytes": N, "sha256": hex_digest}``.

The handler is intentionally NOT a coroutine and does NOT call any
LLM / external service. It performs a real, deterministic filesystem
write. It is registered at runtime by
:mod:`aios.goals.entry_point` under the service name
``"goal.handler.v1"`` (see :mod:`aios.goals.adapter`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def goal_handler(payload: dict[str, Any]) -> dict[str, Any]:
    """Perform the T1 deterministic filesystem write.

    Args:
        payload: A dict that must contain at least:
            * ``"goal"`` (str): The goal text to write.
            * ``"output_path"`` (str): The filesystem path to write to.

            Other keys (``plan_id``, ``task_id``, ``execution_id``,
            ``step_id``, ``correlation_id``, ``planning_labels``) are
            ignored by this handler. The WorkflowManager merges those into
            the payload automatically when invoking the step handler
            (see ``aios.core.workflow._execute_step``).

    Returns:
        A dict ``{"written": str, "bytes": int, "sha256": str}`` where
        ``written`` is the resolved path, ``bytes`` is the integer count
        of bytes written (UTF-8 encoded), and ``sha256`` is the lowercase
        hex digest of the written bytes.

    Raises:
        ValueError: If ``goal`` or ``output_path`` is missing/empty.
        OSError: If the filesystem write fails for any reason
            (propagated unchanged from ``pathlib``).
    """
    goal = payload.get("goal")
    if not isinstance(goal, str):
        raise ValueError("payload['goal'] is required and must be a str")

    output_path_raw = payload.get("output_path")
    if not output_path_raw:
        raise ValueError("payload['output_path'] is required and must be non-empty")
    if not isinstance(output_path_raw, (str, Path)):
        raise ValueError(
            "payload['output_path'] must be a str or pathlib.Path, "
            f"got {type(output_path_raw).__name__}"
        )

    output_path = Path(output_path_raw)

    # Create parent directory if needed. This is deterministic and
    # idempotent: parents_ok=True is the default for ``mkdir``.
    parent = output_path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    # Encode the goal deterministically as UTF-8. We encode first so
    # ``bytes`` and ``sha256`` reflect the exact bytes written to disk.
    encoded = goal.encode("utf-8")

    # Write the bytes. Using ``write_bytes`` is the most direct path;
    # the handler does not pretend this is an LLM-generated artifact.
    output_path.write_bytes(encoded)

    # Compute SHA-256 of the EXACT bytes we just wrote. We read from
    # memory (the encoded buffer) rather than re-reading the file, so
    # the digest matches the bytes that landed on disk for THIS call
    # even if the file is concurrently modified by something else
    # (deterministic with respect to the handler's own write).
    digest = hashlib.sha256(encoded).hexdigest()

    return {
        "written": str(output_path),
        "bytes": len(encoded),
        "sha256": digest,
    }


__all__ = ["goal_handler"]
