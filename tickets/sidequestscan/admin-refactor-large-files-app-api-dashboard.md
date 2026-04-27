# Refactor Large Files in app/api/dashboard

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `app/api/dashboard/route.ts`

## What to Fix

1. `app/api/dashboard/route.ts`: File has 514 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
