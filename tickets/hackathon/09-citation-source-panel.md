# 09-citation-source-panel.md

## Problem
Citations only convince judges if they can see the source text. A clickable proof panel is the visual payoff of RAG.

## Potentially Related Files
- `app/static/app.js`, `app/static/style.css`

## What to Fix
1. Render `[1]`, `[2]` in the answer as clickable chips.
2. Clicking a chip shows the source chunk, document name, and page number in a side panel.
3. Highlight the chunk text.

## Acceptance Criteria
- Every citation in an answer opens its matching source text.
- The panel shows document name and page.
- It works with multiple documents loaded.
