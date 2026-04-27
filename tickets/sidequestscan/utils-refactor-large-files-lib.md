# Refactor Large Files in lib

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `lib/notifications.ts`
- `lib/wallet-badges.ts`

## What to Fix

1. `lib/notifications.ts`: File has 330 lines (threshold: 300). Consider refactoring.
2. `lib/wallet-badges.ts`: File has 634 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
