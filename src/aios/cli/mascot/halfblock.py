"""
AI-OS Cyber Turtle Half-Block Rasterizer.

Converts packed 2-bit raster data to ANSI terminal output using half-block
characters (▀, ▄, █, ░). Each terminal character represents two vertical pixels.

Semantic pixel codes:
    00 = transparent
    01 = body (dark green)
    10 = accent (green)
    11 = reserved (invalid)

Handles all 9 semantic combinations for upper/lower pixel pairs:
    transparent/transparent → space (no color)
    body/transparent → ▀ with body fg, default bg
    transparent/body → ▄ with default fg, body bg
    accent/transparent → ▀ with accent fg, default bg
    transparent/accent → ▄ with default fg, accent bg
    body/body → █ with body fg
    accent/accent → █ with accent fg
    body/accent → ▀ with body fg, accent bg
    accent/body → ▀ with accent fg, body bg
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

from aios.cli.mascot.assets import MascotAssets, _FrameData


class RenderMode(str, Enum):
    """Rendering mode based on terminal capabilities."""
    FULL = "full"              # Full color, animated, half-block
    NARROW = "narrow"          # Compact rendering for narrow terminals
    MONOCHROME = "monochrome"  # Single color, no ANSI
    JSON = "json"              # No rendering, JSON output only
    FALLBACK = "fallback"      # Basic text fallback


@dataclass(frozen=True)
class PaletteColors:
    """ANSI color codes for rendering."""
    # Dark green body colors
    body_fg: str = "\x1b[38;2;13;40;24m"       # #0D2818 - dark green
    body_bg: str = "\x1b[48;2;13;40;24m"

    body_mid_fg: str = "\x1b[38;2;26;61;36m"   # #1A3D24 - medium dark green
    body_mid_bg: str = "\x1b[48;2;26;61;36m"

    body_light_fg: str = "\x1b[38;2;46;125;50m"  # #2E7D32 - lighter green
    body_light_bg: str = "\x1b[48;2;46;125;50m"

    # Green accent colors (ONLY green)
    accent_bright_fg: str = "\x1b[38;2;76;175;80m"   # #4CAF50 - bright green
    accent_bright_bg: str = "\x1b[48;2;76;175;80m"

    accent_highlight_fg: str = "\x1b[38;2;129;199;132m"  # #81C784 - highlight green
    accent_highlight_bg: str = "\x1b[48;2;129;199;132m"

    accent_pale_fg: str = "\x1b[38;2;165;214;167m"   # #A5D6A7 - pale green
    accent_pale_bg: str = "\x1b[48;2;165;214;167m"

    accent_very_light_fg: str = "\x1b[38;2;200;230;201m"  # #C8E6C9 - very light green
    accent_very_light_bg: str = "\x1b[48;2;200;230;201m"

    # Reset
    reset: str = "\x1b[0m"

    # Monochrome
    mono_fg: str = "\x1b[38;2;204;204;204m"  # #CCCCCC
    mono_bg: str = "\x1b[48;2;0;0;0m"        # Black

    @classmethod
    def for_mode(cls, mode: RenderMode) -> "PaletteColors":
        """Get appropriate palette for render mode."""
        if mode in (RenderMode.MONOCHROME, RenderMode.FALLBACK, RenderMode.JSON):
            return PaletteColors(
                body_fg="", body_bg="",
                body_mid_fg="", body_mid_bg="",
                body_light_fg="", body_light_bg="",
                accent_bright_fg="", accent_bright_bg="",
                accent_highlight_fg="", accent_highlight_bg="",
                accent_pale_fg="", accent_pale_bg="",
                accent_very_light_fg="", accent_very_light_bg="",
                reset="",
                mono_fg="", mono_bg="",
            )
        return cls()


# =============================================================================
# HALF-BLOCK CHARACTER SELECTION
# =============================================================================

# Upper/lower pixel → character mapping
# Upper pixel determines if we use ▀ (upper only), ▄ (lower only), █ (both), or space (neither)
# Color is handled via ANSI fg/bg

HALF_BLOCK_UPPER = "▀"  # Upper pixel only
HALF_BLOCK_LOWER = "▄"  # Lower pixel only
HALF_BLOCK_FULL = "█"   # Both pixels
HALF_BLOCK_NONE = " "   # Neither pixel


def select_halfblock_char(upper: int, lower: int) -> str:
    """Select half-block character based on pixel presence."""
    has_upper = upper != 0
    has_lower = lower != 0

    if has_upper and has_lower:
        return HALF_BLOCK_FULL
    elif has_upper:
        return HALF_BLOCK_UPPER
    elif has_lower:
        return HALF_BLOCK_LOWER
    else:
        return HALF_BLOCK_NONE


def get_color_for_pixel(code: int, palette: PaletteColors, prefer_fg: bool = True) -> Tuple[str, str]:
    """
    Get ANSI fg/bg for a pixel code.

    Returns (fg_code, bg_code) - one may be empty if not applicable.
    """
    if code == 0:  # transparent
        return ("", "")
    elif code == 1:  # body
        # Use mid-tone body color for good visibility
        return (palette.body_mid_fg, palette.body_mid_bg)
    elif code == 2:  # accent
        return (palette.accent_bright_fg, palette.accent_bright_bg)
    else:
        return ("", "")  # reserved - should not happen


# =============================================================================
# RASTERIZER
# =============================================================================

class HalfBlockRasterizer:
    """
    Renders packed 2-bit raster frames to ANSI terminal output.

    Each terminal character cell represents 2 vertical pixels (upper/lower).
    Uses half-block Unicode characters with ANSI fg/bg for color.
    """

    def __init__(self, render_mode: RenderMode = RenderMode.FULL):
        self.render_mode = render_mode
        self.palette = PaletteColors.for_mode(render_mode)

    def set_mode(self, mode: RenderMode) -> None:
        """Update render mode and palette."""
        self.render_mode = mode
        self.palette = PaletteColors.for_mode(mode)

    def render_frame(self, frame: _FrameData) -> str:
        """
        Render a frame to ANSI string.

        Processes pixel pairs (upper/lower) for half-block rendering.
        """
        pixels = frame.unpack()
        width = frame.width
        height = frame.height

        # For half-block, we process pairs of rows
        # Each output row = 2 input rows
        output_rows = []
        for y in range(0, height, 2):
            upper_row = pixels[y] if y < height else [0] * width
            lower_row = pixels[y + 1] if y + 1 < height else [0] * width

            line_parts = []
            for x in range(width):
                upper_code = upper_row[x]
                lower_code = lower_row[x]

                char = select_halfblock_char(upper_code, lower_code)

                if char == HALF_BLOCK_NONE:
                    line_parts.append(" ")
                    continue

                # Determine colors for this character cell
                if char == HALF_BLOCK_FULL:
                    # Both pixels present - use upper for fg, lower for bg
                    upper_fg, upper_bg = get_color_for_pixel(upper_code, self.palette)
                    lower_fg, lower_bg = get_color_for_pixel(lower_code, self.palette)

                    if upper_code != 0 and lower_code != 0:
                        if upper_code == lower_code:
                            # Same semantic - solid block with that color
                            fg = upper_fg
                            bg = ""
                        else:
                            # Mixed - use upper as fg, lower as bg
                            fg = upper_fg
                            bg = lower_bg
                    elif upper_code != 0:
                        fg = upper_fg
                        bg = ""
                    else:
                        fg = lower_fg
                        bg = ""
                elif char == HALF_BLOCK_UPPER:
                    # Only upper pixel
                    fg, bg = get_color_for_pixel(upper_code, self.palette)
                else:  # HALF_BLOCK_LOWER
                    # Only lower pixel
                    fg, bg = get_color_for_pixel(lower_code, self.palette)

                # Build ANSI sequence
                if self.render_mode == RenderMode.MONOCHROME:
                    # Monochrome: no color, just character
                    line_parts.append(char)
                elif self.render_mode == RenderMode.FALLBACK:
                    # Fallback: use simple ASCII
                    if char == HALF_BLOCK_FULL:
                        line_parts.append("@")
                    elif char == HALF_BLOCK_UPPER:
                        line_parts.append("^")
                    elif char == HALF_BLOCK_LOWER:
                        line_parts.append("v")
                    else:
                        line_parts.append(" ")
                else:
                    # Full color mode
                    ansi = ""
                    if fg:
                        ansi += fg
                    if bg:
                        ansi += bg
                    if ansi:
                        line_parts.append(f"{ansi}{char}{self.palette.reset}")
                    else:
                        line_parts.append(char)

            output_rows.append("".join(line_parts))

        return "\n".join(output_rows)

    def render_frame_narrow(self, frame: _FrameData, max_width: int = 20) -> str:
        """Render frame with horizontal cropping for narrow terminals."""
        # For narrow mode, we can either crop or scale down
        # Simple approach: crop to max_width characters (which is 2*max_width pixels)
        pixels = frame.unpack()
        width = min(frame.width, max_width * 2)  # 2 pixels per char
        height = frame.height

        output_rows = []
        for y in range(0, height, 2):
            upper_row = pixels[y] if y < height else [0] * width
            lower_row = pixels[y + 1] if y + 1 < height else [0] * width

            line_parts = []
            for x in range(0, width, 2):  # Step by 2 to get char columns
                if x >= width:
                    break
                upper_code = upper_row[x] if x < len(upper_row) else 0
                lower_code = lower_row[x] if x < len(lower_row) else 0

                char = select_halfblock_char(upper_code, lower_code)

                if self.render_mode == RenderMode.MONOCHROME:
                    line_parts.append(char if char != HALF_BLOCK_NONE else " ")
                elif self.render_mode == RenderMode.FALLBACK:
                    if char == HALF_BLOCK_FULL:
                        line_parts.append("@")
                    elif char == HALF_BLOCK_UPPER:
                        line_parts.append("^")
                    elif char == HALF_BLOCK_LOWER:
                        line_parts.append("v")
                    else:
                        line_parts.append(" ")
                else:
                    if char == HALF_BLOCK_NONE:
                        line_parts.append(" ")
                        continue

                    # Same color logic as full render
                    if char == HALF_BLOCK_FULL:
                        upper_fg, upper_bg = get_color_for_pixel(upper_code, self.palette)
                        lower_fg, lower_bg = get_color_for_pixel(lower_code, self.palette)
                        if upper_code != 0 and lower_code != 0:
                            if upper_code == lower_code:
                                fg, bg = upper_fg, ""
                            else:
                                fg, bg = upper_fg, lower_bg
                        elif upper_code != 0:
                            fg, bg = upper_fg, ""
                        else:
                            fg, bg = lower_fg, ""
                    elif char == HALF_BLOCK_UPPER:
                        fg, bg = get_color_for_pixel(upper_code, self.palette)
                    else:
                        fg, bg = get_color_for_pixel(lower_code, self.palette)

                    ansi = ""
                    if fg:
                        ansi += fg
                    if bg:
                        ansi += bg
                    if ansi:
                        line_parts.append(f"{ansi}{char}{self.palette.reset}")
                    else:
                        line_parts.append(char)

            output_rows.append("".join(line_parts))

        return "\n".join(output_rows)


# =============================================================================
# FALLBACK RENDERER (for when half-block not supported)
# =============================================================================

# Minimal fallback frames - just state indicators
FALLBACK_FRAMES = {
    "IDLE": [
        "[TURTLE]  IDLE",
    ],
    "PLANNING": [
        "[TURTLE]  PLANNING...",
    ],
    "EXECUTING": [
        "[TURTLE]  EXECUTING...",
    ],
    "REVIEWING": [
        "[TURTLE]  REVIEWING...",
    ],
    "VERIFYING": [
        "[TURTLE]  VERIFYING...",
    ],
    "LEARNING": [
        "[TURTLE]  LEARNING...",
    ],
    "ESCALATING": [
        "[TURTLE]  ESCALATING!",
    ],
    "COMPLETE": [
        "[TURTLE]  COMPLETE",
    ],
}


def render_fallback(state: str, frame_index: int = 0) -> str:
    """Render text fallback for unsupported terminals."""
    frames = FALLBACK_FRAMES.get(state, FALLBACK_FRAMES["IDLE"])
    frame = frames[frame_index % len(frames)]
    return frame


# =============================================================================
# JSON OUTPUT (no rendering)
# =============================================================================

def render_json(state: str, frame_index: int = 0, frame_data: Optional[_FrameData] = None) -> str:
    """Render JSON status representation (no ANSI art)."""
    import json
    data = {
        "state": state,
        "frame": frame_index,
        "dimensions": None,
    }
    if frame_data:
        data["dimensions"] = {"width": frame_data.width, "height": frame_data.height}
    return json.dumps(data)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def render_state(state: str, frame_index: int = 0, mode: RenderMode = RenderMode.FULL) -> str:
    """Render a state at a specific frame index."""
    if mode == RenderMode.JSON:
        frame = MascotAssets.get_frame(state, frame_index)
        return render_json(state, frame_index, frame)

    if mode == RenderMode.FALLBACK:
        return render_fallback(state, frame_index)

    frame = MascotAssets.get_frame(state, frame_index)
    rasterizer = HalfBlockRasterizer(mode)

    if mode == RenderMode.NARROW:
        return rasterizer.render_frame_narrow(frame)
    else:
        return rasterizer.render_frame(frame)