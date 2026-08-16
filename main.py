"""CapStoneFlow Discord Associate Bot - Modernized Modular Entrypoint."""
import asyncio
import logging
import os
import io
import discord
from discord.ext import commands
from config import DISCORD_TOKEN
from database import init_db, verify_database_connection
from keep_alive import keep_alive

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CapStoneFlowBot")

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
            "cogs.admin"
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
    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is missing! Add it to your .env file.")
        return

    # Start Keep-Alive web server for 24/7 cloud deployments (Render, Railway, Fly.io, or UptimeRobot)
    if os.getenv("KEEP_ALIVE_ENABLED", "true").lower() == "true" or os.getenv("RENDER") or os.getenv("PORT"):
        keep_alive()

    bot = AssociateBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
