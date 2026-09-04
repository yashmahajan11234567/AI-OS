"""
Kernel CLI Commands for AI-OS.
"""

import asyncio
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
from aios.core.kernel import KernelConfig
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
):
    """Check kernel health (for Docker healthcheck)."""
    # This command reads the health status file written by the kernel
    # Returns exit code 0 if healthy, non-zero otherwise
    import sys
    import json
    from pathlib import Path

    health_file = Path(data_dir) / "kernel.health"

    if not health_file.exists():
        print("[bold red]Kernel health file not found[/bold red]")
        sys.exit(1)

    try:
        health_data = json.loads(health_file.read_text())
        status = health_data.get("status", "unknown")

        if status == "healthy":
            print("[bold green]Kernel healthy[/bold green]")
            sys.exit(0)
        elif status == "degraded":
            print("[bold yellow]Kernel degraded[/bold yellow]")
            sys.exit(0)  # Degraded is still considered alive
        elif status == "shutting_down":
            print("[bold yellow]Kernel shutting down[/bold yellow]")
            sys.exit(1)
        else:
            print(f"[bold red]Kernel unhealthy: {status}[/bold red]")
            sys.exit(1)
    except Exception as e:
        print(f"[bold red]Health check failed: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    app()