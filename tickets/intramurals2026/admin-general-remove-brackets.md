# Remove Brackets Tab from Admin Dashboard

## Problem

The admin dashboard currently includes a Brackets tab for managing elimination bracket nodes. This feature should be removed from the admin UI navigation.

## Potentially Related Files

- [components/admin/sidebar.tsx](../app/components/admin/sidebar.tsx) — Admin sidebar navigation (likely defines Brackets tab/link)
- [components/admin/mobile-nav.tsx](../app/components/admin/mobile-nav.tsx) — Mobile admin nav
- [app/admin/(dashboard)/](../app/app/admin/(dashboard)/) — Dashboard layout and routes
- [actions/bracket.ts](../app/actions/bracket.ts) — Bracket server actions (can remain in codebase for api use)

## What to Fix

1. Remove Brackets link/entry from admin sidebar component
2. Remove Brackets link from mobile admin navigation
3. Remove or deprecate the brackets dashboard/route page (optional, can redirect to 404)
4. Keep bracket database infrastructure and server actions intact (for API/internal use)

## Acceptance Criteria

- No "Brackets" tab/link visible in admin sidebar
- No Brackets option in mobile admin menu
- Accessing `/admin/brackets` directly either redirects or shows 404
- Other admin tabs/pages remain functional
- Bracket data remains in database (not deleted)
