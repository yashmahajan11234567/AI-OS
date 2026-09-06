#!/usr/bin/env python3
from aios.cli.mascot.assets import MascotAssets
from aios.cli.mascot.halfblock import HalfBlockRasterizer, RenderMode

frame = MascotAssets.get_frame('IDLE', 0)

# Test FULL mode - write to file
rasterizer = HalfBlockRasterizer(RenderMode.FULL)
output = rasterizer.render_frame(frame)
with open('render_test_full.txt', 'w', encoding='utf-8') as f:
    f.write(output)

# Also print pixel grid for debugging
pixels = frame.unpack()
print('Raw pixel grid (21x13):')
for i, row in enumerate(pixels):
    line = ''.join('.' if c == 0 else ('#' if c == 1 else '*') for c in row)
    print(f'{i:2d}: {line}')

print()
print('Half-block pairs (combining rows 0-1, 2-3, 4-5, 6-7, 8-9, 10-11, 12):')
for y in range(0, 13, 2):
    upper = pixels[y] if y < 13 else [0]*21
    lower = pixels[y+1] if y+1 < 13 else [0]*21
    line = ''
    for x in range(21):
        u = upper[x]
        l = lower[x]
        if u != 0 and l != 0:
            if u == 1 and l == 1: line += '#'
            elif u == 2 and l == 2: line += '*'
            elif u == 1 and l == 2: line += '+'
            elif u == 2 and l == 1: line += '='
            else: line += '?'
        elif u != 0:
            if u == 1: line += '^'
            else: line += "'"
        elif l != 0:
            if l == 1: line += 'v'
            else: line += ','
        else:
            line += '.'
    print(f'{y}-{y+1}: {line}')