# Rehearse the 8-step demo script

**Dependencies:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11

## Problem

YapPad is pitched for all four categories (Frustrating, Creative AI, Funniest, Pointless-yet-Brilliant), but that only lands if the live demo hits every beat in order without crashing. The features have never been run end-to-end on the actual presentation laptop, with and without internet.

## Potentially Related Files

- `README.md` - demo script and winning angle
- `main.py` - entry point used on stage
- `.env` - local Gemini key on the demo laptop (untracked)

## What to Fix

1. Install from a fresh clone on the demo laptop using only the README instructions.
2. Run the 8-step script: launch ("Oh. You again.") → slow typing sigh → typo shame → backspace guilt → select-all meltdown → live AI roast → 3-step exit → show `i_remember.txt`.
3. Rehearse once with Wi-Fi on (live Gemini roast) and once with Wi-Fi off (canned roast).
4. Time the full run; trim pauses so it fits in under 3 minutes.
5. Prepare a sample paragraph to type for the AI roast so the result is predictable.
6. Write any bugs found as new tickets instead of fixing them inside this ticket.
7. Close with the line: "We built a notepad. It works perfectly. It just hates you."

## Acceptance Criteria

- [ ] All 8 demo steps run back-to-back from a fresh clone without a crash.
- [ ] The full run completes in under 3 minutes.
- [ ] The demo works with Wi-Fi disabled (fallback roast shown).
- [ ] Every team member has run the script at least once.
- [ ] Any bugs found are filed as separate tickets in `tickets/yappad/`.
