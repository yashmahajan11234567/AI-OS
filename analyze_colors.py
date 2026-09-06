#!/usr/bin/env python3
import os
from PIL import Image

def analyze_png_colors(directory):
    all_colors = {}
    files_analyzed = 0

    for filename in os.listdir(directory):
        if filename.endswith('.png'):
            filepath = os.path.join(directory, filename)
            try:
                with Image.open(filepath) as img:
                    # Convert to RGBA if not already
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')

                    # Get all colors
                    colors = img.getcolors(maxcolors=256)
                    if colors:
                        for count, color in colors:
                            color_key = f"rgba{color}"
                            if color_key not in all_colors:
                                all_colors[color_key] = {'count': 0, 'files': []}
                            all_colors[color_key]['count'] += count
                            all_colors[color_key]['files'].append(filename)
                    files_analyzed += 1

            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print(f"Analyzed {files_analyzed} PNG files")
    print("\nUnique colors found:")
    for color_key, info in sorted(all_colors.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{color_key}: {info['count']} pixels")

    return all_colors

if __name__ == "__main__":
    analyze_png_colors("assets/mascot/source")