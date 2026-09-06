"""
Tests for Owl Sprites - Pixel-Art Asset Edition.

Tests that the new asset-backed sprite system works correctly.
"""

import pytest
from aios.cli.owl.sprites import (
    OwlSprites,
    OwlSpriteState,
    OwlFrame,
    OwlAnimation,
)
from aios.cli.owl.halfblock import RenderMode


class TestOwlSprites:
    """Test owl sprite data integrity with pixel-art assets."""

    def test_all_states_have_animations(self):
        """All owl states should have animations defined."""
        for state in OwlSpriteState:
            anim = OwlSprites.get_animation(state)
            assert isinstance(anim, OwlAnimation)
            assert len(anim.frames) > 0, f"Missing animation frames for {state.value}"

    def test_animation_frame_consistency(self):
        """All frames in an animation should have same dimensions."""
        for state in OwlSpriteState:
            anim = OwlSprites.get_animation(state)
            first = anim.frames[0]
            for frame in anim.frames:
                assert frame.width == first.width, f"{state.value}: inconsistent width"
                assert frame.height == first.height, f"{state.value}: inconsistent height"

    def test_get_animation(self):
        """Getting animation returns correct type with frames."""
        for state in OwlSpriteState:
            anim = OwlSprites.get_animation(state)
            assert isinstance(anim, OwlAnimation)
            assert len(anim.frames) > 0

    def test_get_static_frame_full(self):
        """Getting static frame in FULL mode returns frame."""
        for state in OwlSpriteState:
            frame = OwlSprites.get_static_frame(state, narrow=False, monochrome=False)
            assert isinstance(frame, OwlFrame)
            assert frame.height > 0

    def test_get_static_frame_narrow(self):
        """Narrow frames are returned when requested."""
        for state in OwlSpriteState:
            frame = OwlSprites.get_static_frame(state, narrow=True, monochrome=False)
            assert isinstance(frame, OwlFrame)

    def test_get_static_frame_monochrome(self):
        """Monochrome frames are returned when requested."""
        for state in OwlSpriteState:
            frame = OwlSprites.get_static_frame(state, narrow=False, monochrome=True)
            assert isinstance(frame, OwlFrame)

    def test_idle_animation_not_looping(self):
        """IDLE animation should not loop (static)."""
        idle_anim = OwlSprites.get_animation(OwlSpriteState.IDLE)
        assert idle_anim.loop is False

    def test_complete_animation_not_looping(self):
        """COMPLETE animation should not loop (one-shot)."""
        complete_anim = OwlSprites.get_animation(OwlSpriteState.COMPLETE)
        assert complete_anim.loop is False

    def test_active_animations_looping(self):
        """Active state animations should loop."""
        for state in [
            OwlSpriteState.PLANNING,
            OwlSpriteState.EXECUTING,
            OwlSpriteState.REVIEWING,
            OwlSpriteState.VERIFYING,
            OwlSpriteState.LEARNING,
            OwlSpriteState.ESCALATING,
        ]:
            anim = OwlSprites.get_animation(state)
            assert anim.loop is True, f"{state.value} should loop"

    def test_frame_delay_reasonable(self):
        """Frame delays should be reasonable (not too fast) for looping animations."""
        for state in OwlSpriteState:
            anim = OwlSprites.get_animation(state)
            # Max 10 FPS = min 0.1s delay for looping animations
            if anim.loop:
                assert anim.frame_delay >= 0.1, f"{state.value}: frame_delay too short ({anim.frame_delay})"

    def test_validate_all_passes(self):
        """Validation should pass with no errors."""
        errors = OwlSprites.validate_all()
        assert errors == [], f"Sprite validation failed: {errors}"

    def test_owl_frame_validation(self):
        """OwlFrame should validate dimensions."""
        # Valid frame
        frame = OwlFrame(["abc", "def"], 3, 2)
        assert frame.width == 3
        assert frame.height == 2

        # Invalid width - line length doesn't match width
        # Note: Our OwlFrame doesn't validate line lengths vs width (only line count vs height)
        # This is because ANSI codes affect visual width
        # The validation is: len(lines) == height
        with pytest.raises(ValueError):
            OwlFrame(["abc"], 3, 2)  # 1 line but height=2

        # Invalid height - zero
        with pytest.raises(ValueError):
            OwlFrame([], 0, 0)

        # Invalid width - zero
        with pytest.raises(ValueError):
            OwlFrame(["a"], 0, 1)

    def test_owl_animation_validation(self):
        """OwlAnimation should validate frame consistency."""
        frame1 = OwlFrame(["abc", "def"], 3, 2)
        frame2 = OwlFrame(["ghi", "jkl"], 3, 2)

        # Valid
        anim = OwlAnimation([frame1, frame2])
        assert len(anim.frames) == 2

        # Invalid - mismatched dimensions
        frame3 = OwlFrame(["abcd"], 4, 1)
        with pytest.raises(ValueError):
            OwlAnimation([frame1, frame3])

        # Invalid - empty frames
        with pytest.raises(ValueError):
            OwlAnimation([])

    def test_frame_count_matches_assets(self):
        """Frame counts should match asset definitions."""
        from aios.cli.owl.assets import OwlAssets
        for state in OwlSpriteState:
            asset_count = OwlAssets.get_frame_count(state.value.upper())
            anim = OwlSprites.get_animation(state)
            assert len(anim.frames) == asset_count, f"{state.value}: frame count mismatch"

    def test_dimensions_match_assets(self):
        """Dimensions should match asset definitions."""
        from aios.cli.owl.assets import OwlAssets
        for state in OwlSpriteState:
            asset_w, asset_h = OwlAssets.get_dimensions(state.value.upper())
            frame = OwlSprites.get_static_frame(state)
            # Asset dimensions are in pixels; rendered frame uses char cells
            # Each char cell = 2 pixel rows (half-block)
            expected_char_h = (asset_h + 1) // 2
            assert frame.height == expected_char_h, f"{state.value}: height mismatch (got {frame.height}, expected {expected_char_h})"
            # Width should match asset width (1 char per pixel column in half-block)
            assert frame.width == asset_w, f"{state.value}: width mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])