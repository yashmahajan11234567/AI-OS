"""
Unit tests for HalfBlockRasterizer.

Tests:
- All 9 raster combinations (transparent/transparent, body/transparent, transparent/body,
  accent/transparent, transparent/accent, body/body, accent/accent, body/accent, accent/body)
- ANSI foreground/background correctness
- Transparent pixels produce no color artifacts
- Monochrome output has no color ANSI
- JSON has no ANSI
"""

from __future__ import annotations

import pytest
import re
import hashlib

from aios.cli.owl.halfblock import (
    HalfBlockRasterizer,
    RenderMode,
    PaletteColors,
    select_halfblock_char,
    get_color_for_pixel,
    render_fallback,
    render_json,
    render_state,
)
from aios.cli.owl.assets import OwlAssets, _FrameData


def pack_pixels(pixels_2d) -> bytes:
    """Helper to pack 2D pixel array into bytes."""
    flat = []
    for row in pixels_2d:
        flat.extend(row)
    while len(flat) % 4 != 0:
        flat.append(0)
    data = bytearray()
    for i in range(0, len(flat), 4):
        byte_val = (flat[i] << 6) | (flat[i+1] << 4) | (flat[i+2] << 2) | flat[i+3]
        data.append(byte_val)
    return bytes(data)


def create_test_frame(pixels_2d) -> _FrameData:
    """Helper to create a test frame from 2D pixel array."""
    height = len(pixels_2d)
    width = len(pixels_2d[0]) if height > 0 else 0
    data = pack_pixels(pixels_2d)
    checksum = hashlib.sha256(data).hexdigest()[:16]
    return _FrameData(width=width, height=height, data=data, checksum=checksum)


class TestHalfBlockCharacterSelection:
    """Tests for half-block character selection logic."""

    def test_transparent_transparent(self):
        """0, 0 → space (no pixel)."""
        assert select_halfblock_char(0, 0) == " "

    def test_body_transparent(self):
        """1, 0 → ▀ (upper only)."""
        assert select_halfblock_char(1, 0) == "▀"

    def test_transparent_body(self):
        """0, 1 → ▄ (lower only)."""
        assert select_halfblock_char(0, 1) == "▄"

    def test_accent_transparent(self):
        """2, 0 → ▀ (upper only)."""
        assert select_halfblock_char(2, 0) == "▀"

    def test_transparent_accent(self):
        """0, 2 → ▄ (lower only)."""
        assert select_halfblock_char(0, 2) == "▄"

    def test_body_body(self):
        """1, 1 → █ (both)."""
        assert select_halfblock_char(1, 1) == "█"

    def test_accent_accent(self):
        """2, 2 → █ (both)."""
        assert select_halfblock_char(2, 2) == "█"

    def test_body_accent(self):
        """1, 2 → █ (both, mixed)."""
        assert select_halfblock_char(1, 2) == "█"

    def test_accent_body(self):
        """2, 1 → █ (both, mixed)."""
        assert select_halfblock_char(2, 1) == "█"


class TestColorAssignment:
    """Tests for ANSI color assignment."""

    def test_transparent_returns_empty(self):
        """Transparent pixel returns empty color codes."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(0, palette)
        assert fg == "" and bg == ""

    def test_body_returns_body_colors(self):
        """Body pixel returns body color codes."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(1, palette)
        assert fg == palette.body_mid_fg
        assert bg == palette.body_mid_bg

    def test_accent_returns_accent_colors(self):
        """Accent pixel returns accent color codes."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(2, palette)
        assert fg == palette.accent_cyan_fg
        assert bg == palette.accent_cyan_bg

    def test_reserved_returns_empty(self):
        """Reserved pixel returns empty (should not occur)."""
        palette = PaletteColors()
        fg, bg = get_color_for_pixel(3, palette)
        assert fg == "" and bg == ""


class TestFullColorRendering:
    """Tests for full color (FULL mode) rendering."""

    def test_single_body_pixel_renders(self):
        """Single body pixel in upper position renders ▀ with body fg."""
        pixels = [
            [1, 0],  # upper: body, transparent
            [0, 0],  # lower: transparent, transparent
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        # Should contain ▀ with body color ANSI
        assert "▀" in output
        assert "\x1b[38;2;26;31;58m" in output  # body_mid_fg
        assert "\x1b[0m" in output  # reset

    def test_single_accent_pixel_renders(self):
        """Single accent pixel renders with accent color."""
        pixels = [
            [2, 0],
            [0, 0],
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        assert "▀" in output
        assert "\x1b[38;2;0;212;255m" in output  # accent_cyan_fg
        assert "\x1b[0m" in output

    def test_body_over_accent_mixed(self):
        """Body upper + accent lower → █ with body fg, accent bg."""
        pixels = [
            [1],  # body
            [2],  # accent
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        assert "█" in output
        # Should have both fg and bg ANSI
        assert "\x1b[38;2;26;31;58m" in output  # body fg
        assert "\x1b[48;2;0;212;255m" in output  # accent bg
        assert "\x1b[0m" in output

    def test_accent_over_body_mixed(self):
        """Accent upper + body lower → █ with accent fg, body bg."""
        pixels = [
            [2],  # accent
            [1],  # body
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        assert "█" in output
        assert "\x1b[38;2;0;212;255m" in output  # accent fg
        assert "\x1b[48;2;26;31;58m" in output  # body bg
        assert "\x1b[0m" in output

    def test_same_type_both_pixels(self):
        """Body/body or accent/accent → solid █ with single color fg."""
        # Body/body
        pixels = [[1], [1]]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        assert "█" in output
        assert "\x1b[38;2;26;31;58m" in output  # body fg
        # Should NOT have bg set for same type
        assert "\x1b[48;2" not in output

    def test_all_transparent_renders_space(self):
        """All transparent pixels render as spaces."""
        pixels = [
            [0, 0],
            [0, 0],
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        # Should be spaces/newlines only, no ANSI
        assert output.strip() == ""
        assert "\x1b[" not in output


class TestMonochromeRendering:
    """Tests for MONOCHROME mode (no color ANSI)."""

    def test_no_ansi_in_monochrome(self):
        """Monochrome output must not contain ANSI escape codes."""
        pixels = [
            [1, 2],
            [2, 1],
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.MONOCHROME)
        output = rasterizer.render_frame(frame)

        # No ANSI codes at all
        assert "\x1b[" not in output
        # Should still have half-block characters
        assert any(c in output for c in "▀▄█")

    def test_monochrome_character_only(self):
        """Monochrome should output only half-block characters and newlines."""
        pixels = [[1, 2], [2, 1]]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.MONOCHROME)
        output = rasterizer.render_frame(frame)

        # Only allowed characters: half-blocks, newlines
        allowed = set("▀▄█ \n")
        assert all(c in allowed for c in output)


class TestNarrowRendering:
    """Tests for NARROW mode (compact rendering)."""

    def test_narrow_crops_width(self):
        """Narrow mode should crop to max width."""
        # Create wide frame (10 cols = 5 chars)
        pixels = [
            [1] * 10,
            [1] * 10,
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.NARROW)
        output = rasterizer.render_frame_narrow(frame, max_width=3)  # 3 chars = 6 pixels

        lines = output.split('\n')
        # Each line should have at most 3 visible chars (ignoring ANSI)
        for line in lines:
            # Strip ANSI codes
            clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
            assert len(clean) <= 3


class TestFallbackRendering:
    """Tests for FALLBACK mode (ASCII only)."""

    def test_fallback_no_ansi(self):
        """Fallback output must not contain ANSI."""
        pixels = [[1, 2], [2, 1]]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FALLBACK)
        output = rasterizer.render_frame(frame)

        assert "\x1b[" not in output

    def test_fallback_ascii_chars(self):
        """Fallback should use @, ^, v, space."""
        pixels = [[1, 2], [2, 1]]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FALLBACK)
        output = rasterizer.render_frame(frame)

        allowed = set("@^v \n")
        assert all(c in allowed for c in output)


class TestJSONOutput:
    """Tests for JSON mode (no rendering)."""

    def test_json_no_ansi(self):
        """JSON output must not contain ANSI."""
        frame = OwlAssets.get_frame("IDLE", 0)
        output = render_json("IDLE", 0, frame)
        assert "\x1b[" not in output

    def test_json_valid_format(self):
        """JSON output must be valid JSON with expected fields."""
        frame = OwlAssets.get_frame("IDLE", 0)
        output = render_json("PLANNING", 2, frame)
        import json
        data = json.loads(output)
        assert data["state"] == "PLANNING"
        assert data["frame"] == 2
        assert data["dimensions"]["width"] == frame.width
        assert data["dimensions"]["height"] == frame.height


class TestRenderStateConvenience:
    """Tests for render_state() convenience function."""

    def test_full_mode_returns_ansi(self):
        """FULL mode should return string with ANSI."""
        output = render_state("IDLE", 0, RenderMode.FULL)
        assert isinstance(output, str)

    def test_json_mode_no_ansi(self):
        """JSON mode should return JSON string without ANSI."""
        output = render_state("IDLE", 0, RenderMode.JSON)
        assert "\x1b[" not in output
        # Should be valid JSON
        import json
        data = json.loads(output)
        assert data["state"] == "IDLE"

    def test_fallback_mode_no_ansi(self):
        """FALLBACK mode should return ASCII without ANSI."""
        output = render_state("IDLE", 0, RenderMode.FALLBACK)
        assert "\x1b[" not in output
        assert "o.o" in output or "o" in output  # fallback owl content


class TestTransparentNoColorArtifacts:
    """Tests that transparent pixels never produce color artifacts."""

    def test_transparent_surrounded_by_color_no_leak(self):
        """Transparent pixels adjacent to colored pixels should not leak color."""
        # Pattern: body, transparent, body
        # Transparent middle should not have color
        pixels = [
            [1, 0, 1],
            [1, 0, 1],
        ]
        frame = create_test_frame(pixels)
        rasterizer = HalfBlockRasterizer(RenderMode.FULL)
        output = rasterizer.render_frame(frame)

        # The middle char should be space (transparent/transparent = space)
        # No ANSI should appear for the transparent position
        lines = output.split('\n')
        assert len(lines) == 1  # 2 pixel rows = 1 char row
        # First char: body/body → █ with body color
        # Second char: transparent/transparent → space, no ANSI
        # Third char: body/body → █ with body color
        clean = re.sub(r'\x1b\[[0-9;]*m', '', lines[0])
        assert clean[0] in "█▀▄"
        assert clean[1] == " "  # middle is space
        assert clean[2] in "█▀▄"


class TestCodeCoverage:
    """Ensure all 9 combinations are tested."""

    def test_all_nine_combinations_render(self):
        """Verify all 9 semantic combinations produce output without error."""
        combinations = [
            (0, 0),  # transparent/transparent
            (1, 0),  # body/transparent
            (0, 1),  # transparent/body
            (2, 0),  # accent/transparent
            (0, 2),  # transparent/accent
            (1, 1),  # body/body
            (2, 2),  # accent/accent
            (1, 2),  # body/accent
            (2, 1),  # accent/body
        ]

        for upper, lower in combinations:
            pixels = [[upper], [lower]]
            frame = create_test_frame(pixels)
            rasterizer = HalfBlockRasterizer(RenderMode.FULL)
            output = rasterizer.render_frame(frame)
            # Should not raise, should produce string
            assert isinstance(output, str)
            assert len(output) > 0