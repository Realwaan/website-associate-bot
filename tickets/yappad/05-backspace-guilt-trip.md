# Guilt-trip the user on every deletion

**Dependencies:** 01, 02

## Problem

Category A (Most Frustrating) needs the notepad to react emotionally when the user removes text. Right now deleting is silent, so the most relatable frustration beat in the demo (steps 4–5: backspace guilt trip and select-all meltdown) has nothing to show.

## Potentially Related Files

- `judge.py` - BackSpace/Delete counters and timing window
- `popups.py` - guilt-trip lines and the meltdown dialog
- `editor.py` - `<BackSpace>` and `<Delete>` bindings on the `Text` widget

## What to Fix

1. Bind `<BackSpace>` and `<Delete>` in `editor.py` and forward the events to `judge.py`.
2. On a single backspace, `say()` a guilt-trip line in the bubble (no modal), rate-limited to one every 3 seconds (e.g. "Are you sure? You worked so hard on that.").
3. After 5+ backspaces within 10 seconds, escalate to "pattern" lines (e.g. "Deleting again? This is becoming a pattern.").
4. Detect a mass delete: delete/backspace while the selection covers the entire buffer.
5. On a mass delete, open a modal meltdown via `show_modal()` with "...You selected everything. And deleted it. I need a moment."
6. Inside the meltdown, show a fake "Notepad is processing its emotions" progress bar that fills over ~3 seconds before the dialog closes.
7. Make sure the deletion itself still happens — this ticket judges deletions, it never blocks them.
8. Emit `backspace` and `mass_delete` events for the sound and mood tickets.

## Acceptance Criteria

- [ ] A single backspace shows a guilt-trip line in the bubble without stealing focus.
- [ ] No more than one guilt-trip line appears every 3 seconds.
- [ ] 5 backspaces within 10 seconds produce a "pattern" line.
- [ ] Ctrl+A then Backspace opens the meltdown modal with a progress bar that completes in about 3 seconds.
- [ ] After the meltdown closes, the text is actually deleted.
