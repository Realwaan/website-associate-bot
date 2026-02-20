"""Discord Bot for managing support tickets."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import DISCORD_TOKEN, TICKETS_DIR
from database import (
    init_db, add_thread, get_thread, update_thread_status,
    increment_resolved, get_leaderboard
)
from ticket_loader import load_tickets_from_folder, get_available_folders
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    """When the bot is ready, sync commands and initialize database."""
    logger.info(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")


@bot.tree.command(
    name="load-tickets",
    description="Load tickets from a folder into a Discord channel"
)
@app_commands.describe(
    folder="The folder name within tickets/ directory (e.g., support, bugs, features)",
    channel="The Discord channel where threads should be created"
)
async def load_tickets(interaction: discord.Interaction, folder: str, channel: discord.TextChannel):
    """Load tickets from a folder and create threads in the specified channel."""
    await interaction.response.defer()
    
    try:
        # Load tickets from folder
        tickets = load_tickets_from_folder(folder)
        
        if not tickets:
            await interaction.followup.send(f"❌ No markdown files found in `{folder}/` folder")
            return
        
        # Create threads for each ticket
        created_count = 0
        failed_count = 0
        
        for ticket in tickets:
            try:
                thread_name = f"[OPEN] {ticket['name']}"
                
                # Create thread in the specified channel
                thread = await channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread
                )
                
                # Add to database
                add_thread(
                    thread_id=thread.id,
                    ticket_name=ticket['name'],
                    folder=folder,
                    channel_id=channel.id,
                    created_by=str(interaction.user)
                )
                
                # Post initial message in thread
                embed = discord.Embed(
                    title=ticket['name'],
                    description=f"Folder: `{folder}`\nStatus: OPEN\nCreated by: {interaction.user.mention}",
                    color=discord.Color.blue()
                )
                await thread.send(embed=embed)
                
                created_count += 1
                logger.info(f"Created thread: {thread_name} (ID: {thread.id})")
                
            except Exception as e:
                logger.error(f"Failed to create thread for {ticket['name']}: {e}")
                failed_count += 1
        
        # Send summary
        summary = f"✅ Successfully created **{created_count}** thread(s)"
        if failed_count > 0:
            summary += f"\n⚠️ Failed to create **{failed_count}** thread(s)"
        
        embed = discord.Embed(
            title="Tickets Loaded",
            description=summary,
            color=discord.Color.green() if failed_count == 0 else discord.Color.orange()
        )
        embed.add_field(name="Folder", value=f"`{folder}`", inline=False)
        embed.add_field(name="Channel", value=channel.mention, inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except FileNotFoundError:
        await interaction.followup.send(
            f"❌ Folder `{folder}` not found in `{TICKETS_DIR}/` directory",
        )
    except Exception as e:
        logger.error(f"Error loading tickets: {e}")
        await interaction.followup.send(f"❌ Error loading tickets: {e}")


@bot.tree.command(
    name="claim",
    description="Claim a ticket by updating its status to CLAIMED"
)
@app_commands.describe(
    thread="The thread/ticket to claim"
)
async def claim_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Claim a ticket and update its status to CLAIMED."""
    await interaction.response.defer()
    
    try:
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'CLAIMED':
            await interaction.followup.send("⚠️ This ticket is already claimed")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        old_name = thread.name
        ticket_name = thread_info['ticket_name']
        new_name = f"[CLAIMED][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "CLAIMED")
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Claimed",
            description=f"Claimed by: {interaction.user.mention}",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Old Status", value="[OPEN]", inline=True)
        embed.add_field(name="New Status", value=f"[CLAIMED][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket claimed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error claiming ticket: {e}")
        await interaction.followup.send(f"❌ Error claiming ticket: {e}")


@bot.tree.command(
    name="resolved",
    description="Mark a ticket as RESOLVED and add to leaderboard"
)
@app_commands.describe(
    thread="The thread/ticket to mark as resolved"
)
async def resolve_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Mark a ticket as resolved and update leaderboard."""
    await interaction.response.defer()
    
    try:
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'RESOLVED':
            await interaction.followup.send("⚠️ This ticket is already resolved")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[RESOLVED][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "RESOLVED")
        
        # Update leaderboard
        increment_resolved(interaction.user.id, str(interaction.user))
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Resolved",
            description=f"Resolved by: {interaction.user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Old Status", value=thread_info['status'], inline=True)
        embed.add_field(name="New Status", value=f"[RESOLVED][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket resolved: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error resolving ticket: {e}")
        await interaction.followup.send(f"❌ Error resolving ticket: {e}")


@bot.tree.command(
    name="closed",
    description="Mark a ticket as CLOSED"
)
@app_commands.describe(
    thread="The thread/ticket to mark as closed"
)
async def close_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Mark a ticket as closed."""
    await interaction.response.defer()
    
    try:
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'CLOSED':
            await interaction.followup.send("⚠️ This ticket is already closed")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[CLOSED][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "CLOSED")
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Closed by: {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Old Status", value=thread_info['status'], inline=True)
        embed.add_field(name="New Status", value=f"[CLOSED][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket closed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        await interaction.followup.send(f"❌ Error closing ticket: {e}")


@bot.tree.command(
    name="leaderboard",
    description="Show the leaderboard of resolved tickets"
)
@app_commands.describe(
    limit="Number of top resolvers to show (default: 10, max: 50)"
)
async def show_leaderboard(interaction: discord.Interaction, limit: int = 10):
    """Display the leaderboard of users who have resolved the most tickets."""
    await interaction.response.defer()
    
    try:
        # Clamp limit between 1 and 50
        limit = max(1, min(limit, 50))
        
        leaderboard = get_leaderboard(limit)
        
        if not leaderboard:
            await interaction.followup.send("📊 No resolved tickets yet!")
            return
        
        # Build leaderboard description
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, entry in enumerate(leaderboard, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}️⃣"
            description += f"{medal} **{entry['username']}** - {entry['resolved_count']} resolved\n"
        
        embed = discord.Embed(
            title="🏆 Ticket Resolution Leaderboard",
            description=description,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Showing top {limit} resolvers")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Leaderboard shown to {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error showing leaderboard: {e}")
        await interaction.followup.send(f"❌ Error showing leaderboard: {e}")


@bot.tree.command(
    name="ticket-folders",
    description="List all available ticket folders"
)
async def list_folders(interaction: discord.Interaction):
    """List all available ticket folders."""
    await interaction.response.defer()
    
    try:
        folders = get_available_folders()
        
        if not folders:
            await interaction.followup.send(f"📁 No folders found in `{TICKETS_DIR}/` directory")
            return
        
        folder_list = "\n".join([f"• `{folder}`" for folder in folders])
        
        embed = discord.Embed(
            title="Available Ticket Folders",
            description=folder_list,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Total: {len(folders)} folder(s)")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        await interaction.followup.send(f"❌ Error listing folders: {e}")


def main():
    """Start the bot."""
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
