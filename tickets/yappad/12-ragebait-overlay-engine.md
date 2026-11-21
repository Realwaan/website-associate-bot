# Unleash ragebait overlays with font-shrink punishment

**[PRIORITY]**

**Dependencies:** 01, 02, 06, 10

## Problem

To dominate Category A (Most Frustrating), YapPad needs active visual harassment whenever the user makes a writing mistake or spams Backspace: a dead-center ragebait modal with runaway buttons, 4-corner-hopping error stalkers that dodge `✕`, shrinking error cards, and a progressive font-shrink punishment (`15.5px → 11px`) that forces the user to click `🔍 Beg For Normal Font`.

## Potentially Related Files

- `js/ragebait.js` - `YP.Ragebait`: `showCenterRagebait`, `spawnCornerStalker`, `spawnShrinkingError`, `onMistake`, `unleashAll`, `clearAll`
- `js/app.js` - `applyFontShrinkPunishment(errorCount)` and `#btn-restore-font` handler
- `styles.css` - `--editor-font-size`, corner-stalker positions, shrink card transitions, hazard stripes

## What to Fix

1. Build `showCenterRagebait(issue)` in `js/ragebait.js` that pops dead-center with `playRageBuzzer()`, mistake counter, runaway `✨ Fix It For Me` button (`-46px` shift on hover), once-dodging `✕` (`-28px`), and humiliating dismiss button.
2. Build `spawnCornerStalker(issue)`: up to `2` cards that hop `top-left → top-right → bottom-right → bottom-left` every `1650ms` (`playCornerZip()`) and dodge `✕` hover up to `3` times before allowing close.
3. Build `spawnShrinkingError(issue)`: up to `3` cards that scale through `[1.0, 0.84, 0.70, 0.56, 0.44, 0.34, 0.26]` (`550ms` initial pulse, then every `1350ms` and on hover with `playShrinkSqueak()`).
4. Wire `YP.Ragebait.onMistake(issue)` to trigger the center popup, corner stalker, and shrinking card on new mistakes and on every `5th` Backspace.
5. Implement `applyFontShrinkPunishment(errorCount)` in `js/app.js` to shrink `--editor-font-size` from `15.5px` to `14px` (3 sins), `13px` (4 sins), `12px` (5 sins), and `11px` (6+ sins), revealing `#btn-restore-font` (`🔍 Beg For Normal Font`).

## Acceptance Criteria

- [ ] Making a mistake fires `YP.Ragebait.onMistake`, spawning the center ragebait modal, a corner-hopping card, and a shrinking error card inside `#ragebait-layer`.
- [ ] Corner stalker cards hop across the 4 corners every `1650ms` and dodge `✕` hover 3 times before closing.
- [ ] Shrinking error cards step down from `100%` to `26%` scale over time and on hover.
- [ ] Accumulating 3 to 6+ errors shrinks `--editor-font-size` down to `11px` across both backdrop and textarea and reveals `🔍 Beg For Normal Font`.
- [ ] Clicking `🔍 Beg For Normal Font` restores `--editor-font-size` to `15.5px` after a humiliating confirmation remark.
