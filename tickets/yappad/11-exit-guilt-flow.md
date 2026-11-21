# Block exit with a 3-step guilt flow plus i_remember.txt

**Dependencies:** 01, 10

## Problem

Closing the window currently just closes it. The demo's finale (steps 7–8) needs YapPad to resist being closed with unsaved work, escalate across three confirmations, and leave a passive-aggressive note behind on the desktop. This is the closing laugh of the presentation.

## Potentially Related Files

- `editor.py` - `WM_DELETE_WINDOW` protocol handler, `dirty` flag, File → Exit
- `popups.py` - `show_modal()` for the three confirmation steps
- `sounds.py` - `violin` on close without saving

## What to Fix

1. Register a `WM_DELETE_WINDOW` handler and route File → Exit through it.
2. If there are no unsaved changes, close immediately (still write the note).
3. If unsaved, show modal step 1: "Are you sure?" (Yes / No).
4. On Yes, step 2: "Are you REALLY sure?"; on Yes, step 3: "The notepad will remember this." (OK).
5. Choosing No at any step cancels and returns to the editor with text intact.
6. Play the `violin` sound when closing without saving.
7. On close, write `i_remember.txt` containing "You closed me. I'm fine. Everything is fine." to `~/Desktop`, falling back to the home directory if no Desktop folder exists.
8. Never overwrite an unrelated file: if `i_remember.txt` exists, append a new line with a timestamp.

## Acceptance Criteria

- [ ] Closing with unsaved changes shows exactly three escalating dialogs before the app exits.
- [ ] Choosing No at any step keeps the app open with the text unchanged.
- [ ] Closing with no unsaved changes exits without any dialogs.
- [ ] After exit, `i_remember.txt` exists on the Desktop (or home folder) with the expected line.
- [ ] Closing twice appends a second line instead of overwriting the file.
