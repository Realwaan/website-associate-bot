"""Unit tests for LeaderboardCog (/leaderboard and /sprint-stats)."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from cogs.leaderboard import LeaderboardCog


class TestLeaderboardCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.cog = LeaderboardCog(self.bot)

        self.interaction = MagicMock(spec=discord.Interaction)
        self.interaction.response.is_done.return_value = False
        self.interaction.response.defer = AsyncMock()
        self.interaction.followup.send = AsyncMock()

    @patch("cogs.leaderboard.get_leaderboard_dev")
    @patch("cogs.leaderboard.get_leaderboard_qa")
    async def test_show_leaderboard_both_teams(self, mock_qa, mock_dev):
        """Tests /leaderboard both shows Dev and QA tables with medals and counts."""
        mock_dev.return_value = [
            {"user_id": 101, "username": "alice", "dev_resolved_count": 8},
            {"user_id": 102, "username": "bob", "dev_resolved_count": 5},
        ]
        mock_qa.return_value = [
            {"user_id": 201, "username": "charlie", "qa_reviewed_count": 7},
        ]

        await self.cog.show_leaderboard.callback(self.cog, self.interaction, role="both", limit=10)

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("Leaderboard", embed.title)
        field_names = [f.name for f in embed.fields]
        self.assertIn("💻 Top Developers", field_names)
        self.assertIn("🛡️ Top QA Reviewers", field_names)

        # Alice should have gold medal
        dev_field = next(f for f in embed.fields if f.name == "💻 Top Developers")
        self.assertIn("🥇", dev_field.value)
        self.assertIn("alice", dev_field.value)
        self.assertIn("**8** resolved", dev_field.value)

    @patch("cogs.leaderboard.get_threads_by_status")
    async def test_sprint_stats_calculation(self, mock_get_threads):
        """Tests /sprint-stats progress bar and completion rate calculation."""
        mock_get_threads.return_value = {
            "OPEN": [{"thread_id": 1, "folder": "backend"}],
            "CLAIMED": [{"thread_id": 2, "folder": "backend"}],
            "PENDING-REVIEW": [{"thread_id": 3, "folder": "frontend"}],
            "REVIEWED": [{"thread_id": 4, "folder": "frontend"}],
            "CLOSED": [{"thread_id": 5, "folder": "frontend"}],
        }

        await self.cog.sprint_stats.callback(self.cog, self.interaction)

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("Sprint Progress Dashboard", embed.title)
        # Total = 5, Completed = 2 (REVIEWED + CLOSED), Rate = 40.0%
        self.assertIn("40.0% Completed", embed.description)
        self.assertIn("█", embed.description)  # Progress bar fill
        self.assertIn("Total Pipeline: **5** tickets tracked", embed.description)


if __name__ == "__main__":
    unittest.main()
