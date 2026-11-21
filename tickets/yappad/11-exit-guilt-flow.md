# Block exit with a 3-step guilt flow plus i_remember.txt

**Dependencies:** 01, 02, 10

## Problem

Closing YapPad should be a memorable stage finale. Clicking the window `✕` button (or `File → Exit`) must trap the user in a 3-step guilt confirmation dialog, play a synthesized sad violin, auto-download `i_remember.txt`, save a persistent grudge in `localStorage`, and transition to the staring-eyes Abandoned Desktop screen.

## Potentially Related Files

- `js/modals.js` - `openExitFlow` (3-step modal chain, `i_remember.txt` download, grudge persistence)
- `index.html` - window chrome `✕` button and `#abandoned-screen` overlay
- `js/app.js` - startup grudge detector (`yp_remembers_close` / `sn_remembers_close`), `beforeunload` listener, `Demo → Reset Grudge Memory`
- `js/audio.js` - `playSadViolin`

## What to Fix

1. Wire the window chrome `✕` button and `File → Exit` to `YP.Modals.openExitFlow()`.
2. Present 3 escalating confirmation steps ("Are you sure?", "Are you REALLY sure?", "YapPad will remember this.") while playing `playSadViolin()`.
3. On completion of Step 3, trigger a browser download of `i_remember.txt` containing `"You closed me. I'm fine. Everything is fine."` (plus timestamp and close count).
4. Persist `sn_remembers_close = "true"` / `yp_remembers_close = "true"` and increment `sn_close_count` / `yp_close_count` in `localStorage`.
5. Reveal `#abandoned-screen` with staring eyes and a button to sheepishly reopen YapPad.
6. On next load, if the grudge flag is set, start at a higher escalation stage and greet the user with a grudge remark; allow resetting via `Demo → Reset Grudge Memory`.

## Acceptance Criteria

- [ ] Clicking `✕` walks through all 3 confirmation steps and can be canceled at Steps 1–2.
- [ ] Completing Step 3 downloads `i_remember.txt`, sets the grudge keys in `localStorage`, and shows `#abandoned-screen`.
- [ ] Reloading after an exit displays the grudge greeting, and `Demo → Reset Grudge Memory` clears the grudge state back to Stage 0.
