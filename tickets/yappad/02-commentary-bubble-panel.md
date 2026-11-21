# Build the non-blocking commentary bubble

**[PRIORITY]**

**Dependencies:** 01

## Problem

Almost every YapPad feature "talks" to the user. If each comment were a modal `messagebox`, typing would freeze on every backspace or typo and the demo would stall. The notepad needs one shared, non-blocking speech bubble that any module can push a line to, plus a single helper for the few moments that are allowed to be modal (meltdown, save prompt, exit flow).

## Potentially Related Files

- `popups.py` - bubble widget, message queue, modal helper
- `editor.py` - docks the bubble panel into the main window
- `mood.py` - later supplies the current mood for bubble styling

## What to Fix

1. Create a `Bubble` panel in `popups.py` docked at the right or top of the editor window (never covering the text cursor).
2. Expose `say(text, source=None)` that queues a message; show one message at a time.
3. Auto-dismiss each message after ~4 seconds, then show the next queued one.
4. Cap the queue (e.g. 5) and drop the oldest lines so the bubble never lags far behind the user.
5. Make sure showing a message never steals keyboard focus from the `Text` widget.
6. Support a mood color/emoji prefix via an optional `style` argument (default neutral).
7. Add `show_modal(title, text, buttons)` helper wrapping a `Toplevel` dialog for the three modal flows.

## Acceptance Criteria

- [ ] Calling `say("test")` from anywhere shows the line in the bubble within 100 ms.
- [ ] Typing continues uninterrupted while bubble messages appear and disappear.
- [ ] Each message disappears on its own after about 4 seconds.
- [ ] Pushing 20 messages rapidly shows at most 5 queued lines, not 20.
- [ ] `show_modal()` blocks input to the editor until a button is pressed and returns the chosen button.
