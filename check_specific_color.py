#!/usr/bin/env python3
import os
from PIL import Image

def check_for_color(directory, target_color):
    target_rgba = (*target_color, 255)  # Add alpha channel
    found_in_files = []

    for filename in os.listdir(directory):
        if filename.endswith('.png'):
            filepath = os.path.join(directory, filename)
            try:
                with Image.open(filepath) as img:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')

                    # Check if color exists in this image
                    colors = img.getcolors(maxcolors=256)
                    if colors:
                        for count, color in colors:
                            if color == target_rgba:
                                found_in_files.append((filename, count))
                                break

            except Exception as e:
                print(f"Error processing {filename}: {e}")

    return found_in_files

if __name__ == "__main__":
    # Check for the specific color mentioned: #00BFA6
    teal_color = (0, 191, 166)  # #00BFA6 in RGB
    results = check_for_color("assets/mascot/source", teal_color)

    print(f"Checking for color #{teal_color[0]:02X}{teal_color[1]:02X}{teal_color[2]:02X} (teal/green):")
    if results:
        print(f"FOUND in {len(results)} files:")
        for filename, count in results:
            print(f"  {filename}: {count} pixels")
    else:
        print("NOT FOUND - color is not present in source assets")