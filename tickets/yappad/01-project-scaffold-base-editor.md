# Scaffold YapPad web app shell with synchronized editor

**[PRIORITY]**

**Dependencies:** None

## Problem

YapPad needs a zero-dependency browser-based text editor shell that runs both via `http://127.0.0.1:3456` (`node server.mjs`) and directly via `file://` (`index.html`). Without the window chrome, menu bar, telemetry ribbon, and pixel-synced `#editor-backdrop` + `#editor-textarea`, none of the real-time judgment, ragebait, mood, or AI modules can attach to the page.

## Potentially Related Files

- `index.html` - app shell, menus, telemetry ribbon, backdrop/textarea, overlays
- `styles.css` - design tokens, mood themes, pixel-synced `--editor-font-size`
- `server.mjs` - zero-dependency Node HTTP static server on port `3456`
- `js/app.js` - `window.YP` (aliased as `window.SN`) main controller, file open/save, line numbers, cursor telemetry
- `.gitignore` - ignores `.env`, `node_modules/`, logs

## What to Fix

1. Build `index.html` with window chrome titled "YapPad", menus (`File`, `Edit`, `Mood`, `AI Brain`, `Demo`, `Help`), and telemetry ribbon (`WPM`, `Backspaces`, `Errors`, `Mood`, `#btn-restore-font` hidden until ≥3 sins).
2. Add the synchronized `#editor-backdrop` + `#editor-textarea` with line numbers, cursor line/col telemetry, and pixel-synced `--editor-font-size`.
3. Include layout containers for `#commentary-panel`, SVG `#yappad-face` status bar, `#abandoned-screen`, `#ragebait-layer`, `#toast-stack`, and `#modal-overlay`.
4. Load classic scripts via `<script defer>` in dependency order (`audio.js`, `moods.js`, `grammar.js`, `ai.js`, `modals.js`, `ragebait.js`, `app.js`) attached to `window.YP` (`window.SN` alias).
5. Build `server.mjs` as a zero-dependency Node static server (`127.0.0.1`, `PORT` or `3456`) with path-traversal protection.
6. Support `File → New` (`Alt+N`), `File → Open .txt` (`Ctrl+O`), and `File → Save .txt` (`Ctrl+S`).
7. Ensure `[hidden] { display: none !important; }` and responsive layout fit cleanly within `862x694` without viewport clipping.

## Acceptance Criteria

- [ ] `node server.mjs` starts cleanly on `http://127.0.0.1:3456` and serves `index.html` with zero console errors.
- [ ] Opening `index.html` directly via `file://` works without ES module CORS errors.
- [ ] Typing in `#editor-textarea` keeps `#editor-backdrop` scroll and `--editor-font-size` pixel-synced.
- [ ] Line numbers, word/char count, and cursor row/column update live on every edit.
- [ ] Path-traversal requests (e.g. `/../`) to `server.mjs` return HTTP 403 or 404.
