"""
AI-OS CLI Main Entry Point.
"""

import typer
from rich import print

from aios.core.constants import APP_NAME
from aios.core.version import __version__

# Import and register commands
from aios.cli.commands.doctor import register_doctor_command
from aios.cli.commands.kernel import app as kernel_app

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
def kernel():
    """Start the Hermes Kernel (interactive mode)."""
    print("[yellow]Use 'aios kernel start' to start the kernel[/yellow]")


if __name__ == "__main__":
    app()