#!/usr/bin/env python3
"""
Create refined turtle pixel-art sprite for AI-OS mascot.

Key improvements:
- Smaller head (5x4), clearly separated from shell
- Rounded shell dome
- Four distinct legs
- Small tail
- Narrower plastron
"""

from PIL import Image, ImageDraw

# Color palette (RGBA)
SHELL_DARK = (0x1B, 0x57, 0x22, 255)    # #1B5722
SHELL_MID = (0x26, 0x6B, 0x2D, 255)     # #266B2D
SHELL_LIGHT = (0x3E, 0x88, 0x35, 255)   # #3E8835
ACCENT = (0x5C, 0xC0, 0x47, 255)        # #5CC047
PLASTRON = (0xB8, 0xB0, 0x48, 255)      # #B8B048
EYE = (0x18, 0x10, 0x28, 255)           # #181028
TRANSPARENT = (0, 0, 0, 0)

WIDTH = 50
HEIGHT = 30

img = Image.new('RGBA', (WIDTH, HEIGHT), TRANSPARENT)
draw = ImageDraw.Draw(img)

def set_pixel(x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        draw.point((x, y), color)

def fill_rect(x1, y1, x2, y2, color):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            set_pixel(x, y, color)

# ============================================
# SHELL - Rounded dome, dominant feature
# ============================================
# Center at x=16, width 27, dome top at y=6

shell_cx = 16
shell_top = 6
shell_bottom = 18
shell_half_width = 13  # Full width = 27

# Draw shell with dome curve
for y in range(shell_top, shell_bottom + 1):
    if y <= shell_top + 2:
        # Dome curve - expands from point
        width = max(1, int(shell_half_width * 2 * ((y - shell_top) / 3)))
    else:
        # Full width
        width = shell_half_width * 2

    left = shell_cx - width // 2
    right = shell_cx + width // 2

    if right <= left:
        continue

    for x in range(left, right + 1):
        # Color based on position
        dist_from_center = abs(x - shell_cx) / max(1, width // 2)

        if y <= shell_top + 1:
            color = SHELL_LIGHT
        elif y >= shell_bottom - 1:
            color = SHELL_DARK
        elif dist_from_center < 0.3:
            color = SHELL_MID
        else:
            color = SHELL_DARK
        set_pixel(x, y, color)

# Shell segmentation - horizontal lines
for seg_y in [10, 13]:
    for x in range(shell_cx - 12, shell_cx + 13):
        set_pixel(x, seg_y, SHELL_DARK)

# Shell edge outline
for y in range(shell_top, shell_bottom + 1):
    if y <= shell_top + 2:
        width = max(1, int(shell_half_width * 2 * ((y - shell_top) / 3)))
    else:
        width = shell_half_width * 2
    left = shell_cx - width // 2
    right = shell_cx + width // 2
    set_pixel(left, y, SHELL_DARK)
    set_pixel(right, y, SHELL_DARK)

# ============================================
# HEAD - Small, protruding RIGHT
# ============================================
# Position: right of shell (shell right edge ~29)
# Size: 5 wide x 4 tall

head_x = 30
head_y = 9
head_w = 5
head_h = 4

for y in range(head_y, head_y + head_h):
    for x in range(head_x, head_x + head_w):
        set_pixel(x, y, ACCENT)

# Eye - small dark spot
set_pixel(head_x + 3, head_y + 1, EYE)
set_pixel(head_x + 4, head_y + 1, EYE)

# ============================================
# TAIL - Small, pointed, LEFT side
# ============================================
# Position: left of shell (shell left edge ~3)
# Size: tapered, ~3 wide, ~4 tall

tail_x = 1
tail_y = 13
for y in range(tail_y, tail_y + 4):
    width = 3 - (y - tail_y)
    if width > 0:
        for x in range(tail_x, tail_x + width):
            set_pixel(x, y, ACCENT)

# ============================================
# LEGS - Four distinct legs
# ============================================
# Below shell, chunky pixel-art style

leg_h = 6
leg_w = 4

# Front-right leg (right side)
for y in range(19, 19 + leg_h):
    for x in range(24, 24 + leg_w):
        set_pixel(x, y, ACCENT)

# Front-left leg
for y in range(19, 19 + leg_h):
    for x in range(18, 18 + leg_w):
        set_pixel(x, y, ACCENT)

# Back-right leg
for y in range(19, 19 + leg_h):
    for x in range(12, 12 + leg_w):
        set_pixel(x, y, ACCENT)

# Back-left leg
for y in range(19, 19 + leg_h):
    for x in range(6, 6 + leg_w):
        set_pixel(x, y, ACCENT)

# ============================================
# PLASTRON - Yellow belly, narrower than shell
# ============================================
# Width: 18 (narrower than shell's 27)

plastron_top = 21
plastron_bottom = 26
plastron_cx = 16
plastron_width = 18

for y in range(plastron_top, plastron_bottom + 1):
    left = plastron_cx - plastron_width // 2
    right = plastron_cx + plastron_width // 2
    for x in range(left, right + 1):
        set_pixel(x, y, PLASTRON)

# Save
img.save('assets/mascot/source/idle.png')
print("Created refined turtle sprite: assets/mascot/source/idle.png")
print(f"Dimensions: {WIDTH}x{HEIGHT}")
print("\nAnatomy:")
print("  Shell: Rounded dome 27x13 at center")
print("  Head: 5x4 protruding right with eye")
print("  Tail: Tapered 3x4 on left")
print("  Legs: 4 legs, each 4x6")
print("  Plastron: 18x6 yellow belly")
