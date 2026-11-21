# Build the commentary panel with toast notifications

**[PRIORITY]**

**Dependencies:** 01

## Problem

YapPad constantly judges the user while they type. It needs a dedicated in-window Margin Notes feed (`#commentary-panel`), a floating toast stack (`#toast-stack`) for quick barbs, and a shared modal overlay (`#modal-overlay`) for blocking flows so routine commentary never steals focus from `#editor-textarea`.

## Potentially Related Files

- `index.html` - `#commentary-panel`, `#toast-stack`, `#modal-overlay` markup
- `styles.css` - commentary card animations, mood border/badge styling, toast transitions
- `js/app.js` - `addCommentary(text, meta)` and `showToast(text, tone)` helpers
- `js/modals.js` - shared modal open/close lifecycle on `#modal-overlay`

## What to Fix

1. Build `#commentary-panel` as a live Margin Notes sidebar showing timestamped judgment cards with mood badges and category tags.
2. Expose `addCommentary(text, options)` on `YP.App` to prepend a card, cap the visible history so the DOM stays fast, and highlight new entries.
3. Build `#toast-stack` for non-blocking floating notifications that auto-dismiss after ~4 seconds.
4. Ensure neither `addCommentary` nor `showToast` steals keyboard focus or cursor selection from `#editor-textarea`.
5. Build the reusable `#modal-overlay` manager in `js/modals.js` for blocking dialogs (save sabotage, meltdown, exit trap, AI settings, scoreboard).
6. Add a "Clear Notes" control in `#commentary-panel` that snarkily reacts when clicked.

## Acceptance Criteria

- [ ] Calling `addCommentary()` prepends a styled card in `#commentary-panel` within 50 ms.
- [ ] Typing in `#editor-textarea` continues uninterrupted while commentary cards and toasts appear.
- [ ] Toasts in `#toast-stack` auto-dismiss after ~4 seconds and cap stack height.
- [ ] Opening a modal via `YP.Modals` displays `#modal-overlay` and traps action until dismissed.
- [ ] All user-derived strings rendered in commentary cards or toasts are HTML-escaped.
