"""Database module for managing tickets and leaderboard (PostgreSQL)."""
import os
import asyncio
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
import glob
from pathlib import Path
from urllib.parse import urlparse, unquote
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import pool as psycopg2_pool
from config import DATABASE_URL
from cache import cache_get, cache_set, cache_delete, ROLE_TTL, THREAD_TTL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "15000"))
_UNSET = object()

# ── Connection pool ────────────────────────────────────────────────────────────
# Supabase's transaction-mode pooler supports a small number of server-side
# connections.  We keep 2 warm connections and allow bursting to 8.
_DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
_DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "8"))
_pool: psycopg2_pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2_pool.ThreadedConnectionPool | None:
    """Return the shared connection pool, creating it lazily if needed."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:        # double-check after acquiring lock
            return _pool
        if not DATABASE_URL:
            logger.error("DATABASE_URL is not set. Database operations will fail.")
            return None
        try:
            _pool = psycopg2_pool.ThreadedConnectionPool(
                _DB_POOL_MIN,
                _DB_POOL_MAX,
                DATABASE_URL,
                cursor_factory=DictCursor,
                sslmode="require",
                connect_timeout=DB_CONNECT_TIMEOUT_SECONDS,
                options=f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
            )
            logger.info(
                "PostgreSQL connection pool created (min=%s, max=%s).",
                _DB_POOL_MIN, _DB_POOL_MAX,
            )
        except psycopg2.Error as exc:
            logger.error("Failed to create connection pool: %s", exc)
            _pool = None
    return _pool


@contextmanager
def get_db():
    """Borrow a connection from the pool, yield it, then return it.

    Usage::

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
            conn.commit()
    """
    p = _get_pool()
    if p is None:
        raise RuntimeError("Database pool is unavailable.")
    conn = p.getconn()
    try:
        yield conn
    except psycopg2.Error:
        conn.rollback()
        raise
    finally:
        # Reset the connection so the next caller starts clean.
        try:
            conn.rollback()
        except Exception:
            pass
        p.putconn(conn)


def get_connection():
    """Compatibility shim — returns a *pooled* connection.

    Prefer using the ``get_db()`` context manager in new code so the
    connection is returned to the pool automatically.  Callers using this
    function are responsible for calling ``release_connection(conn)`` when
    finished.
    """
    p = _get_pool()
    if p is None:
        return None
    try:
        return p.getconn()
    except psycopg2.Error as exc:
        logger.error("Could not obtain connection from pool: %s", exc)
        return None


def release_connection(conn):
    """Return a connection obtained via ``get_connection()`` to the pool."""
    if conn is None:
        return
    p = _get_pool()
    if p is None:
        try:
            conn.close()
        except Exception:
            pass
        return
    try:
        conn.rollback()
    except Exception:
        pass
    p.putconn(conn)



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
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        logger.info("Database startup connectivity check passed.")
        return True
    except Exception as e:
        logger.error("Database startup connectivity check failed: %s", e)
        return False


def init_db():
    """Initialize the database and run migrations."""
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    except Exception as e:
        logger.error("Database initialization skipped: %s", e)
        return

    # Run pending migrations
    run_migrations()

def run_migrations():
    """Run all pending SQL migrations."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM migrations")
            applied_migrations = {row['name'] for row in cursor.fetchall()}

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
    except Exception as e:
        logger.error("Migration run skipped: %s", e)

def add_thread(thread_id: int, ticket_name: str, folder: str, channel_id: int, created_by: str | None = None):
    """Add a new thread to the database."""
    cache_delete(f"thread:{thread_id}")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO threads (thread_id, ticket_name, folder, channel_id, status, created_by)
            VALUES (%s, %s, %s, %s, 'OPEN', %s)
            ON CONFLICT (thread_id) DO UPDATE SET
                ticket_name = EXCLUDED.ticket_name,
                folder = EXCLUDED.folder,
                channel_id = EXCLUDED.channel_id,
                status = 'OPEN',
                created_by = EXCLUDED.created_by,
                claimed_by_id = NULL,
                claimed_by_username = NULL,
                resolved_by_id = NULL,
                resolved_by_username = NULL,
                reviewed_by_id = NULL,
                reviewed_by_username = NULL,
                pr_url = NULL
        """, (thread_id, ticket_name, folder, channel_id, created_by))
        conn.commit()

def get_thread(thread_id: int):
    """Get a thread from the database (cached)."""
    key = f"thread:{thread_id}"
    hit, value = cache_get(key)
    if hit:
        return value
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM threads WHERE thread_id = %s", (thread_id,))
        row = cursor.fetchone()
    result = dict(row) if row else None
    cache_set(key, result, THREAD_TTL)
    return result

def update_thread_status(
    thread_id: int,
    status: str,
    claimed_by_id: int | None | object = _UNSET,
    claimed_by_username: str | None | object = _UNSET,
    resolved_by_id: int | None | object = _UNSET,
    resolved_by_username: str | None | object = _UNSET,
    reviewed_by_id: int | None | object = _UNSET,
    reviewed_by_username: str | None | object = _UNSET,
    pr_url: str | None | object = _UNSET,
):
    """Update the status of a thread and optionally track who made the change."""
    updates = []
    params = [status.upper()]

    if status.upper() == 'OPEN':
        if claimed_by_id is _UNSET: claimed_by_id = None
        if claimed_by_username is _UNSET: claimed_by_username = None
        if resolved_by_id is _UNSET: resolved_by_id = None
        if resolved_by_username is _UNSET: resolved_by_username = None
        if reviewed_by_id is _UNSET: reviewed_by_id = None
        if reviewed_by_username is _UNSET: reviewed_by_username = None
        if pr_url is _UNSET: pr_url = None
    elif status.upper() == 'CLAIMED':
        if resolved_by_id is _UNSET: resolved_by_id = None
        if resolved_by_username is _UNSET: resolved_by_username = None
        if reviewed_by_id is _UNSET: reviewed_by_id = None
        if reviewed_by_username is _UNSET: reviewed_by_username = None
        if pr_url is _UNSET: pr_url = None
    elif status.upper() == 'PENDING-REVIEW':
        if reviewed_by_id is _UNSET: reviewed_by_id = None
        if reviewed_by_username is _UNSET: reviewed_by_username = None

    if claimed_by_id is not _UNSET or claimed_by_username is not _UNSET:
        claim_id_value = None if claimed_by_id is _UNSET else claimed_by_id
        claim_username_value = None if claimed_by_username is _UNSET else claimed_by_username
        updates.append("claimed_by_id = %s, claimed_by_username = %s")
        params.extend([claim_id_value, claim_username_value])

    if resolved_by_id is not _UNSET or resolved_by_username is not _UNSET:
        resolve_id_value = None if resolved_by_id is _UNSET else resolved_by_id
        resolve_username_value = None if resolved_by_username is _UNSET else resolved_by_username
        updates.append("resolved_by_id = %s, resolved_by_username = %s")
        params.extend([resolve_id_value, resolve_username_value])

    if pr_url is not _UNSET:
        updates.append("pr_url = %s")
        params.append(pr_url)

    if reviewed_by_id is not _UNSET or reviewed_by_username is not _UNSET:
        review_id_value = None if reviewed_by_id is _UNSET else reviewed_by_id
        review_username_value = None if reviewed_by_username is _UNSET else reviewed_by_username
        updates.append("reviewed_by_id = %s, reviewed_by_username = %s")
        params.extend([review_id_value, review_username_value])

    params.append(thread_id)
    update_clause = ", ".join(updates)
    if update_clause:
        update_clause = ", " + update_clause

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE threads SET status = %s{update_clause} WHERE thread_id = %s
        """, params)
        conn.commit()
    # Bust the thread cache so next read reflects the new status
    cache_delete(f"thread:{thread_id}")


# ===== User Role Management =====

def set_user_role(user_id: int, username: str, is_developer: bool = False, is_qa: bool = False, is_pm: bool = False):
    """Set or update a user's roles (can have multiple)."""
    cache_delete(f"roles:{user_id}")
    with get_db() as conn:
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
        cursor.execute("""
            INSERT INTO leaderboard (user_id, username, dev_resolved_count, qa_reviewed_count)
            VALUES (%s, %s, 0, 0)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username))
        conn.commit()

def get_user_roles(user_id: int) -> dict:
    """Get a user's roles (cached)."""
    key = f"roles:{user_id}"
    hit, value = cache_get(key)
    if hit:
        return value
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_developer, is_qa, is_pm FROM user_roles WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
    if row:
        is_pm = bool(row['is_pm'])
        result = {
            "is_developer": bool(row['is_developer']) or is_pm,
            "is_qa": bool(row['is_qa']) or is_pm,
            "is_pm": is_pm
        }
    else:
        result = {"is_developer": False, "is_qa": False, "is_pm": False}
    cache_set(key, result, ROLE_TTL)
    return result

def has_role(user_id: int, role: str) -> bool:
    """Check if user has a specific role permission (uses cached get_user_roles)."""
    roles = get_user_roles(user_id)
    return roles.get(f"is_{role.lower()}", False)


# ===== Leaderboard Management =====

def increment_developer_resolved(user_id: int, username: str):
    """Increment the resolved count for a developer."""
    with get_db() as conn:
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

def increment_qa_reviewed(user_id: int, username: str):
    """Increment the reviewed count for a QA."""
    with get_db() as conn:
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

def decrement_developer_resolved(user_id: int):
    """Decrement the resolved count for a developer (use for unresolve)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leaderboard
            SET dev_resolved_count = GREATEST(0, dev_resolved_count - 1)
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()

def decrement_qa_reviewed(user_id: int):
    """Decrement the reviewed count for a QA (use for unreview)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leaderboard
            SET qa_reviewed_count = GREATEST(0, qa_reviewed_count - 1)
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()

def get_leaderboard_dev(limit: int = 10):
    """Get the developer leaderboard sorted by resolved count."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, dev_resolved_count, last_dev_resolved
            FROM leaderboard WHERE dev_resolved_count > 0
            ORDER BY dev_resolved_count DESC LIMIT %s
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_leaderboard_qa(limit: int = 10):
    """Get the QA leaderboard sorted by reviewed count."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, qa_reviewed_count, last_qa_reviewed
            FROM leaderboard WHERE qa_reviewed_count > 0
            ORDER BY qa_reviewed_count DESC LIMIT %s
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def get_user_resolved_count(user_id: int) -> int:
    """Get the resolved count for a specific developer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT dev_resolved_count FROM leaderboard WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
    return row['dev_resolved_count'] if row else 0


# ===== Loaded Tickets Management =====

def is_ticket_loaded(ticket_filename: str, folder: str) -> bool:
    """Check if a ticket has already been loaded."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM loaded_tickets WHERE ticket_filename = %s AND folder = %s",
            (ticket_filename, folder)
        )
        return cursor.fetchone() is not None

def mark_ticket_loaded(ticket_filename: str, folder: str, thread_id: int, channel_id: int):
    """Mark a ticket as loaded in the database."""
    with get_db() as conn:
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

def remove_thread_record(thread_id: int):
    """Remove a thread and any loaded-ticket mapping that points to it."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM loaded_tickets WHERE thread_id = %s", (thread_id,))
        cursor.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))
        conn.commit()

def get_loaded_tickets(folder: str) -> list:
    """Get all loaded tickets for a specific folder."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ticket_filename, thread_id, channel_id, loaded_at FROM loaded_tickets WHERE folder = %s",
            (folder,)
        )
        return [dict(row) for row in cursor.fetchall()]

# ===== Settings Management =====

def set_setting(key: str, value: str):
    """Set a persistent configuration value."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, value))
        conn.commit()

def get_setting(key: str) -> str | None:
    """Get a persistent configuration value."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cursor.fetchone()
    return row['value'] if row else None


def delete_setting(key: str):
    """Delete a persistent configuration value."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = %s", (key,))
        conn.commit()


# ===== Thread Statistics =====

def get_threads_by_status() -> dict:
    """Get all threads grouped by status."""
    default = {"OPEN": [], "CLAIMED": [], "PENDING-REVIEW": [], "REVIEWED": [], "CLOSED": []}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, ticket_name, thread_id, channel_id
            FROM threads ORDER BY status, created_at DESC
        """)
        rows = cursor.fetchall()
    status_groups = {k: [] for k in default}
    for row in rows:
        s = row['status'].upper()
        status_groups.setdefault(s, []).append(dict(row))
    return status_groups


def get_stale_threads(threshold_hours: int = 48) -> list:
    """Get threads that have remained in active statuses beyond threshold hours."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                thread_id, ticket_name, folder, channel_id, status, created_at,
                FLOOR(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600) AS age_hours
            FROM threads
            WHERE status IN ('OPEN', 'CLAIMED', 'PENDING-REVIEW')
              AND EXTRACT(EPOCH FROM (NOW() - created_at)) >= (%s * 3600)
            ORDER BY created_at ASC
            """,
            (max(1, int(threshold_hours)),),
        )
        return [dict(row) for row in cursor.fetchall()]


# ── Async wrappers ─────────────────────────────────────────────────────────────
# psycopg2 is synchronous.  Running DB calls directly in an async function
# blocks the event loop, which delays every Discord interaction.
# These wrappers offload work to a thread-pool executor so the bot stays
# responsive while waiting for Supabase round-trips.

async def async_get_thread(thread_id: int):
    """Non-blocking version of get_thread."""
    return await asyncio.to_thread(get_thread, thread_id)

async def async_get_user_roles(user_id: int) -> dict:
    """Non-blocking version of get_user_roles."""
    return await asyncio.to_thread(get_user_roles, user_id)

async def async_has_role(user_id: int, role: str) -> bool:
    """Non-blocking version of has_role."""
    return await asyncio.to_thread(has_role, user_id, role)

async def async_update_thread_status(thread_id: int, status: str, **kwargs):
    """Non-blocking version of update_thread_status."""
    return await asyncio.to_thread(update_thread_status, thread_id, status, **kwargs)

async def async_get_threads_by_status() -> dict:
    """Non-blocking version of get_threads_by_status."""
    return await asyncio.to_thread(get_threads_by_status)

async def async_get_leaderboard_dev(limit: int = 10) -> list:
    """Non-blocking version of get_leaderboard_dev."""
    return await asyncio.to_thread(get_leaderboard_dev, limit)

async def async_get_leaderboard_qa(limit: int = 10) -> list:
    """Non-blocking version of get_leaderboard_qa."""
    return await asyncio.to_thread(get_leaderboard_qa, limit)

async def async_get_setting(key: str) -> str | None:
    """Non-blocking version of get_setting."""
    return await asyncio.to_thread(get_setting, key)

async def async_set_setting(key: str, value: str) -> None:
    """Non-blocking version of set_setting."""
    return await asyncio.to_thread(set_setting, key, value)
