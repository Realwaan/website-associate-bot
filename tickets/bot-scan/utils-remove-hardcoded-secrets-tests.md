# Remove Hardcoded Secrets in tests

**[CRITICAL]**

## Problem

Possible hardcoded secrets, API keys, or tokens were detected in the source code. These should be moved to environment variables immediately.

## Potentially Related Files

- `tests/test_scan_project.py`
- `tests/test_webhook_integration.py`

## What to Fix

1. `tests/test_scan_project.py` line 22: Possible hardcoded secret or API key
2. `tests/test_webhook_integration.py` line 16: Possible hardcoded secret or API key
3. `tests/test_webhook_integration.py` line 29: Possible hardcoded secret or API key
4. `tests/test_webhook_integration.py` line 46: Possible hardcoded secret or API key

## Acceptance Criteria

- All secrets moved to environment variables (`.env`)
- No plaintext keys or tokens remain in source code
- `.env.example` updated with placeholder keys
