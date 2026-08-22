"""Admin, Ticket Loader, and Ticketing System Maintenance Cog."""
import asyncio
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
    set_user_role, get_user_roles, remove_thread_record,
    clear_loaded_tickets, update_thread_status, get_thread
)
from ticket_loader import parse_ticket_file, get_available_folders, load_tickets_from_folder
from config import TICKETS_DIR

logger = logging.getLogger(__name__)

async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)

class AdminCog(commands.Cog, name="Admin"):
    """Handles ticket loading, maintenance, channel configuration, and user roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_summary_task.start()

    def cog_unload(self):
        self.daily_summary_task.cancel()

    # 1. /load-tickets
    @app_commands.command(name="load-tickets", description="Import markdown tickets from a folder and create Discord threads")
    @app_commands.describe(folder="Folder inside tickets/ (e.g. borneo, intramurals2026)")
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
                filename = filepath.name
                if await asyncio.to_thread(is_ticket_loaded, filename, folder):
                    skipped_count += 1
                    continue

                ticket_data = parse_ticket_file(str(filepath))
                title = ticket_data.get("title") or filepath.stem
                priority = ticket_data.get("priority")
                prefix = f"[{priority}]" if priority else "[OPEN]"
                thread_name = f"{prefix} {title}"[:100]

                # Create thread in the current channel
                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    auto_archive_duration=1440,
                    type=discord.ChannelType.public_thread
                )

                # Format description & lists
                problem = ticket_data.get("problem") or "No problem description provided."
                
                embed = discord.Embed(
                    title=f"📋 Ticket: {title}",
                    description=problem[:2000],
                    color=0xef4444 if priority == "CRITICAL" else (0xf59e0b if priority == "PRIORITY" else 0x38bdf8)
                )

                if priority:
                    embed.add_field(name="🚨 Priority", value=f"`{priority}`", inline=True)
                embed.add_field(name="📂 Folder", value=f"`{folder}`", inline=True)

                if ticket_data.get("what_to_fix"):
                    items = ticket_data["what_to_fix"]
                    fix_text = "\n".join(f"**{i+1}.** {item}" for i, item in enumerate(items)) if isinstance(items, list) else str(items)
                    embed.add_field(name="🛠️ What to Fix", value=fix_text[:1024], inline=False)

                if ticket_data.get("acceptance_criteria"):
                    items = ticket_data["acceptance_criteria"]
                    criteria_text = "\n".join(f"▫️ {item}" for i, item in enumerate(items)) if isinstance(items, list) else str(items)
                    embed.add_field(name="✅ Acceptance Criteria", value=criteria_text[:1024], inline=False)

                if ticket_data.get("related_files"):
                    items = ticket_data["related_files"]
                    files_text = "\n".join(f"📄 `{item}`" for item in items) if isinstance(items, list) else str(items)
                    embed.add_field(name="📁 Related Files", value=files_text[:1024], inline=False)

                embed.set_footer(text="Type /claim in this thread to take ownership.")
                await thread.send(embed=embed)

                await asyncio.to_thread(
                    add_thread,
                    thread.id,
                    title,
                    folder,
                    interaction.channel_id,
                    interaction.user.name,
                )
                await asyncio.to_thread(
                    mark_ticket_loaded,
                    filename,
                    folder,
                    thread.id,
                    interaction.channel_id,
                )
                loaded_count += 1

            embed = discord.Embed(
                title="📦 Ticket Batch Import Complete",
                description=f"✅ Created **{loaded_count}** new ticket threads.\n⏩ Skipped **{skipped_count}** previously loaded tickets.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /load-tickets: {e}")
            await interaction.followup.send(f"❌ Error loading tickets: {e}")

    # 2. /cleanup-tickets
    @app_commands.command(name="cleanup-tickets", description="Archive and clean up completed CLOSED tickets in this channel")
    @app_commands.describe(action="Cleanup mode")
    @app_commands.choices(action=[
        app_commands.Choice(name="Archive Closed Threads (Clean Discord channel)", value="archive_closed"),
        app_commands.Choice(name="Purge Closed Records from Database", value="purge_closed_db"),
    ])
    async def cleanup_tickets(self, interaction: discord.Interaction, action: str):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles['is_pm']:
                await interaction.followup.send("❌ Only Project Managers can run ticket cleanup.")
                return

            grouped_tickets = await asyncio.to_thread(get_threads_by_status)
            closed_tickets = grouped_tickets.get("CLOSED", [])
            if not closed_tickets:
                await interaction.followup.send("ℹ️ No CLOSED tickets found to clean up.")
                return

            archived_count = 0
            for t in closed_tickets:
                thread_id = t['thread_id']
                try:
                    thread = interaction.guild.get_thread(thread_id)
                    if thread:
                        if action == "archive_closed":
                            await thread.edit(archived=True, locked=True)
                            archived_count += 1
                    if action == "purge_closed_db":
                        await asyncio.to_thread(remove_thread_record, thread_id)
                        archived_count += 1
                except Exception as ex:
                    logger.warning(f"Failed to process thread {thread_id}: {ex}")

            embed = discord.Embed(
                title="🧹 Ticket Cleanup Completed",
                description=f"Successfully processed **{archived_count}** closed tickets.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /cleanup-tickets: {e}")
            await interaction.followup.send(f"❌ Error during cleanup: {e}")

    # 3. /clear
    @app_commands.command(
        name="clear",
        description="Clear messages here and close the ticket thread if used inside one",
    )
    @app_commands.describe(
        amount="Maximum number of recent messages to delete (1-1000; default 100)",
    )
    async def clear_channel(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 1000] = 100,
    ):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles["is_pm"]:
                await interaction.followup.send(
                    "❌ Only Project Managers can clear messages or close ticket threads.",
                    ephemeral=True,
                )
                return

            channel = interaction.channel
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                await interaction.followup.send(
                    "❌ This command can only be used in a text channel or ticket thread.",
                    ephemeral=True,
                )
                return

            member = interaction.guild.get_member(self.bot.user.id) if interaction.guild else None
            if member is None:
                await interaction.followup.send(
                    "❌ I could not verify my server permissions. Please try again shortly.",
                    ephemeral=True,
                )
                return

            permissions = channel.permissions_for(member)
            if not permissions.manage_messages:
                await interaction.followup.send(
                    "❌ I need the **Manage Messages** permission in this channel.",
                    ephemeral=True,
                )
                return
            if isinstance(channel, discord.Thread) and not permissions.manage_threads:
                await interaction.followup.send(
                    "❌ I need the **Manage Threads** permission to close this ticket thread.",
                    ephemeral=True,
                )
                return

            deleted = await channel.purge(
                limit=int(amount),
                bulk=True,
                reason=f"CapStoneFlow /clear by {interaction.user}",
            )

            closed = False
            database_warning = None
            if isinstance(channel, discord.Thread):
                thread_info = None
                try:
                    thread_info = await asyncio.to_thread(get_thread, channel.id)
                except Exception as exc:
                    database_warning = "The database status could not be updated."
                    logger.warning("Could not load ticket %s before /clear: %s", channel.id, exc)

                ticket_name = (thread_info or {}).get("ticket_name") or channel.name
                await channel.edit(
                    name=f"[CLOSED] {ticket_name}"[:100],
                    archived=True,
                    locked=True,
                    reason=f"CapStoneFlow /clear by {interaction.user}",
                )
                closed = True

                if thread_info:
                    try:
                        await asyncio.to_thread(update_thread_status, channel.id, "CLOSED")
                    except Exception as exc:
                        database_warning = "The database status could not be updated."
                        logger.warning("Could not mark ticket %s closed after /clear: %s", channel.id, exc)

            summary = f"✅ Cleared **{len(deleted)}** message(s)."
            if closed:
                summary += " The ticket thread was archived and locked."
            if database_warning:
                summary += f" ⚠️ {database_warning}"
            await interaction.followup.send(summary, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Discord denied the cleanup. Check **Manage Messages** and **Manage Threads** permissions.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error in /clear: {e}")
            await interaction.followup.send(
                "❌ Could not clear this channel. Please try again or check the bot permissions.",
                ephemeral=True,
            )

    # 4. /reset-ticket
    @app_commands.command(name="reset-ticket", description="Reset current ticket thread back to OPEN state (PM only)")
    async def reset_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be run inside a ticket thread.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles['is_pm']:
                await interaction.followup.send("❌ Only Project Managers can reset ticket states.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info:
                await interaction.followup.send("❌ Thread is not tracked in the database.")
                return

            ticket_name = thread_info['ticket_name']
            new_name = f"[OPEN] {ticket_name}"[:100]
            await thread.edit(name=new_name)
            await asyncio.to_thread(update_thread_status, thread.id, "OPEN")

            embed = discord.Embed(
                title="🔄 Ticket Reset to OPEN",
                description=f"Ticket state has been cleared and reset to `[OPEN]` by {interaction.user.mention}.",
                color=0x38bdf8
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /reset-ticket: {e}")
            await interaction.followup.send(f"❌ Error resetting ticket: {e}")

    # 4. /clear-folder-tickets
    @app_commands.command(name="clear-folder-tickets", description="Reset import cache for a folder so tickets can be reloaded")
    @app_commands.describe(folder="Folder inside tickets/ to clear")
    async def clear_folder(self, interaction: discord.Interaction, folder: str):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles['is_pm']:
                await interaction.followup.send("❌ Only Project Managers can clear folder import caches.")
                return

            count = await asyncio.to_thread(clear_loaded_tickets, folder)
            embed = discord.Embed(
                title="🗑️ Folder Import Cache Cleared",
                description=f"Cleared **{count}** ticket import markers for folder `{folder}`.\nYou can now run `/load-tickets {folder}` to re-import.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /clear-folder-tickets: {e}")
            await interaction.followup.send(f"❌ Error clearing folder: {e}")

    # 5. /ticket-folders
    @app_commands.command(name="ticket-folders", description="List all available ticket folders in the repository")
    async def list_folders(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        folders = get_available_folders()
        if not folders:
            await interaction.followup.send("📂 No ticket folders found in `tickets/`.")
            return

        lines = []
        for folder in folders:
            folder_path = Path(TICKETS_DIR) / folder
            count = len(list(folder_path.glob("*.md")))
            lines.append(f"📁 **`{folder}`** — `{count}` ticket(s)")

        embed = discord.Embed(
            title="📂 Available Ticket Folders",
            description="\n".join(lines),
            color=0x6366f1
        )
        embed.set_footer(text="Use /load-tickets <folder> to create threads.")
        await interaction.followup.send(embed=embed)

    # 6. /setreminderschannel
    @app_commands.command(name="setreminderschannel", description="Set channel for daily 8:00 AM PHT ticket summaries")
    async def set_reminders_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await safe_defer(interaction)
        await asyncio.to_thread(set_setting, "reminders_channel_id", str(channel.id))
        await interaction.followup.send(f"✅ Daily sprint reminders channel set to {channel.mention}.")

    # 7. /assign-role
    @app_commands.command(name="assign-role", description="Set your active workspace role (Developer, QA, or PM)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Developer (Claim & Resolve)", value="dev"),
        app_commands.Choice(name="QA Reviewer (Verify & Review)", value="qa"),
        app_commands.Choice(name="Project Manager (Lead & Manage)", value="pm"),
    ])
    async def assign_role(self, interaction: discord.Interaction, role: str):
        await safe_defer(interaction)
        is_dev = role == "dev"
        is_qa = role == "qa"
        is_pm = role == "pm"
        await asyncio.to_thread(
            set_user_role,
            interaction.user.id,
            interaction.user.name,
            is_developer=is_dev,
            is_qa=is_qa,
            is_pm=is_pm,
        )
        
        role_label = "Developer" if is_dev else ("QA Reviewer" if is_qa else "Project Manager")
        await interaction.followup.send(f"🎉 Your role has been set to **{role_label}**.")

    # Daily Summary Task at 8:00 AM PHT (00:00 UTC)
    @tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
    async def daily_summary_task(self):
        channel_id = await asyncio.to_thread(get_setting, "reminders_channel_id")
        if not channel_id:
            return
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return

        grouped_tickets = await asyncio.to_thread(get_threads_by_status)
        open_tickets = grouped_tickets.get("OPEN", [])
        claimed_tickets = grouped_tickets.get("CLAIMED", [])
        review_tickets = grouped_tickets.get("PENDING-REVIEW", [])

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
