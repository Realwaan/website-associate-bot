# Let YapPad ghostwrite when the user goes idle

**Dependencies:** 03

## Problem

When the user abandons the keyboard for 15 seconds, YapPad should refuse to sit quietly and start typing its own self-indulgent monologue directly into the document at typewriter speed (`38ms`/char), while remaining reversible so the user's real notes are not permanently ruined.

## Potentially Related Files

- `js/app.js` - `15s` idle detector, `38ms`/char ghostwriter interval, undo snapshot
- `js/moods.js` - mood-specific ghost-writing scripts
- `styles.css` - active ghostwriting status indicator

## What to Fix

1. Trigger ghostwriting when idle time reaches `15s` in the `js/app.js` telemetry loop.
2. Select a mood-matched ghostwriting script from `YP.Moods` (`js/moods.js`).
3. Save an undo snapshot before ghostwriting starts so `Ctrl+Z` (or `Edit → Undo`) restores the pre-ghostwritten document in one step.
4. Stream the ghostwritten sentence into `#editor-textarea` at `38ms` per character while keeping `#editor-backdrop` synchronized.
5. Announce the takeover in `#commentary-panel` (e.g. "Fine. Since you walked away, I'll write this myself.").
6. Immediately stop the `38ms`/char interval if the user presses any key or clicks into the editor, and re-arm only after the user types again.

## Acceptance Criteria

- [ ] Leaving the editor idle for `15s` streams a ghostwritten sentence into `#editor-textarea` at ~`38ms`/char.
- [ ] Pressing any key mid-stream immediately halts the ghostwriter without duplicating text.
- [ ] A single undo restores the document to its exact pre-ghostwriting state.
- [ ] Remaining idle after a completed ghostwrite does not loop endlessly until the user types again.
