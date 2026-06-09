# Refactor Large Files

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `ai_client.py`
- `database.py`
- `main.py`
- `math_renderer.py`
- `pdf_brief_scanner.py`
- `repo_updates.py`

## What to Fix

1. `ai_client.py`: File has 344 lines (threshold: 300). Consider refactoring.
2. `database.py`: File has 1159 lines (threshold: 300). Consider refactoring.
3. `main.py`: File has 4209 lines (threshold: 300). Consider refactoring.
4. `math_renderer.py`: File has 358 lines (threshold: 300). Consider refactoring.
5. `pdf_brief_scanner.py`: File has 489 lines (threshold: 300). Consider refactoring.
6. `repo_updates.py`: File has 429 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
