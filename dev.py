"""
dev.py — Local development runner with auto-restart.

Watches all .py files in the project directory.  Whenever a file is saved
(or a new commit is pulled), the bot restarts automatically.

Usage:
    python dev.py

Stop with Ctrl+C.
This script is for LOCAL development only — Render handles production restarts
automatically via autoDeploy: true in render.yaml.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
WATCH_DIR   = Path(__file__).resolve().parent
WATCH_EXTS  = {".py"}
IGNORE_DIRS = {"__pycache__", ".venv", "venv", ".git", "node_modules"}
POLL_INTERVAL = 1.5          # seconds between file-system checks
BOT_SCRIPT  = "main.py"
# ─────────────────────────────────────────────────────────────────────────────


def _snapshot(root: Path) -> dict[Path, float]:
    """Return {filepath: mtime} for every watched file under root."""
    result = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place so os.walk skips them
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            if Path(fname).suffix in WATCH_EXTS:
                fp = Path(dirpath) / fname
                try:
                    result[fp] = fp.stat().st_mtime
                except OSError:
                    pass
    return result


def _changed_files(before: dict, after: dict) -> list[Path]:
    """Return a list of files that were added or modified."""
    changed = []
    for fp, mtime in after.items():
        if before.get(fp) != mtime:
            changed.append(fp)
    return changed


class BotProcess:
    """Manages the subprocess running main.py."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self._kill()
            print(f"\n🟢  Starting {BOT_SCRIPT} …\n{'─' * 50}")
            self._proc = subprocess.Popen(
                [sys.executable, BOT_SCRIPT],
                cwd=WATCH_DIR,
            )

    def restart(self, reason: str):
        print(f"\n🔄  Change detected in: {reason}")
        self.start()

    def _kill(self):
        if self._proc and self._proc.poll() is None:
            print("⏹   Stopping previous process …")
            if sys.platform == "win32":
                self._proc.terminate()
            else:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def stop(self):
        with self._lock:
            self._kill()


def main():
    bot = BotProcess()
    bot.start()

    snapshot = _snapshot(WATCH_DIR)
    print(f"👀  Watching {len(snapshot)} file(s) for changes …  (Ctrl+C to stop)\n")

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            new_snapshot = _snapshot(WATCH_DIR)
            changed = _changed_files(snapshot, new_snapshot)
            if changed:
                snapshot = new_snapshot
                # Show only relative paths so the output stays readable
                names = ", ".join(str(f.relative_to(WATCH_DIR)) for f in changed[:3])
                if len(changed) > 3:
                    names += f" (+{len(changed) - 3} more)"
                bot.restart(names)
    except KeyboardInterrupt:
        print("\n\n🛑  Dev watcher stopped.")
        bot.stop()


if __name__ == "__main__":
    main()
