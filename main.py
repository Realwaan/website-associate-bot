"""Discord Bot for managing support tickets."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import DISCORD_TOKEN, TICKETS_DIR
from database import (
    init_db, add_thread, get_thread, update_thread_status,
    increment_developer_resolved, increment_qa_reviewed, 
    get_leaderboard_dev, get_leaderboard_qa,
    set_user_role, get_user_roles, has_role
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
    name="set-role",
    description="Set user roles (Developer or QA or both)"
)
@app_commands.describe(
    user="The user to assign a role to",
    developer="Check if user is a Developer",
    qa="Check if user is a QA"
)
async def set_role(interaction: discord.Interaction, user: discord.User, developer: bool = False, qa: bool = False):
    """Set user roles. User can have both Developer and QA roles."""
    await interaction.response.defer()
    
    try:
        if not developer and not qa:
            await interaction.followup.send("❌ User must have at least one role (Developer or QA)")
            return
        
        # Set user role in database
        set_user_role(user.id, str(user), is_developer=developer, is_qa=qa)
        
        roles_assigned = []
        if developer:
            roles_assigned.append("👨‍💻 Developer")
        if qa:
            roles_assigned.append("🔍 QA")
        
        roles_text = " + ".join(roles_assigned)
        
        embed = discord.Embed(
            title="Role Assigned",
            description=f"Assigned to {user.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Roles", value=roles_text, inline=False)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Roles set for {user}: Developer={developer}, QA={qa}")
        
    except Exception as e:
        logger.error(f"Error setting role: {e}")
        await interaction.followup.send(f"❌ Error setting role: {e}")



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
        # Load tickets from folder with parsing
        tickets = load_tickets_from_folder(folder)
        
        if not tickets:
            await interaction.followup.send(f"❌ No markdown files found in `{folder}/` folder")
            return
        
        # Create threads for each ticket
        created_count = 0
        failed_count = 0
        
        for ticket in tickets:
            try:
                # Use parsed title if available, otherwise use name
                display_name = ticket.get('title') or ticket['name']
                thread_name = f"[OPEN] {display_name}"
                
                # Create thread in the specified channel
                thread = await channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread
                )
                
                # Add to database
                add_thread(
                    thread_id=thread.id,
                    ticket_name=display_name,
                    folder=folder,
                    channel_id=channel.id,
                    created_by=str(interaction.user)
                )
                
                # Build detailed embed with parsed information
                embed = discord.Embed(
                    title=display_name,
                    color=discord.Color.blue()
                )
                
                # Add priority if present
                if ticket.get('priority'):
                    embed.add_field(name="🚨 Priority", value=f"**{ticket['priority']}**", inline=False)
                
                # Add problem section
                if ticket.get('problem'):
                    problem_text = ticket['problem'][:1024]  # Discord limit
                    if len(ticket['problem']) > 1024:
                        problem_text += "..."
                    embed.add_field(name="Problem", value=problem_text, inline=False)
                
                # Add what to fix
                if ticket.get('what_to_fix'):
                    fix_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(ticket['what_to_fix'][:5])])
                    if len(ticket['what_to_fix']) > 5:
                        fix_text += f"\n... and {len(ticket['what_to_fix']) - 5} more"
                    embed.add_field(name="What to Fix", value=fix_text, inline=False)
                
                # Add acceptance criteria
                if ticket.get('acceptance_criteria'):
                    criteria_text = "\n".join([f"✓ {item}" for item in ticket['acceptance_criteria'][:5]])
                    if len(ticket['acceptance_criteria']) > 5:
                        criteria_text += f"\n... and {len(ticket['acceptance_criteria']) - 5} more"
                    embed.add_field(name="Acceptance Criteria", value=criteria_text, inline=False)
                
                # Add related files if present
                if ticket.get('related_files'):
                    files_text = "\n".join([f"• {file[:100]}" for file in ticket['related_files'][:3]])
                    if len(ticket['related_files']) > 3:
                        files_text += f"\n• ... and {len(ticket['related_files']) - 3} more"
                    embed.add_field(name="Related Files", value=files_text, inline=False)
                
                embed.add_field(name="Status", value="🔵 OPEN", inline=True)
                embed.add_field(name="Folder", value=f"`{folder}`", inline=True)
                embed.set_footer(text=f"Created by {interaction.user}")
                
                await thread.send(embed=embed)
                
                created_count += 1
                logger.info(f"Created thread: {thread_name} (ID: {thread.id})")
                
            except Exception as e:
                logger.error(f"Failed to create thread for {ticket.get('title', ticket['name'])}: {e}")
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
    description="Claim a ticket by updating its status to CLAIMED (Developer only)"
)
@app_commands.describe(
    thread="The thread/ticket to claim"
)
async def claim_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Claim a ticket and update its status to CLAIMED. Only Developers can claim."""
    await interaction.response.defer()
    
    try:
        # Check if user is a Developer
        if not has_role(interaction.user.id, "developer"):
            await interaction.followup.send("❌ Only Developers can claim tickets. Use `/set-role` to assign a role.")
            return
        
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
        update_thread_status(thread.id, "CLAIMED", claimed_by_id=interaction.user.id, claimed_by_username=username)
        
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
    description="Mark a ticket as PENDING-REVIEW and add developer score (Developer only)"
)
@app_commands.describe(
    thread="The thread/ticket to mark as pending review"
)
async def resolve_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Mark a ticket as pending review. Only Developers can mark as resolved."""
    await interaction.response.defer()
    
    try:
        # Check if user is a Developer
        if not has_role(interaction.user.id, "developer"):
            await interaction.followup.send("❌ Only Developers can mark tickets as pending review. Use `/set-role` to assign a role.")
            return
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] == 'PENDING-REVIEW':
            await interaction.followup.send("⚠️ This ticket is already pending review")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[Pending-Review][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "PENDING-REVIEW", resolved_by_id=interaction.user.id, resolved_by_username=username)
        
        # Update developer leaderboard
        increment_developer_resolved(interaction.user.id, str(interaction.user))
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Pending Review",
            description=f"Marked by: {interaction.user.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Old Status", value=thread_info['status'], inline=True)
        embed.add_field(name="New Status", value=f"[Pending-Review][{username}]", inline=True)
        embed.add_field(name="Next Step", value="Waiting for QA review. Use `/reviewed` to approve.", inline=False)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket marked pending review: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error marking ticket as pending review: {e}")
        await interaction.followup.send(f"❌ Error marking ticket as pending review: {e}")


@bot.tree.command(
    name="reviewed",
    description="Approve a ticket after review and add to QA score (QA only)"
)
@app_commands.describe(
    thread="The thread/ticket to mark as reviewed"
)
async def reviewed_ticket(interaction: discord.Interaction, thread: discord.Thread):
    """Mark a ticket as reviewed after QA approval. Only QAs can review."""
    await interaction.response.defer()
    
    try:
        # Check if user is a QA
        if not has_role(interaction.user.id, "qa"):
            await interaction.followup.send("❌ Only QAs can review tickets. Use `/set-role` to assign a role.")
            return
        
        # Get thread info from database
        thread_info = get_thread(thread.id)
        
        if not thread_info:
            await interaction.followup.send("❌ This thread is not tracked in the database")
            return
        
        if thread_info['status'] != 'PENDING-REVIEW':
            await interaction.followup.send("⚠️ This ticket is not pending review. Only pending review tickets can be reviewed.")
            return
        
        if thread_info['status'] == 'REVIEWED':
            await interaction.followup.send("⚠️ This ticket is already reviewed")
            return
        
        # Get user's display name
        member = interaction.guild.get_member(interaction.user.id)
        username = member.display_name if member else interaction.user.name
        
        # Update thread name
        ticket_name = thread_info['ticket_name']
        new_name = f"[Reviewed][{username}]{ticket_name}"
        
        await thread.edit(name=new_name)
        update_thread_status(thread.id, "REVIEWED", reviewed_by_id=interaction.user.id, reviewed_by_username=username)
        
        # Update QA leaderboard
        increment_qa_reviewed(interaction.user.id, str(interaction.user))
        
        # Send notification
        embed = discord.Embed(
            title="Ticket Reviewed",
            description=f"Reviewed by: {interaction.user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Old Status", value="[Pending-Review]", inline=True)
        embed.add_field(name="New Status", value=f"[Reviewed][{username}]", inline=True)
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket reviewed: {thread.id} by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error reviewing ticket: {e}")
        await interaction.followup.send(f"❌ Error reviewing ticket: {e}")


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
    role="Filter leaderboard by role: 'dev' for Developers or 'qa' for QAs (default: dev)",
    limit="Number of top resolvers to show (default: 10, max: 50)"
)
async def show_leaderboard(interaction: discord.Interaction, role: str = "dev", limit: int = 10):
    """Display the leaderboard of users who have resolved the most tickets."""
    await interaction.response.defer()
    
    try:
        # Validate role parameter
        role_lower = role.lower().strip()
        if role_lower not in ["dev", "developer", "qa", "qas"]:
            await interaction.followup.send("❌ Invalid role. Use 'dev' for Developers or 'qa' for QAs.")
            return
        
        # Normalize role
        if role_lower in ["dev", "developer"]:
            role_param = "dev"
            title_role = "👨‍💻 Developer Resolution Leaderboard"
            stat_name = "Resolved"
        else:
            role_param = "qa"
            title_role = "🔍 QA Review Leaderboard"
            stat_name = "Reviewed"
        
        # Clamp limit between 1 and 50
        limit = max(1, min(limit, 50))
        
        # Get leaderboard based on role
        if role_param == "dev":
            leaderboard = get_leaderboard_dev(limit)
        else:
            leaderboard = get_leaderboard_qa(limit)
        
        if not leaderboard:
            await interaction.followup.send(f"📊 No {role_param.upper()} activity yet!")
            return
        
        # Build leaderboard description
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, entry in enumerate(leaderboard, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}️⃣"
            
            if role_param == "dev":
                count = entry['dev_resolved_count']
            else:
                count = entry['qa_reviewed_count']
            
            description += f"{medal} **{entry['username']}** - {count} {stat_name}\n"
        
        embed = discord.Embed(
            title=title_role,
            description=description,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Showing top {limit} {role_param.upper()}s")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Leaderboard shown to {interaction.user} (role: {role_param})")
        
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
