"""
AI-OS CLI Main Entry Point.
"""

import sys
import typer
from rich import print

from aios.core.constants import APP_NAME
from aios.core.version import __version__

# Import and register commands
from aios.cli.commands.doctor import register_doctor_command
from aios.cli.commands.kernel import app as kernel_app
from aios.cli.commands.onboard import main as onboard_main

app = typer.Typer(
    name="aios",
    help="AI-OS - Your modular AI operating system.",
    no_args_is_help=True,
)

# Register commands
register_doctor_command(app)
app.add_typer(kernel_app, name="kernel")


@app.callback()
def main():
    """AI-OS root command."""
    pass


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


if __name__ == "__main__":
    app()