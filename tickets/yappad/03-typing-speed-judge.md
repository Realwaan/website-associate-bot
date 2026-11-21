# Judge typing speed with WPM tracking

**Dependencies:** 01, 02

## Problem

The core joke of YapPad is that it watches *how* you type. Right now the editor has no idea whether the user is typing slowly, quickly, or not at all, so it cannot sigh, panic, or get lonely. This is demo steps 1–2 and the first thing judges see.

## Potentially Related Files

- `judge.py` - keystroke timestamps, rolling WPM, idle timer
- `editor.py` - `<Key>` binding on the `Text` widget, status bar
- `popups.py` - `say()` for comments

## What to Fix

1. Bind `<Key>` on the `Text` widget (tkinter only — no `pynput`, no global hooks) and forward printable keystrokes to `judge.py`.
2. Compute a rolling WPM over the last 10 seconds (5 characters = 1 word).
3. Show live WPM in the status bar, updated at least once per second.
4. When WPM stays below 15 for 5+ seconds while typing, `say()` a slow line (e.g. "😴 Still waiting...", "*sigh*").
5. When WPM exceeds 80, `say()` a panic line (e.g. "SLOW DOWN I CAN'T KEEP UP").
6. After 5 seconds with no keystrokes, `say()` "Hello? Are you still there? I'm lonely." once per idle period.
7. Rate-limit speed comments to one every 8 seconds so they don't spam the bubble.
8. Emit `slow_typing`, `fast_typing`, and `idle` events other modules (sounds, mood) can subscribe to.

## Acceptance Criteria

- [ ] Status bar WPM changes while typing and decays to 0 when idle.
- [ ] Typing one character every ~2 seconds produces a slow-typing comment.
- [ ] Mashing keys quickly produces "SLOW DOWN I CAN'T KEEP UP" (or another panic line).
- [ ] Stopping for 5 seconds produces the lonely line exactly once until typing resumes.
- [ ] `pynput` is not imported anywhere in the project.
