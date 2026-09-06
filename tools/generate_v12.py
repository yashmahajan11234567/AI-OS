#!/usr/bin/env python3
"""
M10-T5 V12 - Optimized for half-block 2-color rendering
Dome created via upper/lower half-block pattern
"""

from PIL import Image

# Design for half-block pairs:
# Output row 0 (px 0,1): ▄▄▄ - only px 1 set (sparse peak)
# Output row 1 (px 2,3): ▄▄███████▄▄ - px 2 sparse, px 3 dense
# Output row 2 (px 4,5): ██████████ - both dense
# Output row 3 (px 6,7): ▄█████████▄▄▄▄ - px 6 dense, px 7 sparse (head)
# Output row 4 (px 8,9): ██▀▀██▀▀██▀ ██▀▀ - px 8 dense, px 9 sparse (feet)
# Output row 5 (px 10,11): ▀█  ▀█  ▀█  ▀█ - px 10 sparse, px 11 sparse
# Output row 6 (px 12): empty

# SILHOUETTE ONLY - use BODY color for shell, ACCENT for head/feet
# Body colors (#0D2818, #1A3D24, #2E7D32) -> code 01 (dark)
# Accent colors (#4CAF50, #81C784, #A5D6A7, #C8E6C9) -> code 10 (bright)
# Eye: DARK_SHELL (#0D2818) -> body code

BODY = (0x1A, 0x3D, 0x24)       # #1A3D24 - primary shell color
ACCENT = (0x4C, 0xAF, 0x50)     # #4CAF50 - head, feet highlights
EYE = (0x0D, 0x28, 0x18)        # #0D2818 - eye (darkest body)

# Row 7: "...##########..####.." = 3 + 10 + 2 + 4 + 2 = 21
SILHOUETTE = [
    ".....................",  # y=0: empty
    ".........###.........",  # y=1: peak - sparse (3 wide) -> output row 0: ▄▄▄
    ".......#######.......",  # y=2: rising sparse (7 wide) -> output row 1 upper
    ".....###########.....",  # y=3: widening dense (11 wide) -> output row 1 lower
    "....#############....",  # y=4: max dense (13 wide) -> output row 2 upper
    "....#############....",  # y=5: max dense (13 wide) -> output row 2 lower
    "....#############....",  # y=6: upper shell dense (13 wide) -> output row 3 upper
    "...##########..####..",  # y=7: shell lower (10) + gap + head (4) -> output row 3 lower
    "....#############....",  # y=8: shell bottom dense (13) -> output row 4 upper
    "....##..##..##..##...",  # y=9: four feet -> output row 4 lower
    "....##..##..##..##...",  # y=10: four feet -> output row 5 upper
    ".....#...#...#...#...",  # y=11: toes -> output row 5 lower
    ".....................",   # y=12: empty -> output row 6
]

# Verify
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)} - '{row}'"
assert len(SILHOUETTE) == 13

print("Silhouette verified: 21x13")

img = Image.new('RGBA', (21, 13), (0, 0, 0, 0))

# Base coloring: shell=BODY, head/feet=ACCENT
for y in range(13):
    for x in range(21):
        if SILHOUETTE[y][x] == '#':
            # Head: y=7, x>=16 (after gap at 13,14)
            if y == 7 and x >= 15:
                img.putpixel((x, y), (*ACCENT, 255))
            # Feet: y>=9
            elif y >= 9:
                img.putpixel((x, y), (*ACCENT, 255))
            # Tail: left side y=6-8, x<=2
            elif y >= 6 and y <= 8 and x <= 2:
                img.putpixel((x, y), (*BODY, 255))
            # Shell: everything else
            else:
                img.putpixel((x, y), (*BODY, 255))

# --- HEAD REFINEMENT ---
# Row 6 (y=6): shell to x=14, neck at 15, head at 16,17
# Row 7 (y=7): shell to x=12, neck 13,14, head 15,16,17, snout 18,19

# Clear row 6 right side (x >= 15)
for x in range(15, 21):
    img.putpixel((x, 6), (0, 0, 0, 0))

# Row 6: shell x=4-14, neck 15, head 16,17
for x in range(4, 15):
    img.putpixel((x, 6), (*BODY, 255))
img.putpixel((15, 6), (*BODY, 255))   # Neck
img.putpixel((16, 6), (*ACCENT, 255)) # Head
img.putpixel((17, 6), (*ACCENT, 255)) # Head

# Clear row 7 right side (x >= 13)
for x in range(13, 21):
    img.putpixel((x, 7), (0, 0, 0, 0))

# Row 7: shell x=3-12, neck 13,14, head 15,16,17, snout 18,19
for x in range(3, 13):
    img.putpixel((x, 7), (*BODY, 255))
img.putpixel((13, 7), (*BODY, 255))   # Neck
img.putpixel((14, 7), (*BODY, 255))   # Neck
img.putpixel((15, 7), (*ACCENT, 255)) # Head back
img.putpixel((16, 7), (*ACCENT, 255)) # Head middle
img.putpixel((17, 7), (*EYE, 255))    # Eye
img.putpixel((18, 7), (*ACCENT, 255)) # Head front
img.putpixel((19, 7), (*ACCENT, 255)) # Snout

img.save("assets/mascot/source/idle.png")
preview = img.resize((21*8, 13*8), Image.NEAREST)
preview.save("assets/mascot/source/idle_preview_8x.png")
print("Saved.")

colors_used = {}
for y in range(13):
    for x in range(21):
        p = img.getpixel((x, y))
        if p[3] > 0:
            key = (p[0], p[1], p[2])
            colors_used[key] = colors_used.get(key, 0) + 1

print("\nColors used:")
for rgb, count in sorted(colors_used.items()):
    print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count} pixels")

print("\nSilhouette:")
for y in range(13):
    row_str = ""
    for x in range(21):
        p = img.getpixel((x, y))
        row_str += '#' if p[3] > 0 else '.'
    print(row_str)