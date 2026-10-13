"""PDF brief scanner for website/project planning uploads.

This module extracts text from a PDF design brief, asks the configured AI
provider to structure the findings, and writes loadable roadmap/ticket files
into the bot's tickets/ folder.

JUSTIFICATION:
This file exceeds the standard 300-line threshold because it integrates PDF text extraction
(using multiple fallbacks: native text vs OCR via Tesseract), structured schema translation,
response parsing (including fallback options for raw LLM outputs), Markdown serialization, and
ticket file generation in a single unified entry point.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
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

try:
    import pypdfium2 as pdfium
except ImportError as exc:  # pragma: no cover - dependency guard
    pdfium = None  # type: ignore[assignment]
    _PDFIUM_IMPORT_ERROR = exc
else:  # pragma: no cover - import success path
    _PDFIUM_IMPORT_ERROR = None

try:
    import pytesseract
except ImportError as exc:  # pragma: no cover - dependency guard
    pytesseract = None  # type: ignore[assignment]
    _PYTESSERACT_IMPORT_ERROR = exc
else:  # pragma: no cover - import success path
    _PYTESSERACT_IMPORT_ERROR = None


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
    used_ocr: bool


def _slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "item"


def _safe_folder_name(value: str) -> str:
    cleaned = _slugify(value.replace(".pdf", ""))
    if not cleaned or cleaned == "item":
        return "pdf-brief"
    return cleaned


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, count=1, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


import logging as _logging
_pdf_logger = _logging.getLogger(__name__)


def _parse_json_response(text: str) -> dict[str, Any]:
    # Log what the model actually returned so we can diagnose failures.
    preview = text[:500].replace("\n", " ") if text else "<empty>"
    _pdf_logger.debug("scan_docs raw response (first 500 chars): %s", preview)

    cleaned = _strip_code_fences(text)

    # 1. Happy path: the whole string is valid JSON.
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Model appended text after the JSON object (common with thinking models).
    #    raw_decode stops at the end of the first complete JSON value.
    start = cleaned.find("{")
    if start >= 0:
        try:
            data, _ = json.JSONDecoder().raw_decode(cleaned, start)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Log the full response at WARNING level so it appears in Render logs.
    _pdf_logger.warning("scan_docs could not parse JSON. Full response:\n%s", text[:2000])
    raise AIClientError("AI response was not valid JSON.")


def _ocr_enabled() -> bool:
    """Return whether OCR fallback is enabled for scan-pdf."""

    raw = os.getenv("ENABLE_PDF_OCR_FALLBACK", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _extract_text_with_ocr(pdf_path: str, page_count: int) -> str:
    """Extract text via OCR for scanned/image-only PDFs."""

    if pdfium is None:
        raise AIClientError(
            "OCR fallback requires `pypdfium2`. Install dependencies and redeploy."
        ) from _PDFIUM_IMPORT_ERROR
    if pytesseract is None:
        raise AIClientError(
            "OCR fallback requires `pytesseract`. Install dependencies and redeploy."
        ) from _PYTESSERACT_IMPORT_ERROR

    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    doc = pdfium.PdfDocument(pdf_path)
    try:
        max_pages = min(page_count, 40)
        rendered_scale = 220 / 72.0
        parts: list[str] = []

        for index in range(max_pages):
            try:
                page = doc[index]
                bitmap = page.render(scale=rendered_scale)
                image = bitmap.to_pil()
                text = pytesseract.image_to_string(image) or ""
            except Exception:
                text = ""

            if text.strip():
                parts.append(text.strip())

        return "\n\n".join(parts).strip()
    finally:
        try:
            doc.close()
        except Exception:
            pass


def extract_pdf_text(pdf_path: str) -> tuple[int, str, bool]:
    """Extract selectable text from each PDF page.

    Returns a tuple of (page_count, extracted_text, used_ocr).
    """
    if PdfReader is None:
        raise AIClientError(
            "PDF support is unavailable. Install the `pypdf` package to enable `/scan-pdf`."
        ) from _PYPDF_IMPORT_ERROR

    reader = None
    parts: list[str] = []
    page_count = 0
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = ""
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            if text.strip():
                parts.append(text.strip())

        page_count = len(reader.pages)
    finally:
        if reader is not None and hasattr(reader, "close"):
            try:
                reader.close()
            except Exception:
                pass

    extracted_text = "\n\n".join(parts).strip()
    used_ocr = False

    # OCR fallback for scanned/image-heavy briefs with little or no text layer.
    if _ocr_enabled() and len(extracted_text) < 250:
        try:
            ocr_text = _extract_text_with_ocr(pdf_path, page_count)
        except AIClientError:
            if not extracted_text:
                raise
            ocr_text = ""

        if ocr_text:
            used_ocr = True
            extracted_text = f"{extracted_text}\n\n{ocr_text}".strip() if extracted_text else ocr_text

    return page_count, extracted_text, used_ocr


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
        "Return valid JSON only — no markdown fences, no commentary, no text before or after the JSON object.\n"
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
        "- In roadmap_markdown, provide a concise phased milestone plan (Phase 1, Phase 2, Phase 3, Phase 4) covering timeline, milestones, and deliverable goals.\n"
        "- Use the PDF details to infer logo, fonts, color palette, features, mockups, and wireframes.\n"
        "- If the PDF is image-heavy or ambiguous, record that in open_questions.\n"
        "- Keep acceptance criteria concrete and testable.\n\n"
        f"PDF file: {pdf_name}\n"
        f"Pages scanned: {page_count}\n\n"
        "PDF content:\n"
        f"<<<PDF_TEXT_START\n{brief_excerpt}\nPDF_TEXT_END>>>\n\n"
        "Respond with the JSON object only. Do not write anything before or after the opening {{ and closing }} braces."
    )


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _render_brief_markdown(
    data: dict[str, Any],
    pdf_name: str,
    page_count: int,
    chars_extracted: int,
    used_ocr: bool,
) -> str:
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
        f"- Extraction mode: {'OCR fallback' if used_ocr else 'Embedded PDF text'}",
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


def _render_roadmap_markdown(
    data: dict[str, Any],
    pdf_name: str,
    page_count: int,
    chars_extracted: int,
    used_ocr: bool,
    tickets: list[dict[str, Any]],
    output_folder: str,
) -> str:
    """Render a comprehensive, PM-ready ROADMAP.md document with full ticket cross-referencing."""
    project_name = str(data.get("project_name") or Path(pdf_name).stem).strip() or Path(pdf_name).stem
    summary = str(data.get("summary") or "").strip() or "No executive summary was provided."
    design_system = data.get("design_system") if isinstance(data.get("design_system"), dict) else {}
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    features = _normalize_list(data.get("features"))
    wireframes = _normalize_list(data.get("wireframes"))
    open_questions = _normalize_list(data.get("open_questions"))
    ai_roadmap_raw = str(data.get("roadmap_markdown") or "").strip()

    extraction_mode = "OCR fallback (Scanned/Image PDF)" if used_ocr else "Embedded vector text"

    lines: list[str] = [
        f"# {project_name} — Development Roadmap",
        "",
        f"> **Source Brief**: `{pdf_name}` ({page_count} pages • {chars_extracted:,} chars extracted via {extraction_mode})",
        "",
        "---",
        "",
        "## 1. Executive Summary & Vision",
        "",
        summary,
        "",
        "### Scope & Delivery Targets",
        f"- **Target Pages Identified**: {len(pages)}",
        f"- **Core Extracted Features**: {len(features)}",
        f"- **Generated Execution Tickets**: {len(tickets)} under `tickets/{output_folder}/`",
        "",
        "---",
        "",
        "## 2. Design System Foundations",
        "",
    ]

    logo = str(design_system.get("logo") or "Not specified").replace("|", "/")
    colors_list = _normalize_list(design_system.get("color_palette"))
    if not colors_list:
        p_col = design_system.get("primary_color") or design_system.get("primaryColor")
        s_col = design_system.get("secondary_color") or design_system.get("secondaryColor")
        if p_col:
            colors_list.append(f"Primary: {p_col}")
        if s_col:
            colors_list.append(f"Secondary: {s_col}")
    colors = ", ".join(colors_list) or "Not specified"
    colors = colors.replace("|", "/")

    fonts = ", ".join(_normalize_list(design_system.get("fonts"))) or "Not specified"
    fonts = fonts.replace("|", "/")
    tone = str(design_system.get("visual_tone") or "Not specified").replace("|", "/")

    lines.extend([
        "| Foundation Element | Specification |",
        "| :--- | :--- |",
        f"| **Brand Identity / Logo** | {logo} |",
        f"| **Color Palette** | {colors} |",
        f"| **Typography** | {fonts} |",
        f"| **Visual Tone** | {tone} |",
        "",
    ])

    design_notes = _normalize_list(design_system.get("notes"))
    if design_notes:
        lines.append("**Design Notes:**")
        lines.extend([f"- {note}" for note in design_notes])
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. Site Architecture & Target Pages",
        "",
    ])

    if pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            p_name = str(page.get("name") or "Page").strip()
            p_purpose = str(page.get("purpose") or "Not specified").strip()
            p_sections = ", ".join(_normalize_list(page.get("sections"))) or "General layout"
            p_notes = ", ".join(_normalize_list(page.get("notes")))
            note_str = f" • *Notes*: {p_notes}" if p_notes else ""
            lines.append(f"- **{p_name}**: {p_purpose}")
            lines.append(f"  - *Sections*: {p_sections}{note_str}")
    else:
        lines.append("- *(No specific page hierarchy extracted from brief)*")
    lines.append("")

    if features:
        lines.append("### Core Features")
        lines.extend([f"- {f}" for f in features])
        lines.append("")

    if wireframes:
        lines.append("### Wireframe & Layout Specifications")
        lines.extend([f"- {w}" for w in wireframes])
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 4. Phased Implementation Roadmap",
        "",
    ])

    # If the AI model provided an explicit phased markdown roadmap, incorporate it seamlessly
    if ai_roadmap_raw and any(k in ai_roadmap_raw.lower() for k in ("phase", "milestone", "sprint", "week")):
        clean_ai = ai_roadmap_raw
        if clean_ai.startswith("#"):
            first_line, _, rest = clean_ai.partition("\n")
            if "roadmap" in first_line.lower():
                clean_ai = rest.strip()
        lines.append(clean_ai)
        lines.append("")
    else:
        lines.extend([
            "### Phase 1: Brand Foundations & Architecture Setup",
            "- Lock typography tokens, color palette, and asset exports.",
            "- Initialize project repository, directory architecture, and design tokens.",
            "- Scaffold baseline routing and shared navigation / footer layouts.",
            "- **Quality Gate**: Tokens committed, CI build green, responsive navigation skeleton renders cleanly.",
            "",
            "### Phase 2: Page Scaffolding & Core UI Layouts",
            "- Implement primary landing/home page sections and hero components.",
            "- Build content templates for all primary pages specified in the brief.",
            "- Ensure mobile-first responsive breakpoints and grid structure.",
            "- **Quality Gate**: All target pages accessible; layout adheres to wireframe specifications without console errors.",
            "",
            "### Phase 3: Interactive Features & Functional Integration",
            "- Build interactive components, form validations, and user flow actions.",
            "- Integrate dynamic states, client interactions, or third-party embeds.",
            "- Implement loading, error, and empty states across user pathways.",
            "- **Quality Gate**: End-to-end interactive flows pass functional testing; error handling active.",
            "",
            "### Phase 4: Polish, Accessibility & Launch Readiness",
            "- Audit contrast ratios, keyboard navigation, and WCAG accessibility standards.",
            "- Optimize image assets, performance vitals, and metadata / SEO tags.",
            "- Cross-browser and cross-device QA walkthrough against client brief.",
            "- **Quality Gate**: QA sign-off across all ticket acceptance criteria.",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 5. Execution Ticket Index",
        "",
        "| # | Ticket Title | Priority | Ticket File | Deliverable Focus |",
        "| :---: | :--- | :---: | :--- | :--- |",
    ])

    if tickets:
        for idx, t in enumerate(tickets, start=1):
            t_title = str(t.get("title", f"Task {idx}")).replace("|", "-").strip()
            t_file = t.get("filename", f"pdf-{idx:02d}.md")
            t_prio = str(t.get("priority", "medium")).lower()
            if t_prio == "critical":
                badge = "🔴 CRITICAL"
            elif t_prio == "high":
                badge = "🟡 PRIORITY"
            else:
                badge = "🟢 NORMAL"
            t_prob = str(t.get("problem", "Brief deliverable")).replace("|", "-").replace("\n", " ").strip()
            if len(t_prob) > 90:
                t_prob = t_prob[:87] + "..."
            lines.append(f"| {idx:02d} | [{t_title}]({t_file}) | {badge} | `{t_file}` | {t_prob} |")
    else:
        lines.append("| - | No tickets generated | - | - | - |")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 6. Scope Boundaries & Open Questions",
        "",
    ])

    if open_questions:
        lines.extend([f"- [ ] **Clarification Needed**: {q}" for q in open_questions])
    else:
        lines.append("- [x] No unresolved ambiguities or blocking questions identified in brief.")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 7. Execution Next Steps",
        "",
        "To publish these tickets into your Discord forum threads or tracking pipeline, run:",
        "```text",
        f"/load-tickets {output_folder}",
        "```",
        "",
    ])

    return "\n".join(lines).strip() + "\n"


def scan_pdf_brief(
    pdf_file: str | Path | None = None,
    output_folder: str = "pdf-brief",
    tickets_dir: str = "tickets",
    ai_client: NvidiaAIClient | None = None,
    ai_profile: str = "scan_docs",
    *,
    pdf_path: str | Path | None = None,
) -> PDFScanResult:
    """Analyze a design brief PDF and generate roadmap/ticket markdown files."""

    target = pdf_file if pdf_file is not None else pdf_path
    if target is None:
        raise ValueError("A PDF path or file must be provided.")

    pdf_obj = Path(target)
    if not pdf_obj.exists() or not pdf_obj.is_file():
        raise FileNotFoundError(f"PDF not found: {target}")

    if ai_client is None:
        raise AIClientError("An AI client instance must be provided.")

    if not ai_client.is_configured(ai_profile):
        raise AIClientError(
            "NVIDIA AI is not configured for the scan-docs profile. Set the AI_SCAN_DOCS_* variables (or legacy NVIDIA_* fallback)."
        )

    page_count, extracted_text, used_ocr = extract_pdf_text(str(pdf_obj))
    if not extracted_text.strip():
        raise AIClientError(
            "No extractable text was found in the PDF. If this is image-only, install OCR runtime (Tesseract) and set `TESSERACT_CMD` if needed."
        )

    prompt = _build_prompt(pdf_obj.name, extracted_text, page_count)
    analysis_text = ai_client.chat(
        prompt,
        system="You are a JSON API. Output ONLY a single valid JSON object. No markdown, no explanation, no text outside the braces.",
        max_tokens=4096,
        temperature=0.1,
        top_p=0.9,
        enable_thinking=False,
        profile=ai_profile,
    )
    data = _parse_json_response(analysis_text)

    out_folder = _safe_folder_name(output_folder)
    out_path = Path(tickets_dir) / out_folder
    out_path.mkdir(parents=True, exist_ok=True)

    project_name = str(data.get("project_name") or pdf_obj.stem).strip() or pdf_obj.stem
    summary = str(data.get("summary") or "").strip() or "No summary was generated."
    design_system = data.get("design_system") if isinstance(data.get("design_system"), dict) else {}
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    features = _normalize_list(data.get("features"))
    wireframes = _normalize_list(data.get("wireframes"))
    open_questions = _normalize_list(data.get("open_questions"))

    generated_ticket_files: list[str] = []
    ticket_records: list[dict[str, Any]] = []
    tickets_raw = data.get("tickets") if isinstance(data.get("tickets"), list) else []
    generated_names: set[str] = set()

    for idx, ticket in enumerate(tickets_raw, start=1):
        if not isinstance(ticket, dict):
            continue

        title = str(ticket.get("title") or f"Website Build Task {idx}").strip()
        filename = f"pdf-{idx:02d}-{_slugify(title)}.md"
        if filename in generated_names:
            filename = f"pdf-{idx:02d}-{_slugify(title)}-{idx}.md"
        generated_names.add(filename)

        ticket_file = out_path / filename
        ticket_file.write_text(_render_ticket_markdown(ticket, pdf_obj.name), encoding="utf-8")
        generated_ticket_files.append(str(ticket_file))

        ticket_records.append({
            "index": idx,
            "title": title,
            "filename": filename,
            "priority": str(ticket.get("priority") or "medium"),
            "problem": str(ticket.get("problem") or ""),
        })

    brief_markdown = _render_brief_markdown(data, pdf_obj.name, page_count, len(extracted_text), used_ocr)
    roadmap_markdown = _render_roadmap_markdown(
        data=data,
        pdf_name=pdf_obj.name,
        page_count=page_count,
        chars_extracted=len(extracted_text),
        used_ocr=used_ocr,
        tickets=ticket_records,
        output_folder=out_folder,
    )

    brief_file = out_path / "PDF_BRIEF.md"
    roadmap_file = out_path / "ROADMAP.md"
    brief_file.write_text(brief_markdown, encoding="utf-8")
    roadmap_file.write_text(roadmap_markdown, encoding="utf-8")

    return PDFScanResult(
        pdf_name=pdf_obj.name,
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
        used_ocr=used_ocr,
    )


def default_pdf_folder(pdf_filename: str) -> str:
    """Create a safe default output folder from a PDF filename."""

    return _safe_folder_name(Path(pdf_filename).stem)
