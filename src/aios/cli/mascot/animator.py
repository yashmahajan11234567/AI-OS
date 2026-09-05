"""
AI-OS Cyber Turtle Animator.

Manages animation lifecycle, frame timing, and cancellation.
Ensures clean task lifecycle with no orphan tasks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable
from enum import Enum

from aios.cli.mascot.state import MascotState
from aios.cli.mascot.renderer import MascotRenderer, RenderMode
from aios.cli.mascot.sprites import MascotSprites, MascotSpriteState, MascotAnimation, MascotSpriteState


class AnimationState(str, Enum):
    """Internal animation state."""
    STOPPED = "stopped"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETING = "completing"  # For one-shot COMPLETE animation


@dataclass
class AnimationConfig:
    """Configuration for animation behavior."""
    max_fps: float = 10.0
    frame_delay: float = 0.1
    complete_duration: float = 3.0  # COMPLETE animation duration


class MascotAnimator:
    """
    Manages mascot animation lifecycle.

    - One cancellable asyncio.Task
    - Retain strong reference
    - Cancel cleanly
    - Await task completion
    - No orphan tasks
    - Shutdown-safe
    - Ctrl+C-safe
    """

    def __init__(
        self,
        renderer: MascotRenderer,
        config: Optional[AnimationConfig] = None,
        frame_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.renderer = renderer
        self._config = config or AnimationConfig()
        self._frame_callback = frame_callback or (lambda frame: None)
        self._frame_queue: asyncio.Queue = asyncio.Queue()

        self._task: Optional[asyncio.Task] = None
        self._current_state: Optional[MascotState] = None
        self._animation_state: AnimationState = AnimationState.STOPPED
        self._frame_index: int = 0
        self._start_time: float = 0.0
        self._complete_frames_shown: int = 0

        # Frame timing
        self._min_frame_interval = 1.0 / self._config.max_fps

    @property
    def is_running(self) -> bool:
        return self._animation_state == AnimationState.RUNNING

    @property
    def current_state(self) -> Optional[MascotState]:
        return self._current_state

    @property
    def animation_state(self) -> AnimationState:
        return self._animation_state

    async def start(self, state: MascotState) -> None:
        """
        Start animation for the given state.

        Interrupts any running animation.
        """
        # Cancel current animation if running
        if self._animation_state == AnimationState.RUNNING:
            await self.cancel()

        self._current_state = state
        self._animation_state = AnimationState.RUNNING
        self._frame_index = 0
        self._start_time = time.monotonic()
        self._complete_frames_shown = 0

        # Check if state should animate
        from aios.cli.mascot.state import MascotStateMapper
        if MascotStateMapper.should_animate(state):
            self._task = asyncio.create_task(self._animation_loop())
        else:
            # Static state - just set state, no frame rendering needed
            self._task = None

    async def change_state(self, new_state: MascotState) -> None:
        """
        Transition to a new animation state.

        Per spec §10: new authoritative state interrupts current animation.
        """
        # Check if we should interrupt
        from aios.cli.mascot.state import MascotStateMapper
        if not MascotStateMapper.is_interruptible(self._current_state, new_state):
            return  # Same state, don't restart

        await self.start(new_state)

    async def cancel(self) -> None:
        """Cancel current animation cleanly."""
        if self._animation_state == AnimationState.STOPPED:
            return

        self._animation_state = AnimationState.CANCELLING

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                # Suppress other exceptions during cancellation
                pass

        self._task = None
        self._animation_state = AnimationState.STOPPED
        self._current_state = None

        # Show cursor again - handle both sync and async callbacks
        cursor_frame = self.renderer.show_cursor()
        result = self._frame_callback(cursor_frame)
        if asyncio.iscoroutine(result):
            await result

    async def stop(self) -> None:
        """Stop current animation cleanly (alias for cancel)."""
        await self.cancel()

    async def complete(self, result: str = "PASS") -> None:
        """
        Run COMPLETE one-shot animation.

        Shows scroll open -> result -> scroll close -> return to IDLE.
        Approximately 3 seconds total.
        """
        await self.cancel()

        self._current_state = MascotState.COMPLETE
        self._animation_state = AnimationState.COMPLETING
        self._frame_index = 0
        self._start_time = time.monotonic()

        # Run the complete animation sequence
        animation = MascotSprites.get_animation(MascotSpriteState.COMPLETE)
        frame_delay = self._config.complete_duration / len(animation.frames)

        for frame_idx, frame in enumerate(animation.frames):
            self._frame_index = frame_idx
            rendered = self.renderer.render_animation_frame(
                MascotState.COMPLETE, frame_idx
            )
            await self._frame_callback(rendered)
            await asyncio.sleep(frame_delay)

        # Animation done - return to IDLE
        self._animation_state = AnimationState.STOPPED
        self._task = None

        # Render IDLE state
        idle_frame = self.renderer.render_static(MascotState.IDLE)
        await self._frame_callback(idle_frame)

    async def shutdown(self) -> None:
        """Shutdown animator - cancel any running animation."""
        await self.cancel()

    async def render_startup(
        self,
        version: str,
        status: str,
        health: str,
        mode: str,
        autonomy: str,
    ) -> str:
        """Render startup screen via renderer."""
        return self.renderer.render_startup_screen(version, status, health, mode, autonomy)

    async def _animation_loop(self) -> None:
        """Main animation loop - runs at configured FPS."""
        # Hide cursor during animation
        result = self._frame_callback(self.renderer.hide_cursor())
        if asyncio.iscoroutine(result):
            await result

        try:
            while self._animation_state == AnimationState.RUNNING:
                loop_start = time.monotonic()

                # Get current animation
                animation = MascotSprites.get_animation(MascotSpriteState(self._current_state.value))
                if not animation.frames:
                    break

                # Render frame
                rendered = self.renderer.render_animation_frame(
                    self._current_state, self._frame_index
                )
                result = self._frame_callback(rendered)
                if asyncio.iscoroutine(result):
                    await result
                # Also push to frame queue for testing
                await self._frame_queue.put(rendered)

                # Advance frame
                self._frame_index = (self._frame_index + 1) % len(animation.frames)

                # Frame timing - maintain max FPS
                elapsed = time.monotonic() - loop_start
                sleep_time = max(0, self._min_frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            # Clean cancellation
            raise
        except Exception:
            # On any error, stop animation
            pass
        finally:
            # Always restore cursor
            result = self._frame_callback(self.renderer.show_cursor())
            if asyncio.iscoroutine(result):
                await result


class SyncMascotAnimator:
    """
    Synchronous animator for CLI commands that don't need async.

    Used for simple static rendering or short one-shot animations.
    """

    def __init__(self, renderer: MascotRenderer):
        self._renderer = renderer
        self._animator = MascotAnimator(renderer)

    def start(self, state: MascotState) -> None:
        """Sync start works."""
        self._animator._current_state = state
        self._animator._animation_state = AnimationState.RUNNING

    def stop(self) -> None:
        """Sync stop works."""
        # Cancel any running task
        if self._animator._task:
            self._animator._task.cancel()
            self._animator._task = None
        self._animator._animation_state = AnimationState.STOPPED

    def change_state(self, new_state: MascotState) -> None:
        """Sync change_state works."""
        self._animator._current_state = new_state
        self._animator._animation_state = AnimationState.RUNNING

    def render_startup(
        self,
        version: str,
        status: str,
        health: str,
        mode: str,
        autonomy: str,
    ) -> str:
        """Sync render_startup works."""
        return self._renderer.render_startup_screen(version, status, health, mode, autonomy)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def animate_complete_sync(self, result: str = "PASS", frame_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Synchronous COMPLETE animation (blocking).

        For use in CLI commands that run to completion.
        """
        callback = frame_callback or (lambda frame: print(frame, end="", flush=True))

        animation = MascotSprites.get_animation(MascotSpriteState.COMPLETE)
        frame_delay = 3.0 / len(animation.frames)

        # Hide cursor
        callback(self._renderer.hide_cursor())

        try:
            for frame_idx in range(len(animation.frames)):
                rendered = self._renderer.render_animation_frame(
                    MascotState.COMPLETE, frame_idx
                )
                callback(rendered)
                time.sleep(frame_delay)
        finally:
            # Show cursor and return to idle
            callback(self._renderer.show_cursor())
            idle = self._renderer.render_static(MascotState.IDLE)
            callback(idle)


# Import time for SyncMascotAnimator
import time