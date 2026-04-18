"""Project roadmap builder based on code scan findings.

Generates a roadmap markdown file with prioritized milestones and
suggested features. Can also generate scanner ticket files in the same
output folder to keep roadmap and execution tasks aligned.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from datetime import datetime

from scan_project import (
    scan_directory,
    group_issues,
    generate_tickets,
    DEFAULT_IGNORE_DIRS,
    DEFAULT_FILE_EXTENSIONS,
    DEFAULT_LARGE_FILE_THRESHOLD,
)


@dataclass
class RoadmapResult:
    """Result object returned by build_project_roadmap."""

    total_files_scanned: int
    total_issues: int
    total_tickets: int
    roadmap_file: str
    generated_ticket_files: list[str]
    top_categories: list[tuple[str, int]]
    suggested_features: list[str]


def _collect_file_stats(
    project_path: str,
    ignore_dirs: set[str],
    file_extensions: set[str],
) -> tuple[int, dict[str, int], dict[str, int]]:
    """Count scanned files, extensions, and top directories."""

    project = Path(project_path).resolve()
    total_files = 0
    ext_counts: Counter[str] = Counter()
    dir_counts: Counter[str] = Counter()

    for path in project.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(project)
        parts = rel.parts
        if any(p.startswith(".") for p in parts):
            continue
        if any(p in ignore_dirs for p in parts):
            continue

        ext = path.suffix.lower()
        if ext not in file_extensions:
            continue

        total_files += 1
        ext_counts[ext] += 1

        top_dir = parts[0] if len(parts) > 1 else "root"
        dir_counts[top_dir] += 1

    return total_files, dict(ext_counts), dict(dir_counts)


def _detect_project_profile(extension_counts: dict[str, int]) -> list[str]:
    """Infer high-level project profile from file extensions."""

    profile: list[str] = []
    exts = extension_counts

    if any(ext in exts for ext in (".ts", ".tsx", ".js", ".jsx")):
        profile.append("JavaScript/TypeScript application")
    if any(ext in exts for ext in (".py",)):
        profile.append("Python services/scripts")
    if any(ext in exts for ext in (".css", ".scss", ".html", ".vue", ".svelte")):
        profile.append("Web UI/front-end")
    if any(ext in exts for ext in (".java", ".go", ".rb", ".php", ".rs", ".cs")):
        profile.append("Back-end or polyglot modules")

    if not profile:
        profile.append("General codebase")

    return profile


def _suggest_features(category_counts: dict[str, int], extension_counts: dict[str, int], total_files: int) -> list[str]:
    """Generate practical feature/roadmap suggestions from findings."""

    suggestions: list[str] = []

    if category_counts.get("hardcoded-secret", 0) > 0:
        suggestions.append("Add a secrets-health command to validate required environment variables before deploy.")

    if category_counts.get("todo", 0) >= 5:
        suggestions.append("Introduce a technical debt dashboard command summarizing TODO/FIXME trend per folder.")

    if category_counts.get("large-file", 0) >= 3:
        suggestions.append("Create a refactor roadmap for oversized modules and track progress per sprint.")

    if category_counts.get("skipped-test", 0) > 0:
        suggestions.append("Add a quality gate that blocks release when skipped tests are detected in main branches.")

    has_web_stack = any(ext in extension_counts for ext in (".ts", ".tsx", ".js", ".jsx", ".html", ".css"))
    has_python = ".py" in extension_counts

    if has_web_stack:
        suggestions.append("Add end-to-end smoke checks for core user flows and post a daily pass/fail summary.")

    if has_python:
        suggestions.append("Add automated lint/type checks for Python commands and scheduled jobs.")

    if total_files >= 200:
        suggestions.append("Add a weekly architecture review note generated from scan hotspots to keep roadmap realistic.")

    # Keep output focused and readable.
    deduped: list[str] = []
    for s in suggestions:
        if s not in deduped:
            deduped.append(s)

    if not deduped:
        deduped.append("Add a monthly product-health report combining issue trends, ticket throughput, and top risk areas.")

    return deduped[:6]


def _pick_most_impactful_feature(
    category_counts: dict[str, int],
    extension_counts: dict[str, int],
) -> dict[str, object]:
    """Select one high-impact feature aligned to scan findings and constraints."""

    candidates = [
        {
            "key": "hardcoded-secret",
            "title": "Secrets Health Check Command",
            "description": "Add a command that validates required environment variables before deploy/runtime actions.",
            "weight": 12,
            "tasks": [
                "Define a required-variables manifest in config and environment docs.",
                "Implement a bot command that checks variable presence and basic format.",
                "Return safe, non-secret output (missing names only, never values).",
                "Wire command access to PM/admin roles and add usage guidance.",
                "Add tests for complete, partial, and missing-env scenarios.",
            ],
            "scope_boundaries": [
                "No secret rotation or vault integration.",
                "No automatic environment mutation/fixes.",
                "No deployment pipeline redesign.",
            ],
        },
        {
            "key": "large-file",
            "title": "Module Refactor Tracking Board",
            "description": "Add automated progress tracking for oversized-module refactors to reduce delivery risk.",
            "weight": 8,
            "tasks": [
                "Define thresholds and metadata for large-file refactor tickets.",
                "Generate a compact markdown board from scanner results grouped by area.",
                "Link each item to ticket status and owner for execution visibility.",
                "Add a refresh step to update board after each scan cycle.",
                "Validate board output with existing SideQuest roadmap format.",
            ],
            "scope_boundaries": [
                "No automatic code refactor generation.",
                "No changes to ticket workflow states or role model.",
                "No UI dashboard outside markdown/report files.",
            ],
        },
        {
            "key": "skipped-test",
            "title": "Skipped-Test Quality Gate",
            "description": "Add a quality gate that flags or blocks release readiness when skipped tests are detected.",
            "weight": 9,
            "tasks": [
                "Define release-readiness rules for skipped tests and acceptable exceptions.",
                "Implement scanner aggregation for skipped tests by area and severity.",
                "Expose a command/report that surfaces gate status clearly.",
                "Add override documentation with explicit PM approval trail.",
                "Add tests for pass/fail/override gate behavior.",
            ],
            "scope_boundaries": [
                "No full CI/CD platform migration.",
                "No test framework rewrite.",
                "No performance benchmarking expansion.",
            ],
        },
        {
            "key": "todo",
            "title": "Technical Debt Trend Report",
            "description": "Add a report that tracks TODO/FIXME backlog trends to guide incremental cleanup.",
            "weight": 5,
            "tasks": [
                "Normalize TODO/FIXME finding categories and metadata.",
                "Build a trend summary grouped by folder and age.",
                "Publish the report as markdown alongside roadmap outputs.",
                "Add simple thresholds for warning escalation.",
                "Add tests for trend calculations and markdown rendering.",
            ],
            "scope_boundaries": [
                "No automatic TODO deletion or code edits.",
                "No mandatory deadline enforcement workflow.",
                "No cross-repo aggregation.",
            ],
        },
    ]

    has_web_stack = any(ext in extension_counts for ext in (".ts", ".tsx", ".js", ".jsx", ".html", ".css"))
    has_python = ".py" in extension_counts

    best = None
    best_score = -1

    for candidate in candidates:
        score = category_counts.get(candidate["key"], 0) * candidate["weight"]

        # Slightly favor features aligned to current stack.
        if candidate["key"] == "large-file" and has_web_stack:
            score += 3
        if candidate["key"] in ("hardcoded-secret", "todo", "skipped-test") and has_python:
            score += 2

        if score > best_score:
            best = candidate
            best_score = score

    if not best:
        return {
            "title": "Product Health Baseline Report",
            "description": "Create a baseline health report from current scan findings.",
            "justification": "This keeps improvements scoped to existing project goals by prioritizing measurable risk reduction before adding new product surface area.",
            "tasks": [
                "Aggregate findings by category and directory.",
                "Generate markdown output with prioritized remediation order.",
                "Include owner/status placeholders for execution tracking.",
            ],
            "scope_boundaries": [
                "No architecture rewrite.",
                "No workflow state changes.",
                "No new deployment dependencies.",
            ],
        }

    top_driver = category_counts.get(best["key"], 0)
    justification = (
        f"This is the best choice because it directly targets the highest-impact scan pressure "
        f"for `{best['key']}` ({top_driver} finding(s)) while staying inside current roadmap goals "
        f"of stability, quality, and predictable delivery."
    )

    return {
        "title": best["title"],
        "description": best["description"],
        "justification": justification,
        "tasks": best["tasks"],
        "scope_boundaries": best["scope_boundaries"],
    }


def _build_roadmap_markdown(
    project_path: str,
    output_folder: str,
    scan_source: str,
    total_files: int,
    profile: list[str],
    category_counts: dict[str, int],
    top_dirs: list[tuple[str, int]],
    top_categories: list[tuple[str, int]],
    suggestions: list[str],
    impactful_feature: dict[str, object],
    ticket_count: int,
) -> str:
    """Create a markdown roadmap document."""

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    category_lines = "\n".join([f"- **{cat}**: {count}" for cat, count in top_categories]) or "- No issues found"
    dir_lines = "\n".join([f"- `{d}`: {count} scanned file(s)" for d, count in top_dirs]) or "- No directories scanned"
    profile_lines = "\n".join([f"- {p}" for p in profile])
    suggestions_lines = "\n".join([f"{idx}. {item}" for idx, item in enumerate(suggestions, start=1)])
    feature_tasks = impactful_feature.get("tasks", [])
    feature_scope = impactful_feature.get("scope_boundaries", [])
    feature_tasks_lines = "\n".join([f"1. {task}" for task in feature_tasks]) or "1. No tasks specified"
    feature_scope_lines = "\n".join([f"- {item}" for item in feature_scope]) or "- No boundaries specified"

    hardcoded = category_counts.get("hardcoded-secret", 0)
    empty_catch = category_counts.get("empty-catch", 0)
    debug = category_counts.get("debug", 0)
    todo = category_counts.get("todo", 0)
    large_file = category_counts.get("large-file", 0)
    skipped = category_counts.get("skipped-test", 0)

    return f"""# Project Roadmap: {output_folder}

Generated from automated scan of `{scan_source}` on **{now}**.

## Snapshot

- Scanned files: **{total_files}**
- Generated issue tickets: **{ticket_count}**
- Primary project profile:
{profile_lines}

## Current Hotspots

{category_lines}

## Directory Focus

{dir_lines}

## Suggested Feature Improvements

{suggestions_lines}

## Most Impactful Feature To Add

### Feature

**{impactful_feature.get("title", "N/A")}**

{impactful_feature.get("description", "")}

### Why This Is The Best Choice

{impactful_feature.get("justification", "")}

### Necessary Tasks

{feature_tasks_lines}

### Scope Boundaries

{feature_scope_lines}

## Roadmap (Execution Order)

### Milestone 1: Stability and Risk Control (Week 1)

- Remove all detected hardcoded secrets (**{hardcoded}** finding(s)).
- Fix swallowed exception paths (**{empty_catch}** finding(s)).
- Remove accidental debug statements in runtime code (**{debug}** finding(s)).

### Milestone 2: Code Quality and Delivery Confidence (Week 2)

- Resolve or convert TODO/FIXME backlog (**{todo}** finding(s)).
- Re-enable and stabilize skipped tests (**{skipped}** finding(s)).
- Break down oversized files into maintainable modules (**{large_file}** finding(s)).

### Milestone 3: Product Smoothing and Roadmap Cadence (Week 3+)

- Pick 2 to 3 suggested features above and convert them into tickets.
- Review scan trends weekly and update priorities by impact and effort.
- Keep generated scanner tickets in sync with delivered work to avoid roadmap drift.

## How to Use This Roadmap

1. Load generated tickets from `tickets/{output_folder}/` into Discord.
2. Prioritize Milestone 1 tickets first.
3. Track completion in your normal claim -> review -> close workflow.
4. Re-run scan monthly and compare category counts to validate improvement.
"""


def build_project_roadmap(
    project_path: str,
    output_folder: str,
    scan_source: str | None = None,
    tickets_dir: str = "tickets",
    ignore_dirs: set[str] | None = None,
    file_extensions: set[str] | None = None,
    large_file_threshold: int = DEFAULT_LARGE_FILE_THRESHOLD,
    generate_issue_tickets: bool = True,
) -> RoadmapResult:
    """Scan project and generate roadmap markdown (and optional tickets)."""

    ignore = ignore_dirs or DEFAULT_IGNORE_DIRS
    extensions = file_extensions or DEFAULT_FILE_EXTENSIONS

    issues = scan_directory(
        project_path=project_path,
        ignore_dirs=ignore,
        file_extensions=extensions,
        large_file_threshold=large_file_threshold,
    )

    category_counts: Counter[str] = Counter(issue.category for issue in issues)
    grouped = group_issues(issues) if issues else {}

    generated_files: list[str] = []
    if generate_issue_tickets and grouped:
        generated_files = generate_tickets(grouped, output_folder, tickets_dir)

    total_files, ext_counts, dir_counts = _collect_file_stats(project_path, ignore, extensions)
    profile = _detect_project_profile(ext_counts)

    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    suggestions = _suggest_features(dict(category_counts), ext_counts, total_files)
    impactful_feature = _pick_most_impactful_feature(dict(category_counts), ext_counts)

    out_dir = Path(tickets_dir) / output_folder
    out_dir.mkdir(parents=True, exist_ok=True)
    roadmap_file = out_dir / "ROADMAP.md"

    roadmap_md = _build_roadmap_markdown(
        project_path=project_path,
        output_folder=output_folder,
        scan_source=scan_source or project_path,
        total_files=total_files,
        profile=profile,
        category_counts=dict(category_counts),
        top_dirs=top_dirs,
        top_categories=top_categories,
        suggestions=suggestions,
        impactful_feature=impactful_feature,
        ticket_count=len(generated_files),
    )

    roadmap_file.write_text(roadmap_md.strip() + "\n", encoding="utf-8")

    return RoadmapResult(
        total_files_scanned=total_files,
        total_issues=len(issues),
        total_tickets=len(generated_files),
        roadmap_file=str(roadmap_file),
        generated_ticket_files=generated_files,
        top_categories=top_categories,
        suggested_features=suggestions,
    )
