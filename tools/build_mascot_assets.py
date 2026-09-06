#!/usr/bin/env python3
"""
AI-OS Mascot Asset Build Tool.

Converts PNG pixel-art source files into packed 2-bit raster representation
for deterministic runtime rendering. Uses Pillow for build-time processing
only - Pillow is NOT a runtime dependency.

Semantic pixel codes:
    00 = transparent
    01 = body (dark green)
    10 = accent (green)
    11 = reserved (rejects if found)

Runtime format: deterministic bytes, packed 4 pixels per byte (2 bits each).
"""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow required for build tool. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Palette mapping: RGB -> semantic code
# Dark green body colors -> 01 (body)
# Green accent colors -> 10 (accent)
# Transparent -> 00
# Anything else -> error

BODY_COLORS = {
    (0x0D, 0x28, 0x18),  # #0D2818 - dark green / near-black body
    (0x1A, 0x3D, 0x24),  # #1A3D24 - medium dark green
    (0x2E, 0x7D, 0x32),  # #2E7D32 - lighter green for body detail
}

ACCENT_COLORS = {
    (0x4C, 0xAF, 0x50),  # #4CAF50 - bright green accent
    (0x81, 0xC7, 0x84),  # #81C784 - highlight green
    (0xA5, 0xD6, 0xA7),  # #A5D6A7 - pale green
    (0xC8, 0xE6, 0xC9),  # #C8E6C9 - very light green (thought bubbles, etc.)
}

RESERVED_CODE = 0b11  # 11 = reserved, should never appear in valid source

# Target dimensions (new: 21x13)
TARGET_WIDTH = 21
TARGET_HEIGHT = 13

# Acceptable canonical sizes (in priority order)
CANONICAL_SIZES = [
    (21, 13),
    (24, 16),
    (32, 20),
]

SOURCE_DIR = Path("assets/mascot/source")
GENERATED_DIR = Path("assets/mascot/generated")
OUTPUT_MODULE = Path("src/aios/cli/mascot/assets.py")

# State definitions
MASCOT_STATES = [
    "IDLE",
    "PLANNING",
    "EXECUTING",
    "REVIEWING",
    "VERIFYING",
    "LEARNING",
    "ESCALATING",
    "COMPLETE",
]

# Frames per state (for animations)
STATE_FRAME_COUNTS = {
    "IDLE": 1,
    "PLANNING": 3,
    "EXECUTING": 3,
    "REVIEWING": 3,
    "VERIFYING": 4,
    "LEARNING": 3,
    "ESCALATING": 3,
    "COMPLETE": 3,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class FrameData:
    """Packed frame data for runtime."""
    width: int
    height: int
    data: bytes  # Packed 2-bit pixels: 4 pixels per byte
    checksum: str  # SHA256 of raw pixel data for verification

    def __post_init__(self):
        expected_bytes = (self.width * self.height + 3) // 4
        if len(self.data) != expected_bytes:
            raise ValueError(f"Data length {len(self.data)} != expected {expected_bytes}")

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "data": self.data.hex(),
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FrameData":
        return cls(
            width=d["width"],
            height=d["height"],
            data=bytes.fromhex(d["data"]),
            checksum=d["checksum"],
        )


@dataclass(frozen=True)
class StateData:
    """All frames for a state."""
    name: str
    frames: List[FrameData]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "frames": [f.to_dict() for f in self.frames],
        }


# =============================================================================
# COLOR CLASSIFICATION
# =============================================================================

def classify_pixel(r: int, g: int, b: int, a: int) -> int:
    """
    Classify a pixel into semantic code.

    Returns:
        0 = transparent
        1 = body
        2 = accent
        3 = reserved (error)
    """
    if a == 0:
        return 0  # transparent

    rgb = (r, g, b)
    if rgb in BODY_COLORS:
        return 1  # body
    if rgb in ACCENT_COLORS:
        return 2  # accent

    # Unknown color - check if close to body or accent
    closest = None
    min_dist = float('inf')

    for body_rgb in BODY_COLORS:
        dist = (r - body_rgb[0])**2 + (g - body_rgb[1])**2 + (b - body_rgb[2])**2
        if dist < min_dist:
            min_dist = dist
            closest = 1

    for accent_rgb in ACCENT_COLORS:
        dist = (r - accent_rgb[0])**2 + (g - accent_rgb[1])**2 + (b - accent_rgb[2])**2
        if dist < min_dist:
            min_dist = dist
            closest = 2

    if min_dist < 1000:  # Tolerance threshold
        print(f"WARNING: Pixel ({r},{g},{b}) not in exact palette, classified as {'body' if closest==1 else 'accent'} (dist={min_dist})", file=sys.stderr)
        return closest

    raise ValueError(f"Unknown pixel color: RGB=({r},{g},{b}), alpha={a}. Not in allowed palette.")


# =============================================================================
# PACKING / UNPACKING
# =============================================================================

def pack_pixels(pixels: List[List[int]]) -> bytes:
    """
    Pack 2D array of 2-bit pixel codes into bytes.
    4 pixels per byte, row-major order.
    """
    flat = []
    for row in pixels:
        flat.extend(row)

    # Pad to multiple of 4
    while len(flat) % 4 != 0:
        flat.append(0)

    result = bytearray()
    for i in range(0, len(flat), 4):
        byte_val = (flat[i] << 6) | (flat[i+1] << 4) | (flat[i+2] << 2) | flat[i+3]
        result.append(byte_val)

    return bytes(result)


def unpack_pixels(data: bytes, width: int, height: int) -> List[List[int]]:
    """Unpack bytes back to 2D pixel array."""
    pixels = []
    for byte_val in data:
        pixels.append((byte_val >> 6) & 0x3)
        pixels.append((byte_val >> 4) & 0x3)
        pixels.append((byte_val >> 2) & 0x3)
        pixels.append(byte_val & 0x3)

    # Trim to actual size
    pixels = pixels[:width * height]

    # Reshape to 2D
    result = []
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        result.append(row)

    return result


def compute_checksum(pixels: List[List[int]]) -> str:
    """Compute SHA256 of raw pixel data for verification."""
    flat = []
    for row in pixels:
        flat.extend(row)
    # Pack for hashing
    packed = pack_pixels(pixels)
    return hashlib.sha256(packed).hexdigest()[:16]


# =============================================================================
# IMAGE PROCESSING
# =============================================================================

def find_best_size(image: Image.Image) -> Tuple[int, int]:
    """Find the best canonical size that accommodates the image."""
    w, h = image.size
    for cw, ch in CANONICAL_SIZES:
        if w <= cw and h <= ch:
            return (cw, ch)
    # If image is larger than largest canonical, use largest
    return CANONICAL_SIZES[-1]


def process_png(png_path: Path, target_width: int, target_height: int) -> List[List[int]]:
    """
    Process a PNG file into 2D semantic pixel array.
    Validates dimensions and palette.
    """
    img = Image.open(png_path)

    # Convert to RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Find best canonical size
    cw, ch = find_best_size(img)
    if (cw, ch) != (target_width, target_height):
        print(f"  Note: Using canonical size {cw}x{ch} instead of {target_width}x{target_height}")

    # Create canvas at canonical size
    canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    # Center the image
    offset_x = (cw - img.width) // 2
    offset_y = (ch - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), img)

    # Classify each pixel
    pixels = []
    for y in range(ch):
        row = []
        for x in range(cw):
            r, g, b, a = canvas.getpixel((x, y))
            code = classify_pixel(r, g, b, a)
            if code == RESERVED_CODE:
                raise ValueError(f"Reserved pixel code (11) found at ({x},{y})")
            row.append(code)
        pixels.append(row)

    return pixels


# =============================================================================
# BUILD PIPELINE
# =============================================================================

def build_state(state_name: str, frame_count: int) -> StateData:
    """Build all frames for a state."""
    frames = []

    for frame_idx in range(frame_count):
        # Try both single file and numbered files
        if frame_count == 1:
            png_path = SOURCE_DIR / f"{state_name.lower()}.png"
        else:
            png_path = SOURCE_DIR / f"{state_name.lower()}_{frame_idx}.png"

        if not png_path.exists():
            raise FileNotFoundError(f"Source PNG not found: {png_path}")

        print(f"  Processing {png_path.name}...")

        pixels = process_png(png_path, TARGET_WIDTH, TARGET_HEIGHT)
        checksum = compute_checksum(pixels)
        data = pack_pixels(pixels)

        frame = FrameData(
            width=len(pixels[0]),
            height=len(pixels),
            data=data,
            checksum=checksum,
        )
        frames.append(frame)

    return StateData(name=state_name, frames=frames)


def build_all() -> Dict[str, StateData]:
    """Build all states."""
    all_states = {}
    for state in MASCOT_STATES:
        print(f"Building {state}...")
        frame_count = STATE_FRAME_COUNTS[state]
        all_states[state] = build_state(state, frame_count)
    return all_states


def generate_runtime_module(states: Dict[str, StateData]) -> str:
    """Generate the runtime assets.py module."""
    lines = [
        '"""',
        'AI-OS Cyber Turtle Runtime Assets.',
        '',
        'AUTO-GENERATED by tools/build_mascot_assets.py',
        'DO NOT EDIT MANUALLY.',
        '',
        'Packed 2-bit raster data for deterministic pixel-art turtle rendering.',
        'Semantic codes: 00=transparent, 01=body (green), 10=accent (green), 11=reserved',
        '"""',
        '',
        '# flake8: noqa',
        '# fmt: off',
        '',
        'from dataclasses import dataclass',
        'from typing import Dict, List, Tuple',
        '',
        '',
        '@dataclass(frozen=True)',
        'class _FrameData:',
        '    """Internal frame data."""',
        '    width: int',
        '    height: int',
        '    data: bytes',
        '    checksum: str',
        '',
        '    def unpack(self) -> List[List[int]]:',
        '        """Unpack to 2D pixel array."""',
        '        pixels = []',
        '        for byte_val in self.data:',
        '            pixels.append((byte_val >> 6) & 0x3)',
        '            pixels.append((byte_val >> 4) & 0x3)',
        '            pixels.append((byte_val >> 2) & 0x3)',
        '            pixels.append(byte_val & 0x3)',
        '        pixels = pixels[:self.width * self.height]',
        '        result = []',
        '        for y in range(self.height):',
        '            result.append(pixels[y * self.width:(y + 1) * self.width])',
        '        return result',
        '',
        '    def verify(self) -> bool:',
        '        """Verify checksum matches."""',
        '        import hashlib',
        '        packed = self.data',
        '        return hashlib.sha256(packed).hexdigest()[:16] == self.checksum',
        '',
        '',
        'class MascotAssets:',
        '    """Runtime access to mascot pixel-art assets."""',
        '',
        '    # Packed frame data for all states',
        '    _FRAMES: Dict[str, List[_FrameData]] = {',
    ]

    for state_name, state_data in states.items():
        lines.append(f'        "{state_name}": [')
        for frame in state_data.frames:
            lines.extend([
                f'            _FrameData(',
                f'                width={frame.width},',
                f'                height={frame.height},',
                f'                data=bytes.fromhex("{frame.data.hex()}"),',
                f'                checksum="{frame.checksum}",',
                f'            ),',
            ])
        lines.append('        ],')

    lines.extend([
        '    }',
        '',
        '    # Frame counts per state',
        '    _FRAME_COUNTS = {',
    ])
    for state_name, state_data in states.items():
        lines.append(f'        "{state_name}": {len(state_data.frames)},')

    lines.extend([
        '    }',
        '',
        '    # Canonical dimensions (all frames same per state)',
        '    _DIMENSIONS = {',
    ])
    for state_name, state_data in states.items():
        if state_data.frames:
            f = state_data.frames[0]
            lines.append(f'        "{state_name}": ({f.width}, {f.height}),')

    lines.extend([
        '    }',
        '',
        '    @classmethod',
        '    def get_frames(cls, state: str) -> List[_FrameData]:',
        '        """Get all frames for a state."""',
        '        return cls._FRAMES.get(state, cls._FRAMES["IDLE"])',
        '',
        '    @classmethod',
        '    def get_frame(cls, state: str, index: int) -> _FrameData:',
        '        """Get specific frame for a state."""',
        '        frames = cls.get_frames(state)',
        '        return frames[index % len(frames)]',
        '',
        '    @classmethod',
        '    def get_frame_count(cls, state: str) -> int:',
        '        """Get number of frames for a state."""',
        '        return cls._FRAME_COUNTS.get(state, 1)',
        '',
        '    @classmethod',
        '    def get_dimensions(cls, state: str) -> Tuple[int, int]:',
        '        """Get dimensions for a state."""',
        '        return cls._DIMENSIONS.get(state, (17, 11))',
        '',
        '    @classmethod',
        '    def verify_all(cls) -> bool:',
        '        """Verify all asset checksums."""',
        '        for frames in cls._FRAMES.values():',
        '            for frame in frames:',
        '                if not frame.verify():',
        '                    return False',
        '        return True',
        '',
        '',
        '# Module-level validation on import',
        'if not MascotAssets.verify_all():',
        '    raise RuntimeError("Mascot asset checksum verification failed")',
    ])

    return '\n'.join(lines)


def main():
    """Main build entry point."""
    print("=" * 60)
    print("AI-OS Mascot Asset Build Tool")
    print("=" * 60)

    # Verify source directory exists
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    # Build all states
    try:
        states = build_all()
    except Exception as e:
        print(f"ERROR: Build failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate runtime module
    print("\nGenerating runtime module...")
    module_code = generate_runtime_module(states)

    # Write output
    OUTPUT_MODULE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MODULE.write_text(module_code)
    print(f"Written to: {OUTPUT_MODULE}")

    # Also write JSON manifest for debugging
    manifest = {name: state.to_dict() for name, state in states.items()}
    manifest_path = GENERATED_DIR / "manifest.json"
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written to: {manifest_path}")

    # Summary
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    for state_name, state_data in states.items():
        f = state_data.frames[0]
        print(f"  {state_name}: {len(state_data.frames)} frame(s), {f.width}x{f.height}, {len(f.data)} bytes/frame")

    print("\nBuild successful!")
    return 0


if __name__ == "__main__":
    sys.exit(main())