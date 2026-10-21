# 06-collision-bounded-halo-cropper.md

**[CRITICAL]**

## Problem
Standard bounding box detectors crop images tightly to the graphics boundary. This clips chart legends, axis titles (e.g., "$ in Millions"), and figure footnotes, causing Vision LLMs to hallucinate or misread units during live demo queries. Inverted coordinates from PDF pt units can also cause zero-pixel image crop crashes.

## Potentially Related Files
- `app/ast_builder.py` - HaloCropper bounding box expansion and WebP rasterizer
- `tests/test_ast_builder.py` - visual crop geometry and halo bounds tests

## What to Fix
1. Detect visual bounding boxes from PDF stream objects and Markdown table patterns.
2. Implement 12% outward halo padding around bounding boxes to capture adjacent legends and footnotes.
3. Clamp halo expansion strictly against page boundary margins and prevent overlapping into adjacent text blocks.
4. Sanitize coordinate pairs (`x0 <= x1`, `y0 <= y1`) to prevent negative dimensions or inverted crop rectangles.
5. Render and save lossless WebP image crops into `app/static/crops/` with unique visual node IDs.

## Acceptance Criteria
- Cropped visuals preserve complete axis labels, units, and captions without clipping.
- Zero crashes on inverted coordinate inputs or zero-area bounding boxes.
- WebP crops are generated and accessible via HTTP URLs.
- Render cache ensures a PDF page is rasterized at most once during batch cropping.\n