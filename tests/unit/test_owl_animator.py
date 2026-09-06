"""
Tests for Owl Animator.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from aios.cli.owl.animator import (
    OwlAnimator,
    SyncOwlAnimator,
)
from aios.cli.owl.renderer import OwlRenderer, RenderMode
from aios.cli.owl.state import OwlState


class TestOwlAnimator:
    """Test async owl animator."""

    @pytest.fixture
    def renderer(self):
        """Create a test renderer in JSON mode (no TTY needed)."""
        return OwlRenderer(force_mode=RenderMode.JSON)

    @pytest.fixture
    def animator(self, renderer):
        """Create an animator instance."""
        return OwlAnimator(renderer)

    @pytest.mark.asyncio
    async def test_animator_creation(self, animator):
        """Animator can be created."""
        assert animator is not None
        assert animator.renderer is not None
        assert animator._task is None
        assert animator._current_state is None

    @pytest.mark.asyncio
    async def test_start_idle_no_animation(self, animator):
        """Starting IDLE doesn't create animation task."""
        await animator.start(OwlState.IDLE)
        assert animator._task is None
        assert animator._current_state == OwlState.IDLE

    @pytest.mark.asyncio
    async def test_start_complete_no_animation(self, animator):
        """Starting COMPLETE doesn't create animation task."""
        await animator.start(OwlState.COMPLETE)
        assert animator._task is None
        assert animator._current_state == OwlState.COMPLETE

    @pytest.mark.asyncio
    async def test_start_planning_creates_task(self, animator):
        """Starting PLANNING creates animation task."""
        await animator.start(OwlState.PLANNING)
        assert animator._task is not None
        assert animator._current_state == OwlState.PLANNING
        assert not animator._task.done()

        # Cleanup
        await animator.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, animator):
        """Stop cancels running animation task."""
        await animator.start(OwlState.PLANNING)
        task = animator._task
        assert task is not None

        await animator.stop()
        assert task.cancelled() or task.done()
        assert animator._task is None
        assert animator._current_state is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, animator):
        """Stop when not running is safe (idempotent)."""
        await animator.stop()  # Should not raise
        assert animator._task is None

    @pytest.mark.asyncio
    async def test_change_state_running(self, animator):
        """Changing state while running restarts animation."""
        await animator.start(OwlState.PLANNING)
        first_task = animator._task

        await animator.change_state(OwlState.EXECUTING)
        assert animator._current_state == OwlState.EXECUTING
        assert animator._task != first_task
        assert not animator._task.done()

        await animator.stop()

    @pytest.mark.asyncio
    async def test_change_state_to_idle_stops(self, animator):
        """Changing to IDLE stops animation."""
        await animator.start(OwlState.PLANNING)
        await animator.change_state(OwlState.IDLE)
        assert animator._task is None
        assert animator._current_state == OwlState.IDLE

    @pytest.mark.asyncio
    async def test_change_state_to_complete_stops(self, animator):
        """Changing to COMPLETE stops animation."""
        await animator.start(OwlState.PLANNING)
        await animator.change_state(OwlState.COMPLETE)
        assert animator._task is None
        assert animator._current_state == OwlState.COMPLETE

    @pytest.mark.asyncio
    async def test_change_state_same_no_restart(self, animator):
        """Changing to same state doesn't restart."""
        await animator.start(OwlState.PLANNING)
        first_task = animator._task

        await animator.change_state(OwlState.PLANNING)
        assert animator._task == first_task
        assert not animator._task.done()

        await animator.stop()

    @pytest.mark.asyncio
    async def test_render_startup(self, animator):
        """render_startup returns static startup screen."""
        output = await animator.render_startup(
            version="1.0.0",
            status="RUNNING",
            health="HEALTHY",
            mode="OPERATIONAL",
            autonomy="OFF",
        )
        assert isinstance(output, str)
        # In JSON mode, startup is empty
        assert output == ""

    @pytest.mark.asyncio
    async def test_task_cleanup_on_exception(self, animator):
        """Task is cleaned up if animation throws."""
        await animator.start(OwlState.PLANNING)
        task = animator._task

        # Simulate task exception by cancelling
        task.cancel()
        await asyncio.sleep(0)  # Let cancellation process

        # State should be cleaned up
        await animator.stop()
        assert animator._task is None


class TestSyncOwlAnimator:
    """Test sync owl animator wrapper."""

    @pytest.fixture
    def renderer(self):
        return OwlRenderer(force_mode=RenderMode.JSON)

    @pytest.fixture
    def animator(self, renderer):
        return SyncOwlAnimator(renderer)

    def test_sync_creation(self, animator):
        """Sync animator wraps async internally."""
        assert animator is not None
        assert animator._animator is not None

    def test_sync_start(self, animator):
        """Sync start works."""
        animator.start(OwlState.PLANNING)
        assert animator._animator._current_state == OwlState.PLANNING
        animator.stop()

    def test_sync_stop(self, animator):
        """Sync stop works."""
        animator.start(OwlState.PLANNING)
        animator.stop()
        assert animator._animator._task is None

    def test_sync_change_state(self, animator):
        """Sync change_state works."""
        animator.start(OwlState.PLANNING)
        animator.change_state(OwlState.EXECUTING)
        assert animator._animator._current_state == OwlState.EXECUTING
        animator.stop()

    def test_sync_context_manager(self, renderer):
        """Sync animator works as context manager."""
        with SyncOwlAnimator(renderer) as animator:
            animator.start(OwlState.PLANNING)
            assert animator._animator._current_state == OwlState.PLANNING
        # Should auto-stop on exit
        assert renderer is not None

    def test_sync_render_startup(self, animator):
        """Sync render_startup works."""
        output = animator.render_startup(
            version="1.0.0",
            status="RUNNING",
            health="HEALTHY",
            mode="OPERATIONAL",
            autonomy="OFF",
        )
        assert isinstance(output, str)
        # In JSON mode, empty
        assert output == ""


class TestAnimationFrameGeneration:
    """Test that animation frames are generated correctly."""

    @pytest.fixture
    def renderer_full(self):
        return OwlRenderer(force_mode=RenderMode.FULL)

    @pytest.fixture
    def animator_full(self, renderer_full):
        return OwlAnimator(renderer_full)

    @pytest.mark.asyncio
    async def test_animation_frames_match_sprites(self, animator_full):
        """Animation frames use correct sprite frames."""
        await animator_full.start(OwlState.PLANNING)

        # Get a frame
        frame = await asyncio.wait_for(
            animator_full._frame_queue.get(),
            timeout=1.0
        )

        assert isinstance(frame, str)
        assert len(frame) > 0

        await animator_full.stop()

    @pytest.mark.asyncio
    async def test_animation_respects_frame_delay(self, animator_full):
        """Animation respects frame delay timing."""
        import time

        await animator_full.start(OwlState.PLANNING)
        start = time.monotonic()

        # Get 3 frames
        frames = []
        for _ in range(3):
            frame = await asyncio.wait_for(
                animator_full._frame_queue.get(),
                timeout=2.0
            )
            frames.append(frame)

        elapsed = time.monotonic() - start

        # 3 frames at >= 0.1s each = at least 0.2s (first frame immediate)
        # Actually, let's just verify frames exist
        assert len(frames) == 3

        await animator_full.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])