# Roast content every ~30 words via AI Brain

**Dependencies:** 02, 07

## Problem

Category B (Creative Use of AI) requires YapPad to evaluate what the user wrote every ~30 words using the active mood and live telemetry (`WPM`, `Backspaces`, `Errors`). It must support live cloud calls to Google Gemini (`gemini-2.5-flash`) or OpenAI (`gpt-4o-mini`) and fall back seamlessly to a built-in contextual offline critic when offline.

## Potentially Related Files

- `js/ai.js` - `YP.AI` prompt builder, Gemini & OpenAI REST callers (`12s` `AbortController` timeout), `generateOfflineRoast`, `testConnection`
- `js/modals.js` - `openAISettingsModal` (`AI Brain → Configure Gemini / OpenAI API...`)
- `js/app.js` - `~30`-word trigger, `Ctrl+J` manual roast shortcut, telemetry injection

## What to Fix

1. Build `YP.AI` in `js/ai.js` supporting three providers persisted in `localStorage` (`yp_ai_config` / `sn_ai_config`): `"offline"`, `"gemini"` (`gemini-2.5-flash`), and `"openai"` (`gpt-4o-mini`).
2. Include active mood, recent text, and live telemetry (`WPM`, `Backspaces`, `Errors`) in the prompt.
3. Enforce a `12s` `AbortController` timeout on cloud REST requests and automatically fall back to `generateOfflineRoast` on network failure, timeout, or missing key.
4. Ensure `generateOfflineRoast` produces contextual, mood-specific roasts (including fake academic citations in `Intellectual` mood).
5. Trigger a roast automatically every ~30 words typed and on demand via `Ctrl+J` or `AI Brain → Roast My Writing Now`.
6. Build `openAISettingsModal` in `js/modals.js` with provider selector, API key input, model override, and a **Test Connection** button calling `YP.AI.testConnection()`.

## Acceptance Criteria

- [ ] `YP.AI.generateOfflineRoast` returns a non-empty, mood-styled roast (with a citation in `Intellectual` mood) in `0ms` offline.
- [ ] Typing ~30 words (or pressing `Ctrl+J`) triggers an AI Judgment card in `#commentary-panel` and plays `playRoastPop()`.
- [ ] Cloud requests time out cleanly after `12s` via `AbortController` and fall back to `generateOfflineRoast` without throwing uncaught errors.
- [ ] `AI Brain → Configure Gemini / OpenAI API...` saves settings to `localStorage` and allows testing the connection.
