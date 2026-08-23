"""Scanner Cog for automated codebase analysis, PDF brief parsing, and roadmap generation."""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional
from services.code_scanner import scanner_service
from services.ai_service import ai_service
from config import TICKETS_DIR, DEFAULT_REPO_URL, GITHUB_TOKEN

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

class ScannerCog(commands.Cog, name="Scanner"):
    """Handles codebase scanning, AI brief analysis, and roadmap generation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /scan-project
    @app_commands.command(name="scan-project", description="Scan a local folder and generate categorized ticket markdown files")
    @app_commands.describe(path="Path to the directory to scan", folder="Folder name under tickets/ to store generated files")
    async def scan_project(self, interaction: discord.Interaction, path: str, folder: str = "scan-results"):
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
                    summary_fields.append((cat.replace('_', ' ').title(), len(items)))

            embed = discord.Embed(
                title="🔍 Project Scan Complete",
                description=f"Scanned `{target_path.name}` • Generated **{ticket_count}** ticket files in `tickets/{folder}/`",
                color=0x38bdf8
            )

            for name, count in summary_fields:
                embed.add_field(name=name, value=f"`{count}` occurrences", inline=True)

            embed.set_footer(text="Run /load-tickets to publish these tickets into Discord threads.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-project: {e}")
            await interaction.followup.send(f"❌ Scan failed: {e}")

    # 2. /scan-repo
    @app_commands.command(name="scan-repo", description="Clone and scan the project GitHub repository")
    @app_commands.describe(repo_url="GitHub Repository URL (defaults to USCCE)", folder="Ticket output folder")
    async def scan_repo(self, interaction: discord.Interaction, repo_url: str = DEFAULT_REPO_URL, folder: str = "repo-scan"):
        await safe_defer(interaction)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                await interaction.followup.send(f"⏳ Cloning `{repo_url}` and analyzing codebase...")
                
                clone_target = repo_url
                if GITHUB_TOKEN and "github.com" in repo_url:
                    clean_repo = repo_url.replace("https://github.com/", "").replace("http://github.com/", "").replace(".git", "")
                    clone_target = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{clean_repo}.git"

                # Clone shallow
                res = await asyncio.to_thread(
                    subprocess.run,
                    ["git", "clone", "--depth", "1", clone_target, tmpdir],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    await interaction.channel.send(f"❌ Failed to clone repository: {res.stderr[:200]}")
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
                    color=0x10b981
                )
                await interaction.channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-repo: {e}")
            await interaction.channel.send(f"❌ Error scanning repo: {e}")

    # 3. /scan-pdf
    @app_commands.command(name="scan-pdf", description="Upload a PDF brief and generate an AI roadmap & ticket bundle")
    @app_commands.describe(pdf_attachment="Project specification or proposal PDF")
    async def scan_pdf(self, interaction: discord.Interaction, pdf_attachment: discord.Attachment):
        await safe_defer(interaction)
        try:
            if not pdf_attachment.filename.lower().endswith(".pdf"):
                await interaction.followup.send("❌ Please attach a valid `.pdf` document.")
                return

            pdf_bytes = await pdf_attachment.read()
            
            # Extract text using pypdf outside Discord's event loop.
            text = await asyncio.to_thread(_extract_pdf_text, pdf_bytes)

            if not text.strip():
                await interaction.followup.send("⚠️ Could not extract text from this PDF (it might be scanned images).")
                return

            # AI Analysis via Gemini Free Tier
            analysis = await asyncio.to_thread(ai_service.analyze_pdf_brief, text)

            embed = discord.Embed(
                title=f"📄 AI Brief Analysis: {analysis.get('projectTitle', pdf_attachment.filename)}",
                description="Parsed design system tokens, core milestones, and technical scope.",
                color=0x8b5cf6
            )

            ds = analysis.get("designSystem", {})
            embed.add_field(name="🎨 Color Palette", value=f"Primary: `{ds.get('primaryColor', '#38bdf8')}`\nSecondary: `{ds.get('secondaryColor', '#818cf8')}`", inline=True)
            embed.add_field(name="🔤 Typography", value=", ".join(ds.get("fonts", ["Inter"])), inline=True)

            features = "\n".join([f"• {f}" for f in analysis.get("coreFeatures", [])[:5]])
            embed.add_field(name="✨ Core Features", value=features or "No features listed", inline=False)

            phases = "\n".join([f"**Phase {p.get('phaseNumber')}: {p.get('title')}** ({len(p.get('deliverables', []))} deliverables)" for p in analysis.get("phases", [])])
            embed.add_field(name="🗺️ Roadmap Outline", value=phases or "Standard 5-Phase Model", inline=False)

            embed.set_footer(text="Powered by Google Gemini 1.5 Flash • Free AI Engine")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /scan-pdf: {e}")
            await interaction.followup.send(f"❌ Failed to process PDF brief: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ScannerCog(bot))


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract PDF text away from Discord's event loop."""
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
