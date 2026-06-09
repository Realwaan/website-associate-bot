# Refactor Large Files in scripts

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `scripts/roadmap_builder.py`
- `scripts/scan_project.py`

## What to Fix

1. `scripts/roadmap_builder.py`: File has 1005 lines (threshold: 300). Consider refactoring.
2. `scripts/scan_project.py`: File has 647 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
