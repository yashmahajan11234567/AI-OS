#!/usr/bin/env python3
"""
Upscale all mascot sprites from 21x13 to 50x30.

Scales 21x13 → 50x30 using nearest-neighbor with slight smoothing
to preserve pixel-art look while matching the new IDLE size.
"""

from PIL import Image, ImageDraw
import os

# Target dimensions
TARGET_WIDTH = 50
TARGET_HEIGHT = 30

# Source directory
SOURCE_DIR = "assets/mascot/source"

# States to upscale (all except idle which is already 50x30)
states = [
    "planning_0.png",
    "planning_1.png",
    "planning_2.png",
    "executing_0.png",
    "executing_1.png",
    "executing_2.png",
    "reviewing_0.png",
    "reviewing_1.png",
    "reviewing_2.png",
    "verifying_0.png",
    "verifying_1.png",
    "verifying_2.png",
    "verifying_3.png",
    "learning_0.png",
    "learning_1.png",
    "learning_2.png",
    "escalating_0.png",
    "escalating_1.png",
    "escalating_2.png",
    "complete_0.png",
    "complete_1.png",
    "complete_2.png",
]

print(f"Upscaling {len(states)} sprites from 21x13 to {TARGET_WIDTH}x{TARGET_HEIGHT}...")

for filename in states:
    src_path = os.path.join(SOURCE_DIR, filename)

    if not os.path.exists(src_path):
        print(f"  SKIP: {filename} (not found)")
        continue

    # Load source
    img = Image.open(src_path).convert('RGBA')

    if img.size == (TARGET_WIDTH, TARGET_HEIGHT):
        print(f"  SKIP: {filename} (already {TARGET_WIDTH}x{TARGET_HEIGHT})")
        continue

    # Scale using NEAREST to preserve hard pixel edges
    # Scale factor: 50/21 ≈ 2.38x, 30/13 ≈ 2.31x
    scaled = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.NEAREST)

    # Save back
    scaled.save(src_path)
    print(f"  OK: {filename} ({img.size[0]}x{img.size[1]} -> {TARGET_WIDTH}x{TARGET_HEIGHT})")

print("\nUpscale complete!")
