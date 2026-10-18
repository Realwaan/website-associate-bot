# 13-pre-demo-safety-check.md

## Problem
Leaking the API key or hitting disallowed ports means disqualification, and a flaky network can break the live demo.

## Potentially Related Files
- `.env`, `.gitignore`
- `scripts/check_secrets.py` in the bot repo

## What to Fix
1. Run a secret scan on the product repo before the final push.
2. Confirm the app only calls the provided Gemma API and no other external ports.
3. Cache a few demo answers locally as a fallback if the API is slow.
4. Close unrelated apps and tabs before presenting.

## Acceptance Criteria
- Secret scan reports nothing.
- The key is stored only in each teammate's local `.env`.
- Demo works with the fallback if the network drops.
