"""Comprehensive test suite for TicketsCog and lifecycle commands."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from cogs.tickets import TicketsCog, _safe_edit_thread_name


class TestTicketsCog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.cog = TicketsCog(self.bot)

        # Mock interaction
        self.interaction = MagicMock(spec=discord.Interaction)
        self.interaction.response.is_done.return_value = False
        self.interaction.response.defer = AsyncMock()
        self.interaction.followup.send = AsyncMock()
        self.interaction.user = MagicMock(spec=discord.Member)
        self.interaction.user.id = 123456789
        self.interaction.user.name = "dev_user"
        self.interaction.user.display_name = "Dev User"
        self.interaction.user.mention = "<@123456789>"

        # Mock guild
        self.guild = MagicMock(spec=discord.Guild)
        self.guild.get_member.return_value = self.interaction.user
        self.interaction.guild = self.guild

        # Mock thread channel with isinstance pass
        self.thread = MagicMock()
        self.thread.__class__ = discord.Thread
        self.thread.id = 987654321
        self.thread.name = "[OPEN] Implement Auth Flow"
        self.thread.edit = AsyncMock()
        self.thread.send = AsyncMock()
        self.thread.parent = MagicMock()
        self.thread.parent.id = 111222333
        self.interaction.channel = self.thread
        self.interaction.channel_id = self.thread.id

    async def test_safe_edit_thread_name_success(self):
        """Verifies clean thread rename returns True."""
        success = await _safe_edit_thread_name(self.thread, "[CLAIMED] [dev_user] Implement Auth Flow")
        self.assertTrue(success)
        self.thread.edit.assert_awaited_once()

    async def test_safe_edit_thread_name_handles_429(self):
        """Verifies Discord 429 rate limit returns False without raising exception."""
        http_429 = discord.HTTPException(response=MagicMock(status=429), message="Rate limited")
        http_429.status = 429
        self.thread.edit.side_effect = http_429

        success = await _safe_edit_thread_name(self.thread, "[CLAIMED] [dev_user] Implement Auth Flow")
        self.assertFalse(success)

    async def test_safe_edit_thread_name_handles_503(self):
        """Verifies Discord 503 Service Unavailable returns False without raising exception."""
        http_503 = discord.HTTPException(response=MagicMock(status=503), message="Service Unavailable")
        http_503.status = 503
        self.thread.edit.side_effect = http_503

        success = await _safe_edit_thread_name(self.thread, "[CLAIMED] [dev_user] Implement Auth Flow")
        self.assertFalse(success)

    async def test_safe_edit_thread_name_noop_when_name_identical(self):
        """Verifies when target thread name matches existing name, no API call is made."""
        self.thread.name = "[OPEN] Implement Auth Flow"
        success = await _safe_edit_thread_name(self.thread, "[OPEN] Implement Auth Flow")
        self.assertTrue(success)
        self.thread.edit.assert_not_called()

    async def test_safe_edit_thread_name_unarchives_if_archived(self):
        """Verifies unarchiving is automatically added if thread was archived and no explicit archive requested."""
        self.thread.name = "[OPEN] Implement Auth Flow"
        self.thread.archived = True
        success = await _safe_edit_thread_name(self.thread, "[CLAIMED] [dev_user] Implement Auth Flow")
        self.assertTrue(success)
        self.thread.edit.assert_awaited_once_with(
            name="[CLAIMED] [dev_user] Implement Auth Flow",
            archived=False
        )

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    async def test_claim_ticket_success(self, mock_update, mock_roles, mock_get_thread):
        """Dev successfully claims an OPEN ticket."""
        mock_roles.return_value = {"is_developer": True, "is_qa": False, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "OPEN",
            "folder": "auth",
            "claimed_by_username": None,
        }

        await self.cog.claim_ticket.callback(self.cog, self.interaction)

        mock_update.assert_called_once_with(
            self.thread.id,
            "CLAIMED",
            claimed_by_id=self.interaction.user.id,
            claimed_by_username="Dev User",
        )
        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        self.assertIn("embed", kwargs)
        self.assertIn("Ticket Claimed", kwargs["embed"].title)

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    async def test_claim_ticket_non_dev_rejected(self, mock_update, mock_roles, mock_get_thread):
        """Non-developer cannot claim a ticket."""
        mock_roles.return_value = {"is_developer": False, "is_qa": True, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "OPEN",
            "folder": "auth",
        }

        await self.cog.claim_ticket.callback(self.cog, self.interaction)

        mock_update.assert_not_called()
        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        self.assertIn("Only Developers", args[0])

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    @patch("cogs.tickets.increment_developer_resolved")
    async def test_resolve_ticket_success(self, mock_record, mock_update, mock_roles, mock_get_thread):
        """Dev resolves ticket with PR url, moving to PENDING-REVIEW and incrementing stats."""
        mock_roles.return_value = {"is_developer": True, "is_qa": False, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "CLAIMED",
            "folder": "auth",
            "claimed_by_id": self.interaction.user.id,
            "claimed_by_username": "Dev User",
        }

        pr_url = "https://github.com/org/repo/pull/42"
        await self.cog.resolve_ticket.callback(self.cog, self.interaction, pr_url=pr_url)

        mock_update.assert_called_once_with(
            self.thread.id,
            "PENDING-REVIEW",
            resolved_by_id=self.interaction.user.id,
            resolved_by_username="Dev User",
            pr_url=pr_url,
        )
        mock_record.assert_called_once_with(self.interaction.user.id, "Dev User")
        self.interaction.followup.send.assert_awaited_once()

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    @patch("cogs.tickets.decrement_developer_resolved")
    async def test_unresolve_ticket_success(self, mock_decrement, mock_update, mock_roles, mock_get_thread):
        """Dev unresolves ticket back to CLAIMED, decrementing stats."""
        mock_roles.return_value = {"is_developer": True, "is_qa": False, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "PENDING-REVIEW",
            "folder": "auth",
            "resolved_by_id": self.interaction.user.id,
            "resolved_by_username": "Dev User",
            "claimed_by_id": self.interaction.user.id,
        }

        await self.cog.unresolve_ticket.callback(self.cog, self.interaction)

        mock_update.assert_called_once_with(
            self.thread.id,
            "CLAIMED",
            resolved_by_id=None,
            resolved_by_username=None,
            pr_url=None,
        )
        mock_decrement.assert_called_once_with(self.interaction.user.id)

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    @patch("cogs.tickets.increment_qa_reviewed")
    async def test_review_ticket_success(self, mock_record, mock_update, mock_roles, mock_get_thread):
        """QA reviews ticket from PENDING-REVIEW to REVIEWED and increments stats."""
        mock_roles.return_value = {"is_developer": False, "is_qa": True, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "PENDING-REVIEW",
            "folder": "auth",
            "resolved_by_id": 9999,
        }

        await self.cog.review_ticket.callback(self.cog, self.interaction)

        mock_update.assert_called_once_with(
            self.thread.id,
            "REVIEWED",
            reviewed_by_id=self.interaction.user.id,
            reviewed_by_username="Dev User",
        )
        mock_record.assert_called_once_with(self.interaction.user.id, "Dev User")

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    @patch("cogs.tickets.decrement_qa_reviewed")
    async def test_unreview_ticket_success(self, mock_decrement, mock_update, mock_roles, mock_get_thread):
        """QA unreviews ticket back to PENDING-REVIEW, decrementing stats."""
        mock_roles.return_value = {"is_developer": False, "is_qa": True, "is_pm": False}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "REVIEWED",
            "folder": "auth",
            "reviewed_by_id": self.interaction.user.id,
            "reviewed_by_username": "Dev User",
        }

        await self.cog.unreview_ticket.callback(self.cog, self.interaction)

        mock_update.assert_called_once_with(
            self.thread.id,
            "PENDING-REVIEW",
            reviewed_by_id=None,
            reviewed_by_username=None,
        )
        mock_decrement.assert_called_once_with(self.interaction.user.id)

    @patch("cogs.tickets.get_thread")
    @patch("cogs.tickets.get_user_roles")
    @patch("cogs.tickets.update_thread_status")
    async def test_close_ticket_success(self, mock_update, mock_roles, mock_get_thread):
        """PM closes reviewed ticket, archiving and locking thread."""
        mock_roles.return_value = {"is_developer": False, "is_qa": False, "is_pm": True}
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "REVIEWED",
            "folder": "auth",
            "claimed_by_id": 111,
            "reviewed_by_id": 222,
        }

        await self.cog.close_ticket.callback(self.cog, self.interaction)

        mock_update.assert_called_once_with(self.thread.id, "CLOSED")
        self.thread.edit.assert_awaited_once_with(
            name="[CLOSED] [Dev User] Implement Auth Flow", archived=True, locked=True
        )

    @patch("cogs.tickets.get_thread")
    async def test_ticket_info_embed_rendering(self, mock_get_thread):
        """Checks /ticket-info renders comprehensive metadata embed."""
        mock_get_thread.return_value = {
            "thread_id": self.thread.id,
            "ticket_name": "Implement Auth Flow",
            "status": "CLAIMED",
            "folder": "auth",
            "claimed_by_username": "coder_alice",
            "pr_url": "https://github.com/foo/bar/pull/1",
            "external_task_id": "TASK-99",
            "created_at": "2026-10-12 10:00:00",
        }

        await self.cog.ticket_info.callback(self.cog, self.interaction)

        self.interaction.followup.send.assert_awaited_once()
        args, kwargs = self.interaction.followup.send.call_args
        embed = kwargs["embed"]
        self.assertIn("Implement Auth Flow", embed.title)
        self.assertIn("CLAIMED", embed.description)


if __name__ == "__main__":
    unittest.main()
