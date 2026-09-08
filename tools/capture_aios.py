



#!/usr/bin/env python3
"""Capture aios startup output to file."""
import os
import sys

# Force full render mode
os.environ['FORCE_COLOR'] = '1'

# Capture output
from io import StringIO
from aios.cli.main import show_startup_screen

# Call show_startup_screen directly
output = show_startup_screen()

# Write to file
with open('aios_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)
    f.write('\n')

print("Output captured to aios_output.txt")
