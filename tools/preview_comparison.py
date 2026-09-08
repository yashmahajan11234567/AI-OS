#!/usr/bin/env python3
"""Side-by-side pixel comparison for final report."""
from aios.cli.mascot.assets import MascotAssets
from PIL import Image

frame = MascotAssets.get_frame('IDLE', 0)
pixels = frame.unpack()
sym = {0: '.', 1: 'S', 2: 'A', 3: 'P'}

print("=" * 70)
print("NEW RECONSTRUCTED TURTLE - 32x20 source")
print("=" * 70)
for y in range(20):
    row = pixels[y]
    if any(c > 0 for c in row):
        print(f"y={y:2d}: " + "".join(sym.get(c, "?") for c in row))

print("\n" + "=" * 70)
print("DIMENSIONS:", frame.width, "x", frame.height)
print("BYTES:", len(frame.data))
print("=" * 70)
