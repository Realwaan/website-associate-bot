import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import database
from services.authorization import get_user_roles
from services.scan_safety import validate_repo_url, clone_repository
from services.code_scanner import CodeScanner
from services.ticket_presentation import ticket_embed
from ticket_loader import resolve_ticket_folder, ticket_files, load_tickets_from_folder, validate_ticket


@pytest.mark.parametrize('url', ['https://github.com.evil.invalid/a/b', 'https://evil.invalid/github.com/repo',
                                'http://github.com/a/b', 'https://github.com:443/a/b',
                                'https://user@github.com/a/b', 'https://127.0.0.1/a/b'])
def test_no_credentials_to_unapproved_origin(url):
    with pytest.raises(ValueError):
        validate_repo_url(url)


def test_clone_has_timeout_no_redirects_and_no_secret_in_argv():
    with patch('services.scan_safety.subprocess.run') as run:
        clone_repository('owner/repo', 'destination', 'SYNTHETIC_TOKEN')
    args, kwargs = run.call_args
    assert 'SYNTHETIC_TOKEN' not in str(args)
    assert kwargs['timeout'] == 120
    env = kwargs['env']
    settings = {env[f'GIT_CONFIG_KEY_{i}']: env[f'GIT_CONFIG_VALUE_{i}'] for i in range(int(env['GIT_CONFIG_COUNT']))}
    assert settings['http.followRedirects'] == 'false'
    assert settings['http.https://github.com/.extraHeader'].endswith('SYNTHETIC_TOKEN')


def test_scanners_do_not_serialize_secrets_even_in_other_categories():
    from scripts.scan_project import _detect_in_file
    secret = 'SYNTHETIC_SECRET_12345678901234567890'
    line = f'api_key = "{secret}" # TODO: remove\n'
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, 'sample.py').write_text(line, encoding='utf-8')
        scanner = CodeScanner()
        results = scanner.scan_directory(directory)
        assert results['hardcoded_secrets']
        assert secret not in json.dumps(results)
        for category, findings in results.items():
            assert secret not in scanner.generate_ticket_markdown(category, findings, 'test')
    assert secret not in str(_detect_in_file('sample.py', [line]))


def test_import_containment_and_planning_files():
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory, 'tickets'); base.mkdir()
        folder = base / 'valid'; folder.mkdir()
        (folder / 'PLAN.md').write_text('# Plan')
        (folder / 'ticket.md').write_text('# Ticket')
        with pytest.raises(ValueError):
            resolve_ticket_folder('../outside', base)
        with pytest.raises(ValueError):
            resolve_ticket_folder(directory, base)
        assert [p.name for p in ticket_files('valid', base)] == ['ticket.md']


def test_capstone_bundle_is_complete_and_scheduled():
    tickets = load_tickets_from_folder('otog-capstone')
    assert len(tickets) == 18
    ids = {ticket['ticket_id'] for ticket in tickets}
    assert len(ids) == 18
    by_id = {t['ticket_id']: t for t in tickets}
    import re
    for ticket in tickets:
        validate_ticket(ticket)
        assert ticket['start_date'] <= ticket['due_date'] <= '2026-12-08'
        assert ticket['owner_suggestion']
        assert ticket['timezone'] == 'Asia/Manila'
        assert len(ticket_embed(ticket, 'otog-capstone')) <= 6000
        for dependency in re.findall(r'CAP-\d{2}', ticket['dependencies']):
            assert dependency in ids and dependency != ticket['ticket_id']
            assert by_id[dependency]['due_date'] <= ticket['due_date']


def test_ordinary_output_is_not_reported_as_debug():
    from scripts.scan_project import _detect_in_file
    lines = ['print("Welcome to the application")', 'console.error("Request failed")']
    assert not any(i.category == 'debug' for i in _detect_in_file('app.py', lines))
    assert any(i.category == 'debug' for i in _detect_in_file('app.py', ['print("debugging")']))


def test_permissions_are_current_server_specific():
    member_a = SimpleNamespace(id=7, guild=SimpleNamespace(id=1), roles=[SimpleNamespace(name='Project Manager')], guild_permissions=None)
    member_b = SimpleNamespace(id=7, guild=SimpleNamespace(id=2), roles=[], guild_permissions=None)
    assert get_user_roles(7, member_a)['is_pm']
    assert not get_user_roles(7, member_b)['is_pm']
    assert not get_user_roles(7)['is_pm']
    member_a.roles.clear()
    assert not get_user_roles(7, member_a)['is_pm']


def test_stale_transition_never_mutates_or_scores():
    conn = MagicMock(); cursor = conn.cursor.return_value
    cursor.fetchone.return_value = {'status': 'CLAIMED', 'claimed_by_id': 2}
    with patch.object(database, 'get_db') as context:
        context.return_value.__enter__.return_value = conn
        with pytest.raises(ValueError, match='changed'):
            database.update_thread_status(1, 'CLAIMED', claimed_by_id=3, expected={'status': 'OPEN'})
    assert cursor.execute.call_count == 1
    conn.commit.assert_not_called()


def test_transition_and_score_use_same_connection_and_commit():
    conn = MagicMock(); cursor = conn.cursor.return_value
    old = {'status': 'CLAIMED', 'claimed_by_id': 2, 'resolved_by_id': None, 'reviewed_by_id': None}
    cursor.fetchone.return_value = old
    with patch.object(database, 'get_db') as context, patch.object(database, 'sync_linked_task_status'):
        context.return_value.__enter__.return_value = conn
        database.update_thread_status(1, 'PENDING-REVIEW', resolved_by_id=2, resolved_by_username='Dev', expected=old)
    queries = [args[0][0] for args in cursor.execute.call_args_list]
    assert 'FOR UPDATE' in queries[0]
    assert any('UPDATE threads' in q for q in queries)
    assert any('INSERT INTO leaderboard' in q for q in queries)
    conn.commit.assert_called_once()


def test_score_failure_does_not_commit_state():
    conn = MagicMock(); cursor = conn.cursor.return_value
    cursor.fetchone.return_value = {'status': 'CLAIMED', 'resolved_by_id': None, 'reviewed_by_id': None}
    cursor.execute.side_effect = [None, None, RuntimeError('injected score failure')]
    with patch.object(database, 'get_db') as context:
        context.return_value.__enter__.return_value = conn
        with pytest.raises(RuntimeError):
            database.update_thread_status(1, 'PENDING-REVIEW', resolved_by_id=2, resolved_by_username='Dev')
    conn.commit.assert_not_called()


def test_pool_queues_waiters_and_evicts_broken_connections():
    import threading
    import time
    from psycopg2 import pool as psycopg2_pool

    fake_pool = MagicMock()
    broken_conn = MagicMock(closed=1)
    good_conn = MagicMock(closed=0)
    fake_pool.getconn.side_effect = [broken_conn, good_conn]

    conn = database._acquire_pooled_connection(fake_pool, timeout=1.0)
    assert conn is good_conn
    fake_pool.putconn.assert_called_once_with(broken_conn, close=True)
    database._release_pooled_connection(fake_pool, conn)
    fake_pool.putconn.assert_called_with(good_conn, close=False)

    # Verify bounded semaphore waits and wakes up when a slot is released
    sem = threading.BoundedSemaphore(1)
    sem.acquire()
    pool2 = MagicMock()
    pool2.getconn.return_value = good_conn

    def release_soon():
        time.sleep(0.05)
        sem.release()

    with patch.object(database, '_pool_semaphore', sem):
        t = threading.Thread(target=release_soon)
        t.start()
        acquired = database._acquire_pooled_connection(pool2, timeout=1.0)
        assert acquired is good_conn
        database._release_pooled_connection(pool2, acquired)
        t.join()

        # Exhausted timeout raises PoolError
        sem.acquire()
        with pytest.raises(psycopg2_pool.PoolError):
            database._acquire_pooled_connection(pool2, timeout=0.02)
        sem.release()


def test_guild_scoped_settings_and_leaderboard_queries():
    conn = MagicMock(); cursor = conn.cursor.return_value
    cursor.fetchone.return_value = {'value': '999'}
    with patch.object(database, 'get_db') as context:
        context.return_value.__enter__.return_value = conn
        database.set_setting('reminders_channel_id', '999', guild_id=42)
        val = database.get_setting('reminders_channel_id', guild_id=42)
    assert val == '999'
    insert_sql, insert_params = cursor.execute.call_args_list[0][0]
    assert 'ON CONFLICT (guild_id, key)' in insert_sql
    assert insert_params == (42, 'reminders_channel_id', '999')

    conn2 = MagicMock(); cursor2 = conn2.cursor.return_value
    cursor2.fetchall.return_value = [{'user_id': 7, 'username': 'dev', 'dev_resolved_count': 3, 'last_dev_resolved': None}]
    with patch.object(database, 'get_db') as context2:
        context2.return_value.__enter__.return_value = conn2
        rows = database.get_leaderboard_dev(limit=5, guild_id=42)
    assert len(rows) == 1
    lb_sql, lb_params = cursor2.execute.call_args_list[0][0]
    assert 'WHERE guild_id = %s' in lb_sql
    assert lb_params == (42, 5)


def test_webhook_push_when_bot_unready_enqueues_dead_letter():
    import main
    payload = {
        'ref': 'refs/heads/main',
        'repository': {'name': 'repo', 'owner': {'login': 'owner'}},
        'commits': [{'id': 'c1', 'message': 'fix'}],
    }
    with patch('webhook_security.verify_github_signature', return_value=True), \
         patch.object(main, 'register_webhook_delivery', return_value=True), \
         patch.object(main, 'bot', None), \
         patch.object(main, 'enqueue_webhook_dead_letter') as mock_dl:
        code, msg = main.github_webhook_handler(json.dumps(payload).encode('utf-8'), {'X-GitHub-Event': 'push', 'X-GitHub-Delivery': 'd-1'})
    assert code == 202
    mock_dl.assert_called_once()

