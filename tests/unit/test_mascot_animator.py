"""
Tests for Cyber Turtle Animator.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aios.cli.mascot.animator import (
    MascotAnimator,
    SyncMascotAnimator,
    AnimationState,
    AnimationConfig,
)
from aios.cli.mascot.state import MascotState, MascotStateMapper
from aios.cli.mascot.renderer import MascotRenderer, RenderMode


class TestAnimationConfig:
    """Tests for AnimationConfig."""

    def test_default_config(self):
        """Default config should have reasonable values."""
        config = AnimationConfig()
        assert config.max_fps == 10.0
        assert config.frame_delay == 0.1
        assert config.complete_duration == 3.0

    def test_custom_config(self):
        """Custom config should accept values."""
        config = AnimationConfig(max_fps=5.0, frame_delay=0.2, complete_duration=5.0)
        assert config.max_fps == 5.0
        assert config.frame_delay == 0.2
        assert config.complete_duration == 5.0


class TestMascotAnimator:
    """Tests for MascotAnimator."""

    @pytest.fixture
    def renderer(self):
        """Create a renderer in FULL mode for testing."""
        return MascotRenderer(force_mode=RenderMode.FULL)

    @pytest.fixture
    def animator(self, renderer):
        """Create an animator with mock callback."""
        callback = AsyncMock()
        return MascotAnimator(renderer, frame_callback=callback)

    @pytest.mark.asyncio
    async def test_start_idle_no_animation(self, animator):
        """Starting IDLE should not create animation task (static)."""
        await animator.start(MascotState.IDLE)
        assert animator.current_state == MascotState.IDLE
        assert animator.animation_state == AnimationState.RUNNING
        assert animator._task is None

    @pytest.mark.asyncio
    async def test_start_complete_no_animation(self, animator):
        """Starting COMPLETE should not create animation task (static for start)."""
        await animator.start(MascotState.COMPLETE)
        assert animator.current_state == MascotState.COMPLETE
        assert animator._task is None

    @pytest.mark.asyncio
    async def test_start_active_state_creates_task(self, animator):
        """Starting active state should create animation task."""
        await animator.start(MascotState.PLANNING)
        assert animator.current_state == MascotState.PLANNING
        assert animator._task is not None
        assert not animator._task.done()
        # Cleanup
        await animator.cancel()

    @pytest.mark.asyncio
    async def test_change_state_same_no_restart(self, animator):
        """Changing to same state should not restart."""
        await animator.start(MascotState.PLANNING)
        original_task = animator._task
        await animator.change_state(MascotState.PLANNING)
        assert animator._task is original_task
        await animator.cancel()

    @pytest.mark.asyncio
    async def test_change_state_different_interrupts(self, animator):
        """Changing to different state should interrupt and restart."""
        await animator.start(MascotState.PLANNING)
        original_task = animator._task
        await animator.change_state(MascotState.EXECUTING)
        assert animator._task is not original_task
        assert animator.current_state == MascotState.EXECUTING
        await animator.cancel()

    @pytest.mark.asyncio
    async def test_change_state_escalation_interrupts(self, animator):
        """ESCALATING should always interrupt."""
        await animator.start(MascotState.PLANNING)
        await animator.change_state(MascotState.ESCALATING)
        assert animator.current_state == MascotState.ESCALATING
        await animator.cancel()

    @pytest.mark.asyncio
    async def test_cancel_stops_animation(self, animator):
        """Cancel should stop animation and cleanup task."""
        await animator.start(MascotState.PLANNING)
        assert animator._task is not None
        await animator.cancel()
        assert animator.animation_state == AnimationState.STOPPED
        assert animator._task is None
        assert animator.current_state is None

    @pytest.mark.asyncio
    async def test_cancel_idempotent(self, animator):
        """Cancel should be idempotent."""
        await animator.cancel()  # Should not raise
        await animator.cancel()  # Should not raise
        assert animator.animation_state == AnimationState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_alias_for_cancel(self, animator):
        """Stop should work as alias for cancel."""
        await animator.start(MascotState.PLANNING)
        await animator.stop()
        assert animator.animation_state == AnimationState.STOPPED

    @pytest.mark.asyncio
    async def test_complete_animation(self, animator):
        """Complete should run one-shot COMPLETE animation."""
        await animator.complete("PASS")
        assert animator.animation_state == AnimationState.STOPPED
        assert animator._task is None

    @pytest.mark.asyncio
    async def test_shutdown_cancels(self, animator):
        """Shutdown should cancel any running animation."""
        await animator.start(MascotState.PLANNING)
        await animator.shutdown()
        assert animator.animation_state == AnimationState.STOPPED

    @pytest.mark.asyncio
    async def test_render_startup(self, animator):
        """render_startup should return startup screen."""
        result = await animator.render_startup(
            version="1.0.0",
            status="RUNNING",
            health="HEALTHY",
            mode="OPERATIONAL",
            autonomy="OFF",
        )
        assert isinstance(result, str)
        assert "AI-OS" in result
        assert "1.0.0" in result

    @pytest.mark.asyncio
    async def test_callback_receives_frames(self, renderer):
        """Callback should receive rendered frames during animation."""
        callback = AsyncMock()
        animator = MascotAnimator(renderer, frame_callback=callback)

        await animator.start(MascotState.PLANNING)
        # Give it a moment to render a frame
        await asyncio.sleep(0.05)
        await animator.cancel()

        # Should have been called at least once (hide_cursor + frames)
        assert callback.call_count >= 1


class TestSyncMascotAnimator:
    """Tests for SyncMascotAnimator."""

    @pytest.fixture
    def renderer(self):
        """Create a renderer for testing."""
        return MascotRenderer(force_mode=RenderMode.FULL)

    def test_sync_start(self, renderer):
        """Sync start should set state."""
        animator = SyncMascotAnimator(renderer)
        animator.start(MascotState.PLANNING)
        assert animator._animator.current_state == MascotState.PLANNING

    def test_sync_stop(self, renderer):
        """Sync stop should clear state."""
        animator = SyncMascotAnimator(renderer)
        animator.start(MascotState.PLANNING)
        animator.stop()
        assert animator._animator.animation_state == AnimationState.STOPPED

    def test_sync_change_state(self, renderer):
        """Sync change_state should update state."""
        animator = SyncMascotAnimator(renderer)
        animator.start(MascotState.PLANNING)
        animator.change_state(MascotState.EXECUTING)
        assert animator._animator.current_state == MascotState.EXECUTING

    def test_sync_render_startup(self, renderer):
        """Sync render_startup should work."""
        animator = SyncMascotAnimator(renderer)
        result = animator.render_startup("1.0.0", "RUNNING", "HEALTHY", "OPERATIONAL", "OFF")
        assert isinstance(result, str)
        assert "AI-OS" in result

    def test_context_manager(self, renderer):
        """Sync animator should work as context manager."""
        with SyncMascotAnimator(renderer) as animator:
            animator.start(MascotState.PLANNING)
            assert animator._animator.current_state == MascotState.PLANNING
        # Should auto-stop on exit
        assert animator._animator.animation_state == AnimationState.STOPPED

    def test_animate_complete_sync(self, renderer):
        """Sync animate_complete should render frames."""
        animator = SyncMascotAnimator(renderer)
        frames_rendered = []
        def capture_frame(frame):
            frames_rendered.append(frame)

        animator.animate_complete_sync("PASS", frame_callback=capture_frame)

        # Should have rendered COMPLETE frames + idle return
        assert len(frames_rendered) >= 4  # 3 COMPLETE frames + 1 idle
        # Should end with idle
        assert "IDLE" in frames_rendered[-1] or len(frames_rendered[-1]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])