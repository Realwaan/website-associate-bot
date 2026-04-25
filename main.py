"""Discord Bot for managing support tickets."""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import os
import re
import tempfile
import subprocess
import asyncio
from urllib.parse import urlparse
from datetime import datetime, time, timezone, timedelta
from config import DISCORD_TOKEN, TICKETS_DIR, SCAN_IGNORE_DIRS, SCAN_FILE_EXTENSIONS, SCAN_LARGE_FILE_THRESHOLD
from database import (
    init_db, verify_database_connection, add_thread, get_thread, update_thread_status,
    increment_developer_resolved, increment_qa_reviewed, 
    decrement_developer_resolved, decrement_qa_reviewed,
    get_leaderboard_dev, get_leaderboard_qa,
    set_user_role, get_user_roles, has_role,
    is_ticket_loaded, mark_ticket_loaded, get_loaded_tickets, remove_thread_record,
    set_setting, get_setting, get_threads_by_status, get_stale_threads
)
from ticket_loader import load_tickets_from_folder, get_available_folders
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from scan_project import scan_and_generate_with_summary
from roadmap_builder import build_project_roadmap
from ai_client import NvidiaAIClient, AIClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
# Privileged intents (require toggle in Discord Developer Portal):
# - message_content: Not needed since the bot uses slash commands only.
# - members: Only needed for /rebuild-db role syncing.
# If you enable "SERVER MEMBERS INTENT" and "MESSAGE CONTENT INTENT"
# in the Developer Portal, you can set these to True.
intents.message_content = False
intents.members = False

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
ai_client = NvidiaAIClient()


async def clear_global_app_commands() -> int:
    """Remove all globally registered slash commands for this application."""
    app_id = bot.application_id
    if app_id is None:
        app_info = await bot.application_info()
        app_id = app_info.id

    # Empty bulk upsert deletes existing global app commands.
    await bot.http.bulk_upsert_global_commands(app_id, [])
    return app_id


async def safe_defer(interaction: discord.Interaction, ephemeral: bool = False):
    """Defer interaction safely and ignore already-acknowledged race conditions."""
    if interaction.response.is_done():
        return
    try:
        await interaction.response.defer(ephemeral=ephemeral)
    except discord.HTTPException as e:
        # 40060: already acknowledged, 10062: interaction expired/unknown.
        if getattr(e, "code", None) not in (40060, 10062):
            raise


def normalize_ticket_name(name: str) -> str:
    """Normalize a ticket name for matching to filenames."""
    cleaned = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def build_branch_name(ticket_name: str) -> str:
    """Build a git-safe branch name from a ticket title."""
    base = re.sub(r"[^a-z0-9\s-]", "", ticket_name.lower())
    base = re.sub(r"[\s_]+", "-", base).strip("-")
    base = re.sub(r"-+", "-", base)

    if not base:
        base = "ticket-work"

    # Keep branch names short and readable for git tooling.
    return f"issue/{base[:60].rstrip('-')}"


def parse_thread_name(thread_name: str) -> tuple[str | None, str | None]:
    """Parse a thread name into status and ticket display name."""
    patterns = [
        ("OPEN", r"^\[OPEN\]\s*(.+)$"),
        ("CLAIMED", r"^\[CLAIMED\]\[.+?\](.+)$"),
        ("PENDING-REVIEW", r"^\[Pending-Review\]\[.+?\](.+)$"),
        ("REVIEWED", r"^\[Reviewed\]\[.+?\](.+)$"),
        ("CLOSED", r"^\[CLOSED\]\[.+?\](.+)$"),
    ]

    for status, pattern in patterns:
        match = re.match(pattern, thread_name)
        if match:
            return status, match.group(1).strip()

    return None, None


@bot.event
async def on_ready():
    """When the bot is ready, sync commands and initialize database."""
    logger.info(f"Logged in as {bot.user}")
    try:
        # Strict guild-only strategy:
        # 1) Clear all global commands to avoid duplicate listings.
        # 2) Sync all commands to each guild for immediate propagation.
        app_id = await clear_global_app_commands()
        logger.info(f"Cleared all global app commands for application {app_id}")

        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            bot.tree.copy_global_to(guild=guild)
            guild_synced = await bot.tree.sync(guild=guild)
            logger.info(f"Guild-only sync complete: {guild.name} -> {len(guild_synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start scheduled task
    if not scheduled_ticket_summary.is_running():
        scheduled_ticket_summary.start()
        logger.info("Scheduled ticket summary task started")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Ensure users always receive a response when a slash command fails unexpectedly."""
    logger.exception("Unhandled app command error: %s", error)

    # Interaction is already expired; attempting to reply will fail again.
    if isinstance(error, app_commands.CommandInvokeError):
        original = getattr(error, "original", None)
        if isinstance(original, discord.HTTPException) and getattr(original, "code", None) == 10062:
            return

    message = "❌ Something went wrong while processing this command. Please try again."
    try:
        try:
            await interaction.followup.send(message, ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        logger.exception("Failed to send app command error response")


@bot.tree.command(
    name="sync-commands",
    description="Force sync slash commands to this server (admins only)"
)
async def sync_commands(interaction: discord.Interaction):
    """Force a guild-only slash command sync for the current server."""
    await safe_defer(interaction, ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Only administrators can force sync commands.", ephemeral=True)
        return

    try:
        app_id = await clear_global_app_commands()

        # Rebuild current guild command set from the code-defined global set.
        bot.tree.clear_commands(guild=interaction.guild)
        bot.tree.copy_global_to(guild=interaction.guild)
        guild_synced = await bot.tree.sync(guild=interaction.guild)

        global_commands = await bot.tree.fetch_commands()
        guild_commands = await bot.tree.fetch_commands(guild=interaction.guild)
        global_names = sorted({cmd.name for cmd in global_commands})
        guild_names = sorted({cmd.name for cmd in guild_commands})
        overlap = sorted(set(global_names).intersection(set(guild_names)))

        await interaction.followup.send(
            f"✅ Guild-only sync complete with {len(guild_synced)} command(s)."
            f"\nCleared global commands for app: {app_id}"
            f"\nGlobal visible: {len(global_commands)} | Guild visible: {len(guild_commands)}"
            f"\nOverlap: {len(overlap)}"
            "\nIf duplicates still appear, reopen Discord and run /debug-commands.",
            ephemeral=True,
        )
        logger.info(
            "Forced guild-only sync of %s commands in guild %s by %s (global cleared for app %s)",
            len(guild_synced),
            interaction.guild.id,
            interaction.user,
            app_id,
        )
    except Exception as e:
        logger.error(f"Failed to force sync commands: {e}")
        await interaction.followup.send(f"❌ Failed to sync commands: {e}", ephemeral=True)


@bot.tree.command(
    name="debug-commands",
    description="Show global/guild command counts and overlaps (admins only)"
)
async def debug_commands(interaction: discord.Interaction):
    """Debug slash command registration to diagnose duplicate entries."""
    await safe_defer(interaction, ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Only administrators can use this command.", ephemeral=True)
        return

    try:
        global_commands = await bot.tree.fetch_commands()
        guild_commands = await bot.tree.fetch_commands(guild=interaction.guild)

        global_names = sorted(cmd.name for cmd in global_commands)
        guild_names = sorted(cmd.name for cmd in guild_commands)
        overlap = sorted(set(global_names).intersection(set(guild_names)))

        embed = discord.Embed(
            title="🧪 Command Registration Debug",
            color=discord.Color.orange(),
            description="Shows command registration sources that can cause duplicate entries.",
        )
        embed.add_field(name="Global Commands", value=str(len(global_names)), inline=True)
        embed.add_field(name="Guild Commands", value=str(len(guild_names)), inline=True)
        embed.add_field(name="Overlapping Names", value=str(len(overlap)), inline=True)

        if overlap:
            text = "\n".join([f"• {name}" for name in overlap[:20]])
            if len(overlap) > 20:
                text += f"\n• ... and {len(overlap) - 20} more"
            embed.add_field(name="Overlap List", value=text, inline=False)
        else:
            embed.add_field(name="Overlap List", value="None detected", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to debug command registration: {e}")
        await interaction.followup.send(f"❌ Failed to debug command registration: {e}", ephemeral=True)


@bot.tree.command(
    name="set-role",
    description="Assign yourself a role (Developer, QA, or PM)"
)
@app_commands.describe(
    role="The role to assign: 'developer', 'qa', or 'pm'"
)
@app_commands.choices(role=[
    app_commands.Choice(name="Developer", value="developer"),
    app_commands.Choice(name="QA", value="qa"),
    app_commands.Choice(name="Project Manager", value="pm")
])
async def set_role(interaction: discord.Interaction, role: str):
    """Assign yourself a Developer, QA, or PM role."""
    await safe_defer(interaction)
    
    try:
        role_lower = role.lower()
        
        # Check if user is trying to set PM role
        if role_lower == "pm":
            # Only admins can assign PM role
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ Only server admins can set the Project Manager role.")
                return
        
        # Determine role parameters
        if role_lower == "developer":
            is_developer = True
            is_qa = False
            is_pm = False
            discord_role_name = "Developer"
            emoji = "👨‍💻"
        elif role_lower == "qa":
            is_developer = False
            is_qa = True
            is_pm = False
            discord_role_name = "QA"
            emoji = "🔍"
        elif role_lower == "pm":
            is_developer = True
            is_qa = True
            is_pm = True
            discord_role_name = "Project Manager"
            emoji = "📋"
        else:
            await interaction.followup.send("❌ Invalid role. Choose 'developer', 'qa', or 'pm'.")
            return
        
        # Get or create Discord role
        guild = interaction.guild
        discord_role = discord.utils.get(guild.roles, name=discord_role_name)
        
        if not discord_role:
            # Create the role if it doesn't exist
            color = discord.Color.blurple() if role_lower == "developer" else (discord.Color.gold() if role_lower == "qa" else discord.Color.purple())
            discord_role = await guild.create_role(
                name=discord_role_name,
                color=color,
                reason="Ticket bot role assignment"
            )
            logger.info(f"Created Discord role: {discord_role_name}")
        
        # Remove all bot-managed roles from user first
        bot_role_names = ["Developer", "QA", "Project Manager"]
        for role_name in bot_role_names:
            old_role = discord.utils.get(guild.roles, name=role_name)
            if old_role and old_role in interaction.user.roles:
                await interaction.user.remove_roles(old_role)
                logger.info(f"Removed {role_name} role from {interaction.user}")
        
        # Assign the new Discord role to user
        await interaction.user.add_roles(discord_role)
        logger.info(f"Assigned {discord_role_name} role to {interaction.user}")
        
        # Set user role in database
        set_user_role(interaction.user.id, str(interaction.user), is_developer=is_developer, is_qa=is_qa, is_pm=is_pm)
        
        embed = discord.Embed(
            title="Role Assigned",
            description=f"{emoji} You have been assigned the **{discord_role_name}** role",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Discord Role", value=f"<@&{discord_role.id}>", inline=False)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Role '{role_lower}' set for {interaction.user}: {interaction.user.id}")
        
    except Exception as e:
        logger.error(f"Error setting role: {e}")
        await interaction.followup.send(f"❌ Error setting role: {e}")




@bot.tree.command(
    name="setreminderschannel",
    description="Set the channel for daily ticket summaries (PM only)"
)
@app_commands.describe(
    channel="The channel where daily summaries should be sent"
)
async def set_reminders_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel for daily ticket summaries. Only PMs can use this."""
    await safe_defer(interaction)
    
    try:
        # Check if user is a PM
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can set the reminders channel.")
            return
        
        # Save to database
        set_setting("reminders_channel_id", str(channel.id))
        
        embed = discord.Embed(
            title="Reminders Channel Set",
            description=f"Daily ticket summaries will be sent to {channel.mention} every 8:00 AM PH Time.",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Reminders channel set to {channel.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error setting reminders channel: {e}")
        await interaction.followup.send(f"❌ Error setting reminders channel: {e}")


# ===== Scheduled Task =====

def format_ticket_list(tickets: list) -> str:
    """Format a list of tickets for the summary message."""
    if not tickets:
        return "None"
    
    lines = []
    for t in tickets:
        lines.append(f"• {t['ticket_name']} (ID: {t['thread_id']})")
    
    return "\n".join(lines)


def format_stale_ticket_list(tickets: list) -> str:
    """Format stale tickets with status and age for summary messages."""
    if not tickets:
        return "None"

    lines = []
    for t in tickets:
        age_hours = int(t.get('age_hours') or 0)
        if age_hours >= 24:
            age_text = f"{age_hours // 24}d {age_hours % 24}h"
        else:
            age_text = f"{age_hours}h"

        lines.append(
            f"• {t['ticket_name']} [{t['status']}] (age: {age_text}) - <#{t['thread_id']}>"
        )

    return "\n".join(lines)


@bot.tree.command(
    name="setstalethreshold",
    description="Set stale ticket threshold (hours) for daily summaries (PM only)"
)
@app_commands.describe(
    hours="Mark tickets as stale after this many hours (min: 1, max: 336)"
)
async def set_stale_threshold(interaction: discord.Interaction, hours: int):
    """Set stale ticket threshold used by daily summary digest."""
    await safe_defer(interaction)

    try:
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can set stale threshold.")
            return

        hours = max(1, min(hours, 336))
        set_setting("stale_threshold_hours", str(hours))

        embed = discord.Embed(
            title="Stale Threshold Updated",
            description=f"Tickets older than **{hours}** hour(s) in OPEN/CLAIMED/PENDING-REVIEW will be listed as stale.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"Stale threshold set to {hours} hours by {interaction.user}")

    except Exception as e:
        logger.error(f"Error setting stale threshold: {e}")
        await interaction.followup.send(f"❌ Error setting stale threshold: {e}")


@tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))  # 8 AM PH Time
async def scheduled_ticket_summary():
    """Daily task to send ticket summary."""
    try:
        channel_id_str = get_setting("reminders_channel_id")
        if not channel_id_str:
            logger.warning("Scheduled task: No reminders channel set.")
            return
        
        channel_id = int(channel_id_str)
        channel = bot.get_channel(channel_id)
        if not channel:
            # Try fetching if not in cache
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception:
                logger.error(f"Scheduled task: Could not find channel {channel_id}")
                return
        
        # Get status groups
        status_groups = get_threads_by_status()

        stale_threshold_str = get_setting("stale_threshold_hours")
        stale_threshold_hours = 48
        if stale_threshold_str:
            try:
                stale_threshold_hours = max(1, int(stale_threshold_str))
            except ValueError:
                stale_threshold_hours = 48

        stale_tickets = get_stale_threads(stale_threshold_hours)
        
        # Format message
        message = "@everyone\n"
        message += "📅 **DAILY TICKET SUMMARY (8 AM PH TIME)**\n\n"
        
        # Open
        message += "🔵 **Open**\n"
        message += format_ticket_list(status_groups.get("OPEN")) + "\n\n"
        
        # Claimed
        message += "🟡 **Claimed**\n"
        message += format_ticket_list(status_groups.get("CLAIMED")) + "\n\n"
        
        # Pending-Review
        message += "🟠 **Pending-Review**\n"
        message += format_ticket_list(status_groups.get("PENDING-REVIEW")) + "\n\n"
        
        # Reviewed
        message += "🟢 **Reviewed**\n"
        message += format_ticket_list(status_groups.get("REVIEWED")) + "\n\n"
        
        # Closed
        message += "🔴 **Closed**\n"
        message += format_ticket_list(status_groups.get("CLOSED")) + "\n\n"

        # Stale tickets digest
        message += f"⏰ **Stale Tickets ({stale_threshold_hours}h+)**\n"
        message += format_stale_ticket_list(stale_tickets)
        
        # Send message (ensure it's not too long for one message, if it is, it will be truncated)
        if len(message) > 2000:
            message = message[:1997] + "..."
            
        await channel.send(message)
        logger.info(f"Sent scheduled summary to channel {channel_id}")
        
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")


@bot.tree.command(
    name="load-tickets",
    description="Load tickets from a folder into a Discord channel (PM only)"
)
@app_commands.describe(
    folder="The folder name within tickets/ directory (e.g., support, bugs, features)",
    channel="The Discord channel where threads should be created"
)
async def load_tickets(interaction: discord.Interaction, folder: str, channel: discord.TextChannel):
    """Load tickets from a folder and create threads in the specified channel. Only PMs can use this."""
    await safe_defer(interaction)
    
    try:
        # Check if user is a PM
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can load tickets. Use `/set-role` to get the PM role.")
            return
        
        # Load tickets from folder with parsing
        tickets = load_tickets_from_folder(folder)
        
        if not tickets:
            await interaction.followup.send(f"❌ No markdown files found in `{folder}/` folder")
            return

        ticket_entries = []
        ticket_filename_by_norm = {}
        for ticket in tickets:
            ticket_filename = ticket.get('name', '')
            display_name = ticket.get('title') or ticket.get('name', '')
            normalized_name = normalize_ticket_name(display_name)
            ticket_entries.append({
                "ticket": ticket,
                "ticket_filename": ticket_filename,
                "display_name": display_name,
                "normalized_name": normalized_name,
            })
            if normalized_name and normalized_name not in ticket_filename_by_norm:
                ticket_filename_by_norm[normalized_name] = ticket_filename

        loaded_rows = get_loaded_tickets(folder)
        loaded_by_filename = {row['ticket_filename']: row for row in loaded_rows}

        active_threads = list(channel.threads)
        archived_threads = []
        try:
            async for archived in channel.archived_threads(limit=None):
                archived_threads.append(archived)
        except Exception as e:
            logger.warning(f"Could not fetch archived threads for dedupe in channel {channel.id}: {e}")

        existing_threads_by_ticket = {}
        for existing_thread in (active_threads + archived_threads):
            _, parsed_ticket_name = parse_thread_name(existing_thread.name)
            display_ticket_name = parsed_ticket_name or re.sub(r"^\[[^\]]+\]\s*", "", existing_thread.name).strip()
            normalized_existing = normalize_ticket_name(display_ticket_name)
            if normalized_existing in ticket_filename_by_norm:
                existing_threads_by_ticket.setdefault(normalized_existing, []).append(existing_thread)

        duplicates_removed_count = 0
        duplicate_cleanup_failed_count = 0
        for normalized_name, thread_group in list(existing_threads_by_ticket.items()):
            if len(thread_group) <= 1:
                continue

            ticket_filename = ticket_filename_by_norm.get(normalized_name)
            preferred_thread_id = None
            if ticket_filename and ticket_filename in loaded_by_filename:
                preferred_thread_id = loaded_by_filename[ticket_filename].get('thread_id')

            keeper = None
            if preferred_thread_id is not None:
                keeper = next((t for t in thread_group if t.id == preferred_thread_id), None)
            if keeper is None:
                keeper = min(thread_group, key=lambda t: t.id)

            duplicates = [t for t in thread_group if t.id != keeper.id]
            for duplicate_thread in duplicates:
                try:
                    await duplicate_thread.delete(reason="Removing duplicate ticket thread")
                except Exception:
                    try:
                        await duplicate_thread.edit(archived=True, locked=True)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to remove duplicate thread {duplicate_thread.id}: {cleanup_error}")
                        duplicate_cleanup_failed_count += 1
                        continue

                remove_thread_record(duplicate_thread.id)
                duplicates_removed_count += 1

            existing_threads_by_ticket[normalized_name] = [keeper]

            if ticket_filename:
                mark_ticket_loaded(ticket_filename, folder, keeper.id, channel.id)
                loaded_by_filename[ticket_filename] = {
                    "ticket_filename": ticket_filename,
                    "thread_id": keeper.id,
                    "channel_id": channel.id,
                }
        
        # Create threads for each ticket
        created_count = 0
        failed_count = 0
        skipped_count = 0

        def build_section_messages(section_title: str, section_body: str, max_length: int = 1950) -> list[str]:
            """Split long section text into safe plain-message chunks."""
            if not section_body:
                return []

            chunks = []
            remaining = section_body.strip()
            first_chunk = True

            while remaining:
                header = f"**{section_title}**\n" if first_chunk else f"**{section_title} (cont.)**\n"
                available = max_length - len(header)

                if len(remaining) <= available:
                    chunks.append(header + remaining)
                    break

                split_at = remaining.rfind("\n", 0, available)
                if split_at <= 0:
                    split_at = available

                part = remaining[:split_at].rstrip()
                chunks.append(header + part)
                remaining = remaining[split_at:].lstrip("\n")
                first_chunk = False

            return chunks
        
        for entry in ticket_entries:
            try:
                ticket = entry['ticket']
                ticket_filename = entry['ticket_filename']
                display_name = entry['display_name']
                normalized_name = entry['normalized_name']

                # Check if this ticket has already been loaded
                existing_group = existing_threads_by_ticket.get(normalized_name, [])
                if existing_group:
                    canonical_thread = existing_group[0]
                    mark_ticket_loaded(ticket_filename, folder, canonical_thread.id, channel.id)
                    loaded_by_filename[ticket_filename] = {
                        "ticket_filename": ticket_filename,
                        "thread_id": canonical_thread.id,
                        "channel_id": channel.id,
                    }
                    logger.info(f"Ticket already exists as thread {canonical_thread.id}: {ticket_filename} (skipping)")
                    skipped_count += 1
                    continue

                if ticket_filename in loaded_by_filename or is_ticket_loaded(ticket_filename, folder):
                    logger.info(f"Ticket already loaded: {ticket_filename} (skipping)")
                    skipped_count += 1
                    continue
                
                thread_name = f"[OPEN] {display_name}"
                
                # Create thread in the specified channel
                thread = await channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread
                )
                
                # Add to database
                add_thread(
                    thread_id=thread.id,
                    ticket_name=display_name,
                    folder=folder,
                    channel_id=channel.id,
                    created_by=str(interaction.user)
                )
                
                # Mark ticket as loaded
                mark_ticket_loaded(ticket_filename, folder, thread.id, channel.id)
                loaded_by_filename[ticket_filename] = {
                    "ticket_filename": ticket_filename,
                    "thread_id": thread.id,
                    "channel_id": channel.id,
                }
                existing_threads_by_ticket[normalized_name] = [thread]
                
                # Send plain sectioned messages instead of a single embed.
                messages = []

                header_lines = [f"**{display_name}**"]
                if ticket.get('priority'):
                    header_lines.append(f"🚨 **Priority**: {ticket['priority']}")
                header_lines.append(f"📁 **Folder**: `{folder}`")
                header_lines.append("**Status**: 🔵 OPEN")
                header_lines.append(f"*Created by {interaction.user}*")
                messages.append("\n".join(header_lines))

                if ticket.get('problem'):
                    messages.extend(build_section_messages("Problem", ticket['problem']))

                if ticket.get('what_to_fix'):
                    fix_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(ticket['what_to_fix'])])
                    messages.extend(build_section_messages("What to Fix", fix_text))

                if ticket.get('acceptance_criteria'):
                    criteria_text = "\n".join([f"- {item}" for item in ticket['acceptance_criteria']])
                    messages.extend(build_section_messages("Acceptance Criteria", criteria_text))

                if ticket.get('related_files'):
                    files_text = "\n".join([f"- {file}" for file in ticket['related_files']])
                    messages.extend(build_section_messages("Related Files", files_text))

                # Fallback for roadmap-like markdown that does not use the
                # standard ticket section headers (Problem/What to Fix/Acceptance Criteria).
                if len(messages) == 1 and ticket.get('raw_content'):
                    raw_content = ticket['raw_content'].strip()
                    if raw_content:
                        # Remove the first H1 and priority marker to avoid repeating the header.
                        raw_content = re.sub(r"^#\s+.+?$", "", raw_content, count=1, flags=re.MULTILINE).strip()
                        raw_content = re.sub(r"^\*\*\[(PRIORITY|CRITICAL)\]\*\*\s*$", "", raw_content, flags=re.MULTILINE).strip()
                        if raw_content:
                            messages.extend(build_section_messages("Details", raw_content))

                for message in messages:
                    await thread.send(message)
                
                created_count += 1
                logger.info(f"Created thread: {thread_name} (ID: {thread.id})")
                
            except Exception as e:
                logger.error(f"Failed to create thread for {ticket.get('title', ticket['name'])}: {e}")
                failed_count += 1
        
        # Send summary
        summary = f"✅ Successfully created **{created_count}** thread(s)"
        if skipped_count > 0:
            summary += f"\n⏭️ **{skipped_count}** ticket(s) already loaded (skipped)"
        if failed_count > 0:
            summary += f"\n⚠️ Failed to create **{failed_count}** thread(s)"
        if duplicates_removed_count > 0:
            summary += f"\n🧹 Removed **{duplicates_removed_count}** duplicate thread(s)"
        if duplicate_cleanup_failed_count > 0:
            summary += f"\n⚠️ Could not remove **{duplicate_cleanup_failed_count}** duplicate thread(s); check bot permissions"
        
        embed = discord.Embed(
            title="Tickets Loaded",
            description=summary,
            color=discord.Color.green() if failed_count == 0 else discord.Color.orange()
        )
        embed.add_field(name="Folder", value=f"`{folder}`", inline=False)
        embed.add_field(name="Channel", value=channel.mention, inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except FileNotFoundError:
        await interaction.followup.send(
            f"❌ Folder `{folder}` not found in `{TICKETS_DIR}/` directory",
        )
    except Exception as e:
        logger.error(f"Error loading tickets: {e}")
        await interaction.followup.send(f"❌ Error loading tickets: {e}")


@bot.tree.command(
    name="rebuild-db",
    description="Rebuild database entries from existing threads in a channel (PM only)"
)
@app_commands.describe(
    folder="The folder name within tickets/ directory",
    channel="The Discord channel where threads already exist"
)
async def rebuild_db(interaction: discord.Interaction, folder: str, channel: discord.TextChannel):
    """Rebuild database from existing threads in a channel."""
    await safe_defer(interaction)

    try:
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can rebuild the database.")
            return

        folder_path = Path(TICKETS_DIR) / folder
        if not folder_path.exists() or not folder_path.is_dir():
            await interaction.followup.send(f"❌ Folder `{folder}` not found in `{TICKETS_DIR}/` directory")
            return

        init_db()

        tickets = load_tickets_from_folder(folder)
        name_to_filename = {}
        for ticket in tickets:
            display_name = ticket.get("title") or ticket["name"]
            name_to_filename[normalize_ticket_name(display_name)] = ticket["name"]

        active_threads = list(channel.threads)
        archived_threads = []
        try:
            async for thread in channel.archived_threads(limit=None):
                archived_threads.append(thread)
        except Exception as e:
            logger.warning(f"Failed to read archived threads for {channel.id}: {e}")

        threads_by_id = {t.id: t for t in (active_threads + archived_threads)}

        rebuilt_count = 0
        skipped_count = 0
        unmatched_count = 0

        for thread in threads_by_id.values():
            status, ticket_name = parse_thread_name(thread.name)
            if not status or not ticket_name:
                skipped_count += 1
                continue

            add_thread(
                thread_id=thread.id,
                ticket_name=ticket_name,
                folder=folder,
                channel_id=channel.id,
                created_by=str(interaction.user)
            )
            update_thread_status(thread.id, status)

            filename = name_to_filename.get(normalize_ticket_name(ticket_name))
            if filename:
                mark_ticket_loaded(filename, folder, thread.id, channel.id)
            else:
                unmatched_count += 1

            rebuilt_count += 1

        role_synced_count = 0
        missing_member_intent = False
        try:
            async for member in interaction.guild.fetch_members(limit=None):
                role_names = {role.name for role in member.roles}
                is_dev = "Developer" in role_names
                is_qa = "QA" in role_names
                is_pm = "Project Manager" in role_names

                # PM inherits both developer and QA permissions.
                if is_pm:
                    is_dev = True
                    is_qa = True

                if is_dev or is_qa or is_pm:
                    set_user_role(member.id, str(member), is_developer=is_dev, is_qa=is_qa, is_pm=is_pm)
                    role_synced_count += 1
        except Exception as e:
            logger.warning(f"Failed to sync member roles: {e}")
            missing_member_intent = True

        summary = (
            f"✅ Rebuilt **{rebuilt_count}** thread(s)\n"
            f"⏭️ Skipped **{skipped_count}** thread(s) without a known status prefix\n"
            f"⚠️ Unmatched **{unmatched_count}** thread(s) to ticket filenames\n"
            f"👥 Synced **{role_synced_count}** user role(s) from Discord"
        )

        if missing_member_intent:
            summary += "\n⚠️ Member role sync failed (check Members intent and bot permissions)"

        embed = discord.Embed(
            title="Database Rebuild Complete",
            description=summary,
            color=discord.Color.green() if rebuilt_count > 0 else discord.Color.orange()
        )
        embed.add_field(name="Folder", value=f"`{folder}`", inline=False)
        embed.add_field(name="Channel", value=channel.mention, inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error rebuilding database: {e}")
        await interaction.followup.send(f"❌ Error rebuilding database: {e}")


@bot.tree.command(
    name="claim",
    description="Claim a ticket (use inside a thread) - Developer only"
)
async def claim_ticket(interaction: discord.Interaction):
    """Claim a ticket and update its status to CLAIMED. Only Developers can claim. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a Developer or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_developer'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only Developers can claim tickets. Use `/set-role` to get the Developer role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'CLAIMED':
            existing_branch = build_branch_name(thread_info['ticket_name'])
            await interaction.followup.send(
                "⚠️ This ticket is already claimed\n"
                f"Suggested branch: `{existing_branch}`\n"
                f"Use: `git checkout {existing_branch}` (or create it if missing)."
            )
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[CLAIMED][{username}]{ticket_name}"
        branch_name = build_branch_name(ticket_name)
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "CLAIMED", claimed_by_id=interaction.user.id, claimed_by_username=username)
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Claimed",
            description=f"Claimed by: {interaction.user.mention}",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Old Status", value="[OPEN]", inline=True)
        embed.add_field(name="New Status", value=f"[CLAIMED][{username}]", inline=True)
        embed.add_field(name="Suggested Branch", value=f"`{branch_name}`", inline=False)
        embed.add_field(
            name="Next Step",
            value=(
                f"Run `git checkout -b {branch_name}` in your local repo, then push with "
                f"`git push -u origin {branch_name}`."
            ),
            inline=False,
        )
        embed.add_field(
            name="When Done",
            value="Use `/resolved <pr_url>` in this thread to send the ticket to QA review.",
            inline=False,
        )
        
        await interaction.followup.send(embed=embed)
        await interaction.followup.send(
            "🔧 Branch quick copy:\n"
            f"`{branch_name}`\n"
            f"`git checkout -b {branch_name}`\n"
            f"`git push -u origin {branch_name}`"
        )
        logger.info(f"Ticket claimed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error claiming ticket: {e}")
        await interaction.followup.send(f"❌ Error claiming ticket: {e}")


@bot.tree.command(
    name="branch-suggest",
    description="Print the suggested git branch name for this ticket (use inside a thread)"
)
async def branch_suggest(interaction: discord.Interaction):
    """Print the suggested branch name for the current ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
            
        ticket_name = thread_info['ticket_name']
        branch_name = build_branch_name(ticket_name)
        
        await interaction.followup.send(
            f"🌿 Suggested branch for **{ticket_name}**:\n"
            f"`{branch_name}`\n\n"
            f"**Commands:**\n"
            f"`git checkout -b {branch_name}`\n"
            f"`git push -u origin {branch_name}`"
        )
        
    except Exception as e:
        logger.error(f"Error suggesting branch: {e}")
        await interaction.followup.send(f"❌ Error suggesting branch: {e}")


@bot.tree.command(
    name="unclaim",
    description="Unclaim a ticket (use inside a thread) - Developer only"
)
async def unclaim_ticket(interaction: discord.Interaction):
    """Unclaim a ticket and reset its status back to OPEN. Only Developers can unclaim. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a Developer or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_developer'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only Developers can unclaim tickets. Use `/set-role` to get the Developer role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] != 'CLAIMED':
            await interaction.followup.send("⚠️ This ticket is not claimed. You can only unclaim CLAIMED tickets.")
            return

        # Only PMs or the current claimer can unclaim this ticket.
        # If claimed_by_id is somehow missing but status is CLAIMED, allow any developer to unclaim.
        is_pm = user_roles['is_pm']
        claimed_by_id = thread_info.get('claimed_by_id')
        if not is_pm and claimed_by_id is not None and claimed_by_id != interaction.user.id:
            claimed_by = thread_info.get('claimed_by_username') or "another developer"
            await interaction.followup.send(
                f"❌ Only the current claimer ({claimed_by}) or a PM can unclaim this ticket."
            )
            return
        
        # Update thread name - remove claim prefix
        ticket_name = thread_info['ticket_name']
        new_name = f"[OPEN] {ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(
            thread.id,
            "OPEN",
            claimed_by_id=None,
            claimed_by_username=None,
            resolved_by_id=None,
            resolved_by_username=None,
            reviewed_by_id=None,
            reviewed_by_username=None,
            pr_url=None,
        )
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Unclaimed",
            description=f"Unclaimed by: {interaction.user.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Old Status", value="[CLAIMED]", inline=True)
        embed.add_field(name="New Status", value="[OPEN]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket unclaimed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error unclaiming ticket: {e}")
        await interaction.followup.send(f"❌ Error unclaiming ticket: {e}")


@bot.tree.command(
    name="resolved",
    description="Mark a ticket as PENDING-REVIEW with PR link (use inside a thread) - Developer only"
)
@app_commands.describe(
    pr_url="Link to your PR/pull request (required)"
)
async def resolve_ticket(interaction: discord.Interaction, pr_url: str):
    """Mark a ticket as pending review with PR URL. Only Developers can mark as resolved. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a Developer or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_developer'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only Developers can mark tickets as pending review. Use `/set-role` to get the Developer role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'PENDING-REVIEW':
            await interaction.followup.send("⚠️ This ticket is already pending review")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[Pending-Review][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "PENDING-REVIEW", resolved_by_id=interaction.user.id, resolved_by_username=username, pr_url=pr_url)
        
        # Update developer leaderboard
        increment_developer_resolved(interaction.user.id, str(interaction.user))
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Pending Review",
            description=f"Marked by: {interaction.user.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Old Status", value=thread_info['status'], inline=True)
        embed.add_field(name="New Status", value=f"[Pending-Review][{username}]", inline=True)
        embed.add_field(name="PR Link", value=pr_url, inline=False)
        embed.add_field(name="Next Step", value="Waiting for QA review. Use `/reviewed` to approve.", inline=False)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket marked pending review: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error marking ticket as pending review: {e}")
        await interaction.followup.send(f"❌ Error marking ticket as pending review: {e}")


@bot.tree.command(
    name="unresolve",
    description="Revert a PENDING-REVIEW ticket back to CLAIMED (use inside a thread) - Developer only"
)
async def unresolve_ticket(interaction: discord.Interaction):
    """Revert a ticket from PENDING-REVIEW to CLAIMED. Only Developers can unresolve. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a Developer or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_developer'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only Developers can unresolve tickets. Use `/set-role` to get the Developer role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] != 'PENDING-REVIEW':
            await interaction.followup.send("⚠️ This ticket is not pending review. Only PENDING-REVIEW tickets can be unresolved.")
            return
        
        # Update thread name back to CLAIMED
        ticket_name = thread_info['ticket_name']
        username = thread_info['claimed_by_username'] or thread_info['resolved_by_username'] or "dev"
        new_name = f"[CLAIMED][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        
        # In database.py, update_thread_status with CLAIMED resets the other fields if we don't pass them
        # We want to keep the claim info but reset the resolution info
        update_thread_status(thread.id, "CLAIMED", 
                             resolved_by_id=None, 
                             resolved_by_username=None, 
                             pr_url=None)
        
        # Decrement developer leaderboard
        # Find the original resolver's ID
        resolver_id = thread_info['resolved_by_id']
        if resolver_id:
            decrement_developer_resolved(resolver_id)
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Unresolved",
            description=f"Unresolved by: {interaction.user.mention}",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Old Status", value="[Pending-Review]", inline=True)
        embed.add_field(name="New Status", value=f"[CLAIMED][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket unresolved: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error unresolving ticket: {e}")
        await interaction.followup.send(f"❌ Error unresolving ticket: {e}")



@bot.tree.command(
    name="reviewed",
    description="Approve a ticket after review (use inside a thread) - QA only"
)
async def reviewed_ticket(interaction: discord.Interaction):
    """Mark a ticket as reviewed after QA approval. Only QAs can review. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a QA or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_qa'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only QAs can review tickets. Use `/set-role` to get the QA role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] != 'PENDING-REVIEW':
            await interaction.followup.send("⚠️ This ticket is not pending review. Only pending review tickets can be reviewed.")
            return
        
        if thread_info['status'] == 'REVIEWED':
            await interaction.followup.send("⚠️ This ticket is already reviewed")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[Reviewed][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "REVIEWED", reviewed_by_id=interaction.user.id, reviewed_by_username=username)
        
        # Update QA leaderboard
        increment_qa_reviewed(interaction.user.id, str(interaction.user))
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Reviewed",
            description=f"Reviewed by: {interaction.user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Old Status", value="[Pending-Review]", inline=True)
        embed.add_field(name="New Status", value=f"[Reviewed][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket reviewed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error reviewing ticket: {e}")
        await interaction.followup.send(f"❌ Error reviewing ticket: {e}")


@bot.tree.command(
    name="unreview",
    description="Revert a REVIEWED ticket back to PENDING-REVIEW (use inside a thread) - QA only"
)
async def unreview_ticket(interaction: discord.Interaction):
    """Revert a ticket from REVIEWED back to PENDING-REVIEW. Only QAs can unreview. Must be used inside a ticket thread."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        # Check if user is a QA or PM
        user_roles = get_user_roles(interaction.user.id)
        if not (user_roles['is_qa'] or user_roles['is_pm']):
            await interaction.followup.send("❌ Only QAs can unreview tickets. Use `/set-role` to get the QA role.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] != 'REVIEWED':
            await interaction.followup.send("⚠️ This ticket is not reviewed. Only REVIEWED tickets can be unreviewed.")
            return
        
        # Update thread name back to PENDING-REVIEW
        ticket_name = thread_info['ticket_name']
        dev_username = thread_info['resolved_by_username'] or "dev"
        new_name = f"[Pending-Review][{dev_username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        
        # Update status back to PENDING-REVIEW and clear reviewer info
        update_thread_status(thread.id, "PENDING-REVIEW", 
                             reviewed_by_id=None, 
                             reviewed_by_username=None)
        
        # Decrement QA leaderboard
        reviewer_id = thread_info['reviewed_by_id']
        if reviewer_id:
            decrement_qa_reviewed(reviewer_id)
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Unreviewed",
            description=f"Unreviewed by: {interaction.user.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Old Status", value="[Reviewed]", inline=True)
        embed.add_field(name="New Status", value=f"[Pending-Review][{dev_username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket unreviewed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error unreviewing ticket: {e}")
        await interaction.followup.send(f"❌ Error unreviewing ticket: {e}")



@bot.tree.command(
    name="closed",
    description="Mark a ticket as CLOSED (use inside a thread) - PM or involved Dev/QA only"
)
async def close_ticket(interaction: discord.Interaction):
    """Mark a ticket as closed. Must be used inside a ticket thread. Restrict to PM or involved users."""
    await safe_defer(interaction)
    
    try:
        # Check if user is in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a thread. Go to the ticket thread and try again.")
            return
        
        thread = interaction.channel
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'CLOSED':
            await interaction.followup.send("⚠️ This ticket is already closed")
            return

        # Ownership / Permission Check
        user_roles = get_user_roles(interaction.user.id)
        is_pm = user_roles['is_pm']
        
        # Check if user is involved (Dev who claimed/resolved, or QA who reviewed)
        is_involved = (
            interaction.user.id == thread_info['claimed_by_id'] or
            interaction.user.id == thread_info['resolved_by_id'] or
            interaction.user.id == thread_info['reviewed_by_id']
        )
        
        if not (is_pm or is_involved):
            await interaction.followup.send("❌ Only Project Managers or the Developer/QA involved in this ticket can close it.")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[CLOSED][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "CLOSED")
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Closed by: {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Old Status", value=thread_info['status'], inline=True)
        embed.add_field(name="New Status", value=f"[CLOSED][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket closed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        await interaction.followup.send(f"❌ Error closing ticket: {e}")



@bot.tree.command(
    name="leaderboard",
    description="Show the leaderboard of resolved tickets"
)
@app_commands.describe(
    role="Filter leaderboard by role: 'dev' for Developers or 'qa' for QAs (default: dev)",
    limit="Number of top resolvers to show (default: 10, max: 50)"
)
async def show_leaderboard(interaction: discord.Interaction, role: str = "dev", limit: int = 10):
    """Display the leaderboard of users who have resolved the most tickets."""
    await safe_defer(interaction)
    
    try:
        # Validate role parameter
        role_lower = role.lower().strip()
        if role_lower not in ["dev", "developer", "qa", "qas"]:
            await interaction.followup.send("❌ Invalid role. Use 'dev' for Developers or 'qa' for QAs.")
            return
        
        # Normalize role
        if role_lower in ["dev", "developer"]:
            role_param = "dev"
            title_role = "👨‍💻 Developer Resolution Leaderboard"
            stat_name = "Resolved"
        else:
            role_param = "qa"
            title_role = "🔍 QA Review Leaderboard"
            stat_name = "Reviewed"
        
        # Clamp limit between 1 and 50
        limit = max(1, min(limit, 50))
        
        # Get leaderboard based on role
        if role_param == "dev":
            leaderboard = get_leaderboard_dev(limit)
        else:
            leaderboard = get_leaderboard_qa(limit)
        
        if not leaderboard:
            await interaction.followup.send(f"📊 No {role_param.upper()} activity yet!")
            return
        
        # Build leaderboard description
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, entry in enumerate(leaderboard, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}️⃣"
            
            if role_param == "dev":
                count = entry['dev_resolved_count']
            else:
                count = entry['qa_reviewed_count']
            
            description += f"{medal} **{entry['username']}** - {count} {stat_name}\n"
        
        embed = discord.Embed(
            title=title_role,
            description=description,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Showing top {limit} {role_param.upper()}s")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Leaderboard shown to {interaction.user} (role: {role_param})")
        
    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        await interaction.followup.send(f"❌ Error showing leaderboard: {e}")


@bot.tree.command(
    name="ticket-folders",
    description="List all available ticket folders"
)
async def list_folders(interaction: discord.Interaction):
    """List all available ticket folders."""
    await safe_defer(interaction)
    
    try:
        folders = get_available_folders()
        
        if not folders:
            await interaction.followup.send(f"📁 No folders found in `{TICKETS_DIR}/` directory")
            return
        
        folder_list = "\n".join([f"• `{folder}`" for folder in folders])
        
        embed = discord.Embed(
            title="Available Ticket Folders",
            description=folder_list,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Total: {len(folders)} folder(s)")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        await interaction.followup.send(f"❌ Error listing folders: {e}")


@bot.tree.command(
    name="help",
    description="Show all available commands and how to use them"
)
async def show_help(interaction: discord.Interaction):
    """Display help information for all commands."""
    await safe_defer(interaction)
    
    try:
        # Create main help embed
        embed = discord.Embed(
            title="📖 Ticket Bot Help",
            description="Complete guide to all available commands",
            color=discord.Color.blurple()
        )
        
        # Role Management
        embed.add_field(
            name="👥 Role Management",
            value="**`/set-role <developer|qa|pm>`**\n" +
                  "Assign yourself a role (Developer, QA, or PM).\n" +
                  "Also assigns the corresponding Discord role.\n" +
                  "`/set-role developer` or `/set-role qa` or `/set-role pm`",
            inline=False
        )
        
        # Ticket Loading
        embed.add_field(
            name="📂 Loading Tickets (PM only)",
            value="**`/load-tickets <folder> <channel>`**\n" +
                  "Load tickets from a folder into a Discord channel.\n" +
                  "Creates threads for each markdown file.\n" +
                  "**`/rebuild-db <folder> <channel>`**\n" +
                  "Rebuild database entries from existing threads in a channel.\n" +
                  "**`/scan-project <path> <folder> [threshold]`**\n" +
                  "Scan a codebase and generate issue-based ticket files.\n" +
                  "**`/scan-roadmap <path> <folder> [threshold] [generate_tickets]`**\n" +
                  "Generate full repo structure/component analysis and a 12-week (3-month) roadmap.\n" +
                  "**`/scan-repo <repo_url> [folder] [branch] [threshold] [generate_tickets]`**\n" +
                  "Cloud-safe scan by cloning a repository URL before analysis.\n" +
                  "*Only Project Managers can use this*\n" +
                  "`/load-tickets support #support-channel`",
            inline=False
        )
        
        # Developer Commands
        embed.add_field(
            name="👨‍💻 Developer Commands",
            value="**`/claim`** (in thread) - Claim a ticket to work on it\n" +
                  "After claiming, checkout the suggested branch from the bot response.\n" +
                  "Branch workflow guide: `CLAIM_BRANCH_WORKFLOW.md`\n" +
                  "**`/unclaim`** (in thread) - Unclaim a ticket and reset to OPEN\n" +
                  "**`/resolved <pr_url>`** (in thread) - Submit ticket for QA review with PR link (adds to dev leaderboard)\n" +
                  "**`/unresolve`** (in thread) - Revert status back to CLAIMED (decrements leaderboard)\n" +
                  "*Only available to users with Developer role*",
            inline=False
        )
        
        # QA Commands
        embed.add_field(
            name="🔍 QA Commands",
            value="**`/reviewed`** (in thread) - Approve reviewed ticket (adds to QA leaderboard)\n" +
                  "**`/unreview`** (in thread) - Revert status back to Pending-Review (decrements leaderboard)\n" +
                  "Must be used on tickets in Pending-Review status\n" +
                  "*Only available to users with QA role*",
            inline=False
        )
        
        # General Commands
        embed.add_field(
            name="⚙️ General Commands",
            value="**`/closed`** (in thread) - Close a ticket\n" +
                  "**`/ticket-info`** (in thread) - View ticket tracking details\n" +
                  "**`/ask-ai <prompt>`** - Ask configured NVIDIA model (PM only)\n" +
                  "**`/leaderboard <dev|qa> [limit]`** - View leaderboard\n" +
                  "**`/stats`** - Show project ticket overview\n" +
                  "**`/setreminderschannel <channel>`** - Set channel for daily 8 AM summary (PM only)\n" +
                  "**`/ticket-folders`** - List all available ticket folders\n" +
                  "**`/archive-closed`** - Archive all closed threads in the channel (PM/Admin only)\n" +
                  "**`/setstalethreshold <hours>`** - Set stale-ticket threshold for daily summary (PM only)\n" +
                  "**`/clear <amount>`** - Delete messages in the channel (PM/Admin only)\n" +
                  "**`/sync-commands`** - Force sync commands to this server (Admin only)\n" +
                  "**`/help`** - Show this help message",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        # Send workflow embed
        workflow_embed = discord.Embed(
            title="🔄 Ticket Workflow",
            description="The typical ticket lifecycle",
            color=discord.Color.green()
        )
        
        workflow_embed.add_field(
            name="1️⃣ Load Tickets",
            value="`/load-tickets <folder> <channel>`\nCreates `[OPEN]` threads",
            inline=True
        )
        
        workflow_embed.add_field(
            name="2️⃣ Developer Claims",
            value="`/claim` (in thread)\nStatus: `[CLAIMED][dev]`\nThen run git checkout with suggested branch",
            inline=True
        )
        
        workflow_embed.add_field(
            name="3️⃣ Dev Submits",
            value="`/resolved <pr_url>` (in thread)\nStatus: `[Pending-Review][dev]`",
            inline=True
        )
        
        workflow_embed.add_field(
            name="4️⃣ QA Reviews",
            value="`/reviewed` (in thread)\nStatus: `[Reviewed][qa]`",
            inline=True
        )
        
        workflow_embed.add_field(
            name="5️⃣ Close Ticket",
            value="`/closed` (in thread)\nStatus: `[CLOSED][user]`",
            inline=True
        )
        
        workflow_embed.add_field(
            name="6️⃣ Check Leaderboard",
            value="`/leaderboard dev` or `/leaderboard qa`",
            inline=True
        )
        
        await interaction.followup.send(embed=workflow_embed)
        
        # Send roles and permissions embed
        roles_embed = discord.Embed(
            title="📋 Roles & Permissions",
            description="What each role can do",
            color=discord.Color.gold()
        )
        
        roles_embed.add_field(
            name="🔧 Project Manager (Admin)",
            value="✓ `/load-tickets` - Load tickets into channels\n" +
                  "✓ `/rebuild-db` - Rebuild database from existing threads\n" +
                  "✓ `/scan-project` - Scan local/runtime-accessible folder\n" +
                  "✓ `/scan-roadmap` - Build roadmap from local/runtime-accessible folder\n" +
                  "✓ `/scan-repo` - Clone and scan repository URL (cloud-safe)\n" +
                  "✓ `/claim` - Claim tickets (like Dev)\n" +
                  "✓ `/resolved` - Submit for review (like Dev)\n" +
                  "✓ `/reviewed` - Approve tickets (like QA)\n" +
                  "✓ `/closed` - Close tickets\n" +
                  "✓ Can do EVERYTHING\n" +
                  "✓ Gets Discord `Project Manager` role",
            inline=True
        )
        
        roles_embed.add_field(
            name="👨‍💻 Developer",
            value="✓ `/claim` - Claim tickets\n" +
                  "✓ `/resolved` - Submit for review\n" +
                  "✓ `/closed` - Close tickets\n" +
                  "✓ View dev leaderboard\n" +
                  "✓ Gets Discord `Developer` role",
            inline=True
        )
        
        roles_embed.add_field(
            name="🔍 QA",
            value="✓ `/reviewed` - Approve tickets\n" +
                  "✓ `/closed` - Close tickets\n" +
                  "✓ View QA leaderboard\n" +
                  "✓ Gets Discord `QA` role",
            inline=True
        )
        
        roles_embed.add_field(
            name="📝 Role System",
            value="⚠️ **ONE role per user only**\n" +
                  "When you set a new role, your old role is replaced\n" +
                  "PM has all permissions (like an admin)",
            inline=False
        )
        
        await interaction.followup.send(embed=roles_embed)
        
        logger.info(f"Help shown to {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error showing help: {e}")
        await interaction.followup.send(f"❌ Error showing help: {e}")


@bot.tree.command(
    name="ask-ai",
    description="Ask the configured NVIDIA AI model (PM only)"
)
@app_commands.describe(
    prompt="What you want the model to answer",
    temperature="Creativity level from 0.0 to 2.0 (default: 0.7)"
)
async def ask_ai(interaction: discord.Interaction, prompt: str, temperature: float = 0.7):
    """Run a prompt against NVIDIA chat-completions and return the response."""
    await safe_defer(interaction)

    try:
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can use `/ask-ai`.")
            return

        if len(prompt.strip()) < 2:
            await interaction.followup.send("❌ Prompt is too short.")
            return

        if len(prompt) > 4000:
            await interaction.followup.send("❌ Prompt is too long. Keep it under 4000 characters.")
            return

        if not ai_client.is_configured():
            await interaction.followup.send(
                "❌ AI is not configured. Set `NVIDIA_API_KEY`, `NVIDIA_MODEL`, and `NVIDIA_INVOKE_URL` in environment variables."
            )
            return

        # Run blocking HTTP call off the event loop to avoid interaction expiry.
        answer = await asyncio.to_thread(
            ai_client.chat,
            prompt,
            temperature=temperature,
            max_tokens=2048,
            top_p=0.95,
            enable_thinking=True,
        )

        header = f"🤖 **Model:** `{ai_client.model}`\n\n"
        full_text = header + answer

        max_len = 1900
        parts = [full_text[i:i + max_len] for i in range(0, len(full_text), max_len)]
        for idx, part in enumerate(parts[:5], start=1):
            if len(parts) > 1:
                await interaction.followup.send(f"**AI Response ({idx}/{len(parts)})**\n{part}")
            else:
                await interaction.followup.send(part)

        if len(parts) > 5:
            await interaction.followup.send("⚠️ Response truncated after 5 messages.")

    except AIClientError as e:
        logger.warning("AI request failed: %s", e)
        await interaction.followup.send(f"❌ AI request failed: {e}")
    except Exception as e:
        logger.error("Error running ask-ai: %s", e)
        await interaction.followup.send(f"❌ Error running ask-ai: {e}")


@bot.tree.command(
    name="scan-project",
    description="Scan a project folder for issues and auto-generate tickets (PM only)"
)
@app_commands.describe(
    path="Absolute path to the project folder to scan (e.g. F:\\my-project)",
    folder="Output folder name in tickets/ for generated ticket files",
    threshold="Line count threshold for large file detection (default: 300)"
)
async def scan_project(interaction: discord.Interaction, path: str, folder: str, threshold: int = SCAN_LARGE_FILE_THRESHOLD):
    """Scan a project directory for code issues and generate ticket markdown files.
    Only PMs can use this command."""
    await safe_defer(interaction)

    try:
        # Check if user is a PM
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can scan projects. Use `/set-role pm` first.")
            return

        # Validate path
        project_path = Path(path)
        if not project_path.exists() or not project_path.is_dir():
            await interaction.followup.send(f"❌ Path not found or not a directory: `{path}`")
            return

        # Send "scanning" message
        await interaction.followup.send(f"🔍 Scanning `{path}`... this may take a moment.")

        # Run the scanner
        total_issues, total_tickets, generated_files, summary = scan_and_generate_with_summary(
            project_path=str(project_path),
            output_folder=folder,
            tickets_dir=TICKETS_DIR,
            ignore_dirs=SCAN_IGNORE_DIRS,
            file_extensions=SCAN_FILE_EXTENSIONS,
            large_file_threshold=threshold,
        )

        if total_issues == 0:
            embed = discord.Embed(
                title="✨ No Issues Found",
                description=f"Scanned `{path}` — no issues detected!",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            return

        # Build results embed
        embed = discord.Embed(
            title="📋 Scan Complete",
            description=f"Scanned `{path}`",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Files Scanned", value=str(summary.files_scanned), inline=True)
        embed.add_field(name="Issues Found", value=str(total_issues), inline=True)
        embed.add_field(name="Tickets Generated", value=str(total_tickets), inline=True)
        embed.add_field(name="Output Folder", value=f"`tickets/{folder}/`", inline=True)

        sev = summary.by_severity
        severity_line = (
            f"High: **{sev.get('high', 0)}** | "
            f"Medium: **{sev.get('medium', 0)}** | "
            f"Low: **{sev.get('low', 0)}**"
        )
        embed.add_field(name="Severity Breakdown", value=severity_line, inline=False)

        if summary.by_category:
            top_categories = sorted(summary.by_category.items(), key=lambda x: x[1], reverse=True)[:5]
            category_lines = "\n".join([f"• `{name}`: {count}" for name, count in top_categories])
            embed.add_field(name="Top Issue Categories", value=category_lines, inline=False)

        if summary.top_directories:
            hotspot_lines = "\n".join([f"• `{directory}`: {count}" for directory, count in summary.top_directories])
            embed.add_field(name="Code Hotspots", value=hotspot_lines, inline=False)

        # List generated tickets
        if generated_files:
            file_list = "\n".join([f"• `{Path(f).name}`" for f in generated_files[:20]])
            if len(generated_files) > 20:
                file_list += f"\n• ... and {len(generated_files) - 20} more"
            embed.add_field(name="Generated Tickets", value=file_list, inline=False)

        embed.add_field(
            name="Next Step",
            value=f"Run `/load-tickets {folder} #channel` to create Discord threads from these tickets.",
            inline=False
        )

        await interaction.followup.send(embed=embed)
        logger.info(
            f"Project scan complete: {summary.files_scanned} files, "
            f"{total_issues} issues, {total_tickets} tickets in {folder}/"
        )

    except FileNotFoundError as e:
        await interaction.followup.send(f"❌ {e}")
    except Exception as e:
        logger.error(f"Error scanning project: {e}")
        await interaction.followup.send(f"❌ Error scanning project: {e}")


@bot.tree.command(
    name="scan-roadmap",
    description="Scan full project and generate a roadmap + suggestions (PM only)"
)
@app_commands.describe(
    path="Absolute folder path OR HTTPS Git repo URL to scan",
    folder="Output folder name in tickets/ for roadmap and generated tickets",
    threshold="Line count threshold for large file detection (default: 300)",
    generate_tickets="Also generate issue ticket files in the same folder (default: true)",
    skip_code_issues="Skip issue detectors (TODO/debug/secrets/etc.) and focus roadmap on features/components"
)
async def scan_roadmap(
    interaction: discord.Interaction,
    path: str,
    folder: str,
    threshold: int = SCAN_LARGE_FILE_THRESHOLD,
    generate_tickets: bool = True,
    skip_code_issues: bool = True,
):
    """Generate a project roadmap from scanner findings. Only PMs can use this command."""
    await safe_defer(interaction)

    try:
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can generate roadmaps. Use `/set-role pm` first.")
            return

        source_label = path
        if path.startswith("http://") or path.startswith("https://"):
            await interaction.followup.send(f"🌐 Cloning repository for roadmap scan: `{path}`")
            with tempfile.TemporaryDirectory(prefix="roadmap-scan-") as tmp:
                clone_target = Path(tmp) / "repo"
                clone_proc = subprocess.run(
                    ["git", "clone", "--depth", "1", path, str(clone_target)],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=240,
                )

                if clone_proc.returncode != 0:
                    stderr = (clone_proc.stderr or "").strip()
                    short_error = stderr[:900] if stderr else "Unknown clone error"
                    await interaction.followup.send(
                        "❌ Failed to clone repository. Ensure URL is valid and accessible from cloud runtime.\n"
                        f"Details: `{short_error}`"
                    )
                    return

                result = build_project_roadmap(
                    project_path=str(clone_target),
                    output_folder=folder,
                    scan_source=source_label,
                    tickets_dir=TICKETS_DIR,
                    ignore_dirs=SCAN_IGNORE_DIRS,
                    file_extensions=SCAN_FILE_EXTENSIONS,
                    large_file_threshold=threshold,
                    generate_issue_tickets=generate_tickets,
                    skip_code_issues=skip_code_issues,
                )
        else:
            project_path = Path(path)
            if not project_path.exists() or not project_path.is_dir():
                await interaction.followup.send(f"❌ Path not found or not a directory: `{path}`")
                return

            await interaction.followup.send(f"🧭 Building roadmap from `{path}`... this may take a moment.")
            result = build_project_roadmap(
                project_path=str(project_path),
                output_folder=folder,
                scan_source=source_label,
                tickets_dir=TICKETS_DIR,
                ignore_dirs=SCAN_IGNORE_DIRS,
                file_extensions=SCAN_FILE_EXTENSIONS,
                large_file_threshold=threshold,
                generate_issue_tickets=generate_tickets,
                skip_code_issues=skip_code_issues,
            )

        embed = discord.Embed(
            title="🧭 Roadmap Generated",
            description=f"Scanned `{source_label}` and built execution roadmap",
            color=discord.Color.green(),
        )
        embed.add_field(name="Scanned Files", value=str(result.total_files_scanned), inline=True)
        embed.add_field(name="Components", value=str(result.total_components), inline=True)
        embed.add_field(name="Roadmap Weeks", value=str(result.roadmap_weeks), inline=True)
        embed.add_field(name="Issues Found", value=str(result.total_issues), inline=True)
        embed.add_field(name="Tickets Generated", value=str(result.total_tickets), inline=True)
        embed.add_field(name="Roadmap File", value=f"`tickets/{folder}/ROADMAP.md`", inline=False)

        if result.top_categories:
            top = "\n".join([f"• {name}: {count}" for name, count in result.top_categories[:5]])
            embed.add_field(name="Top Findings", value=top, inline=False)

        if result.suggested_features:
            suggestions = "\n".join([f"• {item}" for item in result.suggested_features[:4]])
            embed.add_field(name="Suggested Features", value=suggestions, inline=False)

        if result.top_components:
            comp_lines = "\n".join([f"• {name}: {count} issue(s)" for name, count in result.top_components[:4]])
            embed.add_field(name="Top Components", value=comp_lines, inline=False)

        if result.detected_features:
            feature_lines = "\n".join([f"• {name}: {count} component(s)" for name, count in result.detected_features[:4]])
            embed.add_field(name="Detected Feature Map", value=feature_lines, inline=False)

        embed.add_field(
            name="Next Step",
            value=f"Review `tickets/{folder}/ROADMAP.md`, then run `/load-tickets {folder} #channel`.",
            inline=False,
        )

        await interaction.followup.send(embed=embed)
        logger.info(
            "Roadmap generated for %s: files=%s issues=%s tickets=%s folder=%s",
            path,
            result.total_files_scanned,
            result.total_issues,
            result.total_tickets,
            folder,
        )
    except FileNotFoundError as e:
        await interaction.followup.send(f"❌ {e}")
    except subprocess.TimeoutExpired:
        await interaction.followup.send("❌ Repository clone timed out. Try a smaller repo or use `/scan-repo` with a specific branch.")
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        await interaction.followup.send(f"❌ Error generating roadmap: {e}")


def _repo_default_folder(repo_url: str) -> str:
    """Create a safe default folder name from repository URL."""
    parsed = urlparse(repo_url)
    name = Path(parsed.path).name or "repo-scan"
    if name.endswith(".git"):
        name = name[:-4]
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", name).strip("-")
    return name.lower() or "repo-scan"


@bot.tree.command(
    name="scan-repo",
    description="Clone and scan a Git repo URL in cloud-safe mode (PM only)"
)
@app_commands.describe(
    repo_url="Git repository URL (HTTPS)",
    folder="Output folder name in tickets/ (optional)",
    branch="Branch to scan (optional, default: repo default branch)",
    threshold="Line count threshold for large file detection (default: 300)",
    generate_tickets="Also generate issue ticket files in the same folder (default: true)",
    skip_code_issues="Skip issue detectors (TODO/debug/secrets/etc.) and focus roadmap on features/components"
)
async def scan_repo(
    interaction: discord.Interaction,
    repo_url: str,
    folder: str | None = None,
    branch: str | None = None,
    threshold: int = SCAN_LARGE_FILE_THRESHOLD,
    generate_tickets: bool = True,
    skip_code_issues: bool = True,
):
    """Clone a repo to temp storage and run roadmap scanner. Only PMs can use this command."""
    await safe_defer(interaction)

    try:
        if not has_role(interaction.user.id, "pm"):
            await interaction.followup.send("❌ Only Project Managers can scan repositories. Use `/set-role pm` first.")
            return

        if not repo_url.startswith("http://") and not repo_url.startswith("https://"):
            await interaction.followup.send("❌ Please provide a valid HTTP/HTTPS Git repository URL.")
            return

        output_folder = folder or _repo_default_folder(repo_url)
        await interaction.followup.send(f"🌐 Cloning and scanning repository: `{repo_url}`")

        with tempfile.TemporaryDirectory(prefix="repo-scan-") as tmp:
            clone_target = Path(tmp) / "repo"
            clone_cmd = ["git", "clone", "--depth", "1"]
            if branch:
                clone_cmd.extend(["--branch", branch])
            clone_cmd.extend([repo_url, str(clone_target)])

            clone_proc = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=240,
            )

            if clone_proc.returncode != 0:
                stderr = (clone_proc.stderr or "").strip()
                short_error = stderr[:900] if stderr else "Unknown clone error"
                await interaction.followup.send(
                    "❌ Failed to clone repository. Ensure URL is valid and accessible from cloud runtime.\n"
                    f"Details: `{short_error}`"
                )
                return

            result = build_project_roadmap(
                project_path=str(clone_target),
                output_folder=output_folder,
                scan_source=repo_url,
                tickets_dir=TICKETS_DIR,
                ignore_dirs=SCAN_IGNORE_DIRS,
                file_extensions=SCAN_FILE_EXTENSIONS,
                large_file_threshold=threshold,
                generate_issue_tickets=generate_tickets,
                skip_code_issues=skip_code_issues,
            )

        embed = discord.Embed(
            title="🌐 Repo Scan Complete",
            description=f"Scanned `{repo_url}`",
            color=discord.Color.teal(),
        )
        embed.add_field(name="Scanned Files", value=str(result.total_files_scanned), inline=True)
        embed.add_field(name="Components", value=str(result.total_components), inline=True)
        embed.add_field(name="Roadmap Weeks", value=str(result.roadmap_weeks), inline=True)
        embed.add_field(name="Issues Found", value=str(result.total_issues), inline=True)
        embed.add_field(name="Tickets Generated", value=str(result.total_tickets), inline=True)
        embed.add_field(name="Output Folder", value=f"`tickets/{output_folder}/`", inline=False)
        embed.add_field(name="Roadmap File", value=f"`tickets/{output_folder}/ROADMAP.md`", inline=False)

        if result.top_categories:
            top = "\n".join([f"• {name}: {count}" for name, count in result.top_categories[:5]])
            embed.add_field(name="Top Findings", value=top, inline=False)

        if result.top_components:
            comp_lines = "\n".join([f"• {name}: {count} issue(s)" for name, count in result.top_components[:4]])
            embed.add_field(name="Top Components", value=comp_lines, inline=False)

        if result.detected_features:
            feature_lines = "\n".join([f"• {name}: {count} component(s)" for name, count in result.detected_features[:4]])
            embed.add_field(name="Detected Feature Map", value=feature_lines, inline=False)

        embed.add_field(
            name="Next Step",
            value=f"Review `tickets/{output_folder}/ROADMAP.md`, then run `/load-tickets {output_folder} #channel`.",
            inline=False,
        )

        await interaction.followup.send(embed=embed)
        logger.info(
            "Repo scan complete: repo=%s files=%s issues=%s tickets=%s folder=%s",
            repo_url,
            result.total_files_scanned,
            result.total_issues,
            result.total_tickets,
            output_folder,
        )
    except subprocess.TimeoutExpired:
        await interaction.followup.send("❌ Repository clone timed out. Try a smaller repo or specify a branch.")
    except FileNotFoundError:
        await interaction.followup.send("❌ Git is not available in this runtime. Install git in deployment image to use `/scan-repo`.")
    except Exception as e:
        logger.error(f"Error scanning repository URL: {e}")
        await interaction.followup.send(f"❌ Error scanning repository URL: {e}")


@bot.tree.command(
    name="clear",
    description="Bulk delete messages in the current channel (PM/Admin only)"
)
@app_commands.describe(amount="The number of messages to delete (max 100)")
async def clear_messages(interaction: discord.Interaction, amount: int = 10):
    """Delete a specified number of messages in the channel."""
    await safe_defer(interaction, ephemeral=True)
    
    try:
        # Check if user is a PM or Admin
        is_pm = has_role(interaction.user.id, "pm")
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_pm or is_admin):
            await interaction.followup.send("❌ Only Project Managers or Administrators can use this command.")
            return
            
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("❌ This command can only be used in regular text channels.")
            return
            
        # Limit to 100 max
        delete_amount = min(max(1, amount), 100)
        
        # Purge messages
        deleted = await interaction.channel.purge(limit=delete_amount)
        await interaction.followup.send(f"✅ Successfully deleted {len(deleted)} message(s).", ephemeral=True)
        logger.info(f"Cleared {len(deleted)} messages in {interaction.channel.name} by {interaction.user}")
        
    except discord.Forbidden:
        await interaction.followup.send("❌ The bot doesn't have permission to manage messages here.")
    except Exception as e:
        logger.error(f"Error clearing messages: {e}")
        await interaction.followup.send(f"❌ Error clearing messages: {e}")


@bot.tree.command(
    name="archive-closed",
    description="Archive all [CLOSED] threads in the current channel (PM/Admin only)"
)
async def archive_closed_threads(interaction: discord.Interaction):
    """Finds all open threads with the [CLOSED] prefix and archives them."""
    await safe_defer(interaction)
    
    try:
        is_pm = has_role(interaction.user.id, "pm")
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_pm or is_admin):
            await interaction.followup.send("❌ Only Project Managers or Administrators can archive threads.")
            return
            
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("❌ This command must be run in the parent text channel, not inside a thread.")
            return
            
        archived_count = 0
        for thread in interaction.channel.threads:
            if thread.name.startswith("[CLOSED]"):
                await thread.edit(archived=True, reason=f"Bulk archived by {interaction.user}")
                archived_count += 1
                
        if archived_count > 0:
            embed = discord.Embed(
                title="Threads Archived",
                description=f"✅ Successfully archived **{archived_count}** closed thread(s).",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("ℹ️ No active `[CLOSED]` threads found to archive.")
            
    except Exception as e:
        logger.error(f"Error archiving threads: {e}")
        await interaction.followup.send(f"❌ Error archiving threads: {e}")


@bot.tree.command(
    name="stats",
    description="Show a dashboard overview of project ticket statistics"
)
async def project_stats(interaction: discord.Interaction):
    """Display an overview of tickets grouped by status."""
    await safe_defer(interaction)
    
    try:
        status_groups = get_threads_by_status()
        
        open_count = len(status_groups.get("OPEN", []))
        claimed_count = len(status_groups.get("CLAIMED", []))
        pending_count = len(status_groups.get("PENDING-REVIEW", []))
        reviewed_count = len(status_groups.get("REVIEWED", []))
        closed_count = len(status_groups.get("CLOSED", []))
        
        total_active = open_count + claimed_count + pending_count + reviewed_count
        
        embed = discord.Embed(
            title="📊 Project Ticket Statistics",
            color=discord.Color.blurple()
        )
        
        embed.add_field(name="🔵 Open", value=str(open_count), inline=True)
        embed.add_field(name="🟡 Claimed", value=str(claimed_count), inline=True)
        embed.add_field(name="🟠 Pending Review", value=str(pending_count), inline=True)
        
        embed.add_field(name="🟢 Reviewed", value=str(reviewed_count), inline=True)
        embed.add_field(name="🔴 Closed", value=str(closed_count), inline=True)
        embed.add_field(name="📈 Total Active", value=str(total_active), inline=True)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error viewing stats: {e}")
        await interaction.followup.send(f"❌ Error viewing stats: {e}")


@bot.tree.command(
    name="ticket-info",
    description="View tracking details for the current ticket (use inside a thread)"
)
async def ticket_info(interaction: discord.Interaction):
    """Fetch database info about the current ticket."""
    await safe_defer(interaction)
    
    try:
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send("❌ This command must be used inside a ticket thread.")
            return
            
        thread_info = get_thread(interaction.channel.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database as a ticket.")
            return
            
        embed = discord.Embed(
            title="🏷️ Ticket Information",
            description=f"**{thread_info.get('ticket_name', 'Unknown')}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="📁 Folder", value=f"`{thread_info.get('folder', 'Unknown')}`", inline=True)
        embed.add_field(name="📌 Status", value=f"`{thread_info.get('status', 'Unknown')}`", inline=True)
        embed.add_field(name="📅 Created By", value=thread_info.get('created_by') or "Unknown", inline=True)
        
        claimed_by = thread_info.get('claimed_by_username')
        if claimed_by:
            embed.add_field(name="👨‍💻 Claimed By", value=claimed_by, inline=True)
            
        resolved_by = thread_info.get('resolved_by_username')
        if resolved_by:
            embed.add_field(name="🛠️ Resolved By", value=resolved_by, inline=True)
            
        reviewed_by = thread_info.get('reviewed_by_username')
        if reviewed_by:
            embed.add_field(name="🔍 Reviewed By", value=reviewed_by, inline=True)
            
        pr_url = thread_info.get('pr_url')
        if pr_url:
            embed.add_field(name="🔗 PR Link", value=pr_url, inline=False)
            
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error fetching ticket info: {e}")
        await interaction.followup.send(f"❌ Error fetching ticket info: {e}")



# ─── Commit / Merge Announcements ─────────────────────────────────────────────

COMMIT_CHANNEL_SETTING = "commit_announce_channel_id"


@bot.tree.command(
    name="set-commit-channel",
    description="Set the channel where commit/merge announcements will be posted (PM only)"
)
@app_commands.describe(channel="The text channel that will receive commit announcements")
async def set_commit_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Configure the commit announcement channel. PM-only."""
    await safe_defer(interaction, ephemeral=True)

    if not has_role(interaction.user.id, "pm"):
        await interaction.followup.send("❌ Only Project Managers can configure the commit channel.")
        return

    set_setting(COMMIT_CHANNEL_SETTING, str(channel.id))
    await interaction.followup.send(
        f"✅ Commit announcements will now be posted to {channel.mention}."
    )
    logger.info(f"Commit channel set to {channel.id} by {interaction.user}")


@bot.tree.command(
    name="post-commits",
    description="Post recent commits (or merged-only) to the configured announcement channel (PM only)"
)
@app_commands.describe(
    repo_url="Base GitHub repository URL (e.g. https://github.com/org/repo)",
    limit="Number of commits to include (default 10)",
    merged_only="If True, only include merge commits (default False)",
    branch="Branch to read commits from (default: current HEAD)"
)
async def post_commits(
    interaction: discord.Interaction,
    repo_url: str,
    limit: app_commands.Range[int, 1, 50] = 10,
    merged_only: bool = False,
    branch: str = "HEAD",
):
    """Fetch recent git commits and post a formal announcement embed to the configured channel."""
    await safe_defer(interaction, ephemeral=True)

    if not has_role(interaction.user.id, "pm"):
        await interaction.followup.send("❌ Only Project Managers can post commit announcements.")
        return

    # ── Resolve the target channel ────────────────────────────────────────────
    channel_id_str = get_setting(COMMIT_CHANNEL_SETTING)
    if not channel_id_str:
        await interaction.followup.send(
            "❌ No commit channel configured. Use `/set-commit-channel` first."
        )
        return

    target_channel = interaction.guild.get_channel(int(channel_id_str))
    if not target_channel:
        await interaction.followup.send(
            "❌ Configured commit channel not found. Use `/set-commit-channel` to update it."
        )
        return

    # ── Build git log command ─────────────────────────────────────────────────
    # Format: hash | author | date | subject
    git_format = "%H|%an|%ad|%s"
    date_format = "%Y-%m-%d %H:%M +0000"

    git_cmd = [
        "git", "log",
        f"--format={git_format}",
        f"--date=format:{date_format}",
        f"-n {limit}",
        branch,
    ]
    if merged_only:
        git_cmd.insert(2, "--merges")

    try:
        result = subprocess.run(
            ["git", "log"]
            + (["--merges"] if merged_only else [])
            + [
                f"--format={git_format}",
                f"--date=format:{date_format}",
                f"-n{limit}",
                branch,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        await interaction.followup.send("❌ `git` is not available in this environment.")
        return
    except subprocess.TimeoutExpired:
        await interaction.followup.send("❌ `git log` timed out.")
        return

    raw_output = result.stdout.strip()
    if not raw_output:
        commit_type = "merge commits" if merged_only else "commits"
        await interaction.followup.send(
            f"⚠️ No {commit_type} found on branch `{branch}`."
        )
        return

    # ── Parse commits ─────────────────────────────────────────────────────────
    commits = []
    for line in raw_output.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        commit_hash, author, date_str, subject = parts
        commits.append({
            "hash": commit_hash.strip(),
            "short_hash": commit_hash.strip()[:7],
            "author": author.strip(),
            "date": date_str.strip(),
            "subject": subject.strip(),
        })

    if not commits:
        await interaction.followup.send("⚠️ Could not parse any commits from `git log` output.")
        return

    # ── Build and post the announcement ───────────────────────────────────────
    repo_url = repo_url.rstrip("/")
    commit_type_label = "Merge Commits" if merged_only else "Recent Commits"
    posted_by = interaction.user.display_name or interaction.user.name
    now_utc = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    # Header embed
    header_embed = discord.Embed(
        title=f"📋 Development Update — {commit_type_label}",
        description=(
            f"The following {'merge ' if merged_only else ''}commit(s) have been recorded "
            f"on branch **`{branch}`**.\n\n"
            f"*Posted by {posted_by} · {now_utc}*"
        ),
        color=discord.Color.from_rgb(30, 144, 255),  # Dodger blue — formal, clear
    )
    header_embed.set_footer(text="Source Control Update  ·  For internal use only")
    await target_channel.send(embed=header_embed)

    # One embed per commit (up to Discord's limit)
    for idx, commit in enumerate(commits, start=1):
        commit_url = f"{repo_url}/commit/{commit['hash']}"
        is_merge = commit["subject"].lower().startswith("merge")

        embed_color = discord.Color.from_rgb(88, 101, 242) if is_merge else discord.Color.from_rgb(87, 242, 135)
        kind_label = "🔀 Merge Commit" if is_merge else "✅ Commit"

        embed = discord.Embed(
            title=f"{kind_label}  ·  `{commit['short_hash']}`",
            description=f"**{commit['subject']}**",
            url=commit_url,
            color=embed_color,
            timestamp=datetime.strptime(commit["date"], "%Y-%m-%d %H:%M +0000").replace(tzinfo=timezone.utc),
        )
        embed.add_field(name="Author", value=commit["author"], inline=True)
        embed.add_field(name="Date", value=commit["date"], inline=True)
        embed.add_field(name="Reference", value=f"[View on GitHub]({commit_url})", inline=True)
        embed.set_footer(text=f"Commit {idx} of {len(commits)}")

        await target_channel.send(embed=embed)

    # Confirmation back to PM
    await interaction.followup.send(
        f"✅ Posted **{len(commits)}** {commit_type_label.lower()} to {target_channel.mention}."
    )
    logger.info(
        f"post-commits: {len(commits)} entries posted to channel {target_channel.id} by {interaction.user}"
    )


def main():
    """Start the bot."""
    try:
        if not verify_database_connection():
            raise RuntimeError("Database startup verification failed. Check DATABASE_URL credentials and host settings.")

        # Auto-enable keep-alive in Render unless explicitly overridden.
        keep_alive_enabled = os.getenv("KEEP_ALIVE_ENABLED")
        if keep_alive_enabled is None:
            keep_alive_enabled = "true" if os.getenv("RENDER") else "false"

        if keep_alive_enabled.lower() == "true":
            from keep_alive import keep_alive
            keep_alive()
        else:
            logger.info("Keep-alive server disabled (set KEEP_ALIVE_ENABLED=true to enable).")

        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()

