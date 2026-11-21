# Judge typing speed with rolling WPM sparkline

**Dependencies:** 01, 02

## Problem

YapPad needs to watch *how* the user types in the browser: sighing when they type too slowly, shaking in panic when they mash keys too quickly, and calling them out after 5 seconds of idleness. Judges also need to see a live WPM telemetry readout and sparkline in the top ribbon.

## Potentially Related Files

- `js/app.js` - `450ms` telemetry loop, `6500ms` rolling keystroke window, sparkline renderer
- `index.html` - WPM counter and `#wpm-sparkline` in the telemetry ribbon
- `styles.css` - panic shake animation and telemetry badge styling
- `js/audio.js` - `playSigh` and `playPanicPip` triggers

## What to Fix

1. Record printable keystroke timestamps on `#editor-textarea` inside a `6500ms` rolling window.
2. Run a `450ms` telemetry interval in `js/app.js` that computes live WPM (5 chars = 1 word) and updates the telemetry ribbon.
3. Render a live WPM sparkline (`#wpm-sparkline`) showing recent typing velocity trends.
4. Trigger a Slow Sigh comment + `playSigh()` when active typing stays below `22 WPM` for `3.6s` (`12s` cooldown).
5. Trigger a Panic comment + `playPanicPip()` + window shake class when typing reaches `>=78 WPM` for `1.5s` (`10s` cooldown).
6. Trigger a lonely check comment after `5s` of idleness (`3.5s` when in `Sad` mood) once per idle window.

## Acceptance Criteria

- [ ] Telemetry ribbon WPM readout and `#wpm-sparkline` update live while typing and decay to `0` when idle.
- [ ] Typing slowly (`<22 WPM` for `3.6s`) triggers a slow-typing commentary line and sigh sound (`12s` cooldown).
- [ ] Typing rapidly (`>=78 WPM` for `1.5s`) triggers a panic commentary line, pip sound, and shake animation (`10s` cooldown).
- [ ] Stopping for `5s` (`3.5s` in `Sad` mood) fires the lonely check exactly once until typing resumes.
