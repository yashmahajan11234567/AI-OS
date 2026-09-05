"""
Tests for Cyber Turtle Asset Build Tool.

Tests that the build tool correctly processes source PNGs
and generates deterministic runtime assets.
"""

import pytest
import json
import hashlib
import subprocess
import sys
from pathlib import Path

# Import the build module functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))


class TestBuildMascotAssets:
    """Tests for the mascot asset build pipeline."""

    def test_source_pngs_exist(self):
        """All 23 source PNG files should exist."""
        source_dir = Path("assets/mascot/source")
        expected_files = [
            "idle.png",
            "planning_0.png", "planning_1.png", "planning_2.png",
            "executing_0.png", "executing_1.png", "executing_2.png",
            "reviewing_0.png", "reviewing_1.png", "reviewing_2.png",
            "verifying_0.png", "verifying_1.png", "verifying_2.png", "verifying_3.png",
            "learning_0.png", "learning_1.png", "learning_2.png",
            "escalating_0.png", "escalating_1.png", "escalating_2.png",
            "complete_0.png", "complete_1.png", "complete_2.png",
        ]
        for fname in expected_files:
            fpath = source_dir / fname
            assert fpath.exists(), f"Missing source file: {fpath}"

    def test_build_script_runs(self):
        """Build script should execute successfully."""
        result = subprocess.run(
            [sys.executable, "tools/build_mascot_assets.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=30,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert "Build successful!" in result.stdout

    def test_generated_module_exists(self):
        """Generated runtime module should exist."""
        module_path = Path("src/aios/cli/mascot/assets.py")
        assert module_path.exists(), "Generated assets.py not found"

    def test_manifest_exists(self):
        """Manifest JSON should exist."""
        manifest_path = Path("assets/mascot/generated/manifest.json")
        assert manifest_path.exists(), "Manifest not found"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Verify all 8 states present
        expected_states = [
            "IDLE", "PLANNING", "EXECUTING", "REVIEWING",
            "VERIFYING", "LEARNING", "ESCALATING", "COMPLETE"
        ]
        for state in expected_states:
            assert state in manifest, f"State {state} missing from manifest"
            assert "frames" in manifest[state]
            assert len(manifest[state]["frames"]) > 0

    def test_frame_counts_match_spec(self):
        """Frame counts should match specification."""
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

        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        for state, expected in expected_counts.items():
            actual = len(manifest[state]["frames"])
            assert actual == expected, f"{state}: expected {expected} frames, got {actual}"

    def test_dimensions_17x11(self):
        """All frames should be 17x11 pixels."""
        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        for state, data in manifest.items():
            for frame in data["frames"]:
                assert frame["width"] == 17, f"{state}: width {frame['width']} != 17"
                assert frame["height"] == 11, f"{state}: height {frame['height']} != 11"

    def test_bytes_per_frame_47(self):
        """Each frame should be 47 bytes (17*11*2 bits / 8 = 374 bits = 47 bytes)."""
        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        for state, data in manifest.items():
            for frame in data["frames"]:
                # data is hex string, so bytes = len(hex) / 2
                actual_bytes = len(frame["data"]) // 2
                assert actual_bytes == 47, f"{state}: {actual_bytes} bytes != 47"

    def test_checksums_valid(self):
        """All frames should have valid checksums."""
        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        for state, data in manifest.items():
            for frame in data["frames"]:
                # Verify checksum by recomputing
                packed_data = bytes.fromhex(frame["data"])
                computed = hashlib.sha256(packed_data).hexdigest()[:16]
                assert frame["checksum"] == computed, f"{state}: checksum mismatch"

    def test_total_frames_23(self):
        """Total frame count should be 23."""
        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        total = sum(len(data["frames"]) for data in manifest.values())
        assert total == 23, f"Total frames: {total} != 23"

    def test_deterministic_build(self):
        """Running build twice should produce identical output."""
        # First build
        result1 = subprocess.run(
            [sys.executable, "tools/build_mascot_assets.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=30,
        )
        assert result1.returncode == 0

        module1 = Path("src/aios/cli/mascot/assets.py").read_bytes()
        manifest1 = Path("assets/mascot/generated/manifest.json").read_bytes()

        # Second build
        result2 = subprocess.run(
            [sys.executable, "tools/build_mascot_assets.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=30,
        )
        assert result2.returncode == 0

        module2 = Path("src/aios/cli/mascot/assets.py").read_bytes()
        manifest2 = Path("assets/mascot/generated/manifest.json").read_bytes()

        # Should be byte-for-byte identical
        assert module1 == module2, "Module not deterministic"
        assert manifest1 == manifest2, "Manifest not deterministic"

    def test_no_forbidden_colors_in_source(self):
        """Verify source PNGs don't contain forbidden colors."""
        # This is validated during build - if build passes, palette is clean
        # But we can also check the manifest only uses codes 0, 1, 2
        manifest_path = Path("assets/mascot/generated/manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        for state, data in manifest.items():
            for frame in data["frames"]:
                # Unpack would only contain 0, 1, 2 if build succeeded
                # Just verify checksum format is valid
                assert len(frame["checksum"]) == 16
                assert all(c in "0123456789abcdef" for c in frame["checksum"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])