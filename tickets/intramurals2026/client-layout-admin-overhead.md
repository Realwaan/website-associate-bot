# Add Admin Dashboard overhead banner to public layout

## Problem

Admins currently browse the public site without an easy way to jump back to their dashboard. Similar to WordPress, if an admin visits `/`, they should see an overhead banner/bar providing a quick link back to the Admin Dashboard.

## Potentially Related Files

- [app/(public)/layout.tsx](../app/app/(public)/layout.tsx) — The public layout wrapper for the application.
- [components/public/navbar.tsx](../app/components/public/navbar.tsx) — May need adjustment to accommodate the top banner.

## What to Fix

1. In `app/(public)/layout.tsx` (or a dedicated component imported there), verify the current user's session and role.
2. If `user.role === 'ADMIN'`, conditionally render a sticky header at the very top of the layout.
3. The banner should say "Go to Admin Dashboard" and link to `/admin` or the appropriate admin root route.

## Acceptance Criteria

- Only users with `ADMIN` role see the banner.
- The banner appears at the top of the screen overlaid/above the standard navbar.
- Clicking the banner correctly routes the admin to the Admin Dashboard.
- Standard users (`NORMAL` role) or guests do not see this banner.
