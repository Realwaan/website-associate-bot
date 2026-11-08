"""Codebase Scanner Service for detecting code quality issues and generating structured ticket files."""
import os
import re
from pathlib import Path
from typing import Dict, List, Any
from config import (
    SCAN_IGNORE_DIRS,
    SCAN_FILE_EXTENSIONS,
    SCAN_LARGE_FILE_THRESHOLD,
    SCAN_ENABLE_TODO,
    SCAN_ENABLE_DEBUG,
    SCAN_ENABLE_EMPTY_CATCH,
    SCAN_ENABLE_SKIPPED_TEST,
    SCAN_ENABLE_HARDCODED_SECRET,
    SCAN_ENABLE_LARGE_FILE,
)

SECRET_PATTERNS = [
    re.compile(r'(?:api[_-]?key|auth[_-]?token|secret|password)\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', re.I),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'eyJ[a-zA-Z0-9_\-]{20,}\.eyJ[a-zA-Z0-9_\-]{20,}'),
]

DEBUG_PATTERNS = [
    re.compile(r'\bconsole\.(?:log|debug|warn|error|trace)\s*\('),
    re.compile(r'\bprint\s*\('),
    re.compile(r'\bdebugger\b'),
]

TODO_PATTERNS = [
    re.compile(r'\b(?:TODO|FIXME|HACK|XXX)\b\s*[:\-]?\s*(.*)', re.I),
]

EMPTY_CATCH_PATTERNS = [
    re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}'),
    re.compile(r'except(?:\s+[\w\s,]+)?:\s*pass'),
]

SKIPPED_TEST_PATTERNS = [
    re.compile(r'@pytest\.mark\.skip'),
    re.compile(r'\bit\.skip\('),
    re.compile(r'\bdescribe\.skip\('),
    re.compile(r'\btest\.skip\('),
]

class CodeScanner:
    """Scans projects and groups code issues into actionable tickets."""

    def scan_directory(self, base_path: str) -> Dict[str, List[Dict[str, Any]]]:
        results: Dict[str, List[Dict[str, Any]]] = {
            "todos": [],
            "debug_statements": [],
            "empty_catches": [],
            "oversized_files": [],
            "skipped_tests": [],
            "hardcoded_secrets": []
        }

        root = Path(base_path)
        if not root.exists():
            return results

        for path in root.rglob("*"):
            if any(part in SCAN_IGNORE_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_FILE_EXTENSIONS:
                continue

            try:
                rel_path = str(path.relative_to(root))
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                total_lines = len(lines)
                if SCAN_ENABLE_LARGE_FILE and total_lines > SCAN_LARGE_FILE_THRESHOLD:
                    results["oversized_files"].append({
                        "file": rel_path,
                        "lines": total_lines,
                        "threshold": SCAN_LARGE_FILE_THRESHOLD
                    })

                content = "".join(lines)
                if SCAN_ENABLE_EMPTY_CATCH:
                    for p in EMPTY_CATCH_PATTERNS:
                        if p.search(content):
                            results["empty_catches"].append({
                                "file": rel_path,
                                "message": "Empty catch / except block found"
                            })

                for idx, line in enumerate(lines, 1):
                    # Secrets
                    if SCAN_ENABLE_HARDCODED_SECRET:
                        for sp in SECRET_PATTERNS:
                            if sp.search(line):
                                results["hardcoded_secrets"].append({
                                    "file": rel_path,
                                    "line": idx,
                                    "snippet": line.strip()[:60]
                                })
                                break

                    # Debug
                    if SCAN_ENABLE_DEBUG:
                        for dp in DEBUG_PATTERNS:
                            if dp.search(line):
                                results["debug_statements"].append({
                                    "file": rel_path,
                                    "line": idx,
                                    "snippet": line.strip()[:60]
                                })
                                break

                    # TODOs
                    if SCAN_ENABLE_TODO:
                        for tp in TODO_PATTERNS:
                            m = tp.search(line)
                            if m:
                                results["todos"].append({
                                    "file": rel_path,
                                    "line": idx,
                                    "comment": m.group(1).strip() or line.strip()
                                })
                                break

                    # Skipped tests
                    if SCAN_ENABLE_SKIPPED_TEST:
                        for stp in SKIPPED_TEST_PATTERNS:
                            if stp.search(line):
                                results["skipped_tests"].append({
                                    "file": rel_path,
                                    "line": idx,
                                    "snippet": line.strip()[:60]
                                })
                                break
            except Exception:
                continue

        return results

    def generate_ticket_markdown(self, category: str, items: List[Dict[str, Any]], folder: str) -> str:
        """Formats scan findings into the standard ticket specification format compatible with ticket_loader.py."""
        files = sorted({item.get("file", "") for item in items if item.get("file")})
        title = f"Fix {category.replace('_', ' ').title()} in {folder}"
        is_critical = category == "hardcoded_secrets"
        is_priority = category in {"empty_catches", "todos"}

        md = f"# {title}\n\n"
        if is_critical:
            md += "**[CRITICAL]**\n\n"
        elif is_priority:
            md += "**[PRIORITY]**\n\n"

        md += "## Problem\n\n"
        md += f"Automated scanner detected {len(items)} {category.replace('_', ' ')} issues across {len(files)} file(s).\n\n"

        md += "## Potentially Related Files\n\n"
        for f in files[:10]:
            md += f"- `{f}`\n"
        if not files:
            md += "- *(to be determined)*\n"
        md += "\n"

        md += "## What to Fix\n\n"
        for idx, item in enumerate(items[:15], 1):
            f = item.get("file", "")
            l = item.get("line", "")
            msg = item.get("comment") or item.get("snippet") or item.get("message") or f"{item.get('lines', 0)} lines"
            line_str = f":{l}" if l else ""
            md += f"{idx}. `{f}{line_str}`: {msg}\n"
        if len(items) > 15:
            md += f"{min(len(items), 16)}. Resolve the remaining {len(items) - 15} occurrence(s) across affected files.\n"
        md += "\n"

        md += "## Acceptance Criteria\n\n"
        md += f"- All {len(items)} occurrences in target files are resolved\n"
        md += "- Code compiles and passes all automated tests\n"
        md += "- No new debug statements or secrets introduced\n"

        return md

scanner_service = CodeScanner()
