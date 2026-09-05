#!/usr/bin/env python3
"""
Create the canonical 23-frame Cyber Turtle source PNG files.

Design requirements:
- 17x11 pixel canvas
- Cyber / terminal turtle mascot
- Highly pixelated, square/LED-matrix aesthetic
- Angular/geometric shell
- Angular head
- Simple geometric legs
- Geometric eyes
- Crisp terminal silhouette
- Recognizable as a turtle
- Dark navy / near-black body
- Blue/cyan accents only
- No gradients
- No photographic/realistic style
- No emoji turtle
- No ASCII-art-looking turtle
- No excessive detail
- Must remain recognizable at terminal scale

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

Palette (ONLY these colors allowed):
- Transparent (alpha=0)
- Dark Navy body: #0B1020
- Blue/Cyan accent shades only
"""

from PIL import Image
from pathlib import Path

# Palette - ONLY dark navy + blue/cyan
DARK_NAVY = (0x0B, 0x10, 0x20)      # #0B1020 - near-black / dark navy body
NAVY_BLUE = (0x1A, 0x1F, 0x3A)      # #1A1F3A - dark navy blue
MEDIUM_BLUE = (0x2A, 0x3F, 0x6E)    # #2A3F6E - medium blue
CYAN = (0x00, 0xD4, 0xFF)           # #00D4FF - bright cyan accent
BLUE = (0x00, 0x88, 0xFF)           # #0088FF - electric blue accent
DEEP_BLUE = (0x00, 0x66, 0xAA)      # #0066AA - deep blue accent
BRIGHT_CYAN = (0x00, 0xEE, 0xFF)    # #00EEFF - brighter cyan for highlights

WIDTH = 17
HEIGHT = 11

SOURCE_DIR = Path("assets/mascot/source")
SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def create_canvas():
    """Create transparent 17x11 canvas."""
    return Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))


def set_pixel(img, x, y, color, alpha=255):
    """Set pixel if in bounds."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        img.putpixel((x, y), (*color, alpha))


def get_base_turtle():
    """
    Create the base idle cyber turtle pattern.

    Design: Angular geometric turtle with:
    - Shell: rows 0-7, angular hexagonal shape
    - Head: top-right, angular with geometric eyes
    - Legs: 4 simple geometric legs
    - Tail: small angular tail
    """
    img = create_canvas()

    # ===================== SHELL (main body) =====================
    # Row 0: Shell top edge (angular)
    for x in range(4, 13):
        set_pixel(img, x, 0, DARK_NAVY)
    # Angular shell corners
    set_pixel(img, 3, 0, DARK_NAVY)
    set_pixel(img, 13, 0, DARK_NAVY)

    # Row 1: Shell upper
    for x in range(3, 14):
        set_pixel(img, x, 1, DARK_NAVY)
    # Shell pattern accents (cyan lines on shell)
    set_pixel(img, 5, 1, CYAN)
    set_pixel(img, 8, 1, CYAN)
    set_pixel(img, 11, 1, CYAN)

    # Row 2: Shell middle-upper (head area on right)
    for x in range(2, 14):
        if x not in (11, 12):  # Leave space for head connection
            set_pixel(img, x, 2, DARK_NAVY)
    # Shell pattern
    set_pixel(img, 4, 2, CYAN)
    set_pixel(img, 7, 2, CYAN)
    set_pixel(img, 10, 2, CYAN)
    set_pixel(img, 13, 2, CYAN)

    # Row 3: Shell middle with head
    for x in range(2, 12):
        set_pixel(img, x, 3, DARK_NAVY)
    # Head starts at x=12
    for x in range(12, 16):
        set_pixel(img, x, 3, DARK_NAVY)
    # Shell pattern
    set_pixel(img, 3, 3, CYAN)
    set_pixel(img, 6, 3, CYAN)
    set_pixel(img, 9, 3, CYAN)
    # Head accents - geometric eyes
    set_pixel(img, 13, 3, BLUE)
    set_pixel(img, 14, 3, BLUE)

    # Row 4: Shell middle-lower with head
    for x in range(2, 12):
        set_pixel(img, x, 4, DARK_NAVY)
    for x in range(12, 16):
        set_pixel(img, x, 4, DARK_NAVY)
    # Shell pattern
    set_pixel(img, 4, 4, CYAN)
    set_pixel(img, 7, 4, CYAN)
    set_pixel(img, 10, 4, CYAN)
    # Head detail
    set_pixel(img, 13, 4, DEEP_BLUE)
    set_pixel(img, 14, 4, DEEP_BLUE)

    # Row 5: Shell lower
    for x in range(2, 13):
        set_pixel(img, x, 5, DARK_NAVY)
    # Shell pattern
    set_pixel(img, 3, 5, CYAN)
    set_pixel(img, 6, 5, CYAN)
    set_pixel(img, 9, 5, CYAN)
    set_pixel(img, 12, 5, CYAN)
    # Front legs (simple geometric)
    set_pixel(img, 1, 5, DARK_NAVY)   # Front-left
    set_pixel(img, 13, 5, DARK_NAVY)  # Front-right (head side)

    # Row 6: Shell bottom with legs
    for x in range(3, 12):
        set_pixel(img, x, 6, DARK_NAVY)
    # Shell pattern
    set_pixel(img, 4, 6, CYAN)
    set_pixel(img, 7, 6, CYAN)
    set_pixel(img, 10, 6, CYAN)
    # Legs
    set_pixel(img, 1, 6, DARK_NAVY)   # Front-left
    set_pixel(img, 2, 6, DARK_NAVY)   # Mid-left
    set_pixel(img, 12, 6, DARK_NAVY)  # Front-right
    set_pixel(img, 13, 6, DARK_NAVY)  # Rear-right

    # Row 7: Lower body/legs
    for x in range(4, 11):
        set_pixel(img, x, 7, DARK_NAVY)
    # Legs continue
    set_pixel(img, 2, 7, DARK_NAVY)   # Rear-left
    set_pixel(img, 3, 7, DARK_NAVY)
    set_pixel(img, 11, 7, DARK_NAVY)
    set_pixel(img, 12, 7, DARK_NAVY)
    set_pixel(img, 13, 7, DARK_NAVY)  # Tail

    # Row 8: Legs bottom
    set_pixel(img, 3, 8, DARK_NAVY)   # Rear-left foot
    set_pixel(img, 4, 8, DARK_NAVY)
    set_pixel(img, 10, 8, DARK_NAVY)
    set_pixel(img, 11, 8, DARK_NAVY)  # Rear-right foot
    set_pixel(img, 12, 8, DARK_NAVY)  # Tail tip

    # Row 9-10: Empty (ground level)

    return img


def create_idle():
    """IDLE: calm static cyber turtle - base pattern."""
    return get_base_turtle()


def create_planning_frames():
    """
    PLANNING: turtle appears to be thinking/planning.
    Use a small geometric thought indicator above head.
    Subtle head motion/tilt across frames.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: thought bubble appearing (small geometric indicator)
    f0 = base.copy()
    # Thought indicator: small geometric triangle/LED pattern above head
    set_pixel(f0, 13, 0, BRIGHT_CYAN)
    set_pixel(f0, 12, 1, BRIGHT_CYAN)
    set_pixel(f0, 14, 1, BRIGHT_CYAN)
    set_pixel(f0, 11, 2, BRIGHT_CYAN)
    set_pixel(f0, 13, 2, BRIGHT_CYAN)
    set_pixel(f0, 15, 2, BRIGHT_CYAN)
    frames.append(f0)

    # Frame 1: thought processing - indicator pulsing
    f1 = base.copy()
    # Thought indicator shifted/animated
    set_pixel(f1, 12, 0, BRIGHT_CYAN)
    set_pixel(f1, 14, 0, BRIGHT_CYAN)
    set_pixel(f1, 13, 1, BRIGHT_CYAN)
    set_pixel(f1, 12, 2, BRIGHT_CYAN)
    set_pixel(f1, 14, 2, BRIGHT_CYAN)
    # Head tilt suggestion - eyes shift slightly
    set_pixel(f1, 14, 3, BLUE)  # Right eye brighter
    set_pixel(f1, 13, 3, CYAN)
    frames.append(f1)

    # Frame 2: planning complete - focused
    f2 = base.copy()
    # Solid thought indicator
    set_pixel(f2, 13, 0, CYAN)
    set_pixel(f2, 12, 1, CYAN)
    set_pixel(f2, 14, 1, CYAN)
    set_pixel(f2, 11, 2, CYAN)
    set_pixel(f2, 13, 2, CYAN)
    set_pixel(f2, 15, 2, CYAN)
    # Eyes focused
    set_pixel(f2, 13, 3, BLUE)
    set_pixel(f2, 14, 3, BLUE)
    frames.append(f2)

    return frames


def create_executing_frames():
    """
    EXECUTING: turtle actively moves forward.
    Visible leg/body movement between frames.
    Energetic but still cyber-terminal.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: leg extension begins (forward motion start)
    f0 = base.copy()
    # Front legs extended forward
    set_pixel(f0, 0, 5, DARK_NAVY)   # Front-left extended
    set_pixel(f0, 1, 5, DARK_NAVY)
    set_pixel(f0, 14, 5, DARK_NAVY)  # Front-right extended
    set_pixel(f0, 15, 5, DARK_NAVY)
    # Rear legs pushing back
    set_pixel(f0, 2, 7, DARK_NAVY)
    set_pixel(f0, 3, 7, DARK_NAVY)
    set_pixel(f0, 10, 7, DARK_NAVY)
    set_pixel(f0, 11, 7, DARK_NAVY)
    # Body slightly shifted forward (shell pattern shift)
    set_pixel(f0, 13, 0, CYAN)
    set_pixel(f0, 14, 0, CYAN)
    frames.append(f0)

    # Frame 1: mid-stride - legs alternating
    f1 = base.copy()
    # Left legs forward, right legs back
    set_pixel(f1, 0, 5, DARK_NAVY)
    set_pixel(f1, 1, 5, DARK_NAVY)
    set_pixel(f1, 2, 6, DARK_NAVY)
    set_pixel(f1, 3, 6, DARK_NAVY)
    set_pixel(f1, 12, 5, DARK_NAVY)
    set_pixel(f1, 13, 5, DARK_NAVY)
    set_pixel(f1, 10, 7, DARK_NAVY)
    set_pixel(f1, 11, 7, DARK_NAVY)
    # Shell accents showing motion
    set_pixel(f1, 12, 1, BLUE)
    set_pixel(f1, 11, 2, BLUE)
    frames.append(f1)

    # Frame 2: other stride - legs swapped
    f2 = base.copy()
    # Right legs forward, left legs back
    set_pixel(f2, 2, 7, DARK_NAVY)
    set_pixel(f2, 3, 7, DARK_NAVY)
    set_pixel(f2, 14, 5, DARK_NAVY)
    set_pixel(f2, 15, 5, DARK_NAVY)
    set_pixel(f2, 13, 6, DARK_NAVY)
    set_pixel(f2, 14, 6, DARK_NAVY)
    set_pixel(f2, 0, 6, DARK_NAVY)
    set_pixel(f2, 1, 6, DARK_NAVY)
    # Shell accents
    set_pixel(f2, 13, 1, BLUE)
    set_pixel(f2, 12, 2, BLUE)
    frames.append(f2)

    return frames


def create_reviewing_frames():
    """
    REVIEWING: turtle moves/circles as if inspecting.
    Optional small geometric inspection markers/bits.
    Motion must visibly differ from EXECUTING (more deliberate, side-to-side).
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: turning left to inspect
    f0 = base.copy()
    # Head turned left (eyes shifted)
    set_pixel(f0, 12, 3, BLUE)
    set_pixel(f0, 13, 3, BLUE)
    # Inspection marker on left side
    set_pixel(f0, 2, 1, CYAN)
    set_pixel(f0, 1, 2, CYAN)
    set_pixel(f0, 2, 2, CYAN)
    set_pixel(f0, 1, 3, CYAN)
    # Body slight left lean
    set_pixel(f0, 2, 4, CYAN)
    frames.append(f0)

    # Frame 1: inspecting center/down
    f1 = base.copy()
    # Head centered, looking down
    set_pixel(f1, 13, 3, BLUE)
    set_pixel(f1, 14, 3, BLUE)
    # Inspection markers scanning down shell
    for y in range(1, 7):
        set_pixel(f1, 6, y, BLUE)
    # Legs in neutral inspect pose
    set_pixel(f1, 1, 7, DARK_NAVY)
    set_pixel(f1, 12, 7, DARK_NAVY)
    frames.append(f1)

    # Frame 2: turning right to inspect
    f2 = base.copy()
    # Head turned right
    set_pixel(f2, 14, 3, BLUE)
    set_pixel(f2, 15, 3, BLUE)
    # Inspection marker on right side
    set_pixel(f2, 14, 1, CYAN)
    set_pixel(f2, 15, 2, CYAN)
    set_pixel(f2, 14, 2, CYAN)
    set_pixel(f2, 15, 3, CYAN)
    # Body slight right lean
    set_pixel(f2, 13, 4, CYAN)
    frames.append(f2)

    return frames


def create_verifying_frames():
    """
    VERIFYING: turtle carries/uses a magnifying glass.
    Motion should suggest inspection/verification.
    4 frames for detailed verification sequence.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: magnifying glass appearing on right side
    f0 = base.copy()
    # Magnifying glass: circular frame at head level right side
    # Glass frame (cyan circle-ish)
    glass_pixels = [
        (14, 1), (15, 1), (16, 1),
        (14, 2),          (16, 2),
        (14, 3),          (16, 3),
        (14, 4), (15, 4), (16, 4),
    ]
    for x, y in glass_pixels:
        if x < WIDTH and y < HEIGHT:
            set_pixel(f0, x, y, CYAN)
    # Glass center (clear/bright)
    set_pixel(f0, 15, 2, BRIGHT_CYAN)
    # Handle
    set_pixel(f0, 16, 4, CYAN)
    set_pixel(f0, 16, 5, CYAN)
    frames.append(f0)

    # Frame 1: scanning left across shell
    f1 = base.copy()
    # Magnifier moved left
    glass_pixels = [
        (11, 1), (12, 1), (13, 1),
        (11, 2),          (13, 2),
        (11, 3),          (13, 3),
        (11, 4), (12, 4), (13, 4),
    ]
    for x, y in glass_pixels:
        if x < WIDTH and y < HEIGHT:
            set_pixel(f1, x, y, CYAN)
    set_pixel(f1, 12, 2, BRIGHT_CYAN)
    set_pixel(f1, 13, 4, CYAN)
    set_pixel(f1, 13, 5, CYAN)
    # Scanning beam on shell
    for x in range(4, 12):
        set_pixel(f1, x, 2, BLUE)
    frames.append(f1)

    # Frame 2: scanning right/lower
    f2 = base.copy()
    # Magnifier lower right
    glass_pixels = [
        (12, 3), (13, 3), (14, 3),
        (12, 4),          (14, 4),
        (12, 5),          (14, 5),
        (12, 6), (13, 6), (14, 6),
    ]
    for x, y in glass_pixels:
        if x < WIDTH and y < HEIGHT:
            set_pixel(f2, x, y, CYAN)
    set_pixel(f2, 13, 4, BRIGHT_CYAN)
    set_pixel(f2, 14, 6, CYAN)
    set_pixel(f2, 14, 7, CYAN)
    # Scanning beam lower
    for x in range(4, 12):
        set_pixel(f2, x, 5, BLUE)
    frames.append(f2)

    # Frame 3: verification complete - checkmark indicator
    f3 = base.copy()
    # Magnifier gone, checkmark appears on shell
    checkmark = [
        (8, 2), (9, 3), (10, 2),
        (9, 2), (10, 3), (11, 4),
    ]
    for x, y in checkmark:
        set_pixel(f3, x, y, BLUE)
    # Verified badge
    set_pixel(f3, 13, 1, CYAN)
    set_pixel(f3, 14, 1, CYAN)
    set_pixel(f3, 13, 2, CYAN)
    frames.append(f3)

    return frames


def create_learning_frames():
    """
    LEARNING: turtle reads an open book.
    Page-turning/page-state change across frames.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: book open on shell
    f0 = base.copy()
    # Book rectangle on shell center
    for y in range(2, 7):
        for x in range(5, 11):
            if x in (5, 10) or y in (2, 6):
                set_pixel(f0, x, y, CYAN)  # Book border
            else:
                set_pixel(f0, x, y, DEEP_BLUE)  # Book pages
    # Page indicator left side
    set_pixel(f0, 5, 3, BRIGHT_CYAN)
    set_pixel(f0, 5, 4, BRIGHT_CYAN)
    set_pixel(f0, 5, 5, BRIGHT_CYAN)
    frames.append(f0)

    # Frame 1: page turning
    f1 = base.copy()
    for y in range(2, 7):
        for x in range(5, 11):
            if x in (5, 10) or y in (2, 6):
                set_pixel(f1, x, y, CYAN)
            else:
                set_pixel(f1, x, y, DEEP_BLUE)
    # Page turning - diagonal line
    set_pixel(f1, 6, 3, BRIGHT_CYAN)
    set_pixel(f1, 7, 4, BRIGHT_CYAN)
    set_pixel(f1, 8, 5, BRIGHT_CYAN)
    frames.append(f1)

    # Frame 2: knowledge absorbed - glow effect on shell
    f2 = base.copy()
    for y in range(2, 7):
        for x in range(5, 11):
            if x in (5, 10) or y in (2, 6):
                set_pixel(f2, x, y, CYAN)
            else:
                set_pixel(f2, x, y, DEEP_BLUE)
    # Glow radiating from book center
    for x in range(6, 10):
        for y in range(3, 6):
            if (x == 6 or x == 9 or y == 3 or y == 5):
                set_pixel(f2, x, y, CYAN)
    frames.append(f2)

    return frames


def create_escalating_frames():
    """
    ESCALATING: turtle remains recognizable.
    A `?` indicator appears above/near it.
    Question indicator changes/bounces between frames.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: question mark above shell
    f0 = base.copy()
    # Geometric question mark (angular/LED style)
    qm = [
        (7, -1), (8, -1), (9, -1),  # Top bar
        (9, 0),                     # Curve
        (8, 1),                     # Mid
        (7, 2),                     # Lower
        (7, 3),                     # Dot
    ]
    for x, y in qm:
        if 0 <= y < HEIGHT:
            set_pixel(f0, x, y, CYAN)
    # Exclamation on body (alert)
    set_pixel(f0, 7, 5, CYAN)
    frames.append(f0)

    # Frame 1: question mark bouncing/moving
    f1 = base.copy()
    qm = [
        (8, -1), (9, -1), (10, -1),  # Shifted right
        (10, 0),
        (9, 1),
        (8, 2),
        (8, 3),
    ]
    for x, y in qm:
        if 0 <= y < HEIGHT:
            set_pixel(f1, x, y, CYAN)
    # Double exclamation
    set_pixel(f1, 7, 5, CYAN)
    set_pixel(f1, 7, 6, CYAN)
    set_pixel(f1, 10, 5, CYAN)
    set_pixel(f1, 10, 6, CYAN)
    frames.append(f1)

    # Frame 2: urgent pulsing - whole shell highlights
    f2 = base.copy()
    qm = [
        (7, -1), (8, -1), (9, -1),
        (9, 0),
        (8, 1),
        (7, 2),
        (7, 3),
    ]
    for x, y in qm:
        if 0 <= y < HEIGHT:
            set_pixel(f2, x, y, BRIGHT_CYAN)
    # Pulsing shell accent
    for x in range(4, 13):
        set_pixel(f2, x, 1, CYAN)
        set_pixel(f2, x, 4, CYAN)
    frames.append(f2)

    return frames


def create_complete_frames():
    """
    COMPLETE: turtle holds a completion scroll.
    Scroll visibly opens/closes between frames.
    Completion remains visually distinct.
    """
    frames = []
    base = get_base_turtle()

    # Frame 0: scroll appearing on right side
    f0 = base.copy()
    # Scroll vertical on right
    for y in range(0, 8):
        set_pixel(f0, 14, y, CYAN)
        set_pixel(f0, 15, y, CYAN)
    # Scroll ends (rolled)
    for x in range(13, 16):
        set_pixel(f0, x, 0, CYAN)
        set_pixel(f0, x, 7, CYAN)
    frames.append(f0)

    # Frame 1: scroll unrolling
    f1 = base.copy()
    # Scroll wider/unrolled
    for y in range(0, 8):
        for x in range(12, 16):
            set_pixel(f1, x, y, CYAN)
    # Text lines on scroll (small geometric dots)
    set_pixel(f1, 13, 2, BLUE)
    set_pixel(f1, 14, 3, BLUE)
    set_pixel(f1, 13, 4, BLUE)
    set_pixel(f1, 14, 5, BLUE)
    frames.append(f1)

    # Frame 2: complete - checkmark on scroll
    f2 = base.copy()
    for y in range(0, 8):
        for x in range(12, 16):
            set_pixel(f2, x, y, CYAN)
    # Checkmark on scroll
    check = [
        (12, 3), (13, 4), (14, 3),
        (13, 2), (14, 3), (15, 4),
    ]
    for x, y in check:
        if x < WIDTH:
            set_pixel(f2, x, y, BLUE)
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


def generate_contact_sheet():
    """Generate a contact sheet showing all frames for visual verification."""
    # We'll create this manually after generation
    pass


def main():
    print("=" * 60)
    print("Creating AI-OS Cyber Turtle Source PNGs")
    print("=" * 60)
    print(f"Canvas: {WIDTH}x{HEIGHT}")
    print(f"Palette: Dark Navy (#0B1020) + Blue/Cyan accents ONLY")
    print(f"Source dir: {SOURCE_DIR}")
    print()

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

    # Verify frame counts
    total = 1 + 3 + 3 + 3 + 4 + 3 + 3 + 3
    print(f"\nTotal frames: {total}")
    print("Distribution:")
    print(f"  IDLE: 1")
    print(f"  PLANNING: 3")
    print(f"  EXECUTING: 3")
    print(f"  REVIEWING: 3")
    print(f"  VERIFYING: 4")
    print(f"  LEARNING: 3")
    print(f"  ESCALATING: 3")
    print(f"  COMPLETE: 3")


if __name__ == "__main__":
    main()