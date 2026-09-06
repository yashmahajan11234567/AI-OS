"""
AI-OS CLI Health Command.

Root-level health alias (aios health) - delegates to kernel health.
Preserves aios kernel health behavior.
"""

import typer
import sys
import json
from pathlib import Path

from aios.cli.output import create_formatter
from aios.core.kernel import CanonicalHealthState
from aios.core.kernel_management import get_kernel

app = typer.Typer(name="health", help="Check kernel health (alias for 'aios kernel health')")


@app.callback(invoke_without_command=True)
def health(
    ctx: typer.Context,
    data_dir: str = typer.Option("/opt/data", "--data-dir", "-d", help="Data directory for health file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Check kernel health (for Docker healthcheck).

    Returns exit code 0 if healthy/degraded, non-zero otherwise.
    With --json, outputs full health report as JSON.

    This is an alias for 'aios kernel health' - preserves existing behavior.
    """
    formatter = create_formatter(json_output)
    context = formatter.context

    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        if context.format.value == "json":
            formatter.print_json({
                "status": "unknown",
                "checks": {}
            })
        else:
            formatter.print_error("Kernel health file not found")
        sys.exit(0)  # Not an error - just unknown state

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        if context.format.value == "json":
            # Enhanced output with canonical state, liveness, readiness
            formatter.print_json(health_data)
            # Exit code based on canonical state
            terminal_states = {CanonicalHealthState.STOPPED.value, CanonicalHealthState.ERROR.value}
            if status in terminal_states:
                sys.exit(1)
            sys.exit(0)

        # Human-readable output
        if status == CanonicalHealthState.RUNNING.value:
            formatter.print_success("Kernel healthy (RUNNING)")
            sys.exit(0)
        elif status == CanonicalHealthState.DEGRADED.value:
            formatter.print_warning("Kernel degraded")
            sys.exit(0)  # Degraded is still considered alive
        elif status == CanonicalHealthState.READY.value:
            formatter.print_success("Kernel ready (READY)")
            sys.exit(0)
        elif status == CanonicalHealthState.STARTING.value:
            formatter.print_warning("Kernel starting")
            sys.exit(1)
        elif status == CanonicalHealthState.STOPPING.value:
            formatter.print_warning("Kernel stopping")
            sys.exit(1)
        elif status == CanonicalHealthState.STOPPED.value:
            formatter.print_error("Kernel stopped")
            sys.exit(1)
        elif status == CanonicalHealthState.ERROR.value:
            formatter.print_error("Kernel error")
            sys.exit(1)
        elif status == CanonicalHealthState.UNHEALTHY.value:
            formatter.print_error("Kernel unhealthy")
            sys.exit(1)
        else:
            formatter.print_error(f"Kernel unknown state: {status}")
            sys.exit(1)
    except Exception as e:
        if context.format.value == "json":
            formatter.print_json({"status": "error", "alive": False, "ready": False, "error": str(e)})
        else:
            formatter.print_error(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()