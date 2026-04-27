"""Project roadmap builder based on full repository analysis.

Scans the entire repository structure, analyzes each component and existing
features, then generates a prioritized 12-week (3-month) development roadmap.
It can also generate scanner ticket files in the same output folder to keep
planning and execution aligned.
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


FEATURE_SIGNATURES: dict[str, tuple[str, ...]] = {
    "Authentication & Accounts": ("auth", "login", "register", "signup", "password", "session"),
    "User Profile": ("profile", "account", "avatar", "settings", "user"),
    "Community & Social": ("community", "thread", "comment", "mention", "share", "report"),
    "Notifications": ("notification", "alerts", "feed", "reminder"),
    "Admin & Moderation": ("admin", "dashboard", "moderation", "rbac", "role", "permission"),
    "Reports & Exports": ("report", "analytics", "stats", "pdf", "export"),
    "Search & Discovery": ("search", "filter", "query", "leaderboard"),
    "Media & Uploads": ("upload", "image", "photo", "video", "attachment"),
    "Integrations & API": ("api", "webhook", "integration", "provider", "client"),
    "Automation & Scheduling": ("cron", "schedule", "worker", "job", "task"),
}


@dataclass
class RoadmapResult:
    """Result object returned by build_project_roadmap."""

    total_files_scanned: int
    total_issues: int
    total_tickets: int
    total_components: int
    roadmap_weeks: int
    roadmap_file: str
    generated_ticket_files: list[str]
    top_categories: list[tuple[str, int]]
    top_components: list[tuple[str, int]]
    detected_features: list[tuple[str, int]]
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


def _infer_component_type(component_name: str, ext_counts: Counter[str]) -> str:
    """Infer component type based on name hints and dominant extensions."""

    name = component_name.lower()
    web_ext = ext_counts.get(".tsx", 0) + ext_counts.get(".ts", 0) + ext_counts.get(".jsx", 0) + ext_counts.get(".js", 0)
    py_ext = ext_counts.get(".py", 0)
    style_ext = ext_counts.get(".css", 0) + ext_counts.get(".scss", 0) + ext_counts.get(".html", 0)

    if any(k in name for k in ("script", "migrations", "migration", "tool", "utils")):
        return "automation"
    if any(k in name for k in ("api", "server", "backend", "bot", "service")):
        return "backend"
    if any(k in name for k in ("client", "frontend", "web", "ui", "pages", "components")):
        return "frontend"
    if web_ext > 0 and py_ext > 0:
        return "full-stack"
    if web_ext + style_ext > py_ext and (web_ext + style_ext) > 0:
        return "frontend"
    if py_ext > 0:
        return "backend"
    return "shared"


def _extract_feature_hits(rel_path: str) -> set[str]:
    """Detect likely implemented features from file paths."""

    value = rel_path.lower()
    hits: set[str] = set()

    for feature_name, keywords in FEATURE_SIGNATURES.items():
        if any(keyword in value for keyword in keywords):
            hits.add(feature_name)

    return hits


def _analyze_repository_components(
    project_path: str,
    ignore_dirs: set[str],
    file_extensions: set[str],
    issues_by_component: dict[str, int],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Analyze repository structure and each top-level component."""

    project = Path(project_path).resolve()
    buckets: dict[str, dict[str, object]] = {}
    feature_component_counts: Counter[str] = Counter()

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

        component_name = parts[0] if len(parts) > 1 else "root"
        rel_path = str(rel).replace("\\", "/")

        if component_name not in buckets:
            buckets[component_name] = {
                "name": component_name,
                "file_count": 0,
                "ext_counts": Counter(),
                "sample_files": [],
                "features": set(),
            }

        comp = buckets[component_name]
        comp["file_count"] += 1
        comp["ext_counts"][ext] += 1

        sample_files = comp["sample_files"]
        if len(sample_files) < 5:
            sample_files.append(rel_path)

        comp["features"].update(_extract_feature_hits(rel_path))

    components: list[dict[str, object]] = []
    for component_name, data in buckets.items():
        file_count = int(data["file_count"])
        issue_count = issues_by_component.get(component_name, 0)
        issue_density = issue_count / max(file_count, 1)

        base_health = 100 - int(issue_density * 35) - min(15, file_count // 20)
        if issue_count == 0:
            base_health += 4
        health_score = max(35, min(100, base_health))

        ext_counts = data["ext_counts"]
        dominant_exts = [ext for ext, _ in ext_counts.most_common(3)]
        features = sorted(data["features"])
        for feature in features:
            feature_component_counts[feature] += 1

        components.append(
            {
                "name": component_name,
                "type": _infer_component_type(component_name, ext_counts),
                "file_count": file_count,
                "issue_count": issue_count,
                "health_score": health_score,
                "dominant_exts": dominant_exts,
                "features": features,
                "sample_files": data["sample_files"],
            }
        )

    components.sort(key=lambda c: (int(c["issue_count"]), int(c["file_count"])), reverse=True)
    return components, dict(feature_component_counts)


def _suggest_features(
    category_counts: dict[str, int],
    extension_counts: dict[str, int],
    total_files: int,
    feature_component_counts: dict[str, int],
) -> list[str]:
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

    if feature_component_counts.get("Community & Social", 0) > 0:
        suggestions.append("Improve in-app moderation tooling and automate report triage for community features.")

    if feature_component_counts.get("Reports & Exports", 0) > 0:
        suggestions.append("Add scheduled exports and role-based report views to reduce manual PM operations.")

    if total_files >= 200:
        suggestions.append("Add a weekly architecture review note generated from scan hotspots to keep roadmap realistic.")

    deduped: list[str] = []
    for item in suggestions:
        if item not in deduped:
            deduped.append(item)

    if not deduped:
        deduped.append("Add a monthly product-health report combining issue trends, ticket throughput, and top risk areas.")

    return deduped[:8]


def _pick_most_impactful_feature(
    category_counts: dict[str, int],
    extension_counts: dict[str, int],
    feature_component_counts: dict[str, int],
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
            "title": "Component Refactor Progress Board",
            "description": "Add automated progress tracking for oversized-module refactors by component to reduce delivery risk.",
            "weight": 8,
            "tasks": [
                "Define thresholds and metadata for large-file refactor tickets.",
                "Generate a compact markdown board grouped by component risk.",
                "Link each item to ticket status and owner for execution visibility.",
                "Add a refresh step to update board after each scan cycle.",
                "Validate board output with existing roadmap ticket format.",
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
            "description": "Add a report that tracks TODO/FIXME backlog trends by component to guide cleanup.",
            "weight": 5,
            "tasks": [
                "Normalize TODO/FIXME finding categories and metadata.",
                "Build a trend summary grouped by component and age.",
                "Publish the report as markdown alongside roadmap outputs.",
                "Add thresholds for warning escalation and PM follow-up.",
                "Add tests for trend calculations and markdown rendering.",
            ],
            "scope_boundaries": [
                "No automatic TODO deletion or code edits.",
                "No mandatory deadline enforcement workflow.",
                "No cross-repo aggregation.",
            ],
        },
        {
            "key": "community",
            "title": "Community Moderation Automation",
            "description": "Improve community safety by automating report triage and moderation workload visibility.",
            "weight": 7,
            "tasks": [
                "Add moderation queue summaries grouped by risk level.",
                "Track report turnaround metrics and stale moderation items.",
                "Expose a weekly moderation health note for PM review.",
                "Add permission checks for admin-only moderation actions.",
                "Add tests for role restrictions and queue state transitions.",
            ],
            "scope_boundaries": [
                "No ML moderation classifier rollout.",
                "No policy rewrite or legal policy changes.",
                "No external moderation platform migration.",
            ],
        },
    ]

    has_web_stack = any(ext in extension_counts for ext in (".ts", ".tsx", ".js", ".jsx", ".html", ".css"))
    has_python = ".py" in extension_counts

    best = None
    best_score = -1

    for candidate in candidates:
        if candidate["key"] == "community":
            score = feature_component_counts.get("Community & Social", 0) * candidate["weight"]
        else:
            score = category_counts.get(candidate["key"], 0) * candidate["weight"]

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
            "justification": "This keeps improvements scoped to current goals by prioritizing measurable risk reduction before adding new product surface area.",
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

    if best["key"] == "community":
        top_driver = feature_component_counts.get("Community & Social", 0)
        driver_label = "community components"
    else:
        top_driver = category_counts.get(best["key"], 0)
        driver_label = f"{best['key']} findings"

    justification = (
        f"This is the best choice because it directly targets the highest-impact scan pressure "
        f"for {driver_label} ({top_driver}) while keeping delivery scope within the next three months."
    )

    return {
        "title": best["title"],
        "description": best["description"],
        "justification": justification,
        "tasks": best["tasks"],
        "scope_boundaries": best["scope_boundaries"],
    }


def _build_twelve_week_plan(
    top_components: list[dict[str, object]],
    category_counts: dict[str, int],
    impactful_feature: dict[str, object],
) -> list[dict[str, object]]:
    """Build a 12-week implementation plan with progress checkpoints."""

    component_names = [str(c["name"]) for c in top_components[:4]]
    while len(component_names) < 4:
        component_names.append("core")

    impactful_title = str(impactful_feature.get("title", "Top priority feature"))

    weekly_plan = [
        {
            "week": 1,
            "target_progress": 8,
            "focus": "Repository baseline and architecture map",
            "components": [component_names[0], component_names[1]],
            "deliverable": "Finalize component owners, risks, and acceptance criteria for each area.",
        },
        {
            "week": 2,
            "target_progress": 16,
            "focus": "Most impactful feature discovery and scope lock",
            "components": [component_names[0], component_names[1]],
            "deliverable": f"Define final scope, success metrics, and execution plan for {impactful_title}.",
        },
        {
            "week": 3,
            "target_progress": 24,
            "focus": "Most impactful feature build - core implementation",
            "components": [component_names[0], component_names[1]],
            "deliverable": f"Build the core workflow and internal interfaces for {impactful_title}.",
        },
        {
            "week": 4,
            "target_progress": 32,
            "focus": "Most impactful feature build - integration",
            "components": [component_names[0], component_names[1], component_names[2]],
            "deliverable": f"Integrate {impactful_title} with permissions, data flow, and error handling across target components.",
        },
        {
            "week": 5,
            "target_progress": 40,
            "focus": "Most impactful feature hardening and standout polish",
            "components": [component_names[0], component_names[1], component_names[2]],
            "deliverable": f"Complete QA-ready polish, rollout notes, and differentiation details so {impactful_title} stands out in release demos.",
        },
        {
            "week": 6,
            "target_progress": 50,
            "focus": "Component sprint 2",
            "components": [component_names[1]],
            "deliverable": "Ship second high-risk component improvements with regression checklist.",
        },
        {
            "week": 7,
            "target_progress": 60,
            "focus": "Quality gates and reliability",
            "components": [component_names[2], "tests"],
            "deliverable": f"Stabilize skipped tests ({category_counts.get('skipped-test', 0)}) and enforce release-readiness checks.",
        },
        {
            "week": 8,
            "target_progress": 70,
            "focus": "Refactor oversized modules",
            "components": [component_names[2], component_names[3]],
            "deliverable": f"Reduce oversized-module pressure ({category_counts.get('large-file', 0)}) and document new boundaries.",
        },
        {
            "week": 9,
            "target_progress": 80,
            "focus": "Most impactful feature build - phase 1",
            "components": [component_names[0], component_names[1]],
            "deliverable": f"Implement core slice of {impactful_title} with internal validation.",
        },
        {
            "week": 10,
            "target_progress": 90,
            "focus": "Most impactful feature build - phase 2",
            "components": [component_names[0], component_names[1]],
            "deliverable": f"Complete integration, permission checks, and rollout notes for {impactful_title}.",
        },
        {
            "week": 11,
            "target_progress": 95,
            "focus": "UAT, bug bash, and release prep",
            "components": ["cross-component"],
            "deliverable": "Run full regression, fix blockers, and finalize release checklist.",
        },
        {
            "week": 12,
            "target_progress": 100,
            "focus": "Release and roadmap refresh",
            "components": ["cross-component"],
            "deliverable": "Release improvements, compare baseline vs endline metrics, and generate next-quarter roadmap seed.",
        },
    ]

    return weekly_plan


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
    components: list[dict[str, object]],
    feature_component_counts: dict[str, int],
    weekly_plan: list[dict[str, object]],
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

    component_lines = []
    for component in components[:10]:
        features = component["features"] or ["General"]
        feature_text = ", ".join(features[:4])
        exts = ", ".join(component["dominant_exts"]) if component["dominant_exts"] else "n/a"
        component_lines.append(
            f"- **{component['name']}** ({component['type']}): {component['file_count']} file(s), "
            f"{component['issue_count']} issue(s), health {component['health_score']}/100, "
            f"stack [{exts}], features [{feature_text}]"
        )
    component_block = "\n".join(component_lines) or "- No components detected"

    feature_inventory = sorted(feature_component_counts.items(), key=lambda x: x[1], reverse=True)
    feature_inventory_lines = "\n".join([f"- **{name}**: present in {count} component(s)" for name, count in feature_inventory[:10]])
    if not feature_inventory_lines:
        feature_inventory_lines = "- No explicit feature signatures detected"

    month_one_progress = weekly_plan[3]["target_progress"] if len(weekly_plan) >= 4 else 0
    month_two_progress = weekly_plan[7]["target_progress"] if len(weekly_plan) >= 8 else 0
    month_three_progress = weekly_plan[11]["target_progress"] if len(weekly_plan) >= 12 else 100

    week_lines = []
    for item in weekly_plan:
        components_line = ", ".join(item["components"])
        week_lines.append(
            f"### Week {item['week']} (Target Progress: {item['target_progress']}%)\n"
            f"- Focus: {item['focus']}\n"
            f"- Components: {components_line}\n"
            f"- Deliverable: {item['deliverable']}"
        )
    weekly_block = "\n\n".join(week_lines)

    return f"""# Project Roadmap: {output_folder}

Generated from automated scan of `{scan_source}` on **{now}**.

## Snapshot

- Scanned files: **{total_files}**
- Detected components: **{len(components)}**
- Generated issue tickets: **{ticket_count}**
- Roadmap horizon: **12 weeks (3 months)**
- Primary project profile:
{profile_lines}

## Repository Structure and Component Analysis

{component_block}

## Current Feature Inventory

{feature_inventory_lines}

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

## 12-Week Development Roadmap (3 Months)

### Month Targets

- **Month 1 (Weeks 1-4):** baseline mapping then accelerated standout-feature build, target **{month_one_progress}%** completion.
- **Month 2 (Weeks 5-8):** standout-feature hardening followed by reliability and component stabilization, target **{month_two_progress}%** completion.
- **Month 3 (Weeks 9-12):** impactful feature delivery and release readiness, target **{month_three_progress}%** completion.

{weekly_block}

## How to Use This Roadmap

1. Load generated tickets from `tickets/{output_folder}/` into Discord.
2. Prioritize Weeks 1-4 first to reduce technical risk.
3. Track weekly progress target completion in your claim -> review -> close workflow.
4. Re-run scan monthly and compare category/component metrics to validate improvement.
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
    skip_code_issues: bool = False,
    write_roadmap_file: bool = True,
) -> RoadmapResult:
    """Scan project and generate roadmap markdown (and optional tickets)."""

    ignore = ignore_dirs or DEFAULT_IGNORE_DIRS
    extensions = file_extensions or DEFAULT_FILE_EXTENSIONS

    issues: list = []
    if not skip_code_issues:
        issues = scan_directory(
            project_path=project_path,
            ignore_dirs=ignore,
            file_extensions=extensions,
            large_file_threshold=large_file_threshold,
        )

    issues_by_component: Counter[str] = Counter()
    for issue in issues:
        parts = Path(issue.file_path).parts
        component_name = parts[0] if len(parts) > 1 else "root"
        issues_by_component[component_name] += 1

    category_counts: Counter[str] = Counter(issue.category for issue in issues)
    grouped = group_issues(issues) if issues else {}

    generated_files: list[str] = []
    if generate_issue_tickets and grouped and not skip_code_issues:
        generated_files = generate_tickets(grouped, output_folder, tickets_dir)

    total_files, ext_counts, dir_counts = _collect_file_stats(project_path, ignore, extensions)
    profile = _detect_project_profile(ext_counts)

    components, feature_component_counts = _analyze_repository_components(
        project_path=project_path,
        ignore_dirs=ignore,
        file_extensions=extensions,
        issues_by_component=dict(issues_by_component),
    )

    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    suggestions = _suggest_features(dict(category_counts), ext_counts, total_files, feature_component_counts)
    impactful_feature = _pick_most_impactful_feature(dict(category_counts), ext_counts, feature_component_counts)
    weekly_plan = _build_twelve_week_plan(components, dict(category_counts), impactful_feature)

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
        components=components,
        feature_component_counts=feature_component_counts,
        weekly_plan=weekly_plan,
    )

    if write_roadmap_file:
        roadmap_file.write_text(roadmap_md.strip() + "\n", encoding="utf-8")

    top_components = [(str(c["name"]), int(c["issue_count"])) for c in components[:8]]
    detected_features = sorted(feature_component_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    return RoadmapResult(
        total_files_scanned=total_files,
        total_issues=len(issues),
        total_tickets=len(generated_files),
        total_components=len(components),
        roadmap_weeks=len(weekly_plan),
        roadmap_file=str(roadmap_file),
        generated_ticket_files=generated_files,
        top_categories=top_categories,
        top_components=top_components,
        detected_features=detected_features,
        suggested_features=suggestions,
    )
