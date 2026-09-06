"""
Tests for Owl Renderer - Pixel-Art Asset Edition.

Tests that the renderer works correctly with the new half-block rasterizer
and asset system.
"""

import os
import pytest
from unittest.mock import patch

from aios.cli.owl.renderer import (
    OwlRenderer,
    RenderMode,
    TerminalCapabilities,
)
from aios.cli.owl.state import OwlState
from aios.cli.owl.palette import OwlPalette, DEFAULT_PALETTE, MONOCHROME_PALETTE
from aios.core.constants import APP_NAME


class TestOwlRenderer:
    """Test owl renderer capabilities and rendering."""

    def test_renderer_creation(self):
        """Renderer can be created."""
        renderer = OwlRenderer()
        assert renderer is not None
        assert renderer.capabilities is not None
        assert hasattr(renderer, '_rasterizer')

    def test_capabilities_detection(self):
        """Capabilities are detected properly."""
        renderer = OwlRenderer()
        caps = renderer.capabilities

        assert isinstance(caps.is_tty, bool)
        assert isinstance(caps.width, int)
        assert isinstance(caps.height, int)
        assert isinstance(caps.supports_color, bool)
        assert isinstance(caps.supports_unicode, bool)
        assert caps.width > 0
        assert caps.height > 0

    def test_render_mode_detection_tty_color(self):
        """Full mode detected for TTY with color."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color", "CI": ""}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.FULL

    def test_render_mode_detection_narrow(self):
        """Narrow mode for narrow terminals."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(30, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer(force_mode=RenderMode.NARROW)
                    assert renderer.render_mode == RenderMode.NARROW

    def test_render_mode_detection_no_color(self):
        """Monochrome mode when NO_COLOR=1."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"NO_COLOR": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.MONOCHROME

    def test_render_mode_detection_force_color(self):
        """Force color overrides NO_COLOR."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.FULL

    def test_render_mode_detection_dumb_term(self):
        """Fallback for TERM=dumb."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "dumb"}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.FALLBACK

    def test_render_mode_detection_non_tty(self):
        """Fallback for non-TTY (piped output)."""
        with patch('sys.stdout.isatty', return_value=False):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                renderer = OwlRenderer()
                assert renderer.render_mode == RenderMode.FALLBACK

    def test_render_mode_detection_ci(self):
        """CI mode uses static fallback."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"CI": "true", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.FALLBACK

    def test_render_mode_json_env(self):
        """JSON mode when AIOS_JSON_OUTPUT=1."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"AIOS_JSON_OUTPUT": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    assert renderer.render_mode == RenderMode.JSON

    def test_force_mode_override(self):
        """Force mode overrides detection."""
        renderer = OwlRenderer(force_mode=RenderMode.MONOCHROME)
        assert renderer.render_mode == RenderMode.MONOCHROME

    def test_get_palette_full(self):
        """Full mode returns default palette."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    palette = renderer.get_palette()
                    assert palette == DEFAULT_PALETTE

    def test_get_palette_monochrome(self):
        """Monochrome mode returns monochrome palette."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"NO_COLOR": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    palette = renderer.get_palette()
                    assert palette == MONOCHROME_PALETTE

    def test_render_static_full_mode(self):
        """Static rendering in full mode returns output."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.IDLE)
                    assert isinstance(output, str)

    def test_render_static_narrow_mode(self):
        """Static rendering in narrow mode returns output."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(30, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.IDLE)
                    assert isinstance(output, str)

    def test_render_static_monochrome_mode(self):
        """Static rendering in monochrome mode returns no ANSI color."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"NO_COLOR": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.IDLE)
                    # Should not have RGB ANSI escape sequences for color
                    assert "38;2" not in output and "48;2" not in output

    def test_render_static_fallback_mode(self):
        """Static rendering in fallback mode returns ASCII."""
        with patch('sys.stdout.isatty', return_value=False):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                renderer = OwlRenderer()
                output = renderer.render_static(OwlState.IDLE)
                assert isinstance(output, str)
                # Fallback should be ASCII text
                assert "\x1b[" not in output

    def test_render_static_json_mode(self):
        """JSON mode returns empty string for static render."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"AIOS_JSON_OUTPUT": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.IDLE)
                    assert output == ""

    def test_render_animation_frame_full_mode(self):
        """Animation frame rendering in full mode."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_animation_frame(OwlState.PLANNING, 0)
                    assert isinstance(output, str)

    def test_render_animation_frame_non_animated_modes(self):
        """Animation frame falls back to static in non-animated modes."""
        for mode in [RenderMode.NARROW, RenderMode.MONOCHROME, RenderMode.FALLBACK, RenderMode.JSON]:
            with patch('sys.stdout.isatty', return_value=True):
                with patch('shutil.get_terminal_size', return_value=(80, 24)):
                    with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                        renderer = OwlRenderer(force_mode=mode)
                        static = renderer.render_static(OwlState.PLANNING)
                        anim = renderer.render_animation_frame(OwlState.PLANNING, 0)
                        assert anim == static

    def test_render_startup_screen(self):
        """Startup screen renders with all sections."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_startup_screen(
                        version="1.0.0",
                        status="RUNNING",
                        health="HEALTHY",
                        mode="OPERATIONAL",
                        autonomy="OFF",
                    )
                    assert APP_NAME in output
                    assert "v1.0.0" in output
                    assert "RUNNING" in output
                    assert "HEALTHY" in output
                    assert "OPERATIONAL" in output
                    assert "OFF" in output

    def test_render_startup_screen_json_mode(self):
        """Startup screen returns empty in JSON mode."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"AIOS_JSON_OUTPUT": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_startup_screen(
                        version="1.0.0",
                        status="RUNNING",
                        health="HEALTHY",
                        mode="OPERATIONAL",
                        autonomy="OFF",
                    )
                    assert output == ""

    def test_render_startup_screen_fallback_mode(self):
        """Startup screen in fallback mode returns ASCII."""
        with patch('sys.stdout.isatty', return_value=False):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                renderer = OwlRenderer()
                output = renderer.render_startup_screen(
                    version="1.0.0",
                    status="RUNNING",
                    health="HEALTHY",
                    mode="OPERATIONAL",
                    autonomy="OFF",
                )
                assert isinstance(output, str)
                assert APP_NAME in output
                assert "\x1b[" not in output

    def test_clear_line(self):
        """Clear line returns ANSI sequence."""
        renderer = OwlRenderer()
        assert renderer.clear_line() == "\r\x1b[2K"

    def test_move_cursor_up(self):
        """Move cursor up returns ANSI sequence."""
        renderer = OwlRenderer()
        assert renderer.move_cursor_up(3) == "\x1b[3A"

    def test_hide_show_cursor(self):
        """Cursor hide/show sequences."""
        renderer = OwlRenderer()
        assert renderer.hide_cursor() == "\x1b[?25l"
        assert renderer.show_cursor() == "\x1b[?25h"

    def test_monochrome_no_color_ansi(self):
        """Monochrome mode must not emit color ANSI codes."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"NO_COLOR": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.PLANNING)
                    # No RGB color codes
                    assert "38;2" not in output
                    assert "48;2" not in output

    def test_json_no_ansi(self):
        """JSON mode must not emit any ANSI."""
        with patch('sys.stdout.isatty', return_value=True):
            with patch('shutil.get_terminal_size', return_value=(80, 24)):
                with patch.dict(os.environ, {"AIOS_JSON_OUTPUT": "1", "TERM": "xterm-256color"}, clear=False):
                    renderer = OwlRenderer()
                    output = renderer.render_static(OwlState.EXECUTING)
                    assert output == ""
                    output = renderer.render_animation_frame(OwlState.EXECUTING, 0)
                    assert output == ""
                    output = renderer.render_startup_screen("1.0", "OK", "OK", "OK", "OK")
                    assert output == ""

    def test_fallback_no_ansi(self):
        """Fallback mode must not emit ANSI."""
        with patch('sys.stdout.isatty', return_value=False):
            renderer = OwlRenderer()
            output = renderer.render_static(OwlState.LEARNING)
            assert "\x1b[" not in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])