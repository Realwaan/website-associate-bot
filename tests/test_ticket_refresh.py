from unittest.mock import MagicMock, AsyncMock, patch
import discord
import pytest
from cogs.admin import AdminCog
from ticket_loader import load_tickets_from_folder


def setup_cog():
    bot = MagicMock()
    with patch.object(AdminCog, 'daily_summary_task'):
        cog = AdminCog(bot)
    interaction = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 123
    interaction.channel = channel
    return cog, bot, interaction, channel


@pytest.mark.asyncio
async def test_refresh_edits_original_with_full_content_without_new_thread():
    cog, bot, interaction, channel = setup_cog()
    ticket = load_tickets_from_folder('otog-capstone')[0]
    thread = MagicMock(spec=discord.Thread)
    thread.parent_id = channel.id
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
    channel.create_thread.assert_not_called()
    update.assert_not_called()


@pytest.mark.asyncio
async def test_uncertain_import_does_not_create_duplicate():
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
