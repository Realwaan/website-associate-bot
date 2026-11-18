"""CapStoneFlow Discord Associate Bot - Modernized Modular Entrypoint."""
import asyncio
import hashlib
import logging
import os
import io
import re
import time
import discord
from discord.ext import commands
from services.readiness import bot_is_ready

from config import DISCORD_TOKEN
from database import (
    init_db,
    add_thread,
    get_thread,
    get_thread_by_external_task_id,
    get_threads_by_status,
    update_thread_status,
    begin_integration_delivery,
    finish_integration_delivery,
    get_setting,
    get_setting_across_guilds,
    set_setting,
    mark_repo_event_posted,
    register_webhook_delivery,
    enqueue_webhook_dead_letter,
    log_command_metric,
)
from keep_alive import (
    keep_alive,
    set_capstone_ticket_handler,
    set_capstone_status_handler,
    set_capstone_ready_checker,
    set_github_webhook_handler,
)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CapStoneFlowBot")

# Intents configuration
intents = discord.Intents.default()
intents.message_content = os.getenv("INTENTS_MESSAGE_CONTENT", "false").lower() == "true"
intents.members = os.getenv("INTENTS_MEMBERS", "false").lower() == "true"

# Exports and helper methods preserved for backward compatibility and test suites
from math_renderer import has_latex, render_equations_to_single_png
from database import async_has_role
from ai_client import NvidiaAIClient

try:
    ai_client = NvidiaAIClient()
except Exception:
    ai_client = None


class AssociateBot(commands.Bot):
    """Modular Discord bot for CapStoneFlow support tickets and codebase scanning."""

    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents,
            help_command=None
        )
        self.ai_client = ai_client

    async def setup_hook(self):
        """Loads all modular extensions from cogs/ directory."""
        # Every command is acknowledged immediately by its cog.  This handler
        # is the last-resort safety net for errors that escape a command body.
        self.tree.on_error = self.on_app_command_error

        # 1. Initialize Database Schema
        try:
            await asyncio.to_thread(init_db)
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Database initialization warning: {e}")

        # 2. Load Cogs
        cogs = [
            "cogs.tickets",
            "cogs.scanner",
            "cogs.leaderboard",
            "cogs.admin",
            "cogs.workflows"
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded Cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load Cog {cog}: {e}")

        # 3. Smart global command sync logic
        # Automatically sync when the command tree signature changes or when SYNC_COMMANDS=true.
        # Persisting the signature in settings avoids redundant syncs on restart (preventing 429 rate limits)
        # while ensuring newly added commands are always registered with Discord.
        cmd_specs = sorted(
            f"{c.name}:{c.description}:{sorted(getattr(c, '_params', {}).keys())}"
            for c in self.tree.get_commands()
        )
        current_sig = hashlib.sha256("|".join(cmd_specs).encode("utf-8")).hexdigest()[:16]
        bot_app_id = str(getattr(self, "application_id", None) or getattr(getattr(self, "user", None), "id", None) or "default")
        sig_key = f"synced_commands_signature:{bot_app_id}"
        stored_sig = None
        try:
            stored_sig = await asyncio.to_thread(get_setting, sig_key)
        except Exception:
            pass

        force_sync = os.getenv("SYNC_COMMANDS", "false").lower() in ("true", "1", "yes")
        sig_changed = bool(cmd_specs) and (stored_sig != current_sig)

        if force_sync or sig_changed:
            try:
                guild_id_raw = os.getenv("CAPSTONE_GUILD_ID", "").strip()
                if guild_id_raw:
                    try:
                        guild = discord.Object(id=int(guild_id_raw))
                        stale_commands = self.tree.get_commands(guild=guild)
                        self.tree.clear_commands(guild=guild)
                        await self.tree.sync(guild=guild)
                        logger.info(
                            "Removed %s guild-scoped command registrations from %s.",
                            len(stale_commands),
                            guild_id_raw,
                        )
                    except ValueError:
                        logger.warning("Ignoring invalid CAPSTONE_GUILD_ID=%r", guild_id_raw)

                synced = await self.tree.sync()
                logger.info(
                    "Synced %s global application slash commands for app %s (signature=%s).",
                    len(synced),
                    bot_app_id,
                    current_sig,
                )
                try:
                    await asyncio.to_thread(set_setting, sig_key, current_sig)
                except Exception:
                    pass
            except discord.HTTPException as e:
                if e.status == 429:
                    logger.warning("⚠️ Discord global rate limit (429) encountered during startup command sync. Startup will continue without re-syncing.")
                else:
                    logger.error(f"Failed to sync slash commands: {e}")
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")
        else:
            logger.info(
                "Slash commands already up-to-date (signature=%s, count=%s). Use /sync-commands or set SYNC_COMMANDS=true to force sync.",
                current_sig,
                len(cmd_specs),
            )

    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        """Record command execution telemetry asynchronously."""
        try:
            actor_id = getattr(getattr(interaction, "user", None), "id", None)
            actor_id_int = actor_id if isinstance(actor_id, int) else None
            await asyncio.to_thread(log_command_metric, command.name, actor_id_int, True, 0, None)
        except Exception:
            pass

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Log uncaught slash-command errors and always give the user feedback."""
        original = getattr(error, "original", error)
        logger.error(
            "Unhandled application command error: %s",
            original,
            exc_info=(type(original), original, getattr(original, "__traceback__", None)),
        )

        try:
            cmd_name = getattr(getattr(interaction, "command", None), "name", "unknown")
            actor_id = getattr(getattr(interaction, "user", None), "id", None)
            actor_id_int = actor_id if isinstance(actor_id, int) else None
            await asyncio.to_thread(log_command_metric, cmd_name, actor_id_int, False, 0, str(original)[:500])
        except Exception:
            pass

        if isinstance(original, discord.HTTPException) and original.status == 429:
            logger.warning("⚠️ Discord rate limit (429) active; skipping user response to prevent compounding rate limits.")
            return

        if isinstance(original, discord.Forbidden):
            message = "⚠️ The bot does not have permission to complete that command."
        elif isinstance(original, RuntimeError) and "Database" in str(original):
            message = "⚠️ The database is unavailable right now. Please try again shortly."
        else:
            message = "⚠️ The command failed, but the bot is still online. Please try again."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException as e:
            if e.status == 429:
                logger.warning("Could not send application command error response due to Discord 429 rate limit.")
            else:
                logger.exception("Could not send application command error response")

    async def on_ready(self):
        logger.info(f"🟢 Logged in as {self.user} (ID: {self.user.id})")
        expected_id = os.getenv("EXPECTED_DISCORD_BOT_ID", "").strip()
        if expected_id and str(self.user.id) != expected_id:
            logger.error("Bot account mismatch: expected %s, connected %s. Closing connection.", expected_id, self.user.id)
            await self.close()
            return
        logger.info("Bot is active and ready to manage tickets and scans.")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="CapStoneFlow Tickets • /claim"
            )
        )

    async def on_message(self, message: discord.Message):
        await on_message(message)


bot = AssociateBot()
_capstone_task_locks: dict[str, asyncio.Lock] = {}

WEBSITE_TO_DISCORD_STATUS = {
    "backlog": "OPEN",
    "todo": "OPEN",
    "in_progress": "CLAIMED",
    "peer_review": "PENDING-REVIEW",
    "adviser_review": "REVIEWED",
    "done": "CLOSED",
}


def _strip_leading_bracket_prefixes(title: str) -> str:
    """Strip any leading [STATUS], [PRIORITY], or [username] bracket tags from a thread title."""
    cleaned = (title or "").strip()
    while cleaned.startswith("[") and "]" in cleaned:
        cleaned = cleaned.split("]", 1)[1].strip()
    return cleaned or (title or "").strip()


def _integration_metadata(payload: dict) -> tuple[str, str]:
    metadata = payload.get("__integration") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        raise ValueError("Integration metadata is required")
    idempotency_key = str(metadata.get("idempotency_key") or "").strip()
    correlation_id = str(metadata.get("correlation_id") or "").strip()
    if not idempotency_key or not correlation_id:
        raise ValueError("Integration idempotency and correlation IDs are required")
    return idempotency_key, correlation_id


def _stored_delivery_response(delivery: dict) -> dict:
    response = delivery.get("response_json") or {
        "ok": False,
        "message": delivery.get("error_text") or "Integration request failed",
    }
    if not isinstance(response, dict):
        response = {"ok": False, "message": "Invalid stored integration response"}
    return {**response, "_http_status": int(delivery.get("response_status") or 500)}


def _begin_delivery(payload: dict, operation: str, task_id: str) -> tuple[dict, str, str]:
    idempotency_key, correlation_id = _integration_metadata(payload)
    delivery = begin_integration_delivery(
        idempotency_key,
        correlation_id,
        operation,
        task_id,
        {key: value for key, value in payload.items() if key != "__integration"},
    )
    if delivery.get("state") == "succeeded":
        return delivery, idempotency_key, correlation_id
    if not delivery.get("_claimed"):
        return delivery, idempotency_key, correlation_id
    return delivery, idempotency_key, correlation_id


def _mark_delivery_failed(payload: dict, status_code: int, message: str) -> None:
    try:
        idempotency_key, _ = _integration_metadata(payload)
        finish_integration_delivery(
            idempotency_key,
            response_status=status_code,
            response_payload={"ok": False, "message": message},
            error_text=message,
        )
    except Exception:
        logger.exception("Could not persist CapStoneFlow integration failure")

async def create_capstone_ticket(payload: dict) -> dict:
    """Create one Discord thread from a CapStoneFlow task."""
    task = payload.get("task") if isinstance(payload.get("task"), dict) else payload
    task_id = str(task.get("id") or "").strip()
    title = str(task.get("title") or "Untitled task").strip()
    if not task_id:
        raise ValueError("task.id is required")

    delivery, idempotency_key, _correlation_id = await asyncio.to_thread(
        _begin_delivery,
        payload,
        "ticket.create",
        task_id,
    )
    if delivery.get("state") == "succeeded":
        return _stored_delivery_response(delivery)
    if not delivery.get("_claimed"):
        return {
            "ok": False,
            "message": "The same ticket request is already being processed.",
            "_http_status": 409,
        }

    task_lock = _capstone_task_locks.setdefault(task_id, asyncio.Lock())
    async with task_lock:
        existing = await asyncio.to_thread(get_thread_by_external_task_id, task_id)
        if existing:
            guild_id = str(existing.get("guild_id") or os.getenv("CAPSTONE_GUILD_ID", "@me"))
            result = {"ok": True, "taskId": task_id, "threadId": str(existing["thread_id"]), "channelId": str(existing["channel_id"]), "channelUrl": f"https://discord.com/channels/{guild_id}/{existing['thread_id']}", "status": existing["status"], "reused": True}
            await asyncio.to_thread(
                finish_integration_delivery,
                idempotency_key,
                response_status=200,
                response_payload=result,
            )
            return {**result, "_http_status": 200}

        channel_id = int(os.getenv("CAPSTONE_TICKET_CHANNEL_ID", "0"))
        if not channel_id:
            raise ValueError("CAPSTONE_TICKET_CHANNEL_ID is not configured")
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise ValueError("CAPSTONE_TICKET_CHANNEL_ID must point to a text channel")
        configured_guild_id = os.getenv("CAPSTONE_GUILD_ID")
        actual_guild_id = str(getattr(getattr(channel, "guild", None), "id", ""))
        if configured_guild_id and actual_guild_id != configured_guild_id:
            raise ValueError("CAPSTONE_TICKET_CHANNEL_ID is not in CAPSTONE_GUILD_ID")

        folder = str(task.get("folder") or task.get("phase") or "capstoneflow")[:100]
        clean_title = _strip_leading_bracket_prefixes(title)
        thread = await channel.create_thread(name=f"[OPEN] {clean_title}"[:100], auto_archive_duration=1440, type=discord.ChannelType.public_thread)
        embed = discord.Embed(title=f"📋 Ticket: {clean_title}", description=str(task.get("problemStatement") or task.get("description") or "No problem description provided.")[:4000], color=0x38bdf8)
        for label, key in (("Priority", "priority"), ("Phase", "phase"), ("Folder", "folder")):
            if task.get(key):
                embed.add_field(name=label, value=f"`{str(task[key])[:1024]}`", inline=True)
        if task.get("acceptanceCriteria"):
            criteria = task["acceptanceCriteria"]
            criteria = criteria if isinstance(criteria, list) else [criteria]
            formatted_criteria = []
            for item in criteria:
                if isinstance(item, dict):
                    text = str(item.get("text") or item.get("title") or "").strip()
                    marker = "✅" if item.get("completed") else "•"
                else:
                    text = str(item).strip()
                    marker = "•"
                if text:
                    formatted_criteria.append(f"{marker} {text}")
            if formatted_criteria:
                embed.add_field(name="Acceptance Criteria", value="\n".join(formatted_criteria)[:1024], inline=False)
        embed.set_footer(text="CapStoneFlow • Use /claim in this thread to take ownership.")
        try:
            message = await thread.send(embed=embed)
            guild_id = getattr(getattr(channel, "guild", None), "id", None)
            await asyncio.to_thread(
                add_thread,
                thread.id,
                clean_title,
                folder,
                channel.id,
                "CapStoneFlow",
                task_id,
                int(guild_id) if guild_id else None,
            )
        except Exception as exc:
            # Discord side effects must not leave an untracked thread behind.
            try:
                await thread.delete(reason="CapStoneFlow integration record failed")
            except Exception:
                try:
                    await thread.edit(archived=True, locked=True, reason="CapStoneFlow integration record failed")
                except Exception:
                    logger.exception("Could not compensate orphan CapStoneFlow thread %s", thread.id)
            await asyncio.to_thread(
                finish_integration_delivery,
                idempotency_key,
                response_status=500,
                error_text=str(exc),
            )
            raise
        guild_id = getattr(getattr(channel, "guild", None), "id", "@me")
        result = {"ok": True, "taskId": task_id, "threadId": str(thread.id), "channelId": str(channel.id), "messageId": str(message.id), "guildId": str(guild_id), "channelUrl": f"https://discord.com/channels/{guild_id}/{thread.id}", "status": "OPEN", "reused": False}
        await asyncio.to_thread(
            finish_integration_delivery,
            idempotency_key,
            response_status=201,
            response_payload=result,
        )
        return {**result, "_http_status": 201}


async def sync_capstone_ticket_status(payload: dict) -> dict:
    """Apply a website state transition to the linked Discord thread."""
    task_id = str(payload.get("taskId") or "").strip()
    website_status = str(payload.get("status") or "").strip().lower()
    actor = str(payload.get("actor") or "CapStoneFlow").strip()[:100]
    if not task_id:
        raise ValueError("taskId is required")
    discord_status = WEBSITE_TO_DISCORD_STATUS.get(website_status)
    if not discord_status:
        raise ValueError("Unsupported website task status")

    delivery, idempotency_key, _correlation_id = await asyncio.to_thread(
        _begin_delivery,
        payload,
        "ticket.status",
        task_id,
    )
    if delivery.get("state") == "succeeded":
        return _stored_delivery_response(delivery)
    if not delivery.get("_claimed"):
        return {
            "ok": False,
            "message": "The same status request is already being processed.",
            "_http_status": 409,
        }

    thread_info = await asyncio.to_thread(get_thread_by_external_task_id, task_id)
    if not thread_info:
        result = {"ok": False, "message": "No Discord ticket is linked to this task."}
        await asyncio.to_thread(
            finish_integration_delivery,
            idempotency_key,
            response_status=404,
            response_payload=result,
            error_text=result["message"],
        )
        return {**result, "_http_status": 404}

    thread = bot.get_channel(int(thread_info["thread_id"]))
    if thread is None:
        thread = await bot.fetch_channel(int(thread_info["thread_id"]))
    if not isinstance(thread, discord.Thread):
        raise ValueError("The linked Discord channel is not a ticket thread")

    status_kwargs = {}
    if discord_status == "CLAIMED":
        status_kwargs["claimed_by_username"] = actor
    elif discord_status == "PENDING-REVIEW":
        status_kwargs["resolved_by_username"] = actor
    elif discord_status == "REVIEWED":
        status_kwargs["reviewed_by_username"] = actor
    elif discord_status == "CLOSED":
        status_kwargs["reviewed_by_username"] = actor

    # 1. Guarantee database state persistence and linked task sync first
    await asyncio.to_thread(update_thread_status, thread.id, discord_status, expected=thread_info, **status_kwargs)

    # 2. Safely perform Discord thread rename with archive-safe order and rate-limit queueing
    from services.thread_rename_sync import format_status_thread_name, safe_edit_thread_name

    raw_ticket_name = str(thread_info.get("ticket_name") or thread.name)
    target_name = format_status_thread_name(discord_status, raw_ticket_name, actor)
    reason = f"CapStoneFlow website status update by {actor}"
    rename_throttled = False

    embed = discord.Embed(
        title=f"🔄 Status Sync: [{discord_status}]",
        description=f"Ticket status was updated to **{discord_status}** (`{website_status}`) by **{actor}** via CapStoneFlow.",
        color=0x10b981 if discord_status in ("REVIEWED", "CLOSED") else (0xf59e0b if discord_status == "PENDING-REVIEW" else 0x3b82f6)
    )

    if discord_status == "CLOSED":
        if getattr(thread, "archived", False) is True or getattr(thread, "locked", False) is True:
            try:
                await asyncio.wait_for(thread.edit(archived=False, locked=False, reason=reason), timeout=2.5)
            except Exception as exc:
                logger.debug("Could not unarchive thread %s before close notification: %s", thread.id, exc)
        try:
            embed.set_footer(text="CapStoneFlow • Real-Time Synchronized")
            await thread.send(embed=embed)
        except Exception as exc:
            logger.debug("Could not post Discord in-thread close notification: %s", exc)
        renamed = await safe_edit_thread_name(thread, target_name, archived=True, locked=True, reason=reason)
        rename_throttled = not renamed
    else:
        edit_kwargs: dict = {"reason": reason}
        if getattr(thread, "archived", False) is True or getattr(thread, "locked", False) is True:
            edit_kwargs.update({"archived": False, "locked": False})
        renamed = await safe_edit_thread_name(thread, target_name, **edit_kwargs)
        rename_throttled = not renamed
        try:
            if rename_throttled:
                embed.set_footer(text="CapStoneFlow • Rename rate-limited; queued for automatic sync.")
            else:
                embed.set_footer(text="CapStoneFlow • Real-Time Synchronized")
            await thread.send(embed=embed)
        except Exception as exc:
            logger.debug("Could not post Discord in-thread notification: %s", exc)

    result = {
        "ok": True,
        "taskId": task_id,
        "threadId": str(thread.id),
        "status": website_status,
        "discordStatus": discord_status,
        "syncStatus": "synced",
        "renameThrottled": rename_throttled,
    }
    await asyncio.to_thread(
        finish_integration_delivery,
        idempotency_key,
        response_status=200,
        response_payload=result,
    )
    return {**result, "_http_status": 200}


def _strip_latex_equations(text: str) -> str:
    # Strip display $$...$$ equations
    cleaned = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    # Strip inline $...$ equations
    cleaned = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', '', cleaned, flags=re.DOTALL)
    return cleaned


def _format_math_content(text: str) -> str:
    return re.sub(r'\$\$(.*?)\$\$', r'```latex\n\1\n```', text, flags=re.DOTALL)


async def on_message(message: discord.Message):
    """Handle incoming messages (e.g. AI-Chat threads)."""
    bot_user = getattr(bot, "user", None)
    bot_user_id = getattr(bot_user, "id", None)
    if not message.author or (bot_user_id and message.author.id == bot_user_id):
        return

    if isinstance(message.channel, discord.Thread) and "AI-Chat" in message.channel.name:
        async with message.channel.typing():
            history = []
            async for item in message.channel.history(limit=20):
                role = "assistant" if (bot_user_id and item.author.id == bot_user_id) else "user"
                history.insert(0, {"role": role, "content": item.content})

            if ai_client:
                system_ctx = None
                try:
                    from pathlib import Path
                    from services.rust_bridge import build_repo_context_fast

                    latest_query = (message.content or "").strip()
                    if latest_query:
                        repo_root = str(Path(__file__).resolve().parent)
                        chunks = await asyncio.to_thread(build_repo_context_fast, repo_root, latest_query, 3, 1800)
                        if chunks:
                            context_blocks = [
                                f"--- {c['file']}:{c['start_line']}-{c['end_line']} ---\n{c['snippet']}"
                                for c in chunks
                            ]
                            system_ctx = (
                                "You are an expert AI engineering assistant. Use the retrieved workspace context below when relevant:\n\n"
                                + "\n\n".join(context_blocks)
                            )
                except Exception:
                    system_ctx = None

                if system_ctx:
                    reply = await asyncio.to_thread(ai_client.chat, history, system=system_ctx)
                else:
                    reply = await asyncio.to_thread(ai_client.chat, history)
                if has_latex() and "$$" in reply:
                    png_bytes = await asyncio.to_thread(render_equations_to_single_png, reply)
                    if png_bytes:
                        file = discord.File(io.BytesIO(png_bytes), filename="equation.png")
                        embed = discord.Embed(description=_strip_latex_equations(reply), color=0x38bdf8)
                        embed.set_image(url="attachment://equation.png")
                        await message.channel.send(embed=embed, file=file)
                        return
                await message.channel.send(reply)

    if hasattr(bot, 'process_commands') and callable(getattr(bot, 'process_commands')):
        res = bot.process_commands(message)
        if asyncio.iscoroutine(res):
            await res

def capstone_ticket_handler(payload: dict):
    if not bot.loop or bot.loop.is_closed():
        return 503, {"ok": False, "message": "Discord bot is not ready"}
    future = asyncio.run_coroutine_threadsafe(create_capstone_ticket(payload), bot.loop)
    try:
        result = future.result(timeout=20)
        status_code = int(result.pop("_http_status", 201 if not result.get("reused") else 200))
        return status_code, result
    except TimeoutError:
        _mark_delivery_failed(payload, 504, "Discord request timed out")
        return 504, {"ok": False, "message": "Discord request timed out"}
    except ValueError as exc:
        logger.warning("CapStoneFlow ticket validation failed: %s", exc)
        _mark_delivery_failed(payload, 400, str(exc))
        return 400, {"ok": False, "message": str(exc)}
    except RuntimeError as exc:
        logger.error("CapStoneFlow ticket dependency failed: %s", exc)
        _mark_delivery_failed(payload, 503, "Database or Discord dependency unavailable")
        return 503, {"ok": False, "message": "Database or Discord dependency unavailable"}
    except Exception as exc:
        logger.exception("CapStoneFlow ticket creation failed")
        _mark_delivery_failed(payload, 500, "Ticket creation failed")
        return 500, {"ok": False, "message": "Ticket creation failed"}


def capstone_status_handler(payload: dict):
    if not bot.loop or bot.loop.is_closed():
        return 503, {"ok": False, "message": "Discord bot is not ready"}
    future = asyncio.run_coroutine_threadsafe(sync_capstone_ticket_status(payload), bot.loop)
    try:
        result = future.result(timeout=20)
        status_code = int(result.pop("_http_status", 200))
        return status_code, result
    except TimeoutError:
        _mark_delivery_failed(payload, 504, "Discord request timed out")
        return 504, {"ok": False, "message": "Discord request timed out"}
    except ValueError as exc:
        logger.warning("CapStoneFlow status validation failed: %s", exc)
        _mark_delivery_failed(payload, 400, str(exc))
        return 400, {"ok": False, "message": str(exc)}
    except RuntimeError:
        logger.error("CapStoneFlow status dependency failed")
        _mark_delivery_failed(payload, 503, "Database or Discord dependency unavailable")
        return 503, {"ok": False, "message": "Database or Discord dependency unavailable"}
    except Exception:
        logger.exception("CapStoneFlow status update failed")
        _mark_delivery_failed(payload, 500, "Ticket status update failed")
        return 500, {"ok": False, "message": "Ticket status update failed"}


async def _fetch_channel_by_id(channel_id_str: str | None):
    text = str(channel_id_str or "").strip()
    if not text.isdigit():
        return None
    cid = int(text)
    channel = bot.get_channel(cid)
    if channel is None:
        try:
            channel = await bot.fetch_channel(cid)
        except Exception as exc:
            logger.debug("Could not fetch Discord channel %s: %s", cid, exc)
            return None
    return channel


async def _resolve_webhook_target_channel():
    """Resolve the destination channel for GitHub webhook updates."""
    from repo_updates import find_project_updates_channel

    channel = await _fetch_channel_by_id(await asyncio.to_thread(get_setting, "commit_channel_id"))
    if channel is not None:
        return channel

    try:
        scoped_rows = await asyncio.to_thread(get_setting_across_guilds, "commit_channel_id")
        for row in scoped_rows:
            channel = await _fetch_channel_by_id(row.get("value"))
            if channel is not None:
                return channel
    except Exception as exc:
        logger.debug("Could not query guild-scoped commit_channel_id: %s", exc)

    env_channel_id = os.getenv("PROJECT_UPDATES_CHANNEL_ID") or os.getenv("COMMIT_CHANNEL_ID")
    channel = await _fetch_channel_by_id(env_channel_id)
    if channel is not None:
        return channel

    for guild in getattr(bot, "guilds", None) or []:
        discovered = find_project_updates_channel(guild)
        if discovered is not None:
            try:
                await asyncio.to_thread(set_setting, "commit_channel_id", str(discovered.id), getattr(guild, "id", None))
            except Exception as exc:
                logger.debug("Could not persist auto-discovered commit channel %s: %s", discovered.id, exc)
            return discovered

    reminders_channel = await _fetch_channel_by_id(await asyncio.to_thread(get_setting, "reminders_channel_id"))
    if reminders_channel is not None:
        return reminders_channel

    for guild in getattr(bot, "guilds", None) or []:
        if getattr(guild, "system_channel", None):
            return guild.system_channel
        for ch in getattr(guild, "text_channels", None) or []:
            return ch
    return None


async def _is_auto_updates_enabled() -> bool:
    try:
        auto_enabled = await asyncio.to_thread(get_setting, "auto_updates_enabled")
        return str(auto_enabled or "").strip().lower() != "false"
    except Exception as exc:
        logger.debug("Could not check auto_updates_enabled setting: %s", exc)
        return True


async def _build_webhook_ticket_lookup(target_channel) -> dict[str, int | str]:
    from repo_updates import build_cap_ticket_lookup

    raw_guild_id = getattr(getattr(target_channel, "guild", None), "id", None)
    gid = int(raw_guild_id) if isinstance(raw_guild_id, int) else None
    try:
        grouped = await asyncio.to_thread(get_threads_by_status, gid)
        return build_cap_ticket_lookup(grouped, gid)
    except Exception as exc:
        logger.debug("Could not build CAP ticket lookup for webhook card: %s", exc)
        return {}


def _make_mark_event_posted():
    async def mark_event_posted(key: str, ch_id: int) -> bool:
        try:
            return await asyncio.to_thread(mark_repo_event_posted, key, ch_id)
        except Exception as exc:
            logger.debug("mark_repo_event_posted fallback to settings for %s: %s", key, exc)
            setting_key = f"event_posted:{ch_id}:{key}"
            val = await asyncio.to_thread(get_setting, setting_key)
            if val:
                return False
            await asyncio.to_thread(set_setting, setting_key, "1")
            return True

    return mark_event_posted


async def _process_github_push_payload(
    payload: dict,
    delivery_id: str | None = None,
    *,
    _requeue_on_error: bool = True,
) -> None:
    """Extract and post grouped GitHub commits arriving via webhook payload."""
    try:
        if payload.get("deleted") is True:
            return

        repo_data = payload.get("repository", {})
        repo_name = repo_data.get("name")
        owner_data = repo_data.get("owner", {})
        repo_owner = owner_data.get("login") or owner_data.get("name")
        ref = payload.get("ref", "")
        branch = ref.removeprefix("refs/heads/") if ref.startswith("refs/heads/") else (ref.split("/")[-1] if "/" in ref else "main")
        commits = payload.get("commits", [])

        if not repo_owner or not repo_name or not commits:
            return
        if not await _is_auto_updates_enabled():
            logger.info("Skipping GitHub webhook push for %s/%s because auto_updates_enabled is false.", repo_owner, repo_name)
            return

        target_channel = await _resolve_webhook_target_channel()
        if not target_channel:
            logger.warning("No channel found to post webhook commits to.")
            return

        ticket_lookup = await _build_webhook_ticket_lookup(target_channel)
        sender = payload.get("sender") or {}
        pusher = payload.get("pusher") or {}
        pusher_login = sender.get("login") or pusher.get("name")
        pusher_avatar = sender.get("avatar_url")

        from repo_updates import post_push_commits_from_payload
        posted = await post_push_commits_from_payload(
            target_channel=target_channel,
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            commits=commits,
            mark_event_posted=_make_mark_event_posted(),
            compare_url=payload.get("compare"),
            pusher_login=pusher_login,
            pusher_avatar=pusher_avatar,
            ticket_lookup=ticket_lookup,
        )
        logger.info("Posted %s webhook commit(s) to #%s", posted, getattr(target_channel, "name", "channel"))
    except Exception as exc:
        logger.exception("Error processing GitHub push payload: %s", exc)
        if not _requeue_on_error:
            raise
        try:
            await asyncio.to_thread(
                enqueue_webhook_dead_letter,
                delivery_id or f"push-{int(time.time())}",
                "push",
                payload if isinstance(payload, dict) else {},
                str(exc),
            )
        except Exception as dl_exc:
            logger.warning("Could not enqueue push webhook dead letter: %s", dl_exc)


async def _process_github_pull_request_payload(
    payload: dict,
    delivery_id: str | None = None,
    *,
    _requeue_on_error: bool = True,
) -> None:
    """Post a dedicated Pull Request card from a GitHub pull_request webhook payload."""
    try:
        action = str(payload.get("action") or "").lower()
        if action not in {"opened", "closed", "reopened", "ready_for_review"}:
            return
        repo_data = payload.get("repository") or {}
        repo_name = repo_data.get("name")
        owner_data = repo_data.get("owner") or {}
        repo_owner = owner_data.get("login") or owner_data.get("name")
        pr = payload.get("pull_request") or {}
        if not repo_owner or not repo_name or not pr:
            return
        if not await _is_auto_updates_enabled():
            return

        target_channel = await _resolve_webhook_target_channel()
        if not target_channel:
            logger.warning("No channel found to post pull_request webhook update to.")
            return

        ticket_lookup = await _build_webhook_ticket_lookup(target_channel)
        sender = payload.get("sender") or {}
        from repo_updates import post_pull_request_from_payload
        posted = await post_pull_request_from_payload(
            target_channel=target_channel,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr=pr,
            action=action,
            sender_login=sender.get("login"),
            sender_avatar=sender.get("avatar_url"),
            mark_event_posted=_make_mark_event_posted(),
            ticket_lookup=ticket_lookup,
        )
        if posted:
            logger.info("Posted pull_request #%s (%s) to #%s", pr.get("number"), action, getattr(target_channel, "name", "channel"))
    except Exception as exc:
        logger.exception("Error processing GitHub pull_request payload: %s", exc)
        if not _requeue_on_error:
            raise
        try:
            await asyncio.to_thread(
                enqueue_webhook_dead_letter,
                delivery_id or f"pr-{int(time.time())}",
                "pull_request",
                payload if isinstance(payload, dict) else {},
                str(exc),
            )
        except Exception as dl_exc:
            logger.warning("Could not enqueue pull_request webhook dead letter: %s", dl_exc)


async def _process_github_pr_review_payload(
    payload: dict,
    delivery_id: str | None = None,
    *,
    _requeue_on_error: bool = True,
) -> None:
    """Post a PR review feedback card from a GitHub pull_request_review webhook payload."""
    try:
        action = str(payload.get("action") or "").lower()
        if action not in {"submitted", "created"}:
            return
        repo_data = payload.get("repository") or {}
        repo_name = repo_data.get("name")
        owner_data = repo_data.get("owner") or {}
        repo_owner = owner_data.get("login") or owner_data.get("name")
        pr = payload.get("pull_request") or {}
        review = payload.get("review") or {}
        if not repo_owner or not repo_name or not pr or not review:
            return
        if not await _is_auto_updates_enabled():
            return

        target_channel = await _resolve_webhook_target_channel()
        if not target_channel:
            logger.warning("No channel found to post pull_request_review webhook update to.")
            return

        ticket_lookup = await _build_webhook_ticket_lookup(target_channel)
        from repo_updates import post_pr_review_from_payload
        posted = await post_pr_review_from_payload(
            target_channel=target_channel,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr=pr,
            review=review,
            mark_event_posted=_make_mark_event_posted(),
            ticket_lookup=ticket_lookup,
        )
        if posted:
            logger.info("Posted pull_request_review on PR #%s to #%s", pr.get("number"), getattr(target_channel, "name", "channel"))
    except Exception as exc:
        logger.exception("Error processing GitHub pull_request_review payload: %s", exc)
        if not _requeue_on_error:
            raise
        try:
            await asyncio.to_thread(
                enqueue_webhook_dead_letter,
                delivery_id or f"review-{int(time.time())}",
                "pull_request_review",
                payload if isinstance(payload, dict) else {},
                str(exc),
            )
        except Exception as dl_exc:
            logger.warning("Could not enqueue pull_request_review webhook dead letter: %s", dl_exc)


async def replay_dead_letter_event(event_type: str, payload: dict, delivery_id: str | None = None) -> None:
    """Replay a previously queued GitHub webhook payload from webhook_dead_letters."""
    if not isinstance(payload, dict):
        return
    if event_type == "push":
        await _process_github_push_payload(payload, delivery_id, _requeue_on_error=False)
    elif event_type == "pull_request":
        if "pull_request" in payload:
            await _process_github_pull_request_payload(payload, delivery_id, _requeue_on_error=False)
        elif "commits" in payload:
            await _process_github_push_payload(payload, delivery_id, _requeue_on_error=False)
    elif event_type == "pull_request_review":
        await _process_github_pr_review_payload(payload, delivery_id, _requeue_on_error=False)


def github_webhook_handler(raw_body: bytes, headers: dict) -> tuple[int, str]:
    """Verify and dispatch incoming GitHub webhook requests."""
    import json
    from webhook_security import verify_github_signature

    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    require_secret = os.getenv("WEBHOOK_REQUIRE_SECRET", "true").lower() == "true"
    sig_header = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")

    if not verify_github_signature(
        raw_body=raw_body,
        signature_header=sig_header,
        secret=secret,
        require_secret=require_secret,
    ):
        return 401, "Invalid webhook signature"

    event_type = headers.get("X-GitHub-Event") or headers.get("x-github-event") or "unknown"
    delivery_id = (headers.get("X-GitHub-Delivery") or headers.get("x-github-delivery") or "").strip()

    if delivery_id:
        try:
            is_first_delivery = register_webhook_delivery(delivery_id, event_type)
            if not is_first_delivery:
                return 200, "Duplicate webhook delivery ignored"
        except Exception as exc:
            logger.debug("Webhook replay receipt DB check skipped: %s", exc)

    if event_type == "ping":
        return 200, "pong"

    if event_type == "push":
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return 400, "Invalid JSON payload"

        if bot and getattr(bot, "loop", None) and not bot.loop.is_closed():
            asyncio.run_coroutine_threadsafe(_process_github_push_payload(payload, delivery_id or None), bot.loop)
            return 200, "Push event received and scheduled"
        try:
            enqueue_webhook_dead_letter(
                delivery_id or f"push-{int(time.time())}",
                "push",
                payload if isinstance(payload, dict) else {},
                "Discord bot event loop was not ready when webhook arrived",
            )
            return 202, "Push event queued in dead-letter table until bot is ready"
        except Exception:
            return 503, "Discord bot is not ready to process webhook"

    if event_type == "pull_request":
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return 400, "Invalid JSON payload"

        pr = payload.get("pull_request") or {}
        action = str(payload.get("action") or "").lower()
        if action in {"opened", "closed", "reopened", "ready_for_review"}:
            is_merged = action == "closed" and bool(pr.get("merged"))
            ok_msg = "Merged pull_request event received and scheduled" if is_merged else f"Pull request {action} event received and scheduled"
            dl_msg = "Merged pull_request event queued in dead-letter table until bot is ready" if is_merged else f"Pull request {action} event queued in dead-letter table until bot is ready"
            if bot and getattr(bot, "loop", None) and not bot.loop.is_closed():
                asyncio.run_coroutine_threadsafe(_process_github_pull_request_payload(payload, delivery_id or None), bot.loop)
                return 200, ok_msg
            try:
                enqueue_webhook_dead_letter(
                    delivery_id or f"pr-{int(time.time())}",
                    "pull_request",
                    payload,
                    "Discord bot event loop was not ready when webhook arrived",
                )
                return 202, dl_msg
            except Exception:
                return 503, "Discord bot is not ready to process webhook"

    if event_type == "pull_request_review":
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return 400, "Invalid JSON payload"

        action = str(payload.get("action") or "").lower()
        if action in {"submitted", "created"}:
            if bot and getattr(bot, "loop", None) and not bot.loop.is_closed():
                asyncio.run_coroutine_threadsafe(_process_github_pr_review_payload(payload, delivery_id or None), bot.loop)
                return 200, "Pull request review event received and scheduled"
            try:
                enqueue_webhook_dead_letter(
                    delivery_id or f"review-{int(time.time())}",
                    "pull_request_review",
                    payload,
                    "Discord bot event loop was not ready when webhook arrived",
                )
                return 202, "Pull request review event queued in dead-letter table until bot is ready"
            except Exception:
                return 503, "Discord bot is not ready to process webhook"

    return 200, f"Event {event_type} ignored"


def main():
    # 1. Start Keep-Alive web server immediately for Render health checks (/health)
    if os.getenv("KEEP_ALIVE_ENABLED", "true").lower() == "true" or os.getenv("RENDER") or os.getenv("PORT"):
        try:
            set_capstone_ticket_handler(capstone_ticket_handler)
            set_capstone_status_handler(capstone_status_handler)
            set_capstone_ready_checker(lambda: bot_is_ready(bot))
            set_github_webhook_handler(github_webhook_handler)
            keep_alive()
            logger.info("Keep-alive web server initialized.")
        except Exception as e:
            logger.warning(f"Keep-alive web server warning: {e}")

    # 2. Check for Discord Token
    if not DISCORD_TOKEN:
        logger.critical("⚠️ DISCORD_TOKEN is missing! Please configure DISCORD_TOKEN in Render Environment Variables.")
        # Keep web container alive so health check passes on Render
        while True:
            time.sleep(30)

    global bot
    retry_delay = 30
    while True:
        try:
            bot = AssociateBot()
            bot.run(DISCORD_TOKEN, reconnect=True)
            logger.warning("Discord bot stopped; retrying in %s seconds.", retry_delay)
        except Exception as e:
            logger.error("Error running Discord bot: %s", e)
            discord_status = getattr(e, "status", None)
            if discord_status == 429 or "1015" in str(e) or "429" in str(e):
                retry_delay = max(retry_delay, 900)
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 900)

if __name__ == "__main__":
    main()
