#!/usr/bin/env python3
"""
Create turtle mascot source PNGs from pixel arrays.
"""

from PIL import Image
import sys
from pathlib import Path

# Palette
BODY_COLORS = {
    1: (0x0D, 0x28, 0x18),  # #0D2818 - darkest
    2: (0x1A, 0x3D, 0x24),  # #1A3D24 - dark
    3: (0x2E, 0x7D, 0x32),  # #2E7D32 - medium
}

ACCENT_COLORS = {
    4: (0x4C, 0xAF, 0x50),  # #4CAF50 - bright
    5: (0x81, 0xC7, 0x84),  # #81C784 - light
    6: (0xA5, 0xD6, 0xA7),  # #A5D6A7 - pale
    7: (0xC8, 0xE6, 0xC9),  # #C8E6C9 - very light
}

# 21x13 canvas
WIDTH = 21
HEIGHT = 13

# Semantic codes from build tool:
# 0 = transparent (00)
# 1 = body (01) - maps to dark greens
# 2 = accent (10) - maps to bright greens

def create_idle_v5():
    """Create the V5 idle turtle with proper anatomy for half-block rendering.

    Design principles for half-block (2 pixel rows = 1 char row):
    - Design in row PAIRS: (0,1), (2,3), (4,5), (6,7), (8,9), (10,11), (12)
    - Shell should be compact (~8-10 chars wide in half-block = 16-20 pixels)
    - Head must be clearly visible on right
    - Neck visible between shell and head
    - 4 legs visible as distinct feet
    - Tail on left/rear
    - NO central vertical ridge
    - EYE: 2 pixels vertically so it renders as full block █ in half-block
    """
    # Start with all transparent
    pixels = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

    # ===================== DESIGN IN ROW PAIRS =====================
    # Pair 0-1: Very top of shell dome (small)
    # Row 0: empty
    # Row 1: shell top
    pixels[1][8] = 1
    pixels[1][9] = 1
    pixels[1][10] = 1
    pixels[1][11] = 1

    # Pair 2-3: Shell upper curve, start of highlights
    # Row 2:
    pixels[2][7] = 1
    pixels[2][8] = 1
    pixels[2][9] = 2  # highlight
    pixels[2][10] = 2  # highlight
    pixels[2][11] = 1
    pixels[2][12] = 1

    # Row 3:
    pixels[3][6] = 1
    pixels[3][7] = 1
    pixels[3][8] = 1
    pixels[3][9] = 1
    pixels[3][10] = 1
    pixels[3][11] = 1
    pixels[3][12] = 1
    pixels[3][13] = 1

    # Pair 4-5: Shell widest part + NECK + HEAD with EYE
    # Row 4: shell body + left highlight + neck base + head top + EYE TOP
    pixels[4][5] = 1
    pixels[4][6] = 2  # left highlight
    pixels[4][7] = 2  # left highlight
    pixels[4][8] = 1
    pixels[4][9] = 1
    pixels[4][10] = 1
    pixels[4][11] = 1
    pixels[4][12] = 2  # right highlight
    pixels[4][13] = 2  # right highlight
    pixels[4][14] = 1
    # Neck starts at shell right edge (x=14)
    pixels[4][15] = 1  # neck
    # Head top
    pixels[4][16] = 1
    pixels[4][17] = 2  # EYE - TOP pixel (accent!)
    pixels[4][18] = 1  # snout top

    # Row 5: shell body + neck + head main + EYE BOTTOM
    pixels[5][4] = 1
    pixels[5][5] = 1
    pixels[5][6] = 2  # left highlight cont.
    pixels[5][7] = 2  # left highlight cont.
    pixels[5][8] = 1
    pixels[5][9] = 1
    pixels[5][10] = 1
    pixels[5][11] = 1
    pixels[5][12] = 2  # right highlight cont.
    pixels[5][13] = 2  # right highlight cont.
    pixels[5][14] = 1
    # Neck
    pixels[5][15] = 1  # neck middle
    # Head
    pixels[5][16] = 1
    pixels[5][17] = 2  # EYE - BOTTOM pixel (accent!) - makes full block █
    pixels[5][18] = 1  # snout

    # Pair 6-7: Shell lower body + HEAD BOTTOM + FRONT LEGS
    # Row 6: shell lower + neck bottom + head bottom
    pixels[6][4] = 1
    pixels[6][5] = 1
    pixels[6][6] = 1
    pixels[6][7] = 1
    pixels[6][8] = 1
    pixels[6][9] = 1
    pixels[6][10] = 1
    pixels[6][11] = 1
    pixels[6][12] = 1
    pixels[6][13] = 1
    pixels[6][14] = 1
    # Neck bottom
    pixels[6][15] = 1
    # Head bottom
    pixels[6][16] = 1
    pixels[6][17] = 1

    # Row 7: shell bottom curve + FRONT LEGS (wider)
    pixels[7][5] = 1
    pixels[7][6] = 1
    pixels[7][7] = 1
    pixels[7][8] = 1
    pixels[7][9] = 1
    pixels[7][10] = 1
    pixels[7][11] = 1
    pixels[7][12] = 1
    pixels[7][13] = 1
    pixels[7][14] = 1
    # Front left leg (wider - 2 pixels)
    pixels[7][4] = 1
    pixels[7][5] = 1
    # Front right leg (wider - 2 pixels)
    pixels[7][13] = 1
    pixels[7][14] = 1

    # Pair 8-9: Shell underside + REAR LEGS + FEET
    # Row 8: shell underside curve + front feet
    pixels[8][6] = 1
    pixels[8][7] = 1
    pixels[8][8] = 1
    pixels[8][9] = 1
    pixels[8][10] = 1
    pixels[8][11] = 1
    pixels[8][12] = 1
    pixels[8][13] = 1
    # Front left foot (accent)
    pixels[8][4] = 2  # foot highlight
    pixels[8][5] = 1  # foot
    # Front right foot (accent)
    pixels[8][12] = 1  # foot
    pixels[8][13] = 2  # foot highlight

    # Row 9: shell bottom edge + rear legs/feet
    pixels[9][7] = 1
    pixels[9][8] = 1
    pixels[9][9] = 1
    pixels[9][10] = 1
    pixels[9][11] = 1
    pixels[9][12] = 1
    # Rear left leg/foot
    pixels[9][4] = 1
    pixels[9][5] = 2  # foot highlight
    # Rear right leg/foot
    pixels[9][12] = 2  # foot highlight
    pixels[9][13] = 1
    # Tail (left/rear) - small, tapered
    pixels[9][2] = 1
    pixels[9][3] = 1

    # Pair 10-11: Tail taper
    # Row 10: tail
    pixels[10][2] = 1
    pixels[10][3] = 1
    # Row 11: tail tip
    pixels[11][2] = 1
    pixels[11][3] = 1

    # Row 12: empty (canvas bottom)

    return pixels


def render_to_png(pixels, output_path):
    """Render pixel array to PNG."""
    img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))

    for y in range(HEIGHT):
        for x in range(WIDTH):
            code = pixels[y][x]
            if code == 0:
                continue
            elif code == 1:
                color = BODY_COLORS[1]  # darkest body
            elif code == 2:
                color = ACCENT_COLORS[4]  # bright accent
            else:
                color = BODY_COLORS[1]

            img.putpixel((x, y), (*color, 255))

    img.save(output_path)
    print(f"Saved to {output_path}")


def create_preview_8x(pixels, output_path):
    """Create 8x scaled preview."""
    img = Image.new('RGBA', (WIDTH * 8, HEIGHT * 8), (0, 0, 0, 0))

    for y in range(HEIGHT):
        for x in range(WIDTH):
            code = pixels[y][x]
            if code == 0:
                color = (0, 0, 0, 0)
            elif code == 1:
                color = (*BODY_COLORS[1], 255)
            elif code == 2:
                color = (*ACCENT_COLORS[4], 255)
            else:
                color = (*BODY_COLORS[1], 255)

            # Draw 8x8 block
            for dy in range(8):
                for dx in range(8):
                    img.putpixel((x * 8 + dx, y * 8 + dy), color)

    img.save(output_path)
    print(f"Preview saved to {output_path}")


def main():
    # Create V5 idle
    pixels = create_idle_v5()

    # Render to PNG
    render_to_png(pixels, Path("assets/mascot/source/idle.png"))
    create_preview_8x(pixels, Path("assets/mascot/source/idle_preview_8x.png"))

    # Print ASCII for verification
    print("\nASCII preview (1=body, 2=accent, .=transparent):")
    for row in pixels:
        line = ''.join('.' if c == 0 else ('#' if c == 1 else '*') for c in row)
        print(line)

    # Stats
    body_count = sum(1 for row in pixels for c in row if c == 1)
    accent_count = sum(1 for row in pixels for c in row if c == 2)
    transparent_count = sum(1 for row in pixels for c in row if c == 0)
    print(f"\nPixels: {body_count} body, {accent_count} accent, {transparent_count} transparent")
    print(f"Total: {body_count + accent_count + transparent_count} (expected {WIDTH * HEIGHT})")

    # Half-block pair analysis
    print("\nHalf-block pairs (combining rows 0-1, 2-3, 4-5, 6-7, 8-9, 10-11, 12):")
    for y in range(0, 13, 2):
        upper = pixels[y] if y < 13 else [0]*21
        lower = pixels[y+1] if y+1 < 13 else [0]*21
        line = ''
        for x in range(21):
            u = upper[x]
            l = lower[x]
            if u != 0 and l != 0:
                if u == 1 and l == 1: line += '#'
                elif u == 2 and l == 2: line += '*'
                elif u == 1 and l == 2: line += '+'
                elif u == 2 and l == 1: line += '='
                else: line += '?'
            elif u != 0:
                if u == 1: line += '^'
                else: line += "'"
            elif l != 0:
                if l == 1: line += 'v'
                else: line += ','
            else:
                line += '.'
        print(f'{y}-{y+1}: {line}')


if __name__ == "__main__":
    main()