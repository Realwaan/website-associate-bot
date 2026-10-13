"""Scanner Cog for automated codebase analysis, PDF brief parsing, roadmap generation, and MVP planning."""
import asyncio
import io
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import DEFAULT_REPO_URL, GITHUB_TOKEN, TICKETS_DIR
from database import add_thread, mark_ticket_loaded
from services.ai_service import ai_service
from services.code_scanner import scanner_service
from ticket_loader import parse_ticket_markdown

logger = logging.getLogger(__name__)


async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(thinking=True)
        except discord.HTTPException as e:
            if e.status == 429:
                logger.warning("Discord API 429 rate limit hit during safe_defer.")
            else:
                logger.warning(f"Failed to defer interaction: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error in safe_defer: {e}")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract PDF text away from Discord's event loop."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


class ScannerCog(commands.Cog, name="Scanner"):
    """Handles codebase scanning, AI brief analysis, roadmap generation, and MVP sprint planning."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /scan-project
    @app_commands.command(
        name="scan-project",
        description="Scan a local folder and generate categorized ticket markdown files",
    )
    @app_commands.describe(
        path="Path to the directory to scan",
        folder="Folder name under tickets/ to store generated files",
    )
    async def scan_project(
        self,
        interaction: discord.Interaction,
        path: str,
        folder: str = "scan-results",
    ):
        await safe_defer(interaction)
        try:
            target_path = Path(path).resolve()
            if not target_path.exists():
                await interaction.followup.send(f"❌ Target path `{path}` does not exist.")
                return

            results = await asyncio.to_thread(scanner_service.scan_directory, str(target_path))
            out_dir = Path(TICKETS_DIR) / folder
            out_dir.mkdir(parents=True, exist_ok=True)

            ticket_count = 0
            summary_fields = []

            for cat, items in results.items():
                if items:
                    ticket_md = scanner_service.generate_ticket_markdown(cat, items, folder)
                    file_name = f"{cat}.md"
                    with open(out_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(ticket_md)
                    ticket_count += 1
                    summary_fields.append((cat.replace("_", " ").title(), len(items)))

            embed = discord.Embed(
                title="🔍 Project Scan Complete",
                description=f"Scanned `{target_path.name}` • Generated **{ticket_count}** ticket files in `tickets/{folder}/`",
                color=0x38BDF8,
            )

            for name, count in summary_fields:
                embed.add_field(name=name, value=f"`{count}` occurrences", inline=True)

            embed.set_footer(text=f"Run /load-tickets {folder} to publish these tickets into Discord threads.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-project: {e}")
            await interaction.followup.send(f"❌ Scan failed: {e}")

    # 2. /scan-repo
    @app_commands.command(
        name="scan-repo",
        description="Clone and scan the project GitHub repository",
    )
    @app_commands.describe(
        repo_url="GitHub Repository URL (defaults to USCCE)",
        folder="Ticket output folder",
    )
    async def scan_repo(
        self,
        interaction: discord.Interaction,
        repo_url: str = DEFAULT_REPO_URL,
        folder: str = "repo-scan",
    ):
        await safe_defer(interaction)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                await interaction.followup.send(f"⏳ Cloning `{repo_url}` and analyzing codebase...")

                clone_cmd = ["git", "clone", "--depth", "1"]
                if GITHUB_TOKEN and "github.com" in repo_url:
                    clone_cmd += ["-c", f"http.extraHeader=Authorization: Bearer {GITHUB_TOKEN}"]
                    clone_cmd.append(repo_url)
                else:
                    clone_cmd.append(repo_url)

                res = await asyncio.to_thread(
                    subprocess.run,
                    clone_cmd + [tmpdir],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    await interaction.followup.send(f"❌ Failed to clone repository: {res.stderr[:200]}")
                    return

                results = await asyncio.to_thread(scanner_service.scan_directory, tmpdir)
                out_dir = Path(TICKETS_DIR) / folder
                out_dir.mkdir(parents=True, exist_ok=True)

                ticket_count = 0
                for cat, items in results.items():
                    if items:
                        ticket_md = scanner_service.generate_ticket_markdown(cat, items, folder)
                        with open(out_dir / f"{cat}.md", "w", encoding="utf-8") as f:
                            f.write(ticket_md)
                        ticket_count += 1

                embed = discord.Embed(
                    title="🐙 Remote GitHub Scan Complete",
                    description=f"Successfully analyzed `{repo_url}`.\nCreated **{ticket_count}** ticket files under `tickets/{folder}/`.",
                    color=0x10B981,
                )
                embed.set_footer(text=f"Run /load-tickets {folder} to import these tickets.")
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-repo: {e}")
            await interaction.followup.send(f"❌ Error scanning repo: {e}")

    # 3. /scan-roadmap
    @app_commands.command(
        name="scan-roadmap",
        description="Scan codebase and generate a prioritized 12-week roadmap with suggested improvements",
    )
    @app_commands.describe(
        path_or_repo_url="Local folder path or HTTPS git repo URL to scan",
        folder="Output folder name under tickets/ (default: roadmap)",
        threshold="Large file threshold in lines (default: 300)",
        generate_tickets="Whether to generate ticket markdown files in the folder (default: True)",
    )
    async def scan_roadmap(
        self,
        interaction: discord.Interaction,
        path_or_repo_url: str,
        folder: str = "roadmap",
        threshold: int = 300,
        generate_tickets: bool = True,
    ):
        await safe_defer(interaction)
        try:
            folder_clean = re.sub(r"[^a-zA-Z0-9_\-]+", "-", folder.lower()).strip("-") or "roadmap"
            is_remote = path_or_repo_url.startswith(("http://", "https://", "git@"))

            def _build(target_dir: str, scan_source: str):
                scripts_dir = str(Path(__file__).resolve().parents[1] / "scripts")
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                from roadmap_builder import build_project_roadmap

                return build_project_roadmap(
                    project_path=target_dir,
                    output_folder=folder_clean,
                    scan_source=scan_source,
                    tickets_dir=TICKETS_DIR,
                    large_file_threshold=threshold,
                    generate_issue_tickets=generate_tickets,
                    write_roadmap_file=True,
                )

            if is_remote:
                repo_url = path_or_repo_url
                with tempfile.TemporaryDirectory() as tmpdir:
                    await interaction.followup.send(f"⏳ Cloning `{repo_url}` and analyzing architecture roadmap...")
                    clone_cmd = ["git", "clone", "--depth", "1"]
                    if GITHUB_TOKEN and "github.com" in repo_url:
                        clone_cmd += ["-c", f"http.extraHeader=Authorization: Bearer {GITHUB_TOKEN}"]
                    clone_cmd += [repo_url, tmpdir]

                    res = await asyncio.to_thread(subprocess.run, clone_cmd, capture_output=True, text=True)
                    if res.returncode != 0:
                        await interaction.followup.send(f"❌ Failed to clone repository: {res.stderr[:200]}")
                        return

                    result = await asyncio.to_thread(_build, tmpdir, repo_url)
            else:
                target_path = Path(path_or_repo_url).resolve()
                if not target_path.exists():
                    await interaction.followup.send(f"❌ Target path `{path_or_repo_url}` does not exist.")
                    return
                await interaction.followup.send(f"⏳ Scanning `{target_path.name}` and generating development roadmap...")
                result = await asyncio.to_thread(_build, str(target_path), str(target_path))

            roadmap_file_path = Path(result.roadmap_file)
            embed = discord.Embed(
                title="🗺️ Architecture & 12-Week Roadmap Analysis Complete",
                description=(
                    f"Scanned **{result.total_files_scanned}** files across **{result.total_components}** components.\n"
                    f"Identified **{result.total_issues}** issues • Generated **{result.total_tickets}** tickets under `tickets/{folder_clean}/`.\n"
                    f"Prioritized 12-week milestone schedule generated in `ROADMAP.md`."
                ),
                color=0x6366F1,
            )

            if result.detected_features:
                features_str = ", ".join(f"`{f[0]}` ({f[1]})" for f in result.detected_features[:5])
                embed.add_field(name="✨ Detected Features", value=features_str, inline=False)

            if result.suggested_features:
                suggestions_str = "\n".join(f"• {s}" for s in result.suggested_features[:4])
                embed.add_field(name="💡 Suggested Improvements", value=suggestions_str, inline=False)

            embed.set_footer(text=f"CapStoneFlow • Use /load-tickets {folder_clean} to import these tickets.")

            if roadmap_file_path.exists():
                file = discord.File(str(roadmap_file_path), filename="ROADMAP.md")
                await interaction.followup.send(embed=embed, file=file)
            else:
                await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-roadmap: {e}")
            await interaction.followup.send(f"❌ Error generating roadmap: {e}")

    # 4. /plan-mvp
    @app_commands.command(
        name="plan-mvp",
        description="Plan an MVP hackathon project: generates scoped tickets with CTAs and acceptance criteria",
    )
    @app_commands.describe(
        idea="Project idea, requirements, or problem statement to solve",
        folder="Output folder under tickets/ (e.g. hackathon-mvp)",
        context="Optional tech stack or architecture constraints (e.g. Next.js, Supabase, Tailwind)",
        auto_load="Whether to immediately create Discord threads for these tickets in this channel",
    )
    async def plan_mvp(
        self,
        interaction: discord.Interaction,
        idea: str,
        folder: str = "hackathon-mvp",
        context: Optional[str] = None,
        auto_load: bool = False,
    ):
        await safe_defer(interaction)
        try:
            folder_clean = re.sub(r"[^a-zA-Z0-9_\-]+", "-", folder.lower()).strip("-") or "hackathon-mvp"

            from concise_planner import (
                build_plan_summary,
                generate_concise_plan,
                parse_ai_plan_response,
                write_plan_tickets,
            )

            # 1. Generate plan text
            raw_response = await asyncio.to_thread(
                generate_concise_plan,
                getattr(self.bot, "ai_client", None),
                idea,
                context=context or "",
                max_tickets=8,
            )

            # 2. Parse tickets
            project_summary, tickets = await asyncio.to_thread(
                parse_ai_plan_response,
                raw_response,
            )

            # 3. Write tickets to disk
            ticket_files = await asyncio.to_thread(
                write_plan_tickets,
                tickets,
                folder_clean,
                tickets_dir=TICKETS_DIR,
            )

            # 4. Write PLAN.md
            plan_path = await asyncio.to_thread(
                build_plan_summary,
                project_summary,
                tickets,
                folder_clean,
                idea,
                tickets_dir=TICKETS_DIR,
            )

            embed = discord.Embed(
                title=f"🚀 MVP Sprint Plan: {folder_clean}",
                description=project_summary[:1500],
                color=0x10B981,
            )
            embed.add_field(name="💡 Idea / Pitch", value=idea[:500], inline=False)
            if context:
                embed.add_field(name="🛠️ Tech Stack & Constraints", value=context[:500], inline=False)

            tickets_summary = []
            for idx, t in enumerate(tickets, 1):
                prio_badge = "🚨 [PRIORITY]" if t.priority else "▫️"
                tickets_summary.append(f"**{idx}. {prio_badge} {t.title}** (`{t.area}`)\n→ *CTA*: {t.cta}")

            embed.add_field(
                name=f"📋 MVP Scoped Tickets ({len(tickets)})",
                value="\n".join(tickets_summary)[:1024],
                inline=False,
            )
            embed.set_footer(text=f"CapStoneFlow • Saved in tickets/{folder_clean}/ • PLAN.md attached")

            plan_file = discord.File(plan_path, filename="PLAN.md")
            await interaction.followup.send(embed=embed, file=plan_file)

            # 5. Auto-load tickets if requested
            if auto_load:
                target_channel = interaction.channel
                if isinstance(target_channel, discord.TextChannel):
                    loaded_threads = []
                    for t_path in ticket_files:
                        t_data = parse_ticket_markdown(t_path)
                        t_title = t_data.get("title") or Path(t_path).stem
                        th_name = f"[OPEN] {t_title}"[:100]
                        try:
                            thread = await target_channel.create_thread(
                                name=th_name,
                                auto_archive_duration=1440,
                                type=discord.ChannelType.public_thread,
                            )
                            t_embed = discord.Embed(
                                title=f"📋 Ticket: {t_title}",
                                description=(t_data.get("problem") or "No problem description")[:2000],
                                color=0x38BDF8,
                            )
                            if t_data.get("what_to_fix"):
                                fixes = t_data["what_to_fix"]
                                f_text = "\n".join(f"**{i+1}.** {it}" for i, it in enumerate(fixes)) if isinstance(fixes, list) else str(fixes)
                                t_embed.add_field(name="🛠️ What to Fix", value=f_text[:1024], inline=False)
                            if t_data.get("acceptance_criteria"):
                                crits = t_data["acceptance_criteria"]
                                c_text = "\n".join(f"▫️ {it}" for i, it in enumerate(crits)) if isinstance(crits, list) else str(crits)
                                t_embed.add_field(name="✅ Acceptance Criteria", value=c_text[:1024], inline=False)
                            t_embed.set_footer(text="Type /claim in this thread to take ownership.")
                            await thread.send(embed=t_embed)

                            await asyncio.to_thread(
                                add_thread,
                                thread.id,
                                t_title,
                                folder_clean,
                                target_channel.id,
                                interaction.user.name,
                            )
                            await asyncio.to_thread(
                                mark_ticket_loaded,
                                Path(t_path).name,
                                folder_clean,
                                thread.id,
                                target_channel.id,
                            )
                            loaded_threads.append(thread.mention)
                            await asyncio.sleep(0.8)
                        except Exception as exc:
                            logger.warning("Could not auto-create thread for %s: %s", t_path, exc)

                    if loaded_threads:
                        load_embed = discord.Embed(
                            title="⚡ Auto-Load Live!",
                            description=f"Created **{len(loaded_threads)}** ticket threads:\n" + "\n".join(f"👉 {t}" for t in loaded_threads),
                            color=0x10B981,
                        )
                        await target_channel.send(embed=load_embed)
        except Exception as e:
            logger.error(f"Error in /plan-mvp: {e}")
            await interaction.followup.send(f"❌ Failed to generate MVP plan: {e}")

    # 5. /scan-pdf
    @app_commands.command(
        name="scan-pdf",
        description="Upload a design or problem brief PDF and generate an AI roadmap & ticket bundle",
    )
    @app_commands.describe(
        pdf_attachment="Project specification or proposal PDF",
        folder="Optional folder name in tickets/ (defaults to PDF filename slug)",
    )
    async def scan_pdf(
        self,
        interaction: discord.Interaction,
        pdf_attachment: discord.Attachment,
        folder: Optional[str] = None,
    ):
        await safe_defer(interaction)
        tmp_path = None
        try:
            if not pdf_attachment.filename.lower().endswith(".pdf"):
                await interaction.followup.send("❌ Please attach a valid `.pdf` document.")
                return

            pdf_bytes = await pdf_attachment.read()
            out_folder = folder or Path(pdf_attachment.filename).stem
            out_folder = re.sub(r"[^a-zA-Z0-9_\-]+", "-", out_folder.lower()).strip("-") or "pdf-brief"

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)

            try:
                from pdf_brief_scanner import scan_pdf_brief
                from ai_client import NvidiaAIClient

                client = NvidiaAIClient()
                result = await asyncio.to_thread(
                    scan_pdf_brief,
                    pdf_file=tmp_path,
                    output_folder=out_folder,
                    tickets_dir=TICKETS_DIR,
                    ai_client=client,
                )
                roadmap_file = Path(result.roadmap_file)
                ticket_count = len(result.generated_ticket_files)

                embed = discord.Embed(
                    title=f"📄 AI Brief Analysis: {result.project_name}",
                    description=f"Scanned `{pdf_attachment.filename}` ({result.pages_scanned} pages) • Generated **{ticket_count}** tickets under `tickets/{out_folder}/`.",
                    color=0x8B5CF6,
                )
                ds = result.design_system
                if ds:
                    embed.add_field(
                        name="🎨 Color Palette",
                        value=f"Primary: `{ds.get('primary_color') or ds.get('primaryColor', '#38bdf8')}`\nSecondary: `{ds.get('secondary_color') or ds.get('secondaryColor', '#818cf8')}`",
                        inline=True,
                    )
                    fonts = ds.get("fonts", ["Inter"])
                    embed.add_field(
                        name="🔤 Typography",
                        value=", ".join(fonts) if isinstance(fonts, list) else str(fonts),
                        inline=True,
                    )
                if result.features:
                    embed.add_field(
                        name="✨ Core Features",
                        value="\n".join(f"• {f}" for f in result.features[:5]),
                        inline=False,
                    )
                embed.set_footer(text=f"CapStoneFlow • Run /load-tickets {out_folder} to create threads.")

                if roadmap_file.exists():
                    f = discord.File(str(roadmap_file), filename="ROADMAP.md")
                    await interaction.followup.send(embed=embed, file=f)
                else:
                    await interaction.followup.send(embed=embed)
            except Exception as exc:
                logger.warning("pdf_brief_scanner encountered error, falling back to ai_service: %s", exc)
                text = await asyncio.to_thread(_extract_pdf_text, pdf_bytes)
                if not text.strip():
                    await interaction.followup.send("⚠️ Could not extract text from this PDF (it might be scanned images without OCR).")
                    return

                analysis = await asyncio.to_thread(ai_service.analyze_pdf_brief, text)
                out_dir = Path(TICKETS_DIR) / out_folder
                out_dir.mkdir(parents=True, exist_ok=True)

                roadmap_content = f"# {analysis.get('projectTitle', out_folder)} Roadmap\n\n"
                for p in analysis.get("phases", []):
                    roadmap_content += f"## Phase {p.get('phaseNumber')}: {p.get('title')}\n"
                    for d in p.get("deliverables", []):
                        roadmap_content += f"- {d}\n"
                    roadmap_content += "\n"

                roadmap_file = out_dir / "ROADMAP.md"
                roadmap_file.write_text(roadmap_content, encoding="utf-8")

                ticket_count = 0
                for idx, feat in enumerate(analysis.get("coreFeatures", []), 1):
                    slug = re.sub(r"[^a-z0-9]+", "-", feat.lower()).strip("-")[:40] or f"feature-{idx}"
                    ticket_md = (
                        f"# Implement {feat}\n\n"
                        f"## Problem\nImplement core feature extracted from brief: {feat}\n\n"
                        f"## What to Fix\n1. Scaffold {feat} architecture\n2. Add test verification\n\n"
                        f"## Acceptance Criteria\n- [ ] {feat} is fully functional\n- [ ] Automated tests pass\n"
                    )
                    (out_dir / f"pdf-{idx:02d}-{slug}.md").write_text(ticket_md, encoding="utf-8")
                    ticket_count += 1

                embed = discord.Embed(
                    title=f"📄 AI Brief Analysis: {analysis.get('projectTitle', pdf_attachment.filename)}",
                    description=f"Generated `ROADMAP.md` and **{ticket_count}** tickets under `tickets/{out_folder}/`.",
                    color=0x8B5CF6,
                )
                ds = analysis.get("designSystem", {})
                embed.add_field(
                    name="🎨 Color Palette",
                    value=f"Primary: `{ds.get('primaryColor', '#38bdf8')}`\nSecondary: `{ds.get('secondaryColor', '#818cf8')}`",
                    inline=True,
                )
                embed.add_field(
                    name="🔤 Typography",
                    value=", ".join(ds.get("fonts", ["Inter"])),
                    inline=True,
                )
                features = "\n".join([f"• {f}" for f in analysis.get("coreFeatures", [])[:5]])
                embed.add_field(
                    name="✨ Core Features",
                    value=features or "No features listed",
                    inline=False,
                )
                embed.set_footer(text=f"CapStoneFlow • Run /load-tickets {out_folder} to publish.")

                file = discord.File(str(roadmap_file), filename="ROADMAP.md")
                await interaction.followup.send(embed=embed, file=file)
        except Exception as e:
            logger.error(f"Error in /scan-pdf: {e}")
            await interaction.followup.send(f"❌ Failed to process PDF brief: {e}")
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    # 6. /ask-ai
    @app_commands.command(
        name="ask-ai",
        description="Ask technical, architecture, or coding questions to CapStoneFlow AI",
    )
    @app_commands.describe(question="Your question about coding, architecture, debugging, or system design")
    async def ask_ai(self, interaction: discord.Interaction, question: str):
        await safe_defer(interaction)
        try:
            answer = await asyncio.to_thread(
                ai_service.generate_text,
                question,
                system_prompt="You are an expert software engineer and technical architect assisting a hackathon team. Provide clear, direct, actionable explanations with concise code examples where appropriate.",
                temperature=0.3,
            )

            from math_renderer import has_latex, render_equations_to_single_png

            if has_latex() and "$$" in answer:
                png_bytes = await asyncio.to_thread(render_equations_to_single_png, answer)
                if png_bytes:
                    file = discord.File(io.BytesIO(png_bytes), filename="equation.png")
                    clean_text = re.sub(r"\$\$.*?\$\$", "", answer, flags=re.DOTALL).strip()
                    embed = discord.Embed(
                        title="💡 AI Technical Response",
                        description=clean_text[:4000],
                        color=0x38BDF8,
                    )
                    embed.set_image(url="attachment://equation.png")
                    embed.set_footer(text="CapStoneFlow AI • Rendered with Math Engine")
                    await interaction.followup.send(embed=embed, file=file)
                    return

            embed = discord.Embed(
                title="💡 AI Technical Response",
                description=answer[:4000],
                color=0x38BDF8,
            )
            embed.set_footer(text="CapStoneFlow AI • Hackathon Co-Pilot")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /ask-ai: {e}")
            await interaction.followup.send(f"❌ Error getting AI answer: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ScannerCog(bot))
