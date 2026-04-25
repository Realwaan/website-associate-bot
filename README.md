# Website Associate Bot

A Discord bot that turns markdown files into trackable support tickets with role-based workflows, leaderboards, and automated project scanning. Built for small teams that need lightweight project management without leaving Discord.

## What It Does

- Reads `.md` ticket files from local folders and creates Discord threads for each one.
- Tracks every ticket through a status pipeline: **OPEN → CLAIMED → Pending-Review → Reviewed → CLOSED**.
- Enforces role-based permissions so Developers, QAs, and Project Managers each have clear responsibilities.
- Maintains separate leaderboards for Developers (resolved count) and QAs (reviewed count).
- Scans external project directories for common code issues (TODOs, debug statements, hardcoded secrets, etc.) and auto-generates ticket files.
- Sends a daily ticket summary to a configured channel at 8:00 AM PH Time.

---

## Features

### Ticket Management
- Load tickets from markdown files organized in folders.
- Create Discord threads for each ticket with status prefixes.
- Parse ticket sections: Problem, What to Fix, Acceptance Criteria, Related Files.
- Prevent duplicate loading — already-loaded tickets are skipped.

### Role-Based Workflow
Three roles, one per user at a time:

| Role | Discord Role Created | Key Permissions |
|------|---------------------|-----------------|
| **Developer** | `Developer` | Claim, resolve, unclaim, unresolve tickets |
| **QA** | `QA` | Review, unreview tickets |
| **Project Manager** | `Project Manager` | All of the above, plus load tickets, rebuild database, scan projects, set reminders channel |

PM role requires server admin to assign. Developer and QA can be self-assigned.

### Undo Actions
Every forward status change has a matching undo command to correct mistakes without database hacks:

| Forward | Undo | Leaderboard Effect |
|---------|------|--------------------|
| `/claim` | `/unclaim` | None |
| `/resolved` | `/unresolve` | Decrements dev count |
| `/reviewed` | `/unreview` | Decrements QA count |

### Project Scanner
The `/scan-project` command walks an external codebase and detects:
- TODO / FIXME / HACK / XXX comments
- Leftover `console.log`, `print()`, `debugger` statements
- Empty catch / except blocks
- Oversized files (configurable threshold, default 300 lines)
- Skipped / disabled tests
- Hardcoded secrets and API keys

Issues are grouped by area and category, then written as ticket `.md` files ready to load with `/load-tickets`.

### Roadmap Generator
The `/scan-roadmap` command scans the full project and creates:
- `tickets/<folder>/ROADMAP.md` with prioritized milestones
- Suggested product/engineering improvements based on findings
- Full repository structure analysis (top-level components, risk, and feature map)
- A 12-week (3-month) development roadmap with weekly progress targets
- Optional issue ticket generation in the same folder for execution

This helps PMs turn raw scanner findings into a usable execution roadmap with clear sequencing across 3 months.

### Cloud-Safe Repository Scanner
If your bot is deployed in cloud (Render), it cannot access local paths like `F:\...` from your machine.
Use `/scan-repo` instead:
- Clones an HTTPS Git repository URL into temporary runtime storage
- Scans the cloned codebase
- Generates roadmap and optional issue tickets under `tickets/<folder>/`

### Scheduled Summaries
A daily task posts a ticket summary grouped by status to a channel set with `/setreminderschannel`. Runs at 8:00 AM PH Time (00:00 UTC).

### Leaderboards
Separate scoreboards for Developers and QAs. Scores update automatically when tickets move through the pipeline and decrement correctly on undo.

---

## MVP and Feature Suggestions

When writing tickets or planning work, the bot is designed around a **ship-the-core-first** philosophy. Follow these rules to keep the project focused:

### Suggesting an MVP or Best Feature

A good MVP ticket answers **yes** to all of these:

1. **Does the user see or interact with it directly?** If not, it is infrastructure — defer it.
2. **Can you demo it in under 60 seconds?** If the demo needs a five-minute setup explanation, the scope is too large.
3. **Does it work without other unbuilt features?** If it depends on three other tickets being done first, it is not MVP.
4. **Can one person finish it in one sitting?** A ticket that takes a full sprint is a project, not a ticket.

When the bot scans a project and generates tickets, each ticket already follows this pattern: one category of issue, in one area of the codebase, with concrete acceptance criteria.

### Preventing Scope Creep

Scope creep happens when a ticket quietly expands to include "while we're at it" work. The bot's ticket format fights this by design:

- **One ticket = one problem.** The ticket guideline enforces this. If a ticket's "What to Fix" section has items touching unrelated parts of the codebase, split it.
- **Acceptance criteria are the contract.** When a developer runs `/resolved`, QA checks the acceptance criteria — nothing more. If something is not listed, it is out of scope for this ticket.
- **Priority markers exist for a reason.** Only use `[PRIORITY]` for work that blocks other tickets and `[CRITICAL]` for production-breaking bugs. Everything else is normal priority.
- **The scanner groups issues tightly.** Auto-generated tickets are scoped to one issue category in one directory. They do not balloon into "fix everything in the project" tickets.
- **Undo commands reduce pressure to over-deliver.** If a developer pushes a ticket to review and realizes they added unrelated changes, they can `/unresolve`, split the work, and re-submit cleanly.

### Red Flags for Scope Creep

When writing or reviewing a ticket, watch for:

- "What to Fix" has more than 8–10 steps.
- Steps reference files in 3+ unrelated directories.
- Acceptance criteria include items that were not in the Problem section.
- The ticket title uses "and" (e.g., "Fix navbar and add search and update footer").
- Estimated effort exceeds what one person can finish before submitting for review.

If any of these appear, split the ticket into smaller, independent tickets.

---

## Workflow

```
PM loads tickets          Developer works           QA verifies            PM closes
─────────────────    ──────────────────────    ──────────────────    ──────────────
/load-tickets          /claim                   /reviewed              /closed
   │                      │                        │                     │
   ▼                      ▼                        ▼                     ▼
[OPEN]  ──────────▶  [CLAIMED]  ──────────▶  [Pending-Review]  ──▶  [Reviewed]  ──▶  [CLOSED]
                     /unclaim ◀──── undo      /unresolve ◀── undo   /unreview ◀── undo
```

1. **PM loads tickets:** `/load-tickets <folder> <channel>` creates `[OPEN]` threads from markdown files.
2. **Developer claims:** `/claim` inside a thread → `[CLAIMED][username]ticket-name`.
    - Immediately create a git branch using the bot's suggested branch name.
    - Full guide: [CLAIM_BRANCH_WORKFLOW.md](CLAIM_BRANCH_WORKFLOW.md)
3. **Developer submits:** `/resolved <pr_url>` inside a thread → `[Pending-Review][username]ticket-name`. Adds to dev leaderboard.
4. **QA reviews:** `/reviewed` inside a thread → `[Reviewed][username]ticket-name`. Adds to QA leaderboard.
5. **PM or involved user closes:** `/closed` inside a thread → `[CLOSED][username]ticket-name`.

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`, then fill in your real values:

```bash
cp .env.example .env
```

Or create/edit the `.env` file directly:

```
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://postgres.<project_ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres
```

To get a bot token:
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application → go to **Bot** → click **Reset Token** and copy it.
3. Paste the token into `.env`.

### 3. Invite Bot to Server

1. In the Developer Portal, go to **OAuth2 → URL Generator**.
2. Select scopes: `bot`, `applications.commands`.
3. Select permissions: `Manage Channels`, `Manage Threads`, `Send Messages`, `Embed Links`, `Manage Roles`.
4. Copy the generated URL, open it in a browser, and select your server.

### 4. Set Up Ticket Folders

Create folders inside the `tickets/` directory. Each folder holds `.md` ticket files for a specific project or category.

### 5. Run the Bot

```bash
python main.py
```

---

## Docker

Build the image:

```bash
docker build -t website-associate-bot .
```

Run the bot (loads `DISCORD_TOKEN` from your local `.env` file):

```bash
docker run --rm --env-file .env website-associate-bot
```

Mount tickets locally to edit without rebuilding:

```bash
docker run --rm --env-file .env -v $(pwd)/tickets:/app/tickets website-associate-bot
```

---

## Deploy Independently (Render + Supabase + Uptime)

This bot can run 24/7 without your local machine by deploying to Render and using Supabase PostgreSQL.

### 1. Push this repository to GitHub

Render deploys from your Git repository, so make sure the latest code is pushed.

### 2. Create a Render Web Service

1. In Render, click **New +** → **Blueprint** (recommended) or **Web Service**.
2. Connect your GitHub repository.
3. If using Blueprint, Render will read `render.yaml` automatically.

### 3. Set Environment Variables in Render

Add these values in Render service settings:

```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://postgres.<project_ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres
KEEP_ALIVE_ENABLED=true
DB_CONNECT_TIMEOUT_SECONDS=10
DB_STATEMENT_TIMEOUT_MS=15000
```

Tip:
- Use `.env.example` in this repository as the source-of-truth template for variable names and defaults.

Notes:
- Use the **Supabase Session Pooler** URL (`pooler.supabase.com:5432`) for IPv4-friendly connectivity.
- Keep credentials in Render secrets, not in source control.

### 4. Health Endpoint for Render and Uptime

The bot now exposes:
- `/` → basic alive message
- `/health` → returns `ok`

Render health checks use `/health` via `render.yaml`.

### 5. Uptime Monitor (Optional but useful)

Set your uptime tool (for example UptimeRobot) to `GET` this URL every 5 minutes:

`https://<your-render-service>.onrender.com/health`

This verifies service availability and can help keep free-tier services warm where applicable.

### 6. Verify Deployment

In Render logs, confirm:
- Database startup connectivity check passed
- Logged in as `<your bot name>`
- Scheduled ticket summary task started

---

## Commands

### Role Management

| Command | Description | Who Can Use |
|---------|-------------|-------------|
| `/set-role developer` | Assign yourself the Developer role | Anyone |
| `/set-role qa` | Assign yourself the QA role | Anyone |
| `/set-role pm` | Assign yourself the Project Manager role | Server admins only |

### Ticket Loading (PM Only)

| Command | Description |
|---------|-------------|
| `/load-tickets <folder> <channel>` | Load markdown files from a folder into a channel as threads |
| `/rebuild-db <folder> <channel>` | Rebuild database entries from existing threads (recovery tool) |
| `/scan-project <path> <folder> [threshold]` | Scan a project directory for issues and auto-generate ticket files |
| `/scan-roadmap <path_or_repo_url> <folder> [threshold] [generate_tickets]` | Scan local folder or HTTPS repo URL and generate roadmap markdown with suggested improvements |
| `/scan-repo <repo_url> [folder] [branch] [threshold] [generate_tickets]` | Cloud-safe scan by cloning a repo URL and generating roadmap/tickets |

### Developer Commands (Use Inside a Thread)

| Command | Description | Leaderboard |
|---------|-------------|-------------|
| `/claim` | Claim a ticket to work on | — |
| `/unclaim` | Unclaim; resets to OPEN | — |
| `/resolved <pr_url>` | Submit for QA review with PR link | +1 dev |
| `/unresolve` | Revert to CLAIMED | -1 dev |

### QA Commands (Use Inside a Thread)

| Command | Description | Leaderboard |
|---------|-------------|-------------|
| `/reviewed` | Approve a Pending-Review ticket | +1 QA |
| `/unreview` | Revert to Pending-Review | -1 QA |

### General Commands

| Command | Description |
|---------|-------------|
| `/closed` | Close a ticket (PM or involved Dev/QA) |
| `/leaderboard <dev\|qa> [limit]` | Show leaderboard (default: dev, limit: 10) |
| `/setreminderschannel <channel>` | Set channel for daily ticket summary (PM only) |
| `/ticket-folders` | List all available ticket folders |
| `/help` | Show in-Discord help with workflow and role info |

---

## Ticket Format

All ticket markdown files follow this structure:

```markdown
# Ticket Title

**[PRIORITY]**

## Problem

Clear explanation of the issue, why it matters, and what needs to be fixed.

## Potentially Related Files

- File path and description
- File path and description

## What to Fix

1. First step
2. Second step
3. Third step

## Acceptance Criteria

- Testable condition 1
- Testable condition 2
- Testable condition 3
```

### Priority Markers

| Marker | When to Use |
|--------|-------------|
| `**[PRIORITY]**` | Feature blocks other work or is critical for MVP |
| `**[CRITICAL]**` | Production is broken |
| *(none)* | Standard ticket |

See [ticketsguideline.md](ticketsguideline.md) for the full writing guide, naming conventions, and examples.

---

## Scanner Configuration

The project scanner's behavior is controlled in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SCAN_IGNORE_DIRS` | `node_modules`, `.git`, `.next`, `dist`, etc. | Directories the scanner skips |
| `SCAN_FILE_EXTENSIONS` | `.ts`, `.tsx`, `.js`, `.py`, `.css`, etc. | File types the scanner reads |
| `SCAN_LARGE_FILE_THRESHOLD` | `300` lines | Files above this get flagged |

---

## Database

The bot uses SQLite (`tickets.db`) with migration-based schema management:

| Table | Purpose |
|-------|---------|
| `threads` | Maps Discord threads to ticket info with full status history |
| `user_roles` | Stores Developer / QA / PM role assignments |
| `leaderboard` | Separate dev resolved and QA reviewed counters |
| `loaded_tickets` | Tracks which tickets have been loaded to prevent duplicates |
| `settings` | Key-value store for bot configuration (e.g., reminders channel) |
| `migrations` | Tracks which SQL migrations have been applied |

The database and all tables are created automatically on first run via `migrations/001_initial_schema.sql`.

---

## Project Structure

```
website-associate-bot/
├── main.py                    # Bot commands and event handlers
├── config.py                  # Environment variables and scanner settings
├── database.py                # SQLite operations and migrations
├── ticket_loader.py           # Markdown file parser
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build (uses uv for fast installs)
├── .env.example               # Safe environment template (committable)
├── .env                       # Local secrets (not committed)
├── .gitignore                 # Git ignore patterns
├── ticketsguideline.md        # Ticket writing guide
├── tickets.db                 # SQLite database (auto-created)
├── migrations/
│   └── 001_initial_schema.sql # Database schema
├── scripts/
│   ├── scan_project.py        # Code scanner and ticket generator
│   └── migrate_db.py          # Standalone migration runner
└── tickets/                   # Ticket markdown files by folder
    ├── intramurals2026/
    ├── borneo/
    ├── my-scan/
    └── SideQuest/
```

---

## Troubleshooting

**Bot does not respond to commands:**
- Verify `DISCORD_TOKEN` is set correctly in `.env`.
- Check that the bot has `applications.commands` scope and the required permissions.
- Run `/ticket-folders` to confirm the bot is online.

**PM commands say "Only Project Managers can...":**
- The PM role requires a server admin to run `/set-role pm`. Regular members cannot self-assign it.

**Role permissions not working:**
- Use `/set-role` to assign a role first. Roles are one-per-user; setting a new role replaces the old one.

**Tickets not loading:**
- Check that the folder exists inside `tickets/` and contains `.md` files.
- Verify the folder name matches what you pass to `/load-tickets`.
- Already-loaded tickets are skipped. Check the bot's response for the skip count.

**Thread info not displaying correctly:**
- Verify the markdown file follows the correct format (see [ticketsguideline.md](ticketsguideline.md)).
- The parser falls back to raw content if section parsing fails.
- Confirm the bot has permission to post embeds in the target channel.

**Scanner not finding issues:**
- Make sure the project path is absolute (e.g., `F:\my-project`).
- Check `config.py` to confirm file extensions and ignored directories match your project.
- Adjust the `threshold` parameter if your codebase uses larger files intentionally.

**Cloud bot cannot scan local machine path:**
- This is expected for Render/containers; cloud runtime cannot read your local `F:\` drive.
- Use `/scan-repo` with a Git URL, or run scanner locally and push generated ticket files to the deployed bot repository.

---

## License

MIT
