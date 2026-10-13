"""Unit tests for pdf_brief_scanner (ROADMAP.md generation, PDF text extraction, tickets)."""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import json

from pdf_brief_scanner import (
    _slugify,
    _safe_folder_name,
    _parse_json_response,
    _render_brief_markdown,
    _render_ticket_markdown,
    _render_roadmap_markdown,
    scan_pdf_brief,
    extract_pdf_text,
    PDFScanResult,
)
from ai_client import AIClientError


class TestPdfBriefScanner(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(_slugify("Hello World!"), "hello-world")
        self.assertEqual(_slugify("   Feature #1: Auth & Login   "), "feature-1-auth-login")
        self.assertEqual(_slugify("---"), "item")
        self.assertEqual(_slugify("A" * 100, max_len=20), "a" * 20)

    def test_safe_folder_name(self):
        self.assertEqual(_safe_folder_name("Client_Brief_v1.pdf"), "client-brief-v1")
        self.assertEqual(_safe_folder_name(""), "pdf-brief")

    def test_parse_json_response_clean(self):
        payload = {"project_name": "Acme Store", "summary": "An ecommerce store"}
        parsed = _parse_json_response(json.dumps(payload))
        self.assertEqual(parsed["project_name"], "Acme Store")

    def test_parse_json_response_fences_and_trailing(self):
        payload = {"project_name": "Beta Site"}
        raw = f"```json\n{json.dumps(payload)}\n```\nHere is some reasoning commentary."
        parsed = _parse_json_response(raw)
        self.assertEqual(parsed["project_name"], "Beta Site")

    def test_parse_json_response_invalid(self):
        with self.assertRaises(AIClientError):
            _parse_json_response("This is not JSON at all.")

    def test_render_roadmap_markdown_structure(self):
        """Verifies that _render_roadmap_markdown generates a comprehensive PM roadmap."""
        data = {
            "project_name": "Solaris Energy",
            "summary": "Renewable energy consumer portal.",
            "design_system": {
                "logo": "Solaris Sun Icon",
                "fonts": ["Inter", "Space Grotesk"],
                "color_palette": ["#10b981", "#047857"],
                "visual_tone": "Clean, modern, sustainable",
                "notes": ["Use 8px border radii"],
            },
            "pages": [
                {
                    "name": "Landing Page",
                    "purpose": "Educate and capture leads",
                    "sections": ["Hero", "Calculator", "FAQ"],
                    "notes": ["Calculator needs reactive formula"],
                }
            ],
            "features": ["Savings Calculator", "Installer Finder"],
            "wireframes": ["Desktop 12-col grid", "Mobile drawer nav"],
            "open_questions": ["Is Stripe payment required in Phase 1?"],
            "roadmap_markdown": "",
        }
        tickets = [
            {
                "index": 1,
                "title": "Implement Savings Calculator | Core",
                "filename": "pdf-01-implement-savings-calculator.md",
                "priority": "critical",
                "problem": "Users need an interactive calculator | high value to estimate annual power bill reduction.",
            },
            {
                "index": 2,
                "title": "Build Mobile Navigation",
                "filename": "pdf-02-build-mobile-navigation.md",
                "priority": "high",
                "problem": "Responsive navbar collapses to drawer on mobile devices.",
            },
        ]

        md = _render_roadmap_markdown(
            data=data,
            pdf_name="solaris-brief.pdf",
            page_count=6,
            chars_extracted=4500,
            used_ocr=False,
            tickets=tickets,
            output_folder="solaris-v1",
        )

        # 1. Title & Executive Summary
        self.assertIn("# Solaris Energy — Development Roadmap", md)
        self.assertIn("Renewable energy consumer portal", md)
        self.assertIn("solaris-brief.pdf", md)

        # 2. Design System table
        self.assertIn("## 2. Design System Foundations", md)
        self.assertIn("#10b981", md)
        self.assertIn("Space Grotesk", md)
        self.assertIn("Clean, modern, sustainable", md)

        # 3. Architecture & Pages
        self.assertIn("Landing Page", md)
        self.assertIn("Savings Calculator", md)

        # 4. Phased Milestones with Quality Gates
        self.assertIn("## 4. Phased Implementation Roadmap", md)
        self.assertIn("Phase 1: Brand Foundations", md)
        self.assertIn("Phase 2: Page Scaffolding", md)
        self.assertIn("Phase 3: Interactive Features", md)
        self.assertIn("Phase 4: Polish", md)
        self.assertIn("Quality Gate", md)

        # 5. Ticket Index with clickable links and priority badges
        self.assertIn("## 5. Execution Ticket Index", md)
        self.assertIn("[Implement Savings Calculator - Core](pdf-01-implement-savings-calculator.md)", md)
        self.assertIn("🔴 CRITICAL", md)
        self.assertIn("🟡 PRIORITY", md)

        # 6. Open Questions
        self.assertIn("Is Stripe payment required in Phase 1?", md)

        # 7. Next Steps command
        self.assertIn("/load-tickets solaris-v1", md)

    def test_scan_pdf_brief_end_to_end(self):
        """Tests that scan_pdf_brief generates ROADMAP.md, PDF_BRIEF.md, and ticket files."""
        mock_ai = MagicMock()
        mock_ai.is_configured.return_value = True

        mock_ai_response = {
            "project_name": "Nexus Portal",
            "summary": "Next-gen community forum.",
            "design_system": {
                "logo": "Nexus Hexagon",
                "fonts": ["Geist", "Geist Mono"],
                "color_palette": ["#6366f1", "#4f46e5"],
                "visual_tone": "Futuristic developer-first",
            },
            "pages": [{"name": "Home", "purpose": "Feed overview", "sections": ["Feed", "Sidebar"]}],
            "features": ["Markdown editor", "Real-time notifications"],
            "wireframes": ["Split desktop layout"],
            "open_questions": ["Database provider choice?"],
            "roadmap_markdown": "",
            "tickets": [
                {
                    "title": "Setup Geist Typography & Colors",
                    "priority": "high",
                    "problem": "App lacks defined CSS tokens.",
                    "related_files": ["globals.css"],
                    "what_to_fix": ["Configure tailwind theme", "Import fonts"],
                    "acceptance_criteria": ["CSS tokens active"],
                },
                {
                    "title": "Build Markdown Editor Component",
                    "priority": "critical",
                    "problem": "Users need to write formatted forum posts.",
                    "related_files": ["components/Editor.tsx"],
                    "what_to_fix": ["Scaffold Editor component", "Add preview tab"],
                    "acceptance_criteria": ["Live preview updates"],
                },
            ],
        }
        mock_ai.chat.return_value = json.dumps(mock_ai_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "nexus_spec.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 sample pdf binary data")

            tickets_root = Path(tmpdir) / "tickets"

            with patch("pdf_brief_scanner.extract_pdf_text", return_value=(4, "Sample extracted brief text for Nexus Portal", False)):
                # Test using pdf_file keyword
                result = scan_pdf_brief(
                    pdf_file=str(pdf_path),
                    output_folder="nexus-spec",
                    tickets_dir=str(tickets_root),
                    ai_client=mock_ai,
                )

                self.assertEqual(result.project_name, "Nexus Portal")
                self.assertEqual(result.pages_scanned, 4)
                self.assertEqual(len(result.generated_ticket_files), 2)

                out_folder = tickets_root / "nexus-spec"
                roadmap_file = out_folder / "ROADMAP.md"
                brief_file = out_folder / "PDF_BRIEF.md"

                self.assertTrue(roadmap_file.exists())
                self.assertTrue(brief_file.exists())

                roadmap_text = roadmap_file.read_text(encoding="utf-8")
                self.assertIn("# Nexus Portal — Development Roadmap", roadmap_text)
                self.assertIn("## 5. Execution Ticket Index", roadmap_text)
                self.assertIn("[Setup Geist Typography & Colors](pdf-01-setup-geist-typography-colors.md)", roadmap_text)
                self.assertIn("🔴 CRITICAL", roadmap_text)
                self.assertIn("/load-tickets nexus-spec", roadmap_text)

                # Test that tickets were written
                t1 = out_folder / "pdf-01-setup-geist-typography-colors.md"
                self.assertTrue(t1.exists())
                t1_text = t1.read_text(encoding="utf-8")
                self.assertIn("**[PRIORITY]**", t1_text)
                self.assertIn("## What to Fix", t1_text)

    def test_scan_pdf_brief_with_pdf_path_keyword(self):
        """Verifies backward-compatibility when called with pdf_path keyword."""
        mock_ai = MagicMock()
        mock_ai.is_configured.return_value = True
        mock_ai.chat.return_value = json.dumps({
            "project_name": "Path Test",
            "summary": "Testing pdf_path arg",
            "tickets": [],
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 dummy")
            tickets_root = Path(tmpdir) / "tickets"

            with patch("pdf_brief_scanner.extract_pdf_text", return_value=(1, "dummy text", False)):
                res = scan_pdf_brief(
                    pdf_path=str(pdf_path),
                    output_folder="test-folder",
                    tickets_dir=str(tickets_root),
                    ai_client=mock_ai,
                )
                self.assertEqual(res.project_name, "Path Test")


if __name__ == "__main__":
    unittest.main()
