"""Admin and Ticket Loader Cog."""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import glob
import logging
from pathlib import Path
from datetime import time, timezone
from database import (
    add_thread, is_ticket_loaded, mark_ticket_loaded,
    set_setting, get_setting, get_threads_by_status,
    set_user_role, get_user_roles
)
from ticket_loader import parse_ticket_file
from config import TICKETS_DIR

logger = logging.getLogger(__name__)

async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer()

class AdminCog(commands.Cog, name="Admin"):
    """Handles ticket loading, channel configuration, and user roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_summary_task.start()

    def cog_unload(self):
        self.daily_summary_task.cancel()

    # 1. /load-tickets
    @app_commands.command(name="load-tickets", description="Load .md ticket files from a folder and create Discord threads")
    @app_commands.describe(folder="Folder inside tickets/ (e.g. sprint-1)")
    async def load_tickets(self, interaction: discord.Interaction, folder: str):
        await safe_defer(interaction)
        try:
            target_dir = Path(TICKETS_DIR) / folder
            if not target_dir.exists():
                await interaction.followup.send(f"❌ Folder `{TICKETS_DIR}/{folder}` does not exist.")
                return

            md_files = list(target_dir.glob("*.md"))
            if not md_files:
                await interaction.followup.send(f"⚠️ No `.md` files found in `{TICKETS_DIR}/{folder}`.")
                return

            loaded_count = 0
            skipped_count = 0

            for filepath in md_files:
                rel_path = str(filepath.relative_to(Path(TICKETS_DIR)))
                if is_ticket_loaded(rel_path):
                    skipped_count += 1
                    continue

                ticket_data = parse_ticket_file(str(filepath))
                title = ticket_data.get("title", filepath.stem)
                thread_name = f"[OPEN]{title}"[:100]

                # Create thread in the current channel
                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    auto_archive_duration=1440,
                    type=discord.ChannelType.public_thread
                )

                # Post initial ticket embed
                embed = discord.Embed(
                    title=f"📋 Ticket: {title}",
                    description=ticket_data.get("problem", "No problem statement provided."),
                    color=0x38bdf8
                )
                if ticket_data.get("what_to_fix"):
                    embed.add_field(name="🛠️ What to Fix", value=ticket_data["what_to_fix"][:1024], inline=False)
                if ticket_data.get("acceptance_criteria"):
                    embed.add_field(name="✅ Acceptance Criteria", value=ticket_data["acceptance_criteria"][:1024], inline=False)
                if ticket_data.get("related_files"):
                    embed.add_field(name="📁 Related Files", value=ticket_data["related_files"][:1024], inline=False)

                embed.set_footer(text="Type /claim to take ownership of this ticket.")
                await thread.send(embed=embed)

                add_thread(thread.id, title, "OPEN")
                mark_ticket_loaded(rel_path)
                loaded_count += 1

            embed = discord.Embed(
                title="📦 Ticket Batch Import",
                description=f"Loaded **{loaded_count}** new tickets into threads.\nSkipped **{skipped_count}** already-loaded tickets.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /load-tickets: {e}")
            await interaction.followup.send(f"❌ Error loading tickets: {e}")

    # 2. /setreminderschannel
    @app_commands.command(name="setreminderschannel", description="Set channel for daily 8:00 AM PHT ticket summaries")
    async def set_reminders_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await safe_defer(interaction)
        set_setting("reminders_channel_id", str(channel.id))
        await interaction.followup.send(f"✅ Daily sprint reminders channel set to {channel.mention}.")

    # 3. /assign-role
    @app_commands.command(name="assign-role", description="Set your active workspace role (Developer or QA)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Developer (Claim & Resolve)", value="dev"),
        app_commands.Choice(name="QA (Verify & Review)", value="qa"),
    ])
    async def assign_role(self, interaction: discord.Interaction, role: str):
        await safe_defer(interaction)
        is_dev = role == "dev"
        is_qa = role == "qa"
        set_user_role(interaction.user.id, is_dev=is_dev, is_qa=is_qa, is_pm=False)
        
        role_label = "Developer" if is_dev else "QA Reviewer"
        await interaction.followup.send(f"🎉 Your role has been set to **{role_label}**.")

    # Daily Summary Task at 8:00 AM PHT (00:00 UTC)
    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
    async def daily_summary_task(self):
        channel_id = get_setting("reminders_channel_id")
        if not channel_id:
            return
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        open_tickets = get_threads_by_status("OPEN")
        claimed_tickets = get_threads_by_status("CLAIMED")
        review_tickets = get_threads_by_status("PENDING-REVIEW")

        embed = discord.Embed(
            title="🌅 Daily Sprint Ticket Briefing",
            description="Good morning team! Here is the current ticket pipeline status:",
            color=0x6366f1
        )
        embed.add_field(name="🟢 Open Tickets", value=f"`{len(open_tickets)}` unassigned", inline=True)
        embed.add_field(name="🟡 In Progress", value=f"`{len(claimed_tickets)}` claimed", inline=True)
        embed.add_field(name="🔵 Pending Review", value=f"`{len(review_tickets)}` waiting for QA", inline=True)
        embed.set_footer(text="CapStoneFlow • Daily Standup Pipeline")

        await channel.send(embed=embed)

    @daily_summary_task.before_loop
    async def before_daily_summary(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
