"""Leaderboard Cog for tracking Developer and QA contributions and sprint progress."""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import get_leaderboard_dev, get_leaderboard_qa, get_threads_by_status

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

class LeaderboardCog(commands.Cog, name="Leaderboard"):
    """Displays Developer and QA contribution scoreboards and sprint progress dashboards."""

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
                    "Live hackathon & sprint contributions"
                    if role == "both"
                    else ("Developer resolution scoreboard" if role == "dev" else "QA verification scoreboard")
                ),
                color=0x6366F1 # Indigo
            )

            # Developer section
            if dev_leaders:
                dev_text = ""
                for idx, row in enumerate(dev_leaders, 1):
                    medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
                    user_id = row['user_id']
                    count = row['dev_resolved_count']
                    username = row.get('username')
                    user_display = f"**{username}** (<@{user_id}>)" if username else f"<@{user_id}>"
                    dev_text += f"{medal} {user_display}: **{count}** resolved\n"
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
                    username = row.get('username')
                    user_display = f"**{username}** (<@{user_id}>)" if username else f"<@{user_id}>"
                    qa_text += f"{medal} {user_display}: **{count}** reviewed\n"
                embed.add_field(name="🛡️ Top QA Reviewers", value=qa_text, inline=False)
            else:
                embed.add_field(name="🛡️ Top QA Reviewers", value="*No reviewed tickets yet.*", inline=False)

            embed.set_footer(text=f"CapStoneFlow • Showing top {int(limit)} contributors")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /leaderboard: {e}")
            await interaction.followup.send(f"❌ Error fetching leaderboard: {e}")

    @app_commands.command(
        name="sprint-stats",
        description="View real-time hackathon sprint progress, burndown metrics, and completion rate",
    )
    async def sprint_stats(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            grouped_tickets = await asyncio.to_thread(get_threads_by_status)
            open_list = grouped_tickets.get("OPEN", [])
            claimed_list = grouped_tickets.get("CLAIMED", [])
            review_list = grouped_tickets.get("PENDING-REVIEW", [])
            verified_list = grouped_tickets.get("REVIEWED", [])
            closed_list = grouped_tickets.get("CLOSED", [])

            total = len(open_list) + len(claimed_list) + len(review_list) + len(verified_list) + len(closed_list)
            completed = len(verified_list) + len(closed_list)
            completion_rate = (completed / total * 100) if total > 0 else 0.0

            # Generate visual ASCII progress bar
            bar_length = 16
            filled_len = int(round(bar_length * (completion_rate / 100.0)))
            progress_bar = "█" * filled_len + "░" * (bar_length - filled_len)

            embed = discord.Embed(
                title="📊 Hackathon Sprint Progress Dashboard",
                description=f"**Sprint Velocity**: `[{progress_bar}]` **{completion_rate:.1f}% Completed**\nTotal Pipeline: **{total}** tickets tracked",
                color=0x10B981 if completion_rate >= 75 else (0xF59E0B if completion_rate >= 40 else 0x6366F1)
            )

            embed.add_field(name="🟢 Open Pool", value=f"`{len(open_list)}` unassigned", inline=True)
            embed.add_field(name="🟡 In Development", value=f"`{len(claimed_list)}` claimed", inline=True)
            embed.add_field(name="🔵 QA Verification", value=f"`{len(review_list)}` pending", inline=True)
            embed.add_field(name="🟣 QA Verified", value=f"`{len(verified_list)}` verified", inline=True)
            embed.add_field(name="🏁 Completed & Closed", value=f"`{len(closed_list)}` closed", inline=True)
            embed.add_field(name="🎯 Finished Total", value=f"`{completed}` of `{total}`", inline=True)

            # Collect active folders
            folders = set()
            for status_tickets in grouped_tickets.values():
                for t in status_tickets:
                    if t.get("folder"):
                        folders.add(t["folder"])
            if folders:
                folders_display = ", ".join(f"`{f}`" for f in sorted(folders)[:6])
                embed.add_field(name="📂 Active Modules / Folders", value=folders_display, inline=False)

            embed.set_footer(text="CapStoneFlow • Live Hackathon Burndown")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /sprint-stats: {e}")
            await interaction.followup.send(f"❌ Error fetching sprint stats: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
