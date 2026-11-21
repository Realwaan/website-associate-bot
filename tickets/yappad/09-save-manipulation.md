# Manipulate the Ctrl+S save flow

**Dependencies:** 01, 02

## Problem

In a normal editor, `Ctrl+S` quietly saves the document. In YapPad, saving must interrogate the user—either saving normally, demanding they rate their own work `/10` before downloading, or stalling for a 5-second dramatic countdown with suspense music—while always delivering the saved `.txt` download at the end.

## Potentially Related Files

- `js/modals.js` - `openSaveFlow(mode)` (`normal` / `rate` / `delay`)
- `js/app.js` - `Ctrl+S` interception (`e.preventDefault()`), `.txt` Blob download helper, `Demo` menu triggers
- `js/audio.js` - `playSuspenseMusic` and `playDisappointmentDing`

## What to Fix

1. Intercept `Ctrl+S` (`Cmd+S`) and `File → Save .txt` in `js/app.js` and route through `YP.Modals.openSaveFlow()`.
2. Support three save modes (randomly selected on `Ctrl+S`, or explicitly chosen from `Demo → Save Sabotage: Rate /10` and `Demo → Save Sabotage: 5s Suspense`): `normal`, `rate`, and `delay`.
3. In `rate` mode, require the user to rate their writing `1–10`, mock their chosen score (especially high scores), and then trigger the `.txt` download.
4. In `delay` mode, show a 5-second dramatic countdown bar while playing `playSuspenseMusic()` before triggering the `.txt` download.
5. Clear the unsaved `dirty` state once the `.txt` download completes.

## Acceptance Criteria

- [ ] Pressing `Ctrl+S` prevents the browser's default save-page dialog and opens `openSaveFlow`.
- [ ] `rate` mode validates a `1–10` score, delivers a snarky reaction to the rating, and downloads the `.txt` file.
- [ ] `delay` mode runs a 5-second suspense countdown with audio before downloading the `.txt` file.
- [ ] Both `Demo → Save Sabotage: Rate /10` and `Demo → Save Sabotage: 5s Suspense` trigger their respective flows directly.
