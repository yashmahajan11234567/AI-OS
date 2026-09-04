"""
Kernel CLI Commands for AI-OS.
"""

import asyncio
import json
import sys
from pathlib import Path
import typer
from rich import print
from rich.table import Table
from rich.panel import Panel

from aios.core.kernel_management import (
    run_kernel,
    stop_kernel,
    get_kernel,
    is_running,
)
from aios.core.kernel import KernelConfig, CanonicalHealthState
from aios.core.health_manager import HealthManager, get_health_manager, HealthStatus

app = typer.Typer(name="kernel", help="Hermes Kernel management commands")


@app.command(name="start")
def start_cmd(
    config_path: str = typer.Option(None, "--config", "-c", help="Configuration file path"),
    data_dir: str = typer.Option("./data", "--data-dir", "-d", help="Data directory"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    auto_start: bool = typer.Option(True, "--auto-start/--no-auto-start", help="Auto-start services"),
    run_forever: bool = typer.Option(True, "--run-forever/--no-run-forever", help="Run kernel indefinitely until shutdown signal"),
):
    """Start the Hermes Kernel."""
    config = KernelConfig(
        config_path=Path(config_path) if config_path else None,
        data_dir=Path(data_dir),
        log_level=log_level,
        auto_start_services=auto_start,
    )

    async def _start():
        kernel = await run_kernel(config)
        print(Panel.fit(
            f"[bold green]Hermes Kernel started[/bold green]\n"
            f"Name: {kernel.config.name}\n"
            f"Version: {kernel.config.version}\n"
            f"Data Dir: {kernel.config.data_dir}",
            title="Kernel Status",
        ))

        if run_forever:
            await kernel.run_forever()

    asyncio.run(_start())


@app.command(name="stop")
def stop_cmd():
    """Stop the Hermes Kernel."""
    async def _stop():
        await stop_kernel()
        print("[bold yellow]Hermes Kernel stopped[/bold yellow]")

    asyncio.run(_stop())


@app.command(name="status")
def status_cmd():
    """Show kernel status."""
    kernel = get_kernel()
    if not kernel:
        print("[bold red]Kernel not running[/bold red]")
        return

    stats = kernel.get_stats()

    # Core stats
    eb = stats.get("event_bus", {})
    rm = stats.get("resource_manager", {})

    table = Table(title="Kernel Statistics")
    table.add_column("Component", style="cyan")
    table.add_column("Metric", style="green")
    table.add_column("Value", style="yellow")

    table.add_row("Kernel", "Uptime (s)", f"{stats["kernel"]["uptime_seconds"]:.0f}")
    table.add_row("Event Bus", "Events Published", str(eb.get("total_events_published", 0)))
    table.add_row("Event Bus", "Subscriptions", str(eb.get("active_subscriptions", 0)))
    table.add_row("Resource Manager", "Total Allocations", str(rm.get("total_allocations", 0)))

    print(table)


@app.command(name="health")
def health_cmd(
    data_dir: str = typer.Option("/opt/data", "--data-dir", "-d", help="Data directory for health file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Check kernel health (for Docker healthcheck).

    Returns exit code 0 if healthy/degraded, non-zero otherwise.
    With --json, outputs full health report as JSON.
    """
    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        if json_output:
            print(json.dumps({"status": "unknown", "alive": False, "ready": False, "error": "Health file not found"}))
        else:
            print("[bold red]Kernel health file not found[/bold red]")
        sys.exit(1)

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        if json_output:
            # Enhanced output with canonical state, liveness, readiness
            print(json.dumps(health_data, indent=2))
            # Exit code based on canonical state
            terminal_states = {CanonicalHealthState.STOPPED.value, CanonicalHealthState.ERROR.value}
            if status in terminal_states:
                sys.exit(1)
            sys.exit(0)

        # Human-readable output
        if status == CanonicalHealthState.RUNNING.value:
            print("[bold green]Kernel healthy (RUNNING)[/bold green]")
            sys.exit(0)
        elif status == CanonicalHealthState.DEGRADED.value:
            print("[bold yellow]Kernel degraded[/bold yellow]")
            sys.exit(0)  # Degraded is still considered alive
        elif status == CanonicalHealthState.READY.value:
            print("[bold green]Kernel ready (READY)[/bold green]")
            sys.exit(0)
        elif status == CanonicalHealthState.STARTING.value:
            print("[bold yellow]Kernel starting[/bold yellow]")
            sys.exit(1)
        elif status == CanonicalHealthState.STOPPING.value:
            print("[bold yellow]Kernel stopping[/bold yellow]")
            sys.exit(1)
        elif status == CanonicalHealthState.STOPPED.value:
            print("[bold yellow]Kernel stopped[/bold yellow]")
            sys.exit(1)
        elif status == CanonicalHealthState.ERROR.value:
            print("[bold red]Kernel error[/bold red]")
            sys.exit(1)
        elif status == CanonicalHealthState.UNHEALTHY.value:
            print("[bold red]Kernel unhealthy[/bold red]")
            sys.exit(1)
        else:
            print(f"[bold red]Kernel unknown state: {status}[/bold red]")
            sys.exit(1)
    except Exception as e:
        if json_output:
            print(json.dumps({"status": "error", "alive": False, "ready": False, "error": str(e)}))
        else:
            print(f"[bold red]Health check failed: {e}[/bold red]")
        sys.exit(1)


@app.command(name="alive")
def alive_cmd(
    data_dir: str = typer.Option("/opt/data", "--data-dir", "-d", help="Data directory for health file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Liveness check - returns 0 if kernel is responsive and not in terminal state.

    Used by Docker HEALTHCHECK and Kubernetes liveness probes.
    """
    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        if json_output:
            print(json.dumps({"alive": False, "error": "Health file not found"}))
        else:
            print("[bold red]Kernel not alive (no health file)[/bold red]")
        sys.exit(1)

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        # Alive if not in terminal state
        terminal_states = {CanonicalHealthState.STOPPED.value, CanonicalHealthState.ERROR.value}
        alive = status not in terminal_states

        if json_output:
            print(json.dumps({"alive": alive, "status": status}))

        if alive:
            if json_output:
                pass  # Already printed
            else:
                print("[bold green]Kernel alive[/bold green]")
            sys.exit(0)
        else:
            if not json_output:
                print(f"[bold red]Kernel not alive (state: {status})[/bold red]")
            sys.exit(1)
    except Exception as e:
        if json_output:
            print(json.dumps({"alive": False, "error": str(e)}))
        else:
            print(f"[bold red]Liveness check failed: {e}[/bold red]")
        sys.exit(1)


@app.command(name="ready")
def ready_cmd(
    data_dir: str = typer.Option("/opt/data", "--data-dir", "-d", help="Data directory for health file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Readiness check - returns 0 if kernel is ready to accept work.

    Used by Kubernetes readiness probes.
    """
    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        if json_output:
            print(json.dumps({"ready": False, "error": "Health file not found"}))
        else:
            print("[bold red]Kernel not ready (no health file)[/bold red]")
        sys.exit(1)

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        # Ready if in READY or RUNNING state
        ready_states = {CanonicalHealthState.READY.value, CanonicalHealthState.RUNNING.value, CanonicalHealthState.DEGRADED.value}
        ready = status in ready_states

        if json_output:
            print(json.dumps({"ready": ready, "status": status}))

        if ready:
            if not json_output:
                print("[bold green]Kernel ready[/bold green]")
            sys.exit(0)
        else:
            if not json_output:
                print(f"[bold yellow]Kernel not ready (state: {status})[/bold yellow]")
            sys.exit(1)
    except Exception as e:
        if json_output:
            print(json.dumps({"ready": False, "error": str(e)}))
        else:
            print(f"[bold red]Readiness check failed: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    app()