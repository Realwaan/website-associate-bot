"""CapStoneFlow Discord Associate Bot - Modernized Modular Entrypoint."""
import asyncio
import logging
import os
import io
import time
import discord
from discord.ext import commands
from config import DISCORD_TOKEN
from database import (
    init_db,
    add_thread,
    get_thread,
    get_thread_by_external_task_id,
    update_thread_status,
    begin_integration_delivery,
    finish_integration_delivery,
)
from keep_alive import (
    keep_alive,
    set_capstone_ticket_handler,
    set_capstone_status_handler,
    set_capstone_ready_checker,
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

class AssociateBot(commands.Bot):
    """Modular Discord bot for CapStoneFlow support tickets and codebase scanning."""

    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents,
            help_command=None
        )

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

        # 3. Global command sync logic
        # Discord heavily rate-limits global slash command syncing (200 syncs per day, plus Cloudflare 429 IP bans).
        # We only auto-sync if SYNC_COMMANDS is explicitly enabled.
        sync_enabled = os.getenv("SYNC_COMMANDS", "false").lower() in ("true", "1", "yes")
        if sync_enabled:
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
                logger.info("Synced %s global application slash commands.", len(synced))
            except discord.HTTPException as e:
                if e.status == 429:
                    logger.warning("⚠️ Discord global rate limit (429) encountered during startup command sync. Startup will continue without re-syncing.")
                else:
                    logger.error(f"Failed to sync slash commands: {e}")
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")
        else:
            logger.info("Skipping automatic slash command sync on startup to prevent Discord 429 rate limits. Use /sync-commands or set SYNC_COMMANDS=true to force sync.")

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Log uncaught slash-command errors and always give the user feedback."""
        original = getattr(error, "original", error)
        logger.error(
            "Unhandled application command error: %s",
            original,
            exc_info=(type(original), original, getattr(original, "__traceback__", None)),
        )

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
        logger.info("Bot is active and ready to manage tickets and scans.")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="CapStoneFlow Tickets • /claim"
            )
        )

    async def on_message(self, message: discord.Message):
        await on_message(message)

# Exports and helper methods preserved for backward compatibility and test suites
from math_renderer import has_latex, render_equations_to_single_png
from database import async_has_role
from ai_client import NvidiaAIClient

try:
    ai_client = NvidiaAIClient()
except Exception:
    ai_client = None

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
        thread = await channel.create_thread(name=f"[OPEN] {title}"[:100], auto_archive_duration=1440, type=discord.ChannelType.public_thread)
        embed = discord.Embed(title=f"📋 Ticket: {title}", description=str(task.get("problemStatement") or task.get("description") or "No problem description provided.")[:4000], color=0x38bdf8)
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
                title,
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
    await asyncio.to_thread(update_thread_status, thread.id, discord_status, **status_kwargs)

    # 2. Safely perform Discord thread rename with rate-limit resilience
    ticket_name = str(thread_info.get("ticket_name") or thread.name)
    if ticket_name.startswith("[") and "] " in ticket_name:
        ticket_name = ticket_name.split("] ", 1)[1]
    edit_kwargs = {
        "name": f"[{discord_status}] {ticket_name}"[:100],
        "reason": f"CapStoneFlow website status update by {actor}",
    }
    if discord_status == "CLOSED":
        edit_kwargs.update({"archived": True, "locked": True})
    else:
        edit_kwargs.update({"archived": False, "locked": False})

    rename_throttled = False
    try:
        await thread.edit(**edit_kwargs)
    except discord.HTTPException as exc:
        logger.warning(
            "Discord thread edit throttled or rejected for thread %s: %s (status: %s)",
            thread.id, exc, getattr(exc, "status", None)
        )
        rename_throttled = True
    except Exception as exc:
        logger.warning("Discord thread edit unexpected error for thread %s: %s", thread.id, exc)
        rename_throttled = True

    # 3. Post an in-thread notification embed for team awareness in Discord
    try:
        embed = discord.Embed(
            title=f"🔄 Status Sync: [{discord_status}]",
            description=f"Ticket status was updated to **{discord_status}** (`{website_status}`) by **{actor}** via CapStoneFlow.",
            color=0x10b981 if discord_status in ("REVIEWED", "CLOSED") else (0xf59e0b if discord_status == "PENDING-REVIEW" else 0x3b82f6)
        )
        if rename_throttled:
            embed.set_footer(text="CapStoneFlow • Thread rename throttled by Discord rate-limit; database state synchronized.")
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
    import re
    # Strip display $$...$$ equations
    cleaned = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    # Strip inline $...$ equations
    cleaned = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', '', cleaned, flags=re.DOTALL)
    return cleaned


def _format_math_content(text: str) -> str:
    import re
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




def main():
    # 1. Start Keep-Alive web server immediately for Render health checks (/health)
    if os.getenv("KEEP_ALIVE_ENABLED", "true").lower() == "true" or os.getenv("RENDER") or os.getenv("PORT"):
        try:
            set_capstone_ticket_handler(capstone_ticket_handler)
            set_capstone_status_handler(capstone_status_handler)
            set_capstone_ready_checker(lambda: bot.is_ready())
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
