#!/usr/bin/env python3
"""
Revert ONLY the last eye-addition change.
Remove the single eye pixel at (24,7) and restore the source to the
immediately previous good state (no eye).
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

# Show current state
SYM = {BODY_RGB: 'S', PLASTRON_RGB: 'P', ACCENT_RGB: 'A', EYE_RGB: 'E'}
print("CURRENT STATE:")
for y in range(H):
    row = ''
    has = False
    for x in range(W):
        r, g, b, a = pixels[x, y]
        if a == 255:
            row += SYM.get((r, g, b), '?')
            has = True
        else:
            row += '.'
    if has:
        print(f"y={y:2d}: {row}")

# Remove eye pixel at (24,7) - revert to accent color
EYE_POS = (24, 7)
ex, ey = EYE_POS
r, g, b, a = pixels[ex, ey]
print(f"\nEye pixel at ({ex},{ey}): RGB({r},{g},{b}), alpha={a}")
print(f"Reverting eye pixel to accent color RGB{ACCENT_RGB}")

pixels[ex, ey] = ACCENT_RGB + (255,)

# Save
img.save(SRC)
print(f"\nSaved: {SRC}")
print(f"Size: {W}x{H}")
print("\nREVERTED STATE:")
for y in range(H):
    row = ''
    has = False
    for x in range(W):
        r, g, b, a = pixels[x, y]
        if a == 255:
            row += SYM.get((r, g, b), '?')
            has = True
        else:
            row += '.'
    if has:
        print(f"y={y:2d}: {row}")
