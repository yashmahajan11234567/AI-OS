"""
AI-OS CLI Ready Command.

Root-level ready alias (aios ready) - delegates to kernel ready.
Preserves aios kernel ready behavior.
"""

import typer
import sys
import json
from pathlib import Path

from aios.cli.output import create_formatter
from aios.core.kernel import CanonicalHealthState

app = typer.Typer(name="ready", help="Check kernel readiness (alias for 'aios kernel ready')")


@app.callback(invoke_without_command=True)
def ready(
    ctx: typer.Context,
    data_dir: str = typer.Option("/opt/data", "--data-dir", "-d", help="Data directory for health file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Readiness check - returns 0 if kernel is ready to accept work.

    Used by Kubernetes readiness probes.
    This is an alias for 'aios kernel ready' - preserves existing behavior.
    """
    formatter = create_formatter(json_output)
    context = formatter.context

    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        if context.format.value == "json":
            formatter.print_json({"ready": False, "status": "unknown", "details": {}})
        else:
            formatter.print_error("Kernel not ready (no health file)")
        sys.exit(0)  # Not an error - just unknown state

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        # Ready if in READY or RUNNING state
        ready_states = {CanonicalHealthState.READY.value, CanonicalHealthState.RUNNING.value, CanonicalHealthState.DEGRADED.value}
        ready = status in ready_states

        if context.format.value == "json":
            formatter.print_json({"ready": ready, "status": status})

        if ready:
            if context.format.value != "json":
                formatter.print_success("Kernel ready")
            sys.exit(0)
        else:
            if context.format.value != "json":
                formatter.print_warning(f"Kernel not ready (state: {status})")
            sys.exit(1)
    except Exception as e:
        if context.format.value == "json":
            formatter.print_json({"ready": False, "error": str(e)})
        else:
            formatter.print_error(f"Readiness check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()