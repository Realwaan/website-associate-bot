"""Admin, Ticket Loader, and Ticketing System Maintenance Cog."""
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import glob
import logging
import re
from pathlib import Path
from datetime import time, timezone
from typing import Optional
from database import (
    add_thread, is_ticket_loaded, mark_ticket_loaded,
    set_setting, get_setting, get_threads_by_status,
    set_user_role, get_user_roles, remove_thread_record,
    clear_loaded_tickets, update_thread_status, get_thread,
    get_db,
)
from ticket_loader import parse_ticket_file, get_available_folders, load_tickets_from_folder
from config import TICKETS_DIR
from math_renderer import has_latex

logger = logging.getLogger(__name__)

_THREAD_STATUS_RE = re.compile(
    r"^\[(OPEN|CLAIMED|PENDING-REVIEW|REVIEWED|CLOSED)\](?:\[[^\]]+\])?\s*(.*)$",
    re.IGNORECASE,
)
_PRIORITY_STATUS_RE = re.compile(
    r"^\[(?:CRITICAL|PRIORITY|HIGH|MEDIUM|LOW)\]\s*"
    r"\[(OPEN|CLAIMED|PENDING-REVIEW|REVIEWED|CLOSED)\]"
    r"(?:\[[^\]]+\])?\s*(.*)$",
    re.IGNORECASE,
)
_PRIORITY_ONLY_RE = re.compile(
    r"^\[(?:CRITICAL|PRIORITY|HIGH|MEDIUM|LOW)\]\s*(.*)$",
    re.IGNORECASE,
)


def _parse_thread_status(name: str) -> tuple[str | None, str]:
    """Extract a tracked status and clean ticket name from a thread title."""
    clean_name = (name or "").strip()
    match = _THREAD_STATUS_RE.match(clean_name) or _PRIORITY_STATUS_RE.match(clean_name)
    if not match:
        priority_match = _PRIORITY_ONLY_RE.match(clean_name)
        if priority_match:
            return "OPEN", priority_match.group(1).strip()
        return None, clean_name
    return match.group(1).upper(), match.group(2).strip()


def _normalize_ticket_name(value: str) -> str:
    """Normalize titles so markdown files can be matched to Discord threads."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _rebuild_thread_record(
    thread_id: int,
    ticket_name: str,
    folder: str,
    channel_id: int,
    status: str,
    created_by: str,
    filename: str | None,
) -> None:
    """Persist one recovered thread in a worker thread."""
    add_thread(thread_id, ticket_name, folder, channel_id, created_by)
    update_thread_status(thread_id, status)
    if filename:
        mark_ticket_loaded(filename, folder, thread_id, channel_id)

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

class AdminCog(commands.Cog, name="Admin"):
    """Handles ticket loading, maintenance, channel configuration, and user roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            self.daily_summary_task.start()
        except RuntimeError:
            pass

    def cog_unload(self):
        try:
            self.daily_summary_task.cancel()
        except Exception:
            pass

    # 1. /load-tickets
    @app_commands.command(name="load-tickets", description="Import markdown tickets from a folder and create Discord threads")
    @app_commands.describe(
        folder="Folder inside tickets/ (e.g. borneo, intramurals2026)",
        channel="Target text channel (defaults to the current channel)",
    )
    async def load_tickets(
        self,
        interaction: discord.Interaction,
        folder: str,
        channel: Optional[discord.TextChannel] = None,
    ):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles["is_pm"]:
                await interaction.followup.send(
                    "❌ Only Project Managers can load tickets.",
                    ephemeral=True,
                )
                return

            target_channel = channel or interaction.channel
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.followup.send(
                    "❌ Choose a text channel or run this command in a text channel.",
                    ephemeral=True,
                )
                return

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
                # Keep the lifecycle prefix as OPEN so /claim and /rebuild-db
                # can recognize every imported ticket. Priority is shown in
                # the embed instead of replacing the workflow status.
                thread_name = f"[OPEN] {title}"[:100]

                # Create thread in the selected target channel with 429 backoff resilience
                thread = None
                for attempt in range(2):
                    try:
                        thread = await target_channel.create_thread(
                            name=thread_name,
                            auto_archive_duration=1440,
                            type=discord.ChannelType.public_thread
                        )
                        break
                    except discord.HTTPException as err:
                        if err.status == 429 and attempt == 0:
                            logger.warning("Discord 429 during thread creation; backing off 2.0s...")
                            await asyncio.sleep(2.0)
                        else:
                            raise

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
                    target_channel.id,
                    interaction.user.name,
                )
                await asyncio.to_thread(
                    mark_ticket_loaded,
                    filename,
                    folder,
                    thread.id,
                    target_channel.id,
                )
                loaded_count += 1
                # Sleep briefly to respect Discord burst rate limits for thread creation
                await asyncio.sleep(0.8)

            embed = discord.Embed(
                title="📦 Ticket Batch Import Complete",
                description=f"✅ Created **{loaded_count}** new ticket threads in {target_channel.mention}.\n⏩ Skipped **{skipped_count}** previously loaded tickets.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /load-tickets: {e}")
            await interaction.followup.send(f"❌ Error loading tickets: {e}")

    # 2. /rebuild-db
    @app_commands.command(
        name="rebuild-db",
        description="Recover ticket database records from existing Discord threads",
    )
    @app_commands.describe(
        folder="Folder containing the ticket markdown files",
        channel="Text channel containing the ticket threads",
    )
    async def rebuild_db(
        self,
        interaction: discord.Interaction,
        folder: str,
        channel: discord.TextChannel,
    ):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles["is_pm"]:
                await interaction.followup.send(
                    "❌ Only Project Managers can rebuild the ticket database.",
                    ephemeral=True,
                )
                return

            folder_path = Path(TICKETS_DIR) / folder
            if not folder_path.is_dir():
                await interaction.followup.send(
                    f"❌ Folder `{folder}` was not found in `{TICKETS_DIR}/`.",
                    ephemeral=True,
                )
                return

            tickets = await asyncio.to_thread(load_tickets_from_folder, folder)
            name_to_filename = {}
            for ticket in tickets:
                display_name = ticket.get("title") or ticket.get("name") or ""
                filename = ticket.get("name")
                if filename:
                    name_to_filename[_normalize_ticket_name(display_name)] = filename

            threads_by_id = {thread.id: thread for thread in channel.threads}
            try:
                async for thread in channel.archived_threads(limit=None):
                    threads_by_id[thread.id] = thread
            except discord.HTTPException as exc:
                logger.warning("Could not read archived threads in %s: %s", channel.id, exc)

            rebuilt_count = 0
            skipped_count = 0
            unmatched_count = 0
            for thread in threads_by_id.values():
                status, ticket_name = _parse_thread_status(thread.name)
                if not status or not ticket_name:
                    skipped_count += 1
                    continue

                filename = name_to_filename.get(_normalize_ticket_name(ticket_name))
                await asyncio.to_thread(
                    _rebuild_thread_record,
                    thread.id,
                    ticket_name,
                    folder,
                    channel.id,
                    status,
                    interaction.user.name,
                    filename,
                )
                rebuilt_count += 1
                if not filename:
                    unmatched_count += 1

            embed = discord.Embed(
                title="🧰 Ticket Database Rebuild Complete",
                description=(
                    f"Rebuilt **{rebuilt_count}** ticket record(s) from {channel.mention}.\n"
                    f"Skipped **{skipped_count}** thread(s) without a recognized ticket status.\n"
                    f"Unmatched **{unmatched_count}** thread(s) to markdown files."
                ),
                color=0x10B981 if rebuilt_count else 0xF59E0B,
            )
            embed.set_footer(text="Existing Discord threads were preserved.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.exception("Error in /rebuild-db: %s", e)
            await interaction.followup.send(
                "❌ Could not rebuild the ticket database. Check the folder, channel, and database connection.",
                ephemeral=True,
            )

    # 3. /cleanup-tickets
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

            try:
                deleted = await channel.purge(
                    limit=int(amount),
                    bulk=True,
                    reason=f"CapStoneFlow /clear by {interaction.user}",
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Discord denied message deletion. Check **Manage Messages** in this channel.",
                    ephemeral=True,
                )
                return
            except Exception:
                logger.exception("Message purge failed during /clear in channel %s", channel.id)
                await interaction.followup.send(
                    "❌ I could not finish deleting messages in this channel.",
                    ephemeral=True,
                )
                return

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
                target_name = f"[CLOSED] {ticket_name}"[:100]
                edit_kwargs = {
                    "archived": True,
                    "locked": True,
                    "reason": f"CapStoneFlow /clear by {interaction.user}",
                }
                if getattr(channel, "name", None) != target_name:
                    edit_kwargs["name"] = target_name

                try:
                    await asyncio.wait_for(channel.edit(**edit_kwargs), timeout=2.0)
                    closed = True
                except (asyncio.TimeoutError, TimeoutError):
                    logger.warning("Thread edit timed out (>2.0s) during /clear on %s", channel.id)
                    closed = True
                except discord.Forbidden:
                    database_warning = "Messages were cleared, but Discord denied closing the ticket thread."
                    logger.warning("Could not archive/lock ticket %s after /clear: missing thread permission", channel.id)
                except discord.HTTPException as exc:
                    if exc.status in (429, 500, 502, 503, 504):
                        logger.warning("Discord API %s during /clear thread edit on %s: %s", exc.status, channel.id, exc)
                        closed = True
                    else:
                        database_warning = "Messages were cleared, but the ticket thread could not be closed."
                        logger.exception("Could not archive/lock ticket %s after /clear: %s", channel.id, exc)
                except Exception:
                    database_warning = "Messages were cleared, but the ticket thread could not be closed."
                    logger.exception("Could not archive/lock ticket %s after /clear", channel.id)

                if thread_info and closed:
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
            try:
                await interaction.followup.send(summary, ephemeral=True)
            except discord.HTTPException:
                # The cleanup already completed; do not turn a successful purge
                # into an application-command failure if the interaction webhook
                # expires while Discord is processing the thread edit.
                logger.warning("Could not send /clear completion response for channel %s", channel.id)
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

    # 4. /commands
    @app_commands.command(
        name="commands",
        description="Show the available CapStoneFlow bot commands",
    )
    async def show_commands(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            commands = sorted(self.bot.tree.get_commands(), key=lambda command: command.name)
            lines = [
                f"`/{command.name}` — {command.description or 'No description available.'}"
                for command in commands
            ]

            chunks: list[str] = []
            current: list[str] = []
            current_length = 0
            for line in lines:
                if current and current_length + len(line) + 1 > 950:
                    chunks.append("\n".join(current))
                    current = []
                    current_length = 0
                current.append(line)
                current_length += len(line) + 1
            if current:
                chunks.append("\n".join(current))

            embed = discord.Embed(
                title="📖 CapStoneFlow Commands",
                description="Use ticket lifecycle commands inside ticket threads. PM-only commands require the Project Manager role.",
                color=0x6366F1,
            )
            for index, chunk in enumerate(chunks or ["No commands are currently synchronized."]):
                embed.add_field(
                    name="Available Commands" if index == 0 else "Available Commands (continued)",
                    value=chunk,
                    inline=False,
                )
            embed.set_footer(text="CapStoneFlow • Use /commands any time for this guide.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.exception("Error in /commands: %s", e)
            await interaction.followup.send(
                "❌ Could not load the command guide.",
                ephemeral=True,
            )

    # 5. /reset-ticket
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
            if getattr(thread, "name", None) != new_name:
                try:
                    await asyncio.wait_for(thread.edit(name=new_name), timeout=2.0)
                except (asyncio.TimeoutError, TimeoutError):
                    logger.warning("Timeout renaming thread %s during reset", thread.id)
                except discord.HTTPException as exc:
                    if exc.status in (429, 500, 502, 503, 504):
                        logger.warning("Discord API %s renaming thread %s during reset: %s", exc.status, thread.id, exc)
                    else:
                        logger.warning("Could not rename thread %s during reset: %s", thread.id, exc)
                except Exception as edit_err:
                    logger.warning("Could not rename thread %s during reset: %s", thread.id, edit_err)
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
    @app_commands.command(name="clear-folder-tickets", description="Reset import cache for a folder so tickets can be reloaded (PM only)")
    @app_commands.describe(
        folder="Folder inside tickets/ to clear",
        channel="Optional channel to scope ticket reset",
    )
    async def clear_folder(
        self,
        interaction: discord.Interaction,
        folder: str,
        channel: Optional[discord.TextChannel] = None,
    ):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles['is_pm']:
                await interaction.followup.send("❌ Only Project Managers can clear folder import caches.", ephemeral=True)
                return

            channel_id = channel.id if channel else None
            count = await asyncio.to_thread(clear_loaded_tickets, folder, channel_id)
            scope_desc = f" for channel {channel.mention}" if channel else ""
            embed = discord.Embed(
                title="🗑️ Folder Import Cache Cleared",
                description=f"Cleared **{count}** ticket import markers for folder `{folder}`{scope_desc}.\nYou can now run `/load-tickets {folder}` to re-import.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /clear-folder-tickets: {e}")
            await interaction.followup.send(f"❌ Error clearing folder: {e}", ephemeral=True)

    # 4b. /reset-loaded (Alias for /clear-folder-tickets)
    @app_commands.command(name="reset-loaded", description="Reset import cache for a folder so tickets can be reloaded (PM only)")
    @app_commands.describe(
        folder="Folder inside tickets/ to clear",
        channel="Optional channel to scope ticket reset",
    )
    async def reset_loaded(
        self,
        interaction: discord.Interaction,
        folder: str,
        channel: Optional[discord.TextChannel] = None,
    ):
        await self.clear_folder.callback(self, interaction, folder, channel)

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
    @app_commands.command(name="setreminderschannel", description="Set channel for daily 8:00 AM PHT ticket summaries (PM only)")
    async def set_reminders_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await safe_defer(interaction)
        user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
        if not user_roles["is_pm"]:
            await interaction.followup.send(
                "❌ Only Project Managers can change the reminders channel.",
                ephemeral=True,
            )
            return
        await asyncio.to_thread(set_setting, "reminders_channel_id", str(channel.id))
        await interaction.followup.send(f"✅ Daily sprint reminders channel set to {channel.mention}.")

    # Helper: Apply role synchronization
    async def _apply_user_role(
        self,
        interaction: discord.Interaction,
        target_member: discord.Member,
        role: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.followup.send(
                "❌ This command can only be used inside the Discord server.",
                ephemeral=True,
            )
            return

        is_dev = role == "dev"
        is_qa = role == "qa"
        is_pm = role == "pm"

        # Check permissions for PM role: allow administrator, manage_guild, or manage_channels
        has_pm_permission = (
            interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_guild
            or interaction.user.guild_permissions.manage_channels
        )
        if is_pm and not has_pm_permission:
            await interaction.followup.send(
                "❌ Setting the Project Manager role requires Administrator, Manage Server, or Manage Channels permissions.",
                ephemeral=True,
            )
            return

        # If assigning for another user, require PM or manage_roles/administrator
        if target_member.id != interaction.user.id:
            caller_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            caller_has_perm = (
                caller_roles.get("is_pm")
                or interaction.user.guild_permissions.administrator
                or interaction.user.guild_permissions.manage_roles
                or interaction.user.guild_permissions.manage_guild
            )
            if not caller_has_perm:
                await interaction.followup.send(
                    "❌ You must be a Project Manager or Server Admin to change roles for other team members.",
                    ephemeral=True,
                )
                return

        bot_member = interaction.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            await interaction.followup.send(
                "❌ I need the **Manage Roles** permission to synchronize Discord roles.",
                ephemeral=True,
            )
            return

        role_label = "Developer" if is_dev else ("QA Reviewer" if is_qa else "Project Manager")
        discord_role_name = "Developer" if is_dev else ("QA" if is_qa else "Project Manager")
        discord_role = discord.utils.get(interaction.guild.roles, name=discord_role_name)
        if discord_role is None:
            discord_role = await interaction.guild.create_role(
                name=discord_role_name,
                color=(
                    discord.Color.blurple()
                    if is_dev
                    else (discord.Color.gold() if is_qa else discord.Color.purple())
                ),
                reason="CapStoneFlow role synchronization",
            )

        is_above = False
        if hasattr(discord_role, "position") and hasattr(bot_member.top_role, "position"):
            try:
                is_above = discord_role.position >= bot_member.top_role.position
            except (TypeError, AttributeError):
                is_above = False
        else:
            try:
                is_above = discord_role >= bot_member.top_role
            except TypeError:
                is_above = False

        if is_above:
            await interaction.followup.send(
                f"❌ I cannot manage the **{discord_role_name}** role because it is above my highest role.",
                ephemeral=True,
            )
            return

        managed_names = {"Developer", "QA", "Project Manager"}
        old_roles = [
            existing
            for existing in target_member.roles
            if existing.name in managed_names and existing != discord_role
        ]
        if old_roles:
            await target_member.remove_roles(
                *old_roles,
                reason="CapStoneFlow role synchronization",
            )
        if discord_role not in target_member.roles:
            await target_member.add_roles(
                discord_role,
                reason="CapStoneFlow role synchronization",
            )

        try:
            await asyncio.to_thread(
                set_user_role,
                target_member.id,
                target_member.name,
                is_developer=is_dev,
                is_qa=is_qa,
                is_pm=is_pm,
            )
        except Exception as exc:
            logger.exception("Discord role changed but database role sync failed: %s", exc)
            await interaction.followup.send(
                f"⚠️ Discord role **{role_label}** was assigned to {target_member.mention}, but the database could not be updated. Please retry after the database is available.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"🎉 **{target_member.display_name}** has been assigned the **{role_label}** role in Discord and CapStoneFlow.",
        )

    # 7. /assign-role
    @app_commands.command(name="assign-role", description="Set your active workspace role (Developer, QA, or PM)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Developer (Claim & Resolve)", value="dev"),
        app_commands.Choice(name="QA Reviewer (Verify & Review)", value="qa"),
        app_commands.Choice(name="Project Manager (Lead & Manage)", value="pm"),
    ])
    async def assign_role(self, interaction: discord.Interaction, role: str):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.user, discord.Member):
                await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
                return
            await self._apply_user_role(interaction, interaction.user, role)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Discord denied the role change. Check the bot's **Manage Roles** permission and role hierarchy.",
                ephemeral=True,
            )
        except Exception as e:
            logger.exception("Error in /assign-role: %s", e)
            await interaction.followup.send(
                "❌ Could not synchronize your role. Please try again.",
                ephemeral=True,
            )

    # 7b. /set-role
    @app_commands.command(name="set-role", description="Assign a workspace role to yourself or a team member")
    @app_commands.describe(
        role="Workspace role to assign",
        member="Team member to assign the role to (defaults to yourself)",
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="Developer (Claim & Resolve)", value="dev"),
        app_commands.Choice(name="QA Reviewer (Verify & Review)", value="qa"),
        app_commands.Choice(name="Project Manager (Lead & Manage)", value="pm"),
    ])
    async def set_role(
        self,
        interaction: discord.Interaction,
        role: str,
        member: Optional[discord.Member] = None,
    ):
        await safe_defer(interaction)
        try:
            target = member or interaction.user
            if not isinstance(target, discord.Member):
                await interaction.followup.send("❌ This command must be used in a server.", ephemeral=True)
                return
            await self._apply_user_role(interaction, target, role)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Discord denied the role change. Check the bot's **Manage Roles** permission and role hierarchy.",
                ephemeral=True,
            )
        except Exception as e:
            logger.exception("Error in /set-role: %s", e)
            await interaction.followup.send(
                "❌ Could not synchronize role. Please try again.",
                ephemeral=True,
            )

    # 8. /help (Alias for /commands)
    @app_commands.command(name="help", description="Show the CapStoneFlow command guide and workflows")
    async def show_help(self, interaction: discord.Interaction):
        await self.show_commands.callback(self, interaction)

    # 9. /set-commit-channel
    @app_commands.command(name="set-commit-channel", description="Set default channel for formal commit and merge bulletins (PM only)")
    @app_commands.describe(channel="Channel to receive commit and merged PR bulletins")
    async def set_commit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await safe_defer(interaction)
        user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
        if not user_roles["is_pm"]:
            await interaction.followup.send(
                "❌ Only Project Managers can set the commit bulletin channel.",
                ephemeral=True,
            )
            return
        await asyncio.to_thread(set_setting, "commit_channel_id", str(channel.id))
        await interaction.followup.send(f"✅ Repository commit and merge bulletins channel set to {channel.mention}.")

    # 10. /update-project
    @app_commands.command(name="update-project", description="Post formal repository updates (commits/PRs) with GitHub links (PM only)")
    @app_commands.describe(
        repo_url="GitHub repository URL or owner/repo shorthand",
        branch="Git branch to check (default: main)",
        limit="Maximum initial items to post (default: 5)",
        feed_type="Scope of updates (both, commits, merged)",
        channel="Target channel (defaults to commit channel or current channel)",
    )
    @app_commands.choices(feed_type=[
        app_commands.Choice(name="Commits and Merged PRs", value="both"),
        app_commands.Choice(name="Commits Only", value="commits"),
        app_commands.Choice(name="Merged Pull Requests Only", value="merged"),
    ])
    async def update_project(
        self,
        interaction: discord.Interaction,
        repo_url: str,
        branch: str = "main",
        limit: app_commands.Range[int, 1, 30] = 5,
        feed_type: str = "both",
        channel: Optional[discord.TextChannel] = None,
    ):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles["is_pm"]:
                await interaction.followup.send("❌ Only Project Managers can run /update-project.", ephemeral=True)
                return

            target_channel = channel
            if not target_channel:
                stored_ch_id = await asyncio.to_thread(get_setting, "commit_channel_id")
                if stored_ch_id and stored_ch_id.isdigit():
                    target_channel = self.bot.get_channel(int(stored_ch_id))
            if not target_channel:
                target_channel = interaction.channel

            if not isinstance(target_channel, discord.TextChannel):
                await interaction.followup.send("❌ Target channel must be a text channel.", ephemeral=True)
                return

            await asyncio.to_thread(set_setting, "commit_channel_id", str(target_channel.id))
            await asyncio.to_thread(set_setting, "auto_updates_repo", repo_url)
            await asyncio.to_thread(set_setting, "auto_updates_branch", branch)
            await asyncio.to_thread(set_setting, "auto_updates_feed_type", feed_type)

            github_token = os.getenv("GITHUB_TOKEN")

            async def _mark_event(key: str, ch_id: int) -> bool:
                s_key = f"event_posted:{ch_id}:{key}"
                existing = await asyncio.to_thread(get_setting, s_key)
                if existing:
                    return False
                await asyncio.to_thread(set_setting, s_key, "1")
                return True

            from repo_updates import post_project_updates
            ok, msg, commits_count, prs_count = await post_project_updates(
                target_channel=target_channel,
                repo_url=repo_url,
                branch=branch,
                limit=limit,
                feed_type=feed_type,
                reported_by=interaction.user.name,
                github_token=github_token,
                get_setting=lambda k: asyncio.to_thread(get_setting, k),
                set_setting=lambda k, v: asyncio.to_thread(set_setting, k, v),
                mark_event_posted=_mark_event,
            )

            if not ok:
                await interaction.followup.send(f"⚠️ {msg}")
                return

            summary = discord.Embed(
                title="📢 Repository Updates Broadcast",
                description=(
                    f"**Status:** {msg}\n"
                    f"**Commits Posted:** `{commits_count}`\n"
                    f"**PRs Posted:** `{prs_count}`\n"
                    f"**Destination:** {target_channel.mention}\n"
                    f"**Auto-updates:** Channel persisted for incoming webhooks."
                ),
                color=0x10b981 if (commits_count > 0 or prs_count > 0) else 0x38bdf8,
            )
            await interaction.followup.send(embed=summary)
        except Exception as e:
            logger.exception("Error in /update-project: %s", e)
            await interaction.followup.send(f"❌ Error updating project: {e}")

    # 11. /auto-updates
    @app_commands.command(name="auto-updates", description="Control automatic repository notifications (PM only)")
    @app_commands.describe(
        action="Action to perform",
        repo_url="Optional GitHub repo URL to monitor",
        branch="Optional branch (default: main)",
        feed_type="Optional feed type (both, commits, merged)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Status & Inspection", value="status"),
        app_commands.Choice(name="Enable Automatic Notifications", value="enable"),
        app_commands.Choice(name="Disable Automatic Notifications", value="disable"),
    ])
    async def auto_updates(
        self,
        interaction: discord.Interaction,
        action: str,
        repo_url: Optional[str] = None,
        branch: Optional[str] = "main",
        feed_type: Optional[str] = "both",
    ):
        await safe_defer(interaction)
        user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
        if not user_roles["is_pm"]:
            await interaction.followup.send("❌ Only Project Managers can configure automatic updates.", ephemeral=True)
            return

        if action == "enable":
            await asyncio.to_thread(set_setting, "auto_updates_enabled", "true")
            if repo_url:
                await asyncio.to_thread(set_setting, "auto_updates_repo", repo_url)
            if branch:
                await asyncio.to_thread(set_setting, "auto_updates_branch", branch)
            if feed_type:
                await asyncio.to_thread(set_setting, "auto_updates_feed_type", feed_type)
            await interaction.followup.send("✅ Automatic repository updates enabled.")
        elif action == "disable":
            await asyncio.to_thread(set_setting, "auto_updates_enabled", "false")
            await interaction.followup.send("⏸️ Automatic repository updates paused.")
        else:
            enabled = (await asyncio.to_thread(get_setting, "auto_updates_enabled")) or "true"
            curr_repo = (await asyncio.to_thread(get_setting, "auto_updates_repo")) or "Not configured"
            curr_branch = (await asyncio.to_thread(get_setting, "auto_updates_branch")) or "main"
            curr_feed = (await asyncio.to_thread(get_setting, "auto_updates_feed_type")) or "both"
            commit_ch_id = await asyncio.to_thread(get_setting, "commit_channel_id")
            ch_mention = f"<#{commit_ch_id}>" if commit_ch_id else "None (will use notifications/system channel)"
            webhook_sec = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
            embed = discord.Embed(
                title="⚙️ Auto-Updates Configuration",
                color=0x6366f1,
            )
            embed.add_field(name="Status", value="🟢 Enabled" if enabled == "true" else "🔴 Disabled", inline=True)
            embed.add_field(name="Target Channel", value=ch_mention, inline=True)
            embed.add_field(name="Repository", value=f"`{curr_repo}`", inline=False)
            embed.add_field(name="Branch", value=f"`{curr_branch}`", inline=True)
            embed.add_field(name="Feed Scope", value=f"`{curr_feed}`", inline=True)
            embed.add_field(name="Webhook Secret Configured", value="✅ Yes" if webhook_sec else "⚠️ No", inline=True)
            embed.set_footer(text="Endpoint: POST /webhook/github")
            await interaction.followup.send(embed=embed)

    # 12. /health-details
    @app_commands.command(name="health-details", description="Show database latency, auto-update/webhook status, and diagnostics")
    async def health_details(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        import time
        from database import get_db

        db_ok = False
        db_latency_ms = None
        try:
            t0 = time.perf_counter()
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
            t1 = time.perf_counter()
            db_ok = True
            db_latency_ms = round((t1 - t0) * 1000, 2)
        except Exception:
            db_latency_ms = None

        ws_latency_ms = round(self.bot.latency * 1000, 2) if self.bot.latency else 0.0
        webhook_secret_set = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
        auto_enabled = (await asyncio.to_thread(get_setting, "auto_updates_enabled")) or "true"
        commit_ch = await asyncio.to_thread(get_setting, "commit_channel_id")
        remind_ch = await asyncio.to_thread(get_setting, "reminders_channel_id")

        embed = discord.Embed(
            title="🩺 CapStoneFlow System Health & Diagnostics",
            description="Live operational telemetry and connection status.",
            color=0x10b981 if db_ok else 0xef4444,
        )
        embed.add_field(
            name="🗄️ Database (PostgreSQL)",
            value=f"{'🟢 Connected' if db_ok else '🔴 Offline'}\n`Latency: {db_latency_ms} ms`" if db_ok else "🔴 Unavailable",
            inline=True,
        )
        embed.add_field(
            name="⚡ Discord Gateway",
            value=f"🟢 Connected\n`Latency: {ws_latency_ms} ms`",
            inline=True,
        )
        embed.add_field(
            name="🔗 GitHub Webhook",
            value=f"{'✅ Secret Configured' if webhook_secret_set else '⚠️ Secret Missing'}\n`/webhook/github`",
            inline=True,
        )
        embed.add_field(
            name="📢 Bulletin Channel",
            value=f"<#{commit_ch}>" if commit_ch else "`Not configured`",
            inline=True,
        )
        embed.add_field(
            name="🌅 Reminders Channel",
            value=f"<#{remind_ch}>" if remind_ch else "`Not configured`",
            inline=True,
        )
        embed.add_field(
            name="🔄 Auto-Updates",
            value="🟢 Active" if auto_enabled == "true" else "⏸️ Paused",
            inline=True,
        )
        embed.set_footer(text=f"CapStoneFlow v1.0 • Guilds: {len(self.bot.guilds)}")
        await interaction.followup.send(embed=embed)

    # 13. /ai-status
    @app_commands.command(name="ai-status", description="Show current AI provider, model, and reasoning engine status (PM only)")
    async def ai_status(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
        if not user_roles["is_pm"]:
            await interaction.followup.send("❌ Only Project Managers can view AI status.", ephemeral=True)
            return

        local_url = os.getenv("LOCAL_LLM_URL") or os.getenv("AI_BASE_URL") or os.getenv("AI_INVOKE_URL")
        is_local = bool(local_url and any(loc in local_url for loc in ["localhost", "127.0.0.1", "192.168", "10.", "http"]))
        nvidia_key = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("AI_ANSWER_API_KEY"))
        gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        latex_enabled = has_latex()

        if is_local:
            provider_label = "Local Model (Gemma 4 / On-Prem Hardware)"
            model_name = os.getenv("LOCAL_LLM_MODEL") or os.getenv("AI_MODEL") or "gemma-4"
        elif nvidia_key:
            provider_label = "Nvidia Cloud API"
            model_name = os.getenv("NVIDIA_MODEL") or os.getenv("AI_ANSWER_MODEL") or "meta/llama-3.1-70b-instruct"
        elif gemini_key:
            provider_label = "Google Gemini"
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        else:
            provider_label = "Offline Heuristic Fallback"
            model_name = "Built-in 3-Ticket Engine"

        embed = discord.Embed(
            title="🤖 CapStoneFlow AI Engine Status",
            description="Real-time status of AI planning, chat reasoning, and local model orchestration.",
            color=0x10B981 if is_local else (0x8b5cf6 if (nvidia_key or gemini_key) else 0xf59e0b),
        )
        embed.add_field(name="Active Provider", value=f"`{provider_label}`", inline=True)
        embed.add_field(name="Selected Model", value=f"`{model_name}`", inline=True)
        if is_local:
            embed.add_field(name="Local/On-Prem Endpoint", value=f"`{local_url}`", inline=True)
        embed.add_field(name="📐 Math Renderer (LaTeX)", value="✅ Available" if latex_enabled else "⚠️ Fallback", inline=True)
        embed.add_field(name="Nvidia API Key", value="✅ Configured" if nvidia_key else "❌ Not required (Local)" if is_local else "❌ Missing", inline=True)
        embed.add_field(name="Gemini API Key", value="✅ Configured" if gemini_key else "❌ Not required (Local)" if is_local else "❌ Missing", inline=True)
        embed.add_field(name="Cloud Cost / Bill", value="`$0.00 (Zero Cloud Bill)`" if (is_local or gemini_key) else "`Commercial Tier`", inline=True)
        embed.add_field(name="Offline Resilience", value="✅ Active & Ready", inline=True)
        embed.set_footer(text="Future Forge Ready • Powers /plan-mvp, /ask-ai, and AI-Chat threads")
        await interaction.followup.send(embed=embed)

    # 8. /sync-commands
    @app_commands.command(name="sync-commands", description="Manually synchronize slash commands with Discord (PM only)")
    async def sync_commands_command(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not user_roles["is_pm"]:
                await interaction.followup.send("❌ Only Project Managers can sync commands.", ephemeral=True)
                return

            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="⚡ Slash Commands Synchronized",
                description=f"Successfully synchronized **{len(synced)}** application slash commands globally.",
                color=0x10b981
            )
            await interaction.followup.send(embed=embed)
        except discord.HTTPException as e:
            if e.status == 429:
                await interaction.followup.send("⚠️ Discord is currently rate-limiting command syncs (429). Please wait 15 minutes before retrying.", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Failed to sync commands: {e}", ephemeral=True)
        except Exception as e:
            logger.exception("Error in /sync-commands: %s", e)
            await interaction.followup.send(f"❌ Error syncing commands: {e}", ephemeral=True)

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
