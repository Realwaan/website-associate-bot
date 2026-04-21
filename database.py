"""Database module for managing tickets and leaderboard (PostgreSQL)."""
import os
import logging
from datetime import datetime
import glob
from pathlib import Path
from urllib.parse import urlparse, unquote
import psycopg2
from psycopg2.extras import DictCursor
from config import DATABASE_URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "15000"))


def get_database_url_summary() -> dict:
    """Return a safe, non-secret summary of DATABASE_URL for diagnostics."""
    if not DATABASE_URL:
        return {"configured": False}

    parsed = urlparse(DATABASE_URL)
    raw_user = unquote(parsed.username or "")
    db_name = parsed.path.lstrip("/") if parsed.path else ""

    return {
        "configured": True,
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": parsed.port,
        "db": db_name,
        "user": raw_user,
        "has_tenant_suffix": "." in raw_user,
    }


def validate_database_url() -> tuple[bool, str]:
    """Validate DATABASE_URL shape without exposing secrets."""
    if not DATABASE_URL:
        return False, "DATABASE_URL is missing."

    parsed = urlparse(DATABASE_URL)
    if parsed.scheme not in {"postgresql", "postgres"}:
        return False, "DATABASE_URL must start with postgres:// or postgresql://"

    if not parsed.hostname:
        return False, "DATABASE_URL is missing host."

    if not parsed.path or parsed.path == "/":
        return False, "DATABASE_URL is missing database name in path."

    if not parsed.username:
        return False, "DATABASE_URL is missing username."

    if parsed.password is None:
        return False, "DATABASE_URL is missing password."

    return True, "ok"


def verify_database_connection() -> bool:
    """Validate URL and verify that a simple query can run successfully."""
    is_valid, reason = validate_database_url()
    if not is_valid:
        logger.error("Database configuration invalid: %s", reason)
        return False

    summary = get_database_url_summary()
    logger.info(
        "Database startup check: host=%s port=%s db=%s user=%s tenant_suffix=%s",
        summary.get("host"),
        summary.get("port") or 5432,
        summary.get("db"),
        summary.get("user"),
        summary.get("has_tenant_suffix"),
    )

    try:
        conn = get_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        logger.info("Database startup connectivity check passed.")
        return True
    except psycopg2.Error as e:
        logger.error("Database startup connectivity check failed: %s", e)
        return False

def get_connection():
    """Get a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set. Database operations will fail.")
        return None
    # For Supabase pooler connections, credentials must be used exactly as encoded
    # in DATABASE_URL (e.g. user can be 'postgres.<project_ref>').
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=DictCursor,
        sslmode='require',
        connect_timeout=DB_CONNECT_TIMEOUT_SECONDS,
        options=f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
    )
    return conn

def init_db():
    """Initialize the database and run migrations."""
    if not DATABASE_URL:
        return
    conn = get_connection()
    if not conn:
        logger.error("Database initialization skipped because a connection could not be established.")
        return
    cursor = conn.cursor()

    # Create migrations table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    # Run pending migrations
    run_migrations()

def run_migrations():
    """Run all pending SQL migrations."""
    conn = get_connection()
    if not conn:
        logger.error("Migration run skipped because a connection could not be established.")
        return
    cursor = conn.cursor()

    # Get applied migrations
    cursor.execute("SELECT name FROM migrations")
    applied_migrations = {row['name'] for row in cursor.fetchall()}

    # Get all migration files
    migration_files = sorted((Path(__file__).resolve().parent / "migrations").glob("*.sql"))

    for migration_file in migration_files:
        migration_name = os.path.basename(migration_file)
        if migration_name not in applied_migrations:
            logger.info(f"Applying migration: {migration_name}")
            with open(migration_file, 'r') as f:
                sql = f.read()
                try:
                    cursor.execute(sql)
                    cursor.execute("INSERT INTO migrations (name) VALUES (%s)", (migration_name,))
                    conn.commit()
                except psycopg2.Error as e:
                    logger.error(f"Error applying migration {migration_name}: {e}")
                    conn.rollback()
                    break

    conn.close()

def add_thread(thread_id: int, ticket_name: str, folder: str, channel_id: int, created_by: str | None = None):
    """Add a new thread to the database."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO threads (thread_id, ticket_name, folder, channel_id, status, created_by)
        VALUES (%s, %s, %s, %s, 'OPEN', %s)
        ON CONFLICT (thread_id) DO UPDATE SET
            ticket_name = EXCLUDED.ticket_name,
            folder = EXCLUDED.folder,
            channel_id = EXCLUDED.channel_id,
            status = 'OPEN',
            created_by = EXCLUDED.created_by
    """, (thread_id, ticket_name, folder, channel_id, created_by))

    conn.commit()
    conn.close()

def get_thread(thread_id: int):
    """Get a thread from the database."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM threads WHERE thread_id = %s", (thread_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None

def update_thread_status(thread_id: int, status: str, claimed_by_id: int | None = None, claimed_by_username: str | None = None,
                        resolved_by_id: int | None = None, resolved_by_username: str | None = None,
                        reviewed_by_id: int | None = None, reviewed_by_username: str | None = None, pr_url: str | None = None):
    """Update the status of a thread and optionally track who made the change."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    updates = []
    params = [status.upper()]

    if claimed_by_id is not None:
        updates.append("claimed_by_id = %s, claimed_by_username = %s")
        params.extend([claimed_by_id, claimed_by_username])

    if resolved_by_id is not None:
        updates.append("resolved_by_id = %s, resolved_by_username = %s")
        params.extend([resolved_by_id, resolved_by_username])

    if pr_url is not None:
        updates.append("pr_url = %s")
        params.append(pr_url)

    if reviewed_by_id is not None:
        updates.append("reviewed_by_id = %s, reviewed_by_username = %s")
        params.extend([reviewed_by_id, reviewed_by_username])

    params.append(thread_id)

    update_clause = ", ".join(updates) if updates else ""
    if update_clause:
        update_clause = ", " + update_clause

    cursor.execute(f"""
        UPDATE threads SET status = %s{update_clause} WHERE thread_id = %s
    """, params)

    conn.commit()
    conn.close()


# ===== User Role Management =====

def set_user_role(user_id: int, username: str, is_developer: bool = False, is_qa: bool = False, is_pm: bool = False):
    """Set or update a user's roles (can have multiple)."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_roles (user_id, username, is_developer, is_qa, is_pm)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            is_developer = EXCLUDED.is_developer,
            is_qa = EXCLUDED.is_qa,
            is_pm = EXCLUDED.is_pm
    """, (user_id, username, int(is_developer), int(is_qa), int(is_pm)))

    # Also ensure user exists in leaderboard
    cursor.execute("""
        INSERT INTO leaderboard (user_id, username, dev_resolved_count, qa_reviewed_count)
        VALUES (%s, %s, 0, 0)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username))

    conn.commit()
    conn.close()

def get_user_roles(user_id: int) -> dict:
    """Get a user's roles."""
    conn = get_connection()
    if not conn: return {"is_developer": False, "is_qa": False, "is_pm": False}
    cursor = conn.cursor()

    cursor.execute("SELECT is_developer, is_qa, is_pm FROM user_roles WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        is_pm = bool(row['is_pm'])
        return {
            # PM inherits both developer and QA permissions.
            "is_developer": bool(row['is_developer']) or is_pm,
            "is_qa": bool(row['is_qa']) or is_pm,
            "is_pm": is_pm
        }
    return {"is_developer": False, "is_qa": False, "is_pm": False}

def has_role(user_id: int, role: str) -> bool:
    """Check if user has a specific role permission."""
    roles = get_user_roles(user_id)
    return roles.get(f"is_{role.lower()}", False)


# ===== Leaderboard Management =====

def increment_developer_resolved(user_id: int, username: str):
    """Increment the resolved count for a developer."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leaderboard (user_id, username, dev_resolved_count, last_dev_resolved)
        VALUES (%s, %s, 1, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            dev_resolved_count = leaderboard.dev_resolved_count + 1,
            last_dev_resolved = EXCLUDED.last_dev_resolved
    """, (user_id, username, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def increment_qa_reviewed(user_id: int, username: str):
    """Increment the reviewed count for a QA."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leaderboard (user_id, username, qa_reviewed_count, last_qa_reviewed)
        VALUES (%s, %s, 1, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            qa_reviewed_count = leaderboard.qa_reviewed_count + 1,
            last_qa_reviewed = EXCLUDED.last_qa_reviewed
    """, (user_id, username, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def decrement_developer_resolved(user_id: int):
    """Decrement the resolved count for a developer (use for unresolve)."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leaderboard 
        SET dev_resolved_count = GREATEST(0, dev_resolved_count - 1)
        WHERE user_id = %s
    """, (user_id,))

    conn.commit()
    conn.close()

def decrement_qa_reviewed(user_id: int):
    """Decrement the reviewed count for a QA (use for unreview)."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leaderboard 
        SET qa_reviewed_count = GREATEST(0, qa_reviewed_count - 1)
        WHERE user_id = %s
    """, (user_id,))

    conn.commit()
    conn.close()

def get_leaderboard_dev(limit: int = 10):
    """Get the developer leaderboard sorted by resolved count."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, dev_resolved_count, last_dev_resolved
        FROM leaderboard
        WHERE dev_resolved_count > 0
        ORDER BY dev_resolved_count DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_leaderboard_qa(limit: int = 10):
    """Get the QA leaderboard sorted by reviewed count."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, qa_reviewed_count, last_qa_reviewed
        FROM leaderboard
        WHERE qa_reviewed_count > 0
        ORDER BY qa_reviewed_count DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_user_resolved_count(user_id: int) -> int:
    """Get the resolved count for a specific developer."""
    conn = get_connection()
    if not conn: return 0
    cursor = conn.cursor()

    cursor.execute("SELECT dev_resolved_count FROM leaderboard WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()

    return row['dev_resolved_count'] if row else 0


# ===== Loaded Tickets Management =====

def is_ticket_loaded(ticket_filename: str, folder: str) -> bool:
    """Check if a ticket has already been loaded."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM loaded_tickets WHERE ticket_filename = %s AND folder = %s",
        (ticket_filename, folder)
    )
    result = cursor.fetchone()
    conn.close()

    return result is not None

def mark_ticket_loaded(ticket_filename: str, folder: str, thread_id: int, channel_id: int):
    """Mark a ticket as loaded in the database."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO loaded_tickets (ticket_filename, folder, thread_id, channel_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (ticket_filename, folder) DO UPDATE SET
            thread_id = EXCLUDED.thread_id,
            channel_id = EXCLUDED.channel_id,
            loaded_at = CURRENT_TIMESTAMP
    """, (ticket_filename, folder, thread_id, channel_id))

    conn.commit()
    conn.close()

def remove_thread_record(thread_id: int):
    """Remove a thread and any loaded-ticket mapping that points to it."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("DELETE FROM loaded_tickets WHERE thread_id = %s", (thread_id,))
    cursor.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))

    conn.commit()
    conn.close()

def get_loaded_tickets(folder: str) -> list:
    """Get all loaded tickets for a specific folder."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()

    cursor.execute(
        "SELECT ticket_filename, thread_id, channel_id, loaded_at FROM loaded_tickets WHERE folder = %s",
        (folder,)
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

# ===== Settings Management =====

def set_setting(key: str, value: str):
    """Set a persistent configuration value."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, value))

    conn.commit()
    conn.close()

def get_setting(key: str) -> str | None:
    """Get a persistent configuration value."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
    row = cursor.fetchone()
    conn.close()

    return row['value'] if row else None


def delete_setting(key: str):
    """Delete a persistent configuration value."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM settings WHERE key = ?", (key,))

    conn.commit()
    conn.close()


# ===== Thread Statistics =====

def get_threads_by_status() -> dict:
    """Get all threads grouped by status."""
    conn = get_connection()
    if not conn: return {"OPEN": [], "CLAIMED": [], "PENDING-REVIEW": [], "REVIEWED": [], "CLOSED": []}
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, ticket_name, thread_id, channel_id
        FROM threads
        ORDER BY status, created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    status_groups = {
        "OPEN": [],
        "CLAIMED": [],
        "PENDING-REVIEW": [],
        "REVIEWED": [],
        "CLOSED": []
    }

    for row in rows:
        status = row['status'].upper()
        if status in status_groups:
            status_groups[status].append(dict(row))
        else:
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(dict(row))

    return status_groups


def get_stale_threads(threshold_hours: int = 48) -> list:
    """Get threads that have remained in active statuses beyond threshold hours."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            thread_id,
            ticket_name,
            folder,
            channel_id,
            status,
            created_at,
            FLOOR(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600) AS age_hours
        FROM threads
        WHERE status IN ('OPEN', 'CLAIMED', 'PENDING-REVIEW')
          AND EXTRACT(EPOCH FROM (NOW() - created_at)) >= (%s * 3600)
        ORDER BY created_at ASC
        """,
        (max(1, int(threshold_hours)),),
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
