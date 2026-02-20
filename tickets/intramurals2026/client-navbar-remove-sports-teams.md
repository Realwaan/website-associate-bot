# Remove SPORTS and TEAMS links from Navbar

## Problem

The navbar currently displays "Sports" and "Teams" links that should be removed from the public navigation. These routes exist but should not be user-facing in the main menu.

## Potentially Related Files

- [components/public/navbar.tsx](../app/components/public/navbar.tsx) — Line 18–20: `navLinks` array defines all navigation items including "Sports" and "Teams"
- [app/(public)/sports/](../app/app/(public)/sports/) — Route page (keep but hide from nav)
- [app/(public)/teams/](../app/app/(public)/teams/) — Route page (keep but hide from nav)

## What to Fix

1. Remove the `/sports` and `/teams` entries from the `navLinks` array in `navbar.tsx`
2. Verify that the routes still exist (users can access via direct URL) but are no longer in the navigation menu
3. Update mobile menu to reflect the same change

## Acceptance Criteria

- "Sports" link is not visible in desktop navbar
- "Teams" link is not visible in mobile fullscreen menu
- Routes remain accessible via direct URL (no 404)
- Navigation highlights correct active route after removal
