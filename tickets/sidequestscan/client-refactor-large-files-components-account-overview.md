# Refactor Large Files in components/account-overview

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `components/account-overview/account-overview-card-transactions-modal.tsx`
- `components/account-overview/use-account-overview.ts`

## What to Fix

1. `components/account-overview/account-overview-card-transactions-modal.tsx`: File has 310 lines (threshold: 300). Consider refactoring.
2. `components/account-overview/use-account-overview.ts`: File has 360 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
