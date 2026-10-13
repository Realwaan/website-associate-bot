"""Unit tests for AdminCog (roles, reset-loaded, commit channels, health, AI status)."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from cogs.admin import AdminCog


class TestAdminCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        with patch.object(AdminCog, "daily_summary_task"):
            self.cog = AdminCog(self.bot)

        self.interaction = MagicMock(spec=discord.Interaction)
        self.interaction.response.is_done.return_value = False
        self.interaction.response.defer = AsyncMock()
        self.interaction.followup.send = AsyncMock()

        self.user = MagicMock(spec=discord.Member)
        self.user.id = 1001
        self.user.name = "admin_user"
        self.user.display_name = "Admin User"
        self.user.roles = []
        self.user.guild_permissions = MagicMock()
        self.user.guild_permissions.administrator = True
        self.user.guild_permissions.manage_guild = True
        self.user.guild_permissions.manage_channels = True
        self.user.guild_permissions.manage_roles = True

        self.guild = MagicMock(spec=discord.Guild)
        self.guild.me = MagicMock()
        self.guild.me.guild_permissions = MagicMock()
        self.guild.me.guild_permissions.manage_roles = True
        self.guild.me.top_role = MagicMock()
        self.guild.roles = []

        self.interaction.user = self.user
        self.interaction.guild = self.guild

    def tearDown(self):
        pass

    @patch("cogs.admin.set_user_role")
    async def test_assign_role_dev(self, mock_set_role):
        """User self-assigns Developer role successfully."""
        mock_role = MagicMock()
        mock_role.name = "Developer"
        self.guild.roles.append(mock_role)

        await self.cog.assign_role.callback(self.cog, self.interaction, role="dev")

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        self.assertIn("Developer", args[0])
        mock_set_role.assert_called_once_with(
            self.user.id, self.user.name, is_developer=True, is_qa=False, is_pm=False
        )

    @patch("cogs.admin.set_user_role")
    async def test_assign_role_pm_denied_non_admin(self, mock_set_role):
        """Non-admin / non-manager cannot self-assign PM role."""
        self.user.guild_permissions.administrator = False
        self.user.guild_permissions.manage_guild = False
        self.user.guild_permissions.manage_channels = False

        await self.cog.assign_role.callback(self.cog, self.interaction, role="pm")

        mock_set_role.assert_not_called()
        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        self.assertIn("requires Administrator, Manage Server, or Manage Channels", args[0])

    @patch("cogs.admin.get_user_roles")
    @patch("cogs.admin.clear_loaded_tickets")
    async def test_reset_loaded_alias(self, mock_clear, mock_get_roles):
        """PM calls /reset-loaded alias to clear folder ticket cache."""
        mock_get_roles.return_value = {"is_pm": True}
        mock_clear.return_value = 5

        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 555
        channel.mention = "<#555>"

        await self.cog.reset_loaded.callback(self.cog, self.interaction, folder="auth", channel=channel)

        mock_clear.assert_called_once_with("auth", 555)
        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("Folder Import Cache Cleared", embed.title)
        self.assertIn("Cleared **5** ticket import markers", embed.description)

    @patch("cogs.admin.get_user_roles")
    @patch("cogs.admin.set_setting")
    async def test_set_commit_channel(self, mock_set_setting, mock_get_roles):
        """PM configures default repository commit channel."""
        mock_get_roles.return_value = {"is_pm": True}
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 777
        channel.mention = "<#777>"

        await self.cog.set_commit_channel.callback(self.cog, self.interaction, channel=channel)

        mock_set_setting.assert_called_once_with("commit_channel_id", "777")
        self.interaction.followup.send.assert_awaited_once()

    @patch("cogs.admin.get_user_roles")
    @patch("cogs.admin.set_setting")
    async def test_auto_updates_enable(self, mock_set_setting, mock_get_roles):
        """PM enables auto updates."""
        mock_get_roles.return_value = {"is_pm": True}

        await self.cog.auto_updates.callback(
            self.cog,
            self.interaction,
            action="enable",
            repo_url="owner/repo",
            branch="main",
            feed_type="both",
        )

        mock_set_setting.assert_any_call("auto_updates_enabled", "true")
        mock_set_setting.assert_any_call("auto_updates_repo", "owner/repo")
        self.interaction.followup.send.assert_awaited_once()

    @patch("cogs.admin.get_setting")
    @patch("database.get_db")
    async def test_health_details(self, mock_get_db, mock_get_setting):
        """Verifies /health-details embed reports DB and Discord status."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_get_setting.return_value = "true"

        self.cog.bot.latency = 0.042

        await self.cog.health_details.callback(self.cog, self.interaction)

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("Health & Diagnostics", embed.title)
        field_names = [f.name for f in embed.fields]
        self.assertIn("🗄️ Database (PostgreSQL)", field_names)
        self.assertIn("⚡ Discord Gateway", field_names)

    @patch("cogs.admin.get_user_roles")
    async def test_ai_status(self, mock_get_roles):
        """PM inspects AI status embed."""
        mock_get_roles.return_value = {"is_pm": True}

        await self.cog.ai_status.callback(self.cog, self.interaction)

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("AI Engine Status", embed.title)


if __name__ == "__main__":
    unittest.main()
