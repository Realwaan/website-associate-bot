"""Shared output redaction and bounded GitHub cloning."""
import os
import re
import subprocess
from urllib.parse import urlsplit

_SECRET = re.compile(
    r'''(?i)(?:api[_-]?key|secret|password|token|auth)\s*[:=]\s*["'][^"']+["']'''
    r'|ghp_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}|(?:sk|pk)_(?:live|test)_[A-Za-z0-9]+'
    r'|eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?'
)


def redact_source(text):
    # Omit the entire line: multiple detectors must never preserve another copy.
    return '[REDACTED: potential credential]' if _SECRET.search(text) else text


def validate_repo_url(value):
    value = (value or '').strip()
    if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        value = 'https://github.com/' + value + '.git'
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com'
            or parsed.query or parsed.fragment
            or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', parsed.path)):
        raise ValueError('Use an HTTPS github.com owner/repository URL.')
    return value


def clone_repository(url, destination, token=None):
    url = validate_repo_url(url)
    env = os.environ.copy()
    # Do not inherit arbitrary Git config injected through environment variables.
    for key in list(env):
        if key.startswith('GIT_CONFIG_'):
            env.pop(key)
    settings = [('http.followRedirects', 'false'), ('credential.helper', ''),
                ('protocol.allow', 'never'), ('protocol.https.allow', 'always')]
    if token:
        settings.append(('http.https://github.com/.extraHeader', 'Authorization: Bearer ' + token))
    env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_COUNT=str(len(settings)))
    for index, (key, value) in enumerate(settings):
        env[f'GIT_CONFIG_KEY_{index}'] = key
        env[f'GIT_CONFIG_VALUE_{index}'] = value
    return subprocess.run(['git', 'clone', '--depth', '1', '--', url, destination],
                          env=env, capture_output=True, text=True, timeout=120)
