# Fix Empty Exception Handlers in tests

## Problem

Empty or swallowed exception handlers were found. These hide errors and make debugging difficult. Each catch block should either handle the error properly or re-throw it.

## Potentially Related Files

- `tests/test_scan_project.py`

## What to Fix

1. `tests/test_scan_project.py` line 21: Empty or swallowed exception handler

## Acceptance Criteria

- All catch/except blocks either handle errors meaningfully or re-throw
- No silently swallowed exceptions in the affected files
