"""
AI-OS CLI Status Command.

Root-level status command showing system status from authoritative sources.
"""

import typer
from typing import Optional
from rich.table import Table
from rich.panel import Panel

from aios.cli.output import create_formatter, OutputContext
from aios.core.kernel_management import get_kernel, is_running
from aios.core.lifecycle_manager import get_lifecycle_manager, LifecycleState
from aios.core.health_manager import get_health_manager, HealthStatus

app = typer.Typer(name="status", help="Show AI-OS system status")


@app.callback(invoke_without_command=True)
def status(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Show AI-OS system status.

    Uses authoritative sources:
    - LifecycleManager.state
    - HealthManager status
    - HermesKernel.get_stats()
    - Service status
    """
    formatter = create_formatter(json_output)
    context = formatter.context

    # Get kernel - handle case where not initialized
    try:
        kernel = get_kernel()
        lifecycle = get_lifecycle_manager()
        health_mgr = get_health_manager()
    except RuntimeError:
        kernel = None
        lifecycle = None
        health_mgr = None

    # Build status data
    status_data = {
        "status": "RUNNING" if is_running() else "STOPPED",
        "lifecycle_state": None,
        "health": {
            "overall_status": None,
            "details": None,
        },
        "kernel": {
            "running": is_running(),
            "stats": {},
        },
        "services": {},
    }

    # Lifecycle state
    if lifecycle:
        status_data["lifecycle_state"] = lifecycle.state.value

    # Health status
    if health_mgr:
        status_data["health"]["overall_status"] = health_mgr.overall_status.value
        status_data["health"]["details"] = health_mgr.get_all_health()

    # Kernel stats
    if kernel and is_running():
        try:
            stats = kernel.get_stats()
            status_data["kernel"]["stats"] = stats
        except Exception as e:
            status_data["kernel"]["stats_error"] = str(e)

    # Kernel stats
    if kernel and is_running():
        try:
            stats = kernel.get_stats()
            status_data["kernel_stats"] = stats
        except Exception as e:
            status_data["kernel_stats_error"] = str(e)

    # Service status (from kernel if available)
    if kernel and hasattr(kernel, '_services'):
        services = {}
        for name, svc_status in kernel._services.items():
            services[name] = {
                "started": svc_status.started,
                "healthy": svc_status.healthy,
                "started_at": svc_status.started_at.isoformat() if svc_status.started_at else None,
                "last_error": svc_status.last_error,
            }
        status_data["services"] = services

    if context.format.value == "json":
        formatter.print_json(status_data)
        return

    # Human-readable output
    if is_running():
        formatter.print_success("AI-OS Kernel: RUNNING")
    else:
        formatter.print_error("AI-OS Kernel: NOT RUNNING")

    # Lifecycle panel
    if lifecycle:
        state = lifecycle.state
        state_color = {
            LifecycleState.OPERATIONAL: "green",
            LifecycleState.DEGRADED: "yellow",
            LifecycleState.INITIALIZING: "blue",
            LifecycleState.SHUTTING_DOWN: "yellow",
            LifecycleState.TERMINATED: "red",
            LifecycleState.ROLLBACK_IN_PROGRESS: "red",
            LifecycleState.RECOVERY_IN_PROGRESS: "blue",
            LifecycleState.UNINITIALIZED: "dim",
        }.get(state, "white")

        formatter.print_panel(
            f"State: [{state_color}]{state.value}[/{state_color}]\n"
            f"Initialized: {lifecycle.initialized_managers}",
            title="Lifecycle Manager",
            style=state_color,
        )

    # Health panel
    if health_mgr:
        health = health_mgr.overall_status
        health_color = {
            HealthStatus.HEALTHY: "green",
            HealthStatus.DEGRADED: "yellow",
            HealthStatus.UNHEALTHY: "red",
            HealthStatus.UNKNOWN: "dim",
        }.get(health, "white")

        all_health = health_mgr.get_all_health()
        details = "\n".join([
            f"  {comp}: [{health_color}]{status}[/{health_color}]"
            for comp, status in all_health.get("components", {}).items()
        ])

        formatter.print_panel(
            f"Overall: [{health_color}]{health.value}[/{health_color}]\n"
            f"Total Checks: {all_health.get('total_checks', 0)}\n"
            f"Healthy: {all_health.get('healthy_checks', 0)}  "
            f"Degraded: {all_health.get('degraded_checks', 0)}  "
            f"Unhealthy: {all_health.get('unhealthy_checks', 0)}\n"
            f"{details}",
            title="Health Manager",
            style=health_color,
        )

    # Kernel stats
    if kernel and is_running():
        stats = status_data["kernel_stats"]
        if stats:
            eb = stats.get("event_bus", {})
            rm = stats.get("resource_manager", {})

            table = Table(title="Kernel Statistics")
            table.add_column("Component", style="cyan")
            table.add_column("Metric", style="green")
            table.add_column("Value", style="yellow")

            table.add_row("Kernel", "Uptime (s)", f"{stats.get('kernel', {}).get('uptime_seconds', 0):.0f}")
            table.add_row("Event Bus", "Events Published", str(eb.get("total_events_published", 0)))
            table.add_row("Event Bus", "Subscriptions", str(eb.get("active_subscriptions", 0)))
            table.add_row("Resource Manager", "Total Allocations", str(rm.get("total_allocations", 0)))

            formatter.console.print(table)

    # Services
    if status_data["services"]:
        table = Table(title="Engineering Services")
        table.add_column("Service", style="cyan")
        table.add_column("Started", style="green")
        table.add_column("Healthy", style="yellow")
        table.add_column("Error", style="red")

        for name, info in status_data["services"].items():
            started = "✓" if info["started"] else "✗"
            healthy = "✓" if info["healthy"] else "✗"
            error = info["last_error"] or ""
            table.add_row(name, started, healthy, error[:50] if error else "")

        formatter.console.print(table)


if __name__ == "__main__":
    app()