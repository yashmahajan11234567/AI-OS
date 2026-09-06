#!/usr/bin/env python3
"""
M10-T5 V10b - Half-block separation focus
Shell ends at pixel row 6, head starts at pixel row 7
Output rows: (0,1)->0, (2,3)->1, (4,5)->2, (6,7)->3, (8,9)->4, (10,11)->5, (12)->6

DESIGN:
- Shell dominates pixel rows 0-6 (output rows 0-3)
- Gap at pixel row 6-7 boundary
- Head dominates pixel rows 7-10 (output rows 3-5)
- Feet at pixel rows 9-11
"""

from PIL import Image

# 21x13 silhouette
SILHOUETTE = [
    ".....................",  # 0: empty breathing room
    ".........###.........",  # 1: dome peak          -> pair 0 (row 1)
    ".......#######.......",  # 2: rising             -> pair 1 (row 2)
    ".....###########.....",  # 3: widening           -> pair 1 (row 3)
    "....#############....",  # 4: shell max width    -> pair 2 (row 4)
    "....#############....",  # 5: shell max          -> pair 2 (row 5)
    "....#############....",  # 6: shell END          -> pair 3 upper (row 6)
    "...##########..#####.",  # 7: head starts        -> pair 3 lower (row 7)
    "....#############....",  # 8: shell bottom       -> pair 4 upper (row 8)
    "....##..##..##..##...",  # 9: feet               -> pair 4 lower (row 9)
    "....##..##..##..##...",  # 10: feet              -> pair 5 upper (row 10)
    ".....#...#...#...#...",  # 11: toes              -> pair 5 lower (row 11)
    ".....................",   # 12: empty             -> row 6 (single)
]

# Verify all rows are 21 chars
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)} != 21 - '{row}'"

print("Silhouette verified: 21x13")
print(f"Turtle pixels: {sum(row.count('#') for row in SILHOUETTE)}")

# Green palette
DARK = (0x0D, 0x28, 0x18)       # #0D2818 - shell darkest
MED = (0x1A, 0x3D, 0x24)        # #1A3D24 - shell medium
LIGHT = (0x2E, 0x7D, 0x32)      # #2E7D32 - shell light / head dark
MED2 = (0x4C, 0xAF, 0x50)       # #4CAF50 - head medium / feet
BRIGHT = (0x81, 0xC7, 0x84)     # #81C784 - head bright / snout
EYE = (0xC8, 0xE6, 0xC9)        # #C8E6C9 - eye

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD: pixel rows 7-10, right side (x >= 13)
    if y >= 7 and y <= 10 and x >= 13:
        if y == 7 and x == 17:  # Eye at front of head
            return EYE
        if x >= 18:  # Snout
            return BRIGHT
        return MED2  # Head body

    # TAIL: left rear, rows 6-8, x <= 2
    if y >= 6 and y <= 8 and x <= 2:
        return MED  # Tail color

    # FEET: rows 9-11
    if y >= 9:
        return MED2

    # SHELL: rows 0-8, primarily left/center, ending at x=12
    if y <= 3:
        # Upper dome
        if 8 <= x <= 12:
            return DARK
        elif 7 <= x <= 13:
            return MED
        return MED
    elif y <= 5:
        # Mid shell
        if x <= 12:
            return DARK if 5 <= x <= 10 else MED
        return MED if x == 13 else None
    elif y <= 6:
        # Row 6: shell end
        if x <= 12:
            return MED
        return None  # Gap!
    elif y <= 8:
        # Row 7-8: shell bottom curve
        if x <= 12:
            return MED
        return None

    return MED

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
print("Saved idle.png and idle_preview_8x.png")

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

# Print the silhouette
print("\nSilhouette:")
for row in SILHOUETTE:
    print(row.replace('.', ' '))