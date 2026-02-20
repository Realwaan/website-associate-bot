"""Database module for managing tickets and leaderboard."""
import sqlite3
import os
from datetime import datetime
from config import DATABASE_FILE


def get_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create threads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id INTEGER PRIMARY KEY,
            ticket_name TEXT NOT NULL,
            folder TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            status TEXT DEFAULT 'OPEN',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        )
    """)

    # Create leaderboard table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            resolved_count INTEGER DEFAULT 0,
            last_resolved_date TIMESTAMP,
            total_resolved INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def add_thread(thread_id: int, ticket_name: str, folder: str, channel_id: int, created_by: str = None):
    """Add a new thread to the database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO threads (thread_id, ticket_name, folder, channel_id, status, created_by)
        VALUES (?, ?, ?, ?, 'OPEN', ?)
    """, (thread_id, ticket_name, folder, channel_id, created_by))

    conn.commit()
    conn.close()


def get_thread(thread_id: int):
    """Get a thread from the database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM threads WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_thread_status(thread_id: int, status: str):
    """Update the status of a thread."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE threads SET status = ? WHERE thread_id = ?
    """, (status.upper(), thread_id))

    conn.commit()
    conn.close()


def increment_resolved(user_id: int, username: str):
    """Increment the resolved count for a user in the leaderboard."""
    conn = get_connection()
    cursor = conn.cursor()

    # Try to update first
    cursor.execute("""
        UPDATE leaderboard 
        SET resolved_count = resolved_count + 1, 
            last_resolved_date = ?,
            total_resolved = total_resolved + 1
        WHERE user_id = ?
    """, (datetime.now().isoformat(), user_id))

    # If no rows were updated, insert a new one
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO leaderboard (user_id, username, resolved_count, last_resolved_date, total_resolved)
            VALUES (?, ?, 1, ?, 1)
        """, (user_id, username, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_leaderboard(limit: int = 10):
    """Get the leaderboard of resolved tickets, sorted by resolved count."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, resolved_count, last_resolved_date
        FROM leaderboard
        ORDER BY resolved_count DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_user_resolved_count(user_id: int) -> int:
    """Get the resolved count for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT resolved_count FROM leaderboard WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else 0
