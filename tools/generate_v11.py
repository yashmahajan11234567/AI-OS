#!/usr/bin/env python3
"""
M10-T5 V11 - Face refinement only
Connect neck to head, square head with single dark eye
"""

from PIL import Image

# V10b silhouette with gap removed - neck connects to head
# Row 7: shell lower + neck + head (connected)
# Row 8: shell bottom + head bottom (square)
SILHOUETTE = [
    ".....................",  # 0
    ".........###.........",  # 1: dome peak
    ".......#######.......",  # 2: rising
    ".....###########.....",  # 3: widening
    "....#############....",  # 4: shell max
    "....#############....",  # 5: shell max
    "....#############....",  # 6: shell end
    "...##############....",  # 7: shell lower + neck + head (3+14+4=21) - CONNECTED
    "....###########.####.",  # 8: shell bottom + head bottom (4+11+1+4+1=21) - square head
    "....##..##..##..##...",  # 9: feet
    "....##..##..##..##...",  # 10: feet
    ".....#...#...#...#...",  # 11: toes
    ".....................",   # 12
]

# Verify
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)} - '{row}'"

print("Silhouette verified: 21x13")
print(f"Turtle pixels: {sum(row.count('#') for row in SILHOUETTE)}")

# Palette - darkest body color for eye (reads as dark dot)
DARK_SHELL = (0x0D, 0x28, 0x18)       # #0D2818 - darkest body, used for eye
MED_SHELL = (0x1A, 0x3D, 0x24)        # #1A3D24 - medium body
HEAD_COLOR = (0x4C, 0xAF, 0x50)       # #4CAF50 - head main
HEAD_DARK = (0x2E, 0x7D, 0x32)        # #2E7D32 - head darker
SNOOT_COLOR = (0x81, 0xC7, 0x84)      # #81C784 - snout highlight
FOOT_COLOR = (0x4C, 0xAF, 0x50)       # #4CAF50
TAIL_COLOR = (0x2E, 0x7D, 0x32)       # #2E7D32

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD ROW 7 (y=7): "...##############...."
    # x=3-12: shell lower (10 wide), x=13-19: neck+head (7 wide)
    if y == 7:
        if x <= 12:
            return MED_SHELL  # Shell lower
        # Neck + head: x=13-19
        if x == 16:  # Eye position - inside head, toward front
            return DARK_SHELL  # Dark dot for eye
        if x >= 18:  # Snout
            return SNOOT_COLOR
        return HEAD_COLOR  # Neck/head body

    # HEAD ROW 8 (y=8): "....###########.####."
    # x=4-14: shell bottom (11 wide), x=15: gap, x=16-19: head bottom (4 wide)
    if y == 8:
        if x <= 14:
            return MED_SHELL  # Shell bottom
        if x == 15:
            return None  # Gap
        # Head bottom: x=16-19 (square/flat)
        if x >= 17:
            return SNOOT_COLOR
        return HEAD_COLOR

    # TAIL: left rear, rows 6-8, x <= 2
    if y >= 6 and y <= 8 and x <= 2:
        return TAIL_COLOR

    # FEET: rows 9-11
    if y >= 9:
        return FOOT_COLOR

    # SHELL - unchanged from V10b
    if y <= 3:
        if 8 <= x <= 12:
            return DARK_SHELL
        elif 7 <= x <= 13:
            return MED_SHELL
        return MED_SHELL
    elif y <= 5:
        if x <= 12:
            return DARK_SHELL if 5 <= x <= 10 else MED_SHELL
        return MED_SHELL if x == 13 else None
    elif y <= 6:
        if x <= 12:
            return MED_SHELL
        return None

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

print("\nColors used:")
for rgb, count in sorted(colors_used.items()):
    print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count} pixels")

print("\nSilhouette:")
for row in SILHOUETTE:
    print(row.replace('.', ' '))