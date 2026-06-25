"""Concise project planner — AI-powered MVP ticket generation with CTA.

Takes a natural-language project description, calls the configured AI model
with concise-planning rules, and produces MVP-scoped ticket markdown files
with a Call-to-Action section on each ticket.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt that embeds the concise-planning skill
# ---------------------------------------------------------------------------

_PLAN_SYSTEM_PROMPT = """\
You are a concise project planner. Your job is to convert a project description
into a set of MVP-scoped development tickets.

PLANNING RULES (MANDATORY):
1. Each ticket solves ONE problem. Never use "and" in ticket titles.
2. MVP test — a feature belongs in MVP only if ALL are true:
   a. Users interact with it directly.
   b. It works without other unbuilt features.
   c. You can demo it in under 60 seconds.
   d. One person can finish it in one sitting.
3. Cap "What to Fix" at 5-8 concrete, actionable steps.
4. Keep acceptance criteria binary — pass or fail, no judgment calls.
5. Every ticket MUST include a CTA (Call to Action): one clear sentence
   stating who should do what next (e.g. "Developer claims this first",
   "Designer reviews mockup before development starts").
6. Order tickets by dependency: blockers first. Mark true blockers as priority.
7. Do NOT mix bug fixes with new features in one ticket.
8. Keep related files to one area of the codebase.

TICKET AREAS (use for the "area" field):
- "client" — public-facing UI, client components
- "admin"  — admin dashboard
- "server" — server actions, API routes, backend logic
- "utils"  — utilities, seeds, scripts, infrastructure

OUTPUT FORMAT:
Return ONLY a valid JSON object with this exact structure (no markdown fences,
no extra text before or after):

{
  "project_summary": "One paragraph summarizing the MVP scope.",
  "tickets": [
    {
      "area": "client",
      "slug": "login-register",
      "title": "Implement Login/Register Feature",
      "priority": true,
      "problem": "Users cannot create accounts...",
      "related_files": ["components/auth/LoginForm.tsx", "actions/auth.ts"],
      "what_to_fix": [
        "Create login page with email/password form",
        "Add form validation with Zod schema",
        "Create signUp server action"
      ],
      "acceptance_criteria": [
        "Users can sign up with email/password",
        "Session persists across page navigation"
      ],
      "cta": "Developer: Claim this ticket first — it blocks all user-facing features.",
      "blocks": []
    }
  ]
}

CRITICAL: Output ONLY the JSON object. No markdown code fences. No preamble.
No explanatory text. Just the raw JSON.
"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PlannedTicket:
    """One MVP-scoped ticket produced by the planner."""

    area: str
    slug: str
    title: str
    priority: bool
    problem: str
    related_files: list[str]
    what_to_fix: list[str]
    acceptance_criteria: list[str]
    cta: str
    blocks: list[str] = field(default_factory=list)


@dataclass
class PlanResult:
    """Full result of a planning run."""

    project_summary: str
    tickets: list[PlannedTicket]
    plan_file: str
    ticket_files: list[str]
    folder: str


# ---------------------------------------------------------------------------
# AI interaction
# ---------------------------------------------------------------------------

def generate_concise_plan(
    ai_client,
    description: str,
    *,
    context: str = "",
    max_tickets: int = 8,
    profile: str = "answer",
) -> str:
    """Call the AI model to generate a concise plan as raw JSON text.

    Parameters
    ----------
    ai_client:
        Configured NvidiaAIClient instance.
    description:
        Natural-language project description.
    context:
        Optional additional context (tech stack, constraints).
    max_tickets:
        Maximum number of tickets the AI should generate.
    profile:
        AI profile to use for the request.

    Returns
    -------
    str
        Raw JSON text from the AI response.
    """
    user_prompt = f"PROJECT DESCRIPTION:\n{description}\n"
    if context:
        user_prompt += f"\nADDITIONAL CONTEXT:\n{context}\n"
    user_prompt += (
        f"\nGenerate up to {max_tickets} MVP-scoped tickets for this project. "
        "Follow all planning rules strictly. Return ONLY the JSON object."
    )

    return ai_client.chat(
        user_prompt,
        system=_PLAN_SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=4096,
        top_p=0.9,
        enable_thinking=True,
        profile=profile,
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _extract_json_from_response(raw: str) -> str:
    """Extract JSON from AI response, stripping markdown fences if present."""

    # Strip markdown code fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    # Try to find JSON object boundaries
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in AI response")

    # Find the matching closing brace
    depth = 0
    for i, char in enumerate(cleaned[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start:i + 1]

    # Fallback: return from first { to end
    return cleaned[start:]


def parse_ai_plan_response(raw: str) -> tuple[str, list[PlannedTicket]]:
    """Parse the AI JSON response into validated ticket objects.

    Parameters
    ----------
    raw:
        Raw text response from the AI model.

    Returns
    -------
    tuple[str, list[PlannedTicket]]
        Project summary and list of parsed tickets.

    Raises
    ------
    ValueError
        If the response cannot be parsed into valid tickets.
    """
    json_text = _extract_json_from_response(raw)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("AI response is not a JSON object")

    project_summary = str(data.get("project_summary", "No summary provided."))
    raw_tickets = data.get("tickets", [])

    if not isinstance(raw_tickets, list):
        raise ValueError("'tickets' field is not a list")

    if not raw_tickets:
        raise ValueError("AI generated zero tickets")

    tickets: list[PlannedTicket] = []
    valid_areas = {"client", "admin", "server", "utils"}

    for i, raw_ticket in enumerate(raw_tickets):
        if not isinstance(raw_ticket, dict):
            logger.warning("Skipping non-dict ticket at index %d", i)
            continue

        area = str(raw_ticket.get("area", "client")).lower()
        if area not in valid_areas:
            area = "client"

        slug = str(raw_ticket.get("slug", f"ticket-{i + 1}")).lower()
        slug = re.sub(r"[^a-z0-9-]", "-", slug).strip("-")
        slug = re.sub(r"-+", "-", slug)
        if not slug:
            slug = f"ticket-{i + 1}"

        title = str(raw_ticket.get("title", f"Ticket {i + 1}"))
        priority = bool(raw_ticket.get("priority", False))
        problem = str(raw_ticket.get("problem", ""))
        related_files = [str(f) for f in raw_ticket.get("related_files", []) if f]
        what_to_fix = [str(s) for s in raw_ticket.get("what_to_fix", []) if s]
        acceptance_criteria = [str(c) for c in raw_ticket.get("acceptance_criteria", []) if c]
        cta = str(raw_ticket.get("cta", "Claim this ticket and start working."))
        blocks = [str(b) for b in raw_ticket.get("blocks", []) if b]

        if not problem:
            problem = f"This ticket addresses: {title}"

        if not what_to_fix:
            what_to_fix = ["Implement the feature described in the problem section."]

        if not acceptance_criteria:
            acceptance_criteria = ["The feature works as described in the problem section."]

        tickets.append(PlannedTicket(
            area=area,
            slug=slug,
            title=title,
            priority=priority,
            problem=problem,
            related_files=related_files,
            what_to_fix=what_to_fix,
            acceptance_criteria=acceptance_criteria,
            cta=cta,
            blocks=blocks,
        ))

    if not tickets:
        raise ValueError("All tickets were invalid after parsing")

    return project_summary, tickets


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------

def _ticket_to_markdown(ticket: PlannedTicket) -> str:
    """Convert a PlannedTicket to the standard ticket markdown format."""

    lines: list[str] = [f"# {ticket.title}", ""]

    if ticket.priority:
        lines.extend(["**[PRIORITY]**", ""])

    lines.extend(["## Problem", "", ticket.problem, ""])

    lines.append("## Potentially Related Files")
    lines.append("")
    if ticket.related_files:
        for f in ticket.related_files:
            lines.append(f"- `{f}`")
    else:
        lines.append("- *(to be determined during implementation)*")
    lines.append("")

    lines.append("## What to Fix")
    lines.append("")
    for i, step in enumerate(ticket.what_to_fix, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    lines.append("## Acceptance Criteria")
    lines.append("")
    for criterion in ticket.acceptance_criteria:
        lines.append(f"- {criterion}")
    lines.append("")

    lines.append("## Call to Action")
    lines.append("")
    lines.append(f"**→** {ticket.cta}")
    lines.append("")

    return "\n".join(lines)


def write_plan_tickets(
    tickets: list[PlannedTicket],
    folder: str,
    tickets_dir: str = "tickets",
) -> list[str]:
    """Write ticket markdown files to disk.

    Parameters
    ----------
    tickets:
        List of planned tickets to write.
    folder:
        Subfolder name within tickets_dir.
    tickets_dir:
        Root tickets directory (default: "tickets").

    Returns
    -------
    list[str]
        Absolute paths of generated ticket files.
    """
    out_dir = Path(tickets_dir) / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []

    for ticket in tickets:
        filename = f"{ticket.area}-{ticket.slug}.md"
        filepath = out_dir / filename
        content = _ticket_to_markdown(ticket)
        filepath.write_text(content, encoding="utf-8")
        generated.append(str(filepath))
        logger.info("Wrote ticket: %s", filepath)

    return generated


def build_plan_summary(
    project_summary: str,
    tickets: list[PlannedTicket],
    folder: str,
    description: str,
    tickets_dir: str = "tickets",
) -> str:
    """Generate a PLAN.md summary file and return its path.

    Parameters
    ----------
    project_summary:
        AI-generated project summary.
    tickets:
        All planned tickets.
    folder:
        Output folder name.
    description:
        Original user description.
    tickets_dir:
        Root tickets directory.

    Returns
    -------
    str
        Path to the generated PLAN.md file.
    """
    out_dir = Path(tickets_dir) / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    priority_tickets = [t for t in tickets if t.priority]
    normal_tickets = [t for t in tickets if not t.priority]
    ordered = priority_tickets + normal_tickets

    # Build ticket index
    index_lines: list[str] = []
    for i, ticket in enumerate(ordered, 1):
        priority_tag = " 🔴" if ticket.priority else ""
        index_lines.append(
            f"| {i} | [{ticket.title}]({ticket.area}-{ticket.slug}.md){priority_tag} "
            f"| `{ticket.area}` | {ticket.cta} |"
        )
    index_block = "\n".join(index_lines)

    # Build dependency notes
    dep_lines: list[str] = []
    for ticket in ordered:
        if ticket.blocks:
            blocked_list = ", ".join(ticket.blocks)
            dep_lines.append(f"- **{ticket.title}** blocks → {blocked_list}")
    dep_block = "\n".join(dep_lines) if dep_lines else "No explicit dependencies identified."

    plan_md = f"""\
# Concise Plan: {folder}

Generated on **{now}** via `/plan-project`.

## Project Overview

{project_summary}

## Original Description

> {description[:1000]}

## MVP Scope

- **Total tickets:** {len(tickets)}
- **Priority tickets:** {len(priority_tickets)}
- **Standard tickets:** {len(normal_tickets)}

## Ticket Index

| # | Ticket | Area | Call to Action |
|---|--------|------|----------------|
{index_block}

## Dependencies

{dep_block}

## How to Use This Plan

1. Review tickets in `tickets/{folder}/` and adjust scope if needed.
2. Load into Discord: `/load-tickets {folder} #your-channel`
3. Developers claim tickets with `/claim` in each thread.
4. Follow the CTA on each ticket for the recommended next step.
5. Use `/resolved` when done, `/reviewed` for QA approval.
"""

    plan_path = out_dir / "PLAN.md"
    plan_path.write_text(plan_md, encoding="utf-8")
    logger.info("Wrote plan summary: %s", plan_path)
    return str(plan_path)
