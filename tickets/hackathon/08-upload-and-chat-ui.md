# 08-upload-and-chat-ui.md

## Problem
Judges see the UI first. We need a clean page to upload documents and ask questions.

## Potentially Related Files
- `app/static/index.html`, `app/static/app.js`, `app/static/style.css`

## What to Fix
1. Add a drag-and-drop upload area with indexing progress.
2. Add a chat box that calls `POST /ask` and shows the answer.
3. Show loading and error states.
4. Keep it plain HTML and JS, with no build step.

## Acceptance Criteria
- Upload and ask works fully from the browser.
- Layout is readable when projected on a screen.
- A failed request shows a message instead of a blank page.
