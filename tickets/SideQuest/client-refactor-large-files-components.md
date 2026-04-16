# Refactor Large Files in components

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `components/account-overview.tsx`
- `components/ai-assistant-widget.tsx`
- `components/budgets-manager.tsx`
- `components/collaboration-manager.tsx`
- `components/installments-manager.tsx`
- `components/recurring-manager.tsx`
- `components/transactions-manager.tsx`

## What to Fix

1. `components/account-overview.tsx`: File has 744 lines (threshold: 300). Consider refactoring.
2. `components/ai-assistant-widget.tsx`: File has 345 lines (threshold: 300). Consider refactoring.
3. `components/budgets-manager.tsx`: File has 457 lines (threshold: 300). Consider refactoring.
4. `components/collaboration-manager.tsx`: File has 1062 lines (threshold: 300). Consider refactoring.
5. `components/installments-manager.tsx`: File has 1165 lines (threshold: 300). Consider refactoring.
6. `components/recurring-manager.tsx`: File has 509 lines (threshold: 300). Consider refactoring.
7. `components/transactions-manager.tsx`: File has 2259 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
