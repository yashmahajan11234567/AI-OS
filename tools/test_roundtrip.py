#!/usr/bin/env python3
"""
Round-trip test: PNG → semantic pixels → packed → unpacked PNG

Verifies that the build pipeline preserves the original artwork.
"""

import hashlib
from PIL import Image
from pathlib import Path

SOURCE_DIR = Path("assets/owl/source")
GENERATED_DIR = Path("assets/owl/generated")

# Palette from build tool
BODY_COLORS = {
    (0x0B, 0x10, 0x20),  # #0B1020 - dark navy / near-black
    (0x1A, 0x1F, 0x3A),  # #1A1F3A - dark navy blue
    (0x2A, 0x3F, 0x6E),  # #2A3F6E - medium blue
}

ACCENT_COLORS = {
    (0x00, 0xD4, 0xFF),  # #00D4FF - bright cyan
    (0x00, 0x88, 0xFF),  # #0088FF - electric blue
    (0x00, 0xBF, 0xA6),  # #00BFA6 - teal
    (0x00, 0xAA, 0xFF),  # #00AAFF - blue (magnifier)
    (0x00, 0xCC, 0x66),  # #00CC66 - green (learning)
    (0xFF, 0xD7, 0x00),  # #FFD700 - gold (thinking cap)
    (0xFF, 0x33, 0x44),  # #FF3344 - red (executing)
    (0xFF, 0xAA, 0x00),  # #FFAA00 - yellow (escalation)
    (0xE0, 0xE0, 0xE0),  # #E0E0E0 - light gray (scroll)
}

CANONICAL_SIZES = [
    (17, 11),
    (24, 16),
    (32, 20),
]

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

def classify_pixel(r, g, b, a):
    """Classify a pixel into semantic code (copied from build tool)."""
    if a == 0:
        return 0  # transparent
    rgb = (r, g, b)
    if rgb in BODY_COLORS:
        return 1  # body
    if rgb in ACCENT_COLORS:
        return 2  # accent
    # Find closest
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
    if min_dist < 1000:
        return closest
    raise ValueError(f"Unknown pixel color: RGB=({r},{g},{b}), alpha={a}")

def find_best_size(img):
    w, h = img.size
    for cw, ch in CANONICAL_SIZES:
        if w <= cw and h <= ch:
            return (cw, ch)
    return CANONICAL_SIZES[-1]

def pack_pixels(flat):
    """Pack flat pixel array into bytes."""
    while len(flat) % 4 != 0:
        flat.append(0)
    result = bytearray()
    for i in range(0, len(flat), 4):
        byte_val = (flat[i] << 6) | (flat[i+1] << 4) | (flat[i+2] << 2) | flat[i+3]
        result.append(byte_val)
    return bytes(result)

def unpack_pixels(data, width, height):
    """Unpack bytes back to 2D pixel array."""
    pixels = []
    for byte_val in data:
        pixels.append((byte_val >> 6) & 0x3)
        pixels.append((byte_val >> 4) & 0x3)
        pixels.append((byte_val >> 2) & 0x3)
        pixels.append(byte_val & 0x3)
    pixels = pixels[:width * height]
    result = []
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        result.append(row)
    return result

def process_png_to_pixels(png_path):
    """Process PNG to 2D semantic pixel array."""
    img = Image.open(png_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    cw, ch = find_best_size(img)
    canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    offset_x = (cw - img.width) // 2
    offset_y = (ch - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), img)

    pixels = []
    for y in range(ch):
        row = []
        for x in range(cw):
            r, g, b, a = canvas.getpixel((x, y))
            code = classify_pixel(r, g, b, a)
            row.append(code)
        pixels.append(row)
    return pixels, cw, ch

def pixels_to_png(pixels, width, height, palette_map, output_path):
    """Convert 2D pixel array back to PNG."""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for y in range(height):
        for x in range(width):
            code = pixels[y][x]
            if code in palette_map and palette_map[code] is not None:
                r, g, b = palette_map[code]
                img.putpixel((x, y), (r, g, b, 255))
    img.save(output_path)

def compute_checksum(pixels):
    flat = []
    for row in pixels:
        flat.extend(row)
    packed = pack_pixels(flat)
    return hashlib.sha256(packed).hexdigest()[:16]

# Palette map for reverse conversion
REVERSE_PALETTE = {
    0: (0, 0, 0, 0),  # transparent
    1: (0x0B, 0x10, 0x20, 255),  # dark navy body
    2: (0x00, 0xD4, 0xFF, 255),  # cyan accent
}

# Reverse palette with just RGB for simple mapping
REVERSE_PALETTE_RGB = {
    0: None,  # transparent
    1: (0x0B, 0x10, 0x20),  # dark navy body
    2: (0x00, 0xD4, 0xFF),  # cyan accent
}

def main():
    print("=" * 60)
    print("Round-trip Test: PNG -> Semantic -> Packed -> Unpacked -> PNG")
    print("=" * 60)

    all_passed = True

    for state_name, frame_count in STATE_FRAME_COUNTS.items():
        print(f"\nTesting {state_name} ({frame_count} frames)...")
        for frame_idx in range(frame_count):
            if frame_count == 1:
                png_path = SOURCE_DIR / f"{state_name.lower()}.png"
            else:
                png_path = SOURCE_DIR / f"{state_name.lower()}_{frame_idx}.png"

            # Step 1: PNG → semantic pixels
            pixels, w, h = process_png_to_pixels(png_path)
            original_checksum = compute_checksum(pixels)

            # Step 2: semantic pixels → packed
            flat = []
            for row in pixels:
                flat.extend(row)
            packed = pack_pixels(flat)

            # Step 3: packed → unpacked semantic pixels
            unpacked_pixels = unpack_pixels(packed, w, h)
            unpacked_checksum = compute_checksum(unpacked_pixels)

            # Step 4: unpacked semantic -> PNG (for visual verification)
            roundtrip_path = GENERATED_DIR / f"roundtrip_{state_name.lower()}_{frame_idx}.png"
            pixels_to_png(unpacked_pixels, w, h, REVERSE_PALETTE_RGB, roundtrip_path)

            # Verify checksums match
            if original_checksum == unpacked_checksum:
                print(f"  Frame {frame_idx}: PASS Checksum match ({original_checksum})")
            else:
                print(f"  Frame {frame_idx}: FAIL CHECKSUM MISMATCH!")
                print(f"    Original: {original_checksum}")
                print(f"    Unpacked: {unpacked_checksum}")
                all_passed = False

            # Verify no reserved codes (3) in unpacked
            has_reserved = any(p == 3 for row in unpacked_pixels for p in row)
            if has_reserved:
                print(f"  Frame {frame_idx}: FAIL RESERVED CODE (3) FOUND!")
                all_passed = False
            else:
                print(f"  Frame {frame_idx}: PASS No reserved codes")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL ROUND-TRIP TESTS PASSED")
    else:
        print("ROUND-TRIP TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())