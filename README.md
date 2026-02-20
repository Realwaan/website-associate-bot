# Discord Ticket Management Bot

A Discord bot for managing support tickets organized by folder and channel. Track ticket statuses and maintain a leaderboard of resolved tickets.

## Features

✨ **Ticket Management**
- Load tickets from markdown files organized in folders
- Create Discord threads for each ticket with status prefixes
- Track ticket status: `[OPEN]`, `[CLAIMED]`, `[RESOLVED]`, `[CLOSED]`
- Update thread names to reflect current status

📊 **Leaderboard**
- Automatic leaderboard of users who have resolved tickets
- View top resolvers with `/leaderboard` command
- Persistent data storage using SQLite

🗂️ **Folder Organization**
- Organize tickets into different folders (e.g., `support/`, `bugs/`, `features/`)
- Load tickets from any folder into any Discord channel
- Flexible folder structure

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file and add your Discord bot token:

```
DISCORD_TOKEN=your_bot_token_here
```

To get a bot token:
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and click "Add Bot"
4. Copy the token and paste it in `.env`

### 3. Invite Bot to Server

1. In Developer Portal, go to "OAuth2" > "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Manage Channels`, `Manage Threads`, `Send Messages`, `Embed Links`
4. Copy the generated URL and open it in browser
5. Select your server and authorize

### 4. Create Ticket Folders

Create folders inside the `tickets/` directory:

```
tickets/
├── support/
│   ├── password-reset.md
│   └── login-issue.md
├── bugs/
│   ├── ui-glitch.md
│   └── api-timeout.md
└── features/
    └── dark-mode.md
```

### 5. Run the Bot

```bash
python main.py
```

## Commands

### `/load-tickets <folder> <channel>`
Load all markdown files from a specified folder into a Discord channel.

**Parameters:**
- `folder` - Folder name within `tickets/` directory (e.g., `support`, `bugs`)
- `channel` - Discord channel where threads will be created

**Example:**
```
/load-tickets support #support-squad
/load-tickets bugs #bug-reports
```

### `/claim <thread>`
Mark a ticket as claimed (status: `[CLAIMED]`).

**Parameters:**
- `thread` - The thread to claim

### `/resolved <thread>`
Mark a ticket as resolved (status: `[RESOLVED]`). Adds user to leaderboard.

**Parameters:**
- `thread` - The thread to mark as resolved

### `/closed <thread>`
Mark a ticket as closed (status: `[CLOSED]`).

**Parameters:**
- `thread` - The thread to close

### `/leaderboard [limit]`
Display the leaderboard of users who have resolved the most tickets.

**Parameters:**
- `limit` - Number of top resolvers to show (default: 10, max: 50)

### `/ticket-folders`
List all available ticket folders in the `tickets/` directory.

## Ticket File Format

Create markdown files in your ticket folders. The filename (without `.md`) becomes the thread name.

**Example: `tickets/support/password-reset.md`**
```markdown
# Password Reset Issue

## Problem
User is unable to reset their password.

## Steps to Reproduce
1. Click forgot password
2. Enter email
3. Check inbox

## Expected Behavior
Email should arrive within 5 minutes.
```

The thread will be created as: `[OPEN] password-reset`

## Database

The bot uses SQLite (`tickets.db`) to store:
- **Thread tracking** - Maps Discord threads to ticket information
- **Leaderboard** - Tracks number of resolved tickets per user

The database is automatically created and initialized on first run.

## Project Structure

```
website-associate-bot/
├── main.py                    # Main bot code with commands
├── config.py                  # Configuration and environment variables
├── database.py                # SQLite database operations
├── ticket_loader.py           # Ticket file parsing
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (Discord token)
├── .gitignore                 # Git ignore patterns
├── tickets.db                 # SQLite database (auto-created)
└── tickets/                   # Ticket markdown files
    ├── support/
    ├── bugs/
    └── features/
```

## Troubleshooting

**Bot doesn't respond to commands:**
- Verify bot has correct permissions in your server
- Check that `DISCORD_TOKEN` is set correctly in `.env`
- Run `/ticket-folders` to verify bot is working

**Tickets not loading:**
- Ensure folder exists in `tickets/` directory
- Check that files have `.md` extension
- Verify folder name matches what you pass to `/load-tickets`

**Threads not created in correct channel:**
- Make sure the channel parameter references the correct Discord channel
- Verify bot has permission to create threads in that channel

## License

MIT

## Support

For issues or suggestions, contact the development team.
