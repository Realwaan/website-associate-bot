# Architecture Guide Template

This document serves as a template to outline the system architecture, design decisions, and database schemas of the **Website Associate Bot**.

---

## 🏗️ System Overview

Describe the high-level architecture here. Explain how the components interact:

*   **Discord Bot Client (`main.py`):** Coordinates event handlers and registers Slash Commands.
*   **Keep-Alive & Webhook Gateway (`keep_alive.py`):** Runs a background WSGI server to handle GitHub webhooks and Render health check queries.
*   **Database Interface (`database.py`):** Manages connection pooling and executes queries.
*   **Cache (`cache.py`):** Implements an in-memory TTL cache to reduce database round-trips for roles and thread statuses.
*   **Math Rendering Engine (`math_renderer.py` / `latex_formatter.py`):** Compiles and renders LaTeX equations as images for Discord threads.

---

## 🗄️ Database Schema & Migrations

### Database Engine
*   **Production:** PostgreSQL (hosted on Supabase, managed via connection pooling).
*   **Local / Testing:** PostgreSQL (via environment configuration) or mocked.

### Core Tables

#### `threads`
Maps active Discord threads to their associated project folders and ticket states.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `thread_id` | `BIGINT` | `PRIMARY KEY` | Discord Thread ID. |
| `ticket_name` | `TEXT` | `NOT NULL` | Original title of the ticket. |
| `folder` | `TEXT` | `NOT NULL` | Folder source in the tickets directory. |
| `status` | `TEXT` | `DEFAULT 'OPEN'` | Status in the ticket pipeline (OPEN, CLAIMED, etc.). |

#### `user_roles`
Stores the mapped roles of developers, QAs, and Project Managers.

#### `leaderboard`
Stores resolved and reviewed counts for devs and QA respectively.

#### `loaded_tickets`
Tracks which files have been imported to prevent duplicate thread generation.

### Migrations Workflow
Migrations are stored in the `/migrations/` directory as raw SQL files.
They are executed in sequential alphabetical/numeric order upon bot startup via `init_db()` or via `/scripts/migrate_db.py`.

---

## 🔄 Concurrency & Background Workers

### Event Loops & Webhook Queueing
Explain how the Flask server (running in a background daemon thread) communicates with the main Discord event loop.
*   Flask accepts webhook requests, verifies the signature, and enqueues the raw payload to an `asyncio.Queue` thread-safely via `call_soon_threadsafe()`.
*   A background asyncio loop (`process_webhook_events`) polls the queue and processes events without blocking the Discord client.

### Background Tasks (`discord.ext.tasks`)
Detail background tasks:
1.  **Scheduled Summary:** Runs daily at 8:00 AM PH time to post a digest of all tickets.
2.  **Repository updates polling:** Periodically polls configured repositories for new commits if webhooks are not configured.
3.  **Dead Letter Retry:** Re-attempts delivery for failed webhook entries.
4.  **Operational Cleanup:** Prunes metrics and logging records older than configured thresholds.
