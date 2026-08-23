"""Tickets Cog for managing ticket lifecycle (/claim, /unclaim, /resolved, /unresolve, /reviewed, /unreview, /closed)."""
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from database import (
    get_thread, update_thread_status,
    increment_developer_resolved, increment_qa_reviewed,
    decrement_developer_resolved, decrement_qa_reviewed,
    get_user_roles
)

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

class TicketsCog(commands.Cog, name="Tickets"):
    """Handles ticket status workflow and assignment commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /claim
    @app_commands.command(name="claim", description="Claim an OPEN ticket (use inside a ticket thread) - Developer only")
    async def claim_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info:
                await interaction.followup.send("❌ This thread is not tracked in the database.")
                return

            if thread_info['status'] != 'OPEN':
                await interaction.followup.send(f"⚠️ Ticket cannot be claimed. Current status is **{thread_info['status']}**.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not (user_roles['is_developer'] or user_roles['is_pm']):
                await interaction.followup.send("❌ Only Developers or PMs can claim tickets.")
                return

            member = interaction.guild.get_member(interaction.user.id)
            username = member.display_name if member else interaction.user.name
            ticket_name = thread_info['ticket_name']
            new_name = f"[CLAIMED][{username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "CLAIMED",
                claimed_by_id=interaction.user.id,
                claimed_by_username=username,
            )

            embed = discord.Embed(
                title="🎯 Ticket Claimed",
                description=f"**{username}** has claimed this ticket.",
                color=0x10b981 # Emerald
            )
            embed.add_field(name="Old Status", value="`[OPEN]`", inline=True)
            embed.add_field(name="New Status", value=f"`[CLAIMED][{username}]`", inline=True)
            embed.set_footer(text="CapStoneFlow Discord Bot • Ticket Assigned")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /claim: {e}")
            await interaction.followup.send(f"❌ Error claiming ticket: {e}")

    # 2. /unclaim
    @app_commands.command(name="unclaim", description="Release a claimed ticket back to OPEN pool (use inside thread)")
    async def unclaim_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info:
                await interaction.followup.send("❌ This thread is not tracked in the database.")
                return

            if thread_info['status'] != 'CLAIMED':
                await interaction.followup.send(f"⚠️ Ticket is not in CLAIMED status (Current: **{thread_info['status']}**).")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if interaction.user.id != thread_info['claimed_by_id'] and not user_roles['is_pm']:
                await interaction.followup.send("❌ Only the developer who claimed this ticket or a PM can unclaim it.")
                return

            ticket_name = thread_info['ticket_name']
            new_name = f"[OPEN]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "OPEN",
                claimed_by_id=None,
                claimed_by_username=None,
            )

            embed = discord.Embed(
                title="Ticket Unclaimed",
                description=f"Ticket released back to open pool by {interaction.user.mention}.",
                color=discord.Color.orange()
            )
            embed.add_field(name="New Status", value="`[OPEN]`", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /unclaim: {e}")
            await interaction.followup.send(f"❌ Error unclaiming ticket: {e}")

    # 3. /resolved
    @app_commands.command(name="resolved", description="Submit ticket for QA review (use inside thread) - Developer only")
    @app_commands.describe(pr_url="Optional GitHub Pull Request or commit URL")
    async def resolve_ticket(self, interaction: discord.Interaction, pr_url: Optional[str] = None):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info:
                await interaction.followup.send("❌ This thread is not tracked in the database.")
                return

            if thread_info['status'] != 'CLAIMED':
                await interaction.followup.send(f"⚠️ Ticket must be CLAIMED before it can be resolved (Current: **{thread_info['status']}**).")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if interaction.user.id != thread_info['claimed_by_id'] and not user_roles['is_pm']:
                await interaction.followup.send("❌ Only the assigned developer or a PM can submit this ticket for review.")
                return

            member = interaction.guild.get_member(interaction.user.id)
            username = member.display_name if member else interaction.user.name
            ticket_name = thread_info['ticket_name']
            new_name = f"[Pending-Review][{username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "PENDING-REVIEW",
                resolved_by_id=interaction.user.id,
                resolved_by_username=username,
                pr_url=pr_url,
            )
            await asyncio.to_thread(increment_developer_resolved, interaction.user.id, username)

            embed = discord.Embed(
                title="🚀 Ticket Ready for Review",
                description=f"**{username}** submitted this ticket for QA verification.",
                color=0x3b82f6 # Blue
            )
            embed.add_field(name="Status", value=f"`[Pending-Review][{username}]`", inline=True)
            if pr_url:
                embed.add_field(name="PR / Commit Link", value=f"[View GitHub PR]({pr_url})", inline=False)
            embed.set_footer(text="CapStoneFlow • Developer Score +1")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /resolved: {e}")
            await interaction.followup.send(f"❌ Error resolving ticket: {e}")

    # 4. /unresolve
    @app_commands.command(name="unresolve", description="Revert ticket from Pending-Review back to CLAIMED (use inside thread)")
    async def unresolve_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info or thread_info['status'] != 'PENDING-REVIEW':
                await interaction.followup.send("⚠️ Ticket is not currently in PENDING-REVIEW status.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if interaction.user.id != thread_info['resolved_by_id'] and not user_roles['is_pm']:
                await interaction.followup.send("❌ Only the developer who resolved this ticket or a PM can unresolve it.")
                return

            dev_id = thread_info['resolved_by_id']
            dev_username = thread_info['resolved_by_username'] or interaction.user.name
            ticket_name = thread_info['ticket_name']
            new_name = f"[CLAIMED][{dev_username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "CLAIMED",
                resolved_by_id=None,
                resolved_by_username=None,
                pr_url=None,
            )
            if dev_id:
                await asyncio.to_thread(decrement_developer_resolved, dev_id)

            embed = discord.Embed(
                title="Ticket Unresolved",
                description=f"Ticket returned to CLAIMED state by {interaction.user.mention}.",
                color=discord.Color.orange()
            )
            embed.add_field(name="New Status", value=f"`[CLAIMED][{dev_username}]`", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /unresolve: {e}")
            await interaction.followup.send(f"❌ Error unresolving ticket: {e}")

    # 5. /reviewed
    @app_commands.command(name="reviewed", description="Mark ticket as Reviewed/Verified (use inside thread) - QA only")
    async def review_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info or thread_info['status'] != 'PENDING-REVIEW':
                await interaction.followup.send("⚠️ Ticket must be in PENDING-REVIEW before it can be reviewed.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if not (user_roles['is_qa'] or user_roles['is_pm']):
                await interaction.followup.send("❌ Only QA or Project Managers can review tickets.")
                return

            # Peer review enforcement: Developer cannot review their own ticket
            if interaction.user.id == thread_info['resolved_by_id'] and not user_roles['is_pm']:
                await interaction.followup.send("❌ You cannot review a ticket you resolved. Another QA member must verify it.")
                return

            member = interaction.guild.get_member(interaction.user.id)
            qa_username = member.display_name if member else interaction.user.name
            ticket_name = thread_info['ticket_name']
            new_name = f"[Reviewed][{qa_username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "REVIEWED",
                reviewed_by_id=interaction.user.id,
                reviewed_by_username=qa_username,
            )
            await asyncio.to_thread(increment_qa_reviewed, interaction.user.id, qa_username)

            embed = discord.Embed(
                title="✅ Ticket Verified & Reviewed",
                description=f"**{qa_username}** verified all acceptance criteria.",
                color=0x22c55e # Success green
            )
            embed.add_field(name="Status", value=f"`[Reviewed][{qa_username}]`", inline=True)
            embed.set_footer(text="CapStoneFlow • QA Score +1")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /reviewed: {e}")
            await interaction.followup.send(f"❌ Error reviewing ticket: {e}")

    # 6. /unreview
    @app_commands.command(name="unreview", description="Revert ticket from Reviewed back to Pending-Review (use inside thread)")
    async def unreview_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info or thread_info['status'] != 'REVIEWED':
                await interaction.followup.send("⚠️ Ticket is not currently in REVIEWED status.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            if interaction.user.id != thread_info['reviewed_by_id'] and not user_roles['is_pm']:
                await interaction.followup.send("❌ Only the QA who reviewed this ticket or a PM can unreview it.")
                return

            qa_id = thread_info['reviewed_by_id']
            dev_username = thread_info['resolved_by_username'] or 'Dev'
            ticket_name = thread_info['ticket_name']
            new_name = f"[Pending-Review][{dev_username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(
                update_thread_status,
                thread.id,
                "PENDING-REVIEW",
                reviewed_by_id=None,
                reviewed_by_username=None,
            )
            if qa_id:
                await asyncio.to_thread(decrement_qa_reviewed, qa_id)

            embed = discord.Embed(
                title="Ticket Unreviewed",
                description=f"Ticket reverted back to Pending-Review by {interaction.user.mention}.",
                color=discord.Color.orange()
            )
            embed.add_field(name="New Status", value=f"`[Pending-Review][{dev_username}]`", inline=True)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /unreview: {e}")
            await interaction.followup.send(f"❌ Error unreviewing ticket: {e}")

    # 7. /closed
    @app_commands.command(name="closed", description="Mark a ticket as CLOSED (use inside thread) - PM or involved team members")
    async def close_ticket(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send("❌ This command must be used inside a ticket thread.")
                return

            thread = interaction.channel
            thread_info = await asyncio.to_thread(get_thread, thread.id)
            if not thread_info:
                await interaction.followup.send("❌ This thread is not tracked in the database.")
                return

            if thread_info['status'] == 'CLOSED':
                await interaction.followup.send("⚠️ This ticket is already closed.")
                return

            user_roles = await asyncio.to_thread(get_user_roles, interaction.user.id)
            is_involved = (
                interaction.user.id == thread_info['claimed_by_id'] or
                interaction.user.id == thread_info['resolved_by_id'] or
                interaction.user.id == thread_info['reviewed_by_id']
            )

            if not (user_roles['is_pm'] or is_involved):
                await interaction.followup.send("❌ Only PMs or involved team members can close tickets.")
                return

            member = interaction.guild.get_member(interaction.user.id)
            username = member.display_name if member else interaction.user.name
            ticket_name = thread_info['ticket_name']
            new_name = f"[CLOSED][{username}]{ticket_name}"

            await thread.edit(name=new_name)
            await asyncio.to_thread(update_thread_status, thread.id, "CLOSED")

            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"Closed by {interaction.user.mention}.",
                color=discord.Color.red()
            )
            embed.add_field(name="Final Status", value=f"`[CLOSED][{username}]`", inline=True)
            embed.set_footer(text="CapStoneFlow • Sprint Milestone Achieved")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in /closed: {e}")
            await interaction.followup.send(f"❌ Error closing ticket: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
