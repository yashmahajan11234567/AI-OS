"""
AI-OS CLI Diagnostics Command.

Exposes existing diagnostic information only - no new observability.
"""

import typer
import json
from typing import Optional

from aios.cli.output import create_formatter
from aios.core.kernel_management import get_kernel, is_running
from aios.core.lifecycle_manager import get_lifecycle_manager
from aios.core.health_manager import get_health_manager
from aios.events.core.bus import get_core_event_bus

app = typer.Typer(name="diagnostics", help="Show diagnostic information")


@app.callback(invoke_without_command=True)
def diagnostics(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    kernel: bool = typer.Option(True, "--kernel/--no-kernel", help="Include kernel stats"),
    lifecycle: bool = typer.Option(True, "--lifecycle/--no-lifecycle", help="Include lifecycle state"),
    health: bool = typer.Option(True, "--health/--no-health", help="Include health status"),
    eventbus: bool = typer.Option(False, "--eventbus/--no-eventbus", help="Include EventBus diagnostics"),
    services: bool = typer.Option(True, "--services/--no-services", help="Include service status"),
):
    """
    Expose existing diagnostic information only:
    - Kernel stats
    - Service status
    - Health
    - Lifecycle
    - EventBus diagnostics (if already accessible)

    Does NOT implement T6 observability.
    """
    formatter = create_formatter(json_output)
    context = formatter.context

    diag_data = {}

    # Kernel stats
    if kernel:
        try:
            k = get_kernel()
            if k and is_running():
                try:
                    diag_data["kernel_stats"] = k.get_stats()
                    diag_data["kernel_health"] = k.health_state.value
                    diag_data["kernel_alive"] = k.is_alive
                    diag_data["kernel_ready"] = k.is_ready
                except Exception as e:
                    diag_data["kernel_stats_error"] = str(e)
            else:
                diag_data["kernel"] = "not running"
        except RuntimeError:
            diag_data["kernel"] = "not initialized"

    # Lifecycle
    if lifecycle:
        try:
            lm = get_lifecycle_manager()
            if lm:
                diag_data["lifecycle"] = {
                    "state": lm.state.value,
                    "is_operational": lm.is_operational,
                    "is_terminated": lm.is_terminated,
                    "initialized_managers": lm.initialized_managers,
                    "phase_plan": lm.phase_plan,
                }
            else:
                diag_data["lifecycle"] = "not initialized"
        except RuntimeError:
            diag_data["lifecycle"] = "not initialized"

    # Health
    if health:
        try:
            hm = get_health_manager()
            if hm:
                diag_data["health"] = hm.get_all_health()
            else:
                diag_data["health"] = "not initialized"
        except RuntimeError:
            diag_data["health"] = "not initialized"

    # EventBus
    if eventbus:
        eb = get_core_event_bus()
        if eb:
            try:
                diag_data["eventbus"] = {
                    "running": eb.is_running if hasattr(eb, 'is_running') else True,
                    "history_size": len(eb._history) if hasattr(eb, '_history') else 0,
                    "subscriptions": len(eb._subscriptions) if hasattr(eb, '_subscriptions') else 0,
                }
            except Exception as e:
                diag_data["eventbus_error"] = str(e)
        else:
            diag_data["eventbus"] = "not initialized"

    # Services
    if services:
        k = get_kernel()
        if k and hasattr(k, '_services'):
            svcs = {}
            for name, svc in k._services.items():
                svcs[name] = {
                    "started": svc.started,
                    "healthy": svc.healthy,
                    "started_at": svc.started_at.isoformat() if svc.started_at else None,
                    "last_error": svc.last_error,
                }
            diag_data["services"] = svcs
        else:
            diag_data["services"] = {}

    if context.format.value == "json":
        formatter.print_json(diag_data)
    else:
        # Human-readable summary
        formatter.print_panel(
            "AI-OS Diagnostics",
            title="Diagnostics",
            style="cyan",
        )

        if "kernel_stats" in diag_data:
            ks = diag_data["kernel_stats"]
            formatter.print_info(f"Kernel: {diag_data.get('kernel_health', 'unknown')} (alive={diag_data.get('kernel_alive')}, ready={diag_data.get('kernel_ready')})")

        if "lifecycle" in diag_data:
            lc = diag_data["lifecycle"]
            if isinstance(lc, dict):
                formatter.print_info(f"Lifecycle: {lc['state']} (operational={lc['is_operational']})")
                if lc.get("initialized_managers"):
                    formatter.print_info(f"  Managers: {', '.join(lc['initialized_managers'])}")
            else:
                formatter.print_info(f"Lifecycle: {lc}")

        if "health" in diag_data:
            hl = diag_data["health"]
            if isinstance(hl, dict):
                formatter.print_info(f"Health: {hl.get('overall', 'unknown')} (checks={hl.get('total_checks', 0)})")
            else:
                formatter.print_info(f"Health: {hl}")

        if "eventbus" in diag_data:
            eb = diag_data["eventbus"]
            if isinstance(eb, dict):
                formatter.print_info(f"EventBus: running={eb.get('running')}, subscriptions={eb.get('subscriptions')}")
            else:
                formatter.print_info(f"EventBus: {eb}")

        if "services" in diag_data:
            svcs = diag_data["services"]
            if svcs:
                for name, info in svcs.items():
                    status = "✓" if info.get("started") else "✗"
                    healthy = "✓" if info.get("healthy") else "✗"
                    formatter.print_info(f"  {name}: started={status} healthy={healthy}")


if __name__ == "__main__":
    app()