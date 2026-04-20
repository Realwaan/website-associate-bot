# client-help-center-cleanup.md

## Problem
The Help Center currently presents two primary actions: "Request Help NOW" and "Report hazard". The user wants to simplify the interface to focus primarily on emergency assistance, keeping only the "Request Help NOW" button.

## Potentially Related Files
- [HelpDashboard.tsx](../apps/mobile/src/components/screens/HelpDashboard.tsx#L262-L279) - Current implementation of the "Report hazard" card and button

## What to Fix
1. Locate the card component for "Report hazard" in `HelpDashboard.tsx`.
2. Delete the entire `div` containing the "Report hazard" info and button (lines 262 to 279).
3. Ensure no unused imports or state variables remain if they were only used for this specific card.

## Acceptance Criteria
- The "Report hazard" card and button are no longer visible in the Help Center dashboard.
- The "Request Help NOW" button remains functional and correctly styled.
- The layout adjusts properly to the removal of the hazard report section.
