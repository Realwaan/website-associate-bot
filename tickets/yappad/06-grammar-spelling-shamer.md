# Shame writing mistakes without fixing them

**Dependencies:** 01, 02

## Problem

YapPad must catch spelling and grammar mistakes at `0ms` mid-typing without false-firing on valid partial words, underline them in the synchronized backdrop, and mock the user—while refusing to autocorrect and making the `✨ Autocorrect` button physically dodge the cursor.

## Potentially Related Files

- `js/grammar.js` - `YP.Grammar.analyze`, `LEXICON_PREFIXES`, `isPrefixOfLexicon`, `renderBackdropHTML`, `escapeHTML`
- `js/app.js` - `0ms` `input` listener (`runGrammarCheck(true)`), `seenIssueKeys` / `seenIssueStarts` pruning, dodging `#btn-autocorrect`
- `styles.css` - wavy red/amber underline spans in `#editor-backdrop`

## What to Fix

1. Build `YP.Grammar.analyze(text, options)` in `js/grammar.js` with `LEXICON_PREFIXES` (`isPrefixOfLexicon`) so valid prefixes (`delet`, `notep`, `qu`, `in`, `Hello. W`) produce `0` false positives mid-word.
2. Immediately flag mid-typing typos (`teh`, `notpad`, `definately`, `recieve`, `seperate`, `occured`), `3+` repeated letters (`sooo`), zero-vowel `4+` letter mashes, `q` followed by non-`u`, uncapitalized sentence starts (`Hello. w`), double spaces, repeated words (`the the`), and grammar crimes (`We could of`, `should of`, `your welcome`, comma splices).
3. Call `runGrammarCheck(true)` at `0ms` on `#editor-textarea`'s `input` event.
4. Prune resolved issue fingerprints from `state.seenIssueKeys` and `state.seenIssueStarts` so fixed mistakes re-arm if typed again, while extending the same span (`sooo` → `soooo`) does not re-spam.
5. Render XSS-safe wavy underlines in `#editor-backdrop` via `renderBackdropHTML(text, issues)` and `escapeHTML(text)`.
6. Make the ribbon's `✨ Autocorrect` button dodge the pointer on hover/click and log "I won't fix that. You need to learn."

## Acceptance Criteria

- [ ] `YP.Grammar.analyze` reports `0` issues for clean sentences, `"going"`, and partial prefixes `"delet"`, `"notep"`, `"qu"`, `"in"`, `"Hello. W"` when `cursorPos === text.length`.
- [ ] Typing `"teh"`, `"sooo"`, `"We could of"`, `"the the"`, `"Hello. w"`, or `"notpad"` fires at `0ms` without requiring a trailing space.
- [ ] `renderBackdropHTML` escapes `<script>` tags and renders wavy underline markup aligned with `#editor-textarea`.
- [ ] Fixing a typo and retyping it fires the shamer again, while extending `"sooo"` to `"soooo"` does not re-spam.
- [ ] Hovering or clicking `✨ Autocorrect` dodges the cursor and never autocorrects the text.
