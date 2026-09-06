"""
AI-OS CLI Owl Visual Identity Package.

Provides pixel-art owl animations for AI-OS terminal experience.
The owl is a presentation/control surface only - it never mutates AI-OS state.
"""

from aios.cli.owl.state import OwlState, OwlStateMapper
from aios.cli.owl.renderer import OwlRenderer
from aios.cli.owl.animator import OwlAnimator
from aios.cli.owl.sprites import OwlSprites
from aios.cli.owl.palette import OwlPalette

__all__ = [
    "OwlState",
    "OwlStateMapper",
    "OwlRenderer",
    "OwlAnimator",
    "OwlSprites",
    "OwlPalette",
]