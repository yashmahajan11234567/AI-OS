"""
AI-OS Owl Sprite Definitions - Pixel-Art Asset Edition.

This module provides the public sprite interface using packed pixel-art assets
loaded from the generated runtime asset module. No hand-authored Unicode strings.

The owl is a presentation/control surface only - it never mutates AI-OS state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

from aios.cli.owl.assets import OwlAssets, _FrameData
from aios.cli.owl.halfblock import RenderMode, render_state, HalfBlockRasterizer


class OwlSpriteState(str, Enum):
    """Logical owl states that map to sprite frames."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    VERIFYING = "verifying"
    LEARNING = "learning"
    ESCALATING = "escalating"
    COMPLETE = "complete"


@dataclass(frozen=True)
class OwlFrame:
    """Single owl animation frame - rendered string output."""
    lines: List[str]
    width: int
    height: int

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Frame dimensions must be positive")
        if len(self.lines) != self.height:
            raise ValueError("Line count must match height")
        for line in self.lines:
            # Width in characters may vary due to ANSI codes
            pass


@dataclass(frozen=True)
class OwlAnimation:
    """Animation sequence for an owl state."""
    frames: List[OwlFrame]
    loop: bool = True
    frame_delay: float = 0.15  # ~6-7 FPS, max 10 FPS per spec

    def __post_init__(self):
        if not self.frames:
            raise ValueError("Animation must have at least one frame")
        # Validate all frames have same dimensions
        first = self.frames[0]
        for frame in self.frames:
            if frame.width != first.width or frame.height != first.height:
                raise ValueError("All frames must have same dimensions")


class OwlSprites:
    """Centralized sprite data for all owl states - backed by pixel-art assets."""

    # Cache for rendered frames per mode
    _RENDERED_CACHE: Dict[tuple, OwlFrame] = {}

    @classmethod
    def _render_asset_frame(cls, state: str, frame_index: int, mode: RenderMode) -> OwlFrame:
        """Render an asset frame to OwlFrame for the given mode."""
        cache_key = (state, frame_index, mode)
        if cache_key in cls._RENDERED_CACHE:
            return cls._RENDERED_CACHE[cache_key]

        asset_frame = OwlAssets.get_frame(state, frame_index)
        # Use asset dimensions (each char cell = 2 pixel rows)
        asset_width, asset_height = OwlAssets.get_dimensions(state)
        char_width = asset_width  # half-block: 1 char per column
        char_height = (asset_height + 1) // 2  # 2 pixel rows per char row

        rendered_str = render_state(state, frame_index, mode)
        lines = rendered_str.split('\n')

        # Ensure we have the expected number of lines
        if len(lines) != char_height:
            # Pad or trim to match expected height
            if len(lines) < char_height:
                lines.extend([''] * (char_height - len(lines)))
            else:
                lines = lines[:char_height]

        frame = OwlFrame(
            lines=lines,
            width=char_width,
            height=char_height,
        )
        cls._RENDERED_CACHE[cache_key] = frame
        return frame

    @classmethod
    def get_animation(cls, state: OwlSpriteState) -> OwlAnimation:
        """Get animation for a state."""
        asset_state = state.value.upper()
        frame_count = OwlAssets.get_frame_count(asset_state)
        frames = [
            cls._render_asset_frame(asset_state, i, RenderMode.FULL)
            for i in range(frame_count)
        ]

        # Determine loop behavior per state
        loop = asset_state not in ("IDLE", "COMPLETE")
        delay = 0.15
        if asset_state == "EXECUTING":
            delay = 0.12
        elif asset_state == "ESCALATING":
            delay = 0.20
        elif asset_state == "COMPLETE":
            delay = 1.0

        return OwlAnimation(frames=frames, loop=loop, frame_delay=delay)

    @classmethod
    def get_static_frame(
        cls,
        state: OwlSpriteState,
        narrow: bool = False,
        monochrome: bool = False,
    ) -> OwlFrame:
        """Get static frame for a state with fallback priority."""
        asset_state = state.value.upper()

        if monochrome:
            mode = RenderMode.MONOCHROME
        elif narrow:
            mode = RenderMode.NARROW
        else:
            mode = RenderMode.FULL

        # For non-looping animations, return first frame
        animation = cls.get_animation(state)
        if not animation.loop:
            return cls._render_asset_frame(asset_state, 0, mode)

        # For looping, return first frame as static representation
        return cls._render_asset_frame(asset_state, 0, mode)

    @classmethod
    def get_dimensions(cls, state: OwlSpriteState, narrow: bool = False, monochrome: bool = False) -> tuple[int, int]:
        """Get dimensions for a state."""
        asset_state = state.value.upper()
        asset_w, asset_h = OwlAssets.get_dimensions(asset_state)
        char_w = asset_w
        char_h = (asset_h + 1) // 2
        return (char_w, char_h)

    @classmethod
    def validate_all(cls) -> List[str]:
        """Validate all sprite data. Returns list of errors (empty if valid)."""
        errors = []

        # Check all states have animations
        for state in OwlSpriteState:
            try:
                anim = cls.get_animation(state)
                if not anim.frames:
                    errors.append(f"Missing animation frames for state: {state.value}")
            except Exception as e:
                errors.append(f"Error getting animation for {state.value}: {e}")

        # Verify assets
        if not OwlAssets.verify_all():
            errors.append("Asset checksum verification failed")

        return errors


# Validate on import
_SPRITE_ERRORS = OwlSprites.validate_all()
if _SPRITE_ERRORS:
    raise RuntimeError(f"Owl sprite validation failed: {_SPRITE_ERRORS}")