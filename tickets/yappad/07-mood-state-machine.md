# Add the mood state machine

**[PRIORITY]**

**Dependencies:** 02

## Problem

Without moods, YapPad says the same kind of thing forever and the comedy flatlines. The outline defines six moods that change how the notepad reacts, and the AI roast ticket needs the current mood for its prompt. There is no shared mood state today, so each feature would invent its own tone.

## Potentially Related Files

- `mood.py` - mood enum, transitions, timers, line selection
- `popups.py` - mood emoji/color in the bubble and status bar
- `editor.py` - word scrambling for the Angry mood
- `judge.py` - events that can push mood changes

## What to Fix

1. Define six moods in `mood.py`: Passive-Aggressive 😒 (default), Dramatic 😤, Intellectual 🧐, Sad 😢, Angry 😡, Supportive 🥰.
2. Expose `mood.current` and `mood.line(category)` so other modules pick mood-appropriate lines from one place.
3. Shift mood randomly every 45–90 seconds, weighted so Supportive is rare (≤5%).
4. Push event-driven shifts: long idle → Sad, mass delete → Dramatic, many backspaces → Angry.
5. Revert Supportive back to Passive-Aggressive after exactly 10 seconds.
6. In Angry mood, occasionally scramble one recent word (max once per 60s) as a single undo step with a highlight tag, then `say()` an apology.
7. In Intellectual mood, word-choice comments include a fake citation (e.g. "(Oxford, 1987)").
8. Show the current mood emoji and name in the status bar; announce changes in the bubble.

## Acceptance Criteria

- [ ] The status bar shows the current mood, starting as Passive-Aggressive.
- [ ] The mood changes on its own within 90 seconds of use.
- [ ] Supportive mood always reverts to Passive-Aggressive after 10 seconds.
- [ ] A scrambled word in Angry mood is highlighted and fully restored by one Ctrl+Z.
- [ ] Comments from at least two other modules visibly change tone when the mood changes.
