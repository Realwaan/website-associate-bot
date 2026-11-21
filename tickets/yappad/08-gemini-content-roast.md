# Roast content every ~30 words via Gemini

**Dependencies:** 02, 07

## Problem

Category B (Creative Use of AI) depends on YapPad reading *what* the user wrote and reacting with contextual, passive-aggressive commentary. Nothing currently sends text to an LLM. The roast must also survive venue Wi-Fi failing, or demo step 6 dies on stage.

## Potentially Related Files

- `ai_roast.py` - Gemini client, prompt, fallback roasts, background worker
- `mood.py` - `mood.current` included in the prompt
- `popups.py` - `say()` to deliver the roast
- `.env.example` - `GEMINI_API_KEY` placeholder

## What to Fix

1. Read `GEMINI_API_KEY` from `.env` via `python-dotenv`; never hardcode it.
2. Track word count; trigger a roast each time the count grows by 30 words since the last roast.
3. Send the last ~150 words plus the current mood to Gemini (`google-genai`) with a system prompt asking for one passive-aggressive line under 20 words, no slurs or profanity.
4. Run the request on a background thread with a 6-second timeout; post the result back to the UI via `root.after()`.
5. Keep a list of 20+ canned roasts (e.g. "This paragraph has no direction. Much like your life.", "This is actually good. I'm suspicious.") used when the key is missing, the call times out, or it errors.
6. Skip a new roast if one is already in flight.
7. Log (not crash) on API errors; show the fallback roast instead.

## Acceptance Criteria

- [ ] With a valid key, typing 30 words produces a roast that references the written content.
- [ ] The editor never freezes while a roast request is in progress.
- [ ] With no `.env` or with Wi-Fi off, a canned roast appears instead and the app does not crash.
- [ ] No API key appears in any tracked file or commit.
- [ ] Typing 90 words produces exactly 3 roasts.
