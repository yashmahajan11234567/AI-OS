#!/usr/bin/env python3
"""Direct nearest-neighbor expansion: 18x15 -> 20x17."""
from PIL import Image
import numpy as np
from collections import Counter

PALETTE = {
    (0x23,0x5D,0x2D):'body',(0x0D,0x28,0x18):'body',(0x1A,0x3D,0x24):'body',(0x2E,0x7D,0x32):'body',
    (0x69,0x6B,0x3A):'body',(0x6A,0x6B,0x41):'body',(0x6D,0xAF,0x4B):'accent',(0x8C,0xC2,0x4A):'accent',
    (0x8C,0xC2,0x68):'accent',(0x75,0xBE,0x52):'accent',(0x4C,0xAF,0x50):'accent',(0x81,0xC7,0x84):'accent',
    (0xA5,0xD6,0xA7):'accent',(0xC8,0xE6,0xC9):'accent',(0x8E,0xA7,0x42):'accent',(0xBA,0xB6,0x4B):'plastron',
    (0xB9,0xB5,0x4A):'plastron',(0xB9,0xB4,0x4E):'plastron',(0xBA,0xB5,0x4F):'plastron',(0xB8,0xB0,0x48):'plastron',
    (0x18,0x10,0x28):'eye',(0,0,0):'eye'
}
REF_COLORS = {'body':(0x69,0x6B,0x3A),'plastron':(0xB9,0xB4,0x4E),'accent':(0x8C,0xC2,0x4A),'eye':(0x18,0x10,0x28)}
BG_RGB = (25,25,25)

img = Image.open('tools/turtle_pixel.png').convert('RGB')
arr = np.array(img, dtype=np.float32)
H_ref, W_ref = arr.shape[:2]

CURRENT_W, CURRENT_H = 18, 15
SCALE = 38
off_x = (W_ref - CURRENT_W * SCALE) // 2
off_y = (H_ref - CURRENT_H * SCALE) // 2

def nearest_palette(r,g,b):
    best_cat, best_dist = None, float('inf')
    for (pr,pg,pb), cat in PALETTE.items():
        d = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
        if d < best_dist:
            best_dist = d
            best_cat = cat
    return best_cat if best_dist < 4000 else None

# Extract current 18x15
current_pixels = []
for ty in range(CURRENT_H):
    row = []
    for tx in range(CURRENT_W):
        x0 = off_x + tx*SCALE
        y0 = off_y + ty*SCALE
        colors = []
        for y in range(y0, min(y0+SCALE, H_ref)):
            for x in range(x0, min(x0+SCALE, W_ref)):
                r,g,b = arr[y,x]
                if abs(r-BG_RGB[0])>8 or abs(g-BG_RGB[1])>8 or abs(b-BG_RGB[2])>8:
                    colors.append((r,g,b))
        if not colors:
            row.append(None)
        else:
            mode = Counter(colors).most_common(1)[0][0]
            row.append(nearest_palette(*mode))
    current_pixels.append(row)

# Nearest-neighbor upscale 18x15 -> 20x17
EXPANDED_W, EXPANDED_H = 20, 17
expanded_pixels = [[None] * EXPANDED_W for _ in range(EXPANDED_H)]

for y in range(EXPANDED_H):
    src_y = int(y * CURRENT_H / EXPANDED_H)
    src_y = min(src_y, CURRENT_H - 1)
    for x in range(EXPANDED_W):
        src_x = int(x * CURRENT_W / EXPANDED_W)
        src_x = min(src_x, CURRENT_W - 1)
        expanded_pixels[y][x] = current_pixels[src_y][src_x]

SYM = {None:'.','body':'S','plastron':'P','accent':'A','eye':'E'}
print('CURRENT 18x15:')
for y in range(CURRENT_H):
    s = ''.join(SYM.get(c,'?') for c in current_pixels[y])
    if any(c is not None for c in current_pixels[y]):
        print(f'y={y:2d}: {s}')
print()
print('EXPANDED 20x17 (nearest-neighbor):')
for y in range(EXPANDED_H):
    s = ''.join(SYM.get(c,'?') for c in expanded_pixels[y])
    if any(c is not None for c in expanded_pixels[y]):
        print(f'y={y:2d}: {s}')

# Place on 32x20 canvas
W, H = 32, 20
offset_x = (W - EXPANDED_W) // 2  # 6
offset_y = (H - EXPANDED_H) // 2  # 1
output = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for ty in range(EXPANDED_H):
    for tx in range(EXPANDED_W):
        cat = expanded_pixels[ty][tx]
        if cat and cat != 'unknown':
            sx = tx + offset_x
            sy = ty + offset_y
            if 0 <= sx < W and 0 <= sy < H:
                output.putpixel((sx, sy), REF_COLORS[cat] + (255,))

output.save('assets/mascot/source/idle.png')
print(f'\nSaved 32x20 source with 20x17 turtle at ({offset_x},{offset_y})')
