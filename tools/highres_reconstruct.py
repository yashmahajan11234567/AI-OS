#!/usr/bin/env python3
"""
Higher-resolution reconstruction: extract from reference at correct scale,
then upscale to 20x17 on 32x20 source.
"""
from PIL import Image
import numpy as np
from collections import Counter

PALETTE = {
    (0x23,0x5D,0x2D):'body',(0x0D,0x28,0x18):'body',(0x1A,0x3D,0x24):'body',(0x2E,0x7D,0x32):'body',
    (0x69,0x6B,0x3A):'body',(0x6A,0x6B,0x41):'body',(0x6D,0xAF,0x4B):'accent',(0x8C,0xC2,0x4A):'accent',
    (0x8C,0xC2,0x68):'accent',(0x75,0xBE,0x52):'accent',(0x4C,0xAF,0x50):'accent',(0x81,0xC7,0x84):'accent',
    (0xA5,0xD6,0xA7):'accent',(0xC8,0xE6,0xC9):'accent',(0x8E,0xA7,0x42):'accent',(0xBA,0xB6,0x4B):'plastron',
    (0xB9,0xB5,0x4A):'plastron',(0xB9,0xB4,0x4E):'plastron',(0xBA,0xB5,0x4F):'plastron',(0xB8,0xB0,0x48):'plastron',
    (0x18,0x10,0x28):'eye'
}
REF_COLORS = {'body':(0x69,0x6B,0x3A),'plastron':(0xB9,0xB4,0x4E),'accent':(0x8C,0xC2,0x4A),'eye':(0x18,0x10,0x28)}
BG_RGB = (25,25,25)
BG_THRESHOLD = 35
SYM = {None:'.','body':'S','plastron':'P','accent':'A','eye':'E'}

def nearest_palette(r,g,b):
    # Background check: near BG_RGB or very dark neutral pixels
    if abs(r-BG_RGB[0])<=BG_THRESHOLD and abs(g-BG_RGB[1])<=BG_THRESHOLD and abs(b-BG_RGB[2])<=BG_THRESHOLD:
        return None
    best_cat, best_dist = None, float('inf')
    for (pr,pg,pb), cat in PALETTE.items():
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < best_dist:
            best_dist = d
            best_cat = cat
    return best_cat if best_dist < 4000 else None

img = Image.open('tools/turtle_pixel.png').convert('RGB')
arr = np.array(img, dtype=np.float32)
H_ref, W_ref = arr.shape[:2]

# Extract at 2x working resolution: 32x26
WORK_W, WORK_H = 32, 26
SCALE = 19
off_x = (W_ref - WORK_W * SCALE) // 2  # 3
off_y = (H_ref - WORK_H * SCALE) // 2  # 2

print(f"Reference: {W_ref}x{H_ref}")
print(f"Working resolution: {WORK_W}x{WORK_H}")
print(f"Cell size: {SCALE}px, offset: ({off_x},{off_y})")

work_pixels = []
for ty in range(WORK_H):
    row = []
    for tx in range(WORK_W):
        x0 = off_x + tx * SCALE
        y0 = off_y + ty * SCALE
        x1 = min(x0 + SCALE, W_ref)
        y1 = min(y0 + SCALE, H_ref)

        colors = []
        for y in range(y0, y1):
            for x in range(x0, x1):
                r, g, b = arr[y, x]
                if abs(r-BG_RGB[0])>8 or abs(g-BG_RGB[1])>8 or abs(b-BG_RGB[2])>8:
                    colors.append((r,g,b))

        if not colors:
            row.append(None)
        else:
            mode = Counter(colors).most_common(1)[0][0]
            row.append(nearest_palette(*mode))
            if row[-1] == 'eye':
                row[-1] = None
    work_pixels.append(row)

print("\nHIGH-RES 32x26:")
for y in range(WORK_H):
    s = ''.join(SYM.get(c,'?') for c in work_pixels[y])
    if any(c is not None for c in work_pixels[y]):
        print(f"y={y:2d}: {s}")

# Crop vertically to fit 32x20
SRC_W, SRC_H = 32, 20
crop = (WORK_H - SRC_H) // 2
output = Image.new('RGBA', (SRC_W, SRC_H), (0,0,0,0))
for y in range(SRC_H):
    for x in range(SRC_W):
        cat = work_pixels[y+crop][x]
        if cat and cat != 'unknown' and cat != 'eye':
            output.putpixel((x,y), REF_COLORS[cat] + (255,))

output.save('assets/mascot/source/idle.png')
print(f"\nSaved: assets/mascot/source/idle.png ({SRC_W}x{SRC_H})")
print(f"       Cropped from 32x26 to 32x20")

# Show bounding box
rgba = output.convert('RGBA')
min_x, min_y = SRC_W, SRC_H
max_x, max_y = 0, 0
for y in range(SRC_H):
    for x in range(SRC_W):
        if rgba.getpixel((x,y))[3] > 0:
            min_x = min(min_x, x); min_y = min(min_y, y)
            max_x = max(max_x, x); max_y = max(max_y, y)
print(f"       Bounding box: ({min_x},{min_y}) to ({max_x},{max_y})")
print(f"       Bounding size: {max_x-min_x+1}x{max_y-min_y+1}")
