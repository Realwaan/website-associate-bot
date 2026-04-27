"""PDF brief scanner for website/project planning uploads.

This module extracts text from a PDF design brief, asks the configured AI
provider to structure the findings, and writes loadable roadmap/ticket files
into the bot's tickets/ folder.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

from ai_client import AIClientError, NvidiaAIClient

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - dependency guard
    PdfReader = None  # type: ignore[assignment]
    _PYPDF_IMPORT_ERROR = exc
else:  # pragma: no cover - import success path
    _PYPDF_IMPORT_ERROR = None


@dataclass
class PDFScanResult:
    """Structured result returned after scanning a design brief PDF."""

    pdf_name: str
    pages_scanned: int
    chars_extracted: int
    project_name: str
    summary: str
    roadmap_file: str
    brief_file: str
    generated_ticket_files: list[str]
    design_system: dict[str, Any]
    pages: list[dict[str, Any]]
    features: list[str]
    wireframes: list[str]
    open_questions: list[str]


def _slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "item"


def _safe_folder_name(value: str) -> str:
    cleaned = _slugify(value.replace(".pdf", ""))
    return cleaned or "pdf-brief"


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, count=1, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError as exc:
                raise AIClientError(f"AI response was not valid JSON: {exc}") from exc
        else:
            raise AIClientError("AI response was not valid JSON.")

    if not isinstance(data, dict):
        raise AIClientError("AI response JSON must be an object.")
    return data


def extract_pdf_text(pdf_path: str) -> tuple[int, str]:
    """Extract selectable text from each PDF page.

    Returns a tuple of (page_count, extracted_text).
    """
    if PdfReader is None:
        raise AIClientError(
            "PDF support is unavailable. Install the `pypdf` package to enable `/scan-pdf`."
        ) from _PYPDF_IMPORT_ERROR

    reader = PdfReader(pdf_path)
    parts: list[str] = []

    for page in reader.pages:
        text = ""
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        if text.strip():
            parts.append(text.strip())

    return len(reader.pages), "\n\n".join(parts).strip()


def _trim_text_for_prompt(text: str, max_chars: int = 28000) -> str:
    if len(text) <= max_chars:
        return text

    head = text[:20000].rstrip()
    tail = text[-6000:].lstrip()
    return f"{head}\n\n[... PDF content truncated for prompt size ...]\n\n{tail}"


def _build_prompt(pdf_name: str, extracted_text: str, page_count: int) -> str:
    brief_excerpt = _trim_text_for_prompt(extracted_text)
    return (
        "You are analyzing a website/product design brief PDF for a Discord project manager. "
        "Convert the PDF into a structured implementation plan for building the website.\n\n"
        "Return valid JSON only. Do not use markdown fences or extra commentary.\n"
        "Schema:\n"
        "{\n"
        '  "project_name": "string",\n'
        '  "summary": "string",\n'
        '  "design_system": {\n'
        '    "logo": "string",\n'
        '    "fonts": ["string"],\n'
        '    "color_palette": ["string"],\n'
        '    "visual_tone": "string",\n'
        '    "notes": ["string"]\n'
        "  },\n"
        '  "pages": [{"name": "string", "purpose": "string", "sections": ["string"], "notes": ["string"]}],\n'
        '  "features": ["string"],\n'
        '  "wireframes": ["string"],\n'
        '  "open_questions": ["string"],\n'
        '  "roadmap_markdown": "string",\n'
        '  "tickets": [\n'
        "    {\n"
        '      "title": "string",\n'
        '      "priority": "low|medium|high|critical",\n'
        '      "problem": "string",\n'
        '      "related_files": ["string"],\n'
        '      "what_to_fix": ["string"],\n'
        '      "acceptance_criteria": ["string"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Guidelines:\n"
        "- Focus on a website build or redesign workflow, not codebase issues.\n"
        "- Make tickets actionable and scoped so each one can be loaded into a Discord thread.\n"
        "- Create 5 to 10 tickets covering branding, layout, responsive behavior, page sections, content structure, and any interactions implied by the PDF.\n"
        "- Use the PDF details to infer logo, fonts, color palette, features, mockups, and wireframes.\n"
        "- If the PDF is image-heavy or ambiguous, record that in open_questions.\n"
        "- Keep acceptance criteria concrete and testable.\n\n"
        f"PDF file: {pdf_name}\n"
        f"Pages scanned: {page_count}\n\n"
        "PDF content:\n"
        f"<<<PDF_TEXT_START\n{brief_excerpt}\nPDF_TEXT_END>>>"
    )


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _render_brief_markdown(data: dict[str, Any], pdf_name: str, page_count: int, chars_extracted: int) -> str:
    project_name = str(data.get("project_name") or Path(pdf_name).stem).strip()
    summary = str(data.get("summary") or "").strip() or "No summary was generated."
    design_system = data.get("design_system") if isinstance(data.get("design_system"), dict) else {}
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    features = _normalize_list(data.get("features"))
    wireframes = _normalize_list(data.get("wireframes"))
    open_questions = _normalize_list(data.get("open_questions"))

    lines = [
        f"# {project_name}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Source PDF",
        "",
        f"- File: `{pdf_name}`",
        f"- Pages scanned: {page_count}",
        f"- Extracted text characters: {chars_extracted}",
        "",
        "## Design System",
        "",
        f"- Logo: {str(design_system.get('logo') or 'Not specified')}",
        f"- Fonts: {', '.join(_normalize_list(design_system.get('fonts'))) or 'Not specified'}",
        f"- Color Palette: {', '.join(_normalize_list(design_system.get('color_palette'))) or 'Not specified'}",
        f"- Visual Tone: {str(design_system.get('visual_tone') or 'Not specified')}",
    ]

    design_notes = _normalize_list(design_system.get("notes"))
    if design_notes:
        lines.extend(["- Notes:"] + [f"  - {note}" for note in design_notes])

    lines.extend(["", "## Pages", ""])
    if pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            name = str(page.get("name") or "Page").strip()
            purpose = str(page.get("purpose") or "").strip() or "Not specified"
            sections = ", ".join(_normalize_list(page.get("sections"))) or "Not specified"
            notes = ", ".join(_normalize_list(page.get("notes"))) or "Not specified"
            lines.extend([
                f"- **{name}**",
                f"  - Purpose: {purpose}",
                f"  - Sections: {sections}",
                f"  - Notes: {notes}",
            ])
    else:
        lines.append("- No page breakdown was generated.")

    lines.extend(["", "## Features", ""])
    if features:
        lines.extend([f"- {item}" for item in features])
    else:
        lines.append("- No feature list was generated.")

    lines.extend(["", "## Wireframes / Mockups", ""])
    if wireframes:
        lines.extend([f"- {item}" for item in wireframes])
    else:
        lines.append("- No wireframe notes were generated.")

    lines.extend(["", "## Open Questions", ""])
    if open_questions:
        lines.extend([f"- {item}" for item in open_questions])
    else:
        lines.append("- No open questions were generated.")

    return "\n".join(lines).strip() + "\n"


def _render_ticket_markdown(ticket: dict[str, Any], pdf_name: str) -> str:
    title = str(ticket.get("title") or "Website Build Ticket").strip()
    priority = str(ticket.get("priority") or "").strip().lower()
    problem = str(ticket.get("problem") or "").strip() or "This ticket was generated from the uploaded PDF brief."
    related_files = _normalize_list(ticket.get("related_files")) or [f"PDF brief: {pdf_name}"]
    what_to_fix = _normalize_list(ticket.get("what_to_fix")) or ["Turn the PDF brief into an implementation-ready task."]
    acceptance_criteria = _normalize_list(ticket.get("acceptance_criteria")) or ["The scoped work is implemented and reviewed."]

    priority_line = ""
    if priority in {"high", "critical"}:
        priority_label = "CRITICAL" if priority == "critical" else "PRIORITY"
        priority_line = f"\n**[{priority_label}]**\n"

    related_lines = "\n".join(f"- {item}" for item in related_files)
    fix_lines = "\n".join(f"{idx}. {item}" for idx, item in enumerate(what_to_fix, start=1))
    criteria_lines = "\n".join(f"- {item}" for item in acceptance_criteria)

    return f"""# {title}{priority_line}
## Problem

{problem}

## Potentially Related Files

{related_lines}

## What to Fix

{fix_lines}

## Acceptance Criteria

{criteria_lines}
""".strip() + "\n"


def scan_pdf_brief(
    pdf_path: str,
    output_folder: str,
    tickets_dir: str,
    ai_client: NvidiaAIClient,
) -> PDFScanResult:
    """Analyze a design brief PDF and generate roadmap/ticket markdown files."""

    pdf_file = Path(pdf_path)
    if not pdf_file.exists() or not pdf_file.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not ai_client.is_configured():
        raise AIClientError(
            "NVIDIA AI is not configured. Set NVIDIA_API_KEY, NVIDIA_MODEL, and NVIDIA_INVOKE_URL."
        )

    page_count, extracted_text = extract_pdf_text(str(pdf_file))
    if not extracted_text.strip():
        raise AIClientError(
            "No extractable text was found in the PDF. This feature works best on text-based briefs or PDFs with selectable text."
        )

    prompt = _build_prompt(pdf_file.name, extracted_text, page_count)
    analysis_text = ai_client.chat(
        prompt,
        max_tokens=4096,
        temperature=0.2,
        top_p=0.9,
        enable_thinking=False,
    )
    data = _parse_json_response(analysis_text)

    out_folder = _safe_folder_name(output_folder)
    out_path = Path(tickets_dir) / out_folder
    out_path.mkdir(parents=True, exist_ok=True)

    project_name = str(data.get("project_name") or pdf_file.stem).strip() or pdf_file.stem
    summary = str(data.get("summary") or "").strip() or "No summary was generated."
    design_system = data.get("design_system") if isinstance(data.get("design_system"), dict) else {}
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    features = _normalize_list(data.get("features"))
    wireframes = _normalize_list(data.get("wireframes"))
    open_questions = _normalize_list(data.get("open_questions"))
    roadmap_markdown = str(data.get("roadmap_markdown") or "").strip()
    if not roadmap_markdown:
        roadmap_markdown = (
            f"# {project_name} Roadmap\n\n"
            "## Phase 1: Brand and Structure\n"
            "- Confirm logo, palette, and font choices.\n"
            "- Lock the core page list and wireframe hierarchy.\n\n"
            "## Phase 2: Core Pages\n"
            "- Build the homepage and primary marketing pages.\n"
            "- Implement content sections and responsive layout.\n\n"
            "## Phase 3: Refinement\n"
            "- Polish interactions, accessibility, and final content.\n"
        )
    if not roadmap_markdown.lstrip().startswith("#"):
        roadmap_markdown = f"# {project_name} Roadmap\n\n{roadmap_markdown}"

    brief_markdown = _render_brief_markdown(data, pdf_file.name, page_count, len(extracted_text))
    brief_file = out_path / "PDF_BRIEF.md"
    roadmap_file = out_path / "ROADMAP.md"
    brief_file.write_text(brief_markdown, encoding="utf-8")
    roadmap_file.write_text(roadmap_markdown.rstrip() + "\n", encoding="utf-8")

    generated_ticket_files: list[str] = []
    tickets = data.get("tickets") if isinstance(data.get("tickets"), list) else []
    generated_names: set[str] = set()

    for idx, ticket in enumerate(tickets, start=1):
        if not isinstance(ticket, dict):
            continue

        title = str(ticket.get("title") or f"Website Build Task {idx}").strip()
        filename = f"pdf-{idx:02d}-{_slugify(title)}.md"
        if filename in generated_names:
            filename = f"pdf-{idx:02d}-{_slugify(title)}-{idx}.md"
        generated_names.add(filename)

        ticket_file = out_path / filename
        ticket_file.write_text(_render_ticket_markdown(ticket, pdf_file.name), encoding="utf-8")
        generated_ticket_files.append(str(ticket_file))

    return PDFScanResult(
        pdf_name=pdf_file.name,
        pages_scanned=page_count,
        chars_extracted=len(extracted_text),
        project_name=project_name,
        summary=summary,
        roadmap_file=str(roadmap_file),
        brief_file=str(brief_file),
        generated_ticket_files=generated_ticket_files,
        design_system=design_system,
        pages=pages if isinstance(pages, list) else [],
        features=features,
        wireframes=wireframes,
        open_questions=open_questions,
    )


def default_pdf_folder(pdf_filename: str) -> str:
    """Create a safe default output folder from a PDF filename."""

    return _safe_folder_name(Path(pdf_filename).stem)
