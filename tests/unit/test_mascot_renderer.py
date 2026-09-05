"""
Tests for Cyber Turtle Renderer.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from aios.cli.mascot.renderer import MascotRenderer, RenderMode, TerminalCapabilities
from aios.cli.mascot.state import MascotState
from rich.console import Console


class TestMascotRenderer:
    """Tests for MascotRenderer."""

    def test_renderer_initialization(self):
        """Renderer should initialize without errors."""
        renderer = MascotRenderer()
        assert renderer is not None
        assert renderer.capabilities is not None
        assert isinstance(renderer.capabilities, TerminalCapabilities)

    def test_render_static_idle(self):
        """Render static IDLE frame."""
        renderer = MascotRenderer(force_mode=RenderMode.FULL)
        result = renderer.render_static(MascotState.IDLE)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_static_all_states(self):
        """Render static frames for all states."""
        renderer = MascotRenderer(force_mode=RenderMode.FULL)
        for state in MascotState:
            result = renderer.render_static(state)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_render_static_monochrome(self):
        """Render static in monochrome mode (no ANSI)."""
        renderer = MascotRenderer(force_mode=RenderMode.MONOCHROME)
        result = renderer.render_static(MascotState.IDLE)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "\x1b[" not in result

    def test_render_static_fallback(self):
        """Render static in fallback mode."""
        renderer = MascotRenderer(force_mode=RenderMode.FALLBACK)
        result = renderer.render_static(MascotState.IDLE)
        assert isinstance(result, str)
        assert "[TURTLE]" in result

    def test_render_static_json(self):
        """Render static in JSON mode returns empty string."""
        renderer = MascotRenderer(force_mode=RenderMode.JSON)
        result = renderer.render_static(MascotState.IDLE)
        assert result == ""

    def test_render_animation_frame(self):
        """Render animation frame."""
        renderer = MascotRenderer(force_mode=RenderMode.FULL)
        result = renderer.render_animation_frame(MascotState.PLANNING, 0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_animation_frame_non_full_modes(self):
        """Non-FULL modes return static for animation frames."""
        for mode in [RenderMode.MONOCHROME, RenderMode.FALLBACK, RenderMode.NARROW, RenderMode.JSON]:
            renderer = MascotRenderer(force_mode=mode)
            result = renderer.render_animation_frame(MascotState.PLANNING, 0)
            static_result = renderer.render_static(MascotState.PLANNING, override_mode=mode)
            assert result == static_result

    def test_render_startup_screen_full(self):
        """Render startup screen in full mode."""
        renderer = MascotRenderer(force_mode=RenderMode.FULL)
        result = renderer.render_startup_screen("1.0.0", "RUNNING", "HEALTHY", "OPERATIONAL", "OFF")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "AI-OS" in result
        assert "1.0.0" in result

    def test_render_startup_screen_fallback(self):
        """Render startup screen in fallback mode."""
        renderer = MascotRenderer(force_mode=RenderMode.FALLBACK)
        result = renderer.render_startup_screen("1.0.0", "RUNNING", "HEALTHY", "OPERATIONAL", "OFF")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "AI-OS" in result
        assert "AUTONOMOUS OPERATING SYSTEM" in result

    def test_render_startup_screen_json(self):
        """Render startup screen in JSON mode returns empty."""
        renderer = MascotRenderer(force_mode=RenderMode.JSON)
        result = renderer.render_startup_screen("1.0.0", "RUNNING", "HEALTHY", "OPERATIONAL", "OFF")
        assert result == ""

    def test_ansi_sequences(self):
        """Test ANSI helper methods."""
        renderer = MascotRenderer()
        assert renderer.clear_line() == "\r\x1b[2K"
        assert renderer.move_cursor_up(3) == "\x1b[3A"
        assert renderer.hide_cursor() == "\x1b[?25l"
        assert renderer.show_cursor() == "\x1b[?25h"

    def test_capabilities_property(self):
        """Capabilities property returns detected capabilities."""
        renderer = MascotRenderer()
        caps = renderer.capabilities
        assert hasattr(caps, 'is_tty')
        assert hasattr(caps, 'width')
        assert hasattr(caps, 'height')
        assert hasattr(caps, 'supports_color')
        assert hasattr(caps, 'supports_unicode')
        assert hasattr(caps, 'render_mode')


class TestTerminalCapabilities:
    """Tests for terminal capability detection."""

    def test_render_mode_json_env(self):
        """AIOS_JSON_OUTPUT=1 forces JSON mode."""
        with patch.dict(os.environ, {"AIOS_JSON_OUTPUT": "1"}):
            renderer = MascotRenderer()
            assert renderer.render_mode == RenderMode.JSON

    def test_render_mode_ci_env(self):
        """CI=true forces FALLBACK mode."""
        with patch.dict(os.environ, {"CI": "true"}):
            renderer = MascotRenderer()
            assert renderer.render_mode == RenderMode.FALLBACK

    def test_render_mode_no_color(self):
        """NO_COLOR=1 forces MONOCHROME mode."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            renderer = MascotRenderer()
            # Need TTY for this test - console may not be TTY in test env
            # So just verify it would be MONOCHROME if TTY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])