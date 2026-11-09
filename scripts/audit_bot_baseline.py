"""Offline audit probes: synthetic fixtures only; no credentials, network or database."""
import ast
import json
from pathlib import Path
import re
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
config_tree = ast.parse((ROOT / 'config.py').read_text(encoding='utf-8'))
config = types.ModuleType('config')
for statement in config_tree.body:
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id.startswith('SCAN_'):
                try:
                    setattr(config, target.id, ast.literal_eval(statement.value))
                except ValueError:
                    setattr(config, target.id, True)
config.TICKETS_DIR = str(ROOT / 'tickets')
sys.modules['config'] = config
from services.code_scanner import CodeScanner
from ticket_loader import load_tickets_from_folder

results = {}
scanner = CodeScanner()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    fake_secret = 'SYNTHETIC_AUDIT_SECRET_0123456789'
    (root / 'sample.py').write_text(
        f'api_key = "{fake_secret}"\nprint("Normal CLI output")\n', encoding='utf-8')
    findings = scanner.scan_directory(directory)
    markdown = scanner.generate_ticket_markdown('hardcoded_secrets', findings['hardcoded_secrets'], 'audit')
    results['synthetic_secret_copied_into_ticket'] = fake_secret in markdown
    results['ordinary_cli_output_flagged_as_debug'] = len(findings['debug_statements']) == 1
    (root / 'tickets').mkdir()
    outside = root / 'outside'
    outside.mkdir()
    (outside / 'sample.md').write_text('# Outside ticket\n', encoding='utf-8')
    import ticket_loader
    ticket_loader.TICKETS_DIR = str(root / 'tickets')
    try:
        results['loader_accepts_parent_directory'] = len(load_tickets_from_folder('../outside')) == 1
    except ValueError:
        results['loader_accepts_parent_directory'] = False
    ticket_loader.TICKETS_DIR = str(ROOT / 'tickets')

from services.scan_safety import validate_repo_url
try:
    validate_repo_url('https://github.com.example.invalid/team/repo.git')
    results['non_github_host_passes_validator'] = True
except ValueError:
    results['non_github_host_passes_validator'] = False
tickets = load_tickets_from_folder('otog-capstone')
results['otog_tickets_parsed'] = len(tickets)
results['otog_ticket_has_structured_due_date'] = 'due_date' in tickets[0]
results['otog_ticket_has_structured_owner'] = bool(tickets[0].get('owner_suggestion'))
print(json.dumps(results, indent=2))
