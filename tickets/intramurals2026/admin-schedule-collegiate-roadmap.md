# Implement Collegiate Program Roadmap and Admin Management

## Problem

The tournament needs a visualization of collegiate program dates, and admins need tools to manage these dates.

## Potentially Related Files

- [prisma/schema.prisma](../app/prisma/schema.prisma) — Add `CollegiateProgram` model.
- [app/(public)/schedule/page.tsx](../app/app/(public)/schedule/page.tsx)
- [components/public/schedule/roadmap-timeline.tsx](../app/components/public/schedule/roadmap-timeline.tsx) [NEW]
- [app/admin/programs/page.tsx](../app/app/admin/programs/page.tsx) [NEW]

## What to Fix

1.  **Roadmap**: Design a beautiful timeline for collegiate programs on the schedule page.
2.  **Dates**: Seed data using the Discord #resources information.
3.  **Admin**: Create `/admin/programs` to Allow CRUD operations on program dates.

## Acceptance Criteria

- Beautiful roadmap visible on the public schedule page.
- Admins can update collegiate program dates and details.
