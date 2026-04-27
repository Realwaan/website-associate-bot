# Refactor Large Files in app/api/assistant

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `app/api/assistant/providers.ts`
- `app/api/assistant/transaction-actions.ts`

## What to Fix

1. `app/api/assistant/providers.ts`: File has 305 lines (threshold: 300). Consider refactoring.
2. `app/api/assistant/transaction-actions.ts`: File has 595 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
