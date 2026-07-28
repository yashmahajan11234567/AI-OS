import typer
from rich import print

from aios.config.loader import load_config
from aios.config.validator import validate_config_file
from pathlib import Path

def register_doctor_command(app: typer.Typer):
    @app.command()
    def doctor():
        """Run doctor command to check configuration."""
        config_path = Path("config/app.yaml")
        try:
            config = load_config(config_path)
            validated_config = validate_config_file(config_path)
            print("[green]Configuration is valid![/green]")
            print("\n[bold]Configuration:[/bold]")
            print(f"  Name: {validated_config.name}")
            print(f"  Version: {validated_config.version}")
            print(f"  Environment: {validated_config.environment}")
            print(f"  Workspace: {validated_config.workspace.path}")
            print(f"  Logs: {validated_config.logs.path}")
            print(f"  Config directory: {validated_config.config}")
        except Exception as e:
            print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)
