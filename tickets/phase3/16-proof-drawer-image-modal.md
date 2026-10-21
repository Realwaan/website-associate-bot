# Verified Proof Drawer and Citation Image Inspection

**[PRIORITY]**

## Problem
Auditors require transparent source traceability. If the AI provides an answer without showing the exact paragraph text, page number, and visual crop, the user cannot verify the claim. Furthermore, if the LLM hallucinates citation indices higher than the retrieved chunk count (e.g. citing `[7]` when only 3 chunks exist), clicking citations throws index errors.

## Potentially Related Files
- `src/components` / `app/static/index.html` - citation card rendering and lightbox image modal
- `app/generator.py` - citation badge formatting and index sanitization
- `tests/test_api_endpoints.py` - citation source payload tests

## What to Fix
1. Sanitize generated citation indices in `app/generator.py` so citation numbers are strictly clamped to the count of retrieved chunks (`k <= len(chunks)`).
2. Render an interactive "Verified Proof Drawer" below answers displaying each cited passage with page number and file name.
3. If a cited chunk has linked visual elements, display a high-resolution WebP crop thumbnail directly inside the card.
4. Implement a lightbox modal so clicking a visual crop expands it to full resolution for inspection.
5. Display retrieval latency and measured dense similarity confidence on each proof card.

## Acceptance Criteria
- Every claim in the generated answer references a valid citation card in the Proof Drawer.
- Zero out-of-range citation index bugs (`[7]` on 3 chunks).
- Linked visual crops render cleanly and expand in a full-screen lightbox modal.
- Smoothly scrolls to proof cards when citation pills are clicked.
