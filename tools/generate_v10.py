#!/usr/bin/env python3
"""
M10-T5 V10 - Full colored turtle mascot
Targeting unmistakable turtle anatomy in 21x13
"""

from PIL import Image

# V10 Silhouette
SILHOUETTE = [
    ".....................",  # 0
    ".........###.........",  # 1: small dome peak
    ".......#######.......",  # 2: rising
    ".....###########.....",  # 3: widening
    "....#############....",  # 4: shell max width
    "..##############.###.",  # 5: shell + gap + head start
    "..###############..#.",  # 6: shell + gap + head
    "...#############..#..",  # 7: shell lower + head
    "....#############....",  # 8: shell bottom curved
    "....##..##..##..##...",  # 9: four feet
    "....##..##..##..##...",  # 10
    ".....#...#...#...#...",  # 11
    ".....................",   # 12
]

# Verify
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)}"

print("Silhouette verified: 21x13")

# Color palette - using green only with clear shell/head separation
DARK_SHELL = (0x0D, 0x28, 0x18)       # #0D2818 - shell darkest
MED_SHELL = (0x1A, 0x3D, 0x24)        # #1A3D24 - shell medium
LIGHT_SHELL = (0x2E, 0x7D, 0x32)      # #2E7D32 - shell light
DARK_HEAD = (0x2E, 0x7D, 0x32)        # #2E7D32 - head darker
MED_HEAD = (0x4C, 0xAF, 0x50)         # #4CAF50 - head medium
BRIGHT_HEAD = (0x81, 0xC7, 0x84)      # #81C784 - head bright/snout
EYE_COLOR = (0xC8, 0xE6, 0xC9)        # #C8E6C9 - eye
FOOT_COLOR = (0x4C, 0xAF, 0x50)       # #4CAF50 - feet
TAIL_COLOR = (0x2E, 0x7D, 0x32)       # #2E7D32 - tail

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD REGION: rows 5-7, columns 16-20 (after gap at 14-15)
    if y >= 5 and y <= 7 and x >= 16:
        if y == 6 and x == 18:  # Eye position - front of head
            return EYE_COLOR
        if x >= 19:  # Snout tip
            return BRIGHT_HEAD
        if y == 5 and x <= 16:  # Neck (thin)
            return MED_SHELL
        return MED_HEAD  # Head body

    # TAIL: left rear, rows 5-7, x=0-2
    if y >= 5 and y <= 7 and x <= 2:
        return TAIL_COLOR

    # FEET: rows 9-11
    if y >= 9:
        return FOOT_COLOR

    # SHELL - DOMED with clear color
    if y <= 3:
        # Top dome
        if 8 <= x <= 12:
            return DARK_SHELL
        elif 7 <= x <= 13:
            return MED_SHELL
        return MED_SHELL
    elif y == 4:
        # Upper shell
        if 4 <= x <= 14:
            return MED_SHELL
        return MED_SHELL
    elif y <= 6:
        # Mid shell - ends at x=13 (gap at 14-15)
        if x <= 13:
            if 4 <= x <= 12:
                return DARK_SHELL
            return MED_SHELL
        return None  # Gap (transparent)
    elif y <= 8:
        # Lower shell with stepped curve
        if x <= 13:
            return MED_SHELL
        return None
    else:
        return MED_SHELL

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
print("Saved.")

colors_used = {}
for y in range(13):
    for x in range(21):
        p = img.getpixel((x, y))
        if p[3] > 0:
            key = (p[0], p[1], p[2])
            colors_used[key] = colors_used.get(key, 0) + 1

for rgb, count in sorted(colors_used.items()):
    print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count} pixels")