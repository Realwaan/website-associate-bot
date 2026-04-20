# Add Missing Sports to Schedule

## Problem

The schedule page is missing several existing sports — presumably sports exist in the database but are not displaying in the schedule view or filter/category lists.

## Potentially Related Files

- [actions/sport.ts](../app/actions/sport.ts) — Server action to fetch sports
- [components/public/schedule/schedule-content.tsx](../app/components/public/schedule/schedule-content.tsx) — Displays filtered matches by sport
- [actions/match.ts](../app/actions/match.ts) — Fetch matches (may need sport join)
- [prisma/schema.prisma](../app/prisma/schema.prisma) — Sport model definition

## What to Fix

1. Audit which sports should be displayed but are missing
2. Verify sports exist in database (via Prisma Studio or Supabase)
3. Check schedule filtering logic — ensure all sports are fetched and displayed
4. If sports are hidden (e.g., `is_active` field), add field to sportmodel if needed
5. Test that all sports render with correct matches in schedule

## Acceptance Criteria

- All expected sports appear in schedule filter/list
- Each sport displays its associated matches
- No sports are missing from the display
- Schedule loads correctly with all sports populated
