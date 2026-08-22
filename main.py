"""CapStoneFlow Discord Associate Bot - Modernized Modular Entrypoint."""
import asyncio
import logging
import os
import io
import discord
from discord.ext import commands
from config import DISCORD_TOKEN
from database import init_db, verify_database_connection, add_thread, get_thread_by_external_task_id
from keep_alive import keep_alive, set_capstone_ticket_handler

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
        # 1. Initialize Database Schema
        try:
            init_db()
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

        # 3. Sync Slash Application Commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application slash commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    async def on_ready(self):
        logger.info(f"🟢 Logged in as {self.user} (ID: {self.user.id})")
        logger.info("Bot is active and ready to manage tickets and scans.")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="CapStoneFlow Tickets • /claim"
            )
        )

# Exports and helper methods preserved for backward compatibility and test suites
from math_renderer import has_latex, render_equations_to_single_png
from database import async_has_role
from ai_client import NvidiaAIClient

try:
    ai_client = NvidiaAIClient()
except Exception:
    ai_client = None

bot = AssociateBot()

async def create_capstone_ticket(payload: dict) -> dict:
    """Create one Discord thread from a CapStoneFlow task."""
    task = payload.get("task") if isinstance(payload.get("task"), dict) else payload
    task_id = str(task.get("id") or "").strip()
    title = str(task.get("title") or "Untitled task").strip()
    if not task_id:
        raise ValueError("task.id is required")

    existing = await asyncio.to_thread(get_thread_by_external_task_id, task_id)
    if existing:
        return {"taskId": task_id, "threadId": str(existing["thread_id"]), "channelId": str(existing["channel_id"]), "channelUrl": f"https://discord.com/channels/{payload.get('guildId', '@me')}/{existing['thread_id']}", "status": existing["status"], "reused": True}

    channel_id = int(task.get("discordChannelId") or os.getenv("CAPSTONE_TICKET_CHANNEL_ID", "0"))
    if not channel_id:
        raise ValueError("CAPSTONE_TICKET_CHANNEL_ID is not configured")
    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    if not hasattr(channel, "create_thread"):
        raise ValueError("CAPSTONE_TICKET_CHANNEL_ID must point to a text channel")

    folder = str(task.get("folder") or task.get("phase") or "capstoneflow")[:100]
    thread = await channel.create_thread(name=f"[OPEN] {title}"[:100], auto_archive_duration=1440, type=discord.ChannelType.public_thread)
    embed = discord.Embed(title=f"📋 Ticket: {title}", description=str(task.get("problemStatement") or task.get("description") or "No problem description provided.")[:4000], color=0x38bdf8)
    for label, key in (("Priority", "priority"), ("Phase", "phase"), ("Folder", "folder")):
        if task.get(key):
            embed.add_field(name=label, value=f"`{str(task[key])[:1024]}`", inline=True)
    if task.get("acceptanceCriteria"):
        criteria = task["acceptanceCriteria"]
        criteria = criteria if isinstance(criteria, list) else [criteria]
        embed.add_field(name="Acceptance Criteria", value="\n".join(f"• {str(item)}" for item in criteria)[:1024], inline=False)
    embed.set_footer(text="CapStoneFlow • Use /claim in this thread to take ownership.")
    message = await thread.send(embed=embed)
    await asyncio.to_thread(add_thread, thread.id, title, folder, channel.id, "CapStoneFlow", task_id)
    guild_id = getattr(getattr(channel, "guild", None), "id", "@me")
    return {"taskId": task_id, "threadId": str(thread.id), "channelId": str(channel.id), "messageId": str(message.id), "guildId": str(guild_id), "channelUrl": f"https://discord.com/channels/{guild_id}/{thread.id}", "status": "OPEN", "reused": False}

def capstone_ticket_handler(payload: dict):
    if not bot.loop or bot.loop.is_closed():
        return 503, {"ok": False, "message": "Discord bot is not ready"}
    future = asyncio.run_coroutine_threadsafe(create_capstone_ticket(payload), bot.loop)
    try:
        return 201, {"ok": True, **future.result(timeout=20)}
    except TimeoutError:
        return 504, {"ok": False, "message": "Discord request timed out"}
    except Exception as exc:
        logger.error("CapStoneFlow ticket creation failed: %s", exc)
        return 400, {"ok": False, "message": str(exc)}

def _strip_latex_equations(text: str) -> str:
    import re
    cleaned = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'\$.*?\$', '', cleaned)
    return cleaned

def _format_math_content(text: str) -> str:
    import re
    return re.sub(r'\$\$(.*?)\$\$', r'```latex\n\1\n```', text, flags=re.DOTALL)

async def on_message(message: discord.Message):
    if not message.author or getattr(message.author, "id", None) == getattr(getattr(bot, "user", None), "id", None):
        return

    # Check if inside an AI-Chat thread
    if isinstance(message.channel, discord.Thread) and "AI-Chat" in message.channel.name:
        async with message.channel.typing():
            history = []
            async for m in message.channel.history(limit=20):
                role = "assistant" if m.author.id == bot.user.id else "user"
                history.insert(0, {"role": role, "content": m.content})

            if ai_client:
                reply = ai_client.chat(history)
                if has_latex() and "$$" in reply:
                    png_bytes = render_equations_to_single_png(reply)
                    if png_bytes:
                        file = discord.File(io.BytesIO(png_bytes), filename="equation.png")
                        embed = discord.Embed(description=_strip_latex_equations(reply), color=0x38bdf8)
                        embed.set_image(url="attachment://equation.png")
                        await message.channel.send(embed=embed, file=file)
                        return
                await message.channel.send(reply)




def main():
    # 1. Start Keep-Alive web server immediately for Render health checks (/health)
    if os.getenv("KEEP_ALIVE_ENABLED", "true").lower() == "true" or os.getenv("RENDER") or os.getenv("PORT"):
        try:
            set_capstone_ticket_handler(capstone_ticket_handler)
            keep_alive()
            logger.info("Keep-alive web server initialized.")
        except Exception as e:
            logger.warning(f"Keep-alive web server warning: {e}")

    # 2. Check for Discord Token
    if not DISCORD_TOKEN:
        logger.critical("⚠️ DISCORD_TOKEN is missing! Please configure DISCORD_TOKEN in Render Environment Variables.")
        # Keep web container alive so health check passes on Render
        import time
        while True:
            time.sleep(30)

    try:
        global bot
        bot = AssociateBot()
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error running Discord bot: {e}")
        import time
        while True:
            time.sleep(30)

if __name__ == "__main__":
    main()
