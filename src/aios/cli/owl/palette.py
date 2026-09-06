"""
AI-OS Owl Color Palette.

Near-black/dark navy background with blue/cyan palette.
Minimal colors, crisp terminal aesthetic.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OwlPalette:
    """Color palette for AI-OS owl rendering."""

    # Primary owl body colors
    body_dark: str = "#0B1020"       # Near-black / dark navy
    body_mid: str = "#1A1F3A"        # Dark navy blue
    body_light: str = "#2A3F6E"      # Medium blue

    # Accent colors (blue/cyan palette)
    accent_cyan: str = "#00D4FF"     # Bright cyan
    accent_blue: str = "#0088FF"     # Electric blue
    accent_teal: str = "#00BFA6"     # Teal

    # Eye colors
    eye_dark: str = "#000000"        # Black for negative-space eyes
    eye_bright: str = "#00FFFF"      # Bright cyan for active eyes
    eye_dim: str = "#006688"         # Dim blue for inactive eyes

    # Special states
    thinking_cap: str = "#FFD700"    # Gold for planning cap
    hunter_red: str = "#FF3344"      # Red for executing focus
    magnifier_blue: str = "#00AAFF"  # Blue for verifying
    book_green: str = "#00CC66"      # Green for learning
    escalation_yellow: str = "#FFAA00"  # Yellow for escalation
    scroll_white: str = "#E0E0E0"    # Light gray for completion scroll

    # Background/fallback
    background: str = "#0B1020"      # Same as body_dark
    monochrome_fg: str = "#CCCCCC"   # Light gray for monochrome mode
    monochrome_bg: str = "#000000"   # Black for monochrome mode

    @classmethod
    def from_rich_style(cls, style: str) -> "OwlPalette":
        """Create palette from Rich style string."""
        # For now, return default. Could parse hex colors from style.
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
DEFAULT_PALETTE = OwlPalette()

# Monochrome fallback palette
MONOCHROME_PALETTE = OwlPalette(
    body_dark="#FFFFFF",
    body_mid="#CCCCCC",
    body_light="#999999",
    accent_cyan="#FFFFFF",
    accent_blue="#CCCCCC",
    accent_teal="#999999",
    eye_dark="#000000",
    eye_bright="#FFFFFF",
    eye_dim="#999999",
    thinking_cap="#FFFFFF",
    hunter_red="#FFFFFF",
    magnifier_blue="#FFFFFF",
    book_green="#FFFFFF",
    escalation_yellow="#FFFFFF",
    scroll_white="#FFFFFF",
    background="#000000",
    monochrome_fg="#FFFFFF",
    monochrome_bg="#000000",
)