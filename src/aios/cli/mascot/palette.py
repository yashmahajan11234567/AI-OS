"""
AI-OS Cyber Turtle Color Palette - GREEN EDITION.

Dark green body with green accent palette ONLY.
No red, yellow, gold, orange, gray, white, purple, pink, blue, cyan, brown, or teal.
Minimal colors, crisp terminal aesthetic.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MascotPalette:
    """Color palette for AI-OS cyber turtle rendering."""

    # Primary turtle body colors (dark green family)
    body_dark: str = "#0D2818"       # Near-black / dark green
    body_mid: str = "#1A3D24"        # Medium dark green
    body_light: str = "#2E7D32"      # Lighter green for body detail

    # Accent colors (green palette ONLY)
    accent_bright: str = "#4CAF50"   # Bright green accent
    accent_highlight: str = "#81C784"  # Highlight green
    accent_pale: str = "#A5D6A7"     # Pale green
    accent_very_light: str = "#C8E6C9"  # Very light green (thought bubbles, etc.)

    # Eye colors (green only)
    eye_bright: str = "#A5D6A7"      # Pale green for active eyes
    eye_dim: str = "#2E7D32"         # Green for inactive eyes

    # Special states - ALL green only
    thought_indicator: str = "#C8E6C9"   # Very light green for planning thought
    motion_indicator: str = "#81C784"    # Highlight green for executing motion
    inspect_marker: str = "#4CAF50"      # Bright green for reviewing inspection
    magnifier: str = "#4CAF50"           # Bright green for verifying magnifier
    book_glow: str = "#81C784"           # Highlight green for learning glow
    escalation_mark: str = "#C8E6C9"     # Very light green for escalation ?
    scroll_accent: str = "#4CAF50"       # Bright green for completion scroll

    # Background/fallback
    background: str = "#0D2818"      # Same as body_dark
    monochrome_fg: str = "#CCCCCC"   # Light gray for monochrome mode
    monochrome_bg: str = "#000000"   # Black for monochrome mode

    @classmethod
    def from_rich_style(cls, style: str) -> "MascotPalette":
        """Create palette from Rich style string."""
        return cls()

    def get_color(self, name: str, fallback: str = "") -> str:
        """Get a color by name with fallback."""
        return getattr(self, name, fallback)

    def to_rich_style(self, fg: str, bg: Optional[str] = None, bold: bool = False) -> str:
        """Convert palette color to Rich style string."""
        style = ""
        if bold:
            style += "bold "
        style += fg
        if bg:
            style += f" on {bg}"
        return style


# Default palette instance
DEFAULT_PALETTE = MascotPalette()

# Monochrome fallback palette
MONOCHROME_PALETTE = MascotPalette(
    body_dark="#FFFFFF",
    body_mid="#CCCCCC",
    body_light="#999999",
    accent_bright="#FFFFFF",
    accent_highlight="#CCCCCC",
    accent_pale="#999999",
    accent_very_light="#FFFFFF",
    eye_bright="#FFFFFF",
    eye_dim="#999999",
    thought_indicator="#FFFFFF",
    motion_indicator="#FFFFFF",
    inspect_marker="#FFFFFF",
    magnifier="#FFFFFF",
    book_glow="#FFFFFF",
    escalation_mark="#FFFFFF",
    scroll_accent="#FFFFFF",
    background="#000000",
    monochrome_fg="#FFFFFF",
    monochrome_bg="#000000",
)