"""
Tests for Cyber Turtle Half-Block Rasterizer.
"""

import pytest
from aios.cli.mascot.halfblock import (
    RenderMode,
    HalfBlockRasterizer,
    PaletteColors,
    select_halfblock_char,
    get_color_for_pixel,
    render_fallback,
    render_json,
    render_state,
)
from aios.cli.mascot.assets import MascotAssets, _FrameData


class TestHalfBlockCharSelection:
    """Tests for half-block character selection logic."""

    def test_select_halfblock_char_all_cases(self):
        """Test all four combinations of upper/lower pixel presence."""
        # Neither
        assert select_halfblock_char(0, 0) == " "
        # Upper only
        assert select_halfblock_char(1, 0) == "▀"
        assert select_halfblock_char(2, 0) == "▀"
        # Lower only
        assert select_halfblock_char(0, 1) == "▄"
        assert select_halfblock_char(0, 2) == "▄"
        # Both
        assert select_halfblock_char(1, 1) == "█"
        assert select_halfblock_char(2, 2) == "█"
        assert select_halfblock_char(1, 2) == "█"
        assert select_halfblock_char(2, 1) == "█"


class TestGetColorForPixel:
    """Tests for pixel color mapping."""

    def test_transparent_returns_empty(self):
        """Transparent pixel returns empty strings."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(0, palette)
        assert fg == ""
        assert bg == ""

    def test_body_returns_body_colors(self):
        """Body pixel returns body fg/bg."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(1, palette)
        assert fg == palette.body_mid_fg
        assert bg == palette.body_mid_bg

    def test_accent_returns_accent_colors(self):
        """Accent pixel returns accent fg/bg."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(2, palette)
        assert fg == palette.accent_cyan_fg
        assert bg == palette.accent_cyan_bg

    def test_reserved_returns_empty(self):
        """Reserved pixel returns empty strings."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(3, palette)
        assert fg == ""
        assert bg == ""

    def test_monochrome_mode_returns_empty(self):
        """Monochrome palette returns empty color codes."""
        palette = PaletteColors.for_mode(RenderMode.MONOCHROME)
        fg, bg = get_color_for_pixel(1, palette)
        assert fg == ""
        assert bg == ""
        fg, bg = get_color_for_pixel(2, palette)
        assert fg == ""
        assert bg == ""


class TestHalfBlockRasterizer:
    """Tests for HalfBlockRasterizer."""

    def test_render_full_mode(self):
        """Full mode renders with ANSI colors."""
        frame = MascotAssets.get_frame("IDLE", 0)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        result = rasterizer.render_frame(frame)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain ANSI escape sequences
        assert "\x1b[" in result

    def test_render_monochrome_mode(self):
        """Monochrome mode renders without ANSI colors."""
        frame = MascotAssets.get_frame("IDLE", 0)
        rasterizer = HalfBlockRasterizer(RenderMode.MONOCHROME)
        result = rasterizer.render_frame(frame)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should NOT contain ANSI escape sequences
        assert "\x1b[" not in result
        # Should contain half-block chars
        assert "▀" in result or "▄" in result or "█" in result

    def test_render_fallback_mode(self):
        """Fallback mode renders ASCII."""
        frame = MascotAssets.get_frame("IDLE", 0)
        rasterizer = HalfBlockRasterizer(RenderMode.FALLBACK)
        result = rasterizer.render_frame(frame)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain ASCII fallback chars
        assert "@" in result or "^" in result or "v" in result or " " in result

    def test_render_narrow_mode(self):
        """Narrow mode renders cropped output."""
        frame = MascotAssets.get_frame("IDLE", 0)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        result = rasterizer.render_frame_narrow(frame, max_width=10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_set_mode_updates_palette(self):
        """set_mode should update palette for new mode."""
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        assert rasterizer.palette.body_fg != ""
        rasterizer.set_mode(RenderMode.MONOCHROME)
        assert rasterizer.palette.body_fg == ""


class TestRenderFallback:
    """Tests for fallback renderer."""

    def test_render_fallback_all_states(self):
        """All states should have fallback rendering."""
        for state in [
            "IDLE", "PLANNING", "EXECUTING", "REVIEWING",
            "VERIFYING", "LEARNING", "ESCALATING", "COMPLETE"
        ]:
            result = render_fallback(state)
            assert isinstance(result, str)
            assert len(result) > 0
            assert "[TURTLE]" in result

    def test_render_fallback_frame_index_wrapping(self):
        """Frame index should wrap around."""
        result0 = render_fallback("IDLE", 0)
        result1 = render_fallback("IDLE", 1)
        assert result0 == result1


class TestRenderJson:
    """Tests for JSON renderer."""

    def test_render_json_structure(self):
        """JSON output should have correct structure."""
        frame = MascotAssets.get_frame("IDLE", 0)
        result = render_json("IDLE", 0, frame)
        import json
        data = json.loads(result)
        assert data["state"] == "IDLE"
        assert data["frame"] == 0
        assert data["dimensions"] == {"width": 17, "height": 11}

    def test_render_json_without_frame_data(self):
        """JSON output without frame data should have null dimensions."""
        result = render_json("IDLE", 0, None)
        import json
        data = json.loads(result)
        assert data["dimensions"] is None


class TestRenderState:
    """Tests for convenience render_state function."""

    def test_render_state_full_mode(self):
        """render_state with FULL mode should produce colored output."""
        result = render_state("IDLE", 0, RenderMode.FULL)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "\x1b[" in result

    def test_render_state_monochrome_mode(self):
        """render_state with MONOCHROME mode should produce non-colored output."""
        result = render_state("IDLE", 0, RenderMode.MONOCHROME)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "\x1b[" not in result

    def test_render_state_fallback_mode(self):
        """render_state with FALLBACK mode should produce fallback text."""
        result = render_state("IDLE", 0, RenderMode.FALLBACK)
        assert isinstance(result, str)
        assert "[TURTLE]" in result

    def test_render_state_json_mode(self):
        """render_state with JSON mode should produce JSON."""
        result = render_state("IDLE", 0, RenderMode.JSON)
        import json
        data = json.loads(result)
        assert data["state"] == "IDLE"

    def test_render_state_narrow_mode(self):
        """render_state with NARROW mode should produce cropped output."""
        result = render_state("IDLE", 0, RenderMode.NARROW)
        assert isinstance(result, str)
        assert len(result) > 0


class TestPaletteColors:
    """Tests for PaletteColors."""

    def test_for_mode_full(self):
        """FULL mode should have all colors."""
        palette = PaletteColors.for_mode(RenderMode.FULL)
        assert palette.body_fg != ""
        assert palette.accent_cyan_fg != ""
        assert palette.reset == "\x1b[0m"

    def test_for_mode_monochrome(self):
        """MONOCHROME mode should have empty colors."""
        palette = PaletteColors.for_mode(RenderMode.MONOCHROME)
        assert palette.body_fg == ""
        assert palette.accent_cyan_fg == ""
        assert palette.reset == ""

    def test_for_mode_fallback(self):
        """FALLBACK mode should have empty colors."""
        palette = PaletteColors.for_mode(RenderMode.FALLBACK)
        assert palette.body_fg == ""
        assert palette.accent_cyan_fg == ""

    def test_for_mode_json(self):
        """JSON mode should have empty colors."""
        palette = PaletteColors.for_mode(RenderMode.JSON)
        assert palette.body_fg == ""
        assert palette.accent_cyan_fg == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])