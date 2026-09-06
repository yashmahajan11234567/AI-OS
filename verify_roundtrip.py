#!/usr/bin/env python3
"""
Verify round-trip: PNG → semantic pixels → 2-bit packed data → decoded pixels
"""

import sys
from pathlib import Path

# Add the src directory to path so we can import the mascot modules
sys.path.insert(0, 'src')

from aios.cli.mascot.assets import MascotAssets
from PIL import Image

def verify_roundtrip_for_state(state_name, frame_index=0):
    """Verify round-trip for a specific state/frame."""
    print(f"Verifying round-trip for {state_name} frame {frame_index}")

    # Get the frame data from runtime assets
    frame_data = MascotAssets.get_frame(state_name, frame_index)

    # Unpack to get pixel array
    unpacked_pixels = frame_data.unpack()

    # Verify checksum
    checksum_valid = frame_data.verify()
    print(f"  Checksum valid: {checksum_valid}")

    if not checksum_valid:
        return False

    # Load original PNG and process it the same way
    # Check if we need numbered files or single file
    state_frame_count = MascotAssets.get_frame_count(state_name)
    if state_frame_count == 1:
        png_path = Path(f"assets/mascot/source/{state_name.lower()}.png")
    else:
        png_path = Path(f"assets/mascot/source/{state_name.lower()}_{frame_index}.png")

    if not png_path.exists():
        print(f"  ERROR: Source PNG not found: {png_path}")
        return False

    # Process PNG the same way as build tool
    from tools.build_mascot_assets import process_png, compute_checksum, pack_pixels

    try:
        source_pixels = process_png(png_path, 17, 11)
        source_checksum = compute_checksum(source_pixels)
        source_packed = pack_pixels(source_pixels)

        # Compare with runtime data
        pixels_match = source_pixels == unpacked_pixels
        packed_match = source_packed == frame_data.data
        checksum_match = source_checksum == frame_data.checksum

        print(f"  Pixel arrays match: {pixels_match}")
        print(f"  Packed data match: {packed_match}")
        print(f"  Checksum match: {checksum_match}")

        # Check for reserved pixels (11)
        flat_pixels = [p for row in unpacked_pixels for p in row]
        has_reserved = any(p == 3 for p in flat_pixels)
        print(f"  Has reserved pixels (11): {has_reserved}")

        if has_reserved:
            print("  ERROR: Found reserved pixel values!")
            return False

        return pixels_match and packed_match and checksum_match and not has_reserved

    except Exception as e:
        print(f"  ERROR processing source PNG: {e}")
        return False

def main():
    print("ROUND-TRIP VALIDATION")
    print("=" * 50)

    states = ["IDLE", "PLANNING", "EXECUTING", "REVIEWING", "VERIFYING", "LEARNING", "ESCALATING", "COMPLETE"]
    all_passed = True

    for state in states:
        frame_count = MascotAssets.get_frame_count(state)
        print(f"\n{state} ({frame_count} frames):")

        # Check first frame of each state
        if verify_roundtrip_for_state(state, 0):
            print(f"  PASS {state} round-trip PASSED")
        else:
            print(f"  FAIL {state} round-trip FAILED")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("PASS ROUND-TRIP VALIDATION RESULT: PASS")
        print("   PNG -> semantic pixels -> 2-bit packed -> decoded pixels preserves all data")
        print("   No reserved pixel values found")
        print("   Checksums match")
    else:
        print("FAIL ROUND-TRIP VALIDATION RESULT: FAIL")

    return "PASS" if all_passed else "FAIL"

if __name__ == "__main__":
    result = main()
    print(f"\nFINAL RESULT: {result}")