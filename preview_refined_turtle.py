#!/usr/bin/env python3
"""
Generate large visual preview of refined turtle.
"""

from PIL import Image

# Load and upscale
img = Image.open('assets/mascot/source/idle.png')
scale = 8
preview = img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)

# Save preview
preview.save('refined_turtle_preview_8x.png')
print(f"Preview saved: refined_turtle_preview_8x.png ({preview.width}x{preview.height})")
