"""Leaderboard Cog for tracking Developer and QA contributions."""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import get_leaderboard_dev, get_leaderboard_qa

logger = logging.getLogger(__name__)

async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)

class LeaderboardCog(commands.Cog, name="Leaderboard"):
    """Displays Developer and QA contribution scoreboards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View Developer and QA contribution leaderboards")
    @app_commands.describe(
        role="Show both teams or filter to Developers/QA",
        limit="Number of entries to show (1-50; default 10)",
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="Both teams", value="both"),
        app_commands.Choice(name="Developers", value="dev"),
        app_commands.Choice(name="QA reviewers", value="qa"),
    ])
    async def show_leaderboard(
        self,
        interaction: discord.Interaction,
        role: str = "both",
        limit: app_commands.Range[int, 1, 50] = 10,
    ):
        await safe_defer(interaction)
        try:
            role = role.lower()
            dev_leaders = []
            qa_leaders = []
            if role in {"both", "dev"}:
                dev_leaders = await asyncio.to_thread(get_leaderboard_dev, int(limit))
            if role in {"both", "qa"}:
                qa_leaders = await asyncio.to_thread(get_leaderboard_qa, int(limit))

            embed = discord.Embed(
                title="🏆 CapStoneFlow Leaderboard",
                description=(
                    "Live sprint metrics for both teams"
                    if role == "both"
                    else ("Developer resolution leaderboard" if role == "dev" else "QA review leaderboard")
                ),
                color=0x6366f1 # Indigo
            )

            # Developer section
            if dev_leaders:
                dev_text = ""
                for idx, row in enumerate(dev_leaders, 1):
                    medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
                    user_id = row['user_id']
                    count = row['dev_resolved_count']
                    dev_text += f"{medal} <@{user_id}>: **{count}** resolved\n"
                embed.add_field(name="💻 Top Developers", value=dev_text, inline=False)
            else:
                embed.add_field(name="💻 Top Developers", value="*No resolved tickets yet.*", inline=False)

            # QA section
            if qa_leaders:
                qa_text = ""
                for idx, row in enumerate(qa_leaders, 1):
                    medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
                    user_id = row['user_id']
                    count = row['qa_reviewed_count']
                    qa_text += f"{medal} <@{user_id}>: **{count}** reviewed\n"
                embed.add_field(name="🛡️ Top QA Reviewers", value=qa_text, inline=False)
            else:
                embed.add_field(name="🛡️ Top QA Reviewers", value="*No reviewed tickets yet.*", inline=False)

            embed.set_footer(text=f"CapStoneFlow • Showing up to {int(limit)} entries")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /leaderboard: {e}")
            await interaction.followup.send(f"❌ Error fetching leaderboard: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
