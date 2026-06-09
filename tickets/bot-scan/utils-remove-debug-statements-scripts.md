# Remove Debug Statements in scripts

## Problem

Debug/console statements were found left in production code. These should be removed or replaced with proper logging before deployment.

## Potentially Related Files

- `scripts/check_secrets.py`
- `scripts/install_git_hook.py`
- `scripts/migrate_db.py`
- `scripts/scan_project.py`

## What to Fix

1. `scripts/check_secrets.py` line 52: Debug statement left in code
2. `scripts/check_secrets.py` line 85: Debug statement left in code
3. `scripts/check_secrets.py` line 93: Debug statement left in code
4. `scripts/check_secrets.py` line 95: Debug statement left in code
5. `scripts/check_secrets.py` line 96: Debug statement left in code
6. `scripts/check_secrets.py` line 99: Debug statement left in code
7. `scripts/install_git_hook.py` line 18: Debug statement left in code
8. `scripts/install_git_hook.py` line 28: Debug statement left in code
9. `scripts/install_git_hook.py` line 31: Debug statement left in code
10. `scripts/install_git_hook.py` line 32: Debug statement left in code
11. `scripts/migrate_db.py` line 14: Debug statement left in code
12. `scripts/migrate_db.py` line 17: Debug statement left in code
13. `scripts/migrate_db.py` line 27: Debug statement left in code
14. `scripts/migrate_db.py` line 42: Debug statement left in code
15. `scripts/migrate_db.py` line 45: Debug statement left in code
16. `scripts/migrate_db.py` line 55: Debug statement left in code
17. `scripts/migrate_db.py` line 59: Debug statement left in code
18. `scripts/migrate_db.py` line 60: Debug statement left in code
19. `scripts/migrate_db.py` line 63: Debug statement left in code
20. `scripts/migrate_db.py` line 98: Debug statement left in code
21. `scripts/migrate_db.py` line 99: Debug statement left in code
22. `scripts/scan_project.py` line 91: Debug statement left in code
23. `scripts/scan_project.py` line 491: Debug statement left in code
24. `scripts/scan_project.py` line 631: Debug statement left in code
25. `scripts/scan_project.py` line 632: Debug statement left in code
26. `scripts/scan_project.py` line 639: Debug statement left in code
27. `scripts/scan_project.py` line 640: Debug statement left in code
28. `scripts/scan_project.py` line 641: Debug statement left in code
29. `scripts/scan_project.py` line 642: Debug statement left in code
30. `scripts/scan_project.py` line 643: Debug statement left in code

## Acceptance Criteria

- No `console.log` / `print()` / `debugger` statements remain in production code
- Proper logging (if needed) replaces removed debug statements
