# Refactor Large Files in components/ui

## Problem

The following files exceed the recommended line-count threshold and may benefit from being split into smaller, more focused modules.

## Potentially Related Files

- `components/ui/category-combobox.tsx`

## What to Fix

1. `components/ui/category-combobox.tsx`: File has 456 lines (threshold: 300). Consider refactoring.

## Acceptance Criteria

- Each flagged file is split into smaller modules (under the line threshold) or justified with a comment
- All imports and references updated after refactoring
