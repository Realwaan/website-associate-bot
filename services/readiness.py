"""Dependency checks for the HTTP readiness probe (never mutates data)."""
from pathlib import Path

from database import get_db

REQUIRED_EXTENSIONS = frozenset({
    'cogs.tickets', 'cogs.scanner', 'cogs.leaderboard',
    'cogs.admin', 'cogs.workflows',
})
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'migrations'


def bot_is_ready(bot):
    if bot is None or not bot.is_ready():
        return False
    if not REQUIRED_EXTENSIONS.issubset(bot.extensions):
        return False
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT name FROM migrations')
                applied = {row['name'] for row in cursor.fetchall()}
                required = {path.name for path in MIGRATIONS_DIR.glob('*.sql')}
                return required.issubset(applied)
    except Exception:
        return False
