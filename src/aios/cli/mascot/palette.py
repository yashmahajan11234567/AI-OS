"""
AI-OS Cyber Turtle Color Palette.

Dark navy / near-black body with blue/cyan accent palette ONLY.
No red, green, yellow, gold, orange, gray, white, purple, pink, or brown.
Minimal colors, crisp terminal aesthetic.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MascotPalette:
    """Color palette for AI-OS cyber turtle rendering."""

    # Primary turtle body colors (dark navy family)
    body_dark: str = "#0B1020"       # Near-black / dark navy
    body_mid: str = "#1A1F3A"        # Dark navy blue
    body_light: str = "#2A3F6E"      # Medium blue

    # Accent colors (blue/cyan palette ONLY)
    accent_cyan: str = "#00D4FF"     # Bright cyan
    accent_blue: str = "#0088FF"     # Electric blue
    accent_deep: str = "#0066AA"     # Deep blue
    accent_bright: str = "#00EEFF"   # Brighter cyan

    # Eye colors (blue/cyan only)
    eye_bright: str = "#00FFFF"      # Bright cyan for active eyes
    eye_dim: str = "#006688"         # Dim blue for inactive eyes

    # Special states - ALL blue/cyan only
    thought_indicator: str = "#00EEFF"   # Bright cyan for planning thought
    motion_indicator: str = "#00AAFF"    # Blue for executing motion
    inspect_marker: str = "#00D4FF"      # Cyan for reviewing inspection
    magnifier: str = "#00D4FF"           # Cyan for verifying magnifier
    book_glow: str = "#00AAFF"           # Blue for learning glow
    escalation_mark: str = "#00EEFF"     # Bright cyan for escalation ?
    scroll_accent: str = "#00D4FF"       # Cyan for completion scroll

    # Background/fallback
    background: str = "#0B1020"      # Same as body_dark
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
    accent_cyan="#FFFFFF",
    accent_blue="#CCCCCC",
    accent_deep="#999999",
    accent_bright="#FFFFFF",
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