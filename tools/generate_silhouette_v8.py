#!/usr/bin/env python3
"""
Generate M10-T5 V8 idle.png from binary silhouette blueprint.

SILHOUETTE FIRST - then color.

21 x 13 pixels.
# = TURTLE
. = TRANSPARENT
"""

from PIL import Image

# Binary silhouette from spec
SILHOUETTE = [
    ".....................",  # Row 0
    ".......#####.........",  # Row 1
    ".....#########.......",  # Row 2
    "....###########......",  # Row 3
    "...##############....",  # Row 4
    "..###############.###",  # Row 5
    "..###############.###",  # Row 6
    "...##############.###",  # Row 7
    "....############.....",  # Row 8
    "...##..##..##..##....",  # Row 9
    "...##..##..##..##....",  # Row 10
    "....#...#...#...#....",  # Row 11
    ".....................",  # Row 12
]

# Verify dimensions
assert len(SILHOUETTE) == 13, f"Expected 13 rows, got {len(SILHOUETTE)}"
for i, row in enumerate(SILHOUETTE):
    assert len(row) == 21, f"Row {i}: expected 21 cols, got {len(row)}"

print("Silhouette verified: 21x13")

# Count turtle pixels
turtle_pixels = sum(row.count('#') for row in SILHOUETTE)
print(f"Turtle pixels: {turtle_pixels}")
print(f"Transparent: {21*13 - turtle_pixels}")

# Now create the colored version
# First, let's map the silhouette to color zones
# We'll use the silhouette as a mask and apply colors based on anatomical regions

# Color palette (RGB)
DARK = (0x0D, 0x28, 0x18)       # #0D2818 - main shell/body
MEDIUM = (0x1A, 0x3D, 0x24)      # #1A3D24 - shell shaping
BRIGHT = (0x4C, 0xAF, 0x50)      # #4CAF50 - small accents
LIGHT = (0x81, 0xC7, 0x84)       # #81C784 - lighter accents
PALE = (0xA5, 0xD6, 0xA7)        # #A5D6A7 - pale
VERY_LIGHT = (0xC8, 0xE6, 0xC9)  # #C8E6C9 - eye

def get_color_for_pixel(x, y, is_turtle):
    """Determine color based on anatomical position within silhouette."""
    if not is_turtle:
        return (0, 0, 0)  # Transparent - will handle alpha separately

    # Analyze position
    # Shell center area
    # Head area (right side, rows 1-7)
    # Legs (rows 9-11)
    # Tail (left side, rows 5-7)

    # HEAD region: rightmost columns, upper portion
    if x >= 15 and y <= 7:
        # Neck/head area
        if x >= 18:
            return VERY_LIGHT if (x == 20 and y == 3) else BRIGHT
        return MEDIUM

    # TAIL region: left side, lower-middle
    if x <= 2 and y >= 5 and y <= 7:
        return MEDIUM

    # LEGS region: rows 9-11
    if y >= 9:
        return BRIGHT

    # SHELL: central mass
    # Top of shell gets lighter for dome effect
    if y <= 3:
        return MEDIUM
    # Upper shell
    elif y <= 6:
        # Center of shell gets darker
        if 6 <= x <= 14:
            return DARK
        return MEDIUM
    # Lower shell
    else:
        return MEDIUM

# Create the image
img = Image.new('RGBA', (21, 13), (0, 0, 0, 0))

for y in range(13):
    for x in range(21):
        is_turtle = SILHOUETTE[y][x] == '#'
        color = get_color_for_pixel(x, y, is_turtle)
        if is_turtle:
            r, g, b = color
            img.putpixel((x, y), (r, g, b, 255))

# Save
output_path = "assets/mascot/source/idle.png"
img.save(output_path)
print(f"Saved to {output_path}")

# Create 8x preview
preview = img.resize((21*8, 13*8), Image.NEAREST)
preview_path = "assets/mascot/source/idle_preview_8x.png"
preview.save(preview_path)
print(f"Preview saved to {preview_path}")

# Print color distribution
colors_used = {}
for y in range(13):
    for x in range(21):
        pixel = img.getpixel((x, y))
        if pixel[3] > 0:
            key = (pixel[0], pixel[1], pixel[2])
            colors_used[key] = colors_used.get(key, 0) + 1

print("\nColors used:")
for rgb, count in sorted(colors_used.items()):
    hex_c = '#%02X%02X%02X' % rgb
    print(f"  {hex_c}: {count} pixels")