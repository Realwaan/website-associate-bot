# Remove Hardcoded Secrets in scripts

**[CRITICAL]**

## Problem

Possible hardcoded secrets, API keys, or tokens were detected in the source code. These should be moved to environment variables immediately.

## Potentially Related Files

- `scripts/scan_project.py`

## What to Fix

1. `scripts/scan_project.py` line 39: Possible hardcoded secret or API key

## Acceptance Criteria

- All secrets moved to environment variables (`.env`)
- No plaintext keys or tokens remain in source code
- `.env.example` updated with placeholder keys
