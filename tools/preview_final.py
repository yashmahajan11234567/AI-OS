

#!/usr/bin/env python3
"""Render final IDLE preview to file."""
import os
os.environ['FORCE_COLOR'] = '1'

from aios.cli.mascot.renderer import MascotRenderer, RenderMode
from aios.cli.mascot.animator import SyncMascotAnimator

renderer = MascotRenderer(force_mode=RenderMode.FULL)
animator = SyncMascotAnimator(renderer)

output = animator.render_startup(
    version="0.2.0",
    status="STOPPED",
    health="UNINITIALIZED",
    mode="IDLE",
    autonomy="OFF",
)

with open('final_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)
    f.write('\n')

print("Written to final_output.txt")
