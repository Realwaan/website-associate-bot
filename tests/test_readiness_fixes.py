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
