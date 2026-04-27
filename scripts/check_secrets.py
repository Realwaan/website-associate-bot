"""Simple secret scanner for tracked project files.

Usage:
    python scripts/check_secrets.py

Exits with code 1 if any likely secrets are found.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Common token/credential signatures.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("NVIDIA API token", re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}\b")),
    ("Discord bot token", re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b")),
    ("Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}\b", re.IGNORECASE)),
    ("Potential password assignment", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*[^\s]{8,}")),
    (
        "Database URL with credentials",
        re.compile(r"\bpostgres(?:ql)?://[^\s:@<]+:[^\s@<]+@[^\s<]+"),
    ),
]

SKIP_FILES = {
    ".env.example",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


def _git_tracked_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        print(f"Failed to list tracked files via git: {exc}", file=sys.stderr)
        return []

    files: list[Path] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = Path(line.strip())
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        files.append(path)
    return files


def _scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings: list[str] = []
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            findings.append(f"{path}:{line_no}: {label}")
    return findings


def main() -> int:
    files = _git_tracked_files()
    if not files:
        print("No tracked files found (or git unavailable).")
        return 0

    findings: list[str] = []
    for path in files:
        findings.extend(_scan_file(path))

    if findings:
        print("Potential secrets detected:")
        for item in findings:
            print(f"- {item}")
        print("\nResolve or remove these before committing.")
        return 1

    print("No obvious secrets detected in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
