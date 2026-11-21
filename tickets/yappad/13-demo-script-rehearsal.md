# Verify smoke tests with 90-second stage demo runbook

**Dependencies:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12

## Problem

To sweep all four hackathon categories (`A–D`, 100 pts total) in a 90-second presentation, YapPad needs automated unit and HTTP smoke tests (`smoke_test.mjs`, `http_smoke.mjs`), a live Category Coverage Scoreboard modal (`Help → Category Coverage (A–D)`), one-click `Demo` menu triggers, and a rehearsed runbook.

## Potentially Related Files

- `smoke_test.mjs` - unit smoke tests for moods, 0ms grammar/prefix rules, XSS escaping, and offline AI roasts
- `http_smoke.mjs` - HTTP smoke test against `server.mjs`
- `js/modals.js` - `openScoreboardModal` (`Help → Category Coverage (A–D)`) and `openAboutModal`
- `js/app.js` - `Demo` menu actions (`Insert Roastable Sample Text`, `Trigger Angry Word Scramble`, `Save Sabotage`, `Trigger Mass-Delete Meltdown`, `Reset Grudge Memory`)
- `README.md` - quick-start guide and 90-second stage demo runbook

## What to Fix

1. Build `openScoreboardModal` in `js/modals.js` (`Help → Category Coverage (A–D)`) showing live session telemetry mapped across Categories A, B, C, and D (25 pts each).
2. Wire all `Demo` menu presets in `js/app.js`, including `Demo → Insert Roastable Sample Text` to trigger font-shrink punishment (`11px`), wavy underlines, ragebait overlays, and AI roast simultaneously.
3. Write `smoke_test.mjs` covering all 6 moods (`supportive.durationSec === 10`, fake citations), `0` false positives on clean words/prefixes (`"going"`, `"delet"`, `"notep"`, `"qu"`, `"in"`, `"Hello. W"`), `0ms` detection on `"teh"`, `"sooo"`, `"We could of"`, `"the the"`, `"Hello. w"`, `"notpad"`, XSS `<script>` escaping in `renderBackdropHTML`, and offline AI roasts.
4. Write `http_smoke.mjs` verifying `server.mjs` serves `index.html`, `styles.css`, and all `js/*.js` modules with HTTP 200 and blocks path traversal.
5. Verify `node --check` passes on `server.mjs` and every `js/*.js` file.
6. Document the 90-second stage demo runbook in `README.md`.

## Acceptance Criteria

- [ ] `node --check` exits `0` on `server.mjs` and all `js/*.js` modules.
- [ ] `node smoke_test.mjs` prints `ALL_UNIT_CHECKS_PASSED` and exits `0`.
- [ ] `node http_smoke.mjs` prints `HTTP_SMOKE_TEST_PASSED` and exits `0`.
- [ ] `Demo → Insert Roastable Sample Text` triggers wavy underlines, `11px` font-shrink punishment, ragebait overlays, and an AI roast in one click.
- [ ] `Help → Category Coverage (A–D)` opens the live hackathon scoreboard modal.
