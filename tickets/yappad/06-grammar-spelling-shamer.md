# Shame writing mistakes without fixing them

**Dependencies:** 02

## Problem

A normal editor quietly corrects typos. YapPad should instead notice mistakes and judge them out loud — but never fix them. There is currently no spelling or grammar detection, so demo step 3 ("make a typo → passive-aggressive popup") cannot happen. Detection must be offline and instant (no Java, no LLM calls).

## Potentially Related Files

- `judge.py` - word-boundary detection, spelling and grammar checks
- `editor.py` - red underline tag on the `Text` widget
- `popups.py` - shaming lines
- `requirements.txt` - `pyspellchecker`

## What to Fix

1. Load `pyspellchecker` (`SpellChecker()`) once at startup.
2. When the user finishes a word (space, Enter, or punctuation), check it; ignore numbers, URLs, and words under 2 characters.
3. Tag misspelled words with a red underline tag; never change the text.
4. `say()` a shaming line on a misspelling (e.g. "That's not a word. I checked. Twice.", "I won't fix that. You need to learn.").
5. Add regex grammar heuristics on sentence end: standalone lowercase "i", double spaces, a sentence starting with a lowercase letter, and a simple comma splice (", " followed by a pronoun + verb pattern such as ", it is").
6. `say()` a grammar line for each heuristic hit (e.g. "Comma splice. Disappointing.").
7. Rate-limit shaming to one comment every 4 seconds; underlines still apply for every mistake.
8. Emit a `grammar_error` event for the sound ticket.

## Acceptance Criteria

- [ ] Typing "teh " underlines "teh" in red and shows a shaming line.
- [ ] The misspelled word is not autocorrected or changed in any way.
- [ ] Typing "i went home." triggers a grammar comment about lowercase "i".
- [ ] Typing "It rained, it was cold." triggers the comma-splice comment.
- [ ] Spelling and grammar checks work with Wi-Fi disabled.
