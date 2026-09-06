"""
Unit tests for OwlAssets runtime module.

Tests:
- All 8 states have valid frames
- Frame dimensions valid
- Packed frame byte lengths valid
- Reserved pixel code rejected
- Checksum deterministic
- Asset loading deterministic
"""

from __future__ import annotations

import pytest

from aios.cli.owl.assets import OwlAssets, _FrameData


class TestOwlAssets:
    """Tests for OwlAssets runtime module."""

    # All 8 canonical states
    STATES = [
        "IDLE",
        "PLANNING",
        "EXECUTING",
        "REVIEWING",
        "VERIFYING",
        "LEARNING",
        "ESCALATING",
        "COMPLETE",
    ]

    def test_all_states_have_frames(self):
        """All 8 states must have at least one frame."""
        for state in self.STATES:
            frames = OwlAssets.get_frames(state)
            assert len(frames) > 0, f"State {state} has no frames"
            # Verify each frame is a _FrameData instance
            for frame in frames:
                assert isinstance(frame, _FrameData), f"Frame for {state} is not _FrameData"

    def test_frame_dimensions_valid(self):
        """All frames must have positive dimensions."""
        for state in self.STATES:
            frames = OwlAssets.get_frames(state)
            for frame in frames:
                assert frame.width > 0, f"Frame width must be positive for {state}"
                assert frame.height > 0, f"Frame height must be positive for {state}"

    def test_packed_frame_byte_lengths_valid(self):
        """Packed frame data length must match dimensions."""
        for state in self.STATES:
            frames = OwlAssets.get_frames(state)
            for frame in frames:
                # 2 bits per pixel = 4 pixels per byte
                expected_bytes = (frame.width * frame.height + 3) // 4
                assert len(frame.data) == expected_bytes, \
                    f"Frame data length mismatch for {state}: got {len(frame.data)}, expected {expected_bytes}"

    def test_reserved_pixel_code_rejected(self):
        """Reserved pixel code (11) should not appear in any frame."""
        for state in self.STATES:
            frames = OwlAssets.get_frames(state)
            for frame in frames:
                pixels = frame.unpack()
                for row in pixels:
                    for pixel in row:
                        assert pixel != 3, f"Reserved pixel code (11) found in {state}"

    def test_checksum_deterministic(self):
        """Checksum must be deterministic for each frame."""
        for state in self.STATES:
            frames = OwlAssets.get_frames(state)
            for frame in frames:
                # Verify checksum matches
                assert frame.verify(), f"Checksum verification failed for {state} frame"

    def test_asset_loading_deterministic(self):
        """Repeated loading must produce identical results."""
        for state in self.STATES:
            frames1 = OwlAssets.get_frames(state)
            frames2 = OwlAssets.get_frames(state)
            assert len(frames1) == len(frames2)
            for f1, f2 in zip(frames1, frames2):
                assert f1.width == f2.width
                assert f1.height == f2.height
                assert f1.data == f2.data
                assert f1.checksum == f2.checksum

    def test_get_frame_index_wrapping(self):
        """Frame index should wrap around."""
        for state in self.STATES:
            frame_count = OwlAssets.get_frame_count(state)
            if frame_count > 1:
                frame0 = OwlAssets.get_frame(state, 0)
                frame_wrapped = OwlAssets.get_frame(state, frame_count)
                assert frame0.data == frame_wrapped.data

    def test_get_frame_count(self):
        """Frame counts must match expected."""
        expected_counts = {
            "IDLE": 1,
            "PLANNING": 3,
            "EXECUTING": 3,
            "REVIEWING": 3,
            "VERIFYING": 4,
            "LEARNING": 3,
            "ESCALATING": 3,
            "COMPLETE": 3,
        }
        for state, expected in expected_counts.items():
            assert OwlAssets.get_frame_count(state) == expected, f"Frame count mismatch for {state}"

    def test_get_dimensions(self):
        """Dimensions must be consistent for each state."""
        for state in self.STATES:
            w, h = OwlAssets.get_dimensions(state)
            assert w > 0 and h > 0
            # All frames in a state should have same dimensions
            frames = OwlAssets.get_frames(state)
            for frame in frames:
                assert frame.width == w
                assert frame.height == h

    def test_verify_all(self):
        """Global verification must pass."""
        assert OwlAssets.verify_all(), "Global asset verification failed"

    def test_unknown_state_returns_idle(self):
        """Unknown state should fall back to IDLE."""
        frames = OwlAssets.get_frames("UNKNOWN_STATE")
        idle_frames = OwlAssets.get_frames("IDLE")
        assert frames == idle_frames

    def test_frame_data_immutability(self):
        """FrameData should be frozen/immutable."""
        frame = OwlAssets.get_frame("IDLE", 0)
        assert hasattr(frame, '__dataclass_fields__')
        # dataclass with frozen=True should prevent mutation
        with pytest.raises(AttributeError):
            frame.width = 999


class TestFrameDataInternals:
    """Tests for internal _FrameData methods."""

    def test_unpack_returns_2d_array(self):
        """unpack() should return 2D list matching dimensions."""
        frame = OwlAssets.get_frame("IDLE", 0)
        pixels = frame.unpack()
        assert len(pixels) == frame.height
        for row in pixels:
            assert len(row) == frame.width

    def test_unpack_values_valid(self):
        """Unpacked pixel values must be valid semantic codes (0, 1, 2)."""
        frame = OwlAssets.get_frame("IDLE", 0)
        pixels = frame.unpack()
        for row in pixels:
            for pixel in row:
                assert pixel in (0, 1, 2), f"Invalid pixel code: {pixel}"

    def test_verify_method(self):
        """verify() method should validate checksum."""
        frame = OwlAssets.get_frame("IDLE", 0)
        assert frame.verify() is True

        # Corrupt data should fail
        import hashlib
        corrupt_data = bytes([b ^ 0xFF for b in frame.data])
        corrupt_frame = _FrameData(
            width=frame.width,
            height=frame.height,
            data=corrupt_data,
            checksum=frame.checksum,
        )
        assert corrupt_frame.verify() is False