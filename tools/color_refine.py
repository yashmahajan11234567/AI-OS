#!/usr/bin/env python3
"""
M10-T5.3 — Add turtle eye only.
Add exactly ONE eye pixel inside the light-green head.
Everything else stays identical.
"""
from PIL import Image

SRC = 'assets/mascot/source/idle.png'

# Current colors
BODY_RGB = (0x69, 0x6B, 0x3A)
PLASTRON_RGB = (0xB9, 0xB4, 0x4E)
ACCENT_RGB = (0x8C, 0xC2, 0x4A)
EYE_RGB = (0x18, 0x10, 0x28)

# Load
img = Image.open(SRC).convert('RGBA')
W, H = img.width, img.height
pixels = img.load()

# === EYE PIXEL ===
# Place inside light-green head, front/right portion
# Head has two lobes at rows 7-8: cols 20-21 and cols 24-25
# Eye goes in right/front lobe at (24, 7)
EYE_POSITION = (24, 7)

# Show BEFORE
SYM = {BODY_RGB: 'S', PLASTRON_RGB: 'P', ACCENT_RGB: 'A', EYE_RGB: 'E'}
print("BEFORE:")
for y in range(H):
    row = ''
    has = False
    for x in range(W):
        r, g, b, a = pixels[x, y]
        if a == 0:
            row += '.'
        else:
            row += SYM.get((r, g, b), '?')
            has = True
    if has:
        print(f"y={y:2d}: {row}")

# Verify eye position is currently accent (light green head)
ex, ey = EYE_POSITION
r, g, b, a = pixels[ex, ey]
assert a == 255, f"Eye position ({ex},{ey}) is transparent"
assert (r, g, b) == ACCENT_RGB, f"Eye position ({ex},{ey}) is {hex(r<<16|g<<8|b)}, not accent"

# Place eye
pixels[ex, ey] = EYE_RGB + (255,)

# Save
img.save(SRC)
print(f"\nEye added at ({ex},{ey}) with color RGB{EYE_RGB}")
print()

print("AFTER:")
for y in range(H):
    row = ''
    has = False
    for x in range(W):
        r, g, b, a = pixels[x, y]
        if a == 0:
            row += '.'
        else:
            row += SYM.get((r, g, b), '?')
            has = True
    if has:
        print(f"y={y:2d}: {row}")

print(f"\nSaved: {SRC}")
print(f"Size: {W}x{H}")
