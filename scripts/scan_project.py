"""Project code scanner that auto-generates ticket markdown files.

Walks a project directory, detects issues (TODOs, debug statements,
empty catches, large files, etc.), and generates ticket .md files
in the bot's tickets/ folder.
"""
import os
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via config.py)
# ---------------------------------------------------------------------------

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", ".next", "dist", "build", "out",
    "__pycache__", ".venv", "venv", ".cache", "coverage",
    ".turbo", ".vercel", ".svelte-kit", "vendor", ".idea",
    ".vscode", "public", "static",
}

DEFAULT_FILE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".css", ".scss",
    ".java", ".go", ".rb", ".php", ".svelte", ".vue",
    ".html", ".rs", ".cs",
}

DEFAULT_LARGE_FILE_THRESHOLD = 300  # lines


# ---------------------------------------------------------------------------
# Issue data class
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    """A single detected issue in a source file."""
    file_path: str         # relative to project root
    line_number: int
    category: str          # e.g. "todo", "debug", "empty-catch", "large-file", "skipped-test", "hardcoded-secret"
    severity: str          # "low", "medium", "high"
    message: str           # human-readable description
    snippet: str = ""      # the offending line/text


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

# TODO / FIXME / HACK / XXX
_TODO_PATTERN = re.compile(
    r"(?:#|//|/\*|\*|<!--)\s*(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)\b[:\s]*(.*)",
    re.IGNORECASE,
)

# Debug / console statements
_DEBUG_PATTERNS = [
    re.compile(r"\bconsole\.(log|debug|info|warn|error|trace|dir)\s*\(", re.IGNORECASE),
    re.compile(r"\bprint\s*\(", re.IGNORECASE),
    re.compile(r"\bSystem\.out\.print(ln)?\s*\(", re.IGNORECASE),
    re.compile(r"\blogger\.(debug|info|warn)\s*\(.*?(test|temp|xxx|delete)", re.IGNORECASE),
    re.compile(r"\bdebugger\b"),
]

# Empty catch / except blocks (simple heuristic)
_EMPTY_CATCH_PATTERNS = [
    re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}", re.IGNORECASE),
    re.compile(r"except\s*.*?:\s*pass\b", re.IGNORECASE),
    re.compile(r"catch\s*\([^)]*\)\s*\{\s*//", re.IGNORECASE),  # catch with only a comment
]

# Skipped tests
_SKIP_TEST_PATTERNS = [
    re.compile(r"\b(test|it|describe)\.skip\s*\("),
    re.compile(r"\bxit\s*\("),
    re.compile(r"\bxdescribe\s*\("),
    re.compile(r"@pytest\.mark\.skip"),
    re.compile(r"@(Ignore|Disabled)\b"),
]

# Hardcoded secrets (simplified)
_SECRET_PATTERNS = [
    re.compile(r"""(api[_-]?key|secret|password|token|auth)\s*[:=]\s*["'][^"']{8,}["']""", re.IGNORECASE),
    re.compile(r"""(sk_live|pk_live|sk_test|pk_test)_[A-Za-z0-9]{10,}"""),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

# Filenames that look like they shouldn't be checked for debug statements
_LOGGER_WHITELIST_FILENAMES = {"logger.ts", "logger.js", "logging.py", "log.py", "logger.py"}


def _detect_in_file(rel_path: str, lines: list[str]) -> list[Issue]:
    """Run all detectors on a single file's lines."""
    issues: list[Issue] = []
    basename = Path(rel_path).name.lower()
    is_test_file = any(p in basename for p in ("test", "spec", ".test.", ".spec."))

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip empty / very short lines
        if len(stripped) < 3:
            continue

        # 1) TODO / FIXME / HACK
        m = _TODO_PATTERN.search(stripped)
        if m:
            tag = m.group(1).upper()
            msg = m.group(2).strip() or "(no description)"
            severity = "high" if tag in ("FIXME", "BUG", "HACK") else "medium"
            issues.append(Issue(
                file_path=rel_path,
                line_number=i,
                category="todo",
                severity=severity,
                message=f"[{tag}] {msg}",
                snippet=stripped,
            ))

        # 2) Debug / console statements (skip logger utility files and test files)
        if basename not in _LOGGER_WHITELIST_FILENAMES and not is_test_file:
            for pat in _DEBUG_PATTERNS:
                if pat.search(stripped):
                    # Skip if it looks like actual production logging, not debug
                    if re.search(r"console\.(warn|error)\s*\(", stripped):
                        continue
                    issues.append(Issue(
                        file_path=rel_path,
                        line_number=i,
                        category="debug",
                        severity="low",
                        message=f"Debug statement left in code",
                        snippet=stripped,
                    ))
                    break  # one match per line is enough

        # 3) Empty catch/except
        for pat in _EMPTY_CATCH_PATTERNS:
            if pat.search(stripped):
                issues.append(Issue(
                    file_path=rel_path,
                    line_number=i,
                    category="empty-catch",
                    severity="medium",
                    message="Empty or swallowed exception handler",
                    snippet=stripped,
                ))
                break

        # 4) Skipped tests
        if is_test_file:
            for pat in _SKIP_TEST_PATTERNS:
                if pat.search(stripped):
                    issues.append(Issue(
                        file_path=rel_path,
                        line_number=i,
                        category="skipped-test",
                        severity="low",
                        message="Disabled/skipped test case",
                        snippet=stripped,
                    ))
                    break

        # 5) Hardcoded secrets
        for pat in _SECRET_PATTERNS:
            if pat.search(stripped):
                issues.append(Issue(
                    file_path=rel_path,
                    line_number=i,
                    category="hardcoded-secret",
                    severity="high",
                    message="Possible hardcoded secret or API key",
                    snippet=stripped[:80] + ("..." if len(stripped) > 80 else ""),
                ))
                break

    return issues


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------

def scan_directory(
    project_path: str,
    ignore_dirs: set[str] | None = None,
    file_extensions: set[str] | None = None,
    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD,
) -> list[Issue]:
    """Walk a project directory and detect issues in all matching files.

    Args:
        project_path: Absolute path to the project root.
        ignore_dirs: Directory names to skip.
        file_extensions: File extensions to scan (e.g. {".ts", ".py"}).
        large_file_threshold: Files above this line count get flagged.

    Returns:
        List of Issue objects found across the project.
    """
    ignore = ignore_dirs or DEFAULT_IGNORE_DIRS
    extensions = file_extensions or DEFAULT_FILE_EXTENSIONS
    project = Path(project_path).resolve()
    all_issues: list[Issue] = []

    if not project.exists() or not project.is_dir():
        raise FileNotFoundError(f"Project path not found: {project_path}")

    for root_str, dirs, files in os.walk(project):
        root = Path(root_str)

        # Prune ignored directories (modifying dirs in-place)
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith(".")]

        for filename in files:
            file_path = root / filename
            ext = file_path.suffix.lower()

            if ext not in extensions:
                continue

            rel = str(file_path.relative_to(project)).replace("\\", "/")

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (PermissionError, OSError):
                continue

            lines = content.splitlines()

            # Large file check
            if len(lines) > large_file_threshold:
                all_issues.append(Issue(
                    file_path=rel,
                    line_number=0,
                    category="large-file",
                    severity="low",
                    message=f"File has {len(lines)} lines (threshold: {large_file_threshold}). Consider refactoring.",
                    snippet="",
                ))

            # Run line-by-line detectors
            all_issues.extend(_detect_in_file(rel, lines))

    logger.info(f"Scanned {project_path}: found {len(all_issues)} issue(s)")
    return all_issues


# ---------------------------------------------------------------------------
# Group issues into ticket-worthy chunks
# ---------------------------------------------------------------------------

def _classify_area(file_path: str) -> str:
    """Determine the ticket area prefix from the file path."""
    fp = file_path.lower()

    if any(p in fp for p in ("admin", "dashboard")):
        return "admin"
    if any(p in fp for p in ("test", "spec", "__tests__")):
        return "utils"
    if any(p in fp for p in ("util", "lib", "helper", "script", "seed", "migration", "config")):
        return "utils"
    if any(p in fp for p in ("server", "api/", "actions/", "routes/")):
        return "server"
    return "client"


def _slugify(text: str, max_len: int = 50) -> str:
    """Convert text to a filename-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-")


def group_issues(issues: list[Issue]) -> dict[str, list[Issue]]:
    """Group issues into ticket-worthy sets.

    Groups by (area, category, parent_directory) so each ticket
    focuses on one type of problem in one area of the codebase.
    """
    buckets: dict[str, list[Issue]] = defaultdict(list)

    for issue in issues:
        area = _classify_area(issue.file_path)
        parent = str(Path(issue.file_path).parent)
        if parent == ".":
            parent = "root"
        key = f"{area}|{issue.category}|{parent}"
        buckets[key].append(issue)

    return dict(buckets)


# ---------------------------------------------------------------------------
# Generate ticket markdown files
# ---------------------------------------------------------------------------

_CATEGORY_LABELS = {
    "todo": "Resolve TODO/FIXME Comments",
    "debug": "Remove Debug Statements",
    "empty-catch": "Fix Empty Exception Handlers",
    "large-file": "Refactor Large Files",
    "skipped-test": "Re-enable Skipped Tests",
    "hardcoded-secret": "Remove Hardcoded Secrets",
}

_CATEGORY_PROBLEMS = {
    "todo": "The following files contain TODO, FIXME, HACK, or similar markers indicating unfinished work or known issues that need attention.",
    "debug": "Debug/console statements were found left in production code. These should be removed or replaced with proper logging before deployment.",
    "empty-catch": "Empty or swallowed exception handlers were found. These hide errors and make debugging difficult. Each catch block should either handle the error properly or re-throw it.",
    "large-file": "The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.",
    "skipped-test": "Disabled or skipped test cases were found. These should either be re-enabled and fixed, or removed if no longer relevant.",
    "hardcoded-secret": "Possible hardcoded secrets, API keys, or tokens were detected in the source code. These should be moved to environment variables immediately.",
}


def generate_tickets(
    grouped: dict[str, list[Issue]],
    output_folder: str,
    tickets_dir: str = "tickets",
) -> list[str]:
    """Generate ticket markdown files from grouped issues.

    Args:
        grouped: Output of group_issues().
        output_folder: Folder name inside tickets/ (e.g. "my-project-scan")
        tickets_dir: Base tickets directory path.

    Returns:
        List of generated file paths (relative to tickets_dir).
    """
    out_path = Path(tickets_dir) / output_folder
    out_path.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []

    # Track canonical filenames generated in this run to avoid accidental duplicates.
    generated_names: set[str] = set()

    for key, issues in grouped.items():
        area, category, parent_dir = key.split("|", 2)
        parent_slug = _slugify(parent_dir.replace("/", "-").replace("\\", "-"))

        # Build filename
        label_slug = _slugify(_CATEGORY_LABELS.get(category, category))
        filename = f"{area}-{label_slug}-{parent_slug}.md" if parent_slug != "root" else f"{area}-{label_slug}.md"

        # Keep scanner output idempotent: always target the canonical filename.
        # If legacy duplicate files (e.g. *-extra.md) exist from older scans,
        # remove them so repeated scans don't multiply loadable tickets.
        if parent_slug != "root":
            legacy_extra = out_path / f"{area}-{label_slug}-{parent_slug}-extra.md"
        else:
            legacy_extra = out_path / f"{area}-{label_slug}-extra.md"

        if legacy_extra.exists():
            try:
                legacy_extra.unlink()
                logger.info(f"Removed legacy duplicate ticket: {legacy_extra.name}")
            except OSError as e:
                logger.warning(f"Could not remove legacy duplicate ticket {legacy_extra.name}: {e}")

        if filename in generated_names:
            logger.warning(f"Skipping duplicate canonical ticket key in this scan run: {filename}")
            continue
        generated_names.add(filename)

        # Build ticket content
        title = _CATEGORY_LABELS.get(category, category.title())
        nice_dir = parent_dir.replace("\\", "/")
        full_title = f"{title} in {nice_dir}" if nice_dir != "root" else title

        # Priority for secrets
        priority_line = ""
        if category == "hardcoded-secret":
            priority_line = "\n**[CRITICAL]**\n"

        # Problem section
        problem = _CATEGORY_PROBLEMS.get(category, "Issues were detected that require attention.")

        # Related files
        unique_files = list(dict.fromkeys(i.file_path for i in issues))
        related_lines = []
        for fp in unique_files[:15]:  # cap at 15
            related_lines.append(f"- `{fp}`")
        related_section = "\n".join(related_lines) if related_lines else "- (see details below)"

        # What to fix — list each issue
        fix_items = []
        for idx, issue in enumerate(issues[:30], start=1):  # cap at 30 items
            loc = f"`{issue.file_path}` line {issue.line_number}" if issue.line_number else f"`{issue.file_path}`"
            fix_items.append(f"{idx}. {loc}: {issue.message}")
        fix_section = "\n".join(fix_items)

        # Acceptance criteria
        criteria_map = {
            "todo": [
                "All TODO/FIXME/HACK comments in the listed files are resolved or converted into tracked tickets",
                "No orphan TODO markers remain in the affected directory",
            ],
            "debug": [
                "No `console.log` / `print()` / `debugger` statements remain in production code",
                "Proper logging (if needed) replaces removed debug statements",
            ],
            "empty-catch": [
                "All catch/except blocks either handle errors meaningfully or re-throw",
                "No silently swallowed exceptions in the affected files",
            ],
            "large-file": [
                "Each flagged file is split into smaller modules (under the line threshold) or justified with a comment",
                "All imports and references updated after refactoring",
            ],
            "skipped-test": [
                "Skipped tests are either re-enabled and passing, or explicitly removed with an explanation",
                "Test suite passes without skip markers",
            ],
            "hardcoded-secret": [
                "All secrets moved to environment variables (`.env`)",
                "No plaintext keys or tokens remain in source code",
                "`.env.example` updated with placeholder keys",
            ],
        }
        criteria_items = criteria_map.get(category, ["Issue is resolved", "Code is reviewed and tested"])
        criteria_section = "\n".join(f"- {c}" for c in criteria_items)

        # Assemble the markdown
        ticket_md = f"""# {full_title}
{priority_line}
## Problem

{problem}

## Potentially Related Files

{related_section}

## What to Fix

{fix_section}

## Acceptance Criteria

{criteria_section}
"""

        ticket_file = out_path / filename
        ticket_file.write_text(ticket_md.strip() + "\n", encoding="utf-8")
        generated.append(str(ticket_file))
        logger.info(f"Generated ticket: {filename} ({len(issues)} issue(s))")

    return generated


# ---------------------------------------------------------------------------
# High-level convenience function
# ---------------------------------------------------------------------------

def scan_and_generate(
    project_path: str,
    output_folder: str,
    tickets_dir: str = "tickets",
    ignore_dirs: set[str] | None = None,
    file_extensions: set[str] | None = None,
    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD,
) -> tuple[int, int, list[str]]:
    """Scan a project and generate tickets in one call.

    Returns:
        (total_issues, total_tickets, list_of_generated_file_paths)
    """
    issues = scan_directory(
        project_path,
        ignore_dirs=ignore_dirs,
        file_extensions=file_extensions,
        large_file_threshold=large_file_threshold,
    )

    if not issues:
        return 0, 0, []

    grouped = group_issues(issues)
    generated = generate_tickets(grouped, output_folder, tickets_dir)
    return len(issues), len(generated), generated


# ---------------------------------------------------------------------------
# CLI entrypoint (for standalone use)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python scan_project.py <project_path> <output_folder_name>")
        print("Example: python scan_project.py F:\\my-nextjs-app my-app-scan")
        sys.exit(1)

    proj = sys.argv[1]
    folder = sys.argv[2]

    total_issues, total_tickets, files = scan_and_generate(proj, folder)
    print(f"\n{'='*50}")
    print(f"Scan complete!")
    print(f"  Issues found : {total_issues}")
    print(f"  Tickets made : {total_tickets}")
    print(f"  Output folder: tickets/{folder}/")
    if files:
        print(f"\nGenerated files:")
        for f in files:
            print(f"  {f}")
