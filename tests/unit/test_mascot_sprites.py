"""
Tests for Cyber Turtle Sprites - Pixel-Art Asset Edition.

Tests that the new asset-backed sprite system works correctly.
"""

import pytest
from aios.cli.mascot.sprites import (
    MascotSprites,
    MascotSpriteState,
    MascotFrame,
    MascotAnimation,
)
from aios.cli.mascot.halfblock import RenderMode


class TestMascotSprites:
    """Test mascot sprite data integrity with pixel-art assets."""

    def test_all_states_have_animations(self):
        """All mascot states should have animations defined."""
        for state in MascotSpriteState:
            anim = MascotSprites.get_animation(state)
            assert isinstance(anim, MascotAnimation)
            assert len(anim.frames) > 0, f"Missing animation frames for {state.value}"

    def test_animation_frame_consistency(self):
        """All frames in an animation should have same dimensions."""
        for state in MascotSpriteState:
            anim = MascotSprites.get_animation(state)
            first = anim.frames[0]
            for frame in anim.frames:
                assert frame.width == first.width, f"{state.value}: inconsistent width"
                assert frame.height == first.height, f"{state.value}: inconsistent height"

    def test_get_animation(self):
        """Getting animation returns correct type with frames."""
        for state in MascotSpriteState:
            anim = MascotSprites.get_animation(state)
            assert isinstance(anim, MascotAnimation)
            assert len(anim.frames) > 0

    def test_get_static_frame_full(self):
        """Getting static frame in FULL mode returns frame."""
        for state in MascotSpriteState:
            frame = MascotSprites.get_static_frame(state, narrow=False, monochrome=False)
            assert isinstance(frame, MascotFrame)
            assert frame.height > 0

    def test_get_static_frame_narrow(self):
        """Narrow frames are returned when requested."""
        for state in MascotSpriteState:
            frame = MascotSprites.get_static_frame(state, narrow=True, monochrome=False)
            assert isinstance(frame, MascotFrame)

    def test_get_static_frame_monochrome(self):
        """Monochrome frames are returned when requested."""
        for state in MascotSpriteState:
            frame = MascotSprites.get_static_frame(state, narrow=False, monochrome=True)
            assert isinstance(frame, MascotFrame)

    def test_idle_animation_not_looping(self):
        """IDLE animation should not loop (static)."""
        idle_anim = MascotSprites.get_animation(MascotSpriteState.IDLE)
        assert idle_anim.loop is False

    def test_complete_animation_not_looping(self):
        """COMPLETE animation should not loop (one-shot)."""
        complete_anim = MascotSprites.get_animation(MascotSpriteState.COMPLETE)
        assert complete_anim.loop is False

    def test_active_animations_looping(self):
        """Active state animations should loop."""
        for state in [
            MascotSpriteState.PLANNING,
            MascotSpriteState.EXECUTING,
            MascotSpriteState.REVIEWING,
            MascotSpriteState.VERIFYING,
            MascotSpriteState.LEARNING,
            MascotSpriteState.ESCALATING,
        ]:
            anim = MascotSprites.get_animation(state)
            assert anim.loop is True, f"{state.value} should loop"

    def test_frame_delay_reasonable(self):
        """Frame delays should be reasonable (not too fast) for looping animations."""
        for state in MascotSpriteState:
            anim = MascotSprites.get_animation(state)
            # Max 10 FPS = min 0.1s delay for looping animations
            if anim.loop:
                assert anim.frame_delay >= 0.1, f"{state.value}: frame_delay too short ({anim.frame_delay})"

    def test_validate_all_passes(self):
        """Validation should pass with no errors."""
        errors = MascotSprites.validate_all()
        assert errors == [], f"Sprite validation failed: {errors}"

    def test_mascot_frame_validation(self):
        """MascotFrame should validate dimensions."""
        # Valid frame
        frame = MascotFrame(["abc", "def"], 3, 2)
        assert frame.width == 3
        assert frame.height == 2

        # Invalid width - line length doesn't match width
        # Note: Our MascotFrame doesn't validate line lengths vs width (only line count vs height)
        # This is because ANSI codes affect visual width
        # The validation is: len(lines) == height
        with pytest.raises(ValueError):
            MascotFrame(["abc"], 3, 2)  # 1 line but height=2

        # Invalid height - zero
        with pytest.raises(ValueError):
            MascotFrame([], 0, 0)

        # Invalid width - zero
        with pytest.raises(ValueError):
            MascotFrame(["a"], 0, 1)

    def test_mascot_animation_validation(self):
        """MascotAnimation should validate frame consistency."""
        frame1 = MascotFrame(["abc", "def"], 3, 2)
        frame2 = MascotFrame(["ghi", "jkl"], 3, 2)

        # Valid
        anim = MascotAnimation([frame1, frame2])
        assert len(anim.frames) == 2

        # Invalid - mismatched dimensions
        frame3 = MascotFrame(["abcd"], 4, 1)
        with pytest.raises(ValueError):
            MascotAnimation([frame1, frame3])

        # Invalid - empty frames
        with pytest.raises(ValueError):
            MascotAnimation([])

    def test_frame_count_matches_assets(self):
        """Frame counts should match asset definitions."""
        from aios.cli.mascot.assets import MascotAssets
        for state in MascotSpriteState:
            asset_count = MascotAssets.get_frame_count(state.value.upper())
            anim = MascotSprites.get_animation(state)
            assert len(anim.frames) == asset_count, f"{state.value}: frame count mismatch"

    def test_dimensions_match_assets(self):
        """Dimensions should match asset definitions."""
        from aios.cli.mascot.assets import MascotAssets
        for state in MascotSpriteState:
            asset_w, asset_h = MascotAssets.get_dimensions(state.value.upper())
            frame = MascotSprites.get_static_frame(state)
            # Asset dimensions are in pixels; rendered frame uses char cells
            # Each char cell = 2 pixel rows (half-block)
            expected_char_h = (asset_h + 1) // 2
            assert frame.height == expected_char_h, f"{state.value}: height mismatch (got {frame.height}, expected {expected_char_h})"
            # Width should match asset width (1 char per pixel column in half-block)
            assert frame.width == asset_w, f"{state.value}: width mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])