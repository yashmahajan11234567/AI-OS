#!/usr/bin/env python3
"""Side-by-side comparison of current 18x15 vs new 20x17 turtle."""
from PIL import Image
from aios.cli.mascot.assets import MascotAssets
import os

os.environ['FORCE_COLOR'] = '1'

frame = MascotAssets.get_frame('IDLE', 0)
pixels = frame.unpack()
w, h = frame.width, frame.height

sym = {0: '.', 1: 'S', 2: 'A', 3: 'P'}

print("=" * 70)
print("NEW EXPANDED TURTLE - 20x17 on 32x20 canvas")
print("=" * 70)

for y in range(h):
    row = pixels[y]
    count = sum(1 for c in row if c > 0)
    if count > 0:
        print(f"y={y:2d}: " + ''.join(sym.get(c, '?') for c in row))

print("\n" + "=" * 70)
print("DIMENSIONS:", w, "x", h)
print("BYTES:", len(frame.data))
print("CHECKSUM:", frame.checksum)
print("=" * 70)
