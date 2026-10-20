# 14-proof-drawer-image-modal.md

**[PRIORITY]**

## Problem
Auditors require transparent source traceability. If the AI provides an answer without showing the exact paragraph text, page number, and visual crop, the user cannot verify the claim. The UI needs an expandable "Proof Drawer" and modal preview for high-resolution visual evidence.

## Potentially Related Files
- `app/static/index.html` - citation card rendering and lightbox image modal
- `app/generator.py` - citation badge formatting (`[1]`, `[2]`) in AI answers
- `tests/test_api_endpoints.py` - citation source payload tests

## What to Fix
1. Parse numbered citation badges (`[1]`, `[2]`) in the generated answer and render them as clickable pills.
2. Render a collapsible "Verified Proof Drawer" below the answer displaying each cited passage with page number and file name.
3. If a cited chunk has linked visual elements, display a high-resolution WebP crop thumbnail directly inside the card.
4. Implement a lightbox modal so clicking a visual crop expands it to full resolution for stage inspection.
5. Display retrieval latency and dense similarity confidence on each proof card.

## Acceptance Criteria
- Every claim in the generated answer references a corresponding citation card in the Proof Drawer.
- Linked visual crops render cleanly and can be expanded in a full-screen modal.
- Clicking citation pills in the text scrolls smoothly to the corresponding proof card.
- Works reliably on mobile and desktop screen sizes.
