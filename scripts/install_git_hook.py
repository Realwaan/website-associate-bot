"""Configure local git hooks to use .githooks in this repository.

Usage:
    python scripts/install_git_hook.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    hooks_path = repo_root / ".githooks"
    pre_commit = hooks_path / "pre-commit"

    if not pre_commit.exists():
        print(f"Missing hook file: {pre_commit}")
        return 1

    try:
        subprocess.run(
            ["git", "config", "--local", "core.hooksPath", str(hooks_path)],
            check=True,
            cwd=repo_root,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Failed to configure core.hooksPath: {exc}")
        return 1

    print(f"Configured core.hooksPath to: {hooks_path}")
    print("Pre-commit secret scan is now enabled for this repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
