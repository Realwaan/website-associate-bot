# Scaffold YapPad with a working tkinter editor

**[PRIORITY]**

**Dependencies:** None

## Problem

The YapPad repo only contains an empty README. Nobody can build the sentient features (judging, moods, roasts) in parallel until there is an agreed module layout and a plain notepad that actually opens, edits, and saves text. Every other YapPad ticket builds on this skeleton.

## Potentially Related Files

- `main.py` - app entry point; loads `.env`, creates the window (new)
- `editor.py` - core tkinter `Text` editor, menu, status bar (new)
- `judge.py`, `mood.py`, `ai_roast.py`, `popups.py` - empty module stubs (new)
- `sounds/` - empty folder with `.gitkeep` (new)
- `requirements.txt` - `pyspellchecker`, `pygame`, `google-genai`, `python-dotenv` (new)
- `.env.example` - `GEMINI_API_KEY=` placeholder only (new)
- `.gitignore` - `.env`, `__pycache__/`, `*.pyc`, `venv/` (new)

## What to Fix

1. Create the project structure listed above at the repo root.
2. Build `editor.py` with a tkinter window titled "YapPad", a scrollable `Text` widget with `undo=True`, and a bottom status bar.
3. Add File menu actions: New, Open (`.txt`), Save (Ctrl+S), Save As, Exit — all functional with no sentient behavior yet.
4. Track a `dirty` flag that flips on edit and resets on save (needed later by save and exit tickets).
5. Expose simple hooks (e.g. `editor.on_key`, `editor.on_save`, `editor.on_close`) that later tickets can register callbacks on.
6. Show the greeting "Oh. You again." in the status bar on startup.
7. Add `.env.example` and `.gitignore`; confirm `.env` is never tracked.
8. Document setup (`pip install -r requirements.txt`, `python main.py`) in the README.

## Acceptance Criteria

- [ ] `python main.py` opens the YapPad window with no errors on a clean venv.
- [ ] A user can type, open a `.txt` file, edit it, and save it back to disk.
- [ ] Ctrl+Z / Ctrl+Y undo and redo edits.
- [ ] The status bar shows "Oh. You again." on launch.
- [ ] `.env` is listed in `.gitignore` and no API key exists in any tracked file.
- [ ] Every module from the project structure exists, even if empty.
