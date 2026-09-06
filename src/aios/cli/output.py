"""
AI-OS CLI Output Module.

Shared helpers for JSON mode, human-readable output, terminal detection,
and fallback behavior. Does not create a competing logging framework.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, TextIO
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style


class OutputFormat(str, Enum):
    """Output format modes."""
    HUMAN = "human"
    JSON = "json"


class OutputMode(str, Enum):
    """CLI output mode detection."""
    INTERACTIVE = "interactive"  # TTY, human-readable
    PIPE = "pipe"                # Non-TTY, piped output
    JSON = "json"                # Explicit JSON requested
    CI = "ci"                    # CI environment


@dataclass
class OutputContext:
    """Context for output formatting decisions."""
    format: OutputFormat = OutputFormat.HUMAN
    mode: OutputMode = OutputMode.INTERACTIVE
    is_tty: bool = True
    is_json: bool = False
    no_color: bool = False
    force_color: bool = False
    term: str = ""
    console: Optional[Console] = None

    @classmethod
    def detect(cls, json_flag: bool = False, console: Optional[Console] = None) -> "OutputContext":
        """Detect output context from environment and flags."""
        is_tty = sys.stdout.isatty()
        no_color = os.environ.get("NO_COLOR") == "1"
        force_color = os.environ.get("FORCE_COLOR") == "1"
        term = os.environ.get("TERM", "").lower()
        ci = os.environ.get("CI") == "true"

        # Determine mode
        if json_flag:
            mode = OutputMode.JSON
            format = OutputFormat.JSON
        elif not is_tty:
            mode = OutputMode.PIPE
            format = OutputFormat.HUMAN
        elif ci:
            mode = OutputMode.CI
            format = OutputFormat.HUMAN
        else:
            mode = OutputMode.INTERACTIVE
            format = OutputFormat.HUMAN

        # Override for no-color
        if no_color and not force_color:
            format = OutputFormat.HUMAN  # Still human but no ANSI

        return cls(
            format=format,
            mode=mode,
            is_tty=is_tty,
            is_json=json_flag,
            no_color=no_color,
            force_color=force_color,
            term=term,
            console=console,
        )

    def should_use_color(self) -> bool:
        """Determine if color should be used."""
        if self.no_color and not self.force_color:
            return False
        if self.format == OutputFormat.JSON:
            return False
        if self.mode == OutputMode.PIPE and not self.force_color:
            return False
        if self.term == "dumb":
            return False
        return True

    def should_use_rich(self) -> bool:
        """Determine if Rich formatting should be used."""
        return (
            self.format == OutputFormat.HUMAN
            and self.should_use_color()
            and self.is_tty
        )


class OutputFormatter:
    """Formats output for both human and JSON consumption."""

    def __init__(self, context: OutputContext):
        self.context = context
        self._console = context.console or Console(
            force_terminal=context.should_use_color(),
            legacy_windows=False,
            color_system="auto" if context.should_use_color() else None,
        )

    @property
    def console(self) -> Console:
        return self._console

    def print(self, *args, **kwargs) -> None:
        """Print using Rich console."""
        self._console.print(*args, **kwargs)

    def print_json(self, data: Any) -> None:
        """Print data as JSON to stdout."""
        if self.context.format == OutputFormat.JSON:
            json.dump(data, sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
        else:
            # Pretty print for human
            self._console.print_json(data=data)

    def print_error(self, message: str, **fields) -> None:
        """Print error message."""
        if self.context.format == OutputFormat.JSON:
            self.print_json({"error": message, **fields})
        else:
            style = Style(color="red", bold=True) if self.context.should_use_color() else None
            self._console.print(f"Error: {message}", style=style)

    def print_warning(self, message: str, **fields) -> None:
        """Print warning message."""
        if self.context.format == OutputFormat.JSON:
            self.print_json({"warning": message, **fields})
        else:
            style = Style(color="yellow", bold=True) if self.context.should_use_color() else None
            self._console.print(f"Warning: {message}", style=style)

    def print_info(self, message: str, **fields) -> None:
        """Print info message."""
        if self.context.format == OutputFormat.JSON:
            self.print_json({"info": message, **fields})
        else:
            style = Style(color="cyan") if self.context.should_use_color() else None
            self._console.print(message, style=style)

    def print_success(self, message: str, **fields) -> None:
        """Print success message."""
        if self.context.format == OutputFormat.JSON:
            self.print_json({"success": message, **fields})
        else:
            style = Style(color="green", bold=True) if self.context.should_use_color() else None
            self._console.print(message, style=style)

    def print_table(
        self,
        columns: list[str],
        rows: list[list[str]],
        title: Optional[str] = None,
    ) -> None:
        """Print a formatted table."""
        if self.context.format == OutputFormat.JSON:
            data = [dict(zip(columns, row)) for row in rows]
            self.print_json({"table": data, "title": title})
            return

        table = Table(title=title, show_header=True, header_style="bold cyan")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        self._console.print(table)

    def print_panel(self, content: str, title: str, style: str = "cyan") -> None:
        """Print a panel."""
        if self.context.format == OutputFormat.JSON:
            self.print_json({"panel": {"title": title, "content": content}})
            return

        panel_style = style if self.context.should_use_color() else "white"
        self._console.print(Panel(content, title=title, style=panel_style))

    def print_key_value(self, key: str, value: Any, indent: int = 2) -> None:
        """Print key-value pair."""
        if self.context.format == OutputFormat.JSON:
            # Handled by caller via print_json
            pass
        else:
            prefix = " " * indent
            k_style = Style(color="cyan", bold=True) if self.context.should_use_color() else None
            v_style = Style(color="white") if self.context.should_use_color() else None
            self._console.print(f"{prefix}{key}:", style=k_style, end=" ")
            self._console.print(str(value), style=v_style)


def create_output_context(
    json_flag: bool = False,
    console: Optional[Console] = None,
) -> OutputContext:
    """Create output context from flags and environment."""
    return OutputContext.detect(json_flag, console)


def create_formatter(
    json_flag: bool = False,
    console: Optional[Console] = None,
) -> OutputFormatter:
    """Create output formatter from flags and environment."""
    return OutputFormatter(create_output_context(json_flag, console))


# Convenience for CLI commands
def get_json_flag(ctx: Any) -> bool:
    """Extract json flag from typer context or args."""
    # Check context params
    if hasattr(ctx, 'params') and ctx.params:
        return ctx.params.get('json', False) or ctx.params.get('json_output', False)
    return False