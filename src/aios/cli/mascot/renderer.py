"""
AI-OS Cyber Turtle Renderer.

Handles terminal capability detection, frame rendering, and fallback modes.
Never mutates AI-OS state.
"""

from __future__ import annotations

import os
import sys
import shutil
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum

from rich.console import Console, ConsoleOptions, RenderResult
from rich.style import Style
from rich.text import Text
from rich.segment import Segment

from aios.cli.mascot.sprites import MascotSprites, MascotSpriteState, MascotFrame
from aios.cli.mascot.palette import MascotPalette, DEFAULT_PALETTE, MONOCHROME_PALETTE
from aios.cli.mascot.state import MascotState
from aios.cli.mascot.halfblock import RenderMode, HalfBlockRasterizer, render_fallback, render_json
from aios.cli.output import create_formatter
from aios.core.constants import APP_NAME


@dataclass(frozen=True)
class TerminalCapabilities:
    """Detected terminal capabilities."""
    is_tty: bool
    width: int
    height: int
    supports_color: bool
    supports_unicode: bool
    rich_console: Console
    render_mode: RenderMode


class MascotRenderer:
    """
    Renders mascot frames to terminal with capability detection and fallbacks.

    Responsibilities:
    - TTY detection
    - Rich terminal capability detection
    - Color detection
    - Terminal width detection
    - Static frame rendering
    - Animation frame rendering
    - Fallback mode
    - Narrow mode
    - No-color mode

    Never mutates AI-OS state.
    """

    # Minimum width for full mascot rendering
    MIN_FULL_WIDTH = 40
    MIN_NARROW_WIDTH = 20

    def __init__(
        self,
        console: Optional[Console] = None,
        force_mode: Optional[RenderMode] = None,
        palette: Optional[MascotPalette] = None,
    ):
        self._console = console or Console(
            force_terminal=True,
            legacy_windows=False,
            color_system="auto",
        )
        self._force_mode = force_mode
        self._palette = palette or DEFAULT_PALETTE
        self._caps: Optional[TerminalCapabilities] = None
        self._rasterizer = HalfBlockRasterizer()
        self._detect_capabilities()

    def _detect_capabilities(self) -> None:
        """Detect terminal capabilities and determine render mode."""
        # Check TTY
        is_tty = sys.stdout.isatty()

        # Check terminal size
        try:
            size = shutil.get_terminal_size(fallback=(80, 24))
            width = size.columns
            height = size.lines
        except Exception:
            width = 80
            height = 24

        # Check color support
        supports_color = self._check_color_support()

        # Check unicode support
        supports_unicode = self._check_unicode_support()

        # Determine render mode
        render_mode = self._determine_render_mode(
            is_tty, width, supports_color, supports_unicode
        )

        self._caps = TerminalCapabilities(
            is_tty=is_tty,
            width=width,
            height=height,
            supports_color=supports_color,
            supports_unicode=supports_unicode,
            rich_console=self._console,
            render_mode=render_mode,
        )

        # Update rasterizer
        self._rasterizer.set_mode(render_mode)

    def _check_color_support(self) -> bool:
        """Check if terminal supports color."""
        # FORCE_COLOR=1 overrides NO_COLOR and other disables
        if os.environ.get("FORCE_COLOR") == "1":
            return True

        # Explicit disable via env vars
        if os.environ.get("NO_COLOR") == "1":
            return False
        if os.environ.get("FORCE_COLOR") == "0":
            return False

        # Check TERM
        term = os.environ.get("TERM", "").lower()
        if term == "dumb":
            return False

        # CI environments often don't support color well
        if os.environ.get("CI") == "true":
            return False

        # Rich console color system detection
        return self._console.color_system is not None

    def _check_unicode_support(self) -> bool:
        """Check if terminal supports Unicode block characters."""
        # Conservative: assume modern terminals support it
        term = os.environ.get("TERM", "").lower()
        if term == "dumb":
            return False
        return True

    def _determine_render_mode(
        self,
        is_tty: bool,
        width: int,
        supports_color: bool,
        supports_unicode: bool,
    ) -> RenderMode:
        """Determine render mode from capabilities."""
        # Force mode takes precedence
        if self._force_mode:
            return self._force_mode

        # JSON output mode
        if os.environ.get("AIOS_JSON_OUTPUT") == "1":
            return RenderMode.JSON

        # CI environments force fallback mode
        if os.environ.get("CI") == "true":
            return RenderMode.FALLBACK

        # Non-TTY or no unicode -> fallback
        if not is_tty or not supports_unicode:
            return RenderMode.FALLBACK

        # No color -> monochrome
        if not supports_color:
            return RenderMode.MONOCHROME

        # Narrow terminal
        if width < self.MIN_FULL_WIDTH:
            return RenderMode.NARROW

        # Full capability
        return RenderMode.FULL

    @property
    def capabilities(self) -> TerminalCapabilities:
        """Get detected terminal capabilities."""
        return self._caps

    @property
    def console(self) -> Console:
        """Get Rich console instance."""
        return self._console

    @property
    def render_mode(self) -> RenderMode:
        """Get current render mode."""
        return self._caps.render_mode if self._caps else RenderMode.FALLBACK

    def get_palette(self) -> MascotPalette:
        """Get appropriate palette for current mode."""
        if self.render_mode == RenderMode.MONOCHROME:
            return MONOCHROME_PALETTE
        return self._palette

    def render_static(
        self,
        state: MascotState,
        override_mode: Optional[RenderMode] = None,
    ) -> str:
        """
        Render a static mascot frame for the given state.

        Returns plain text (with ANSI if color enabled) suitable for printing.
        """
        mode = override_mode or self.render_mode

        if mode == RenderMode.JSON:
            return ""

        # Map MascotState to MascotSpriteState
        sprite_state = MascotSpriteState(state.value)

        if mode == RenderMode.NARROW:
            frame = MascotSprites.get_static_frame(sprite_state, narrow=True, monochrome=False)
            return "\n".join(frame.lines)
        elif mode == RenderMode.MONOCHROME:
            frame = MascotSprites.get_static_frame(sprite_state, narrow=False, monochrome=True)
            return "\n".join(frame.lines)
        elif mode == RenderMode.FALLBACK:
            return render_fallback(state.value)
        else:
            frame = MascotSprites.get_static_frame(sprite_state, narrow=False, monochrome=False)
            return "\n".join(frame.lines)

    def render_animation_frame(
        self,
        state: MascotState,
        frame_index: int,
        override_mode: Optional[RenderMode] = None,
    ) -> str:
        """
        Render a specific animation frame for the given state.

        Returns plain text (with ANSI if color enabled).
        """
        mode = override_mode or self.render_mode

        if mode in (RenderMode.JSON, RenderMode.FALLBACK, RenderMode.MONOCHROME, RenderMode.NARROW):
            # These modes don't animate - return static
            return self.render_static(state, override_mode)

        # Full mode - render animation frame
        sprite_state = MascotSpriteState(state.value)
        animation = MascotSprites.get_animation(sprite_state)
        if frame_index >= len(animation.frames):
            frame_index = 0
        frame = animation.frames[frame_index]

        return "\n".join(frame.lines)

    def render_startup_screen(
        self,
        version: str,
        status: str,
        health: str,
        mode: str,
        autonomy: str,
    ) -> str:
        """Render the AI-OS startup screen with mascot and status info."""
        mode_type = self.render_mode

        if mode_type == RenderMode.JSON:
            return ""

        if mode_type == RenderMode.FALLBACK:
            return self._render_startup_fallback(version, status, health, mode, autonomy)

        # Build startup screen using half-block rasterizer
        # Get IDLE mascot frame
        mascot_text = self.render_static(MascotState.IDLE)

        # Build status lines
        lines = mascot_text.split('\n')

        # Add status panel to the right of mascot
        status_lines = [
            f"  {APP_NAME} v{version}",
            f"  Status: {status}",
            f"  Health: {health}",
            f"  Mode: {mode}",
            f"  Autonomy: {autonomy}",
        ]

        # Combine mascot with status
        max_mascot_lines = len(lines)
        result_lines = []
        for i in range(max(max_mascot_lines, len(status_lines))):
            mascot_line = lines[i] if i < max_mascot_lines else ""
            status_line = status_lines[i] if i < len(status_lines) else ""
            result_lines.append(f"{mascot_line}{status_line}")

        return '\n'.join(result_lines)

    def _render_startup_fallback(
        self,
        version: str,
        status: str,
        health: str,
        mode: str,
        autonomy: str,
    ) -> str:
        """Text fallback for startup screen."""
        lines = [
            "",
            f"{APP_NAME} - AUTONOMOUS OPERATING SYSTEM",
            f"v{version}  Status: {status}  Health: {health}  Mode: {mode}  Autonomy: {autonomy}",
            "",
            "Commands:",
            "  aios status       System status",
            "  aios health       Health check",
            "  aios ready        Readiness check",
            "  aios diagnostics  Diagnostics",
            "  aios kernel       Kernel management",
            "  aios onboard      Integration onboarding",
            "  aios doctor       Configuration check",
            "  aios version      Show version",
            "",
        ]
        return "\n".join(lines)

    def clear_line(self) -> str:
        """Get ANSI sequence to clear current line."""
        return "\r\x1b[2K"

    def move_cursor_up(self, lines: int) -> str:
        """Get ANSI sequence to move cursor up N lines."""
        return f"\x1b[{lines}A"

    def hide_cursor(self) -> str:
        """Get ANSI sequence to hide cursor."""
        return "\x1b[?25l"

    def show_cursor(self) -> str:
        """Get ANSI sequence to show cursor."""
        return "\x1b[?25h"