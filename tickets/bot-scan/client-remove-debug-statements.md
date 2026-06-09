# Remove Debug Statements

## Problem

Debug/console statements were found left in production code. These should be removed or replaced with proper logging before deployment.

## Potentially Related Files

- `dev.py`
- `main.py`
- `ticket_loader.py`

## What to Fix

1. `dev.py` line 67: Debug statement left in code
2. `dev.py` line 74: Debug statement left in code
3. `dev.py` line 79: Debug statement left in code
4. `dev.py` line 100: Debug statement left in code
5. `dev.py` line 115: Debug statement left in code
6. `main.py` line 457: Debug statement left in code
7. `main.py` line 3381: Debug statement left in code
8. `ticket_loader.py` line 104: Debug statement left in code

## Acceptance Criteria

- No `console.log` / `print()` / `debugger` statements remain in production code
- Proper logging (if needed) replaces removed debug statements
