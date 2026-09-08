#!/usr/bin/env python3
"""
Expand current approved 18x15 turtle to 20x17 using outer-layer addition.
Only body/accent/plastron contours expand; eye shape is preserved.
"""
from pathlib import Path
from PIL import Image

SOURCE_DIR = Path("assets/mascot/source")
PALETTE_RGB = {
    (0x69,0x6B,0x3A):'body',(0x6A,0x6B,0x41):'body',(0x6D,0xAF,0x4B):'accent',(0x8C,0xC2,0x4A):'accent',
    (0x8C,0xC2,0x68):'accent',(0xB9,0xB4,0x4E):'plastron',(0xB8,0xB0,0x48):'plastron',(0x18,0x10,0x28):'eye'
}
REF_COLORS = {'body':(0x69,0x6B,0x3A),'plastron':(0xB9,0xB4,0x4E),'accent':(0x8C,0xC2,0x4A),'eye':(0x18,0x10,0x28)}

# Load current approved 18x15
src_img = Image.open(SOURCE_DIR / 'idle.png').convert('RGBA')
CURRENT_W, CURRENT_H = 18, 15
x0 = (src_img.width - CURRENT_W) // 2
y0 = (src_img.height - CURRENT_H) // 2

# Extract categories
cats = [[None]*CURRENT_W for _ in range(CURRENT_H)]
for y in range(CURRENT_H):
    for x in range(CURRENT_W):
        r,g,b,a = src_img.getpixel((x+x0, y+y0))
        if a == 0:
            cats[y][x] = None
        else:
            cats[y][x] = PALETTE_RGB.get((r,g,b), 'body')

# Print baseline
SYM = {None:'.','body':'S','plastron':'P','accent':'A','eye':'E'}
print("CURRENT 18x15 BASELINE:")
for y in range(CURRENT_H):
    s = ''.join(SYM.get(c,'?') for c in cats[y])
    if any(c is not None for c in cats[y]):
        print(f"y={y:2d}: {s}")
print()

# Expand to 20x17: add outer layer around non-eye pixels
EXPANDED_W, EXPANDED_H = 20, 17
expanded = [[None]*EXPANDED_W for _ in range(EXPANDED_H)]

# Place original in center
for y in range(CURRENT_H):
    for x in range(CURRENT_W):
        expanded[y+1][x+1] = cats[y][x]

# Add outer pixels for non-eye neighbors only
for y in range(EXPANDED_H):
    for x in range(EXPANDED_W):
        if expanded[y][x] is not None:
            continue
        visible = []
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny,nx = y+dy, x+dx
            if 0<=ny<EXPANDED_H and 0<=nx<EXPANDED_W:
                c = expanded[ny][nx]
                if c is not None and c != 'eye':
                    visible.append(c)
        if visible:
            expanded[y][x] = max(set(visible), key=visible.count)

print("EXPANDED 20x17 (non-eye outer layer):")
for y in range(EXPANDED_H):
    s = ''.join(SYM.get(c,'?') for c in expanded[y])
    if any(c is not None for c in expanded[y]):
        print(f"y={y:2d}: {s}")
print()

# Place on 32x20 canvas
SRC_W, SRC_H = 32, 20
ox = (SRC_W - EXPANDED_W) // 2
oy = (SRC_H - EXPANDED_H) // 2
output = Image.new('RGBA', (SRC_W, SRC_H), (0,0,0,0))
for y in range(EXPANDED_H):
    for x in range(EXPANDED_W):
        c = expanded[y][x]
        if c and c != 'unknown':
            sx, sy = x+ox, y+oy
            if 0<=sx<SRC_W and 0<=sy<SRC_H:
                output.putpixel((sx,sy), REF_COLORS[c]+(255,))

output.save(SOURCE_DIR / 'idle.png')
print(f"Saved: {SOURCE_DIR / 'idle.png'} ({SRC_W}x{SRC_H})")
print(f"Turtle at ({ox},{oy}), size {EXPANDED_W}x{EXPANDED_H}")
