


#!/usr/bin/env python3
"""Analyze turtle_primary.png to extract exact pixel positions."""
from PIL import Image
import numpy as np

img = Image.open('turtle/turtle_primary.png')
img_rgb = img.convert('RGB')
arr = np.array(img_rgb)

# Find non-black pixels
mask = np.any(arr > 20, axis=-1)
ys, xs = np.where(mask)

print(f"Image size: {img.size}")
print(f"Non-black pixels: {len(xs)}")
print(f"Bounds: x=[{xs.min()}, {xs.max()}], y=[{ys.min()}, {ys.max()}]")
print(f"Turtle size: {xs.max()-xs.min()+1} x {ys.max()-ys.min()+1}")

# Print unique colors
unique_colors = np.unique(arr.reshape(-1, 3), axis=0)
print(f"\nUnique colors ({len(unique_colors)}):")
for color in unique_colors:
    if np.any(color > 20):
        hex_color = '#{:02X}{:02X}{:02X}'.format(*color)
        print(f"  RGB{tuple(color)} = {hex_color}")

# Print turtle grid
print("\nTurtle pixel grid (#=filled, .=empty):")
for y in range(ys.min(), ys.max() + 1):
    row = ''
    for x in range(xs.min(), xs.max() + 1):
        if mask[y, x]:
            row += '#'
        else:
            row += '.'
    print(f"  {row}")
