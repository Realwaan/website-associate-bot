# Synthesize procedural Web Audio sound effects

**Dependencies:** 01

## Problem

Loading external `.mp3` files can fail on `file://` origins or flaky venue Wi-Fi. YapPad needs a zero-asset procedural Web Audio API synthesizer (`js/audio.js`) that generates all 13 comedic sound effects in the browser and degrades gracefully if Web Audio is unavailable or muted.

## Potentially Related Files

- `js/audio.js` - `YP.Audio` procedural Web Audio synthesizer and `localStorage` persistence
- `index.html` - audio mute/volume controls in the window chrome / menu
- `js/app.js` - wires sound triggers to typing, grammar, ragebait, save, and exit events

## What to Fix

1. Build `YP.Audio` in `js/audio.js` using `AudioContext` oscillators, gain envelopes, and noise buffers with zero external audio asset dependencies.
2. Implement all 13 synthesizer cues: `playSigh`, `playDisappointmentDing`, `playPanicPip`, `playGuiltPop`, `playOrchestralSting`, `playSuspenseMusic`, `playSadViolin`, `playAngryBuzz`, `playSupportiveChime`, `playRoastPop`, `playRageBuzzer`, `playCornerZip`, and `playShrinkSqueak`.
3. Persist `{ enabled, volume }` in `localStorage` (`yp_audio_config` / `sn_audio_config`).
4. Resume `AudioContext` cleanly on the first user gesture and silently no-op in headless/Node environments where `AudioContext` is absent.
5. Add a quick Mute/Unmute toggle button in the top chrome.

## Acceptance Criteria

- [ ] `YP.Audio` exposes all 13 sound methods and runs without loading any external `.mp3` or `.wav` files.
- [ ] Calling any `YP.Audio.play*()` method in Node or when muted never throws an exception.
- [ ] Toggling Mute updates `localStorage` and silences all cues immediately.
