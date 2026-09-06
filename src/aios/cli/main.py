"""
AI-OS CLI Main Entry Point.
"""

import sys
import os
import typer
from typing import Optional

from rich import print
from rich.console import Console

from aios.core.constants import APP_NAME
from aios.core.version import __version__
from aios.core.kernel_management import get_kernel, is_running
from aios.core.lifecycle_manager import get_lifecycle_manager
from aios.core.health_manager import get_health_manager

# Import and register commands
from aios.cli.commands.doctor import register_doctor_command
from aios.cli.commands.kernel import app as kernel_app
from aios.cli.commands.onboard import main as onboard_main
from aios.cli.commands.status import app as status_app
from aios.cli.commands.health import app as health_app
from aios.cli.commands.ready import app as ready_app
from aios.cli.commands.diagnostics import app as diagnostics_app

# Mascot integration
from aios.cli.mascot.renderer import MascotRenderer, RenderMode
from aios.cli.mascot.animator import SyncMascotAnimator
from aios.cli.output import create_formatter

app = typer.Typer(
    name="aios",
    help="AI-OS - Your modular AI operating system.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)

# Register commands
register_doctor_command(app)
app.add_typer(kernel_app, name="kernel")
app.add_typer(status_app, name="status")
app.add_typer(health_app, name="health")
app.add_typer(ready_app, name="ready")
app.add_typer(diagnostics_app, name="diagnostics")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """AI-OS root command."""
    # Handle --version flag
    if version:
        print(f"[bold cyan]{APP_NAME}[/bold cyan] v{__version__}")
        raise typer.Exit(0)

    # If no subcommand and no args, show startup screen
    if ctx.invoked_subcommand is None and not ctx.args:
        show_startup_screen()
        raise typer.Exit(0)


@app.command()
def version():
    """Show AI-OS version."""
    print(f"[bold cyan]{APP_NAME}[/bold cyan] v{__version__}")


@app.command()
def onboard(ctx: typer.Context):
    """User resource onboarding for external integrations."""
    # Delegate to the legacy argparse-based implementation
    # This is a bridge until full typer migration
    if not ctx.invoked_subcommand:
        print("[yellow]Use 'aios onboard --help' for onboarding commands[/yellow]")
        return

    # Get the subcommand and args
    subcommand = ctx.invoked_subcommand
    sub_args = sys.argv[2:]  # Skip 'aios' and 'onboard'

    sys.exit(onboard_main(sub_args))


def show_startup_screen() -> None:
    """Show AI-OS startup screen with cyber turtle mascot and status."""
    # Create renderer and animator
    renderer = MascotRenderer()
    animator = SyncMascotAnimator(renderer)
    formatter = create_formatter()

    # Gather status info - handle case where kernel isn't initialized
    health_text = "UNKNOWN"
    try:
        kernel = get_kernel()
        if is_running():
            status_text = "RUNNING"
        else:
            status_text = "STOPPED"

        health_mgr = get_health_manager()
        if health_mgr:
            health_text = health_mgr.overall_status.value
        elif kernel:
            health_text = kernel.health_state.value
    except RuntimeError:
        # Kernel not initialized
        status_text = "STOPPED"
        health_text = "UNINITIALIZED"

    # Mode
    if status_text == "RUNNING":
        mode_text = "OPERATIONAL"
    else:
        mode_text = "IDLE"

    # Autonomy (from config or default)
    autonomy_text = "OFF"  # Default - autonomy is opt-in

    # Render startup screen
    startup_output = animator.render_startup(
        version=__version__,
        status=status_text,
        health=health_text,
        mode=mode_text,
        autonomy=autonomy_text,
    )

    # In JSON mode, don't print anything (startup is visual only)
    if renderer.render_mode != RenderMode.JSON:
        # Print without Rich markup processing since we already have ANSI
        console = Console(force_terminal=True, legacy_windows=False)
        from rich.text import Text
        console.print(Text.from_ansi(startup_output))


if __name__ == "__main__":
    app()