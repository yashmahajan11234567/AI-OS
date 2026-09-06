#!/usr/bin/env python3
"""
Generate the exact M10-T5 V7 idle.png from the pixel blueprint.

21 × 13 pixels, 4-color palette:
D = DARK GREEN #1A3D24 (body)
M = MEDIUM GREEN #2E7D32 (body)
B = BRIGHT GREEN #4CAF50 (accent)
L = LIGHT GREEN #C8E6C9 (accent - eye)
. = TRANSPARENT
"""

from PIL import Image

# Exact 21x13 grid from blueprint
GRID = [
    ".....................",  # Row 0
    ".....................",  # Row 1
    ".......DDDDDD........",  # Row 2
    ".....DDBBDDBBDD......",  # Row 3
    "....DBDDDDDDDBDD.....",  # Row 4
    "...DDDDBDDDBDDDD.....",  # Row 5
    "..DDDDDDDDDDDDDDMMML.",  # Row 6
    ".MDDDDDDDDDDDDDD.MMMB",  # Row 7
    "MMMDDDDDDDDDDDD......",  # Row 8
    "....MM.MM..MM.MM.....",  # Row 9
    "....MM.MM..MM.MM.....",  # Row 10
    "....MM.MM..MM.MM.....",  # Row 11
    ".....................",  # Row 12
]

# Color mapping
COLORS = {
    '.': (0, 0, 0, 0),           # Transparent
    'D': (0x1A, 0x3D, 0x24, 0xFF),  # #1A3D24 - Dark Green (body)
    'M': (0x2E, 0x7D, 0x32, 0xFF),  # #2E7D32 - Medium Green (body)
    'B': (0x4C, 0xAF, 0x50, 0xFF),  # #4CAF50 - Bright Green (accent)
    'L': (0xC8, 0xE6, 0xC9, 0xFF),  # #C8E6C9 - Light Green (accent - eye)
}

def main():
    width = 21
    height = 13

    # Create image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    for y, row in enumerate(GRID):
        for x, char in enumerate(row):
            if char in COLORS:
                img.putpixel((x, y), COLORS[char])
            else:
                raise ValueError(f"Unknown character '{char}' at ({x},{y})")

    # Save
    output_path = "assets/mascot/source/idle.png"
    img.save(output_path)
    print(f"Saved to {output_path}")
    print(f"Dimensions: {img.size}")

    # Also create 8x preview
    preview = img.resize((width * 8, height * 8), Image.NEAREST)
    preview_path = "assets/mascot/source/idle_preview_8x.png"
    preview.save(preview_path)
    print(f"Preview saved to {preview_path}")
    print(f"Preview dimensions: {preview.size}")

    # Verify pixel counts
    pixel_counts = {'D': 0, 'M': 0, 'B': 0, 'L': 0, '.': 0}
    for row in GRID:
        for char in row:
            pixel_counts[char] += 1

    print("\nPixel counts:")
    for k, v in pixel_counts.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()