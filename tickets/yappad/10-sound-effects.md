# Play sound effects for judgment events

**Dependencies:** 03, 05, 06

## Problem

Audible sighs and dramatic stings make the judgment land in a room full of people — text alone is easy to miss during a demo. There is no audio layer yet. It must never crash the app on laptops without audio devices or with missing files.

## Potentially Related Files

- `sounds.py` - `pygame.mixer` wrapper with `play(name)` (new)
- `sounds/` - `sigh.mp3`, `ding.mp3`, `dramatic.mp3`, `violin.mp3`
- `judge.py` - emits `slow_typing`, `grammar_error`, `mass_delete` events
- `README.md` - credits for sound sources

## What to Fix

1. Create `sounds.py` that initializes `pygame.mixer` once and preloads clips from `sounds/`.
2. Expose `play(name)`; if mixer init fails or the file is missing, silently no-op (log once).
3. Map events: `slow_typing` → `sigh`, `grammar_error` → `ding`, `mass_delete` → `dramatic`, close-without-save → `violin`.
4. Rate-limit each sound (e.g. sigh at most once per 10s) so audio doesn't stack.
5. Add a View → Mute toggle.
6. Source four royalty-free/CC0 clips (each under 5s, under 200 KB) and credit them in the README.

## Acceptance Criteria

- [ ] Slow typing plays a sigh; a typo plays a ding; select-all delete plays the dramatic sting.
- [ ] Deleting a file from `sounds/` does not crash the app — that sound is just silent.
- [ ] The app starts and runs normally on a machine with no audio device.
- [ ] The Mute toggle silences all sounds immediately.
- [ ] All four clips have a CC0 or royalty-free source listed in the README.
