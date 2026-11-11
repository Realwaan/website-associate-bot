import json
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from cogs.admin import AdminCog
from ticket_loader import load_tickets_from_folder


def setup_cog():
    bot = MagicMock()
    with patch.object(AdminCog, 'daily_summary_task'), patch.object(AdminCog, 'auto_updates_task'):
        cog = AdminCog(bot)
    interaction = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 123
    channel.threads = []
    interaction.channel = channel
    return cog, bot, interaction, channel


class TestTicketRefresh(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_edits_original_with_full_content_without_new_thread(self):
        cog, bot, interaction, channel = setup_cog()
        ticket = load_tickets_from_folder('otog-capstone')[0]
        thread = MagicMock(spec=discord.Thread)
        thread.parent_id = channel.id
        thread.archived = False
        bot.get_channel.return_value = thread
        original = MagicMock()
        original.author.id = bot.user.id
        original.embeds = [discord.Embed(title='Ticket: ' + ticket['title'])]
        original.edit = AsyncMock()

        async def history(**kwargs):
            yield original
        thread.history = history
        records = [{'channel_id': channel.id, 'thread_id': 55, 'ticket_filename': ticket['name'] + '.md'}]
        with patch('cogs.admin.get_user_roles', return_value={'is_pm': True}), \
             patch('cogs.admin.get_loaded_tickets', return_value=records), \
             patch('cogs.admin.update_thread_status') as update:
            await cog.refresh_tickets.callback(cog, interaction, 'otog-capstone')
        original.edit.assert_awaited_once()
        payload = original.edit.call_args.kwargs
        assert payload['attachments'][0].fp.getvalue().decode() == ticket['raw_content']
        embed_fields = {f.name: f.value for f in payload['embed'].fields}
        assert '📁 Related Files' in embed_fields
        channel.create_thread.assert_not_called()
        update.assert_not_called()

    async def test_refresh_skips_deleted_thread_and_unarchives_valid_thread(self):
        cog, bot, interaction, channel = setup_cog()
        tickets = load_tickets_from_folder('otog-capstone')
        t0, t1 = tickets[0], tickets[1]

        valid_thread = MagicMock(spec=discord.Thread)
        valid_thread.id = 66
        valid_thread.parent_id = channel.id
        valid_thread.archived = True
        valid_thread.edit = AsyncMock()

        def get_ch(tid):
            if tid == 66:
                return valid_thread
            return None

        bot.get_channel.side_effect = get_ch
        bot.fetch_channel = AsyncMock(side_effect=RuntimeError("404 Unknown Channel"))

        original = MagicMock()
        original.author.id = bot.user.id
        original.embeds = [discord.Embed(title='Ticket: ' + t1['title'])]
        original.edit = AsyncMock()

        async def history(**kwargs):
            yield original
        valid_thread.history = history

        records = [
            {'channel_id': channel.id, 'thread_id': 55, 'ticket_filename': t0['name'] + '.md'},
            {'channel_id': channel.id, 'thread_id': 66, 'ticket_filename': t1['name']},  # stem without .md (as stored by rebuild-db)
        ]
        with patch('cogs.admin.get_user_roles', return_value={'is_pm': True}), \
             patch('cogs.admin.get_loaded_tickets', return_value=records):
            await cog.refresh_tickets.callback(cog, interaction, 'otog-capstone')

        valid_thread.edit.assert_any_await(archived=False)
        valid_thread.edit.assert_any_await(archived=True)
        original.edit.assert_awaited_once()
        msg_sent = interaction.followup.send.call_args.args[0]
        assert "Updated 1 existing ticket messages" in msg_sent

    async def test_uncertain_import_does_not_create_duplicate(self):
        cog, bot, interaction, channel = setup_cog()
        ticket = load_tickets_from_folder('otog-capstone')[0]
        from pathlib import Path
        with patch('cogs.admin.get_user_roles', return_value={'is_pm': True}), \
             patch('cogs.admin.ticket_files', return_value=[Path(ticket['path'])]), \
             patch('cogs.admin.is_ticket_loaded', return_value=False), \
             patch('cogs.admin.reserve_ticket_import', return_value={'created': False, 'state': 'pending', 'thread_id': None}):
            await cog.load_tickets.callback(cog, interaction, 'otog-capstone')
        channel.create_thread.assert_not_called()
        assert any('uncertain' in str(call) for call in interaction.followup.send.call_args_list)

    async def test_merged_pull_request_webhook_schedules_update(self):
        import main as main_mod
        payload = {
            "action": "closed",
            "pull_request": {
                "number": 42,
                "title": "feat: add wallet transfer idempotency",
                "merged": True,
                "merge_commit_sha": "abc1234567890",
                "html_url": "https://github.com/Realwaan/OTOG/pull/42",
                "base": {"ref": "main"},
                "merged_by": {"login": "Realwaan"},
            },
            "repository": {
                "name": "OTOG",
                "owner": {"login": "Realwaan"},
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "deliv-pr-42",
        }
        dummy_bot = MagicMock()
        dummy_bot.loop = MagicMock()
        dummy_bot.loop.is_closed.return_value = False
        with patch.dict("os.environ", {"WEBHOOK_REQUIRE_SECRET": "false", "GITHUB_WEBHOOK_SECRET": ""}, clear=False), \
             patch.object(main_mod, "bot", dummy_bot), \
             patch("main.register_webhook_delivery", return_value=True), \
             patch("main.asyncio.run_coroutine_threadsafe") as mock_rcts:
            status, msg = main_mod.github_webhook_handler(raw_body, headers)
            assert status == 200
            assert "Merged pull_request" in msg
            mock_rcts.assert_called_once()
            coro = mock_rcts.call_args.args[0]
            coro.close()
