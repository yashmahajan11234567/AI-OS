#!/usr/bin/env python3
"""
Generate M10-T5 V8 idle.png - Iteration 4
Better head/shell separation, clearer turtle
"""

from PIL import Image

# Key improvements:
# - Clear gap between shell and head (neck)
# - Head is more rounded and protrudes further
# - Tail visible on left
# - Feet well separated

SILHOUETTE = [
    ".....................",  # 0
    ".........###.........",  # 1: small dome peak
    ".......#######.......",  # 2
    ".....###########.....",  # 3
    "....#############....",  # 4: shell upper
    "..#############..###.",  # 5: shell GAP head (neck at x=13, head at 15+)
    "..#############..###.",  # 6: shell GAP head clear
    "...############..#...",  # 7: shell lower, head separate
    "....############.....",  # 8: shell bottom
    "....##..##..##..##...",  # 9: feet
    "....##..##..##..##...",  # 10
    ".....#...#...#...#...",  # 11
    ".....................",   # 12
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

    # HEAD: right side, rows 5-7, x>=15 (after gap at x=13-14)
    if y >= 5 and y <= 7 and x >= 15:
        if x == 17 and y == 6:  # Eye
            return VERY_LIGHT
        if x >= 19:  # Snout
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
        # Shell ends at x=13 (gap at 14, head at 15+)
        if x <= 13:
            if 4 <= x <= 12:
                return DARK
            return MEDIUM
        return None  # Gap is transparent
    else:
        if x <= 12:
            return MEDIUM
        return None

# Silent gap handling - the gap is created by silhouette having '.' at x=13-14
# But we need to ensure the shell doesn't extend into gap

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