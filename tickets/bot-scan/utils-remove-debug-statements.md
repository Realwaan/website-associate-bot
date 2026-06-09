# Remove Debug Statements

## Problem

Debug/console statements were found left in production code. These should be removed or replaced with proper logging before deployment.

## Potentially Related Files

- `config.py`

## What to Fix

1. `config.py` line 22: Debug statement left in code

## Acceptance Criteria

- No `console.log` / `print()` / `debugger` statements remain in production code
- Proper logging (if needed) replaces removed debug statements
