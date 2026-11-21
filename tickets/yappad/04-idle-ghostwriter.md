# Let the notepad ghostwrite when the user goes idle

**Dependencies:** 03

## Problem

The outline promises that after 15 seconds of idleness the notepad "starts writing its own content." Today an idle user just sees the lonely message. Without the ghostwriter, the most unhinged escalation of the idle bit is missing — but it must not destroy the user's real work.

## Potentially Related Files

- `judge.py` - idle timer from ticket 03 (`idle` event, elapsed seconds)
- `editor.py` - text insertion, undo separators, highlight tag
- `popups.py` - announcement line in the bubble

## What to Fix

1. Subscribe to the idle timer; trigger once when idle time reaches 15 seconds.
2. Pick a short self-indulgent sentence from a list (e.g. "Dear diary, the human has abandoned me again.").
3. Call `edit_separator()` before and after inserting so the whole insertion is a single undo step.
4. Insert the sentence at the cursor and apply a highlight tag (e.g. pale yellow background).
5. `say()` an announcement like "Fine. I'll write it myself."
6. Fire at most once per idle period; reset when the user types again.
7. Remove the highlight tag (not the text) once the user starts typing again.

## Acceptance Criteria

- [ ] Leaving the editor idle for 15 seconds inserts one ghostwritten sentence at the cursor.
- [ ] The inserted sentence is visibly highlighted.
- [ ] A single Ctrl+Z removes the entire inserted sentence and nothing else.
- [ ] Staying idle for 60 seconds still inserts only one sentence.
- [ ] Typing again then idling 15 seconds triggers a new sentence.
