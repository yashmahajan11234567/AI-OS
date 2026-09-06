#!/usr/bin/env python3
import os
from PIL import Image

def audit_palette(directory):
    """Comprehensive palette audit of all PNG files."""
    all_colors = {}
    files_analyzed = 0

    for filename in sorted(os.listdir(directory)):
        if filename.endswith('.png'):
            filepath = os.path.join(directory, filename)
            try:
                with Image.open(filepath) as img:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')

                    colors = img.getcolors(maxcolors=256)
                    if colors:
                        for count, color in colors:
                            color_key = f"rgba{color}"
                            if color_key not in all_colors:
                                all_colors[color_key] = {'count': 0, 'files': set()}
                            all_colors[color_key]['count'] += count
                            all_colors[color_key]['files'].add(filename)
                    files_analyzed += 1

            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print(f"PALETTE AUDIT - Analyzed {files_analyzed} PNG files")
    print("=" * 50)

    # Define approved colors
    TRANSPARENT = (0, 0, 0, 0)
    DARK_NAVY_BODY = (11, 16, 32, 255)  # #0B1020

    # Approved blue/cyan family
    APPROVED_ACCENTS = {
        (0, 212, 255, 255): "#00D4FF",
        (0, 136, 255, 255): "#0088FF",
        (0, 102, 170, 255): "#0066AA",
        (0, 238, 255, 255): "#00EEFF"
    }

    print("\nCOLOR ANALYSIS:")
    print("-" * 30)

    transparent_count = 0
    body_count = 0
    accent_count = 0
    other_count = 0

    for color_key, info in sorted(all_colors.items(), key=lambda x: x[1]['count'], reverse=True):
        # Parse RGBA values from string like "rgba(11, 16, 32, 255)"
        rgba_str = color_key[5:-1]  # Remove 'rgba(' and ')'
        rgba_vals = tuple(int(x.strip()) for x in rgba_str.split(','))

        count = info['count']

        if rgba_vals == TRANSPARENT:
            print(f"{color_key}: {count} pixels (TRANSPARENT) PASS")
            transparent_count += count
        elif rgba_vals == DARK_NAVY_BODY:
            print(f"{color_key}: {count} pixels (DARK NAVY BODY #0B1020) PASS")
            body_count += count
        elif rgba_vals in APPROVED_ACCENTS:
            hex_val = APPROVED_ACCENTS[rgba_vals]
            print(f"{color_key}: {count} pixels (APPROVED ACCENT {hex_val}) PASS")
            accent_count += count
        else:
            print(f"{color_key}: {count} pixels (UNAPPROVED COLOR) FAIL")
            other_count += count

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Transparent pixels: {transparent_count}")
    print(f"Body pixels (#0B1020): {body_count}")
    print(f"Accent pixels: {accent_count}")
    print(f"Other/unapproved pixels: {other_count}")

    # Check for problematic colors mentioned in requirements
    PROBLEMATIC_COLORS = {
        (0, 191, 166, 255): "#00BFA6 (teal/green)",
        (255, 0, 0, 255): "#FF0000 (red)",
        (0, 255, 0, 255): "#00FF00 (green)",
        (255, 255, 0, 255): "#FFFF00 (yellow)",
        (255, 165, 0, 255): "#FFA500 (orange)",
        (128, 128, 128, 255): "#808080 (gray)",
        (255, 255, 255, 255): "#FFFFFF (white)",
        (128, 0, 128, 255): "#800080 (purple)",
        (255, 192, 203, 255): "#FFC0CB (pink)",
        (139, 69, 19, 255): "#8B4513 (brown)"
    }

    print("\nPROBLEMATIC COLOR CHECK:")
    print("-" * 25)
    problematic_found = False
    for rgb, description in PROBLEMATIC_COLORS.items():
        rgba = (*rgb, 255)
        color_key = f"rgba{rgba}"
        if color_key in all_colors:
            count = all_colors[color_key]['count']
            print(f"FOUND {description}: {count} pixels FAIL")
            problematic_found = True
        else:
            print(f"NOT FOUND {description} PASS")

    if not problematic_found and other_count == 0:
        print("\nPALETTE AUDIT RESULT: PASS")
        print("   - Only transparent, #0B1020 body, and blue/cyan accents found")
        print("   - No teal/green (#00BFA6) or other unauthorized colors")
        return "PASS"
    else:
        print("\nPALETTE AUDIT RESULT: FAIL")
        print("   - Unauthorized colors detected")
        return "FAIL"

if __name__ == "__main__":
    result = audit_palette("assets/mascot/source")
    print(f"\nFINAL RESULT: {result}")