from unittest.mock import MagicMock, patch

import pytest

from services import readiness
import keep_alive


@pytest.mark.parametrize('connected,extensions,db_error,missing,expected', [
    (False, True, False, False, False),
    (True, False, False, False, False),
    (True, True, True, False, False),
    (True, True, False, True, False),
    (True, True, False, False, True),
])
def test_required_dependencies(connected, extensions, db_error, missing, expected):
    bot = MagicMock()
    bot.is_ready.return_value = connected
    bot.extensions = readiness.REQUIRED_EXTENSIONS if extensions else {}
    with patch.object(readiness, 'get_db') as db:
        if db_error:
            db.side_effect = RuntimeError('offline')
        cursor = db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [] if missing else [
            {'name': p.name} for p in readiness.MIGRATIONS_DIR.glob('*.sql')
        ]
        assert readiness.bot_is_ready(bot) is expected
        if not connected or not extensions:
            db.assert_not_called()


def test_readiness_exception_returns_503_and_liveness_stays_available():
    with patch.object(keep_alive, '_capstone_ready_checker', side_effect=RuntimeError('private detail')):
        client = keep_alive.app.test_client()
        response = client.get('/ready')
        assert response.status_code == 503
        assert b'private detail' not in response.data
        assert client.get('/health').status_code == 200
