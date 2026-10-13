"""Unit tests for ScannerCog (/scan-project, /scan-roadmap, /plan-mvp, /ask-ai)."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import tempfile
import discord
import scripts.roadmap_builder
from cogs.scanner import ScannerCog


class TestScannerCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.cog = ScannerCog(self.bot)

        self.interaction = MagicMock(spec=discord.Interaction)
        self.interaction.response.is_done.return_value = False
        self.interaction.response.defer = AsyncMock()
        self.interaction.followup.send = AsyncMock()

    def tearDown(self):
        import shutil
        for folder in ["test-scan", "test-roadmap", "test-mvp"]:
            p = Path("tickets") / folder
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)

    @patch("cogs.scanner.scanner_service.scan_directory")
    @patch("cogs.scanner.scanner_service.generate_ticket_markdown")
    async def test_scan_project(self, mock_gen_md, mock_scan_dir):
        """Tests /scan-project generates tickets and returns summary embed."""
        mock_scan_dir.return_value = {
            "todos": [{"file": "app.py", "line": 10, "comment": "TODO: fix auth"}],
            "debug": [],
        }
        mock_gen_md.return_value = "# [PRIORITY] Fix TODOs\n## Problem\nFix todos"

        with tempfile.TemporaryDirectory() as tmpdir:
            await self.cog.scan_project.callback(self.cog, self.interaction, path=tmpdir, folder="test-scan")

            self.interaction.followup.send.assert_awaited_once()
            args, kwargs = self.interaction.followup.send.call_args
            embed = kwargs["embed"]
            self.assertIn("Project Scan Complete", embed.title)
            self.assertIn("Generated **1** ticket files", embed.description)

    @patch("discord.File")
    @patch("scripts.roadmap_builder.build_project_roadmap")
    async def test_scan_roadmap_local(self, mock_build_roadmap, mock_file_cls):
        """Tests /scan-roadmap calls roadmap builder and attaches ROADMAP.md."""
        mock_file_instance = MagicMock()
        mock_file_instance.filename = "ROADMAP.md"
        mock_file_cls.return_value = mock_file_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_roadmap_path = Path(tmpdir) / "ROADMAP.md"
            fake_roadmap_path.write_text("# 12-Week Roadmap\n## Week 1: Core", encoding="utf-8")

            mock_result = MagicMock()
            mock_result.roadmap_file = str(fake_roadmap_path)
            mock_result.total_files_scanned = 25
            mock_result.total_components = 4
            mock_result.total_issues = 7
            mock_result.total_tickets = 3
            mock_result.detected_features = [("Authentication", 3)]
            mock_result.suggested_features = ["Add rate limiting", "Set up CI/CD"]
            mock_build_roadmap.return_value = mock_result

            await self.cog.scan_roadmap.callback(
                self.cog,
                self.interaction,
                path_or_repo_url=tmpdir,
                folder="test-roadmap",
            )

            # Two calls: 1 for progress ("⏳ Scanning..."), 1 for final embed
            self.assertEqual(self.interaction.followup.send.await_count, 2)
            last_call = self.interaction.followup.send.call_args_list[-1]
            kwargs = last_call[1]
            embed = kwargs["embed"]
            self.assertIn("Roadmap Analysis Complete", embed.title)
            self.assertIn("file", kwargs)
            self.assertEqual(kwargs["file"].filename, "ROADMAP.md")

    @patch("discord.File")
    @patch("concise_planner.generate_concise_plan")
    @patch("concise_planner.parse_ai_plan_response")
    @patch("concise_planner.write_plan_tickets")
    @patch("concise_planner.build_plan_summary")
    async def test_plan_mvp(self, mock_build_summary, mock_write_tickets, mock_parse, mock_gen_plan, mock_file_cls):
        """Tests /plan-mvp generates structured tickets and PLAN.md."""
        mock_file_instance = MagicMock()
        mock_file_instance.filename = "PLAN.md"
        mock_file_cls.return_value = mock_file_instance

        mock_gen_plan.return_value = "Plan text"
        mock_ticket = MagicMock()
        mock_ticket.title = "Landing Page Hero"
        mock_ticket.priority = True
        mock_ticket.area = "Frontend"
        mock_ticket.cta = "Implement hero banner"
        mock_parse.return_value = ("Project Vision", [mock_ticket])

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "PLAN.md"
            plan_path.write_text("# Sprint Plan", encoding="utf-8")
            mock_build_summary.return_value = str(plan_path)
            mock_write_tickets.return_value = [str(Path(tmpdir) / "01.md")]

            await self.cog.plan_mvp.callback(
                self.cog,
                self.interaction,
                idea="AI Flashcard Maker for Medical Students",
                folder="med-mvp",
                context="React, FastAPI",
                auto_load=False,
            )

            self.interaction.followup.send.assert_awaited_once()
            args, kwargs = self.interaction.followup.send.call_args
            embed = kwargs["embed"]
            self.assertIn("MVP Sprint Plan", embed.title)
            self.assertIn("Landing Page Hero", embed.fields[2].value)
            self.assertEqual(kwargs["file"].filename, "PLAN.md")
            self.assertEqual(kwargs["file"].filename, "PLAN.md")

    @patch("services.ai_service.ai_service.generate_text")
    @patch("math_renderer.has_latex")
    @patch("math_renderer.render_equations_to_single_png")
    async def test_ask_ai_with_math_latex(self, mock_render_png, mock_has_latex, mock_gen_text):
        """Tests /ask-ai renders LaTeX math equations into a PNG attachment."""
        mock_gen_text.return_value = "The loss function is $$L = \\frac{1}{2}(y - \\hat{y})^2$$."
        mock_has_latex.return_value = True
        mock_render_png.return_value = b"\x89PNG\r\n\x1a\n"

        await self.cog.ask_ai.callback(self.cog, self.interaction, question="What is MSE?")

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("AI Technical Response", embed.title)
        self.assertIn("file", kwargs)
        self.assertEqual(kwargs["file"].filename, "equation.png")


if __name__ == "__main__":
    unittest.main()
