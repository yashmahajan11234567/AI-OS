#!/usr/bin/env python3
"""
Generate M10-T5 V8 idle.png - Iteration 3
Designed for half-block rendering (7 output rows from 13 pixel rows)
"""

from PIL import Image

# Each row MUST be exactly 21 characters
SILHOUETTE = [
    ".....................",  # 0: 21
    ".........###.........",  # 1: 9+3+9=21
    ".......#######.......",  # 2: 7+7+7=21
    ".....###########.....",  # 3: 5+11+5=21
    "....#############....",  # 4: 4+13+4=21
    "..###############.#..",  # 5: 2+15+1+1+2=21
    "..###############.##.",  # 6: 2+15+1+2+1=21
    "...##############.#..",  # 7: 3+14+1+1+2=21
    "....############.....",  # 8: 4+12+5=21
    "....##..##..##..##...",  # 9: 4+2+2+2+2+2+2+2+3=21
    "....##..##..##..##...",  # 10: 21
    ".....#...#...#...#...",  # 11: 5+1+3+1+3+1+3+1+3=21 (ends with 3 dots)
    ".....................",    # 12: 21
]

# Verify
assert len(SILHOUETTE) == 13
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)}"

print("Silhouette verified: 21x13")
turtle_pixels = sum(row.count('#') for row in SILHOUETTE)
print(f"Turtle pixels: {turtle_pixels}")

print("\nSilhouette:")
for row in SILHOUETTE:
    print(row.replace('.', ' '))

# Color palette
DARK = (0x0D, 0x28, 0x18)       # #0D2818
MEDIUM = (0x1A, 0x3D, 0x24)      # #1A3D24
BRIGHT = (0x4C, 0xAF, 0x50)      # #4CAF50
VERY_LIGHT = (0xC8, 0xE6, 0xC9)  # #C8E6C9 - eye

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD: right side, rows 5-7, x>=15
    if y >= 5 and y <= 7 and x >= 15:
        if x == 17 and y == 6:  # Eye
            return VERY_LIGHT
        if x >= 19:  # Snout tip
            return BRIGHT
        return MEDIUM

    # TAIL: left side, rows 5-7, x<=2
    if y >= 5 and y <= 7 and x <= 2:
        return MEDIUM

    # FEET: rows 9-11
    if y >= 9:
        return BRIGHT

    # SHELL
    if y <= 3:
        if 8 <= x <= 12:
            return DARK
        return MEDIUM
    elif y <= 6:
        if 4 <= x <= 13:
            return DARK
        return MEDIUM
    else:
        return MEDIUM

img = Image.new('RGBA', (21, 13), (0, 0, 0, 0))

for y in range(13):
    for x in range(21):
        is_turtle = SILHOUETTE[y][x] == '#'
        color = get_color(x, y, is_turtle)
        if color:
            img.putpixel((x, y), (*color, 255))

img.save("assets/mascot/source/idle.png")
preview = img.resize((21*8, 13*8), Image.NEAREST)
preview.save("assets/mascot/source/idle_preview_8x.png")
print("\nSaved.")

colors_used = {}
for y in range(13):
    for x in range(21):
        p = img.getpixel((x, y))
        if p[3] > 0:
            key = (p[0], p[1], p[2])
            colors_used[key] = colors_used.get(key, 0) + 1

for rgb, count in sorted(colors_used.items()):
    print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count}")