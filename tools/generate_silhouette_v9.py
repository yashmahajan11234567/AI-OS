#!/usr/bin/env python3
"""
Generate M10-T5 V9 idle.png - Final anatomical refinement
Key changes from V8:
- More domed shell (rounded top, stepped curved underside)
- Clearly horizontal right-facing head (not vertical antenna)
- Better head/shell separation with visible neck
- Head proportionally larger relative to shell
- Clear turtle feet
"""

from PIL import Image

# V9 Silhouette - each row EXACTLY 21 chars
SILHOUETTE = [
    ".....................",  # 0: 21
    ".........##..........",  # 1: 9+2+10=21 tiny peak
    ".......#######.......",  # 2: 7+7+7=21 rising
    ".....###########.....",  # 3: 5+11+5=21 wider
    "....#############....",  # 4: 4+13+4=21 max width
    "..#############..###.",  # 5: 2+13+2+3+1=21 shell+gap+head
    "..#############..####",  # 6: 2+13+2+4=21 shell+gap+head
    "...############..#...",  # 7: 3+12+2+1+3=21 shell lower+head
    "....#############....",  # 8: 4+13+4=21 shell bottom
    "....##..##..##..##...",  # 9: 4+2+2+2+2+2+2+2+3=21 feet
    "....##..##..##..##...",  # 10: same
    ".....#...#...#...#...",  # 11: 5+1+3+1+3+1+3+1+3=21
    ".....................",   # 12: 21
]

# Verify
assert len(SILHOUETTE) == 13
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: {len(row)}: '{row}'"

print("Silhouette verified: 21x13")
turtle_pixels = sum(row.count('#') for row in SILHOUETTE)
print(f"Turtle pixels: {turtle_pixels}")

print("\nSilhouette:")
for row in SILHOUETTE:
    print(row.replace('.', ' '))

# Color palette
DARK = (0x0D, 0x28, 0x18)       # #0D2818
MEDIUM = (0x1A, 0x3D, 0x24)      # #1A3D24
DARK_GREEN = (0x2E, 0x7D, 0x32)  # #2E7D32
BRIGHT = (0x4C, 0xAF, 0x50)      # #4CAF50
LIGHT = (0x81, 0xC7, 0x84)       # #81C784
PALE = (0xA5, 0xD6, 0xA7)        # #A5D6A7
VERY_LIGHT = (0xC8, 0xE6, 0xC9)  # #C8E6C9 - eye

def get_color(x, y, is_turtle):
    if not is_turtle:
        return None

    # HEAD: right side, rows 5-7, x>=15 (gap at 13-14)
    if y >= 5 and y <= 7 and x >= 15:
        if x == 17 and y == 6:  # Eye
            return VERY_LIGHT
        if x >= 19:  # Snout tip
            return BRIGHT
        if y == 5 and x <= 16:  # Neck (thinner)
            return MEDIUM
        return MEDIUM  # Head

    # TAIL: left side, rows 5-7, x<=2
    if y >= 5 and y <= 7 and x <= 2:
        return MEDIUM

    # FEET: rows 9-11
    if y >= 9:
        return BRIGHT

    # SHELL - DOMED
    if y <= 3:
        # Top dome - center darker
        if 8 <= x <= 12:
            return DARK
        return MEDIUM
    elif y == 4:
        # Upper shell
        if 4 <= x <= 14:
            return DARK_GREEN
        return MEDIUM
    elif y <= 6:
        # Mid shell - ends at x=13
        if x <= 13:
            if 4 <= x <= 12:
                return DARK
            return MEDIUM
        return None
    elif y <= 8:
        # Lower shell stepped
        if x <= 12:
            return MEDIUM
        return None
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