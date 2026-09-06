#!/usr/bin/env python3
"""
Create a contact sheet showing all 23 frames for visual verification.
Upscales each frame for visibility.
"""

from PIL import Image
from pathlib import Path

SOURCE_DIR = Path("assets/mascot/source")
OUTPUT_PATH = Path("assets/mascot/contact_sheet.png")

# State order and frame counts
STATES = [
    ("IDLE", 1),
    ("PLANNING", 3),
    ("EXECUTING", 3),
    ("REVIEWING", 3),
    ("VERIFYING", 4),
    ("LEARNING", 3),
    ("ESCALATING", 3),
    ("COMPLETE", 3),
]

SCALE = 10  # Upscale factor for visibility
PADDING = 5
LABEL_HEIGHT = 20

def load_frame(state_name, frame_idx):
    """Load a frame PNG."""
    if frame_idx == 0 and state_name == "IDLE":
        path = SOURCE_DIR / f"{state_name.lower()}.png"
    else:
        path = SOURCE_DIR / f"{state_name.lower()}_{frame_idx}.png"
    return Image.open(path).convert('RGBA')

def create_contact_sheet():
    # Calculate dimensions
    max_frames = max(count for _, count in STATES)
    sheet_width = max_frames * (21 * SCALE + PADDING) + PADDING
    sheet_height = len(STATES) * (13 * SCALE + PADDING + LABEL_HEIGHT) + PADDING

    sheet = Image.new('RGBA', (sheet_width, sheet_height), (0x1a, 0x1a, 0x2e, 255))  # Dark terminal bg

    y_offset = PADDING

    for state_name, frame_count in STATES:
        x_offset = PADDING

        # Draw state label
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("consola.ttf", 14)
        except:
            font = ImageFont.load_default()
        draw.text((x_offset, y_offset), state_name, fill=(0x81, 0xc7, 0x84, 255), font=font)

        y_offset += LABEL_HEIGHT

        for frame_idx in range(frame_count):
            frame = load_frame(state_name, frame_idx)
            # Upscale with nearest neighbor (pixel art)
            frame_scaled = frame.resize((21 * SCALE, 13 * SCALE), Image.NEAREST)
            sheet.paste(frame_scaled, (x_offset, y_offset), frame_scaled)
            x_offset += 21 * SCALE + PADDING

        y_offset += 13 * SCALE + PADDING

    sheet.save(OUTPUT_PATH)
    print(f"Contact sheet saved to: {OUTPUT_PATH}")
    print(f"Dimensions: {sheet.size}")

if __name__ == "__main__":
    create_contact_sheet()