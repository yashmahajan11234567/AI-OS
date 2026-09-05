"""
AI-OS Cyber Turtle Mascot Module.

Presentation-only mascot for AI-OS startup screen and status display.
The mascot never mutates AI-OS state - it only renders based on authoritative state.
"""

from aios.cli.mascot.state import MascotState, MascotStateMapper, MascotStateContext
from aios.cli.mascot.renderer import MascotRenderer, RenderMode
from aios.cli.mascot.animator import MascotAnimator, SyncMascotAnimator
from aios.cli.mascot.sprites import MascotSprites, MascotSpriteState, MascotFrame, MascotAnimation
from aios.cli.mascot.assets import MascotAssets
from aios.cli.mascot.palette import MascotPalette, DEFAULT_PALETTE, MONOCHROME_PALETTE
from aios.cli.mascot.halfblock import HalfBlockRasterizer, RenderMode

__all__ = [
    # State
    "MascotState",
    "MascotStateMapper",
    "MascotStateContext",
    # Renderer
    "MascotRenderer",
    "RenderMode",
    # Animator
    "MascotAnimator",
    "SyncMascotAnimator",
    # Sprites
    "MascotSprites",
    "MascotSpriteState",
    "MascotFrame",
    "MascotAnimation",
    # Assets
    "MascotAssets",
    # Palette
    "MascotPalette",
    "DEFAULT_PALETTE",
    "MONOCHROME_PALETTE",
    # Half-block
    "HalfBlockRasterizer",
]