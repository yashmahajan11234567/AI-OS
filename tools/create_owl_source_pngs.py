#!/usr/bin/env python3
"""
Create the canonical 23-frame owl source PNG files.

Design requirements:
- 17x11 pixel canvas
- Angular horned owl silhouette
- Recognizable geometric eyes with negative-space gaps
- Dark navy body (#0B1020)
- Cyan/blue accents (#00D4FF, #0088FF)
- State-specific accent details:
  - PLANNING: cap/head planning visual (gold accent #FFD700)
  - EXECUTING: hunter/attack eyes (red accent #FF3344)
  - REVIEWING: flight/drift visual (teal accent #00BFA6)
  - VERIFYING: magnifying-glass / scanning visual (blue accent #00AAFF)
  - LEARNING: book/page visual (green accent #00CC66)
  - ESCALATING: question-mark / escalation visual (yellow accent #FFAA00)
  - COMPLETE: scroll/result visual (light gray accent #E0E0E0)

Frames:
- IDLE: 1 frame
- PLANNING: 3 frames
- EXECUTING: 3 frames
- REVIEWING: 3 frames
- VERIFYING: 4 frames
- LEARNING: 3 frames
- ESCALATING: 3 frames
- COMPLETE: 3 frames
Total: 23 frames
"""

from PIL import Image
from pathlib import Path

# Palette
DARK_NAVY = (0x0B, 0x10, 0x20)      # #0B1020
NAVY_BLUE = (0x1A, 0x1F, 0x3A)      # #1A1F3A
MEDIUM_BLUE = (0x2A, 0x3F, 0x6E)    # #2A3F6E
CYAN = (0x00, 0xD4, 0xFF)           # #00D4FF
BLUE = (0x00, 0x88, 0xFF)           # #0088FF
TEAL = (0x00, 0xBF, 0xA6)           # #00BFA6
BLUE_ACCENT = (0x00, 0xAA, 0xFF)    # #00AAFF
GREEN = (0x00, 0xCC, 0x66)          # #00CC66
GOLD = (0xFF, 0xD7, 0x00)           # #FFD700
RED = (0xFF, 0x33, 0x44)            # #FF3344
YELLOW = (0xFF, 0xAA, 0x00)         # #FFAA00
LIGHT_GRAY = (0xE0, 0xE0, 0xE0)     # #E0E0E0

WIDTH = 17
HEIGHT = 11

SOURCE_DIR = Path("assets/owl/source")
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

def create_canvas():
    """Create transparent 17x11 canvas."""
    return Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))

def set_pixel(img, x, y, color, alpha=255):
    """Set pixel if in bounds."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        img.putpixel((x, y), (*color, alpha))

def get_base_owl():
    """Create the base idle owl pattern (body + eyes)."""
    img = create_canvas()

    # Body silhouette - angular horned owl
    # Row 0: top of head/horns
    for x in range(8, 17):
        set_pixel(img, x, 0, DARK_NAVY)

    # Row 1: upper head
    for x in range(7, 17):
        set_pixel(img, x, 1, DARK_NAVY)
    # Horns - leave gaps at 13, 14, 15 for horn tips
    set_pixel(img, 13, 1, DARK_NAVY)
    set_pixel(img, 14, 1, DARK_NAVY)
    set_pixel(img, 15, 1, DARK_NAVY)

    # Row 2: eye level - geometric eyes with negative space
    for x in range(6, 17):
        if x not in (8, 9, 13, 14):  # Eye gaps
            set_pixel(img, x, 2, DARK_NAVY)
    # Eyes - cyan accents
    set_pixel(img, 8, 2, CYAN)
    set_pixel(img, 9, 2, CYAN)
    set_pixel(img, 13, 2, CYAN)
    set_pixel(img, 14, 2, CYAN)

    # Row 3: below eyes
    for x in range(5, 16):
        set_pixel(img, x, 3, DARK_NAVY)

    # Row 4: chest/body widening
    for x in range(4, 15):
        if x not in (7, 10):
            set_pixel(img, x, 4, DARK_NAVY)
    # Accent details
    set_pixel(img, 7, 4, CYAN)
    set_pixel(img, 10, 4, CYAN)

    # Row 5: body continues
    for x in range(3, 14):
        set_pixel(img, x, 5, DARK_NAVY)

    # Row 6: lower body
    for x in range(2, 14):
        if x not in (6, 7, 8, 9, 10, 11):
            set_pixel(img, x, 6, DARK_NAVY)
    set_pixel(img, 6, 6, CYAN)
    set_pixel(img, 7, 6, CYAN)
    set_pixel(img, 8, 6, CYAN)
    set_pixel(img, 9, 6, CYAN)
    set_pixel(img, 10, 6, CYAN)
    set_pixel(img, 11, 6, CYAN)

    # Row 7: body continues
    for x in range(2, 14):
        set_pixel(img, x, 7, DARK_NAVY)

    # Row 8: lower body with feather detail
    for x in range(3, 14):
        if x not in (6, 7, 8, 9, 10, 11, 12):
            set_pixel(img, x, 8, DARK_NAVY)
    set_pixel(img, 6, 8, CYAN)
    set_pixel(img, 7, 8, CYAN)
    set_pixel(img, 8, 8, CYAN)
    set_pixel(img, 9, 8, CYAN)
    set_pixel(img, 10, 8, CYAN)
    set_pixel(img, 11, 8, CYAN)
    set_pixel(img, 12, 8, CYAN)

    # Row 9: bottom of body
    for x in range(4, 14):
        set_pixel(img, x, 9, DARK_NAVY)

    # Row 10: feet/claws
    # Leave empty (transparent)

    return img

def create_idle():
    """IDLE: calm canonical owl - base pattern."""
    return get_base_owl()

def create_planning_frames():
    """PLANNING: cap/head planning visual - gold thinking cap on frame 0, animated."""
    frames = []
    base = get_base_owl()

    # Frame 0: thinking cap appearing
    f0 = base.copy()
    # Add gold cap on top (row 0-1)
    for x in range(7, 16):
        set_pixel(f0, x, 0, GOLD)
        set_pixel(f0, x, 1, GOLD)
    # Cap tip
    set_pixel(f0, 11, 0, GOLD)
    frames.append(f0)

    # Frame 1: cap with gear/processing
    f1 = base.copy()
    for x in range(7, 16):
        set_pixel(f1, x, 0, GOLD)
        set_pixel(f1, x, 1, GOLD)
    # Rotating gear indicator
    set_pixel(f1, 11, 0, CYAN)
    set_pixel(f1, 10, 1, CYAN)
    set_pixel(f1, 12, 1, CYAN)
    frames.append(f1)

    # Frame 2: cap complete, eyes focused
    f2 = base.copy()
    for x in range(7, 16):
        set_pixel(f2, x, 0, GOLD)
        set_pixel(f2, x, 1, GOLD)
    # Eyes brighter cyan
    set_pixel(f2, 8, 2, BLUE)
    set_pixel(f2, 9, 2, BLUE)
    set_pixel(f2, 13, 2, BLUE)
    set_pixel(f2, 14, 2, BLUE)
    frames.append(f2)

    return frames

def create_executing_frames():
    """EXECUTING: hunter/attack eyes - red accents, aggressive posture."""
    frames = []
    base = get_base_owl()

    # Frame 0: eyes narrowing to red
    f0 = base.copy()
    # Red eyes - hunter mode
    set_pixel(f0, 8, 2, RED)
    set_pixel(f0, 9, 2, RED)
    set_pixel(f0, 13, 2, RED)
    set_pixel(f0, 14, 2, RED)
    # Body tension - slight forward lean (shift body pixels)
    frames.append(f0)

    # Frame 1: striking pose - wings/shoulders back
    f1 = base.copy()
    set_pixel(f1, 8, 2, RED)
    set_pixel(f1, 9, 2, RED)
    set_pixel(f1, 13, 2, RED)
    set_pixel(f1, 14, 2, RED)
    # Shoulder accent flares
    for x in range(4, 7):
        set_pixel(f1, x, 4, RED)
    for x in range(12, 15):
        set_pixel(f1, x, 4, RED)
    frames.append(f1)

    # Frame 2: attack/execution complete - returning
    f2 = base.copy()
    set_pixel(f2, 8, 2, RED)
    set_pixel(f2, 9, 2, RED)
    set_pixel(f2, 13, 2, RED)
    set_pixel(f2, 14, 2, RED)
    # Body settling
    frames.append(f2)

    return frames

def create_reviewing_frames():
    """REVIEWING: flight/drift visual - teal accents, wings spread."""
    frames = []
    base = get_base_owl()

    # Frame 0: wings spreading
    f0 = base.copy()
    # Wing accents teal
    for x in range(3, 6):
        set_pixel(f0, x, 5, TEAL)
        set_pixel(f0, x, 6, TEAL)
    for x in range(12, 15):
        set_pixel(f0, x, 5, TEAL)
        set_pixel(f0, x, 6, TEAL)
    set_pixel(f0, 8, 2, TEAL)
    set_pixel(f0, 9, 2, TEAL)
    set_pixel(f0, 13, 2, TEAL)
    set_pixel(f0, 14, 2, TEAL)
    frames.append(f0)

    # Frame 1: gliding - wings fully spread
    f1 = base.copy()
    for x in range(2, 7):
        set_pixel(f1, x, 4, TEAL)
        set_pixel(f1, x, 5, TEAL)
        set_pixel(f1, x, 6, TEAL)
    for x in range(11, 16):
        set_pixel(f1, x, 4, TEAL)
        set_pixel(f1, x, 5, TEAL)
        set_pixel(f1, x, 6, TEAL)
    set_pixel(f1, 8, 2, TEAL)
    set_pixel(f1, 9, 2, TEAL)
    set_pixel(f1, 13, 2, TEAL)
    set_pixel(f1, 14, 2, TEAL)
    frames.append(f1)

    # Frame 2: wings folding
    f2 = base.copy()
    for x in range(4, 7):
        set_pixel(f2, x, 5, TEAL)
        set_pixel(f2, x, 6, TEAL)
    for x in range(11, 14):
        set_pixel(f2, x, 5, TEAL)
        set_pixel(f2, x, 6, TEAL)
    set_pixel(f2, 8, 2, TEAL)
    set_pixel(f2, 9, 2, TEAL)
    set_pixel(f2, 13, 2, TEAL)
    set_pixel(f2, 14, 2, TEAL)
    frames.append(f2)

    return frames

def create_verifying_frames():
    """VERIFYING: magnifying-glass / scanning visual - blue scanning beam."""
    frames = []
    base = get_base_owl()

    # Frame 0: magnifier appearing
    f0 = base.copy()
    # Magnifying glass on right side
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx*dx + dy*dy <= 4:
                px, py = 14 + dx, 2 + dy
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    set_pixel(f0, px, py, BLUE_ACCENT)
    # Center of magnifier - clear
    set_pixel(f0, 14, 2, CYAN)
    set_pixel(f0, 15, 2, CYAN)
    frames.append(f0)

    # Frame 1: scanning beam left
    f1 = base.copy()
    for x in range(8, 15):
        set_pixel(f1, x, 2, BLUE_ACCENT)
        set_pixel(f1, x, 3, BLUE_ACCENT)
    set_pixel(f1, 8, 2, CYAN)
    set_pixel(f1, 9, 2, CYAN)
    set_pixel(f1, 13, 2, CYAN)
    set_pixel(f1, 14, 2, CYAN)
    frames.append(f1)

    # Frame 2: scanning beam right
    f2 = base.copy()
    for x in range(8, 15):
        set_pixel(f2, x, 4, BLUE_ACCENT)
        set_pixel(f2, x, 5, BLUE_ACCENT)
    set_pixel(f2, 8, 2, CYAN)
    set_pixel(f2, 9, 2, CYAN)
    set_pixel(f2, 13, 2, CYAN)
    set_pixel(f2, 14, 2, CYAN)
    frames.append(f2)

    # Frame 3: verification complete - checkmark
    f3 = base.copy()
    # Green checkmark on chest
    check = [(7, 5), (8, 6), (9, 5), (9, 4), (10, 3), (11, 2)]
    for x, y in check:
        set_pixel(f3, x, y, GREEN)
    set_pixel(f3, 8, 2, CYAN)
    set_pixel(f3, 9, 2, CYAN)
    set_pixel(f3, 13, 2, CYAN)
    set_pixel(f3, 14, 2, CYAN)
    frames.append(f3)

    return frames

def create_learning_frames():
    """LEARNING: book/page visual - green accents, pages turning."""
    frames = []
    base = get_base_owl()

    # Frame 0: book open
    f0 = base.copy()
    # Book on chest area
    for y in range(4, 9):
        for x in range(5, 12):
            if x in (5, 11) or y in (4, 8):
                set_pixel(f0, x, y, GREEN)
            else:
                set_pixel(f0, x, y, LIGHT_GRAY)
    # Page turn indicator
    set_pixel(f0, 7, 5, GREEN)
    set_pixel(f0, 7, 6, GREEN)
    set_pixel(f0, 7, 7, GREEN)
    frames.append(f0)

    # Frame 1: page turning
    f1 = base.copy()
    for y in range(4, 9):
        for x in range(5, 12):
            if x in (5, 11) or y in (4, 8):
                set_pixel(f1, x, y, GREEN)
            else:
                set_pixel(f1, x, y, LIGHT_GRAY)
    # Page turning animation
    set_pixel(f1, 8, 5, CYAN)
    set_pixel(f1, 8, 6, CYAN)
    set_pixel(f1, 8, 7, CYAN)
    frames.append(f1)

    # Frame 2: knowledge absorbed - glow
    f2 = base.copy()
    for y in range(4, 9):
        for x in range(5, 12):
            if x in (5, 11) or y in (4, 8):
                set_pixel(f2, x, y, GREEN)
            else:
                set_pixel(f2, x, y, LIGHT_GRAY)
    # Glow effect
    for x in range(6, 11):
        set_pixel(f2, x, 5, BLUE)
        set_pixel(f2, x, 6, BLUE)
    frames.append(f2)

    return frames

def create_escalating_frames():
    """ESCALATING: question-mark / escalation visual - yellow ! and ? marks."""
    frames = []
    base = get_base_owl()

    # Frame 0: question mark above head
    f0 = base.copy()
    # Yellow question mark
    qm = [(8, 0), (9, 0), (10, 0), (11, 0), (11, 1), (10, 2), (9, 3), (9, 4)]
    for x, y in qm:
        set_pixel(f0, x, y, YELLOW)
    # Exclamation on body
    set_pixel(f0, 7, 4, YELLOW)
    set_pixel(f0, 10, 4, YELLOW)
    frames.append(f0)

    # Frame 1: double exclamation
    f1 = base.copy()
    qm = [(8, 0), (9, 0), (10, 0), (11, 0), (11, 1), (10, 2), (9, 3), (9, 4)]
    for x, y in qm:
        set_pixel(f1, x, y, YELLOW)
    # Double exclamation
    set_pixel(f1, 7, 4, YELLOW)
    set_pixel(f1, 7, 5, YELLOW)
    set_pixel(f1, 10, 4, YELLOW)
    set_pixel(f1, 10, 5, YELLOW)
    frames.append(f1)

    # Frame 2: urgent pulsing
    f2 = base.copy()
    qm = [(8, 0), (9, 0), (10, 0), (11, 0), (11, 1), (10, 2), (9, 3), (9, 4)]
    for x, y in qm:
        set_pixel(f2, x, y, YELLOW)
    # Pulsing body accent
    for x in range(6, 12):
        set_pixel(f2, x, 5, YELLOW)
    frames.append(f2)

    return frames

def create_complete_frames():
    """COMPLETE: scroll/result visual - light gray scroll unrolling."""
    frames = []
    base = get_base_owl()

    # Frame 0: scroll appearing
    f0 = base.copy()
    # Scroll on right side
    for y in range(0, 10):
        set_pixel(f0, 14, y, LIGHT_GRAY)
        set_pixel(f0, 15, y, LIGHT_GRAY)
    # Scroll ends
    for x in range(13, 16):
        set_pixel(f0, x, 0, LIGHT_GRAY)
        set_pixel(f0, x, 9, LIGHT_GRAY)
    frames.append(f0)

    # Frame 1: scroll unrolling
    f1 = base.copy()
    for y in range(0, 10):
        for x in range(12, 16):
            set_pixel(f1, x, y, LIGHT_GRAY)
    frames.append(f1)

    # Frame 2: complete - checkmark on scroll
    f2 = base.copy()
    for y in range(0, 10):
        for x in range(12, 16):
            set_pixel(f2, x, y, LIGHT_GRAY)
    # Checkmark on scroll
    check = [(12, 3), (13, 4), (14, 3), (14, 2), (15, 1), (16, 0)]
    for x, y in check:
        if x < WIDTH:
            set_pixel(f2, x, y, GREEN)
    frames.append(f2)

    return frames

def save_frames(frames, prefix):
    """Save frames as PNG files."""
    paths = []
    for i, frame in enumerate(frames):
        if len(frames) == 1:
            path = SOURCE_DIR / f"{prefix}.png"
        else:
            path = SOURCE_DIR / f"{prefix}_{i}.png"
        frame.save(path)
        paths.append(path)
        print(f"Created: {path}")
    return paths

def main():
    print("=" * 60)
    print("Creating AI-OS Owl Source PNGs")
    print("=" * 60)

    # Create all frames
    print("\nCreating IDLE frame...")
    idle_frames = [create_idle()]
    save_frames(idle_frames, "idle")

    print("\nCreating PLANNING frames...")
    planning_frames = create_planning_frames()
    save_frames(planning_frames, "planning")

    print("\nCreating EXECUTING frames...")
    executing_frames = create_executing_frames()
    save_frames(executing_frames, "executing")

    print("\nCreating REVIEWING frames...")
    reviewing_frames = create_reviewing_frames()
    save_frames(reviewing_frames, "reviewing")

    print("\nCreating VERIFYING frames...")
    verifying_frames = create_verifying_frames()
    save_frames(verifying_frames, "verifying")

    print("\nCreating LEARNING frames...")
    learning_frames = create_learning_frames()
    save_frames(learning_frames, "learning")

    print("\nCreating ESCALATING frames...")
    escalating_frames = create_escalating_frames()
    save_frames(escalating_frames, "escalating")

    print("\nCreating COMPLETE frames...")
    complete_frames = create_complete_frames()
    save_frames(complete_frames, "complete")

    print("\n" + "=" * 60)
    print("All 23 source PNG frames created!")
    print("=" * 60)

if __name__ == "__main__":
    main()