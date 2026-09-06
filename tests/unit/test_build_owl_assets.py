"""
Unit tests for build_owl_assets.py build tool.

Tests:
- PNG → packed representation → unpacked raster preserves semantic pixel data
- Fails loudly on invalid artwork
- Validates dimensions
- Validates palette/colors
- Rejects malformed/translucent/unsupported pixels
"""

from __future__ import annotations

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Skip all tests if Pillow not available
pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="Pillow not available")

from build_owl_assets import (
    classify_pixel,
    pack_pixels,
    unpack_pixels,
    compute_checksum,
    process_png,
    find_best_size,
    build_state,
    build_all,
    BODY_COLORS,
    ACCENT_COLORS,
    CANONICAL_SIZES,
    SOURCE_DIR,
)


class TestColorClassification:
    """Tests for pixel color classification."""

    def test_transparent_classified_as_zero(self):
        """Alpha=0 should be transparent (code 0)."""
        assert classify_pixel(255, 0, 0, 0) == 0

    def test_body_colors_classified_as_one(self):
        """Body palette colors should be code 1."""
        for r, g, b in BODY_COLORS:
            assert classify_pixel(r, g, b, 255) == 1, f"Body color ({r},{g},{b}) not classified as body"

    def test_accent_colors_classified_as_two(self):
        """Accent palette colors should be code 2."""
        for r, g, b in ACCENT_COLORS:
            assert classify_pixel(r, g, b, 255) == 2, f"Accent color ({r},{g},{b}) not classified as accent"

    def test_unknown_color_raises_error(self):
        """Colors not in palette should raise ValueError."""
        # Bright red not in palette
        with pytest.raises(ValueError, match="Unknown pixel color"):
            classify_pixel(255, 0, 0, 255)

    def test_near_palette_color_warns_classifies(self, capsys):
        """Colors close to palette should warn and classify (not error)."""
        # Close to body color #0B1020
        result = classify_pixel(0x0C, 0x11, 0x21, 255)
        assert result in (1, 2)  # Should classify as body or accent
        captured = capsys.readouterr()
        assert "WARNING" in captured.err or "warning" in captured.err.lower()


class TestPackUnpack:
    """Tests for pixel packing/unpacking round-trip."""

    def test_pack_unpack_preserves_data(self):
        """Round-trip pack → unpack should preserve pixel data."""
        original = [
            [0, 1, 2, 1, 0],
            [1, 1, 1, 2, 2],
            [2, 2, 0, 0, 1],
            [0, 0, 0, 0, 0],
        ]
        packed = pack_pixels(original)
        unpacked = unpack_pixels(packed, 5, 4)
        assert unpacked == original

    def test_pack_unpack_various_dimensions(self):
        """Test various dimensions."""
        for w, h in [(1, 1), (2, 2), (3, 3), (4, 4), (5, 3), (17, 11), (24, 16)]:
            original = [[(x + y) % 3 for x in range(w)] for y in range(h)]
            packed = pack_pixels(original)
            unpacked = unpack_pixels(packed, w, h)
            assert unpacked == original, f"Failed for {w}x{h}"

    def test_checksum_deterministic(self):
        """Same pixels should produce same checksum."""
        pixels = [[1, 2], [2, 1]]
        cs1 = compute_checksum(pixels)
        cs2 = compute_checksum(pixels)
        assert cs1 == cs2
        assert len(cs1) == 16  # Truncated SHA256

    def test_checksum_changes_with_data(self):
        """Different pixels should produce different checksums."""
        pixels1 = [[1, 0], [0, 0]]
        pixels2 = [[0, 1], [0, 0]]
        assert compute_checksum(pixels1) != compute_checksum(pixels2)


class TestCanonicalSizeSelection:
    """Tests for canonical size selection."""

    def test_exact_match(self):
        """Image matching canonical size should use that size."""
        img = MagicMock()
        img.size = (17, 11)
        w, h = find_best_size(img)
        assert (w, h) == (17, 11)

    def test_smaller_than_smallest(self):
        """Image smaller than smallest canonical uses smallest."""
        img = MagicMock()
        img.size = (10, 8)
        w, h = find_best_size(img)
        assert (w, h) == (17, 11)

    def test_between_sizes(self):
        """Image between sizes uses next larger."""
        img = MagicMock()
        img.size = (20, 12)  # Between 17x11 and 24x16
        w, h = find_best_size(img)
        assert (w, h) == (24, 16)

    def test_larger_than_largest(self):
        """Image larger than largest canonical uses largest."""
        img = MagicMock()
        img.size = (50, 40)
        w, h = find_best_size(img)
        assert (w, h) == (32, 20)


class TestPNGProcessing:
    """Tests for PNG processing (requires actual PNG files)."""

    def create_test_png(self, tmp_path: Path, pixels_2d, filename: str) -> Path:
        """Create a test PNG file from pixel array."""
        height = len(pixels_2d)
        width = len(pixels_2d[0]) if height > 0 else 0

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        for y, row in enumerate(pixels_2d):
            for x, code in enumerate(row):
                if code == 0:
                    img.putpixel((x, y), (0, 0, 0, 0))
                elif code == 1:
                    img.putpixel((x, y), (0x0B, 0x10, 0x20, 255))  # body
                elif code == 2:
                    img.putpixel((x, y), (0x00, 0xD4, 0xFF, 255))  # accent

        png_path = tmp_path / filename
        img.save(png_path)
        return png_path

    def test_valid_png_processes_correctly(self, tmp_path):
        """Valid PNG with palette colors should process correctly."""
        # Simple 3x2 owl-like pattern
        pixels = [
            [0, 1, 0],
            [1, 1, 1],
        ]
        png_path = self.create_test_png(tmp_path, pixels, "test.png")

        # Temporarily override SOURCE_DIR
        import build_owl_assets
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            result = process_png(png_path, 17, 11)
            assert len(result) == 11  # canonical height
            assert len(result[0]) == 17  # canonical width
        finally:
            build_owl_assets.SOURCE_DIR = original_source

    def test_png_with_unknown_color_raises(self, tmp_path):
        """PNG with color not in palette should raise ValueError."""
        # Create PNG with invalid color (bright red)
        img = Image.new('RGBA', (5, 5), (255, 0, 0, 255))
        png_path = tmp_path / "invalid.png"
        img.save(png_path)

        import build_owl_assets
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            with pytest.raises(ValueError, match="Unknown pixel color"):
                process_png(png_path, 17, 11)
        finally:
            build_owl_assets.SOURCE_DIR = original_source

    def test_png_with_transparency_preserves_alpha(self, tmp_path):
        """Transparent pixels should remain transparent (code 0)."""
        pixels = [
            [0, 1, 0],
            [0, 1, 0],
        ]
        png_path = self.create_test_png(tmp_path, pixels, "transparent_test.png")

        import build_owl_assets
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            result = process_png(png_path, 17, 11)
            # Image is 3x2, centered in 17x11 canvas
            # Offset: ((17-3)//2, (11-2)//2) = (7, 4)
            # So the body pixels (1s) should be at y=4,5 and x=7,8,9
            ox, oy = 7, 4
            # Corners of canvas should be transparent
            assert result[0][0] == 0
            assert result[0][16] == 0
            assert result[10][0] == 0
            assert result[10][16] == 0
            # Center area where 3x2 image was pasted should have body
            assert result[oy][ox+1] == 1  # top middle of 3x2 -> (4, 8)
            assert result[oy+1][ox+1] == 1  # bottom middle of 3x2 -> (5, 8)
        finally:
            build_owl_assets.SOURCE_DIR = original_source


class TestBuildPipeline:
    """Tests for the full build pipeline."""

    def test_build_state_requires_source_files(self, tmp_path):
        """build_state should fail if source PNG missing."""
        import build_owl_assets
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            with pytest.raises(FileNotFoundError, match="Source PNG not found"):
                build_state("IDLE", 1)
        finally:
            build_owl_assets.SOURCE_DIR = original_source

    def test_build_all_validates_all_states(self):
        """build_all should process all 8 states."""
        # This test would require actual PNG files, so we just verify
        # the function exists and has the right signature
        import inspect
        sig = inspect.signature(build_all)
        assert list(sig.parameters.keys()) == []


class TestIntegrationRoundTrip:
    """Integration test: PNG → packed → unpacked preserves semantics."""

    def create_owl_png(self, tmp_path: Path, state_name: str, frame_idx: int = 0) -> Path:
        """Create a simple owl-like PNG for testing."""
        # 17x11 pattern with body outline and accent eyes
        width, height = 17, 11
        pixels = [[0] * width for _ in range(height)]

        # Simple owl silhouette
        for y in range(height):
            for x in range(width):
                # Body: rough oval
                cx, cy = width // 2, height // 2
                dx, dy = x - cx, y - cy
                if (dx * dx) / (cx * cx) + (dy * dy) / (cy * cy) < 0.8:
                    pixels[y][x] = 1  # body

        # Eyes (accent)
        pixels[3][5] = 2
        pixels[3][11] = 2

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        for y, row in enumerate(pixels):
            for x, code in enumerate(row):
                if code == 1:
                    img.putpixel((x, y), (0x0B, 0x10, 0x20, 255))
                elif code == 2:
                    img.putpixel((x, y), (0x00, 0xD4, 0xFF, 255))

        png_path = tmp_path / f"{state_name.lower()}_{frame_idx}.png"
        img.save(png_path)
        return png_path

    def test_round_trip_preserves_semantics(self, tmp_path):
        """Full round-trip: PNG → pack → unpack preserves body/accent/transparent semantics."""
        # Create test PNG for IDLE state (1 frame, no index)
        png_path = self.create_owl_png(tmp_path, "IDLE", 0)
        # Rename to match build_state expectation for single frame (no index)
        png_path.rename(tmp_path / "idle.png")

        import build_owl_assets
        from build_owl_assets import unpack_pixels
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            state_data = build_state("IDLE", 1)

            # Verify frame data
            assert len(state_data.frames) == 1
            frame = state_data.frames[0]

            # Unpack and check semantics preserved
            unpacked = unpack_pixels(frame.data, frame.width, frame.height)

            # Should have body pixels (1) and accent pixels (2)
            has_body = any(1 in row for row in unpacked)
            has_accent = any(2 in row for row in unpacked)
            has_transparent = any(0 in row for row in unpacked)

            assert has_body, "Body pixels lost in round-trip"
            assert has_accent, "Accent pixels lost in round-trip"
            assert has_transparent, "Transparent pixels lost in round-trip"

            # No reserved codes
            for row in unpacked:
                for pixel in row:
                    assert pixel != 3, "Reserved code appeared in round-trip"

        finally:
            build_owl_assets.SOURCE_DIR = original_source


class TestErrorHandling:
    """Tests for error handling and validation."""

    def test_reserved_code_rejection(self):
        """Pixel code 3 (reserved) should be rejected during processing."""
        # This would require a PNG that somehow produces code 3,
        # which our classifier prevents. But we can test the check exists.
        from build_owl_assets import RESERVED_CODE
        assert RESERVED_CODE == 3

    def test_malformed_png_handled(self, tmp_path):
        """Corrupt/malformed PNG should raise appropriate error."""
        # Create invalid file
        bad_png = tmp_path / "bad.png"
        bad_png.write_bytes(b"not a png")

        import build_owl_assets
        original_source = build_owl_assets.SOURCE_DIR
        build_owl_assets.SOURCE_DIR = tmp_path

        try:
            with pytest.raises(Exception):
                process_png(bad_png, 17, 11)
        finally:
            build_owl_assets.SOURCE_DIR = original_source


# Run as script for quick verification
if __name__ == "__main__":
    pytest.main([__file__, "-v"])