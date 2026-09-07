# M10-T5 READ-ONLY INVESTIGATION REPORT
## AI-OS Mascot Turtle - Reference vs Current Implementation Analysis

**Date**: 2026-09-07
**Status**: READ-ONLY - NO IMPLEMENTATION
**User Instruction**: "DO NOT implement anything yet. STOP after the read-only analysis."

---

## EXECUTIVE SUMMARY

The reference image `C:\Development\AI-OS\image.png` is a **full-resolution illustration (288x120)**, NOT a pixel-art sprite. It cannot be directly converted to the current 21x13 pixel-art format. The turtle shape and colors must be manually recreated as pixel art matching the reference's visual style.

---

## SECTION A: REFERENCE IMAGE ANALYSIS

### A.1 Basic Properties
- **File**: `C:\Development\AI-OS\image.png` (CANONICAL - DO NOT MODIFY)
- **Dimensions**: 288x120 pixels
- **Transparency**: None (fully opaque)
- **Total unique colors**: 3,820
- **Format**: Full illustration with gradients/anti-aliasing

### A.2 Turtle Detection (Opaque Image)
Since the image has no transparency, turtle was detected via background segmentation:
- **Background color range**: RGB(0-5, 12-25, 4-15) - very dark green/black
- **Background pixels**: 28,987 (83.9%)
- **Turtle pixels**: 5,573 (16.1%)
- **Turtle bounding box**: (71, 29) to (203, 116) = **133x88 pixels**

### A.3 Turtle Colors
- **Turtle unique colors**: 3,260 (mostly gradients)
- **Bright pixels (G > 50)**: 5,323 (95.5% of turtle)
- **Yellow pixels (plastron candidate)**: 55 pixels
  - Criteria: R > 150, G > 140, B < 100
  - Very few - likely plastron is mostly in mid-tone range
- **Eye pixels**: 19 pixels
  - Very dark, non-background: R < 20, G < 20, B < 30

### A.4 Key Finding: NOT Pixel-Art
The reference is a **smooth illustration** with:
- Anti-aliased edges
- Gradient shading on shell
- Thousands of color variations
- No hard pixel boundaries

**Conclusion**: This CANNOT be directly downscaled to pixel art. The current 21x13 sprite format requires manual pixel-art creation inspired by the reference, not automated conversion.

---

## SECTION B: CURRENT IMPLEMENTATION ANALYSIS

### B.1 Current Source PNG
- **File**: `assets/mascot/source/idle.png`
- **Dimensions**: 21x13 pixels
- **Transparency**: Yes (192 transparent pixels, 81 opaque)
- **Bounding box**: (4, 1) to (17, 9) = **14x9 pixels**
- **Unique colors**: 6

### B.2 Current Color Palette
```
#181028 - 1 pixel   (eye)
#1B5722 - 17 pixels  (shell dark)
#266B2D - 20 pixels  (shell mid)  ← PRIMARY SHELL
#3E8835 - 5 pixels   (shell light)
#5CC047 - 15 pixels  (accent - head/legs/tail)
#B8B048 - 23 pixels  (plastron yellow)
```

### B.3 Current Turtle Anatomy (21x13)
```
Row 0:  ...............
Row 1:  .....11111.....  (shell top)
Row 2:  ....1111111....  (shell)
Row 3:  ...222211111...  (head + shell)
Row 4:  ..22211111111..  (head + shell + plastron)
Row 5:  .222233333331..  (head + plastron)
Row 6:  ..22222222222..  (head + legs)
Row 7:  ..2........22..  (legs)
Row 8:  ..2..3..3...2..  (legs + plastron)
Row 9:  .....33333.....  (plastron bottom)
Row 10: ...............
Row 11: ...............
Row 12: ...............
```

**Key issues with current turtle**:
1. Shell is only 7 pixels wide (too narrow)
2. Head protrudes only 2 pixels (should be more prominent)
3. Plastron (yellow) is small and disconnected
4. No visible tail
5. No shell segmentation/scutes
6. Overall shape doesn't match reference proportions

---

## SECTION C: PIPELINE ANALYSIS

### C.1 Asset Pipeline
```
Source PNG (21x13)
    ↓
build_mascot_assets.py (classify pixels → semantic codes 0-3)
    ↓
Packed 2-bit raster (4 pixels/byte)
    ↓
assets.py (runtime module)
    ↓
halfblock.py (renderer - pairs of rows → half-block chars)
    ↓
Terminal output (▀▄█ with ANSI colors)
```

### C.2 Semantic Code Mapping
- **Code 0**: Transparent (00)
- **Code 1**: Body/shell (01) → greens #1B5722, #266B2D, #3E8835
- **Code 2**: Accent (10) → green #5CC047 (head/legs/tail)
- **Code 3**: Plastron (11) → yellow #B8B048

### C.3 Geometry Preservation Check
✅ **Source PNG geometry**: Preserved (21x13 canvas, 14x9 turtle bbox)
✅ **Semantic codes**: Preserved (per-pixel classification)
✅ **Pixel coordinates**: Preserved (row-major order)
❌ **Half-block rendering**: Reduces vertical resolution by 2x (13 rows → 7 lines)
❌ **Terminal character aspect**: Characters are ~2:1 height:width, causing distortion

### C.4 Where Geometry is Altered/Lost

#### C.4.1 Half-Block Vertical Compression
- **Input**: 13 rows of pixels
- **Output**: 7 lines of half-block characters
- **Loss**: Pairs of rows are merged, losing vertical detail
- **Impact**: Fine details (shell scutes, eye) may be lost or merged

#### C.4.2 Terminal Character Aspect Ratio
- **Issue**: Terminal characters are roughly twice as tall as wide
- **Result**: 21x13 pixel art appears stretched vertically in terminal
- **Current mitigation**: None - no aspect ratio correction

#### C.4.3 Color Quantization
- **Source**: 6 colors
- **Render**: 5 ANSI colors (3 shell greens, 1 accent, 1 plastron)
- **Impact**: Minimal - source already uses limited palette

---

## SECTION D: COMPARISON - REFERENCE vs CURRENT

### D.1 Reference Visual Characteristics
- **Head**: Large, rounded, protruding right with visible eye
- **Shell**: Large, domed, extends horizontally, brownish-olive (#686838 range)
- **Legs**: Four distinct legs, two visible (front and back)
- **Tail**: Small, pointed, on left side
- **Plastron**: Yellow/light-green, visible underneath
- **Colors**: Shell greens (#5EB749 range), brown/olive (#686838), yellow (#B8B048)
- **Style**: Smooth illustration with gradients

### D.2 Current Implementation Visual Characteristics
- **Head**: Small, 2 pixels wide, green (#5CC047)
- **Shell**: Narrow (7 pixels), dark green (#266B2D)
- **Legs**: Two visible, thin, green (#5CC047)
- **Tail**: Not visible
- **Plastron**: Small disconnected region, yellow (#B8B048)
- **Colors**: Dark shell greens (#1B5722, #266B2D, #3E8835), accent green (#5CC047)
- **Style**: Minimal pixel art

### D.3 Critical Differences
1. **Shell color**: Reference is brownish-olive (#686838), current is dark green (#266B2D)
2. **Shell size**: Reference is large and domed, current is narrow
3. **Head prominence**: Reference has large rounded head, current has small protrusion
4. **Shell detail**: Reference shows segmentation/scutes, current is solid
5. **Overall proportions**: Reference is wider and more balanced

---

## SECTION E: GEOMETRY CORRUPTION POINTS

### E.1 Current halfblock.py Issues

#### E.1.1 Vertical Resolution Loss
```python
# Line 170: Processes pairs of rows
for y in range(0, height, 2):
    upper_row = pixels[y]
    lower_row = pixels[y + 1]
```
**Impact**: Two rows merged into one character. For 13-row sprite, bottom row (row 12) is ignored if height is odd.

#### E.1.2 No Aspect Ratio Correction
```python
# Lines 175-177: Direct pixel-to-char mapping
for x in range(width):
    upper_code = upper_row[x]
    lower_code = lower_row[x]
```
**Impact**: Characters are ~2:1 aspect, but pixels are 1:1, causing vertical stretching.

#### E.1.3 Color Blending in Mixed Pixels
```python
# Lines 191-199: Mixed semantic codes
if upper_code == lower_code:
    fg = upper_fg
    bg = ""
else:
    fg = upper_fg
    bg = lower_bg
```
**Impact**: When upper and lower pixels have different semantic codes, the character uses fg for upper half and bg for lower half. This can create visible seams.

### E.2 Current build_mascot_assets.py Issues

#### E.2.1 Nearest-Neighbor Downscaling Risk
```python
# Line 334: Centered paste (no scaling)
canvas.paste(img, (offset_x, offset_y), img)
```
**Current behavior**: No scaling for 21x13 source. But if reference is used, would need downscaling which loses detail.

#### E.2.2 Palette Mismatch
```python
# Lines 50-70: Color sets
BODY_COLORS = {(0x1B, 0x57, 0x22), ...}  # Dark greens
ACCENT_COLORS = {(0x5C, 0xC0, 0x47), ...}  # Bright green
PLASTRON_COLORS = {(0xB8, 0xB0, 0x48)}  # Yellow
```
**Issue**: Reference uses brownish-olive (#686838) which is NOT in current palette.

---

## SECTION F: MINIMAL IMPLEMENTATION STRATEGY

### F.1 Recommended Approach: Manual Pixel-Art Recreation

**Rationale**: Reference is a smooth illustration, not pixel art. Automated downscaling will fail. Manual recreation preserves pixel-art aesthetic while matching reference anatomy.

### F.2 Steps (DO NOT IMPLEMENT YET)

#### Step 1: Create New Source PNG
- **Dimensions**: 21x13 (keep current format)
- **Style**: Pixel art matching reference anatomy
- **Colors**: Use current palette (6 colors)
- **Anatomy requirements**:
  - Larger shell (11-13 pixels wide, domed top)
  - Prominent head (3-4 pixels, protruding right)
  - Visible tail (2-3 pixels, left side)
  - Shell segmentation (2-3 horizontal lines)
  - Balanced proportions

#### Step 2: Update Color Palette (if needed)
- Add brownish-olive #686838 to BODY_COLORS (for shell)
- Keep existing colors for consistency
- Update build script color sets

#### Step 3: Rebuild Assets
```bash
python tools/build_mascot_assets.py
```

#### Step 4: Verify Tests
```bash
pytest tests/unit/test_mascot_assets.py -v
pytest tests/unit/test_mascot_halfblock.py -v
```

### F.3 Alternative Approach: Increase Resolution

**If 21x13 is too small for desired detail**:
- Increase to 32x20 or 50x20
- Update CANONICAL_SIZES in build script
- Update RENDER_SIZES mapping
- Rebuild all assets
- Update test expectations

**Trade-offs**:
- ✅ More detail possible (shell scutes, better anatomy)
- ❌ Larger in terminal (more lines)
- ❌ Requires updating all tests and runtime code

---

## SECTION G: FILES REQUIRING MODIFICATION

### G.1 If Using Current 21x13 Format (Recommended)

| File | Changes Required |
|------|------------------|
| `assets/mascot/source/idle.png` | **Replace** with new pixel-art turtle |
| `tools/build_mascot_assets.py` | Add #686838 to BODY_COLORS (line 57) |
| `src/aios/cli/mascot/assets.py` | **Regenerate** (run build script) |
| `tests/unit/test_mascot_assets.py` | No changes (accepts codes 0-3) |
| `tests/unit/test_mascot_halfblock.py` | No changes (accepts codes 0-3) |

### G.2 If Increasing Resolution

| File | Changes Required |
|------|------------------|
| `assets/mascot/source/idle.png` | **Replace** with larger pixel-art |
| `tools/build_mascot_assets.py` | Update CANONICAL_SIZES, RENDER_SIZES |
| `src/aios/cli/mascot/assets.py` | **Regenerate** |
| `src/aios/cli/mascot/halfblock.py` | Update default dimensions (line 507) |
| `tests/unit/test_mascot_assets.py` | Update expected dimensions (line 164) |
| `tests/unit/test_mascot_halfblock.py` | Update expected dimensions |

---

## SECTION H: CRITICAL ARCHITECTURAL PRINCIPLES

### H.1 Must Preserve
1. **Source raster defines geometry** - Renderer must NOT reconstruct anatomy
2. **Per-pixel semantic codes** - No zone-based classification
3. **2-bit packed format** - 4 pixels per byte, deterministic
4. **Transparency support** - Code 0 for transparent pixels
5. **Color palette** - Fixed set of ANSI colors for terminal

### H.2 Must NOT Break
1. **Pixel occupancy** - Don't add/remove pixels
2. **Transparency** - Don't fill transparent regions
3. **Turtle silhouette** - Don't change outline shape
4. **Pixel coordinates** - Don't shift or scale non-uniformly
5. **Canvas size** - Don't change 21x13 (unless intentional)

### H.3 Renderer Limitations (Accept These)
1. **Vertical compression**: Half-block chars merge 2 rows
2. **Aspect ratio distortion**: Terminal chars are ~2:1
3. **Color quantization**: Limited to 5 ANSI colors
4. **No gradients**: Only solid colors per pixel

---

## SECTION I: RECOMMENDATION

### Immediate Action (Pending User Approval)

**DO NOT IMPLEMENT** until user reviews this analysis and approves approach.

### Proposed Next Steps

1. **User reviews this report** and confirms understanding
2. **User approves approach**: Manual pixel-art recreation at 21x13
3. **Create new source PNG** with improved turtle anatomy
4. **Update build script** with brownish-olive color
5. **Rebuild assets** and run tests
6. **Show preview** to user for approval
7. **Iterate** if needed

### Alternative Consideration

If user wants reference to look "closer" in terminal:
- Consider increasing resolution to 32x20 or 50x20
- More pixels = more detail = better match to reference
- But larger in terminal

---

## APPENDIX: TECHNICAL DETAILS

### A.1 Color Distance Calculations
Reference shell colors (brownish-olive):
- #686838: R(104), G(104), B(56)
- Distance to #266B2D (current shell): ΔE ≈ 45 (significant)
- **Recommendation**: Add #686838 to BODY_COLORS

### A.2 Half-Block Rendering Math
- Input: 13 rows × 21 columns = 273 pixels
- Output: 7 lines × 21 characters = 147 characters
- Compression: 2:1 vertical (inherent to half-block)
- Aspect ratio correction needed: Multiply width by 2 OR height by 0.5

### A.3 Terminal Character Dimensions
- Typical terminal char: ~9×16 pixels (width×height)
- Aspect ratio: 16/9 ≈ 1.78:1 (height:width)
- For square pixels: Need to render at 2× width or 0.5× height

---

## CONCLUSION

**The reference image is a full illustration, not a pixel-art sprite.** It serves as a visual guide for the desired turtle appearance, not a direct source for conversion.

**Current implementation is functionally correct** (21x13 pixel art, 6 colors, proper semantic codes) but **does not match reference anatomy** (wrong shell color, small shell, missing tail, no segmentation).

**Solution**: Manually create new 21x13 pixel-art turtle inspired by reference, then rebuild assets. No pipeline changes needed except adding brownish-olive color to palette.

**Next step**: Await user approval of this analysis before proceeding.

---

**END OF REPORT**
