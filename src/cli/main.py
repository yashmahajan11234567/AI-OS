import typer
from rich import print

from src.core.constants import APP_NAME
from src.core.version import __version__

app = typer.Typer(
    name="aios",
    help="AI-OS - Your modular AI operating system.",
)


@app.callback()
def main():
    """AI-OS root command."""
    pass


@app.command()
def version():
    """Show AI-OS version."""
    print(f"[bold cyan]{APP_NAME}[/bold cyan] v{__version__}")


if __name__ == "__main__":
    app()