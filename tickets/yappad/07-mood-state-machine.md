# Add the mood state machine with SVG face

**[PRIORITY]**

**Dependencies:** 01, 02

## Problem

Without shifting moods and visual escalation, YapPad's personality stays static. The app needs 6 distinct moods, escalation stages (`0..4`), ambient weather effects (Sad rain, Supportive sparkles), an Angry word scrambler, and an animated SVG face in the status bar whose pupils track the user's cursor.

## Potentially Related Files

- `js/moods.js` - `YP.Moods` definitions, dialogue pools, `makeFakeCitation(word)`, `getFaceState`, mood roller
- `js/app.js` - mood shift timer, Angry word scrambler, eye-tracking pupil listener, escalation stage updates
- `styles.css` - `body[data-mood]` and `body[data-escalation="0..4"]` tokens, Sad rain, Supportive sparkles
- `index.html` - `Mood` menu and SVG face status bar

## What to Fix

1. Define all 6 moods in `js/moods.js`: `passive-aggressive` (😒 default), `dramatic` (😤), `intellectual` (🧐 with `makeFakeCitation(word)`), `sad` (😢 with animated rain), `angry` (😡 with word scrambler + apology), and rare `supportive` (🥰 ~8% roll weight, `durationSec: 10` before reverting).
2. Implement `getFaceState(mood, escalation)` to drive the status-bar SVG face mouth, eyebrows, and eye-tracking pupils.
3. Update `body[data-mood]` and `body[data-escalation="0..4"]` as mistakes, backspaces, and time accumulate.
4. In `Angry` mood (or via `Demo → Trigger Angry Word Scramble`), scramble a recent word in the editor and immediately follow with a passive-aggressive apology.
5. Wire the `Mood` top menu so presenters can switch to any of the 6 moods on demand during the live demo.

## Acceptance Criteria

- [ ] `YP.Moods` exposes all 6 moods with `supportive.durationSec === 10` and `makeFakeCitation(word)` returning an academic citation string.
- [ ] Switching moods updates `body[data-mood]`, the telemetry mood badge, and the SVG face expression.
- [ ] `Supportive` mood automatically reverts to `Passive-Aggressive` after 10 seconds.
- [ ] `Sad` mood displays the rain overlay and `Supportive` mood displays sparkles.
- [ ] `Angry` word scrambler scrambles a word in the editor and logs an apology comment.
