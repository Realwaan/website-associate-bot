# Collision-Bounded Halo Cropper for Visual Elements

**[CRITICAL]**

## Problem
Standard bounding box detectors crop images tightly to graphics boundaries. This clips chart legends, axis units (e.g., '$ in Millions'), and figure footnotes, causing Vision LLMs to hallucinate or misread units during live demo queries. In addition, hardcoding fake table bounding boxes (blindly cropping the middle 40% of a page) produces broken crops on real documents.

## Potentially Related Files
- app/ast_builder.py - HaloCropper bounding box expansion and WebP rasterizer
- tests/test_ast_builder.py - visual crop geometry and halo bounds tests

## What to Fix
1. Detect visual bounding boxes from PDF stream graphics and real table structures rather than hardcoding static page percentages.
2. Implement 12% outward halo padding around bounding boxes to capture adjacent legends, axis labels, and footnotes.
3. Clamp halo expansion strictly against page boundary margins to prevent overlapping adjacent text blocks.
4. Sanitize coordinate pairs (x0 <= x1, y0 <= y1) to prevent negative dimensions or inverted crop rectangles.
5. Render and save lossless WebP image crops into data/crops/ with unique visual node IDs.

## Acceptance Criteria
- Cropped visuals preserve complete axis labels, units, and captions without clipping.
- No hardcoded center-page bounding box hacks; geometry adapts to true element coordinates.
- Zero crashes on inverted coordinate inputs or zero-area bounding boxes.
- WebP crops are generated and accessible via HTTP URLs.
