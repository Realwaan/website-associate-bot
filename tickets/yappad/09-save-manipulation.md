# Manipulate the Ctrl+S save flow

**Dependencies:** 01

## Problem

Saving is currently a normal, instant action. The outline wants Ctrl+S to second-guess the user ("Saving... but are you really done though?") with randomized manipulation — while still being a notepad that *works perfectly*. The file must always end up saved.

## Potentially Related Files

- `editor.py` - Ctrl+S binding and save routine from ticket 01
- `popups.py` - `show_modal()` for the rating prompt, `say()` for comments
- `sounds.py` - optional dramatic sting during the delay (ticket 10)

## What to Fix

1. Wrap the existing save routine so Ctrl+S first `say()`s "Saving... but are you really done though?".
2. Randomly pick one of three branches (roughly equal odds): normal save, rating prompt, or dramatic delay.
3. Rating prompt: modal asks "Rate your work before I save it. /10"; accept 1–10, react to the score, then save.
4. Dramatic delay: show "Saving..." with a 5-second countdown in the status bar (play the dramatic sound if available), then save.
5. Prevent a second Ctrl+S from starting another save while one is in progress.
6. Reset the `dirty` flag only after the file is written.

## Acceptance Criteria

- [ ] Pressing Ctrl+S 10 times shows at least two different save branches.
- [ ] In every branch, the file on disk contains the latest text afterwards.
- [ ] The rating prompt rejects values outside 1–10 and reacts to the given score.
- [ ] The dramatic delay saves after about 5 seconds without freezing the window.
- [ ] Pressing Ctrl+S during an in-progress save does not trigger a second save.
