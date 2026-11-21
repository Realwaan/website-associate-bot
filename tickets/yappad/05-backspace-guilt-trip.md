# Guilt-trip the user on every deletion

**Dependencies:** 01, 02

## Problem

Category A (Most Frustrating) requires YapPad to punish self-doubt. Every Backspace should increment the live telemetry counter and guilt-trip the user, every 5th Backspace should pop a center rage intervention, and deleting the whole document should trigger a dramatic emotional meltdown modal.

## Potentially Related Files

- `js/app.js` - `keydown` Backspace/Delete counter, mass-delete detector, 5th-backspace hook
- `js/modals.js` - `openBackspaceIntervention` and `openMeltdownModal`
- `js/ragebait.js` - center ragebait popup integration on every 5th Backspace
- `js/audio.js` - `playGuiltPop`, `playRageBuzzer`, `playOrchestralSting`

## What to Fix

1. Increment the live `Backspaces` counter in the telemetry ribbon on every `Backspace` or `Delete` keypress.
2. Fire a guilt-trip commentary card / toast + `playGuiltPop()` on single backspaces (rate-limited so normal editing stays readable).
3. On every `5th` Backspace, trigger the center ragebait intervention (`showCenterRagebait` / `openBackspaceIntervention`) with `playRageBuzzer()`.
4. Detect a mass delete (Select-All + `Backspace`/`Delete` when the buffer has content, or `Demo → Trigger Mass-Delete Meltdown`).
5. Open `openMeltdownModal` in `js/modals.js` with `playOrchestralSting()`, showing "...You selected everything. And deleted it. I need a moment."
6. Render a fake "YapPad is processing its emotions..." progress bar inside the meltdown modal before returning control.

## Acceptance Criteria

- [ ] Pressing `Backspace` increments the telemetry ribbon counter and logs a guilt-trip comment.
- [ ] Every `5th` Backspace opens the center ragebait intervention popup.
- [ ] `Ctrl+A` followed by `Backspace`/`Delete` opens the meltdown modal with the animated emotional-processing progress bar.
- [ ] `Demo → Trigger Mass-Delete Meltdown` launches the meltdown modal on demand for stage demos.
