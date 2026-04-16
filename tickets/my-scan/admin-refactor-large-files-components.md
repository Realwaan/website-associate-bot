# Refactor Large Files in components

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `components/dashboard-dashboard.tsx`

## What to Fix

1. `components/dashboard-dashboard.tsx`: File has 1589 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
