#!/usr/bin/env python3
"""
Convert turtle_pixel.png to AI-OS mascot source asset.
Expands current 18x15 turtle by 1-pixel outer layer -> 20x17.
"""
from pathlib import Path

from PIL import Image
import numpy as np
from collections import Counter

SOURCE_DIR = Path("assets/mascot/source")

# Build tool exact palette with categories
PALETTE = {
    # Body/shell colors
    (0x23, 0x5D, 0x2D): 'body',  (0x0D, 0x28, 0x18): 'body',
    (0x1A, 0x3D, 0x24): 'body',  (0x2E, 0x7D, 0x32): 'body',
    (0x69, 0x6B, 0x3A): 'body',  (0x6A, 0x6B, 0x41): 'body',
    # Accent colors (head/legs/tail)
    (0x6D, 0xAF, 0x4B): 'accent',  (0x8C, 0xC2, 0x4A): 'accent',
    (0x8C, 0xC2, 0x68): 'accent',  (0x75, 0xBE, 0x52): 'accent',
    (0x4C, 0xAF, 0x50): 'accent',  (0x81, 0xC7, 0x84): 'accent',
    (0xA5, 0xD6, 0xA7): 'accent',  (0xC8, 0xE6, 0xC9): 'accent',
    # Reference colors
    (0x8E, 0xA7, 0x42): 'accent',  (0xBA, 0xB6, 0x4B): 'plastron',
    (0xB9, 0xB5, 0x4A): 'plastron',  (0xB9, 0xB4, 0x4E): 'plastron',
    (0xBA, 0xB5, 0x4F): 'plastron',
    # Plastron
    (0xB8, 0xB0, 0x48): 'plastron',
    # Eye
    (0x18, 0x10, 0x28): 'eye',  (0, 0, 0): 'eye',
}

# Reference colors for output
REF_COLORS = {
    'body': (0x69, 0x6B, 0x3A),
    'plastron': (0xB9, 0xB4, 0x4E),
    'accent': (0x8C, 0xC2, 0x4A),
    'eye': (0x18, 0x10, 0x28),
}

def nearest_palette(r, g, b):
    best_cat, best_dist = None, float('inf')
    for (pr, pg, pb), cat in PALETTE.items():
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < best_dist:
            best_dist = d
            best_cat = cat
    if best_cat and best_dist < 4000:
        return best_cat
    return 'unknown'

def main():
    img = Image.open('tools/turtle_pixel.png').convert('RGB')
    arr = np.array(img, dtype=np.float32)
    H_ref, W_ref = arr.shape[:2]

    # === CURRENT APPROVED BASELINE: 18x15 ===
    CURRENT_W, CURRENT_H = 18, 15
    SCALE = 38
    off_x = (W_ref - CURRENT_W * SCALE) // 2
    off_y = (H_ref - CURRENT_H * SCALE) // 2

    # === LAYER EXPANSION: add 1-pixel border -> 20x17 ===
    EXPANDED_W, EXPANDED_H = 20, 17

    # Final source is 32x20 (centered)
    W, H = 32, 20
    expanded_offset_x = (W - EXPANDED_W) // 2  # 6
    expanded_offset_y = (H - EXPANDED_H) // 2  # 1

    print(f"Reference: {W_ref}x{H_ref}")
    print(f"Current turtle: {CURRENT_W}x{CURRENT_H}")
    print(f"Expanded turtle: {EXPANDED_W}x{EXPANDED_H}")
    print(f"Source: {W}x{H}")
    print(f"Expanded turtle offset in source: ({expanded_offset_x},{expanded_offset_y})")
    print()

    BG_RGB = (25, 25, 25)

    def is_background(r, g, b):
        return abs(r - BG_RGB[0]) <= 8 and abs(g - BG_RGB[1]) <= 8 and abs(b - BG_RGB[2]) <= 8

    SYM = {'bg': '.', 'body': 'S', 'plastron': 'P', 'accent': 'A', 'eye': 'E'}

    # === Step 1: Load current approved 18x15 shape from source ===
    current_img = Image.open(SOURCE_DIR / 'idle.png').convert('RGBA')
    current_pixels = []
    for y in range(CURRENT_H):
        row = []
        for x in range(CURRENT_W):
            r, g, b, a = current_img.getpixel((x, y))
            if a == 0:
                row.append(None)
            else:
                # Map RGB back to category
                rgb = (r, g, b)
                if rgb in [(0x18,0x10,0x28), (0,0,0)]:
                    row.append('eye')
                elif rgb in [(0x69,0x6B,0x3A),(0x6A,0x6B,0x41)]:
                    row.append('body')
                elif rgb in [(0xB9,0xB4,0x4E),(0xB8,0xB0,0x48)]:
                    row.append('plastron')
                elif rgb in [(0x8C,0xC2,0x4A),(0x8C,0xC2,0x68),(0x6D,0xAF,0x4B)]:
                    row.append('accent')
                else:
                    row.append('body')
        current_pixels.append(row)

    # Print approved 18x15 shape
    print("APPROVED 18x15 BASELINE:")
    for y in range(CURRENT_H):
        row_str = ''.join(SYM.get(c, '.') if c else '.' for c in current_pixels[y])
        if any(c is not None for c in current_pixels[y]):
            print(f"y={y:2d}: {row_str}")
    print()

    # === Step 2: Nearest-neighbor upscale from 18x15 to 20x17 ===
    # This preserves exact internal structure while adding an even outer layer
    expanded_pixels = [[None] * EXPANDED_W for _ in range(EXPANDED_H)]

    for y in range(EXPANDED_H):
        src_y = (y * CURRENT_H) // EXPANDED_H
        for x in range(EXPANDED_W):
            src_x = (x * CURRENT_W) // EXPANDED_W
            expanded_pixels[y][x] = current_pixels[src_y][src_x]

    # Print expanded 20x17 shape
    print("EXPANDED 20x17 (outer layer added):")
    for y in range(EXPANDED_H):
        row_str = ''.join(SYM.get(c, '.') if c else '.' for c in expanded_pixels[y])
        if any(c is not None for c in expanded_pixels[y]):
            print(f"y={y:2d}: {row_str}")
    print()

    # === Step 3: Place on 32x20 canvas ===
    output = Image.new('RGBA', (W, H), (0, 0, 0, 0))

    for ty in range(EXPANDED_H):
        for tx in range(EXPANDED_W):
            category = expanded_pixels[ty][tx]
            if category and category != 'unknown':
                sx = tx + expanded_offset_x
                sy = ty + expanded_offset_y
                if 0 <= sx < W and 0 <= sy < H:
                    color = REF_COLORS.get(category, REF_COLORS['body'])
                    output.putpixel((sx, sy), color + (255,))

    # Save
    output.save('assets/mascot/source/idle.png')
    print(f"\nSaved: assets/mascot/source/idle.png ({W}x{H})")
    print(f"       Expanded turtle centered at ({expanded_offset_x},{expanded_offset_y})")

if __name__ == "__main__":
    main()
