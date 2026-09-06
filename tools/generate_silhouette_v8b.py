#!/usr/bin/env python3
"""
Generate M10-T5 V8 idle.png - Iteration 2
Refined silhouette for better turtle recognition
"""

from PIL import Image

# Refined binary silhouette - more turtle-like
# Each row MUST be exactly 21 characters

SILHOUETTE = [
    ".....................",  # Row 0: 21
    ".......#######.......",  # Row 1: 7+7+7=21
    ".....###########.....",  # Row 2: 5+11+5=21
    "....#############....",  # Row 3: 4+13+4=21
    "...###############...",  # Row 4: 3+15+3=21
    "..###############.##.",  # Row 5: 2+15+1+2+1=21  shell + head start
    "..###############..#.",  # Row 6: 2+15+2+1+1=21
    "...##############.#..",  # Row 7: 3+14+1+1+2=21  head protrudes right
    "....############.....",  # Row 8: 4+12+5=21
    "....##..##..##..##...",  # Row 9: 4+2+2+2+2+2+2+2+3=21  four feet
    "....##..##..##..##...",  # Row 10: same
    ".....#...#...#...#...",  # Row 11: 5+1+3+1+3+1+3+1+3=21  foot bottoms
    ".....................",  # Row 12: 21
]

# Verify dimensions
assert len(SILHOUETTE) == 13
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)}"

print("Silhouette verified: 21x13")
turtle_pixels = sum(row.count('#') for row in SILHOUETTE)
print(f"Turtle pixels: {turtle_pixels}")

# Color palette
DARK = (0x0D, 0x28, 0x18)       # #0D2818
MEDIUM = (0x1A, 0x3D, 0x24)      # #1A3D24
BRIGHT = (0x4C, 0xAF, 0x50)      # #4CAF50
LIGHT = (0x81, 0xC7, 0x84)       # #81C784
PALE = (0xA5, 0xD6, 0xA7)        # #A5D6A7
VERY_LIGHT = (0xC8, 0xE6, 0xC9)  # #C8E6C9 - eye

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD: right side, rows 5-7
    if x >= 15 and y >= 5 and y <= 7:
        if x == 17 and y == 6:  # Eye
            return VERY_LIGHT
        if x >= 18:  # Snout tip
            return BRIGHT
        return MEDIUM  # Neck/head

    # TAIL: left side, rows 5-7
    if x <= 2 and y >= 5 and y <= 7:
        return MEDIUM

    # FEET: rows 9-11
    if y >= 9:
        return BRIGHT

    # SHELL: central mass
    if y <= 3:
        if 7 <= x <= 13:
            return DARK
        return MEDIUM
    elif y <= 6:
        if 5 <= x <= 13:
            return DARK
        return MEDIUM
    else:
        return MEDIUM

# Create image
img = Image.new('RGBA', (21, 13), (0, 0, 0, 0))

for y in range(13):
    for x in range(21):
        is_turtle = SILHOUETTE[y][x] == '#'
        color = get_color(x, y, is_turtle)
        if color:
            img.putpixel((x, y), (*color, 255))

output_path = "assets/mascot/source/idle.png"
img.save(output_path)
print(f"Saved to {output_path}")

preview = img.resize((21*8, 13*8), Image.NEAREST)
preview.save("assets/mascot/source/idle_preview_8x.png")
print("Preview saved")

# Color distribution
colors_used = {}
for y in range(13):
    for x in range(21):
        p = img.getpixel((x, y))
        if p[3] > 0:
            key = (p[0], p[1], p[2])
            colors_used[key] = colors_used.get(key, 0) + 1

print("\nColors used:")
for rgb, count in sorted(colors_used.items()):
    print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count}")