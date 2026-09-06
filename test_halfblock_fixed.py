#!/usr/bin/env python3
"""
Test all 9 half-block renderer combinations.
"""

import sys
sys.path.insert(0, 'src')

from aios.cli.mascot.halfblock import (
    select_halfblock_char,
    get_color_for_pixel,
    HalfBlockRasterizer,
    RenderMode,
    PaletteColors
)
from aios.cli.mascot.assets import _FrameData

def test_halfblock_char_selection():
    """Test the half-block character selection logic."""
    print("Testing half-block character selection...")

    # Test cases: (upper, lower, expected_index, description)
    # Expected: 0=space, 1=upper block (▀), 2=lower block (▄), 3=full block (█)
    test_cases = [
        (0, 0, 0, "transparent/transparent"),
        (1, 0, 1, "body/transparent"),
        (0, 1, 2, "transparent/body"),
        (2, 0, 1, "accent/transparent"),
        (0, 2, 2, "transparent/accent"),
        (1, 1, 3, "body/body"),
        (2, 2, 3, "accent/accent"),
        (1, 2, 3, "body/accent"),  # Both pixels present -> full block
        (2, 1, 3, "accent/body"),  # Both pixels present -> full block
    ]

    all_passed = True
    for upper, lower, expected_index, desc in test_cases:
        result = select_halfblock_char(upper, lower)
        # Convert to index for comparison to avoid unicode issues
        if result == " ":
            result_index = 0
        elif result == "▀":
            result_index = 1
        elif result == "▄":
            result_index = 2
        elif result == "█":
            result_index = 3
        else:
            result_index = -1  # unknown

        if result_index == expected_index:
            print(f"  PASS {desc}")
        else:
            print(f"  FAIL {desc}: expected index {expected_index}, got {result_index}")
            all_passed = False

    return all_passed

def test_color_mapping():
    """Test color mapping for pixel codes."""
    print("\nTesting color mapping...")

    palette = PaletteColors()

    # Test cases: (code, expected_has_color, description)
    test_cases = [
        (0, False, "transparent"),
        (1, True, "body"),
        (2, True, "accent"),
        (3, False, "reserved"),
    ]

    all_passed = True
    for code, has_color, desc in test_cases:
        fg, bg = get_color_for_pixel(code, palette)
        has_fg_bg = bool(fg or bg)
        if has_color == has_fg_bg:
            print(f"  PASS {desc}")
        else:
            print(f"  FAIL {desc}: expected color={'yes' if has_color else 'no'}")
            all_passed = False

    return all_passed

def test_rasterizer_modes():
    """Test different render modes."""
    print("\nTesting rasterizer render modes...")

    # Create a simple test frame (2x2 pixels)
    # Packed format: 4 pixels per byte
    # Pixel layout (row-major):
    # [0,0]=transparent(0), [0,1]=body(1)
    # [1,0]=accent(2), [1,1]=transparent(0)
    # Packed: byte = (0<<6)|(1<<4)|(2<<2)|(0) = 0|64|128|0 = 192

    test_frame = _FrameData(
        width=2,
        height=2,
        data=bytes([192]),  # 11000000 binary
        checksum="dummy"
    )

    modes = [RenderMode.FULL, RenderMode.MONOCHROME, RenderMode.NARROW, RenderMode.FALLBACK, RenderMode.JSON]
    all_passed = True

    for mode in modes:
        try:
            rasterizer = HalfBlockRasterizer(mode)
            result = rasterizer.render_frame(test_frame)
            print(f"  PASS {mode.value}: produced output")
        except Exception as e:
            print(f"  FAIL {mode.value}: ERROR - {e}")
            all_passed = False

    return all_passed

def main():
    print("HALF-BLOCK RENDERER COMBINATIONS TEST")
    print("=" * 50)

    test1 = test_halfblock_char_selection()
    test2 = test_color_mapping()
    test3 = test_rasterizer_modes()

    print("\n" + "=" * 50)
    if test1 and test2 and test3:
        print("PASS HALF-BLOCK RENDERER TEST RESULT: PASS")
        print("   All 9 combinations work correctly")
        print("   Character selection, color mapping, and render modes functional")
    else:
        print("FAIL HALF-BLOCK RENDERER TEST RESULT: FAIL")

    return "PASS" if (test1 and test2 and test3) else "FAIL"

if __name__ == "__main__":
    result = main()
    print(f"\nFINAL RESULT: {result}")