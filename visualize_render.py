#!/usr/bin/env python3
"""
Visualize the half-block rendering as ASCII art.
"""

from aios.cli.mascot.assets import MascotAssets
from aios.cli.mascot.halfblock import HalfBlockRasterizer, RenderMode, select_halfblock_char

frame = MascotAssets.get_frame('IDLE', 0)
rasterizer = HalfBlockRasterizer(RenderMode.MONOCHROME)
output = rasterizer.render_frame(frame)

# Write to file instead of printing
with open('mono_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)

print("=== MONOCHROME HALF-BLOCK RENDERING (saved to file) ===")
with open('mono_output.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    # Replace Unicode with ASCII for display
    content = content.replace('▀', '^').replace('▄', 'v').replace('█', '#')
    print(content)
print()

# Also create a simplified ASCII version for analysis
pixels = frame.unpack()

print("=== ROW-PAIR ANALYSIS ===")
for y in range(0, 13, 2):
    upper = pixels[y] if y < 13 else [0]*21
    lower = pixels[y+1] if y+1 < 13 else [0]*21

    # Show what half-block chars would be used
    chars = []
    for x in range(21):
        u = upper[x]
        l = lower[x]
        ch = select_halfblock_char(u, l)
        if ch == ' ':
            chars.append('.')
        elif ch == '▀':  # ▀
            chars.append('^')
        elif ch == '▄':  # ▄
            chars.append('v')
        elif ch == '█':  # █
            chars.append('#')
        else:
            chars.append('?')

    # Also show color info
    color_info = []
    for x in range(21):
        u = upper[x]
        l = lower[x]
        if u == 2 and l == 2:
            color_info.append('*')  # accent full
        elif u == 2 or l == 2:
            color_info.append('+')  # accent mixed
        else:
            color_info.append('.')

    print(f"Pair {y}-{y+1}: {' '.join(chars)}")
    print(f"         {' '.join(color_info)}")

print()
print("=== VISUAL INTERPRETATION ===")
print("Each # = half-block character (full, upper, or lower)")
print("Eye should appear as a distinct bright pixel on head")

# Let's also print a "zoomed" view showing the turtle shape
print()
print("=== ZOOMED VIEW (2x horizontal) ===")
for y in range(0, 13, 2):
    upper = pixels[y] if y < 13 else [0]*21
    lower = pixels[y+1] if y+1 < 13 else [0]*21
    line = ''
    for x in range(21):
        u = upper[x]
        l = lower[x]
        if u != 0 and l != 0:
            if u == 2 and l == 2:
                line += 'EE'  # Eye!
            elif u == 2 or l == 2:
                line += 'aa'  # Accent
            else:
                line += '##'  # Body
        elif u != 0:
            if u == 2:
                line += 'a.'  # Upper accent
            else:
                line += '#.'  # Upper body
        elif l != 0:
            if l == 2:
                line += '.a'  # Lower accent
            else:
                line += '.#'  # Lower body
        else:
            line += '..'
    print(f"  {line}")